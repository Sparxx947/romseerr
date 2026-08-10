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

Der eingebaute DRI3-Schalter des Images (`DRINODE` + `DISABLE_DRI3=false`) ist
**keine** Alternative: mit Intel-Arc-Karten und aktuellem Mesa stürzt Xvfb dabei
mit `Segmentation fault` ab.

---

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

**Der Engpass ist die CPU, und zwar vermeidbar.** Die Kodierung kostet rund
**1,2 Kerne je Sitzung** (124 % → 371 % beim Öffnen beider Streams). Das liegt daran,
dass Selkies hier in Software kodiert:

```
[x11] No GPU Encoder available -> Using CPU Software Encoding.
[x11] Encoder: CPU | Mode: H264 | Res: 1920x1080 | FPS: 30
```

`VCS` bleibt in **allen** Messungen bei 0 % — die Video-Engine der Arc liegt brach.
Ursache ist dieselbe Bauart wie beim DRI3-Problem: Selkies leitet den GPU-Index aus dem
**Namen** des Knotens ab (`parse_dri_node_to_index`: `renderD129` → Index 1), im
Container existiert aber nur ein Knoten, der dort Index 0 ist. Das Aufnahmemodul sucht
Karte 1, findet keine und weicht auf die CPU aus.

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

The image's own DRI3 switch is not an alternative: with Intel Arc cards and current
Mesa, Xvfb segfaults.

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
