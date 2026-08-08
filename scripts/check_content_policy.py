#!/usr/bin/env python3
"""Prüft, dass keine Inhalte im Repository landen. / Content policy check.

Romseerr ist Werkzeug. Weder Spielinhalte noch Firmware, Schlüssel oder Verweise auf
Bezugsquellen gehören hierher — die Quellen trägt der Betreiber in den Einstellungen
ein. Die Regel steht in .github/CONTRIBUTING.md; dieses Skript setzt sie durch.

Romseerr is tooling. Game content, firmware, keys and pointers to content sources do
not belong here; sources are supplied by the operator at runtime.

    python scripts/check_content_policy.py            # ganzer Baum / whole tree
    python scripts/check_content_policy.py a.py b.md  # nur diese Dateien / only these

Rückgabe 0 = sauber, 1 = Fund. / Exit 0 clean, 1 on a finding.

ABSICHT DER BAUWEISE: Das Skript wird von zwei Stellen aufgerufen — vom Test
(schnelles Signal beim Entwickeln) und von einem Workflow, der es aus dem
HAUPTZWEIG auscheckt. Letzteres ist der Punkt: ein Pull Request, der Inhalte
mitbringt, könnte sonst im selben Zug die Prüfung aufweichen.

DESIGN NOTE: called from the test (fast local signal) and from a workflow that
checks this file out from the DEFAULT branch — so a pull request cannot lower its
own gate.
"""
import os
import re
import sys

# Endungen, die auf Spielinhalte oder Abbilder hindeuten. Bewusst knapp: es geht um
# das, was hier realistisch aufschlägt, nicht um eine vollständige Systematik.
CONTENT_EXT = {
    "iso", "chd", "cue", "gdi", "cdi", "rvz", "wbfs", "gcm", "nsp", "xci", "cia",
    "sfc", "smc", "nes", "gba", "gbc", "n64", "z64", "v64", "smd", "pce",
    "vpk", "pkg", "wud", "wux",
}
# ".md" fehlt hier bewusst: es ist zugleich Markdown und Mega Drive. Bei einem Repo
# voller Markdown ist der Fehlalarm sicher, der echte Fund unwahrscheinlich — und ein
# Prüfer, der bei jedem Lauf rauscht, wird abgeschaltet.
# ".md" is deliberately absent: Markdown and Mega Drive share it, and a check that
# cries wolf on every run gets turned off.

# Dateinamen, die typisch für Firmware, BIOS oder Schlüssel sind.
FIRMWARE_RE = re.compile(
    r"^(?:"
    r"scph\d+.*|"                      # PlayStation-BIOS
    r"dc_(?:boot|flash)\.bin|"         # Dreamcast
    r"mcpx.*\.bin|complex.*\.bin|"     # Xbox
    r"boot9\.bin|boot11\.bin|aes_keys\.txt|seeddb\.bin|"   # 3DS
    r"prod\.keys|title\.keys|"         # Switch
    r".*UPDAT\.PUP|"                   # PS3/Vita-Firmware
    r"keys\.txt|"                      # diverse
    r".*\.(?:bios|rom0|rom1|rom2|erom|nvm|mec)"
    r")$", re.I)

# Fest verdrahtete Verweise auf Bezugsquellen. Offizielle Projekt- und Hersteller-
# adressen sind ausdrücklich erlaubt (siehe ALLOWED_HOSTS) — verboten ist, dass
# dieses Repository jemandem sagt, wo er Inhalte herbekommt.
URL_RE = re.compile(r"""https?://[^\s"'<>)\]`]+""", re.I)
# Im HOSTNAMEN verdächtig. Nicht im Pfad: dieses Projekt heißt Romseerr, verwaltet
# /roms und spricht mit einem Dienst namens romm — ein Muster auf den Pfad meldet
# dauernd die eigene Anwendung.
# Suspicious in the HOSTNAME, not the path: this project manages /roms and talks to a
# service called romm, so matching paths would flag the application itself.
HOST_HINT_RE = re.compile(r"(?:rom|iso|nsp|xci|bios|firmware|torrent|ddl|warez|scene|nzb)", re.I)

