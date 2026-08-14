"""Die Kernlogik der Bibliothekswerkzeuge — die Entscheidung „ein Spiel oder eine Sammlung?".

WARUM GERADE DIESE FUNKTIONEN: Der Umbau verschiebt Zehntausende Dateien. Fast alles
darin ist Dateisystemarbeit, die sich nur am echten Bestand messen laesst. Die EINE
Stelle, an der ein Denkfehler stillen Schaden anrichtet, ist die Erkennung: Wird eine
Sammlung faelschlich fuer ein Spiel gehalten, bleiben Hunderte Titel unsichtbar; wird ein
Multi-Disk-Spiel fuer eine Sammlung gehalten, zerfaellt es in Einzeldateien.

Diese Datei prueft deshalb die reinen Funktionen, nicht den Umbau selbst.

The tools move tens of thousands of files, and almost all of that is filesystem work that
can only be measured against a real library. The one place where a mistake does silent
damage is the classification, so that is what is tested here.
"""
import importlib.util
import json
import os
import re
import shutil

import pytest

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WERKZEUG = os.path.join(WURZEL, "contrib", "library-tools", "retronas-organisieren")
SORTIERER = os.path.join(WURZEL, "contrib", "library-tools", "retronas-mixed-sortieren")
PRUEFER = os.path.join(WURZEL, "contrib", "library-tools", "rom-abbilder-pruefen")


def _laden(pfad, name):
    """Ein Skript ohne `.py`-Endung als Modul laden — IMMER aus der Quelle.

    WARUM NICHT `SourceFileLoader` (#399): Der legt Bytecode unter `__pycache__` ab und
    haelt ihn fuer aktuell, wenn der Zeitstempel der Quelle passt — auf die SEKUNDE genau.
    Wird eine Datei mehrfach innerhalb derselben Sekunde geaendert, laeuft der Test gegen
    den alten Stand. Genau das ist passiert: Eine Aenderung um 06:00:45 lief gegen einen
    Cache von 06:00, der Test meldete das Verhalten VOR der Aenderung, und die Ursache
    stand nirgends — weder im Test noch im Quelltext.

    `compile` + `exec` kennt keinen Cache. Der Preis ist ein Uebersetzungsvorgang je
    Testlauf; er kostet Millisekunden.

    Always compile from source: the bytecode cache validates on a whole-second timestamp,
    so a file edited twice within one second runs the tests against the older version.
    """
    import types
    quelle = open(pfad, encoding="utf-8").read()
    mod = types.ModuleType(name)
    mod.__file__ = pfad
    exec(compile(quelle, pfad, "exec"), mod.__dict__)
    return mod


@pytest.fixture(scope="module")
def org():
    return _laden(WERKZEUG, "retronas_organisieren")


@pytest.fixture(scope="module")
def mix():
    return _laden(SORTIERER, "retronas_mixed_sortieren")


@pytest.fixture(scope="module")
def abb():
    return _laden(PRUEFER, "rom_abbilder_pruefen")


# --- Datentraeger-Marker: das einzige verlaessliche Zeichen -------------------------

@pytest.mark.parametrize("name", [
    "Spiel (Disk 1).d64",
    "Spiel (Disk 2 of 3).d64",
    "Spiel [Disc 2].iso",
    "Cassette 50 (1983)(Cascade)(Side A).zip",
    "Titel (Tape 1).tap",
    "Titel (Part 2).adf",
    "Titel (Diskette 1).img",
])
def test_disk_markers_are_recognised(org, name):
    """Alle gebraeuchlichen Schreibweisen des Datentraeger-Markers werden erkannt."""
    assert org.ohne_marker(name) != os.path.splitext(name)[0].lower(), \
        f"Marker in {name!r} nicht erkannt"


def test_two_sides_of_one_title_collapse_to_the_same_name(org):
    """Zwei Seiten desselben Titels fallen zusammen — das macht sie zu EINEM Spiel."""
    a = org.ohne_marker("Cassette 50 (1983)(Cascade)(Side A).zip")
    b = org.ohne_marker("Cassette 50 (1983)(Cascade)(Side B).zip")
    assert a == b


def test_two_different_titles_do_not_collapse(org):
    """Zwei verschiedene Titel fallen NICHT zusammen — auch bei langem gemeinsamem Anfang.

    Der gemessene Fall, an dem eine frueher erwogene Regel gescheitert waere: Diese beiden
    teilen 22 Zeichen am Anfang und sind zwei verschiedene Demos. Ein gemeinsamer
    Namensanfang taugt deshalb NICHT als Kriterium — der Datentraeger-Marker schon.
    """
    a = org.ohne_marker("VC Songs-Cartridge - Inventio-Pac.prg")
    b = org.ohne_marker("VC Songs-Cartridge - The Mad Boogy.prg")
    assert a != b


# --- Ordner: ein Spiel oder eine Sammlung? ------------------------------------------

def test_a_multi_disk_game_is_one_game(org, tmp_path):
    """Wenige Dateien, die sich auf denselben Titel reduzieren -> ein Spiel."""
    d = tmp_path / "Ultima IV"
    d.mkdir()
    for i in (1, 2, 3, 4):
        (d / f"Ultima IV (Disk {i}).d64").write_bytes(b"x" * 16)
    assert org.ist_spielordner(str(d), "c64") is True


def test_a_collection_is_not_one_game(org, tmp_path):
    """Viele verschiedene Titel -> Sammlung, auch wenn sie in einem Ordner liegen.

    Genau das war der Ausgangsfall: RomM zaehlte `OneLoad64-Games-Collection-v5` als EIN
    Spiel, obwohl 27.451 Dateien darin lagen.
    """
    d = tmp_path / "OneLoad64-Games-Collection-v5"
    d.mkdir()
    for n in ("Boulder Dash", "Turrican", "Giana Sisters", "Wizball", "Paradroid",
              "Uridium", "Armalyte", "Katakis", "Hawkeye", "Creatures",
              "Mayhem in Monsterland", "Rainbow Islands", "Bubble Bobble"):
        (d / f"{n}.prg").write_bytes(b"x" * 16)
    assert org.ist_spielordner(str(d), "c64") is False


def _dreamcast_titel(wurzel, name, spuren=("track01.bin", "track02.raw", "track03.bin")):
    """Baut den GEMESSENEN Dreamcast-Aufbau nach — nicht einen erfundenen.

    Vorlage ist `dc/Bangai-O (PAL)(M3)/` von der Anlage: eine `.gdi` mit dem Titelnamen,
    daneben generisch benannte Spuren. Genau diese Kombination hat der alte Test nie
    abgedeckt.
    """
    d = wurzel / name
    d.mkdir()
    zeilen = [str(len(spuren))]
    for i, s in enumerate(spuren, 1):
        zeilen.append(f"{i} {i * 600} 4 2352 {s} 0")
        (d / s).write_bytes(b"x" * 32)
    (d / f"{name}.gdi").write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return d


def test_a_disc_image_set_is_one_game(org, tmp_path):
    """Eine `.gdi` samt ihrer Spuren ist EIN Spiel. (#462)

    DER SCHADEN, DEN DIESER TEST VERHINDERT: Ohne ihn galt der Ordner als Sammlung und
    wurde flachgelegt. Die Spurnamen sind bei JEDEM Dreamcast-Spiel dieselben, kollidierten
    also und wurden zu `track01 (53).bin` — waehrend die `.gdi` weiter `track01.bin` nennt.
    Alle 138 Titel zeigten danach auf dieselbe Datei; am Emulator gemessen als tausende
    `W[GDROM]: Sector Read miss`, und Flycast blieb im BIOS stehen.

    Die alte Regel KONNTE das nicht sehen: Sie vergleicht Namen, und hier ist die
    Namensgleichheit absichtlich abwesend.
    """
    d = _dreamcast_titel(tmp_path, "Bangai-O v1.001 (2000)(Virgin)(PAL)(M3)[!]")
    assert org.ist_spielordner(str(d), "dc") is True


def test_a_disc_image_set_with_more_tracks_than_the_file_limit_is_still_one_game(org, tmp_path):
    """Auch mit 38 Spuren. (#462)

    `SPIEL_MAX_DATEIEN` ist 12, und `Bangai-O` hatte gemessen 38 Dateien. Stuende die
    Abbild-Pruefung HINTER der Dateizahl-Schranke, waere der Ordner weiterhin eine
    Sammlung — der Fix waere da und wirkungslos.
    """
    spuren = [f"track{i:02d}.raw" for i in range(1, 39)]
    d = _dreamcast_titel(tmp_path, "Grosses Spiel", spuren=spuren)
    assert len(list(d.iterdir())) > org.SPIEL_MAX_DATEIEN
    assert org.ist_spielordner(str(d), "dc") is True


def test_a_cue_sheet_names_its_own_bin(org, tmp_path):
    """`.cue` + `.bin` genauso — die Liste nennt ihre Datei. (#462)"""
    d = tmp_path / "Spiel (USA)"
    d.mkdir()
    (d / "Spiel (USA).bin").write_bytes(b"x" * 32)
    (d / "Spiel (USA).cue").write_text(
        'FILE "Spiel (USA).bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n',
        encoding="utf-8")
    assert org.ist_spielordner(str(d), "psx") is True


def test_two_different_titles_in_one_folder_stay_a_collection(org, tmp_path):
    """Zwei verschiedene Abbildlisten -> Sammlung, kein Spiel. (#462)

    Sonst wuerde der Fix aus jedem Ordner mit mehreren Abbildern ein einziges „Spiel"
    machen und das urspruengliche Problem in die andere Richtung wiederholen.
    """
    d = tmp_path / "Zwei Spiele"
    d.mkdir()
    for name in ("Spiel A", "Spiel B"):
        (d / f"{name}.bin").write_bytes(b"x" * 32)
        (d / f"{name}.cue").write_text(f'FILE "{name}.bin" BINARY\n', encoding="utf-8")
    assert org.ist_spielordner(str(d), "psx") is False


def test_a_multi_disc_game_with_two_cues_is_still_one_game(org, tmp_path):
    """Aber `(Disc 1)`/`(Disc 2)` desselben Titels bleibt EIN Spiel. (#462)

    Die Marker-Regel gilt weiter — sie wird auf die LISTEN angewandt, nicht auf die
    Spurdateien. Ohne diesen Fall waere jedes Mehrfach-Disc-Spiel ploetzlich eine Sammlung.
    """
    d = tmp_path / "Final Fantasy VII (USA)"
    d.mkdir()
    for i in (1, 2, 3):
        (d / f"Final Fantasy VII (USA) (Disc {i}).bin").write_bytes(b"x" * 32)
        (d / f"Final Fantasy VII (USA) (Disc {i}).cue").write_text(
            f'FILE "Final Fantasy VII (USA) (Disc {i}).bin" BINARY\n', encoding="utf-8")
    assert org.ist_spielordner(str(d), "psx") is True


def test_a_disc_set_missing_a_track_is_not_treated_as_one_game(org, tmp_path):
    """Fehlt eine genannte Datei, ist der Ordner kaputt — und bleibt eine Sammlung. (#462)

    Ihn trotzdem als Einheit zu behandeln wuerde den Schaden festigen: Der Ordner waende
    unangetastet weitergereicht, und niemand saehe, dass er unvollstaendig ist.
    """
    d = _dreamcast_titel(tmp_path, "Unvollstaendig")
    (d / "track02.raw").unlink()
    assert org.ist_spielordner(str(d), "dc") is False


def test_platforms_whose_folders_are_always_one_game(org, tmp_path):
    """Bei DOS, PS3, ScummVM & Co. ist ein Ordner IMMER ein Spiel.

    Dort besteht ein Titel aus vielen Dateien — eine Installation, ein Abbild-Baum. Die
    Dateizahl taugt dort als Kriterium nicht, deshalb entscheidet die Plattform.
    """
    d = tmp_path / "Monkey Island"
    d.mkdir()
    for i in range(40):
        (d / f"datei{i}.dat").write_bytes(b"x" * 8)
    assert org.ist_spielordner(str(d), "dos") is True
    # Dieselbe Struktur auf einer Plattform ohne diese Regel: Sammlung.
    assert org.ist_spielordner(str(d), "c64") is False


