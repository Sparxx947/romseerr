"""Browsertests: was nur eine geladene Seite zeigen kann.

Diese Datei prüft Dinge, die der Flask-Testclient grundsätzlich nicht sehen kann —
gerendertes HTML, ausgeführtes JavaScript, die Adresszeile und die Tastatur.

ZU DEN `xfail`-MARKERN: Hier steht aktuell keiner mehr. #319, #320, #329 und #330 waren
belegte Fehler; ihre Marker sind entfernt, nachdem die jeweilige Reparatur sie als
XPASS(strict) hat anschlagen lassen. Genau dafuer ist `strict` da. Offen und weiterhin
markiert sind #323 (Komprimierung) und #328 (Spezifikation) in den anderen Dateien.
Die zugehörigen Prüfungen gehören trotzdem jetzt in die Suite, sonst wird der Befund
beim nächsten Umbau still wieder eingebaut. `strict=True` heißt: Besteht die Prüfung
eines Tages doch, schlägt sie fehl mit dem Hinweis, den Marker zu entfernen. Damit ist
zugleich die Regel aus CONTRIBUTING erfüllt, dass jede neue Prüfung einmal rot war —
diese drei sind es nachweislich.
"""
import os
import re

import pytest

from hilfen import REPO
from . import bildmessung
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


def test_der_bestaetigungsdialog_ist_bedienbar_und_bricht_sicher_ab(seite, servermod, anfrage_vorhanden):
    """Solange hier `confirm()` stand, war dieser Pfad UEBERHAUPT NICHT pruefbar: Ein nativer
    Dialog friert die Seite fuer den Testtreiber ein. Genau deshalb hatten mehrere
    zerstoerende Wege gar keine Abdeckung. (#641)

    Geprueft wird, was der native Dialog richtig machte und was leicht verloren geht:
    Der Fokus liegt beim ABBRECHEN, nicht bei der zerstoerenden Wahl — sonst loescht die
    Eingabetaste. Und Escape bricht ab, ohne dass etwas passiert.
    """
    # Der Loeschknopf erscheint nur bei done/error/denied — die Fixture legt `pending` an.
    # Ohne diesen Schritt uebersprang sich der Test selbst, und ein uebersprungener Test
    # sagt nichts (dieselbe Falle, die `anfrage_vorhanden` ueberhaupt noetig machte).
    servermod.set_state(anfrage_vorhanden["id"], state="done", msg="Testlauf")
    seite.get_by_text("Anfragen", exact=False).first.click()
    seite.wait_for_timeout(900)
    knopf = seite.locator("#jobs button").filter(has_text="🗑").first
    assert knopf.count() > 0, "keine loeschbare Anfrage — die Vorbereitung greift nicht"
    knopf.click()
    dlg = seite.locator("dialog#frage")
    dlg.wait_for(state="visible", timeout=4000)
    # Der Fokus darf NICHT auf der zerstoerenden Wahl liegen. Geprueft wird die KLASSE,
    # nicht der Text: Bei zwei Wahlen heisst die zerstoerende schlicht „OK", und ein Test
    # auf das Wort „loeschen" ginge daran vorbei — genau so blieb er bei der Gegenprobe
    # gruen, obwohl der Fokus auf dem falschen Knopf lag.
    fokus = seite.evaluate("document.activeElement.className || ''")
    assert "gefahr" not in fokus, f"Fokus steht auf der zerstoerenden Wahl (class={fokus!r})"
    assert seite.evaluate("document.activeElement.closest('dialog#frage')!==null"), \
        "der Fokus liegt gar nicht im Dialog"
    seite.keyboard.press("Escape")
    seite.wait_for_timeout(500)
    assert not dlg.is_visible(), "Escape schliesst den Dialog nicht"


def test_die_aurora_buehne_erscheint_nur_beim_entdecken(seite):
    """Die Buehne stand ausserhalb von `#discview` und wurde deshalb von `zeige()` nie
    ausgeblendet — in Anfragen, Problemen, Abdeckung und Einstellungen stand eine halbe
    Bildschirmhoehe „Finde ein Spiel" ueber Inhalten, die mit Suchen nichts zu tun haben.

    WARUM DER FRUEHERE TEST DAS NICHT FAND: Er prueft, DASS das Design greift, und ich habe
    beim Bauen nur die Entdecken-Ansicht gerendert. Ein Design ist nicht ein Bildschirm —
    dieser Test geht deshalb ALLE Ansichten durch. (#636)"""
    seite.evaluate("document.documentElement.dataset.design='aurora'")
    seite.wait_for_timeout(400)
    b = seite.locator("#buehne")
    assert b.is_visible(), "die Buehne fehlt schon beim Entdecken"
    for name in ("Anfragen", "Probleme", "Abdeckung", "Bibliothek", "Nachrichten"):
        menuepunkt(seite, name).click()
        seite.wait_for_timeout(350)
        assert not b.is_visible(), f"die Buehne steht noch in der Ansicht {name}"
    menuepunkt(seite, "Entdecken").click()
    seite.wait_for_timeout(350)
    assert b.is_visible(), "zurueck beim Entdecken fehlt die Buehne"


def test_ein_treffer_ohne_plattform_wird_benannt_statt_fragezeichen(seite):
    """Ohne Slug stand in der Karte ein blosses `?` — der Titel liess sich anfordern, ohne
    dass jemand sah, dass er mangels Zielordner in `.unsortiert` landet. (#621)

    WARUM IM BROWSER UND NICHT IM UNIT-TEST: Der Unit-Test liest die Datei und prueft, dass
    der Schluessel darin vorkommt. Ob `plattformMarke()` ihn zur Laufzeit auch AUFLOEST —
    mit geladener Sprachtabelle und ausgefuehrtem JavaScript — sieht nur eine echte Seite.
    Genau dort sassen sechs Fehler in einem gruenen Build (#319-#324).
    """
    seite.wait_for_selector("text=Romseerr", timeout=15000)
    ohne = seite.evaluate("plattformMarke('')")
    assert "?" not in ohne, f"die Karte zeigt weiterhin ein Fragezeichen: {ohne}"
    assert "unbekannt" in ohne.lower() or "unknown" in ohne.lower(), ohne
    # Die Folge muss im Hinweis stehen, sonst ist die Kennzeichnung nur ein Etikett.
    assert "unsortiert" in ohne.lower(), f"der Hinweis nennt den Ordner nicht: {ohne}"
    # Gegenprobe: ein bekannter Slug wird unveraendert dargestellt.
    mit = seite.evaluate("plattformMarke('snes')")
    assert "unbekannt" not in mit.lower() and "unknown" not in mit.lower(), mit


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
    zeilen = seite.locator("button.libkopf, button.libzeile, .job").count()
    assert zeilen > 0 or anklickbar, ("Die Bibliotheksansicht zeigt keine Zeilen — die "
                                      "Prüfung könnte nichts finden und wäre wertlos")
    assert not anklickbar, ("Anklickbar, aber nicht per Tastatur erreichbar: "
                            + ", ".join(anklickbar[:8]))


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


def test_der_zurueck_knopf_kehrt_zur_vorigen_ansicht(seite):
    """Zurück muss zur vorigen Ansicht führen, nicht aus der Anwendung heraus. (#320)

    Das war das eigentliche Versprechen hinter dem Routing-Fehler: Solange die Bibliothek
    keine eigene Adresse setzte, gab es fuer sie keinen History-Eintrag — der Zurueck-Knopf
    sprang an ihr vorbei.

    Geprueft wird zusaetzlich, dass ein Klick GENAU EINEN Eintrag erzeugt: Der `href` und
    `show()` koennten sonst beide schreiben, und Zurueck braeuchte zwei Druecke.
    """
    menuepunkt(seite, "Probleme").click()
    seite.wait_for_timeout(400)
    menuepunkt(seite, "Bibliothek").click()
    seite.wait_for_timeout(400)
    assert seite.url.endswith("#/library"), f"unerwartet: {seite.url}"

    seite.go_back()
    seite.wait_for_timeout(600)
    assert seite.url.endswith("#/issues"), (
        f"nach einmal Zurueck: {seite.url} — erzeugt ein Klick zwei History-Eintraege?")


def test_a_non_german_language_is_fetched_and_applied(seite, eingerichtet):
    """Eine andere Sprache wird nachgeladen und angewendet — ohne Zwischenstand. (#350)

    DAS IST DER RISKANTE PFAD. Deutsch liegt im Skript und braucht keinen Abruf; alles
    andere wird geholt. Kommt die Datei zu spaet, zeichnet die Seite erst deutsch und
    springt dann um — genau das, was der Umbau vermeiden soll.

    Geprueft wird gegen einen Text, den es NUR auf Englisch gibt, damit der Test nicht
    versehentlich die deutsche Rueckfallebene bestaetigt.

    German is inlined and needs no fetch; every other language is loaded. If the file
    arrives late the page renders in German and then jumps.
    """
    # Ueber `setLang` — den Weg, den auch das Sprachmenue nimmt. Ein Setzen von
    # `localStorage` allein genuegt NICHT: `loadAuth()` holt die Sprache aus dem Profil
    # und ueberschreibt sie beim Laden wieder. Genau darauf ist dieser Test zuerst
    # hereingefallen.
    seite.evaluate("setLang('en')")
    seite.wait_for_timeout(1200)

    zustand = seite.evaluate("""() => ({
        lang: LANG,
        geladen: Object.keys(I18N),
        entdecken: t('nav_discover'),
        bibliothek: t('nav_library')
    })""")
    assert zustand["lang"] == "en"
    assert "en" in zustand["geladen"], "die englische Tabelle wurde nicht geholt"
    assert zustand["entdecken"] == "Discover", f"unerwartet: {zustand['entdecken']!r}"
    assert zustand["bibliothek"] == "Library"

    # Und im DOM, nicht nur in der Tabelle: `applyI18n` muss NACH dem Laden gelaufen sein.
    sichtbar = seite.locator("a.nav").first.inner_text()
    assert "Discover" in sichtbar, f"die Seite zeigt noch: {sichtbar!r}"

    seite.evaluate("localStorage.setItem('lang','de')")


def test_eine_anfrage_fuehrt_zur_karte_des_spiels(seite, anfrage_vorhanden):
    """Ein Klick auf den Titel einer Anfrage öffnet die Detailansicht. (#390)

    WARUM IM BROWSER: Die Prüfungen daneben lesen den Quelltext — sie sehen, dass eine
    Klickbindung dasteht, nicht, dass sie greift. Genau diese Lücke hat hier schon einmal
    gekostet: Eine Seitenleiste war mit der Maus bedienbar und mit der Tastatur nicht, und
    kein Test bemerkte es.

    WARUM DIE SUCHE FEST VERDRAHTET IST (#459): Dieser Test hing an zwei Dingen, die er gar
    nicht prüfen will — dass Archive.org erreichbar ist, und dass das Auffrischen nicht
    dazwischenfunkt. In der CI gibt es kein Netz nach draußen, also fand die Suche nie eine
    Karte, und übrig blieb die Kurzmeldung, die ein Auffrischen wegwischen konnte. Das war
    keine Flatterhaftigkeit, sondern eine falsch gestellte Frage: Geprüft werden soll
    „Klick öffnet die Karte", nicht „das Internet ist da".

    EN: the test used to depend on Archive.org being reachable and on the refresh not
    interfering — neither of which it means to test. `/api/search` is stubbed to one
    matching hit, so the question is only whether the click opens the card.
    """
    seite.route("**/api/search*", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='[{"title":"Super Mario World","platform":"snes","platform_slug":"snes",'
             '"source":"archive","size":524288,"ref":"probe","cover":"","gkey":"smw"}]'))
    seite.goto(seite.url.split("#")[0] + "#/requests")
    seite.wait_for_timeout(600)
    titel = seite.locator(".jobt")
    assert titel.count() > 0, ("keine Anfragezeile sichtbar — die Fixture hat nichts "
                               "angelegt, der Test waere sonst inhaltsleer")
    assert titel.first.is_visible()
    # Der Zeiger sagt dem Nutzer, dass hier etwas passiert.
    assert titel.first.evaluate("e=>getComputedStyle(e).cursor") == "pointer"
    titel.first.click()
    seite.wait_for_timeout(1500)
    # Die Suche liefert hier garantiert einen Treffer, also MUSS die Karte aufgehen. Das
    # frühere „Karte ODER Meldung" verwässerte genau die Frage, um die es geht.
    modal = seite.locator("#modal")
    assert modal.count() and modal.is_visible(), (
        "der Klick hat die Karte nicht geöffnet, obwohl die Suche einen passenden Treffer "
        "liefert — Meldung in der Zeile: "
        + (seite.locator(".jobmsg").first.inner_text().strip() or "(keine)"))
    assert "Super Mario World" in modal.inner_text(), \
        "die Karte zeigt einen anderen Titel als den angeklickten"


def test_the_requests_list_is_not_rebuilt_when_nothing_changed(seite, anfrage_vorhanden):
    """Eine unveraenderte Anfragenliste wird NICHT neu gezeichnet. (#419)

    WOZU: Die Ansicht frischt alle 4 Sekunden auf und ersetzte dabei `#jobs` vollstaendig —
    auch wenn sich nichts bewegt hat. Jede Ersetzung ist ein Fenster, in dem ein Klick ins
    Leere geht: Die Zeile wird gerade abgehaengt, `onclick` laeuft nicht, und es passiert
    NICHTS. Kein Fehler, keine Meldung. Zweimal klicken half.

    WARUM DIESE PRUEFUNG UND NICHT DER KLICKTEST: Der Klicktest daneben faellt nur, wenn der
    Klick zufaellig ins Fenster faellt — unter Last etwa jeder dritte Lauf, auf einer ruhigen
    Maschine keiner von zwoelf. Gemessen: 0 von 12 rot mit Fix UND 0 von 12 ohne. Eine
    Pruefung, die den Fehler nur manchmal sieht, beweist seine Abwesenheit nie.

    Deshalb wird hier die EIGENSCHAFT geprueft statt der Symptomfall: Bleibt der Knoten
    derselbe, gibt es das Fenster nicht mehr. Das ist deterministisch — der Test wartet
    laenger als einen Auffrischtakt und sieht nach, ob dasselbe DOM-Element noch dasteht.

    EN: the view replaced the whole list every 4 s even when nothing changed, and a click
    landing in that window did nothing at all. The click test only catches it under load,
    so this checks the property instead: the same node must survive a refresh cycle.
    """
    seite.goto(seite.url.split("#")[0] + "#/requests")
    seite.wait_for_timeout(600)
    zeile = seite.locator(".jobt").first
    assert zeile.count() > 0, "keine Anfragezeile — die Fixture hat nichts angelegt"

    # Den Knoten markieren. Ueberlebt die Markierung, ist es derselbe Knoten; wird die
    # Liste neu gebaut, ist sie weg — `innerHTML=''` nimmt jedes Attribut mit.
    zeile.evaluate("e => e.dataset.probe = 'x'")

    # Laenger warten als EIN Auffrischtakt (4 s), damit mindestens einer stattgefunden hat.
    seite.wait_for_timeout(5200)

    ueberlebt = seite.evaluate(
        "() => document.querySelectorAll('.jobt[data-probe=\"x\"]').length")
    assert ueberlebt == 1, (
        "die Anfragenliste wurde neu aufgebaut, obwohl sich nichts geaendert hat — "
        "in genau diesem Moment geht ein Klick des Nutzers verloren")


