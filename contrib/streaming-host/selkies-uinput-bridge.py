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
import ctypes, fcntl, logging, os, signal, socket, struct, sys, threading, time

from evdev import UInput, ecodes, AbsInfo

CONTROLLER_NAME_MAX_LEN = 255
INTERPOSER_MAX_BTNS = 512
INTERPOSER_MAX_AXES = 64
# Ueberschreibbar, damit sich die Bruecke pruefen laesst, ohne die echten Sockets zu
# belegen: ein Testlauf auf `/tmp/selkies_js0.sock` wuerde eine spaetere Selkies-Sitzung
# blockieren. / EN: overridable so a test run never squats on the real socket paths.
SOCKET_PRAEFIX = os.environ.get("SELKIES_JS_SOCKET_PREFIX", "/tmp/selkies_js")
SOCKETS = [f"{SOCKET_PRAEFIX}{i}.sock" for i in range(4)]

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

# --- Geraeteknoten im Container -------------------------------------------------------
#
# GEMESSEN am 2026-08-10, und der Grund fuer diesen ganzen Abschnitt: uinput legt das
# Geraet im **Kernel** an, also erscheint es im devtmpfs des HOSTS (`/dev/input/event3`,
# `js0`). Der Container hat aber ein eigenes `/dev` — dort taucht **nichts** auf, und
# genau dort laufen die Emulatoren. Ohne Knoten ist das Geraet fuer sie nicht vorhanden.
#
# Sichtbar ist es trotzdem: `/sys` ist im Container gemountet und fuehrt das frische
# Geraet samt seiner Geraetenummer (`/sys/devices/virtual/input/<sysname>/event3/dev`
# -> `13:67`). Daraus laesst sich der Knoten selbst anlegen; `mknod` ist erlaubt, weil
# CAP_MKNOD in Dockers Standardsatz steckt (der Container ist NICHT privilegiert).
#
# EN: uinput creates the device in the kernel, so the node appears in the HOST's devtmpfs
# while the emulators live in the container's own /dev. /sys is visible inside, carries
# the device number, and CAP_MKNOD is part of Docker's default set — so the bridge
# creates the matching nodes itself.

SYSFS_INPUT = "/sys/devices/virtual/input"
DEV_INPUT = "/dev/input"

# UI_GET_SYSNAME(len) = _IOC(_IOC_READ, 'U', 44, len) aus linux/uinput.h.
# _IOC(dir, type, nr, size) = (dir << 30) | (size << 16) | (type << 8) | nr
_SYSNAME_LEN = 64
UI_GET_SYSNAME = (2 << 30) | (_SYSNAME_LEN << 16) | (ord("U") << 8) | 44


def sysname_lesen(fd):
    """Den sysfs-Namen des eben angelegten Geraets erfragen (z. B. `input40`).

    **Warum nicht ueber den Geraetenamen suchen:** Selkies meldet alle vier Pads unter
    demselben Namen. Ein Suchlauf ueber `/sys/.../name` traefe bei zwei verbundenen
    Controllern das falsche Geraet — und zwar lautlos, mit vertauschten Spielern. Der
    Kernel beantwortet die Frage eindeutig, also wird er gefragt.
    EN: all four pads share one name, so searching sysfs by name would silently mix up
    players; the kernel answers unambiguously.
    """
    puffer = bytearray(_SYSNAME_LEN)
    fcntl.ioctl(fd, UI_GET_SYSNAME, puffer)
    return puffer.split(b"\x00", 1)[0].decode()