def test_ancillary_files_do_not_make_a_folder_a_collection(org, tmp_path):
    """Bilder und Textdateien zaehlen bei der Entscheidung nicht mit."""
    d = tmp_path / "Turrican"
    d.mkdir()
    (d / "Turrican (Disk 1).d64").write_bytes(b"x" * 16)
    (d / "Turrican (Disk 2).d64").write_bytes(b"x" * 16)
    for beiwerk in ("cover.jpg", "screenshot.png", "readme.txt", "info.nfo"):
        (d / beiwerk).write_bytes(b"x" * 8)
    assert org.ist_spielordner(str(d), "c64") is True


# --- Mixed-Sortierer: nur eindeutige Endungen ---------------------------------------

def test_the_sorter_only_moves_unambiguous_extensions(mix):
    """`.bin`, `.iso`, `.rom`, `.img` werden NICHT zugeordnet.

    Sie kommen auf einem Dutzend Plattformen vor. Eine falsche Zuordnung ist teurer als
    eine ausgelassene: Der Titel liegt danach unter der falschen Konsole und faellt
    niemandem auf, waehrend eine ausgelassene Datei sichtbar liegen bleibt.
    """
    for endung in (".bin", ".iso", ".rom", ".img"):
        assert endung not in mix.ENDUNG_PLATTFORM, \
            f"{endung} ist mehrdeutig und darf nicht zugeordnet werden"


def test_the_sorter_recognises_clear_extensions(mix):
    """Eindeutige Endungen werden zugeordnet — sonst waere das Werkzeug wirkungslos."""
    for endung in (".d64", ".nes", ".sfc", ".gba"):
        assert endung in mix.ENDUNG_PLATTFORM, f"{endung} sollte zugeordnet werden"


def test_the_sorter_places_aquarius_cassettes(mix, tmp_path):
    """`.caq` gehoert zum Mattel Aquarius und zu sonst nichts. (#515)

    GEMESSEN nach dem Gesamtumbau: `Mixed` hielt 536 Dateien, und der Trockenlauf
    verschob NICHTS. Zu Recht — bis auf eine Endung:

        .jpg 52  .txt 51  .html 41  .wav 41  .ico 38  .png 31
        .exe 29  .bin 28  .gif 22  .vpl 17  .vrs 14  .caq 13

    Alles andere bleibt aus gutem Grund liegen: Beiwerk, Windows-Programme,
    VICE-Konfiguration, und `.bin`, das bewusst mehrdeutig ist. Die 13 `.caq` stammen
    aus derselben `Mattel Intellivision & Aquarius ROMs`-Sammlung, deren
    Intellivision-Haelfte ueber `.int` sauber einsortiert wurde — die Aquarius-Haelfte
    hatte kein Ziel, obwohl der Ordner `aquarius` existiert.

    Zwischen 52 Werbescans faellt ein Kassettenabzug niemandem auf. Genau dafuer gibt
    es die Tabelle.

    EN: `.caq` is the Aquarius cassette format and belongs to nothing else. Measured
    after the full rebuild: it was the only unambiguous extension still sitting in
    `Mixed`, while the folder it belongs to already existed.
    """
    assert mix.ENDUNG_PLATTFORM.get(".caq") == "aquarius"
    assert mix.plattform_fuer("Alien Quest (19xx)(-)(Part 1 of 2).caq") == "aquarius"
    # Die Ratsche: die Aufnahme darf nichts anderes mitziehen. `.cas` etwa ist ein
    # Kassettenformat mehrerer Systeme (MSX, Coleco) und bleibt draussen.
    assert ".cas" not in mix.ENDUNG_PLATTFORM, (
        ".cas liegt auf mehreren Systemen und darf nicht zugeordnet werden")


def test_emulators_and_bios_are_not_games(mix):
    """Emulatoren und BIOS-Abbilder werden nicht als Spiele einsortiert."""
    assert mix.plattform_fuer("WinUAE1610.exe") is None
    assert mix.plattform_fuer("kickstart13.rom") is None
    assert mix.plattform_fuer("CCS64.exe") is None


def test_the_file_limit_separates_a_game_from_a_collection(org, tmp_path):
    """Auch bei GLEICHEM Titel entscheidet ab einer Menge die Anzahl. (Ergaenzt nach
    einer Gegenprobe.)

    Der Test darueber faellt schon deshalb richtig aus, weil die Titel dort verschieden
    sind — die Dateigrenze wird dabei gar nicht befragt. Eine Gegenprobe mit
    `SPIEL_MAX_DATEIEN = 9999` blieb deshalb gruen, obwohl die Regel ausgehebelt war.

    Dieser Fall befragt sie: viele Dateien, die alle auf DENSELBEN Titel reduzieren. Ein
    Spiel mit mehr als zwoelf Disketten ist selten; eine Sammlung hat Hunderte.
    """
    wenig = tmp_path / "Kleines Spiel"
    wenig.mkdir()
    for i in range(1, 5):
        (wenig / f"Kleines Spiel (Disk {i}).d64").write_bytes(b"x" * 16)
    assert org.ist_spielordner(str(wenig), "c64") is True

    viel = tmp_path / "Grosse Sammlung"
    viel.mkdir()
    for i in range(1, 41):
        (viel / f"Grosse Sammlung (Disk {i}).d64").write_bytes(b"x" * 16)
    assert org.ist_spielordner(str(viel), "c64") is False, \
        "40 Dateien desselben Namens sind eine Sammlung, kein Spiel"


# --- #371: Wiederaufsetzen nach einem Abbruch ---------------------------------------

def _stand(tmp_path, erledigt, fertig=False, aktuell=None):
    import json
    d = tmp_path / ".umbau"
    d.mkdir(parents=True, exist_ok=True)
    (d / "fortschritt.json").write_text(json.dumps({
        "erledigt": [{"plattform": p, "dateien": 1} for p in erledigt],
        "fertig": fertig, "aktuell": aktuell}), encoding="utf-8")
    return str(d / "fortschritt.json")


def test_an_interrupted_run_resumes_where_it_stopped(org, tmp_path):
    """Nach einem Abbruch werden die fertigen Plattformen uebersprungen. (#371)

    WARUM DAS ZAEHLT: Ein voller Lauf ueber diese Bibliothek dauert ueber 19 Stunden.
    Starb er, fing er bei der ERSTEN Plattform wieder an — die Fortschrittsdatei wurde
    geschrieben und nie gelesen. Der einzige Rueckweg war `--ausser` mit einer von Hand
    aus den Protokollen zusammengesuchten Liste, ausgerechnet direkt nach einem Absturz.
    """
    pfad = _stand(tmp_path, ["nes", "gb"], fertig=False, aktuell={"plattform": "snes"})
    erledigt, unterbrochen = org.stand_laden(pfad)
    assert erledigt == {"nes", "gb"}
    assert unterbrochen is True


def test_the_platform_that_was_running_is_done_again(org, tmp_path):
    """Die beim Abbruch LAUFENDE Plattform steht nicht in `erledigt` — sie kommt wieder dran.

    Absicht, kein Versehen: Mitten in einer Plattform wieder aufzusetzen braeuchte einen
    Stand je Eintrag. Der Durchlauf ist dagegen weitgehend wiederholbar — was schon die
    richtige Form hat, wird nicht angefasst. Der Preis ist ein Durchgang, keine doppelte
    Arbeit.
    """
    pfad = _stand(tmp_path, ["nes"], aktuell={"plattform": "snes"})
    erledigt, _ = org.stand_laden(pfad)
    assert "snes" not in erledigt


def test_a_finished_run_is_not_a_resume_point(org, tmp_path):
    """Ein abgeschlossener Lauf setzt NICHT fort. (#371)

    Wer nach dem Ende erneut startet, will neu bauen — nicht nichts tun. Ohne diese
    Unterscheidung waere der zweite Aufruf still wirkungslos, und das sieht aus wie Erfolg.
    """
    pfad = _stand(tmp_path, ["nes", "gb", "snes"], fertig=True)
    erledigt, unterbrochen = org.stand_laden(pfad)
    assert erledigt == set() and unterbrochen is False


def test_a_missing_or_broken_progress_file_starts_from_the_beginning(org, tmp_path):
    """Ohne lesbare Datei wird von vorn begonnen — nicht geraten. (#371)"""
    assert org.stand_laden(str(tmp_path / "gibtsnicht.json")) == (set(), False)
    kaputt = tmp_path / "kaputt.json"
    kaputt.write_text("{kein json", encoding="utf-8")
    assert org.stand_laden(str(kaputt)) == (set(), False)


# --- #397: eine abgestuerzte Plattform gilt nicht als erledigt ----------------------

def _bibliothek(tmp_path, *plattformen):
    """Eine Wurzel mit je einer Datei je Plattform — genug, damit sie als Kandidat zaehlt."""
    for p in plattformen:
        d = tmp_path / p
        d.mkdir()
        (d / f"{p}.rom").write_bytes(b"x" * 8)
    return str(tmp_path)


def _lauf(org, monkeypatch, wurzel, scheitert_an=()):
    """`alle_umbauen` mit einem `umbauen`, das an bestimmten Plattformen scheitert.

    Der echte Umbau ist Dateisystemarbeit; hier geht es einzig um die Buchfuehrung
    darueber, was fertig wurde.
    """
    import json

    def umbauen(_wurzel, plattform, _trocken, _prot, _nur_beiwerk=False):
        if plattform in scheitert_an:
            raise RuntimeError(f"kein freier Name fuer VERSION.NFO ({plattform})")
        return 0

    monkeypatch.setattr(org, "umbauen", umbauen)
    org.alle_umbauen(wurzel, False, set())
    with open(os.path.join(wurzel, ".umbau", "fortschritt.json"), encoding="utf-8") as f:
        return json.load(f)


def test_a_platform_that_crashed_is_not_recorded_as_done(org, tmp_path, monkeypatch):
    """Eine Plattform, die mit einer Ausnahme endete, steht NICHT in `erledigt`. (#397)

    WARUM DAS ZAEHLT: Seit #372 ist `erledigt` die Wiederaufsetzliste. Der volle Lauf vom
    2026-08-11 meldete `ALLE 74 PLATTFORMEN FERTIG`, obwohl `c64` (RuntimeError) und
    `amiga` (UnicodeEncodeError) abgestuerzt waren — beide standen trotzdem in `erledigt`.
    Ein Fortsetzen haette damit ausgerechnet die zwei uebersprungen, die nicht fertig sind.
    """
    wurzel = _bibliothek(tmp_path, "gb", "c64", "amiga")
    stand = _lauf(org, monkeypatch, wurzel, scheitert_an={"c64", "amiga"})

    fertige = {e["plattform"] for e in stand["erledigt"]}
    assert fertige == {"gb"}, f"abgestuerzte Plattformen gelten als erledigt: {fertige}"
    assert {e["plattform"] for e in stand.get("fehlgeschlagen") or []} == {"c64", "amiga"}


def test_a_run_with_failures_is_not_a_finished_run(org, tmp_path, monkeypatch):
    """Bleibt eine Plattform mit Fehler zurueck, ist der Lauf nicht `fertig`. (#397)

    `fertig: true` schaltet den Wiederaufsetzpunkt ab (`stand_laden`). Stuende es nach
    einem Lauf mit Fehlern da, muesste man die zwei Plattformen wieder von Hand ueber
    `--ausser` zusammensuchen — genau das, was #371 abschaffen sollte.
    """
    wurzel = _bibliothek(tmp_path, "gb", "c64")
    stand = _lauf(org, monkeypatch, wurzel, scheitert_an={"c64"})
    assert stand["fertig"] is False

    erledigt, unterbrochen = org.stand_laden(
        os.path.join(wurzel, ".umbau", "fortschritt.json"))
    assert erledigt == {"gb"} and unterbrochen is True, \
        "die abgestuerzte Plattform kommt beim Fortsetzen nicht wieder dran"