def test_the_requests_list_still_refreshes_when_something_changed(seite, servermod,
                                                                  anfrage_vorhanden):
    """Und trotzdem kommt eine neue Anfrage von selbst an. (#419)

    DIE HAELFTE, OHNE DIE DER FIX WERTLOS WAERE: Man kann das Fenster aus #419 auch
    schliessen, indem man gar nicht mehr auffrischt — die Pruefung daneben waere dann gruen
    und die Ansicht kaputt. Sie zeigte einen Stand von vor zehn Minuten und niemand saehe
    es, weil nichts fehlschlaegt.

    Deshalb hier die Gegenrichtung: eine Anfrage wird server-seitig angelegt, ohne dass die
    Seite irgendetwas davon erfaehrt, und muss von selbst erscheinen.

    EN: the other half. The window could also be closed by never refreshing at all, which
    would leave this green and the view stale. A job created server-side must still show up.
    """
    seite.goto(seite.url.split("#")[0] + "#/requests")
    seite.wait_for_timeout(600)
    vorher = seite.locator(".jobt").count()
    assert vorher > 0, "keine Anfragezeile — die Fixture hat nichts angelegt"

    servermod.new_job({"title": "Chrono Trigger", "source": "archive",
                       "ref": "probe-419", "platform_slug": "snes", "size": 1},
                      user="admin", approved=False)

    # Kein reload, kein Klick: Die Ansicht muss das von allein merken.
    seite.wait_for_timeout(5200)
    nachher = seite.locator(".jobt").count()
    assert nachher == vorher + 1, (
        f"{vorher} Zeilen vorher, {nachher} nachher — eine neue Anfrage ist nicht von "
        "selbst angekommen; die Ansicht friert ein statt zu aktualisieren")
    assert seite.locator(".jobt", has_text="Chrono Trigger").count() == 1


def test_switching_language_redraws_the_requests_list(seite, anfrage_vorhanden):
    """Ein Sprachwechsel erreicht auch die Anfragenliste. (#419)

    DIE REGRESSION, DIE DER FIX FAST GEBAUT HAETTE: `setLang()` zeichnet die Ansicht neu,
    indem es `loadJobs()` aufruft. Der erste Entwurf von #419 verglich nur die DATEN — und
    die aendern sich beim Sprachwechsel nicht. Die Liste waere als einzige Ansicht der
    Oberflaeche in der alten Sprache stehen geblieben, ohne Fehler und ohne Hinweis.

    Gefunden hat das kein Test, sondern das Nachlesen, wer `loadJobs` sonst noch ruft. Das
    ist die Lehre: Wer eine Auffrischung an eine Bedingung knuepft, muss JEDEN Aufrufer
    durchgehen — jeder von ihnen hatte einen Grund.

    EN: setLang() re-renders through loadJobs(). Comparing only the data would have frozen
    this one view in the previous language, silently.
    """
    seite.goto(seite.url.split("#")[0] + "#/requests")
    seite.wait_for_timeout(600)
    assert seite.locator(".jobt").count() > 0, "keine Anfragezeile — Fixture leer"

    def gruppenleiste():
        return seite.locator("#jobs .ssub").first.inner_text()

    vorher = gruppenleiste()
    seite.evaluate("setLang('en')")
    seite.wait_for_timeout(900)
    nachher = gruppenleiste()
    assert nachher != vorher, (
        f"die Anfragenliste steht nach dem Sprachwechsel unveraendert auf {vorher!r} — "
        "sie wurde nicht neu gezeichnet")
    assert "All" in nachher, f"unerwartete Beschriftung nach dem Wechsel: {nachher!r}"

    seite.evaluate("setLang('de')")
    seite.wait_for_timeout(900)


def test_a_click_survives_the_list_being_rebuilt(seite, anfrage_vorhanden):
    """Ein Klick wirkt auch, nachdem die Liste neu aufgebaut wurde. (#449)

    WARUM DIESER TEST UND NICHT DER DANEBEN: `test_eine_anfrage_fuehrt_zur_karte_des_spiels`
    faellt nur, wenn der Klick zufaellig in einen Neuaufbau faellt. Genau deshalb hat es
    zwei Runden gedauert, den Rest des Problems zu bemerken: #419 machte die Momente
    seltener, ich hielt das Problem fuer geloest, und in der CI fiel es wieder.

    Hier wird der Neuaufbau ERZWUNGEN, statt auf ihn zu hoffen: `innerHTML` auf sich selbst
    zu setzen ersetzt jedes Kindelement. Eine Bindung, die an der Zeile hing, ist danach
    weg — ein Zuhoerer am Behaelter ueberlebt es.

    EN: the neighbouring test only fails when the click happens to land in a rebuild, which
    is why the remaining half went unnoticed for two rounds. Here the rebuild is forced.
    """
    seite.goto(seite.url.split("#")[0] + "#/requests")
    seite.wait_for_timeout(600)
    assert seite.locator(".jobt").count() > 0, "keine Anfragezeile — Fixture leer"

    # Genau das, was loadJobs tut: alle Kindelemente durch neue ersetzen.
    #
    # UND NACHSEHEN, DASS ES WIRKLICH PASSIERT IST. Bleibt der Austausch aus — weil der
    # Behaelter umbenannt wurde, die Liste leer ist oder der Browser optimiert —, klickt
    # der Test auf die URSPRUENGLICHE Zeile. Dann waere auch eine Bindung je Zeile gruen,
    # und die Pruefung sagte nichts, ohne fehlzuschlagen. Genau diese Sorte Stille hat das
    # Problem hier zwei Runden lang getragen.
    ersetzt = seite.evaluate("""() => {
        const j = document.getElementById('jobs');
        if (!j) return 'kein Behaelter';
        const vorher = j.querySelector('.jobt');
        j.innerHTML = j.innerHTML;
        const nachher = j.querySelector('.jobt');
        return (vorher && nachher && vorher !== nachher) ? 'ok' : 'nicht ersetzt';
    }""")
    assert ersetzt == "ok", (
        f"der Neuaufbau hat nicht stattgefunden ({ersetzt}) — dann sagt dieser Test nichts")
    seite.wait_for_timeout(200)

    # DER ZUHOERER MUSS DEN AUSTAUSCH UEBERLEBT HABEN — und das ist eine ANDERE Frage als
    # „hat der Klick gewirkt". Ohne diese Trennung meldet der Test nur „nichts passiert",
    # und man weiss nicht, ob die Bindung weg war oder der Klick daneben ging. Genau so
    # stand es in der CI: kein `/api/search` im Protokoll, also war der Handler nie dran.
    assert seite.evaluate(
        "() => document.getElementById('jobs').dataset.klickgebunden === '1'"), \
        "der Behaelter traegt die Bindung nicht mehr — sie haengt wieder an der Zeile"

    # UND DIE SUCHE FEST VERDRAHTEN. Sonst haengt der Ausgang daran, ob Archive.org
    # erreichbar ist: mit Netz oeffnet sich die Karte, ohne Netz bleibt nur eine
    # Kurzmeldung, die ein Auffrischen wegwischen kann. Beides prueft dieser Test nicht.
    seite.route("**/api/search*", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='[{"title":"Super Mario World","platform":"snes","platform_slug":"snes",'
             '"source":"archive","size":524288,"ref":"probe","cover":"","gkey":"smw"}]'))

    seite.locator(".jobt").first.click()
    seite.wait_for_timeout(1500)

    modal = seite.locator("#modal")
    assert modal.count() and modal.is_visible(), (
        "nach einem Neuaufbau oeffnete der Klick die Karte nicht, obwohl die Suche einen "
        "Treffer liefert — Meldung in der Zeile: "
        + (seite.locator(".jobmsg").first.inner_text().strip() or "(keine)"))


def test_the_answer_to_a_click_survives_the_next_refresh(seite, anfrage_vorhanden):
    """Die Antwort auf den Klick ueberlebt das naechste Auffrischen. (#459)

    DER REST VON #449, DEN DIE DELEGATION NICHT LOEST. Der Klick kommt an — im Serverlog
    steht die `/api/search`-Anfrage —, aber `openJobDetail` schrieb seine Antwort in die
    `.jobmsg` DER ZEILE. Das naechste `loadJobs` ersetzt die Zeile, und die Meldung ist
    weg, unter Umstaenden im selben Augenblick, in dem sie erschien.

    Diese Meldung ist die EINZIGE Rueckmeldung, die der Klick in diesem Fall erzeugt.
    Verschwindet sie, sieht ein funktionierender Klick genauso aus wie ein kaputter — so ist
    der Fehler zweimal durchgerutscht.

    WARUM DIE ANTWORT ABGEFANGEN WIRD: Auf einer Maschine MIT Netz findet die Suche eine
    Karte, das Fenster geht auf, und es gibt keine Kurzmeldung — der Test uebersprang sich
    selbst. Ein uebersprungener Test sagt nichts. Also wird `/api/search` hier fest auf
    „nichts gefunden" gelegt, und der Fall ist auf jeder Maschine derselbe.

    EN: the delegation from #450 fixed the click; the answer still lived in the row and did
    not survive the rebuild. `/api/search` is stubbed to an empty result so the case is the
    same with or without outbound network — otherwise the test skips itself on a machine
    that finds a card, and a skipped test proves nothing.
    """
    seite.route("**/api/search*",
                lambda route: route.fulfill(status=200, content_type="application/json",
                                            body="[]"))
    seite.goto(seite.url.split("#")[0] + "#/requests")
    seite.wait_for_timeout(600)
    assert seite.locator(".jobt").count() > 0, "keine Anfragezeile — Fixture leer"

    seite.locator(".jobt").first.click()
    seite.wait_for_timeout(1200)

    text_vorher = seite.locator(".jobmsg").first.inner_text().strip()
    assert text_vorher, ("der Klick erzeugte weder Karte noch Meldung — genau das war der "
                         "stille Fehlschlag aus #459")

    # DEN ECHTEN NEUAUFBAU ERZWINGEN — und zwar den, den `loadJobs` macht.
    #
    # `j.innerHTML = j.innerHTML` taugt hier NICHT: Der Rundlauf erhaelt den TEXT, er steht
    # ja im serialisierten HTML. Er verwirft nur Ereignisbindungen — deshalb ist er fuer
    # die Klickfrage nebenan richtig und fuer die Meldungsfrage hier falsch. Mit ihm bestand
    # dieser Test auch gegen den alten, kaputten Stand.
    #
    # Der echte Weg ist `loadJobs` mit geleertem `JOBSTAND`: Es setzt `innerHTML=''` und
    # zeichnet aus den Daten neu. Alles, was nur im DOM stand, ist danach weg.
    seite.evaluate("() => { const j = document.getElementById('jobs');"
                   "        j.querySelector('.jobmsg').dataset.probe = 'x';"
                   "        JOBSTAND = ''; loadJobs(); }")
    seite.wait_for_timeout(1200)

    weg = seite.evaluate("() => document.querySelectorAll('.jobmsg[data-probe=\"x\"]').length")
    assert weg == 0, ("die Liste wurde gar nicht neu gezeichnet — dann prueft dieser Test "
                      "nichts. Erwartet war ein echter Neuaufbau durch loadJobs.")

    text_nachher = seite.locator(".jobmsg").first.inner_text().strip()
    assert text_nachher == text_vorher, (
        f"die Meldung hat den Neuaufbau nicht ueberlebt: {text_vorher!r} -> "
        f"{text_nachher!r} — sie haengt wieder an der Zeile statt am Auftrag")


def test_a_failing_lookup_says_so_instead_of_doing_nothing(seite, anfrage_vorhanden):
    """Ein Fehlschlag muss sichtbar sein, nicht still. (#459)

    Hier stand ein LEERER `catch`. Netzfehler, kaputtes JSON, ein 500 aus `/api/search` —
    alles wurde verschluckt: Die Zeile hellte wieder auf, und sonst geschah nichts. Von
    einem toten Knopf ist das nicht zu unterscheiden, und es ist genau der Zustand, den ein
    Nutzer trifft, wenn die Suche gerade nicht antwortet.

    Der Fall wird erzwungen, nicht abgewartet: `/api/search` antwortet mit 500.

    EN: the empty catch swallowed every failure — the row un-dimmed and nothing happened,
    indistinguishable from a dead button. Forced here with a 500.
    """
    seite.route("**/api/search*",
                lambda route: route.fulfill(status=500, content_type="application/json",
                                            body='{"error":"kaputt"}'))
    seite.goto(seite.url.split("#")[0] + "#/requests")
    seite.wait_for_timeout(600)
    assert seite.locator(".jobt").count() > 0, "keine Anfragezeile — Fixture leer"

    seite.locator(".jobt").first.click()
    seite.wait_for_timeout(1200)

    text = seite.locator(".jobmsg").first.inner_text().strip()
    assert text, ("ein fehlgeschlagener Abruf hinterliess keine Meldung — der Klick sieht "
                  "aus, als haette er nichts getan")


def test_der_update_hinweis_verlinkt_die_genannte_version(seite, eingerichtet):
    """Nicht die Zeichenkette im Quelltext, sondern das `href` im gerenderten DOM. (#577)

    Der Hinweis erscheint nur, wenn `/api/version?check=1` ein Update meldet — auf einer
    frischen Testinstanz tut er das nie. Der Fall wird deshalb erzwungen: Die Antwort wird
    abgefangen und meldet eine neuere Beta. Ohne diese Vorgabe prüfte der Test einen Link,
    den es auf der Seite gar nicht gibt, und bestünde inhaltsleer — dieselbe Falle, die
    schon `bibliothek_gefuellt` nötig gemacht hat.

    EN: forces the update banner via a routed /api/version?check=1 and asserts the rendered
    href, not the source string. Without the stub the link never renders and the test would
    pass vacuously.
    """
    seite.route("**/api/version?check=1",
                lambda route: route.fulfill(
                    status=200, content_type="application/json",
                    body='{"version":"1.3.0-beta.1","commit":"abc1234","provenance":"build",'
                         '"latest":"1.3.0-beta.2","update_available":true}'))
    seite.goto(f"{eingerichtet}/#/settings/about", wait_until="domcontentloaded")
    seite.wait_for_timeout(1200)

    link = seite.locator("#setcontent a").filter(has_text="1.3.0-beta.2").first
    assert link.count() > 0, ("kein Update-Link gerendert — dann prueft dieser Test nichts. "
                              "Erwartet war der Hinweis aus der vorgegebenen Antwort.")
    ziel = link.get_attribute("href")
    assert ziel.endswith("/releases/tag/v1.3.0-beta.2"), (
        f"der Link fuehrt woandershin als sein Text verspricht: {ziel}")
    assert "noopener" in (link.get_attribute("rel") or ""), "rel fehlt am externen Link"


def test_der_gefahrenknopf_hebt_sich_in_jedem_design_ab(seite):
    """Ein als gefaehrlich markierter Knopf muss anders aussehen als seine Nachbarn.

    WARUM IM BROWSER: Die Unit-Tests pruefen, dass die Klasse im Markup steht, die Regel im
    Stylesheet und die Variable je Design gesetzt ist. Alles drei war wahr, waehrend der
    Knopf auf der Einstellungsseite orange blieb wie jeder andere — `#setcontent button`
    faerbt mit einer ID, und eine ID schlaegt jede Klasse. Was am Ende gilt, entscheidet
    die Kaskade, und die rechnet nur ein echter Browser aus. (#647)
    """
    seite.evaluate("location.hash='#/settings/maint'")
    seite.wait_for_timeout(600)
    assert seite.locator("#setcontent").count() == 1, "Einstellungsseite nicht geladen"

    designs = seite.evaluate("typeof DESIGNS!=='undefined'?DESIGNS:['aurora']")
    assert len(designs) >= 2, f"zu wenige Designs gefunden: {designs}"

    gleich = []
    for d in designs:
        seite.evaluate(f"document.documentElement.dataset.design={d!r}")
        seite.wait_for_timeout(250)
        farben = seite.evaluate("""() => {
          const wirt = document.getElementById('setcontent');
          const mach = (k) => { const b = document.createElement('button');
            if (k) b.className = k; b.textContent = 'x'; wirt.appendChild(b);
            const s = getComputedStyle(b);
            const c = [s.backgroundColor, s.color]; b.remove(); return c; };
          return {normal: mach(''), gefahr: mach('gefahr')};
        }""")
        if farben["gefahr"][0] == farben["normal"][0]:
            gleich.append(f"{d}: beide {farben['gefahr'][0]}")

    assert not gleich, ("der Gefahrenknopf sieht aus wie ein gewoehnlicher: "
                        + "; ".join(gleich))


