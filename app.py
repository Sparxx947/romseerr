#!/usr/bin/env python3
# rom-suche — Seerr-artige ROM-Suche & Auto-Download (Archive.org + Usenet/SAB), Dedup gegen Bibliothek.
import os, re, json, time, threading, queue, subprocess, urllib.parse, html
from datetime import datetime
import requests
from flask import Flask, request, jsonify, Response

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

ROMS       = "/roms"
SAB_DONE   = "/sab-complete"
JD_WATCH   = "/jd-watch"
JD_OUT     = "/jd-output/rom-suche"           # Sicht der rom-suche (=/mnt/user/Downloads/rom-suche)
JD_DL_BASE = os.environ.get("JD_DL_BASE","/output/rom-suche")  # Sicht des JD-Containers
STAGING    = "/config/staging"
JOBDB      = "/config/jobs.json"
LOGFILE    = "/config/rom-suche.log"

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

# ---------- IGDB Cover (optional, best effort) ----------
IGDB = {"token": "", "exp": 0, "cache": {}}
def igdb_cover(title):
    if not (IGDB_ID and IGDB_SECRET): return ""
    key = norm(title)
    if key in IGDB["cache"]: return IGDB["cache"][key]
    try:
        if time.time() > IGDB["exp"]:
            r = requests.post("https://id.twitch.tv/oauth2/token", params={
                "client_id": IGDB_ID, "client_secret": IGDB_SECRET,
                "grant_type": "client_credentials"}, timeout=8)
            j = r.json(); IGDB["token"] = j["access_token"]; IGDB["exp"] = time.time()+j.get("expires_in",3600)-60
        h = {"Client-ID": IGDB_ID, "Authorization": f"Bearer {IGDB['token']}"}
        q = f'search "{title[:60]}"; fields cover.image_id; limit 1;'
        r = requests.post("https://api.igdb.com/v4/games", headers=h, data=q, timeout=8)
        d = r.json()
        url = ""
        if d and d[0].get("cover"):
            url = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{d[0]['cover']['image_id']}.jpg"
        IGDB["cache"][key] = url
        return url
    except Exception:
        return ""

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

