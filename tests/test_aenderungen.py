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


# ---------------------------------------------------------------------------
# #691 — eine Karte je Spiel, nicht je Fassung
# ---------------------------------------------------------------------------

def test_a_game_owned_on_one_platform_counts_as_owned_everywhere(appmod, monkeypatch):
    """Sonst zerfaellt die Karte in sich. (#691)

    Die Oberflaeche zeigt eine Karte je Spiel. Gaebe der Sortierschluessel weiter den
    Zustand des EINZELTREFFERS vor, staende bei einem Spiel, das auf einer Plattform
    daliegt und auf einer anderen nicht, die nicht vorhandene Fassung vorn — die Karte
    truege einen Download-Knopf fuer ein Spiel mit gruenem Haken.
    """
    # DIE VORHANDENE FASSUNG STEHT BEWUSST IN DER MITTE. Stuende sie vorn oder hinten,
    # lieferte auch eine schlichte Zuweisung („die erste/letzte gewinnt") zufaellig das
    # richtige Ergebnis, und der Test bewiese nichts — genau das deckte ein Mutationstest
    # auf. Nur mit der Mitte muss ueber ALLE Fassungen zusammengefasst werden.
    treffer = [
        _tr("Silent Hill 2 PC", "pc"),          # dieselbe gkey, NICHT vorhanden
        _tr("Silent Hill 2 PS2", "ps2"),        # dieselbe gkey, VORHANDEN
        _tr("Silent Hill 2 Xbox", "xbox"),      # dieselbe gkey, NICHT vorhanden
        _tr("Ein anderes Spiel", "pc"),
    ]
    monkeypatch.setattr(appmod, "search_archive", lambda q, **k: [dict(t) for t in treffer])
    monkeypatch.setattr(appmod, "search_usenet", lambda q, cats: [])
    monkeypatch.setattr(appmod, "catalog_urls", lambda: [])
    monkeypatch.setattr(appmod, "norm", lambda s: "sh2" if "Silent Hill 2" in s else s.lower())
    monkeypatch.setattr(appmod, "in_library", lambda t, p: "PS2" in t)

    res = appmod.do_search("egal", [])
    nach_titel = {r["title"]: r for r in res}
    assert all(r["grp_in_library"] for r in res if r["gkey"] == "sh2"), \
        "die PC-Fassung gilt nicht als vorhanden, obwohl das Spiel auf PS2 daliegt"
    assert nach_titel["Ein anderes Spiel"]["grp_in_library"] is False

    # Die Gruppe wandert ans Ende — wie ein einzelner vorhandener Treffer es taete.
    assert res[0]["title"] == "Ein anderes Spiel", \
        f"oben steht {res[0]['title']!r}; die vorhandene Gruppe gehoert ans Ende"
    # ... und INNERHALB der Gruppe steht die vorhandene Fassung vorn, damit der Vertreter
    # der Karte zum gruenen Haken passt.
    gruppe = [r for r in res if r["gkey"] == "sh2"]
    assert gruppe[0]["title"] == "Silent Hill 2 PS2", \
        f"die Gruppe wird von {gruppe[0]['title']!r} vertreten — das traegt keinen Haken"


def test_an_entirely_missing_game_stays_above_a_partly_owned_one(appmod, monkeypatch):
    """Der Zweck der Suche ist das Anfragen. (#691)"""
    treffer = [_tr("Habe ich auf PS2", "ps2"), _tr("Habe ich gar nicht", "pc")]
    monkeypatch.setattr(appmod, "search_archive", lambda q, **k: [dict(t) for t in treffer])
    monkeypatch.setattr(appmod, "search_usenet", lambda q, cats: [])
    monkeypatch.setattr(appmod, "catalog_urls", lambda: [])
    monkeypatch.setattr(appmod, "in_library", lambda t, p: "PS2" in t)
    res = appmod.do_search("egal", [])
    assert [r["title"] for r in res] == ["Habe ich gar nicht", "Habe ich auf PS2"]


def test_every_result_carries_the_group_state(appmod, monkeypatch):
    """Ohne das Feld faellt die Oberflaeche stumm auf `undefined` zurueck. (#691)"""
    monkeypatch.setattr(appmod, "search_archive", lambda q, **k: [_tr("A", "pc"), _tr("B", "ps2")])
    monkeypatch.setattr(appmod, "search_usenet", lambda q, cats: [])
    monkeypatch.setattr(appmod, "catalog_urls", lambda: [])
    monkeypatch.setattr(appmod, "in_library", lambda t, p: False)
    res = appmod.do_search("egal", [])
    assert res and all("grp_in_library" in r for r in res), \
        "nicht jeder Treffer traegt `grp_in_library`"


