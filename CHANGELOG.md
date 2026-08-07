# Changelog

Alle nennenswerten Änderungen an diesem Projekt. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [SemVer](https://semver.org/lang/de/).

## [Unreleased]

### Behoben / Fixed
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
