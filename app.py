#!/usr/bin/env python3
"""
Romseerr — eine Seerr-artige Such-/Anfrage-Oberfläche für ROMs.
Romseerr — a Seerr-style search/request front-end for ROMs.

================================================================================
ÜBERBLICK / OVERVIEW
================================================================================
Romseerr ist bewusst **eine schlanke Oberfläche vor bestehenden Werkzeugen**: Es
sucht Titel (Archive.org + Usenet über Prowlarr), stößt Downloads an (SABnzbd bzw.
JDownloader bzw. direkt via aria2), entpackt/sortiert das Ergebnis in eine
ROM-Bibliothek und meldet Verfügbarkeit. Die gesamte App ist bewusst **eine einzige
Datei** ohne Build-Schritt — Flask-Backend UND das komplette Frontend (HTML/CSS/JS
als Strings) leben hier drin.

Ausführliche Architektur inkl. Diagramm: docs/ARCHITECTURE.md.
API-Referenz: /api/docs (Redoc) bzw. docs/API.md. Mitwirken: .github/CONTRIBUTING.md.

================================================================================
AUFBAU DIESER DATEI / HOW THIS FILE IS ORGANIZED  (Reihenfolge = Abschnitts-Header)
================================================================================
  1. Konfiguration            – Env-Variablen, Pfade (per Env überschreibbar).
  2. Plattform-Zuordnung      – Dateiendung/Token -> Plattform-Slug; Slug -> Anzeigename.
  3. Normalisierung + Index   – norm(): Titel vergleichbar machen; RAM-Index für Dedup.
  4. SQLite                   – persistenter Bibliotheks-Index + users/jobs (Migration aus JSON).
  5. IGDB                     – optionale Cover/Beschreibungen/„beliebt je Konsole".
  6. Suche                    – Archive.org- und Prowlarr/Usenet-Abfrage, Nachfilter.
  7. Jobs                     – Anfrage-Objekte (Zustandsmaschine) + Persistenz.
  8. Download/Import/Worker   – Downloads anstoßen, entpacken, einsortieren (2 Threads + Queue).
  9. Auth                     – Benutzer, Login, granulare Rechte, Decorators.
 10. Web-Push (VAPID)         – optionale Browser-Benachrichtigungen.
 11. Web-UI                   – Vorlagen (templates/) + statische Dateien (static/), inhaltsgehasht.
 12. Auth-/Admin-Routen       – REST-Endpunkte (siehe OpenAPI-Abschnitt).
 13. OpenAPI                  – Selbstdokumentation (/api/openapi.json, /api/docs).
 14. Start                    – Index laden, Worker starten, Flask starten.

================================================================================
DATENHALTUNG / STORAGE  (alles unter CONFIG_DIR, Default /config)
================================================================================
  romseerr.db  – SQLite, der Normalfall: `library` (Dedup-Index), `meta`, `users`,
                 `jobs`, `kv` (Einstellungen, Probleme, Mail-Protokoll, Push-Abos,
                 Favoriten, Bewertungen, Wunschlisten), `catalog`, `fh_items`,
                 `messages`, `ra_games`. settings/issues/maillog/push_subs.json werden
                 beim ersten Start migriert (danach `.migrated`). Fehlt so eine Datei,
                 heisst das meist: hier nie benutzt — kein Beleg fuer eine Migration.
  secret.key, vapid.json, tls/, logos/
               – bleiben BEWUSST Dateien. Schluesselmaterial gehoert nicht in dieselbe
                 Datei wie die Daten, die es schuetzt: eine DB-Sicherung oder ein Export
                 naehme es sonst mit. Geschrieben wird es mit 0600 (schreibe_geheim);
                 aeltere Bestaende werden beim Lesen nachgezogen. Bilder gehoeren nicht
                 in eine Spalte.

                 EN: SQLite is the default. Six former JSON stores are migrated on first
                 start; a missing file usually means the feature was never used here.
                 Key material stays in files on purpose and is written with 0600.
  Die ROM-Bibliothek selbst liegt unter ROMS (Default /roms/<plattform>/…).

================================================================================
AUTH-MODELL / AUTH MODEL
================================================================================
  * Session-Cookie (signiert mit secret.key) ODER API-Key (Header X-Api-Key /
    Query ?apikey=, Admin-äquivalent) — siehe _guard() und die *_required-Decorators.
  * Granulare Rechte (PERMS): request, autoapprove, manage_requests, manage_users,
    manage_issues, manage_settings, quota_exempt. Admins haben implizit alle.

================================================================================
WICHTIGE FALLSTRICKE / IMPORTANT GOTCHAS
================================================================================
  * Das Frontend liegt in templates/ und static/ — NICHT mehr als Python-String.
    Damit ist die alte Falle weg, dass Python die Backslash-Escapes des JavaScripts
    interpretierte (`join('\\n')` -> echter Umbruch -> unterminiertes JS-Literal).
    tests/test_smoke.py::test_inline_js_parses prüft jetzt die echten .js-Dateien.
  * Statische Dateien werden unter /assets/<hash>/<pfad> mit `immutable` ausgeliefert;
    beide Verzeichnisse müssen ins Image (siehe Dockerfile).
  * Pro-Aufruf geöffnete SQLite-Verbindungen werden mit contextlib.closing wieder
    geschlossen (sonst File-Descriptor-Leck bei jedem Request).
  * Deployment: ein neues Image erfordert `docker rm`+`run` — `docker restart` lädt
    KEIN neues Image.
"""
import os, re, sys, json, time, threading, queue, subprocess, urllib.parse, html, secrets, smtplib, base64, sqlite3, unicodedata
from collections import Counter
from datetime import datetime, timezone
from functools import wraps
from contextlib import closing
from email.message import EmailMessage
import requests
try:
    from pywebpush import webpush, WebPushException
    from py_vapid import Vapid
    from cryptography.hazmat.primitives import serialization
    PUSH_OK = True
except Exception:
    PUSH_OK = False
from flask import Flask, request, jsonify, Response, session, redirect, g, has_request_context
from werkzeug.security import generate_password_hash, check_password_hash

# ---------- Konfiguration ----------
# Alle Zugangsdaten/URLs kommen aus Umgebungsvariablen (docker-compose .env), die Datenpfade
# aus CONFIG_DIR/ROMS (per Env überschreibbar, Default /config /roms). Nichts ist hartkodiert.
SAB_URL      = os.environ.get("SAB_URL", "").rstrip("/")
SAB_APIKEY   = os.environ.get("SAB_APIKEY", "")
SAB_CAT      = os.environ.get("SAB_CAT", "roms")
PROW_URL     = os.environ.get("PROWLARR_URL", "").rstrip("/")
PROW_KEY     = os.environ.get("PROWLARR_APIKEY", "")
PROW_CATS    = os.environ.get("PROWLARR_CATS", "1000")
IGDB_ID      = os.environ.get("IGDB_CLIENT_ID", "")
IGDB_SECRET  = os.environ.get("IGDB_CLIENT_SECRET", "")
ROMM_URL     = os.environ.get("ROMM_URL", "").rstrip("/")
ROMM_USER    = os.environ.get("ROMM_USER", "")
ROMM_PASS    = os.environ.get("ROMM_PASS", "")
PORT         = int(os.environ.get("PORT", "8770"))

# ---------- Version / Build ----------
# Die Version kommt aus version.txt (von release-please gepflegt) und NICHT aus einer
# Konstante im Code — sonst driftet sie mit jedem Release auseinander. Commit und
# Bauzeitpunkt werden beim Image-Bau per ARG->ENV eingespritzt; im Quell-Checkout
# fehlen sie und bleiben None (kein Fehler).
def _read_version():
    v = os.environ.get("ROMSEERR_VERSION", "").strip()
    if v: return v
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.txt")) as f:
            return f.read().strip() or "0.0.0"
    except OSError:
        return "0.0.0"

VERSION      = _read_version()
BUILD_COMMIT = os.environ.get("ROMSEERR_COMMIT", "").strip() or None
BUILD_DATE   = os.environ.get("ROMSEERR_BUILT_AT", "").strip() or None

# Basis-Verzeichnisse (per Env überschreibbar — Default = Container-Mounts; nötig für Tests)
CONFIG_DIR = os.environ.get("ROMSEERR_CONFIG", "/config")
ROMS       = os.environ.get("ROMSEERR_ROMS", "/roms")
SAB_DONE   = "/sab-complete"
JD_WATCH     = "/jd-watch"
JD_OUT_ROOT  = "/jd-output"                  # Mountpunkt, unter dem Romseerr JDownloaders Ausgabe sieht
JD_OUT       = JD_OUT_ROOT + "/romseerr"     # Rückfall, wenn sich aus JD_DL_BASE nichts ableiten lässt
JD_DL_BASE   = os.environ.get("JD_DL_BASE","/output/romseerr")  # Sicht des JD-Containers
# Einwurfordner fuer den Massenimport (#396). Wer Dateien per SMB hineinlegt, bekommt sie
# ohne Klick in die Bibliothek — soweit ihre Plattform bestimmbar ist.
#
# WARUM UEBERSCHREIBBAR: Wie ROMS. Ohne das laesst sich der Scanner nicht testen, und ein
# Test, der den echten Einwurfordner braucht, wird nicht geschrieben.
IMPORT_SHARE = os.environ.get("ROMSEERR_IMPORT", "/import")
STAGING    = os.path.join(CONFIG_DIR, "staging")
JOBDB      = os.path.join(CONFIG_DIR, "jobs.json")
LOGFILE    = os.path.join(CONFIG_DIR, "romseerr.log")
USERS_FILE = os.path.join(CONFIG_DIR, "users.json")
SECRET_FILE= os.path.join(CONFIG_DIR, "secret.key")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
MAILLOG_FILE  = os.path.join(CONFIG_DIR, "maillog.json")
ISSUES_FILE   = os.path.join(CONFIG_DIR, "issues.json")
PUSH_FILE     = os.path.join(CONFIG_DIR, "push_subs.json")
VAPID_FILE    = os.path.join(CONFIG_DIR, "vapid.json")
DB_FILE       = os.path.join(CONFIG_DIR, "romseerr.db")
TLS_DIR       = os.path.join(CONFIG_DIR, "tls")
TLS_CERT      = os.path.join(TLS_DIR, "cert.pem")
TLS_KEY       = os.path.join(TLS_DIR, "key.pem")

# ---------- Dienst-Verbindungen: UI-Einstellungen mit Env als Fallback ----------
# Die obigen Konstanten sind nur noch die DEFAULTS aus der Umgebung. Zur Laufzeit werden
# Verbindungswerte über cfg("key") gelesen: erst settings["connections"] (Admin-Oberfläche),
# sonst der Env-Default. So ist alles über die Einstellungsseite konfigurierbar.
# Proxy fuer den EIGENEN Download (#346). Leer = direkt.
#
# Was aria2c mit seinem Rueckgabewert sagt — die Faelle, die hier vorkommen. (#382)
#
# WOZU: Ohne diese Tabelle stand beim Nutzer wortwoertlich
#   Command '['aria2c', '-x8', ...]' returned non-zero exit status 24.
# Das nennt das gescheiterte WERKZEUG, nicht den Grund, und niemand kann daraus etwas
# ableiten. 24 heisst laut aria2-Dokumentation „HTTP authorization failed" — bei
# Archive.org also: Der Titel liegt in der Sammlung `loggedin` und braucht ein Konto.
#
# Nur die Codes, die hier real auftreten koennen. Ein unbekannter Wert wird DURCHGEREICHT
# statt geraten: eine falsche Erklaerung ist schlimmer als gar keine.
ARIA_GRUND = {
    1:  "unbekannter Fehler beim Laden / unknown download error",
    3:  "Datei existiert nicht mehr an der Quelle / file no longer at the source",
    9:  "kein Platz auf dem Datentraeger / no space left",
    19: "Namensaufloesung fehlgeschlagen / name resolution failed",
    22: "Quelle antwortet mit einem Fehler / the source returned an HTTP error",
    24: "die Quelle verlangt eine Anmeldung (HTTP 401) / the source requires a login",
    28: "Zeitueberschreitung / timed out",
}


def ia_kopfzeile():
    """-> ["--header", "Authorization: LOW <key>:<secret>"] oder [].

    NIE PROTOKOLLIEREN. Der Rueckgabewert enthaelt das Geheimnis im Klartext; Romseerrs
    Log-Zeilen landen in Issues und Berichten, und das Repository ist oeffentlich. Deshalb
    gibt diese Funktion die fertigen ARGUMENTE zurueck und nichts, was man versehentlich
    in eine Meldung schreibt. (#384)
    """
    a, g = cfg("ia_access"), cfg("ia_secret")
    if not (a and g):
        return []
    return ["--header", f"Authorization: LOW {a}:{g}"]


def ia_bereit():
    """Sind beide Schluessel hinterlegt? Einer allein nuetzt nichts."""
    return bool(cfg("ia_access") and cfg("ia_secret"))


def aria_fehler(code):
    """-> lesbarer Grund fuer einen aria2c-Rueckgabewert, sonst der nackte Code."""
    grund = ARIA_GRUND.get(code)
    return f"{grund} (aria2c {code})" if grund else f"aria2c beendete sich mit {code}"


# WARUM DAS UEBERHAUPT NOETIG IST: Bei `source: archive` laedt Romseerr SELBST, mit `aria2c`
# im eigenen Container — es reicht die Datei nicht an SABnzbd oder JDownloader weiter.
# Deren VPN-Konfiguration wirkt hier also nicht. Gemessen lief dieser Weg unter derselben
# Adresse wie der Anschluss, waehrend Usenet und Torrent laengst durch einen Tunnel gingen.
#
# WARUM EIN PROXY UND NICHT EINE VPN-NETZWERKKARTE: Romseerr veroeffentlicht eine
# Oberflaeche. Haengt man den Container in die Netzwerk-Namensraum eines VPN-Containers,
# ist die Oberflaeche nur noch ueber dessen Portfreigaben erreichbar — eine viel groessere
# Aenderung mit mehr Wegen, sie falsch zu machen. Der Proxy betrifft nur den Download.
#
# FAIL-CLOSED: Ist ein Proxy gesetzt und nicht erreichbar, SCHEITERT der Download. Er faellt
# NICHT auf den direkten Weg zurueck. Ein VPN, das im Fehlerfall offen faellt, ist
# schlimmer als keins — es laedt zu der Annahme ein, geschuetzt zu sein.
#
# Romseerr downloads Archive.org files itself with aria2c, so the download clients' VPN
# does not apply. A proxy covers just that path; a VPN network namespace would also move
# the web interface. Fail-closed by construction: a dead proxy fails the download.
DL_PROXY = os.environ.get("DL_PROXY", "")

_ENV_CONN = {"sab_url": SAB_URL, "sab_apikey": SAB_APIKEY, "sab_cat": SAB_CAT,
             "prow_url": PROW_URL, "prow_apikey": PROW_KEY, "prow_cats": PROW_CATS,
             "igdb_id": IGDB_ID, "igdb_secret": IGDB_SECRET,
             "dl_proxy": DL_PROXY,
             "romm_url": ROMM_URL, "romm_user": ROMM_USER, "romm_pass": ROMM_PASS,
             # JDownloader: drei verschiedene SICHTEN auf dieselbe Uebergabe —
             # jd_watch/jd_out sieht Romseerr, jd_dl_base sieht JDownloader. (#83)
             # jd_out hat BEWUSST keinen festen Default mehr: leer heisst „aus jd_dl_base
             # ableiten". Ein fester Default stand sonst still gegen ein geaendertes
             # jd_dl_base und Romseerr wartete auf einen Ordner, den JDownloader nie
             # befuellt — genau der Fall aus #197.
             "jd_watch": os.environ.get("JD_WATCH", JD_WATCH),
             "jd_out": os.environ.get("JD_OUT", ""),
             "jd_dl_base": JD_DL_BASE,
             # Scraper / Cover-Quellen
             "sgdb_key": os.environ.get("STEAMGRIDDB_KEY", ""),
             "ss_user":  os.environ.get("SCREENSCRAPER_USER", ""),
             "ss_pass":  os.environ.get("SCREENSCRAPER_PASS", ""),
             # RetroAchievements-Web-API-Key (optional, nur Dekoration auf der Detailseite)
             "ra_key":   os.environ.get("RETROACHIEVEMENTS_KEY", ""),
             # Archive.org: S3-artiges Schluesselpaar von archive.org/account/s3.php.
             #
             # WARUM SCHLUESSEL UND KEIN PASSWORT (#384): Ein Schluessel ist einzeln
             # widerrufbar, ohne das Konto anzufassen; er hat keine Sitzung, die nachts um
             # drei still ablaeuft; und `aria2c` nimmt ihn als Kopfzeile entgegen, so dass
             # der Downloadweg ein Argument braucht statt eines neuen Clients. Romseerr
             # fasst das Kontopasswort damit nie an.
             "ia_access": os.environ.get("IA_ACCESS_KEY", ""),
             "ia_secret": os.environ.get("IA_SECRET_KEY", ""),
             # Katalog-JSON-Quellen fuer den Filehoster-Zweig — eine URL je Zeile.
             # Bewusst NUR konfigurierbar, nie im Repo hinterlegt. (#63)
             "catalog_urls": os.environ.get("CATALOG_URLS", ""),
             # Streaming-Host (#71): Browser-URL des Hosts + optionaler Start-Dienst
             "stream_url": os.environ.get("STREAM_URL", ""),
             "stream_launch": os.environ.get("STREAM_LAUNCH", ""),
             # Zweiter Platz (#137). Bewusst als eigene Schluessel und nicht als Liste:
             # Platz 1 bleibt damit unveraendert, eine bestehende Einrichtung merkt vom
             # Umbau nichts, und ein dritter Platz ist zwei Zeilen mehr.
             # EN: separate keys rather than a list, so seat 1 stays byte-identical for
             # existing installs and a third seat is two more lines.
             "stream_url_2": os.environ.get("STREAM_URL_2", ""),
             "stream_launch_2": os.environ.get("STREAM_LAUNCH_2", "")}
CONN_KEYS = list(_ENV_CONN.keys())
CONN_SECRET = {"sab_apikey", "prow_apikey", "igdb_secret", "romm_pass",
               "sgdb_key", "ss_pass", "ra_key", "ia_secret"}   # in der GUI maskiert (Klartext-Anzeige via Reveal-Endpoint)
def cfg(key):
    """Verbindungswert holen: settings['connections'] (UI) hat Vorrang, sonst Env-Default."""
    v = (load_settings().get("connections") or {}).get(key)
    if v in (None, ""): v = _ENV_CONN.get(key, "")
    return v.rstrip("/") if (key.endswith("_url") and isinstance(v, str)) else v
# __CONN_HELPERS_END__

ROM_EXT = {"sfc","smc","nes","fds","gb","gba","gbc","n64","z64","v64","ndd","md","gen","smd","sms",
           "gg","32x","pce","sgx","ngp","ngc","ws","wsc","iso","bin","cue","chd","img","cdi","gdi",
           "adf","d64","t64","rom","a26","a78","lnx","vec","3ds","cia","nsp","xci","wbfs","rvz","dol",
           "gcm","pbp","ecm","dsk","st","ipf","col","int","j64","jag","min","vb","ws",
           # Wii U (#391): OHNE diese Endungen kann die Plattform GAR NICHT importieren —
           # ein 5,5-GB-Download endete mit „1 Nicht-ROM uebersprungen". `.wux` ist das
           # komprimierte Disc-Abbild, `.wud` das unkomprimierte, `.wua` Cemus eigenes
           # Format, `.rpx` die ausfuehrbare Datei eines entpackten Spiels.
           "wux", "wud", "wua", "rpx",
           # Gleiche Luecke, andere Plattform: Wii-Kanaele und zwei verbreitete
           # GameCube/Wii-Abbildformate.
           "wad", "gcz", "nkit",
           # PS Vita: `.vpk` ist das Installationspaket, das Vita3K einliest. Ohne diesen
           # Eintrag kann die Plattform ebenfalls nichts importieren. (#391)
           "vpk",
           # Xbox: `.xbe` ist die ausfuehrbare Datei eines entpackten Titels. `.iso` steht
           # schon oben, ist aber MEHRDEUTIG — die Plattform kommt dann aus dem Auftrag.
           "xbe",
           # Heimcomputer (#410). Am Bestand gemessen betrafen die Luecken 51.118 Dateien:
           # `.z80` 12.180, `.tzx` 11.525, `.prg` 9.740, `.tap` 6.966, `.g64` 6.131,
           # `.crt` 4.123. Ein Download in einem dieser Formate endete mit
           # „0 Datei(en) -> nichts", genau wie Wii U vor #392. Dass die Heimcomputer
           # ueberhaupt Inhalt haben, liegt an der RetroNAS-Freigabe, nicht am Import.
           "prg", "tap", "crt", "d71", "d81", "g64", "p00", "x64",   # Commodore
           "z80", "sna", "tzx",                                       # ZX Spectrum
           "cdt",                                                     # Amstrad CPC
           "adz", "dms",                                              # Amiga
           "a52", "car"}                                              # Atari 5200
ARCH_EXT = {"zip","7z","rar","gz","tar","tgz","bz2","xz"}
SKIP_FILES = re.compile(r'(\.xml$|\.sqlite$|\.torrent$|_meta\.|__ia_thumb|\.log$|\.txt$|\.nfo$)', re.I)

def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a") as f: f.write(line+"\n")
    except Exception: pass

# ---------- Plattform-Zuordnung ----------
# Tabellen, die ROMs einer Konsole zuordnen: Dateiendung -> Slug (EXT2PLAT), Usenet-Kategorie
# -> Slug, Slug -> Anzeigename (SLUG_NAME), sowie SKIP_FILES (Beifang wie Scans/Handbücher).
# Prowlarr-Usenet-Kategorie-ID -> Slug
USENET_CAT = {101010:"nds",101020:"psp",101030:"wii",101035:"switch",101040:"xbox",101050:"xbox360",
              101060:"wii",101080:"ps3",101090:"xboxone",101100:"ps4",101110:"switch",104050:"pc"}
# Slug -> Usenet-Kategorie-IDs (Umkehrung; nur moderne Konsolen liegen auf Usenet)
SLUG2USE = {}
for _cid, _slug in USENET_CAT.items(): SLUG2USE.setdefault(_slug, []).append(_cid)

# WO EIN INDEXER NICHT TRENNT (#375, #452). Nicht jede Plattform bekommt beim Indexer
# eine eigene Kategorie; manche fahren in der des Nachbarn mit. Nachgemessen:
#
#   Wii U     -> Wii-Kategorien. `Super.Mario.3D.World.USA.WiiU-PoWeRUp` kommt mit
#                {1030, 101030}; die Standardkategorie fuer Wii U (1130) liefert NULL.
#   PS Vita   -> PSP-Kategorie 101020. Eine eigene Vita-Kategorie gibt es nicht.
#
# Ohne diese Eintraege ist die Kategorienliste des Slugs LEER, und die Auswahl der
# Plattform schaltet die Usenet-Suche KOMPLETT AB.
#
# Wer hier steht, darf ausserdem seine Kategorie am Titel zurueckerobern — siehe
# `search_usenet`. Ohne das kaeme jeder Treffer unter dem Slug des Vermieters zurueck
# und fiele aus dem Filter der eigenen Plattform (gemessen: 16 von 16 falsch, #452).
#
# Where an indexer does not separate two platforms, the neighbour's categories are the
# only way in — and the title is what sorts the results out again afterwards.
KAT_LEIHE = {"wiiu": "wii", "psvita": "psp"}   # Mieter -> Eigentuemer der Kategorie
for _mieter, _eigner in KAT_LEIHE.items():
    SLUG2USE.setdefault(_mieter, []).extend(SLUG2USE.get(_eigner, []))

# Für die Plattform-Vorauswahl in der Oberfläche (Gruppe -> [(slug, Anzeigename)])
PLATFORMS = [
 ("Nintendo", [("nes","NES"),("snes","SNES"),("n64","N64"),("gb","Game Boy"),("gbc","GB Color"),
   ("gba","GB Advance"),("nds","DS"),("3ds","3DS"),("ngc","GameCube"),("wii","Wii"),
   ("wiiu","Wii U"),("switch","Switch"),("virtualboy","Virtual Boy")]),
 ("Sega", [("sms","Master System"),("genesis","Mega Drive"),("segacd","Mega-CD"),
   ("sega32x","32X"),("gamegear","Game Gear"),("saturn","Saturn"),("dreamcast","Dreamcast"),
   ("sg1000","SG-1000")]),
 ("Sony", [("psx","PS1"),("ps2","PS2"),("ps3","PS3"),("ps4","PS4"),("psp","PSP"),("psvita","Vita")]),
 ("Microsoft", [("xbox","Xbox"),("xbox360","Xbox 360"),("xboxone","Xbox One")]),
 ("Sonstige", [("turbografx16","PC Engine"),("neogeo","Neo Geo"),
   ("neo-geo-cd","Neo Geo CD"),("neogeopocket","NGP"),
   ("wonderswan","WonderSwan"),("atari2600","Atari 2600"),("atari5200","Atari 5200"),
   ("atari7800","Atari 7800"),
   ("lynx","Lynx"),("jaguar","Jaguar"),("3do","3DO"),("amiga","Amiga"),
   ("amiga-cd32","Amiga CD32"),("c64","C64"),
   ("c16","C16 / Plus-4"),("vic20","VIC-20"),("colecovision","ColecoVision"),
   ("intellivision","Intellivision"),("acpc","Amstrad CPC"),("zxs","ZX Spectrum"),
   ("dos","DOS"),("arcade","Arcade")]),
]
SLUG_NAME = {s:n for _g,items in PLATFORMS for s,n in items}

# --- Hersteller-Ordnung fuer die Bibliotheksansicht (#322) -------------------------
#
# WARUM EINE ZWEITE LISTE UND NICHT `PLATFORMS`: Die beiden haben verschiedene Aufgaben.
# `PLATFORMS` ist die Vorauswahl im Suchfilter — dort sind fuenf kurze Gruppen richtig,
# und ein Sammeltopf „Sonstige" stoert niemanden, weil man ohnehin einzelne Haken setzt.
# Die Bibliotheksansicht behauptet dagegen, „nach Hersteller und System" zu ordnen. Mit
# derselben Liste landeten dort gemessen **74 % aller Titel** in „Sonstige" (79.005) oder
# in einer Gruppe ohne Namen (21.498) — und `scummvm`, die zweitgroesste Plattform der
# ganzen Bibliothek, stand unter einem Gedankenstrich.
#
# Auffaellig dabei: **Commodore ist mit 40.371 Titeln groesser als Nintendo** und hatte
# keine eigene Gruppe. Genau das ist der Fehler, den eine Ordnung vermeiden soll.
#
# Two lists with two jobs: PLATFORMS is the search filter's pre-selection, where five
# short groups and a catch-all are fine. The library view claims to order "by vendor and
# system", and with the same list 74 % of titles fell into a catch-all or a nameless
# group — including scummvm, the second-largest platform in the library.
#
# DOS, ScummVM und Arcade sind keine Hersteller. Sie bekommen eine eigene Gruppe, statt
# sie in einen Rest zu draengen, in dem niemand sie sucht.
LIB_VENDORS = [
 ("Nintendo",   ["nes","snes","n64","gb","gbc","gba","nds","3ds","ngc","wii","wiiu",
                 "switch","virtualboy","famicom","sfam","satellaview","64dd","pokemon-mini",
                 "new-nintendo-3ds","nintendo-dsi","e-reader-slash-card-e-reader"]),
 ("Sega",       ["sms","genesis","segacd","sega32x","gamegear","saturn","dreamcast","sg1000",
                 "sc3000","sega-pico","segacd32","multivision","naomi","stv","model1","model2",
                 "model3","hikaru"]),
 ("Sony",       ["psx","ps2","ps3","ps4","ps5","psp","psvita","pocketstation","psp-minis"]),
 ("Microsoft",  ["xbox","xbox360","xboxone","series-x-s","win","win3x","win9x","msx","msx2",
                 "msx2plus","msx-turbo"]),
 ("Commodore",  ["c64","amiga","amiga-cd32","amiga-cd","vic20","c16","c128","cpet",
                 "commodore-cdtv","commodore","plus4"]),
 ("Sinclair",   ["zxs","zx80","zx81","sinclair-ql","zx-spectrum-next","timex-sinclair-2068",
                 "sinclair"]),
 ("Atari",      ["atari2600","atari5200","atari7800","lynx","jaguar","atari-st","atari8bit",
                 "atari800","atari-jaguar-cd","atari-xegs","atari-vcs","atari"]),
 ("Amstrad",    ["acpc","amstrad-gx4000","amstrad-pcw","amstrad"]),
 ("NEC",        ["turbografx16","pc-fx","pc-8800-series","pc-9800-series",
                 "nec-pc-6000-series","supergrafx","nec"]),
 ("SNK",        ["neogeo","neogeopocket","neogeomvs","neogeoaes","neo-geo-cd","neo-geo-x","snk"]),
 ("Bandai",     ["wonderswan","swancrystal","bandai","playdia"]),
 ("Sharp",      ["sharp-x68000","x1","smc-777","sharp-mz-2200","sharp","sharp-zaurus"]),
 # Die drei folgenden Gruppen sind KEINE Hersteller, sondern Sammelbegriffe. Sie tragen
 # deshalb einen i18n-Schluessel statt eines festen Textes — Herstellernamen sind in allen
 # Sprachen gleich, „Heimcomputer" ist es nicht.
 # The last three are categories, not vendors, so they carry an i18n key: brand names are
 # the same in every language, "home computers" is not.
 ("lib_grp_home",     ["colecovision","colecoadam","intellivision","vectrex","3do","apple",
                 "appleii","appleiii","apple-iigs","bbcmicro","acorn-electron",
                 "acorn-archimedes","oric","dragon-32-slash-64","trs-80","ti-99",
                 "thomson-mo5","thomson-to","fm-7","fm-towns","tandy","enterprise",
                 "memotech-mtx","sam-coupe","galaksija","epoch-super-cassette-vision",
                 "epoch-cassette-vision","epoch-game-pocket-computer","epoch_co"]),
 ("lib_grp_pc",  ["dos","scummvm","arcade","mame","fbneo","cps1","cps2","cps3","atomiswave",
                 "pico8","tic-80","linux","mac","openbor","z-machine","glulx","pc-booter"]),
 ("lib_grp_hand",["g-and-w","gp32","GP32","gp2x","gp2x-wiz","RG350","dingoo","pandora",
                 "LCD Handhelds","handheld-electronic-lcd","dedicated-handheld","watara",
                 "supervision","gamate","game-dot-com","mega-duck-slash-cougar-boy",
                 "arduboy","pokitto","uzebox","wasm-4","evercade"]),
]
LIB_VENDOR_OF = {s: v for v, slugs in LIB_VENDORS for s in slugs}
# Wie die Gruppe heisst, in der alles Uebrige landet. NIE ein Gedankenstrich: Eine
# Ueberschrift, die nichts sagt, ist schlimmer als eine, die „Rest" sagt.
LIB_REST = "lib_grp_rest"
# Schluessel beginnen mit `lib_grp_` — daran erkennt die Oberflaeche, dass sie uebersetzen
# muss statt den Text direkt anzuzeigen.
LIB_GRP_PREFIX = "lib_grp_"
# IGDB-Plattform-IDs (für „beliebt pro Konsole")
IGDB_PLAT = {"snes":19,"nes":18,"n64":4,"gb":33,"gbc":22,"gba":24,"nds":20,"3ds":37,"ngc":21,
 "wii":5,"switch":130,"genesis":29,"sms":64,"gamegear":35,"saturn":32,"dreamcast":23,
 "psx":7,"ps2":8,"ps3":9,"psp":38,"xbox":11,"xbox360":12,"arcade":52,"turbografx16":86,
 "atari2600":59,"neogeo":80,"neo-geo-cd":136}
# Startseite: Reihenfolge der wichtigsten Konsolen
DISCOVER_ORDER = ["snes","nes","n64","gb","gba","genesis","psx","ps2","nds","ngc","dreamcast","arcade","switch"]
# Schlüsselwort -> bevorzugter Slug (für Archive.org-Titel/Sammlung und Fallback)
KW = [
 (r"super\s*nintendo|snes|super\s*famicom", "snes"),
 (r"nintendo\s*entertainment|\bnes\b|famicom", "nes"),
 (r"nintendo\s*64|\bn64\b", "n64"),
 (r"game\s*boy\s*advance|\bgba\b", "gba"),
 (r"game\s*boy\s*color|\bgbc\b", "gbc"),
 (r"game\s*boy", "gb"),
 (r"gamecube|\bngc\b|\bgcn\b|\bgc\b", "ngc"),
 (r"nintendo\s*ds|\bnds\b", "nds"),
 (r"nintendo\s*3ds|\b3ds\b", "3ds"),
 # Formatmarker zaehlen mit: Ein Release heisst oft nur `[NSP]` oder `XCI`. (#393)
 (r"\bswitch\b|\bnsw\b|\bnsp\b|\bxci\b", "switch"),
 (r"\bwii\s*u\b|wiiu|\bwup\b|\bwux\b|\bwud\b|\bwua\b", "wiiu"),
 (r"\bwii\b", "wii"),
 (r"virtual\s*boy", "virtualboy"),
 (r"mega\s*drive|megadrive|genesis|\bmd\b", "genesis"),
 (r"master\s*system", "sms"),
 (r"game\s*gear", "gamegear"),
 (r"sega\s*saturn|\bsaturn\b", "saturn"),
 (r"dreamcast", "dreamcast"),
 (r"sega\s*cd|mega\s*cd", "segacd"),
 (r"sega\s*32x|\b32x\b", "sega32x"),
 (r"playstation\s*portable|\bpsp\b", "psp"),
 # `PSVita` als EIN Wort ist die haeufigste Schreibweise — und `\bvita\b` traf sie nie:
 # zwischen `S` und `V` steht keine Wortgrenze. Gemessen 2 von 5 erkannt. (#393)
 (r"playstation\s*vita|\bpsvita\b|\bpsv\b|\bvita\b", "psvita"),
 (r"playstation\s*2|\bps2\b", "ps2"),
 (r"playstation\s*3|\bps3\b", "ps3"),
 # NICHT BEDIENTE PLATTFORMEN, und sie stehen VOR den allgemeineren Mustern (#607):
 # `playstation` allein faellt sonst auf `psx`, und `PS5` wurde bis dahin GAR NICHT
 # erkannt — `guess_platform` gab None zurueck, womit die Indexer-Kategorie gewann und
 # ein PS5-Release als Switch-Treffer erschien. Gemessen: drei der vier "Switch"-Treffer
 # fuer Resident Evil 4 waren PS5, einer davon 62 GB.
 (r"playstation\s*5|\bps5\b", "ps5"),
 (r"xbox[\s._-]*series|\bxsx\b|\bxss\b", "xboxseries"),   # Trenner: Release-Namen nutzen Punkte
 (r"playstation\s*4|\bps4\b", "ps4"),
 (r"playstation|\bpsx\b|\bps1\b|psone", "psx"),
 (r"xbox\s*360|\bx360\b", "xbox360"),
 (r"xbox\s*one", "xboxone"),
 (r"\bxbox\b|\bxbe\b", "xbox"),
 (r"turbografx|pc\s*engine|\bpce\b", "turbografx16"),
 (r"neo\s*geo\s*pocket", "neogeopocket"),
 # VOR dem allgemeinen Muster — sonst schluckt `neo geo` auch die CD. (#518)
 (r"neo[\s-]*geo[\s-]*cd", "neo-geo-cd"),
 (r"neo\s*geo", "neogeo"),
 (r"wonderswan", "wonderswan"),
 (r"atari\s*2600", "atari2600"),
 (r"atari\s*7800", "atari7800"),
 (r"atari\s*lynx|\blynx\b", "lynx"),
 (r"jaguar", "jaguar"),
 (r"\b3do\b", "3do"),
 (r"amiga", "amiga"),
 (r"commodore\s*64|\bc64\b", "c64"),
 (r"\bdos\b|ms-?dos", "dos"),
 (r"arcade|\bmame\b", "arcade"),
]

# WAS DIESER STACK NICHT BEDIENT (#607). Kein Ordner, kein Emulator, kein Importweg —
# ein solcher Treffer ist hier NIE richtig, egal unter welcher Kategorie er ankommt.
#
# Das ist ausdruecklich ein anderer Fall als #452: Dort ist die Kategorie eines Indexers
# zu grob (Wii U faehrt unter Wii mit), und die Regel „die Kategorie gewinnt" ist richtig.
# Hier gewinnt sie etwas, das niemand gebrauchen kann.
#
# EN: platforms this stack does not serve at all; such a hit is never right here, whatever
# category it arrives under — a different case from #452, where a category is merely coarse.
NICHT_BEDIENT = {"ps5", "xboxseries"}

def guess_platform(text):
    t = (text or "").lower()
    for pat, slug in KW:
        if re.search(pat, t): return slug
    return None

# Dateiendung -> Slug (eindeutige Cartridge-Systeme; Disc-Endungen bleiben offen)
EXT2PLAT = {"sfc":"snes","smc":"snes","nes":"nes","fds":"nes","n64":"n64","z64":"n64","v64":"n64",
 "ndd":"n64","gba":"gba","gbc":"gbc","gb":"gb","gg":"gamegear","sms":"sms","md":"genesis",
 "gen":"genesis","smd":"genesis","32x":"sega32x","pce":"turbografx16","sgx":"turbografx16",
 "ws":"wonderswan","wsc":"wonderswan","a26":"atari2600","a78":"atari7800","lnx":"lynx",
 "vec":"vectrex","j64":"jaguar","jag":"jaguar","3ds":"3ds","cia":"3ds","nsp":"switch",
 "xci":"switch","vb":"virtualboy","col":"colecovision","int":"intellivision","min":"pokemini",
            # Eindeutige Endungen -> Plattform. Sie schlagen den Hinweis aus dem Auftrag,
            # deshalb stehen hier nur solche, die es auf genau EINER Plattform gibt. (#391)
            "wux":"wiiu","wud":"wiiu","wua":"wiiu","rpx":"wiiu",
            "vpk":"psvita","xbe":"xbox",
            # Heimcomputer, NUR die eindeutigen (#410).
            "prg":"c64","crt":"c64","g64":"c64","p00":"c64","x64":"c64","d71":"c64","d81":"c64",
            "z80":"zxs","tzx":"zxs",
            "cdt":"acpc",
            "adz":"amiga","dms":"amiga",
            "a52":"atari5200"}
# BEWUSST NICHT ZUGEORDNET, obwohl importierbar (#410):
#   `.tap` — C64 UND ZX Spectrum. Beide Systeme, dieselbe Endung.
#   `.sna` — ZX Spectrum, aber auch ein Amiga-Schnappschussformat.
#   `.car` — Atari 5200, aber auch anderswo gebraucht.
# Sie stehen in `ROM_EXT`, damit die Dateien ankommen; die Plattform kommt aus dem Auftrag,
# der weiss, wonach gefragt wurde. Dieselbe Behandlung wie `.iso` und `.bin`.

# Titel, die keine ROMs sind -> aus der Suche filtern
NOISE_RE = re.compile(r'\b(winamp|skin|wallpaper|theme|soundtrack|\bost\b|manual|guide|artbook|'
                      r'source\s*code|github\.com|homebrew\s*dev|prototype\s*disc|magazine|'
                      r'strategy\s*guide|comic|sprite\s*sheet|music)\b', re.I)

# ---------- Normalisierung / Bibliotheks-Index ----------
# norm() bringt zwei Schreibweisen desselben Spiels auf denselben String, damit die
# Dedup („habe ich das schon?") funktioniert. REGION_RE entfernt Region-/Format-Tokens
# (USA, EUR, snes, v1.2 …), die nichts über die Identität des Spiels aussagen.
REGION_RE = re.compile(r'\b(usa|eur|europe|japan|jpn|world|korea|kor|rev\s*\d+|proper|repack|'
    r'nsw|xci|nsp|disc\s*\d+|snes|smc|sfc|nes|n64|z64|gba|gbc|\bgb\b|megadrive|genesis|'
    r'\bmd\b|psx|ps1|ps2|ps3|psp|switch|wii|gamecube|ngc|arcade|mame)\b')
#          ^^^ ps3 fehlte, waehrend ps1/ps2/psp dastanden. Folge: ein Ordner wie
#              "Ape Escape 4 PS3-EU BG" behielt seinen Plattform-Anhang und traf
#              keinen Katalogtitel — der Stream-Knopf erschien nie. (#152)

# Disc-/Produktkennung am Namensende: BLES00562, BLUS30232, BCUS99205, NPUB… — vier
# Buchstaben, fuenf Ziffern. PS3- und PSP-Abzuege tragen sie fast immer, und ohne diese
# Regel traf KEIN einziger PS3-Titel seinen Katalogeintrag: 9 von 10 startbaren Ordnern
# der Testbibliothek enden so.
#
# BEWUSST ENG GEFASST: `norm()` ist die Grundlage der Dedup. Eine grosszuegigere Regel
# (etwa „letztes kurzes Token weg") wuerde echte Titelbestandteile fressen und zwei
# verschiedene Spiele zusammenfallen lassen — ein Fehler, der sich still auswirkt.
# Vier Buchstaben plus fuenf Ziffern ist ein Format, kein Wort.
# Narrow on purpose: norm() is the dedup key, so a looser rule would silently merge
# distinct games. Four letters plus five digits is a format, not a word.
DISC_ID_RE = re.compile(r'\b[a-z]{4}\d{5}\b')

# Der Apostroph wurde bisher wie jedes andere Sonderzeichen durch ein LEERZEICHEN
# ersetzt. Damit wurde aus `O'Clock` -> `o clock`, waehrend ein Release, das ihn gar
# nicht erst schreibt (`OClock`), `oclock` ergab: zwei Schluessel fuer dasselbe Spiel.
# Betrifft jeden Genitiv — `Dragon's Lair`, `Bobby's World`, `Archer Maclean's 3D Pool`.
# An 315.706 Namen der echten Bibliothek gemessen: 160 Titelgruppen finden dadurch
# zusammen, und in 159 davon unterscheiden sich die Namen ausschliesslich in der
# Schreibweise. Deshalb ENTFERNEN statt ersetzen. (#615)
# EN: the apostrophe became a space, so `O'Clock` and `OClock` were different keys.
APOSTROPH_RE = re.compile(r"[’'`ʼ]")

# Derselbe Griff traf akzentuierte Buchstaben: `é` wurde zum LEERZEICHEN, also ergab
# `Pokémon` -> `pok mon` und `Pokemon` -> `pokemon`. Zwei Schluessel fuer denselben Titel,
# und zwar fuer einen der meistgefragten. An 315.706 Namen gemessen: 56 Titelgruppen fallen
# allein am Akzent auseinander. (#618)
#
# NFD zerlegt `é` in `e` + kombinierendes Akzentzeichen; letzteres traegt die Kategorie `Mn`
# und faellt weg. Das deckt alles ab, was im Bestand vorkommt — bis auf die folgenden, die
# GAR KEINE Zerlegung haben und deshalb einzeln stehen muessen.
#
# `ü` wird zu `u`, nicht zu `ue`: Die Paare im Bestand heissen `Zurück`/`Zuruck`, nicht
# `Zurück`/`Zurueck`. Grundbuchstabe ist die Regel, die zu den Daten passt.
#
# CJK, Hangul und IPA-Zeichen werden BEWUSST NICHT gefaltet (35 Vorkommen). Sie haben keinen
# sinnvollen ASCII-Grundbuchstaben; eine erfundene Zuordnung wuerde Kollisionen schaffen
# statt welche aufzuloesen. Fuer sie bleibt alles wie bisher.
# EN: fold accents to their base letter; the table covers what NFD cannot decompose.
SONDERBUCHSTABEN = str.maketrans({
    'ß': 'ss', 'ø': 'o', 'æ': 'ae', 'œ': 'oe', 'ð': 'd', 'đ': 'd', 'ł': 'l', 'þ': 'th',
})


def _grundbuchstaben(s):
    """Akzente auf den Grundbuchstaben abbilden. Erwartet kleingeschriebenen Text."""
    # 228 von 315.706 Namen der Bibliothek enthalten ueberhaupt Nicht-ASCII. Ohne diese
    # Abkuerzung liefe `normalize` fuer alle uebrigen umsonst und kostete beim Index-Aufbau
    # rund eine halbe Sekunde; mit ihr bleibt der Aufschlag im Messrauschen.
    if s.isascii():
        return s
    s = s.translate(SONDERBUCHSTABEN)
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')

# Szene-Releases haengen ihr Gruppenkuerzel hinter das Plattform-Token:
# `Sonic.X.Shadow.Generations.NSW.NiiNTENDO`, `Crime OClock NSW-SUXXORS`. REGION_RE warf
# `NSW` weg und liess `NiiNTENDO` stehen — damit war dasselbe Spiel von zwei Gruppen zwei
# verschiedene Schluessel, `in_library()` schwieg, und der Titel wurde ein zweites Mal
# geholt. Am Bestand gemessen: drei Spiele doppelt, 26 GB. (#615)
#
# BEWUSST SO ENG WIE DISC_ID_RE, und aus demselben Grund: Eine zu weite Regel laesst zwei
# Spiele still zusammenfallen. Drei Bedingungen, jede einzeln an der Bibliothek gepruefte
# Antwort auf einen konkreten Fehlgriff:
#
#   * NUR direkt hinter einem Plattform-Token am Namensende. Ein blosses „letztes Wort weg"
#     frisst Titelbestandteile.
#   * Mindestens vier Zeichen, keine roemische Ziffer, und im ORIGINAL mindestens zwei
#     Grossbuchstaben. Szene-Kuerzel schreiben sich SUXXORS, NiiNTENDO, LiGHTFORCE, ZER0;
#     `Edition` oder `Deluxe` tut das nie. Ohne diese Pruefung verschmolzen
#     `Aviator Arcade II` mit `Aviator` und `Commando Arcade SE` mit `COMMANDO`.
#   * `arcade` und `mame` stehen NICHT in der Liste, obwohl REGION_RE sie kennt: sie kommen
#     in echten Titeln vor. Mit den drei Bedingungen oben bleiben davon genau zwei Faelle
#     im Bestand uebrig, beide durchgehend gross geschrieben — `TERMINATOR_2_ARCADE_GAME`
#     haette `GAME` verloren, `Sears Super Video Arcade BIOS` sein `BIOS`. Der Ausschluss
#     ist also klein, aber nicht leer; die ALL-CAPS-Regel unten faengt dieselbe Falle
#     allgemein, auch fuer Token, die hier bleiben muessen.
#
# Wirkung an 315.706 echten Namen: fuenf Schluessel aendern sich, genau EINE zusaetzliche
# Titelgruppe findet zusammen — `IL-2 Sturmovik - Birds of Prey` mit seinem PSP-ZER0-Release.
# Null Fehlverschmelzungen.
# EN: strips a trailing scene group tag; deliberately narrow, see the three conditions above.
GRUPPE_PLAT = (r'(?:nsw|nsp|xci|switch|psx|ps1|ps2|ps3|psp|wii|gamecube|ngc|snes|n64|'
               r'gba|gbc|megadrive|genesis)')
GRUPPE_RE = re.compile(r'\b' + GRUPPE_PLAT + r'\s+([a-z0-9]{4,15})\s*$')
ROEMISCH = frozenset("i ii iii iv v vi vii viii ix x xi xii xiii xiv xv".split())
GROSS_RE = re.compile(r'[A-Z]')


def _schluessel_leer(s):
    """Bliebe nach den restlichen Schritten nichts uebrig?"""
    return not re.sub(r'[^a-z0-9]+', '', DISC_ID_RE.sub(' ', REGION_RE.sub(' ', s)))


def _ohne_gruppenkuerzel(s, roh):
    """Szene-Kuerzel am Ende entfernen — oder unveraendert lassen. Siehe GRUPPE_RE."""
    m = GRUPPE_RE.search(s)
    if not m:
        return s
    tok = m.group(1)
    if tok in ROEMISCH:
        return s
    # Ist der GANZE Name gross geschrieben, sagt die Grossschreibung des letzten Wortes
    # nichts mehr aus — dann besteht jedes Wort die Pruefung. `TERMINATOR_2_ARCADE_GAME`
    # haette so sein `GAME` verloren und waere mit `Terminator 2` verschmolzen.
    # EN: in an all-caps name the caps test carries no signal, so don't apply the rule.
    if roh.upper() == roh:
        return s
    # Grossschreibung im ORIGINAL pruefen, nicht im bereits kleingeschriebenen String.
    om = re.search(r'(?i)(?<![a-z0-9])' + re.escape(tok) + r'(?![a-z0-9])', roh)
    # Steht im Original ein BINDESTRICH direkt vor dem Kuerzel und endet der Name damit,
    # ist es nach Szene-Konvention immer die Gruppe — auch klein geschrieben. Das faengt
    # `NSW-nogrp`, `PS3-Caravan`, `Wii-Caravan` und `XCI-Ziperto`, die sonst haengen
    # blieben. Gemessen kostet es genau einen Fehlgriff in 315.706 Namen:
    # `camera-switch-symbolic`, eine Icon-Datei im c64-Ordner, also kein Titel.
    mit_strich = re.search(r'(?i)-' + re.escape(tok) + r'$', roh.strip())
    if not om or (len(GROSS_RE.findall(om.group(0))) < 2 and not mit_strich):
        return s
    gekuerzt = s[:m.start(1)] + s[m.end(1):]
    # `GBA-AENP` besteht nur aus Plattform-Token und Kuerzel. Ein leerer Schluessel
    # wuerde alles mit allem verschmelzen — dann lieber das Kuerzel behalten.
    return s if _schluessel_leer(gekuerzt) else gekuerzt


# `os.path.splitext()` haelt ALLES hinter dem letzten Punkt fuer eine Endung. In einem
# Titel mit Punkt loescht das echten Text:
#
#     splitext("R.B.I. Baseball (U) [!]")  ->  ('R.B.I', '. Baseball (U) [!]')
#     splitext("Sailor ... Vol. 3")        ->  ('Sailor ... Vol', '. 3')
#
# An 315.706 Namen gemessen: 10.551 verlieren so echten Text, und **1.307 Titelgruppen mit
# 5.401 Dateien** fallen dadurch auf einen gemeinsamen Schluessel — 60 verschiedene
# `R.B.I.`-Hacks unter einem, fuenf `Lipstick`-Baende unter einem. Das ist die Umkehrung
# von #615: dort war der Schluessel zu eng und holte doppelt, hier ist er zu weit und haelt
# einen fehlenden Band fuer vorhanden. (#617)
#
# ZWEI BEDINGUNGEN, weil eine allein nicht reicht:
#   * `ROM_EXT`/`ARCH_EXT` decken die bekannten Formate ab — aber nicht alles. `.p8`
#     (PICO-8) steht in keiner der beiden Listen und kommt 12.536-mal vor; bliebe es im
#     Schluessel, faende keine dieser Dateien mehr ihren Katalogeintrag.
#   * Deshalb zusaetzlich die Form: bis zu fuenf Zeichen, nur a-z0-9, und beginnt mit einem
#     BUCHSTABEN. Genau das trennt `.p8` von `.0f`, `.1`, `.55` und `.91` — Versionsnummern
#     sehen sonst wie Endungen aus. Ein Rest mit Leerzeichen oder Klammer ist ohnehin Text.
# EN: only strip something that actually looks like an extension; a dot inside a title is not one.
ENDUNG_RE = re.compile(r'^[a-z][a-z0-9]{0,4}$')


def _ohne_endung(name):
    stamm, ext = os.path.splitext(name)
    e = ext[1:].lower()
    return stamm if (e in ROM_EXT or e in ARCH_EXT or ENDUNG_RE.match(e)) else name


def norm(name):
    """Datei-/Titelname -> normalisierter Vergleichsschlüssel (Endung, Klammern, Region,
    Versionsnummern und Sonderzeichen entfernt, lowercase). Grundlage der Dedup."""
    roh = _ohne_endung(str(name)[:MAX_NAME])                   # gedeckelt: siehe _tags
    s = roh.lower()
    s = re.sub(r'[\._\-+]+', ' ', s)                          # Trenner ZUERST zu Space
    s = re.sub(r'\([^)]*\)|\[[^\]]*\]|\{[^}]*\}', ' ', s)     # (USA), [!], {...}
    s = re.sub(r'\bv?\d+(\.\d+)+\b', ' ', s)                   # v1.2.3
    s = _ohne_gruppenkuerzel(s, roh)                           # …NSW-SUXXORS (#615)
    s = REGION_RE.sub(' ', s)                                  # Region/Plattform-Tokens
    s = DISC_ID_RE.sub(' ', s)                                 # BLES00562, BLUS30232 …
    s = APOSTROPH_RE.sub('', s)                                # O'Clock == OClock (#615)
    s = _grundbuchstaben(s)                                    # Pokémon == Pokemon (#618)
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

# ---------- Fassungen: Region / Revision / Sprache / Dump-Status (#77) ----------
# Ein ROM-Titel ist fast nie EINE Datei. Dasselbe Spiel gibt es als USA-, Europa- und
# Japan-Fassung, als Revision, als Beta oder Prototyp, als Übersetzungspatch. Das ist
# KEINE Qualitätsleiter — Region ändert Inhalt (Sprache, Schwierigkeit, Zensur, 50/60 Hz),
# und „neueste Revision" ist nicht immer die beste. Deshalb wird hier nichts sortiert,
# sondern gelesen, gezeigt und ausgewählt.
#
# Gelesen werden die üblichen Namenskonventionen (No-Intro, Redump, TOSEC, GoodTools).
# Grundregel: Was nicht dasteht, wird NICHT geraten — unbekannt bleibt unbekannt.
REGIONS = {   # Anzeigename -> erkannte Schreibweisen (No-Intro/Redump-Langform + GoodTools-Kürzel)
    "World":     ["world", "w"],
    "USA":       ["usa", "us", "u", "ntsc-u", "ntsc-us", "america", "north america"],
    "Europe":    ["europe", "eur", "e", "pal", "pal-e"],
    "Japan":     ["japan", "jpn", "jp", "j", "ntsc-j"],   # 'jp' ist KEIN No-Intro-Sprachcode (das ist 'ja')
    "Germany":   ["germany", "ger", "g"],
    "France":    ["france", "fra", "f"],
    "Spain":     ["spain", "spa", "s"],
    "Italy":     ["italy", "ita", "i"],
    "Netherlands": ["netherlands", "holland"],
    "Sweden":    ["sweden", "swe", "sw"],
    "Australia": ["australia", "aus", "a"],
    "Korea":     ["korea", "kor", "k"],
    "China":     ["china", "chn", "ch"],
    "Taiwan":    ["taiwan", "twn"],
    "Brazil":    ["brazil", "bra", "b"],
    "Canada":    ["canada", "can"],
    "Asia":      ["asia"],
    "Russia":    ["russia", "rus"],
    "UK":        ["uk", "united kingdom"],
}
_REGION_TOKEN = {tok: name for name, toks in REGIONS.items() for tok in toks}
# No-Intro-Sprachcodes. Zwei Buchstaben = Sprache, EIN Buchstabe = GoodTools-Region —
# daran hängt die Unterscheidung von „(E)" (Europa) und „(En)" (Englisch).
LANG_CODES = {"en", "ja", "fr", "de", "es", "it", "nl", "pt", "sv", "no", "da",
              "fi", "zh", "ko", "pl", "ru", "cs", "hu", "tr", "el", "he", "ar"}
DUMP_TAGS = [   # Reihenfolge = Vorrang bei mehreren Treffern
    ("hack",        [r"\bhack\b", r"^\[t[\+\-]", r"\btrainer\b", r"\btrained\b"]),
    ("translation", [r"\btranslation\b", r"^t[\+\-]\w", r"\btranslated\b"]),
    ("prototype",   [r"\bproto(type)?\b"]),
    ("beta",        [r"\bbeta\b"]),
    ("alpha",       [r"\balpha\b"]),
    ("demo",        [r"\bdemo\b", r"\bkiosk\b"]),
    ("sample",      [r"\bsample\b"]),
    ("unlicensed",  [r"\bunl\b", r"\bunlicensed\b", r"\baftermarket\b", r"\bpirate\b"]),
    ("bad",         [r"^\[b\d*\]$", r"\bbad\s*dump\b", r"\boverdump\b"]),
]
PRERELEASE = {"prototype", "beta", "alpha", "demo", "sample"}   # standardmäßig nicht gewollt

MAX_NAME = 300   # Release-Namen sind nie länger; deckelt den Aufwand der Klammer-Regexe

def _tags(name):
    """Alle Klammer-/Klammerausdrücke eines Release-Namens: (USA), [!], (Rev A) …

    Die Eingabe wird gedeckelt: Titel stammen aus fremden Indexern, und die Alternation
    über unbalancierte Klammern läuft ungedeckelt quadratisch."""
    out = []
    for a, b in re.findall(r'\(([^)]*)\)|\[([^\]]*)\]', (name or "")[:MAX_NAME]):
        t = (a or b).strip()
        if t: out.append(t)
    return out

def parse_release(name):
    """Release-Name -> Fassungs-Merkmale.

    Rückgabe: regions (Liste), languages (Liste), revision (str|""), dump (str),
    `known` (bool: wurde überhaupt etwas erkannt). Was nicht dasteht, bleibt leer —
    ein unlesbarer Name wird zu „unspezifiziert", NIEMALS zu einem falschen Etikett."""
    out = {"regions": [], "languages": [], "revision": "", "dump": "", "known": False}
    if not name: return out
    low = str(name)[:MAX_NAME].lower()
    for raw in _tags(name):
        low_tag = raw.lower().strip()
        parts = [p.strip() for p in re.split(r'[,+/]', low_tag) if p.strip()]
        for p in parts:
            # Reihenfolge ist entscheidend: EIN Buchstabe ist GoodTools-Region ((E)=Europa),
            # ZWEI Buchstaben mit bekanntem Sprachcode sind Sprache ((En)=Englisch, (De)=Deutsch).
            if len(p) == 2 and p in LANG_CODES:
                if p not in out["languages"]: out["languages"].append(p)
            elif p in _REGION_TOKEN:
                r = _REGION_TOKEN[p]
                if r not in out["regions"]: out["regions"].append(r)
        m = re.match(r'^(?:rev(?:ision)?\s*([0-9a-z]+)|v\s*([0-9][0-9.]*))$', low_tag)
        if m and not out["revision"]:
            out["revision"] = "Rev " + (m.group(1) or m.group(2)).upper()
        # GoodTools-Mehrsprachigkeit (M3) sagt „3 Sprachen", nicht welche — als Hinweis merken
        if re.fullmatch(r'm\d+', low_tag) and "multi" not in out["languages"]:
            out["languages"].append("multi")
    if not out["revision"]:
        m = re.search(r'\brev(?:ision)?\s*([0-9a-z]{1,3})\b', low)
        if m: out["revision"] = "Rev " + m.group(1).upper()
    for status, pats in DUMP_TAGS:
        hay = [t.lower() for t in _tags(name)] + [low]
        if any(re.search(p, h) for p in pats for h in hay):
            out["dump"] = status; break
    out["known"] = bool(out["regions"] or out["languages"] or out["revision"] or out["dump"])
    return out

def variant_label(v):
    """Kurzes, ehrliches Etikett. Ohne Erkennung: „unspezifiziert" statt einer Erfindung."""
    bits = []
    if v.get("regions"): bits.append("/".join(v["regions"]))
    if v.get("languages"): bits.append(",".join(x.upper() for x in v["languages"]))
    if v.get("revision"): bits.append(v["revision"])
    if v.get("dump"): bits.append(v["dump"])
    return " · ".join(bits) if bits else ""

DEFAULT_VARIANT_PREFS = {"regions": ["Europe", "USA", "World", "Japan"], "lang": "", "prerelease": False}

def variant_prefs(user=""):
    """Nutzer-Voreinstellung schlägt Instanz-Voreinstellung schlägt Standard."""
    p = dict(DEFAULT_VARIANT_PREFS)
    inst = (load_settings().get("variant") or {})
    for k in p:
        if inst.get(k) not in (None, "", []): p[k] = inst[k]
    if user:
        u = (load_users().get(user, {}).get("variant") or {})
        for k in p:
            if u.get(k) not in (None, "", []): p[k] = u[k]
    p["regions"] = [r for r in (p.get("regions") or []) if r in REGIONS]
    p["prerelease"] = bool(p.get("prerelease"))
    return p

def sanitize_variant_prefs(d):
    """Eingaben festklopfen: nur bekannte Regionen, bekannter Sprachcode, Bool."""
    d = d if isinstance(d, dict) else {}
    regions = [r for r in (d.get("regions") or []) if r in REGIONS][:8]
    lang = str(d.get("lang") or "").lower()
    return {"regions": regions, "lang": lang if lang in LANG_CODES else "",
            "prerelease": bool(d.get("prerelease"))}

def variant_rank(v, prefs):
    """Sortierschlüssel für Kandidaten — KEINE Qualitätsleiter, sondern die Reihenfolge,
    die der Nutzer angegeben hat. Kleiner ist besser."""
    regions = prefs.get("regions") or []
    pos = min((regions.index(r) for r in v.get("regions", []) if r in regions), default=len(regions))
    unwanted = 1 if (v.get("dump") in PRERELEASE and not prefs.get("prerelease")) else 0
    broken = 1 if v.get("dump") in ("bad",) else 0
    lang = 0 if (prefs.get("lang") and prefs["lang"] in v.get("languages", [])) else 1
    # Revision zuletzt und nur als Gleichstand-Brecher: „neuer" ist nicht automatisch „besser".
    rev = -1 * len(v.get("revision", ""))
    return (broken, unwanted, pos, lang, rev)

# RAM-Abbild des Bibliotheks-Index (schnelles in_library): per = {slug: {norm,…}},
# all = alle norms plattformübergreifend, slugs = vorhandene Plattform-Ordner, ts = Bauzeit.
LIB = {"per": {}, "all": set(), "slugs": set(), "ts": 0, "failed": {}}
LIB_LOCK = threading.Lock()

# ---------- SQLite: persistenter Bibliotheks-Index ----------
# Der Index (zehntausende Titel) wird zusätzlich in SQLite gehalten, damit der Start den
# RAM-Index aus der DB laden kann (~1 s) statt jedes Mal das Dateisystem zu durchlaufen (~24 s).
DB_LOCK = threading.Lock()   # serialisiert SCHREIBende Zugriffe; Reads laufen dank WAL lock-frei

def db_conn():
    """Neue SQLite-Verbindung im WAL-Modus. Aufrufer schließt sie via contextlib.closing
    (pro-Aufruf-Verbindungen, sonst FD-Leck). WAL erlaubt Leser parallel zum einen Schreiber."""
    c = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=30000")
    return c

def _migrate_json(c, count_sql, insert_sql, path, rows_fn):
    """JSON-Datei einmalig in eine leere Tabelle übernehmen (literale SQL). rename erst nach Commit."""
    if c.execute(count_sql).fetchone()[0] or not os.path.exists(path):
        return False
    try:
        data = json.load(open(path))
    except Exception as e:
        log(f"Migration {path}: JSON-Fehler {e}"); return False
    rows = rows_fn(data)
    if not rows: return False
    c.executemany(insert_sql, rows)
    return True

# Kleiner Key-Value-Store in SQLite für kleine Ganzobjekt-Stores (settings/issues/maillog/push):
# ein JSON-Blob je Schlüssel. Bewusst kein relationales Schema — diese Daten werden immer als
# Ganzes geladen/gespeichert; so bleibt es einfach, aber alles liegt transaktionssicher in der DB.
def kv_get(key, default):
    try:
        with closing(db_conn()) as c:
            r = c.execute("SELECT data FROM kv WHERE k=?", (key,)).fetchone()
            return json.loads(r[0]) if r else default
    except Exception:
        return default
def kv_put(key, value):
    try:
        with DB_LOCK, closing(db_conn()) as c, c:
            c.execute("INSERT OR REPLACE INTO kv(k,data) VALUES(?,?)", (key, json.dumps(value)))
    except Exception as e:
        log(f"kv-Speichern-Fehler {key}: {e}")
def _migrate_kv(c, key, path):
    """JSON-Datei einmalig als kv-Blob übernehmen (parametrisiert). rename erst nach Commit."""
    if c.execute("SELECT COUNT(*) FROM kv WHERE k=?", (key,)).fetchone()[0] or not os.path.exists(path):
        return False
    try: data = json.load(open(path))
    except Exception as e: log(f"kv-Migration {path}: {e}"); return False
    c.execute("INSERT OR REPLACE INTO kv(k,data) VALUES(?,?)", (key, json.dumps(data)))
    return True

def db_init():
    try:
        # WAL/Init + Schema in einer Schreib-Transaktion
        with DB_LOCK, closing(db_conn()) as c, c:
            c.execute("CREATE TABLE IF NOT EXISTS library(slug TEXT, norm TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_lib_norm ON library(norm)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_lib_slug ON library(slug, norm)")
            # Anzeigename je Titel (#293). `norm` ist kleingeschrieben und entkernt —
            # als Bibliotheksliste unlesbar. Nachgerüstet statt neu angelegt, damit
            # bestehende Datenbanken nicht neu aufgebaut werden muessen; der naechste
            # Index-Lauf fuellt die Spalte.
            if "name" not in {r[1] for r in c.execute("PRAGMA table_info(library)")}:
                c.execute("ALTER TABLE library ADD COLUMN name TEXT")
            c.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT)")
            # Katalog = „welche Titel gibt es für diese Plattform" (Momentaufnahme aus IGDB).
            # Getrennt von `library` (= was wir haben); die Differenz ist die Abdeckung. (#78)
            c.execute("CREATE TABLE IF NOT EXISTS catalog(slug TEXT, norm TEXT, name TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_cat_slug ON catalog(slug, norm)")
            # RetroAchievements: je Konsole die Titel MIT Achievement-Set. Vorab geholt, damit
            # die Detailseite ohne Netzzugriff auskommt und die Zuordnung über eine kuratierte
            # Liste läuft statt über eine Freitextsuche. (#79)
            c.execute("CREATE TABLE IF NOT EXISTS ra_games(slug TEXT, norm TEXT, ra_id INTEGER, "
                      "title TEXT, achievements INTEGER, points INTEGER)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_ra_slug ON ra_games(slug, norm)")
            # Filehoster-Katalog: Momentaufnahmen der in den Einstellungen hinterlegten
            # Katalog-JSONs. Die QUELLEN stehen nie im Repo — nur der Parser. (#63)
            c.execute("CREATE TABLE IF NOT EXISTS fh_items(norm TEXT, title TEXT, uris TEXT, "
                      "size TEXT, uploaded TEXT, src TEXT, url TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_fh_norm ON fh_items(norm)")
            c.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, data TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS jobs(seq INTEGER PRIMARY KEY AUTOINCREMENT, jid TEXT, data TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, data TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, "
                      "sender TEXT, recipient TEXT, body TEXT, ts INTEGER, read INTEGER DEFAULT 0)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_msg_rcpt ON messages(recipient, read)")
            mig_u = _migrate_json(c, "SELECT COUNT(*) FROM users",
                                  "INSERT OR REPLACE INTO users(username,data) VALUES(?,?)", USERS_FILE,
                                  lambda d: [(k, json.dumps(v)) for k, v in d.items()] if isinstance(d, dict) else [])
            mig_j = _migrate_json(c, "SELECT COUNT(*) FROM jobs",
                                  "INSERT INTO jobs(jid,data) VALUES(?,?)", JOBDB,
                                  lambda d: [(j.get("id",""), json.dumps(j)) for j in d] if isinstance(d, list) else [])
            kv_migs = [(SETTINGS_FILE, _migrate_kv(c, "settings", SETTINGS_FILE)),
                       (ISSUES_FILE,   _migrate_kv(c, "issues",   ISSUES_FILE)),
                       (MAILLOG_FILE,  _migrate_kv(c, "maillog",  MAILLOG_FILE)),
                       (PUSH_FILE,     _migrate_kv(c, "push",     PUSH_FILE))]
        # rename der Quelldateien erst NACH erfolgreichem Commit (verlustfrei)
        if mig_u: os.rename(USERS_FILE, USERS_FILE + ".migrated"); log("users.json -> SQLite migriert")
        if mig_j: os.rename(JOBDB, JOBDB + ".migrated"); log("jobs.json -> SQLite migriert")
        for path, done in kv_migs:
            if done: os.rename(path, path + ".migrated"); log(f"{os.path.basename(path)} -> SQLite migriert")
    except Exception as e:
        log(f"DB-Init-Fehler: {e}")

def schreibe_geheim(pfad, inhalt):
    """Schluesselmaterial mit 0600 schreiben, nicht mit der Standard-umask. (#192)

    Beide Dateien hier — `secret.key` (Sitzungssignatur) und `vapid.json` (privater
    Push-Schluessel) — entstanden bisher ueber ein schlichtes `open(..., "w")` und lagen
    damit auf einer gemessenen Installation als **0664** im Konfigverzeichnis: lesbar fuer
    Gruppe und alle anderen. Bei einem Verzeichnis, das per Bind-Mount aus einem Container
    kommt, ist das keine theoretische Groesse.

    Key material is written with an explicit 0600 rather than whatever the umask allows;
    on a measured installation both files sat at 0664 in a bind-mounted config directory.
    """
    fd = os.open(pfad, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, inhalt.encode() if isinstance(inhalt, str) else inhalt)
    finally:
        os.close(fd)

def geheim_absichern(pfad):
    """Bestehendes Schluesselmaterial auf 0600 nachziehen. (#192)

    Neue Dateien entstehen ueber `schreibe_geheim`; diese Funktion ist fuer die, die es
    schon gibt — ein Fix, der nur bei Neuinstallationen wirkt, repariert keine einzige
    laufende Anlage.

    New files come from `schreibe_geheim`; this one exists for the files that are already
    there, because a fix that only applies to fresh installs repairs nothing that runs.
    """
    try:
        modus = os.stat(pfad).st_mode & 0o777
        if modus & 0o077:
            os.chmod(pfad, 0o600)
            log(f"Rechte auf 0600 gesetzt (war {modus:o}): {os.path.basename(pfad)}")
    except OSError:
        pass

def geheimnisse_absichern():
    """Alles bekannte Schluesselmaterial beim Start auf 0600 ziehen. (#256)

    `geheim_absichern` beim Lesen reicht nicht: `vapid.json` wird nur angefasst, wenn
    Web-Push tatsaechlich benutzt wird. Auf der gemessenen Anlage ist das nie der Fall —
    also behielt ausgerechnet der Schluessel die offenen Rechte, den niemand anfasst. Das
    ist genau verkehrt herum, ein ungenutztes Geheimnis ist kein sichereres Geheimnis.

    EN: tightening on read is not enough — a key nobody reads keeps its loose permissions,
    which is exactly backwards. This runs at startup regardless of use.
    """
    for pfad in (SECRET_FILE, VAPID_FILE, TLS_CERT, TLS_KEY):
        if os.path.exists(pfad):
            geheim_absichern(pfad)

def save_index_to_db(per, allset, slugs, ts, namen=None):
    """RAM-Index atomar in SQLite spiegeln (library-Tabelle komplett ersetzen + meta-Zähler).

    `namen` bildet (slug, norm) -> Anzeigename ab (#293). Fehlt es, bleibt die Spalte
    leer und die Bibliotheksansicht faellt auf `norm` zurueck — die Liste ist dann
    haesslich, aber nicht falsch.
    """
    namen = namen or {}
    rows = [(slug, n, namen.get((slug, n))) for slug, s in per.items() for n in s]
    try:
        with DB_LOCK, closing(db_conn()) as c, c:
            c.execute("DELETE FROM library")
            c.executemany("INSERT INTO library(slug,norm,name) VALUES(?,?,?)", rows)
            c.executemany("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                          [("index_ts", str(ts)), ("index_titles", str(len(allset))),
                           ("index_platforms", str(len(slugs))), ("slugs", json.dumps(sorted(slugs)))])
    except Exception as e:
        log(f"Index-DB-Speichern-Fehler: {e}")

def load_index_from_db():
    """RAM-Index aus SQLite füllen. Gibt den Zeitstempel zurück oder None."""
    try:
        with closing(db_conn()) as c:
            row = c.execute("SELECT value FROM meta WHERE key='index_ts'").fetchone()
            if not row: return None
            ts = float(row[0])
            per, allset = {}, set()
            for slug, n in c.execute("SELECT slug,norm FROM library"):
                per.setdefault(slug, set()).add(n); allset.add(n)
            sl = c.execute("SELECT value FROM meta WHERE key='slugs'").fetchone()
            slugs = set(json.loads(sl[0])) if sl else set(per.keys())
            for s in slugs: per.setdefault(s, set())
        with LIB_LOCK:
            LIB["per"], LIB["all"], LIB["slugs"], LIB["ts"] = per, allset, slugs, ts
        return ts
    except Exception as e:
        log(f"Index-DB-Laden-Fehler: {e}"); return None

# ---------- Ordnernamen -> Plattform (#124) ----------
# Drei Systeme sehen dieselben Ordner und meinen Verschiedenes damit:
#
#   RetroNAS  legt den Baum SELBST an (633 Ordner, davon 406 leer) und bestimmt damit
#             die Namen. Umbenennen haelt bis zu seinem naechsten Lauf.
#   RomM      nimmt den Ordnernamen woertlich als Plattform — es versteht sie ebenso
#             wenig, meldet es aber nicht.
#   Romseerr  schlug sie bisher nach und meldete "unbekannt" — die Plattform verschwand
#             samt Inhalt aus Abdeckung, Spielen und Streamen.
#
# WARUM EINE TABELLE UND KEINE SYMLINKS: Ein Symlink auf ein Verzeichnis IST fuer RomM
# ein Verzeichnis. `ngc -> gc` ergaebe zwei Plattformen mit denselben Dateien, also eine
# doppelte Bibliothek. Und ein Umbenennen macht RetroNAS beim naechsten Lauf rueckgaengig,
# wonach die Bibliothek still auf zwei Ordner verteilt liegt.
#
# Diese Tabelle aendert nichts auf der Platte, uebersteht jeden RetroNAS-Lauf und wirkt
# bei jeder Installation ohne Zutun des Betreibers.
#
# Three systems read the same folders and mean different things by them. A table beats
# symlinks (RomM would scan both and duplicate the library) and beats renaming (RetroNAS
# recreates its own names on the next run, splitting the library silently).
FOLDER_ALIASES = {
    "gc": "ngc",                       # GameCube
    "dc": "dreamcast",
    "tg16": "turbografx16",
    "turbografx-cd": "turbografx16",
    "neogeoaes": "neogeo", "neogeomvs": "neogeo",
    # `neo-geo-cd` steht bewusst NICHT hier (#518). AES und MVS sind dieselbe
    # Hardware in anderen Gehaeusen; die Neo Geo CD ist eine eigene Konsole mit
    # eigenem BIOS und CD-Abbildern statt Cartridge-Romsets.
    #
    # ENTSCHEIDEND IST ABER NICHT DIE HISTORIE, SONDERN DASS ROMM SIE TRENNT:
    #
    #     RomM: Neo Geo AES  neogeoaes    300 ROMs
    #           Neo Geo CD   neo-geo-cd   100 ROMs
    #           (eine Plattform `neogeo` gibt es dort gar nicht)
    #
    # Solange der Alias stand, fragte `romm_find` nach `neogeo` und bekam nichts:
    #     romm_find("Aero Fighters 2 (World)", "neogeo")      -> None
    #     romm_find("Aero Fighters 2 (World)", "neo-geo-cd")  -> Aero Fighters 2
    # 100 vorhandene, gescannte Titel waren damit unspielbar.
    # EN: RomM keeps them apart, so aliasing them together made romm_find miss
    # every CD title.
    "neo-geo-pocket": "neogeopocket", "neo-geo-pocket-color": "neogeopocket",
    "wonderswan-color": "wonderswan",
    "sega32": "sega32x", "sega-32x": "sega32x",
    "gen": "genesis",
    "famicom": "nes", "fds": "nes",
    "sfam": "snes", "satellaview": "snes", "sufami-turbo": "snes",
    "atari-jaguar-cd": "jaguar",
    # Arcade-Romsets sind keine eigenen Plattformen, sondern Teilmengen desselben Kerns.
    "c-plus-4": "c16", "plus4": "c16",  # dieselbe Maschinenfamilie, derselbe Kern
    "c128": "c64",
    "vic-20": "vic20",
    "zx-spectrum": "zxs", "spectrum": "zxs",
    "amstrad": "acpc", "cpc": "acpc",
    "coleco": "colecovision",
    "cps1": "arcade", "cps2": "arcade", "cps3": "arcade",
    "atomiswave": "arcade", "stv": "arcade",
}

# Ordner, die GAR KEINE Plattform sind. Ohne diese Liste werden sie zu einer — in RomM
# ist das bereits passiert (dort existiert eine Plattform "VVVVVV Data file").
# Folders that are not platforms at all; without this they become one.
IGNORE_FOLDERS = {
    "VVVVVV Data file for RPi",        # eine Spieldatendatei (data.zip)
    "Amiga-Fullset", "Amiga-Fullset.rar",
    # Emulator- und Firmware-Ordner, keine Plattformen. NACHGESEHEN, nicht vermutet: der
    # Unterschied ist „kein Spielinhalt" gegen „Inhalt ohne Kern", und nur Ersteres darf
    # verschwinden. `RG350` (.opk-Pakete) und `LCD Handhelds` (.mgw-Dateien) stehen
    # deshalb bewusst NICHT hier — das sind Spiele, denen im Player nur der Kern fehlt,
    # und sie zu verstecken wuerde eine Luecke als Ordnung ausgeben. (#124)
    # Emulator and firmware directories. Checked, not assumed: "no game content" is a
    # different thing from "content without a core", and only the former may disappear.
    "WinUAE1610",                      # Amiga-Emulator samt Konfiguration und Aufzeichnungen
    "Dingoo",                          # enthaelt einen Firmware-Installer, keine Spiele
    # `Mixed` ist eine ABLAGE, kein System — und war lange Romseerrs eigene Erfindung:
    # `resolve_slug("")` gab den Namen zurueck, der Import legte den Ordner an, der Index
    # machte eine Plattform daraus. Die Ursache ist weg (#367); der Ordner bleibt, weil
    # RetroNAS ihn ebenfalls anlegt und weil dort echte Dateien liegen — 707 gemessen,
    # davon 198 Intellivision-ROMs. Sie einzusortieren ist #366; sie als System zu fuehren
    # war immer falsch.
    #
    # WAS DAS KOSTET, offen gesagt: Die Bibliothekszahl faellt um die dort gezaehlten
    # Titel. Das ist eine Korrektur, kein Verlust — es waren nie Titel eines Systems.
    #
    # Mixed is a holding area, not a system, and was Romseerr's own invention. The cause is
    # gone; the folder stays because RetroNAS creates it too and it holds real files.
    "Mixed",
}

# XSym: das Symlink-Format, mit dem Netatalk/Samba Verweise auf Dateisystemen ablegen,
# die keine kennen. Genau 1067 Byte gross, beginnend mit "XSym\n".
#
# WARUM DAS HIER STEHT: RetroNAS legt Herstellerordner (`nec`, `nintendo`, `sega`) an,
# deren gesamter Inhalt aus solchen Verweisen auf die echten Plattformordner besteht.
# Ueber SMB gelesen sind das gewoehnliche Dateien — und damit wurden sie zu Titeln, die
# Ordner zu Plattformen und die Ordner zu drei "unversorgten Plattformen", die es nie
# gab. Die Ordner am NAMEN zu verbieten waere falsch: in einer anderen Bibliothek ist
# `sega/` voller Mega-Drive-Spiele, und die duerfen nicht verschwinden. (#193)
#
# Die Groesse wird ZUERST geprueft, weil sie fast nie zutrifft — der Kopf wird deshalb
# nur bei einer Handvoll Dateien ueberhaupt gelesen.
# EN: XSym is the symlink format Netatalk/Samba use on filesystems without symlinks —
# exactly 1067 bytes starting with "XSym\n". Read over SMB they look like ordinary
# files and became titles. Banning the folder NAMES would be wrong: elsewhere `sega/`
# holds real games.
XSYM_GROESSE = 1067


def ist_xsym(pfad):
    """-> True, wenn die Datei ein XSym-Symlink ist und kein Spiel."""
    try:
        if os.path.getsize(pfad) != XSYM_GROESSE:
            return False
        with open(pfad, "rb") as f:
            return f.read(5) == b"XSym\n"
    except OSError:
        return False


def folder_slug(ordner):
    """Ordnername -> Plattform-Slug. Leer = ignorieren.

    Ohne Treffer bleibt der Name UNVERAENDERT: eine unbekannte Plattform ist kein
    Fehler, sondern eine, die dieses Projekt noch nicht kennt. Sie kleinzuschreiben
    oder zu raten wuerde bestehende Bibliotheken umsortieren."""
    if ordner in IGNORE_FOLDERS:
        return ""
    return FOLDER_ALIASES.get(ordner.lower(), ordner)


def slug_folders(slug):
    """Slug -> alle Ordner, die dazu beitragen. Aus der KONSTANTEN Tabelle abgeleitet,
    nie aus der Eingabe — dieselbe Regel wie bisher bei STREAM_DIR."""
    return [slug] + sorted(f for f, z in FOLDER_ALIASES.items() if z == slug)


def bibliothek_ordner(slug):
    """Slug -> Ordner, in den ein Import gehoert. (#454)

    Lesen kannte `FOLDER_ALIASES` laengst, Schreiben nicht: Das Ziel war schlicht
    `ROMS/<slug>`. Liegt die Bibliothek einer Plattform im Alias-Ordner — RetroNAS nennt
    GameCube `gc` und Dreamcast `dc` —, dann landete jeder Download DANEBEN statt DARIN,
    und der Bestand teilte sich lautlos in zwei Ordner. Sichtbar wurde das nicht, weil das
    Lesen beide wieder zusammenfuegt; auf der Platte war die Plattform trotzdem zweigeteilt,
    und alles, was die Ordner direkt liest (RomM, RetroNAS' Freigaben, ein blankes `ls`),
    sah nur eine Haelfte.

    Deshalb: der Ordner, in dem diese Plattform SCHON liegt, sonst der Slug. Die Reihenfolge
    kommt aus `slug_folders` und damit aus der konstanten Tabelle, nie aus der Eingabe.

    Slug -> the folder an import belongs in. Prefer a folder that already holds this
    platform's content, so an alias-named library does not get split in two.
    """
    for f in slug_folders(slug):
        p = os.path.join(ROMS, f)
        try:
            with os.scandir(p) as eintraege:     # `with`, sonst bleibt der Deskriptor offen
                if any(eintraege):
                    return p
        except OSError:                          # gibt es nicht, ist keiner, nicht lesbar
            continue
    return os.path.join(ROMS, slug)


INDEX_FEHLER_ZEIGEN = 10   # so viele Plattformnamen stehen in der Schlussmeldung

def _index_fehlertext(fehler):
    """Zusatz fuer die Schlussmeldung des Indexlaufs. Ohne Fehler: leer. (#381)

    Die Zeile mit der Titelzahl ist die, die gelesen wird — im Containerprotokoll, in
    der Fehlersuche, beim Vergleich zweier Laeufe. Steht dort nichts, ist eine Zahl,
    die stillschweigend Plattformen auslaesst, glaubwuerdiger als sie sein darf.
    LEER BLEIBEN IST TEIL DER SACHE: Eine Warnung, die immer dasteht, wird nicht gelesen.

    Gedeckelt, weil eine komplett nicht gemountete Freigabe sonst alle ~600 Namen in
    eine Zeile schriebe — die ZAHL ist dann die Auskunft, nicht die Liste.

    EN: the title-count line is the one people actually read; a total that silently
    omits platforms must not stand there alone. Capped — with the share unmounted the
    count is the information, not six hundred names.
    """
    if not fehler: return ""
    namen = sorted(fehler)
    kopf = ", ".join(f"{s} ({fehler[s]})" for s in namen[:INDEX_FEHLER_ZEIGEN])
    rest = len(namen) - INDEX_FEHLER_ZEIGEN
    if rest > 0: kopf += f", … (+{rest} weitere)"
    wort = "Plattform" if len(namen) == 1 else "Plattformen"
    return f" — {len(namen)} {wort} NICHT gelesen: {kopf}"


def build_index():
    """Bibliotheks-Index aus dem Dateisystem neu aufbauen (ROMS/<slug>/…, 2 Ebenen tief),
    in LIB (RAM) ablegen UND in SQLite persistieren. Läuft beim allerersten Start und
    danach periodisch im Hintergrund (periodic_index) sowie nach jedem Import."""
    per, allset, slugs = {}, set(), set()
    # Anzeigename je (slug, norm) — der Dateiname ohne Endung (#293). Bei mehreren
    # Dateien desselben Titels gewinnt der KUERZESTE: `Turrican.d64` ist als
    # Ueberschrift brauchbar, `Turrican (1990)(Rainbow Arts)[cr ABC][t +3].d64` nicht.
    namen = {}
    # Plattformen, deren Ordner NICHT gelesen werden konnte -> Fehlerart (#381).
    # Eine solche Plattform traegt null Titel bei und war bis hierher nicht von einer
    # wirklich leeren zu unterscheiden.
    fehler = {}
    try:
        for ordner in os.listdir(ROMS):
            p = os.path.join(ROMS, ordner)
            if not os.path.isdir(p): continue
            # Versteckte Ordner sind keine Plattformen (#321). Der Umbau der Bibliothek
            # legt sein Arbeitsverzeichnis als `.umbau` neben die Plattformen; dessen
            # Protokolldateien tauchten danach als 62 „Titel" in der Ansicht auf. Die
            # Regel gilt allgemein: Was mit einem Punkt beginnt, gehoert einem Werkzeug,
            # nicht der Bibliothek — `.cache`, `.stfolder` und Ordner von Synchronisations-
            # diensten haetten dasselbe Problem erzeugt.
            # A leading dot marks a tool's directory, not a platform; the library
            # reorganiser's `.umbau` showed up as 62 "titles" before this.
            if ordner.startswith("."): continue
            slug = folder_slug(ordner)
            if not slug: continue          # kein Plattformordner (#124)
            slugs.add(slug)
            # Mehrere Ordner koennen auf denselben Slug zeigen (cps1, cps2 -> arcade).
            # setdefault statt Zuweisung, sonst ueberschreibt der zweite den ersten.
            s = per.setdefault(slug, set())
            # WARUM `onerror` UND NICHT NUR DER `except`-ZWEIG UNTEN (#381):
            # `os.walk` WIRFT bei einem Lesefehler nichts. Ohne `onerror` ruft es
            # niemanden und liefert fuer den betroffenen Ordner einfach nichts —
            # der `except` unten wurde bei genau diesem Fall nie betreten. Rechte-,
            # Mount-, Symlink- und E/A-Fehler laufen allesamt hier durch.
            #
            # Live nachgemessen: `/roms/pico8` steht auf `drwx-w----`, der Container
            # darf schreiben, aber nicht lesen. 13.176 Titel wurden als 0 verbucht,
            # vier Indexlaeufe in Folge meldeten dieselbe Zahl ohne ein Wort dazu.
            #
            # EN: os.walk raises NOTHING on a read error — without onerror it silently
            # yields nothing, so the except below never fired for the very cases that
            # matter (permissions, unreadable mounts, broken symlinks, I/O errors).
            def _lesefehler(err, _slug=slug):
                # Erster Fehler je Plattform genuegt; ein gesperrter Baum wuerde sonst
                # dieselbe Meldung hundertfach schreiben.
                if _slug not in fehler:
                    fehler[_slug] = type(err).__name__
                    log(f"Index: Plattform {_slug} nicht vollstaendig gelesen: "
                        f"{type(err).__name__}: {err}")
            try:
                for root, dirs, files in os.walk(p, onerror=_lesefehler):
                    # EIN ORDNER, DER EIN SPIEL IST, IST EIN TITEL — und NICHT sein
                    # Innenleben. (#477)
                    #
                    # Der Import weiss das laengst (`SPIELORDNER_MUSTER`, #391), der Index
                    # wusste es nicht: Er lief hinein und legte die Bestandteile als Titel
                    # ab. Am Bestand gemessen, nach einem vollstaendigen Neuaufbau:
                    #
                    #   wiiu    31 Eintraege: `app`, `bootDrcTex`, `bootLogoTex`, `bootMovie`
                    #   psvita  14 Eintraege: `args`, `eboot`, `Gravite`, `icon`
                    #   ps3     27 Eintraege: `PS3_DISC`, `ICON0`, …
                    #
                    # `bootMovie` ist ein Video IN Captain Toad, `Gravite` die `.psarc` IN
                    # Gravity Rush. Die echten Titel fehlten ganz — und damit fand
                    # `stream_info` sie nicht, obwohl sie vollstaendig dalagen.
                    #
                    # EN: the import path has known this since #391; the index walked into
                    # the folder and filed its contents as titles, so a complete, present
                    # title was unreachable through the UI.
                    if root != p and ist_titel_ordner(root):
                        name = os.path.basename(root)
                        n = norm(name)
                        if n:
                            s.add(n); allset.add(n)
                            anzeige = os.path.splitext(name)[0].strip() or name
                            vorher = namen.get((slug, n))
                            if vorher is None or len(anzeige) < len(vorher):
                                namen[(slug, n)] = anzeige
                        dirs[:] = []       # nicht hineinlaufen
                        continue
                    for fn in files:
                        n = norm(fn)
                        if not n: continue
                        # Symlink-Platzhalter sind keine Titel (#193). Die Pruefung
                        # kostet fast nichts: sie sieht zuerst auf die Groesse.
                        if ist_xsym(os.path.join(root, fn)): continue
                        s.add(n); allset.add(n)
                        anzeige = os.path.splitext(fn)[0].strip() or fn
                        vorher = namen.get((slug, n))
                        if vorher is None or len(anzeige) < len(vorher):
                            namen[(slug, n)] = anzeige
                    # nur zwei Ebenen tief laufen (Performance)
                    if root != p and os.path.relpath(root, p).count(os.sep) >= 1:
                        dirs[:] = []
            except Exception as e:
                # Netz fuer alles, was NICHT ueber `onerror` laeuft. Frueher `pass` —
                # und damit die einzige Stelle, an der ein Fehler ganz verschwand.
                fehler.setdefault(slug, type(e).__name__)
                log(f"Index: Plattform {slug} abgebrochen: {type(e).__name__}: {e}")
    except Exception as e:
        log(f"Index-Fehler: {e}")
    ts = time.time()
    with LIB_LOCK:
        LIB["per"], LIB["all"], LIB["slugs"], LIB["ts"] = per, allset, slugs, ts
        LIB["failed"] = fehler
    save_index_to_db(per, allset, slugs, ts, namen)   # persistieren -> schneller Neustart
    log(f"Bibliotheks-Index: {len(slugs)} Plattformen, {len(allset)} Titel "
        f"(in DB gesichert){_index_fehlertext(fehler)}")
    refresh_coverage_counts()   # Abdeckung folgt der Bibliothek, wird nicht je Request gerechnet (#78)

# ---------- Abdeckung je Plattform (#78) ----------
# „412 von 1.180" — die Frage, die ein sammelnder Nutzer zuerst stellt. Dafür braucht es
# neben dem, was da ist (`library`), eine Vorstellung davon, was es GIBT (`catalog`).
#
# WICHTIG: Eine Prozentzahl ohne Grundlage lädt zu falschen Schlüssen ein. Metadaten-Sätze
# sind sich uneins, was als eigener Titel zählt (Regionalfassungen, Revisionen, Unlizenziertes).
# Deshalb steht an JEDER Zahl die Quelle und der Stand der Momentaufnahme — auch in der API.
CATALOG_SOURCE = "IGDB"
CATALOG_MAX    = 3000        # Titel je Plattform (darüber wird die Zahl als Untergrenze geführt)
CATALOG_PAGE   = 500         # IGDB-Maximum je Abfrage
COVERAGE_LOCK  = threading.Lock()

def load_coverage(): return kv_get("coverage", {})
def save_coverage(c): kv_put("coverage", c)

def fetch_catalog(slug):
    """Titelliste einer Plattform von IGDB holen und die Katalogtabelle für sie ersetzen.

    Nur Hauptspiele (`category = 0`), damit DLC und Editionen die Grundgesamtheit nicht
    aufblähen. Liefert die Zahl der gespeicherten Titel oder None, wenn die Quelle nichts
    hergibt — dann wird bewusst KEINE Momentaufnahme geschrieben, statt 0 zu behaupten."""
    pid = IGDB_PLAT.get(slug)
    if not pid or not igdb_token(): return None
    rows, offset = [], 0
    while offset < CATALOG_MAX:
        d = igdb_query("games", f'fields name; where platforms=({pid}) & category = 0; '
                                f'sort name asc; limit {CATALOG_PAGE}; offset {offset};')
        if not isinstance(d, list) or not d: break
        for g in d:
            nm = (g or {}).get("name") or ""
            n = norm(nm)
            if n: rows.append((slug, n, nm))
        if len(d) < CATALOG_PAGE: break
        offset += CATALOG_PAGE
    if not rows: return None
    seen, uniq = set(), []
    for slg, n, nm in rows:
        if n in seen: continue
        seen.add(n); uniq.append((slg, n, nm))
    try:
        with DB_LOCK, closing(db_conn()) as c, c:
            c.execute("DELETE FROM catalog WHERE slug=?", (slug,))
            c.executemany("INSERT INTO catalog(slug,norm,name) VALUES(?,?,?)", uniq)
    except Exception as e:
        log(f"Katalog-Speichern {slug}: {e}"); return None
    return len(uniq)

def refresh_coverage_counts():
    """Besessen/bekannt je Plattform neu auszählen und ablegen. Läuft nach jedem
    Index-Lauf und nach jedem Katalog-Abruf — NICHT je Request (das skaliert nicht)."""
    cov = load_coverage()
    try:
        with closing(db_conn()) as c:
            known = dict(c.execute("SELECT slug, COUNT(*) FROM catalog GROUP BY slug"))
            owned = dict(c.execute(
                "SELECT c.slug, COUNT(*) FROM catalog c "
                "WHERE EXISTS(SELECT 1 FROM library l WHERE l.slug=c.slug AND l.norm=c.norm) "
                "GROUP BY c.slug"))
    except Exception as e:
        log(f"Abdeckung-Zählen: {e}"); return cov
    for slug, k in known.items():
        e = cov.setdefault(slug, {})
        e.update({"known": k, "owned": owned.get(slug, 0), "source": CATALOG_SOURCE,
                  "capped": k >= CATALOG_MAX, "counted": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        e.setdefault("snapshot", e["counted"])
    for slug in list(cov):
        if slug not in known: cov.pop(slug)      # Katalog weg -> keine Zahl behaupten
    save_coverage(cov)
    return cov

def coverage_overview():
    """Übersicht je Plattform. Plattformen ohne Momentaufnahme erscheinen MIT diesem Hinweis,
    statt als „0 %" — das wäre die falscheste aller Zahlen."""
    cov = load_coverage()
    with LIB_LOCK:
        have = {s: len(v) for s, v in LIB["per"].items()}
    out = []
    for _grp, items in PLATFORMS:
        for slug, name in items:
            e = cov.get(slug)
            row = {"slug": slug, "name": name, "files": have.get(slug, 0),
                   "catalog": bool(IGDB_PLAT.get(slug))}
            if e:
                row.update({"owned": e.get("owned", 0), "known": e.get("known", 0),
                            "pct": round(100.0 * e.get("owned", 0) / e["known"], 1) if e.get("known") else None,
                            "source": e.get("source", CATALOG_SOURCE), "snapshot": e.get("snapshot", ""),
                            "capped": bool(e.get("capped"))})
            else:
                row.update({"owned": None, "known": None, "pct": None, "snapshot": "", "source": ""})
            out.append(row)
    return out

def missing_titles(slug, offset=0, limit=100, q=""):
    """Fehlende Titel einer Plattform (Katalog minus Bibliothek), paginiert und filterbar."""
    sql = ("SELECT c.name FROM catalog c WHERE c.slug=? "
           "AND NOT EXISTS(SELECT 1 FROM library l WHERE l.slug=c.slug AND l.norm=c.norm)")
    args = [slug]
    if q:
        sql += " AND c.name LIKE ?"; args.append(f"%{q}%")
    cnt_sql = sql.replace("SELECT c.name", "SELECT COUNT(*)", 1)
    sql += " ORDER BY c.name LIMIT ? OFFSET ?"
    try:
        with closing(db_conn()) as c:
            total = c.execute(cnt_sql, args).fetchone()[0]
            names = [r[0] for r in c.execute(sql, args + [int(limit), int(offset)])]
    except Exception as e:
        log(f"Fehlende-Titel {slug}: {e}"); return {"total": 0, "titles": []}
    return {"total": total, "titles": names}


def owned_titles(slug, offset=0, limit=100, q=""):
    """Die VORHANDENEN Titel einer Plattform, paginiert und filterbar. (#293)

    Das Gegenstueck zu `missing_titles`. Die Abdeckungsseite konnte bisher nur
    beantworten, was FEHLT — vor dem Regal ist aber die haeufigere Frage, was man
    fuer eine Konsole HAT.

    Paginiert von Anfang an, nicht nachtraeglich: `c64` haelt hier fuenfstellige
    Titelzahlen, und eine vollstaendige Liste wuerde den Browser anhalten.

    Angezeigt wird `name` (der kuerzeste Dateiname des Titels); wo die Spalte noch
    leer ist — Datenbank von vor #293, Index seitdem nicht neu gebaut —, faellt es
    auf `norm` zurueck, damit die Liste nie leer aussieht.
    """
    sql = "SELECT COALESCE(NULLIF(l.name,''), l.norm) FROM library l WHERE l.slug=?"
    args = [slug]
    if q:
        sql += " AND (l.name LIKE ? OR l.norm LIKE ?)"
        args += [f"%{q}%", f"%{q.lower()}%"]
    cnt_sql = sql.replace("SELECT COALESCE(NULLIF(l.name,''), l.norm)", "SELECT COUNT(*)", 1)
    sql += " ORDER BY 1 LIMIT ? OFFSET ?"
    try:
        with closing(db_conn()) as c:
            total = c.execute(cnt_sql, args).fetchone()[0]
            names = [r[0] for r in c.execute(sql, args + [int(limit), int(offset)])]
    except Exception as e:
        log(f"Vorhandene-Titel {slug}: {e}"); return {"total": 0, "titles": []}
    return {"total": total, "titles": names}

# ---------- RetroAchievements (optional, rein schmückend) (#79) ----------
# Für eine Bibliothek voller Jahrzehnte alter Titel sagen Sternebewertungen wenig. Ein
# Achievement-Set sagt zweierlei zugleich: dass ein Titel lohnt und dass ihn noch jemand spielt.
#
# Das Schwierige ist die ZUORDNUNG, nicht das Abrufen. Deshalb wird je Konsole einmal die
# kuratierte Liste „Spiele mit Set" geholt und lokal abgelegt; zur Laufzeit ist die Zuordnung
# dann ein exakter Abgleich der normalisierten Titel gegen diese Liste — kein Fuzzy-Matching,
# denn eine falsche Zuordnung ist schlimmer als gar keine.
#
# Die Konsolen-IDs werden NICHT hartkodiert, sondern zur Laufzeit über die Systemliste von
# RetroAchievements aufgelöst. Eine geratene ID würde stillschweigend die falsche Konsole
# indizieren; ein nicht auflösbarer Name fällt dagegen als „keine Zuordnung" auf.
RA_BASE = "https://retroachievements.org/API"
RA_ALIASES = {
    "nes": ["nes/famicom", "nes", "famicom"],
    "snes": ["snes/super famicom", "snes", "super nintendo", "super famicom"],
    "n64": ["nintendo 64"], "gb": ["game boy"], "gbc": ["game boy color"],
    "gba": ["game boy advance"], "nds": ["nintendo ds"], "3ds": ["nintendo 3ds"],
    "ngc": ["gamecube", "nintendo gamecube"], "wii": ["wii"], "virtualboy": ["virtual boy"],
    "sms": ["master system"], "genesis": ["mega drive", "genesis", "mega drive/genesis", "sega genesis"],
    "segacd": ["sega cd", "mega cd"], "sega32x": ["32x", "sega 32x"],
    "gamegear": ["game gear"], "saturn": ["saturn", "sega saturn"], "dreamcast": ["dreamcast"],
    "psx": ["playstation"], "ps2": ["playstation 2"], "psp": ["playstation portable", "psp"],
    "turbografx16": ["pc engine", "turbografx-16", "pc engine/turbografx-16"],
    "neogeopocket": ["neo geo pocket"], "wonderswan": ["wonderswan"],
    "atari2600": ["atari 2600"], "atari7800": ["atari 7800"], "lynx": ["atari lynx"],
    "jaguar": ["atari jaguar"], "3do": ["3do interactive multiplayer", "3do"],
    "arcade": ["arcade"], "c64": ["commodore 64"], "amiga": ["amiga"], "dos": ["ms-dos", "dos"],
}
RA_LOCK = threading.Lock()
RA_PROGRESS_TTL = 900        # Nutzerfortschritt ändert sich oft, muss aber nicht live sein
_RA_PROGRESS = {}            # (user, ra_id) -> (ts, dict)

def _ra_name(s):
    return re.sub(r'[^a-z0-9]', '', str(s or "").lower())

def ra_key(): return cfg("ra_key")

def ra_get(endpoint, params, timeout=15):
    """RA-Aufruf. Gibt bei jedem Fehler None zurück — diese Funktion ist Dekoration,
    ihr Ausfall darf nirgends sichtbar werden."""
    key = ra_key()
    if not key: return None
    try:
        r = requests.get(f"{RA_BASE}/{endpoint}", params={**params, "y": key}, timeout=timeout)
        return r.json() if r.ok else None
    except Exception:
        return None

def ra_consoles():
    """Slug -> RA-Konsolen-ID, zur Laufzeit über die Systemliste aufgelöst."""
    data = ra_get("API_GetConsoleIDs.php", {"a": 1, "g": 1})
    if not isinstance(data, list): return {}
    by_name = {_ra_name(c.get("Name")): c.get("ID") for c in data if isinstance(c, dict)}
    out = {}
    for slug, names in RA_ALIASES.items():
        for cand in names:
            cid = by_name.get(_ra_name(cand))
            if cid: out[slug] = int(cid); break
    return out

def ra_fetch_console(slug, cid):
    """Alle Titel MIT Achievement-Set einer Konsole holen und lokal ablegen."""
    data = ra_get("API_GetGameList.php", {"i": cid, "f": 1}, timeout=40)
    if not isinstance(data, list) or not data: return None
    rows, seen = [], set()
    for g in data:
        if not isinstance(g, dict): continue
        title = g.get("Title") or ""
        n = norm(title)
        if not n or n in seen: continue
        seen.add(n)
        rows.append((slug, n, int(g.get("ID") or 0), title,
                     int(g.get("NumAchievements") or 0), int(g.get("Points") or 0)))
    if not rows: return None
    try:
        with DB_LOCK, closing(db_conn()) as c, c:
            c.execute("DELETE FROM ra_games WHERE slug=?", (slug,))
            c.executemany("INSERT INTO ra_games(slug,norm,ra_id,title,achievements,points) "
                          "VALUES(?,?,?,?,?,?)", rows)
    except Exception as e:
        log(f"RA-Speichern {slug}: {e}"); return None
    return len(rows)

def ra_lookup(title, slug=""):
    """Titel -> Achievement-Set. Exakter Abgleich des normalisierten Titels; ohne Plattform
    wird plattformübergreifend gesucht und nur ein EINDEUTIGER Treffer akzeptiert."""
    n = norm(title)
    if not n: return None
    try:
        with closing(db_conn()) as c:
            if slug:
                rows = list(c.execute("SELECT slug,ra_id,title,achievements,points FROM ra_games "
                                      "WHERE slug=? AND norm=? LIMIT 2", (slug, n)))
            else:
                rows = list(c.execute("SELECT slug,ra_id,title,achievements,points FROM ra_games "
                                      "WHERE norm=? LIMIT 2", (n,)))
    except Exception:
        return None
    if len(rows) != 1: return None      # mehrdeutig -> lieber nichts zeigen
    s, rid, t, ach, pts = rows[0]
    return {"id": rid, "title": t, "platform": s, "achievements": ach, "points": pts,
            "url": f"https://retroachievements.org/game/{rid}"}

def ra_user_progress(ra_user, ra_id):
    """Fortschritt eines Nutzers für ein Set. Gecacht — muss nicht live sein."""
    if not (ra_user and ra_id): return None
    k = (ra_user, ra_id)
    hit = _RA_PROGRESS.get(k)
    if hit and time.time() - hit[0] < RA_PROGRESS_TTL: return hit[1]
    d = ra_get("API_GetGameInfoAndUserProgress.php", {"u": ra_user, "g": ra_id})
    out = None
    if isinstance(d, dict):
        out = {"earned": int(d.get("NumAwardedToUser") or 0),
               "earned_hardcore": int(d.get("NumAwardedToUserHardcore") or 0),
               "total": int(d.get("NumAchievements") or d.get("achievements_published") or 0),
               "completion": d.get("UserCompletion") or ""}
    _RA_PROGRESS[k] = (time.time(), out)
    return out

def ra_has_set(title, slug=""):
    return ra_lookup(title, slug) is not None

def in_library(title, slug):
    n = norm(title)
    if not n: return False
    with LIB_LOCK:
        if slug and slug in LIB["per"]:
            return n in LIB["per"][slug]
        return n in LIB["all"]      # Plattform unbekannt -> global prüfen (konservativ)

# Wohin eine Datei geht, deren Plattform sich nicht bestimmen laesst. Der PUNKT ist die
# ganze Mechanik: `build_index` ueberspringt Ordner, die damit beginnen (#321). Ein
# Ablageort, der keine Plattform vortaeuscht, braucht deshalb keine neue Sonderregel.
# A leading dot is the whole mechanism: build_index skips such folders, so a holding area
# needs no special case to stay out of the platform list.
UNSORTIERT = ".unsortiert"


def resolve_slug(slug):
    """Auf einen existierenden Ordner abbilden, sonst unveraendert lassen.

    UNBEKANNT BLEIBT LEER (#367). Frueher stand hier `"Mixed"` — und weil dieser Wert
    weiterlief bis `os.makedirs(ROMS/<slug>)`, ERZEUGTE Romseerr daraus eine Plattform:
    erst den Ordner, dann den Eintrag im Index, dann das System in der Ansicht. Ein Titel
    ohne erkennbare Plattform war damit nicht etwa unbeschriftet, sondern mit einer
    Plattform beschriftet, die es nicht gibt.

    Unknown stays empty: the old "Mixed" sentinel flowed into os.makedirs and thereby
    created the very platform it was standing in for.
    """
    if not slug: return ""
    with LIB_LOCK:
        if slug in LIB["slugs"]: return slug
    return slug   # neuer Plattform-Ordner ist ok

# ---------- IGDB (optional, best effort): Cover, Beschreibung, Beliebt ----------
IGDB = {"token": "", "exp": 0, "cache": {}}
def igdb_token():
    if not (cfg("igdb_id") and cfg("igdb_secret")): return ""
    if time.time() > IGDB["exp"]:
        r = requests.post("https://id.twitch.tv/oauth2/token", params={
            "client_id": cfg("igdb_id"), "client_secret": cfg("igdb_secret"),
            "grant_type": "client_credentials"}, timeout=8)
        j = r.json(); IGDB["token"] = j["access_token"]; IGDB["exp"] = time.time()+j.get("expires_in",3600)-60
    return IGDB["token"]

def igdb_query(endpoint, body):
    tok = igdb_token()
    if not tok: return []
    try:
        h = {"Client-ID": cfg("igdb_id"), "Authorization": f"Bearer {tok}"}
        return requests.post(f"https://api.igdb.com/v4/{endpoint}", headers=h, data=body, timeout=8).json()
    except Exception:
        return []

def igdb_game(title):
    key = norm(title)
    if key in IGDB["cache"]: return IGDB["cache"][key]
    d = igdb_query("games", f'search "{title[:60]}"; fields name,cover.image_id,summary; limit 1;')
    g = d[0] if d else {}
    IGDB["cache"][key] = g
    return g

def _igdb_escape(s):
    """Anführungszeichen/Backslashes für die Apicalypse-Query entschärfen."""
    return str(s).replace("\\", "").replace('"', "").replace("\n", " ")[:60]

def igdb_multisearch(titles, limit=5):
    """Mehrere Titel in EINEM Rutsch suchen (IGDB-`multiquery`, max. 10 Abfragen je Request).

    Nötig für den Wunschlisten-Import: 200 Einzelabfragen wären bei IGDBs 4 Req/s
    quälend langsam, als multiquery sind es 20 Requests. Rückgabe: {Eingabetitel:
    [Kandidatenname, …]}. Fehler und fehlende Zugangsdaten ergeben ein leeres Dict —
    der Aufrufer behandelt das als „nicht geprüft", nicht als „nicht gefunden"."""
    out = {}
    if not (titles and igdb_token()): return out
    uniq = list(dict.fromkeys(t for t in titles if t))
    for i in range(0, len(uniq), 10):
        chunk = uniq[i:i+10]
        body = "".join(f'query games "q{n}" {{ search "{_igdb_escape(t)}"; fields name; limit {limit}; }};'
                       for n, t in enumerate(chunk))
        try:
            tok = igdb_token()
            h = {"Client-ID": cfg("igdb_id"), "Authorization": f"Bearer {tok}"}
            r = requests.post("https://api.igdb.com/v4/multiquery", headers=h, data=body, timeout=15)
            for part in (r.json() if r.ok else []):
                n = int(str(part.get("name", "q0"))[1:] or 0)
                if 0 <= n < len(chunk):
                    out[chunk[n]] = [g.get("name", "") for g in (part.get("result") or []) if g.get("name")]
        except Exception as e:
            log(f"IGDB-multiquery-Fehler: {e}")
    return out

def _cover_url(g):
    return f"https://images.igdb.com/igdb/image/upload/t_cover_big/{g['cover']['image_id']}.jpg" if g.get("cover") else ""

_SGDB_CACHE = {}
def sgdb_cover(title):
    """Cover über SteamGridDB (Scraper-Fallback), wenn ein Key hinterlegt ist. 1h/prozessweit gecacht."""
    key = cfg("sgdb_key")
    if not key or not title: return ""
    if title in _SGDB_CACHE: return _SGDB_CACHE[title]
    url = ""
    try:
        h = {"Authorization": "Bearer " + key}
        r = requests.get("https://www.steamgriddb.com/api/v2/search/autocomplete/" +
                         urllib.parse.quote(title[:80]), headers=h, timeout=8).json()
        data = r.get("data") or []
        if data:
            gid = data[0].get("id")
            g = requests.get(f"https://www.steamgriddb.com/api/v2/grids/game/{gid}?dimensions=600x900&limit=1",
                             headers=h, timeout=8).json()
            gd = g.get("data") or []
            if gd: url = gd[0].get("url", "")
    except Exception as e:
        log(f"SteamGridDB-Fehler: {e}")
    _SGDB_CACHE[title] = url
    return url

def igdb_cover(title):
    """Cover-URL: zuerst IGDB, sonst SteamGridDB als Fallback (falls Scraper-Key gesetzt)."""
    return _cover_url(igdb_game(title)) or sgdb_cover(title)
def igdb_desc(title):  return (igdb_game(title) or {}).get("summary", "")

def igdb_rich(title):
    key = "rich:" + norm(title)
    if key in IGDB["cache"]: return IGDB["cache"][key]
    d = igdb_query("games", f'search "{title[:60]}"; fields name,summary,rating,aggregated_rating,'
        f'genres.name,first_release_date,involved_companies.company.name,involved_companies.developer,'
        f'screenshots.image_id,similar_games.name,collection.name,collection.games.name; limit 1;')
    g = d[0] if isinstance(d, list) and d else {}
    rating = g.get("aggregated_rating") or g.get("rating")
    year = ""
    if g.get("first_release_date"):
        # ZEITZONENBEWUSST, nicht `utcfromtimestamp` (#588): Das Abbild faehrt
        # `python:3.14-slim`, dort ist der alte Aufruf abgekuendigt. Faellt er weg,
        # schlaegt das hier NICHT durch — der `except` darunter faengt den AttributeError,
        # und dann fehlt in jeder Detailansicht stillschweigend das Erscheinungsjahr.
        # Ein Absturz waere leichter zu finden gewesen.
        try: year = datetime.fromtimestamp(g["first_release_date"], tz=timezone.utc).year
        except Exception: pass
    dev = ""
    for ic in g.get("involved_companies", []) or []:
        if ic.get("developer") and ic.get("company"): dev = ic["company"].get("name",""); break
    out = {"name": g.get("name",""),
           "summary": g.get("summary",""), "rating": round(rating) if rating else None, "year": year,
           "developer": dev, "genres": [x.get("name") for x in g.get("genres",[]) or [] if x.get("name")],
           "screenshots": [f"https://images.igdb.com/igdb/image/upload/t_screenshot_med/{s['image_id']}.jpg"
                           for s in (g.get("screenshots",[]) or [])[:6] if s.get("image_id")],
           "similar": [x.get("name") for x in (g.get("similar_games",[]) or [])[:8] if x.get("name")]}
    col = g.get("collection") or {}
    if col.get("name") and col.get("games"):
        me = norm(g.get("name",""))
        series = [x.get("name") for x in (col.get("games") or []) if x.get("name") and norm(x["name"]) != me]
        if series:
            out["series"] = col["name"]
            out["series_games"] = series[:12]
    IGDB["cache"][key] = out
    return out

# Die IGDB-Plattform-IDs, die Romseerr ueberhaupt bedienen kann. Aus IGDB_PLAT
# abgeleitet, damit die beiden nicht auseinanderlaufen: Wer dort eine Plattform
# ergaenzt, erweitert damit automatisch auch die Empfehlungen.
IGDB_PLAT_IDS = set(IGDB_PLAT.values())

def igdb_similar_games(title, limit=20):
    """Ähnliche Spiele (mit Cover) zu einem Titel – Grundlage für „Weil du … angefragt hast".

    GEFILTERT AUF UNSERE PLATTFORMEN (#324): IGDB liefert zu einem Xbox-Titel wie Fable
    bereitwillig Borderlands 3, GreedFall und The Elder Scrolls VI. Nichts davon gibt es
    fuer eine Plattform, die diese Instanz bedient — die oberste Zeile der Startseite
    zeigte damit ausschliesslich Titel, die niemand anfragen kann. Ein Vorschlag, der nie
    einloesbar ist, kostet mehr Vertrauen als eine kuerzere Zeile.

    `The Elder Scrolls VI` war dabei besonders sprechend: unveroeffentlicht, ohne Cover,
    ohne Bewertung — eine schwarze Kachel an der prominentesten Stelle der Anwendung.

    Filtered to the platforms this instance can actually serve: IGDB happily returns
    modern PC titles for a retro seed, and a suggestion that can never be fulfilled costs
    more trust than a shorter row.
    """
    key = "simg:" + norm(title)
    if key in IGDB["cache"]: return IGDB["cache"][key]
    d = igdb_query("games", f'search "{title[:60]}"; '
        f'fields name,similar_games.name,similar_games.cover.image_id,'
        f'similar_games.total_rating,similar_games.platforms; limit 1;')
    g = d[0] if isinstance(d, list) and d else {}
    out = []
    for s in (g.get("similar_games", []) or []):
        if not (s.get("name") and s.get("cover")):
            continue
        # `platforms` fehlt bei unvollstaendigen IGDB-Eintraegen. Solche Titel fliegen
        # RAUS statt durchzurutschen: Ohne Plattformangabe ist unbekannt, ob es sie
        # ueberhaupt fuer eine unserer Konsolen gibt — und im gemessenen Fall waren es
        # genau die unveroeffentlichten.
        plats = s.get("platforms") or []
        ids = {p.get("id") if isinstance(p, dict) else p for p in plats}
        if not (ids & IGDB_PLAT_IDS):
            continue
        out.append({"title": s.get("name",""), "cover": _cover_url(s),
                    "ext_rating": round(s["total_rating"]) if s.get("total_rating") else None})
        if len(out) >= limit:
            break
    IGDB["cache"][key] = out
    return out

def recommend_for_user(user, limit=20):
    """Personalisierte Empfehlung: nimmt die zuletzt vom Nutzer angefragten Titel als
    Saat und liefert dazu ähnliche Spiele, die noch nicht in der Bibliothek sind.
    Gibt {seed, games} oder None zurück (None = keine Anfragen / keine Treffer)."""
    if not user: return None
    with JOBS_LOCK:
        titles = [j.get("title","") for j in reversed(JOBS)
                  if j.get("user") == user and j.get("state") != "denied"]
    seeds = []
    for tq in titles:
        q = clean_query(tq)
        if q and q.lower() not in [s.lower() for s in seeds]:
            seeds.append(q)
        if len(seeds) >= 4: break
    for seed in seeds:
        sims = [s for s in igdb_similar_games(seed, limit) if not in_library(s["title"], None)]
        if sims:
            return {"seed": seed, "games": sims}
    return None

def clean_query(t):
    # Verrauschte Release-/Usenet-Titel auf den Spielnamen kürzen (für IGDB-Cover-Suche)
    t = re.sub(r'[\._]+', ' ', (t or "")[:MAX_NAME])          # gedeckelt: siehe _tags
    # `maxsplit=` BENANNT (#588): positional ist auf Python 3.14 abgekuendigt, und das
    # Abbild faehrt genau das. Anders als beim Jahr in `igdb_rich` steht hier kein
    # `except` darum — faellt die Form weg, ist es ein TypeError mitten in der
    # Cover-Suche.
    t = re.split(r'\b(update|dlc|proper|repack|multi\d*|nsw|xci|nsp|wbfs|rvz|ps[1-5]|psp|psvita|'
                 r'wiiu?|xbox\w*|switch|eur|usa|jpn|europe|japan|v\d+(\.\d+)*)\b',
                 t, maxsplit=1, flags=re.I)[0]
    t = re.sub(r'\([^)]*\)|\[[^\]]*\]', ' ', t)
    t = re.sub(r'-\s*\w+$', '', t)          # -GROUP am Ende
    return re.sub(r'\s+', ' ', t).strip()

def igdb_popular(limit=40):
    # `total_rating` kostet nichts extra — es kommt aus derselben Abfrage und macht aus
    # einer Wand von Covern eine, die sich auf einen Blick ordnen lässt. (#210)
    d = igdb_query("games", f'fields name,cover.image_id,total_rating; '
        f'where cover != null & total_rating_count > 80; '
        f'sort total_rating_count desc; limit {limit};')
    if not isinstance(d, list): return []
    return [{"title": g.get("name",""), "cover": _cover_url(g),
             "ext_rating": round(g["total_rating"]) if g.get("total_rating") else None}
            for g in d if isinstance(g, dict) and g.get("cover")]

def igdb_popular_platform(pid, limit=20):
    d = igdb_query("games", f'fields name,cover.image_id,total_rating; '
        f'where platforms=({pid}) & cover != null & total_rating_count > 12; '
        f'sort total_rating_count desc; limit {limit};')
    if not isinstance(d, list): return []
    return [{"title": g.get("name",""), "cover": _cover_url(g),
             "ext_rating": round(g["total_rating"]) if g.get("total_rating") else None}
            for g in d if isinstance(g, dict) and g.get("cover")]

# IGDB-Genre-ID -> Anzeigename (für Genre-Reihen im Discover)
IGDB_GENRES = [("rpg",12,"Rollenspiele / RPG"), ("platform",8,"Jump 'n' Run"),
               ("shooter",5,"Shooter"), ("fighting",4,"Beat 'em up"),
               ("racing",10,"Rennspiele / Racing"), ("adventure",31,"Adventure"),
               ("puzzle",9,"Puzzle"), ("sport",14,"Sport"), ("strategy",15,"Strategie / Strategy")]
def igdb_popular_genre(gid, limit=20):
    d = igdb_query("games", f'fields name,cover.image_id,total_rating; '
        f'where genres=({gid}) & cover != null & total_rating_count > 30; '
        f'sort total_rating_count desc; limit {limit};')
    if not isinstance(d, list): return []
    return [{"title": g.get("name",""), "cover": _cover_url(g),
             "ext_rating": round(g["total_rating"]) if g.get("total_rating") else None}
            for g in d if isinstance(g, dict) and g.get("cover")]

DISCOVER_CACHE = {"ts": 0, "rows": []}
def discover_rows():
    """Startseiten-Reihen: „beliebt je Konsole" (DISCOVER_ORDER) + „beliebt je Genre"
    (IGDB_GENRES), 1 h gecacht. Die `in_library`-Markierung und der Sperrlisten-Filter
    werden bei jedem Aufruf frisch angewandt (nicht gecacht)."""
    if time.time()-DISCOVER_CACHE["ts"] < 3600 and DISCOVER_CACHE["rows"]:
        rows = DISCOVER_CACHE["rows"]
    else:
        rows = []
        for slug in DISCOVER_ORDER:
            pid = IGDB_PLAT.get(slug)
            games = igdb_popular_platform(pid, 20) if pid else []
            if games:
                rows.append({"slug": slug, "key": "c:"+slug, "console": SLUG_NAME.get(slug, slug), "games": games})
        for key, gid, name in IGDB_GENRES:
            games = igdb_popular_genre(gid, 20)
            if games:
                rows.append({"slug": "", "key": "genre:"+key, "console": name, "games": games})
        DISCOVER_CACHE["rows"], DISCOVER_CACHE["ts"] = rows, time.time()
    # Bibliotheks-Markierung je Spiel frisch (nicht cachen)
    bl = [str(p).strip().lower() for p in load_settings().get("blocklist", []) if str(p).strip()]
    offen = angefragte_titel()
    def markiere(g, slug):
        da = in_library(g["title"], slug or None)
        return {**g, "in_library": da, "requested": (not da) and norm(g["title"]) in offen}
    return [{"slug": r["slug"], "key": r.get("key", r["console"]), "console": r["console"],
             "games": [markiere(g, r["slug"]) for g in r["games"] if not is_blocked(g["title"], bl)]}
            for r in rows]

# ---------- Ausgehende Anfragen an selbst gesetzte URLs (#89) ----------
# Webhook-URLs kommen vom Nutzer. Ohne Pruefung wird der Server damit zum HTTP-Client
# fuer beliebige Ziele — auch solche, die NUR er erreicht (andere Container, Router- und
# Firewall-Oberflaechen, Metadaten-Endpunkte). Das kann JEDER angemeldete Nutzer ausloesen,
# nicht nur ein Admin: es genuegt, das eigene Webhook-Feld zu setzen und "Test" zu druecken.
#
# Bewusst KEIN pauschales Verbot privater Ziele: viele betreiben ihr Benachrichtigungsziel
# im selben Netz. Deshalb eine ausdrueckliche Admin-Einstellung, standardmaessig AUS.
_PRIVATE_OK_KEY = "allow_private_webhooks"

def allow_private_targets():
    return bool(load_settings().get(_PRIVATE_OK_KEY))

def url_allowed(url):
    """(ok, grund). Prueft Schema und die AUFGELOESTE Adresse — ein Hostname sagt nichts,
    `interner-dienst.example.com` kann auf 127.0.0.1 zeigen."""
    import ipaddress, socket
    try:
        u = urllib.parse.urlsplit(str(url or ""))
    except Exception:
        return False, "invalid"
    if u.scheme not in ("http", "https"): return False, "scheme"
    if not u.hostname: return False, "invalid"
    if allow_private_targets(): return True, ""
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except Exception:
        return False, "dns"
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False, "dns"
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
                or ip.is_reserved or ip.is_unspecified):
            return False, "private"
    return True, ""

def err_kind(e):
    """Fehlerart statt Ausnahmetext. Der Volltext gehoert ins Log, nicht in eine Antwort —
    er verraet interne Pfade, Hostnamen und Bibliotheksdetails."""
    import socket as _s
    if isinstance(e, requests.Timeout): return "timeout"
    if isinstance(e, requests.ConnectionError): return "nicht erreichbar / unreachable"
    if isinstance(e, requests.HTTPError) and e.response is not None:
        return f"HTTP {e.response.status_code}"
    if isinstance(e, (_s.gaierror,)): return "DNS"
    if isinstance(e, ValueError): return "ungueltige Antwort / invalid response"
    return "Fehler / error"

URL_REFUSED = {"scheme": "nur http(s) erlaubt / http(s) only",
               "private": "Ziel im privaten Netz — in den Einstellungen ausdruecklich erlauben / "
                          "private target, enable it explicitly in settings",
               "dns": "Name nicht aufloesbar / cannot resolve",
               "invalid": "keine gueltige URL / not a valid URL"}

def safe_request(method, url, _redirects=2, **kw):
    """Wie requests.request, aber nur an erlaubte Ziele — und Weiterleitungen werden
    einzeln neu geprueft. Ohne das genuegt eine Umleitung auf 127.0.0.1, um die
    Pruefung der Ausgangs-URL zu umgehen."""
    ok, why = url_allowed(url)
    if not ok:
        raise PermissionError(URL_REFUSED.get(why, why))
    kw.setdefault("timeout", 8)
    kw["allow_redirects"] = False
    r = requests.request(method, url, **kw)
    if r.is_redirect and _redirects > 0 and r.headers.get("Location"):
        nxt = urllib.parse.urljoin(url, r.headers["Location"])
        return safe_request(method, nxt, _redirects - 1, **kw)
    return r

def safe_post(url, **kw): return safe_request("POST", url, **kw)
def safe_get(url, **kw):  return safe_request("GET", url, **kw)

def notify_send(text):
    """Meldung an ALLE aktiven globalen Kanäle senden: Discord-Webhook (Einstellungen oder
    Env-Fallback), Telegram, generischer Webhook. Gibt True zurück, wenn mind. einer sendete."""
    s = load_settings(); sent = False
    dc = s.get("discord", {})
    wh = dc.get("url") if dc.get("enabled") else os.environ.get("DISCORD_WEBHOOK", "")
    if wh:
        try: safe_post(wh, json={"content": text}); sent = True
        except Exception as e: log(f"Discord-Fehler: {e}")
    ag = s.get("agents", {})
    tg = ag.get("telegram", {})
    if tg.get("enabled") and tg.get("token") and tg.get("chat"):
        try: requests.post(f"https://api.telegram.org/bot{tg['token']}/sendMessage",
                           json={"chat_id": tg["chat"], "text": text}, timeout=8); sent = True
        except Exception as e: log(f"Telegram-Fehler: {e}")
    gw = ag.get("webhook", {})
    if gw.get("enabled") and gw.get("url"):
        try: safe_post(gw["url"], json={"content": text, "text": text}); sent = True
        except Exception as e: log(f"Webhook-Fehler: {e}")
    gt = ag.get("gotify", {})
    if gt.get("enabled") and gt.get("url") and gt.get("token"):
        try: safe_post(f"{gt['url'].rstrip('/')}/message", params={"token": gt["token"]},
                       json={"title": "Romseerr", "message": text}); sent = True
        except Exception as e: log(f"Gotify-Fehler: {e}")
    nt = ag.get("ntfy", {})
    if nt.get("enabled") and nt.get("topic"):
        base = (nt.get("url") or "https://ntfy.sh").rstrip("/")
        hdr = {"Authorization": "Bearer " + nt["token"]} if nt.get("token") else {}
        try: safe_post(f"{base}/{nt['topic']}", data=text.encode("utf-8"), headers=hdr); sent = True
        except Exception as e: log(f"ntfy-Fehler: {e}")
    po = ag.get("pushover", {})
    if po.get("enabled") and po.get("token") and po.get("user"):
        try: requests.post("https://api.pushover.net/1/messages.json",
                           data={"token": po["token"], "user": po["user"], "message": text}, timeout=8); sent = True
        except Exception as e: log(f"Pushover-Fehler: {e}")
    return sent

def notify_available(title, platform):
    notify_send(f"🎮 **{title}** ist jetzt verfügbar / now available ({platform})")

# ---------- Suche ----------
def search_archive(q, limit=30):
    out = []
    try:
        params = {"q": f'title:({q}) AND mediatype:software', "rows": limit, "output": "json",
                  "sort[]": "downloads desc"}
        # `collection` MITHOLEN (#382): Archive.org kennzeichnet zugangsbeschraenkte
        # Eintraege ueber die Sammlung `loggedin`. Ohne dieses Feld sieht ein solcher
        # Treffer aus wie jeder andere — bis der Download nach dem Klick mit HTTP 401
        # abbricht. Bei „Mario Kart 8 (Europe)" waren das 5,5 GB, die nie kommen konnten.
        params_list = [("fl[]","identifier"),("fl[]","title"),("fl[]","item_size"),
                       ("fl[]","downloads"),("fl[]","subject"),("fl[]","collection")]
        url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(params) + "&" + urllib.parse.urlencode(params_list)
        r = requests.get(url, timeout=15); d = r.json()
        for doc in d.get("response",{}).get("docs",[]):
            ident = doc.get("identifier"); title = doc.get("title") or ident
            if not ident: continue
            if NOISE_RE.search(str(title)): continue
            subj = doc.get("subject"); subj = " ".join(subj) if isinstance(subj,list) else (subj or "")
            slug = guess_platform(f"{title} {subj} {ident}")
            coll = doc.get("collection")
            coll = coll if isinstance(coll, list) else ([coll] if coll else [])
            out.append({"source":"archive","ref":ident,"title":str(title)[:140],
                        "platform":slug, "size":int(doc.get("item_size") or 0),
                        "cover":f"https://archive.org/services/img/{ident}",
                        # Zugangsbeschraenkt: der Download braucht ein Konto, das Romseerr
                        # nicht hat. Der Treffer bleibt sichtbar — es gibt ihn ja —, traegt
                        # die Einschraenkung aber mit. (#382)
                        # Mit hinterlegten Schluesseln ist der Titel ladbar — dann ist
                        # das Schloss falsch. Die Sperre haengt am KONTO, nicht am Titel.
                        "restricted": ("loggedin" in coll) and not ia_bereit(),
                        "extra":str(doc.get("downloads") or 0)})
    except Exception as e:
        log(f"Archive-Suche-Fehler: {e}")
    return out

# ---------- Filehoster: generischer Katalog-JSON-Indexer (#63) ----------
# Der Filehoster-Zweig (write_crawljob -> JDownloader) existierte, aber KEINE Quelle lieferte
# je `source=filehoster` — er war damit unerreichbar. Statt einen einzelnen Anbieter fest
# einzubauen, liest Romseerr das verbreitete Katalog-JSON-Format:
#
#   {"name": "...", "downloads": [{"title","uris":[...],"uploadDate","fileSize"}, ...]}
#
# Belegt am Original-Validator des Hydra-Launchers (v2.1.0,
# src/main/events/helpers/validators.ts) — nicht aus Sekundärquellen abgeschrieben.
#
# **Die Quell-URLs gehören in die Einstellungen, NIE in dieses Repo.** Wir liefern den
# Parser, der Betreiber die Quellen. `uploadDate`/`fileSize` sind dort Strings, keine Zahlen.
CATALOG_TTL = int(os.environ.get("ROMSEERR_CATALOG_TTL", "21600"))   # 6 h
CATALOG_LOCK = threading.Lock()

def catalog_urls():
    """Quell-URLs aus den Einstellungen (eine je Zeile oder komma-getrennt)."""
    raw = cfg("catalog_urls") or ""
    return [u.strip() for u in re.split(r"[\s,]+", raw) if u.strip().startswith(("http://", "https://"))]

def fetch_catalog_source(url):
    """Eine Katalogquelle holen, prüfen und ihre Einträge ablegen. Rückgabe (name, anzahl)
    oder eine Ausnahme mit lesbarem Grund — eine unbrauchbare Quelle soll auffallen."""
    r = safe_get(url, timeout=30, headers={"Accept": "application/json"})
    if not r.ok: raise RuntimeError(f"HTTP {r.status_code}")
    data = r.json()
    if not isinstance(data, dict) or not isinstance(data.get("downloads"), list):
        raise RuntimeError("kein Katalog-JSON (erwartet {name, downloads[]}) / not a catalogue JSON")
    name = str(data.get("name") or url)[:255]
    rows, seen = [], set()
    for it in data["downloads"]:
        if not isinstance(it, dict): continue
        title = str(it.get("title") or "")[:255]
        uris = [str(u) for u in (it.get("uris") or []) if isinstance(u, str)]
        n = norm(title)
        if not (n and uris) or n in seen: continue
        seen.add(n)
        rows.append((n, title, json.dumps(uris), str(it.get("fileSize") or "")[:64],
                     str(it.get("uploadDate") or "")[:64], name, url))
    with DB_LOCK, closing(db_conn()) as c, c:
        c.execute("DELETE FROM fh_items WHERE url=?", (url,))
        c.executemany("INSERT INTO fh_items(norm,title,uris,size,uploaded,src,url) "
                      "VALUES(?,?,?,?,?,?,?)", rows)
    return name, len(rows)

def refresh_catalogs(force=False):
    """Alle hinterlegten Quellen auffrischen. Linkfäule ist hier die Regel, deshalb TTL
    und ein sichtbarer Stand je Quelle statt stiller Ewigkeit."""
    meta = kv_get("catalog_meta", {})
    now = time.time()
    for url in catalog_urls():
        m = meta.get(url) or {}
        if not force and now - float(m.get("ts") or 0) < CATALOG_TTL: continue
        try:
            name, n = fetch_catalog_source(url)
            meta[url] = {"name": name, "count": n, "ts": now, "error": "",
                         "fetched": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))}
            log(f"Katalogquelle '{name}': {n} Einträge")
        except Exception as e:
            # Auch hier nur die Fehlerart: der Katalogstatus ist fuer Admins sichtbar,
            # der Ausnahmetext koennte interne Pfade tragen. (#89)
            meta[url] = {**m, "ts": now, "error": err_kind(e) if isinstance(e, Exception) else "Fehler",
                         "fetched": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))}
            log(f"Katalogquelle {url}: {e}")
    for url in list(meta):
        if url not in catalog_urls():
            meta.pop(url)
            try:
                with DB_LOCK, closing(db_conn()) as c, c:
                    c.execute("DELETE FROM fh_items WHERE url=?", (url,))
            except Exception as e:
                # NICHT STILL (#589): Der Eintrag ist oben schon aus `meta` gefallen, die
                # Quelle also aus der Verwaltung verschwunden. Bleiben ihre Zeilen in
                # `fh_items` liegen, tauchen sie weiter in Suchergebnissen auf — ohne
                # dass es noch eine Quelle gaebe, der man das ansehen koennte.
                log(f"Katalogquelle {url} entfernt, aber ihre Eintraege blieben stehen: "
                    f"{err_kind(e)} — sie erscheinen weiter in der Suche.")
    kv_put("catalog_meta", meta)
    return meta

def split_uris(uris):
    """URIs sind gemischt und brauchen verschiedene Wege: `magnet:` ist ein Torrent
    (hier ausdrücklich NICHT zuständig), direktes HTTP laden wir selbst, alles andere
    ist ein Filehoster und geht an JDownloader."""
    direct, hoster, magnet = [], [], []
    for u in uris:
        low = str(u).lower()
        if low.startswith("magnet:"): magnet.append(u)
        elif re.search(r"\.(zip|rar|7z|iso|bin|chd|nsp|xci|gz|tar|[a-z0-9]{2,4})(\?|$)", low) \
             and low.startswith(("http://", "https://")) and not re.search(
                 r"(mega\.nz|mediafire|1fichier|pixeldrain|gofile|rapidgator|turbobit|katfile|"
                 r"drive\.google|dropbox|buzzheavier|datanodes|qiwi|fuckingfast)", low):
            direct.append(u)
        elif low.startswith(("http://", "https://")): hoster.append(u)
    return direct, hoster, magnet

def search_filehoster(q, limit=30):
    """Katalogtreffer als normale Suchergebnisse mit `source="filehoster"`."""
    toks = [t for t in norm(q).split() if t]
    if not toks: return []
    # Bewusst EIN literaler SQL-String: das erste Token grenzt in der DB ein, die
    # restlichen Token werden in Python geprüft. Eine dynamisch zusammengesetzte
    # WHERE-Kette wäre zwar ebenso parametrisiert, aber Bandit meldet sie als B608 —
    # und literales SQL ist hier ohnehin die einfachere Lösung.
    try:
        with closing(db_conn()) as c:
            rows = list(c.execute(
                "SELECT title, uris, size, uploaded, src, norm FROM fh_items "
                "WHERE norm LIKE ? ORDER BY LENGTH(title) LIMIT ?",
                (f"%{toks[0]}%", int(limit) * 8)))
    except Exception as e:
        log(f"Filehoster-Suche-Fehler: {e}"); return []
    out = []
    for title, uris_json, size, uploaded, src, n in rows:
        if len(out) >= limit: break
        if not all(t in n for t in toks[1:]): continue
        try: uris = json.loads(uris_json)
        except Exception: continue
        direct, hoster, _magnet = split_uris(uris)
        if not (direct or hoster): continue       # nur Magnet -> hier nicht zuständig
        if NOISE_RE.search(title): continue
        out.append({"source": "filehoster", "ref": "\n".join(direct + hoster),
                    "title": title[:140], "platform": guess_platform(title),
                    "size": 0, "cover": "", "extra": f"{src} · {size} · {uploaded}".strip(" ·")})
    return out

def worker_catalog():
    """Katalogquellen im Hintergrund frisch halten (Linkfäule!)."""
    time.sleep(45)
    while True:
        beat("catalog")
        try:
            if catalog_urls(): refresh_catalogs()
        except Exception as e:
            log(f"Katalog-Worker: {e}")
        time.sleep(max(600, CATALOG_TTL // 4))

def plattform_aus_kategorie_und_titel(aus_kategorie, titel):
    """Plattform eines Usenet-Treffers. Die Kategorie des Indexers zaehlt — ausser der Titel
    nennt eine Plattform, die genau in DIESER Kategorie mitfaehrt (`KAT_LEIHE`, #452).

    Bewusst eng: Ein Titel, der irgendeine fremde Plattform erwaehnt, darf die Kategorie
    NICHT umwerfen. Nur der eingetragene Mieter darf seine eigene Kategorie zurueckerobern,
    denn nur dort ist die Kategorie nachweislich zu grob.

    Platform of a usenet hit. The indexer category wins, unless the title names a platform
    that is a documented tenant of exactly that category."""
    aus_titel = guess_platform(titel or "")
    if not aus_kategorie:
        return aus_titel
    if aus_titel and KAT_LEIHE.get(aus_titel) == aus_kategorie:
        return aus_titel
    return aus_kategorie


def search_usenet(q, cats, limit=30):
    out = []
    verworfen = 0
    if not (cfg("prow_url") and cfg("prow_apikey") and cats): return out
    try:
        u = f"{cfg("prow_url")}/api/v1/search"
        r = requests.get(u, params={"query":q,"categories":cats,"type":"search","limit":limit},
                         headers={"X-Api-Key":cfg("prow_apikey")}, timeout=25)
        for it in r.json():
            if it.get("protocol") != "usenet": continue
            cats = [c.get("id") for c in it.get("categories",[]) if c.get("id")]
            slug = None
            for c in cats:
                if c in USENET_CAT: slug = USENET_CAT[c]; break
            # ZUERST das Unbrauchbare aussortieren (#607) — bevor irgendeine Kategorie
            # ihm eine Plattform gibt. Ein PS5-Release ist hier auch dann falsch, wenn der
            # Indexer es unter Switch fuehrt; frueher kam es damit als Switch-Treffer an.
            if guess_platform(it.get("title", "")) in NICHT_BEDIENT:
                verworfen += 1
                continue
            slug = plattform_aus_kategorie_und_titel(slug, it.get("title",""))
            out.append({"source":"usenet","ref":it.get("downloadUrl"),"title":it.get("title","")[:140],
                        "platform":slug,"size":int(it.get("size") or 0),
                        "cover":"", "extra":it.get("indexer","")})
    except Exception as e:
        log(f"Usenet-Suche-Fehler: {e}")
    if verworfen:
        # NICHT STILL WENIGER LIEFERN. Wer sucht und nichts findet, soll nachlesen
        # koennen, ob es nichts gab oder ob etwas aussortiert wurde.
        log(f"Usenet-Suche '{q[:40]}': {verworfen} Treffer fuer nicht bediente "
            f"Plattformen verworfen")
    return out

SET_RE = re.compile(r'\b(collection|fullset|full set|romset|rom set|no-?intro|redump|1g1r|'
                    r'\bpack\b|\bsets?\b|megapack|goodset|good\w+ v\d|tosec|complete\s+set)\b', re.I)
def is_set(title, size):
    if SET_RE.search(title or ""): return True
    return (size or 0) > 4*1024**3      # >4 GB -> vermutlich Sammlung

def is_blocked(title, bl=None):
    """True, wenn der Titel ein Sperrlisten-Stichwort als Teilstring enthält (case-insensitive).
    `bl` kann vorbereitet übergeben werden; sonst wird die Sperrliste aus den Einstellungen geladen."""
    if bl is None:
        bl = [str(p).strip().lower() for p in load_settings().get("blocklist", []) if str(p).strip()]
    t = (title or "").lower()
    return any(p in t for p in bl)

def do_search(q, platforms=None):
    """Suche über die aktiven Quellen und Zusammenführung: Archive.org (Retro) + Prowlarr/
    Usenet (moderne Konsolen), nach `platforms` gefiltert, gruppiert (gkey) für die Versionen-
    Ansicht und mit `in_library`-Markierung. Reine Retro-Auswahl überspringt Usenet."""
    platforms = [p for p in (platforms or []) if p]
    # IMMER ALLE QUELLEN FRAGEN (#375, Jens' Vorgabe). Hier stand vorher eine Abkuerzung:
    # Enthielt die Auswahl keine Plattform mit bekannter Usenet-Kategorie, wurde Usenet
    # gar nicht erst befragt. Gedacht war das fuer reine Retro-Auswahlen, die auf
    # Archive.org liegen — bezahlt haben es die Plattformen, deren Kategorie schlicht
    # FEHLTE: „Wii U" schaltete Usenet ab, obwohl sieben Veroeffentlichungen dalagen.
    #
    # Eine Quelle wegen einer TABELLE zu ueberspringen heisst, einen Tabellenfehler in
    # ein fehlendes Suchergebnis zu uebersetzen — und das sieht aus wie „gibt es nicht".
    # Gefiltert wird jetzt ausschliesslich am Ergebnis, nie an der Frage.
    #
    # Always ask every source: skipping one because of a lookup table turns a table gap
    # into a missing result, which looks exactly like "does not exist".
    usenet_cats = cfg("prow_cats")
    res = []
    bl = [str(p).strip().lower() for p in load_settings().get("blocklist", []) if str(p).strip()]
    ar = search_archive(q); us = search_usenet(q, usenet_cats)
    fh = search_filehoster(q) if catalog_urls() else []
    offen = angefragte_titel()   # einmal, nicht je Treffer
    for idx, r in enumerate(ar+us+fh):
        if is_blocked(r["title"], bl): continue        # Sperrliste
        if platforms:
            # bekannte Fremd-Plattform raus (beide Quellen)
            if r["platform"] and r["platform"] not in platforms: continue
            # Usenet ohne erkannte Plattform raus (Titel tragen sonst keine Zuordnung)
            if r["source"]=="usenet" and not r["platform"]: continue
        r["platform_slug"] = resolve_slug(r["platform"])
        r["in_library"] = in_library(r["title"], r["platform"])
        r["is_set"] = is_set(r["title"], r["size"])
        r["gkey"] = norm(r["title"])          # zum Gruppieren gleicher Titel (Versionen)
        # „angefragt" ist ein ANDERER Zustand als „vorhanden", und beide interessieren VOR
        # dem Klick. Ohne das trägt die Karte einen Download-Knopf für etwas, das längst
        # unterwegs ist. Vorhandenes schlägt angefragt — sonst stünde beides da. (#205)
        r["requested"] = (not r["in_library"]) and r["gkey"] in offen
        # Fassung aus dem Release-Namen lesen (Region/Revision/Sprache/Dump-Status). (#77)
        r["variant"] = parse_release(r["title"])
        r["variant_label"] = variant_label(r["variant"])
        r["_rank"] = idx
        # Cover für Usenet-Treffer werden im Frontend lazy über /api/cover geladen
        res.append(r)
    # Einzeltitel zuerst, dann Sets; Vorhandene ans Ende; INNERHALB desselben Titels nach
    # der Fassungs-Voreinstellung des Nutzers, sonst Relevanz-Reihenfolge. (#77)
    prefs = variant_prefs(session.get("user", "") if has_request_context() else "")
    # BESTAETIGTE TREFFER ZUERST (#375). Ein Ergebnis OHNE erkannte Plattform passiert
    # jeden Filter — absichtlich, denn Archive.org-Titel tragen oft keine Zuordnung und
    # sind trotzdem gemeint. Sie deshalb aber VOR den bestaetigten zu zeigen, war der
    # Fehler: Bei „Mario Kart 8" mit Filter `wiiu` standen sieben unbestimmte Titel oben
    # (ein PC-Torrent, Switch-NSPs, ein Mod) und der erste echte Wii-U-Treffer auf Platz 6.
    # Wer nach einer Plattform filtert, sucht diese Plattform.
    #
    # Confirmed matches first: unclassified results still pass a filter — Archive.org
    # titles often carry no platform and are still what was meant — but they no longer
    # occupy the top of a filtered list.
    passt = (lambda x: 0 if (platforms and x["platform"] in platforms) else 1) if platforms \
        else (lambda x: 0)
    res.sort(key=lambda x: (x["in_library"], passt(x), x["is_set"],
                            variant_rank(x["variant"], prefs), x["_rank"]))
    return res

# ---------- Jobs ----------
# Ein „Job" ist eine Anfrage/ein Download. Zustandsmaschine (Feld `state`):
#   pending  -> (Admin gibt frei) -> queued -> downloading -> importing -> done
#                \-> (Admin lehnt ab) -> denied            \-> error
# `queued`-Jobs werden über die Queue Q an worker_download übergeben; nach Abschluss
# sortiert worker_collect sie ein und setzt `done`. JOBS ist die Liste im RAM, per
# save_jobs()/load_jobs() in SQLite gespiegelt. JOBS_LOCK schützt die Liste.
JOBS = []           # Liste von Job-Dicts / list of job dicts
JOBS_LOCK = threading.Lock()
Q = queue.Queue()   # jid-Warteschlange freigegebener Jobs für worker_download

def load_jobs():
    global JOBS
    try:
        with closing(db_conn()) as c:
            JOBS = [json.loads(d) for (d,) in c.execute("SELECT data FROM jobs ORDER BY seq")]
    except Exception as e:
        log(f"Job-Laden-Fehler: {e}"); JOBS = []
# Zustaende, die einen laufenden Prozess VORAUSSETZEN. Sie ueberleben einen Neustart
# nicht: Der Arbeitsfaden, der sie gesetzt hat, ist dann weg, und niemand setzt sie je
# weiter. `pending`/`queued` sind hier bewusst NICHT dabei — die warten auf eine
# Entscheidung bzw. auf die Warteschlange und sind nach einem Neustart voellig in Ordnung.
FLUECHTIGE_ZUSTAENDE = ("downloading", "importing")

def jobs_nach_neustart_aufraeumen():
    """Auftraege einsammeln, die ein Neustart mitten in der Arbeit erwischt hat. (#336)

    WARUM DAS NOETIG IST — gemessen, nicht befuerchtet: Nach vier gewoehnlichen
    Deployments an einem Tag stand ein Import 11,5 Stunden auf `importing`, mit leerem
    Staging. Nichts entpackte mehr etwas; der Zustand war nur noch eine Behauptung.

    WARUM DAS MEHR ALS EINEN TOTEN AUFTRAG KOSTET: `importing` steht in
    OFFENE_ZUSTAENDE. Damit gilt der Titel als „bereits angefragt" und laesst sich nicht
    erneut anfordern, UND sein Rest-Ordner ist vor dem Aufraeumen geschuetzt (#244) —
    beides mit einem Zustand, der nie endet.

    WARUM `error` UND NICHT ERNEUT IN DIE WARTESCHLANGE: Was der Import schon getan hat,
    weiss niemand mehr — halb entpackte Dateien koennen im Zielordner liegen. Ein blinder
    zweiter Lauf wuerde darauf aufsetzen. `error` mit klarer Meldung gibt die Entscheidung
    an den Menschen zurueck, und der Titel ist sofort wieder anfragbar.

    States that require a running thread cannot survive a restart: the thread is gone and
    nobody advances them. They are moved to `error` rather than re-queued, because what a
    half-finished import already wrote is unknown, and a blind second run would build on it.
    """
    with JOBS_LOCK:
        betroffen = [(j["id"], str(j.get("title") or "")[:40]) for j in JOBS
                     if j.get("state") in FLUECHTIGE_ZUSTAENDE]
    # Ausserhalb des Locks: `set_state` nimmt es selbst. Und ueber `set_state` statt per
    # Hand, damit der Zeitstempel dieselbe Form hat wie ueberall sonst — eine zweite
    # Schreibweise faellt erst auf, wenn jemand die Liste sortiert.
    for jid, _titel in betroffen:
        set_state(jid, state="error",
                  msg="durch Neustart unterbrochen — bitte erneut anfragen / "
                      "interrupted by a restart, please request again")
    if betroffen:
        log(f"Neustart-Aufraeumen: {len(betroffen)} Auftrag/Auftraege abgebrochen — "
            + "; ".join(f"{jid} {t}" for jid, t in betroffen))
    return [jid for jid, _ in betroffen]

# --- Wachhund fuer haengende Auftraege (#340) --------------------------------------
#
# Der Neustart-Aufraeumer oben faengt genau EINEN Fall: Der Prozess ist gestorben. Ein
# Arbeitsfaden, der LEBT aber nicht vorankommt, sieht von aussen genauso aus — nur dass
# kein Neustart kommt, der ihn einsammelt. Ein Entpacken auf voller Platte, ein Abruf
# ohne Zeitlimit, ein Faden hinter einer Sperre: alles laeuft, nichts bewegt sich.
#
# WARUM NICHT NACH ALTER: Ein grosser Download DARF Stunden brauchen. `aria2c` laeuft hier
# synchron und ohne Zwischenmeldung — ein Wachhund, der auf Meldungen achtet, wuerde genau
# die gesunden Faelle abwuergen. Und eine Pruefung, die arbeitende Downloads abbricht, ist
# binnen einer Woche abgeschaltet; dann steht die Regel schlechter da als ohne sie.
#
# Gemessen wird deshalb ECHTER Fortschritt: die Bytes im Arbeitsverzeichnis des Auftrags.
# Waechst die Zahl, passiert etwas — unabhaengig davon, ob jemand eine Meldung schreibt.
#
# Age is the wrong criterion: a large download legitimately takes hours, and aria2c runs
# synchronously without progress messages. Real progress is measured instead — bytes in the
# job's working directory.

# Wie lange darf ein Zustand OHNE Fortschritt bleiben, bevor er als haengend gilt?
# Grosszuegig gewaehlt: Der Preis eines zu frueh abgebrochenen Downloads ist hoeher als
# der eines spaeter erkannten Haengers.
WACHHUND_GRENZEN = {
    "downloading": int(os.environ.get("ROMSEERR_MAX_STILL_DOWNLOAD", 6 * 3600)),
    "importing":   int(os.environ.get("ROMSEERR_MAX_STILL_IMPORT", 2 * 3600)),
}
WACHHUND_TAKT = int(os.environ.get("ROMSEERR_WACHHUND_TAKT", 300))

def job_arbeitsbytes(jid):
    """Bytes im Arbeitsverzeichnis eines Auftrags — ueber alle Ablagen hinweg.

    Gibt 0 zurueck, wenn nichts (mehr) da ist. Das ist KEIN Hinweis auf einen Haenger:
    zwischen Download und Import liegt ein Moment, in dem der Ordner verschoben wird.
    Deshalb entscheidet allein, ob sich die Zahl VERAENDERT — in beide Richtungen.
    """
    gesamt = 0
    for basis in (STAGING, SAB_DONE, jd_out_dir()):
        if not basis or not os.path.isdir(basis):
            continue
        pfad = os.path.join(basis, f"romseerr_{jid}")
        if not os.path.isdir(pfad):
            continue
        for wurzel, _d, dateien in os.walk(pfad):
            for fn in dateien:
                try:
                    gesamt += os.path.getsize(os.path.join(wurzel, fn))
                except OSError:
                    pass
    return gesamt

def worker_wachhund():
    """Auftraege abbrechen, die leben, aber seit zu langer Zeit nicht vorankommen."""
    letzte = {}          # jid -> (bytes, zeitpunkt der letzten Veraenderung)
    while True:
        time.sleep(WACHHUND_TAKT)
        try:
            with JOBS_LOCK:
                offen = [(j["id"], j.get("state"), float(j.get("ts") or 0))
                         for j in JOBS if j.get("state") in WACHHUND_GRENZEN]
            jetzt = time.time()
            aktiv = set()
            for jid, zustand, ts in offen:
                aktiv.add(jid)
                groesse = job_arbeitsbytes(jid)
                alt_groesse, seit = letzte.get(jid, (None, jetzt))
                if alt_groesse is None or groesse != alt_groesse:
                    letzte[jid] = (groesse, jetzt)      # es bewegt sich
                    continue
                # Auch eine Zustandsmeldung zaehlt als Lebenszeichen — sie kommt bei
                # Usenet-Downloads im Prozentschritt, wo die Bytes woanders liegen.
                bewegung = max(seit, ts)
                grenze = WACHHUND_GRENZEN[zustand]
                if jetzt - bewegung > grenze:
                    std = grenze // 3600
                    set_state(jid, state="error",
                              msg=(f"seit ueber {std} h kein Fortschritt — abgebrochen / "
                                   f"no progress for over {std} h, aborted"))
                    log(f"Wachhund: Auftrag {jid} in '{zustand}' seit "
                        f"{int((jetzt - bewegung) / 60)} min ohne Fortschritt — abgebrochen")
                    letzte.pop(jid, None)
            for jid in [k for k in letzte if k not in aktiv]:
                letzte.pop(jid, None)
        except Exception as e:
            log(f"Wachhund-Fehler: {e}")

def save_jobs():
    try:
        with DB_LOCK, closing(db_conn()) as c, c:
            c.execute("DELETE FROM jobs")
            c.executemany("INSERT INTO jobs(jid,data) VALUES(?,?)",
                          [(j.get("id",""), json.dumps(j)) for j in JOBS])
    except Exception as e:
        log(f"Job-Speichern-Fehler: {e}")
def set_state(jid, **kw):
    """Felder eines Jobs aktualisieren (z. B. state=…, msg=…) und persistieren."""
    with JOBS_LOCK:
        for j in JOBS:
            if j["id"]==jid:
                j.update(kw)
                j["updated"] = datetime.now().strftime("%H:%M:%S")
                # `updated` ist eine Uhrzeit OHNE Datum — zum Anzeigen gedacht und fuer
                # jede Altersrechnung untauglich (ueber Mitternacht laeuft sie rueckwaerts).
                # `ts` ist der maschinenlesbare Zeitpunkt daneben. (#340)
                # `updated` is a time of day without a date: fine to display, useless for
                # measuring age. `ts` is the machine-readable one.
                j["ts"] = time.time()
        save_jobs()

def new_job(item, user="", approved=True):
    """Anfrage anlegen. approved=True -> direkt `queued` + in die Worker-Queue;
    approved=False -> `pending` (wartet auf Admin-Freigabe). Gibt den Job zurück."""
    # FRUEH ABSAGEN, nicht nach 5,5 GB (#382/#384). Ein zugangsbeschraenkter
    # Archive.org-Titel ohne hinterlegte Schluessel endet zwangslaeufig in HTTP 401 —
    # das jetzt zu sagen ist ehrlicher als ein Auftrag, der stundenlang laeuft und
    # scheitert. Dieselbe Regel wie bei den 3DS-Abbildern (#299).
    if item.get("restricted") and item.get("source") == "archive" and not ia_bereit():
        raise ValueError("ia_login_required")
    jid = f"{int(time.time())}{len(JOBS)%1000:03d}"
    job = {"id":jid,"title":item["title"],"source":item["source"],"ref":item["ref"],
           "platform":item.get("platform_slug") or "","size":item.get("size",0),
           "variant":item.get("variant") or parse_release(item.get("title","")),
           "variant_label":variant_label(item.get("variant") or parse_release(item.get("title",""))),
           "variant_wanted":item.get("variant_wanted") or {},
           "user":user,"state":"queued" if approved else "pending","created":int(time.time()),
           "updated":datetime.now().strftime("%H:%M:%S"),"msg":"" if approved else "wartet auf Freigabe"}
    with JOBS_LOCK: JOBS.append(job); save_jobs()
    if approved: Q.put(jid)
    return job

# Zustaende, in denen ein Titel BEREITS ANGEFRAGT ist, aber noch nicht in der Bibliothek
# liegt. `done` gehoert nicht dazu — dann greift `in_library`, und beides zugleich zu
# melden waere doppelt gemoppelt. `error`/`denied` auch nicht: da ist nichts unterwegs,
# und der Titel soll wieder anforderbar aussehen. (#205)
OFFENE_ZUSTAENDE = ("pending", "queued", "approved", "downloading", "importing")

def angefragte_titel():
    """Menge normalisierter Titel, die gerade in Arbeit sind. Normalisiert, weil ein
    Suchtreffer anders geschrieben ist als der Job-Titel (Release-Namen, Klammern)."""
    with JOBS_LOCK:
        return {norm(j.get("title", "")) for j in JOBS
                if j.get("state") in OFFENE_ZUSTAENDE and j.get("title")}

def get_job(jid):
    with JOBS_LOCK:
        for j in JOBS:
            if j["id"]==jid: return dict(j)
    return None

# ---------- Wunschliste (Wishlist + Auto-Download) ----------
# Titel, für die es (noch) keine Quelle gibt, kann ein Nutzer vormerken. Ein
# Hintergrund-Worker sucht periodisch erneut; taucht eine passende Quelle auf,
# wird sie automatisch angefragt und der Eintrag entfernt. Struktur im kv-Store
# unter "wishlist": {user: [{title, platform, added}]}.
WISH_LOCK = threading.Lock()
WISH_INTERVAL = int(os.environ.get("ROMSEERR_WISH_INTERVAL", "1800"))   # Sekunden zwischen den Läufen
def load_wishlist(): return kv_get("wishlist", {})
def save_wishlist(w): kv_put("wishlist", w)
def wishlist_add(user, title, platform=""):
    title = (title or "").strip()
    if not (user and title): return
    with WISH_LOCK:
        w = load_wishlist(); lst = w.setdefault(user, [])
        if any(norm(e.get("title","")) == norm(title) and (e.get("platform") or "") == (platform or "")
               for e in lst): return
        lst.append({"title": title, "platform": platform or "", "added": int(time.time())})
        save_wishlist(w)
# --- Eigene Bewertungen und Kommentare (#210) --------------------------------------
# ENTSCHIEDEN, bevor die Tabelle stand (das verlangte das Issue ausdruecklich):
#
#   * Bewertet wird der TITEL, nicht die Fassung. Die Bibliothek haelt mehrere Fassungen
#     desselben Spiels; eine Meinung gilt dem Spiel. Schluessel ist `norm(title)` — dieselbe
#     Normalisierung wie bei Favoriten und `in_library`.
#   * JE NUTZER, nicht gemittelt. Zwei Menschen sind der interessante Fall, und der
#     Mittelwert aus zwei Meinungen sagt weniger als beide nebeneinander. „Deine Bewertung"
#     steht vorn, die der anderen daneben.
#   * Gespeichert in SQLite ueber `kv`, keine neue JSON-Datei (#192).
RATE_LOCK = threading.Lock()
def load_ratings(): return kv_get("ratings", {})
def load_comments(): return kv_get("comments", {})
def rating_set(user, title, stars):
    """stars 1..5, 0 loescht die eigene Bewertung wieder."""
    k = norm(title)
    if not (user and k): return
    with RATE_LOCK:
        r = load_ratings(); je = r.setdefault(k, {})
        if stars: je[user] = {"stars": int(stars), "ts": int(time.time())}
        else: je.pop(user, None)
        if not je: r.pop(k, None)
        kv_put("ratings", r)
def comment_add(user, title, text):
    k, text = norm(title), (text or "").strip()[:2000]
    if not (user and k and text): return
    with RATE_LOCK:
        c = load_comments()
        c.setdefault(k, []).append({"user": user, "text": text, "ts": int(time.time())})
        kv_put("comments", c)

# --- Favoriten (#207) -------------------------------------------------------------
# BEWUSST ein eigener Speicher, nicht ein Feld an der Wunschliste: die beiden Listen
# beantworten gegensaetzliche Fragen. Die Wunschliste sagt „habe ich nicht, haette ich
# gern" und LEERT sich, sobald der Titel eintrifft — genau das ist ihr Zweck. Ein Favorit
# sagt „habe ich, will ich schnell wiederfinden" und darf nie von selbst verschwinden.
# Zusammengelegt waere jedes Eintreffen ein Datenverlust auf der einen oder eine
# Karteileiche auf der anderen Seite. Ein Titel darf in beiden stehen (kurz), in einer
# oder in keiner.
FAV_LOCK = threading.Lock()
def load_favs(): return kv_get("favourites", {})
def save_favs(f): kv_put("favourites", f)
def fav_add(user, title, platform=""):
    title = (title or "").strip()
    if not (user and title): return
    with FAV_LOCK:
        f = load_favs(); lst = f.setdefault(user, [])
        if any(norm(e.get("title","")) == norm(title) for e in lst): return
        lst.append({"title": title, "platform": platform or "", "added": int(time.time())})
        save_favs(f)
def fav_remove(user, title):
    with FAV_LOCK:
        f = load_favs()
        f[user] = [e for e in f.get(user, []) if norm(e.get("title","")) != norm(title)]
        save_favs(f)
def is_fav(user, title):
    return any(norm(e.get("title","")) == norm(title) for e in load_favs().get(user, []))

def wishlist_remove(user, title, platform=None):
    with WISH_LOCK:
        w = load_wishlist()
        w[user] = [e for e in w.get(user, [])
                   if not (norm(e.get("title","")) == norm(title)
                           and (platform is None or (e.get("platform") or "") == (platform or "")))]
        save_wishlist(w)

def _title_tokens(s):
    return [w for w in re.split(r'\s+', re.sub(r'[^a-z0-9]+', ' ', (s or "").lower())) if len(w) > 1]
def wishlist_title_matches(want, cand):
    """Streng: JEDES Wort des Wunschtitels muss als ganzes Token im Treffer vorkommen.
    Verhindert, dass ein kurzer Eintrag („Mario") einen unpassenden Obermenge-Titel auslöst."""
    wt = _title_tokens(want)
    ct = set(_title_tokens(cand))
    return bool(wt) and all(w in ct for w in wt)

# ---------- Wunschlisten-Import (Liste einfügen / Datei hochladen) ----------
# Eine Wunschliste entsteht selten Eintrag für Eintrag — sie liegt schon irgendwo als
# Notizzettel oder Tabelle. Der Import ist bewusst ein ZWEISCHRITT: erst Vorschau
# (getroffen / mehrdeutig / nicht gefunden), dann schreibt der Nutzer, was er bestätigt.
# Der Fehlermodus, den es zu vermeiden gilt, ist eine still mit Beinahe-Treffern
# gefüllte Wunschliste — der Auto-Download würde die dann auch noch holen.
WISH_IMPORT_MAX = 200          # Zeilen je Import (danach klare Meldung statt endloser Schleife)
_PLAT_LOOKUP = {**{s: s for s in SLUG_NAME},
                **{n.lower(): s for s, n in SLUG_NAME.items()}}

def parse_platform(token):
    """'snes', 'SNES', 'Game Boy' -> Slug; unbekannt -> '' (statt zu raten)."""
    return _PLAT_LOOKUP.get((token or "").strip().lower(), "")

def parse_wishlist_text(text):
    """Freitext in [(Titel, Plattform-Slug, Rohzeile)] zerlegen.

    Ein Titel je Zeile, optional `Titel;Plattform` (auch Tab). Ein **Komma** trennt nur
    dann ab, wenn der Teil dahinter wirklich eine bekannte Plattform ist — sonst würde
    „Sonic 3 & Knuckles, Special Edition" mitten im Titel zerschnitten."""
    rows = []
    for raw in (text or "").splitlines():
        line = raw.strip().lstrip("﻿")
        if not line or line.startswith("#"): continue
        title, plat = line, ""
        for sep in (";", "\t"):
            if sep in line:
                a, _, b = line.partition(sep)
                title, plat = a.strip(), parse_platform(b)
                break
        else:
            if "," in line:
                a, _, b = line.rpartition(",")
                p = parse_platform(b)
                if p: title, plat = a.strip(), p
        title = title.strip().strip('"').strip()
        if title: rows.append((title[:120], plat, line))
    return rows

def wishlist_preview(user, text):
    """Vorschau erzeugen: je Zeile den Zustand bestimmen, OHNE etwas zu schreiben.

    Zustände: `in_library` (schon da), `duplicate` (schon auf der Wunschliste),
    `matched` (genau ein Katalogtreffer), `ambiguous` (mehrere — der Nutzer wählt),
    `not_found` (Katalog kennt ihn nicht) und `unverified` (kein IGDB konfiguriert
    oder Abfrage fehlgeschlagen — bewusst NICHT als „nicht gefunden" ausgegeben)."""
    rows = parse_wishlist_text(text)
    truncated = len(rows) > WISH_IMPORT_MAX
    rows = rows[:WISH_IMPORT_MAX]
    have = {(norm(e.get("title", "")), e.get("platform") or "")
            for e in load_wishlist().get(user, [])}
    cand_map = igdb_multisearch([t for t, _p, _r in rows])
    checked = bool(cand_map)
    entries = []
    for title, plat, raw in rows:
        e = {"title": title, "platform": plat, "line": raw, "candidates": []}
        if in_library(title, plat or None):
            e["status"] = "in_library"
        elif (norm(title), plat) in have:
            e["status"] = "duplicate"
        elif not checked:
            e["status"] = "unverified"
        else:
            cands = cand_map.get(title, [])
            exact = [c for c in cands if norm(c) == norm(title)]
            if len(exact) == 1:
                e["status"] = "matched"; e["title"] = exact[0]
            elif cands:
                e["status"] = "ambiguous"; e["candidates"] = cands[:5]
            else:
                e["status"] = "not_found"
        entries.append(e)
    counts = {}
    for e in entries: counts[e["status"]] = counts.get(e["status"], 0) + 1
    return {"ok": True, "entries": entries, "counts": counts, "total": len(entries),
            "truncated": truncated, "max": WISH_IMPORT_MAX, "checked": checked,
            "quota": quota_info(user)}

def wishlist_import(user, entries):
    """Bestätigte Einträge schreiben. Nutzt denselben Weg wie eine Einzel-Hinzufügung
    (`wishlist_add`, dedupliziert) und dieselbe Bibliotheksprüfung — der Import ist damit
    nachweislich kein zweiter, laxerer Pfad."""
    added, skipped = 0, 0
    for e in (entries or [])[:WISH_IMPORT_MAX]:
        title = (e.get("title") or "").strip()[:120]
        plat = parse_platform(e.get("platform") or "")
        if not title or in_library(title, plat or None):
            skipped += 1; continue
        before = len(load_wishlist().get(user, []))
        wishlist_add(user, title, plat)
        if len(load_wishlist().get(user, [])) > before: added += 1
        else: skipped += 1        # wishlist_add dedupliziert -> war schon drauf
    return {"ok": True, "added": added, "skipped": skipped}

def worker_wishlist():
    """Prüft periodisch alle Wunschlisten. Erscheint zu einem Eintrag eine passende
    Quelle (Titel-Abgleich streng, um Fehlgriffe zu vermeiden) und ist er nicht schon
    in der Bibliothek, wird automatisch angefragt (immer freigegeben — der Nutzer hat
    den Titel bewusst vorgemerkt) und der Eintrag entfernt."""
    time.sleep(90)   # dem Index/den Diensten nach dem Start Zeit geben
    while True:
        beat("wishlist")
        try:
            for user, lst in list(load_wishlist().items()):
                for e in list(lst):
                    title = e.get("title",""); plat = e.get("platform") or ""
                    if not title: continue
                    if in_library(title, plat or None):
                        wishlist_remove(user, title, plat); continue
                    try:
                        hits = do_search(title, [plat] if plat else None)
                    except Exception as ex:
                        log(f"Wunschliste-Suche '{title}': {ex}"); continue
                    best = next((r for r in hits if not r["in_library"]
                                 and wishlist_title_matches(title, r["title"])), None)
                    if not best: continue
                    new_job(best, user=user, approved=True)
                    wishlist_remove(user, title, plat)
                    try:
                        send_push_to_user(user, "Romseerr",
                            f"Aus deiner Wunschliste verfügbar / from your wishlist: {title[:60]}")
                        notify_send(f"⭐ Wunschliste erfüllt / wishlist granted: **{title}** ({user})")
                    except Exception: pass
                    time.sleep(2)   # externe Quellen schonen
        except Exception as ex:
            log(f"Wunschlisten-Worker: {ex}")
        time.sleep(WISH_INTERVAL)

def quota_used(user, days):
    """Anzahl der Anfragen eines Nutzers innerhalb der letzten `days` Tage (abgelehnte zählen nicht)."""
    cutoff = time.time() - int(days)*86400
    with JOBS_LOCK:
        return sum(1 for j in JOBS if j.get("user")==user and j.get("state")!="denied" and j.get("created",0)>=cutoff)
def quota_info(user):
    """Kontingent-Status für einen Nutzer (enabled/count/days/used/remaining);
    quota_exempt-Berechtigte und deaktiviertes Kontingent -> {'enabled': False}."""
    q = load_settings().get("quota", {})
    if not q.get("enabled") or has_perm("quota_exempt", user):
        return {"enabled": False}
    cnt = int(q.get("count", 10) or 10); days = int(q.get("days", 7) or 7)
    used = quota_used(user, days)
    return {"enabled": True, "count": cnt, "days": days, "used": used, "remaining": max(0, cnt-used)}

# ---------- Download-Aktionen ----------
def dl_name(jid, title):
    """Download-/Ordnername für SAB & JDownloader: stabiles Präfix `romseerr_<jid>` plus
    (nach `__`) der bereinigte ROM-Titel, damit die Anfrage in SABnzbd/JDownloader
    erkennbar ist. `worker_collect` findet den fertigen Ordner über das Präfix. (#64)"""
    safe = re.sub(r'[^A-Za-z0-9]+', '.', (title or '')).strip('.')[:80]
    return f"romseerr_{jid}__{safe}" if safe else f"romseerr_{jid}"

# Der Auftragspraefix aus `dl_name`, wie er in einem Dateinamen ankommt. (#613)
PRAEFIX_RE = re.compile(r"^romseerr_\d+__")

def ohne_auftragspraefix(name):
    """`romseerr_<jid>__Titel.xci` -> `Titel.xci`. (#613)

    WOHER DER PRAEFIX KOMMT UND WARUM ER BLEIBEN MUSS: `dl_name` setzt ihn, damit
    `find_output` den fertigen Ordner wiederfindet (#64). Das ist richtig — er gehoert
    zur Auftragsverwaltung.

    WARUM ER TROTZDEM NICHT IN DIE BIBLIOTHEK GEHOERT: Besteht ein Release aus einer
    einzigen Datei, benennt SAB sie nach dem Auftrag, und der Import uebernahm den Namen
    unveraendert. In der Bibliothek standen daraufhin acht Dateien wie
    `romseerr_1786694061017__Sonic.X.Shadow.Generations.NSW.NiiNTENDO.xci` — RomM zeigt
    den Dateinamen als Titel an.

    Schwerer wiegt der Zeitstempel darin: Zwei Kopien desselben Spiels, zu verschiedenen
    Zeiten geholt, tragen verschiedene Praefixe und sehen damit fuer die Dublettenpruefung
    wie zwei verschiedene Titel aus.

    EN: the job prefix belongs to the job machinery, not to the shelf — and because it
    contains a timestamp, two copies of one game never look like duplicates.
    """
    return PRAEFIX_RE.sub("", name or "")

def find_output(base, jid):
    """Fertigen Ausgabeordner zu einem Job über das `romseerr_<jid>`-Präfix finden
    (exakt oder mit Titel-Suffix). Robust gegen die Namensbereinigung von SAB/JD:
    der jid ist fixer Länge, ein direkt folgendes Zeichen darf keine Ziffer sein
    (sonst wäre es ein längerer jid), damit keine Verwechslung entsteht."""
    pref = f"romseerr_{jid}"
    try:
        # `with`, sonst bleibt der Deskriptor offen (#589) — hier besonders, weil die
        # Funktion mitten in der Schleife per `return` verlassen wird.
        with os.scandir(base) as eintraege:
            for e in eintraege:
                if not e.is_dir() or not e.name.startswith(pref): continue
                rest = e.name[len(pref):]
                if rest == "" or not rest[0].isdigit():
                    return e.path
    except (FileNotFoundError, NotADirectoryError): pass
    return None

def sab_add(url, name):
    r = requests.get(f"{cfg("sab_url")}/api", params={"mode":"addurl","name":url,"nzbname":name,
        "cat":cfg("sab_cat"),"apikey":cfg("sab_apikey"),"output":"json"}, timeout=20)
    j = r.json()
    if not j.get("status"): raise RuntimeError(f"SAB: {j}")
    return j

def sab_cleanup(jid):
    """Nach dem Import den SAB-History-Eintrag samt Dateien entfernen (del_files=1),
    damit erledigte Downloads nicht in SABnzbd liegen bleiben. Über das
    `romseerr_<jid>`-Präfix zugeordnet. (#65)"""
    if not (cfg("sab_url") and cfg("sab_apikey")): return
    pref = f"romseerr_{jid}"
    try:
        j = requests.get(f"{cfg('sab_url')}/api", params={"mode":"history","output":"json",
            "apikey":cfg("sab_apikey"),"limit":200}, timeout=10).json()
        for s in (j.get("history",{}) or {}).get("slots",[]) or []:
            nm = (s.get("name","") or "") + " " + (s.get("nzb_name","") or "")
            if pref in nm and s.get("nzo_id"):
                requests.get(f"{cfg('sab_url')}/api", params={"mode":"history","name":"delete",
                    "value":s["nzo_id"],"del_files":1,"apikey":cfg("sab_apikey"),"output":"json"}, timeout=10)
    except Exception as e:
        log(f"SAB-Cleanup {jid}: {e}")

def sab_failed(jid):
    """Die Fehlermeldung aus SABnzbds History, wenn der Auftrag dort gescheitert ist. (#235)

    Ein NZB, das SAB nicht laden konnte, verlaesst die Warteschlange **ohne** je einen
    Ordner anzulegen. worker_collect kannte nur „Ordner da?" und „noch in der Queue?" —
    zwischen diesen beiden Fragen fiel der Fehlschlag hindurch, und der Auftrag blieb fuer
    immer auf `downloading`. Die History ist die einzige Stelle, an der SAB den Fehlschlag
    festhaelt; gelesen wurde sie bisher nur nach einem ERFOLGREICHEN Import.

    Gibt den Grund zurueck (immer eine nicht-leere Zeichenkette, wenn gescheitert), sonst
    None. Der History-Eintrag bleibt liegen: er ist der Beleg fuer den Betreiber, und der
    Auftrag steht danach nicht mehr auf `downloading`, kann also nicht doppelt anschlagen.
    """
    if not (cfg("sab_url") and cfg("sab_apikey")): return None
    pref = f"romseerr_{jid}"
    try:
        j = requests.get(f"{cfg('sab_url')}/api", params={"mode":"history","output":"json",
            "apikey":cfg("sab_apikey"),"limit":200}, timeout=10).json()
        for s in (j.get("history",{}) or {}).get("slots",[]) or []:
            nm = (s.get("name","") or "") + " " + (s.get("nzb_name","") or "")
            if pref in nm and str(s.get("status","")).lower() == "failed":
                return (s.get("fail_message") or "").strip() or "SABnzbd: fehlgeschlagen / failed"
    except Exception as e:
        log(f"SAB-History {jid}: {e}")
    return None

def sab_queue():
    """SAB-Warteschlange -> {Dateiname: Prozent}. Best effort (für die Fortschrittsanzeige)."""
    out = {}
    if not (cfg("sab_url") and cfg("sab_apikey")): return out
    try:
        j = requests.get(f"{cfg('sab_url')}/api", params={"mode":"queue","output":"json",
            "apikey":cfg("sab_apikey")}, timeout=8).json()
        for s in (j.get("queue", {}) or {}).get("slots", []) or []:
            out[s.get("filename") or ""] = s.get("percentage", "")
    except Exception:
        pass
    return out

def sab_hat_auftrag(jid):
    """Laeuft dieser Auftrag schon in SAB? -> Name des Eintrags oder None. (#609)

    Ein Neustart erklaert laufende Auftraege fuer tot (#336) — SAB laedt sie aber weiter.
    Ohne diese Frage uebergibt ein `retry` dasselbe NZB ein zweites Mal.

    GEMESSEN nach einem Deploy waehrend 13 Downloads: 19 Warteschlangeneintraege fuer 13
    Auftraege, vier Titel doppelt, 115,6 GB offen statt 66. Und schlimmer als die doppelte
    Last: SAB haengt bei Namensgleichheit ein `.1` an, womit ZWEI Ordner denselben Praefix
    `romseerr_<jid>` tragen. `find_output` nimmt den, den `os.scandir` zuerst liefert — im
    gemessenen Fall waeren das 180 KB statt 853 MB gewesen, und der Auftrag haette Erfolg
    gemeldet.

    EN: does SAB already have this job? Without asking, a retry after a restart hands the
    same NZB over twice and the import may then pick the empty folder.
    """
    marke = f"romseerr_{jid}"
    for name in sab_queue():
        if not name.startswith(marke):
            continue
        # DIESELBE VORSICHT WIE IN `find_output`: Praefixgleichheit allein genuegt NICHT.
        # `romseerr_111` passt sonst auf `romseerr_1119__…`, und ein fremder Auftrag
        # gaelte als der eigene — der Titel wuerde dann nie geladen, weil Romseerr ihn
        # faelschlich fuer schon laufend haelt. Das Zeichen direkt hinter der Auftrags-ID
        # darf deshalb keine Ziffer sein; `dl_name` setzt dort `__`.
        rest = name[len(marke):]
        if rest and rest[0].isdigit():
            continue
        return name
    return None

def jd_watch_dir(): return cfg("jd_watch") or JD_WATCH

def jd_out_from_base(base):
    """Romseerrs Sicht auf JDownloaders Zielordner AUS der JD-Sicht ableiten.

    Beide zeigen auf denselben Ordner auf der Platte, nur der Mountpunkt heisst anders:
    JDownloader sieht ihn unter `/output`, Romseerr unter `/jd-output`. Ersetzt wird
    deshalb genau das erste Pfadsegment, der Rest bleibt — `/output/rom-suche` wird zu
    `/jd-output/rom-suche`. (#197)"""
    teile = [p for p in (base or "").strip().split("/") if p]
    if not teile: return JD_OUT
    return "/".join([JD_OUT_ROOT] + teile[1:])

def jd_out_dir():
    """Ausdrueckliche Einstellung schlaegt alles, sonst wird aus `jd_dl_base` abgeleitet.

    Vorher hatten beide Sichten je einen eigenen Default. Wer in der Oberfläche
    `jd_dl_base` aenderte (hier: auf `/output/rom-suche`), liess `jd_out` still auf
    `/jd-output/romseerr` stehen — ein Ordner, den JDownloader nie anlegt. Die Uebergabe
    meldete daraufhin „Ausgabe-Ordner fehlt", obwohl nichts fehlte ausser der
    Uebereinstimmung. (#197)"""
    gesetzt = (cfg("jd_out") or "").strip().rstrip("/")
    return gesetzt or jd_out_from_base(cfg("jd_dl_base"))

def jd_ensure_out():
    """Ausgabe-Ordner anlegen, wenn er fehlt. Gibt (ok, Hinweis) zurueck.

    Ein fehlender Zielordner ist kein Zustand, den ein Mensch beheben muss — JDownloader
    legt ihn beim ersten Download selbst an, Romseerr braucht ihn aber schon vorher zum
    Einsammeln. Achtmal dieselbe Startwarnung zu schreiben und nichts zu tun war die
    schlechtere Haelfte davon. (#197)"""
    out = jd_out_dir()
    if os.path.isdir(out): return True, out
    try:
        os.makedirs(out, exist_ok=True)
        log(f"JDownloader-Ausgabeordner angelegt / created: {out}")
        return True, out
    except Exception as e:
        return False, f"{out} ({e.__class__.__name__})"

def jd_check(anlegen=False):
    """Zustand der Ordner-Uebergabe an JDownloader. Es gibt keinen Handschlag — ein
    Ordner-Handoff bestaetigt nichts —, also ist die Pruefung der Verzeichnisse die
    EINZIGE Moeglichkeit, dem Betreiber ueberhaupt ein Signal zu geben. (#83)

    „fehlt" und „nicht beschreibbar" werden getrennt gemeldet: der eine Fall wird durch
    einen Mount geloest, der andere durch Besitzrechte.

    `anlegen=True` versucht den Ausgabe-Ordner zu erzeugen. Nur wer die Uebergabe
    tatsaechlich benutzt (Start, Schreiben einer .crawljob) heilt; eine Anzeige bleibt
    eine Anzeige und veraendert nichts. (#197)"""
    watch, out = jd_watch_dir(), jd_out_dir()
    if not os.path.isdir(watch):
        return {"ok": False, "reason": "watch_missing",
                "info": f"Watch-Ordner fehlt / watch dir not found: {watch}",
                "fix": "Bind-Mount auf JDownloaders folderwatch prüfen / "
                       "check the bind-mount to JDownloader's folderwatch"}
    if not os.access(watch, os.W_OK):
        return {"ok": False, "reason": "watch_readonly",
                "info": f"Watch-Ordner nicht beschreibbar (uid {os.getuid()}) / "
                        f"not writable by uid {os.getuid()}: {watch}",
                # Die Abhilfe gehoert in die Meldung: uid und Pfad allein sagen dem
                # Betreiber nicht, WAS er aendern soll. (#204)
                "fix": f"{watch} für uid {os.getuid()} beschreibbar machen — gemeinsame "
                       f"Gruppe oder 0775; JDownloader muss die Datei weiterhin löschen "
                       f"können / make it writable for both containers"}
    if anlegen and not os.path.isdir(out):
        jd_ensure_out()
    if not os.path.isdir(out):
        return {"ok": False, "reason": "out_missing",
                "info": f"Ausgabe-Ordner fehlt / output dir not found: {out}",
                "fix": f"{out} anlegen oder JD_DL_BASE/JD_OUT angleichen / "
                       f"create it, or align JD_DL_BASE and JD_OUT"}
    return {"ok": True, "reason": "", "info": f"{watch} → {out}", "fix": ""}

def write_crawljob(jid, links, folder, name):
    """`.crawljob` in den Watch-Ordner legen. folder = JD-Container-Sicht
    (z. B. /output/romseerr/...); JD legt sie selbst an.

    Schlaegt das Schreiben fehl, MUSS die Ausnahme durch: frueher wurde nur geloggt und
    der Job blieb fuer immer auf `downloading` stehen — der Ausfall war unsichtbar. (#83)

    FELDER: `autoStart`/`autoConfirm` sind in JDownloader vom Typ **BooleanStatus**
    (`TRUE`/`FALSE`/`UNSET`), nicht boolean — so steht es in der Beschreibung der
    FolderWatch-Erweiterung. Deshalb `"TRUE"` und nicht `"true"`. In dieser Form ist der
    ganze Weg nachgemessen: Uebergabe, Download und Entpacken durch JDownloader. (#219)

    `overwritePackagizerRules` stand hier frueher und gibt es **nicht** — der Setter heisst
    `setOverwritePackagizerEnabled` (aus `FolderWatch.jar` ausgelesen). Das Feld war immer
    wirkungslos und ist raus.

    EHRLICH ZUR MESSUNG: Ob `"true"` den Auftrag *verliert*, ist NICHT sauber belegt. Die
    erste Messreihe lief gegen einen JDownloader, in dem ein **modaler Dialog** offen stand
    ("links already in the downloadlist") und alles blockierte — Auftraege sahen deshalb
    verschwunden aus, lagen aber nur fest. Belegt ist: die dokumentierte Schreibweise
    funktioniert. Wer hier etwas aendert, misst gegen einen JDownloader OHNE offene
    Dialoge, sonst misst er den Dialog.

    BETRIEBSVORAUSSETZUNG (Doku): JDownloader darf im Automatikbetrieb nichts fragen.
    `Default On Added Dupes Links Action` und die Offline-Variante muessen auf eine
    Aktion stehen, nicht auf `ASK` — sonst wartet ein Dialog, den im Container niemand
    sieht, und die Uebergabe steht still."""
    st = jd_check(anlegen=True)
    if not st["ok"]:
        raise RuntimeError(f"JDownloader-Uebergabe nicht moeglich / handover not possible: {st['info']}")
    data = [{"text":"\n".join(links) if isinstance(links,list) else links,
             "downloadFolder":folder,"packageName":name,
             "autoStart":"TRUE","autoConfirm":"TRUE"}]
    path = os.path.join(jd_watch_dir(), f"romseerr_{jid}.crawljob")
    with open(path,"w") as f: json.dump(data,f)
    log(f"crawljob geschrieben: {path}")

def jd_probe(wartezeit=30):
    """Misst, ob auf der ANDEREN Seite der Uebergabe ueberhaupt jemand zuhoert. (#218)

    `jd_check` prueft drei Dinge, und alle drei liegen auf unserer Seite: Ordner da,
    beschreibbar, Ziel da. Nach #197 meldete es `ok: True` — zutreffend und trotzdem
    nutzlos als Antwort auf die einzige Frage, die zaehlt: *passiert etwas, wenn ich eine
    Datei hineinlege?* Auf der gemessenen Anlage war die FolderWatch-Erweiterung
    ueberhaupt nicht installiert; Romseerr schrieb korrekte Auftraege in ein korrekt
    eingehaengtes Verzeichnis, und niemand las sie.

    Die Sonde legt eine `.crawljob` ab, die **nichts tun darf** (`enabled`, `autoStart`,
    `autoConfirm` alle `FALSE`) und wartet, ob sie abgeholt wird. JDownloader verschiebt
    eingelesene Dateien nach `folderwatch/added/`; verschwindet sie, liest jemand mit.

    WAS SIE NICHT BEWEIST: dass ein Auftrag auch *laeuft*. Ein modaler Dialog auf der
    JD-Seite (`Default On Added Dupes Links Action` = `ASK`) verschluckt Auftraege,
    nachdem die Datei eingelesen wurde — die Sonde saehe das als Erfolg. Sie beantwortet
    „hoert jemand zu", nicht „geschieht etwas". Fuer Zweiteres braucht es die
    My.JDownloader-API, die hier bewusst nicht vorausgesetzt wird.

    PREIS: Es bleibt ein deaktivierter Eintrag in JDownloaders Linksammler zurueck.
    Deshalb laeuft die Sonde nur auf ausdrueckliche Anforderung, nie im Statusabruf.
    """
    st = jd_check()
    if not st["ok"]:
        return st                                  # Ordnerproblem: das ist die Antwort
    pfad = os.path.join(jd_watch_dir(), "romseerr_probe.crawljob")
    daten = [{"text": "https://example.invalid/romseerr-probe.bin",
              "packageName": "romseerr-probe", "enabled": "FALSE",
              "autoStart": "FALSE", "autoConfirm": "FALSE"}]
    try:
        with open(pfad, "w") as f: json.dump(daten, f)
    except OSError as e:
        return {"ok": False, "reason": "watch_readonly", "info": err_kind(e),
                "fix": f"{jd_watch_dir()} beschreibbar machen / make it writable"}

    ende = time.time() + max(5, wartezeit)
    while time.time() < ende:
        if not os.path.exists(pfad):
            return {"ok": True, "reason": "consumed",
                    "info": f"Auftrag wurde binnen {int(wartezeit)} s abgeholt / "
                            f"picked up within {int(wartezeit)} s"}
        time.sleep(1)

    # Liegen geblieben: aufraeumen, damit die Sonde keine Spur hinterlaesst, die spaeter
    # als echter Auftrag missverstanden wird.
    try: os.remove(pfad)
    except OSError: pass
    return {"ok": False, "reason": "not_consumed",
            "info": f"Auftrag lag nach {int(wartezeit)} s unveraendert da / "
                    f"still untouched after {int(wartezeit)} s",
            "fix": "FolderWatch-Erweiterung in JDownloader installieren und aktivieren "
                   "(Einstellungen → Extension Modules) / install and enable the "
                   "FolderWatch extension in JDownloader"}

def archive_file_urls(ident):
    r = requests.get(f"https://archive.org/metadata/{ident}", timeout=20); m = r.json()
    files = m.get("files",[]); urls=[]
    for fo in files:
        nm = fo.get("name","")
        if SKIP_FILES.search(nm): continue
        ext = nm.rsplit(".",1)[-1].lower() if "." in nm else ""
        if ext in ROM_EXT or ext in ARCH_EXT or fo.get("format","").lower() in ("iso","chd"):
            urls.append(f"https://archive.org/download/{ident}/{urllib.parse.quote(nm)}")
    if not urls:  # zur Not alles außer Metadaten
        for fo in files:
            nm = fo.get("name","")
            if not SKIP_FILES.search(nm):
                urls.append(f"https://archive.org/download/{ident}/{urllib.parse.quote(nm)}")
    return urls

# ---------- Worker: Download starten ----------
def worker_download():
    """Dauerthread: nimmt freigegebene Jobs aus Q und startet den Download je Quelle:
    usenet -> SABnzbd, archive -> aria2 direkt (import direkt danach), filehoster ->
    .crawljob für JDownloader. usenet/filehoster laufen asynchron weiter und werden
    später von worker_collect eingesammelt. Fehler -> state=error."""
    while True:
        beat("download")
        # Mit Timeout warten statt unbegrenzt zu blockieren: sonst sähe ein gesunder,
        # aber unbeschäftigter Worker in den Metriken wie ein hängender aus.
        try:
            jid = Q.get(timeout=30)
        except queue.Empty:
            continue
        job = get_job(jid)
        if not job:
            Q.task_done(); continue
        try:
            if job["source"]=="usenet":
                # HAT SAB DEN AUFTRAG SCHON? (#609) Ein Neustart erklaert laufende
                # Auftraege fuer tot (#336) — SAB laedt sie aber weiter. Ein `retry`
                # uebergab dasselbe NZB danach ein zweites Mal, und niemand fragte nach.
                #
                # Gemessen nach einem Deploy waehrend 13 Downloads: 19 Warteschlangen-
                # eintraege fuer 13 Auftraege, vier Titel doppelt, 115,6 GB offen statt
                # 66. Schlimmer als die doppelte Last ist die Folge davon: SAB haengt bei
                # Namensgleichheit ein `.1` an, und dann gibt es ZWEI Ordner mit demselben
                # Praefix `romseerr_<jid>`. `find_output` nimmt den ersten, den
                # `os.scandir` liefert — im gemessenen Fall waeren das 180 KB statt
                # 853 MB gewesen, und der Auftrag haette Erfolg gemeldet.
                #
                # EN: a restart declares running jobs dead while SAB keeps downloading;
                # retry then queued the same NZB again. Ask SAB first and adopt what is
                # already there.
                schon = sab_hat_auftrag(jid)
                if schon:
                    set_state(jid, state="downloading",
                              msg="läuft bereits in SAB / already in SAB")
                    log(f"Auftrag {jid}: SAB laedt bereits ({schon[:60]}) — "
                        f"nicht erneut uebergeben")
                    # KEIN `Q.task_done()` hier: Wir stehen im `try`, und dessen `finally`
                    # ruft es ohnehin — auch beim `continue`. Zweimal waere ein
                    # `ValueError: task_done() called too many times`, und der traefe den
                    # Arbeitsfaden, nicht diesen Auftrag.
                    continue
                set_state(jid, state="downloading", msg="an SAB übergeben")
                sab_add(job["ref"], dl_name(jid, job.get("title","")))
                # Ordnername in SAB-complete = romseerr_<jid>__<titel> (Präfix romseerr_<jid>)
            elif job["source"]=="archive":
                set_state(jid, state="downloading", msg="Archive.org-Download läuft")
                urls = archive_file_urls(job["ref"])
                if not urls: raise RuntimeError("keine ladbaren Dateien")
                dst = os.path.join(STAGING, f"romseerr_{jid}")
                os.makedirs(dst, exist_ok=True)
                inp = os.path.join(dst, ".urls")
                with open(inp,"w") as f: f.write("\n".join(urls))
                # `check=True` wuerde die nackte CalledProcessError weiterreichen — genau
                # die unlesbare Meldung aus #382. Deshalb den Code selbst auswerten.
                r = subprocess.run(["aria2c","-x8","-s8","-j4","--auto-file-renaming=false",
                                    "--continue=true"] + ia_kopfzeile() + ["-d",dst,"-i",inp],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if r.returncode != 0:
                    raise RuntimeError(aria_fehler(r.returncode))
                os.remove(inp)
                import_folder(jid, dst)
            elif job["source"]=="filehoster":
                # URI-Weiche: direktes HTTP laden wir selbst (kein JDownloader noetig),
                # alles andere geht als .crawljob an JDownloader. (#63)
                links = [u for u in str(job["ref"]).split("\n") if u.strip()]
                if not links: raise RuntimeError("keine Links / no links")
                direct, hoster, _magnet = split_uris(links)
                if direct:
                    set_state(jid, state="downloading", msg="direkter Download läuft")
                    dst = os.path.join(STAGING, f"romseerr_{jid}")
                    os.makedirs(dst, exist_ok=True)
                    inp = os.path.join(dst, ".urls")
                    with open(inp, "w") as f: f.write("\n".join(direct))
                    befehl = ["aria2c","-x8","-s8","-j4","--auto-file-renaming=false",
                              "--continue=true","--max-tries=3","-d",dst,"-i",inp]
                    # Der Proxy gilt fuer ALLE Protokolle (`--all-proxy`), nicht nur http:
                    # Archive.org liefert ueber https, und ein nur fuer http gesetzter
                    # Proxy waere genau der Fall, der aussieht wie Schutz und keiner ist.
                    # All protocols, not just http: archive.org serves over https, and a
                    # proxy set for http alone looks like protection and is none.
                    if cfg("dl_proxy"):
                        befehl += [f"--all-proxy={cfg('dl_proxy')}"]
                    rc = subprocess.run(befehl,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
                    try: os.remove(inp)
                    except OSError: pass
                    if rc != 0:
                        # Linkfaeule ist hier der Normalfall — als klarer Fehler melden,
                        # statt den Job stumm haengen zu lassen.
                        raise RuntimeError("Link tot oder nicht ladbar / link dead or unreachable")
                    import_folder(jid, dst)
                else:
                    set_state(jid, state="downloading", msg="an JDownloader übergeben")
                    dn = dl_name(jid, job.get("title",""))
                    write_crawljob(jid, hoster, f"{cfg("jd_dl_base")}/{dn}", dn)
        except Exception as e:
            set_state(jid, state="error", msg=str(e)[:200]); log(f"Job {jid} Fehler: {e}")
            count_import("failure", "exception")
        finally:
            Q.task_done()

# ---------- Import (entpacken + einsortieren) ----------
def extract_archives(folder):
    """Alle Archive (ARCH_EXT) im Ordner rekursiv mit `unar` entpacken und das Archiv löschen."""
    for root,_,files in os.walk(folder):
        for fn in files:
            ext = fn.rsplit(".",1)[-1].lower() if "." in fn else ""
            if ext in ARCH_EXT:
                fp = os.path.join(root,fn)
                subprocess.run(["unar","-f","-q","-o",root,fp], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                try: os.remove(fp)
                except Exception: pass

# Ordner, die EIN Spiel sind — erkannt an ihrem Aufbau, nicht an einer Dateizahl. (#391)
#
# WOZU: Der Import lief bisher ueber `os.walk` und kopierte jede Datei mit passender
# Endung einzeln. Fuer eine Plattform, deren Titel ein ORDNER ist, ist das in beide
# Richtungen falsch. Gemessen an „MARIO KART 8 wii u uncompressed":
#
#     14 Datei(en) -> 14×wiiu · 170 Nicht-ROM uebersprungen
#
# Die 14 waren `.bin`-Bruchstuecke aus dem Spielinneren, die 170 waren das Spiel — samt
# `code/*.rpx`, ohne die Cemu nichts startet. Bruchstuecke kamen in die Bibliothek, der
# Titel wurde verworfen.
#
# WARUM STRUKTUR UND NICHT DATEIZAHL: Ein entpacktes Wii-U-Spiel hat Tausende Dateien, eine
# Sammlung auch. Was sie unterscheidet, ist ein FESTER Aufbau — `code`+`content`+`meta` ist
# kein Zufall, sondern das Format. Die Bibliothekswerkzeuge treffen dieselbe Unterscheidung
# fuer bereits einsortierte Ordner; hier geht es um die Ankunft.
#
# Recognised by structure, not by file count: an unpacked game and a collection both have
# thousands of files, but the layout is fixed by the format.
SPIELORDNER_MUSTER = [
    # (Slug, benoetigte Eintraege im Ordner) — alle muessen vorhanden sein.
    ("wiiu", {"code", "content", "meta"}),
    ("ps3",  {"ps3_game"}),
    ("ngc",  {"sys", "files"}),          # entpacktes GameCube-/Wii-Abbild
    # PS Vita: der ausgepackte VPK-Aufbau. `eboot.bin` UND `sce_sys` — beides zusammen,
    # denn `eboot.bin` allein hat jeder Vita-Titel, und ein einzelnes Bruchstueck duerfte
    # die Plattform nicht fuer sich beanspruchen. `sce_module`/`PSP2` sind optional und
    # stehen deshalb NICHT hier. Ohne diesen Eintrag nahm der Import nur die `eboot.bin`
    # mit (`.bin` steht in ROM_EXT) und liess den Rest des Titels liegen — und weil jeder
    # Vita-Titel so heisst, ueberschrieb der naechste Import den vorigen. (#455)
    ("psvita", {"eboot.bin", "sce_sys"}),
]
# Einzelne Dateien, die einen Ordner allein zum Spiel machen.
SPIELORDNER_DATEI = {"default.xbe": "xbox", "ps3_disc.sfb": "ps3"}


# Abbildlisten und was sie nennen — fuer die Frage „ist dieser Ordner EIN Titel?". (#477)
#
# WARUM NICHT UEBER `spielordner_slug`: Das liefert einen SLUG, und ein Abbild-Set verraet
# seine Plattform nicht. Eine `.cue` steht bei psx, saturn, segacd und turbografx-cd; eine
# `.gdi` bei dc. Fuer den INDEX ist die Plattform aber schon bekannt — dort lautet die
# Frage nur „ein Titel oder viele?".
_ABBILDLISTE = (".gdi", ".cue", ".m3u")
_CUE_FILE = re.compile(r'^\s*FILE\s+(?:"([^"]+)"|(\S+))', re.I | re.M)


def _abbild_nennt(pfad):
    """Dateinamen, die eine Abbildliste nennt. Leer, wenn unlesbar."""
    endung = os.path.splitext(pfad)[1].lower()
    try:
        with open(pfad, "r", encoding="utf-8", errors="replace") as f:
            text = f.read(200_000)
    except OSError:
        return []
    if endung == ".gdi":
        namen = []
        for zeile in text.splitlines()[1:]:
            teile = zeile.split()
            if len(teile) >= 6:
                namen.append(" ".join(teile[4:-1]).strip('"'))
        return namen
    if endung == ".cue":
        return [(a or b) for a, b in _CUE_FILE.findall(text)]
    return [z.strip() for z in text.splitlines()
            if z.strip() and not z.lstrip().startswith("#")]


def ist_titel_ordner(pfad):
    """-> True, wenn dieser Ordner GENAU EIN Titel ist. (#477)

    Zwei Wege, und der zweite fehlte:

      1. Ein bekannter Aufbau aus `SPIELORDNER_MUSTER` (Wii U, PS3, GameCube, Vita, Xbox).
      2. Ein ABBILD-SET: eine `.gdi`/`.cue`/`.m3u` nennt Dateien, die daneben liegen.

    Ohne den zweiten Weg legt der Index einen Dreamcast-Titel als `track01`, `track02`, …
    ab — dieselbe Sorte Unsinn wie `bootMovie` und `Gravite` vor diesem Fix, nur mit
    anderen Namen. Dass alle Listen auf denselben Titel reduzieren, wird mitgeprueft:
    Zwei verschiedene Spiele in einem Ordner sind eine Sammlung, kein Titel.

    EN: two routes — a known layout, or an image list naming files that sit beside it.
    Without the second, a restored Dreamcast title would be indexed as `track01`, `track02`.
    """
    if spielordner_slug(pfad):
        return True
    try:
        with os.scandir(pfad) as it:          # `with`, sonst bleibt der Deskriptor offen (#589)
            eintraege = [e for e in it if e.is_file()]
    except OSError:
        return False
    listen = [e for e in eintraege
              if os.path.splitext(e.name)[1].lower() in _ABBILDLISTE]
    if not listen:
        return False
    if len({norm(e.name) for e in listen}) != 1:
        return False                      # zwei Titel in einem Ordner = Sammlung
    vorhanden = {e.name.lower() for e in eintraege}
    genannt = []
    for e in listen:
        v = _abbild_nennt(e.path)
        if not v:
            return False                  # unlesbar oder leer — nicht raten
        genannt.extend(v)
    return all(os.path.basename(n).lower() in vorhanden for n in genannt)


def spielordner_slug(pfad):
    """-> Plattform-Slug, wenn dieser Ordner EIN Spiel ist; sonst "".

    Nur die oberste Ebene wird angesehen: Der Aufbau steht dort oder gar nicht.
    """
    try:
        eintraege = {e.lower() for e in os.listdir(pfad)}
    except OSError:
        return ""
    for slug, noetig in SPIELORDNER_MUSTER:
        if noetig <= eintraege:
            return slug
    for datei, slug in SPIELORDNER_DATEI.items():
        if datei in eintraege:
            return slug
    return ""


def spielordner_finden(wurzel, tiefe=2):
    """Alle Spielordner unter `wurzel` -> [(pfad, slug), …].

    Zwei Ebenen tief: Ein Archiv entpackt sich oft in einen Zwischenordner
    (`Mario Kart 8/code/…` oder `Mario Kart 8 (EUR)/Mario Kart 8/code/…`). Tiefer zu suchen
    hiesse, in den Spielinhalt hineinzulaufen — `content/` enthaelt selbst Unterordner.
    """
    gefunden, offen = [], [(wurzel, 0)]
    while offen:
        pfad, ebene = offen.pop(0)
        slug = spielordner_slug(pfad)
        if slug:
            gefunden.append((pfad, slug))
            continue                      # NICHT hineinlaufen: der Inhalt gehoert dazu
        if ebene >= tiefe:
            continue
        try:
            for e in sorted(os.listdir(pfad)):
                q = os.path.join(pfad, e)
                if os.path.isdir(q):
                    offen.append((q, ebene + 1))
        except OSError:
            pass
    return gefunden


def rom_endung(fn):
    """(Endung, Zielname) fuer eine Datei — oder (None, None), wenn es keine ROM ist. (#241)

    Normalfall ist die letzte Endung. Downloadprogramme benennen fertige Dateien aber
    nach geratenem Inhalt um: SABnzbds *deobfuscate final filenames* haengt eine zweite
    Endung an, wenn es den Inhalt zu erkennen glaubt — aus `spiel.nsp` wird `spiel.nsp.hdf`.
    ROM-Formate kennt so ein Rater nicht, deshalb trifft es genau die Dateien, um die es
    hier geht (im Log der laufenden Anlage: .hdf, .sndr, .sfv …).

    Steht vor einem unbekannten Suffix eine bekannte ROM-Endung, gilt die — und der
    angehaengte Suffix faellt beim Kopieren weg, sonst liegt in der Bibliothek ein Name,
    den kein Emulator oeffnet. Nur EINE Ebene tief und nur, wenn die innere Endung
    wirklich in ROM_EXT steht: `spiel.nsp.hdf` ja, `spiel.foo.bar` nein.
    """
    teile = fn.split(".")
    if len(teile) < 2: return None, None
    letzte = teile[-1].lower()
    if letzte in ROM_EXT:
        return letzte, fn
    if len(teile) >= 3:
        vorletzte = teile[-2].lower()
        if vorletzte in ROM_EXT:
            return vorletzte, ".".join(teile[:-1])
    return None, None

# Kennungen, die eine Datei ZWEIFELSFREI ausweisen — Offset -> Bytes -> Endung. (#611)
# Bewusst kurz: Hier steht nur, was eindeutig ist. Raten waere der Fehler aus #607.
INHALT_KENNUNG = ((0, b"PFS0", "nsp"), (0x100, b"HEAD", "xci"))
# Darunter lohnt das Nachsehen nicht — ein Switch-Titel ist nie 40 MB klein, und so
# bleibt der Griff zur Platte auf die Faelle beschraenkt, um die es geht.
INHALT_MINDESTGROESSE = 64 * 1024 * 1024

def rom_endung_aus_inhalt(pfad):
    """Endung aus der DATEIKENNUNG, wenn der Name nichts hergibt. -> Endung oder None. (#611)

    ANLASS, gemessen: Ein 6,2-GB-Release hiess `….hdf` — normalerweise ein
    Amiga-Festplattenabbild, und `hdf` steht nicht in `ROM_EXT`. Die Datei begann mit
    `PFS0`, war also eine tadellose Switch-NSP. Der Import ging daran vorbei und meldete
    „keine ROM-Dateien gefunden", nachdem er 6,2 GB geholt, entpackt und geprueft hatte.
    Umbenennen und erneut einlesen genuegte.

    `rom_endung` deckt den verwandten Fall `spiel.nsp.hdf` schon ab (#241) — dort steht
    die richtige Endung noch im Namen. Hier steht sie nirgends.

    ENG GEFASST, und das ist der Unterschied zu #607: Dort war das Problem, dass
    `libmagic` RAET; hier wird eine einzelne, eindeutige Kennung geprueft. Nur bei
    unbekannter Endung, nur ab 64 MB, nur diese zwei Signaturen.

    Die XCI-Kennung sitzt bei 0x100, HINTER der RSA-Signatur — eine fruehere Pruefung in
    diesem Projekt suchte sie bei 0 und erklaerte acht heile Dateien fuer kaputt.

    EN: derive the extension from the file's magic when the name gives nothing — narrowly:
    unknown extension only, 64 MB minimum, two unambiguous signatures.
    """
    try:
        if os.path.getsize(pfad) < INHALT_MINDESTGROESSE:
            return None
        with open(pfad, "rb") as f:
            for off, magie, ext in INHALT_KENNUNG:
                f.seek(off)
                if f.read(len(magie)) == magie:
                    return ext
    except OSError:
        return None
    return None

def import_folder(jid, folder):
    """Kern der Einsortierung: Archive entpacken, jede Datei einer Plattform zuordnen
    (eindeutige Endung via EXT2PLAT schlägt den Job-Hinweis), **Dedup** gegen die
    Bibliothek, dann nach ROMS/<slug>/ kopieren. Danach Index neu bauen, RomM-Scan
    anstoßen, Job auf `done` setzen und (falls etwas neu ist) Benachrichtigungen
    senden (global, persönlicher Webhook, Web-Push, E-Mail). Staging wird aufgeräumt."""
    job = get_job(jid)
    if not job: return
    set_state(jid, state="importing", msg="entpacken/einsortieren")
    extract_archives(folder)
    job_slug = job.get("platform")
    moved, skipped, by_plat = 0, 0, {}
    copy_errors = 0
    uebergangen = []          # Namen der übersprungenen Dateien, für eine brauchbare Meldung (#242)
    # ZUERST die Spielordner: Was als Ganzes ein Titel ist, wird als Ganzes verschoben —
    # und seine Dateien danach NICHT noch einmal einzeln eingesammelt. (#391)
    ordner_titel = spielordner_finden(folder)
    schon_drin = []
    for quelle, slug in ordner_titel:
        name = os.path.basename(quelle.rstrip("/")) or os.path.basename(folder)
        ziel_ordner = bibliothek_ordner(slug)     # nicht ROMS/<slug> — siehe #454
        os.makedirs(ziel_ordner, exist_ok=True)
        dst = os.path.join(ziel_ordner, name)
        if os.path.exists(dst):
            schon_drin.append(quelle)
            continue
        try:
            # `cp -a` und danach loeschen, nicht `mv`: Staging und Bibliothek liegen auf
            # verschiedenen Dateisystemen, und ein abgebrochenes `mv` hinterliesse dort
            # einen halben Titel. Erst wenn die Kopie steht, ist der Titel da.
            subprocess.run(["cp", "-a", quelle, dst], check=True)
            moved += 1
            by_plat[slug] = by_plat.get(slug, 0) + 1
            schon_drin.append(quelle)
            log(f"Job {jid}: Spielordner {name!r} -> {slug}/")
        except Exception as e:
            log(f"Spielordner-Fehler {name}: {e}"); copy_errors += 1

    def in_spielordner(pfad):
        """Liegt diese Datei INNERHALB eines schon verschobenen Titels?"""
        return any(pfad == q or pfad.startswith(q.rstrip("/") + os.sep)
                   for q in schon_drin)

    for root,_,files in os.walk(folder):
        if in_spielordner(root):
            continue
        for fn in files:
            if SKIP_FILES.search(fn) or fn == ".urls": continue
            src = os.path.join(root,fn)
            # NUR bekannte ROM-/Disk-Endungen importieren. Alles andere (entpackte
            # Fangames, .exe/.dll/.ogg, Emulatoren …) übersprin­gen, statt die
            # Bibliothek zu vermüllen. (#61) — `ziel` kann sich von `fn` unterscheiden,
            # wenn ein Downloadprogramm eine zweite Endung angehängt hat. (#241)
            ext, ziel = rom_endung(fn)
            if not ext:
                # Der Name gibt nichts her — dann in die Datei sehen (#611). Ein Release
                # kann seine NSP `.hdf` nennen; 6,2 GB deswegen liegen zu lassen und
                # „keine ROM-Dateien" zu melden, ist die teuerste Art, recht zu haben.
                ext = rom_endung_aus_inhalt(src)
                if ext:
                    ziel = f"{fn}.{ext}"
                    log(f"{fn}: als .{ext} erkannt (Dateikennung, nicht am Namen)")
            if not ext:
                skipped += 1
                uebergangen.append(fn)
                continue
            # Plattform pro Datei: eindeutige Endung schlägt den Job-Hinweis
            slug = resolve_slug(EXT2PLAT.get(ext) or job_slug)
            # Gegen den Namen pruefen, der TATSAECHLICH in der Bibliothek landet (#613).
            # Mit Praefix verglich diese Zeile gegen etwas, das dort nie steht — und
            # jeder erneute Import galt als neu.
            if in_library(ohne_auftragspraefix(ziel), slug):
                continue  # schon vorhanden -> nicht doppeln
            # Ohne Plattform NICHT raten und schon gar keine erfinden: ab in die Ablage.
            # Sie beginnt mit einem Punkt und ist damit keine Plattform — die Datei ist
            # da, sichtbar, und taucht nirgends als System auf. (#367)
            ordner = slug or UNSORTIERT
            target = os.path.join(ROMS, ordner); os.makedirs(target, exist_ok=True)
            # OHNE UNSEREN AUFTRAGSPRAEFIX (#613) — der ist Buchfuehrung, kein Titel.
            dst = os.path.join(target, ohne_auftragspraefix(ziel))
            if os.path.exists(dst): continue
            try:
                subprocess.run(["cp","-a",src,dst], check=True); moved += 1
                # Gezaehlt wird der ORDNER, nicht der Slug: aus einem leeren Slug wuerde
                # sonst die Meldung „1 Datei(en) → 1×" — eine Zahl ohne Ort. Wer wissen
                # will, wo seine Datei liegt, bekommt hier die einzige Antwort. (#367)
                by_plat[ordner] = by_plat.get(ordner,0)+1
            except Exception as e:
                log(f"move-Fehler {fn}: {e}"); copy_errors += 1
    # Staging aufräumen
    try:
        if folder.startswith(STAGING): subprocess.run(["rm","-rf",folder])
    except Exception: pass
    build_index()
    # NUR DIE BETROFFENEN PLATTFORMEN. Ein voller Lauf ueber 45.000 ROMs fuer eine
    # Handvoll importierter Dateien dauert Stunden und blockiert dabei jeden weiteren
    # Scan.
    #
    # UMRECHNEN, NICHT DURCHREICHEN: `by_plat` traegt Romseerr-SLUGS, RomM erwartet
    # ORDNERNAMEN (`platform_fs_slugs`). Die beiden weichen ab — `dreamcast` liegt in
    # `dc`, `ngc` in `gc`. Ungerechnet liefe der Scan ins Leere und meldete trotzdem
    # Erfolg, also genau der Fehler, den #520 behebt, nur eine Schicht tiefer.
    ordner = sorted({o for sl in by_plat if sl != UNSORTIERT
                     for o in slug_folders(sl)})
    ok, grund = romm_scan(ordner or None)
    if not ok:
        log(f"RomM-Scan nicht ausgeloest: {grund}")
    # Nichts importiert UND nichts war schon vorhanden, aber es lagen Nicht-ROM-Dateien vor
    # -> als Fehler melden (mislabeltes Item ohne echte ROM), statt „done" vorzutäuschen. (#61)
    if moved == 0 and not by_plat and skipped:
        # Die blosse Zahl half niemandem: „1 übersprungen" hat eine ganze Diagnoserunde
        # gekostet, weil weder Datei noch Endung dabeistanden — und der Ordner war zu dem
        # Zeitpunkt schon geloescht. Endungen und ein Beispiel, gedeckelt. (#242)
        endungen = Counter((n.rsplit(".",1)[-1].lower() if "." in n else "—") for n in uebergangen)
        top = ", ".join(f".{e}" for e, _ in endungen.most_common(3))
        beispiel = f" ({uebergangen[0][:60]})" if uebergangen else ""
        detail = f"{skipped} übersprungen: {top}{beispiel}" if top else f"{skipped} übersprungen"
        set_state(jid, state="error",
                  msg=f"keine ROM-Dateien gefunden / no ROM files — {detail}")
        log(f"Job {jid}: keine ROM-Dateien, {detail}")
        count_import("failure", "no_rom_files")
        return False
    where = ", ".join(f"{v}×{k}" for k,v in by_plat.items()) or "nichts (schon vorhanden?)"
    tail = f" · {skipped} Nicht-ROM übersprungen" if skipped else ""
    # Zaehler zuruecksetzen: was einmal geklappt hat, faengt bei einer spaeteren Anfrage
    # nicht mit „3. Versuch" an. (#200)
    set_state(jid, state="done", msg=f"{moved} Datei(en) → {where}{tail}",
              tries=0, tried_sources=[])
    log(f"Job {jid} fertig: {moved} Dateien → {where}{tail}")
    # Genau EIN Ausgang je Import. Nichts kopiert, aber Kopierfehler aufgetreten -> Fehlschlag,
    # auch wenn der Job-Zustand (unverändert) „done" bleibt.
    if moved == 0 and copy_errors: count_import("failure", "copy_failed")
    else: count_import("success")
    if moved:
        notify_available(job.get("title",""), where)
        send_push_to_user(job.get("user",""), "Romseerr",
                          f"🎮 {job.get('title','')} verfügbar / available ({where})")
        wh = load_users().get(job.get("user",""), {}).get("webhook","")
        if wh:
            try: safe_post(wh, json={"content": f"🎮 **{job.get('title','')}** ist jetzt verfügbar / now available ({where})"})
            except Exception as e: log(f"Personal-Notify-Fehler: {e}")
        if load_settings().get("agents", {}).get("email", {}).get("enabled"):
            em = load_users().get(job.get("user",""), {}).get("email","")
            if em: send_mail(em, "Romseerr — verfügbar / available",
                             f"{job.get('title','')} ({where}) ist jetzt verfügbar / is now available.")
    return True

# ---------- Worker: fertige SAB/JD-Downloads einsortieren ----------
def romm_scan(fs_slugs=None):
    """RomM einen Scan anstoßen. -> (ok, grund). Optional auf Ordner begrenzt.

    WAS HIER VORHER STAND UND WARUM ES NIE FUNKTIONIERT HAT (#520): Ein `POST /api/scan`
    mit einem `except Exception` drumherum. Am laufenden RomM gemessen:

        POST /api/login  -> 200
        POST /api/scan   -> 403  "CSRF token verification failed"
        (mit korrektem CSRF-Kopf) -> 404  {"detail":"Not Found"}

    Zwei unabhängige Fehler — und BEIDE unsichtbar, weil `requests` bei 4xx nichts wirft.
    Der `except`-Zweig wurde nie betreten, `log()` schrieb nie eine Zeile, und jeder
    Aufrufer hielt einen Scan für angefordert. Ein Aufruf, der zurückkehrt, erfolgreich
    aussieht und nichts tut.

    DEN SCAN GIBT ES NICHT ALS REST-ENDPUNKT. Er ist ein Socket.IO-Ereignis
    (`@socket_server.on("scan")`), eingehängt unter `/ws`. Die Aufgabe `scan_library`
    trägt `manual_run: false`, `POST /api/tasks/run/scan_library` scheitert also mit 400.

    WARUM POLLING UND KEIN WEBSOCKET: Socket.IO spricht auch reines HTTP — OPEN, CONNECT,
    dann das Ereignis als POST. Damit genügt `requests`, das ohnehin hier ist; ein
    `websockets`- oder `python-socketio`-Paket wäre eine neue Abhängigkeit für einen
    Aufruf, der einmal je Import passiert.

    `fs_slugs` begrenzt den Lauf auf einzelne Ordner. Für ein paar importierte Dateien
    45.000 ROMs anzufassen ist kein Verhältnis — und ein voller Lauf dauert Stunden.

    EN: there is no REST endpoint for the scan; it is a Socket.IO event under `/ws`.
    The previous code posted to a route that returns 403 and then 404, and reported
    neither, because requests does not raise on 4xx. Plain HTTP polling keeps this
    dependency-free.
    """
    if not (cfg("romm_url") and cfg("romm_user") and cfg("romm_pass")):
        return False, "nicht konfiguriert"
    u = cfg("romm_url").rstrip("/")
    basis = f"{u}/ws/socket.io/"
    p = {"EIO": "4", "transport": "polling"}
    try:
        s = requests.Session()
        r = s.post(f"{u}/api/login", auth=(cfg("romm_user"), cfg("romm_pass")), timeout=10)
        # JEDER SCHRITT WIRD GEPRUEFT. Genau das fehlte.
        if not r.ok:
            return False, f"Anmeldung: HTTP {r.status_code}"
        r = s.get(basis, params=p, timeout=15)
        if not r.ok:
            return False, f"Socket-Handschlag: HTTP {r.status_code}"
        m = re.search(r'"sid":"([^"]+)"', r.text or "")
        if not m:
            return False, f"keine Sitzungskennung in der Antwort: {(r.text or '')[:60]}"
        p = dict(p, sid=m.group(1))
        r = s.post(basis, params=p, data="40", timeout=15)
        if not r.ok:
            return False, f"Namensraum: HTTP {r.status_code}"
        s.get(basis, params=p, timeout=15)          # Bestaetigung abholen
        auftrag = {"platforms": [], "type": "quick", "apis": [], "roms_ids": [],
                   "platform_fs_slugs": list(fs_slugs or [])}
        r = s.post(basis, params=p, data="42" + json.dumps(["scan", auftrag]), timeout=15)
        if not r.ok:
            return False, f"Scan-Ereignis: HTTP {r.status_code}"
        # EINE ABSAGE IST KEINE ZUSAGE. RomM weist ab, solange ein Scan-Auftrag wartet —
        # und wartende Auftraege stapeln sich, wenn niemand sie abholt. Ohne dieses
        # Nachlesen sieht die Absage wie ein Erfolg aus, und genau darum geht es hier.
        r = s.get(basis, params=p, timeout=25)
        for teil in (r.text or "").split("\x1e"):
            if teil.startswith("42") and "scan:done_ko" in teil:
                try:
                    grund = json.loads(teil[2:])[1]
                except Exception:
                    grund = teil[:80]
                return False, f"RomM lehnt ab: {grund}"
    except Exception as e:
        log(f"RomM-Scan fehlgeschlagen: {type(e).__name__}: {e}")
        return False, str(e)
    return True, ""

# ---------- Play im Browser: Verweis auf RomMs Spieler (#69) ----------
# RomM bringt EmulatorJS fest eingebaut mit — kein zusaetzlicher Container, kein CDN.
# Romseerr emuliert deshalb NICHTS selbst, sondern loest Titel -> RomM-ROM-ID auf und
# verlinkt in RomMs Spieler. Route dort: /rom/<id>/ejs (belegt im RomM-Router).
#
# Der Knopf erscheint nur, wenn es fuer die Plattform ueberhaupt einen Kern gibt.
# PS2, GameCube, Wii, Dreamcast und Switch haben KEINEN und bekommen auch nie einen —
# das ist eine harte Grenze der WebAssembly-Emulation, kein "noch nicht". Sie duerfen
# den Knopf deshalb niemals zeigen (dafuer gibt es #71).
PLAYABLE = {   # Slug -> EmulatorJS-Kern (nur zur Nachvollziehbarkeit dokumentiert)
    "nes": "fceumm", "snes": "snes9x", "n64": "mupen64plus_next", "gb": "gambatte",
    "gbc": "gambatte", "gba": "mgba", "nds": "melonds", "virtualboy": "beetle_vb",
    "sms": "smsplus", "genesis": "genesis_plus_gx", "segacd": "genesis_plus_gx",
    "sega32x": "picodrive", "gamegear": "genesis_plus_gx", "saturn": "yabause",
    "psx": "mednafen_psx_hw", "psp": "ppsspp", "turbografx16": "mednafen_pce",
    "neogeopocket": "mednafen_ngp", "wonderswan": "mednafen_wswan", "lynx": "handy",
    "jaguar": "virtualjaguar", "atari2600": "stella2014", "atari7800": "prosystem",
    "3do": "opera", "amiga": "puae", "c64": "vice_x64", "dos": "dosbox_pure",
    "arcade": "fbneo", "neogeo": "fbneo", "neo-geo-cd": "fbneo",
    # Heimcomputer und fruehe Konsolen (#124). Die Kernnamen wurden NICHT aus der
    # libretro-Liste abgeschrieben, sondern in der eingesetzten RomM-Fassung
    # nachgesehen — ein Eintrag auf einen Kern, den der Player nicht mitbringt, waere
    # ein Knopf, der nicht funktioniert.
    # Core names were read out of the deployed RomM build rather than copied from
    # libretro's catalogue.
    "c16": "vice_xplus4",              # C16 und Plus/4 teilen sich den Kern
    "vic20": "vice_xvic",
    "colecovision": "gearcoleco",
    "atari5200": "a5200",
    "acpc": "cap32",                   # Amstrad CPC
    "zxs": "fuse",                     # ZX Spectrum
    # Braucht KEINEN neuen Kern: `genesis_plus_gx` laeuft hier ohnehin (Genesis, Mega-CD,
    # Game Gear) und spielt SG-1000 mit. 406 Dateien lagen deshalb ohne Grund still. (#124)
    "sg1000": "genesis_plus_gx",
    # Ebenfalls ohne neuen Kern: `puae` ist fuer den Amiga schon eingetragen und spielt
    # das CD32 mit — es ist dieselbe Maschine mit CD-Laufwerk. Der Kern wurde im
    # eingesetzten RomM-Bau per HEAD nachgesehen, nicht aus libretros Katalog
    # abgeschrieben. 715 Dateien lagen deshalb still. (#193)
    # Same core, no addition: puae already serves the Amiga and plays CD32 as well.
    "amiga-cd32": "puae",
}
# NICHT eingetragen, weil der Player die Kerne nicht mitbringt — nachgesehen, nicht
# vermutet. Gegen die eingesetzte Fassung geprueft (48 Kerne): Vectrex (`vecx`),
# Atari 8-Bit (`atari800`), Atari ST (`hatari`), ScummVM (`scummvm`), Sharp X68000
# (`px68k`) und **Intellivision** (`freeintv`). Letzteres stand hier eingetragen und
# war ein Knopf, der nicht funktionieren konnte: der Kern antwortet mit 404. Genau
# dagegen gibt es jetzt `GET /api/play/cores`. Das ist eine Grenze von RomMs
# EmulatorJS-Bau, keine Entscheidung dieses Projekts.
# Not entered because the player lacks those cores — checked against the deployed build,
# not copied from libretro's catalogue. Intellivision was listed and could not work.
# Plattformen, deren Kern ohne BIOS startet und dann scheitert — der Nutzer soll das
# VORHER lesen, statt vor einer schwarzen Flaeche zu sitzen.
NEEDS_BIOS = {"psx", "3do", "saturn", "amiga", "segacd", "amiga-cd32", "neo-geo-cd"}
# Arcade-Kerne brauchen zum Kern passende Romsets; ein pauschaler Play-Knopf scheitert
# bei den meisten Dumps. Nicht verstecken, aber ehrlich beschriften.
CAVEAT = {"arcade": "romset", "neogeo": "romset"}
PLAY_MAX_BYTES = int(os.environ.get("ROMSEERR_PLAY_MAX_MB", "2048")) * 1024 * 1024

def romm_session():
    """Angemeldete RomM-Sitzung oder None. Fehler sind still — Play ist eine Zugabe."""
    if not (cfg("romm_url") and cfg("romm_user") and cfg("romm_pass")): return None
    try:
        s = requests.Session()
        r = s.post(f"{cfg("romm_url")}/api/login", auth=(cfg("romm_user"), cfg("romm_pass")), timeout=10)
        return s if r.ok else None
    except Exception:
        return None

def romm_find(title, slug=""):
    """Titel -> RomM-Eintrag. Exakter Abgleich des normalisierten Namens; bei mehreren
    gleich guten Treffern wird der erste genommen, aber NUR wenn die Plattform passt."""
    s = romm_session()
    if not s: return None
    try:
        r = s.get(f"{cfg("romm_url")}/api/roms",
                  params={"search_term": clean_query(title)[:80], "limit": 25}, timeout=12)
        if not r.ok: return None
        items = (r.json() or {}).get("items") or []
    except Exception:
        return None
    want = norm(title)
    for it in items:
        if not isinstance(it, dict): continue
        if slug and (it.get("platform_slug") or "") != slug: continue
        for cand in (it.get("name"), it.get("fs_name_no_tags"), it.get("fs_name")):
            if cand and norm(cand) == want:
                return {"id": it.get("id"), "name": it.get("name") or cand,
                        "platform": it.get("platform_slug") or slug,
                        "size": int(it.get("fs_size_bytes") or 0)}
    return None

def play_info(title, slug=""):
    """Kann dieser Titel im Browser gespielt werden — und wenn nein, warum nicht?

    Gibt IMMER einen Grund zurueck. Ein Knopf, der nichts tut, ist schlimmer als keiner."""
    slug = resolve_slug(slug) if slug else ""
    if not cfg("romm_url"):
        return {"playable": False, "reason": "no_romm"}
    if slug and slug not in PLAYABLE:
        # Harte Grenze: fuer diese Plattformen gibt es keinen Kern und wird es keinen geben.
        return {"playable": False, "reason": "no_core", "platform": slug}
    hit = romm_find(title, slug)
    if not hit:
        return {"playable": False, "reason": "not_in_library", "platform": slug}
    plat = hit.get("platform") or slug
    if plat not in PLAYABLE:
        return {"playable": False, "reason": "no_core", "platform": plat}
    if hit["size"] and hit["size"] > PLAY_MAX_BYTES:
        # Grosse Abbilder landen komplett im Browser-Speicher — lieber eine Meldung
        # als ein abstuerzender Tab.
        return {"playable": False, "reason": "too_large", "platform": plat,
                "size": hit["size"], "limit": PLAY_MAX_BYTES}
    return {"playable": True, "platform": plat, "core": PLAYABLE[plat],
            "rom_id": hit["id"], "name": hit["name"],
            "url": f"{cfg("romm_url")}/rom/{hit['id']}/ejs",
            "needs_bios": plat in NEEDS_BIOS, "caveat": CAVEAT.get(plat, "")}

# ---------- Stream: nativ emulierte Plattformen in den Browser (#71) ----------
# EmulatorJS deckt PS2, GameCube, Wii und Switch NICHT ab und wird es nie — dafuer gibt es
# keinen Kern und keiner ist baubar (siehe #69). Fuer diese Plattformen laeuft der Emulator
# server-seitig auf einem Streaming-Host; der Browser bekommt Bild und schickt Eingaben.
#
# Romseerr emuliert nichts, liefert keinen Emulator und keine Firmware aus. Es loest einen
# Titel auf eine Datei auf und bittet den Host, sie zu starten. Mehr nicht.
#
# EINZELPLATZ: mit einer GPU ist das eine Sitzung gleichzeitig. Das muss die Oberflaeche
# klar sagen, statt beim zweiten Versuch zu scheitern.
STREAMABLE = {"psx", "ps2", "ngc", "wii", "wiiu", "switch", "dreamcast", "3ds",
              "xbox", "ps3", "psvita"}

# Ausnahme von der Regel "Browser-Kern ODER Stream, nie beides" (#101).
#
# Die Regel bleibt richtig: zwei Knoepfe fuer dasselbe Spiel sind erklaerungsbeduerftig,
# und fuer die meisten Plattformen gibt es einen klar besseren Weg. Bei PS1 gibt es das
# nicht — beide Wege sind ihre eigene Sache wert:
#   Browser  — sofort, ohne Sitzung, MEHRERE Personen gleichzeitig
#   Stream   — Vollbild und Speicherstaende neben den anderen Konsolen, aber nur EINE
#              Sitzung zur selben Zeit (#137)
# Wer hier eine Plattform eintraegt, trifft diese Entscheidung ausdruecklich; alles,
# was NICHT hier steht, bleibt eine verbotene Ueberschneidung.
#
# EN: deliberate exception to "browser core or stream, never both". For PS1 neither way
# is clearly better, so both are offered. Anything not listed here stays an error.
DUAL_WEG = {"psx"}
# Verzeichnisname je Plattform. Der Umweg ueber diese feste Tabelle ist Absicht: der
# Pfad wird damit aus einer KONSTANTE gebaut, nicht aus der Eingabe. Ein '../'-Versuch
# findet hier schlicht keinen Eintrag, statt bis in os.path.join durchzureichen.
# Grenze fuer eine hochgeladene Firmware-Datei. Sonys PS3-Paket ist mit gut 200 MB der
# groesste reale Fall; darueber hinaus soll niemand den Streaming-Host volllaufen lassen.
FIRMWARE_MAX_BYTES = int(os.environ.get("FIRMWARE_MAX_BYTES", str(512 * 1024 * 1024)))

# Slug -> Ordner, in denen gesucht werden darf. Aus der konstanten Aliastabelle
# abgeleitet, damit weiterhin gilt: nachschlagen statt durchreichen.
STREAM_DIR = {s: slug_folders(s) for s in STREAMABLE}
STREAM_TTL = int(os.environ.get("ROMSEERR_STREAM_TTL", "7200"))   # 2 h, dann faellt der Platz frei
STREAM_LOCK = threading.Lock()

def stream_cfg():
    return {"url": cfg("stream_url"), "launch": cfg("stream_launch")}

# Obere Schranke fuer die Platzsuche. Kein Grenzwert der Anlage, nur ein Anschlag gegen
# eine Endlosschleife, falls jemand `stream_url_999` einträgt.
STREAM_SEATS_MAX = 8


def stream_seats():
    """Eingerichtete Plaetze in fester Reihenfolge -> [{"id", "url", "launch"}, …].

    Platz 1 sind die bisherigen Schluessel `stream_url`/`stream_launch`; fuer eine
    bestehende Einrichtung aendert sich damit nichts. Weitere heissen `stream_url_2`,
    `stream_launch_2` und so fort, und die Suche endet an der ERSTEN Luecke — sonst
    haette ein vergessener `stream_url_5` einen Platz erzeugt, den niemand eingerichtet
    hat und der bei jedem Start ins Leere liefe.
    EN: seat 1 keeps the original keys; the scan stops at the first gap so a stray
    higher-numbered entry cannot conjure a seat nobody configured.
    """
    seats = []
    # Platz 1 ueber `stream_cfg()` und nicht direkt ueber `cfg()`: sonst faellt ein Platz
    # weg, bei dem NUR der Start-Dienst eingerichtet ist (Browser-URL leer) — und das
    # war vor #137 eine gueltige Einrichtung.
    # EN: via stream_cfg so a seat with only a launch service configured still counts.
    eins = stream_cfg()
    if eins["url"] or eins["launch"]:
        seats.append({"id": 1, "url": eins["url"], "launch": eins["launch"]})
    for n in range(2, STREAM_SEATS_MAX + 1):
        u, l = cfg(f"stream_url_{n}"), cfg(f"stream_launch_{n}")
        if not (u or l):
            break
        seats.append({"id": n, "url": u, "launch": l})
    return seats


def stream_sessions():
    """Belegte Plaetze als {"1": sitzung, …}. Abgelaufene fallen von selbst heraus.

    Ein vergessener Browser-Tab darf keinen Platz dauerhaft blockieren — deshalb traegt
    jede Sitzung ihr eigenes Ablaufdatum, und aufgeraeumt wird beim Lesen.

    MIGRATION: Bis #137 gab es genau einen Platz unter dem Schluessel `stream_session`.
    Ein solcher Eintrag wird hier zu Platz 1 — wer waehrend des Updates gerade spielte,
    verliert seinen Platz also nicht.
    EN: sessions expire on their own; a pre-#137 single-seat record becomes seat 1, so
    an update does not evict whoever is playing.
    """
    roh = kv_get("stream_sessions", None)
    if roh is None:
        alt = kv_get("stream_session", None)
        roh = {"1": alt} if alt else {}
        if alt:
            kv_put("stream_sessions", roh)
            kv_put("stream_session", None)
    jetzt = time.time()
    lebend = {str(k): v for k, v in (roh or {}).items()
              if v and jetzt <= float(v.get("expires") or 0)}
    if lebend != (roh or {}):
        kv_put("stream_sessions", lebend)
    return lebend


def stream_session_of(user):
    """-> (platz_id, sitzung) des Nutzers, sonst (None, None)."""
    for sid, ses in stream_sessions().items():
        if ses.get("user") == user:
            return sid, ses
    return None, None


def stream_freier_platz(user):
    """-> Platz fuer diesen Nutzer: sein eigener, sonst der erste freie, sonst None.

    Der eigene Platz zuerst: wer einen zweiten Titel startet, soll seinen Platz
    weiterbenutzen und nicht den zweiten mit belegen.
    EN: reuse the caller's own seat before taking a free one, so starting a second
    title does not occupy both.
    """
    belegt = stream_sessions()
    eigener, _ = stream_session_of(user)
    if eigener:
        return eigener
    for seat in stream_seats():
        if str(seat["id"]) not in belegt:
            return str(seat["id"])
    return None

# Titel-ID einer Switch-Datei, z. B. [010032A01AACA000]. Die letzten drei Stellen sagen,
# WAS die Datei ist: 000 = Basisspiel, 800 = Update, alles andere = DLC.
# Leerzeichen innerhalb der Klammern sind erlaubt: `[ 0100643002136800]` kommt in
# echten Sammlungen vor und waere sonst gar keine Titel-ID — die Datei fiele auf die
# schwaechere Fassungsregel zurueck.
_TITEL_ID = re.compile(r"\[\s*0[0-9a-fA-F]{15}\s*\]")
# Fassungsnummer, z. B. [v0] oder [v131072]. v0 ist die Erstfassung.
_FASSUNG = re.compile(r"\[v(\d+)\]")


def ist_zusatz(name):
    """-> True, wenn die Datei ein Update oder DLC ist und NICHT allein startet.

    WARUM DAS NOETIG IST: Update und Basisspiel tragen denselben Titel und sind nach der
    Normalisierung ununterscheidbar — `A Tale For Anna [..A800][v131072].nsp` (40 MB) und
    `A Tale for Anna [..A000][v0].nsp` (1,1 GB) werden beide zu "a tale for anna". Wer
    das Update erwischt, bekommt im Emulator:

        Error while loading ROM! (0007-003C)

    und ein Fenster, das nur die Oberflaeche zeigt. Von aussen sieht das aus, als koenne
    der Emulator die Plattform nicht — genau als solches lag es als Fehler vor (#174).

    EN: update and base game normalise to the same title, so picking the update yields
    "Error while loading ROM" and a window showing only the emulator UI — which reads
    like the emulator cannot run the platform at all.
    """
    m = _TITEL_ID.search(name)
    if m:
        # Die Titel-ID entscheidet ALLEIN. Frueher fiel eine Basis-ID (`000`) hier
        # durch zur Fassungsregel unten — und eine Basis mit eingespieltem Update
        # traegt eine Fassung > 0, wurde also als Update verworfen. In der Bibliothek
        # nachgemessen: 5 von 484 Dateien, darunter `Crime O'Clock [..DE000][v65536]`.
        # Die ID sagt, WAS die Datei ist; die Fassung sagt nur, wie alt sie ist.
        # EN: the title ID decides on its own — a base ID carrying an applied update has
        # a version > 0 and used to be discarded as an update.
        return not m.group(0).lower().rstrip().rstrip("]").endswith("000")
    v = _FASSUNG.search(name)
    return bool(v and v.group(1) != "0")  # ohne Titel-ID bleibt nur die Fassung


def beste_datei(pfade):
    """-> die Datei, die wirklich startet.

    Zuerst alles aussortieren, was erkennbar Update oder DLC ist. Bleibt danach mehr als
    eines uebrig (etwa eine .xci neben einer .nsp), gewinnt die GROESSTE — das Basisspiel
    ist praktisch immer die groesste Datei seines Titels, und raten muss man hier ohnehin.
    Sortiert wird zusaetzlich nach Namen, damit die Wahl bei gleicher Groesse stabil
    bleibt und nicht von der Reihenfolge im Dateisystem abhaengt.
    EN: drop updates and DLC first, then take the largest remaining file; ties break by
    name so the choice does not depend on directory order.
    """
    echte = [p for p in pfade if not ist_zusatz(os.path.basename(p))] or list(pfade)

    def groesse(p):
        try:
            return os.path.getsize(p)
        except OSError:
            return 0
    return sorted(echte, key=lambda p: (-groesse(p), p))[0]


def stream_find_file(title, slug):
    """Titel -> Datei in der Bibliothek. Ohne Datei kein Stream (dieselbe Regel wie bei Play).

    Der Slug kommt vom Aufrufer und geht in einen Pfad. Er wird deshalb HIER gegen die
    feste Menge geprueft und nicht nur beim Aufrufer — sonst haenge die Sicherheit an der
    Reihenfolge der Pruefungen in stream_info(), und die kann sich aendern."""
    ordner = STREAM_DIR.get(slug)        # Nachschlagen statt Durchreichen
    if not ordner: return None
    want = norm(title)
    if not want: return None
    # Ordner, die zwar so HEISSEN wie der Titel, aber keinen erkennbaren Titelaufbau
    # tragen. Sie bleiben die letzte Antwort — aber erst, wenn keine Datei passt.
    rueckfall = None
    try:
        for name in ordner:
            base = os.path.join(ROMS, name)
            if not os.path.isdir(base): continue
            treffer = []
            # EINE Wanderung fuer Ordner UND Dateien, zwei Ebenen tief — dieselben
            # zwei, die auch der Index laeuft. Vorher waren es zwei getrennte
            # Durchgaenge, und beide hatten je einen Fehler. (#477, nach #150/#478)
            for root, dirs, files in os.walk(base):
                dirs.sort()              # feste Reihenfolge, sonst haengt das Ergebnis
                                         # an der Reihenfolge des Dateisystems
                tief = 0 if root == base else os.path.relpath(root, base).count(os.sep) + 1

                # Ein Titel ist nicht immer eine DATEI. Eine PS3-Disc ist ein Ordner mit
                # PS3_GAME/USRDIR/EBOOT.BIN darin — 10 von 17 Titeln der Testbibliothek.
                # Ohne diesen Zweig meldete jeder PS3-Titel "not_in_library", der Stream-
                # Knopf erschien nie, und der Start-Dienst haette ihn klaglos gestartet:
                # zwei Seiten, die sich widersprechen. (#150; die Dienstseite war #149)
                #
                # ZWEI ERGAENZUNGEN AUS #477, beide am Bestand gemessen (2026-08-13):
                #
                # 1. NUR EIN ORDNER, DER WIRKLICH EIN TITEL IST, schlaegt die Datei.
                #    `ist_titel_ordner` beantwortet genau das seit #478; die Stream-
                #    Suche hat nie gefragt. In `/roms/dc` liegen nebeneinander
                #    `Sonic Adventure.cdi` (757 MB, spielbar) und der Ordner
                #    `Sonic Adventure (PAL)/`, der oben nur eine `.url` und einen
                #    Unterordner traegt. Beide normalisieren gleich, der Ordner gewann,
                #    und der Start-Dienst antwortete darauf `Ordner ohne startbaren
                #    Inhalt` — nachgemessen mit dessen eigenem `_bootdatei`, das ''
                #    liefert. Die Bibliothek hatte den Titel, der Stream nicht.
                #
                # 2. AUCH EINE EBENE TIEFER. Der Index legt Ordner-Titel bis Ebene 2 ab,
                #    die Suche sah nur Ebene 1. `/roms/ps3/DmC Devil May Cry [+All DLC]
                #    BLUS30723/Devil May Cry 5/` ist ein PS3-Titel, steht im Index und
                #    bekam von der Auskunft `not_in_library`.
                #
                # EN: only a folder that really IS a title outranks a playable image,
                # and folder titles are looked for on both levels the index walks.
                for d in dirs:
                    if norm(d) != want: continue
                    voll = os.path.join(root, d)
                    if ist_titel_ordner(voll):
                        return voll
                    if rueckfall is None:
                        rueckfall = voll

                for fn in files:
                    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
                    if ext in ROM_EXT and norm(fn) == want:
                        treffer.append(os.path.join(root, fn))

                # TIEFENBREMSE: `dirs[:] = []` STUTZT den Ast, `break` beendete die
                # GANZE Wanderung — und genau das stand hier. Sobald irgendwo ein
                # Ordner auf Ebene 2 auftauchte, war alles danach unsichtbar. Gemessen:
                # in `/roms/dc` sah die Suche 64 von 173 Dateien (52 der 109
                # uebersehenen waren ROMs), in `/roms/psx` 2925 von 2993. In `gc` und
                # `ps2` liegt nichts auf Ebene 2 — deshalb fiel es dort nie auf.
                # EN: `break` ended the whole walk instead of pruning the branch.
                if tief >= 1:
                    dirs[:] = []
            if treffer:
                return beste_datei(treffer)
    except OSError:
        return None
    return rueckfall

def plattform_kandidaten(title):
    """Alle STREAMBAREN Plattformen, die diesen Titel halten. (#175)

    Dieselbe Abfrage, die `plattform_aus_bibliothek` zu einer Entscheidung verdichtet —
    hier aber vollstaendig, damit eine Absage die Auswahl nennen kann, statt nur
    „mehrdeutig" zu sagen. Bei genau diesem Grund hat der Bedienende die fehlende
    Information, und ihn nicht danach zu fragen ist die eigentliche Luecke.
    """
    n = norm(title)
    if not n:
        return []
    with LIB_LOCK:
        return sorted(s for s in STREAMABLE if n in (LIB["per"].get(s) or set()))

def plattform_aus_bibliothek(title):
    """Welche STREAMBARE Plattform haelt diesen Titel? -> Slug, '' oder '?' (mehrdeutig).

    WOZU: Die Plattform am Suchtreffer ist nicht die des Bestands. Ein Treffer kann
    `Mixed` heissen — ein realer Ordner mit gemischtem Inhalt, keine Plattform —
    waehrend die passende Datei in `ps2/` liegt. Bisher gab stream_info() an dieser
    Stelle auf, und der Nutzer sah keinen Stream-Knopf, obwohl der Titel dalag.
    Der Index weiss laengst, wo er liegt; diese Kenntnis wird jetzt benutzt. (#154)

    The platform on a search hit is not the platform of the copy in the library.
    The index already knows where the file is; use that instead of giving up.
    """
    treffer = plattform_kandidaten(title)
    if len(treffer) == 1:
        return treffer[0]
    # MEHRDEUTIG WIRD NICHT GERATEN. Denselben Titel gibt es fuer PS2 und Wii; das
    # PS2-Abbild zu starten, wenn die Wii-Fassung gemeint war, ist genau die stille
    # Fehlentscheidung, die dieses Projekt vermeidet. Lieber eine Absage mit Grund.
    return "?" if treffer else ""


_3DS_ABBILD = (".3ds", ".cci")
# Kann der Host entschluesseln? Kurz gemerkt (60 s): Die Frage stellt sich bei jedem
# Titelaufruf, die Antwort aendert sich hoechstens nach einem Neustart des Hosts. Ohne
# Zwischenspeicher waere es eine HTTP-Anfrage pro Suchtreffer.
_HOST_KANN = {"wert": None, "bis": 0.0}

def host_kann_entschluesseln():
    """-> True/False. Bei Unerreichbarkeit: False — dann gilt die vorsichtige Antwort.

    WARUM NICHT EINFACH IMMER DURCHLASSEN: Kann der Host es nicht, waere die Zusage eine
    Luege, die erst nach dem Belegen eines Platzes auffliegt — genau der Zustand, den #299
    beseitigt hat. Und warum nicht immer absagen: Dann waere die Faehigkeit umsonst gebaut.
    Deshalb wird gefragt.
    """
    return host_faehigkeiten().get("can_decrypt_3ds", False)


def host_kann_cia_installieren():
    """-> True/False. Ohne Antwort gilt „kann nicht" — aus demselben Grund wie oben. (#315)"""
    return host_faehigkeiten().get("can_install_cia", False)


def host_faehigkeiten():
    """-> dict der gemeldeten Faehigkeiten. Bei Unerreichbarkeit leer, also alles False."""
    if _HOST_KANN["wert"] is not None and time.time() < _HOST_KANN["bis"]:
        return _HOST_KANN["wert"]
    wert = {}
    url = _agent_url("status")
    if url:
        try:
            r = safe_get(url, timeout=6)
            if r.ok:
                antwort = r.json() or {}
                wert = {k: bool(antwort.get(k))
                        for k in ("can_decrypt_3ds", "can_install_cia")}
        except Exception:
            wert = {}
    _HOST_KANN.update({"wert": wert, "bis": time.time() + 60})
    return wert

# Kategorien der 3DS-Titel-ID (obere 32 Bit). Nur diese beiden starten; alles andere ist
# Zubehoer zu einem anderen Titel und startet auch installiert nicht. Am Bestand gemessen:
# von 25 CIAs sind 13 Updates und 2 DLC — bei zweien log der Dateiname, die Titel-ID nie.
_CIA_STARTBAR = {0x00040000, 0x00040002}          # Anwendung, Demo
_CIA_ZUBEHOER = {0x0004000E: "cia_update", 0x0004008C: "cia_dlc"}
_CIA_SIG = {0x00010000: (0x200, 0x3C), 0x00010001: (0x100, 0x3C), 0x00010002: (0x3C, 0x40),
            0x00010003: (0x200, 0x3C), 0x00010004: (0x100, 0x3C), 0x00010005: (0x3C, 0x40)}


def cia_titel_id(pfad):
    """-> (titel_id, fehler). Liest die Titel-ID aus der TMD einer CIA.

    Aufbau: CIA-Kopf, Zertifikatskette, Ticket, TMD — jeder Abschnitt auf 64 Byte
    ausgerichtet. In der TMD folgt hinter Signaturtyp, Signatur und Auffuellung der Kopf mit
    der Titel-ID bei 0x4C.
    """
    import struct
    try:
        with open(pfad, "rb") as f:
            kopf = f.read(0x8000)
    except OSError as e:
        return 0, str(e)
    if len(kopf) < 0x2020:
        return 0, "zu kurz"
    try:
        hs, _t, _v, certs, tickets, _tmds = struct.unpack_from("<IHHIII", kopf, 0)
        aus = lambda n: (n + 63) // 64 * 64
        off = aus(hs) + aus(certs) + aus(tickets)
        sigtyp = struct.unpack_from(">I", kopf, off)[0]
        if sigtyp not in _CIA_SIG:
            return 0, f"unbekannter Signaturtyp 0x{sigtyp:08X}"
        laenge, fuell = _CIA_SIG[sigtyp]
        tmd = off + 4 + laenge + fuell
        if tmd + 0x54 > len(kopf):
            return 0, "TMD ausserhalb des Kopfes"
        return struct.unpack_from(">Q", kopf, tmd + 0x4C)[0], ""
    except (struct.error, IndexError) as e:
        return 0, f"nicht lesbar: {e}"


def _cia_startbar(pfad):
    """-> (startbar, grund) fuer eine `.cia`.

    HIER GILT DAS GEGENTEIL VOM ABBILD: Bei `.3ds` wird im Zweifel durchgelassen, weil ein
    fehlender NCSD-Kopf eine zulaessige Abweichung sein kann. Eine CIA MUSS eine TMD haben —
    ist sie nicht lesbar, ist die Datei kaputt, und der Agent sagt ohnehin ab. Durchlassen
    kostete dann nur den Platz, den #299 gerade eingespart hat.
    """
    titel, fehler = cia_titel_id(pfad)
    if fehler:
        return False, "cia_unreadable"
    kategorie = titel >> 32
    if kategorie in _CIA_ZUBEHOER:
        return False, _CIA_ZUBEHOER[kategorie]
    if kategorie in _CIA_STARTBAR:
        return True, ""
    return False, "cia_not_bootable"


def dreids_art(pfad):
    """-> ".cia", ".3ds" oder "" — was die Datei WIRKLICH ist, unabhaengig vom Namen. (#422)

    Zwei Kennungen, beide am Anfang und beide eindeutig genug, um danach zu handeln:

    - **CIA**: Das erste Feld ist die Kopfgroesse, und die betraegt bei jeder CIA `0x2020`.
      Ein NCSD-Abbild hat an derselben Stelle die ersten Bytes seiner Signatur; dass die
      zufaellig `20 20 00 00` lauten, ist bei 2^32 Moeglichkeiten kein Risiko, das eine
      Fallunterscheidung wert waere.
    - **NCSD**: die Kennung `NCSD` bei 0x100.

    GIBT IM ZWEIFEL "" ZURUECK, nicht eine Vermutung. Der Aufrufer faellt dann auf die
    Endung zurueck — also auf genau das Verhalten von vorher. Eine unlesbare Datei aendert
    damit nichts, statt eine Absage auszuloesen.

    EN: returns what the file actually is. A CIA always starts with header size 0x2020; an
    NCSD image carries `NCSD` at 0x100. Returns "" when neither matches, so the caller falls
    back to the extension — the previous behaviour.
    """
    import struct
    try:
        with open(pfad, "rb") as f:
            kopf = f.read(4)
            f.seek(0x100)
            kennung = f.read(4)
    except OSError:
        return ""
    if len(kopf) == 4 and struct.unpack("<I", kopf)[0] == 0x2020:
        return ".cia"
    if kennung == b"NCSD":
        return ".3ds"
    return ""


# Switch: die letzten drei Stellen der Titel-ID sagen, WAS das Paket ist. (#427)
# `000` Basisspiel, `800` Update, ab `001` aufwaerts Zusatzinhalt. Dasselbe Prinzip wie bei
# den 3DS-Kategorien (#315) — nur an anderer Stelle in der Kennung.
_NSP_ZUBEHOER = {"800": "nsp_update"}


def switch_titel_id(pfad):
    """-> (titel_id_hex, fehler). Liest die Titel-ID AUS DER DATEI, nicht aus dem Namen.

    WARUM NICHT AUS DEM DATEINAMEN: Die Klammer `[0100...000]` ist Szene-Konvention. Sie
    stimmt hier meist, aber eben nur meist — `[Trowzer's Top Tonic Pack]` traegt gar keine,
    und das Wort „DLC" steht mal als `[DLC]`, mal als `[space scout pack dlc]` mitten im
    Namen. Wer danach filtert, filtert die Schreibweise, nicht den Inhalt.

    WIE: Eine NSP ist ein PFS0-Archiv. Darin liegen `<rights-id>.tik` und `.cert`, und die
    ersten 16 Hexzeichen der Rights-ID SIND die Titel-ID. Das steht unverschluesselt im
    Inhaltsverzeichnis — es braucht keine Schluessel, nur den Kopf der Datei.

    Am Bestand gemessen: 387 von 434 Dateien liefern die ID auf diesem Weg. 25 sind XCI
    (anderer Behaelter), 4 haben weder Ticket noch `cnmt.xml`.

    EN: read the title ID from inside the archive. The bracketed ID in the filename is a
    scene convention that usually agrees — usually is not a basis for refusing a launch.
    """
    import struct
    try:
        with open(pfad, "rb") as f:
            kopf = f.read(0x8000)
    except OSError as e:
        return "", str(e)
    if kopf[:4] != b"PFS0":
        return "", "kein PFS0-Archiv"
    try:
        anzahl = struct.unpack_from("<I", kopf, 4)[0]
        if not 0 < anzahl <= 4000:
            return "", "unglaubwuerdige Eintragszahl"
        basis = 0x10 + anzahl * 0x18
        for i in range(anzahl):
            _off, _size, str_off, _r = struct.unpack_from("<QQII", kopf, 0x10 + i * 0x18)
            ende = kopf.index(b"\x00", basis + str_off)
            name = kopf[basis + str_off:ende].decode("utf-8", "replace")
            if name.endswith((".tik", ".cert")) and len(name) > 16:
                return name[:16].lower(), ""
    except (struct.error, ValueError, IndexError) as e:
        return "", f"Inhaltsverzeichnis nicht lesbar ({e.__class__.__name__})"
    return "", "kein Ticket im Archiv"


# Wii U: die ersten acht Hexziffern der Titelkennung sagen, WAS ein Titel ist. (#512)
# Dieselbe Idee wie `_CIA_ZUBEHOER` beim 3DS (`0004000E`) — nur die Konsolenfamilie
# daneben. Sie fehlte, und deshalb bot Romseerr ein Update als startbar an, waehrend der
# Start-Dienst es seit #502 ablehnt: eine Zusage, die die andere Seite nicht haelt.
_WIIU_ZUBEHOER = {"0005000E": "wiiu_update", "0005000C": "wiiu_dlc",
                  "0005001B": "wiiu_system"}


def wiiu_startbar(ordner):
    """-> (startbar, grund) fuer einen Wii-U-Titelordner. (#512)

    GELESEN WIRD `code/app.xml`, NICHT `meta/meta.xml`. Die beiden koennen sich
    widersprechen, und beim einzigen Wii-U-Titel des Bestands tun sie es:

        meta/meta.xml   title_id = 0005000010180700   (behauptet: Basisspiel)
        code/app.xml    title_id = 0005000E10180700   (Update)

    Cemu liest `app.xml` und antwortet darauf `Unable to mount title` — eine Meldung, die
    eine Datei nennt und die Ursache verschweigt. Wer `meta.xml` liest, bekommt mit voller
    Ueberzeugung die falsche Antwort.

    IM ZWEIFEL DURCHLASSEN, wie bei Switch und 3DS: Fehlt `app.xml` oder steht dort keine
    lesbare Kennung, geht der Titel durch. Eine falsche Absage kostet mehr als ein
    Fehlversuch.

    EN: reads `code/app.xml`, not `meta/meta.xml` — the two can disagree, and in the one
    Wii U title here they do. Anything unreadable passes.
    """
    xml = os.path.join(ordner, "code", "app.xml")
    try:
        with open(xml, "r", encoding="utf-8", errors="replace") as f:
            text = f.read(8192)
    except OSError:
        return True, ""
    m = re.search(r"<title_id[^>]*>\s*([0-9A-Fa-f]{16})\s*<", text)
    if not m:
        return True, ""
    grund = _WIIU_ZUBEHOER.get(m.group(1).upper()[:8])
    return (False, grund) if grund else (True, "")


def switch_startbar(pfad):
    """-> (startbar, grund) fuer eine Switch-Datei.

    IM ZWEIFEL DURCHLASSEN — wie bei `.3ds` und aus demselben Grund: Eine falsche Absage
    kostet mehr als ein Fehlversuch. Eine XCI ist ein Cartridge-Abbild und praktisch immer
    ein Basisspiel; ein Archiv ohne Ticket ist schlicht nicht beurteilbar. Beide gehen
    durch.

    Abgewiesen wird nur, was sich EINDEUTIG als Update oder Zusatzinhalt ausweist. Am
    Bestand: 110 Updates und rund 40 DLC unter 434 Dateien — jedes davon war bisher ein
    Startknopf, der einen Platz belegt und ein Bild verspricht, das nicht kommen kann.

    EN: refuse only what identifies itself as an update or add-on; anything unreadable
    passes, because a wrong refusal is the expensive error.
    """
    titel, fehler = switch_titel_id(pfad)
    if fehler or len(titel) != 16:
        return True, ""
    endung = titel[-3:]
    if endung in _NSP_ZUBEHOER:
        return False, _NSP_ZUBEHOER[endung]
    if endung == "000":
        return True, ""
    # Alles zwischen 001 und 7ff ist Zusatzinhalt. Nicht als Liste, weil die Nummern
    # fortlaufend vergeben werden — eine Aufzaehlung waere ab dem naechsten Titel unvollstaendig.
    try:
        n = int(endung, 16)
    except ValueError:
        return True, ""
    return (False, "nsp_dlc") if 0 < n < 0x800 else (True, "")


def dreids_startbar(pfad):
    """-> (startbar, grund) fuer eine 3DS-Datei. Alles andere gilt als startbar. (#299)

    WARUM DAS HIER STEHT UND NICHT NUR IM AGENTEN: Der Agent weist beim Start ab — da hat
    der Nutzer schon geklickt, einen Platz belegt und wartet auf ein Bild, das nie kommt.
    Romseerr hat den Dateipfad und kann dieselbe Frage VORHER beantworten. Die Absage
    gehoert dorthin, wo die Zusage stand.

    WIE: Ein `.3ds`/`.cci` ist ein NCSD-Abbild. Bei 0x100 steht `NCSD`, die erste Partition
    beginnt bei 0x4000 mit `NCCH` bei 0x4100. Ab 0x4188 liegen acht Flag-Bytes; Bit 2 von
    Flag 7 (0x04) ist `NoCrypto` — gesetzt heisst unverschluesselt und damit spielbar.

    Im Zweifel WIRD durchgelassen: Ein Abbild ohne NCSD-Kopf ist nicht beurteilbar, und
    eine falsche Absage ist hier teurer als ein Fehlversuch. Von 1249 gemessenen Abbildern
    war genau eines nicht beurteilbar.

    The agent refuses at launch — by then the user has clicked, taken a seat and is waiting
    for a picture that never comes. Romseerr has the path and can answer the same question
    first. When in doubt it passes: a wrong refusal costs more than a failed attempt.
    """
    # DER INHALT SCHLAEGT DEN NAMEN. (#422)
    #
    # Vorher entschied allein die Endung. In der Bibliothek liegt ein „Save Data Transfer
    # Tool", das `.3ds` heisst und eine CIA IST. Es fiel damit durch die NCSD-Pruefung in den
    # Zweig „nicht beurteilbar, also durchlassen" — und wurde als startbar angeboten. Der
    # Nutzer klickt, belegt einen Platz und wartet auf ein Bild, das nie kommt. Genau das
    # soll diese Funktion verhindern.
    #
    # Die Regel „im Zweifel durchlassen" bleibt richtig und bleibt stehen. Falsch war nur
    # die Annahme, diese Datei sei zweifelhaft: Ihr Inhalt sagt eindeutig, was sie ist, und
    # nur ihr Name luegt. Die Schnueffelei fuegt also Wissen hinzu, keine Absagen — was sich
    # nicht erkennen laesst, geht weiterhin durch.
    #
    # EN: content beats the name. Sniffing adds knowledge, not refusals; anything that
    # identifies as nothing still passes.
    art = dreids_art(pfad) or os.path.splitext(pfad)[1].lower()
    if art == ".cia":
        # Eine CIA startet nie DIREKT, aber sie laesst sich installieren — danach startet
        # der installierte Titel. Was wirklich entscheidet, ist die ART des Pakets, und die
        # steht in der Titel-ID, nicht im Dateinamen. (#315)
        return _cia_startbar(pfad)
    if art not in _3DS_ABBILD:
        return True, ""
    try:
        with open(pfad, "rb") as f:
            f.seek(0x100)
            if f.read(4) != b"NCSD": return True, ""
            f.seek(0x4100)
            if f.read(4) != b"NCCH": return True, ""
            f.seek(0x4188)
            flags = f.read(8)
    except OSError:
        return True, ""
    if len(flags) < 8 or flags[7] & 0x04:
        return True, ""
    return False, "encrypted"

def stream_info(title, slug, user=""):
    """Ist der Titel streambar — und wenn nein, warum nicht? Antwortet immer mit Grund."""
    slug = resolve_slug(slug) if slug else ""
    conf = stream_cfg()
    if not conf["url"]:
        return {"streamable": False, "reason": "no_host"}
    if slug in PLAYABLE:
        # Dafuer gibt es einen Browser-Kern — Stream waere die schlechtere Wahl.
        return {"streamable": False, "reason": "use_play", "platform": slug}
    if slug not in STREAMABLE:
        # Der Treffer nennt keine streambare Plattform. Bevor abgesagt wird: liegt der
        # Titel vielleicht trotzdem in einer? (#154)
        ersatz = plattform_aus_bibliothek(title)
        if ersatz == "?":
            # Die Kandidaten gehoeren in die Antwort: der Resolver kennt sie ohnehin, und
            # ohne sie ist die Absage eine Sackgasse statt einer Frage. (#175)
            return {"streamable": False, "reason": "ambiguous_platform", "platform": slug,
                    "candidates": plattform_kandidaten(title)}
        if not ersatz:
            return {"streamable": False, "reason": "not_supported", "platform": slug}
        slug = ersatz
    path = stream_find_file(title, slug)
    if not path:
        return {"streamable": False, "reason": "not_in_library", "platform": slug}
    entschluesselt_erst = False
    if slug == "switch":
        # Dieselbe Frage wie bei 3DS und aus demselben Grund: Ein Update oder ein DLC
        # startet nicht fuer sich, und das steht VOR der Platzvergabe fest. (#427)
        startbar, grund = switch_startbar(path)
        if not startbar:
            return {"streamable": False, "reason": grund, "platform": slug}
    if slug == "wiiu" and os.path.isdir(path):
        # Dieselbe Frage wie bei Switch und 3DS. Der Start-Dienst lehnt ein Update seit
        # #502 ab — ohne diese Zeile zeigt Romseerr trotzdem den Knopf, und die Absage
        # kommt erst NACH dem Klick. (#512)
        startbar, grund = wiiu_startbar(path)
        if not startbar:
            return {"streamable": False, "reason": grund, "platform": slug}
    if slug == "3ds":
        # Vor der Platzvergabe fragen, nicht danach: Ein belegter Platz fuer einen Titel,
        # der ohnehin nicht startet, nimmt ihn jemandem weg, der spielen koennte. (#299)
        startbar, grund = dreids_startbar(path)
        # Verschluesselt ist KEINE Absage mehr, wenn der Host entschluesseln kann — es
        # dauert dann nur. Der Vermerk reist mit, damit die Oberflaeche die Wartezeit
        # ankuendigen kann; ein stiller Start von mehreren Minuten sieht sonst aus wie
        # ein Haenger, und genau dagegen gibt es #288. (#354)
        if not startbar and grund == "encrypted" and host_kann_entschluesseln():
            entschluesselt_erst = True
            startbar, grund = True, ""
        if startbar and path.lower().endswith(".cia") and not host_kann_cia_installieren():
            # Eine startbare CIA ist nur dann eine Zusage, wenn der Host sie auch
            # installieren kann. Sonst waere es dieselbe Luege wie vor #299 — sie flöge
            # erst auf, nachdem ein Platz belegt ist. (#315)
            startbar, grund = False, "cia_not_bootable"
        elif startbar and path.lower().endswith(".cia"):
            entschluesselt_erst = True     # Installation dauert, das gehoert angekuendigt
        if not startbar:
            return {"streamable": False, "reason": grund, "platform": slug, "path": path}
    # Besetzt ist erst, wenn KEIN Platz mehr frei ist — nicht schon, wenn einer belegt
    # ist. Genau das war die Einschraenkung des Einzelplatzes. (#137)
    platz = stream_freier_platz(user)
    seats = {str(s["id"]): s for s in stream_seats()}
    belegt = stream_sessions()
    if platz is None:
        # Wer blockiert, ist eine Frage der Auskunft, nicht der Logik: bei mehreren
        # Plaetzen wird der zuerst belegte genannt, damit die Meldung stabil bleibt.
        andere = [belegt[k] for k in sorted(belegt)] or [{}]
        return {"streamable": False, "platform": slug, "path": path, "reason": "busy",
                "busy_with": andere[0].get("title", ""),
                "busy_user": andere[0].get("user", ""),
                "seats": len(seats), "seats_free": 0,
                "url": conf["url"]}
    return {"streamable": True, "platform": slug, "path": path, "reason": "",
            "will_decrypt": entschluesselt_erst,
            "busy_with": "", "busy_user": "",
            "seat": platz, "seats": len(seats),
            "seats_free": len(seats) - len(belegt) + (1 if platz in belegt else 0),
            # Die URL des ZUGETEILTEN Platzes, nicht die des ersten: bei zwei Plaetzen
            # sind es zwei verschiedene Adressen, und die falsche fuehrt auf den
            # Desktop eines anderen.
            # EN: the URL of the ASSIGNED seat — the wrong one lands on someone else's desktop.
            "url": (seats.get(platz) or {}).get("url") or conf["url"]}

def stream_start(user, title, slug):
    """Einen Platz belegen und — falls ein Start-Dienst hinterlegt ist — den Titel starten."""
    info = stream_info(title, slug, user)
    if not info.get("streamable"):
        return info, 409 if info.get("reason") == "busy" else 400
    with STREAM_LOCK:
        # Zweite Pruefung IM Lock (Wettlauf): zwischen `stream_info` und hier kann der
        # letzte freie Platz weg sein. Bei einem Einzelplatz war das "ist besetzt?",
        # bei mehreren ist es "ist noch einer frei?" — sonst belegen zwei gleichzeitige
        # Anfragen denselben Platz und der zweite Spieler landet im Bild des ersten.
        # EN: re-check inside the lock; with several seats the question is whether one
        # is still free, otherwise two simultaneous requests take the same seat.
        platz = stream_freier_platz(user)
        if platz is None:
            belegt = stream_sessions()
            andere = [belegt[k] for k in sorted(belegt)] or [{}]
            return {"streamable": False, "reason": "busy",
                    "busy_with": andere[0].get("title", ""),
                    "busy_user": andere[0].get("user", "")}, 409
        seats = {str(s["id"]): s for s in stream_seats()}
        conf = {"url": (seats.get(platz) or {}).get("url") or cfg("stream_url"),
                "launch": (seats.get(platz) or {}).get("launch") or ""}
        launched = False
        fehler = ""
        fehlergrund = ""          # maschinenlesbar, damit die Oberflaeche unterscheiden kann (#177)
        if conf["launch"]:
            try:
                # RELATIV zur Bibliothekswurzel schicken. Ein absoluter Pfad bedeutet
                # im Streaming-Host nicht dasselbe wie hier — haengt er die Bibliothek
                # unter einem anderen Punkt ein, zeigt der Pfad ins Leere, der Start
                # scheitert still, und der Nutzer sieht nur den Desktop. Genau so
                # passiert. Der absolute Pfad geht zur Vertraeglichkeit weiter mit.
                # Send a library-relative path: an absolute one does not mean the same
                # thing on the streaming host, and the launch fails silently.
                rel = os.path.relpath(info["path"], ROMS)
                if rel.startswith(".."): rel = ""     # nicht unterhalb der Wurzel
                # Region aus dem Dateinamen (#77). Sie entscheidet auf dem Host, welches
                # BIOS gewaehlt wird — bei der PS2 ist es regionsgebunden, und ein
                # falsches meldet sich nicht, es laeuft nur "komisch". Ohne erkannte
                # Region wird nichts gesetzt statt geraten.
                # Region drives BIOS selection on the host; nothing is set when unknown.
                regionen = parse_release(os.path.basename(info["path"])).get("regions") or []
                r = safe_post(conf["launch"],
                              json={"rel": rel, "path": info["path"],
                                    "platform": info["platform"],
                                    "region": regionen[0] if regionen else ""}, timeout=15)
                launched = bool(r.ok)
                if not r.ok:
                    try: fehler = str((r.json() or {}).get("msg") or "")[:300]
                    except Exception: fehler = f"HTTP {r.status_code}"
                    # Ein nicht passendes Geheimnis ist ein ANDERER Fehler als ein toter
                    # Host, und beide sahen gleich aus: „Start fehlgeschlagen". Der
                    # Betreiber sucht dann am falschen Ende — der Dienst laeuft ja. 401
                    # ist die einzige Antwort, die der Start-Dienst auf ein falsches
                    # Token gibt, also ist sie hier eindeutig. (#177)
                    if r.status_code == 401:
                        fehlergrund = "bad_token"
                        log("Stream-Start abgelehnt: Token stimmt nicht ueberein (401)")
                    else:
                        log(f"Stream-Start abgelehnt: HTTP {r.status_code} {fehler}")
            except Exception as e:
                fehler = err_kind(e)
                log(f"Stream-Start-Fehler: {e}")
        alle = dict(stream_sessions())
        alle[platz] = {"user": user, "title": title, "platform": info["platform"],
                       "started": int(time.time()), "seat": platz,
                       "expires": time.time() + STREAM_TTL, "launched": launched}
        kv_put("stream_sessions", alle)
    return {"streamable": True, "url": conf["url"], "launched": launched,
            "launch_error": fehler, "launch_reason": fehlergrund,
            "platform": info["platform"], "expires_in": STREAM_TTL,
            "seat": platz, "seats": len(stream_seats())}, 200

def worker_collect():
    """Dauerthread (alle 20 s): sucht für noch laufende usenet/filehoster-Jobs den fertigen
    Ausgabeordner (SAB_DONE bzw. JD_OUT, Name `romseerr_<jid>`). Ist er **stabil** (Größe
    ändert sich nicht mehr), wird import_folder aufgerufen. So werden asynchrone Downloads
    eingesammelt, die worker_download nur angestoßen hat."""
    while True:
        beat("collect")
        try:
            with JOBS_LOCK:
                pending = [dict(j) for j in JOBS if j["state"]=="downloading" and j["source"] in ("usenet","filehoster")]
            sabq = None
            for job in pending:
                jid = job["id"]; pref = f"romseerr_{jid}"
                cand = None
                if job["source"]=="usenet":
                    cand = find_output(SAB_DONE, jid)
                    if not cand:  # noch in der SAB-Queue -> Fortschritt anzeigen
                        if sabq is None: sabq = sab_queue()
                        pct = next((v for k, v in sabq.items() if pref in k), None)
                        if pct not in (None, ""):
                            set_state(jid, msg=f"{pct}%")
                        else:
                            # Weder auf der Platte noch in der Warteschlange: entweder gerade
                            # dazwischen, oder gescheitert. Nur die History weiss es. (#235)
                            grund = sab_failed(jid)
                            if grund:
                                log(f"Job {jid}: SAB gescheitert — {grund}")
                                set_state(jid, state="error", msg=grund)
                                continue
                else:
                    p = find_output(jd_out_dir(), jid)
                    # `with`, sonst bleibt der Deskriptor offen (#589) — `any()` bricht
                    # beim ersten Eintrag ab und laesst den Iterator halb gelesen liegen.
                    if p:
                        with os.scandir(p) as it:
                            if any(it): cand = p
                if cand and folder_stable(cand):
                    einsortieren(jid, job, cand)
        except Exception as e:
            log(f"collect-Fehler: {e}")
        time.sleep(20)

def einsortieren(jid, job, cand):
    """import_folder + Aufraeumen — eine Stelle fuer beide Aufrufer. (#240, #245)

    worker_collect und das erneute Einlesen muessen sich identisch verhalten; laegen die
    Regeln zweimal vor, wuerde eine davon frueher oder spaeter abweichen. Gibt zurueck,
    ob etwas eingelesen wurde.
    """
    erfolg = import_folder(jid, cand)
    # Aufraeumen NUR nach einem geglueckten Import. Vorher lief beides gleich: ein Import,
    # der nichts erkannte, loeschte den Download trotzdem — samt SAB-History mit
    # `del_files=1`. Zwei Gigabyte weg, und die Ursache war hinterher nur noch aus der NZB
    # und dem Log des Downloadprogramms zu rekonstruieren. Was liegen bleibt, kann
    # angesehen und nach einer Korrektur erneut eingelesen werden. (#240)
    if erfolg is False:
        log(f"Job {jid}: Import ohne Treffer — Download bleibt liegen: {cand}")
        return False
    # Erledigten Download aus SAB/JD und von der Platte entfernen. (#65)
    if job.get("source") == "usenet": sab_cleanup(jid)
    try:
        if os.path.isdir(cand) and (cand.startswith(SAB_DONE) or cand.startswith(jd_out_dir())):
            subprocess.run(["rm", "-rf", cand])
    except Exception as e:
        log(f"Ausgabe-Cleanup {jid}: {e}")
    return True

def folder_stable(path, wait=6):
    """True, wenn sich die Gesamtgröße des Ordners über `wait` Sekunden nicht ändert
    (= Download vermutlich abgeschlossen), damit nicht mitten im Schreiben importiert wird."""
    def groesse():
        # `with`, sonst bleibt der Deskriptor offen (#589). In einem Generatorausdruck
        # wiegt das schwerer als sonst: Der Iterator wird erst beim Aufraeumen
        # geschlossen, und diese Funktion laeuft je Auftrag mehrfach.
        with os.scandir(path) as it:
            return sum(f.stat().st_size for f in it if f.is_file())
    try:
        a = groesse()
        time.sleep(wait)
        b = groesse()
        return a==b
    except Exception: return False

# ---------- Benutzerverwaltung / Auth ----------
def load_users():
    try:
        with closing(db_conn()) as c:
            return {u: json.loads(d) for u, d in c.execute("SELECT username,data FROM users")}
    except Exception as e:
        log(f"users-Laden-Fehler: {e}"); return {}
class KeinAdminMehr(RuntimeError):
    """Der Schreibvorgang wuerde eine Instanz hinterlassen, in die niemand mehr hineinkommt."""

def _hat_admin(u):
    """Mindestens ein Konto mit Adminrolle UND gesetztem Passwort. (#234)"""
    return any((v or {}).get("role") == "admin" and str((v or {}).get("pw") or "").strip()
               for v in (u or {}).values())

def save_users(u):
    """Die Benutzerliste ERSETZEN — mit der Sperre, die bisher nur der Import kannte. (#234)

    Diese Funktion ist ein Ersetzer, kein Ergaenzer: sie leert die Tabelle und schreibt das
    uebergebene Dict als Gesamtbestand. Die Bedingung „mindestens ein Admin mit Passwort"
    stand deshalb an genau einer Stelle richtig — im Import — und an keiner anderen. Ueber
    die Benutzerverwaltung, ein Rechte-Formular oder einen Wartungsaufruf war eine Instanz
    erreichbar, in der sich niemand mehr anmelden kann und die sich auch nicht mehr
    reparieren laesst.

    Eine **leere** Liste ist ausdruecklich erlaubt: dann greift `api_setup`, und der erste
    Admin wird neu angelegt — das sperrt niemanden aus. Verboten ist der Zustand dazwischen:
    Konten vorhanden, aber keines, das noch hineinkommt.
    """
    if u and not _hat_admin(u):
        raise KeinAdminMehr("kein Admin mit Passwort / no admin with a password")
    try:
        vorher = len(load_users())
        with DB_LOCK, closing(db_conn()) as c, c:
            c.execute("DELETE FROM users")
            c.executemany("INSERT INTO users(username,data) VALUES(?,?)",
                          [(k, json.dumps(v)) for k, v in u.items()])
        # Jede Verkleinerung protokollieren. Die Invariante oben verhindert das Aussperren,
        # nicht das versehentliche Ueberschreiben mit einem gueltigen, aber falschen Bestand
        # — und ein solcher Vorfall soll wenigstens nachweisbar sein, statt lautlos zu
        # passieren.
        if vorher > len(u):
            log(f"Benutzerliste verkleinert: {vorher} -> {len(u)} "
                f"({', '.join(sorted(u)) or 'leer'})")
    except Exception as e:
        log(f"users-Speichern-Fehler: {e}")
def speichere_nutzer_http(users):
    """save_users fuer HTTP-Handler: die Invariante wird zur 400, nicht zum Serverfehler.

    Gibt eine fertige Antwort zurueck, wenn der Schreibvorgang abgelehnt wurde, sonst None.
    Ohne das waere aus einer sauberen Sperre ein 500er geworden — technisch sicher, aber
    fuer den Bedienenden ununterscheidbar von einem Absturz. (#234)
    """
    try:
        save_users(users); return None
    except KeinAdminMehr:
        return jsonify({"ok": False,
                        "msg": "es muss ein Admin mit Passwort bleiben / "
                               "one admin with a password must remain"}), 400

def load_settings():
    return kv_get("settings", {})
def save_settings(s):
    kv_put("settings", s)
def may_autoapprove(username):
    usr = load_users().get(username, {})
    return usr.get("role") == "admin" or "autoapprove" in (usr.get("perms") or []) or bool(usr.get("autoapprove"))

def mail_log_add(to, subject, ok, err=""):
    try:
        entries = kv_get("maillog", [])
        entries.insert(0, {"ts": datetime.now().strftime("%Y-%m-%d %H:%M"), "to": to,
                           "subject": subject, "ok": bool(ok), "err": (err or "")[:120]})
        kv_put("maillog", entries[:100])
    except Exception: pass

def send_mail(to, subject, body):
    s = load_settings().get("smtp", {})
    if not (s.get("enabled") and s.get("host") and to): return False
    try:
        msg = EmailMessage()
        msg["From"] = s.get("from") or s.get("user") or "romseerr@localhost"
        msg["To"] = to; msg["Subject"] = subject; msg.set_content(body)
        port = int(s.get("port") or 587); mode = s.get("tls", "starttls")
        srv = smtplib.SMTP_SSL(s["host"], port, timeout=15) if (mode == "ssl" or port == 465) \
              else smtplib.SMTP(s["host"], port, timeout=15)
        if not (mode == "ssl" or port == 465) and mode != "none": srv.starttls()
        if s.get("user"): srv.login(s["user"], s.get("pass", ""))
        srv.send_message(msg); srv.quit(); mail_log_add(to, subject, True); return True
    except Exception as e:
        log(f"Mail-Fehler: {e}"); mail_log_add(to, subject, False, str(e)); return False

# ---------- Web-Push (VAPID) ----------
VAPID_CACHE = {}
def ensure_vapid():
    """VAPID-Schlüsselpaar laden/erzeugen; gibt {'priv_pem','pub_b64'} oder None."""
    if not PUSH_OK: return None
    if VAPID_CACHE: return VAPID_CACHE
    try:
        d = json.load(open(VAPID_FILE))
        geheim_absichern(VAPID_FILE)      # Altbestand nachziehen (#192)
        VAPID_CACHE.update(d); return VAPID_CACHE
    except Exception: pass
    try:
        v = Vapid(); v.generate_keys()
        priv_pem = v.private_pem().decode()
        raw = v.public_key.public_bytes(serialization.Encoding.X962,
                                        serialization.PublicFormat.UncompressedPoint)
        pub_b64 = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
        d = {"priv_pem": priv_pem, "pub_b64": pub_b64}
        schreibe_geheim(VAPID_FILE, json.dumps(d)); VAPID_CACHE.update(d)
        log("VAPID-Schlüssel erzeugt")
        return VAPID_CACHE
    except Exception as e:
        log(f"VAPID-Fehler: {e}"); return None

def load_push():
    return kv_get("push", {})
def save_push(d):
    kv_put("push", d)

def send_push_to_user(user, title, body):
    """Web-Push an alle Abos eines Nutzers senden (VAPID). Abgelaufene Abos (404/410) werden
    verworfen. No-op, wenn pywebpush fehlt oder kein Abo existiert."""
    if not PUSH_OK or not user: return
    vp = ensure_vapid()
    if not vp: return
    subs = load_push().get(user, []); keep = []
    for s in subs:
        try:
            webpush(subscription_info=s, data=json.dumps({"title": title, "body": body}),
                    vapid_private_key=vp["priv_pem"], vapid_claims={"sub": "mailto:romseerr@localhost"})
            keep.append(s)
        except WebPushException as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 410): pass   # Abo abgelaufen -> verwerfen
            else: keep.append(s); log(f"Push-Fehler: {e}")
        except Exception as e:
            keep.append(s); log(f"Push-Fehler: {e}")
    if len(keep) != len(subs):
        d = load_push(); d[user] = keep; save_push(d)

# Passwort-Reset-Token (nur im RAM, 1 h gültig). gen_reset erzeugt, check_reset prüft/löst auf.
RESET_TOKENS = {}
def gen_reset(user):
    """Einmal-Token für „Passwort vergessen" erzeugen (1 h gültig, nur im RAM)."""
    tok = secrets.token_urlsafe(24); RESET_TOKENS[tok] = {"user": user, "exp": time.time()+3600}; return tok
def check_reset(tok):
    """Reset-Token -> Benutzername, falls gültig und nicht abgelaufen; sonst None."""
    d = RESET_TOKENS.get(tok)
    return d["user"] if d and d["exp"] > time.time() else None
_SECRET_CACHE = []

def app_secret():
    """Signaturschlüssel für die Flask-Session (secret.key). Beim ersten Mal erzeugt & gespeichert.

    EIN NICHT GESPEICHERTER SCHLUESSEL DARF NICHT SCHWEIGEN (#587): Vorher verschwand das
    Scheitern von `schreibe_geheim` in einem `except Exception: pass`. Laesst sich das
    Konfigverzeichnis nicht beschreiben, entsteht dann bei JEDEM Start ein anderer
    Schluessel — und weil er die Flask-Session signiert, sind damit bei jedem Neustart alle
    Anmeldungen ungueltig. Von aussen sieht das nach einem Sitzungsfehler aus, nicht nach
    einem Rechteproblem, und in `romseerr.log` stand dazu nichts.

    Dass `log()` hier trotzdem ankommt, ist kein Zufall: Es schreibt ZUERST auf stdout und
    nur den Dateianteil bedingt — im selben Fehlerfall waere das Protokoll ja auch nicht
    schreibbar. Die Meldung steht damit im Container-Protokoll.

    Dieselbe Lage behandelt `ensure_vapid()` seit jeher richtig (Meldung auf beiden Wegen,
    Wert im Prozess stabil ueber `VAPID_CACHE`), und `storage_state()` gibt es genau
    deshalb (#216). Diese Funktion war die einzige der Art ohne beides.

    EN: a session key that cannot be persisted is no longer discarded in silence — every
    restart would otherwise mint a new one and log everybody out, with nothing in the log.
    """
    try:
        wert = open(SECRET_FILE).read().strip()
        geheim_absichern(SECRET_FILE)
        return wert
    except Exception:
        pass
    # IM PROZESS STABIL BLEIBEN, wie `VAPID_CACHE` es tut. Heute ruft nur
    # `app.secret_key = app_secret()` einmal auf; ein zweiter Aufrufer bekaeme sonst einen
    # anderen Schluessel und entwertete die Sitzungen des ersten.
    if _SECRET_CACHE:
        return _SECRET_CACHE[0]
    s = secrets.token_hex(32)
    try:
        schreibe_geheim(SECRET_FILE, s)
        # AUCH DER GUTFALL WIRD GEMELDET. Beim ersten Start ist ein neuer Schluessel
        # normal; taucht die Zeile spaeter wieder auf, ist die Datei verschwunden — und
        # genau dann will man wissen, wann.
        log(f"Neuer Sitzungsschluessel erzeugt und gespeichert: "
            f"{os.path.basename(SECRET_FILE)}")
    except Exception as e:
        log(f"Sitzungsschluessel konnte NICHT gespeichert werden ({SECRET_FILE}): "
            f"{e.__class__.__name__}: {e} — bis das behoben ist, meldet jeder Neustart "
            f"alle Benutzer ab.")
    _SECRET_CACHE.append(s)
    return s
# Decorators zum Schutz von Routen. Alle akzeptieren auch den API-Key (g.api_auth, s. _guard).
def login_required(f):
    """Route nur für angemeldete Nutzer (oder gültigen API-Key). API -> 401, sonst Redirect /login."""
    @wraps(f)
    def w(*a, **k):
        if g.get("api_auth") or session.get("user"): return f(*a, **k)
        if request.path.startswith("/api/"): return jsonify({"error": "auth"}), 401
        return redirect("/login")
    return w
def admin_required(f):
    """Route nur für Admins (oder API-Key). Sonst 403."""
    @wraps(f)
    def w(*a, **k):
        if g.get("api_auth") or session.get("role") == "admin": return f(*a, **k)
        return jsonify({"error": "admin"}), 403
    return w
def get_apikey():
    """Aktuellen API-Key aus den Einstellungen holen; beim ersten Mal einen erzeugen."""
    s = load_settings(); k = s.get("apikey")
    if not k:
        k = secrets.token_hex(16); s["apikey"] = k; save_settings(s)
    return k

# Granulare Rechte (Admin hat implizit ALLE). Werden je Benutzer in dessen `perms`-Liste gespeichert
# und über has_perm()/den perm_required-Decorator geprüft.
PERMS = ["request", "autoapprove", "manage_requests", "manage_users", "manage_issues",
         "manage_settings", "quota_exempt"]
# Privilegierte Rechte: nur ein echter Admin darf sie vergeben/entziehen (sonst könnte
# sich ein Nutzer mit manage_users zum Admin hochstufen). Ebenso Rollenwechsel.
PRIV_PERMS = {"manage_users", "manage_settings"}
def caller_is_admin():
    return bool(g.get("api_auth")) or session.get("role") == "admin"
# Gültige Oberflächensprachen und -Designs (Design = Look, per Nutzer/global wählbar).
LANGS = ("de", "en", "fr", "es", "it")
DESIGNS = ("seerr", "glass", "clean")
def has_perm(perm, user=None):
    """Hat der Nutzer (Default: der aktuelle) das Recht? API-Key und Admin -> immer True."""
    if g.get("api_auth"): return True
    usr = load_users().get(user or session.get("user"), {})
    if usr.get("role") == "admin": return True
    return perm in (usr.get("perms") or [])
def perm_required(perm):
    """Decorator-Fabrik: Route nur, wenn der Nutzer `perm` hat (Admin/API-Key immer). Sonst 403."""
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if has_perm(perm): return f(*a, **k)
            return jsonify({"error": "forbidden", "need": perm}), 403
        return w
    return deco

# ---------- Web-UI ----------
# Das Frontend liegt in templates/*.html und static/{css,js}/ — kein Build-Schritt, aber auch
# kein eingebettetes HTML/CSS/JS mehr in dieser Datei. Übersetzt wird über das JS-Objekt I18N
# + t() (static/js/index.js); Ansichten werden per show() umgeschaltet.
app = Flask(__name__, static_folder=None)   # eigene, inhaltsgehashte Auslieferung (serve_asset)
app.secret_key = app_secret()
app.config["PERMANENT_SESSION_LIFETIME"] = 60*60*24*30
# Cookie-Härtung: HttpOnly (kein JS-Zugriff) + SameSite=Strict (CSRF-Schutz, da alle
# API-Aufrufe same-origin sind). Secure nur setzen, wenn hinter HTTPS betrieben
# (ROMSEERR_HTTPS=1) — sonst würde das Cookie über reines HTTP im LAN nicht gesetzt.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("ROMSEERR_HTTPS", "") == "1"

# ---------- Frontend: Vorlagen + statische Dateien (#73) ----------
# HTML/CSS/JS liegen NICHT mehr als Python-Strings hier drin, sondern in templates/ und
# static/. Drei Dinge waren dadurch blockiert: Browser-Caching (eingebettetes CSS/JS wird bei
# jedem Seitenaufruf neu übertragen), eine CSP ohne `unsafe-inline`, und jede Arbeit an der
# Oberfläche selbst.
#
# Nebeneffekt, der eine ganze Fehlerklasse beseitigt: In einem Python-String wurde jeder
# Backslash-Escape des eingebetteten JavaScripts von PYTHON interpretiert — aus join('\n')
# wurde ein echter Zeilenumbruch und damit ein unterminiertes JS-Literal, das das gesamte
# Skript lahmlegte. In einer .js-Datei kann das nicht mehr passieren.
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TPL_DIR    = os.path.join(BASE_DIR, "templates")
ASSET_RE   = re.compile(r"__ASSET:([A-Za-z0-9._/-]+)__")
# WARUM `.json` HIER STEHT: Ohne Eintrag faellt eine Datei auf `application/octet-stream`
# zurueck — und damit aus der Vorkomprimierung heraus, die nur Text-Typen packt. Die
# Sprachdateien (#350) gingen so mit 17 KB statt rund 4 KB ueber die Leitung, und der
# Inhaltstyp war obendrein falsch. Aufgefallen erst beim Nachmessen am laufenden Dienst;
# die Behauptung, es sei abgedeckt, war ungeprueft.
# Without an entry a file falls back to octet-stream and drops out of the pre-compression,
# which only packs text types.
ASSET_MIME = {".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8",
              ".svg": "image/svg+xml", ".png": "image/png", ".webmanifest": "application/manifest+json",
              ".json": "application/json; charset=utf-8"}
_ASSETS    = {}   # "css/index.css" -> {"hash","body","mime"}
_TPL_CACHE = {}

def load_assets():
    """Alle Dateien unter static/ einlesen und inhaltlich hashen. Einmal beim Start —
    die Dateien liegen im Image und ändern sich zur Laufzeit nicht."""
    import hashlib
    _ASSETS.clear()
    for root, _dirs, files in os.walk(STATIC_DIR):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, STATIC_DIR).replace(os.sep, "/")
            try:
                with open(full, "rb") as f: body = f.read()
            except OSError as e:
                log(f"Asset-Lesefehler {rel}: {e}"); continue
            ext = os.path.splitext(fn)[1].lower()
            mime = ASSET_MIME.get(ext, "application/octet-stream")
            _ASSETS[rel] = {"hash": hashlib.sha256(body).hexdigest()[:12], "body": body,
                            "mime": mime, "gz": _gzip_wenn_lohnend(body, mime)}
    return len(_ASSETS)

# Ab welcher Groesse lohnt Komprimierung? Darunter kostet der gzip-Kopf mehr, als der
# Inhalt spart. 1 KiB ist die uebliche Grenze.
GZIP_MIN = 1024

def _gzip_wenn_lohnend(body, mime):
    """Vorkomprimierte Fassung — oder None, wenn sie nichts bringt. (#323)

    WARUM BEIM LADEN UND NICHT JE ANFRAGE: Die Dateien liegen im Image und aendern sich
    zur Laufzeit nicht. Einmal komprimieren kostet beim Start Millisekunden; je Anfrage zu
    komprimieren kostet dieselbe Arbeit immer wieder fuer dasselbe Ergebnis.

    WARUM MTIME=0: Ohne das traegt der gzip-Kopf einen Zeitstempel, und dieselbe Datei
    ergaebe bei jedem Start andere Bytes. Das ist bei inhaltsgehashten URLs unschoen und
    macht Vergleiche im Test unmoeglich.

    WARUM NICHT ALLES: Bilder, Schriften und wasm sind bereits komprimiert; sie durch gzip
    zu schicken macht sie im Zweifel groesser. Deshalb nur Text, und nur wenn das Ergebnis
    tatsaechlich kleiner ist — gemessen, nicht angenommen.

    Compressed once at load: the files ship in the image and never change at runtime.
    mtime=0 keeps the bytes stable across restarts. Only text, and only when the result is
    actually smaller — measured, not assumed.
    """
    if len(body) < GZIP_MIN:
        return None
    # Der MIME-Typ traegt Parameter (`application/javascript; charset=utf-8`). Ein
    # Vergleich auf Gleichheit geht daran vorbei — und zwar lautlos: `text/css` kam ueber
    # das Praefix trotzdem durch, `application/javascript` nicht. Genau das grosse Buendel,
    # um das es hier geht, blieb dadurch unkomprimiert.
    # The MIME type carries parameters; comparing for equality silently missed exactly the
    # large bundle this is about, while text/* slipped through via the prefix.
    typ = mime.split(";")[0].strip().lower()
    if not (typ.startswith("text/") or typ in (
            "application/javascript", "application/json", "image/svg+xml",
            "application/manifest+json", "application/xml")):
        return None
    import gzip as _gzip, io
    puffer = io.BytesIO()
    with _gzip.GzipFile(fileobj=puffer, mode="wb", compresslevel=9, mtime=0) as f:
        f.write(body)
    gz = puffer.getvalue()
    return gz if len(gz) < len(body) else None

def asset_url(rel):
    """Inhaltsgehashte URL. Der Hash steht im PFAD (nicht als Query), damit die Antwort
    `immutable` sein darf: eine geänderte Datei bekommt eine andere URL, statt dass ein
    Proxy raten muss, ob sein Zwischenspeicher noch stimmt."""
    a = _ASSETS.get(rel)
    return f"/assets/{a['hash']}/{rel}" if a else f"/assets/dev/{rel}"

def render_page(name):
    """Vorlage lesen und die __ASSET:…__-Platzhalter durch gehashte URLs ersetzen.
    Bewusst KEINE Template-Engine: die Dateien stecken voller JS-Template-Literale
    (`${…}`) und CSS-Klammern, die eine Engine falsch deuten könnte."""
    if name in _TPL_CACHE: return _TPL_CACHE[name]
    with open(os.path.join(TPL_DIR, name), encoding="utf-8") as f:
        html = f.read()
    html = ASSET_RE.sub(lambda m: asset_url(m.group(1)), html)
    _TPL_CACHE[name] = html
    return html

@app.route("/assets/<h>/<path:rel>")
def serve_asset(h, rel):
    """Statische Datei unter ihrer gehashten URL. Nur mit passendem Hash — eine URL mit
    falschem Hash darf nicht dieselbe Datei ausliefern, sonst wäre `immutable` gelogen."""
    a = _ASSETS.get(rel)
    if not a or a["hash"] != h:
        return Response("not found", status=404, mimetype="text/plain")
    kopf = {"Cache-Control": "public, max-age=31536000, immutable"}
    # `Vary: Accept-Encoding` ist Pflicht, sobald zwei Fassungen unter DERSELBEN URL
    # ausgeliefert werden: Ohne den Kopf reicht ein Proxy die gepackte Fassung an einen
    # Client weiter, der kein gzip kann. Zusammen mit `immutable` waere das ein Jahr lang
    # kaputt. / Two representations under one URL require Vary; with immutable, getting
    # this wrong would be broken for a year.
    kopf["Vary"] = "Accept-Encoding"
    if a["gz"] and "gzip" in request.headers.get("Accept-Encoding", ""):
        kopf["Content-Encoding"] = "gzip"
        return Response(a["gz"], mimetype=a["mime"], headers=kopf)
    return Response(a["body"], mimetype=a["mime"], headers=kopf)

load_assets()   # beim Import, damit auch Tests und der WSGI-Betrieb ohne __main__ funktionieren





@app.route("/")
@login_required
def index(): return Response(render_page("index.html"), mimetype="text/html")

@app.route("/api/search")
@login_required
def api_search():
    q = request.args.get("q","").strip()
    if not q: return jsonify([])
    plats = [p for p in request.args.get("platforms","").split(",") if p]
    res = do_search(q, plats)
    if request.args.get("achievements") == "1":
        res = [r for r in res if ra_has_set(r.get("title", ""), r.get("platform", ""))]
    return jsonify(res)

@app.route("/api/platforms")
def api_platforms():
    return jsonify([{"group":g, "items":[{"slug":s,"name":n,"usenet":bool(SLUG2USE.get(s))}
                    for s,n in items]} for g,items in PLATFORMS])

# Fortschritt eines laufenden Katalogabrufs (nur ein Lauf gleichzeitig)
COVERAGE_BUILD = {"running": False, "done": 0, "total": 0, "current": ""}

@app.route("/api/coverage")
def api_coverage():
    """Abdeckung je Plattform. Jede Zahl trägt Quelle und Stand — eine nackte Prozentzahl
    wäre hier irreführend, weil Metadatensätze sich uneins sind, was ein eigener Titel ist."""
    return jsonify({"platforms": coverage_overview(), "source": CATALOG_SOURCE,
                    "max_per_platform": CATALOG_MAX, "building": bool(COVERAGE_BUILD["running"])})

@app.route("/api/coverage/refresh", methods=["POST"])
@perm_required("manage_settings")
def api_coverage_refresh():
    """Momentaufnahme(n) neu holen. Läuft im Hintergrund — ein Katalogabruf sind je
    Plattform mehrere IGDB-Seiten, das gehört nicht in einen Request."""
    d = request.get_json(silent=True) or {}
    only = (d.get("slug") or "").strip()
    slugs = [only] if only else [s for s in IGDB_PLAT if s in SLUG_NAME]
    if only and only not in IGDB_PLAT:
        return jsonify({"ok": False, "msg": f"keine Katalogquelle für '{only}' / no catalogue source"}), 400
    if not igdb_token():
        return jsonify({"ok": False, "msg": "IGDB nicht konfiguriert / not configured"}), 400
    with COVERAGE_LOCK:
        if COVERAGE_BUILD["running"]:
            return jsonify({"ok": False, "msg": "läuft bereits / already running"}), 409
        COVERAGE_BUILD.update({"running": True, "done": 0, "total": len(slugs), "current": ""})

    def run():
        try:
            cov = load_coverage()
            for slug in slugs:
                COVERAGE_BUILD["current"] = slug
                n = fetch_catalog(slug)
                if n:
                    cov = load_coverage()
                    cov.setdefault(slug, {})["snapshot"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    save_coverage(cov)
                    log(f"Katalog {slug}: {n} Titel ({CATALOG_SOURCE})")
                else:
                    log(f"Katalog {slug}: keine Daten — keine Momentaufnahme geschrieben")
                COVERAGE_BUILD["done"] += 1
            refresh_coverage_counts()
        except Exception as e:
            log(f"Katalog-Lauf-Fehler: {e}")
        finally:
            COVERAGE_BUILD.update({"running": False, "current": ""})
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True, "platforms": len(slugs)})

RA_BUILD = {"running": False, "done": 0, "total": 0, "current": ""}

@app.route("/api/catalog/status")
def api_catalog_status():
    """Stand der Filehoster-Katalogquellen: Name, Anzahl, Abrufzeitpunkt, Fehler.
    Der Stand gehört sichtbar hin — Katalogquellen veralten schnell (Linkfäule). (#63)"""
    meta = kv_get("catalog_meta", {})
    try:
        with closing(db_conn()) as c:
            total = c.execute("SELECT COUNT(*) FROM fh_items").fetchone()[0]
    except Exception:
        total = 0
    jd = jd_check()
    return jsonify({"sources": [{"url": u, **{k: v for k, v in (meta.get(u) or {}).items() if k != "ts"}}
                                for u in catalog_urls()],
                    "configured": len(catalog_urls()), "items": total, "ttl": CATALOG_TTL,
                    "jd": {"ok": jd["ok"], "info": jd["info"]}})

@app.route("/api/catalog/refresh", methods=["POST"])
@perm_required("manage_settings")
def api_catalog_refresh():
    if not catalog_urls():
        return jsonify({"ok": False, "msg": "keine Katalogquelle hinterlegt / no catalogue source"}), 400
    with CATALOG_LOCK:
        threading.Thread(target=lambda: refresh_catalogs(force=True), daemon=True).start()
    return jsonify({"ok": True, "sources": len(catalog_urls())})

@app.route("/api/ra/status")
def api_ra_status():
    """Stand der RetroAchievements-Zuordnung: welche Plattformen indiziert sind, wie viele
    Sets, und welche Slugs sich NICHT auf eine RA-Konsole abbilden ließen."""
    try:
        with closing(db_conn()) as c:
            per = dict(c.execute("SELECT slug, COUNT(*) FROM ra_games GROUP BY slug"))
    except Exception:
        per = {}
    meta = kv_get("ra_meta", {})
    return jsonify({"enabled": bool(ra_key()), "platforms": per, "total": sum(per.values()),
                    "snapshot": meta.get("snapshot", ""), "unmapped": meta.get("unmapped", []),
                    "build": dict(RA_BUILD)})

@app.route("/api/ra/refresh", methods=["POST"])
@perm_required("manage_settings")
def api_ra_refresh():
    """Set-Listen neu holen. Hintergrundlauf — je Konsole eine Abfrage, das dauert."""
    if not ra_key():
        return jsonify({"ok": False, "msg": "kein RetroAchievements-Key hinterlegt / no API key"}), 400
    with RA_LOCK:
        if RA_BUILD["running"]:
            return jsonify({"ok": False, "msg": "läuft bereits / already running"}), 409
        RA_BUILD.update({"running": True, "done": 0, "total": 0, "current": ""})

    def run():
        try:
            consoles = ra_consoles()
            unmapped = [s for s in RA_ALIASES if s not in consoles]
            if unmapped: log(f"RA: keine Konsolen-Zuordnung für {', '.join(sorted(unmapped))}")
            RA_BUILD["total"] = len(consoles)
            for slug, cid in consoles.items():
                RA_BUILD["current"] = slug
                n = ra_fetch_console(slug, cid)
                log(f"RA {slug} (Konsole {cid}): {n if n else 'keine Daten'}")
                RA_BUILD["done"] += 1
            kv_put("ra_meta", {"snapshot": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "unmapped": sorted(unmapped)})
        except Exception as e:
            log(f"RA-Lauf-Fehler: {e}")
        finally:
            RA_BUILD.update({"running": False, "current": ""})
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True})

@app.route("/api/coverage/status")
def api_coverage_status():
    return jsonify(dict(COVERAGE_BUILD))

@app.route("/api/coverage/<slug>/missing")
def api_coverage_missing(slug):
    """Die FEHLENDEN Titel — das ist die Liste, mit der man etwas anfangen kann."""
    try:
        offset = max(0, int(request.args.get("offset", 0) or 0))
        limit = min(500, max(1, int(request.args.get("limit", 100) or 100)))
    except ValueError:
        offset, limit = 0, 100
    d = missing_titles(slug, offset, limit, (request.args.get("q") or "").strip()[:60])
    e = load_coverage().get(slug, {})
    return jsonify({**d, "slug": slug, "offset": offset, "limit": limit,
                    "source": e.get("source", ""), "snapshot": e.get("snapshot", "")})

@app.route("/api/library/platforms")
@login_required
def api_library_platforms():
    """Die eigene Bibliothek, nach Hersteller und System gruppiert. (#293, #322)

    ORDNUNG: `LIB_VENDORS`, NICHT `PLATFORMS`. Die beiden Listen haben verschiedene
    Aufgaben — die Begruendung steht bei `LIB_VENDORS`. Kurz: Mit der Filterliste landeten
    74 % aller Titel in „Sonstige" oder in einer Gruppe ohne Namen.

    Plattformen OHNE Katalogquelle erscheinen hier ebenfalls: was man besitzt, weiss
    Romseerr auch ohne IGDB, und sie hinter einer nicht berechenbaren Prozentzahl
    verschwinden zu lassen waere der Fehler, den die Abdeckungsseite gerade vermeidet.

    Grouped by LIB_VENDORS rather than by the search filter's PLATFORMS; with the latter
    74 % of titles ended up in a catch-all or a nameless group.
    """
    with LIB_LOCK:
        per = {s: len(v) for s, v in (LIB["per"] or {}).items()}

    def eintrag(slug, anzahl):
        return {"slug": slug, "name": SLUG_NAME.get(slug, slug), "owned": anzahl}

    gruppen = []
    zugeordnet = set()
    for hersteller, slugs in LIB_VENDORS:
        systeme = [eintrag(sl, per[sl]) for sl in slugs if per.get(sl)]
        if not systeme:
            continue
        zugeordnet.update(x["slug"] for x in systeme)
        # Innerhalb einer Gruppe nach Titelzahl: Wer die Bibliothek ansieht, sucht zuerst
        # das grosse Regal. Alphabetisch waere die Reihenfolge zwar stabiler, aber sie
        # stellt `3do` mit 39 Titeln vor `c64` mit 24.021.
        systeme.sort(key=lambda x: -x["owned"])
        gruppen.append({"vendor": hersteller,
                        "owned": sum(x["owned"] for x in systeme),
                        "platforms": systeme})
    # Gruppen nach Groesse, damit die Ansicht oben beginnt, wo am meisten steht.
    gruppen.sort(key=lambda g: -g["owned"])

    # Alles, was in keiner Gruppe steht. Frueher trug diese Gruppe einen Gedankenstrich
    # als Ueberschrift — und darunter lag `scummvm` mit 16.487 Titeln. Sie heisst jetzt
    # und steht ausdruecklich am Ende, nicht nach Groesse einsortiert: Sie ist ein
    # Auffangbecken, kein Hersteller.
    rest = [eintrag(sl, n) for sl, n in sorted(per.items()) if n and sl not in zugeordnet]
    if rest:
        rest.sort(key=lambda x: -x["owned"])
        gruppen.append({"vendor": LIB_REST, "rest": True,
                        "owned": sum(x["owned"] for x in rest), "platforms": rest})
    return jsonify({"vendors": gruppen, "total": sum(per.values())})

@app.route("/api/library/<slug>/titles")
def api_library_titles(slug):
    """Die vorhandenen Titel einer Plattform — das Gegenstueck zu `…/missing`. (#293)"""
    try:
        offset = max(0, int(request.args.get("offset", 0) or 0))
        limit = min(500, max(1, int(request.args.get("limit", 100) or 100)))
    except ValueError:
        offset, limit = 0, 100
    d = owned_titles(slug, offset, limit, (request.args.get("q") or "").strip()[:60])
    return jsonify({**d, "slug": slug, "name": SLUG_NAME.get(slug, slug),
                    "offset": offset, "limit": limit})


@app.route("/api/detail")
def api_detail():
    source = request.args.get("source",""); ref = request.args.get("ref",""); title = request.args.get("title","")
    rich = igdb_rich(title) if title else {}
    out = {"description": rich.get("summary","") or "", "files": [], "name": rich.get("name","") or "",
           "rating": rich.get("rating"), "year": rich.get("year",""), "developer": rich.get("developer",""),
           "genres": rich.get("genres", []), "screenshots": rich.get("screenshots", []), "similar": rich.get("similar", []),
           "series": rich.get("series", ""), "series_games": rich.get("series_games", [])}
    # RetroAchievements: rein additiv. Kein Set, kein Key, kein Dienst -> Abschnitt faellt weg,
    # es erscheint KEIN Fehler. (#79)
    ra = ra_lookup(title, request.args.get("platform", "")) if title else None
    if ra:
        out["achievements"] = ra
        me = load_users().get(session.get("user", ""), {}).get("ra_user", "")
        if me:
            prog = ra_user_progress(me, ra["id"])
            if prog: out["achievements"]["progress"] = prog
    if source == "archive" and ref:
        try:
            m = requests.get(f"https://archive.org/metadata/{ref}", timeout=15).json()
            fs = []
            for fo in m.get("files", []):
                nm = fo.get("name","")
                if SKIP_FILES.search(nm): continue
                fs.append({"name": nm, "size": int(fo.get("size") or 0)})
            out["files"] = sorted(fs, key=lambda x:-x["size"])[:60]
        except Exception as e:
            log(f"Archive-Detail {ref}: {e}"); out["error"] = err_kind(e)
    return jsonify(out)

@app.route("/api/play")
@perm_required("request")
def api_play():
    """Kann der Titel im Browser gespielt werden? Antwortet immer mit einem Grund."""
    title = (request.args.get("title") or "").strip()
    if not title: return jsonify({"playable": False, "reason": "no_title"}), 400
    return jsonify(play_info(title, (request.args.get("platform") or "").strip()))

@app.route("/api/stream")
@perm_required("request")
def api_stream_info():
    """Ist der Titel streambar? Antwortet immer mit einem Grund."""
    title = (request.args.get("title") or "").strip()
    if not title: return jsonify({"streamable": False, "reason": "no_title"}), 400
    return jsonify(stream_info(title, (request.args.get("platform") or "").strip(),
                               session.get("user", "")))

@app.route("/api/stream/start", methods=["POST"])
@perm_required("request")
def api_stream_start():
    d = request.get_json(silent=True) or {}
    title = (d.get("title") or "").strip()
    if not title: return jsonify({"streamable": False, "reason": "no_title"}), 400
    out, code = stream_start(session.get("user", ""), title, (d.get("platform") or "").strip())
    return jsonify(out), code

@app.route("/api/stream/stop", methods=["POST"])
@perm_required("request")
def api_stream_stop():
    """Platz freigeben. Nur der Inhaber oder ein Anfragen-Verwalter — sonst koennte
    jeder jedem die laufende Sitzung abdrehen."""
    me = session.get("user", "")
    # Ohne Platzangabe der eigene; Verwalter duerfen einen fremden ausdruecklich nennen.
    # Frueher gab es nur einen, deshalb war "welchen?" keine Frage — jetzt schon, und
    # ein Verwalter, der ohne Angabe beendet, soll NICHT zufaellig einen fremden treffen.
    # EN: without an explicit seat, stop your own; a manager must name a foreign one.
    gewuenscht = (request.args.get("seat") or "").strip()
    sitzungen = stream_sessions()
    if gewuenscht:
        if gewuenscht not in sitzungen:
            return jsonify({"ok": True, "was_running": False})
        sid, ses = gewuenscht, sitzungen[gewuenscht]
    else:
        sid, ses = stream_session_of(me)
    if not ses:
        return jsonify({"ok": True, "was_running": False})
    if ses.get("user") != me and not has_perm("manage_requests"):
        return jsonify({"ok": False, "msg": "fremde Sitzung / not your session"}), 403
    rest = {k: v for k, v in sitzungen.items() if k != sid}
    kv_put("stream_sessions", rest)
    return jsonify({"ok": True, "was_running": True, "seat": sid})

def _agent_url(pfad):
    """Der Start-Dienst hat mehrere Endpunkte unter derselben Wurzel; in den
    Einstellungen steht die /launch-Adresse samt Token. Beides wird hier getrennt,
    statt den Betreiber vier URLs eintragen zu lassen."""
    launch = stream_cfg()["launch"]
    if not launch: return None
    basis = launch.split("?")[0].rsplit("/", 1)[0]
    q = launch.split("?", 1)[1] if "?" in launch else ""
    return f"{basis}/{pfad}" + (("?" + q) if q else "")

@app.route("/api/stream/emulators/catalog")
@perm_required("manage_settings")
def api_stream_catalog():
    """Was kann der Streaming-Host installieren, was ist installiert? Eine frische
    Installation hat NICHTS — der Betreiber waehlt hier aus, statt dass beim ersten
    Start ungefragt hunderte Megabyte geladen werden."""
    url = _agent_url("catalog")
    if not url: return jsonify({"ok": False, "reason": "no_launcher"}), 400
    try:
        r = safe_get(url, timeout=130)
        return jsonify({"ok": r.ok, **(r.json() if r.ok else {})}), (200 if r.ok else 502)
    except Exception as e:
        log(f"Stream-Katalog: {e}")
        return jsonify({"ok": False, "reason": err_kind(e)}), 502

@app.route("/api/stream/emulators/install", methods=["POST"])
@perm_required("manage_settings")
def api_stream_install():
    """Einen Emulator auf dem Streaming-Host installieren."""
    url = _agent_url("install")
    if not url: return jsonify({"ok": False, "reason": "no_launcher"}), 400
    name = ((request.get_json(silent=True) or {}).get("name") or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", name):
        return jsonify({"ok": False, "reason": "bad_name"}), 400
    try:
        r = safe_post(url, json={"name": name}, timeout=30)
        if r.status_code == 409: return jsonify({"ok": False, "reason": "already_running"}), 409
        if r.status_code == 404: return jsonify({"ok": False, "reason": "unknown"}), 404
        return jsonify({"ok": r.ok}), (200 if r.ok else 502)
    except Exception as e:
        log(f"Stream-Installation: {e}")
        return jsonify({"ok": False, "reason": err_kind(e)}), 502

# ------------------------------------------------------- Firmware und BIOS (#107)

@app.route("/api/stream/firmware")
@perm_required("manage_settings")
def api_stream_firmware():
    """Welche Plattform braucht Firmware, ist sie da, sieht sie heil aus? Die Antwort
    kommt vom Streaming-Host — Romseerr hat die Dateien nicht und soll nicht raten."""
    url = _agent_url("firmware")
    if not url: return jsonify({"ok": False, "reason": "no_launcher"}), 400
    try:
        r = safe_request("get", url, timeout=30)
        return jsonify(r.json() if r.ok else {"ok": False, "reason": "agent"}), (200 if r.ok else 502)
    except Exception as e:
        log(f"Firmware-Status: {e}")
        return jsonify({"ok": False, "reason": err_kind(e)}), 502


@app.route("/api/stream/firmware/upload", methods=["POST"])
@perm_required("manage_settings")
def api_stream_firmware_upload():
    """Eine BIOS-/Firmware-Datei zum Streaming-Host durchreichen.

    Romseerr speichert sie NICHT und legt sie nirgends ab: sie geht durch, und was
    hier bleibt, ist nichts. Das ist keine Bequemlichkeit, sondern Absicht — die
    Dateien gehoeren dem Betreiber, und ein zweiter Aufbewahrungsort waere ein
    zweiter Ort, an dem sie verloren gehen oder auftauchen koennen.

    Passed through to the streaming host; Romseerr stores nothing."""
    url = _agent_url("firmware/upload")
    if not url: return jsonify({"ok": False, "reason": "no_launcher"}), 400
    datei = request.files.get("file")
    if not datei or not datei.filename:
        return jsonify({"ok": False, "reason": "no_file"}), 400
    plattform = (request.form.get("platform") or "").strip()
    # Der Name darf vom Betreiber kommen (manche Emulatoren erwarten genau einen),
    # sonst nehmen wir den der hochgeladenen Datei.
    name = (request.form.get("name") or "").strip() or os.path.basename(datei.filename)
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", plattform):
        return jsonify({"ok": False, "reason": "bad_platform"}), 400
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
        return jsonify({"ok": False, "reason": "bad_name"}), 400
    try:
        roh = datei.read(FIRMWARE_MAX_BYTES + 1)
        if len(roh) > FIRMWARE_MAX_BYTES:
            return jsonify({"ok": False, "reason": "too_large",
                            "limit": FIRMWARE_MAX_BYTES}), 413
        r = safe_post(f"{url}{'&' if '?' in url else '?'}"
                      f"platform={urllib.parse.quote(plattform)}&name={urllib.parse.quote(name)}",
                      data=roh, headers={"Content-Type": "application/octet-stream"},
                      timeout=300)
        return jsonify(r.json() if r.content else {"ok": r.ok}), (200 if r.ok else 400)
    except Exception as e:
        log(f"Firmware-Upload: {e}")
        return jsonify({"ok": False, "reason": err_kind(e)}), 502


@app.route("/api/stream/firmware/vendor", methods=["POST"])
@perm_required("manage_settings")
def api_stream_firmware_vendor():
    """Firmware beim Hersteller holen. Gibt es nur fuer die PS3: Sony veroeffentlicht
    seine Systemsoftware selbst. Fuer alles andere existiert keine berechtigte Quelle,
    und dieses Projekt baut keine."""
    url = _agent_url("firmware/vendor")
    if not url: return jsonify({"ok": False, "reason": "no_launcher"}), 400
    plattform = ((request.get_json(silent=True) or {}).get("platform") or "").strip()
    if plattform != "ps3":
        return jsonify({"ok": False, "reason": "no_vendor_source"}), 400
    try:
        r = safe_post(f"{url}{'&' if '?' in url else '?'}platform=ps3", timeout=30)
        if r.status_code == 409: return jsonify({"ok": False, "reason": "already_running"}), 409
        return jsonify({"ok": r.ok}), (200 if r.ok else 502)
    except Exception as e:
        log(f"Firmware vom Hersteller: {e}")
        return jsonify({"ok": False, "reason": err_kind(e)}), 502


@app.route("/api/stream/emulators")
@perm_required("manage_settings")
def api_stream_emulators():
    """Welche Emulatoren liegen auf dem Streaming-Host, aus welcher Quelle, und
    laeuft gerade eine Aktualisierung? Fragt den Start-Dienst — Romseerr weiss das
    nicht selbst und soll es auch nicht raten."""
    conf = stream_cfg()
    if not conf["launch"]:
        return jsonify({"ok": False, "reason": "no_launcher"}), 400
    # Der Start-Dienst hat /update neben /launch; die URL wird entsprechend abgeleitet.
    url = conf["launch"].split("?")[0].rsplit("/", 1)[0] + "/update"
    q = conf["launch"].split("?", 1)[1] if "?" in conf["launch"] else ""
    try:
        r = safe_get(url + (("?" + q) if q else ""), timeout=15)
        return jsonify({"ok": r.ok, **(r.json() if r.ok else {})}), (200 if r.ok else 502)
    except Exception as e:
        log(f"Stream-Emulatoren: {e}")
        return jsonify({"ok": False, "reason": err_kind(e)}), 502

@app.route("/api/stream/emulators/update", methods=["POST"])
@perm_required("manage_settings")
def api_stream_emulators_update():
    """Aktualisierung der Emulatoren auf dem Streaming-Host anstossen.

    Ohne `name` laufen alle, mit `name` genau einer (#338). Einzeln ist der Normalfall:
    Ein Sammellauf laedt hunderte Megabyte fuer Emulatoren, die niemand benutzt, und wer
    eine Regression sucht, will genau einen Schritt tun koennen.

    Der Lauf dauert Minuten, deshalb antwortet der Dienst sofort; der Fortschritt kommt
    ueber /api/stream/emulators.

    Without `name` all emulators run, with `name` exactly one.
    """
    conf = stream_cfg()
    if not conf["launch"]:
        return jsonify({"ok": False, "reason": "no_launcher"}), 400
    name = ((request.get_json(silent=True) or {}).get("name") or "").strip()
    if name and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}", name):
        return jsonify({"ok": False, "reason": "bad_name"}), 400
    url = conf["launch"].split("?")[0].rsplit("/", 1)[0] + "/update"
    q = conf["launch"].split("?", 1)[1] if "?" in conf["launch"] else ""
    if name:
        q = (q + "&" if q else "") + "name=" + urllib.parse.quote(name)
    try:
        r = safe_post(url + (("?" + q) if q else ""), timeout=20)
        if r.status_code == 409:
            return jsonify({"ok": False, "reason": "already_running"}), 409
        return jsonify({"ok": r.ok}), (200 if r.ok else 502)
    except Exception as e:
        log(f"Stream-Emulator-Update: {e}")
        return jsonify({"ok": False, "reason": err_kind(e)}), 502

@app.route("/api/stream/emulators/rollback", methods=["POST"])
@perm_required("manage_settings")
def api_stream_emulators_rollback():
    """Einen Emulator auf die vorige Fassung zuruecksetzen. Ein Update kann eine
    Regression bringen — dann soll der Rueckweg ein Klick sein und keine Suche."""
    conf = stream_cfg()
    if not conf["launch"]:
        return jsonify({"ok": False, "reason": "no_launcher"}), 400
    name = ((request.get_json(silent=True) or {}).get("name") or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", name):
        return jsonify({"ok": False, "reason": "bad_name"}), 400
    url = conf["launch"].split("?")[0].rsplit("/", 1)[0] + "/rollback"
    q = conf["launch"].split("?", 1)[1] if "?" in conf["launch"] else ""
    try:
        r = safe_post(url + (("?" + q) if q else ""), json={"name": name}, timeout=120)
        return jsonify({"ok": r.ok, **(r.json() if r.ok else {})}), (200 if r.ok else 502)
    except Exception as e:
        log(f"Stream-Emulator-Rueckkehr: {e}")
        return jsonify({"ok": False, "reason": err_kind(e)}), 502

@app.route("/api/stream/status")
@perm_required("request")
def api_stream_status():
    conf = stream_cfg()
    seats = stream_seats()
    sitzungen = stream_sessions()
    me = session.get("user", "")
    _, meine = stream_session_of(me)
    felder = ("user", "title", "platform", "started", "launched")
    return jsonify({"configured": bool(seats), "has_launcher": bool(conf["launch"]),
                    "seats": len(seats), "seats_free": max(0, len(seats) - len(sitzungen)),
                    "ttl": STREAM_TTL,
                    # `session` bleibt die EIGENE Sitzung — die Oberflaeche fragt damit
                    # "laeuft bei mir etwas?", und das darf sich durch fremde Plaetze
                    # nicht aendern. Alle Plaetze stehen daneben in `sessions`.
                    # EN: `session` stays the caller's own, so the UI question
                    # "am I playing?" keeps its meaning; all seats are listed separately.
                    "session": {k: meine[k] for k in felder} if meine else None,
                    "sessions": {sid: {k: s[k] for k in felder}
                                 for sid, s in sitzungen.items()}})

# ---------- Logos: mitgebracht wird KEINES (#211/#199) ----------
# ENTSCHIEDEN und hier festgehalten, damit es nicht beim naechsten Anlauf neu verhandelt
# wird: Konsolen- und Herstellerlogos sind **Marken**. In einer privaten Instanz zu zeigen
# ist eine Sache, die Dateien in ein OEFFENTLICHES Repository zu legen eine andere — und
# dieses Repo ist oeffentlich. Deshalb:
#
#   * ausgeliefert wird ausschliesslich, was der BETREIBER selbst in `<config>/logos`
#     ablegt. Im Repo liegt kein einziges Bild.
#   * ohne Dateien bleibt es bei der Typografie („GameCube" statt `ngc`), die nachweislich
#     funktioniert. Das Layout muss ohne Logo vollstaendig sein, nicht nur ertraeglich.
#
# Dateiname = Plattform-Slug (`snes.png`) oder Herstellergruppe kleingeschrieben
# (`nintendo.svg`). Erlaubt sind png/svg/webp/jpg.
LOGO_DIR = os.path.join(CONFIG_DIR, "logos")
LOGO_EXT = {".png": "image/png", ".svg": "image/svg+xml",
            ".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
_LOGO_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

def logo_dateien():
    """{name: dateiname} der vorhandenen Logos. Nur brave Namen — der Ordner gehoert dem
    Betreiber, aber der Name kommt gleich aus einer URL zurueck."""
    out = {}
    try:
        for f in sorted(os.listdir(LOGO_DIR)):
            stamm, ext = os.path.splitext(f)
            if ext.lower() in LOGO_EXT and _LOGO_NAME.match(stamm.lower()):
                out.setdefault(stamm.lower(), f)
    except OSError:
        pass
    return out

@app.route("/api/logos")
def api_logos():
    """Welche Logos liegen bereit? Die Oberflaeche fragt einmal und weiss dann, wo sie ein
    Bild statt des Namens zeigen kann — statt je Karte einen 404 zu erzeugen."""
    return jsonify(sorted(logo_dateien().keys()))

@app.route("/logo/<name>")
def logo(name):
    """Ein Logo ausliefern. `name` wird NICHT als Pfad benutzt, sondern gegen die zuvor
    eingelesene Liste geprueft — sonst waere `..%2f..%2fsecret.key` eine Datei."""
    datei = logo_dateien().get(str(name).lower())
    if not datei:
        return Response("not found", status=404, mimetype="text/plain")
    pfad = os.path.join(LOGO_DIR, datei)
    try:
        with open(pfad, "rb") as f: body = f.read()
    except OSError:
        return Response("not found", status=404, mimetype="text/plain")
    mime = LOGO_EXT.get(os.path.splitext(datei)[1].lower(), "application/octet-stream")
    return Response(body, mimetype=mime, headers={"Cache-Control": "public, max-age=3600"})

@app.route("/api/cover")
def api_cover():
    title = request.args.get("title", "")
    return jsonify({"cover": igdb_cover(clean_query(title)) if title else ""})

@app.route("/api/discover")
def api_discover():
    items = igdb_popular(40)
    for it in items:
        it["in_library"] = in_library(it["title"], None)
    return jsonify(items)

@app.route("/api/discover/rows")
def api_discover_rows():
    rows = discover_rows()
    rec = recommend_for_user(session.get("user", ""))
    if rec:
        bl = [str(p).strip().lower() for p in load_settings().get("blocklist", []) if str(p).strip()]
        games = [{**gm, "in_library": in_library(gm["title"], None)}
                 for gm in rec["games"] if not is_blocked(gm["title"], bl)]
        if games:
            rows = [{"slug": "", "key": "reco", "console": rec["seed"],
                     "reco": True, "games": games}] + rows
    return jsonify(rows)

@app.route("/api/download", methods=["POST"])
def api_download():
    it = request.get_json(force=True)
    if is_blocked(it.get("title","")):
        return jsonify({"ok":False,"msg":"gesperrt / blocked"})
    # Server-seitige Dedup-Sperre
    if in_library(it.get("title",""), it.get("platform")):
        return jsonify({"ok":False,"msg":"bereits in Bibliothek"})
    requester = session.get("user","")
    user = requester; onbehalf = False
    fu = (it.get("for_user") or "").strip()
    if fu and fu != requester and has_perm("manage_requests") and fu in load_users():
        user = fu; onbehalf = True   # Anfrage im Namen eines anderen Nutzers
    qi = quota_info(user)
    if qi.get("enabled") and qi.get("remaining", 1) <= 0 and not onbehalf:
        return jsonify({"ok":False,"msg":"Kontingent erschöpft / quota reached"})
    auto = onbehalf or may_autoapprove(user)
    # Was der Nutzer angefragt HAT und was er sich gewuenscht hatte — beides festhalten,
    # damit eine Falschlieferung spaeter belegbar ist statt Diskussionssache. (#77)
    it["variant"] = parse_release(it.get("title", ""))
    it["variant_wanted"] = variant_prefs(user)
    try:
        job = new_job(it, user=user, approved=auto)
    except ValueError as e:
        # Kein Auftrag, keine Warteschlange, kein stundenlanger Fehlversuch — sondern eine
        # Antwort, mit der der Nutzer etwas anfangen kann. (#384)
        if str(e) == "ia_login_required":
            return jsonify({"ok": False, "reason": "ia_login_required",
                            "msg": "Dieser Titel verlangt ein Archive.org-Konto. "
                                   "Schlüssel unter Einstellungen → Verbindungen eintragen "
                                   "(archive.org/account/s3.php). / This title needs an "
                                   "Archive.org account; add the keys in the settings."})
        raise
    if onbehalf:
        send_push_to_user(user, "Romseerr", f"Für dich angefragt / requested for you: {it.get('title','')[:60]}")
    if not auto:
        notify_send(f"🔔 Neue Anfrage / new request: **{it.get('title','')}** von {user} — Freigabe nötig")
    return jsonify({"ok":True,"id":job["id"],"pending": not auto})

@app.route("/api/jobs")
def api_jobs():
    with JOBS_LOCK: js = list(reversed(JOBS))
    # Ohne manage_requests sieht ein Nutzer nur die EIGENEN Anfragen (Datenschutz).
    if not has_perm("manage_requests"):
        me = session.get("user", "")
        js = [j for j in js if j.get("user") == me]
    js = js[:100]
    # Nur fuer fehlgeschlagene Auftraege nachsehen, ob die Dateien noch liegen: sonst
    # boete die Oberflaeche ein „erneut einlesen" an, das beim Druecken scheitert. Die
    # Pruefung kostet ein isdir je Fehler-Auftrag, nicht je Auftrag. (#245)
    for j in js:
        if j.get("state") == "error":
            j["reimportable"] = bool(find_output(SAB_DONE, j["id"]) or
                                     find_output(jd_out_dir(), j["id"]))
    return jsonify(js)

@app.route("/api/wishlist", methods=["GET", "POST"])
def api_wishlist():
    user = session.get("user", "") or "api"
    if request.method == "POST":
        if not has_perm("request"):
            return jsonify({"ok": False, "msg": "keine Berechtigung / no permission"}), 403
        d = request.get_json(force=True) or {}
        title = (d.get("title") or "").strip()
        if not title:
            return jsonify({"ok": False, "msg": "Titel fehlt / title missing"}), 400
        if in_library(title, (d.get("platform") or "") or None):
            return jsonify({"ok": False, "msg": "bereits in Bibliothek / already in library"})
        wishlist_add(user, title, d.get("platform", ""))
        return jsonify({"ok": True})
    return jsonify(load_wishlist().get(user, []))

@app.route("/api/wishlist/import", methods=["POST"])
def api_wishlist_import():
    """Wunschliste aus eingefügter Liste oder Datei füllen — zweistufig.

    Ohne `confirm` wird nur eine **Vorschau** berechnet (nichts geschrieben); mit
    `confirm: true` werden die mitgeschickten, vom Nutzer bestätigten `entries`
    übernommen. Dieselbe Berechtigung wie beim Einzel-Hinzufügen."""
    user = session.get("user", "") or "api"
    if not has_perm("request"):
        return jsonify({"ok": False, "msg": "keine Berechtigung / no permission"}), 403
    d = request.get_json(force=True, silent=True) or {}
    if d.get("confirm"):
        entries = d.get("entries")
        if not isinstance(entries, list):
            return jsonify({"ok": False, "msg": "entries fehlt / missing"}), 400
        return jsonify(wishlist_import(user, entries))
    text = d.get("text")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"ok": False, "msg": "Liste ist leer / list is empty"}), 400
    if len(text) > 200_000:
        return jsonify({"ok": False, "msg": "Liste zu groß / list too large (max 200 kB)"}), 413
    return jsonify(wishlist_preview(user, text))

EXAMPLE_WISHLIST = """\
# Romseerr — Beispiel-Wunschliste / example wishlist
# Ein Titel je Zeile. Zeilen mit # werden übersprungen.
# One title per line. Lines starting with # are skipped.
#
# Plattform ist optional. Erlaubt sind Semikolon, Tabulator — und ein Komma
# NUR dann, wenn dahinter wirklich eine Plattform steht (sonst bleibt es Teil
# des Titels). Slug oder Anzeigename, beides geht: snes / SNES, gb / Game Boy.
# Platform is optional: semicolon, tab, or a comma followed by a real platform.
#
# --- nur Titel / title only -------------------------------------------------
Chrono Trigger
The Legend of Zelda: A Link to the Past
# --- Titel;Plattform (Slug) / title;platform (slug) -------------------------
Super Metroid;snes
Metroid Fusion;gba
# --- Titel;Plattform (Anzeigename) / title;platform (display name) ----------
Pokemon Crystal;Game Boy
Metal Gear Solid;PS1
# --- Titel,Plattform — Komma trennt nur vor einer echten Plattform ----------
Castlevania: Symphony of the Night,psx
# ... hier bleibt das Komma Teil des Titels / here the comma stays in the title:
Sonic 3 & Knuckles, Collectors Edition
"""

@app.route("/api/wishlist/example.csv")
def api_wishlist_example():
    """Beispieldatei im erwarteten Format zum Herunterladen — erspart das Raten,
    wie Plattformen anzugeben sind, und ist selbst ein gültiger Import."""
    return Response(EXAMPLE_WISHLIST, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="romseerr-wishlist-example.csv"'})

@app.route("/api/titlemeta")
@login_required
def api_titlemeta():
    """Eigene Bewertung, die der anderen und die Kommentare zu einem Titel."""
    title = request.args.get("title", "")
    k = norm(title); me = session.get("user", "") or "api"
    je = load_ratings().get(k, {})
    return jsonify({
        "mine": (je.get(me) or {}).get("stars"),
        "others": [{"user": u, "stars": v.get("stars")} for u, v in je.items() if u != me],
        "comments": load_comments().get(k, [])[-50:]})

@app.route("/api/titlemeta/rating", methods=["POST"])
@login_required
def api_titlemeta_rating():
    d = request.get_json(force=True) or {}
    try: stars = max(0, min(5, int(d.get("stars") or 0)))
    except (TypeError, ValueError): stars = 0
    rating_set(session.get("user", "") or "api", d.get("title", ""), stars)
    return jsonify({"ok": True})

@app.route("/api/titlemeta/comment", methods=["POST"])
@login_required
def api_titlemeta_comment():
    d = request.get_json(force=True) or {}
    comment_add(session.get("user", "") or "api", d.get("title", ""), d.get("text", ""))
    return jsonify({"ok": True})

@app.route("/api/favourites", methods=["GET", "POST"])
@login_required
def api_favourites():
    """Favoriten des angemeldeten Nutzers. Zwei Menschen haben nichts miteinander zu tun,
    deshalb je Benutzer und nie gemeinsam. (#207)"""
    user = session.get("user", "") or "api"
    if request.method == "POST":
        d = request.get_json(force=True) or {}
        title = (d.get("title") or "").strip()
        if not title:
            return jsonify({"ok": False, "msg": "Titel fehlt / title missing"}), 400
        fav_add(user, title, d.get("platform", ""))
        return jsonify({"ok": True})
    return jsonify(load_favs().get(user, []))

@app.route("/api/favourites/remove", methods=["POST"])
@login_required
def api_favourites_remove():
    user = session.get("user", "") or "api"
    d = request.get_json(force=True) or {}
    fav_remove(user, (d.get("title") or "").strip())
    return jsonify({"ok": True})

@app.route("/api/wishlist/remove", methods=["POST"])
def api_wishlist_remove():
    user = session.get("user", "") or "api"
    d = request.get_json(force=True) or {}
    wishlist_remove(user, (d.get("title") or "").strip(), d.get("platform"))
    return jsonify({"ok": True})

@app.route("/health")
def health():
    """Liveness — plus der Speicherzustand.

    Bewusst weiterhin HTTP 200, auch wenn nicht geschrieben werden kann: den Container
    deswegen auf `unhealthy` zu setzen, übergäbe ihn der Restart-Policy, und eine
    Neustartschleife verdeckt die Ursache, statt sie zu zeigen. Sichtbar wird es über das
    Feld, die Startwarnung und das Banner. Bisher bestand `/health` aus zwei Lesezahlen —
    eine schreibgeschützte Datenbank besteht die mühelos. (#216)"""
    st = storage_state()
    return jsonify({"ok":True,"lib_titles":len(LIB['all']),"jobs":len(JOBS),
                    "storage":"rw" if st["ok"] else "ro",
                    # Plattformen, die beim letzten Indexlauf nicht lesbar waren (#381).
                    # Ohne dieses Feld ist `lib_titles` eine Zahl ohne Vorbehalt: eine
                    # teilweise gelesene Bibliothek sieht von aussen aus wie eine kleine.
                    "lib_failed":len(LIB.get('failed') or {}),
                    "lib_failed_platforms":sorted(LIB.get('failed') or {})})

# ---------- Betriebsmetriken (Prometheus) ----------
# /health beantwortet nur „läuft der Prozess". Die interessanten Ausfälle hier sind leise:
# ein Worker, der keine Jobs mehr annimmt, Importe, die reihenweise scheitern, eine
# Warteschlange, die nicht mehr abfließt. Genau das steht hier drin.
#
# Zähler leben im Prozess und werden NICHT auf Platte gehalten — Prometheus verträgt
# Neustarts (Counter-Reset), solange sie dazwischen monoton steigen.
# Bewusst KEIN Label je Titel oder Nutzer: die Kardinalität würde mit der Bibliothek wachsen.
METRICS_LOCK = threading.Lock()
IMPORTS      = {}   # (Ergebnis, Grund) -> Anzahl
WORKER_SEEN  = {}   # Worker-Name -> Unix-Zeit des letzten Durchlaufs
JOB_STATES   = ("pending", "queued", "downloading", "importing", "done", "error", "denied")
IMPORT_REASONS = {"none", "no_rom_files", "copy_failed", "exception"}

def beat(worker):
    """Lebenszeichen eines Hintergrund-Workers setzen (romseerr_worker_last_run_...)."""
    WORKER_SEEN[worker] = time.time()

def count_import(result, reason="none"):
    """Import-Ausgang zählen. `reason` ist auf IMPORT_REASONS begrenzt, damit die
    Label-Menge endlich bleibt — freie Fehlertexte gehören ins Log, nicht in eine Metrik."""
    with METRICS_LOCK:
        k = (result, reason if reason in IMPORT_REASONS else "other")
        IMPORTS[k] = IMPORTS.get(k, 0) + 1

def _mlabel(v):
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

def render_metrics():
    """Prometheus-Textformat (0.0.4) von Hand rendern — spart eine Abhängigkeit und
    ist bei dieser Menge Metriken übersichtlicher als eine Client-Bibliothek."""
    out = []
    def block(name, typ, helptext, samples):
        out.append(f"# HELP {name} {helptext}")
        out.append(f"# TYPE {name} {typ}")
        for labels, val in samples:
            lbl = ("{" + ",".join(f'{k}="{_mlabel(v)}"' for k, v in labels.items()) + "}") if labels else ""
            out.append(f"{name}{lbl} {val}")

    now = time.time()
    with JOBS_LOCK:
        jobs = [dict(j) for j in JOBS]

    per_state = {s: 0 for s in JOB_STATES}   # feste Reihe: Zustände verschwinden nie aus der Ausgabe
    for j in jobs:
        st = j.get("state", "")
        per_state[st] = per_state.get(st, 0) + 1
    block("romseerr_requests", "gauge", "Anfragen (Jobs) je Zustand / requests by state",
          [({"state": s}, n) for s, n in sorted(per_state.items())])

    waiting = [j for j in jobs if j.get("state") in ("pending", "queued")]
    block("romseerr_queue_depth", "gauge",
          "Wartende Anfragen (pending + queued) / requests waiting to be worked on",
          [({}, len(waiting))])
    oldest = min((j.get("created") or now for j in waiting), default=now)
    block("romseerr_queue_oldest_age_seconds", "gauge",
          "Alter der ältesten wartenden Anfrage / age of the oldest waiting request",
          [({}, round(max(0.0, now - oldest), 1))])

    with METRICS_LOCK:
        imports = dict(IMPORTS)
    block("romseerr_imports_total", "counter",
          "Abgeschlossene Importe nach Ergebnis / completed imports by outcome",
          [({"result": r, "reason": rs}, n) for (r, rs), n in sorted(imports.items())]
          or [({"result": "success", "reason": "none"}, 0)])

    try:
        wl = load_wishlist()
        wish_n = sum(len(v) for v in wl.values())
    except Exception:
        wish_n = 0
    block("romseerr_wishlist_entries", "gauge", "Einträge auf allen Wunschlisten / wishlist entries",
          [({}, wish_n)])

    block("romseerr_worker_last_run_timestamp_seconds", "gauge",
          "Letzter Durchlauf je Hintergrund-Worker / last run per background worker",
          [({"worker": w}, round(ts, 1)) for w, ts in sorted(WORKER_SEEN.items())])

    block("romseerr_library_titles", "gauge", "Titel im Bibliotheks-Index / indexed library titles",
          [({}, len(LIB["all"]))])
    block("romseerr_library_platforms", "gauge", "Plattformen mit Titeln / platforms holding titles",
          [({}, len(LIB["slugs"]))])
    block("romseerr_library_index_timestamp_seconds", "gauge",
          "Zeitpunkt des letzten Index-Laufs / time of the last index run", [({}, round(LIB["ts"], 1))])

    block("romseerr_build_info", "gauge", "Version und Build als statische Info / build info",
          [({"version": VERSION, "commit": BUILD_COMMIT or "", "built_at": BUILD_DATE or ""}, 1)])
    return "\n".join(out) + "\n"

@app.route("/metrics")
def api_metrics():
    """Prometheus-Endpunkt. Bewusst NICHT öffentlich — Metriken verraten Nutzungsmuster.
    Er hängt an derselben Schleuse wie die API, ein Scraper nutzt also den API-Key
    (`?apikey=…` oder Header `X-Api-Key`)."""
    return Response(render_metrics(), mimetype="text/plain; version=0.0.4; charset=utf-8")

# ---------- Version / Update-Hinweis ----------
UPDATE_URL   = "https://api.github.com/repos/Sparxx947/romseerr/releases/latest"
# ZWEITE ADRESSE, WEIL DIE ERSTE VORABVERSIONEN NICHT KENNT. `/releases/latest` ueberspringt
# Entwuerfe UND Vorabversionen — in einem Projekt, dessen Releases bisher ausnahmslos Betas
# sind, antwortet sie mit 404, sobald die Betas korrekt als Vorabversion markiert sind
# (#572). Der Hinweis bliebe dann fuer immer leer, ohne dass irgendwo etwas scheitert.
# Die Liste kennt beides und ist nach Erscheinen sortiert, das erste Element ist das
# neueste Release ueberhaupt. Entwuerfe zeigt sie nur einem angemeldeten Aufrufer mit
# Schreibrecht — hier fragt niemand angemeldet, sie bleiben also aussen vor.
#
# EN: /releases/latest skips pre-releases, so a betas-only project gets a silent 404 once
# the betas are marked correctly. The list endpoint knows both and is newest-first.
UPDATE_ANY_URL = "https://api.github.com/repos/Sparxx947/romseerr/releases?per_page=1"
UPDATE_TTL   = 6 * 3600
_UPDATE      = {"ts": 0, "latest": None}

_SEMVER_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?")

def _semver(v):
    """'v1.2.3-beta.1' -> Sortierschlüssel. NUR vergleichen, nicht anzeigen.

    DER VORABTEIL MUSS MITZAEHLEN. Vorher warf diese Funktion ihn weg, damit galten
    `1.3.0-beta.1` und `1.3.0-beta.2` als dieselbe Version — und schwerer wiegend: die erste
    stabile `1.3.0` wurde einer laufenden `1.3.0-beta.1` nicht angeboten. Seit #572 sind
    alle Releases dieses Projekts Vorabversionen, der Hinweis vergleicht also fast immer
    Beta gegen Beta: genau der Fall, den er nicht konnte. (#574)

    Rangfolge nach SemVer 2.0.0 §11, hier als Tupel gegossen, damit `>` sie von selbst
    einhält:
      * Zahlenteil zuerst — `1.4.0-beta.1` schlaegt `1.3.0`.
      * Eine Version OHNE Vorabteil steht ueber derselben MIT: darum `(1,)` gegen `(0, …)`.
      * Innerhalb des Vorabteils Bezeichner fuer Bezeichner. Ein rein numerischer zaehlt
        als Zahl (`beta.10` > `beta.9`, was eine Zeichenkette umgekehrt sortieren wuerde)
        und rangiert unter einem alphanumerischen — daher die Kennung 0 vor 1.
      * Bei gleichem Anfang gewinnt der laengere Vorabteil; das erledigt der
        Tupelvergleich, der das kuerzere Tupel als kleiner ansieht.
    Build-Metadaten (`+abc`) bleiben aussen vor, wie es die Norm verlangt — der reguläre
    Ausdruck laesst `+` gar nicht erst in den Vorabteil.

    EN: sort key honouring SemVer 2.0.0 §11 precedence, including pre-releases — a version
    without a pre-release outranks the same version with one, numeric identifiers compare
    numerically and rank below alphanumeric ones, build metadata is ignored.
    """
    m = _SEMVER_RE.match(str(v or ""))
    if not m:
        # Unlesbares ist das Kleinste ueberhaupt und loest deshalb nie einen Hinweis aus.
        return (0, 0, 0, (0,))
    zahl = tuple(int(x) for x in m.group(1, 2, 3))
    vorab = m.group(4)
    if not vorab:
        return zahl + ((1,),)
    teile = tuple((0, int(t), "") if t.isdigit() else (1, 0, t) for t in vorab.split("."))
    return zahl + ((0,) + teile,)

def _release_tag(url):
    """Eine Release-Adresse abfragen -> (Version ohne führendes v, HTTP-Status).

    Die beiden Endpunkte antworten verschieden geformt: `/releases/latest` mit EINEM
    Objekt, `/releases` mit einer Liste. Beides hier auf denselben Nenner bringen, damit
    der Aufrufer nur noch über den Status entscheidet."""
    r = requests.get(url, timeout=5, headers={"Accept": "application/vnd.github+json"})
    if r.status_code != 200:
        return None, r.status_code
    daten = r.json() or {}
    if isinstance(daten, list):
        daten = daten[0] if daten else {}
    return (str((daten or {}).get("tag_name") or "").lstrip("v") or None), 200

def latest_release():
    """Neueste veröffentlichte Version von GitHub, gecacht. Fehler sind still — ein
    Update-Hinweis darf nie eine Seite kaputt machen oder verzögert beantworten."""
    now = time.time()
    if now - _UPDATE["ts"] < UPDATE_TTL: return _UPDATE["latest"]
    _UPDATE["ts"] = now
    try:
        tag, code = _release_tag(UPDATE_URL)
        # 404 ist hier KEIN Ausfall, sondern eine Auskunft: es gibt (noch) keine stabile
        # Fassung. Nur dann die Liste fragen — sie kennt auch Vorabversionen. Bei jedem
        # anderen Fehler bleibt es bei einer Anfrage: ein Register, das gerade 500 sagt,
        # bekommt von uns nicht die doppelte Last.
        # EN: 404 means "no stable release yet", not "broken" — only then ask the list.
        if code == 404:
            tag, _ = _release_tag(UPDATE_ANY_URL)
        if tag:
            _UPDATE["latest"] = tag
    except Exception:
        pass
    return _UPDATE["latest"]

@app.route("/api/version")
def api_version():
    """Laufende Version + Build-Herkunft. Bewusst ohne Auth (die Login-Seite zeigt sie an);
    verrät nur, was ohnehin im Release-Feed steht. Der Update-Abgleich ist optional und
    passiert nur bei ?check=1, damit die normale Abfrage nie ins Netz greift."""
    # `provenance` beantwortet die Frage, die `null` offen laesst: Weiss diese Instanz,
    # woraus sie gebaut wurde? Ein Container lief hier einen ganzen Arbeitstag mit dem
    # Stand vom Vortag, und `{"commit": null}` sah aus wie eine Antwort, war aber
    # keine. Fehlende Angaben sind jetzt ein benannter Zustand, kein Loch.
    # `provenance` answers what a bare null leaves open: does this instance know what it
    # was built from? A container ran a full day on the previous day's code and
    # {"commit": null} read like an answer while being the absence of one.
    herkunft = "build" if (BUILD_COMMIT and BUILD_DATE) else (
        "teilweise" if (BUILD_COMMIT or BUILD_DATE) else "unbekannt")
    out = {"version": VERSION, "commit": BUILD_COMMIT, "built_at": BUILD_DATE,
           "provenance": herkunft}
    if herkunft != "build":
        out["provenance_hint"] = (
            "Ohne ROMSEERR_COMMIT und ROMSEERR_BUILT_AT beim Bauen laesst sich nicht "
            "feststellen, ob diese Instanz dem Quellstand entspricht. "
            "/ Without those build args an instance cannot say whether it matches the source.")
    if request.args.get("check") == "1" and load_settings().get("update_check", True):
        latest = latest_release()
        out["latest"] = latest
        out["update_available"] = bool(latest and _semver(latest) > _semver(VERSION))
    return jsonify(out)

# ---------- Auth-Routen ----------
PUBLIC = {"/login","/api/login","/api/setup","/api/auth/status","/health","/reset","/api/forgot","/api/reset",
          "/manifest.webmanifest","/sw.js","/icon.svg","/api/openapi.json","/api/docs","/api/version"}
@app.before_request
def _guard():
    """Zentrale Auth-Schleuse VOR jeder Anfrage:
      1. Pfade in PUBLIC (Login, Health, PWA-Assets, API-Doku …) ohne Prüfung durchlassen.
      2. Gültiger API-Key (Header X-Api-Key oder ?apikey=) -> g.api_auth=True (Admin-äquivalent).
      3. Sonst gültige Session verlangen; fehlt sie -> API: 401, Web: Redirect auf /login.
    Die *_required-Decorators bauen darauf auf (sie erlauben zusätzlich g.api_auth)."""
    p = request.path
    # Statische Dateien sind öffentlich — die Login-Seite braucht ihr CSS/JS, bevor
    # überhaupt jemand angemeldet ist. Sie enthalten nichts Vertrauliches.
    if p in PUBLIC or p.startswith("/assets/"): return
    key = request.headers.get("X-Api-Key") or request.args.get("apikey")
    stored = load_settings().get("apikey")
    # Konstante-Zeit-Vergleich gegen Timing-Angriffe (compare_digest verträgt keine None/Längenunterschiede)
    if key and stored and secrets.compare_digest(str(key), str(stored)):
        g.api_auth = True; return
    u = session.get("user")
    if not u or u not in load_users():
        session.clear()
        # /metrics wird von einem Scraper geholt, nicht von einem Browser — ein Redirect
        # auf /login käme dort als HTTP 200 mit HTML an und sähe wie ein Erfolg aus.
        if p.startswith("/api/") or p == "/metrics": return jsonify({"error":"auth"}), 401
        return redirect("/login")

@app.route("/login")
def login_page(): return Response(render_page("login.html"), mimetype="text/html")

@app.route("/api/auth/status")
def auth_status():
    g = load_settings().get("general", {})
    usr = load_users().get(session.get("user"), {}) if session.get("user") else {}
    return jsonify({"user":session.get("user"), "role":session.get("role"),
                    "setup": len(load_users())==0,
                    "default_lang": g.get("default_lang","de"),
                    "default_design": g.get("default_design","seerr"),
                    "app_name": g.get("app_name","Romseerr"),
                    "version": VERSION,
                    "avatar": usr.get("avatar",""),
                    "display_name": usr.get("display_name",""),
                    "user_lang": usr.get("lang",""),
                    "user_design": usr.get("design",""),
                    "perms": usr.get("perms", [])})

@app.route("/api/profile", methods=["GET"])
def api_profile_get():
    u = session.get("user"); usr = load_users().get(u, {})
    return jsonify({"username":u, "email":usr.get("email",""), "lang":usr.get("lang",""),
                    "design":usr.get("design",""),
                    "display_name":usr.get("display_name",""), "avatar":usr.get("avatar",""),
                    "webhook":usr.get("webhook",""), "ra_user":usr.get("ra_user",""),
                    "variant": variant_prefs(u), "variant_regions": list(REGIONS),
                    "quota": quota_info(u)})

@app.route("/api/profile", methods=["POST"])
def api_profile_set():
    u = session.get("user"); users = load_users()
    if u not in users: return jsonify({"ok":False}), 404
    d = request.get_json(force=True)
    if "email" in d: users[u]["email"] = (d.get("email") or "").strip()[:120]
    if "display_name" in d: users[u]["display_name"] = (d.get("display_name") or "").strip()[:60]
    if "webhook" in d: users[u]["webhook"] = (d.get("webhook") or "").strip()[:300]
    if "lang" in d: users[u]["lang"] = d.get("lang") if d.get("lang") in LANGS else ""
    if "design" in d: users[u]["design"] = d.get("design") if d.get("design") in DESIGNS else ""
    # RetroAchievements-Konto: freiwillig, nur fuer den eigenen Fortschritt (#79)
    if "ra_user" in d: users[u]["ra_user"] = (d.get("ra_user") or "").strip()[:60]
    if "variant" in d: users[u]["variant"] = sanitize_variant_prefs(d.get("variant"))
    if "avatar" in d:
        av = d.get("avatar") or ""
        if len(av) > 300000: return jsonify({"ok":False,"msg":"Bild zu groß (max ~300 KB)"}), 400
        users[u]["avatar"] = av
    save_users(users); return jsonify({"ok":True})

@app.route("/api/profile/password", methods=["POST"])
def api_profile_pw():
    u = session.get("user"); users = load_users()
    d = request.get_json(force=True); old = d.get("old","") or ""; new = d.get("new","") or ""
    if u not in users or not check_password_hash(users[u]["pw"], old):
        return jsonify({"ok":False,"msg":"altes Passwort falsch / wrong current password"}), 400
    if len(new) < 6: return jsonify({"ok":False,"msg":"min. 6 Zeichen"}), 400
    users[u]["pw"] = generate_password_hash(new); save_users(users)
    return jsonify({"ok":True})

@app.route("/api/profile/notify-test", methods=["POST"])
def api_profile_notify_test():
    wh = ((request.get_json(silent=True) or {}).get("url") or "").strip()
    if not wh: return jsonify({"ok":False,"msg":"keine URL"}), 400
    # Zuerst FRAGEN, dann senden: die Begruendung kommt aus der festen Tabelle URL_REFUSED
    # und nicht aus einem Ausnahmetext — der duerfte so oder so nicht nach aussen. (#89)
    ok, why = url_allowed(wh)
    if not ok:
        return jsonify({"ok":False,"msg":URL_REFUSED.get(why, "abgelehnt / refused")}), 400
    try:
        safe_post(wh, json={"content":"✅ Romseerr — persönlicher Test / personal test"})
        return jsonify({"ok":True})
    except Exception as e:
        log(f"Persoenlicher Webhook-Test: {e}")
        return jsonify({"ok":False,"msg":err_kind(e)}), 400

@app.route("/api/forgot", methods=["POST"])
def api_forgot():
    q = ((request.get_json(silent=True) or {}).get("user") or "").strip().lower()
    users = load_users(); matched = None
    for un, uv in users.items():
        if un.lower() == q or (q and uv.get("email","").lower() == q):
            matched = un; break
    if matched and users[matched].get("email") and load_settings().get("smtp", {}).get("enabled"):
        tok = gen_reset(matched); base = request.host_url.rstrip("/")
        send_mail(users[matched]["email"], "Romseerr — Passwort zurücksetzen / password reset",
                  f"Link (1 Stunde gültig / valid 1 hour):\n{base}/reset?token={tok}")
    return jsonify({"ok": True})   # generisch, verrät keine Existenz

@app.route("/reset")
def reset_page(): return Response(render_page("reset.html"), mimetype="text/html")

@app.route("/api/reset", methods=["POST"])
def api_reset():
    d = request.get_json(force=True); u = check_reset(d.get("token","")); new = d.get("new","") or ""
    if not u: return jsonify({"ok":False,"msg":"Token ungültig/abgelaufen / invalid or expired"}), 400
    if len(new) < 6: return jsonify({"ok":False,"msg":"min. 6 Zeichen"}), 400
    users = load_users()
    if u not in users: return jsonify({"ok":False}), 400
    users[u]["pw"] = generate_password_hash(new); save_users(users)
    RESET_TOKENS.pop(d.get("token",""), None)
    return jsonify({"ok": True})

@app.route("/api/settings/mail-test", methods=["POST"])
@admin_required
def api_mail_test():
    to = ((request.get_json(silent=True) or {}).get("to") or "").strip()
    if not to: return jsonify({"ok":False,"msg":"keine Adresse"}), 400
    ok = send_mail(to, "Romseerr — Test", "SMTP-Test erfolgreich / SMTP test successful.")
    return jsonify({"ok": ok, "msg": "" if ok else "Versand fehlgeschlagen (Log prüfen)"})

# ---------- Bibliothek organisieren (#593) ----------
# Die Werkzeuge unter `library-tools/` bauen die Bibliothek um. Sie schreiben ihren Stand
# nach `<roms>/.umbau/` — und ZWEI Dateien, nicht eine: `fortschritt.json` fuer den vollen
# Umbau und `fortschritt-beiwerk.json` fuer `--nur-beiwerk`. Beide getrennt zu halten war
# Absicht (#318): Sonst gaelte eine Plattform, die nur eingesammelt wurde, als vollstaendig
# umgebaut, und ein spaeterer Lauf wuerde sie ueberspringen.
UMBAU_DIR = os.path.join(ROMS, ".umbau")
UMBAU_STAENDE = {"voll": "fortschritt.json", "beiwerk": "fortschritt-beiwerk.json"}

def _umbau_stand(datei):
    """Eine Fortschrittsdatei -> Fortschritt in Prozent, Laufzeit, Restschaetzung.

    RECHNET AUF DATEIEN, NICHT AUF PLATTFORMEN: `amiga` allein sind ueber 270.000
    Eintraege, `gbc` sind 5.548 — eine Prozentzahl aus „Plattformen erledigt" stuende
    stundenlang auf demselben Wert und spraenge dann. `gesamt_dateien` und
    `offen_dateien` stehen ohnehin in der Datei.

    KEIN ZUSTAND AUS EINEM AUFTRAGSDATENSATZ: Romseerr raeumt beim Start laufende
    Auftraege ab (#336). Ein Neustart mitten im Umbau wuerde einen Auftragseintrag als tot
    markieren, waehrend der Umbau weiterlaeuft — die Datei weiss es besser, denn sie wird
    vom laufenden Werkzeug geschrieben.

    EN: derives percent/elapsed/remaining from the progress file rather than from a job
    record, because a restart clears job records while the rebuild keeps going.
    """
    try:
        with open(datei, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            return None
    except (OSError, ValueError):
        return None

    gesamt = d.get("gesamt_dateien") or 0
    offen = d.get("offen_dateien")
    fertig = bool(d.get("fertig"))
    erledigt = [e for e in (d.get("erledigt") or []) if isinstance(e, dict)]
    getan = (gesamt - offen) if (gesamt and isinstance(offen, (int, float))) else None
    prozent = round(100 * getan / gesamt, 1) if (gesamt and getan is not None) else None
    if fertig:
        prozent = 100.0

    # `aktuell` steht nur waehrend eines Laufs in der Datei. Ein sauber beendeter Lauf
    # setzt `fertig`; fehlt beides, ist der Lauf abgebrochen — und genau das ist die
    # Auskunft, wegen der jemand hier nachsieht.
    aktuell = d.get("aktuell") if isinstance(d.get("aktuell"), dict) else None
    zustand = "fertig" if fertig else ("laeuft" if aktuell else "abgebrochen")

    start = d.get("start")
    geaendert = os.path.getmtime(datei)
    # DAUER, NICHT „WIE LANGE HER" (#593). Fuer einen laufenden Lauf ist beides dasselbe,
    # fuer einen beendeten nicht: Der volle Umbau vom 12.08. stand nach der ersten Fassung
    # mit 152.901 s (42 h) da — gelaufen war er rund 12. Aufgefallen erst an der echten
    # Anlage, weil die Tests `start` relativ zu `time.time()` schreiben und dort beide
    # Lesarten zusammenfallen.
    # Als Ende eines beendeten Laufs dient der letzte Schreibzugriff auf die Datei;
    # genauer geht es nicht, denn das Werkzeug notiert keinen Endzeitpunkt.
    ende = time.time() if zustand == "laeuft" else geaendert
    laeuft_seit = max(0, int(ende - start)) if isinstance(start, (int, float)) else None
    # Restschaetzung nur, wenn schon etwas geschafft ist — sonst waere sie eine Division
    # durch null mit dem Anschein einer Auskunft. Und nur fuer einen LAUFENDEN Lauf:
    # Bei einem abgebrochenen waere sie eine Vorhersage ueber etwas, das niemand mehr tut.
    rest = None
    if zustand == "laeuft" and laeuft_seit and getan and gesamt and getan < gesamt:
        rest = int(laeuft_seit / getan * (gesamt - getan))
    return {"zustand": zustand, "prozent": prozent, "laeuft_seit": laeuft_seit,
            "rest_geschaetzt": rest, "dateien_gesamt": gesamt, "dateien_offen": offen,
            "plattformen_gesamt": d.get("plattformen_gesamt"),
            "plattformen_erledigt": len(erledigt),
            "aktuell": (aktuell or {}).get("plattform"),
            "fehlgeschlagen": [e.get("plattform") for e in (d.get("fehlgeschlagen") or [])
                               if isinstance(e, dict) and e.get("plattform")],
            "geaendert": geaendert}

def _umbau_protokolle(grenze=12):
    """Die juengsten Aktionsprotokolle — jedes ist ein Rueckweg.

    Der Name traegt Plattform und Zeitpunkt, der Inhalt eine JSON-Zeile je Aktion. Genau
    diese Datei nimmt `--zurueck` entgegen; sie hier zu nennen ist der Unterschied
    zwischen „es gibt einen Rueckweg" und „hier ist er".
    """
    try:
        with os.scandir(UMBAU_DIR) as it:
            dateien = [e for e in it if e.is_file() and e.name.endswith(".jsonl")]
    except OSError:
        return []
    dateien.sort(key=lambda e: e.stat().st_mtime, reverse=True)
    out = []
    for e in dateien[:grenze]:
        st = e.stat()
        out.append({"name": e.name, "groesse": st.st_size, "zeit": st.st_mtime,
                    "zurueck": f"retronas-organisieren --zurueck /roms/.umbau/{e.name}"})
    return out

@app.route("/api/library/organize/status")
@admin_required
def api_library_organize_status():
    """Zustand der Bibliotheks-Umbauten. Rein lesend — hier wird nichts gestartet."""
    staende = {}
    for art, name in UMBAU_STAENDE.items():
        s = _umbau_stand(os.path.join(UMBAU_DIR, name))
        if s: staende[art] = s
    # AUS DIESER INSTANZ ODER VON AUSSEN? Beides kommt vor — ein Lauf kann auch im
    # Wegwerf-Container von Hand gestartet worden sein. Nur den eigenen kann diese
    # Oberflaeche anhalten, und genau das muss sie sagen koennen.
    #
    # DER LETZTE LAUF BLEIBT STEHEN, bis ein neuer beginnt. Die erste Fassung liess ihn
    # verschwinden, sobald der Prozess endete — also genau in dem Augenblick, in dem sein
    # ERGEBNIS da war: Das Werkzeug gibt seine Zusammenfassung am Ende aus, nicht
    # unterwegs. Am echten System nachgemessen: waehrend des Laufs 0 Zeilen, danach kein
    # Lauf mehr. Ein Testlauf hinterliess damit nichts als eine leere Anzeige — und
    # ausgerechnet dafuer ist er da.
    eigener = _umbau_laeuft()
    lauf = None
    if UMBAU_LAUF["proc"] is not None:
        p = UMBAU_LAUF["proc"]
        lauf = {"art": UMBAU_LAUF["art"], "trocken": UMBAU_LAUF["trocken"],
                "plattform": UMBAU_LAUF["plattform"],
                "gestartet": UMBAU_LAUF["gestartet"],
                "laeuft": eigener,
                "code": None if eigener else p.returncode,
                "ausgabe": UMBAU_LAUF["ausgabe"][-40:]}
    return jsonify({
        "roms": ROMS,
        "umbau_dir": UMBAU_DIR,
        "vorhanden": os.path.isdir(UMBAU_DIR),
        "staende": staende,
        "laeuft": any(s["zustand"] == "laeuft" for s in staende.values()) or eigener,
        "eigener_lauf": lauf,
        "werkzeug": os.path.isfile(WERKZEUG),
        "protokolle": _umbau_protokolle(),
    })

def _werkzeug_pfad():
    """Wo `retronas-organisieren` liegt — im Abbild anders als im Quell-Checkout.

    Der Dockerfile kopiert `contrib/library-tools/` nach `/app/library-tools/`, im
    Repository liegt es unter `contrib/`. Ohne beide Orte laeuft der Endpunkt im
    Entwickler-Checkout nie an, und damit waere er auch nicht zu testen — was genau die
    Art Luecke ist, in der sich Fehler halten.
    """
    hier = os.path.dirname(os.path.abspath(__file__))
    for teil in ("library-tools", os.path.join("contrib", "library-tools")):
        p = os.path.join(hier, teil, "retronas-organisieren")
        if os.path.isfile(p):
            return p
    return os.path.join(hier, "library-tools", "retronas-organisieren")

WERKZEUG = _werkzeug_pfad()
# Ein Lauf je Instanz. Mehr waeren nicht nur unnoetig, sie stritten sich um dieselben
# Dateien und denselben Wiederaufsetzpunkt.
UMBAU_LAUF = {"proc": None, "art": None, "trocken": None, "plattform": None,
              "gestartet": None, "ausgabe": []}
UMBAU_SPERRE = threading.Lock()

def _umbau_laeuft():
    p = UMBAU_LAUF["proc"]
    return bool(p and p.poll() is None)

def _umbau_starten(art, trocken, plattform=None):
    """Das Werkzeug als Unterprozess starten und seine Ausgabe mitschreiben.

    WARUM IM EIGENEN PROZESS UND NICHT IM FADEN: Das Werkzeug ist ein eigenstaendiges
    Programm mit eigenem `main()`; es zu importieren hiesse, seine Argumentverarbeitung
    und sein Beenden in Romseerr hineinzuziehen.

    WAS EIN NEUSTART BEDEUTET — und warum das vertretbar ist: Der Unterprozess stirbt
    mit dem Container. Ein Deploy mitten im Umbau bricht ihn also ab. Das ist hinnehmbar,
    WEIL das Werkzeug wiederaufsetzbar ist (#371/#372): Der naechste Lauf ueberspringt,
    was schon durch ist. Und die Anzeige liest ihren Zustand aus der Fortschrittsdatei,
    nicht aus diesem Datensatz hier — nach einem Neustart steht dort „abgebrochen", was
    die Wahrheit ist, statt „laeuft", was eine Luege waere.
    """
    argumente = [sys.executable, "-u", WERKZEUG]
    if trocken: argumente.append("--trocken")
    if art == "beiwerk": argumente.append("--nur-beiwerk")
    argumente += [plattform] if plattform else ["--alle"]
    argumente += ["--wurzel", ROMS]
    p = subprocess.Popen(argumente, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, bufsize=1, cwd=ROMS)
    UMBAU_LAUF.update({"proc": p, "art": art, "trocken": bool(trocken),
                       "plattform": plattform, "gestartet": time.time(), "ausgabe": []})

    def mitlesen():
        # Nur die letzten Zeilen halten: Ein voller Lauf schreibt Zehntausende, und der
        # Zweck hier ist „was tut es gerade", nicht ein zweites Protokoll — das echte
        # steht ohnehin in `.umbau/`.
        for zeile in p.stdout:
            UMBAU_LAUF["ausgabe"].append(zeile.rstrip())
            del UMBAU_LAUF["ausgabe"][:-200]
        p.wait()
        log(f"Bibliotheks-Umbau beendet ({art}{', trocken' if trocken else ''}): "
            f"Rueckgabewert {p.returncode}")
    threading.Thread(target=mitlesen, daemon=True).start()
    return p

@app.route("/api/library/organize/run", methods=["POST"])
@admin_required
def api_library_organize_run():
    """Einen Umbau starten. Trocken oder echt, ganze Bibliothek oder eine Plattform."""
    d = request.get_json(silent=True) or {}
    art = "beiwerk" if d.get("art") == "beiwerk" else "voll"
    trocken = bool(d.get("trocken"))
    plattform = (str(d.get("plattform") or "").strip() or None)
    # GEGEN EINE LISTE PRUEFEN, NICHT EINEN PFAD BAUEN. Der Name kommt aus einem
    # Eingabefeld und wird zu einem Kommandozeilenargument. Die erste Fassung pruefte ein
    # Muster und setzte ihn DANN in `os.path.join(ROMS, …)` — CodeQL hat das zu Recht als
    # „uncontrolled data used in path expression" gemeldet: Die Reihenfolge verlaesst sich
    # darauf, dass das Muster an alles gedacht hat.
    # Hier wird stattdessen mit den Verzeichnissen verglichen, die es TATSAECHLICH gibt.
    # Damit kann kein Wert aus der Anfrage mehr in einen Pfad geraten — was nicht in der
    # Bibliothek steht, kommt gar nicht erst durch. Das Muster bleibt als erste Schranke,
    # damit Unfug nicht bis zum Verzeichnislesen kommt.
    # EN: compared against the directories that actually exist instead of being joined into
    # a path, so no request value reaches the filesystem as a path at all.
    if plattform:
        if not re.fullmatch(r"[A-Za-z0-9 ._-]{1,64}", plattform) or plattform.startswith("."):
            return jsonify({"ok": False, "msg": "unzulaessiger Plattformname"}), 400
        try:
            with os.scandir(ROMS) as it:
                bekannt = {e.name for e in it if e.is_dir() and not e.name.startswith(".")}
        except OSError:
            bekannt = set()
        if plattform not in bekannt:
            return jsonify({"ok": False, "msg": f"kein Ordner {plattform} in der Bibliothek"}), 400
    if not os.path.isfile(WERKZEUG):
        return jsonify({"ok": False, "msg": "Werkzeug nicht im Abbild"}), 500

    with UMBAU_SPERRE:
        if _umbau_laeuft():
            return jsonify({"ok": False, "msg": "es laeuft bereits ein Umbau"}), 409
        # ZWEITE SPERRE, und die ist die wichtigere: Ein Lauf, den ein anderer Prozess
        # gestartet hat — etwa der Wegwerf-Container von Hand —, taucht in UMBAU_LAUF
        # nicht auf. Die Fortschrittsdatei sieht ihn trotzdem.
        for name in UMBAU_STAENDE.values():
            s = _umbau_stand(os.path.join(UMBAU_DIR, name))
            if s and s["zustand"] == "laeuft":
                return jsonify({"ok": False,
                                "msg": "laut Fortschrittsdatei laeuft bereits ein Umbau"}), 409
        _umbau_starten(art, trocken, plattform)
    log(f"Bibliotheks-Umbau gestartet: {art}"
        f"{', trocken' if trocken else ''}{', ' + plattform if plattform else ', alle'}")
    return jsonify({"ok": True, "art": art, "trocken": trocken, "plattform": plattform})

@app.route("/api/library/organize/stop", methods=["POST"])
@admin_required
def api_library_organize_stop():
    """Einen laufenden Umbau anhalten.

    `terminate`, nicht `kill`: Das Werkzeug schreibt jede Aktion sofort ins Protokoll und
    haelt den Wiederaufsetzpunkt aktuell, ein sauberes Signal genuegt also. Was bereits
    verschoben wurde, bleibt verschoben — der Rueckweg dafuer ist das Protokoll.
    """
    if not _umbau_laeuft():
        return jsonify({"ok": False, "msg": "es laeuft kein Umbau aus dieser Instanz"}), 409
    UMBAU_LAUF["proc"].terminate()
    log("Bibliotheks-Umbau auf Anforderung angehalten")
    return jsonify({"ok": True})

@app.route("/api/blocklist", methods=["GET"])
@admin_required
def api_blocklist_get():
    return jsonify(load_settings().get("blocklist", []))

@app.route("/api/blocklist", methods=["POST"])
@admin_required
def api_blocklist_set():
    pats = (request.get_json(force=True) or {}).get("patterns", [])
    pats = [str(p).strip()[:80] for p in pats if str(p).strip()][:200]
    s = load_settings(); s["blocklist"] = pats; save_settings(s)
    return jsonify({"ok": True})

@app.route("/api/maillog")
@admin_required
def api_maillog():
    return jsonify(kv_get("maillog", []))

# ---- Probleme / Issues ----
def load_issues():
    return kv_get("issues", [])
def save_issues(x):
    kv_put("issues", x)

@app.route("/api/issues", methods=["GET"])
def api_issues_get():
    items = load_issues()
    if session.get("role") != "admin":
        items = [i for i in items if i.get("user") == session.get("user")]
    return jsonify(sorted(items, key=lambda i: i.get("created", 0), reverse=True))

@app.route("/api/issues", methods=["POST"])
def api_issues_add():
    d = request.get_json(force=True); items = load_issues()
    iid = f"{int(time.time())}{len(items)%1000:03d}"
    items.append({"id":iid, "user":session.get("user",""), "title":(d.get("title") or "")[:140],
                  "platform":(d.get("platform") or "")[:40], "type":(d.get("type") or "other")[:30],
                  "message":(d.get("message") or "")[:1000], "status":"open",
                  "created":int(time.time()), "ts":datetime.now().strftime("%Y-%m-%d %H:%M")})
    save_issues(items)
    notify_send(f"🐞 Neues Problem / new issue: {(d.get('title') or '')[:80]} ({session.get('user','')})")
    return jsonify({"ok":True, "id":iid})

@app.route("/api/issues/<iid>/close", methods=["POST"])
@perm_required("manage_issues")
def api_issues_close(iid):
    items = load_issues()
    for i in items:
        if i["id"] == iid: i["status"] = "closed"
    save_issues(items); return jsonify({"ok":True})

@app.route("/api/issues/<iid>/comment", methods=["POST"])
@login_required
def api_issues_comment(iid):
    txt = (request.get_json(force=True).get("text") or "").strip()[:1000]
    if not txt: return jsonify({"error":"empty"}), 400
    items = load_issues()
    for i in items:
        if i["id"] == iid:
            if i.get("user") != session.get("user") and not has_perm("manage_issues"):
                return jsonify({"error":"forbidden"}), 403
            i.setdefault("comments", []).append({
                "user": session.get("user",""), "text": txt, "staff": bool(has_perm("manage_issues")),
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M")})
            save_issues(items)
            return jsonify({"ok":True, "comments": i["comments"]})
    return jsonify({"error":"not found"}), 404

@app.route("/api/issues/<iid>", methods=["DELETE"])
@perm_required("manage_issues")
def api_issues_del(iid):
    save_issues([i for i in load_issues() if i["id"] != iid]); return jsonify({"ok":True})

# ---- Private Nachrichten / direct messages ----
def msg_unread(user):
    try:
        with closing(db_conn()) as c:
            return c.execute("SELECT COUNT(*) FROM messages WHERE recipient=? AND read=0", (user,)).fetchone()[0]
    except Exception:
        return 0

@app.route("/api/messages")
@login_required
def api_messages():
    me = session.get("user", "")
    with closing(db_conn()) as c:
        rows = c.execute("SELECT id,sender,recipient,body,ts,read FROM messages "
                         "WHERE sender=? OR recipient=? ORDER BY ts", (me, me)).fetchall()
    msgs = [{"id": r[0], "from": r[1], "to": r[2], "body": r[3], "ts": r[4], "read": bool(r[5])} for r in rows]
    users = [u for u in load_users().keys() if u != me]
    return jsonify({"me": me, "messages": msgs, "users": sorted(users), "unread": msg_unread(me)})

@app.route("/api/messages", methods=["POST"])
@login_required
def api_messages_send():
    d = request.get_json(force=True); me = session.get("user", "")
    to = (d.get("to") or "").strip(); body = (d.get("body") or "").strip()[:2000]
    if not body: return jsonify({"ok": False, "msg": "leer / empty"}), 400
    if to == me or to not in load_users(): return jsonify({"ok": False, "msg": "Empfänger?"}), 400
    with DB_LOCK, closing(db_conn()) as c, c:
        c.execute("INSERT INTO messages(sender,recipient,body,ts,read) VALUES(?,?,?,?,0)",
                  (me, to, body, int(time.time())))
    # Empfänger benachrichtigen (best effort): Web-Push + persönlicher Discord-Webhook
    send_push_to_user(to, "Romseerr", f"✉ {me}: {body[:60]}")
    wh = load_users().get(to, {}).get("webhook", "")
    if wh:
        try: safe_post(wh, json={"content": f"✉ **{me}**: {body[:200]}"})
        except Exception: pass
    return jsonify({"ok": True})

@app.route("/api/messages/read", methods=["POST"])
@login_required
def api_messages_read():
    me = session.get("user", ""); other = (request.get_json(force=True).get("from") or "").strip()
    with DB_LOCK, closing(db_conn()) as c, c:
        c.execute("UPDATE messages SET read=1 WHERE recipient=? AND sender=?", (me, other))
    return jsonify({"ok": True})

# ---------- Admin: Logs, Statistik, Wartung ----------
JOB_FINISHED = {"done", "error", "denied"}

@app.route("/api/logs")
@admin_required
def api_logs():
    try: n = int(request.args.get("n", 200) or 200)
    except (TypeError, ValueError): n = 200
    n = min(max(n, 1), 1000)
    try:
        with open(LOGFILE) as f: lines = f.readlines()
    except Exception: lines = []
    return jsonify({"lines": [l.rstrip("\n") for l in lines[-n:]]})

@app.route("/api/admin/stats")
@admin_required
def api_admin_stats():
    with JOBS_LOCK: js = list(JOBS)
    with LIB_LOCK: plat, titles = len(LIB["slugs"]), len(LIB["all"])
    return jsonify({"jobs_total": len(js),
        "jobs_active": sum(1 for j in js if j.get("state") not in JOB_FINISHED),
        "jobs_finished": sum(1 for j in js if j.get("state") in JOB_FINISHED),
        "lib_platforms": plat, "lib_titles": titles, "igdb_cache": len(IGDB["cache"]),
        "discover_age": int(time.time()-DISCOVER_CACHE["ts"]) if DISCOVER_CACHE["ts"] else None})

@app.route("/api/admin/cache/clear", methods=["POST"])
@admin_required
def api_admin_cache_clear():
    IGDB["cache"].clear(); DISCOVER_CACHE["rows"] = []; DISCOVER_CACHE["ts"] = 0
    log("Cache geleert (Admin)")
    return jsonify({"ok": True})

@app.route("/api/import/status")
@login_required
def api_import_status():
    """Was im Einwurfordner liegt und was damit passieren wird. (#396)

    Ein Trockenlauf: Er verschiebt nichts, er sagt nur, was einsortierbar ist und was
    nicht — mit Grund. Ohne diese Ansicht waere der Ordner eine Blackbox, in der Dateien
    verschwinden oder eben nicht, und niemand wuesste warum.
    """
    if not os.path.isdir(IMPORT_SHARE):
        return jsonify({"aktiv": False, "pfad": IMPORT_SHARE,
                        "msg": "Einwurfordner nicht eingehängt / import share not mounted"})
    bereit, offen = einwurf_scannen(trocken=True)
    return jsonify({"aktiv": True, "pfad": IMPORT_SHARE, "takt_sek": EINWURF_TAKT,
                    "bereit": bereit[:200], "offen": offen[:200],
                    "bereit_gesamt": len(bereit), "offen_gesamt": len(offen)})


@app.route("/api/import/scan", methods=["POST"])
@admin_required
def api_import_scan():
    """Sofort einlesen, statt auf den naechsten Takt zu warten. (#396)"""
    fertig, offen = einwurf_scannen()
    if fertig:
        threading.Thread(target=build_index, daemon=True).start()
    return jsonify({"ok": True, "eingeordnet": len(fertig), "offen": len(offen)})


@app.route("/api/admin/reindex", methods=["POST"])
@admin_required
def api_admin_reindex():
    threading.Thread(target=build_index, daemon=True).start()
    log("Bibliotheks-Reindex angestoßen (Admin)")
    return jsonify({"ok": True})

@app.route("/api/leftovers")
@perm_required("manage_settings")
def api_leftovers():
    """Was von fehlgeschlagenen Importen liegen geblieben ist. (#244)"""
    e = leftover_dirs()
    return jsonify({"items": e, "total": sum(x["size"] for x in e),
                    "days": load_settings().get("leftover_days", 14)})

@app.route("/api/leftovers/remove", methods=["POST"])
@perm_required("manage_settings")
def api_leftovers_remove():
    """Liegengebliebene Ordner entfernen — einzeln (`jid`) oder alle (`all: true`).

    Geloescht wird ueber `leftover_remove`, nie ueber einen Pfad aus dem Request: sonst
    entschiede der Aufrufer, was `rm -rf` trifft.
    """
    d = request.get_json(silent=True) or {}
    ziel = leftover_dirs()
    if not d.get("all"):
        jid = str(d.get("jid") or "")
        ziel = [x for x in ziel if x["jid"] == jid]
        if not ziel: return jsonify({"error": "nicht gefunden / not found"}), 404
    weg, bytes_weg, fehler = 0, 0, []
    for x in ziel:
        ok, grund = leftover_remove(x["path"])
        if ok: weg += 1; bytes_weg += x["size"]
        else: fehler.append(f"{x['name']}: {grund}")
    log(f"{weg} liegengebliebene Downloads entfernt ({bytes_weg/1073741824:.1f} GB, Admin)")
    return jsonify({"ok": not fehler, "removed": weg, "bytes": bytes_weg, "errors": fehler})

def job_dateien_da(jid):
    """Pfad des liegengebliebenen Downloads zu einem Auftrag — oder None. (#246)"""
    return find_output(SAB_DONE, jid) or find_output(jd_out_dir(), jid)

@app.route("/api/jobs/<jid>", methods=["DELETE"])
@perm_required("manage_requests")
def api_job_delete(jid):
    """Eine abgeschlossene Anfrage entfernen. (#246)

    Fehlgeschlagene Anfragen zaehlen dauerhaft im Zaehler mit (`jobOffen` = aktiv+fehler),
    ohne einen Weg, sie einzeln loszuwerden — die Zahl konnte nur steigen.

    Der heikle Teil ist der liegengebliebene Download: der Auftrag ist das Einzige, was
    einen `romseerr_<jid>`-Ordner noch einem Titel zuordnet. Wird er geloescht, bleibt ein
    unidentifizierbarer Haufen zurueck, den die Frist irgendwann wegraeumt. Deshalb
    entweder mitloeschen (`files: true`) oder im Ergebnis ausdruecklich melden, dass Daten
    zurueckbleiben — stillschweigend verwaisen lassen ist der eine Ausgang, den es nicht
    geben darf.
    """
    global JOBS
    j = get_job(jid)
    if not j: return jsonify({"ok": False, "msg": "unbekannt / unknown"}), 404
    if j.get("state") not in JOB_FINISHED:
        return jsonify({"ok": False,
                        "msg": "laufende Anfrage / request still active"}), 400
    mit_dateien = bool((request.get_json(silent=True) or {}).get("files"))
    pfad = job_dateien_da(jid)
    dateien_weg = False
    if pfad and mit_dateien:
        dateien_weg, _ = leftover_remove(pfad)
    with JOBS_LOCK:
        JOBS = [x for x in JOBS if x.get("id") != jid]; save_jobs()
    log(f"Anfrage {jid} entfernt (Admin)"
        + (f", Dateien geloescht" if dateien_weg else
           f", Dateien bleiben liegen: {pfad}" if pfad else ""))
    return jsonify({"ok": True, "files_deleted": dateien_weg,
                    "files_left": bool(pfad) and not dateien_weg})

@app.route("/api/jobs/clear-finished", methods=["POST"])
@perm_required("manage_requests")
def api_jobs_clear_finished():
    """Abgeschlossene Anfragen sammelweise entfernen — auf Wunsch nur bestimmte Zustaende.

    Ohne Angabe alles Abgeschlossene (`done`, `error`, `denied`), wie bisher. Mit
    `states` laesst sich das eingrenzen; „nur die Fehlgeschlagenen" ist der haeufige Fall,
    und der ging vorher nur alles-oder-nichts. (#246)
    """
    global JOBS
    gewuenscht = (request.get_json(silent=True) or {}).get("states") or []
    zustaende = {z for z in gewuenscht if z in JOB_FINISHED} or set(JOB_FINISHED)
    with JOBS_LOCK:
        before = len(JOBS); JOBS = [j for j in JOBS if j.get("state") not in zustaende]; save_jobs()
        removed = before - len(JOBS)
    log(f"{removed} Anfragen entfernt ({', '.join(sorted(zustaende))}, Admin)")
    return jsonify({"ok": True, "removed": removed})

# ---------- PWA + Web-Push ----------
MANIFEST = {"name":"Romseerr","short_name":"Romseerr","start_url":"/","scope":"/",
    "display":"standalone","background_color":"#0b0d10","theme_color":"#0b0d10",
    "icons":[{"src":"/icon.svg","sizes":"any","type":"image/svg+xml","purpose":"any maskable"}]}

@app.route("/manifest.webmanifest")
def pwa_manifest(): return Response(json.dumps(MANIFEST), mimetype="application/manifest+json")

@app.route("/icon.svg")
def pwa_icon():
    a = _ASSETS.get("icon.svg")
    return Response(a["body"] if a else b"", mimetype="image/svg+xml")

@app.route("/sw.js")
def pwa_sw():
    # Der Service-Worker MUSS unter / liegen — sein Geltungsbereich ergibt sich aus dem Pfad.
    # Deshalb hier ausgeliefert statt unter der gehashten Asset-URL, und bewusst ohne
    # langes Caching: ein festgenagelter Service-Worker wäre kaum wieder loszuwerden.
    a = _ASSETS.get("js/sw.js")
    return Response(a["body"] if a else b"", mimetype="application/javascript",
                    headers={"Cache-Control": "no-cache"})

@app.route("/api/push/pubkey")
@login_required
def api_push_pubkey():
    vp = ensure_vapid()
    return jsonify({"enabled": bool(vp), "key": (vp or {}).get("pub_b64", "")})

@app.route("/api/push/subscribe", methods=["POST"])
@login_required
def api_push_subscribe():
    sub = request.get_json(force=True)
    if not sub or not sub.get("endpoint"): return jsonify({"error": "bad"}), 400
    u = session.get("user", ""); d = load_push(); lst = d.get(u, [])
    if not any(x.get("endpoint") == sub["endpoint"] for x in lst): lst.append(sub)
    d[u] = lst; save_push(d)
    return jsonify({"ok": True})

@app.route("/api/push/unsubscribe", methods=["POST"])
@login_required
def api_push_unsubscribe():
    ep = (request.get_json(force=True) or {}).get("endpoint", "")
    u = session.get("user", ""); d = load_push()
    d[u] = [x for x in d.get(u, []) if x.get("endpoint") != ep]; save_push(d)
    return jsonify({"ok": True})

@app.route("/api/push/test", methods=["POST"])
@login_required
def api_push_test():
    send_push_to_user(session.get("user", ""), "Romseerr", "Test-Benachrichtigung / test notification")
    return jsonify({"ok": True})

@app.route("/api/apikey", methods=["GET"])
@admin_required
def api_apikey_get():
    return jsonify({"apikey": get_apikey()})

@app.route("/api/apikey/regenerate", methods=["POST"])
@admin_required
def api_apikey_regen():
    s = load_settings(); s["apikey"] = secrets.token_hex(16); save_settings(s)
    return jsonify({"apikey": s["apikey"]})

@app.route("/api/setup", methods=["POST"])
def api_setup():
    if load_users(): return jsonify({"ok":False,"msg":"bereits eingerichtet"}), 400
    d = request.get_json(force=True); u=(d.get("username") or "").strip(); p=d.get("password") or ""
    if not u or len(p)<6: return jsonify({"ok":False,"msg":"Benutzername + Passwort (min. 6 Zeichen)"}), 400
    save_users({u: {"pw":generate_password_hash(p), "role":"admin"}})
    session.permanent=True; session["user"]=u; session["role"]="admin"
    return jsonify({"ok":True})

# Einfaches In-RAM-Rate-Limit gegen Passwort-Bruteforce: max. LOGIN_MAX Fehlversuche je
# (IP, Benutzer) im gleitenden Fenster LOGIN_WINDOW, danach LOGIN_MAX weitere = HTTP 429.
LOGIN_FAILS = {}
LOGIN_WINDOW = 300     # Sekunden
LOGIN_MAX = 8          # erlaubte Fehlversuche im Fenster
def _rl_key(user):
    ip = (request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
          or request.remote_addr or "?")
    return f"{ip}|{(user or '').lower()}"
def login_blocked(user):
    now = time.time(); k = _rl_key(user)
    LOGIN_FAILS[k] = [t for t in LOGIN_FAILS.get(k, []) if now - t < LOGIN_WINDOW]
    return len(LOGIN_FAILS[k]) >= LOGIN_MAX
def login_fail(user):
    LOGIN_FAILS.setdefault(_rl_key(user), []).append(time.time())
def login_ok(user):
    LOGIN_FAILS.pop(_rl_key(user), None)

@app.route("/api/login", methods=["POST"])
def api_login():
    d = request.get_json(force=True); u=(d.get("username") or "").strip(); p=d.get("password") or ""
    if login_blocked(u):
        return jsonify({"ok":False,"msg":"Zu viele Fehlversuche — bitte kurz warten / too many attempts"}), 429
    usr = load_users().get(u)
    if usr and check_password_hash(usr["pw"], p):
        login_ok(u)
        session.permanent=True; session["user"]=u; session["role"]=usr.get("role","user")
        return jsonify({"ok":True,"role":session["role"]})
    login_fail(u)
    return jsonify({"ok":False,"msg":"Falsche Zugangsdaten"}), 401

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear(); return jsonify({"ok":True})

@app.route("/api/users", methods=["GET"])
@perm_required("manage_users")
def api_users_list():
    return jsonify([{"username":u,"role":v.get("role","user"),"perms":v.get("perms",[])}
                    for u,v in load_users().items()])

@app.route("/api/users", methods=["POST"])
@perm_required("manage_users")
def api_users_add():
    d = request.get_json(force=True); u=(d.get("username") or "").strip(); p=d.get("password") or ""
    role = "admin" if d.get("role")=="admin" else "user"
    if not u or len(p)<6: return jsonify({"ok":False,"msg":"Benutzername + Passwort (min. 6 Zeichen)"}), 400
    # Nur Admins dürfen einen Admin anlegen oder privilegierte Rechte vergeben.
    if role == "admin" and not caller_is_admin():
        return jsonify({"ok":False,"msg":"nur Admin darf Admins anlegen / admin only"}), 403
    users = load_users()
    if u in users: return jsonify({"ok":False,"msg":"Benutzer existiert bereits"}), 400
    perms = [x for x in (d.get("perms") or ["request"]) if x in PERMS]
    if not caller_is_admin(): perms = [x for x in perms if x not in PRIV_PERMS]
    users[u] = {"pw":generate_password_hash(p), "role":role, "perms":perms}
    save_users(users)
    return jsonify({"ok":True})

@app.route("/api/users/<u>", methods=["PATCH"])
@perm_required("manage_users")
def api_users_patch(u):
    users = load_users()
    if u not in users: return jsonify({"ok":False}), 404
    d = request.get_json(force=True)
    if "perms" in d:
        newp = [x for x in (d.get("perms") or []) if x in PERMS]
        if not caller_is_admin():
            # Nicht-Admins dürfen privilegierte Rechte weder vergeben noch entziehen:
            # bestehende privilegierte Rechte bewahren, neue nicht zulassen.
            cur = users[u].get("perms", [])
            newp = [x for x in newp if x not in PRIV_PERMS] + [x for x in cur if x in PRIV_PERMS]
        users[u]["perms"] = newp
    if "autoapprove" in d: users[u]["autoapprove"] = bool(d["autoapprove"])
    if d.get("role") in ("admin","user") and d["role"] != users[u].get("role"):
        if not caller_is_admin():
            return jsonify({"ok":False,"msg":"nur Admin darf Rollen ändern / admin only"}), 403
        admins = [x for x,v in users.items() if v.get("role")=="admin"]
        if users[u].get("role")=="admin" and d["role"]!="admin" and len(admins)<=1:
            return jsonify({"ok":False,"msg":"letzter Admin"}), 400
        users[u]["role"] = d["role"]
    fehler = speichere_nutzer_http(users)
    return fehler or jsonify({"ok":True})

# ---- Einstellungen (Benachrichtigungen) ----
@app.route("/api/settings", methods=["GET"])
@admin_required
def api_settings_get():
    s = load_settings(); sm = s.get("smtp", {})
    return jsonify({"discord": s.get("discord", {"enabled": False, "url": ""}),
                    "general": s.get("general", {"app_name": "Romseerr", "default_lang": "de", "default_design": "seerr"}),
                    "smtp": {"enabled": bool(sm.get("enabled")), "host": sm.get("host",""),
                             "port": sm.get("port","587"), "user": sm.get("user",""),
                             "from": sm.get("from",""), "tls": sm.get("tls","starttls"),
                             "has_pass": bool(sm.get("pass"))},
                    "agents": {
                        "telegram": {"enabled": bool(s.get("agents",{}).get("telegram",{}).get("enabled")),
                                     "chat": s.get("agents",{}).get("telegram",{}).get("chat",""),
                                     "has_token": bool(s.get("agents",{}).get("telegram",{}).get("token"))},
                        "webhook": {"enabled": bool(s.get("agents",{}).get("webhook",{}).get("enabled")),
                                    "url": s.get("agents",{}).get("webhook",{}).get("url","")},
                        "email": {"enabled": bool(s.get("agents",{}).get("email",{}).get("enabled"))},
                        "gotify": {"enabled": bool(s.get("agents",{}).get("gotify",{}).get("enabled")),
                                   "url": s.get("agents",{}).get("gotify",{}).get("url",""),
                                   "has_token": bool(s.get("agents",{}).get("gotify",{}).get("token"))},
                        "ntfy": {"enabled": bool(s.get("agents",{}).get("ntfy",{}).get("enabled")),
                                 "url": s.get("agents",{}).get("ntfy",{}).get("url",""),
                                 "topic": s.get("agents",{}).get("ntfy",{}).get("topic",""),
                                 "has_token": bool(s.get("agents",{}).get("ntfy",{}).get("token"))},
                        "pushover": {"enabled": bool(s.get("agents",{}).get("pushover",{}).get("enabled")),
                                     "user": s.get("agents",{}).get("pushover",{}).get("user",""),
                                     "has_token": bool(s.get("agents",{}).get("pushover",{}).get("token"))}},
                    "quota": s.get("quota", {"enabled": False, "count": 10, "days": 7}),
                    "onboarded": bool(s.get("onboarded")),
                    "update_check": bool(s.get("update_check", True)),
                    "allow_private_webhooks": bool(s.get(_PRIVATE_OK_KEY)),
                    "variant": variant_prefs(), "variant_regions": list(REGIONS),
                    "connections": {**{k: cfg(k) for k in CONN_KEYS if k not in CONN_SECRET},
                                    **{"has_"+k: bool(cfg(k)) for k in CONN_SECRET}}})

@app.route("/api/settings", methods=["POST"])
@admin_required
def api_settings_set():
    d = request.get_json(force=True); s = load_settings()
    if "discord" in d:
        dc = d["discord"]; s["discord"] = {"enabled": bool(dc.get("enabled")), "url": (dc.get("url") or "").strip()}
    if "general" in d:
        g = d["general"]
        s["general"] = {"app_name": (g.get("app_name") or "Romseerr")[:40],
                        "default_lang": g.get("default_lang") if g.get("default_lang") in LANGS else "de",
                        "default_design": g.get("default_design") if g.get("default_design") in DESIGNS else "seerr"}
    if "smtp" in d:
        m = d["smtp"]; cur = s.get("smtp", {})
        s["smtp"] = {"enabled": bool(m.get("enabled")), "host": (m.get("host") or "").strip(),
                     "port": str(m.get("port") or "587"), "user": (m.get("user") or "").strip(),
                     "from": (m.get("from") or "").strip(), "tls": m.get("tls") or "starttls",
                     "pass": m.get("pass") if m.get("pass") else cur.get("pass", "")}
    if "agents" in d:
        a = d["agents"]; cur = s.get("agents", {}); s.setdefault("agents", {})
        if "telegram" in a:
            tg = a["telegram"]
            s["agents"]["telegram"] = {"enabled": bool(tg.get("enabled")), "chat": (tg.get("chat") or "").strip(),
                "token": tg.get("token") if tg.get("token") else cur.get("telegram",{}).get("token","")}
        if "webhook" in a:
            gw = a["webhook"]
            s["agents"]["webhook"] = {"enabled": bool(gw.get("enabled")), "url": (gw.get("url") or "").strip()}
        if "email" in a:
            s["agents"]["email"] = {"enabled": bool(a["email"].get("enabled"))}
        if "gotify" in a:
            gt = a["gotify"]
            s["agents"]["gotify"] = {"enabled": bool(gt.get("enabled")), "url": (gt.get("url") or "").strip(),
                "token": gt.get("token") if gt.get("token") else cur.get("gotify",{}).get("token","")}
        if "ntfy" in a:
            nt = a["ntfy"]
            s["agents"]["ntfy"] = {"enabled": bool(nt.get("enabled")), "url": (nt.get("url") or "").strip(),
                "topic": (nt.get("topic") or "").strip(),
                "token": nt.get("token") if nt.get("token") else cur.get("ntfy",{}).get("token","")}
        if "pushover" in a:
            po = a["pushover"]
            s["agents"]["pushover"] = {"enabled": bool(po.get("enabled")), "user": (po.get("user") or "").strip(),
                "token": po.get("token") if po.get("token") else cur.get("pushover",{}).get("token","")}
    if "quota" in d:
        qq = d["quota"]
        s["quota"] = {"enabled": bool(qq.get("enabled")), "count": int(qq.get("count") or 10),
                      "days": int(qq.get("days") or 7)}
    if "connections" in d:
        cn = d["connections"]; s.setdefault("connections", {})
        for k in CONN_KEYS:
            if k not in cn: continue
            v = cn[k]
            if k in CONN_SECRET:
                if v: s["connections"][k] = v          # Secret nur bei neuem Wert überschreiben
            else:
                s["connections"][k] = (v or "").strip()  # leer = Env-Default nutzen
    if "onboarded" in d: s["onboarded"] = bool(d["onboarded"])
    if "update_check" in d: s["update_check"] = bool(d["update_check"])
    if _PRIVATE_OK_KEY in d: s[_PRIVATE_OK_KEY] = bool(d[_PRIVATE_OK_KEY])
    if "variant" in d: s["variant"] = sanitize_variant_prefs(d["variant"])
    save_settings(s); return jsonify({"ok": True})

# ---------- Konfiguration exportieren / importieren ----------
# Eine Dateisicherung der SQLite-DB schützt gegen Plattenverlust, aber nicht gegen die drei
# Fälle, um die es hier geht: Umzug auf einen neuen Host, Prüfbarkeit (eine Sicherung, die
# nie zurückgespielt wurde, ist eine Vermutung) und selektives Wiederherstellen.
EXPORT_SCHEMA = 1
REDACTED = "__REDACTED__"   # Platzhalter für ausgelassene Geheimnisse: „vorhanden, aber nicht im Dokument"

def _path_get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d: return None
        d = d[k]
    return d

def _path_set(d, path, val):
    for k in path[:-1]:
        if not isinstance(d.get(k), dict): d[k] = {}
        d = d[k]
    d[path[-1]] = val

def secret_paths(settings):
    """Pfade zu Geheimnissen im settings-Baum. Dynamisch ermittelt, weil Agenten und
    Verbindungen wachsen — eine feste Liste würde beim nächsten Agenten stillschweigend
    ein Kennwort im Klartext exportieren."""
    paths = [("apikey",), ("smtp", "pass"), ("discord", "url"), ("agents", "webhook", "url")]
    for agent in (settings.get("agents") or {}):
        paths.append(("agents", agent, "token"))
    paths += [("connections", k) for k in CONN_SECRET]
    return paths

def _fernet(passphrase, salt, iterations):
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes as _h
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    kdf = PBKDF2HMAC(algorithm=_h.SHA256(), length=32, salt=salt, iterations=iterations)
    return Fernet(base64.urlsafe_b64encode(kdf.derive(passphrase.encode())))

def build_export(passphrase=""):
    """Versioniertes, lesbares Export-Dokument bauen.

    Geheimnisse sind standardmäßig **nicht** enthalten — ein Export ist eine Datei, die
    herumgereicht und an Nachrichten gehängt wird. An ihrer Stelle steht REDACTED, damit
    der Import „war gesetzt, kenne ich aber nicht" von „war leer" unterscheiden kann.
    Mit Passphrase werden sie stattdessen verschlüsselt beigelegt (PBKDF2 + Fernet)."""
    settings = json.loads(json.dumps(load_settings()))   # tiefe Kopie, Original nie anfassen
    users = json.loads(json.dumps(load_users()))
    stash = {}
    for p in secret_paths(settings):
        v = _path_get(settings, p)
        if v not in (None, ""):
            stash["settings." + ".".join(p)] = v
            _path_set(settings, p, REDACTED)
    for name, u in users.items():
        for field in ("pw", "webhook"):
            if u.get(field):
                stash[f"users.{name}.{field}"] = u[field]
                u[field] = REDACTED
    with JOBS_LOCK:
        jobs = json.loads(json.dumps(JOBS))
    doc = {"schema": EXPORT_SCHEMA, "app": "romseerr", "version": VERSION,
           "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "settings": settings, "users": users, "requests": jobs,
           "wishlist": load_wishlist(), "secrets": {"mode": "omitted"}}
    if passphrase:
        salt = os.urandom(16); iterations = 200_000
        token = _fernet(passphrase, salt, iterations).encrypt(json.dumps(stash).encode())
        doc["secrets"] = {"mode": "encrypted", "cipher": "fernet", "kdf": "pbkdf2-sha256",
                          "iterations": iterations, "salt": base64.b64encode(salt).decode(),
                          "data": token.decode()}
    return doc

def _restore_secrets(doc, passphrase):
    """Verschlüsselte Geheimnisse zurückholen -> (stash, fehlermeldung). Kein Werfen:
    kein Ausnahmetext soll je in eine Antwort geraten."""
    sec = doc.get("secrets") or {}
    if sec.get("mode") != "encrypted": return {}, ""
    if not passphrase: return None, "Passphrase fehlt / passphrase missing"
    try:
        f = _fernet(passphrase, base64.b64decode(sec["salt"]), int(sec.get("iterations") or 200_000))
        return json.loads(f.decrypt(sec["data"].encode()).decode()), ""
    except Exception as e:
        log(f"Import-Entschluesselung: {e}")
        return None, "Passphrase falsch oder Daten beschädigt / wrong passphrase or corrupt data"

def _unredact(value, current):
    """REDACTED heißt „behalte, was da ist" — auch im replace-Modus. Ein Export ohne
    Geheimnisse darf beim Zurückspielen nicht den laufenden API-Key wegwischen."""
    return current if value == REDACTED else value

def apply_import(doc, mode, passphrase=""):
    """Dokument übernehmen. `mode` muss der Aufrufer ausdrücklich wählen:
    `replace` ersetzt den jeweiligen Bereich vollständig, `merge` legt ihn darüber.

    Gibt `(counts, fehlermeldung)` zurück statt zu werfen: die Meldungen sind bewusste,
    für Nutzer geschriebene Texte — kein Ausnahmetext soll je in eine Antwort geraten."""
    if not isinstance(doc, dict) or doc.get("app") != "romseerr":
        return None, "kein Romseerr-Export / not a Romseerr export"
    schema = doc.get("schema")
    if not isinstance(schema, int):
        return None, "Schema-Version fehlt / schema version missing"
    if schema > EXPORT_SCHEMA:
        return None, (f"Schema {schema} ist neuer als diese Version (max {EXPORT_SCHEMA}) — "
                      f"bitte Romseerr aktualisieren / newer than this build, please update")
    if schema < 1:
        return None, f"Schema {schema} wird nicht unterstützt / unsupported"
    if mode not in ("merge", "replace"):
        return None, "mode muss 'merge' oder 'replace' sein / must be 'merge' or 'replace'"
    stash, err = _restore_secrets(doc, passphrase)
    if err: return None, err
    counts = {}

    if isinstance(doc.get("settings"), dict):
        cur = load_settings()
        new = json.loads(json.dumps(doc["settings"]))
        for p in secret_paths(new):
            v = _path_get(new, p)
            if v is None: continue
            key = "settings." + ".".join(p)
            _path_set(new, p, _unredact(stash.get(key, v), _path_get(cur, p)))
        if mode == "merge":
            merged = json.loads(json.dumps(cur))
            def deep(a, b):
                for k, v in b.items():
                    if isinstance(v, dict) and isinstance(a.get(k), dict): deep(a[k], v)
                    else: a[k] = v
            deep(merged, new); new = merged
        save_settings(new); counts["settings"] = 1

    if isinstance(doc.get("users"), dict):
        cur = load_users()
        new = json.loads(json.dumps(doc["users"]))
        for name, u in new.items():
            for field in ("pw", "webhook"):
                if field in u:
                    u[field] = _unredact(stash.get(f"users.{name}.{field}", u[field]),
                                         (cur.get(name) or {}).get(field, ""))
        result = new if mode == "replace" else {**cur, **new}
        # Ein Import darf niemanden aussperren: ohne Admin (mit Kennwort) wäre die Instanz tot.
        if not any(u.get("role") == "admin" and u.get("pw") for u in result.values()):
            return None, ("Import würde keinen Administrator mit Kennwort hinterlassen / "
                          "would leave no admin with a password")
        save_users(result); counts["users"] = len(result)

    if isinstance(doc.get("wishlist"), dict):
        cur = load_wishlist()
        if mode == "replace":
            save_wishlist(doc["wishlist"])
        else:
            for user, lst in doc["wishlist"].items():
                have = {(norm(e.get("title", "")), e.get("platform") or "") for e in cur.get(user, [])}
                for e in (lst or []):
                    if (norm(e.get("title", "")), e.get("platform") or "") not in have:
                        cur.setdefault(user, []).append(e)
            save_wishlist(cur)
        counts["wishlist"] = sum(len(v) for v in load_wishlist().values())

    if isinstance(doc.get("requests"), list):
        with JOBS_LOCK:
            if mode == "replace":
                JOBS[:] = doc["requests"]
            else:
                known = {j.get("id") for j in JOBS}
                JOBS.extend(j for j in doc["requests"] if j.get("id") not in known)
            save_jobs()
            counts["requests"] = len(JOBS)
    return counts, ""

@app.route("/api/export")
@admin_required
def api_export():
    """Export ohne Geheimnisse (GET). Für einen Export MIT verschlüsselten Geheimnissen
    gibt es POST — die Passphrase gehört nicht in eine URL (Logs, Verlauf, Referrer)."""
    return jsonify(build_export())

@app.route("/api/export", methods=["POST"])
@admin_required
def api_export_post():
    d = request.get_json(force=True, silent=True) or {}
    pw = d.get("passphrase") or ""
    if d.get("secrets") == "encrypt":
        if len(pw) < 8:
            return jsonify({"ok": False, "msg": "Passphrase zu kurz (min. 8) / passphrase too short"}), 400
        try:
            import cryptography  # noqa: F401
        except ImportError:
            return jsonify({"ok": False, "msg": "cryptography fehlt — Geheimnisse können nicht "
                                                "verschlüsselt werden / not available"}), 501
    else:
        pw = ""
    return jsonify(build_export(pw))

@app.route("/api/import", methods=["POST"])
@admin_required
def api_import():
    d = request.get_json(force=True, silent=True) or {}
    doc = d.get("document")
    if doc is None: doc = d if "schema" in d else None
    try:
        counts, err = apply_import(doc, d.get("mode"), d.get("passphrase") or "")
    except Exception as e:
        log(f"Import-Fehler: {e}")
        return jsonify({"ok": False, "msg": "Import fehlgeschlagen / failed"}), 500
    if err:
        return jsonify({"ok": False, "msg": err}), 400
    log(f"Konfiguration importiert ({d.get('mode')}): {counts}")
    return jsonify({"ok": True, "mode": d.get("mode"), "counts": counts})

@app.route("/api/settings/connections/reveal")
@admin_required
def api_conn_reveal():
    """Klartext-Werte aller Verbindungseinstellungen (nur Admin) für die Anzeige in der UI."""
    return jsonify({k: cfg(k) for k in CONN_KEYS})

# ---------- HTTPS / TLS: Zertifikat über die Oberfläche hinterlegen ----------
def tls_info():
    """Status des hinterlegten Zertifikats (ohne den privaten Schlüssel je auszugeben)."""
    s = load_settings().get("tls", {}) or {}
    info = {"enabled": bool(s.get("enabled")), "port": int(s.get("port") or 8443),
            "has_cert": os.path.exists(TLS_CERT) and os.path.exists(TLS_KEY), "cn": "", "expires": ""}
    if info["has_cert"]:
        try:
            from cryptography import x509
            crt = x509.load_pem_x509_certificate(open(TLS_CERT, "rb").read())
            try: info["cn"] = crt.subject.rfc4514_string()
            except Exception: pass
            exp = getattr(crt, "not_valid_after_utc", None) or crt.not_valid_after
            info["expires"] = exp.strftime("%Y-%m-%d")
        except Exception as e:
            log(f"Mail-Test: {e}"); info["error"] = err_kind(e)
    return info

def _tls_validate(cert, key):
    """Cert+Key parsen und prüfen, dass sie zusammenpassen (ssl-Kontext). Wirft bei Fehler."""
    import ssl, tempfile
    cp = kp = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f: f.write(cert); cp = f.name
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f: f.write(key); kp = f.name
        ssl.create_default_context(ssl.Purpose.CLIENT_AUTH).load_cert_chain(cp, kp)
    finally:
        for p in (cp, kp):
            if p:
                try: os.remove(p)
                except Exception: pass

@app.route("/api/settings/tls")
@admin_required
def api_tls_get():
    return jsonify(tls_info())

@app.route("/api/settings/tls", methods=["POST"])
@admin_required
def api_tls_set():
    d = request.get_json(force=True)
    cert = (d.get("cert") or "").strip(); key = (d.get("key") or "").strip()
    try: port = int(d.get("port") or 8443)
    except (TypeError, ValueError): port = 8443
    if not (1 <= port <= 65535): port = 8443
    enabled = bool(d.get("enabled"))
    if cert or key:
        if not (cert and key):
            return jsonify({"ok": False, "msg": "Zertifikat UND Schlüssel nötig / need both"}), 400
        try:
            _tls_validate(cert, key)
        except Exception as e:
            # Der Text von load_cert_chain kann Dateipfade enthalten -> nur ins Log.
            log(f"TLS-Upload ungueltig: {e}")
            return jsonify({"ok": False, "msg": "Zertifikat oder Schlüssel ungültig / "
                                                "certificate or key invalid"}), 400
        os.makedirs(TLS_DIR, exist_ok=True)
        # Ueber schreibe_geheim, nicht open()+chmod: dazwischen laege die Datei mit den
        # Rechten der umask auf der Platte, und ein privater Schluessel soll gar nicht
        # erst so entstehen. (#192)
        schreibe_geheim(TLS_CERT, cert)
        schreibe_geheim(TLS_KEY, key)
        log("TLS-Zertifikat aktualisiert (Neustart nötig zum Aktivieren)")
    s = load_settings(); s["tls"] = {"enabled": enabled, "port": port}; save_settings(s)
    return jsonify({"ok": True, "restart": True, **tls_info()})

@app.route("/api/settings/tls/remove", methods=["POST"])
@admin_required
def api_tls_remove():
    for p in (TLS_CERT, TLS_KEY):
        try: os.remove(p)
        except Exception: pass
    s = load_settings(); s["tls"] = {"enabled": False, "port": int((s.get("tls") or {}).get("port") or 8443)}
    save_settings(s)
    return jsonify({"ok": True})

# Beim Start gesammelte Erreichbarkeitswarnungen (siehe check_config). Bewusst NICHT
# live geprüft: dafür müsste jeder Aufruf der Oberfläche fremde Dienste anfragen.
START_WARN = []

def storage_state():
    """Kann Romseerr schreiben, wo es schreiben MUSS? Prüft mit einem echten Schreibversuch.

    `os.access` beantwortet die Frage nicht: auf eingehängten Dateisystemen und bei ACLs
    liefert es die Auskunft des Verzeichnisbits, nicht das Ergebnis. Und die Frage stellt
    sich hier scharf — das Abbild läuft als uid 1000, der eingehängte Ordner kommt vom
    Betreiber und gehört im Zweifel jemand anderem.

    Vorgeschichte: 18 Stunden lang beantwortete Romseerr jede Anfrage, lieferte die ganze
    Oberfläche und meldete `healthy`, während **nichts** gespeichert wurde — die Datenbank
    war schreibgeschützt. Lesen ging, und alles, was jemand ansieht, ist Lesen. (#216)"""
    zustand = {"dir": True, "db": True, "reason": ""}
    probe = os.path.join(CONFIG_DIR, ".schreibprobe")
    try:
        with open(probe, "w") as f: f.write("x")
        os.remove(probe)
    except Exception as e:
        zustand["dir"] = False; zustand["reason"] = f"{CONFIG_DIR}: {e.__class__.__name__}"
    try:
        with closing(db_conn()) as c:
            # Eine echte Transaktion. `PRAGMA quick_check` liest nur und ginge auch
            # schreibgeschützt glatt durch — genau die beruhigende Zahl, die hier täuscht.
            c.execute("CREATE TABLE IF NOT EXISTS _rw_probe(x INTEGER)")
            c.execute("DROP TABLE _rw_probe")
            c.commit()
    except Exception as e:
        zustand["db"] = False
        zustand["reason"] = (zustand["reason"] + "; " if zustand["reason"] else "") + \
                            f"{DB_FILE}: {e.__class__.__name__}"
    zustand["ok"] = zustand["dir"] and zustand["db"]
    return zustand

def config_warnings():
    """Konfigurationsprobleme, die einen ganzen Weg lahmlegen — für die Oberfläche.

    Zwei Herkünfte mit Absicht: Dateisystemprüfungen (JDownloader-Übergabe) laufen LIVE,
    weil sie nichts kosten und sich zwischendurch ändern können; Erreichbarkeit stammt aus
    dem Startlauf, weil sie fremde Dienste anfragt.

    Anlass: die Übergabe an JDownloader war unbenutzbar, die Warnung stand achtmal im
    Logfile — und in der Oberfläche sagte nichts, dass Downloads gar nicht erst starten
    können. Ein Fehler, den nur das Log kennt, ist für Benutzer kein Fehler, sondern
    unerklärliches Verhalten. (#197)"""
    w = [dict(x) for x in START_WARN]
    # Zuerst, weil alles andere davon abhängt: was nicht gespeichert werden kann, ist
    # verloren, egal wie gut der Rest läuft. (#216)
    st = storage_state()
    if not st["ok"]:
        w.append({"key": "storage", "reason": "readonly",
                  "text": f"Es kann nichts gespeichert werden / nothing can be stored — {st['reason']}",
                  "fix": f"{CONFIG_DIR} muss der uid {os.getuid()} gehören oder für sie "
                         f"beschreibbar sein / must be writable by uid {os.getuid()}"})
    jd = jd_check()
    if not jd["ok"]:
        w.append({"key": "jd", "reason": jd["reason"],
                  "text": f"JDownloader-Übergabe / hand-off — {jd['info']}",
                  "fix": jd.get("fix", "")})
    return w

@app.route("/api/config/warnings")
@perm_required("manage_settings")
def api_config_warnings():
    return jsonify({"warnings": config_warnings()})

@app.route("/api/jd/probe", methods=["POST"])
@perm_required("manage_settings")
def api_jd_probe():
    """Die Uebergabe an JDownloader wirklich ausprobieren. (#218)

    Bewusst POST und bewusst nicht Teil von `/api/services/status`: der Lauf dauert
    Sekunden und hinterlaesst einen deaktivierten Eintrag im Linksammler.
    """
    d = request.get_json(silent=True) or {}
    try:
        wartezeit = min(120, max(5, int(d.get("wait") or 30)))
    except (TypeError, ValueError):
        wartezeit = 30
    return jsonify(jd_probe(wartezeit))

@app.route("/api/play/cores")
@perm_required("manage_settings")
def api_play_cores():
    """Prueft je spielbarer Plattform, ob der Player den Kern wirklich mitbringt. (#124)

    PLAYABLE ordnet jedem Slug einen EmulatorJS-Kern zu, aber ob der im **eingesetzten**
    RomM-Bau existiert, stand nirgends — und `intellivision` zeigte auf `freeintv`, das
    dort mit 404 antwortet. Das war ein Play-Knopf, der nicht funktionieren konnte, und
    von aussen sah er aus wie jeder andere.

    Geprueft wird per HEAD auf die Kerndatei; 200 heisst vorhanden, 404 heisst fehlend.
    Kein Download, kein Start.

    EN: PLAYABLE maps slugs to EmulatorJS cores, but nothing checked whether the deployed
    RomM build actually ships them. One entry pointed at a core answering 404.
    """
    basis = (cfg("romm_url") or "").rstrip("/")
    if not basis:
        return jsonify({"error": "RomM nicht konfiguriert / not configured"}), 400
    aus, fehlend = [], 0
    for slug, kern in sorted(PLAYABLE.items()):
        da = False
        for muster in (f"/assets/emulatorjs/data/cores/{kern}-wasm.data",
                       f"/assets/emulatorjs/data/cores/{kern}-thread-wasm.data"):
            try:
                if requests.head(basis + muster, timeout=8).status_code == 200:
                    da = True; break
            except Exception:
                pass
        if not da: fehlend += 1
        aus.append({"platform": slug, "core": kern, "available": da})
    return jsonify({"cores": aus, "missing": fehlend, "ok": fehlend == 0})

@app.route("/api/usenet/check")
@perm_required("manage_settings")
def api_usenet_check():
    """Den Usenet-Weg durchmessen, OHNE etwas herunterzuladen. (#196)

    Der Bericht „Usenet geht nicht" konnte drei verschiedene Dinge bedeuten — leere Suche,
    abgelehnter NZB, nicht eingesammelter Download —, und von aussen sahen alle drei gleich
    aus. Das war der eigentliche Defekt: eine Kette ohne Messpunkte. Hier ist jede Stufe
    einzeln beantwortet.

    Der Ordner-Vergleich am Ende ist die Lehre aus #197: Romseerr und SABnzbd sehen
    denselben Ordner unter verschiedenen Namen, und wenn die Sichten auseinanderlaufen,
    laeuft der Download durch und wird trotzdem nie gefunden. Ein Automat kann die beiden
    Namensraeume nicht vergleichen — beide Sichten nebeneinander kann ein Mensch."""
    schritte = []
    def schritt(name, ok, info): schritte.append({"step": name, "ok": bool(ok), "info": info})

    # 1. Suche
    treffer = []
    try:
        treffer = search_usenet("mario", cfg("prow_cats"), limit=10)
        schritt("search", bool(treffer),
                f"{len(treffer)} Treffer / results"
                + ("" if treffer else f" — Kategorien: {cfg('prow_cats') or '—'}"))
    except Exception as e:
        schritt("search", False, err_kind(e))

    # 2. SABnzbd: erreichbar, nicht pausiert, Kategorie vorhanden
    kat = (cfg("sab_cat") or "").strip()
    try:
        j = requests.get(f"{cfg('sab_url')}/api", params={"mode": "get_cats", "output": "json",
                         "apikey": cfg("sab_apikey")}, timeout=10).json()
        kats = j.get("categories") or []
        schritt("category", (not kat) or kat in kats,
                f"{kat or '—'} in [{', '.join(map(str, kats)) or '—'}]")
        q = requests.get(f"{cfg('sab_url')}/api", params={"mode": "queue", "output": "json",
                         "apikey": cfg("sab_apikey")}, timeout=10).json().get("queue", {})
        schritt("queue", not q.get("paused"),
                "pausiert / paused" if q.get("paused") else f"{q.get('noofslots', 0)} in der Warteschlange")
    except Exception as e:
        schritt("category", False, err_kind(e)); schritt("queue", False, err_kind(e))

    # 3. Einsammelordner — beide Sichten nebeneinander, damit ein Mensch sie vergleichen kann
    sab_sicht = ""
    try:
        c = (requests.get(f"{cfg('sab_url')}/api", params={"mode": "get_config", "output": "json",
             "apikey": cfg("sab_apikey")}, timeout=10).json().get("config") or {})
        ziel = (c.get("misc") or {}).get("complete_dir", "")
        unter = next((x.get("dir") for x in (c.get("categories") or []) if x.get("name") == kat), "")
        sab_sicht = "/".join(p for p in [str(ziel).rstrip("/"), str(unter or "").strip("/")] if p)
    except Exception as e:
        sab_sicht = f"({err_kind(e)})"
    schritt("collect", os.path.isdir(SAB_DONE),
            f"Romseerr: {SAB_DONE} · SABnzbd: {sab_sicht or '—'}")

    # 4. Liefert jeder Indexer ueberhaupt NZB-Dateien aus? (#236)
    #
    # Die vier Stufen oben koennen komplett gruen sein, waehrend jeder Download scheitert:
    # ein Indexer, der Treffer liefert, aber auf die Download-Adresse mit seiner eigenen
    # HTML-Seite antwortet, ist von hier aus sonst unsichtbar. Genau das war der Fall —
    # ein Indexer stellte 94 % der Treffer und keine einzige NZB. Unterschieden wird das
    # an einem einzigen Header.
    #
    # Ein Abruf zaehlt bei den meisten Indexern als „grab" gegen ein Stundenlimit, deshalb
    # hoechstens einer je Indexer und nur auf ausdruecklichen Aufruf — nie im Hintergrund.
    if treffer:
        # Feldnamen von search_usenet: der Indexer steht in `extra`, die Adresse in `ref`.
        # Prowlarrs Rohnamen (`indexer`/`downloadUrl`) gibt es hier nicht mehr — genau die
        # standen hier zuerst, und beide Seiten der Naht waren im Test so gemockt, dass sie
        # sich gegenseitig bestaetigten. (#238)
        proben = {}
        for t in treffer:
            proben.setdefault(t.get("extra") or "?", []).append(t)
        for name, ts in proben.items():
            url = (ts[0].get("ref") or "").strip()
            anteil = f"{len(ts)}/{len(treffer)} Treffer"
            if not url:
                schritt(f"indexer:{name}", False, f"{anteil} · keine Download-Adresse")
                continue
            try:
                r = requests.get(url, timeout=45, stream=True)
                kopf = next(r.iter_content(400), b"") or b""
                r.close()
                ct = (r.headers.get("content-type") or "").lower()
                ist_nzb = "nzb" in ct or b"<nzb" in kopf
                schritt(f"indexer:{name}", ist_nzb,
                        f"{anteil} · liefert {ct.split(';')[0] or '—'}"
                        + ("" if ist_nzb else "  ← keine NZB-Datei / not an NZB"))
            except Exception as e:
                schritt(f"indexer:{name}", False, f"{anteil} · {err_kind(e)}")

    return jsonify({"steps": schritte, "ok": all(s["ok"] for s in schritte)})

@app.route("/api/services/status")
@admin_required
def api_services_status():
    out = []
    try:
        j = requests.get(f"{cfg("sab_url")}/api", params={"mode":"version","output":"json","apikey":cfg("sab_apikey")}, timeout=6).json()
        out.append({"name":"SABnzbd","ok":True,"info":"v"+str(j.get("version",""))})
    except Exception as e: out.append({"name":"SABnzbd","ok":False,"info":err_kind(e)})
    try:
        r = requests.get(f"{cfg("prow_url")}/api/v1/system/status", headers={"X-Api-Key":cfg("prow_apikey")}, timeout=6)
        out.append({"name":"Prowlarr","ok":r.ok,"info":"v"+str(r.json().get("version",""))})
    except Exception as e: out.append({"name":"Prowlarr","ok":False,"info":err_kind(e)})
    try:
        r = requests.get(f"{cfg("romm_url")}/api/heartbeat", timeout=6)
        out.append({"name":"RomM","ok":r.ok,"info":"erreichbar"})
    except Exception as e: out.append({"name":"RomM","ok":False,"info":err_kind(e)})
    out.append({"name":"IGDB","ok":bool(igdb_token()),"info":"Cover / Discover"})
    if cfg("sgdb_key"):
        try:
            r = requests.get("https://www.steamgriddb.com/api/v2/search/autocomplete/mario",
                             headers={"Authorization":"Bearer "+cfg("sgdb_key")}, timeout=6)
            out.append({"name":"SteamGridDB","ok":r.ok,"info":"Cover-Fallback"})
        except Exception as e: out.append({"name":"SteamGridDB","ok":False,"info":err_kind(e)})
    if cfg("ss_user"):
        out.append({"name":"ScreenScraper","ok":True,"info":"Zugang hinterlegt / configured"})
    # JDownloader hat keine API in diesem Aufbau — geprueft wird die Ordner-Uebergabe. (#83)
    # Und genau so heisst die Zeile auch: „JDownloader ❌" liest sich als „das Programm
    # laeuft nicht" und schickte die Fehlersuche zweimal an den falschen Ort — der
    # Downloader lief die ganze Zeit, unbenutzbar war der Uebergabe-Ordner. (#204)
    jd = jd_check()
    out.append({"name":"JDownloader-Übergabe / hand-off","ok":jd["ok"],
                "info":jd["info"] + (f" — {jd['fix']}" if jd.get("fix") else "")})
    out.append({"name":"Archive.org","ok":True,"info":"public API"})
    return jsonify(out)

@app.route("/api/settings/notify-test", methods=["POST"])
@admin_required
def api_settings_test():
    d = request.get_json(silent=True) or {}; dc = d.get("discord") or {}
    if dc.get("url"):
        ok_url, why = url_allowed(dc["url"])
        if not ok_url:
            return jsonify({"ok": False, "msg": URL_REFUSED.get(why, "abgelehnt / refused")}), 400
        try:
            safe_post(dc["url"], json={"content":"✅ Romseerr — Testbenachrichtigung / test notification"})
            return jsonify({"ok": True})
        except Exception as e:
            log(f"Discord-Test: {e}")
            return jsonify({"ok": False, "msg": err_kind(e)}), 400
    ok = notify_send("✅ Romseerr — Testbenachrichtigung / test notification")
    return jsonify({"ok": ok, "msg": "" if ok else "kein Webhook konfiguriert"})

# ---- Freigabe-Workflow ----
@app.route("/api/jobs/<jid>/approve", methods=["POST"])
@perm_required("manage_requests")
def api_job_approve(jid):
    j = get_job(jid)
    if not j or j.get("state") != "pending": return jsonify({"ok": False}), 400
    set_state(jid, state="queued", msg="freigegeben"); Q.put(jid)
    return jsonify({"ok": True})

@app.route("/api/jobs/<jid>/deny", methods=["POST"])
@perm_required("manage_requests")
def api_job_deny(jid):
    if not get_job(jid): return jsonify({"ok": False}), 404
    set_state(jid, state="denied", msg="abgelehnt")
    return jsonify({"ok": True})

ESKALATION_AB = 3      # ab diesem Versuch die Quelle wechseln, statt sie zu wiederholen

def alternative_quelle(job):
    """Einen Treffer fuer DENSELBEN Titel aus einer anderen Quelle. (#200)

    Der Titelvergleich laeuft ueber `norm()` — dieselbe Normalisierung wie die Dedup.
    Streng ist hier Absicht: ein Wechsel, der ein anderes Spiel holt, waere schlimmer als
    der Fehlschlag, den er beheben soll. Lieber „alle Quellen versucht" melden, als etwas
    Falsches einzusortieren.
    """
    ziel = norm(job.get("title", ""))
    if not ziel: return None
    versucht = set(job.get("tried_sources") or []) | {job.get("source")}
    plat = job.get("platform")
    try:
        treffer = do_search(job.get("title", ""), [plat] if plat else None)
    except Exception as e:
        log(f"Quellenwechsel {job.get('id')}: Suche fehlgeschlagen — {err_kind(e)}")
        return None
    for r in treffer:
        if r.get("source") in versucht: continue
        if (r.get("gkey") or norm(r.get("title", ""))) != ziel: continue
        return r
    return None

@app.route("/api/jobs/<jid>/retry", methods=["POST"])
@perm_required("manage_requests")
def api_job_retry(jid):
    """Erneut versuchen — und ab dem dritten Mal ueber eine ANDERE Quelle. (#200)

    Vorher setzte der Knopf nur den Zustand zurueck und stellte denselben Auftrag erneut
    ein. Wer dreimal drueckt, wartet dreimal auf dieselbe Meldung: eine Quelle, die einen
    Titel nicht liefert, liefert ihn auch beim vierten Mal nicht — der Artikel ist
    unvollstaendig, der Indexer veraltet oder die Kategorie falsch, und nichts davon
    bessert sich durch Warten. Die anderen Quellen scheitern unabhaengig davon, ein
    Wechsel ist also der einzige Versuch, der neue Information traegt.
    """
    j = get_job(jid)
    if not j: return jsonify({"ok": False}), 404
    if j.get("state") not in ("error", "denied"):
        return jsonify({"ok": False, "msg": "nur fehlgeschlagene/abgelehnte / only failed/denied"}), 400

    versuch = int(j.get("tries") or 1) + 1          # der urspruengliche Lauf war Versuch 1
    versucht = [x for x in dict.fromkeys((j.get("tried_sources") or []) + [j.get("source")]) if x]
    felder = {"tries": versuch, "tried_sources": versucht}

    if versuch >= ESKALATION_AB:
        alt = alternative_quelle(j)
        if not alt:
            # Nicht wieder einstellen: sonst dreht sich derselbe Fehlschlag im Kreis, und
            # „nichts hat funktioniert" laese sich weiterhin wie „eines ist kaputt".
            set_state(jid, state="error", msg=f"alle Quellen versucht / all sources tried "
                                              f"({', '.join(versucht) or '—'})", **felder)
            return jsonify({"ok": False, "exhausted": True,
                            "msg": "alle Quellen versucht / all sources tried",
                            "tried": versucht}), 409
        felder.update(source=alt["source"], ref=alt["ref"])
        meldung = f"{versuch}. Versuch über {alt['source']} / attempt via {alt['source']}"
    else:
        meldung = f"{versuch}. Versuch / attempt {versuch}"

    set_state(jid, state="queued", msg=meldung, **felder)
    Q.put(jid)
    return jsonify({"ok": True, "tries": versuch, "source": (get_job(jid) or {}).get("source")})

@app.route("/api/jobs/<jid>/reimport", methods=["POST"])
@perm_required("manage_requests")
def api_job_reimport(jid):
    """Den liegengebliebenen Download erneut einlesen — ohne ihn neu zu holen. (#245)

    Abgrenzung zu `/retry`: das laedt die Ausgabe komplett neu. Hier liegen die Daten
    bereits auf der Platte, und genau dafuer hebt #240 sie auf — 2 GB erneut zu ziehen,
    weil eine Endung falsch erkannt wurde, waere das Gegenteil davon.

    Laeuft im Hintergrund: das Einsortieren kopiert unter Umstaenden Gigabytes, und eine
    HTTP-Anfrage, die dabei ins Timeout laeuft, sagt dem Aufrufer nichts ueber den Ausgang.
    """
    j = get_job(jid)
    if not j: return jsonify({"ok": False, "msg": "unbekannt / unknown"}), 404
    if j.get("state") != "error":
        return jsonify({"ok": False, "msg": "nur fehlgeschlagene / only failed"}), 400
    cand = find_output(SAB_DONE, jid) or find_output(jd_out_dir(), jid)
    if not cand:
        return jsonify({"ok": False, "msg": "keine Dateien mehr da / files are gone"}), 404
    job = dict(j)
    threading.Thread(target=lambda: einsortieren(jid, job, cand), daemon=True).start()
    log(f"Job {jid}: erneutes Einlesen angestossen ({cand})")
    return jsonify({"ok": True, "path": os.path.basename(cand)})

@app.route("/api/users/<u>", methods=["DELETE"])
@perm_required("manage_users")
def api_users_del(u):
    users = load_users()
    if u not in users: return jsonify({"ok":False,"msg":"unbekannt"}), 404
    if u == session.get("user"): return jsonify({"ok":False,"msg":"nicht sich selbst"}), 400
    admins = [x for x,v in users.items() if v.get("role")=="admin"]
    if users[u].get("role")=="admin" and len(admins)<=1:
        return jsonify({"ok":False,"msg":"letzter Admin"}), 400
    users.pop(u,None)
    fehler = speichere_nutzer_http(users)
    return fehler or jsonify({"ok":True})

# ---------- OpenAPI / API-Dokumentation ----------
# Einzige Quelle der Wahrheit. Ausgeliefert unter /api/openapi.json, gerendert unter /api/docs.
# docs/openapi.yaml im Repo wird daraus per scripts/build_openapi.py erzeugt.
_SEC = [{"cookieAuth": []}, {"apiKeyHeader": []}, {"apiKeyQuery": []}]   # Session ODER API-Key
_PUB = []                                                               # kein Auth (öffentlich)

def _op(summary, tag, security=None, params=None, body=None, responses=None):
    """Eine Operation der Spezifikation.

    ZWEI DINGE PASSIEREN HIER AUTOMATISCH, weil sie sonst an 43 Stellen einzeln stehen
    muessten und genau deshalb gefehlt haben (#328):

    1. **200 geht nie verloren.** Frueher ERSETZTE ein `responses=`-Argument die Vorgabe.
       Wer nur einen Fehlerfall ergaenzen wollte (`responses=_R_PERM`), loeschte damit
       stillschweigend den Erfolgsfall — `/api/stream/status` dokumentierte am Ende nur
       403 und keine einzige gelungene Antwort.
    2. **401 wird ergaenzt, sobald die Operation nicht oeffentlich ist.** `login_required`
       gibt fuer `/api/`-Pfade 401 zurueck; das stand in seinem Docstring und in keiner
       Operation. Wer einen Client aus der Spezifikation erzeugt, behandelte damit den
       haeufigsten Fehlerfall ueberhaupt nicht.

    Ausdruecklich uebergebene Werte gewinnen — die Automatik ergaenzt nur, was fehlt.

    Two things happen automatically because doing them by hand at 43 call sites is exactly
    why they were missing: the 200 is never dropped by a `responses=` argument, and 401 is
    added for every non-public operation. Explicit values still win.
    """
    antworten = {"200": {"description": "OK"}}
    antworten.update(responses or {})
    sicherheit = _SEC if security is None else security
    if sicherheit:
        antworten.setdefault("401", _R_AUTH["401"])
    o = {"summary": summary, "tags": [tag], "responses": antworten}
    o["security"] = sicherheit
    if params: o["parameters"] = params
    if body: o["requestBody"] = {"content": {"application/json": {"schema": body}}}
    return o

_R_AUTH = {"401": {"description": "nicht angemeldet / not authenticated"}}
_R_PERM = {"403": {"description": "fehlende Berechtigung / missing permission"}}
_qp = lambda n, d: {"name": n, "in": "query", "required": False, "schema": {"type": "string"}, "description": d}
_pp = lambda n, d: {"name": n, "in": "path", "required": True, "schema": {"type": "string"}, "description": d}

OPENAPI = {
    "openapi": "3.1.0",
    "info": {
        "title": "Romseerr API",
        "version": VERSION,
        "description": "Selbstgehostete Seerr-artige ROM-Suche & -Anfrage. / Self-hosted "
                       "Seerr-style ROM search & request. Auth per Session-Cookie oder API-Key "
                       "(Header `X-Api-Key` bzw. Query `?apikey=`; API-Key = Admin-äquivalent).",
        "license": {"name": "MIT"},
    },
    "servers": [{"url": "/", "description": "dieselbe Herkunft / same origin"}],
    "tags": [
        {"name": "System", "description": "Health, Auth-Status, PWA-Assets"},
        {"name": "Auth", "description": "Ersteinrichtung, Login/Logout, Passwort-Reset"},
        {"name": "Search", "description": "Suche, Discover, Detail, Cover, Plattformen"},
        {"name": "Requests", "description": "Downloads/Anfragen (Jobs) + Freigabe"},
        {"name": "Issues", "description": "Problemmeldungen + Kommentare"},
        {"name": "Messages", "description": "Private Direktnachrichten zwischen Nutzern"},
        {"name": "Profile", "description": "Eigenes Profil, Passwort, Benachrichtigungen"},
        {"name": "Push", "description": "Web-Push-Abos"},
        {"name": "Admin", "description": "Benutzer, Einstellungen, Sperrliste, Logs, Wartung, API-Key"},
        {"name": "Docs", "description": "diese Spezifikation"},
    ],
    "components": {
        "securitySchemes": {
            "cookieAuth": {"type": "apiKey", "in": "cookie", "name": "session"},
            "apiKeyHeader": {"type": "apiKey", "in": "header", "name": "X-Api-Key"},
            "apiKeyQuery": {"type": "apiKey", "in": "query", "name": "apikey"},
        }
    },
    "paths": {
        # --- System ---
        "/health": {"get": _op("Liveness-Probe (Titelzahl, Jobs) samt Speicherzustand "
                               "(storage: rw/ro — ro heißt: es wird nichts gespeichert) und "
                               "lib_failed/lib_failed_platforms: Plattformordner, die beim letzten "
                               "Indexlauf nicht lesbar waren — über 0 ist lib_titles unvollständig",
                               "System", _PUB)},
        "/api/version": {"get": _op("Laufende Version, Commit und Bauzeitpunkt (optional Update-Abgleich)", "System", _PUB,
            params=[_qp("check", "1 = zusätzlich gegen den Release-Feed prüfen (latest, update_available)")])},
        "/metrics": {"get": _op("Betriebsmetriken im Prometheus-Textformat (Auth wie API)", "System",
            responses={**_R_AUTH, "200": {"description": "text/plain; version=0.0.4"}})},
        "/api/auth/status": {"get": _op("Anmelde-/Setup-Status, App-Name, Version", "System", _PUB)},
        "/manifest.webmanifest": {"get": _op("PWA-Manifest", "System", _PUB)},
        "/sw.js": {"get": _op("Service-Worker", "System", _PUB)},
        "/icon.svg": {"get": _op("App-Icon", "System", _PUB)},
        "/assets/{h}/{rel}": {"get": _op("Statische Datei unter inhaltsgehashter URL (immutable)", "System", _PUB,
            params=[_pp("h", "Inhaltshash"), _pp("rel", "Pfad unter static/")],
            responses={"200": {"description": "Datei"}, "404": {"description": "unbekannt oder falscher Hash"}})},
        "/": {"get": _op("Web-Oberfläche (HTML)", "System", _SEC)},
        "/login": {"get": _op("Login-Seite (HTML)", "System", _PUB)},
        "/reset": {"get": _op("Passwort-Reset-Seite (HTML)", "System", _PUB)},
        # --- Auth ---
        "/api/setup": {"post": _op("Ersten Admin anlegen (nur solange kein Nutzer existiert)", "Auth", _PUB,
            body={"type": "object", "required": ["username", "password"],
                  "properties": {"username": {"type": "string"}, "password": {"type": "string"},
                                 "display_name": {"type": "string"}}})},
        "/api/login": {"post": _op("Anmelden (Session-Cookie)", "Auth", _PUB,
            body={"type": "object", "required": ["username", "password"],
                  "properties": {"username": {"type": "string"}, "password": {"type": "string"}}},
            responses={"200": {"description": "OK"}, "401": {"description": "falsche Zugangsdaten"}})},
        "/api/logout": {"post": _op("Abmelden", "Auth")},
        "/api/forgot": {"post": _op("Passwort-Reset per E-Mail anstoßen (generische Antwort)", "Auth", _PUB,
            body={"type": "object", "properties": {"user": {"type": "string", "description": "Benutzername oder E-Mail"}}})},
        "/api/reset": {"post": _op("Passwort mit Token setzen", "Auth", _PUB,
            body={"type": "object", "required": ["token", "password"],
                  "properties": {"token": {"type": "string"}, "password": {"type": "string"}}})},
        # --- Search ---
        "/api/search": {"get": _op("ROMs suchen (Archive.org + Usenet), plattform-gefiltert", "Search",
            params=[_qp("q", "Suchbegriff"), _qp("platforms", "kommagetrennte Plattform-Slugs")],
            responses={**_R_AUTH, "200": {"description": "Trefferliste"}})},
        "/api/coverage": {"get": _op("Abdeckung je Plattform (besessen/bekannt/Prozent, mit Quelle und Stand)", "Search")},
        "/api/coverage/status": {"get": _op("Fortschritt eines laufenden Katalogabrufs", "Search")},
        "/api/catalog/status": {"get": _op("Filehoster-Katalogquellen: Stand, Anzahl, Fehler", "Search")},
        "/api/catalog/refresh": {"post": _op("Katalogquellen sofort neu holen", "Admin",
            responses={**_R_PERM, "200": {"description": "gestartet"},
                       "400": {"description": "keine Quelle hinterlegt"}})},
        "/api/ra/status": {"get": _op("RetroAchievements: indizierte Plattformen, Set-Zahl, Stand, nicht zugeordnete Slugs", "Search")},
        "/api/ra/refresh": {"post": _op("RetroAchievements: Set-Listen je Konsole neu holen (Hintergrundlauf)", "Admin",
            responses={**_R_PERM, "200": {"description": "gestartet"},
                       "400": {"description": "kein API-Key hinterlegt"},
                       "409": {"description": "Lauf bereits aktiv"}})},
        "/api/coverage/refresh": {"post": _op("Katalog-Momentaufnahme neu holen (Hintergrundlauf)", "Admin",
            body={"type": "object", "properties": {"slug": {"type": "string", "description": "nur diese Plattform; leer = alle"}}},
            responses={**_R_PERM, "200": {"description": "gestartet"},
                       "400": {"description": "keine Katalogquelle / IGDB nicht konfiguriert"},
                       "409": {"description": "Lauf bereits aktiv"}})},
        "/api/coverage/{slug}/missing": {"get": _op("Fehlende Titel einer Plattform (paginiert, filterbar)", "Search",
            params=[_pp("slug", "Plattform-Slug"), _qp("offset", "Versatz"), _qp("limit", "max. 500"),
                    _qp("q", "Textfilter")])},
        "/api/library/platforms": {"get": _op(
            "Eigene Bibliothek: Titelzahl je System, nach Hersteller gruppiert", "Search")},
        "/api/library/{slug}/titles": {"get": _op(
            "Vorhandene Titel einer Plattform (paginiert, filterbar)", "Search",
            params=[_pp("slug", "Plattform-Slug"), _qp("offset", "Versatz"),
                    _qp("limit", "max. 500"), _qp("q", "Textfilter")])},
        "/api/library/organize/status": {"get": _op(
            "Zustand der Bibliotheks-Umbauten: Fortschritt, Laufzeit, Restschätzung und "
            "die Protokolle samt Rückweg. Rein lesend — startet nichts.", "Admin",
            responses={**_R_AUTH, **_R_PERM, "200": {"description": "Stände je Laufart + Protokolle"}})},
        "/api/library/organize/run": {"post": _op(
            "Einen Bibliotheks-Umbau starten: `art` (voll|beiwerk), `trocken`, optional "
            "`plattform`. Lehnt ab, wenn bereits einer läuft — auch einen, der außerhalb "
            "gestartet wurde.", "Admin",
            responses={**_R_AUTH, **_R_PERM, "200": {"description": "gestartet"},
                       "400": {"description": "unzulässiger oder unbekannter Plattformname"},
                       "409": {"description": "es läuft bereits ein Umbau"}})},
        "/api/library/organize/stop": {"post": _op(
            "Einen aus dieser Instanz gestarteten Umbau anhalten", "Admin",
            responses={**_R_AUTH, **_R_PERM, "200": {"description": "angehalten"},
                       "409": {"description": "kein Lauf aus dieser Instanz"}})},
        "/api/discover": {"get": _op("Beliebte Titel (flach)", "Search")},
        "/api/discover/rows": {"get": _op("Startseiten-Reihen (beliebt je Konsole + je Genre)", "Search")},
        "/api/detail": {"get": _op("Detaildaten inkl. IGDB (Wertung, Screenshots, Ähnliches) + Dateien", "Search",
            params=[_qp("source", "archive|usenet"), _qp("ref", "Quell-Referenz"), _qp("title", "Titel")])},
        "/api/play": {"get": _op("Kann der Titel im Browser gespielt werden (RomM/EmulatorJS)?", "Search",
            params=[_qp("title", "Titel"), _qp("platform", "Plattform-Slug")],
            responses={**_R_PERM, "200": {"description": "playable + Grund/URL"},
                       "400": {"description": "kein Titel"}})},
        "/api/stream": {"get": _op("Ist der Titel streambar (Plattform ohne Browser-Kern)?", "Search",
            params=[_qp("title", "Titel"), _qp("platform", "Plattform-Slug")],
            responses={**_R_PERM, "400": {"description": "kein Titel angegeben / no title given"}})},
        "/api/stream/start": {"post": _op("Einzelplatz belegen und Titel auf dem Streaming-Host starten", "Requests",
            body={"type": "object", "required": ["title"],
                  "properties": {"title": {"type": "string"}, "platform": {"type": "string"}}},
            responses={**_R_PERM, "200": {"description": "gestartet"},
                       "409": {"description": "Platz belegt"}})},
        "/api/stream/stop": {"post": _op("Sitzung beenden (Inhaber oder manage_requests)", "Requests",
            responses={**_R_PERM, "200": {"description": "freigegeben"}})},
        "/api/stream/status": {"get": _op("Zustand des Einzelplatzes", "Requests", responses=_R_PERM)},
        "/api/stream/emulators": {"get": _op("Emulatoren auf dem Streaming-Host: Stand, Quelle, laufende Aktualisierung", "Admin",
            responses={**_R_PERM, "200": {"description": "Liste + Update-Zustand"},
                       "400": {"description": "kein Start-Dienst hinterlegt"},
                       "502": {"description": "Start-Dienst nicht erreichbar"}})},
        "/api/stream/emulators/catalog": {"get": _op("Installierbare und installierte Emulatoren des Streaming-Hosts", "Admin",
            responses={**_R_PERM, "200": {"description": "Katalog"},
                       "400": {"description": "kein Start-Dienst hinterlegt"},
                       "502": {"description": "Start-Dienst nicht erreichbar"}})},
        "/api/stream/emulators/install": {"post": _op("Einen Emulator auf dem Streaming-Host installieren", "Admin",
            body={"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}},
            responses={**_R_PERM, "200": {"description": "gestartet"},
                       "400": {"description": "kein Start-Dienst / unzulaessiger Name"},
                       "404": {"description": "nicht im Katalog"},
                       "409": {"description": "laeuft bereits"}})},
        "/api/stream/firmware": {"get": _op("Firmware-/BIOS-Zustand je Plattform auf dem Streaming-Host", "Admin",
            responses={**_R_PERM, "200": {"description": "Zustand je Plattform"},
                       "400": {"description": "kein Start-Dienst hinterlegt"},
                       "502": {"description": "Start-Dienst nicht erreichbar"}})},
        "/api/stream/firmware/upload": {"post": _op(
            "Eine BIOS-/Firmware-Datei zum Streaming-Host durchreichen (multipart, Feld 'file'). "
            "Romseerr speichert sie nicht.", "Admin",
            responses={**_R_PERM, "200": {"description": "eingespielt"},
                       "400": {"description": "keine Datei / unzulaessige Plattform oder Name"},
                       "413": {"description": "zu gross"},
                       "502": {"description": "Start-Dienst nicht erreichbar"}})},
        "/api/stream/firmware/vendor": {"post": _op(
            "Firmware beim Hersteller holen. Nur PS3 - Sony veroeffentlicht seine "
            "Systemsoftware selbst; fuer andere Plattformen gibt es keine berechtigte Quelle.",
            "Admin",
            body={"type": "object", "required": ["platform"],
                  "properties": {"platform": {"type": "string", "enum": ["ps3"]}}},
            responses={**_R_PERM, "200": {"description": "gestartet"},
                       "400": {"description": "kein Start-Dienst / keine Herstellerquelle"},
                       "409": {"description": "laeuft bereits"},
                       "502": {"description": "Start-Dienst nicht erreichbar"}})},
        "/api/stream/emulators/rollback": {"post": _op("Einen Emulator auf die vorige Fassung zuruecksetzen", "Admin",
            body={"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}},
            responses={**_R_PERM, "200": {"description": "zurueckgesetzt"},
                       "400": {"description": "kein Start-Dienst / unzulaessiger Name"},
                       "502": {"description": "Start-Dienst nicht erreichbar"}})},
        "/api/stream/emulators/update": {"post": _op("Emulatoren auf dem Streaming-Host aktualisieren (Hintergrundlauf)", "Admin",
            responses={**_R_PERM, "200": {"description": "gestartet"},
                       "409": {"description": "laeuft bereits"},
                       "502": {"description": "Start-Dienst nicht erreichbar"}})},
        "/api/cover": {"get": _op("Cover-URL zu einem Titel (lazy, via IGDB)", "Search",
            params=[_qp("title", "Titel")])},
        "/api/platforms": {"get": _op("Verfügbare Plattformen/Slugs", "Search")},
        # --- Requests / Jobs ---
        "/api/download": {"post": _op("ROM anfragen/herunterladen (Auto-Freigabe oder pending)", "Requests",
            body={"type": "object", "description": "Trefferobjekt aus /api/search bzw. /api/detail"},
            responses={**_R_AUTH, "200": {"description": "Job angelegt"}})},
        "/api/jobs": {"get": _op("Eigene Anfragen (Admin: alle) mit Status", "Requests")},
        "/api/favourites": {
            "get": _op("Favoriten des angemeldeten Nutzers", "User", responses={**_R_AUTH, "200": {"description": "Liste"}}),
            "post": _op("Titel zu den Favoriten hinzufügen", "User",
                body={"type": "object", "properties": {"title": {"type": "string"}, "platform": {"type": "string"}}},
                responses={**_R_AUTH, "200": {"description": "OK"}})},
        "/api/favourites/remove": {"post": _op("Titel aus den Favoriten entfernen", "User",
            body={"type": "object", "properties": {"title": {"type": "string"}}},
            responses={**_R_AUTH, "200": {"description": "OK"}})},
        "/api/titlemeta": {"get": _op("Eigene Bewertung, die der anderen und Kommentare zu einem Titel", "User",
            params=[_qp("title", "Titel")], responses={**_R_AUTH, "200": {"description": "OK"}})},
        "/api/titlemeta/rating": {"post": _op("Eigene Bewertung setzen (1–5, 0 löscht)", "User",
            body={"type": "object", "properties": {"title": {"type": "string"}, "stars": {"type": "integer"}}},
            responses={**_R_AUTH, "200": {"description": "OK"}})},
        "/api/titlemeta/comment": {"post": _op("Kommentar zu einem Titel schreiben", "User",
            body={"type": "object", "properties": {"title": {"type": "string"}, "text": {"type": "string"}}},
            responses={**_R_AUTH, "200": {"description": "OK"}})},
        "/api/play/cores": {"get": _op("Je spielbarer Plattform pruefen, ob der EmulatorJS-Kern "
            "im eingesetzten RomM-Bau wirklich ausgeliefert wird (HEAD, kein Download)", "Admin",
            responses={**_R_PERM, "200": {"description": "Liste mit `available` je Plattform"},
                       "400": {"description": "RomM nicht konfiguriert"}})},
        "/api/jd/probe": {"post": _op("Die JDownloader-Uebergabe ausprobieren: eine wirkungslose "
            "`.crawljob` ablegen und pruefen, ob sie abgeholt wird. Dauert Sekunden und "
            "hinterlaesst einen deaktivierten Eintrag im Linksammler", "Admin",
            responses={**_R_PERM, "200": {"description": "Ergebnis mit `reason` und `fix`"}})},
        "/api/usenet/check": {"get": _op("Den Usenet-Weg stufenweise durchmessen, ohne etwas zu laden "
                                        "(Suche, SAB-Kategorie, Warteschlange, Einsammelordner)", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/logos": {"get": _op("Welche Logos der Betreiber hinterlegt hat (Dateinamen ohne Endung). "
                                  "Im Repo liegt bewusst keines — Konsolenlogos sind Marken.", "System", _PUB)},
        "/logo/{name}": {"get": _op("Ein hinterlegtes Logo ausliefern", "System", _PUB,
            params=[{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}])},
        "/api/wishlist": {
            "get": _op("Eigene Wunschliste (vorgemerkte, noch nicht verfügbare Titel)", "Requests"),
            "post": _op("Titel auf die Wunschliste setzen (Auto-Download, sobald verfügbar)", "Requests",
                body={"type": "object", "required": ["title"],
                      "properties": {"title": {"type": "string"}, "platform": {"type": "string"}}},
                responses={**_R_AUTH, "200": {"description": "vorgemerkt"}})},
        "/api/wishlist/import": {"post": _op(
            "Wunschliste aus Liste/Datei einspielen — ohne `confirm` nur Vorschau, mit `confirm` schreiben",
            "Requests",
            body={"type": "object",
                  "properties": {"text": {"type": "string", "description": "Rohtext, ein Titel je Zeile (optional `Titel;Plattform`)"},
                                 "confirm": {"type": "boolean", "description": "true = die bestätigten `entries` schreiben"},
                                 "entries": {"type": "array", "description": "nur mit confirm: bestätigte Einträge",
                                             "items": {"type": "object", "properties": {"title": {"type": "string"},
                                                                                        "platform": {"type": "string"}}}}},
                  },
            responses={**_R_PERM, "200": {"description": "Vorschau bzw. Ergebnis"},
                       "413": {"description": "Liste zu groß"}})},
        "/api/wishlist/example.csv": {"get": _op("Beispieldatei im erwarteten Importformat", "Requests")},
        "/api/wishlist/remove": {"post": _op("Titel von der Wunschliste entfernen", "Requests",
            body={"type": "object", "required": ["title"],
                  "properties": {"title": {"type": "string"}, "platform": {"type": "string"}}},
            responses={**_R_AUTH, "200": {"description": "entfernt"}})},
        "/api/jobs/{jid}/approve": {"post": _op("Anfrage freigeben", "Requests",
            params=[_pp("jid", "Job-ID")], responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/jobs/{jid}/deny": {"post": _op("Anfrage ablehnen", "Requests",
            params=[_pp("jid", "Job-ID")], responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/jobs/{jid}/retry": {"post": _op("Fehlgeschlagene/abgelehnte Anfrage erneut versuchen", "Requests",
            params=[_pp("jid", "Job-ID")], responses={**_R_PERM, "200": {"description": "erneut eingereiht"}})},
        "/api/jobs/{jid}/retry": {"post": _op("Erneut versuchen; ab dem dritten Versuch ueber "
            "eine andere Quelle. 409 mit `exhausted`, wenn keine Quelle mehr uebrig ist", "Requests",
            params=[{"name": "jid", "in": "path", "required": True, "schema": {"type": "string"}}],
            responses={**_R_PERM, "200": {"description": "eingestellt"},
                       "400": {"description": "falscher Zustand"},
                       "409": {"description": "alle Quellen versucht"}})},
        "/api/jobs/{jid}": {"delete": _op("Eine abgeschlossene Anfrage entfernen; mit "
            "`files: true` auch den liegengebliebenen Download. Die Antwort meldet mit "
            "`files_left`, ob Daten zurueckbleiben", "Requests",
            params=[{"name": "jid", "in": "path", "required": True, "schema": {"type": "string"}}],
            responses={**_R_PERM, "200": {"description": "entfernt"},
                       "400": {"description": "Anfrage laeuft noch"},
                       "404": {"description": "unbekannt"}})},
        "/api/jobs/{jid}/reimport": {"post": _op("Einen liegengebliebenen Download erneut "
            "einlesen, ohne ihn neu zu holen (nur Zustand `error`)", "Requests",
            params=[{"name": "jid", "in": "path", "required": True, "schema": {"type": "string"}}],
            responses={**_R_PERM, "200": {"description": "angestossen"},
                       "400": {"description": "falscher Zustand"},
                       "404": {"description": "unbekannt oder Dateien weg"}})},
        "/api/leftovers": {"get": _op("Downloads auflisten, die ein fehlgeschlagener Import "
            "liegen gelassen hat (Ordner, Groesse, Alter, zugehoeriger Auftrag)", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/leftovers/remove": {"post": _op("Liegengebliebene Downloads entfernen — "
            "einzeln per `jid` oder alle per `all: true`", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"},
                       "404": {"description": "nicht gefunden"}})},
        "/api/jobs/clear-finished": {"post": _op("Abgeschlossene Anfragen entfernen", "Requests",
            responses={**_R_PERM, "200": {"description": "entfernt"}})},
        # --- Issues ---
        "/api/issues": {
            "get": _op("Problemmeldungen (eigene; Admin: alle)", "Issues"),
            "post": _op("Problem melden", "Issues",
                body={"type": "object", "required": ["title"],
                      "properties": {"title": {"type": "string"}, "platform": {"type": "string"},
                                     "type": {"type": "string"}, "message": {"type": "string"}}})},
        "/api/issues/{iid}/comment": {"post": _op("Kommentar (Melder oder Staff)", "Issues",
            params=[_pp("iid", "Issue-ID")],
            body={"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}},
            responses={**_R_PERM, "200": {"description": "OK"}, "400": {"description": "leer"}})},
        "/api/issues/{iid}/close": {"post": _op("Problem schließen", "Issues",
            params=[_pp("iid", "Issue-ID")], responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/issues/{iid}": {"delete": _op("Problem löschen", "Issues",
            params=[_pp("iid", "Issue-ID")], responses={**_R_PERM, "200": {"description": "OK"}})},
        # --- Messages ---
        "/api/messages": {
            "get": _op("Eigene Direktnachrichten + Nutzerliste + ungelesen-Zähler", "Messages"),
            "post": _op("Nachricht an einen Nutzer senden", "Messages",
                body={"type": "object", "required": ["to", "body"],
                      "properties": {"to": {"type": "string"}, "body": {"type": "string"}}},
                responses={**_R_AUTH, "200": {"description": "gesendet"}, "400": {"description": "leer/Empfänger"}})},
        "/api/messages/read": {"post": _op("Nachrichten eines Absenders als gelesen markieren", "Messages",
            body={"type": "object", "properties": {"from": {"type": "string"}}})},
        # --- Profile ---
        "/api/profile": {
            "get": _op("Eigenes Profil", "Profile"),
            "post": _op("Profil ändern (Name, E-Mail, Sprache, Design, Avatar, persönl. Webhook)", "Profile",
                body={"type": "object", "properties": {
                    "display_name": {"type": "string"}, "email": {"type": "string"},
                    "lang": {"type": "string", "enum": ["", "de", "en", "fr", "es", "it"]},
                    "design": {"type": "string", "enum": ["", "seerr", "glass", "clean"]},
                    "avatar": {"type": "string", "description": "data-URI"}, "webhook": {"type": "string"}}})},
        "/api/profile/password": {"post": _op("Eigenes Passwort ändern", "Profile",
            body={"type": "object", "required": ["old", "new"],
                  "properties": {"old": {"type": "string"}, "new": {"type": "string"}}})},
        "/api/profile/notify-test": {"post": _op("Persönlichen Webhook testen", "Profile",
            body={"type": "object", "properties": {"url": {"type": "string"}}})},
        # --- Push ---
        "/api/push/pubkey": {"get": _op("VAPID-Public-Key + ob Push verfügbar", "Push")},
        "/api/push/subscribe": {"post": _op("Push-Abo speichern", "Push",
            body={"type": "object", "required": ["endpoint"], "description": "PushSubscription-JSON"})},
        "/api/push/unsubscribe": {"post": _op("Push-Abo entfernen", "Push",
            body={"type": "object", "properties": {"endpoint": {"type": "string"}}})},
        "/api/push/test": {"post": _op("Test-Push an sich selbst", "Push")},
        # --- Admin ---
        "/api/users": {
            "get": _op("Benutzer auflisten", "Admin", responses={**_R_PERM, "200": {"description": "Liste"}}),
            "post": _op("Benutzer anlegen", "Admin",
                body={"type": "object", "required": ["username", "password"],
                      "properties": {"username": {"type": "string"}, "password": {"type": "string"},
                                     "role": {"type": "string", "enum": ["user", "admin"]},
                                     "perms": {"type": "array", "items": {"type": "string"}}}},
                responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/users/{u}": {
            "patch": _op("Benutzer ändern (Rolle/Rechte/Auto-Freigabe)", "Admin", params=[_pp("u", "Benutzername")],
                body={"type": "object", "properties": {"role": {"type": "string"},
                      "perms": {"type": "array", "items": {"type": "string"}}, "autoapprove": {"type": "boolean"}}},
                responses={**_R_PERM, "200": {"description": "OK"}}),
            "delete": _op("Benutzer löschen", "Admin", params=[_pp("u", "Benutzername")],
                responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/settings": {
            "get": _op("Einstellungen (Discord, SMTP-Status, Quota, Agenten, general)", "Admin",
                responses={**_R_PERM, "200": {"description": "OK"}}),
            "post": _op("Einstellungen speichern", "Admin",
                body={"type": "object", "description": "Teil- oder Gesamtobjekt der Einstellungen"},
                responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/settings/mail-test": {"post": _op("Test-E-Mail senden", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/export": {
            "get": _op("Konfiguration exportieren (ohne Geheimnisse)", "Admin",
                       responses={**_R_PERM, "200": {"description": "versioniertes JSON-Dokument"}}),
            "post": _op("Konfiguration exportieren, Geheimnisse optional mit Passphrase verschlüsselt", "Admin",
                        body={"type": "object",
                              "properties": {"secrets": {"type": "string", "enum": ["omit", "encrypt"]},
                                             "passphrase": {"type": "string", "description": "min. 8 Zeichen, nur bei secrets=encrypt"}}},
                        responses={**_R_PERM, "200": {"description": "versioniertes JSON-Dokument"},
                                   "400": {"description": "Passphrase zu kurz"},
                                   "501": {"description": "Verschlüsselung nicht verfügbar"}})},
        "/api/import": {"post": _op("Konfiguration importieren (mode: merge|replace, ausdrücklich zu wählen)", "Admin",
            body={"type": "object", "required": ["document", "mode"],
                  "properties": {"document": {"type": "object", "description": "Export-Dokument"},
                                 "mode": {"type": "string", "enum": ["merge", "replace"]},
                                 "passphrase": {"type": "string", "description": "nötig, wenn der Export verschlüsselte Geheimnisse enthält"}}},
            responses={**_R_PERM, "200": {"description": "übernommen"},
                       "400": {"description": "Schema/Modus/Passphrase ungültig"}})},
        "/api/settings/connections/reveal": {"get": _op("Verbindungswerte im Klartext (Admin)", "Admin",
            responses={**_R_PERM, "200": {"description": "key->value"}})},
        "/api/settings/tls": {
            "get": _op("HTTPS/TLS-Status (CN, Ablauf, Port)", "Admin",
                responses={**_R_PERM, "200": {"description": "OK"}}),
            "post": _op("TLS-Zertifikat + Schlüssel hinterlegen (Neustart nötig)", "Admin",
                body={"type": "object", "properties": {"cert": {"type": "string", "description": "PEM"},
                      "key": {"type": "string", "description": "PEM"}, "port": {"type": "integer"},
                      "enabled": {"type": "boolean"}}},
                responses={**_R_PERM, "200": {"description": "gespeichert"}, "400": {"description": "ungültig"}})},
        "/api/settings/tls/remove": {"post": _op("TLS-Zertifikat entfernen", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/settings/notify-test": {"post": _op("Benachrichtigungs-Agenten testen", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/blocklist": {
            "get": _op("Sperrliste lesen", "Admin", responses={**_R_PERM, "200": {"description": "OK"}}),
            "post": _op("Sperrliste setzen", "Admin",
                body={"type": "object", "properties": {"blocklist": {"type": "array", "items": {"type": "string"}}}},
                responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/services/status": {"get": _op("Status angebundener Dienste (SAB, Prowlarr, RomM …)", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/config/warnings": {"get": _op("Konfigurationsprobleme, die einen ganzen Weg lahmlegen "
                                            "(JDownloader-Übergabe live, Erreichbarkeit aus dem Startlauf)", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/maillog": {"get": _op("Mail-Versand-Protokoll", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/logs": {"get": _op("Anwendungs-Log (letzte Zeilen)", "Admin",
            params=[_qp("n", "Anzahl Zeilen (max 1000)")], responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/admin/stats": {"get": _op("Laufzeit-Statistik (Jobs, Bibliothek, Cache)", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/admin/cache/clear": {"post": _op("IGDB-/Discover-Cache leeren", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/import/status": {"get": _op(
            "Stand des Einwurfordners — was einsortierbar ist und was nicht", "Import")},
        "/api/import/scan": {"post": _op(
            "Einwurfordner sofort einlesen (Admin)", "Import",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/admin/reindex": {"post": _op("Bibliotheks-Index neu aufbauen (Hintergrund)", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/apikey": {"get": _op("API-Key anzeigen", "Admin",
            responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/apikey/regenerate": {"post": _op("API-Key neu erzeugen", "Admin",
            responses={**_R_PERM, "200": {"description": "neuer Key"}})},
        # --- Docs ---
        "/api/openapi.json": {"get": _op("Diese OpenAPI-Spezifikation", "Docs", _PUB)},
        "/api/docs": {"get": _op("Interaktive API-Dokumentation (Redoc)", "Docs", _PUB)},
    },
}


@app.route("/api/openapi.json")
def api_openapi(): return jsonify(OPENAPI)

@app.route("/api/docs")
def api_docs(): return Response(render_page("redoc.html"), mimetype="text/html")

# ---------- Start ----------
# ---------- Liegengebliebene Downloads (#244) ----------
# Seit #240 bleibt ein Download liegen, den der Import nicht verwerten konnte. Das ist
# Absicht — aber niemand raeumt sie je weg, und niemand SIEHT sie ueberhaupt. Ein Ordner,
# von dem keiner weiss, ist nicht aufgehoben, sondern verloren.

def leftover_dirs():
    """Alle `romseerr_<jid>`-Ordner in den Sammelverzeichnissen, die zu KEINEM laufenden
    Auftrag mehr gehoeren — mit jid, Groesse, Alter und dem zugehoerigen Auftrag.

    Der Schutz sitzt hier und nicht beim Loeschen: ein Ordner, dessen Auftrag noch laeuft,
    taucht gar nicht erst in der Liste auf. Alter allein ist als Kriterium untauglich —
    ein grosser Download kann Stunden brauchen und sieht dabei alt aus.
    """
    aus = []
    laufend = {j["id"] for j in JOBS if j.get("state") in OFFENE_ZUSTAENDE}
    jobs = {j["id"]: j for j in JOBS}
    for basis in (SAB_DONE, jd_out_dir()):
        if not basis or not os.path.isdir(basis): continue
        try:
            with os.scandir(basis) as it:     # `with`, sonst bleibt der Deskriptor offen (#589)
                eintraege = list(it)
        except OSError:
            continue
        for e in eintraege:
            if not e.is_dir() or not e.name.startswith("romseerr_"): continue
            rest = e.name[len("romseerr_"):]
            jid = rest.split("__")[0].split("_")[0]
            if jid in laufend: continue          # gehoert einem laufenden Auftrag
            job = jobs.get(jid) or {}
            groesse, alter = 0, 0.0
            try:
                for wurzel, _, dateien in os.walk(e.path):
                    for d in dateien:
                        try: groesse += os.path.getsize(os.path.join(wurzel, d))
                        except OSError: pass
                alter = (time.time() - os.path.getmtime(e.path)) / 86400
            except OSError:
                pass
            aus.append({"jid": jid, "path": e.path, "name": e.name,
                        "size": groesse, "age_days": round(alter, 1),
                        "title": job.get("title", ""), "state": job.get("state", "")})
    return sorted(aus, key=lambda x: -x["age_days"])

def leftover_remove(pfad):
    """Einen liegengebliebenen Ordner loeschen — mit Sperre gegen alles ausserhalb.

    `rm -rf` auf einem Pfad, der aus einer Einstellung stammt, ist die eine Stelle, an der
    ein Denkfehler nicht rueckgaengig zu machen ist. Deshalb dreifach: aufgeloester Pfad
    (kein Symlink-Ausbruch), muss UNTERHALB eines Sammelordners liegen, und der Name muss
    das `romseerr_`-Praefix tragen.
    """
    if not pfad: return False, "kein Pfad"
    echt = os.path.realpath(pfad)
    if os.path.basename(echt).startswith("romseerr_") is False:
        return False, "kein Romseerr-Ordner"
    erlaubt = False
    for basis in (SAB_DONE, jd_out_dir()):
        if not basis: continue
        b = os.path.realpath(basis)
        if echt != b and echt.startswith(b.rstrip("/") + "/"):
            erlaubt = True; break
    if not erlaubt:
        return False, "ausserhalb der Sammelordner"
    if not os.path.isdir(echt):
        return False, "nicht vorhanden"
    try:
        subprocess.run(["rm", "-rf", echt], check=True)
        return True, ""
    except Exception as e:
        return False, err_kind(e)

def worker_leftovers():
    """Taeglich: liegengebliebene Ordner verfallen lassen, die aelter sind als die Frist.

    Die Frist muss lang genug sein, dass eine Korrektur und ein erneutes Einlesen
    hineinpassen — sonst raeumt die Automatik genau das weg, wofuer #240 die Daten
    aufgehoben hat. 0 schaltet sie ab.
    """
    while True:
        time.sleep(6 * 3600)
        beat("leftovers")
        try:
            tage = int(load_settings().get("leftover_days", 14) or 0)
        except (TypeError, ValueError):
            tage = 14
        if tage <= 0: continue
        weg, bytes_weg = 0, 0
        for e in leftover_dirs():
            if e["age_days"] < tage: continue
            ok, _ = leftover_remove(e["path"])
            if ok: weg += 1; bytes_weg += e["size"]
        if weg:
            log(f"{weg} liegengebliebene Downloads entfernt "
                f"({bytes_weg/1073741824:.1f} GB, aelter als {tage} Tage)")

def periodic_index():
    while True:
        time.sleep(600); beat("index"); build_index()

# --- Massenimport aus dem Einwurfordner (#396) --------------------------------------
#
# Der Zustand je Datei steht im RAM: Groesse und Aenderungszeit beim letzten Durchlauf.
# Er muss keinen Neustart ueberleben — nach einem Neustart wird eben einmal mehr gewartet,
# und das ist billiger als eine Datei, die halb kopiert importiert wird.
_EINWURF_GESEHEN = {}
EINWURF_TAKT = int(os.environ.get("IMPORT_SCAN_SEC", "300"))


def einwurf_stabil(pfad):
    """-> True, wenn Groesse UND Aenderungszeit seit dem letzten Durchlauf gleich sind.

    WARUM ZWEI DURCHLAEUFE statt einer Wartezeit: Ueber SMB dauert eine 5-GB-Kopie
    Minuten. Eine einzelne Pruefung muesste in der Schleife schlafen — entweder zu kurz,
    um wahr zu sein, oder sie blockiert alles andere. Zwei Durchlaeufe im Abstand des
    Taktes beantworten dieselbe Frage, ohne zu warten.

    Two passes rather than a sleep: an SMB copy takes minutes, and a single check would
    either be too short to be true or would block the loop.
    """
    try:
        st = os.stat(pfad)
    except OSError:
        _EINWURF_GESEHEN.pop(pfad, None)
        return False
    jetzt = (st.st_size, int(st.st_mtime))
    vorher = _EINWURF_GESEHEN.get(pfad)
    _EINWURF_GESEHEN[pfad] = jetzt
    return vorher == jetzt and st.st_size > 0


def einwurf_ziel(pfad, name):
    """-> (slug, grund). Leerer Slug heisst: liegen lassen und sagen warum.

    NICHT RATEN. Ein Download traegt seinen Plattform-Hinweis aus dem Auftrag; eine in den
    Share gelegte Datei traegt nichts. 25 der 82 anerkannten Endungen sind mehrdeutig —
    `.bin`, `.iso`, `.chd` liegen je auf einem Dutzend Systemen. Was sich nicht bestimmen
    laesst, bleibt sichtbar liegen, statt unter der falschen Konsole zu verschwinden.
    """
    ext, ziel = rom_endung(name)
    if not ext:
        return "", "kein ROM-Format"
    slug = EXT2PLAT.get(ext)
    if slug:
        return slug, f"Endung .{ext}"
    # Zweiter Weg: der Ordner, in dem die Datei liegt, kann die Plattform nennen.
    ordner = os.path.basename(os.path.dirname(pfad)).lower()
    if ordner and ordner != os.path.basename(IMPORT_SHARE).lower():
        aus_ordner = resolve_slug(FOLDER_ALIASES.get(ordner, ordner))
        if aus_ordner and aus_ordner in {v for v in EXT2PLAT.values()} | set(STREAMABLE):
            return aus_ordner, f"Ordner {ordner!r}"
    # Dritter Weg: der Titel selbst.
    aus_titel = guess_platform(name)
    if aus_titel:
        return aus_titel, "Titel"
    return "", f".{ext} ist mehrdeutig — Plattform nicht bestimmbar"


def einwurf_scannen(trocken=False):
    """Einen Durchlauf ueber den Einwurfordner. -> (eingeordnet, offen)."""
    if not os.path.isdir(IMPORT_SHARE):
        return [], []
    eingeordnet, offen = [], []
    for wurzel, dirs, dateien in os.walk(IMPORT_SHARE):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in dateien:
            if SKIP_FILES.search(fn) or fn.startswith("."):
                continue
            quelle = os.path.join(wurzel, fn)
            slug, grund = einwurf_ziel(quelle, fn)
            if not slug:
                offen.append({"datei": os.path.relpath(quelle, IMPORT_SHARE),
                              "grund": grund})
                continue
            if not einwurf_stabil(quelle):
                offen.append({"datei": os.path.relpath(quelle, IMPORT_SHARE),
                              "grund": "wird noch kopiert"})
                continue
            eingeordnet.append({"datei": os.path.relpath(quelle, IMPORT_SHARE),
                                "quelle": quelle, "slug": slug, "grund": grund})
    if trocken:
        return eingeordnet, offen
    fertig = []
    for e in eingeordnet:
        if einwurf_verschieben(e["quelle"], e["slug"]):
            fertig.append(e)
    return fertig, offen


def einwurf_verschieben(quelle, slug):
    """Datei in die Bibliothek verschieben. Erst kopieren, pruefen, DANN loeschen.

    Einwurfordner und Bibliothek liegen auf verschiedenen Dateisystemen — `os.rename`
    scheitert dort, und ein abgebrochenes Verschieben hinterliesse eine halbe Datei, die
    wie ein Titel aussieht. Deshalb: nach `.teil` kopieren, Groesse vergleichen, im Ziel
    umbenennen, und erst danach die Quelle entfernen.
    """
    name = os.path.basename(quelle)
    ziel_ordner = bibliothek_ordner(slug)     # nicht ROMS/<slug> — siehe #454
    try:
        os.makedirs(ziel_ordner, exist_ok=True)
        endgueltig = os.path.join(ziel_ordner, name)
        if os.path.exists(endgueltig):
            log(f"Einwurf: {name!r} liegt schon unter {slug}/ — Quelle bleibt")
            return False
        teil = endgueltig + ".teil"
        import shutil
        shutil.copyfile(quelle, teil)
        # Rechte vom ZIELORDNER erben, nicht fest setzen. Ohne das gehoert die Datei dem
        # Container-Benutzer, und RomM, RetroNAS und SMB koennen sie nicht bewegen —
        # derselbe Fall, den `baum_rechte_setzen` in den Bibliothekswerkzeugen abfaengt.
        #
        # WARUM GEERBT UND NICHT `0o664`: Ein fester Wert ist zweimal falsch. Er behauptet
        # zu wissen, wie diese Bibliothek eingerichtet ist — und Bandit meldet ihn zurecht
        # als B103, weil eine fest verdrahtete grosszuegige Maske im Quelltext nie zu
        # begruenden ist. Der Ordner daneben weiss es besser: Was fuer ihn gilt, gilt auch
        # fuer die Datei darin, nur ohne Ausfuehrungsrecht.
        try:
            ordner_modus = os.stat(ziel_ordner).st_mode & 0o777
            os.chmod(teil, ordner_modus & 0o666)
        except OSError:
            pass
        if os.path.getsize(teil) != os.path.getsize(quelle):
            os.remove(teil)
            raise OSError("Groesse nach dem Kopieren verschieden")
        os.replace(teil, endgueltig)
        # AB HIER IST DER TITEL DA. Was jetzt noch schiefgeht, kostet keine Daten — aber
        # es muss anders klingen als „nichts passiert". Am echten Share gemessen: Ein per
        # SMB angelegter Unterordner kann `755` sein, und der Container laeuft als uid 1000
        # in der Gruppe `users` — dann gelingt das Kopieren und das Loeschen der Quelle
        # nicht. Die Datei ist in der Bibliothek, liegt aber weiter im Einwurfordner.
        try:
            os.remove(quelle)
        except OSError as e:
            log(f"Einwurf: {name!r} ist unter {slug}/ angekommen, die Quelle liess sich "
                f"NICHT entfernen ({e.strerror}) — Rechte des Ordners pruefen")
            _EINWURF_GESEHEN.pop(quelle, None)
            return True          # angekommen ist angekommen
        _EINWURF_GESEHEN.pop(quelle, None)
        log(f"Einwurf: {name!r} -> {slug}/")
        return True
    except Exception as e:
        log(f"Einwurf-Fehler {name!r}: {e}")
        return False


def periodic_einwurf():
    """Hintergrundlauf. EIGENE Schleife, nicht an den Index gehaengt.

    Der Index laeuft ueber 127.000 Titel; darauf sollte kein Einwurf warten muessen.
    """
    while True:
        time.sleep(EINWURF_TAKT)
        try:
            beat("einwurf")
            fertig, _offen = einwurf_scannen()
            if fertig:
                build_index()
        except Exception as e:
            log(f"Einwurf-Lauf-Fehler: {e}")


def check_config():
    """Beim Start einmal prüfen und WARNEN (nicht fatal), wenn optionale Dienste fehlen oder
    nicht erreichbar sind — spart Rätselraten, warum z. B. keine Cover oder kein Usenet da sind.
    Läuft im Hintergrund, damit die Erreichbarkeitsprüfung den Start nicht verzögert.

    Die Erreichbarkeitsbefunde landen zusätzlich in `START_WARN`, weil sie sonst nur im
    Logfile stehen — und dorthin sieht niemand, dem gerade ein Download nicht ankommt. (#197)"""
    def reach(url):
        try: requests.get(url, timeout=4); return True
        except Exception: return False
    START_WARN.clear()
    def warn(key, text):
        log(f"Konfig-WARNUNG: {text}")
        START_WARN.append({"key": key, "text": text})
    # Die erste Frage beim Start, weil sie alle anderen entwertet: kann ich schreiben?
    # Nicht als Abbruch — ein sichtbarer Fehler nützt mehr als ein Dienst, der gar nicht
    # erst hochkommt und dessen Grund niemand sieht. (#216)
    st = storage_state()
    if not st["ok"]:
        log(f"Konfig-WARNUNG: SPEICHERN NICHT MÖGLICH / cannot store anything — {st['reason']}. "
            f"{CONFIG_DIR} muss für uid {os.getuid()} beschreibbar sein.")
    if not (cfg("igdb_id") and cfg("igdb_secret")):
        log("Konfig: IGDB nicht gesetzt — keine Cover/Discover.")
    if not (cfg("sab_url") and cfg("sab_apikey")):
        log("Konfig: SABnzbd nicht gesetzt — Usenet-Download aus.")
    elif not reach(cfg("sab_url")):
        warn("sab", f"SABnzbd ({cfg("sab_url")}) nicht erreichbar / not reachable.")
    # Erst heilen, dann melden: ein fehlender Ausgabeordner ist behebbar, ohne jemanden zu fragen.
    jd = jd_check(anlegen=True)
    if not jd["ok"]:
        log(f"Konfig-WARNUNG: JDownloader-Uebergabe — {jd['info']}")
    # --- Wirkt der Download-Proxy wirklich? (#346) --------------------------------
    # Nicht „ist er erreichbar" — sondern: kommt der Verkehr unter einer ANDEREN Adresse
    # heraus? Ein Proxy, der still auf den direkten Weg zurueckfaellt, ist erreichbar und
    # nutzlos zugleich, und genau das sieht man ihm nicht an.
    #
    # Die Adressen selbst werden NICHT protokolliert. Sie gehoeren niemandem ausser dem
    # Betreiber, und ein Logfile wandert schneller in einen Fehlerbericht als einem lieb
    # ist. Verglichen wird, gemeldet wird nur das Ergebnis des Vergleichs.
    #
    # Not "is it reachable" but "does traffic leave under a different address": a proxy
    # that silently falls back is reachable and useless at the same time. The addresses are
    # deliberately never logged — only the result of the comparison.
    if cfg("dl_proxy"):
        try:
            direkt = requests.get("https://api.ipify.org", timeout=6).text.strip()
            ueber = requests.get("https://api.ipify.org", timeout=10,
                                 proxies={"http": cfg("dl_proxy"),
                                          "https": cfg("dl_proxy")}).text.strip()
            if not ueber:
                warn("dlproxy", "Download-Proxy liefert keine Antwort — Downloads werden scheitern.")
            elif ueber == direkt:
                warn("dlproxy", "Download-Proxy ist erreichbar, aendert aber die "
                                "Austrittsadresse NICHT — der Verkehr laeuft ungeschuetzt.")
            else:
                log("Download-Proxy wirkt: Austrittsadresse unterscheidet sich.")
        except Exception as e:
            # Fail-closed: Ein gesetzter, aber unbrauchbarer Proxy laesst die Downloads
            # scheitern — das ist gewollt. Die Warnung sagt nur, warum.
            warn("dlproxy", f"Download-Proxy nicht nutzbar ({err_kind(e)}) — "
                            "Downloads ueber diesen Weg werden scheitern.")

    if not (cfg("prow_url") and cfg("prow_apikey")):
        log("Konfig: Prowlarr nicht gesetzt — Usenet-Suche aus.")
    elif not reach(cfg("prow_url")):
        warn("prow", f"Prowlarr ({cfg("prow_url")}) nicht erreichbar / not reachable.")

if __name__ == "__main__":
    os.makedirs(STAGING, exist_ok=True)
    geheimnisse_absichern()      # vor allem anderen: Rechte am Schluesselmaterial (#256)
    db_init(); load_jobs(); jobs_nach_neustart_aufraeumen()
    if load_index_from_db():
        log(f"Bibliotheks-Index aus DB geladen: {len(LIB['slugs'])} Plattformen, {len(LIB['all'])} Titel")
        threading.Thread(target=build_index, daemon=True).start()   # im Hintergrund auffrischen
    else:
        build_index()   # kein DB-Index -> erstmalig aus dem Dateisystem
    threading.Thread(target=worker_download, daemon=True).start()
    threading.Thread(target=worker_collect, daemon=True).start()
    threading.Thread(target=periodic_index, daemon=True).start()
    threading.Thread(target=periodic_einwurf, daemon=True).start()
    threading.Thread(target=check_config, daemon=True).start()
    threading.Thread(target=worker_wishlist, daemon=True).start()
    threading.Thread(target=worker_catalog, daemon=True).start()
    threading.Thread(target=worker_leftovers, daemon=True).start()
    threading.Thread(target=worker_wachhund, daemon=True).start()   # (#340)
    # Optionaler HTTPS-Listener (eigener Port), wenn ein Zertifikat hinterlegt & aktiviert ist.
    def _start_https():
        info = tls_info()
        if not (info["enabled"] and info["has_cert"]): return
        import ssl as _ssl
        try:
            ctx = _ssl.create_default_context(_ssl.Purpose.CLIENT_AUTH); ctx.load_cert_chain(TLS_CERT, TLS_KEY)
            log(f"HTTPS-Listener auf :{info['port']}")
            app.run(host="0.0.0.0", port=info["port"], threaded=True, ssl_context=ctx)  # nosec B104
        except Exception as e:
            log(f"HTTPS-Start-Fehler: {e}")
    threading.Thread(target=_start_https, daemon=True).start()
    log(f"Romseerr startet auf :{PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)  # nosec B104 - Container-Dienst, bindet bewusst alle Interfaces
