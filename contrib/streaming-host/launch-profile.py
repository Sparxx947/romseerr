#!/usr/bin/env python3
"""Startprofil je Emulator: Controller-Belegung und regionsrichtiges BIOS.
/ Launch profile per emulator: controller mapping and region-correct BIOS.

WARUM DAS UEBERHAUPT GEHT, OHNE JEDEN CONTROLLER EINZELN ZU KENNEN:
Zwei Normierungen liegen bereits dazwischen. Der Browser bildet ueber die Gamepad-API
jedes physische Pad auf das "Standard Gamepad" ab, und Selkies reicht das als EIN
virtuelles Xbox-Pad in den Container. Der Emulator sieht deshalb nie "ein DualSense",
sondern immer dieselbe Xbox-Belegung. Eine Zuordnung je Emulator genuegt damit fuer
ALLE Controller — die Arbeit waechst mit der Zahl der Emulatoren, nicht der Pads.

Two normalisations already sit in between: the browser maps any pad to the standard
gamepad layout, and Selkies presents that as one virtual Xbox pad. So an emulator always
sees the same layout, and one mapping per emulator covers every controller.

WAS ES NICHT TUT: bestehende Einstellungen ueberschreiben. Die Tastaturbelegung bleibt
— PCSX2 speichert Alternativen als WIEDERHOLTE Schluessel, nicht als Liste mit Trenner
(`&` ist dort der Akkord, also gleichzeitig gedrueckte Tasten). Gamepad und Tastatur
funktionieren danach nebeneinander.

    launch-profile.py --apply pcsx2            # Controller-Belegung setzen
    launch-profile.py --bios pcsx2 Europe      # BIOS zur Region waehlen
    launch-profile.py --status                 # Stand
"""
import os
import re
import subprocess
import sys
import time

CONFIG = os.environ.get("FW_CONFIG_ROOT", "/config")

# PCSX2: Namen aus s_sdl_button_setting_names / s_sdl_axis_setting_names
# (pcsx2/Input/SDLInputSource.cpp) — abgelesen, nicht geraten.
PCSX2 = {
    "Up": "DPadUp", "Down": "DPadDown", "Left": "DPadLeft", "Right": "DPadRight",
    "Cross": "FaceSouth", "Circle": "FaceEast", "Square": "FaceWest", "Triangle": "FaceNorth",
    "Select": "Back", "Start": "Start",
    "L1": "LeftShoulder", "R1": "RightShoulder",
    "L3": "LeftStick", "R3": "RightStick",
    "L2": "+LeftTrigger", "R2": "+RightTrigger",
    "LUp": "-LeftY", "LDown": "+LeftY", "LLeft": "-LeftX", "LRight": "+LeftX",
    "RUp": "-RightY", "RDown": "+RightY", "RLeft": "-RightX", "RRight": "+RightX",
    "Analog": "Guide",
}


def pcsx2_ini():
    return os.path.join(CONFIG, ".config/PCSX2/inis/PCSX2.ini")


def pcsx2_apply(pruefen=False):
    """-> (geaendert, meldung). Fuegt SDL-Belegungen im Abschnitt [Pad1] hinzu."""
    pfad = pcsx2_ini()
    if not os.path.isfile(pfad):
        return False, "PCSX2.ini gibt es noch nicht — der Emulator legt sie beim ersten Start an"

    with open(pfad, encoding="utf-8", errors="ignore") as f:
        zeilen = f.read().splitlines()

    # Abschnitt [Pad1] finden. Ohne ihn gibt es nichts zu ergaenzen; ihn selbst
    # anzulegen waere geraten — PCSX2 schreibt dort mehr als nur Tastenbelegungen.
    start = None
    for i, z in enumerate(zeilen):
        if z.strip() == "[Pad1]":
            start = i
            break
    if start is None:
        return False, "kein [Pad1] in der PCSX2.ini"
    ende = len(zeilen)
    for i in range(start + 1, len(zeilen)):
        if zeilen[i].startswith("["):
            ende = i
            break

    block = zeilen[start + 1:ende]
    vorhanden = {z for z in block if "SDL-0/" in z}
    neu = []
    for taste, sdl in PCSX2.items():
        zeile = f"{taste} = SDL-0/{sdl}"
        if not any(z.strip() == zeile for z in vorhanden):
            neu.append(zeile)
    if not neu:
        return False, "Gamepad-Belegung steht bereits"
    if pruefen:
        return True, f"{len(neu)} Belegungen wuerden ergaenzt"

    # Sicherung EINMAL: der Ausgangsstand vor dem ersten Eingriff, nicht der von
    # vorhin. Ein Backup, das bei jedem Lauf ueberschrieben wird, sichert nach dem
    # zweiten Lauf nichts mehr.
    sicherung = pfad + ".vor-gamepad"
    if not os.path.exists(sicherung):
        with open(sicherung, "w", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n")

    zeilen[ende:ende] = neu
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen) + "\n")
    return True, f"{len(neu)} Gamepad-Belegungen ergaenzt (Tastatur bleibt)"


# ---------------------------------------------------------------- BIOS je Region
# Bei der PS2 ist das BIOS REGIONSGEBUNDEN. Ein PAL-Titel auf einem NTSC-BIOS laeuft
# mit falscher Bildwiederholrate, teils gar nicht — und meldet das nicht, er "laeuft
# komisch". Genau die Sorte Fehler, die man stundenlang woanders sucht.
#
# On the PS2 the BIOS is region-bound, and a mismatch does not report itself.
#
# Erkennung in zwei Stufen, absichtlich in dieser Reihenfolge:
#   1. Klartext im Dateinamen (PAL, USA, Japan …) — das schreiben Dumps meistens hin
#   2. die REGIONSZIFFER der Modellnummer (SCPH-xxxxR): 0 = Japan, 1 = USA, 4 = Europa
#
# Nur diese drei Ziffern sind hier hinterlegt, weil nur sie belastbar sind. Alles
# andere bleibt "unbekannt" — lieber keine Zuordnung als eine erratene, die still das
# falsche BIOS waehlt.
# Only those three digits are encoded, because only those are certain; anything else
# stays unknown rather than becoming a guess that silently picks the wrong BIOS.
REGION_WORT = {
    "europe": "Europe", "eur": "Europe", "pal": "Europe", "germany": "Europe",
    "france": "Europe", "spain": "Europe", "italy": "Europe", "uk": "Europe",
    "usa": "USA", "us": "USA", "ntsc-u": "USA", "america": "USA",
    "japan": "Japan", "jpn": "Japan", "jap": "Japan", "ntsc-j": "Japan",
}
MODELL_ZIFFER = {"0": "Japan", "1": "USA", "4": "Europe"}


