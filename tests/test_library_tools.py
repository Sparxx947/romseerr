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
import os

import pytest

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WERKZEUG = os.path.join(WURZEL, "contrib", "library-tools", "retronas-organisieren")
SORTIERER = os.path.join(WURZEL, "contrib", "library-tools", "retronas-mixed-sortieren")


def _laden(pfad, name):
    """Ein Skript ohne `.py`-Endung als Modul laden."""
    spec = importlib.util.spec_from_loader(
        name, importlib.machinery.SourceFileLoader(name, pfad))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def org():
    return _laden(WERKZEUG, "retronas_organisieren")


@pytest.fixture(scope="module")
def mix():
    return _laden(SORTIERER, "retronas_mixed_sortieren")


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
