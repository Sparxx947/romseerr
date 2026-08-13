"""Tests fuer den Streaming-Host / streaming host tests.

Herausgeloest aus `test_smoke.py`, das mit 512,0 kB exakt auf der Groessengrenze sass,
die sich dieses Repository in `.github/CONTRIBUTING.md` selbst setzt — der naechste Test
scheiterte dort an der Inhaltsregel statt an seiner Sache (#505).

Hier steht, was den START-DIENST betrifft: die Init-Skripte unter
`contrib/streaming-host/init`, die Emulator-Einrichtung, das Auffinden und Starten von
Titeln. Was die Anwendung selbst prueft, bleibt in `test_smoke.py`.

EN: split out of test_smoke.py, which sat exactly on this repository's own size limit.
Everything here concerns the streaming host; application behaviour stays in the smoke file.
"""
import ast
import json
import os
import yaml
import re
import sys
import shlex
import shutil
import subprocess
import tempfile
import time

import pytest

from hilfen import (  # noqa: F401  gemeinsam genutzt (#505)
    REPO,
    _3ds_datei,
    _agent_modul,
    _agent_module,
    _agent_pfadwahl,
    _argv,
    _cia_datei,
    _falsches_werkzeug,
    _lp_mit_config,
    _mitschrift_emulator,
    _ncsd_bauen,
    _nsp_datei,
    _param_sfo,
    _pcsx2_ini,
    _pid_lebt,
    _profil_modul,
    _vita_bibliothek,
    _wrapper_emulator,
)



