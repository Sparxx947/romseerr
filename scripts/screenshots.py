#!/usr/bin/env python3
"""Erzeugt die Bilder in `docs/img/` aus einem nachbaubaren Vorführstand. (#743)

    python3 scripts/screenshots.py                 # alle Bilder neu
    python3 scripts/screenshots.py --nur 04 10     # nur diese Nummern
    python3 scripts/screenshots.py --behalten      # Instanz stehen lassen (zum Nachsehen)
    python3 scripts/screenshots.py --pruefen       # nichts schreiben, nur vergleichen

WARUM ES DIESES SKRIPT GIBT: Die vierzehn Bilder in `docs/img/` waren Handarbeit. Sie kamen
am 2026-08-15 mit #707 herein und zeigten schon damals **1.4.3**, während 1.5.0 lief; einen
Tag später ersetzte #739 die Emoji-Überschriften, und die Bilder zeigten eine Oberfläche, die
es nicht mehr gab. Ein Bild altert lautlos — niemand liest es beim Zusammenführen gegen.

WARUM EIN VORFÜHRSTAND UND NICHT DIE ECHTE INSTANZ: Jens' Bibliothek hat 293.068 Titel, und
das Repository ist öffentlich. Ein Bild lässt sich nicht durchsuchen; was einmal darauf ist,
findet niemand wieder heraus. Der Stand hier entsteht deshalb aus den Daten weiter unten —
private Inhalte können gar nicht erst hineingeraten, das ist stärker als daran zu denken,
sie unkenntlich zu machen.

WARUM IM SELBEN PROZESS: `app.py` wird als eigenes Modulobjekt geladen (wie in
`tests/conftest.py`), damit Modul-Globale — allen voran der Datenbankpfad — getrennt bleiben
und der Vorführstand über die internen Funktionen gesetzt werden kann. Über `/api/download`
ginge das nicht: Der Endpunkt startet einen ECHTEN Download.

EN: builds docs/img/ from a reproducible demo state. The 14 images were hand-made and went
stale silently — they shipped showing 1.4.3 while 1.5.0 was current, and a day later #739
changed the very headings they showed. The demo state is defined below, so real library
content cannot appear even by accident.
"""
import argparse
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import threading
import time

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.path.join(WURZEL, "docs", "img")

# Feste Zeitbasis. OHNE DIE ist jedes Bild ein anderes: Anfragen zeigen ihre Uhrzeit, und
# ein Lauf um 11:04 ergäbe ein anderes Bild als einer um 11:05 — jeder Durchlauf ein Diff,
# und niemand könnte eine echte Änderung von Rauschen unterscheiden.
JETZT = 1755000000          # 2025-08-12 14:00:00 UTC, fest gewählt


# ---------------------------------------------------------------- Der Vorführstand
#
# Titel bewusst aus dem Bereich, den Archive.org als frei zugänglich führt, und ohne
# Bezug zu einer echten Bibliothek. Wer hier etwas ergänzt: Es landet in einem
# öffentlichen Repository.

BIBLIOTHEK = {
    "snes": ["Super Boulder Dash (Demo).sfc", "Chrono Quest (Homebrew).sfc",
             "Puzzle Garden (Homebrew).sfc"],
    "nes": ["Micro Mages (Homebrew).nes", "Lizard (Demo).nes"],
    "gb": ["Tobu Tobu Girl (Homebrew).gb", "Deadeus (Homebrew).gb"],
    "genesis": ["Tanglewood (Demo).md", "Xeno Crisis (Demo).md"],
    "ps2": ["Homebrew Launcher (Demo).iso"],
    "psx": ["Alanna (Homebrew).bin"],
}

BENUTZER = [
    # (Name, Rolle) — der erste wird über /api/setup angelegt und ist der Admin.
    ("demo", "admin"),
    ("gast", "user"),
]

