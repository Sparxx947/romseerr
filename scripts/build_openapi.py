#!/usr/bin/env python3
"""Erzeugt docs/openapi.yaml aus der einzigen Quelle der Wahrheit app.OPENAPI.

Aufruf: python scripts/build_openapi.py
So bleibt die Repo-Spec mit dem in der App ausgelieferten /api/openapi.json identisch.
"""
import os
import sys

import yaml  # pyyaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# Import ohne Nebenwirkungen (build_index/app.run laufen nur unter __main__)
import app  # noqa: E402

out = os.path.join(ROOT, "docs", "openapi.yaml")
with open(out, "w") as f:
    f.write("# GENERIERT aus app.OPENAPI — nicht von Hand ändern. / GENERATED — do not edit.\n")
    f.write("# Neu erzeugen: python scripts/build_openapi.py\n")
    yaml.safe_dump(app.OPENAPI, f, sort_keys=False, allow_unicode=True, width=100)
print(f"geschrieben / wrote: {out}")
