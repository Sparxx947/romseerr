#!/usr/bin/env python3
"""Bruecke: Selkies-Gamepad-Sockets -> echte Kernel-Geraete ueber uinput. (#119)

WARUM ES DAS GIBT: Selkies reicht Gamepads ueber einen LD_PRELOAD-Interposer weiter.
Die Emulatoren hier sind AppImages mit **statisch gelinkter** Runtime (`AppRun` ist
static-pie) — auf statische Binaerdateien wirkt LD_PRELOAD nicht. Gemessen: im laufenden
Emulator ist kein Interposer geladen, und er sieht null Eingabegeraete, obwohl Selkies das
Pad korrekt annimmt und seine Sockets bedient.

Diese Bruecke verbindet sich genau so wie der Interposer als Client an die Sockets, liest
die Geraetebeschreibung und legt daraus ein **echtes** Eingabegeraet an. Danach braucht
kein Prozess mehr ein Preloading — ein Kernel-Geraet sieht jeder, unabhaengig davon, wie
er verpackt ist.

EN: Selkies hands gamepads over through an LD_PRELOAD interposer, which cannot reach
AppImages with a statically linked runtime. This bridge speaks the same socket protocol
and creates real kernel devices instead, which every process can see.

Das Protokoll stammt aus Selkies' eigenem `input_handler.py` (JsConfigCtypes) und
`joystick_interposer.c`, nicht aus einer Vermutung.
"""
import ctypes, logging, os, signal, socket, struct, sys, threading, time

from evdev import UInput, ecodes, AbsInfo

CONTROLLER_NAME_MAX_LEN = 255
INTERPOSER_MAX_BTNS = 512
INTERPOSER_MAX_AXES = 64
SOCKETS = [f"/tmp/selkies_js{i}.sock" for i in range(4)]

# Die C-Struktur ist auf 8 Byte endausgerichtet und damit 1360 Byte gross, waehrend die
# ctypes-Fassung 1354 meldet — Selkies fuehrt beide Zahlen selbst (`C_INTERPOSER_STRUCT_SIZE`
# gegen `sizeof(JsConfigCtypes)`). Ueber den Socket kommen 1360. Laese man nur 1354, blieben
# 6 Byte im Puffer und ALLE folgenden Ereignisse waeren um 6 Byte verschoben: Tasten und
# Achsen wuerden vertauscht, ohne dass irgendwo ein Fehler auftritt.
# EN: the C struct is padded to 1360; reading only ctypes' 1354 would shift every
# subsequent event by six bytes, silently swapping buttons and axes.
KONFIG_GROESSE = 1360

log = logging.getLogger("uinput-bridge")

# Ereignisse auf den js-Sockets: struct js_event { __u32 time; __s16 value;
# __u8 type; __u8 number; } — 8 Byte, Format 'IhBB'.
JS_EVENT = struct.Struct("IhBB")
JS_EVENT_BUTTON = 0x01
JS_EVENT_AXIS = 0x02
JS_EVENT_INIT = 0x80          # Anfangszustand, kein echter Tastendruck


class JsConfig(ctypes.Structure):
    """Geraetebeschreibung, die Selkies beim Verbinden schickt. Feldfolge exakt wie in
    Selkies' `JsConfigCtypes` — weicht sie ab, liest man Muell und legt ein Phantomgeraet
    an."""
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


def geraet_anlegen(cfg):
    """Aus der Beschreibung ein uinput-Geraet bauen.

    Die Achsen bekommen den Wertebereich eines Joysticks (-32767..32767); Trigger und
    Steuerkreuz melden sich ueber dieselbe Achsenliste, deshalb wird nicht unterschieden —
    was Selkies als Achse fuehrt, wird eine Achse.
    """
    tasten = [cfg.btn_map[i] for i in range(cfg.num_btns)]
    achsen = [cfg.axes_map[i] for i in range(cfg.num_axes)]
    faehigkeiten = {
        ecodes.EV_KEY: tasten,
        ecodes.EV_ABS: [(a, AbsInfo(value=0, min=-32767, max=32767,
                                    fuzz=0, flat=0, resolution=0)) for a in achsen],
    }
    name = cfg.name.decode("utf-8", "replace").strip("\x00") or "Selkies Gamepad"
    return UInput(faehigkeiten, name=name, vendor=cfg.vendor,
                  product=cfg.product, version=cfg.version), name, tasten, achsen


def bediene(pfad):
    """Einen Socket bedienen: verbinden, Beschreibung lesen, Geraet anlegen, weiterreichen.

    Bricht die Verbindung ab, wird das Geraet abgeraeumt und neu verbunden — Selkies legt
    die Sockets bei jeder neuen Sitzung neu an, und ein Geraet, das auf einen toten Socket
    zeigt, waere schlimmer als keines.
    """
    while True:
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect(pfad)
            roh = b""
            while len(roh) < KONFIG_GROESSE:
                teil = s.recv(KONFIG_GROESSE - len(roh))
                if not teil:
                    raise ConnectionError("Verbindung beim Lesen der Beschreibung verloren")
                roh += teil
            cfg = JsConfig.from_buffer_copy(roh)
            ui, name, tasten, achsen = geraet_anlegen(cfg)
            # `ui.device` ist bei python-evdev nicht garantiert gesetzt — es hier
            # ungeprueft zu lesen hat die Verbindung abgeschossen, NACHDEM das Geraet
            # bereits stand. Eine Diagnosezeile darf niemals der Grund sein, dass etwas
            # nicht funktioniert. / a logging line must never be the reason something fails.
            pfad_geraet = getattr(getattr(ui, "device", None), "path", "?")
            log.info("%s: Geraet '%s' angelegt (%d Tasten, %d Achsen) -> %s",
                     os.path.basename(pfad), name, len(tasten), len(achsen), pfad_geraet)
            s.settimeout(None)
            puffer = b""
            while True:
                teil = s.recv(4096)
                if not teil:
                    raise ConnectionError("Socket geschlossen")
                puffer += teil
                while len(puffer) >= JS_EVENT.size:
                    _zeit, wert, typ, nummer = JS_EVENT.unpack(puffer[:JS_EVENT.size])
                    puffer = puffer[JS_EVENT.size:]
                    if typ & JS_EVENT_INIT:
                        continue          # Anfangszustand, kein Druck
                    if typ & JS_EVENT_BUTTON and nummer < len(tasten):
                        ui.write(ecodes.EV_KEY, tasten[nummer], 1 if wert else 0)
                        ui.syn()
                    elif typ & JS_EVENT_AXIS and nummer < len(achsen):
                        ui.write(ecodes.EV_ABS, achsen[nummer], wert)
                        ui.syn()
        except Exception as e:
            log.info("%s: %s — neuer Versuch in 3 s", os.path.basename(pfad), e)
        finally:
            try: ui.close()
            except Exception: pass
            try: s.close()
            except Exception: pass
        time.sleep(3)


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    try:
        os.close(os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK))
    except OSError as e:
        log.error("/dev/uinput nicht nutzbar: %s — Modul geladen? Geraet durchgereicht?", e)
        return 1
    for pfad in SOCKETS:
        threading.Thread(target=bediene, args=(pfad,), daemon=True).start()
    log.info("Bruecke laeuft fuer %d Sockets", len(SOCKETS))
    signal.pause()
    return 0


if __name__ == "__main__":
    sys.exit(main())