def search_usenet(q, limit=30):
    out = []
    if not (PROW_URL and PROW_KEY): return out
    try:
        u = f"{PROW_URL}/api/v1/search"
        r = requests.get(u, params={"query":q,"categories":PROW_CATS,"type":"search","limit":limit},
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

def do_search(q):
    res = []
    ar = search_archive(q); us = search_usenet(q)
    for idx, r in enumerate(ar+us):
        r["platform_slug"] = resolve_slug(r["platform"])
        r["in_library"] = in_library(r["title"], r["platform"])
        r["is_set"] = is_set(r["title"], r["size"])
        r["_rank"] = idx
        if not r["cover"] and r["source"]=="usenet":
            r["cover"] = igdb_cover(re.sub(r'[\._]', ' ', r["title"]))
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

def new_job(item):
    jid = f"{int(time.time())}{len(JOBS)%1000:03d}"
    job = {"id":jid,"title":item["title"],"source":item["source"],"ref":item["ref"],
           "platform":item.get("platform_slug") or "Mixed","size":item.get("size",0),
           "state":"queued","updated":datetime.now().strftime("%H:%M:%S"),"msg":""}
    with JOBS_LOCK: JOBS.append(job); save_jobs()
    Q.put(jid)
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

# ---------- Web-UI ----------
app = Flask(__name__)

PAGE = """<!doctype html><html lang=de><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>rom-suche</title>
<style>
:root{--bg:#14161a;--card:#1e2229;--acc:#7c5cff;--ok:#2ecc71;--txt:#e6e8ec;--mut:#8b929e}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:var(--bg);color:var(--txt)}
header{position:sticky;top:0;background:#0f1114;padding:14px 18px;display:flex;gap:12px;align-items:center;border-bottom:1px solid #262b33;z-index:5}
h1{font-size:18px;margin:0;color:var(--acc)}
input{flex:1;padding:11px 14px;border-radius:10px;border:1px solid #2c323b;background:#0b0d10;color:var(--txt);font-size:15px}
button.tab{background:none;border:none;color:var(--mut);font-size:14px;cursor:pointer;padding:8px}
button.tab.on{color:var(--txt);border-bottom:2px solid var(--acc)}
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
.job{background:var(--card);border:1px solid #262b33;border-radius:10px;padding:10px 12px;margin-bottom:8px;display:flex;justify-content:space-between;gap:10px}
.st{font-size:12px;padding:2px 8px;border-radius:6px;background:#2a2f37}
.st.done{background:#1e5e3a}.st.error{background:#6e2a2a}.st.downloading,.st.importing{background:#5a4a1e}
.hint{color:var(--mut);padding:0 18px 18px;font-size:12px}
</style></head><body>
<header><h1>🎮 rom-suche</h1>
<input id=q placeholder="Spiel suchen … (Enter)" autofocus>
<button class="tab on" id=tS onclick="show('s')">Suche</button>
<button class="tab" id=tJ onclick="show('j')">Downloads</button></header>
<div id=grid></div><div class=hint id=hint>Tippe einen Titel und drücke Enter.</div>
<div id=jobs></div>
<script>
let cur='s';
function show(v){cur=v;document.getElementById('grid').style.display=v=='s'?'grid':'none';
 document.getElementById('hint').style.display=v=='s'?'block':'none';
 document.getElementById('jobs').style.display=v=='j'?'block':'none';
 document.getElementById('tS').className='tab'+(v=='s'?' on':'');document.getElementById('tJ').className='tab'+(v=='j'?' on':'');
 if(v=='j')loadJobs();}
function sz(b){if(!b)return'';let u=['B','KB','MB','GB','TB'],i=0;while(b>=1024&&i<4){b/=1024;i++}return b.toFixed(1)+' '+u[i];}
async function search(){let q=document.getElementById('q').value.trim();if(!q)return;
 document.getElementById('hint').textContent='Suche läuft …';
 let r=await fetch('/api/search?q='+encodeURIComponent(q));let d=await r.json();
 let g=document.getElementById('grid');g.innerHTML='';
 if(!d.length){document.getElementById('hint').textContent='Keine Treffer.';return;}
 document.getElementById('hint').textContent=d.length+' Treffer';
 d.forEach(it=>{let c=document.createElement('div');c.className='card';
  let cov=it.cover?`background-image:url('${it.cover}')`:'';
  let src=it.source=='usenet'?'📡 Usenet':'🗄 Archive';
  let btn=it.in_library?`<div class=have>✓ in Bibliothek</div>`:
    `<button class=dl onclick='dl(this,${JSON.stringify(JSON.stringify(it))})'>⬇ Download</button>`;
  let settag=it.is_set?' · 📦 Sammlung':'';
  c.innerHTML=`<div class=cover style="${cov}"><span class=badge>${it.platform_slug||'?'}</span><span class=src>${src}</span></div>
   <div class=body><div class=t>${it.title.replace(/</g,'&lt;')}</div><div class=meta>${sz(it.size)}${settag}</div>${btn}</div>`;
  g.appendChild(c);});}
async function dl(btn,js){btn.disabled=true;btn.textContent='…';
 let it=JSON.parse(js);
 let r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(it)});
 let d=await r.json();btn.textContent=d.ok?'✓ in Warteschlange':'Fehler';}
async function loadJobs(){let r=await fetch('/api/jobs');let d=await r.json();let j=document.getElementById('jobs');
 j.innerHTML=d.length?'':'<div class=hint>Noch keine Downloads.</div>';
 d.forEach(o=>{let e=document.createElement('div');e.className='job';
  e.innerHTML=`<div><div>${o.title.replace(/</g,'&lt;')}</div><div class=meta style="color:#8b929e;font-size:11px">${o.platform} · ${o.source} · ${o.msg||''}</div></div>
   <span class="st ${o.state}">${o.state}</span>`;j.appendChild(e);});}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key=='Enter')search();});
setInterval(()=>{if(cur=='j')loadJobs();},4000);
</script></body></html>"""

@app.route("/")
def index(): return Response(PAGE, mimetype="text/html")

@app.route("/api/search")
def api_search():
    q = request.args.get("q","").strip()
    if not q: return jsonify([])
    return jsonify(do_search(q))

@app.route("/api/download", methods=["POST"])
def api_download():
    it = request.get_json(force=True)
    # Server-seitige Dedup-Sperre
    if in_library(it.get("title",""), it.get("platform")):
        return jsonify({"ok":False,"msg":"bereits in Bibliothek"})
    job = new_job(it)
    return jsonify({"ok":True,"id":job["id"]})

@app.route("/api/jobs")
def api_jobs():
    with JOBS_LOCK: return jsonify(list(reversed(JOBS))[:100])

@app.route("/health")
def health(): return jsonify({"ok":True,"lib_titles":len(LIB['all']),"jobs":len(JOBS)})

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
