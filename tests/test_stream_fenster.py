"""Streaming-Host: Fensterbefund und Vollbild.

HERAUSGELOEST AUS `test_smoke.py` (#493). Nicht aus Ordnungsliebe: Die Inhaltsregel des
Repositories (`scripts/check_content_policy.py`) laesst keine Datei ueber 512 kB zu, und
`test_smoke.py` stand bei 510 kB — die naechsten Tests haetten die Prueflinie gerissen,
egal welche. Der Schnitt liegt an einer Naht, die ohnehin da war: alles, was das FENSTER
des Emulators betrifft, steht jetzt hier.

EN: split out of test_smoke.py because the repository's content policy caps a file at
512 kB and test_smoke.py had reached 510 kB. The seam is the emulator WINDOW.
"""
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _profil_modul(config_root):
    """`launch-profile.py` als Modul laden, mit eigenem Konfigurationsbaum.

    Wortgleich zu dem Helfer in `test_smoke.py` — bewusst kopiert statt geteilt: eine
    gemeinsame `conftest.py`-Fassung waere ein drittes Ding, das man kennen muss, um
    einen dieser Tests zu lesen.
    """
    import importlib.util
    alt = dict(os.environ); os.environ["FW_CONFIG_ROOT"] = str(config_root)
    try:
        pfad = os.path.join(REPO, "contrib/streaming-host/launch-profile.py")
        spec = importlib.util.spec_from_file_location("launch_profile_fenster_test", pfad)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
    finally:
        os.environ.clear(); os.environ.update(alt)


# ------------------------------------- Fehlerdialog statt Spielfenster melden (#288)

class _FensterAttrappe:
    """Ein X11 ohne X11: liefert `_x` genau die Ausgaben, die xdotool/xprop liefern.

    Die Fenster kommen als Liste von (id, breite, hoehe, typ, titel). Gemessen am
    laufenden Host — `App Encrypted` traegt wirklich `_NET_WM_WINDOW_TYPE_DIALOG,
    _NET_WM_WINDOW_TYPE_NORMAL`, also BEIDE Typen, und genau daran muss die Erkennung
    vorbeikommen.
    """

    def __init__(self, fenster, vollbild=(), aktiv=""):
        self.fenster = {f[0]: f for f in fenster}
        self.gesetzt = []          # welche Fenster aufgezogen wurden
        # `vollbild`: Fenster, die _NET_WM_STATE_FULLSCREEN tragen — also im EIGENEN
        # Vollbild des Emulators stehen. Am laufenden Host abgelesen (#493): DuckStation,
        # PCSX2 und Flycast tun das alle drei, xemu und Azahar nicht.
        self.vollbild = set(vollbild)
        self.aktiv = aktiv or (fenster[0][0] if fenster else "")
        self.tasten = []           # welche Tasten an welches Fenster gingen

    def __call__(self, *args, **_kw):
        class R:
            stdout = ""
            stderr = ""
            returncode = 0
        r = R()
        a = list(args)
        if a[:2] == ["xdotool", "getdisplaygeometry"]:
            r.stdout = "1920 1080"
        elif a[:2] == ["xdotool", "search"]:
            r.stdout = "\n".join(self.fenster)
        elif a[:2] == ["xdotool", "getwindowgeometry"]:
            _i, b, h, _t, _n = self.fenster[a[3]]
            r.stdout = f"WIDTH={b}\nHEIGHT={h}\n"
        elif a[:2] == ["xdotool", "getwindowname"]:
            r.stdout = self.fenster[a[2]][4]
        elif a[:2] == ["xdotool", "getactivewindow"]:
            r.stdout = self.aktiv
        elif a[0] == "xprop" and "_NET_WM_WINDOW_TYPE" in a:
            r.stdout = f"_NET_WM_WINDOW_TYPE(ATOM) = {self.fenster[a[2]][3]}"
        elif a[0] == "xprop" and "_NET_WM_STATE" in a:
            # Genau der Wortlaut des Hosts, samt der Fehlermeldung fuer ein Fenster
            # ohne die Eigenschaft — `xprop` liefert dort "not found", keinen Leerstring.
            r.stdout = ("_NET_WM_STATE(ATOM) = _NET_WM_STATE_FULLSCREEN, "
                        "_NET_WM_STATE_FOCUSED" if a[2] in self.vollbild
                        else "_NET_WM_STATE:  not found.")
        elif a[:2] == ["xdotool", "windowsize"]:
            self.gesetzt.append(a[2])
        elif a[:2] == ["xdotool", "key"]:
            self.tasten.append((a[3], a[4]))
        return r