def test_a_run_without_failures_is_still_marked_finished(org, tmp_path, monkeypatch):
    """Gegenprobe: ohne Fehler bleibt es beim alten Verhalten. (#397)"""
    wurzel = _bibliothek(tmp_path, "gb", "nes")
    stand = _lauf(org, monkeypatch, wurzel)
    assert stand["fertig"] is True
    assert {e["plattform"] for e in stand["erledigt"]} == {"gb", "nes"}
    assert not stand.get("fehlgeschlagen")


def test_the_closing_summary_names_the_failures(org, tmp_path, monkeypatch, capsys):
    """Die Schlussmeldung nennt die Fehlschlaege, nicht nur die Zahl der Fertigen. (#397)

    Der Fehler stand im Protokoll — zwei Zeilen ueber `ALLE 74 PLATTFORMEN FERTIG`, in
    einer Datei mit 1.194 Zeilen. Wer auf die Schlussmeldung schaut, sah nur Erfolg.
    """
    wurzel = _bibliothek(tmp_path, "gb", "c64", "amiga")
    _lauf(org, monkeypatch, wurzel, scheitert_an={"c64", "amiga"})
    kopf = [z for z in capsys.readouterr().out.splitlines() if "===" in z][-1]
    assert "ALLE" not in kopf, f"die Schlussmeldung meldet vollen Erfolg: {kopf!r}"
    assert "c64" in kopf and "amiga" in kopf, \
        f"die Schlussmeldung verschweigt, welche Plattformen scheiterten: {kopf!r}"


# --- #397: Kollisionsnamen gehen nicht aus -------------------------------------------

def test_more_than_ten_thousand_identical_names_still_get_a_place(org, monkeypatch):
    """Der zehntausendste gleichnamige Eintrag bekommt einen Platz. (#397)

    NACHGEMESSEN, nicht angenommen: Unter `c64` liegen 9.999 Dateien `VERSION (i).NFO`,
    hoechster Index 9999 — genau die Obergrenze der frueheren Suche (`range(2, 10000)`).
    Der Lauf starb dort mit `RuntimeError: kein freier Name fuer VERSION.NFO`. Die Grenze
    beschraenkte nicht die Suche, sondern die Bibliothek.
    """
    org._freier_name_start.clear()
    belegt = {"VERSION.NFO"} | {f"VERSION ({i}).NFO" for i in range(2, 12000)}
    monkeypatch.setattr(org.os.path, "exists",
                        lambda p: os.path.basename(p) in belegt)
    ziel = org.freier_name("/roms/c64", "VERSION.NFO")
    assert os.path.basename(ziel) == "VERSION (12000).NFO"


def test_the_search_for_a_free_name_does_not_get_quadratically_slower(org, tmp_path):
    """Die Suche faengt dort an, wo sie zuletzt aufhoerte — nicht jedes Mal bei 2. (#397)

    Fuer den n-ten gleichnamigen Eintrag pruefte die alte Fassung n Namen; ueber 9.999
    Dateien sind das rund 50 Millionen Anfragen ans Dateisystem, jede auf dem Array. Das
    ist derselbe Fehler wie die Obergrenze, nur als Laufzeit statt als Ausnahme.
    """
    org._freier_name_start.clear()
    ordner = tmp_path / "c64"
    ordner.mkdir()
    n = 0
    echtes_exists = os.path.exists

    def zaehlend(p):
        nonlocal n
        n += 1
        return echtes_exists(p)

    import unittest.mock
    with unittest.mock.patch.object(org.os.path, "exists", zaehlend):
        for _ in range(200):
            open(org.freier_name(str(ordner), "VERSION.NFO"), "w").close()
    assert n < 3 * 200, f"{n} Dateisystemanfragen fuer 200 Namen — die Suche laeuft neu an"


# --- #397: Dateinamen, die kein gueltiges UTF-8 sind ----------------------------------

# `\udce0` ist Pythons Ersatzzeichen fuer das Byte 0xE0 — so liest `os.listdir` einen
# Namen, der in keiner UTF-8-Fassung existiert. Unter `amiga` liegen 21 solcher Namen
# (nachgezaehlt), alle aus `MUI38/MUI/Locale/Catalogs` — `catal\xe0`, `espa\xf1ol`.
UNGUELTIG = "catal\udce0.catalog"


def test_a_filename_that_is_not_valid_utf8_can_be_logged(org, tmp_path):
    """Ein Name mit ungueltigem Byte bricht das Protokoll nicht ab. (#397)

    Der `amiga`-Lauf starb an `UnicodeEncodeError: '\\udce0' surrogates not allowed` —
    beim SCHREIBEN der Protokollzeile. Das Protokoll ist der einzige Rueckweg; scheitert
    es, ist nicht nur die Plattform hin, sondern auch der Weg zurueck.
    """
    prot = org.Protokoll(str(tmp_path / ".umbau" / "p.jsonl"), False)
    try:
        prot.schreiben("verschoben", von=f"/roms/amiga/Bigpack/{UNGUELTIG}",
                       nach=f"/roms/amiga/{UNGUELTIG}")
    finally:
        prot.zu()
    assert os.path.getsize(tmp_path / ".umbau" / "p.jsonl") > 0


def test_such_a_file_survives_the_whole_way_back(org, tmp_path, capsys):
    """Und `--zurueck` legt genau diesen Namen wieder zurueck. (#397)

    Ein Protokoll, das sich nicht mehr lesen laesst, ist so wertlos wie keins.
    """
    von = tmp_path / "sammlung"
    von.mkdir()
    quelle = von / UNGUELTIG
    quelle.write_bytes(b"inhalt")
    ziel = tmp_path / UNGUELTIG

    pfad = str(tmp_path / ".umbau" / "p.jsonl")
    prot = org.Protokoll(pfad, False)
    try:
        os.replace(str(quelle), str(ziel))
        prot.schreiben("verschoben", von=str(quelle), nach=str(ziel))
    finally:
        prot.zu()

    org.zurueck(pfad)
    capsys.readouterr()
    assert quelle.exists() and not ziel.exists(), \
        "der Rueckweg findet den Namen nicht wieder"


# --- #399: Beiwerk gehoert nicht auf Ebene 1 -----------------------------------------

def test_ancillary_files_are_collected_off_the_game_level(org, tmp_path):
    """Beiwerk wandert von Ebene 1 in einen eigenen Ordner. (#399)

    WARUM DAS ZAEHLT: Ebene 1 ist die SPIELEBENE — RomM zaehlt dort jeden Eintrag als
    genau ein Spiel. Unter `c64` standen 10.018 `.nfo`, 1.871 `.svg` und weiteres Beiwerk
    als „Spiele": 10.726 von 57.615 Eintraegen, fast jeder fuenfte.

    Jens' Entscheidung war Weg 2 — sammeln statt loeschen oder liegen lassen. Nichts geht
    verloren, und Ebene 1 traegt einen Ordner statt zehntausend Dateien.
    """
    # Das Verhaeltnis ist Absicht: Am echten Bestand sind es 19 % (c64) bis 26 % (gbc)
    # Beiwerk auf Ebene 1. Eine erste Fassung dieses Tests hatte 4 von 7 Eintraegen als
    # Beiwerk — 57 %, und damit ueber der Schranke, die genau das als Irrtum wertet. Der
    # Test scheiterte an seiner eigenen unrealistischen Annahme.
    basis = tmp_path / "c64"
    basis.mkdir()
    for i in range(12):
        (basis / f"Spiel {i}.d64").write_bytes(os.urandom(64))
    for n in ("VERSION.NFO", "readme.txt", "cover.jpg", "liste.html"):
        (basis / n).write_bytes(os.urandom(32))

    class StummesProtokoll:
        def schreiben(self, *a, **k): pass
    org.umbauen(str(tmp_path), "c64", False, StummesProtokoll())

    oben = sorted(p.name for p in basis.iterdir())
    assert "_beiwerk" in oben, "kein Sammelordner angelegt"
    spiele = [x for x in oben if x != "_beiwerk"]
    assert len(spiele) == 12 and all(x.endswith(".d64") for x in spiele), \
        f"Ebene 1 stimmt nicht: {oben}"
    gesammelt = sorted(p.name for p in (basis / "_beiwerk").iterdir())
    assert gesammelt == ["VERSION.NFO", "cover.jpg", "liste.html", "readme.txt"], gesammelt


def test_the_ancillary_folder_is_visible_not_hidden(org):
    """Der Sammelordner beginnt mit `_`, NICHT mit einem Punkt. (#399)

    Ein versteckter Ordner waere fuer Romseerr unsichtbar (#321) — aber RomM zaehlt ihn
    trotzdem, weil RomM Ebene 1 liest und keine Punktregel kennt. Dann stuende dort wieder
    ein „Spiel", nur ein anderes. Sichtbar ist hier richtig: Es ist kein
    Werkzeugverzeichnis, sondern Inhalt.
    """
    assert not org.BEIWERK_ORDNER.startswith("."), \
        "ein versteckter Ordner waere fuer RomM trotzdem ein Eintrag"
    assert org.BEIWERK_ORDNER.startswith("_")


def test_arcade_platforms_keep_their_layout(org, tmp_path):
    """Bei Arcade wird NICHTS eingesammelt. (#399)

    Dort ist das Archiv das Spiel, und MAME-Romsets erwarten ihre Begleitdateien an Ort
    und Stelle. Dieselbe Ausnahme, die schon fuer das Entpacken gilt.
    """
    basis = tmp_path / "arcade"
    basis.mkdir()
    (basis / "info.txt").write_bytes(os.urandom(16))
    (basis / "spiel.zip").write_bytes(os.urandom(16))

    class StummesProtokoll:
        def schreiben(self, *a, **k): pass
    org.umbauen(str(tmp_path), "arcade", False, StummesProtokoll())
    assert not (basis / "_beiwerk").exists(), "bei Arcade darf nicht eingesammelt werden"
    assert (basis / "info.txt").exists()


def test_a_platform_whose_games_are_png_is_not_emptied(org, tmp_path):
    """Wo `.png` das SPIELFORMAT ist, wird nichts eingesammelt. (#399)

    BEINAHE-SCHADEN, am echten Bestand gefunden: PICO-8-Karten sind `.png` —
    `10002.p8.png` ist ein Spiel, kein Bild. Unter `pico8` liegen 12.629 davon. Die Regel
    „Beiwerk gehoert nicht auf Ebene 1" haette die Plattform GELEERT statt sie aufzuraeumen.
    """
    basis = tmp_path / "pico8"
    basis.mkdir()
    for i in range(4):
        (basis / f"1000{i}.p8.png").write_bytes(os.urandom(32))
    (basis / "liesmich.txt").write_bytes(os.urandom(16))

    class StummesProtokoll:
        def schreiben(self, *a, **k): pass
    org.umbauen(str(tmp_path), "pico8", False, StummesProtokoll())

    verblieben = sorted(p.name for p in basis.iterdir())
    assert len([x for x in verblieben if x.endswith(".png")]) == 4, \
        f"PICO-8-Karten wurden verschoben: {verblieben}"


