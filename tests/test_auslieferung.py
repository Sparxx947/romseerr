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


@pytest.mark.xfail(strict=True,
                   reason="#323: statische Dateien werden unkomprimiert ausgeliefert")
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