def test_stream_agent_refuses_paths_outside_the_library(appmod):
    """Der Start-Dienst darf ausschliesslich Dateien aus der Bibliothek starten —
    sonst waere er ein Fernstart fuer beliebige Dateien. (#71)"""
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "contrib", "streaming-host", "stream-agent.py")
    os.environ["STREAM_AGENT_TOKEN"] = "testtoken"
    os.environ["STREAM_ROMS"] = appmod.ROMS
    spec = importlib.util.spec_from_file_location("stream_agent", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Ohne konfigurierten Emulator lehnt der Dienst schon vorher ab — dann wuerde der
    # Test die PFADPRUEFUNG gar nicht erreichen und faelschlich gruen sein.
    mod.EMULATORS["ps2"] = "/bin/true %s"
    ok, msg = mod.launch("/etc/passwd", "ps2")
    assert ok is False and "ausserhalb" in msg
    ok, msg = mod.launch(os.path.join(appmod.ROMS, "gibt-es-nicht.iso"), "ps2")
    assert ok is False and "nicht gefunden" in msg
    ok, msg = mod.launch(os.path.join(appmod.ROMS, "x.iso"), "voellig-unbekannt")
    assert ok is False and "kein Emulator" in msg


def test_firmware_script_uses_the_same_platform_slugs():
    """Der Streaming-Host, Romseerr und das Firmware-Skript muessen dieselben Kuerzel
    verwenden. Eine zweite Schreibweise braeuchte eine Uebersetzungstabelle, und die
    waere genau die Stelle, an der spaeter ein Eintrag fehlt. (#107)"""
    pfad = os.path.join(REPO, "contrib/streaming-host/init/25-firmware")
    text = open(pfad, encoding="utf-8").read()
    tabelle = re.search(r"KATALOG=\((.*?)\n\)", text, re.S).group(1)
    slugs = {z.strip().strip('"').split("|")[0] for z in tabelle.strip().splitlines() if z.strip().startswith('"')}
    import app as appmod
    unbekannt = slugs - set(appmod.STREAMABLE)
    assert not unbekannt, f"Kuerzel kennt Romseerr nicht: {sorted(unbekannt)}"


def test_firmware_staging_and_target_agree_where_they_are_the_same_place():
    """Fuer PS3 und Vita IST die Ablage das Zielverzeichnis — der Emulator liest die
    PUP von dort. Weichen die Namen ab, liegt dieselbe Datei an zwei Orten, und beim
    naechsten Blick ist unklar, welcher gilt. (#107)"""
    pfad = os.path.join(REPO, "contrib/streaming-host/init/25-firmware")
    text = open(pfad, encoding="utf-8").read()
    tabelle = re.search(r"KATALOG=\((.*?)\n\)", text, re.S).group(1)
    for zeile in tabelle.strip().splitlines():
        zeile = zeile.strip().strip('"')
        if not zeile or zeile.startswith("#"):
            continue
        slug, _name, _emu, ziel = zeile.split("|")[:4]
        if ziel.startswith("firmware/"):
            assert ziel == f"firmware/{slug}", \
                f"{slug}: Ablage firmware/{slug}, Ziel {ziel} — zwei Orte fuer dieselbe Datei"


def test_firmware_import_places_even_when_output_is_truncated(tmp_path):
    """Ein `| head -1` schickt SIGPIPE. Stand das Platzieren HINTER der Meldung, fiel
    genau die Arbeit aus: die Datei lag in der Ablage, der Emulator sah sie nie, und
    der Status meldete weiter "fehlt". Reihenfolge ist hier Verhalten, nicht Stil. (#107)"""
    import subprocess
    skript = os.path.join(REPO, "contrib/streaming-host/init/25-firmware")
    umg = {**os.environ, "FW_CONFIG_ROOT": str(tmp_path)}
    (tmp_path / "dc_boot.bin").write_bytes(b"\0" * 2097152)
    (tmp_path / "dc_flash.bin").write_bytes(b"\0" * 131072)
    subprocess.run(["bash", skript], env=umg, capture_output=True)
    for name in ("dc_boot.bin", "dc_flash.bin"):
        # Genau der Aufruf, der den Fehler ausgeloest hat: Ausgabe nach einer Zeile zu.
        subprocess.run(f"bash {skript} --import dreamcast {tmp_path/name} 2>&1 | head -1",
                       shell=True, env=umg, capture_output=True)  # nosec B602 - Testaufruf
    ziel = tmp_path / ".local/share/flycast"
    fehlend = [n for n in ("dc_boot.bin", "dc_flash.bin") if not (ziel / n).exists()]
    assert not fehlend, f"nicht platziert: {fehlend}"


def test_firmware_is_readable_by_the_account_that_runs_the_emulator():
    """Das Skript laeuft als root mit umask 077, der Emulator als abc. Ohne Korrektur
    liegt die Firmware als -rw------- root root da und der Emulator kann seine EIGENE
    Firmware nicht lesen — ein schwarzes Bild, also genau der Fehler, den dieses
    Skript verhindern soll. (#107)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/init/25-firmware"), encoding="utf-8").read()
    assert "stat -c '%u:%g'" in text, "Besitzer muss abgelesen werden, nicht geraten"
    assert "besitz_richten" in text
    assert text.count("besitz_richten ") >= 3, "Ablage, Ziel und Datei muessen erfasst sein"


def test_firmware_parent_directory_is_owned_too():
    """Die Plattformordner dem Emulator zu geben genuegt nicht: bleibt /config/firmware
    bei root und 0700, ist alles darunter unerreichbar, egal wem es gehoert. Genau so
    war die PS3-PUP nach dem ersten Anlauf nicht lesbar. (#107)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/init/25-firmware"), encoding="utf-8").read()
    platzieren = text.split("platzieren() {", 1)[1].split("\n}", 1)[0]
    assert 'besitz_richten "$FW"' in platzieren, "das uebergeordnete Verzeichnis fehlt"


def test_launch_service_sets_the_documented_gamepad_variable():
    """Selkies dokumentiert DREI Variablen; das Abbild setzt zwei und laesst
    SDL_JOYSTICK_DEVICE weg — am laufenden Container nachgemessen. Ohne sie sieht der
    Emulator kein Pad. (#19)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/init/30-agent"), encoding="utf-8").read()
    assert "export SDL_JOYSTICK_DEVICE=" in text
    assert "SELKIES_INTERPOSER" in text, "der Interposer muss auch ohne Vorgabe des Abbilds greifen"


def test_agent_takes_the_preload_from_the_image_not_a_reconstruction():
    """Das Abbild laedt ZWEI Bibliotheken vor: den Interposer und eine gefaelschte
    libudev, ueber die SDL die Geraete aufzaehlt. Ein Nachbau von Hand hatte nur die
    erste — dann steht ein Geraetepfad bereit, den niemand aufzaehlt. Die maszgebliche
    Fassung steht in der s6-Umgebung. (#19)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/init/30-agent"), encoding="utf-8").read()
    assert "/run/s6/container_environment/LD_PRELOAD" in text, \
        "die Vorgabe des Abbilds muss gelesen, nicht nachgebaut werden"


def test_nothing_is_mounted_into_the_selkies_web_root():
    """Das Abbild macht beim Start `rm -Rf /usr/share/selkies/web` und kopiert das
    Dashboard neu dorthin. Ein Bind-Mount IN dieses Verzeichnis laesst das `rm`
    scheitern; `cp -a` legt die Quelle dann eine Ebene ZU TIEF ab, die Wurzel bleibt
    ohne index.html, nginx antwortet 403 — und der Stream startet nie. Am laufenden
    Host nachgemessen: der Client verband sich als "Legacy client, Slot: None", es
    lief keine Video-Pipeline. Sah nach einem Browserproblem aus, war ein Kopierschritt.

    The image wipes that directory on boot; mounting into it breaks the web root."""
    text = open(os.path.join(REPO, "contrib/streaming-host/docker-compose.yml"),
                encoding="utf-8").read()
    for zeile in text.splitlines():
        nackt = zeile.strip()
        if nackt.startswith("#") or ":" not in nackt:
            continue
        assert ":/usr/share/selkies/web/" not in nackt, (
            f"in die Web-Wurzel darf nichts eingehaengt werden — {nackt!r}; "
            "stattdessen nach /opt haengen und in init/05-web kopieren")


def test_web_root_is_repaired_and_the_check_page_is_copied():
    """Die Heilung haengt am SYMPTOM (fehlende index.html), nicht an der heutigen
    Ursache — sonst faengt sie die naechste Variante nicht. Und die Pruefseite wird
    kopiert statt eingehaengt, siehe Test oben."""
    text = open(os.path.join(REPO, "contrib/streaming-host/init/05-web"),
                encoding="utf-8").read()
    assert 'index.html' in text and 'cp -a "$DASH/." "$WEB/"' in text, \
        "die Wurzel muss geheilt werden, wenn die index.html fehlt"
    assert "/opt/gamepad-check.html" in text, \
        "die Pruefseite muss aus /opt kopiert werden"


def test_agent_rejects_traversal_in_the_relative_path(tmp_path):
    """`rel` wird an die Bibliothekswurzel geheftet und ist damit genauso eine Eingabe
    von aussen wie der absolute Pfad vorher. Die Pruefung muss GREIFEN, sonst hat der
    bequemere Vertrag ein Loch aufgemacht. (#130)"""
    m = _agent_module(tmp_path, EMU_PS2="/bin/true %s")
    for boese in ("../../etc/passwd", "../../../etc/shadow", "/etc/passwd"):
        ok, msg = m.launch("", "ps2", boese)
        assert not ok, f"durchgelassen: {boese!r}"


def test_agent_prefers_the_relative_path(tmp_path):
    """Beides wird geschickt; massgeblich ist `rel`. Ein absoluter Pfad bedeutet in
    zwei Containern nicht dasselbe. (#130)"""
    (tmp_path / "ps2").mkdir()
    (tmp_path / "ps2" / "spiel.iso").write_bytes(b"x")
    m = _agent_module(tmp_path, EMU_PS2="/bin/true %s")
    # Der absolute Pfad ist absichtlich falsch — mit `rel` muss es trotzdem gehen.
    ok, msg = m.launch("/woanders/ps2/spiel.iso", "ps2", "ps2/spiel.iso")
    assert ok, msg
    m._stop_locked()


def test_agent_launches_a_folder_title(tmp_path):
    """Eine PS3-Disc ist ein ORDNER (PS3_DISC.SFB + PS3_GAME/USRDIR/EBOOT.BIN) —
    nachgemessen, 13 von 17 Titeln der Testbibliothek. Die frühere Prüfung auf
    `isfile` wies solche Titel ab, und zwar mit der Meldung über verschiedene
    Einhängepunkte: eine plausible, aber falsche Fährte."""
    spiel = tmp_path / "ps3" / "Ein Spiel"
    (spiel / "PS3_GAME" / "USRDIR").mkdir(parents=True)
    (spiel / "PS3_GAME" / "USRDIR" / "EBOOT.BIN").write_bytes(b"x")
    (spiel / "PS3_DISC.SFB").write_bytes(b"x")
    m = _agent_module(tmp_path, EMU_PS3="/bin/true %s")
    ok, msg = m.launch("", "ps3", "ps3/Ein Spiel")
    assert ok, msg
    assert m._current["path"].endswith("EBOOT.BIN"), m._current["path"]
    m._stop_locked()


def test_agent_resolves_against_the_listing_not_by_building_a_path(tmp_path):
    """Der Kern des Umbaus: der Pfad wird nicht aus der Anfrage GEBAUT, sondern Stufe
    fuer Stufe gegen den echten Verzeichnisinhalt abgeglichen. Der zurueckgegebene
    Wert stammt damit aus dem Dateisystem; die Anfrage bestimmt nur die Auswahl.

    Nachweis ueber einen Namen, der sich nur in der Gross-/Kleinschreibung
    unterscheidet: `os.path.join` haette daraus klaglos einen Pfad gebaut, der auf
    einem case-insensitiven Dateisystem sogar existiert. Der Abgleich gegen das
    Listing nimmt ihn nicht an, weil der Eintrag so nicht heisst."""
    (tmp_path / "ps2").mkdir()
    (tmp_path / "ps2" / "Spiel.iso").write_bytes(b"x")
    m = _agent_module(tmp_path, EMU_PS2="/bin/true %s")
    assert m._bibliothekspfad("ps2/Spiel.iso"), "der echte Name muss gehen"
    assert not m._bibliothekspfad("ps2/spiel.ISO"), "nur was so im Listing steht"
    assert not m._bibliothekspfad("ps2/../ps2/Spiel.iso"), "'..' bleibt verboten"
    assert not m._bibliothekspfad(""), "leer ist kein Titel"
    # Symlinks werden nicht verfolgt — was ausserhalb liegt, ist nie startbar.
    (tmp_path / "draussen.iso").write_bytes(b"x")
    (tmp_path / "ps2" / "Verweis.iso").symlink_to(tmp_path / "draussen.iso")
    assert not m._bibliothekspfad("ps2/Verweis.iso")


def test_agent_refuses_a_boot_file_that_symlinks_out_of_the_library(tmp_path):
    """Der ORDNER liegt in der Bibliothek — die Startdatei darin muss es deshalb
    nicht. Ein Symlink genuegt, um heraus zu zeigen, und dann startet der Emulator
    auf einer beliebigen Datei des Hosts.

    Diese Luecke war im ersten Anlauf drin: die Pruefung lief nur auf dem Pfad von
    aussen, nicht auf der aus dem Ordner aufgeloesten Datei. Gefunden hat sie CodeQL
    (`py/path-injection`), nicht der Testlauf — deshalb steht sie jetzt hier."""
    draussen = tmp_path / "geheim.bin"
    draussen.write_bytes(b"x")
    roms = tmp_path / "lib"
    spiel = roms / "ps3" / "Boeses Spiel" / "PS3_GAME" / "USRDIR"
    spiel.mkdir(parents=True)
    (spiel / "EBOOT.BIN").symlink_to(draussen)
    m = _agent_module(roms, EMU_PS3="/bin/true %s")
    ok, msg = m.launch("", "ps3", "ps3/Boeses Spiel")
    assert not ok, "Symlink aus der Bibliothek heraus wurde gestartet"
    assert "Bibliothek" in msg, msg


def test_agent_refuses_a_folder_it_cannot_boot_instead_of_guessing(tmp_path):
    """Zwei Abbilder in einem Ordner: welches gemeint ist, weiss der Agent nicht.
    Ein geratenes Spiel zu starten waere schlimmer als eine klare Absage — der
    Nutzer sucht sonst den Fehler im Emulator."""
    ordner = tmp_path / "ps2" / "Sammlung"
    ordner.mkdir(parents=True)
    for n in ("a.iso", "b.iso"):
        (ordner / n).write_bytes(b"x")
    m = _agent_module(tmp_path, EMU_PS2="/bin/true %s")
    ok, msg = m.launch("", "ps2", "ps2/Sammlung")
    assert not ok and "startbaren" in msg, msg
    # Ein EINZELNES Abbild ist dagegen eindeutig und muss gehen.
    (ordner / "b.iso").unlink()
    ok, msg = m.launch("", "ps2", "ps2/Sammlung")
    assert ok, msg
    m._stop_locked()


def test_pcsx2_profile_keeps_the_keyboard(tmp_path):
    """PCSX2 speichert Alternativen als WIEDERHOLTE Schluessel (`&` ist der Akkord).
    Die Gamepad-Belegung kommt deshalb NEBEN die Tastatur, nicht an ihre Stelle —
    sonst nimmt ein Profil dem Betreiber weg, was vorher ging. (#119)"""
    ini = _pcsx2_ini(tmp_path, "[Pad1]\nType = DualShock2\nUp = Keyboard/Up\n\n[Pad2]\n")
    m = _profil_modul(tmp_path)
    geaendert, msg = m.pcsx2_apply()
    text = ini.read_text(encoding="utf-8")
    assert geaendert, msg
    assert "Up = Keyboard/Up" in text, "Tastaturbelegung darf nicht verschwinden"
    assert "Up = SDL-0/DPadUp" in text
    assert "Cross = SDL-0/FaceSouth" in text


def test_pcsx2_profile_is_idempotent(tmp_path):
    """Es laeuft vor JEDEM Start. Ein zweiter Lauf darf die Datei nicht weiter
    aufblaehen — sonst waechst die Konfiguration mit jeder Partie. (#119)"""
    ini = _pcsx2_ini(tmp_path, "[Pad1]\nType = DualShock2\nUp = Keyboard/Up\n\n[Pad2]\n")
    m = _profil_modul(tmp_path)
    m.pcsx2_apply()
    nach_erstem = ini.read_text(encoding="utf-8")
    geaendert, _ = m.pcsx2_apply()
    assert not geaendert
    assert ini.read_text(encoding="utf-8") == nach_erstem


def test_pcsx2_profile_keeps_the_original_backup(tmp_path):
    """Die Sicherung ist der Ausgangsstand vor dem ERSTEN Eingriff. Wuerde sie bei
    jedem Lauf ueberschrieben, sicherte sie ab dem zweiten Lauf nichts mehr. (#119)"""
    ini = _pcsx2_ini(tmp_path, "[Pad1]\nType = DualShock2\nUp = Keyboard/Up\n\n[Pad2]\n")
    m = _profil_modul(tmp_path)
    m.pcsx2_apply()
    sicherung = str(ini) + ".vor-gamepad"
    assert os.path.isfile(sicherung)
    assert "SDL-0" not in open(sicherung, encoding="utf-8").read()
    inhalt = open(sicherung, encoding="utf-8").read()
    m.pcsx2_apply()
    assert open(sicherung, encoding="utf-8").read() == inhalt, "Sicherung wurde ueberschrieben"


def test_pcsx2_profile_refuses_unknown_target(tmp_path):
    m = _profil_modul(tmp_path)
    assert m.main(["--apply", "gibtsnicht"]) == 1
    assert m.main([]) == 2


def test_gamepad_check_page_is_self_contained():
    """Die Fehlersuche darf nicht daran scheitern, dass der Host nicht ins Internet
    kommt — und eine Seite mit externen Verweisen tut genau das, nur langsam und ohne
    Fehlermeldung. (#133)"""
    pfad = os.path.join(REPO, "contrib/streaming-host/web/gamepad-check.html")
    text = open(pfad, encoding="utf-8").read()
    extern = re.findall(r'(?:src|href)\s*=\s*["\'](https?:)?//[^"\']+', text)
    assert not extern, f"externe Ressourcen: {extern}"
    assert "getGamepads" in text and "hasFocus" in text and "isSecureContext" in text


def test_gamepad_check_page_reaches_the_container():
    """Ohne Einhaengung ist die Seite im Repo und nicht im Container. (#133)

    Sie wird nach /opt gehaengt und von init/05-web an ihren Platz kopiert — NICHT
    direkt in die Web-Wurzel, die das Abbild beim Start leerraeumt. Der urspruengliche
    Weg hat genau das gebrochen, siehe
    test_nothing_is_mounted_into_the_selkies_web_root."""
    yml = open(os.path.join(REPO, "contrib/streaming-host/docker-compose.yml"), encoding="utf-8").read()
    assert "./web/gamepad-check.html:/opt/gamepad-check.html:ro" in yml
    init = open(os.path.join(REPO, "contrib/streaming-host/init/05-web"), encoding="utf-8").read()
    assert 'cp -f "$QUELLE"' in init, "die eingehaengte Seite muss an ihren Platz kopiert werden"


def test_rpcs3_binds_player_one_to_sdl_not_the_keyboard(tmp_path):
    """RPCS3s Standard bindet Spieler 1 an die TASTATUR und schreibt bis zum ersten
    Griff in den Einstellungsdialog gar keine Eingabekonfiguration. Am laufenden Host
    nachgemessen: Selkies liefert das Pad, RPCS3 zaehlt es auf, im Spiel passiert
    nichts. (#156)"""
    m = _profil_modul(tmp_path)
    geaendert, msg = m.rpcs3_apply()
    assert geaendert, msg
    pfad = m.rpcs3_input()
    text = open(pfad, encoding="utf-8").read()
    assert "Handler: SDL" in text, text
    # Der Gerätename hat sich mit der Gamepad-Brücke GEÄNDERT (#119): über Selkies'
    # Interposer meldete SDL den rohen Namen "Microsoft X-Box 360 pad", bei echten
    # Kernel-Geräten erkennt es sie an VID/PID und nimmt den Namen aus seiner eigenen
    # Datenbank. Im RPCS3-Log gemessen. Der alte Name darf nicht zurückkehren — er
    # führt zu "Adding empty device": Pad angenommen, an nichts gebunden.
    assert "Xbox 360 Controller 1" in text, text
    assert "Microsoft X-Box 360 pad" not in text, "alter Interposer-Name zurück"
    # Die Belegung wird mitgeliefert; früher musste sie von Hand gesetzt werden, und
    # eine leere Config sieht im Spiel exakt wie ein defekter Controller aus.
    assert "Config:" in text and "Cross: South" in text, text
    assert len(m.RPCS3_BELEGUNG) >= 24, "Belegung unvollständig"
    # Und die Meldung darf nicht mehr zur Handarbeit auffordern.
    assert "Pad-Dialog" not in msg, msg


def test_setup_starter_takes_the_environment_from_the_running_agent(tmp_path):
    """Ein von Hand gestarteter Emulator sieht das Pad NICHT — ohne den
    Selkies-Interposer existieren die virtuellen Geraete fuer SDL nicht, und die
    Geraeteliste bleibt leer. Das sah nach kaputtem Controller aus und war eine
    fehlende Umgebung. Der Starter liest sie beim laufenden Dienst ab statt sie
    nachzubauen — eine zweite Liste derselben Variablen wuerde lautlos auseinander
    laufen. (#160)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/emu-setup"),
                encoding="utf-8").read()
    assert "/proc/$pid/environ" in text, "die Umgebung muss vom Dienst kommen"
    assert "selkies_joystick_interposer" in text, "ohne Interposer-Pruefung fehlt der Hinweis"
    assert "AppRun.wrapped" in text, "Einzelinstanz muss erkannt werden"
    # Der Token des Dienstes hat in der Umgebung eines Einrichtungsprogramms nichts
    # verloren — es wird nur uebernommen, was fuer Anzeige, Ton und Eingabe zaehlt.
    assert "STREAM_AGENT_TOKEN" not in text


def test_rpcs3_never_overwrites_an_existing_mapping(tmp_path):
    """Das Profil laeuft VOR JEDEM Start. Wuerde es eine vorhandene Datei ersetzen,
    waere die von Hand im Pad-Dialog gesetzte Belegung beim naechsten Start weg —
    lautlos, und es haette die Arbeit des Nutzers zunichte gemacht. Genau so war es
    im ersten Wurf. (#158)"""
    m = _profil_modul(tmp_path)
    pfad = m.rpcs3_input()
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    eigen = "Player 1 Input:\n  Handler: SDL\n  Device: \"Mein Pad\"\n  Config:\n    Cross: A\n"
    open(pfad, "w", encoding="utf-8").write(eigen)
    geaendert, msg = m.rpcs3_apply()
    assert not geaendert, msg
    assert open(pfad, encoding="utf-8").read() == eigen, "die eigene Belegung wurde angetastet"


def test_rpcs3_device_name_is_overridable(tmp_path, monkeypatch):
    """Der Name ist abgelesen, nicht geraten — und trotzdem ueberschreibbar, falls ein
    anderes Abbild das Pad anders benennt. Ohne diesen Ausweg muesste man die Datei
    aendern, um einen Namen zu korrigieren. (#156)"""
    monkeypatch.setenv("RPCS3_PAD_NAME", "Irgendein Pad")
    m = _profil_modul(tmp_path)
    m.rpcs3_apply()
    assert "Irgendein Pad" in open(m.rpcs3_input(), encoding="utf-8").read()


def test_every_provided_emulator_has_a_profile_entry(tmp_path):
    """Ein fehlender Eintrag ist nicht von 'braucht nichts' zu unterscheiden. Wer einen
    Emulator hinzufuegt, soll sich entscheiden muessen — deshalb wird die Liste gegen
    den Katalog gehalten. (#119)"""
    katalog = open(os.path.join(REPO, "contrib/streaming-host/init/20-emulators"),
                   encoding="utf-8").read()
    tabelle = re.search(r"KATALOG=\((.*?)\n\)", katalog, re.S).group(1)
    dirs = {z.strip().strip('"').split("|")[1] for z in tabelle.strip().splitlines()
            if z.strip().startswith('"')}
    m = _profil_modul(tmp_path)
    fehlt = dirs - set(m.PROFILE)
    assert not fehlt, f"ohne Profil-Eintrag: {sorted(fehlt)}"


def test_rpcs3_resolves_itself_instead_of_needing_a_hand_typed_url():
    """RPCS3 stand als `url|RPCS3_URL`, weil rpcs3.net automatisierte Abrufe mit 403
    abweist. Folge: PS3 blieb uninstalliert, obwohl Firmware und Titel vorhanden waren
    — und niemand sah, warum. Das Projekt veroeffentlicht seine Linux-Builds selbst in
    einem GitHub-Binaerdepot, das sich wie jedes andere Release aufloesen laesst.

    Bewusst OHNE Netz geprueft: der Test haelt die Entscheidung fest, nicht die
    Verfuegbarkeit von GitHub. Ein Test, der bei jedem Ausfall von GitHub rot wird,
    wird abgeschaltet und schuetzt dann gar nichts mehr."""
    katalog = open(os.path.join(REPO, "contrib/streaming-host/init/20-emulators"),
                   encoding="utf-8").read()
    tabelle = re.search(r"KATALOG=\((.*?)\n\)", katalog, re.S).group(1)
    zeilen = {z.strip().strip('"').split("|")[1]: z.strip().strip('"').split("|")
              for z in tabelle.strip().splitlines() if z.strip().startswith('"')}
    art, quelle, muster = zeilen["rpcs3"][3], zeilen["rpcs3"][4], zeilen["rpcs3"][5]
    assert art == "release", f"RPCS3 soll sich selbst aufloesen, ist aber '{art}'"
    assert "rpcs3-binaries-linux" in quelle, quelle
    assert muster, "ohne Muster waehlt release_asset das erstbeste Asset"


def test_bios_region_is_read_not_guessed(tmp_path):
    """Klartext im Namen zuerst, dann die Regionsziffer der Modellnummer. Alles andere
    bleibt unbekannt — ein geratenes BIOS meldet sich nicht, das Spiel laeuft nur
    'komisch'. (#119)"""
    m = _profil_modul(tmp_path)
    assert m.bios_region("SCPH-70004_BIOS_V12_PAL_200.BIN") == "Europe"
    assert m.bios_region("scph39001.bin") == "USA"
    assert m.bios_region("scph10000.bin") == "Japan"
    assert m.bios_region("irgendwas.bin") == ""          # nicht raten
    assert m.bios_region("scph55555.bin") == ""          # unbekannte Ziffer


def test_bios_refuses_when_the_region_is_missing(tmp_path):
    """Lieber kein BIOS setzen als das falsche. Die Meldung nennt, was da ist. (#119)"""
    bios = tmp_path / ".config/PCSX2/bios"; bios.mkdir(parents=True)
    (tmp_path / ".config/PCSX2/inis").mkdir(parents=True)
    (bios / "scph39001.bin").write_bytes(b"\0" * (4 * 1024 * 1024))
    (tmp_path / ".config/PCSX2/inis/PCSX2.ini").write_text("[Filenames]\nBIOS = x.bin\n", encoding="utf-8")
    m = _profil_modul(tmp_path)
    geaendert, msg = m.pcsx2_bios_setzen("Japan")
    assert not geaendert and "kein BIOS fuer Japan" in msg and "USA" in msg, msg
    assert "BIOS = x.bin" in (tmp_path / ".config/PCSX2/inis/PCSX2.ini").read_text(encoding="utf-8")


def test_firmware_status_distinguishes_file_present_from_installed():
    """`ready` hiess "die Datei liegt da". Fuer RPCS3 ist das nicht dasselbe wie "der
    Emulator hat sie": die PUP muss ins dev_flash eingespielt werden. Vorher meldete
    Romseerr PS3 als vollstaendig, waehrend RPCS3 `SYS: Missing Firmware` schrieb und
    jeder Start im schwarzen Bild geendet waere. Am laufenden Host nachgemessen. (#162)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/init/25-firmware"),
                encoding="utf-8").read()
    tabelle = re.search(r"KATALOG=\((.*?)\n\)", text, re.S).group(1)
    eintraege = {z.strip().strip('"').split("|")[0]: z.strip().strip('"').split("|")
                 for z in tabelle.strip().splitlines() if z.strip().startswith('"')}
    # ps3 muss eine Ablage nennen, sonst ist die Pruefung wirkungslos.
    assert eintraege["ps3"][6].endswith("dev_flash"), eintraege["ps3"]
    # Wo die Datei allein genuegt, darf KEINE Ablage stehen — sonst meldet eine
    # korrekt eingerichtete Plattform ploetzlich "nicht eingespielt".
    for p in ("ps2", "dreamcast", "xbox", "3ds", "switch", "wiiu"):
        assert eintraege[p][6] == "", (p, eintraege[p])
    assert '"installed":%s' in text and '"needs_install":%s' in text


def test_dolphin_is_an_appimage_not_a_distribution_package():
    """Das apt-Paket startet, legt alle Konfigurationsdateien an — und oeffnet NIE ein
    Fenster. Nachgemessen im Container: weder mit noch ohne VirtualGL, mit erzwungenem
    `-platform xcb`, ohne Argumente, mit und ohne Selkies-Interposer. Im X-Baum stand
    nur Qts internes 3x3-Fenster. Die AppImage oeffnet an derselben Stelle
    "Dolphin 2606". (#165)"""
    katalog = open(os.path.join(REPO, "contrib/streaming-host/init/20-emulators"),
                   encoding="utf-8").read()
    tabelle = re.search(r"KATALOG=\((.*?)\n\)", katalog, re.S).group(1)
    zeilen = {z.strip().strip('"').split("|")[1]: z.strip().strip('"').split("|")
              for z in tabelle.strip().splitlines() if z.strip().startswith('"')}
    art, quelle = zeilen["dolphin"][3], zeilen["dolphin"][4]
    assert art == "release", f"Dolphin soll als AppImage kommen, ist aber '{art}'"
    assert "Dolphin-emu-AppImage" in quelle, quelle
    assert "|apt|" not in katalog, "es soll kein apt-Eintrag mehr geben"


def test_nothing_falls_back_to_the_apt_dolphin():
    """Ein Rueckfall auf etwas, das nachweislich kein Fenster oeffnet, ist schlechter
    als keiner: er macht aus einem klaren "nicht installiert" ein stummes "Knopf da,
    nichts passiert". (#165)"""
    agent = open(os.path.join(REPO, "contrib/streaming-host/init/30-agent"),
                 encoding="utf-8").read()
    aktiv = [z for z in agent.splitlines()
             if "/usr/games/dolphin-emu" in z and not z.strip().startswith("#")]
    assert not aktiv, f"noch ein Rueckfall auf das apt-Paket: {aktiv}"
    # AUF DIE EIGENSCHAFT PRUEFEN, NICHT AUF DIE SCHREIBWEISE. Die erste Fassung nagelte
    # `EMU_GC="$VGL $EMU/dolphin/AppRun` woertlich fest und brach, als #440 den Aufruf auf
    # den Helfer `apprun` umstellte — obwohl Dolphin danach genau dasselbe startet. Ein
    # Test, der an einer legitimen Umformulierung scheitert, erzieht dazu, ihn anzupassen
    # statt ihn zu lesen, und das ist der Anfang vom Ende seiner Aussage.
    #
    # Was zaehlt: EMU_GC wird GENAU EINMAL gesetzt, aus dem entpackten AppImage unter
    # $EMU/dolphin — und aus nichts anderem.
    # `EMU_GC=` statt `export EMU_GC=`: Seit SC2155 (declare-and-assign) stehen Zuweisung
    # und Export getrennt — `EMU_GC="…" && export EMU_GC`. Auf die Exportform zu pruefen
    # traf danach nichts mehr. Zum zweiten Mal an dieser Zeile: was zaehlt, ist die
    # Zuweisung, nicht ihre Schreibweise.
    setzungen = [z.strip() for z in agent.splitlines()
                 if "EMU_GC=" in z and not z.strip().startswith("#")]
    assert len(setzungen) == 1, f"EMU_GC wird {len(setzungen)}-mal gesetzt: {setzungen}"
    assert "$EMU/dolphin/AppRun" in setzungen[0] or "apprun dolphin" in setzungen[0], \
        f"Dolphin kommt nicht mehr aus dem entpackten AppImage: {setzungen[0]}"


def test_flycast_is_launched_in_fullscreen_with_the_right_config_syntax():
    """Flycast bekommt Vollbild und Renderer ausdruecklich mitgegeben. (#304)

    NACHGEMESSEN: Seine Konfigurationsdatei war leer — Flycast schreibt erst beim Beenden.
    Er lief also mit den eingebauten Vorgaben, `fullscreen = no` bei 640x480 auf einem
    1920x1080-Bildschirm.

    GEPRUEFT WIRD DIE SEKTION, NICHT NUR DER SCHLUESSEL. `-config pvr.rend=4` sieht richtig
    aus und tut NICHTS: Flycast liest das als Sektion `pvr`, Schluessel `rend`, findet
    nichts und schweigt. Genau daran waere fast die Fehldiagnose „dieser Build kann kein
    Vulkan" entstanden. Ein Test, der nur `pvr.rend` sucht, wuerde den stillen Fall
    durchwinken — deshalb steht hier die volle Form mit `config:`.

    EN: a misspelled `-config` key is silently ignored, so the section prefix is the part
    that must be pinned. Checking for `pvr.rend` alone would pass the broken form.
    """
    agent = open(os.path.join(REPO, "contrib/streaming-host/init/30-agent"),
                 encoding="utf-8").read()
    setzungen = [z.strip() for z in agent.splitlines()
                 if "EMU_DC=" in z and not z.strip().startswith("#")]
    assert len(setzungen) == 1, f"EMU_DC wird {len(setzungen)}-mal gesetzt: {setzungen}"
    zeile = setzungen[0]
    assert "window:fullscreen=yes" in zeile, \
        f"Flycast startet ohne Vollbild — gemessen 640x480 auf 1920x1080: {zeile}"
    assert "config:pvr.rend=" in zeile, (
        "der Renderer ist ohne Sektion angegeben und wird STILL ignoriert — "
        f"`config:pvr.rend=` ist die wirksame Form: {zeile}")


def test_stream_size_and_framerate_are_configured_not_left_to_the_browser():
    """Ohne feste Werte richtet sich der Stream nach dem Browserfenster — hier waren
    das 3828x1902 bei 60 fps, und Bildschirmaufnahme samt Farbkonvertierung kosteten
    dauerhaft CPU. Gemessen: selkies 50 -> 13 %, Xvfb 41 -> 7 %. (#170)"""
    yml = open(os.path.join(REPO, "contrib/streaming-host/docker-compose.yml"),
               encoding="utf-8").read()
    for k in ("SELKIES_MANUAL_WIDTH", "SELKIES_MANUAL_HEIGHT", "SELKIES_FRAMERATE"):
        assert k in yml, k
    env = open(os.path.join(REPO, "contrib/streaming-host/.env.example"),
               encoding="utf-8").read()
    for k in ("STREAM_WIDTH", "STREAM_HEIGHT", "STREAM_FRAMERATE"):
        assert k in env, k


def test_dolphin_gets_dual_core(tmp_path):
    """Dolphin laeuft ohne diese Einstellung EINKERNIG — nachgemessen: ein Thread
    "CPU-GPU thread" bei 100 %, waehrend 27 Threads brachlagen. (#170)"""
    m = _profil_modul(tmp_path)
    assert m.PROFILE["dolphin"]["controller"] is m.dolphin_apply
    # Ohne Dolphin.ini darf es nicht raten, sondern muss das sagen.
    geaendert, msg = m.dolphin_dualcore()
    assert not geaendert and "noch nicht" in msg, msg
    pfad = m.dolphin_ini()
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    open(pfad, "w", encoding="utf-8").write("[Core]\nGFXBackend = OGL\n")
    geaendert, msg = m.dolphin_dualcore()
    assert geaendert, msg
    assert "CPUThread = True" in open(pfad, encoding="utf-8").read()
    # Zweiter Lauf: nichts mehr zu tun (das Profil laeuft vor JEDEM Start).
    assert m.dolphin_dualcore()[0] is False
    # Und dasselbe fuer den Sammelschritt, sobald er einmal durchgelaufen ist —
    # sonst schriebe jeder Start die Dateien neu.
    assert m.dolphin_apply()[0] is True      # erster Lauf: Gamepad fehlt noch
    assert m.dolphin_apply()[0] is False


def test_a_failed_mesa_utils_install_is_reported():
    """Der Fehlschlag verschwand in /dev/null — und genau deshalb war spaeter nicht
    zu beantworten, ob die GPU benutzt wird. Die Fehlersuche lief zweimal in die
    falsche Richtung. (#170)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/init/10-virtualgl"),
                encoding="utf-8").read()
    assert "WARNUNG: mesa-utils" in text, "ein Fehlschlag muss gemeldet werden"
    assert "glxinfo" in text


def test_firmware_is_matched_by_size_where_names_vary():
    """Zweimal hatten wir Dateinamen ERFUNDEN, die es so nicht gibt: xemu erwartete
    angeblich `mcpx_1.0.bin` und `bios.bin` (real: `mcpx-1.1.bin`, `xbox-5838.bin`,
    beide mit korrekter Groesse), und Sonys Vita-Datei heisst `PSVUPDAT.PUP`, nicht
    `PSVITAUPDAT.PUP`. Beide Plattformen wurden als unvollstaendig gemeldet, obwohl
    alles dalag. Die PS2-Zeile machte es von Anfang an richtig. (#172)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/init/25-firmware"),
                encoding="utf-8").read()
    tabelle = re.search(r"KATALOG=\((.*?)\n\)", text, re.S).group(1)
    e = {z.strip().strip('"').split("|")[0]: z.strip().strip('"').split("|")
         for z in tabelle.strip().splitlines() if z.strip().startswith('"')}
    assert "*mcpx*" in e["xbox"][4], e["xbox"][4]
    assert "PSVUPDAT.PUP" in e["psvita"][4] and "PSVITAUPDAT" not in e["psvita"][4]
    # Beide muessen Muster sein, sonst haengt es wieder am Namen.
    for p in ("xbox", "psvita"):
        assert "*" in e[p][4], (p, e[p][4])


def test_a_pattern_picks_the_file_that_fits_the_size():
    """Beim Xbox liegen zwei .bin nebeneinander: MCPX mit 512 B und das BIOS mit
    256 KB. Die alphabetisch erste war immer das MCPX — das BIOS wurde deshalb als
    "Groesse unerwartet" gemeldet, obwohl es danebenlag. (#172)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/init/25-firmware"),
                encoding="utf-8").read()
    assert "groesse_passt" in text, "es braucht eine eigene Groessenpruefung"
    # Mindestmass, weil das Xbox-BIOS in 256 KB, 512 KB und 1 MB vorkommt.
    assert '">"*)' in text, "ein Mindestmass (>N) muss ausdrueckbar sein"
    assert "erste=" in text, "bei mehreren Treffern muss der passende gewaehlt werden"


def test_the_display_backend_is_pinned_not_left_to_chance():
    """Die Emulatoren liefen auf X11, weil es im Container NICHTS ANDERES GAB —
    WAYLAND_DISPLAY nicht gesetzt, kein Socket. Gleichzeitig liefert jedes
    Qt-AppImage `libqwayland.so` neben `libqxcb.so`, und Qt nimmt Wayland, sobald
    die Variable auftaucht. Eine Abwesenheit ist keine Entscheidung: #169 will den
    Xvfb durch ein echtes Xorg ersetzen, und dieser Umbau ist nur zu beurteilen,
    wenn der Unterbau vorher und nachher derselbe ist. (#178)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/init/30-agent"),
                encoding="utf-8").read()
    for var, wert in (("QT_QPA_PLATFORM", "xcb"),
                      ("SDL_VIDEODRIVER", "x11"),
                      ("GDK_BACKEND", "x11")):
        # Vorgabe, nicht Sperre: die Zuweisung muss ueberschreibbar bleiben.
        muster = rf'export {var}="\$\{{{var}:-{wert}\}}"'
        assert re.search(muster, text), f"{var} fehlt oder ist nicht ueberschreibbar"


def test_the_setup_starter_inherits_the_pinned_backend():
    """emu-setup liest die Umgebung aus dem laufenden Dienst und uebernimmt nur eine
    Auswahl — bewusst, damit der Token nicht mitwandert. Genau deshalb muss die
    Auswahl mitwachsen: faellt QT_QPA_PLATFORM heraus, oeffnet der Einrichtungslauf
    den Emulator mit einem anderen Unterbau als der Spielstart, und die Belegung, die
    man dort setzt, gilt fuer ein anderes Fenster. (#178)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/emu-setup"),
                encoding="utf-8").read()
    fall = re.search(r"case \"\$z\" in\n(.*?)\n\s*esac", text, re.S).group(1)
    assert "QT_QPA_PLATFORM=*" in fall, fall
    assert "GDK_BACKEND=*" in fall, fall
    assert "SDL_*" in fall, "SDL_VIDEODRIVER haengt an diesem Muster"
    # Der Token darf weiterhin NICHT mitwandern.
    assert "STREAM_AGENT_TOKEN" not in fall


def test_extraction_resolves_squashfs_root_instead_of_moving_the_symlink():
    """Bei uruntime-AppImages (pkgforge-Dolphin, RPCS3) ist `squashfs-root` KEIN
    Verzeichnis, sondern ein Symlink auf `AppDir`. Das blosse Verschieben legte
    zwei Emulatoren auf DASSELBE Verzeichnis: `dolphin` und `rpcs3` zeigten beide
    auf `./AppDir`, dessen AppRun.wrapped auf `usr/bin/rpcs3` verwies — ein
    GameCube-Titel haette RPCS3 gestartet, ohne eine Fehlermeldung. (#176)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/init/20-emulators"),
                encoding="utf-8").read()
    assert "readlink -f squashfs-root" in text, "das Ziel muss aufgeloest werden"
    # AppDir muss mit weggeraeumt werden, sonst mischen sich zwei Entpackungen.
    assert re.search(r"rm -rf squashfs-root AppDir", text), text[:0] or "AppDir bleibt stehen"
    # Und der Fehlerfall muss laut sein, nicht still.
    assert re.search(r'if \[ -L "\$EMU/\$dir\.neu" \]', text), "Symlink-Fall wird nicht abgefangen"


def test_the_kept_previous_build_is_not_listed_as_an_emulator():
    """`<name>.alt` ist die aufgehobene vorige Fassung, aus der `can_rollback`
    gespeist wird. Sie trug ebenfalls ein AppRun und stand deshalb als eigener
    Emulator ohne Quelle in der Liste — was sie wie eine Altlast aussehen liess.
    Wer sie daraufhin aufraeumt, loescht den Rueckweg. (#176)"""
    text = open(os.path.join(REPO, "contrib/streaming-host/stream-agent.py"),
                encoding="utf-8").read()
    block = re.search(r"def installed_emulators\(\):(.*?)\n\ndef ", text, re.S).group(1)
    assert 'name.endswith(".alt")' in block, block
    # can_rollback muss weiterhin GENAU auf dieses Verzeichnis schauen.
    assert 'name + ".alt", "AppRun"' in block


def test_token_rotation_is_documented_in_both_languages(appmod):
    """Das Wechseln des Tokens steht in der Anleitung — zweisprachig. (#177)

    Ohne beschriebenes Verfahren wird aus einem Alltagsvorgang ein Ausfall: der Wert steht
    an zwei Stellen, und wer nur eine ändert, hat einen Stream, der ohne Erklärung abweist.
    """
    text = open("contrib/streaming-host/README.md", encoding="utf-8").read()
    for marke in ("Das Token wechseln", "Rotating the token"):
        assert marke in text, f"Abschnitt fehlt: {marke}"
    # Die Reihenfolge ist der Kern — ohne sie ist es nur eine Liste von Orten.
    for stelle in ("STREAM_AGENT_TOKEN", "openssl rand", "stream-agent"):
        assert stelle in text, f"{stelle} fehlt in der Anleitung"
    de = text.index("Das Token wechseln"); en = text.index("Rotating the token")
    assert "Reihenfolge" in text[de:de+1800] and "in this order" in text[en:en+1800], \
        "die Reihenfolge muss in beiden Sprachen dastehen, nicht nur in einer"


def test_dolphin_gcpad_uses_the_spelling_dolphin_itself_writes(tmp_path):
    """Dolphin benennt Tasten und Achsen UNTERSCHIEDLICH — und ignoriert still, was es
    nicht auflösen kann.

    Gemessen am 2026-08-10, nachdem Dolphin die Zuweisung selbst geschrieben hatte:
    Tasten tragen den Ereigniscode-Namen OHNE `BTN_` und ohne Zeichen (`SOUTH`),
    Achsen sind durchnummeriert und stehen in schrägen Anführungszeichen (`Axis 1-`).
    Vorher stand hier `BTN_A` bzw. `ABS_Y-`; die Belegung sah vollständig aus und tat
    nichts. Genau das hält dieser Test fest — ein Rückfall auf die alte Schreibweise
    wäre von außen nicht zu erkennen. (#119)
    """
    m = _profil_modul(tmp_path)
    werte = dict(m.DOLPHIN_PAD)
    assert werte["Buttons/A"] == "SOUTH"
    assert werte["Main Stick/Up"] == "`Axis 1-`"
    for schluessel, wert in m.DOLPHIN_PAD:
        assert not wert.startswith("BTN_"), f"{schluessel}: BTN_-Präfix wirkt nicht"
        assert "ABS_" not in wert, f"{schluessel}: Achsen heißen 'Axis N', nicht ABS_*"
    # Jede Achse braucht die schrägen Anführungszeichen, jede Taste darf sie nicht haben.
    for schluessel, wert in m.DOLPHIN_PAD:
        if "Axis" in wert:
            assert wert.startswith("`") and wert.endswith("`"), schluessel


def test_dolphin_gcpad_replaces_only_port_one(tmp_path):
    """Die anderen drei Ports gehören dem Benutzer und dürfen nicht verschwinden.
    Zusätzlich muss ein zweiter Lauf nichts mehr tun, sonst wächst die Datei bei
    jedem Start."""
    m = _profil_modul(tmp_path)
    pfad = m.dolphin_gcpad_ini()
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("[GCPad1]\nDevice = XInput2/0/Virtual core pointer\nButtons/A = `X`\n"
                "\n[GCPad2]\nDevice = etwas\nButtons/A = `Y`\n")

    geaendert, _ = m.dolphin_gcpad()
    assert geaendert
    inhalt = open(pfad, encoding="utf-8").read()
    assert "[GCPad2]" in inhalt and "Device = etwas" in inhalt
    assert "XInput2" not in inhalt.split("[GCPad2]")[0]
    assert os.path.exists(pfad + ".vor-gamepad"), "Rückweg fehlt"

    nochmal, msg = m.dolphin_gcpad()
    assert not nochmal, msg


def test_duckstation_disables_the_setup_wizard(tmp_path):
    """Ohne diesen Schalter ist die schönste Belegung wertlos.

    DuckStation öffnet beim ersten Start einen **modalen** "Setup Wizard". Im Container
    sieht den niemand, und jeder Start staut sich dahinter — gemessen am laufenden Host:
    Prozess lebte, Fenster hieß "DuckStation Setup Wizard", ein Spiel startete nie. Mit
    dem Schalter bootet derselbe Aufruf direkt in den Titel. Dieselbe Falle wie RPCS3s
    Willkommensfenster (#164) und JDownloaders Rückfragen (#219). (#268)
    """
    m = _profil_modul(tmp_path)
    pfad = m.duckstation_ini()
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("[Main]\nConfirmPowerOff = true\n\n[Pad1]\nType = AnalogController\n"
                "Cross = Keyboard/K\n\n[Pad2]\nType = None\n")

    geaendert, msg = m.duckstation_apply()
    assert geaendert, msg
    inhalt = open(pfad, encoding="utf-8").read()
    assert "SetupWizardIncomplete = false" in inhalt, "Erstlaufdialog nicht abgeschaltet"
    # Der Schalter gehört in [Main], nicht in den Pad-Abschnitt.
    assert "SetupWizardIncomplete" in inhalt.split("[Pad1]")[0]
    # South, NICHT FaceSouth: DuckStation kennt PCSX2s Face*-Namen nicht (am Binary
    # nachgemessen) und ignoriert sie stillschweigend — Sticks gehen, Tasten nicht.
    assert "Cross = SDL-0/A" in inhalt
    assert "FaceSouth" not in inhalt, "PCSX2-Name für DuckStation geschrieben"
    assert "Type = AnalogController" in inhalt, "der Controller-Typ gehört dem Benutzer"
    assert "[Pad2]" in inhalt and "Type = None" in inhalt, "Spieler 2 angetastet"
    assert not m.duckstation_apply()[0], "zweiter Lauf darf nichts mehr tun"


def test_duckstation_reuses_the_pcsx2_binding_names(tmp_path):
    """Beide Emulatoren benutzen dieselben Namen und dieselbe SDL-Quelle — nachgesehen
    in DuckStations eigener settings.ini. Eine zweite Tabelle daneben würde auseinander
    laufen, sobald jemand nur eine pflegt. (#268)"""
    m = _profil_modul(tmp_path)
    quelle = open(os.path.join(REPO, "contrib/streaming-host/launch-profile.py"),
                  encoding="utf-8").read()
    # Es darf genau EINE Bindungstabelle geben.
    assert quelle.count("\"Cross\":") == 1, "zweite Tabelle mit denselben Namen angelegt"
    assert m.PROFILE["duckstation"]["controller"] is m.duckstation_apply
    assert m.PROFILE["duckstation"]["geprueft"] is True, \
        "am 2026-08-10 im Spiel bestätigt — Controller inklusive Tasten"


def test_duckstation_resets_the_wizard_flag_when_it_flips_back(tmp_path):
    """DuckStation setzt den Schalter beim BEENDEN wieder auf `true`.

    Am laufenden Host passiert: Schalter gesetzt, Spiel bootete direkt — und nach dem
    Beenden stand wieder `SetupWizardIncomplete = true` in der Datei, dazu war die
    Pad-Belegung verschwunden. Beim nächsten Start öffnete der Dialog erneut.

    Eine Prüfung auf "steht der Schlüssel da?" hält das für erledigt. Geprüft werden
    muss der WERT — und die vorhandene Zeile ersetzt, nicht eine zweite danebengelegt,
    sonst stehen zwei widersprechende Einträge in derselben Datei. Das Profil läuft vor
    jedem Start, also heilt es sich damit selbst. (#268)
    """
    m = _profil_modul(tmp_path)
    pfad = m.duckstation_ini()
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    # Genau der Zustand, den DuckStation hinterlässt: Schalter zurück, Belegung weg.
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("[Main]\nConfirmPowerOff = true\nSetupWizardIncomplete = true\n\n"
                "[Pad1]\nType = AnalogController\nCross = Keyboard/K\n\n[Pad2]\nType = None\n")

    geaendert, msg = m.duckstation_apply()
    assert geaendert, msg
    inhalt = open(pfad, encoding="utf-8").read()
    assert "SetupWizardIncomplete = false" in inhalt
    assert "SetupWizardIncomplete = true" not in inhalt, "alter Wert blieb stehen"
    assert inhalt.count("SetupWizardIncomplete") == 1, "zwei widersprechende Einträge"
    assert inhalt.count("SDL-0/") == 25, "Belegung nicht wiederhergestellt"

    # Und wenn NUR der Schalter zurückkippt, muss die Belegung unangetastet bleiben.
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(inhalt.replace("SetupWizardIncomplete = false",
                               "SetupWizardIncomplete = true"))
    geaendert, msg = m.duckstation_apply()
    assert geaendert and "Erstlauf" in msg, msg
    wieder = open(pfad, encoding="utf-8").read()
    assert "SetupWizardIncomplete = false" in wieder
    assert wieder.count("SDL-0/") == 25, "Belegung beim Nachziehen zerstört"


def test_duckstation_face_buttons_use_its_own_names(tmp_path):
    """DuckStation kennt PCSX2s `Face*`-Namen NICHT.

    Am ausgelieferten Binary nachgemessen (2026-08-10):

        src/util/sdl_input_source.cpp, Tabelle s_button_info:
        "A", "B", "X", "Y", "LeftShoulder", ... — kein FaceSouth, kein South

    Alle übrigen 21 Werte sind identisch. Der Fehler entstand, weil ich geprüft hatte,
    dass die SCHLÜSSEL übereinstimmen, und daraus schloss, die Werte täten es auch:
    Stick und Steuerkreuz funktionierten, die vier Tasten nicht — stillschweigend.
    Deshalb hält dieser Test genau die Abweichung fest. (#268)
    """
    m = _profil_modul(tmp_path)
    assert m.DUCKSTATION_ANDERS == {
        "FaceSouth": "A", "FaceEast": "B",
        "FaceWest": "X", "FaceNorth": "Y",
    }, "Abweichungstabelle geändert — gegen s_button_info im Quelltext prüfen"
    # Was NICHT abweicht, darf auch nicht übersetzt werden.
    for wert in ("DPadUp", "LeftShoulder", "LeftStick", "+LeftTrigger", "-LeftY",
                 "Back", "Start", "Guide"):
        assert wert not in m.DUCKSTATION_ANDERS, wert
    # Und die Tabelle muss auf PCSX2s Werte passen, sonst übersetzt sie ins Leere.
    for pcsx2_wert in m.DUCKSTATION_ANDERS:
        assert pcsx2_wert in m.PCSX2.values(), f"{pcsx2_wert} gibt es bei PCSX2 gar nicht"


def test_agent_starts_with_dropped_privileges():
    """Der Start-Dienst darf NICHT als root laufen.

    Solange er es tat, liefen auch die Emulatoren als root und schrieben ihre
    Konfigurationen root-eigen — ein im Desktop gestarteter Emulator (`abc`) konnte
    sie dann weder lesen noch schreiben. Gefunden: Dolphins Verzeichnis nicht
    beschreibbar, PCSX2.ini mit Modus 600 nicht lesbar, RPCS3s input_configs.
    Das Fehlerbild ist ein "defekter Controller" oder ein Emulator, der Einstellungen
    vergisst — **ohne jede Fehlermeldung**. (#273)

    `s6-setuidgid` und nicht `setpriv`, weil es die ZUSATZGRUPPEN behält; an einer
    davon (`video5zxv`) hängt der Zugriff auf die GPU-Knoten.
    """
    text = open(os.path.join(REPO, "contrib/streaming-host/init/30-agent"),
                encoding="utf-8").read()
    start = [z for z in text.splitlines()
             if "stream-agent.py" in z or ('"$AGENT"' in z and "nohup" in z)]
    starter = [z for z in start if "nohup" in z]
    assert starter, "keine Startzeile für den Agenten gefunden"
    for z in starter:
        assert "s6-setuidgid" in z, f"Agent startet ohne Rechteabgabe: {z.strip()}"
    # Und der Altbestand muss geheilt werden, sonst bleibt Unlesbares liegen.
    assert "-user 0" in text and "chown" in text, \
        "keine Reparatur der root-eigenen Altdateien"


def test_the_two_seats_do_not_share_ports_but_do_share_config():
    """Zwei Plätze müssen sich `/config` und die GPU teilen — aber niemals Ports.

    Der erste Anlauf benutzte `extends`, und **`extends` führt Listen zusammen**: der
    zweite Dienst erbte damit die Ports des ersten und hätte beim Start mit "port is
    already allocated" abgebrochen. Das wäre erst beim Ausrollen aufgefallen. Deshalb
    prüft dieser Test beide Richtungen — was getrennt sein muss und was gemeinsam. (#137)
    """
    import yaml
    pfad = os.path.join(REPO, "contrib/streaming-host/docker-compose.yml")
    d = yaml.safe_load(open(pfad, encoding="utf-8"))
    s1, s2 = d["services"]["stream-host"], d["services"]["stream-host-2"]

    def haefen(s):
        return {str(p).split(":")[0] for p in (s.get("ports") or [])}
    assert not (haefen(s1) & haefen(s2)), \
        f"Platz 1 und 2 veröffentlichen denselben Port: {haefen(s1) & haefen(s2)}"
    assert len(haefen(s2)) == 3, "der zweite Platz braucht genau drei eigene Ports"

    # Geteilt, weil der Betreiber es so gewählt hat: eine Bibliothek, eine GPU,
    # ein /config. Liefe der zweite Platz auf anderen Volumes, wäre es ein zweiter Host.
    assert s1.get("volumes") == s2.get("volumes"), "Volumes müssen geteilt sein"
    assert s1.get("devices") == s2.get("devices"), "GPU muss geteilt sein"

    # Nur Platz 1 aktualisiert die gemeinsamen Emulatoren — sonst entpacken zwei
    # Container dieselbe AppImage in dasselbe Verzeichnis.
    assert str(s2["environment"]["EMU_AUTO_UPDATE"]).lower() == "false"
    assert s2["environment"]["AGENT_PORT"] != s1["environment"]["AGENT_PORT"]

    # Ohne Profil bleibt die Anlage einsitzig — ein zweiter Container darf nicht
    # ungefragt mitstarten.
    assert s2.get("profiles") == ["seat2"]
    assert not s1.get("profiles")


def test_gpu_encoding_is_switched_on():
    """Ohne `SELKIES_AUTO_GPU` kodiert Selkies in SOFTWARE — lautlos.

    Gemessen am 2026-08-10: ~1,2 CPU-Kerne je Sitzung, während die Video-Engine der
    Karte brachlag (VCS durchgehend 0 %). Im Log steht dann nur eine Zeile:
    `No GPU Encoder available -> Using CPU Software Encoding`.

    Der Grund ist eine Rechnung im Selkies-Quelltext: ohne die Variable leitet es den
    GPU-Index aus dem NAMEN des Knotens ab (`renderD129` → Index 1) und öffnet die n-te
    Karte — der Container hat aber genau eine, und die ist dort Index 0. Mit AUTO_GPU
    sucht das Aufnahmemodul die Karte selbst und die Rechnung entfällt.

    Die Variable war schon einmal gesetzt und ist beim Umstieg auf Compose verloren
    gegangen, weil sie nur am Container hing (dieselbe Falle wie bei SELKIES_FRAMERATE).
    Deshalb dieser Test. (#283)
    """
    import yaml
    pfad = os.path.join(REPO, "contrib/streaming-host/docker-compose.yml")
    d = yaml.safe_load(open(pfad, encoding="utf-8"))
    for dienst in ("stream-host", "stream-host-2"):
        env = d["services"][dienst].get("environment") or {}
        wert = str(env.get("SELKIES_AUTO_GPU", ""))
        assert wert, f"{dienst}: SELKIES_AUTO_GPU fehlt — Kodierung fiele auf die CPU zurück"
        # Der Code prüft gegen diese Liste; ein Standard aus ihr wäre wirkungslos.
        assert not any(w in wert.lower() for w in ("false", "off", "no")) or ":-" in wert, \
            f"{dienst}: Standardwert schaltet die GPU-Kodierung ab: {wert}"


def test_a_permission_error_is_reported_not_thrown(tmp_path):
    """Ein Rechtefehler darf das Startprofil nicht als Traceback verlassen.

    Genau das ist passiert (2026-08-10): `PCSX2.ini` gehörte noch root mit Modus 600 —
    ein Überbleibsel aus der Zeit, als Emulatoren als root liefen (#273). Der Agent
    läuft seither als `abc`, konnte die Datei nicht lesen, und der `PermissionError`
    verließ das Profil als Traceback:

        PermissionError: [Errno 13] Permission denied: '.../PCSX2.ini'

    Folge: Der Schritt brach ab, BIOS und Vollbild wurden nicht gesetzt, und PCSX2 kam
    mit einem 500×101-Dialog statt mit dem Spiel hoch. Von außen: "der Stream geht auf,
    aber es startet kein Spiel" — nichts daran deutet auf Dateirechte.

    Die Meldung muss deshalb sagen, **wem** die Datei gehört, **wer** wir sind und
    **was zu tun ist**. Und der Rückgabewert darf kein Erfolg sein. (#283/#273)
    """
    m = _profil_modul(tmp_path)
    pfad = m.pcsx2_ini()
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("[Pad1]\nType = DualShock2\n")
    os.chmod(pfad, 0o000)
    try:
        geaendert, msg = m.sicher(m.pcsx2_apply)
    finally:
        os.chmod(pfad, 0o600)
    assert not geaendert, "ein Rechtefehler darf nicht als Erfolg gelten"
    assert msg.startswith("KEIN ZUGRIFF"), msg
    for teil in ("gehoert", "wir sind", "chown"):
        assert teil in msg, f"Meldung nennt '{teil}' nicht: {msg}"


# ------------------------------------------- xemu: Erstkonfiguration (#300)

def test_xemu_gets_extra_library_paths_at_launch():
    """xemu braucht zwei Bibliothekspfade, die sonst niemand braucht. (#300)

    Ohne `/config/lib` scheitert der Start an fehlender `libusb-1.0.so.0` — xemus
    AppImage bringt sie als einziges nicht mit. Ohne den Pulse-Unterordner bleibt der
    Ton stumm, weil ALSA sein Pulse-Modul nicht laden kann.

    Geprueft wird am Quelltext des Agenten, weil hier kein Emulator laeuft.
    """
    quelle = open(os.path.join(REPO, "contrib/streaming-host/stream-agent.py"),
                  encoding="utf-8").read()
    assert '"xbox": ["/config/lib"' in quelle, "xemu bekommt keinen libusb-Pfad"
    assert "pulseaudio" in quelle, "Pulse-Unterordner fehlt — der Ton bliebe stumm"
    # Die vorhandene Umgebung darf nicht verlorengehen.
    assert "vorher = umg.get(\"LD_LIBRARY_PATH\", \"\")" in quelle
    # Und der Start muss die Umgebung auch benutzen.
    assert "env=umgebung" in quelle, "Popen bekommt die Umgebung nicht"


def test_xemu_init_script_is_wired_and_defensive():
    """`init/22-xemu-vorbereiten` holt libusb und das Festplattenabbild. (#300)"""
    pfad = os.path.join(REPO, "contrib/streaming-host/init/22-xemu-vorbereiten")
    assert os.access(pfad, os.X_OK), "Init-Skript ist nicht ausfuehrbar"
    text = open(pfad, encoding="utf-8").read()
    assert "libusb-1.0.so.0" in text and "xbox_hdd.qcow2" in text
    # Nach /config, nicht nach /usr: nur /config ueberlebt eine Abbild-Aktualisierung.
    assert "/config/lib" in text and "/usr/lib" not in text.split("HDD_URL")[0]
    # Fehlendes Netz darf den Containerstart nicht abbrechen.
    assert "exit 0" in text.splitlines()[-1]
    # Nur taetig werden, wenn xemu ueberhaupt da ist.
    assert "/config/emulators/xemu/AppRun" in text


def test_xemu_goes_fullscreen_by_key_not_by_config(tmp_path, monkeypatch):
    """xemu ignoriert `fullscreen` in seiner Konfiguration, und der Fenstertrick
    vergroessert nur die Huelle — der gezeichnete Bereich bleibt 960 Pixel breit in
    einem 1920 breiten Fenster. Nur F11 wirkt. Alles am laufenden Host gemessen. (#300)
    """
    m = _profil_modul(tmp_path)
    gesendet = []

    class R:
        stdout = "12345"
        stderr = ""
        returncode = 0

    def falsches_x(*args, **kw):
        gesendet.append(args)
        return R()

    monkeypatch.setattr(m, "_x", falsches_x)
    monkeypatch.setattr(m.time, "sleep", lambda *_a: None)

    ok, msg = m.xemu_vollbild()
    assert ok, msg
    tasten = [a for a in gesendet if a[:2] == ("xdotool", "key")]
    assert tasten, f"keine Taste gesendet: {gesendet}"
    assert "F11" in tasten[0], tasten[0]
    # Das Fenster muss vorher den Fokus bekommen, sonst geht die Taste ins Leere.
    assert any(a[:2] == ("xdotool", "windowactivate") for a in gesendet), gesendet


def test_xemu_fullscreen_reports_when_no_window_exists(tmp_path, monkeypatch):
    """Ohne laufenden Emulator gibt es nichts zu schalten — das muss gesagt werden,
    statt stillschweigend Erfolg zu melden. (#300)"""
    m = _profil_modul(tmp_path)

    class Leer:
        stdout = ""
        stderr = ""
        returncode = 1

    monkeypatch.setattr(m, "_x", lambda *a, **k: Leer())
    ok, msg = m.xemu_vollbild()
    assert not ok and "kein xemu-Fenster" in msg, msg


def test_encrypted_3ds_images_are_rejected_before_launch(tmp_path):
    """Ein verschluesselter Titel darf gar nicht erst starten. (#299)

    Azahar spielt ausschliesslich entschluesselte Dumps und entschluesselt NICHT selbst;
    der Wunsch danach wurde upstream als "closed as not planned" abgelehnt. Ohne diese
    Pruefung endet so ein Titel als leerer Stream — der Emulator startet, zeigt
    `App Encrypted` oder gar kein Fenster, und der Nutzer sieht einen Desktop ohne
    jede Erklaerung.

    Am Bestand nachgemessen: 1248 von 1249 Abbildern verschluesselt. Das ist der
    Normalfall einer Sammlung aus Cartridge-Dumps, kein Randfall.
    """
    import importlib.util
    pfad = os.path.join(REPO, "contrib/streaming-host/stream-agent.py")
    spec = importlib.util.spec_from_file_location("agent_3ds_test", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    verschluesselt = str(tmp_path / "verschluesselt.3ds")
    entschluesselt = str(tmp_path / "entschluesselt.3ds")
    _ncsd_bauen(verschluesselt, nocrypto=False)
    _ncsd_bauen(entschluesselt, nocrypto=True)

    ok, grund = m._3ds_spielbar(verschluesselt)
    assert not ok, "verschluesseltes Abbild wurde durchgelassen"
    assert "VERSCHLUESSELT" in grund, grund

    ok, _ = m._3ds_spielbar(entschluesselt)
    assert ok, "entschluesseltes Abbild wurde faelschlich abgewiesen"

    # CIAs starten nie direkt — unabhaengig von jeder Verschluesselung.
    cia = str(tmp_path / "paket.cia")
    open(cia, "wb").write(b"x" * 100)
    ok, grund = m._3ds_spielbar(cia)
    assert not ok and "Installationspakete" in grund, grund

    # Was kein NCSD ist, wird NICHT abgewiesen: lieber starten lassen und den
    # Emulator entscheiden, als einen brauchbaren Titel wegen einer zu strengen
    # Pruefung zu blockieren.
    fremd = str(tmp_path / "fremd.3ds")
    open(fremd, "wb").write(b"x" * 100)
    ok, _ = m._3ds_spielbar(fremd)
    assert ok, "unbekanntes Format darf nicht abgewiesen werden"
def test_azahar_binds_the_pad_and_swaps_a_b(tmp_path):
    """Azahars Voreinstellung ist die TASTATUR — dieselbe Falle wie RPCS3 (#156).

    Und die 3DS-Tasten sind gegenueber Xbox VERTAUSCHT: A liegt rechts, B unten. Wer
    stur A auf A legt, bekommt ein Pad, auf dem jede Bestaetigung abbricht. (#304)
    """
    m = _profil_modul(tmp_path)
    ini = m.azahar_ini()
    os.makedirs(os.path.dirname(ini), exist_ok=True)
    with open(ini, "w", encoding="utf-8") as f:
        f.write("[Controls]\nprofile=0\n"
                'profiles\\1\\button_a="code:65,engine:keyboard"\n'
                "profiles\\1\\button_a\\default=true\n")
    geaendert, msg = m.azahar_apply()
    assert geaendert, msg
    text = open(ini, encoding="utf-8").read()
    assert "engine:sdl" in text and "engine:keyboard" not in text, text
    # A und B vertauscht: 3DS-A liegt auf SDL-Knopf 1, 3DS-B auf 0.
    assert 'button_a="button:1' in text, text
    assert 'button_b="button:0' in text, text
    # Qts default-Flag muss false sein, sonst gilt der Wert nicht.
    assert "button_a\\default=false" in text, text


def test_azahar_does_not_overwrite_an_existing_sdl_mapping(tmp_path):
    """Eine vorhandene SDL-Belegung stammt von Azahars Auto-Map — und nur das kennt den
    richtigen Port.

    Im Container liegen ACHT identische Pad-Geraete; unseres ist fuer SDL das dritte,
    nicht das erste. Der Port haengt an der Aufzaehlungsreihenfolge und kann sich
    verschieben, deshalb darf eine funktionierende Belegung nicht ueberschrieben
    werden. (#304)
    """
    m = _profil_modul(tmp_path)
    ini = m.azahar_ini()
    os.makedirs(os.path.dirname(ini), exist_ok=True)
    vorhanden = ("[Controls]\nprofile=0\n"
                 'profiles\\1\\button_a="button:1,engine:sdl,guid:abc,port:2"\n'
                 "profiles\\1\\button_a\\default=false\n")
    with open(ini, "w", encoding="utf-8") as f:
        f.write(vorhanden)
    geaendert, msg = m.azahar_apply()
    assert not geaendert, msg
    assert open(ini, encoding="utf-8").read() == vorhanden, "Auto-Map wurde ueberschrieben"


def test_the_emulator_script_keeps_more_than_one_generation():
    """Der Rueckweg reicht mehr als eine Fassung weit, und die Marke wandert mit. (#338)

    Vorher gab es genau eine (`.alt`), und `rollback` TAUSCHTE aktuelle und vorige Fassung:
    zweimal zurueck landete wieder am Anfang. Schlimmer war der wahrscheinliche Fall — ein
    Update auf eine bereits kaputte Fassung ueberschrieb die letzte gute.

    Geprueft wird die Struktur des Skripts, nicht sein Lauf: Es laeuft nur IM Container,
    und die Ringlogik wurde dort gegen ein nachgebautes Verzeichnis gemessen (vier
    Installationen, drei Rueckschritte, drei verschiedene Fassungen).

    Die `.url`-Marke ist der Punkt, an dem es still schiefgehen kann: Sie ist es, wogegen
    die automatische Aktualisierung vergleicht. Eine zurueckgeholte Fassung ohne ihre Marke
    wuerde beim naechsten Lauf sofort wieder auf die kaputte gehoben.
    """
    pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "contrib", "streaming-host", "init", "20-emulators")
    with open(pfad, encoding="utf-8") as f:
        skript = f.read()

    assert "GENERATIONEN=${EMU_GENERATIONEN:-3}" in skript, \
        "die Zahl der aufgehobenen Fassungen ist nicht einstellbar"
    assert "generationen_schieben" in skript and "generationen_zaehlen" in skript
    # Der alte Tausch darf nicht zurueckkommen — er ist der Fehler, um den es ging.
    assert "$dir.zurueck" not in skript, "rollback tauscht wieder, statt zurueckzugehen"
    # Altbestand mit nur einer Generation muss uebernommen werden.
    assert '$dir.alt" ] && [ ! -d "$EMU/$dir.alt1"' in skript, \
        "der Altbestand aus der Ein-Generationen-Zeit wird nicht uebernommen"
    # Die Marke wandert mit der Fassung.
    assert '$dir.url.alt1"' in skript, "die .url-Marke wandert nicht mit"


def test_an_update_run_covers_installed_emulators(appmod):
    """Ein Aktualisierungslauf erfasst, was installiert IST — nicht nur, was eingeschaltet
    ist. (#313)

    Der Schalter `INSTALL_*` heisst „installiere das beim Start". Wer einen Emulator ueber
    die Oberflaeche installiert hat, setzt ihn nicht — und das sind hier alle. Der Lauf
    uebersprang sie vollstaendig und meldete trotzdem Erfolg: `/update` antwortete
    „gestartet", die Fassung blieb unveraendert.
    """
    pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "contrib", "streaming-host", "init", "20-emulators")
    with open(pfad, encoding="utf-8") as f:
        skript = f.read()
    assert 'installiert "$(feld "$zeile" 2)" || continue' in skript, \
        "installierte Emulatoren werden beim Sammellauf wieder uebersprungen"


# --- #356: die Fehlerklasse „ausgeliefert und wirkungslos" --------------------------

def test_the_3ds_decrypt_url_names_a_file_that_upstream_actually_has():
    """Der Dateiname in der Quell-URL muss einer sein, den es gibt. (#356)

    WARUM DAS EINE PRUEFUNG WERT IST: Die erste Fassung zeigte auf `decrypt.py`; das
    Repository hat `decrypt_3ds.py` und `decrypt_cia.py`. Der Name war geraten. Das Skript
    bricht bei einem Fehlschlag ABSICHTLICH mit `exit 0` ab, damit der Container startet —
    also war die Faehigkeit einfach nicht da, ohne dass irgendwo etwas rot wurde.
    Ausgeliefert und wirkungslos ist der teuerste Zustand: Er sieht aus wie fertig.
    """
    pfad = os.path.join(REPO, "contrib/streaming-host/init/23-3ds-entschluesseln")
    text = open(pfad, encoding="utf-8").read()
    m = re.search(r"DECRYPT_3DS_URL:-(\S+?)\}", text)
    assert m, "keine Vorgabe-URL gefunden"
    assert os.path.basename(m.group(1)) in ("decrypt_3ds.py", "decrypt_cia.py"), \
        f"{m.group(1)} nennt eine Datei, die es im Repository nicht gibt"


def test_the_3ds_setup_does_not_gate_on_a_file_the_tool_never_reads():
    """Keine Sperre auf `boot9.bin` — das Werkzeug oeffnet die Datei nie. (#356)

    Es traegt die vier Retail-KeyX fest im Quelltext. Die Sperre prueft eine Voraussetzung,
    die es nicht gibt — und lag zusaetzlich VOR `25-firmware`, das die Datei erst hinlegt.
    Zwei Fehler ergaenzten sich so zu einem dritten: Sie konnte auf einem frischen
    Container nie zutreffen.
    """
    pfad = os.path.join(REPO, "contrib/streaming-host/init/23-3ds-entschluesseln")
    for nr, zeile in enumerate(open(pfad, encoding="utf-8"), 1):
        if zeile.lstrip().startswith("#"):
            continue
        assert "boot9" not in zeile, \
            f"Zeile {nr} macht die Einrichtung von boot9.bin abhaengig: {zeile.strip()}"


def test_the_agent_reads_the_same_title_id_as_romseerr(tmp_path):
    """Agent und Romseerr muessen dieselbe Titel-ID lesen. (#315)

    Zwei Leser derselben Struktur sind eine Stelle, an der spaeter genau eine angepasst
    wird. Solange es sie gibt, muessen sie nachweislich uebereinstimmen — sonst sagt
    Romseerr zu, was der Agent ablehnt.
    """
    import importlib.util
    pfad = os.path.join(REPO, "contrib", "streaming-host", "stream-agent.py")
    spec = importlib.util.spec_from_file_location("stream_agent_tid", pfad)
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)

    import app as appmod
    for kategorie in (0x00040000, 0x00040002, 0x0004000E, 0x0004008C):
        tid = (kategorie << 32) | 0x00123400
        datei = _cia_datei(tmp_path, f"T{kategorie:08X}.cia", tid)
        assert agent.cia_titel_id(datei)[0] == appmod.cia_titel_id(datei)[0] == tid, \
            f"Agent und Romseerr lesen 0x{kategorie:08X} verschieden"


def test_the_decrypted_cia_is_found_whatever_the_tool_names_it(tmp_path, monkeypatch):
    """Der Agent findet die Ausgabe, ohne ihren Namen nachzurechnen. (#388)

    Der Fehler: `decrypt_cia.py` haengt IMMER `-decrypted.cia` an, der Agent erwartete die
    Endung der Eingabe. Bei der atomaren `.part`-Datei gingen beide auseinander — die
    Entschluesselung lief durch, 342 MB lagen korrekt da, und der Start scheiterte mit
    „keine Ausgabedatei".
    """
    agent = _agent_modul()
    quelle = tmp_path / "Titel.cia"
    quelle.write_bytes(b"\x00" * 64)
    cache = tmp_path / "cache"
    monkeypatch.setattr(agent, "ENTSCHL_CACHE", str(cache))
    monkeypatch.setattr(agent, "ENTSCHL_WERKZEUG_CIA", _falsches_werkzeug(tmp_path, "normal"))
    monkeypatch.setattr(agent, "_cache_aufraeumen", lambda schonen="": None)

    ziel, fehler = agent._cia_entschluesseln(str(quelle))
    assert not fehler, f"unerwarteter Fehler: {fehler}"
    assert os.path.isfile(ziel) and os.path.getsize(ziel) == 64

    # UND der Fall, der den alten Weg wirklich bricht: ein Ausgabename, den man aus der
    # Eingabe NICHT herleiten kann. Mit einer sauberen `.cia` als Eingabe waere die
    # Nachrechnung zufaellig richtig gewesen — dieser Test war ohne diesen Teil
    # gegenstandslos, was die Gegenprobe gezeigt hat.
    os.remove(ziel)
    monkeypatch.setattr(agent, "ENTSCHL_WERKZEUG_CIA",
                        _falsches_werkzeug(tmp_path, "anderer_name"))
    ziel2, fehler2 = agent._cia_entschluesseln(str(quelle))
    assert not fehler2, f"Ausgabe mit unerwartetem Namen nicht gefunden: {fehler2}"
    assert os.path.isfile(ziel2)


def test_nothing_is_left_behind_in_the_cache(tmp_path, monkeypatch):
    """Weder Erfolg noch Fehlschlag hinterlassen Reste. (#388)

    Der alte Weg loeschte zwei Namen, von denen keiner die echte Ausgabe war: Bei jedem
    Versuch blieben Hunderte Megabyte liegen — und zaehlten gegen den Deckel des
    Zwischenspeichers, ohne je benutzt zu werden.
    """
    agent = _agent_modul()
    quelle = tmp_path / "Titel.cia"
    quelle.write_bytes(b"\x00" * 64)
    cache = tmp_path / "cache"
    monkeypatch.setattr(agent, "ENTSCHL_CACHE", str(cache))
    monkeypatch.setattr(agent, "_cache_aufraeumen", lambda schonen="": None)

    monkeypatch.setattr(agent, "ENTSCHL_WERKZEUG_CIA", _falsches_werkzeug(tmp_path, "normal"))
    ziel, _ = agent._cia_entschluesseln(str(quelle))
    assert sorted(os.listdir(cache)) == [os.path.basename(ziel)], \
        f"nach dem Erfolg liegt mehr im Zwischenspeicher: {os.listdir(cache)}"

    os.remove(ziel)
    monkeypatch.setattr(agent, "ENTSCHL_WERKZEUG_CIA", _falsches_werkzeug(tmp_path, "nichts"))
    ziel2, fehler = agent._cia_entschluesseln(str(quelle))
    assert fehler and not ziel2, "ein Werkzeug ohne Ausgabe muss einen Fehler ergeben"
    assert os.listdir(cache) == [], \
        f"nach dem Fehlschlag bleibt etwas liegen: {os.listdir(cache)}"


def test_every_contrib_tool_is_named_in_its_readme():
    """Jedes Werkzeug unter `contrib/` steht in der README daneben. (#395)

    GEMESSEN BEIM FUND: `contrib/streaming-host/README.md` hat 1.444 Zeilen und erwaehnte
    fuenf der dortigen Dateien mit keinem Wort — darunter `launch-profile.py` mit 1.187
    Zeilen, also den zweitgroessten Brocken des Verzeichnisses, und `emu-setup`, ohne das
    sich keine Tastenbelegung setzen laesst.

    Die Dateien selbst sind gut dokumentiert; jede traegt einen zweisprachigen Kopf. Nur
    erfaehrt man von ihrer Existenz nicht, wenn man nicht ohnehin `ls` tippt. Doku, die
    voraussetzt, dass man schon weiss, wonach man sucht, hilft genau denen nicht, fuer die
    sie da ist.

    EN: every tool under contrib/ must be named in the README beside it. The files carry
    good headers; the problem was that nothing pointed at them.
    """
    fehlend = {}
    for ordner in sorted(os.listdir(os.path.join(REPO, "contrib"))):
        basis = os.path.join(REPO, "contrib", ordner)
        readme = os.path.join(basis, "README.md")
        if not os.path.isdir(basis) or not os.path.isfile(readme):
            continue
        text = open(readme, encoding="utf-8").read()
        luecke = []
        for wurzel, verz, dateien in os.walk(basis):
            verz[:] = [v for v in verz
                       if v not in ("__pycache__", ".pytest_cache", "node_modules")]
            for datei in dateien:
                pfad = os.path.join(wurzel, datei)
                # Nur ausfuehrbare Werkzeuge. Beiwerk (Bilder, .md, Konfiguration im Web-
                # Verzeichnis) einzeln aufzuzaehlen waere Ballast ohne Nutzen.
                if datei.endswith(".md") or not os.access(pfad, os.X_OK):
                    continue
                if datei not in text:
                    luecke.append(os.path.relpath(pfad, basis))
        if luecke:
            fehlend[ordner] = sorted(luecke)
    assert not fehlend, (
        "diese Werkzeuge kommen in der README daneben nicht vor — man findet sie nur, "
        f"wenn man ohnehin nachsieht: {json.dumps(fehlend, ensure_ascii=False)}")


def test_the_agent_reads_the_same_format_as_romseerr(appmod, tmp_path):
    """Beide Seiten muessen dieselbe Datei gleich einordnen. (#422)

    WARUM DAS EINE EIGENE PRUEFUNG BRAUCHT: `dreids_art` in `app.py` und `_3ds_art` im
    Agenten sind zwei Kopien derselben Regel. Laufen sie auseinander, sagt Romseerr zu und
    der Agent ab — der Nutzer klickt, belegt einen Platz und bekommt eine Absage, die
    Romseerr eine Sekunde vorher ausgeschlossen hatte. Das ist der unangenehmste Zustand:
    zwei Aussagen, beide fuer sich stimmig, die sich widersprechen.

    Der Fix fuer #422 musste deshalb auf BEIDEN Seiten passieren. Diese Pruefung haelt sie
    zusammen, statt sich darauf zu verlassen, dass jemand daran denkt.

    EN: the rule exists twice. If the copies drift, Romseerr promises and the agent refuses
    a second later. This holds them together instead of relying on someone remembering.
    """
    import importlib.util
    pfad = os.path.join(REPO, "contrib", "streaming-host", "stream-agent.py")
    os.environ["STREAM_AGENT_TOKEN"] = "testtoken"
    os.environ["STREAM_ROMS"] = appmod.ROMS
    spec = importlib.util.spec_from_file_location("stream_agent_422", pfad)
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)

    faelle = [
        (_cia_datei(tmp_path, "getarnte.3ds", 0x0004000000000000), ".cia"),
        (_cia_datei(tmp_path, "ehrliche.cia", 0x0004000000000000), ".cia"),
        (_3ds_datei(tmp_path, "abbild.cia", verschluesselt=False), ".3ds"),
        (_3ds_datei(tmp_path, "abbild.3ds", verschluesselt=False), ".3ds"),
    ]
    for datei, erwartet in faelle:
        a, b = appmod.dreids_art(datei), agent._3ds_art(datei)
        assert a == b == erwartet, (
            f"{os.path.basename(datei)}: Romseerr sagt {a!r}, der Agent {b!r}, "
            f"erwartet {erwartet!r}")

    # Und die Unentschieden-Regel gilt auf beiden Seiten gleich.
    fremd = tmp_path / "fremd.3ds"
    fremd.write_bytes(b"\x00" * 4096)
    assert appmod.dreids_art(str(fremd)) == agent._3ds_art(str(fremd)) == ""


def test_romseerr_and_the_agent_refuse_the_same_switch_packages(appmod, tmp_path):
    """Beide Seiten sagen dasselbe ab. (#427)

    Romseerr fragt vor der Platzvergabe, der Agent noch einmal beim Start. Laufen die
    beiden auseinander, haengt die Zusage daran, welchen Weg jemand genommen hat — und ein
    direkter Aufruf des Dienstes umgeht die Pruefung ganz.

    EN: if the two drift, whether a launch is refused depends on which route was taken.
    """
    import importlib.util
    pfad = os.path.join(REPO, "contrib", "streaming-host", "stream-agent.py")
    os.environ["STREAM_AGENT_TOKEN"] = "testtoken"
    os.environ["STREAM_ROMS"] = appmod.ROMS
    spec = importlib.util.spec_from_file_location("stream_agent_427", pfad)
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)

    for kennung, soll_ab in (("0100633007d48000", False), ("0100633007d48800", True),
                             ("010091d01597d002", True)):
        f = _nsp_datei(tmp_path, f"x{kennung}.nsp", kennung)
        rs_ab = not appmod.switch_startbar(f)[0]
        ag_ab = bool(agent._switch_art(f))
        assert rs_ab == ag_ab == soll_ab, (
            f"{kennung}: Romseerr weist ab={rs_ab}, Agent={ag_ab}, erwartet {soll_ab}")


def test_a_killed_emulator_is_reaped():
    """Nach `kill()` wird gewartet — sonst bleibt ein Zombie stehen. (#428)

    WAS PASSIERT WAR: `_stop_locked` schickt SIGTERM, wartet 8 s und schickt dann SIGKILL —
    ohne danach zu warten. Das Kind ist tot, aber nie abgeholt: ein Zombie je beendeter
    Sitzung, fuer die ganze Laufzeit des Dienstes. Eden verlaesst SIGTERM nicht binnen 8 s,
    nimmt also immer diesen Zweig.

    WARUM DAS MEHR KOSTET ALS EINEN TABELLENEINTRAG: `ps` zeigt einen Zombie mit demselben
    Namen und weiterlaufender Zeit wie einen lebenden Prozess. Ich habe daran zweimal die
    falsche Diagnose gestellt — „der Emulator laeuft nach /stop weiter" — und ein Issue mit
    dieser Behauptung geschrieben, bevor ich die Zustandsspalte gelesen habe.

    WARUM DAS HIER EINE QUELLTEXTPRUEFUNG IST und kein Verhaltenstest — nachgemessen, nicht
    angenommen: Ein Verhaltenstest funktioniert in DIESEM Prozess nicht. Jedes
    `subprocess.Popen` irgendwo im selben Python-Prozess ruft `subprocess._cleanup()` auf
    und erntet dabei ALLE beendeten Kinder. Im Testlauf gibt es solche Aufrufe, das Kind
    wird also ohnehin abgeholt — die Pruefung waere mit UND ohne den Fix gruen.

    Gemessen: allein laufend bleibt das Kind ohne `p.wait()` ein Zombie
    (`State: Z (zombie)` nach 0,3 s, 1 s und 2 s), mit `p.wait()` ist es weg. Unter pytest
    ist es in beiden Faellen weg. Ein Verhaltenstest haette also Sorgfalt bewiesen, die es
    nicht gibt — genau das Muster, gegen das die uebrigen Pruefungen hier gebaut sind.

    EN: this is a source check on purpose. Any `subprocess.Popen` in the same process reaps
    all finished children, so a behavioural test would be green with and without the fix.
    Measured standalone: without `p.wait()` the child stays `Z (zombie)`; with it, it is gone.

    SEIT #489 IST DER HARTE ABBRUCH EIN `SIGKILL` AN DIE PROZESSGRUPPE, nicht mehr
    `p.kill()` — weil `p` bei Vita3K die Shell des Wrappers ist und nicht der Emulator.
    Geprueft wird deshalb weiter dasselbe: dass es einen harten Abbruch gibt und dass
    danach geerntet wird. Nur die Schreibweise hat sich geaendert, nicht die Zusage.

    EN: since #489 the hard abort is a SIGKILL to the process group; the promise checked
    here — hard abort, then reap — is unchanged.
    """
    quelle = open(os.path.join(REPO, "contrib", "streaming-host", "stream-agent.py"),
                  encoding="utf-8").read()
    m = re.search(r"^def _stop_locked\(\):(.*?)(?=^def |\Z)", quelle, re.S | re.M)
    assert m, "_stop_locked ist nicht mehr auffindbar"
    koerper = m.group(1)
    hart = re.search(r"^\s*(p\.kill\(\)|_senden\(p, gruppe, signal\.SIGKILL\))\s*$",
                     koerper, re.M)
    assert hart, "der harte Abbruch fehlt"
    nach_kill = koerper[hart.end():]
    assert re.search(r"^\s*p\.wait\(\)\s*$", nach_kill, re.M), (
        "nach dem harten Abbruch wird nicht geerntet — das Kind bleibt als Zombie stehen, "
        "und `ps` zeigt es wie einen laufenden Emulator")


# --- #440: ein Update darf den Emulator nicht loeschen ------------------------------

def test_installing_an_emulator_moves_the_new_build_into_place():
    """Nach `generationen_schieben` muss `.neu` an seinen Platz. (#440)

    OHNE DIESE ZEILE IST EIN UPDATE EINE LOESCHUNG. `generationen_schieben` raeumt die
    bisherige Fassung nach `.alt1`; der frisch entpackte Baum liegt als `$dir.neu`. Fehlt
    die Umbenennung, gibt es `$dir` danach NICHT MEHR — und `30-agent` setzt seine
    `EMU_*`-Variable nur, wenn `$dir/AppRun` existiert. Die ganze Plattform verschwindet.

    Gemessen am 2026-08-12: `ps2` und `ps3` fehlten seit dem 11.08. 10:22 in `/status`,
    waehrend 17 PS3-Titel in der Bibliothek lagen. Beide waren an dem Tag aktualisiert
    worden. Kein Fehler, kein Fenster, keine fehlende Datei, nach der jemand gesucht
    haette — der Streamen-Knopf erschien einfach nicht mehr.

    QUELLTEXTPRUEFUNG, weil der Fehlerfall ein vollstaendiger Installationslauf mit
    Download und Entpacken waere. Was hier schuetzt, ist die Zusicherung, dass die
    Umbenennung ueberhaupt vorkommt — und zwar NACH dem Schieben, denn davor wuerde sie
    von ihm wieder weggeraeumt.

    EN: without the rename an update deletes the emulator: the previous build moves to
    .alt1 and the new tree stays at .neu, so $dir is gone and the platform disappears.
    """
    quelle = open(os.path.join(REPO, "contrib", "streaming-host", "init", "20-emulators"),
                  encoding="utf-8").read()
    assert 'mv "$EMU/$dir.neu" "$EMU/$dir"' in quelle, (
        "die neue Fassung wird nie an ihren Platz geschoben — ein Update loescht damit "
        "den Emulator, den es aktualisieren sollte")

    # NICHT ab einem Suchbegriff versetzen: `quelle.index("installiere")` traf die
    # Funktionsdefinition, die NACH ihrem eigenen Aufruf von `generationen_schieben`
    # steht — die Suche lief ins Leere und der Test brach mit `ValueError` ab, also mit
    # einem Fehler ueber die Suche statt ueber die geprueste Sache.
    schieben = quelle.index('generationen_schieben "$dir"\n')
    umbenennen = quelle.index('mv "$EMU/$dir.neu" "$EMU/$dir"')
    assert schieben < umbenennen, (
        "die Umbenennung steht VOR dem Generationenschub — der wuerde sie wieder "
        "wegraeumen")


def test_vita3k_is_started_at_the_binary_not_through_the_shell_wrapper():
    """Der erzeugte Startbefehl endet an der Binaerdatei, nicht an AppRun. (#489)

    AM HOST GEMESSEN. `AppRun.wrapped` ist bei den anderen Emulatoren das Programm und
    wird `exec`-t; bei Vita3K ist es ein Shell-Skript, das das Programm als KIND startet:

        head -c2 AppRun.wrapped:  vita3k "#!"   rpcs3 ELF   cemu ELF

        #!/bin/sh
        if [ "${APPIMAGE}" != "" ]; then
            export PATH="$APPDIR/usr/bin:$PATH"
            "${APPDIR}/usr/bin/Vita3K" $@       <- kein exec, $@ unquotiert
        fi

    Der Agent fuehrt damit die PID der SHELL. Gemessen: `/stop` meldet `ok`, `/status`
    sagt `running: false`, und der Emulator laeuft als Waise weiter (PPid 1) — erst
    `kill -9` beendet ihn. Die Fensterpruefung meldete `kein sichtbares Fenster`,
    waehrend dasselbe Werkzeug an der echten PID `Welcome to Vita3K` fand (#488).

    Der Test FUEHRT den Helfer aus, statt die Zeile zu lesen: dass `apprun_direkt` im
    Text steht, sagt noch nicht, dass er auf die Binaerdatei zeigt.

    EN: executes the helper and checks the command it emits ends at the binary, carries
    the PATH the wrapper would have set, and survives shlex.split unchanged.
    """
    quelle = open(os.path.join(REPO, "contrib", "streaming-host", "init", "30-agent"),
                  encoding="utf-8").read().splitlines()
    try:
        start = next(i for i, z in enumerate(quelle) if z.startswith("apprun_direkt() {"))
    except StopIteration:
        raise AssertionError("apprun_direkt() fehlt in init/30-agent (#489)")
    ende = next(i for i in range(start, len(quelle)) if quelle[i].strip() == "}")
    funktion = "\n".join(quelle[start:ende + 1])

    lauf = subprocess.run(
        ["bash", "-c", f'EMU=/emu; VGL=vglrun; PATH=/usr/bin\n{funktion}\n'
                       'apprun_direkt vita3k Vita3K'],
        capture_output=True, text=True)
    assert lauf.returncode == 0, lauf.stderr
    befehl = lauf.stdout

    assert befehl.endswith("/emu/vita3k/usr/bin/Vita3K"), (
        f"der Startbefehl endet nicht an der Binaerdatei: {befehl!r}")
    # NICHT im Text nach "/AppRun" suchen: `APPIMAGE=.../AppRun` steht dort voellig zu
    # Recht — der Wrapper wird uebersprungen, die Variable muss aber gesetzt bleiben,
    # sonst tut das entpackte AppImage gar nichts (#440/#314). Gefragt ist, ob AppRun
    # als AUSFUEHRBARES ARGUMENT auftaucht.
    ausfuehrbar = [t for t in shlex.split(befehl) if "=" not in t.split("/")[0]]
    assert not any(t.endswith("/AppRun") for t in ausfuehrbar), (
        f"laeuft weiterhin ueber den Wrapper: {ausfuehrbar}")
    # Der Wrapper setzte PATH — faellt er weg, muss es hier stehen.
    assert "PATH=/emu/vita3k/usr/bin:/usr/bin" in befehl, (
        f"der PATH, den der Wrapper gesetzt hat, fehlt: {befehl!r}")
    assert "APPDIR=/emu/vita3k" in befehl and "APPIMAGE=/emu/vita3k/AppRun" in befehl

    # Der Agent zerlegt die Zeile mit shlex — nichts darf dabei zerfallen.
    teile = shlex.split(befehl)
    assert teile[-1] == "/emu/vita3k/usr/bin/Vita3K", teile
    assert "vglrun" in teile, teile


def test_every_emulator_is_launched_with_appdir_and_appimage():
    """Entpackte AppImages bekommen APPDIR und APPIMAGE. (#440/#314)

    WARUM: `linuxdeploy` erzeugt bei manchen Emulatoren ein `AppRun.wrapped`, das das
    Programm nur startet, wenn `$APPIMAGE` gesetzt ist:

        if [ "${APPIMAGE}" != "" ]; then "${APPDIR}/usr/bin/Vita3K" $@ ; fi

    Beim entpackten Baum ist sie leer — der Zweig wird uebersprungen und der Prozess endet
    mit **Exit 0 und ohne jede Ausgabe**. Am Host nachgestellt: `stdout 0 Bytes, stderr 0
    Bytes`. Mit gesetzten Variablen startet Vita3K normal und meldet seine Version.

    Betroffen sind vita3k, cemu und rpcs3 — gesetzt wird es aber fuer ALLE. Vier
    Sonderfaelle waeren die Sorte Wissen, die beim naechsten neuen Emulator fehlt, und
    `APPDIR` auf den entpackten Baum zu zeigen ist ohnehin richtig.

    EN: some extracted AppImages exit 0 with no output unless $APPIMAGE is set. Applied to
    every emulator rather than to the three known ones.
    """
    quelle = open(os.path.join(REPO, "contrib", "streaming-host", "init", "30-agent"),
                  encoding="utf-8").read()
    assert "apprun()" in quelle, "der Helfer, der APPDIR/APPIMAGE setzt, fehlt"
    assert "APPDIR=" in quelle and "APPIMAGE=" in quelle

    # ZWEI STARTFORMEN SEIT #489, und beide setzen APPDIR/APPIMAGE:
    #   apprun <ordner>                 ueber AppRun  — die Regel
    #   apprun_direkt <ordner> <prog>   an der Binaerdatei, vorbei am Shell-Wrapper
    # Nur nach `$(apprun ` zu suchen haette die zweite Form fuer einen rohen Start
    # gehalten; nur die Zahl zu senken haette Vita3K klammheimlich aus der Pruefung
    # genommen. Gezaehlt wird deshalb, was eine EMU_*-Startzeile ist, egal welche Form.
    # `[^"]*` VOR dem Helferaufruf: Eine Startzeile darf etwas voranstellen — xemu
    # setzt `env LD_LIBRARY_PATH=/config/lib` (#525). Ohne diese Lockerung fiel genau
    # diese Zeile aus der Zaehlung, und der Test blieb gruen, weil 10 >= 10 noch
    # stimmte. Eine Pruefung, aus der ein Fall stillschweigend herausfaellt, ist
    # schlimmer als eine, die fehlt.
    zeilen = [z.strip() for z in quelle.splitlines()
              if re.search(r'\bEMU_[A-Z0-9]+="[^"]*\$\(apprun', z)]
    alle = [z.strip() for z in quelle.splitlines() if re.search(r'\bEMU_[A-Z0-9]+="', z)]
    assert len(zeilen) == len(alle), (
        "diese Startzeilen werden nicht mitgezaehlt und damit nicht geprueft: "
        f"{[z for z in alle if z not in zeilen]}")
    assert len(zeilen) >= 10, f"nur {len(zeilen)} Startzeilen gefunden — Muster kaputt?"

    # Kein Emulator darf an beiden Helfern vorbei gestartet werden.
    roh = [z.strip() for z in quelle.splitlines()
           if re.search(r'\bEMU_[A-Z0-9]+="', z) and "$(apprun" not in z]
    assert not roh, (
        "diese Emulatoren werden ohne APPDIR/APPIMAGE gestartet und koennen deshalb "
        f"stillschweigend nichts tun: {roh}")

    # Und die zweite Form muss es wirklich geben — sonst faellt Vita3K stumm auf den
    # Wrapper zurueck, und #489 ist wieder da.
    # xemu startet ohne diesen Pfad SOFORT nicht — `libusb-1.0.so.0` liegt in
    # /config/lib, und nichts sonst macht das dem Lader bekannt (#525).
    xemu = [z for z in zeilen if "EMU_XBOX=" in z]
    assert xemu, "die xemu-Startzeile fehlt"
    assert "LD_LIBRARY_PATH=/config/lib" in xemu[0], (
        "xemu wird ohne Bibliothekspfad gestartet und endet sofort mit "
        f"'error while loading shared libraries: libusb-1.0.so.0': {xemu[0]}")

    assert "apprun_direkt()" in quelle, "der Helfer aus #489 fehlt"
    assert any("apprun_direkt vita3k" in z for z in zeilen), (
        "Vita3K wird wieder ueber den Shell-Wrapper gestartet — /stop wirkt dann nicht "
        "und die Fensterpruefung sieht die Shell (#489)")


def _heilungsschleife():
    """Die Schleife aus `init/30-agent`, die root-eigene Dateien zurueckgibt.

    Herausgeschnitten von `for baum in` bis zum zugehoerigen `done`, damit der Test das
    AUSGELIEFERTE Skript prueft und nicht eine Kopie im Test.
    """
    quelle = open(os.path.join(REPO, "contrib", "streaming-host", "init", "30-agent"),
                  encoding="utf-8").read().splitlines()
    try:
        start = next(i for i, z in enumerate(quelle) if z.startswith("for baum in "))
    except StopIteration:
        raise AssertionError("die Heilungsschleife fehlt in init/30-agent")
    ende = next(i for i in range(start, len(quelle)) if quelle[i].strip() == "done")
    return "\n".join(quelle[start:ende + 1])


def test_the_ownership_healing_covers_the_cache_directory(tmp_path):
    """`/config/.cache` muss mitgeheilt werden — daran hing Cemu. (#509)

    GEMESSEN am 2026-08-13 am laufenden Host:

        drwxr-xr-x 2 root root  /config/.cache/Cemu        (angelegt 2026-08-10)
        3044 Dateien unter /config/.cache gehoerten root

    Cemu oeffnete daraufhin einen modalen Dialog — „Cemu can't write to
    /config/.cache/Cemu!" — und kam nie bis zur eigenen Initialisierung: kein Protokoll,
    kein Hauptfenster, und der Dialog reagierte auf keine Taste und keinen Klick. Von
    aussen sah das nach einem kaputten Startpfad aus (#502).

    DER TEST FUEHRT DIE SCHLEIFE AUS, mit zwei Anpassungen, die er offenlegt:

      * `/config` zeigt auf ein Wegwerfverzeichnis — sonst wuerde er am echten
        Container arbeiten.
      * `-user 0` wird zur eigenen Kennung. Ohne root lassen sich keine root-eigenen
        Dateien anlegen; die Frage „welche Baeume laeuft die Schleife ab und was gibt
        sie weiter?" bleibt davon unberuehrt.

    `chown` ist eine Attrappe im PATH, die nur mitschreibt. Damit braucht der Test keine
    Rechte und veraendert nichts.

    EN: executes the healing loop against a throwaway tree with `chown` stubbed, so it
    needs no privileges. `/config` and `-user 0` are substituted, and the test says so.
    """
    schleife = _heilungsschleife()

    wurzel = tmp_path / "config"
    for teil in (".config/PCSX2", ".local/share/Cemu", ".cache/Cemu",
                 ".cache/mesa_shader_cache/17"):
        (wurzel / teil).mkdir(parents=True)
        (wurzel / teil / "datei").write_text("x")
    (wurzel / "agent-token").write_text("geheim")

    stub = tmp_path / "bin"
    stub.mkdir()
    mitschrift = tmp_path / "chown.log"
    (stub / "chown").write_text(
        f'#!/bin/sh\nshift\nfor a in "$@"; do echo "$a" >> "{mitschrift}"; done\n')
    (stub / "chown").chmod(0o755)

    angepasst = (schleife.replace("/config", str(wurzel))
                         .replace("-user 0", '-user "$(id -u)"'))
    lauf = subprocess.run(["bash", "-c", angepasst], capture_output=True, text=True,
                          env={**os.environ, "PATH": f"{stub}:{os.environ['PATH']}"})
    assert lauf.returncode == 0, lauf.stderr

    beruehrt = mitschrift.read_text().splitlines() if mitschrift.exists() else []
    for erwartet in (".config/PCSX2/datei", ".local/share/Cemu/datei",
                     ".cache/Cemu/datei", ".cache/mesa_shader_cache/17/datei"):
        assert any(p.endswith(erwartet) for p in beruehrt), (
            f"{erwartet} wurde nicht geheilt — dort blieb es root-eigen. "
            f"Beruehrt wurden: {beruehrt}")

    # DIE GEGENRICHTUNG, und sie ist die wichtigere: `/config/agent-token` gehoert root
    # mit Absicht und muss es bleiben. Es ist das Einzige zwischen einer Anfrage und
    # einem gestarteten Prozess auf dem Host — ein `chown -R /config` wuerde es `abc`
    # uebergeben, und die Pruefung oben waere trotzdem gruen.
    assert not any(p.endswith("agent-token") for p in beruehrt), (
        "das Token wurde mitgeheilt — es muss root:600 bleiben (siehe README, #273)")


def test_a_missing_agent_refuses_instead_of_starting_a_stale_copy(tmp_path):
    """Ohne `/opt/stream-agent.py` bricht der Start ab — er weicht NICHT aus. (#500)

    Hier stand ein Rueckfall:

        [ -f "$AGENT" ] || AGENT=/config/stream-agent.py   # Rueckfall fuer Altbestand

    Am laufenden Host nachgemessen, was er gestartet haette:

        /opt/stream-agent.py      75621 Byte   1510 Zeilen   (aus dem Repo)
        /config/stream-agent.py    6703 Byte    158 Zeilen   (7. August, verwaist)

    Die Altfassung kennt weder `psx` noch `psvita`, `ps3` oder `xbox` und verdrahtet
    Emulatorpfade, die es nicht mehr gibt. Sie haette Anfragen beantwortet und gesund
    ausgesehen — der Stream kommt hoch, die Emulatortabelle ist falsch, und nichts sagt
    warum. Ein Rueckfall ist nur dann ein Netz, wenn das Hineinfallen SICHTBAR ist.

    Dieser Test FUEHRT den Block aus, statt ihn zu lesen: dass die Zeile weg ist, sagt
    noch nicht, dass der Abbruch auch eintritt.

    EN: executes the path-choosing block from the shipped script. A missing agent must
    exit non-zero with a message, not silently fall back to a stale copy.
    """
    block = _agent_pfadwahl()
    # Nur die WIRKSAMEN Zeilen — der Kommentar darf den alten Pfad nennen, er erklaert ihn.
    wirksam = [z for z in block.splitlines() if not z.strip().startswith("#")]
    assert not any("/config/stream-agent.py" in z for z in wirksam), (
        "die Pfadwahl greift weiterhin aktiv auf /config/stream-agent.py zurueck: "
        f"{[z for z in wirksam if '/config/stream-agent.py' in z]}")

    # /opt/stream-agent.py gibt es auf dem Testlaeufer nicht — genau der Fall.
    assert not os.path.exists("/opt/stream-agent.py"), (
        "unerwartet: auf diesem Rechner existiert /opt/stream-agent.py, "
        "der Fehlfall laesst sich so nicht pruefen")
    lauf = subprocess.run(["bash", "-c", block], capture_output=True, text=True,
                          cwd=str(tmp_path))
    assert lauf.returncode != 0, (
        f"fehlender Agent wurde nicht abgelehnt (Exit {lauf.returncode}) — "
        "genau so startet still eine Altfassung")
    meldung = lauf.stderr + lauf.stdout
    assert "stream-agent.py" in meldung, f"keine brauchbare Meldung: {meldung!r}"


def test_the_agent_path_is_taken_when_it_exists(tmp_path):
    """Die Gegenprobe: ist die Datei da, laeuft der Block durch. (#500)

    Ohne sie beweist der Test darueber nur, dass irgendetwas fehlschlaegt — auch ein
    Block, der IMMER abbricht, waere gruen. Der Pfad wird dafuer auf eine vorhandene
    Datei umgebogen; alles andere bleibt der ausgelieferte Text.

    EN: the counter-check. Without it a block that always aborts would pass too.
    """
    echt = tmp_path / "stream-agent.py"
    echt.write_text("# Platzhalter\n")
    block = _agent_pfadwahl().replace("/opt/stream-agent.py", str(echt))
    lauf = subprocess.run(["bash", "-c", block + "\necho OK-$AGENT"],
                          capture_output=True, text=True, cwd=str(tmp_path))
    assert lauf.returncode == 0, f"vorhandener Agent wurde abgelehnt: {lauf.stderr!r}"
    assert f"OK-{echt}" in lauf.stdout, lauf.stdout


def test_the_agent_reports_platforms_that_have_no_emulator(appmod):
    """Was FEHLT, wird genannt — nicht nur, was da ist. (#440)

    DER TEURE ZUSTAND WAR NICHT DER FEHLER, SONDERN SEINE UNSICHTBARKEIT. `/status` nannte
    seit jeher nur die vorhandenen Plattformen. Als `ps2` und `ps3` verschwanden, sah das
    aus wie „war nie da" — Romseerr antwortete `not_supported`, der Knopf fehlte, und kein
    Protokolleintrag sagte, dass hier etwas abhanden gekommen ist.

    Ein Fehlen ist dabei kein Alarm: Wer keinen PS2-Emulator installiert, soll nichts Rotes
    sehen. Die Auskunft ist eine Tatsache, die den Unterschied zwischen „nicht eingerichtet"
    und „verschwunden" ueberhaupt erst sichtbar macht.

    EN: the expensive part was not the fault but its invisibility. Reported as a fact, not
    an alarm.
    """
    import importlib.util
    pfad = os.path.join(REPO, "contrib", "streaming-host", "stream-agent.py")
    os.environ["STREAM_AGENT_TOKEN"] = "testtoken"
    os.environ["STREAM_ROMS"] = appmod.ROMS
    os.environ["EMU_PS2"] = ""                       # nicht eingerichtet
    os.environ["EMU_PSX"] = "/gibt/es/nicht/AppRun -batch %s"   # eingerichtet, aber weg
    spec = importlib.util.spec_from_file_location("stream_agent_440", pfad)
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)
    try:
        fehlt = agent.fehlende_plattformen()
        assert "ps2" in fehlt, "eine Plattform ohne Startbefehl wird nicht gemeldet"
        assert "psx" in fehlt, (
            "eine Plattform, deren AppRun verschwunden ist, wird nicht gemeldet — genau "
            "der Fall, der ps2 und ps3 einen Tag lang unsichtbar gemacht hat")
        assert "platforms_missing" in open(pfad, encoding="utf-8").read(), \
            "die Auskunft steht nicht in /status"
    finally:
        os.environ.pop("EMU_PSX", None)


