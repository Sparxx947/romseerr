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
VERSION      = "0.1.0"

# Basis-Verzeichnisse (per Env überschreibbar — Default = Container-Mounts; nötig für Tests)
CONFIG_DIR = os.environ.get("ROMSEERR_CONFIG", "/config")
ROMS       = os.environ.get("ROMSEERR_ROMS", "/roms")
SAB_DONE   = "/sab-complete"
JD_WATCH   = "/jd-watch"
JD_OUT     = "/jd-output/rom-suche"           # Sicht der rom-suche (=/mnt/user/Downloads/rom-suche)
JD_DL_BASE = os.environ.get("JD_DL_BASE","/output/rom-suche")  # Sicht des JD-Containers
STAGING    = os.path.join(CONFIG_DIR, "staging")
JOBDB      = os.path.join(CONFIG_DIR, "jobs.json")
LOGFILE    = os.path.join(CONFIG_DIR, "rom-suche.log")
USERS_FILE = os.path.join(CONFIG_DIR, "users.json")
SECRET_FILE= os.path.join(CONFIG_DIR, "secret.key")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
MAILLOG_FILE  = os.path.join(CONFIG_DIR, "maillog.json")
ISSUES_FILE   = os.path.join(CONFIG_DIR, "issues.json")
PUSH_FILE     = os.path.join(CONFIG_DIR, "push_subs.json")
VAPID_FILE    = os.path.join(CONFIG_DIR, "vapid.json")
DB_FILE       = os.path.join(CONFIG_DIR, "romseerr.db")

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
            c.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, data TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS jobs(seq INTEGER PRIMARY KEY AUTOINCREMENT, jid TEXT, data TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, data TEXT)")
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
    if not (IGDB_ID and IGDB_SECRET): return ""
    if time.time() > IGDB["exp"]:
        r = requests.post("https://id.twitch.tv/oauth2/token", params={
            "client_id": IGDB_ID, "client_secret": IGDB_SECRET,
            "grant_type": "client_credentials"}, timeout=8)
        j = r.json(); IGDB["token"] = j["access_token"]; IGDB["exp"] = time.time()+j.get("expires_in",3600)-60
    return IGDB["token"]

def igdb_query(endpoint, body):
    tok = igdb_token()
    if not tok: return []
    try:
        h = {"Client-ID": IGDB_ID, "Authorization": f"Bearer {tok}"}
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

def _cover_url(g):
    return f"https://images.igdb.com/igdb/image/upload/t_cover_big/{g['cover']['image_id']}.jpg" if g.get("cover") else ""

def igdb_cover(title): return _cover_url(igdb_game(title))
def igdb_desc(title):  return (igdb_game(title) or {}).get("summary", "")

def igdb_rich(title):
    key = "rich:" + norm(title)
    if key in IGDB["cache"]: return IGDB["cache"][key]
    d = igdb_query("games", f'search "{title[:60]}"; fields name,summary,rating,aggregated_rating,'
        f'genres.name,first_release_date,involved_companies.company.name,involved_companies.developer,'
        f'screenshots.image_id,similar_games.name; limit 1;')
    g = d[0] if isinstance(d, list) and d else {}
    rating = g.get("aggregated_rating") or g.get("rating")
    year = ""
    if g.get("first_release_date"):
        try: year = datetime.utcfromtimestamp(g["first_release_date"]).year
        except Exception: pass
    dev = ""
    for ic in g.get("involved_companies", []) or []:
        if ic.get("developer") and ic.get("company"): dev = ic["company"].get("name",""); break
    out = {"summary": g.get("summary",""), "rating": round(rating) if rating else None, "year": year,
           "developer": dev, "genres": [x.get("name") for x in g.get("genres",[]) or [] if x.get("name")],
           "screenshots": [f"https://images.igdb.com/igdb/image/upload/t_screenshot_med/{s['image_id']}.jpg"
                           for s in (g.get("screenshots",[]) or [])[:6] if s.get("image_id")],
           "similar": [x.get("name") for x in (g.get("similar_games",[]) or [])[:8] if x.get("name")]}
    IGDB["cache"][key] = out
    return out

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
    if not (PROW_URL and PROW_KEY and cats): return out
    try:
        u = f"{PROW_URL}/api/v1/search"
        r = requests.get(u, params={"query":q,"categories":cats,"type":"search","limit":limit},
                         headers={"X-Api-Key":PROW_KEY}, timeout=25)
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
        usenet_cats = PROW_CATS if any(SLUG2USE.get(p) for p in platforms) else ""
    else:
        usenet_cats = PROW_CATS
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
def sab_add(url, name):
    r = requests.get(f"{SAB_URL}/api", params={"mode":"addurl","name":url,"nzbname":name,
        "cat":SAB_CAT,"apikey":SAB_APIKEY,"output":"json"}, timeout=20)
    j = r.json()
    if not j.get("status"): raise RuntimeError(f"SAB: {j}")
    return j

