"""Fixtures für die Browsertests: echter Anmeldeweg, Konsolenüberwachung.

WARUM ES DIESE EBENE BRAUCHT: Die Unit-Tests fassen `app` über den Flask-Testclient an.
Der rendert kein HTML, führt kein JavaScript aus und kennt weder Tastatur noch Adress-
zeile. Genau dort saßen sechs Fehler (#319-#324) in einem grünen Build. Ein Test, der die
Seite nie geladen hat, sagt nichts über die Seite.

WARUM DER ECHTE ANMELDEWEG: Eine frische Instanz hat keine Benutzer; `/api/setup` legt den
ersten an. Der Test geht diesen Weg statt eine Sitzung zu fälschen — sonst wäre die
Anmeldung selbst die einzige nie geprüfte Seite. Die Zugangsdaten unten gelten nur für die
Wegwerf-Instanz im Temp-Verzeichnis, die `live_server` aufspannt.

The unit tests drive `app` through the Flask test client, which renders no HTML, runs no
JavaScript and has neither a keyboard nor an address bar. Six defects lived there in a
green build. These fixtures add a real browser against the real login flow.
"""
import pytest

pytest.importorskip("playwright", reason="pytest-playwright nicht installiert")

@pytest.fixture
def seite(page, eingerichtet, zugangsdaten):
    """Eine angemeldete Seite mit geschlossener Einführungstour.

    WARUM DIE TOUR WEG MUSS: Sie ist ein Modal und fängt den Fokus — völlig korrekt für
    einen Dialog. Wer sie stehen lässt, misst aber nur noch sie: Ein erster Tastatur-
    durchlauf ergab „nichts auf der Seite erreichbar", und das stimmte auch — für den
    Dialog davor. Jede Aussage über die Seite dahinter setzt voraus, dass er zu ist.

    The onboarding tour is a modal and correctly traps focus. Left open, every keyboard
    measurement describes the dialog rather than the page behind it.
    """
    page.goto(f"{eingerichtet}/login", wait_until="domcontentloaded")
    nutzer, passwort = zugangsdaten
    page.fill("#u", nutzer)
    page.fill("#p", passwort)
    page.click("#btn")
    page.wait_for_url("**/#/**", timeout=15000)
    page.wait_for_timeout(800)
    for _ in range(6):
        knopf = page.get_by_role("button", name="Überspringen")
        if knopf.count() == 0:
            break
        knopf.first.click()
        page.wait_for_timeout(300)
    return page


@pytest.fixture
def bibliothek_gefuellt(servermod, seite):
    """Legt ein paar Titel in den Index, damit die Bibliotheksansicht Zeilen hat.

    WARUM DAS NÖTIG IST — und was ohne diese Fixture passiert ist: Der Tastaturtest für
    die Bibliothek suchte anklickbare `div`s und fand auf der leeren Testinstanz keine.
    Er BESTAND also, obwohl der Fehler nachweislich da ist — inhaltsleer wahr. Der
    `xfail(strict=True)` deckte das auf, indem er als XPASS anschlug; ohne ihn wäre eine
    Prüfung in die Suite gewandert, die nie etwas gefunden hätte.

    Die Zeilen kommen über `save_index_to_db`, nicht über einen Scan echter Ordner: Der
    Test soll die ANSICHT prüfen, nicht das Einlesen des Dateisystems.

    Without seeded data the library view has no rows, so the keyboard test found nothing
    and passed vacuously. The strict xfail exposed that as an XPASS.
    """
    per = {"snes": {"super mario world", "chrono trigger"},
           "nes": {"super mario bros 3"}}
    namen = {("snes", "super mario world"): "Super Mario World",
             ("snes", "chrono trigger"): "Chrono Trigger",
             ("nes", "super mario bros 3"): "Super Mario Bros. 3"}
    alle = {n for s in per.values() for n in s}
    servermod.save_index_to_db(per, alle, set(per), 1, namen)
    servermod.load_index_from_db()
    seite.reload(wait_until="domcontentloaded")
    seite.wait_for_timeout(800)
    for _ in range(6):
        knopf = seite.get_by_role("button", name="Überspringen")
        if knopf.count() == 0:
            break
        knopf.first.click()
        seite.wait_for_timeout(300)
    return seite


def menuepunkt(seite, name):
    """Ein Menüpunkt der Seitenleiste, unabhängig davon, ob er eine Rolle hat.

    WARUM NICHT `get_by_role("link")`: Die Einträge sind `<a>` OHNE `href` und haben damit
    keine Rolle — `get_by_role` findet sie nicht (#329). Ein Test, der sich darauf stützt,
    überspringt sich selbst und meldet trotzdem Grün. Genau das ist hier zuerst passiert:
    fünf stille `skip`s in einem grün aussehenden Lauf.

    Sobald #329 behoben ist, findet dieser Selektor die Einträge weiterhin.
    """
    return seite.locator("a.nav, button.nav").filter(has_text=name).first


@pytest.fixture
def konsolenfehler(page):
    """Sammelt Konsolenfehler und ungefangene Ausnahmen der Seite.

    Muss VOR dem ersten `goto` greifen, sonst entgehen ihm die Fehler beim Laden —
    deshalb ein eigenes Fixture statt einer Prüfung am Testende.
    """
    fehler = []
    page.on("console",
            lambda m: fehler.append(f"{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: fehler.append(f"pageerror: {e}"))
    return fehler


@pytest.fixture
def anfrage_vorhanden(servermod, seite):
    """Legt eine Anfrage an, damit die Anfragenliste eine Zeile hat.

    WARUM: Ohne sie übersprang der Test für #390 sich selbst — auf der leeren Testinstanz
    gibt es keine Anfrage, also nichts zu klicken. Ein übersprungener Test ist ein Test,
    der nichts sagt, und genau dieselbe Falle hat schon `bibliothek_gefuellt` nötig
    gemacht: Der Tastaturtest der Bibliothek bestand inhaltsleer.

    Ohne Fixture bewiese der Klicktest nur, dass die Seite sich öffnen lässt.
    """
    job = servermod.new_job({"title": "Super Mario World", "source": "archive",
                             "ref": "probe", "platform_slug": "snes", "size": 1},
                            user="admin", approved=False)
    seite.reload()
    seite.wait_for_timeout(400)
    return job