def bios_region(dateiname):
    """-> 'Europe' | 'USA' | 'Japan' | '' (unbekannt)."""
    klein = dateiname.lower()
    for wort, region in REGION_WORT.items():
        if re.search(r"(?<![a-z])" + re.escape(wort) + r"(?![a-z])", klein):
            return region
    m = re.search(r"scph[-_ ]?(\d{5})", klein)
    if m:
        return MODELL_ZIFFER.get(m.group(1)[-1], "")
    return ""


def ps2_bios_waehlen(region):
    """-> (dateiname, meldung). Waehlt das BIOS zur Region aus dem Bestand."""
    ordner = os.path.join(CONFIG, ".config/PCSX2/bios")
    if not os.path.isdir(ordner):
        return "", "kein BIOS-Verzeichnis"
    # Nur echte BIOS-Abbilder: 4 MiB. rom1/rom2/EROM sind Beiwerk und keine Auswahl.
    kandidaten = []
    for f in sorted(os.listdir(ordner)):
        voll = os.path.join(ordner, f)
        if os.path.isfile(voll) and os.path.getsize(voll) == 4 * 1024 * 1024:
            kandidaten.append((f, bios_region(f)))
    if not kandidaten:
        return "", "kein 4-MiB-BIOS gefunden"
    passend = [f for f, r in kandidaten if r and r == region]
    if passend:
        return passend[0], f"{region}: {passend[0]}"
    # Nichts Passendes: NICHT still das erste nehmen. Der Aufrufer soll sagen koennen,
    # welches BIOS fehlt — ein schwarzes Bild erklaert sich sonst nie.
    hab = ", ".join(sorted({r or "unbekannt" for _, r in kandidaten}))
    return "", f"kein BIOS fuer {region or 'unbekannte Region'} (vorhanden: {hab})"


def pcsx2_bios_setzen(region):
    """-> (geaendert, meldung). Traegt das BIOS in [Filenames] ein."""
    pfad = pcsx2_ini()
    if not os.path.isfile(pfad):
        return False, "PCSX2.ini gibt es noch nicht"
    datei, meldung = ps2_bios_waehlen(region)
    if not datei:
        return False, meldung
    zeilen = open(pfad, encoding="utf-8", errors="ignore").read().splitlines()
    start = next((i for i, z in enumerate(zeilen) if z.strip() == "[Filenames]"), None)
    if start is None:
        return False, "kein [Filenames] in der PCSX2.ini"
    for i in range(start + 1, len(zeilen)):
        if zeilen[i].startswith("["):
            break
        if zeilen[i].split("=")[0].strip() == "BIOS":
            if zeilen[i].split("=", 1)[1].strip() == datei:
                return False, f"BIOS steht bereits auf {datei}"
            zeilen[i] = f"BIOS = {datei}"
            open(pfad, "w", encoding="utf-8").write("\n".join(zeilen) + "\n")
            return True, meldung
    return False, "kein BIOS-Eintrag in [Filenames]"


def _ini_setzen(pfad, abschnitt, schluessel, wert):
    """Einen Schluessel in einem [Abschnitt] setzen. -> (geaendert, meldung)."""
    if not os.path.isfile(pfad):
        return False, "Konfigurationsdatei gibt es noch nicht"
    zeilen = open(pfad, encoding="utf-8", errors="ignore").read().splitlines()
    start = next((i for i, z in enumerate(zeilen) if z.strip() == abschnitt), None)
    if start is None:
        return False, f"kein {abschnitt}"
    for i in range(start + 1, len(zeilen)):
        if zeilen[i].startswith("["):
            break
        if zeilen[i].split("=")[0].strip() == schluessel:
            if zeilen[i].split("=", 1)[1].strip() == wert:
                return False, f"{schluessel} steht bereits auf {wert}"
            zeilen[i] = f"{schluessel} = {wert}"
            open(pfad, "w", encoding="utf-8").write("\n".join(zeilen) + "\n")
            return True, f"{schluessel} = {wert}"
    return False, f"kein {schluessel} in {abschnitt}"


def pcsx2_vollbild():
    """PCSX2 startet im Vollbild.

    WARUM DER EIGENE SCHALTER UND NICHT DER FENSTERTRICK: Gemessen — PCSX2 setzt seine
    Fenstergroesse SELBST zurueck. `xdotool` schob es auf 1024x768, Sekunden spaeter
    stand wieder 1025x648 mit Panel-Versatz. Gegen die Fensterverwaltung eines
    Emulators anzuarbeiten ist ein Wettlauf, den man nicht gewinnt. Wo ein Emulator
    einen Schalter hat, ist der die Wahrheit; der Fenstertrick bleibt der Rueckfall
    fuer die, die keinen haben.
    Measured: PCSX2 restores its own geometry, so the window trick loses the race.
    Where an emulator has its own switch, that switch is authoritative.
    """
    return _ini_setzen(pcsx2_ini(), "[UI]", "StartFullscreen", "true")


