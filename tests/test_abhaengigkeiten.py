"""Was das Image mitbringt, muss dranstehen — und zwar genau. (#380)

WARUM DIESE TESTS: `/api/version` meldet `provenance: build` samt Commit. Der Commit ist
festgenagelt, die Abhängigkeiten waren es nicht (`flask>=3.0`, `requests>=2.31`,
`pywebpush>=1.14`). Zwei Bauten desselben Commits sind damit zwei verschiedene Programme,
und der Endpunkt behauptet das Gegenteil. Gemessen am 2026-08-12: 6 der 27 Pakete im
laufenden Image wurden in den 30 Tagen davor veröffentlicht, `pywebpush` sechs Tage vorher
— und über eine Hauptversionsgrenze hinweg (1.x → 2.4.0), die `>=1.14` erlaubt.

Der zweite Fund, den das Issue nicht nannte: `app.py` importiert SECHS fremde Pakete,
deklariert waren DREI. `werkzeug` steht unbedingt im Kopf der Datei, `cryptography` trägt
die Geheimnisverschlüsselung und das Zertifikat — beide kamen nur als Beifang von Flask
bzw. pywebpush ins Image. Fällt der Beifang weg, bricht der Import, ohne dass jemand
etwas geändert hätte.

EN: the image pins its commit but floated its dependencies; app.py imports six
distributions and declared three. These tests hold both halves.
"""
import ast
import importlib.util
import re
import sys
from pathlib import Path

import pytest

md = pytest.importorskip("importlib.metadata")
packaging_req = pytest.importorskip("packaging.requirements")

WURZEL = Path(__file__).resolve().parent.parent
REQ = WURZEL / "requirements.txt"
DOCKERFILE = WURZEL / "Dockerfile"
GENERATOR = WURZEL / "scripts" / "lock_requirements.py"

# Abschnittsmarken in requirements.txt. Der direkte Abschnitt ist das, was app.py selbst
# importiert; alles darunter ist die transitive Hülle und wird erzeugt, nicht gepflegt.
MARKE_DIREKT = "# --- direkt / direct ---"
MARKE_TRANSITIV = "# --- transitiv / transitive ---"

ZEILE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;#]+)\s*$")
BASIS = re.compile(r"^FROM\s+python:(\d+\.\d+)", re.MULTILINE)


