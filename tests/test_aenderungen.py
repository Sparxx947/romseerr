"""Smoke-Tests / smoke tests für Romseerr.

Prüfen Verhalten (nicht nur Syntax): Health, Titel-Normalisierung/Dedup, Bibliotheks-Index,
Sperrliste, Setup-/Login-Fluss und dass das eingebettete JavaScript gültig ist.
"""
import ast
import json
import os
import yaml
import re
import urllib.parse
import sys
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from hilfen import (  # noqa: F401  gemeinsam genutzt (#505)
    ADMIN_FIX,
    ANSICHTEN_OHNE_BROWSERTEST,
    DATEI_SPEICHER,
    DOC_EN_BODEN,
    DOC_ROUTEN_OHNE,
    HYDRA_SAMPLE,
    REPO,
    ZWEISPRACHIG_IN_EINEM_STUECK,
    _3ds_datei,
    _DE_WORTE,
    _EN_WORTE,
    _Protokoll,
    _admin,
    _als,
    _cia_datei,
    _doc_bloecke,
    _doc_dateien,
    _hat_englisch,
    _index_mit_protokoll,
    _index_zurueck,
    _js,
    _lege_titel_an,
    _mit_index,
    _nsp_datei,
    _readme_ueberschriften,
    _route_funktionen,
    _routen_und_ansichten,
    _seed_catalog,
    _seed_ra,
    _staging,
    _stream_ready,
    _unlesbar_machen,
    _workflow,
    i18n_hat,
    sprachtabellen,
)



"""Pruefungen zu den Aenderungen vom 2026-08-14/15.

Ausgelagert aus `test_smoke.py`, weil die Datei die Repo-Grenze von 512 kB
ueberschritten hat (`scripts/check_content_policy.py`). Die Fixtures kommen
weiterhin aus `conftest.py`, die Hilfen aus `hilfen.py` — beides gilt
dateiuebergreifend, es musste nichts dupliziert werden.
"""

# --- #649: Endung aus der Dateikennung ersetzt die falsche, statt sich anzuhängen -------

def test_ziel_mit_endung_replaces_a_wrong_extension(appmod):
    """`Portal.2.NSW.VENOM.hdf` wird `…VENOM.nsp`, nicht `…VENOM.hdf.nsp`. (#649)

    Der angehängte Rest blieb im Namen und damit im Dedup-Schlüssel — dieselbe Datei aus
    einer Quelle ohne Verschleierung galt als neu.
    """
    assert appmod.ziel_mit_endung("Portal.2.NSW.VENOM.hdf", "nsp") == "Portal.2.NSW.VENOM.nsp"
    assert appmod.ziel_mit_endung("Game.bin", "nsp") == "Game.nsp"
    assert appmod.ziel_mit_endung("Marble.Master.mdf", "xci") == "Marble.Master.xci"


def test_ziel_mit_endung_keeps_names_that_only_look_like_extensions(appmod):
    """Die Grenzen sind an echten Namen der Bibliothek gemessen, nicht geschätzt. (#649)

    Ein einzelner Buchstabe hinter einem Punkt ist in 17 Titeln Teil des Namens
    (`H.E.R.O`, `I.C.U.P.S`, `H.A.T.E`), und eine Zahl dahinter ist eine Versionsangabe.
    Beides darf nicht als Endung gelten — sonst kostet der Fix mehr, als er einbringt.
    """
    # Einzelbuchstabe: echte Titel aus der Bibliothek
    assert appmod.ziel_mit_endung("H.E.R.O", "nsp") == "H.E.R.O.nsp"
    assert appmod.ziel_mit_endung("I.C.U.P.S", "nsp") == "I.C.U.P.S.nsp"
    # Versions- und Zählnummern
    assert appmod.ziel_mit_endung("Spiel v1.0", "nsp") == "Spiel v1.0.nsp"
    assert appmod.ziel_mit_endung("AGS_Mini.7z.001", "nsp") == "AGS_Mini.7z.001.nsp"
    # gar kein Punkt
    assert appmod.ziel_mit_endung("crom0 (32)", "nsp") == "crom0 (32).nsp"
    # zu lang für eine Endung
    assert appmod.ziel_mit_endung("Sammlung.komplett", "nsp") == "Sammlung.komplett.nsp"
    # bereits die richtige Endung — nichts zu ersetzen, nichts zu doppeln
    assert appmod.ziel_mit_endung("Spiel.nsp", "nsp") == "Spiel.nsp.nsp"


def test_the_import_uses_the_replacing_form(appmod):
    """Die Funktion muss auch aufgerufen werden. (#649)

    Sie stand fertig da, während `import_folder` weiter `f"{fn}.{ext}"` baute — genau so
    bleibt ein Fix ausgeliefert und wirkungslos.
    """
    quelle = open(os.path.join(REPO, "app.py"), encoding="utf-8").read()
    m = re.search(r"ext = rom_endung_aus_inhalt\(src\)(.*?)\n            if not ext:", quelle, re.S)
    assert m, "die Stelle im Import ist nicht mehr auffindbar"
    zweig = m.group(1)
    assert "ziel_mit_endung(fn, ext)" in zweig, "der Import hängt die Endung weiterhin selbst an"
    assert 'ziel = f"{fn}.{ext}"' not in zweig, "die alte, anhängende Form steht noch da"


def test_the_replacement_actually_fixes_the_dedup_key(appmod):
    """Der Zweck der Änderung, gemessen am echten `norm()`. (#649)

    Ohne sie lieferte `Portal.2.NSW.VENOM.hdf.nsp` den Schlüssel „portal 2 venom hdf":
    der Rest verhinderte, dass die Gruppenkürzel-Regel griff, denn die verlangt das Kürzel
    am Namensende. 7,3 GB wären ein zweites Mal geholt worden.
    """
    vorher = appmod.norm("Portal.2.NSW.VENOM.hdf.nsp")
    nachher = appmod.norm(appmod.ziel_mit_endung("Portal.2.NSW.VENOM.hdf", "nsp"))
    sauber = appmod.norm("Portal 2 (Switch).nsp")
    assert vorher != sauber, f"Ausgangslage stimmt nicht mehr: {vorher!r} == {sauber!r}"
    assert nachher == sauber, f"der Schlüssel passt immer noch nicht: {nachher!r} != {sauber!r}"


