#!/usr/bin/env python3
"""Controller-Belegung je Emulator setzen. / Apply a controller mapping per emulator.

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

    controller-profile.py --apply pcsx2      # eine Belegung setzen
    controller-profile.py --status           # was ist belegt?
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


# Emulator -> (Funktion, Anmerkung). Wer hinzukommt, steht hier — eine Stelle.
PROFILE = {
    "pcsx2": (pcsx2_apply, "PS2"),
}
# Flycast, xemu, Cemu, Azahar, Vita3K und der Switch-Emulator ordnen ein erkanntes
# SDL-Pad selbst zu und brauchen keine Vorbelegung. Sollte sich das als falsch
# erweisen, gehoert der Eintrag hierher — geprueft, nicht vermutet.
# The others map a detected SDL pad themselves; entries belong here once measured.


def main(argv):
    if not argv or argv[0] not in ("--apply", "--status"):
        print(__doc__.strip().splitlines()[-3], file=sys.stderr)
        return 2
    if argv[0] == "--status":
        for name, (fn, sys_) in PROFILE.items():
            noetig, msg = fn(pruefen=True)
            print(f"{name} ({sys_}): {'offen' if noetig else 'gesetzt'} — {msg}")
        return 0
    ziel = argv[1] if len(argv) > 1 else ""
    if ziel not in PROFILE:
        print(f"kein Profil fuer '{ziel}' / no profile for it", file=sys.stderr)
        return 1
    geaendert, msg = PROFILE[ziel][0]()
    print(f"[controller] {ziel}: {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
