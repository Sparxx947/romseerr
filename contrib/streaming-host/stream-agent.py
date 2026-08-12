#!/usr/bin/env python3
"""Start-Dienst für den Streaming-Host / launch agent for the streaming host (Romseerr #71).

Romseerr emuliert nichts und liefert keinen Emulator aus. Es löst einen Titel auf eine
Datei auf und bittet DIESEN Dienst, sie zu starten. Der Dienst läuft im Streaming-Container
(Selkies/KasmVNC o. ä.), sieht dessen Anzeige und dessen GPU.

Bewusst ohne Abhängigkeiten (nur Standardbibliothek), damit er in jedes Desktop-Image passt.

    python3 stream-agent.py

Konfiguration über Umgebungsvariablen:

    STREAM_AGENT_PORT   Port (Default 8901)
    STREAM_AGENT_TOKEN  gemeinsames Geheimnis; MUSS gesetzt sein
    STREAM_ROMS         Wurzel der ROM-Bibliothek, wie der Container sie sieht (Default /roms)
    EMU_PS2 EMU_GC EMU_SWITCH   Pfade zu den Emulatoren

In Romseerr eintragen unter Einstellungen → Verbindungen:

    Streaming-Host   http://<host>:3000/      (die Browser-Oberfläche)
    Start-Dienst     http://<host>:8901/launch?token=…

SICHERHEIT: Dieser Dienst startet Prozesse. Er gehört NICHT ins offene Netz.
  * Ohne gültiges Token wird jede Anfrage abgewiesen.
  * Der Pfad muss innerhalb von STREAM_ROMS liegen — nach Auflösung von Symlinks.
    Sonst wäre er ein Fernstart für beliebige Dateien.
  * Es wird nie eine Shell benutzt; die Argumentliste geht direkt an execve.
"""
import json
import os
import re
import time
import shlex
import subprocess
import sys
import threading
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("STREAM_AGENT_PORT", "8901"))
TOKEN = os.environ.get("STREAM_AGENT_TOKEN", "")
ROMS = os.path.realpath(os.environ.get("STREAM_ROMS", "/roms"))

# Plattform -> Startbefehl. %s wird durch den ROM-Pfad ersetzt.
# Plattform -> Startbefehl. Leer = nicht verfuegbar, der Aufrufer bekommt dann eine
# klare Absage statt eines Startversuchs ins Leere. Die Werte setzt init/30-agent.
EMULATORS = {
    "psx":       os.environ.get("EMU_PSX", ""),
    "ps2":       os.environ.get("EMU_PS2", ""),
    "ngc":       os.environ.get("EMU_GC", ""),
    "wii":       os.environ.get("EMU_GC", ""),
    "wiiu":      os.environ.get("EMU_WIIU", ""),
    "switch":    os.environ.get("EMU_SWITCH", ""),
    "3ds":       os.environ.get("EMU_3DS", ""),
    "dreamcast": os.environ.get("EMU_DC", ""),
    "xbox":      os.environ.get("EMU_XBOX", ""),
    "ps3":       os.environ.get("EMU_PS3", ""),
    "psvita":    os.environ.get("EMU_VITA", ""),
}

# `window` haelt fest, ob nach dem Start wirklich ein Spielfenster erschien (#288):
#   "" (leer)      noch nichts gestartet
#   "pending"      Start laeuft, das Fenster wird noch erwartet
#   "ok"           Spielfenster steht
#   "dialog"       der Emulator zeigt einen Fehlerdialog — `window_detail` ist dessen Titel
#   "kein-fenster" nichts Sichtbares entstanden
# WOZU: Der Start GELINGT auch dann, wenn der Titel scheitert — verschluesselte 3DS-ROMs,
# NKit-komprimierte Wii-ISOs. Der Nutzer sah bis dahin nur einen leeren Stream.
_current = {"proc": None, "platform": "", "path": "", "window": "", "window_detail": ""}
_lock = threading.Lock()

# Ordner-Titel -> die Datei, mit der der Emulator startet.
#
# WARUM EINE TABELLE UND KEINE SUCHE NACH "der groessten Datei": Bei einer PS3-Disc
# waere das oft ein Video oder ein Datenarchiv, nicht die EBOOT.BIN. Die Reihenfolge
# ist die Rangfolge; der erste Treffer gewinnt.
# A table, not a "largest file" heuristic: on a PS3 disc that would usually pick a
# video, not the boot binary.
BOOTPFADE = {
    "ps3": ("PS3_GAME/USRDIR/EBOOT.BIN", "USRDIR/EBOOT.BIN", "EBOOT.BIN"),
}
# Rueckfall fuer Ordner ohne bekannte Struktur: eine einzelne Abbilddatei darin ist
# eindeutig. Bei MEHREREN wird bewusst NICHT geraten — lieber eine klare Absage als
# ein zufaellig gewaehltes Spiel.
BOOT_ENDUNGEN = (".iso", ".chd", ".cue", ".gdi", ".rvz", ".wbfs", ".nsp", ".xci", ".pkg")


def _bibliothekspfad(rel):
    """Loest einen bibliotheksrelativen Pfad auf. -> absoluter Pfad oder ''.

    WARUM NICHT EINFACH os.path.join(ROMS, rel) UND HINTERHER PRUEFEN:
    Weil dabei aus der Anfrage ein Pfad GEBAUT wird und man den Ausbruch danach wieder
    einfangen muss. Das ging bisher gut (realpath + commonpath), war aber eine Zusage,
    die bei jeder Aenderung neu einzuhalten ist — und genau daran ist es beinahe
    gescheitert: die Startdatei aus einem Ordner lief anfangs an der Pruefung vorbei.
    Zudem sieht CodeQL diese Bauart grundsaetzlich als `py/path-injection`, weil ihm
    nicht beweisbar ist, dass die Pruefung greift.
    Hier wird stattdessen STUFE FUER STUFE gegen den ECHTEN Verzeichnisinhalt
    abgeglichen. Der Wert stammt damit aus dem Dateisystem, die Anfrage bestimmt nur
    noch die AUSWAHL. Ein Ausbruch ist so nicht mehr abzufangen, sondern gar nicht
    erst zu formulieren.
    Resolved by matching each step against the actual directory listing: the value
    comes from the filesystem, the request only selects. Escaping is not caught after
    the fact, it cannot be expressed.

    Symlinks werden bewusst NICHT verfolgt. Eine Bibliothek darf welche enthalten, aber
    dann zeigt der Emulator moeglicherweise auf etwas ausserhalb — und was ausserhalb
    liegt, ist hier nie startbar.
    """
    teile = [t for t in (rel or "").split("/") if t not in ("", ".")]
    if not teile or any(t == ".." for t in teile):
        return ""
    aktuell = ROMS
    for gesucht in teile:
        gefunden = ""
        try:
            for eintrag in os.listdir(aktuell):
                if eintrag == gesucht:
                    gefunden = eintrag      # aus dem Dateisystem, nicht aus der Anfrage
                    break
        except OSError:
            return ""
        if not gefunden:
            return ""
        aktuell = os.path.join(aktuell, gefunden)
        if os.path.islink(aktuell):
            return ""
    return aktuell


def _bootdatei(ordner, platform):
    """-> absoluter Pfad der Startdatei, oder '' wenn nicht eindeutig bestimmbar."""
    for rel in BOOTPFADE.get(platform, ()):
        k = os.path.join(ordner, *rel.split("/"))
        if os.path.isfile(k):
            return k
    treffer = []
    try:
        for e in sorted(os.listdir(ordner)):
            k = os.path.join(ordner, e)
            if os.path.isfile(k) and e.lower().endswith(BOOT_ENDUNGEN):
                treffer.append(k)
    except OSError:
        return ""
    return treffer[0] if len(treffer) == 1 else ""

