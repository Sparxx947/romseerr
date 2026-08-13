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
    launch-profile.py --dialogs vita3k         # Startdialoge abstellen
    launch-profile.py --grundbild              # leeren Desktop aufnehmen (vor dem Start)
    launch-profile.py --status                 # Stand
"""
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time

CONFIG = os.environ.get("FW_CONFIG_ROOT", "/config")
# Flycasts Renderer-Kennziffern: 0 und 3 sind OpenGL, 4 und 5 Vulkan
# (5 mit Per-Pixel-Sortierung). 4 ist der Wert, den die Startzeile seit #304
# mitgibt — hier steht er, damit beide Wege dieselbe Zahl meinen.
FLYCAST_RENDERER = "4"

# xemus Renderer. Anders als bei Flycast ist das keine Kennziffer, sondern ein Name aus
# `CONFIG_DISPLAY_RENDERER__COUNT` — im Binary abgelesen, nicht geraten. Seit #498 laeuft
# xemu OHNE VirtualGL; ohne diesen Eintrag landete OpenGL dann auf dem Software-Rasterer.
XEMU_RENDERER = "VULKAN"

# Cemus Audio-Backend als Kennziffer. Die Reihenfolge stammt aus Cemus eigener
# Startausgabe (DirectSound, XAudio 2.8, XAudio 2.7, Cubeb) — abgelesen, nicht geraten.
# Nur Cubeb ist im Container verfuegbar; die Vorgabe 0 (DirectSound) laesst Cemu stumm
# laufen, ohne dass etwas fehlschlaegt. (#541)
CEMU_AUDIO_API = "3"

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


# ZWEI MODALE FENSTER FANGEN JEDEN PSX-START AB. (#492)
#
# Dieselbe Klasse Falle wie DuckStations Setup-Wizard oben und Vita3Ks Willkommensfenster
# (#488): ein Fenster, das im Container niemand sieht und wegklickt, und der Start staut
# sich dahinter. NACHGEMESSEN am laufenden Host (2026-08-13, „Sheep" (PAL), DuckStation
# 0.1-11609-ga233ec1fb), jeder Schalter mit Gegenprobe:
#
#   NoDesktopFile | CheckAtStartup     | Fenster
#   (fehlt)       | (fehlt)            | nur "DuckStation" 500x193 — KEIN Spielfenster
#   true          | (fehlt)            | Spiel + "Automatic Updater" 651x474 mittendrauf
#   true          | false              | Spiel, kein Dialog; Fensterschritt meldet "ok"
#   true          | true  (Gegenprobe) | "Automatic Updater" wieder da
#   (entfernt)    | false (Gegenprobe) | "DuckStation" wieder da, kein Spielfenster
#
# WOHER DER ERSTE WERT KOMMT: nicht aus den Zeichenketten der Binaerdatei, sondern aus dem
# Dialog selbst. Er hat ein Kaestchen „Don't ask again"; nach einem Klick darauf schrieb
# DuckStation GENAU EINE neue Zeile in die settings.ini — `[Main] NoDesktopFile = true`,
# sonst nichts (Schluesselmengen vorher/nachher verglichen). Der zweite Wert ist am
# Verhalten gemessen; `[AutoUpdater] CheckAtStartup` steht in der Voreinstellung gar
# nicht in der Datei.
#
# WARUM HIER ANGEHAENGT WIRD UND BEI VITA3K NICHT: Vita3Ks `config.yml` fuehrt JEDEN
# Schluessel, ein fehlender heisst dort „die Fassung hat ihn umbenannt". DuckStations
# settings.ini fuehrt nur, was vom Standard abweicht — beide Schalter fehlen im
# Auslieferungszustand, und „nichts anhaengen" hiesse hier „nie etwas tun". Dass ein
# angehaengter Eintrag WIRKT, ist gemessen (Zeile 3 und 4 der Tabelle).
#
# EN: two modal windows catch every PSX launch. Both values measured on the running host
# with a counter-check per switch; the first was written by DuckStation itself after
# ticking "Don't ask again". Unlike Vita3K's config.yml, DuckStation's settings.ini only
# lists non-default keys, so a missing key must be appended, not reported.
DUCKSTATION_DIALOGE = (
    ("Main",        "NoDesktopFile",  "true",  "Verknuepfungs-Abfrage"),
    ("AutoUpdater", "CheckAtStartup", "false", "Update-Abfrage"),
)


# WARUM NEBEN `_ini_setzen` OBEN: Das aeltere Geschwister nimmt einen PFAD, liest und
# schreibt selbst und ERSETZT nur einen vorhandenen Schluessel — genau richtig fuer den
# einen Schalter, den PCSX2 und Dolphin brauchen. Hier sind es ZWEI Schalter in EINER
# Datei, einer davon in einem Abschnitt, den es noch gar nicht gibt: das braucht eine
# Zeilenliste, die zwischen den Schritten weitergereicht wird, und einen Anlegeweg.
# Zwei Aufgaben, zwei Werkzeuge — das aeltere umzubauen haette drei belegte Behebungen
# angefasst, um eine neue zu bauen.
# EN: the older `_ini_setzen` takes a path and only replaces existing keys; these work on
# a line list and can create a missing section.
def _zeilen_abschnitt(zeilen, name):
    """-> (erste, hinter_letzter) Zeile INNERHALB von `[name]`, oder None."""
    kopf = f"[{name}]"
    i = next((k for k, z in enumerate(zeilen) if z.strip() == kopf), None)
    if i is None:
        return None
    ende = next((k for k in range(i + 1, len(zeilen))
                 if zeilen[k].lstrip().startswith("[")), len(zeilen))
    return i + 1, ende


def _zeilen_wert(zeilen, abschnitt, schluessel):
    """-> Wert in Kleinschreibung, oder None. Nur IM genannten Abschnitt gesucht.

    Der Abschnitt gehoert zur Frage: `settings.ini` fuehrt denselben Schluesselnamen in
    mehreren Abschnitten, und ein Treffer im falschen waere eine falsche Auskunft.
    """
    bereich = _zeilen_abschnitt(zeilen, abschnitt)
    if bereich is None:
        return None
    for z in zeilen[bereich[0]:bereich[1]]:
        if "=" in z and z.split("=")[0].strip() == schluessel:
            return z.split("=", 1)[1].strip().lower()
    return None


def _zeilen_setzen(zeilen, abschnitt, schluessel, wert):
    """-> neue Zeilenliste, in der `[abschnitt] schluessel = wert` steht.

    Drei Faelle, und der mittlere ist der, an dem es schiefgeht: eine vorhandene Zeile
    wird ERSETZT statt eine zweite danebengelegt (zwei widersprechende Eintraege waeren
    eine Wette darauf, welchen der Emulator liest), ein fehlender Schluessel kommt ans
    Ende SEINES Abschnitts (ans Dateiende gehaengt gehoerte er der letzten Sektion,
    nicht `[Main]`), und ein fehlender Abschnitt wird angelegt.
    """
    zeile = f"{schluessel} = {wert}"
    bereich = _zeilen_abschnitt(zeilen, abschnitt)
    if bereich is None:
        rand = [] if not zeilen or not zeilen[-1].strip() else [""]
        return zeilen + rand + [f"[{abschnitt}]", zeile]
    anfang, ende = bereich
    for k in range(anfang, ende):
        if "=" in zeilen[k] and zeilen[k].split("=")[0].strip() == schluessel:
            return zeilen[:k] + [zeile] + zeilen[k + 1:]
    # Hinter die letzte NICHT leere Zeile des Abschnitts, nicht hinter dessen Leerzeile:
    # sonst stuende der Eintrag optisch beim naechsten Abschnitt.
    letzte = max((k for k in range(anfang, ende) if zeilen[k].strip()), default=anfang - 1)
    return zeilen[:letzte + 1] + [zeile] + zeilen[letzte + 1:]


def duckstation_dialoge(pruefen=False):
    """-> (geaendert, meldung). Die beiden Startdialoge abstellen. (#492)

    Zwei Regeln wie ueberall hier: NICHTS ANLEGEN, wenn die Datei fehlt — der Emulator
    schreibt sie beim ersten Start, und eine von uns erfundene koennte Felder vermissen
    lassen. Und geprueft wird der WERT, nicht das Vorhandensein des Schluessels; genau
    daran kam der Setup-Wizard zweimal zurueck.

    NICHT HIER, sondern weiter oben in `duckstation_apply`: `SetupWizardIncomplete`. Der
    sitzt im Gamepad-Schritt, weil der ohnehin dieselbe Datei aufmacht, ist dort gemessen
    und getestet — ihn nur der Ordnung halber umzuziehen hiesse, eine belegte Behebung
    gegen eine unbelegte zu tauschen.

    EN: same two rules as everywhere here — never create the file, and go by the value,
    not by the key. `SetupWizardIncomplete` stays in `duckstation_apply`.
    """
    pfad = duckstation_ini()
    if not os.path.isfile(pfad):
        return False, "settings.ini gibt es noch nicht — der Emulator legt sie beim ersten Start an"
    try:
        with open(pfad, encoding="utf-8", errors="ignore") as f:
            zeilen = f.read().splitlines()
    except OSError as e:
        return False, f"settings.ini nicht lesbar: {e.strerror}"

    # Ohne `[Main]` ist das nicht DuckStations settings.ini. Dieselbe Absage wie im
    # Gamepad-Schritt: einen Schalter in eine fremde Datei zu schreiben wirkt nicht und
    # meldete trotzdem Erfolg.
    if _zeilen_abschnitt(zeilen, "Main") is None:
        return False, "kein [Main] in der settings.ini — nicht die erwartete Datei"

    offen = [e for e in DUCKSTATION_DIALOGE
             if _zeilen_wert(zeilen, e[0], e[1]) != e[2]]
    if not offen:
        return False, "die Startdialoge stehen bereits ab"
    if pruefen:
        return True, "wuerde abstellen: " + ", ".join(n for *_, n in offen)

    sicherung = pfad + ".vor-dialogen"
    if not os.path.exists(sicherung):
        try:
            with open(sicherung, "w", encoding="utf-8") as f:
                f.write("\n".join(zeilen) + "\n")
        except OSError:
            pass                      # ohne Rueckweg, aber nicht ohne Behebung
    for abschnitt, schluessel, wert, _ in offen:
        zeilen = _zeilen_setzen(zeilen, abschnitt, schluessel, wert)
    try:
        with open(pfad, "w", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n")
    except OSError as e:
        return False, f"settings.ini nicht schreibbar: {e.strerror}"
    return True, "abgestellt: " + ", ".join(n for *_, n in offen)


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


def dolphin_wiimote_ini():
    return os.path.join(CONFIG, ".config/dolphin-emu/WiimoteNew.ini")


# WIIMOTE-BELEGUNG (#297). Zwei Vokabulare treffen hier aufeinander, und BEIDE sind
# abgelesen, keines geraten:
#
#   Steuernamen (links)  aus der vorhandenen `WiimoteNew.ini`, die Dolphin selbst
#                        angelegt hat — `Buttons/1`, `IR/Up`, `Shake/X`, `Nunchuk/…`
#   Eingaenge (rechts)   aus `GCPadNew.ini`, wo dieselbe Schreibweise nachweislich
#                        funktioniert (siehe DOLPHIN_PAD)
#
# WAS DEN AUSSCHLAG GAB: `SELECT` und `MODE` kommen in der GameCube-Datei NICHT vor.
# Waeren sie von dort abgeleitet worden, blieben Minus und Home leer. Sie stammen aus
# einer Messung am Geraet selbst:
#
#   BTN_A BTN_B BTN_NORTH BTN_WEST BTN_TL BTN_TR BTN_SELECT BTN_START BTN_MODE
#   BTN_THUMBL BTN_THUMBR
#   ABS_X ABS_Y ABS_Z ABS_RX ABS_RY ABS_RZ ABS_HAT0X ABS_HAT0Y
#
# Das ist die Liste, die die Bruecke wirklich anlegt — nicht die, die ein Xbox-Pad
# ueblicherweise hat.
#
# ZWEI ENTSCHEIDUNGEN, die keine Messung sind und deshalb hier stehen:
#
#   1. `Tilt` UND `Nunchuk/Stick` liegen beide auf dem linken Stick. Ein Spiel liest
#      entweder Neigung oder Nunchuk, nie beides — sie stoeren sich also nicht, und
#      eine Umschaltung je Spiel waere Aufwand ohne Gegenwert.
#   2. `B` liegt auf dem rechten Trigger, nicht auf einer Taste: Am echten Geraet ist B
#      der Abzug an der Unterseite.
#
# `Tilt/Forward` ist ZUSAMMENGESETZT: die Gruppe `Tilt` stammt aus der Dolphin-Binaerdatei,
# die Richtungsnamen aus `IMUAccelerometer/Forward` derselben Datei. Beide Haelften sind
# belegt, die Verbindung war es nicht — bis ein Mensch am Pad bestaetigt hat, dass das
# Kippen ankommt (2026-08-13, Kororinpa).
#
# EN: both vocabularies are read, not guessed — control names from the file Dolphin wrote
# itself, input spellings from the GameCube file where they demonstrably work. SELECT and
# MODE come from measuring the device, because the GameCube file never uses them. Two
# choices are judgement, not measurement: tilt and the nunchuk stick share the left stick,
# and B sits on the right trigger because that is where it is on the real device.
DOLPHIN_WIIMOTE = [
    ("Buttons/A", "SOUTH"),
    ("Buttons/B", "`Axis 5+`"),
    ("Buttons/1", "WEST"),
    ("Buttons/2", "NORTH"),
    ("Buttons/-", "SELECT"),
    ("Buttons/+", "START"),
    ("Buttons/Home", "MODE"),
    ("D-Pad/Up", "`Axis 7-`"),
    ("D-Pad/Down", "`Axis 7+`"),
    ("D-Pad/Left", "`Axis 6-`"),
    ("D-Pad/Right", "`Axis 6+`"),
    ("IR/Up", "`Axis 4-`"),
    ("IR/Down", "`Axis 4+`"),
    ("IR/Left", "`Axis 3-`"),
    ("IR/Right", "`Axis 3+`"),
    ("Tilt/Forward", "`Axis 1+`"),
    ("Tilt/Backward", "`Axis 1-`"),
    ("Tilt/Left", "`Axis 0-`"),
    ("Tilt/Right", "`Axis 0+`"),
    ("Shake/X", "TL"),
    ("Shake/Y", "TL"),
    ("Shake/Z", "TL"),
    ("Extension", "Nunchuk"),
    ("Nunchuk/Buttons/C", "THUMBL"),
    ("Nunchuk/Buttons/Z", "`Axis 2+`"),
    ("Nunchuk/Stick/Up", "`Axis 1-`"),
    ("Nunchuk/Stick/Down", "`Axis 1+`"),
    ("Nunchuk/Stick/Left", "`Axis 0-`"),
    ("Nunchuk/Stick/Right", "`Axis 0+`"),
    ("Nunchuk/Stick/Calibration", KALIBRIERUNG),
]


def dolphin_wiimote(pruefen=False):
    """-> (geaendert, meldung). Legt Wii-Remote 1 auf das gebrueckte Gamepad. (#297)

    WARUM ES DAS BRAUCHT, obwohl der GameCube-Controller laengst ging: Dolphin fuehrt
    beide Belegungen in GETRENNTEN Dateien, und nur `GCPadNew.ini` war gesetzt. Gemessen
    am laufenden Host:

        GCPadNew.ini    Device = evdev/0/Microsoft X-Box 360 pad     <- funktionierte
        WiimoteNew.ini  Device = XInput2/0/Virtual core pointer      <- Mausklicks

    `Buttons/A = ``Click 1``` — die Wii-Remote hing am X11-Zeiger. Ein Wii-Titel bekam
    also nie eine Eingabe, waehrend derselbe Emulator am GameCube tadellos lief. Von
    aussen sah das nach einem kaputten Controller aus.

    Nur `[Wiimote1]` wird ersetzt; Wiimote 2 bis 4 und das Balance Board bleiben stehen.
    Rueckweg als `.vor-gamepad` daneben.

    EN: Dolphin keeps the two mappings in separate files and only the GameCube one was
    set — the Wii Remote was bound to the X11 pointer, so Wii titles received nothing
    while the same emulator worked fine on GameCube.
    """
    pfad = dolphin_wiimote_ini()
    block = ["[Wiimote1]", f"Device = {DOLPHIN_GERAET}"]
    block += [f"{schluessel} = {wert}" for schluessel, wert in DOLPHIN_WIIMOTE]

    if os.path.isfile(pfad):
        with open(pfad, encoding="utf-8", errors="ignore") as f:
            zeilen = f.read().splitlines()
    else:
        zeilen = []

    start = next((i for i, z in enumerate(zeilen) if z.strip() == "[Wiimote1]"), None)
    if start is None:
        if pruefen:
            return True, "Wiimote1 wuerde angelegt"
        zeilen = block + ([""] + zeilen if zeilen else [])
    else:
        ende = next((i for i in range(start + 1, len(zeilen))
                     if zeilen[i].startswith("[")), len(zeilen))
        if [z.strip() for z in zeilen[start:ende] if z.strip()] == block:
            return False, "Wii-Remote-Belegung steht bereits"
        if pruefen:
            return True, "Wii-Remote haengt nicht am Pad"
        sicherung = pfad + ".vor-gamepad"
        if not os.path.exists(sicherung):
            with open(sicherung, "w", encoding="utf-8") as f:
                f.write("\n".join(zeilen) + "\n")
        zeilen[start:ende] = block

    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen) + "\n")
    return True, f"Wii-Remote 1 auf {DOLPHIN_GERAET} gelegt"


def dolphin_apply(pruefen=False):
    """-> (geaendert, meldung). Gamepad-Belegung UND Dual Core.

    Die Funktion stand schon vorher unter `controller` in der Profiltabelle, setzte aber
    ausschliesslich Dual Core — der Eintrag behauptete etwas, das der Code nicht tat.
    Genau deshalb kam am GameCube nie ein Controller an, obwohl die Bruecke lief.
    EN: this was listed as the controller step while only ever setting dual core.
    """
    geaendert = []
    for schritt in (dolphin_gcpad, dolphin_wiimote, dolphin_dualcore):
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
def xemu_vollbild():
    """xemu ins Vollbild schalten — per TASTE, nicht per Konfiguration.

    DREI WEGE PROBIERT, nur einer wirkt (alles am laufenden Host gemessen, #300):

    1. `fullscreen = true` in der `xemu.toml`: wird beim Start **ignoriert**. Das
       Fenster oeffnet weiter in 1280x960.
    2. Der Fenstertrick (`nur_emulator`): vergroessert die X-Fenster-HUELLE auf
       1920x1080, aber xemus GL-Bereich waechst NICHT mit — sichtbar bleibt ein
       960 Pixel breiter Ausschnitt in einem 1920 breiten Fenster. Bei Dolphin und
       PCSX2 greift derselbe Trick, bei xemu nicht.
    3. **F11 an das Fenster**: wirkt. Der gezeichnete Bereich waechst sofort mit.

    Deshalb steht hier eine Tastensendung statt eines Konfigurationsschluessels — und
    deshalb muss sie NACH dem Start kommen, nicht davor.
    """
    return f11_vollbild("xemu")


def f11_vollbild(fenstername):
    """F11 an das Fenster schicken. -> (ok, meldung).

    Gemeinsamer Weg fuer alle Emulatoren, bei denen der Fenstertrick die HUELLE
    vergroessert und der gezeichnete Bereich nicht mitwaechst. Gemessen wurde jeder
    einzelne — geraten wird hier nichts:

    | Emulator | Fenstertrick | nach F11 |
    |---|---|---|
    | xemu   | 960 von 1920 breit | wirkt (#306) |
    | Azahar | 53,3 % der Flaeche | **99,3 %** (#316) |
    | Eden   | 88,6 % der Flaeche | **99,3 %** (#316) |

    WIE GEMESSEN: nicht mit `xdotool getwindowgeometry` — das meldete in allen drei
    Faellen brav 1920x1080, waehrend das Bild kleiner war. Stattdessen `xwd -root` und
    darin der Rahmen der nicht-schwarzen Pixel. Die Fenstergroesse ist genau die Zahl,
    die hier nichts beweist.

    EN: shared route for emulators whose drawn area does not follow the window. Each was
    measured with `xwd`, not with window geometry — that reported 1920x1080 in all three
    cases while the picture was smaller.
    """
    fenster = _x("xdotool", "search", "--onlyvisible",
                 "--name", fenstername).stdout.split()
    if not fenster:
        return False, f"kein {fenstername}-Fenster gefunden — laeuft der Emulator?"
    fid = fenster[0]
    _x("xdotool", "windowactivate", fid)
    time.sleep(1)
    _x("xdotool", "key", "--window", fid, "F11")
    return True, "Vollbild ueber F11 geschaltet"


def azahar_vollbild():
    """Azahar ins Vollbild — F11, nicht der Fenstertrick. (#316)

    NACHGEMESSEN am laufenden Host mit `Shovel_Knight_EUR_MULTi5_3DS.3ds`: Nach dem
    Fenstertrick war das Fenster 1920x1080 und BEMALT waren 1915x577 — 53,3 %, die untere
    Haelfte blieb schwarz. Zweimal gemessen, um einen Ladezustand auszuschliessen: gleiches
    Ergebnis. Nach F11: 99,3 %.

    Das ist der Fall, den #316 fuer Azahar vermutet hat, und er ist eingetreten.
    """
    return f11_vollbild("Azahar")


def eden_vollbild():
    """Eden (Switch) ins Vollbild — ebenfalls F11. (#316)

    NACHGEMESSEN mit `Arcade Archives DIG DUG`: Der Fenstertrick liess einen gleichmaessigen
    Rand von etwa 36 Pixeln ringsum stehen — 88,6 %. Das ist ein anderes Fehlerbild als bei
    Azahar (nicht die halbe Flaeche schwarz, sondern ein Rahmen), aber dieselbe Abhilfe:
    nach F11 sind es 99,3 %.

    Ein Rand von 36 Pixeln faellt beim Zusehen kaum auf. Genau deshalb wurde er gemessen
    und nicht beurteilt.
    """
    return f11_vollbild("Eden")


# --------------------------------------------------------------- Azahar (3DS)

def eden_ini():
    return os.path.join(CONFIG, ".config", "eden", "qt-config.ini")


def switchemu_apply(pruefen=False):
    """-> (geaendert, meldung). MELDET, ob Edens Spieler 1 auf einem Pad liegt. (#298)

    SCHREIBT ABSICHTLICH NICHTS. Das ist keine Faulheit, sondern die Regel aus #304:
    Vokabular wird gelesen, nicht geraten. Edens Bindungssyntax steht nicht im Programm
    (`strings` findet keine `engine:`-Zeichenketten), und genau an dieser Abkuerzung ist
    die DuckStation-Reparatur schon einmal gescheitert — eine plausible Vermutung, die
    sich als falsch herausstellte.

    WAS HIER GEMESSEN WURDE, am laufenden Host in `qt-config.ini`:

        player_0_button_a="engine:keyboard,code:67,toggle:0"
        player_0_button_b="engine:keyboard,code:88,toggle:0"
        player_0_lstick="engine:analog_from_button,…keyboard…"

    70 `player_0_*`-Zeilen, keine einzige `guid:`-Angabe. Spieler 1 liegt auf der
    TASTATUR. Die bisherige Einstufung „ordnet ein erkanntes SDL-Pad selbst zu" war eine
    Annahme und ist damit widerlegt.

    Das Fehlerbild ist dasselbe wie bei RPCS3 vor #304: Der Stream geht auf, das Spiel
    laeuft, und der Controller tut nichts — von aussen nicht von „Emulator kaputt" zu
    unterscheiden. Ein stiller Defekt wird hier zu einer Zeile im Protokoll; mehr kann
    diese Funktion ehrlicherweise nicht leisten.

    DER WEG ZUR ECHTEN REPARATUR: Eden einmal selbst ein Pad zuordnen lassen (in seiner
    Oberflaeche) und die entstandene Datei vergleichen — so wurde Dolphins Schreibweise
    gefunden. Das braucht einen Menschen an der Oberflaeche, nicht mehr Raten.

    EN: reports, does not write. Eden's binding vocabulary is not readable from the
    binary, and guessing it is exactly the shortcut that produced a wrong answer for
    DuckStation. Measured: player 1 is bound to the keyboard, with no guid anywhere —
    the previous "maps an SDL pad itself" was an assumption and is disproved.
    """
    pfad = eden_ini()
    if not os.path.isfile(pfad):
        return False, "qt-config.ini gibt es noch nicht — Eden legt sie beim ersten Start an"
    with open(pfad, encoding="utf-8", errors="ignore") as f:
        text = f.read()
    zeilen = [z for z in text.splitlines() if z.startswith("player_0_button_a=")]
    if not zeilen:
        return False, "keine Belegung fuer Spieler 1 gefunden — Eden hat noch nichts geschrieben"
    belegung = zeilen[0].split("=", 1)[1].strip().strip('"')
    if "guid:" in text or "engine:sdl" in belegung:
        return False, "Spieler 1 liegt auf einem Pad"
    # KEINE Reparatur, aber auch kein Schweigen.
    return False, (f"Spieler 1 liegt auf der TASTATUR ({belegung[:34]}…) — der Controller "
                   "tut im Spiel nichts. Zuordnung einmal in Edens Oberflaeche vornehmen, "
                   "dann kann sie hier festgeschrieben werden (#298)")


def flycast_cfg():
    return os.path.join(CONFIG, ".config", "flycast", "emu.cfg")


def flycast_apply(pruefen=False):
    """-> (geaendert, meldung). Schreibt den Vulkan-Renderer in Flycasts Konfiguration.

    WARUM UEBERHAUPT, wo die Startzeile `-config config:pvr.rend=4` doch mitgibt: weil
    Flycast diesen Wert NICHT uebernimmt. Am laufenden Host nachgemessen — Flycast mit
    dem Renderer auf der Kommandozeile gestartet, Vulkan bestaetigt:

        rend/vulkan/vulkan_context.cpp: Vulkan API 1.1. Device Intel(R) Arc(tm) A310

    danach sauber beendet (die Datei wurde um 12:48:51 neu geschrieben, es lag also
    nicht an einem harten Abbruch) — und in `emu.cfg` steht weiterhin NUR:

        [window]
        fullscreen = yes
        height = 480 …

    Kein `[config]`-Abschnitt. Ein `-config`-Wert ist fuer Flycast fluechtig und
    wandert nie in den gespeicherten Satz.

    DIE FOLGE ist keine Kleinigkeit: Ueber den Start-Dienst laeuft Flycast auf Vulkan,
    ueber den Desktop gestartet auf dem eingebauten Standard. Derselbe Emulator,
    dasselbe Spiel, zwei Verhaltensweisen — und die Ursache steht in einer Zeile, die
    niemand sieht.

    DASS ES TRAEGT, IST GEPRUEFT und nicht angenommen: Wert von Hand eingetragen,
    Flycast gestartet, beendet, Datei erneut gelesen — der Abschnitt stand noch da.
    Flycast liest ihn also und schreibt ihn zurueck.

    GEPRUEFT WIRD DER WERT, NICHT DER SCHLUESSEL. Genau daran ist die DuckStation-
    Reparatur einmal gescheitert: Der Assistent kam wieder, weil nur geprueft wurde, ob
    der Schluessel existiert — und der Emulator ihn beim Beenden auf `true` zurueckschrieb.

    EN: the renderer given on the command line is transient — Flycast never writes it
    back, so the same title runs on Vulkan through the service and on the built-in
    default from the desktop. Verified by hand that a value written into the file does
    survive a full launch/exit cycle. The VALUE is checked, not the key.
    """
    pfad = flycast_cfg()
    if not os.path.isfile(pfad):
        return False, "emu.cfg gibt es noch nicht — Flycast legt sie beim ersten Beenden an"
    with open(pfad, encoding="utf-8", errors="ignore") as f:
        zeilen = f.read().splitlines()

    abschnitt, wert = "", None
    for z in zeilen:
        t = z.strip()
        if t.startswith("[") and t.endswith("]"):
            abschnitt = t[1:-1]
        elif abschnitt == "config" and t.replace(" ", "").startswith("pvr.rend="):
            wert = t.split("=", 1)[1].strip()
    if wert == FLYCAST_RENDERER:
        return False, f"Renderer steht bereits auf {FLYCAST_RENDERER} (Vulkan)"
    if pruefen:
        return True, (f"Renderer steht auf {wert or 'nichts'} statt {FLYCAST_RENDERER}"
                      " — ueber den Desktop gestartet liefe Flycast anders")

    neu, gesetzt, in_config = [], False, False
    for z in zeilen:
        t = z.strip()
        if t.startswith("[") and t.endswith("]"):
            if in_config and not gesetzt:
                neu.append(f"pvr.rend = {FLYCAST_RENDERER}")
                gesetzt = True
            in_config = t == "[config]"
        if in_config and t.replace(" ", "").startswith("pvr.rend="):
            neu.append(f"pvr.rend = {FLYCAST_RENDERER}")
            gesetzt = True
            continue
        neu.append(z)
    if not gesetzt:
        # Kein `[config]`-Abschnitt vorhanden — er gehoert VOR den Rest, damit er nicht
        # versehentlich unter `[window]` landet.
        neu = ["[config]", f"pvr.rend = {FLYCAST_RENDERER}", ""] + neu

    sicherung = pfad + ".vor-renderer"
    if not os.path.exists(sicherung):
        shutil.copy2(pfad, sicherung)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("\n".join(neu) + "\n")
    return True, (f"Renderer auf {FLYCAST_RENDERER} (Vulkan) gesetzt, "
                  f"Rueckweg: {sicherung}")


def xemu_toml():
    return os.path.join(CONFIG, ".local", "share", "xemu", "xemu", "xemu.toml")


def xemu_apply(pruefen=False):
    """-> (geaendert, meldung). Bindet Spieler 1 an das GEBRUECKTE Pad. (#304)

    NACHGEMESSEN, nicht vermutet. Alle acht Joystick-Geraete im Container sind identisch:

        js0..js7   bus=0003 vendor=045e product=028e   Microsoft X-Box 360 pad

    Daraus folgt EINE SDL-Kennung, naemlich die, die in dieser Datei ohnehin schon als
    Kennung des gebrueckten Pads steht. xemus Konfiguration band aber:

        port1 = '000081b84d6963726f736f6674205800'   <- kein anwesendes Geraet
        port2..4 = '030081b85e0400008e02000000010000'

    Die Kennung auf Port 1 hat Bustyp `0000` und traegt statt Vendor/Product den ASCII-Namen
    — so bildet SDL eine Kennung, wenn es ein Geraet NICHT identifizieren kann. Sie ist ein
    Ueberbleibsel; kein aktuelles Geraet hat sie. Ports 2 bis 4 stimmen, ausgerechnet der
    Platz von Spieler 1 nicht.

    WAS HIER NICHT BEHAUPTET WIRD: dass der Controller deshalb tot ist. Ob xemu auf das
    erste verfuegbare Pad zurueckfaellt, wenn die gebundene Kennung fehlt, ist nicht
    gemessen — das braucht jemanden am Pad. Repariert wird es trotzdem: Eine Bindung, die
    ein nicht vorhandenes Geraet benennt, ist unabhaengig vom Rueckfall falsch.

    NUR PORT 1 WIRD ANGEFASST. Ports 2 bis 4 stehen richtig, und wer sie fuer einen zweiten
    Spieler umgestellt hat, soll das behalten.

    EN: all eight devices share one SDL GUID; xemu bound port 1 to a GUID no present device
    carries. Whether xemu falls back is not measured and not claimed — a binding naming an
    absent device is wrong either way. Only port 1 is touched.
    """
    pfad = xemu_toml()
    if not os.path.isfile(pfad):
        return False, "xemu.toml gibt es noch nicht — der Emulator legt sie beim ersten Start an"
    with open(pfad, encoding="utf-8", errors="ignore") as f:
        zeilen = f.read().splitlines()

    aktuell = ""
    for z in zeilen:
        if z.strip().startswith("port1 ="):
            aktuell = z.split("=", 1)[1].strip().strip("'\"")
            break
    if not aktuell:
        return False, "kein port1-Eintrag — xemu hat noch keine Bindung geschrieben"
    if aktuell == PAD_GUID:
        return False, "Spieler 1 liegt bereits auf dem gebrueckten Pad"
    if pruefen:
        return True, f"port1 zeigt auf {aktuell[:8]}… statt auf das gebrueckte Pad"

    neu = []
    for z in zeilen:
        if z.strip().startswith("port1 ="):
            vorne = z[:len(z) - len(z.lstrip())]
            neu.append(f"{vorne}port1 = '{PAD_GUID}'")
        else:
            neu.append(z)
    # Die Kennung muss auch in `gamepad_mappings` stehen, sonst kennt xemu sie nicht.
    if not any(PAD_GUID in z for z in neu):
        return False, "die Kennung des gebrueckten Pads steht nicht in gamepad_mappings"
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("\n".join(neu) + "\n")
    return True, "Spieler 1 auf das gebrueckte Pad gelegt"


def xemu_renderer(pruefen=False):
    """-> (geaendert, meldung). Schreibt den Vulkan-Renderer in xemus Konfiguration. (#498)

    WARUM: Ohne diesen Eintrag laeuft xemu auf OpenGL. Das war solange folgenlos, wie der
    Emulator ueber VirtualGL gestartet wurde — seit #498 tut er das NICHT mehr, und ohne
    Bruecke landet OpenGL auf dem Software-Rasterer. Der Eintrag ist damit kein Feinschliff,
    sondern die Bedingung dafuer, dass die Startzeile ueberhaupt funktioniert.

    WARUM NICHT AUF DER KOMMANDOZEILE: xemu kennt dafuer keinen Schalter. Gepruefte
    Schluesselnamen aus dem Binary (`CONFIG_DISPLAY_RENDERER__COUNT`), nicht geraten.

    NACHGEMESSEN, ein Faktor auf einmal, Fenster in allen drei Zeilen 1920x1080:

        Renderer   vglrun   bemalte Flaeche nach Vollbild
        OpenGL     ja       ~62 %
        Vulkan     ja       62,9 %
        Vulkan     nein     100 %

    Die mittlere Zeile ist die wichtige: Vulkan ALLEIN reicht nicht. Solange VirtualGL
    dazwischen liegt, laeuft die Bildausgabe weiter ueber den abgefangenen GL-Pfad und das
    Bild bleibt beschnitten. Erst beides zusammen wirkt.

    DASS VULKAN GREIFT, ist am Protokoll geprueft und nicht am Vorhandensein der Zeile:

        Selected physical device: Intel(R) Arc(tm) A310 Graphics (DG2)

    Im OpenGL-Lauf steht diese Zeile kein einziges Mal, im Vulkan-Lauf genau einmal.

    GEPRUEFT WIRD DER WERT, NICHT DER SCHLUESSEL — dieselbe Falle wie bei Flycast und
    DuckStation: Ein vorhandener Schluessel mit falschem Wert sieht aus wie Erfolg.

    EN: without this entry xemu renders with OpenGL, which was harmless only while it was
    launched through VirtualGL. Since #498 it no longer is, and unbridged OpenGL falls back
    to the software rasteriser — so this is a precondition, not a refinement. Vulkan alone
    does not fix the crop (middle row); both changes are needed. The VALUE is checked.
    """
    pfad = xemu_toml()
    if not os.path.isfile(pfad):
        return False, "xemu.toml gibt es noch nicht — der Emulator legt sie beim ersten Start an"
    with open(pfad, encoding="utf-8", errors="ignore") as f:
        zeilen = f.read().splitlines()

    abschnitt, wert = "", None
    for z in zeilen:
        t = z.strip()
        if t.startswith("[") and t.endswith("]"):
            abschnitt = t[1:-1]
        elif abschnitt == "display" and t.replace(" ", "").startswith("renderer="):
            wert = t.split("=", 1)[1].strip().strip("'\"")
    if wert == XEMU_RENDERER:
        return False, f"Renderer steht bereits auf {XEMU_RENDERER}"
    if pruefen:
        return True, (f"Renderer steht auf {wert or 'nichts'} statt {XEMU_RENDERER}"
                      " — ohne VirtualGL waere das der Software-Rasterer")

    # `[display]` MUSS VOR `[display.window]` STEHEN. In TOML ist eine Obertabelle nach
    # ihren Untertabellen zwar erlaubt, aber sie hier davorzusetzen macht die Datei auch
    # fuer aeltere Parser eindeutig — und xemu schreibt sie beim Beenden ohnehin neu.
    neu, gesetzt, in_display = [], False, False
    for z in zeilen:
        t = z.strip()
        if t.startswith("[") and t.endswith("]"):
            if in_display and not gesetzt:
                neu.append(f"renderer = '{XEMU_RENDERER}'")
                gesetzt = True
            in_display = t == "[display]"
        if in_display and t.replace(" ", "").startswith("renderer="):
            neu.append(f"renderer = '{XEMU_RENDERER}'")
            gesetzt = True
            continue
        neu.append(z)
    if not gesetzt:
        eingefuegt, fertig = [], False
        for z in neu:
            if not fertig and z.strip().startswith("[display"):
                eingefuegt += ["[display]", f"renderer = '{XEMU_RENDERER}'", ""]
                fertig = True
            eingefuegt.append(z)
        if not fertig:
            eingefuegt += ["", "[display]", f"renderer = '{XEMU_RENDERER}'"]
        neu = eingefuegt

    sicherung = pfad + ".vor-renderer"
    if not os.path.exists(sicherung):
        shutil.copy2(pfad, sicherung)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("\n".join(neu) + "\n")
    return True, f"Renderer auf {XEMU_RENDERER} gesetzt, Rueckweg: {sicherung}"


def cemu_settings():
    return os.path.join(CONFIG, ".config", "Cemu", "settings.xml")


def cemu_audio(pruefen=False):
    """-> (geaendert, meldung). Setzt Cemus Ausgabe auf ein Backend, das es hier gibt. (#541)

    DER FEHLER WAR STILL, und das ist der eigentliche Punkt. Cemu startete, spielte mit
    60 FPS, nahm den Controller an — und war stumm. Fehlgeschlagen ist dabei nichts; im
    Protokoll steht genau eine Zeile, und die sieht harmlos aus:

        ------- Init Audio backend -------
        DirectSound: not supported
        XAudio 2.8: not supported
        XAudio 2.7: not supported
        Cubeb: available
        ------- Run title -------
        can't initialize tv audio: failed to find selected device while trying to create audio device

    Gespeichert war `<api>0</api>` — DirectSound, ein Windows-Backend, das Cemu selbst als
    `not supported` auffuehrt. Es fragt also ein Geraet bei einem Backend an, das es nicht
    gibt, findet keins, und macht weiter.

    DIE NUMMER IST ABGELESEN, NICHT GERATEN: Cemu druckt seine Backends beim Start in der
    Reihenfolge der Aufzaehlung — DirectSound, XAudio 2.8, XAudio 2.7, Cubeb — also 0, 1, 2, 3.

    NACHGEMESSEN, nicht angenommen: Nach der Umstellung erscheint Cemu als aktiver
    Wiedergabestrom am PulseAudio-Server (`Cemu Cubeb`, `Corked: no`), die Fehlerzeile ist
    weg, und ein Mensch hat den Ton an zwei Titeln bestaetigt.

    WAS HIER BEWUSST NICHT STEHT: eine Aenderung an `<delay>`. Bei einem Titel klang der Ton
    zerhackt, und der naheliegende Griff waere der Puffer gewesen. Gemessen half er nicht
    (`<delay>` 2 -> 9 aenderte die Puffer-Latenz nicht einmal, ebensowenig
    `PULSE_LATENCY_MSEC=120`), und die Gegenprobe mit einem zweiten Titel war am Standardwert
    makellos: 0 ms Stille in 8 Sekunden gegen 4040 ms beim ersten. Es lag am Titelbildschirm
    jenes Spiels, nicht an Cemu. Deshalb bleibt der Puffer, wie er ist — eine Einstellung ohne
    belegte Wirkung ist Ballast, den spaeter niemand mehr einzuordnen weiss.

    EN: Cemu stored `<api>0</api>` (DirectSound), which it lists as unsupported here, so it
    asked a non-existent backend for a device and silently ran mute — picture, speed and
    gamepad all fine. The index is read off Cemu's own startup listing. Deliberately does NOT
    touch `<delay>`: raising it changed nothing measurable, and a second title was clean at
    the default, so the chopped audio belonged to one title's attract screen.
    """
    pfad = cemu_settings()
    if not os.path.isfile(pfad):
        return False, "settings.xml gibt es noch nicht — Cemu legt sie beim ersten Beenden an"
    with open(pfad, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    # Der Abschnitt zaehlt: `<api>` steht auch unter `<Overlay>` und anderswo. Wer nur nach
    # `<api>` sucht, trifft irgendeinen und meldet Erfolg fuer den falschen.
    m = re.search(r"<Audio>(.*?)</Audio>", text, re.S)
    if not m:
        return False, "kein <Audio>-Abschnitt in settings.xml"
    innen = m.group(1)
    treffer = re.search(r"<api>\s*(\d+)\s*</api>", innen)
    if not treffer:
        return False, "kein <api>-Eintrag im Audio-Abschnitt"
    if treffer.group(1) == CEMU_AUDIO_API:
        return False, f"Audio steht bereits auf Backend {CEMU_AUDIO_API} (Cubeb)"
    if pruefen:
        return True, (f"Audio steht auf Backend {treffer.group(1)} statt {CEMU_AUDIO_API}"
                      " (Cubeb) — Cemu laeuft dann stumm, ohne dass etwas fehlschlaegt")

    neu_innen = innen[:treffer.start()] + f"<api>{CEMU_AUDIO_API}</api>" + innen[treffer.end():]
    neu = text[:m.start(1)] + neu_innen + text[m.end(1):]
    sicherung = pfad + ".vor-audio"
    if not os.path.exists(sicherung):
        shutil.copy2(pfad, sicherung)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(neu)
    return True, f"Audio auf Backend {CEMU_AUDIO_API} (Cubeb) gesetzt, Rueckweg: {sicherung}"


def cemu_controller_profil():
    return os.path.join(CONFIG, ".config", "Cemu", "controllerProfiles", "controller0.xml")


# CEMUS ZUORDNUNG, WORTGETREU UEBERNOMMEN (#304).
#
# Die Paare sind undurchsichtige Zahlen — `<mapping>` ist Cemus interne Nummer der
# Wii-U-Taste, `<button>` die des SDL-Eingangs. Was welche Zahl bedeutet, steht nirgends
# ausserhalb des Quelltexts von Cemu, und **es muss auch niemand wissen**: Diese Liste
# stammt aus der Datei, die Cemu SELBST geschrieben hat, nachdem in seiner Oberflaeche ein
# Pad hinzugefuegt wurde — und ein Mensch hat sie am 2026-08-13 am Pad bestaetigt.
#
# WARUM NICHT DIE NAMEN NACHSCHLAGEN: Weil jede Uebersetzung eine Fehlerquelle waere, die
# nichts gewinnt. Die Zahlen ohne Umweg zu uebernehmen ist die einzige Fassung, die
# nachweislich funktioniert hat.
#
# EN: opaque numbers on purpose. `<mapping>` is Cemu's internal Wii U button id, `<button>`
# the SDL input id; the meaning lives in Cemu's source. This list is what Cemu itself wrote
# after a pad was added in its UI, confirmed at the pad by a person. Translating the numbers
# into names would only add a place to be wrong.
CEMU_ZUORDNUNG = [
    (24, 40),
    (23, 46),
    (22, 41),
    (21, 47),
    (20, 38),
    (19, 44),
    (18, 39),
    (17, 45),
    (16, 8),
    (15, 7),
    (14, 14),
    (1, 1),
    (2, 0),
    (3, 3),
    (4, 2),
    (5, 9),
    (6, 10),
    (7, 42),
    (8, 43),
    (9, 6),
    (10, 4),
    (11, 11),
    (12, 12),
    (13, 13),
]

# Cemus Schreibweise fuer dasselbe Pad ist eine DRITTE: `<index>_<GUID>`, waehrend Eden
# `port:N` + GUID ohne Namenspruefsumme schreibt und Azahar `port:N` + GUID MIT Pruefsumme.
# Wer das vereinheitlicht, bricht zwei davon. / EN: a third spelling for the same pad.
# Bewusst als Zeichenkette und NICHT ueber PAD_GUID: Diese Konstante steht weiter unten
# in der Datei, und ein Verweis nach vorn liesse das Modul beim Laden mit einem
# NameError sterben — was genau einmal passiert ist, beim Schreiben dieser Zeile.
# EN: deliberately a literal; PAD_GUID is defined further down and a forward
# reference kills the module at import time.
CEMU_UUID = os.environ.get("CEMU_PAD_UUID",
                           "0_030081b85e0400008e02000000010000")


def cemu_controller(pruefen=False):
    """-> (geaendert, meldung). Legt Cemus Wii-U-GamePad auf das gebrueckte Pad. (#304)

    OHNE DIESE DATEI GIBT ES GAR KEINE ZUORDNUNG. Am 2026-08-13 nachgesehen: Der Ordner
    `controllerProfiles` war leer, Cemu war nie eingerichtet worden. Das faellt nicht auf,
    weil Cemu trotzdem startet, das Spiel laeuft und der Ton kommt — nur die Eingabe
    fehlt, und das sieht nach einem toten Controller aus.

    Die Datei wird NUR angelegt, wenn keine da ist. Wer sein Pad in Cemus Oberflaeche
    selbst zugeordnet hat, soll das behalten — eine bestehende Zuordnung zu ueberschreiben
    waere anmassend und liesse sich schwer bemerken.

    EN: without this file there is no mapping at all, and nothing about the launch says so —
    Cemu starts, the game runs, audio plays, only input is missing. Written only when
    absent, so a hand-made mapping is never overwritten.
    """
    pfad = cemu_controller_profil()
    if os.path.isfile(pfad):
        with open(pfad, encoding="utf-8", errors="ignore") as f:
            vorhanden = f.read()
        if CEMU_UUID in vorhanden:
            return False, "Zuordnung steht bereits auf dem gebrueckten Pad"
        return False, ("es gibt bereits ein Profil fuer ein ANDERES Geraet — bleibt "
                       "unangetastet, damit eine eigene Zuordnung nicht verloren geht")
    if pruefen:
        return True, "keine Zuordnung vorhanden — der Controller taete nichts"

    eintraege = "\n".join(
        "\t\t\t<entry>\n\t\t\t\t<mapping>%d</mapping>\n\t\t\t\t<button>%d</button>\n\t\t\t</entry>"
        % paar for paar in CEMU_ZUORDNUNG)
    inhalt = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<emulated_controller>\n"
        "\t<type>Wii U GamePad</type>\n"
        "\t<controller>\n"
        "\t\t<api>SDLController</api>\n"
        "\t\t<uuid>%s</uuid>\n"
        "\t\t<display_name>Xbox 360 Game Controller</display_name>\n"
        "\t\t<rumble>0</rumble>\n"
        "\t\t<axis>\n\t\t\t<deadzone>0.25</deadzone>\n\t\t\t<range>1</range>\n\t\t</axis>\n"
        "\t\t<rotation>\n\t\t\t<deadzone>0.25</deadzone>\n\t\t\t<range>1</range>\n\t\t</rotation>\n"
        "\t\t<trigger>\n\t\t\t<deadzone>0.25</deadzone>\n\t\t\t<range>1</range>\n\t\t</trigger>\n"
        "\t\t<mappings>\n%s\n\t\t</mappings>\n"
        "\t</controller>\n"
        "</emulated_controller>\n") % (CEMU_UUID, eintraege)

    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(inhalt)
    return True, f"Wii-U-GamePad auf {CEMU_UUID} gelegt ({len(CEMU_ZUORDNUNG)} Zuordnungen)"


def azahar_ini():
    return os.path.join(CONFIG, ".config", "azahar-emu", "qt-config.ini")


def vita3k_config():
    return os.path.join(CONFIG, ".config", "Vita3K", "config.yml")


def vita3k_vollbild(pruefen=False):
    """-> (geaendert, meldung). Vita3K startet Titel im Fenster. (#304)

    AM LAUFENDEN HOST ABGELESEN, nicht geraten. Die Datei traegt genau einen Schalter
    dafuer, und er stand aus:

        boot-apps-full-screen: false      <- der hier
        backend-renderer: Vulkan          <- steht bereits richtig
        keyboard-gui-fullscreen: F11      <- der Tastenweg, den wir NICHT brauchen

    Warum nicht der Tastenweg: Der greift erst, wenn ein Fenster da ist, und der Agent
    ruft die Vorbereitung VOR dem Start auf — dieselbe Falle wie bei xemu (#429). Ein
    Schalter in der Konfiguration wirkt beim naechsten Start und braucht kein Fenster.

    Vita3K schreibt seine Konfiguration beim Beenden; existiert sie noch nicht, wird hier
    NICHTS angelegt. Eine von uns erfundene Datei koennte Felder vermissen lassen, die der
    Emulator erwartet — und der Fehler saehe dann nach einem kaputten Emulator aus.

    EN: read off the running host. `boot-apps-full-screen: false` is the one switch; the
    renderer is already Vulkan. The keyboard route needs a window, which does not exist
    when the agent prepares the launch. Nothing is created if the file is absent.
    """
    pfad = vita3k_config()
    if not os.path.isfile(pfad):
        return False, "config.yml gibt es noch nicht — der Emulator legt sie beim ersten Start an"
    try:
        with open(pfad, encoding="utf-8") as f:
            zeilen = f.read().splitlines()
    except OSError as e:
        return False, f"config.yml nicht lesbar: {e.strerror}"

    schluessel = "boot-apps-full-screen:"
    treffer = [i for i, z in enumerate(zeilen) if z.strip().startswith(schluessel)]
    if not treffer:
        # NICHT ANHAENGEN. Fehlt der Schluessel, hat diese Fassung ihn vielleicht anders
        # benannt — dann waere ein angehaengter Eintrag wirkungslos und wir haetten es
        # trotzdem als Erfolg gemeldet.
        return False, f"{schluessel} steht nicht in der config.yml — Fassung geaendert?"
    i = treffer[0]
    if zeilen[i].split(":", 1)[1].strip().lower() == "true":
        return False, "steht bereits auf Vollbild"
    if pruefen:
        return True, "wuerde auf Vollbild stellen"
    zeilen[i] = f"{schluessel} true"
    try:
        with open(pfad, "w", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n")
    except OSError as e:
        return False, f"config.yml nicht schreibbar: {e.strerror}"
    return True, "Titel starten jetzt im Vollbild"


# ZWEI MODALE FENSTER FANGEN JEDEN VITA-START AB. (#488)
#
# Beide sind dieselbe Klasse Falle wie DuckStations Setup-Wizard: ein Fenster, das im
# Container niemand sieht und wegklickt, und der Start staut sich dahinter. Gemessen am
# laufenden Host (2026-08-13, Gravity Rush, Vita3K v0.2.1 4072-80075ce5) an der ECHTEN
# Vita3K-PID — nicht an der des Wrappers, der eine andere ist (#489):
#
#   show-welcome | check-for-updates-mode | Fenster
#   true         | 1                      | nur "Welcome to Vita3K", kein Spiel, 4,5 % CPU
#   false        | 1                      | Spiel + "Update Available", 320x183 mittendrauf
#   false        | 0                      | Spiel, kein Dialog; Fensterschritt meldet "ok",
#   false        | 1  (Gegenprobe)        | "Update Available" wieder da
#
# Die letzte Zeile ist der Grund, warum der zweite Schalter hier steht und nicht als
# Vermutung im Issue: der Dialog haette auch „einmal je Fassung" sein koennen. Ist er
# nicht — er kommt mit `1` jedes Mal wieder und bleibt mit `0` weg.
#
# WAS HIER NICHT BEHAUPTET WIRD: dass `0` in Vita3Ks Quelltext „nie" heisst. Der Wert ist
# GEMESSEN, nicht abgelesen — die Aufzaehlung steht nicht in den Zeichenketten der
# Binaerdatei. Belegt ist: mit `0` kommt der Dialog nicht, und Vita3K schreibt die `0`
# beim Start unveraendert zurueck, nimmt sie also an.
#
# NICHT DABEI: `warn-missing-firmware`. Der dritte Dialog derselben Klasse — hier
# folgenlos, weil die Firmware vollstaendig ist (#485/#486). Wer ihn vorsorglich
# abschaltet, verliert die Warnung genau dann, wenn sie einmal berechtigt waere.
#
# EN: two modal windows catch every Vita launch; both measured on the running host with a
# counter-check per switch. `0` is measured to keep the update dialog away — it is NOT
# claimed to be the source's name for "never".
VITA3K_DIALOGE = (
    ("show-welcome", "false", "Willkommensdialog"),
    ("check-for-updates-mode", "0", "Update-Abfrage"),
)


def vita3k_dialoge(pruefen=False):
    """-> (geaendert, meldung). Die beiden Startdialoge abstellen. (#488)

    Dieselben drei Regeln wie beim Vollbild oben, und aus denselben Gruenden:
    NICHTS ANLEGEN, wenn die Datei fehlt; NICHTS ANHAENGEN, wenn ein Schluessel fehlt
    (eine neue Fassung koennte ihn umbenannt haben — ein angehaengter Eintrag waere
    wirkungslos und wuerde trotzdem als Erfolg gemeldet); und geprueft wird der WERT,
    nicht das Vorhandensein.

    Fehlt einer der beiden Schluessel, wird der andere trotzdem gesetzt und der fehlende
    in der Meldung benannt. Halb wirksam ist besser als gar nicht — solange dabeisteht,
    welche Haelfte fehlt.

    EN: same three rules as the fullscreen switch above. A missing key is reported, never
    appended; the other key is still set.
    """
    pfad = vita3k_config()
    if not os.path.isfile(pfad):
        return False, "config.yml gibt es noch nicht — der Emulator legt sie beim ersten Start an"
    try:
        with open(pfad, encoding="utf-8") as f:
            zeilen = f.read().splitlines()
    except OSError as e:
        return False, f"config.yml nicht lesbar: {e.strerror}"

    offen, fehlend = [], []
    for schluessel, soll, name in VITA3K_DIALOGE:
        i = next((k for k, z in enumerate(zeilen)
                  if z.strip().startswith(schluessel + ":")), None)
        if i is None:
            fehlend.append(schluessel)
        elif zeilen[i].split(":", 1)[1].strip().lower() != soll:
            offen.append((i, schluessel, soll, name))

    hinweis = (f" — steht nicht in der config.yml: {', '.join(fehlend)} (Fassung geaendert?)"
               if fehlend else "")
    if not offen:
        return False, ("die Startdialoge stehen bereits ab" if not fehlend
                       else "nichts zu setzen" + hinweis)
    if pruefen:
        return True, "wuerde abstellen: " + ", ".join(n for *_, n in offen) + hinweis

    for i, schluessel, soll, _ in offen:
        vorne = zeilen[i][:len(zeilen[i]) - len(zeilen[i].lstrip())]
        zeilen[i] = f"{vorne}{schluessel}: {soll}"
    try:
        with open(pfad, "w", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n")
    except OSError as e:
        return False, f"config.yml nicht schreibbar: {e.strerror}"
    return True, "abgestellt: " + ", ".join(n for *_, n in offen) + hinweis


# SDL-Kennung des gebrueckten Pads. Aufbau: Bus 03 (USB), Vendor 045e (Microsoft),
# Product 028e (Xbox 360 Controller) — jeweils byteweise gedreht. SDL hat sie sich in
# xemus Konfiguration selbst eingetragen; von dort abgelesen, nicht erfunden.
PAD_GUID = "030081b85e0400008e02000000010000"
# Frueherer Name; die Kennung ist nicht azahar-spezifisch, sondern die des gebrueckten
# Pads — alle acht Geraete im Container tragen sie. (#304)
AZAHAR_GUID = PAD_GUID

# WELCHER PORT: nicht 0. Im Container liegen ACHT identische "Microsoft X-Box 360 pad"
# (js0..js7) — die vier der Bruecke und vier weitere —, und das gebrueckte Pad ist fuer
# SDL das dritte. Azahars eigenes Auto-Map hat `port:2` eingetragen; meine Annahme
# `port:0` war falsch und lieferte ein Pad, das erkannt wurde und nichts ausloeste.
#
# ACHTUNG: Der Port ist NICHT stabil. Er haengt an der Aufzaehlungsreihenfolge und kann
# sich nach einem Neustart der Bruecke verschieben. Deshalb wird eine bereits
# vorhandene SDL-Belegung NIE ueberschrieben — nur die Tastatur-Voreinstellung wird
# ersetzt. Wer sichergehen will, laesst Azahar einmal selbst mappen.
AZAHAR_PORT = 2

# 3DS-Taste -> SDL-Eingabe. Knopfnummern sind die des Xbox-360-Layouts, wie SDL sie
# meldet: 0=A 1=B 2=X 3=Y 4=LB 5=RB 6=Back 7=Start.
#
# ACHTUNG, die 3DS-Tasten sind gegenueber Xbox VERTAUSCHT: Auf dem 3DS liegt A rechts
# und B unten — dieselbe Anordnung wie bei Nintendo ueblich, spiegelverkehrt zu Xbox.
# Wer hier stur A auf A legt, bekommt ein Pad, auf dem jede Bestaetigung abbricht.
AZAHAR_BELEGUNG = {
    "button_a":      f"button:1,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},engine:sdl",
    "button_b":      f"button:0,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},engine:sdl",
    "button_x":      f"button:3,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},engine:sdl",
    "button_y":      f"button:2,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},engine:sdl",
    "button_l":      f"button:4,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},engine:sdl",
    "button_r":      f"button:5,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},engine:sdl",
    "button_start":  f"button:7,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},engine:sdl",
    "button_select": f"button:6,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},engine:sdl",
    # Schultertasten ZL/ZR liegen auf den ANALOGEN Triggern (Achse 2 und 5).
    "button_zl":     f"axis:2,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},direction:+,threshold:0.5,engine:sdl",
    "button_zr":     f"axis:5,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},direction:+,threshold:0.5,engine:sdl",
    # Steuerkreuz ueber den Hat.
    "button_up":     f"hat:0,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},direction:up,engine:sdl",
    "button_down":   f"hat:0,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},direction:down,engine:sdl",
    "button_left":   f"hat:0,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},direction:left,engine:sdl",
    "button_right":  f"hat:0,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},direction:right,engine:sdl",
    # Schiebepad und C-Stick als Achsenpaare.
    "circle_pad":    f"axis_x:0,axis_y:1,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},engine:sdl",
    "c_stick":       f"axis_x:3,axis_y:4,guid:{AZAHAR_GUID},port:{AZAHAR_PORT},engine:sdl",
}


def azahar_apply(pruefen=False):
    r"""-> (geaendert, meldung). Legt Spieler 1 auf das gebrueckte Gamepad.

    Azahars Standardbelegung ist die TASTATUR (`engine:keyboard`) — dieselbe Falle wie
    bei RPCS3 (#156): Das Pad wird erkannt und aufgezaehlt, im Spiel passiert nichts,
    und von aussen sieht das aus wie ein defekter Controller.

    Qt schreibt neben jeden Schluessel ein `\default`-Flag. Steht es auf `true`, gilt
    der eingebaute Standard und der danebenstehende Wert wird beim naechsten Start
    ueberschrieben — deshalb muss BEIDES gesetzt werden. Genau daran ist hier zuerst die
    Umstellung auf Vulkan gescheitert: Der Wert stand richtig da und wirkte trotzdem
    nicht.
    EN: Azahar defaults to the keyboard. Qt keeps a `\default` flag next to every key;
    while it is true the value beside it is ignored and rewritten.
    """
    pfad = azahar_ini()
    if not os.path.isfile(pfad):
        return False, "qt-config.ini gibt es noch nicht — der Emulator legt sie beim ersten Start an"

    with open(pfad, encoding="utf-8", errors="ignore") as f:
        zeilen = f.read().splitlines()

    # Steht dort schon eine SDL-Belegung, bleibt sie unangetastet: Sie stammt dann von
    # Azahars Auto-Map, und das kennt den richtigen Port — wir raten ihn nur.
    if any("engine:sdl" in z and "profiles\\1\\button_a" in z for z in zeilen):
        return False, "SDL-Belegung vorhanden (vermutlich Auto-Map) — unveraendert gelassen"

    gewuenscht = {f"profiles\\1\\{k}": v for k, v in AZAHAR_BELEGUNG.items()}
    geaendert = False
    neu_zeilen, gesehen = [], set()
    for z in zeilen:
        schluessel = z.split("=", 1)[0].strip()
        # Der Wert selbst
        if schluessel in gewuenscht:
            soll = f'{schluessel}="{gewuenscht[schluessel]}"'
            gesehen.add(schluessel)
            if z != soll:
                geaendert = True
            neu_zeilen.append(soll)
            continue
        # Das zugehoerige default-Flag muss false sein, sonst gilt der Wert nicht.
        if schluessel.endswith("\\default"):
            basis = schluessel[: -len("\\default")]
            if basis in gewuenscht:
                soll = f"{schluessel}=false"
                if z != soll:
                    geaendert = True
                neu_zeilen.append(soll)
                continue
        neu_zeilen.append(z)

    fehlend = [k for k in gewuenscht if k not in gesehen]
    if fehlend:
        # Neue Schluessel gehoeren in den [Controls]-Abschnitt, nicht ans Dateiende.
        try:
            i = neu_zeilen.index("[Controls]") + 1
        except ValueError:
            neu_zeilen.append("[Controls]")
            i = len(neu_zeilen)
        for k in sorted(fehlend):
            neu_zeilen[i:i] = [f'{k}="{gewuenscht[k]}"', f"{k}\\default=false"]
        geaendert = True

    if pruefen or not geaendert:
        return geaendert, ("Belegung muesste gesetzt werden" if geaendert
                           else "Gamepad-Belegung steht bereits")
    sicherung = pfad + ".vor-gamepad"
    if not os.path.exists(sicherung):
        shutil.copy2(pfad, sicherung)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("\n".join(neu_zeilen) + "\n")
    return True, f"Gamepad-Belegung gesetzt ({len(gewuenscht)} Tasten), Rueckweg: {sicherung}"


PROFILE = {
    # geprueft: Bild und Gamepad im Spiel bestaetigt (2026-08-10). Bis dahin drei
    # Anlaeufe — Erstlaufdialog, dann PCSX2s Face*-Namen, dann `South` aus dem Binary.
    # Erst der Quelltext (`s_button_info`) lieferte A/B/X/Y.
    "duckstation": {"system": "PS1",         "controller": duckstation_apply,
                    "bios": None, "vollbild": None,
                    # Eigener Platz, wie bei vita3k (#488): die beiden Schalter haengen
                    # nicht an der Gamepad-Belegung, und einer steht nicht einmal im
                    # selben Abschnitt der Datei. (#492)
                    "dialoge": duckstation_dialoge,
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
    # NACHGEMESSEN am laufenden Host (2026-08-12, #304), nicht angenommen:
    #   Bild    : Vollbild und Renderer stehen in der STARTZEILE (init/30-agent), nicht
    #             hier — Flycast nimmt `-config SEKTION:schluessel=wert` entgegen, und
    #             eine Konfigurationsdatei zu schreiben waere der umstaendlichere Weg.
    #             Gemessen: 1920x1080 auf 0,0, bemalte Flaeche 100 %.
    #   BIOS    : `dc_boot.bin` und `dc_flash.bin` liegen bereits richtig — nichts zu tun.
    #   Dialog  : es gibt keinen Erstlaufdialog, Flycast bootet den Titel direkt
    #             (`N[BOOT]: Game ID is [T7011D  50]`).
    #   Gamepad : Flycast oeffnet alle vier virtuellen Pads von selbst und belegt sie
    #             (`SDL: Opened joystick 0..3 on port 0..3` / `Resetting SDL gamepad to
    #             default`). Es braucht KEINE Zuordnung von uns — und das ist hier zum
    #             ersten Mal BELEGT statt angenommen: ein Mensch hat in Fatal Fury -
    #             Mark of the Wolves gedrueckt und die Figur hat reagiert (2026-08-12).
    #             Bei DuckStation, PCSX2, Dolphin und RPCS3 genuegte die Automatik NICHT,
    #             deshalb steht diese Zeile hier ausdruecklich: Flycast ist die Ausnahme,
    #             nicht die Regel. (#301, #304)
    #   Ton     : ebenfalls von einem Menschen bestaetigt (2026-08-12). Damit ist bei
    #             Flycast alles drei belegt — Bild, Ton, Gamepad — und nichts davon aus
    #             einem Protokoll geschlossen.
    "flycast":   {"system": "Dreamcast",     "controller": flycast_apply, "bios": None,
                  "vollbild": None, "geprueft": True},
    # Fenster und Ton am laufenden Host bestaetigt (2026-08-10, #300) — es brauchte
    # KEINE Konfigurationsdatei, nur libusb, den Pulse-Pfad und das Festplattenabbild
    # (init/22-xemu-vorbereiten). Der Controller ist NICHT geprueft.
    # geprueft: Bild, Ton UND Gamepad im Spiel bestaetigt (2026-08-10, #300) — der
    # Controller von einem Menschen gedrueckt, nicht aus einem Log geschlossen.
    # Es brauchte KEINE Konfigurationsdatei, sondern libusb, den Pulse-Pfad, das
    # Festplattenabbild und vor allem das RICHTIGE BIOS: alle Retail-Dumps bleiben
    # schwarz, erst das gepatchte COMPLEX 4627 mit MCPX 1.0 bootet.
    "xemu":      {"system": "Xbox",          "controller": xemu_apply, "bios": None,
                  # vollbild=None ist KEIN Rueckschritt: Der Tastenweg lag hier falsch.
                  # `--fullscreen` ruft der Agent VOR dem Start auf, damit ein Emulator
                  # seine Konfiguration frisch liest — eine Tastensendung findet dort kein
                  # Fenster und lief ins Leere. Am Host nachgestellt:
                  #   [vollbild] xemu: kein xemu-Fenster gefunden — laeuft der Emulator?
                  # Der Tastenweg steht jetzt in `vollbild_sicherstellen()`, das NACH dem
                  # Start misst und nur nachhilft, wenn das Bild zu klein ist. (#429)
                  "vollbild": None,
                  # EIGENER PLATZ, weil `controller` hier schon belegt ist (#498). Flycast
                  # schreibt seinen Renderer noch unter `controller` mit — das traegt, solange
                  # ein Emulator nur EINE Sache zu setzen hat. xemu hat zwei, und zwei Anliegen
                  # in eine Funktion zu ziehen, damit die Tabelle passt, waere die falsche
                  # Reihenfolge: Die Tabelle hat sich nach dem Emulator zu richten.
                  "einstellungen": [xemu_renderer],
                  "geprueft": True},
    "cemu":      {"system": "Wii U",         "controller": cemu_controller, "bios": None, "vollbild": None,
                  # Cemu ordnet ein SDL-Pad selbst zu, sobald es in seiner Oberflaeche
                  # hinzugefuegt wurde — die Belegung schreibt es dann nach
                  # `controllerProfiles/controller0.xml`. Der Ton dagegen steht auf einem
                  # Backend, das es hier nicht gibt, und das faellt nirgends auf. (#541)
                  "einstellungen": [cemu_audio],
                  # geprueft: Bild, Ton und Gamepad am laufenden Host bestaetigt
                  # (2026-08-13) — mit einem Wii-U-BASISSPIEL, nachdem die Bibliothek
                  # zuvor nur ein Update enthielt (#302).
                  "geprueft": True},
    # vollbild=None ist hier NACHGEMESSEN, nicht angenommen (#316): Der Fenstertrick
    # genuegt, der gezeichnete Bereich waechst mit. Gemessen am laufenden Emulator ueber
    # die Pixel, nicht ueber die Fenstergeometrie — die meldet den Rahmen, nicht den
    # Inhalt, und genau daran ist der Fall bei xemu lange unbemerkt geblieben.
    # geprueft: Bild (97,6 %), Ton UND Gamepad am laufenden Host bestaetigt
    # (2026-08-13). Der Controller brauchte dieselbe Korrektur wie Eden — Azahar hatte
    # sich `port:2` aus der Zeit vor #535 gemerkt.
    "azahar":    {"system": "3DS",           "controller": azahar_apply,
                  # Tastenweg: siehe xemu — greift nach dem Start, nicht hier. (#429)
                  "bios": None, "vollbild": None,
                  "geprueft": True},
    # Am laufenden Host abgelesen (2026-08-12, #304): `backend-renderer` steht bereits auf
    # Vulkan, `boot-apps-full-screen` stand auf `false`. Der Schalter kommt in die
    # Konfiguration und NICHT als Tastensendung — die braeuchte ein Fenster, das es zum
    # Zeitpunkt der Vorbereitung nicht gibt (#429). `geprueft` bleibt False, bis ein
    # Mensch Bild, Ton und Pad im Spiel bestaetigt hat (#303).
    # geprueft: Bild (100 %, 60 FPS), Ton und Gamepad am laufenden Host bestaetigt
    # (2026-08-13, AM2R). Vita3K ordnet ein erkanntes SDL-Pad SELBST zu — es meldet beim
    # Start `1 Controllers Connected: Xbox 360 Controller` und nahm die Eingaben ohne jede
    # Konfigurationsdatei an. `controller: None` ist hier gemessen, nicht ungeprueft.
    "vita3k":    {"system": "PS Vita",       "controller": None, "bios": None,
                  "vollbild": vita3k_vollbild,
                  # EIGENER PLATZ, nicht in `controller` mit hineingelegt (#488). Bei
                  # DuckStation sitzt der Setup-Wizard im Controller-Schritt, weil dort
                  # ohnehin dieselbe Datei angefasst wird. Hier gibt es keine
                  # Controller-Belegung, in die er hineinpasste — dann ist ein Schritt,
                  # der heisst, was er tut, ehrlicher als ein Sammelplatz. Andere
                  # Emulatoren duerfen `dialoge` weglassen.
                  "dialoge": vita3k_dialoge,
                  "geprueft": True},
    # geprueft: Bild, Ton und Gamepad im Spiel bestaetigt (2026-08-10, #119). Dass die
    # Warnung „Adding empty device" verschwindet, war nur der Hinweis — den Nachweis
    # hat ein Mensch am Pad erbracht.
    "rpcs3":     {"system": "PS3",           "controller": rpcs3_apply,
                  "bios": None, "vollbild": None,
                  "geprueft": True},
    # `controller` war None mit der Begruendung „ordnet ein erkanntes SDL-Pad selbst zu".
    # Das war eine ANNAHME und ist widerlegt: Spieler 1 liegt auf der Tastatur (#298).
    # Die Funktion repariert nichts — sie macht den stillen Defekt zu einer Zeile im
    # Protokoll, bis Edens Bindungssyntax gelesen statt geraten werden kann.
    # geprueft: Bild (100 %), Ton und Gamepad am laufenden Host bestaetigt
    # (2026-08-13). Die Zuordnung stand auf `port:1` aus der Zeit vor #535 und musste
    # nachgezogen werden.
    "switchemu": {"system": "Switch",        "controller": switchemu_apply, "bios": None,
                  # Tastenweg: siehe xemu — greift nach dem Start, nicht hier. (#429)
                  "vollbild": None,
                  "geprueft": True},
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


class _LeerErgebnis:
    stdout = ""
    stderr = ""
    returncode = 1


def _x(*args, **kw):
    """Ein X-Werkzeug aufrufen. Ein haengendes Werkzeug darf den Schritt nicht kosten.

    `xdotool windowactivate --sync` wartet, bis das Fenster den Fokus HAT — und ein
    modaler Fehlerdialog gibt ihn nie her. Am laufenden Host gemessen: der Fensterschritt
    lief dadurch in den 60-Sekunden-Timeout des Agenten, und der Befund kam als
    "unbekannt" statt als Dialogtitel an. Ein Timeout hier ist ein Messwert, kein
    Programmabbruch. (#288)
    """
    umg = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":1")}
    try:
        return subprocess.run(args, capture_output=True, text=True, env=umg, timeout=20, **kw)
    except subprocess.TimeoutExpired:
        return _LeerErgebnis()


def ist_dialog(fid):
    """Traegt das Fenster _NET_WM_WINDOW_TYPE_DIALOG?

    WOZU: Scheitert ein Titel, zeigen die Emulatoren keinen Fehler auf einem Kanal, den
    wir lesen — sie zeigen einen DIALOG. Gemessen: `App Encrypted` (Azahar, 3DS),
    `CIA must be installed before usage` (Azahar), `NKit Warning` (Dolphin, Wii).
    Alle drei sind gross genug, um die Flaechenschwelle unten zu ueberspringen, und
    wurden deshalb wie ein Spielfenster behandelt — samt Aufziehen auf Vollbild. Genau
    das sieht der Nutzer dann als "der Stream geht auf, aber da ist nichts".

    Der Typ ist der emulatorunabhaengige Weg: eine Liste bekannter Fehlertexte zu
    pflegen waere sproede und in jeder neuen Emulatorfassung falsch.
    EN: a failing title shows a DIALOG, not an error on any channel we read. The window
    type is the emulator-agnostic test; a list of known error strings would rot.
    """
    typ = _x("xprop", "-id", fid, "_NET_WM_WINDOW_TYPE").stdout
    return "_NET_WM_WINDOW_TYPE_DIALOG" in typ


def ist_vollbild(fid):
    """Traegt das Fenster _NET_WM_STATE_FULLSCREEN — steht der Emulator also SELBST
    im Vollbild?

    WOZU (#493): DuckStation, PCSX2 und Flycast bekommen ihr Vollbild aus der Startzeile
    beziehungsweise der Konfiguration. Ihr Spielfenster traegt den Zustand dann wirklich —
    am laufenden Host abgelesen, bei allen dreien:

        _NET_WM_STATE(ATOM) = _NET_WM_STATE_FULLSCREEN, _NET_WM_STATE_FOCUSED

    Das ist die Auskunft, die keine Flaechenmessung liefern kann — auch `emulatoranteil()`
    nicht: Ein Titel, der noch die Disc bootet, ist schwarz. Schwarz auf hell IST eine
    Aenderung, schwarz auf schwarz nicht, und in beiden Faellen liegt der Wert unter der
    Schwelle, obwohl das Fenster den ganzen Schirm deckt. Genau so kam DuckStation zu einem
    F11, das sein Vollbild wieder abschaltete.

    Fehlt die Eigenschaft, meldet `xprop` "_NET_WM_STATE:  not found." — kein Leerstring
    und kein Fehler. Die Pruefung auf den Namen trifft deshalb beides richtig.

    EN: does the emulator hold its own fullscreen? This is the fact the painted-area
    measurement cannot supply — a title still booting its disc is black yet covers the
    whole screen.
    """
    return "_NET_WM_STATE_FULLSCREEN" in _x("xprop", "-id", fid, "_NET_WM_STATE").stdout


def fenstergroesse(fid):
    """-> "1920x1080" oder "" — die GEMESSENE Groesse des Fensters. (#493)

    WOZU: Der Fensterbefund nannte bisher die BILDSCHIRMgroesse, also das Ziel des
    Schrittes statt seines Ergebnisses. Gemessen, waehrend ein Titel lief: `/status`
    meldete "1 Fenster auf 1920x1080", das Fenster war 640x480 gross.
    EN: the verdict used to quote the screen size — the aim, not the outcome.
    """
    g = _x("xdotool", "getwindowgeometry", "--shell", fid).stdout
    masse = dict(z.split("=", 1) for z in g.strip().splitlines() if "=" in z)
    b, h = masse.get("WIDTH", "").strip(), masse.get("HEIGHT", "").strip()
    return f"{b}x{h}" if b and h else ""


def fenstername(fid):
    return _x("xdotool", "getwindowname", fid).stdout.strip()


def nachkommen(pid, grenze=32):
    """PID und alle Nachkommen, Eltern zuerst. -> [pid, kind, enkel, …]

    WOZU (#489): Vita3Ks `AppRun.wrapped` ist als einziges der Emulator-Verpackungen ein
    Shell-Skript und startet das Programm als KIND, ohne `exec`. Der Agent verfolgt damit
    die Shell, und die hat kein Fenster. Am laufenden Host gemessen, bei sichtbar
    laufendem Spiel:

        xdotool search --pid 11616   (Wrapper)   -> nichts
        xdotool search --pid 11634   (Vita3K)    -> 46137351 [Vita3K v0.2.1 …]
                                                    46137358 [GRAVITY RUSH™ (PCSF00024)]

    `/status` meldete dazu `"window": "kein-fenster"`. Das war keine Beobachtung, sondern
    eine Verwechslung — nachgesehen wurde an der falschen PID.

    WARUM /proc UND NICHT `pgrep -P`: das hier laeuft ohne zusaetzliche Werkzeuge, und
    ein Baum braucht ohnehin die ganze Tabelle. Threads stehen nicht in /proc auf oberster
    Ebene, ein Emulator mit vielen Threads bleibt also EIN Eintrag.

    `grenze` ist eine Reissleine, keine Fachaussage: Bei den gemessenen Emulatoren sind es
    zwei Prozesse. Wer eines Tages ein Programm startet, das Dutzende Kinder aufmacht, soll
    nicht in Dutzende `xdotool`-Aufrufe laufen — dann lieber unvollstaendig als langsam.

    EN: the agent tracks the wrapper shell, which owns no window; the emulator does.
    Reading /proc avoids depending on another tool, and `grenze` is a runaway guard.
    """
    kinder = {}
    try:
        eintraege = os.listdir("/proc")
    except OSError:
        return [pid]
    for name in eintraege:
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/stat", encoding="utf-8", errors="replace") as f:
                daten = f.read()
        except OSError:
            continue            # in der Zwischenzeit beendet — kein Fehler
        # Der Programmname steht in Klammern und darf SELBST Leerzeichen und Klammern
        # enthalten. Deshalb hinter der LETZTEN `)` aufteilen, nicht am ersten Leerzeichen.
        schluss = daten.rfind(")")
        felder = daten[schluss + 2:].split() if schluss > 0 else []
        if len(felder) < 2:
            continue
        try:
            kinder.setdefault(int(felder[1]), []).append(int(name))
        except ValueError:
            continue
    gefunden = [pid]
    i = 0
    while i < len(gefunden) and len(gefunden) < grenze:
        for k in sorted(kinder.get(gefunden[i], [])):
            if k not in gefunden:
                gefunden.append(k)
        i += 1
    return gefunden[:grenze]


def sichtbare_fenster(pid, mit_dialogen=False):
    """Sichtbare Fenster des Prozesses UND seiner Nachkommen, groesstes zuerst.

    `--onlyvisible` ist wichtig: Emulatoren legen unsichtbare Hilfsfenster an, und ohne
    den Filter erwischt man eines davon. Beim ersten Anlauf hier genau passiert — das
    Skript meldete Erfolg an einem Fenster, das niemand sieht, waehrend das Spielfenster
    unveraendert danebenstand.
    Without --onlyvisible one grabs a helper window and reports success on something
    nobody sees, which is exactly what happened on the first attempt.

    Dialoge bleiben standardmaessig draussen (siehe `ist_dialog`) — ein aufs Vollbild
    gezogener Fehlerdialog ist schlimmer als gar keine Behandlung.

    GEFRAGT WIRD AUCH BEI DEN KINDPROZESSEN (#489, siehe `nachkommen`): `xdotool --pid`
    trifft nur die genannte PID, und bei Vita3K ist das die Shell des Wrappers, nicht der
    Emulator. Fuer die uebrigen Emulatoren aendert sich damit nichts — deren `AppRun`
    `exec`-t, die verfolgte PID IST das Programm und hat keine Kinder.
    """
    kandidaten = nachkommen(pid)
    ids = []
    for kandidat in kandidaten:
        r = _x("xdotool", "search", "--onlyvisible", "--pid", str(kandidat))
        for z in r.stdout.split():
            if z.strip() and z not in ids:
                ids.append(z)
    mit_flaeche = []
    for i in ids:
        g = _x("xdotool", "getwindowgeometry", "--shell", i).stdout
        masse = dict(z.split("=", 1) for z in g.strip().splitlines() if "=" in z)
        try:
            f = int(masse.get("WIDTH", 0)) * int(masse.get("HEIGHT", 0))
        except ValueError:
            f = 0
        if f <= 10000:                    # Platzhalter, kein echtes Fenster
            continue
        if not mit_dialogen and ist_dialog(i):
            continue
        mit_flaeche.append((f, i))
    return [i for _f, i in sorted(mit_flaeche, reverse=True)]


def dialoge(pid):
    """-> [(id, Titel)] der sichtbaren Dialogfenster des Prozesses.

    Der Titel IST die Fehlermeldung: `App Encrypted` sagt genau, was fehlt. Deshalb wird
    er nach oben durchgereicht, statt ihn zu verwerfen.
    """
    gefunden = []
    for fid in sichtbare_fenster(pid, mit_dialogen=True):
        if ist_dialog(fid):
            gefunden.append((fid, fenstername(fid)))
    return gefunden


def fenster_von_pid(pid, versuche=20):
    """Groesstes sichtbares Fenster. Ein Emulator braucht Sekunden bis dahin."""
    for _ in range(versuche):
        ids = sichtbare_fenster(pid)
        if ids:
            return ids[0]
        time.sleep(1)
    return ""


def _fenster_fuellen(fid, b, h, aktivieren=True):
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
    # NUR das groesste Fenster aktivieren. `--sync` wartet, bis das Fenster den Fokus
    # HAT — und den kann immer nur eines haben. Bei Eden (vier Fenster, drei Runden)
    # lief jeder vergebliche Versuch in seinen 20-Sekunden-Timeout: gemessen 157 s fuer
    # den ganzen Schritt, womit der Agent nach 60 s abbrach und der Befund als
    # "unbekannt" ankam statt als "ok". Ohne Aktivierung sind es wenige Sekunden.
    # OHNE `--sync`: das Warten auf die Fokus-Bestaetigung ist der teure Teil, und bei
    # Eden sind alle vier Fenster gleich gross — die Reihenfolge trifft dann auch mal
    # ein Hilfsfenster, das den Fokus nie bekommt. Der Fokus wird auch ohne Bestaetigung
    # gesetzt; das anschliessende Warten unten reicht aus. Gemessen: 157 s -> 67 s
    # durch die Beschraenkung auf ein Fenster, -> wenige Sekunden ohne `--sync`.
    if aktivieren:
        _x("xdotool", "windowactivate", fid)
    _x("xdotool", "windowraise", fid)
    time.sleep(0.4)
    _x("xdotool", "windowmove", fid, "0", "0")


def nur_emulator(pid, runden=3, pause=6):
    """-> (zustand, meldung). Panel weg, Dekoration weg, Fenster auf volle Flaeche.

    zustand ist einer von:
      "ok"          — ein Spielfenster steht auf voller Flaeche
      "dialog"      — der Emulator zeigt einen Fehlerdialog; meldung ist dessen Titel
      "kein-fenster"— gar nichts Sichtbares entstanden
      "fehler"      — die Bildschirmgroesse war nicht zu ermitteln
    Frueher ein bool. Ein blosses False sagte nicht, WARUM nichts zu sehen ist, und
    genau diese Auskunft fehlte dem Nutzer vor dem leeren Stream (#288).

    MEHRERE RUNDEN, weil das SPIELFENSTER spaeter entsteht als das erste Fenster des
    Emulators. Einmalig anzuwenden traf beim ersten Anlauf ein Hilfsfenster, meldete
    Erfolg, und der Nutzer sah weiter den Desktop. Deshalb wird nach dem Start noch
    ein paar Mal nachgesehen, ob ein neues, groesseres Fenster dazugekommen ist.
    Several rounds because the game window appears after the first one; applying once
    reported success on a helper window while the user still saw the desktop."""
    breite_hoehe = _x("xdotool", "getdisplaygeometry").stdout.split()
    if len(breite_hoehe) != 2:
        return "fehler", "Bildschirmgroesse nicht ermittelbar"
    b, h = breite_hoehe
    if not fenster_von_pid(pid):
        # Kein Spielfenster — aber vielleicht ein Dialog, der sagt WARUM (#288).
        offen = dialoge(pid)
        if offen:
            return "dialog", offen[0][1]
        return "kein-fenster", "kein sichtbares Fenster zum Prozess gefunden"
    # Dialog VOR dem Aufziehen pruefen, nicht erst danach. Zwei Gruende, beide gemessen:
    # der Dialog ist modal, also haengt jedes `windowactivate --sync` auf den Fenstern
    # dahinter in seinen Timeout — der ganze Schritt lief so in die 60 Sekunden des
    # Agenten. Und aufzuziehen gibt es ohnehin nichts, wenn kein Spiel laeuft.
    offen = dialoge(pid)
    if offen:
        return "dialog", offen[0][1]
    # Panel ausblenden. Schlaegt es fehl, ist das kein Grund abzubrechen — ein Fenster
    # ueber dem Panel ist immer noch besser als ein Desktop.
    _x("xfconf-query", "-c", "xfce4-panel", "-p", "/panels/panel-1/autohide-behavior",
       "-t", "int", "-s", "2", "--create")
    behandelt = set()
    for runde in range(runden):
        # sichtbare_fenster liefert groesstes zuerst — das ist das Spielfenster, und nur
        # das bekommt den Fokus (siehe _fenster_fuellen).
        for platz, fid in enumerate(sichtbare_fenster(pid)):
            _fenster_fuellen(fid, b, h, aktivieren=(platz == 0))
            behandelt.add(fid)
        if runde < runden - 1:
            time.sleep(pause)
    if not behandelt:
        offen = dialoge(pid)
        if offen:
            return "dialog", offen[0][1]
        return "kein-fenster", "kein sichtbares Fenster"
    # Auch WENN ein Fenster behandelt wurde, kann daneben ein Fehlerdialog stehen: bei
    # Azahar bleibt das leere Hauptfenster auf 1920x1080 offen und der Dialog `App
    # Encrypted` liegt davor. Ein Erfolg waere hier gelogen.
    offen = dialoge(pid)
    if offen:
        return "dialog", offen[0][1]
    # KEINE GROESSE ZUSAGEN, DIE HIER NIEMAND NACHSIEHT (#493): Frueher stand an dieser
    # Stelle die BILDSCHIRMgroesse `{b}x{h}` — das Ziel des Schrittes, nicht sein Ergebnis.
    # Gemessen, waehrend ein Titel lief: `/status` meldete "1 Fenster auf 1920x1080",
    # `xdotool` meldete 640x480. Die Zahl kommt jetzt aus `main`, NACH dem Vollbildschritt,
    # denn erst dort entstand der Schaden.
    # EN: the size used to be the screen geometry — the aim, not the outcome. It is
    # measured in `main` after the fullscreen step, which is where the damage happened.
    return "ok", f"{len(behandelt)} Fenster, ohne Rahmen, Panel ausgeblendet"


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


# Wo das Grundbild liegt — die Aufnahme des LEEREN Desktops, gegen die gemessen wird.
# In /tmp, weil es nur fuer diesen Containerlauf gilt: nach einem Neustart koennen
# Aufloesung oder Hintergrundbild andere sein, und ein altes Grundbild waere dann eine
# Messlatte, die nichts mehr misst.
GRUNDBILD = os.path.join(tempfile.gettempdir(), "vollbild-grundbild.xwd")

# Ab hier gilt der Bildschirm als vom Emulator uebernommen. NICHT 100: ein Titel mit
# anderem Seitenverhaeltnis malt am Rand schwarze Balken, und wo das Grundbild schon
# schwarz war, zaehlt das nicht als uebernommen. Am laufenden Host gemessen (siehe
# `emulatoranteil`): leerer Desktop 0,06 %, xemu mit halbem Bild 74,87 %, Flycast im
# echten Vollbild 99,97 %.
VOLLBILD_SCHWELLE = 90.0

# Unter diesem Helligkeitswert gilt ein Bildpunkt als schwarz. SCHWELLE 18 STATT 0: ein
# X-Server liefert am Rand gern ein paar Restwerte; bei 0 waere jeder Punkt „bemalt".
SCHWARZ = 18

# Bis zu dieser Abweichung je Farbkanal gilt ein Bildpunkt als UNVERAENDERT.
#
# WARUM NICHT 0 (also bitgleich): Grundbild und Messbild werden mit verschiedenen
# Farbtiefen aufgenommen — der leere Desktop liefert 24 bpp, sobald ein Emulator mit
# 32-Bit-Visual im Vollbild steht, liefert `xwd -root` 32 bpp. Der Verlauf des
# Hintergrundbildes wird dabei anders gerastert. Am laufenden Host gemessen, im rechts
# NEBEN xemu sichtbaren Stueck Hintergrundbild: nur 7,2 % der Punkte sind bitgleich,
# 63,4 % liegen innerhalb von 8, 85,9 % innerhalb von 16. Auf der weissen Flaeche von
# xemu dagegen liegt bei Toleranz 16 KEIN einziger Punkt — echter Bildinhalt weicht viel
# weiter ab als das Rauschen.
#
# WARUM 8 UND NICHT 16: Die Toleranz gemessen durchgereicht, drei Zustaende:
#
#     Toleranz   leerer Desktop   xemu (Bild 1280x963)   Flycast (echtes Vollbild)
#          0          0,06 %            95,13 %                  100,00 %
#          8          0,06 %            74,87 %                   99,97 %
#         16          0,06 %            64,45 %                   90,62 %
#         32          0,06 %            44,52 %                   77,52 %
#
# 16 trifft xemus wahren Wert besser (1280*963 von 1920*1080 = 59,4 %), bringt aber
# Flycast auf 90,62 % — einen halben Punkt ueber der Schwelle. Ein dunkler Titel faellt
# dort unter sie und bekaeme ein F11, das ihm sein Vollbild naehme. 8 laesst den Gutfall
# bei 99,97 % und meldet xemu trotzdem 15 Punkte unter der Schwelle.
# EN: baseline and measurement are captured at different colour depths, so a gradient
# wallpaper dithers differently; 8 keeps the good case at 99.97 % while still flagging
# xemu 15 points below the threshold.
FARBTOLERANZ = 8

# Abgetastet wird jeder 6. Punkt in beiden Richtungen — bei 1920x1080 rund 57.000
# Punkte, genug fuer eine Flaechenangabe und schnell genug, um im Startweg zu stehen.
RASTER = 6


def _xwd_kopf(daten):
    """-> Kopfangaben einer `xwd`-Aufnahme, oder None wenn unbrauchbar.

    DIE SCHRITTWEITE KOMMT AUS `bits_per_pixel`, NICHT AUS `bytes_per_line` — und zwar
    JE AUFNAHME. Am laufenden Host gemessen, zwei Aufnahmen DESSELBEN 1920 Punkte breiten
    Schirms, wenige Minuten auseinander:

        leerer Desktop         bits_per_pixel 24   bytes_per_line 7680   -> 3 Byte/Punkt
        Flycast im Vollbild    bits_per_pixel 32   bytes_per_line 7680   -> 4 Byte/Punkt

    `bytes_per_line` ist im ersten Fall AUFGEFUELLT: 1920 * 3 = 5760 genutzte Byte je
    Zeile, der Rest ist Rand. 7680 / 1920 zu rechnen ergibt 4 und liest damit ueber die
    Zeile hinaus — nachgestellt und angesehen: das Bild erscheint auf drei Viertel der
    Breite gestaucht, mit einem schwarzen Streifen rechts, und 25 % der Punkte lesen sich
    als reines Schwarz. Mit 3 Byte dekodiert dieselbe Datei sauber (0 % Nullpunkte) und
    deckt sich Punkt fuer Punkt mit dem, was `ffmpeg` aus ihr macht.

    Dass sich der Wert zwischen zwei Aufnahmen aendert, ist der Grund fuer das „je
    Aufnahme": Grundbild und Messbild koennen verschiedene Schrittweiten haben.

    EN: derive the stride from bits_per_pixel, per capture. bytes_per_line is padded — a
    24-bpp 1920-wide row uses 5760 of its 7680 bytes, and dividing gives 4, which reads
    past the row: the image decodes squeezed into three quarters of the width with a black
    band on the right.
    """
    if len(daten) < 100:
        return None
    k = struct.unpack(">25I", daten[:100])
    kopfgroesse, version, format_ = k[0], k[1], k[2]
    breite, hoehe, bpp, bytes_pro_zeile, ncolors = k[4], k[5], k[11], k[12], k[19]
    if version != 7 or format_ != 2 or not breite or not hoehe or not bytes_pro_zeile:
        return None
    return {"start": kopfgroesse + ncolors * 12, "breite": breite, "hoehe": hoehe,
            "zeile": bytes_pro_zeile, "schritt": max(1, bpp // 8),
            "r": k[14], "g": k[15], "b": k[16]}


def _punkt(daten, kopf, x, y):
    o = kopf["start"] + y * kopf["zeile"] + x * kopf["schritt"]
    return int.from_bytes(daten[o:o + kopf["schritt"]], "little")


def _farbe(wert, kopf):
    return (((wert & kopf["r"]) >> 16) & 0xFF, ((wert & kopf["g"]) >> 8) & 0xFF,
            wert & kopf["b"] & 0xFF)


def _helligkeit(wert, kopf):
    return max(_farbe(wert, kopf))


def _gleiche_farbe(a, ka, b, kb):
    """Zwei Bildpunkte, die dasselbe zeigen — bis auf FARBTOLERANZ je Kanal."""
    fa, fb = _farbe(a, ka), _farbe(b, kb)
    return all(abs(fa[i] - fb[i]) <= FARBTOLERANZ for i in range(3))


def _bildschirm_aufnehmen():
    """-> Rohdaten einer `xwd -root`-Aufnahme, oder None. `xwd` liegt im Basis-Image."""
    ziel = os.path.join(tempfile.gettempdir(), "vollbild-messung.xwd")
    try:
        r = _x("xwd", "-root", "-silent", "-out", ziel)
        if r.returncode != 0 or not os.path.isfile(ziel):
            return None
        return open(ziel, "rb").read()
    except OSError:
        return None
    finally:
        try:
            os.remove(ziel)
        except OSError:
            pass


def desktop_ist_frei():
    """-> (True, "") wenn ausser Panel und Desktop kein Fenster im Bild steht.

    `_NET_CLIENT_LIST` fuehrt die verwalteten Programmfenster. Am laufenden Host im
    Leerlauf abgelesen — genau zwei, und beide sind Moebel, kein Programm:

        _NET_CLIENT_LIST(WINDOW): window id # 0x1a00003, 0x1c00017
        0x1a00003 [xfce4-panel] _NET_WM_WINDOW_TYPE_DOCK
        0x1c00017 [Desktop]     _NET_WM_WINDOW_TYPE_DESKTOP

    EN: the managed-window list is empty of applications when only the panel and the
    desktop are up.
    """
    liste = _x("xprop", "-root", "_NET_CLIENT_LIST").stdout
    for fid in re.findall(r"0x[0-9a-fA-F]+", liste):
        typ = _x("xprop", "-id", fid, "_NET_WM_WINDOW_TYPE").stdout
        if "_NET_WM_WINDOW_TYPE_DESKTOP" in typ or "_NET_WM_WINDOW_TYPE_DOCK" in typ:
            continue
        return False, (fenstername(fid) or fid)
    return True, ""


def grundbild_aufnehmen():
    """Den LEEREN Desktop aufnehmen, gegen den spaeter gemessen wird. -> (ok, meldung)

    WOZU (#495): Ohne Vergleichsbild kann keine Flaechenmessung ein Spiel von einem
    Hintergrundbild unterscheiden — beide sind „bemalt". Mit ihm ist die Frage
    beantwortbar und kostet einen zweiten `xwd`-Aufruf.

    ZWEI SPERREN, und beide sind noetig:

    1. Steht ein Programmfenster im Bild, wird NICHT aufgenommen. Ein Grundbild mit dem
       Spiel darin waere die perfekte Taeuschung: jeder folgende Start saehe aus, als
       haette der Emulator nichts uebernommen — also genau die Fehlmessung, gegen die
       das Grundbild gebaut ist. Das alte bleibt dann liegen; der Desktop aendert sich
       nicht, ein Grundbild von vorhin ist so gut wie eines von jetzt.
    2. Ein fast ganz schwarzer Schirm wird abgelehnt. So sieht es aus, wenn X oder XFCE
       noch hochfahren — und gegen ein schwarzes Grundbild misst spaeter JEDER Emulator
       100 %, also nie wieder eine Korrektur.

    EN: two guards. A baseline WITH a game in it would mark every later launch as "the
    emulator took nothing over"; an all-black one (X still starting) would mark every
    launch as perfect. Both would silently disable the correction.
    """
    frei, stoerer = desktop_ist_frei()
    if not frei:
        return False, f"nicht aufgenommen — ein Fenster steht im Bild: {stoerer}"
    daten = _bildschirm_aufnehmen()
    kopf = _xwd_kopf(daten) if daten else None
    if not kopf:
        return False, "Bildschirm nicht lesbar"
    punkte = nicht_schwarz = 0
    for y in range(0, kopf["hoehe"], RASTER):
        for x in range(0, kopf["breite"], RASTER):
            punkte += 1
            if _helligkeit(_punkt(daten, kopf, x, y), kopf) > SCHWARZ:
                nicht_schwarz += 1
    anteil = nicht_schwarz / punkte * 100 if punkte else 0.0
    if anteil < 5:
        return False, (f"nur {anteil:.1f} % des Schirms sind nicht schwarz — "
                       "faehrt die Oberflaeche noch hoch?")
    try:
        with open(GRUNDBILD, "wb") as f:
            f.write(daten)
    except OSError as e:
        return False, f"nicht schreibbar: {e.__class__.__name__}"
    return True, (f"Grundbild aufgenommen: {kopf['breite']}x{kopf['hoehe']}, "
                  f"{anteil:.1f} % nicht schwarz")


def emulatoranteil():
    """-> Anteil des Bildschirms in Prozent, den der EMULATOR uebernommen hat, oder None.

    DIE ALTE MESSUNG WAR NICHT UNGENAU, SONDERN VERKEHRT HERUM (#495). Sie suchte den
    Rahmen der nicht-schwarzen Punkte auf dem Bildschirm — und ein Hintergrundbild ist
    nicht schwarz. Am laufenden Host gemessen, drei Zustaende:

        leerer Desktop, kein Emulator        99,28 %
        xemu, Bild 1280x963 auf dem Desktop  99,28 %   <- bitgleich derselbe Wert
        Flycast, echtes Vollbild             73,56 %   <- der Gutfall misst WENIGER

    Der leere Desktop stand also ueber der Schwelle und ein wirklich bildschirmfuellender
    Emulator darunter.

    WIE ES JETZT GEHT: verglichen wird Punkt fuer Punkt mit dem Grundbild des leeren
    Desktops (`grundbild_aufnehmen`). Ein Punkt zaehlt als „noch Desktop", wenn er
    unveraendert ist (bis auf FARBTOLERANZ) UND im Grundbild nicht schwarz war — schwarz
    auf schwarz ist keine Auskunft, das malt ein Emulator genauso. Der Rest gehoert dem
    Emulator. Dieselben drei Zustaende, am laufenden Host gemessen:

        leerer Desktop                        0,06 %
        xemu, Bild 1280x963                  74,87 %   (wahrer Wert 59,4 %)
        Flycast, echtes Vollbild             99,97 %

    WARUM NICHT EINFACH AUF DIE FENSTERGEOMETRIE BESCHRAENKEN, wie #495 vorschlug: weil
    der Desktop INNERHALB des Fensters liegt. xemus X-Fenster ist wirklich 1920x1080
    (`xwininfo` bestaetigt es), bemalt wird davon aber nur rund 1280x963 — der Rest bleibt
    unberuehrt und zeigt weiter, was vorher da war. Auf die Fenstergeometrie beschraenkt
    gemessen kam derselbe Fehlwert heraus: 99,64 %.

    WAS DIE ZAHL NICHT IST: eine genaue Flaechenangabe. xemu deckt 1280*963 von 1920*1080,
    also 59,4 % — gemeldet werden 74,87 %, weil das Rauschen im Hintergrundbild (siehe
    FARBTOLERANZ) zulasten des Desktops geht. Gebraucht wird hier eine Entscheidung
    „fuellt aus / fuellt nicht aus", und dafuer ist der Abstand zur Schwelle gross genug.
    Wer die Zahl als Flaechenmass liest, liest zu viel hinein.

    EN: the old measurement was inverted, not merely imprecise — a bare desktop scored
    above the threshold and a genuinely fullscreen emulator below it. Restricting it to
    the window geometry does not help, because xemu leaves most of its own window
    unpainted and the wallpaper shows through there.
    """
    try:
        grund = open(GRUNDBILD, "rb").read()
    except OSError:
        return None
    jetzt = _bildschirm_aufnehmen()
    if not jetzt:
        return None
    try:
        kg, kj = _xwd_kopf(grund), _xwd_kopf(jetzt)
        if not kg or not kj:
            return None
        if (kg["breite"], kg["hoehe"]) != (kj["breite"], kj["hoehe"]):
            # Aufloesung gewechselt: das Grundbild misst nicht mehr denselben Schirm.
            return None
        punkte = desktop = 0
        for y in range(0, kg["hoehe"], RASTER):
            for x in range(0, kg["breite"], RASTER):
                punkte += 1
                wg = _punkt(grund, kg, x, y)
                if _helligkeit(wg, kg) > SCHWARZ and \
                   _gleiche_farbe(wg, kg, _punkt(jetzt, kj, x, y), kj):
                    desktop += 1
        if not punkte:
            return None
        return 100 - desktop / punkte * 100
    except (struct.error, ValueError):
        return None


def vollbild_sicherstellen(fensterid=None):
    """Messen, und nur wenn noetig mit F11 nachhelfen. -> (anteil_vorher, anteil_nachher, weg)

    WARUM MESSEN UND NICHT EINFACH F11 SCHICKEN: **F11 ist ein Umschalter.** Ein Emulator,
    bei dem der Fenstertrick bereits gewirkt hat, fiele dadurch WIEDER aus dem Vollbild —
    aus einem funktionierenden Fall wuerde ein kaputter. Die Messung ist deshalb keine
    zusaetzliche Vorsicht, sondern das, was die Korrektur ueberhaupt erst ungefaehrlich
    macht.

    So braucht auch ein Emulator, den nie jemand ausprobiert hat, keine vorab ausgefuellte
    Zeile in einer Tabelle: Er wird beim ersten Start gemessen und, wenn noetig, korrigiert.

    EN: F11 is a toggle. Sending it blindly would knock an already-fullscreen emulator back
    out. Measuring first is what makes the correction safe — and it means an emulator nobody
    has ever exercised is handled on its first launch.
    """
    vorher = emulatoranteil()
    if vorher is None:
        # Kein Grundbild, kein Vergleich — und lieber nichts tun als auf gut Glueck ein
        # F11 schicken. Es ist ein Umschalter: geraten waere hier schlimmer als warten.
        return None, None, "nicht messbar"
    if vorher >= VOLLBILD_SCHWELLE:
        return vorher, vorher, "Bildschirm bereits uebernommen"
    ziel = fensterid
    if not ziel:
        gefunden = _x("xdotool", "getactivewindow").stdout.split()
        ziel = gefunden[0] if gefunden else None
    if not ziel:
        return vorher, vorher, "kein Fenster fuer F11 gefunden"
    # DIE MESSUNG OBEN GENUEGT NICHT — sie war der Fehler. (#493)
    #
    # Ein Titel, der gerade noch die Disc bootet, ist schwarz: DuckStation kam bei jedem
    # PSX-Start auf 34,3 %, obwohl sein Fenster den ganzen Schirm deckte und
    # `_NET_WM_STATE_FULLSCREEN` trug. F11 schaltete daraufhin genau das ab — danach
    # 640x480 in der Ecke, mit Titelleiste zurueck, und so blieb es.
    #
    # Am Grundbild aendert das nichts: ein schwarz gemaltes Bild deckt den Desktop zwar
    # zu, zaehlt hier aber nicht als uebernommen (schwarz auf hell ist eine Aenderung,
    # schwarz auf schwarz nicht — siehe `emulatoranteil`). Der Bootschirm bleibt also ein
    # Grund fuer ein F11, das dem Emulator sein eigenes Vollbild nehmen wuerde.
    #
    # Der Fensterzustand entscheidet das, kostet einen `xprop`-Aufruf und ist
    # emulatorunabhaengig: Wer sein Vollbild selbst haelt, wird in Ruhe gelassen. Wer
    # keinen eigenen Schalter hat — xemu, Azahar, Eden —, traegt den Zustand nicht und
    # bekommt sein F11 weiterhin.
    # EN: a title still booting its disc is black, which no area measurement can tell from
    # a small window. The window state is the fact that distinguishes the two.
    if ist_vollbild(str(ziel)):
        return vorher, vorher, "steht im eigenen Vollbild — F11 waere der Ausstieg"
    _x("xdotool", "windowactivate", str(ziel))
    time.sleep(1)
    _x("xdotool", "key", "--window", str(ziel), "F11")
    time.sleep(2)
    nachher = emulatoranteil()
    return vorher, nachher, "F11"


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
    if argv and argv[0] == "--dialogs":
        if len(argv) < 2 or argv[1] not in PROFILE:
            print("Aufruf: --dialogs <emulator>", file=sys.stderr); return 1
        fn = PROFILE[argv[1]].get("dialoge")
        if not fn:
            print(f"[dialoge] {argv[1]}: keine bekannten Startdialoge")
            return 0
        geaendert, msg = sicher(fn)
        print(f"[dialoge] {argv[1]}: {msg}")
        # WIE BEIM VOLLBILD: immer 0. Ein Dialog, der stehen bleibt, kostet das Bild —
        # den Start zu verweigern kostet das Spiel. / always 0: a leftover dialog costs
        # the picture, refusing the launch costs the game.
        return 0
    if argv and argv[0] == "--window":
        if len(argv) < 2 or not argv[1].isdigit():
            print("Aufruf: --window <pid>", file=sys.stderr); return 1
        zustand, msg = nur_emulator(int(argv[1]))
        print(f"[fenster] {msg}")
        # MESSEN, NICHT ANNEHMEN (#429). Der Fensterschritt meldet bisher „ok", sobald die
        # HUELLE auf voller Flaeche steht — und genau das war bei xemu, Azahar und Eden
        # wahr, waehrend das Bild kleiner blieb. Deshalb hier die Gegenprobe am Inhalt,
        # und nur wo sie ausfaellt, die Korrektur per F11.
        anteil = None
        if zustand == "ok":
            vorher, nachher, weg = vollbild_sicherstellen()
            anteil = nachher
            if vorher is None:
                # NICHT VERSCHWEIGEN. Ohne Grundbild unterbleibt die Korrektur — das ist
                # die sichere Seite, aber es ist auch der Zustand, in dem xemu wieder mit
                # halbem Bild dasteht. Wer das Log liest, muss es sehen.
                print("[vollbild] nicht messbar — kein Grundbild oder Schirm nicht lesbar")
            elif weg == "F11":
                print(f"[vollbild] {vorher:.1f} % vom Emulator -> F11 -> "
                      f"{nachher if nachher is None else f'{nachher:.1f} %'}")
            else:
                print(f"[vollbild] {vorher:.1f} % vom Emulator — {weg}")
            # ZULETZT NACHMESSEN (#493). Der Befund oben entsteht, BEVOR der
            # Vollbildschritt laeuft — und genau der hat den Titel bisher aus seinem
            # eigenen Vollbild geholt. Eine Groesse, die vor dem Schaden abgelesen wurde,
            # ist keine Auskunft ueber den Zustand danach.
            # EN: measured last, because the fullscreen step runs after the window step
            # and used to be what shrank the window.
            sichtbar = sichtbare_fenster(int(argv[1]))
            gemessen = fenstergroesse(sichtbar[0]) if sichtbar else ""
            if gemessen:
                msg = f"{msg}, gemessen {gemessen}"
                print(f"[fenster] groesstes Fenster gemessen: {gemessen}")
        # Maschinenlesbar als LETZTE Zeile, damit der Agent den Befund weiterreichen
        # kann statt ihn nur ins Log zu schreiben (#288). Eine JSON-Zeile statt eines
        # blossen Exit-Codes, weil der Dialogtitel die eigentliche Auskunft ist.
        # `emulator` statt des frueheren `bemalt`: der Wert misst nicht mehr, wieviel
        # Farbe auf dem Schirm ist, sondern wieviel davon der Emulator uebernommen hat.
        # Denselben Namen weiterzufuehren hiesse, die alte Bedeutung mitzuschleppen.
        print(json.dumps({"window": zustand, "detail": msg, "emulator": anteil}))
        return 0 if zustand == "ok" else 1
    if argv and argv[0] == "--grundbild":
        # VOR dem Start des Emulators aufzurufen — danach steht sein Fenster im Bild und
        # die Aufnahme wird (zu Recht) verweigert.
        _ok, msg = grundbild_aufnehmen()
        print(f"[grundbild] {msg}")
        # IMMER 0. Ohne Grundbild unterbleibt spaeter nur die Vollbildkorrektur; den
        # Start deswegen abzubrechen kostet das Spiel. / always 0: a missing baseline
        # only disables the fullscreen correction, it must not fail the launch.
        return 0
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
        # ALLE Aufrufzeilen, nicht die drittletzte: die stand hier fest verdrahtet und
        # zeigte nach jeder neuen Zeile im Kopf auf eine andere. (#488)
        for zeile in __doc__.splitlines():
            if zeile.strip().startswith("launch-profile.py "):
                print(zeile.strip(), file=sys.stderr)
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
    # WEITERE EINSTELLUNGEN ZUERST. Sie entscheiden, WIE der Emulator startet (xemus
    # Renderer etwa), waehrend die Controllerbindung nur beeinflusst, was er dann
    # entgegennimmt. Scheitert eine davon, soll das sichtbar sein, bevor irgendjemand
    # den Controller fuer die Ursache haelt.
    fehler = False
    for fn_extra in PROFILE[ziel].get("einstellungen") or []:
        _, msg = sicher(fn_extra)
        print(f"[einstellungen] {ziel}: {msg}")
        fehler = fehler or msg.startswith("KEIN ZUGRIFF")

    fn = PROFILE[ziel]["controller"]
    if not fn:
        print(f"[controller] {ziel}: ordnet ein erkanntes SDL-Pad selbst zu")
        return 1 if fehler else 0
    geaendert, msg = sicher(fn)
    print(f"[controller] {ziel}: {msg}")
    # Ein Rechtefehler ist KEIN Erfolg. Frueher verliess er das Programm als Traceback,
    # der Rueckgabewert blieb 0, und der Agent startete den Emulator ohne gesetztes
    # BIOS und ohne Vollbild — das Ergebnis war ein Dialog statt eines Spiels.
    # EN: a permission error is not success; it used to leave as a traceback while the
    # exit code stayed 0 and the emulator came up unconfigured.
    return 1 if (fehler or msg.startswith("KEIN ZUGRIFF")) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
