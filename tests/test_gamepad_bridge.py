"""Tests fuer die Gamepad-Bruecke (#119).

Die Bruecke laeuft im Streaming-Host und braucht dort einen Kernel mit `uinput`. Hier
wird deshalb NICHT die Kernel-Wirkung geprueft — die ist am laufenden System gemessen
worden (Socket -> Geraet -> Knoten -> Lesen als uid 1000). Geprueft wird, was ohne
Kernel pruefbar ist und was beim naechsten Umbau still kaputtgehen koennte:

* die Groesse der Konfigurationsstruktur (die 6 Byte Polsterung),
* die ioctl-Nummer fuer UI_GET_SYSNAME,
* die Entscheidungen in `knoten_spiegeln` (anlegen / ueberspringen / ersetzen).

EN: the kernel effect was measured on the live host; these tests cover the parts that
can break silently without a kernel — struct padding, the ioctl number, and the node
bookkeeping.
"""
import ctypes
import importlib.util
import os
import sys
import types

import pytest

BRUECKE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "contrib", "streaming-host", "selkies-uinput-bridge.py",
)


@pytest.fixture(scope="module")
def bruecke():
    """Laedt die Bruecke mit einem Platzhalter fuer `evdev`.

    `python-evdev` steckt im Streaming-Host-Abbild, nicht in der Testumgebung. Ohne
    Platzhalter wuerden diese Tests ueberall uebersprungen — und ein Test, der nie
    laeuft, haelt nichts fest.
    EN: python-evdev lives in the streaming-host image, not here; without a stub these
    tests would always skip, and a test that never runs guards nothing.
    """
    echt = sys.modules.get("evdev")
    stub = types.ModuleType("evdev")

    class UInput:
        # Die Bruecke haengt `_find_device` ab; das Attribut muss also existieren.
        def _find_device(self, fd):
            raise AssertionError("darf nicht aufgerufen werden")

    stub.UInput = UInput
    stub.AbsInfo = lambda **kw: kw
    stub.ecodes = types.SimpleNamespace(EV_KEY=1, EV_ABS=3)
    sys.modules["evdev"] = stub
    try:
        spec = importlib.util.spec_from_file_location("selkies_uinput_bridge", BRUECKE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        yield mod
    finally:
        if echt is not None:
            sys.modules["evdev"] = echt
        else:
            sys.modules.pop("evdev", None)


def test_konfig_groesse_ist_gepolstert(bruecke):
    """1360 auf dem Draht gegen 1354 in ctypes — daran haengt die Ereignisausrichtung.

    Wer hier auf `sizeof` umstellt, verschiebt JEDES folgende Ereignis um sechs Byte:
    Tasten wuerden zu Achsen, ohne dass irgendwo ein Fehler auftritt.
    """
    assert ctypes.sizeof(bruecke.JsConfig) == 1354
    assert bruecke.KONFIG_GROESSE == 1360


def test_ui_get_sysname_nummer(bruecke):
    """UI_GET_SYSNAME(64) = _IOC(_IOC_READ, 'U', 44, 64) aus linux/uinput.h."""
    erwartet = (2 << 30) | (64 << 16) | (ord("U") << 8) | 44
    assert bruecke.UI_GET_SYSNAME == erwartet
    assert bruecke.UI_GET_SYSNAME == 0x8040552C


def test_js_ereignis_ist_acht_byte(bruecke):
    """struct js_event ist 8 Byte; ein anderer Wert zerlegt den Ereignisstrom."""
    assert bruecke.JS_EVENT.size == 8


def test_socket_praefix_ist_ueberschreibbar(bruecke):
    """Ohne Env die echten Pfade — sonst belegte ein Testlauf die Selkies-Sockets."""
    assert bruecke.SOCKETS[0] == "/tmp/selkies_js0.sock"
    assert len(bruecke.SOCKETS) == 4


def _sysfs_bauen(tmp_path, sysname, handler):
    """Ein sysfs-Verzeichnis nachbauen: {handler: "major:minor"}."""
    wurzel = tmp_path / "sys" / sysname
    for name, dev in handler.items():
        d = wurzel / name
        d.mkdir(parents=True)
        (d / "dev").write_text(dev + "\n")
    # `power` und `capabilities` liegen dort auch und duerfen NICHT als Handler zaehlen.
    (wurzel / "power").mkdir()
    (wurzel / "capabilities").mkdir()
    return wurzel


def _stat_vortaeuschen(monkeypatch, nummern):
    """`os.stat` NUR fuer die genannten Pfade ersetzen.

    Ein pauschaler Ersatz hat hier zuerst `os.makedirs` zerlegt (dort fehlt dann
    `st_mode`) — die Ersetzung muss so eng sein wie die Frage, die sie beantwortet.
    """
    echt = os.stat

    class Ersatz:
        def __init__(self, rdev):
            self.st_rdev = rdev

    def stat_ersatz(pfad, *a, **k):
        if str(pfad) in nummern:
            return Ersatz(nummern[str(pfad)])
        return echt(pfad, *a, **k)

    monkeypatch.setattr(os, "stat", stat_ersatz)


def test_knoten_anlegen_und_ueberspringen(bruecke, tmp_path, monkeypatch):
    """Anlegen, was fehlt — ueberspringen, was schon auf dasselbe Geraet zeigt.

    `os.mknod` wird ersetzt, weil ein Test keine Geraeteknoten anlegen darf. Geprueft
    wird die Buchfuehrung, nicht die Kernel-Wirkung; die ist am laufenden Host gemessen.
    """
    _sysfs_bauen(tmp_path, "input52", {"event3": "13:67", "js0": "13:0"})
    dev = tmp_path / "dev"
    dev.mkdir()
    monkeypatch.setattr(bruecke, "SYSFS_INPUT", str(tmp_path / "sys"))
    monkeypatch.setattr(bruecke, "DEV_INPUT", str(dev))

    gerufen = []

    def mknod_ersatz(pfad, modus, nummer):
        gerufen.append((pfad, os.major(nummer), os.minor(nummer)))
        open(pfad, "w").close()          # Platzhalter, damit stat() spaeter greift

    monkeypatch.setattr(os, "mknod", mknod_ersatz)
    monkeypatch.setattr(os, "chmod", lambda *a, **k: None)

    angelegt, schon_richtig = bruecke.knoten_spiegeln("input52")

    assert sorted(os.path.basename(p) for p in angelegt) == ["event3", "js0"]
    assert schon_richtig == []
    assert (str(dev / "event3"), 13, 67) in gerufen
    assert (str(dev / "js0"), 13, 0) in gerufen
    # `power` und `capabilities` sind keine Handler und duerfen nicht auftauchen.
    assert not any("power" in p or "capabilities" in p for p, _, _ in gerufen)


def test_vorhandener_richtiger_knoten_wird_nicht_neu_angelegt(bruecke, tmp_path, monkeypatch):
    """Nach einem Neuverbinden vergibt der Kernel oft dieselben Nummern.

    Der Knoten zeigt dann schon auf das richtige Geraet. Er darf weder neu angelegt
    noch beim Aufraeumen entfernt werden — sonst nimmt die Bruecke etwas weg, das sie
    nicht angelegt hat.
    """
    _sysfs_bauen(tmp_path, "input60", {"event9": "13:73"})
    dev = tmp_path / "dev"
    dev.mkdir()
    monkeypatch.setattr(bruecke, "SYSFS_INPUT", str(tmp_path / "sys"))
    monkeypatch.setattr(bruecke, "DEV_INPUT", str(dev))

    (dev / "event9").write_text("")      # Knoten existiert bereits
    _stat_vortaeuschen(monkeypatch, {str(dev / "event9"): os.makedev(13, 73)})
    monkeypatch.setattr(os, "mknod", lambda *a, **k: pytest.fail("darf nicht anlegen"))

    angelegt, schon_richtig = bruecke.knoten_spiegeln("input60")
    assert angelegt == []
    assert [os.path.basename(p) for p in schon_richtig] == ["event9"]


def test_falsch_zeigender_knoten_wird_ersetzt(bruecke, tmp_path, monkeypatch):
    """Selkies legt `js0..js3` als Attrappen an. Zeigt so ein Knoten woanders hin,
    muss er weichen — sonst oeffnet ein Emulator ein totes Geraet und meldet einen
    Controller, der nie etwas sendet."""
    _sysfs_bauen(tmp_path, "input61", {"js0": "13:0"})
    dev = tmp_path / "dev"
    dev.mkdir()
    monkeypatch.setattr(bruecke, "SYSFS_INPUT", str(tmp_path / "sys"))
    monkeypatch.setattr(bruecke, "DEV_INPUT", str(dev))

    (dev / "js0").write_text("")
    # zeigt auf eine Attrappe, nicht auf unser Geraet
    _stat_vortaeuschen(monkeypatch, {str(dev / "js0"): os.makedev(13, 1064)})
    entfernt = []
    monkeypatch.setattr(os, "unlink", lambda p: entfernt.append(p))
    monkeypatch.setattr(os, "mknod", lambda *a, **k: None)
    monkeypatch.setattr(os, "chmod", lambda *a, **k: None)

    angelegt, schon_richtig = bruecke.knoten_spiegeln("input61")
    assert [os.path.basename(p) for p in angelegt] == ["js0"]
    assert schon_richtig == []
    assert entfernt == [str(dev / "js0")]


def test_knoten_entfernen_uebergeht_fehler(bruecke, tmp_path):
    """Ein bereits verschwundener Knoten darf das Aufraeumen nicht abbrechen —
    sonst bliebe der Rest der Liste stehen."""
    p = tmp_path / "weg"
    bruecke.knoten_entfernen([str(p)])          # existiert gar nicht
    q = tmp_path / "da"
    q.write_text("")
    bruecke.knoten_entfernen([str(p), str(q)])
    assert not q.exists()


def test_geraetesuche_ist_abgeschaltet(bruecke):
    """python-evdev wuerde den Knoten raten und Selkies' Attrappe treffen (ENXIO).

    Der Patch muss sitzen; ohne ihn stirbt der Konstruktor, NACHDEM der Kernel das
    Geraet schon erzeugt hat.
    """
    from evdev import UInput
    assert UInput._find_device(object(), 0) is None


# --- #535: Reihenfolge der Geraeteknoten -------------------------------------------

def test_devices_are_created_in_socket_order_during_a_reconnect_storm(bruecke):
    """Alle vier gleichzeitig -> Knoten entstehen in Socket-Reihenfolge. (#535)

    AM 2026-08-13 GENAU SO SCHIEFGEGANGEN, aus dem Protokoll der Bruecke:

        12:58:43,618  selkies_js2.sock  ->  /dev/input/js0
        12:58:43,621  selkies_js0.sock  ->  /dev/input/js1   <- das Pad, auf Platz zwei
        12:58:43,633  selkies_js1.sock  ->  /dev/input/js2

    Socket js2 war vier Millisekunden schneller. Der Kernel vergibt `jsN` in der
    Reihenfolge der Entstehung, und weil alle vier Geraete dieselbe SDL-Kennung tragen,
    kann ein Emulator sie nicht unterscheiden — er nimmt das erste. Das war das stumme.
    Eden band `port:0`, der Controller war tot; nach der Korrektur `port:1`, und es ging.

    Die Reihenfolge war bisher nur beim ERSTEN Start geordnet. Ein Neuladen der Seite
    verbindet alle vier gleichzeitig neu, und dann entschied das Rennen.

    EN: node numbers follow creation order, and four identical devices give an emulator
    nothing to choose by. Ordering held at startup only; a page reload reconnects all
    four at once.
    """
    import threading
    anzahl = 4
    bruecke._DRAN = 0
    reihenfolge = []
    sperre = threading.Lock()
    los = threading.Event()

    def arbeiter(i):
        los.wait()
        assert bruecke._warte_bis_dran(i, anzahl), f"{i} kam nicht an die Reihe"
        with sperre:
            reihenfolge.append(i)
        bruecke._naechster_dran(i, anzahl)

    # Absichtlich verdrehte Startreihenfolge — genau wie im echten Sturm.
    faeden = [threading.Thread(target=arbeiter, args=(i,)) for i in (2, 0, 3, 1)]
    for f in faeden:
        f.start()
    los.set()
    for f in faeden:
        f.join(timeout=10)
    assert reihenfolge == [0, 1, 2, 3], reihenfolge


def test_a_lone_reconnect_is_not_blocked_by_peers_that_never_ask(bruecke, monkeypatch):
    """Ein einzeln wiederverbindender Socket wartet nicht ewig. (#535)

    Die Frist ist der Punkt, nicht das Warten. Verbindet sich NUR Socket 2 neu, fordern
    die anderen drei ihren Platz nie an — ohne Frist stuende er fuer immer. Nach der
    Frist legt er trotzdem an und bekommt die Nummer, die er vorher hatte; genau dort
    gilt die alte Annahme weiter, und genau dort war sie richtig.

    Ohne diesen Test waere eine Schranke, die IMMER blockiert, ebenfalls gruen — und der
    Controller nach jedem einzelnen Verbindungsabbruch tot.
    """
    monkeypatch.setattr(bruecke, "_REIHE_FRIST", 0.3)
    bruecke._DRAN = 0
    import time as _t
    start = _t.monotonic()
    dran = bruecke._warte_bis_dran(2, 4)      # 0 ist an der Reihe, nicht 2
    dauer = _t.monotonic() - start
    assert dran is False, "haette nicht an der Reihe sein duerfen"
    assert 0.2 < dauer < 3, f"Frist nicht eingehalten: {dauer:.2f}s"