# --- #656: was in `.unsortiert` liegt, wird sichtbar -----------------------------------

def test_unsortiert_lists_what_the_import_could_not_place(appmod, tmp_path, monkeypatch):
    """Ordner UND Einzeldateien, mit Größe, Anzahl und Alter. (#656)"""
    roms = tmp_path / "roms"; (roms / ".unsortiert").mkdir(parents=True)
    monkeypatch.setattr(appmod, "ROMS", str(roms))
    ordner = roms / ".unsortiert" / "mario-kart-8-bruchstuecke"; ordner.mkdir()
    (ordner / "Audio.bin").write_bytes(b"x" * 400)
    (ordner / "Course.bin").write_bytes(b"y" * 600)
    (roms / ".unsortiert" / "einzeln.bin").write_bytes(b"z" * 100)

    e = {x["name"]: x for x in appmod.unsortiert_eintraege()}
    assert set(e) == {"mario-kart-8-bruchstuecke", "einzeln.bin"}, e
    assert e["mario-kart-8-bruchstuecke"]["is_dir"] is True
    assert e["mario-kart-8-bruchstuecke"]["size"] == 1000
    assert e["mario-kart-8-bruchstuecke"]["files"] == 2
    assert e["einzeln.bin"]["is_dir"] is False and e["einzeln.bin"]["size"] == 100


def test_unsortiert_is_read_only(appmod, tmp_path, monkeypatch):
    """Anschauen, nicht anfassen. (#656)

    Was hier liegt, konnte niemand zuordnen — eine Plattform dafür zu raten ist genau das,
    wovor dieser Ordner bewahrt. Die Ansicht darf deshalb nichts verschieben und nichts
    löschen, und es darf auch keinen Endpunkt dafür geben.
    """
    roms = tmp_path / "roms"; (roms / ".unsortiert").mkdir(parents=True)
    monkeypatch.setattr(appmod, "ROMS", str(roms))
    datei = roms / ".unsortiert" / "bleibt.bin"; datei.write_bytes(b"x" * 10)
    appmod.unsortiert_eintraege()
    assert datei.exists() and datei.read_bytes() == b"x" * 10, "das Auflisten hat angefasst"

    pfade = {str(r) for r in appmod.app.url_map.iter_rules()}
    schreibend = [p for p in pfade if "unsortiert" in p and p != "/api/unsortiert"]
    assert not schreibend, f"es gibt schreibende Endpunkte dafür: {schreibend}"
    regel = next(r for r in appmod.app.url_map.iter_rules() if str(r) == "/api/unsortiert")
    assert set(regel.methods) <= {"GET", "HEAD", "OPTIONS"}, f"nicht nur lesend: {regel.methods}"


def test_unsortiert_endpoint_needs_permission(appmod, client):
    """Der Ordner nennt Pfade und Dateinamen. (#656)"""
    appmod.save_users({**ADMIN_FIX, "g": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "g"; sess["role"] = "user"
    assert client.get("/api/unsortiert").status_code == 403
    appmod.save_users({})


def test_unsortiert_survives_a_missing_folder(appmod, tmp_path, monkeypatch):
    """Ohne den Ordner eine leere Liste, kein Fehler. (#656)"""
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path / "gibtsnicht"))
    assert appmod.unsortiert_eintraege() == []


def test_the_maintenance_view_actually_shows_it(appmod):
    """Die Funktion muss auch aufgerufen und eingebaut werden. (#656)"""
    js = _js()
    m = re.search(r"async function secMaint\(c\)\{(.*?)\n(?=async function |function )", js, re.S)
    assert m, "secMaint nicht gefunden"
    koerper = m.group(1)
    assert "id=unslist" in koerper, "der Abschnitt fehlt in der Wartungsansicht"
    assert "loadUnsortiert()" in koerper, "die Liste wird nie geladen"
    lade = re.search(r"async function loadUnsortiert\(\)\{(.*?)\n\}", js, re.S)
    assert lade and "/api/unsortiert" in lade.group(1), "die Funktion fragt den Endpunkt nicht"
    for schluessel in ("uns_title", "uns_hint", "uns_none", "uns_count"):
        assert i18n_hat(schluessel), f"{schluessel} fehlt in einer Sprache"


def test_counted_strings_do_not_glue_a_number_to_a_plural_noun(appmod):
    """„1 Einträge" — richtig für jede Zahl außer eins, und eins ist der Normalfall. (#675)

    Statt Singular- und Pluralformen in fünf Sprachen zu pflegen, steht die Zahl hinter dem
    Substantiv: „Einträge: 1". Das stimmt für jede Anzahl und übersteht auch die nächste
    Sprache, ohne dass jemand ihre Pluralregeln kennen muss.
    """
    for sprache, tabelle in sprachtabellen().items():
        wert = tabelle.get("uns_count")
        assert wert, f"{sprache}: uns_count fehlt"
        assert not re.match(r"^\s*\{n\}\s+\S", wert), \
            f"{sprache}: die Zahl klebt am Substantiv — {wert!r}"
        assert "{n}" in wert and "{s}" in wert, f"{sprache}: Platzhalter fehlen — {wert!r}"


# --- #638: Klick auf einen Anfragetitel führt zur Karte --------------------------------

def test_search_falls_back_to_the_cleaned_title(appmod, client, monkeypatch):
    """Findet der rohe Release-Titel nichts, wird der gekürzte versucht — in DIESER
    Reihenfolge, denn ein exakter Treffer ist der bessere. (#638)"""
    _admin(appmod, client, "such1")
    gefragt = []
    def falsch(q, plats, stats=None):
        gefragt.append(q)
        return [{"title": "Resident Evil 2", "platform": "psx"}] if q == "Resident Evil 2" else []
    monkeypatch.setattr(appmod, "do_search", falsch)

    roh = "Resident Evil 2 PS1 (Europe) (Disc 1&2)"
    # kodiert, sonst schneidet das `&` in `1&2` die Abfrage ab — der Titel ist genau
    # deshalb ein guter Prüffall
    r = client.get("/api/search?clean=1&q=" + urllib.parse.quote(roh))
    assert r.status_code == 200
    assert r.get_json(), "trotz Kürzung kein Treffer"
    assert gefragt[0] == roh, f"der rohe Titel wurde nicht zuerst versucht: {gefragt}"
    assert len(gefragt) == 2 and gefragt[1] == "Resident Evil 2", gefragt
    appmod.save_users({})


