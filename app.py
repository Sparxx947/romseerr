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
 11. Web-UI                   – PAGE/LOGIN_PAGE/RESET_PAGE: das gesamte Frontend als String.
 12. Auth-/Admin-Routen       – REST-Endpunkte (siehe OpenAPI-Abschnitt).
 13. OpenAPI                  – Selbstdokumentation (/api/openapi.json, /api/docs).
 14. Start                    – Index laden, Worker starten, Flask starten.

================================================================================
DATENHALTUNG / STORAGE  (alles unter CONFIG_DIR, Default /config)
================================================================================
  romseerr.db  – SQLite: Tabelle `library` (Dedup-Index), `meta`, `users`, `jobs`.
  settings.json, issues.json, maillog.json, push_subs.json, secret.key, vapid.json
               – kleine, menschenlesbare JSON-/Key-Dateien (bewusst NICHT in der DB).
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
  * Das Frontend-JS steckt in NICHT-rohen Python-Strings (PAGE): Backslash-Escapes
    MÜSSEN verdoppelt werden (`\\n`), sonst zerbricht das gesamte Inline-Skript.
    Der Test tests/test_smoke.py::test_inline_js_parses wacht darüber.
  * Pro-Aufruf geöffnete SQLite-Verbindungen werden mit contextlib.closing wieder
    geschlossen (sonst File-Descriptor-Leck bei jedem Request).
  * Deployment: ein neues Image erfordert `docker rm`+`run` — `docker restart` lädt
    KEIN neues Image.