# Der Kasten des Textes im Knopf, relativ zum Knopf. Ein `Range` über den Inhalt liefert
# den Inhaltsbereich der Zeile — das ist der Kasten, den die Zentrierung bewegt.
KASTEN_IM_KNOPF = """
() => {
  const b = document.querySelector('#modal .x');
  if (!b) return null;
  const k = b.getBoundingClientRect();
  const r = document.createRange(); r.selectNodeContents(b);
  const t = r.getBoundingClientRect();
  return {links: t.left - k.left, rechts: k.right - t.right,
          oben: t.top - k.top, unten: k.bottom - t.bottom,
          knopf: [k.width, k.height], text: [t.width, t.height]};
}
"""


def test_das_x_im_schliessknopf_steht_mittig(seite):
    """Das × sitzt in der Mitte seines Knopfes — gemessen an der Tinte. (#659)

    WARUM AN DER TINTE UND NICHT AM KASTEN: Gemessen wurde am laufenden Stand ein Knopf
    von 32x32 mit einem × von 8x7 Pixeln und den Rändern links 15, rechts 9, oben 18,
    unten 7 — mittig wären 12 und 12,5. Also gut 3 px nach rechts und 5,5 px nach unten
    verschoben, ein Sechstel der Knopfhöhe. Jeder Kasten für sich sah dabei plausibel aus.

    URSACHE, nachgemessen statt vermutet: Nicht die Voreinstellung des Browsers, sondern
    eine eigene Regel — `button,select,textarea{…padding:9px 14px}` weiter oben in
    derselben Datei. `#modal .x` setzt sie nie zurück. Bei `box-sizing:border-box` bleiben
    von 32 px Breite 4 px Inhalt übrig; ein 10,3 px breites Zeichen passt da nicht hinein
    und wird deshalb trotz `text-align:center` links angeschlagen statt zentriert. Senk-
    recht dasselbe: 14 px Inhaltshöhe gegen einen 24 px hohen Zeilenkasten, der unten
    überläuft.

    EN: measured on the running build, the glyph sat 3 px right and 5.5 px low in a 32 px
    button. The cause is this project's own `button{padding:9px 14px}` rule, which
    `#modal .x` never resets — not a browser default. With border-box that leaves 4 px of
    content width, and an inline box wider than its line box is start-aligned, not centred.
    """
    seite.evaluate("openUsers()")
    seite.wait_for_selector("#modal .x", timeout=15000)
    seite.wait_for_timeout(400)

    bild = bildmessung.png_lesen(seite.locator("#modal .x").first.screenshot())
    masse = bildmessung.tintenraender(bild)
    assert masse, ("im Knopf ist kein helles Zeichen zu finden — dann misst dieser Test "
                   "nichts und bestünde inhaltsleer")
    waag = masse["links"] - masse["rechts"]
    senk = masse["oben"] - masse["unten"]
    assert abs(waag) <= 2 and abs(senk) <= 2, (
        f"das × steht nicht mittig: Ränder links {masse['links']} rechts {masse['rechts']} "
        f"oben {masse['oben']} unten {masse['unten']} (Tinte {masse['tinte']} in "
        f"{masse['bild']}) — Versatz {waag} waagerecht, {senk} senkrecht")


def test_die_mitte_des_schliessknopfs_haengt_nicht_an_der_schriftart(seite):
    """Der Textkasten sitzt mittig, egal welche Schrift ihn füllt. (#659)

    WORUM ES GEHT: Der tiefere Fehler war nicht der Versatz, sondern woran er hing — an
    der Schrift, die die Seite gerade rendert. Ein auf Zahlen getrimmtes `margin` wäre bei
    der nächsten Schrift wieder daneben. Diese Prüfung nagelt deshalb die Eigenschaft
    fest, nicht den Messwert: Der Kasten wird zentriert, also bleiben die Ränder gleich,
    während sich Schriftart und Schriftgröße unter ihm ändern.

    Der Vergleich läuft über den Kasten und nicht über die Tinte, weil die Tinte selbst
    schriftabhängig ist — jede Schrift setzt das × ein wenig anders in ihre Punze. Genau
    diesen Rest darf die Regel nicht ausgleichen wollen.

    ZUR TOLERANZ VON EINEM PIXEL: Sie deckt Rundung ab, nicht Schieflage. Bei `serif 22px`
    ist der Textkasten 25 px hoch und der Knopf 32 — das sind 3,5 px je Seite, und der
    Browser meldet daraus 3 oben und 4 unten. Vor der Reparatur standen hier 14 gegen 7,7
    und 9 gegen -1; eine Toleranz von 1 px lässt das weiterhin auffliegen.

    EN: the real defect was that the offset depended on whichever font rendered the page,
    so a hand-tuned margin would drift with the next font. This pins the property instead:
    the text box stays centred while font family and size change beneath it. The 1 px
    tolerance only absorbs rounding of an odd box height inside an even button.
    """
    seite.evaluate("openUsers()")
    seite.wait_for_selector("#modal .x", timeout=15000)
    seite.wait_for_timeout(400)

    schief = []
    for familie, groesse in [("system-ui, sans-serif", "18px"), ("serif", "22px"),
                             ("monospace", "13px"), ("cursive", "18px")]:
        seite.evaluate(
            "([f,g]) => {const b=document.querySelector('#modal .x');"
            "b.style.fontFamily=f; b.style.fontSize=g;}", [familie, groesse])
        seite.wait_for_timeout(150)
        m = seite.evaluate(KASTEN_IM_KNOPF)
        assert m, "kein Schließknopf im Modal"
        if abs(m["links"] - m["rechts"]) > 1 or abs(m["oben"] - m["unten"]) > 1:
            schief.append(f"{familie} {groesse}: links {m['links']:.1f} rechts "
                          f"{m['rechts']:.1f} oben {m['oben']:.1f} unten {m['unten']:.1f}")
    assert not schief, ("der Textkasten sitzt nicht mittig im Knopf, die Zentrierung hängt "
                        "also an der Schrift: " + "; ".join(schief))


def test_alle_schliessknoepfe_teilen_dieselbe_regel():
    """Sieben Modale, ein Knopf — dieselbe Klasse, damit eine Regel wirklich alle trifft.

    WOZU: Die Reparatur von #659 ist eine einzige CSS-Regel. Das stimmt nur, solange jedes
    Modal denselben Knopf schreibt. Baut jemand ein Modal mit eigenem Markup oder eigenem
    Inline-Stil, sitzt das × dort wieder daneben, und keine der Messungen oben würde es
    bemerken — sie sehen nur das eine geöffnete Modal.

    EN: the fix is one CSS rule, which only holds while every modal emits the same button.
    The browser checks above only ever open one modal and would miss a divergent copy.
    """
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    knoepfe = re.findall(r"<button [^>]*onclick=\"closeModal\(\)\"[^>]*>(.*?)</button>", js)
    assert len(knoepfe) >= 7, (f"nur {len(knoepfe)} Schließknöpfe gefunden — das Muster "
                               "passt nicht mehr, die Prüfung liefe ins Leere")
    fremd = [k for k in re.findall(r"<button ([^>]*)onclick=\"closeModal\(\)\"([^>]*)>", js)
             if "class=x" not in k[0] + k[1]]
    assert not fremd, f"Schließknopf ohne die Klasse x: {fremd}"
    inline = [k for k in re.findall(r"<button [^>]*onclick=\"closeModal\(\)\"[^>]*>", js)
              if "style=" in k]
    assert not inline, f"Schließknopf mit eigenem Inline-Stil: {inline}"


# Die Naht zwischen Kopfleiste und dem, was darunter liegt. Gemessen werden die Zeile
# ZWEI Pixel über und die Zeile EIN Pixel unter dem Rahmen — der Rahmen selbst
# (`#side{border-bottom:1px}`) ist eine gewollte Trennlinie und wäre in jeder
# Sprungmessung ein Ausreißer, der nichts über den Verlauf aussagt.
NAHT_JS = """
() => {
  const s = document.getElementById('side');
  const b = document.getElementById('buehne');
  return {unten: s.getBoundingClientRect().bottom, dpr: devicePixelRatio,
          buehne: !!(b && !b.hidden)};
}
"""


def naht_messen(seite):
    """Der Farbsprung über die Unterkante der Kopfleiste, in Manhattan-Einheiten."""
    lage = seite.evaluate(NAHT_JS)
    bild = bildmessung.png_lesen(seite.screenshot())
    y0 = int(round(lage["unten"] * lage["dpr"]))
    sprung = bildmessung.zeilensprung(bild, y0 - 2, y0 + 1)
    sprung["buehne"] = lage["buehne"]
    sprung["spanne"] = bildmessung.zeilenspanne(bild, y0 - 2)
    return sprung


def test_der_aurora_schleier_bricht_nicht_an_der_kopfleiste_ab(seite):
    """Der Verlauf läuft über die Unterkante der Kopfleiste hinweg — auch dort, wo
    keine Bühne darunter liegt. (#657)

    GEMESSEN AM STAND VORHER, 1280x900, Gerätepixel je Spalte über die volle Breite:

    | Ansicht | größter Sprung | Median |
    |---|---|---|
    | Entdecken, mit Bühne | 84 | 43 |
    | Anfragen, ohne Bühne | 76 | 36 |

    Unter der Kopfleiste stand in Anfragen der nackte Hintergrund rgb(11,9,16), während
    die Leiste darüber bis rgb(51,20,23) glühte. Zwei getrennte Schleier, jeder von
    seinem eigenen `overflow:hidden` beschnitten — `#side::before` und `#buehne::before`.

    WARUM DIE ANSICHT OHNE BÜHNE MITGEPRÜFT WIRD: Sie ist der schlechtere Fall und auf
    einem Bildschirmauszug der Entdecken-Seite gar nicht zu sehen. Ein Test, der nur
    Entdecken misst, ließe die Hälfte des Fehlers stehen.

    WARUM DIE SPANNE MITGEPRÜFT WIRD: Eine Naht ist auch dann sprungfrei, wenn der
    Schleier ganz fehlt. Ohne diese Gegenprobe bestünde ein gelöschter Verlauf.

    EN: the glow must carry across the header's bottom edge, including in views without
    the stage — the worse case, and one a screenshot of the discover page never shows.
    The span check keeps a deleted glow from passing vacuously.
    """
    seite.set_viewport_size({"width": 1280, "height": 900})
    # Die Konfigurationswarnung schöbe sich als eigener Kasten zwischen Leiste und Bühne
    # und würde statt der Naht ihren eigenen Rand messen. Auf der Wegwerf-Instanz steht
    # sie immer, auf einer eingerichteten nie.
    seite.evaluate("""document.documentElement.dataset.design='aurora';
                      document.getElementById('cfgwarn').style.display='none'""")
    seite.wait_for_timeout(1200)

    mit = naht_messen(seite)
    assert mit["buehne"], "die Bühne fehlt beim Entdecken — dann misst der Test nicht, was er soll"
    menuepunkt(seite, "Anfragen").click()
    seite.wait_for_timeout(800)
    ohne = naht_messen(seite)
    assert not ohne["buehne"], "die Bühne steht noch in den Anfragen — falsche Ansicht gemessen"

    for name, m in (("Entdecken (mit Bühne)", mit), ("Anfragen (ohne Bühne)", ohne)):
        assert m["spanne"] >= 40, (
            f"{name}: über der Naht ist gar kein Verlauf mehr zu sehen (Spanne "
            f"{m['spanne']}) — die Sprungmessung darunter wäre inhaltsleer")
        assert m["max"] <= 14, (
            f"{name}: der Schleier bricht an der Kopfleiste ab — größter Sprung "
            f"{m['max']} bei x={m['bei_x']}, Median {m['median']}")


def test_der_schleier_erzeugt_keinen_waagerechten_bildlauf(seite):
    """Die Schicht ragt über das Fenster hinaus — sichtbar werden darf davon nichts. (#657)

    WARUM DAS EINE EIGENE PRÜFUNG IST: Der Überstand ist kein Schmuck. `aurora-wandern`
    verschiebt den Verlauf um bis zu 3 % der Breite; ohne Rand lag am rechten Fensterrand
    je nach Phase ein bis zu 26 px breiter Streifen blank. Der Preis dafür war beim ersten
    Versuch waagerechter Bildlauf: gemessen 97 px, auf JEDER Seite.

    Zwei Regeln halten das zusammen — `position:relative` auf `body`, damit der Kasten
    überhaupt beschneiden kann, und `overflow-x` auch auf `html`, weil `body` seinen Wert
    sonst ans Ansichtsfenster weiterreicht. Jede allein reicht nicht (gemessen: 97 bzw.
    101 px). Fällt eine davon weg, sagt genau diese Prüfung es.

    Die klebende Suchleiste wird mitgeprüft, weil sie der Grund ist, warum dort `clip`
    steht und nicht `hidden`: Mit `hidden` wird `body` zum Rollbereich, und `#topbar` klebt
    dann an ihm statt am Fenster — gemessen top -263,5 statt 0.

    EN: the overflowing glow layer must not become a horizontal scrollbar, and the fix for
    that must not be `overflow:hidden`, which turns body into a scroll container and stops
    the sticky search bar from sticking.
    """
    seite.evaluate("document.documentElement.dataset.design='aurora'")
    # Inhalt, damit die Seite laenger wird als das Fenster — ohne den gaebe es nichts zu
    # rollen, und die Haelfte dieser Pruefung liefe ins Leere.
    #
    # FEST VERDRAHTET, NICHT ECHT GESUCHT: Hier stand eine echte Suche nach „mario". Damit
    # hing der Ausgang daran, ob Archive.org gerade antwortet — und wenn nicht, scheiterte
    # der Test an seiner EIGENEN Voraussetzung („die Seite ist gar nicht laenger als das
    # Fenster"), nicht an dem, was er prueft. Dieselbe Lehre steht in dieser Datei weiter
    # oben schon einmal; hier war sie noch nicht angewandt.
    import json as _j
    seite.route("**/api/search*", lambda route: route.fulfill(
        status=200, content_type="application/json",
        headers={"X-Platform-Hidden": "0"},
        body=_j.dumps([{"title": f"Titel {i}", "platform": "snes", "platform_slug": "snes",
                        "source": "archive", "size": 524288, "ref": f"r{i}", "cover": "",
                        "gkey": f"g{i}", "in_library": False, "grp_in_library": False,
                        "is_set": False, "variant": {}, "variant_label": ""}
                       for i in range(30)])))
    seite.fill("#q", "Probe")
    seite.press("#q", "Enter")
    for _ in range(60):
        if seite.locator("#grid .card").count(): break
        seite.wait_for_timeout(200)
    seite.wait_for_timeout(800)
    for breite, hoehe in ((390, 844), (1280, 900)):
        seite.set_viewport_size({"width": breite, "height": hoehe})
        seite.wait_for_timeout(600)
        mass = seite.evaluate("""() => {
          window.scrollTo(500, 0); const x = window.scrollX; window.scrollTo(0, 0);
          window.scrollTo(0, 400); const y = window.scrollY;
          const t = document.getElementById('topbar').getBoundingClientRect().top;
          window.scrollTo(0, 0);
          return {x, y, top: t, sw: document.documentElement.scrollWidth,
                  iw: innerWidth, sh: document.documentElement.scrollHeight};
        }""")
        assert mass["x"] == 0 and mass["sw"] <= mass["iw"], (
            f"bei {breite} px Breite laesst sich die Seite waagerecht schieben: "
            f"scrollX {mass['x']}, scrollWidth {mass['sw']} bei {mass['iw']} px Fenster")
        assert mass["sh"] > hoehe + 400, (
            f"die Seite ist bei {breite} px gar nicht laenger als das Fenster "
            f"({mass['sh']} bei {hoehe}) — dann sagt die Bildlaufpruefung nichts")
        assert mass["y"] > 0, "senkrechter Bildlauf geht nicht mehr"
        assert mass["top"] == 0, (
            f"die Suchleiste klebt bei {breite} px nicht mehr am Fenster "
            f"(top {mass['top']}) — `overflow:hidden` statt `clip` macht `body` "
            "zum Rollbereich")