def test_amiga_icons_and_tracker_music_are_ancillary(org, tmp_path):
    """`.info`, `.sid` und `.mod` sind kein Spielformat — sie gehoeren nicht auf Ebene 1. (#318)

    AM ECHTEN BESTAND GEMESSEN (2026-08-14), Ebene 1 unter `<roms>`:

        amiga    55.102 `.sid`   37.315 `.info`   15.938 `.mod`   von 273.002 Eintraegen
        c64       9.012 `.sid`                                    von  72.061 Eintraegen

    Zusammen **117.366 Eintraege**, die RomM als Spiele zaehlt — mehr, als die Bibliothek
    vor dem Umbau ueberhaupt an Titeln hatte. Es ist Musik und Dekoration:

        `.info`   200 von 200 beginnen mit `E3 10 00 01` — Amiga DiskObject, ein
                  Workbench-Symbol. Es beschreibt die Datei daneben, es IST sie nicht.
        `.sid`    198 `PSID` + 2 `RSID` von 200 — C64-Musik (High Voltage SID Collection).
        `.mod`    175 von 200 tragen `M.K.`/`M!K!` bei 1080 — ProTracker. Der Rest sind
                  aeltere 15-Instrumente-Fassungen, die per Bauart kein Kennzeichen haben.

    DIE PROBE, DIE DIE ENTSCHEIDUNG TRAEGT: `ROM_EXT` in `app.py` kennt keine der drei.
    Romseerrs Importer haelt sie also laengst fuer Nicht-ROMs — das Werkzeug zieht hier
    nach, es entscheidet nichts Neues.

    EN: Workbench icons and tracker/SID music are ancillary, not games. Romseerr's own
    importer already refuses all three; this only aligns the library tool with it.
    """
    for endung in (".info", ".sid", ".mod"):
        assert endung in org.BEIWERK, f"{endung} zaehlt noch als Spiel"

    # Und durch den ganzen Umbau, nicht nur gegen die Liste: Das Verhaeltnis bleibt unter
    # der Schranke aus `BEIWERK_HOECHSTANTEIL` — am Bestand sind es 40 % (amiga), hier 8
    # von 20 Eintraegen.
    basis = tmp_path / "amiga"
    basis.mkdir()
    for i in range(12):
        (basis / f"Spiel {i}.adf").write_bytes(os.urandom(64))
    for n in ("Spiel 0.adf.info", "Disk.info", "Commando.sid", "Ocean Loader.sid",
              "axel_f.mod", "enigma.mod", "cover.jpg", "liesmich.txt"):
        (basis / n).write_bytes(os.urandom(32))

    class StummesProtokoll:
        def schreiben(self, *a, **k): pass
    org.umbauen(str(tmp_path), "amiga", False, StummesProtokoll())

    spiele = sorted(p.name for p in basis.iterdir() if p.name != "_beiwerk")
    assert len(spiele) == 12 and all(x.endswith(".adf") for x in spiele), \
        f"Ebene 1 stimmt nicht: {spiele}"
    gesammelt = sorted(p.name for p in (basis / "_beiwerk").iterdir())
    assert gesammelt == ["Commando.sid", "Disk.info", "Ocean Loader.sid",
                         "Spiel 0.adf.info", "axel_f.mod", "cover.jpg",
                         "enigma.mod", "liesmich.txt"], gesammelt


def test_no_platform_holds_its_games_in_an_ancillary_format(org):
    """Keine der Beiwerk-Endungen darf zugleich als ROM gelten. (#318)

    Der Beinahe-Schaden von `pico8` war genau dieser Widerspruch: `.png` stand als Beiwerk
    UND war das Spielformat. Er wurde damals von Hand als Ausnahme nachgetragen. Diese
    Pruefung faengt den naechsten Fall automatisch — sie liest `ROM_EXT` aus `app.py` und
    verlangt, dass sich die beiden Listen nicht ueberschneiden, ausser wo eine
    `BEIWERK_AUSNAHME` den Widerspruch ausdruecklich benennt.

    EN: an extension may not be ancillary and a ROM format at the same time, unless a
    per-platform exception says so out loud.
    """
    import ast
    with open(os.path.join(WURZEL, "app.py"), encoding="utf-8") as f:
        quelle = f.read()
    rom_ext = None
    for knoten in ast.walk(ast.parse(quelle)):
        if (isinstance(knoten, ast.Assign)
                and any(getattr(z, "id", "") == "ROM_EXT" for z in knoten.targets)):
            rom_ext = {"." + x for x in ast.literal_eval(knoten.value)}
            break
    assert rom_ext, "ROM_EXT nicht in app.py gefunden"

    benannt = set().union(*org.BEIWERK_AUSNAHME.values()) if org.BEIWERK_AUSNAHME else set()
    widerspruch = (org.BEIWERK & rom_ext) - benannt
    assert not widerspruch, (
        f"{sorted(widerspruch)} gilt als Beiwerk UND als ROM — entweder aus BEIWERK "
        f"nehmen oder als BEIWERK_AUSNAHME der betroffenen Plattform benennen")


def test_collection_is_refused_when_it_would_take_most_of_the_platform(org, tmp_path):
    """Waeren mehr als die Haelfte betroffen, wird NICHT eingesammelt. (#399)

    Dann stimmt nicht der Bestand, sondern die Einordnung — und Nichtstun ist die richtige
    Antwort. `pico8` steht ausdruecklich in der Ausnahmeliste; diese Schranke faengt den
    naechsten Fall, den noch niemand gemessen hat.
    """
    basis = tmp_path / "unbekannt"
    basis.mkdir()
    for i in range(8):
        (basis / f"datei{i}.txt").write_bytes(os.urandom(16))
    (basis / "spiel.d64").write_bytes(os.urandom(32))

    class StummesProtokoll:
        def schreiben(self, *a, **k): pass
    org.umbauen(str(tmp_path), "unbekannt", False, StummesProtokoll())

    assert not (basis / "_beiwerk").exists(), \
        "bei ueberwiegendem Beiwerk darf nicht eingesammelt werden"
    assert len(list(basis.iterdir())) == 9, "es darf nichts verschoben worden sein"


# --- #318: `--nur-beiwerk` — der eine Schritt, der ohne Rest zurueckgeht --------------
#
# WOZU ES DEN SCHALTER GIBT: Am Bestand liegen (2026-08-14 gemessen, `find -maxdepth 1`
# ueber alle 74 Plattformen) **121.768 Beiwerk-Dateien auf Ebene 1** verteilt auf 33
# Plattformen, die RomM allesamt als Spiele zaehlt — 108.354 davon unter `amiga`, 9.012
# unter `c64`, 2.166 unter `gbc`, der Rest kleinteilig.
#
# Sie einzusammeln verlangte bisher einen VOLLEN `retronas-organisieren`-Lauf. Der
# entpackt aber auch Archive und LOESCHT Dubletten, und dieser Teil steht zwar im
# Protokoll, ist daraus aber nicht wiederherstellbar. Auf `amiga` (440.000 Dateien) ist er
# ausserdem ein Langlauf ueber Stunden. Schritt 3c allein besteht aus `shutil.move` — und
# damit faellt der ganze Grund weg, aus dem der Umbau bisher nicht lief.


def _stumm():
    class StummesProtokoll:
        def schreiben(self, *a, **k): pass
    return StummesProtokoll()


def test_only_the_ancillary_step_runs_when_only_it_is_asked_for(org, tmp_path):
    """`--nur-beiwerk` fasst NUR Ebene-1-Beiwerk an. (#318)

    Die drei Schritte, die es NICHT tut, sind genau die, die sich nicht zuruecknehmen
    lassen oder Stunden kosten: entpacken (die Quelldatei wird danach geloescht),
    Sammlungen aufloesen, Dubletten entfernen. Der Test legt von jeder Sorte eine Probe
    aus und verlangt, dass sie unberuehrt bleibt.

    EN: the ancillary-only run must not unpack, not flatten collections and not delete
    duplicates — those are the irreversible parts.
    """
    basis = tmp_path / "c64"
    basis.mkdir()
    for i in range(12):
        (basis / f"Spiel {i}.d64").write_bytes(os.urandom(64))
    (basis / "liesmich.txt").write_bytes(os.urandom(16))
    (basis / "cover.jpg").write_bytes(os.urandom(16))
    # Ein Archiv, eine Sammlung und zwei bitgleiche Dateien — die drei Schritte, die
    # ausbleiben muessen.
    import zipfile
    with zipfile.ZipFile(basis / "sammlung.zip", "w") as zf:
        zf.writestr("drin.d64", "x" * 32)
    sammlung = basis / "OneLoad64"
    sammlung.mkdir()
    for i in range(30):
        (sammlung / f"Titel {i}.d64").write_bytes(os.urandom(32))
    gleich = os.urandom(128)
    (basis / "Dublette A.d64").write_bytes(gleich)
    (basis / "Dublette B.d64").write_bytes(gleich)

    org.umbauen(str(tmp_path), "c64", False, _stumm(), True)

    assert (basis / "sammlung.zip").is_file(), "das Archiv wurde entpackt"
    assert (basis / "OneLoad64").is_dir() and len(list(sammlung.iterdir())) == 30, \
        "die Sammlung wurde aufgeloest"
    assert (basis / "Dublette A.d64").is_file() and (basis / "Dublette B.d64").is_file(), \
        "eine Dublette wurde geloescht — genau das darf hier nicht passieren"
    gesammelt = sorted(p.name for p in (basis / "_beiwerk").iterdir())
    assert gesammelt == ["cover.jpg", "liesmich.txt"], gesammelt


def test_an_ancillary_only_run_goes_back_without_a_trace(org, tmp_path):
    """`--zurueck` stellt nach `--nur-beiwerk` den Ausgangsstand VOLLSTAENDIG her. (#318)

    Das ist die Begruendung des Schalters, deshalb wird sie geprueft und nicht behauptet.
    Mitgeprueft: der angelegte `_beiwerk`-Ordner verschwindet wieder. Bliebe er leer
    stehen, zaehlte RomM ihn als ein Spiel — der Rueckweg waere auf jeder angefassten
    Plattform um genau einen Eintrag daneben.
    """
    basis = tmp_path / "c64"
    basis.mkdir()
    for i in range(12):
        (basis / f"Spiel {i}.d64").write_bytes(os.urandom(64))
    for n in ("VERSION.NFO", "readme.txt", "cover.jpg"):
        (basis / n).write_bytes(os.urandom(32))
    vorher = sorted(p.name for p in basis.iterdir())

    pfad = org.protokoll_pfad(str(tmp_path), "c64", True)
    prot = org.Protokoll(pfad, False)
    try:
        org.umbauen(str(tmp_path), "c64", False, prot, True)
    finally:
        prot.zu()
    assert (basis / "_beiwerk").is_dir(), "es wurde gar nicht eingesammelt"

    org.zurueck(pfad)
    assert sorted(p.name for p in basis.iterdir()) == vorher, \
        "der Ausgangsstand ist nicht wiederhergestellt"
    assert not (basis / "_beiwerk").exists(), "der leere Sammelordner blieb stehen"

    # Und im Protokoll steht ausschliesslich Ruecknehmbares.
    with open(pfad, **org.PROTOKOLL_KODIERUNG) as f:
        arten = {json.loads(z)["art"] for z in f if z.strip()}
    assert arten <= {"verschoben", "ordner_angelegt"}, \
        f"ein --nur-beiwerk-Lauf hat mehr getan als verschoben: {sorted(arten)}"


def test_an_ancillary_only_run_is_not_a_finished_rebuild(org, tmp_path, monkeypatch):
    """Ein `--nur-beiwerk --alle` darf einen spaeteren vollen Lauf NICHT verkuerzen. (#318)

    Beide Laufarten schreiben ihren Fortschritt; teilten sie sich eine Datei, gaelte eine
    nur aufgeraeumte Plattform als vollstaendig umgebaut. Der naechste `--alle`-Lauf
    uebersprAENGE sie — ohne je ein Archiv entpackt zu haben, und ohne es zu sagen. Das
    ist derselbe Fehler wie #397, nur eine Ebene hoeher.
    """
    wurzel = _bibliothek(tmp_path, "gb", "c64", "amiga")

    def umbauen(_wurzel, _plattform, _trocken, _prot, _nur_beiwerk=False):
        return 0
    monkeypatch.setattr(org, "umbauen", umbauen)

    org.alle_umbauen(wurzel, False, set(), False, True)
    umbau = os.path.join(wurzel, ".umbau")
    assert os.path.exists(os.path.join(umbau, "fortschritt-beiwerk.json")), \
        "der Beiwerk-Lauf hat seinen Fortschritt nirgends abgelegt"
    assert not os.path.exists(os.path.join(umbau, "fortschritt.json")), \
        "er hat den Wiederaufsetzpunkt des VOLLEN Laufs beschrieben"

    erledigt, _ = org.stand_laden(os.path.join(umbau, "fortschritt.json"))
    assert erledigt == set(), "ein voller Lauf wuerde jetzt Plattformen ueberspringen"


