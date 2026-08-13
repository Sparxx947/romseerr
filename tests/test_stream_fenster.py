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

    Die Flaechenmessung kann diesen Fall nicht unterscheiden: sie misst den BILDSCHIRM,
    nicht das Fenster. Der leere XFCE-Desktop allein misst 99,27782600308642 % — bitgleich
    mit dem Wert, den das Log oben als Erfolg fuehrt. Der Zustand des Fensters kann es,
    und den gibt es umsonst.

    EN: the window step is not the culprit — measured, all four of its calls leave the
    fullscreen state intact. The F11 afterwards is, because the painted-area measurement
    reads a black boot screen as "too small" and cannot tell a game apart from the desktop.
    """
    m = _profil_modul(tmp_path)
    x = _FensterAttrappe([("0x1", 1920, 1080, NORMAL, "Spyro the Dragon")],
                         vollbild=["0x1"])
    monkeypatch.setattr(m, "_x", x)
    monkeypatch.setattr(m.time, "sleep", lambda *_a: None)
    # Der Bildschirm ist noch schwarz — genau die Lage, in der bisher F11 kam.
    monkeypatch.setattr(m, "gezeichneter_anteil", lambda: 34.3)

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
    monkeypatch.setattr(m, "gezeichneter_anteil", lambda: 34.3)

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
    monkeypatch.setattr(m, "gezeichneter_anteil", lambda: 99.3)

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

    mess = koerper.index("gezeichneter_anteil()")
    taste = koerper.index('"F11"')
    assert mess < taste, "F11 wird geschickt, bevor gemessen wurde"

    # Und der Rueckweg ohne Korrektur muss es geben: liegt die Flaeche schon ueber der
    # Schwelle, darf NICHTS gesendet werden.
    assert "VOLLBILD_SCHWELLE" in koerper, "es gibt keine Schwelle, ab der nichts passiert"
    assert re.search(r">= VOLLBILD_SCHWELLE:\s*\n\s*return", koerper), \
        "ueber der Schwelle wird nicht frueh zurueckgekehrt — F11 traefe auch den Gutfall"
