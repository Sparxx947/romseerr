"""Gemeinsame Helfer und Konstanten der Testdateien.

Hier steht alles, was `test_smoke.py` UND `test_stream_host.py` brauchen koennen. Der
Anlass ist die Aufteilung aus #505 — und die Form ist eine Lehre aus #506: Waeren diese
Funktionen in beide Dateien KOPIERT worden, gaebe es zwei Fassungen, die auseinander
laufen. Genau so kam es dazu, dass vier Tests still eine andere Datei geprueft haben als
ihr Name sagt.

Sie liegen bewusst geschlossen hier und nicht verteilt: Ein Helfer, der einen anderen
Helfer benutzt, waere sonst je nach Aufteilung mal da und mal nicht.

EN: helpers and constants shared by both test files. Copying rather than sharing them is
how four tests came to exercise the wrong file (#506); keeping them together avoids the
follow-up problem of helpers that use other helpers.
"""
import ast
import json
import os
import yaml
import re
import sys
import shlex
import shutil
import subprocess
import tempfile
import time

import pytest


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



# Jede Instanz braucht mindestens einen Admin mit Passwort — save_users weist alles andere
# ab (#234). Die Fixtures hier bauten vorher Instanzen, die NUR aus einem Nutzerkonto
# bestanden: real waere das genau der ausgesperrte Zustand, in den die App nicht geraten
# darf. Der Admin gehoert also dazu, nicht als Zugestaendnis an die Pruefung, sondern weil
# der Testaufbau sonst etwas Unmoegliches beschreibt.
ADMIN_FIX = {"chef": {"pw": "x", "role": "admin", "perms": []}}


def _staging(appmod, jid, files):
    import os
    folder = os.path.join(appmod.STAGING, f"test_{jid}")
    os.makedirs(folder, exist_ok=True)
    for name, data in files.items():
        with open(os.path.join(folder, name), "wb") as f: f.write(data)
    return folder


