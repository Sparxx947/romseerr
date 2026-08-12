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
import re
import sys
from pathlib import Path

import pytest

md = pytest.importorskip("importlib.metadata")
packaging_req = pytest.importorskip("packaging.requirements")

WURZEL = Path(__file__).resolve().parent.parent
REQ = WURZEL / "requirements.txt"

# Abschnittsmarken in requirements.txt. Der direkte Abschnitt ist das, was app.py selbst
# importiert; alles darunter ist die transitive Hülle und wird erzeugt, nicht gepflegt.
MARKE_DIREKT = "# --- direkt / direct ---"
MARKE_TRANSITIV = "# --- transitiv / transitive ---"

ZEILE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;#]+)\s*$")


def norm(name):
    """PEP 503: `Werkzeug`, `py_vapid` und `py-vapid` sind derselbe Name."""
    return re.sub(r"[-_.]+", "-", name).lower()


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


def _huelle(saat):
    """Transitive Hülle der installierten Verteilungen ab `saat` (normalisierte Namen).

    Extras bleiben draußen: `requests[socks]` zieht PySocks, das niemand hier benutzt.
    Marker werden mit `extra=""` ausgewertet, damit genau das passiert.
    """
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
            if r.marker is not None and not r.marker.evaluate({"extra": ""}):
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