def test_no_hard_coded_green_is_left_in_the_stylesheet(appmod):
    """Die Ursache war das Literal, nicht der Farbton. (#660)

    Das Gruen stand an fuenf Stellen, vier davon fest im Stylesheet — deshalb bekamen alle
    vier Designs dasselbe Signalgruen, egal wie sie sonst aussahen. Nur EINE Stelle
    umzufaerben haette Anfrageliste und Abdeckung gruen gelassen, waehrend die Karten sich
    aendern; das waere schlimmer gewesen als der Ausgangszustand.

    Dieser Waechter faengt den Rueckfall: Wer die naechste „vorhanden"-Stelle wieder mit
    einer festen Farbe baut, faellt hier auf.
    """
    # DER GANZE BAUM, KEINE HANDGEPFLEGTE LISTE (#699). Dieser Waechter sah zuerst nur ins
    # Stylesheet — und uebersah SIEBEN Literale, die als Inline-Stile im JavaScript standen.
    # Auf Aurora hiess das: das neue gedaempfte Gruen auf den Karten, das alte Signalgruen
    # auf dem Freigabeknopf. Genau die Spaltung, die #660 beseitigen sollte, eine Datei
    # weiter.
    #
    # Eine Liste zu pflegen haette denselben Fehler nur verschoben: Ein Mutationstest hat
    # gezeigt, dass niemand merkt, wenn eine Datei wieder herausfaellt. Deshalb wird
    # GESUCHT statt aufgezaehlt — eine neue Datei ist damit von selbst mit abgedeckt.
    gefunden, gesehen = [], []
    for wurzel in ("static", "templates"):
        for pfad, _, dateien in os.walk(os.path.join(REPO, wurzel)):
            for name in dateien:
                if not name.endswith((".css", ".js", ".html", ".json", ".svg")):
                    continue
                voll = os.path.join(pfad, name)
                gesehen.append(os.path.relpath(voll, REPO).replace(os.sep, "/"))
                inhalt = open(voll, encoding="utf-8", errors="replace").read()
                for ton in ("#1e5e3a", "#2ecc71", "#3fb950"):
                    if ton in inhalt:
                        gefunden.append(f"{os.path.relpath(voll, REPO)}: {ton}")

    # DER WAECHTER MUSS SEINE EIGENE REICHWEITE BELEGEN. Ein Mutationstest hat gezeigt,
    # dass er sich lautlos verengen laesst: Suchwurzel auf `static/css` zurueckgestellt,
    # Literal ins JavaScript zurueckgelegt — und alles blieb gruen. Das ist derselbe
    # Fehler wie der, den dieser Test verhindern soll, nur eine Ebene hoeher.
    #
    # Diese drei Dateien tragen den Zustand „vorhanden" heute. Faellt eine aus der Suche,
    # scheitert der Test hier und nicht erst, wenn jemand die Farben nachmisst.
    for pflicht in ("static/css/index.css", "static/js/index.js", "templates/index.html"):
        assert pflicht in gesehen, \
            f"die Suche hat {pflicht} nicht angesehen — der Waechter wurde verengt"
    assert len(gesehen) >= 8, f"nur {len(gesehen)} Dateien durchsucht, das ist zu wenig"

    assert not gefunden, \
        "festes Gruen statt --ok/--ok-bg:\n  " + "\n  ".join(gefunden)
    css = open(os.path.join(REPO, "static", "css", "index.css"), encoding="utf-8").read()
    # Und die Variablen muessen wirklich JE DESIGN gesetzt sein, nicht nur einmal global.
    assert css.count("--ok:") == 4, \
        f"--ok ist {css.count('--ok:')}x gesetzt, erwartet 4 (ein Wert je Design)"
    assert css.count("--ok-bg:") == 4, \
        f"--ok-bg ist {css.count('--ok-bg:')}x gesetzt, erwartet 4"


def test_no_emoji_left_in_the_navigation_translations(appmod):
    """Ein Symbol im Uebersetzungstext ueberlebt und steht dann NEBEN dem Zeichen. (#658)

    `logout` trug „🚪 Abmelden" in allen fuenf Dateien — deshalb war es das einzige der drei
    Benutzermenue-Symbole, das ueberhaupt sichtbar war (die anderen beiden loeschte
    `applyI18n` schon beim Laden, siehe #337). Bleibt es stehen, sieht man kuenftig Zeichen
    UND Emoji nebeneinander.
    """
    import re
    emoji = re.compile("[\U0001F300-\U0001FAFF]")
    schluessel = ("nav_discover", "nav_requests", "nav_issues", "nav_coverage",
                  "nav_library", "nav_messages", "nav_settings", "nav_users",
                  "nav_lists", "profile", "logout")
    for lang in ("de", "en", "fr", "es", "it"):
        p = os.path.join(REPO, "static", "i18n", f"{lang}.json")
        d = json.load(open(p, encoding="utf-8"))
        for k in schluessel:
            wert = d.get(k, "")
            assert not emoji.search(wert), f"{lang}.json: {k} traegt noch ein Emoji: {wert!r}"
    # ... und in der deutschen Tabelle, die INLINE im JavaScript steht — die sechste Stelle,
    # die genau deshalb regelmaessig vergessen wird.
    js = open(os.path.join(REPO, "static", "js", "index.js"), encoding="utf-8").read()
    tabelle = js[js.index("const I18N={de:{"):]
    tabelle = tabelle[:tabelle.index("}};") + 3]
    for k in schluessel:
        m = re.search(r'"' + k + r'":"([^"]*)"', tabelle)
        if m:
            assert not emoji.search(m.group(1)), \
                f"inline-Tabelle: {k} traegt noch ein Emoji: {m.group(1)!r}"


def test_every_css_variable_used_actually_exists(appmod):
    """Ein Tippfehler in einer Variablen ist LAUTLOS. (#699)

    CSS wirft dafuer nichts: `var(--okk)` ist kein Fehler, die Eigenschaft bleibt einfach
    ungesetzt, und die Farbe faellt auf den Erbwert zurueck. Ein Mutationstest hat genau
    das gezeigt — `var(--ok)` zu `var(--okk)` verbogen, und weder der Quelltextwaechter
    noch der Browsertest merkten es. Der eine sah nur nach Literalen, der andere pruefte
    eine nachgebaute Probe statt der echten Stelle.

    Geprueft wird deshalb der Bezug selbst: Jede benutzte Variable muss irgendwo definiert
    sein. Das faengt den Tippfehler an JEDER Stelle, nicht nur bei den gruenen.
    """
    import re
    css = open(os.path.join(REPO, "static", "css", "index.css"), encoding="utf-8").read()
    js = open(os.path.join(REPO, "static", "js", "index.js"), encoding="utf-8").read()
    html = open(os.path.join(REPO, "templates", "index.html"), encoding="utf-8").read()

    # Definiert wird ausschliesslich im Stylesheet (`--name:`), benutzt ueberall.
    definiert = set(re.findall(r"(--[a-z0-9-]+)\s*:", css))
    assert len(definiert) > 15, f"nur {len(definiert)} Variablen gefunden — Muster stimmt nicht"

    fehlend = []
    for datei, inhalt in (("index.css", css), ("index.js", js), ("index.html", html)):
        for name in set(re.findall(r"var\(\s*(--[a-z0-9-]+)", inhalt)):
            if name not in definiert:
                fehlend.append(f"{datei}: var({name})")
    assert not fehlend, \
        ("diese Variablen werden benutzt, aber nirgends gesetzt — CSS meldet das nicht:\n  "
         + "\n  ".join(sorted(fehlend)))


