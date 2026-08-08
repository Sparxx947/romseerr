#!/usr/bin/env python3
"""Start-Dienst für den Streaming-Host / launch agent for the streaming host (Romseerr #71).

Romseerr emuliert nichts und liefert keinen Emulator aus. Es löst einen Titel auf eine
Datei auf und bittet DIESEN Dienst, sie zu starten. Der Dienst läuft im Streaming-Container
(Selkies/KasmVNC o. ä.), sieht dessen Anzeige und dessen GPU.

Bewusst ohne Abhängigkeiten (nur Standardbibliothek), damit er in jedes Desktop-Image passt.

    python3 stream-agent.py

Konfiguration über Umgebungsvariablen:

    STREAM_AGENT_PORT   Port (Default 8901)
    STREAM_AGENT_TOKEN  gemeinsames Geheimnis; MUSS gesetzt sein
    STREAM_ROMS         Wurzel der ROM-Bibliothek, wie der Container sie sieht (Default /roms)
    EMU_PS2 EMU_GC EMU_SWITCH   Pfade zu den Emulatoren

In Romseerr eintragen unter Einstellungen → Verbindungen:

    Streaming-Host   http://<host>:3000/      (die Browser-Oberfläche)
    Start-Dienst     http://<host>:8901/launch?token=…

SICHERHEIT: Dieser Dienst startet Prozesse. Er gehört NICHT ins offene Netz.
  * Ohne gültiges Token wird jede Anfrage abgewiesen.
  * Der Pfad muss innerhalb von STREAM_ROMS liegen — nach Auflösung von Symlinks.
    Sonst wäre er ein Fernstart für beliebige Dateien.
  * Es wird nie eine Shell benutzt; die Argumentliste geht direkt an execve.
"""
import json
import os
import re
import time
import shlex
import subprocess
import sys
import threading
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("STREAM_AGENT_PORT", "8901"))
TOKEN = os.environ.get("STREAM_AGENT_TOKEN", "")
ROMS = os.path.realpath(os.environ.get("STREAM_ROMS", "/roms"))

# Plattform -> Startbefehl. %s wird durch den ROM-Pfad ersetzt.
# Plattform -> Startbefehl. Leer = nicht verfuegbar, der Aufrufer bekommt dann eine
# klare Absage statt eines Startversuchs ins Leere. Die Werte setzt init/30-agent.
EMULATORS = {
    "ps2":       os.environ.get("EMU_PS2", ""),
    "ngc":       os.environ.get("EMU_GC", ""),
    "wii":       os.environ.get("EMU_GC", ""),
    "wiiu":      os.environ.get("EMU_WIIU", ""),
    "switch":    os.environ.get("EMU_SWITCH", ""),
    "3ds":       os.environ.get("EMU_3DS", ""),
    "dreamcast": os.environ.get("EMU_DC", ""),
    "xbox":      os.environ.get("EMU_XBOX", ""),
    "ps3":       os.environ.get("EMU_PS3", ""),
    "psvita":    os.environ.get("EMU_VITA", ""),
}

_current = {"proc": None, "platform": "", "path": ""}
_lock = threading.Lock()

# Ordner-Titel -> die Datei, mit der der Emulator startet.
#
# WARUM EINE TABELLE UND KEINE SUCHE NACH "der groessten Datei": Bei einer PS3-Disc
# waere das oft ein Video oder ein Datenarchiv, nicht die EBOOT.BIN. Die Reihenfolge
# ist die Rangfolge; der erste Treffer gewinnt.
# A table, not a "largest file" heuristic: on a PS3 disc that would usually pick a
# video, not the boot binary.
BOOTPFADE = {
    "ps3": ("PS3_GAME/USRDIR/EBOOT.BIN", "USRDIR/EBOOT.BIN", "EBOOT.BIN"),
}
# Rueckfall fuer Ordner ohne bekannte Struktur: eine einzelne Abbilddatei darin ist
# eindeutig. Bei MEHREREN wird bewusst NICHT geraten — lieber eine klare Absage als
# ein zufaellig gewaehltes Spiel.
BOOT_ENDUNGEN = (".iso", ".chd", ".cue", ".gdi", ".rvz", ".wbfs", ".nsp", ".xci", ".pkg")