ANFRAGEN = [
    # (Titel, Plattform, Zustand, Nutzer, Alter in Minuten, Meldung)
    ("Tobu Tobu Girl (Homebrew)", "gb", "done", "demo", 240, ""),
    ("Xeno Crisis (Demo)", "genesis", "downloading", "demo", 12, "42 %"),
    ("Micro Mages (Homebrew)", "nes", "pending", "gast", 5, "wartet auf Freigabe"),
    ("Alanna (Homebrew)", "psx", "error", "gast", 90, "Quelle antwortete nicht"),
]

WUNSCHLISTE = [("Chrono Quest II", "snes"), ("Lizard 2", "nes")]
FAVORITEN = [("Tobu Tobu Girl (Homebrew)", "gb"), ("Xeno Crisis (Demo)", "genesis")]

PROBLEME = [
    ("Ton fehlt im Browser-Spieler", "gb", "audio",
     "Beim Start ist das Bild da, der Ton bleibt stumm. Mit Kopfhörern getestet."),
]

NACHRICHTEN = [
    ("gast", "demo", "Kann ich Xeno Crisis angefragt bekommen?", 45),
    ("demo", "gast", "Läuft schon — steht in der Warteschlange.", 40),
]

def platzhalter_cover(text, ton="#3b2f63"):
    """Ein eingebettetes Ersatzcover als data-URI.

    ECHTE COVER SCHEIDEN AUS: Sie gehören anderen, das Repository ist öffentlich, und ein
    Bild lässt sich nicht durchsuchen — was einmal drin ist, findet niemand wieder heraus.
    Eine leere Fläche sähe dagegen nach einem Fehler aus. Der Platzhalter ist erkennbar
    einer und zeigt trotzdem, wie die Kachel aufgebaut ist.
    """
    import base64
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="264" height="352">'
           f'<rect width="100%" height="100%" fill="{ton}"/>'
           f'<rect x="18" y="18" width="228" height="316" fill="none" stroke="#6f63a8" '
           f'stroke-width="2" stroke-dasharray="6 6"/>'
           f'<text x="132" y="176" fill="#b9b0dd" font-family="sans-serif" font-size="15" '
           f'text-anchor="middle">{text}</text></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


# Hinterlegte Antworten der FREMDEN Quellen.
#
# WARUM NICHT ECHT SUCHEN: Zwei Gründe, und beide wiegen schwer. Erstens wäre kein Lauf
# wie der vorige — Archive.org sortiert nach Downloads, die Trefferliste ändert sich
# täglich, und jeder Lauf ergäbe ein anderes Bild ohne dass sich etwas geändert hätte.
# Zweitens landete fremder Inhalt in einem öffentlichen Repository, ohne dass ihn jemand
# gelesen hat; was auf einem Bild steht, findet niemand mehr heraus.
#
# Die Bilder von Suche und Detailkarte sind damit GESTELLT. Das ist bei Doku-Aufnahmen
# üblich und richtig — aber es gehört gesagt, deshalb steht es hier und in der Doku.
SUCHTREFFER = [
    {"source": "archive", "ref": "tobu-tobu-girl-demo", "title": "Tobu Tobu Girl (Homebrew)",
     "platform": "gb", "size": 96 * 1024, "cover": platzhalter_cover("Ersatzcover"),
     "restricted": False, "extra": "1284"},
    {"source": "archive", "ref": "tobu-tobu-girl-deluxe", "title": "Tobu Tobu Girl Deluxe (Homebrew)",
     "platform": "gb", "size": 512 * 1024, "cover": platzhalter_cover("Ersatzcover"),
     "restricted": False, "extra": "863"},
    {"source": "archive", "ref": "gb-homebrew-sammlung", "title": "Game Boy Homebrew Collection",
     "platform": "gb", "size": 24 * 1024 * 1024, "cover": platzhalter_cover("Ersatzcover", "#2f3f63"),
     "restricted": False, "extra": "402"},
]

DETAIL = {
    "name": "Tobu Tobu Girl", "summary":
        "Ein Arcade-Sprungspiel für den Game Boy: Die Katze fällt nie, sie steigt — "
        "wer den Rhythmus hält, kommt weiter. Freie Veröffentlichung der Entwickler.",
    "first_release_date": 1481068800, "rating": 82.0,
    "genres": ["Arcade", "Plattform"], "platforms": ["Game Boy"],
    "cover": None, "screenshots": [], "similar": [], "collection": "",
}