def write_crawljob(jid, links, folder, name):
    # folder = JD-Container-Sicht (z.B. /output/rom-suche/...); JD legt sie selbst an.
    data = [{"text":"\n".join(links) if isinstance(links,list) else links,
             "downloadFolder":folder,"packageName":name,"enabled":"true","autoStart":"true",
             "autoConfirm":"true","overwritePackagizerRules":"true"}]
    path = os.path.join(JD_WATCH, f"romsuche_{jid}.crawljob")
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
        jid = Q.get()
        job = get_job(jid)
        if not job: continue
        try:
            if job["source"]=="usenet":
                set_state(jid, state="downloading", msg="an SAB übergeben")
                sab_add(job["ref"], f"romsuche_{jid}")
                # Ordnername in SAB-complete = romsuche_<jid>
            elif job["source"]=="archive":
                set_state(jid, state="downloading", msg="Archive.org-Download läuft")
                urls = archive_file_urls(job["ref"])
                if not urls: raise RuntimeError("keine ladbaren Dateien")
                dst = os.path.join(STAGING, f"romsuche_{jid}")
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
                write_crawljob(jid, job["ref"], f"{JD_DL_BASE}/romsuche_{jid}", f"romsuche_{jid}")
        except Exception as e:
            set_state(jid, state="error", msg=str(e)[:200]); log(f"Job {jid} Fehler: {e}")
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
    moved, by_plat = 0, {}
    for root,_,files in os.walk(folder):
        for fn in files:
            if SKIP_FILES.search(fn) or fn == ".urls": continue
            src = os.path.join(root,fn)
            ext = fn.rsplit(".",1)[-1].lower() if "." in fn else ""
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
            except Exception as e: log(f"move-Fehler {fn}: {e}")
    # Staging aufräumen
    try:
        if folder.startswith(STAGING): subprocess.run(["rm","-rf",folder])
    except Exception: pass
    build_index()
    romm_scan()
    where = ", ".join(f"{v}×{k}" for k,v in by_plat.items()) or "nichts (schon vorhanden?)"
    set_state(jid, state="done", msg=f"{moved} Datei(en) → {where}")
    log(f"Job {jid} fertig: {moved} Dateien → {where}")
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
    if not (ROMM_URL and ROMM_USER and ROMM_PASS): return
    try:
        s = requests.Session()
        s.post(f"{ROMM_URL}/api/login", auth=(ROMM_USER,ROMM_PASS), timeout=10)
        s.post(f"{ROMM_URL}/api/scan", json={"platforms":[], "type":"quick"}, timeout=10)
    except Exception as e:
        log(f"RomM-Scan-Hinweis: {e}")