def _in_bibliothek(pfad):
    """-> aufgeloester Pfad, wenn er unter ROMS liegt, sonst ''.

    Geprueft wird die AUFGELOESTE Form: sonst genuegt ein Symlink oder ein '..' zum
    Ausbrechen. Bewusst eine eigene Funktion, weil die Pruefung an ZWEI Stellen
    gebraucht wird — beim Pfad von aussen und noch einmal bei der Startdatei, die aus
    einem Ordner aufgeloest wurde. Beim ersten Anlauf fehlte die zweite, und ein
    Symlink im Titelordner haette den Emulator auf eine beliebige Datei des Hosts
    zeigen lassen. Gefunden hat das CodeQL, nicht ich.
    Resolved form only; needed twice, and the second call was missing at first.
    """
    try:
        real = os.path.realpath(pfad)
        return real if os.path.commonpath([real, ROMS]) == ROMS else ""
    except (ValueError, OSError):
        return ""


def _bootdatei(ordner, platform):
    """-> absoluter Pfad der Startdatei, oder '' wenn nicht eindeutig bestimmbar."""
    for rel in BOOTPFADE.get(platform, ()):
        k = os.path.join(ordner, *rel.split("/"))
        if os.path.isfile(k):
            return k
    treffer = []
    try:
        for e in sorted(os.listdir(ordner)):
            k = os.path.join(ordner, e)
            if os.path.isfile(k) and e.lower().endswith(BOOT_ENDUNGEN):
                treffer.append(k)
    except OSError:
        return ""
    return treffer[0] if len(treffer) == 1 else ""

# Emulator-Aktualisierung. Laeuft im Hintergrund, damit der Aufrufer nicht minutenlang
# auf einer HTTP-Antwort haengt — Downloads sind hier hunderte Megabyte.
# Runs in the background; downloads are hundreds of megabytes.
UPDATE_SCRIPT = os.environ.get("EMU_UPDATE_SCRIPT", "/custom-cont-init.d/20-emulators")
_update = {"running": False, "started": 0, "finished": 0, "rc": None, "log": "", "target": ""}

# Firmware und BIOS. Dasselbe Muster: die Tabelle steht im Skript, hier wird sie nur
# abgefragt. / Same pattern as the emulator catalogue: the table lives in the script.
FIRMWARE_SCRIPT = os.environ.get("FIRMWARE_SCRIPT", "/custom-cont-init.d/25-firmware")
# Controller-Belegung. Wird VOR jedem Start angewandt, nicht einmalig beim Hochfahren:
# die Emulatoren schreiben ihre Konfiguration beim Beenden zurueck, und eine einmal
# gesetzte Belegung waere danach womoeglich wieder weg.
# Applied before every launch, not once at boot: emulators rewrite their config on exit.
PROFILE_SCRIPT = os.environ.get("PROFILE_SCRIPT", "/opt/launch-profile.py")
# Plattform -> Emulator, fuer den es ein Profil gibt. Kein Eintrag = der Emulator ordnet
# ein erkanntes SDL-Pad selbst zu. / No entry = the emulator maps a detected pad itself.
# Plattform -> Emulator im Startprofil. Ohne Eintrag wird kein Profil angewandt.
PROFILE_EMU = {"ps2": "pcsx2", "ngc": "dolphin", "wii": "dolphin", "wiiu": "cemu",
               "switch": "switchemu", "3ds": "azahar", "dreamcast": "flycast",
               "xbox": "xemu", "ps3": "rpcs3", "psvita": "vita3k"}
# Grenze fuer einen Upload. Die groesste Datei, die hier real ankommt, ist Sonys
# PS3-Paket mit gut 200 MB; 512 MB lassen Luft, ohne dass jemand den Container mit
# einem Dauerstrom volllaufen lassen kann.
# Cap for uploads: Sony's PS3 package is the largest real case at ~200 MB.
MAX_UPLOAD = int(os.environ.get("FIRMWARE_MAX_BYTES", str(512 * 1024 * 1024)))
_vendor = {"running": False, "rc": None, "log": "", "target": ""}


def firmware_status():
    try:
        r = subprocess.run(["/bin/bash", FIRMWARE_SCRIPT, "--status"],
                           capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout) if r.returncode == 0 else {"ok": False, "platforms": []}
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return {"ok": False, "platforms": []}