def test_vita3k_switches_the_measured_key_and_only_that(tmp_path, monkeypatch):
    """Vita3K bekommt `boot-apps-full-screen: true` — und sonst nichts. (#304)

    AM LAUFENDEN HOST ABGELESEN: Die `config.yml` traegt genau einen Schalter dafuer, und
    er stand auf `false`. `backend-renderer` steht dort bereits auf `Vulkan` und darf NICHT
    mitverstellt werden — wer beim Vollbild auch am Renderer dreht, sucht den naechsten
    Fehler an der falschen Stelle.
    """
    import importlib.util
    pfad = os.path.join(REPO, "contrib/streaming-host/launch-profile.py")
    spec = importlib.util.spec_from_file_location("lp_vita", pfad)
    lp = importlib.util.module_from_spec(spec)
    monkeypatch.setenv("FW_CONFIG_ROOT", str(tmp_path))
    spec.loader.exec_module(lp)

    d = tmp_path / ".config" / "Vita3K"
    d.mkdir(parents=True)
    (d / "config.yml").write_text(
        "stretch_the_display_area: false\n"
        "backend-renderer: Vulkan\n"
        "boot-apps-full-screen: false\n"
        "keyboard-gui-fullscreen: F11\n", encoding="utf-8")

    geaendert, meldung = lp.vita3k_vollbild()
    assert geaendert, meldung
    text = (d / "config.yml").read_text(encoding="utf-8")
    assert "boot-apps-full-screen: true" in text
    assert "backend-renderer: Vulkan" in text, "der Renderer wurde mitverstellt"
    assert "keyboard-gui-fullscreen: F11" in text, "eine fremde Zeile ging verloren"

    # Zweiter Aufruf aendert nichts mehr — sonst schriebe jeder Start die Datei neu.
    nochmal, _ = lp.vita3k_vollbild()
    assert nochmal is False


