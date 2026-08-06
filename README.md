# 🎮 rom-suche

Seerr-artige ROM-Suche & Auto-Download mit Einsortierung für **RomM** / **RetroNAS**.
Sucht parallel über **Archive.org** (Retro) und **Usenet** (Prowlarr → SABnzbd, moderne
Konsolen), lädt auf Knopfdruck herunter, entpackt, sortiert nach Plattform ein — und
bietet nur an, was **noch nicht in der Bibliothek** ist (Dedup).

> Hinweis: Für den Betrieb ist der Nutzer selbst verantwortlich. Das Repo enthält
> **keine** Zugangsdaten — alle Secrets kommen über `.env`.

## Funktionen

- **Weboberfläche** (Port 8770) mit Cover, Plattform-/Quelle-Badge, Größe, „Download"-Knopf
  und Download-Statusliste.
- **Zwei Suchquellen:**
  - **Archive.org** — titel-gebundene Such-API, direkter Download via `aria2` (Retro-ROMs,
    No-Intro/Redump/TOSEC). Rausch-Filter gegen Skins/Wallpaper/Quellcode.
  - **Usenet** — Prowlarr (nur lesend) für Console-Kategorien; Grabs laufen über eine
    **isolierte SABnzbd-Kategorie** (`roms`), damit Film-/Serien-Setups unberührt bleiben.
- **Plattform-Vorauswahl** — Systeme vorab als Chips wählen, damit die Suche nicht
  über alles läuft (Auswahl bleibt via `localStorage` erhalten). Usenet wird breit
  über *Console* abgefragt und nach Plattform nachgefiltert; reine Retro-Auswahl
  überspringt Usenet ganz.
- **Dedup** gegen die bestehende Bibliothek (normalisierter Titel je Plattform).
- **Plattform-Erkennung** an der Dateiendung beim Import (`.sfc`→snes, `.gba`→gba …).
- **Filehoster-Zweig** (optional) über JDownloader FolderWatch (`.crawljob`).

## Architektur

```
        ┌────────── Weboberfläche (Flask, :8770) ──────────┐
Suche → │  Archive.org-API            Prowlarr (usenet, ro) │
        └───────┬───────────────────────────┬──────────────┘
      Download  │                            │
                ▼                            ▼
        aria2 → /config/staging      SAB addurl (cat=roms)
                │                            │
                └──────► Import: entpacken (unar) → /roms/<plattform>/
                                   Dedup-Sperre · RomM-Scan
```

## Schnellstart

```bash
cp .env.example .env       # Werte eintragen (SAB/Prowlarr-Key, Pfade …)
docker compose up -d --build
# Oberfläche: http://<host>:8770
```

## Konfiguration

Alle Variablen siehe [`.env.example`](.env.example). Wichtig:

| Variable | Zweck |
|---|---|
| `SAB_URL` / `SAB_APIKEY` | SABnzbd für Usenet-Grabs |
| `SAB_CAT` | eigene Kategorie (Standard `roms`) — **nicht** movies/tv |
| `PROWLARR_URL` / `PROWLARR_APIKEY` | Usenet-Suche (nur lesend) |
| `IGDB_CLIENT_ID/SECRET` | optionale Cover für Usenet-Treffer |
| `ROMM_URL/USER/PASS` | optionaler RomM-Scan nach Import |
| `ROMS_LIB` | RomM-/RetroNAS-Bibliothek (Ziel + Dedup-Quelle) |

## Endpunkte

- `/` — Weboberfläche
- `GET /api/search?q=<titel>&platforms=<slug,slug>` — Suche (JSON), optional plattformgefiltert
- `GET /api/platforms` — verfügbare Plattformen (gruppiert, mit Usenet-Flag)
- `POST /api/download` — Download anstoßen (Body = Treffer-Objekt)
- `GET /api/jobs` — Download-Status
- `GET /health` — Health/Index-Größe

## Stack

Python 3.12 · Flask · aria2 · unar. Ein Container, self-contained.