def firmware_platforms():
    """Welche Plattformkuerzel kennt das Skript? Damit wird eine Eingabe geprueft —
    gegen die TABELLE, nicht gegen ein Muster. Ein Muster sagt nur, wie ein Name
    aussehen darf; die Tabelle sagt, welcher existiert."""
    return {p.get("platform") for p in firmware_status().get("platforms", [])}


def run_vendor(platform):
    """Herstellerbezug im Hintergrund — Sonys Paket ist ueber 200 MB."""
    _vendor.update({"running": True, "rc": None, "log": "", "target": platform})
    try:
        r = subprocess.run(["/bin/bash", FIRMWARE_SCRIPT, "--vendor", platform],
                           capture_output=True, text=True, timeout=3600)
        _vendor["rc"] = r.returncode
        _vendor["log"] = (r.stdout + r.stderr)[-8000:]
    except subprocess.TimeoutExpired:
        _vendor["rc"] = -1; _vendor["log"] = "Zeitueberschreitung / timed out"
    except OSError as e:
        _vendor["rc"] = -1
        _vendor["log"] = f"Start fehlgeschlagen / launch failed: {e.__class__.__name__}"
    finally:
        _vendor["running"] = False


def run_update():
    """Das Installationsskript erneut ausfuehren. Es ist idempotent und laedt nur,
    was sich geaendert hat — deshalb ist 'aktualisieren' dasselbe wie 'installieren'."""
    _update.update({"running": True, "started": int(time.time()),
                    "finished": 0, "rc": None, "log": ""})
    try:
        # EMU_AUTO_UPDATE erzwingen: ein ausdruecklich angestossener Lauf soll
        # aktualisieren, auch wenn der automatische Abgleich abgeschaltet ist.
        env = {**os.environ, "EMU_AUTO_UPDATE": "true"}
        r = subprocess.run(["/bin/bash", UPDATE_SCRIPT], env=env, capture_output=True,
                           text=True, timeout=3600)
        _update["rc"] = r.returncode
        _update["log"] = (r.stdout + r.stderr)[-8000:]
    except subprocess.TimeoutExpired:
        _update["rc"] = -1
        _update["log"] = "Zeitueberschreitung / timed out"
    except OSError as e:
        _update["rc"] = -1
        _update["log"] = f"Start fehlgeschlagen / launch failed: {e.__class__.__name__}"
    finally:
        _update["running"] = False
        _update["finished"] = int(time.time())


def catalogue():
    """Was ist installierbar, was ist installiert? Kommt aus dem Installationsskript
    selbst — dort steht die Tabelle, und zwei Wahrheiten waeren eine zu viel."""
    try:
        r = subprocess.run(["/bin/bash", UPDATE_SCRIPT, "--catalog"],
                           capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout) if r.returncode == 0 else []
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return []


def run_install(name):
    """Genau einen Emulator installieren. Laeuft im Hintergrund — das sind hunderte
    Megabyte, darauf soll niemand in einer HTTP-Antwort warten."""
    _update.update({"running": True, "started": int(time.time()),
                    "finished": 0, "rc": None, "log": "", "target": name})
    try:
        r = subprocess.run(["/bin/bash", UPDATE_SCRIPT, "--only", name],
                           env={**os.environ, "EMU_AUTO_UPDATE": "true"},
                           capture_output=True, text=True, timeout=3600)
        _update["rc"] = r.returncode
        _update["log"] = (r.stdout + r.stderr)[-8000:]
    except subprocess.TimeoutExpired:
        _update["rc"] = -1; _update["log"] = "Zeitueberschreitung / timed out"
    except OSError as e:
        _update["rc"] = -1
        _update["log"] = f"Start fehlgeschlagen / launch failed: {e.__class__.__name__}"
    finally:
        _update["running"] = False
        _update["finished"] = int(time.time())