NORMAL = "_NET_WM_WINDOW_TYPE_NORMAL"
DIALOG = "_NET_WM_WINDOW_TYPE_DIALOG, _NET_WM_WINDOW_TYPE_NORMAL"


def test_an_error_dialog_is_reported_instead_of_a_fake_success(tmp_path, monkeypatch):
    """Scheitert der TITEL, laeuft der Emulator weiter und zeigt einen Dialog.

    Gemessen an drei Plattformen: `App Encrypted` und `CIA must be installed before
    usage` (Azahar, 3DS), `NKit Warning` (Dolphin, Wii). In allen Faellen meldete der
    Start bisher Erfolg, der Stream ging auf, und es lief kein Spiel — der Nutzer sah
    einen leeren Desktop ohne jede Auskunft. (#288)

    Der Dialog ist 293x101 = 29.593 Pixel und liegt damit UEBER der Flaechenschwelle
    von 10.000, wurde also wie ein Spielfenster behandelt und sogar auf Vollbild
    gezogen. Genau deshalb genuegt die Groesse als Kriterium nicht.
    """
    m = _profil_modul(tmp_path)
    x = _FensterAttrappe([
        ("0x1", 1920, 1080, NORMAL, "Azahar 2125.1.3"),   # leeres Hauptfenster
        ("0x2", 293, 101, DIALOG, "App Encrypted"),       # die eigentliche Auskunft
    ])
    monkeypatch.setattr(m, "_x", x)
    monkeypatch.setattr(m.time, "sleep", lambda *_a: None)

    zustand, meldung = m.nur_emulator(4711, runden=1, pause=0)

    assert zustand == "dialog", (zustand, meldung)
    assert meldung == "App Encrypted", meldung
    # Und der Dialog darf NICHT aufs Vollbild gezogen werden: ein bildschirmfuellender
    # Fehlerdialog ist genau das, was als "leerer Stream" ankommt.
    assert "0x2" not in x.gesetzt, "Fehlerdialog wurde aufgezogen"


def test_a_real_game_window_still_reports_ok(tmp_path, monkeypatch):
    """Die Gegenrichtung: ohne Dialog bleibt es beim Erfolg.

    Ohne diese Haelfte wuerde eine Fassung, die IMMER "dialog" meldet, den Test oben
    bestehen — und PS1, PS2, GameCube, Wii, PS3 und Switch waeren stillgelegt. (#288)
    """
    m = _profil_modul(tmp_path)
    x = _FensterAttrappe([("0x1", 1920, 1080, NORMAL, "Dolphin | Vulkan | Dewy's Adventure")])
    monkeypatch.setattr(m, "_x", x)
    monkeypatch.setattr(m.time, "sleep", lambda *_a: None)

    zustand, meldung = m.nur_emulator(4711, runden=1, pause=0)

    assert zustand == "ok", (zustand, meldung)
    assert "0x1" in x.gesetzt, "Spielfenster wurde nicht aufgezogen"


def test_no_window_at_all_is_distinguished_from_a_dialog(tmp_path, monkeypatch):
    """Ein eShop-3DS-Titel oeffnet GAR KEIN Fenster (`Error 8` im Emulator-Log).

    Das ist ein anderer Befund als ein Dialog und muss anders heissen — sonst sucht man
    nach einem Dialogtext, den es nicht gibt. (#288)
    """
    m = _profil_modul(tmp_path)
    x = _FensterAttrappe([("0x1", 100, 30, NORMAL, "Azahar")])   # nur das Ladefenster
    monkeypatch.setattr(m, "_x", x)
    monkeypatch.setattr(m.time, "sleep", lambda *_a: None)

    zustand, _meldung = m.nur_emulator(4711, runden=1, pause=0)

    assert zustand == "kein-fenster", zustand


def test_window_verdict_is_machine_readable_for_the_agent(tmp_path, monkeypatch, capsys):
    """`--window` muss den Befund als letzte Zeile in JSON ausgeben.

    Der Agent liest ihn dort und reicht ihn ueber /status weiter. Ein blosser Exit-Code
    genuegt nicht: der Dialogtitel IST die Auskunft. (#288)
    """
    m = _profil_modul(tmp_path)
    x = _FensterAttrappe([("0x2", 484, 101, DIALOG, "CIA must be installed before usage")])
    monkeypatch.setattr(m, "_x", x)
    monkeypatch.setattr(m.time, "sleep", lambda *_a: None)

    rc = m.main(["--window", "4711"])

    letzte = capsys.readouterr().out.strip().splitlines()[-1]
    befund = json.loads(letzte)
    assert rc == 1, "ein gescheiterter Titel darf nicht mit 0 enden"
    assert befund["window"] == "dialog", befund
    assert befund["detail"] == "CIA must be installed before usage", befund