def test_search_does_not_clean_when_the_raw_title_works(appmod, client, monkeypatch):
    """Wo es heute geht, muss es weiter gehen — und ohne zweite Suche. (#638)"""
    _admin(appmod, client, "such2")
    gefragt = []
    def treffer(q, plats, stats=None):
        gefragt.append(q)
        return [{"title": "Crime OClock", "platform": "switch"}]
    monkeypatch.setattr(appmod, "do_search", treffer)
    r = client.get("/api/search?clean=1&q=Crime OClock NSW-SUXXORS")
    assert r.status_code == 200 and r.get_json()
    assert gefragt == ["Crime OClock NSW-SUXXORS"], f"unnötig zweimal gesucht: {gefragt}"
    appmod.save_users({})


def test_search_leaves_the_query_alone_without_the_flag(appmod, client, monkeypatch):
    """Ohne `clean=1` bleibt alles wie zuvor — die Suchleiste kürzt nicht. (#638)"""
    _admin(appmod, client, "such3")
    gefragt = []
    monkeypatch.setattr(appmod, "do_search", lambda q, p, st=None: gefragt.append(q) or [])
    client.get("/api/search?q=" + urllib.parse.quote("Resident Evil 2 PS1 (Europe) (Disc 1&2)"))
    assert len(gefragt) == 1, f"ohne Schalter wurde gekürzt: {gefragt}"
    appmod.save_users({})


def test_clicking_a_request_title_says_something_immediately(appmod):
    """Rückmeldung VOR dem Netzaufruf, nicht danach. (#638)

    Gemessen hatte der erste Hinweis 3 s gebraucht, weil die Suche erst Usenet und
    Archive.org fragt. Bis dahin war die Zeile nur auf 60 % Deckkraft — klicken, warten,
    nichts sehen, den Knopf für kaputt halten. Geprüft wird die Reihenfolge im Quelltext:
    die Meldung muss vor dem `fetch` stehen.
    """
    js = _js()
    m = re.search(r"async function openJobDetail\(titel, ?plattform, ?el\)\{(.*?)\n\}", js, re.S)
    assert m, "openJobDetail nicht gefunden"
    koerper = m.group(1)
    vor_meldung = koerper.index("jobMeldungSetzen(jid,t('job_searching'))")
    vor_fetch = koerper.index("await fetch(")
    assert vor_meldung < vor_fetch, "die Rückmeldung kommt erst nach dem Netzaufruf"
    # auf die URL prüfen, nicht auf das Wort: `clean=1` steht auch im Kommentar darüber,
    # und eine Prüfung, die den Kommentar findet, prüft den Code nicht
    ohne_kommentar = re.sub(r"^\s*//.*$", "", koerper, flags=re.M)
    assert "search?clean=1" in ohne_kommentar, "die Suche fordert die Kürzung nicht an"
    assert i18n_hat("job_searching"), "job_searching fehlt in einer Sprache"


# --- #672: Sprache und Benutzermenü stehen unter Aurora in der Navigation ---------------

def test_the_account_block_moves_only_under_aurora(appmod):
    """Nur dort, wo die Navigation oben liegt. (#672)

    In den drei anderen Designs ist `#side` eine Spalte am linken Rand — und aus genau
    dieser Ecke hat #206 den Block geholt, weil sie niemand absucht. Der Wunsch aus #672
    beschreibt Aurora; ihn überall umzusetzen hieße, #206 rückgängig zu machen.
    """
    js = _js()
    # bis `;}` am Zeilenende — die Funktion schließt auf derselben Zeile, ein Regex auf
    # `\n}` läuft in den nächsten Code hinein und prüft dann etwas anderes
    m = re.search(r"function kopfrechtsPlatzieren\(dz\)\{(.*?;\})$", js, re.S | re.M)
    assert m, "die Funktion fehlt"
    koerper = m.group(1)
    assert "'aurora'" in koerper, "sie unterscheidet die Designs nicht"
    assert "'side'" in koerper and "'topbar'" in koerper, "sie kennt nicht beide Ziele"
    assert "appendChild" in koerper, "der Block wird nicht verschoben, sondern anders erzeugt"
    assert "innerHTML" not in koerper, "eine zweite Fassung läuft auseinander (#632)"
    a = re.search(r"function applyDesign\(dz\)\{(.*?)\n(?=function |let |const )", js, re.S)
    assert a and "kopfrechtsPlatzieren(dz)" in a.group(1), \
        "beim Designwechsel wird nicht umgehängt"


def test_the_default_markup_still_follows_206(appmod):
    """Im Markup bleibt der Block in der Suchzeile — das Umhängen ist die Ausnahme. (#672)

    Andernfalls stünde er beim ersten Rendern kurz an der falschen Stelle.
    """
    tpl = open(os.path.join(REPO, "templates/index.html"), encoding="utf-8").read()
    topbar = tpl[tpl.index("<div id=topbar>"):tpl.index("</main>")]
    assert "class=kopfrechts" in topbar, "der Block startet nicht in der Suchzeile"
    side = tpl[tpl.index("<div id=side>"):tpl.index("<main>")]
    assert "class=kopfrechts" not in side, "er steht schon im Markup in der Navigation"


# --- #661: Zurück und Leeren in der Suchzeile ------------------------------------------

def test_the_search_buttons_only_appear_when_they_do_something(appmod):
    """Ein Knopf, bei dem nichts passiert, ist von einem kaputten nicht zu unterscheiden.
    Das war der Befund in #638 — hier von vornherein vermieden. (#661)"""
    js = _js()
    m = re.search(r"function suchKnoepfe\(\)\{(.*?;\})$", js, re.S | re.M)
    assert m, "suchKnoepfe fehlt"
    k = m.group(1)
    assert "q.value" in k, "der Leeren-Knopf hängt nicht am Feldinhalt"
    assert "EIGENE_SCHRITTE>0" in k, "der Zurück-Knopf hängt nicht an der Verlaufstiefe"
    assert k.count("'none'") == 2, "einer der beiden wird nie versteckt"