def norm(name):
    """PEP 503: `Werkzeug`, `py_vapid` und `py-vapid` sind derselbe Name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _image_python():
    """Die Python-Fassung des Abbilds, aus dem Dockerfile gelesen — oder None. (#667)

    NICHT `sys.version_info`: requirements.txt beschreibt das Abbild, nicht den Rechner,
    auf dem pytest gerade läuft. Marker wie `python_version < "3.13"` fallen je Fassung
    anders aus, und dann misst der Test etwas anderes, als er behauptet.
    """
    treffer = BASIS.search(DOCKERFILE.read_text(encoding="utf-8"))
    return treffer.group(1) if treffer else None


def _image_umgebung():
    """Markerumgebung des Abbilds — None, wenn die Fassung nicht ablesbar ist. (#667)

    Gemessen am 2026-08-15 an der Hülle dieser Datei, jeweils gegen `dev`:

    | abweichende Umgebung | Wirkung auf die Hülle |
    |---|---|
    | Python 3.12 statt 3.14 | `typing-extensions` kommt dazu (aiohttp, aiosignal) |
    | PyPy statt CPython | `cffi` und `pycparser` fallen weg (cryptography) |
    | darwin/win32 statt linux | keine — heute fragt kein Marker der Hülle danach |

    `sys_platform` steht trotzdem drin: `python:*-slim` IST ein Linux-Abbild, und die
    Zeile kostet nichts, während der nächste Marker sie wieder brauchen kann.
    """
    version = _image_python()
    if version is None:
        return None
    return {
        # Extras bleiben draußen: `requests[socks]` zöge PySocks, das hier niemand nutzt.
        "extra": "",
        "python_version": version,
        # Die Patch-Stelle steht nicht im Tag `python:3.14-slim`. Kein Marker der Hülle
        # fragt danach — die drei `python_full_version`-Vergleiche stehen alle auf
        # `< '3.11'` und sind auf jeder Patch-Stelle von 3.14 gleich falsch.
        "python_full_version": f"{version}.0",
        "platform_python_implementation": "CPython",
        "sys_platform": "linux",
    }


def _umgebung_oder_skip():
    """Ohne die Fassung des Abbilds lieber ehrlich überspringen als falsch messen."""
    umgebung = _image_umgebung()
    if umgebung is None:
        pytest.skip(f"keine `FROM python:<fassung>`-Zeile in {DOCKERFILE.name} — "
                    "Marker nicht gegen das Abbild auswertbar")
    return umgebung


def _lies_requirements():
    """(alle, direkt, transitiv) — jeweils normalisierter Name -> Version."""
    alle, direkt, transitiv = {}, {}, {}
    abschnitt = None
    for roh in REQ.read_text(encoding="utf-8").splitlines():
        zeile = roh.strip()
        if zeile == MARKE_DIREKT:
            abschnitt = direkt
            continue
        if zeile == MARKE_TRANSITIV:
            abschnitt = transitiv
            continue
        if not zeile or zeile.startswith("#"):
            continue
        treffer = ZEILE.match(zeile)
        name = treffer.group(1) if treffer else zeile.split("=")[0].split(">")[0].split("<")[0]
        alle[norm(name)] = zeile
        if abschnitt is not None:
            abschnitt[norm(name)] = zeile
    return alle, direkt, transitiv


def _fremde_importe_von_app():
    """Top-Level-Importe aus app.py, die nicht aus der Standardbibliothek kommen."""
    baum = ast.parse((WURZEL / "app.py").read_text(encoding="utf-8"))
    module = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            module.update(a.name.split(".")[0] for a in knoten.names)
        elif isinstance(knoten, ast.ImportFrom) and knoten.level == 0 and knoten.module:
            module.add(knoten.module.split(".")[0])
    return {m for m in module if m not in sys.stdlib_module_names and m != "app"}


def _huelle(saat, umgebung=None):
    """Transitive Hülle der installierten Verteilungen ab `saat` (normalisierte Namen).

    Ohne `umgebung` wird gegen das Abbild gerechnet, nicht gegen den laufenden
    Interpreter (#667) — welche Marker das betrifft, steht bei `_image_umgebung()`.
    Extras bleiben draußen: `requests[socks]` zieht PySocks, das niemand hier benutzt;
    dafür trägt jede Umgebung `extra=""`.
    """
    if umgebung is None:
        umgebung = _umgebung_oder_skip()
    Requirement = packaging_req.Requirement
    gesehen, fehlend, stapel = set(), set(), list(saat)
    while stapel:
        name = stapel.pop()
        if norm(name) in gesehen:
            continue
        gesehen.add(norm(name))
        try:
            bedingungen = md.requires(name) or []
        except md.PackageNotFoundError:
            fehlend.add(norm(name))
            continue
        for roh in bedingungen:
            r = Requirement(roh)
            if r.marker is not None and not r.marker.evaluate(umgebung):
                continue
            stapel.append(r.name)
    return gesehen, fehlend


def test_jede_zeile_ist_exakt_gepinnt():
    """Kein `>=`, kein `~=`, keine offene Flanke — sonst driftet der Bau.

    Das ist die Zeile, an der #380 hängt: `pywebpush>=1.14` hat 2.4.0 hereingelassen.
    """
    lose = []
    for roh in REQ.read_text(encoding="utf-8").splitlines():
        zeile = roh.strip()
        if not zeile or zeile.startswith("#"):
            continue
        if not ZEILE.match(zeile):
            lose.append(zeile)
    assert not lose, "nicht exakt gepinnt: " + ", ".join(lose)


def test_alles_was_app_py_importiert_ist_direkt_deklariert():
    """Was `import` sagt, muss in requirements.txt stehen — nicht bloß mitkommen.

    `werkzeug`, `cryptography` und `py_vapid` kamen als Beifang von Flask bzw. pywebpush.
    Ein Upstream, der sie fallen lässt, bricht Romseerr ohne eine einzige eigene Änderung.
    """
    _, direkt, _ = _lies_requirements()
    paket_von_modul = md.packages_distributions()
    fehlt, unbekannt = [], []
    for modul in sorted(_fremde_importe_von_app()):
        verteilungen = paket_von_modul.get(modul)
        if not verteilungen:
            unbekannt.append(modul)
            continue
        if not any(norm(v) in direkt for v in verteilungen):
            fehlt.append(f"{modul} ({'/'.join(verteilungen)})")
    if unbekannt:
        pytest.skip("nicht installiert, Zuordnung nicht messbar: " + ", ".join(unbekannt))
    assert not fehlt, "importiert, aber nicht direkt deklariert: " + ", ".join(fehlt)


def test_transitive_huelle_ist_vollstaendig():
    """Jedes Paket, das mitinstalliert wird, steht auch drin.

    Ohne das bleibt die Hälfte des Images unbenannt: Jinja2, Werkzeug, cryptography und
    zwanzig weitere waren im Image und in keiner Datei. Der Dockerfile installiert mit
    `--no-deps`; diese Liste IST damit das Image, nicht nur eine Wunschliste.
    """
    alle, direkt, _ = _lies_requirements()
    if not direkt:
        pytest.fail(f"kein Abschnitt {MARKE_DIREKT!r} in requirements.txt")
    huelle, fehlend_installiert = _huelle(direkt)
    if fehlend_installiert:
        pytest.skip("nicht installiert, Hülle nicht messbar: " + ", ".join(sorted(fehlend_installiert)))
    fehlt = sorted(h for h in huelle if h not in alle)
    assert not fehlt, "wird mitinstalliert, steht aber nicht in requirements.txt: " + ", ".join(fehlt)


def test_keine_verwaisten_eintraege():
    """Umgekehrte Richtung: nichts steht drin, was niemand mehr braucht.

    Eine entfernte Abhängigkeit hinterlässt sonst einen Pin, den Dependabot weiter
    hochzieht — Arbeit und Bauzeit für ein Paket, das keiner mehr importiert.
    """
    alle, direkt, _ = _lies_requirements()
    huelle, fehlend_installiert = _huelle(direkt)
    if fehlend_installiert:
        pytest.skip("nicht installiert, Hülle nicht messbar: " + ", ".join(sorted(fehlend_installiert)))
    verwaist = sorted(a for a in alle if a not in huelle)
    assert not verwaist, "steht in requirements.txt, wird von niemandem gebraucht: " + ", ".join(verwaist)


def test_die_huelle_wird_gegen_das_abbild_gerechnet_nicht_gegen_den_laufenden_python():
    """Die Hülle darf nicht davon abhängen, womit pytest gerade startet. (#667)

    Der Docstring über dieser Datei sagt, die Liste SEI das Abbild. Das gilt nur, wenn
    auch die Marker gegen das Abbild ausgewertet werden. Gemessen am 2026-08-15 auf
    Python 3.12.13: `aiohttp` und `aiosignal` verlangen `typing_extensions` hinter
    `python_version < "3.13"`, die Hülle hatte damit 27 statt 26 Einträge, und
    `test_transitive_huelle_ist_vollstaendig` schlug fehl — auf unverändertem `dev`,
    während dieselbe Prüfung in der CI (3.14) grün war.

    WAS DARAN GEFÄHRLICH IST, ist nicht das rote Kreuz, sondern der naheliegende Schluss
    daraus: Wer `typing-extensions` in requirements.txt nachträgt, liefert dem
    3.14-Abbild ein Paket, das dort niemand braucht — und `test_keine_verwaisten_eintraege`
    meldet es in der Gegenrichtung.

    EN: the hull must not depend on the interpreter running pytest. On 3.12 two packages
    pull typing-extensions behind a version marker; the image (3.14) does not.
    """
    _, direkt, _ = _lies_requirements()
    abbild = _image_python()
    if abbild is None:
        pytest.skip(f"keine `FROM python:<fassung>`-Zeile in {DOCKERFILE.name}")

    # Von Hand aufgeschrieben statt `_image_umgebung()` aufgerufen: Der Test soll die
    # Erwartung nicht aus derselben Funktion beziehen, die er prüft.
    fuer_abbild = {"extra": "", "python_version": abbild, "python_full_version": f"{abbild}.0",
                   "platform_python_implementation": "CPython", "sys_platform": "linux"}
    erwartet, fehlend = _huelle(direkt, fuer_abbild)
    if fehlend:
        pytest.skip("nicht installiert, Hülle nicht messbar: " + ", ".join(sorted(fehlend)))

    # GEGENPROBE, sonst prüft der Test nichts: Auf einem Interpreter, unter dem ohnehin
    # jeder Marker gleich ausfällt, ist die Voreinstellung nicht zu unterscheiden — dann
    # das ehrlich sagen, statt grün zu melden. In der CI (3.14) ist das der Normalfall.
    laufend, _ = _huelle(direkt, {"extra": ""})
    hier = f"{sys.version_info.major}.{sys.version_info.minor}"
    if laufend == erwartet:
        pytest.skip(f"auf Python {hier} entscheidet kein Marker dieser Hülle anders als auf "
                    f"{abbild} — der Unterschied ist hier nicht messbar")

    voreingestellt, _ = _huelle(direkt)
    assert voreingestellt == erwartet, (
        f"die Hülle wird gegen den laufenden Interpreter ({hier}) gerechnet statt gegen das "
        f"Abbild ({abbild}); Unterschied: " + ", ".join(sorted(voreingestellt ^ erwartet)))


def test_der_generator_zielt_auf_die_python_fassung_des_abbilds():
    """`scripts/lock_requirements.py` muss für dieselbe Fassung auflösen wie der Bau. (#667)

    Die Zahl stand dort als eigene Konstante ein zweites Mal — und war stehengeblieben:
    `ZIEL_PYTHON = "3.12"` samt Kommentar „`FROM python:3.12-slim`", während der
    Dockerfile längst auf 3.14 stand. Gemessen am 2026-08-15 mit `uv pip compile` über
    denselben direkten Abschnitt: 27 Pakete für 3.12, 26 für 3.14, Unterschied
    `typing-extensions`. Ein Lauf des Generators hätte es also hineingeschrieben.

    Das ist derselbe Riss wie in #588, nur eine Datei weiter — dort trennten sich
    Dockerfile und Workflows, hier Dockerfile und Generator. Die Prüfung von damals
    (`test_ci_tests_the_python_the_image_runs`) sieht nur `.github/workflows`.

    EN: the lock script must resolve for the image's Python. Its hard-coded copy of the
    version had gone stale (3.12 vs 3.14) and would have written typing-extensions in.
    """
    abbild = _image_python()
    if abbild is None:
        pytest.skip(f"keine `FROM python:<fassung>`-Zeile in {DOCKERFILE.name}")
    if not GENERATOR.exists():
        pytest.skip(f"{GENERATOR.name} nicht vorhanden")
    lade = importlib.util.spec_from_file_location("lock_requirements", GENERATOR)
    modul = importlib.util.module_from_spec(lade)
    lade.loader.exec_module(modul)
    assert modul.ziel_python() == abbild, (
        f"der Generator löst für Python {modul.ziel_python()} auf, das Abbild fährt "
        f"{abbild} — die Hülle wäre eine andere")


def test_dockerfile_loest_nicht_selbst_auf():
    """`pip install --no-deps` + `pip check` — sonst ist die Liste bloß ein Vorschlag.

    Ohne `--no-deps` holt pip fehlende Abhängigkeiten in der neuesten Fassung nach, und
    die Datei sagt wieder nicht, was drin ist. `pip check` macht eine unvollständige
    Liste beim Bau laut, statt sie erst zur Laufzeit auffliegen zu lassen.
    """
    text = (WURZEL / "Dockerfile").read_text(encoding="utf-8")
    installationen = [z.strip() for z in text.splitlines() if "pip install" in z]
    assert installationen, "kein `pip install` im Dockerfile gefunden"
    ohne = [z for z in installationen if "--no-deps" not in z]
    assert not ohne, "installiert mit Auflösung statt aus der Liste: " + " | ".join(ohne)
    assert "pip check" in text, "kein `pip check` im Dockerfile — unvollständige Liste bliebe still"
