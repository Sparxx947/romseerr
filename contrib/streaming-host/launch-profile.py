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
RPCS3_PAD = os.environ.get("RPCS3_PAD_NAME", "Microsoft X-Box 360 pad")


def rpcs3_input():
    return os.path.join(CONFIG, ".config/rpcs3/input_configs/global/Default.yml")


def rpcs3_apply(pruefen=False):
    """-> (geaendert, meldung). Legt den SDL-Handler an, WENN noch nichts da ist.

    WAS DAS TUT UND WAS NICHT: RPCS3s Standard bindet Spieler 1 an die Tastatur und
    schreibt bis zum ersten Griff in den Einstellungsdialog gar keine Konfiguration.
    Dieser Stumpf sorgt dafuer, dass wenigstens der SDL-Handler und das richtige Geraet
    eingetragen sind.

    ER MACHT DAS PAD NOCH NICHT SPIELBAR. Nachgemessen, entgegen der urspruenglichen
    Annahme: RPCS3 ergaenzt KEINE Standardbelegung. Im Log steht dann

        Input: Pad 0: device='...', handler=SDL
        Input: Pad 0: config=            <- leer
        SDL: Adding empty device: ...

    Die Tastenbelegung muss einmal im Pad-Dialog von RPCS3 gesetzt werden. Danach
    bleibt sie in /config erhalten.

    UND DESHALB WIRD NIE UEBERSCHRIEBEN: Das Profil laeuft VOR JEDEM Start. Wuerde es
    eine vorhandene Datei ersetzen, waere die von Hand gesetzte Belegung beim naechsten
    Start weg — lautlos, und es haette die Arbeit des Nutzers zunichte gemacht. Das war
    im ersten Wurf tatsaechlich so. (#158)
    Never overwrites: the profile runs before every launch, so replacing an existing
    file would silently discard the mapping the operator set by hand.
    """
    pfad = rpcs3_input()
    soll = f'Player 1 Input:\n  Handler: SDL\n  Device: "{RPCS3_PAD}"\n'
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
    return True, (f"SDL-Handler angelegt, Geraet '{RPCS3_PAD}' — "
                  "Tastenbelegung noch EINMAL im Pad-Dialog von RPCS3 setzen")


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
    "pcsx2":     {"system": "PS2",           "controller": pcsx2_apply,
                  "bios": pcsx2_bios_setzen, "vollbild": pcsx2_vollbild,
                  "geprueft": True},
    "dolphin":   {"system": "GameCube/Wii",  "controller": None, "bios": None, "vollbild": None,
                  "geprueft": False},
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
    # geprueft bleibt False, bis ein Mensch das Pad IM SPIEL bewegt hat. Gemessen ist
    # bisher nur, dass RPCS3 das Geraet annimmt (die Warnung „Adding empty device"
    # verschwindet) — das ist ein Hinweis, kein Nachweis.
    "rpcs3":     {"system": "PS3",           "controller": rpcs3_apply,
                  "bios": None, "vollbild": None,
                  "geprueft": False},
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


def main(argv):
    if argv and argv[0] == "--fullscreen":
        if len(argv) < 2 or argv[1] not in PROFILE:
            print("Aufruf: --fullscreen <emulator>", file=sys.stderr); return 1
        fn = PROFILE[argv[1]].get("vollbild")
        if not fn:
            print(f"[vollbild] {argv[1]}: kein eigener Schalter — Fenstertrick greift")
            return 2                       # 2 = Rueckfall noetig
        geaendert, msg = fn()
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
        geaendert, msg = fn(argv[2])
        print(f"[bios] {argv[1]}: {msg}")
        return 0 if geaendert or "bereits" in msg else 1
    if not argv or argv[0] not in ("--apply", "--status"):
        print(__doc__.strip().splitlines()[-3], file=sys.stderr)
        return 2
    if argv[0] == "--status":
        for name, e in PROFILE.items():
            teile = []
            if e["controller"]:
                noetig, msg = e["controller"](pruefen=True)
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
    geaendert, msg = fn()
    print(f"[controller] {ziel}: {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
