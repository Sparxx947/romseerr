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

Vier Wege führen zur Antwort, in dieser Reihenfolge:

1. **Die Plattform kennt nur Spielordner.** Bei DOS, PS3, ScummVM, Wii und ähnlichen
   besteht ein Titel immer aus vielen Dateien. Dort taugt die Dateizahl nicht.
2. **Der Ordner ist ein Abbild-Set.** Eine `.gdi`, `.cue` oder `.m3u` **nennt ihre
   Dateien**, und die liegen daneben. Struktur, kein Namensvergleich.
3. **Wenige Dateien, die auf denselben Titel reduzieren.** Nach Abzug des
   Datenträger-Markers — `(Disk 1)`, `(Side A)`, `[Disc 2]`, `(Tape 1 of 3)` — bleibt
   derselbe Name übrig. Das ist ein Multi-Disk-Spiel.
4. **Sonst: Sammlung.**

#### „Kein Archiv" ist kein Fehlschlag (#447)

Unter `amiga` liegen Dateien, die `.ZIP` oder `.LZH` heißen und keine sind — kein
`PK\x03\x04`, kein LHA-Kopf, sondern Amiga-Cruncher-Formate mit Kennungen wie
`85 15 02 41` oder `95 0a 02 41`.

Sie als *„Archiv ließ sich nicht entpacken"* zu melden ist doppelt falsch: Es behauptet
einen Schaden, den es nicht gibt, **und begräbt die echten**. Gemessen: **49 von 78**
Meldungen waren solche Dateien, und darunter lagen genau **zwei** wirklich beschädigte
Archive.

Der Lauf trennt deshalb zwei Befunde, weil sie verschiedene Antworten verlangen:

| Befund | Antwort |
|---|---|
| beschädigtes Archiv | neu beschaffen |
| kein Archiv | umbenennen — die Datei ist heil, nur falsch benannt |

**Ohne Formatliste.** Die Kennungen sind uneinheitlich, eine Liste wäre Raterei. Die Frage
*„erkennt ein Entpacker den Inhalt überhaupt?"* ist dagegen messbar: `lsar` antwortet auf
ein unbekanntes Format mit `Couldn't recognize the archive format`. Fehlt `lsar`, gilt im
Zweifel „Archiv" — lieber ein Fehlalarm als eine still übersprungene Datei.

#### Satzmitglieder werden nie als Dublette gelöscht (#467)

Schritt 3b entfernt **bitgleiche** Dateien auf Ebene 1. Bei CD-Titeln ist das falsch: Spur 01
ist bei vielen Spielen identisch — eine leere Datenspur oder ein Kopierschutzhinweis. Aus
dem Laufprotokoll, wörtlich:

```
dublette_entfernt  turbografx-cd/Monster Lair (USA) (Track 01).bin
                   gleich_wie  turbografx-cd/Valis II (USA) (Track 01).bin
```

Zwei verschiedene Spiele. Danach nennt Monster Lairs `.cue` eine Datei, die es nicht mehr
gibt. Unter `dc` sind so **375 Dateien gelöscht** worden — deshalb sind von 213 Titeln nur
13 aus dem Protokoll rekonstruierbar: Der Rest ist weg, nicht verlegt.

**Bitgleichheit macht zwei Spuren nicht austauschbar.** Was eine Abbildliste im selben
Ordner nennt, ist von der Dublettenerkennung ausgenommen; der Lauf sagt am Ende, wie viele
Dateien er deshalb verschont hat.

#### Warum Abbild-Sets eine eigene Regel brauchen (#462)

Ein Dreamcast-Titel sieht so aus:

```
Bangai-O (PAL)(M3)/Bangai-O v1.001 (2000)(Virgin)(PAL)(M3)[!].gdi
Bangai-O (PAL)(M3)/track01.bin   track02.raw   track03.bin
```

Regel 3 fragt nach Namensgleichheit und findet vier verschiedene Stämme. Sie **kann** das
nicht sehen, denn hier ist die Namensgleichheit nicht bloß abwesend, sie ist *absichtlich*
abwesend: Die Spuren heißen bei jedem Spiel gleich.