def test_the_log_of_an_ancillary_only_run_says_so_in_its_name(org):
    """Am Dateinamen erkennbar, welcher Art der Lauf war. (#318)

    In `.umbau/` liegen Dutzende Protokolle. Nur die aus `--nur-beiwerk` gehen restlos
    zurueck; wer `--zurueck` aufruft, soll das vorher sehen und nicht erst hinterher.
    """
    voll = org.protokoll_pfad("/roms", "amiga", False)
    nur = org.protokoll_pfad("/roms", "amiga", True)
    assert "-beiwerk-" in os.path.basename(nur)
    assert "-beiwerk-" not in os.path.basename(voll)


# --- #366: Zusammenhang statt Endung --------------------------------------------------

def test_publisher_year_and_size_together_identify_intellivision(mix):
    """Die KOMBINATION traegt die Plattform, nicht die Endung. (#366)

    `.bin` bleibt unzugeordnet — die Endung liegt auf einem Dutzend Systemen, und eine
    falsche Zuordnung kostet mehr als eine ausgelassene. Genau deshalb ordnete der
    Sortierer unter `Mixed` von 707 Dateien GENAU EINE zu.

    Die 198 `.bin` dort sind aber nicht mehrdeutig: Sie tragen Herausgeber und Jahr im
    Namen und haben Kassettengroesse.
    """
    assert mix.plattform_fuer("Shark! Shark! (1982)(Mattel).bin", 16384) == "intellivision"
    assert mix.plattform_fuer("Popeye (1983)(Parker Bros).bin", 16384) == "intellivision"
    assert mix.plattform_fuer("River Raid (1982-83)(Activision).bin", 16384) == "intellivision"


def test_the_extension_alone_still_decides_nothing(mix):
    """Ohne den Zusammenhang bleibt `.bin` liegen. (#366)

    Das ist der Grundsatz, der NICHT aufgeweicht wird: Eine `.bin` ohne Herausgeber, ohne
    Jahr oder mit Festplattengroesse ist genauso mehrdeutig wie zuvor.
    """
    assert mix.plattform_fuer("font.bin", 15288) is None
    assert mix.plattform_fuer("BL.bin", 10478) is None
    assert mix.plattform_fuer("Shark! Shark! (1982)(Mattel).bin", 700 * 1024 * 1024) is None
    assert mix.plattform_fuer("Irgendwas (1982)(Mattel).bin") is None   # ohne Groesse


def test_aquarius_is_not_filed_as_intellivision(mix):
    """Aquarius-Titel bleiben liegen. (#366)

    Der Bestand kommt aus einem Satz „Mattel Intellivision & Aquarius" — beide Systeme sind
    von Mattel, beide nutzen `.bin`, und ein Aquarius-Titel unter `intellivision` faellt
    niemandem auf. Am Namen erkennbar ist genau einer; das ist die Grenze dieser Regel und
    steht so im PR.
    """
    # DIESER FALL PRUEFT DEN AUSSCHLUSS WIRKLICH: Herausgeber `(Mattel)` steht in der
    # Liste, Jahr und Groesse passen — ohne den Ausschluss waere die Datei „intellivision".
    #
    # Die erste Fassung dieses Tests nahm `Aquarius BASIC ROM (1982)(Microsoft).bin`. Der
    # faellt schon durch die Herausgeberliste, denn Microsoft steht nicht darin. Der Test
    # bestand also aus dem falschen Grund, und die Gegenprobe zeigte es: Den Ausschluss zu
    # entfernen brach nichts.
    assert mix.plattform_fuer("Aquarius Cart (1983)(Mattel).bin", 8192) is None
    assert mix.plattform_fuer("Aquarius BASIC ROM (1982)(Microsoft).bin", 8192) is None


# --- #412: endungslose PRG-Dateien an ihrer Ladeadresse erkennen ---------------------

@pytest.fixture(scope="module")
def prg():
    return _laden(os.path.join(WURZEL, "contrib", "library-tools", "retronas-prg-benennen"),
                  "retronas_prg_benennen")


def _prg_datei(ordner, name, adresse, fuellung=500):
    import struct
    p = ordner / name
    p.write_bytes(struct.pack("<H", adresse) + b"\x00" * fuellung)
    return p


def test_a_commodore_load_address_is_recognised(prg, tmp_path):
    """Die ersten zwei Bytes sagen, dass es ein PRG ist. (#412)

    Gemessen am echten Bestand: `$2001` ist die VIC-20-BASIC-Startadresse, `$1201` und
    `$1801` die Varianten mit Speichererweiterung, `$0801` der C64. Von 303 endungslosen
    Dateien unter `vic-20` tragen 190 eine der ersten fuenf, 29 laden auf `$1000` und
    14 auf `$0401`.
    """
    for adr in (0x0801, 0x1001, 0x1201, 0x1801, 0x2001, 0x0401, 0x1000):
        p = _prg_datei(tmp_path, f"spiel{adr:04x}", adr)
        gefunden, _wie = prg.ladeadresse(str(p))
        assert gefunden == adr, f"${adr:04X} nicht erkannt"


def test_a_file_without_a_known_address_is_left_alone(prg, tmp_path):
    """Was keine bekannte Ladeadresse traegt, bleibt unangetastet. (#412)

    DIE REGEL, DIE HALTEN MUSS: Manche der 4.843 Dateien sind womoeglich wirklich Text.
    Eine `readme` in `readme.prg` zu verwandeln machte aus einer harmlosen Datei ein
    kaputtes Spiel — dieselbe Asymmetrie wie ueberall hier: eine falsche Zuordnung kostet
    mehr als eine ausgelassene.

    Am Bestand gemessen: 70 der 303 tragen Adressen wie `$10f1` oder `$6b24`, die keiner
    Maschine entsprechen.
    """
    (tmp_path / "00readme").write_bytes(b"Dies ist Text.\n")
    assert prg.ladeadresse(str(tmp_path / "00readme"))[0] is None
    kaputt = _prg_datei(tmp_path, "kaputt", 0x10F1)
    assert prg.ladeadresse(str(kaputt))[0] is None


def test_the_size_must_fit_the_machine(prg, tmp_path):
    """Ladeadresse plus Groesse muessen in 64 KB passen. (#412)

    Sonst ist es kein Commodore-Programm — die Maschine hat nicht mehr Adressraum. Das
    faengt grosse Dateien ab, deren erste zwei Bytes zufaellig stimmen.
    """
    klein = _prg_datei(tmp_path, "klein", 0x2001, 500)
    assert prg.plausibel(str(klein), 0x2001) is True
    riesig = _prg_datei(tmp_path, "riesig", 0x2001, 200000)
    assert prg.plausibel(str(riesig), 0x2001) is False


def test_renaming_is_reversible(prg, tmp_path):
    """Jede Umbenennung steht im Protokoll und laesst sich zuruecknehmen. (#412)

    Bei 4.843 Dateien ist das keine Kuer: Ohne Rueckweg waere ein Fehler in der Regel nicht
    mehr einzufangen.
    """
    basis = tmp_path / "vic-20"
    basis.mkdir()
    for n, a in (("adressdaten", 0x1801), ("Demo", 0x1201)):
        _prg_datei(basis, n, a)
    (basis / "00readme").write_bytes(b"Text\n")

    prot_pfad = str(tmp_path / ".umbau" / "prg-test.jsonl")
    prot = prg.Protokoll(prot_pfad, False)
    prg.benennen(str(tmp_path), "vic-20", False, prot)
    prot.zu()

    assert sorted(p.name for p in basis.iterdir()) == \
        ["00readme", "Demo.prg", "adressdaten.prg"]

    prg.zurueck(prot_pfad)
    assert sorted(p.name for p in basis.iterdir()) == ["00readme", "Demo", "adressdaten"]


# --- #424: ein Fehler muss auffindbar sein, nicht nur gezaehlt ----------------------

def test_an_error_names_the_file_instead_of_only_counting_it(org, tmp_path, capsys):
    """Ein Fehler landet mit Pfad im Protokoll UND auf dem Bildschirm. (#424)

    WAS DAS AUFGEDECKT HAT: Der c64-Lauf meldete `FEHLER: 3` bei 62.894 Dateien — und es
    gab keinen Weg herauszufinden, welche drei. Weder im Bildschirmprotokoll noch im JSONL
    stand ein Name. Der Zaehler war die einzige Spur, und er zeigt auf nichts.

    Bei den Pruefsummen ist das nicht bloss unbequem: Eine Datei ohne Pruefsumme wird beim
    Dublettenabgleich UEBERSPRUNGEN. Eine echte Dublette kann also stehen bleiben, und
    hinterher kann niemand nachsehen, welche Datei es war. Eine kleine, beruhigende Zahl
    verdeckte drei unbekannte Dateien.

    EN: `FEHLER: 3` out of 62,894 files, with nothing naming them. A file that cannot be
    checksummed is skipped for de-duplication, so a real duplicate may survive unrecorded.
    """
    protokoll_pfad = tmp_path / "prot.jsonl"

    class Protokoll:
        """Nur so viel wie noetig — geprueft wird, WAS geschrieben wird, nicht wie."""

        def __init__(self):
            self.eintraege = []

        def schreiben(self, art, **werte):
            self.eintraege.append({"art": art, **werte})
            protokoll_pfad.write_text(
                "\n".join(json.dumps(e) for e in self.eintraege), encoding="utf-8")

    prot = Protokoll()
    z = {"fehler": 0}
    org.fehler_merken(z, prot, "datei_pruefsumme", "/roms/c64/kaputt.d64",
                      "Input/output error")

    assert z["fehler"] == 1, "der Zaehler muss bleiben — er ist die Zusammenfassung"

    assert len(prot.eintraege) == 1, "nichts ins Protokoll geschrieben"
    e = prot.eintraege[0]
    assert e["art"] == "fehler"
    assert e["pfad"] == "/roms/c64/kaputt.d64", "der Pfad fehlt — genau das war das Problem"
    assert e["schritt"] == "datei_pruefsumme", "ohne Schritt weiss man nicht, WAS schieffiel"
    assert "Input/output" in e["grund"]

    # Und auf dem Bildschirm, waehrend der Lauf noch sichtbar ist.
    ausgabe = capsys.readouterr().out
    assert "/roms/c64/kaputt.d64" in ausgabe, "der Pfad steht nicht in der Ausgabe"
    assert "datei_pruefsumme" in ausgabe


def test_every_error_counter_goes_through_the_recording_helper(org):
    """Kein `z["fehler"] += 1` mehr an der Aufzeichnung vorbei. (#424)

    WARUM ALS QUELLTEXTPRUEFUNG: Die drei Stellen liegen tief in `umbauen`, hinter einem
    Lauf ueber Zehntausende Dateien und hinter `OSError`-Zweigen, die sich in einem Test
    nur mit erheblichem Aufwand ausloesen lassen. Was hier wirklich schuetzt, ist die
    Zusicherung, dass es keinen zweiten, stillen Weg gibt — und die ist am Quelltext
    ablesbar.

    Eine vierte Stelle, die kuenftig nur zaehlt, faellt damit sofort auf.

    EN: the three sites sit deep inside a run over tens of thousands of files behind
    OSError branches. What protects here is the guarantee that no silent path exists.
    """
    quelle = open(WERKZEUG, encoding="utf-8").read()
    roh = re.findall(r'^\s*z\["fehler"\] \+= 1', quelle, re.M)
    assert len(roh) == 1, (
        f"{len(roh)} Stellen zaehlen Fehler direkt hoch; erlaubt ist genau eine — die in "
        "`fehler_merken`, die dabei auch aufzeichnet")