# Emulator-Aktualisierung. Laeuft im Hintergrund, damit der Aufrufer nicht minutenlang
# auf einer HTTP-Antwort haengt — Downloads sind hier hunderte Megabyte.
# Runs in the background; downloads are hundreds of megabytes.
UPDATE_SCRIPT = os.environ.get("EMU_UPDATE_SCRIPT", "/custom-cont-init.d/20-emulators")
_update = {"running": False, "started": 0, "finished": 0, "rc": None, "log": "", "target": ""}

# Firmware und BIOS. Dasselbe Muster: die Tabelle steht im Skript, hier wird sie nur
# abgefragt. / Same pattern as the emulator catalogue: the table lives in the script.
FIRMWARE_SCRIPT = os.environ.get("FIRMWARE_SCRIPT", "/custom-cont-init.d/25-firmware")
# Controller-Belegung. Wird VOR jedem Start angewandt, nicht einmalig beim Hochfahren:
# die Emulatoren schreiben ihre Konfiguration beim Beenden zurueck, und eine einmal
# gesetzte Belegung waere danach womoeglich wieder weg.
# Applied before every launch, not once at boot: emulators rewrite their config on exit.
PROFILE_SCRIPT = os.environ.get("PROFILE_SCRIPT", "/opt/launch-profile.py")
# Plattform -> Emulator, fuer den es ein Profil gibt. Kein Eintrag = der Emulator ordnet
# ein erkanntes SDL-Pad selbst zu. / No entry = the emulator maps a detected pad itself.
# Plattform -> Emulator im Startprofil. Ohne Eintrag wird kein Profil angewandt.
PROFILE_EMU = {"ps2": "pcsx2", "ngc": "dolphin", "wii": "dolphin", "wiiu": "cemu",
               "switch": "switchemu", "3ds": "azahar", "dreamcast": "flycast",
               "xbox": "xemu", "ps3": "rpcs3", "psvita": "vita3k"}
# Grenze fuer einen Upload. Die groesste Datei, die hier real ankommt, ist Sonys
# PS3-Paket mit gut 200 MB; 512 MB lassen Luft, ohne dass jemand den Container mit
# einem Dauerstrom volllaufen lassen kann.
# Cap for uploads: Sony's PS3 package is the largest real case at ~200 MB.
MAX_UPLOAD = int(os.environ.get("FIRMWARE_MAX_BYTES", str(512 * 1024 * 1024)))
_vendor = {"running": False, "rc": None, "log": "", "target": ""}


def firmware_status():
    try:
        r = subprocess.run(["/bin/bash", FIRMWARE_SCRIPT, "--status"],
                           capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout) if r.returncode == 0 else {"ok": False, "platforms": []}
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return {"ok": False, "platforms": []}


def firmware_platforms():
    """Welche Plattformkuerzel kennt das Skript? Damit wird eine Eingabe geprueft —
    gegen die TABELLE, nicht gegen ein Muster. Ein Muster sagt nur, wie ein Name
    aussehen darf; die Tabelle sagt, welcher existiert."""
    return {p.get("platform") for p in firmware_status().get("platforms", [])}


def run_vendor(platform):
    """Herstellerbezug im Hintergrund — Sonys Paket ist ueber 200 MB."""
    _vendor.update({"running": True, "rc": None, "log": "", "target": platform})
    try:
        r = subprocess.run(["/bin/bash", FIRMWARE_SCRIPT, "--vendor", platform],
                           capture_output=True, text=True, timeout=3600)
        _vendor["rc"] = r.returncode
        _vendor["log"] = (r.stdout + r.stderr)[-8000:]
    except subprocess.TimeoutExpired:
        _vendor["rc"] = -1; _vendor["log"] = "Zeitueberschreitung / timed out"
    except OSError as e:
        _vendor["rc"] = -1
        _vendor["log"] = f"Start fehlgeschlagen / launch failed: {e.__class__.__name__}"
    finally:
        _vendor["running"] = False


def run_update():
    """Das Installationsskript erneut ausfuehren. Es ist idempotent und laedt nur,
    was sich geaendert hat — deshalb ist 'aktualisieren' dasselbe wie 'installieren'."""
    _update.update({"running": True, "started": int(time.time()),
                    "finished": 0, "rc": None, "log": ""})
    try:
        # EMU_AUTO_UPDATE erzwingen: ein ausdruecklich angestossener Lauf soll
        # aktualisieren, auch wenn der automatische Abgleich abgeschaltet ist.
        env = {**os.environ, "EMU_AUTO_UPDATE": "true"}
        r = subprocess.run(["/bin/bash", UPDATE_SCRIPT], env=env, capture_output=True,
                           text=True, timeout=3600)
        _update["rc"] = r.returncode
        _update["log"] = (r.stdout + r.stderr)[-8000:]
    except subprocess.TimeoutExpired:
        _update["rc"] = -1
        _update["log"] = "Zeitueberschreitung / timed out"
    except OSError as e:
        _update["rc"] = -1
        _update["log"] = f"Start fehlgeschlagen / launch failed: {e.__class__.__name__}"
    finally:
        _update["running"] = False
        _update["finished"] = int(time.time())


def catalogue():
    """Was ist installierbar, was ist installiert? Kommt aus dem Installationsskript
    selbst — dort steht die Tabelle, und zwei Wahrheiten waeren eine zu viel."""
    try:
        r = subprocess.run(["/bin/bash", UPDATE_SCRIPT, "--catalog"],
                           capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout) if r.returncode == 0 else []
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return []


def run_install(name):
    """Genau einen Emulator installieren. Laeuft im Hintergrund — das sind hunderte
    Megabyte, darauf soll niemand in einer HTTP-Antwort warten."""
    _update.update({"running": True, "started": int(time.time()),
                    "finished": 0, "rc": None, "log": "", "target": name})
    try:
        r = subprocess.run(["/bin/bash", UPDATE_SCRIPT, "--only", name],
                           env={**os.environ, "EMU_AUTO_UPDATE": "true"},
                           capture_output=True, text=True, timeout=3600)
        _update["rc"] = r.returncode
        _update["log"] = (r.stdout + r.stderr)[-8000:]
    except subprocess.TimeoutExpired:
        _update["rc"] = -1; _update["log"] = "Zeitueberschreitung / timed out"
    except OSError as e:
        _update["rc"] = -1
        _update["log"] = f"Start fehlgeschlagen / launch failed: {e.__class__.__name__}"
    finally:
        _update["running"] = False
        _update["finished"] = int(time.time())