def worker_collect():
    """Dauerthread (alle 20 s): sucht für noch laufende usenet/filehoster-Jobs den fertigen
    Ausgabeordner (SAB_DONE bzw. JD_OUT, Name `romsuche_<jid>`). Ist er **stabil** (Größe
    ändert sich nicht mehr), wird import_folder aufgerufen. So werden asynchrone Downloads
    eingesammelt, die worker_download nur angestoßen hat."""
    while True:
        try:
            with JOBS_LOCK:
                pending = [dict(j) for j in JOBS if j["state"]=="downloading" and j["source"] in ("usenet","filehoster")]
            for job in pending:
                jid = job["id"]; name = f"romsuche_{jid}"
                cand = None
                if job["source"]=="usenet":
                    p = os.path.join(SAB_DONE, name)
                    if os.path.isdir(p): cand = p
                else:
                    p = os.path.join(JD_OUT, name)
                    if os.path.isdir(p) and any(os.scandir(p)): cand = p
                if cand and folder_stable(cand):
                    import_folder(jid, cand)
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
:root{--bg:#14161a;--card:#1e2229;--acc:#7c5cff;--ok:#2ecc71;--txt:#e6e8ec;--mut:#8b929e}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:var(--bg);color:var(--txt)}
#side{position:fixed;top:0;left:0;bottom:0;width:210px;background:#0f1114;border-right:1px solid #262b33;display:flex;flex-direction:column;padding:16px 12px;z-index:6}
#side .logo{font-size:20px;font-weight:700;margin:4px 8px 18px;background:linear-gradient(90deg,#8a7bff,#6c5ce7);-webkit-background-clip:text;background-clip:text;color:transparent}
.nav{display:block;padding:10px 12px;border-radius:10px;color:var(--mut);font-size:14px;cursor:pointer;text-decoration:none;margin-bottom:4px}
.nav:hover{background:#1a1e25;color:var(--txt)}
.nav.on{background:var(--acc);color:#fff}
#side .grow{flex:1}
#side .ubox{border-top:1px solid #262b33;padding-top:10px}
#side .ubox #who{padding:4px 12px 8px;font-size:12px;color:var(--mut)}
main{margin-left:210px}
#topbar{position:sticky;top:0;background:#0f1114;padding:14px 18px;display:flex;gap:12px;align-items:center;border-bottom:1px solid #262b33;z-index:5}
input{flex:1;padding:11px 14px;border-radius:10px;border:1px solid #2c323b;background:#0b0d10;color:var(--txt);font-size:15px}
.fbtn{background:#1e2229;border:1px solid #2c323b;color:var(--txt);font-size:13px;cursor:pointer;padding:10px 12px;border-radius:10px;white-space:nowrap}
#langsw{display:flex;gap:8px;padding:6px 12px}
#langsw b{cursor:pointer;font-size:12px;color:var(--mut);font-weight:700}
#langsw b.on{color:var(--acc)}
#who{font-size:12px;color:var(--mut);display:flex;align-items:center;padding:4px 12px}
#who img{width:30px;height:30px;border-radius:50%;object-fit:cover;margin-right:7px;border:1px solid #2c323b}
@media(max-width:680px){#side{position:static;width:auto;flex-direction:row;flex-wrap:wrap;align-items:center;padding:10px}#side .logo{margin:0 12px 0 4px}#side .grow{display:none}#side .ubox{border:none;padding:0}main{margin-left:0}.nav{padding:8px 10px;margin:0}}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px;padding:18px}
.card{background:var(--card);border-radius:12px;overflow:hidden;display:flex;flex-direction:column;border:1px solid #262b33}
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
#modal .box{max-width:760px;margin:24px auto;background:var(--card);border:1px solid #262b33;border-radius:14px;overflow:hidden}
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
.pcover{aspect-ratio:3/4;border-radius:10px;background:#0b0d10 center/cover no-repeat;position:relative;border:1px solid #262b33;transition:border-color .15s,transform .15s}
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
 <a class=nav id=nSet data-i18n=nav_settings onclick="show('set')" style="display:none">⚙️ Einstellungen</a>
 <div class=grow></div>
 <div id=langsw><b data-l=de class=on onclick="setLang('de')">DE</b><b data-l=en onclick="setLang('en')">EN</b><b data-l=fr onclick="setLang('fr')">FR</b><b data-l=es onclick="setLang('es')">ES</b></div>
 <div class=ubox><div id=who onclick="openProfile()" style="cursor:pointer"></div>
  <a class=nav data-i18n=profile onclick="openProfile()">👤 Profil</a>
  <a class=nav data-i18n=logout onclick="logout()">🚪 Abmelden</a></div>
</div>
<main>
 <div id=topbar>
  <input id=q data-i18n-ph=search_ph placeholder="Spiel suchen … (Enter)" autofocus>
  <button class=fbtn id=tF onclick="toggleFilter()">🎛 Plattformen: Alle</button>
 </div>
 <div id=filter></div>
 <div id=discview><div id=grid></div><div class=hint id=hint data-i18n=hint_type>Tippe einen Titel und drücke Enter.</div></div>
 <div id=jobs></div>
 <div id=settings></div>
 <div id=issues></div>
</main>
<div id=modal></div>
<script>
const I18N={de:{
 nav_discover:'🔍 Entdecken',nav_requests:'📥 Anfragen',nav_users:'👤 Benutzer',nav_settings:'⚙️ Einstellungen',logout:'🚪 Abmelden',
 search_ph:'Spiel suchen … (Enter)',platforms:'Plattformen',all:'Alle',selected:'gewählt',
 hint_type:'Tippe einen Titel und drücke Enter.',loading_home:'Lade Startseite …',popular_on:'Beliebt auf',click_search:'klick zum Suchen',
 searching:'Suche läuft …',no_results:'Keine Treffer.',results:'Treffer',in_library:'✓ in Bibliothek',download:'⬇ Download',requested:'✓ angefragt',collection:'Sammlung',
 versions:'Versionen / Quellen',files:'Dateien',no_desc:'Keine Beschreibung verfügbar.',screenshots:'Screenshots',similar:'Ähnliche Spiele',
 no_requests:'Noch keine Anfragen.',approve:'Freigeben',deny:'Ablehnen',reset:'Alle zurücksetzen',
 users:'Benutzer',new_user:'Neuen Benutzer anlegen',create:'Anlegen',del:'Löschen',autoapprove:'Auto-Freigabe',role_user:'Nutzer',role_admin:'Admin',username:'Benutzername',password:'Passwort',
 notif_discord:'Benachrichtigungen — Discord',active:'aktiv',test:'Test',save:'Speichern',saved:'gespeichert ✓',test_sent:'Test gesendet ✓',webhook_ph:'Discord Webhook-URL',
 st_pending:'⏳ Wartet auf Freigabe',st_queued:'Angefragt',st_downloading:'Lädt…',st_importing:'Wird verarbeitet',st_done:'✅ Verfügbar',st_error:'Fehler',st_denied:'Abgelehnt',st_exists:'vorhanden',
 settings:'Einstellungen',sec_general:'Allgemein',sec_notif:'Benachrichtigungen',sec_users:'Benutzer',sec_services:'Dienste',sec_about:'Über',app_name:'App-Name',default_lang:'Standardsprache',refresh:'Aktualisieren',version:'Version',about_txt:'Selbstgebauter Seerr-Klon für ROMs.',sec_maint:'Logs & Wartung',logs:'Protokoll',clear_cache:'Cache leeren',reindex:'Neu indexieren',clear_finished:'Fertige entfernen',done_word:'Erledigt',lbl_jobs:'Anfragen',lbl_lib:'Bibliothek',
 profile:'Profil',display_name:'Anzeigename',email:'E-Mail',language:'Sprache',avatar:'Avatar',pwebhook:'Persönlicher Discord-Webhook',change_pw:'Passwort ändern',cur_pw:'Aktuelles Passwort',new_pw:'Neues Passwort',choose_img:'Bild wählen',saved_ok:'gespeichert ✓',
 blocklist:'Sperrliste',add_btn:'Hinzufügen',pattern_ph:'Stichwort/Muster im Titel',
 nav_issues:'🐞 Probleme',issues:'Probleme',report_issue:'Problem melden',issue_msg:'Beschreibung',close_btn:'Schließen',st_open:'offen',st_closed:'geschlossen',submit:'Absenden',issue_type:'Art',comment_ph:'Kommentar schreiben …',comment_send:'Senden',push_enable:'🔔 Push aktivieren',push_disable:'🔕 Push deaktivieren',push_unsupported:'Push nicht verfügbar (HTTPS nötig)',push_denied:'Erlaubnis verweigert',push_on:'Push aktiviert ✓',push_off:'Push deaktiviert'
},en:{
 nav_discover:'🔍 Discover',nav_requests:'📥 Requests',nav_users:'👤 Users',nav_settings:'⚙️ Settings',logout:'🚪 Sign out',
 search_ph:'Search a game … (Enter)',platforms:'Platforms',all:'All',selected:'selected',
 hint_type:'Type a title and press Enter.',loading_home:'Loading home …',popular_on:'Popular on',click_search:'click to search',
 searching:'Searching …',no_results:'No results.',results:'results',in_library:'✓ in library',download:'⬇ Download',requested:'✓ requested',collection:'Collection',
 versions:'Versions / sources',files:'Files',no_desc:'No description available.',screenshots:'Screenshots',similar:'Similar games',
 no_requests:'No requests yet.',approve:'Approve',deny:'Deny',reset:'Reset all',
 users:'Users',new_user:'Create new user',create:'Create',del:'Delete',autoapprove:'Auto-approve',role_user:'User',role_admin:'Admin',username:'Username',password:'Password',
 notif_discord:'Notifications — Discord',active:'enabled',test:'Test',save:'Save',saved:'saved ✓',test_sent:'test sent ✓',webhook_ph:'Discord webhook URL',
 st_pending:'⏳ Awaiting approval',st_queued:'Requested',st_downloading:'Downloading…',st_importing:'Processing',st_done:'✅ Available',st_error:'Error',st_denied:'Denied',st_exists:'in library',
 settings:'Settings',sec_general:'General',sec_notif:'Notifications',sec_users:'Users',sec_services:'Services',sec_about:'About',app_name:'App name',default_lang:'Default language',refresh:'Refresh',version:'Version',about_txt:'Self-built Seerr clone for ROMs.',sec_maint:'Logs & maintenance',logs:'Log',clear_cache:'Clear cache',reindex:'Reindex',clear_finished:'Clear finished',done_word:'Done',lbl_jobs:'Requests',lbl_lib:'Library',
 profile:'Profile',display_name:'Display name',email:'Email',language:'Language',avatar:'Avatar',pwebhook:'Personal Discord webhook',change_pw:'Change password',cur_pw:'Current password',new_pw:'New password',choose_img:'Choose image',saved_ok:'saved ✓',
 blocklist:'Blocklist',add_btn:'Add',pattern_ph:'Keyword/pattern in title',
 nav_issues:'🐞 Issues',issues:'Issues',report_issue:'Report issue',issue_msg:'Message',close_btn:'Close',st_open:'open',st_closed:'closed',submit:'Submit',issue_type:'Type',comment_ph:'Write a comment …',comment_send:'Send',push_enable:'🔔 Enable push',push_disable:'🔕 Disable push',push_unsupported:'Push unavailable (needs HTTPS)',push_denied:'Permission denied',push_on:'Push enabled ✓',push_off:'Push disabled'
},fr:{
 nav_discover:'🔍 Découvrir',nav_requests:'📥 Demandes',nav_users:'👤 Utilisateurs',nav_settings:'⚙️ Paramètres',logout:'🚪 Déconnexion',
 search_ph:'Rechercher un jeu … (Entrée)',platforms:'Plateformes',all:'Toutes',selected:'sélectionné',
 hint_type:'Saisissez un titre et appuyez sur Entrée.',loading_home:'Chargement …',popular_on:'Populaire sur',click_search:'cliquer pour rechercher',
 searching:'Recherche …',no_results:'Aucun résultat.',results:'résultats',in_library:'✓ dans la bibliothèque',download:'⬇ Télécharger',requested:'✓ demandé',collection:'Collection',
 versions:'Versions / sources',files:'Fichiers',no_desc:'Aucune description disponible.',screenshots:'Captures',similar:'Jeux similaires',
 no_requests:'Aucune demande.',approve:'Approuver',deny:'Refuser',reset:'Tout réinitialiser',
 users:'Utilisateurs',new_user:'Créer un utilisateur',create:'Créer',del:'Supprimer',autoapprove:'Approbation auto',role_user:'Utilisateur',role_admin:'Admin',username:"Nom d'utilisateur",password:'Mot de passe',
 notif_discord:'Notifications — Discord',active:'activé',test:'Test',save:'Enregistrer',saved:'enregistré ✓',test_sent:'test envoyé ✓',webhook_ph:'URL du webhook Discord',
 st_pending:"⏳ En attente d'approbation",st_queued:'Demandé',st_downloading:'Téléchargement…',st_importing:'Traitement',st_done:'✅ Disponible',st_error:'Erreur',st_denied:'Refusé',st_exists:'présent',
 settings:'Paramètres',sec_general:'Général',sec_notif:'Notifications',sec_users:'Utilisateurs',sec_services:'Services',sec_about:'À propos',app_name:"Nom de l'app",default_lang:'Langue par défaut',refresh:'Actualiser',version:'Version',about_txt:'Clone de Seerr pour ROMs, fait maison.',sec_maint:'Journaux & maintenance',logs:'Journal',clear_cache:'Vider le cache',reindex:'Réindexer',clear_finished:'Effacer terminés',done_word:'Terminé',lbl_jobs:'Demandes',lbl_lib:'Bibliothèque',
 profile:'Profil',display_name:'Nom affiché',email:'E-mail',language:'Langue',avatar:'Avatar',pwebhook:'Webhook Discord personnel',change_pw:'Changer le mot de passe',cur_pw:'Mot de passe actuel',new_pw:'Nouveau mot de passe',choose_img:'Choisir une image',saved_ok:'enregistré ✓',
 blocklist:'Liste de blocage',add_btn:'Ajouter',pattern_ph:'Mot-clé/motif dans le titre',
 nav_issues:'🐞 Problèmes',issues:'Problèmes',report_issue:'Signaler un problème',issue_msg:'Message',close_btn:'Fermer',st_open:'ouvert',st_closed:'fermé',submit:'Envoyer',issue_type:'Type',comment_ph:'Écrire un commentaire …',comment_send:'Envoyer',push_enable:'🔔 Activer push',push_disable:'🔕 Désactiver push',push_unsupported:'Push indisponible (HTTPS requis)',push_denied:'Permission refusée',push_on:'Push activé ✓',push_off:'Push désactivé'
},es:{
 nav_discover:'🔍 Descubrir',nav_requests:'📥 Solicitudes',nav_users:'👤 Usuarios',nav_settings:'⚙️ Ajustes',logout:'🚪 Salir',
 search_ph:'Buscar un juego … (Intro)',platforms:'Plataformas',all:'Todas',selected:'seleccionado',
 hint_type:'Escribe un título y pulsa Intro.',loading_home:'Cargando …',popular_on:'Popular en',click_search:'clic para buscar',
 searching:'Buscando …',no_results:'Sin resultados.',results:'resultados',in_library:'✓ en la biblioteca',download:'⬇ Descargar',requested:'✓ solicitado',collection:'Colección',
 versions:'Versiones / fuentes',files:'Archivos',no_desc:'Sin descripción disponible.',screenshots:'Capturas',similar:'Juegos similares',
 no_requests:'Aún no hay solicitudes.',approve:'Aprobar',deny:'Rechazar',reset:'Restablecer todo',
 users:'Usuarios',new_user:'Crear usuario',create:'Crear',del:'Eliminar',autoapprove:'Auto-aprobación',role_user:'Usuario',role_admin:'Admin',username:'Usuario',password:'Contraseña',
 notif_discord:'Notificaciones — Discord',active:'activo',test:'Prueba',save:'Guardar',saved:'guardado ✓',test_sent:'prueba enviada ✓',webhook_ph:'URL del webhook de Discord',
 st_pending:'⏳ Esperando aprobación',st_queued:'Solicitado',st_downloading:'Descargando…',st_importing:'Procesando',st_done:'✅ Disponible',st_error:'Error',st_denied:'Rechazado',st_exists:'presente',
 settings:'Ajustes',sec_general:'General',sec_notif:'Notificaciones',sec_users:'Usuarios',sec_services:'Servicios',sec_about:'Acerca de',app_name:'Nombre de la app',default_lang:'Idioma predeterminado',refresh:'Actualizar',version:'Versión',about_txt:'Clon de Seerr para ROMs, hecho en casa.',sec_maint:'Registros y mantenimiento',logs:'Registro',clear_cache:'Vaciar caché',reindex:'Reindexar',clear_finished:'Borrar terminados',done_word:'Hecho',lbl_jobs:'Solicitudes',lbl_lib:'Biblioteca',
 profile:'Perfil',display_name:'Nombre visible',email:'Correo',language:'Idioma',avatar:'Avatar',pwebhook:'Webhook de Discord personal',change_pw:'Cambiar contraseña',cur_pw:'Contraseña actual',new_pw:'Nueva contraseña',choose_img:'Elegir imagen',saved_ok:'guardado ✓',
 blocklist:'Lista de bloqueo',add_btn:'Añadir',pattern_ph:'Palabra clave/patrón en el título',
 nav_issues:'🐞 Problemas',issues:'Problemas',report_issue:'Informar problema',issue_msg:'Mensaje',close_btn:'Cerrar',st_open:'abierto',st_closed:'cerrado',submit:'Enviar',issue_type:'Tipo',comment_ph:'Escribe un comentario …',comment_send:'Enviar',push_enable:'🔔 Activar push',push_disable:'🔕 Desactivar push',push_unsupported:'Push no disponible (requiere HTTPS)',push_denied:'Permiso denegado',push_on:'Push activado ✓',push_off:'Push desactivado'
}};
let LANG=localStorage.getItem('lang')||'de';
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
 document.getElementById('nS').classList.toggle('on',v=='s');
 document.getElementById('nJ').classList.toggle('on',v=='j');
 document.getElementById('nI').classList.toggle('on',v=='issues');
 document.getElementById('nSet').classList.toggle('on',v=='set');
 if(v=='j')loadJobs();if(v=='set')openSettingsView();
 if(v=='issues'){loadIssues(window._ipref);window._ipref=null;}}
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

async function search(){let q=document.getElementById('q').value.trim();if(!q){loadDiscover();return;}
 let hint=document.getElementById('hint');hint.style.display='';hint.textContent=t('searching');
 let r=await fetch('/api/search?q='+encodeURIComponent(q)+'&platforms='+[...SELP].join(','));let d=await r.json();
 window.LASTRES=d;let g=document.getElementById('grid');g.className='';g.innerHTML='';
 if(!d.length){document.getElementById('hint').textContent=t('no_results');return;}
 document.getElementById('hint').textContent=d.length+' '+t('results');
 d.forEach(it=>g.appendChild(renderCard(it)));}
async function dl(btn,it){btn.disabled=true;btn.textContent='…';
 let r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(it)});
 let d=await r.json();btn.textContent=d.ok?t('requested'):(d.msg||t('st_error'));}
// --- Detail-Ansicht (Seerr-Detailseite) ---
async function openDetail(it){let m=document.getElementById('modal');m.style.display='block';window._detit=it;
 let vars=(window.LASTRES||[]).filter(x=>x.gkey&&x.gkey===it.gkey);
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <div class=top><div class=mc style="${it.cover?`background-image:url('${it.cover}')`:''}"></div>
   <div><h2>${it.title.replace(/</g,'&lt;')}</h2>
    <div class=meta>${it.platform_slug||'?'} · ${it.source=='usenet'?'📡 Usenet':'🗄 Archive'} · ${sz(it.size)}${it.is_set?' · 📦 Sammlung':''}</div>
    <div class=meta2 id=mrich></div>
    <button onclick="reportFromDetail()" style="margin-top:8px;background:#2a2f37;border:none;color:#fff;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:12px">🐞 ${t('report_issue')}</button>
    <div class=desc id=mdesc>…</div></div></div>
  <div class=sec id=mshots style="display:none"><h3>${t('screenshots')}</h3><div class=shots id=mshotsw></div></div>
  <div class=sec><h3>${t('versions')} (${vars.length})</h3><div id=mvar></div></div>
  <div class=sec id=mfiles></div>
  <div class=sec id=msim style="display:none"><h3>${t('similar')}</h3><div class=chips id=msimw></div></div></div>`;
 let mv=document.getElementById('mvar');
 vars.forEach(v=>{let row=document.createElement('div');row.className='row';
  let s=document.createElement('span');s.textContent=`${v.source=='usenet'?'📡':'🗄'} ${sz(v.size)} · ${v.platform_slug} · ${v.title.slice(0,48)}`;
  row.appendChild(s);let b=document.createElement('button');
  if(v.in_library){b.textContent='✓ vorhanden';b.disabled=true;}else{b.textContent='⬇ Download';b.onclick=()=>dl(b,v);}
  row.appendChild(b);mv.appendChild(row);});
 let r=await fetch('/api/detail?source='+encodeURIComponent(it.source)+'&ref='+encodeURIComponent(it.ref||'')+'&title='+encodeURIComponent(it.title));
 let d=await r.json();
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
 if(d.files&&d.files.length)document.getElementById('mfiles').innerHTML='<h3>'+t('files')+'</h3><div class=flist>'+
   d.files.map(f=>`<div>${f.name.replace(/</g,'&lt;')} — ${sz(f.size)}</div>`).join('')+'</div>';}
function simSearch(n){closeModal();document.getElementById('q').value=n;show('s');search();}
function closeModal(){document.getElementById('modal').style.display='none';}
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
  sec.innerHTML=`<div class=rowh>${r.slug?t('popular_on')+' ':''}<b>${r.console}</b> <span>· ${t('click_search')}</span></div><div class=strip></div>`;
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
 j.innerHTML=d.length?'':('<div class=hint>'+t('no_requests')+'</div>');
 d.forEach(o=>{let e=document.createElement('div');e.className='job';let L=stlab(o.state);let right;
  if(o.state=='pending'&&canDo('manage_requests')){
   right=`<button onclick="approveJob('${o.id}')" style="background:#1e5e3a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer;margin-right:6px">${t('approve')}</button><button onclick="denyJob('${o.id}')" style="background:#6e2a2a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer">${t('deny')}</button>`;
  }else{right=`<span class="st ${L[1]}">${L[0]}</span>`;}
  e.innerHTML=`<div><div>${o.title.replace(/</g,'&lt;')}</div><div class=meta style="color:#8b929e;font-size:11px">👤 <b style="color:#b9c0cc">${(o.user||'—').replace(/</g,'&lt;')}</b> · ${o.platform} · ${o.source} · ${o.msg||''}</div></div><div>${right}</div>`;
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
async function loadAuth(){let d=await(await fetch('/api/auth/status')).json();
 window.ROLE=d.role;window.VERSION=d.version||'';window.PERMS=d.perms||[];
 let lang=d.user_lang||localStorage.getItem('lang')||d.default_lang||'de';
 if(lang!=LANG){LANG=lang;localStorage.setItem('lang',lang);setLang(lang);}
 let who=document.getElementById('who');
 if(d.user){let nm=(d.display_name||d.user);
   who.innerHTML=(d.avatar?`<img src="${d.avatar}">`:'👋 ')+nm.replace(/</g,'&lt;');}
 else who.textContent='';
 if(d.role=='admin')document.getElementById('nSet').style.display='';}
// --- Benutzerprofil (#23) ---
let PAV='';
async function openProfile(){let m=document.getElementById('modal');m.style.display='block';PAV='';
 let p=await(await fetch('/api/profile')).json();
 let inp='style="flex:1;min-width:120px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px"';
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <div class=sec><h3>${t('profile')} — ${(p.username||'').replace(/</g,'&lt;')}</h3>
   <div class=row><div id=pav style="width:66px;flex:0 0 66px;height:66px;border-radius:50%;background:#0b0d10 center/cover no-repeat;border:1px solid #2c323b;${p.avatar?`background-image:url('${p.avatar}')`:''}"></div>
    <label style="flex:1;font-size:12px;color:#8b929e">${t('avatar')}<br><input type=file accept="image/*" onchange="pickAvatar(event)"></label></div>
   <div class=row><input id=pdn ${inp} placeholder="${t('display_name')}" value="${(p.display_name||'').replace(/"/g,'&quot;')}"></div>
   <div class=row><input id=pmail ${inp} placeholder="${t('email')}" value="${(p.email||'').replace(/"/g,'&quot;')}"></div>
   <div class=row><label style="color:#8b929e;font-size:13px">${t('language')}</label><select id=plang ${inp}><option value="">—</option><option value=de ${p.lang=='de'?'selected':''}>Deutsch</option><option value=en ${p.lang=='en'?'selected':''}>English</option><option value=fr ${p.lang=='fr'?'selected':''}>Français</option><option value=es ${p.lang=='es'?'selected':''}>Español</option></select></div>
   <div class=row><input id=pwh ${inp} placeholder="${t('pwebhook')}" value="${(p.webhook||'').replace(/"/g,'&quot;')}"><button onclick="testPWebhook()">${t('test')}</button></div>
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
async function saveProfile(){let d={display_name:document.getElementById('pdn').value,email:document.getElementById('pmail').value,lang:document.getElementById('plang').value,webhook:document.getElementById('pwh').value};
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
 let secs=[['general',t('sec_general')],['notif',t('sec_notif')],['users',t('sec_users')],['blocklist',t('blocklist')],['services',t('sec_services')],['maint',t('sec_maint')],['about',t('sec_about')]];
 document.getElementById('settings').innerHTML='<div class=setwrap><div class=setnav>'+
  secs.map(x=>`<a class=snav data-sec="${x[0]}" onclick="setSection('${x[0]}')">${x[1]}</a>`).join('')+
  '</div><div id=setcontent></div></div>';
 setSection(SETSEC);}
function setSection(sec){SETSEC=sec;
 document.querySelectorAll('.snav').forEach(e=>e.classList.toggle('on',e.dataset.sec==sec));
 let c=document.getElementById('setcontent');
 ({general:secGeneral,notif:secNotif,users:secUsers,blocklist:secBlocklist,services:secServices,maint:secMaint,about:secAbout}[sec]||secGeneral)(c);}
async function secMaint(c){
 c.innerHTML=`<h3>${t('sec_maint')}</h3><div id=mstats class=meta>…</div>
  <div style="margin:10px 0;display:flex;gap:8px;flex-wrap:wrap">
   <button onclick="admCache()">${t('clear_cache')}</button>
   <button onclick="admReindex()">${t('reindex')}</button>
   <button onclick="admClearJobs()">${t('clear_finished')}</button>
   <button onclick="loadLogs()">${t('refresh')}</button>
   <span id=mmsg class=meta></span></div>
  <h3 style="margin-top:16px">${t('logs')}</h3><pre id=logbox class=logbox>…</pre>`;
 loadMStats();loadLogs();}
async function loadMStats(){let s=await(await fetch('/api/admin/stats')).json();
 document.getElementById('mstats').textContent=`${t('lbl_jobs')}: ${s.jobs_total} (${s.jobs_active} / ${s.jobs_finished}) · ${t('lbl_lib')}: ${s.lib_titles} (${s.lib_platforms}) · IGDB-Cache: ${s.igdb_cache}`;}
async function loadLogs(){let d=await(await fetch('/api/logs')).json();let b=document.getElementById('logbox');if(!b)return;b.textContent=(d.lines||[]).join('\\n');b.scrollTop=b.scrollHeight;}
async function admCache(){await fetch('/api/admin/cache/clear',{method:'POST'});document.getElementById('mmsg').textContent=t('done_word');loadMStats();}
async function admReindex(){await fetch('/api/admin/reindex',{method:'POST'});document.getElementById('mmsg').textContent=t('done_word');setTimeout(()=>{loadMStats();loadLogs();},1800);}
async function admClearJobs(){let r=await(await fetch('/api/jobs/clear-finished',{method:'POST'})).json();document.getElementById('mmsg').textContent=t('done_word')+' ('+(r.removed||0)+')';loadMStats();}
async function secGeneral(c){let s=await(await fetch('/api/settings')).json();let gg=s.general||{};let qo=s.quota||{};
 c.innerHTML=`<h3>${t('sec_general')}</h3>
  <div class=frow><label>${t('app_name')}</label><input id=gname value="${(gg.app_name||'Romseerr').replace(/"/g,'&quot;')}"></div>
  <div class=frow><label>${t('default_lang')}</label><select id=glang><option value=de ${(gg.default_lang||'de')=='de'?'selected':''}>Deutsch</option><option value=en ${gg.default_lang=='en'?'selected':''}>English</option><option value=fr ${gg.default_lang=='fr'?'selected':''}>Français</option><option value=es ${gg.default_lang=='es'?'selected':''}>Español</option></select></div>
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
async function saveGeneral(){let d={general:{app_name:document.getElementById('gname').value.trim(),default_lang:document.getElementById('glang').value}};
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
  <div class=frow><label style="min-width:auto"><input type=checkbox id=agwhen ${(ag.webhook||{}).enabled?'checked':''}> Webhook (Slack/Gotify/Pushover…)</label><span></span></div>
  <div class=frow><input id=agwhurl placeholder="Webhook-URL" value="${((ag.webhook||{}).url||'').replace(/"/g,'&quot;')}"><button onclick="testAgents()">${t('test')}</button></div>
  <div class=frow><button onclick="saveAgents()">${t('save')}</button><span id=agmsg class=meta></span></div>
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
  webhook:{enabled:document.getElementById('agwhen').checked,url:document.getElementById('agwhurl').value}}};
 let tok=document.getElementById('agtgtok').value;if(tok)d.agents.telegram.token=tok;
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
function secAbout(c){c.innerHTML=`<h3>Romseerr — ${t('sec_about')}</h3>
  <div class=frow><span>${t('version')}</span><span class=meta>${window.VERSION||''}</span></div>
  <p class=meta>${t('about_txt')}</p>`;}
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
applyI18n();loadAuth();loadPlatforms();loadDiscover();
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
</form>
<script>
let setup=false;
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
    return jsonify(do_search(q, plats))

@app.route("/api/platforms")
def api_platforms():
    return jsonify([{"group":g, "items":[{"slug":s,"name":n,"usenet":bool(SLUG2USE.get(s))}
                    for s,n in items]} for g,items in PLATFORMS])

@app.route("/api/detail")
def api_detail():
    source = request.args.get("source",""); ref = request.args.get("ref",""); title = request.args.get("title","")
    rich = igdb_rich(title) if title else {}
    out = {"description": rich.get("summary","") or "", "files": [],
           "rating": rich.get("rating"), "year": rich.get("year",""), "developer": rich.get("developer",""),
           "genres": rich.get("genres", []), "screenshots": rich.get("screenshots", []), "similar": rich.get("similar", [])}
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
    return jsonify(discover_rows())

@app.route("/api/download", methods=["POST"])
def api_download():
    it = request.get_json(force=True)
    if is_blocked(it.get("title","")):
        return jsonify({"ok":False,"msg":"gesperrt / blocked"})
    # Server-seitige Dedup-Sperre
    if in_library(it.get("title",""), it.get("platform")):
        return jsonify({"ok":False,"msg":"bereits in Bibliothek"})
    user = session.get("user","")
    qi = quota_info(user)
    if qi.get("enabled") and qi.get("remaining", 1) <= 0:
        return jsonify({"ok":False,"msg":"Kontingent erschöpft / quota reached"})
    auto = may_autoapprove(user)
    job = new_job(it, user=user, approved=auto)
    if not auto:
        notify_send(f"🔔 Neue Anfrage / new request: **{it.get('title','')}** von {user} — Freigabe nötig")
    return jsonify({"ok":True,"id":job["id"],"pending": not auto})

@app.route("/api/jobs")
def api_jobs():
    with JOBS_LOCK: return jsonify(list(reversed(JOBS))[:100])

@app.route("/health")
def health(): return jsonify({"ok":True,"lib_titles":len(LIB['all']),"jobs":len(JOBS)})

# ---------- Auth-Routen ----------
PUBLIC = {"/login","/api/login","/api/setup","/api/auth/status","/health","/reset","/api/forgot","/api/reset",
          "/manifest.webmanifest","/sw.js","/icon.svg","/api/openapi.json","/api/docs"}
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
    if key and key == load_settings().get("apikey"):
        g.api_auth = True; return
    u = session.get("user")
    if not u or u not in load_users():
        session.clear()
        if p.startswith("/api/"): return jsonify({"error":"auth"}), 401
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
                    "app_name": g.get("app_name","Romseerr"),
                    "version": VERSION,
                    "avatar": usr.get("avatar",""),
                    "display_name": usr.get("display_name",""),
                    "user_lang": usr.get("lang",""),
                    "perms": usr.get("perms", [])})