def test_vita3k_creates_nothing_when_the_config_is_absent(tmp_path, monkeypatch):
    """Fehlt die `config.yml`, wird KEINE angelegt. (#304)

    Eine von uns erfundene Konfiguration koennte Felder vermissen lassen, die der Emulator
    erwartet — und der Fehler saehe danach nach einem kaputten Emulator aus statt nach
    einer erfundenen Datei. Vita3K schreibt sie beim Beenden selbst.
    """
    import importlib.util
    pfad = os.path.join(REPO, "contrib/streaming-host/launch-profile.py")
    spec = importlib.util.spec_from_file_location("lp_vita2", pfad)
    lp = importlib.util.module_from_spec(spec)
    monkeypatch.setenv("FW_CONFIG_ROOT", str(tmp_path))
    spec.loader.exec_module(lp)

    geaendert, meldung = lp.vita3k_vollbild()
    assert geaendert is False
    assert "noch nicht" in meldung
    assert not (tmp_path / ".config").exists(), "es wurde doch etwas angelegt"


def test_vita3k_does_not_invent_the_key_when_it_is_missing(tmp_path, monkeypatch):
    """Fehlt der Schluessel, wird er NICHT angehaengt. (#304)

    Haette die naechste Fassung ihn umbenannt, waere ein angehaengter Eintrag wirkungslos —
    und wir haetten trotzdem Erfolg gemeldet. Das ist der Fall „ausgeliefert und
    wirkungslos", nur eine Ebene frueher.
    """
    import importlib.util
    pfad = os.path.join(REPO, "contrib/streaming-host/launch-profile.py")
    spec = importlib.util.spec_from_file_location("lp_vita3", pfad)
    lp = importlib.util.module_from_spec(spec)
    monkeypatch.setenv("FW_CONFIG_ROOT", str(tmp_path))
    spec.loader.exec_module(lp)

    d = tmp_path / ".config" / "Vita3K"
    d.mkdir(parents=True)
    (d / "config.yml").write_text("backend-renderer: Vulkan\n", encoding="utf-8")

    geaendert, meldung = lp.vita3k_vollbild()
    assert geaendert is False
    assert "steht nicht" in meldung, meldung
    assert (d / "config.yml").read_text(encoding="utf-8") == "backend-renderer: Vulkan\n"


