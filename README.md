# 🎮 Romseerr

[![CI](https://github.com/Sparxx947/romseerr/actions/workflows/ci.yml/badge.svg)](https://github.com/Sparxx947/romseerr/actions/workflows/ci.yml)
[![Security](https://github.com/Sparxx947/romseerr/actions/workflows/security.yml/badge.svg)](https://github.com/Sparxx947/romseerr/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Beta](https://img.shields.io/badge/status-beta-orange.svg)](#projektstatus)

*English version: **[README.en.md](README.en.md)** · Wiki: **[Home](../../wiki)***

**Romseerr ist ein „Seerr" für ROMs** — eine Such-, Anfrage- und Auto-Download-Oberfläche
für die Retro- und Konsolenwelt, im Stil von Overseerr / Jellyseerr. Nutzer suchen Spiele,
stellen Anfragen, und Romseerr lädt sie über den umliegenden Stack herunter, entpackt sie,
sortiert sie in die Bibliothek ein und meldet sich, wenn sie verfügbar sind. Die Bibliothek
teilen sich **RomM** (Browser/Player) und **RetroNAS**.

> ⚠️ **Verantwortung & Recht:** Für den Betrieb und die Rechtmäßigkeit der beschafften Inhalte
> ist ausschließlich der Betreiber verantwortlich. Das Repository enthält **keinerlei
> Zugangsdaten** — alle Secrets kommen ausschließlich über `.env` bzw. die Einstellungsseite.

---

## Inhalt

- [Highlights](#highlights)
- [Funktionen im Detail](#funktionen-im-detail)
- [So funktioniert eine Anfrage](#so-funktioniert-eine-anfrage)
- [Der Stack](#der-stack)
- [Schnellstart](#schnellstart)
- [Ersteinrichtung](#ersteinrichtung)
- [Konfiguration](#konfiguration)
- [Benutzer, Rollen & Rechte](#benutzer-rollen--rechte)
- [Benachrichtigungen](#benachrichtigungen)
- [Designs & Sprachen](#designs--sprachen)
- [API](#api)
- [Versionen: aktualisieren und zurückgehen](#versionen-aktualisieren-und-zurückgehen)
- [Sicherheit](#sicherheit)
- [HTTPS & PWA](#https--pwa)
- [Entwicklung & Tests](#entwicklung--tests)
- [Projektaufbau](#projektaufbau)
- [Projektstatus](#projektstatus)
- [Lizenz](#lizenz)

---

## Was Romseerr ist — und was nicht

Romseerr ist **Werkzeug**: es sucht, fragt an, lädt herunter und sortiert ein.
Es **hostet keine Inhalte, beschafft keine und verlinkt keine**. Welche Quellen es
abfragt, trägt der Betreiber in den Einstellungen ein — nichts davon steht in
diesem Repository, und nichts ist voreingestellt.

Ebenso wenig enthält dieses Repository Emulatoren, BIOS-Abbilder, Firmware oder
Konsolen-Schlüssel. Emulatoren werden auf Wunsch von den **offiziellen
Projektquellen** geholt; Firmware und BIOS stammen aus **Hardware, die dir
gehört**. Ein CI-Lauf prüft das bei jedem Pull Request.

Die vollständige Regel steht in
[CONTRIBUTING](.github/CONTRIBUTING.md#was-hier-nicht-hineingehört).

## Highlights

- 🔍 **Suchen & Entdecken** über **Archive.org** und **Usenet** (Prowlarr → SABnzbd), mit
  Startseiten-Reihen je Konsole und Genre, Empfehlungen und Detailseiten (IGDB).
- ⬇️ **Anfrage → Download → Import → verfügbar** vollautomatisch, inkl. Entpacken,
  Plattform-Erkennung, **Dedup** und Einsortierung nach `/roms/<plattform>/`.
- 👤 **Mehrbenutzer** mit Rollen, **granularen Rechten**, **Auto-Freigabe**, **Kontingenten**
  und einem **Freigabe-Workflow** für Anfragen.
- ⭐ **Wunschliste mit Auto-Download**, **Sammel-Anfragen**, **Anfrage im Namen anderer**,
  **personalisierte Empfehlungen** und **Reihen-/Collection-Ansicht**.
- ✉️ **Nachrichten** zwischen Nutzern, **Problem-Meldungen** mit Kommentaren, **Sperrliste**.
- 🎨 **Drei wählbare Designs** (Seerr / Glas / Klar) und **fünf Sprachen** (DE/EN/FR/ES/IT).
- 🔔 **Benachrichtigungen** über Discord, Telegram, E-Mail, Gotify, ntfy, Pushover und **Web-Push (PWA)**.
- 🔑 **REST-API** mit API-Key und vollständiger **OpenAPI-3.1**-Doku (`/api/docs`).
- 🧩 **Ein einziges `app.py`** (Python 3.12 / Flask), **SQLite**-Persistenz, kein Build-Schritt,
  **non-root**-Container mit Healthcheck, Multi-Arch-Image (amd64 + arm64).

---

## Funktionen im Detail

### Suchen & Entdecken
- **Startseite** mit Reihen „Beliebt auf «Konsole»" und je Genre (IGDB), plus einer
  personalisierten Reihe **„Weil du … angefragt hast"** aus der eigenen Anfrage-Historie.
- **Suche** über zwei Quellen gleichzeitig: **Archive.org** (Retro, direkter Download) und
  **Usenet** (Prowlarr-Indexer → SABnzbd, v. a. moderne Konsolen). **Plattform-Vorauswahl**
  grenzt die Suche ein; eine reine Retro-Auswahl schaltet Usenet aus.
- **Dedup** gegen die bestehende Bibliothek: vorhandene Titel werden markiert und ans Ende
  sortiert; ein erneuter Download wird server- und clientseitig verhindert.
- **Cover** über IGDB (SteamGridDB als Fallback), für Usenet-Treffer lazy nachgeladen.

### Detailseite
- Cover, Beschreibung, Wertung, Jahr, Entwickler, Genres, **Screenshots**, **ähnliche Spiele**
  und die **Spielreihe/Collection** (Klick startet die Suche), Versionen/Quellen und Dateiliste.
- Direkt von hier: anfragen, **auf die Wunschliste setzen** oder ein **Problem melden**.

### Abdeckung

Die Seite ist nach **Hersteller** gruppiert (Nintendo, Sega, Sony, Microsoft, Sonstige) —
dieselbe Einteilung wie der Plattformfilter, nicht eine zweite Liste. Eine Herstellerkarte
klappt ihre Konsolen auf, jede mit Quelle und Stand wie bisher.

Die Zahl auf der Herstellerkarte ist **Summe besessen ÷ Summe bekannt**, nicht das Mittel
der Prozente — sonst zählte der Virtual Boy (16 Titel) so viel wie die SNES (2825). Die
Methode steht als `Σ` auf der Karte. Und weil **nicht jede Plattform eine Katalogquelle
hat**, steht dort auch „x von y Konsolen messbar": eine Zahl über einen Ausschnitt, ohne
das dazuzusagen, wäre irreführend.

### Logos — bewusst keine im Repo

Konsolen- und Herstellerlogos sind **Marken**. Romseerr liefert deshalb **kein einziges
Bild mit**. Wer welche zeigen will, legt sie selbst ab:

```
<config>/logos/snes.png        # Dateiname = Plattform-Slug
<config>/logos/nintendo.svg    # oder Herstellergruppe, kleingeschrieben
```

Erlaubt sind `png`, `svg`, `webp`, `jpg`. Liegt keine Datei da, steht der **Name** dort —
das ist der Normalfall und vollständig so, kein Notbehelf.

### Anfragen & Download
- **Anfrage-Workflow**: Nutzer mit Auto-Freigabe laden sofort; sonst muss ein Admin freigeben.
- **Sammel-Anfrage** („Alle anfragen") fordert alle noch nicht vorhandenen Treffer auf einmal an.
- **Anfrage im Namen eines anderen Nutzers** (für Admins).
- **Wunschliste**: Titel vormerken, auch wenn es noch keine Quelle gibt — ein Hintergrund-Worker
  sucht periodisch nach und lädt automatisch, sobald etwas Passendes auftaucht (strenger
  Titel-Abgleich gegen Fehlgriffe). Die Liste lässt sich auch **aus einer Liste oder Datei
  einspielen** (TXT/CSV, ein Titel je Zeile, optional `Titel;Plattform`) — mit **Vorschau**
  vor dem Schreiben: getroffen / mehrdeutig / nicht gefunden. Eine **Beispieldatei** im
  erwarteten Format gibt es im Dialog (bzw. unter `/api/wishlist/example.csv`).
- 📺 **Stream** für die Plattformen, die der Browser **nicht** emulieren kann (PS2, GameCube,
  Wii, Switch): der Emulator läuft auf einem Streaming-Host, der Browser bekommt Bild und Ton.
  Romseerr emuliert nichts und liefert weder Emulator noch Firmware aus — es löst einen Titel
  auf eine Datei auf und bittet den Host, sie zu starten. **Einzelplatz**: eine Sitzung
  gleichzeitig, mit Namen des Belegers, Ablauf und ausdrücklichem Beenden. Der schlanke
  komplette Streaming-Host liegt als **`contrib/streaming-host/`** bei (Compose,
  Init-Skripte, Start-Dienst, Doku) und ist ohne fremde Umgebung nachbaubar.
  **Ton und Gamepad brauchen dort HTTPS** — über HTTP verweigert der Browser die
  WebCodecs-API, und beides bleibt still, ohne dass ein Fehler erscheint.
- ▶ **Play im Browser**: liegt der Titel in RomM und gibt es für die Plattform einen
  EmulatorJS-Kern, führt ein Knopf auf der Detailseite direkt in RomMs eingebauten Spieler.
  Romseerr emuliert selbst nichts. **PS2, GameCube, Wii, Dreamcast und Switch zeigen den Knopf
  nie** — dafür existiert kein Kern und wird keiner existieren. Jede Absage nennt ihren Grund
  (nicht in der Bibliothek, zu groß für den Browser, keine RomM-Verbindung); BIOS-Bedarf und
  die Romset-Eigenheit von Arcade stehen vorher da, nicht erst vor einem schwarzen Bild.
- 📦 **Filehoster-Weg (experimentell)**: ein generischer **Katalog-JSON-Indexer** im
  verbreiteten Format `{name, downloads:[{title, uris, uploadDate, fileSize}]}`. **Romseerr
  liefert nur den Parser — die Quell-URLs trägt der Betreiber unter Einstellungen →
  Verbindungen ein, im Repo steht keine.** Die URIs werden aufgeteilt: direktes HTTP lädt
  Romseerr selbst, Filehoster gehen als `.crawljob` an JDownloader, `magnet:` bleibt außen vor.
  Kataloge haben eine TTL und zeigen ihren Stand — Linkfäule ist hier der Normalfall, und ein
  toter Link endet als klarer Job-Fehler statt als Dauerhänger.
- **Anfrage-Verlauf** je Nutzer mit Zeitstempel (für Admins pro Nutzer filterbar), inklusive
  der **gelieferten Fassung**.
- 🏷 **Fassungen (Region/Revision/Sprache)**: Romseerr liest die üblichen Namenskonventionen
  (No-Intro, Redump, TOSEC, GoodTools) und gruppiert die Kandidaten auf der Detailseite nach
  Fassung statt roher Release-Namen. **Voreinstellung je Nutzer** (Regionsreihenfolge,
  bevorzugte Sprache, Beta/Prototyp zulassen) mit **instanzweitem Rückfall** in den
  Einstellungen. Region ändert Inhalt (Sprache, Schwierigkeit, Zensur, 50/60 Hz) — das ist
  **keine Qualitätsleiter**, deshalb wird nach der eingestellten Reihenfolge gewählt, nicht
  sortiert. Was im Namen nicht steht, bleibt **unspezifiziert** und wird nie geraten.
- 🏆 **RetroAchievements** auf der Detailseite: Anzahl der Achievements, Punkte und Link zum
  Set; mit hinterlegtem Konto (Profil) zusätzlich der eigene Fortschritt. Dazu ein Suchfilter
  „nur mit Achievements". Rein schmückend — **ohne Key oder bei Ausfall verschwindet der
  Abschnitt, es erscheint kein Fehler.** Die Zuordnung läuft über die vorab geholte Set-Liste
  je Konsole und verlangt einen **exakten** Titeltreffer; mehrdeutige Treffer werden verworfen,
  weil eine falsche Zuordnung schlimmer ist als gar keine.
- 📊 **Abdeckung je Plattform**: „412 von 1.180" — und ein Klick öffnet die **fehlenden**
  Titel (paginiert, filterbar, per Sammelauswahl auf die Wunschliste). Grundlage ist eine
  Momentaufnahme aus IGDB; **Quelle und Stand stehen an jeder Zahl**, denn Metadatensätze
  sind sich uneins, was als eigener Titel zählt. Plattformen ohne Momentaufnahme zeigen das
  an, statt „0 %" zu behaupten.
- **Export/Import der Konfiguration** (Einstellungen → Logs & Wartung): versioniertes JSON mit
  Einstellungen, Benutzern & Rechten, Anfragen und Wunschlisten. Geheimnisse bleiben ohne
  Passphrase draußen, mit Passphrase liegen sie verschlüsselt bei. Beim Import ist
  `Zusammenführen` oder `Ersetzen` ausdrücklich zu wählen.

### Import
- Entpacken mit `unar`, **Plattform-Erkennung** an der Dateiendung, **Dedup** und Einsortierung
  nach `/roms/<plattform>/` (RomM & RetroNAS teilen sich diese Bibliothek), danach optionaler
  **RomM-Scan**. Es werden **nur bekannte ROM-/Disk-Endungen** importiert — Nicht-ROM-Dateien
  (Emulatoren, `.exe`/`.dll`, Assets) werden übersprungen; enthält ein Item keine ROM, endet die
  Anfrage sauber als Fehler statt die Bibliothek zu vermüllen.
- In **SABnzbd/JDownloader** erscheint der Download unter dem **ROM-Titel**; nach dem Import
  wird der erledigte Download dort **automatisch entfernt**.

### Verwaltung
- **Einstellungen** mit Unterbereichen: Allgemein, Benachrichtigungen, Benutzer, Verbindungen,
  Sperrliste, Dienste, Logs & Wartung, HTTPS, Über.
- **Verbindungen** (SABnzbd/Prowlarr/IGDB/RomM …) komplett über die Weboberfläche konfigurierbar,
  Secrets maskiert, Klartext-Anzeige auf Wunsch. Leere Felder fallen auf die `.env`-Werte zurück.
- **Erststart-Assistent**, der beim ersten Aufbau Schritt für Schritt durch die Dienste führt.

---

## So funktioniert eine Anfrage

```
Suche ──► Treffer (Archive / Usenet)
             │  Anfrage (ggf. Admin-Freigabe)
             ▼
   ┌─────────────────────────────────────────────┐
   │ Archive.org  → aria2 lädt direkt             │
   │ Usenet       → SABnzbd lädt die NZB          │
   │ Filehoster*  → .crawljob für JDownloader     │
   └─────────────────────────────────────────────┘
             │  fertige Dateien
             ▼
   Entpacken (unar) → nur ROM-Endungen → Dedup →
   Einsortieren /roms/<plattform>/ → Index/RomM-Scan →
   „verfügbar" + Benachrichtigung  (Download aus SAB/JD entfernt)
```

\* **Filehoster ist experimentell** (siehe [Projektstatus](#projektstatus) / Issue #63):
der Code-Weg existiert, aber es ist noch keine Quelle verdrahtet, die Filehoster-Treffer liefert.

---

## Der Stack

Romseerr ist nur die **Oberfläche**; die eigentliche Arbeit erledigt der umliegende Stack.
Architektur, Datenfluss und Komponenten sind ausführlich in
**[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** beschrieben.

| Dienst | Rolle | Port (Standard) |
|---|---|---|
| **Romseerr** | Such-/Anfrage-Oberfläche, Import, Benachrichtigung | 8770 (HTTP) · 8443 (HTTPS, optional) |
| **SABnzbd** | Usenet-Downloads (Kategorie `roms`) | 8080 |
| **Prowlarr** | Indexer-Suche (nur lesend) | 9696 |
| **JDownloader** | Filehoster-Downloads (experimentell) | 5800 |
| **RomM** (+ MariaDB) | Bibliothek / Browser-Player | 8998 |

Technik: **Python 3.12 · Flask · SQLite · aria2 · unar**. Kein Build-Schritt — das komplette
Frontend liegt als String in `app.py` und wird ohne Bundler ausgeliefert.

---

## Schnellstart

### Kompletter Stack (Romseerr + SABnzbd + Prowlarr + JDownloader + RomM)

```bash
git clone https://github.com/Sparxx947/romseerr.git && cd romseerr
cp .env.example .env          # Pfade, DB-Passwörter, IGDB-Keys … setzen
docker compose up -d --build
# SABnzbd (:8080) und Prowlarr (:9696) einrichten, deren API-Keys in .env eintragen
docker compose up -d          # erneut, damit Romseerr die Keys übernimmt
# Oberfläche: http://<host>:8770  → beim ersten Aufruf Admin anlegen
```

### Nur Romseerr (vorhandener Stack)

Betreibst du SABnzbd/Prowlarr/JDownloader/RomM bereits, brauchst du nur den Dienst
`romseerr` aus `docker-compose.yml` und zeigst dessen `.env`-URLs auf die vorhandenen Hosts.
Alternativ das fertige Image von der GitHub Container Registry:

```bash
docker run -d --name romseerr -p 8770:8770 \
  --env-file .env \
  -v /pfad/zur/rom-bibliothek:/roms \
  -v ./config:/config \
  ghcr.io/sparxx947/romseerr:latest
```

Der Container läuft **non-root** und bringt einen **Healthcheck** auf `/health` mit.

> **`/config` muss der uid 1000 gehören** (oder für sie beschreibbar sein) — das ist die
> Kennung, unter der das Abbild läuft. Passt sie nicht, startet Romseerr trotzdem,
> beantwortet jede Anfrage und meldet `healthy`, **speichert aber nichts**: keine Anfrage,
> keinen Job, keine Einstellung. Sichtbar wird das an `"storage": "ro"` in `/health`, einer
> Startwarnung und einem Hinweis in der Oberfläche. Prüfen: `docker exec romseerr id`,
> setzen: `chown -R 1000 ./config`.

---

## Ersteinrichtung

1. **Admin anlegen** — der erste Aufruf zeigt die Ersteinrichtung; danach ist die Registrierung
   geschlossen (weitere Nutzer legt der Admin an).
2. **Assistent** — führt durch die Dienste (SABnzbd, Prowlarr, IGDB, RomM); jeder Schritt lässt
   sich testen oder überspringen. Später jederzeit erneut über *Einstellungen → Über* aufrufbar.
3. **Verbindungen prüfen** — unter *Einstellungen → Verbindungen*; *Dienste* zeigt die Erreichbarkeit.
4. **Usenet-Weg prüfen** — *Einstellungen → Verbindungen → SABnzbd* misst Suche, Kategorie,
   Warteschlange und Einsammelordner einzeln durch, ohne etwas herunterzuladen. Die letzte
   Zeile zeigt Romseerrs und SABnzbds Sicht auf denselben Ordner: laufen sie auseinander,
   läuft der Download durch und wird nie eingesammelt.

---

## Konfiguration

Zwei Wege, die sich ergänzen — **die Weboberfläche hat Vorrang, `.env` ist der Fallback**:

- **Weboberfläche** — *Einstellungen → Verbindungen* (persistiert in SQLite, Secrets maskiert).
- **Umgebungsvariablen** (`.env`, siehe `.env.example`):

| Variable | Zweck |
|---|---|
| `ROMSEERR_CONFIG` | Konfig-/DB-Verzeichnis (Default `/config`) |
| `ROMSEERR_ROMS` | Ziel-Bibliothek (Default `/roms`) |
| `ROMSEERR_HTTPS` | `1` setzt das Session-Cookie auf `Secure` (hinter HTTPS/Proxy) |
| `ROMSEERR_WISH_INTERVAL` | Intervall des Wunschlisten-Workers in Sekunden (Default 1800) |
| `CATALOG_URLS` | Katalog-JSON-Quellen für den Filehoster-Weg (leer = inaktiv, s. u.) |
| `ROMSEERR_CATALOG_TTL` | Auffrischintervall der Kataloge in Sekunden (Default 21600) |
| `ROMSEERR_PLAY_MAX_MB` | Größengrenze für „Im Browser spielen" in MB (Default 2048) |
| `STREAM_URL` / `STREAM_LAUNCH` | Streaming-Host: Browser-URL und optionaler Start-Dienst |
| `ROMSEERR_STREAM_TTL` | Ablauf einer Streaming-Sitzung in Sekunden (Default 7200) |
| `SAB_URL` / `SAB_APIKEY` / `SAB_CAT` | SABnzbd-Anbindung |
| `PROW_URL` / `PROW_APIKEY` / `PROW_CATS` | Prowlarr-Anbindung |
| `IGDB_CLIENT_ID` / `IGDB_CLIENT_SECRET` | IGDB (Cover, Metadaten, Empfehlungen) |
| `ROMM_URL` / `ROMM_USER` / `ROMM_PASS` | RomM-Scan nach dem Import |
| `JD_DL_BASE` | Basis-Zielordner für JDownloader (Filehoster), **aus Sicht des JD-Containers** |
| `JD_WATCH` / `JD_OUT` | Romseerrs Sicht auf Übergabe- und Zielordner. `JD_OUT` leer = **aus `JD_DL_BASE` abgeleitet** |

> **JDownloader braucht die FolderWatch-Erweiterung** (*Einstellungen → Extension Modules*).
> Sie gehört nicht zur Grundinstallation; ohne sie wird der Übergabe-Ordner nie gelesen.
> Zum Format der `.crawljob` siehe `docs/ARCHITECTURE.md` — `autoStart`/`autoConfirm` sind
> `BooleanStatus` (`TRUE`).
>
> **JDownloader darf im Automatikbetrieb nichts fragen.** Steht *Default On Added Dupes
> Links Action* (oder die Offline-Variante) auf `ASK`, wartet beim ersten wiederholten
> oder toten Link ein **modaler Dialog**, den im Container niemand sieht — und alle
> folgenden Aufträge stauen sich dahinter.

Vollständige Liste und Standardwerte: **`.env.example`**.

---

## Adressen und Verlauf

Jede Ansicht hat eine Adresse, und ein Titel auch:

| Adresse | Ansicht |
|---|---|
| `#/discover` · `#/requests` · `#/settings` | Entdecken · Anfragen · Einstellungen |
| `#/issues` · `#/messages` · `#/coverage` | Probleme · Nachrichten · Abdeckung |
| `#/title/<quelle>/<ref>?v=…&t=…&p=…` | Detailfenster über der Ansicht `v` |
| `#/settings/<bereich>/<unterseite>` | z. B. `#/settings/notif/telegram` |

Damit tut der Browser von sich aus das Richtige: **Zurück** kehrt zur vorherigen Ansicht
zurück und schließt ein offenes Detailfenster, statt die Anwendung zu verlassen — auf dem
Telefon *ist* Zurück die Navigation. Ein **Neuladen** kommt dort heraus, wo man war, und
ein **Link** auf einen Titel lässt sich verschicken.

### Karten auf Entdecken und in der Suche

Jede Karte trägt oben links den **Plattformnamen** (»GameCube«, nicht `ngc`) und, wenn
zutreffend, unten ein Zustandsabzeichen:

| Abzeichen | Bedeutung | Aktionsfeld |
|---|---|---|
| ✓ grün | schon in der Bibliothek | *Details* — dort liegen Spielen und Streamen |
| ⏳ gelb | schon angefragt, noch nicht da | abgeschaltet, damit niemand doppelt anfragt |
| keins | weder noch | *Download* |

Das Symbol trägt die Bedeutung, die Farbe verstärkt sie nur — auf einem dunklen Cover
sagt Grün allein einem rot-grün-blinden Menschen nichts. **Nichts wird ausgeblendet:**
Zu wissen, dass ein Titel schon da ist, ist nützlich; er soll nur nicht mehr gelesen
werden müssen.

### Anfragen

Über der Liste stehen fünf Filter mit **Zahlen** — *Alle*, *aktiv*, *erledigt*,
*abgelehnt*, *fehlgeschlagen* —, und bei mehreren Nutzern zusätzlich der Nutzerfilter;
beide greifen zusammen. Die Seite sagt damit, was sie enthält, ohne dass man sie
durchklickt.

**Abgelehnt ist eine eigene Gruppe**, weder *erledigt* noch *fehlgeschlagen*: Unter
*fehlgeschlagen* würde man nach Defekten suchen und Entscheidungen finden; unter
*erledigt* wäre es zwar richtig einsortiert, aber nicht mehr auffindbar.

In der Navigation trägt *Anfragen* einen **Zähler** der unerledigten Aufträge: laufende
**und** fehlgeschlagene. Ein Fehlschlag fällt bewusst nicht heraus — sonst lernt man,
dass Null „alles gut" heißt, während etwas ungelöst liegen bleibt. Die Farbe trennt beides
(rot bei Fehlern). Bei Null verschwindet der Zähler ganz, und gezählt werden die
**eigenen** Aufträge, auch für Verwalter — sonst stünde dort nie eine Null.

### Bewertungen und Kommentare

Die Karten auf *Entdecken* tragen die **IGDB-Bewertung** — mit Quelle beschriftet, weil
eine nackte Zahl sonst als die eigene gelesen wird. Ohne Wert steht dort nichts.

In der Detailansicht kommt die **eigene** Bewertung dazu (1–5 Sterne, zurücknehmbar) und
ein Kommentarbereich. Bewertet wird der **Titel**, nicht die einzelne Fassung — die
Bibliothek hält mehrere Fassungen desselben Spiels, die Meinung gilt dem Spiel. Und sie
steht **je Person**: „deine Bewertung" vorn, die der anderen daneben. Ein Mittelwert aus
zwei Meinungen sagt weniger als beide nebeneinander.

### Meine Listen

Über das Benutzermenü oben rechts, Adresse `#/lists`. Zwei Listen, die man leicht
verwechselt — und die deshalb getrennt bleiben:

| | Wunschliste | Favoriten |
|---|---|---|
| handelt von | Titeln, die du **nicht** hast | Titeln, die du **hast** |
| Zweck | daran denken, sie zu holen | schnell wiederfinden |
| endet | wenn der Titel eintrifft | nie |

Sie teilen sich **keinen** Speicher: Dass ein Eintrag die Wunschliste beim Eintreffen
verlässt, ist ihr Zweck — ein Favorit, der von selbst verschwindet, wäre ein Fehler. Ein
Titel darf in beiden stehen, in einer oder in keiner. Beides ist **je Benutzer**.

Vorher stand die Wunschliste unter *Anfragen*, hineingezeichnet in dieselbe Seite. Eine
Anfrage ist aber etwas, worauf das System eine Antwort schuldet — mit Zustand, mit Ende,
und für Verwalter über alle Nutzer sichtbar. Eine Wunschliste ist das Gegenteil.

### Fußzeile

Unten am Fenster angeheftet und mittig: Name, **laufende Version** (verlinkt auf ihren
Release), **GitHub** und der **kurze Commit**. Der Commit ist der Teil, der einen
`dev`-Bau von dem Release unterscheidet, dessen Nummer er trägt — beide melden dieselbe
Version. Wurde ein Abbild ohne Bau-Argumente erzeugt, steht dort zusätzlich ⚠.

Damit trägt jeder Bildschirmauszug seinen Stand, ohne dass jemand danach fragen muss.
**Ohne Anmeldung** erscheint nur der Repo-Link: eine Versionsnummer auf der Anmeldeseite
sagt einem Fremden, welche Lücken er nachschlagen kann.

### Kopfleiste

Oben rechts stehen **Sprache** und **Person**: die Sprache als Aufklappmenü (eingeklappt
die Flagge, in der Liste Flagge **und** Eigenname — eine Flagge allein ist ein Land, keine
Sprache), daneben Name und Bild mit einem Menü für *Profil* und *Abmelden*. Beide Menüs
schließen per Klick daneben und mit Escape. Die Seitenleiste trägt nur noch die Navigation.

### Einstellungen

Das Bereichsmenü liegt **oben**, damit die Formulare die volle Breite bekommen — sie
enthalten URLs und Schlüssel. **Benachrichtigungen** und **Verbindungen** haben eine
zweite Zeile mit *einer Seite je Verfahren bzw. Dienst*: Telegram einrichten heißt nicht
mehr, an Discord vorbeizuscrollen. Jeder Eintrag zeigt seinen Stand — gefüllter Punkt
*aktiv*, offener Punkt *eingerichtet, aber aus*, kein Punkt *nicht eingerichtet*.

Gespeichert wird immer nur, was auf der Seite steht; die übrigen Verfahren bleiben
unberührt.

---

## Benutzer, Rollen & Rechte

- **Rollen:** `admin` (alles) und `user`. Zusätzlich **granulare Rechte**:
  `request`, `autoapprove`, `manage_requests`, `manage_users`, `manage_issues`,
  `manage_settings`, `quota_exempt`.
- **Sichtbarkeit:** Nutzer sehen **nur ihre eigenen** Anfragen und Problem-Meldungen;
  wer `manage_requests`/`manage_issues` hat, sieht alle.
- **Kein Rechteausbruch:** Die Admin-Rolle und die privilegierten Rechte
  (`manage_users`/`manage_settings`) darf **nur ein echter Admin** vergeben.
- **Kontingente (Quotas):** X Anfragen je Y Tage, mit Ausnahme-Recht `quota_exempt`.

---

## Benachrichtigungen

In der Oberfläche konfigurierbar (jeweils mit Testknopf):
**Discord**, **Telegram**, **E-Mail (SMTP)**, generischer **Webhook**, **Gotify**, **ntfy**,
**Pushover** sowie **Web-Push** (PWA, benötigt HTTPS). Jeder Nutzer kann zusätzlich einen
**persönlichen Discord-Webhook** hinterlegen. Passwort-Reset läuft per E-Mail.

---

## Designs & Sprachen

- **Designs:** drei wählbare Looks — **Seerr** (dunkel, poliert), **Glas** (Glassmorphism,
  Farbverlauf + Blur), **Klar** (flach, minimal). Der Admin setzt den Standard, jeder Nutzer
  wählt im Profil ein eigenes. Eigene Designs lassen sich leicht ergänzen — siehe die Wiki-Seite
  **[Designs / Themes](../../wiki/Designs)**.
- **Sprachen:** Deutsch, Englisch, Französisch, Spanisch, Italienisch (Umschalter in der Seitenleiste).

---

## API

- **Interaktiv:** `http://<host>:8770/api/docs` (Redoc) · **Spec:** `/api/openapi.json`
- **Anleitung + Auth:** [`docs/API.md`](docs/API.md) · **OpenAPI 3.1 im Repo:** [`docs/openapi.yaml`](docs/openapi.yaml)

Programmatischer Zugriff per **API-Key** (Header `X-Api-Key` oder `?apikey=`), admin-äquivalent:

```bash
curl -H "X-Api-Key: $KEY" http://<host>:8770/api/jobs
```

Der Schlüssel wird unter *Einstellungen → Allgemein* erzeugt und kann dort rotiert werden.

---

## Versionen: aktualisieren und zurückgehen

*Versions: updating, and going back*

Jeder Release hinterlässt **drei** Dinge, die dasselbe bezeichnen und Verschiedenes können:

| | wofür | änderbar |
|---|---|---|
| Abbild `ghcr.io/sparxx947/romseerr:1.1.0-beta.1` | ein Container, der **zieht** | nein |
| Git-Tag `v1.1.0-beta.1` | ein Bau **aus dem Quelltext** | nein — Tags sind unveränderlich |
| Zweig `release/v1.1.0-beta.1` | ein Bau aus dem Quelltext | **ja** — hierhin darf eine nachgezogene Korrektur |

**Eine andere Version fahren** heißt für einen ziehenden Container: die Marke am Abbild
ändern, mehr nicht.

```yaml
services:
  romseerr:
    image: ghcr.io/sparxx947/romseerr:1.0.0-beta.1   # statt :1.1.0-beta.1
```

`latest` zeigt bewusst **nie** auf ein Pre-Release. Wer Betas will, trägt sie namentlich ein.

**Aus dem Quelltext bauen** — so läuft die Referenzinstallation, und so kommt die Instanz
zu einer belastbaren Auskunft über sich selbst:

```bash
git checkout release/v1.1.0-beta.1        # oder: git checkout v1.1.0-beta.1
docker build -t romseerr:local \
  --build-arg "ROMSEERR_COMMIT=$(git rev-parse --short HEAD)" \
  --build-arg "ROMSEERR_BUILT_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)" .
```

**Ohne die beiden Argumente** meldet `/api/version` weder Commit noch Bauzeitpunkt, und
die Frage „läuft das, was im Repo steht?" ist wieder Ratesache — genau der Fall, der
einmal einen Arbeitstag gekostet hat. Nach dem Ausrollen prüfen:

```bash
curl -s http://<host>:8770/api/version
{"version":"1.1.0-beta.1","commit":"24a331e","built_at":"…","provenance":"build"}
```

Meldet `provenance` etwas anderes als `build`, wurde ohne diese Angaben gebaut.

**Was ein alter Stand nicht verspricht:** Er ist erreichbar, nicht garantiert lauffähig.
Abhängigkeiten können sich nicht mehr auflösen, und ein einmal migrierter Datenbestand
passt womöglich nicht mehr zu einer älteren Fassung. Vor einem Rücksprung die Daten sichern.

*Every release leaves three things: an image tag for a container that pulls, an immutable
git tag, and a `release/…` branch that can take a backport. Changing the image tag is all
a pulling container needs; `latest` never points at a pre-release. When building from
source, pass `ROMSEERR_COMMIT` and `ROMSEERR_BUILT_AT` — without them `/api/version`
cannot say what it is running. An older state is reachable, not guaranteed to run: back up
the data before going back.*

---

## Sicherheit

- **Session-Cookie** signiert, `HttpOnly`, `SameSite=Strict`; `Secure` via `ROMSEERR_HTTPS=1`.
  Der Signierschlüssel wird persistent unter `config/secret.key` gehalten.
- **Login-Rate-Limit** (Fehlversuche je IP+Nutzer im Zeitfenster → HTTP 429).
- **API-Key** wird in konstanter Zeit verglichen.
- **Keine Secrets im Repo** — `.gitignore` schließt `.env`, `config/` und `*.db*` aus;
  CI prüft mit **Gitleaks**, **Trivy**, **Bandit** und **CodeQL**.

---

## HTTPS & PWA

- **HTTPS** ohne separaten Reverse-Proxy: unter *Einstellungen → HTTPS* ein Zertifikat + Schlüssel
  (PEM) hinterlegen; die App startet dann zusätzlich einen HTTPS-Listener (Neustart nötig).
- **PWA**: installierbar, mit Service-Worker und **Web-Push** (benötigt HTTPS).

---

## Entwicklung & Tests

```bash
pip install -r requirements.txt pytest pyyaml
pytest -q                     # Tests laufen gegen temporäre Verzeichnisse, nie gegen echte Daten
python scripts/build_openapi.py   # docs/openapi.yaml aus der OPENAPI-Spec erzeugen
```

- Datenpfade über `ROMSEERR_CONFIG` / `ROMSEERR_ROMS`; für einen echten Lauf `cp .env.example .env`.
- Das **Frontend** liegt in `static/` und `templates/`; die Tests prüfen u. a., dass jede
  JavaScript-Datei von Node **geparst** wird und die **OpenAPI-Spec alle Routen** abdeckt.

### Aus dem Quellstand bauen / building from source

```bash
docker build -t romseerr:local \
  --build-arg ROMSEERR_COMMIT="$(git rev-parse --short HEAD)" \
  --build-arg ROMSEERR_BUILT_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" .
```

**Die beiden Build-Argumente sind kein Beiwerk.** Ohne sie meldet `/api/version` nur
`{"commit": null}` — und das sieht aus wie eine Antwort, ist aber die Abwesenheit einer.
Eine Instanz kann dann nicht sagen, ob sie dem Quellstand entspricht; genau so lief hier
ein Container einen ganzen Arbeitstag mit dem Stand vom Vortag, ohne dass es auffiel.
Fehlen sie, sagt Romseerr das in den Einstellungen ausdrücklich.

*Without those two build args an instance cannot say whether it matches the source, and
`{"commit": null}` reads like an answer while being the absence of one.*

### Zweige / branches

| Zweig | Inhalt |
|---|---|
| **`dev`** | Entwicklungsstand, Standardzweig — hierhin gehen alle Pull Requests |
| **`main`** | **genau der aktuelle Release** — wird vom Release-Lauf vorgespult, nie von Hand |

Wer eine **stabile Fassung** will, nimmt `main` oder einen Tag. Wer **mitentwickelt oder den
neuesten Stand** braucht, nimmt `dev`. Einzelheiten samt Release-Ablauf:
[`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md).

*Want a stable checkout? Use `main` or a tag. Want the newest state? Use `dev`.*
- Beiträge willkommen — siehe [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md),
  [`.github/CODE_OF_CONDUCT.md`](.github/CODE_OF_CONDUCT.md) und [`.github/SECURITY.md`](.github/SECURITY.md).
- Ausführliche Doku im **[Wiki](../../wiki)**.

---

## Projektaufbau

```
app.py                Backend + komplettes Frontend (ein File, kein Build-Schritt)
Dockerfile            non-root Image (USER 1000) + Healthcheck
docker-compose.yml    Referenz-Stack (Romseerr + SAB + Prowlarr + JDownloader + RomM)
.env.example          alle Konfigurationswerte
requirements.txt      Flask, requests, pywebpush
scripts/              build_openapi.py
tests/                pytest (Smoke, i18n-JS, OpenAPI-Abdeckung, Rechte, Import …)
docs/                 API.md, ARCHITECTURE.md, openapi.yaml
.github/              CI/Security/Release-Workflows, Issue-/PR-Vorlagen, Community-Dateien
```

---

## Projektstatus

**Beta.** Der Kern ist vollständig und getestet: Suche/Discover, Anfrage-Workflow, der
**Archive.org**- und **Usenet**-Downloadweg (end-to-end verifiziert, inkl. Import, SAB-Titel und
Auto-Cleanup), Benutzer/Rechte/Quotas, Wunschliste, Nachrichten, Probleme, Designs, i18n, PWA und API.

**Bekannte Einschränkung:** Der **Filehoster-Weg** (JDownloader) ist **experimentell** — der
Code existiert, aber es ist noch keine Quelle verdrahtet, die `source=filehoster`-Treffer liefert
([#63](../../issues/63)). Fortschritt und Ideen: [CHANGELOG](CHANGELOG.md) und die
[Issues](../../issues).

---

## Lizenz

[MIT](LICENSE). Romseerr ist ein privates, selbstgebautes Projekt und steht in keiner Verbindung
zu Overseerr, Jellyseerr, RomM oder RetroNAS.
