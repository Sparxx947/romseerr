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
import os, re, json, time, threading, queue, subprocess, urllib.parse, html, secrets, smtplib, base64, sqlite3
from collections import Counter
from datetime import datetime
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
_ENV_CONN = {"sab_url": SAB_URL, "sab_apikey": SAB_APIKEY, "sab_cat": SAB_CAT,
             "prow_url": PROW_URL, "prow_apikey": PROW_KEY, "prow_cats": PROW_CATS,
             "igdb_id": IGDB_ID, "igdb_secret": IGDB_SECRET,
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
             # Katalog-JSON-Quellen fuer den Filehoster-Zweig — eine URL je Zeile.
             # Bewusst NUR konfigurierbar, nie im Repo hinterlegt. (#63)
             "catalog_urls": os.environ.get("CATALOG_URLS", ""),
             # Streaming-Host (#71): Browser-URL des Hosts + optionaler Start-Dienst
             "stream_url": os.environ.get("STREAM_URL", ""),
             "stream_launch": os.environ.get("STREAM_LAUNCH", "")}
CONN_KEYS = list(_ENV_CONN.keys())
CONN_SECRET = {"sab_apikey", "prow_apikey", "igdb_secret", "romm_pass",
               "sgdb_key", "ss_pass", "ra_key"}   # in der GUI maskiert (Klartext-Anzeige via Reveal-Endpoint)
def cfg(key):
    """Verbindungswert holen: settings['connections'] (UI) hat Vorrang, sonst Env-Default."""
    v = (load_settings().get("connections") or {}).get(key)
    if v in (None, ""): v = _ENV_CONN.get(key, "")
    return v.rstrip("/") if (key.endswith("_url") and isinstance(v, str)) else v
# __CONN_HELPERS_END__

ROM_EXT = {"sfc","smc","nes","fds","gb","gba","gbc","n64","z64","v64","ndd","md","gen","smd","sms",
           "gg","32x","pce","sgx","ngp","ngc","ws","wsc","iso","bin","cue","chd","img","cdi","gdi",
           "adf","d64","t64","rom","a26","a78","lnx","vec","3ds","cia","nsp","xci","wbfs","rvz","dol",
           "gcm","pbp","ecm","dsk","st","ipf","col","int","j64","jag","min","vb","ws"}
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