# --- Die Marke als Weg zurück auf die Startseite (#662) ----------------------------
#
# Vorher stand dort ein `div` ohne Klickziel, ohne `cursor`, ohne Tab-Position. Gemessen
# an unverändertem `dev`: ein Klick ließ die Adresse auf `#/library` stehen, und ein
# Tab-Durchlauf über 40 Schritte erreichte das Element kein einziges Mal.
#
# EN: the mark used to be a plain div — measured on unmodified dev, a click left the URL
# on #/library and 40 tab steps never reached it.

MARKE = "#side .logo"


def test_ein_klick_auf_die_marke_fuehrt_zur_startseite(seite):
    """Klick auf Zeichen oder Schriftzug führt zur Entdecken-Ansicht mit LEEREM Suchfeld.

    WARUM DAS LEEREN DAZUGEHÖRT: `zeige()` blendet die Bühne nur ein, solange das Suchfeld
    leer ist (`index.js`: `zeigeBuehne(v=='s' && !q.value)`). Eine Rückkehr, die den alten
    Suchbegriff stehen lässt, landet also auf einer Trefferliste — nicht auf der Startseite.
    Genau das ist der Unterschied zwischen diesem Weg und dem Menüpunkt „Entdecken".

    EN: returning to the start page means the discover view with an empty search field;
    leaving the query in place lands on a result list instead, and the stage stays hidden.
    """
    seite.evaluate("document.documentElement.dataset.design='aurora'")
    seite.fill("#q", "mario")
    seite.press("#q", "Enter")
    seite.wait_for_timeout(1500)
    menuepunkt(seite, "Bibliothek").click()
    seite.wait_for_timeout(400)
    assert not seite.locator("#buehne").is_visible(), "Vorbedingung verfehlt: Bühne steht"

    seite.locator(MARKE).click()
    seite.wait_for_timeout(900)
    assert seite.url.endswith("#/discover"), f"nach dem Klick auf die Marke: {seite.url}"
    assert seite.input_value("#q") == "", "das Suchfeld hält noch den alten Begriff"
    assert seite.locator("#discview").is_visible(), "die Entdecken-Ansicht ist nicht sichtbar"
    assert seite.locator("#buehne").is_visible(), (
        "die Bühne fehlt — die Startseite ist die Entdecken-Ansicht MIT Bühne")


def test_die_marke_ist_mit_der_tastatur_erreichbar_und_zeigt_den_fokus(seite):
    """Erreichbar per Tab, auslösbar per Enter, und man sieht, wo der Fokus steht.

    Ein `div` mit `onclick` wäre für all das unsichtbar: keine Rolle, keine Tab-Position,
    kein Fokusring. Deshalb ein echter `<a href>` — dieselbe Begründung wie bei den
    Menüpunkten in #329.

    EN: a div with an onclick has no role, no tab stop and no focus ring.
    """
    menuepunkt(seite, "Bibliothek").click()
    seite.wait_for_timeout(400)
    seite.evaluate("document.activeElement && document.activeElement.blur()")

    for _ in range(40):
        seite.keyboard.press("Tab")
        if seite.evaluate(
                "() => document.activeElement === document.querySelector('#side .logo')"):
            break
    else:
        pytest.fail("die Marke ist per Tab nicht erreichbar")

    ring = seite.evaluate("""() => {
      const s = getComputedStyle(document.querySelector('#side .logo'));
      return {stil: s.outlineStyle, breite: s.outlineWidth};
    }""")
    assert ring["stil"] != "none" and ring["breite"] not in ("0px", ""), (
        f"kein sichtbarer Fokusring auf der Marke: {ring}")

    seite.keyboard.press("Enter")
    seite.wait_for_timeout(900)
    assert seite.url.endswith("#/discover"), f"Enter auf der Marke führt nirgendwohin: {seite.url}"


def test_die_marke_legt_keinen_ueberfluessigen_verlaufseintrag_an(seite):
    """Einmal Zurück führt dorthin zurück, wo der Benutzer herkam.

    Zwei Fallen auf einmal: Der `href` und `navGeh()` dürfen nicht BEIDE schreiben (dann
    braucht Zurück zwei Drücke, #320), und ein Klick auf die Marke, während die Startseite
    schon steht, darf gar keinen Eintrag anlegen — sonst muss man sich durch die eigenen
    Klicks zurückdrücken.

    EN: one back press must return to where the user came from; clicking the mark while
    already on the start page must not push a duplicate entry.
    """
    menuepunkt(seite, "Probleme").click()
    seite.wait_for_timeout(400)
    menuepunkt(seite, "Bibliothek").click()
    seite.wait_for_timeout(400)

    seite.locator(MARKE).click()
    seite.wait_for_timeout(700)
    assert seite.url.endswith("#/discover"), f"nach dem Klick: {seite.url}"
    seite.locator(MARKE).click()
    seite.wait_for_timeout(700)

    seite.go_back()
    seite.wait_for_timeout(700)
    assert seite.url.endswith("#/library"), (
        f"nach einmal Zurück: {seite.url} — legt die Marke einen Eintrag zu viel an?")


def test_die_marke_sieht_als_verweis_aus_wie_vorher(seite):
    """Aus dem `div` wird ein `<a>` — das Schriftbild darf sich in keinem Design ändern.

    WARUM DAS EINE EIGENE PRÜFUNG BRAUCHT: `.logo` färbt seinen Text über
    `background-clip:text` mit `color:transparent`. Ein Verweis bringt Linkfarbe und
    Unterstreichung des Browsers mit; setzt sich davon etwas durch, ist der Schriftzug
    blau oder unterstrichen — und die Farbe kommt aus vier verschiedenen Design-Regeln.
    Verglichen wird deshalb gegen einen eingesetzten `div.logo` als Referenz: Der trägt
    genau das Aussehen, das vorher da war.

    EN: turning the div into a link must not bring link colour or underline along; the
    reference div carries exactly the previous appearance, in all four designs.
    """
    marke = seite.locator(MARKE)
    assert marke.evaluate("e => e.tagName") == "A", (
        "die Marke ist kein Verweis — ein div mit onclick hat keine Rolle und keinen Fokus")
    assert marke.evaluate("e => getComputedStyle(e).cursor") == "pointer", (
        "kein `cursor:pointer` — nichts zeigt an, dass die Marke etwas tut")

    designs = seite.evaluate("typeof DESIGNS!=='undefined'?DESIGNS:['aurora']")
    assert len(designs) >= 4, f"zu wenige Designs gefunden: {designs}"
    abweichend = []
    for d in designs:
        seite.evaluate(f"document.documentElement.dataset.design={d!r}")
        seite.wait_for_timeout(250)
        unterschied = seite.evaluate("""() => {
          const a = document.querySelector('#side .logo');
          const ref = document.createElement('div');
          ref.className = a.className; ref.innerHTML = a.innerHTML;
          a.parentNode.insertBefore(ref, a.nextSibling);
          const felder = ['color', 'webkitTextFillColor', 'backgroundImage',
                          'textDecorationLine', 'fontSize', 'fontWeight'];
          const sa = getComputedStyle(a), sr = getComputedStyle(ref);
          const raus = {};
          felder.forEach(f => { if (sa[f] !== sr[f]) raus[f] = [sa[f], sr[f]]; });
          const ka = a.getBoundingClientRect(), kr = ref.getBoundingClientRect();
          if (Math.abs(ka.width - kr.width) > 0.5 || Math.abs(ka.height - kr.height) > 0.5)
            raus.kasten = [[ka.width, ka.height], [kr.width, kr.height]];
          ref.remove();
          return raus;
        }""")
        if unterschied:
            abweichend.append(f"{d}: {unterschied}")
    assert not abweichend, ("der Schriftzug sieht als Verweis anders aus: "
                            + "; ".join(abweichend))


def test_konto_und_sprache_wandern_nur_unter_aurora(seite):
    """Unter Aurora in die Navigation, sonst in der Suchzeile. (#672 / #206)

    WARUM IM BROWSER: Das Umhaengen passiert erst zur Laufzeit in `applyDesign` — im
    Markup steht der Block immer in der Suchzeile. Ob er tatsaechlich wandert (und beim
    Zurueckschalten auch wieder zurueck), zeigt nur die geladene Seite.
    """
    fehler = []
    for d in seite.evaluate("typeof DESIGNS!=='undefined'?DESIGNS:['aurora']"):
        seite.evaluate(f"applyDesign({d!r})")
        seite.wait_for_timeout(300)
        wo = seite.evaluate("""() => {
          const kr = document.querySelector('.kopfrechts');
          if (!kr) return {fehlt: true};
          const side = document.getElementById('side'), top = document.getElementById('topbar');
          const r = kr.getBoundingClientRect();
          const sr = side.getBoundingClientRect();
          return {in_side: side.contains(kr), in_top: top.contains(kr),
                  anzahl: document.querySelectorAll('.kopfrechts').length,
                  luft_rechts: sr.right - r.right, sichtbar: r.width > 0 && r.height > 0};
        }""")
        if wo.get("fehlt"):
            fehler.append(f"{d}: kein .kopfrechts vorhanden"); continue
        if wo["anzahl"] != 1:
            fehler.append(f"{d}: {wo['anzahl']} Fassungen statt einer")
        if not wo["sichtbar"]:
            fehler.append(f"{d}: unsichtbar")
        if d == "aurora":
            if not wo["in_side"]:
                fehler.append("aurora: der Block steht nicht in der Navigation")
            elif wo["luft_rechts"] > 40:
                fehler.append(f"aurora: {wo['luft_rechts']:.0f} px Luft nach rechts — nicht am Ende")
        else:
            if not wo["in_top"]:
                fehler.append(f"{d}: der Block hat die Suchzeile verlassen (#206)")
    assert not fehler, "; ".join(fehler)


def test_das_menue_bleibt_im_bild(seite):
    """Am Fuss einer Seitenleiste muss es nach OBEN aufklappen. (#672)

    Sonst liegt es unterhalb des Fensterrands und ist unerreichbar — sichtbar wird das
    erst, wenn man es oeffnet und nachmisst.
    """
    fehler = []
    for d in seite.evaluate("typeof DESIGNS!=='undefined'?DESIGNS:['aurora']"):
        seite.evaluate(f"document.documentElement.dataset.design={d!r}")
        seite.wait_for_timeout(250)
        seite.evaluate("document.getElementById('userbox').classList.add('auf')")
        seite.wait_for_timeout(200)
        m = seite.evaluate("""() => {
          const el = document.getElementById('usermenu');
          const r = el.getBoundingClientRect();
          return {oben: r.top, unten: r.bottom, hoehe: window.innerHeight, sichtbar: r.height > 0};
        }""")
        seite.evaluate("document.getElementById('userbox').classList.remove('auf')")
        if not m["sichtbar"]:
            fehler.append(f"{d}: das Menue hat keine Hoehe"); continue
        if m["unten"] > m["hoehe"] + 1 or m["oben"] < -1:
            fehler.append(f"{d}: Menue ausserhalb des Bildes "
                          f"(oben {m['oben']:.0f}, unten {m['unten']:.0f}, Fenster {m['hoehe']})")
    assert not fehler, "; ".join(fehler)


def test_leeren_knopf_erscheint_und_raeumt_auf(seite):
    """Der Knopf zeigt sich erst, wenn es etwas zu leeren gibt — und leert dann. (#661)

    WARUM IM BROWSER: Sichtbarkeit haengt an `style.display`, das ein Ereignis setzt.
    Ob der Knopf nach dem Tippen erscheint und nach dem Klick wieder verschwindet, sieht
    nur eine Seite, auf der wirklich getippt wurde.
    """
    q = seite.locator("#q")
    knopf = seite.locator("#tClear")
    assert not knopf.is_visible(), "der Leeren-Knopf steht schon bei leerem Feld da"

    q.fill("Zelda")
    seite.dispatch_event("#q", "input")
    seite.wait_for_timeout(200)
    assert knopf.is_visible(), "nach dem Tippen erscheint er nicht"

    knopf.click()
    seite.wait_for_timeout(400)
    assert q.input_value() == "", "das Feld ist nicht leer"
    assert not knopf.is_visible(), "er bleibt nach dem Leeren stehen"
    assert seite.evaluate("document.activeElement===document.getElementById('q')"), \
        "der Fokus steht nicht mehr im Feld"


def test_escape_raeumt_erst_dialog_dann_suchfeld(seite):
    """Escape gehoert zuerst dem Dialog. (#661)

    Waere es andersherum, verloere man mit dem Schliessen eines Dialogs seine Suche —
    und das faellt erst auf, wenn es einmal passiert ist.
    """
    seite.locator("#q").fill("Mario")
    seite.dispatch_event("#q", "input")
    seite.wait_for_timeout(150)

    # Dialog auf: er muss zuerst weichen, das Feld bleibt
    seite.evaluate("""() => {
      const m = document.getElementById('modal');
      m.innerHTML = '<div class=box>Test</div>'; m.style.display = 'block';
    }""")
    seite.keyboard.press("Escape")
    seite.wait_for_timeout(250)
    assert seite.evaluate("document.getElementById('modal').style.display") != "block", \
        "der Dialog blieb offen"
    assert seite.locator("#q").input_value() == "Mario", \
        "das Feld wurde geleert, obwohl der Dialog dran war"

    # zweites Escape: jetzt das Feld
    seite.keyboard.press("Escape")
    seite.wait_for_timeout(250)
    assert seite.locator("#q").input_value() == "", "das Feld wurde nicht geleert"


def test_zurueck_knopf_zeigt_sich_nur_mit_eigenem_verlauf(seite):
    """Sonst fuehrte er aus Romseerr hinaus. (#661/#226)"""
    zurueck = seite.locator("#tBack")
    start = seite.evaluate("EIGENE_SCHRITTE")
    if start == 0:
        assert not zurueck.is_visible(), "er steht da, obwohl es nichts zurueck gibt"
    menuepunkt(seite, "Anfragen").click()
    seite.wait_for_timeout(400)
    assert seite.evaluate("EIGENE_SCHRITTE") > 0, "Testaufbau: kein eigener Verlaufseintrag"
    assert zurueck.is_visible(), "nach einem eigenen Schritt fehlt der Zurueck-Knopf"


# --- #688: der Plattformfilter haelt Treffer zurueck, ohne es zu sagen ---

def _suche_mit_filter(seite, treffer, versteckt, filt="snes"):
    """Setzt den Plattformfilter, verdrahtet /api/search samt Kopfzeile, sucht."""
    seite.evaluate("""f => { SELP = new Set([f]);
      localStorage.setItem('romp', JSON.stringify([f])); updateFLabel(); }""", filt)
    gefragt = []
    seite.route("**/api/search*", lambda route: (
        gefragt.append(route.request.url),
        route.fulfill(status=200, content_type="application/json",
                      headers={"X-Platform-Hidden": str(
                          versteckt if "platforms=" + filt in route.request.url else 0)},
                      body=treffer if "platforms=" + filt in route.request.url else "[]"),
    ) and None)
    seite.locator("#q").fill("Silent Hill Homecoming")
    seite.keyboard.press("Enter")
    seite.wait_for_timeout(800)
    return gefragt


TREFFER_JSON = ('[{"title":"Irgendwas ohne Plattform","platform":"","platform_slug":"",'
                '"source":"archive","size":524288,"ref":"p1","cover":"","gkey":"a"}]')


