"""Vertragstest: stimmt der Server mit seiner eigenen OpenAPI-Spezifikation überein?

WARUM: `app.py` nennt die Spezifikation ausdrücklich „einzige Quelle der Wahrheit", und
die Suite prüft bereits, dass jede Route DARIN STEHT. Was sie nicht prüft, ist die andere
Richtung: ob die Antworten dem entsprechen, was dort zugesagt wird. Eine Spezifikation,
die nie gegen den Server läuft, ist ein Versprechen, kein Vertrag.

WIE: Schemathesis liest die Spezifikation und erzeugt daraus mit Hypothesis Fälle je
Operation — auch die Randfälle, auf die von Hand niemand kommt. Geprüft wird gegen die
eingebauten Prüfungen: Antwortschema eingehalten, kein Server-Fehler, dokumentierter
Status-Code, korrekter Content-Type.

WARUM ANGEMELDET: Unangemeldet antworten alle 40 lesenden Endpunkte mit 401, und der Lauf
prüft dann nur noch den Türsteher — über die eigentlichen Antworten sagt er nichts. Der
Fund aus dem unangemeldeten Lauf (401 ist nirgends dokumentiert) steht als eigene Prüfung
unten, statt als Nebenwirkung im Rauschen unterzugehen.

WARUM NUR LESEND: Die Erzeugung ist zufällig. Ein `POST /api/setup` oder ein Löschen mit
erfundenen Daten würde den Zustand der Testinstanz unter den übrigen Tests verändern.
Deshalb laufen hier ausschließlich GET-Operationen; die schreibenden bleiben bei den
gezielten Tests in `test_smoke.py`, wo die Erwartung bekannt ist.

Contract testing: the app calls its OpenAPI spec the single source of truth, and the suite
already checks that every route appears in it. It never checked the other direction — that
responses match what is promised. Schemathesis generates cases per operation from the spec.
"""
import pytest

schemathesis = pytest.importorskip("schemathesis", reason="schemathesis nicht installiert")

@pytest.fixture(scope="session")
def schema(live_server):
    """Die Spezifikation, wie der laufende Server sie ausliefert.

    Bewusst über HTTP und nicht aus `docs/openapi.yaml`: Die Datei im Repo wird erzeugt
    und könnte veraltet sein. Geprüft werden soll, was der Server tatsächlich zusagt.
    """
    return schemathesis.openapi.from_url(f"{live_server}/api/openapi.json")


schema_lazy = schemathesis.pytest.from_fixture("schema")

# WELCHE PRÜFUNGEN — und warum nicht alle:
#
# Aktiv sind die vier, die eine Aussage über den VERTRAG treffen: Hält die Antwort ihr
# Schema ein, ist der Status-Code dokumentiert, stimmt der Content-Type, und fällt der
# Server nirgends um.
#
# Bewusst AUS, weil sie hier aus dem falschen Grund anschlagen — beides gemessen, nicht
# vermutet:
#
#   ignored_auth        Schlägt bei jedem Endpunkt an, weil die Sitzung als `cookies=`
#                       an Schemathesis vorbei gesetzt wird. Es entfernt daraufhin die
#                       ihm bekannte Authentifizierung (keine), sieht weiter 200 und
#                       meldet „Auth wird ignoriert". Ein Artefakt des Aufbaus.
#   negative_data_      Die Spezifikation beschreibt ihre Query-Parameter nicht. Damit
#   rejection /         ist jede Eingabe schemakonform, und die Prüfung „ungültige Daten
#   positive_data_      hätten abgelehnt werden müssen" hat nichts, woran sie sich
#   acceptance          festhalten könnte. Sie meldet 40x dasselbe.
#
# Die undokumentierten Parameter sind ein echter Mangel — er steht als eigener Befund
# fest, statt hier als Rauschen mitzulaufen. Sobald die Spezifikation ihre Parameter
# beschreibt, gehören diese Prüfungen wieder an.
#
# Only the four checks that say something about the contract are enabled. `ignored_auth`
# and the negative-data checks fire for reasons of the setup and of an underspecified
# schema, not because of a defect; a check that fires for the wrong reason gets muted
# within a week, and then the rule is worse off than with no test at all.
schemathesis.checks.load_all_checks()   # füllt die Registry; ohne das ist sie fast leer
VERTRAGS_PRUEFUNGEN = schemathesis.checks.CHECKS.get_by_names([
    "response_schema_conformance",
    "status_code_conformance",
    "content_type_conformance",
    "not_a_server_error",
])


# Bekannte Lücken der Spezifikation. Die Menge ist LEER, seit #328 behoben ist — sie
# bleibt als Ort stehen, an dem eine neue Lücke namentlich landet, statt als pauschales
# „Fehler erlaubt". Wer hier etwas einträgt, schuldet ein Issue dazu.
# Empty since #328; kept as the place where a new gap is named rather than waved through.
BEKANNT_LUECKENHAFT = set()


@schema_lazy.parametrize()
def test_antworten_halten_die_spezifikation_ein(case, sitzung):
    """Jede dokumentierte GET-Operation antwortet so, wie die Spezifikation es zusagt."""
    if case.method.upper() != "GET":
        pytest.skip("nur lesende Operationen — siehe Modul-Docstring")
    if case.path in BEKANNT_LUECKENHAFT:
        pytest.xfail(f"#328: Status-Codes von {case.path} sind nicht dokumentiert")
    case.call_and_validate(cookies=sitzung, checks=VERTRAGS_PRUEFUNGEN)


def test_401_ist_dokumentiert(live_server):
    """Wer unangemeldet an einen `/api/`-Endpunkt klopft, bekommt 401 — das gehört in die
    Spezifikation.

    `login_required` gibt für `/api/`-Pfade ausdrücklich 401 zurück; das steht in seinem
    eigenen Docstring. In der Spezifikation steht es bei keiner einzigen Operation. Wer
    einen Client daraus erzeugt, behandelt den häufigsten Fehlerfall überhaupt nicht.
    """
    import requests

    spez = requests.get(f"{live_server}/api/openapi.json", timeout=10).json()
    r = requests.get(f"{live_server}/api/jobs", timeout=10)
    assert r.status_code == 401, f"unerwartet: {r.status_code}"

    # WAS „GESCHUETZT" HEISST: Nicht jeder Pfad unter /api/ verlangt eine Anmeldung.
    # `/api/version`, `/api/openapi.json`, `/api/docs`, `/api/auth/status` und
    # `/api/logos` sind absichtlich oeffentlich und tragen deshalb ein LEERES
    # `security` — sie koennen gar kein 401 liefern. Die erste Fassung dieser Pruefung
    # zaehlte sie mit und meldete auch nach der Reparatur noch fuenf Verstoesse.
    # A path under /api/ is not automatically protected; the public ones carry an empty
    # `security` and cannot answer 401. The first version of this check counted them.
    geschuetzt = [
        pfad for pfad, ops in spez["paths"].items()
        if pfad.startswith("/api/")
        for m, op in ops.items()
        if m == "get" and op.get("security")          # leer = oeffentlich
        and "401" not in (op.get("responses") or {})
    ]
    assert not geschuetzt, (
        f"{len(geschuetzt)} GET-Operationen antworten mit 401, dokumentieren es aber nicht: "
        + ", ".join(geschuetzt[:8]) + (" …" if len(geschuetzt) > 8 else ""))
