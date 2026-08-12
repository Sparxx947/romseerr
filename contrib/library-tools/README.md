# Bibliothek umbauen / Reshaping the library

*Deutsch zuerst, English below.*

---

## Deutsch

### Das Problem: drei Programme, drei Zählweisen

RomM, Romseerr und RetroNAS lesen **denselben Ordner** und kommen zu verschiedenen
Ergebnissen:

| | zählt |
|---|---|
| **RetroNAS** | nichts — es stellt nur bereit, die Struktur darunter ist ihm gleich |
| **RomM** | **jeden Eintrag der ersten Ebene** als genau ein Spiel |
| **Romseerr** | zwei Ebenen tief, **jede Datei** als Titel |

Gemessen an einer echten Bibliothek: RomM sah unter `c64` genau **75 Spiele** — darunter
`C64.GIF`, `BASIC.ROM` und einen Ordner `OneLoad64-Games-Collection-v5` mit 27.451 Dateien,
gezählt als **ein** Spiel. Romseerr sah in denselben Daten **23.802 Titel**.

Keins der beiden ist falsch konfiguriert. Sie erwarten schlicht verschiedene Formen.

### Die Zielform erfüllt alle drei zugleich

```
<plattform>/Spiel.rom              eine Datei  = ein Spiel
<plattform>/Spiel/                 ein Ordner  = ein Spiel
    Disk 1.d64                                   (Multi-Disk, DOS-Installation, PS3-Titel)
    Disk 2.d64
```

Ebene 1 ist damit die **Spielebene** — genau das erwartet RomM. Romseerr kommt damit
ebenso zurecht, RetroNAS ohnehin.

### Die eine Entscheidung, auf die es ankommt

Ist ein Ordner **ein Spiel** oder **eine Sammlung**? Beide Fehlrichtungen kosten:

- Sammlung fälschlich als Spiel → Hunderte Titel bleiben unsichtbar
- Multi-Disk-Spiel fälschlich als Sammlung → es zerfällt in Einzeldateien

Drei Wege führen zur Antwort, in dieser Reihenfolge:

1. **Die Plattform kennt nur Spielordner.** Bei DOS, PS3, ScummVM, Wii und ähnlichen
   besteht ein Titel immer aus vielen Dateien. Dort taugt die Dateizahl nicht.
2. **Wenige Dateien, die auf denselben Titel reduzieren.** Nach Abzug des
   Datenträger-Markers — `(Disk 1)`, `(Side A)`, `[Disc 2]`, `(Tape 1 of 3)` — bleibt
   derselbe Name übrig. Das ist ein Multi-Disk-Spiel.
3. **Sonst: Sammlung.**

**Der Datenträger-Marker ist das einzige verlässliche Zeichen.** Ein gemeinsamer
Namensanfang genügt **nicht**: `VC Songs-Cartridge - Inventio-Pac` und
`VC Songs-Cartridge - The Mad Boogy` teilen 22 Zeichen und sind zwei verschiedene Demos.
Am Bestand nachgemessen, nicht angenommen.

### Benutzung

```bash
# Eine Plattform, erst als Vorschau — es wird nichts verschoben
retronas-organisieren --trocken /roms c64

# Wirklich umbauen; jeder Schritt wird protokolliert
retronas-organisieren /roms c64

# Alles, kleinste Plattform zuerst
retronas-organisieren --alle /roms

# Zurück: das Protokoll Schritt für Schritt rückwärts
retronas-organisieren --zurueck /roms/.umbau/c64-20260810-134827.jsonl

# Nach einem Abbruch: derselbe Befehl setzt fort, wo er aufgehört hat
retronas-organisieren --alle /roms

# Doch von vorn
retronas-organisieren --alle --neu /roms
```

**Ein abgebrochener Lauf fängt nicht von vorn an.** `<roms>/.umbau/fortschritt.json` hält
fest, welche Plattformen durch sind; ein erneuter Aufruf überspringt sie und sagt beim
Start, wie viele das sind. Das ist keine Kosmetik: Ein voller Lauf dauert hier über 19
Stunden, und `amiga` allein sind 440.564 Dateien — nach einem Absturz alles zu wiederholen
kostet einen Tag.

Zwei Feinheiten:

- **Die beim Abbruch laufende Plattform wird wiederholt.** Mitten in ihr aufzusetzen
  bräuchte einen Stand je Eintrag; der Durchlauf ist dagegen weitgehend wiederholbar — was
  schon die richtige Form hat, wird nicht angefasst. Der Preis ist ein Durchgang, keine
  doppelte Arbeit.
