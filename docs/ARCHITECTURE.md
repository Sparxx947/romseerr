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
   sortiert nach `ROMS/<slug>/` ein, liest **die betroffenen Plattformen** neu ein (#655) und
   **benachrichtigt** (Job → `done`).
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

### Der Import darf nicht die ganze Bibliothek neu lesen (#655)

Ein Import von **zwei Dateien dauerte 6,5 Minuten**, und fast nichts davon war der Import.
Am echten Bestand nachgemessen (599 Plattformen, 293.068 Titel, 660.671 Dateien in 15.366
Ordnern, Unraid/shfs):

| Abschnitt von `build_index()` | Zeit |
|---|---|
| Wanderung über `/roms` | **254,2 s** |
| `save_index_to_db` (293.068 Zeilen ersetzen) | 6,5 s |
| `refresh_coverage_counts` | 0,0 s |
| **gesamt** | **260,7 s** |

Das lief **je Import**, unabhängig davon, ob eine Datei ankam oder tausend — und auch dann,
wenn *keine* ankam. Der teuerste Fall im Issue war genau der: eine 1-MB-Datei, die sich als
Dublette herausstellte. Solange der Lauf läuft, steht der Job auf `importing`, der einzige
`worker_download`-Faden ist belegt, und alles dahinter wartet.

**`index_aktualisieren(slugs)` liest nur die betroffenen Plattformen** — und liest sie
*vollständig* neu:

| | addiert nur | Plattform neu gelesen | voller Lauf |
|---|---|---|---|
| neue Datei | ✓ | ✓ | ✓ |
| gelöschte Datei in derselben Plattform | ✗ | ✓ | ✓ |
| Umbenennung in derselben Plattform | ✗ | ✓ | ✓ |
| Änderung in einer **anderen** Plattform | ✗ | ✗ | ✓ |

**Warum je Plattform und nicht je Datei:** Ein Zusatz „diese Datei kommt hinzu" wäre noch
schneller, könnte aber nur *addieren*. Ein Plattformordner wird hier ganz neu gelesen und
sein Anteil am Index **ersetzt**; für die genannten Plattformen ist das Ergebnis Zeichen für
Zeichen dasselbe wie nach einem vollen Neubau — RAM-Index, DB-Zeilen und die Zähler in
`meta`. Das ist die Bedingung aus dem Issue, und sie steht als Test da
(`test_index_aktualisieren_ergibt_dasselbe_wie_ein_voller_neubau`, mit Löschung und
Umbenennung, nicht nur mit einer neuen Datei).

Übrig bleibt genau die letzte Zeile der Tabelle — und dafür läuft `periodic_index`
unverändert **alle 600 s über alles**. Der volle Lauf verschwindet nicht, er wird nur nicht
mehr an einen Import gehängt, der ihn nicht braucht.

**Gefiltert wird am Slug, nicht am Ordnernamen.** `dc` und `dreamcast` sind dieselbe
Plattform (#454), und ein Import landet je nach Bestand im einen oder im anderen Ordner.
Die Ordnerliste wird deshalb wie beim vollen Lauf durchgegangen und `folder_slug()`
entscheidet — dieselbe Regel, nur mit einem Filter dahinter.

**`LIB["ts"]` bleibt bei einem Teillauf stehen.** Der Wert beantwortet „wann wurde die
Bibliothek zuletzt *vollständig* gelesen", und ein Teillauf beantwortet das nicht. Ihn
mitzuziehen hieße, eine Aussage über 598 Plattformen zu machen, die dieser Lauf nie
angesehen hat.

*EN: importing two files took 6.5 minutes, and almost none of that was the import.
Measured on the real library: `build_index()` costs 260.7 s, 254.2 s of it walking 660,671
files — and it ran after every import, even one that added nothing.
`index_aktualisieren(slugs)` re-reads only the affected platforms, but re-reads them in
full and REPLACES their share of the index, so deletions and renames inside them are
covered exactly as by a full rebuild. Only other platforms lag, and the periodic full run
every 600 s still covers those. Filtering is by slug, not folder name, because `dc` and
`dreamcast` are one platform. `LIB["ts"]` deliberately keeps meaning "last FULL run".*

### Nicht die Prüfung war teuer, sondern ihre Anzahl (#666)

Von den 254,2 s Wanderung oben gingen rund 70 % für **eine einzige Zeile** drauf:
`ist_xsym()` je Datei. Die Prüfung schützt eine echte Zusage (#193) und ist für sich schon
minimal — eine Größenabfrage, den Kopf liest sie nur bei einem Treffer. Nur fragt der Index
sie **660.671-mal**, und über Unraids shfs kostet ein `stat` rund 260 µs. Am Bestand
gemessen, jeweils der volle Durchlauf über `/roms`:

| Durchlauf | Zeit | Fund |
|---|---|---|
| nackter `os.walk`, nur zählen | 17,9 s | 660.671 Dateien |
| `stat` je Datei, nacheinander | **193,1 s** | 17 Dateien mit 1067 Byte, davon **7** echte XSym |
| `stat` je Datei, je Ordner gebündelt über 16 Threads | **55,0 s** | dieselben 17, dieselben 7 |
| dasselbe mit 32 Threads | 58,7 s | dieselben |

**Die Zusage bleibt wörtlich bestehen.** Jede Datei wird weiterhin gefragt, jede
1067-Byte-Datei weiterhin am Kopf geprüft. Es wartet nur nicht mehr jede Anfrage auf die
Antwort der vorigen — die Zeit ging fast vollständig im Warten auf den Syscall drauf, nicht
in Rechenarbeit, und genau das lässt sich verteilen, ohne die Regel anzufassen. 16 Threads,
weil 32 nichts mehr bringen.

Am kompletten Wanderungsabschnitt nachgemessen, alt gegen neu, mit dem echten `norm()` und
`ist_titel_ordner()` daneben:

| | Zeit | Ergebnis |
|---|---|---|
| Datei für Datei | 236,0 s | 599 Plattformen, 293.068 Titel |
| je Ordner gebündelt | **96,4 s** | 599 Plattformen, 293.068 Titel |

Titelzahlen **je Plattform** und **alle Anzeigenamen** stimmen überein — geprüft, nicht
angenommen. Der neue Lauf stand zuerst und war beim zweiten Mal wieder bei 96,5 s; es ist
kein warmer Zwischenspeicher.

**Zwei naheliegende Abkürzungen wurden verworfen**, beide schneller, beide nicht mehr
dieselbe Zusage:

| Abkürzung | warum nicht |
|---|---|
| nur die **erste Datei je Ordner** fragen | die Herstellerordner aus #193 bestehen ganz aus Verweisen, aber ein *einzelner* Platzhalter zwischen echten ROMs rutschte damit als Titel durch |
| nur Dateien **ohne bekannte ROM-Endung** fragen | eine Namensregel — genau das, was #193 verworfen hat; ein Verweis darf `Sonic.bin` heißen |

**Erst normalisieren, dann fragen.** Eine Datei ohne Titelschlüssel wird ohnehin übergangen
und braucht keine Anfrage. Das war vorher schon so, weil das `continue` davor stand; beim
Bündeln muss die Reihenfolge von Hand erhalten bleiben, sonst fragt der Index *mehr* Dateien
als zuvor. Ein Test hält das fest.

*EN: about 70 % of the 254.2 s walk was one line — `ist_xsym()` per file. The check itself
is already minimal; its COUNT is the cost: 660,671 files, ~260 µs per `stat` over shfs.
Batching per folder across 16 threads takes the full pass from 193.1 s to 55.0 s and the
whole walk section from 236.0 s to 96.4 s, with identical output — same 599 platforms,
same 293,068 titles, same per-platform counts and display names, same 7 stand-ins found.
The #193 guarantee is untouched: every file is still asked and every 1067-byte file still
has its header read; the calls simply no longer queue up, because the time was spent
waiting on the syscall, not computing. 32 threads gain nothing. Two obvious shortcuts were
rejected — asking only the first file per folder (a lone stand-in among real ROMs would
slip through) and asking only files without a known ROM extension (a name-based rule,
which is exactly what #193 refused; a stand-in may be called `Sonic.bin`). Normalising
before asking keeps the file count down and is pinned by a test.*

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

**Steht die richtige Endung nirgends im Namen**, entscheidet die Dateikennung
(`rom_endung_aus_inhalt`) — eng gefasst: nur bei unbekannter Endung, erst ab 64 MB, nur
zwei eindeutige Signaturen. Was sie liefert, **ersetzt** die vorhandene Endung, statt sich
anzuhängen (`ziel_mit_endung`, #649). Das ist der Unterschied zwischen
`Portal.2.NSW.VENOM.nsp` und `Portal.2.NSW.VENOM.hdf.nsp`; die zweite Form lief zwar, ließ
den Rest aber im Namen und damit im Dedup-Schlüssel stehen — `norm()` lieferte
„portal 2 venom hdf" statt „portal 2", weil die Gruppenkürzel-Regel das Kürzel am
Namensende erwartet. Dieselbe Datei aus einer Quelle ohne Verschleierung wäre ein zweites
Mal geholt worden.

**Gekürzt wird nur, was wie eine Endung aussieht**, und die Grenzen sind am Bestand
gemessen statt geschätzt: mindestens zwei Zeichen, beginnend mit einem Buchstaben. In der
Bibliothek endet der Name von 17 Titeln auf einen einzelnen Buchstaben hinter einem Punkt
(`H.E.R.O`, `I.C.U.P.S`, `H.A.T.E`) — dort ist die letzte Silbe Teil des Namens. Der
Ziffernausschluss schützt Versionsangaben (`Spiel v1.0`, `AGS_Mini.7z.001`).

Eine Positivliste „bekannter Müll-Suffixe" wäre der naheliegende, aber falsche Weg:
**`.hdf` ist bei Amiga ein echtes Format** — 3.193 Festplattenabbilder in der Bibliothek
tragen es. Was eine Endung bedeutet, hängt an der Datei, nicht am Suffix. Tragfähig ist
allein, dass die Kennung diese eine Datei bereits eindeutig bestimmt hat.

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

**`.unsortiert` wird angezeigt, nicht sortiert.** Was sich beim Import keiner Plattform
zuordnen liess, landet dort statt geraten zu werden — die Oberfläche warnte an drei Stellen
davor, dass das passieren *kann*, hat den Ordner aber nie geöffnet: `UNSORTIERT` kam im Code
ausschliesslich als Ziel vor. Am 2026-08-14 lagen dort Bruchstücke seit dem 11. August, ohne
dass es irgendwo stand. `unsortiert_eintraege()` und `GET /api/unsortiert` liefern Name,
Grösse, Dateizahl und Alter, die Wartungsansicht zeigt sie unter den liegengebliebenen
Downloads (#656).

Dass diese Ansicht **nur liest**, ist keine Sparsamkeit, sondern der Zweck des Ordners: Was
hier liegt, konnte niemand zuordnen, und eine Plattform dafür zu raten ist genau das, wovor
er bewahrt. Es gibt deshalb bewusst keinen schreibenden Endpunkt — ein Test hält das fest.

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
unknown, and trims the bogus suffix when copying. When the right extension is nowhere in the
name, the file's magic decides (`rom_endung_aus_inhalt`: unknown extension only, 64 MB
minimum, two unambiguous signatures) and what it returns **replaces** the existing extension
rather than being appended (#649) — `Portal.2.NSW.VENOM.nsp`, not `…VENOM.hdf.nsp`, whose
leftover suffix stayed in the dedup key and would have caused the same file to be fetched
twice. Only extension-shaped endings are cut, with the limits measured rather than guessed:
at least two characters, starting with a letter, because 17 titles in the library end in a
single letter after a dot (`H.E.R.O`) and digits mark versions (`AGS_Mini.7z.001`). A
positive list of "junk suffixes" would be the obvious wrong answer: `.hdf` is a genuine
Amiga format carried by 3,193 files here. What an extension means depends on the file, not
on the suffix. And a failed import must not destroy the
payload: cleanup now happens only when the import actually took something, because
previously both paths cleaned up identically and a 2 GB download was deleted along with
the client's history entry (`del_files=1`), leaving nothing to diagnose. Leftover folders
are listed under Settings → Logs & maintenance with size, age and owning request, can be
removed individually or in bulk, and expire after `leftover_days` (default 14, 0 = off).
`retry` counts attempts (`tries`) and remembers failed sources (`tried_sources`); from the third attempt it switches source via `alternative_quelle()`, matching titles through `norm()` strictly — switching to a different game would be worse than the failure it fixes. With no match left it returns `409 exhausted` and does **not** re-queue. A successful import resets the counter. `DELETE /api/jobs/{jid}` removes a finished request (`done`, `error`, `denied`; active ones are refused). Failed requests count toward the badge forever otherwise. If a kept download belongs to it, the call either deletes it too (`files: true`) or reports `files_left` — silently orphaning it is the one outcome not allowed, since the request is the only thing mapping that folder to a title. `clear-finished` accepts `states` to limit the sweep to one group. `POST /api/jobs/{jid}/reimport` re-runs the import against the kept folder — as opposed to `/retry`, which re-downloads everything. Both end in `einsortieren()` so import and cleanup cannot drift apart, and the button only appears when the files are actually still there (`reimportable` per failed job). Two guards live in the code rather than the UI: folders belonging to a **running** job are
`.unsortiert` is now shown rather than sorted: whatever the import could not match to a platform lands there instead of being guessed, and the interface warned about that in three places while never once opening the folder — `UNSORTIERT` appeared in the code only as a destination. `unsortiert_eintraege()` and `GET /api/unsortiert` report name, size, file count and age. The view is deliberately read-only, and there is no writing endpoint: what sits there is precisely what nobody could classify, so guessing a platform for it is the thing the folder exists to prevent (#656). 

folders belonging to a running job are
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

**Sie ist ein Verweis, kein Schmuck (#662).** Ein Klick auf Zeichen oder Schriftzug führt
zur Startseite. Drei Dinge daran sind leicht zu übersehen:

- **„Startseite" heißt Entdecken MIT LEEREM SUCHFELD.** `zeige()` blendet die Bühne nur
  ein, solange `#q` leer ist. Bleibt der Suchbegriff stehen, landet der Klick auf einer
  Trefferliste — dann tut die Marke nichts anderes als der Menüpunkt „Entdecken". Das
  Leeren steht deshalb in `sucheLeeren()`, einer eigenen Funktion: Der Zurück-/Leeren-Knopf
  der Suche (#661) braucht dieselbe Zurücksetzung, und zwei Fassungen davon laufen
  auseinander, sobald eine von beiden noch etwas mehr zurücksetzt.
- **`<a href>` und `return false`, nicht `div` mit `onclick`.** Nur der Verweis steht in
  der Tab-Reihenfolge, hat eine Rolle und lässt sich in einem neuen Tab öffnen — gemessen
  am Stand davor: 40 Tab-Schritte, kein Treffer. Der Klick läuft trotzdem über `markeGeh()`
  → `show()` statt über die Navigation des Browsers, aus demselben Grund wie bei den
  Menüpunkten: `routeSetzen` zählt in `EIGENE_SCHRITTE` mit, wie viele Verlaufseinträge die
  App selbst gesetzt hat.
- **Ein Verweis bringt Farbe und Unterstreichung mit.** `.logo` färbt seinen Text über
  `background-clip:text` mit `color:transparent`; die Farbe hält, weil `#side .logo` eine
  ID trägt und damit `a:-webkit-any-link` schlägt, die Unterstreichung nicht — die muss
  ausdrücklich weg. Und die Breite des Kastens bleibt, wie sie ist: Der Verlauf wird über
  den Kasten gemalt, ein `width:fit-content` färbte den Schriftzug anders.
  `test_die_marke_sieht_als_verweis_aus_wie_vorher` vergleicht dafür in allen vier Designs
  gegen einen eingesetzten `div.logo` als Referenz.

*EN: the mark is a cartridge with the letter R cut out, in three files — full for the
interface, simplified for favicons, and a maskable tile with a safe area. It is defined
once as `<g id="rs-marke">` and referenced with `<use>`, including from the footer and
about page built in JS. Two rules, both learned the hard way: paths only, never a font or
an emoji (a favicon loads no emoji font), and `maskable` needs its own image with clearance
rather than a second word in `purpose`. The 🎮 stays in Discord notifications, where it is
decoration in a message rather than a mark standing on its own.
Since #662 the mark is also a link home. Three things are easy to miss there: "home" means
the discover view with an EMPTY search field, because the stage only shows while `#q` is
empty — the reset lives in `sucheLeeren()` so the search clear button (#661) can reuse it;
it must be a real `<a href>` rather than a div with an onclick (measured before the change:
40 tab steps never reached it), while the click still goes through `markeGeh()` → `show()`
so that `EIGENE_SCHRITTE` keeps counting the history entries the app pushed; and a link
brings link colour and underline along, so the underline is switched off explicitly and the
box width is left alone — the gradient is painted across the box, so a narrower box would
recolour the wordmark.*

### Designs
Vier Stück, umschaltbar in den Einstellungen und in `DESIGNS` (`static/js/index.js`)
aufgezählt: `seerr`, `glass`, `clean` und `aurora`. Gewählt wird über `data-design` am
`<html>`-Element; jedes Design definiert dieselben Variablen (`--bg`, `--card`, `--acc`,
`--gefahr`, …) neu, die Regeln selbst greifen ausschließlich über diese Variablen.

**Die Navigation wechselt die Achse.** `#side` ist im Grundzustand eine feste Spalte am
linken Rand und **nur unter Aurora** — sowie unter 680 px — eine Zeile oben. Wer dort etwas
einbaut, baut es für zwei Layouts. Sprache und Benutzermenü sitzen seit #672 am **Ende** der
Navigation: rechts in der Zeile, unten in der Spalte, wo Konten üblicherweise stehen. Der
Plattformfilter und der Pokal bleiben in der Suchzeile, weil sie zum Suchen gehören.

Zwei Fallen, beide gemessen statt vermutet: `margin-left:auto` schiebt in einer Spalte
nichts — ohne `margin-top:auto` klebt der Block am Logo, mit **264 px Luft** nach unten. Und
ein Menü, das am Fuß der Leiste nach unten aufklappt, liegt **106 px unterhalb** des
Fensterrands und ist unerreichbar; in der Spalte muss es nach oben öffnen. Der Browsertest
misst beides je Design, weil eine Regel im Stylesheet nichts darüber beweist, wohin der
Flex-Container sie tatsächlich legt.

**Größe verrät eine Sammlung nur in der Modul-Ära (#689).** `is_set` steht im
Sortierschlüssel der Suche, und alles, was dort landet, rutscht ans Listenende. Die Regel
„über 4 GB ist vermutlich eine Sammlung" stammt aus der Retro-Sicht und traf ab der CD-Ära
fast nur Einzelspiele: Gemessen über zwölf Suchen galten **156** Treffer als Sammlung, davon
waren **136 Einzelspiele** — `Uncharted 2` mit 21,9 GB, `The Last of Us` mit 29,5 GB,
`Silent Hill Homecoming` mit 6,7 GB.

Der sichtbare Schaden: Bei „Silent Hill" standen die drei Homecoming-Fassungen auf Platz 33,
34 und 53 von 59. In einer Liste dieser Länge ist das dasselbe wie nicht gefunden — genau so
ist es aufgefallen.

Die Schwelle gilt deshalb nur noch für Plattformen vor 1994 (`SET_GROESSE_BIS_JAHR`), wo ein
Einzelspiel höchstens ein paar hundert MB hat. Was dabei durchgerutscht wäre, fängt das
Namensmuster: Von 136 Verlusten waren nach Einzelprüfung **vier echte Sammlungen** — Mod-
Archive und ROMhack-Pakete —, und für die stehen jetzt `mod archive`, `rom hacks`, `cias`,
`anthology` und `trilogy` in `SET_RE`. **`archive` allein bewusst nicht**: Das Wort steht in
jedem zweiten Archive.org-Titel.

**Nur das Cover-Abzeichen ist absolut positioniert (#698).** Jens meldete, dass „Im Browser
spielen" oben links über der Navigationsleiste stand. Gemessen bei offener Detailkarte: der
Knopf bei **(6, 6)**, sein Platz `#mplay` bei **(892, 529)** — 900 px daneben.

Die Ursache reichte weiter als der eine Knopf. `.badge` war absolut positioniert; weiter
unten im Blatt steht eine **zweite** `.badge`-Regel für die Abzeichen der Detailansicht, mit
gleicher Spezifität und später. Sie gewann für alles, was sie selbst deklariert — Grund,
Rahmen, Polsterung, Schriftgröße — **aber sie setzt `position` nicht zurück**. Von der ersten
Regel wirkte also nur noch `position/top/left`, und die wirkte überall: Ein Abzeichen in
einem Kasten bei (40, 582) landete bei (6, 6). Betroffen waren Bewertung, Jahr, Entwickler,
Genres und die Achievements-Zeile.

Die Regel ist deshalb an `.cover` gebunden und enthält **ausschließlich** die Positionierung.
Alles Sichtbare kommt weiter aus der Regel darunter — hätte man es mit hochgezogen, hätte
sich das Aussehen des Cover-Abzeichens still geändert, in Aurora sogar seine runde Form.

Der Spielen-Knopf trägt jetzt eine eigene Klasse und wird gebaut wie der Stream-Knopf daneben:
Die beiden sind Geschwister — „hier spielen" und „auf dem Host spielen" — und gehören als
Paar gelesen.

**Menü und Reiter tragen gezeichnete Zeichen (#658).** Die Navigation lief auf Emoji — die
kommen aus der Schriftart, die das System gerade hat. Dass `.navsym` ein
`font-variant-emoji:emoji` und die Zeichen den Variantenselektor U+FE0F trugen, sagte es
deutlich: Zwei Kunstgriffe, um einer Schrift eine Darstellung abzuringen, mit einem Ergebnis,
das sich je Plattform unterschied. Jens hat aus zwei Entwürfen den **Konturstil** gewählt.

Die Formensprache stammt aus der Marke, aber nicht als Kopie: Wo es um ein **Spiel** geht,
trägt das Zeichen die Modulsilhouette mit ihrer abgeschrägten Ecke. Wo nicht, steht bewusst
eine gewöhnliche Form — Regler, Schloss, Glocke. Jede Idee in die Modulform zu zwingen macht
die Reihe schlechter, nicht geschlossener. Entdecken ist deshalb eine **Lupe mit
Modulglas**: Ein Modul mit einer Lupe daneben wären bei 21 px zwei zu kleine Dinge.

**Der #337-Weg war live, und zwar schlimmer als gedacht.** `applyI18n` setzt `textContent`
des Elements mit `data-i18n` und löscht damit jedes Kind. Bei `profile` und `nav_lists` stand
das Symbol nur in der Vorlage, nicht in der Übersetzung — am laufenden Stand gemessen waren
👤 und ⭐ deshalb **nie** zu sehen, nicht erst nach einem Sprachwechsel, sondern schon beim
Laden. Nur 🚪 überlebte, weil es im Übersetzungstext saß; genau deshalb musste es beim Umbau
aus allen fünf Sprachdateien heraus.

Die Untereinträge der Einstellungen (Discord, SMTP, Telegram …) bekommen **keine** Zeichen:
Dort stehen Produktnamen, ein erfundenes Zeichen sagt weniger als der Name, und ein
Produktlogo gehört nicht in unsere Formensprache.

**„Vorhanden" trägt die Sprache der Marke (#660).** Das Grün stand an **fünf** Stellen, vier
davon fest als `#1e5e3a` im Stylesheet — deshalb bekamen alle vier Designs dasselbe
Signalgrün, egal wie sie sonst aussehen. Nur das Abzeichen auf dem Cover umzufärben hätte
Anfrageliste und Abdeckung grün gelassen, während die Karten sich ändern; das wäre schlimmer
gewesen als der Ausgangszustand. Jedes Design setzt jetzt `--ok` und `--ok-bg` selbst.

Das Zeichen ist gezeichnet, nicht getippt: Der Haken ist aus der Modulsilhouette
**herausgeschnitten** (`fill-rule="evenodd"`), dieselbe Bauart wie das R im Logo. Vorher
stand dort das Textzeichen `✓`, das aus der Schrift des Systems kommt — die Schwäche, die
die Marke in #650 gerade abgelegt hatte.

Das Abzeichen ist dabei **größer** geworden, und das ist der Punkt: Am Entwurf gemessen war
die Modulform bei 11 px nicht von einem gerundeten Quadrat zu unterscheiden, die abgeschrägte
Ecke ging unter. Ohne diese Vergrößerung wäre die Form umsonst — ein Test hält 16 px als
Untergrenze fest.

**Auch die neutralen Farben kommen aus Variablen (#705).** Nach den Statusfarben blieben
**153** feste Farben im JavaScript, und der größte Teil war schlicht die Palette des
Standard-Designs: `#8b929e`, `#e6e8ec` und `#2c323b` sind wörtlich die Seerr-Werte von
`--mut`, `--txt` und `--border`. In den drei anderen Designs waren sie damit falsch — es
fiel nur niemandem auf, weil heute alle vier Designs dunkel sind. Ein helles Design hätte
alle 153 auf einmal sichtbar gemacht.

Zugeordnet wurde nach der **Rolle**, nicht nach dem Ton: Was das Element *ist*, entscheidet
die Variable. Dabei kamen zwei Rollen dazu, die es vorher nur als Zahl gab:

- **`--btn2`** — der zurückhaltende Knopf. Dialoge und Karten liegen selbst auf `--card`;
  ein Knopf mit demselben Grund wäre dort unsichtbar. Genau deshalb stand im JavaScript
  überall ein helleres `#2a2f37`.
- **`--link`** — die Verweisfarbe. Der naheliegende Griff zu `--acc` war in drei von vier
  Designs richtig und in Seerr falsch: `#7c5cff` auf `#0f1114` ergibt **4,35:1** gegen die
  geforderten 4,5. Der Akzent ist als *Knopffarbe* gewählt, also für weiße Schrift **auf**
  ihm — als kleine Schrift auf dem dunkelsten Grund taugt er nicht überall.

**Gefunden hat das die Barrierefreiheitsprüfung, nicht ich.** axe meldete den Verstoß auf
jeder Ansicht, nachdem die Verweise auf `--acc` lagen. Ein Browsertest hält die Bedingung
jetzt ausdrücklich fest, gemessen gegen Fußzeile *und* Karte.

Übrig bleiben **29** feste Farben, und die sind Absicht — je Ton mit Begründung in
`JS_FESTE_FARBEN`: weiße Schrift auf farbigem Grund (18), die Avatar-Palette (5, die muss
sich *voneinander* unterscheiden und darf gerade nicht mitwandern), der Streamen-Knopf, das
Hinweisblau `unverified` und eine durchscheinende Fortschrittsspur.

**Warnung und Fehler haben jetzt ebenfalls Variablen — und der Wächter zählt nicht mehr
Sünder auf, sondern hält den Bestand fest (#703).** 33 feste Farbangaben trugen Warn- und
Fehlerbedeutung, und die Gefahr-Variablen aus #647 (`--gefahr*`, `--bad`) standen
**ausschließlich im Aurora-Block**. In den anderen drei Designs fiel jedes
`var(--bad,#f85149)` auf sein Literal zurück — tückischer als ein nacktes Literal, weil der
Code sich liest, als wäre das Thema erledigt. Alle vier Designs setzen jetzt den vollen Satz.

Zwei Dinge fielen dabei auf, die den Wächter aus #699 als zu eng entlarvten:

- **`#2a6f4b`**, ein viertes Erfolgsgrün am Abzeichen „laufende Anfragen", lief ungehindert
  durch: derselbe Sinn, anderer Ton, kein Treffer in der Werteliste.
- **Vier weitere Statusfarben** (`#7ac57a`, `#c9a227`, `#16a34a`, `#d97706`) waren gar nicht
  zu sehen, weil sie über Nachschlagetabellen zugewiesen werden statt über `color:`.

Der Wächter sucht deshalb **jedes** Hex-Literal im JavaScript (ohne Kommentare, dort stehen
die Issue-Nummern) und vergleicht gegen eine festgehaltene Bestandsaufnahme. Jede neue feste
Farbe fällt auf, auch eine, an die niemand gedacht hat.

Die Bestandsaufnahme ist dabei **keine Erlaubnisliste**: Die verbliebenen 153 Vorkommen sind
zum großen Teil die Werte des Standard-Designs, fest ins JavaScript geschrieben (`#2a2f37`
33×, `#8b929e` 23×, `#e6e8ec` 19×) — in den drei anderen Designs also falsch. Das ist ein
eigenes, größeres Stück Arbeit und als eigenes Issue erfasst.

Die Aurora-Töne mussten dabei anders gewählt werden als in den übrigen Designs: Auroras
Akzent ist ein Orangerot, und Bernstein wie Rot lagen mit Abstand 89 bzw. 102 zu dicht am
Download-Knopf. Dort stehen deshalb ein Gelb (`#f2d55c`, Abstand 144) und ein Rosarot
(`#ff8fa8`, Abstand 139).

**Der Wächter dazu sucht den ganzen Baum ab, statt eine Liste zu pflegen (#699).** Die
erste Fassung sah nur ins Stylesheet — und übersah **sieben** Literale, die als Inline-Stile
im JavaScript standen. Auf Aurora hieß das: das neue gedämpfte Grün auf den Karten, das alte
Signalgrün auf dem Freigabeknopf. Genau die Spaltung, die #660 beseitigen sollte, nur eine
Datei weiter.

Eine handgepflegte Dateiliste hätte den Fehler bloß verschoben: Ein Mutationstest zeigte,
dass niemand merkt, wenn eine Datei wieder herausfällt. Deshalb wird gesucht statt
aufgezählt, **und der Wächter belegt seine eigene Reichweite** — fehlt eine der drei
tragenden Dateien in der Suche, scheitert er dort und nicht erst beim Nachmessen der Farben.

Dazu kommt ein zweiter Wächter: Jede benutzte `var(--…)` muss irgendwo definiert sein. Ein
Tippfehler ist sonst lautlos — CSS wirft dafür nichts, die Eigenschaft bleibt ungesetzt und
die Farbe fällt auf den Erbwert zurück.

Die Farben sind gerechnet, nicht geschätzt, und ein Browsertest misst den Kontrast im
laufenden Aufbau statt ihn zu behaupten. Der einzige enge Fall ist **Glas**: Dessen Akzent
ist Cyan `#22d3ee`, und Cyan liegt nah an Grün. Der Abstand dort war mit 126 der niedrigste
im Bestand und steigt auf 140, indem das Grün ins Gelbgrüne geht statt ins Türkise.

**Eine Karte je Spiel, nicht je Fassung (#691).** Über zehn Reihen-Suchen waren **6 bis
36 %** der Karten Wiederholungen desselben Spiels — im schlimmsten Fall zehnmal
`mario kart`, was neun andere Spiele von den ersten Seiten drückt. Die Oberfläche
widersprach sich dabei selbst: Der Sammelknopf zählte `gkey` und bot „Alle anfragen (25)"
an, während 47 Karten danebenlagen.

Zusammengefasst wird im **Frontend** (`gruppiere()`), nicht in der Antwort: Die
Fassungsliste der Detailansicht baut auf `window.LASTRES` (`x.gkey===it.gkey`), und die
Regionswahl aus #77 ist genau der Grund, warum es sie gibt. Die Antwort bleibt deshalb
vollständig; nur die Anzeige fasst zusammen.

Sortiert wird dafür nach dem Zustand der **Gruppe** (`grp_in_library`), nicht des
Einzeltreffers. Ein Spiel gilt als vorhanden, sobald irgendeine Fassung in der Bibliothek
liegt — das ist die Frage vor dem Klick („habe ich das?"), und `varRow` löst sie danach je
Fassung wieder auf. Ohne diese Stufe zerfiele die Karte: Bei einem Spiel, das auf einer
Plattform daliegt und auf einer anderen nicht, stünde die nicht vorhandene Fassung vorn,
und die Karte trüge einen Download-Knopf neben einem grünen Haken. `in_library` bleibt als
**innerer** Rang darunter, damit die vertretende Fassung zum Zeichen passt.

Die Zahl über der Liste zählt jetzt Karten statt Fassungen, und der Sammelknopf zählt
ebenfalls nach dem Gruppenzustand. Das war zuerst nicht so und fiel erst beim Nachmessen
am laufenden System auf: Bei `Mario Kart` bot der Knopf **25** Spiele an, während **24**
Download-Knöpfe dastanden. Die Differenz war genau eine gemischte Gruppe — ein Spiel, das
auf einer Plattform daliegt und auf einer anderen frei ist. Die Karte trägt dort den Haken
und keinen Download-Knopf; der Knopf hätte die freie Fassung trotzdem geholt. Eine
Sammelanfrage, die lädt, was die Oberfläche als vorhanden ausweist, ist schlimmer als eine
Zahl daneben.

**Der Plattformfilter sagt in der Liste, was er zurückhält (#688).** Ein Klick auf eine
Entdecken-Karte setzt den Filter auf deren Plattform und schreibt ihn nach `localStorage` —
sinnvoll für die Suche, die der Klick auslöst, und danach bleibt er dort stehen. Über
Suchen, über Neuladen, über Tage. „Silent Hill Homecoming" fand mit hängengebliebenem `snes`
noch **4 Treffer statt 14**.

Warum das nicht wie ein Filter aussieht: Ergebnisse **ohne** erkannte Plattform passieren
jeden Filter absichtlich (Archive.org-Titel tragen oft keine Zuordnung und sind trotzdem
gemeint). Es bleibt also etwas übrig — die Liste wirkt nicht gefiltert, sondern so, als
gäbe es den Titel kaum.

Der Knopf darüber half nicht: „Plattformen: 1 gewählt" sagt, wie viele Plattformen gewählt
sind, nicht dass **gerade** zehn Treffer fehlen. `do_search()` zählt deshalb mit, was allein
der Plattformfilter weggenommen hat, und `/api/search` gibt die Zahl als Kopfzeile
`X-Platform-Hidden` zurück — als Kopfzeile, weil die Antwort eine nackte Liste ist, die in
`window.LASTRES`, in `d.forEach` und in der Sammelanfrage steckt; daraus ein Objekt zu
machen, um eine Zahl unterzubringen, hätte jeden dieser Aufrufer angefasst.

Gezählt wird **nur** der Plattformfilter. Sperrliste und Achievements-Filter bleiben außen
vor: Der Hinweis bietet „Filter aufheben" an, und der Klick muss die genannten Treffer auch
wirklich zurückholen. Eine Zahl, die zum Teil aus einer anderen Quelle stammt, wäre nach dem
Klick unerklärlich.

**„In Bibliothek" und „Plattform unbekannt" schließen einander aus (#685).** Sagt ein
Treffer keine Plattform, prüft `in_library()` global gegen die ganze Bibliothek — richtig,
aber es beantwortet nur das *Ob*. Die Karte hatte danach nichts anzuzeigen und schrieb die
Warnung neben das Häkchen. `library_slugs()` beantwortet das *Wo* und hängt es als
`lib_slugs` an den Treffer; die Karte zeigt die erste Plattform normal und die weiteren
darunter gedämpft.

**Sortiert wird nach dem Erscheinungsjahr der Plattform** (`PLAT_JAHR`), älteste zuerst —
bei einem Titel auf mehreren Systemen ist das fast immer die, auf der er zuerst erschien.
Gemessen: **6,9 %** aller Titel liegen auf mehr als einer Plattform (20.249 von 293.067),
Spitzenreiter „pac man" auf 22.

Das ist bewusst das Jahr der **Konsole**, nicht des Spiels: IGDB liefert `first_release_date`
nur als ein Datum je Spiel, plattformweise Daten wären zusätzliche Abfragen je Treffer — und
die Titel, um die es geht (`Super Mario World 64 (Unl)`, Hacks, Homebrew), kennt IGDB gar
nicht. Ein Homebrew von 2020 für den Atari 2600 stünde damit vorn; deshalb behauptet die
Karte nichts über das Spiel, sondern nennt die Plattform zuerst, die es am längsten gibt,
und markiert die Angabe als **abgeleitet**.

Die Warnung selbst bleibt, wo sie hingehört: Bei Treffern, die **nicht** in der Bibliothek
sind, sagt sie weiterhin, dass ein Import in `.unsortiert` landen würde (#621, #367).

**Vier Zahlen, die gern verwechselt werden (#654).** Am gemessenen Bestand vom
2026-08-15:

| Zahl | was sie ist | Wert |
|---|---|---|
| Ordner | jeder Plattformordner unter `ROMS`, auch leere (`LIB["slugs"]`) | 599 |
| Plattformen | die mit Inhalt (`LIB["per"]`, nicht leer) | 64 |
| Einträge | Summe je Plattform — derselbe Titel auf zwei Systemen zählt zweimal | 323.776 |
| Titel | eindeutige `norm()`-Schlüssel über alles (`LIB["all"]`) | 293.067 |

Die Startseite nannte Einträge „Titel" und die Logzeile Ordner „Plattformen" — dadurch
widersprachen sich zwei Anzeigen, obwohl **jede Zahl für sich stimmte**. Dazwischen liegen
noch die 310.004 eindeutigen *Anzeigenamen*; die Differenz zu den Titeln sind Namen, die
denselben `norm()`-Schlüssel teilen, also erkannte Dubletten.

Merksatz: `slugs` sind Ordner, `per` sind Plattformen, die Summe ihrer Längen sind Einträge,
und `all` sind Titel. Wer eine dieser Mengen als eine andere beschriftet, erzeugt genau
diesen Widerspruch wieder.

**Die Suchzeile trägt Zurück und Leeren (#661).** Beide erscheinen nur, wenn sie etwas
bewirken: der Zurück-Knopf, wenn `EIGENE_SCHRITTE > 0` — ohne diese Frage führte ein
`history.back()` aus der Anwendung heraus, sobald jemand direkt auf einer Such-Adresse
gelandet ist (#194/#226) —, der Leeren-Knopf, wenn im Feld etwas steht. Ein Knopf, bei dem
nichts passiert, ist von einem kaputten nicht zu unterscheiden; das war der Befund in #638.

**Geleert wird an genau einer Stelle.** `sucheLeeren(fokus)` bedient den Klick auf die
Marke (#662), den Knopf und Escape. Beim Bauen stand kurzzeitig eine zweite Funktion
gleichen Namens in der Datei — die spätere gewinnt stillschweigend, und `markeGeh()` hätte
unbemerkt die andere Wirkung bekommen. Ein Test zählt die Definitionen.

**Escape hat eine feste Reihenfolge:** Menü, dann Dialog, dann das Suchfeld. Stünde das
Leeren vorn, nähme ein Escape dem Dialog das Schließen weg — und wer einen Dialog schließt,
will nicht seine Suche verlieren.

**Die Navigation wechselt die Achse — und nicht alles darf mitwandern.** `#side` ist im
Grundzustand eine feste Spalte am linken Rand und **nur unter Aurora** (sowie unter 680 px)
eine Zeile oben. Sprache und Benutzermenü stehen deshalb im Markup in der Suchzeile und
werden von `kopfrechtsPlatzieren()` **nur unter Aurora** in die Navigation gehängt, wo sie
oben rechts landen (#672).

Überall zu verschieben wäre der naheliegende, aber falsche Schluss: In den drei anderen
Designs landeten sie unten links in der Spalte — und **aus genau dieser Ecke hat #206 sie
geholt**, weil sie dort niemand absucht. Zwei Wünsche, die einander widersprechen, und die
Auflösung ist der Ort, nicht die Regel. Verschoben wird der **eine** Knoten, keine zweite
Fassung: Zwei Kopien laufen auseinander, wie es der Zeilenbeschriftung in #632 ergangen ist.

Zwei Dinge, an denen das regelmäßig scheitert:

- **Ein Design ist kein Bildschirm.** Wer nur die Entdecken-Ansicht ansieht, übersieht, was
  in Anfragen, Problemen, Abdeckung und Einstellungen passiert — genau so blieb die
  Aurora-Bühne in allen Ansichten stehen (#636).
- **Die Kaskade entscheidet, nicht die Absicht.** `#setcontent button` und
  `#modal .row button` färben mit einer ID, und eine ID schlägt jede Klasse. Eine neue
  Knopfklasse muss diese Bereiche mitnennen, sonst bleibt sie folgenlos, während Variable,
  Regel und Markup allesamt richtig aussehen (#647). Statische Tests merken das nicht;
  geprüft wird im Browsertest über die **berechnete** Farbe, für jedes Design.
- **Ein Verlauf über zwei Kästen ist kein Verlauf.** Der Aurora-Schleier lag zunächst
  zweimal getrennt vor — in `#side::before` und in `#buehne::before` —, jeder vom
  `overflow:hidden` seines eigenen Kastens beschnitten und jeder anders eingestellt. An der
  Unterkante der Kopfleiste ergab das eine harte Kante (gemessen 84 bzw. 76 Farbeinheiten
  über die Naht). Seit #657 trägt ihn `body::before` als **eine** Schicht mit `z-index:-1`;
  `#side` ist dafür durchsichtig. Wer daran arbeitet, sollte drei Messwerte kennen: die
  Schicht muss über das Fenster hinausragen, weil die Animation sie um bis zu 3 % der
  Breite verschiebt; beschnitten wird sie nur, wenn `body` `position:relative` **und**
  `html` ein `overflow-x` trägt (jede Regel allein lässt 97 bzw. 101 px Bildlauf stehen);
  und dort gehört `clip` hin, nicht `hidden` — `hidden` macht `body` zum Rollbereich und
  die klebende Suchleiste hört auf zu kleben.

*EN: size only indicates a collection on cartridge-era platforms (#689). `is_set` feeds the sort key, so anything marked lands at the bottom. Measured across twelve queries: 156 hits counted as collections, 136 of them single games — `Uncharted 2` at 21.9 GB, `The Last of Us` at 29.5 GB. The three Silent Hill Homecoming releases sat at positions 33, 34 and 53 of 59, which is how it surfaced. The threshold now applies only below 1994; the four genuine collections that would have slipped through are caught by name instead. `archive` alone is deliberately not a keyword — it appears in every other Archive.org title.*

*EN: the platform filter states in the list what it is holding back (#688). Clicking a discover card sets the filter to that platform and persists it to `localStorage` — reasonable for the search the click triggers, and it then stays there across searches, reloads and days. With a stale `snes` filter, "Silent Hill Homecoming" returned 4 hits instead of 14. It does not look filtered because results without a recognised platform deliberately pass any filter, so something always remains. The button above reads "Plattformen: 1 gewählt", which says how many platforms are selected, not that ten hits are being withheld right now. `do_search()` therefore counts what the platform filter alone removed and `/api/search` returns it as an `X-Platform-Hidden` header — a header because the response is a bare list consumed in three places. Only the platform filter is counted: the notice offers "drop filter", and that click must actually bring the named hits back.*

*EN: one card per game, not per release (#691). Across ten series searches, 6–36 % of the cards were repeats of the same game — ten `mario kart` entries at worst, pushing nine other games off the first screens. The interface contradicted itself: the bulk button counted `gkey` and offered "Alle anfragen (25)" while 47 cards sat next to it. Grouping happens in the frontend (`gruppiere()`), not in the response: the detail view builds its version list from `window.LASTRES`, and the region choice from #77 is the reason that view exists. Sorting therefore keys on the GROUP state (`grp_in_library`) rather than the individual hit — a game counts as owned once any release is in the library, which is the question asked before the click, and `varRow` resolves it per release afterwards. Without that step the card falls apart: for a game owned on one platform and missing on another, the missing release would rank first and the card would carry a download button beside a green tick. `in_library` remains as an inner rank so the representing release matches the badge.*

*EN: "in library" now speaks the mark's language (#660). The green sat in five places, four of them hard-coded as `#1e5e3a`, so all four themes got the same signal green whatever else they looked like — and restyling only the cover badge would have left the request list and coverage view green while the cards changed, which is worse than the original state. Each theme now sets `--ok` and `--ok-bg` itself. The glyph is drawn, not typed: the tick is cut OUT of the cartridge silhouette (`fill-rule="evenodd"`), the same construction as the R in the mark; it used to be the text character `✓`, which comes from whatever font the system has. The badge grew, and that is the point — measured on the draft, the cartridge was indistinguishable from a rounded square at 11 px, so a test pins 16 px as the floor. Contrast is measured in a browser test rather than asserted; the only tight case is Glass, whose cyan accent sits close to green — distance there rises from 126 to 140 by going yellow-green rather than teal.*

*EN: warning and error now have variables too, and the guard records an inventory instead of listing offenders (#703). 33 hard-coded places carried warning or error meaning, and the danger variables from #647 lived only in the Aurora block — so every `var(--bad,#f85149)` fell back to its literal in three of four themes, which reads as if the problem were already solved. Two findings exposed the #699 guard as too narrow: a fourth success green `#2a6f4b` passed because the guard listed values, and four more status colours were invisible to it because they are assigned through lookup tables rather than a `color:` property. The guard now scans every hex literal in the JavaScript (comments stripped — issue numbers look like hex) against a recorded inventory. That inventory is not an allow-list: most of the 153 remaining occurrences are the default theme's palette written literally into JS, wrong in the other three themes, filed separately. Aurora needed different tones because its accent is an orange-red and both amber and red sat 89/102 away from the download button; it uses a yellow at 144 and a pink-red at 139 instead.*

*EN: the neutral colours now come from variables too (#705). After the status colours, 153 hard-coded values remained in the JavaScript, most of them simply the default theme's palette — `#8b929e`, `#e6e8ec` and `#2c323b` are literally the Seerr values of `--mut`, `--txt` and `--border`, and therefore wrong in the other three themes; nobody noticed because all four themes are dark today. Mapping went by ROLE, not by tone, and two roles that previously existed only as a number got names: `--btn2` (the quiet button — cards and dialogs sit on `--card` themselves, so a button with the same ground would be invisible) and `--link`. The obvious reach for `--acc` was right in three themes and wrong in Seerr: `#7c5cff` on `#0f1114` is 4.35:1 against the required 4.5. The accent is chosen as a BUTTON colour, for white text on it. The accessibility suite caught that, not I; a browser test now pins the condition against both the footer and the card. 29 literals remain deliberately, each with a reason recorded — white on coloured grounds, the avatar palette (which must differ from itself, not follow the theme), the stream button, the "unverified" info blue and a translucent progress track.*

*EN: menu and tabs carry drawn icons (#658). The navigation ran on emoji, which come from whatever font the system has — `.navsym` even carried `font-variant-emoji:emoji` plus U+FE0F, two coercions to force a presentation out of a font. Jens chose the outline style from two drafts. The vocabulary comes from the mark without copying it: where the subject is a GAME the icon carries the cartridge silhouette with its chamfered corner; where it is not, a conventional shape stands instead — sliders, padlock, bell. Discover is a magnifier whose lens carries the chamfer, because a cartridge with a separate magnifier would be two too-small things at 21 px. The #337 path was live and worse than assumed: `applyI18n` sets `textContent` and deletes children, and for `profile` and `nav_lists` the symbol lived only in the template, so 👤 and ⭐ were never visible at all — not after a language switch, but from load. Only 🚪 survived because it sat inside the translated string, which is why it had to come out of all five language files. Settings sub-entries deliberately get no icons: they are product names.*

*EN: only the cover badge is absolutely positioned (#698). Jens reported the play button sitting over the navigation bar. Measured with the detail card open: the button at (6, 6), its own slot `#mplay` at (892, 529) — 900 px away. The cause reached further than that one button: a second `.badge` rule further down restyles the detail badges with equal specificity and later position, winning for background, border, padding and font size — but it does not reset `position`. Only `position/top/left` survived from the first rule, and that applied everywhere: rating, year, developer, genres and the achievements row were all absolutely positioned. The rule is now scoped to `.cover` and contains nothing but the positioning; pulling the visual properties up with it would have silently restyled the cover badge, including its pill shape in Aurora.*

*EN: a card can no longer say "in library" and "platform unknown" at once (#685). `in_library()` falls back to a global check when the hit names no platform — correct, but it only answers whether. `library_slugs()` answers where, sorted by the platform's release year (oldest first), which for a title on several systems is almost always the one it appeared on first. Measured: 6.9% of titles sit on more than one platform. Deliberately the console's year, not the game's — IGDB gives one date per game and does not know the hacks and homebrew this concerns. The card marks the value as derived.*

*EN: four counts that get confused (#654), measured on 2026-08-15: **folders** — every platform directory including empty ones (`LIB["slugs"]`, 599); **platforms** — those with content (64); **entries** — the per-platform sum, where a title on two systems counts twice (323,776); **titles** — unique `norm()` keys (`LIB["all"]`, 293,067). The home page called entries "titles" and the log called folders "platforms", so two displays contradicted each other while every number was correct. Rule of thumb: `slugs` are folders, `per` are platforms, the sum of its lengths are entries, `all` are titles.*

*EN: the search row carries back and clear buttons (#661). Both appear only when they do something — back when `EIGENE_SCHRITTE > 0`, clear when the field holds text; a button that does nothing is indistinguishable from a broken one (#638). Clearing happens in exactly one function, `sucheLeeren(fokus)`, shared by the mark click (#662), the button and Escape: a second function of the same name briefly existed while building this, and the later definition wins silently. Escape has a fixed order — menu, dialog, then the field.*

*EN: the navigation changes axis — `#side` is a fixed left column by default and a top row only under Aurora and below 680px, so anything placed there is built for two layouts. The language picker and user menu sit at the END of the navigation since #672: right in the row, bottom in the column. Two measured traps: `margin-left:auto` shifts nothing in a column (264px of slack without `margin-top:auto`), and a menu opening downwards at the foot of a sidebar lands 106px below the viewport. The browser test measures both per theme.*

*EN: the navigation changes axis — `#side` is a fixed left column by default and a top row only under Aurora. The language picker and user menu therefore live in the search row in the markup and are moved into the navigation by `kopfrechtsPlatzieren()` **only under Aurora** (#672). Moving them in every theme would be the obvious wrong answer: elsewhere they would end up at the bottom of the left column, which is exactly where #206 took them from because nobody looks there. One node is moved, never a second copy (#632).*

*EN: four themes — `seerr`, `glass`, `clean`, `aurora` — selected through `data-design` on
the root element, each redefining the same variables. Three recurring traps: a theme is not
a single screen (check every view, cf. #636); the cascade decides rather than the intention
— `#setcontent button` and `#modal .row button` paint by ID, which outranks any class, so a
new button class has to name those contexts or it silently does nothing (#647); and a
gradient spanning two boxes is not one gradient. The Aurora glow used to live in
`#side::before` and `#buehne::before`, each clipped by its own `overflow:hidden`, which cut
it dead at the header edge (measured 84 and 76 colour units across the seam). Since #657 it
is a single `body::before` layer at `z-index:-1` with a transparent header. It has to
overhang the window because the animation shifts it by up to 3% of the width, it is only
clipped when `body` has `position:relative` **and** `html` has an `overflow-x` (either rule
alone leaves 97 resp. 101 px of horizontal scroll), and that clip must be `clip`, not
`hidden` — `hidden` turns body into a scroll container and the sticky search bar stops
sticking. Static checks cannot see any of this; the browser tests measure pixels.*

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
