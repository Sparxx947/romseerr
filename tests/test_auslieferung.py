"""Wie die Oberfläche über die Leitung geht: Komprimierung und Caching.

WARUM HIER UND NICHT MIT LIGHTHOUSE: Für genau diese zwei Fragen braucht es keine
Node-Werkzeugkette. Lighthouse ist als eigener CI-Schritt vorgesehen (#326), wo es
Budgets über die Zeit hält — die Grundtatsachen prüft die Suite selbst, in Millisekunden.

Beide Prüfungen laufen gegen den echten Server, nicht gegen den Testclient: Ob eine
Antwort komprimiert ausgeliefert wird, entscheidet die WSGI-Schicht, und die umgeht der
Testclient.
"""
import pytest

requests = pytest.importorskip("requests")

# Ab dieser Größe lohnt Komprimierung. Darunter kostet der Kopf mehr, als der Inhalt spart.
MINDESTGROESSE = 1024


def _asset_pfade(basis):
    """Die gehashten Asset-Pfade, so wie die Login-Seite sie einbindet."""
    import re
    html = requests.get(f"{basis}/login", timeout=10).text
    return re.findall(r'(?:href|src)="(/assets/[^"]+)"', html)


def test_assets_werden_lange_zwischengespeichert(live_server):
    """Inhaltsgehashte Assets müssen `immutable` tragen.

    Das ist der Teil, der heute schon richtig ist — und deshalb festgehalten gehört:
    Wer den Hash aus dem Pfad nimmt, macht daraus stillschweigend einen Fehler, bei dem
    Clients eine alte Fassung ein Jahr lang behalten.
    """
    pfade = _asset_pfade(live_server)
    assert pfade, "keine gehashten Assets in der Login-Seite gefunden"
    for p in pfade:
        cc = requests.get(f"{live_server}{p}", timeout=10).headers.get("Cache-Control", "")
        assert "immutable" in cc and "max-age" in cc, f"{p}: Cache-Control ist {cc!r}"


def test_grosse_textdateien_werden_komprimiert(live_server):
    """Wer gzip anbietet, soll gzip bekommen.

    Das Hauptbündel ist rund 219 KB; gzip spart daran etwa 69 %. Auf dem LAN fällt das
    nicht auf — über einen Reverse Proxy auf ein Telefon mit Mobilfunk schon.
    """
    ungepackt = []
    for p in _asset_pfade(live_server):
        r = requests.get(f"{live_server}{p}", headers={"Accept-Encoding": "gzip, deflate"},
                         timeout=10)
        roh = int(r.headers.get("Content-Length") or len(r.content))
        if roh < MINDESTGROESSE:
            continue
        if not r.headers.get("Content-Encoding"):
            ungepackt.append(f"{p} ({roh} Bytes)")
    assert not ungepackt, "unkomprimiert ausgeliefert: " + ", ".join(ungepackt)


def test_every_served_asset_type_has_a_real_content_type(live_server, servermod):
    """Keine ausgelieferte Datei faellt auf `application/octet-stream` zurueck. (#350)

    WARUM DAS MEHR IST ALS EINE FORMALIE: Der Inhaltstyp entscheidet auch ueber die
    Vorkomprimierung — sie packt nur Text. Eine Datei ohne Eintrag in `ASSET_MIME` faellt
    also gleich doppelt durch: falscher Typ UND unkomprimiert.

    Gemessener Fall: Die Sprachdateien gingen mit 17.106 statt 6.704 Bytes ueber die
    Leitung, weil `.json` fehlte. Aufgefallen ist es erst beim Nachmessen am laufenden
    Dienst — im Pull Request stand da bereits, es sei abgedeckt.

    The content type also decides pre-compression, which only packs text. A missing entry
    costs twice: wrong type and no compression.
    """
    ohne = sorted({rel for rel, a in servermod._ASSETS.items()
                   if a["mime"] == "application/octet-stream"})
    assert not ohne, ("Dateien ohne eigenen Inhaltstyp (und damit ohne Komprimierung): "
                      + ", ".join(ohne[:8]) + (" …" if len(ohne) > 8 else ""))


def test_the_language_files_are_compressed(live_server, servermod):
    """Die Sprachdateien werden gepackt ausgeliefert. (#350)

    Sie sind der Grund, warum es die Aufteilung gibt — sie ungepackt zu schicken haette
    einen guten Teil des Gewinns wieder aufgezehrt.
    """
    sprachen = [rel for rel in servermod._ASSETS if rel.startswith("i18n/")]
    assert len(sprachen) == 5, f"unerwartet: {sprachen}"
    for rel in sprachen:
        a = servermod._ASSETS[rel]
        assert a["gz"], f"{rel} wird nicht komprimiert"
        assert len(a["gz"]) < len(a["body"]) * 0.6, \
            f"{rel}: nur {100 - 100 * len(a['gz']) // len(a['body'])} % gespart"
