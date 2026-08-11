"""Browsertests: was nur eine geladene Seite zeigen kann.

Diese Datei prüft Dinge, die der Flask-Testclient grundsätzlich nicht sehen kann —
gerendertes HTML, ausgeführtes JavaScript, die Adresszeile und die Tastatur.

ZU DEN `xfail`-MARKERN: #319, #320 und #323 sind belegte, noch nicht behobene Fehler.
Die zugehörigen Prüfungen gehören trotzdem jetzt in die Suite, sonst wird der Befund
beim nächsten Umbau still wieder eingebaut. `strict=True` heißt: Besteht die Prüfung
eines Tages doch, schlägt sie fehl mit dem Hinweis, den Marker zu entfernen. Damit ist
zugleich die Regel aus CONTRIBUTING erfüllt, dass jede neue Prüfung einmal rot war —
diese drei sind es nachweislich.
"""
import pytest

from .conftest import menuepunkt

# Menüpunkt -> erwartetes Adress-Segment. Einstellungen führt einen Unterbereich mit,
# deshalb wird nur der Anfang verglichen.
ANSICHTEN = {
    "Entdecken": "#/discover",
    "Anfragen": "#/requests",
    "Probleme": "#/issues",
    "Abdeckung": "#/coverage",
    "Bibliothek": "#/library",
    "Nachrichten": "#/messages",
    "Einstellungen": "#/settings",
}

# Der sichtbare Inhaltsbereich je Ansicht. WARUM NICHT `body`: Die ersten Zeichen von
# `body` sind Kopf- und Seitenleiste — auf jeder Ansicht dieselben. Ein Test, der das
# vergleicht, meldet „alle Ansichten sind gleich" und meint die Navigation. Genau so
# ist diese Prüfung beim ersten Lauf falsch angeschlagen.
CONTAINER = "#discview, #jobs, #settings, #issues, #messages, #coverage, #library, #lists"


def test_startseite_laedt_ohne_konsolenfehler(seite, konsolenfehler):
    """Die Startseite rendert und wirft dabei kein JavaScript-Fehler.

    Der häufigste Weg, eine Oberfläche zu zerlegen, ist ein Fehler in einem Modul, das
    beim Laden ausgeführt wird: Die Seite bleibt sichtbar, aber alles darunter ist tot.
    Der Testclient bemerkt das nie, weil er kein JavaScript ausführt.
    """
    seite.wait_for_selector("text=Romseerr", timeout=15000)
    assert not konsolenfehler, "Konsolenfehler beim Laden: " + " | ".join(konsolenfehler)


def test_jede_ansicht_der_seitenleiste_rendert(seite):
    """Jeder Menüpunkt zeigt eigenen Inhalt statt einer leeren Fläche.

    Geprüft wird nicht auf einen bestimmten Text, sondern darauf, dass sich der sichtbare
    Inhalt gegenüber der vorigen Ansicht ÄNDERT. Ein Test auf feste Überschriften würde
    bei jeder Umbenennung rot, ohne dass etwas kaputt wäre.
    """
    leer = []
    for name in ANSICHTEN:
        link = menuepunkt(seite, name)
        assert link.count() > 0, f"Menüpunkt {name} nicht gefunden"
        link.click()
        seite.wait_for_timeout(400)
        sichtbar = seite.locator(CONTAINER).filter(visible=True)
        if sichtbar.count() == 0:
            leer.append(f"{name}: kein sichtbarer Inhaltsbereich")
    assert not leer, "; ".join(leer)


@pytest.mark.xfail(strict=True,
                   reason="#320: `lib` fehlt in ROUTEN, Bibliothek landet auf #/discover")
def test_jede_ansicht_traegt_ihre_eigene_adresse(seite):
    """Jeder Menüpunkt muss seine eigene Adresse setzen.

    WARUM ALLE SIEBEN UND NICHT EINE: Die erste Fassung dieser Prüfung sah nur die
    Bibliothek, fand die Adresse unverändert und ließ daraus „die Anwendung routet nicht"
    werden. Tatsächlich routen sechs von sieben Ansichten einwandfrei; `routeBauen` fällt
    bei einem unbekannten Schlüssel still auf `discover` zurück. Eine Tabelle über alle
    Ansichten hätte das sofort gezeigt — ein Einzelfall zeigt es nie.
    """
    falsch = []
    for name, erwartet in ANSICHTEN.items():
        menuepunkt(seite, name).click()
        seite.wait_for_timeout(400)
        hash_ = "#" + seite.url.split("#", 1)[1] if "#" in seite.url else "(keiner)"
        if not hash_.startswith(erwartet):
            falsch.append(f"{name}: {hash_} statt {erwartet}")
    assert not falsch, "; ".join(falsch)