# --- #304: xemu bindet Spieler 1 an das gebrueckte Pad ------------------------------

def _profil(tmp_path):
    """Das Startprofil mit CONFIG auf ein Testverzeichnis geladen."""
    import types
    quelle = open(os.path.join(WURZEL, "contrib", "streaming-host", "launch-profile.py"),
                  encoding="utf-8").read()
    mod = types.ModuleType("lp_304")
    mod.__file__ = "launch-profile.py"
    exec(compile(quelle, "launch-profile.py", "exec"), mod.__dict__)
    mod.CONFIG = str(tmp_path)
    return mod


def _xemu_toml(tmp_path, port1):
    p = tmp_path / ".local" / "share" / "xemu" / "xemu"
    p.mkdir(parents=True, exist_ok=True)
    (p / "xemu.toml").write_text(
        "[input]\n"
        "gamepad_mappings = [\n"
        "    { gamepad_id = '030081b85e0400008e02000000010000'}\n"
        "    ]\n"
        "\n"
        "[input.bindings]\n"
        "port1_driver = 'usb-xbox-gamepad'\n"
        f"port1 = '{port1}'\n"
        "port2 = '030081b85e0400008e02000000010000'\n", encoding="utf-8")
    return p / "xemu.toml"


def test_xemu_player_one_is_moved_onto_the_bridged_pad(tmp_path):
    """Spieler 1 darf nicht auf einer Kennung liegen, die kein Geraet traegt. (#304)

    NACHGEMESSEN AM HOST: Alle acht Joystick-Geraete im Container sind identisch
    (`bus=0003 vendor=045e product=028e`), tragen also EINE SDL-Kennung. xemu band Port 1
    trotzdem auf `000081b84d6963726f736f6674205800` — Bustyp `0000` und der ASCII-Name
    statt Vendor/Product, so bildet SDL eine Kennung fuer ein Geraet, das es NICHT
    identifizieren kann. Ports 2 bis 4 hatten die richtige; ausgerechnet Spieler 1 nicht.

    Ob xemu auf das erste verfuegbare Pad zurueckfaellt, ist NICHT gemessen und wird hier
    nicht behauptet — das braucht jemanden am Pad. Eine Bindung, die ein abwesendes Geraet
    benennt, ist unabhaengig davon falsch.

    EN: all eight devices share one GUID; port 1 named one that no device carries.
    """
    mod = _profil(tmp_path)
    pfad = _xemu_toml(tmp_path, "000081b84d6963726f736f6674205800")

    geaendert, meldung = mod.xemu_apply()
    assert geaendert, f"nichts geaendert: {meldung}"
    text = pfad.read_text(encoding="utf-8")
    assert "port1 = '030081b85e0400008e02000000010000'" in text, text
    # Port 2 bleibt unangetastet — wer ihn fuer einen zweiten Spieler gesetzt hat,
    # soll das behalten.
    assert "port2 = '030081b85e0400008e02000000010000'" in text


def test_xemu_mapping_is_left_alone_when_it_is_already_right(tmp_path):
    """Steht Spieler 1 schon richtig, wird nichts geschrieben. (#304)

    Sonst schriebe der Startweg bei JEDEM Start dieselbe Datei neu — Schreibzugriffe ohne
    Anlass, und jede Aenderung eines Menschen daran waere nach dem naechsten Start weg.
    """
    mod = _profil(tmp_path)
    pfad = _xemu_toml(tmp_path, "030081b85e0400008e02000000010000")
    vorher = pfad.read_text(encoding="utf-8")

    geaendert, meldung = mod.xemu_apply()
    assert not geaendert, meldung
    assert pfad.read_text(encoding="utf-8") == vorher, "die Datei wurde ohne Anlass angefasst"


def test_xemu_does_nothing_without_a_config(tmp_path):
    """Ohne `xemu.toml` wird nichts erfunden. (#304)

    Die Datei entsteht beim ersten Start des Emulators. Sie vorher anzulegen hiesse, eine
    Struktur zu raten, die xemu danach ohnehin ueberschreibt — und im Zweifel eine falsche.
    """
    mod = _profil(tmp_path)
    geaendert, meldung = mod.xemu_apply()
    assert not geaendert and "gibt es noch nicht" in meldung, meldung


# --- #442: Entpacken gegen eine gleichnamige Datei ----------------------------------

def test_unpacking_survives_a_file_with_the_archive_s_name(org, tmp_path):
    """Ein Archiv neben einer gleichnamigen DATEI darf den Lauf nicht abreissen. (#442)

    DIE ECHTE LAGE, an der der Umbau dreimal gescheitert ist. Unter `amiga` lagen
    nebeneinander:

        Kolumbus          <- eine Datei, 357 kB, endungslos (bei Amiga voellig normal)
        Kolumbus (2)
        Kolumbus.rar

    Schritt 1 entpackt Archive in einen Ordner, der nach dem Archiv heisst — also
    `Kolumbus`. `os.makedirs(ziel, exist_ok=True)` verzeiht aber NUR ein vorhandenes
    Verzeichnis. Gegen eine gleichnamige Datei wirft es `FileExistsError`, und die Ausnahme
    nimmt die ganze Plattform mit:

        amiga: FileExistsError: [Errno 17] File exists: '/roms/amiga/Kolumbus'

    WARUM ES SICH NIE VON SELBST LOESTE: Der erste Durchlauf hebt die Datei auf Ebene 1,
    das Archiv liegt noch da. Der naechste Lauf beginnt die Plattform von vorn und
    kollidiert an derselben Stelle. `amiga` konnte damit NIE fertig werden — unabhaengig
    davon, ob ein Container-Neustart dazwischenkam.

    Das `(2)` daneben zeigt, dass `freier_name()` ueberall sonst greift. Das Entpackziel
    war die einzige Stelle ohne.

    EN: an archive beside a same-named file aborted the whole platform, and on resume it
    happened again every time — so the platform could never finish.
    """
    import zipfile

    basis = tmp_path / "amiga"
    basis.mkdir()
    # Die Datei, die den Namen schon belegt.
    (basis / "Kolumbus").write_bytes(b"\x00" * 64)
    # Und das Archiv, das genau dorthin entpackt werden soll.
    with zipfile.ZipFile(basis / "Kolumbus.zip", "w") as z:
        z.writestr("spiel.adf", b"\x00" * 32)

    protokoll = org.Protokoll(str(tmp_path / "prot.jsonl"), False)
    try:
        org.umbauen(str(tmp_path), "amiga", False, protokoll)
    finally:
        protokoll.zu()

    # Die vorhandene Datei bleibt, und der Archivinhalt ist angekommen.
    assert (basis / "Kolumbus").is_file(), "die gleichnamige Datei wurde ueberschrieben"
    adf = list(basis.glob("**/spiel.adf"))
    assert adf, f"der Archivinhalt fehlt — Inhalt: {sorted(p.name for p in basis.iterdir())}"


def test_the_extraction_target_goes_through_the_collision_check(org):
    """Kein Entpackziel mehr ohne `freier_name`. (#442)

    Der Verhaltenstest daneben deckt den einen bekannten Fall ab. Diese Pruefung deckt die
    Regel: Es darf keinen zweiten Weg geben, auf dem ein Entpackziel ohne Kollisionspruefung
    entsteht — sonst kehrt derselbe Fehler an anderer Stelle zurueck.
    """
    import inspect
    import re
    quelle = inspect.getsource(org.umbauen)
    # AUF DIE DIREKTE ZUWEISUNG PRUEFEN. Die erste Fassung suchte nur nach
    # `os.path.splitext(a)[0]` und meldete die REPARIERTE Zeile — dort steht der Ausdruck
    # weiterhin, nur eben als Argument von `freier_name`. Ein Waechter, der die Loesung
    # anzeigt, ist so unbrauchbar wie einer, der das Problem uebersieht.
    assert not re.search(r"^\s*ziel\s*=\s*os\.path\.splitext\(a\)\[0\]\s*$",
                         quelle, re.M), \
        "ein Entpackziel wird direkt aus dem Archivnamen gebildet, ohne freier_name"

    # Und die Gegenrichtung: die Zuweisung im Archiv-Zweig MUSS ueber freier_name gehen.
    #
    # KEIN ZEICHENFENSTER. Die erste Fassung sah sich die ersten 1600 Zeichen nach
    # `for a in archive:` an — und die waren vom Kommentar ueber genau diesen Fix gefuellt,
    # sodass der Waechter an der Erklaerung scheiterte statt an der Sache. Willkuerliche
    # Fenstergroessen sind eine Annahme ueber Formatierung, keine Pruefung.
    zweig = quelle[quelle.index("for a in archive:"):]
    ohne_kommentar = "\n".join(z for z in zweig.splitlines()
                                if not z.strip().startswith("#"))
    zuweisung = ohne_kommentar[:ohne_kommentar.index("if trocken:")]
    assert "freier_name(" in zuweisung, \
        f"das Entpackziel geht nicht ueber freier_name: {zuweisung.strip()!r}"


# --- #447: RAR, LZH und LHA muessen aufgehen ----------------------------------------

def test_the_unpacker_prefers_unar_over_7z(org):
    """`unar` steht vor `7z` — und `7z` bleibt als Ersatz. (#447)

    GEMESSEN am Umbau vom 2026-08-12, allein auf `amiga`:

        45 zip · 28 lzh · 7 rar · 4 lha     = 84 Archive, die geschlossen blieben

    Die `.rar` sind ECHTE RAR-Dateien — `52 61 72 21` (`Rar!`) in den ersten vier Bytes,
    keine falsch benannten. Der Umbau lief in `python:3.12-alpine` mit `p7zip`, und dessen
    RAR-Codec fehlt, weil er unfrei ist. `.lzh` und `.lha` sind auf dem Amiga das NORMALE
    Verteilformat: Ein Archiv mit zwanzig Spielen zaehlte so als ein einziger Eintrag.

    `7z` bleibt als Ersatz stehen, damit das Werkzeug auch in einem Container laeuft, in dem
    nur das vorhanden ist — die Reihenfolge entscheidet, nicht das Entweder-oder.

    EN: Alpine's p7zip ships without the non-free RAR codec, and lzh/lha are the normal
    Amiga distribution formats. unar handles all of them; 7z stays as a fallback.
    """
    namen = [n for n, _ in org._ENTPACKER]
    assert namen[0] == "unar", f"unar steht nicht an erster Stelle: {namen}"
    assert "7z" in namen, "7z ist als Ersatz verschwunden"


def test_a_rejected_zip_is_handed_on_instead_of_given_up(org, tmp_path):
    """Ein `.zip`, das Python ablehnt, wird weitergereicht statt aufgegeben. (#447/#422)

    45 der 84 Fehlschlaege trugen `.zip`. Python meldete `BadZipFile: File is not a zip
    file` — die Datei heisst so, ist aber keine. In diesen Bestaenden sind das haeufig
    falsch benannte LHA-Archive.

    Vorher endete der Versuch dort: `except Exception: return False`. Der Name entschied
    also, ob ein Archiv aufgeht. Dieselbe Lehre wie bei den 3DS-Abbildern (#422) — der
    INHALT entscheidet, und ein Werkzeug, das ihn liest, bekommt seine Gelegenheit.

    Geprueft wird am echten Verhalten: eine Datei mit `.zip` im Namen, die in Wahrheit ein
    TAR ist. Python lehnt sie ab; ein Entpacker, der den Inhalt liest, schafft sie.
    """
    import tarfile
    getarnt = tmp_path / "spiel.zip"
    inhalt = tmp_path / "inhalt.adf"
    inhalt.write_bytes(b"\x00" * 32)
    with tarfile.open(getarnt, "w") as t:
        t.add(inhalt, arcname="inhalt.adf")

    ziel = tmp_path / "raus"
    ok = org.entpacken(str(getarnt), str(ziel))
    if not any(shutil.which(n) for n, _ in org._ENTPACKER):
        pytest.skip("weder unar noch 7z vorhanden — der Weiterreich-Zweig ist hier nicht messbar")
    assert ok, "das getarnte Archiv wurde aufgegeben, statt weitergereicht zu werden"
    assert (ziel / "inhalt.adf").exists() or list(ziel.rglob("inhalt.adf")), \
        f"Inhalt fehlt: {[p.name for p in ziel.rglob('*')]}"


