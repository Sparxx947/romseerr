# Streaming-Host für Romseerr

*(English below)*

Für die Plattformen, die ein Browser **nicht** emulieren kann — PlayStation 2,
GameCube, Wii, Switch. Der Emulator läuft hier server-seitig mit GPU, der Browser
bekommt Bild und Ton und schickt Eingaben zurück.

**Romseerr emuliert nichts.** Es löst einen Titel auf eine Datei auf und bittet den
Start-Dienst, sie zu öffnen. Emulatoren, BIOS- und Firmware-Abbilder liefert dieses
Projekt nicht mit — die besorgst du dir selbst, aus Hardware, die dir gehört.

Für alles, was EmulatorJS kann (NES bis PSP), brauchst du das hier **nicht** —
dafür gibt es den Play-Knopf.

---

## Kurzfassung

```bash
cp .env.example .env
$EDITOR .env                      # ROMS_DIR, GPU-Knoten, Token, Domain
docker compose --profile acme up -d
```

Ohne eigene Domain: den Profilschalter weglassen und ein eigenes Zertifikat nach
`data/config/ssl/cert.pem` + `cert.key` legen.

Danach in Romseerr unter **Einstellungen → Verbindungen**:

| Feld | Wert |
|---|---|
| Streaming-Host | `https://dein-host:8902/` |
| Start-Dienst | `http://dein-host:8901/launch?token=<STREAM_AGENT_TOKEN>` |

---

## HTTPS ist Pflicht, nicht Kür

Das ist die wichtigste Zeile dieser Datei.