# ---------------------------------------------------------------- Ansichten
#
# (Nummer, Dateiname, Weg dorthin, Breite, Höhe). Der Weg ist entweder ein Hash-Pfad
# oder eine Funktion, die zusätzlich klicken muss.

BREIT = (1440, 900)
SCHMAL = (420, 860)

ANSICHTEN = [
    ("01", "01-anmeldung",        "#/",             BREIT, "abgemeldet"),
    ("02", "02-suche",            "#/",             BREIT, "suche"),
    ("03", "03-detailkarte",      "#/",             BREIT, "detail"),
    ("04", "04-bibliothek",       "#/library",      BREIT, None),
    ("05", "05-abdeckung",        "#/coverage",     BREIT, None),
    ("06", "06-einstellungen",    "#/settings",     BREIT, None),
    ("07", "07-profil",           "#/settings",     BREIT, "profil"),
    ("08", "08-einfuehrungstour", "#/",             BREIT, "tour"),
    ("10", "10-anfragen",         "#/requests",     BREIT, None),
    ("11", "11-entdecken",        "#/",             BREIT, None),
    ("12", "12-schmal-entdecken", "#/",             SCHMAL, None),
    ("13", "13-schmal-suche",     "#/",             SCHMAL, "suche"),
    ("14", "14-schmal-bibliothek", "#/library",     SCHMAL, None),
    # Die vier Designs teilen sich eine Ansicht und unterscheiden sich nur im Design.
    ("09", "09-design-seerr",     "#/",             BREIT, "design:seerr"),
    ("09", "09-design-glas",      "#/",             BREIT, "design:glass"),
    ("09", "09-design-klar",      "#/",             BREIT, "design:clean"),
    ("09", "09-design-aurora",    "#/",             BREIT, "design:aurora"),
    # Bereiche, die bisher NIE fotografiert waren (#744).
    ("15", "15-probleme",         "#/issues",       BREIT, None),
    ("16", "16-listen",           "#/lists",        BREIT, None),
    ("17", "17-nachrichten",      "#/messages",     BREIT, None),
]

# Die Unterbereiche der Einstellungen (#745). Sie werden als AUSSCHNITT aufgenommen, nicht
# als ganze Seite: In eine Wiki-Seite eingebettet ist ein 1440er Vollbild unlesbar, und die
# Seitenleiste daneben sagt nichts, was die übrigen Bilder nicht schon zeigen.
EINSTELLUNGEN = [
    ("20", "20-set-allgemein",   "general"),
    ("21", "21-set-benachrichtigungen", "notif"),
    ("22", "22-set-verbindungen", "conn"),
    ("23", "23-set-benutzer",    "users"),
    ("24", "24-set-sperrliste",  "blocklist"),
    ("25", "25-set-dienste",     "services"),
    ("26", "26-set-einwurf",     "drop"),
    ("27", "27-set-organisieren", "organize"),
    ("28", "28-set-wartung",     "maint"),
    ("29", "29-set-https",       "tls"),
    ("30", "30-set-ueber",       "about"),
]
ANSICHTEN += [(nr, name, "#/settings", BREIT, "set:" + sec)
              for nr, name, sec in EINSTELLUNGEN]

# Die API hat sehr wohl eine Oberfläche — Redoc unter /api/docs. Sie gehört in docs/API.md.
ANSICHTEN.append(("41", "41-api-docs", "api/docs", BREIT, "roh"))

# Seiten, die nicht zur App gehören, aber dokumentiert sind. Sie MUESSEN hier stehen und
# nicht daneben von Hand entstehen — genau daran ist die erste Bilderserie gealtert.
ANSICHTEN.append(("40", "40-gamepad-pruefung",
                  "contrib/streaming-host/web/gamepad-check.html", (1000, 720), "datei"))