def test_zurueckgehaltene_treffer_stehen_in_der_liste(seite):
    """Die Zahl gehoert dorthin, wo das Ergebnis steht. (#688)

    WARUM IM BROWSER: Der Hinweis entsteht aus einer HTTP-KOPFZEILE, die nur ein echter
    Abruf traegt — der Flask-Testclient rendert nichts und fuehrt kein JavaScript aus.
    Ob die Zahl beim Nutzer ankommt, sieht nur eine Seite, die wirklich gesucht hat.
    """
    _suche_mit_filter(seite, TREFFER_JSON, 10)
    hinweis = seite.locator(".plathint")
    assert hinweis.count() == 1, "kein Hinweis auf zurueckgehaltene Treffer"
    text = hinweis.inner_text()
    assert "10" in text, f"die Zahl fehlt im Hinweis: {text!r}"
    assert seite.locator(".plathint-x").is_visible(), "kein Weg aus dem Filter heraus"


def test_zurueckgehaltene_treffer_stehen_auch_bei_null_treffern_da(seite):
    """Der schlimmste Fall ist der, in dem gar nichts kommt. (#688)

    Eine leere Liste mit haengengebliebenem Filter liest sich als „gibt es nicht". Genau
    dort muss der Grund stehen — der Zweig fuer null Treffer springt frueh heraus und
    haette den Hinweis sonst uebersprungen.
    """
    _suche_mit_filter(seite, "[]", 14)
    assert seite.locator(".plathint").count() == 1, \
        "bei null Treffern fehlt der Hinweis — genau da wird er gebraucht"
    assert "14" in seite.locator(".plathint").inner_text()


def test_kein_hinweis_ohne_filter(seite):
    """Ohne Filter haelt nichts zurueck — dann steht dort auch nichts. (#688)"""
    seite.evaluate("() => { SELP = new Set(); localStorage.setItem('romp','[]'); }")
    seite.route("**/api/search*", lambda route: route.fulfill(
        status=200, content_type="application/json",
        headers={"X-Platform-Hidden": "0"}, body=TREFFER_JSON))
    seite.locator("#q").fill("Silent Hill")
    seite.keyboard.press("Enter")
    seite.wait_for_timeout(800)
    assert seite.locator(".plathint").count() == 0, "Hinweis ohne aktiven Filter"


def test_filter_aufheben_sucht_ohne_den_filter_neu(seite):
    """Der Knopf muss die Treffer wirklich zurueckholen. (#688)

    Nur den Filter zu leeren, ohne neu zu suchen, liesse die duenne Liste stehen — mit
    dem Hinweis daneben, dass zehn Treffer fehlen, und nichts passiert. Geprueft wird
    deshalb die ZWEITE Anfrage: sie darf keine Plattform mehr tragen.
    """
    gefragt = _suche_mit_filter(seite, TREFFER_JSON, 10)
    assert len(gefragt) == 1, f"unerwartete Zahl Suchanfragen: {gefragt}"

    seite.locator(".plathint-x").click()
    seite.wait_for_timeout(900)

    assert len(gefragt) == 2, "der Klick hat keine neue Suche ausgeloest"
    assert "platforms=snes" not in gefragt[1], \
        f"die zweite Suche traegt den Filter noch: {gefragt[1]}"
    assert seite.evaluate("() => JSON.parse(localStorage.getItem('romp')||'[]').length") == 0, \
        "der Filter steht noch in localStorage und kaeme beim naechsten Laden zurueck"
    assert seite.locator(".plathint").count() == 0, \
        "der Hinweis steht noch da, obwohl nichts mehr zurueckgehalten wird"


# --- #691: eine Karte je Spiel, nicht je Fassung ---

def _sechs_fassungen(gkeys):
    """Trefferliste bauen: je Eintrag (gkey, titel, vorhanden)."""
    import json as _j
    return _j.dumps([
        {"title": t, "platform": "pc", "platform_slug": "pc", "source": "archive",
         "size": 524288, "ref": f"r{i}", "cover": "", "gkey": g,
         "in_library": lib, "grp_in_library": lib, "is_set": False,
         "variant": {}, "variant_label": ""}
        for i, (g, t, lib) in enumerate(gkeys)])


def _suche(seite, koerper):
    seite.evaluate("() => { SELP = new Set(); localStorage.setItem('romp','[]'); }")
    seite.route("**/api/search*", lambda route: route.fulfill(
        status=200, content_type="application/json",
        headers={"X-Platform-Hidden": "0"}, body=koerper))
    seite.locator("#q").fill("Mario Kart")
    seite.keyboard.press("Enter")
    seite.wait_for_timeout(900)


def test_dieselbe_gkey_ergibt_eine_karte(seite):
    """Zehnmal `mario kart` verdraengte neun andere Spiele. (#691)

    WARUM IM BROWSER: Die Zusammenfassung passiert beim Aufbau der Liste. Ob am Ende eine
    Karte dasteht oder sechs, sieht nur eine Seite, die wirklich gesucht hat.
    """
    _suche(seite, _sechs_fassungen([
        ("mk", "Mario Kart (USA)", False), ("mk", "Mario Kart (EUR)", False),
        ("mk", "Mario Kart (JPN)", False), ("mk", "Mario Kart Rev A", False),
        ("mk8", "Mario Kart 8", False), ("mkw", "Mario Kart Wii", False),
    ]))
    karten = seite.locator("#grid .card")
    assert karten.count() == 3, \
        f"{karten.count()} Karten statt 3 — sechs Fassungen, drei Spiele"
    titel = [karten.nth(i).locator(".t").inner_text().strip() for i in range(3)]
    assert len(set(titel)) == 3, f"ein Titel steht doppelt: {titel}"


def test_die_karte_sagt_wie_viele_fassungen_dahinter_liegen(seite):
    """Sonst waere die Zusammenfassung ein Verlust. (#691)"""
    _suche(seite, _sechs_fassungen([
        ("mk", "Mario Kart (USA)", False), ("mk", "Mario Kart (EUR)", False),
        ("mk", "Mario Kart (JPN)", False), ("mk8", "Mario Kart 8", False),
    ]))
    meta = seite.locator("#grid .card").first.locator(".meta").inner_text()
    assert "3" in meta and "Fassungen" in meta, \
        f"die Karte verschweigt die drei Fassungen: {meta!r}"
    # Bei genau einer Fassung waere „1 Fassung" nur Rauschen.
    meta2 = seite.locator("#grid .card").nth(1).locator(".meta").inner_text()
    assert "Fassungen" not in meta2, f"Einzelfassung traegt trotzdem eine Zahl: {meta2!r}"


def test_die_zahl_ueber_der_liste_zaehlt_was_dasteht(seite):
    """„47 Treffer" neben 30 Karten war der Widerspruch. (#691)"""
    _suche(seite, _sechs_fassungen([
        ("mk", "Mario Kart (USA)", False), ("mk", "Mario Kart (EUR)", False),
        ("mk8", "Mario Kart 8", False),
    ]))
    hint = seite.locator("#hint").inner_text()
    karten = seite.locator("#grid .card").count()
    assert hint.strip().startswith(str(karten)), \
        f"oben steht {hint!r}, danebenliegen aber {karten} Karten"


def test_die_detailansicht_kennt_weiterhin_alle_fassungen(seite):
    """Zusammenfassen darf nichts wegwerfen. (#691)

    Die Fassungsliste in der Karte baut auf `window.LASTRES`. Wuerde dort nur noch der
    Vertreter stehen, waere die Wahl zwischen Regionen und Fassungen (#77) verloren —
    und genau die ist der Grund, warum es die Detailansicht gibt.
    """
    _suche(seite, _sechs_fassungen([
        ("mk", "Mario Kart (USA)", False), ("mk", "Mario Kart (EUR)", False),
        ("mk", "Mario Kart (JPN)", False),
    ]))
    assert seite.evaluate("() => window.LASTRES.length") == 3, \
        "LASTRES wurde beim Zusammenfassen beschnitten"
    seite.locator("#grid .card").first.locator(".t").click()
    seite.wait_for_timeout(1500)
    # Nicht `h3` allgemein — der erste ist die Bewertung. Gemeint ist die Ueberschrift
    # ueber der Fassungsliste, und die haengt am Behaelter `#mvar`.
    kopf = seite.locator("#modal .sec", has=seite.locator("#mvar")).locator("h3").inner_text()
    assert "(3)" in kopf, f"die Detailansicht zaehlt nicht drei Fassungen: {kopf!r}"
    assert seite.locator("#mvar .row").count() == 3, \
        f"{seite.locator('#mvar .row').count()} Fassungszeilen statt 3"


def test_der_sammelknopf_zaehlt_was_die_liste_anbietet(seite):
    """25 angeboten, 24 Knoepfe sichtbar. (#691)

    WARUM DAS AUFFIEL: Nach dem Zusammenfassen zeigt die Karte den Zustand der GRUPPE. Ein
    Spiel, das auf einer Plattform daliegt und auf einer anderen frei ist, traegt damit den
    Haken und keinen Download-Knopf. Der Sammelknopf zaehlte aber weiter je Einzelfassung
    und bot es mit an — bei `Mario Kart` am laufenden System als 25 gegen 24 gemessen.

    Eine Sammelanfrage, die etwas holt, das die Oberflaeche als vorhanden ausweist, ist
    schlimmer als eine Zahl daneben: Sie laedt herunter, was schon da ist.
    """
    import json as _j
    seite.evaluate("() => { SELP = new Set(); localStorage.setItem('romp','[]'); }")
    # `mk` ist die gemischte Gruppe: eine Fassung vorhanden, eine frei.
    koerper = _j.dumps([
        {"title": "Mario Kart Wii", "platform": "wii", "platform_slug": "wii",
         "source": "archive", "size": 1, "ref": "r1", "cover": "", "gkey": "mk",
         "in_library": True, "grp_in_library": True, "is_set": False,
         "variant": {}, "variant_label": ""},
        {"title": "Mario Kart Wii (EUR)", "platform": "wii", "platform_slug": "wii",
         "source": "archive", "size": 1, "ref": "r2", "cover": "", "gkey": "mk",
         "in_library": False, "grp_in_library": True, "is_set": False,
         "variant": {}, "variant_label": ""},
        {"title": "Mario Kart 8", "platform": "wiiu", "platform_slug": "wiiu",
         "source": "archive", "size": 1, "ref": "r3", "cover": "", "gkey": "mk8",
         "in_library": False, "grp_in_library": False, "is_set": False,
         "variant": {}, "variant_label": ""},
        {"title": "Mario Kart DS", "platform": "nds", "platform_slug": "nds",
         "source": "archive", "size": 1, "ref": "r4", "cover": "", "gkey": "mkds",
         "in_library": False, "grp_in_library": False, "is_set": False,
         "variant": {}, "variant_label": ""},
    ])
    seite.route("**/api/search*", lambda route: route.fulfill(
        status=200, content_type="application/json",
        headers={"X-Platform-Hidden": "0"}, body=koerper))
    seite.locator("#q").fill("Mario Kart")
    seite.keyboard.press("Enter")
    seite.wait_for_timeout(900)

    # NUR die Download-Knoepfe. `.dl.zw` ist „Details" bzw. „angefragt" — ein
    # aktiver Knopf, der nichts herunterlaedt, und er zaehlte hier faelschlich mit.
    knoepfe = seite.locator("#grid .card .act button.dl:not(.zw)").count()
    knopf = seite.locator("#bulkbtn")
    assert knopf.count() == 1, "kein Sammelknopf — der Test prueft dann nichts"
    import re as _re
    zahl = int(_re.search(r"\((\d+)\)", knopf.inner_text()).group(1))
    assert zahl == 2, f"der Sammelknopf bietet {zahl} an; anfragbar sind 2 Spiele"
    assert zahl == knoepfe, \
        f"der Sammelknopf bietet {zahl} an, die Liste zeigt {knoepfe} Download-Knoepfe"


def test_die_sammelanfrage_holt_keine_vorhandenen_spiele(seite):
    """Die Zahl daneben ist das kleinere Uebel — das hier laedt herunter. (#691)

    Ein Test auf die Beschriftung des Knopfes beweist NICHT, was der Klick tut: Ein
    Mutationstest liess die Zaehlung richtig und die Anfrage falsch, und alles blieb
    gruen. Geprueft wird deshalb, was wirklich an `/api/download` geht.
    """
    import json as _j
    seite.evaluate("() => { SELP = new Set(); localStorage.setItem('romp','[]'); }")
    koerper = _j.dumps([
        {"title": "Habe ich (Wii)", "platform": "wii", "platform_slug": "wii",
         "source": "archive", "size": 1, "ref": "r1", "cover": "", "gkey": "mk",
         "in_library": True, "grp_in_library": True, "is_set": False,
         "variant": {}, "variant_label": ""},
        {"title": "Dieselbe Reihe, freie Fassung", "platform": "wii", "platform_slug": "wii",
         "source": "archive", "size": 1, "ref": "r2", "cover": "", "gkey": "mk",
         "in_library": False, "grp_in_library": True, "is_set": False,
         "variant": {}, "variant_label": ""},
        {"title": "Habe ich gar nicht", "platform": "wiiu", "platform_slug": "wiiu",
         "source": "archive", "size": 1, "ref": "r3", "cover": "", "gkey": "mk8",
         "in_library": False, "grp_in_library": False, "is_set": False,
         "variant": {}, "variant_label": ""},
        # ZWEI freie Spiele sind noetig: Der Sammelknopf erscheint erst ab zwei. Mit nur
        # einem gaebe es nichts zu klicken, und der Test bewiese nichts.
        {"title": "Habe ich auch nicht", "platform": "nds", "platform_slug": "nds",
         "source": "archive", "size": 1, "ref": "r4", "cover": "", "gkey": "mkds",
         "in_library": False, "grp_in_library": False, "is_set": False,
         "variant": {}, "variant_label": ""},
    ])
    seite.route("**/api/search*", lambda route: route.fulfill(
        status=200, content_type="application/json",
        headers={"X-Platform-Hidden": "0"}, body=koerper))
    geholt = []
    seite.route("**/api/download", lambda route: (
        geholt.append(_j.loads(route.request.post_data or "{}").get("title")),
        route.fulfill(status=200, content_type="application/json", body='{"ok":true}'),
    ) and None)

    seite.locator("#q").fill("Mario Kart")
    seite.keyboard.press("Enter")
    seite.wait_for_timeout(900)
    seite.locator("#bulkbtn").click()
    seite.wait_for_timeout(1500)

    assert sorted(geholt) == ["Habe ich auch nicht", "Habe ich gar nicht"], \
        ("die Sammelanfrage holte " + repr(geholt) + " — die freie Fassung eines Spiels, "
         "dessen Karte den Haken traegt, gehoert NICHT dazu")


# --- #660: „vorhanden" in der Sprache der Marke ---

def _kontrast_js():
    """WCAG-Kontrast zweier CSS-Farben, im Browser gerechnet."""
    return """(a,b)=>{const z=s=>s.match(/\\d+(\\.\\d+)?/g).slice(0,3).map(Number);
      const l=c=>{const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)};
      const [r,g,bl]=c.map(f);return .2126*r+.7152*g+.0722*bl};
      const la=l(z(a)),lb=l(z(b));return (Math.max(la,lb)+.05)/(Math.min(la,lb)+.05);}"""


def test_jedes_design_setzt_sein_eigenes_gruen(seite):
    """Die Ursache war ein Literal, keine Variable. (#660)

    `--ok` stand einmal global und kein Design ueberschrieb es — alle vier bekamen
    dasselbe Signalgruen. Drei weitere Stellen hatten die Farbe gar nicht als Variable,
    sondern als `#1e5e3a` im Stylesheet stehen.
    """
    werte = seite.evaluate("""() => {
      const merk = document.documentElement.dataset.design, out = {};
      for (const d of ['', 'glass', 'clean', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const cs = getComputedStyle(document.documentElement);
        out[d || 'seerr'] = [cs.getPropertyValue('--ok').trim(),
                             cs.getPropertyValue('--ok-bg').trim()];
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return out;
    }""")
    assert len(werte) == 4
    for design, (ok, okbg) in werte.items():
        assert ok and okbg, f"{design} setzt --ok/--ok-bg nicht: {werte[design]}"
    # ... und sie muessen sich UNTERSCHEIDEN, sonst ist die Variable nur Zierde.
    gruene = {v[0] for v in werte.values()}
    assert len(gruene) == 4, f"nicht jedes Design hat ein eigenes Gruen: {werte}"


