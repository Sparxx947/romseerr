#!/usr/bin/env python3
"""Sonde fuer die Gamepad-Bruecke: prueft die ganze Kette OHNE angeschlossenen Controller.

    docker exec -u 0 stream-host python3 /opt/gamepad-bridge-probe.py

Warum es das gibt: Selkies legt seine Gamepad-Sockets nur an, wenn ein Browser ein Pad
meldet. Ohne Controller ist die Bruecke damit gar nicht pruefbar — und "es kommt nichts
an" hat drei moegliche Ursachen, die von aussen gleich aussehen: die Bruecke laeuft nicht,
der Geraeteknoten fehlt im Container, oder die Device-Cgroup verbietet das Oeffnen.

Die Sonde spielt die SELKIES-Seite nach und misst die Wirkung am echten Kernel: sie legt
einen eigenen Socket an, startet eine zweite Bruecken-Instanz darauf, schickt Ereignisse
und liest sie als der Benutzer wieder, unter dem die Emulatoren laufen. Die echten
Sockets bleiben dabei unberuehrt (eigenes Praefix), eine laufende Sitzung stoert sie nicht.

EN: Selkies only creates its gamepad sockets once a browser reports a pad, so without a
controller the bridge cannot be tested at all. This probe emulates the Selkies side and
measures the effect on the real kernel — it never touches the production sockets.
"""
import ctypes, os, socket, struct, subprocess, sys, time

PRAEFIX = "/tmp/romseerr_gamepad_probe_js"
SOCKET_PFAD = PRAEFIX + "0.sock"
BRUECKE = "/opt/selkies-uinput-bridge.py"
EMULATOR_UID = 1000            # `abc` im Webtop-Abbild
KONFIG_GROESSE = 1360

CONTROLLER_NAME_MAX_LEN = 255
INTERPOSER_MAX_BTNS = 512
INTERPOSER_MAX_AXES = 64


class JsConfig(ctypes.Structure):
    """Feldfolge exakt wie in Selkies' `JsConfigCtypes`."""
    _fields_ = [
        ("name", ctypes.c_char * CONTROLLER_NAME_MAX_LEN),
        ("vendor", ctypes.c_uint16),
        ("product", ctypes.c_uint16),
        ("version", ctypes.c_uint16),
        ("num_btns", ctypes.c_uint16),
        ("num_axes", ctypes.c_uint16),
        ("btn_map", ctypes.c_uint16 * INTERPOSER_MAX_BTNS),
        ("axes_map", ctypes.c_uint8 * INTERPOSER_MAX_AXES),
    ]


TASTEN = [304, 305, 307, 308, 310, 311, 314, 315, 316, 317, 318]   # BTN_SOUTH ...
ACHSEN = [0, 1, 2, 3, 4, 5, 16, 17]                                # ABS_X ...
JS_EVENT = struct.Struct("IhBB")
EINGABE_EREIGNIS = struct.Struct("llHHi")     # struct input_event, 24 Byte auf 64 Bit


def konfig_bytes():
    cfg = JsConfig()
    cfg.name = b"Romseerr Probe Pad"
    cfg.vendor, cfg.product, cfg.version = 0x045E, 0x028E, 0x0114
    cfg.num_btns, cfg.num_axes = len(TASTEN), len(ACHSEN)
    for i, b in enumerate(TASTEN):
        cfg.btn_map[i] = b
    for i, a in enumerate(ACHSEN):
        cfg.axes_map[i] = a
    roh = bytes(cfg)
    # Auf dem Draht sind es 1360 Byte, ctypes meldet 1354 — ohne Polsterung wartet die
    # Bruecke ewig auf sechs fehlende Byte.
    return roh + b"\x00" * (KONFIG_GROESSE - len(roh))


def sag(zeichen, text):
    print(f"{zeichen} {text}", flush=True)


