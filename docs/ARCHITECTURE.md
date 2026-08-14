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

### Zweiter Weg hinein: der Einwurfordner

Nicht alles kommt über eine Anfrage. Wer eine ganze Sammlung hat, legt sie in
`IMPORT_SHARE` (im Container `/import`); ein eigener Thread (`periodic_einwurf`, Takt
`IMPORT_SCAN_SEC`, Vorgabe 300 s) sieht nach und sortiert ein. Die Oberfläche zeigt und
löst denselben Lauf unter Einstellungen → Einwurf aus, die API über
`/api/import/status` (Trockenlauf) und `/api/import/scan`.

Drei Eigenschaften, die den Unterschied zu einem simplen „verschiebe alles" ausmachen:

- **Ruhe vor dem Anfassen.** `einwurf_stabil` merkt sich Größe und Änderungszeit und lässt
  eine Datei erst nach **zwei** gleichen Durchgängen zu. Über SMB dauert eine 5-GB-Kopie
  Minuten; ohne diese Bedingung läge ein halb kopiertes Abbild als Titel in der Bibliothek
  und startete nie.
- **Verschieben über Dateisystemgrenzen.** Einwurfordner und Bibliothek liegen in der
  Regel auf verschiedenen Speichern, `os.rename` scheitert dort. Deshalb: nach `.teil`
  kopieren → Größe vergleichen → `os.replace` → Quelle löschen. Ein Abbruch hinterlässt
  eine `.teil`-Datei, nie eine halbe ROM. Scheitert nur das **Löschen**, gilt der Import
  trotzdem als erfolgreich — der Titel ist angekommen, und das Protokoll nennt den Grund.
- **Nichts raten.** Wo eine Datei sich keiner Plattform zuordnen lässt, wandert sie nach
  `.unsortiert` und steht mit Grund im Bericht. 25 der 82 anerkannten Endungen sind
  mehrdeutig; ein Download bringt seinen Plattform-Hinweis aus der Anfrage mit, eine
  hineingelegte Datei bringt nichts mit. Der Ordnername darf entscheiden, wo die Endung es
  nicht kann.

*A second way in: a watched drop folder, scanned on its own thread every 5 minutes and on
demand. A file is only touched after size and mtime stayed equal across two passes; moves
are copy → verify → replace → delete because the two sides are different filesystems; and
anything unclassifiable goes to `.unsortiert` with a reason rather than being guessed at.*