# ------------------------------------------------------------------ RPCS3 (PS3)
# Der Standard von RPCS3 bindet Spieler 1 an die TASTATUR. Solange niemand im
# Einstellungsdialog etwas anfasst, schreibt es ueberhaupt keine Eingabekonfiguration —
# `input_configs/` existiert dann gar nicht. Am laufenden Host nachgemessen: Selkies
# liefert das Pad, RPCS3 zaehlt es sogar auf, und im Spiel passiert nichts. (#156)
#
# RPCS3's default binds player 1 to the KEYBOARD and writes no input config at all
# until someone opens its settings dialog.
#
# DER GERAETENAME IST NICHT GERATEN, SONDERN ABGELESEN. Aus RPCS3s Log:
#   SDL: Found game pad 1: name='Microsoft X-Box 360 pad'
#   SDL: Adding empty device: SDL Device 1        <- vorher, mit falschem Namen
# Er ist stabil, weil Selkies jedes physische Pad auf EIN virtuelles Xbox-Pad abbildet
# (siehe Kopf dieser Datei) — der Emulator sieht nie "einen DualSense". Ueber
# RPCS3_PAD_NAME trotzdem ueberschreibbar, falls ein Abbild das anders benennt.
# DER INDEX AM ENDE GEHOERT DAZU. RPCS3 unterscheidet die fuenf identischen
# virtuellen Pads, die Selkies bereitstellt, durch eine angehaengte Nummer. Ohne sie
# nimmt es das Geraet zwar an, aber ohne Belegung — im Log steht dann
# "Adding empty device", und das Pad tut im Spiel nichts.
# Abgelesen aus der Datei, die RPCS3 nach dem Einrichten von Hand selbst geschrieben
# hat. (#160)
# The trailing index matters: RPCS3 disambiguates the identical virtual pads.
#
# DER NAME HAT SICH MIT DER GAMEPAD-BRUECKE GEAENDERT (2026-08-10, #119). Solange die
# Pads ueber Selkies' Interposer kamen, meldete SDL den rohen Namen
# `Microsoft X-Box 360 pad`. Die Bruecke legt jetzt ECHTE Kernel-Geraete an, und SDL
# erkennt sie an VID/PID (0x45e/0x28e) als bekannten Controller — es benutzt dann den
# Namen aus seiner eigenen Datenbank: `Xbox 360 Controller`. Gemessen im RPCS3-Log:
#
#   SDL: Found game pad 1: name='Xbox 360 Controller', path='/dev/input/event3'
#   SDL: Adding empty device: Microsoft X-Box 360 pad 1     <- alter Name, ins Leere
#   Pad 0: device='Xbox 360 Controller 1', handler=SDL      <- nach der Korrektur
#
# ERKENNUNGSMERKMAL, wenn der Name je wieder wandert: "Adding empty device" im Log.
# Das Pad wird angenommen, hat aber keine Belegung und tut im Spiel nichts — von aussen
# ununterscheidbar von einem defekten Controller.
# EN: the name changed when real kernel devices replaced the interposer's dummies: SDL
# recognises them by VID/PID and uses its own database name. Watch for "Adding empty
# device" in the log — the pad is accepted but bound to nothing.
RPCS3_PAD = os.environ.get("RPCS3_PAD_NAME", "Xbox 360 Controller 1")

# Die Belegung selbst — abgelesen aus der Datei, die RPCS3 nach dem Einrichten im
# Pad-Dialog geschrieben hat, nicht aus der Dokumentation.
#
# WARUM SIE HIER STEHT: Bis 2026-08-10 legte dieses Profil nur Handler und Geraet an,
# und die Tastenbelegung musste EINMAL von Hand im Dialog gesetzt werden. Auf einer
# frischen Maschine hiess das: Pad wird erkannt, Spiel startet, nichts reagiert — und
# der Grund stand nur im Log ("config=" leer). Mit der vollstaendigen Belegung ist ein
# frisch eingerichteter Host sofort spielbar.
#
# `PS Button` ist bewusst zusammengesetzt: der Guide-Knopf allein wird von manchen
# Pads gar nicht gemeldet, deshalb zusaetzlich die Kombination Back+Start.
# EN: read from the file RPCS3 itself wrote after configuring the pad by hand. Until
# now only handler and device were written and the mapping had to be set manually once,
# which on a fresh host looks like a dead controller.
RPCS3_BELEGUNG = [
    ("Left Stick Left", "LS X-"), ("Left Stick Down", "LS Y-"),
    ("Left Stick Right", "LS X+"), ("Left Stick Up", "LS Y+"),
    ("Right Stick Left", "RS X-"), ("Right Stick Down", "RS Y-"),
    ("Right Stick Right", "RS X+"), ("Right Stick Up", "RS Y+"),
    ("Start", "Start"), ("Select", "Back"),
    ("PS Button", '"Back&Start,Guide"'),
    ("Square", "West"), ("Cross", "South"), ("Circle", "East"), ("Triangle", "North"),
    ("Left", "Left"), ("Down", "Down"), ("Right", "Right"), ("Up", "Up"),
    ("R1", "RB"), ("R2", "RT"), ("R3", "RS"),
    ("L1", "LB"), ("L2", "LT"), ("L3", "LS"),
]


def rpcs3_input():
    return os.path.join(CONFIG, ".config/rpcs3/input_configs/global/Default.yml")


def rpcs3_apply(pruefen=False):
    """-> (geaendert, meldung). Legt Handler, Geraet UND Belegung an, wenn nichts da ist.

    WAS DAS TUT: RPCS3s Standard bindet Spieler 1 an die Tastatur und schreibt bis zum
    ersten Griff in den Einstellungsdialog gar keine Konfiguration. Frueher legte dieses
    Profil nur Handler und Geraet an — RPCS3 ergaenzt naemlich KEINE Standardbelegung,
    im Log steht dann

        Input: Pad 0: device='...', handler=SDL
        Input: Pad 0: config=            <- leer
        SDL: Adding empty device: ...

    und im Spiel passiert nichts. Die Belegung musste einmal von Hand gesetzt werden.
    Seit 2026-08-10 wird sie mitgeliefert (`RPCS3_BELEGUNG`), damit ein frisch
    eingerichteter Host sofort spielbar ist.
    EN: RPCS3 adds no default mapping of its own, so an empty config looks like a dead
    controller; the mapping now ships with the profile.

    UND DESHALB WIRD NIE UEBERSCHRIEBEN: Das Profil laeuft VOR JEDEM Start. Wuerde es
    eine vorhandene Datei ersetzen, waere die von Hand gesetzte Belegung beim naechsten
    Start weg — lautlos, und es haette die Arbeit des Nutzers zunichte gemacht. Das war
    im ersten Wurf tatsaechlich so. (#158)
    Never overwrites: the profile runs before every launch, so replacing an existing
    file would silently discard the mapping the operator set by hand.
    """
    pfad = rpcs3_input()
    soll = ('Player 1 Input:\n'
            '  Handler: SDL\n'
            f'  Device: "{RPCS3_PAD}"\n'
            '  Config:\n'
            + "".join(f"    {k}: {v}\n" for k, v in RPCS3_BELEGUNG))
    if os.path.isfile(pfad):
        return False, "Konfiguration vorhanden — unveraendert gelassen"
    if pruefen:
        return True, "SDL-Handler wuerde angelegt (Belegung bleibt zu setzen)"
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    # Sicherung EINMAL, wie bei PCSX2: der Ausgangsstand, nicht der von vorhin.
    sicherung = pfad + ".vor-gamepad"
    if os.path.isfile(pfad) and not os.path.exists(sicherung):
        try:
            with open(pfad, encoding="utf-8", errors="ignore") as a, \
                 open(sicherung, "w", encoding="utf-8") as b:
                b.write(a.read())
        except OSError:
            pass
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(soll)
    return True, (f"SDL-Handler und Belegung angelegt ({len(RPCS3_BELEGUNG)} Eintraege), "
                  f"Geraet '{RPCS3_PAD}'")