# Für die Plattform-Vorauswahl in der Oberfläche (Gruppe -> [(slug, Anzeigename)])
PLATFORMS = [
 ("Nintendo", [("nes","NES"),("snes","SNES"),("n64","N64"),("gb","Game Boy"),("gbc","GB Color"),
   ("gba","GB Advance"),("nds","DS"),("3ds","3DS"),("ngc","GameCube"),("wii","Wii"),
   ("wiiu","Wii U"),("switch","Switch"),("virtualboy","Virtual Boy")]),
 ("Sega", [("sms","Master System"),("genesis","Mega Drive"),("segacd","Mega-CD"),
   ("sega32x","32X"),("gamegear","Game Gear"),("saturn","Saturn"),("dreamcast","Dreamcast")]),
 ("Sony", [("psx","PS1"),("ps2","PS2"),("ps3","PS3"),("ps4","PS4"),("psp","PSP"),("psvita","Vita")]),
 ("Microsoft", [("xbox","Xbox"),("xbox360","Xbox 360"),("xboxone","Xbox One")]),
 ("Sonstige", [("turbografx16","PC Engine"),("neogeo","Neo Geo"),("neogeopocket","NGP"),
   ("wonderswan","WonderSwan"),("atari2600","Atari 2600"),("atari5200","Atari 5200"),
   ("atari7800","Atari 7800"),
   ("lynx","Lynx"),("jaguar","Jaguar"),("3do","3DO"),("amiga","Amiga"),("c64","C64"),
   ("c16","C16 / Plus-4"),("vic20","VIC-20"),("colecovision","ColecoVision"),
   ("intellivision","Intellivision"),("acpc","Amstrad CPC"),("zxs","ZX Spectrum"),
   ("dos","DOS"),("arcade","Arcade")]),
]
SLUG_NAME = {s:n for _g,items in PLATFORMS for s,n in items}
# IGDB-Plattform-IDs (für „beliebt pro Konsole")
IGDB_PLAT = {"snes":19,"nes":18,"n64":4,"gb":33,"gbc":22,"gba":24,"nds":20,"3ds":37,"ngc":21,
 "wii":5,"switch":130,"genesis":29,"sms":64,"gamegear":35,"saturn":32,"dreamcast":23,
 "psx":7,"ps2":8,"ps3":9,"psp":38,"xbox":11,"xbox360":12,"arcade":52,"turbografx16":86,
 "atari2600":59,"neogeo":80}
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
 (r"gamecube|\bngc\b|\bgc\b", "ngc"),
 (r"nintendo\s*ds|\bnds\b", "nds"),
 (r"nintendo\s*3ds|\b3ds\b", "3ds"),
 (r"\bswitch\b|\bnsw\b", "switch"),
 (r"\bwii\s*u\b|wiiu", "wiiu"),
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
 (r"playstation\s*vita|\bvita\b", "psvita"),
 (r"playstation\s*2|\bps2\b", "ps2"),
 (r"playstation\s*3|\bps3\b", "ps3"),
 (r"playstation\s*4|\bps4\b", "ps4"),
 (r"playstation|\bpsx\b|\bps1\b|psone", "psx"),
 (r"xbox\s*360", "xbox360"),
 (r"xbox\s*one", "xboxone"),
 (r"\bxbox\b", "xbox"),
 (r"turbografx|pc\s*engine|\bpce\b", "turbografx16"),
 (r"neo\s*geo\s*pocket", "neogeopocket"),
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
 "xci":"switch","vb":"virtualboy","col":"colecovision","int":"intellivision","min":"pokemini"}

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
def norm(name):
    """Datei-/Titelname -> normalisierter Vergleichsschlüssel (Endung, Klammern, Region,
    Versionsnummern und Sonderzeichen entfernt, lowercase). Grundlage der Dedup."""
    s = os.path.splitext(str(name)[:MAX_NAME])[0].lower()      # gedeckelt: siehe _tags
    s = re.sub(r'[\._\-+]+', ' ', s)                          # Trenner ZUERST zu Space
    s = re.sub(r'\([^)]*\)|\[[^\]]*\]|\{[^}]*\}', ' ', s)     # (USA), [!], {...}
    s = re.sub(r'\bv?\d+(\.\d+)+\b', ' ', s)                   # v1.2.3
    s = REGION_RE.sub(' ', s)                                  # Region/Plattform-Tokens
    s = DISC_ID_RE.sub(' ', s)                                 # BLES00562, BLUS30232 …
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
LIB = {"per": {}, "all": set(), "slugs": set(), "ts": 0}
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

def save_index_to_db(per, allset, slugs, ts):
    """RAM-Index atomar in SQLite spiegeln (library-Tabelle komplett ersetzen + meta-Zähler)."""
    rows = [(slug, n) for slug, s in per.items() for n in s]
    try:
        with DB_LOCK, closing(db_conn()) as c, c:
            c.execute("DELETE FROM library")
            c.executemany("INSERT INTO library(slug,norm) VALUES(?,?)", rows)
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
    "neogeoaes": "neogeo", "neogeomvs": "neogeo", "neo-geo-cd": "neogeo",
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
}


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