def installed_emulators():
    """Was liegt da, und aus welcher Quelle? Die .url-Datei neben dem Ordner ist die
    zuletzt installierte Release-URL und damit die belastbarste Versionsangabe."""
    base = os.path.dirname(UPDATE_SCRIPT)  # nur fuer den Fall der Faelle
    emu = os.environ.get("EMU_DIR", "/config/emulators")
    out = []
    try:
        for name in sorted(os.listdir(emu)):
            # `<name>.alt` ist die aufgehobene VORIGE Fassung, aus der `can_rollback`
            # unten gespeist wird — keine eigene Installation. Sie traegt ebenfalls ein
            # AppRun und stand deshalb als eigener Emulator in der Liste, ohne Quelle
            # und ohne Version. Wer sie fuer eine Altlast haelt und aufraeumt, loescht
            # den Rueckweg. `.alt` is the kept previous build, not an installation.
            if name.endswith(".alt"):
                continue
            d = os.path.join(emu, name)
            if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "AppRun")):
                continue
            src = ""
            marker = os.path.join(emu, name + ".url")
            if os.path.exists(marker):
                try:
                    src = open(marker).read().strip()
                except OSError:
                    pass
            prev = ""
            pm = os.path.join(emu, name + ".url.alt")
            if os.path.exists(pm):
                try:
                    prev = os.path.basename(open(pm).read().strip())
                except OSError:
                    pass
            out.append({"name": name, "source": src,
                        "version": os.path.basename(src) if src else "",
                        "previous": prev,
                        "can_rollback": os.path.exists(os.path.join(emu, name + ".alt", "AppRun"))})
    except OSError:
        pass
    return out


def _stop_locked():
    p = _current["proc"]
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            p.kill()
    _current.update({"proc": None, "platform": "", "path": "",
                     "window": "", "window_detail": ""})


# Bibliothekspfade, die einzelne Emulatoren zusaetzlich brauchen (#300).
#
# xemus AppImage bringt als einziges KEINE libusb mit, und der Container hat keine —
# ohne diesen Pfad endet der Start mit `error while loading shared libraries`. Die
# Kopie liegt in /config/lib (siehe init/22-xemu-vorbereiten).
#
# Der zweite Pfad ist der Ton: ALSA laedt sein Pulse-Modul ueber `libpulse.so.0`, das
# wiederum `libpulsecommon-<version>.so` braucht. Die liegt im System, aber in einem
# UNTERORDNER, der nicht im Suchpfad steht — deshalb schlug der Ton mit
# `Couldn't open audio device` fehl, obwohl Pulse laeuft.
#
# WARUM NICHT den ganzen lib-Ordner eines anderen Emulators: genau das wurde versucht
# und ging schief. Dessen `libpulse.so.0` verdraengt die des Systems und passt nicht
# zur System-`libpulsecommon` — `undefined symbol: pa_in_valgrind`. Es wird deshalb
# genau eine Datei geliehen, nicht ein Verzeichnis.
EXTRA_LIBS = {
    "xbox": ["/config/lib", "/usr/lib/x86_64-linux-gnu/pulseaudio"],
}


def start_umgebung(platform):
    """Umgebung fuer den Emulatorstart: die eigene plus etwaige Zusatzpfade."""
    umg = dict(os.environ)
    extra = EXTRA_LIBS.get(platform)
    if extra:
        vorher = umg.get("LD_LIBRARY_PATH", "")
        umg["LD_LIBRARY_PATH"] = ":".join(extra + ([vorher] if vorher else []))
    return umg


# ------------------------------------------- 3DS: vor dem Start pruefbar (#299)
#
# Azahar laedt ausschliesslich ENTSCHLUESSELTE Abbilder und entschluesselt NICHT selbst —
# auch nicht mit `aes_keys.txt` und `boot9.bin`. Der Wunsch danach wurde upstream als
# "closed as not planned" abgelehnt (azahar-emu/azahar#2207).
#
# Ohne diese Pruefung endet ein verschluesselter Titel als leerer Stream: Azahar startet,
# zeigt `App Encrypted` oder gar kein Fenster, und der Nutzer sieht einen Desktop ohne
# Erklaerung. Am Bestand nachgemessen waren 1248 von 1249 Abbildern verschluesselt — das
# ist kein Randfall, sondern der Normalfall einer Sammlung aus Cartridge-Dumps.
#
# Geprueft wird der NCCH-Kopf: Bei 0x100 steht `NCSD`, die erste Partition beginnt bei
# 0x4000 mit `NCCH` bei 0x4100, und ab 0x188 liegen acht Flag-Bytes. Bit 2 von Flag 7
# (0x04) ist `NoCrypto` — gesetzt heisst unverschluesselt.
#
# EN: Azahar only loads decrypted dumps and will not decrypt (upstream: closed as not
# planned). Without this check an encrypted title becomes an empty stream.
_3DS_ENDUNGEN = (".3ds", ".cci")


# --- 3DS: auf Anforderung entschluesseln (#354) -------------------------------------
#
# WOHIN, UND WARUM NICHT AN ORT UND STELLE: Das VERSCHLUESSELTE Original ist es, was den
# Titel identifizierbar macht. Gemessen: 3DS hat mit 15 von 20 Hasheous-Treffern die beste
# Erkennungsquote dieser Bibliothek — `dos`, `gba`, `nds` und `gbc` haben je null. Hasheous
# gleicht Pruefsummen gegen Dump-Datenbanken ab, und die fuehren 3DS-Titel verschluesselt.
# Am Original zu schreiben aendert jede Pruefsumme und wirft genau diese Treffer weg.
#
# Der Zwischenspeicher liegt AUSSERHALB der Bibliothek: laege er darin, indexierte RomM die
# Kopien als zusaetzliche Titel, und das Umbau-Werkzeug faende sie beim naechsten Lauf.
#
# Die oft genannten 397 GB sind ein Phantom — sie unterstellen, alles werde entschluesselt.
# Auf Anforderung heisst: nur was gestartet wird. Der Deckel unten fasst ein Dutzend Titel.
#
# The encrypted original is what identifies the title: 3DS has the best match rate in this
# library, and those matches are on the encrypted bytes. The cache lives outside the library
# so RomM does not index the copies.
ENTSCHL_WERKZEUG = "/config/tools/3ds-decrypt"
ENTSCHL_CACHE = os.environ.get("DECRYPT_3DS_CACHE", "/config/3ds-entschluesselt")
ENTSCHL_DECKEL = int(os.environ.get("DECRYPT_3DS_CACHE_GB", "50")) * 1024 ** 3
ENTSCHL_WERKZEUG_CIA = "/config/tools/3ds-decrypt-cia"
AZAHAR = "/config/emulators/azahar/AppRun"
# Wohin Azahar installierte Titel legt. Der Pfad ist fest: die beiden Nullenketten sind die
# id0/id1 der emulierten SD-Karte und werden von Azahar nicht variiert.
AZAHAR_SDMC = ("/config/.local/share/azahar-emu/sdmc/Nintendo 3DS/"
               "00000000000000000000000000000000/00000000000000000000000000000000/title")

# Kategorien der 3DS-Titel-ID (obere 32 Bit). Nur diese beiden starten; alles andere ist
# Zubehoer zu einem anderen Titel. Am Bestand nachgemessen: von 25 CIAs sind 13 Updates und
# 2 DLC — der DATEINAME lag dabei in zwei Faellen daneben, die Titel-ID nie. (#315)
CIA_STARTBAR = {0x00040000, 0x00040002}          # Anwendung, Demo
CIA_ZUBEHOER = {0x0004000E: "update", 0x0004008C: "dlc"}

_SIG_LAENGE = {0x00010000: (0x200, 0x3C), 0x00010001: (0x100, 0x3C), 0x00010002: (0x3C, 0x40),
               0x00010003: (0x200, 0x3C), 0x00010004: (0x100, 0x3C), 0x00010005: (0x3C, 0x40)}