# ------------------------------------------------------------- Dolphin (GameCube/Wii)
# Dolphin laeuft ohne diese Einstellung EINKERNIG. Am laufenden Host nachgemessen: ein
# einzelner Thread namens "CPU-GPU thread" bei 100 %, waehrend 27 Threads brachlagen.
# Mit Dual Core teilt sich die Arbeit auf CPU- und Video-Thread. Die offizielle
# Leistungsanleitung nennt das "one of the biggest performance boosts available".
#
# WAS ES NICHT LOEST: Der Engpass WANDERT damit auf den Video-Thread, der weiterhin
# einen Kern saettigt — unabhaengig von Aufloesung und Bildrate. Ursache ist der
# VirtualGL-Umweg, nicht Dolphin. Siehe #167 und #169. Dual Core ist trotzdem richtig:
# es verteilt die Arbeit dorthin, wo Platz ist.
# Dual core moves the bottleneck to the video thread rather than removing it; the
# VirtualGL detour is the actual cause.
# DuckStation benutzt DIESELBEN Schluessel wie PCSX2 (`Cross`, `L1`, `LUp`) — aber bei
# den vier Gesichtstasten andere WERTE. Aus dem Quelltext abgelesen
# (`src/util/sdl_input_source.cpp`, Tabelle `s_button_info`), nicht geraten:
#
#   A, B, X, Y  |  LeftShoulder, RightShoulder  |  DPadUp/Down/Left/Right
#   Back, Guide, Start  |  LeftStick, RightStick
#   Achsen: LeftX, LeftY, RightX, RightY, LeftTrigger, RightTrigger
#
# Alle uebrigen 21 Werte sind mit PCSX2 identisch — deshalb eine Abweichungstabelle
# statt einer zweiten Vollliste, die beim naechsten Umbau auseinanderliefe.
#
# ZWEI FEHLSCHLUESSE AUF DEM WEG HIERHIN, beide dieselbe Sorte:
#   1. "Die Schluessel stimmen, also stimmen die Werte" — falsch, `FaceSouth` gibt es
#      hier nicht. Ergebnis: Stick und Steuerkreuz gingen, die Tasten nicht.
#   2. `strings duckstation-qt | grep -x South` fand die Zeichenkette, und ich hielt
#      das fuer den Beweis. **Eine vorhandene Zeichenkette sagt nichts darueber, wofuer
#      sie verwendet wird** — `South` steht dort in ganz anderem Zusammenhang.
# DuckStation ignoriert einen unbekannten Wert stillschweigend, wie Dolphin und RPCS3
# auch; eine halb falsche Belegung sieht deshalb aus wie ein halb defekter Controller.
#
# EN: same keys as PCSX2 but different values for the four face buttons, read from
# s_button_info in sdl_input_source.cpp. Note the second wrong turn: finding a string
# in the binary proves it exists, not what it is used for.
DUCKSTATION_ANDERS = {
    "FaceSouth": "A", "FaceEast": "B",
    "FaceWest": "X", "FaceNorth": "Y",
}


def duckstation_ini():
    return os.path.join(CONFIG, ".local/share/duckstation/settings.ini")