# --- Abbildlisten pruefen (#465) -------------------------------------------------------

def _cue(ordner, name, nennt):
    (ordner / f"{name}.cue").write_text(
        "".join(f'FILE "{n}" BINARY\n' for n in nennt), encoding="utf-8")


def test_a_renamed_data_file_is_recognised_as_solvable(abb, tmp_path):
    """Nennt die `.cue` einen alten Namen und liegt die Datei unter IHREM Stamm da,
    ist der Fall eindeutig. (#465)

    Am Bestand gemessen: `Sexy Parodius (Japan).cue` sucht
    `Sexy Parodius (J) [SLPM-86009].bin`, daneben liegt `Sexy Parodius (Japan).bin`.
    """
    d = tmp_path / "psx"
    d.mkdir()
    _cue(d, "Spiel (Japan)", ["Spiel (J) [SLPM-1].bin"])
    (d / "Spiel (Japan).bin").write_bytes(b"x" * 64)
    befunde, _ = abb.ordner_pruefen(str(d), os.listdir(d))
    assert len(befunde) == 1
    assert befunde[0]["ursache"] == "umbenannt"
    assert befunde[0]["loesungen"] == {"Spiel (J) [SLPM-1].bin": "Spiel (Japan).bin"}


def test_a_broken_cue_does_not_grab_another_games_image(abb, tmp_path):
    """Eine kaputte `.cue` darf NICHT auf fremde Daten umgebogen werden. (#465)

    DAS WAR EIN ECHTER FEHLER IN DER ERSTEN FASSUNG. Die Regel lautete „gibt es genau eine
    Datei dieser Endung, ist sie gemeint". Im Ordner lagen eine heile `.cue` mit ihrer
    `.bin` und eine zweite `.cue`, deren Daten wirklich fehlen — und die bekam die `.bin`
    des ersten Spiels zugewiesen. Am Probebestand aufgefallen, bevor es den echten sah.

    Ein geratener Verweis sieht heil aus und ist es nicht. Das ist schlechter als ein
    sichtbar kaputter, weil niemand mehr hinsieht.
    """
    d = tmp_path / "psx"
    d.mkdir()
    _cue(d, "Spiel (Japan)", ["Spiel (J) [SLPM-1].bin"])
    (d / "Spiel (Japan).bin").write_bytes(b"x" * 64)
    _cue(d, "Verloren", ["Weg.bin"])
    befunde, _ = abb.ordner_pruefen(str(d), os.listdir(d))
    nach_liste = {b["liste"]: b for b in befunde}
    assert nach_liste["Verloren.cue"]["ursache"] == "fehlend", \
        "die kaputte Liste wurde auf fremde Daten umgebogen"
    assert not nach_liste["Verloren.cue"]["loesungen"]
    assert nach_liste["Spiel (Japan).cue"]["ursache"] == "umbenannt"


def test_shared_references_are_reported_even_when_every_name_resolves(abb, tmp_path):
    """Der Kollisionsfall — den die Frage nach fehlenden Dateien NICHT sehen kann. (#465)

    In `/roms/dc` meldete die naheliegende Pruefung NULL Defekte, obwohl alle 138 Titel
    kaputt waren: Im flachgelegten Ordner existiert `track01.bin` ja, jede `.gdi` fand
    einen Treffer — nur den falschen. Namenspraesenz ist nicht dasselbe wie die richtige
    Datei.
    """
    d = tmp_path / "dc"
    d.mkdir()
    zeilen = "3\n1 0 4 2352 track01.bin 0\n2 600 0 2352 track02.raw 0\n3 45000 4 2352 track03.bin 0\n"
    for name in ("Spiel A", "Spiel B"):
        (d / f"{name}.gdi").write_text(zeilen, encoding="utf-8")
    for n in ("track01.bin", "track02.raw", "track03.bin"):
        (d / n).write_bytes(b"x" * 32)
    befunde, geteilt = abb.ordner_pruefen(str(d), os.listdir(d))
    assert befunde == [], "keine Datei fehlt — die erste Frage sieht hier nichts"
    assert len(geteilt) == 3, f"der Kollisionsschaden wurde nicht gemeldet: {geteilt}"


def test_a_playlist_of_stream_urls_is_not_a_broken_image(abb, tmp_path):
    """`.m3u` mit Netzadressen ist kein defektes Abbild. (#465)

    Am Bestand: `RG350/heavy-metal.m3u` verweist auf einen Radio-Stream. Ohne diese
    Unterscheidung wuerde das Werkzeug ihn „reparieren" wollen.
    """
    d = tmp_path / "RG350"
    d.mkdir()
    (d / "heavy-metal.m3u").write_text(
        "#EXTM3U\nhttp://stream.rockantenne.de/heavy-metal\n", encoding="utf-8")
    befunde, _ = abb.ordner_pruefen(str(d), os.listdir(d))
    assert befunde == [], f"Stream-Adressen als Defekt gemeldet: {befunde}"


def test_repairing_keeps_a_copy_of_the_original(abb, tmp_path):
    """Vor dem Umschreiben bleibt eine Sicherung liegen. (#465)

    Eine kaputte Liste ist ersetzbar; eine FALSCH reparierte faellt niemandem auf. Deshalb
    ist der Rueckweg Pflicht und nicht Kuer.
    """
    d = tmp_path / "psx"
    d.mkdir()
    _cue(d, "Spiel", ["Alt.bin"])
    (d / "Spiel.bin").write_bytes(b"x" * 64)
    ok, grund = abb.liste_umschreiben(str(d / "Spiel.cue"), {"Alt.bin": "Spiel.bin"})
    assert ok, grund
    assert 'FILE "Spiel.bin"' in (d / "Spiel.cue").read_text(encoding="utf-8")
    assert (d / "Spiel.cue.vor-fix").exists(), "keine Sicherung angelegt"
    assert 'FILE "Alt.bin"' in (d / "Spiel.cue.vor-fix").read_text(encoding="utf-8")


def test_sorting_out_moves_and_never_deletes(abb, tmp_path):
    """`--aussortieren` VERSCHIEBT nach `_defekt/`. (#465)

    Die vorhandenen Spuren sind echte Daten. Ob sie ersetzbar sind, entscheidet der
    Betreiber — ein Skript, das sie loescht, nimmt ihm diese Entscheidung ab.
    """
    d = tmp_path / "psx"
    d.mkdir()
    _cue(d, "Verloren", ["Weg.bin"])
    (d / "Verloren.bin.teilstueck").write_bytes(b"x" * 8)
    z = abb.plattform_pruefen(str(tmp_path), "psx", reparieren=False, aussortieren=True)
    assert z["aussortiert"] >= 1
    assert (d / "_defekt" / "Verloren.cue").exists()
    assert not (d / "Verloren.cue").exists()
    protokoll = list((tmp_path / ".abbildpruefung").glob("*.jsonl"))
    assert protokoll, "kein Protokoll geschrieben"
    zeilen = [json.loads(z) for z in protokoll[0].read_text(encoding="utf-8").splitlines()]
    assert any(e["art"] == "verschoben" and e["von"] and e["nach"] for e in zeilen)


def test_a_failed_rewrite_says_why(abb, tmp_path):
    """Ein Fehlschlag nennt seinen Grund, statt nur eine Zahl nicht zu erhoehen. (#465)

    DAS IST AM ECHTEN BESTAND PASSIERT. Der Lauf meldete „11 gefunden, 0 repariert" — und
    kein Wort dazu, dass JEDER Schreibversuch an `Permission denied` gescheitert war (der
    Container laeuft als uid 1000, die Bibliothek gehoert 99:users). Das las sich wie
    „nichts zu tun" und war „nichts ging".
    """
    d = tmp_path / "psx"
    d.mkdir()
    _cue(d, "Spiel", ["Alt.bin"])
    (d / "Spiel.bin").write_bytes(b"x" * 8)
    (d / "Spiel.cue").chmod(0o444)
    d.chmod(0o555)
    try:
        ok, grund = abb.liste_umschreiben(str(d / "Spiel.cue"), {"Alt.bin": "Spiel.bin"})
    finally:
        d.chmod(0o755)
        (d / "Spiel.cue").chmod(0o644)
    assert ok is False
    assert grund, "der Fehlschlag blieb stumm"
    assert "schreibbar" in grund or "lesbar" in grund, grund


def test_a_missing_reference_that_is_not_in_the_text_is_reported(abb, tmp_path):
    """Auch „steht so gar nicht drin" ist ein Grund, kein stilles False. (#465)"""
    d = tmp_path / "psx"
    d.mkdir()
    _cue(d, "Spiel", ["Alt.bin"])
    ok, grund = abb.liste_umschreiben(str(d / "Spiel.cue"), {"Gibtsnicht.bin": "X.bin"})
    assert ok is False and grund


# --- Dubletten: Satzmitglieder sind tabu (#467) ----------------------------------------

def test_a_shared_cd_track_is_never_deduplicated(org, tmp_path, capsys):
    """Zwei Spiele mit BITGLEICHER Spur 01 behalten beide ihre Datei. (#467)

    DER GEMESSENE SCHADEN, nicht ein erfundener. Aus dem Laufprotokoll:

        dublette_entfernt  turbografx-cd/Monster Lair (USA) (Track 01).bin
                           gleich_wie  turbografx-cd/Valis II (USA) (Track 01).bin

    Zwei verschiedene Spiele. Bei CD-Titeln ist Spur 01 haeufig identisch — eine leere
    Datenspur. Danach nennt Monster Lairs `.cue` eine Datei, die es nicht mehr gibt.
    Unter `dc` sind so 375 Dateien geloescht worden.

    Bitgleichheit macht zwei Spuren NICHT austauschbar: Jeder Satz braucht sein eigenes
    Exemplar.
    """
    d = tmp_path / "turbografx-cd"
    d.mkdir()
    gleich = b"\x00" * 2048
    for spiel in ("Monster Lair (USA)", "Valis II (USA)"):
        (d / f"{spiel} (Track 01).bin").write_bytes(gleich)
        (d / f"{spiel} (Track 02).bin").write_bytes(spiel.encode() * 8)
        (d / f"{spiel}.cue").write_text(
            f'FILE "{spiel} (Track 01).bin" BINARY\nFILE "{spiel} (Track 02).bin" BINARY\n',
            encoding="utf-8")

    class P:
        def schreiben(self, *a, **k):
            pass
    org.umbauen(str(tmp_path), "turbografx-cd", False, P())

    for spiel in ("Monster Lair (USA)", "Valis II (USA)"):
        assert (d / f"{spiel} (Track 01).bin").exists(), \
            f"{spiel} hat seine Spur 01 an das andere Spiel verloren"


def test_a_real_duplicate_that_no_list_claims_is_still_removed(org, tmp_path):
    """Die Dublettenerkennung bleibt sonst scharf. (#467)

    Ohne diesen Test koennte man #467 „loesen", indem man Schritt 3b ganz abschaltet —
    gruen und nutzlos. Was keine Abbildliste nennt, wird weiterhin entfernt.
    """
    d = tmp_path / "snes"
    d.mkdir()
    (d / "Spiel.sfc").write_bytes(b"y" * 512)
    (d / "Spiel (2).sfc").write_bytes(b"y" * 512)

    class P:
        def schreiben(self, *a, **k):
            pass
    org.umbauen(str(tmp_path), "snes", False, P())
    uebrig = sorted(p.name for p in d.iterdir())
    assert len(uebrig) == 1, f"die echte Dublette blieb liegen: {uebrig}"