def test_vita3k_takes_both_startup_dialogs_out_of_the_way(tmp_path, monkeypatch):
    """`show-welcome: false` UND `check-for-updates-mode: 0` — beide, sonst nichts. (#488)

    Der Willkommensdialog allein reicht nicht: mit ihm aus dem Weg bootet der Titel zwar,
    aber `Update Available` legt sich mitten auf das Spielfenster. Beide Werte sind am
    laufenden Host gemessen, jeder mit Gegenprobe.
    """
    lp = _lp_mit_config(tmp_path, monkeypatch, "lp_vita_dlg1")

    d = tmp_path / ".config" / "Vita3K"
    d.mkdir(parents=True)
    (d / "config.yml").write_text(
        "backend-renderer: Vulkan\n"
        "boot-apps-full-screen: true\n"
        "show-welcome: true\n"
        "warn-missing-firmware: true\n"
        "check-for-updates-mode: 1\n", encoding="utf-8")

    geaendert, meldung = lp.vita3k_dialoge()
    assert geaendert, meldung
    text = (d / "config.yml").read_text(encoding="utf-8")
    assert "show-welcome: false" in text, text
    assert "check-for-updates-mode: 0" in text, text
    # NICHTS SONST. `warn-missing-firmware` ist der dritte Dialog derselben Klasse und
    # bleibt bewusst stehen: die Firmware ist vollstaendig (#485/#486), der Schalter hat
    # hier also nichts abzufangen — und wer ihn mitverstellt, verliert die Warnung genau
    # dann, wenn sie einmal berechtigt waere.
    assert "warn-missing-firmware: true" in text, text
    assert "backend-renderer: Vulkan" in text, "der Renderer wurde mitverstellt"
    assert "boot-apps-full-screen: true" in text, "eine fremde Zeile ging verloren"

    # Zweiter Aufruf schreibt nicht noch einmal — sonst faende Vita3K bei jedem Start
    # eine frisch geschriebene Datei vor.
    nochmal, _ = lp.vita3k_dialoge()
    assert nochmal is False