def knoten_spiegeln(sysname):
    """Zu jedem Handler (`eventN`, `jsN`) einen Knoten im Container-`/dev/input` anlegen.

    Liefert `(angelegt, schon_richtig)`. Entfernt werden spaeter NUR die selbst
    angelegten; was die Bruecke vorgefunden hat, fasst sie beim Aufraeumen nicht an.
    `schon_richtig` gibt es, damit das Log den Unterschied benennen kann: ein blosses
    "Knoten: KEINE" liest sich wie ein Fehlschlag, obwohl der Knoten bereits auf genau
    dieses Geraet zeigt — der haeufige Fall nach einem Neuverbinden, weil der Kernel
    dieselben Nummern erneut vergibt.
    EN: returns (created, already_correct); only the created ones are removed later.
    Reporting them separately keeps "none" from reading like a failure.
    """
    verzeichnis = os.path.join(SYSFS_INPUT, sysname)
    angelegt = []
    schon_richtig = []
    os.makedirs(DEV_INPUT, exist_ok=True)
    for eintrag in sorted(os.listdir(verzeichnis)):
        if not eintrag.startswith(("event", "js")):
            continue
        dev_datei = os.path.join(verzeichnis, eintrag, "dev")
        if not os.path.exists(dev_datei):
            continue
        with open(dev_datei) as f:
            major, minor = (int(t) for t in f.read().strip().split(":"))
        ziel = os.path.join(DEV_INPUT, eintrag)
        geraetenummer = os.makedev(major, minor)
        try:
            vorhanden = os.stat(ziel)
        except FileNotFoundError:
            vorhanden = None
        if vorhanden is not None:
            if vorhanden.st_rdev == geraetenummer:
                schon_richtig.append(ziel)
                continue            # zeigt schon auf dasselbe Geraet / already correct
            # Selkies legt js0..js3 als Attrappen an; sie tragen dieselben Namen und
            # zeigen ins Leere. Ersetzt wird nur, was auf etwas ANDERES zeigt, und es
            # wird protokolliert — ein stilles Ueberschreiben in /dev waere gefaehrlich.
            log.info("%s zeigte auf %d:%d, wird ersetzt", ziel,
                     os.major(vorhanden.st_rdev), os.minor(vorhanden.st_rdev))
            os.unlink(ziel)
        os.mknod(ziel, 0o600 | 0o020000, geraetenummer)   # 0o020000 = S_IFCHR
        # Die Emulatoren laufen als `abc` (uid 1000), die Bruecke als root. Ohne
        # Leserecht fuer alle waere das Geraet da und trotzdem unbenutzbar — der
        # Fehlerfall, der wie ein Treiberproblem aussieht.
        os.chmod(ziel, 0o666)
        angelegt.append(ziel)
    return angelegt, schon_richtig


# Alle selbst angelegten Knoten, damit auch ein Abbruch von aussen sie wieder loswird.
# OHNE DAS bleiben sie liegen: `terminate` beendet den Prozess, das `finally` im
# Arbeitsthread laeuft dann nicht mehr. Gemessen — nach einem Neustart der Bruecke im
# laufenden Container standen `event7` und `js4` verwaist da und zeigten ins Leere.
# EN: a terminated process never runs the worker's finally block, leaving nodes that
# point at destroyed devices.
ALLE_KNOTEN = []
KNOTEN_SPERRE = threading.Lock()


def knoten_entfernen(pfade):
    """Selbst angelegte Knoten wieder abraeumen.

    Ein Knoten, der auf ein abgeraeumtes Geraet zeigt, ist schlimmer als keiner: SDL
    findet ihn, oeffnet ihn und meldet ein Pad, das nie etwas sendet.
    EN: a node pointing at a destroyed device is worse than none — SDL would offer a
    controller that never sends anything.
    """
    for p in pfade:
        try:
            os.unlink(p)
        except OSError as e:
            log.info("Knoten %s liess sich nicht entfernen: %s", p, e)
        with KNOTEN_SPERRE:
            if p in ALLE_KNOTEN:
                ALLE_KNOTEN.remove(p)


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