@app.route("/api/profile", methods=["GET"])
def api_profile_get():
    u = session.get("user"); usr = load_users().get(u, {})
    return jsonify({"username":u, "email":usr.get("email",""), "lang":usr.get("lang",""),
                    "display_name":usr.get("display_name",""), "avatar":usr.get("avatar",""),
                    "webhook":usr.get("webhook",""), "quota": quota_info(u)})

@app.route("/api/profile", methods=["POST"])
def api_profile_set():
    u = session.get("user"); users = load_users()
    if u not in users: return jsonify({"ok":False}), 404
    d = request.get_json(force=True)
    if "email" in d: users[u]["email"] = (d.get("email") or "").strip()[:120]
    if "display_name" in d: users[u]["display_name"] = (d.get("display_name") or "").strip()[:60]
    if "webhook" in d: users[u]["webhook"] = (d.get("webhook") or "").strip()[:300]
    if "lang" in d: users[u]["lang"] = "en" if d.get("lang")=="en" else ("de" if d.get("lang")=="de" else "")
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

# ---------- Admin: Logs, Statistik, Wartung ----------
JOB_FINISHED = {"done", "error", "denied"}

@app.route("/api/logs")
@admin_required
def api_logs():
    n = min(int(request.args.get("n", 200) or 200), 1000)
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
    users = load_users()
    if u in users: return jsonify({"ok":False,"msg":"Benutzer existiert bereits"}), 400
    perms = [x for x in (d.get("perms") or ["request"]) if x in PERMS]
    users[u] = {"pw":generate_password_hash(p), "role":role, "perms":perms}
    save_users(users)
    return jsonify({"ok":True})