def duckstation_apply(pruefen=False):
    """-> (geaendert, meldung). Legt Spieler 1 auf das gebrueckte Gamepad.

    DuckStation benutzt DIESELBEN Tastennamen wie PCSX2 (`Cross`, `L1`, `LUp`, …) und
    dieselbe SDL-Quelle — am laufenden Host in seiner `settings.ini` nachgesehen, nicht
    angenommen. Deshalb wird hier die vorhandene Tabelle wiederverwendet statt einer
    zweiten danebengestellt: zwei Listen mit denselben Namen laufen auseinander, sobald
    jemand nur eine pflegt.
    EN: DuckStation uses the same binding names and SDL source as PCSX2 (verified in its
    settings.ini on the running host), so the existing table is reused rather than
    duplicated.

    Anders als bei PCSX2 steht hier je Taste nur EIN Wert: DuckStation fuehrt pro
    Schluessel eine Zeile, PCSX2 erlaubt mehrere. Die Tastaturbelegung von Spieler 1
    weicht daher dem Gamepad; der Rueckweg liegt als `.vor-gamepad` daneben.
    """
    pfad = duckstation_ini()
    if not os.path.isfile(pfad):
        return False, "settings.ini gibt es noch nicht — der Emulator legt sie beim ersten Start an"

    with open(pfad, encoding="utf-8", errors="ignore") as f:
        zeilen = f.read().splitlines()

    # ERSTLAUFDIALOG ABSCHALTEN, sonst ist die Belegung wertlos: DuckStation oeffnet beim
    # ersten Start einen modalen "Setup Wizard". Im Container sieht den niemand, und
    # dahinter staut sich alles — gemessen: der Prozess lief, das Fenster hiess
    # "DuckStation Setup Wizard", ein Spiel startete nie. Mit dem Schalter bootet
    # derselbe Aufruf direkt in den Titel (nachgewiesen an "Spyro the Dragon", 1920x1080).
    # Dieselbe Falle wie RPCS3s Willkommensfenster und JDownloaders Rueckfragen.
    # EN: without this, DuckStation opens a modal setup wizard nobody can see in a
    # container and every launch stalls behind it.
    # Auf den WERT pruefen, nicht auf die Existenz des Schluessels: DuckStation setzt
    # ihn beim Beenden wieder auf `true`, solange der Assistent nie durchlaufen wurde.
    # Eine Pruefung auf "steht der Schluessel da?" haelt das fuer erledigt — und beim
    # naechsten Start oeffnet der Dialog erneut. Genau so ist es passiert (2026-08-10).
    # EN: check the value, not the key: DuckStation resets it to true on exit, so a
    # presence check considers it done while the wizard reappears on the next launch.
    wizard_falsch = not any(
        z.split("=")[0].strip() == "SetupWizardIncomplete"
        and z.split("=", 1)[-1].strip().lower() == "false"
        for z in zeilen)

    start = next((i for i, z in enumerate(zeilen) if z.strip() == "[Pad1]"), None)
    if start is None:
        return False, "kein [Pad1] in der settings.ini"
    ende = next((i for i in range(start + 1, len(zeilen))
                 if zeilen[i].startswith("[")), len(zeilen))

    block = zeilen[start + 1:ende]
    # `Type` bleibt, wie er ist: AnalogController ist DuckStations Standard, aber wer
    # ihn bewusst auf DigitalController gestellt hat, soll das behalten.
    behalten = [z for z in block if z.split("=")[0].strip() == "Type"]
    neu = [f"{taste} = SDL-0/{DUCKSTATION_ANDERS.get(sdl, sdl)}"
           for taste, sdl in sorted(PCSX2.items())]

    vorher = [z for z in block if z.strip()]
    nachher = behalten + neu
    pad_fehlt = vorher != nachher
    if not pad_fehlt and not wizard_falsch:
        return False, "Gamepad-Belegung und Erstlaufdialog stehen bereits"
    if pruefen:
        was = []
        if pad_fehlt:
            was.append(f"{len(neu)} Belegungen")
        if wizard_falsch:
            was.append("Erstlaufdialog")
        return True, " und ".join(was) + " wuerden gesetzt"

    sicherung = pfad + ".vor-gamepad"
    if not os.path.exists(sicherung):
        with open(sicherung, "w", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n")

    if pad_fehlt:
        zeilen[start + 1:ende] = nachher + [""]
    # Den Schalter ZULETZT einsetzen: er steht in [Main], also VOR [Pad1], und wuerde
    # die oben bestimmten Indizes sonst verschieben.
    # EN: insert last — [Main] precedes [Pad1] and would shift the indices computed above.
    if wizard_falsch:
        # Vorhandene Zeile ERSETZEN, nicht eine zweite danebenlegen: DuckStation hat den
        # Schluessel meist schon (auf `true`), und zwei widersprechende Eintraege waeren
        # eine Wette darauf, welchen es liest.
        # EN: replace the existing key instead of adding a second, contradicting one.
        vorhanden = next((i for i, z in enumerate(zeilen)
                          if z.split("=")[0].strip() == "SetupWizardIncomplete"), None)
        if vorhanden is not None:
            zeilen[vorhanden] = "SetupWizardIncomplete = false"
        else:
            try:
                zeilen.insert(zeilen.index("[Main]") + 1, "SetupWizardIncomplete = false")
            except ValueError:
                pass      # kein [Main] — dann ist die Datei nicht die erwartete

    with open(pfad, "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen) + "\n")
    getan = []
    if pad_fehlt:
        getan.append(f"{len(neu)} Gamepad-Belegungen (Spieler 1)")
    if wizard_falsch:
        getan.append("Erstlaufdialog abgeschaltet")
    return True, ", ".join(getan)


def dolphin_ini():
    return os.path.join(CONFIG, ".config/dolphin-emu/Dolphin.ini")


def dolphin_gcpad_ini():
    return os.path.join(CONFIG, ".config/dolphin-emu/GCPadNew.ini")


# GEMESSEN, nicht abgeleitet: Dolphin hat diese Schreibweisen am 2026-08-10 SELBST in
# die Datei geschrieben, nachdem in der Oberflaeche eine Taste und eine Achse zugewiesen
# wurden. Die Asymmetrie ist der Grund, warum Raten hier scheitert:
#
#   Tasten -> Name des Ereigniscodes OHNE `BTN_`-Praefix und ohne Zeichen:  SOUTH
#   Achsen -> durchnummeriert, in schraegen Anfuehrungszeichen:             `Axis 1-`
#
# Vorher stand hier `BTN_A` und `ABS_Y-`. Beides ist falsch, und **Dolphin ignoriert
# unbekannte Eingaenge stillschweigend** — die Belegung stand vollstaendig da und tat
# nichts. Kein Fehler, keine Meldung, kein Hinweis in der Oberflaeche.
#
# EN: measured, not guessed — Dolphin wrote these spellings itself. Buttons use the
# event-code name without the BTN_ prefix; axes are numbered. Dolphin silently ignores
# inputs it cannot resolve, so a wrong spelling looks exactly like a working config.
#
# Die Achsennummern folgen der aufsteigenden ABS-Code-Reihenfolge des Geraets:
#   0=ABS_X 1=ABS_Y 2=ABS_Z(LT) 3=ABS_RX 4=ABS_RY 5=ABS_RZ(RT) 6=HAT0X 7=HAT0Y
KALIBRIERUNG = "100.00 141.42 100.00 141.42 100.00 141.42 100.00 141.42"
DOLPHIN_PAD = [
    ("Buttons/A", "SOUTH"),
    ("Buttons/B", "EAST"),
    ("Buttons/X", "NORTH"),
    ("Buttons/Y", "WEST"),
    ("Buttons/Z", "TR"),
    ("Buttons/Start", "START"),
    ("Main Stick/Up", "`Axis 1-`"),
    ("Main Stick/Down", "`Axis 1+`"),
    ("Main Stick/Left", "`Axis 0-`"),
    ("Main Stick/Right", "`Axis 0+`"),
    ("Main Stick/Calibration", KALIBRIERUNG),
    ("C-Stick/Up", "`Axis 4-`"),
    ("C-Stick/Down", "`Axis 4+`"),
    ("C-Stick/Left", "`Axis 3-`"),
    ("C-Stick/Right", "`Axis 3+`"),
    ("C-Stick/Calibration", KALIBRIERUNG),
    # L liegt zusaetzlich auf der Schultertaste: die Trigger-Achse ruht bei -32767,
    # nicht bei 0, deshalb greift `Axis 2+` erst ab etwa halbem Druck.
    # EN: the trigger axis rests at -32767, so the analog half only engages past centre.
    ("Triggers/L", "TL"),
    ("Triggers/R", "`Axis 5+`"),
    ("Triggers/L-Analog", "`Axis 2+`"),
    ("Triggers/R-Analog", "`Axis 5+`"),
    ("D-Pad/Up", "`Axis 7-`"),
    ("D-Pad/Down", "`Axis 7+`"),
    ("D-Pad/Left", "`Axis 6-`"),
    ("D-Pad/Right", "`Axis 6+`"),
]

# Ueberschreibbar, falls ein Abbild das gebrueckte Pad anders benennt — genauso wie
# RPCS3_PAD_NAME. Der Index 0 ist Selkies' Slot 0, weil die Bruecke ihre Geraete in
# Socket-Reihenfolge anlegt. / EN: overridable; index 0 is Selkies' slot 0.
DOLPHIN_GERAET = os.environ.get("DOLPHIN_PAD_NAME",
                                "evdev/0/Microsoft X-Box 360 pad")


def dolphin_gcpad(pruefen=False):
    """-> (geaendert, meldung). Legt GameCube-Port 1 auf das gebrueckte Gamepad.

    Ersetzt ausschliesslich den Abschnitt `[GCPad1]`; die Ports 2 bis 4 bleiben, wie sie
    sind. Die Tastaturbelegung von Port 1 entfaellt dabei — Dolphin bindet einen Port an
    GENAU EIN Geraet, und ein zweites Geraet liesse sich nur ueber voll qualifizierte
    Ausdruecke dazunehmen. Der Rueckweg liegt als `.vor-gamepad` daneben.
    EN: Dolphin binds one port to exactly one device, so the keyboard mapping of port 1
    is replaced; ports 2-4 are untouched and a backup is kept.
    """
    pfad = dolphin_gcpad_ini()
    block = ["[GCPad1]", f"Device = {DOLPHIN_GERAET}"]
    block += [f"{schluessel} = {wert}" for schluessel, wert in DOLPHIN_PAD]

    if os.path.isfile(pfad):
        with open(pfad, encoding="utf-8", errors="ignore") as f:
            zeilen = f.read().splitlines()
    else:
        zeilen = []

    start = next((i for i, z in enumerate(zeilen) if z.strip() == "[GCPad1]"), None)
    if start is None:
        if pruefen:
            return True, "GCPad1 wuerde angelegt"
        zeilen = block + ([""] + zeilen if zeilen else [])
    else:
        ende = next((i for i in range(start + 1, len(zeilen))
                     if zeilen[i].startswith("[")), len(zeilen))
        if [z.strip() for z in zeilen[start:ende] if z.strip()] == block:
            return False, "Gamepad-Belegung steht bereits"
        if pruefen:
            return True, "Gamepad-Belegung wuerde gesetzt"
        # Sicherung EINMAL, vom Ausgangsstand — nicht bei jedem Lauf neu.
        sicherung = pfad + ".vor-gamepad"
        if not os.path.exists(sicherung):
            with open(sicherung, "w", encoding="utf-8") as f:
                f.write("\n".join(zeilen) + "\n")
        zeilen[start:ende] = block

    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen) + "\n")
    return True, f"GameCube-Port 1 auf {DOLPHIN_GERAET} gelegt"