def test_back_never_leaves_romseerr(appmod):
    """`history.back()` ohne eigenen Verlaufseintrag führt aus der Anwendung heraus —
    genau davor schützt `EIGENE_SCHRITTE` seit #194/#226. (#661)"""
    js = _js()
    m = re.search(r"function suchZurueck\(\)\{(.*?;?\})$", js, re.S | re.M)
    assert m, "suchZurueck fehlt"
    assert "EIGENE_SCHRITTE>0" in m.group(1), "der Knopf prüft die Verlaufstiefe nicht"


def test_clearing_has_exactly_one_implementation(appmod):
    """EINE Funktion fürs Leeren, nicht zwei. (#661/#662)

    Beim Bauen stand kurzzeitig eine zweite `sucheLeeren` in der Datei — gleicher Name,
    andere Wirkung, und die spätere gewinnt stillschweigend. `markeGeh()` aus #662 hätte
    dann unbemerkt die neue Fassung bekommen. Der Klick auf die Marke, der Leeren-Knopf
    und Escape gehen deshalb alle durch dieselbe Funktion.
    """
    js = _js()
    assert len(re.findall(r"^function sucheLeeren\(", js, re.M)) == 1, \
        "es gibt mehr als eine Definition — die spätere überschreibt die frühere"
    m = re.search(r"^function sucheLeeren\(fokus\)\{(.*?return true;\})$", js, re.S | re.M)
    assert m, "sucheLeeren nimmt kein `fokus`-Argument mehr"
    k = m.group(1)
    assert "q.value=''" in k, "das Feld wird nicht geleert"
    assert "suchKnoepfe()" in k, "die Knöpfe werden danach nicht aktualisiert"
    assert "loadDiscover()" in k, "es führt nicht zur Startseite"
    assert "if(fokus)q.focus()" in k, "der Fokus wird nicht bedingt gesetzt"
    # der Klick auf die Marke darf NICHT im Suchfeld enden
    marke = re.search(r"function markeGeh\(\)\{(.*?\})$", js, re.M)
    assert marke and "sucheLeeren()" in marke.group(1), \
        "der Klick auf die Marke geht nicht durch dieselbe Funktion oder fordert Fokus an"


def test_escape_clears_the_field_last_of_all(appmod):
    """Reihenfolge: Menü, Dialog, dann erst das Feld. (#661)

    Stünde das Leeren vorn, nähme ein Escape dem Dialog das Schließen weg — und wer einen
    Dialog schließt, will nicht seine Suche verlieren.
    """
    js = _js()
    m = re.search(r"document\.addEventListener\('keydown',e=>\{\n if\(e\.key!=='Escape'\)return;(.*?)\}\);",
                  js, re.S)
    assert m, "der Escape-Handler ist nicht auffindbar"
    k = m.group(1)
    i_menu, i_modal = k.index("closeMenus()"), k.index("closeModal()")
    i_feld = k.index("sucheLeeren(true)")
    assert i_menu < i_modal < i_feld, \
        f"falsche Reihenfolge: Menü {i_menu}, Dialog {i_modal}, Feld {i_feld}"
    assert "return;}" in k[i_modal-30:i_modal+30], "der Dialogzweig kehrt nicht zurück"


def test_the_search_buttons_are_drawn_not_typed(appmod):
    """Pfade, keine Textzeichen — wie die Marke (#650) und das × im Dialog (#659). (#661)"""
    tpl = open(os.path.join(REPO, "templates/index.html"), encoding="utf-8").read()
    for knopf_id in ("tBack", "tClear"):
        i = tpl.index(f"id={knopf_id}")
        block = tpl[i:tpl.index("</button>", i)]
        assert "<svg" in block and "<path" in block, f"{knopf_id}: kein gezeichnetes Zeichen"
        assert "aria-label" in block, f"{knopf_id}: kein zugänglicher Name"
        assert "data-i18n-al" in block, f"{knopf_id}: der Name wird nicht übersetzt"
    js = _js()
    assert "data-i18n-al" in js and "setAttribute('aria-label'" in js, \
        "aria-label wird nirgends übersetzt"
    for s in ("such_back", "such_clear"):
        assert i18n_hat(s), f"{s} fehlt in einer Sprache"


# --- #654: Ordner, Plattformen, Einträge und Titel sind vier verschiedene Zahlen --------

def test_the_index_log_separates_folders_from_platforms(appmod, tmp_path, monkeypatch, capsys):
    """599 Ordner, 64 davon mit Inhalt — beides „Plattformen" zu nennen ergab zwei
    Zahlen, die einander widersprachen, obwohl jede für sich stimmte. (#654)"""
    quelle = open(os.path.join(REPO, "app.py"), encoding="utf-8").read()
    m = re.search(r'log\(f"Bibliotheks-Index: (.*?)\)\n', quelle, re.S)
    assert m, "die Logzeile ist nicht auffindbar"
    zeile = m.group(1)
    assert "mit_inhalt" in zeile, "die Zeile nennt weiterhin die Ordnerzahl als Plattformen"
    assert "Ordner" in zeile, "die Ordnerzahl fehlt ganz"
    assert "len(slugs)} Ordner" in zeile, "`slugs` wird nicht als Ordnerzahl ausgewiesen"

    # BEIDE Logzeilen, nicht nur die eine: der Index wird beim Start aus der DB geladen und
    # bei Änderungen neu gebaut. Die Ladezeile trug denselben Fehler und blieb beim ersten
    # Anlauf stehen — sichtbar erst im Log der laufenden Anlage.
    i = quelle.index('log(f"Bibliotheks-Index aus DB geladen:')
    laden = quelle[i:quelle.index("\n", quelle.index("Titel", i))]
    assert "Plattformen mit Inhalt" in laden, \
        f"die Ladezeile nennt Ordner weiterhin Plattformen: {laden[:120]}"
    assert "Ordner)" in laden, "die Ordnerzahl fehlt in der Ladezeile"
    assert "LIB['slugs']} Plattformen" not in laden, "sie zählt weiterhin Ordner als Plattformen"