def cia_titel_id(pfad):
    """-> (titel_id, fehler). Liest die Titel-ID aus der TMD einer CIA.

    WARUM NICHT AM DATEINAMEN: `... - Update 11 ...` und `(DLC)` stehen oft, aber nicht
    immer im Namen — und zweimal stand etwas anderes drin, als die Datei enthaelt. Die
    Titel-ID ist die einzige Quelle, die nicht von der Sorgfalt des Packers abhaengt.

    Der Aufbau: CIA-Kopf, dann Zertifikatskette, Ticket, TMD — jeder Abschnitt auf 64 Byte
    ausgerichtet. In der TMD folgt hinter Signaturtyp, Signatur und Auffuellung der Kopf,
    dessen Titel-ID bei 0x4C steht.
    """
    import struct
    try:
        with open(pfad, "rb") as f:
            kopf = f.read(0x8000)
    except OSError as e:
        return 0, str(e)
    if len(kopf) < 0x2020:
        return 0, "Datei zu kurz fuer einen CIA-Kopf"
    try:
        hs, _typ, _ver, certs, tickets, _tmds = struct.unpack_from("<IHHIII", kopf, 0)
        aus = lambda n: (n + 63) // 64 * 64
        off = aus(hs) + aus(certs) + aus(tickets)
        sigtyp = struct.unpack_from(">I", kopf, off)[0]
        if sigtyp not in _SIG_LAENGE:
            return 0, f"unbekannter Signaturtyp 0x{sigtyp:08X}"
        laenge, fuell = _SIG_LAENGE[sigtyp]
        tmd = off + 4 + laenge + fuell
        if tmd + 0x54 > len(kopf):
            return 0, "TMD liegt ausserhalb des gelesenen Bereichs"
        return struct.unpack_from(">Q", kopf, tmd + 0x4C)[0], ""
    except (struct.error, IndexError) as e:
        return 0, f"CIA-Kopf nicht lesbar: {e}"

def entschluesselung_moeglich():
    """Kann dieser Host ueberhaupt entschluesseln? Ohne Werkzeug ODER Bibliothek: nein."""
    if not os.path.isfile(ENTSCHL_WERKZEUG):
        return False
    try:
        subprocess.run([sys.executable, "-c", "import Crypto"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        return True
    except Exception:
        return False

def _cache_name(pfad):
    """Schluessel aus Pfad, Groesse und Aenderungszeit.

    Die beiden letzten muessen mit hinein: Wird ein Original ersetzt — ein besserer Dump,
    eine andere Region —, verfaellt der Eintrag von selbst. Nur der Pfad wuerde still die
    alte Fassung weiterstarten, und das faellt niemandem auf.
    """
    import hashlib
    try:
        st = os.stat(pfad)
        kennung = f"{pfad}|{st.st_size}|{int(st.st_mtime)}"
    except OSError:
        kennung = pfad
    kurz = hashlib.sha256(kennung.encode()).hexdigest()[:16]
    return os.path.join(ENTSCHL_CACHE, kurz + os.path.splitext(pfad)[1].lower())

def _cache_aufraeumen(schonen=""):
    """Ueber dem Deckel: aelteste Zugriffe zuerst loeschen.

    Der gerade erzeugte Eintrag wird geschont — ihn wegzuwerfen, bevor er benutzt wurde,
    waere die teuerste aller Reihenfolgen.
    """
    try:
        eintraege = []
        for f in os.listdir(ENTSCHL_CACHE):
            p = os.path.join(ENTSCHL_CACHE, f)
            if os.path.isfile(p) and p != schonen and not p.endswith(".part"):
                st = os.stat(p)
                eintraege.append((st.st_atime, st.st_size, p))
        gesamt = sum(g for _a, g, _p in eintraege)
        try:
            gesamt += os.path.getsize(schonen) if schonen else 0
        except OSError:
            pass
        eintraege.sort()
        while gesamt > ENTSCHL_DECKEL and eintraege:
            _a, groesse, pfad = eintraege.pop(0)
            try:
                os.remove(pfad); gesamt -= groesse
                print(f"[3ds] Zwischenspeicher: {os.path.basename(pfad)} verdraengt", flush=True)
            except OSError:
                break
    except OSError:
        pass

def _3ds_entschluesseln(pfad):
    """-> (ziel, fehler). Entschluesselt nach Bedarf; ein Treffer im Zwischenspeicher
    wird sofort zurueckgegeben.

    ATOMAR: Es wird nach `.part` geschrieben und erst bei Erfolg umbenannt. Ein
    abgebrochener Lauf darf nichts hinterlassen, was spaeter fuer einen guten Dump gehalten
    wird — eine halb entschluesselte Datei sieht wie ein Abbild aus und startet nur nicht.
    """
    ziel = _cache_name(pfad)
    if os.path.isfile(ziel) and os.path.getsize(ziel) > 0:
        os.utime(ziel, None)              # Zugriffszeit auffrischen, fuer die Verdraengung
        return ziel, ""
    os.makedirs(ENTSCHL_CACHE, exist_ok=True)
    teil = ziel + ".part"
    try:
        import shutil
        shutil.copyfile(pfad, teil)       # das Werkzeug arbeitet in-place auf seiner Kopie
        r = subprocess.run([sys.executable, ENTSCHL_WERKZEUG, teil],
                           capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout or "")[-300:] or "unbekannter Fehler")
        os.replace(teil, ziel)
    except Exception as e:
        try: os.remove(teil)
        except OSError: pass
        return "", f"Entschluesselung fehlgeschlagen / decryption failed: {e}"
    _cache_aufraeumen(schonen=ziel)
    return ziel, ""

def cia_installierbar():
    """Kann dieser Host CIAs installieren? Braucht Entschluesselung UND Azahar."""
    return (entschluesselung_moeglich()
            and os.path.isfile(ENTSCHL_WERKZEUG_CIA)
            and os.path.isfile(AZAHAR))


def _cia_installiert(titel):
    """-> Pfad des installierten Titels oder "". Sucht die Inhaltsdatei auf der SD-Karte.

    WARUM DAS ZUERST GEPRUEFT WIRD: Eine Installation ist DAUERHAFT — anders als der
    Zwischenspeicher der Abbilder aendert sie Azahars SD-Karte. Ein zweiter Start desselben
    Titels darf deshalb weder entschluesseln noch installieren, sondern nur starten.
    """
    ordner = os.path.join(AZAHAR_SDMC, f"{titel >> 32:08x}", f"{titel & 0xFFFFFFFF:08x}",
                          "content")
    try:
        apps = sorted(d for d in os.listdir(ordner) if d.lower().endswith(".app"))
    except OSError:
        return ""
    # Die erste Inhaltsdatei ist der ausfuehrbare Teil; weitere sind Zusatzinhalte.
    return os.path.join(ordner, apps[0]) if apps else ""


def _cia_entschluesseln(pfad):
    """-> (ziel, fehler). Entschluesselt in ein EIGENES Verzeichnis und raeumt es weg.

    WARUM EIN VERZEICHNIS UND NICHT NUR EINE .part-DATEI (#388): `decrypt_cia.py` bildet
    seinen Ausgabenamen selbst — `splitext(eingabe)[0] + "-decrypted.cia"`, mit FESTER
    Endung. Wer diesen Namen nachrechnet, rechnet ihn irgendwann falsch nach: Die erste
    Fassung uebergab `<hash>.cia.part` und erwartete `<hash>.cia-decrypted.part`, waehrend
    das Werkzeug `<hash>.cia-decrypted.cia` schrieb. Die Entschluesselung lief durch, die
    Datei war da, und der Aufrufer meldete „keine Ausgabedatei" — 342 MB blieben liegen.

    Deshalb wird hier NICHT nachgerechnet: Im eigenen Verzeichnis liegt hinterher genau
    eine `.cia`, die nicht die Eingabe ist. Das ist die Ausgabe, egal wie sie heisst. Und
    das Verzeichnis verschwindet mitsamt allem, was das Werkzeug sonst noch ablegt.

    The tool builds its own output name with a hardcoded extension. Rather than recomputing
    it — which is how this broke — decrypt inside a scratch directory and take whatever
    .cia is not the input.
    """
    ziel = _cache_name(pfad)
    if os.path.isfile(ziel) and os.path.getsize(ziel) > 0:
        os.utime(ziel, None)
        return ziel, ""
    os.makedirs(ENTSCHL_CACHE, exist_ok=True)

    import shutil, tempfile
    arbeit = tempfile.mkdtemp(prefix="cia-", dir=ENTSCHL_CACHE)
    try:
        eingabe = os.path.join(arbeit, "eingabe.cia")
        shutil.copyfile(pfad, eingabe)
        r = subprocess.run([sys.executable, ENTSCHL_WERKZEUG_CIA, eingabe],
                           capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout or "")[-300:] or "Werkzeug scheiterte")
        aus = [f for f in os.listdir(arbeit)
               if f.lower().endswith(".cia") and f != "eingabe.cia"]
        if not aus:
            raise RuntimeError("das Werkzeug hat keine Ausgabedatei hinterlassen")
        # `os.replace` statt `shutil.move`: atomar, solange beides im selben Dateisystem
        # liegt — und das Arbeitsverzeichnis liegt bewusst IM Zwischenspeicher.
        os.replace(os.path.join(arbeit, aus[0]), ziel)
    except Exception as e:
        return "", f"CIA-Entschluesselung fehlgeschlagen / CIA decryption failed: {e}"
    finally:
        shutil.rmtree(arbeit, ignore_errors=True)
    _cache_aufraeumen(schonen=ziel)
    return ziel, ""