def dolphin_apply(pruefen=False):
    """-> (geaendert, meldung). Gamepad-Belegung UND Dual Core.

    Die Funktion stand schon vorher unter `controller` in der Profiltabelle, setzte aber
    ausschliesslich Dual Core — der Eintrag behauptete etwas, das der Code nicht tat.
    Genau deshalb kam am GameCube nie ein Controller an, obwohl die Bruecke lief.
    EN: this was listed as the controller step while only ever setting dual core.
    """
    geaendert = []
    for schritt in (dolphin_gcpad, dolphin_dualcore):
        tat, meldung = schritt(pruefen)
        if tat:
            geaendert.append(meldung)
    if not geaendert:
        return False, "Gamepad-Belegung und Dual Core stehen bereits"
    return True, "; ".join(geaendert)


def dolphin_dualcore(pruefen=False):
    """-> (geaendert, meldung). Schaltet Dual Core ein (CPUThread)."""
    pfad = dolphin_ini()
    if not os.path.isfile(pfad):
        return False, "Dolphin.ini gibt es noch nicht — der Emulator legt sie beim ersten Start an"
    zeilen = open(pfad, encoding="utf-8", errors="ignore").read().splitlines()
    for z in zeilen:
        if z.split("=")[0].strip() == "CPUThread" and z.split("=", 1)[-1].strip() == "True":
            return False, "Dual Core steht bereits"
    if pruefen:
        return True, "Dual Core wuerde gesetzt"
    # `_ini_setzen` ERSETZT nur einen vorhandenen Schluessel. Dolphin schreibt CPUThread
    # aber gar nicht erst hin, solange niemand es umstellt — der Standard steht nur im
    # Code. Also einfuegen statt ersetzen, und den Abschnitt notfalls anlegen.
    # _ini_setzen only replaces an existing key; Dolphin never writes this one.
    geaendert, meldung = _ini_setzen(pfad, "[Core]", "CPUThread", "True")
    if geaendert or "bereits" in meldung:
        return geaendert, meldung
    start = next((i for i, z in enumerate(zeilen) if z.strip() == "[Core]"), None)
    if start is None:
        zeilen += ["[Core]"]
        start = len(zeilen) - 1
    zeilen.insert(start + 1, "CPUThread = True")
    open(pfad, "w", encoding="utf-8").write("\n".join(zeilen) + "\n")
    return True, "Dual Core eingeschaltet (CPUThread)"


# JEDER bereitgestellte Emulator steht hier — auch der, der nichts braucht.
#
# WARUM AUSDRUECKLICH STATT WEGGELASSEN: Ein fehlender Eintrag ist nicht von einem
# "braucht nichts" zu unterscheiden. Wer einen Emulator hinzufuegt, soll gezwungen
# sein, sich zu entscheiden — und wer spaeter hierher sieht, soll erkennen, was
# geprueft wurde und was nur noch nicht drankam. Ein Test haelt die Liste mit dem
# Katalog in 20-emulators zusammen.
#
# Every provided emulator appears here, including those needing nothing: an absent
# entry is indistinguishable from "nothing needed", and adding an emulator must force
# a decision. A test keeps this list in step with the catalogue.
#
#   controller: Funktion oder None (None = ordnet ein SDL-Pad selbst zu)
#   bios:       Funktion oder None (None = braucht kein BIOS zum Starten)
#   geprueft:   Ist das am laufenden Emulator NACHGEMESSEN oder nur angenommen?
PROFILE = {
    # geprueft: Bild und Gamepad im Spiel bestaetigt (2026-08-10). Bis dahin drei
    # Anlaeufe — Erstlaufdialog, dann PCSX2s Face*-Namen, dann `South` aus dem Binary.
    # Erst der Quelltext (`s_button_info`) lieferte A/B/X/Y.
    "duckstation": {"system": "PS1",         "controller": duckstation_apply,
                    "bios": None, "vollbild": None,
                    "geprueft": True},
    "pcsx2":     {"system": "PS2",           "controller": pcsx2_apply,
                  "bios": pcsx2_bios_setzen, "vollbild": pcsx2_vollbild,
                  "geprueft": True},
    # geprueft: Bild, Ton UND Gamepad sind am laufenden System bestaetigt — der
    # Controller von einem Menschen in Metroid Prime, nicht aus einem Log geschlossen.
    # (2026-08-10, #119)
    "dolphin":   {"system": "GameCube/Wii",  "controller": dolphin_apply,
                  "bios": None, "vollbild": None,
                  "geprueft": True},
    "flycast":   {"system": "Dreamcast",     "controller": None, "bios": None, "vollbild": None,
                  "geprueft": False},
    "xemu":      {"system": "Xbox",          "controller": None, "bios": None, "vollbild": None,
                  "geprueft": False},
    "cemu":      {"system": "Wii U",         "controller": None, "bios": None, "vollbild": None,
                  "geprueft": False},
    "azahar":    {"system": "3DS",           "controller": None, "bios": None, "vollbild": None,
                  "geprueft": False},
    "vita3k":    {"system": "PS Vita",       "controller": None, "bios": None, "vollbild": None,
                  "geprueft": False},
    # geprueft: Bild, Ton und Gamepad im Spiel bestaetigt (2026-08-10, #119). Dass die
    # Warnung „Adding empty device" verschwindet, war nur der Hinweis — den Nachweis
    # hat ein Mensch am Pad erbracht.
    "rpcs3":     {"system": "PS3",           "controller": rpcs3_apply,
                  "bios": None, "vollbild": None,
                  "geprueft": True},
    "switchemu": {"system": "Switch",        "controller": None, "bios": None, "vollbild": None,
                  "geprueft": False},
}
# "geprueft: False" heisst NICHT "funktioniert nicht", sondern "noch nicht am
# laufenden Emulator nachgemessen". Die Unterscheidung ist der Punkt: sie zeigt, wo
# eine Zusage auf Messung beruht und wo auf Annahme. Siehe #136.


