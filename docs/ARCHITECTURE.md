# Architektur & Stack

Romseerr ist bewusst **eine schlanke Oberfläche vor bestehenden Werkzeugen** —
es lädt nicht selbst herunter und verwaltet keine Bibliothek, sondern orchestriert
Suche, Download und Einsortierung über den umliegenden Stack.

## Überblick

```mermaid
flowchart TD
    U[Benutzer im Browser] -->|Login/Suche/Anfrage| R[Romseerr :8770]

    R -->|Titel-Suche| A[(Archive.org API)]
    R -->|Cover/Beschreibung/Beliebt| I[(IGDB API)]
    R -->|Usenet-Suche, lesend| P[Prowlarr :9696]

    R -->|Archive.org: aria2 direkt| ST[/config/staging]
    R -->|Usenet: addurl cat=roms| S[SABnzbd]
    R -->|Filehoster: .crawljob| J[JDownloader]

    S -->|fertig| SC[/sab-complete]
    J -->|fertig| JO[/jd-output]
    ST --> IMP{Import: entpacken,\nPlattform erkennen, dedup}
    SC --> IMP
    JO --> IMP
    IMP -->|einsortiert| LIB[(ROM-Bibliothek\n/roms/&lt;plattform&gt;)]
    LIB --> M[RomM :8998]
    LIB --> RN[RetroNAS]
    IMP -.Discord.-> N[Benachrichtigung]
```

## Komponenten

| Dienst | Rolle | Port | Von Romseerr genutzt über |
|---|---|---|---|
| **Romseerr** | Such-/Anfrage-Oberfläche, Import-Logik, Benutzerverwaltung | 8770 | — |
| **Prowlarr** | Usenet-Indexer-Suche (nur **lesend** abgefragt) | 9696 | REST-API `X-Api-Key` |
| **SABnzbd** | Usenet-Downloads (isolierte Kategorie `roms`) | 8080 | REST-API `addurl` |
| **JDownloader** | Filehoster-Downloads (`.crawljob` via FolderWatch) | 5800 | Datei-Ablage in `folderwatch/` |
| **RomM** (+ MariaDB) | Bibliothek, Cover, Im-Browser-Spielen | 8998 | teilt sich die Bibliothek; Filesystem-Watcher |
| **Archive.org** | Retro-ROM-Quelle (Such-API + direkte Downloads) | — | HTTPS |
| **IGDB** | Cover, Beschreibungen, „beliebt je Konsole" | — | HTTPS (Twitch-OAuth) |

**Wichtig:** Romseerr fasst die Film-/Serien-Kette nicht an. Prowlarr wird nur
gelesen; Usenet-Grabs laufen über eine **eigene SABnzbd-Kategorie** (`roms`) mit
eigenem Zielordner, damit Radarr/Sonarr davon nichts sehen.

## Datenfluss

1. **Suche** — Romseerr fragt parallel Archive.org (Titel-Suche, Retro) und
   Prowlarr (Usenet, moderne Konsolen) ab, reichert mit IGDB-Covern an, prüft
   jeden Treffer gegen die Bibliothek (**Dedup**) und filtert nach Plattform-Vorauswahl.
2. **Anfrage/Download** — je Quelle:
   - *Archive.org* → `aria2` lädt direkt nach `/config/staging`.
   - *Usenet* → `addurl` an SABnzbd, Kategorie `roms`, Ergebnis in `/sab-complete`.
   - *Filehoster* → `.crawljob` in JDownloaders `folderwatch/`, Ergebnis in `/jd-output`.
3. **Import** — ein Hintergrund-Worker erkennt fertige Downloads, entpackt
   (`unar`), bestimmt die Plattform an der **Dateiendung** (`.sfc`→snes …),
   überspringt bereits Vorhandenes (Dedup) und verschiebt nach
   `/roms/<plattform>/`.
4. **Bibliothek** — RomM und RetroNAS teilen sich denselben `/roms`-Baum. RomMs
   Filesystem-Watcher erkennt die neue Datei; optional meldet Romseerr die
   Verfügbarkeit per Discord.

## Konfiguration (Auszug)