def test_admin_stats_reports_all_four_numbers(appmod, client, monkeypatch):
    """Ordner, Plattformen mit Inhalt, Einträge und Titel. (#654)

    Die vier hängen zusammen und werden verwechselt: `LIB["slugs"]` sind Ordner,
    `LIB["per"]` die Plattformen mit Inhalt, die Summe ihrer Längen die Einträge und
    `LIB["all"]` die eindeutigen Titel.
    """
    _admin(appmod, client, "stat1")
    monkeypatch.setitem(appmod.LIB, "slugs", {"snes", "nes", "leer1", "leer2"})
    monkeypatch.setitem(appmod.LIB, "per", {"snes": {"a", "b"}, "nes": {"b", "c"}, "leer1": set()})
    monkeypatch.setitem(appmod.LIB, "all", {"a", "b", "c"})

    d = client.get("/api/admin/stats").get_json()
    assert d["lib_folders"] == 4, f"Ordnerzahl falsch: {d}"
    assert d["lib_platforms"] == 2, f"leere Plattformen mitgezählt: {d}"
    assert d["lib_entries"] == 4, f"Einträge falsch (2+2 erwartet): {d}"
    assert d["lib_titles"] == 3, f"Titel falsch (a,b,c erwartet): {d}"
    appmod.save_users({})


def test_the_library_view_counts_entries_not_titles(appmod):
    """Was je Plattform steht, sind Einträge — derselbe Titel auf zwei Systemen zählt
    zweimal. Ihn „Titel" zu nennen ergab 323.776 gegen 293.067. (#654)"""
    js = _js()
    for stelle in ("(d.total||0).toLocaleString()", "p.owned.toLocaleString()",
                   "Number(st.total).toLocaleString()"):
        i = js.index(stelle)
        umfeld = js[i:i + 120]
        assert "lib_entries" in umfeld, f"noch als Titel beschriftet: {umfeld[:80]}"
    assert i18n_hat("lib_entries"), "lib_entries fehlt in einer Sprache"


def test_the_stream_host_describes_virtualgl_as_it_is(appmod):
    """Neun von zehn Emulatoren starten darüber — der Kopf muss das sagen. (#628)

    Diese Prüfung hat schon einmal das Gegenteil verlangt: Ich hatte aus einer
    Fehlmessung geschlossen, VirtualGL sei unbenutzt, und die Doku entsprechend
    umgeschrieben. `VGLDEV` steht nie in der Container-Umgebung — `30-agent` liest die
    Gerätedatei erst beim Start eines Emulators. Wer es per `docker exec` misst, sieht
    leer und schließt falsch.

    Gemessen: `/config/.vgl-device` trägt `/dev/dri/card2`, und `apprun()` — mit
    `vglrun`-Präfix — wird von neun Emulatoren aufgerufen, `apprun_ohne_vgl` nur von xemu.
    """
    basis = os.path.join(REPO, "contrib", "streaming-host", "init")
    agent = open(os.path.join(basis, "30-agent"), encoding="utf-8").read()

    mit = set(re.findall(r"\$\(apprun ([a-z0-9]+)\)", agent))
    ohne = set(re.findall(r"\$\(apprun_ohne_vgl ([a-z0-9]+)\)", agent))
    assert len(mit) >= 9, f"nur {len(mit)} Emulatoren über apprun: {sorted(mit)}"
    assert ohne == {"xemu"}, f"ohne VirtualGL erwartet nur xemu, gefunden: {sorted(ohne)}"

    kopf = agent[:agent.index("VGLDEV=")]
    # BEIDE Hälften müssen dastehen: der Wrapper wird gesetzt, UND Vulkan geht daran
    # vorbei. Nur eine davon zu nennen erzeugt genau die zwei Fehlschlüsse, die diese
    # Datei heute schon zweimal enthalten hat.
    assert "vglrun" in kopf and "apprun_ohne_vgl" in kopf, \
        "der Kopf sagt nicht, dass der Präfix gesetzt wird"
    assert "Vulkan" in kopf, "er verschweigt, dass Vulkan daran vorbeigeht"
    assert "RUECKFALL" in kopf or "Rückfall" in kopf, "die Rolle bleibt unbenannt"
    assert "Container-Umgebung" in kopf, \
        "die Messfalle steht nicht dabei — sie hat schon zu einem falschen Schluss geführt"

    vgl = open(os.path.join(basis, "10-virtualgl"), encoding="utf-8").read()
    kopf2 = vgl[:vgl.index("# ---")]
    assert "Vulkan" in kopf2 and "vorbei" in kopf2.lower(), \
        "der Kopf trennt nicht zwischen gesetztem Wrapper und tatsächlichem Renderer"
    assert "libvglfaker" in kopf2, "die zweite Messfalle fehlt"
    for emu in ("dolphin", "pcsx2", "xemu"):
        assert emu in kopf2, f"{emu} fehlt in der Aufstellung"


# --- #684: Web-Push lässt sich prüfen, und der Test sagt die Wahrheit ------------------

def test_push_send_reports_what_happened(appmod, monkeypatch):
    """Kein stilles Ende mehr. (#684)

    Die Funktion gab nichts zurück und meldete Fehlschläge nur ins Log — der Test-Endpunkt
    antwortete deshalb immer `ok`. Dieselbe Bauart hat bei den liegengebliebenen Downloads
    (#645) monatelang einen echten Fehler verdeckt.
    """
    monkeypatch.setattr(appmod, "PUSH_OK", False)
    e = appmod.send_push_to_user("u", "T", "B")
    assert e["gesendet"] == 0 and "pywebpush" in e["grund"], e

    monkeypatch.setattr(appmod, "PUSH_OK", True)
    monkeypatch.setattr(appmod, "ensure_vapid", lambda: None)
    e = appmod.send_push_to_user("u", "T", "B")
    assert e["gesendet"] == 0 and "VAPID" in e["grund"], e

    monkeypatch.setattr(appmod, "ensure_vapid", lambda: {"priv_pem": "x"})
    monkeypatch.setattr(appmod, "load_push", lambda: {})
    e = appmod.send_push_to_user("u", "T", "B")
    assert e["abos"] == 0 and "kein Abo" in e["grund"], e

    monkeypatch.setattr(appmod, "load_push", lambda: {"u": [{"endpoint": "e1"}]})
    # `webpush` gibt es nur, wenn pywebpush installiert ist — `raising=False`
    monkeypatch.setattr(appmod, "webpush", lambda **kw: None, raising=False)
    e = appmod.send_push_to_user("u", "T", "B")
    assert e["gesendet"] == 1 and not e["grund"], e