def cia_bereitstellen(pfad):
    """-> (startpfad, fehler). Entschluesselt, installiert und nennt den startbaren Pfad.

    Reihenfolge mit Bedacht: erst nachsehen, ob der Titel schon installiert ist. Sonst
    kostete jeder Start eine volle Kopie und eine Installation fuer nichts.
    """
    titel, fehler = cia_titel_id(pfad)
    if fehler:
        return "", f"cia_unreadable: {fehler}"
    kategorie = titel >> 32
    if kategorie in CIA_ZUBEHOER:
        # Update und DLC gehoeren zu einem anderen Titel. Sie zu installieren waere
        # sinnvoll, sie zu STARTEN nie — deshalb ist das hier eine Absage, keine Panne.
        return "", CIA_ZUBEHOER[kategorie]
    if kategorie not in CIA_STARTBAR:
        return "", "cia_not_bootable"

    schon = _cia_installiert(titel)
    if schon:
        print(f"[3ds] CIA bereits installiert: {titel:016X}", flush=True)
        return schon, ""

    if not cia_installierbar():
        return "", "cia_not_bootable"

    print(f"[3ds] entschluessele und installiere {os.path.basename(pfad)}", flush=True)
    klar, fehler = _cia_entschluesseln(pfad)
    if fehler:
        return "", fehler
    umgebung = dict(os.environ, HOME="/config")
    try:
        r = subprocess.run([AZAHAR, "--install", klar], env=umgebung,
                           capture_output=True, text=True, timeout=1800)
    except Exception as e:
        return "", f"cia_install_failed: {e}"
    if "successfully" not in (r.stdout + r.stderr).lower():
        return "", "cia_install_failed: " + (r.stdout + r.stderr).strip()[-200:]

    start = _cia_installiert(titel)
    if not start:
        # Installation gemeldet, aber nichts auffindbar: lieber absagen als einen Pfad
        # raten. Ein geratener Pfad startet den falschen Titel oder gar nichts.
        return "", "cia_install_failed: installiert, aber kein Inhalt gefunden"
    print(f"[3ds] installiert, starte {titel:016X}", flush=True)
    return start, ""


def _3ds_art(pfad):
    """-> ".cia", ".3ds" oder "" — was die Datei WIRKLICH ist, unabhaengig vom Namen. (#422)

    Gegenstueck zu `dreids_art` in `app.py`; beide Seiten muessen dasselbe entscheiden,
    sonst sagt Romseerr zu und der Agent ab (oder umgekehrt).

    - **CIA**: Das erste Feld ist die Kopfgroesse und betraegt bei jeder CIA `0x2020`.
    - **NCSD**: die Kennung `NCSD` bei 0x100.

    Im Zweifel "" — der Aufrufer faellt dann auf die Endung zurueck, also auf das
    Verhalten von vorher.

    EN: mirror of `dreids_art` in app.py. Both sides must decide alike, otherwise Romseerr
    promises and the agent refuses.
    """
    import struct
    try:
        with open(pfad, "rb") as f:
            kopf = f.read(4)
            f.seek(0x100)
            kennung = f.read(4)
    except OSError:
        return ""
    if len(kopf) == 4 and struct.unpack("<I", kopf)[0] == 0x2020:
        return ".cia"
    if kennung == b"NCSD":
        return ".3ds"
    return ""


def _switch_art(pfad):
    """-> Absagegrund, oder "" wenn die Datei ein Spiel sein kann. (#427)

    Die letzten drei Stellen der Titel-ID sagen, WAS das Paket ist: `000` Basisspiel,
    `800` Update, ab `001` Zusatzinhalt. Die ID steht unverschluesselt im
    Inhaltsverzeichnis der NSP — im Namen von `<rights-id>.tik`, dessen erste 16
    Hexzeichen sie sind. Es braucht dafuer keine Schluessel.

    IM ZWEIFEL DURCHLASSEN: XCI ist ein anderer Behaelter und praktisch immer ein
    Basisspiel; ein Archiv ohne Ticket ist nicht beurteilbar. Beide gehen durch. Eine
    falsche Absage kostet mehr als ein Fehlversuch — dieselbe Regel wie bei 3DS.

    EN: refuse only what identifies itself as update or add-on. The title ID sits
    unencrypted in the PFS0 index; no keys needed.
    """
    import struct
    try:
        with open(pfad, "rb") as f:
            kopf = f.read(0x8000)
    except OSError:
        return ""
    if kopf[:4] != b"PFS0":
        return ""
    try:
        anzahl = struct.unpack_from("<I", kopf, 4)[0]
        if not 0 < anzahl <= 4000:
            return ""
        basis = 0x10 + anzahl * 0x18
        titel = ""
        for i in range(anzahl):
            _o, _s, so, _r = struct.unpack_from("<QQII", kopf, 0x10 + i * 0x18)
            ende = kopf.index(b"\x00", basis + so)
            name = kopf[basis + so:ende].decode("utf-8", "replace")
            if name.endswith((".tik", ".cert")) and len(name) > 16:
                titel = name[:16].lower()
                break
    except (struct.error, ValueError, IndexError):
        return ""
    if len(titel) != 16:
        return ""
    endung = titel[-3:]
    if endung == "800":
        return ("Das ist ein Update, kein Spiel / "
                "this is an update, not a game")
    if endung == "000":
        return ""
    try:
        n = int(endung, 16)
    except ValueError:
        return ""
    if 0 < n < 0x800:
        return ("Das ist ein Zusatzinhalt (DLC), kein eigenstaendiges Spiel / "
                "this is add-on content, not a game")
    return ""


