#!/usr/bin/env python3
# rom-suche — Seerr-artige ROM-Suche & Auto-Download (Archive.org + Usenet/SAB), Dedup gegen Bibliothek.
import os, re, json, time, threading, queue, subprocess, urllib.parse, html, secrets, smtplib
from datetime import datetime
from functools import wraps
from email.message import EmailMessage
import requests
from flask import Flask, request, jsonify, Response, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash

# ---------- Konfiguration ----------
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

ROMS       = "/roms"
SAB_DONE   = "/sab-complete"
JD_WATCH   = "/jd-watch"
JD_OUT     = "/jd-output/rom-suche"           # Sicht der rom-suche (=/mnt/user/Downloads/rom-suche)
JD_DL_BASE = os.environ.get("JD_DL_BASE","/output/rom-suche")  # Sicht des JD-Containers
STAGING    = "/config/staging"
JOBDB      = "/config/jobs.json"
LOGFILE    = "/config/rom-suche.log"
USERS_FILE = "/config/users.json"
SECRET_FILE= "/config/secret.key"
SETTINGS_FILE = "/config/settings.json"

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
REGION_RE = re.compile(r'\b(usa|eur|europe|japan|jpn|world|korea|kor|rev\s*\d+|proper|repack|'
    r'nsw|xci|nsp|disc\s*\d+|snes|smc|sfc|nes|n64|z64|gba|gbc|\bgb\b|megadrive|genesis|'
    r'\bmd\b|psx|ps1|ps2|psp|switch|wii|gamecube|ngc|arcade|mame)\b')
def norm(name):
    s = os.path.splitext(name)[0].lower()
    s = re.sub(r'[\._\-+]+', ' ', s)                          # Trenner ZUERST zu Space
    s = re.sub(r'\([^)]*\)|\[[^\]]*\]|\{[^}]*\}', ' ', s)     # (USA), [!], {...}
    s = re.sub(r'\bv?\d+(\.\d+)+\b', ' ', s)                   # v1.2.3
    s = REGION_RE.sub(' ', s)                                  # Region/Plattform-Tokens
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

LIB = {"per": {}, "all": set(), "slugs": set(), "ts": 0}
LIB_LOCK = threading.Lock()

def build_index():
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
    with LIB_LOCK:
        LIB["per"], LIB["all"], LIB["slugs"], LIB["ts"] = per, allset, slugs, time.time()
    log(f"Bibliotheks-Index: {len(slugs)} Plattformen, {len(allset)} Titel")

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

DISCOVER_CACHE = {"ts": 0, "rows": []}
def discover_rows():
    if time.time()-DISCOVER_CACHE["ts"] < 3600 and DISCOVER_CACHE["rows"]:
        rows = DISCOVER_CACHE["rows"]
    else:
        rows = []
        for slug in DISCOVER_ORDER:
            pid = IGDB_PLAT.get(slug)
            games = igdb_popular_platform(pid, 20) if pid else []
            if games:
                rows.append({"slug": slug, "console": SLUG_NAME.get(slug, slug), "games": games})
        DISCOVER_CACHE["rows"], DISCOVER_CACHE["ts"] = rows, time.time()
    # Bibliotheks-Markierung je Spiel frisch (nicht cachen)
    return [{"slug": r["slug"], "console": r["console"],
             "games": [{**g, "in_library": in_library(g["title"], r["slug"])} for g in r["games"]]}
            for r in rows]

def notify_send(text):
    s = load_settings().get("discord", {})
    wh = s.get("url") if s.get("enabled") else os.environ.get("DISCORD_WEBHOOK", "")
    if not wh: return False
    try:
        requests.post(wh, json={"content": text}, timeout=8); return True
    except Exception as e:
        log(f"Notify-Fehler: {e}"); return False

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

def do_search(q, platforms=None):
    platforms = [p for p in (platforms or []) if p]
    # Usenet breit über Console (1000) abfragen und danach nach Plattform filtern —
    # Indexer taggen vieles nur unter der Oberkategorie. Retro-only-Auswahl -> Usenet aus.
    if platforms:
        usenet_cats = PROW_CATS if any(SLUG2USE.get(p) for p in platforms) else ""
    else:
        usenet_cats = PROW_CATS
    res = []
    ar = search_archive(q); us = search_usenet(q, usenet_cats)
    for idx, r in enumerate(ar+us):
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
JOBS = []           # Liste dicts
JOBS_LOCK = threading.Lock()
Q = queue.Queue()