def test_push_test_endpoint_can_fail(appmod, client, monkeypatch):
    """`ok` heißt: mindestens ein Abo hat sie angenommen. (#684)"""
    _admin(appmod, client, "pusht")
    monkeypatch.setattr(appmod, "send_push_to_user",
                        lambda *a: {"abos": 0, "gesendet": 0, "abgelaufen": 0, "grund": "kein Abo"})
    d = client.post("/api/push/test").get_json()
    assert d["ok"] is False and d["grund"] == "kein Abo", d

    monkeypatch.setattr(appmod, "send_push_to_user",
                        lambda *a: {"abos": 1, "gesendet": 1, "abgelaufen": 0, "grund": ""})
    assert client.post("/api/push/test").get_json()["ok"] is True
    appmod.save_users({})


def test_the_push_test_button_exists_and_shows_the_reason(appmod):
    """Der Endpunkt war da, nur rief ihn niemand. (#684)"""
    js = _js()
    # bis zur schließenden Klammer der Funktion, nicht bis zum ersten textContent
    i = js.index("async function testPush(){")
    j = js.index("\n", js.index("d.grund", i))
    m = re.match(r"(?s).*", js[i:j])
    assert m, "testPush fehlt"
    k = m.group(0)
    assert "/api/push/test" in k, "der vorhandene Endpunkt wird nicht benutzt"
    assert "d.grund" in k, "der Grund vom Server wird verworfen"
    assert "test_sent" in k, "der Erfolgsfall meldet nichts"
    # und der Knopf zeigt sich nur im abonnierten Zustand
    # bis zur Zeile mit dem Testknopf lesen — die Funktion endet mit `'none';}` und ein
    # Regex auf das erste `;}` bricht schon nach der ersten Bedingung ab
    i = js.index("async function refreshPushBtn(){")
    j = js.index("\n", js.index("pushtest", i))
    refresh = js[i:j]
    assert "pushtest" in refresh, "der Testknopf wird nie ein- oder ausgeblendet"
    # die Bedingung muss in DERSELBEN Anweisung stehen wie der Knopf — `st=='on'` kommt
    # eine Zeile höher schon vor, und ein Test, der das findet, prüft die falsche Stelle
    zeile = [z for z in refresh.splitlines() if "pushtest" in z][-1]
    assert "st=='on'" in zeile, f"der Testknopf hängt nicht am Abo-Zustand: {zeile.strip()}"
    assert "'none'" in zeile, "er wird nie versteckt"


# --- #685: „in Bibliothek" und „Plattform unbekannt" schließen einander aus -------------

def test_library_slugs_says_where_not_only_whether(appmod, monkeypatch):
    """`in_library` beantwortet nur das Ob — die Karte braucht das Wo. (#685)"""
    monkeypatch.setitem(appmod.LIB, "per", {"snes": {appmod.norm("Pac-Man")},
                                            "gb": {appmod.norm("Pac-Man")},
                                            "nes": {appmod.norm("Anderes")}})
    monkeypatch.setitem(appmod.LIB, "all", {appmod.norm("Pac-Man"), appmod.norm("Anderes")})
    s = appmod.library_slugs("Pac-Man")
    assert set(s) == {"snes", "gb"}, s
    assert appmod.library_slugs("Gibt Es Nicht") == []


def test_the_oldest_platform_comes_first(appmod, monkeypatch):
    """Bei einem Titel auf mehreren Systemen ist die älteste Plattform fast immer die,
    auf der er zuerst erschien. (#685)

    Das ist das Jahr der KONSOLE, nicht des Spiels — und die Karte behauptet auch nichts
    anderes. IGDB liefert nur ein Gesamtdatum je Spiel und kennt Hacks und Homebrew nicht,
    also genau die Titel, um die es hier geht.
    """
    n = appmod.norm("Pac-Man")
    monkeypatch.setitem(appmod.LIB, "per", {"gb": {n}, "atari2600": {n}, "nes": {n}, "snes": {n}})
    monkeypatch.setitem(appmod.LIB, "all", {n})
    # Game Boy 1989 VOR SNES 1990 — beim Schreiben des Tests hatte ich das andersherum
    # erwartet, und der Code hatte recht.
    assert appmod.library_slugs("Pac-Man") == ["atari2600", "nes", "gb", "snes"], \
        appmod.library_slugs("Pac-Man")
    # Laufzeitumgebungen ohne Erscheinungsdatum gehören ans Ende, nicht an den Anfang
    monkeypatch.setitem(appmod.LIB, "per", {"scummvm": {n}, "snes": {n}})
    assert appmod.library_slugs("Pac-Man") == ["snes", "scummvm"]


def test_every_platform_of_the_library_has_a_year(appmod):
    """Ein fehlendes Jahr sortiert stumm ans Ende — das darf kein Versehen sein. (#685)"""
    slugs = {s for gruppe in appmod.PLATFORMS for s, _ in gruppe[1]}
    fehlt = sorted(s for s in slugs if s not in appmod.PLAT_JAHR)
    assert not fehlt, f"Plattformen ohne Jahresangabe: {fehlt}"