def test_vita3k_dialogs_create_nothing_when_the_config_is_absent(tmp_path, monkeypatch):
    """Fehlt die `config.yml`, wird KEINE angelegt. (#488)

    Dieselbe Regel wie beim Vollbild (#304): eine von uns erfundene Konfiguration koennte
    Felder vermissen lassen, die der Emulator erwartet.
    """
    lp = _lp_mit_config(tmp_path, monkeypatch, "lp_vita_dlg2")

    geaendert, meldung = lp.vita3k_dialoge()
    assert geaendert is False
    assert "noch nicht" in meldung, meldung
    assert not (tmp_path / ".config").exists(), "es wurde doch etwas angelegt"


def test_vita3k_dialogs_do_not_invent_a_missing_key(tmp_path, monkeypatch):
    """Fehlt ein Schluessel, wird er NICHT angehaengt — er wird GEMELDET. (#488)

    Die Ratsche gegen genau den Fall, an dem DuckStations Wizard zweimal zurueckkam:
    eine neue Fassung benennt den Schalter um, ein angehaengter Eintrag bliebe wirkungslos,
    und wir haetten trotzdem Erfolg gemeldet. Der andere, vorhandene Schluessel wird
    trotzdem gesetzt — halb wirksam ist besser als gar nicht, solange es dabeisteht.
    """
    lp = _lp_mit_config(tmp_path, monkeypatch, "lp_vita_dlg3")

    d = tmp_path / ".config" / "Vita3K"
    d.mkdir(parents=True)
    (d / "config.yml").write_text(
        "show-welcome: true\n"
        "backend-renderer: Vulkan\n", encoding="utf-8")

    geaendert, meldung = lp.vita3k_dialoge()
    text = (d / "config.yml").read_text(encoding="utf-8")
    assert "check-for-updates-mode" not in text, "der fehlende Schluessel wurde erfunden"
    assert "check-for-updates-mode" in meldung, meldung
    assert geaendert, meldung
    assert "show-welcome: false" in text, text


def test_vita3k_dialogs_leave_a_value_that_already_fits(tmp_path, monkeypatch):
    """Gesetzt wird nach dem WERT, nicht nach dem Vorhandensein des Schluessels. (#488)"""
    lp = _lp_mit_config(tmp_path, monkeypatch, "lp_vita_dlg4")

    d = tmp_path / ".config" / "Vita3K"
    d.mkdir(parents=True)
    (d / "config.yml").write_text(
        "show-welcome: false\n"
        "check-for-updates-mode: 0\n", encoding="utf-8")
    vorher = (d / "config.yml").stat().st_mtime_ns

    geaendert, meldung = lp.vita3k_dialoge()
    assert geaendert is False, meldung
    assert (d / "config.yml").stat().st_mtime_ns == vorher, "die Datei wurde neu geschrieben"


def test_the_agent_takes_the_vita_dialogs_away_before_the_launch(tmp_path):
    """Der Agent ruft den Schritt AUF, sonst steht er ungenutzt in der Datei. (#488)

    Gemessen wird die Aufrufliste des Startprofils, nicht sein Programmtext: ein Schritt,
    den niemand aufruft, ist genau der Fehler „ausgeliefert und wirkungslos".
    Und er muss VOR dem Start liegen — danach liest Vita3K seine Konfiguration nicht mehr.
    """
    roms, pref = _vita_bibliothek(tmp_path)
    befehl, datei = _mitschrift_emulator(tmp_path)
    mitschrift = tmp_path / "profil.log"
    profil = tmp_path / "profil.py"
    profil.write_text(
        "import sys, time\n"
        f"open({str(mitschrift)!r}, 'a').write(' '.join(sys.argv[1:]) + '|'"
        " + str(time.time()) + '\\n')\n", encoding="utf-8")
    m = _agent_module(roms, EMU_VITA=f"{befehl} -r %s", VITA_PREF=str(pref),
                      PROFILE_SCRIPT=str(profil))
    ok, msg = m.launch("", "psvita", "psvita/Gravity Rush (Europe).vpk")
    assert ok, msg
    _argv(datei, m._current["proc"])
    m._stop_locked()

    zeilen = [z.split("|") for z in mitschrift.read_text().splitlines()]
    aufrufe = [z[0] for z in zeilen]
    assert "--dialogs vita3k" in aufrufe, aufrufe
    # Vor dem Start: der Fensterschritt (`--window`) laeuft als einziger danach, und er
    # ist deshalb die Messlatte fuer „davor".
    dialoge = next(float(z[1]) for z in zeilen if z[0] == "--dialogs vita3k")
    fenster = [float(z[1]) for z in zeilen if z[0].startswith("--window")]
    assert not fenster or dialoge < min(fenster), zeilen


# --- #492: zwei modale Fenster fangen jeden PSX-Start ab ----------------------------
#
# NACHGEMESSEN am laufenden Host (2026-08-13, „Sheep" (PAL), DuckStation
# 0.1-11609-ga233ec1fb), jeder Schalter mit Gegenprobe. Die Tabelle steht im Issue:
#
#   NoDesktopFile | CheckAtStartup | Fenster
#   (fehlt)       | (fehlt)        | nur "DuckStation" 500x193 — KEIN Spielfenster
#   true          | (fehlt)        | Spiel + "Automatic Updater" 651x474 mittendrauf
#   true          | false          | Spiel, kein Dialog -> Fensterschritt meldet "ok"
#   true          | true  (Gegenprobe) | "Automatic Updater" wieder da
#   (entfernt)    | false (Gegenprobe) | "DuckStation" wieder da, kein Spielfenster
#
# Der ERSTE Wert ist nicht geraten: der Dialog hat ein Kaestchen „Don't ask again", und
# nach einem Klick darauf schrieb DuckStation SELBST genau eine neue Zeile in die
# settings.ini — `[Main] NoDesktopFile = true`, sonst nichts (Schluesselmengen vorher
# und nachher verglichen). Der zweite Wert ist am Verhalten gemessen, nicht abgelesen.
#
# WARUM ZWEI SCHALTER: ohne den zweiten tauscht die Behebung nur einen Dialog gegen
# einen anderen — dieselbe Lehre wie bei Vita3K (#488).

def test_duckstation_takes_both_startup_dialogs_out_of_the_way(tmp_path, monkeypatch):
    """`NoDesktopFile` UND `CheckAtStartup` — beide, sonst nichts. (#492)"""
    lp = _lp_mit_config(tmp_path, monkeypatch, "lp_duck_dlg1")

    d = tmp_path / ".local" / "share" / "duckstation"
    d.mkdir(parents=True)
    (d / "settings.ini").write_text(
        "[Main]\n"
        "ConfirmPowerOff = true\n"
        "SetupWizardIncomplete = false\n"
        "\n"
        "[Display]\n"
        "VSync = false\n", encoding="utf-8")

    geaendert, meldung = lp.duckstation_dialoge()
    assert geaendert, meldung
    text = (d / "settings.ini").read_text(encoding="utf-8")
    assert "NoDesktopFile = true" in text, text
    assert "[AutoUpdater]" in text, text
    assert "CheckAtStartup = false" in text, text
    # Fremde Zeilen bleiben, wo sie waren.
    assert "ConfirmPowerOff = true" in text, text
    assert "VSync = false" in text, text
    assert "SetupWizardIncomplete = false" in text, "der Erstlaufdialog wurde mitverstellt"

    # Zweiter Aufruf schreibt nicht noch einmal.
    nochmal, _ = lp.duckstation_dialoge()
    assert nochmal is False