def installed_emulators():
    """Was liegt da, und aus welcher Quelle? Die .url-Datei neben dem Ordner ist die
    zuletzt installierte Release-URL und damit die belastbarste Versionsangabe."""
    base = os.path.dirname(UPDATE_SCRIPT)  # nur fuer den Fall der Faelle
    emu = os.environ.get("EMU_DIR", "/config/emulators")
    out = []
    try:
        for name in sorted(os.listdir(emu)):
            d = os.path.join(emu, name)
            if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "AppRun")):
                continue
            src = ""
            marker = os.path.join(emu, name + ".url")
            if os.path.exists(marker):
                try:
                    src = open(marker).read().strip()
                except OSError:
                    pass
            prev = ""
            pm = os.path.join(emu, name + ".url.alt")
            if os.path.exists(pm):
                try:
                    prev = os.path.basename(open(pm).read().strip())
                except OSError:
                    pass
            out.append({"name": name, "source": src,
                        "version": os.path.basename(src) if src else "",
                        "previous": prev,
                        "can_rollback": os.path.exists(os.path.join(emu, name + ".alt", "AppRun"))})
    except OSError:
        pass
    return out


def _stop_locked():
    p = _current["proc"]
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            p.kill()
    _current.update({"proc": None, "platform": "", "path": ""})


