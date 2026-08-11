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

## What Romseerr is — and is not

Romseerr is **tooling**: it searches, requests, downloads and files things away.
It **hosts no content, obtains none and links to none**. Which sources it queries
is configured by the operator — none of them live in this repository, and none are
preset.

Nor does this repository contain emulators, BIOS images, firmware or console keys.
Emulators are fetched on request from the **projects' own releases**; firmware and
BIOS come from **hardware you own**. CI checks this on every pull request.

The full rule is in
[CONTRIBUTING](.github/CONTRIBUTING.md#what-does-not-belong-here).

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

### Library — what is actually here

Coverage answers "what is missing". In front of a shelf the more common question is the
other one: **what do I have for this console?** That is the **Library** menu entry,
grouped by **manufacturer** and **system**.

The grouping here is deliberately **not the one the platform filter uses**. The filter does
fine with five short groups and a catch-all, since you tick individual boxes anyway. A view
that claims to order *by manufacturer* cannot: with the filter's list **74 % of all titles**
landed in the catch-all or in a group with no name at all, and **Commodore — larger than
Nintendo at roughly 40,000 titles** — had no group of its own. Commodore, Sinclair, Amstrad,
Atari, NEC, SNK, Sharp and Bandai now stand on their own; DOS, ScummVM and arcade are not
manufacturers and have their own group. What is left over is called "Unassigned" — never a
dash. Clicking a system opens its titles, with a filter and in
pages: `c64` and ScummVM hold five-figure title counts here, and a complete list would
stall the browser.

**Platforms without a catalogue source appear here too.** No percentage can be computed
for them — but what you own is known without IGDB, and leaving them out would be the very
mistake the coverage page takes care to avoid.

Shown is the **shortest filename** of a title: `Turrican` rather than
`Turrican (1990)(Rainbow Arts)[cr ABC][t +3]`. Titles are normalised internally (lower
case, stripped), which would be unreadable as a list.

Available as an API too: `GET /api/library/platforms` and
`GET /api/library/<slug>/titles` (`offset`, `limit`, `q`) — the counterpart to `…/missing`.

### Coverage

The page is grouped by **manufacturer** (Nintendo, Sega, Sony, Microsoft, other) — the same
grouping the platform filter uses, not a second list. A manufacturer card expands to its
consoles, each with source and snapshot date as before.

The figure on the manufacturer card is **sum owned ÷ sum known**, not the average of the
percentages — otherwise the Virtual Boy (16 titles) would weigh as much as the SNES (2825).
The method is shown as `Σ` on the card. And because **not every platform has a catalogue
source**, the card also states "x of y consoles measurable": a figure covering only part of
a group, without saying so, would mislead.

**Hidden directories are not platforms.** A leading dot marks a tool's directory, not a
part of the library. The reorganiser keeps its working directory as `.umbau` next to the
platform folders, and its log files previously showed up as a platform of their own with
62 titles. The same rule covers `.cache`, `.stfolder` and the directories of sync tools.

**The view works from the keyboard.** Vendor groups and system rows are buttons rather
than clickable areas: they sit in the tab order, carry a readable name including the
title count, and an expanded group announces that through `aria-expanded`.

**Symlink placeholders do not count as titles.** Where the library sits on a filesystem
without real symlinks (Netatalk, Samba), links are stored in the **XSym** format — read
back over the share these are ordinary files. Left alone they become titles, pure grouping
folders such as `nec/` or `sega/` become platforms, and coverage reports gaps that never
existed. Detection goes by content (exactly 1067 bytes, `XSym` header), **not by folder
name**: in someone else's library `sega/` holds real games.

### Logos — deliberately none in the repository

Console and manufacturer logos are **trademarks**, so Romseerr ships **no image files at
all**. Anyone who wants them supplies their own:

```
<config>/logos/snes.png        # filename = platform slug
<config>/logos/nintendo.svg    # or manufacturer group, lower case
```

`png`, `svg`, `webp` and `jpg` are accepted. With no file present the **name** is shown —
that is the normal case and complete as it stands, not a fallback.

### Requests & downloads
- **Playable in the browser** only counts when RomM's player actually ships the core.
  *Settings → Services* checks that per platform against the running installation rather
  than trusting a list.
- **An admin always remains**: changes that would remove the last way in are refused — on
  deletion as well as on a role change.
- **Approval workflow**: users with auto-approve download immediately; otherwise an admin approves.
- **Retry switches source** — from the third attempt Romseerr uses a different source instead of
  repeating the failing one. The entry shows the attempt, the button announces the switch, and
  when no source is left it says so rather than trying again.
- **Remove finished requests** — individually via 🗑 or by group ("clear shown", tied to the
  active filter). Active requests cannot be deleted. Failed ones otherwise keep counting toward
  the badge forever. If a download is still on disk, Romseerr asks whether to delete it too —
  and says so explicitly when files stay behind.
- **Bulk request** ("Request all") requests every not-yet-owned hit at once.
- **Request on behalf of another user** (for admins).
- **Wishlist**: watch titles even when no source exists yet — a background worker re-searches
  periodically and auto-downloads as soon as a matching source appears (strict title matching to
  avoid false positives). The list can also be **imported from a pasted list or a file**
  (TXT/CSV, one title per line, optionally `title;platform`) with a **preview** before anything
  is written: matched / ambiguous / not found. An **example file** in the expected format is
  offered in the dialog (also at `/api/wishlist/example.csv`).
- 📺 **Stream** for the platforms the browser **cannot** emulate (PS2, GameCube, Wii, Switch):
  the emulator runs on a streaming host and the browser receives video and audio. If the same
  title exists on **several** platforms, Romseerr does not guess — it offers the candidates as
  buttons. Romseerr
  emulates nothing and ships neither emulator nor firmware — it resolves a title to a file and
  asks the host to launch it. **Single seat**: one session at a time, showing who holds it,
  with an expiry and an explicit stop. The thin launch service ships as
  **`contrib/streaming-host/`** (compose file, init scripts, launch service, docs)
  and is reproducible without anyone's particular environment. **Audio and gamepad
  require HTTPS** there — over HTTP the browser gates the WebCodecs API and both
  stay silent with no error shown.
  Where a title has **several files** — base game, update, DLC — Romseerr picks the base
  game: **the title ID decides**, on Switch its last three digits (`000` base, `800`
  update, anything else DLC). Only when the name carries no title ID does size break the
  tie. The order matters: a base game with an applied update carries a version > 0 and
  would otherwise look like an update. Launching an update on its own gets you nothing
  but `Error while loading ROM!` — indistinguishable from the outside from an emulator
  that cannot run the platform at all.
- ▶ **Play in the browser**: if the title exists in RomM and the platform has an EmulatorJS
  core, a button on the detail view opens RomM's built-in player. Romseerr emulates nothing
  itself. **PS2, GameCube, Wii, Dreamcast and Switch never show the button** — no core exists
  and none will. Every refusal states its reason (not in the library, too large for the
  browser, no RomM connection); BIOS requirements and the arcade romset caveat are stated up
  front rather than after a black screen.
- 📦 **Filehoster path (experimental)**: a generic **catalogue JSON indexer** for the common
  `{name, downloads:[{title, uris, uploadDate, fileSize}]}` format. **Romseerr ships the parser
  only — the operator supplies the source URLs under Settings -> Connections; none are in this
  repository.** URIs are routed: plain HTTP is downloaded directly, filehoster links go to
  JDownloader as a `.crawljob`, `magnet:` is out of scope. Catalogues have a TTL and show their
  age — link rot is the norm here, and a dead link ends as a clear job error rather than a hang.
- **Per-user request history** with timestamps (admins can filter by user), including the
  **delivered variant**.
- 🏷 **Release variants (region/revision/language)**: Romseerr reads the common naming
  conventions (No-Intro, Redump, TOSEC, GoodTools) and groups detail-view candidates by variant
  instead of listing raw release names. **Per-user preferences** (region order, preferred
  language, accept beta/prototype) with an **instance-wide fallback** in settings. Region
  changes content (language, difficulty, censorship, 50/60 Hz) — that is **not a quality
  ladder**, so candidates follow the configured order rather than being sorted. Anything the
  name does not state stays **unspecified** and is never guessed.
- 🏆 **RetroAchievements** on the detail view: achievement count, points and a link to the set;
  with an account linked in the profile, your own progress as well. Plus a "with achievements
  only" search filter. Purely decorative — **without a key, or on any outage, the section
  disappears and no error surfaces.** Matching runs against the per-console set list fetched in
  advance and requires an **exact** title match; ambiguous matches are discarded, because a
  wrong match is worse than no match.
- 📊 **Per-platform coverage**: "412 of 1,180" — and one click opens the **missing** titles
  (paginated, filterable, bulk-select onto the wishlist). Based on a snapshot from IGDB;
  **source and date sit next to every number**, because metadata sets disagree about what
  counts as a distinct title. Platforms without a snapshot say so instead of claiming "0%".
- **Configuration export/import** (Settings -> Logs & maintenance): versioned JSON holding
  settings, users & permissions, requests and wishlists. Secrets stay out without a passphrase
  and are attached encrypted with one. On import, `merge` or `replace` must be chosen
  explicitly.

### Import
- Unpacking with `unar`, **platform detection** by file extension, **dedup** and sorting into
  `/roms/<platform>/` (RomM & RetroNAS share this library), followed by an optional **RomM scan**.
  Only **known ROM/disk extensions** are imported — non-ROM files (emulators, `.exe`/`.dll`,
  assets) are skipped; if an item contains no ROM, the request ends cleanly as an error instead of
  polluting the library.
- If the download client appends a **second extension** (SABnzbd's *deobfuscate* turns
  `game.nsp` into `game.nsp.hdf`), the second-to-last one counts — the file is imported and the
  bogus suffix is dropped when copying.
- In **SABnzbd/JDownloader** the download appears under the **ROM title**; after the import the
  finished download is **removed** there automatically — but only after a **successful** import.
  If Romseerr recognises nothing, the download stays put so nothing is lost and the cause can
  still be inspected. Those folders are listed under *Settings → Logs & maintenance* with size
  and age, can be removed individually or in bulk, and expire after a configurable window
  (default 14 days, `0` disables it). Once the cause is fixed, **Re-import** on the failed
  request reads those same files again — no new download. (*Retry*, by contrast, fetches the
  whole release a second time.)

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

`latest` only ever points at a stable version: the tag is applied when the version string
carries no `-`, so a pre-release cannot claim it. Images are built by the `release-please`
workflow itself, right after it creates the release — not by an `on: release` trigger,
because a release created by a bot with the default `GITHUB_TOKEN` triggers no further
workflows. That is why v1.1.0-beta.1 shipped without an image.

> **`/config` must be owned by uid 1000** (or writable for it) — that is the uid the image
> runs as. If it is not, Romseerr still starts, answers every request and reports
> `healthy`, but **stores nothing**: no request, no job, no setting. You can see it as
> `"storage": "ro"` in `/health`, a startup warning and a notice in the interface. Check
> with `docker exec romseerr id`, fix with `chown -R 1000 ./config`.

---

## First run

1. **Create an admin** — the first visit shows the setup; afterwards registration is closed
   (the admin creates further users).
2. **Wizard** — walks through the services (SABnzbd, Prowlarr, IGDB, RomM); each step can be tested
   or skipped. Reopen it any time under *Settings → About*.
3. **Check connections** under *Settings → Connections*; *Services* shows reachability.
4. **Check the usenet path** — *Settings → Connections → SABnzbd* measures search, category,
   queue and collect folder one by one without downloading anything. The last line shows
   Romseerr's and SABnzbd's view of the same folder: if they diverge, downloads finish and
   are never picked up. A further stage per indexer fetches **one** file and reports whether
   an actual NZB comes back — an indexer can serve plenty of results and answer every
   download URL with an HTML page.

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
| `CATALOG_URLS` | catalogue JSON sources for the filehoster path (empty = inactive, see below) |
| `ROMSEERR_CATALOG_TTL` | catalogue refresh interval in seconds (default 21600) |
| `ROMSEERR_PLAY_MAX_MB` | size limit for "play in browser" in MB (default 2048) |
| `STREAM_URL` / `STREAM_LAUNCH` | streaming host: browser URL and optional launch service. The token in `STREAM_LAUNCH` must match the host's `STREAM_AGENT_TOKEN` — **rotation is documented in `contrib/streaming-host/README.md`**, and the order matters |
| `ROMSEERR_STREAM_TTL` | streaming session expiry in seconds (default 7200) |
| `SAB_URL` / `SAB_APIKEY` / `SAB_CAT` | SABnzbd |
| `PROW_URL` / `PROW_APIKEY` / `PROW_CATS` | Prowlarr |
| `IGDB_CLIENT_ID` / `IGDB_CLIENT_SECRET` | IGDB (covers, metadata, recommendations) |
| `ROMM_URL` / `ROMM_USER` / `ROMM_PASS` | RomM scan after import |
| `JD_DL_BASE` | base target folder for JDownloader (filehoster), **as the JD container sees it** |
| `JD_WATCH` / `JD_OUT` | Romseerr's view of the hand-off and target folders. Empty `JD_OUT` = **derived from `JD_DL_BASE`** |

> **JDownloader needs the FolderWatch extension** (*Settings → Extension Modules*). It is
> not part of a stock install, and without it the hand-off folder is never read — and the
> directory check cannot tell, since it only covers our own half. Verify it under
> *Settings → Connections → JDownloader → **Test the hand-off***: it drops an inert job and
> watches whether anyone picks it up. For the
> `.crawljob` format see `docs/ARCHITECTURE.md` — `autoStart`/`autoConfirm` are
> `BooleanStatus` (`TRUE`).
>
> **JDownloader must not ask anything in unattended operation.** With *Default On Added
> Dupes Links Action* (or its offline counterpart) left at `ASK`, the first duplicate or
> dead link opens a **modal dialog** nobody sees inside the container — and every later
> job queues up behind it.

Full list and defaults: **`.env.example`**.

---

## Addresses and history

Every view has an address, and so does a title:

| Address | View |
|---|---|
| `#/discover` · `#/requests` · `#/settings` | discover · requests · settings |
| `#/issues` · `#/messages` · `#/coverage` | issues · messages · coverage |
| `#/library` · `#/lists` | library · lists |
| `#/title/<source>/<ref>?v=…&t=…&p=…` | detail dialog on top of view `v` |
| `#/settings/<section>/<subpage>` | e.g. `#/settings/notif/telegram` |

**The interface is served compressed.** Scripts, stylesheets and SVG are compressed once
at startup and kept ready in memory — 245 KB become 79 KB, **68 % less**, at no per-request
cost. Together with the content-hashed `immutable` URLs a returning browser fetches nothing.

The sidebar entries are **real links**: they sit in the tab order, work from the
keyboard and can be opened in a new tab. The active one carries `aria-current`, so a
screen reader knows where you are.

So the browser does the right thing on its own: **Back** returns to the previous view and
closes an open detail dialog instead of leaving the application — on a phone, Back *is*
the navigation. A **reload** lands where you were, and a **link** to a title can be sent
to someone.

### Cards on discover and in search

The top row **"Because you requested"** only suggests titles that exist for a platform this
instance can serve. Without that filter IGDB happily returned modern PC games for an Xbox
seed — including an unreleased one, which sat at the very top as a black tile. A suggestion
that can never be fulfilled costs more trust than a shorter row.


Every card carries the **platform name** in the top left ("GameCube", not `ngc`) and,
where it applies, a state badge at the bottom:

| Badge | Meaning | Action area |
|---|---|---|
| ✓ green | already in the library | *Details* — play and stream live there |
| ⏳ amber | already requested, not here yet | disabled, so nobody requests twice |
| none | neither | *Download* |

The symbol carries the meaning and the colour only reinforces it — on a dark cover, green
alone says nothing to a red-green colour blind reader. **Nothing is hidden:** knowing a
title is already there is useful, it just should not have to be *read*.

### Requests

Above the list are five filters with **counts** — *all*, *active*, *done*, *denied*,
*failed* — plus the user filter when there is more than one account; the two combine. The
page therefore states what it holds without being clicked through.

**Denied is its own group**, neither *done* nor *failed*: under *failed* you would go
looking for defects and find decisions, and under *done* it would be filed correctly but
no longer findable.

In the navigation, *Requests* carries a **count** of unfinished jobs: running **and**
failed ones. A failure deliberately does not drop out — otherwise you learn that zero means
fine while something sits unresolved. Colour separates the two (red when a failure is
included). At zero the badge disappears entirely, and it counts **your own** jobs, admins
included — otherwise it would never be zero and would stop meaning anything.

### Ratings and comments

Cards on *Discover* carry the **IGDB rating**, labelled with its source — an unlabelled
number reads as your own. With no value, nothing is shown.

The detail view adds **your own** rating (1–5 stars, clearable) and a comment section.
The **title** is rated, not the individual release: the library holds several versions of
one game and an opinion belongs to the game. Ratings are **per person** — yours first, the
others beside it. An average of two opinions says less than both side by side.

### My lists

Reachable from the user menu in the top right, address `#/lists`. Two lists that are easy
to confuse — which is why they stay apart:

| | Wishlist | Favourites |
|---|---|---|
| about | titles you do **not** have | titles you **have** |
| purpose | remember to obtain it | get back to it quickly |
| ends | when the title arrives | never |

They share **no** store: a wishlist entry leaving when the title arrives is the point — a
favourite disappearing by itself would be a defect. A title may sit in both, in one, or in
neither. Both are **per user**.

The wishlist used to live under *Requests*, drawn into that same page. But a request is
something the system owes an answer to — it has a state, it ends, and admins see
everyone's. A wishlist is the opposite.

### Footer

Pinned to the bottom of the window and centred: name, the **running version** (linking to
its own release), **GitHub**, and the **short commit**. The commit is what tells a `dev`
build apart from the release whose number it carries — both report the same version. If an
image was built without the build arguments, a ⚠ appears as well.

Every screenshot therefore carries its own version, without anyone having to ask. **When
signed out** only the repository link is shown: a version number on a login page tells a
stranger which vulnerabilities to look up.

### Header

**Language** and **user** live in the top right: language as a dropdown (collapsed to the
flag, flag **and** the language's own name in the list — a flag is a country, not a
language), next to it the name and avatar with a menu for *profile* and *sign out*. Both
menus close on click-outside and on Escape. The sidebar now carries navigation only.

### Settings

The section menu sits **on top** so the forms get the full width — they carry URLs and
keys. **Notifications** and **Connections** have a second row with *one page per method
or service*: setting up Telegram no longer means scrolling past Discord. Each entry shows
its state — filled dot *active*, hollow dot *configured but off*, no dot *not configured*.

Saving only ever sends what is on the page; the other methods are left untouched.

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

**The spec names the failure cases too.** Every operation requiring authentication
documents **401**, and permission-bound ones **403** — previously only the success case
was listed, so a client generated from it did not handle the most common error at all.
A test compares the spec against the running server so the two cannot drift apart again.

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
pip install -r requirements.txt -r requirements-dev.txt
playwright install --with-deps chromium   # once, for the browser tests

pytest                        # everything: unit, delivery, contract, browser
pytest --ignore=tests/e2e     # without a browser (fast)
pytest tests/e2e --no-cov     # browser only
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
tests/e2e/            browser tests: Playwright + axe-core — see docs/TESTING.md
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

## Contributing

Documentation is mandatory and bilingual; two **ratchets** in the test suite hold the level
reached instead of relying on memory. Details, and what deliberately **cannot** be checked:
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

[MIT](LICENSE). Romseerr is a private, self-built project and is not affiliated with Overseerr,
Jellyseerr, RomM or RetroNAS.