> **Wer RomM unter Unraid betreibt: die Vorlage ist die Wahrheit, nicht der laufende
> Container.** Alles, was am laufenden Container gesetzt wird und nicht in der
> Docker-Vorlage steht, ist beim nächsten Neuanlegen weg — und zwar lautlos. Das hat hier
> zweimal zugeschlagen: erst bei den Metadaten-Schlüsseln, dann bei `SCAN_TIMEOUT` (#317).
>
> Besonders unangenehm ist genau dieser Wert: Die Vorgabe liegt unter 24 Stunden, ein
> vollständiger Scan einer großen Bibliothek dauert länger — und **ein Scan, der ins
> Zeitlimit läuft, sieht aus wie einer, der fertig ist.** RomM meldet keinen Abschluss,
> es hört nur auf zu arbeiten.
>
> *On Unraid the template is the truth, not the running container: anything set past it is
> gone at the next recreate, silently. A scan that hits its timeout looks exactly like a
> scan that finished.*

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
ohne sie wird der Ordner nie gelesen.

`jd_check()` merkt davon nichts: seine drei Prüfungen liegen alle auf **unserer** Seite —
Ordner da, beschreibbar, Ziel da — und melden zutreffend `ok`, während auf der anderen
Seite niemand zuhört. Genau so gemessen: korrekte Aufträge in einem korrekt eingehängten
Verzeichnis, 120 Sekunden unverändert, in JDownloader keine einzige
`folderwatch`-Zeile. Deshalb gibt es `jd_probe()` (#218): eine wirkungslose `.crawljob`
(`enabled`/`autoStart`/`autoConfirm` alle `FALSE`, Ziel `example.invalid`) wird abgelegt,
und wenn sie binnen der Wartezeit verschwindet, liest jemand mit — `not_consumed` ist ein
eigener Grund mit eigener Abhilfe.

**Was die Sonde nicht beweist:** dass ein Auftrag danach auch *läuft*. Steht auf der
JD-Seite ein modaler Dialog offen, wird die Datei eingelesen und der Auftrag bleibt
trotzdem liegen — die Sonde sähe das als Erfolg. Sie beantwortet „hört jemand zu", nicht
„geschieht etwas"; für Zweiteres bräuchte es die My.JDownloader-API, die hier bewusst
nicht vorausgesetzt wird. Sie läuft nur auf Anforderung (*Einstellungen → Verbindungen →
JDownloader*), weil sie Sekunden kostet und einen deaktivierten Eintrag im Linksammler
hinterlässt.

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

#### Wessen Plattform gilt: Kategorie oder Titel? (#452)

Ein Usenet-Treffer trägt zwei Aussagen über seine Plattform — die **Kategorie** des
Indexers und den **Titel**. Die Kategorie gilt, denn sie ist gepflegt; der Titel ist
Fließtext. Nur: nicht jede Plattform bekommt eine eigene Kategorie. Zwei fahren beim
hiesigen Indexer in der des Nachbarn mit, und dort ist die Kategorie nachweislich zu grob:

| Plattform | Kategorie | Kategorie sagt | Titel sagt |
|---|---|---|---|
| PS Vita | `101020` | `psp` | `psvita` |
| Wii U | `101030`, `101060` | `wii` | `wiiu` |

Beides steht in **einer** Tabelle, `KAT_LEIHE` (Mieter → Eigentümer), und sie hat zwei
Wirkungen. Erstens erbt der Mieter die Kategorien des Eigentümers — ohne das ist seine
Kategorienliste leer, und `search_usenet` steigt bei `not cats` sofort aus: Die Auswahl
dieser Plattform **schaltet die Usenet-Suche ab**, lautlos, ohne Fehler. Zweitens darf der
Mieter seine Kategorie am Titel zurückerobern: Nennt der Titel eine Plattform, die genau
in der gefundenen Kategorie mitfährt, gewinnt der Titel (`plattform_aus_kategorie_und_titel`).

Die Erlaubnis ist bewusst eng. Titel erwähnen ständig fremde Systeme („PS2 Classics",
„Dreamcast Port"); dürfte jeder Titeltreffer die Kategorie schlagen, wäre die Zuordnung
schlechter als vorher. Sie gilt nur für den eingetragenen Mieter und nur für dessen eigene
Kategorie. Gemessen vor der Änderung: **16 von 16** Treffern kamen unter dem Slug des
Eigentümers zurück — ein Vita-Download landete im PSP-Ordner, und die Wii-U-Treffer aus
#375 waren zwar auffindbar, fielen aber aus dem Wii-U-Filter, weil sie `wii` hießen.

*EN: a usenet hit states its platform twice — indexer category and title. The category
wins, because it is curated. But not every platform gets its own category: PS Vita rides
in the PSP category, Wii U in the Wii ones. `KAT_LEIHE` (tenant → owner of the category)
records both facts and does two things. The tenant inherits the owner's categories —
without that its category list is empty and `search_usenet` bails out at `not cats`,
silently disabling usenet search for that platform. And the tenant may reclaim its own
category from the title: if the title names a platform that is a documented tenant of
exactly the category found, the title wins. Deliberately narrow — a title merely
mentioning some foreign platform must not reclassify anything, or the result would be
worse than before. Measured before the change: 16 of 16 hits carried the owner's slug.*

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

### Wenn ein Titel auf mehreren Plattformen liegt (#175)

`stream_info` raet nicht: denselben Titel gibt es fuer PS2 und Wii, und das PS2-Abbild zu
starten, wenn die Wii-Fassung gemeint war, ist genau die stille Fehlentscheidung, die
dieses Projekt vermeidet. Die Absage `ambiguous_platform` traegt jetzt aber die
**Kandidatenliste** — der Resolver kennt sie ohnehin —, und die Oberflaeche macht daraus
eine Auswahl statt einer Sackgasse. Das ist der einzige Absagegrund, den der Bedienende
aufloesen kann; bei allen anderen (kein Emulator, keine Firmware, Platz belegt) ist die
fehlende Information auf der Hostseite.

Damit ein neuer Grund nicht wieder stumm im allgemeinen Satz verschwindet, gibt es in der
Oberflaeche die Tabelle `STREAM_GRUND`, und ein Test vergleicht sie mit den Gruenden, die
`stream_info` tatsaechlich erzeugt — samt der Frage, ob der zugehoerige Text in allen fuenf
Sprachen existiert.

*EN: `stream_info` still refuses to guess between platforms, but `ambiguous_platform` now
carries the candidate list, so the panel offers a choice instead of a dead end — this is
the one refusal the operator can resolve. A test keeps the reason codes the server emits
and the UI's `STREAM_GRUND` table in step, in all five languages.*

### Welche Plattformen im Browser laufen (#124)

`PLAYABLE` ordnet jedem Slug einen EmulatorJS-Kern zu. Entscheidend ist, woher der
Kernname kommt: **aus dem eingesetzten RomM-Bau, nicht aus dem libretro-Katalog.** Der
Unterschied ist keine Förmlichkeit — `freeintv` (Intellivision) steht im Katalog und
fehlt im Player, der Eintrag war ein Play-Knopf, der nicht funktionieren konnte und von
außen aussah wie jeder andere. `GET /api/play/cores` prüft das jetzt je Plattform per
HEAD gegen den laufenden Player.

Ordner, die keine Plattform sind, stehen in `IGNORE_FOLDERS` — aber nur, wenn sie
**keinen Spielinhalt** haben. Das ist der feine Unterschied zu „Inhalt ohne Kern": ein
Emulator-Verzeichnis darf verschwinden, `LCD Handhelds` (`.mgw`-Dateien) und `RG350`
(`.opk`-Pakete) dürfen es nicht — dort fehlt nur der Kern, und sie zu verstecken hieße,
eine Lücke als Ordnung auszugeben.

*EN: `PLAYABLE` maps slugs to EmulatorJS cores, and the names must come from the deployed
RomM build rather than libretro's catalogue — one entry pointed at a core the player does
not ship, which cannot work and looks like any other button. `GET /api/play/cores` now
checks each one. `IGNORE_FOLDERS` hides directories with no game content; content that
merely lacks a core stays visible.*

### Den RomM-Scan gibt es nicht als REST-Aufruf (#520)

`POST /api/scan` ist **weg**. Wer es trotzdem aufruft, bekommt zwei Absagen
hintereinander — und `requests` wirft bei keiner davon:

```
POST /api/login  -> 200
POST /api/scan   -> 403  "CSRF token verification failed"
   (mit korrektem CSRF-Kopf)  -> 404  {"detail":"Not Found"}
```

Der Scan ist ein **Socket.IO-Ereignis**, eingehängt unter `/ws`. Die Aufgabe
`scan_library` trägt `manual_run: false`, `POST /api/tasks/run/scan_library` scheitert
also mit 400.

**Ohne neue Abhängigkeit:** Socket.IO spricht auch reines HTTP. `GET` holt das
OPEN-Paket mit der Sitzungskennung, ein `POST "40"` meldet den Namensraum an, und das
Ereignis ist ein `POST "42[\"scan\", {…}]"`. Damit genügt `requests`; ein
`websockets`- oder `python-socketio`-Paket wäre eine neue Abhängigkeit für einen Aufruf,
der einmal je Import passiert.

**Zwei Dinge, die man leicht falsch macht:**

- **CSRF gilt für REST, nicht für den Socket** — und das Merkmal ist an die
  Benutzerkennung gebunden. Erst anmelden, dann einen beliebigen GET, *dann* liegt ein
  brauchbares `romm_csrftoken` vor. Eines von vor der Anmeldung gehört „niemandem" und
  wird abgewiesen.
- **`platform_fs_slugs` sind ORDNERNAMEN, keine Slugs.** `dreamcast` liegt in `dc`,
  `ngc` in `gc`. Ungerechnet läuft der Scan ins Leere und meldet trotzdem Erfolg.

**Und die eigentliche Lehre:** Jeder Schritt prüft seinen Statuscode, und eine Absage
(`scan:done_ko`) wird gelesen. Die alte Fassung stand in einem `except Exception`, das
nie betreten wurde — der Aufruf kehrte zurück, sah erfolgreich aus und tat nichts. Das
ist der dritte Fehler dieser Bauart an einem Tag (#500, #513).

*EN: there is no REST endpoint for the scan any more — 403 then 404, and requests raises
on neither. It is a Socket.IO event under `/ws`, reachable over plain HTTP polling, so no
new dependency. CSRF applies to REST only and its token is bound to the user id, so it
must be fetched after logging in. `platform_fs_slugs` are folder names, not slugs. Every
step now checks its status code and a refusal is read, because the previous version
returned, looked successful and did nothing.*

### Ein Alias ist erst richtig, wenn RomM ihn auch zieht (#518)

`FOLDER_ALIASES` fasst Ordner zusammen, die dieselbe Plattform meinen — `neogeoaes` und
`neogeomvs` sind dieselbe Hardware in anderen Gehäusen, und sie zeigen beide auf `neogeo`.
`neo-geo-cd` zeigte ebenfalls dorthin, und das war falsch.

**Nicht wegen der Konsolengeschichte, sondern weil RomM sie trennt:**

```
RomM:  Neo Geo AES   neogeoaes    300 ROMs
       Neo Geo CD    neo-geo-cd   100 ROMs
       eine Plattform `neogeo` gibt es dort GAR NICHT
```

`play_info` fragt nicht den eigenen Index, sondern `romm_find()`. Mit dem Alias fragte es
nach einer Plattform, die RomM nicht kennt:

```
romm_find("Aero Fighters 2 (World)", "neogeo")      -> None
romm_find("Aero Fighters 2 (World)", "neo-geo-cd")  -> Aero Fighters 2
```

100 vorhandene, von RomM gescannte Titel waren damit unspielbar — und der Play-Knopf
konnte gar nicht erst erscheinen, ohne dass irgendwo etwas rot wurde.

**Die Regel:** Ein Alias darf nur zusammenfassen, was RomM ebenfalls zusammenfasst. Wo die
beiden auseinandergehen, gewinnt RomM — es hält die Daten, an denen `play_info` hängt.

Dazu gehören drei Kleinigkeiten, die sonst nachziehen müssen: der Kern (`fbneo`, derselbe
wie für Neo Geo), der **BIOS-Hinweis** (ein CD-Abbild braucht das System-ROM, ein
Cartridge-Romset nicht) und die Reihenfolge in `KW` — `neo\s*geo` passt auch auf
`Neo Geo CD`, das genauere Muster muss davor stehen.

*EN: `FOLDER_ALIASES` may only merge what RomM merges. It kept `neo-geo-cd` under
`neogeo`, but RomM has no `neogeo` platform at all — so `play_info`, which asks
`romm_find()` rather than the local index, found nothing for 100 present and scanned
titles, and the play button simply never appeared. Where the two disagree, RomM wins: it
holds the data play depends on. Three things follow — the core, the BIOS note (a CD image
needs the system ROM, a cartridge romset does not), and the order in `KW`, where the
narrower pattern must precede the general one.*

### Beide Seiten müssen dieselbe Frage stellen (#427, #502, #512)

Ob ein Titel startbar ist, beantworten **zwei** Stellen: `stream_info` in Romseerr, bevor
der Knopf erscheint, und der Start-Dienst, bevor er einen Prozess startet. Das ist
Absicht, keine Doppelarbeit — ein direkter Aufruf des Dienstes umgeht Romseerr, und wer
nur dort prüft, hat eine Zusage, die vom gewählten Weg abhängt.

Fragt umgekehrt nur der Dienst, bekommt der Nutzer den Knopf, **belegt einen Platz** und
liest die Absage erst danach. Genau so lag es bei Wii U: Der Dienst lehnte ein Update
seit #502 ab, Romseerr bot es weiter an.

| Plattform | Woran erkannt | Quelle |
|---|---|---|
| 3DS | Titel-ID `0004000E` / `0004008C` | TMD in der `.cia` |
| Switch | letzte drei Stellen der Titel-ID | `<rights-id>.tik` in der NSP |
| Wii U | Titel-ID `0005000E` / `0005000C` / `0005001B` | `code/app.xml` |

Bei Wii U ausdrücklich `code/app.xml` und **nicht** `meta/meta.xml`: Die beiden können
sich widersprechen, und beim einzigen Wii-U-Titel des Bestands tun sie es —
`meta.xml` behauptet `00050000…` (Spiel), `app.xml` sagt `0005000E…` (Update). Cemu liest
`app.xml`. Wer die andere Datei nimmt, bekommt mit voller Überzeugung die falsche Antwort.

**Überall gilt: im Zweifel durchlassen.** Was sich nicht eindeutig als Zubehör ausweist,
bleibt startbar. Eine falsche Absage nimmt einen vorhandenen Titel dauerhaft aus dem
Angebot, und danach sucht niemand mehr.

#### Ein Grund ohne Text ist keine Auskunft

Die Kette hat drei Glieder: `app.py` liefert einen Code, `STREAM_GRUND` in `index.js`
bildet ihn auf einen Schlüssel ab, die Sprachdateien tragen den Satz. Reißt das mittlere
Glied, fällt der Code stumm in „Streamen gerade nicht möglich" — der Satz existiert, ist
aber unerreichbar.

Genau das war seit #427 der Fall: `stream_nsp_update` und `stream_nsp_dlc` lagen in
**allen fünf Sprachen** bereit und fehlten nur in `STREAM_GRUND`. Der Test dagegen sammelte
nur Codes, die als **wörtlicher String** in `stream_info` stehen — und alle
Plattformprüfungen liefern ihren Grund über eine Hilfsfunktion, als Variable. Er meldete
also Erfolg für etwas, das er nicht prüfte (#513). Gesammelt wird jetzt zusätzlich aus den
`*_startbar`-Funktionen und ihren `_*_ZUBEHOER`-Tabellen.

*EN: two places answer "is this startable" — Romseerr before the button appears and the
launch service before it starts a process. Deliberately both: calling the service directly
bypasses Romseerr, and checking only there means the user takes a seat before reading the
refusal. Wii U reads `code/app.xml`, not `meta/meta.xml`, because the two can disagree and
here they do. Everywhere: when in doubt, let it through — a wrong refusal removes a title
that exists. The reason travels through three links (code → `STREAM_GRUND` → translations);
when the middle one is missing the code falls silently into the generic sentence, which is
what happened to the Switch texts, and the test that should have caught it only saw reasons
spelled out literally rather than those returned through a helper.*

## Benutzerverwaltung

Session-basiert (signierte Cookies, Secret in `/config/secret.key`). Beim ersten
Aufruf ohne Benutzer erscheint die **Ersteinrichtung** (Admin anlegen). Rollen:
`admin` (darf Benutzer verwalten, freigeben, Einstellungen ändern) und `user`. Alle
Routen außer Login/Setup/Health sind geschützt; gelöschte Benutzer verlieren sofort
den Zugriff.

**Es muss immer ein Admin mit Passwort übrig bleiben** (#234). `save_users()` ist ein
**Ersetzer**: es leert die Tabelle und schreibt das übergebene Dict als Gesamtbestand.
Die Bedingung stand deshalb lange an genau einer Stelle richtig — im Import — und an
keiner anderen; über Benutzerverwaltung, Rechteformular oder einen Wartungsaufruf war
eine Instanz erreichbar, in die niemand mehr hineinkommt und die sich nicht mehr
reparieren lässt. Die Prüfung sitzt jetzt in `save_users()` selbst und wirft
`KeinAdminMehr`; HTTP-Handler machen daraus über `speichere_nutzer_http()` eine **400**,
damit aus einer Sperre kein Serverfehler wird.

Eine **leere** Liste bleibt erlaubt — dann greift die Ersteinrichtung, und das sperrt
niemanden aus. Verboten ist der Zustand dazwischen: Konten vorhanden, aber keines mit
Zugang.

Zusätzlich protokolliert jede **Verkleinerung** der Benutzerliste ihre Zahlen. Die
Invariante verhindert das Aussperren, nicht das versehentliche Überschreiben mit einem
gültigen, aber falschen Bestand — genau so gingen hier schon einmal zwei echte Konten
verloren, und ein solcher Vorfall soll wenigstens nachweisbar sein.

**Freigabe-Workflow:** Jeder Benutzer hat ein Flag *Auto-Freigabe*. Anfragen von
Nutzern ohne Auto-Freigabe landen als `pending` und müssen vom Admin unter „Anfragen"
freigegeben (oder abgelehnt) werden; Admins und Auto-Freigabe-Nutzer laden sofort.

**Benachrichtigungen** sind in den Einstellungen konfigurierbar (Discord-Webhook,
mit Test) und melden neue Anfragen sowie Verfügbarkeit; Fallback über `DISCORD_WEBHOOK`.

## Persistenz

Alles unter `CONFIG_DIR` (Default `/config`):

- **`romseerr.db` (SQLite)** — der Normalfall. Tabellen: `library` (Dedup-Index), `meta`,
  `users`, `jobs`, `kv` (Einstellungen, Probleme, Mail-Protokoll, Push-Abos, Favoriten,
  Bewertungen, Wunschlisten, Abdeckung, Sitzung), `catalog` und `fh_items` (Kataloge),
  `messages`, `ra_games`. Der Bibliotheks-Index wird beim Start **aus der DB geladen**
  (~1 s) statt das Dateisystem zu durchlaufen (~24 s).
  `users.json`, `jobs.json`, `settings.json`, `issues.json`, `maillog.json` und
  `push_subs.json` werden beim ersten Start **verlustfrei migriert** und danach als
  `.migrated` gesichert. Wo eine dieser Dateien nie existierte, gibt es auch keine
  `.migrated` — „keine Datei" ist also **kein** Beleg für eine Migration, sondern meist
  dafür, dass das Feature auf dieser Installation nie benutzt wurde.
- **Dateien, die bewusst Dateien bleiben** — jeweils mit Grund, nicht aus Versehen:
  `secret.key` (Sitzungssignatur) und `vapid.json` (privater Push-Schlüssel) gehören nicht
  in dieselbe Datei wie die Daten, die sie schützen: eine DB-Sicherung, ein Export oder
  eine Kopie zum Nachsehen nähme sie sonst mit. `tls/` (Zertifikat und Schlüssel) aus
  demselben Grund, `logos/` weil Bilddateien nicht in eine Spalte gehören.
  Alles Schlüsselmaterial entsteht über `schreibe_geheim()` mit **0600**; ältere Bestände
  zieht `geheimnisse_absichern()` **beim Start** nach — gemessen lagen `secret.key` und
  `vapid.json` bei `0664`. Beim Start und nicht erst beim Lesen, weil `vapid.json` nur
  angefasst wird, wenn Web-Push tatsächlich benutzt wird: sonst behielte ausgerechnet der
  Schlüssel die offenen Rechte, den niemand anfasst. (#256)

**Eine leere Tabelle ist nicht automatisch ein Fehler**, aber auch kein Beweis für
Absicht — von außen sieht ein ungenutztes Feature aus wie ein stehengebliebener Schreiber.
Nachgemessen: `catalog` füllt sich ausschließlich über *Abdeckung → Katalog aktualisieren*
(kein Timer), `ra_games` bleibt ohne RetroAchievements-Schlüssel leer, `messages` ist ein
reines Nutzerfeature. Was tatsächlich läuft, schreibt auch: `fh_items` trug bei der Messung
650 Einträge.

*EN: SQLite is the default; six former JSON stores are migrated on first start, and a
missing file usually means the feature was never used here rather than that it moved. Key
material stays in files on purpose — a database backup or export would otherwise carry the
keys that protect it — and is written with 0600, with older permissions corrected on read.
An empty table is not proof of a fault, but not proof of intent either: `catalog` only
fills on an explicit refresh, `ra_games` needs a key that is not set, `messages` is a user
feature.*

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

### Ein Ordnername, zwei Namensgeber (#454)

RetroNAS und Romseerr nennen dieselbe Plattform verschieden: `gc` gegen `ngc`, `dc` gegen
`dreamcast`. `FOLDER_ALIASES` bildet das ab, und **Lesen** benutzt es überall —
`slug_folders()` liefert alle beitragenden Ordner, `STREAM_DIR` baut darauf auf, der Index
ordnet `gc`-Dateien dem Slug `ngc` zu.

**Schreiben tat es nicht.** Das Importziel war schlicht `ROMS/<slug>`, an zwei Stellen.
Liegt die Bibliothek im Alias-Ordner, landete jeder Download also *daneben* statt *darin*:

```
roms/gc          713 Dateien  561 GB   <- die Bibliothek
roms/ngc           0 Dateien           <- wohin Importe gingen
```

Das Tückische daran ist die **Unsichtbarkeit**: Das Lesen fügt beide Ordner wieder
zusammen, in Romseerr sah alles vollständig aus. Auf der Platte war die Plattform trotzdem
zweigeteilt, und alles, was die Ordner direkt liest — RomMs Scan, RetroNAS' Freigaben, ein
blankes `ls` — sah nur eine Hälfte. Eine Messung ist daran schon gescheitert: „diese
Plattformen haben keinen Inhalt", während GameCube und Dreamcast durchgehend gefüllt waren.

`bibliothek_ordner(slug)` nimmt jetzt den Ordner, in dem die Plattform **schon liegt**, und
fällt sonst auf den Slug zurück. Ein *leerer* Alias-Ordner zählt dabei nicht — sonst gewänne
der Streuner gegen die Bibliothek, und genau so herum lagen `ngc` und `dreamcast` auf der
Anlage. Die Reihenfolge kommt aus `slug_folders` und damit aus der konstanten Tabelle, nie
aus der Eingabe.

*EN: RetroNAS and Romseerr name the same platform differently (`gc`/`ngc`, `dc`/`dreamcast`).
Reading resolved this everywhere; writing did not, so downloads landed beside the library
instead of inside it. The split was invisible, because reading merges both folders again —
only something reading the directories directly (RomM's scan, RetroNAS' shares, a plain
`ls`) sees one half. `bibliothek_ordner(slug)` now prefers the folder that already holds
the platform and falls back to the slug. An empty alias folder does not count, or the stray
would beat the library.*

### Der Index muss dasselbe wissen wie der Import (#477)

`SPIELORDNER_MUSTER` sagt dem **Import**, dass ein Ordner ein Titel sein kann. Der **Index**
wusste es nicht: Er lief hinein und legte die Bestandteile als Titel ab. Nach einem
vollständigen Neuaufbau am echten Bestand gemessen:

```
wiiu    31 Einträge:  app, bootDrcTex, bootLogoTex, bootMovie
psvita  14 Einträge:  args, eboot, Gravite, icon
ps3     27 Einträge:  PS3_DISC, ICON0, …
```

`bootMovie` ist ein Video **in** Captain Toad, `Gravite` die `.psarc` **in** Gravity Rush.
Die echten Titel fehlten ganz — und damit fand `stream_info` sie nicht: **ein vollständiger,
vorhandener Titel war über die Oberfläche unerreichbar.**

`ist_titel_ordner()` beantwortet die Frage jetzt für beide Wege:

| Weg | erkennt |
|---|---|
| `spielordner_slug` | bekannter Aufbau — Wii U, PS3, GameCube, Vita, Xbox |
| Abbild-Set | eine `.gdi`/`.cue`/`.m3u` nennt Dateien, die daneben liegen |

**Warum zwei Wege und nicht einer:** `spielordner_slug` liefert einen *Slug*, und ein
Abbild-Set verrät seine Plattform nicht — eine `.cue` steht bei psx, saturn, segacd und
turbografx-cd. Für den Index ist die Plattform aber schon bekannt; dort lautet die Frage nur
„ein Titel oder viele?". Ohne den zweiten Weg hieße ein wiederhergestellter
Dreamcast-Titel `track01`, `track02`, `track03`.

**Die Tiefe bleibt bei zwei Ebenen.** Drei wurden gemessen: 32,6 s gegen 106,3 s für 7,6 %
mehr Dateien — das 3,3-fache für einen Lauf, der periodisch läuft. Titel, die tiefer liegen,
holt der Bibliotheksumbau auf Ebene 1; das ist seine Aufgabe, nicht die des Index.

*EN: the import path has known since #391 that a folder can be a title; the index did not,
so it walked in and filed game data as titles — a complete, present title was unreachable
through the UI. `ist_titel_ordner()` now answers for both a known layout and an image set.
Two routes rather than one because `spielordner_slug` returns a platform, which an image
set does not reveal — the index already knows the platform and only asks "one title or
many?". Depth stays at two levels: three costs 3.3x for 7.6% more files, and normalising
deeper trees is the library rebuild's job.*

### Zwei Wanderungen über denselben Baum laufen auseinander (#477)

Dass der Index Ordner-Titel kennt, war nur die halbe Miete. `stream_find_file()` lief eine
**zweite, eigene** Wanderung — und die hatte drei Fehler, jeden davon am Bestand gemessen:

| Fehler | gemessen |
|---|---|
| Ordner schlug **immer** die Datei | `Sonic Adventure (PAL)/` (nur eine `.url` + ein Unterordner) verdrängte `Sonic Adventure.cdi`, 757 MB, spielbar |
| nur Ebene 1 | `ps3/DmC … BLUS30723/Devil May Cry 5/` steht im Index, die Auskunft sagte `not_in_library` |
| `break` statt `dirs[:] = []` | beendete die **ganze** Wanderung am ersten verschachtelten Ordner: `dc` 64 von 173 Dateien gesehen, `psx` 2925 von 2993 |

Der erste ist der bösartigste, weil beide Seiten *scheinbar* funktionierten: Die Auskunft
meldete den Titel als streambar und nannte den Ordner — der Start-Dienst öffnete ihn und
antwortete `Ordner ohne startbaren Inhalt`, während das spielbare Abbild danebenlag.

**Was jetzt gewinnt, ist aber nicht die `.cdi`** (nachgemessen am laufenden Dienst, #501):
Eine Ebene tiefer liegt `[GDI] Sonic Adventure (PAL)/` mit einer `.gdi` und drei Spuren,
1,2 GB — ein echtes Abbild-Set und damit ein Titelordner. Der Ordnerzweig zieht es vor,
bevor die Dateisuche drankommt. Das ist richtig: Beides ist spielbar, und der leere
Elternordner ist weg. Nur die Erwartung „das Abbild gewinnt" war falsch.

**Die Regel dahinter:** Zwei Wanderungen über denselben Baum driften auseinander. Es gibt
jetzt **eine**, mit derselben Tiefe wie der Index, und der Ordnerzweig stellt dieselbe Frage
wie der Index — `ist_titel_ordner()`. Nur ein Ordner, der wirklich ein Titel *ist*, schlägt
ein spielbares Abbild.

**Die Ratsche gegen den Übereifer:** 39 Ordner im Bestand sind weder Titelaufbau noch
Abbild-Set und enthalten auch keinen — `gc/Pikmin (USA) (v1.00)` etwa trägt eine einzelne
`.rvz`, die der Start-Dienst selbst auflöst. Die kommen weiterhin zurück, aber als
**Rückfall**, erst nachdem keine Datei gepasst hat. Wer den Ordnerzweig strenger macht,
darf sie nicht verlieren.

*EN: the index knowing about folder titles was only half of it — `stream_find_file()` ran a
second, separate walk with three measured faults: a folder always outranked a file (an empty
`Sonic Adventure (PAL)/` beat a playable 757 MB `.cdi`), it only looked one level down, and
`break` ended the whole walk at the first nested folder instead of pruning that branch (`dc`
saw 64 of 173 files). The first is the worst kind, because both sides appeared to work: the
API called the title streamable and named the folder, and the launcher then reported "folder
with nothing bootable" while the image sat beside it. Two walks over one tree drift apart —
there is now one, at the index's depth, asking the index's question (`ist_titel_ordner()`).
A folder that is neither a title layout nor an image set is still returned, but only as a
fallback once no file matched: 39 such folders exist and must not be lost. Note what wins
in that first row is not the `.cdi` (#501): one level down sits `[GDI] Sonic Adventure
(PAL)/` with a `.gdi` and three tracks, 1.2 GB — a real image set, therefore a title folder,
therefore preferred. Both are playable and the empty parent is gone; only the expectation
"the image wins" was wrong.*

### Wenn ein Ordner EIN Spiel ist (#391, #455)

Für manche Plattformen ist ein Titel kein *File*, sondern ein *Ordner*. Der Import lief
ursprünglich über `os.walk` und kopierte jede Datei mit passender Endung einzeln — für
solche Plattformen in beide Richtungen falsch: Bruchstücke aus dem Spielinneren kamen in
die Bibliothek, der Titel selbst wurde verworfen.

`SPIELORDNER_MUSTER` erkennt sie **am Aufbau, nicht an der Dateizahl**. Ein entpacktes
Spiel hat Tausende Dateien, eine Sammlung auch; was sie unterscheidet, gibt das Format vor:

| Plattform | verlangte Einträge |
|---|---|
| Wii U | `code` + `content` + `meta` |
| PS3 | `ps3_game` (oder die Datei `ps3_disc.sfb`) |
| GameCube/Wii | `sys` + `files` |
| PS Vita | `eboot.bin` + `sce_sys` |
| Xbox | die Datei `default.xbe` |

Bei der Vita zählt das **Paar**. `eboot.bin` hat jeder Titel — allein darf sie die
Plattform nicht beanspruchen, sonst würde aus einem Bruchstück ein anerkannter Titel.
`sce_module` und `PSP2` liegen oft daneben, sind aber optional und stehen deshalb nicht in
der Bedingung. Gemessen an einem echten Import: Das Release liefert einen **Ordner**,
dessen Name auf `.vpk` endet; am Namen hängt die Erkennung bewusst nicht, denn andere
Releases liefern denselben Aufbau unter dem blanken Titel.

Ohne den Eintrag fällt der Import auf „jede Datei einzeln" zurück. Bei der Vita nahm er
dann genau die `eboot.bin` mit (`.bin` steht in `ROM_EXT`) — 10 MB ohne `param.sfo`, für
Vita3K unbrauchbar und für Menschen nicht identifizierbar. Und weil jeder Vita-Titel so
heißt, hätte der nächste Import den vorigen überschrieben.

*EN: for some platforms a title is a folder, not a file. `SPIELORDNER_MUSTER` recognises
them by their fixed layout rather than by file count — an unpacked game and a collection
both have thousands of files. For PS Vita the pair `eboot.bin` + `sce_sys` is required:
every Vita title has an `eboot.bin`, so on its own it must not claim the platform, or a
fragment would be promoted to a title. `sce_module` and `PSP2` are optional. Without the
entry the import falls back to copying files one by one and takes the `eboot.bin` alone —
unusable for Vita3K, unidentifiable for a human, and overwritten by the next import,
because every Vita title carries that same name.*

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

**Erneut versuchen heißt nicht: dasselbe noch einmal** (#200). `retry` setzte bisher nur
den Zustand zurück und stellte denselben Auftrag erneut ein — wer dreimal drückte, wartete
dreimal auf dieselbe Meldung. Der Auftrag zählt jetzt seine Versuche (`tries`) und merkt
sich die gescheiterten Quellen (`tried_sources`). **Ab dem dritten Versuch** wechselt
`alternative_quelle()` auf eine andere Quelle: eine Quelle, die einen Titel nicht liefert,
liefert ihn auch beim vierten Mal nicht — der Artikel ist unvollständig, der Indexer
veraltet oder die Kategorie falsch, und nichts davon bessert sich durch Warten. Die
übrigen Quellen scheitern unabhängig davon, ein Wechsel trägt also als Einziger neue
Information.

Der Titelvergleich beim Wechsel läuft über `norm()` — dieselbe Normalisierung wie die
Dedup — und ist **streng**: ein Wechsel, der ein anderes Spiel holt, wäre schlimmer als der
Fehlschlag, den er beheben soll. Findet sich kein passender Treffer, endet der Aufruf mit
`409` und `exhausted`, und der Auftrag wird **nicht** erneut eingestellt; „alle Quellen
versucht" liest sich sonst wie „eines ist kaputt". Ein geglückter Import setzt den Zähler
zurück. In der Oberfläche steht der Versuch am Eintrag, und der Knopf heißt vor dem
Wechsel *Erneut · andere Quelle* — ein plötzlich anderes Ergebnis wäre sonst nicht
erklärbar.

**Anfragen entfernen** (#246): Der Zähler am Anfragen-Knopf zählt `jobOffen` — also
*aktiv* **und** *fehler*. Jede fehlgeschlagene Anfrage erhöhte ihn dauerhaft, und die Zahl
konnte nur steigen. `DELETE /api/jobs/{jid}` entfernt eine **abgeschlossene** Anfrage
(`done`, `error`, `denied`); laufende werden mit 400 abgewiesen, damit nichts verschwindet,
während im Hintergrund noch geladen wird.

Der heikle Teil ist der liegengebliebene Download: der Auftrag ist das Einzige, was einen
`romseerr_<jid>`-Ordner noch einem Titel zuordnet. Deshalb kennt der Endpunkt genau zwei
Ausgänge — Dateien mitlöschen (`files: true`) oder im Ergebnis ausdrücklich melden, dass
sie zurückbleiben (`files_left`). Stillschweigend verwaisen lassen ist der eine Ausgang,
den es nicht geben darf, sonst räumt die Frist aus #244 später etwas weg, über das nie
jemand entschieden hat.

`POST /api/jobs/clear-finished` nimmt jetzt optional `states` und lässt sich damit auf eine
Gruppe eingrenzen; in der Anfragenliste hängt der Knopf am aktiven Gruppenfilter. Vorher
gab es ihn nur unter *Wartung* und nur alles-oder-nichts — beschriftet als „Fertige
entfernen", obwohl er immer schon auch Fehler und Ablehnungen mitnahm.

**Erneut einlesen statt neu laden** (#245): `POST /api/jobs/{jid}/reimport` lässt
`import_folder()` noch einmal über den liegengebliebenen Ordner laufen. Das ist etwas
anderes als `POST /api/jobs/{jid}/retry`, das den Auftrag zurück in die
Download-Warteschlange legt und **alles neu holt** — 2 GB erneut zu ziehen, weil eine
Endung falsch erkannt wurde, wäre genau das Gegenteil dessen, wofür #240 die Daten
aufhebt. Beide Wege enden in `einsortieren()`, damit Import und Aufräumen nicht an zwei
Stellen auseinanderlaufen. Angeboten wird der Knopf nur, wenn die Dateien wirklich noch
da sind: `/api/jobs` meldet das je fehlgeschlagenem Auftrag als `reimportable`, denn ein
Knopf, der beim Drücken scheitert, ist schlechter als keiner.

Zwei Sperren sitzen bewusst tief im Code, nicht in der Oberfläche: `leftover_dirs()` zeigt
Ordner **laufender** Aufträge gar nicht erst an (Alter allein wäre untauglich — ein großer
Download kann Stunden brauchen und sieht dabei alt aus), und `leftover_remove()` löscht
nur, was nach Auflösung aller Symlinks unterhalb eines Sammelordners liegt **und** das
`romseerr_`-Präfix trägt. `rm -rf` auf einem Pfad aus einer Einstellung ist die eine Stelle
hier, an der ein Denkfehler nicht rückgängig zu machen ist.

Ob das Löschen geklappt hat, entscheidet **der Zustand am Ziel**, nicht der Rückgabewert
von `rm`: `leftover_remove()` prüft nach dem Aufruf, ob der Ordner wirklich weg ist. Der
Grund für einen Fehlschlag wird bis in die Oberfläche durchgereicht — er steht unter der
Liste und zusätzlich im Log, weil eine Meldung im Browser den nächsten Klick nicht
überlebt. Vorher fiel er zweimal hintereinander unter den Tisch: `loRemove()` warf die
Antwort weg, und die Logzeile nannte nur die Zahl der Erfolge. „0 entfernt" las sich damit
wie „nichts zu tun", während in Wahrheit die Rechte fehlten — der Download-Client legt
seine Ordner unter einer anderen Kennung ohne Gruppen-Schreibrecht an, sodass Romseerr sie
sieht, aber nicht leeren darf (#645).

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
`retry` counts attempts (`tries`) and remembers failed sources (`tried_sources`); from the third attempt it switches source via `alternative_quelle()`, matching titles through `norm()` strictly — switching to a different game would be worse than the failure it fixes. With no match left it returns `409 exhausted` and does **not** re-queue. A successful import resets the counter. `DELETE /api/jobs/{jid}` removes a finished request (`done`, `error`, `denied`; active ones are refused). Failed requests count toward the badge forever otherwise. If a kept download belongs to it, the call either deletes it too (`files: true`) or reports `files_left` — silently orphaning it is the one outcome not allowed, since the request is the only thing mapping that folder to a title. `clear-finished` accepts `states` to limit the sweep to one group. `POST /api/jobs/{jid}/reimport` re-runs the import against the kept folder — as opposed to `/retry`, which re-downloads everything. Both end in `einsortieren()` so import and cleanup cannot drift apart, and the button only appears when the files are actually still there (`reimportable` per failed job). Two guards live in the code rather than the UI: folders belonging to a **running** job are
never listed, and removal only accepts paths that resolve inside a collect directory and
carry the `romseerr_` prefix. Success is decided by the state at the target, not by the
return code of `rm` — the folder has to be gone. The reason for a failure now reaches both
the page (below the list) and the log, since a message in the browser does not survive the
next click. It used to be dropped twice over: `loRemove()` discarded the response, and the
log line only carried the success count, so "0 removed" read like "nothing to do" while the
real cause was permissions — the download client creates its folders under a different
account without group write access, so Romseerr can see them but not empty them (#645).*

### Kurzmeldungen an einer Zeile überleben das Auffrischen nicht (#449, #459)

Die Anfragenliste zeichnet sich alle vier Sekunden neu und ersetzt dabei `#jobs` vollständig.
Was an einer **Zeile** hängt, ist danach weg. Das hat zweimal in Folge zugeschlagen, in zwei
verschiedenen Formen:

| hängt an der Zeile | Folge | Lösung |
|---|---|---|
| `onclick` je Zeile | Klick ins Fenster tut nichts (#449) | ein Zuhörer am **Behälter**, `jobKlickBindung` |
| Meldungstext in `.jobmsg` | Antwort verschwindet, evtl. sofort (#459) | `JOBMELDUNG`-Karte je **Auftrags-Id**, von `loadJobs` wieder eingetragen |

Beide Male war die Ursache dieselbe und die erste Reparatur nur die Hälfte: #419 senkte die
Zahl der Neuaufbauten, das Fenster blieb. **Nicht seltener machen, sondern woanders
verankern** — am Behälter, der nicht ersetzt wird, oder am Auftrag, der die Zeile überdauert.

Dazu gehört: **kein stilles Scheitern.** In `openJobDetail` stand ein leerer `catch`; ein
Netzfehler oder ein 500 aus `/api/search` ließ die Zeile aufhellen und sonst geschah nichts —
von einem toten Knopf nicht zu unterscheiden. Jeder Ausgang schreibt jetzt eine Meldung.

Für Tests heißt das: `j.innerHTML = j.innerHTML` verwirft **Ereignisbindungen**, erhält aber
den **Text** — er steht ja im serialisierten HTML. Für die Klickfrage ist dieser Rundlauf
also der richtige Hebel, für die Meldungsfrage der falsche. Dort braucht es den echten Weg:
`JOBSTAND` leeren und `loadJobs()` rufen. Mit dem falschen Hebel bestand die Prüfung auch
gegen den kaputten Stand.

*EN: the requests list replaces `#jobs` wholesale every four seconds, so anything bound to a
row is lost. Twice in a row this bit: the per-row click handler (#449) and the message text
in `.jobmsg` (#459). Reducing how often it happens is not a fix — anchor elsewhere: on the
container, which is never replaced, or on the job id, which outlives the row. And never fail
silently: the empty `catch` in `openJobDetail` made a broken lookup look like a dead button.
For tests: an `innerHTML` round-trip discards event handlers but preserves text, so it is the
right lever for the click question and the wrong one for the message question — there, clear
`JOBSTAND` and call `loadJobs()`.*

### Etwas an der Oberfläche ändern
Datei unter `static/` oder `templates/` bearbeiten, App neu starten (der Hash und damit die
URL ändern sich automatisch). Kein Build, kein Bündler.

### Die Marke
Ein Modul mit ausgestanztem **R**, in drei Fassungen unter `static/`:

| Datei | Wofür | Besonderheit |
|---|---|---|
| `logo.svg` | Oberfläche, ab ~24 px | volles Zeichen mit drei Kontakten |
| `icon.svg` | Lesezeichen, Reiter | gröbere Balken, keine Kontakte |
| `icon-maskable.svg` | installierte App | Fläche mit Sicherheitsabstand |

In den Seiten steht sie **einmal** als `<g id="rs-marke">` in `templates/index.html`, alles
Weitere referenziert sie mit `<use href="#rs-marke">` — auch die Fußzeile und die
Über-Seite, die `index.js` baut. `login.html` und `reset.html` sind eigene Dokumente und
tragen sie direkt.

Zwei Regeln, beide aus Fehlern der Vorgängerfassung (#650):

- **Keine Schrift, kein Emoji, nur Pfade.** Vorher war das Icon ein 🎮 als `<text>` — das
  Ergebnis hing daran, welche Emoji-Schrift der Anzeigende hat, und im Favicon wird gar
  keine geladen. `test_the_brand_never_depends_on_a_font_or_an_emoji` verbietet die
  Rückkehr für **jede** SVG-Datei unter `static/`, nicht nur für die drei genannten.
- **`maskable` ist ein eigenes Bild, kein zweites Wort.** Android und iOS schneiden die
  Kachel rund; ein randloses Zeichen verliert dabei seine Ecke. Das Manifest trug
  `purpose: "any maskable"` für ein Icon ganz ohne Sicherheitsabstand.

In Benachrichtigungen an Discord bleibt das 🎮 stehen: dort ist es Schmuck in einer
Textnachricht, kein Zeichen, das für sich stehen muss.

*EN: the mark is a cartridge with the letter R cut out, in three files — full for the
interface, simplified for favicons, and a maskable tile with a safe area. It is defined
once as `<g id="rs-marke">` and referenced with `<use>`, including from the footer and
about page built in JS. Two rules, both learned the hard way: paths only, never a font or
an emoji (a favicon loads no emoji font), and `maskable` needs its own image with clearance
rather than a second word in `purpose`. The 🎮 stays in Discord notifications, where it is
decoration in a message rather than a mark standing on its own.*

### Designs
Vier Stück, umschaltbar in den Einstellungen und in `DESIGNS` (`static/js/index.js`)
aufgezählt: `seerr`, `glass`, `clean` und `aurora`. Gewählt wird über `data-design` am
`<html>`-Element; jedes Design definiert dieselben Variablen (`--bg`, `--card`, `--acc`,
`--gefahr`, …) neu, die Regeln selbst greifen ausschließlich über diese Variablen.

Zwei Dinge, an denen das regelmäßig scheitert:

- **Ein Design ist kein Bildschirm.** Wer nur die Entdecken-Ansicht ansieht, übersieht, was
  in Anfragen, Problemen, Abdeckung und Einstellungen passiert — genau so blieb die
  Aurora-Bühne in allen Ansichten stehen (#636).
- **Die Kaskade entscheidet, nicht die Absicht.** `#setcontent button` und
  `#modal .row button` färben mit einer ID, und eine ID schlägt jede Klasse. Eine neue
  Knopfklasse muss diese Bereiche mitnennen, sonst bleibt sie folgenlos, während Variable,
  Regel und Markup allesamt richtig aussehen (#647). Statische Tests merken das nicht;
  geprüft wird im Browsertest über die **berechnete** Farbe, für jedes Design.

*EN: four themes — `seerr`, `glass`, `clean`, `aurora` — selected through `data-design` on
the root element, each redefining the same variables. Two recurring traps: a theme is not a
single screen (check every view, cf. #636), and the cascade decides rather than the
intention — `#setcontent button` and `#modal .row button` paint by ID, which outranks any
class, so a new button class has to name those contexts or it silently does nothing (#647).
Static checks cannot see this; the browser test reads the computed colour per theme.*

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
