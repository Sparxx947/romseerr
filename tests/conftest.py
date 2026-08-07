"""Test-Fixtures: importiert app mit temporären CONFIG/ROMS-Verzeichnissen.

Die Basis-Pfade werden per Env gesetzt, BEVOR app importiert wird, damit die Tests
niemals echte Daten unter /config oder /roms anfassen.
"""
import os
import sys
import tempfile
import importlib

import pytest


@pytest.fixture(scope="session")
def appmod():
    tmp = tempfile.mkdtemp(prefix="romseerr-test-")
    os.makedirs(os.path.join(tmp, "roms"), exist_ok=True)
    os.environ["ROMSEERR_CONFIG"] = tmp
    os.environ["ROMSEERR_ROMS"] = os.path.join(tmp, "roms")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    sys.modules.pop("app", None)
    mod = importlib.import_module("app")
    mod.db_init()
    return mod


@pytest.fixture
def client(appmod):
    appmod.app.config["TESTING"] = True
    return appmod.app.test_client()
