"""Test-Fixtures: importiert app mit temporären CONFIG/ROMS-Verzeichnissen.

Die Basis-Pfade werden per Env gesetzt, BEVOR app importiert wird, damit die Tests
niemals echte Daten unter /config oder /roms anfassen.
"""
import os
import sys
import tempfile
import importlib
import importlib.util
import threading

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


# --- Echter HTTP-Server -----------------------------------------------------------
# WARUM: Der Testclient oben umgeht die WSGI-Schicht. Alles, was dort entschieden wird —
# Komprimierung, Caching-Köpfe, Weiterleitungen — ist für ihn unsichtbar, ebenso wie
# gerendertes HTML und ausgeführtes JavaScript. Die Browser- und Vertragstests brauchen
# deshalb einen echten Server. Er steht hier und nicht in tests/e2e/, damit auch die
# Tests neben dem Browser (Vertrag, Auslieferung) ihn nutzen können.
#
# The test client above bypasses the WSGI layer, so compression, caching headers and
# redirects are invisible to it. Browser and contract tests need a real server; it lives
# here so the non-browser tests can use it too.

@pytest.fixture(scope="session")
def servermod():
    """Eine ZWEITE, eigenständige App-Instanz für alles, was über HTTP läuft.

    WARUM NICHT `appmod`: Die Browser- und Vertragstests müssen sich anmelden, und dafür
    legt `/api/setup` den ersten Benutzer an. Damit ist die Instanz eingerichtet — und
    `test_setup_and_login` in test_smoke.py, das eine jungfräuliche Instanz erwartet,
    schlägt fehl. Beim ersten Lauf hat das sechs fremde Tests umgeworfen, je nach
    Reihenfolge. Eine Prüfung, die andere Prüfungen abhängig von der Reihenfolge
    beeinflusst, ist schlimmer als keine.

    Die zweite Instanz bekommt ein eigenes Temp-Verzeichnis und wird als eigenes
    Modulobjekt geladen (`app_server`), damit die Modul-Globalen — allen voran der
    Datenbankpfad — getrennt bleiben.

    A second, independent app instance: the browser tests must create the first user to
    log in, which would leave the shared instance "already set up" and break tests that
    expect a virgin one. Separate temp dir, separate module object.
    """
    tmp = tempfile.mkdtemp(prefix="romseerr-server-")
    os.makedirs(os.path.join(tmp, "roms"), exist_ok=True)
    alt = {k: os.environ.get(k) for k in ("ROMSEERR_CONFIG", "ROMSEERR_ROMS")}
    os.environ["ROMSEERR_CONFIG"] = tmp
    os.environ["ROMSEERR_ROMS"] = os.path.join(tmp, "roms")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    spec = importlib.util.spec_from_file_location(
        "app_server", os.path.join(root, "app.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["app_server"] = mod
    spec.loader.exec_module(mod)
    mod.db_init()

    for k, v in alt.items():                 # Umgebung zurückdrehen, sonst erbt der
        if v is None:                        # nächste Import die falschen Pfade
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return mod


# Zugangsdaten der Wegwerf-Instanz. Sie stehen hier und nicht in den einzelnen Test-
# dateien, weil `/api/setup` nur EINMAL geht: Wer als Zweiter mit anderen Daten kommt,
# bekommt 400 beim Einrichten und danach 401 beim Anmelden. Genau so ist der Vertragstest
# im Verbund mit den Browsertests gescheitert — allein grün, gemeinsam rot.
#
# One set of credentials for the whole session: `/api/setup` works once, so a second
# fixture with different credentials gets 400 and then fails to log in.
TEST_USER = "romseerr-test"
TEST_PASS = "romseerr-test-passwort"


@pytest.fixture(scope="session")
def zugangsdaten():
    """Die Zugangsdaten der Wegwerf-Instanz, als Fixture — pytest vererbt sie an die
    conftest.py der Unterverzeichnisse, ein Import über Paketgrenzen hinweg nicht."""
    return TEST_USER, TEST_PASS


@pytest.fixture(scope="session")
def eingerichtet(live_server):
    """Legt einmalig den ersten Admin an und gibt die Basis-URL zurück."""
    import requests

    r = requests.post(f"{live_server}/api/setup",
                      json={"username": TEST_USER, "password": TEST_PASS}, timeout=10)
    assert r.status_code in (200, 400), f"Setup fehlgeschlagen: {r.status_code} {r.text[:200]}"
    return live_server


@pytest.fixture(scope="session")
def sitzung(eingerichtet):
    """Angemeldete Sitzungs-Cookies für Anfragen ohne Browser."""
    import requests

    s = requests.Session()
    r = s.post(f"{eingerichtet}/api/login",
               json={"username": TEST_USER, "password": TEST_PASS}, timeout=10)
    assert r.ok, f"Anmeldung fehlgeschlagen: {r.status_code} {r.text[:200]}"
    return dict(s.cookies)


@pytest.fixture(scope="session")
def live_server(servermod):
    """Startet die App auf einem freien Port und gibt die Basis-URL zurück.

    Port 0 heißt: das Betriebssystem sucht einen freien. Ein fester Port ließe parallele
    Läufe und eine lokal laufende Instanz gegeneinander laufen.

    Der Server läuft im selben Prozess wie pytest, damit `pytest-cov` den Code sieht, den
    die Anfragen auslösen — bei einem Subprozess bliebe die Abdeckung der Routen unsichtbar.
    """
    from werkzeug.serving import make_server

    srv = make_server("127.0.0.1", 0, servermod.app, threaded=True)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_port}"
    finally:
        srv.shutdown()
        thread.join(timeout=5)


@pytest.fixture(autouse=True)
def _suchspeicher_leeren(appmod):
    """Die Zwischenspeicher sind Modulzustand und ueberleben sonst den Test. (#726, #731)

    GEMESSEN BEIM FUND: Sieben bestehende `do_search`-Tests schlugen fehl, sobald der
    Zwischenspeicher da war — nicht weil sie kaputt sind, sondern weil der Treffer des
    vorigen Tests noch drinlag. Ein globaler Speicher, der zwischen Tests durchschlaegt,
    schlaegt auch zwischen Anfragen durch; deshalb wird er hier geleert und nicht in den
    einzelnen Tests.

    Jeder weitere Speicher gehoert in dieselbe Liste — er hat dasselbe Problem.
    """
    # #726 Suchquellen, #731 archive.org-Metadaten, #730 RomM-Treffer
    für_alle = ("SUCH_CACHE", "ARCHIVE_META", "ROMM_CACHE")
    for name in für_alle:
        try:
            getattr(appmod, name).clear()
        except AttributeError:
            pass
    yield
    for name in für_alle:
        try:
            getattr(appmod, name).clear()
        except AttributeError:
            pass
