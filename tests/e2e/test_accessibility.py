"""Barrierefreiheit: axe-core über die Ansichten, plus was axe nicht kann.

WAS AXE LEISTET: Kontrast, fehlende Namen an Knöpfen und Verweisen, kaputtes ARIA,
Dokumentstruktur. Das ist viel, und es kostet fast nichts, wenn ohnehin ein Browser läuft.

WAS AXE NICHT LEISTET — nachgeprüft, nicht vermutet: Es gibt in der Regelliste **keine**
Regel, die ein `div` oder `span` mit Klick-Behandler bemängelt. Die nächstliegenden
(`nested-interactive`, `button-name`, `aria-allowed-role`) schlagen bei einem nackten
`div` mit `onclick` nicht an. Mehrere verbreitete Anleitungen behaupten das Gegenteil.
Ein reiner axe-Lauf hätte die Bibliotheksansicht aus #319 als sauber gemeldet.
Deshalb liegt die Tastaturprüfung in `test_browser.py` und nicht hier.

SCHWELLE: Geprüft wird auf `critical` und `serious`. `moderate`/`minor` melden auch
Stilfragen; eine Prüfung, die aus schwachem Grund anschlägt, wird abgeschaltet — und dann
steht die Regel schlechter da als ohne Test.
"""
import pytest

from .conftest import menuepunkt

axe_mod = pytest.importorskip("axe_playwright_python.sync_playwright",
                              reason="axe-playwright-python nicht installiert")
Axe = axe_mod.Axe

SCHWERE = {"critical", "serious"}


def _verstoesse(ergebnis):
    """Nur die schweren Verstöße, als lesbare Zeilen."""
    zeilen = []
    for v in ergebnis.response.get("violations", []):
        if v.get("impact") not in SCHWERE:
            continue
        knoten = len(v.get("nodes", []))
        zeilen.append(f"{v['impact']}: {v['id']} — {v['help']} ({knoten}x)")
    return zeilen


def test_startseite_ohne_schwere_verstoesse(seite):
    """Die Startseite trägt keine kritischen oder schweren axe-Verstöße."""
    ergebnis = Axe().run(seite)
    schwer = _verstoesse(ergebnis)
    assert not schwer, "axe auf Entdecken:\n  " + "\n  ".join(schwer)


def test_jeder_bedienbare_teil_hat_einen_namen(seite):
    """Knöpfe und Verweise brauchen einen vorlesbaren Namen.

    Ein Menüpunkt, der nur aus einem Emoji besteht, wird als dieses Zeichen vorgelesen.
    Genau das steht in der Seitenleiste zweimal.
    """
    ohne = seite.evaluate("""() => {
        const treffer = [];
        for (const el of document.querySelectorAll('a,button')) {
            if (!el.offsetParent) continue;
            const name = (el.getAttribute('aria-label') || el.innerText || '').trim();
            const sichtbar = name.replace(/[\\p{Emoji_Presentation}\\p{Extended_Pictographic}\\s]/gu, '');
            if (!sichtbar) treffer.push(el.outerHTML.slice(0, 80));
        }
        return treffer;
    }""")
    assert not ohne, "Ohne vorlesbaren Namen:\n  " + "\n  ".join(ohne)


@pytest.mark.parametrize("ansicht", ["Anfragen", "Probleme", "Abdeckung", "Bibliothek"])
def test_weitere_ansichten_ohne_schwere_verstoesse(seite, ansicht):
    """Dieselbe Prüfung auf den übrigen Ansichten.

    Die Bibliothek wurde von Hand geprüft; die anderen drei nie. Genau dafür ist der
    parametrisierte Lauf da — er kostet je Ansicht Sekunden.
    """
    link = menuepunkt(seite, ansicht)
    assert link.count() > 0, f"Menüpunkt {ansicht} nicht gefunden"
    link.click()
    seite.wait_for_timeout(700)
    schwer = _verstoesse(Axe().run(seite))
    assert not schwer, f"axe auf {ansicht}:\n  " + "\n  ".join(schwer)
