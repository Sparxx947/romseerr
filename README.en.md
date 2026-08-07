# 🎮 Romseerr

[![CI](https://github.com/Sparxx947/romseerr/actions/workflows/ci.yml/badge.svg)](https://github.com/Sparxx947/romseerr/actions/workflows/ci.yml)
[![Security](https://github.com/Sparxx947/romseerr/actions/workflows/security.yml/badge.svg)](https://github.com/Sparxx947/romseerr/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

*Deutsch: [README.md](README.md)*

A **Seerr for ROMs** — a search, request and auto-download frontend for the
retro/console world, sorting into **RomM** and **RetroNAS**. Inspired by
Overseerr/Jellyseerr: a home page with popular games per console, detail pages,
a request workflow, user management and notifications.

> You are responsible for what you run. This repo contains **no** credentials —
> all secrets come from `.env`.

## Features

- **Home page with per-console rows** — popular games per major console (IGDB);
  clicking searches the title, scoped to that platform.
- **Search** over **Archive.org** (retro, direct download) and **Usenet**
  (Prowlarr → SABnzbd, modern consoles), with **platform pre-selection** and
  **dedup** against the existing library. Covers via IGDB (lazy-loaded for Usenet).
- **Detail view** — cover, description, file list, versions/sources.
- **Auto-import** — extract (`unar`), detect platform by file extension, sort into
  `/roms/<platform>/` (RomM & RetroNAS share the library).
- **User management** — login/first-run setup, roles (admin/user), per-user
  **auto-approve** and **approval workflow** (requests without auto-approve need admin approval).
- **Notifications** — Discord webhook configurable in the UI (with test).
- **i18n** — language switch for German, English, French, Spanish and Italian.
- **Designs** — three selectable looks (Seerr, Glass, Clean); admin sets the default, each user picks their own.
- **Sidebar** (Discover / Requests / Users / Settings) in Seerr style.

**Planned** (see [CHANGELOG](CHANGELOG.md) / issues): SQLite backend, user profile,
password reset via email, blocklist, issues/problems.

## Stack

Romseerr is the frontend; the surrounding stack does the work (SABnzbd, Prowlarr,
JDownloader, RomM). Architecture, data flow and components are documented in
**[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## Quick start

**Full stack** (Romseerr + SABnzbd + Prowlarr + JDownloader + RomM):

```bash
cp .env.example .env        # set values (paths, DB passwords, IGDB …)
docker compose up -d --build
# configure SABnzbd/Prowlarr -> put their API keys into .env -> `up -d` again
# Romseerr: http://<host>:8770  (create an admin on first visit)
```

**Romseerr only** (existing stack): use just the `romseerr` service in
`docker-compose.yml` and point its `.env` URLs at your hosts.

## API

Full documentation:

- **Interactive:** `http://<host>:8770/api/docs` (Redoc) · **Spec:** `/api/openapi.json`
- **Guide + auth (API key/session):** [`docs/API.md`](docs/API.md)
- **OpenAPI 3.1 in the repo:** [`docs/openapi.yaml`](docs/openapi.yaml)

Programmatic access via API key (header `X-Api-Key` or `?apikey=`), e.g.
`curl -H "X-Api-Key: $KEY" http://<host>:8770/api/jobs`.

## Stack components

| Service | Role | Port |
|---|---|---|
| Romseerr | search/request frontend | 8770 |
| SABnzbd | Usenet downloads (category `roms`) | 8080 |
| Prowlarr | indexer search (read-only) | 9696 |
| JDownloader | filehoster downloads | 5800 |
| RomM (+MariaDB) | library/player | 8998 |

Stack: Python 3.12 · Flask · aria2 · unar.