@app.route("/api/users/<u>", methods=["PATCH"])
@perm_required("manage_users")
def api_users_patch(u):
    users = load_users()
    if u not in users: return jsonify({"ok":False}), 404
    d = request.get_json(force=True)
    if "perms" in d: users[u]["perms"] = [x for x in (d.get("perms") or []) if x in PERMS]
    if "autoapprove" in d: users[u]["autoapprove"] = bool(d["autoapprove"])
    if d.get("role") in ("admin","user"):
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
                    "general": s.get("general", {"app_name": "Romseerr", "default_lang": "de"}),
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
                        "email": {"enabled": bool(s.get("agents",{}).get("email",{}).get("enabled"))}},
                    "quota": s.get("quota", {"enabled": False, "count": 10, "days": 7})})

@app.route("/api/settings", methods=["POST"])
@admin_required
def api_settings_set():
    d = request.get_json(force=True); s = load_settings()
    if "discord" in d:
        dc = d["discord"]; s["discord"] = {"enabled": bool(dc.get("enabled")), "url": (dc.get("url") or "").strip()}
    if "general" in d:
        g = d["general"]
        s["general"] = {"app_name": (g.get("app_name") or "Romseerr")[:40],
                        "default_lang": "en" if g.get("default_lang") == "en" else "de"}
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
    if "quota" in d:
        qq = d["quota"]
        s["quota"] = {"enabled": bool(qq.get("enabled")), "count": int(qq.get("count") or 10),
                      "days": int(qq.get("days") or 7)}
    save_settings(s); return jsonify({"ok": True})