def test_der_kontrast_ist_gemessen_und_reicht(seite):
    """4,5:1 gegen den Kartengrund des jeweiligen Designs — im Browser gerechnet. (#660)

    Die Abnahme des Issues verlangt ausdruecklich „gemessen, nicht geschaetzt". Ein Wert
    aus einer Tabelle im Kopf des Entwicklers ist genau das Gegenteil.
    """
    werte = seite.evaluate("""(kontrast) => {
      const k = eval(kontrast), merk = document.documentElement.dataset.design, out = {};
      for (const d of ['', 'glass', 'clean', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const cs = getComputedStyle(document.documentElement);
        const probe = document.createElement('div');
        probe.style.color = cs.getPropertyValue('--ok').trim();
        probe.style.background = cs.getPropertyValue('--card').trim();
        document.body.appendChild(probe);
        const c = getComputedStyle(probe);
        out[d || 'seerr'] = k(c.color, c.backgroundColor);
        probe.remove();
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return out;
    }""", _kontrast_js())
    for design, wert in werte.items():
        assert wert >= 4.5, f"{design}: Kontrast nur {wert:.2f}:1 gegen die Karte"


def test_das_zeichen_ist_gezeichnet_und_kein_schriftzeichen(seite):
    """Ein Textzeichen kommt aus der Schrift des Systems. (#660/#650)"""
    quelle = seite.content()
    assert 'id="rs-vorhanden"' in quelle, "die Zeichnung fehlt in der Vorlage"
    # KEIN `<text>`, kein Emoji — dieselbe Regel wie bei der Marke.
    definition = quelle.split('id="rs-vorhanden"', 1)[1].split("</g>", 1)[0]
    assert "<text" not in definition, "die Zeichnung benutzt eine Schrift"
    assert "fill-rule" in definition and "evenodd" in definition, \
        "der Haken ist nicht ausgeschnitten — das ist die Bauart der Marke"


def test_das_abzeichen_ist_gross_genug_fuer_die_modulform(seite):
    """Der Einwand, der die Umsetzung geaendert hat. (#660)

    Bei den alten 11 px war die Modulform nicht von einem gerundeten Quadrat zu
    unterscheiden — die abgeschraegte Ecke ging unter. Am Entwurf gemessen, bevor es
    gebaut wurde. Faellt das je unter 16 px zurueck, ist die Form wieder umsonst.
    """
    seite.evaluate("""() => {
      const p = document.createElement('div'); p.className = 'pcover';
      p.style.cssText = 'position:relative;width:80px;height:110px';
      p.innerHTML = '<span class=have2><svg viewBox="0 0 64 64"><use href="#rs-vorhanden"/></svg></span>';
      p.id = 'probe660'; document.body.appendChild(p);
    }""")
    kasten = seite.evaluate(
        "() => document.querySelector('#probe660 .have2 svg').getBoundingClientRect().width")
    seite.evaluate("() => document.getElementById('probe660').remove()")
    assert kasten >= 16, f"das Zeichen misst nur {kasten:.0f} px — dafuer ist es zu fein"


def test_die_zeichnung_fuellt_ihr_feld_aus(seite):
    """Sonst bleibt von der Modulform nichts uebrig. (#660)

    Die erste Fassung mass nur 30 von 64 Einheiten — bei 18 px gerendert waren das 2,2 px
    Schraege, und das Abzeichen sah aus wie ein gerundetes Quadrat mit Haken. Die Form war
    da und trotzdem nicht zu sehen. Wer die Zeichnung spaeter verkleinert, macht denselben
    Fehler noch einmal; deshalb steht die Untergrenze hier und nicht nur im Kommentar.
    """
    breite = seite.evaluate("""() => {
      const g = document.getElementById('rs-vorhanden');
      const p = g.querySelector('path');
      const b = p.getBBox();
      return {w: b.width, h: b.height};
    }""")
    assert breite["w"] >= 48, \
        f"die Zeichnung ist nur {breite['w']:.0f} von 64 Einheiten breit — zu klein fuer die Schraege"
    assert breite["h"] >= 48, f"die Zeichnung ist nur {breite['h']:.0f} von 64 Einheiten hoch"


# --- #658: gezeichnete Zeichen statt Emoji ---

EMOJI_MUSTER = r"[\U0001F300-\U0001FAFF←-➿️]"


def test_kein_emoji_mehr_in_navigation_und_benutzermenue(seite):
    """Emoji kommen aus der Schrift, die das System gerade hat. (#658/#650)"""
    import re
    texte = seite.evaluate("""() => {
      const raus = [];
      document.querySelectorAll('#side .nav, #usermenu .mitem').forEach(e => raus.push(e.textContent));
      return raus;
    }""")
    assert len(texte) >= 9, f"nur {len(texte)} Menuepunkte gefunden — der Test sieht zu wenig an"
    for t in texte:
        treffer = re.findall(EMOJI_MUSTER, t)
        assert not treffer, f"Emoji {treffer} steht noch in {t.strip()!r}"


def test_jedes_zeichen_zeigt_auf_eine_vorhandene_definition(seite):
    """Ein `use` ins Leere rendert NICHTS — lautlos. (#658)

    Das ist die gefaehrlichste Stelle an dieser Bauart: Ein Tippfehler in der Kennung
    erzeugt keinen Fehler, keine Warnung und keine Luecke im Aufbau — nur ein unsichtbares
    Zeichen. Geprueft wird deshalb beides: dass die Kennung existiert UND dass wirklich
    etwas gezeichnet wird.
    """
    # DAS BENUTZERMENUE AUFKLAPPEN. Zugeklappt steht es auf `display:none`, und dort gibt
    # `getBBox()` immer 0 zurueck — der Test haette drei Zeichen als „rendert nichts"
    # gemeldet, die voellig in Ordnung sind. Erst messen, wenn es etwas zu messen gibt.
    seite.evaluate("() => document.getElementById('usermenu').style.display = 'block'")
    seite.wait_for_timeout(200)
    ergebnis = seite.evaluate("""() => {
      const raus = [];
      document.querySelectorAll('svg.navsym use').forEach(u => {
        const id = (u.getAttribute('href') || '').slice(1);
        const ziel = document.getElementById(id);
        let flaeche = 0;
        try { const b = u.ownerSVGElement.getBBox(); flaeche = b.width * b.height; } catch (e) {}
        raus.push({id, da: !!ziel, flaeche});
      });
      return raus;
    }""")
    seite.evaluate("() => document.getElementById('usermenu').style.display = ''")
    assert ergebnis, "keine Zeichen gefunden — der Test sieht nichts an"
    fehlend = [e["id"] for e in ergebnis if not e["da"]]
    assert not fehlend, f"diese Kennungen gibt es nicht: {fehlend}"
    leer = [e["id"] for e in ergebnis if e["flaeche"] < 1]
    assert not leer, f"diese Zeichen rendern nichts: {leer}"


def test_ein_sprachwechsel_loescht_kein_zeichen(seite):
    """DER RUECKFALLWEG AUS #337, und er war live. (#658)

    `applyI18n` setzt `textContent` des Elements mit `data-i18n` — und loescht damit jedes
    Kind. Am laufenden Stand gemessen waren 👤 (Profil) und ⭐ (Meine Listen) deshalb NIE
    zu sehen: Das Symbol stand nur in der Vorlage, nicht in der Uebersetzung, und wurde
    schon beim Laden weggeschrieben. Nur 🚪 ueberlebte, weil es im Uebersetzungstext sass.

    Deshalb sitzt das Zeichen jetzt in einem EIGENEN Knoten neben dem uebersetzten Text.
    """
    zaehle = "() => document.querySelectorAll('#side .nav svg.navsym, #usermenu .mitem svg.navsym').length"
    # GENAU ZEHN, nicht „mindestens neun". Ein Mutationstest hat gezeigt, wozu eine
    # weiche Untergrenze taugt: Wird ein Zeichen zurueck INS uebersetzte Element gelegt,
    # ist es schon beim LADEN weg (applyI18n laeuft sofort) — der Zaehler stand dann von
    # Anfang an auf 9 und blieb es, und ein Vorher-Nachher-Vergleich merkte nichts.
    # 7 Menuepunkte + 3 im Benutzermenue.
    erwartet = seite.evaluate("() => document.querySelectorAll('#side .nav').length"
                              " + document.querySelectorAll('#usermenu .mitem').length")
    vorher = seite.evaluate(zaehle)
    assert vorher == erwartet, \
        (f"{vorher} Zeichen bei {erwartet} Menuepunkten — eines fehlt schon beim Laden. "
         "Das ist der #337-Weg: ein Zeichen im uebersetzten Element wird sofort geloescht.")
    for sprache in ("en", "fr", "de"):
        seite.evaluate("s => setLang(s)", sprache)
        seite.wait_for_timeout(700)
        jetzt = seite.evaluate(zaehle)
        assert jetzt == vorher, \
            f"nach dem Wechsel auf {sprache} sind es {jetzt} statt {vorher} Zeichen"
    # ... und der Text muss trotzdem uebersetzt worden sein, sonst prueft das nichts.
    seite.evaluate("() => setLang('en')")
    seite.wait_for_timeout(700)
    text = seite.evaluate("() => document.querySelector('#usermenu .mitem:last-child').textContent.trim()")
    seite.evaluate("() => setLang('de')")
    seite.wait_for_timeout(700)
    assert text == "Sign out", f"der Text wurde nicht uebersetzt: {text!r}"


def test_die_zeichen_wirken_in_allen_vier_designs(seite):
    """21 px ist die Groesse, in der sie wirklich stehen. (#658)"""
    werte = seite.evaluate("""() => {
      const merk = document.documentElement.dataset.design, out = {};
      for (const d of ['', 'glass', 'clean', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const s = document.querySelector('#side .nav svg.navsym');
        const r = s.getBoundingClientRect(), cs = getComputedStyle(s);
        out[d || 'seerr'] = {breite: Math.round(r.width), farbe: cs.color};
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return out;
    }""")
    for design, w in werte.items():
        assert 17 <= w["breite"] <= 26, f"{design}: Zeichen ist {w['breite']} px breit"
    # Die Farbe MUSS sich je Design unterscheiden — sonst erbt sie nicht, sondern steht fest.
    farben = {w["farbe"] for w in werte.values()}
    assert len(farben) > 1, f"die Zeichen tragen ueberall dieselbe Farbe: {farben}"


def test_die_einstellungsreiter_tragen_zeichen_die_untereintraege_nicht(seite):
    """Zwei Entscheidungen in einem Test. (#658)

    Die elf Reiter bekommen Zeichen. Die Untereintraege bewusst NICHT: Dort stehen
    Produktnamen (Discord, SMTP, Telegram), und ein erfundenes Zeichen sagt dort weniger
    als der Name — ein Produktlogo wiederum gehoert nicht in unsere Formensprache.
    """
    seite.evaluate("() => show('set')")
    seite.wait_for_timeout(900)
    reiter = seite.evaluate("() => document.querySelectorAll('.snav').length")
    mit = seite.evaluate("() => document.querySelectorAll('.snav svg.navsym').length")
    assert reiter == 11, f"{reiter} Reiter statt 11"
    assert mit == 11, f"nur {mit} von {reiter} Reitern tragen ein Zeichen"
    # Untereintraege: der Benachrichtigungsreiter hat welche
    seite.evaluate("() => setSection('notif')")
    seite.wait_for_timeout(700)
    unter = seite.evaluate("() => document.querySelectorAll('#setsub .ssub').length")
    unter_mit = seite.evaluate("() => document.querySelectorAll('#setsub svg.navsym').length")
    assert unter > 0, "keine Untereintraege sichtbar — der Test prueft dann nichts"
    assert unter_mit == 0, f"{unter_mit} Untereintraege tragen ein Zeichen, erwartet 0"


def test_die_gruenen_stellen_im_javascript_ziehen_mit_dem_design_mit(seite):
    """Der Waechter im Quelltext beweist nur, dass kein Literal DASTEHT. (#699)

    Ob `var(--ok)` an der Stelle auch wirklich auf eine gesetzte Variable zeigt, sieht man
    erst im Aufbau: Ein Tippfehler im Variablennamen faellt nicht auf — CSS wirft dafuer
    keinen Fehler, die Eigenschaft bleibt einfach ungesetzt und die Farbe faellt auf den
    Erbwert zurueck. Geprueft wird deshalb die GERECHNETE Farbe, und zwar in zwei Designs,
    weil eine feste Farbe in beiden dieselbe waere.
    """
    werte = seite.evaluate("""() => {
      const merk = document.documentElement.dataset.design, out = {};
      for (const d of ['', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const probe = document.createElement('span');
        // dieselbe Schreibweise wie an den sieben Stellen
        probe.style.color = 'var(--ok)';
        probe.style.background = 'var(--ok-bg)';
        document.body.appendChild(probe);
        const cs = getComputedStyle(probe);
        out[d || 'seerr'] = [cs.color, cs.backgroundColor];
        probe.remove();
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return out;
    }""")
    for design, (farbe, grund) in werte.items():
        assert farbe and "rgba(0, 0, 0, 0)" not in farbe, f"{design}: --ok ist nicht gesetzt"
        assert "rgba(0, 0, 0, 0)" not in grund, f"{design}: --ok-bg ist nicht gesetzt"
    assert werte["seerr"] != werte["aurora"], \
        f"beide Designs bekommen dieselbe Farbe — die Variable wirkt nicht: {werte}"


# --- #698: der Spielen-Knopf gehoert in die Karte ---

def test_ein_abzeichen_ausserhalb_eines_covers_bleibt_im_fluss(seite):
    """Die eigentliche Ursache, und sie reichte weiter als der eine Knopf. (#698)

    `.badge` war absolut positioniert, und die zweite `.badge`-Regel weiter unten setzte
    `position` nicht zurueck — sie gewann nur fuer Grund, Rahmen, Polsterung und
    Schriftgroesse. Gemessen: ein Abzeichen in einem Kasten bei (40,582) landete bei
    (6,6), also in der Bildschirmecke. Betroffen waren Bewertung, Jahr, Entwickler,
    Genres und die Achievements-Zeile — nicht nur der Knopf, ueber den es auffiel.
    """
    werte = seite.evaluate("""() => {
      const h = document.createElement('div');
      h.style.cssText = 'margin:40px;padding:20px';
      h.innerHTML = 'davor <span class=badge id=p698>★ 8.4</span> danach';
      document.body.appendChild(h);
      const b = document.getElementById('p698');
      const r = b.getBoundingClientRect(), e = h.getBoundingClientRect();
      const out = {position: getComputedStyle(b).position,
                   dx: Math.abs(r.x - e.x), dy: Math.abs(r.y - e.y)};
      h.remove();
      return out;
    }""")
    assert werte["position"] != "absolute", \
        "ein Abzeichen ausserhalb eines Covers ist absolut positioniert"
    assert werte["dx"] < 200 and werte["dy"] < 200, \
        f"das Abzeichen sitzt {werte['dx']:.0f}/{werte['dy']:.0f} px neben seinem Kasten"