# Adressen, die trotz verdächtiger Zeichenkette in Ordnung sind: Projektquellen,
# Hersteller, Dokumentation, Metadaten. Namentlich, damit eine neue Aufnahme im
# Diff sichtbar ist statt stillschweigend zu passieren.
ALLOWED_HOSTS = (
    "github.com", "api.github.com", "raw.githubusercontent.com", "objects.githubusercontent.com",
    "gitlab.com", "codeberg.org",
    "archive.org",                 # Suchquelle, keine feste Inhaltsadresse
    "api.igdb.com", "images.igdb.com", "id.twitch.tv",
    "retroachievements.org", "steamgriddb.com", "www.steamgriddb.com",
    "screenscraper.fr",
    "playstation.net", "playstation.com",   # Hersteller-Firmware (PS3/Vita)
    "nintendo.com", "xbox.com",
    "virtualgl.org", "pcsx2.net", "dolphin-emu.org", "rpcs3.net",
    "hydralauncher.gg", "docs.hydralauncher.gg",
    "letsencrypt.org", "certbot.eff.org", "eff.org",
    "linuxserver.io", "www.linuxserver.io", "lscr.io",
    "selkies-project.github.io", "contributor-covenant.org", "www.contributor-covenant.org",
    "bandit.readthedocs.io", "docs.pytest.org", "docs.github.com", "docs.seerr.dev",
    "example.com", "example.org", "beispiel.tld", "invalid",
)

# Einzelne Dateien, die von der Größenprüfung ausgenommen sind. Leer — und das soll
# so bleiben; ein Eintrag hier ist eine Entscheidung, die jemand im Diff sieht.
SIZE_EXCEPTIONS: set = set()

MAX_BYTES = 512 * 1024          # alles darüber ist erklärungsbedürftig
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", "data"}
TEXT_EXT = {"py", "md", "yml", "yaml", "json", "txt", "sh", "js", "css", "html",
            "toml", "cfg", "ini", "example", "gitignore", "trivyignore", "lock"}


def ext_of(path):
    return path.rsplit(".", 1)[-1].lower() if "." in os.path.basename(path) else ""


def check_file(root, rel):
    """-> Liste von Beanstandungen für EINE Datei."""
    full = os.path.join(root, rel)
    if not os.path.isfile(full):
        return []
    name = os.path.basename(rel)
    ext = ext_of(rel)
    out = []

    if ext in CONTENT_EXT:
        out.append(f"{rel}: sieht nach Spielinhalt aus (.{ext}) / looks like game content")
    if FIRMWARE_RE.match(name):
        out.append(f"{rel}: sieht nach Firmware/BIOS/Schlüsseln aus / looks like firmware, BIOS or keys")

    try:
        size = os.path.getsize(full)
    except OSError:
        return out
    if size > MAX_BYTES and rel not in SIZE_EXCEPTIONS:
        out.append(f"{rel}: {size // 1024} kB — zu groß für dieses Repo "
                   f"(Grenze {MAX_BYTES // 1024} kB) / too large for this repository")

    # Verweise nur in Textdateien suchen; Binärdateien sind ohnehin schon oben dran.
    if ext in TEXT_EXT or ext == "":
        try:
            text = open(full, encoding="utf-8", errors="ignore").read()
        except OSError:
            return out
        for m in URL_RE.finditer(text):
            url = m.group(0)
            rest = re.sub(r"^https?://", "", url)
            host = rest.split("/")[0].split(":")[0].split("@")[-1].lower()
            if any(host == a or host.endswith("." + a) for a in ALLOWED_HOSTS):
                continue
            # Interne Dienstnamen (kein Punkt) und Loopback sind Konfigurationsbeispiele,
            # keine Bezugsquellen. / Internal service names and loopback are examples.
            if "." not in host or host in ("localhost",) or host.startswith("127."):
                continue
            pfad = rest.split("/", 1)[1] if "/" in rest else ""
            verdacht = bool(HOST_HINT_RE.search(host))
            # Direkter Dateilink auf Spielinhalt zählt auch bei unauffälligem Host.
            ziel = pfad.split("?")[0].rsplit(".", 1)[-1].lower() if "." in pfad else ""
            if not verdacht and ziel not in CONTENT_EXT:
                continue
            zeile = text[:m.start()].count("\n") + 1
            out.append(f"{rel}:{zeile}: möglicher Verweis auf eine Bezugsquelle "
                       f"/ possible content-source URL: {url[:90]}")
    return out


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if argv:
        dateien = [os.path.relpath(p, root) if os.path.isabs(p) else p for p in argv]
    else:
        dateien = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                dateien.append(os.path.relpath(os.path.join(dirpath, fn), root))

    funde = []
    for rel in dateien:
        if any(part in SKIP_DIRS for part in rel.split(os.sep)):
            continue
        # Dieses Skript selbst enthält naturgemäß die Suchmuster.
        if rel.replace(os.sep, "/") == "scripts/check_content_policy.py":
            continue
        funde += check_file(root, rel)

    if funde:
        print("Inhaltsregel verletzt / content policy violated:", file=sys.stderr)
        for f in funde:
            print("  " + f, file=sys.stderr)
        print("\nRegel: .github/CONTRIBUTING.md — dieses Repository enthält nur Werkzeug.",
              file=sys.stderr)
        print("Rule: .github/CONTRIBUTING.md — this repository contains tooling only.",
              file=sys.stderr)
        return 1
    print(f"Inhaltsregel eingehalten / content policy satisfied ({len(dateien)} Dateien geprüft)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