def app_laden(config_dir, roms_dir, jd_watch, jd_out):
    """`app.py` als eigenes Modulobjekt — dasselbe Vorgehen wie in tests/conftest.py.

    JD_WATCH/JD_OUT zeigen auf echte, beschreibbare Ordner. NICHT aus Ordnungsliebe: Ohne
    sie meldet `config_warnings()` „JDownloader-Übergabe unbenutzbar", und dieses Banner
    liegt in jedem Bild über der Oberfläche. Die Warnung wäre dabei sogar richtig — der
    Vorführstand soll sie nur nicht auslösen.
    """
    schluessel = ("ROMSEERR_CONFIG", "ROMSEERR_ROMS", "JD_WATCH", "JD_OUT")
    alt = {k: os.environ.get(k) for k in schluessel}
    os.environ["ROMSEERR_CONFIG"] = config_dir
    os.environ["ROMSEERR_ROMS"] = roms_dir
    os.environ["JD_WATCH"] = jd_watch
    os.environ["JD_OUT"] = jd_out
    if WURZEL not in sys.path:
        sys.path.insert(0, WURZEL)
    spec = importlib.util.spec_from_file_location(
        "app_shot", os.path.join(WURZEL, "app.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["app_shot"] = mod
    spec.loader.exec_module(mod)
    mod.db_init()
    for k, v in alt.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return mod


def bibliothek_anlegen(roms_dir):
    """Leere Dateien mit sprechenden Namen — der Index liest Namen, nicht Inhalte."""
    for slug, dateien in BIBLIOTHEK.items():
        ordner = os.path.join(roms_dir, slug)
        os.makedirs(ordner, exist_ok=True)
        for name in dateien:
            with open(os.path.join(ordner, name), "wb") as f:
                # Ein paar Byte, damit die Größenanzeige nicht überall 0 zeigt.
                f.write(b"\0" * (1024 * 96))


def stand_setzen(mod):
    """Anfragen, Wunschliste, Favoriten, Probleme, Nachrichten — über die internen
    Funktionen, nicht über die API: `/api/download` startet einen ECHTEN Download."""
    for titel, plattform, zustand, nutzer, alter_min, meldung in ANFRAGEN:
        erstellt = JETZT - alter_min * 60
        mod.JOBS.append({
            "id": f"{erstellt}{len(mod.JOBS):03d}", "title": titel, "source": "archive",
            "ref": "demo", "platform": plattform, "size": 96 * 1024,
            "variant": {}, "variant_label": "", "variant_wanted": {},
            "user": nutzer, "state": zustand, "created": erstellt,
            "updated": time.strftime("%H:%M:%S", time.gmtime(erstellt)), "msg": meldung})
    mod.save_jobs()

    # Wunschliste und Favoriten ueber die vorhandenen Funktionen — sie halten die
    # Dubletten-Regel und das Feldformat, ein selbst gebautes dict tut das nicht.
    for titel, plattform in WUNSCHLISTE:
        mod.wishlist_add("demo", titel, plattform)
    for titel, plattform in FAVORITEN:
        mod.fav_add("demo", titel, plattform)

    probleme = mod.load_issues()
    for i, (titel, plattform, art, text) in enumerate(PROBLEME, 1):
        probleme.append({"id": i, "user": "gast", "title": titel, "platform": plattform,
                         "type": art, "message": text, "status": "open",
                         "ts": JETZT - 3600, "comments": []})
    mod.save_issues(probleme)

    # Nachrichten liegen als eigene Tabelle, nicht im kv-Speicher.
    from contextlib import closing
    with closing(mod.db_conn()) as c, c:
        for von, an, text, alter_min in NACHRICHTEN:
            c.execute("INSERT INTO messages(sender,recipient,body,ts,read) VALUES(?,?,?,?,?)",
                      (von, an, text, JETZT - alter_min * 60, 1))


def quellen_stillegen(mod):
    """Die fremden Quellen durch hinterlegte Antworten ersetzen.

    OHNE DAS zeigt das Suchbild „Suche läuft …", bis die Frist abläuft: Archive.org und
    Prowlarr sind aus einem Wegwerf-Stand nicht erreichbar, und das sollen sie auch nicht
    sein. Ersetzt wird an der Quelle, nicht in der Oberfläche — `do_search` mit allem, was
    darin steckt (Dedup, Plattformfilter, Sperrliste, Zwischenspeicher), läuft dadurch
    unverändert und ist auf dem Bild echt zu sehen.
    """
    mod.search_archive = lambda q, limit=30: [dict(t) for t in SUCHTREFFER]
    mod.search_usenet = lambda q, cats=None: []
    mod.search_filehoster = lambda q: []
    mod.igdb_game = lambda titel: dict(DETAIL)
    mod.igdb_rich = lambda titel: dict(DETAIL)
    mod.igdb_cover = lambda titel: platzhalter_cover("Ersatzcover")
    mod.igdb_desc = lambda titel: DETAIL["summary"]
    mod.igdb_similar_games = lambda titel, limit=20: []
    mod.igdb_popular = lambda limit=40: []

    # Entdecken bleibt sonst leer — die Reihen kommen vollständig aus IGDB. Geliefert
    # werden die Titel des Vorführstands: Dann greift die `in_library`-Markierung, und
    # das Bild zeigt genau den Fall, um den es auf der Startseite geht.
    def _beliebt(slug):
        return [{"title": os.path.splitext(n)[0], "cover": platzhalter_cover("Ersatzcover"),
                 "platform": slug, "year": 2018 + i}
                for i, n in enumerate(BIBLIOTHEK.get(slug, []))]

    mod.igdb_popular_platform = lambda pid, limit=20: _beliebt(
        next((s for s, p in mod.IGDB_PLAT.items() if p == pid), ""))
    mod.igdb_popular_genre = lambda gid, limit=20: []


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--nur", nargs="*", default=None, help="nur diese Nummern")
    p.add_argument("--behalten", action="store_true", help="Instanz nicht abräumen")
    p.add_argument("--pruefen", action="store_true", help="nichts schreiben, nur vergleichen")
    a = p.parse_args()

    tmp = tempfile.mkdtemp(prefix="romseerr-bilder-")
    config_dir = os.path.join(tmp, "config")
    roms_dir = os.path.join(tmp, "roms")
    jd_watch = os.path.join(tmp, "jd-watch")
    jd_out = os.path.join(tmp, "jd-out")
    for d in (config_dir, jd_watch, jd_out):
        os.makedirs(d, exist_ok=True)
    bibliothek_anlegen(roms_dir)
    print(f"Vorführstand in {tmp}")

    mod = app_laden(config_dir, roms_dir, jd_watch, jd_out)
    mod.build_index()
    stand_setzen(mod)
    quellen_stillegen(mod)
    print(f"  Bibliothek: {sum(len(v) for v in BIBLIOTHEK.values())} Titel, "
          f"{len(ANFRAGEN)} Anfragen, {len(PROBLEME)} Probleme")

    from werkzeug.serving import make_server
    srv = make_server("127.0.0.1", 0, mod.app, threaded=True)
    faden = threading.Thread(target=srv.serve_forever, daemon=True)
    faden.start()
    basis = f"http://127.0.0.1:{srv.server_port}"
    print(f"  läuft auf {basis}")

    try:
        aufnehmen(basis, a)
    finally:
        srv.shutdown()
        faden.join(timeout=5)
        if a.behalten:
            print(f"Instanz behalten: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


def aufnehmen(basis, a):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    import requests

    s = requests.Session()
    r = s.post(f"{basis}/api/setup", json={"username": "demo", "password": "demo-passwort"},
               timeout=10)
    print(f"  Einrichtung: {r.status_code}")
    s.post(f"{basis}/api/login", json={"username": "demo", "password": "demo-passwort"},
           timeout=10)
    for name, rolle in BENUTZER[1:]:
        s.post(f"{basis}/api/users", json={"username": name, "password": name + "-passwort",
                                           "role": rolle}, timeout=10)

    os.makedirs(ZIEL, exist_ok=True)
    gewaehlt = set(a.nur) if a.nur else None
    geschrieben = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for nummer, name, weg, groesse, sonder in ANSICHTEN:
            if gewaehlt and nummer not in gewaehlt:
                continue
            ctx = browser.new_context(viewport={"width": groesse[0], "height": groesse[1]},
                                      device_scale_factor=1, locale="de-DE")
            seite = ctx.new_page()
            standbild(seite)
            try:
                bild = eine_ansicht(seite, basis, weg, sonder)
                if bild is None:
                    print(f"  {name}: übersprungen ({sonder})")
                    ctx.close()
                    continue
                pfad = os.path.join(ZIEL, name + ".webp")
                if a.pruefen:
                    alt = os.path.exists(pfad)
                    print(f"  {name}: {'vorhanden' if alt else 'FEHLT'}")
                else:
                    Image.open(io.BytesIO(bild)).save(pfad, "WEBP", quality=88, method=6)
                    geschrieben.append(name)
                    print(f"  {name}.webp geschrieben")
            except Exception as e:
                print(f"  {name}: FEHLER {type(e).__name__}: {e}")
            ctx.close()
        browser.close()
    print(f"\n{len(geschrieben)} Bilder geschrieben.")


def standbild(seite):
    """Alles anhalten, was sich von selbst bewegt — sonst ist kein Lauf wie der vorige.

    GEMESSEN: Ohne das waren 4 von 20 Bildern zwischen zwei Läufen verschieden. Zwei
    Ursachen, beide unsichtbar, solange man nur hinsieht:

      * **Animationen.** Aurora hat einen wandernden Verlauf, und auch „Klar" blendet
        Karten ein. Ein Bild fängt sie irgendwo auf halbem Weg.
      * **Der Schreibcursor.** Das Suchfeld bekommt beim Laden den Fokus, und der Cursor
        blinkt — je nach Auslösezeitpunkt ist er auf dem Bild oder nicht.

    Ein Bild, das sich bei jedem Lauf ändert, erzeugt bei jedem Aufruf einen Diff — und
    dann sieht niemand mehr, wenn sich wirklich etwas geändert hat.

    NICHT GEMACHT, WEIL ES SCHADET: `Date.now()` einzufrieren. Der Versuch verschlechterte
    das Ergebnis von 4 auf 8 abweichende Bilder — die Oberfläche rechnet an mehreren
    Stellen mit der Uhr, und eine stehende Uhr bringt sie durcheinander, statt sie zu
    beruhigen. Gemessen, nicht vermutet.
    """
    seite.add_init_script("""
        document.addEventListener('DOMContentLoaded', () => {
            const s = document.createElement('style');
            s.textContent = `*, *::before, *::after {
                animation-duration: 0s !important; animation-delay: 0s !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0s !important; transition-delay: 0s !important;
                scroll-behavior: auto !important; caret-color: transparent !important;
            }`;
            document.head.appendChild(s);
        });
    """)


def eine_ansicht(seite, basis, weg, sonder):
    """Eine Seite ansteuern, vorbereiten, aufnehmen. Gibt PNG-Bytes zurück."""
    if sonder == "datei":
        # Eine Seite aus dem Repository, ohne Server. Der Streaming-Host liefert sie im
        # Betrieb aus; fuer das Bild genuegt die Datei.
        seite.goto("file://" + os.path.join(WURZEL, weg), wait_until="networkidle")
        seite.wait_for_timeout(1200)
        return seite.screenshot()

    if sonder == "roh":
        # Eine Seite ausserhalb der Anwendung (Redoc). Kein Anmelden, kein Assistent,
        # kein Routing — nur hingehen und warten, bis sie steht.
        seite.goto(basis + "/" + weg, wait_until="networkidle")
        seite.wait_for_timeout(2500)
        return seite.screenshot()

    if sonder != "abgemeldet":
        seite.goto(basis, wait_until="domcontentloaded")
        seite.evaluate("""async () => {
            await fetch('/api/login', {method:'POST',
              headers:{'Content-Type':'application/json'},
              body: JSON.stringify({username:'demo', password:'demo-passwort'})});
        }""")

    if sonder and sonder.startswith("design:"):
        # Das Design liest `applyDesign()` BEIM LADEN aus localStorage. Der Wert allein
        # genügt deshalb nicht: `goto` auf denselben Pfad mit anderem Hash lädt die Seite
        # NICHT neu, das Design blieb also mal stehen und wechselte mal — gemessen als
        # 91,5 % Bildunterschied zwischen zwei Läufen, während alles andere stabil war.
        seite.goto(basis, wait_until="domcontentloaded")
        seite.evaluate(f"localStorage.setItem('design', '{sonder.split(':', 1)[1]}')")
        seite.reload(wait_until="networkidle")

    seite.goto(basis + "/" + weg, wait_until="networkidle")
    seite.wait_for_timeout(700)

    # DER ASSISTENT LIEGT SONST ÜBER JEDEM BILD. Er erscheint, solange keine Verbindung
    # eingerichtet ist — im Vorführstand also immer. Nur das Tour-Bild will ihn sehen.
    if sonder != "tour":
        seite.evaluate("""() => {
            try { if (typeof wizFinish === 'function') wizFinish(); } catch (e) {}
            const m = document.getElementById('modal');
            if (m) m.style.display = 'none';
        }""")
        seite.wait_for_timeout(400)

    if sonder == "suche":
        seite.fill("#q", "Tobu Tobu Girl")
        seite.press("#q", "Enter")
        seite.wait_for_timeout(2500)
    elif sonder == "detail":
        seite.fill("#q", "Tobu Tobu Girl")
        seite.press("#q", "Enter")
        seite.wait_for_timeout(2500)
        karte = seite.locator(".card").first
        if karte.count():
            karte.click()
            seite.wait_for_timeout(2000)
        else:
            return None
    elif sonder == "profil":
        # Das Profil hängt im Nutzermenü, nicht in der Seitenleiste — der Eintrag ist
        # unsichtbar, solange das Menü zu ist, und ein Klick darauf läuft in die Frist.
        seite.evaluate("openProfile()")
        seite.wait_for_timeout(1200)
    elif sonder == "tour":
        seite.evaluate("startWizard()")
        seite.wait_for_timeout(900)
        if seite.evaluate("(document.getElementById('modal')||{}).style?.display") != "block":
            return None
    elif sonder and sonder.startswith("set:"):
        seite.evaluate(f"setSection('{sonder.split(':', 1)[1]}')")
        seite.wait_for_timeout(1200)
        seite.evaluate("document.activeElement && document.activeElement.blur()")
        bereich = seite.locator(".setwrap").first
        if not bereich.count():
            return None
        return bereich.screenshot()

    # Fokus weg vom Suchfeld: Der blinkende Cursor ist sonst mal da und mal nicht, und
    # der Fokusrahmen liegt auf jedem Bild, auf dem er nichts zu suchen hat.
    if sonder not in ("suche", "abgemeldet"):
        seite.evaluate("document.activeElement && document.activeElement.blur()")
    return bis_ruhig(seite)


def bis_ruhig(seite, versuche=12, pause=350):
    """Aufnehmen, bis zwei Bilder hintereinander gleich sind.

    WARUM NICHT EINFACH LÄNGER WARTEN: Weil „lange genug" keine Eigenschaft der Seite ist,
    sondern eine Wette. Gemessen an zwei vollen Läufen mit fester Wartezeit wichen **6 von
    20** Bildern ab — und bei jedem Lauf ANDERE sechs. Das ist die Signatur eines
    Wettlaufs, nicht die einer Animation: Logos, Zählerstände und Abzeichen kommen
    nachgeladen, und `networkidle` gilt schon, bevor die Oberfläche sie eingebaut hat.

    Zwei gleiche Aufnahmen hintereinander sind dagegen eine Aussage ÜBER DIE SEITE: Sie
    bewegt sich nicht mehr. Kostet ein paar hundert Millisekunden je Bild und macht die
    Zeitwahl überflüssig.
    """
    letztes = None
    for _ in range(versuche):
        jetzt = seite.screenshot()
        if jetzt == letztes:
            return jetzt
        letztes = jetzt
        seite.wait_for_timeout(pause)
    return letztes


if __name__ == "__main__":
    main()