def test_das_cover_abzeichen_bleibt_dagegen_absolut(seite):
    """Die Gegenprobe: dort ist die absolute Lage GEWOLLT. (#698)

    Ohne sie laege die Plattformmarke nicht mehr oben links auf dem Cover, sondern
    schoebe das Bild auseinander. Eine Reparatur, die das mitnimmt, waere keine.
    """
    werte = seite.evaluate("""() => {
      const c = document.createElement('div');
      c.className = 'cover'; c.style.cssText = 'position:relative;width:120px;height:160px';
      c.innerHTML = '<span class=badge id=p698c>SNES</span>';
      document.body.appendChild(c);
      const b = document.getElementById('p698c');
      const out = {position: getComputedStyle(b).position,
                   oben: b.getBoundingClientRect().y - c.getBoundingClientRect().y};
      c.remove();
      return out;
    }""")
    assert werte["position"] == "absolute", "die Plattformmarke liegt nicht mehr auf dem Cover"
    assert abs(werte["oben"] - 6) < 2, f"sie sitzt {werte['oben']:.0f} px von oben statt 6"


def test_der_spielen_knopf_liegt_in_der_karte(seite):
    """Jens: „oben links steht ‚Im Browser spielen'". (#698)

    Gemessen war der Knopf bei (6,6), sein Platz `#mplay` bei (892,529) — 900 px daneben,
    quer ueber der Navigationsleiste. Geprueft wird deshalb die LAGE, nicht das Markup:
    Der Knopf muss innerhalb der Karte liegen, sonst ist es egal, welche Klasse er traegt.
    """
    lage = seite.evaluate("""() => {
      const box = document.createElement('div');
      box.className = 'box'; box.style.cssText = 'margin:60px;padding:20px';
      box.innerHTML = '<div id=mplay698><a class=spielknopf href="#">▶ spielen</a></div>';
      document.body.appendChild(box);
      const k = box.querySelector('.spielknopf');
      const r = k.getBoundingClientRect(), b = box.getBoundingClientRect();
      const out = {position: getComputedStyle(k).position,
                   drin: r.x >= b.x - 1 && r.y >= b.y - 1
                         && r.right <= b.right + 1 && r.bottom <= b.bottom + 1};
      box.remove();
      return out;
    }""")
    assert lage["position"] != "absolute", "der Knopf ist wieder absolut positioniert"
    assert lage["drin"], "der Knopf liegt ausserhalb der Karte"


def test_loadplay_baut_den_knopf_wirklich_in_den_fluss(seite):
    """Ein nachgebautes Element beweist nichts ueber die echte Stelle. (#698)

    Ein Mutationstest hat es gezeigt: `class=badge` zurueck an den Spielen-Knopf gelegt,
    und die drei Lagepruefungen blieben gruen — sie bauten sich ihr Element selbst.
    Hier laeuft `loadPlay` wirklich, mit verdrahteter Antwort, und geprueft wird, was
    danach im Dokument steht.
    """
    seite.route("**/api/play*", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='{"playable":true,"url":"http://example.invalid/spielen"}'))
    lage = seite.evaluate("""async () => {
      // Der Kasten, in den loadPlay schreibt, samt Umgebung wie in der Detailkarte.
      const box = document.createElement('div');
      box.className = 'box'; box.style.cssText = 'margin:60px;padding:20px';
      box.innerHTML = '<div id=mplay></div>';
      document.body.appendChild(box);
      await loadPlay({title: 'Probe', platform_slug: 'snes'});
      const k = box.querySelector('#mplay a');
      const out = k ? {
        klassen: k.className,
        position: getComputedStyle(k).position,
        drin: (() => { const r = k.getBoundingClientRect(), b = box.getBoundingClientRect();
               return r.x >= b.x - 1 && r.y >= b.y - 1; })(),
      } : null;
      box.remove();
      return out;
    }""")
    assert lage, "loadPlay hat keinen Knopf gebaut — die Attrappe greift nicht"
    assert "badge" not in lage["klassen"], \
        f"der Knopf traegt wieder die Cover-Abzeichen-Klasse: {lage['klassen']!r}"
    assert lage["position"] != "absolute", "der Knopf ist absolut positioniert"
    assert lage["drin"], "der Knopf liegt ausserhalb seines Kastens"


def test_warnung_und_fehler_haben_in_jedem_design_genug_kontrast(seite):
    """Gemessen, nicht geschaetzt — wie bei --ok in #660. (#703)

    Zwei Bedingungen zugleich: Der Ton muss gegen den Kartengrund lesbar sein (4,5:1),
    UND er muss sich vom Akzent unterscheiden lassen. Der Akzent ist der Download-Knopf;
    in Aurora ist er ein Orangerot, und dort lagen die naheliegenden Warn- und Fehlertoene
    mit Abstand 89 bzw. 102 zu dicht daran. Deshalb steht dort ein Gelb statt eines
    Bernsteins und ein Rosarot statt eines Orangerots.
    """
    werte = seite.evaluate("""(kontrast) => {
      const k = eval(kontrast);
      const abstand = (a, b) => { const z = s => s.match(/\\d+(\\.\\d+)?/g).slice(0,3).map(Number);
        const [x,y,w] = z(a), [p,q,r] = z(b);
        return Math.sqrt((x-p)**2 + (y-q)**2 + (w-r)**2); };
      const merk = document.documentElement.dataset.design, out = {};
      for (const d of ['', 'glass', 'clean', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const probe = document.createElement('div');
        document.body.appendChild(probe);
        const lies = v => { probe.style.color = `var(${v})`; return getComputedStyle(probe).color; };
        const cs = getComputedStyle(document.documentElement);
        probe.style.color = cs.getPropertyValue('--card').trim();
        const karte = getComputedStyle(probe).color;
        probe.style.color = cs.getPropertyValue('--acc').trim();
        const akzent = getComputedStyle(probe).color;
        out[d || 'seerr'] = {
          warn:   [k(lies('--warn'), karte),   abstand(lies('--warn'), akzent)],
          bad:    [k(lies('--bad'), karte),    abstand(lies('--bad'), akzent)],
          warnbg: k('rgb(255,255,255)', lies('--warn-bg')),
          errbg:  k('rgb(255,255,255)', lies('--err-bg')),
        };
        probe.remove();
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return out;
    }""", _kontrast_js())
    for design, w in werte.items():
        assert w["warn"][0] >= 4.5, f"{design}: --warn nur {w['warn'][0]:.2f}:1 gegen die Karte"
        assert w["bad"][0] >= 4.5, f"{design}: --bad nur {w['bad'][0]:.2f}:1 gegen die Karte"
        assert w["warnbg"] >= 4.5, f"{design}: weiss auf --warn-bg nur {w['warnbg']:.2f}:1"
        assert w["errbg"] >= 4.5, f"{design}: weiss auf --err-bg nur {w['errbg']:.2f}:1"
        assert w["warn"][1] >= 110, \
            f"{design}: --warn liegt nur {w['warn'][1]:.0f} vom Akzent entfernt"
        assert w["bad"][1] >= 110, \
            f"{design}: --bad liegt nur {w['bad'][1]:.0f} vom Akzent entfernt"


def test_der_auftragszaehler_faerbt_sich_bei_fehlern(seite):
    """Ob zwei Variablen verschieden AUSSEHEN, sieht man nicht im Quelltext. (#703/#198)

    Der Quelltexttest kann nur pruefen, dass die beiden Zweige verschieden geschrieben
    sind. Ob `var(--err-bg)` und `var(--ok-bg)` im Aufbau auch verschiedene Farben ergeben
    — und ob sie ueberhaupt gesetzt sind — entscheidet erst der Browser.
    """
    werte = seite.evaluate("""() => {
      const merk = document.documentElement.dataset.design, out = {};
      for (const d of ['', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const p = document.createElement('span'); document.body.appendChild(p);
        const lies = v => { p.style.background = `var(${v})`;
                            return getComputedStyle(p).backgroundColor; };
        out[d || 'seerr'] = {fehler: lies('--err-bg'), normal: lies('--ok-bg')};
        p.remove();
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return out;
    }""")
    for design, w in werte.items():
        assert "rgba(0, 0, 0, 0)" not in w["fehler"], f"{design}: --err-bg ist nicht gesetzt"
        assert "rgba(0, 0, 0, 0)" not in w["normal"], f"{design}: --ok-bg ist nicht gesetzt"
        assert w["fehler"] != w["normal"], \
            f"{design}: Fehler und Normalfall haben dieselbe Farbe {w['fehler']}"


def test_der_zurueckhaltende_knopf_hebt_sich_von_der_karte_ab(seite):
    """`--btn2` ist eine neue Rolle, und sie muss sichtbar sein. (#705)

    Dialoge und Karten liegen selbst auf `--card`. Ein Knopf mit demselben Grund waere
    dort unsichtbar — genau deshalb stand im JavaScript ueberall ein helleres `#2a2f37`.
    Die Rolle gab es also schon, nur ohne Namen und nur in den Werten des Standard-
    Designs. Geprueft wird beides: Der Knopf muss sich vom Kartengrund abheben UND seine
    Schrift tragen.
    """
    werte = seite.evaluate("""() => {
      const merk = document.documentElement.dataset.design, out = {};
      const zahl = s => s.match(/\\d+(\\.\\d+)?/g).slice(0,3).map(Number);
      for (const d of ['', 'glass', 'clean', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const p = document.createElement('span'); document.body.appendChild(p);
        const lies = v => { p.style.background = `var(${v})`;
                            return getComputedStyle(p).backgroundColor; };
        const btn2 = lies('--btn2'), card = lies('--card');
        p.style.color = 'var(--txt)'; const txt = getComputedStyle(p).color;
        out[d || 'seerr'] = {btn2, card, txt,
          abstand: Math.hypot(...zahl(btn2).map((v,i) => v - zahl(card)[i]))};
        p.remove();
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return out;
    }""")
    for design, w in werte.items():
        assert "rgba(0, 0, 0, 0)" not in w["btn2"], f"{design}: --btn2 ist nicht gesetzt"
        assert w["btn2"] != w["card"], \
            f"{design}: der Knopf hat denselben Grund wie die Karte — er ist unsichtbar"
        assert w["abstand"] >= 8, \
            f"{design}: Knopf und Karte liegen nur {w['abstand']:.0f} auseinander"
    # UND JE DESIGN EIN EIGENER WERT. Ein Mutationstest hat gezeigt, dass „ist gesetzt"
    # hier nichts beweist: CSS-Variablen fallen auf `:root` zurueck. Faellt `--btn2` aus
    # einem Design heraus, ist sie weiterhin gesetzt — nur mit dem Wert des
    # Standard-Designs, und genau das war der Zustand, den #705 beseitigt hat.
    werte_je_design = {w["btn2"] for w in werte.values()}
    assert len(werte_je_design) == 4, \
        f"nicht jedes Design hat einen eigenen Knopfgrund: {werte_je_design}"


def test_alle_designs_setzen_die_neutralen_rollen(seite):
    """Was das JavaScript benutzt, muss jedes Design auch liefern. (#705)

    111 Vorkommen wurden auf `--txt`, `--mut`, `--input`, `--card`, `--btn2`, `--border`
    und `--acc` umgestellt. Fehlt eine davon in einem Design, faellt die Farbe still auf
    den Erbwert zurueck — und niemand sieht es, weil heute alle vier Designs dunkel sind.
    """
    fehlend = seite.evaluate("""() => {
      const merk = document.documentElement.dataset.design, raus = [];
      for (const d of ['', 'glass', 'clean', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const cs = getComputedStyle(document.documentElement);
        for (const n of ['--txt','--mut','--input','--card','--btn2','--border','--acc',
                         '--acc2','--hover'])
          if (!cs.getPropertyValue(n).trim()) raus.push(`${d || 'seerr'}: ${n}`);
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return raus;
    }""")
    assert not fehlend, "diese Variablen fehlen: " + ", ".join(fehlend)


def test_die_verweisfarbe_traegt_auf_dem_dunkelsten_grund(seite):
    """Der Akzent ist eine KNOPFFARBE, keine Schriftfarbe. (#705)

    Beim Umstellen legte ich die Verweise auf `--acc` — naheliegend, und in drei von vier
    Designs auch richtig. In Seerr ergab das `#7c5cff` auf `#0f1114` und damit **4,35:1**
    gegen die geforderten 4,5. Gefunden hat es die Barrierefreiheitspruefung, nicht ich;
    dieser Test macht die Bedingung ausdruecklich, damit sie nicht wieder still verrutscht.

    Geprueft wird gegen den DUNKELSTEN Grund, auf dem Verweise vorkommen — die Fusszeile —
    und zusaetzlich gegen die Karte.
    """
    werte = seite.evaluate("""(kontrast) => {
      const k = eval(kontrast);
      const merk = document.documentElement.dataset.design, out = {};
      for (const d of ['', 'glass', 'clean', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const p = document.createElement('span'); document.body.appendChild(p);
        const lies = (eig, v) => { p.style[eig] = `var(${v})`;
          return getComputedStyle(p)[eig === 'color' ? 'color' : 'backgroundColor']; };
        out[d || 'seerr'] = {
          fuss:  k(lies('color', '--link'), lies('background', '--topbar')),
          karte: k(lies('color', '--link'), lies('background', '--card')),
        };
        p.remove();
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return out;
    }""", _kontrast_js())
    for design, w in werte.items():
        assert w["fuss"] >= 4.5, \
            f"{design}: Verweis auf der Fusszeile nur {w['fuss']:.2f}:1"
        assert w["karte"] >= 4.5, \
            f"{design}: Verweis auf der Karte nur {w['karte']:.2f}:1"


# --- #708: die drei Knoepfe auf der Detailkarte ---

def _detailkarte_oeffnen(seite):
    """Eine Detailkarte oeffnen, ohne von einer echten Suche abzuhaengen."""
    seite.route("**/api/search*", lambda route: route.fulfill(
        status=200, content_type="application/json",
        headers={"X-Platform-Hidden": "0"},
        body='[{"title":"Probe","platform":"snes","platform_slug":"snes","source":"archive",'
             '"size":524288,"ref":"p708","cover":"","gkey":"probe","in_library":false,'
             '"grp_in_library":false,"is_set":false,"variant":{},"variant_label":""}]'))
    seite.evaluate("() => { SELP = new Set(); localStorage.setItem('romp','[]'); }")
    seite.locator("#q").fill("Probe")
    seite.press("#q", "Enter")
    for _ in range(60):
        if seite.locator("#grid .card").count(): break
        seite.wait_for_timeout(200)
    seite.locator("#grid .card .t").first.click()
    seite.wait_for_timeout(1200)


def test_die_drei_knoepfe_der_detailkarte_stimmen_ueberein(seite):
    """Zwei trugen ihre Gestaltung inline, einer kam aus dem Stylesheet. (#708)

    In Aurora unterschieden sie sich damit in Grund, Schriftfarbe UND Eckenradius.
    Gemessen: `rgb(38,32,47)`/`#fff`/6px gegen `rgb(42,47,55)`/`rgb(230,232,236)`/12px.

    Und der Befund ging andersherum aus als erwartet: Aurora rundet jeden Knopf auf 12 px;
    weil INLINE jede Designregel schlaegt, folgte ausgerechnet der Favoriten-Knopf dem
    Design und die beiden anderen ignorierten es.
    """
    _detailkarte_oeffnen(seite)
    werte = seite.evaluate("""() => {
      const merk = document.documentElement.dataset.design, out = {};
      for (const d of ['', 'glass', 'clean', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const k = [...document.querySelectorAll('#modal .kartenknopf')];
        out[d || 'seerr'] = k.map(e => { const c = getComputedStyle(e);
          return [c.backgroundColor, c.color, c.borderRadius]; });
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return out;
    }""")
    for design, knoepfe in werte.items():
        assert len(knoepfe) == 3, f"{design}: {len(knoepfe)} Knoepfe statt 3"
        einzig = {tuple(k) for k in knoepfe}
        assert len(einzig) == 1, \
            f"{design}: die drei Knoepfe sehen verschieden aus — {einzig}"
    # ... und sie muessen sich JE DESIGN unterscheiden, sonst haengen sie wieder fest.
    assert len({tuple(v[0]) for v in werte.values()}) == 4, \
        f"die Knoepfe sehen in allen Designs gleich aus: {werte}"