def build_index():
    """Bibliotheks-Index aus dem Dateisystem neu aufbauen (ROMS/<slug>/…, 2 Ebenen tief),
    in LIB (RAM) ablegen UND in SQLite persistieren. Läuft beim allerersten Start und
    danach periodisch im Hintergrund (periodic_index) sowie nach jedem Import."""
    per, allset, slugs = {}, set(), set()
    try:
        for ordner in os.listdir(ROMS):
            p = os.path.join(ROMS, ordner)
            if not os.path.isdir(p): continue
            slug = folder_slug(ordner)
            if not slug: continue          # kein Plattformordner (#124)
            slugs.add(slug)
            # Mehrere Ordner koennen auf denselben Slug zeigen (cps1, cps2 -> arcade).
            # setdefault statt Zuweisung, sonst ueberschreibt der zweite den ersten.
            s = per.setdefault(slug, set())
            try:
                for root, dirs, files in os.walk(p):
                    for fn in files:
                        n = norm(fn)
                        if n: s.add(n); allset.add(n)
                    # nur zwei Ebenen tief laufen (Performance)
                    if root != p and os.path.relpath(root, p).count(os.sep) >= 1:
                        dirs[:] = []
            except Exception: pass
    except Exception as e:
        log(f"Index-Fehler: {e}")
    ts = time.time()
    with LIB_LOCK:
        LIB["per"], LIB["all"], LIB["slugs"], LIB["ts"] = per, allset, slugs, ts
    save_index_to_db(per, allset, slugs, ts)   # persistieren -> schneller Neustart
    log(f"Bibliotheks-Index: {len(slugs)} Plattformen, {len(allset)} Titel (in DB gesichert)")
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

def resolve_slug(slug):
    """auf existierenden Ordner mappen, sonst so lassen (wird angelegt) / Mixed."""
    if not slug: return "Mixed"
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
        try: year = datetime.utcfromtimestamp(g["first_release_date"]).year
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