def test_f11_is_not_sent_to_a_window_that_is_already_in_its_own_fullscreen(tmp_path,
                                                                          monkeypatch):
    """Ein Emulator, der SELBST im Vollbild steht, darf kein F11 bekommen. (#493)

    AM LAUFENDEN HOST GEMESSEN, und der Befund war ein anderer als der im Issue vermutete.
    Der Fensterschritt (`nur_emulator`) ist NICHT der Taeter — alle vier seiner Aufrufe
    einzeln auf das Fenster von DuckStation angewandt, ohne Agent daneben:

        0 Ausgangsstand          1920x1080  _NET_WM_STATE_FULLSCREEN
        1 nach _MOTIF_WM_HINTS   1920x1080  _NET_WM_STATE_FULLSCREEN
        2 nach windowsize        1920x1080  _NET_WM_STATE_FULLSCREEN
        3 nach windowmove        1920x1080  _NET_WM_STATE_FULLSCREEN
        4 nach windowactivate    1920x1080  _NET_WM_STATE_FULLSCREEN
        5 nach windowraise       1920x1080  _NET_WM_STATE_FULLSCREEN

    Der Taeter ist das F11 danach. Aus dem Agent-Log, bei jedem PSX-Start derselbe Satz:

        [vollbild] 34.3 % bemalt -> F11 -> 99.3 %

    34,3 % misst nicht ein zu kleines Fenster, sondern ein SCHWARZES — DuckStation bootet
    zu diesem Zeitpunkt noch die Disc. F11 schaltet daraufhin das eigene Vollbild AB, und
    danach steht der Titel auf 640x480 in der Ecke, mit Titelleiste zurueck.

    Keine Flaechenmessung kann diesen Fall unterscheiden — auch die seit #495 nicht, die
    gegen ein Grundbild des leeren Desktops misst: Ein schwarz gemaltes Bild deckt den
    Desktop zwar zu, aber schwarz auf schwarz ist keine Aenderung, und der Bootschirm
    bleibt damit ein Anlass fuer ein F11. Der Zustand des Fensters entscheidet es, und den
    gibt es umsonst.

    (Die 99,27782600308642 %, die hier frueher als „Wert des leeren Desktops" standen, sind
    der obere Anschlag jener Messung — 1915 * 1075 von 1920 * 1080 ist der groesste Rahmen,
    den ein 6er-Raster aufspannen kann. Jede vollstaendig bemalte Flaeche liefert ihn, das
    Hintergrundbild wie ein bildschirmfuellender Emulator.)

    EN: the window step is not the culprit — measured, all four of its calls leave the
    fullscreen state intact. The F11 afterwards is, because no area measurement can tell
    a black boot screen from a small window. The window state can.
    """
    m = _profil_modul(tmp_path)
    x = _FensterAttrappe([("0x1", 1920, 1080, NORMAL, "Spyro the Dragon")],
                         vollbild=["0x1"])
    monkeypatch.setattr(m, "_x", x)
    monkeypatch.setattr(m.time, "sleep", lambda *_a: None)
    # Der Bildschirm ist noch schwarz — genau die Lage, in der bisher F11 kam.
    monkeypatch.setattr(m, "emulatoranteil", lambda: 34.3)

    vorher, nachher, weg = m.vollbild_sicherstellen()

    assert x.tasten == [], f"F11 ging an ein Fenster im eigenen Vollbild: {x.tasten}"
    assert weg != "F11", weg
    assert (vorher, nachher) == (34.3, 34.3), (vorher, nachher)


def test_f11_still_reaches_an_emulator_without_a_fullscreen_switch(tmp_path, monkeypatch):
    """Die Gegenprobe: xemu, Azahar und Eden haben keinen eigenen Schalter. (#429, #493)

    Ohne diese Haelfte bestuende der Test oben auch eine Fassung, die F11 GAR NICHT mehr
    schickt — und damit waeren genau die drei Emulatoren wieder halbbildschirmgross, wegen
    derer der Tastenweg ueberhaupt gebaut wurde. Am laufenden Host gemessen: deren Fenster
    traegt `_NET_WM_STATE_FULLSCREEN` NICHT.
    """
    m = _profil_modul(tmp_path)
    x = _FensterAttrappe([("0x1", 1920, 1080, NORMAL, "xemu | Halo")])   # kein Vollbild
    monkeypatch.setattr(m, "_x", x)
    monkeypatch.setattr(m.time, "sleep", lambda *_a: None)
    monkeypatch.setattr(m, "emulatoranteil", lambda: 34.3)

    _vorher, _nachher, weg = m.vollbild_sicherstellen()

    assert weg == "F11", weg
    assert x.tasten == [("0x1", "F11")], x.tasten


