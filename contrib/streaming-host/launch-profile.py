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
import sys

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
                  "bios": pcsx2_bios_setzen, "geprueft": True},
    "dolphin":   {"system": "GameCube/Wii",  "controller": None, "bios": None,
                  "geprueft": False},
    "flycast":   {"system": "Dreamcast",     "controller": None, "bios": None,
                  "geprueft": False},
    "xemu":      {"system": "Xbox",          "controller": None, "bios": None,
                  "geprueft": False},
    "cemu":      {"system": "Wii U",         "controller": None, "bios": None,
                  "geprueft": False},
    "azahar":    {"system": "3DS",           "controller": None, "bios": None,
                  "geprueft": False},
    "vita3k":    {"system": "PS Vita",       "controller": None, "bios": None,
                  "geprueft": False},
    "rpcs3":     {"system": "PS3",           "controller": None, "bios": None,
                  "geprueft": False},
    "switchemu": {"system": "Switch",        "controller": None, "bios": None,
                  "geprueft": False},
}
# "geprueft: False" heisst NICHT "funktioniert nicht", sondern "noch nicht am
# laufenden Emulator nachgemessen". Die Unterscheidung ist der Punkt: sie zeigt, wo
# eine Zusage auf Messung beruht und wo auf Annahme. Siehe #136.


def main(argv):
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