def test_der_favoriten_umschalter_behaelt_sein_zeichen(seite):
    """DIE FALLE AUS #337, in ihrer dritten Form. (#708)

    `toggleFav` setzte `btn.textContent` — das loescht jedes Kind. Ein Zeichen im Knopf
    waere beim ersten Klick verschwunden, und zwar lautlos: Der Text stimmt danach, nur
    das Zeichen fehlt. Genau so haben Abdeckung und Bibliothek 2024 ihre Symbole verloren.
    """
    _detailkarte_oeffnen(seite)
    seite.route("**/api/favourites*", lambda route: route.fulfill(
        status=200, content_type="application/json", body='{"ok":true}'))
    vorher = seite.evaluate("""() => {
      const b = document.getElementById('favbtn');
      return {zeichen: b.querySelectorAll('svg').length,
              kennung: (b.querySelector('use')||{}).getAttribute?.('href'),
              text: (b.querySelector('span')||{}).textContent};
    }""")
    assert vorher["zeichen"] == 1, "der Knopf traegt schon vor dem Klick kein Zeichen"
    seite.locator("#favbtn").click()
    seite.wait_for_timeout(900)
    nachher = seite.evaluate("""() => {
      const b = document.getElementById('favbtn');
      return {zeichen: b.querySelectorAll('svg').length,
              kennung: (b.querySelector('use')||{}).getAttribute?.('href'),
              text: (b.querySelector('span')||{}).textContent,
              an: b.classList.contains('on')};
    }""")
    assert nachher["zeichen"] == 1, "nach dem Klick ist das Zeichen weg (textContent-Falle)"
    assert nachher["text"] == vorher["text"], "die Beschriftung hat sich veraendert"
    assert nachher["kennung"] != vorher["kennung"], \
        f"das Zeichen wechselt nicht mit dem Zustand: bleibt {nachher['kennung']}"
    assert nachher["an"], "der Knopf traegt den Zustand nicht"


def test_kein_schriftzeichen_mehr_in_den_drei_knoepfen(seite):
    """Zeichen aus der Systemschrift, wie in #658 abgeschafft. (#708)"""
    import re
    _detailkarte_oeffnen(seite)
    texte = seite.evaluate(
        "() => [...document.querySelectorAll('#modal .kartenknopf')].map(e => e.textContent)")
    assert len(texte) == 3
    for t in texte:
        treffer = re.findall(r"[\U0001F300-\U0001FAFF♠-♧❤♡♥☆★]", t)
        assert not treffer, f"Schriftzeichen {treffer} steht noch in {t.strip()!r}"


# --- #710: die Fusszeile in Aurora ---

def test_die_fusszeile_laesst_in_keinem_design_einen_streifen_frei(seite):
    """Jens: die Fussleiste ist nicht durchgehend, sondern abgeschnitten. (#710)

    Gemessen bei 1611 px: In Seerr, Glas und Klar beginnt sie bei 210 — genau dort, wo die
    Seitenleiste endet, also richtig. In Aurora ist die Navigation eine Zeile OBEN, es gibt
    gar keine linke Spalte — und die Fusszeile hielt trotzdem ihren Abstand von 210 px ein.
    Links blieb ein Streifen frei, durch den der Inhalt scrollte.

    Geprueft wird die Zusage, nicht die Zahl: Die Leiste beginnt entweder am Fensterrand
    oder genau dort, wo die Seitenleiste endet. Einen dritten Fall darf es nicht geben.
    """
    werte = seite.evaluate("""() => {
      const merk = document.documentElement.dataset.design, out = {};
      for (const d of ['', 'glass', 'clean', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const f = document.getElementById('fuss').getBoundingClientRect();
        const s = document.getElementById('side').getBoundingClientRect();
        out[d || 'seerr'] = {fuss: Math.round(f.left), rechts: Math.round(f.right),
                             spalte: Math.round(s.right), fenster: Math.round(window.innerWidth),
                             // Eine SPALTE ist sie nur, wenn sie nicht die ganze Breite fuellt
                             ist_spalte: Math.round(s.width) < Math.round(window.innerWidth) - 40};
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return out;
    }""")
    for design, w in werte.items():
        soll = w["spalte"] if w["ist_spalte"] else 0
        assert w["fuss"] == soll, (
            f"{design}: die Fusszeile beginnt bei {w['fuss']}, erwartet {soll} "
            f"({'neben der Spalte' if w['ist_spalte'] else 'am Fensterrand'}) — "
            f"{w['fuss'] - soll} px bleiben frei")
        assert w["rechts"] == w["fenster"], \
            f"{design}: die Fusszeile endet bei {w['rechts']}, das Fenster bei {w['fenster']}"


def test_der_inhalt_beginnt_wo_die_navigation_endet(seite):
    """Die dritte Stelle, die dieselbe Breite annimmt. (#710)

    `--navspalte` steht an drei Stellen: `#side`, `main` und `#fuss`. Der Fehler aus #710
    war, dass eine davon beim Umbau vergessen wurde. Ein Mutationstest hat gezeigt, dass
    `main` gar nicht geprueft war — bricht dort der Abstand weg, verschwindet der Inhalt
    unter der Seitenleiste, und kein Test haette es gemerkt.
    """
    werte = seite.evaluate("""() => {
      const merk = document.documentElement.dataset.design, out = {};
      for (const d of ['', 'glass', 'clean', 'aurora']) {
        if (d) document.documentElement.dataset.design = d;
        else delete document.documentElement.dataset.design;
        const m = document.querySelector('main').getBoundingClientRect();
        const s = document.getElementById('side').getBoundingClientRect();
        out[d || 'seerr'] = {inhalt: Math.round(m.left), spalte: Math.round(s.right),
                             ist_spalte: Math.round(s.width) < Math.round(window.innerWidth) - 40};
      }
      if (merk) document.documentElement.dataset.design = merk;
      else delete document.documentElement.dataset.design;
      return out;
    }""")
    for design, w in werte.items():
        soll = w["spalte"] if w["ist_spalte"] else 0
        assert w["inhalt"] == soll, (
            f"{design}: der Inhalt beginnt bei {w['inhalt']}, erwartet {soll} — "
            f"er liegt {'unter der Seitenleiste' if w['inhalt'] < soll else 'zu weit rechts'}")


def test_die_ereignisauswahl_steht_im_profil_und_liest_sich_zurueck(seite):
    """Die Voreinstellung muss als AN erscheinen, nicht als AUS. (#714)

    Fehlt ein Schluessel, ist das Ereignis eingeschaltet — so verhaelt sich der Server.
    Zeigte die Oberflaeche stattdessen leere Kaesten, saehe „nicht eingestellt" wie
    „abgewaehlt" aus, und wer einmal speichert, schaltet ungewollt alles ab.
    """
    seite.evaluate("() => openProfile()")
    seite.wait_for_timeout(1800)
    zustand = seite.evaluate("""() => {
      const k = [...document.querySelectorAll('#evuser input[data-ev]')];
      return {anzahl: k.length, alle_an: k.every(x => x.checked),
              namen: k.map(x => x.dataset.ev)};
    }""")
    assert zustand["anzahl"] == 6, f"{zustand['anzahl']} Ereignisse statt 6"
    assert zustand["alle_an"], "ohne eigene Auswahl muessen alle Kaesten AN sein"
    assert "available" in zustand["namen"] and "message" in zustand["namen"], \
        f"die Ereignisse fehlen: {zustand['namen']}"

    # Abwaehlen und wieder auslesen — die Bauform muss zurueckliefern, was dasteht.
    gelesen = seite.evaluate("""() => {
      document.querySelector('#evuser input[data-ev="message"]').checked = false;
      return ereignisLesen('evuser');
    }""")
    assert gelesen["message"] is False, "das Abwaehlen kommt nicht an"
    assert gelesen["available"] is True, "ein anderes Ereignis wurde mitgenommen"
    seite.evaluate("() => closeModal()")


# --- #719: Cover erst laden, wenn sie gebraucht werden ---

# Ein winziges eingebettetes Bild: Die Testinstanz hat keine IGDB-Zugangsdaten, und ein
# Test, der dafuer ins Netz greift, misst das Netz. Fuer die Frage „wird das Cover
# gesetzt?" reicht ein Pixel.
_PIXEL = ("data:image/gif;base64,"
          "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")


def _entdecken_verdrahten(seite, reihen=20, je_reihe=20):
    import json as _j
    daten = [{"slug": f"p{r}", "key": f"c:p{r}", "console": f"Konsole {r}",
              "games": [{"title": f"Spiel {r}-{g}", "cover": _PIXEL,
                         "in_library": False, "ext_rating": None}
                        for g in range(je_reihe)]}
             for r in range(reihen)]
    seite.route("**/api/discover/rows*", lambda route: route.fulfill(
        status=200, content_type="application/json", body=_j.dumps(daten)))


def _entdecken_aufbauen(seite):
    # `loadDiscover()` DIREKT rufen, nicht ueber `show('s')`: Die Ansicht baut sich beim
    # Anmelden schon einmal auf, und zwar bevor die Attrappe steht. Ein zweiter Aufruf
    # holt die Reihen neu — jetzt aus der Attrappe.
    seite.evaluate("() => loadDiscover()")
    for _ in range(100):
        if seite.locator(".pcover").count(): break
        seite.wait_for_timeout(200)
    seite.wait_for_timeout(1500)


def test_die_startseite_laedt_nur_sichtbare_cover(seite):
    """440 Cover im Dokument, 48 auf dem Bildschirm. (#719)

    GEMESSEN AM LAUFENDEN STAND: Die Startseite baut 22 Reihen mit je 20 Titeln. Weil die
    Cover als CSS-HINTERGRUNDBILD eingebunden waren, konnte der Browser nichts aufschieben
    — `loading="lazy"` wirkt nur auf `<img>`. 240 Bilder zu je rund 400 ms wurden geholt,
    neun von zehn davon fuer niemanden; die Seite selbst stand nach 141 ms.

    Geprueft wird die Zusage, nicht die Zahl: Deutlich weniger Cover tragen beim Aufbau
    ein Bild, als im Dokument stehen — und die im sichtbaren Bereich tragen eines.
    """
    _entdecken_verdrahten(seite)
    _entdecken_aufbauen(seite)
    zahlen = seite.evaluate("""() => {
      const alle = [...document.querySelectorAll('.pcover')];
      const hat = e => !!e.style.backgroundImage && e.style.backgroundImage !== 'none';
      const sichtbar = alle.filter(e => { const r = e.getBoundingClientRect();
        return r.top < innerHeight && r.bottom > 0 && r.left < innerWidth && r.right > 0; });
      return {gesamt: alle.length, mit_bild: alle.filter(hat).length,
              sichtbar: sichtbar.length, sichtbar_mit_bild: sichtbar.filter(hat).length};
    }""")
    assert zahlen["gesamt"] > 100, f"nur {zahlen['gesamt']} Cover — der Test prueft nichts"
    assert zahlen["mit_bild"] < zahlen["gesamt"], \
        f"alle {zahlen['gesamt']} Cover tragen ein Bild — es wird nichts aufgeschoben"
    # Was man sieht, muss auch da sein. Ein Aufschub, der sichtbare Kaesten leer laesst,
    # ist keine Verbesserung, sondern ein Fehler.
    assert zahlen["sichtbar"] > 0, "nichts im Blick — der Test prueft nichts"
    assert zahlen["sichtbar_mit_bild"] >= zahlen["sichtbar"] * 0.8, \
        (f"nur {zahlen['sichtbar_mit_bild']} von {zahlen['sichtbar']} sichtbaren Covern "
         "tragen ein Bild — der Vorlauf reicht nicht")


def test_ein_cover_erscheint_beim_scrollen(seite):
    """Aufgeschoben heisst nicht weggelassen. (#719)"""
    _entdecken_verdrahten(seite)
    _entdecken_aufbauen(seite)
    ohne = seite.evaluate("""() => {
      const e = [...document.querySelectorAll('.pcover')].find(
        x => !x.style.backgroundImage || x.style.backgroundImage === 'none');
      if (!e) return null;
      e.id = 'probe719';
      return true;
    }""")
    assert ohne, "alle Cover trugen sofort ein Bild — dann schiebt nichts auf"
    seite.evaluate("() => document.getElementById('probe719').scrollIntoView()")
    seite.wait_for_timeout(2000)
    danach = seite.evaluate("""() => {
      const e = document.getElementById('probe719');
      return !!e.style.backgroundImage && e.style.backgroundImage !== 'none';
    }""")
    assert danach, "ein Cover blieb nach dem Scrollen leer — aufgeschoben statt geladen"


def test_spielen_und_streamen_warten_nicht_auf_die_detailabfrage(seite):
    """Sie brauchen nichts aus ihr. (#721)

    Gemessen am laufenden Stand: Der Dialog steht nach 2 ms, gefuellt ist er nach ~1,94 s.
    `/api/detail` brauchte 589 ms — und `play` (1330 ms), `stream` und `titlemeta`
    starteten erst DANACH, obwohl `play` und `stream` nur den angeklickten Treffer
    brauchen, der laengst vorliegt.

    `loadTitleMeta` bleibt bewusst hinten: Es nimmt `window._detname` aus genau dieser
    Antwort. Vorgezogen fiele es auf den Release-Namen zurueck, und daran haengen die
    Bewertungen — schneller und daneben ist nicht schneller.
    """
    reihenfolge = []

    # EINE FABRIK, KEIN `lambda route, w=weg`: Playwright sieht sich die Stelligkeit des
    # Handlers an und uebergibt einem zweiparametrigen `(route, request)` — der
    # Vorgabewert wurde dabei ueberschrieben, und in der Liste landeten Request-Objekte
    # statt der Namen.
    def horcher(name):
        def handler(route):
            reihenfolge.append(name)
            route.fulfill(status=200, content_type="application/json",
                          body='{"playable":false,"reason":"no_core","streamable":false,'
                               '"files":[],"name":"Probe"}')
        return handler
    for weg in ("detail", "play", "stream"):
        seite.route(f"**/api/{weg}?**", horcher(weg))
    seite.route("**/api/search*", lambda route: route.fulfill(
        status=200, content_type="application/json", headers={"X-Platform-Hidden": "0"},
        body='[{"title":"Probe","platform":"snes","platform_slug":"snes","source":"archive",'
             '"size":524288,"ref":"p721","cover":"","gkey":"p","in_library":false,'
             '"grp_in_library":false,"is_set":false,"variant":{},"variant_label":""}]'))
    seite.evaluate("() => { SELP = new Set(); localStorage.setItem('romp','[]'); }")
    seite.locator("#q").fill("Probe")
    seite.press("#q", "Enter")
    for _ in range(60):
        if seite.locator("#grid .card").count(): break
        seite.wait_for_timeout(200)
    reihenfolge.clear()
    seite.locator("#grid .card .t").first.click()
    seite.wait_for_timeout(2500)

    assert "play" in reihenfolge and "stream" in reihenfolge, \
        f"play/stream wurden gar nicht gerufen: {reihenfolge}"
    # STRENG: play muss VOR detail losgelaufen sein, nicht „ungefaehr gleichzeitig".
    # Ein Mutationstest hat gezeigt, wozu die weiche Fassung taugte: Mit sofort
    # antwortenden Attrappen sieht [detail, play, stream] genauso aus wie
    # [play, stream, detail], solange man nur „hoechstens eine Position spaeter" fordert.
    assert reihenfolge.index("play") < reihenfolge.index("detail"), \
        (f"play startete erst nach detail: {reihenfolge} — dann wartet es auf eine "
         "Antwort, aus der es nichts braucht")
    assert reihenfolge.index("stream") < reihenfolge.index("detail"), \
        f"stream startete erst nach detail: {reihenfolge}"