def test_duckstation_puts_nodesktopfile_into_main_not_at_the_end(tmp_path, monkeypatch):
    """`NoDesktopFile` gehoert in `[Main]`, nicht ans Dateiende. (#492)

    Eine `key = value`-Zeile hinter der letzten Sektion gehoert dieser letzten Sektion —
    nicht `[Main]`. Sie waere wirkungslos und wuerde trotzdem als Erfolg gemeldet.
    """
    lp = _lp_mit_config(tmp_path, monkeypatch, "lp_duck_dlg2")

    d = tmp_path / ".local" / "share" / "duckstation"
    d.mkdir(parents=True)
    (d / "settings.ini").write_text(
        "[Main]\n"
        "ConfirmPowerOff = true\n"
        "\n"
        "[Hacks]\n"
        "GPUFIFOSize = 16\n", encoding="utf-8")

    geaendert, meldung = lp.duckstation_dialoge()
    assert geaendert, meldung
    zeilen = (d / "settings.ini").read_text(encoding="utf-8").splitlines()
    i = zeilen.index("NoDesktopFile = true")
    davor = [z for z in zeilen[:i] if z.startswith("[")]
    assert davor[-1] == "[Main]", zeilen


def test_duckstation_dialogs_create_no_settings_file(tmp_path, monkeypatch):
    """Fehlt die `settings.ini`, wird KEINE angelegt. (#492)

    Dieselbe Regel wie bei Vita3K (#488) und beim Gamepad-Schritt: eine von uns
    erfundene Konfiguration koennte Felder vermissen lassen, die der Emulator erwartet.
    """
    lp = _lp_mit_config(tmp_path, monkeypatch, "lp_duck_dlg3")

    geaendert, meldung = lp.duckstation_dialoge()
    assert geaendert is False
    assert "noch nicht" in meldung, meldung
    assert not (tmp_path / ".local").exists(), "es wurde doch etwas angelegt"


def test_duckstation_dialogs_refuse_a_file_without_main(tmp_path, monkeypatch):
    """Ohne `[Main]` ist es nicht DuckStations settings.ini — dann lieber nichts. (#492)

    Der Gamepad-Schritt haelt sich seit jeher an dieselbe Regel. Ein Schalter, den wir in
    eine fremde Datei schreiben, wirkt nicht und meldet trotzdem Erfolg.
    """
    lp = _lp_mit_config(tmp_path, monkeypatch, "lp_duck_dlg4")

    d = tmp_path / ".local" / "share" / "duckstation"
    d.mkdir(parents=True)
    (d / "settings.ini").write_text("[Sonstwas]\nfoo = bar\n", encoding="utf-8")

    geaendert, meldung = lp.duckstation_dialoge()
    assert geaendert is False
    assert "[Main]" in meldung, meldung
    assert (d / "settings.ini").read_text(encoding="utf-8") == "[Sonstwas]\nfoo = bar\n"


def test_duckstation_dialogs_go_by_the_value_not_the_key(tmp_path, monkeypatch):
    """Gesetzt wird nach dem WERT, nicht nach dem Vorhandensein des Schluessels. (#492)

    Genau daran kam DuckStations Setup-Wizard zweimal zurueck: der Schluessel stand da,
    auf `true`, und eine Pruefung auf „steht er da?" hielt das fuer erledigt.
    """
    lp = _lp_mit_config(tmp_path, monkeypatch, "lp_duck_dlg5")

    d = tmp_path / ".local" / "share" / "duckstation"
    d.mkdir(parents=True)
    (d / "settings.ini").write_text(
        "[Main]\n"
        "NoDesktopFile = false\n"
        "\n"
        "[AutoUpdater]\n"
        "CheckAtStartup = true\n", encoding="utf-8")

    geaendert, meldung = lp.duckstation_dialoge()
    assert geaendert, meldung
    text = (d / "settings.ini").read_text(encoding="utf-8")
    assert "NoDesktopFile = true" in text, text
    assert "CheckAtStartup = false" in text, text
    # ERSETZT, nicht danebengelegt: zwei widersprechende Eintraege waeren eine Wette
    # darauf, welchen DuckStation liest.
    assert text.count("NoDesktopFile") == 1, text
    assert text.count("CheckAtStartup") == 1, text


def test_duckstation_dialogs_leave_a_file_that_already_fits(tmp_path, monkeypatch):
    """Stehen beide Werte schon richtig, wird die Datei NICHT neu geschrieben. (#492)"""
    lp = _lp_mit_config(tmp_path, monkeypatch, "lp_duck_dlg6")

    d = tmp_path / ".local" / "share" / "duckstation"
    d.mkdir(parents=True)
    (d / "settings.ini").write_text(
        "[Main]\n"
        "NoDesktopFile = true\n"
        "\n"
        "[AutoUpdater]\n"
        "CheckAtStartup = false\n", encoding="utf-8")
    vorher = (d / "settings.ini").stat().st_mtime_ns

    geaendert, meldung = lp.duckstation_dialoge()
    assert geaendert is False, meldung
    assert (d / "settings.ini").stat().st_mtime_ns == vorher, "die Datei wurde neu geschrieben"


def test_every_emulator_with_a_profile_is_reachable_from_a_platform(tmp_path):
    """Jeder Emulator im Startprofil muss an einer Plattform haengen. (#492)

    DIE RATSCHE ZUM EIGENTLICHEN FEHLER. `duckstation` stand seit #140 im Startprofil —
    mit Gamepad-Belegung und Erstlaufdialog — und `psx` fehlte in der Zuordnung des
    Agenten. Das Profil wurde bei einem PSX-Start also NIE angewandt; was auf dem Host
    stand, stand dort von Hand. Aufgefallen ist es erst, als DuckStation einen neuen
    Dialog aufmachte, den niemand wegraeumte.

    Gemessen wird die Erreichbarkeit, nicht der Programmtext: ein Profil, das keine
    Plattform aufruft, ist ausgeliefert und wirkungslos.
    """
    import importlib.util
    pfad = os.path.join(REPO, "contrib/streaming-host/launch-profile.py")
    spec = importlib.util.spec_from_file_location("lp_erreichbar", pfad)
    lp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lp)

    m = _agent_module(str(tmp_path))
    erreichbar = set(m.PROFILE_EMU.values())
    fehlend = sorted(set(lp.PROFILE) - erreichbar)
    assert not fehlend, f"Profil vorhanden, aber keine Plattform ruft es auf: {fehlend}"


def test_the_agent_takes_the_duckstation_dialogs_away_before_the_launch(tmp_path):
    """Der Agent ruft den Schritt AUF, sonst steht er ungenutzt in der Datei. (#492)

    Gemessen wird die Aufrufliste des Startprofils, nicht sein Programmtext: ein Schritt,
    den niemand aufruft, ist genau der Fehler „ausgeliefert und wirkungslos". Und er muss
    VOR dem Start liegen — danach liest DuckStation seine settings.ini nicht mehr.
    """
    roms = tmp_path / "roms" / "psx"
    roms.mkdir(parents=True)
    (roms / "Sheep.cue").write_text("FILE \"Sheep.bin\" BINARY\n", encoding="utf-8")
    (roms / "Sheep.bin").write_bytes(b"\0" * 16)
    befehl, datei = _mitschrift_emulator(tmp_path)
    mitschrift = tmp_path / "profil.log"
    profil = tmp_path / "profil.py"
    profil.write_text(
        "import sys, time\n"
        f"open({str(mitschrift)!r}, 'a').write(' '.join(sys.argv[1:]) + '|'"
        " + str(time.time()) + '\\n')\n", encoding="utf-8")
    m = _agent_module(str(tmp_path / "roms"), EMU_PSX=f"{befehl} -batch %s",
                      PROFILE_SCRIPT=str(profil))
    ok, msg = m.launch("", "psx", "psx/Sheep.cue")
    assert ok, msg
    _argv(datei, m._current["proc"])
    m._stop_locked()

    zeilen = [z.split("|") for z in mitschrift.read_text().splitlines()]
    aufrufe = [z[0] for z in zeilen]
    assert "--dialogs duckstation" in aufrufe, aufrufe
    dialoge = next(float(z[1]) for z in zeilen if z[0] == "--dialogs duckstation")
    fenster = [float(z[1]) for z in zeilen if z[0].startswith("--window")]
    assert not fenster or dialoge < min(fenster), zeilen


def test_every_pup_entry_declares_where_it_ends_up():
    """Wer eine `.PUP` erwartet, MUSS eine Ablage angeben. (#479)

    EINE REGEL STATT EINES EINZELFALLS. Eine PUP ist ein Update-Paket: Sie wird in den
    Emulator eingespielt und nie an Ort und Stelle benutzt. Fehlt die Ablage, greift im
    Skript der Zweig

        # Eingespielt? Ohne Ablage im Katalog ist die Frage gegenstandslos (true).

    und der Status meldet GRUEN fuer eine Firmware, die der Emulator gar nicht hat. Genau
    so stand `psvita` monatelang auf `installed: true`, waehrend Vita3Ks `vs0`, `os0` und
    `sa0` LEER waren — 133 MB bereitgelegt, null eingespielt. Aufgefallen erst beim
    Startversuch, an Vita3Ks „Welcome"-Fenster.

    Fuer psx, ps2, dreamcast, xbox, 3ds, switch und wiiu ist die Vorgabe richtig: Dort IST
    die Firmware die Datei im Verzeichnis, es gibt keinen zweiten Schritt. Deshalb haengt
    diese Pruefung an der PUP und nicht an einer Plattformliste — die naechste Plattform
    mit Update-Paket ist damit von selbst mitgeprueft.
    """
    pfad = os.path.join(REPO, "contrib/streaming-host/init/25-firmware")
    text = open(pfad, encoding="utf-8").read()
    tabelle = re.search(r"KATALOG=\((.*?)\n\)", text, re.S).group(1)
    ohne = []
    for zeile in tabelle.strip().splitlines():
        zeile = zeile.strip()
        if not zeile.startswith('"'):
            continue
        felder = zeile.strip('"').split("|")
        if len(felder) < 5 or ".PUP" not in felder[4].upper():
            continue
        ablage = felder[6] if len(felder) > 6 else ""
        if not ablage.strip():
            ohne.append(felder[0])
    assert not ohne, (
        f"diese Eintraege erwarten eine .PUP ohne Ablage: {ohne} — ihr Status meldet "
        "'eingespielt', ohne das je geprueft zu haben")


def test_no_desktop_entry_runs_a_bare_apprun():
    """Kein Desktop-Eintrag startet ein nacktes `AppRun`. (#482)

    Ein entpacktes AppImage laeuft NUR mit gesetztem `$APPIMAGE`; sonst endet es mit
    Exit 0 und ohne jede Ausgabe. Alle elf Eintraege auf dem Host waren deshalb tot — ein
    Klick tat buchstaeblich nichts, und nirgends erschien ein Fehler.

    Aufgefallen ist es erst, als die Vita-Firmware von Hand eingespielt werden musste: Der
    Desktop ist der einzige Weg zur eigenen Oberflaeche eines Emulators, und einige
    Schritte gibt es nur dort.

    Geprueft wird die EIGENSCHAFT, nicht die Schreibweise: Wer `AppRun` startet, muss
    vorher `APPIMAGE` setzen. Der Eintrag fuer ein apt-Paket (`/usr/games/...`) braucht das
    nicht und bleibt unberuehrt.
    """
    pfad = os.path.join(REPO, "contrib/streaming-host/init/20-emulators")
    text = open(pfad, encoding="utf-8").read()
    aufrufe = [z.strip() for z in text.splitlines()
               if re.search(r"^\s*(command -v .*&& )?desktop ", z) and not z.strip().startswith("#")]
    assert aufrufe, "keine desktop-Aufrufe gefunden — sucht der Test noch das Richtige?"
    schlecht = [z for z in aufrufe if "AppRun" in z and "apprun_befehl" not in z]
    assert not schlecht, (
        "diese Eintraege starten ein nacktes AppRun und tun beim Klick nichts: " + str(schlecht))


def test_the_vita_entry_checks_both_firmware_parts():
    """Vita3K braucht Firmware UND Font-Paket — der Status muss beide sehen. (#484)

    Nach dem Einspielen der PUP meldete Romseerr `installed`, waehrend Vita3K selbst sagte:

        Firmware is not fully installed.

    Gemessen: `vs0` 1473 Dateien, `os0` 69 — und `sa0` LEER. Das Font-Paket landet in `sa0`
    und ist ein eigener Schritt (`Download Firmware Font Package`). Ein Teil von zwei ist
    nicht „eingespielt", sondern halb, und halb ist hier unbrauchbar.

    Geprueft wird die Eigenschaft: Der psvita-Eintrag nennt MEHRERE Ablagen, und `sa0`
    gehoert dazu. Ohne diese Pruefung waere die Rueckkehr zu einer einzigen Ablage
    unauffaellig — der Status stuende wieder gruen, ohne etwas geprueft zu haben.
    """
    pfad = os.path.join(REPO, "contrib/streaming-host/init/25-firmware")
    text = open(pfad, encoding="utf-8").read()
    tabelle = re.search(r"KATALOG=\((.*?)\n\)", text, re.S).group(1)
    zeile = [z.strip().strip('"') for z in tabelle.splitlines()
             if z.strip().startswith('"psvita|')]
    assert zeile, "kein psvita-Eintrag im Katalog"
    ablagen = [a for a in zeile[0].split("|")[6].split(";") if a.strip()]
    assert len(ablagen) >= 2, (
        f"psvita nennt nur {len(ablagen)} Ablage(n) — Firmware und Font-Paket sind zwei "
        f"Schritte: {ablagen}")
    assert any(a.rstrip('/').endswith("sa0") for a in ablagen), (
        f"das Font-Paket landet in `sa0`, das steht nicht in den Ablagen: {ablagen}")


def test_a_vita_title_is_launched_by_its_title_id(tmp_path):
    """Vita3K bekommt die Kennung aus `param.sfo`, nicht den Pfad. (#481)

    GEMESSEN am laufenden Host, bevor etwas geaendert wurde. Die Hilfe des Emulators
    sagt, was `-r` will:

        -r, --installed-path TEXT:{PCSF00024}   Path to the installed app to run

    Die geschweifte Menge ist die Liste der INSTALLIERTEN Titel — `-r` nimmt eine
    Kennung, keinen Pfad. Mit dem Pfad (als EIN argv-Element, ohne Shell):

        CLI parsing error: --installed-path: /roms/psvita/Gravity not in {PCSF00024}
        [E] [main]: Failed to initialise config          (Exit 4)

    EN: `-r` takes an installed title id, not a path; the id lives in
    `sce_sys/param.sfo`. Measured on the running host before the change.
    """
    roms, pref = _vita_bibliothek(tmp_path)
    befehl, datei = _mitschrift_emulator(tmp_path)
    m = _agent_module(roms, EMU_VITA=f"{befehl} -r %s", VITA_PREF=str(pref))
    ok, msg = m.launch("", "psvita", "psvita/Gravity Rush (Europe).vpk")
    assert ok, msg
    argumente = _argv(datei, m._current["proc"])
    m._stop_locked()
    assert argumente == ["-r", "PCSF00024"], argumente
    # Der Pfad darf NIRGENDS in der Argumentliste stehen — auch nicht zusaetzlich.
    assert not any("Gravity Rush" in a for a in argumente), argumente


def test_the_vita_title_id_comes_from_param_sfo_not_from_the_folder_name(tmp_path):
    """Die Kennung wird gelesen, nicht aus dem Ordnernamen geraten. (#481)

    Der Ordner heisst hier `PCSF99999 Gravity Rush` und die Datei sagt `PCSF00024` —
    wer den Namen nimmt, faellt darauf herein. Auf dem Host ist der Unterschied real:
    der Ordner heisst `Gravity Rush (Europe).vpk`, installiert ist `PCSF00024`.
    """
    roms, pref = _vita_bibliothek(tmp_path, ordnername="PCSF99999 Gravity Rush")
    befehl, datei = _mitschrift_emulator(tmp_path)
    m = _agent_module(roms, EMU_VITA=f"{befehl} -r %s", VITA_PREF=str(pref))
    ok, msg = m.launch("", "psvita", "psvita/PCSF99999 Gravity Rush")
    assert ok, msg
    argumente = _argv(datei, m._current["proc"])
    m._stop_locked()
    assert argumente == ["-r", "PCSF00024"], argumente


def test_a_vita_title_that_is_not_installed_is_refused_with_its_id(tmp_path):
    """Nicht installiert heisst absagen — nicht eine leere Oberflaeche oeffnen. (#481)

    Ohne `-r` oeffnet Vita3K seine Titelliste, und der Stream zeigt einen Emulator statt
    eines Spiels: ein Start, der GELINGT und trotzdem nichts spielt. Die Absage nennt die
    Kennung, weil man ohne sie nicht nachsehen kann, was fehlt.
    """
    roms, pref = _vita_bibliothek(tmp_path, installiert=())
    befehl, datei = _mitschrift_emulator(tmp_path)
    m = _agent_module(roms, EMU_VITA=f"{befehl} -r %s", VITA_PREF=str(pref))
    ok, msg = m.launch("", "psvita", "psvita/Gravity Rush (Europe).vpk")
    assert not ok, "ein nicht installierter Titel wurde gestartet"
    assert "PCSF00024" in msg, msg
    assert "nicht installiert" in msg and "not installed" in msg, msg
    assert not datei.exists(), "der Emulator wurde trotz Absage gestartet"


def test_the_vita_title_id_is_taken_from_the_listing_not_glued_to_a_path(tmp_path):
    """Die Kennung wird im Listing GESUCHT, nicht an einen Pfad geheftet. (#481)

    Sie stammt aus einer Datei der Bibliothek und ist damit eine Eingabe von aussen —
    dieselbe Ueberlegung wie bei `_bibliothekspfad`. Wer sie mit `os.path.join` an
    `ux0/app` klebt, prueft mit `isdir` einen Pfad, den die Eingabe mitgebaut hat.
    """
    roms, pref = _vita_bibliothek(tmp_path, titel_id="../app/PCSF00024")
    m = _agent_module(roms, EMU_VITA="/bin/true -r %s", VITA_PREF=str(pref))
    kennung, fehler = m.vita_startwert(str(roms / "psvita" / "Gravity Rush (Europe).vpk"))
    assert not kennung and fehler, (kennung, fehler)

    # Und ohne param.sfo gibt es nichts zu raten.
    ohne = roms / "psvita" / "Kein Titel"
    ohne.mkdir()
    kennung, fehler = m.vita_startwert(str(ohne))
    assert not kennung and "param.sfo" in fehler, (kennung, fehler)


def test_other_platforms_still_get_the_path(tmp_path):
    """Gegenprobe: nur PS Vita bekommt eine Kennung, alle anderen weiter den Pfad.

    Diese Pruefung war vor der Aenderung gruen und muss es bleiben — sie faengt den Fall,
    dass die Vita-Sonderbehandlung auf andere Plattformen ueberlaeuft. Ein PS3-Titel ist
    ebenfalls ein ORDNER, geht also durch dieselbe Stelle.
    """
    roms = tmp_path / "roms"
    spiel = roms / "ps3" / "Ein Spiel" / "PS3_GAME" / "USRDIR"
    spiel.mkdir(parents=True)
    (spiel / "EBOOT.BIN").write_bytes(b"x")
    befehl, datei = _mitschrift_emulator(tmp_path, "rpcs3.sh")
    m = _agent_module(roms, EMU_PS3=f"{befehl} --no-gui %s")
    ok, msg = m.launch("", "ps3", "ps3/Ein Spiel")
    assert ok, msg
    argumente = _argv(datei, m._current["proc"])
    m._stop_locked()
    assert argumente[0] == "--no-gui" and argumente[1].endswith("EBOOT.BIN"), argumente


def test_the_emulator_is_launched_in_its_own_process_group(tmp_path):
    """Jeder Start bekommt eine EIGENE Sitzung. (#489)

    WARUM DAS DIE ERSTE PRUEFUNG IST — am laufenden Host gemessen, und das Issue sagt es
    nicht: Agent und Emulator standen in DERSELBEN Prozessgruppe.

        1414  1414  1414  python3 /opt/stream-agent.py
        11616 1414  1414  /bin/sh …/AppRun.wrapped -r PCSF00024
        11634 11616 1414  …/usr/bin/Vita3K -r PCSF00024

    Ein `killpg` auf diese Gruppe haette den DIENST SELBST beendet. `start_new_session`
    ist deshalb nicht Beiwerk der Behebung, sondern ihre Voraussetzung.

    EN: measured on the host, agent and emulator shared process group 1414 — a killpg
    would have taken down the service itself. The new session is what makes it safe.
    """
    (tmp_path / "ps2").mkdir()
    (tmp_path / "ps2" / "spiel.iso").write_bytes(b"x")
    befehl, _marke = _wrapper_emulator(tmp_path, "ps2")
    m = _agent_module(tmp_path, EMU_PS2=f"{befehl} %s")
    ok, msg = m.launch("", "ps2", "ps2/spiel.iso")
    assert ok, msg
    try:
        pid = m._current["proc"].pid
        assert os.getpgid(pid) == pid, (
            "der Emulator steht in der Gruppe des Agenten — ein killpg darauf beendet "
            f"den Dienst selbst (pgid {os.getpgid(pid)}, pid {pid})")
    finally:
        m._stop_locked()