# --------------------------------------------------------- Nur das Emulatorfenster
# Der Stream zeigt sonst den ganzen XFCE-Desktop: Panel, Fensterrahmen, Raender. Das
# kostet Bildflaeche (und damit Bandbreite), laedt zu Fehlklicks ein, und ein
# verlorener Fokus bedeutet einen stummen Controller.
#
# BEWUSST EMULATORUNABHAENGIG: Jeder Emulator hat einen anderen Vollbild-Schalter, und
# einige haben gar keinen. Statt neun Sonderfaelle zu pflegen, wird das FENSTER
# behandelt — das koennen alle, weil es keiner von ihnen tun muss.
#
# Deliberately emulator-agnostic: every emulator has a different fullscreen switch and
# some have none, so the WINDOW is handled instead of nine special cases.
#
# `xdotool windowstate` gaebe es dafuer, ist aber erst ab 3.2021 dabei; hier liegt
# 3.2016. Deshalb der klassische Weg: _MOTIF_WM_HINTS entfernt die Dekoration, und
# Groesse/Position kommen von der Bildschirmgeometrie.
XPROP_KEINE_DEKO = ["-f", "_MOTIF_WM_HINTS", "32c", "-set", "_MOTIF_WM_HINTS", "2, 0, 0, 0, 0"]


def _x(*args, **kw):
    umg = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":1")}
    return subprocess.run(args, capture_output=True, text=True, env=umg, timeout=20, **kw)


def sichtbare_fenster(pid):
    """Sichtbare Fenster des Prozesses, groesstes zuerst.

    `--onlyvisible` ist wichtig: Emulatoren legen unsichtbare Hilfsfenster an, und ohne
    den Filter erwischt man eines davon. Beim ersten Anlauf hier genau passiert — das
    Skript meldete Erfolg an einem Fenster, das niemand sieht, waehrend das Spielfenster
    unveraendert danebenstand.
    Without --onlyvisible one grabs a helper window and reports success on something
    nobody sees, which is exactly what happened on the first attempt."""
    r = _x("xdotool", "search", "--onlyvisible", "--pid", str(pid))
    mit_flaeche = []
    for i in [z for z in r.stdout.split() if z.strip()]:
        g = _x("xdotool", "getwindowgeometry", "--shell", i).stdout
        masse = dict(z.split("=", 1) for z in g.strip().splitlines() if "=" in z)
        try:
            f = int(masse.get("WIDTH", 0)) * int(masse.get("HEIGHT", 0))
        except ValueError:
            f = 0
        if f > 10000:                     # echte Fenster, keine Platzhalter
            mit_flaeche.append((f, i))
    return [i for _f, i in sorted(mit_flaeche, reverse=True)]


def fenster_von_pid(pid, versuche=20):
    """Groesstes sichtbares Fenster. Ein Emulator braucht Sekunden bis dahin."""
    for _ in range(versuche):
        ids = sichtbare_fenster(pid)
        if ids:
            return ids[0]
        time.sleep(1)
    return ""


def _fenster_fuellen(fid, b, h):
    # REIHENFOLGE ZAEHLT: erst Groesse, dann Position. Andersherum schiebt xfwm4 das
    # Fenster beim Vergroessern wieder unter die Panel-Zeile — gemessen: y=50 statt 0,
    # also genau die Panelhoehe. Und danach noch einmal setzen, weil der
    # Fenstermanager auf die Groessenaenderung selbst mit einer Positionierung
    # antwortet.
    # Order matters: size first, then position, then position again — xfwm4 answers a
    # resize with a reposition, which put the window back under the panel row.
    _x("xprop", "-id", fid, *XPROP_KEINE_DEKO)
    _x("xdotool", "windowsize", fid, b, h)
    _x("xdotool", "windowmove", fid, "0", "0")
    _x("xdotool", "windowactivate", "--sync", fid)
    _x("xdotool", "windowraise", fid)
    time.sleep(0.4)
    _x("xdotool", "windowmove", fid, "0", "0")