def main():
    if not os.path.exists(BRUECKE):
        sag("FEHLER", f"{BRUECKE} fehlt — ist sie im Compose eingehaengt?")
        return 2
    for p in (SOCKET_PFAD,):
        if os.path.exists(p):
            os.unlink(p)

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCKET_PFAD)
    os.chmod(SOCKET_PFAD, 0o666)
    srv.listen(1)
    srv.settimeout(20)

    umgebung = dict(os.environ, SELKIES_JS_SOCKET_PREFIX=PRAEFIX)
    kind = subprocess.Popen([sys.executable, "-u", BRUECKE],
                            env=umgebung, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    try:
        try:
            verbindung, _ = srv.accept()
        except socket.timeout:
            sag("FEHLER", "Die Bruecke hat sich nicht verbunden. Log ansehen:")
            sag("      ", "docker exec stream-host tail -20 /config/gamepad-bridge.log")
            return 1
        sag("OK", "Bruecke verbunden")
        verbindung.sendall(konfig_bytes())

        # Auf den Knoten warten. Die Bruecke legt ihn an, NACHDEM der Kernel das Geraet
        # erzeugt hat — vorher gibt es im Container nichts zu sehen.
        knoten = None
        vorher = set(os.listdir("/dev/input"))
        for _ in range(50):
            time.sleep(0.2)
            neu = set(os.listdir("/dev/input")) - vorher
            treffer = sorted(n for n in neu if n.startswith("event"))
            if treffer:
                knoten = "/dev/input/" + treffer[0]
                break
        if not knoten:
            sag("FEHLER", "Kein neuer Geraeteknoten in /dev/input.")
            sag("      ", "Meist fehlt /dev/uinput oder das Modul auf dem HOST.")
            return 1
        sag("OK", f"Geraeteknoten angelegt: {knoten}")

        # Als der Benutzer lesen, unter dem die Emulatoren laufen — nur das beantwortet
        # die Frage, die zaehlt. Scheitert es hier mit EPERM, fehlt die Cgroup-Regel.
        kind_pid = os.fork()
        if kind_pid == 0:
            os.setgid(EMULATOR_UID)
            os.setuid(EMULATOR_UID)
            try:
                fd = os.open(knoten, os.O_RDONLY | os.O_NONBLOCK)
            except PermissionError:
                os._exit(3)
            except OSError:
                os._exit(4)
            ende, gezaehlt = time.time() + 6, 0
            while time.time() < ende:
                try:
                    daten = os.read(fd, EINGABE_EREIGNIS.size * 64)
                except BlockingIOError:
                    time.sleep(0.05)
                    continue
                for i in range(0, len(daten) - EINGABE_EREIGNIS.size + 1,
                               EINGABE_EREIGNIS.size):
                    _s, _us, typ, _c, _w = EINGABE_EREIGNIS.unpack(
                        daten[i:i + EINGABE_EREIGNIS.size])
                    if typ in (0x01, 0x03):
                        gezaehlt += 1
            os._exit(0 if gezaehlt else 5)

        time.sleep(1)
        for _ in range(12):
            for typ, nummer, wert in ((0x01, 0, 1), (0x01, 0, 0), (0x02, 0, 30000),
                                      (0x02, 0, -30000), (0x02, 0, 0)):
                verbindung.sendall(JS_EVENT.pack(
                    int(time.time() * 1000) & 0xFFFFFFFF, wert, typ, nummer))
            time.sleep(0.3)

        _, zustand = os.waitpid(kind_pid, 0)
        code = os.waitstatus_to_exitcode(zustand)
        if code == 0:
            sag("OK", f"Eingaben kommen als uid {EMULATOR_UID} an — die Kette steht.")
            return 0
        if code == 3:
            sag("FEHLER", f"{knoten} laesst sich als uid {EMULATOR_UID} nicht oeffnen.")
            sag("      ", "Fehlt `device_cgroup_rules: - 'c 13:* rmw'` im Compose?")
        elif code == 4:
            sag("FEHLER", f"{knoten} zeigt ins Leere (kein Geraet dahinter).")
        else:
            sag("FEHLER", "Knoten lesbar, aber es kam kein einziges Ereignis an.")
        return 1
    finally:
        kind.terminate()
        try:
            kind.wait(timeout=5)
        except subprocess.TimeoutExpired:
            kind.kill()
        srv.close()
        if os.path.exists(SOCKET_PFAD):
            os.unlink(SOCKET_PFAD)


if __name__ == "__main__":
    sys.exit(main())