@app.route("/api/services/status")
@admin_required
def api_services_status():
    out = []
    try:
        j = requests.get(f"{SAB_URL}/api", params={"mode":"version","output":"json","apikey":SAB_APIKEY}, timeout=6).json()
        out.append({"name":"SABnzbd","ok":True,"info":"v"+str(j.get("version",""))})
    except Exception as e: out.append({"name":"SABnzbd","ok":False,"info":str(e)[:40]})
    try:
        r = requests.get(f"{PROW_URL}/api/v1/system/status", headers={"X-Api-Key":PROW_KEY}, timeout=6)
        out.append({"name":"Prowlarr","ok":r.ok,"info":"v"+str(r.json().get("version",""))})
    except Exception as e: out.append({"name":"Prowlarr","ok":False,"info":str(e)[:40]})
    try:
        r = requests.get(f"{ROMM_URL}/api/heartbeat", timeout=6)
        out.append({"name":"RomM","ok":r.ok,"info":"erreichbar"})
    except Exception as e: out.append({"name":"RomM","ok":False,"info":str(e)[:40]})
    out.append({"name":"IGDB","ok":bool(igdb_token()),"info":"Cover / Discover"})
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
        "/api/jobs/{jid}/approve": {"post": _op("Anfrage freigeben", "Requests",
            params=[_pp("jid", "Job-ID")], responses={**_R_PERM, "200": {"description": "OK"}})},
        "/api/jobs/{jid}/deny": {"post": _op("Anfrage ablehnen", "Requests",
            params=[_pp("jid", "Job-ID")], responses={**_R_PERM, "200": {"description": "OK"}})},
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
        # --- Profile ---
        "/api/profile": {
            "get": _op("Eigenes Profil", "Profile"),
            "post": _op("Profil ändern (Name, E-Mail, Sprache, Avatar, persönl. Webhook)", "Profile",
                body={"type": "object", "properties": {
                    "display_name": {"type": "string"}, "email": {"type": "string"},
                    "lang": {"type": "string", "enum": ["de", "en", "fr", "es"]},
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
        time.sleep(600); build_index()

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
    log(f"rom-suche startet auf :{PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)  # nosec B104 - Container-Dienst, bindet bewusst alle Interfaces