# Was noch als feste Farbe im JavaScript steht, Ton -> Anzahl, JE TON MIT GRUND (#705).
#
# Aus 153 Vorkommen wurden 29, und der Rest ist kein Rueckstand, sondern Absicht. Deshalb
# steht hier eine Begruendung statt einer nackten Zahl: Wer den naechsten Eintrag
# hinzufuegt, muss einen schreiben koennen — sonst gehoert die Farbe in eine Variable.
JS_FESTE_FARBEN = {
    # Weisse Schrift auf farbigem Grund. Sie folgt keinem Design, sondern dem Grund unter
    # ihr, und der ist bereits eine Variable.
    "#fff": 18,
    # Avatar-Palette: Diese fuenf muessen sich VONEINANDER unterscheiden, damit zwei
    # Nutzer nicht dieselbe Farbe bekommen. Mit dem Design mitzuwandern wuerde genau das
    # zerstoeren.
    "#e0679a": 1, "#5bbf8a": 1, "#d9a441": 1, "#9b6dd6": 1, "#4bb7c6": 1,
    # Der Streamen-Knopf. Ein eigenes Blau, weil er neben dem Spielen-Knopf steht und sich
    # von ihm unterscheiden muss; eine benannte Rolle dafuer gibt es noch nicht.
    "#2a4d8f": 2,
    # Zustand `unverified` beim Wunschlisten-Import — ein Hinweisblau. Es gibt kein
    # --info; die uebrigen Zustaende der Tabelle nutzen bereits Variablen.
    "#58a6ff": 3,
    # Durchscheinendes Schwarz als Fortschrittsspur. Wirkt ueber jedem Grund gleich.
    "#0003": 1,
}


def _js_ohne_kommentare():
    """Der Quelltext ohne Kommentare — dort stehen die Issue-Nummern (`#661`), und die
    sehen fuer jede Farbsuche aus wie Hex-Werte."""
    import re
    js = open(os.path.join(REPO, "static", "js", "index.js"), encoding="utf-8").read()
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    js = re.sub(r"(?m)^\s*//.*$", "", js)
    return re.sub(r"(?<![:'\"\w])//[^\n'\"]*$", "", js, flags=re.M)