Über **HTTP** an einer LAN-Adresse verweigert Selkies den Dienst komplett
(„This application requires a secure connection"). Und selbst wo das Bild läuft,
brauchen **Ton und Gamepad die WebCodecs-API**, die Browser über HTTP sperren.
Das Ergebnis ist heimtückisch: Video läuft, Ton fehlt, der Controller wird nie
erkannt — und nichts davon erzeugt eine Fehlermeldung.

Drei Wege zu HTTPS:

1. **Eigene Domain + DNS-01** (der certbot-Beiwagen hier). Ein DNS-Eintrag, der auf
   die private Adresse zeigt, reicht — es muss **kein Port nach außen offen** sein.
   Kein Client muss etwas importieren.
2. **Eigenes Zertifikat** aus einer bestehenden PKI: nach `data/config/ssl/` legen.
3. **Nur zum Ausprobieren**: `http://localhost:<port>` über einen SSH-Tunnel.
   `localhost` gilt Browsern als sicherer Kontext.

> **DNS-Rebind-Schutz.** Zeigt ein öffentlicher Name auf eine private Adresse,
> blockieren viele Router die Auflösung (FRITZ!Box, OpenWrt, pi-hole u. a.). Der
> Name lässt sich dann im LAN nicht auflösen, obwohl der Eintrag stimmt. In der
> Router-Oberfläche eine Ausnahme für die Domain eintragen.

---

## GPU: läuft, aber auf der CPU

Der X-Server im Container ist ein `Xvfb` **ohne DRI3**. Ohne DRI3 fällt Mesa auf
`llvmpipe` zurück — Software-Rasterisierung auf der CPU. Es sieht aus, als
funktioniere alles; PS2 und GameCube sind dabei aber unbrauchbar langsam.

Prüfen:

```bash
docker exec stream-host bash -lc 'DISPLAY=:1 glxinfo -B | grep "OpenGL renderer"'
# llvmpipe            -> CPU, falsch
# Mesa Intel/AMD/…    -> GPU, richtig
```

Die Lösung ist **VirtualGL** (`init/10-virtualgl`): es rendert per EGL direkt auf
der Karte und schiebt die Bilder in den X-Server. Kein DRI3, keine Zusatzrechte.

> **VirtualGL will den Card-Knoten, nicht den Render-Knoten.**
> `vglrun -d /dev/dri/renderD128` → `[VGL] ERROR: 245: Invalid EGL device`
> `vglrun -d /dev/dri/card0` → funktioniert
> Welcher es ist, sagt `/opt/VirtualGL/bin/eglinfo -e`. Das Init-Skript ermittelt
> ihn selbst und legt ihn nach `/config/.vgl-device`.

Deshalb müssen in `.env` **beide** Knoten derselben Karte stehen.

### Nachtrag: der DRI3-Schalter funktioniert inzwischen — und macht VirtualGL überflüssig

Hier stand lange, der eingebaute Schalter (`DRINODE` + `DISABLE_DRI3=false`) sei **keine**
Alternative, weil Xvfb mit Intel-Arc-Karten dabei mit `Segmentation fault` abstürzte. Das
gilt nicht mehr. Am laufenden Host nachgemessen (2026-08-10):

```
DRINODE=/dev/dri/renderD129
DISABLE_DRI3=false
```

Xvfb läuft damit stabil, **DRI3 ist vorhanden**, und `vulkaninfo --summary` zeigt
`Intel(R) Arc(tm) A310 Graphics (DG2)` mit dem Mesa-Treiber. Die Emulatoren starten
seitdem **ohne `vglrun`** — Dolphin meldet im Fenstertitel `Vulkan`, und die Karte
arbeitet nachweislich (GPU-Last steigt, Bildrate steht).

**Was das an Rechenzeit spart**, an Dolphin je Thread aus `/proc` gemessen
(100 % = ein Kern voll):

| Thread | vorher (VirtualGL) | jetzt (Vulkan direkt) |
|---|---|---|
| Video thread | **dauerhaft ~100 %** | **5,7 %** |
| CPU thread | — | 51,7 % |

Der Video-Thread war der Engpass: Er kostete pro Bild und pro Zeichenaufruf, nicht pro
Pixel — die Signatur des VirtualGL-Umwegs. Damit erübrigt sich auch der Umbau auf einen
echten Xorg, der dafür einmal geplant war (#169): **das Ziel ist ohne ihn erreicht.**

`init/10-virtualgl` und `/opt/VirtualGL` liegen weiterhin im Abbild, werden aber von
keinem Emulator mehr benutzt. Sie bleiben vorerst als Rückfallebene — wer sie loswerden
will, prüft vorher mit `ps aux | grep vglrun`, ob wirklich nichts mehr darüber startet.

---

### xemu (Xbox) braucht zwei Dinge extra

Am laufenden Host nachgemessen (#300). Beides erledigt `init/22-xemu-vorbereiten`:

1. **`libusb-1.0.so.0`.** Jedes andere Emulator-AppImage bringt seine Bibliotheken mit,
   xemus tut es für libusb **nicht** — und der Container hat keine. Ohne sie endet der
   Start sofort mit `error while loading shared libraries`, der Stream geht auf und
   bleibt leer. Das Skript leiht sie aus einem Emulator, der sie mitbringt, und legt
   eine **Kopie** nach `/config/lib` — nach `/usr` zu schreiben wäre die Falle, die hier
   schon ein per `apt` installiertes Dolphin lautlos verschwinden ließ.
2. **`xbox_hdd.qcow2`.** Die Xbox startet ohne Festplatte nicht. Das Abbild ist leer,
   formatiert und kommt vom xemu-Projekt selbst; das Skript holt es einmalig.

Dazu kommt der **Ton**: ALSA lädt sein Pulse-Modul über `libpulse.so.0`, das wiederum
`libpulsecommon-<version>.so` braucht. Die liegt im System, aber in einem **Unterordner**
außerhalb des Suchpfads — deshalb blieb xemu stumm, obwohl PulseAudio lief. Der Agent
setzt für Xbox deshalb `LD_LIBRARY_PATH` auf beide Pfade.

> **Nicht den ganzen lib-Ordner eines anderen Emulators einhängen.** Genau das wurde
> versucht: dessen `libpulse.so.0` verdrängt die des Systems und passt nicht zur
> System-`libpulsecommon` — `undefined symbol: pa_in_valgrind`, und der Ton bleibt
> wieder weg. Es wird deshalb **genau eine Datei** geliehen, kein Verzeichnis.

### Und vor allem: das richtige BIOS

**Alle Retail-BIOS-Dumps führen zu einem schwarzen Bild** oder zum Hinweis „Ihre Xbox
muss gewartet werden" — sie verlangen eine **gesperrte** Festplatte, und das
mitgelieferte Abbild ist ungesperrt. Am laufenden Host wurden alle 14 Kombinationen
durchgemessen (7 BIOS × 2 MCPX), bewertet über die mittlere Helligkeit im Fenster:

| BIOS | MCPX 1.0 | MCPX 1.1 |
|---|---|---|
| 5838, 5713, 5530, 5101, 4817 | schwarz | schwarz |
| 4034 | 4,5 | schwarz |
| 3944 | 4,3 | 8,4 (Wartungshinweis) |
| **COMPLEX 4627** | **232** | 65 |

Nötig ist also ein **gepatchtes** BIOS — `COMPLEX 4627` zusammen mit **MCPX 1.0**. Die
Firmware-Prüfung kann das nicht abfangen: Sie prüft Größen, und ein Retail-Dump hat
dieselbe Größe.

> **Der Fenstertitel taugt nicht als Erfolgskriterium.** Er lautet immer
> `xemu | v0.8.136` — ob Willkommensdialog, Fehlermeldung oder laufendes Spiel, denn
> xemu zeichnet seine Dialoge ins Fenster statt als eigenes X-Fenster. Wer prüfen will,
> ob wirklich etwas läuft, misst die **Helligkeit im Fensterausschnitt** (schwarz ≈ 0)
> oder vergleicht zwei Aufnahmen: **bitgleiche Bilder bei hoher CPU-Last bedeuten
> eingefrorenen Framebuffer, nicht laufendes Spiel.**

Eine eigene `xemu.toml` braucht es darüber hinaus **nicht** — mit Festplattenabbild
startet xemu auch ohne Konfigurationsdatei und ohne `eeprom.bin`, das es sich selbst
anlegt. Der anfängliche `Failed to load BIOS '(null)'` war ein Folgefehler der
fehlenden Platte.

## Was noch überrascht

**Init-Skripte gehören nach `/custom-cont-init.d`.** Der ältere Pfad
`/config/custom-cont-init.d` ist bei LinuxServer abgeschaltet — dort abgelegte
Skripte werden kommentarlos ignoriert. Das Compose hängt das Verzeichnis richtig ein.

**AppImages brauchen FUSE, Container haben keins.** Der naheliegende „Fix" wäre
`--cap-add SYS_ADMIN` — viel zu viel für einen Spielestarter. `init/20-emulators`
entpackt AppImages stattdessen (`--appimage-extract`) und startet `AppRun`.

**Es gibt genau einen primären Client.** Verbindet sich ein zweiter Browser mit
derselben URL, wird der erste ohne Vorwarnung getrennt
(`Received KILL message from server: a new primary client connected`). Für Zuschauer
und Mitspieler gibt es in der Seitenleiste unter **Teilen** eigene Links — auch für
Gamepad-Spieler 2 bis 4.

**Der Emulator will einen echten Klick.** Fensterfokus allein genügt manchen
Emulatoren nicht; Tastatur und Gamepad wirken erst nach einem Mausklick ins Bild.

**Emulatoren finden Gamepads beim Start.** Schließe dein Pad an und drücke eine
Taste, **bevor** du einen Titel startest — Browser melden Gamepads erst nach einem
Tastendruck, und der Emulator sucht nur beim Start danach.

---

## Ton prüfen, wenn er fehlt

Die Anzeigen im Browser sind hier irreführend (die Statistik zeigt selbst bei
laufendem Video „Bandbreite 0"). Der einzige verlässliche Messpunkt liegt im
Container:

```bash
docker exec stream-host bash -lc \
  'timeout 5 parec --device=output.monitor --format=s16le --rate=48000 --channels=2 \
   > /tmp/p.raw; tr -d "\000" < /tmp/p.raw | wc -c'
```

Kommt dort eine große Zahl heraus, liegt Ton an und das Problem ist der Browser
(fast immer: kein HTTPS). Kommt `0` heraus, ist die Quelle still — dann liegt es am
Emulator oder am Spiel, nicht an der Übertragung.

Zwei Einstellungen sind dafür nötig und im Compose gesetzt:
`SELKIES_AUDIO_ENABLED=true` (Standard ist **aus**) und
`PULSE_SERVER=unix:/defaults/native` (die Aufnahmebibliothek beachtet
`PULSE_RUNTIME_PATH` nicht und scheitert sonst an `pa_context_connect()`).

---

## Emulatoren installieren

**Eine frische Installation bringt keinen einzigen Emulator mit** und lädt auch keinen.
Du wählst in Romseerr unter **Einstellungen → Verbindungen** aus, was auf die Maschine
kommt — je Eintrag ein Klick.

Das ist Absicht: welche Emulatoren auf deinem Rechner landen, hat je nach Rechtsordnung
Gewicht, und diese Entscheidung nimmt dir das Projekt nicht stillschweigend ab.

Für unbeaufsichtigte Ausrollungen gibt es die `INSTALL_*`-Schalter in der `.env` — die
holen beim Containerstart automatisch. Standard ist bei allen `false`.

Zwei Emulatoren brauchen eine Adresse von dir, weil sich ihre Quelle nicht automatisch
ermitteln lässt: **RPCS3** (keine Release-Dateien auf GitHub, offizieller Direktlink
weist automatisierte Abrufe ab) und der **Switch-Emulator** (bewusst ohne eingebaute
Adresse). Romseerr zeigt sie als „URL nötig".

## Was tatsächlich getestet ist

„Installiert" ist nicht „läuft". Diese Tabelle sagt, was **mit einem echten Titel
ausprobiert** wurde — Bild im Browser, Ton am Sink gemessen (nicht nach Gehör),
Controller im Spiel gedrückt.

| Plattform | Emulator | Bild | Ton | Controller | Anmerkung |
|---|---|---|---|---|---|
| PlayStation 1 | DuckStation | ✅ | ✅ | ✅ | |
| PlayStation 2 | PCSX2 | ✅ | ✅ | ✅ | |
| GameCube | Dolphin | ✅ | ✅ | ✅ | |
| Wii | Dolphin | ✅ | ✅ | (⁠—⁠) | Controller nicht eigens geprüft — gleicher Emulator und gleiche Belegung wie GameCube |
| PlayStation 3 | RPCS3 | ✅ | ✅ | ✅ | |
| Switch | Eden | ✅ | ✅ | (⁠—⁠) | Controller nicht eigens geprüft |
| Nintendo 3DS | Azahar | ❌ | ❌ | — | Emulator startet, **kein Titel spielbar** — siehe unten |
| Dreamcast | Flycast | — | — | — | keine Titel in der Bibliothek, nichts zu testen |
| Xbox | xemu | ✅ | ✅ | ✅ | braucht **COMPLEX 4627 + MCPX 1.0** — Retail-BIOS bleiben schwarz |
| Wii U | Cemu | — | — | — | keine Titel in der Bibliothek |
| PS Vita | Vita3K | — | — | — | keine Titel in der Bibliothek |

Ein `—` heißt **ungeprüft**, nicht „defekt". Die vier unteren Zeilen sind ungeprüft,
weil dort schlicht nichts liegt, was man starten könnte.

### Zwei Fallen, die nach einem Defekt des Hosts aussehen

Beides sind **Titelprobleme**, keine Emulatorprobleme — der Emulator läuft in beiden
Fällen einwandfrei, nur das Spiel nicht:

- **3DS: verschlüsselte ROMs.** Azahar startet, aber jeder Titel scheitert. Je nach
  Format anders: ein Cartridge-Dump zeigt den Dialog `App Encrypted`, ein eShop-Titel
  schreibt `Failed to determine system mode (Error 8)` ins Emulator-Log und öffnet gar
  kein Fenster, und ein `.cia` meldet `CIA must be installed before usage` — CIAs muss
  man erst installieren, sie starten nicht direkt. Der Schlüsselsatz (`aes_keys.txt`,
  `boot9.bin`) war dabei vollständig; es liegt an den Dateien, nicht an der Firmware.
  Abhilfe gibt es nur außerhalb dieses Projekts: entschlüsselte Dumps verwenden.
- **Wii: NKit-komprimierte ISOs.** Dolphin öffnet einen `NKit Warning`-Dialog statt des
  Spiels. Dieselbe Bibliothek in `.wbfs` startet ohne Zutun.

### Wo der Host sagt, dass kein Spiel läuft

Der Start selbst **gelingt** in diesen Fällen — der Emulator läuft ja. Deshalb antwortet
`/launch` weiterhin mit `ok`; was scheitert, ist der Titel, und das steht in `/status`:

```
window        ""             noch nichts gestartet
              "pending"      Start läuft, das Fenster wird noch erwartet
              "ok"           ein Spielfenster steht
              "dialog"       Fehlerdialog — window_detail ist dessen Titel
              "kein-fenster" gar nichts Sichtbares entstanden
              "unbekannt"    der Fensterschritt selbst kam nicht durch
window_detail Klartext, bei "dialog" der Titel des Dialogs
```

Bei einer verschlüsselten 3DS-ROM steht dort also `window: "dialog"` und
`window_detail: "App Encrypted"` — die Auskunft, die vorher nur auf dem Bildschirm des
Emulators stand und niemanden erreichte.

Erkannt werden Dialoge am Fenstertyp `_NET_WM_WINDOW_TYPE_DIALOG`, nicht an bekannten
Fehlertexten: eine Textliste wäre in jeder neuen Emulatorfassung falsch. Nebenbei löst
das ein zweites Ärgernis — vorher wurde der Fehlerdialog **selbst** aufs Vollbild
gezogen (er ist mit 293×101 groß genug, um als Fenster durchzugehen), und genau das kam
als „leerer Stream" an.

## Die Bibliothek muss auf beiden Seiten dieselbe sein

Romseerr und der Streaming-Host hängen beide die ROM-Bibliothek ein. **Beide müssen
dieselbe Wurzel meinen** — sonst startet der Emulator nicht, und zwar ohne dass es
danach aussieht: Romseerr öffnet brav den Desktop, der Titel bleibt zu.

```
Romseerr    : /pfad/zur/bibliothek  ->  /roms
Stream-Host : /pfad/zur/bibliothek  ->  /roms     # DIESELBE Quelle
```

Falsch wäre, bei Romseerr `…/bibliothek/roms` einzuhängen und beim Streaming-Host
`…/bibliothek`. Beide heißen im Container `/roms`, meinen aber verschiedene Ordner.

Romseerr schickt den Pfad inzwischen **relativ zur Wurzel**, damit nicht auch noch der
Einhängepunkt übereinstimmen muss. Die Wurzel selbst muss es aber weiterhin — und wenn
sie es nicht tut, sagt der Start-Dienst das im Klartext, statt nur „nicht gefunden".

## Controller

Ein Container darf keine Eingabegeräte anlegen. Selkies löst das mit einem
**vorgeladenen Interposer**, der das Öffnen von `/dev/input/js*` abfängt und die Daten
über einen Unix-Socket aus dem Browser holt — ohne `uinput`, ohne erweiterte Rechte.

Die Selkies-Dokumentation nennt drei Variablen; das Abbild setzt zwei davon und lässt
`SDL_JOYSTICK_DEVICE` weg. Der Start-Dienst ergänzt sie, sonst hat SDL keinen Hinweis,
welches Gerät gemeint ist.

### Prüfseite: was sieht der Browser?

```
https://<host>:<HTTPS_PORT>/gamepad-check.html
```

Sie zeigt sicheren Kontext, Fokus, alle gemeldeten Pads und **live jede gedrückte
Taste**. Damit trennt sich der Fehler sauber: Erscheint das Pad dort, sind Rechner und
Browser in Ordnung und es liegt an der Stream-Seite oder der Übertragung. Erscheint es
nicht, kann auf dem Streaming-Host nichts ankommen — dort zu suchen wäre vergeudet.

Warum es diese Seite überhaupt gibt: **Die Stream-Seite fängt die Tastatur ab** und
reicht sie an den entfernten Desktop weiter. `F12` kommt dort nie beim Browser an —
ausgerechnet die Seite, auf der man die Konsole bräuchte, ist die, auf der man sie nicht
öffnen kann. Diese Prüfseite braucht keine.

**Die Reihenfolge entscheidet, und sie ist nicht intuitiv:**

1. Controller am eigenen Rechner anschließen
2. **eine Taste darauf drücken**, während die Stream-Seite im Vordergrund ist
3. **erst dann** den Titel starten

Grund: Die Gamepad-API des Browsers meldet ein Pad aus Datenschutzgründen erst nach
einem Tastendruck, und die meisten Emulatoren lesen die Geräteliste nur beim Start.
Wer zuerst startet und dann den Controller anfasst, bekommt ein stummes Pad — ohne dass
irgendetwas defekt wäre. In dem Fall genügt es, den Titel neu zu starten.

Zum Nachsehen im Browser: `navigator.getGamepads()` in der Entwicklerkonsole. Kommt
dort nichts, liegt es nicht am Container.

## BIOS und Firmware

Mehrere Emulatoren starten ohne Firmware **gar nicht** — und das äußert sich als
schwarzes Bild, nicht als Fehlermeldung. Romseerr zeigt deshalb unter **Einstellungen →
Verbindungen** je Plattform an, was fehlt.

**Dieses Projekt besorgt keine BIOS-Abbilder.** Für PS2, Xbox, Dreamcast, 3DS, Switch
und Wii U gibt es keine berechtigte Quelle; ein Skript könnte sie nur von Seiten holen,
die sie ohne Erlaubnis verbreiten. Jedes Emulator-Projekt lehnt das ab, dieses ebenfalls.
Was hier automatisiert ist, ist die eigentliche Arbeit: **welche** Datei, ob sie heil
aussieht, und **wohin** sie gehört.

| Weg | Wofür |
|---|---|
| **Hersteller** | Nur **PS3**: Sony veröffentlicht seine Systemsoftware selbst. Ein Klick, der Rest läuft. |
| **Hochladen** | Alles andere. Du wählst die Datei, Romseerr reicht sie durch — **Romseerr speichert sie nicht**. |

Die Dateien landen unter `/config/firmware/<plattform>/` und werden von dort dorthin
kopiert, wo der jeweilige Emulator sucht. Diese Trennung ist Absicht: Wird ein Emulator
neu installiert, bleibt die Firmware erhalten.

**PS Vita:** Vita3K **lädt nichts herunter** — der Quelltext öffnet einen Dateidialog
(`firmware_install_dialog.cpp`). Es gibt dort also nichts zu automatisieren außer dem
Einspielen; die PUP besorgst du dir selbst und lädst sie hoch.

**Was geprüft wird — und was nicht.** Geprüft wird die **Größe**. Das schlägt bei
abgebrochenen Downloads und offensichtlich falschen Dateien an, und genau dafür ist es
da. Es beweist **nicht**, dass der Inhalt korrekt ist — deshalb heißt der Zustand „ok"
und nicht „verifiziert". Eine mitgelieferte Prüfsummenliste gäbe es hier nicht: sie wäre
in der Praxis ein Verzeichnis dafür, welche Kopie „die richtige" ist.

Von Hand geht es auch:

```bash
docker exec stream-host /custom-cont-init.d/25-firmware --status
docker exec stream-host /custom-cont-init.d/25-firmware --import dreamcast /pfad/dc_boot.bin
docker exec stream-host /custom-cont-init.d/25-firmware --vendor ps3
```

## PlayStation 1 (DuckStation)

PS1 ist die einzige Plattform, die **beide Wege** anbietet: den Browser-Kern *und* den
Stream. Das ist eine bewusste Ausnahme (`DUAL_WEG` in `app.py`) — bei allen anderen gilt
weiter „Browser-Kern oder Stream, nie beides". Der Grund: Im Browser spielen mehrere
Personen gleichzeitig und ohne Sitzung, der Stream liefert Vollbild und legt die
Speicherstände neben die der anderen Konsolen.

**PS1 braucht ein BIOS** (512 KiB, `scph*.bin`) unter `<config>/.local/share/duckstation/bios`.
Das PS2-BIOS taugt **nicht** als Ersatz, auch wenn eine PS2 PS1-Discs abspielt. Die
Firmware-Prüfung erkennt es an der **Größe**, nicht am Namen — die Datei heißt je nach
Region und Konsole anders.

**Falle: der Erstlaufdialog.** DuckStation öffnet beim ersten Start einen *modalen*
„Setup Wizard". Im Container sieht den niemand, und **jeder Start staut sich dahinter** —
der Prozess lebt, ein Fenster existiert, ein Spiel startet nie. Das Startprofil setzt
deshalb `SetupWizardIncomplete = false`. Dieselbe Falle wie RPCS3s Willkommensfenster und
JDownloaders Rückfragen; wer einen neuen Emulator ergänzt, sollte zuerst danach suchen.

*EN: PS1 is the only platform offering both the browser core and the stream — a
deliberate exception (`DUAL_WEG`), because neither way is clearly better: the browser
serves several people at once without a session, the stream gives fullscreen and keeps
saves next to the other consoles. It needs a 512 KiB PS1 BIOS in
`<config>/.local/share/duckstation/bios`; the PS2 BIOS is not a substitute, and the check
matches by size because the filename varies. Note the trap: DuckStation opens a modal
setup wizard on first run that nobody can see in a container, and every launch stalls
behind it — the launch profile sets `SetupWizardIncomplete = false`.*

## Zwei Plätze gleichzeitig (optional)

Standardmäßig ist die Anlage **einsitzig**: ein Container, eine Sitzung, und die zweite
Person bekommt „in Benutzung von …". Mit einem Profil wird daraus ein zweiter Platz:

```bash
docker compose --profile seat2 up -d
```

Dazu in Romseerr unter *Einstellungen → Verbindungen* die Adressen des zweiten Platzes
eintragen (`stream_url_2`, `stream_launch_2`). Romseerr vergibt dann den ersten freien
Platz und schickt jeden auf **seine** Adresse.

| | Platz 1 | Platz 2 |
|---|---|---|
| HTTP / HTTPS | 8900 / 8902 | 8910 / 8912 |
| Start-Dienst | 8901 | 8911 |

**Was geteilt wird — und was das kostet.** Beide Container benutzen dasselbe `/config`:
Emulatoren, Firmware, Einstellungen und **Speicherstände**. Das spart Platz und doppelte
Update-Arbeit, hat aber eine klare Kehrseite:

> Spielen zwei Leute **denselben** Emulator, schreiben beide Instanzen dieselben Dateien.
> Wer zuletzt beendet, gewinnt — bei Einstellungen ärgerlich, bei Speicherständen ein
> echter Verlust. Bei zwei **verschiedenen** Konsolen tritt das nicht auf.

Wer das trennen will, hängt für `stream-host-2` ein eigenes `/config` ein und lässt nur
`emulators` und `firmware` gemeinsam.

**Nur Platz 1 aktualisiert die Emulatoren** (`EMU_AUTO_UPDATE=false` beim zweiten).
Liefen beide gleichzeitig in ihren Kataloglauf, entpackten sie dieselbe AppImage in
dasselbe Verzeichnis — das Ergebnis wäre ein halb ersetzter Emulator, ohne Fehlermeldung.

**Zur Bauweise, weil es eine Falle ist:** Der zweite Dienst erbt über **YAML-Anker**,
nicht über `extends`. `extends` führt Listen **zusammen** — der zweite Container erbte
damit die Ports des ersten und brach beim Start mit *„port is already allocated"* ab.
Ein Test hält seither fest, dass sich beide Plätze `/config` und GPU teilen, aber
niemals einen Port.

*EN: the host is single-seat by default; `--profile seat2` adds a second one on ports
8910/8912/8911. Configure `stream_url_2` and `stream_launch_2` in Romseerr, which then
hands out the first free seat and sends each player to their own address. Everything
under `/config` is shared — including save states, so two people on the SAME emulator
overwrite each other and the last to quit wins; different consoles are unaffected. Only
seat 1 updates the shared emulators. The second service inherits through YAML anchors
rather than `extends`, because `extends` merges lists and the second container would
have inherited the first one's ports.*

## Was zwei gleichzeitige Sitzungen kosten (gemessen)

Gemessen am 2026-08-10 auf einer **Arc A310**, 1920×1080 bei 30 fps, mit
`intel_gpu_top`. Je drei Läufe à 10–15 s; Ladephasen verworfen.

| Zustand | RCS (3D) | VCS (Video) | GPU-Takt | CPU gesamt |
|---|---|---|---|---|
| leer | 0 % | 0 % | 0 MHz | — |
| 1 Emulator (PS1), kein Bild | 7,9 % | 0 % | 367 MHz | — |
| 2 Emulatoren (PS1), kein Bild | 15,2 % | 0 % | 575 MHz | — |
| 1 Emulator (GameCube), kein Bild | 18,8 % | 0 % | 745 MHz | 94 % |
| GameCube + PS1, kein Bild | 18,7 % | 0 % | 772 MHz | 124 % |
| **GameCube + PS1, beide Streams offen** | **30,0 %** | **0 %** | 849 MHz | **371 %** |

**Die GPU ist nicht der Engpass.** Bei zwei laufenden Sitzungen mit Bild liegt die
Render-Engine bei 30 % und der Takt bei 849 MHz — von **2450 MHz** möglichem Maximum,
kaum über dem Dauerlast-Takt von 600 MHz. Da ist Luft für mehr als zwei Plätze.

**Zwei gleichartige Sitzungen addieren sich, ungleiche nicht.** Zweimal PS1 verdoppelt
die Last (7,9 → 15,2 %), GameCube plus PS1 kostet dagegen nichts extra (18,8 → 18,7 %).
Der Grund steckt in der Zahl: `RCS %` ist die **Belegungszeit** der Engine, nicht
Rechenleistung. Die zweite Sitzung füllt Lücken, statt die Engine länger zu beschäftigen
— sichtbar daran, dass stattdessen der Takt steigt.

**Der Engpass war die CPU — und das war ein Konfigurationsfehler.** In den Messungen
oben kostete die Kodierung rund **1,2 Kerne je Sitzung**, weil Selkies in Software
kodierte:

```
[x11] No GPU Encoder available -> Using CPU Software Encoding.
```

`VCS` blieb dabei durchgehend bei 0 % — die Video-Engine der Arc lag brach. **Behoben
mit `SELKIES_AUTO_GPU` (#283):**

```
[x11] VAAPI Encoder initialized successfully.
[x11] Encoder: VAAPI | Mode: H264
```

| eine Sitzung mit Bild | Software | **VAAPI** |
|---|---|---|
| VCS (Video-Engine) | 0 % | **2,8 %** |
| VECS | 0 % | 1,5 % |
| CPU des Containers | 179 % | **152 %** |

**Warum die Variable nötig ist:** Ohne sie leitet Selkies den GPU-Index aus dem **Namen**
des Knotens ab (`parse_dri_node_to_index`: `renderD129` → Index 1) und öffnet die n-te
Karte. Der Container bekommt aber genau eine, und die ist dort Index 0 — also sucht es
eine zweite, findet keine und weicht auf die CPU aus. Mit `SELKIES_AUTO_GPU` sucht das
Aufnahmemodul die Karte selbst (`encode_node_index = -2`), und die Rechnung entfällt.

**Versucht und verworfen:** den Knoten als `renderD128` einzuhängen. Das macht den Index
richtig, aber den Knoten widersprüchlich — Name sagt 128, Gerätenummer sagt 129. X und
Vulkan stört das nicht, `libva` lehnt ab: *DRM instance fd does not appear to refer to a
DRM device*.

`Slice count rounded up to 68 (from 4)` im Log ist **kein Fehler**, sondern Rechnen:
1080 ÷ 16 = 67,5 → 68. Intels Low-Power-Encoder will einen Slice je Makroblockzeile.

*EN: measured on an Arc A310 at 1080p30. The GPU is not the bottleneck — two sessions
with video sit at 30 % render engine and 849 MHz of a possible 2450. Two identical
sessions add up, mixed ones do not, because RCS % is engine occupancy rather than work.
The real cost is the CPU: roughly 1.2 cores per session, because Selkies falls back to
software encoding. VCS stays at 0 % throughout — Selkies derives the GPU index from the
node NAME (renderD129 → index 1) while the container exposes a single node at index 0,
so the capture module looks for a card that is not there.*

## Emulatoren aktualisieren und zurücksetzen

Läuft bei jedem Containerstart: die aktuelle Release-URL wird geholt und mit der
installierten verglichen. Aus Romseerr heraus geht es auch direkt —
**Einstellungen → Verbindungen → „Emulatoren aktualisieren"**.

Zwei Sicherheitsnetze, weil ein Update auch schaden kann:

* Ein fehlgeschlagener **Download** oder ein fehlgeschlagenes **Entpacken** lässt
  die laufende Fassung unangetastet. Es wird daneben entpackt und nur bei Erfolg
  getauscht.
* Die **vorige Fassung wird aufgehoben** (genau eine Generation). Bringt ein Update
  eine Regression, ist der Rückweg ein Klick — ohne Netz und ohne die alte Version
  suchen zu müssen.

Für dauerhaftes Bleiben auf einer bestimmten Fassung: die vollständige URL des
gewünschten Release-Assets in `<NAME>_URL` eintragen (z. B. `PCSX2_URL`). Sie
schlägt die Release-Abfrage, auch bei eingeschaltetem Auto-Update.

## DRI3: eine Zeile, kein X-Server-Umbau

Der X-Dienst des Abbilds kann DRI3, sucht dafür aber **fest nach `/dev/dri/renderD128`**.
Hängt die Karte an einem anderen Knoten, greift die Erkennung nie — Xvfb läuft ohne
GPU-Knoten, DRI3 fehlt, und Vulkan kann gar nicht präsentieren. Genau deshalb war
VirtualGL überhaupt nötig.

Die Abhilfe ist `DRINODE` in der Compose-Datei. Gemessen mit und ohne:

| | ohne `DRINODE` | mit |
|---|---|---|
| `xdpyinfo` | Composite, DAMAGE, GLX | **+ DRI3** |
| `vulkaninfo` | *No DRI3 support detected* | präsentierfähige Oberfläche auf der GPU |
| Dolphins Video-Thread | sättigt einen Kern | **14 %** |
| VirtualGL im Prozess | ja | **nein** |

Ein echter Xorg auf der GPU wurde probiert und funktioniert auch (headless, `modesetting`
+ glamor, als unprivilegierter Nutzer) — er wird schlicht nicht gebraucht.

## Gamepads: die uinput-Brücke

Selkies reicht Gamepads über einen **`LD_PRELOAD`-Interposer** weiter. Die Emulatoren hier
sind AppImages, deren Runtime **statisch gelinkt** ist (`AppRun` ist `static-pie`) — und auf
statische Binärdateien wirkt `LD_PRELOAD` nicht. Nachgemessen: Im laufenden Emulator ist
kein Interposer geladen, er öffnet kein einziges Eingabegerät, und sein SDL findet null
Pads. Selkies selbst arbeitet korrekt: Mit Interposer findet ein System-SDL **vier** Pads,
ohne **null**.

Ausprobiert und verworfen: den Interposer neu bauen (geht, ändert nichts), das apt-Paket
statt des AppImage (öffnet kein Fenster), die mitgelieferte `libudev` beiseitelegen
(wirkungslos).

Der Weg, der funktioniert, ist `selkies-uinput-bridge.py`. Sie spricht dasselbe
Socket-Protokoll wie der Interposer und legt daraus **echte Kernel-Geräte** an, die kein
Preloading brauchen. Gestartet wird sie von `init/35-gamepad-bridge`.

### Was dafür nötig ist

| | |
|---|---|
| `uinput`-Modul **auf dem Host** | `modprobe uinput`, dauerhaft über `/etc/modules-load.d/` |
| `/dev/uinput` im Container | steht unter `devices:` |
| `device_cgroup_rules: c 13:* rmw` | **ohne das geht es nicht**, siehe unten |

Die Freigabe ist der Punkt, der am meisten Zeit gekostet hat: Der Container darf Geräte
**anlegen**, aber nicht **öffnen**. Das gebrückte Pad stand als `/dev/input/event3` mit
`crw-rw-rw-` im Container — und `open()` scheiterte trotzdem mit `EPERM`, auch als `root`.
Es sind nicht die Dateirechte, sondern Dockers Device-Cgroup: erlaubt ist nur, was unter
`devices:` aufgeführt ist. Weil die Gerätenummer bei jedem Verbinden wechselt, hilft keine
feste Nummer, sondern nur der ganze Major 13.

**Abwägung:** Damit darf der Container auch die Eingabegeräte des Hosts lesen. Auf einem
Server ohne Tastatur und Maus ist das gegenstandslos — vorher `cat /proc/bus/input/devices`
ansehen.

### Zwei Eigenheiten, die von außen wie Defekte aussehen

**Die Geräte entstehen im `/dev` des Hosts, nicht im Container.** uinput legt sie im Kernel
an, also erscheinen sie im devtmpfs des Hosts; der Container hat sein eigenes `/dev`. Die
Brücke liest deshalb die Gerätenummer aus `/sys/devices/virtual/input/<sysname>/…/dev` und
legt den Knoten selbst an (`mknod` ist erlaubt, der Container ist **nicht** privilegiert).
Beim Verbindungsabbruch räumt sie nur das weg, was sie selbst angelegt hat.

**Selkies bietet immer vier Pads an**, auch ohne angeschlossenen Controller — es entstehen
also stets vier Geräte. Das ist beabsichtigt: Im Container läuft kein `udev`, ein bereits
laufender Emulator würde ein später erscheinendes Gerät nie bemerken. Reihenfolge deshalb:
**erst Pad im Browser verbinden, dann das Spiel starten.**

### Wenn nichts ankommt

Zuerst die Sonde — sie prüft die **ganze** Kette ohne angeschlossenen Controller und sagt,
welches der drei Glieder fehlt:

```bash
docker exec -u 0 stream-host python3 /opt/gamepad-bridge-probe.py
```

```
OK Bruecke verbunden
OK Geraeteknoten angelegt: /dev/input/event7
OK Eingaben kommen als uid 1000 an — die Kette steht.
```

Sie legt einen **eigenen** Socket an und lässt die echten unberührt; eine laufende Sitzung
stört sie nicht. Von Hand nachsehen geht auch:

```bash
docker exec stream-host tail -20 /config/gamepad-bridge.log   # legt sie Geräte an?
docker exec stream-host ls -l /dev/input/                     # event3.. vorhanden?
docker exec -u 1000 stream-host head -c1 /dev/input/event3    # EPERM = Cgroup-Regel fehlt
```

`event1000`–`event1003` und `js0`–`js3` legt **Selkies** an. Die `event100x` sind Attrappen
und melden „No such device" — das ist normal, sie funktionieren nur über den Interposer.
Die `js0`–`js3` zeigen dagegen auf die echten Geräte der Brücke.

### Der Gerätename ändert sich mit der Brücke

Wichtig für jeden Emulator, der Pads über **SDL** anspricht (RPCS3, PCSX2, DuckStation):
Über den Interposer meldete SDL den rohen Namen `Microsoft X-Box 360 pad`. Die Brücke legt
echte Kernel-Geräte an, und SDL erkennt sie an VID/PID (`0x45e/0x28e`) — es benutzt dann
den Namen aus **seiner eigenen Datenbank**: `Xbox 360 Controller`.

Eine Konfiguration, die noch auf den alten Namen zeigt, wird angenommen und ist an nichts
gebunden. Im RPCS3-Log sieht das so aus:

```
SDL: Found game pad 1: name='Xbox 360 Controller', path='/dev/input/event3'
SDL: Adding empty device: Microsoft X-Box 360 pad 1     ← zeigt ins Leere
```

**„Adding empty device" ist das Erkennungsmerkmal** — von außen ununterscheidbar von einem
defekten Controller. Überschreibbar bleibt der Name über `RPCS3_PAD_NAME`.

*EN: with the bridge in place SDL recognises the real kernel devices by VID/PID and uses
its own database name (`Xbox 360 Controller`) instead of the raw one the interposer
reported. A config still pointing at the old name is accepted but bound to nothing —
watch for "Adding empty device" in the log.*

**`NO_GAMEPAD` ist keine Lösung:** Der Schalter entfernt zwar die Attrappen, sein
`else`-Zweig setzt aber `SELKIES_GAMEPAD_ENABLED=false` und schaltet damit die Sockets ab,
aus denen die Brücke liest. Er würde den Controller vollständig abschalten.

*EN: gamepads cannot reach the emulators because `LD_PRELOAD` does not apply to a
statically linked AppImage runtime. `selkies-uinput-bridge.py` speaks the same socket
protocol and creates real kernel devices instead, started by `init/35-gamepad-bridge`.
Three things are required: the `uinput` module on the host, `/dev/uinput` in the container,
and `device_cgroup_rules: c 13:* rmw` — without the last one the container may create
devices but not open them, failing with EPERM even as root, which looks like a permission
bug but is Docker's device cgroup. Note that uinput devices appear in the host's `/dev`,
so the bridge creates the container-side nodes itself from sysfs. Selkies always offers
four pads even with no controller attached; connect the pad before launching a game,
because there is no udev inside the container. Do not set `NO_GAMEPAD`: it also disables
the gamepad sockets the bridge reads from.*

## Der Start-Dienst

`stream-agent.py` nimmt von Romseerr entgegen, welche Datei zu starten ist. Er
startet Prozesse — entsprechend ist er gebaut:

* ohne Token startet er **gar nicht**, Anfragen ohne Token bekommen `401`
* **keine Shell**: die Argumentliste geht unverändert an `execve`
* der Pfad wird über `realpath` aufgelöst und muss **innerhalb** der Bibliothek
  liegen — sonst wäre er ein Fernstart für beliebige Dateien

Er gehört **nicht ins offene Netz**.

### Das Token wechseln

Das Token ist das Einzige zwischen einer Anfrage und einem gestarteten Prozess auf dem
Host. Es steht an **zwei** Stellen, und ändert man nur eine, weist der Start-Dienst
Romseerr ab — der Stream-Knopf meldet dann, dass das Token nicht übereinstimmt.

Ein neues erzeugen (nichts erfinden, das ist der häufigste Fehler):

```bash
openssl rand -hex 32
```

Dann **in dieser Reihenfolge**, damit das Fenster ohne funktionierenden Stream so kurz
wie möglich bleibt:

1. **Romseerr zuerst**: *Einstellungen → Verbindungen → Streaming-Host* → im Feld
   *Start-Dienst* das `token=…` in der URL auf den neuen Wert setzen, speichern.
   Ab hier scheitert der Start — der Host kennt den neuen Wert noch nicht.
2. **Host**: `STREAM_AGENT_TOKEN` in der `.env` ersetzen, dann
   `docker compose up -d stream-agent` (nur dieser Dienst, der Rest läuft weiter).
3. **Prüfen**: einen Titel starten. Kommt „das Token stimmt nicht überein", steht auf
   einer der beiden Seiten noch der alte Wert.

Umgekehrt geht es auch, dauert aber länger: der Neustart des Dienstes ist der langsamere
Schritt, und in dieser Reihenfolge liegt er im Fenster.

**Beide Werte sind Geheimnisse.** Ein Token, das durch ein Terminalprotokoll, einen
Bildschirmabzug oder eine eingefügte Logzeile gelaufen ist, gilt als bekannt — dann ist
dieses Verfahren der Anlass, nicht die Ausnahme.

---

## Zertifikat erneuert sich selbst

Der Beiwagen `stream-certbot` erneuert alle 12 Stunden und legt das Ergebnis in
denselben Ordner, aus dem der Streaming-Host liest. `init/40-cert-watch` bemerkt den
geänderten Fingerabdruck und lädt den Webserver neu.

Bewusst **ohne Docker-Socket**: ein Container, der den Socket sieht, ist faktisch
root auf dem Host. Für einen nginx-Reload ist das kein ausreichender Grund.

DNS-01 funktioniert mit jedem Anbieter, für den certbot ein Plugin hat — `DNS_PLUGIN`
in der `.env` umstellen (`cloudflare`, `route53`, `digitalocean`, `rfc2136`, …).

### Warum certbot ein eigener Container bleibt

Zwei Container für eine Aufgabe sieht nach einem zu viel aus, und die Frage wurde
geprüft (#191). Ergebnis: **der Beiwagen bleibt.** Nachgemessen am laufenden Host:

- **Eine Installation im Streaming-Host würde nicht überleben.** `pip3` ist vorhanden
  (LSIOs Python unter `/lsiopy`), aber `/lsiopy` ist **kein Volume** — was dort landet,
  liegt in der beschreibbaren Schicht und ist nach dem nächsten Image-Update weg.
  Dasselbe Muster, das hier schon einmal einen per `apt` installierten Dolphin lautlos
  verschwinden ließ.
- **Nach `/config` auszuweichen verlagert das Problem nur.** Das Verfahren gibt es hier
  (`init/35-gamepad-bridge` legt python-evdev ABI-gebunden dort ab), aber certbot bringt
  `cryptography` mit — ein kompiliertes Paket. Ein Python-Wechsel im Image (aktuell 3.14)
  macht es unbrauchbar, und dann erneuert sich das Zertifikat still nicht mehr.
- **Was ein abgelaufenes Zertifikat kostet, ist überproportional.** Ohne HTTPS verweigert
  der Browser die WebCodecs-API: **Ton und Gamepad bleiben still, ohne Fehlermeldung.**
  Ein Ausfall, der genau dort nicht auffällt, wo er wehtut.

Dagegen steht als Gewinn: ein Container und `init/40-cert-watch` weniger. Das wiegt das
Risiko nicht auf.

**Sichtbar ist der Fehlschlag heute doppelt** — der Beiwagen steht dann nicht mehr auf
`Up`, und die Ablaufüberwachung schlägt unabhängig davon an. Wer den Umbau später doch
erwägt, muss die zweite Sicherung erst haben, bevor er die erste abschafft.

---
---

# Streaming host for Romseerr

For the platforms a browser **cannot** emulate — PlayStation 2, GameCube, Wii,
Switch. The emulator runs here with GPU access; the browser receives video and audio
and sends input back.

**Romseerr emulates nothing.** It resolves a title to a file and asks the launch
service to open it. No emulators, BIOS or firmware images ship with this project —
you provide those yourself, from hardware you own.

For everything EmulatorJS covers (NES through PSP) you do **not** need this; that is
what the Play button is for.

## Quick start

```bash
cp .env.example .env
$EDITOR .env                      # ROMS_DIR, GPU nodes, token, domain
docker compose --profile acme up -d
```

Without a domain: drop the profile flag and place your own certificate at
`data/config/ssl/cert.pem` + `cert.key`.

Then in Romseerr under **Settings → Connections**, set the streaming host URL
(`https://your-host:8902/`) and the launch service
(`http://your-host:8901/launch?token=<STREAM_AGENT_TOKEN>`).

## HTTPS is required

Over **HTTP** on a LAN address, Selkies refuses to start at all. And even where
video works, **audio and gamepad need the WebCodecs API**, which browsers gate
behind a secure context. The failure is quiet: video runs, audio never plays, the
controller is never detected, and nothing reports an error.

Use a real certificate (the certbot sidecar does DNS-01, so no inbound port is
needed), bring your own, or — for a quick look only — reach it as
`http://localhost:<port>` through an SSH tunnel.

> **DNS rebind protection**: many routers refuse to resolve public names that point
> at private addresses. Add an exception for your domain.

## The GPU trap

The container's X server is `Xvfb` **without DRI3**, so Mesa silently falls back to
`llvmpipe` — software rendering on the CPU. Everything appears to work, just far too
slowly. Check with `glxinfo -B | grep "OpenGL renderer"`.

VirtualGL solves it by rendering via EGL on the card. **It wants the card node, not
the render node** — `renderD*` yields `Invalid EGL device`. Both nodes therefore go
into `.env`.

### Update: the DRI3 switch works now, and it makes VirtualGL redundant

This section long claimed the image's own switch (`DRINODE` + `DISABLE_DRI3=false`) was
no alternative, because Xvfb segfaulted with Intel Arc cards. That no longer holds.
Measured on the running host (2026-08-10) with:

```
DRINODE=/dev/dri/renderD129
DISABLE_DRI3=false
```

Xvfb stays up, **DRI3 is present**, and `vulkaninfo --summary` reports
`Intel(R) Arc(tm) A310 Graphics (DG2)` on the Mesa driver. Emulators now start
**without `vglrun`** — Dolphin reports `Vulkan` in its window title.

**What that saves**, measured per thread from `/proc` on Dolphin (100 % = one full core):

| Thread | before (VirtualGL) | now (Vulkan direct) |
|---|---|---|
| Video thread | **pegged at ~100 %** | **5.7 %** |
| CPU thread | — | 51.7 % |

The video thread was the bottleneck: it cost per frame and per draw call rather than per
pixel — the signature of the VirtualGL round trip. This also retires the planned switch
to a real Xorg (#169): **the goal was reached without it.**

`init/10-virtualgl` and `/opt/VirtualGL` remain in the image but no emulator uses them.
They stay for now as a fallback; before removing them, check with `ps aux | grep vglrun`
that nothing still launches through them.

### xemu (Xbox) needs two extra things

Measured on the running host (#300). `init/22-xemu-vorbereiten` handles both:

1. **`libusb-1.0.so.0`.** Every other emulator AppImage ships its libraries; xemu's does
   **not** ship libusb, and the container has none. Without it the launch dies instantly
   with `error while loading shared libraries` — the stream opens and stays empty. The
   script borrows it from an emulator that does ship it and places a **copy** in
   `/config/lib`; writing to `/usr` is the trap that once made an `apt`-installed Dolphin
   vanish silently.
2. **`xbox_hdd.qcow2`.** The Xbox will not boot without a hard disk. The image is empty,
   formatted, and comes from the xemu project itself; the script fetches it once.

Then there is **audio**: ALSA loads its Pulse module through `libpulse.so.0`, which needs
`libpulsecommon-<version>.so`. That one is present on the system but in a **subdirectory**
outside the search path — which is why xemu stayed silent while PulseAudio was running.
The agent therefore sets `LD_LIBRARY_PATH` to both paths for Xbox.

> **Do not put another emulator's whole lib directory on the path.** That was tried: its
> `libpulse.so.0` shadows the system one and does not match the system
> `libpulsecommon` — `undefined symbol: pa_in_valgrind`, and audio breaks again. Exactly
> **one file** is borrowed, never a directory.

### And above all: the right BIOS

**Every retail BIOS dump yields a black screen** or the console's "Your Xbox requires
service" — retail images demand a **locked** hard disk, and the supplied image is
unlocked. All 14 combinations were measured on the running host (7 BIOS × 2 MCPX),
scored by mean brightness inside the window:

| BIOS | MCPX 1.0 | MCPX 1.1 |
|---|---|---|
| 5838, 5713, 5530, 5101, 4817 | black | black |
| 4034 | 4.5 | black |
| 3944 | 4.3 | 8.4 (service notice) |
| **COMPLEX 4627** | **232** | 65 |

So a **patched** BIOS is required — `COMPLEX 4627` together with **MCPX 1.0**. The
firmware check cannot catch this: it verifies sizes, and a retail dump has the same size.

> **The window title is not a success criterion.** It always reads `xemu | v0.8.136` —
> welcome dialog, error, or running game alike, because xemu draws its dialogs into the
> window rather than as separate X windows. To check whether anything is actually
> running, measure **brightness inside the window** (black ≈ 0), or compare two captures:
> **bit-identical frames under high CPU load mean a frozen framebuffer, not a running
> game.**

Beyond that a dedicated `xemu.toml` is **not** required — with the disk image present,
xemu starts without a config file and without `eeprom.bin`, which it creates itself. The
initial `Failed to load BIOS '(null)'` was a knock-on effect of the missing disk.

## Other surprises

* Init scripts belong in `/custom-cont-init.d`; the older `/config/...` path is
  silently ignored.
* AppImages need FUSE, which containers lack. We extract them rather than granting
  `SYS_ADMIN`.
* **One primary client only** — a second browser on the same URL disconnects the
  first. Use the sharing links in the sidebar for viewers and players 2–4.
* Some emulators need a real **mouse click** in the window before keyboard or
  gamepad input registers.
* Connect your gamepad and press a button **before** launching a title: browsers
  only expose gamepads after a button press, and emulators enumerate at startup.

## Checking audio

Browser-side indicators mislead here. Measure in the container with `parec` on
`output.monitor` and count non-zero bytes: a large number means audio is flowing and
the problem is the browser (almost always: no HTTPS); zero means the source is
silent.

## The launch service

`stream-agent.py` starts processes, so: it refuses to run without a shared token,
never uses a shell, and resolves the path with `realpath`, rejecting anything
outside the ROM library. Do not expose it to the open internet.

### Rotating the token

The token is the only thing between a request and a process starting on the host. It lives
in **two** places, and changing one alone makes the launch service reject Romseerr — the
stream button then says the token does not match, rather than showing a generic failure.

Generate one (do not invent it — that is the common mistake):

```bash
openssl rand -hex 32
```

Then, **in this order**, so the window without a working stream stays as short as possible:

1. **Romseerr first**: *Settings → Connections → streaming host* → set `token=…` in the
   *launch service* URL to the new value and save. Launches fail from here on: the host
   does not know the new value yet.
2. **Host**: replace `STREAM_AGENT_TOKEN` in `.env`, then
   `docker compose up -d stream-agent` (that service only; the rest keeps running).
3. **Check**: start a title. "The token does not match" means one side still holds the old
   value.

The reverse order works too but takes longer: restarting the service is the slower step,
and this way it falls inside the window.

**Both values are secrets.** A token that has passed through a terminal scrollback, a
screenshot or a pasted log line counts as known — and then this procedure is the occasion,
not the exception.

## Installing emulators

**A fresh host ships with no emulators and downloads none.** You pick them in Romseerr
under **Settings → Connections**, one click each.

That is deliberate: which emulators end up on your machine carries legal weight in some
jurisdictions, and the project does not make that choice for you silently.

For unattended deployments the `INSTALL_*` switches in `.env` fetch automatically at
container start. All default to `false`.

Two need a URL from you because their source cannot be resolved automatically: **RPCS3**
(no GitHub release assets; the official direct link refuses automated requests) and the
**Switch emulator** (deliberately without a built-in address). Romseerr shows these as
"URL required".

## What has actually been tested

"Installed" is not "works". This table records what was tried **with a real title** —
picture in the browser, sound measured at the sink (not judged by ear), controller
pressed in-game.

| Platform | Emulator | Picture | Sound | Controller | Note |
|---|---|---|---|---|---|
| PlayStation 1 | DuckStation | ✅ | ✅ | ✅ | |
| PlayStation 2 | PCSX2 | ✅ | ✅ | ✅ | |
| GameCube | Dolphin | ✅ | ✅ | ✅ | |
| Wii | Dolphin | ✅ | ✅ | (⁠—⁠) | controller not checked separately — same emulator and same mapping as GameCube |
| PlayStation 3 | RPCS3 | ✅ | ✅ | ✅ | |
| Switch | Eden | ✅ | ✅ | (⁠—⁠) | controller not checked separately |
| Nintendo 3DS | Azahar | ❌ | ❌ | — | emulator starts, **no title playable** — see below |
| Dreamcast | Flycast | — | — | — | no titles in the library, nothing to test |
| Xbox | xemu | ✅ | ✅ | ✅ | needs **COMPLEX 4627 + MCPX 1.0** — retail BIOS stays black |
| Wii U | Cemu | — | — | — | no titles in the library |
| PS Vita | Vita3K | — | — | — | no titles in the library |

A `—` means **untested**, not "broken". The bottom four rows are untested because there
is simply nothing there to start.

### Two traps that look like a broken host

Both are **title** problems, not emulator problems — the emulator runs fine in both
cases, the game does not:

- **3DS: encrypted ROMs.** Azahar starts, but every title fails, and differently per
  format: a cartridge dump shows an `App Encrypted` dialog, an eShop title writes
  `Failed to determine system mode (Error 8)` to the emulator log and opens no window at
  all, and a `.cia` reports `CIA must be installed before usage` — CIAs have to be
  installed first, they do not boot directly. The key set (`aes_keys.txt`, `boot9.bin`)
  was complete throughout, so this is the files, not the firmware. The only fix lies
  outside this project: use decrypted dumps.
- **Wii: NKit-compressed ISOs.** Dolphin opens an `NKit Warning` dialog instead of the
  game. The same library in `.wbfs` starts without further ado.

### Where the host tells you no game is running

The launch itself **succeeds** in these cases — the emulator is running, after all. So
`/launch` still answers `ok`; what failed is the title, and that shows up in `/status`:

```
window        ""             nothing started yet
              "pending"      launch in progress, window still expected
              "ok"           a game window is up
              "dialog"       error dialog — window_detail holds its title
              "kein-fenster" nothing visible appeared at all
              "unbekannt"    the window step itself did not get through
window_detail plain text; for "dialog" the dialog's title
```

So an encrypted 3DS ROM yields `window: "dialog"` and `window_detail: "App Encrypted"` —
the very information that previously sat on the emulator's own screen and reached nobody.

Dialogs are recognised by window type `_NET_WM_WINDOW_TYPE_DIALOG` rather than by known
error strings, since a string list would be wrong in every new emulator release. This
also fixes a second annoyance: the error dialog used to be pulled to fullscreen *itself*
(at 293x101 it is large enough to pass as a window), which is precisely what arrived as
an "empty stream".

## The library must be the same on both sides

Romseerr and the streaming host both mount the ROM library. **Both must mean the same
root** — otherwise the emulator does not start, and it does not look like a fault:
Romseerr dutifully opens the desktop and the title stays closed.

```
Romseerr     : /path/to/library  ->  /roms
Stream host  : /path/to/library  ->  /roms     # the SAME source
```

Mounting `…/library/roms` for Romseerr and `…/library` for the streaming host is wrong.
Both are called `/roms` inside the container but mean different directories.

Romseerr now sends the path **relative to the root**, so the mount point no longer has
to match. The root still does — and when it does not, the launch service says so plainly
instead of merely reporting "not found".

## Controllers

A container may not create input devices. Selkies solves this with a **preloaded
interposer** that intercepts opening `/dev/input/js*` and pulls the data from the
browser over a unix socket — no `uinput`, no elevated privileges.

Selkies documents three variables; the image sets two and omits `SDL_JOYSTICK_DEVICE`.
The launch service supplies it, otherwise SDL has no hint which device is meant.

### Check page: what does the browser see?

```
https://<host>:<HTTPS_PORT>/gamepad-check.html
```

It shows secure context, focus, every gamepad reported, and **live button activity**.
That splits the fault cleanly: if the pad appears there, the machine and browser are
fine and the problem is the streaming page or the transport. If it does not, nothing can
reach the streaming host and looking there is wasted effort.

Why the page exists at all: **the stream page captures the keyboard** and forwards it to
the remote session, so `F12` never reaches the browser. The page where you would want the
console is the one where you cannot open it. This one needs no console.

**Order matters, and it is not intuitive:**

1. Connect the controller to your own machine
2. **Press a button on it** while the stream page has focus
3. **Then** start the title

The browser's Gamepad API only reports a pad after a button press, and most emulators
enumerate devices once at startup. Start first and the pad stays silent with nothing
actually broken — restarting the title is enough.

Check in the browser with `navigator.getGamepads()`. If nothing shows there, the
container is not the problem.

### The interposer is not enough: the uinput bridge

The interposer only works for dynamically linked programs. The emulators here are
AppImages with a **statically linked** runtime (`AppRun` is `static-pie`), and `LD_PRELOAD`
has no effect on those — measured: no interposer in the running process, zero input
devices opened, SDL finds no pads.

`selkies-uinput-bridge.py` speaks the same socket protocol and creates **real kernel
devices**, which need no preloading. `init/35-gamepad-bridge` starts it.

Three requirements, and the third is the one that costs an afternoon:

| | |
|---|---|
| `uinput` module **on the host** | `modprobe uinput`, persist via `/etc/modules-load.d/` |
| `/dev/uinput` in the container | listed under `devices:` |
| `device_cgroup_rules: c 13:* rmw` | the container may otherwise create devices but not open them |

Without the cgroup rule, `open()` fails with `EPERM` **even as root**, while the node sits
there with `crw-rw-rw-`. That is not a file permission problem — Docker's device cgroup
only admits what is listed under `devices:`. Minor numbers change on every connect, so
only the whole input major works. Be aware this also grants read access to the host's own
input devices; check `cat /proc/bus/input/devices` first.

Two behaviours that look like faults but are not:

* **The devices appear in the host's `/dev`**, because uinput creates them in the kernel
  and the container has its own `/dev`. The bridge reads the device number from
  `/sys/devices/virtual/input/<sysname>/…/dev` and creates the container-side node itself.
  On disconnect it removes only the nodes it created.
* **Selkies always offers four pads**, even with no controller attached, so four devices
  always exist. This is deliberate: there is no `udev` in the container, so an already
  running emulator would never notice a device appearing later. Connect the pad first,
  then launch the title.

Do **not** set `NO_GAMEPAD` to get rid of Selkies' dummy nodes: its `else` branch also
sets `SELKIES_GAMEPAD_ENABLED=false`, which disables the very sockets the bridge reads.

The probe checks the whole chain without a controller attached and names the missing link.
It binds its own socket and leaves the production ones alone:

```bash
docker exec -u 0 stream-host python3 /opt/gamepad-bridge-probe.py
# OK Bruecke verbunden
# OK Geraeteknoten angelegt: /dev/input/event7
# OK Eingaben kommen als uid 1000 an — die Kette steht.

docker exec stream-host tail -20 /config/gamepad-bridge.log
docker exec stream-host ls -l /dev/input/
docker exec -u 1000 stream-host head -c1 /dev/input/event3   # EPERM = cgroup rule missing
```

## BIOS and firmware

Several emulators do not start **at all** without firmware, and that shows up as a black
screen rather than an error. Romseerr therefore lists, per platform, what is missing —
under **Settings → Connections**.

**This project does not obtain BIOS images.** There is no authorised source for PS2,
Xbox, Dreamcast, 3DS, Switch or Wii U; a script could only pull them from sites
distributing them without permission. Every emulator project refuses this, and so does
this one. What is automated here is the real work: **which** file, does it look intact,
and **where** does it belong.

| Route | For |
|---|---|
| **Vendor** | **PS3** only: Sony publishes its own system software. One click. |
| **Upload** | Everything else. You pick the file; Romseerr passes it through and **stores nothing**. |

Files land in `/config/firmware/<platform>/` and are copied from there to wherever the
emulator looks. That separation is deliberate: reinstalling an emulator does not take
the firmware with it.

**PS Vita:** Vita3K **downloads nothing** — its source opens a file dialog
(`firmware_install_dialog.cpp`). There is nothing to automate beyond the import.

**What is checked, and what is not.** Size is checked. That catches truncated downloads
and obviously wrong files, which is what it is for. It does **not** prove the contents
are correct — hence the state is "ok", not "verified". No checksum list is shipped: in
practice it would function as an index of which copy is "the right one".

By hand:

```bash
docker exec stream-host /custom-cont-init.d/25-firmware --status
docker exec stream-host /custom-cont-init.d/25-firmware --import dreamcast /path/dc_boot.bin
docker exec stream-host /custom-cont-init.d/25-firmware --vendor ps3
```

## Updating and rolling back emulators

Runs on every container start, and can be triggered from Romseerr under
**Settings → Connections**. Two safety nets, because an update can also break
things: a failed download or extraction leaves the working build untouched (it is
extracted beside the old one and swapped only on success), and the **previous
build is kept** — exactly one generation — so a regression is one click away from
being undone, with no network and no version hunting.

To stay on a specific build indefinitely, set `<NAME>_URL` (e.g. `PCSX2_URL`) to
the full asset URL; it beats the release lookup even with auto-update on.

## Certificate renewal

The `stream-certbot` sidecar renews every 12 hours into the same directory the
streaming host reads from; `init/40-cert-watch` notices the changed fingerprint and
reloads the web server. Deliberately **without a Docker socket** — a container that
can see the socket is effectively root on the host, which a reload does not justify.

### Why certbot stays a separate container

Two containers for one job looks like one too many, and the question was examined
(#191). The answer: **the sidecar stays.** Measured on the running host:

- **An install inside the streaming host would not survive.** `pip3` is there (LSIO's
  Python under `/lsiopy`), but `/lsiopy` is **not a volume** — anything installed there
  sits in the writable layer and is gone after the next image update. The same pattern
  that once made an `apt`-installed Dolphin vanish silently.
- **Moving it to `/config` only relocates the problem.** The technique exists here
  (`init/35-gamepad-bridge` caches python-evdev there, keyed by ABI), but certbot pulls
  in `cryptography` — a compiled package. A Python change in the image (currently 3.14)
  breaks it, and the certificate then quietly stops renewing.
- **An expired certificate costs disproportionately.** Without HTTPS the browser gates
  the WebCodecs API: **audio and gamepad go silent, with no error shown.** A failure
  that hides exactly where it hurts.

Against that, the gain is one container and `init/40-cert-watch` fewer. That does not
outweigh the risk.

**Failure is visible twice today** — the sidecar drops out of `Up`, and certificate
expiry monitoring alerts independently. Anyone revisiting this later needs the second
safeguard in place *before* removing the first.