Alle Werte über `.env` (siehe `.env.example`). Im **Full-Stack-Compose** zeigen
die URLs auf die Dienstnamen, **standalone** auf deine Hosts:

| Variable | Full-Stack | Standalone (Beispiel) |
|---|---|---|
| `SAB_URL` | `http://sabnzbd:8080` | `http://192.168.1.10:8081` |
| `PROWLARR_URL` | `http://prowlarr:9696` | `http://192.168.1.10:9696` |
| `ROMM_URL` | `http://romm:8080` | `http://192.168.1.10:8998` |
| `JD_DL_BASE` | `/output/romseerr` (Sicht des JD-Containers) | dito |

### JDownloader-Übergabe: drei Sichten, ein Ordner (#197)

Es gibt keine API — die Übergabe läuft über zwei Verzeichnisse, und beide Container
sehen sie unter verschiedenen Namen:

| Sicht | Romseerr | JDownloader |
|---|---|---|
| Auftrag (`.crawljob`) | `/jd-watch` (`JD_WATCH`) | `/config/folderwatch` |
| Ergebnis | `/jd-output/…` (`JD_OUT`) | `/output/…` (`JD_DL_BASE`) |

`JD_OUT` wird **abgeleitet**, wenn es leer ist: das erste Pfadsegment von `JD_DL_BASE`
wird durch `/jd-output` ersetzt. Zwei unabhängige Defaults hatten hier eine stille
Fehlerquelle — wer `JD_DL_BASE` in der Oberfläche änderte, ließ die andere Sicht
zurück, und Romseerr sammelte in einem Ordner ein, den JDownloader nie befüllte.

Der Watch-Ordner braucht Schreibrecht für **beide** Seiten: Romseerr legt die Datei ab,
JDownloader löscht sie nach dem Einlesen. Fehlt es, startet nie ein Download —
sichtbar nur als Warnung, deshalb steht sie seit #197 auch in der Oberfläche
(`/api/config/warnings`).

Auf JDownloader-Seite muss die **FolderWatch-Erweiterung installiert und aktiviert**
sein (*Einstellungen → Extension Modules*). Sie ist nicht Teil der Grundinstallation;
ohne sie wird der Ordner nie gelesen, und Romseerr kann das nicht erkennen — geprüft
wird nur die eigene Hälfte der Übergabe.

#### Das Format der `.crawljob` — Werte, die den Auftrag kosten (#219)

```json
[{"text": "…", "downloadFolder": "/output/romseerr/…", "packageName": "…",
  "autoStart": "TRUE", "autoConfirm": "TRUE"}]
```

`autoStart` und `autoConfirm` sind vom Typ **`BooleanStatus`** (`TRUE` / `FALSE` /
`UNSET`), **nicht** boolean — so beschreibt es die Erweiterung selbst auf ihrer
Einstellungsseite. In dieser Form ist der ganze Weg nachgemessen: Übergabe, Download und
Entpacken durch JDownloader, in 30 Sekunden.

`overwritePackagizerRules` stand hier früher und **existiert nicht** — der Setter heißt
`setOverwritePackagizerEnabled`. Das Feld war immer wirkungslos.

#### JDownloader darf nichts fragen

Der teuerste Fund dabei: Ein **modaler Dialog** blockiert die gesamte Übergabe, und im
Container sieht ihn niemand. Ausgelöst wird er von Standardeinstellungen:

| Einstellung | Standard | Nötig |
|---|---|---|
| `Default On Added Dupes Links Action` | `ASK` | eine Aktion, z. B. `INCLUDE` |
| dieselbe Einstellung für Offline-Links | `ASK` | z. B. `EXCLUDE` |

Steht dort `ASK`, wartet JDownloader beim ersten wiederholten oder toten Link auf eine
Antwort — und **alle** folgenden Aufträge stauen sich dahinter. Von außen sieht das aus,
als verschwänden die Aufträge: die `.crawljob` wird ordnungsgemäß eingelesen und nach
`folderwatch/added/` verschoben, der Link-Collector protokolliert
`Added CrawlerJob … Origin:EXTENSION` — und dann passiert nie wieder etwas. Genau diese
Signatur hat hier eine ganze Messreihe verfälscht.