def test_no_new_hard_coded_colour_appears_in_the_javascript(appmod):
    """Ein Waechter, der Werte aufzaehlt, kann keinen Wert bemerken, den niemand kannte. (#703)

    Genau das ist passiert: Der Waechter aus #699 prueft auf `#1e5e3a`, `#2ecc71` und
    `#3fb950`. Ein VIERTES Erfolgsgruen, `#2a6f4b` am Abzeichen „laufende Anfragen", lief
    ungehindert durch — dieselbe Bedeutung, anderer Ton, kein Treffer.

    Dieser Test dreht die Richtung um: Statt bekannte Suender zu suchen, haelt er den
    GESAMTBESTAND fest. Jede neue feste Farbe faellt auf, auch eine, an die niemand
    gedacht hat.

    ER SUCHT DABEI JEDES HEX-LITERAL, nicht nur die in `color:`-Position. Ein Mutationstest
    hat gezeigt, warum: `msg.style.color='#3d9970'` ist eine ZUWEISUNG und kam in der
    engeren Suche nicht vor. Dieselbe Luecke verbarg vier echte Statusfarben
    (`#7ac57a`, `#c9a227`, `#16a34a`, `#d97706`), die ueber Nachschlagetabellen gesetzt
    werden — gefunden, als die Suche breiter wurde.
    """
    import re, collections
    ohne = _js_ohne_kommentare()
    ist = collections.Counter(m.group(0).lower() for m in
                              re.finditer(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{1,5})?\b", ohne))

    neu = {t: n for t, n in ist.items() if t not in JS_FESTE_FARBEN}
    assert not neu, (
        "neue feste Farbe(n) im JavaScript: "
        + ", ".join(f"{t} ({n}x)" for t, n in sorted(neu.items()))
        + "\nEntweder eine Variable benutzen oder bewusst in JS_FESTE_FARBEN eintragen.")

    mehr = {t: (n, JS_FESTE_FARBEN[t]) for t, n in ist.items()
            if n > JS_FESTE_FARBEN.get(t, 0)}
    assert not mehr, (
        "eine feste Farbe wird jetzt oefter benutzt als festgehalten: "
        + ", ".join(f"{t} {a} statt {b}" for t, (a, b) in sorted(mehr.items())))

    # Und die Statusfarben duerfen gar nicht mehr auftauchen.
    for ton in ("#d29922", "#f85149", "#6e2a2a", "#c0392b", "#2a6f4b", "#5a4410",
                "#7ac57a", "#c9a227", "#16a34a", "#d97706"):
        assert ton not in ist, f"{ton} ist wieder eine feste Farbe statt einer Variablen"


def test_every_theme_defines_the_full_status_set(appmod):
    """Eine Variable, die nur ein Design setzt, ist tueckischer als ein Literal. (#703)

    `--gefahr`, `--gefahr-b`, `--gefahr-h` und `--bad` standen ausschliesslich im
    Aurora-Block. In den anderen drei Designs fiel jedes `var(--bad,#f85149)` auf sein
    Literal zurueck — der Code las sich, als waere das Thema erledigt.
    """
    import re
    css = open(os.path.join(REPO, "static", "css", "index.css"), encoding="utf-8").read()
    # Kommentare raus, sonst zaehlt ein `--gefahr:` im Fliesstext mit.
    ohne = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for name in ("--ok", "--ok-bg", "--warn", "--warn-bg", "--bad", "--err-bg",
                 "--gefahr", "--gefahr-b", "--gefahr-h", "--btn2"):
        n = len(re.findall(re.escape(name) + r"\s*:", ohne))
        assert n == 4, f"{name} ist {n}x gesetzt, erwartet 4 — ein Wert je Design"


# ---------------------------------------------------------------------------
# #712 / #713 — Kontingent nach Volumen, und je Nutzer
# ---------------------------------------------------------------------------

def _kontingent(appmod, **werte):
    """Globales Kontingent setzen und den Ausgangsstand zurueckgeben."""
    s = appmod.load_settings()
    s["quota"] = {"enabled": True, "count": 0, "days": 7, "bytes": 0, **werte}
    appmod.save_settings(s)


def _auftrag(appmod, user, groesse, zustand="done", alter_tage=0):
    appmod.JOBS.append({"id": str(len(appmod.JOBS)), "title": f"T{len(appmod.JOBS)}",
                        "user": user, "size": groesse, "state": zustand,
                        "created": int(appmod.time.time()) - alter_tage*86400})


def test_the_quota_counts_bytes_not_only_requests(appmod, monkeypatch):
    """Die Anzahl begrenzt nicht das, was ausgeht. (#712)

    Ein SNES-Modul wiegt ~4 MB, ein PS3-Titel ~30 GB — Faktor 7.500. Zehn Anfragen koennen
    also 40 MB oder 300 GB heissen, und eine Zahl, die beides gleich behandelt, begrenzt
    keinen Plattenplatz.
    """
    monkeypatch.setattr(appmod, "JOBS", [])
    _kontingent(appmod, bytes=10 * 1024**3)          # 10 GB, keine Anzahlgrenze
    _auftrag(appmod, "a", 4 * 1024**3)
    with appmod.app.test_request_context():
        info = appmod.quota_info("a")
    assert info["enabled"]
    assert info["used_bytes"] == 4 * 1024**3
    assert info["remaining_bytes"] == 6 * 1024**3
    # Die Anzahl ist AUS — sie darf hier nicht bremsen.
    assert info["remaining"] > 100, "die abgeschaltete Anzahl begrenzt trotzdem"
    _auftrag(appmod, "a", 7 * 1024**3)
    with appmod.app.test_request_context():
        assert appmod.quota_info("a")["remaining_bytes"] == 0, "das Volumen laeuft nicht voll"


def test_both_quota_limits_can_be_used_and_switched_off(appmod, monkeypatch):
    """Jede Grenze fuer sich. (#712)

    Eine Anzahl allein laesst 300 GB durch, ein Volumen allein hundert winzige Anfragen.
    Wer beides setzt, ist gegen beides geschuetzt — und wer eines auf 0 setzt, schaltet
    genau dieses ab.
    """
    monkeypatch.setattr(appmod, "JOBS", [])
    _kontingent(appmod, count=3, bytes=0)
    for _ in range(3): _auftrag(appmod, "a", 1)
    with appmod.app.test_request_context():
        i = appmod.quota_info("a")
    assert i["remaining"] == 0, "die Anzahl greift nicht"
    assert i["remaining_bytes"] is None, "ein abgeschaltetes Volumen meldet trotzdem einen Rest"

    monkeypatch.setattr(appmod, "JOBS", [])
    _kontingent(appmod, count=0, bytes=1024)
    _auftrag(appmod, "a", 900)
    with appmod.app.test_request_context():
        i = appmod.quota_info("a")
    assert i["remaining_bytes"] == 124
    assert i["remaining"] > 100, "die abgeschaltete Anzahl begrenzt trotzdem"


def test_denied_and_failed_requests_do_not_spend_the_quota(appmod, monkeypatch):
    """Abgelehntes wurde nie geholt, ein Fehlschlag hat nichts abgelegt. (#712)

    `pending` zaehlt dagegen sehr wohl — sonst liesse sich die Grenze umgehen, indem man
    schneller anfragt, als die Warteschlange leert.
    """
    monkeypatch.setattr(appmod, "JOBS", [])
    _kontingent(appmod, count=10, bytes=1000)
    _auftrag(appmod, "a", 100, "denied")
    _auftrag(appmod, "a", 100, "error")
    _auftrag(appmod, "a", 100, "pending")
    n, b = appmod.quota_used("a", 7)
    assert (n, b) == (1, 100), f"gezaehlt wurden {n} Auftraege / {b} Bytes, erwartet 1 / 100"


def test_a_user_can_have_their_own_quota(appmod, monkeypatch):
    """Vorher gab es nur global plus `quota_exempt` — alles oder nichts. (#713)"""
    monkeypatch.setattr(appmod, "JOBS", [])
    _kontingent(appmod, count=5, bytes=1000)
    appmod.save_users({**ADMIN_FIX,
                       "gross": {"pw": "x", "role": "user", "perms": ["request"],
                                 "quota": {"count": 20, "bytes": 9000}},
                       "normal": {"pw": "x", "role": "user", "perms": ["request"]}})
    try:
        assert appmod.quota_grenzen("gross") == (20, 9000), "die eigene Vorgabe greift nicht"
        assert appmod.quota_grenzen("normal") == (5, 1000), "ohne eigene Vorgabe gilt die globale"
        # Eine eigene Vorgabe darf auch NIEDRIGER sein als die globale.
        appmod.save_users({**appmod.load_users(),
                           "klein": {"pw": "x", "role": "user", "perms": ["request"],
                                     "quota": {"count": 1}}})
        assert appmod.quota_grenzen("klein") == (1, 1000), \
            "eine teilweise eigene Vorgabe muss den Rest global lassen"
    finally:
        appmod.save_users({})


def test_the_download_endpoint_actually_refuses_an_oversized_request(appmod, client, monkeypatch):
    """Eine Grenze, die nicht greift, ist Zierde. (#712)

    Ein Mutationstest hat es gezeigt: Die Volumenpruefung aus `/api/download` liess sich
    entfernen, ohne dass ein Test anschlug — geprueft war nur die Rechnung in
    `quota_info`, nicht die Weigerung.

    Geprueft wird gegen die Groesse DIESER Anfrage, nicht nur gegen den Verbrauch. Sonst
    passte der letzte Titel immer noch hinein, egal wie gross er ist.
    """
    monkeypatch.setattr(appmod, "JOBS", [])
    _kontingent(appmod, count=0, bytes=5 * 1024**3)      # 5 GB, Anzahl aus
    _als(client, appmod, "admin")
    appmod.save_users({**appmod.load_users(),
                       "knapp": {"pw": appmod.generate_password_hash("pw123456"),
                                 "role": "user", "perms": ["request"]}})
    _als(client, appmod, "knapp", rolle="user")
    try:
        # 2 GB passen
        r = client.post("/api/download", json={"title": "Klein", "source": "archive",
                                               "ref": "k", "size": 2 * 1024**3})
        assert r.get_json().get("ok"), f"eine passende Anfrage wurde abgewiesen: {r.get_json()}"
        # 4 GB passen NICHT mehr — 3 GB sind uebrig
        r = client.post("/api/download", json={"title": "Gross", "source": "archive",
                                               "ref": "g", "size": 4 * 1024**3})
        d = r.get_json()
        assert not d.get("ok"), "die zu grosse Anfrage wurde angenommen"
        assert "ontingent" in (d.get("msg") or "") or "quota" in (d.get("msg") or "").lower(), \
            f"die Ablehnung nennt den Grund nicht: {d}"
    finally:
        appmod.save_users({})


def test_the_download_endpoint_refuses_once_the_count_is_spent(appmod, client, monkeypatch):
    """Die Anzahlgrenze war an der Durchsetzung nie geprueft. (#712)

    Das ist ein VORBESTEHENDES Loch, gefunden beim Mutationstest zu dieser Aenderung: Die
    Zeile `if qi.get("remaining", 1) <= 0` liess sich durch `if False` ersetzen, und die
    komplette Testreihe blieb gruen. Geprueft war nur die Rechnung, nie die Weigerung.
    """
    monkeypatch.setattr(appmod, "JOBS", [])
    _kontingent(appmod, count=2, bytes=0)                # 2 Anfragen, Volumen aus
    _als(client, appmod, "admin")
    appmod.save_users({**appmod.load_users(),
                       "zwei": {"pw": appmod.generate_password_hash("pw123456"),
                                "role": "user", "perms": ["request"]}})
    _als(client, appmod, "zwei", rolle="user")
    try:
        for i in (1, 2):
            r = client.post("/api/download", json={"title": f"T{i}", "source": "archive",
                                                   "ref": str(i), "size": 1})
            assert r.get_json().get("ok"), f"Anfrage {i} wurde abgewiesen: {r.get_json()}"
        r = client.post("/api/download", json={"title": "T3", "source": "archive",
                                               "ref": "3", "size": 1})
        d = r.get_json()
        assert not d.get("ok"), "die dritte Anfrage kam durch, obwohl das Kontingent 2 ist"
    finally:
        appmod.save_users({})


# ---------------------------------------------------------------------------
# #714 — Benachrichtigungen je Ereignis
# ---------------------------------------------------------------------------

def test_an_event_deselected_for_the_instance_reaches_nobody(appmod, monkeypatch):
    """Die Zusage ist, dass abgewaehlt auch abgewaehlt heisst. (#714)"""
    gesendet = []
    monkeypatch.setattr(appmod, "safe_post", lambda url, **k: gesendet.append(url))
    s = appmod.load_settings()
    s["discord"] = {"enabled": True, "url": "https://example.invalid/hook"}
    s["notify_events"] = {"issue_new": False}
    appmod.save_settings(s)
    try:
        assert appmod.notify_send("x", "available") or True   # nicht abgewaehlt -> Weg frei
        vorher = len(gesendet)
        appmod.notify_send("y", "issue_new")
        assert len(gesendet) == vorher, "ein abgewaehltes Ereignis wurde trotzdem gesendet"
    finally:
        s.pop("notify_events", None); s["discord"] = {"enabled": False, "url": ""}
        appmod.save_settings(s)


def test_the_default_reproduces_todays_behaviour(appmod):
    """Wer nichts einstellt, merkt nichts. (#714)

    Fehlt die Auswahl oder der einzelne Schluessel, gilt EIN. Waere es andersherum, waere
    nach dem Update jede Benachrichtigung stumm — und niemand haette einen Anhaltspunkt,
    warum.
    """
    assert appmod._ereignis_erlaubt(None, "available")
    assert appmod._ereignis_erlaubt({}, "available")
    assert appmod._ereignis_erlaubt({"message": False}, "available"), \
        "ein anderer abgewaehlter Schluessel darf diesen nicht mitnehmen"
    assert not appmod._ereignis_erlaubt({"available": False}, "available")
    # Ohne Ereignis wird nicht gefiltert — der Testversand haengt sonst an einer Auswahl.
    assert appmod._ereignis_erlaubt({"available": False}, None)


def test_a_user_can_deselect_an_event_for_their_own_channels(appmod):
    """Vier Ereignisse erreichen die persoenlichen Kanaele; keines war waehlbar. (#714)"""
    appmod.save_users({**ADMIN_FIX,
                       "still": {"pw": "x", "role": "user", "perms": ["request"],
                                 "notify_events": {"message": False}}})
    try:
        assert appmod.nutzer_will("still", "available"), "nicht abgewaehltes Ereignis blockiert"
        assert not appmod.nutzer_will("still", "message"), "abgewaehltes Ereignis kommt durch"
        assert appmod.nutzer_will("admin", "message"), "ohne Auswahl muss alles durchgehen"
    finally:
        appmod.save_users({})


def test_every_notifying_call_site_names_its_event(appmod):
    """Ein Anlass ohne Namen ist nicht abwaehlbar — und faellt niemandem auf. (#714)

    Geprueft wird die Quelle, weil sich sonst genau die Stelle einschleicht, die vergessen
    wurde: Beim Bauen dieser Aenderung blieben zwei von sechs Aufrufen zunaechst ohne
    Anlass, und beide Male sah alles richtig aus.

    Die beiden TESTendpunkte tragen bewusst keinen — ein Testversand, der von einer
    Auswahl abhaengt, prueft die Auswahl statt den Weg.
    """
    import re
    quelle = open(os.path.join(REPO, "app.py"), encoding="utf-8").read()
    ohne = []
    for m in re.finditer(r"(notify_send|send_push_to_user)\((.{0,400}?)\)\s*(?:\n|$)",
                         quelle, re.S):
        ruf = m.group(0)
        if "def " in ruf or "ereignis" in ruf:
            continue
        if not re.search(r'"(available|wish_granted|request_new|issue_new|message|request_for)"', ruf):
            ohne.append(ruf.split("\n")[0].strip()[:70])
    # Genau zwei duerfen uebrig bleiben: /api/push/test und /api/notify/test.
    assert len(ohne) <= 2, "Aufrufe ohne Anlass:\n  " + "\n  ".join(ohne)

    # UND DIE PERSOENLICHEN WEBHOOKS, die nicht ueber `send_push_to_user` laufen. Ein
    # Mutationstest hat gezeigt, dass ihre Wache fehlen kann, ohne dass etwas anschlaegt:
    # `nutzer_will` war geprueft, die STELLEN, die es benutzen, nicht.
    # Gemeint sind die PERSOENLICHEN Webhooks — erkennbar daran, dass sie aus
    # `load_users()` kommen. Der Discord-Webhook der Instanz steht in `notify_send` und
    # wird dort schon gefiltert; ihn mitzupruefen war der erste, zu weite Versuch.
    persoenlich = re.findall(
        r'load_users\(\)[^\n]*get\("webhook"[^\n]*\n\s*(if wh[^\n]*:)', quelle)
    assert persoenlich, "keine persoenlichen Webhooks gefunden — das Muster stimmt nicht"
    for zeile in persoenlich:
        assert "nutzer_will" in zeile, \
            f"ein persoenlicher Webhook sendet ungefiltert: {zeile.strip()}"


# ---------------------------------------------------------------------------
# #721 — die Suchquellen laufen nebeneinander
# ---------------------------------------------------------------------------

def test_the_three_search_sources_run_side_by_side(appmod, monkeypatch):
    """In Reihe war die Gesamtzeit die SUMME. (#721)

    Gemessen am laufenden Stand: Ein Klick auf eine Entdecken-Karte brauchte 15,8 s bis
    zur ersten Trefferkarte, und praktisch alles davon war `/api/search`. Bei Fristen von
    15 s (Archive.org) und 25 s (Prowlarr) waere der schlechteste Fall 40 s.

    Geprueft wird die ZUSAGE, nicht die Zahl: Drei Quellen, die je 0,3 s brauchen, duerfen
    zusammen nicht 0,9 s dauern. Eine Zeitmessung ist hier zulaessig, weil der Unterschied
    zwischen Summe und Maximum um den Faktor 3 auseinanderliegt — nicht um Millisekunden.
    """
    import time as _t
    def langsam(_x=None, *a, **k):
        _t.sleep(0.3)
        return []
    monkeypatch.setattr(appmod, "search_archive", langsam)
    monkeypatch.setattr(appmod, "search_usenet", lambda q, cats: langsam())
    monkeypatch.setattr(appmod, "search_filehoster", langsam)
    monkeypatch.setattr(appmod, "catalog_urls", lambda: ["x"])

    start = _t.perf_counter()
    appmod.do_search("egal", [])
    dauer = _t.perf_counter() - start
    assert dauer < 0.7, \
        (f"die Suche brauchte {dauer:.2f}s fuer drei Quellen zu je 0,3s — "
         "das ist die Summe, nicht das Maximum")


def test_one_dead_source_does_not_take_the_search_down(appmod, monkeypatch):
    """Eine tote Quelle darf die anderen nicht mitnehmen. (#721)

    Die drei fangen ihre Fehler selbst ab — aber ein UNERWARTETER Fehler waere in einem
    Faden sonst das Ende der ganzen Suche, und der Nutzer saehe „keine Treffer" statt der
    Treffer, die es sehr wohl gab.
    """
    def kaputt(*a, **k):
        raise RuntimeError("Quelle antwortet nicht")
    monkeypatch.setattr(appmod, "search_archive", kaputt)
    monkeypatch.setattr(appmod, "search_usenet",
                        lambda q, cats: [_tr("Aus Usenet", "snes", "usenet")])
    monkeypatch.setattr(appmod, "catalog_urls", lambda: [])
    monkeypatch.setattr(appmod, "in_library", lambda t, p: False)

    res = appmod.do_search("egal", [])
    assert [r["title"] for r in res] == ["Aus Usenet"], \
        f"die lebende Quelle ging mit unter: {res}"


# ---------------------------------------------------------------------------
# #724 — eine RomM-Sitzung, nicht eine je Nachschlagen
# ---------------------------------------------------------------------------

class _RommAntwort:
    def __init__(self, code=200, daten=None):
        self.status_code = code
        self._daten = daten if daten is not None else {"items": []}
    @property
    def ok(self):
        return 200 <= self.status_code < 300
    def json(self):
        return self._daten


class _RommSitzung:
    """Zaehlt Anmeldungen und Abfragen. Die Antwort auf die Suche ist steuerbar."""
    def __init__(self, zaehler, suchcodes):
        self._z, self._codes = zaehler, suchcodes
    def post(self, url, **k):
        self._z["login"] += 1
        return _RommAntwort(200)
    def get(self, url, **k):
        self._z["suche"] += 1
        code = self._codes.pop(0) if self._codes else 200
        return _RommAntwort(code, {"items": [{"name": "Chrono Trigger", "id": 7,
                                              "platform_slug": "snes",
                                              "fs_size_bytes": 1024}]})


def _romm_stub(appmod, monkeypatch, suchcodes=None):
    zaehler = {"login": 0, "suche": 0}
    codes = list(suchcodes or [])
    class _Req:
        @staticmethod
        def Session():
            return _RommSitzung(zaehler, codes)
    monkeypatch.setattr(appmod, "requests", _Req)
    appmod._ROMM_SITZUNG.update(s=None, schluessel=None, bis=0.0)
    return zaehler


def _romm_cfg(appmod, monkeypatch, passwort="geheim"):
    werte = {"romm_url": "http://romm", "romm_user": "u", "romm_pass": passwort}
    monkeypatch.setattr(appmod, "cfg", lambda k: werte.get(k, ""))
    return werte


def test_romm_does_not_log_in_again_for_every_lookup(appmod, monkeypatch):
    """Die Anmeldung kostet rund eine Sekunde. (#724)

    Im Container gegen das laufende RomM gemessen:

        login 926 ms   suche 1486 ms
        login 993 ms   suche 1574 ms

    Sie wurde bei JEDEM `romm_find` erneut bezahlt, also bei jeder geoeffneten Karte.
    """
    z = _romm_stub(appmod, monkeypatch)
    _romm_cfg(appmod, monkeypatch)
    appmod.romm_find("Chrono Trigger", "snes")
    appmod.romm_find("Chrono Trigger", "snes")
    appmod.romm_find("Chrono Trigger", "snes")
    assert z["suche"] == 3, f"es wurde nicht dreimal gesucht: {z}"
    assert z["login"] == 1, \
        f"es wurde {z['login']}-mal angemeldet statt einmal — die Sitzung wird nicht wiederverwendet"


def test_changed_credentials_invalidate_the_cached_romm_session(appmod, monkeypatch):
    """Sonst redet eine geaenderte Konfiguration weiter ueber das alte Plaetzchen. (#724)"""
    z = _romm_stub(appmod, monkeypatch)
    _romm_cfg(appmod, monkeypatch, passwort="alt")
    appmod.romm_find("Chrono Trigger", "snes")
    _romm_cfg(appmod, monkeypatch, passwort="neu")
    appmod.romm_find("Chrono Trigger", "snes")
    assert z["login"] == 2, \
        (f"nach dem Passwortwechsel wurde {z['login']}-mal angemeldet — die alte Sitzung "
         "wird weiterbenutzt")


def test_an_expired_romm_session_logs_in_once_more_and_retries(appmod, monkeypatch):
    """Sonst wird aus der wiederverwendeten Sitzung ein Feature mit Verfallsdatum. (#724)

    Die erste Suche antwortet mit 401, die zweite mit 200 — das Ergebnis muss trotzdem
    ankommen, und es darf GENAU EINE zusaetzliche Anmeldung geben.
    """
    z = _romm_stub(appmod, monkeypatch, suchcodes=[401, 200])
    _romm_cfg(appmod, monkeypatch)
    treffer = appmod.romm_find("Chrono Trigger", "snes")
    assert treffer and treffer["id"] == 7, \
        f"die abgelaufene Sitzung liess das Nachschlagen scheitern: {treffer}"
    assert z["login"] == 2, f"nicht genau eine Neuanmeldung: {z}"
    assert z["suche"] == 2, f"die Abfrage wurde nicht genau einmal wiederholt: {z}"


def test_the_romm_session_is_built_under_a_lock(appmod):
    """Seit #722 laufen Aufrufer nebeneinander. (#724)

    Ohne Schloss melden sich mehrere Faeden gleichzeitig an und ueberschreiben einander —
    genau die Sekunde, die hier eingespart werden soll, faellt dann mehrfach an.
    """
    import inspect
    quelle = inspect.getsource(appmod.romm_session)
    assert "_ROMM_LOCK" in quelle, \
        "romm_session legt die Sitzung ohne Schloss an — parallele Aufrufer melden sich doppelt an"


# ---------------------------------------------------------------------------
# #726 — kurzes Gedaechtnis je Suchquelle
# ---------------------------------------------------------------------------

def _suche_vorbereiten(appmod, monkeypatch):
    appmod.SUCH_CACHE.clear()
    monkeypatch.setattr(appmod, "catalog_urls", lambda: [])
    monkeypatch.setattr(appmod, "in_library", lambda t, p: False)
    monkeypatch.setattr(appmod, "search_usenet", lambda q, cats: [])


def test_the_same_search_twice_does_not_ask_the_source_twice(appmod, monkeypatch):
    """Archive.org braucht im Median 10,9 s — das zweimal ist einmal zu viel. (#726)

    Gemessen, fuenf Begriffe im Abstand von 15 s: 2,9 / 30 / 30 / 10,9 / 9,4 Sekunden.
    """
    _suche_vorbereiten(appmod, monkeypatch)
    rufe = []
    monkeypatch.setattr(appmod, "search_archive",
                        lambda q: rufe.append(q) or [_tr("Treffer", "snes", "archive")])
    appmod.do_search("Mario", [])
    appmod.do_search("Mario", [])
    assert len(rufe) == 1, f"die Quelle wurde {len(rufe)}-mal gefragt statt einmal"


def test_a_different_search_still_reaches_the_source(appmod, monkeypatch):
    """Der Zwischenspeicher haengt an der Suchzeile, nicht an der Quelle. (#726)"""
    _suche_vorbereiten(appmod, monkeypatch)
    rufe = []
    monkeypatch.setattr(appmod, "search_archive",
                        lambda q: rufe.append(q) or [_tr("Treffer", "snes", "archive")])
    appmod.do_search("Mario", [])
    appmod.do_search("Zelda", [])
    assert rufe == ["Mario", "Zelda"], f"die zweite Suche kam nicht durch: {rufe}"


def test_a_failing_source_falls_back_to_its_last_known_result(appmod, monkeypatch):
    """Der letzte bekannte Stand schlaegt „keine Treffer". (#726)

    Er ist derselbe, den dieselbe Suche vor Minuten geliefert haette — und Archive.org
    faellt gemessen oft genug aus, dass das der Unterschied zwischen Ergebnis und
    leerer Seite ist.
    """
    _suche_vorbereiten(appmod, monkeypatch)
    monkeypatch.setattr(appmod, "search_archive",
                        lambda q: [_tr("Aus dem Archiv", "snes", "archive")])
    appmod.do_search("Mario", [])
    appmod.SUCH_CACHE_TTL_ALT = appmod.SUCH_CACHE_TTL
    # Eintrag kuenstlich altern lassen, damit die Quelle wirklich gefragt wird
    for k in list(appmod.SUCH_CACHE):
        zeit, wert = appmod.SUCH_CACHE[k]
        appmod.SUCH_CACHE[k] = (zeit - appmod.SUCH_CACHE_TTL - 1, wert)

    def tot(q):
        raise RuntimeError("Zeitueberschreitung")
    monkeypatch.setattr(appmod, "search_archive", tot)
    res = appmod.do_search("Mario", [])
    assert [r["title"] for r in res] == ["Aus dem Archiv"], \
        f"die ausgefallene Quelle lieferte nichts statt des letzten Standes: {res}"


def test_an_empty_result_is_not_remembered(appmod, monkeypatch):
    """„Nichts gefunden" ist gueltig — aber als Zwischenstand eine Falle. (#726)

    Sonst taucht eine gerade importierte Datei minutenlang nicht auf.
    """
    _suche_vorbereiten(appmod, monkeypatch)
    rufe = []
    monkeypatch.setattr(appmod, "search_archive", lambda q: rufe.append(q) or [])
    appmod.do_search("Mario", [])
    appmod.do_search("Mario", [])
    assert len(rufe) == 2, "ein leeres Ergebnis wurde gemerkt — neue Treffer blieben unsichtbar"


def test_the_cached_results_are_copies_not_references(appmod, monkeypatch):
    """Die Aufrufer haengen den Treffern Flaggen an. (#726)

    Ohne Kopie waere der Zwischenstand nach dem ersten Aufruf verfaelscht — und zwei
    parallele Anfragen schrieben in dieselben Objekte.
    """
    _suche_vorbereiten(appmod, monkeypatch)
    monkeypatch.setattr(appmod, "search_archive",
                        lambda q: [_tr("Treffer", "snes", "archive")])
    erst = appmod.do_search("Mario", [])
    erst[0]["title"] = "VERAENDERT"
    erst[0]["in_library"] = True
    zweit = appmod.do_search("Mario", [])
    assert zweit[0]["title"] == "Treffer", \
        f"der Zwischenstand wurde vom Aufrufer veraendert: {zweit[0]['title']}"


def test_the_search_cache_is_bounded(appmod, monkeypatch):
    """Jede neue Suchzeile legt einen Eintrag an, und nichts raeumt auf. (#726)"""
    _suche_vorbereiten(appmod, monkeypatch)
    monkeypatch.setattr(appmod, "search_archive",
                        lambda q: [_tr("Treffer", "snes", "archive")])
    for i in range(appmod.SUCH_CACHE_MAX + 25):
        appmod.do_search(f"Suche {i}", [])
    assert len(appmod.SUCH_CACHE) <= appmod.SUCH_CACHE_MAX, \
        f"der Zwischenspeicher waechst unbegrenzt: {len(appmod.SUCH_CACHE)} Eintraege"


def test_a_timed_out_archive_search_is_not_reported_as_no_hits(appmod, monkeypatch):
    """Eine Zeitueberschreitung sah aus wie „nichts gefunden". (#726)

    Damit konnte der Aufrufer beides nicht unterscheiden — und ein Rueckfall auf den
    letzten bekannten Stand war unmoeglich.
    """
    class _Kaputt:
        @staticmethod
        def get(*a, **k):
            raise RuntimeError("Read timed out")
    monkeypatch.setattr(appmod, "requests", _Kaputt)
    import pytest as _p
    with _p.raises(Exception):
        appmod.search_archive("egal")


def test_search_cache_ttl_zero_really_turns_it_off(appmod, monkeypatch):
    """Ein Schalter, der nur die Haelfte abschaltet, ist schlimmer als keiner. (#726)

    Ohne diese Pruefung wuerde `SEARCH_CACHE_TTL=0` zwar keinen Treffer mehr aus dem
    Speicher geben, aber weiter merken — und eine ausgefallene Quelle lieferte dann
    trotzdem alte Daten.
    """
    _suche_vorbereiten(appmod, monkeypatch)
    monkeypatch.setattr(appmod, "SUCH_CACHE_TTL", 0)
    monkeypatch.setattr(appmod, "search_archive",
                        lambda q: [_tr("Treffer", "snes", "archive")])
    appmod.do_search("Mario", [])
    assert not appmod.SUCH_CACHE, \
        f"trotz TTL 0 wurde gemerkt: {list(appmod.SUCH_CACHE)}"

    def tot(q):
        raise RuntimeError("Zeitueberschreitung")
    monkeypatch.setattr(appmod, "search_archive", tot)
    assert appmod.do_search("Mario", []) == [], \
        "trotz TTL 0 kam ein alter Stand zurueck"