def _3ds_spielbar(pfad):
    """-> (spielbar, grund). Nur fuer 3DS-Abbilder; alles andere gilt als spielbar.

    DER INHALT SCHLAEGT DEN NAMEN (#422): In der Bibliothek liegt eine CIA, die `.3ds`
    heisst. Nach der Endung beurteilt fiel sie durch die NCSD-Pruefung in den Zweig
    „nicht beurteilbar, also durchlassen" — und waere als Abbild an den Emulator gegangen,
    der damit nichts anfangen kann.
    """
    endung = _3ds_art(pfad) or os.path.splitext(pfad)[1].lower()
    if endung == ".cia":
        # CIAs sind Installationspakete, keine startbaren Abbilder — unabhaengig von
        # jeder Verschluesselung. Azahar sagt das selbst: "CIA must be installed
        # before usage".
        return False, ("CIA-Dateien sind Installationspakete und starten nicht direkt / "
                       "CIA files are installation packages and do not boot directly")
    if endung not in _3DS_ENDUNGEN:
        return True, ""
    try:
        with open(pfad, "rb") as f:
            f.seek(0x100)
            if f.read(4) != b"NCSD":
                return True, ""          # kein NCSD -> nicht beurteilbar, nicht abweisen
            f.seek(0x4100)
            if f.read(4) != b"NCCH":
                return True, ""
            f.seek(0x4188)
            flags = f.read(8)
    except OSError:
        return True, ""                  # nicht lesbar ist ein anderes Problem
    if len(flags) < 8:
        return True, ""
    if flags[7] & 0x04:                  # NoCrypto
        return True, ""
    return False, ("Das Abbild ist VERSCHLUESSELT. Azahar spielt nur entschluesselte "
                   "Dumps und entschluesselt nicht selbst — der Titel muss entschluesselt "
                   "vorliegen (etwa mit GodMode9 auf einer echten Konsole). / The image "
                   "is ENCRYPTED; Azahar only runs decrypted dumps and will not decrypt.")