def _admin(appmod, client, name="exp"):
    appmod.save_users({name: {"pw": "hash-des-kennworts", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = name; sess["role"] = "admin"


def _seed_catalog(appmod, slug, names):
    """Katalog-Momentaufnahme direkt setzen — die Tests fassen IGDB nie an."""
    from contextlib import closing as _closing
    with appmod.DB_LOCK, _closing(appmod.db_conn()) as c, c:
        c.execute("DELETE FROM catalog WHERE slug=?", (slug,))
        c.executemany("INSERT INTO catalog(slug,norm,name) VALUES(?,?,?)",
                      [(slug, appmod.norm(n), n) for n in names])


def _seed_ra(appmod, rows):
    """RA-Sets direkt setzen — die Tests fassen RetroAchievements nie an."""
    from contextlib import closing as _closing
    with appmod.DB_LOCK, _closing(appmod.db_conn()) as c, c:
        c.execute("DELETE FROM ra_games")
        c.executemany("INSERT INTO ra_games(slug,norm,ra_id,title,achievements,points) VALUES(?,?,?,?,?,?)",
                      [(s, appmod.norm(t), i, t, a, p) for s, t, i, a, p in rows])


HYDRA_SAMPLE = {
    "name": "Beispielquelle",
    "downloads": [
        {"title": "Chrono Trigger (USA)", "uris": ["https://hoster.invalid/f/abc"],
         "uploadDate": "2026-01-02", "fileSize": "12 MB"},
        {"title": "Super Metroid (Europe)",
         "uris": ["https://cdn.invalid/files/supermetroid.zip"],
         "uploadDate": "2026-01-03", "fileSize": "3 MB"},
        {"title": "Nur Torrent", "uris": ["magnet:?xt=urn:btih:deadbeef"],
         "uploadDate": "2026-01-04", "fileSize": "1 MB"},
        {"title": "Ohne Links", "uris": [], "uploadDate": "", "fileSize": ""},
    ],
}


def _stream_ready(appmod, slug="ps2", name="Zzz Streamtitel.iso"):
    d = os.path.join(appmod.ROMS, slug)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, name), "w").close()
    appmod.build_index()
    appmod.save_settings({"connections": {"stream_url": "http://stream.example:3000/"}})


def _mit_index(appmod, per):
    """Den Bibliotheks-Index fuer einen Test setzen und hinterher zuruecklegen."""
    with appmod.LIB_LOCK:
        alt = dict(appmod.LIB["per"]), set(appmod.LIB["slugs"])
        appmod.LIB["per"] = {k: set(v) for k, v in per.items()}
        appmod.LIB["slugs"] = set(per)
    return alt


def _index_zurueck(appmod, alt):
    with appmod.LIB_LOCK:
        appmod.LIB["per"], appmod.LIB["slugs"] = alt[0], alt[1]


# --------------------------------------------------------------- Zweigmodell (#111)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- Uebersetzungen: EINE Quelle fuer alle Pruefungen (#350) ------------------------
# Die Tabellen lagen bis #350 in `index.js`; jede Pruefung suchte sie dort mit einem
# eigenen Muster. Beim Auslagern in JSON fielen deshalb sieben Tests auf einmal um —
# nicht weil etwas kaputt war, sondern weil sieben Stellen dasselbe wussten.
# Jetzt weiss es eine.
#
# Seven checks each grepped index.js with their own pattern; moving the tables broke all
# seven at once. One helper now knows where they live.

def sprachtabellen():
    """{sprache: {schluessel: text}} — aus `static/i18n/*.json`."""
    import json
    ordner = os.path.join(REPO, "static", "i18n")
    aus = {}
    for datei in sorted(os.listdir(ordner)):
        if datei.endswith(".json"):
            with open(os.path.join(ordner, datei), encoding="utf-8") as f:
                aus[datei[:-5]] = json.load(f)
    return aus


def i18n_hat(schluessel):
    """In wie vielen Sprachen gibt es den Schluessel mit nicht-leerem Text?"""
    return sum(1 for t in sprachtabellen().values() if str(t.get(schluessel, "")).strip())


def _workflow(name):
    import yaml
    p = os.path.join(REPO, ".github", "workflows", name)
    # "on:" ist in YAML 1.1 der Wahrheitswert True — deshalb nicht nach "on" suchen.
    return yaml.safe_load(open(p, encoding="utf-8"))


# ------------------------------------------- Pfadvertrag zum Streaming-Host (#130)

def _agent_module(roms, **umgebung):
    """Den Start-Dienst als Modul laden. Der Serverstart haengt an __main__, das
    Importieren ist also folgenlos."""
    import importlib.util
    alt = dict(os.environ)
    os.environ.update({"STREAM_AGENT_TOKEN": "t", "STREAM_ROMS": str(roms), **umgebung})
    try:
        pfad = os.path.join(REPO, "contrib/streaming-host/stream-agent.py")
        spec = importlib.util.spec_from_file_location("stream_agent_test", pfad)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    finally:
        os.environ.clear(); os.environ.update(alt)


# ------------------------------------------------ Controller-Profile (#119)



def _pcsx2_ini(tmp_path, inhalt):
    d = tmp_path / ".config/PCSX2/inis"; d.mkdir(parents=True)
    (d / "PCSX2.ini").write_text(inhalt, encoding="utf-8")
    return d / "PCSX2.ini"


# ------------------------------------------- Startprofil je Emulator (#119)

def _profil_modul(config_root):
    import importlib.util
    alt = dict(os.environ); os.environ["FW_CONFIG_ROOT"] = str(config_root)
    try:
        pfad = os.path.join(REPO, "contrib/streaming-host/launch-profile.py")
        spec = importlib.util.spec_from_file_location("launch_profile_test", pfad)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
    finally:
        os.environ.clear(); os.environ.update(alt)


def _readme_ueberschriften(datei, ebene):
    """Ueberschriften genau EINER Ebene. `"## Foo".startswith("### ")` ist falsch und
    `"### Foo".startswith("## ")` ebenso — das Leerzeichen trennt die Ebenen sauber."""
    text = open(os.path.join(REPO, datei), encoding="utf-8").read()
    return [z.rstrip() for z in text.splitlines() if z.startswith(ebene + " ")]


# Zwei Abschnitte tragen BEIDE Sprachen in einem Stueck — sie richten sich an den, der am
# Quellstand arbeitet, und der liest hier ohnehin beides. Sie haben deshalb bewusst kein
# Gegenstueck in der englischen Datei. Die Ausnahme steht namentlich da, damit sie nicht
# stillschweigend waechst: eine Zahl als Toleranz wuerde jede weitere Luecke schlucken.
ZWEISPRACHIG_IN_EINEM_STUECK = (
    "### Aus dem Quellstand bauen / building from source",
    "### Zweige / branches",
)


def _route_funktionen(js):
    """Schneidet die reinen Routing-Funktionen aus index.js — sie kommen bewusst ohne DOM
    aus, damit sie prüfbar sind, ohne die halbe Oberfläche nachzubauen."""
    stuecke = []
    for name in ("const ROUTEN=", "const ROUTEN_UM=", "function routeParse(", "function routeBauen("):
        i = js.index(name)
        # bis zur nächsten Zeile, die am Zeilenanfang mit einem neuen Statement beginnt
        j = js.index("\n", i)
        tiefe = js.count("{", i, j) - js.count("}", i, j)
        while tiefe > 0:
            j = js.index("\n", j + 1)
            tiefe = js.count("{", i, j) - js.count("}", i, j)
        stuecke.append(js[i:j])
    return "\n".join(stuecke)


# ---------- Die Dokumentationsregel mechanisch halten (#212) ----------
# Doku ist hier Pflicht, auf Deutsch UND Englisch. Bisher hielt das, weil jemand daran
# denkt — die schwächste Garantie, die es gibt. Was schon mechanisch ist (OpenAPI-Abdeckung,
# Spec-Gleichstand), ist nie verrutscht; die Kommentarqualität schwankt. Der Unterschied
# ist nicht Sorgfalt, sondern dass eines davon einen Build rot macht.
#
# BEIDE Prüfungen sind RATSCHEN, keine Zielwerte: sie halten den heutigen Stand fest.
# Neuer Code darf ihn nicht verschlechtern, jede nachgebesserte Stelle hebt den Boden.
# Ein fester Zielwert wäre heute unerreichbar oder später bedeutungslos.

DOC_EN_BODEN = 21.0      # gemessener Anteil zweisprachiger Blöcke: 35 von 166 = 21,08 %
DOC_ROUTEN_OHNE = 73     # Route-Handler ohne Docstring, Stand der Messung

_EN_WORTE = (r"\b(the|is|are|was|were|not|that|which|does|do|with|from|only|never|always|"
             r"because|what|when|where|would|should|could|this|these|those|and|but|for|"
             r"into|about|after|before|instead|rather|still|there|they|them|it|its)\b")
_DE_WORTE = (r"\b(der|die|das|und|nicht|ist|sind|war|ein|eine|einen|dass|wird|werden|sich|"
             r"nur|schon|noch|aber|weil|wenn|dann|dort|hier|man|kann|muss|soll|beim|"
             r"vom|zum|zur|auf|aus|mit|ohne|fuer|für|durch|gegen|jede|jeder|jedes)\b")


def _doc_bloecke(text):
    """Kommentar- und Docstring-Blöcke ab drei Zeilen."""
    import re
    aus = [m.group(1) for m in re.finditer(r'"""(.*?)"""', text, re.S) if m.group(1).count("\n") >= 2]
    lauf = []
    for zeile in text.split("\n"):
        s = zeile.strip()
        if s.startswith("#"):
            lauf.append(s.lstrip("#").strip())
        else:
            if len(lauf) >= 3:
                aus.append("\n".join(lauf))
            lauf = []
    if len(lauf) >= 3:
        aus.append("\n".join(lauf))
    return aus


def _hat_englisch(block):
    """Trägt der Block einen englischen Teil?

    Zeilenweise, weil die Blöcke hier gemischt sind: deutscher Text mit einem englischen
    Absatz. Eine Zeile zählt als englisch bei mindestens drei englischen Funktionswörtern
    und keinem deutschen.

    GEGENGEPRÜFT vor der Einführung, gegen 166 Blöcke und mit einer unabhängig gebauten
    Kontrollregel (`EN:`, `the X is`, `instead of`, …): **0 falsch negative**. Die 27
    zunächst verdächtigen Fälle waren beim Nachlesen durchweg echtes Englisch — die
    Kontrollregel war zu eng, nicht die Heuristik. Das war die Bedingung aus #212: eine
    Erkennung, die falsch anschlägt, wird binnen einer Woche abgeschaltet, und dann steht
    die Regel schlechter da als ganz ohne Test.
    """
    import re
    for zeile in block.split("\n"):
        z = zeile.strip().lower()
        if len(z) >= 25 and len(set(re.findall(_EN_WORTE, z))) >= 3 and not re.search(_DE_WORTE, z):
            return True
    return False


def _doc_dateien():
    dateien = ["app.py"]
    for wurzel, _, namen in os.walk("contrib"):
        dateien += [os.path.join(wurzel, n) for n in namen if n.endswith((".py", ".sh"))]
    return dateien


# ---------- Wo liegt was? (#192) ----------
# Der Umzug von JSON-Dateien nach SQLite lief Speicher für Speicher, und danach hat
# niemand die Gesamtfrage gestellt. Nachgemessen auf der laufenden Anlage:
#
#   users.json / jobs.json / settings.json  -> migriert, `.migrated` daneben, Tabelle gefüllt
#   issues.json / maillog.json / push_subs.json -> NIE geschrieben (kein .migrated, kein kv-Schlüssel)
#   vapid.json                              -> aktive Datei, absichtlich nicht in der DB
#   secret.key                              -> ebenso
#
# „Keine Datei" war dabei kein Beleg für „migriert": bei den drei mittleren heißt es, dass
# das Feature auf dieser Installation nie benutzt wurde. Genau diese Zweideutigkeit soll
# nicht noch einmal von Hand aufgelöst werden müssen.
DATEI_SPEICHER = {
    "users.json": "migriert -> Tabelle users",
    "jobs.json": "migriert -> Tabelle jobs",
    "settings.json": "migriert -> kv['settings']",
    "issues.json": "migriert -> kv['issues'] (Datei entsteht nur bei Altbestand)",
    "maillog.json": "migriert -> kv['maillog'] (dito)",
    "push_subs.json": "migriert -> kv['push'] (dito)",
    "vapid.json": "BLEIBT Datei: privater Push-Schlüssel, absichtlich außerhalb der DB",
    "secret.key": "BLEIBT Datei: Sitzungssignatur, absichtlich außerhalb der DB",
    # In der Neuprüfung zu #192 zusätzlich gefunden — im Issue kamen sie nicht vor:
    "tls": "BLEIBT Verzeichnis: Zertifikat + privater Schlüssel (0600)",
    "logos": "BLEIBT Verzeichnis: Bilddateien gehören nicht in eine Spalte",
    ".schreibprobe": "keine Daten: Schreibprobe für /health (#216)",
}


# ------------------------------- Eigene Bibliothek durchsehen (#293)

def _lege_titel_an(appmod, slug, dateien):
    d = os.path.join(appmod.ROMS, slug)
    os.makedirs(d, exist_ok=True)
    for name, groesse in dateien:
        with open(os.path.join(d, name), "wb") as f:
            f.write(b"x" * groesse)
    appmod.build_index()
    return d


# ------------------------------- 3DS: Verschluesselung vor dem Start erkennen (#299)

def _ncsd_bauen(pfad, nocrypto):
    """Minimales 3DS-Abbild: NCSD-Kennung, NCCH-Kennung, Flags."""
    daten = bytearray(0x4200)
    daten[0x100:0x104] = b"NCSD"
    daten[0x4100:0x4104] = b"NCCH"
    daten[0x4188:0x4190] = bytes([0, 0, 0, 0, 1, 3, 0, 0x04 if nocrypto else 0x00])
    with open(pfad, "wb") as f:
        f.write(daten)


# --- Ansichten, Routen und Browsertests -------------------------------------------
# Beide Pruefungen sind statisch: Sie lesen index.js und die Tabelle der Browsertests.
# Das ist Absicht — die eine haette #320 am Tag der Entstehung gefunden, ganz ohne Browser.

def _js():
    pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "static", "js", "index.js")
    with open(pfad, encoding="utf-8") as f:
        return f.read()


