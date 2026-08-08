# Changelog

Alle nennenswerten Änderungen an diesem Projekt. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [SemVer](https://semver.org/lang/de/).

## [1.1.0-beta.1](https://github.com/Sparxx947/romseerr/compare/romseerr-v1.0.0-beta.1...romseerr-v1.1.0-beta.1) (2026-08-08)


### Neu / Features

* add configuration export and import ([#85](https://github.com/Sparxx947/romseerr/issues/85)) ([d82256f](https://github.com/Sparxx947/romseerr/commit/d82256f2ea2d91a389616eb703033ca4280aabf4))
* add in-browser play via RomM's built-in EmulatorJS player ([#93](https://github.com/Sparxx947/romseerr/issues/93)) ([f381d3c](https://github.com/Sparxx947/romseerr/commit/f381d3cc51a5f42728634e9b181e2e9ade0769c1))
* add Italian language (5th UI language) ([#51](https://github.com/Sparxx947/romseerr/issues/51)) ([6ab48ef](https://github.com/Sparxx947/romseerr/commit/6ab48ef99bd6d5d098a72890da5e96e1bd197f65))
* **admin:** consolidated settings page with sections ([#8](https://github.com/Sparxx947/romseerr/issues/8)) ([32083f8](https://github.com/Sparxx947/romseerr/commit/32083f8ab6c90b56deb218263845132ee9a4bd79))
* **admin:** logs view, stats and maintenance actions ([#21](https://github.com/Sparxx947/romseerr/issues/21)) ([3bcd160](https://github.com/Sparxx947/romseerr/commit/3bcd160fbd4d34dde9624e7d97170cab928ca0e4))
* **api:** API key for programmatic access ([#14](https://github.com/Sparxx947/romseerr/issues/14)) ([7c57f45](https://github.com/Sparxx947/romseerr/commit/7c57f45bf44ee28b820c0e43d1b4fc3ba400a6c6))
* **auth:** password reset via email (SMTP) ([#10](https://github.com/Sparxx947/romseerr/issues/10)) ([140918d](https://github.com/Sparxx947/romseerr/commit/140918db2fc5987914f5242f9df6b85a7e821c8a))
* **blocklist:** admin blocklist filters search, discover and requests ([#11](https://github.com/Sparxx947/romseerr/issues/11)) ([814644b](https://github.com/Sparxx947/romseerr/commit/814644b284380d56da132927f392896cceb22a6d))
* bulk request and per-user request history ([#48](https://github.com/Sparxx947/romseerr/issues/48)) ([df00cdd](https://github.com/Sparxx947/romseerr/commit/df00cdd327b963fa0bea44fc92288191661e8a8d))
* **connections:** scraper sources + clear-text reveal ([#40](https://github.com/Sparxx947/romseerr/issues/40)) ([8eb7446](https://github.com/Sparxx947/romseerr/commit/8eb7446142b92c79261aa73af131f84d56a31180))
* **db:** move settings, issues, maillog and push into SQLite ([#36](https://github.com/Sparxx947/romseerr/issues/36)) ([65f96d5](https://github.com/Sparxx947/romseerr/commit/65f96d56a7788d0c7397df03fd5de71c987e266b))
* **db:** move users and jobs into SQLite ([#28](https://github.com/Sparxx947/romseerr/issues/28)) ([45c2956](https://github.com/Sparxx947/romseerr/commit/45c29568df025ba0eff58b0b6f8877f57a91c97f))
* **detail:** rich IGDB metadata in the detail view ([#19](https://github.com/Sparxx947/romseerr/issues/19)) ([898511a](https://github.com/Sparxx947/romseerr/commit/898511ad4d519dd051f57854067ee6ba7d12caf9))
* **discover:** genre rows and customizable discover ([#18](https://github.com/Sparxx947/romseerr/issues/18)) ([e50f7ea](https://github.com/Sparxx947/romseerr/commit/e50f7ea78fbfc9c66790af0fd7cbb45996f64b88))
* download progress + multi-arch release image ([#45](https://github.com/Sparxx947/romseerr/issues/45)) ([bd87e6c](https://github.com/Sparxx947/romseerr/commit/bd87e6c743487c9fe885c9432f0220a3d869e251))
* expose operational metrics at /metrics ([#82](https://github.com/Sparxx947/romseerr/issues/82)) ([e59df94](https://github.com/Sparxx947/romseerr/commit/e59df948c6ee6d50c96fe49213ca4a2fbb51ba6e))
* expose running version via /api/version ([#81](https://github.com/Sparxx947/romseerr/issues/81)) ([fce767d](https://github.com/Sparxx947/romseerr/commit/fce767da5988a5754da33d8f3d15177895dafcde))
* **i18n:** add French and Spanish translations ([#22](https://github.com/Sparxx947/romseerr/issues/22)) ([1ddff73](https://github.com/Sparxx947/romseerr/commit/1ddff73e6cc13a23d12d384366d4e034803cf93b))
* **i18n:** add German/English language switch ([#3](https://github.com/Sparxx947/romseerr/issues/3)) ([32aa692](https://github.com/Sparxx947/romseerr/commit/32aa69280e7a9dd5b3b9bcbfb66f1e0fd1979c46))
* import a wishlist from a pasted list or file ([#84](https://github.com/Sparxx947/romseerr/issues/84)) ([a3218fc](https://github.com/Sparxx947/romseerr/commit/a3218fc8905c955cbb51bb5d16f6afe9ee33c21d))
* **index:** persist the library index in SQLite ([#27](https://github.com/Sparxx947/romseerr/issues/27)) ([a0cc795](https://github.com/Sparxx947/romseerr/commit/a0cc795643e3e48f04ee0dc19b444113ac8cccf3))
* install emulators on demand from Romseerr, not automatically ([#110](https://github.com/Sparxx947/romseerr/issues/110)) ([abf85ef](https://github.com/Sparxx947/romseerr/commit/abf85ef8dabb35d38086e75f8ddb6b6405eb380a))
* **issues:** comment threads on issues ([#20](https://github.com/Sparxx947/romseerr/issues/20)) ([1263217](https://github.com/Sparxx947/romseerr/commit/1263217a76a903fad27a3c32a8c3487221b0afda))
* **issues:** user issue reporting with admin management ([#13](https://github.com/Sparxx947/romseerr/issues/13)) ([b9a0b07](https://github.com/Sparxx947/romseerr/commit/b9a0b072dbd969a3c4704b5746f6f5477f7e599e))
* JDownloader service status and configurable paths ([#91](https://github.com/Sparxx947/romseerr/issues/91)) ([d423bc9](https://github.com/Sparxx947/romseerr/commit/d423bc9faed7ba9e05f79505fc85f8b62e6c6ebc))
* **jobs:** retry failed requests + startup config check ([#37](https://github.com/Sparxx947/romseerr/issues/37)) ([f95c0f7](https://github.com/Sparxx947/romseerr/commit/f95c0f7a4c6fe9da62e2c1363e10dd9b8fc6e2c7))
* **mail:** mail send log in the admin area ([#12](https://github.com/Sparxx947/romseerr/issues/12)) ([6684f23](https://github.com/Sparxx947/romseerr/commit/6684f239e8d06884db527af84874c723126c76c8))
* **messages:** private direct messages between users ([#44](https://github.com/Sparxx947/romseerr/issues/44)) ([6e83740](https://github.com/Sparxx947/romseerr/commit/6e83740eebe194c7590361ddc849836c55a86fbe))
* more emulators, and update/rollback from Romseerr ([#103](https://github.com/Sparxx947/romseerr/issues/103)) ([b73d221](https://github.com/Sparxx947/romseerr/commit/b73d221449f914672f1fa587bfdc1cdd3a3b656e))
* **notifications:** additional agents (Telegram, generic webhook, email) ([#15](https://github.com/Sparxx947/romseerr/issues/15)) ([b155e63](https://github.com/Sparxx947/romseerr/commit/b155e63ce0570c1746da59c25f850fb7aec66491))
* **notify:** native Gotify, ntfy and Pushover agents ([#46](https://github.com/Sparxx947/romseerr/issues/46)) ([3ac2c17](https://github.com/Sparxx947/romseerr/commit/3ac2c1754f476bb9858b81d6fe30a814b5ccd37c))
* per-platform coverage and a browsable missing-titles list ([#86](https://github.com/Sparxx947/romseerr/issues/86)) ([22b15c7](https://github.com/Sparxx947/romseerr/commit/22b15c7118a2a4209ea969d47e625ce12dcf62ef))
* **permissions:** granular per-user permissions ([#16](https://github.com/Sparxx947/romseerr/issues/16)) ([d4542da](https://github.com/Sparxx947/romseerr/commit/d4542da6fe7bbf855d250f5877f4bc48d982bcb7))
* personalized recommendations and game series view ([#49](https://github.com/Sparxx947/romseerr/issues/49)) ([58abd24](https://github.com/Sparxx947/romseerr/commit/58abd24b2c345fea7a97c66fd3386f91983dc8b6))
* **profile:** user profile with avatar, language, password change and personal webhook ([#9](https://github.com/Sparxx947/romseerr/issues/9)) ([6a6c6ce](https://github.com/Sparxx947/romseerr/commit/6a6c6ced2fb06bdfa9b2c9d128bf07d184817b54))
* **pwa:** installable PWA and web-push notifications ([#23](https://github.com/Sparxx947/romseerr/issues/23)) ([b44c1e1](https://github.com/Sparxx947/romseerr/commit/b44c1e16205dddc87ad49b1e17259398af76189c))
* **quotas:** per-user request quotas ([#17](https://github.com/Sparxx947/romseerr/issues/17)) ([da86b20](https://github.com/Sparxx947/romseerr/commit/da86b2042f02f4d15f5bc98582a74948c053d15b))
* **requests:** request on behalf of another user ([#47](https://github.com/Sparxx947/romseerr/issues/47)) ([0f54b12](https://github.com/Sparxx947/romseerr/commit/0f54b12519d9dcf267218b0697e73cd8ffb37dc9))
* Romseerr — Seerr-Experience (Auth, Discover, Berechtigungen, Benachrichtigungen, Stack-Doku) ([#2](https://github.com/Sparxx947/romseerr/issues/2)) ([8ecec51](https://github.com/Sparxx947/romseerr/commit/8ecec51b5f82ff80187d6d159e40877984a65cd8))
* **search:** Plattform-Vorauswahl mit Usenet-Nachfilter ([#1](https://github.com/Sparxx947/romseerr/issues/1)) ([e4da364](https://github.com/Sparxx947/romseerr/commit/e4da36424af489a1d29d009591cc40e6b7540edc))
* **security:** login rate limiting, cookie hardening, non-root container ([#35](https://github.com/Sparxx947/romseerr/issues/35)) ([dcb1a14](https://github.com/Sparxx947/romseerr/commit/dcb1a14934507f383dba0a7d8e13c4637b3def70))
* selectable UI designs (Seerr, Glass, Clean) ([#52](https://github.com/Sparxx947/romseerr/issues/52)) ([6d38a74](https://github.com/Sparxx947/romseerr/commit/6d38a74f0ca4123d6f1443d86525099394329453))
* **settings:** service connections configurable in the UI ([#39](https://github.com/Sparxx947/romseerr/issues/39)) ([d00f22a](https://github.com/Sparxx947/romseerr/commit/d00f22abf3c67dc2376e66ed4192f962c1cfcb62))
* ship the streaming host in this repository ([#98](https://github.com/Sparxx947/romseerr/issues/98)) ([5fea21b](https://github.com/Sparxx947/romseerr/commit/5fea21b6f930f6dbf32108d2c5d262688c894e21))
* show RetroAchievements data on the detail view ([#87](https://github.com/Sparxx947/romseerr/issues/87)) ([b56c7bd](https://github.com/Sparxx947/romseerr/commit/b56c7bdeb1dcc6101c7e837cd9e5e1248ed6de7a))
* show ROM title in SABnzbd/JDownloader and clean up after import ([#66](https://github.com/Sparxx947/romseerr/issues/66)) ([423ed35](https://github.com/Sparxx947/romseerr/commit/423ed35068dde23b7797a40e1d4570070515ea41))
* stream natively-emulated platforms into the browser ([#96](https://github.com/Sparxx947/romseerr/issues/96)) ([f6b81ec](https://github.com/Sparxx947/romseerr/commit/f6b81ec337aa141c290559410dec8aa846c86264))
* **tls:** upload an HTTPS certificate via the web UI ([#41](https://github.com/Sparxx947/romseerr/issues/41)) ([2d61304](https://github.com/Sparxx947/romseerr/commit/2d613045899fef8b5a61980bf32e8c9b03998593))
* **ui:** first-run onboarding wizard and detailed About section ([#43](https://github.com/Sparxx947/romseerr/issues/43)) ([e12796e](https://github.com/Sparxx947/romseerr/commit/e12796e8b91c79f073c4be69356cc72f42f17efb))
* **ui:** generated default avatar when no picture is set ([#38](https://github.com/Sparxx947/romseerr/issues/38)) ([9216ded](https://github.com/Sparxx947/romseerr/commit/9216ded12027bcca9eaa0c9e8c009af6907c5c44))
* un-stub the filehoster path with a generic catalogue-JSON indexer ([#92](https://github.com/Sparxx947/romseerr/issues/92)) ([68c6c02](https://github.com/Sparxx947/romseerr/commit/68c6c024cead443c7666ded299ac2316019d964f))
* wishlist with automatic download ([#50](https://github.com/Sparxx947/romseerr/issues/50)) ([19ec174](https://github.com/Sparxx947/romseerr/commit/19ec1747f5dc63722fc3df75adb3c999352347b3))


### Behoben / Fixes

* **db:** avoid f-string SQL in migration helper (bandit B608) ([#29](https://github.com/Sparxx947/romseerr/issues/29)) ([54390ca](https://github.com/Sparxx947/romseerr/commit/54390cab520ecc5451a71ae40537b86dfd74278a))
* harden user management, wishlist matching and input parsing ([#57](https://github.com/Sparxx947/romseerr/issues/57)) ([d70c9ac](https://github.com/Sparxx947/romseerr/commit/d70c9ac92e1a3535e44d5303ce1609fb2bee92a5))
* import only recognized ROM extensions, not junk ([#62](https://github.com/Sparxx947/romseerr/issues/62)) ([58a3a0f](https://github.com/Sparxx947/romseerr/commit/58a3a0fa5b154b6683d66786f296f75d157a11f8))
* mount the launch agent instead of expecting it in /config ([#105](https://github.com/Sparxx947/romseerr/issues/105)) ([ec77799](https://github.com/Sparxx947/romseerr/commit/ec77799f4c0db06bfd8cf39b52cc77c310df9e53))
* pass the init scripts' variables into the container ([#99](https://github.com/Sparxx947/romseerr/issues/99)) ([326b305](https://github.com/Sparxx947/romseerr/commit/326b3056aa936a4ac67c1ad73e43fc8cff27d1b0))
* refuse outbound requests to internal targets and stop leaking exception text ([#94](https://github.com/Sparxx947/romseerr/issues/94)) ([82fd45e](https://github.com/Sparxx947/romseerr/commit/82fd45e1e27a1385f5f714de08b6c986c98248d3))
* request privacy and design-picker active state ([#60](https://github.com/Sparxx947/romseerr/issues/60)) ([8c432c3](https://github.com/Sparxx947/romseerr/commit/8c432c33874040a58d4dac9976359873eca52042))
* stop returning exception text from import, TLS upload and catalogue status ([#95](https://github.com/Sparxx947/romseerr/issues/95)) ([1d7e3fa](https://github.com/Sparxx947/romseerr/commit/1d7e3fada235f8ca453ad5c25f9c5335db568515))
* **ui:** escape newline in loadLogs so inline script parses ([#24](https://github.com/Sparxx947/romseerr/issues/24)) ([fc03d89](https://github.com/Sparxx947/romseerr/commit/fc03d896a3ceb98317e66be29089cf2afb99862b))


### Dokumentation / Documentation

* add contributor scaffolding and dependency review ([#32](https://github.com/Sparxx947/romseerr/issues/32)) ([470a788](https://github.com/Sparxx947/romseerr/commit/470a7887289f29ee615ea3b8ffd806848ba51e7b))
* **api:** OpenAPI 3.1 spec served at /api/docs and /api/openapi.json ([#33](https://github.com/Sparxx947/romseerr/issues/33)) ([92ea95d](https://github.com/Sparxx947/romseerr/commit/92ea95d6a91842505fb8488e9fb9c78cd83e2db5))
* **code:** extensive comments, docstrings and a code tour ([#34](https://github.com/Sparxx947/romseerr/issues/34)) ([90c54bf](https://github.com/Sparxx947/romseerr/commit/90c54bf2a2ab40b2cd172bb334ad81d426753b8f))
* comprehensive README overhaul (DE + EN) ([#67](https://github.com/Sparxx947/romseerr/issues/67)) ([af3dcfb](https://github.com/Sparxx947/romseerr/commit/af3dcfb8ed89c8177c64bbfed07daa79e99fee01))
* state the content policy, and enforce it in CI ([#109](https://github.com/Sparxx947/romseerr/issues/109)) ([e50be1e](https://github.com/Sparxx947/romseerr/commit/e50be1eb176c8ca2b488cd6e22eba11ab48a446c))


### Umbau / Refactoring

* move the front-end out of Python strings into templates/ and static/ ([#90](https://github.com/Sparxx947/romseerr/issues/90)) ([8cd9d41](https://github.com/Sparxx947/romseerr/commit/8cd9d41eb53c7522c6849010ed13979e9568cf7d))

## [Unreleased]

### Hinzugefügt / Added
- **Anfrage im Namen eines anderen Nutzers** — Admins (Recht `manage_requests`) können in der
  Detailansicht einen Empfänger wählen; die Anfrage läuft dann auf dessen Konto (auto-freigegeben,
  Push an den Empfänger). / **Request on behalf of another user** — admins can pick a recipient in the detail view.
- **Weitere Melde-Agenten** — **Gotify**, **ntfy** und **Pushover** nativ in den Benachrichtigungen
  (zusätzlich zu Discord/Telegram/Webhook/E-Mail/Push). / **More notification agents** — native Gotify, ntfy and Pushover.
- **Download-Fortschritt** — laufende Usenet-Downloads zeigen jetzt den Prozentsatz aus der
  SABnzbd-Warteschlange im Anfragen-Status (statt nur „Lädt…"). /
  **Download progress** — active Usenet downloads show the SABnzbd percentage in the request status.
- **Multi-Arch-Image (amd64 + arm64)** — der Release-Workflow baut das Image jetzt für beide
  Architekturen (läuft damit auch auf Raspberry Pi & Co.). /
  **Multi-arch image (amd64 + arm64)** — the release workflow now builds for both architectures.
- **Private Nachrichten zwischen Benutzern** — neuer Bereich „✉ Nachrichten": Direktnachrichten
  an andere Nutzer mit Verlauf je Gesprächspartner, **Ungelesen-Zähler** (Badge in der Sidebar)
  und „als gelesen"-Markierung. Empfänger wird optional über Web-Push + persönlichen Webhook
  benachrichtigt. SQLite-Tabelle `messages`; `GET/POST /api/messages`, `POST /api/messages/read`. /
  **Private messages between users** — a "Messages" section with per-partner threads, an unread
  badge and read receipts; recipients optionally notified via web push + personal webhook.
- **Erststart-Assistent** — beim ersten Start (Admin, noch nicht „onboarded") führt ein Wizard
  Schritt für Schritt durch die Verbindungen (SABnzbd/Prowlarr/IGDB/RomM) mit Test je Schritt;
  jederzeit über Einstellungen → Über erneut aufrufbar. Flag `onboarded` in den Einstellungen. /
  **First-run wizard** — guides new admins through the stack connections step by step with a
  per-step test; reopenable from Settings → About.
- **Ausführlicher „Über"-Bereich** — Version, Bibliotheks-/Anfragen-Statistik, Links (Repo, Wiki,
  API-Doku, Changelog, Issues, Security), Funktions- und Stack-Überblick, Lizenz. /
  **Detailed "About" section** — version, library/request stats, links, feature & stack overview.

### Geändert / Changed
- **Rebrand-Aufräumen** — restliche `rom-suche`/`romsuche_`-Verweise im Code durch `Romseerr`/
  `romseerr_` ersetzt (Log „Romseerr startet…", Logdatei `romseerr.log`, Job-/Ordnernamen
  `romseerr_<id>`, JD-Pfade). Gemeinsprachliches „ROM-Suche" bleibt. /
  **Rebrand cleanup** — remaining `rom-suche`/`romsuche_` references replaced with `Romseerr`/
  `romseerr_` (log line, log file, job/folder names, JD paths).

### Hinzugefügt / Added
- **HTTPS-Zertifikat über die Weboberfläche** — Admin kann unter Einstellungen → **HTTPS** ein
  TLS-Zertifikat + Schlüssel (PEM) hinterlegen (validiert, `/config/tls`, 600). Ist es aktiviert,
  startet die App zusätzlich einen **HTTPS-Listener** auf einem eigenen Port (Default **8443**);
  HTTP auf 8770 bleibt. Ermöglicht Web-Push/PWA ohne separaten Reverse-Proxy. Status zeigt
  CN/Ablauf; der private Schlüssel wird nie ausgegeben. `GET/POST /api/settings/tls`,
  `POST /api/settings/tls/remove`. /
  **HTTPS certificate via the web UI** — admins can upload a TLS cert+key (PEM) under Settings →
  HTTPS; when enabled the app also serves HTTPS on a separate port (default 8443). Status shows
  CN/expiry; the private key is never returned.
- **Scraper-Quellen + Klartext-Anzeige in „Verbindungen"** — neue Felder für **SteamGridDB**
  (Key, als **Cover-Fallback** verdrahtet, wenn IGDB kein Cover hat) und **ScreenScraper**
  (User/Passwort). Secret-Felder haben jetzt einen **👁-Umschalter**, um den Wert im **Klartext**
  anzuzeigen (Admin, via `GET /api/settings/connections/reveal`). SteamGridDB erscheint im
  Dienste-Status/Test. /
  **Scraper sources + reveal in "Connections"** — SteamGridDB (key, wired as a cover fallback)
  and ScreenScraper (user/password); secret fields get a 👁 toggle to show the value in clear
  text (admin, via `/api/settings/connections/reveal`).
- **Dienst-Verbindungen über die Einstellungsseite** — SABnzbd/Prowlarr/IGDB/RomM/JDownloader
  (URLs, API-Keys, Kategorien, Pfade) sind jetzt im Admin-Bereich unter **„Verbindungen"**
  editierbar, mit **`.env` als Fallback** (leeres Feld = Env-Wert). Secrets werden maskiert und
  nur bei Neueingabe überschrieben; „Test"-Knopf prüft die Erreichbarkeit. Werte werden zur
  Laufzeit über `cfg()` gelesen. Die Secrets liegen nur in der Laufzeit-DB unter `/config`
  (gitignoriert), nie im Repo. /
  **Service connections editable in Settings** — SABnzbd/Prowlarr/IGDB/RomM/JDownloader are now
  configurable in the admin "Connections" section, with `.env` as fallback (empty = env value);
  secrets are masked and only overwritten on new input; a test button checks reachability.
- **Default-Avatar** — Nutzer ohne Profilbild bekommen jetzt einen erzeugten Avatar
  (Initiale auf farbigem Kreis) in Sidebar und Profil statt eines leeren Kreises. /
  **Default avatar** — users without a picture get a generated initials avatar.
- **Fehlgeschlagene/abgelehnte Anfragen erneut versuchen** — Knopf „↻ Erneut" in den Anfragen
  (Recht `manage_requests`); `POST /api/jobs/{id}/retry` reiht den Job wieder ein. /
  **Retry failed/denied requests** — "↻ Retry" button; `POST /api/jobs/{id}/retry`.
- **Konfig-Check beim Start** — warnt im Log, wenn IGDB/SABnzbd/Prowlarr fehlen oder nicht
  erreichbar sind (nicht fatal, im Hintergrund). /
  **Startup config check** — logs a warning when IGDB/SABnzbd/Prowlarr are missing or unreachable.

### Geändert / Changed
- **Alle Stores in SQLite** — die letzten JSON-Stores (**settings, issues, maillog, push_subs**)
  liegen jetzt in einem `kv`-Table in `romseerr.db`; bestehende JSON werden beim Start
  verlustfrei migriert (danach `.migrated`). Nur `secret.key`/`vapid.json` bleiben Dateien
  (Secrets). Damit ist die gesamte Persistenz in der Datenbank. /
  **All stores in SQLite** — the remaining JSON stores (settings, issues, maillog, push_subs)
  now live in a `kv` table in `romseerr.db`, migrated losslessly on startup; only the key
  files stay on disk.

### Sicherheit / Security
- **Login-Bruteforce-Schutz** — max. 8 Fehlversuche je (IP, Benutzer) in 5 min, danach HTTP 429.
- **Cookie-Härtung** — Session-Cookie `HttpOnly` + `SameSite=Strict` (CSRF-Schutz); `Secure`
  automatisch, wenn `ROMSEERR_HTTPS=1` (hinter TLS-Proxy).
- **Container läuft als non-root** — Dockerfile `USER 1000` (echter Fix des Trivy-Funds
  AVD-DS-0002 statt Unterdrückung); Volumes müssen dem Laufzeit-User gehören (z. B. `--user 99:100`).
  Zusätzlich `HEALTHCHECK` im Image. /
  **Login brute-force protection** (429 after 8 fails), **hardened session cookie**
  (HttpOnly + SameSite=Strict, Secure via `ROMSEERR_HTTPS=1`), **non-root container**
  (`USER 1000`, real fix for AVD-DS-0002) and an image `HEALTHCHECK`.

### Dokumentation / Documentation
- **Ausführliche Code-Kommentierung** — Modul-Docstring (Architektur, Datenhaltung, Auth,
  Fallstricke), Docstrings auf den nicht-trivialen Funktionen (Index, Worker, Import, Auth,
  Push) und erklärte Abschnitts-Header in `app.py`; `docs/ARCHITECTURE.md` um einen
  **Code-Rundgang** erweitert (Dateiaufbau, Anfrage-Lebenszyklus, „neue Route hinzufügen",
  Fallstricke). /
  **Extensive code documentation** — module docstring, docstrings on the non-trivial functions,
  and a code tour in `docs/ARCHITECTURE.md`.

### Behoben / Fixed
- **CI grün** — `match` als Variablenname (Ruff hielt das Soft-Keyword für ein `match`-Statement)
  → in `matched` umbenannt; bewusste `0.0.0.0`-Bindung mit `# nosec B104` markiert (Bandit);
  Trivy-Action auf gültige Version `0.35.0` gepinnt (0.24.0 existierte nicht mehr); CodeQL auf
  privaten Repos übersprungen statt rot. /
  **Green CI** — renamed `match` variable (tripped Ruff), annotated the intentional `0.0.0.0`
  bind with `# nosec B104`, pinned Trivy to a valid version, skip CodeQL on private repos.
- **Startseite lud keine Spiele / Admin-Menü tot** — in `loadLogs()` stand `join('\n')`
  im **nicht-rohen** Python-`PAGE`-String; Python wandelte `\n` in einen echten Zeilenumbruch
  um, sodass das ausgelieferte Inline-JavaScript ein **unterminiertes String-Literal** enthielt
  und das gesamte Skript nicht lief (keine Discover-Spiele, kein funktionierendes Admin-Portal).
  Gefixt zu `join('\\n')`. **Lehre:** JS-Escapes im `PAGE`-String immer verdoppeln — Syntaxprüfung
  muss gegen den **interpretierten** String laufen (über den Python-AST), nicht gegen den Quelltext. /
  **Home page loaded no games / admin menu dead** — `loadLogs()` used `join('\n')` inside the
  non-raw Python `PAGE` string; Python turned `\n` into a real newline, so the served inline
  JavaScript had an **unterminated string literal** and the whole script failed. Fixed to `join('\\n')`.

### Hinzugefügt / Added
- **Beitragenden-Infrastruktur** — `CONTRIBUTING.md` (zweisprachig), `SECURITY.md`
  (private Sicherheitsmeldung aktiviert), `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1),
  Issue-Formulare (Bug/Feature) + PR-Vorlage, sowie **Dependency-Review** auf PRs
  (blockiert neue Abhängigkeiten mit HIGH-Schwachstellen). /
  **Contributor infrastructure** — bilingual `CONTRIBUTING.md`, `SECURITY.md` (private
  vulnerability reporting enabled), `CODE_OF_CONDUCT.md`, issue forms + PR template, and
  **dependency review** on PRs.

### Hinzugefügt / Added
- **Versioniertes Image nach GHCR** — bei jedem veröffentlichten Release baut ein Workflow
  das Docker-Image und pusht es nach `ghcr.io/sparxx947/romseerr` (Tags `X.Y.Z`, `X.Y`,
  `latest`); so lässt sich ein fertiges Image ziehen statt lokal zu bauen. /
  **Versioned image to GHCR** — on each published release a workflow builds and pushes the
  image to `ghcr.io/sparxx947/romseerr` (tags `X.Y.Z`, `X.Y`, `latest`).

### Hinzugefügt / Added
- **API-Dokumentation (OpenAPI 3.1)** — vollständige, maschinenlesbare Spezifikation als
  einzige Quelle der Wahrheit (`app.OPENAPI`), ausgeliefert unter **`/api/openapi.json`** und
  interaktiv unter **`/api/docs`** (Redoc). Zweisprachige Anleitung in [`docs/API.md`](docs/API.md),
  generierte [`docs/openapi.yaml`](docs/openapi.yaml) (via `scripts/build_openapi.py`). Tests
  erzwingen, dass **jede Route dokumentiert** ist und die Repo-YAML nicht abdriftet. /
  **API documentation (OpenAPI 3.1)** — complete machine-readable spec (single source
  `app.OPENAPI`), served at **`/api/openapi.json`** and rendered at **`/api/docs`** (Redoc);
  bilingual guide in `docs/API.md`, generated `docs/openapi.yaml`. Tests enforce that every
  route is documented and the YAML stays in sync.

### Hinzugefügt / Added
- **Smoke-Tests (pytest) + Inline-JS-Guard** — die CI prüft jetzt **Verhalten**, nicht nur
  Syntax: Health, Titel-Normalisierung/Dedup, Bibliotheks-Index, Sperrliste, Setup/Login,
  Auth-Schutz. Zusätzlich verifiziert ein Test, dass das **eingebettete JavaScript gültig
  parst** (via `node --check` des interpretierten `PAGE`-Strings) — genau die Fehlerklasse,
  die `py_compile` nicht fängt. Neuer CI-Job **Tests**. /
  **Smoke tests (pytest) + inline-JS guard** — CI now checks behavior, not just syntax
  (health, normalization/dedup, index, blocklist, setup/login, auth); plus a test that the
  embedded JavaScript parses (`node --check` on the interpreted `PAGE`). New CI job **Tests**.

### Geändert / Changed
- **Basis-Pfade per Env überschreibbar** — `ROMSEERR_CONFIG` (Default `/config`) und
  `ROMSEERR_ROMS` (Default `/roms`) steuern die Datenverzeichnisse; nötig für Tests, nützlich
  für flexible Deployments. Verhalten mit Defaults unverändert. /
  **Configurable base paths** — `ROMSEERR_CONFIG` / `ROMSEERR_ROMS` (defaults unchanged).
- **users + jobs in SQLite** — Benutzer und Anfragen liegen jetzt in `/config/romseerr.db`
  (Tabellen `users`, `jobs`) statt in JSON-Dateien; bestehende `users.json`/`jobs.json` werden
  beim ersten Start **automatisch übernommen** und als `.migrated` gesichert (verlustfrei, erst
  nach erfolgreichem Commit umbenannt). Funktionssignaturen unverändert. /
  **users + jobs in SQLite** — users and requests now live in `/config/romseerr.db`
  (tables `users`, `jobs`) instead of JSON files; existing `users.json`/`jobs.json` are
  auto-migrated on first start and kept as `.migrated` (lossless, renamed only after commit).

### Hinzugefügt / Added
- **Persistenter Bibliotheks-Index (SQLite)** — der Dedup-Index (~96.000 Titel) wird jetzt in
  `/config/romseerr.db` gespeichert und beim Start **aus der DB geladen** statt jedes Mal aus dem
  Dateisystem aufgebaut: **Startzeit ~24 s → ~1 s**. Im Hintergrund frischt der Index weiter auf
  (Start + alle 10 min); Dedup/`in_library` unverändert. /
  **Persistent library index (SQLite)** — the dedup index (~96k titles) is stored in
  `/config/romseerr.db` and loaded from the DB on startup instead of walking the filesystem
  every time: **startup ~24 s → ~1 s**. Background refresh keeps it current; dedup unchanged.
- **PWA + Web-Push** — Romseerr ist jetzt eine **installierbare PWA** (Manifest, Icon,
  Service-Worker) und kann **Web-Push-Benachrichtigungen** senden, wenn ein ROM verfügbar
  wird. Aktivierung pro Nutzer im Profil (🔔). VAPID-Schlüssel werden beim ersten Start
  erzeugt (`/config/vapid.json`), Abos je Nutzer gespeichert. **Hinweis:** Service-Worker
  und Push funktionieren im Browser nur über **HTTPS** (oder localhost) — hinter einem
  TLS-Reverse-Proxy betreiben. Endpunkte `GET /api/push/pubkey`, `POST /api/push/subscribe`,
  `/api/push/unsubscribe`, `/api/push/test`. Neue Abhängigkeit `pywebpush`. /
  **PWA + web push** — Romseerr is now an **installable PWA** (manifest, icon, service
  worker) and sends **web-push notifications** when a ROM becomes available. Per-user
  opt-in in the profile (🔔). VAPID keys generated on first start; subscriptions stored
  per user. **Note:** service workers and push only work over **HTTPS** (or localhost) —
  run behind a TLS reverse proxy. New dependency `pywebpush`.
- **Mehr Sprachen** — Oberfläche jetzt auch auf **Französisch und Spanisch** (zusätzlich
  zu Deutsch/Englisch); Umschalter in der Sidebar (DE/EN/FR/ES), Profil- und
  Standardsprache-Auswahl erweitert. Alle vier Sprachen vollständig (97 Schlüssel je Sprache). /
  **More languages** — UI now also in **French and Spanish** (besides German/English);
  sidebar switch (DE/EN/FR/ES), profile and default-language selectors extended;
  all four languages complete (97 keys each).
- **Logs & Wartung (Admin)** — neuer Einstellungs-Unterbereich: **Protokollansicht**
  (letzte Log-Zeilen), **Statistik** (Anfragen aktiv/fertig, Bibliotheksgröße, Cache),
  und Wartungsknöpfe **Cache leeren**, **neu indexieren**, **fertige Anfragen entfernen**.
  `GET /api/logs`, `GET /api/admin/stats`, `POST /api/admin/cache/clear`,
  `POST /api/admin/reindex`, `POST /api/jobs/clear-finished`. /
  **Logs & maintenance (admin)** — new settings section: **log view**, **stats**
  (active/finished requests, library size, cache), and maintenance buttons
  **clear cache**, **reindex**, **clear finished requests**.
- **Issue-Kommentare** — Problemmeldungen haben jetzt einen **Kommentar-Verlauf**;
  der Melder und Bearbeiter (Recht `manage_issues`) schreiben Antworten, Staff-Kommentare
  sind markiert (🛠). Fremde ohne Recht werden abgewiesen (403). `POST /api/issues/<id>/comment`. /
  **Issue comments** — issues now have a **comment thread**; the reporter and staff
  (`manage_issues`) can reply, staff comments are marked (🛠); others are refused (403).
- **Detailseite-Tiefe** — die Detailansicht zeigt jetzt **Wertung, Erscheinungsjahr,
  Entwickler und Genres** (Badges), einen **Screenshot-Streifen** und **ähnliche Spiele**
  (anklickbar → neue Suche), alles via IGDB. /
  **Detail depth** — the detail view now shows **rating, release year, developer and
  genres** (badges), a **screenshot strip** and **similar games** (clickable → new search),
  all via IGDB.
- **Discover-Tiefe** — zusätzlich zu „beliebt je Konsole" jetzt **Genre-Reihen** (RPG,
  Jump 'n' Run, Shooter, Racing … via IGDB) und **anpassbares Discover**: Reihen
  ein-/ausblenden (pro Browser gespeichert). /
  **Discover depth** — genre rows (RPG, platform, shooter, racing …) in addition to
  per-console, plus customizable discover (show/hide rows).
- **Anfrage-Kontingente (Quotas)** — Admin setzt X Anfragen pro Y Tage; Nutzer ohne
  „kein Limit"-Recht (`quota_exempt`) werden bei Überschreitung abgelehnt; Rest-Kontingent
  im Profil. /
  **Request quotas** — admins set X requests per Y days; users without the `quota_exempt`
  permission are refused when exceeded; remaining quota shown in the profile.
- **Granulare Berechtigungen** — statt nur admin/user ein Rechte-Set pro Benutzer
  (anfragen, Auto-Freigabe, Anfragen/Benutzer/Probleme/Einstellungen verwalten,
  kontingentfrei); Admins haben implizit alle. Durchgesetzt auf Freigabe/Benutzer/Issues;
  Rechte-Häkchen in der Benutzerverwaltung. /
  **Granular permissions** — per-user permission set instead of just admin/user
  (request, autoapprove, manage requests/users/issues/settings, quota-exempt);
  admins implicitly have all; enforced on approvals/users/issues.
- **Weitere Benachrichtigungs-Agenten** — neben Discord jetzt **Telegram**, **generischer
  Webhook** (Slack/Gotify/Pushover-kompatibel) und **E-Mail bei Verfügbarkeit** (an den
  anfragenden Nutzer). `notify_send` sendet an alle aktiven Agenten. /
  **More notification agents** — besides Discord: Telegram, a generic webhook
  (Slack/Gotify/Pushover-compatible) and email on availability (to the requesting user).
- **API-Key** — programmatischer API-Zugriff ohne Session-Login (Header `X-Api-Key` oder
  `?apikey=`); Key im Admin-Bereich (Allgemein) anzeigen/kopieren/regenerieren.
  `GET /api/apikey`, `POST /api/apikey/regenerate`. /
  **API key** — programmatic API access without a session (header `X-Api-Key` or `?apikey=`);
  view/copy/regenerate in the admin general settings.
- **Probleme/Issues** — Nutzer melden Probleme zu einem ROM (defekt, falsche Region/Plattform,
  sonstiges); Admin sieht alle und schließt/löscht, Nutzer sehen eigene; „Problem melden" auch
  aus der Detailansicht. `/api/issues` (GET/POST), `/api/issues/<id>/close` + DELETE. /
  **Issues** — users report problems about a ROM; admins see/close/delete all, users see their
  own; "report issue" also from the detail view.
- **Mail-Protokoll** — Versand-Log (Zeit, Empfänger, Betreff, Erfolg/Fehler) im Admin-Bereich
  (Benachrichtigungen), persistiert, auf 100 gekappt. `GET /api/maillog`. /
  **Mail log** — send log (time, recipient, subject, success/error) in the admin
  notifications section, persisted, capped at 100.
- **Sperrliste (Blocklist)** — Admin pflegt Stichwörter; passende Titel werden aus Suche
  und Startseite gefiltert und können nicht angefragt werden. `GET/POST /api/blocklist`. /
  **Blocklist** — admins maintain keywords; matching titles are filtered from search and
  the home page and cannot be requested.
- **Passwort-Reset per E-Mail** — SMTP-Konfiguration in den Einstellungen (Host/Port/User/
  Passwort/Absender/TLS + Testmail); „Passwort vergessen?" auf der Login-Seite → zeitlich
  begrenzter Reset-Link (1 h) per Mail; Reset-Seite `/reset`. Endpunkte `/api/forgot`,
  `/api/reset`, `/api/settings/mail-test`. /
  **Password reset via email** — SMTP config in settings (host/port/user/pass/from/TLS +
  test mail); "Forgot password?" on the login page → time-limited reset link (1h) by mail;
  reset page `/reset`.
- **Benutzerprofil** — je Nutzer: Anzeigename, E-Mail, **Avatar-Bild** (Upload → Data-URI),
  Sprache, eigenes Passwort ändern, **persönlicher Discord-Webhook** (bei Verfügbarkeit
  werden allgemeiner **und** persönlicher Webhook benachrichtigt); Avatar in der Sidebar.
  Endpunkte `/api/profile` (GET/POST), `/api/profile/password`, `/api/profile/notify-test`. /
  **User profile** — per user: display name, email, **avatar image** (upload → data URI),
  language, change own password, **personal Discord webhook** (on availability both the
  global and personal webhooks fire); avatar in the sidebar.
- **Admin-Bereich / Settings-Seite** mit Unterbereichen (Allgemein, Benachrichtigungen,
  Benutzer, Dienste-Status, Über); Benutzerverwaltung + Discord dort gebündelt;
  neue Endpunkte `GET /api/services/status`, erweiterte `/api/settings` (general:
  App-Name, Standardsprache), `version` in `/api/auth/status`. /
  **Admin area / settings page** with sections (General, Notifications, Users,
  Services status, About); user management + Discord consolidated there;
  new `GET /api/services/status`, extended `/api/settings` (general: app name,
  default language), `version` in `/api/auth/status`.
- **CI/CD** — GitHub Actions: Lint/Compile/Docker-Build, Security (CodeQL, Bandit, Trivy, gitleaks),
  Release-Bot (release-please), Dependabot; MIT-Lizenz. /
  **CI/CD** — GitHub Actions: lint/compile/docker build, security (CodeQL, Bandit, Trivy, gitleaks),
  release bot (release-please), Dependabot; MIT license.
- **i18n Deutsch + Englisch** — Sprachumschalter (DE/EN) in der Sidebar, Auswahl via `localStorage`;
  Ober­fläche über `data-i18n` und `t()` übersetzt. /
  **i18n German + English** — language switch (DE/EN) in the sidebar, stored in `localStorage`;
  UI translated via `data-i18n` and `t()`.

### Geändert
- **Rebrand zu „Romseerr"** (vormals rom-suche).
- **Seerr-Layout:** feste Sidebar (Entdecken / Anfragen / Benutzer / Abmelden) statt Tab-Leiste.

### Hinzugefügt
- **Einstellungen → Benachrichtigungen:** Discord-Webhook in der Oberfläche konfigurierbar
  (aktiv/URL) mit Test-Knopf; `notify_send` nutzt Einstellungen, fällt auf `DISCORD_WEBHOOK` zurück.
- **Berechtigungen & Freigabe-Workflow:** je Benutzer „Auto-Freigabe"; Anfragen von
  Nutzern ohne Auto-Freigabe landen als **pending** und müssen vom Admin freigegeben
  (oder abgelehnt) werden. Endpunkte `/api/settings`, `/api/users/<u>` (PATCH),
  `/api/jobs/<id>/approve|deny`.
- **Usenet-Cover:** werden lazy über IGDB nachgeladen (`/api/cover`), Release-Titel
  vorher auf den Spielnamen bereinigt.
- **Benutzerverwaltung / Login:** Session-Auth, Ersteinrichtung (Admin anlegen),
  Rollen (admin/user), Admin kann Benutzer anlegen/löschen. Alle Routen geschützt.
  Endpunkte `/api/auth/status`, `/api/login`, `/api/setup`, `/api/logout`, `/api/users`.
- **Startseite mit Konsolen-Reihen:** beliebte Spiele je wichtiger Konsole (IGDB-Popularität),
  sortiert nach Bedeutung; Klick auf ein Poster sucht den Titel plattform-scoped. `GET /api/discover/rows`.
- **Detail-Ansicht** (Modal): Cover, IGDB-Beschreibung, Metadaten, Archive.org-Dateiliste,
  Versionen/Quellen desselben Titels (`gkey`-Gruppierung). `GET /api/detail`.
- **Anfragen-Status** im Seerr-Stil (Angefragt → Lädt → Wird verarbeitet → Verfügbar).
- **Benachrichtigung bei Verfügbarkeit** via Discord-Webhook (`DISCORD_WEBHOOK`, optional).
- Plattform-Vorauswahl in der Suche (Chips, Mehrfachauswahl, `localStorage`).
  Usenet wird breit über *Console* abgefragt und nach Plattform nachgefiltert;
  reine Retro-Auswahl überspringt Usenet. Neuer Endpunkt `GET /api/platforms`.

## [0.1.0] - 2026-08-06

### Hinzugefügt
- Erste Version: Seerr-artige ROM-Suche über Archive.org + Usenet (Prowlarr/SABnzbd).
- Dedup gegen bestehende Bibliothek, Plattform-Erkennung an der Dateiendung.
- Auto-Import (entpacken via `unar`, Einsortierung nach `/roms/<plattform>/`).
- Weboberfläche (:8770), `docker-compose`, Konfiguration über `.env`.