def launch(path, platform, rel="", region=""):
    """(ok, meldung). Einzelplatz: ein laufender Emulator wird zuvor beendet.

    `rel` ist der Pfad RELATIV zur Bibliothekswurzel und hat Vorrang. Ein absoluter
    Pfad bedeutet in zwei Containern nicht dasselbe: haengt der eine die Bibliothek
    unter einem anderen Punkt ein, zeigt er ins Leere. Relativ ist die einzige Angabe,
    die auf beiden Seiten dieselbe Datei benennt — vorausgesetzt, beide meinen
    dieselbe WURZEL, und genau das ist die Bedingung, die dokumentiert gehoert.

    `rel` is relative to the library root and takes precedence: an absolute path does
    not mean the same thing in two containers that mount the library differently."""
    cmd = EMULATORS.get(platform) or ""
    if not cmd:
        return False, f"kein Emulator fuer '{platform}' hinterlegt / no emulator configured"

    # Der Altweg gibt einen absoluten Pfad. Er wird in einen bibliotheksrelativen
    # umgerechnet, damit auch er durch dieselbe Aufloesung geht — eine Tuer, nicht zwei.
    # The legacy absolute path is reduced to a relative one so both go through the
    # same resolution.
    if not rel and path:
        p = os.path.normpath(path)
        if p != ROMS and not p.startswith(ROMS + os.sep):
            return False, "Pfad ausserhalb der Bibliothek / path outside the library"
        rel = p[len(ROMS) + 1:]

    real = _bibliothekspfad(rel)
    if not real:
        # Der haeufigste Grund ist KEIN fehlendes Spiel, sondern zwei Container, die
        # ihre Bibliothek an verschiedenen Stellen einhaengen. Das gehoert in die
        # Meldung, sonst sucht der Betreiber die Datei statt die Einhaengung.
        # The usual cause is two containers mounting the library differently.
        return False, (f"In der Bibliothek nicht gefunden / not found in the library: "
                       f"{rel} — haengen Romseerr und der Streaming-Host DIESELBE "
                       "Bibliothekswurzel ein? / do both mount the same library root?")

    # Switch vor dem Start pruefen (#427). Romseerr fragt dasselbe schon vorher — aber
    # ein direkter Aufruf des Dienstes umgeht das, und dann startet Eden ein Update, das
    # kein Spiel ist. Beide Seiten muessen absagen, sonst haengt die Zusage daran, welchen
    # Weg jemand genommen hat.
    if platform == "switch" and os.path.isfile(real):
        art = _switch_art(real)
        if art:
            return False, art

    # 3DS vor dem Start pruefen (#299): Was verschluesselt ist, kann Azahar nicht
    # spielen — das jetzt zu sagen ist ehrlicher als ein Stream, der leer aufgeht.
    if platform == "3ds" and os.path.isfile(real):
        spielbar, grund = _3ds_spielbar(real)
        if not spielbar and grund.startswith("Das Abbild ist VERSCHLUESSELT"):
            # Verschluesselt ist kein Endzustand mehr, sondern ein Zwischenschritt (#354).
            # Das Original bleibt unangetastet — es ist das, was den Titel identifizierbar
            # macht; entschluesselt wird in einen Zwischenspeicher daneben.
            if not entschluesselung_moeglich():
                return False, grund
            print(f"[3ds] entschluessele {os.path.basename(real)} — das dauert einige Minuten", flush=True)
            ziel, fehler = _3ds_entschluesseln(real)
            if fehler:
                return False, fehler
            real = ziel
            print(f"[3ds] entschluesselt, starte {os.path.basename(real)}", flush=True)
        elif not spielbar and (_3ds_art(real) or
                               os.path.splitext(real)[1].lower()) == ".cia":
            # Eine CIA startet nie DIREKT — aber sie laesst sich installieren, und danach
            # startet der installierte Titel. Was dabei absagt, ist nicht die Datei,
            # sondern ihre Art: Updates und DLC gehoeren zu einem anderen Titel. (#315)
            start, fehler = cia_bereitstellen(real)
            if fehler:
                return False, fehler
            real = start
        elif not spielbar:
            return False, grund

    # Ein Titel ist nicht immer eine Datei. Eine PS3-Disc ist ein ORDNER mit
    # PS3_DISC.SFB und PS3_GAME/USRDIR/EBOOT.BIN darin — nachgemessen, 13 von 17
    # Titeln der Testbibliothek. Die frueher hier stehende Pruefung auf `isfile`
    # hat solche Titel abgewiesen, und zwar mit der Meldung ueber verschiedene
    # Einhaengepunkte: eine PLAUSIBLE, aber falsche Faehrte, die genau in die
    # falsche Richtung schickt.
    #
    # A title is not always a file: a PS3 disc is a directory. The previous `isfile`
    # check rejected those with a message about differing mount points — plausible
    # and wrong, which is the worst kind of error message.
    if os.path.isdir(real):
        boot = _bootdatei(real, platform)
        if not boot:
            return False, (f"Ordner ohne startbaren Inhalt / folder has no bootable file: "
                           f"{os.path.basename(real)}")
        # ERNEUT pruefen. Der Ordner liegt in der Bibliothek, die Startdatei darin muss
        # es deshalb noch lange nicht: ein Symlink genuegt, um heraus zu zeigen.
        # Gefunden hat diese Luecke CodeQL, nicht der Testlauf.
        # The folder being inside the library says nothing about a symlink within it.
        try:
            real = os.path.realpath(boot)
            if os.path.commonpath([real, ROMS]) != ROMS:
                raise ValueError
        except (ValueError, OSError):
            return False, ("Startdatei zeigt aus der Bibliothek heraus / "
                           "boot file points outside the library")

    # Controller-Belegung setzen, bevor der Emulator die Konfiguration liest. Scheitert
    # das, wird trotzdem gestartet: ohne Pad spielen ist schlechter als gar nicht
    # spielen — aber nur ein bisschen, und die Meldung steht im Log.
    # Applied before the emulator reads its config; a failure here does not block the
    # launch, it is logged.
    profil = PROFILE_EMU.get(platform)
    if profil and os.path.isfile(PROFILE_SCRIPT):
        # Controller immer, BIOS nur wenn eine Region bekannt ist. Ohne Region raten
        # waere schlimmer als nichts zu tun: ein falsches BIOS meldet sich nicht,
        # es laeuft nur "komisch".
        # Guessing a region would be worse than leaving it: a wrong BIOS does not
        # announce itself, the game merely behaves oddly.
        # Reihenfolge: Controller, BIOS, Vollbild — alles BEVOR der Emulator seine
        # Konfiguration liest. Danach zu setzen hiesse, gegen einen laufenden Prozess
        # zu arbeiten, der seine eigene Geometrie zurueckschreibt.
        auftraege = [["--apply", profil], ["--fullscreen", profil]]
        if region:
            auftraege.insert(1, ["--bios", profil, region])
        for a in auftraege:
            try:
                r = subprocess.run([sys.executable, PROFILE_SCRIPT] + a,
                                   capture_output=True, text=True, timeout=30)
                print((r.stdout + r.stderr).strip(), flush=True)
            except (subprocess.TimeoutExpired, OSError) as e:
                print(f"[profil] {profil}: {e.__class__.__name__}", flush=True)

    # argv ist damit: fester Befehl aus der Umgebung (der Betreiber setzt ihn) + genau EIN
    # geprueftes Argument aus der Bibliothek. Keine Shell, keine Wortzerlegung durch execve.
    argv = [real if part == "%s" else part for part in shlex.split(cmd)]
    if "%s" not in cmd:
        argv.append(real)
    umgebung = start_umgebung(platform)
    with _lock:
        _stop_locked()
        try:
            # Kein shell=True: die Argumentliste geht unveraendert an execve.
            _current["proc"] = subprocess.Popen(argv, stdout=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL, env=umgebung)
        except OSError as e:
            return False, f"Start fehlgeschlagen / launch failed: {e.__class__.__name__}"
        _current["platform"] = platform
        _current["path"] = real
        _current["window"] = "pending"
        _current["window_detail"] = ""

    # Nur das Emulatorfenster zeigen (#141). Im Hintergrund, weil auf das Fenster bis
    # zu 20 Sekunden gewartet wird — der Aufrufer soll darauf nicht haengen. Schlaegt
    # es fehl, laeuft das Spiel trotzdem: ein Desktop drumherum ist unschoen, ein
    # nicht gestarteter Titel waere schlimmer.
    # Backgrounded because it waits for the window; a failure here must not cost the
    # launch, only the framing.
    if os.path.isfile(PROFILE_SCRIPT):
        pid = _current["proc"].pid
        def _merken(zustand, detail=""):
            # Nur solange derselbe Titel laeuft: ein inzwischen gestarteter zweiter Titel
            # darf nicht den Befund des ersten uebergestuelpt bekommen.
            with _lock:
                if _current["proc"] is not None and _current["proc"].pid == pid:
                    _current["window"] = zustand
                    _current["window_detail"] = detail

        def _fenster():
            try:
                # 150 statt 60 Sekunden: der Schritt wartet bewusst mehrere Runden auf
                # das SPIELFENSTER, das spaeter entsteht als das erste Fenster des
                # Emulators. Bei Eden reichten 60 s nicht, und der Befund kam als
                # "unbekannt" an — also als Nichtaussage genau dort, wo eine Aussage
                # gebraucht wird. (#288)
                r = subprocess.run([sys.executable, PROFILE_SCRIPT, "--window", str(pid)],
                                   capture_output=True, text=True, timeout=150)
                ausgabe = (r.stdout + r.stderr).strip()
                print(ausgabe, flush=True)
                # Letzte Zeile ist die JSON-Auskunft von --window (#288). Faellt sie aus
                # — altes Skript, Absturz —, bleibt es beim Zustand "unbekannt" statt
                # einer erfundenen Zusage.
                befund = {}
                for zeile in reversed(ausgabe.splitlines()):
                    if zeile.startswith("{"):
                        try:
                            befund = json.loads(zeile)
                        except ValueError:
                            befund = {}
                        break
                _merken(befund.get("window", "unbekannt"), befund.get("detail", ""))
            except (subprocess.TimeoutExpired, OSError) as e:
                print(f"[fenster] {e.__class__.__name__}", flush=True)
                _merken("unbekannt", e.__class__.__name__)
        threading.Thread(target=_fenster, daemon=True).start()
    return True, os.path.basename(real)


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorised(self, query):
        if not TOKEN:
            return False
        supplied = (self.headers.get("X-Stream-Token")
                    or (query.get("token") or [""])[0])
        # Konstante Laufzeit: kein Rueckschluss auf das Token ueber die Antwortzeit.
        import hmac
        return hmac.compare_digest(str(supplied), TOKEN)

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if not self._authorised(q):
            return self._reply(401, {"ok": False, "msg": "unauthorised"})
        if u.path not in ("/launch", "/stop", "/update", "/rollback", "/install",
                          "/firmware/upload", "/firmware/vendor"):
            return self._reply(404, {"ok": False, "msg": "not found"})
        if u.path == "/firmware/vendor":
            if _vendor["running"]:
                return self._reply(409, {"ok": False, "msg": "laeuft bereits / already running"})
            plat = (q.get("platform") or [""])[0]
            # Herstellerbezug gibt es nur da, wo der Hersteller wirklich ausliefert.
            # Vita3K laedt NICHTS herunter - der Quelltext oeffnet einen Dateidialog.
            if plat != "ps3":
                return self._reply(400, {"ok": False, "reason": "no_vendor_source",
                                         "msg": "Herstellerbezug nur fuer ps3 / vendor fetch only for ps3"})
            threading.Thread(target=run_vendor, args=(plat,), daemon=True).start()
            return self._reply(200, {"ok": True, "msg": "gestartet / started"})
        if u.path == "/firmware/upload":
            return self._firmware_upload(q)
        if u.path == "/stop":
            with _lock:
                _stop_locked()
            # Panel zurueckholen: ein dauerhaft verstecktes Panel macht den Host
            # unbenutzbar fuer alles, was eine GUI braucht — etwa das Einrichten eines
            # Emulators. Was eine Sitzung aendert, raeumt sie auch wieder weg.
            # A permanently hidden panel would make the host unusable for setup work.
            if os.path.isfile(PROFILE_SCRIPT):
                try:
                    subprocess.run([sys.executable, PROFILE_SCRIPT, "--desktop"],
                                   capture_output=True, timeout=20)
                except (subprocess.TimeoutExpired, OSError):
                    pass
            return self._reply(200, {"ok": True})
        if u.path == "/update":
            if _update["running"]:
                return self._reply(409, {"ok": False, "msg": "laeuft bereits / already running"})
            # Mit `?name=<ordner>` genau EINEN Emulator aktualisieren, ohne die anderen
            # anzufassen (#338). Der Weg dorthin ist derselbe wie beim Installieren:
            # `20-emulators --only <ordner>` laedt, was sich geaendert hat, und laesst den
            # Rest in Ruhe — installieren und aktualisieren sind dort dieselbe Handlung.
            # `?name=<dir>` updates exactly one emulator; the script's --only path already
            # treats installing and updating as the same operation.
            ziel = (q.get("name") or [""])[0].strip()
            if ziel:
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}", ziel):
                    return self._reply(400, {"ok": False, "msg": "ungueltiger Name / bad name"})
                threading.Thread(target=run_install, args=(ziel,), daemon=True).start()
                return self._reply(200, {"ok": True, "msg": f"gestartet / started: {ziel}"})
            threading.Thread(target=run_update, daemon=True).start()
            return self._reply(200, {"ok": True, "msg": "gestartet / started"})
        if u.path == "/install":
            if _update["running"]:
                return self._reply(409, {"ok": False, "msg": "laeuft bereits / already running"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                d = json.loads(self.rfile.read(min(n, 4096)) or b"{}")
            except (ValueError, OSError):
                return self._reply(400, {"ok": False, "msg": "kein gueltiges JSON / invalid JSON"})
            name = str(d.get("name") or "")
            # Der Name geht in eine Argumentliste; nur was ein Ordnername sein darf,
            # und er muss im Katalog stehen. Zwei Pruefungen, weil die erste
            # Zeichenklassen kennt und die zweite die Wirklichkeit.
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", name):
                return self._reply(400, {"ok": False, "msg": "unzulaessiger Name / invalid name"})
            if name not in {e.get("dir") for e in catalogue()}:
                return self._reply(404, {"ok": False, "msg": "nicht im Katalog / not in catalogue"})
            threading.Thread(target=run_install, args=(name,), daemon=True).start()
            return self._reply(200, {"ok": True, "msg": "gestartet / started"})
        if u.path == "/rollback":
            # Zurueck zur vorigen Fassung. Der Name kommt von aussen und geht in eine
            # Argumentliste — deshalb nur Zeichen, die ein Ordnername haben darf.
            # The name comes from outside; restrict it to plausible directory names.
            try:
                n = int(self.headers.get("Content-Length") or 0)
                d = json.loads(self.rfile.read(min(n, 4096)) or b"{}")
            except (ValueError, OSError):
                return self._reply(400, {"ok": False, "msg": "kein gueltiges JSON / invalid JSON"})
            name = str(d.get("name") or "")
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", name):
                return self._reply(400, {"ok": False, "msg": "unzulaessiger Name / invalid name"})
            r = subprocess.run(["/bin/bash", UPDATE_SCRIPT, "--rollback", name],
                               capture_output=True, text=True, timeout=120)
            return self._reply(200 if r.returncode == 0 else 400,
                               {"ok": r.returncode == 0,
                                "msg": (r.stdout + r.stderr).strip()[-400:]})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(min(n, 65536)) or b"{}")
        except (ValueError, OSError):
            return self._reply(400, {"ok": False, "msg": "kein gueltiges JSON / invalid JSON"})
        ok, msg = launch(str(d.get("path") or ""), str(d.get("platform") or ""),
                         str(d.get("rel") or ""), str(d.get("region") or "")[:32])
        return self._reply(200 if ok else 400, {"ok": ok, "msg": msg})

    def _firmware_upload(self, q):
        """Rohe Datei im Rumpf, Plattform und Name in der Abfrage. Kein Multipart:
        das waere ein Parser mehr in einem Dienst, der Prozesse startet — und der
        Aufrufer ist Romseerr, kein Browser-Formular.
        Raw body, no multipart: one parser less in a service that spawns processes."""
        plat = (q.get("platform") or [""])[0]
        name = (q.get("name") or [""])[0]
        if plat not in firmware_platforms():
            return self._reply(400, {"ok": False, "reason": "bad_platform"})
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name or ""):
            return self._reply(400, {"ok": False, "reason": "bad_name"})
        try:
            laenge = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._reply(400, {"ok": False, "reason": "bad_length"})
        if laenge <= 0:
            return self._reply(400, {"ok": False, "reason": "empty"})
        if laenge > MAX_UPLOAD:
            return self._reply(413, {"ok": False, "reason": "too_large",
                                     "limit": MAX_UPLOAD})

        # In eine temporaere Datei schreiben und erst dann dem Skript uebergeben:
        # ein abgebrochener Upload darf keine halbe Firmware in der Ablage hinterlassen,
        # die spaeter als "vorhanden" durchgeht.
        # Write to a temp file first; an aborted upload must not leave half a firmware
        # in place that later reads as "present".
        tmp = tempfile.NamedTemporaryFile(delete=False, prefix="fw-", suffix=".part")
        gelesen = 0
        try:
            while gelesen < laenge:
                block = self.rfile.read(min(65536, laenge - gelesen))
                if not block:
                    break
                tmp.write(block); gelesen += len(block)
            tmp.close()
            if gelesen != laenge:
                return self._reply(400, {"ok": False, "reason": "short_body",
                                         "expected": laenge, "got": gelesen})
            r = subprocess.run(["/bin/bash", FIRMWARE_SCRIPT, "--import", plat, tmp.name, name],
                               capture_output=True, text=True, timeout=300)
            return self._reply(200 if r.returncode == 0 else 400,
                               {"ok": r.returncode == 0,
                                "log": (r.stdout + r.stderr)[-4000:],
                                "status": firmware_status()})
        except (OSError, subprocess.TimeoutExpired) as e:
            return self._reply(500, {"ok": False, "reason": e.__class__.__name__})
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path not in ("/status", "/update", "/catalog", "/firmware"):
            return self._reply(404, {"ok": False, "msg": "not found"})
        if not self._authorised(parse_qs(u.query)):
            return self._reply(401, {"ok": False, "msg": "unauthorised"})
        if u.path == "/firmware":
            return self._reply(200, {"ok": True, **firmware_status(),
                                     "vendor": dict(_vendor)})
        if u.path == "/catalog":
            return self._reply(200, {"ok": True, "catalog": catalogue(),
                                     "busy": _update["running"],
                                     "target": _update.get("target", "")})
        if u.path == "/update":
            return self._reply(200, {"ok": True, **{k: v for k, v in _update.items()},
                                     "emulators": installed_emulators(),
                                     "catalog": catalogue()})
        p = _current["proc"]
        return self._reply(200, {"ok": True, "running": bool(p and p.poll() is None),
                                 "platform": _current["platform"],
                                 "window": _current["window"],
                                 "window_detail": _current["window_detail"],
                                 "file": os.path.basename(_current["path"]) if _current["path"] else "",
                                 "platforms": sorted(k for k, v in EMULATORS.items() if v),
                                 "emulators": installed_emulators(),
                                 # Damit Romseerr weiss, ob ein verschluesselter 3DS-Titel eine
                                   # Absage wert ist oder nur eine Wartezeit (#354).
                                   # Ohne diese Auskunft muesste es raten — und raten
                                   # hiesse entweder falsch absagen oder falsch versprechen.
                                   "can_decrypt_3ds": entschluesselung_moeglich(),
                                   "can_install_cia": cia_installierbar(),
                                   "update_running": _update["running"]})

    def log_message(self, *_a):
        pass   # keine Zugriffsprotokolle auf stderr


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("STREAM_AGENT_TOKEN ist nicht gesetzt — der Dienst startet Prozesse und "
                 "laeuft nicht ungeschuetzt. / refusing to run without a token.")
    print(f"stream-agent auf :{PORT}, Bibliothek {ROMS}, "
          f"Plattformen: {', '.join(sorted(k for k, v in EMULATORS.items() if v))}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()  # nosec B104 - Container-Dienst