Ohne Regel 2 galt der Ordner als Sammlung und wurde flachgelegt. Die generischen Spurnamen
kollidierten und wurden zu `track01 (53).bin` — während die `.gdi` weiterhin `track01.bin`
nennt. **Alle 138 Dreamcast-Titel zeigten danach auf dieselbe Datei.** Am Emulator gemessen
als tausende `W[GDROM]: Sector Read miss`; Flycast blieb im Dreamcast-BIOS stehen und lud
nie ein Spiel.

Drei Bedingungen, alle nötig — jede fängt einen eigenen Fehlschluss ab:

| Bedingung | ohne sie |
|---|---|
| mindestens eine Abbildliste auf oberster Ebene | jeder Ordner wäre ein Spiel |
| alle Listen reduzieren auf **einen** Titel | zwei verschiedene Spiele in einem Ordner würden verschmolzen |
| jede genannte Datei liegt daneben | ein unvollständiger Ordner würde als heil durchgereicht |

Die Prüfung steht **vor** der Dateizahl-Schranke: `Bangai-O` hatte 38 Dateien, die Schranke
liegt bei 12. Dahinter wäre die Regel vorhanden und wirkungslos.

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

**Die Tabelle wächst nur gegen einen Befund.** Nach dem Gesamtumbau hielt `Mixed` 536
Dateien, und der Trockenlauf verschob nichts — zu Recht, bis auf eine Endung:

| | | |
|---|---|---|
| `.jpg` 52 · `.txt` 51 · `.html` 41 · `.wav` 41 | Beiwerk | bleibt |
| `.exe` 29 | Windows-Programme | bleibt |
| `.vpl` 17 · `.vrs` 14 | VICE-Konfiguration | bleibt |
| `.bin` 28 | mehrdeutig | bleibt **mit Absicht** |
| `.caq` 13 | Mattel Aquarius | **fehlte in der Tabelle** (#515) |

Die 13 `.caq` stammen aus derselben `Mattel Intellivision & Aquarius ROMs`-Sammlung, deren
Intellivision-Hälfte über `.int` sauber einsortiert wurde; der Ordner `aquarius` existierte
längst. Zwischen 52 Werbescans fällt ein Kassettenabzug niemandem auf — genau dafür gibt es
die Tabelle.

`.cas` bleibt draußen: Das Kassettenformat tragen MSX und ColecoVision ebenfalls.

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

### Abbildlisten prüfen: `rom-abbilder-pruefen`

Ein Disc-Abbild besteht aus einer kleinen Textliste (`.gdi`, `.cue`, `.m3u`) und mehreren
Datendateien. Fehlt eine davon, ist der Titel unspielbar — und zwar **lautlos**: In der
Bibliothek steht er weiterhin, RomM zählt ihn mit, und erst der Emulator sagt
`Sector Read miss`.

```bash
rom-abbilder-pruefen /roms                    # nur berichten, nichts anfassen
rom-abbilder-pruefen /roms psx --reparieren   # eindeutige Verweise umschreiben
rom-abbilder-pruefen /roms --aussortieren     # Unbrauchbares nach _defekt/ VERSCHIEBEN
```

#### Zwei Fragen, nicht eine

Die naheliegende Prüfung — *nennt die Liste Dateien, die es nicht gibt?* — hat eine blinde
Stelle, und die wurde am Bestand gemessen:

```
/roms/dc  ->  0 Defekte gemeldet, obwohl ALLE 138 Titel kaputt waren
```

Denn dort waren die Spielordner flachgelegt worden, und die Spuren heißen bei jedem
Dreamcast-Spiel `track01.bin`. Im flachen Ordner **existiert** der Name also — jede Liste
fand einen Treffer, nur den falschen. **Namenspräsenz ist nicht dasselbe wie die richtige
Datei.**

Deshalb stellt das Werkzeug zwei Fragen:

| Frage | findet |
|---|---|
| **fehlend** — nennt die Liste Dateien, die nicht daneben liegen? | verlorene oder umbenannte Spuren |
| **geteilt** — nennen *mehrere* Listen im selben Ordner dieselbe Datei? | den Kollisionsschaden aus #462 |

Am Bestand gemessen: 11 eindeutig lösbar, 106 mit wirklich fehlenden Daten, 83 geteilte
Verweise (alle unter `dc`).

#### Was es repariert — und was bewusst nicht

Umgeschrieben wird nur, wenn die gemeinte Datei **eindeutig** ist: Sie trägt den Stamm der
Liste selbst (der häufige Fall umbenannter Rips), oder sie ist die einzige Datei dieser
Endung, **die keine andere Liste beansprucht**.

Der Nachsatz ist der Punkt. Ohne ihn genügte „genau eine `.bin` im Ordner" — und eine
`.cue`, deren Daten wirklich fehlen, wurde auf das Abbild eines **fremden** Spiels
umgebogen. An einem Probebestand aufgefallen, bevor das Werkzeug den echten sah. **Ein
geratener Verweis sieht heil aus und ist es nicht**; das ist schlechter als ein sichtbar
kaputter, weil danach niemand mehr hinsieht.

`--aussortieren` **verschiebt** nach `<plattform>/_defekt/` und löscht nichts. Die
vorhandenen Spuren sind echte Daten; ob sie ersetzbar sind, entscheidet der Betreiber.
Jede Änderung steht mit Quelle und echtem Ziel in `.abbildpruefung/<plattform>-<zeit>.jsonl`,
und vor jedem Umschreiben bleibt eine `.vor-fix`-Sicherung liegen.

Eine `.m3u` mit Netzadressen (Radio-Streams) gilt **nicht** als defektes Abbild.

### Was die Werkzeuge nicht tun

- **Keine Plattformordner umbenennen.** Die Namen stammen von RetroNAS.
- **Nichts löschen außer belegten Dubletten** — gleiche Prüfsumme, gleicher Inhalt.
- **Keine Archive anfassen, wo Archive die richtige Form sind**: Arcade, MAME, Neo Geo
  und CPS erwarten die `.zip` als Spiel. Diese Plattformen stehen in `ARCHIV_BLEIBT`.

### Das Protokoll ist der Rückweg — auch bei gelöschten Dateien

Am 2026-08-12 waren 256 Disc-Abbilder kaputt, darunter **alle 138 Dreamcast-Titel**.
Wiederhergestellt wurden davon 230 — **ohne einen Byte zu laden**. Das ging nur, weil das
Protokoll mehr festhält, als man beim Lesen des Quelltextes vermutet.

#### Verschieben: Quelle und **echtes** Ziel

```json
{"art":"verschoben",
 "von":"/roms/dc/Bomber Hehhe! (JP)/track01.bin",
 "nach":"/roms/dc/track01 (2).bin"}
```

Das Ziel steht **mit Kollisionssuffix** darin. Ein Flachlegen ist damit Datei für Datei
umkehrbar, auch wenn hundert Spiele dieselben Spurnamen tragen.

#### Löschen: die Datei, mit der sie identisch war

```json
{"art":"dublette_entfernt",
 "pfad":"/roms/dc/track03 (67).bin",
 "gleich_wie":"/roms/dc/track03 (7).bin",
 "sha256":"09b26522…"}
```

**Gelöscht wird nur bei Bitgleichheit.** Eine gelöschte Datei ist deshalb nicht verloren,
solange ihr Zwilling existiert — sie lässt sich **kopieren**, und die Kopie ist
konstruktionsbedingt exakt. In allen 555 Fällen war die Vorlage noch da.

#### Zwei Bedingungen, ohne die es schiefgeht

**Nur Satzmitglieder zurückholen.** 161.406 der gelöschten Dateien sind *echte* Dubletten
(`Krull (CCE) (2).a26` neben `Krull (CCE).a26`) und müssen gelöscht bleiben. Die Zahl der
„rettbaren" fiel von 1078 auf 180, als diese Bedingung richtig angewandt wurde: Dateien wie
`Alien Breed 3D (Track 1) (2).bin` sind Zweitkopien, die keine `.cue` nennt. Maßgeblich ist
allein, **ob eine Abbildliste im Zielordner den Namen nennt**.

**Die Prüfsumme nachrechnen, nicht der Protokollzeile glauben** — zweimal: vor dem Kopieren
(ist die Vorlage noch die Datei, die das Protokoll beschreibt?) und danach (ist die Kopie
heil angekommen?).

#### Wann es *nicht* geht

Ist der Zwilling ebenfalls weg, ist die Datei weg. Das Protokoll kann nur zeigen, wo etwas
war und womit es identisch war — es speichert keine Daten.

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

Four routes to the answer, in order:

1. **The platform only ever has game folders.** For DOS, PS3, ScummVM, Wii and similar a
   title always consists of many files, so the file count is no criterion there.
2. **The folder is a disc-image set.** A `.gdi`, `.cue` or `.m3u` **names its files** and
   those files sit next to it. Structure, not name comparison.
3. **Few files that reduce to the same title.** With the medium marker removed —
   `(Disk 1)`, `(Side A)`, `[Disc 2]`, `(Tape 1 of 3)` — the same name remains. That is a
   multi-disk game.
4. **Otherwise: a collection.**

#### "Not an archive" is not a failure (#447)

Under `amiga` there are files named `.ZIP` or `.LZH` that are neither — no `PK\x03\x04`,
no LHA header, but Amiga cruncher formats with signatures like `85 15 02 41`.

Reporting them as *"archive could not be extracted"* is wrong twice over: it claims damage
that does not exist, **and it buries the real cases**. Measured: **49 of 78** messages were
such files, and among them sat exactly **two** genuinely damaged archives.

The run therefore separates two findings, because they call for different answers:

| finding | answer |
|---|---|
| damaged archive | re-fetch it |
| not an archive | rename it — the file is intact, only mislabelled |

**Without a format list.** The signatures are inconsistent, so a list would be guesswork.
The measurable question is whether any extractor recognises the content at all: `lsar`
answers an unknown format with `Couldn't recognize the archive format`. If `lsar` is
absent, the file counts as an archive — a false alarm beats a silently skipped file.

#### Set members are never removed as duplicates (#467)

Step 3b removes **bit-identical** files at level 1. For CD titles that is wrong: track 01 is
frequently identical across many games — an empty data track or a copy-protection notice.
From the run log, verbatim:

```
dublette_entfernt  turbografx-cd/Monster Lair (USA) (Track 01).bin
                   gleich_wie  turbografx-cd/Valis II (USA) (Track 01).bin
```

Two different games. Afterwards Monster Lair's `.cue` names a file that no longer exists.
Under `dc` this deleted **375 files**, which is why only 13 of 213 titles can be
reconstructed from the log: the rest is gone, not misplaced.

**Identical content does not make two tracks interchangeable.** Anything named by an image
list in the same folder is exempt from deduplication, and the run reports how many files it
spared for that reason.

#### Why disc-image sets need their own rule (#462)

A Dreamcast title looks like this:

```
Bangai-O (PAL)(M3)/Bangai-O v1.001 (2000)(Virgin)(PAL)(M3)[!].gdi
Bangai-O (PAL)(M3)/track01.bin   track02.raw   track03.bin
```

Rule 3 asks for matching names and finds four distinct stems. It *cannot* see this case:
the names do not merely fail to match, they are deliberately generic — every Dreamcast game
names its tracks the same way.

Without rule 2 the folder counted as a collection and was flattened. The generic track
names collided and became `track01 (53).bin`, while the `.gdi` still says `track01.bin`.
**All 138 Dreamcast titles then pointed at the same file.** Measured on the emulator as
thousands of `W[GDROM]: Sector Read miss`; Flycast stopped at the Dreamcast BIOS and never
loaded a game.

Three conditions, all required — each catches a different wrong conclusion:

| Condition | without it |
|---|---|
| at least one image list at the top level | every folder would be a game |
| all lists reduce to **one** title | two different games in one folder would be merged |
| every named file is present | an incomplete folder would pass as intact |

The check runs **before** the file-count limit: `Bangai-O` had 38 files, the limit is 12.
Behind it, the rule would be present and ineffective.

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

**The table only grows against a finding.** After the full rebuild `Mixed` held 536 files
and the dry run moved nothing — correctly, except for one extension: 13 `.caq`, the Mattel
Aquarius cassette format, which belongs to nothing else and whose platform folder already
existed (#515). They come from the same `Mattel Intellivision & Aquarius ROMs` collection
whose Intellivision half was placed correctly via `.int`. Everything else stays for good
reasons — ancillary files, Windows programs, VICE configuration, and `.bin`, which is
ambiguous on purpose. `.cas` stays out too: MSX and ColecoVision use it as well.

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

### Checking image lists: `rom-abbilder-pruefen`

A disc image is a small text list (`.gdi`, `.cue`, `.m3u`) plus several data files. If one
is missing the title is unplayable — and **silently so**: it still shows in the library,
RomM counts it, and only the emulator says `Sector Read miss`.

```bash
rom-abbilder-pruefen /roms                    # report only, touch nothing
rom-abbilder-pruefen /roms psx --reparieren   # rewrite unambiguous references
rom-abbilder-pruefen /roms --aussortieren     # MOVE unusable sets to _defekt/
```

#### Two questions, not one

The obvious check — *does the list name files that are not there?* — has a blind spot, and
it was measured on the library:

```
/roms/dc  ->  0 defects reported, while ALL 138 titles were broken
```

The game folders had been flattened, and every Dreamcast game names its tracks
`track01.bin`. In the flat folder that name **exists**, so every list found a match — just
the wrong one. **Name presence is not the same as the right file.**

| Question | finds |
|---|---|
| **missing** — does the list name files that are not beside it? | lost or renamed tracks |
| **shared** — do *several* lists in one folder name the same file? | the collision damage from #462 |

Measured: 11 unambiguously solvable, 106 with genuinely missing data, 83 shared references
(all under `dc`).

#### What it repairs, and what it deliberately does not

A list is rewritten only when the intended file is **unambiguous**: it carries the list's
own stem (the common case of a renamed rip), or it is the only file with that extension
**that no other list claims**.

That last clause is the point. Without it, "exactly one `.bin` in the folder" was enough —
and a `.cue` whose data is genuinely gone got rewired onto **another game's** image. Caught
on a fixture before the tool saw the real library. **A guessed reference looks intact and
is not**, which is worse than a visibly broken one, because nobody looks again.

`--aussortieren` **moves** to `<plattform>/_defekt/` and deletes nothing. The tracks that
are there are real data, and whether they are replaceable is the operator's call. Every
change is recorded with source and real destination in
`.abbildpruefung/<platform>-<time>.jsonl`, and a rewrite leaves a `.vor-fix` copy.

An `.m3u` holding stream URLs is **not** counted as a broken image.

### What the tools do not do

- **Never rename platform folders.** Those names come from RetroNAS.
- **Delete nothing except proven duplicates** — same checksum, same content.
- **Leave archives alone where an archive is the correct shape**: arcade, MAME, Neo Geo and
  CPS expect the `.zip` to be the game. Those platforms are listed in `ARCHIV_BLEIBT`.

### The log is the way back — including for deleted files

On 2026-08-12, 256 disc images were broken, among them **all 138 Dreamcast titles**. 230 of
them were restored **without downloading a byte**. That was only possible because the log
records more than reading the logging code suggests.

#### Moves: source and **real** destination

```json
{"art":"verschoben",
 "von":"/roms/dc/Bomber Hehhe! (JP)/track01.bin",
 "nach":"/roms/dc/track01 (2).bin"}
```

The destination carries the **collision suffix**. A flattening is therefore reversible file
by file, even when a hundred games use the same track names.

#### Deletions: the file it was identical to

```json
{"art":"dublette_entfernt",
 "pfad":"/roms/dc/track03 (67).bin",
 "gleich_wie":"/roms/dc/track03 (7).bin",
 "sha256":"09b26522…"}
```

**A file is only ever deleted when it is bit-identical to another.** A deleted file is
therefore not lost while its twin exists — it can be **copied back**, and the copy is exact
by construction. In all 555 cases the source was still there.

#### Two conditions, without which this goes wrong

**Restore set members only.** 161,406 of the deleted files are *genuine* duplicates
(`Krull (CCE) (2).a26` next to `Krull (CCE).a26`) and must stay deleted. The restorable
count dropped from 1078 to 180 once this was applied properly: files like
`Alien Breed 3D (Track 1) (2).bin` are second copies that no `.cue` names. The only test
that counts is **whether an image list in the target folder names the file**.

**Verify the checksum rather than trusting the log line** — twice: before copying (is the
source still the file the log describes?) and after (did the copy land intact?).

#### When it does *not* work

If the twin is gone too, the file is gone. The log can only show where something went and
what it was identical to; it stores no data.

### Before running

- **It takes time.** Over 19 hours on a 5 TB library. Throughput follows the file count,
  not the data volume: a platform of individually compressed ROMs takes hours for a few
  gigabytes, because every archive is unpacked.
- **One log per platform** lands in `<roms>/.umbau/`. It is what `--zurueck` reads.
- **The `.umbau` folder starts with a dot** — Romseerr skips hidden folders, or the log
  files would appear as a platform with "titles" of their own.