def load_jobs():
    global JOBS
    try:
        with open(JOBDB) as f: JOBS = json.load(f)
    except Exception: JOBS = []
def save_jobs():
    try:
        with open(JOBDB,"w") as f: json.dump(JOBS, f, ensure_ascii=False, indent=1)
    except Exception as e: log(f"Job-Speichern-Fehler: {e}")
def set_state(jid, **kw):
    with JOBS_LOCK:
        for j in JOBS:
            if j["id"]==jid: j.update(kw); j["updated"]=datetime.now().strftime("%H:%M:%S")
        save_jobs()

def new_job(item, user="", approved=True):
    jid = f"{int(time.time())}{len(JOBS)%1000:03d}"
    job = {"id":jid,"title":item["title"],"source":item["source"],"ref":item["ref"],
           "platform":item.get("platform_slug") or "Mixed","size":item.get("size",0),
           "user":user,"state":"queued" if approved else "pending",
           "updated":datetime.now().strftime("%H:%M:%S"),"msg":"" if approved else "wartet auf Freigabe"}
    with JOBS_LOCK: JOBS.append(job); save_jobs()
    if approved: Q.put(jid)
    return job

def get_job(jid):
    with JOBS_LOCK:
        for j in JOBS:
            if j["id"]==jid: return dict(j)
    return None

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
        wh = load_users().get(job.get("user",""), {}).get("webhook","")
        if wh:
            try: requests.post(wh, json={"content": f"🎮 **{job.get('title','')}** ist jetzt verfügbar / now available ({where})"}, timeout=8)
            except Exception as e: log(f"Personal-Notify-Fehler: {e}")

# ---------- Worker: fertige SAB/JD-Downloads einsortieren ----------
def romm_scan():
    if not (ROMM_URL and ROMM_USER and ROMM_PASS): return
    try:
        s = requests.Session()
        s.post(f"{ROMM_URL}/api/login", auth=(ROMM_USER,ROMM_PASS), timeout=10)
        s.post(f"{ROMM_URL}/api/scan", json={"platforms":[], "type":"quick"}, timeout=10)
    except Exception as e:
        log(f"RomM-Scan-Hinweis: {e}")

def worker_collect():
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
    try:
        a = sum(f.stat().st_size for f in os.scandir(path) if f.is_file())
        time.sleep(wait)
        b = sum(f.stat().st_size for f in os.scandir(path) if f.is_file())
        return a==b
    except Exception: return False

# ---------- Benutzerverwaltung / Auth ----------
def load_users():
    try:
        with open(USERS_FILE) as f: return json.load(f)
    except Exception: return {}
def save_users(u):
    with open(USERS_FILE, "w") as f: json.dump(u, f)
def load_settings():
    try:
        with open(SETTINGS_FILE) as f: return json.load(f)
    except Exception: return {}
def save_settings(s):
    with open(SETTINGS_FILE, "w") as f: json.dump(s, f)
def may_autoapprove(username):
    usr = load_users().get(username, {})
    return usr.get("role") == "admin" or bool(usr.get("autoapprove"))

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
        srv.send_message(msg); srv.quit(); return True
    except Exception as e:
        log(f"Mail-Fehler: {e}"); return False

RESET_TOKENS = {}
def gen_reset(user):
    tok = secrets.token_urlsafe(24); RESET_TOKENS[tok] = {"user": user, "exp": time.time()+3600}; return tok
def check_reset(tok):
    d = RESET_TOKENS.get(tok)
    return d["user"] if d and d["exp"] > time.time() else None
def app_secret():
    try: return open(SECRET_FILE).read().strip()
    except Exception:
        s = secrets.token_hex(32)
        try: open(SECRET_FILE, "w").write(s)
        except Exception: pass
        return s
def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("user"):
            if request.path.startswith("/api/"): return jsonify({"error": "auth"}), 401
            return redirect("/login")
        return f(*a, **k)
    return w
def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        if session.get("role") != "admin": return jsonify({"error": "admin"}), 403
        return f(*a, **k)
    return w

# ---------- Web-UI ----------
app = Flask(__name__)
app.secret_key = app_secret()
app.config["PERMANENT_SESSION_LIFETIME"] = 60*60*24*30