def _routen_und_ansichten():
    """(Schluessel in ROUTEN, Schluessel die `zeige()` behandelt)."""
    import re
    js = _js()
    m = re.search(r"ROUTEN\s*=\s*\{([^}]*)\}", js)
    routen = set(re.findall(r"(\w+)\s*:", m.group(1)))
    i = js.find("function zeige(")
    ansichten = set(re.findall(r"v\s*==\s*'(\w+)'", js[i:i + 1400]))
    return routen, ansichten


# RATSCHE, kein Zielwert: Die Zahl der Ansichten ohne Browsertest darf nicht steigen.
# Heute ist sie 1 — `lists` ist routebar, steht aber in keiner Seitenleiste und wird von
# den Browsertests nicht angeklickt. Wer eine Ansicht hinzufuegt und den Browsertest
# vergisst, hebt sie auf 2 und wird rot. Wer `lists` nachtraegt, senkt sie auf 0. (#327)
#
# One view (`lists`) is routable but has no sidebar entry and no browser test. The floor
# records that honestly instead of pretending it is covered.
ANSICHTEN_OHNE_BROWSERTEST = 1


# --- 3DS: die Absage kommt vor der Zusage (#299) -----------------------------------

def _3ds_datei(tmp_path, name, verschluesselt):
    """Ein minimales NCSD-Abbild mit gesetztem oder fehlendem NoCrypto-Bit."""
    p = tmp_path / name
    b = bytearray(0x4200)
    b[0x100:0x104] = b"NCSD"
    b[0x4100:0x4104] = b"NCCH"
    b[0x4188 + 7] = 0x00 if verschluesselt else 0x04     # Bit 2 = NoCrypto
    p.write_bytes(bytes(b))
    return str(p)


