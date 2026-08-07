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
EMULATORS = {
    "ps2":     os.environ.get("EMU_PS2", "/config/emulators/PCSX2.AppImage -- %s"),
    "ngc":     os.environ.get("EMU_GC", "/usr/games/dolphin-emu -b -e %s"),
    "wii":     os.environ.get("EMU_GC", "/usr/games/dolphin-emu -b -e %s"),
    "wiiu":    os.environ.get("EMU_WIIU", ""),
    "switch":  os.environ.get("EMU_SWITCH", "/config/emulators/Eden.AppImage -f -g %s"),
    "3ds":     os.environ.get("EMU_3DS", ""),
    "dreamcast": os.environ.get("EMU_DC", ""),
}

_current = {"proc": None, "platform": "", "path": ""}
_lock = threading.Lock()


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

    real = os.path.realpath(path)
    # Der Pfad kommt von aussen. Nach Aufloesung der Symlinks MUSS er unter ROMS liegen —
    # sonst waere dies ein Fernstart fuer beliebige Dateien auf dem Host.
    if not (real == ROMS or real.startswith(ROMS + os.sep)):
        return False, "Pfad ausserhalb der Bibliothek / path outside the library"
    if not os.path.isfile(real):
        return False, "Datei nicht gefunden / file not found"

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
        if u.path not in ("/launch", "/stop"):
            return self._reply(404, {"ok": False, "msg": "not found"})
        if u.path == "/stop":
            with _lock:
                _stop_locked()
            return self._reply(200, {"ok": True})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(min(n, 65536)) or b"{}")
        except (ValueError, OSError):
            return self._reply(400, {"ok": False, "msg": "kein gueltiges JSON / invalid JSON"})
        ok, msg = launch(str(d.get("path") or ""), str(d.get("platform") or ""))
        return self._reply(200 if ok else 400, {"ok": ok, "msg": msg})

    def do_GET(self):
        u = urlparse(self.path)
        if u.path != "/status":
            return self._reply(404, {"ok": False, "msg": "not found"})
        if not self._authorised(parse_qs(u.query)):
            return self._reply(401, {"ok": False, "msg": "unauthorised"})
        p = _current["proc"]
        return self._reply(200, {"ok": True, "running": bool(p and p.poll() is None),
                                 "platform": _current["platform"],
                                 "file": os.path.basename(_current["path"]) if _current["path"] else "",
                                 "platforms": sorted(k for k, v in EMULATORS.items() if v)})

    def log_message(self, *_a):
        pass   # keine Zugriffsprotokolle auf stderr


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("STREAM_AGENT_TOKEN ist nicht gesetzt — der Dienst startet Prozesse und "
                 "laeuft nicht ungeschuetzt. / refusing to run without a token.")
    print(f"stream-agent auf :{PORT}, Bibliothek {ROMS}, "
          f"Plattformen: {', '.join(sorted(k for k, v in EMULATORS.items() if v))}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()  # nosec B104 - Container-Dienst
