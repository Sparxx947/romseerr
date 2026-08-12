#!/usr/bin/env python3
"""Schreibt die transitive Hälfte von requirements.txt neu. (#380)

Aufruf:
    python3 scripts/lock_requirements.py            # Datei neu schreiben
    python3 scripts/lock_requirements.py --check    # nur melden (Exit 1 = etwas ist neuer)

WAS GEPFLEGT WIRD UND WAS NICHT: Der Abschnitt `--- direkt / direct ---` gehört dem
Menschen — dort steht, was app.py importiert. Alles unter `--- transitiv / transitive ---`
erzeugt dieses Skript. Es rechnet die Hülle mit `uv pip compile` bzw. `pip-compile` aus;
beide lösen für die Zielumgebung auf, nicht für die des Aufrufers.

WARUM DAS NICHT IN CI LÄUFT: Ein `--check` in der CI würde rot, sobald irgendwo auf PyPI
eine neue Fassung erscheint — also an Tagen, an denen niemand etwas geändert hat. Das
Hochziehen ist Dependabots Aufgabe, samt Pull Request, Diff und CI-Lauf. Dieses Skript ist
für den Fall danach: wenn ein Bump neue transitive Pakete mitbringt und der Bau an
`pip check` scheitert.

EN: regenerates the transitive half of requirements.txt. The direct section is hand-kept.
Deliberately not wired into CI — that is Dependabot's job; this is for the aftermath.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQ = os.path.join(WURZEL, "requirements.txt")
MARKE_DIREKT = "# --- direkt / direct ---"
MARKE_TRANSITIV = "# --- transitiv / transitive ---"

# Muss zur Basis des Dockerfiles passen (`FROM python:3.12-slim`) — sonst löst das Skript
# für die Python-Fassung des Aufrufers auf, und das Image bekommt eine andere Hülle.
ZIEL_PYTHON = "3.12"

ZEILE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;#]+)\s*$")


def norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def lies_abschnitte(text):
    """(kopf, direkt, transitiv) — kopf einschließlich der Marke des direkten Teils."""
    kopf, direkt, transitiv = [], [], []
    ziel = kopf
    for zeile in text.splitlines():
        if zeile.strip() == MARKE_DIREKT:
            kopf.append(zeile)
            ziel = direkt
            continue
        if zeile.strip() == MARKE_TRANSITIV:
            ziel = transitiv
            continue
        ziel.append(zeile)
    return "\n".join(kopf), direkt, transitiv


def pakete(zeilen):
    return [z.strip() for z in zeilen if z.strip() and not z.strip().startswith("#")]


def kommentarkopf(zeilen):
    """Die Kommentarzeilen am Anfang eines Abschnitts — sie bleiben erhalten."""
    raus = []
    for z in zeilen:
        if z.strip().startswith("#") or not z.strip():
            raus.append(z)
        else:
            break
    return raus


def loese_auf(direkte):
    """Volle Hülle der direkten Pakete, als sortierte `name==version`-Liste."""
    with tempfile.TemporaryDirectory() as tmp:
        quelle = os.path.join(tmp, "direct.in")
        with open(quelle, "w", encoding="utf-8") as fh:
            fh.write("\n".join(direkte) + "\n")
        if shutil.which("uv"):
            befehl = ["uv", "pip", "compile", quelle, "--python-version", ZIEL_PYTHON,
                      "--upgrade", "--no-header", "--no-annotate"]
        elif shutil.which("pip-compile"):
            befehl = ["pip-compile", "--upgrade", "--no-header", "--no-annotate",
                      "--output-file", "-", quelle]
        else:
            raise SystemExit("Weder `uv` noch `pip-compile` gefunden — "
                             "`pip install uv` oder `pip install pip-tools`.")
        lauf = subprocess.run(befehl, capture_output=True, text=True, check=False)
        if lauf.returncode != 0:
            sys.stderr.write(lauf.stderr)
            raise SystemExit(f"Auflösung fehlgeschlagen ({' '.join(befehl)})")
    treffer = []
    for zeile in lauf.stdout.splitlines():
        m = ZEILE.match(zeile.strip())
        if m:
            treffer.append(f"{m.group(1)}=={m.group(2)}")
    if not treffer:
        raise SystemExit("Auflösung lieferte keine Pakete — Abbruch, statt die Datei zu leeren.")
    return sorted(treffer, key=lambda z: norm(z.split("==")[0]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true",
                   help="nur vergleichen, nichts schreiben (Exit 1 bei Unterschied)")
    args = p.parse_args()

    with open(REQ, encoding="utf-8") as fh:
        alt = fh.read()
    kopf, direkt_zeilen, transitiv_zeilen = lies_abschnitte(alt)
    direkte = pakete(direkt_zeilen)
    if not direkte:
        raise SystemExit(f"Kein Abschnitt {MARKE_DIREKT!r} mit Paketen in {REQ}")

    huelle = loese_auf(direkte)
    direkt_namen = {norm(z.split("==")[0]) for z in direkte}
    neu_direkt = [z for z in huelle if norm(z.split("==")[0]) in direkt_namen]
    neu_transitiv = [z for z in huelle if norm(z.split("==")[0]) not in direkt_namen]

    text = "\n".join([
        kopf,
        *kommentarkopf(direkt_zeilen),
        *neu_direkt,
        "",
        MARKE_TRANSITIV,
        *kommentarkopf(transitiv_zeilen),
        *neu_transitiv,
    ]) + "\n"

    if text == alt:
        print(f"{len(huelle)} Pakete, nichts Neues.")
        return 0
    unterschied = sorted(set(huelle) ^ {z for z in pakete(direkt_zeilen) + pakete(transitiv_zeilen)})
    if args.check:
        print("Unterschied:\n  " + "\n  ".join(unterschied))
        return 1
    with open(REQ, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"{REQ} geschrieben — {len(huelle)} Pakete. Geändert:\n  " + "\n  ".join(unterschied))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