def _cia_datei(tmp_path, name, titel_id):
    """Eine minimale, aber ECHTE CIA: Kopf, Zertifikatskette, Ticket, TMD mit Titel-ID.

    WARUM NICHT EINFACH 64 NULLBYTES: Genau das taten die beiden Vorgaengertests — und sie
    prueften damit nur den Fehlerpfad, waehrend sie behaupteten, die Absage fuer CIAs zu
    pruefen. Solange jede CIA abgewiesen wurde, fiel das nicht auf. Seit #315 haengt die
    Antwort an der Titel-ID, und eine Attrappe ohne TMD kann sie nicht liefern.
    """
    import struct
    hs, certs, tickets = 0x2020, 0x40, 0x40
    aus = lambda n: (n + 63) // 64 * 64
    kopf = bytearray(struct.pack("<IHHIIIIQ", hs, 0, 0, certs, tickets, 0x208, 0, 0))
    kopf += b"\x00" * (aus(hs) - len(kopf))
    kopf += b"\x00" * aus(certs)
    kopf += b"\x00" * aus(tickets)
    tmd = bytearray(struct.pack(">I", 0x00010004))     # RSA_2048_SHA256
    tmd += b"\x00" * (0x100 + 0x3C)                    # Signatur + Auffuellung
    kopf_tmd = bytearray(b"\x00" * 0x54)
    struct.pack_into(">Q", kopf_tmd, 0x4C, titel_id)
    tmd += kopf_tmd
    p = tmp_path / name
    p.write_bytes(bytes(kopf + tmd))
    return str(p)


