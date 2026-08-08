#!/usr/bin/env python3
"""Erzeugt docs/openapi.yaml aus der einzigen Quelle der Wahrheit app.OPENAPI.

Aufruf: python scripts/build_openapi.py
So bleibt die Repo-Spec mit dem in der App ausgelieferten /api/openapi.json identisch.
"""
import os
import re
import sys

import yaml  # pyyaml

# Die Versionszeile hat ZWEI Besitzer: hier wird sie erzeugt (aus version.txt ueber
# app.VERSION), und release-please hebt sie beim Release an. Ohne Absprache scheitert
# jeder Release-Lauf am Gleichstandstest — release-please hebt version.txt, diese Datei
# bleibt zurueck, und der Test vergleicht beide. Genau so hing der Release fest.
#
# Die Absprache ist diese Marke: release-please kennt `x-release-please-version` und
# ersetzt den Wert in der so markierten Zeile. Sie muss jede Neuerzeugung ueberleben,
# deshalb wird sie hier gesetzt und nicht von Hand gepflegt.
#
# The version line has two owners: this generator and release-please. The annotation is
# the agreement between them, and it has to survive regeneration — hence written here.
VERSIONSMARKE = "  # x-release-please-version"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# Import ohne Nebenwirkungen (build_index/app.run laufen nur unter __main__)
import app  # noqa: E402

text = yaml.safe_dump(app.OPENAPI, sort_keys=False, allow_unicode=True, width=100)

# Nur die Versionszeile unter `info:` markieren. `/api/version:` ist ein Pfad und
# `version=0.0.4` steht in einer Beschreibung — beide passen auf dieses Muster nicht,
# weil hier `version:` unmittelbar auf Einrueckung folgen muss. count=1 sichert es ab.
text, treffer = re.subn(r"^(  version: .*)$", r"\1" + VERSIONSMARKE, text, count=1, flags=re.M)
if treffer != 1:
    # Lieber abbrechen als eine Datei schreiben, die release-please nicht anfassen kann:
    # der Fehler faellt sonst erst im Release-Lauf auf, Wochen spaeter.
    raise SystemExit("Versionszeile nicht gefunden — Marke nicht gesetzt, Abbruch. "
                     "/ version line not found; refusing to write an unmarked file.")

out = os.path.join(ROOT, "docs", "openapi.yaml")
with open(out, "w") as f:
    f.write("# GENERIERT aus app.OPENAPI — nicht von Hand ändern. / GENERATED — do not edit.\n")
    f.write("# Neu erzeugen: python scripts/build_openapi.py\n")
    f.write(text)
print(f"geschrieben / wrote: {out}")