def test_a_deeply_nested_set_is_not_skipped(abb, tmp_path):
    """Ein Titel drei Ebenen tief wird geprueft, nicht uebersprungen. (#465)

    DER TEUERSTE FEHLER, DEN EIN PRUEFWERKZEUG HABEN KANN. `tiefe=2` liess das Werkzeug
    129 von 138 Dreamcast-Titeln nie ansehen — sie liegen unter
    `dc/MODE/Dreamcast/<Titel>/`. Gemeldet wurden „2 defekt", eine unabhaengige Zaehlung
    fand 126. Aus „nicht geprueft" wurde damit „in Ordnung".

    Derselbe Blindfleck kostete eine Reparatur: In
    `psp/PSX2PSP/PSX Images/Super Puzzle Fighter 2 Turbo-NTSC/` lag die gesuchte `.bin`
    direkt neben ihrer `.cue`.
    """
    tief = tmp_path / "dc" / "MODE" / "Dreamcast" / "Spiel"
    tief.mkdir(parents=True)
    (tief / "Spiel.cue").write_text('FILE "Weg.bin" BINARY\n', encoding="utf-8")

    z = abb.plattform_pruefen(str(tmp_path), "dc", reparieren=False, aussortieren=False)
    assert z["fehlend"] == 1, (
        "der Titel drei Ebenen tief wurde uebersprungen — das Werkzeug haette Entwarnung "
        "gegeben")


def test_a_deeply_nested_rename_is_repaired(abb, tmp_path):
    """Und die Reparatur greift dort ebenfalls. (#465)"""
    tief = tmp_path / "psp" / "PSX2PSP" / "PSX Images" / "Spiel"
    tief.mkdir(parents=True)
    (tief / "Spiel.cue").write_text('FILE "Alt.bin" BINARY\n', encoding="utf-8")
    (tief / "Spiel.bin").write_bytes(b"x" * 32)

    z = abb.plattform_pruefen(str(tmp_path), "psp", reparieren=True, aussortieren=False)
    assert z["repariert"] == 1, "die Reparatur erreichte die tiefe Ebene nicht"
    assert 'FILE "Spiel.bin"' in (tief / "Spiel.cue").read_text(encoding="utf-8")


# --- „kein Archiv" ist kein Fehlschlag (#447) ------------------------------------------

def test_a_file_that_is_not_an_archive_is_not_reported_as_a_failure(org, tmp_path,
                                                                    monkeypatch, capsys):
    """Eine Datei mit lügender Endung ist KEIN beschädigtes Archiv. (#447)

    Unter `amiga` liegen Dateien, die `.ZIP` oder `.LZH` heissen und keine sind — kein
    `PK\\x03\\x04`, kein LHA-Kopf, sondern Amiga-Cruncher-Formate (`85 15 02 41`,
    `95 0a 02 41`). Sie als „Archiv liess sich nicht entpacken" zu melden behauptet einen
    Schaden, den es nicht gibt, UND begraebt die echten: Von 78 Meldungen waren 49 solche
    Dateien, und darunter lagen genau ZWEI wirklich beschaedigte Archive.

    Die beiden Befunde verlangen verschiedene Antworten — neu beschaffen gegen umbenennen.
    """
    d = tmp_path / "amiga"
    d.mkdir()
    (d / "APHOR.ZIP").write_bytes(bytes.fromhex("85150241") + b"\x00" * 64)

    monkeypatch.setattr(org, "ist_ueberhaupt_ein_archiv", lambda p: False)
    monkeypatch.setattr(org, "entpacken", lambda a, z: False)

    class P:
        def __init__(self):
            self.arten = []
        def schreiben(self, art, **k):
            self.arten.append(art)
    prot = P()
    org.umbauen(str(tmp_path), "amiga", False, prot)

    assert "kein_archiv" in prot.arten, "der Befund wurde gar nicht festgehalten"
    assert "fehler" not in prot.arten, \
        "als Fehler gezaehlt — damit begraebt es die echten Fehlschlaege"


def test_a_genuinely_damaged_archive_is_still_a_failure(org, tmp_path, monkeypatch):
    """Ein ECHTES Archiv, das nicht aufgeht, bleibt ein Fehler. (#447)

    Ohne diesen Test liesse sich #447 „loesen", indem man alle Entpackfehler leise
    schluckt — gruen und blind. `DARKSEED.RAR` ist ein echtes RAR (`lsar` listet
    `Darksee1.adf`), dessen Inhalt beim Entpacken an „Wrong checksum" scheitert. Genau
    dieser Fall muss sichtbar bleiben.
    """
    d = tmp_path / "amiga"
    d.mkdir()
    (d / "DARKSEED.RAR").write_bytes(b"Rar!\x1a\x07\x00" + b"\x00" * 64)

    monkeypatch.setattr(org, "ist_ueberhaupt_ein_archiv", lambda p: True)
    monkeypatch.setattr(org, "entpacken", lambda a, z: False)

    class P:
        def __init__(self):
            self.arten = []
        def schreiben(self, art, **k):
            self.arten.append(art)
    prot = P()
    org.umbauen(str(tmp_path), "amiga", False, prot)

    assert "fehler" in prot.arten, \
        "ein beschaedigtes Archiv wurde stillschweigend uebergangen"


# --- #517: Verweise ohne Endung ------------------------------------------------------

def test_a_cue_that_names_its_track_without_an_extension_is_solvable(abb, tmp_path):
    """`QixNeo.cue` nennt `QixNeo`, daneben liegt `QixNeo.bin`. (#517)

    AM BESTAND GEMESSEN, in `psp/PSX2PSP/PSX Images`:

        QixNeo.cue     -> vermisst ["QixNeo"]      QixNeo.bin     liegt daneben
        mrdomino.cue   -> vermisst ["mrdomino"]    mrdomino.bin   liegt daneben

    `loesung_finden` stieg in der ERSTEN Zeile aus:

        endung = os.path.splitext(vermisst)[1].lower()
        if not endung:
            return None

    Damit war der leichteste Fall ueberhaupt — ein Name ohne Endung und genau eine Datei
    daneben, die so heisst — der einzige, den das Werkzeug nie loesen konnte. Beide Wege
    darueber (Stamm der Liste, einzige freie Datei der Endung) waren unerreichbar.

    EN: a cue may name its track without an extension, and in the library it does. The
    function returned before either of its two routes could run.
    """
    d = tmp_path / "psx"
    d.mkdir()
    (d / "QixNeo.cue").write_text('FILE "QixNeo" BINARY\n  TRACK 01 MODE2/2352\n')
    (d / "QixNeo.bin").write_bytes(b"x" * 64)
    assert abb.loesung_finden("QixNeo.cue", "QixNeo", os.listdir(d), set()) == "QixNeo.bin"


def test_an_extensionless_reference_is_not_guessed_at(abb, tmp_path):
    """Zwei Kandidaten sind keine Eindeutigkeit. (#517)

    Die Enge ist der Punkt, nicht die Nachsicht. Ein geratener Verweis sieht heil aus
    und ist es nicht — dieselbe Falle, an der die erste Fassung von `loesung_finden`
    schon einmal eine kaputte `.cue` auf das Abbild eines FREMDEN Spiels umgebogen hat.

    Drei Ratschen in einem Test, weil sie dieselbe Frage aus drei Richtungen stellen.

    DIESER TEST UNTERSCHEIDET NICHT. Am Stand vor #517 ist er ebenfalls gruen, weil die
    Funktion fuer endungslose Verweise IMMER `None` lieferte — also auch hier. Er haelt
    fest, dass der neue Weg nicht uebereifrig wird; als Beleg, dass die Reparatur wirkt,
    taugt er nicht. Das tun die beiden anderen.
    """
    d = tmp_path / "psx"
    d.mkdir()
    (d / "QixNeo.cue").write_text('FILE "QixNeo" BINARY\n')

    # 1. zwei moegliche Spuren -> keine Antwort
    (d / "QixNeo.bin").write_bytes(b"x")
    (d / "QixNeo.iso").write_bytes(b"x")
    assert abb.loesung_finden("QixNeo.cue", "QixNeo", os.listdir(d), set()) is None

    # 2. die einzige Spur gehoert schon einer anderen Liste
    (d / "QixNeo.iso").unlink()
    assert abb.loesung_finden("QixNeo.cue", "QixNeo", os.listdir(d),
                              {"qixneo.bin"}) is None

    # 3. der Stamm muss EXAKT stimmen — kein Anfang, kein Enthaltensein
    assert abb.loesung_finden("QixNeo.cue", "Qix", os.listdir(d), set()) is None


def test_ancillary_files_are_not_mistaken_for_a_track(abb, tmp_path):
    """Eine `.txt` mit demselben Stamm ist keine Spur. (#517)

    Ohne die Endungsliste waere `QixNeo.txt` ein zweiter Kandidat gewesen — und aus
    einem eindeutigen Treffer eine Auswahl geworden, also gar keine Loesung mehr.
    Beiwerk liegt in dieser Bibliothek ueberall neben den Spielen.
    """
    d = tmp_path / "psx"
    d.mkdir()
    (d / "QixNeo.cue").write_text('FILE "QixNeo" BINARY\n')
    (d / "QixNeo.txt").write_text("Beschreibung")
    (d / "QixNeo.nfo").write_text("x")
    (d / "QixNeo.bin").write_bytes(b"x")
    assert abb.loesung_finden("QixNeo.cue", "QixNeo", os.listdir(d), set()) == "QixNeo.bin"


def test_a_reference_is_not_replaced_twice(abb, tmp_path):
    """Aus `QixNeo` darf `QixNeo.bin` werden, nicht `QixNeo.bin.bin`. (#521)

    Hier standen zwei `replace` hintereinander, und das zweite lief auf dem ERGEBNIS
    des ersten. Solange der alte Verweis eine Endung trug, war das folgenlos: Nach
    `Alt.bin` -> `Neu.bin` kommt `Alt.bin` im Text nicht mehr vor.

    Seit #517 kann der Verweis ohne Endung sein — und ist damit ein PRAEFIX seines
    eigenen Ersatzes. AM ECHTEN BESTAND PASSIERT:

        FILE "QixNeo" BINARY   ->   FILE "QixNeo.bin.bin" BINARY

    Zurueckgeholt aus den `.vor-fix`-Sicherungen, die das Werkzeug vor jeder Aenderung
    anlegt. Eine falsch reparierte Liste ist schlimmer als eine kaputte: die kaputte
    faellt auf.

    EN: at most one replacement per reference. The second call ran on the result of the
    first, harmless only while the old reference carried an extension.
    """
    p = tmp_path / "QixNeo.cue"
    p.write_text('FILE "QixNeo" BINARY\n  TRACK 01 MODE2/2352\n', encoding="utf-8")
    ok, grund = abb.liste_umschreiben(str(p), {"QixNeo": "QixNeo.bin"})
    assert ok, grund
    text = p.read_text(encoding="utf-8")
    assert 'FILE "QixNeo.bin" BINARY' in text, text
    assert ".bin.bin" not in text, text


def test_a_reference_with_a_path_is_still_rewritten(abb, tmp_path):
    """Die Ratsche zur Gegenseite: der Basisname-Versuch darf nicht verlorengehen. (#521)

    Er ist fuer Listen da, die ihre Spur MIT Pfad nennen. Wer den Doppelersatz einfach
    streicht, nimmt diesen Fall mit — deshalb steht er hier fest.
    """
    p = tmp_path / "Spiel.cue"
    p.write_text('FILE "tracks/Alt.bin" BINARY\n', encoding="utf-8")
    ok, grund = abb.liste_umschreiben(str(p), {"Alt.bin": "Neu.bin"})
    assert ok, grund
    assert 'FILE "tracks/Neu.bin" BINARY' in p.read_text(encoding="utf-8")