def launch(path, platform, rel="", region=""):
    """(ok, meldung). Einzelplatz: ein laufender Emulator wird zuvor beendet.

    `rel` ist der Pfad RELATIV zur Bibliothekswurzel und hat Vorrang. Ein absoluter
    Pfad bedeutet in zwei Containern nicht dasselbe: haengt der eine die Bibliothek
    unter einem anderen Punkt ein, zeigt er ins Leere. Relativ ist die einzige Angabe,
    die auf beiden Seiten dieselbe Datei benennt — vorausgesetzt, beide meinen
    dieselbe WURZEL, und genau das ist die Bedingung, die dokumentiert gehoert.

    `rel` is relative to the library root and takes precedence: an absolute path does
    not mean the same thing in two containers that mount the library differently."""
    cmd = EMULATORS.get(platform) or ""
    if not cmd:
        return False, f"kein Emulator fuer '{platform}' hinterlegt / no emulator configured"

    if rel:
        path = os.path.join(ROMS, rel)   # Ausbruchsversuche faengt die Pruefung unten

    # Der Pfad kommt von aussen. Nach Aufloesung der Symlinks MUSS er unter ROMS liegen —
    # sonst waere dies ein Fernstart fuer beliebige Dateien auf dem Host. Geprueft wird die
    # AUFGELOESTE Form (realpath), sonst genuegt ein Symlink oder ein '..' zum Ausbrechen.
    real = _in_bibliothek(path)
    if not real:
        return False, "Pfad ausserhalb der Bibliothek / path outside the library"
    if not os.path.exists(real):
        # Der haeufigste Grund ist KEIN fehlendes Spiel, sondern zwei Container, die
        # ihre Bibliothek an verschiedenen Stellen einhaengen. Das gehoert in die
        # Meldung, sonst sucht der Betreiber die Datei statt die Einhaengung.
        # The usual cause is two containers mounting the library differently.
        return False, (f"Datei nicht gefunden / file not found: {real} — "
                       "haengen Romseerr und der Streaming-Host DIESELBE "
                       "Bibliothekswurzel ein? / do both mount the same library root?")

    # Ein Titel ist nicht immer eine Datei. Eine PS3-Disc ist ein ORDNER mit
    # PS3_DISC.SFB und PS3_GAME/USRDIR/EBOOT.BIN darin — nachgemessen, 13 von 17
    # Titeln der Testbibliothek. Die frueher hier stehende Pruefung auf `isfile`
    # hat solche Titel abgewiesen, und zwar mit der Meldung ueber verschiedene
    # Einhaengepunkte: eine PLAUSIBLE, aber falsche Faehrte, die genau in die
    # falsche Richtung schickt.
    #
    # A title is not always a file: a PS3 disc is a directory. The previous `isfile`
    # check rejected those with a message about differing mount points — plausible
    # and wrong, which is the worst kind of error message.
    if os.path.isdir(real):
        boot = _bootdatei(real, platform)
        if not boot:
            return False, (f"Ordner ohne startbaren Inhalt / folder has no bootable file: "
                           f"{os.path.basename(real)}")
        # ERNEUT pruefen. Der Ordner liegt in der Bibliothek, die Startdatei darin muss
        # es deshalb noch lange nicht: ein Symlink genuegt, um heraus zu zeigen.
        # The folder being inside the library says nothing about a symlink within it.
        real = _in_bibliothek(boot)
        if not real:
            return False, ("Startdatei zeigt aus der Bibliothek heraus / "
                           "boot file points outside the library")

    # Controller-Belegung setzen, bevor der Emulator die Konfiguration liest. Scheitert
    # das, wird trotzdem gestartet: ohne Pad spielen ist schlechter als gar nicht
    # spielen — aber nur ein bisschen, und die Meldung steht im Log.
    # Applied before the emulator reads its config; a failure here does not block the
    # launch, it is logged.
    profil = PROFILE_EMU.get(platform)
    if profil and os.path.isfile(PROFILE_SCRIPT):
        # Controller immer, BIOS nur wenn eine Region bekannt ist. Ohne Region raten
        # waere schlimmer als nichts zu tun: ein falsches BIOS meldet sich nicht,
        # es laeuft nur "komisch".
        # Guessing a region would be worse than leaving it: a wrong BIOS does not
        # announce itself, the game merely behaves oddly.
        # Reihenfolge: Controller, BIOS, Vollbild — alles BEVOR der Emulator seine
        # Konfiguration liest. Danach zu setzen hiesse, gegen einen laufenden Prozess
        # zu arbeiten, der seine eigene Geometrie zurueckschreibt.
        auftraege = [["--apply", profil], ["--fullscreen", profil]]
        if region:
            auftraege.insert(1, ["--bios", profil, region])
        for a in auftraege:
            try:
                r = subprocess.run([sys.executable, PROFILE_SCRIPT] + a,
                                   capture_output=True, text=True, timeout=30)
                print((r.stdout + r.stderr).strip(), flush=True)
            except (subprocess.TimeoutExpired, OSError) as e:
                print(f"[profil] {profil}: {e.__class__.__name__}", flush=True)

    # argv ist damit: fester Befehl aus der Umgebung (der Betreiber setzt ihn) + genau EIN
    # geprueftes Argument aus der Bibliothek. Keine Shell, keine Wortzerlegung durch execve.
    argv = [real if part == "%s" else part for part in shlex.split(cmd)]
    if "%s" not in cmd:
        argv.append(real)
    with _lock:
        _stop_locked()
        try:
            # Kein shell=True: die Argumentliste geht unveraendert an execve.
            _current["proc"] = subprocess.Popen(argv, stdout=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL)
        except OSError as e:
            return False, f"Start fehlgeschlagen / launch failed: {e.__class__.__name__}"
        _current["platform"] = platform
        _current["path"] = real

    # Nur das Emulatorfenster zeigen (#141). Im Hintergrund, weil auf das Fenster bis
    # zu 20 Sekunden gewartet wird — der Aufrufer soll darauf nicht haengen. Schlaegt
    # es fehl, laeuft das Spiel trotzdem: ein Desktop drumherum ist unschoen, ein
    # nicht gestarteter Titel waere schlimmer.
    # Backgrounded because it waits for the window; a failure here must not cost the
    # launch, only the framing.
    if os.path.isfile(PROFILE_SCRIPT):
        pid = _current["proc"].pid
        def _fenster():
            try:
                r = subprocess.run([sys.executable, PROFILE_SCRIPT, "--window", str(pid)],
                                   capture_output=True, text=True, timeout=60)
                print((r.stdout + r.stderr).strip(), flush=True)
            except (subprocess.TimeoutExpired, OSError) as e:
                print(f"[fenster] {e.__class__.__name__}", flush=True)
        threading.Thread(target=_fenster, daemon=True).start()
    return True, os.path.basename(real)


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorised(self, query):
        if not TOKEN:
            return False
        supplied = (self.headers.get("X-Stream-Token")
                    or (query.get("token") or [""])[0])
        # Konstante Laufzeit: kein Rueckschluss auf das Token ueber die Antwortzeit.
        import hmac
        return hmac.compare_digest(str(supplied), TOKEN)

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if not self._authorised(q):
            return self._reply(401, {"ok": False, "msg": "unauthorised"})
        if u.path not in ("/launch", "/stop", "/update", "/rollback", "/install",
                          "/firmware/upload", "/firmware/vendor"):
            return self._reply(404, {"ok": False, "msg": "not found"})
        if u.path == "/firmware/vendor":
            if _vendor["running"]:
                return self._reply(409, {"ok": False, "msg": "laeuft bereits / already running"})
            plat = (q.get("platform") or [""])[0]
            # Herstellerbezug gibt es nur da, wo der Hersteller wirklich ausliefert.
            # Vita3K laedt NICHTS herunter - der Quelltext oeffnet einen Dateidialog.
            if plat != "ps3":
                return self._reply(400, {"ok": False, "reason": "no_vendor_source",
                                         "msg": "Herstellerbezug nur fuer ps3 / vendor fetch only for ps3"})
            threading.Thread(target=run_vendor, args=(plat,), daemon=True).start()
            return self._reply(200, {"ok": True, "msg": "gestartet / started"})
        if u.path == "/firmware/upload":
            return self._firmware_upload(q)
        if u.path == "/stop":
            with _lock:
                _stop_locked()
            # Panel zurueckholen: ein dauerhaft verstecktes Panel macht den Host
            # unbenutzbar fuer alles, was eine GUI braucht — etwa das Einrichten eines
            # Emulators. Was eine Sitzung aendert, raeumt sie auch wieder weg.
            # A permanently hidden panel would make the host unusable for setup work.
            if os.path.isfile(PROFILE_SCRIPT):
                try:
                    subprocess.run([sys.executable, PROFILE_SCRIPT, "--desktop"],
                                   capture_output=True, timeout=20)
                except (subprocess.TimeoutExpired, OSError):
                    pass
            return self._reply(200, {"ok": True})
        if u.path == "/update":
            if _update["running"]:
                return self._reply(409, {"ok": False, "msg": "laeuft bereits / already running"})
            threading.Thread(target=run_update, daemon=True).start()
            return self._reply(200, {"ok": True, "msg": "gestartet / started"})
        if u.path == "/install":
            if _update["running"]:
                return self._reply(409, {"ok": False, "msg": "laeuft bereits / already running"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                d = json.loads(self.rfile.read(min(n, 4096)) or b"{}")
            except (ValueError, OSError):
                return self._reply(400, {"ok": False, "msg": "kein gueltiges JSON / invalid JSON"})
            name = str(d.get("name") or "")
            # Der Name geht in eine Argumentliste; nur was ein Ordnername sein darf,
            # und er muss im Katalog stehen. Zwei Pruefungen, weil die erste
            # Zeichenklassen kennt und die zweite die Wirklichkeit.
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", name):
                return self._reply(400, {"ok": False, "msg": "unzulaessiger Name / invalid name"})
            if name not in {e.get("dir") for e in catalogue()}:
                return self._reply(404, {"ok": False, "msg": "nicht im Katalog / not in catalogue"})
            threading.Thread(target=run_install, args=(name,), daemon=True).start()
            return self._reply(200, {"ok": True, "msg": "gestartet / started"})
        if u.path == "/rollback":
            # Zurueck zur vorigen Fassung. Der Name kommt von aussen und geht in eine
            # Argumentliste — deshalb nur Zeichen, die ein Ordnername haben darf.
            # The name comes from outside; restrict it to plausible directory names.
            try:
                n = int(self.headers.get("Content-Length") or 0)
                d = json.loads(self.rfile.read(min(n, 4096)) or b"{}")
            except (ValueError, OSError):
                return self._reply(400, {"ok": False, "msg": "kein gueltiges JSON / invalid JSON"})
            name = str(d.get("name") or "")
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", name):
                return self._reply(400, {"ok": False, "msg": "unzulaessiger Name / invalid name"})
            r = subprocess.run(["/bin/bash", UPDATE_SCRIPT, "--rollback", name],
                               capture_output=True, text=True, timeout=120)
            return self._reply(200 if r.returncode == 0 else 400,
                               {"ok": r.returncode == 0,
                                "msg": (r.stdout + r.stderr).strip()[-400:]})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(min(n, 65536)) or b"{}")
        except (ValueError, OSError):
            return self._reply(400, {"ok": False, "msg": "kein gueltiges JSON / invalid JSON"})
        ok, msg = launch(str(d.get("path") or ""), str(d.get("platform") or ""),
                         str(d.get("rel") or ""), str(d.get("region") or "")[:32])
        return self._reply(200 if ok else 400, {"ok": ok, "msg": msg})

    def _firmware_upload(self, q):
        """Rohe Datei im Rumpf, Plattform und Name in der Abfrage. Kein Multipart:
        das waere ein Parser mehr in einem Dienst, der Prozesse startet — und der
        Aufrufer ist Romseerr, kein Browser-Formular.
        Raw body, no multipart: one parser less in a service that spawns processes."""
        plat = (q.get("platform") or [""])[0]
        name = (q.get("name") or [""])[0]
        if plat not in firmware_platforms():
            return self._reply(400, {"ok": False, "reason": "bad_platform"})
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name or ""):
            return self._reply(400, {"ok": False, "reason": "bad_name"})
        try:
            laenge = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._reply(400, {"ok": False, "reason": "bad_length"})
        if laenge <= 0:
            return self._reply(400, {"ok": False, "reason": "empty"})
        if laenge > MAX_UPLOAD:
            return self._reply(413, {"ok": False, "reason": "too_large",
                                     "limit": MAX_UPLOAD})

        # In eine temporaere Datei schreiben und erst dann dem Skript uebergeben:
        # ein abgebrochener Upload darf keine halbe Firmware in der Ablage hinterlassen,
        # die spaeter als "vorhanden" durchgeht.
        # Write to a temp file first; an aborted upload must not leave half a firmware
        # in place that later reads as "present".
        tmp = tempfile.NamedTemporaryFile(delete=False, prefix="fw-", suffix=".part")
        gelesen = 0
        try:
            while gelesen < laenge:
                block = self.rfile.read(min(65536, laenge - gelesen))
                if not block:
                    break
                tmp.write(block); gelesen += len(block)
            tmp.close()
            if gelesen != laenge:
                return self._reply(400, {"ok": False, "reason": "short_body",
                                         "expected": laenge, "got": gelesen})
            r = subprocess.run(["/bin/bash", FIRMWARE_SCRIPT, "--import", plat, tmp.name, name],
                               capture_output=True, text=True, timeout=300)
            return self._reply(200 if r.returncode == 0 else 400,
                               {"ok": r.returncode == 0,
                                "log": (r.stdout + r.stderr)[-4000:],
                                "status": firmware_status()})
        except (OSError, subprocess.TimeoutExpired) as e:
            return self._reply(500, {"ok": False, "reason": e.__class__.__name__})
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path not in ("/status", "/update", "/catalog", "/firmware"):
            return self._reply(404, {"ok": False, "msg": "not found"})
        if not self._authorised(parse_qs(u.query)):
            return self._reply(401, {"ok": False, "msg": "unauthorised"})
        if u.path == "/firmware":
            return self._reply(200, {"ok": True, **firmware_status(),
                                     "vendor": dict(_vendor)})
        if u.path == "/catalog":
            return self._reply(200, {"ok": True, "catalog": catalogue(),
                                     "busy": _update["running"],
                                     "target": _update.get("target", "")})
        if u.path == "/update":
            return self._reply(200, {"ok": True, **{k: v for k, v in _update.items()},
                                     "emulators": installed_emulators(),
                                     "catalog": catalogue()})
        p = _current["proc"]
        return self._reply(200, {"ok": True, "running": bool(p and p.poll() is None),
                                 "platform": _current["platform"],
                                 "file": os.path.basename(_current["path"]) if _current["path"] else "",
                                 "platforms": sorted(k for k, v in EMULATORS.items() if v),
                                 "emulators": installed_emulators(),
                                 "update_running": _update["running"]})

    def log_message(self, *_a):
        pass   # keine Zugriffsprotokolle auf stderr


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("STREAM_AGENT_TOKEN ist nicht gesetzt — der Dienst startet Prozesse und "
                 "laeuft nicht ungeschuetzt. / refusing to run without a token.")
    print(f"stream-agent auf :{PORT}, Bibliothek {ROMS}, "
          f"Plattformen: {', '.join(sorted(k for k, v in EMULATORS.items() if v))}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()  # nosec B104 - Container-Dienst
