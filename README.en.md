# 🎮 Romseerr

[![CI](https://github.com/Sparxx947/romseerr/actions/workflows/ci.yml/badge.svg)](https://github.com/Sparxx947/romseerr/actions/workflows/ci.yml)
[![Security](https://github.com/Sparxx947/romseerr/actions/workflows/security.yml/badge.svg)](https://github.com/Sparxx947/romseerr/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Beta](https://img.shields.io/badge/status-beta-orange.svg)](#project-status)

*Deutsche Version: **[README.md](README.md)** · Wiki: **[Home](../../wiki)***

**Romseerr is a "Seerr" for ROMs** — a search, request and auto-download front-end for the
retro/console world, in the style of Overseerr / Jellyseerr. Users search for games, place
requests, and Romseerr downloads them through the surrounding stack, unpacks them, sorts them
into the library and notifies when they are available. The library is shared by **RomM**
(browser/player) and **RetroNAS**.

> ⚠️ **Responsibility & law:** the operator alone is responsible for running the software and for
> the legality of the obtained content. The repository contains **no credentials whatsoever** —
> all secrets come from `.env` or the settings page.

---

## Contents

- [Highlights](#highlights)
- [Features in detail](#features-in-detail)
- [How a request works](#how-a-request-works)
- [The stack](#the-stack)
- [Quick start](#quick-start)
- [First run](#first-run)
- [Configuration](#configuration)
- [Users, roles & permissions](#users-roles--permissions)
- [Notifications](#notifications)
- [Designs & languages](#designs--languages)
- [API](#api)
- [Security](#security)
- [HTTPS & PWA](#https--pwa)
- [Development & tests](#development--tests)
- [Project layout](#project-layout)
- [Project status](#project-status)
- [License](#license)

---

## Highlights

- 🔍 **Search & discover** across **Archive.org** and **Usenet** (Prowlarr → SABnzbd), with
  home rows per console and genre, recommendations and rich detail pages (IGDB).
- ⬇️ **Request → download → import → available**, fully automatic, including unpacking,
  platform detection, **dedup** and sorting into `/roms/<platform>/`.
- 👤 **Multi-user** with roles, **granular permissions**, **auto-approve**, **quotas** and a
  request **approval workflow**.
- ⭐ **Wishlist with auto-download**, **bulk requests**, **request on behalf of others**,
  **personalized recommendations** and a **series/collection** view.
- ✉️ **Private messages** between users, **issue reports** with comments, a **blocklist**.
- 🎨 **Three selectable designs** (Seerr / Glass / Clean) and **five languages** (DE/EN/FR/ES/IT).
- 🔔 **Notifications** via Discord, Telegram, email, Gotify, ntfy, Pushover and **web push (PWA)**.
- 🔑 **REST API** with an API key and a full **OpenAPI 3.1** doc (`/api/docs`).
- 🧩 **A single `app.py`** (Python 3.12 / Flask), **SQLite** persistence, no build step,
  **non-root** container with healthcheck, multi-arch image (amd64 + arm64).

---

## Features in detail

### Search & discover
- **Home page** with rows "Popular on «console»" and per genre (IGDB), plus a personalized row
  **"Because you requested …"** built from your own request history.
- **Search** across two sources at once: **Archive.org** (retro, direct download) and **Usenet**
  (Prowlarr indexers → SABnzbd, mostly modern consoles). A **platform pre-selection** narrows the
  search; a retro-only selection disables Usenet.
- **Dedup** against the existing library: owned titles are flagged and sorted last; re-downloading
  is blocked both server- and client-side.
- **Covers** via IGDB (SteamGridDB fallback), lazily loaded for Usenet hits.

### Detail page
- Cover, description, rating, year, developer, genres, **screenshots**, **similar games** and the
  **series/collection** (click starts a search), versions/sources and file list.
- From here: request, **add to wishlist** or **report an issue**.

### Requests & downloads
- **Approval workflow**: users with auto-approve download immediately; otherwise an admin approves.
- **Bulk request** ("Request all") requests every not-yet-owned hit at once.
- **Request on behalf of another user** (for admins).
- **Wishlist**: watch titles even when no source exists yet — a background worker re-searches
  periodically and auto-downloads as soon as a matching source appears (strict title matching to
  avoid false positives).
- **Per-user request history** with timestamps (admins can filter by user).

### Import
- Unpacking with `unar`, **platform detection** by file extension, **dedup** and sorting into
  `/roms/<platform>/` (RomM & RetroNAS share this library), followed by an optional **RomM scan**.
  Only **known ROM/disk extensions** are imported — non-ROM files (emulators, `.exe`/`.dll`,
  assets) are skipped; if an item contains no ROM, the request ends cleanly as an error instead of
  polluting the library.
- In **SABnzbd/JDownloader** the download appears under the **ROM title**; after the import the
  finished download is **removed** there automatically.

### Administration
- **Settings** with sub-sections: general, notifications, users, connections, blocklist, services,
  logs & maintenance, HTTPS, about.
- **Connections** (SABnzbd/Prowlarr/IGDB/RomM …) fully configurable through the web UI, secrets
  masked, clear-text reveal on demand. Empty fields fall back to `.env`.
- A **first-run wizard** walks through the services on first setup.

---

## How a request works

```
Search ──► hit (Archive / Usenet)
             │  request (admin approval if needed)
             ▼
   ┌─────────────────────────────────────────────┐
   │ Archive.org  → aria2 downloads directly      │
   │ Usenet       → SABnzbd fetches the NZB       │
   │ Filehoster*  → .crawljob for JDownloader     │
   └─────────────────────────────────────────────┘
             │  finished files
             ▼
   Unpack (unar) → ROM extensions only → dedup →
   sort into /roms/<platform>/ → index/RomM scan →
   "available" + notification  (download removed from SAB/JD)
```

\* **Filehoster is experimental** (see [Project status](#project-status) / issue #63): the code path
exists, but no source that yields filehoster hits is wired up yet.

---

## The stack

Romseerr is only the **front-end**; the actual work is done by the surrounding stack. Architecture,
data flow and components are described in detail in **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

| Service | Role | Port (default) |
|---|---|---|
| **Romseerr** | search/request UI, import, notifications | 8770 (HTTP) · 8443 (HTTPS, optional) |
| **SABnzbd** | Usenet downloads (category `roms`) | 8080 |
| **Prowlarr** | indexer search (read-only) | 9696 |
| **JDownloader** | filehoster downloads (experimental) | 5800 |
| **RomM** (+ MariaDB) | library / browser player | 8998 |

Tech: **Python 3.12 · Flask · SQLite · aria2 · unar**. No build step — the entire front-end lives
as a string inside `app.py` and is served without a bundler.

---

## Quick start

### Full stack (Romseerr + SABnzbd + Prowlarr + JDownloader + RomM)

```bash
git clone https://github.com/Sparxx947/romseerr.git && cd romseerr
cp .env.example .env          # set paths, DB passwords, IGDB keys …
docker compose up -d --build
# set up SABnzbd (:8080) and Prowlarr (:9696), put their API keys into .env
docker compose up -d          # again, so Romseerr picks up the keys
# UI: http://<host>:8770  → create an admin on first visit
```

### Romseerr only (existing stack)

If you already run SABnzbd/Prowlarr/JDownloader/RomM, use just the `romseerr` service from
`docker-compose.yml` and point its `.env` URLs at your existing hosts. Or use the prebuilt image
from the GitHub Container Registry:

```bash
docker run -d --name romseerr -p 8770:8770 \
  --env-file .env \
  -v /path/to/rom-library:/roms \
  -v ./config:/config \
  ghcr.io/sparxx947/romseerr:latest
```

The container runs **non-root** and ships a **healthcheck** on `/health`.

---

## First run

1. **Create an admin** — the first visit shows the setup; afterwards registration is closed
   (the admin creates further users).
2. **Wizard** — walks through the services (SABnzbd, Prowlarr, IGDB, RomM); each step can be tested
   or skipped. Reopen it any time under *Settings → About*.
3. **Check connections** under *Settings → Connections*; *Services* shows reachability.

---

## Configuration

Two complementary ways — **the web UI takes precedence, `.env` is the fallback**:

- **Web UI** — *Settings → Connections* (persisted in SQLite, secrets masked).
- **Environment variables** (`.env`, see `.env.example`):

| Variable | Purpose |
|---|---|
| `ROMSEERR_CONFIG` | config/DB directory (default `/config`) |
| `ROMSEERR_ROMS` | target library (default `/roms`) |
| `ROMSEERR_HTTPS` | `1` marks the session cookie `Secure` (behind HTTPS/proxy) |
| `ROMSEERR_WISH_INTERVAL` | wishlist worker interval in seconds (default 1800) |
| `SAB_URL` / `SAB_APIKEY` / `SAB_CAT` | SABnzbd |
| `PROW_URL` / `PROW_APIKEY` / `PROW_CATS` | Prowlarr |
| `IGDB_CLIENT_ID` / `IGDB_CLIENT_SECRET` | IGDB (covers, metadata, recommendations) |
| `ROMM_URL` / `ROMM_USER` / `ROMM_PASS` | RomM scan after import |
| `JD_DL_BASE` | base target folder for JDownloader (filehoster) |

Full list and defaults: **`.env.example`**.

---

## Users, roles & permissions

- **Roles:** `admin` (everything) and `user`. Plus **granular permissions**:
  `request`, `autoapprove`, `manage_requests`, `manage_users`, `manage_issues`,
  `manage_settings`, `quota_exempt`.
- **Visibility:** users see **only their own** requests and issue reports; holders of
  `manage_requests`/`manage_issues` see all.
- **No privilege escalation:** only a real admin may grant the admin role or the privileged
  permissions (`manage_users`/`manage_settings`).
- **Quotas:** X requests per Y days, with a `quota_exempt` bypass.

---

## Notifications

Configurable in the UI (each with a test button): **Discord**, **Telegram**, **email (SMTP)**, a
generic **webhook**, **Gotify**, **ntfy**, **Pushover** and **web push** (PWA, needs HTTPS). Each
user can also set a **personal Discord webhook**. Password reset is done via email.

---

## Designs & languages

- **Designs:** three selectable looks — **Seerr** (dark, polished), **Glass** (glassmorphism,
  gradient + blur), **Clean** (flat, minimal). The admin sets the default, each user picks their own
  in the profile. Adding your own design is easy — see the wiki page
  **[Designs / Themes](../../wiki/Designs)**.
- **Languages:** German, English, French, Spanish, Italian (switcher in the sidebar).

---

## API

- **Interactive:** `http://<host>:8770/api/docs` (Redoc) · **Spec:** `/api/openapi.json`
- **Guide + auth:** [`docs/API.md`](docs/API.md) · **OpenAPI 3.1 in the repo:** [`docs/openapi.yaml`](docs/openapi.yaml)

Programmatic access via an **API key** (header `X-Api-Key` or `?apikey=`), admin-equivalent:

```bash
curl -H "X-Api-Key: $KEY" http://<host>:8770/api/jobs
```

The key is generated under *Settings → General* and can be rotated there.

---

## Security

- **Session cookie** signed, `HttpOnly`, `SameSite=Strict`; `Secure` via `ROMSEERR_HTTPS=1`.
  The signing key is kept persistently at `config/secret.key`.
- **Login rate limit** (failed attempts per IP+user within a window → HTTP 429).
- **API key** compared in constant time.
- **No secrets in the repo** — `.gitignore` excludes `.env`, `config/` and `*.db*`; CI runs
  **Gitleaks**, **Trivy**, **Bandit** and **CodeQL**.

---

## HTTPS & PWA

- **HTTPS** without a separate reverse proxy: under *Settings → HTTPS* provide a certificate + key
  (PEM); the app then also starts an HTTPS listener (restart required).
- **PWA**: installable, with a service worker and **web push** (needs HTTPS).

---

## Development & tests

```bash
pip install -r requirements.txt pytest pyyaml
pytest -q                     # tests run against temp directories, never real data
python scripts/build_openapi.py   # generate docs/openapi.yaml from the OPENAPI spec
```

- Data paths via `ROMSEERR_CONFIG` / `ROMSEERR_ROMS`; for a real run `cp .env.example .env`.
- The **front-end** lives as a string in `app.py`; the tests check, among other things, that every
  inline `<script>` **parses** under Node and that the **OpenAPI spec covers all routes**.
- Contributions welcome — see [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md),
  [`.github/CODE_OF_CONDUCT.md`](.github/CODE_OF_CONDUCT.md) and [`.github/SECURITY.md`](.github/SECURITY.md).
- Detailed docs in the **[wiki](../../wiki)**.

---

## Project layout

```
app.py                backend + full front-end (single file, no build step)
Dockerfile            non-root image (USER 1000) + healthcheck
docker-compose.yml    reference stack (Romseerr + SAB + Prowlarr + JDownloader + RomM)
.env.example          all configuration values
requirements.txt      Flask, requests, pywebpush
scripts/              build_openapi.py
tests/                pytest (smoke, i18n JS, OpenAPI coverage, permissions, import …)
docs/                 API.md, ARCHITECTURE.md, openapi.yaml
.github/              CI/security/release workflows, issue/PR templates, community files
```

---

## Project status

**Beta.** The core is complete and tested: search/discover, the request workflow, the
**Archive.org** and **Usenet** download paths (verified end-to-end, incl. import, SAB title and
auto-cleanup), users/permissions/quotas, wishlist, messages, issues, designs, i18n, PWA and API.

**Known limitation:** the **filehoster path** (JDownloader) is **experimental** — the code exists,
but no source that yields `source=filehoster` hits is wired up yet
([#63](../../issues/63)). Progress and ideas: [CHANGELOG](CHANGELOG.md) and the [issues](../../issues).

---

## License

[MIT](LICENSE). Romseerr is a private, self-built project and is not affiliated with Overseerr,
Jellyseerr, RomM or RetroNAS.