"""
import os, re, json, time, threading, queue, subprocess, urllib.parse, html, secrets, smtplib, base64, sqlite3
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
from flask import Flask, request, jsonify, Response, session, redirect, g
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
JD_WATCH   = "/jd-watch"
JD_OUT     = "/jd-output/romseerr"           # Sicht von Romseerr (=/mnt/user/Downloads/romseerr)
JD_DL_BASE = os.environ.get("JD_DL_BASE","/output/romseerr")  # Sicht des JD-Containers
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
             "jd_dl_base": JD_DL_BASE,
             # Scraper / Cover-Quellen
             "sgdb_key": os.environ.get("STEAMGRIDDB_KEY", ""),
             "ss_user":  os.environ.get("SCREENSCRAPER_USER", ""),
             "ss_pass":  os.environ.get("SCREENSCRAPER_PASS", ""),
             # RetroAchievements-Web-API-Key (optional, nur Dekoration auf der Detailseite)
             "ra_key":   os.environ.get("RETROACHIEVEMENTS_KEY", "")}
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
   ("wonderswan","WonderSwan"),("atari2600","Atari 2600"),("atari7800","Atari 7800"),
   ("lynx","Lynx"),("jaguar","Jaguar"),("3do","3DO"),("amiga","Amiga"),("c64","C64"),
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
    r'\bmd\b|psx|ps1|ps2|psp|switch|wii|gamecube|ngc|arcade|mame)\b')
def norm(name):
    """Datei-/Titelname -> normalisierter Vergleichsschlüssel (Endung, Klammern, Region,
    Versionsnummern und Sonderzeichen entfernt, lowercase). Grundlage der Dedup."""
    s = os.path.splitext(name)[0].lower()
    s = re.sub(r'[\._\-+]+', ' ', s)                          # Trenner ZUERST zu Space
    s = re.sub(r'\([^)]*\)|\[[^\]]*\]|\{[^}]*\}', ' ', s)     # (USA), [!], {...}
    s = re.sub(r'\bv?\d+(\.\d+)+\b', ' ', s)                   # v1.2.3
    s = REGION_RE.sub(' ', s)                                  # Region/Plattform-Tokens
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

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

def build_index():
    """Bibliotheks-Index aus dem Dateisystem neu aufbauen (ROMS/<slug>/…, 2 Ebenen tief),
    in LIB (RAM) ablegen UND in SQLite persistieren. Läuft beim allerersten Start und
    danach periodisch im Hintergrund (periodic_index) sowie nach jedem Import."""
    per, allset, slugs = {}, set(), set()
    try:
        for slug in os.listdir(ROMS):
            p = os.path.join(ROMS, slug)
            if not os.path.isdir(p): continue
            slugs.add(slug)
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
        f'fields name,similar_games.name,similar_games.cover.image_id; limit 1;')
    g = d[0] if isinstance(d, list) and d else {}
    out = [{"title": s.get("name",""), "cover": _cover_url(s)}
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
    t = re.sub(r'[\._]+', ' ', t or "")
    t = re.split(r'\b(update|dlc|proper|repack|multi\d*|nsw|xci|nsp|wbfs|rvz|ps[1-5]|psp|psvita|'
                 r'wiiu?|xbox\w*|switch|eur|usa|jpn|europe|japan|v\d+(\.\d+)*)\b', t, 1, flags=re.I)[0]
    t = re.sub(r'\([^)]*\)|\[[^\]]*\]', ' ', t)
    t = re.sub(r'-\s*\w+$', '', t)          # -GROUP am Ende
    return re.sub(r'\s+', ' ', t).strip()

def igdb_popular(limit=40):
    d = igdb_query("games", f'fields name,cover.image_id; '
        f'where cover != null & total_rating_count > 80; '
        f'sort total_rating_count desc; limit {limit};')
    if not isinstance(d, list): return []
    return [{"title": g.get("name",""), "cover": _cover_url(g)}
            for g in d if isinstance(g, dict) and g.get("cover")]

def igdb_popular_platform(pid, limit=20):
    d = igdb_query("games", f'fields name,cover.image_id; '
        f'where platforms=({pid}) & cover != null & total_rating_count > 12; '
        f'sort total_rating_count desc; limit {limit};')
    if not isinstance(d, list): return []
    return [{"title": g.get("name",""), "cover": _cover_url(g)}
            for g in d if isinstance(g, dict) and g.get("cover")]

# IGDB-Genre-ID -> Anzeigename (für Genre-Reihen im Discover)
IGDB_GENRES = [("rpg",12,"Rollenspiele / RPG"), ("platform",8,"Jump 'n' Run"),
               ("shooter",5,"Shooter"), ("fighting",4,"Beat 'em up"),
               ("racing",10,"Rennspiele / Racing"), ("adventure",31,"Adventure"),
               ("puzzle",9,"Puzzle"), ("sport",14,"Sport"), ("strategy",15,"Strategie / Strategy")]
def igdb_popular_genre(gid, limit=20):
    d = igdb_query("games", f'fields name,cover.image_id; '
        f'where genres=({gid}) & cover != null & total_rating_count > 30; '
        f'sort total_rating_count desc; limit {limit};')
    if not isinstance(d, list): return []
    return [{"title": g.get("name",""), "cover": _cover_url(g)}
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
    return [{"slug": r["slug"], "key": r.get("key", r["console"]), "console": r["console"],
             "games": [{**g, "in_library": in_library(g["title"], r["slug"] or None)}
                       for g in r["games"] if not is_blocked(g["title"], bl)]}
            for r in rows]

def notify_send(text):
    """Meldung an ALLE aktiven globalen Kanäle senden: Discord-Webhook (Einstellungen oder
    Env-Fallback), Telegram, generischer Webhook. Gibt True zurück, wenn mind. einer sendete."""
    s = load_settings(); sent = False
    dc = s.get("discord", {})
    wh = dc.get("url") if dc.get("enabled") else os.environ.get("DISCORD_WEBHOOK", "")
    if wh:
        try: requests.post(wh, json={"content": text}, timeout=8); sent = True
        except Exception as e: log(f"Discord-Fehler: {e}")
    ag = s.get("agents", {})
    tg = ag.get("telegram", {})
    if tg.get("enabled") and tg.get("token") and tg.get("chat"):
        try: requests.post(f"https://api.telegram.org/bot{tg['token']}/sendMessage",
                           json={"chat_id": tg["chat"], "text": text}, timeout=8); sent = True
        except Exception as e: log(f"Telegram-Fehler: {e}")
    gw = ag.get("webhook", {})
    if gw.get("enabled") and gw.get("url"):
        try: requests.post(gw["url"], json={"content": text, "text": text}, timeout=8); sent = True
        except Exception as e: log(f"Webhook-Fehler: {e}")
    gt = ag.get("gotify", {})
    if gt.get("enabled") and gt.get("url") and gt.get("token"):
        try: requests.post(f"{gt['url'].rstrip('/')}/message", params={"token": gt["token"]},
                           json={"title": "Romseerr", "message": text}, timeout=8); sent = True
        except Exception as e: log(f"Gotify-Fehler: {e}")
    nt = ag.get("ntfy", {})
    if nt.get("enabled") and nt.get("topic"):
        base = (nt.get("url") or "https://ntfy.sh").rstrip("/")
        hdr = {"Authorization": "Bearer " + nt["token"]} if nt.get("token") else {}
        try: requests.post(f"{base}/{nt['topic']}", data=text.encode("utf-8"), headers=hdr, timeout=8); sent = True
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
    for idx, r in enumerate(ar+us):
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
        r["_rank"] = idx
        # Cover für Usenet-Treffer werden im Frontend lazy über /api/cover geladen
        res.append(r)
    # Einzeltitel zuerst, dann Sets; Vorhandene ans Ende; sonst Relevanz-Reihenfolge
    res.sort(key=lambda x:(x["in_library"], x["is_set"], x["_rank"]))
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
           "user":user,"state":"queued" if approved else "pending","created":int(time.time()),
           "updated":datetime.now().strftime("%H:%M:%S"),"msg":"" if approved else "wartet auf Freigabe"}
    with JOBS_LOCK: JOBS.append(job); save_jobs()
    if approved: Q.put(jid)
    return job

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

def write_crawljob(jid, links, folder, name):
    # folder = JD-Container-Sicht (z.B. /output/romseerr/...); JD legt sie selbst an.
    data = [{"text":"\n".join(links) if isinstance(links,list) else links,
             "downloadFolder":folder,"packageName":name,"enabled":"true","autoStart":"true",
             "autoConfirm":"true","overwritePackagizerRules":"true"}]
    path = os.path.join(JD_WATCH, f"romseerr_{jid}.crawljob")
    with open(path,"w") as f: json.dump(data,f)
    log(f"crawljob geschrieben: {path}")

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
                set_state(jid, state="downloading", msg="an JDownloader übergeben")
                dn = dl_name(jid, job.get("title",""))
                write_crawljob(jid, job["ref"], f"{cfg("jd_dl_base")}/{dn}", dn)
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
    for root,_,files in os.walk(folder):
        for fn in files:
            if SKIP_FILES.search(fn) or fn == ".urls": continue
            src = os.path.join(root,fn)
            ext = fn.rsplit(".",1)[-1].lower() if "." in fn else ""
            # NUR bekannte ROM-/Disk-Endungen importieren. Alles andere (entpackte
            # Fangames, .exe/.dll/.ogg, Emulatoren …) übersprin­gen, statt die
            # Bibliothek zu vermüllen. (#61)
            if ext not in ROM_EXT:
                skipped += 1; continue
            # Plattform pro Datei: eindeutige Endung schlägt den Job-Hinweis
            slug = resolve_slug(EXT2PLAT.get(ext) or job_slug)
            if in_library(fn, slug):
                continue  # schon vorhanden -> nicht doppeln
            target = os.path.join(ROMS, slug); os.makedirs(target, exist_ok=True)
            dst = os.path.join(target, fn)
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
        set_state(jid, state="error", msg=f"keine ROM-Dateien gefunden / no ROM files ({skipped} übersprungen)")
        log(f"Job {jid}: keine ROM-Dateien, {skipped} Nicht-ROM übersprungen")
        count_import("failure", "no_rom_files")
        return
    where = ", ".join(f"{v}×{k}" for k,v in by_plat.items()) or "nichts (schon vorhanden?)"
    tail = f" · {skipped} Nicht-ROM übersprungen" if skipped else ""
    set_state(jid, state="done", msg=f"{moved} Datei(en) → {where}{tail}")
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
            try: requests.post(wh, json={"content": f"🎮 **{job.get('title','')}** ist jetzt verfügbar / now available ({where})"}, timeout=8)
            except Exception as e: log(f"Personal-Notify-Fehler: {e}")
        if load_settings().get("agents", {}).get("email", {}).get("enabled"):
            em = load_users().get(job.get("user",""), {}).get("email","")
            if em: send_mail(em, "Romseerr — verfügbar / available",
                             f"{job.get('title','')} ({where}) ist jetzt verfügbar / is now available.")

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
                        if pct not in (None, ""): set_state(jid, msg=f"{pct}%")
                else:
                    p = find_output(JD_OUT, jid)
                    if p and any(os.scandir(p)): cand = p
                if cand and folder_stable(cand):
                    import_folder(jid, cand)
                    # Erledigten Download aus SAB/JD und von der Platte entfernen. (#65)
                    if job["source"] == "usenet": sab_cleanup(jid)
                    try:
                        if os.path.isdir(cand) and (cand.startswith(SAB_DONE) or cand.startswith(JD_OUT)):
                            subprocess.run(["rm", "-rf", cand])
                    except Exception as e: log(f"Ausgabe-Cleanup {jid}: {e}")
        except Exception as e:
            log(f"collect-Fehler: {e}")
        time.sleep(20)

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
def save_users(u):
    try:
        with DB_LOCK, closing(db_conn()) as c, c:
            c.execute("DELETE FROM users")
            c.executemany("INSERT INTO users(username,data) VALUES(?,?)",
                          [(k, json.dumps(v)) for k, v in u.items()])
    except Exception as e:
        log(f"users-Speichern-Fehler: {e}")
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
        d = json.load(open(VAPID_FILE)); VAPID_CACHE.update(d); return VAPID_CACHE
    except Exception: pass
    try:
        v = Vapid(); v.generate_keys()
        priv_pem = v.private_pem().decode()
        raw = v.public_key.public_bytes(serialization.Encoding.X962,
                                        serialization.PublicFormat.UncompressedPoint)
        pub_b64 = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
        d = {"priv_pem": priv_pem, "pub_b64": pub_b64}
        json.dump(d, open(VAPID_FILE, "w")); VAPID_CACHE.update(d)
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
    try: return open(SECRET_FILE).read().strip()
    except Exception:
        s = secrets.token_hex(32)
        try: open(SECRET_FILE, "w").write(s)
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
# Das GESAMTE Frontend steckt in den folgenden String-Konstanten (PAGE = App nach Login,
# LOGIN_PAGE, RESET_PAGE). Kein Build-Schritt, keine externen Dateien. Übersetzt wird über
# das JS-Objekt I18N + t(); Ansichten werden per show() umgeschaltet.
# ACHTUNG: Backslash-Escapes im JS hier IMMER verdoppeln (`\\n`) — sonst zerbricht das Skript.
app = Flask(__name__)
app.secret_key = app_secret()
app.config["PERMANENT_SESSION_LIFETIME"] = 60*60*24*30
# Cookie-Härtung: HttpOnly (kein JS-Zugriff) + SameSite=Strict (CSRF-Schutz, da alle
# API-Aufrufe same-origin sind). Secure nur setzen, wenn hinter HTTPS betrieben
# (ROMSEERR_HTTPS=1) — sonst würde das Cookie über reines HTTP im LAN nicht gesetzt.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("ROMSEERR_HTTPS", "") == "1"

PAGE = """<!doctype html><html lang=de><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Romseerr</title>
<link rel=manifest href="/manifest.webmanifest"><meta name=theme-color content="#0b0d10"><link rel=icon href="/icon.svg">
<style>
:root{--bg:#14161a;--card:#1e2229;--acc:#7c5cff;--acc2:#6c5ce7;--ok:#2ecc71;--txt:#e6e8ec;--mut:#8b929e;
 --side:#0f1114;--topbar:#0f1114;--border:#262b33;--hover:#1a1e25;--input:#0b0d10;
 --radius:12px;--shadow:0 1px 2px rgba(0,0,0,.25);--blur:0px;--navon:var(--acc);--navtxt:#fff}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:var(--bg);color:var(--txt);transition:background .25s}
/* ---- Designs (per Nutzer/global wählbar über <html data-design=…>) ---- */
/* seerr = Standard (die :root-Werte oben, dunkel & poliert). glass & clean unten. */
[data-design=glass]{--bg:#0b0e1a;--card:rgba(32,37,58,.55);--acc:#22d3ee;--acc2:#6366f1;--txt:#eaf2ff;--mut:#93a0c0;
 --side:rgba(18,22,38,.55);--topbar:rgba(18,22,38,.45);--border:rgba(255,255,255,.10);--hover:rgba(255,255,255,.07);--input:rgba(10,13,24,.5);
 --radius:16px;--shadow:0 10px 34px rgba(0,0,0,.40);--blur:16px;--navon:linear-gradient(90deg,#22d3ee,#6366f1);--navtxt:#04121a}
[data-design=glass] body{background:
  radial-gradient(1100px 560px at 12% -12%,rgba(99,102,241,.34),transparent 60%),
  radial-gradient(1000px 520px at 108% -4%,rgba(14,165,183,.30),transparent 60%),
  radial-gradient(900px 700px at 50% 120%,rgba(124,92,255,.18),transparent 60%),#0b0e1a;background-attachment:fixed}
[data-design=glass] #side,[data-design=glass] #topbar,[data-design=glass] .card,[data-design=glass] #modal .box,
[data-design=glass] .pcover,[data-design=glass] .job,[data-design=glass] .fbtn,[data-design=glass] input,
[data-design=glass] #setcontent .frow input,[data-design=glass] .badge{backdrop-filter:blur(var(--blur));-webkit-backdrop-filter:blur(var(--blur))}
[data-design=glass] #side .logo{background:linear-gradient(90deg,#22d3ee,#818cf8);-webkit-background-clip:text;background-clip:text}
[data-design=clean]{--bg:#0c0e11;--card:#14171b;--acc:#5b8cff;--acc2:#5b8cff;--txt:#e7eaef;--mut:#7d8695;
 --side:#0c0e11;--topbar:#0c0e11;--border:#1c2026;--hover:#161a1f;--input:#0c0e11;
 --radius:8px;--shadow:none;--blur:0px;--navon:transparent;--navtxt:var(--acc)}
[data-design=clean] #side .logo{background:none;-webkit-text-fill-color:var(--txt);color:var(--txt)}
[data-design=clean] .nav.on{box-shadow:inset 3px 0 0 var(--acc);border-radius:0 8px 8px 0}
[data-design=clean] .card,[data-design=clean] .pcover{box-shadow:none}
[data-design=clean] .pcard:hover .pcover{transform:none;border-color:var(--acc)}
#side{position:fixed;top:0;left:0;bottom:0;width:210px;background:var(--side);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:16px 12px;z-index:6}
#side .logo{font-size:20px;font-weight:700;margin:4px 8px 18px;background:linear-gradient(90deg,#8a7bff,#6c5ce7);-webkit-background-clip:text;background-clip:text;color:transparent}
.nav{display:block;padding:10px 12px;border-radius:10px;color:var(--mut);font-size:14px;cursor:pointer;text-decoration:none;margin-bottom:4px}
.nav:hover{background:var(--hover);color:var(--txt)}
.nav.on{background:var(--navon);color:var(--navtxt)}
#side .grow{flex:1}
#side .ubox{border-top:1px solid var(--border);padding-top:10px}
#side .ubox #who{padding:4px 12px 8px;font-size:12px;color:var(--mut)}
main{margin-left:210px}
#topbar{position:sticky;top:0;background:var(--topbar);padding:14px 18px;display:flex;gap:12px;align-items:center;border-bottom:1px solid var(--border);z-index:5}
input{flex:1;padding:11px 14px;border-radius:10px;border:1px solid var(--border);background:var(--input);color:var(--txt);font-size:15px}
.fbtn{background:var(--card);border:1px solid var(--border);color:var(--txt);font-size:13px;cursor:pointer;padding:10px 12px;border-radius:10px;white-space:nowrap}
#langsw{display:flex;gap:8px;padding:6px 12px}
#langsw b{cursor:pointer;font-size:12px;color:var(--mut);font-weight:700}
#langsw b.on{color:var(--acc)}
/* #modal-Präfix: schlägt die generische Modal-Button-Regel, damit der aktive Zustand sichtbar bleibt */
#modal .dpick{background:var(--input);border:1px solid var(--border);color:var(--mut);padding:6px 11px;border-radius:8px;cursor:pointer;font-size:12px}
#modal .dpick.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
#who{font-size:12px;color:var(--mut);display:flex;align-items:center;padding:4px 12px}
#who img{width:30px;height:30px;border-radius:50%;object-fit:cover;margin-right:7px;border:1px solid #2c323b}
@media(max-width:680px){#side{position:static;width:auto;flex-direction:row;flex-wrap:wrap;align-items:center;padding:10px}#side .logo{margin:0 12px 0 4px}#side .grow{display:none}#side .ubox{border:none;padding:0}main{margin-left:0}.nav{padding:8px 10px;margin:0}}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px;padding:18px}
.card{background:var(--card);border-radius:var(--radius);overflow:hidden;display:flex;flex-direction:column;border:1px solid var(--border);box-shadow:var(--shadow)}
.cover{aspect-ratio:3/4;background:#0b0d10 center/cover no-repeat;position:relative}
.badge{position:absolute;top:6px;left:6px;background:#000a;padding:2px 7px;border-radius:6px;font-size:11px}
.src{position:absolute;top:6px;right:6px;background:#000a;padding:2px 7px;border-radius:6px;font-size:11px}
.body{padding:9px 10px;display:flex;flex-direction:column;gap:6px;flex:1}
.t{font-size:13px;line-height:1.25;max-height:3.2em;overflow:hidden}
.meta{font-size:11px;color:var(--mut)}
.dl{margin-top:auto;padding:8px;border:none;border-radius:8px;background:var(--acc);color:#fff;font-weight:600;cursor:pointer}
.dl:disabled{background:#2a2f37;color:var(--mut);cursor:default}
.have{color:var(--ok);font-size:12px;text-align:center;padding:8px}
#jobs{padding:18px;display:none}
.card .cover{cursor:pointer}
.job{background:var(--card);border:1px solid #262b33;border-radius:10px;padding:10px 12px;margin-bottom:8px;display:flex;justify-content:space-between;gap:10px}
.st{font-size:12px;padding:2px 8px;border-radius:6px;background:#2a2f37}
.st.done{background:#1e5e3a}.st.error{background:#6e2a2a}.st.downloading,.st.importing{background:#5a4a1e}
.hint{color:var(--mut);padding:0 18px 18px;font-size:12px}
#filter{display:none;padding:12px 18px;background:#0f1114;border-bottom:1px solid #262b33}
#filter .grp{margin-bottom:6px}
#filter .gl{font-size:11px;color:var(--mut);margin-bottom:3px;text-transform:uppercase;letter-spacing:.05em}
.chip{display:inline-block;margin:3px;padding:5px 10px;border-radius:16px;border:1px solid #2c323b;background:#1e2229;color:var(--txt);font-size:12px;cursor:pointer;user-select:none}
.chip.on{background:var(--acc);border-color:var(--acc);color:#fff}
#filter .fbtns{margin-top:8px}
#filter .fbtns button{background:#2a2f37;border:none;color:var(--txt);padding:5px 10px;border-radius:6px;font-size:12px;cursor:pointer;margin-right:6px}
#modal{display:none;position:fixed;inset:0;background:#000b;z-index:20;overflow:auto}
#modal .box{max-width:760px;margin:24px auto;background:var(--card);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow)}
#modal .x{float:right;background:#2a2f37;border:none;color:#fff;width:32px;height:32px;border-radius:16px;font-size:18px;cursor:pointer;margin:8px}
#modal .top{display:flex;gap:16px;padding:16px;clear:both}
#modal .mc{width:150px;flex:0 0 150px;aspect-ratio:3/4;border-radius:8px;background:#0b0d10 center/cover no-repeat}
#modal h2{margin:0 0 6px;font-size:20px}
#modal .desc{color:var(--mut);font-size:13px;line-height:1.5;margin:8px 0;max-height:10em;overflow:auto}
#modal .sec{padding:0 16px 16px}
#modal .sec h3{font-size:12px;text-transform:uppercase;color:var(--mut);letter-spacing:.05em;margin:12px 0 6px}
#modal .row{display:flex;justify-content:space-between;gap:10px;padding:7px 10px;background:#171a20;border-radius:8px;margin-bottom:5px;font-size:13px;align-items:center}
#modal .row button{background:var(--acc);border:none;color:#fff;padding:6px 12px;border-radius:6px;font-size:13px;cursor:pointer}
#modal .row button:disabled{background:#2a2f37;color:var(--mut);cursor:default}
.flist{font-size:12px;color:var(--mut);max-height:170px;overflow:auto}
.flist div{padding:3px 0;border-bottom:1px solid #20242b}
.meta2{margin:8px 0 2px;display:flex;flex-wrap:wrap;gap:5px}
.badge{display:inline-block;padding:3px 8px;border-radius:6px;background:#1e2229;border:1px solid #2c323b;color:var(--txt);font-size:12px}
.badge.g{color:var(--mut)}
.shots{display:flex;gap:8px;overflow-x:auto;padding-bottom:4px}
.shots img{height:110px;border-radius:6px;flex:0 0 auto}
.chips{display:flex;flex-wrap:wrap;gap:5px}
.cmts{display:flex;flex-direction:column;gap:4px;margin-top:6px}
.cmt{background:#12151a;border:1px solid #20242b;border-radius:6px;padding:5px 8px;font-size:12px;color:var(--txt)}
.cmt .cu{font-weight:600}
.cmt .cu.staff{color:#5bbf8a}
.logbox{background:#0b0d10;border:1px solid #20242b;border-radius:6px;padding:10px;font:11px/1.5 ui-monospace,monospace;color:#b7c0cc;max-height:340px;overflow:auto;white-space:pre-wrap;word-break:break-all;margin:6px 0}
#grid.disc{display:block}
.drow{margin-bottom:20px}
.rowh{font-size:16px;margin:4px 2px 10px}
.rowh span{color:var(--mut);font-weight:400;font-size:12px}
.strip{display:flex;gap:12px;overflow-x:auto;padding-bottom:8px}
.pcard{flex:0 0 128px;cursor:pointer}
.pcover{aspect-ratio:3/4;border-radius:var(--radius);background:#0b0d10 center/cover no-repeat;position:relative;border:1px solid var(--border);box-shadow:var(--shadow);transition:border-color .15s,transform .15s}
.pcard:hover .pcover{border-color:var(--acc);transform:translateY(-3px)}
.pcover .have2{position:absolute;top:6px;right:6px;background:#1e5e3a;color:#fff;border-radius:10px;padding:1px 7px;font-size:12px}
.pt{font-size:12px;margin-top:6px;line-height:1.2;max-height:2.4em;overflow:hidden}
#settings{display:none}
.setwrap{display:flex;gap:20px;padding:18px}
.setnav{flex:0 0 170px;display:flex;flex-direction:column;gap:4px}
.snav{padding:9px 12px;border-radius:8px;color:var(--mut);cursor:pointer;font-size:14px}
.snav.on{background:var(--acc);color:#fff}
#setcontent{flex:1;max-width:620px}
#setcontent h3{font-size:12px;text-transform:uppercase;color:var(--mut);letter-spacing:.05em;margin:0 0 10px}
.frow{display:flex;gap:10px;align-items:center;margin:8px 0;justify-content:space-between}
.frow>label:first-child{min-width:130px;color:var(--mut);font-size:13px;flex:0 0 auto}
.frow input,.frow select{background:#0b0d10;border:1px solid #2c323b;color:var(--txt);padding:8px;border-radius:6px;flex:1;min-width:60px}
.frow input[type=checkbox]{flex:0 0 auto}
#setcontent button{background:var(--acc);border:none;color:#fff;padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;margin-top:6px}
@media(max-width:680px){.setwrap{flex-direction:column}.setnav{flex-direction:row;flex-wrap:wrap}}
</style></head><body>
<div id=side>
 <div class=logo>🎮 Romseerr</div>
 <a class="nav on" id=nS data-i18n=nav_discover onclick="show('s')">🔍 Entdecken</a>
 <a class=nav id=nJ data-i18n=nav_requests onclick="show('j')">📥 Anfragen</a>
 <a class=nav id=nI data-i18n=nav_issues onclick="show('issues')">🐞 Probleme</a>
 <a class=nav id=nC data-i18n=nav_coverage onclick="show('cov')">📊 Abdeckung</a>
 <a class=nav id=nM onclick="show('msg')">✉ <span data-i18n=nav_messages>Nachrichten</span><span id=msgbadge></span></a>
 <a class=nav id=nSet data-i18n=nav_settings onclick="show('set')" style="display:none">⚙️ Einstellungen</a>
 <div class=grow></div>
 <div id=langsw><b data-l=de class=on onclick="setLang('de')">DE</b><b data-l=en onclick="setLang('en')">EN</b><b data-l=fr onclick="setLang('fr')">FR</b><b data-l=es onclick="setLang('es')">ES</b><b data-l=it onclick="setLang('it')">IT</b></div>
 <div class=ubox><div id=who onclick="openProfile()" style="cursor:pointer"></div>
  <a class=nav data-i18n=profile onclick="openProfile()">👤 Profil</a>
  <a class=nav data-i18n=logout onclick="logout()">🚪 Abmelden</a></div>
</div>
<main>
 <div id=topbar>
  <input id=q data-i18n-ph=search_ph placeholder="Spiel suchen … (Enter)" autofocus>
  <button class=fbtn id=tF onclick="toggleFilter()">🎛 Plattformen: Alle</button>
  <button class=fbtn id=tRA onclick="toggleRA()" title="RetroAchievements">🏆</button>
 </div>
 <div id=filter></div>
 <div id=discview><div id=grid></div><div class=hint id=hint data-i18n=hint_type>Tippe einen Titel und drücke Enter.</div></div>
 <div id=jobs></div>
 <div id=settings></div>
 <div id=issues></div>
 <div id=messages></div>
 <div id=coverage></div>
</main>
<div id=modal></div>
<script>
const I18N={de:{
 nav_discover:'🔍 Entdecken',nav_requests:'📥 Anfragen',nav_users:'👤 Benutzer',nav_settings:'⚙️ Einstellungen',logout:'🚪 Abmelden',
 search_ph:'Spiel suchen … (Enter)',platforms:'Plattformen',all:'Alle',selected:'gewählt',
 hint_type:'Tippe einen Titel und drücke Enter.',loading_home:'Lade Startseite …',popular_on:'Beliebt auf',click_search:'klick zum Suchen',
 searching:'Suche läuft …',no_results:'Keine Treffer.',results:'Treffer',in_library:'✓ in Bibliothek',download:'⬇ Download',requested:'✓ angefragt',collection:'Sammlung',
 versions:'Versionen / Quellen',files:'Dateien',no_desc:'Keine Beschreibung verfügbar.',screenshots:'Screenshots',similar:'Ähnliche Spiele',series:'Reihe',because_you:'Weil du angefragt hast:',
 no_requests:'Noch keine Anfragen.',approve:'Freigeben',deny:'Ablehnen',retry:'Erneut',reset:'Alle zurücksetzen',req_all:'Alle anfragen',flt_user:'Nutzer',flt_all:'Alle',wishlist:'Wunschliste',nav_coverage:'Abdeckung',ra_achievements:'Achievements',ra_points:'Punkte',ra_earned:'erreicht',ra_user:'RetroAchievements-Konto (optional)',ra_refresh:'Sets holen',ra_sets:'Sets',ra_nokey:'kein API-Key hinterlegt',ra_unmapped:'ohne Konsolen-Zuordnung',ra_only:'nur mit Achievements',cov_of:'von',cov_src:'Quelle',cov_asof:'Stand',cov_files:'Dateien',cov_missing:'fehlende Titel',cov_refresh:'Katalog aktualisieren',cov_nosnap:'keine Momentaufnahme — Katalog noch nicht geholt',cov_nosource:'keine Katalogquelle für diese Plattform',cov_basis:'Grundlage ist eine Momentaufnahme aus {src} (max. {max} Titel je Plattform). Metadatensätze sind sich uneins, was als eigener Titel zählt — die Prozentzahl ist eine Orientierung, kein Messwert.',cov_search:'Suchen',cov_none:'Nichts fehlt (oder kein Katalog).',cov_filter:'Filtern …',cov_filter_do:'Filtern',cov_wish_sel:'Auswahl auf die Wunschliste',wl_import:'Import',wl_imp_hint:'Liste einfügen oder Datei wählen (TXT/CSV) — ein Titel je Zeile, optional Titel;Plattform. Nichts wird geschrieben, bevor du die Vorschau bestätigst.',wl_imp_example:'Beispieldatei herunterladen',wl_imp_ph:'Chrono Trigger\\nSuper Metroid;snes',wl_imp_preview:'Vorschau',wl_imp_apply:'Übernehmen',wl_imp_none:'Nichts ausgewählt.',wl_imp_done:'{a} übernommen, {s} übersprungen.',wl_imp_trunc:'Nur die ersten {n} Zeilen werden geprüft.',wl_imp_toobig:'Datei zu groß (max. 200 kB).',wl_imp_nocheck:'Ohne IGDB-Zugang kein Katalogabgleich — Einträge werden ungeprüft übernommen.',wl_s_matched:'getroffen',wl_s_ambiguous:'mehrdeutig',wl_s_notfound:'nicht gefunden',wl_s_duplicate:'schon gemerkt',wl_s_inlib:'schon vorhanden',wl_s_unverified:'ungeprüft',add_wishlist:'⭐ Merken',wl_added:'⭐ gemerkt',wl_empty:'Wunschliste leer.',wl_remove:'Entfernen',
 users:'Benutzer',new_user:'Neuen Benutzer anlegen',create:'Anlegen',del:'Löschen',autoapprove:'Auto-Freigabe',role_user:'Nutzer',role_admin:'Admin',username:'Benutzername',password:'Passwort',
 notif_discord:'Benachrichtigungen — Discord',active:'aktiv',test:'Test',save:'Speichern',saved:'gespeichert ✓',test_sent:'Test gesendet ✓',webhook_ph:'Discord Webhook-URL',
 st_pending:'⏳ Wartet auf Freigabe',st_queued:'Angefragt',st_downloading:'Lädt…',st_importing:'Wird verarbeitet',st_done:'✅ Verfügbar',st_error:'Fehler',st_denied:'Abgelehnt',st_exists:'vorhanden',
 settings:'Einstellungen',sec_general:'Allgemein',sec_notif:'Benachrichtigungen',sec_users:'Benutzer',sec_services:'Dienste',sec_about:'Über',app_name:'App-Name',default_lang:'Standardsprache',refresh:'Aktualisieren',version:'Version',about_build:'Build',upd_avail:'Update verfügbar:',upd_current:'aktuell',about_txt:'Selbstgebauter Seerr-Klon für ROMs.',wiz_welcome:'Willkommen bei Romseerr',wiz_welcome_txt:'Dieser Assistent verbindet dich Schritt für Schritt mit den Diensten des Stacks (SABnzbd, Prowlarr, IGDB, RomM). Jeden Schritt kannst du testen oder überspringen.',wiz_done:'Fertig!',wiz_done_txt:'Die Grundkonfiguration steht. Alles lässt sich später unter Einstellungen → Verbindungen anpassen.',wiz_next:'Weiter',wiz_back:'Zurück',wiz_skip:'Überspringen',wiz_finish:'Loslegen',wiz_step:'Schritt',wiz_reopen:'Assistent erneut öffnen',about_lib:'Bibliothek',about_titles:'Titel',about_platforms:'Plattformen',about_jobs:'Anfragen',about_active:'aktiv',about_links:'Links',about_feat:'Funktionen',about_feat_txt:'Suche über Archive.org + Usenet, Dedup, Discover, Anfragen mit Freigabe, Benutzer & Rechte, Kontingente, Benachrichtigungen (Discord/Telegram/E-Mail/Web-Push), Probleme, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestriert Prowlarr, SABnzbd, JDownloader und RomM. Verbindungen in den Einstellungen konfigurierbar.',about_license:'Lizenz: MIT',sec_maint:'Logs & Wartung',exp_title:'Export / Import',exp_hint:'Sichert Einstellungen, Benutzer & Rechte, Anfragen und Wunschlisten als JSON. Ohne Passphrase bleiben Geheimnisse (Kennwörter, API-Keys, Webhook-URLs) AUSSEN VOR — mit Passphrase werden sie verschlüsselt beigelegt. Dieselbe Passphrase wird beim Import gebraucht.',exp_pass:'Passphrase',exp_pass_ph:'leer = ohne Geheimnisse',exp_do:'Exportieren',exp_merge:'Zusammenführen',exp_replace:'Ersetzen',imp_do:'Importieren',exp_done_plain:'Exportiert (ohne Geheimnisse).',exp_done_enc:'Exportiert (Geheimnisse verschlüsselt).',imp_nofile:'Keine Datei gewählt.',imp_badjson:'Datei ist kein gültiges JSON.',imp_conf_merge:'Import zusammenführen? Bestehende Werte werden überschrieben, nicht genannte bleiben.',imp_conf_replace:'ERSETZEN? Benutzer, Anfragen und Wunschlisten werden vollständig durch die Datei ersetzt.',imp_done:'Importiert:',logs:'Protokoll',clear_cache:'Cache leeren',reindex:'Neu indexieren',clear_finished:'Fertige entfernen',done_word:'Erledigt',lbl_jobs:'Anfragen',lbl_lib:'Bibliothek',sec_conn:'Verbindungen',reveal:'Klartext anzeigen',tls_hint:'Cert + Schlüssel (PEM) hinterlegen — die App startet dann zusätzlich einen HTTPS-Listener auf dem gewählten Port (Neustart nötig). Für Web-Push/PWA ohne separaten Reverse-Proxy.',tls_none:'kein Zertifikat hinterlegt',tls_expires:'gültig bis',tls_key_note:'privater Schlüssel — wird nie angezeigt',tls_restart:'Container neu starten zum Aktivieren',conn_hint:'Leere Felder nutzen den Wert aus der Umgebung (.env). Secrets sind maskiert — leer lassen behält den bestehenden Wert.',
 profile:'Profil',display_name:'Anzeigename',email:'E-Mail',language:'Sprache',design:'Design',default_design:'Standard-Design',d_seerr:'Seerr',d_glass:'Glas',d_clean:'Klar',avatar:'Avatar',pwebhook:'Persönlicher Discord-Webhook',change_pw:'Passwort ändern',cur_pw:'Aktuelles Passwort',new_pw:'Neues Passwort',choose_img:'Bild wählen',saved_ok:'gespeichert ✓',
 blocklist:'Sperrliste',add_btn:'Hinzufügen',pattern_ph:'Stichwort/Muster im Titel',
 nav_issues:'🐞 Probleme',nav_messages:'Nachrichten',msg_to:'An',msg_none:'Noch keine Nachrichten.',msg_ph:'Nachricht schreiben …',msg_send:'Senden',msg_hint:'Strg+Enter sendet',msg_nousers:'Keine anderen Benutzer.',req_for:'Anfrage für',req_self:'mich selbst',issues:'Probleme',report_issue:'Problem melden',issue_msg:'Beschreibung',close_btn:'Schließen',st_open:'offen',st_closed:'geschlossen',submit:'Absenden',issue_type:'Art',comment_ph:'Kommentar schreiben …',comment_send:'Senden',push_enable:'🔔 Push aktivieren',push_disable:'🔕 Push deaktivieren',push_unsupported:'Push nicht verfügbar (HTTPS nötig)',push_denied:'Erlaubnis verweigert',push_on:'Push aktiviert ✓',push_off:'Push deaktiviert'
},en:{
 nav_discover:'🔍 Discover',nav_requests:'📥 Requests',nav_users:'👤 Users',nav_settings:'⚙️ Settings',logout:'🚪 Sign out',
 search_ph:'Search a game … (Enter)',platforms:'Platforms',all:'All',selected:'selected',
 hint_type:'Type a title and press Enter.',loading_home:'Loading home …',popular_on:'Popular on',click_search:'click to search',
 searching:'Searching …',no_results:'No results.',results:'results',in_library:'✓ in library',download:'⬇ Download',requested:'✓ requested',collection:'Collection',
 versions:'Versions / sources',files:'Files',no_desc:'No description available.',screenshots:'Screenshots',similar:'Similar games',series:'Series',because_you:'Because you requested:',
 no_requests:'No requests yet.',approve:'Approve',deny:'Deny',retry:'Retry',reset:'Reset all',req_all:'Request all',flt_user:'User',flt_all:'All',wishlist:'Wishlist',nav_coverage:'Coverage',ra_achievements:'achievements',ra_points:'points',ra_earned:'earned',ra_user:'RetroAchievements account (optional)',ra_refresh:'Fetch sets',ra_sets:'sets',ra_nokey:'no API key stored',ra_unmapped:'no console mapping',ra_only:'with achievements only',cov_of:'of',cov_src:'Source',cov_asof:'as of',cov_files:'files',cov_missing:'missing titles',cov_refresh:'Refresh catalogue',cov_nosnap:'no snapshot — catalogue not fetched yet',cov_nosource:'no catalogue source for this platform',cov_basis:'Based on a snapshot from {src} (max {max} titles per platform). Metadata sets disagree about what counts as a distinct title — the percentage is an orientation, not a measurement.',cov_search:'Search',cov_none:'Nothing missing (or no catalogue).',cov_filter:'Filter …',cov_filter_do:'Filter',cov_wish_sel:'Selection to wishlist',wl_import:'Import',wl_imp_hint:'Paste a list or pick a file (TXT/CSV) — one title per line, optionally title;platform. Nothing is written until you confirm the preview.',wl_imp_example:'Download example file',wl_imp_ph:'Chrono Trigger\\nSuper Metroid;snes',wl_imp_preview:'Preview',wl_imp_apply:'Import',wl_imp_none:'Nothing selected.',wl_imp_done:'{a} imported, {s} skipped.',wl_imp_trunc:'Only the first {n} lines are checked.',wl_imp_toobig:'File too large (max 200 kB).',wl_imp_nocheck:'No IGDB credentials — no catalogue check; entries are imported unverified.',wl_s_matched:'matched',wl_s_ambiguous:'ambiguous',wl_s_notfound:'not found',wl_s_duplicate:'already listed',wl_s_inlib:'already in library',wl_s_unverified:'unverified',add_wishlist:'⭐ Watch',wl_added:'⭐ watched',wl_empty:'Wishlist empty.',wl_remove:'Remove',
 users:'Users',new_user:'Create new user',create:'Create',del:'Delete',autoapprove:'Auto-approve',role_user:'User',role_admin:'Admin',username:'Username',password:'Password',
 notif_discord:'Notifications — Discord',active:'enabled',test:'Test',save:'Save',saved:'saved ✓',test_sent:'test sent ✓',webhook_ph:'Discord webhook URL',
 st_pending:'⏳ Awaiting approval',st_queued:'Requested',st_downloading:'Downloading…',st_importing:'Processing',st_done:'✅ Available',st_error:'Error',st_denied:'Denied',st_exists:'in library',
 settings:'Settings',sec_general:'General',sec_notif:'Notifications',sec_users:'Users',sec_services:'Services',sec_about:'About',app_name:'App name',default_lang:'Default language',refresh:'Refresh',version:'Version',about_build:'Build',upd_avail:'Update available:',upd_current:'up to date',about_txt:'Self-built Seerr clone for ROMs.',wiz_welcome:'Welcome to Romseerr',wiz_welcome_txt:'This wizard connects you to the stack services (SABnzbd, Prowlarr, IGDB, RomM) step by step. You can test or skip each step.',wiz_done:'All set!',wiz_done_txt:'Basic configuration is done. You can adjust everything later under Settings → Connections.',wiz_next:'Next',wiz_back:'Back',wiz_skip:'Skip',wiz_finish:'Get started',wiz_step:'Step',wiz_reopen:'Reopen wizard',about_lib:'Library',about_titles:'titles',about_platforms:'platforms',about_jobs:'Requests',about_active:'active',about_links:'Links',about_feat:'Features',about_feat_txt:'Search across Archive.org + Usenet, dedup, discover, requests with approval, users & permissions, quotas, notifications (Discord/Telegram/email/web push), issues, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestrates Prowlarr, SABnzbd, JDownloader and RomM. Connections configurable under Settings.',about_license:'License: MIT',sec_maint:'Logs & maintenance',exp_title:'Export / import',exp_hint:'Saves settings, users & permissions, requests and wishlists as JSON. Without a passphrase, secrets (passwords, API keys, webhook URLs) are LEFT OUT — with one they are attached encrypted. The same passphrase is needed on import.',exp_pass:'Passphrase',exp_pass_ph:'empty = without secrets',exp_do:'Export',exp_merge:'Merge',exp_replace:'Replace',imp_do:'Import',exp_done_plain:'Exported (without secrets).',exp_done_enc:'Exported (secrets encrypted).',imp_nofile:'No file selected.',imp_badjson:'File is not valid JSON.',imp_conf_merge:'Merge this import? Existing values are overwritten, anything not mentioned stays.',imp_conf_replace:'REPLACE? Users, requests and wishlists are fully replaced by the file.',imp_done:'Imported:',logs:'Log',clear_cache:'Clear cache',reindex:'Reindex',clear_finished:'Clear finished',done_word:'Done',lbl_jobs:'Requests',lbl_lib:'Library',sec_conn:'Connections',reveal:'Show in clear text',tls_hint:'Provide cert + key (PEM) — the app then also starts an HTTPS listener on the chosen port (restart required). For web push/PWA without a separate reverse proxy.',tls_none:'no certificate stored',tls_expires:'valid until',tls_key_note:'private key — never shown',tls_restart:'restart the container to activate',conn_hint:'Empty fields fall back to the environment (.env). Secrets are masked — leave blank to keep the current value.',
 profile:'Profile',display_name:'Display name',email:'Email',language:'Language',design:'Design',default_design:'Default design',d_seerr:'Seerr',d_glass:'Glass',d_clean:'Clean',avatar:'Avatar',pwebhook:'Personal Discord webhook',change_pw:'Change password',cur_pw:'Current password',new_pw:'New password',choose_img:'Choose image',saved_ok:'saved ✓',
 blocklist:'Blocklist',add_btn:'Add',pattern_ph:'Keyword/pattern in title',
 nav_issues:'🐞 Issues',nav_messages:'Messages',msg_to:'To',msg_none:'No messages yet.',msg_ph:'Write a message …',msg_send:'Send',msg_hint:'Ctrl+Enter sends',msg_nousers:'No other users.',req_for:'Request for',req_self:'myself',issues:'Issues',report_issue:'Report issue',issue_msg:'Message',close_btn:'Close',st_open:'open',st_closed:'closed',submit:'Submit',issue_type:'Type',comment_ph:'Write a comment …',comment_send:'Send',push_enable:'🔔 Enable push',push_disable:'🔕 Disable push',push_unsupported:'Push unavailable (needs HTTPS)',push_denied:'Permission denied',push_on:'Push enabled ✓',push_off:'Push disabled'
},fr:{
 nav_discover:'🔍 Découvrir',nav_requests:'📥 Demandes',nav_users:'👤 Utilisateurs',nav_settings:'⚙️ Paramètres',logout:'🚪 Déconnexion',
 search_ph:'Rechercher un jeu … (Entrée)',platforms:'Plateformes',all:'Toutes',selected:'sélectionné',
 hint_type:'Saisissez un titre et appuyez sur Entrée.',loading_home:'Chargement …',popular_on:'Populaire sur',click_search:'cliquer pour rechercher',
 searching:'Recherche …',no_results:'Aucun résultat.',results:'résultats',in_library:'✓ dans la bibliothèque',download:'⬇ Télécharger',requested:'✓ demandé',collection:'Collection',
 versions:'Versions / sources',files:'Fichiers',no_desc:'Aucune description disponible.',screenshots:'Captures',similar:'Jeux similaires',series:'Série',because_you:'Parce que vous avez demandé :',
 no_requests:'Aucune demande.',approve:'Approuver',deny:'Refuser',retry:'Réessayer',reset:'Tout réinitialiser',req_all:'Tout demander',flt_user:'Utilisateur',flt_all:'Tous',wishlist:'Liste de souhaits',nav_coverage:'Couverture',ra_achievements:'succès',ra_points:'points',ra_earned:'obtenus',ra_user:'Compte RetroAchievements (optionnel)',ra_refresh:'Récupérer les sets',ra_sets:'sets',ra_nokey:'aucune clé API',ra_unmapped:'sans correspondance de console',ra_only:'avec succès seulement',cov_of:'sur',cov_src:'Source',cov_asof:'au',cov_files:'fichiers',cov_missing:'titres manquants',cov_refresh:'Actualiser le catalogue',cov_nosnap:'pas d’instantané — catalogue pas encore récupéré',cov_nosource:'pas de source de catalogue pour cette plateforme',cov_basis:'Basé sur un instantané de {src} (max {max} titres par plateforme). Les jeux de métadonnées ne s’accordent pas sur ce qui compte comme titre distinct — le pourcentage est une orientation, pas une mesure.',cov_search:'Chercher',cov_none:'Rien ne manque (ou pas de catalogue).',cov_filter:'Filtrer …',cov_filter_do:'Filtrer',cov_wish_sel:'Sélection vers la liste',wl_import:'Import',wl_imp_hint:'Collez une liste ou choisissez un fichier (TXT/CSV) — un titre par ligne, éventuellement titre;plateforme. Rien n’est écrit avant votre confirmation.',wl_imp_example:'Télécharger un exemple',wl_imp_ph:'Chrono Trigger\\nSuper Metroid;snes',wl_imp_preview:'Aperçu',wl_imp_apply:'Importer',wl_imp_none:'Rien de sélectionné.',wl_imp_done:'{a} importés, {s} ignorés.',wl_imp_trunc:'Seules les {n} premières lignes sont vérifiées.',wl_imp_toobig:'Fichier trop grand (max 200 ko).',wl_imp_nocheck:'Sans accès IGDB, pas de vérification — les entrées sont importées telles quelles.',wl_s_matched:'trouvé',wl_s_ambiguous:'ambigu',wl_s_notfound:'introuvable',wl_s_duplicate:'déjà suivi',wl_s_inlib:'déjà présent',wl_s_unverified:'non vérifié',add_wishlist:'⭐ Suivre',wl_added:'⭐ suivi',wl_empty:'Liste vide.',wl_remove:'Retirer',
 users:'Utilisateurs',new_user:'Créer un utilisateur',create:'Créer',del:'Supprimer',autoapprove:'Approbation auto',role_user:'Utilisateur',role_admin:'Admin',username:"Nom d'utilisateur",password:'Mot de passe',
 notif_discord:'Notifications — Discord',active:'activé',test:'Test',save:'Enregistrer',saved:'enregistré ✓',test_sent:'test envoyé ✓',webhook_ph:'URL du webhook Discord',
 st_pending:"⏳ En attente d'approbation",st_queued:'Demandé',st_downloading:'Téléchargement…',st_importing:'Traitement',st_done:'✅ Disponible',st_error:'Erreur',st_denied:'Refusé',st_exists:'présent',
 settings:'Paramètres',sec_general:'Général',sec_notif:'Notifications',sec_users:'Utilisateurs',sec_services:'Services',sec_about:'À propos',app_name:"Nom de l'app",default_lang:'Langue par défaut',refresh:'Actualiser',version:'Version',about_build:'Build',upd_avail:'Mise à jour disponible :',upd_current:'à jour',about_txt:'Clone de Seerr pour ROMs, fait maison.',wiz_welcome:'Bienvenue sur Romseerr',wiz_welcome_txt:'Cet assistant vous connecte aux services du stack (SABnzbd, Prowlarr, IGDB, RomM) étape par étape. Vous pouvez tester ou passer chaque étape.',wiz_done:'Terminé !',wiz_done_txt:'La configuration de base est prête. Vous pouvez tout ajuster plus tard dans Paramètres → Connexions.',wiz_next:'Suivant',wiz_back:'Retour',wiz_skip:'Passer',wiz_finish:'Commencer',wiz_step:'Étape',wiz_reopen:'Rouvrir l’assistant',about_lib:'Bibliothèque',about_titles:'titres',about_platforms:'plateformes',about_jobs:'Demandes',about_active:'actives',about_links:'Liens',about_feat:'Fonctions',about_feat_txt:'Recherche Archive.org + Usenet, dédup, découverte, demandes avec approbation, utilisateurs & droits, quotas, notifications, problèmes, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestre Prowlarr, SABnzbd, JDownloader et RomM. Connexions configurables dans Paramètres.',about_license:'Licence : MIT',sec_maint:'Journaux & maintenance',exp_title:'Export / import',exp_hint:'Sauvegarde paramètres, utilisateurs & droits, demandes et listes de souhaits en JSON. Sans phrase secrète, les secrets (mots de passe, clés API, URLs de webhook) sont EXCLUS — avec, ils sont joints chiffrés. La même phrase est requise à l’import.',exp_pass:'Phrase secrète',exp_pass_ph:'vide = sans secrets',exp_do:'Exporter',exp_merge:'Fusionner',exp_replace:'Remplacer',imp_do:'Importer',exp_done_plain:'Exporté (sans secrets).',exp_done_enc:'Exporté (secrets chiffrés).',imp_nofile:'Aucun fichier choisi.',imp_badjson:'Le fichier n’est pas du JSON valide.',imp_conf_merge:'Fusionner cet import ? Les valeurs existantes sont écrasées.',imp_conf_replace:'REMPLACER ? Utilisateurs, demandes et listes seront entièrement remplacés.',imp_done:'Importé :',logs:'Journal',clear_cache:'Vider le cache',reindex:'Réindexer',clear_finished:'Effacer terminés',done_word:'Terminé',lbl_jobs:'Demandes',lbl_lib:'Bibliothèque',sec_conn:'Connexions',reveal:'Afficher en clair',tls_hint:'Fournir le certificat + la clé (PEM) — l’app démarre alors un écouteur HTTPS sur le port choisi (redémarrage requis).',tls_none:'aucun certificat',tls_expires:'valide jusqu’au',tls_key_note:'clé privée — jamais affichée',tls_restart:'redémarrer le conteneur pour activer',conn_hint:'Les champs vides utilisent la valeur de l’environnement (.env). Les secrets sont masqués — laisser vide conserve la valeur.',
 profile:'Profil',display_name:'Nom affiché',email:'E-mail',language:'Langue',design:'Thème',default_design:'Thème par défaut',d_seerr:'Seerr',d_glass:'Verre',d_clean:'Épuré',avatar:'Avatar',pwebhook:'Webhook Discord personnel',change_pw:'Changer le mot de passe',cur_pw:'Mot de passe actuel',new_pw:'Nouveau mot de passe',choose_img:'Choisir une image',saved_ok:'enregistré ✓',
 blocklist:'Liste de blocage',add_btn:'Ajouter',pattern_ph:'Mot-clé/motif dans le titre',
 nav_issues:'🐞 Problèmes',nav_messages:'Messages',msg_to:'À',msg_none:'Aucun message.',msg_ph:'Écrire un message …',msg_send:'Envoyer',msg_hint:'Ctrl+Entrée envoie',msg_nousers:'Aucun autre utilisateur.',req_for:'Demande pour',req_self:'moi-même',issues:'Problèmes',report_issue:'Signaler un problème',issue_msg:'Message',close_btn:'Fermer',st_open:'ouvert',st_closed:'fermé',submit:'Envoyer',issue_type:'Type',comment_ph:'Écrire un commentaire …',comment_send:'Envoyer',push_enable:'🔔 Activer push',push_disable:'🔕 Désactiver push',push_unsupported:'Push indisponible (HTTPS requis)',push_denied:'Permission refusée',push_on:'Push activé ✓',push_off:'Push désactivé'
},es:{
 nav_discover:'🔍 Descubrir',nav_requests:'📥 Solicitudes',nav_users:'👤 Usuarios',nav_settings:'⚙️ Ajustes',logout:'🚪 Salir',
 search_ph:'Buscar un juego … (Intro)',platforms:'Plataformas',all:'Todas',selected:'seleccionado',
 hint_type:'Escribe un título y pulsa Intro.',loading_home:'Cargando …',popular_on:'Popular en',click_search:'clic para buscar',
 searching:'Buscando …',no_results:'Sin resultados.',results:'resultados',in_library:'✓ en la biblioteca',download:'⬇ Descargar',requested:'✓ solicitado',collection:'Colección',
 versions:'Versiones / fuentes',files:'Archivos',no_desc:'Sin descripción disponible.',screenshots:'Capturas',similar:'Juegos similares',series:'Serie',because_you:'Porque solicitaste:',
 no_requests:'Aún no hay solicitudes.',approve:'Aprobar',deny:'Rechazar',retry:'Reintentar',reset:'Restablecer todo',req_all:'Solicitar todo',flt_user:'Usuario',flt_all:'Todos',wishlist:'Lista de deseos',nav_coverage:'Cobertura',ra_achievements:'logros',ra_points:'puntos',ra_earned:'obtenidos',ra_user:'Cuenta RetroAchievements (opcional)',ra_refresh:'Obtener sets',ra_sets:'sets',ra_nokey:'sin clave API',ra_unmapped:'sin correspondencia de consola',ra_only:'solo con logros',cov_of:'de',cov_src:'Fuente',cov_asof:'a fecha',cov_files:'archivos',cov_missing:'títulos que faltan',cov_refresh:'Actualizar catálogo',cov_nosnap:'sin instantánea — catálogo aún no obtenido',cov_nosource:'sin fuente de catálogo para esta plataforma',cov_basis:'Basado en una instantánea de {src} (máx. {max} títulos por plataforma). Los conjuntos de metadatos no coinciden en qué cuenta como título propio — el porcentaje orienta, no mide.',cov_search:'Buscar',cov_none:'No falta nada (o no hay catálogo).',cov_filter:'Filtrar …',cov_filter_do:'Filtrar',cov_wish_sel:'Selección a la lista',wl_import:'Importar',wl_imp_hint:'Pega una lista o elige un archivo (TXT/CSV) — un título por línea, opcionalmente título;plataforma. No se escribe nada hasta que confirmes.',wl_imp_example:'Descargar archivo de ejemplo',wl_imp_ph:'Chrono Trigger\\nSuper Metroid;snes',wl_imp_preview:'Vista previa',wl_imp_apply:'Importar',wl_imp_none:'Nada seleccionado.',wl_imp_done:'{a} importados, {s} omitidos.',wl_imp_trunc:'Solo se comprueban las primeras {n} líneas.',wl_imp_toobig:'Archivo demasiado grande (máx. 200 kB).',wl_imp_nocheck:'Sin acceso a IGDB no hay comprobación — se importan sin verificar.',wl_s_matched:'encontrado',wl_s_ambiguous:'ambiguo',wl_s_notfound:'no encontrado',wl_s_duplicate:'ya en la lista',wl_s_inlib:'ya en biblioteca',wl_s_unverified:'sin verificar',add_wishlist:'⭐ Seguir',wl_added:'⭐ en lista',wl_empty:'Lista vacía.',wl_remove:'Quitar',
 users:'Usuarios',new_user:'Crear usuario',create:'Crear',del:'Eliminar',autoapprove:'Auto-aprobación',role_user:'Usuario',role_admin:'Admin',username:'Usuario',password:'Contraseña',
 notif_discord:'Notificaciones — Discord',active:'activo',test:'Prueba',save:'Guardar',saved:'guardado ✓',test_sent:'prueba enviada ✓',webhook_ph:'URL del webhook de Discord',
 st_pending:'⏳ Esperando aprobación',st_queued:'Solicitado',st_downloading:'Descargando…',st_importing:'Procesando',st_done:'✅ Disponible',st_error:'Error',st_denied:'Rechazado',st_exists:'presente',
 settings:'Ajustes',sec_general:'General',sec_notif:'Notificaciones',sec_users:'Usuarios',sec_services:'Servicios',sec_about:'Acerca de',app_name:'Nombre de la app',default_lang:'Idioma predeterminado',refresh:'Actualizar',version:'Versión',about_build:'Build',upd_avail:'Actualización disponible:',upd_current:'actualizado',about_txt:'Clon de Seerr para ROMs, hecho en casa.',wiz_welcome:'Bienvenido a Romseerr',wiz_welcome_txt:'Este asistente te conecta con los servicios del stack (SABnzbd, Prowlarr, IGDB, RomM) paso a paso. Puedes probar u omitir cada paso.',wiz_done:'¡Listo!',wiz_done_txt:'La configuración básica está hecha. Puedes ajustar todo luego en Ajustes → Conexiones.',wiz_next:'Siguiente',wiz_back:'Atrás',wiz_skip:'Omitir',wiz_finish:'Empezar',wiz_step:'Paso',wiz_reopen:'Reabrir asistente',about_lib:'Biblioteca',about_titles:'títulos',about_platforms:'plataformas',about_jobs:'Solicitudes',about_active:'activas',about_links:'Enlaces',about_feat:'Funciones',about_feat_txt:'Búsqueda en Archive.org + Usenet, dedup, descubrir, solicitudes con aprobación, usuarios y permisos, cuotas, notificaciones, problemas, PWA, API.',about_stack:'Stack',about_stack_txt:'Orquesta Prowlarr, SABnzbd, JDownloader y RomM. Conexiones configurables en Ajustes.',about_license:'Licencia: MIT',sec_maint:'Registros y mantenimiento',exp_title:'Exportar / importar',exp_hint:'Guarda ajustes, usuarios y permisos, solicitudes y listas de deseos como JSON. Sin frase de contraseña los secretos (contraseñas, claves API, URLs de webhook) QUEDAN FUERA — con ella se adjuntan cifrados. La misma frase hace falta al importar.',exp_pass:'Frase de contraseña',exp_pass_ph:'vacío = sin secretos',exp_do:'Exportar',exp_merge:'Combinar',exp_replace:'Reemplazar',imp_do:'Importar',exp_done_plain:'Exportado (sin secretos).',exp_done_enc:'Exportado (secretos cifrados).',imp_nofile:'Ningún archivo seleccionado.',imp_badjson:'El archivo no es JSON válido.',imp_conf_merge:'¿Combinar esta importación? Los valores existentes se sobrescriben.',imp_conf_replace:'¿REEMPLAZAR? Usuarios, solicitudes y listas se sustituyen por completo.',imp_done:'Importado:',logs:'Registro',clear_cache:'Vaciar caché',reindex:'Reindexar',clear_finished:'Borrar terminados',done_word:'Hecho',lbl_jobs:'Solicitudes',lbl_lib:'Biblioteca',sec_conn:'Conexiones',reveal:'Mostrar en texto plano',tls_hint:'Proporciona certificado + clave (PEM) — la app inicia además un listener HTTPS en el puerto elegido (requiere reinicio).',tls_none:'sin certificado',tls_expires:'válido hasta',tls_key_note:'clave privada — nunca se muestra',tls_restart:'reinicia el contenedor para activar',conn_hint:'Los campos vacíos usan el valor del entorno (.env). Los secretos se enmascaran — dejar vacío conserva el valor.',
 profile:'Perfil',display_name:'Nombre visible',email:'Correo',language:'Idioma',design:'Diseño',default_design:'Diseño predeterminado',d_seerr:'Seerr',d_glass:'Cristal',d_clean:'Limpio',avatar:'Avatar',pwebhook:'Webhook de Discord personal',change_pw:'Cambiar contraseña',cur_pw:'Contraseña actual',new_pw:'Nueva contraseña',choose_img:'Elegir imagen',saved_ok:'guardado ✓',
 blocklist:'Lista de bloqueo',add_btn:'Añadir',pattern_ph:'Palabra clave/patrón en el título',
 nav_issues:'🐞 Problemas',nav_messages:'Mensajes',msg_to:'Para',msg_none:'Sin mensajes.',msg_ph:'Escribe un mensaje …',msg_send:'Enviar',msg_hint:'Ctrl+Enter envía',msg_nousers:'No hay otros usuarios.',req_for:'Solicitud para',req_self:'yo mismo',issues:'Problemas',report_issue:'Informar problema',issue_msg:'Mensaje',close_btn:'Cerrar',st_open:'abierto',st_closed:'cerrado',submit:'Enviar',issue_type:'Tipo',comment_ph:'Escribe un comentario …',comment_send:'Enviar',push_enable:'🔔 Activar push',push_disable:'🔕 Desactivar push',push_unsupported:'Push no disponible (requiere HTTPS)',push_denied:'Permiso denegado',push_on:'Push activado ✓',push_off:'Push desactivado'
},it:{
 nav_discover:'🔍 Scopri',nav_requests:'📥 Richieste',nav_users:'👤 Utenti',nav_settings:'⚙️ Impostazioni',logout:'🚪 Esci',
 search_ph:'Cerca un gioco … (Invio)',platforms:'Piattaforme',all:'Tutte',selected:'selezionate',
 hint_type:'Digita un titolo e premi Invio.',loading_home:'Caricamento …',popular_on:'Popolari su',click_search:'clicca per cercare',
 searching:'Ricerca …',no_results:'Nessun risultato.',results:'risultati',in_library:'✓ in libreria',download:'⬇ Scarica',requested:'✓ richiesto',collection:'Collezione',
 versions:'Versioni / fonti',files:'File',no_desc:'Nessuna descrizione disponibile.',screenshots:'Screenshot',similar:'Giochi simili',series:'Serie',because_you:'Perché hai richiesto:',
 no_requests:'Ancora nessuna richiesta.',approve:'Approva',deny:'Rifiuta',retry:'Riprova',reset:'Reimposta tutto',req_all:'Richiedi tutto',flt_user:'Utente',flt_all:'Tutti',wishlist:'Lista dei desideri',nav_coverage:'Copertura',ra_achievements:'obiettivi',ra_points:'punti',ra_earned:'ottenuti',ra_user:'Account RetroAchievements (opzionale)',ra_refresh:'Recupera i set',ra_sets:'set',ra_nokey:'nessuna chiave API',ra_unmapped:'senza mappatura console',ra_only:'solo con obiettivi',cov_of:'di',cov_src:'Fonte',cov_asof:'al',cov_files:'file',cov_missing:'titoli mancanti',cov_refresh:'Aggiorna catalogo',cov_nosnap:'nessuna istantanea — catalogo non ancora recuperato',cov_nosource:'nessuna fonte di catalogo per questa piattaforma',cov_basis:'Basato su un’istantanea da {src} (max {max} titoli per piattaforma). I set di metadati non concordano su cosa sia un titolo distinto — la percentuale orienta, non misura.',cov_search:'Cerca',cov_none:'Non manca nulla (o nessun catalogo).',cov_filter:'Filtra …',cov_filter_do:'Filtra',cov_wish_sel:'Selezione alla lista',wl_import:'Importa',wl_imp_hint:'Incolla un elenco o scegli un file (TXT/CSV) — un titolo per riga, opzionalmente titolo;piattaforma. Nulla viene scritto prima della conferma.',wl_imp_example:'Scarica file di esempio',wl_imp_ph:'Chrono Trigger\\nSuper Metroid;snes',wl_imp_preview:'Anteprima',wl_imp_apply:'Importa',wl_imp_none:'Niente selezionato.',wl_imp_done:'{a} importati, {s} saltati.',wl_imp_trunc:'Vengono controllate solo le prime {n} righe.',wl_imp_toobig:'File troppo grande (max 200 kB).',wl_imp_nocheck:'Senza accesso IGDB nessun controllo — le voci vengono importate non verificate.',wl_s_matched:'trovato',wl_s_ambiguous:'ambiguo',wl_s_notfound:'non trovato',wl_s_duplicate:'già in lista',wl_s_inlib:'già in libreria',wl_s_unverified:'non verificato',add_wishlist:'⭐ Segui',wl_added:'⭐ seguito',wl_empty:'Lista vuota.',wl_remove:'Rimuovi',
 users:'Utenti',new_user:'Crea utente',create:'Crea',del:'Elimina',autoapprove:'Auto-approvazione',role_user:'Utente',role_admin:'Admin',username:'Utente',password:'Password',
 notif_discord:'Notifiche — Discord',active:'attivo',test:'Test',save:'Salva',saved:'salvato ✓',test_sent:'test inviato ✓',webhook_ph:'URL webhook Discord',
 st_pending:'⏳ In attesa di approvazione',st_queued:'Richiesto',st_downloading:'Scaricamento…',st_importing:'Elaborazione',st_done:'✅ Disponibile',st_error:'Errore',st_denied:'Rifiutato',st_exists:'presente',
 settings:'Impostazioni',sec_general:'Generale',sec_notif:'Notifiche',sec_users:'Utenti',sec_services:'Servizi',sec_about:'Informazioni',app_name:'Nome dell’app',default_lang:'Lingua predefinita',refresh:'Aggiorna',version:'Versione',about_build:'Build',upd_avail:'Aggiornamento disponibile:',upd_current:'aggiornato',about_txt:'Clone di Seerr per ROM, fatto in casa.',wiz_welcome:'Benvenuto in Romseerr',wiz_welcome_txt:'Questa procedura ti collega ai servizi dello stack (SABnzbd, Prowlarr, IGDB, RomM) passo dopo passo. Puoi testare o saltare ogni passaggio.',wiz_done:'Fatto!',wiz_done_txt:'La configurazione di base è pronta. Puoi regolare tutto in seguito in Impostazioni → Connessioni.',wiz_next:'Avanti',wiz_back:'Indietro',wiz_skip:'Salta',wiz_finish:'Inizia',wiz_step:'Passo',wiz_reopen:'Riapri procedura',about_lib:'Libreria',about_titles:'titoli',about_platforms:'piattaforme',about_jobs:'Richieste',about_active:'attive',about_links:'Link',about_feat:'Funzioni',about_feat_txt:'Ricerca su Archive.org + Usenet, dedup, scoperta, richieste con approvazione, utenti e permessi, quote, notifiche, problemi, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestra Prowlarr, SABnzbd, JDownloader e RomM. Connessioni configurabili nelle Impostazioni.',about_license:'Licenza: MIT',sec_maint:'Log e manutenzione',exp_title:'Esporta / importa',exp_hint:'Salva impostazioni, utenti e permessi, richieste e liste dei desideri come JSON. Senza passphrase i segreti (password, chiavi API, URL webhook) restano ESCLUSI — con la passphrase vengono allegati cifrati. La stessa passphrase serve all’importazione.',exp_pass:'Passphrase',exp_pass_ph:'vuoto = senza segreti',exp_do:'Esporta',exp_merge:'Unisci',exp_replace:'Sostituisci',imp_do:'Importa',exp_done_plain:'Esportato (senza segreti).',exp_done_enc:'Esportato (segreti cifrati).',imp_nofile:'Nessun file scelto.',imp_badjson:'Il file non è JSON valido.',imp_conf_merge:'Unire questa importazione? I valori esistenti vengono sovrascritti.',imp_conf_replace:'SOSTITUIRE? Utenti, richieste e liste vengono sostituiti del tutto.',imp_done:'Importato:',logs:'Log',clear_cache:'Svuota cache',reindex:'Reindicizza',clear_finished:'Cancella completati',done_word:'Fatto',lbl_jobs:'Richieste',lbl_lib:'Libreria',sec_conn:'Connessioni',reveal:'Mostra in chiaro',tls_hint:'Fornisci certificato + chiave (PEM) — l’app avvia anche un listener HTTPS sulla porta scelta (riavvio necessario).',tls_none:'nessun certificato',tls_expires:'valido fino al',tls_key_note:'chiave privata — mai mostrata',tls_restart:'riavvia il container per attivare',conn_hint:'I campi vuoti usano il valore dell’ambiente (.env). I segreti sono mascherati — lasciare vuoto mantiene il valore.',
 profile:'Profilo',display_name:'Nome visualizzato',email:'E-mail',language:'Lingua',design:'Tema',default_design:'Tema predefinito',d_seerr:'Seerr',d_glass:'Vetro',d_clean:'Pulito',avatar:'Avatar',pwebhook:'Webhook Discord personale',change_pw:'Cambia password',cur_pw:'Password attuale',new_pw:'Nuova password',choose_img:'Scegli immagine',saved_ok:'salvato ✓',
 blocklist:'Lista di blocco',add_btn:'Aggiungi',pattern_ph:'Parola chiave/schema nel titolo',
 nav_issues:'🐞 Problemi',nav_messages:'Messaggi',msg_to:'A',msg_none:'Nessun messaggio.',msg_ph:'Scrivi un messaggio …',msg_send:'Invia',msg_hint:'Ctrl+Invio invia',msg_nousers:'Nessun altro utente.',req_for:'Richiesta per',req_self:'me stesso',issues:'Problemi',report_issue:'Segnala problema',issue_msg:'Messaggio',close_btn:'Chiudi',st_open:'aperto',st_closed:'chiuso',submit:'Invia',issue_type:'Tipo',comment_ph:'Scrivi un commento …',comment_send:'Invia',push_enable:'🔔 Attiva push',push_disable:'🔕 Disattiva push',push_unsupported:'Push non disponibile (richiede HTTPS)',push_denied:'Permesso negato',push_on:'Push attivato ✓',push_off:'Push disattivato'
}};
let LANG=localStorage.getItem('lang')||'de';
// Design (Look) so früh wie möglich setzen, um ein Umflackern beim Laden zu vermeiden.
const DESIGNS=['seerr','glass','clean'];
function applyDesign(dz){if(!DESIGNS.includes(dz))dz='seerr';document.documentElement.dataset.design=dz;localStorage.setItem('design',dz);
 document.querySelectorAll('.dpick').forEach(e=>e.classList.toggle('on',e.dataset.d==dz));}
applyDesign(localStorage.getItem('design')||'seerr');
function t(k){return (I18N[LANG]&&I18N[LANG][k])||I18N.de[k]||k;}
function setLang(l){LANG=l;localStorage.setItem('lang',l);applyI18n();
 document.querySelectorAll('#langsw b').forEach(e=>e.classList.toggle('on',e.dataset.l==l));
 if(cur=='s'&&!document.getElementById('q').value.trim())loadDiscover();if(cur=='j')loadJobs();}
function applyI18n(){
 document.querySelectorAll('[data-i18n]').forEach(e=>e.textContent=t(e.dataset.i18n));
 document.querySelectorAll('[data-i18n-ph]').forEach(e=>e.placeholder=t(e.dataset.i18nPh));
 updateFLabel();}
let cur='s';
function show(v){cur=v;
 document.getElementById('discview').style.display=v=='s'?'':'none';
 document.getElementById('jobs').style.display=v=='j'?'block':'none';
 document.getElementById('settings').style.display=v=='set'?'block':'none';
 document.getElementById('issues').style.display=v=='issues'?'block':'none';
 document.getElementById('messages').style.display=v=='msg'?'block':'none';
 document.getElementById('coverage').style.display=v=='cov'?'block':'none';
 document.getElementById('nS').classList.toggle('on',v=='s');
 document.getElementById('nJ').classList.toggle('on',v=='j');
 document.getElementById('nI').classList.toggle('on',v=='issues');
 let nM=document.getElementById('nM');if(nM)nM.classList.toggle('on',v=='msg');
 document.getElementById('nSet').classList.toggle('on',v=='set');
 if(v=='j')loadJobs();if(v=='set')openSettingsView();
 if(v=='issues'){loadIssues(window._ipref);window._ipref=null;}
 let nC=document.getElementById('nC');if(nC)nC.classList.toggle('on',v=='cov');
 if(v=='msg')loadMessages();if(v=='cov')loadCoverage();}
// --- Abdeckung je Plattform: „was fehlt mir" statt „was habe ich" (#78) ---
// Jede Zahl traegt Quelle + Stand — eine nackte Prozentzahl waere hier irrefuehrend.
async function loadCoverage(){let box=document.getElementById('coverage');
 box.innerHTML='<div class=meta>…</div>';
 let d=await(await fetch('/api/coverage')).json();
 let rows=(d.platforms||[]).map(p=>{
  if(p.known==null)return `<div class=job><div><b>${p.name}</b><div class=meta style="font-size:11px">`
    +(p.catalog?t('cov_nosnap'):t('cov_nosource'))+` · ${p.files} ${t('cov_files')}</div></div></div>`;
  let bar=`<div style="background:#2a2f37;border-radius:4px;height:6px;width:120px;overflow:hidden">`
   +`<div style="background:#6c5ce7;height:6px;width:${Math.min(100,p.pct||0)}%"></div></div>`;
  return `<div class=job style="cursor:pointer" onclick="openMissing('${p.slug}','${p.name.replace(/'/g,"")}')">
   <div><b>${p.name}</b><div class=meta style="font-size:11px">${p.owned} ${t('cov_of')} ${p.known}`
   +(p.capped?' +':'')+` · ${p.pct}% · ${t('cov_src')}: ${p.source} · ${t('cov_asof')} ${(p.snapshot||'').slice(0,10)}</div></div>
   <div style="display:flex;align-items:center;gap:10px">${bar}<span class=meta>›</span></div></div>`;}).join('');
 let adm=canDo('manage_settings')?`<button onclick="covRefresh()">${t('cov_refresh')}</button>
   <span id=covmsg class=meta></span>`:'';
 box.innerHTML=`<div class=rowh style="display:flex;align-items:center;gap:10px"><b>📊 ${t('nav_coverage')}</b>
   <span style="margin-left:auto">${adm}</span></div>
  <div class=meta style="margin:6px 0 10px;line-height:1.6">${t('cov_basis').replace('{src}',d.source).replace('{max}',d.max_per_platform)}</div>
  ${rows}`;
 if(d.building)covPoll();}
async function covRefresh(){let m=document.getElementById('covmsg');m.textContent='…';
 let r=await fetch('/api/coverage/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
 let d=await r.json();if(!d.ok){m.textContent=d.msg||t('st_error');return;}covPoll();}
async function covPoll(){let m=document.getElementById('covmsg');if(!m)return;
 let st=await(await fetch('/api/coverage/status')).json();
 if(st.running){m.textContent=`${st.current||''} ${st.done}/${st.total}`;setTimeout(covPoll,2000);}
 else{m.textContent=t('done_word');loadCoverage();}}
let _miss={slug:'',name:'',offset:0,q:''};
async function openMissing(slug,name){_miss={slug:slug,name:name,offset:0,q:''};renderMissing();}
async function renderMissing(){let m=document.getElementById('modal');m.style.display='block';
 m.innerHTML='<div class=box><div class=meta>…</div></div>';
 let u=`/api/coverage/${_miss.slug}/missing?offset=${_miss.offset}&limit=100`+(_miss.q?'&q='+encodeURIComponent(_miss.q):'');
 let d=await(await fetch(u)).json();
 let rows=(d.titles||[]).map((tt,i)=>`<div class=job><label style="display:flex;align-items:center;gap:8px;flex:1">
   <input type=checkbox class=misschk data-title="${tt.replace(/"/g,'&quot;')}"> <span>${tt.replace(/</g,'&lt;')}</span></label>
  <button onclick="missSearch('${tt.replace(/'/g,"\\'").replace(/"/g,'&quot;')}')" style="background:#2a2f37">${t('cov_search')}</button></div>`).join('')
  ||`<div class=meta>${t('cov_none')}</div>`;
 let pages=`<div class=frow style="gap:8px">
   <button ${_miss.offset<=0?'disabled':''} onclick="_miss.offset=Math.max(0,_miss.offset-100);renderMissing()">‹</button>
   <span class=meta>${_miss.offset+1}–${Math.min(d.total,_miss.offset+100)} / ${d.total}</span>
   <button ${_miss.offset+100>=d.total?'disabled':''} onclick="_miss.offset+=100;renderMissing()">›</button></div>`;
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <h2>${_miss.name} — ${t('cov_missing')}</h2>
  <div class=meta style="margin-bottom:8px">${t('cov_src')}: ${d.source||'—'} · ${t('cov_asof')} ${(d.snapshot||'').slice(0,10)}</div>
  <div class=frow style="gap:8px"><input id=missq value="${(_miss.q||'').replace(/"/g,'&quot;')}" placeholder="${t('cov_filter')}" style="flex:1">
   <button onclick="_miss.q=document.getElementById('missq').value;_miss.offset=0;renderMissing()">${t('cov_filter_do')}</button></div>
  <div style="max-height:340px;overflow:auto;margin-top:8px">${rows}</div>
  ${pages}
  <div class=frow style="justify-content:flex-end;gap:8px"><span id=missmsg class=meta></span>
   <button onclick="missWish()">${t('cov_wish_sel')}</button></div></div>`;}
function missSearch(title){closeModal();document.getElementById('q').value=title;show('s');search();}
async function missWish(){let sel=[...document.querySelectorAll('.misschk')].filter(c=>c.checked)
  .map(c=>({title:c.dataset.title,platform:_miss.slug}));
 let msg=document.getElementById('missmsg');
 if(!sel.length){msg.textContent=t('wl_imp_none');return;}
 let d=await(await fetch('/api/wishlist/import',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({confirm:true,entries:sel})})).json();
 msg.textContent=t('wl_imp_done').replace('{a}',d.added||0).replace('{s}',d.skipped||0);}
let msgWith='';
async function loadMessages(){let box=document.getElementById('messages');let d=await(await fetch('/api/messages')).json();
 let me=d.me,users=d.users||[];if(!msgWith&&users.length)msgWith=users[0];
 let unreadBy={};(d.messages||[]).forEach(m=>{if(m.to==me&&!m.read)unreadBy[m.from]=(unreadBy[m.from]||0)+1;});
 let opts=users.map(u=>`<option value="${u}" ${u==msgWith?'selected':''}>${u.replace(/</g,'&lt;')}${unreadBy[u]?' ('+unreadBy[u]+')':''}</option>`).join('');
 let thread=(d.messages||[]).filter(m=>(m.from==msgWith&&m.to==me)||(m.from==me&&m.to==msgWith))
   .map(m=>`<div class=cmt style="max-width:80%;margin-left:${m.from==me?'auto':'0'}"><span class="cu${m.from==me?' staff':''}">${m.from.replace(/</g,'&lt;')}</span> <span class=meta style="font-size:10px">${new Date(m.ts*1000).toLocaleString()}</span><div>${m.body.replace(/</g,'&lt;')}</div></div>`).join('');
 box.innerHTML=`<div style="padding:18px;max-width:680px"><h3 style="text-transform:uppercase;color:#8b929e;font-size:12px">✉ ${t('nav_messages')}</h3>`+
  (users.length?`<div class=frow><label style="min-width:auto">${t('msg_to')}</label><select id=msgsel onchange="msgWith=this.value;loadMessages()">${opts}</select></div>
   <div class=cmts id=msgthread style="max-height:50vh;overflow:auto">${thread||('<div class=meta>'+t('msg_none')+'</div>')}</div>
   <div class=frow><textarea id=msgbody placeholder="${t('msg_ph')}" style="flex:1;min-height:60px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px" onkeydown="if(event.key=='Enter'&&event.ctrlKey)sendMsg()"></textarea></div>
   <div class=frow><button onclick="sendMsg()">${t('msg_send')}</button><span class=meta>${t('msg_hint')}</span></div>`:`<div class=meta>${t('msg_nousers')}</div>`)+`</div>`;
 if(msgWith&&unreadBy[msgWith]){await fetch('/api/messages/read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:msgWith})});updateMsgBadge();}
 let mt=document.getElementById('msgthread');if(mt)mt.scrollTop=mt.scrollHeight;}
async function sendMsg(){let b=document.getElementById('msgbody');let body=(b.value||'').trim();if(!body||!msgWith)return;
 let r=await(await fetch('/api/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:msgWith,body})})).json();
 if(r.ok){b.value='';loadMessages();}}
async function updateMsgBadge(){try{let d=await(await fetch('/api/messages')).json();let el=document.getElementById('msgbadge');if(!el)return;
 el.textContent=d.unread?' '+d.unread+' ':'';el.style.cssText=d.unread?'background:#c0392b;color:#fff;border-radius:10px;padding:0 6px;font-size:11px;margin-left:6px':'';}catch(e){}}
async function loadIssues(pref){let box=document.getElementById('issues');
 let items=await(await fetch('/api/issues')).json();
 let types=['broken','wrong_region','wrong_platform','other'];
 box.innerHTML=`<div style="padding:18px;max-width:640px">
  <h3 style="text-transform:uppercase;color:#8b929e;font-size:12px">${t('report_issue')}</h3>
  <div class=frow><input id=itit placeholder="Titel / title" value="${((pref&&pref.title)||'').replace(/"/g,'&quot;')}"></div>
  <div class=frow><input id=iplat placeholder="Plattform" style="flex:0 0 140px" value="${((pref&&pref.platform)||'').replace(/"/g,'&quot;')}"><select id=ityp>${types.map(x=>'<option>'+x+'</option>').join('')}</select></div>
  <div class=frow><textarea id=imsg placeholder="${t('issue_msg')}" style="flex:1;min-height:60px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px"></textarea></div>
  <div class=frow><button onclick="submitIssue()">${t('submit')}</button><span id=imm class=meta></span></div>
  <h3 style="text-transform:uppercase;color:#8b929e;font-size:12px;margin-top:20px">${t('issues')}</h3><div id=ilist></div></div>`;
 renderIssues(items);}
function renderIssues(items){let d=document.getElementById('ilist');d.innerHTML=items.length?'':'<div class=meta>—</div>';
 items.forEach(i=>{let e=document.createElement('div');e.className='job';e.style.flexDirection='column';e.style.alignItems='stretch';
  let st=i.status=='closed'?t('st_closed'):t('st_open');
  let right=(canDo('manage_issues')&&i.status!='closed')?`<button onclick="closeIssue('${i.id}')" style="background:#1e5e3a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer">${t('close_btn')}</button>`:`<span class="st ${i.status=='closed'?'done':''}">${st}</span>`;
  let cs=(i.comments||[]).map(c=>`<div class=cmt><span class="cu${c.staff?' staff':''}">${(''+(c.user||'')).replace(/</g,'&lt;')}${c.staff?' 🛠':''}</span> <span class=meta style="font-size:10px">${c.ts||''}</span><div>${(''+(c.text||'')).replace(/</g,'&lt;')}</div></div>`).join('');
  e.innerHTML=`<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start"><div><div>${(''+(i.title||'')).replace(/</g,'&lt;')} <span class=meta>(${i.type})</span></div><div class=meta style="font-size:11px">👤 ${(''+(i.user||'')).replace(/</g,'&lt;')} · ${i.platform||''} · ${i.ts||''} · ${(''+(i.message||'')).replace(/</g,'&lt;').slice(0,90)}</div></div><div>${right}</div></div>
   <div class=cmts>${cs}</div>
   <div class=frow style="margin-top:6px"><input id="ic_${i.id}" placeholder="${t('comment_ph')}" style="flex:1" onkeydown="if(event.key=='Enter')addComment('${i.id}')"><button onclick="addComment('${i.id}')">${t('comment_send')}</button></div>`;
  d.appendChild(e);});}
async function addComment(id){let inp=document.getElementById('ic_'+id);let txt=inp.value.trim();if(!txt)return;
 let r=await(await fetch('/api/issues/'+id+'/comment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt})})).json();
 if(r.ok)loadIssues();}
async function submitIssue(){let d={title:document.getElementById('itit').value,platform:document.getElementById('iplat').value,type:document.getElementById('ityp').value,message:document.getElementById('imsg').value};
 if(!d.title.trim()){document.getElementById('imm').textContent='Titel fehlt / title missing';return;}
 let r=await(await fetch('/api/issues',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 if(r.ok)loadIssues();}
async function closeIssue(id){await fetch('/api/issues/'+id+'/close',{method:'POST'});loadIssues();}
function reportFromDetail(){let it=window._detit;if(!it)return;closeModal();window._ipref={title:it.title,platform:it.platform_slug};show('issues');}
function sz(b){if(!b)return'';let u=['B','KB','MB','GB','TB'],i=0;while(b>=1024&&i<4){b/=1024;i++}return b.toFixed(1)+' '+u[i];}
function renderCard(it){let c=document.createElement('div');c.className='card';
 let cov=it.cover?`background-image:url('${it.cover}')`:'';
 let src=it.source=='usenet'?'📡 Usenet':'🗄 Archive';
 let settag=it.is_set?' · 📦 '+t('collection'):'';
 c.innerHTML=`<div class=cover style="${cov}"><span class=badge>${it.platform_slug||'?'}</span><span class=src>${src}</span></div>
  <div class=body><div class=t>${it.title.replace(/</g,'&lt;')}</div><div class=meta>${sz(it.size)}${settag}</div><div class=act></div></div>`;
 c.querySelector('.cover').onclick=()=>openDetail(it);
 let tt=c.querySelector('.t');tt.style.cursor='pointer';tt.onclick=()=>openDetail(it);
 let act=c.querySelector('.act');
 if(it.in_library)act.innerHTML='<div class=have>'+t('in_library')+'</div>';
 else{let b=document.createElement('button');b.className='dl';b.textContent=t('download');b.onclick=()=>dl(b,it);act.appendChild(b);}
 if(!it.cover)fetch('/api/cover?title='+encodeURIComponent(it.title)).then(r=>r.json()).then(d=>{
  if(d.cover){it.cover=d.cover;c.querySelector('.cover').style.backgroundImage="url('"+d.cover+"')";}});
 return c;}

let RAONLY=false;
function toggleRA(){RAONLY=!RAONLY;let b=document.getElementById('tRA');
 b.classList.toggle('on',RAONLY);b.textContent=RAONLY?'🏆 '+t('ra_only'):'🏆';
 if(document.getElementById('q').value.trim())search();}
async function search(){let q=document.getElementById('q').value.trim();if(!q){loadDiscover();return;}
 let hint=document.getElementById('hint');hint.style.display='';hint.textContent=t('searching');
 let r=await fetch('/api/search?q='+encodeURIComponent(q)+'&platforms='+[...SELP].join(',')+(RAONLY?'&achievements=1':''));let d=await r.json();
 window.LASTRES=d;let g=document.getElementById('grid');g.className='';g.innerHTML='';
 if(!d.length){document.getElementById('hint').textContent=t('no_results');return;}
 let games={};d.forEach(x=>{if(!x.in_library){let k=x.gkey||x.title;if(!games[k])games[k]=1;}});
 let n=Object.keys(games).length;
 hint.innerHTML=(d.length+' '+t('results')).replace(/</g,'&lt;');
 if(n>1&&canDo('request')){let b=document.createElement('button');b.id='bulkbtn';
  b.style.cssText='margin-left:12px;background:#2a2f37;border:none;color:#e6e8ec;padding:5px 12px;border-radius:6px;cursor:pointer;font-size:12px';
  b.textContent='⬇ '+t('req_all')+' ('+n+')';b.onclick=bulkRequest;hint.appendChild(b);}
 d.forEach(it=>g.appendChild(renderCard(it)));}
async function bulkRequest(){let b=document.getElementById('bulkbtn');if(b)b.disabled=true;
 let seen={},todo=[];(window.LASTRES||[]).forEach(it=>{if(it.in_library)return;let k=it.gkey||it.title;if(seen[k])return;seen[k]=1;todo.push(it);});
 let ok=0;for(let it of todo){try{let r=await(await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({},it,{for_user:window.reqFor||''}))})).json();if(r.ok)ok++;}catch(e){}
  if(b)b.textContent='⬇ '+ok+'/'+todo.length;}
 if(b)b.textContent='✓ '+ok+'/'+todo.length;}
async function dl(btn,it){btn.disabled=true;btn.textContent='…';
 let payload=Object.assign({},it,{for_user:window.reqFor||''});
 let r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 let d=await r.json();btn.textContent=d.ok?t('requested'):(d.msg||t('st_error'));}
// --- Detail-Ansicht (Seerr-Detailseite) ---
async function openDetail(it){let m=document.getElementById('modal');m.style.display='block';window._detit=it;window.reqFor='';
 let vars=(window.LASTRES||[]).filter(x=>x.gkey&&x.gkey===it.gkey);
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <div class=top><div class=mc style="${it.cover?`background-image:url('${it.cover}')`:''}"></div>
   <div><h2>${it.title.replace(/</g,'&lt;')}</h2>
    <div class=meta>${it.platform_slug||'?'} · ${it.source=='usenet'?'📡 Usenet':'🗄 Archive'} · ${sz(it.size)}${it.is_set?' · 📦 Sammlung':''}</div>
    <div class=meta2 id=mrich></div>
    <button onclick="reportFromDetail()" style="margin-top:8px;background:#2a2f37;border:none;color:#fff;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:12px">🐞 ${t('report_issue')}</button>
    <button id=wlbtn onclick="addWishlist(this)" style="margin-top:8px;margin-left:6px;background:#2a2f37;border:none;color:#fff;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:12px">${t('add_wishlist')}</button>
    <div class=desc id=mdesc>…</div></div></div>
  <div class=sec id=mshots style="display:none"><h3>${t('screenshots')}</h3><div class=shots id=mshotsw></div></div>
  <div id=mra style="display:none;margin:6px 0"></div>
  <div class=sec><h3>${t('versions')} (${vars.length})</h3><div id=reqforbar></div><div id=mvar></div></div>
  <div class=sec id=mfiles></div>
  <div class=sec id=mser style="display:none"><h3 id=mserh>${t('series')}</h3><div class=chips id=mserw></div></div>
  <div class=sec id=msim style="display:none"><h3>${t('similar')}</h3><div class=chips id=msimw></div></div></div>`;
 let mv=document.getElementById('mvar');
 vars.forEach(v=>{let row=document.createElement('div');row.className='row';
  let s=document.createElement('span');s.textContent=`${v.source=='usenet'?'📡':'🗄'} ${sz(v.size)} · ${v.platform_slug} · ${v.title.slice(0,48)}`;
  row.appendChild(s);let b=document.createElement('button');
  if(v.in_library){b.textContent='✓ vorhanden';b.disabled=true;}else{b.textContent='⬇ Download';b.onclick=()=>dl(b,v);}
  row.appendChild(b);mv.appendChild(row);});
 if(canDo('manage_requests')){try{let us=await(await fetch('/api/users')).json();let names=Object.keys(us||{});
   if(names.length){let bar=document.getElementById('reqforbar');
    bar.innerHTML=`<div class=frow style="margin-bottom:8px"><label style="min-width:auto;color:#8b929e;font-size:12px">${t('req_for')}</label><select id=reqforsel onchange="window.reqFor=this.value"><option value="">${t('req_self')}</option>${names.map(u=>`<option value="${u}">${u.replace(/</g,'&lt;')}</option>`).join('')}</select></div>`;}}catch(e){}}
 let r=await fetch('/api/detail?source='+encodeURIComponent(it.source)+'&ref='+encodeURIComponent(it.ref||'')+'&title='+encodeURIComponent(it.title)+'&platform='+encodeURIComponent(it.platform_slug||''));
 let d=await r.json();
 window._detname=d.name||'';
 // RetroAchievements: nur wenn ein Set zugeordnet ist. Kein Set / kein Dienst -> gar nichts. (#79)
 let rabox=document.getElementById('mra');
 if(rabox){if(d.achievements){let a=d.achievements;
   let pr=a.progress?` · <b>${a.progress.earned}/${a.progress.total||a.achievements}</b> ${t('ra_earned')}`
        +(a.progress.completion?` (${a.progress.completion})`:''):'';
   rabox.style.display='';
   rabox.innerHTML=`<span class=badge>🏆 ${a.achievements} ${t('ra_achievements')}</span> `
    +`<span class=meta>${a.points} ${t('ra_points')}${pr} · `
    +`<a href="${a.url}" target=_blank rel=noopener style="color:#5b8cff">RetroAchievements</a></span>`;}
  else rabox.style.display='none';}
 document.getElementById('mdesc').textContent=d.description||t('no_desc');
 let rb=[];
 if(d.rating)rb.push(`<span class=badge>★ ${d.rating}</span>`);
 if(d.year)rb.push(`<span class=badge>${d.year}</span>`);
 if(d.developer)rb.push(`<span class=badge>${d.developer.replace(/</g,'&lt;')}</span>`);
 (d.genres||[]).slice(0,4).forEach(g=>rb.push(`<span class="badge g">${g.replace(/</g,'&lt;')}</span>`));
 document.getElementById('mrich').innerHTML=rb.join(' ');
 if(d.screenshots&&d.screenshots.length){document.getElementById('mshots').style.display='';
   document.getElementById('mshotsw').innerHTML=d.screenshots.map(s=>`<img src="${s}" loading=lazy>`).join('');}
 if(d.similar&&d.similar.length){document.getElementById('msim').style.display='';
   document.getElementById('msimw').innerHTML=d.similar.map(n=>`<button class=chip onclick="simSearch(this.dataset.n)" data-n="${n.replace(/"/g,'&quot;')}">${n.replace(/</g,'&lt;')}</button>`).join('');}
 if(d.series&&d.series_games&&d.series_games.length){document.getElementById('mser').style.display='';
   document.getElementById('mserh').textContent=t('series')+': '+d.series;
   document.getElementById('mserw').innerHTML=d.series_games.map(n=>`<button class=chip onclick="simSearch(this.dataset.n)" data-n="${n.replace(/"/g,'&quot;')}">${n.replace(/</g,'&lt;')}</button>`).join('');}
 if(d.files&&d.files.length)document.getElementById('mfiles').innerHTML='<h3>'+t('files')+'</h3><div class=flist>'+
   d.files.map(f=>`<div>${f.name.replace(/</g,'&lt;')} — ${sz(f.size)}</div>`).join('')+'</div>';}
function simSearch(n){closeModal();document.getElementById('q').value=n;show('s');search();}
async function addWishlist(btn){btn.disabled=true;let it=window._detit||{};
 let r=await(await fetch('/api/wishlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:window._detname||it.title||'',platform:it.platform_slug||''})})).json();
 btn.textContent=r.ok?t('wl_added'):(r.msg||t('st_error'));}
function closeModal(){document.getElementById('modal').style.display='none';}
// --- Wunschlisten-Import: Vorschau ZUERST, geschrieben wird erst nach Bestaetigung (#80) ---
const WLST={matched:['#3fb950','wl_s_matched'],ambiguous:['#d29922','wl_s_ambiguous'],
 not_found:['#f85149','wl_s_notfound'],duplicate:['#8b929e','wl_s_duplicate'],
 in_library:['#8b929e','wl_s_inlib'],unverified:['#58a6ff','wl_s_unverified']};
function openWlImport(){let m=document.getElementById('modal');m.style.display='block';
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <h2>⭐ ${t('wl_import')}</h2>
  <div class=meta style="line-height:1.6;margin-bottom:10px">${t('wl_imp_hint')}
   · <a href="/api/wishlist/example.csv" download style="color:#5b8cff">${t('wl_imp_example')}</a></div>
  <textarea id=wlta placeholder="${t('wl_imp_ph')}" style="width:100%;min-height:150px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:8px;font-family:ui-monospace,monospace;font-size:12px"></textarea>
  <div class=frow style="gap:8px;flex-wrap:wrap">
   <input type=file id=wlfile accept=".txt,.csv,text/plain,text/csv" onchange="wlReadFile(this)" style="flex:1;min-width:200px;font-size:12px">
   <button onclick="wlPreview()">${t('wl_imp_preview')}</button></div>
  <div id=wlres style="margin-top:12px"></div></div>`;}
function wlReadFile(inp){let f=inp.files&&inp.files[0];if(!f)return;
 if(f.size>200000){document.getElementById('wlres').innerHTML='<div class=meta style="color:#f85149">'+t('wl_imp_toobig')+'</div>';return;}
 let rd=new FileReader();rd.onload=()=>{document.getElementById('wlta').value=rd.result||'';};rd.readAsText(f);}
async function wlPreview(){let res=document.getElementById('wlres');res.innerHTML='<div class=meta>…</div>';
 let text=document.getElementById('wlta').value||'';
 let d=await(await fetch('/api/wishlist/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text})})).json();
 if(!d.ok){res.innerHTML='<div class=meta style="color:#f85149">'+((d.msg||t('st_error')).replace(/</g,'&lt;'))+'</div>';return;}
 window._wlprev=d.entries;
 let sum=Object.keys(d.counts||{}).map(k=>`${t(WLST[k]?WLST[k][1]:k)}: <b>${d.counts[k]}</b>`).join(' · ');
 let warn=d.truncated?`<div class=meta style="color:#d29922">${t('wl_imp_trunc').replace('{n}',d.max)}</div>`:'';
 let nochk=d.checked?'':`<div class=meta style="color:#58a6ff">${t('wl_imp_nocheck')}</div>`;
 let rows=d.entries.map((e,i)=>{let st=WLST[e.status]||['#8b929e',e.status];
  let sel=e.status==='ambiguous'
   ?`<select id="wlc${i}" style="background:#1a1d23;color:#e6e8ec;border:1px solid #2a2f37;border-radius:6px;padding:3px 6px;font-size:12px">`
    +e.candidates.map(c=>`<option>${c.replace(/</g,'&lt;')}</option>`).join('')+'</select>'
   :`<span>${(e.title||'').replace(/</g,'&lt;')}</span>`;
  let skip=(e.status==='duplicate'||e.status==='in_library');
  return `<div class=job><div style="display:flex;align-items:center;gap:8px;flex:1">
    <input type=checkbox id="wlk${i}" ${skip?'':'checked'} ${skip?'disabled':''}>
    ${sel}<span class=meta style="font-size:11px">${(e.platform||'—').replace(/</g,'&lt;')}</span></div>
   <span style="color:${st[0]};font-size:12px">${t(st[1])}</span></div>`;}).join('');
 res.innerHTML=`<div class=meta style="margin-bottom:6px">${sum}</div>${warn}${nochk}
  <div style="max-height:320px;overflow:auto">${rows}</div>
  <div class=frow style="justify-content:flex-end;gap:8px"><span id=wlmsg class=meta></span>
   <button onclick="wlApply()">${t('wl_imp_apply')}</button></div>`;}
async function wlApply(){let prev=window._wlprev||[];let out=[];
 prev.forEach((e,i)=>{let k=document.getElementById('wlk'+i);if(!k||!k.checked)return;
  let c=document.getElementById('wlc'+i);
  out.push({title:c?c.value:e.title,platform:e.platform||''});});
 if(!out.length){document.getElementById('wlmsg').textContent=t('wl_imp_none');return;}
 let d=await(await fetch('/api/wishlist/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm:true,entries:out})})).json();
 document.getElementById('wlmsg').textContent=t('wl_imp_done').replace('{a}',d.added||0).replace('{s}',d.skipped||0);
 loadJobs();}
// --- Discover / Startseite: beliebte Spiele je Konsole ---
async function loadDiscover(){let hint=document.getElementById('hint');hint.style.display='';hint.textContent=t('loading_home');
 let g=document.getElementById('grid');
 let rows=await(await fetch('/api/discover/rows')).json();window.DROWS=rows;
 if(!rows.length){hint.textContent=t('hint_type');g.className='';g.innerHTML='';return;}
 hint.style.display='none';g.className='disc';g.innerHTML='';
 let hid=new Set(JSON.parse(localStorage.getItem('dischide')||'[]'));
 let bar=document.createElement('div');bar.style.cssText='display:flex;justify-content:flex-end;margin-bottom:6px';
 bar.innerHTML='<button onclick="toggleDiscCust()" style="background:#1e2229;border:1px solid #2c323b;color:#8b929e;padding:5px 10px;border-radius:8px;cursor:pointer;font-size:12px">⚙ anpassen / customize</button>';
 g.appendChild(bar);
 let cust=document.createElement('div');cust.id='disccust';cust.style.cssText='display:none;background:#171a20;border-radius:8px;padding:10px;margin-bottom:12px';
 rows.forEach(r=>{let lbl=document.createElement('label');lbl.style.cssText='font-size:12px;color:#8b929e;display:inline-flex;gap:5px;align-items:center;margin:0 12px 6px 0';
  let cb=document.createElement('input');cb.type='checkbox';cb.checked=!hid.has(r.key);
  cb.onchange=()=>{let h=new Set(JSON.parse(localStorage.getItem('dischide')||'[]'));cb.checked?h.delete(r.key):h.add(r.key);localStorage.setItem('dischide',JSON.stringify([...h]));loadDiscover();};
  lbl.appendChild(cb);lbl.appendChild(document.createTextNode(r.console));cust.appendChild(lbl);});
 g.appendChild(cust);
 rows.filter(r=>!hid.has(r.key)).forEach(r=>{let sec=document.createElement('div');sec.className='drow';
  let pre=r.reco?t('because_you')+' ':(r.slug?t('popular_on')+' ':'');
  sec.innerHTML=`<div class=rowh>${pre}<b>${(r.console||'').replace(/</g,'&lt;')}</b> <span>· ${t('click_search')}</span></div><div class=strip></div>`;
  let strip=sec.querySelector('.strip');
  r.games.forEach(it=>{let c=document.createElement('div');c.className='pcard';
   c.innerHTML=`<div class=pcover style="${it.cover?`background-image:url('${it.cover}')`:''}">${it.in_library?'<span class=have2>✓</span>':''}</div><div class=pt>${it.title.replace(/</g,'&lt;')}</div>`;
   c.onclick=()=>{SELP=r.slug?new Set([r.slug]):new Set();
    localStorage.setItem('romp',JSON.stringify([...SELP]));updateFLabel();
    document.querySelectorAll('.chip').forEach(e=>e.classList.toggle('on',SELP.has(e.dataset.s)));
    document.getElementById('q').value=it.title;search();};
   strip.appendChild(c);});
  g.appendChild(sec);});}
function toggleDiscCust(){let e=document.getElementById('disccust');e.style.display=e.style.display=='none'?'block':'none';}
const STCLS={downloading:'downloading',importing:'importing',done:'done',error:'error',denied:'error'};
function stlab(s){return [t('st_'+s)||s, STCLS[s]||''];}
async function loadJobs(){let r=await fetch('/api/jobs');let d=await r.json();let j=document.getElementById('jobs');
 j.innerHTML='';
 try{let wl=await(await fetch('/api/wishlist')).json();
  let box=document.createElement('div');box.style.cssText='margin-bottom:14px';
  box.innerHTML='<div class=rowh style="margin-bottom:6px;display:flex;align-items:center;gap:8px">⭐ <b>'+t('wishlist')+'</b>'
   +'<button onclick="openWlImport()" style="margin-left:auto;background:#2a2f37;border:none;color:#e6e8ec;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:12px">'+t('wl_import')+'</button></div>';
  if(wl&&wl.length){
   wl.forEach(e=>{let row=document.createElement('div');row.className='job';
    row.innerHTML=`<div><div>${(e.title||'').replace(/</g,'&lt;')}</div><div class=meta style="color:#8b929e;font-size:11px">${(e.platform||'—').replace(/</g,'&lt;')}</div></div>`;
    let b=document.createElement('button');b.textContent=t('wl_remove');
    b.style.cssText='background:#6e2a2a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer';
    b.onclick=async()=>{await fetch('/api/wishlist/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:e.title,platform:e.platform})});loadJobs();};
    row.appendChild(b);box.appendChild(row);});
  }else{let em=document.createElement('div');em.className='meta';em.textContent=t('wl_empty');box.appendChild(em);}
  j.appendChild(box);}catch(e){}
 if(canDo('manage_requests')){let users=[...new Set(d.map(o=>o.user||'—'))].sort();
  if(users.length>1){let bar=document.createElement('div');bar.style.cssText='margin:0 0 10px;color:#8b929e;font-size:13px';
   let opts='<option value="">'+t('flt_all')+'</option>'+users.map(u=>`<option${window.jobFilter===u?' selected':''}>${u.replace(/</g,'&lt;')}</option>`).join('');
   bar.innerHTML=t('flt_user')+': <select id=jobflt onchange="window.jobFilter=this.value;loadJobs()" style="background:#1a1d23;color:#e6e8ec;border:1px solid #2a2f37;border-radius:6px;padding:4px 8px">'+opts+'</select>';
   j.appendChild(bar);}}
 if(window.jobFilter)d=d.filter(o=>(o.user||'—')===window.jobFilter);
 if(!d.length){let h=document.createElement('div');h.className='hint';h.textContent=t('no_requests');j.appendChild(h);return;}
 d.forEach(o=>{let e=document.createElement('div');e.className='job';let L=stlab(o.state);let right;
  if(o.state=='pending'&&canDo('manage_requests')){
   right=`<button onclick="approveJob('${o.id}')" style="background:#1e5e3a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer;margin-right:6px">${t('approve')}</button><button onclick="denyJob('${o.id}')" style="background:#6e2a2a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer">${t('deny')}</button>`;
  }else{right=`<span class="st ${L[1]}">${L[0]}</span>`;
   if((o.state=='error'||o.state=='denied')&&canDo('manage_requests'))
    right+=`<button onclick="retryJob('${o.id}')" style="background:#2a2f37;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer;margin-left:8px" title="${t('retry')}">↻ ${t('retry')}</button>`;}
  let dt=o.created?new Date(o.created*1000).toLocaleString():'';
  e.innerHTML=`<div><div>${o.title.replace(/</g,'&lt;')}</div><div class=meta style="color:#8b929e;font-size:11px">👤 <b style="color:#b9c0cc">${(o.user||'—').replace(/</g,'&lt;')}</b> · ${o.platform} · ${o.source}${dt?' · '+dt:''} · ${o.msg||''}</div></div><div>${right}</div>`;
  j.appendChild(e);});}
// --- Plattform-Vorauswahl ---
let SELP=new Set(JSON.parse(localStorage.getItem('romp')||'[]'));
async function loadPlatforms(){
 let r=await fetch('/api/platforms');let d=await r.json();
 document.getElementById('filter').innerHTML=d.map(g=>`<div class=grp><div class=gl>${g.group}</div>`+
   g.items.map(it=>`<span class="chip${SELP.has(it.slug)?' on':''}" data-s="${it.slug}" onclick="toggleChip('${it.slug}')" title="${it.usenet?'auch über Usenet':'nur Archive.org'}">${it.name}${it.usenet?' 📡':''}</span>`).join('')+
   `</div>`).join('')+`<div class=fbtns><button onclick="clearP()">${t('reset')}</button></div>`;
 updateFLabel();}
function toggleChip(s){SELP.has(s)?SELP.delete(s):SELP.add(s);
 localStorage.setItem('romp',JSON.stringify([...SELP]));
 document.querySelectorAll('.chip[data-s="'+s+'"]').forEach(e=>e.classList.toggle('on',SELP.has(s)));
 updateFLabel();}
function clearP(){SELP.clear();localStorage.setItem('romp','[]');
 document.querySelectorAll('.chip').forEach(e=>e.classList.remove('on'));updateFLabel();}
function updateFLabel(){let e=document.getElementById('tF');if(e)e.textContent='🎛 '+t('platforms')+': '+(SELP.size?SELP.size+' '+t('selected'):t('all'));}
function toggleFilter(){let f=document.getElementById('filter');f.style.display=f.style.display=='block'?'none':'block';}
// --- Benutzerverwaltung ---
function canDo(perm){return window.ROLE=='admin'||(window.PERMS||[]).includes(perm);}
function defAvatar(name){let n=(name||'?').trim()||'?';let ini=(n[0]||'?').toUpperCase();
 let cols=['#5b8cff','#e0679a','#5bbf8a','#d9a441','#9b6dd6','#4bb7c6'];let c=cols[(n.charCodeAt(0)||0)%cols.length];
 let svg='<svg xmlns="http://www.w3.org/2000/svg" width="66" height="66"><rect width="66" height="66" rx="33" fill="'+c+'"/><text x="33" y="45" font-size="34" text-anchor="middle" fill="#fff" font-family="sans-serif">'+ini+'</text></svg>';
 return 'data:image/svg+xml;base64,'+btoa(unescape(encodeURIComponent(svg)));}
async function loadAuth(){let d=await(await fetch('/api/auth/status')).json();
 window.ROLE=d.role;window.VERSION=d.version||'';window.PERMS=d.perms||[];
 let lang=d.user_lang||localStorage.getItem('lang')||d.default_lang||'de';
 if(lang!=LANG){LANG=lang;localStorage.setItem('lang',lang);setLang(lang);}
 applyDesign(d.user_design||localStorage.getItem('design')||d.default_design||'seerr');
 let who=document.getElementById('who');
 if(d.user){let nm=(d.display_name||d.user);
   who.innerHTML=`<img src="${d.avatar||defAvatar(nm)}">`+nm.replace(/</g,'&lt;');}
 else who.textContent='';
 if(d.role=='admin'){document.getElementById('nSet').style.display='';
   try{let cs=await(await fetch('/api/settings')).json();if(!cs.onboarded)startWizard();}catch(e){}}}
// --- Benutzerprofil (#23) ---
let PAV='';
async function openProfile(){let m=document.getElementById('modal');m.style.display='block';PAV='';
 let p=await(await fetch('/api/profile')).json();
 let inp='style="flex:1;min-width:120px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px"';
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <div class=sec><h3>${t('profile')} — ${(p.username||'').replace(/</g,'&lt;')}</h3>
   <div class=row><div id=pav style="width:66px;flex:0 0 66px;height:66px;border-radius:50%;background:#0b0d10 center/cover no-repeat;border:1px solid #2c323b;background-image:url('${p.avatar||defAvatar(p.display_name||p.username)}')"></div>
    <label style="flex:1;font-size:12px;color:#8b929e">${t('avatar')}<br><input type=file accept="image/*" onchange="pickAvatar(event)"></label></div>
   <div class=row><input id=pdn ${inp} placeholder="${t('display_name')}" value="${(p.display_name||'').replace(/"/g,'&quot;')}"></div>
   <div class=row><input id=pmail ${inp} placeholder="${t('email')}" value="${(p.email||'').replace(/"/g,'&quot;')}"></div>
   <div class=row><label style="color:#8b929e;font-size:13px">${t('language')}</label><select id=plang ${inp}><option value="">—</option><option value=de ${p.lang=='de'?'selected':''}>Deutsch</option><option value=en ${p.lang=='en'?'selected':''}>English</option><option value=fr ${p.lang=='fr'?'selected':''}>Français</option><option value=es ${p.lang=='es'?'selected':''}>Español</option><option value=it ${p.lang=='it'?'selected':''}>Italiano</option></select></div>
   <div class=row><label style="color:#8b929e;font-size:13px">${t('design')}</label><div style="display:flex;gap:8px;flex-wrap:wrap">${DESIGNS.map(dz=>`<button class="dpick${(p.design||'')==dz?' on':''}" data-d="${dz}" onclick="pickDesign('${dz}')">${t('d_'+dz)}</button>`).join('')}</div></div>
   <div class=row><input id=pwh ${inp} placeholder="${t('pwebhook')}" value="${(p.webhook||'').replace(/"/g,'&quot;')}"><button onclick="testPWebhook()">${t('test')}</button></div>
   <div class=row><input id=pra ${inp} placeholder="${t('ra_user')}" value="${(p.ra_user||'').replace(/"/g,'&quot;')}"></div>
   <div class=row><button onclick="saveProfile()">${t('save')}</button><span id=pmsg class=meta></span></div>
   <div class=row><button onclick="togglePush()" id=pushbtn>${t('push_enable')}</button><span id=pushmsg class=meta></span></div>
   <div class=row><span class=meta>Kontingent / Quota</span><span class=meta>${p.quota&&p.quota.enabled?(p.quota.remaining+' / '+p.quota.count+' ('+p.quota.days+'d)'):'—'}</span></div></div>
  <div class=sec><h3>${t('change_pw')}</h3>
   <div class=row><input id=pold type=password ${inp} placeholder="${t('cur_pw')}"><input id=pnew type=password ${inp} placeholder="${t('new_pw')}"></div>
   <div class=row><button onclick="changePw()">${t('change_pw')}</button><span id=pwmsg class=meta></span></div></div></div>`;
 refreshPushBtn();}
function urlB64ToU8(s){let pad='='.repeat((4-s.length%4)%4);let b=(s+pad).replace(/-/g,'+').replace(/_/g,'/');let raw=atob(b);let a=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)a[i]=raw.charCodeAt(i);return a;}
async function pushState(){if(!('serviceWorker'in navigator)||!('PushManager'in window)||!('Notification'in window))return 'unsupported';
 try{let reg=await navigator.serviceWorker.ready;let sub=await reg.pushManager.getSubscription();return sub?'on':'off';}catch(_){return 'unsupported';}}
async function refreshPushBtn(){let b=document.getElementById('pushbtn');if(!b)return;let st=await pushState();
 if(st=='unsupported'){b.textContent=t('push_unsupported');b.disabled=true;return;}
 b.disabled=false;b.textContent=st=='on'?t('push_disable'):t('push_enable');}
async function togglePush(){let msg=document.getElementById('pushmsg');let st=await pushState();
 if(st=='unsupported'){msg.textContent=t('push_unsupported');return;}
 let reg=await navigator.serviceWorker.ready;
 if(st=='on'){let sub=await reg.pushManager.getSubscription();
  if(sub){await fetch('/api/push/unsubscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({endpoint:sub.endpoint})});await sub.unsubscribe();}
  msg.textContent=t('push_off');refreshPushBtn();return;}
 let perm=await Notification.requestPermission();if(perm!='granted'){msg.textContent=t('push_denied');return;}
 let pk=await(await fetch('/api/push/pubkey')).json();if(!pk.enabled||!pk.key){msg.textContent=t('push_unsupported');return;}
 try{let sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:urlB64ToU8(pk.key)});
  await fetch('/api/push/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(sub)});
  msg.textContent=t('push_on');refreshPushBtn();}catch(e){msg.textContent=t('push_denied');}}
function pickAvatar(e){let f=e.target.files[0];if(!f)return;
 if(f.size>280000){document.getElementById('pmsg').textContent='max ~280 KB';return;}
 let r=new FileReader();r.onload=()=>{PAV=r.result;document.getElementById('pav').style.backgroundImage="url('"+PAV+"')";};r.readAsDataURL(f);}
function pickDesign(dz){applyDesign(dz);}
async function saveProfile(){let d={display_name:document.getElementById('pdn').value,email:document.getElementById('pmail').value,lang:document.getElementById('plang').value,design:document.documentElement.dataset.design||'',webhook:document.getElementById('pwh').value,ra_user:(document.getElementById('pra')||{}).value||''};
 if(PAV)d.avatar=PAV;
 let r=await(await fetch('/api/profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('pmsg').textContent=r.ok?t('saved_ok'):(r.msg||t('st_error'));
 if(r.ok){PAV='';loadAuth();if(d.lang){LANG=d.lang;localStorage.setItem('lang',d.lang);setLang(d.lang);}}}
async function changePw(){let d={old:document.getElementById('pold').value,new:document.getElementById('pnew').value};
 let r=await(await fetch('/api/profile/password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('pwmsg').textContent=r.ok?t('saved_ok'):(r.msg||t('st_error'));}
async function testPWebhook(){let wh=document.getElementById('pwh').value.trim();if(!wh)return;
 let r=await(await fetch('/api/profile/notify-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:wh})})).json();
 document.getElementById('pmsg').textContent=r.ok?t('test_sent'):(r.msg||t('st_error'));}
// --- Admin-Bereich / Einstellungen (Seite mit Unterbereichen) ---
let SETSEC='general';
function openSettingsView(){
 let secs=[['general',t('sec_general')],['notif',t('sec_notif')],['conn',t('sec_conn')],['users',t('sec_users')],['blocklist',t('blocklist')],['services',t('sec_services')],['maint',t('sec_maint')],['tls','HTTPS'],['about',t('sec_about')]];
 document.getElementById('settings').innerHTML='<div class=setwrap><div class=setnav>'+
  secs.map(x=>`<a class=snav data-sec="${x[0]}" onclick="setSection('${x[0]}')">${x[1]}</a>`).join('')+
  '</div><div id=setcontent></div></div>';
 setSection(SETSEC);}
function setSection(sec){SETSEC=sec;
 document.querySelectorAll('.snav').forEach(e=>e.classList.toggle('on',e.dataset.sec==sec));
 let c=document.getElementById('setcontent');
 ({general:secGeneral,notif:secNotif,conn:secConn,users:secUsers,blocklist:secBlocklist,services:secServices,maint:secMaint,tls:secTls,about:secAbout}[sec]||secGeneral)(c);}
async function secConn(c){let vals=await(await fetch('/api/settings/connections/reveal')).json();
 function fld(k,label,secret){let v=(vals[k]||'');
  let eye=secret?`<button type=button onclick="togEye('c_${k}',this)" title="${t('reveal')}" style="background:#2a2f37;border:none;color:#8b929e;padding:6px 9px;border-radius:6px;cursor:pointer;margin-left:6px">👁</button>`:'';
  return `<div class=frow><label style="min-width:150px">${label}</label><input id="c_${k}" ${secret?'type=password':''} value="${(''+v).replace(/"/g,'&quot;')}" style="flex:1">${eye}</div>`;}
 c.innerHTML=`<h3>${t('sec_conn')}</h3><div class=meta style="margin-bottom:10px">${t('conn_hint')}</div>
  <h3 style="font-size:13px">SABnzbd</h3>${fld('sab_url','URL')}${fld('sab_apikey','API-Key',1)}${fld('sab_cat','Kategorie / category')}
  <h3 style="font-size:13px">Prowlarr</h3>${fld('prow_url','URL')}${fld('prow_apikey','API-Key',1)}${fld('prow_cats','Kategorien / categories')}
  <h3 style="font-size:13px">IGDB</h3>${fld('igdb_id','Client-ID')}${fld('igdb_secret','Client-Secret',1)}
  <h3 style="font-size:13px">Scraper / Cover-Quellen</h3>${fld('sgdb_key','SteamGridDB-Key',1)}${fld('ss_user','ScreenScraper-User')}${fld('ss_pass','ScreenScraper-Passwort',1)}
  <h3 style="font-size:13px">RomM</h3>${fld('romm_url','URL')}${fld('romm_user','User')}${fld('romm_pass','Passwort / password',1)}
  <h3 style="font-size:13px">RetroAchievements</h3>${fld('ra_key','API-Key',1)}
  <div class=frow><span class=meta id=rastat style="flex:1">…</span>
   <button type=button onclick="raRefresh()" style="background:#2a2f37">${t('ra_refresh')}</button></div>
  <h3 style="font-size:13px">JDownloader</h3>${fld('jd_dl_base','Download-Basis')}
  <div class=frow><button onclick="saveConn()">${t('save')}</button><button onclick="testConn()" style="margin-left:8px;background:#2a2f37">${t('test')}</button><span id=cmsg class=meta></span></div>
  <div id=csvc style="margin-top:10px"></div>`;raStatus();}
async function raStatus(){let el=document.getElementById('rastat');if(!el)return;
 let d=await(await fetch('/api/ra/status')).json();
 if(!d.enabled){el.textContent=t('ra_nokey');return;}
 if(d.build&&d.build.running){el.textContent=`${d.build.current||''} ${d.build.done}/${d.build.total}`;setTimeout(raStatus,2000);return;}
 el.textContent=`${d.total} ${t('ra_sets')} · ${Object.keys(d.platforms||{}).length} ${t('about_platforms')}`
  +(d.snapshot?` · ${t('cov_asof')} ${d.snapshot.slice(0,10)}`:'')
  +((d.unmapped||[]).length?` · ${t('ra_unmapped')}: ${d.unmapped.join(', ')}`:'');}
async function raRefresh(){let el=document.getElementById('rastat');el.textContent='…';
 let d=await(await fetch('/api/ra/refresh',{method:'POST'})).json();
 if(!d.ok){el.textContent=d.msg||t('st_error');return;}setTimeout(raStatus,1500);}
function togEye(id,btn){let el=document.getElementById(id);if(!el)return;el.type=el.type=='password'?'text':'password';btn.style.color=el.type=='text'?'#e6e8ec':'#8b929e';}
async function secTls(c){let d=await(await fetch('/api/settings/tls')).json();
 let ta='flex:1;min-height:110px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px;font-family:ui-monospace,monospace;font-size:11px';
 let status=d.has_cert?`✅ ${(d.cn||'').replace(/</g,'&lt;')} · ${t('tls_expires')} ${d.expires||'?'}`:`⬜ ${t('tls_none')}`;
 c.innerHTML=`<h3>HTTPS / TLS</h3><div class=meta style="margin-bottom:8px">${t('tls_hint')}</div>
  <div class=frow><span class=meta>${status}</span></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=tls_en ${d.enabled?'checked':''}> ${t('active')}</label>
   <label style="min-width:auto;margin-left:16px">Port <input id=tls_port type=number value="${d.port||8443}" style="flex:0 0 100px"></label></div>
  <div class=frow><textarea id=tls_cert placeholder="-----BEGIN CERTIFICATE-----" style="${ta}"></textarea></div>
  <div class=frow><textarea id=tls_key placeholder="-----BEGIN PRIVATE KEY-----   (${t('tls_key_note')})" style="${ta}"></textarea></div>
  <div class=frow><button onclick="saveTls()">${t('save')}</button><button onclick="removeTls()" style="margin-left:8px;background:#6e2a2a">${t('del')}</button><span id=tmsg class=meta></span></div>`;}
async function saveTls(){let body={enabled:document.getElementById('tls_en').checked,port:parseInt(document.getElementById('tls_port').value)||8443};
 let cert=document.getElementById('tls_cert').value.trim(),key=document.getElementById('tls_key').value.trim();
 if(cert||key){body.cert=cert;body.key=key;}
 let r=await(await fetch('/api/settings/tls',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
 document.getElementById('tmsg').textContent=r.ok?(t('saved')+' — '+t('tls_restart')):(r.msg||t('st_error'));if(r.ok)setTimeout(()=>setSection('tls'),700);}
async function removeTls(){await fetch('/api/settings/tls/remove',{method:'POST'});setSection('tls');}
// --- Erststart-Assistent / onboarding wizard ---
const WIZ=[{svc:null},
 {svc:'SABnzbd',fields:[['sab_url','URL'],['sab_apikey','API-Key',1],['sab_cat','Kategorie / category']]},
 {svc:'Prowlarr',fields:[['prow_url','URL'],['prow_apikey','API-Key',1],['prow_cats','Kategorien / categories']]},
 {svc:'IGDB',fields:[['igdb_id','Client-ID'],['igdb_secret','Client-Secret',1]]},
 {svc:'RomM',fields:[['romm_url','URL'],['romm_user','User'],['romm_pass','Passwort / password',1]]},
 {svc:'done'}];
let wizIdx=0,wizVals={};
async function startWizard(){wizIdx=0;try{wizVals=await(await fetch('/api/settings/connections/reveal')).json();}catch(e){wizVals={};}renderWiz();}
function renderWiz(){let m=document.getElementById('modal');m.style.display='block';let s=WIZ[wizIdx];let total=WIZ.length-2;let body,btns;
 let bA='background:var(--acc);border:none;color:#fff;padding:8px 14px;border-radius:6px;cursor:pointer',bG='background:#2a2f37;border:none;color:#e6e8ec;padding:8px 14px;border-radius:6px;cursor:pointer';
 if(s.svc===null){body=`<h2>👋 ${t('wiz_welcome')}</h2><p class=meta style="line-height:1.6">${t('wiz_welcome_txt')}</p>`;
   btns=`<button onclick="wizFinish()" style="${bG}">${t('wiz_skip')}</button><button onclick="wizGo(1)" style="${bA};margin-left:8px">${t('wiz_next')} →</button>`;}
 else if(s.svc==='done'){body=`<h2>✅ ${t('wiz_done')}</h2><p class=meta style="line-height:1.6">${t('wiz_done_txt')}</p>`;
   btns=`<button onclick="wizFinish()" style="${bA}">${t('wiz_finish')}</button>`;}
 else{let inp='style="flex:1;min-width:120px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px"';
   let fl=s.fields.map(f=>`<div class=frow><label style="min-width:130px">${f[1]}</label><input id="w_${f[0]}" ${f[2]?'type=password':''} value="${(''+(wizVals[f[0]]||'')).replace(/"/g,'&quot;')}" ${inp}></div>`).join('');
   body=`<div class=meta>${t('wiz_step')} ${wizIdx}/${total}</div><h2>${s.svc}</h2>${fl}<div class=frow><button onclick="wizTest('${s.svc}')" style="${bG};padding:6px 12px">${t('test')}</button><span id=wtest class=meta></span></div>`;
   btns=`<button onclick="wizGo(-1)" style="${bG}">← ${t('wiz_back')}</button><button onclick="wizSaveNext()" style="${bA};margin-left:8px">${t('wiz_next')} →</button><button onclick="wizGo(1)" style="background:transparent;border:1px solid #2c323b;color:#8b929e;padding:8px 14px;border-radius:6px;cursor:pointer;margin-left:8px">${t('wiz_skip')}</button>`;}
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button><div class=sec>${body}</div><div class=sec style="display:flex;justify-content:flex-end">${btns}</div></div>`;}
function wizGo(dir){wizCollect();wizIdx=Math.max(0,Math.min(WIZ.length-1,wizIdx+dir));renderWiz();}
function wizCollect(){let s=WIZ[wizIdx];if(!s||!s.fields)return;s.fields.forEach(f=>{let el=document.getElementById('w_'+f[0]);if(el)wizVals[f[0]]=el.value;});}
async function wizSave(){let s=WIZ[wizIdx];if(!s.fields)return;let conn={};s.fields.forEach(f=>{conn[f[0]]=wizVals[f[0]]||'';});
 await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({connections:conn})});}
async function wizSaveNext(){wizCollect();await wizSave();wizGo(1);}
async function wizTest(svc){wizCollect();document.getElementById('wtest').textContent='…';await wizSave();
 let d=await(await fetch('/api/services/status')).json();let x=(d||[]).find(o=>o.name===svc);
 document.getElementById('wtest').textContent=x?((x.ok?'✅ ':'❌ ')+(x.info||'')):'—';}
async function wizFinish(){await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({onboarded:true})});closeModal();if(cur=='s')loadDiscover();}
const CONN_ALL=['sab_url','sab_apikey','sab_cat','prow_url','prow_apikey','prow_cats','igdb_id','igdb_secret','sgdb_key','ss_user','ss_pass','romm_url','romm_user','romm_pass','jd_dl_base','ra_key'];
const CONN_SEC=['sab_apikey','prow_apikey','igdb_secret','sgdb_key','ss_pass','romm_pass'];
async function saveConn(){let conn={};CONN_ALL.forEach(k=>{let el=document.getElementById('c_'+k);if(!el)return;
  if(CONN_SEC.includes(k)){if(el.value)conn[k]=el.value;}else{conn[k]=el.value;}});
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({connections:conn})})).json();
 document.getElementById('cmsg').textContent=r.ok?t('saved'):t('st_error');if(r.ok)setTimeout(()=>setSection('conn'),400);}
async function testConn(){let b=document.getElementById('csvc');b.textContent='…';
 let d=await(await fetch('/api/services/status')).json();
 b.innerHTML=(d||[]).map(x=>`<div class=meta>${x.ok?'✅':'❌'} <b>${x.name}</b> ${(x.info||'').replace(/</g,'&lt;')}</div>`).join('');}
async function secMaint(c){
 c.innerHTML=`<h3>${t('sec_maint')}</h3><div id=mstats class=meta>…</div>
  <div style="margin:10px 0;display:flex;gap:8px;flex-wrap:wrap">
   <button onclick="admCache()">${t('clear_cache')}</button>
   <button onclick="admReindex()">${t('reindex')}</button>
   <button onclick="admClearJobs()">${t('clear_finished')}</button>
   <button onclick="loadLogs()">${t('refresh')}</button>
   <span id=mmsg class=meta></span></div>
  <h3 style="margin-top:16px">${t('exp_title')}</h3>
  <div class=meta style="line-height:1.6;margin-bottom:8px">${t('exp_hint')}</div>
  <div class=frow style="gap:8px;flex-wrap:wrap">
   <label style="min-width:150px">${t('exp_pass')}</label>
   <input id=exppw type=password placeholder="${t('exp_pass_ph')}" style="flex:1;min-width:180px">
   <button onclick="doExport()">${t('exp_do')}</button></div>
  <div class=frow style="gap:8px;flex-wrap:wrap">
   <input type=file id=impfile accept=".json,application/json" style="flex:1;min-width:180px;font-size:12px">
   <select id=impmode style="background:#1a1d23;color:#e6e8ec;border:1px solid #2a2f37;border-radius:6px;padding:5px 8px">
    <option value="merge">${t('exp_merge')}</option><option value="replace">${t('exp_replace')}</option></select>
   <button onclick="doImport()" style="background:#6e2a2a">${t('imp_do')}</button></div>
  <div id=impmsg class=meta></div>
  <h3 style="margin-top:16px">${t('logs')}</h3><pre id=logbox class=logbox>…</pre>`;
 loadMStats();loadLogs();}
// --- Export/Import der Konfiguration (#75) ---
async function doExport(){let pw=(document.getElementById('exppw').value||'');
 let msg=document.getElementById('impmsg');msg.style.color='';msg.textContent='…';
 let body=pw?{secrets:'encrypt',passphrase:pw}:{};
 let r=await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 let d=await r.json();
 if(!r.ok||d.ok===false){msg.style.color='#f85149';msg.textContent=d.msg||t('st_error');return;}
 let blob=new Blob([JSON.stringify(d,null,2)],{type:'application/json'});
 let a=document.createElement('a');a.href=URL.createObjectURL(blob);
 a.download='romseerr-export-'+(d.exported_at||'').replace(/[:]/g,'')+'.json';
 document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(a.href);
 msg.textContent=pw?t('exp_done_enc'):t('exp_done_plain');}
async function doImport(){let msg=document.getElementById('impmsg');msg.style.color='';
 let f=document.getElementById('impfile').files[0];
 if(!f){msg.style.color='#f85149';msg.textContent=t('imp_nofile');return;}
 let mode=document.getElementById('impmode').value;
 if(!confirm(t(mode==='replace'?'imp_conf_replace':'imp_conf_merge')))return;
 let doc;try{doc=JSON.parse(await f.text());}catch(e){msg.style.color='#f85149';msg.textContent=t('imp_badjson');return;}
 msg.textContent='…';
 let r=await fetch('/api/import',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({document:doc,mode:mode,passphrase:document.getElementById('exppw').value||''})});
 let d=await r.json();
 if(!d.ok){msg.style.color='#f85149';msg.textContent=d.msg||t('st_error');return;}
 msg.style.color='#3fb950';
 msg.textContent=t('imp_done')+' '+Object.keys(d.counts||{}).map(k=>k+': '+d.counts[k]).join(' · ');}
async function loadMStats(){let s=await(await fetch('/api/admin/stats')).json();
 document.getElementById('mstats').textContent=`${t('lbl_jobs')}: ${s.jobs_total} (${s.jobs_active} / ${s.jobs_finished}) · ${t('lbl_lib')}: ${s.lib_titles} (${s.lib_platforms}) · IGDB-Cache: ${s.igdb_cache}`;}
async function loadLogs(){let d=await(await fetch('/api/logs')).json();let b=document.getElementById('logbox');if(!b)return;b.textContent=(d.lines||[]).join('\\n');b.scrollTop=b.scrollHeight;}
async function admCache(){await fetch('/api/admin/cache/clear',{method:'POST'});document.getElementById('mmsg').textContent=t('done_word');loadMStats();}
async function admReindex(){await fetch('/api/admin/reindex',{method:'POST'});document.getElementById('mmsg').textContent=t('done_word');setTimeout(()=>{loadMStats();loadLogs();},1800);}
async function admClearJobs(){let r=await(await fetch('/api/jobs/clear-finished',{method:'POST'})).json();document.getElementById('mmsg').textContent=t('done_word')+' ('+(r.removed||0)+')';loadMStats();}
async function secGeneral(c){let s=await(await fetch('/api/settings')).json();let gg=s.general||{};let qo=s.quota||{};
 c.innerHTML=`<h3>${t('sec_general')}</h3>
  <div class=frow><label>${t('app_name')}</label><input id=gname value="${(gg.app_name||'Romseerr').replace(/"/g,'&quot;')}"></div>
  <div class=frow><label>${t('default_lang')}</label><select id=glang><option value=de ${(gg.default_lang||'de')=='de'?'selected':''}>Deutsch</option><option value=en ${gg.default_lang=='en'?'selected':''}>English</option><option value=fr ${gg.default_lang=='fr'?'selected':''}>Français</option><option value=es ${gg.default_lang=='es'?'selected':''}>Español</option><option value=it ${gg.default_lang=='it'?'selected':''}>Italiano</option></select></div>
  <div class=frow><label>${t('default_design')}</label><select id=gdesign>${DESIGNS.map(dz=>`<option value="${dz}" ${(gg.default_design||'seerr')==dz?'selected':''}>${t('d_'+dz)}</option>`).join('')}</select></div>
  <button onclick="saveGeneral()">${t('save')}</button> <span id=gmsg class=meta></span>
  <h3 style="margin-top:20px">Kontingent / Quota</h3>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=qen ${qo.enabled?'checked':''}> ${t('active')}</label><span></span></div>
  <div class=frow><input id=qcount type=number style="flex:0 0 90px" value="${qo.count||10}"><input id=qdays type=number style="flex:0 0 90px" value="${qo.days||7}"><span class=meta>Anfragen / X Tage · requests / X days</span></div>
  <button onclick="saveQuota()">${t('save')}</button> <span id=qmsg class=meta></span>
  <h3 style="margin-top:20px">API-Key</h3>
  <div class=frow><input id=akey readonly value="…"><button onclick="copyKey()">📋</button><button onclick="regenKey()">↻</button></div>
  <span class=meta>Header <code>X-Api-Key</code> oder <code>?apikey=…</code></span>`;
 let k=await(await fetch('/api/apikey')).json();document.getElementById('akey').value=k.apikey||'';}
async function regenKey(){if(!confirm('Neuen API-Key erzeugen? Alter wird ungültig. / Regenerate API key?'))return;
 let k=await(await fetch('/api/apikey/regenerate',{method:'POST'})).json();document.getElementById('akey').value=k.apikey||'';}
function copyKey(){let e=document.getElementById('akey');e.select();if(navigator.clipboard)navigator.clipboard.writeText(e.value);}
async function saveGeneral(){let d={general:{app_name:document.getElementById('gname').value.trim(),default_lang:document.getElementById('glang').value,default_design:document.getElementById('gdesign').value}};
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('gmsg').textContent=r.ok?t('saved'):t('st_error');}
async function saveQuota(){let d={quota:{enabled:document.getElementById('qen').checked,count:+document.getElementById('qcount').value,days:+document.getElementById('qdays').value}};
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('qmsg').textContent=r.ok?t('saved_ok'):t('st_error');}
async function secNotif(c){let s=await(await fetch('/api/settings')).json();let dc=s.discord||{};let sm=s.smtp||{};let ag=s.agents||{};
 c.innerHTML=`<h3>${t('notif_discord')}</h3>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=dcen ${dc.enabled?'checked':''}> ${t('active')}</label><span></span></div>
  <div class=frow><input id=dcurl placeholder="${t('webhook_ph')}" value="${(dc.url||'').replace(/"/g,'&quot;')}"><button onclick="testNotify()">${t('test')}</button></div>
  <div class=frow><button onclick="saveSettings()">${t('save')}</button><span id=serr class=meta></span></div>
  <h3 style="margin-top:20px">E-Mail (SMTP)</h3>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=smen ${sm.enabled?'checked':''}> ${t('active')}</label><span></span></div>
  <div class=frow><input id=smhost placeholder="Host" value="${(sm.host||'').replace(/"/g,'&quot;')}"><input id=smport placeholder="Port" style="flex:0 0 80px" value="${sm.port||'587'}"></div>
  <div class=frow><input id=smuser placeholder="User" value="${(sm.user||'').replace(/"/g,'&quot;')}"><input id=smpass type=password placeholder="${sm.has_pass?'•••• gesetzt':'Passwort'}"></div>
  <div class=frow><input id=smfrom placeholder="Absender / From" value="${(sm.from||'').replace(/"/g,'&quot;')}"><select id=smtls style="flex:0 0 120px"><option value=starttls ${sm.tls=='starttls'?'selected':''}>STARTTLS</option><option value=ssl ${sm.tls=='ssl'?'selected':''}>SSL</option><option value=none ${sm.tls=='none'?'selected':''}>none</option></select></div>
  <div class=frow><input id=smto placeholder="Test an / to"><button onclick="mailTest()">${t('test')}</button></div>
  <div class=frow><button onclick="saveSmtp()">${t('save')}</button><span id=smmsg class=meta></span></div>
  <h3 style="margin-top:20px">Weitere Agenten / More agents</h3>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=agem ${(ag.email||{}).enabled?'checked':''}> E-Mail bei Verfügbarkeit / email on availability</label><span></span></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=agtgen ${(ag.telegram||{}).enabled?'checked':''}> Telegram</label><span></span></div>
  <div class=frow><input id=agtgtok type=password placeholder="${(ag.telegram||{}).has_token?'•••• Token gesetzt':'Bot-Token'}"><input id=agtgchat placeholder="Chat-ID" value="${((ag.telegram||{}).chat||'').replace(/"/g,'&quot;')}"></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=agwhen ${(ag.webhook||{}).enabled?'checked':''}> Webhook (generisch / Slack-kompatibel)</label><span></span></div>
  <div class=frow><input id=agwhurl placeholder="Webhook-URL" value="${((ag.webhook||{}).url||'').replace(/"/g,'&quot;')}"></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=aggoen ${(ag.gotify||{}).enabled?'checked':''}> Gotify</label><span></span></div>
  <div class=frow><input id=aggourl placeholder="Gotify-URL (https://gotify.host)" value="${((ag.gotify||{}).url||'').replace(/"/g,'&quot;')}"><input id=aggotok type=password placeholder="${(ag.gotify||{}).has_token?'•••• App-Token gesetzt':'App-Token'}"></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=agnten ${(ag.ntfy||{}).enabled?'checked':''}> ntfy</label><span></span></div>
  <div class=frow><input id=agnturl placeholder="ntfy-URL (Standard https://ntfy.sh)" value="${((ag.ntfy||{}).url||'').replace(/"/g,'&quot;')}"><input id=agnttopic placeholder="Topic" style="flex:0 0 160px" value="${((ag.ntfy||{}).topic||'').replace(/"/g,'&quot;')}"><input id=agnttok type=password placeholder="${(ag.ntfy||{}).has_token?'•••• Token':'Token (optional)'}"></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=agpoen ${(ag.pushover||{}).enabled?'checked':''}> Pushover</label><span></span></div>
  <div class=frow><input id=agpouser placeholder="User-Key" value="${((ag.pushover||{}).user||'').replace(/"/g,'&quot;')}"><input id=agpotok type=password placeholder="${(ag.pushover||{}).has_token?'•••• App-Token gesetzt':'App-Token'}"></div>
  <div class=frow><button onclick="saveAgents()">${t('save')}</button><button onclick="testAgents()" style="margin-left:8px;background:#2a2f37">${t('test')}</button><span id=agmsg class=meta></span></div>
  <h3 style="margin-top:20px">Mail-Protokoll / Mail log</h3><div id=mlog class=meta>…</div>`;
 let ml=await(await fetch('/api/maillog')).json();
 document.getElementById('mlog').innerHTML=ml.length?ml.map(m=>`<div class=frow><span>${m.ok?'🟢':'🔴'} ${m.ts} → ${(''+(m.to||'')).replace(/</g,'&lt;')}</span><span class=meta>${(''+(m.subject||'')).replace(/</g,'&lt;')}${m.err?(' · '+(''+m.err).replace(/</g,'&lt;')):''}</span></div>`).join(''):'—';}
async function saveSmtp(){let d={smtp:{enabled:document.getElementById('smen').checked,host:document.getElementById('smhost').value,port:document.getElementById('smport').value,user:document.getElementById('smuser').value,from:document.getElementById('smfrom').value,tls:document.getElementById('smtls').value}};
 let pw=document.getElementById('smpass').value;if(pw)d.smtp.pass=pw;
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('smmsg').textContent=r.ok?t('saved_ok'):t('st_error');return r.ok;}
async function mailTest(){let to=document.getElementById('smto').value.trim();if(!to)return;await saveSmtp();
 let r=await(await fetch('/api/settings/mail-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:to})})).json();
 document.getElementById('smmsg').textContent=r.ok?t('test_sent'):(r.msg||t('st_error'));}
async function saveAgents(){let d={agents:{email:{enabled:document.getElementById('agem').checked},
  telegram:{enabled:document.getElementById('agtgen').checked,chat:document.getElementById('agtgchat').value},
  webhook:{enabled:document.getElementById('agwhen').checked,url:document.getElementById('agwhurl').value},
  gotify:{enabled:document.getElementById('aggoen').checked,url:document.getElementById('aggourl').value},
  ntfy:{enabled:document.getElementById('agnten').checked,url:document.getElementById('agnturl').value,topic:document.getElementById('agnttopic').value},
  pushover:{enabled:document.getElementById('agpoen').checked,user:document.getElementById('agpouser').value}}};
 let tok=document.getElementById('agtgtok').value;if(tok)d.agents.telegram.token=tok;
 let got=document.getElementById('aggotok').value;if(got)d.agents.gotify.token=got;
 let ntt=document.getElementById('agnttok').value;if(ntt)d.agents.ntfy.token=ntt;
 let pot=document.getElementById('agpotok').value;if(pot)d.agents.pushover.token=pot;
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('agmsg').textContent=r.ok?t('saved_ok'):t('st_error');return r.ok;}
async function testAgents(){await saveAgents();
 let r=await(await fetch('/api/settings/notify-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})})).json();
 document.getElementById('agmsg').textContent=r.ok?t('test_sent'):(r.msg||t('st_error'));}
async function secUsers(c){let list=await(await fetch('/api/users')).json();
 c.innerHTML=`<h3>${t('users')}</h3><div id=ulist></div>
  <h3 style="margin-top:18px">${t('new_user')}</h3>
  <div class=frow><input id=nu placeholder="${t('username')}"><input id=np type=password placeholder="${t('password')}">
   <select id=nr><option value=user>${t('role_user')}</option><option value=admin>${t('role_admin')}</option></select>
   <button onclick="addUser()">${t('create')}</button></div>
  <div id=uerr class=meta style="color:#ff6b6b"></div>`;
 renderUsers(list);}
async function secServices(c){c.innerHTML=`<h3>${t('sec_services')}</h3><button onclick="setSection('services')">${t('refresh')}</button><div id=svc style="margin-top:12px">…</div>`;
 let list=await(await fetch('/api/services/status')).json();
 document.getElementById('svc').innerHTML=list.map(s=>`<div class=frow><span>${s.ok?'🟢':'🔴'} <b>${s.name}</b></span><span class=meta>${(''+ (s.info||'')).replace(/</g,'&lt;')}</span></div>`).join('');}
async function secAbout(c){
 let st={};try{st=await(await fetch('/api/admin/stats')).json();}catch(e){}
 let ver={};try{ver=await(await fetch('/api/version?check=1')).json();}catch(e){}
 let repo='https://github.com/Sparxx947/romseerr';
 let build=[ver.commit?ver.commit.slice(0,7):'',ver.built_at||''].filter(Boolean).join(' · ');
 let upd=ver.update_available?` <a href="${repo}/releases/latest" target=_blank style="color:#5b8cff">${t('upd_avail')} ${ver.latest}</a>`
        :(ver.latest?` <span style="color:#3fb950">${t('upd_current')}</span>`:'');
 c.innerHTML=`<h3>🎮 Romseerr — ${t('sec_about')}</h3>
  <p class=meta style="margin:2px 0 12px">${t('about_txt')}</p>
  <div class=frow><span style="min-width:150px">${t('version')}</span><span class=meta>${ver.version||window.VERSION||'—'}${upd}</span></div>
  ${build?`<div class=frow><span style="min-width:150px">${t('about_build')}</span><span class=meta>${build}</span></div>`:''}
  <div class=frow><span style="min-width:150px">${t('about_lib')}</span><span class=meta>${(st.lib_titles||0).toLocaleString()} ${t('about_titles')} · ${st.lib_platforms||0} ${t('about_platforms')}</span></div>
  <div class=frow><span style="min-width:150px">${t('about_jobs')}</span><span class=meta>${st.jobs_total||0} (${st.jobs_active||0} ${t('about_active')})</span></div>
  <h3 style="font-size:13px;margin-top:16px">${t('about_links')}</h3>
  <div class=meta style="line-height:1.9">
   🔗 <a href="${repo}" target=_blank style="color:#5b8cff">GitHub-Repo</a><br>
   📖 <a href="${repo}/wiki" target=_blank style="color:#5b8cff">Wiki</a> · <a href="/api/docs" target=_blank style="color:#5b8cff">API-Doku</a> · <a href="${repo}/blob/main/CHANGELOG.md" target=_blank style="color:#5b8cff">Changelog</a><br>
   🐞 <a href="${repo}/issues" target=_blank style="color:#5b8cff">Issues melden</a> · 🔒 <a href="${repo}/security/advisories/new" target=_blank style="color:#5b8cff">Sicherheitslücke melden</a>
  </div>
  <h3 style="font-size:13px;margin-top:16px">${t('about_feat')}</h3>
  <div class=meta style="line-height:1.7">${t('about_feat_txt')}</div>
  <h3 style="font-size:13px;margin-top:16px">${t('about_stack')}</h3>
  <div class=meta style="line-height:1.7">${t('about_stack_txt')}</div>
  <p class=meta style="margin-top:16px">${t('about_license')} · <button onclick="startWizard()" style="background:#2a2f37;border:none;color:#e6e8ec;padding:5px 10px;border-radius:6px;cursor:pointer">${t('wiz_reopen')}</button></p>`;}
async function secBlocklist(c){let list=await(await fetch('/api/blocklist')).json();
 c.innerHTML=`<h3>${t('blocklist')}</h3><div id=bllist></div>
  <div class=frow><input id=blnew placeholder="${t('pattern_ph')}"><button onclick="blAdd()">${t('add_btn')}</button></div>`;
 renderBlock(list);}
function renderBlock(list){window.BL=list.slice();let d=document.getElementById('bllist');d.innerHTML='';
 list.forEach((p,i)=>{let row=document.createElement('div');row.className='frow';
  let s=document.createElement('span');s.textContent='🚫 '+p;row.appendChild(s);
  let b=document.createElement('button');b.textContent=t('del');b.onclick=()=>{window.BL.splice(i,1);blSave();};
  row.appendChild(b);d.appendChild(row);});}
async function blSave(){let r=await(await fetch('/api/blocklist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({patterns:window.BL})})).json();
 if(r.ok)setSection('blocklist');}
function blAdd(){let v=document.getElementById('blnew').value.trim();if(!v)return;window.BL=(window.BL||[]).concat([v]);blSave();}
async function saveSettings(){let d={discord:{enabled:document.getElementById('dcen').checked,url:document.getElementById('dcurl').value.trim()}};
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('serr').textContent=r.ok?t('saved'):t('st_error');}
async function testNotify(){let d={discord:{url:document.getElementById('dcurl').value.trim()}};
 let r=await(await fetch('/api/settings/notify-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('serr').textContent=r.ok?t('test_sent'):(r.msg||t('st_error'));}
async function approveJob(id){await fetch('/api/jobs/'+id+'/approve',{method:'POST'});loadJobs();}
async function denyJob(id){await fetch('/api/jobs/'+id+'/deny',{method:'POST'});loadJobs();}
async function retryJob(id){await fetch('/api/jobs/'+id+'/retry',{method:'POST'});loadJobs();}
async function openUsers(){let m=document.getElementById('modal');m.style.display='block';
 let list=await(await fetch('/api/users')).json();
 let inp='style="flex:1;min-width:90px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px"';
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <div class=sec><h3>${t('users')}</h3><div id=ulist></div></div>
  <div class=sec><h3>${t('new_user')}</h3>
   <div class=row><input id=nu placeholder="${t('username')}" ${inp}>
    <input id=np type=password placeholder="${t('password')}" ${inp}>
    <select id=nr ${inp}><option value=user>${t('role_user')}</option><option value=admin>${t('role_admin')}</option></select>
    <label style="font-size:12px;color:#8b929e;display:flex;gap:5px;align-items:center"><input type=checkbox id=naa> ${t('autoapprove')}</label>
    <button onclick="addUser()">${t('create')}</button></div>
   <div id=uerr style="color:#ff6b6b;font-size:12px;margin-top:6px"></div></div></div>`;
 renderUsers(list);}
const PERM_KEYS=['request','autoapprove','manage_requests','manage_users','manage_issues','manage_settings','quota_exempt'];
const PERM_LBL={request:'Anfragen',autoapprove:'Auto-Freigabe',manage_requests:'Anfr. verwalten',manage_users:'Benutzer',manage_issues:'Probleme',manage_settings:'Einstellungen',quota_exempt:'kein Limit'};
function renderUsers(list){let ul=document.getElementById('ulist');ul.innerHTML='';
 list.forEach(u=>{let row=document.createElement('div');row.style.cssText='background:#171a20;border-radius:8px;padding:10px;margin-bottom:8px';
  let head=document.createElement('div');head.style.cssText='display:flex;justify-content:space-between;align-items:center';
  head.innerHTML=`<b>${u.role=='admin'?'👑 ':'👤 '}${(''+u.username).replace(/</g,'&lt;')}</b>`;
  let del=document.createElement('button');del.textContent=t('del');del.style.cssText='background:#6e2a2a;border:none;color:#fff;padding:4px 10px;border-radius:6px;cursor:pointer';
  del.onclick=async()=>{let d=await(await fetch('/api/users/'+encodeURIComponent(u.username),{method:'DELETE'})).json();if(d.ok)setSection('users');else alert(d.msg||'Fehler');};
  head.appendChild(del);row.appendChild(head);
  if(u.role=='admin'){let a=document.createElement('div');a.className='meta';a.style.marginTop='6px';a.textContent='alle Rechte / all permissions';row.appendChild(a);}
  else{let pg=document.createElement('div');pg.style.cssText='display:flex;flex-wrap:wrap;gap:10px;margin-top:8px';
   PERM_KEYS.forEach(pk=>{let lbl=document.createElement('label');lbl.style.cssText='font-size:11px;color:#8b929e;display:flex;gap:4px;align-items:center';
    let cb=document.createElement('input');cb.type='checkbox';cb.checked=(u.perms||[]).includes(pk);
    cb.onchange=()=>{let np=(u.perms||[]).filter(x=>x!=pk);if(cb.checked)np.push(pk);u.perms=np;
     fetch('/api/users/'+encodeURIComponent(u.username),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({perms:np})});};
    lbl.appendChild(cb);lbl.appendChild(document.createTextNode(PERM_LBL[pk]));pg.appendChild(lbl);});
   row.appendChild(pg);}
  ul.appendChild(row);});}
async function addUser(){let u=document.getElementById('nu').value.trim(),p=document.getElementById('np').value,r=document.getElementById('nr').value;
 let d=await(await fetch('/api/users',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({username:u,password:p,role:r})})).json();
 if(d.ok)setSection('users');else document.getElementById('uerr').textContent=d.msg||'Fehler';}
async function logout(){await fetch('/api/logout',{method:'POST'});location.href='/login';}
document.querySelectorAll('#langsw b').forEach(e=>e.classList.toggle('on',e.dataset.l==LANG));
applyI18n();loadAuth();loadPlatforms();loadDiscover();updateMsgBadge();
if('serviceWorker'in navigator){navigator.serviceWorker.register('/sw.js').catch(()=>{});}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key=='Enter')search();});
setInterval(()=>{if(cur=='j')loadJobs();},4000);
</script></body></html>"""

LOGIN_PAGE = """<!doctype html><html lang=de><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Romseerr — Anmelden</title>
<style>
:root{--acc:#6c5ce7}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
 font-family:system-ui,sans-serif;background:radial-gradient(1100px 550px at 50% -10%,#2a2350,#0b0d10);color:#e6e8ec}
.card{background:#171a21;border:1px solid #262b33;border-radius:16px;padding:30px;width:340px;box-shadow:0 20px 60px #0008}
h1{margin:0 0 2px;font-size:28px;text-align:center;background:linear-gradient(90deg,#8a7bff,#6c5ce7);-webkit-background-clip:text;background-clip:text;color:transparent}
p.sub{margin:0 0 18px;text-align:center;color:#8b929e;font-size:13px}
input{width:100%;padding:11px 13px;margin:6px 0;border-radius:10px;border:1px solid #2c323b;background:#0b0d10;color:#e6e8ec;font-size:15px}
button{width:100%;padding:12px;margin-top:10px;border:none;border-radius:10px;background:var(--acc);color:#fff;font-weight:600;font-size:15px;cursor:pointer}
.err{color:#ff6b6b;font-size:13px;min-height:18px;text-align:center;margin-top:8px}
</style></head><body>
<form class=card onsubmit="go(event)">
<h1>🎮 Romseerr</h1><p class=sub id=sub>Anmelden</p>
<input id=u placeholder=Benutzername autofocus autocomplete=username>
<input id=p type=password placeholder=Passwort autocomplete=current-password>
<button id=btn>Anmelden</button><div class=err id=err></div>
<div style="text-align:center;margin-top:10px"><a href="#" id=fgt onclick="forgot();return false" style="color:#8b929e;font-size:12px">Passwort vergessen? / Forgot password?</a></div>
<div style="text-align:center;margin-top:14px;color:#5c6270;font-size:11px" id=ver></div>
</form>
<script>
let setup=false;
fetch('/api/version').then(r=>r.json()).then(v=>{document.getElementById('ver').textContent='v'+v.version;}).catch(()=>{});
fetch('/api/auth/status').then(r=>r.json()).then(d=>{if(d.user){location.href='/';return;}
 setup=d.setup;if(setup){document.getElementById('sub').textContent='Ersteinrichtung — Administrator anlegen';
 document.getElementById('btn').textContent='Administrator anlegen';document.getElementById('fgt').style.display='none';}});
async function forgot(){let q=prompt('Benutzername oder E-Mail / username or email:');if(!q)return;
 await fetch('/api/forgot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:q})});
 let e=document.getElementById('err');e.style.color='#8b929e';
 e.textContent='Falls die Adresse existiert, wurde eine Mail gesendet. / If the address exists, an email was sent.';}
async function go(e){e.preventDefault();
 let u=document.getElementById('u').value.trim(),p=document.getElementById('p').value;
 let r=await fetch(setup?'/api/setup':'/api/login',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({username:u,password:p})});
 let d=await r.json();if(d.ok)location.href='/';else document.getElementById('err').textContent=d.msg||'Fehler';}
</script></body></html>"""

RESET_PAGE = """<!doctype html><html lang=de><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Romseerr — Reset</title>
<style>
:root{--acc:#6c5ce7}*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:system-ui,sans-serif;background:radial-gradient(1100px 550px at 50% -10%,#2a2350,#0b0d10);color:#e6e8ec}
.card{background:#171a21;border:1px solid #262b33;border-radius:16px;padding:30px;width:340px;box-shadow:0 20px 60px #0008}
h1{margin:0 0 2px;font-size:28px;text-align:center;background:linear-gradient(90deg,#8a7bff,#6c5ce7);-webkit-background-clip:text;background-clip:text;color:transparent}
p.sub{margin:0 0 18px;text-align:center;color:#8b929e;font-size:13px}
input{width:100%;padding:11px 13px;margin:6px 0;border-radius:10px;border:1px solid #2c323b;background:#0b0d10;color:#e6e8ec;font-size:15px}
button{width:100%;padding:12px;margin-top:10px;border:none;border-radius:10px;background:var(--acc);color:#fff;font-weight:600;font-size:15px;cursor:pointer}
.err{color:#ff6b6b;font-size:13px;min-height:18px;text-align:center;margin-top:8px}
</style></head><body>
<form class=card onsubmit="go(event)">
<h1>🎮 Romseerr</h1><p class=sub>Neues Passwort setzen / Set new password</p>
<input id=p type=password placeholder="Neues Passwort / New password" autofocus>
<button>Speichern / Save</button><div class=err id=err></div>
</form>
<script>
let tok=new URLSearchParams(location.search).get('token')||'';
async function go(e){e.preventDefault();
 let r=await fetch('/api/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:tok,new:document.getElementById('p').value})});
 let d=await r.json();if(d.ok)location.href='/login';else document.getElementById('err').textContent=d.msg||'Fehler';}
</script></body></html>"""

@app.route("/")
@login_required
def index(): return Response(PAGE, mimetype="text/html")

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
            out["error"] = str(e)[:150]
    return jsonify(out)

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
    return jsonify(js[:100])

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

@app.route("/api/wishlist/remove", methods=["POST"])
def api_wishlist_remove():
    user = session.get("user", "") or "api"
    d = request.get_json(force=True) or {}
    wishlist_remove(user, (d.get("title") or "").strip(), d.get("platform"))
    return jsonify({"ok": True})

@app.route("/health")
def health(): return jsonify({"ok":True,"lib_titles":len(LIB['all']),"jobs":len(JOBS)})

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
    out = {"version": VERSION, "commit": BUILD_COMMIT, "built_at": BUILD_DATE}
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
    if p in PUBLIC: return
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
def login_page(): return Response(LOGIN_PAGE, mimetype="text/html")

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
    try:
        requests.post(wh, json={"content":"✅ Romseerr — persönlicher Test / personal test"}, timeout=8)
        return jsonify({"ok":True})
    except Exception as e:
        return jsonify({"ok":False,"msg":str(e)[:100]}), 400

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
def reset_page(): return Response(RESET_PAGE, mimetype="text/html")

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
        try: requests.post(wh, json={"content": f"✉ **{me}**: {body[:200]}"}, timeout=8)
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

@app.route("/api/jobs/clear-finished", methods=["POST"])
@perm_required("manage_requests")
def api_jobs_clear_finished():
    global JOBS
    with JOBS_LOCK:
        before = len(JOBS); JOBS = [j for j in JOBS if j.get("state") not in JOB_FINISHED]; save_jobs()
        removed = before - len(JOBS)
    log(f"{removed} abgeschlossene Anfragen entfernt (Admin)")
    return jsonify({"ok": True, "removed": removed})

# ---------- PWA + Web-Push ----------
MANIFEST = {"name":"Romseerr","short_name":"Romseerr","start_url":"/","scope":"/",
    "display":"standalone","background_color":"#0b0d10","theme_color":"#0b0d10",
    "icons":[{"src":"/icon.svg","sizes":"any","type":"image/svg+xml","purpose":"any maskable"}]}
ICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">'
    '<rect width="192" height="192" rx="36" fill="#5b8cff"/>'
    '<text x="96" y="132" font-size="104" text-anchor="middle" font-family="sans-serif">🎮</text></svg>')
SW_JS = """self.addEventListener('install',e=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('push',function(e){let d={title:'Romseerr',body:''};
 try{d=e.data.json()}catch(_){if(e.data)d.body=e.data.text()}
 e.waitUntil(self.registration.showNotification(d.title||'Romseerr',{body:d.body||'',icon:'/icon.svg',badge:'/icon.svg'}));});
self.addEventListener('notificationclick',function(e){e.notification.close();
 e.waitUntil(clients.matchAll({type:'window'}).then(cs=>{for(const c of cs){if('focus'in c)return c.focus();}if(clients.openWindow)return clients.openWindow('/');}));});
"""

@app.route("/manifest.webmanifest")
def pwa_manifest(): return Response(json.dumps(MANIFEST), mimetype="application/manifest+json")

@app.route("/icon.svg")
def pwa_icon(): return Response(ICON_SVG, mimetype="image/svg+xml")

@app.route("/sw.js")
def pwa_sw(): return Response(SW_JS, mimetype="application/javascript")

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
    save_users(users); return jsonify({"ok":True})

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
    """Verschlüsselte Geheimnisse zurückholen. Falsche Passphrase -> ValueError."""
    sec = doc.get("secrets") or {}
    if sec.get("mode") != "encrypted": return {}
    if not passphrase: raise ValueError("Passphrase fehlt / passphrase missing")
    try:
        f = _fernet(passphrase, base64.b64decode(sec["salt"]), int(sec.get("iterations") or 200_000))
        return json.loads(f.decrypt(sec["data"].encode()).decode())
    except Exception:
        raise ValueError("Passphrase falsch oder Daten beschädigt / wrong passphrase or corrupt data")

def _unredact(value, current):
    """REDACTED heißt „behalte, was da ist" — auch im replace-Modus. Ein Export ohne
    Geheimnisse darf beim Zurückspielen nicht den laufenden API-Key wegwischen."""
    return current if value == REDACTED else value

def apply_import(doc, mode, passphrase=""):
    """Dokument übernehmen. `mode` muss der Aufrufer ausdrücklich wählen:
    `replace` ersetzt den jeweiligen Bereich vollständig, `merge` legt ihn darüber."""
    if not isinstance(doc, dict) or doc.get("app") != "romseerr":
        raise ValueError("kein Romseerr-Export / not a Romseerr export")
    schema = doc.get("schema")
    if not isinstance(schema, int):
        raise ValueError("Schema-Version fehlt / schema version missing")
    if schema > EXPORT_SCHEMA:
        raise ValueError(f"Schema {schema} ist neuer als diese Version (max {EXPORT_SCHEMA}) — "
                         f"bitte Romseerr aktualisieren / newer than this build, please update")
    if schema < 1:
        raise ValueError(f"Schema {schema} wird nicht unterstützt / unsupported")
    if mode not in ("merge", "replace"):
        raise ValueError("mode muss 'merge' oder 'replace' sein / must be 'merge' or 'replace'")
    stash = _restore_secrets(doc, passphrase)
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
            raise ValueError("Import würde keinen Administrator mit Kennwort hinterlassen / "
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
    return counts

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
        counts = apply_import(doc, d.get("mode"), d.get("passphrase") or "")
    except ValueError as e:
        return jsonify({"ok": False, "msg": str(e)}), 400
    except Exception as e:
        log(f"Import-Fehler: {e}")
        return jsonify({"ok": False, "msg": f"Import fehlgeschlagen / failed: {str(e)[:120]}"}), 500
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
            info["error"] = str(e)[:100]
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
            return jsonify({"ok": False, "msg": "ungültig / invalid: " + str(e)[:140]}), 400
        os.makedirs(TLS_DIR, exist_ok=True)
        with open(TLS_CERT, "w") as f: f.write(cert)
        with open(TLS_KEY, "w") as f: f.write(key)
        try: os.chmod(TLS_CERT, 0o600); os.chmod(TLS_KEY, 0o600)
        except Exception: pass
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

@app.route("/api/services/status")
@admin_required
def api_services_status():
    out = []
    try:
        j = requests.get(f"{cfg("sab_url")}/api", params={"mode":"version","output":"json","apikey":cfg("sab_apikey")}, timeout=6).json()
        out.append({"name":"SABnzbd","ok":True,"info":"v"+str(j.get("version",""))})
    except Exception as e: out.append({"name":"SABnzbd","ok":False,"info":str(e)[:40]})
    try:
        r = requests.get(f"{cfg("prow_url")}/api/v1/system/status", headers={"X-Api-Key":cfg("prow_apikey")}, timeout=6)
        out.append({"name":"Prowlarr","ok":r.ok,"info":"v"+str(r.json().get("version",""))})
    except Exception as e: out.append({"name":"Prowlarr","ok":False,"info":str(e)[:40]})
    try:
        r = requests.get(f"{cfg("romm_url")}/api/heartbeat", timeout=6)
        out.append({"name":"RomM","ok":r.ok,"info":"erreichbar"})
    except Exception as e: out.append({"name":"RomM","ok":False,"info":str(e)[:40]})
    out.append({"name":"IGDB","ok":bool(igdb_token()),"info":"Cover / Discover"})
    if cfg("sgdb_key"):
        try:
            r = requests.get("https://www.steamgriddb.com/api/v2/search/autocomplete/mario",
                             headers={"Authorization":"Bearer "+cfg("sgdb_key")}, timeout=6)
            out.append({"name":"SteamGridDB","ok":r.ok,"info":"Cover-Fallback"})
        except Exception as e: out.append({"name":"SteamGridDB","ok":False,"info":str(e)[:40]})
    if cfg("ss_user"):
        out.append({"name":"ScreenScraper","ok":True,"info":"Zugang hinterlegt / configured"})
    out.append({"name":"Archive.org","ok":True,"info":"public API"})
    return jsonify(out)

@app.route("/api/settings/notify-test", methods=["POST"])
@admin_required
def api_settings_test():
    d = request.get_json(silent=True) or {}; dc = d.get("discord") or {}
    if dc.get("url"):
        try:
            requests.post(dc["url"], json={"content":"✅ Romseerr — Testbenachrichtigung / test notification"}, timeout=8)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "msg": str(e)[:120]}), 400
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

@app.route("/api/jobs/<jid>/retry", methods=["POST"])
@perm_required("manage_requests")
def api_job_retry(jid):
    j = get_job(jid)
    if not j: return jsonify({"ok": False}), 404
    if j.get("state") not in ("error", "denied"):
        return jsonify({"ok": False, "msg": "nur fehlgeschlagene/abgelehnte / only failed/denied"}), 400
    set_state(jid, state="queued", msg="erneut / retried"); Q.put(jid)
    return jsonify({"ok": True})

@app.route("/api/users/<u>", methods=["DELETE"])
@perm_required("manage_users")
def api_users_del(u):
    users = load_users()
    if u not in users: return jsonify({"ok":False,"msg":"unbekannt"}), 404
    if u == session.get("user"): return jsonify({"ok":False,"msg":"nicht sich selbst"}), 400
    admins = [x for x,v in users.items() if v.get("role")=="admin"]
    if users[u].get("role")=="admin" and len(admins)<=1:
        return jsonify({"ok":False,"msg":"letzter Admin"}), 400
    users.pop(u,None); save_users(users); return jsonify({"ok":True})

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
        "/health": {"get": _op("Liveness-Probe (Titelzahl, Jobs)", "System", _PUB)},
        "/api/version": {"get": _op("Laufende Version, Commit und Bauzeitpunkt (optional Update-Abgleich)", "System", _PUB,
            params=[_qp("check", "1 = zusätzlich gegen den Release-Feed prüfen (latest, update_available)")])},
        "/metrics": {"get": _op("Betriebsmetriken im Prometheus-Textformat (Auth wie API)", "System",
            responses={**_R_AUTH, "200": {"description": "text/plain; version=0.0.4"}})},
        "/api/auth/status": {"get": _op("Anmelde-/Setup-Status, App-Name, Version", "System", _PUB)},
        "/manifest.webmanifest": {"get": _op("PWA-Manifest", "System", _PUB)},
        "/sw.js": {"get": _op("Service-Worker", "System", _PUB)},
        "/icon.svg": {"get": _op("App-Icon", "System", _PUB)},
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
        "/api/cover": {"get": _op("Cover-URL zu einem Titel (lazy, via IGDB)", "Search",
            params=[_qp("title", "Titel")])},
        "/api/platforms": {"get": _op("Verfügbare Plattformen/Slugs", "Search")},
        # --- Requests / Jobs ---
        "/api/download": {"post": _op("ROM anfragen/herunterladen (Auto-Freigabe oder pending)", "Requests",
            body={"type": "object", "description": "Trefferobjekt aus /api/search bzw. /api/detail"},
            responses={**_R_AUTH, "200": {"description": "Job angelegt"}})},
        "/api/jobs": {"get": _op("Eigene Anfragen (Admin: alle) mit Status", "Requests")},
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

REDOC_PAGE = """<!doctype html><html><head><meta charset=utf-8>
<title>Romseerr API</title><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{margin:0}</style></head><body>
<redoc spec-url="/api/openapi.json"></redoc>
<script src="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js"></script>
</body></html>"""

@app.route("/api/openapi.json")
def api_openapi(): return jsonify(OPENAPI)

@app.route("/api/docs")
def api_docs(): return Response(REDOC_PAGE, mimetype="text/html")

# ---------- Start ----------
def periodic_index():
    while True:
        time.sleep(600); beat("index"); build_index()

def check_config():
    """Beim Start einmal prüfen und WARNEN (nicht fatal), wenn optionale Dienste fehlen oder
    nicht erreichbar sind — spart Rätselraten, warum z. B. keine Cover oder kein Usenet da sind.
    Läuft im Hintergrund, damit die Erreichbarkeitsprüfung den Start nicht verzögert."""
    def reach(url):
        try: requests.get(url, timeout=4); return True
        except Exception: return False
    if not (cfg("igdb_id") and cfg("igdb_secret")):
        log("Konfig: IGDB nicht gesetzt — keine Cover/Discover.")
    if not (cfg("sab_url") and cfg("sab_apikey")):
        log("Konfig: SABnzbd nicht gesetzt — Usenet-Download aus.")
    elif not reach(cfg("sab_url")):
        log(f"Konfig-WARNUNG: SABnzbd ({cfg("sab_url")}) nicht erreichbar.")
    if not (cfg("prow_url") and cfg("prow_apikey")):
        log("Konfig: Prowlarr nicht gesetzt — Usenet-Suche aus.")
    elif not reach(cfg("prow_url")):
        log(f"Konfig-WARNUNG: Prowlarr ({cfg("prow_url")}) nicht erreichbar.")

if __name__ == "__main__":
    os.makedirs(STAGING, exist_ok=True)
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