def test_a_derived_platform_is_marked_as_derived(appmod):
    """Sie kommt aus der Bibliothek, nicht von der Quelle — das muss man sehen. (#685)"""
    js = _js()
    # bis `return sicher;}` — die Funktion schließt auf derselben Zeile, ein Regex auf
    # `\n}` schneidet mitten hinein und ergibt ungültiges JavaScript
    i = js.index("function plattformMarke(slug,libSlugs){")
    j = js.index("return sicher;}", i) + len("return sicher;}")
    ganze = js[i:j]
    k = ganze
    m = type("M", (), {"group": staticmethod(lambda n=0: ganze)})()
    assert "plat-derived" in k and "plat-more" in k, "erste und weitere Zeile fehlen"
    # AUSFUEHREN statt Text prüfen: dass `libSlugs` irgendwo vorkommt, bleibt auch wahr,
    # wenn die Bedingung nie zutrifft. Vierte blinde Prüfung dieser Art heute.
    node = shutil.which("node")
    if node:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            skript = os.path.join(d, "p.mjs")
            with open(skript, "w", encoding="utf-8") as f:
                f.write("let SLUGNAME={snes:'SNES',gb:'Game Boy'};\n"
                        "let LOGOS=new Set();\n"          # sonst fehlt die Variable
                        "function t(k){return '<'+k+'>';}\n" + m.group(0) + "\n"
                        "console.log(JSON.stringify({"
                        "abgeleitet: plattformMarke('', ['snes','gb']),"
                        "ohne: plattformMarke('', []),"
                        "mit: plattformMarke('snes')}));")
            r = subprocess.run([node, skript], capture_output=True, text=True)
            assert r.returncode == 0, r.stderr.strip()
            d2 = json.loads(r.stdout.strip().splitlines()[-1])
        assert "plat-derived" in d2["abgeleitet"] and "SNES" in d2["abgeleitet"], d2["abgeleitet"]
        assert "Game Boy" in d2["abgeleitet"] and "plat-more" in d2["abgeleitet"], d2["abgeleitet"]
        assert "plat_unknown" not in d2["abgeleitet"], "die Warnung erscheint trotz Ableitung"
        assert "plat_unknown" in d2["ohne"], "ohne Bibliothekstreffer muss die Warnung bleiben"
        assert "SNES" in d2["mit"] and "plat-derived" not in d2["mit"], \
            "eine von der Quelle genannte Plattform darf nicht als abgeleitet gelten"
    assert "plat_derived_hint" in k, "kein Hinweis, woher die Angabe stammt"
    css = open(os.path.join(REPO, "static/css/index.css"), encoding="utf-8").read()
    assert ".plat-more{" in css and "var(--mut)" in css[css.index(".plat-more{"):css.index(".plat-more{")+200], \
        "die weiteren Plattformen sind nicht abgesetzt"
    assert i18n_hat("plat_derived_hint"), "plat_derived_hint fehlt in einer Sprache"


def test_search_attaches_the_derived_platforms(appmod):
    """Nur wenn die Quelle nichts sagt UND der Titel vorhanden ist. (#685)"""
    quelle = open(os.path.join(REPO, "app.py"), encoding="utf-8").read()
    m = re.search(r'r\["in_library"\] = in_library.*?\n(.*?)\n\s*r\["is_set"\]', quelle, re.S)
    assert m, "die Stelle in der Suche ist nicht auffindbar"
    zweig = m.group(1)
    assert 'if r["in_library"] and not r["platform_slug"]' in zweig, \
        "die Ableitung hängt nicht an beiden Bedingungen"
    assert 'library_slugs(r["title"])' in zweig, "library_slugs wird nicht benutzt"


# --- #689: Größe ist nur in der Modul-Ära ein Hinweis auf eine Sammlung -----------------

def test_size_only_marks_a_set_on_cartridge_era_platforms(appmod):
    """4 GB sind auf dem SNES eine Sammlung und auf der PS3 ein normales Spiel. (#689)"""
    gross = 5 * 1024**3
    # Modul-Ära: die Schwelle greift
    assert appmod.is_set("Irgendein Paket", gross, "snes") is True
    assert appmod.is_set("Irgendein Paket", gross, "nes") is True
    # CD-Ära und später: Größe sagt nichts mehr
    assert appmod.is_set("Uncharted 2: Among Thieves PS3 (EUR)", 22 * 1024**3, "ps3") is False
    assert appmod.is_set("Silent Hill Homecoming", 7 * 1024**3, "xbox360") is False
    assert appmod.is_set("Mario Kart Wii", 7 * 1024**3, "wii") is False
    # unbekannte Plattform: kein Urteil aus der Größe
    assert appmod.is_set("The Last Of Us Review Build", 36 * 1024**3, None) is False
    assert appmod.is_set("The Last Of Us Review Build", 36 * 1024**3, "") is False


def test_the_name_still_marks_a_set_on_any_platform(appmod):
    """Das Namensmuster gilt unabhängig von Plattform und Größe. (#689)"""
    for titel in ("SNES Full Set", "Mega Pack 2020", "No-Intro Collection",
                  "New Super Mario Bros Wii Mod Archive", "Pokémon ROMhacks CIAs",
                  "Metroid Prime Trilogy", "Street Fighter Alpha Anthology"):
        assert appmod.is_set(titel, 1, "ps3") is True, f"nicht als Sammlung erkannt: {titel}"


def test_the_word_archive_alone_is_not_a_set(appmod):
    """`Archive` steht in jedem zweiten Titel — es ist die Quelle. (#689)

    Nur `mod archive` zählt, sonst gälte die halbe Archive.org-Ausbeute als Sammlung.
    """
    assert appmod.is_set("Silent Hill 2 Archive.org Upload", 1, "ps2") is False
    assert appmod.is_set("Internet Archive Mirror", 1, "ps2") is False
    assert appmod.is_set("Sonic Generations Mod Archive", 1, "pc") is True


def test_search_passes_the_platform_to_is_set(appmod):
    """Ohne den Slug fällt die Unterscheidung in sich zusammen. (#689)"""
    quelle = open(os.path.join(REPO, "app.py"), encoding="utf-8").read()
    assert 'is_set(r["title"], r["size"], r["platform_slug"])' in quelle, \
        "die Suche übergibt die Plattform nicht"


# ---------------------------------------------------------------------------
# #688 — der Plattformfilter haelt Treffer zurueck, ohne es zu sagen
# ---------------------------------------------------------------------------

def _quellen(monkeypatch, appmod, treffer):
    """Alle drei Quellen durch eine feste Liste ersetzen."""
    monkeypatch.setattr(appmod, "search_archive", lambda q, **k: [dict(t) for t in treffer])
    monkeypatch.setattr(appmod, "search_usenet", lambda q, cats: [])
    monkeypatch.setattr(appmod, "catalog_urls", lambda: [])
    monkeypatch.setattr(appmod, "in_library", lambda t, p: False)


def _tr(titel, plattform, quelle="archive"):
    return {"source": quelle, "ref": titel, "title": titel, "platform": plattform,
            "size": 1, "cover": "", "extra": ""}