def igdb_similar_games(title, limit=20):
    """Ähnliche Spiele (mit Cover) zu einem Titel – Grundlage für „Weil du … angefragt hast"."""
    key = "simg:" + norm(title)
    if key in IGDB["cache"]: return IGDB["cache"][key]
    d = igdb_query("games", f'search "{title[:60]}"; '
        f'fields name,similar_games.name,similar_games.cover.image_id,similar_games.total_rating; limit 1;')
    g = d[0] if isinstance(d, list) and d else {}
    out = [{"title": s.get("name",""), "cover": _cover_url(s),
            "ext_rating": round(s["total_rating"]) if s.get("total_rating") else None}
           for s in (g.get("similar_games", []) or []) if s.get("name") and s.get("cover")][:limit]
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
    t = re.split(r'\b(update|dlc|proper|repack|multi\d*|nsw|xci|nsp|wbfs|rvz|ps[1-5]|psp|psvita|'
                 r'wiiu?|xbox\w*|switch|eur|usa|jpn|europe|japan|v\d+(\.\d+)*)\b', t, 1, flags=re.I)[0]
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
        params_list = [("fl[]","identifier"),("fl[]","title"),("fl[]","item_size"),
                       ("fl[]","downloads"),("fl[]","subject")]
        url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(params) + "&" + urllib.parse.urlencode(params_list)
        r = requests.get(url, timeout=15); d = r.json()
        for doc in d.get("response",{}).get("docs",[]):
            ident = doc.get("identifier"); title = doc.get("title") or ident
            if not ident: continue
            if NOISE_RE.search(str(title)): continue
            subj = doc.get("subject"); subj = " ".join(subj) if isinstance(subj,list) else (subj or "")
            slug = guess_platform(f"{title} {subj} {ident}")
            out.append({"source":"archive","ref":ident,"title":str(title)[:140],
                        "platform":slug, "size":int(doc.get("item_size") or 0),
                        "cover":f"https://archive.org/services/img/{ident}",
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
            except Exception: pass
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

def search_usenet(q, cats, limit=30):
    out = []
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
            if not slug: slug = guess_platform(it.get("title",""))
            out.append({"source":"usenet","ref":it.get("downloadUrl"),"title":it.get("title","")[:140],
                        "platform":slug,"size":int(it.get("size") or 0),
                        "cover":"", "extra":it.get("indexer","")})
    except Exception as e:
        log(f"Usenet-Suche-Fehler: {e}")
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
    # Usenet breit über Console (1000) abfragen und danach nach Plattform filtern —
    # Indexer taggen vieles nur unter der Oberkategorie. Retro-only-Auswahl -> Usenet aus.
    if platforms:
        usenet_cats = cfg("prow_cats") if any(SLUG2USE.get(p) for p in platforms) else ""
    else:
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
    res.sort(key=lambda x: (x["in_library"], x["is_set"], variant_rank(x["variant"], prefs), x["_rank"]))
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
            if j["id"]==jid: j.update(kw); j["updated"]=datetime.now().strftime("%H:%M:%S")
        save_jobs()

def new_job(item, user="", approved=True):
    """Anfrage anlegen. approved=True -> direkt `queued` + in die Worker-Queue;
    approved=False -> `pending` (wartet auf Admin-Freigabe). Gibt den Job zurück."""
    jid = f"{int(time.time())}{len(JOBS)%1000:03d}"
    job = {"id":jid,"title":item["title"],"source":item["source"],"ref":item["ref"],
           "platform":item.get("platform_slug") or "Mixed","size":item.get("size",0),
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

def find_output(base, jid):
    """Fertigen Ausgabeordner zu einem Job über das `romseerr_<jid>`-Präfix finden
    (exakt oder mit Titel-Suffix). Robust gegen die Namensbereinigung von SAB/JD:
    der jid ist fixer Länge, ein direkt folgendes Zeichen darf keine Ziffer sein
    (sonst wäre es ein längerer jid), damit keine Verwechslung entsteht."""
    pref = f"romseerr_{jid}"
    try:
        for e in os.scandir(base):
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
                subprocess.run(["aria2c","-x8","-s8","-j4","--auto-file-renaming=false",
                                "--continue=true","-d",dst,"-i",inp], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                    rc = subprocess.run(["aria2c","-x8","-s8","-j4","--auto-file-renaming=false",
                                         "--continue=true","--max-tries=3","-d",dst,"-i",inp],
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
    for root,_,files in os.walk(folder):
        for fn in files:
            if SKIP_FILES.search(fn) or fn == ".urls": continue
            src = os.path.join(root,fn)
            # NUR bekannte ROM-/Disk-Endungen importieren. Alles andere (entpackte
            # Fangames, .exe/.dll/.ogg, Emulatoren …) übersprin­gen, statt die
            # Bibliothek zu vermüllen. (#61) — `ziel` kann sich von `fn` unterscheiden,
            # wenn ein Downloadprogramm eine zweite Endung angehängt hat. (#241)
            ext, ziel = rom_endung(fn)
            if not ext:
                skipped += 1
                uebergangen.append(fn)
                continue
            # Plattform pro Datei: eindeutige Endung schlägt den Job-Hinweis
            slug = resolve_slug(EXT2PLAT.get(ext) or job_slug)
            if in_library(ziel, slug):
                continue  # schon vorhanden -> nicht doppeln
            target = os.path.join(ROMS, slug); os.makedirs(target, exist_ok=True)
            dst = os.path.join(target, ziel)
            if os.path.exists(dst): continue
            try:
                subprocess.run(["cp","-a",src,dst], check=True); moved += 1
                by_plat[slug] = by_plat.get(slug,0)+1
            except Exception as e:
                log(f"move-Fehler {fn}: {e}"); copy_errors += 1
    # Staging aufräumen
    try:
        if folder.startswith(STAGING): subprocess.run(["rm","-rf",folder])
    except Exception: pass
    build_index()
    romm_scan()
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
def romm_scan():
    """Optional: RomM zu einem schnellen Bibliotheks-Scan anstoßen (nur wenn konfiguriert)."""
    if not (cfg("romm_url") and cfg("romm_user") and cfg("romm_pass")): return
    try:
        s = requests.Session()
        s.post(f"{cfg("romm_url")}/api/login", auth=(cfg("romm_user"),cfg("romm_pass")), timeout=10)
        s.post(f"{cfg("romm_url")}/api/scan", json={"platforms":[], "type":"quick"}, timeout=10)
    except Exception as e:
        log(f"RomM-Scan-Hinweis: {e}")

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
    "arcade": "fbneo", "neogeo": "fbneo",
    # Heimcomputer und fruehe Konsolen (#124). Die Kernnamen wurden NICHT aus der
    # libretro-Liste abgeschrieben, sondern in der eingesetzten RomM-Fassung
    # nachgesehen — ein Eintrag auf einen Kern, den der Player nicht mitbringt, waere
    # ein Knopf, der nicht funktioniert.
    # Core names were read out of the deployed RomM build rather than copied from
    # libretro's catalogue.
    "c16": "vice_xplus4",              # C16 und Plus/4 teilen sich den Kern
    "vic20": "vice_xvic",
    "colecovision": "gearcoleco",
    "intellivision": "freeintv",
    "atari5200": "a5200",
    "acpc": "cap32",                   # Amstrad CPC
    "zxs": "fuse",                     # ZX Spectrum
}
# NICHT eingetragen, weil der Player die Kerne nicht mitbringt — nachgesehen, nicht
# vermutet: Vectrex (`vecx`, 352 Dateien), Atari 8-Bit (`atari800`, 252), Atari ST
# (`hatari`, 120) und ScummVM (441). Das ist eine Grenze von RomMs EmulatorJS-Bau,
# keine Entscheidung dieses Projekts; sobald die Kerne dort auftauchen, sind es vier
# Zeilen. / Not entered because the player lacks those cores — a limit of the build.
# Plattformen, deren Kern ohne BIOS startet und dann scheitert — der Nutzer soll das
# VORHER lesen, statt vor einer schwarzen Flaeche zu sitzen.
NEEDS_BIOS = {"psx", "3do", "saturn", "amiga", "segacd"}
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
STREAMABLE = {"ps2", "ngc", "wii", "wiiu", "switch", "dreamcast", "3ds",
              "xbox", "ps3", "psvita"}
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

def stream_session():
    """Laufende Sitzung oder None. Abgelaufene Sitzungen geben den Platz von selbst frei —
    ein vergessener Browser-Tab darf den Einzelplatz nicht dauerhaft blockieren."""
    ses = kv_get("stream_session", None)
    if not ses: return None
    if time.time() > float(ses.get("expires") or 0):
        kv_put("stream_session", None); return None
    return ses

def stream_find_file(title, slug):
    """Titel -> Datei in der Bibliothek. Ohne Datei kein Stream (dieselbe Regel wie bei Play).

    Der Slug kommt vom Aufrufer und geht in einen Pfad. Er wird deshalb HIER gegen die
    feste Menge geprueft und nicht nur beim Aufrufer — sonst haenge die Sicherheit an der
    Reihenfolge der Pruefungen in stream_info(), und die kann sich aendern."""
    ordner = STREAM_DIR.get(slug)        # Nachschlagen statt Durchreichen
    if not ordner: return None
    want = norm(title)
    if not want: return None
    try:
        for name in ordner:
            base = os.path.join(ROMS, name)
            if not os.path.isdir(base): continue
            # Ein Titel ist nicht immer eine DATEI. Eine PS3-Disc ist ein Ordner mit
            # PS3_GAME/USRDIR/EBOOT.BIN darin — 10 von 17 Titeln der Testbibliothek.
            # Ohne diesen Zweig meldete jeder PS3-Titel "not_in_library", der Stream-
            # Knopf erschien nie, und der Start-Dienst haette ihn klaglos gestartet:
            # zwei Seiten, die sich widersprechen. (#150; die Dienstseite war #149)
            # A title is not always a file; a PS3 disc is a folder. Without this the
            # two sides disagree: Romseerr says "not in library", the launcher starts it.
            #
            # ZUERST der Ordner, dann die Dateisuche: eine Disc traegt denselben Namen
            # wie ein evtl. daneben liegendes Abbild, und der Ordner ist der Titel.
            for eintrag in sorted(os.listdir(base)):
                voll = os.path.join(base, eintrag)
                if os.path.isdir(voll) and norm(eintrag) == want:
                    return voll
            for root, _dirs, files in os.walk(base):
                for fn in files:
                    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
                    if ext in ROM_EXT and norm(fn) == want:
                        return os.path.join(root, fn)
            if root != base and os.path.relpath(root, base).count(os.sep) >= 1:
                break
    except OSError:
        return None
    return None

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
    ses = stream_session()
    busy = bool(ses and ses.get("user") != user)
    return {"streamable": not busy, "platform": slug, "path": path,
            "reason": "busy" if busy else "",
            "busy_with": (ses or {}).get("title", "") if busy else "",
            "busy_user": (ses or {}).get("user", "") if busy else "",
            "url": conf["url"]}

def stream_start(user, title, slug):
    """Einzelplatz belegen und — falls ein Start-Dienst hinterlegt ist — den Titel starten."""
    info = stream_info(title, slug, user)
    if not info.get("streamable"):
        return info, 409 if info.get("reason") == "busy" else 400
    with STREAM_LOCK:
        ses = stream_session()
        if ses and ses.get("user") != user:      # zweite Pruefung IM Lock (Wettlauf)
            return {"streamable": False, "reason": "busy",
                    "busy_with": ses.get("title", ""), "busy_user": ses.get("user", "")}, 409
        conf = stream_cfg()
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
        kv_put("stream_session", {"user": user, "title": title, "platform": info["platform"],
                                  "started": int(time.time()),
                                  "expires": time.time() + STREAM_TTL, "launched": launched})
    return {"streamable": True, "url": conf["url"], "launched": launched,
            "launch_error": fehler, "launch_reason": fehlergrund,
            "platform": info["platform"], "expires_in": STREAM_TTL}, 200

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
                    if p and any(os.scandir(p)): cand = p
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
    try:
        a = sum(f.stat().st_size for f in os.scandir(path) if f.is_file())
        time.sleep(wait)
        b = sum(f.stat().st_size for f in os.scandir(path) if f.is_file())
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
def app_secret():
    """Signaturschlüssel für die Flask-Session (secret.key). Beim ersten Mal erzeugt & gespeichert."""
    try:
        wert = open(SECRET_FILE).read().strip()
        geheim_absichern(SECRET_FILE)
        return wert
    except Exception:
        s = secrets.token_hex(32)
        try: schreibe_geheim(SECRET_FILE, s)
        except Exception: pass
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
ASSET_MIME = {".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8",
              ".svg": "image/svg+xml", ".png": "image/png", ".webmanifest": "application/manifest+json"}
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
            _ASSETS[rel] = {"hash": hashlib.sha256(body).hexdigest()[:12], "body": body,
                            "mime": ASSET_MIME.get(ext, "application/octet-stream")}
    return len(_ASSETS)

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
    return Response(a["body"], mimetype=a["mime"],
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})

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
    ses = stream_session()
    if not ses: return jsonify({"ok": True, "was_running": False})
    if ses.get("user") != me and not has_perm("manage_requests"):
        return jsonify({"ok": False, "msg": "fremde Sitzung / not your session"}), 403
    kv_put("stream_session", None)
    return jsonify({"ok": True, "was_running": True})

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
    """Aktualisierung der Emulatoren auf dem Streaming-Host anstossen. Der Lauf
    dauert Minuten (hunderte Megabyte), deshalb antwortet der Dienst sofort und der
    Fortschritt wird ueber /api/stream/emulators abgefragt."""
    conf = stream_cfg()
    if not conf["launch"]:
        return jsonify({"ok": False, "reason": "no_launcher"}), 400
    url = conf["launch"].split("?")[0].rsplit("/", 1)[0] + "/update"
    q = conf["launch"].split("?", 1)[1] if "?" in conf["launch"] else ""
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
    ses = stream_session()
    conf = stream_cfg()
    return jsonify({"configured": bool(conf["url"]), "has_launcher": bool(conf["launch"]),
                    "seats": 1, "ttl": STREAM_TTL,
                    "session": {k: ses[k] for k in ("user", "title", "platform", "started", "launched")}
                               if ses else None})

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
    job = new_job(it, user=user, approved=auto)
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
                    "storage":"rw" if st["ok"] else "ro"})

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
UPDATE_TTL   = 6 * 3600
_UPDATE      = {"ts": 0, "latest": None}

def _semver(v):
    """'1.2.3' / 'v1.2.3-beta.1' -> (1,2,3). Pre-Release-Suffix wird ignoriert."""
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", str(v or ""))
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)