# python-evdev sucht im Konstruktor von `UInput` den Geraeteknoten — den es hier noch
# gar nicht geben KANN, weil erst dieses Programm ihn anlegt (siehe `knoten_spiegeln`).
# Die Suche scheitert also, faellt auf ein Rateverfahren zurueck und greift die
# naechstbeste Datei in /dev/input: eine von Selkies' Attrappen `event1000..1003`.
# Die zeigen ins Leere, und der Konstruktor stirbt mit ENXIO — NACHDEM der Kernel das
# Geraet bereits erzeugt hat.
#
# GEMESSEN, und es hat sich erst nach der Geraetefreigabe gezeigt: vorher scheiterte
# derselbe Zugriff mit EPERM, und EPERM faengt python-evdev ab. Eine Freigabe hat also
# einen Fehler sichtbar gemacht, der die ganze Zeit da war.
#
# Die Suche wird deshalb abgeschaltet. `ui.device` wird hier nirgends gebraucht —
# geschrieben wird ueber `ui.write`/`ui.syn`, und `close()` und `capabilities()` pruefen
# selbst auf None. Der sysfs-Name kommt vom Kernel (`UI_GET_SYSNAME`), nicht aus Raten.
#
# EN: python-evdev's constructor looks for a device node that cannot exist yet, because
# this program creates it afterwards. It then falls back to guessing and picks one of
# Selkies' dummy nodes, dying with ENXIO after the kernel device was already created.
# We do not need ui.device at all, so the lookup is disabled.
UInput._find_device = lambda self, fd: None


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


