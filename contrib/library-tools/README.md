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