def latest_release():
    """Neueste veröffentlichte Version von GitHub, gecacht. Fehler sind still — ein
    Update-Hinweis darf nie eine Seite kaputt machen oder verzögert beantworten."""
    now = time.time()
    if now - _UPDATE["ts"] < UPDATE_TTL: return _UPDATE["latest"]
    _UPDATE["ts"] = now
    try:
        r = requests.get(UPDATE_URL, timeout=5,
                         headers={"Accept": "application/vnd.github+json"})
        if r.status_code == 200:
            tag = (r.json() or {}).get("tag_name") or ""
            _UPDATE["latest"] = tag.lstrip("v") or None
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
        treffer = do_search(job.get("title", ""), [plat] if plat and plat != "Mixed" else None)
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
    o = {"summary": summary, "tags": [tag],
         "responses": responses or {"200": {"description": "OK"}}}
    o["security"] = _SEC if security is None else security
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
                               "(storage: rw/ro — ro heißt: es wird nichts gespeichert)", "System", _PUB)},
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
        "/api/discover": {"get": _op("Beliebte Titel (flach)", "Search")},
        "/api/discover/rows": {"get": _op("Startseiten-Reihen (beliebt je Konsole + je Genre)", "Search")},
        "/api/detail": {"get": _op("Detaildaten inkl. IGDB (Wertung, Screenshots, Ähnliches) + Dateien", "Search",
            params=[_qp("source", "archive|usenet"), _qp("ref", "Quell-Referenz"), _qp("title", "Titel")])},
        "/api/play": {"get": _op("Kann der Titel im Browser gespielt werden (RomM/EmulatorJS)?", "Search",
            params=[_qp("title", "Titel"), _qp("platform", "Plattform-Slug")],
            responses={**_R_PERM, "200": {"description": "playable + Grund/URL"},
                       "400": {"description": "kein Titel"}})},
        "/api/stream": {"get": _op("Ist der Titel streambar (Plattform ohne Browser-Kern)?", "Search",
            params=[_qp("title", "Titel"), _qp("platform", "Plattform-Slug")], responses=_R_PERM)},
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
            eintraege = list(os.scandir(basis))
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
    if not (cfg("prow_url") and cfg("prow_apikey")):
        log("Konfig: Prowlarr nicht gesetzt — Usenet-Suche aus.")
    elif not reach(cfg("prow_url")):
        warn("prow", f"Prowlarr ({cfg("prow_url")}) nicht erreichbar / not reachable.")

if __name__ == "__main__":
    os.makedirs(STAGING, exist_ok=True)
    geheimnisse_absichern()      # vor allem anderen: Rechte am Schluesselmaterial (#256)
    db_init(); load_jobs()
    if load_index_from_db():
        log(f"Bibliotheks-Index aus DB geladen: {len(LIB['slugs'])} Plattformen, {len(LIB['all'])} Titel")
        threading.Thread(target=build_index, daemon=True).start()   # im Hintergrund auffrischen
    else:
        build_index()   # kein DB-Index -> erstmalig aus dem Dateisystem
    threading.Thread(target=worker_download, daemon=True).start()
    threading.Thread(target=worker_collect, daemon=True).start()
    threading.Thread(target=periodic_index, daemon=True).start()
    threading.Thread(target=check_config, daemon=True).start()
    threading.Thread(target=worker_wishlist, daemon=True).start()
    threading.Thread(target=worker_catalog, daemon=True).start()
    threading.Thread(target=worker_leftovers, daemon=True).start()
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