- **Ein abgeschlossener Lauf ist kein Wiederaufsetzpunkt.** Wer nach dem Ende erneut
  startet, will neu bauen, nicht nichts tun.
- **Eine abgestürzte Plattform gilt nicht als erledigt.** Der Lauf macht mit der nächsten
  weiter — ein unlesbarer Ordner darf keine 19 Stunden kosten —, aber sie bleibt in der
  Wiederaufsetzliste und wird beim nächsten Aufruf wiederholt. Die Schlussmeldung nennt
  sie beim Namen, und `fertig` wird nicht gesetzt:

  ```
  === 72 VON 74 PLATTFORMEN FERTIG, 2 MIT FEHLER: c64, amiga ===
      c64: RuntimeError: kein freier Name fuer VERSION.NFO
      amiga: UnicodeEncodeError: '\udce0' surrogates not allowed
    Erneut versuchen: derselbe Aufruf setzt genau bei diesen fort.
  ```

  **Ein Fehler nennt seine Datei (#424).** Die Zeile `FEHLER: 3` am Ende einer Plattform
  war lange die einzige Spur — bei 62.894 Dateien und ohne einen einzigen Namen. Jetzt
  steht jeder Fehler mit Pfad, Schritt und Grund auf dem Bildschirm **und** als
  `{"art": "fehler", …}` im Protokoll:

  ```
      FEHLER [datei_pruefsumme] /roms/c64/kaputt.d64: Input/output error
  ```

  Das ist kein Schönheitsfehler gewesen. Eine Datei ohne Prüfsumme wird beim
  Dublettenabgleich **übersprungen**, nicht entfernt — eine echte Dublette kann also
  stehen bleiben, und ohne den Namen findet das hinterher niemand mehr.

  *An error now names its file. A file that cannot be checksummed is skipped for
  de-duplication, so a real duplicate may survive — and nothing recorded which one.*

  Der Rückgabewert ist dann `1`. **Warum das zählt (#397):** Am 2026-08-11 meldete der
  volle Lauf `ALLE 74 PLATTFORMEN FERTIG`, während genau diese zwei abgestürzt waren —
  beide unter den drei größten. Weil der Fortschritt bedingungslos eingetragen wurde,
  hätte ein Fortsetzen ausgerechnet sie übersprungen: Der Rückweg war darauf trainiert,
  die Fehlschläge zu ignorieren.

**Zwei Abstürze, die dahintersteckten** — beide nachgemessen, nicht vermutet:

- **`kein freier Name`**: Die Suche nach einem freien Namen lief `(2 … 9999)` und warf
  danach. Unter `c64` liegen 9.999 Dateien `VERSION (i).NFO` — `VERSION.NFO` ist Beiwerk
  und steckt in jedem zweiten Set. Die Grenze beschränkte nicht die Suche, sondern die
  Bibliothek. Sie ist weg; zusätzlich merkt sich die Suche, wo sie zuletzt endete, statt
  für den n-ten Namen n Anfragen ans Dateisystem zu stellen (über 9.999 Dateien rund 50
  Millionen, auf drehenden Platten).
- **`surrogates not allowed`**: Ein Dateiname ist unter Linux eine Bytefolge, kein Text.
  Unter `amiga` tragen 21 Namen Bytes, die kein gültiges UTF-8 sind (`catal\xe0` aus
  `MUI38/MUI/Locale/Catalogs`). Python liest sie mit Ersatzzeichen, kann sie aber nicht
  als UTF-8 schreiben — und daran starb ausgerechnet das **Protokoll**, der einzige
  Rückweg. Protokoll wird jetzt mit `surrogateescape` geschrieben und gelesen; das
  ursprüngliche Byte geht unverändert hindurch, `--zurueck` findet den Namen wieder.

Der `Mixed`-Ordner — eine Sammelablage ohne Plattformzuordnung — wird getrennt aufgelöst:

```bash
retronas-mixed-sortieren --trocken /roms
retronas-mixed-sortieren /roms
```

**Der Zusammenhang kann zuordnen, wo die Endung es nicht kann.** Unter `Mixed` lagen 198
`.bin` — und der Sortierer ordnete von 707 Dateien genau **eine** zu, weil `.bin` auf einem
Dutzend Systemen vorkommt. Die Dateien tragen ihre Herkunft aber im Namen:

    Shark! Shark! (1982)(Mattel).bin                       16.384
    Mountain Madness - Super Pro Skiing (1987)(Intv Corp)  16.384

**Herausgeber + Jahr + Größe** zusammen sind eine Signatur. Die Endung bleibt unzugeordnet;
was trägt, ist die Kombination — der Grundsatz bleibt damit unangetastet. Gemessen: **170**
statt einer Datei.

*Bekannte Grenze:* Der Bestand stammt aus einem Satz „Mattel Intellivision & Aquarius".
Beide Systeme sind von Mattel und nutzen `.bin`. Am Namen erkennbare Aquarius-Titel werden
ausgeschlossen; weiter trägt die Regel nicht. Jeder Schritt steht im Protokoll und lässt
sich mit `--zurueck` zurücknehmen.

Der Sortierer ordnet **nur eindeutige Endungen** zu. `.bin`, `.iso`, `.rom` und `.img`
bleiben bewusst liegen: Sie kommen auf einem Dutzend Plattformen vor, und eine falsche
Zuordnung ist teurer als eine ausgelassene — der Titel läge danach unter der falschen
Konsole und fiele niemandem auf, während eine liegengebliebene Datei sichtbar bleibt.

### Beiwerk landet in `_beiwerk/`

Ebene 1 ist die **Spielebene** — RomM zählt dort jeden Eintrag als genau ein Spiel. Bilder,
Textdateien und `.nfo` standen deshalb als „Spiele" darin: unter `c64` waren es **10.726
von 57.615 Einträgen**, fast jeder fünfte, davon allein 10.018 `.nfo`.

Sie werden jetzt in einen Unterordner `_beiwerk/` je Plattform eingesammelt. Nichts wird
gelöscht: Wer die Textdatei zu einem Spiel sucht, findet sie weiterhin — sie zählt nur
nicht mehr als Titel.

Der Name beginnt mit einem **Unterstrich, nicht mit einem Punkt**. Ein versteckter Ordner
wäre für Romseerr unsichtbar, aber RomM zählt ihn trotzdem — dann stünde dort wieder ein
„Spiel", nur ein anderes.

**Arcade ist ausgenommen.** Dort ist das Archiv das Spiel, und MAME-Romsets erwarten ihre
Begleitdateien an Ort und Stelle.

### Endungslose Programme benennen

Auf der Spielebene liegen **4.843 Dateien ohne Endung** (c64 4.173, amiga 366, vic-20 303).
RomM zählt jede als ein Spiel, und startbar ist keine — kein Emulator erkennt eine Datei
ohne Endung.

Es sind keine Reste, sondern **Commodore-PRG-Dateien**. Die ersten zwei Bytes sind die
Ladeadresse:

    adressdaten   01 18 …    $1801    VIC-20 +8K
    Demo          01 12 …    $1201    VIC-20 +3K
    magic draw    01 20 …    $2001    VIC-20 BASIC

```bash
retronas-prg-benennen --trocken /roms vic-20    # zeigen, nichts ändern
retronas-prg-benennen /roms vic-20              # umbenennen, mit Protokoll
retronas-prg-benennen --alle /roms              # alle Commodore-Plattformen
retronas-prg-benennen --zurueck /roms/.umbau/prg-….jsonl
```

**Was keine bekannte Ladeadresse trägt, bleibt liegen.** Von 303 Dateien unter `vic-20`
tragen 233 eine dokumentierte Adresse; die übrigen 70 haben Werte wie `$10f1`, die keiner
Maschine entsprechen. Eine `readme` in `readme.prg` zu verwandeln machte aus einer
harmlosen Datei ein kaputtes Spiel.

Zusätzlich muss **Ladeadresse plus Größe in 64 KB passen** — sonst ist es kein
Commodore-Programm, sondern eine große Datei mit zufällig passenden ersten Bytes.

### Was die Werkzeuge nicht tun

- **Keine Plattformordner umbenennen.** Die Namen stammen von RetroNAS.
- **Nichts löschen außer belegten Dubletten** — gleiche Prüfsumme, gleicher Inhalt.
- **Keine Archive anfassen, wo Archive die richtige Form sind**: Arcade, MAME, Neo Geo
  und CPS erwarten die `.zip` als Spiel. Diese Plattformen stehen in `ARCHIV_BLEIBT`.

### Vor dem Lauf

- **Er dauert.** An einer 5-TB-Bibliothek über 19 Stunden. Der Durchsatz hängt an der
  Dateizahl, nicht an der Datenmenge: Eine Plattform mit einzeln gepackten ROMs braucht
  Stunden für wenige Gigabyte, weil jedes Archiv entpackt wird.
- **Ein Protokoll je Plattform** landet unter `<roms>/.umbau/`. Es ist die Grundlage für
  `--zurueck`.
- **Der Ordner `.umbau` beginnt mit einem Punkt** — Romseerr überspringt versteckte
  Ordner, sonst erschienen die Protokolldateien als Plattform mit eigenen „Titeln".

---

## English

### The problem: three programs, three ways of counting

RomM, Romseerr and RetroNAS read **the same folder** and disagree:

| | counts |
|---|---|
| **RetroNAS** | nothing — it only serves; the structure below is irrelevant to it |
| **RomM** | **every first-level entry** as exactly one game |
| **Romseerr** | two levels deep, **every file** as a title |

Measured against a real library: RomM saw exactly **75 games** under `c64` — among them
`C64.GIF`, `BASIC.ROM` and a folder `OneLoad64-Games-Collection-v5` holding 27,451 files,
counted as **one** game. Romseerr saw **23,802 titles** in the same data.

Neither is misconfigured. They simply expect different shapes.

### The target shape satisfies all three

```
<platform>/Game.rom               one file   = one game
<platform>/Game/                  one folder = one game
    Disk 1.d64                                 (multi-disk, DOS install, PS3 title)
    Disk 2.d64
```

Level 1 becomes the **game level**, which is what RomM expects. Romseerr handles it too,
and RetroNAS never cared.

### The one decision that matters

Is a folder **one game** or **a collection**? Both errors cost:

- a collection taken for a game → hundreds of titles stay invisible
- a multi-disk game taken for a collection → it falls apart into single files

Three routes to the answer, in order:

1. **The platform only ever has game folders.** For DOS, PS3, ScummVM, Wii and similar a
   title always consists of many files, so the file count is no criterion there.
2. **Few files that reduce to the same title.** With the medium marker removed —
   `(Disk 1)`, `(Side A)`, `[Disc 2]`, `(Tape 1 of 3)` — the same name remains. That is a
   multi-disk game.
3. **Otherwise: a collection.**

**The medium marker is the only reliable signal.** A shared prefix is **not** enough:
`VC Songs-Cartridge - Inventio-Pac` and `VC Songs-Cartridge - The Mad Boogy` share 22
characters and are two different demos. Measured against the library, not assumed.

### Usage

```bash
retronas-organisieren --trocken /roms c64      # preview, nothing is moved
retronas-organisieren /roms c64                # do it, every step logged
retronas-organisieren --alle /roms             # everything, smallest platform first
retronas-organisieren --zurueck /roms/.umbau/c64-….jsonl   # step back through the log
retronas-organisieren --alle /roms             # after an abort: resumes where it stopped
retronas-organisieren --alle --neu /roms       # start over regardless
```

**An aborted run does not start from scratch.** `<roms>/.umbau/fortschritt.json` records
which platforms are done; a later invocation skips them and says how many at startup. A
full pass here takes over 19 hours and `amiga` alone is 440,564 files — repeating all of it
after a crash costs a day.

Two details: the platform that was **running** when the abort happened is redone, because
resuming inside one would need per-entry state while a pass is largely repeatable; and a
**finished** run is not a resume point, since starting again after the end means rebuild,
not do nothing.

**A platform that crashed does not count as done.** The run carries on with the next one —
an unreadable folder must not cost 19 hours — but it stays on the resume list and is
retried by the next invocation. The closing line names it, `fertig` is not set, and the
exit code is `1`:

```
=== 72 VON 74 PLATTFORMEN FERTIG, 2 MIT FEHLER: c64, amiga ===
    c64: RuntimeError: kein freier Name fuer VERSION.NFO
    amiga: UnicodeEncodeError: '\udce0' surrogates not allowed
  Erneut versuchen: derselbe Aufruf setzt genau bei diesen fort.
```

**Why this matters (#397):** on 2026-08-11 the full pass reported `ALLE 74 PLATTFORMEN
FERTIG` while exactly those two had crashed — both among the three largest. Because
progress was recorded unconditionally, a resume would have skipped precisely them: the
recovery path had been taught to ignore the failures.

**The two crashes behind it**, both measured rather than assumed:

- **`kein freier Name`** — the search for a free name ran `(2 … 9999)` and then raised.
  `c64` holds 9,999 files named `VERSION (i).NFO`; `VERSION.NFO` is an ancillary file
  present in every other set. The bound limited the library, not the search. It is gone,
  and the search now remembers where it stopped instead of asking the filesystem n times
  for the n-th name — about 50 million lookups over 9,999 files, on spinning disks.
- **`surrogates not allowed`** — a filename on Linux is a byte string, not text. Under
  `amiga`, 21 names carry bytes that are not valid UTF-8 (`catal\xe0` from
  `MUI38/MUI/Locale/Catalogs`). Python reads them with surrogate escapes but cannot write
  them as UTF-8 — and what died on that was the **log**, the one way back. The log is now
  written and read with `surrogateescape`, so the original byte passes through untouched
  and `--zurueck` finds the name again.

The `Mixed` folder — a holding area with no platform — is resolved separately:

```bash
retronas-mixed-sortieren --trocken /roms
retronas-mixed-sortieren /roms
```

**Context can place what an extension cannot.** `Mixed` held 198 `.bin` files and the
sorter placed exactly **one** of 707, because `.bin` occurs on a dozen systems. But the
files carry their origin in the name — **publisher + year + size** together are a
signature. The extension stays unmapped; the combination is what carries the platform, so
the principle is untouched. Measured: **170** files instead of one.

*Known limit:* the set is "Mattel Intellivision & Aquarius" — both are Mattel and both use
`.bin`. Aquarius titles recognisable by name are excluded; the rule reaches no further.
Every step is logged and reversible with `--zurueck`.

It only maps **unambiguous extensions**. `.bin`, `.iso`, `.rom` and `.img` are deliberately
left alone: they occur on a dozen platforms, and a wrong mapping costs more than a skipped
one — the title would sit under the wrong console unnoticed, while a skipped file stays
visible.

### Ancillary files go to `_beiwerk/`

Level 1 is the **game level** — RomM counts every entry there as exactly one game, so
images, text files and `.nfo` were being counted as games: under `c64` that was **10,726 of
57,615 entries**, nearly one in five, 10,018 of them `.nfo` alone.

They are now collected into a `_beiwerk/` subfolder per platform. Nothing is deleted — the
text file belonging to a game is still there, it simply no longer counts as a title.

The name starts with an **underscore, not a dot**: a hidden folder would be invisible to
Romseerr, but RomM would still count it, putting a "game" back on level 1.

**Arcade is exempt**: there the archive is the game, and MAME romsets expect their
companion files in place.

### Naming extensionless programs

The game level holds **4,843 files with no extension** (c64 4,173, amiga 366, vic-20 303).
RomM counts each as a game, and none can be launched — no emulator recognises a file
without an extension.

They are not leftovers but **Commodore PRG files**; the first two bytes are the load
address (`$2001` VIC-20 BASIC, `$1201` +3K, `$1801` +8K, `$0801` C64).

```bash
retronas-prg-benennen --trocken /roms vic-20
retronas-prg-benennen --alle /roms
retronas-prg-benennen --zurueck /roms/.umbau/prg-….jsonl
```

**Anything without a known load address is left alone.** Of 303 files under `vic-20`, 233
carry a documented address; the other 70 hold values like `$10f1` that match no machine.
Renaming a readme to `readme.prg` would turn a harmless file into a broken game.

Load address plus size must also fit in 64 KB, which catches large files whose first two
bytes happen to match.

### What the tools do not do

- **Never rename platform folders.** Those names come from RetroNAS.
- **Delete nothing except proven duplicates** — same checksum, same content.
- **Leave archives alone where an archive is the correct shape**: arcade, MAME, Neo Geo and
  CPS expect the `.zip` to be the game. Those platforms are listed in `ARCHIV_BLEIBT`.

### Before running

- **It takes time.** Over 19 hours on a 5 TB library. Throughput follows the file count,
  not the data volume: a platform of individually compressed ROMs takes hours for a few
  gigabytes, because every archive is unpacked.
- **One log per platform** lands in `<roms>/.umbau/`. It is what `--zurueck` reads.
- **The `.umbau` folder starts with a dot** — Romseerr skips hidden folders, or the log
  files would appear as a platform with "titles" of their own.
