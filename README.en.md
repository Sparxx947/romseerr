# <img src="static/logo.svg" width="30" alt="" align="top"> Romseerr

[![CI](https://github.com/Sparxx947/romseerr/actions/workflows/ci.yml/badge.svg)](https://github.com/Sparxx947/romseerr/actions/workflows/ci.yml)
[![Security](https://github.com/Sparxx947/romseerr/actions/workflows/security.yml/badge.svg)](https://github.com/Sparxx947/romseerr/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Stable](https://img.shields.io/badge/status-stable-brightgreen.svg)](#project-status)

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
- [Versions: updating, and going back](#versions-updating-and-going-back)
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
- 🎨 **Four selectable designs** (Seerr / Glass / Clean / Aurora) and **five languages** (DE/EN/FR/ES/IT).
- 🔔 **Notifications** via Discord, Telegram, email, Gotify, ntfy, Pushover and **web push (PWA)**.
- 🔑 **REST API** with an API key and a full **OpenAPI 3.1** doc (`/api/docs`).
- 🧩 **A single `app.py`** (Python 3.14 / Flask), **SQLite** persistence, no build step,
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
  The comparison uses a **normalised key**, not the filename — extension, brackets, region and
  version numbers are stripped. Since #615 that includes the trailing **scene group tag**
  (`…NSW-SUXXORS`, `….NSW.NiiNTENDO`) and the **apostrophe** (`O'Clock` = `OClock`). Without
  those — and **accents**, which are folded to their base letter (`Pokémon` = `Pokemon`,
  `Fußball` = `Fussball`; #618) — the same game counted as two: three titles sat in the library as
  byte-identical duplicates, 26 GB. The rule deliberately fires only directly after a platform
  token and only for tags written the way scene groups write them, so that
  `Bomberman 64 - Arcade Edition` does not merge into `Bomberman 64`.
  Conversely, **only an actual extension is stripped** (#617): `splitext()` treated everything
  after the last dot as one and deleted real title text — `R.B.I. Baseball` became `R.B.I`,
  `Vol. 3` became `Vol`. **1,307 title groups covering 5,401 files** shared a key that way, so
  a missing volume counted as present.
- **What this stack does not serve does not show up.** PS5 and Xbox Series releases are
  dropped rather than assigned to some platform (#607). The reason is concrete: the title
  detection did not know `PS5`, returned `None`, and then the indexer's category wins —
  three of the four "Switch" hits for *Resident Evil 4* were PS5, the largest **62 GB**.
  This is explicitly different from a category that is merely too coarse (Wii U rides along
  under Wii, #452): there is no folder, no emulator and no import path for PS5 here, so
  such a hit is **never** right. Dropped hits are logged — a search that quietly returns
  less would be impossible to read.
  Since #616 the same applies to **modern PC and mobile** (`Windows`, `Linux`, `macOS`,
  `Android`, `APK`, `GOG`, `Steam`): 21 of 26 hits for *Cyberpunk 2077* came back with no
  platform at all, were requestable, and landed in `.unsortiert` for want of a destination.
  What still has **no platform** after that is neither guessed nor dropped but **named**: the
  card shows "⚠ platform unknown" together with the consequence — on import the title is
  filed under `.unsortiert` and has to be sorted by hand (#621). Guessing would be worse than
  saying nothing: of 1,217 hits only 19 resolve to exactly one platform via the index, and
  several of those are wrong — `FINAL FANTASY VII (STEAM VERSION)` would get `nes` because a
  NES hack happens to sit there.
  **Retro PC stays served** — `dos` (5,903 titles, `dosbox_pure` core) and `scummvm` have
  their own patterns, which match first. And `PC Engine` is TurboGrafx-16: the pattern
  explicitly excludes `pc-fx`, `pc-8800`, `pc-9800`, `pc-booter` and `pc-jr`, which are real
  platforms in this library.
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
  **3DS: the refusal comes before the promise.** An encrypted image and a `.cia` both fail
  to boot — for different reasons, and both are stated **before** a seat is taken.
  Previously Romseerr said "streamable", the user clicked, took a seat and waited for a
  picture that never arrived. *Encrypted* applies to this title as it is; *`.cia`* applies
  to the format, always — installation packages never boot directly, decrypted or not. When
  in doubt it passes: an image without a readable NCSD header cannot be judged, and a wrong
  refusal costs more than a failed attempt.
  **Switch: updates and DLC are not games.** Of 434 files under `switch/`, **110 are
  updates and 58 are add-on content** — 39 % were Play buttons that cannot boot. The last
  three digits of the title ID decide (`000` game, `800` update, `001` upward DLC), and it
  sits **inside the archive**: in the name of the `<rights-id>.tik` ticket in the PFS0
  index, unencrypted and readable without keys. The filename does not do it — "DLC" appears
  as `[DLC]`, as `[space scout pack dlc]`, and `[Trowzer's Top Tonic Pack]` carries no hint
  at all while being one. An XCI or an archive without a ticket still passes: a wrong
  refusal costs more than a failed attempt.
  **What a file is comes from its content, not its name.** This library holds a "Save Data
  Transfer Tool" named `.3ds` that **is** a `.cia`: header size `0x2020`, certificate chain,
  ticket, TMD, and no `NCSD` at `0x100`. Judged by extension it fell straight into the
  "cannot be judged, so pass" rule and was offered as bootable. It was the only one of 1,249
  images — the count was right, the conclusion was not. The header now decides, in **both**
  directions: an image misnamed `.cia` would otherwise be refused as an unreadable CIA
  although it runs fine, and a wrong refusal is the expensive error here. Anything that
  identifies as neither still passes: the check adds knowledge, not refusals.
  **Encrypted is no longer a dead end when the host can decrypt.** Azahar only plays
  decrypted dumps and does not decrypt by itself; 1,248 of 1,249 measured images in this
  library were encrypted — without this step the platform stays empty. The streaming host
  therefore ships the tool itself (`init/23-3ds-entschluesseln`) and decrypts **at launch,
  into a cache alongside** — measured at 0.07 s for a 128 MB image; the time is in the copy. Romseerr asks for the
  capability and turns the refusal into a promise with an announced wait (`will_decrypt`);
  if the host does not answer, the refusal stands — a promise it cannot keep would only
  surface after a seat has been taken.
  **`.cia` is installed rather than refused.** A CIA never boots directly, but Azahar can
  install it, and the installed title then boots. What decides is the **kind of package**,
  and that lives in the title ID rather than the filename: of 25 CIAs in this library 13 are
  updates and 2 are DLC, which never boot even once installed, and in two cases the filename
  disagreed with the title ID. Romseerr therefore refuses with a reason of its own
  (`cia_update`, `cia_dlc`) and only promises a launch when the host reports
  `can_install_cia`. Unlike an image, an **unreadable CIA is refused** rather than passed:
  a CIA must have a title header, so its absence is a defect and not a special case.
  **Why alongside rather than in place:** *the encrypted original is what identifies the
  title.* Of 20 3DS titles Hasheous matched 15 by checksum — the best rate in the whole
  library, and replacing the files would throw those metadata away. The cache has a cap
  (`DECRYPT_3DS_CACHE_GB`, default 50) and evicts least-recently-used.
- 🎮 **Wii U, PS Vita and Xbox can import now.** `.wux`, `.wud`, `.wua` and `.rpx`
  (Wii U), `.vpk` (Vita) and `.xbe` (Xbox) were missing from the extension list, and
  without them **not a single title** of those platforms could enter the library. A 5.5 GB
  download ended in "1 Nicht-ROM übersprungen". Wii U never working looked like a missing
  title and was a missing line.
- 🔑 **An Archive.org account via key pair, not a password.** Under *Settings →
  Connections → Archive.org* Romseerr takes the access and secret key from
  `archive.org/account/s3.php` and sends them as a header (`Authorization: LOW …`). It is
  revocable on its own, has no session to expire quietly overnight, and the account
  password is never involved. With keys present the padlock on restricted hits disappears,
  because they are downloadable. **Without** keys a restricted title is refused immediately
  with a reason rather than queued.
- 📥 **Bulk import from a drop folder.** Put files in the share over SMB — Romseerr
  looks every 5 minutes and files what it can determine. A file is only touched once size
  **and** mtime are unchanged since the previous pass: an SMB copy of 5 GB takes minutes,
  and a half-copied image would otherwise sit in the library as a title that never starts.
  What cannot be determined stays put, **with a reason**. 25 of the 82 accepted extensions
  are ambiguous; a download carries its platform hint from the request, a dropped file
  carries nothing. The folder name may decide where the extension cannot.
  Moving is copy, verify, then delete: drop folder and library are different filesystems,
  and nothing is deleted that did not arrive.
  **What SAB already has is not fetched twice (#609).** A restart declares running jobs
  dead — SAB keeps downloading them, and a retry then handed the same NZB over again.
  Measured after a deploy during 13 downloads: 19 queue entries for 13 jobs, four titles
  twice, 115.6 GB outstanding instead of 66. Worse than the duplicated load was the
  consequence: SAB appends `.1` on a name clash, so two folders share one prefix — the
  import could have taken 180 KB instead of 853 MB and reported success. SAB is asked
  first now.
  All of it is visible and triggerable under **Settings → Drop folder**: what will be
  filed, what stays put and **why**, plus a button that does not wait for the timer. The
  list itself moves nothing — it is the dry run. With no folder mounted the panel says so
  and names the expected path. Without this view the folder would be exactly the black box
  it was built against: files vanish or they don't, and nobody can see why. (The same data
  is at `/api/import/status`.)
- 🏷️ **The internal job name stays out of the library (#613).** When a release is a
  single file, SAB names it after the job — which was `romseerr_<jid>__<title>`. The prefix
  then travelled into the library filename, and RomM shows filenames as titles; eleven
  files carried it, one since the previous day. The **timestamp** inside it is the worse
  half: two copies of the same game from different downloads looked like two different
  titles to the dedup check. The prefix stays where it belongs — `find_output` locates the
  finished folder by it (#64) — but no longer on the shelf.
- 🔎 **A ROM with the wrong extension is recognised by its magic (#611).** A release
  named its 6.2 GB NSP `….hdf` — normally an Amiga hard-disk image, and `hdf` is not in the
  extension list. The file started with `PFS0`, so it was a perfectly good Switch title;
  the import walked past it and reported "no ROM files" after fetching, unpacking and
  verifying 6.2 GB. When the name gives nothing, the file itself is consulted — **narrowly**:
  unknown extensions only, 64 MB minimum, and two unambiguous signatures (`PFS0` at 0,
  `HEAD` at `0x100`, behind the RSA signature). Explicitly not guesswork like libmagic
  (#607), but one exact magic number at a fixed offset.
- 🗂️ **Organise library — see what the rebuild is doing.** Under **Settings → Organise
  library** (admins only): progress in percent, elapsed time, an estimate of what is left,
  the platform currently being worked on, and the logs with their `--zurueck` command.
  **This view starts nothing** — it reads.
  Two decisions behind it that the display does not show: the percentage is computed over
  **files**, not platforms (`amiga` alone is over 270,000 entries against `gbc`'s 5,548 — a
  per-platform figure would sit still for hours and then jump), and the state comes from
  `<roms>/.umbau/` rather than from a job record: Romseerr clears in-flight jobs on start
  (#336), so a restart during a rebuild would declare the record dead while the rebuild
  keeps running. The file is written by the running tool and knows better. Finished,
  running and **aborted** are three distinct answers — an aborted run leaves neither
  `fertig` nor `aktuell`, which is precisely why someone comes looking. (The same data is
  at `/api/library/organize/status`.)
  **Runs can be started from here too** — dry or real, whole library or a single platform.
  The dry run does not ask (it changes nothing); the real one does. A second run is
  refused **even when the first was started elsewhere**: the progress file is consulted,
  not just this process. Only a run started from this interface can be stopped — what the
  throwaway container started is unknown to this process, and the button says so.
  **Restarting the container aborts a running rebuild.** No work is lost: the tool resumes,
  and because the view reads its state from the file, it then says "aborted" rather than
  "running", which would be a lie.
- ⌨️ **Home-computer formats import now.** `.prg`, `.tap`, `.crt`, `.g64`, `.z80`,
  `.tzx`, `.cdt`, `.adz`, `.a52` and more — 16 formats were missing from the extension
  list, so **nothing could arrive** through Romseerr for C64, VIC-20, ZX Spectrum, CPC,
  Amiga or Atari 5200. Measured against the library: **51,118 files**. That those platforms
  hold content at all is down to the RetroNAS share.
  `.tap`, `.sna` and `.car` deliberately keep **no fixed platform** — `.tap` exists on C64
  *and* ZX Spectrum. They import; the platform comes from the request.
- 📦 **An unpacked game is ONE title, not a pile of files.** Where the title is a
  directory — Wii U (`code`+`content`+`meta`), PS3 (`PS3_GAME`), extracted GameCube images,
  Xbox (`default.xbe`) — it moves into the library as a unit. Recognised by **layout**, not
  by file count: an unpacked game and a collection both have thousands of files, but the
  layout is fixed by the format.
  Previously each file was judged on its own, which went wrong in both directions:
  "14 Datei(en) → 14×wiiu · 170 Nicht-ROM übersprungen" — the 14 were fragments from inside
  the game, the 170 were the game including its executable.
- 🔗 **From a request to its card.** Clicking a request's title opens the game's detail
  view. The title used to be plain text — only the buttons on the right reacted. When the
  search finds nothing the row says so rather than opening an empty window: the likeliest
  click is on a **failed** request, and that is exactly the one that may not be findable.
- 🔒 **Restricted Archive.org items say so beforehand.** Some items sit in the `loggedin`
  collection and need an account; without one the download answers **HTTP 401**. Such hits
  stay visible — they exist — but carry a padlock. Previously this only surfaced after the
  click, and for "Mario Kart 8 (Europe)" after 5.5 GB that could never arrive. When a
  download does fail, the **reason** is now shown instead of
  `returned non-zero exit status 24`.
- 🔎 **Every source is always asked.** The platform filter applies to the *result*, never
  to the *question*. A lookup table used to decide whether Usenet was queried at all, which
  turned a gap in that table into a missing result — indistinguishable from "does not
  exist". Measured: selecting Wii U switched Usenet off while seven releases were sitting
  there, because the indexer files Wii U under the **Wii** categories. Title-based
  classification sorts it out afterwards.
  A result with **no** recognised platform still passes every filter — Archive.org titles
  often carry none and are still what was meant — but now ranks **below** confirmed
  matches. Previously a `wiiu` filter put seven unclassified titles on top and the first
  genuine hit at position 6.
- 🗂 **What is not a platform does not become one.** When a title's platform cannot be
  determined it stays **empty** — Romseerr invents no name. It used to say `Mixed`, and
  because that value flowed all the way to creating the target folder, Romseerr **created**
  the platform it was standing in for: first the folder, then the index entry, then a system
  in the view. A title with no recognisable platform was not unlabelled but labelled with a
  platform that does not exist. Downloads without a platform now go to `.unsortiert`; the
  leading dot is enough to keep it from ever becoming a system. An **existing** `Mixed`
  folder is left alone — it simply no longer counts as a platform.
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
   sort into /roms/<platform>/ → index (that platform only)/RomM scan →
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

Tech: **Python 3.14 · Flask · SQLite · aria2 · unar**. No build step — the entire front-end lives
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
  ghcr.io/sparxx947/romseerr:1.2.0-beta.1
```

> **Do not use `:latest` while there is no stable release.** The tag is only applied to
> stable versions — a pre-release must not move it. Since every release so far has been a
> beta, `:latest` still points at a build from **2026-08-07 07:33** (`bd87e6c`), which
> predates v1.0.0-beta.1. Following it gets you an image belonging to no release at all.
> Use the version number until the first stable one appears.

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

> **`/roms` must be READABLE for that same uid — every platform folder individually.**
> A folder the container may not enter contributes **zero titles**. That used to look
> exactly like an empty platform: here one folder sat at `drwx-w----` (the group could
> write but not read it) and 13,176 titles went missing with nothing saying so anywhere.
> The index run now names it:
>
> ```
> Bibliotheks-Index: 598 Plattformen, 128177 Titel (in DB gesichert) — 1 Plattform NICHT gelesen: pico8 (PermissionError)
> ```
>
> and `/health` carries it as `lib_failed` plus `lib_failed_platforms`. Anything above `0`
> means **`lib_titles` is incomplete**. Check with
> `docker exec romseerr ls /roms/<folder>`, fix with `chmod 755 /path/to/<folder>`.

> **After an import the log carries a different line** (#655). A full run over the whole
> library was measured here at 260.7 s — after every import, even one that added nothing.
> An import now re-reads only the platforms it actually wrote to:
>
> ```
> Bibliotheks-Index aktualisiert: switch (484) — 599 Plattformen, 293068 Titel (in DB gesichert)
> ```
>
> Those platforms are re-read **in full**, so deletions and renames inside them are picked
> up exactly as by a full rebuild. The full run stays and keeps running every 600 s in the
> background.

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
| `JD_WATCH` / `JD_OUT` | Romseerr's view of the hand-off and target folders (host side: `JD_WATCH_HOST` / `JD_OUTPUT`, see below). Empty `JD_OUT` = **derived from `JD_DL_BASE`** |

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

### Host paths vs. Romseerr's own view

The last entries of `.env` (`ROMS_LIB`, `SAB_COMPLETE`, `JD_WATCH_HOST`, `JD_OUTPUT`) are
**host paths for the compose `volumes:`** — Romseerr never sees them, it only sees the
mount points `/roms`, `/sab-complete`, `/jd-watch`, `/jd-output`.

The two sets of names must **not collide**: `env_file: [.env]` pushes every entry of `.env`
into the container, and wherever a host path carries the same name as a variable Romseerr
reads as its *own* path, the host path wins inside — silently.

> **When updating:** this variable used to be called `JD_WATCH`, which was exactly that
> case (#377). **Rename `JD_WATCH=` to `JD_WATCH_HOST=`** in your own `.env`, otherwise
> compose mounts the default `./data/jdownloader/folderwatch` instead of your folder.
> `docker compose config` shows what is actually mounted.
>
> Likewise `PORT` now applies inside and outside (`${PORT}:${PORT}`). The inside used to be
> a fixed `8770`: any other `PORT` published a port nobody listened on — while the health
> check, reading the same variable, still reported `healthy`.

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

**Work that stops progressing is aborted.** A thread that is *alive* but stuck — an
unpack on a full disk, a fetch without a timeout — looks from the outside exactly like one
that is working. **Real progress** is measured instead: the bytes in the job's working
directory, not the time since the last message. A large download may take hours and is left
alone as long as the file grows. Limits: 6 h without progress while downloading, 2 h while
importing (`ROMSEERR_MAX_STILL_DOWNLOAD`, `ROMSEERR_MAX_STILL_IMPORT`).

**A restart aborts work in progress — visibly.** Downloading and importing need a running
process; if the container is replaced mid-way, that thread is gone. Such jobs are moved to
**error** on the next start, with a message asking for the request to be repeated. Before,
they stayed on "importing": the title counted as requested for ever, could not be requested
again, and its half-finished folder was protected from cleanup. Pending and queued requests
are left alone — those survive a restart perfectly well.


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

- **Designs:** four selectable looks — **Seerr** (dark, polished), **Glass** (glassmorphism,
  gradient + blur), **Clean** (flat, minimal) and **Aurora** (#629): navigation on top instead of
  the side, a hero above the discover rows, an aurora gradient and one strong accent.
  **The gradient deliberately sits only where there are no covers** — hero, top bar, empty
  states — and fades out before the first row. The discover view is cover-dominated; a
  gradient behind it puts two colour sources in competition and both lose.
  The admin sets the default, each user picks their own
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

## Versions: updating, and going back

Every release leaves **three** things behind. They name the same version and can do
different things:

| | for what | changeable |
|---|---|---|
| image `ghcr.io/sparxx947/romseerr:1.1.0-beta.1` | a container that **pulls** | no |
| git tag `v1.1.0-beta.1` | a build **from source** | no — tags are immutable |
| branch `release/v1.1.0-beta.1` | a build from source | **yes** — a backported fix goes here |

All three come out of the same run: `release-please` creates the tag and the release, fast
forwards `main`, opens the release branch and **builds the image**. That last step hangs off
this workflow deliberately rather than off an `on: release` trigger — a release created by a
bot with the default `GITHUB_TOKEN` triggers no further workflows, which is exactly why
v1.1.0-beta.1 ended up without an image. `latest` is only applied to a version without a `-`
in its name, so never to a pre-release.

**The same rule governs the GitHub release.** A release whose version carries a `-` is
published as a **pre-release**; `"prerelease": true` in `release-please-config.json` takes
care of it, so nobody has to remember. Both conditions hang off the same `-`, and a test
computes one against the other: an image denied `latest` next to a release calling itself
latest is a contradiction. That is exactly what stood there — two of the four releases were
published as stable while the registry refused those same builds the `latest` tag.

This has an easily missed consequence: if **every** release is a pre-release, `GET
/releases/latest` answers **404**. So the update check asks a second time on that one
status — `/releases?per_page=1`, which knows pre-releases too. Any other error stays an
error and triggers no second request.

**And the comparison counts the pre-release part.** While every release is a beta, both
sides of the comparison carry one — `1.3.0-beta.1` against `1.3.0-beta.2`. Comparing only
`1.3.0` against `1.3.0` never sees an update there, and the first stable `1.3.0` would stay
hidden from a running `1.3.0-beta.1` as well. So the comparison follows SemVer 2.0.0 §11
precedence: numbers first, a version **without** a pre-release above the same version
**with** one, and within the pre-release identifier by identifier with numbers as numbers —
`beta.10` ranks above `beta.9`, though spelling would sort it before.

**The notice links to the version it names.** The web URL `<repo>/releases/latest` skips
pre-releases exactly like the API endpoint of the same name — measured against foreign
repositories: `kubernetes/kubernetes` redirects to `v1.36.3` although `v1.37.0-rc.0` is
newer, and a repository without an eligible release lands on the `/releases` overview
rather than a 404. In a project whose releases are betas throughout, the click therefore
went anywhere except the version its own link text spells out. It now points at
`<repo>/releases/tag/v<version>` — the same pattern the footer already uses for the running
version — and falls back to the overview only when no version is known at all.

**Running a different version** means, for a pulling container, changing the image tag and
nothing else.

```yaml
services:
  romseerr:
    image: ghcr.io/sparxx947/romseerr:1.0.0-beta.1   # instead of :1.1.0-beta.1
```

`latest` deliberately **never** points at a pre-release. Betas have to be named explicitly.

**Building from source** — this is how the reference installation runs, and how the instance
comes to a dependable answer about itself:

```bash
git checkout release/v1.1.0-beta.1        # or: git checkout v1.1.0-beta.1
docker build -t romseerr:local \
  --build-arg "ROMSEERR_COMMIT=$(git rev-parse --short HEAD)" \
  --build-arg "ROMSEERR_BUILT_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)" .
```

**Without those two arguments** `/api/version` reports neither commit nor build time, and
the question "is this running what the repository says?" is guesswork again — precisely the
case that once cost a working day. Check after rolling out:

```bash
curl -s http://<host>:8770/api/version
{"version":"1.1.0-beta.1","commit":"24a331e","built_at":"…","provenance":"build"}
```

If `provenance` reports anything other than `build`, it was built without those arguments.

**What an older state does not promise:** it is reachable, **not guaranteed to run**.
Dependencies may no longer resolve, and data that has already been migrated may not fit an
older version any more. Back up the data before going back.

---


### Downloads through a tunnel

For usenet and filehosters Romseerr hands off to SABnzbd or JDownloader, and their network
decides how traffic leaves. **For Archive.org, Romseerr downloads itself** with `aria2c` in
its own container, so the download clients' VPN configuration does **not** apply to that path.

`DL_PROXY` (or *Settings → Connections*) sets a proxy for exactly that path — for example the
HTTP proxy of a VPN container:

```
DL_PROXY=http://gluetun:8888
```

It applies to **all** protocols. Set for `http` alone it would do nothing: the files arrive
over `https`, and that would look like protection without being any.

**Fail-closed:** if a proxy is configured and unusable, **the download fails**. There is no
fallback to the direct route. A tunnel that fails open is worse than none — it invites the
assumption of protection that is no longer there.

At startup Romseerr checks that the proxy **actually changes the exit address**, not merely
that it answers: a proxy that quietly forwards directly is reachable and useless at the same
time. The result appears in the startup warnings; the addresses themselves are **not** logged.

## Security

- **Session cookie** signed, `HttpOnly`, `SameSite=Strict`; `Secure` via `ROMSEERR_HTTPS=1`.
  The signing key is kept persistently at `config/secret.key`.
  **If it cannot be saved, Romseerr says so (#587):**

  ```
  Sitzungsschluessel konnte NICHT gespeichert werden (/config/secret.key): PermissionError:
  … — bis das behoben ist, meldet jeder Neustart alle Benutzer ab.
  ```

  This used to vanish silently, and the consequence was indistinguishable from a session
  bug: every start minted a different key, so every login was void — with nothing pointing
  at the permissions of the config directory. Creating the key **successfully** is logged
  too; on a first start that is normal, later it means the file has gone missing.
- **Login rate limit** (failed attempts per IP+user within a window → HTTP 429).
- **API key** compared in constant time.
- **Key material** (`secret.key`, `vapid.json`) is kept at `0600`, existing files included.
  **That protects the file, not the place:** if the config directory itself is open — with a
  bind mount from an Unraid share, `0777` is the normal case — anyone who can write there
  can delete and replace the file. The file's mode alone is therefore **no** evidence that
  the key is protected; the directory has to be right as well. (#589)
- **No secrets in the repo** — `.gitignore` excludes `.env`, `config/` and `*.db*`; CI runs
  **Gitleaks**, **Trivy**, **Bandit** and **CodeQL**.
  Two details that otherwise go wrong quietly: on `push` and `pull_request` Gitleaks sees
  **only the new commits** — the full history is scanned by the weekly run alone. And a
  **scheduled run always starts on the default branch**, here the release branch `main`,
  so it would report on a tree nobody runs. The schedule therefore checks out `dev`
  explicitly (`SCAN_REF` in `security.yml`). Without it the weekly run stayed permanently
  red over false positives that had long been fixed.

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

Two tools under [`contrib/library-tools/`](contrib/library-tools/) reshape a library so
that **RomM, Romseerr and RetroNAS see the same thing**. They solve a problem every
installation with this combination has: RomM counts every first-level entry as one game,
Romseerr counts every file two levels deep. On a real library that was **75 against
23,802** for the same console.


## Project layout

```
app.py                backend + full front-end (single file, no build step)
Dockerfile            non-root image (USER 1000) + healthcheck
docker-compose.yml    reference stack (Romseerr + SAB + Prowlarr + JDownloader + RomM)
.env.example          all configuration values
requirements.txt      runtime packages, pinned exactly — transitive ones included (see below)
scripts/              build_openapi.py, lock_requirements.py
tests/                pytest (smoke, i18n JS, OpenAPI coverage, permissions, import …)
tests/e2e/            browser tests: Playwright + axe-core — see docs/TESTING.md
docs/                 API.md, ARCHITECTURE.md, openapi.yaml
.github/              CI/security/release workflows, issue/PR templates, community files
```

### Dependencies: pinned exactly, transitive ones included

`/api/version` reports the commit, so that "is the running thing the source?" has an
answer. With `>=` requirements it only half had one: two builds of the same commit could
be two different programs. Measured on 2026-08-12, **6 of the 27 packages** in the running
image had been released within the previous 30 days, `pywebpush` six days earlier — across
a major version boundary (1.x → 2.4.0) that `>=1.14` explicitly allowed.

So `requirements.txt` carries the **full closure** with `==`, the Dockerfile installs with
`--no-deps` and verifies with `pip check`. The file is no longer a wish list but the
content of the image: if something is missing there, the **build** fails instead of an
import later on. Updates arrive through Dependabot — with `>=` there was nothing for it to
bump, every build floated to the newest anyway.

```bash
python3 scripts/lock_requirements.py            # recompute and write the closure
python3 scripts/lock_requirements.py --check    # only report whether something is newer (exit 1)
```

Only the `--- direkt / direct ---` section is hand-kept: what `app.py` imports itself. The
test tooling in `requirements-dev.txt` stays **deliberately open** — a drifting test tool
turns CI red and is therefore visible, a drifting runtime dependency ships silently.

**Dependabot groups its updates** (`groups` in `.github/dependabot.yml`, #585): one group
per ecosystem for `minor`/`patch`, another for `major`. The reason is cost, not tidiness.
`dev` requires a branch to be up to date and auto-merge is disabled for the repository, so
**every merge sends all remaining Dependabot PRs back to `BEHIND`**, each then needing its
own full CI round. On 2026-08-14 six one-line version bumps cost roughly 40 minutes and six
CI runs, plus a merge conflict between adjacent lines of the same workflow file. Majors
stay separate because they can break — four of those six were majors — and a red one would
otherwise block the harmless updates as well.

---

## Project status

**Stable, as of 1.4.0.** The core is complete and tested: search/discover, the request
workflow, the **Archive.org** and **Usenet** download paths (verified end-to-end, incl.
import, SAB title and auto-cleanup), users/permissions/quotas, wishlist, messages, issues,
designs, i18n, PWA and API.

Every version before this one was a **pre-release**, which had a consequence the version
number does not show: with no stable release, `GET /releases/latest` answers **404**, and
the application's update check needed its own fallback through the release list (#572).
From 1.4.0 on, `latest` points at something again — the fallback stays, but is no longer
the only path that works.

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
