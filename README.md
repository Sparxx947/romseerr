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
- [Sicherheit](#sicherheit)
- [HTTPS & PWA](#https--pwa)
- [Entwicklung & Tests](#entwicklung--tests)
- [Projektaufbau](#projektaufbau)
- [Projektstatus](#projektstatus)
- [Lizenz](#lizenz)

---

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
- **Anfrage-Verlauf** je Nutzer mit Zeitstempel (für Admins pro Nutzer filterbar).
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

---

## Ersteinrichtung

1. **Admin anlegen** — der erste Aufruf zeigt die Ersteinrichtung; danach ist die Registrierung
   geschlossen (weitere Nutzer legt der Admin an).
2. **Assistent** — führt durch die Dienste (SABnzbd, Prowlarr, IGDB, RomM); jeder Schritt lässt
   sich testen oder überspringen. Später jederzeit erneut über *Einstellungen → Über* aufrufbar.
3. **Verbindungen prüfen** — unter *Einstellungen → Verbindungen*; *Dienste* zeigt die Erreichbarkeit.

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
| `SAB_URL` / `SAB_APIKEY` / `SAB_CAT` | SABnzbd-Anbindung |
| `PROW_URL` / `PROW_APIKEY` / `PROW_CATS` | Prowlarr-Anbindung |
| `IGDB_CLIENT_ID` / `IGDB_CLIENT_SECRET` | IGDB (Cover, Metadaten, Empfehlungen) |
| `ROMM_URL` / `ROMM_USER` / `ROMM_PASS` | RomM-Scan nach dem Import |
| `JD_DL_BASE` | Basis-Zielordner für JDownloader (Filehoster) |

Vollständige Liste und Standardwerte: **`.env.example`**.

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
- Das **Frontend** liegt als String in `app.py`; die Tests prüfen u. a., dass jeder Inline-`<script>`
  von Node **geparst** wird und die **OpenAPI-Spec alle Routen** abdeckt.
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
