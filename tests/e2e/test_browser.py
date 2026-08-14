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