def test_the_window_verdict_reports_the_measured_size_not_the_requested_one(tmp_path,
                                                                           monkeypatch,
                                                                           capsys):
    """`/status` darf keine Groesse zusagen, die es nie nachgesehen hat. (#493)

    GEMESSEN, waehrend der Titel lief:

        /status   "window": "ok", "1 Fenster auf 1920x1080, ohne Rahmen, ..."
        xdotool   Position 1,51   Geometry 640x480

    Die Zahl im Befund war die BILDSCHIRMgroesse — also das, was der Schritt anstrebte,
    nicht das, was dabei herauskam. Fuer den Nutzer heisst "ok" damit "es war einmal
    gewollt", nicht "es ist so". Nachgemessen wird NACH dem Vollbildschritt, denn erst
    dort entstand der Schaden.

    EN: the size in the verdict was the screen geometry — what the step aimed for, not
    what it achieved. It is measured after the fullscreen step, because that is where the
    damage happened.
    """
    m = _profil_modul(tmp_path)
    x = _FensterAttrappe([("0x1", 640, 480, NORMAL, "Spyro the Dragon")])
    monkeypatch.setattr(m, "_x", x)
    monkeypatch.setattr(m.time, "sleep", lambda *_a: None)
    monkeypatch.setattr(m, "emulatoranteil", lambda: 99.3)

    m.main(["--window", "4711"])

    befund = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert befund["window"] == "ok", befund
    assert "640x480" in befund["detail"], befund
    assert "1920x1080" not in befund["detail"], befund


def test_agent_exposes_the_window_verdict_on_status():
    """Der Befund muss den Aufrufer erreichen — sonst ist er nur ein Logeintrag.

    Geprueft wird am Quelltext, weil der Agent hier keinen X-Server hat: /status muss
    `window` fuehren, und der Startpfad muss ihn auf "pending" setzen. (#288)
    """
    quelle = open(os.path.join(REPO, "contrib/streaming-host/stream-agent.py"),
                  encoding="utf-8").read()
    assert '"window": _current["window"]' in quelle, "/status meldet den Befund nicht"
    assert '_current["window"] = "pending"' in quelle, "Start setzt den Befund nicht zurueck"
    # Beim Stoppen muss er weg sein, sonst klebt der Befund des Vortitels am naechsten.
    assert '"window": "", "window_detail": ""' in quelle, "Stop raeumt den Befund nicht ab"


# --- #429: Vollbild wird gemessen, nicht angenommen ---------------------------------

def test_the_keystroke_route_does_not_sit_where_it_cannot_fire():
    """Kein Tastenweg im `--fullscreen`-Schritt — der laeuft VOR dem Start. (#429)

    DER FUND: `xemu_vollbild()` schickt F11 an ein xemu-Fenster. Der Agent ruft
    `--fullscreen` aber ab, BEVOR der Emulator gestartet wird — damit dieser seine
    Konfiguration frisch liest. Zu diesem Zeitpunkt gibt es kein Fenster. Am laufenden
    Host nachgestellt:

        [vollbild] xemu: kein xemu-Fenster gefunden — laeuft der Emulator?

    Die Loesung aus #306 stand also im Quelltext und feuerte nie. Genau das Muster
    „ausgeliefert und wirkungslos": Es sah aus wie ein Fix, war aber einer, den niemand
    ausgeloest hat.

    Diese Pruefung haelt die beiden Zeitpunkte auseinander: Was `--fullscreen` tut, muss
    ohne Fenster sinnvoll sein — also Konfiguration schreiben. Tastensendungen gehoeren in
    den Fensterschritt nach dem Start.

    EN: `--fullscreen` runs before the emulator starts, so a keystroke route there finds no
    window and never fires. #306's fix was in the source and inert.
    """
    quelle = open(os.path.join(REPO, "contrib", "streaming-host", "launch-profile.py"),
                  encoding="utf-8").read()
    m = re.search(r"^PROFILE = \{(.*?)^\}", quelle, re.S | re.M)
    assert m, "PROFILE nicht gefunden"
    zugeordnet = set(re.findall(r'"vollbild":\s*([A-Za-z_][A-Za-z0-9_]*)', m.group(1)))
    zugeordnet.discard("None")

    def rumpf(fn):
        m = re.search(rf"^def {fn}\(.*?\):(.*?)(?=^def |\Z)", quelle, re.S | re.M)
        return m.group(1) if m else ""

    for name in sorted(zugeordnet):
        eigener = rumpf(name)
        assert eigener, f"{name} ist zugeordnet, aber nicht definiert"
        # EINE EBENE WEITERVERFOLGEN. Die erste Fassung sah nur in die genannte Funktion —
        # und `azahar_vollbild` besteht aus einer einzigen Zeile: `return
        # f11_vollbild("Azahar")`. Der xdotool-Aufruf steht im gemeinsamen Helfer, also
        # blieb der Waechter gruen, waehrend genau der Fehler wieder dastand, den er
        # verhindern soll. Aufgefallen NUR, weil die Gegenprobe ihn absichtlich einbaute.
        aufgerufen = set(re.findall(r"\b([a-z_][a-z0-9_]*)\(", eigener))
        koerper = eigener + "".join(rumpf(f) for f in aufgerufen if f != name)
        koerper = re.match(r"(.*)", koerper, re.S)
        # AUF DEN AUFRUF PRUEFEN, NICHT AUF DAS WORT. Die erste Fassung suchte
        # "xdotool" im ganzen Funktionskoerper und meldete `pcsx2_vollbild` — das
        # schreibt eine Konfigurationszeile und erwaehnt xdotool nur in seinem
        # Kommentar, um zu begruenden, WARUM es den Fenstertrick nicht benutzt. Ein
        # Waechter, der an einer Erklaerung scheitert, erzieht dazu, Erklaerungen
        # wegzulassen.
        assert '_x("xdotool"' not in koerper.group(1), (
            f"{name} sucht ein Fenster, laeuft aber im `--fullscreen`-Schritt VOR dem "
            "Start — dort gibt es keins. Tastenwege gehoeren in vollbild_sicherstellen().")


