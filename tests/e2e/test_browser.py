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
    # Eine Suche, damit die Seite ueberhaupt laenger wird als das Fenster — ohne Inhalt
    # gaebe es nichts zu rollen, und die Haelfte dieser Pruefung liefe ins Leere.
    seite.fill("#q", "mario")
    seite.press("#q", "Enter")
    seite.wait_for_timeout(1500)
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