def bediene(pfad, bereit=None):
    """Einen Socket bedienen: verbinden, Beschreibung lesen, Geraet anlegen, weiterreichen.

    Bricht die Verbindung ab, wird das Geraet abgeraeumt und neu verbunden — Selkies legt
    die Sockets bei jeder neuen Sitzung neu an, und ein Geraet, das auf einen toten Socket
    zeigt, waere schlimmer als keines.
    """
    while True:
        ui = None
        s = None
        knoten = []
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
            # HANDSHAKE, ohne den GAR NICHTS fliesst: Selkies liest nach der Beschreibung
            # genau EIN Byte — `sizeof(long)` des Clients — und nimmt den Client erst
            # DANACH in seine aktive Liste auf (`clients_dict[writer]`). Nur an diese
            # Liste werden Ereignisse verteilt.
            #
            # Ohne das Byte verhaelt sich alles unauffaellig: Verbindung steht,
            # Beschreibung kommt an, das Geraet entsteht — und es passiert nie etwas.
            # Im Selkies-Log steht dann als einziger Hinweis
            # "Writer not found in active list during finally block".
            # Abgelesen in selkies/input_handler.py `_handle_interposer_client`.
            #
            # EN: Selkies reads exactly one byte (the client's sizeof(long)) after the
            # config and only then adds the client to the list it broadcasts events to.
            # Without it everything looks connected and nothing ever arrives.
            s.sendall(struct.pack("=B", ctypes.sizeof(ctypes.c_long)))
            ui, name, tasten, achsen = geraet_anlegen(cfg)
            # `ui.device` ist bei python-evdev nicht garantiert gesetzt — es hier
            # ungeprueft zu lesen hat die Verbindung abgeschossen, NACHDEM das Geraet
            # bereits stand. Eine Diagnosezeile darf niemals der Grund sein, dass etwas
            # nicht funktioniert. / a logging line must never be the reason something fails.
            # `ui.device.path` wird hier bewusst NICHT protokolliert: python-evdev sucht
            # den Pfad im /dev des CONTAINERS, wo das frische Geraet noch gar nicht steht
            # — und trifft dann Selkies' letzte Attrappe. Gemessen: alle vier Bruecken
            # meldeten `/dev/input/event1003`. Eine falsche, aber glaubwuerdige Angabe
            # kostet mehr als gar keine. Der sysfs-Name kommt dagegen vom Kernel.
            # EN: python-evdev guesses the path inside the container's /dev and hits a
            # Selkies dummy; the sysfs name comes from the kernel and is unambiguous.
            # Der Knoten muss stehen, BEVOR ein Emulator startet: im Container laeuft
            # kein udev, also merkt ein bereits laufendes SDL-Programm nichts von einem
            # spaeter erscheinenden Geraet. Deshalb legt die Bruecke ihn sofort an und
            # laeuft dauerhaft mit — die Reihenfolge ist Pad verbinden, dann Spiel starten.
            # EN: no udev inside the container, so a running SDL process never notices a
            # device that shows up later; the node must exist before the emulator starts.
            sysname = sysname_lesen(ui.fd)
            knoten, vorhanden = knoten_spiegeln(sysname)
            with KNOTEN_SPERRE:
                ALLE_KNOTEN.extend(knoten)
            log.info("%s: Geraet '%s' angelegt (%d Tasten, %d Achsen), %s, "
                     "Knoten neu: %s, bereits richtig: %s",
                     os.path.basename(pfad), name, len(tasten), len(achsen), sysname,
                     ", ".join(knoten) or "—", ", ".join(vorhanden) or "—")
            if bereit is not None:
                bereit.set()          # der naechste Socket darf sein Geraet anlegen
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
            # Erst den Knoten wegnehmen, dann das Geraet zerstoeren: umgekehrt gaebe es
            # ein Zeitfenster, in dem ein Programm einen Knoten oeffnet, hinter dem
            # nichts mehr steht. / EN: node first, device second — the other order leaves
            # a window in which a program can open a node with nothing behind it.
            knoten_entfernen(knoten)
            if ui is not None:
                try: ui.close()
                except Exception: pass
            if s is not None:
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
    # Beim Beenden aufraeumen. Die Arbeitsthreads sind `daemon=True`, ihr `finally`
    # laeuft beim Prozessende NICHT — ohne diesen Handler bleiben die Knoten stehen und
    # zeigen auf Geraete, die es nicht mehr gibt. Das ist schlimmer als kein Knoten:
    # ein Emulator findet ihn, oeffnet ihn und meldet ein Pad, das nie etwas sendet.
    # EN: daemon threads never run their finally on exit; without this the nodes survive
    # their devices and SDL offers a controller that stays silent forever.
    def aufraeumen(signum, rahmen):
        with KNOTEN_SPERRE:
            rest = list(ALLE_KNOTEN)
        if rest:
            log.info("Signal %s — entferne %d Knoten", signum, len(rest))
        knoten_entfernen(rest)
        sys.exit(0)

    signal.signal(signal.SIGTERM, aufraeumen)
    signal.signal(signal.SIGINT, aufraeumen)

    # NACHEINANDER starten, nicht alle auf einmal. Der Kernel vergibt die kleinste freie
    # Geraetenummer, und die Emulatoren sprechen ihre Spieler ueber genau diese Nummer an
    # (Dolphin: `evdev/0/…`, `evdev/1/…`). Starten alle vier Threads gleichzeitig, ent-
    # scheidet der Zufall, welcher Selkies-Slot welche Nummer bekommt — Spieler 1 waere
    # mal das eine, mal das andere Pad. Das faellt erst im Spiel auf und sieht dann nach
    # einem defekten Controller aus.
    #
    # Der Timeout ist wichtig: haengt an Slot 0 gar kein Pad, darf das die anderen nicht
    # aufhalten. Bei spaeteren Einzelverbindungen greift die Reihenfolge nicht mehr —
    # dann wird aber ohnehin genau die Nummer frei, die derselbe Slot vorher hatte.
    #
    # EN: start the sockets one after another so the lowest device number always belongs
    # to slot 0; otherwise which pad becomes player 1 is a race. The timeout keeps an
    # empty slot from blocking the rest.
    for i, pfad in enumerate(SOCKETS):
        bereit = threading.Event()
        threading.Thread(target=bediene, args=(pfad, bereit), daemon=True).start()
        if not bereit.wait(timeout=5) and i == 0:
            log.info("Slot 0 hat in 5 s kein Geraet angelegt — Reihenfolge nicht garantiert")
    log.info("Bruecke laeuft fuer %d Sockets", len(SOCKETS))
    signal.pause()
    return 0


if __name__ == "__main__":
    sys.exit(main())