def test_do_search_reports_how_many_the_platform_filter_hid(appmod, monkeypatch):
    """Die Zahl, die in der Liste fehlte. (#688)

    Jens fand „Silent Hill Homecoming" nicht: Ein Klick auf eine Entdecken-Karte hatte den
    Filter auf `snes` gesetzt, und dort blieb er — ueber Suchen, Neuladen und Tage hinweg.
    Statt 14 Treffern kamen 4, weil Ergebnisse OHNE erkannte Plattform absichtlich jeden
    Filter passieren. Die Liste sah damit nicht gefiltert aus, sondern duenn.
    """
    _quellen(monkeypatch, appmod, [
        _tr("Homecoming PS3", "ps3"),
        _tr("Homecoming Xbox", "xbox360"),
        _tr("Homecoming PC", "pc"),
        _tr("Irgendwas ohne Plattform", ""),      # passiert den Filter, absichtlich
        _tr("Ein SNES-Titel", "snes"),
    ])
    st = {}
    res = appmod.do_search("egal", ["snes"], st)
    assert len(res) == 2, f"erwartet SNES + Unbestimmter, bekam {[r['title'] for r in res]}"
    assert st["plat_hidden"] == 3, \
        f"der Filter nahm 3 Treffer weg, gemeldet werden {st.get('plat_hidden')}"


def test_do_search_counts_usenet_hits_without_a_platform(appmod, monkeypatch):
    """Der zweite Zweig des Filters zaehlt genauso. (#688)

    Usenet-Treffer OHNE erkannte Plattform fliegen bei aktivem Filter raus — anders als
    Archive.org-Treffer, die durchgelassen werden, weil ihre Titel oft keine Zuordnung
    tragen. Diese Asymmetrie ist gewollt. Sie darf aber nicht dazu fuehren, dass ein
    ganzer Zweig lautlos aus der Zaehlung faellt: Wer nach einem Switch-Titel filtert und
    zwanzig Usenet-Treffer verliert, bekaeme eine leere Liste ohne Grund.

    (Diese Luecke fand ein Mutationstest — die vorherigen Tests hatten nur
    Archive.org-Treffer und blieben gruen, als der Zweig aufhoerte zu zaehlen.)
    """
    monkeypatch.setattr(appmod, "search_archive", lambda q, **k: [_tr("SNES-Titel", "snes")])
    monkeypatch.setattr(appmod, "search_usenet", lambda q, cats: [
        _tr("Release ohne Zuordnung", "", "usenet"),
        _tr("Noch eins ohne Zuordnung", "", "usenet"),
    ])
    monkeypatch.setattr(appmod, "catalog_urls", lambda: [])
    monkeypatch.setattr(appmod, "in_library", lambda t, p: False)
    st = {}
    res = appmod.do_search("egal", ["snes"], st)
    assert [r["title"] for r in res] == ["SNES-Titel"],         "die Usenet-Treffer ohne Plattform muessen der Filterung zum Opfer fallen"
    assert st["plat_hidden"] == 2,         f"beide Usenet-Treffer gehoeren in die Zahl, gemeldet werden {st.get('plat_hidden')}"


def test_do_search_reports_zero_when_no_filter_is_set(appmod, monkeypatch):
    """Ohne Filter kann nichts zurueckgehalten werden. (#688)"""
    _quellen(monkeypatch, appmod, [_tr("A", "ps3"), _tr("B", "snes"), _tr("C", "")])
    st = {}
    res = appmod.do_search("egal", [], st)
    assert len(res) == 3
    assert st["plat_hidden"] == 0, f"ohne Filter darf nichts fehlen, gemeldet {st}"


def test_do_search_does_not_blame_the_platform_filter_for_the_blocklist(appmod, monkeypatch):
    """Zwei Filter, eine Zahl — das waere eine Falschauskunft. (#688)

    Die Sperrliste nimmt ebenfalls Treffer weg. Wuerde ihr Anteil mitgezaehlt, boete der
    Hinweis „Filter aufheben" fuer etwas an, das der Plattformfilter nie versteckt hat:
    Der Klick brachte die Treffer nicht zurueck, und die Zahl waere unerklaerlich.
    """
    _quellen(monkeypatch, appmod, [
        _tr("Ein SNES-Titel", "snes"),
        _tr("Gesperrtes PS3-Spiel", "ps3"),       # faellt der Sperrliste zum Opfer
        _tr("Normales PS3-Spiel", "ps3"),         # faellt dem Plattformfilter zum Opfer
    ])
    monkeypatch.setattr(appmod, "load_settings", lambda: {"blocklist": ["gesperrtes"]})
    st = {}
    res = appmod.do_search("egal", ["snes"], st)
    assert [r["title"] for r in res] == ["Ein SNES-Titel"]
    assert st["plat_hidden"] == 1, \
        f"nur der Plattformfilter zaehlt, gemeldet werden {st.get('plat_hidden')}"


def test_do_search_still_works_without_the_stats_argument(appmod, monkeypatch):
    """Drei interne Aufrufer uebergeben nichts. (#688)

    `stats` ist ein Ausgabeparameter und kein zweiter Rueckgabewert, damit die Autosuche,
    der Versionsabgleich und die Tests unveraendert bleiben. Wird das je zu einem Tupel,
    faellt es hier auf und nicht erst im Betrieb.
    """
    _quellen(monkeypatch, appmod, [_tr("A", "ps3"), _tr("B", "snes")])
    res = appmod.do_search("egal", ["snes"])
    assert isinstance(res, list), f"do_search gibt {type(res).__name__} statt einer Liste"
    assert [r["title"] for r in res] == ["B"]


def test_search_endpoint_reports_the_hidden_count_in_a_header(appmod, client, monkeypatch):
    """Die Zahl muss beim Frontend ankommen. (#688)

    Als Kopfzeile und nicht im Rumpf: `/api/search` liefert eine nackte Liste, und die
    steckt in `window.LASTRES`, in `d.forEach`, in der Sammelanfrage. Daraus ein Objekt zu
    machen, um EINE Zahl unterzubringen, haette jeden dieser Aufrufer angefasst.
    """
    _quellen(monkeypatch, appmod, [
        _tr("Homecoming PS3", "ps3"), _tr("Homecoming PC", "pc"), _tr("SNES-Titel", "snes"),
    ])
    _als(client, appmod, "admin")
    r = client.get("/api/search?q=egal&platforms=snes")
    assert r.status_code == 200
    assert r.headers.get("X-Platform-Hidden") == "2", \
        f"Kopfzeile sagt {r.headers.get('X-Platform-Hidden')!r} statt '2'"
    r = client.get("/api/search?q=egal")
    assert r.headers.get("X-Platform-Hidden") == "0", \
        f"ohne Filter erwartet '0', bekam {r.headers.get('X-Platform-Hidden')!r}"
