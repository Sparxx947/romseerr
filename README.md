# 🎮 Romseerr

[![CI](https://github.com/Sparxx947/romseerr/actions/workflows/ci.yml/badge.svg)](https://github.com/Sparxx947/romseerr/actions/workflows/ci.yml)
[![Security](https://github.com/Sparxx947/romseerr/actions/workflows/security.yml/badge.svg)](https://github.com/Sparxx947/romseerr/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

*English: [README.en.md](README.en.md)*

Ein **Seerr für ROMs** — Such-, Anfrage- und Auto-Download-Oberfläche für die
Retro-/Konsolenwelt, mit Einsortierung für **RomM** und **RetroNAS**. Angelehnt an
Overseerr/Jellyseerr: Startseite mit beliebten Spielen je Konsole, Detailseiten,
Anfrage-Workflow, Benutzerverwaltung und Benachrichtigungen.

> Für den Betrieb ist der Nutzer selbst verantwortlich. Das Repo enthält **keine**
> Zugangsdaten — alle Secrets kommen über `.env`.

## Funktionen

- **Startseite mit Konsolen-Reihen** — beliebte Spiele je wichtiger Konsole (IGDB),
  Klick sucht den Titel plattform-scoped.
- **Suche** über **Archive.org** (Retro, direkter Download) und **Usenet** (Prowlarr →
  SABnzbd, moderne Konsolen), mit **Plattform-Vorauswahl** und **Dedup** gegen die
  bestehende Bibliothek. Cover via IGDB (für Usenet lazy nachgeladen).
- **Detail-Ansicht** — Cover, Beschreibung, Dateiliste, Versionen/Quellen.
- **Auto-Import** — entpacken (`unar`), Plattform an der Dateiendung erkennen,
  einsortieren nach `/roms/<plattform>/` (RomM & RetroNAS teilen sich die Bibliothek).
- **Benutzerverwaltung** — Login/Ersteinrichtung, Rollen (admin/user), **Auto-Freigabe**
  je Benutzer und **Freigabe-Workflow** (Anfragen ohne Auto-Freigabe muss der Admin bestätigen).
- **Benachrichtigungen** — Discord-Webhook in der Oberfläche konfigurierbar (mit Test).
- **Mehrsprachig** — Umschalter Deutsch/Englisch (i18n).
- **Seitenmenü** (Entdecken / Anfragen / Benutzer / Einstellungen) im Seerr-Stil.

**Geplant** (siehe [CHANGELOG](CHANGELOG.md) / Issues): SQLite-Backend, i18n de/en,
Benutzerprofil, Passwort-Reset per E-Mail, Sperrliste, Probleme/Issues.

## Stack

Romseerr ist die Oberfläche; die Arbeit erledigt der umliegende Stack (SABnzbd,
Prowlarr, JDownloader, RomM). Architektur, Datenfluss und Komponenten sind
ausführlich in **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** beschrieben.

## Schnellstart

**Kompletter Stack** (Romseerr + SABnzbd + Prowlarr + JDownloader + RomM):

```bash
cp .env.example .env        # Werte setzen (Pfade, DB-Passwörter, IGDB …)
docker compose up -d --build
# SABnzbd/Prowlarr einrichten -> deren API-Keys in .env -> erneut `up -d`
# Romseerr: http://<host>:8770  (beim ersten Aufruf Admin anlegen)
```

**Nur Romseerr** (bestehender Stack): im `docker-compose.yml` nur den Dienst
`romseerr` verwenden und dessen `.env`-URLs auf die vorhandenen Hosts zeigen.

## API

Vollständige Dokumentation:

- **Interaktiv:** `http://<host>:8770/api/docs` (Redoc) · **Spec:** `/api/openapi.json`
- **Anleitung + Auth (API-Key/Session):** [`docs/API.md`](docs/API.md)
- **OpenAPI 3.1 im Repo:** [`docs/openapi.yaml`](docs/openapi.yaml)

Programmatischer Zugriff per API-Key (Header `X-Api-Key` oder `?apikey=`), z. B.
`curl -H "X-Api-Key: $KEY" http://<host>:8770/api/jobs`.

## Stack-Komponenten (Kurz)

| Dienst | Rolle | Port |
|---|---|---|
| Romseerr | Such-/Anfrage-Oberfläche | 8770 |
| SABnzbd | Usenet-Downloads (Kategorie `roms`) | 8080 |
| Prowlarr | Indexer-Suche (nur lesend) | 9696 |
| JDownloader | Filehoster-Downloads | 5800 |
| RomM (+MariaDB) | Bibliothek/Player | 8998 |

Stack: Python 3.12 · Flask · aria2 · unar.
