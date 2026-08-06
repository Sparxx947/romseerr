# Changelog

Alle nennenswerten Änderungen an diesem Projekt. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [SemVer](https://semver.org/lang/de/).

## [Unreleased]

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