PAGE = """<!doctype html><html lang=de><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Romseerr</title>
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
 <a class=nav id=nSet data-i18n=nav_settings onclick="show('set')" style="display:none">⚙️ Einstellungen</a>
 <div class=grow></div>
 <div id=langsw><b data-l=de class=on onclick="setLang('de')">DE</b><b data-l=en onclick="setLang('en')">EN</b></div>
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
</main>
<div id=modal></div>
<script>
const I18N={de:{
 nav_discover:'🔍 Entdecken',nav_requests:'📥 Anfragen',nav_users:'👤 Benutzer',nav_settings:'⚙️ Einstellungen',logout:'🚪 Abmelden',
 search_ph:'Spiel suchen … (Enter)',platforms:'Plattformen',all:'Alle',selected:'gewählt',
 hint_type:'Tippe einen Titel und drücke Enter.',loading_home:'Lade Startseite …',popular_on:'Beliebt auf',click_search:'klick zum Suchen',
 searching:'Suche läuft …',no_results:'Keine Treffer.',results:'Treffer',in_library:'✓ in Bibliothek',download:'⬇ Download',requested:'✓ angefragt',collection:'Sammlung',
 versions:'Versionen / Quellen',files:'Dateien',no_desc:'Keine Beschreibung verfügbar.',
 no_requests:'Noch keine Anfragen.',approve:'Freigeben',deny:'Ablehnen',reset:'Alle zurücksetzen',
 users:'Benutzer',new_user:'Neuen Benutzer anlegen',create:'Anlegen',del:'Löschen',autoapprove:'Auto-Freigabe',role_user:'Nutzer',role_admin:'Admin',username:'Benutzername',password:'Passwort',
 notif_discord:'Benachrichtigungen — Discord',active:'aktiv',test:'Test',save:'Speichern',saved:'gespeichert ✓',test_sent:'Test gesendet ✓',webhook_ph:'Discord Webhook-URL',
 st_pending:'⏳ Wartet auf Freigabe',st_queued:'Angefragt',st_downloading:'Lädt…',st_importing:'Wird verarbeitet',st_done:'✅ Verfügbar',st_error:'Fehler',st_denied:'Abgelehnt',st_exists:'vorhanden',
 settings:'Einstellungen',sec_general:'Allgemein',sec_notif:'Benachrichtigungen',sec_users:'Benutzer',sec_services:'Dienste',sec_about:'Über',app_name:'App-Name',default_lang:'Standardsprache',refresh:'Aktualisieren',version:'Version',about_txt:'Selbstgebauter Seerr-Klon für ROMs.',
 profile:'Profil',display_name:'Anzeigename',email:'E-Mail',language:'Sprache',avatar:'Avatar',pwebhook:'Persönlicher Discord-Webhook',change_pw:'Passwort ändern',cur_pw:'Aktuelles Passwort',new_pw:'Neues Passwort',choose_img:'Bild wählen',saved_ok:'gespeichert ✓'
},en:{
 nav_discover:'🔍 Discover',nav_requests:'📥 Requests',nav_users:'👤 Users',nav_settings:'⚙️ Settings',logout:'🚪 Sign out',
 search_ph:'Search a game … (Enter)',platforms:'Platforms',all:'All',selected:'selected',
 hint_type:'Type a title and press Enter.',loading_home:'Loading home …',popular_on:'Popular on',click_search:'click to search',
 searching:'Searching …',no_results:'No results.',results:'results',in_library:'✓ in library',download:'⬇ Download',requested:'✓ requested',collection:'Collection',
 versions:'Versions / sources',files:'Files',no_desc:'No description available.',
 no_requests:'No requests yet.',approve:'Approve',deny:'Deny',reset:'Reset all',
 users:'Users',new_user:'Create new user',create:'Create',del:'Delete',autoapprove:'Auto-approve',role_user:'User',role_admin:'Admin',username:'Username',password:'Password',
 notif_discord:'Notifications — Discord',active:'enabled',test:'Test',save:'Save',saved:'saved ✓',test_sent:'test sent ✓',webhook_ph:'Discord webhook URL',
 st_pending:'⏳ Awaiting approval',st_queued:'Requested',st_downloading:'Downloading…',st_importing:'Processing',st_done:'✅ Available',st_error:'Error',st_denied:'Denied',st_exists:'in library',
 settings:'Settings',sec_general:'General',sec_notif:'Notifications',sec_users:'Users',sec_services:'Services',sec_about:'About',app_name:'App name',default_lang:'Default language',refresh:'Refresh',version:'Version',about_txt:'Self-built Seerr clone for ROMs.',
 profile:'Profile',display_name:'Display name',email:'Email',language:'Language',avatar:'Avatar',pwebhook:'Personal Discord webhook',change_pw:'Change password',cur_pw:'Current password',new_pw:'New password',choose_img:'Choose image',saved_ok:'saved ✓'
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
 document.getElementById('nS').classList.toggle('on',v=='s');
 document.getElementById('nJ').classList.toggle('on',v=='j');
 document.getElementById('nSet').classList.toggle('on',v=='set');
 if(v=='j')loadJobs();if(v=='set')openSettingsView();}
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
async function openDetail(it){let m=document.getElementById('modal');m.style.display='block';
 let vars=(window.LASTRES||[]).filter(x=>x.gkey&&x.gkey===it.gkey);
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <div class=top><div class=mc style="${it.cover?`background-image:url('${it.cover}')`:''}"></div>
   <div><h2>${it.title.replace(/</g,'&lt;')}</h2>
    <div class=meta>${it.platform_slug||'?'} · ${it.source=='usenet'?'📡 Usenet':'🗄 Archive'} · ${sz(it.size)}${it.is_set?' · 📦 Sammlung':''}</div>
    <div class=desc id=mdesc>…</div></div></div>
  <div class=sec><h3>${t('versions')} (${vars.length})</h3><div id=mvar></div></div>
  <div class=sec id=mfiles></div></div>`;
 let mv=document.getElementById('mvar');
 vars.forEach(v=>{let row=document.createElement('div');row.className='row';
  let s=document.createElement('span');s.textContent=`${v.source=='usenet'?'📡':'🗄'} ${sz(v.size)} · ${v.platform_slug} · ${v.title.slice(0,48)}`;
  row.appendChild(s);let b=document.createElement('button');
  if(v.in_library){b.textContent='✓ vorhanden';b.disabled=true;}else{b.textContent='⬇ Download';b.onclick=()=>dl(b,v);}
  row.appendChild(b);mv.appendChild(row);});
 let r=await fetch('/api/detail?source='+encodeURIComponent(it.source)+'&ref='+encodeURIComponent(it.ref||'')+'&title='+encodeURIComponent(it.title));
 let d=await r.json();
 document.getElementById('mdesc').textContent=d.description||t('no_desc');
 if(d.files&&d.files.length)document.getElementById('mfiles').innerHTML='<h3>'+t('files')+'</h3><div class=flist>'+
   d.files.map(f=>`<div>${f.name.replace(/</g,'&lt;')} — ${sz(f.size)}</div>`).join('')+'</div>';}
function closeModal(){document.getElementById('modal').style.display='none';}
// --- Discover / Startseite: beliebte Spiele je Konsole ---
async function loadDiscover(){let hint=document.getElementById('hint');hint.style.display='';hint.textContent=t('loading_home');
 let g=document.getElementById('grid');
 let rows=await(await fetch('/api/discover/rows')).json();
 if(!rows.length){hint.textContent=t('hint_type');g.className='';g.innerHTML='';return;}
 hint.style.display='none';g.className='disc';g.innerHTML='';
 rows.forEach(r=>{let sec=document.createElement('div');sec.className='drow';
  sec.innerHTML=`<div class=rowh>${t('popular_on')} <b>${r.console}</b> <span>· ${t('click_search')}</span></div><div class=strip></div>`;
  let strip=sec.querySelector('.strip');
  r.games.forEach(it=>{let c=document.createElement('div');c.className='pcard';
   c.innerHTML=`<div class=pcover style="${it.cover?`background-image:url('${it.cover}')`:''}">${it.in_library?'<span class=have2>✓</span>':''}</div><div class=pt>${it.title.replace(/</g,'&lt;')}</div>`;
   c.onclick=()=>{SELP=new Set([r.slug]);localStorage.setItem('romp',JSON.stringify([r.slug]));updateFLabel();
    document.querySelectorAll('.chip').forEach(e=>e.classList.toggle('on',e.dataset.s==r.slug));
    document.getElementById('q').value=it.title;search();};
   strip.appendChild(c);});
  g.appendChild(sec);});}
const STCLS={downloading:'downloading',importing:'importing',done:'done',error:'error',denied:'error'};
function stlab(s){return [t('st_'+s)||s, STCLS[s]||''];}
async function loadJobs(){let r=await fetch('/api/jobs');let d=await r.json();let j=document.getElementById('jobs');
 j.innerHTML=d.length?'':('<div class=hint>'+t('no_requests')+'</div>');
 d.forEach(o=>{let e=document.createElement('div');e.className='job';let L=stlab(o.state);let right;
  if(o.state=='pending'&&window.ROLE=='admin'){
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
async function loadAuth(){let d=await(await fetch('/api/auth/status')).json();
 window.ROLE=d.role;window.VERSION=d.version||'';
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
   <div class=row><label style="color:#8b929e;font-size:13px">${t('language')}</label><select id=plang ${inp}><option value="">—</option><option value=de ${p.lang=='de'?'selected':''}>Deutsch</option><option value=en ${p.lang=='en'?'selected':''}>English</option></select></div>
   <div class=row><input id=pwh ${inp} placeholder="${t('pwebhook')}" value="${(p.webhook||'').replace(/"/g,'&quot;')}"><button onclick="testPWebhook()">${t('test')}</button></div>
   <div class=row><button onclick="saveProfile()">${t('save')}</button><span id=pmsg class=meta></span></div></div>
  <div class=sec><h3>${t('change_pw')}</h3>
   <div class=row><input id=pold type=password ${inp} placeholder="${t('cur_pw')}"><input id=pnew type=password ${inp} placeholder="${t('new_pw')}"></div>
   <div class=row><button onclick="changePw()">${t('change_pw')}</button><span id=pwmsg class=meta></span></div></div></div>`;}
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
 let secs=[['general',t('sec_general')],['notif',t('sec_notif')],['users',t('sec_users')],['services',t('sec_services')],['about',t('sec_about')]];
 document.getElementById('settings').innerHTML='<div class=setwrap><div class=setnav>'+
  secs.map(x=>`<a class=snav data-sec="${x[0]}" onclick="setSection('${x[0]}')">${x[1]}</a>`).join('')+
  '</div><div id=setcontent></div></div>';
 setSection(SETSEC);}
function setSection(sec){SETSEC=sec;
 document.querySelectorAll('.snav').forEach(e=>e.classList.toggle('on',e.dataset.sec==sec));
 let c=document.getElementById('setcontent');
 ({general:secGeneral,notif:secNotif,users:secUsers,services:secServices,about:secAbout}[sec]||secGeneral)(c);}
async function secGeneral(c){let g=(await(await fetch('/api/settings')).json()).general||{};
 c.innerHTML=`<h3>${t('sec_general')}</h3>
  <div class=frow><label>${t('app_name')}</label><input id=gname value="${(g.app_name||'Romseerr').replace(/"/g,'&quot;')}"></div>
  <div class=frow><label>${t('default_lang')}</label><select id=glang><option value=de ${g.default_lang!='en'?'selected':''}>Deutsch</option><option value=en ${g.default_lang=='en'?'selected':''}>English</option></select></div>
  <button onclick="saveGeneral()">${t('save')}</button> <span id=gmsg class=meta></span>`;}
async function saveGeneral(){let d={general:{app_name:document.getElementById('gname').value.trim(),default_lang:document.getElementById('glang').value}};
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('gmsg').textContent=r.ok?t('saved'):t('st_error');}
async function secNotif(c){let s=await(await fetch('/api/settings')).json();let dc=s.discord||{};let sm=s.smtp||{};
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
  <div class=frow><button onclick="saveSmtp()">${t('save')}</button><span id=smmsg class=meta></span></div>`;}
async function saveSmtp(){let d={smtp:{enabled:document.getElementById('smen').checked,host:document.getElementById('smhost').value,port:document.getElementById('smport').value,user:document.getElementById('smuser').value,from:document.getElementById('smfrom').value,tls:document.getElementById('smtls').value}};
 let pw=document.getElementById('smpass').value;if(pw)d.smtp.pass=pw;
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('smmsg').textContent=r.ok?t('saved_ok'):t('st_error');return r.ok;}
async function mailTest(){let to=document.getElementById('smto').value.trim();if(!to)return;await saveSmtp();
 let r=await(await fetch('/api/settings/mail-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:to})})).json();
 document.getElementById('smmsg').textContent=r.ok?t('test_sent'):(r.msg||t('st_error'));}
async function secUsers(c){let list=await(await fetch('/api/users')).json();
 c.innerHTML=`<h3>${t('users')}</h3><div id=ulist></div>
  <h3 style="margin-top:18px">${t('new_user')}</h3>
  <div class=frow><input id=nu placeholder="${t('username')}"><input id=np type=password placeholder="${t('password')}">
   <select id=nr><option value=user>${t('role_user')}</option><option value=admin>${t('role_admin')}</option></select>
   <label style="min-width:auto;flex:0 0 auto"><input type=checkbox id=naa> ${t('autoapprove')}</label><button onclick="addUser()">${t('create')}</button></div>
  <div id=uerr class=meta style="color:#ff6b6b"></div>`;
 renderUsers(list);}
async function secServices(c){c.innerHTML=`<h3>${t('sec_services')}</h3><button onclick="setSection('services')">${t('refresh')}</button><div id=svc style="margin-top:12px">…</div>`;
 let list=await(await fetch('/api/services/status')).json();
 document.getElementById('svc').innerHTML=list.map(s=>`<div class=frow><span>${s.ok?'🟢':'🔴'} <b>${s.name}</b></span><span class=meta>${(''+ (s.info||'')).replace(/</g,'&lt;')}</span></div>`).join('');}
function secAbout(c){c.innerHTML=`<h3>Romseerr — ${t('sec_about')}</h3>
  <div class=frow><span>${t('version')}</span><span class=meta>${window.VERSION||''}</span></div>
  <p class=meta>${t('about_txt')}</p>`;}
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
function renderUsers(list){let ul=document.getElementById('ulist');ul.innerHTML='';
 list.forEach(u=>{let row=document.createElement('div');row.className='row';
  let s=document.createElement('span');s.textContent=(u.role=='admin'?'👑 ':'👤 ')+u.username;row.appendChild(s);
  let right=document.createElement('div');right.style.cssText='display:flex;gap:10px;align-items:center';
  let lbl=document.createElement('label');lbl.style.cssText='font-size:12px;color:#8b929e;display:flex;gap:5px;align-items:center';
  let cb=document.createElement('input');cb.type='checkbox';cb.checked=u.autoapprove;cb.disabled=(u.role=='admin');
  cb.onchange=()=>fetch('/api/users/'+encodeURIComponent(u.username),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({autoapprove:cb.checked})});
  lbl.appendChild(cb);lbl.appendChild(document.createTextNode(t('autoapprove')));right.appendChild(lbl);
  let b=document.createElement('button');b.textContent=t('del');
  b.onclick=async()=>{let d=await(await fetch('/api/users/'+encodeURIComponent(u.username),{method:'DELETE'})).json();
   if(d.ok)setSection('users');else alert(d.msg||'Fehler');};
  right.appendChild(b);row.appendChild(right);ul.appendChild(row);});}
async function addUser(){let u=document.getElementById('nu').value.trim(),p=document.getElementById('np').value,r=document.getElementById('nr').value,aa=document.getElementById('naa').checked;
 let d=await(await fetch('/api/users',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({username:u,password:p,role:r,autoapprove:aa})})).json();
 if(d.ok)setSection('users');else document.getElementById('uerr').textContent=d.msg||'Fehler';}
async function logout(){await fetch('/api/logout',{method:'POST'});location.href='/login';}
document.querySelectorAll('#langsw b').forEach(e=>e.classList.toggle('on',e.dataset.l==LANG));
applyI18n();loadAuth();loadPlatforms();loadDiscover();
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
    out = {"description": igdb_desc(title) if title else "", "files": []}
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
    # Server-seitige Dedup-Sperre
    if in_library(it.get("title",""), it.get("platform")):
        return jsonify({"ok":False,"msg":"bereits in Bibliothek"})
    user = session.get("user","")
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
PUBLIC = {"/login","/api/login","/api/setup","/api/auth/status","/health","/reset","/api/forgot","/api/reset"}
@app.before_request
def _guard():
    p = request.path
    if p in PUBLIC: return
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
                    "user_lang": usr.get("lang","")})

@app.route("/api/profile", methods=["GET"])
def api_profile_get():
    u = session.get("user"); usr = load_users().get(u, {})
    return jsonify({"username":u, "email":usr.get("email",""), "lang":usr.get("lang",""),
                    "display_name":usr.get("display_name",""), "avatar":usr.get("avatar",""),
                    "webhook":usr.get("webhook","")})

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
    users = load_users(); match = None
    for un, uv in users.items():
        if un.lower() == q or (q and uv.get("email","").lower() == q): match = un; break
    if match and users[match].get("email") and load_settings().get("smtp", {}).get("enabled"):
        tok = gen_reset(match); base = request.host_url.rstrip("/")
        send_mail(users[match]["email"], "Romseerr — Passwort zurücksetzen / password reset",
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

@app.route("/api/setup", methods=["POST"])
def api_setup():
    if load_users(): return jsonify({"ok":False,"msg":"bereits eingerichtet"}), 400
    d = request.get_json(force=True); u=(d.get("username") or "").strip(); p=d.get("password") or ""
    if not u or len(p)<6: return jsonify({"ok":False,"msg":"Benutzername + Passwort (min. 6 Zeichen)"}), 400
    save_users({u: {"pw":generate_password_hash(p), "role":"admin"}})
    session.permanent=True; session["user"]=u; session["role"]="admin"
    return jsonify({"ok":True})

@app.route("/api/login", methods=["POST"])
def api_login():
    d = request.get_json(force=True); u=(d.get("username") or "").strip(); p=d.get("password") or ""
    usr = load_users().get(u)
    if usr and check_password_hash(usr["pw"], p):
        session.permanent=True; session["user"]=u; session["role"]=usr.get("role","user")
        return jsonify({"ok":True,"role":session["role"]})
    return jsonify({"ok":False,"msg":"Falsche Zugangsdaten"}), 401

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear(); return jsonify({"ok":True})

@app.route("/api/users", methods=["GET"])
@admin_required
def api_users_list():
    return jsonify([{"username":u,"role":v.get("role","user"),"autoapprove":bool(v.get("autoapprove"))}
                    for u,v in load_users().items()])

@app.route("/api/users", methods=["POST"])
@admin_required
def api_users_add():
    d = request.get_json(force=True); u=(d.get("username") or "").strip(); p=d.get("password") or ""
    role = "admin" if d.get("role")=="admin" else "user"
    if not u or len(p)<6: return jsonify({"ok":False,"msg":"Benutzername + Passwort (min. 6 Zeichen)"}), 400
    users = load_users()
    if u in users: return jsonify({"ok":False,"msg":"Benutzer existiert bereits"}), 400
    users[u] = {"pw":generate_password_hash(p), "role":role, "autoapprove":bool(d.get("autoapprove"))}
    save_users(users)
    return jsonify({"ok":True})

@app.route("/api/users/<u>", methods=["PATCH"])
@admin_required
def api_users_patch(u):
    users = load_users()
    if u not in users: return jsonify({"ok":False}), 404
    d = request.get_json(force=True)
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
                             "has_pass": bool(sm.get("pass"))}})

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
@admin_required
def api_job_approve(jid):
    j = get_job(jid)
    if not j or j.get("state") != "pending": return jsonify({"ok": False}), 400
    set_state(jid, state="queued", msg="freigegeben"); Q.put(jid)
    return jsonify({"ok": True})

@app.route("/api/jobs/<jid>/deny", methods=["POST"])
@admin_required
def api_job_deny(jid):
    if not get_job(jid): return jsonify({"ok": False}), 404
    set_state(jid, state="denied", msg="abgelehnt")
    return jsonify({"ok": True})

@app.route("/api/users/<u>", methods=["DELETE"])
@admin_required
def api_users_del(u):
    users = load_users()
    if u not in users: return jsonify({"ok":False,"msg":"unbekannt"}), 404
    if u == session.get("user"): return jsonify({"ok":False,"msg":"nicht sich selbst"}), 400
    admins = [x for x,v in users.items() if v.get("role")=="admin"]
    if users[u].get("role")=="admin" and len(admins)<=1:
        return jsonify({"ok":False,"msg":"letzter Admin"}), 400
    users.pop(u,None); save_users(users); return jsonify({"ok":True})

# ---------- Start ----------
def periodic_index():
    while True:
        time.sleep(600); build_index()

if __name__ == "__main__":
    os.makedirs(STAGING, exist_ok=True)
    load_jobs(); build_index()
    threading.Thread(target=worker_download, daemon=True).start()
    threading.Thread(target=worker_collect, daemon=True).start()
    threading.Thread(target=periodic_index, daemon=True).start()
    log(f"rom-suche startet auf :{PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