*EN: `autoStart`/`autoConfirm` are `BooleanStatus` (`TRUE`/`FALSE`/`UNSET`), not boolean.
`overwritePackagizerRules` never existed. And JDownloader must not ask anything in
unattended operation — a modal dialog on duplicate or offline links blocks the whole
hand-off, invisibly, and every later job queues up behind it.*

*EN: three views of the same two directories. `JD_OUT` is derived from `JD_DL_BASE`
unless set; the watch folder must be writable by both containers.*

### Der Usenet-Weg: vier Stufen, einzeln messbar (#196)

Derselbe Fehlertyp wie oben, nur mit SABnzbd. Der Weg hat vier Stellen, an denen er
reißen kann — und von außen sah jede Ursache gleich aus („Usenet geht nicht"):

| Stufe | Was geprüft wird | Wenn sie reißt |
|---|---|---|
| Suche | Prowlarr liefert Usenet-Treffer für die Kategorien aus `prow_cats` | Suche bleibt leer |
| Kategorie | die in `sab_cat` gesetzte Kategorie existiert in SABnzbd | NZB landet in keiner oder der falschen |
| Warteschlange | SABnzbd ist nicht pausiert | NZB wird angenommen und passiert nichts |
| Einsammelordner | Romseerrs `SAB_DONE` ist da und lesbar | Download läuft durch, wird aber nie gefunden |
| Indexer | jeder Indexer liefert auf seine Download-Adresse wirklich eine NZB | Treffer da, aber nichts davon ladbar (#236) |

Die letzte Stufe ist wieder eine Frage zweier **Sichten auf denselben Ordner**:

| Sicht | Romseerr | SABnzbd |
|---|---|---|
| Fertige Downloads | `/sab-complete` (`SAB_DONE`) | `complete_dir` + Unterordner der Kategorie |

Ein Automat kann die beiden Namensräume nicht vergleichen — sie stammen aus
verschiedenen Containern. *Einstellungen → Verbindungen → SABnzbd → **Usenet-Weg
prüfen*** (`GET /api/usenet/check`) stellt sie deshalb nebeneinander und beantwortet die
anderen drei Stufen einzeln. Es wird dabei **nichts heruntergeladen**.

Die Indexer-Stufe ist die, die von innen am schwersten zu sehen ist: ein Indexer kann
Treffer im Überfluss liefern und auf jede Download-Adresse mit seiner eigenen HTML-Seite
antworten. Gemessen wurde genau das — ein Indexer stellte **217 von 231 Treffern** und
keine einzige NZB, während Prowlarr keinerlei Fehler meldete und seine Suche einwandfrei
lief. Unterschieden wird es an einem Header: `application/x-nzb` gegen `text/html`. Weil
so ein Abruf beim Indexer als *grab* gegen ein Stundenlimit zählt, holt die Prüfung
höchstens **eine** Datei je Indexer und nur auf ausdrücklichen Aufruf.

#### Wenn SABnzbd den Download verwirft (#235)

Ein NZB, das SAB nicht laden kann, verlässt die Warteschlange, **ohne** je einen Ordner
anzulegen. `worker_collect` kannte nur zwei Fragen — *ist der Ordner da?* und *steckt es
noch in der Warteschlange?* —, und der Fehlschlag fiel zwischen ihnen hindurch: der
Auftrag blieb unbegrenzt auf `downloading`. SABs History ist die einzige Stelle, die den
Fehlschlag festhält, und sie wurde bis dahin nur nach einem *erfolgreichen* Import
gelesen. `sab_failed()` schaut jetzt auch auf dem Fehlerweg nach und übernimmt SABs
`fail_message` als Begründung an den Auftrag. Der History-Eintrag bleibt liegen — er ist
der Beleg für den Betreiber.

*EN: the usenet path breaks in four distinct places that all look identical from the
outside. `GET /api/usenet/check` (Settings → Connections → SABnzbd) answers each stage
separately without downloading anything. The last stage prints Romseerr's `SAB_DONE` and
SABnzbd's `complete_dir` + category folder side by side: no automation can compare those
two namespaces, but a human can — and if they diverge, downloads complete and are never
picked up. A fifth stage fetches one file per indexer and reports whether it is really an
NZB — an indexer can serve plenty of results and answer every download URL with HTML.
Separately, a download SABnzbd gives up on leaves the queue without ever creating a
folder; `sab_failed()` now reads that from SAB's history and fails the job with SAB's own
message instead of leaving it on `downloading` forever.*

**Erststart-Reihenfolge** (Full-Stack): Stack hochfahren → in SABnzbd & Prowlarr
je einen API-Key erzeugen und Indexer/Server einrichten → Keys in `.env` →
`docker compose up -d` erneut → Romseerr im Browser öffnen und Admin anlegen.

## Benutzerverwaltung

Session-basiert (signierte Cookies, Secret in `/config/secret.key`). Beim ersten
Aufruf ohne Benutzer erscheint die **Ersteinrichtung** (Admin anlegen). Rollen:
`admin` (darf Benutzer verwalten, freigeben, Einstellungen ändern) und `user`. Alle
Routen außer Login/Setup/Health sind geschützt; gelöschte Benutzer verlieren sofort
den Zugriff.

**Freigabe-Workflow:** Jeder Benutzer hat ein Flag *Auto-Freigabe*. Anfragen von
Nutzern ohne Auto-Freigabe landen als `pending` und müssen vom Admin unter „Anfragen"
freigegeben (oder abgelehnt) werden; Admins und Auto-Freigabe-Nutzer laden sofort.

**Benachrichtigungen** sind in den Einstellungen konfigurierbar (Discord-Webhook,
mit Test) und melden neue Anfragen sowie Verfügbarkeit; Fallback über `DISCORD_WEBHOOK`.

## Persistenz

Alles unter `CONFIG_DIR` (Default `/config`):

- **`romseerr.db` (SQLite):** Tabelle `library` (Dedup-Index), `meta`, `users`, `jobs`.
  Der Bibliotheks-Index wird beim Start **aus der DB geladen** (~1 s) statt das Dateisystem
  zu durchlaufen (~24 s); im Hintergrund frischt er auf. Bestehende `users.json`/`jobs.json`
  werden beim ersten Start **verlustfrei migriert** (danach als `.migrated` gesichert).
- **JSON-Dateien** (klein, menschenlesbar, bewusst nicht in der DB): `settings.json`,
  `issues.json`, `maillog.json`, `push_subs.json`, sowie `secret.key` und `vapid.json`.

Die ROM-Bibliothek selbst liegt unter `ROMS` (Default `/roms/<plattform>/…`).

---

## Code-Rundgang / Code tour (`app.py`)

Die App braucht **keinen Build-Schritt**: `app.py` ist das Flask-Backend, das Frontend liegt
daneben in `templates/*.html` und `static/{css,js}/` und wird unverändert ausgeliefert. Ganz
oben in `app.py` steht ein ausführliches Modul-Docstring; die Abschnitte in Lesereihenfolge:

```
app.py            Backend (Routen, Worker, DB, OpenAPI)
templates/        index.html · login.html · reset.html · redoc.html
static/css/       index.css · login.css · reset.css · redoc.css
static/js/        index.js (die gesamte App-Oberfläche) · login.js · reset.js · sw.js
static/icon.svg   App-Icon (PWA)
```

| Abschnitt | Inhalt |
|---|---|
| Konfiguration | Env-Variablen, Pfade (`CONFIG_DIR`/`ROMS`, per Env überschreibbar) |
| Plattform-Zuordnung | Endung/Kategorie → Plattform-Slug; `SKIP_FILES` (Beifang) |
| Normalisierung/Index | `norm()` (Dedup-Schlüssel), `LIB` (RAM-Index) |
| SQLite | `db_conn`/`db_init`, Index laden/speichern, `users`/`jobs`, JSON-Migration |
| IGDB | Cover, Beschreibungen, „beliebt je Konsole/Genre" (`discover_rows`) |
| Suche | `do_search`: Archive.org + Prowlarr/Usenet, Nachfilter, Gruppierung |
| Jobs | Zustandsmaschine (`pending→queued→downloading→importing→done`/`error`) |
| Download/Import/Worker | `worker_download` (Queue) · `import_folder` (entpacken/dedup/einsortieren) · `worker_collect` (fertige Downloads einsammeln) |
| Auth | `_guard` (Schleuse), `*_required`-Decorators, `has_perm` (granulare Rechte) |
| Web-Push | VAPID-Schlüssel, Abos, Versand |
| Web-UI | `load_assets`/`asset_url`/`render_page` — Vorlagen lesen, `__ASSET:…__` durch inhaltsgehashte URLs ersetzen; die Oberfläche selbst liegt in `static/js/index.js` (i18n via `I18N`+`t()`) |
| Routen | REST-Endpunkte (vollständig dokumentiert unter `/api/docs`) |
| OpenAPI | `OPENAPI`-Dict → `/api/openapi.json` + `/api/docs` (Redoc) |
| Start | Index laden, Worker-Threads starten, Flask starten |

### Lebenszyklus einer Anfrage / request lifecycle
1. Browser/`/api/search` → `do_search` fragt Quellen ab, markiert `in_library`.
2. `POST /api/download` prüft Sperrliste, Dedup und Kontingent, legt via `new_job` einen Job an
   (`queued` bei Auto-Freigabe, sonst `pending`).
3. `worker_download` startet den Download (SAB/aria2/JDownloader).
4. `worker_collect` erkennt den fertigen Ordner → `import_folder` entpackt, dedupliziert und
   sortiert nach `ROMS/<slug>/` ein, baut den Index neu und **benachrichtigt** (Job → `done`).
   Erkennt der Import **nichts**, gibt er `False` zurück, der Job geht auf `error` und der
   Download **bleibt liegen** (#240).

### Der Import muss zwei Dinge aushalten (#240, #241, #242)

**Downloadprogramme benennen fertige Dateien um.** SABnzbds *deobfuscate final filenames*
rät den Typ aus dem Inhalt und hängt eine zweite Endung an: aus `spiel.nsp` wird
`spiel.nsp.hdf`. ROM-Formate kennt so ein Rater nicht, deshalb trifft es genau die Dateien,
um die es hier geht — im Log einer laufenden Anlage entstanden so `.hdf`, `.sndr`, `.sfv`.
`rom_endung()` nimmt deshalb die vorletzte Endung, wenn die letzte unbekannt und die
vorletzte eine bekannte ROM-Endung ist, und **kürzt den Namen beim Kopieren** — sonst
liegt in der Bibliothek ein Name, den kein Emulator öffnet. Nur eine Ebene tief:
`spiel.nsp.hdf` ja, `spiel.foo.bar` nein.

**Ein fehlgeschlagener Import darf nichts wegwerfen.** Vorher räumten Erfolgs- und
Fehlerweg identisch auf: `import_folder` kehrte auch bei „nichts erkannt" normal zurück,
und `worker_collect` löschte anschließend den Ordner *und* — über `sab_cleanup` mit
`del_files=1` — den History-Eintrag des Downloadprogramms. Knapp zwei Gigabyte waren weg,
und was in dem Paket lag, ließ sich hinterher nur noch aus der NZB und dem Log von SABnzbd
rekonstruieren. Jetzt entscheidet der Rückgabewert: nur nach einem geglückten Import wird
aufgeräumt. Was liegen bleibt, kann angesehen und nach einer Korrektur erneut eingelesen
werden — dafür muss der Ordner **von Hand** entfernt werden, wenn er nicht mehr gebraucht
wird.

Dazu nennt die Fehlermeldung jetzt **Endungen und eine Beispieldatei** statt nur einer
Zahl (#242). „1 übersprungen" hat eine vollständige Diagnoserunde gekostet, weil der
Ordner zu dem Zeitpunkt schon gelöscht war.

**Was liegen bleibt, muss sichtbar sein** (#244). Die Ordner stehen unter
*Einstellungen → Logs & Wartung* mit Titel, Größe, Alter und Zustand des Auftrags; einzeln
oder gesammelt entfernbar, und `leftover_days` (Standard 14, `0` = aus) lässt sie nach
einer Frist von selbst verfallen. Die Frist muss lang genug sein, dass eine Korrektur und
ein erneutes Einlesen hineinpassen — sonst räumt die Automatik genau das weg, wofür die
Daten aufgehoben wurden.

Zwei Sperren sitzen bewusst tief im Code, nicht in der Oberfläche: `leftover_dirs()` zeigt
Ordner **laufender** Aufträge gar nicht erst an (Alter allein wäre untauglich — ein großer
Download kann Stunden brauchen und sieht dabei alt aus), und `leftover_remove()` löscht
nur, was nach Auflösung aller Symlinks unterhalb eines Sammelordners liegt **und** das
`romseerr_`-Präfix trägt. `rm -rf` auf einem Pfad aus einer Einstellung ist die eine Stelle
hier, an der ein Denkfehler nicht rückgängig zu machen ist.

*EN: the import has to survive two things. Download clients rename finished files —
SABnzbd's deobfuscation appends a second extension it guessed from content, turning
`game.nsp` into `game.nsp.hdf`, and ROM formats are exactly what such a guesser does not
know. `rom_endung()` falls back to the second-to-last extension when the last one is
unknown, and trims the bogus suffix when copying. And a failed import must not destroy the
payload: cleanup now happens only when the import actually took something, because
previously both paths cleaned up identically and a 2 GB download was deleted along with
the client's history entry (`del_files=1`), leaving nothing to diagnose. Leftover folders
are listed under Settings → Logs & maintenance with size, age and owning request, can be
removed individually or in bulk, and expire after `leftover_days` (default 14, 0 = off).
Two guards live in the code rather than the UI: folders belonging to a **running** job are
never listed, and removal only accepts paths that resolve inside a collect directory and
carry the `romseerr_` prefix.*

### Etwas an der Oberfläche ändern
Datei unter `static/` oder `templates/` bearbeiten, App neu starten (der Hash und damit die
URL ändern sich automatisch). Kein Build, kein Bündler.

### Eine neue Route hinzufügen
1. Funktion mit `@app.route(...)` + passendem `*_required`-Decorator schreiben.
2. Falls öffentlich: Pfad in die `PUBLIC`-Menge aufnehmen.
3. Endpunkt im `OPENAPI`-Dict dokumentieren (sonst schlägt `test_openapi_covers_all_routes` fehl).
4. `python scripts/build_openapi.py` ausführen (aktualisiert `docs/openapi.yaml`).
5. Wenn möglich einen Smoke-Test in `tests/` ergänzen.

### Fallstricke / gotchas
- **Frontend gehört NICHT in `app.py`.** Der Test `test_no_frontend_left_in_python` schlägt an,
  sobald wieder HTML/CSS/JS in einem Python-String landet. (Die frühere Falle — Python
  interpretierte die Backslash-Escapes des eingebetteten JS, `join('\\n')` wurde zum echten
  Umbruch und legte das ganze Skript lahm — kann in echten `.js`-Dateien nicht mehr auftreten.)
- **Statische Dateien** werden unter `/assets/<inhaltshash>/<pfad>` mit
  `Cache-Control: immutable` ausgeliefert. In der Vorlage steht `__ASSET:js/index.js__`; die
  URL entsteht beim Rendern. Neue Dateien einfach unter `static/` ablegen — `load_assets()`
  liest beim Start alles ein. **Beide Verzeichnisse müssen ins Image** (`Dockerfile`).
- **SQLite-Verbindungen** immer via `contextlib.closing` schließen (sonst FD-Leck pro Request).
- **Deployment:** ein neues Image erfordert `docker rm`+`run` — `docker restart` lädt kein neues Image.
- **Web-Push** funktioniert im Browser nur über **HTTPS** (oder localhost).

Vollständige Details: Modul-Docstring in `app.py`, API unter `/api/docs`, Mitwirken in
[`.github/CONTRIBUTING.md`](../.github/CONTRIBUTING.md).