def test_fullscreen_is_measured_before_it_is_corrected():
    """Erst messen, dann F11 — nicht umgekehrt. (#429)

    WARUM DAS DIE ENTSCHEIDENDE REIHENFOLGE IST: **F11 ist ein Umschalter.** Ein Emulator,
    bei dem der Fenstertrick bereits gewirkt hat, fiele durch ein blindes F11 WIEDER aus
    dem Vollbild — aus einem funktionierenden Fall wuerde ein kaputter. Die Messung ist
    hier keine zusaetzliche Vorsicht, sondern das, was die Korrektur ungefaehrlich macht.

    EN: F11 is a toggle. Measuring first is what makes the correction safe rather than a
    way to break the emulators that already worked.
    """
    quelle = open(os.path.join(REPO, "contrib", "streaming-host", "launch-profile.py"),
                  encoding="utf-8").read()
    m = re.search(r"^def vollbild_sicherstellen\(.*?\):(.*?)(?=^def |\Z)", quelle,
                  re.S | re.M)
    assert m, "vollbild_sicherstellen fehlt"
    koerper = m.group(1)

    mess = koerper.index("emulatoranteil()")
    taste = koerper.index('"F11"')
    assert mess < taste, "F11 wird geschickt, bevor gemessen wurde"

    # Und der Rueckweg ohne Korrektur muss es geben: liegt die Flaeche schon ueber der
    # Schwelle, darf NICHTS gesendet werden.
    assert "VOLLBILD_SCHWELLE" in koerper, "es gibt keine Schwelle, ab der nichts passiert"
    assert re.search(r">= VOLLBILD_SCHWELLE:\s*\n\s*return", koerper), \
        "ueber der Schwelle wird nicht frueh zurueckgekehrt — F11 traefe auch den Gutfall"


# --- #495: die Messung muss ein Spiel vom leeren Desktop unterscheiden ---------------