# --- #388: die Naht zwischen Agent und Entschluesselungswerkzeug ----------------------

def _agent_modul():
    """`stream-agent.py` als Modul laden (kein `.py`-Import moeglich)."""
    import importlib.util
    pfad = os.path.join(REPO, "contrib", "streaming-host", "stream-agent.py")
    spec = importlib.util.spec_from_file_location("stream_agent_cia", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _falsches_werkzeug(tmp_path, verhalten):
    """Ein nachgebautes `decrypt_cia.py`. Baut den Namen wie das ECHTE — feste Endung.

    WARUM NACHGEBAUT: Das echte Werkzeug braucht pycryptodome und laeuft auf dem
    Streaming-Host. Geprueft werden soll hier nicht die Kryptografie, sondern die NAHT —
    und genau dort lag der Fehler: Die Entschluesselung lief durch, der Agent fand die
    Datei nicht und meldete Misserfolg.
    """
    w = tmp_path / "werkzeug.py"
    w.write_text(
        "import os, shutil, sys\n"
        "ein = sys.argv[1]\n"
        f"verhalten = {verhalten!r}\n"
        "if verhalten == 'normal':\n"
        # exakt wie im Original: Endung fest auf .cia, unabhaengig von der Eingabe
        "    aus = os.path.splitext(ein)[0] + '-decrypted.cia'\n"
        "    shutil.copyfile(ein, aus)\n"
        "elif verhalten == 'anderer_name':\n"
        # Ein Name, den NIEMAND aus der Eingabe herleiten kann. Genau das trennt „findet
        # die Ausgabe" von „raet ihren Namen richtig".
        "    shutil.copyfile(ein, os.path.join(os.path.dirname(ein), 'fertig-xyz.cia'))\n"
        "elif verhalten == 'nichts':\n"
        "    pass\n"
        "print('Done')\n", encoding="utf-8")
    return str(w)


# ---------------- Eine Plattform, die nicht gelesen werden kann, muss auffallen (#381)
#
# GEMESSEN, BEVOR HIER ETWAS STAND: `os.walk` wirft bei einem Rechte- oder E/A-Fehler
# KEINE Ausnahme. Ohne `onerror` ruft es niemanden und liefert einfach nichts. Der
# `except Exception: pass` im Rumpf von `build_index` wurde bei genau diesem Fall nie
# betreten — ihn laut zu machen haette nichts geaendert.
#
# Live nachgewiesen am 2026-08-12: `/roms/pico8` steht auf `drwx-w----` (Gruppe darf
# schreiben, nicht lesen), der Container laeuft in dieser Gruppe. 13.202 Dateien,
# 13.176 distinkte Titel — verbucht wurden 0, und vier Indexlaeufe in Folge meldeten
# `598 Plattformen, 128177 Titel` ohne ein Wort dazu.
#
# EN: os.walk raises nothing on a permission or I/O error — without `onerror` it just
# yields nothing. Measured live: /roms/pico8 is 0720, so the container may write but not
# read it; 13,176 titles counted as zero with no log line at all.

def _unlesbar_machen(pfad):
    """0o000 setzen und PRUEFEN, dass es wirkt. Als root wirkt es nicht — dann None.

    Ein Test, der als root stillschweigend durchlaeuft, prueft nichts. Lieber
    uebersprungen als gruen ohne Aussage.
    """
    os.chmod(pfad, 0o000)
    try:
        os.scandir(pfad).close()
    except PermissionError:
        return True
    os.chmod(pfad, 0o755)
    return False


class _Protokoll:
    """Sammelt, was `log()` geschrieben haette."""
    def __init__(self): self.zeilen = []
    def __call__(self, msg): self.zeilen.append(str(msg))
    def mit(self, teil): return [z for z in self.zeilen if teil in z]
    @property
    def schluss(self):
        z = self.mit("Bibliotheks-Index:")
        return z[-1] if z else ""


def _index_mit_protokoll(appmod, monkeypatch):
    p = _Protokoll()
    monkeypatch.setattr(appmod, "log", p)
    # Frisch wie nach einem Start (#766): Seit der volle Lauf einen unveraenderten Bestand
    # verschweigt, haengt die Schlussmeldung davon ab, was ein FRUEHERER Test gebaut hat.
    # Zwei Tests mit gleichem Bestand hintereinander — und der zweite bekaeme nichts zu
    # sehen. Der Merker gehoert dem Prozess, also wird er hier zurueckgelegt, statt jeden
    # Aufrufer daran denken zu lassen.
    appmod.INDEX_LOG_LETZTE.update(sig=None, ts=0.0, still=0)
    appmod.build_index()
    return p


# --- #379: die schreibenden Endpunkte mit Sicherheitsbezug ---------------------------
#
# WARUM GERADE DIESE DREI: Von 24 ungeprueften schreibenden Endpunkten tragen drei eine
# Grenze, deren Bruch nicht auffaellt — Passwort-Zuruecksetzen, Freigabe fremder Anfragen,
# Loeschen. Alle drei sind im Quelltext KORREKT abgesichert; gemessen, nicht angenommen.
# Was fehlte, war die Zusicherung, dass es so bleibt.

def _als(client, appmod, name, passwort="pw123456", rolle="user"):
    """Melde einen Nutzer an; lege ihn an, wenn er fehlt. -> der Client."""
    if client.get("/api/auth/status").get_json().get("setup"):
        client.post("/api/setup", json={"username": "admin", "password": "pw123456",
                                        "display_name": "Admin"})
    client.post("/api/login", json={"username": "admin", "password": "pw123456"})
    if name != "admin":
        users = appmod.load_users()
        if name not in users:
            users[name] = {"pw": appmod.generate_password_hash(passwort), "role": rolle}
            appmod.save_users(users)
        client.post("/api/logout")
        client.post("/api/login", json={"username": name, "password": passwort})
    return client


# --- #427: Updates und DLC sind keine Spiele ----------------------------------------

def _nsp_datei(tmp_path, name, titel_id):
    """Ein minimales, aber ECHTES PFS0-Archiv mit einem Ticket im Inhaltsverzeichnis.

    Nicht einfach ein paar Bytes: Die Titel-ID wird aus dem NAMEN des Ticket-Eintrags
    gelesen, also muss das Inhaltsverzeichnis stimmen. Eine Attrappe ohne gueltiges PFS0
    pruefte nur den Fehlerpfad und behauptete, die Absage zu pruefen — genau die Falle,
    in die die ersten CIA-Tests gelaufen sind.
    """
    import struct
    eintraege = [f"{titel_id}0000000000000004.tik", "abcd.nca"]
    tabelle = b""
    versatz = []
    for n in eintraege:
        versatz.append(len(tabelle))
        tabelle += n.encode() + b"\x00"
    kopf = struct.pack("<4sIII", b"PFS0", len(eintraege), len(tabelle), 0)
    for i, _n in enumerate(eintraege):
        kopf += struct.pack("<QQII", 0, 16, versatz[i], 0)
    p = tmp_path / name
    p.write_bytes(kopf + tabelle + b"\x00" * 64)
    return str(p)


def _agent_pfadwahl():
    """Der Block aus `init/30-agent`, der entscheidet, WELCHE Agent-Datei startet.

    Herausgeschnitten statt nachgebaut: Ein nachgebauter Block prueft die Kopie im Test,
    nicht das Skript, das ausgeliefert wird.

    ABGRENZUNG AN DER LEERZEILE, NICHT AM `fi`. Am `fi` festgemacht, schneidet der Test
    den ALTEN Stand gar nicht erst aus — der hatte keins — und faellt dann mit
    „kein abschliessendes 'fi' gefunden" statt mit „greift auf die Altfassung zurueck".
    Eine Pruefung, die beim eigentlichen Defekt die falsche Ursache nennt, schickt den
    naechsten Leser ans falsche Ende.

    EN: delimited by the blank line, not by `fi`. Anchored at `fi` the extraction fails
    on the very code this is meant to catch, and reports the wrong cause.
    """
    quelle = open(os.path.join(REPO, "contrib", "streaming-host", "init", "30-agent"),
                  encoding="utf-8").read().splitlines()
    try:
        start = next(i for i, z in enumerate(quelle) if z.strip() == "AGENT=/opt/stream-agent.py")
    except StopIteration:
        raise AssertionError("Anker 'AGENT=/opt/stream-agent.py' fehlt in init/30-agent")
    ende = next((i for i in range(start + 1, len(quelle)) if not quelle[i].strip()),
                len(quelle))
    return "\n".join(quelle[start:ende])


# --- #488: zwei modale Fenster fangen jeden Vita-Start ab ---------------------------
#
# NACHGEMESSEN am laufenden Host (2026-08-13, Gravity Rush, Vita3K v0.2.1), mit
# Gegenprobe je Schalter — die Tabelle steht im Issue:
#
#   show-welcome | check-for-updates-mode | Fenster der ECHTEN Vita3K-PID
#   true         | 1                      | nur "Welcome to Vita3K", kein Spiel, 4,5 % CPU
#   false        | 1                      | Spiel + "Update Available" (320x183 mittendrauf)
#   false        | 0                      | Spiel, kein Dialog -> Fensterschritt meldet "ok"
#   false        | 1  (Gegenprobe)        | "Update Available" wieder da
#
# Der zweite Schalter steht hier NICHT auf Verdacht: ohne ihn tauscht die Behebung nur
# einen Dialog gegen einen anderen.

def _lp_mit_config(tmp_path, monkeypatch, name):
    """launch-profile.py mit `tmp_path` als /config laden."""
    import importlib.util
    pfad = os.path.join(REPO, "contrib/streaming-host/launch-profile.py")
    spec = importlib.util.spec_from_file_location(name, pfad)
    lp = importlib.util.module_from_spec(spec)
    monkeypatch.setenv("FW_CONFIG_ROOT", str(tmp_path))
    spec.loader.exec_module(lp)
    return lp


# --- #481: eine PS-Vita-Titelkennung ist kein Pfad ----------------------------------

def _param_sfo(ziel, **werte):
    """Schreibt ein `param.sfo` mit den gegebenen Zeichenketten-Feldern.

    NACH DER ECHTEN DATEI GEBAUT, nicht erfunden: `sce_sys/param.sfo` von
    „Gravity Rush (Europe).vpk" der Bibliothek hat den Kopf

        00 50 53 46 | 01 01 00 00 | 24 01 00 00 | e0 01 00 00 | 11 00 00 00
        Magie        Fassung       Schluessel-   Datentabelle   17 Eintraege
                                   tabelle 0x124  0x1e0

    und darin `TITLE_ID = 'PCSF00024'` als Format 0x0204 (UTF-8). Genau diesen Aufbau
    erzeugt dieser Helfer — mit denselben Feldbreiten und derselben Ausrichtung.

    EN: built from the real file's header, not invented.
    """
    import struct
    namen = sorted(werte)
    schluesseltabelle = b""
    schluesselversatz = {}
    for k in namen:
        schluesselversatz[k] = len(schluesseltabelle)
        schluesseltabelle += k.encode("utf-8") + b"\x00"
    schluesseltabelle += b"\x00" * (-len(schluesseltabelle) % 4)

    datentabelle = b""
    datenversatz = {}
    for k in namen:
        roh = werte[k].encode("utf-8") + b"\x00"
        datenversatz[k] = (len(datentabelle), len(roh))
        datentabelle += roh + b"\x00" * (-len(roh) % 4)

    kopflaenge = 0x14 + 16 * len(namen)
    kopf = b"\x00PSF" + struct.pack("<IIII", 0x0101, kopflaenge,
                                    kopflaenge + len(schluesseltabelle), len(namen))
    for k in namen:
        versatz, laenge = datenversatz[k]
        kopf += struct.pack("<HHIII", schluesselversatz[k], 0x0204, laenge,
                            laenge + (-laenge % 4), versatz)
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    with open(ziel, "wb") as f:
        f.write(kopf + schluesseltabelle + datentabelle)


def _vita_bibliothek(tmp_path, ordnername="Gravity Rush (Europe).vpk",
                     titel_id="PCSF00024", installiert=("PCSF00024",)):
    """Baut Bibliothek und Vita3K-Ablage so, wie sie auf dem Host gemessen wurden:

        /roms/psvita/Gravity Rush (Europe).vpk/sce_sys/param.sfo   <- der Titel
        …/Vita3K/ux0/app/PCSF00024/                                <- installiert
    """
    roms = tmp_path / "roms"
    spiel = roms / "psvita" / ordnername
    (spiel / "sce_sys").mkdir(parents=True)
    _param_sfo(str(spiel / "sce_sys" / "param.sfo"),
               TITLE="GRAVITY RUSH", TITLE_ID=titel_id, CATEGORY="gd")
    (spiel / "eboot.bin").write_bytes(b"x")
    pref = tmp_path / "Vita3K"
    (pref / "ux0" / "app").mkdir(parents=True)
    for tid in installiert:
        (pref / "ux0" / "app" / tid).mkdir()
    return roms, pref


def _mitschrift_emulator(tmp_path, name="vita3k.sh"):
    """Ein Emulator-Ersatz, der seine Argumentliste aufschreibt. -> (befehl, datei)

    Kein Popen-Ersatz: der Agent soll den Prozess WIRKLICH starten, damit auch die
    Argumentuebergabe geprueft wird und nicht nur der Programmtext.
    """
    datei = tmp_path / f"{name}.argv"
    skript = tmp_path / name
    skript.write_text('#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done > '
                      f'"{datei}"\n')
    skript.chmod(0o755)
    return str(skript), datei


def _argv(datei, proc, sekunden=10):
    proc.wait(timeout=sekunden)
    return datei.read_text().splitlines()


# ------------------------------- Der Wrapper zwischen Agent und Emulator (#489)

def _wrapper_emulator(tmp_path, name="vita3k"):
    """Baut Vita3Ks Verpackung NACH, ohne einen Emulator zu starten. -> (befehl, marke)

    GEMESSEN am laufenden Host, bevor etwas geaendert wurde (#489). `AppRun.wrapped` ist
    bei rpcs3, cemu und azahar ein SYMLINK auf die Programmdatei und wird `exec`-t; bei
    vita3k ist es ein Shell-Skript, das das Programm als KIND startet — ohne `exec`:

        #!/bin/sh
        if [ "${APPIMAGE}" != "" ]; then
            export PATH="$APPDIR/usr/bin:$PATH"
            "${APPDIR}/usr/bin/Vita3K" $@

    Der Agent merkt sich damit die PID der SHELL, nicht die des Emulators. Am Host:

        11616  1414  /bin/sh /config/emulators/vita3k/AppRun.wrapped -r PCSF00024
        11634 11616  /config/emulators/vita3k/usr/bin/Vita3K -r PCSF00024

    Der Ersatz hier tut genau dasselbe und ueberlebt wie der echte Emulator ein SIGTERM
    — auch das ist gemessen: `kill` auf den Vita3K-Prozess genuegte nicht, erst `kill -9`.
    """
    marke = tmp_path / f"{name}.lebt"
    kind = tmp_path / f"{name}-emulator.sh"
    kind.write_text(
        "#!/bin/sh\n"
        "trap '' TERM\n"                       # wie Vita3K: SIGTERM genuegt nicht
        f'printf "%s" "$$" > "{marke}"\n'
        "while :; do sleep 0.2; done\n")
    kind.chmod(0o755)
    wrapper = tmp_path / f"{name}-AppRun.wrapped"
    wrapper.write_text(f'#!/bin/sh\n"{kind}" $@\n')   # KEIN exec — das ist der Fall
    wrapper.chmod(0o755)
    return str(wrapper), marke


def _pid_lebt(pid):
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True