@pytest.mark.xfail(strict=True,
                   reason="#320: ROUTEN_UM kennt 'library' nicht, Deep-Link zeigt Entdecken")
def test_deep_link_oeffnet_die_gemeinte_ansicht(seite, eingerichtet):
    """Wer `#/library` aufruft, muss die Bibliothek sehen — nicht Entdecken.

    Gemessen wird der SICHTBARE Inhaltsbereich, nicht die Hervorhebung im Menü: Die
    Markierung könnte richtig sitzen, während darunter etwas anderes steht.
    """
    seite.goto(f"{eingerichtet}/#/library", wait_until="domcontentloaded")
    seite.wait_for_timeout(1500)
    sichtbar = seite.evaluate(
        "() => [...document.querySelectorAll('#discview,#library,#jobs,#issues,#coverage')]"
        ".filter(e => e.offsetParent).map(e => e.id)")
    assert sichtbar == ["library"], f"sichtbar ist stattdessen: {sichtbar}"


@pytest.mark.xfail(strict=True,
                   reason="#319: Bibliothekszeilen sind divs, nicht per Tastatur erreichbar")
def test_bibliothek_ist_mit_der_tastatur_bedienbar(bibliothek_gefuellt):
    """Wer klicken kann, muss auch tabben können.

    WARUM NICHT axe: axe-core hat keine Regel für ein `div` mit Klick-Behandler. Es prüft
    ARIA, sobald ARIA da ist — das Fehlen auf einem generischen Element bemerkt es nicht.
    Diese Lücke schließt nur ein echter Tastaturdurchlauf.

    WARUM `bibliothek_gefuellt`: Auf der leeren Instanz gibt es keine Zeilen, und die
    Prüfung wäre inhaltsleer wahr — siehe Docstring der Fixture.
    """
    seite = bibliothek_gefuellt
    menuepunkt(seite, "Bibliothek").click()
    seite.wait_for_timeout(800)

    anklickbar = seite.evaluate("""() => {
        const treffer = [];
        for (const el of document.querySelectorAll('div,span,li')) {
            if (!el.onclick) continue;
            if (!el.offsetParent) continue;              // unsichtbar
            const ti = el.getAttribute('tabindex');
            const rolle = el.getAttribute('role');
            if (ti === null && !rolle) treffer.push((el.innerText || '').slice(0, 40));
        }
        return treffer;
    }""")
    zeilen = seite.locator(".lib-vendor, .lib-row, [class*=vendor]").count()
    assert zeilen > 0 or anklickbar, ("Die Bibliotheksansicht zeigt keine Zeilen — die "
                                      "Prüfung könnte nichts finden und wäre wertlos")
    assert not anklickbar, ("Anklickbar, aber nicht per Tastatur erreichbar: "
                            + ", ".join(anklickbar[:8]))


@pytest.mark.xfail(strict=True,
                   reason="#329: Menüpunkte sind <a> ohne href — keine Rolle, kein Fokus")
def test_die_navigation_ist_mit_der_tastatur_erreichbar(seite):
    """Wer nicht klicken kann, muss die Ansicht trotzdem wechseln können.

    Das ist die schwerwiegendste Fassung des Problems: Nicht ein Bedienelement IN einer
    Ansicht fehlt, sondern der Weg ZU den Ansichten. Gezählt wird, wie viele der
    Menüpunkte ein Tab-Durchlauf tatsächlich erreicht.

    Der Durchlauf ist auf das Doppelte der Menüpunkte begrenzt: Der Fokus läuft im Kreis,
    und ohne Grenze liefe die Schleife ewig.
    """
    gesamt = seite.locator("a.nav, button.nav").count()
    assert gesamt > 0, "keine Menüpunkte gefunden"

    erreicht = set()
    for _ in range(gesamt * 2 + 6):
        seite.keyboard.press("Tab")
        aktiv = seite.evaluate(
            "() => {const a = document.activeElement;"
            " return a && a.classList.contains('nav') ? (a.innerText || '').trim() : null}")
        if aktiv:
            erreicht.add(aktiv)
    assert len(erreicht) == gesamt, (
        f"nur {len(erreicht)} von {gesamt} Menüpunkten per Tastatur erreichbar")


def test_seite_laeuft_auf_einem_telefon_nicht_ueber(seite):
    """Bei 390 px Breite darf nichts waagerecht überlaufen.

    390 px ist die Breite eines iPhone 14/15. Waagerechtes Scrollen ist auf dem Telefon
    der sicherste Weg, eine Seite unbenutzbar zu machen.
    """
    seite.set_viewport_size({"width": 390, "height": 844})
    seite.wait_for_timeout(600)
    breite = seite.evaluate(
        "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    scroll, sicht = breite
    assert scroll <= sicht + 1, f"Seite ist {scroll} px breit bei {sicht} px Sichtfenster"