def _xwd(breite, hoehe, punkte, bpp=24, zeilenbreite=0):
    """Eine xwd-Aufnahme bauen, wie `xwd -root` sie schreibt. `punkte(x, y) -> (r, g, b)`.

    WOZU EIGENE DATEN STATT EINER AUFNAHME: Diese Tests duerfen keinen X-Server brauchen —
    in der CI gibt es keinen. Der Kopf ist deshalb derselbe, den der laufende Host
    liefert, nachgemessen: Version 7, Format 2 (ZPixmap), 256 Farbeintraege, Masken
    0xff0000/0x00ff00/0x0000ff.

    `bpp` und `zeilenbreite` sind ABSICHTLICH getrennt einstellbar: der laufende Host
    liefert eine 24-bpp-Aufnahme mit einer auf 1920*4 AUFGEFUELLTEN Zeile — 5760 der 7680
    Byte je Zeile tragen Bild, der Rest ist Rand.
    """
    import struct
    kopfgroesse = 100 + 7            # 100 Byte Kopf + "xwd\0" o. ae.; Laenge steht im Kopf
    px = max(1, bpp // 8)
    zeile = zeilenbreite or breite * px
    k = [0] * 25
    k[0] = kopfgroesse; k[1] = 7; k[2] = 2; k[3] = 24
    k[4] = breite; k[5] = hoehe
    k[11] = bpp; k[12] = zeile
    k[14], k[15], k[16] = 0xFF0000, 0x00FF00, 0x0000FF
    k[19] = 0                        # keine Farbtabelle
    daten = bytearray(struct.pack(">25I", *k) + b"xwd\0\0\0\0")
    for y in range(hoehe):
        z = bytearray(zeile)
        for x in range(breite):
            r, g, b = punkte(x, y)
            o = x * px
            z[o] = b; z[o + 1] = g; z[o + 2] = r
        daten += z
    return bytes(daten)


def _schreib(pfad, inhalt):
    with open(pfad, "wb") as f:
        f.write(inhalt)


BLAU = lambda _x, _y: (60, 70, 120)          # Hintergrundbild
WEISS = lambda _x, _y: (255, 255, 255)       # ein Emulator, der den Schirm gefuellt hat


def test_the_measurement_tells_a_running_emulator_from_the_bare_desktop(tmp_path,
                                                                       monkeypatch):
    """Der Abnahmepunkt von #495, und der Grund, warum es das Issue gibt.

    AM LAUFENDEN HOST GEMESSEN, drei Zustaende, alte Messung (`gezeichneter_anteil`):

        leerer Desktop, kein Emulator      99,28 %
        xemu, Bild 1280x963 auf dem Desktop 99,28 %   <- BITGLEICH derselbe Wert
        Flycast, echtes Vollbild            73,56 %   <- der Gutfall misst WENIGER

    Die Zahl war damit nicht bloss ungenau, sondern verkehrt herum: Der leere Desktop
    stand ueber der Schwelle, ein wirklich bildschirmfuellender Emulator darunter.
    Die Ursache ist der Messgegenstand — gesucht wurde der Rahmen der nicht-schwarzen
    Bildpunkte auf dem BILDSCHIRM, und ein Hintergrundbild ist nicht schwarz.

    Gemessen wird deshalb gegen ein GRUNDBILD des leeren Desktops. Dieselben drei
    Zustaende, neue Messung:

        leerer Desktop                       0,06 %
        xemu, Bild 1280x963                 74,87 %
        Flycast, echtes Vollbild            99,97 %

    EN: the old number was not merely imprecise but inverted — the bare desktop scored
    above the threshold and a genuinely fullscreen emulator below it. The measurement now
    compares against a captured picture of the empty desktop.
    """
    m = _profil_modul(tmp_path)
    grund = str(tmp_path / "grund.xwd")
    monkeypatch.setattr(m, "GRUNDBILD", grund)
    _schreib(grund, _xwd(120, 90, BLAU))

    # 1. Nichts laeuft: der Schirm zeigt weiter das Grundbild.
    monkeypatch.setattr(m, "_bildschirm_aufnehmen", lambda: _xwd(120, 90, BLAU))
    leer = m.emulatoranteil()

    # 2. Ein Emulator hat den Schirm uebernommen.
    monkeypatch.setattr(m, "_bildschirm_aufnehmen", lambda: _xwd(120, 90, WEISS))
    voll = m.emulatoranteil()

    assert leer is not None and voll is not None, (leer, voll)
    assert leer < m.VOLLBILD_SCHWELLE <= voll, (leer, voll, m.VOLLBILD_SCHWELLE)


def test_the_measurement_sees_the_desktop_next_to_a_half_screen_emulator(tmp_path,
                                                                        monkeypatch):
    """Der Fall, wegen dessen es den Tastenweg ueberhaupt gibt: xemu. (#429, #495)

    Am laufenden Host gemessen, Fable ueber xemu gestartet: `xdotool` meldet ein Fenster
    von 1920x1080, `xwininfo` bestaetigt es — bemalt wird davon aber nur rund 1280x963.
    Der Rest des Fensters bleibt UNBEMALT und zeigt weiter die Bildpunkte, die vorher da
    waren, also das Hintergrundbild. Deshalb hilft es auch nicht, die Messung auf die
    Fenstergeometrie zu beschraenken (im Issue vorgeschlagen und hier widerlegt): der
    Desktop liegt INNERHALB des Fensters.

    Gegen das Grundbild gemessen faellt genau dieser Teil heraus.
    """
    m = _profil_modul(tmp_path)
    grund = str(tmp_path / "grund.xwd")
    monkeypatch.setattr(m, "GRUNDBILD", grund)
    _schreib(grund, _xwd(120, 90, BLAU))
    # Zwei Drittel der Breite gehoeren dem Emulator, der Rest zeigt das Hintergrundbild.
    halb = lambda x, y: (255, 255, 255) if x < 80 else BLAU(x, y)
    monkeypatch.setattr(m, "_bildschirm_aufnehmen", lambda: _xwd(120, 90, halb))

    anteil = m.emulatoranteil()

    assert anteil is not None
    assert 60 < anteil < 75, anteil
    assert anteil < m.VOLLBILD_SCHWELLE, "der halbe Desktop ginge als Vollbild durch"


def test_a_padded_line_length_does_not_shift_the_reading(tmp_path, monkeypatch):
    """Die Schrittweite kommt aus `bits_per_pixel`, NICHT aus `bytes_per_line`. (#495)

    Am laufenden Host gemessen, zwei Aufnahmen DESSELBEN 1920 Punkte breiten Schirms:

        leerer Desktop            bits_per_pixel 24   bytes_per_line 7680
        Flycast im Vollbild       bits_per_pixel 32   bytes_per_line 7680

    Im ersten Fall ist die Zeile AUFGEFUELLT: 1920 * 3 = 5760 genutzte Byte, der Rest ist
    Rand. `bytes_per_line // breite` ergibt dort 4 und liest ueber die Zeile hinaus.
    Nachgestellt und ANGESEHEN — die Datei einmal so und einmal mit 3 Byte dekodiert:

        3 Byte je Punkt   sauberes Bild, 0 % Nullpunkte, deckungsgleich mit `ffmpeg`
        4 Byte je Punkt   auf drei Viertel der Breite gestaucht, rechts schwarz, 25 % Null

    (Dieser Test stand einmal genau andersherum da. Die Annahme „24 bpp liegen trotzdem in
    32-Bit-Zellen" klang plausibel, die Zahlen dazu waren reproduzierbar — und beides war
    falsch. Aufgefallen ist es erst, als das dekodierte Bild angesehen wurde statt nur
    gerechnet. Wer die Schrittweite anfasst, dekodiere zuerst ein Bild und sehe es an.)

    EN: derive the stride from bits_per_pixel. bytes_per_line is padded, and dividing it by
    the width reads past the row — visible as an image squeezed into three quarters of the
    width. This test once asserted the opposite; the numbers were reproducible and wrong.
    """
    m = _profil_modul(tmp_path)
    grund = str(tmp_path / "grund.xwd")
    monkeypatch.setattr(m, "GRUNDBILD", grund)
    # 24 bpp = 3 Byte je Punkt, Zeile aber auf 4 Byte je Punkt aufgefuellt — genau die
    # Aufnahme des leeren Desktops.
    aufnahme = _xwd(120, 90, BLAU, bpp=24, zeilenbreite=120 * 4)
    _schreib(grund, aufnahme)
    monkeypatch.setattr(m, "_bildschirm_aufnehmen", lambda: aufnahme)

    kopf = m._xwd_kopf(aufnahme)
    assert kopf["schritt"] == 3, kopf
    # Dieselbe Aufnahme gegen sich selbst: der Emulator hat NICHTS uebernommen. Laege die
    # Leseposition daneben, faende die Messung im Rand lauter Schwarz und meldete es als
    # uebernommene Flaeche.
    assert m.emulatoranteil() == 0.0, m.emulatoranteil()


def test_dithering_between_two_colour_depths_is_not_mistaken_for_a_game(tmp_path,
                                                                       monkeypatch):
    """Bitgleichheit ist zu sproede — gemessen, nicht angenommen. (#495)

    Grundbild und Messbild entstehen bei VERSCHIEDENEN Farbtiefen: der leere Desktop
    liefert 24 bpp, sobald ein Emulator mit 32-Bit-Visual im Vollbild steht, liefert
    `xwd -root` 32 bpp. Der Verlauf des Hintergrundbildes wird dabei anders gerastert. Am
    laufenden Host gemessen, im rechts neben xemu SICHTBAREN Stueck Hintergrundbild:

        bitgleich          7,2 %
        Abweichung <=  8  63,4 %
        Abweichung <= 16  85,9 %

    Auf xemus weisser Flaeche liegt bei Toleranz 16 dagegen KEIN einziger Punkt — echter
    Bildinhalt weicht viel weiter ab als das Rauschen. Ohne Toleranz meldete die Messung
    fuer genau diesen Zustand 95,13 % statt 74,87 %: der sichtbare Desktop ging als
    Emulator durch, und der Bildschirmabzug daneben zeigte ihn.

    EN: baseline and measurement are captured at different colour depths, so a gradient
    wallpaper dithers differently. Exact equality reported 95.13 % for a screen that was
    visibly one third desktop.
    """
    m = _profil_modul(tmp_path)
    grund = str(tmp_path / "grund.xwd")
    monkeypatch.setattr(m, "GRUNDBILD", grund)
    _schreib(grund, _xwd(120, 90, BLAU, bpp=24, zeilenbreite=120 * 4))
    # Dasselbe Bild, um wenige Stufen verschoben — und mit der anderen Farbtiefe.
    verrauscht = lambda x, y: tuple(min(255, c + 3 + (x + y) % 5) for c in BLAU(x, y))
    monkeypatch.setattr(m, "_bildschirm_aufnehmen",
                        lambda: _xwd(120, 90, verrauscht, bpp=32))

    assert m.emulatoranteil() == 0.0, (
        "das Rauschen zwischen zwei Farbtiefen wurde als Emulator gezaehlt")


def test_the_baseline_is_refused_while_a_program_window_is_on_screen(tmp_path, monkeypatch):
    """Ein Grundbild MIT Spiel darin waere die perfekte Taeuschung. (#495)

    Es wuerde jeden folgenden Start als „Emulator hat nichts uebernommen" ausweisen —
    also genau die Fehlmessung erzeugen, gegen die es gebaut ist. Aufgenommen wird
    deshalb nur, wenn `_NET_CLIENT_LIST` ausser Panel und Desktop nichts fuehrt.

    Am laufenden Host abgelesen, im Leerlauf:

        _NET_CLIENT_LIST(WINDOW): window id # 0x1a00003, 0x1c00017
        0x1a00003 [xfce4-panel] _NET_WM_WINDOW_TYPE_DOCK
        0x1c00017 [Desktop]     _NET_WM_WINDOW_TYPE_DESKTOP

    EN: a baseline WITH the game in it would mark every later launch as "the emulator took
    nothing over" — the very mismeasurement it exists to prevent.
    """
    m = _profil_modul(tmp_path)
    grund = str(tmp_path / "grund.xwd")
    monkeypatch.setattr(m, "GRUNDBILD", grund)

    class _MitFenster:
        def __call__(self, *args, **_kw):
            class R:
                stdout = ""; stderr = ""; returncode = 0
            r = R()
            a = list(args)
            if a[:3] == ["xprop", "-root", "_NET_CLIENT_LIST"]:
                r.stdout = "_NET_CLIENT_LIST(WINDOW): window id # 0x1a00003, 0x2a00031"
            elif a[0] == "xprop" and "_NET_WM_WINDOW_TYPE" in a:
                r.stdout = ("_NET_WM_WINDOW_TYPE(ATOM) = _NET_WM_WINDOW_TYPE_DOCK"
                            if a[2] == "0x1a00003"
                            else "_NET_WM_WINDOW_TYPE(ATOM) = _NET_WM_WINDOW_TYPE_NORMAL")
            elif a[:2] == ["xdotool", "getwindowname"]:
                r.stdout = "xemu | v0.8.136"
            return r

    monkeypatch.setattr(m, "_x", _MitFenster())
    monkeypatch.setattr(m, "_bildschirm_aufnehmen", lambda: _xwd(120, 90, BLAU))

    ok, meldung = m.grundbild_aufnehmen()

    assert not ok, meldung
    assert "xemu" in meldung, meldung
    assert not os.path.exists(grund), "es wurde trotzdem ein Grundbild geschrieben"


def test_the_agent_takes_the_baseline_before_it_starts_the_emulator():
    """Das Grundbild muss VOR dem Start aufgenommen werden — danach ist es wertlos.

    Geprueft wird am Quelltext, weil der Agent hier keinen X-Server hat. Der Aufruf muss
    NACH `_stop_locked()` stehen (sonst steht der Vortitel noch im Bild) und VOR
    `subprocess.Popen` (sonst der neue).
    """
    quelle = open(os.path.join(REPO, "contrib/streaming-host/stream-agent.py"),
                  encoding="utf-8").read()
    assert "--grundbild" in quelle, "der Agent nimmt nie ein Grundbild auf"
    halt = quelle.index("_stop_locked()\n", quelle.index("umgebung = start_umgebung"))
    grund = quelle.index("--grundbild", halt)
    start = quelle.index("subprocess.Popen", halt)
    assert halt < grund < start, "das Grundbild wird nicht zwischen Stoppen und Starten geholt"