def nur_emulator(pid, runden=3, pause=6):
    """-> (ok, meldung). Panel weg, Dekoration weg, Fenster auf volle Flaeche.

    MEHRERE RUNDEN, weil das SPIELFENSTER spaeter entsteht als das erste Fenster des
    Emulators. Einmalig anzuwenden traf beim ersten Anlauf ein Hilfsfenster, meldete
    Erfolg, und der Nutzer sah weiter den Desktop. Deshalb wird nach dem Start noch
    ein paar Mal nachgesehen, ob ein neues, groesseres Fenster dazugekommen ist.
    Several rounds because the game window appears after the first one; applying once
    reported success on a helper window while the user still saw the desktop."""
    breite_hoehe = _x("xdotool", "getdisplaygeometry").stdout.split()
    if len(breite_hoehe) != 2:
        return False, "Bildschirmgroesse nicht ermittelbar"
    b, h = breite_hoehe
    if not fenster_von_pid(pid):
        return False, "kein sichtbares Fenster zum Prozess gefunden"
    # Panel ausblenden. Schlaegt es fehl, ist das kein Grund abzubrechen — ein Fenster
    # ueber dem Panel ist immer noch besser als ein Desktop.
    _x("xfconf-query", "-c", "xfce4-panel", "-p", "/panels/panel-1/autohide-behavior",
       "-t", "int", "-s", "2", "--create")
    behandelt = set()
    for runde in range(runden):
        for fid in sichtbare_fenster(pid):
            _fenster_fuellen(fid, b, h)
            behandelt.add(fid)
        if runde < runden - 1:
            time.sleep(pause)
    if not behandelt:
        return False, "kein sichtbares Fenster"
    return True, f"{len(behandelt)} Fenster auf {b}x{h}, ohne Rahmen, Panel ausgeblendet"


def panel_zurueck():
    """Nach der Sitzung: Desktop wieder bedienbar. Ein Panel, das versteckt bleibt,
    macht den Host unbenutzbar fuer alles, was eine GUI braucht — etwa das Einrichten
    eines Emulators."""
    _x("xfconf-query", "-c", "xfce4-panel", "-p", "/panels/panel-1/autohide-behavior",
       "-t", "int", "-s", "0", "--create")


def rechte_hinweis(pfad):
    """-> lesbarer Hinweis, warum eine Datei nicht zugaenglich ist.

    WOZU: Ein `PermissionError` verlaesst dieses Programm sonst als Traceback im
    Agent-Log — der Schritt bricht ab, BIOS und Vollbild werden nicht gesetzt, und der
    Emulator startet mit einem Dialog statt mit dem Spiel. Von aussen sieht das aus wie
    "der Stream geht auf, aber es startet kein Spiel". Genau so passiert (2026-08-10).
    EN: a PermissionError otherwise leaves as a traceback, the step aborts, and the
    emulator comes up with a dialog instead of the game.
    """
    try:
        st = os.stat(pfad)
    except OSError:
        return f"{pfad} nicht lesbar"
    import pwd
    def name(uid):
        try:
            return pwd.getpwuid(uid).pw_name
        except KeyError:
            return str(uid)
    return (f"{pfad} gehoert {name(st.st_uid)} (Modus {oct(st.st_mode)[-3:]}), "
            f"wir sind {name(os.geteuid())} — Abhilfe: "
            f"chown {name(os.geteuid())} '{pfad}'")


def sicher(schritt, *args, **kw):
    """Einen Profilschritt ausfuehren und Rechtefehler in Klartext uebersetzen.

    Fehlende Rechte sind hier der Normalfall des Scheiterns, seit Emulatoren nicht mehr
    als root laufen: alles, was frueher als root geschrieben wurde, gehoert root und ist
    mit Modus 600 fuer niemanden sonst lesbar.
    EN: missing permissions are the expected failure mode since emulators stopped
    running as root; anything written back then is root-owned and mode 600.
    """
    try:
        return schritt(*args, **kw)
    except PermissionError as e:
        return False, "KEIN ZUGRIFF: " + rechte_hinweis(e.filename or "?")


def main(argv):
    if argv and argv[0] == "--fullscreen":
        if len(argv) < 2 or argv[1] not in PROFILE:
            print("Aufruf: --fullscreen <emulator>", file=sys.stderr); return 1
        fn = PROFILE[argv[1]].get("vollbild")
        if not fn:
            print(f"[vollbild] {argv[1]}: kein eigener Schalter — Fenstertrick greift")
            return 2                       # 2 = Rueckfall noetig
        geaendert, msg = sicher(fn)
        print(f"[vollbild] {argv[1]}: {msg}")
        return 0
    if argv and argv[0] == "--window":
        if len(argv) < 2 or not argv[1].isdigit():
            print("Aufruf: --window <pid>", file=sys.stderr); return 1
        ok, msg = nur_emulator(int(argv[1]))
        print(f"[fenster] {msg}")
        return 0 if ok else 1
    if argv and argv[0] == "--desktop":
        panel_zurueck(); print("[fenster] Panel wieder eingeblendet"); return 0
    if argv and argv[0] == "--bios":
        if len(argv) < 3 or argv[1] not in PROFILE:
            print("Aufruf: --bios <emulator> <Region>", file=sys.stderr); return 1
        fn = PROFILE[argv[1]]["bios"]
        if not fn:
            print(f"[bios] {argv[1]}: braucht kein BIOS zum Starten")
            return 0
        geaendert, msg = sicher(fn, argv[2])
        print(f"[bios] {argv[1]}: {msg}")
        return 0 if geaendert or "bereits" in msg else 1
    if not argv or argv[0] not in ("--apply", "--status"):
        print(__doc__.strip().splitlines()[-3], file=sys.stderr)
        return 2
    if argv[0] == "--status":
        for name, e in PROFILE.items():
            teile = []
            if e["controller"]:
                noetig, msg = sicher(e["controller"], pruefen=True)
                teile.append(("offen" if noetig else "gesetzt") + f" ({msg})")
            else:
                teile.append("Controller: eigene Zuordnung")
            teile.append("BIOS: regionsabhaengig" if e["bios"] else "BIOS: keins noetig")
            teile.append("gemessen" if e["geprueft"] else "UNGEPRUEFT")
            print(f"{name} ({e['system']}): " + " | ".join(teile))
        return 0
    ziel = argv[1] if len(argv) > 1 else ""
    if ziel not in PROFILE:
        print(f"kein Profil fuer '{ziel}' / no profile for it", file=sys.stderr)
        return 1
    fn = PROFILE[ziel]["controller"]
    if not fn:
        print(f"[controller] {ziel}: ordnet ein erkanntes SDL-Pad selbst zu")
        return 0
    geaendert, msg = sicher(fn)
    print(f"[controller] {ziel}: {msg}")
    # Ein Rechtefehler ist KEIN Erfolg. Frueher verliess er das Programm als Traceback,
    # der Rueckgabewert blieb 0, und der Agent startete den Emulator ohne gesetztes
    # BIOS und ohne Vollbild — das Ergebnis war ein Dialog statt eines Spiels.
    # EN: a permission error is not success; it used to leave as a traceback while the
    # exit code stayed 0 and the emulator came up unconfigured.
    return 1 if msg.startswith("KEIN ZUGRIFF") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