def test_stop_also_ends_the_emulator_the_wrapper_started(tmp_path):
    """`/stop` beendet den ganzen Baum, nicht nur den verfolgten Prozess. (#489)

    GEMESSEN am laufenden Host, vor der Aenderung — `/stop` meldete `{"ok": true}` und
    `/status` sagte `running: false`, waehrend der Emulator weiterlief:

        11634  1  Sl  01:15  /config/emulators/vita3k/usr/bin/Vita3K -r PCSF00024
                ^ PPid 1: verwaist

    Der Dienst haelt sich fuer einsitzig, und der naechste Start laeuft gegen einen
    Emulator, der noch die GPU haelt. Aufgeraeumt werden musste jedes Mal von Hand.

    Der Weg ueber die PROZESSGRUPPE statt ueber die Programmdatei ist Absicht: er ist
    emulatorunabhaengig und trifft auch den naechsten Wrapper, den `linuxdeploy` erzeugt.

    EN: /stop reported success while the emulator kept running, orphaned to PPid 1.
    """
    (tmp_path / "ps2").mkdir()
    (tmp_path / "ps2" / "spiel.iso").write_bytes(b"x")
    befehl, marke = _wrapper_emulator(tmp_path, "ps2")
    m = _agent_module(tmp_path, EMU_PS2=f"{befehl} %s")
    ok, msg = m.launch("", "ps2", "ps2/spiel.iso")
    assert ok, msg
    for _ in range(100):
        if marke.exists():
            break
        time.sleep(0.1)
    assert marke.exists(), "der Ersatz-Emulator ist gar nicht angelaufen"
    enkel = int(marke.read_text())
    assert _pid_lebt(enkel)
    m._stop_locked()
    assert not _pid_lebt(enkel), (
        f"der Emulator (PID {enkel}) laeuft nach /stop weiter — genau der verwaiste "
        "Vita3K-Prozess aus #489")


def test_stop_refuses_to_signal_a_group_that_is_not_the_childs_own(tmp_path, monkeypatch):
    """Die Gruppe wird nur benutzt, wenn sie dem Kind ALLEIN gehoert. (#489)

    Der Schutz gegen genau den Fehler, den die Messung nahegelegt hat: eine Gruppe, in
    der auch der Agent steht. Faellt `start_new_session` je aus — altes Python, ein
    Prozess, der die Gruppe selbst wechselt —, darf daraus kein `killpg` auf den Dienst
    werden. Dann wird nur der verfolgte Prozess beendet; das ist der Zustand VOR dieser
    Aenderung und damit nicht schlechter als vorher.

    ANDERS ALS DIE DREI DAVOR war diese Pruefung schon VOR der Aenderung gruen — es gab
    noch gar kein `killpg`. Sie ist eine Gegenprobe, keine Behebung: sie haelt fest, dass
    die neue Faehigkeit nicht auf eine fremde Gruppe losgeht.

    EN: the group is only used when pgid == pid. Otherwise fall back to signalling the
    tracked process alone — no worse than before, and never the agent's own group. Unlike
    the three above, this one was already green: it is a guard, not a fix.
    """
    (tmp_path / "ps2").mkdir()
    (tmp_path / "ps2" / "spiel.iso").write_bytes(b"x")
    befehl, marke = _wrapper_emulator(tmp_path, "ps2")
    m = _agent_module(tmp_path, EMU_PS2=f"{befehl} %s")
    ok, msg = m.launch("", "ps2", "ps2/spiel.iso")
    assert ok, msg
    for _ in range(100):
        if marke.exists():
            break
        time.sleep(0.1)
    enkel = int(marke.read_text())
    gesendet = []
    monkeypatch.setattr(m.os, "getpgid", lambda _pid: 1)      # fremde Gruppe
    monkeypatch.setattr(m.os, "killpg",
                        lambda gid, sig: gesendet.append((gid, sig)))
    try:
        m._stop_locked()
        assert not gesendet, f"an eine fremde Prozessgruppe gesendet: {gesendet}"
    finally:
        try:
            os.kill(enkel, 9)
        except ProcessLookupError:
            pass


def test_the_window_check_looks_at_the_children_too(tmp_path):
    """Die Fensterpruefung sucht auch bei den Kindprozessen. (#489)

    GEMESSEN am laufenden Host, bei laufendem Spiel — dieselbe Sitzung, zwei PIDs:

        xdotool search --pid 11616   (Wrapper)   -> nichts
        xdotool search --pid 11634   (Vita3K)    -> 46137351 [Vita3K v0.2.1 …]
                                                   46137358 [GRAVITY RUSH™ (PCSF00024)]

    `/status` meldete dazu `"window": "kein-fenster"` — eine FALSCHE Auskunft ueber
    einen Titel, der sichtbar lief. Der Befund war nicht "nichts zu sehen", sondern
    "an der falschen PID nachgesehen".
    """
    m = _profil_modul(tmp_path)
    kind = tmp_path / "kind.sh"
    kind.write_text("#!/bin/sh\nwhile :; do sleep 0.2; done\n")
    kind.chmod(0o755)
    eltern = subprocess.Popen(["/bin/sh", "-c", f'"{kind}" & wait'])
    try:
        for _ in range(100):
            gefunden = m.nachkommen(eltern.pid)
            if gefunden:
                break
            time.sleep(0.1)
        assert gefunden, "der Kindprozess wurde nicht gefunden"
        gefragt = []
        m_x = m._x

        def mitschrift(*args, **kw):
            gefragt.append(args)
            return m_x("true")            # nichts finden, nur aufschreiben
        m.sichtbare_fenster.__globals__["_x"] = mitschrift
        try:
            m.sichtbare_fenster(eltern.pid)
        finally:
            m.sichtbare_fenster.__globals__["_x"] = m_x
        gefragte_pids = {a[-1] for a in gefragt if a[0] == "xdotool"}
        assert str(eltern.pid) in gefragte_pids, gefragt
        for enkel in gefunden:
            assert str(enkel) in gefragte_pids, (
                f"das Kind {enkel} wurde nicht nach Fenstern gefragt — genau der Fall, "
                f"der bei Vita3K `kein-fenster` gemeldet hat: {gefragt}")
    finally:
        eltern.kill()
        eltern.wait()


# ---------------------------------------------------------------------------
# #502: Wii U — die Auskunft sagte startbar, der Start-Dienst fand nichts Startbares.
# Alle Aufbauten hier sind AM EINZIGEN WII-U-TITEL DES BESTANDS gemessen (2026-08-13).
# ---------------------------------------------------------------------------

def _wiiu_titel(wurzel, name, title_id_app, title_id_meta=None, rpx=("Kinopio.rpx",)):
    """Einen Wii-U-Titelordner nachbauen: code/ content/ meta/.

    `title_id_app` und `title_id_meta` sind getrennt, weil sie sich im Bestand
    WIDERSPRECHEN — genau daran hing #502.
    """
    t = wurzel / name
    (t / "code").mkdir(parents=True)
    (t / "content").mkdir()
    (t / "meta").mkdir()
    for r in rpx:
        (t / "code" / r).write_bytes(b"\x7fELF")
    (t / "code" / "app.xml").write_text(
        '<?xml version="1.0"?>\n<app>\n'
        f'  <title_id type="hexBinary" length="8">{title_id_app}</title_id>\n'
        '</app>\n', encoding="utf-8")
    (t / "meta" / "meta.xml").write_text(
        '<?xml version="1.0"?>\n<menu>\n'
        f'  <title_id type="hexBinary" length="8">{title_id_meta or title_id_app}</title_id>\n'
        '</menu>\n', encoding="utf-8")
    return t


def test_the_launcher_resolves_a_wiiu_title_to_its_rpx(tmp_path):
    """Ein Wii-U-Ordner muss eine Startdatei ergeben. (#502)

    GEMESSEN am laufenden Dienst, vor der Reparatur:

        /api/stream  Captain Toad / wiiu -> streamable: true, path: <Ordner>
        _bootdatei(<Ordner>, "wiiu")     -> ''   (= 'Ordner ohne startbaren Inhalt')

    `BOOTPFADE` kannte nur `ps3`, und ein Wii-U-Titel traegt oben `code/`, `content/`,
    `meta/` — keine Datei mit einer der bekannten Endungen. Dasselbe Muster wie #150
    und #477: eine Seite sagt ja, die andere nein.

    Der Name der `.rpx` ist je Titel anders, ein fester Pfad genuegt also nicht.

    DER ORDNERNAME TRAEGT ABSICHTLICH ECKIGE KLAMMERN. Die erste Fassung dieser
    Reparatur benutzte `glob`, und `[AKBP01]` ist dort eine ZEICHENKLASSE, kein Text:
    Das Muster passte auf nichts und lieferte wieder '' — derselbe Fehler mit neuer
    Ursache. Aufgefallen ist das nur, weil hier der ECHTE Ordnername steht. Wer ihn zu
    `Captain Toad` vereinfacht, nimmt die Probe heraus, ohne dass ein Test rot wird.

    EN: a Wii U folder must resolve to a boot file; the table only knew ps3 and a Wii U
    title carries no known boot extension at its top level. The brackets in the folder
    name are deliberate — the first version of this fix used glob, where `[AKBP01]` is a
    character class, and it silently matched nothing.
    """
    m = _agent_module(tmp_path)
    t = _wiiu_titel(tmp_path / "wiiu", "Captain Toad [AKBP01]", "0005000010180700")
    assert m._bootdatei(str(t), "wiiu") == str(t / "code" / "Kinopio.rpx")


def test_the_launcher_refuses_rather_than_guessing_between_two_rpx(tmp_path):
    """Mehrere `.rpx` -> Absage, nicht Raten. (#502)

    Im Bestand liegt eine `red-pro2.rpx` herum (#318). Ein zufaellig gewaehltes
    Programm zu starten waere schlimmer als eine klare Absage: Der Stream ginge auf,
    irgendetwas liefe, und niemand wuesste warum es nicht das Spiel ist.

    DIESER TEST UNTERSCHEIDET NICHT — er ist eine RATSCHE. Am Stand vor #502 ist er
    ebenfalls gruen, weil `_bootdatei` fuer Wii U damals immer '' lieferte, also auch
    hier. Er haelt fest, dass die neue Aufloesung nicht uebereifrig wird; als Beleg,
    dass die Reparatur wirkt, taugt er nicht. Das tun die drei anderen.

    EN: several matches are refused rather than guessed at. This test does NOT
    discriminate — it is a ratchet: it passes against the pre-#502 code too, where the
    resolution returned '' for everything. It guards against over-eagerness, it does not
    prove the fix.
    """
    m = _agent_module(tmp_path)
    t = _wiiu_titel(tmp_path / "wiiu", "Zweideutig", "0005000010180700",
                    rpx=("Kinopio.rpx", "red-pro2.rpx"))
    assert m._bootdatei(str(t), "wiiu") == ""


def test_a_wiiu_update_is_refused_by_name_not_by_cemus_error(tmp_path):
    """Ein Update wird abgesagt, bevor Cemu ratlos wird. (#502)

    AM BESTAND GEMESSEN — die beiden Beschreibungsdateien widersprechen sich:

        meta/meta.xml   title_id = 0005000010180700   (Basisspiel)
        code/app.xml    title_id = 0005000E10180700   (Update)

    Cemu liest `app.xml`, sieht `0005000E` und antwortet:

        Unable to mount title.
        File which failed to load: …/code/Kinopio.rpx

    Diese Meldung nennt eine Datei und verschweigt die Ursache — wer sie liest, sucht
    am Pfad, und dort ist nichts. Nachgemessen: Ordner UND `.rpx` scheitern identisch.

    EN: refused by name before Cemu answers with a message that names a file and hides
    the cause.
    """
    m = _agent_module(tmp_path)
    t = _wiiu_titel(tmp_path / "wiiu", "Captain Toad [AKBP01]",
                    title_id_app="0005000E10180700",     # Update
                    title_id_meta="0005000010180700")    # behauptet Basisspiel
    grund = m._wiiu_art(str(t))
    assert grund, "das Update ging durch"
    assert "0005000E10180700" in grund, grund
    assert "UPDATE" in grund, grund


def test_a_wiiu_base_game_and_an_unreadable_one_both_pass(tmp_path):
    """Basisspiel durch — und im Zweifel ebenfalls. (#502, wie #427/#299)

    Fehlt `app.xml` oder steht dort keine lesbare Kennung, geht der Titel durch. Eine
    falsche Absage kostet mehr als ein Fehlversuch; dieselbe Regel wie bei Switch und
    3DS. Ohne diesen Test waere eine Pruefung, die IMMER absagt, ebenfalls gruen.
    """
    m = _agent_module(tmp_path)
    basis = _wiiu_titel(tmp_path / "wiiu", "Echtes Spiel", "0005000010180700")
    assert m._wiiu_art(str(basis)) == ""

    ohne = tmp_path / "wiiu" / "Ohne app.xml"
    (ohne / "code").mkdir(parents=True)
    (ohne / "code" / "Spiel.rpx").write_bytes(b"\x7fELF")
    assert m._wiiu_art(str(ohne)) == ""


def test_a_wiiu_dlc_and_a_system_title_are_refused_too(tmp_path):
    """`0005000C` ist DLC, `0005001B` ein Systemtitel — beides kein Spiel. (#502)"""
    m = _agent_module(tmp_path)
    for kennung, wort in (("0005000C10180700", "DLC"),
                          ("0005001B10180700", "SYSTEMTITEL")):
        t = _wiiu_titel(tmp_path / "wiiu", f"T{kennung}", kennung)
        grund = m._wiiu_art(str(t))
        assert grund and wort in grund, (kennung, grund)


# ---------------------------------------------------------------------------
# #527: Ein Ruckeln wird dem Emulator angelastet, weil niemand festhaelt, was der
# Host sonst tat.
# ---------------------------------------------------------------------------

def test_the_host_load_is_recorded_with_the_launch(tmp_path):
    """Was der Host beim Start sonst tat, wird mitgeschrieben. (#527)

    AM 2026-08-13 GEMESSEN, und die naheliegende Deutung war falsch:

        Nutzer: „es ruckelt extrem und laeuft wohl auf der CPU statt auf der GPU"

        GL_RENDERER  Mesa Intel(R) Arc(tm) A310 Graphics   <- sehr wohl auf der GPU
        RCS (3D)     0,00 %                                <- die noetige Einheit: FREI
        tdarr-ffmpeg 759 %  tdarr-ffmpeg 733 %  xemu 201 %
        28 Kerne, Load 45,9

    Zwei Umrechnungen belegten rund 15 Kerne. Der Emulator bekam die Schuld fuer eine
    Last, die von woanders kam — und die Antwort kostete eine halbe Stunde Messen.

    Der Zustand laesst sich hinterher NICHT rekonstruieren; deshalb wird er beim Start
    genommen. Bewertet wird nichts: ob eine Last zu hoch ist, haengt vom Titel ab.

    EN: records what else the host was doing at launch, because that state is gone by
    the time anyone asks — and the obvious reading was exactly wrong once.
    """
    m = _agent_module(tmp_path)
    l = m.hostlast()
    assert l, "keine Angabe zur Hostlast"
    assert isinstance(l.get("load"), list) and len(l["load"]) == 3, l
    assert l.get("cpus", 0) >= 1, l
    assert isinstance(l.get("top"), list), l
    for eintrag in l["top"]:
        assert "cpu" in eintrag and "name" in eintrag, eintrag


def test_the_load_recording_does_not_see_itself(tmp_path):
    """Die Messung darf nicht in ihrem eigenen Ergebnis stehen. (#529)

    `ps` rechnet %CPU als Rechenzeit ueber die LEBENSDAUER. Ein Prozess, der
    Millisekunden alt ist, steht damit bei nahezu 100 % — direkt nach dem Ausrollen
    von #527 gemessen:

        100,0 %  ps            <- die Messung
         73,3 %  python3       <- der Messende
         25,0 %  xfce4-panel

    Die Liste hat FUENF Plaetze. Zwei an die Messung zu verlieren heisst, dass zwei
    echte Verbraucher aus der Aufzeichnung fallen — und die gibt es nur, um genau die
    zu nennen. Im Fall, der #527 ausgeloest hat, waren die Antwort zwei `tdarr-ffmpeg`
    mit 759 % und 733 %.

    Dieselbe Falle wie bei `pgrep`/`pkill`, die die eigene Sitzung treffen.

    EN: ps computes %CPU over lifetime, so the measuring call scores ~100 % and takes a
    slot the record exists to give to real consumers.
    """
    m = _agent_module(tmp_path)

    # DIE AUSGABE WIRD VORGEGEBEN, NICHT ERHOFFT. Ein erster Versuch las einfach die
    # echte Prozessliste — und bestand auch gegen den FEHLERHAFTEN Stand, weil `ps` auf
    # dem Testlaeufer zufaellig nicht unter den ersten fuenf stand. Eine kurze Probe
    # beweist keine Abwesenheit.
    eigen = os.getpid()
    # Dieselben Prozesse, in JEDEM Spaltenformat das gefragt sein kann. Ein erster
    # Versuch gab starr vier Spalten zurueck — gegen den alten Stand, der nur `pcpu,comm`
    # abfragt, scheiterte der Test dann an der ZERLEGUNG statt am fehlenden Filter, und
    # eine Meldung ueber die falsche Ursache schickt den naechsten Leser ans falsche Ende.
    prozesse = [(90001, eigen, 100.0, "ps"),          # die Messung selbst
                (eigen, 1, 73.3, "python3"),          # der Messende
                (90003, 1, 759.0, "tdarr-ffmpeg"),
                (90004, 1, 733.0, "tdarr-ffmpeg"),
                (90005, 1, 201.0, "AppRun"),
                (90006, 1, 25.0, "xfce4-panel"),
                (90007, 1, 17.0, "xfdesktop")]

    def _fake(args, **kw):
        spalten = args[args.index("-eo") + 1].split(",")
        kopf = " ".join(x.upper() for x in spalten)
        zeilen = [kopf]
        for pid, ppid, pcpu, comm in prozesse:
            werte = {"pid": pid, "ppid": ppid, "pcpu": pcpu, "comm": comm}
            zeilen.append(" ".join(str(werte[x]) for x in spalten))
        class _Lauf:
            stdout = "\n".join(zeilen) + "\n"
        return _Lauf()

    monkeypatch_ziel = m.subprocess.run
    m.subprocess.run = _fake
    try:
        l = m.hostlast()
    finally:
        m.subprocess.run = monkeypatch_ziel

    namen = [t["name"] for t in l["top"]]
    assert "ps" not in namen, f"die Messung steht in ihrem eigenen Ergebnis: {namen}"
    assert "python3" not in namen, f"der Messende steht darin: {namen}"
    # Und die echten Verbraucher muessen ALLE durchkommen — der Filter darf keinen
    # Platz kosten, sonst faellt weiter unten wieder einer heraus.
    assert namen == ["tdarr-ffmpeg", "tdarr-ffmpeg", "AppRun", "xfce4-panel",
                     "xfdesktop"], namen
    assert l["top"][0]["cpu"] == 759.0, l["top"][0]


def test_the_status_reports_the_load_from_the_launch_not_from_now():
    """Gemeldet wird der Zustand BEIM START, nicht der aktuelle. (#527)

    Der Unterschied ist der ganze Zweck: Wer nachtraeglich misst, misst den falschen
    Moment — die Umrechnung, die das Ruckeln verursacht hat, kann laengst fertig sein.
    Der Wert wird deshalb einmal genommen und danach nicht mehr angefasst.
    """
    quelle = open(os.path.join(REPO, "contrib", "streaming-host", "stream-agent.py"),
                  encoding="utf-8").read()

    # 1. Genommen wird er BEIM START — dort, wo auch Plattform und Pfad gesetzt werden.
    i = quelle.index('_current["window_detail"] = ""')
    j = quelle.index("\n\n", i)
    assert 'hostlast()' in quelle[i:j], (
        "die Hostlast wird beim Start nicht genommen — nachtraeglich gemessen ist es "
        "der falsche Moment")

    # 2. Gemeldet wird das FESTGEHALTENE, nicht eine frische Messung. Stuende in der
    #    Statusantwort `hostlast()`, waere der Wert der von JETZT — und die Umrechnung,
    #    die das Ruckeln verursacht hat, laengst fertig.
    k = quelle.index('"window_detail": _current["window_detail"]')
    ende = quelle.index("}", k)
    antwort = quelle[k:ende]
    assert '_current.get("last")' in antwort, antwort[:200]
    assert "hostlast()" not in antwort, (
        "die Statusantwort misst neu statt zu berichten, was beim Start galt")
