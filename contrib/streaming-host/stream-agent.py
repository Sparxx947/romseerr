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

# Emulator-Aktualisierung. Laeuft im Hintergrund, damit der Aufrufer nicht minutenlang
# auf einer HTTP-Antwort haengt — Downloads sind hier hunderte Megabyte.
# Runs in the background; downloads are hundreds of megabytes.
UPDATE_SCRIPT = os.environ.get("EMU_UPDATE_SCRIPT", "/custom-cont-init.d/20-emulators")
_update = {"running": False, "started": 0, "finished": 0, "rc": None, "log": ""}


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


def launch(path, platform):
    """(ok, meldung). Einzelplatz: ein laufender Emulator wird zuvor beendet."""
    cmd = EMULATORS.get(platform) or ""
    if not cmd:
        return False, f"kein Emulator fuer '{platform}' hinterlegt / no emulator configured"

    # Der Pfad kommt von aussen. Nach Aufloesung der Symlinks MUSS er unter ROMS liegen —
    # sonst waere dies ein Fernstart fuer beliebige Dateien auf dem Host. Geprueft wird die
    # AUFGELOESTE Form (realpath), sonst genuegt ein Symlink oder ein '..' zum Ausbrechen.
    try:
        real = os.path.realpath(path)
        if os.path.commonpath([real, ROMS]) != ROMS:
            raise ValueError
    except (ValueError, OSError):
        return False, "Pfad ausserhalb der Bibliothek / path outside the library"
    if not os.path.isfile(real):
        return False, "Datei nicht gefunden / file not found"

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
        if u.path not in ("/launch", "/stop", "/update", "/rollback"):
            return self._reply(404, {"ok": False, "msg": "not found"})
        if u.path == "/stop":
            with _lock:
                _stop_locked()
            return self._reply(200, {"ok": True})
        if u.path == "/update":
            if _update["running"]:
                return self._reply(409, {"ok": False, "msg": "laeuft bereits / already running"})
            threading.Thread(target=run_update, daemon=True).start()
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
        ok, msg = launch(str(d.get("path") or ""), str(d.get("platform") or ""))
        return self._reply(200 if ok else 400, {"ok": ok, "msg": msg})

    def do_GET(self):
        u = urlparse(self.path)
        if u.path not in ("/status", "/update"):
            return self._reply(404, {"ok": False, "msg": "not found"})
        if not self._authorised(parse_qs(u.query)):
            return self._reply(401, {"ok": False, "msg": "unauthorised"})
        if u.path == "/update":
            return self._reply(200, {"ok": True, **{k: v for k, v in _update.items()},
                                     "emulators": installed_emulators()})
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
