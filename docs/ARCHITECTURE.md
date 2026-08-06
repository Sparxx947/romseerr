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
| `JD_DL_BASE` | `/output/rom-suche` (Sicht des JD-Containers) | dito |

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

Aktuell JSON unter `/config` (`users.json`, `jobs.json`) plus RAM-Bibliotheksindex.
**Geplant:** Umstellung auf eingebettetes **SQLite** (u.a. persistenter
Bibliotheksindex, statt bei jedem Start zu re-scannen).
