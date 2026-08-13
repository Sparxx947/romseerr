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

## Was hier liegt

Jede Datei trägt einen zweisprachigen Kopf, der ihre Existenz begründet — das hier ist
nur die Landkarte, damit man weiß, wo man nachsieht.

| Datei | Wozu |
|---|---|
| `docker-compose.yml` | der Stack: Selkies-Desktop, Start-Dienst, optional `acme` (certbot) und `seat2` |
| `stream-agent.py` | der **Start-Dienst**, den Romseerr aufruft: `/status`, Titel öffnen, 3DS entschlüsseln, CIA installieren, PS-Vita-Titelkennung auflösen |
| `launch-profile.py` | **Startprofil je Emulator**: Controller-Belegung und regionsrichtiges BIOS. Eine Zuordnung je Emulator genügt für alle Pads, weil Browser und Selkies bereits auf ein Xbox-Pad normieren |
| `emu-setup` | einen Emulator **ohne Spiel** öffnen, um Tasten zu belegen — mit derselben Umgebung wie ein Spielstart. Vom Desktop oder über SSH gestartet sieht er das Pad überhaupt nicht |
| `selkies-uinput-bridge.py` | die **uinput-Brücke**: macht aus dem virtuellen Pad ein Gerät, das die Emulatoren finden |
| `gamepad-bridge-probe.py` | prüft dieselbe Brücke, ohne einen Emulator zu starten |
| `renew.sh` | läuft im certbot-Beiwagen. **Nicht** bloß `certbot renew`: das erneuert nur im eigenen Volume, der Host liest aber aus `/config/ssl` — ohne Kopie läuft das ausgelieferte Zertifikat still ab |
| `init/` | Startschritte in fester Reihenfolge, siehe unten |
| `web/` | die Seite, die der Browser bekommt |

Die Schritte unter `init/` laufen nummeriert, und die Reihenfolge ist jedes Mal aus einem
Fehlschlag entstanden:

| Schritt | Wozu |
|---|---|
| `05-web` | richtet die Web-Wurzel her. **Kein Bind-Mount in `/usr/share/selkies/web/`** — das Basis-Image löscht das Verzeichnis beim Start und legt es neu an; ein Mountpunkt darin überlebt das `rm -Rf` und lässt das `cp -a` ins Leere laufen |
| `10-virtualgl` | ermittelt den Card-Knoten. Ohne VirtualGL rendert Mesa auf der CPU |
| `23-3ds-entschluesseln` | holt die 3DS-Werkzeuge (`decrypt_3ds.py`, `3ds-decrypt-cia`) |
| `25-firmware` | legt BIOS und Firmware an ihren Platz |
| `30-agent` | startet den Start-Dienst. Das Token wird **aus einer Datei** gelesen, nicht ins Skript geschrieben |

## What is in here

Every file carries a bilingual header explaining why it exists; this table is only the map.

| File | Purpose |
|---|---|
| `docker-compose.yml` | the stack: Selkies desktop, launch service, optional `acme` and `seat2` |
| `stream-agent.py` | the **launch service** Romseerr calls: `/status`, opening titles, 3DS decryption, CIA install, resolving the PS Vita title id |
| `launch-profile.py` | **per-emulator launch profile**: controller mapping and region-correct BIOS. One mapping per emulator covers every pad, because the browser and Selkies already normalise to an Xbox pad |
| `emu-setup` | open an emulator **without a game** to bind keys, with the same environment a launch gets. Started from the desktop or over SSH it cannot see the pad at all |
| `selkies-uinput-bridge.py` | the **uinput bridge**: turns the virtual pad into a device emulators can find |
| `gamepad-bridge-probe.py` | checks that bridge without starting an emulator |
| `renew.sh` | runs in the certbot sidecar. **Not** just `certbot renew`: that only updates certbot's own volume while the host reads from `/config/ssl`, so the served certificate goes stale in silence |
| `init/` | ordered start-up steps (`05-web`, `10-virtualgl`, `23-3ds-entschluesseln`, `25-firmware`, `30-agent`) |
| `web/` | the page the browser gets |

Each ordering constraint in `init/` came out of a failure; the German table above says which.

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

## Ein Update darf den Emulator nicht löschen

`installiere()` entpackt nach `<name>.neu` und ruft dann `generationen_schieben`, das die
bisherige Fassung nach `.alt1` räumt. **Ohne die abschließende Umbenennung `.neu` → `<name>`
ist ein Update eine Löschung** — genau das war bis 2026-08-12 der Fall.

Die Folge war unsichtbar: `init/30-agent` setzt `EMU_<PLATTFORM>` nur, wenn
`<name>/AppRun` existiert. Fehlt das Verzeichnis, entsteht die Variable nicht, und die
**ganze Plattform** fällt aus der Liste des Agenten. Gemessen: `ps2` und `ps3` fehlten einen
Tag lang, während 17 PS3-Titel in der Bibliothek lagen. Kein Fehler, kein Fenster, keine
fehlende Datei — der Streamen-Knopf erschien einfach nicht mehr.

Merkregel: **Wer zuletzt aktualisiert wurde, war der Kaputte.**

`/status` nennt deshalb jetzt auch `platforms_missing`, und der Agent schreibt es beim Start
ins Protokoll. Ein Fehlen ist kein Alarm — wer keinen PS2-Emulator installiert, soll nichts
Rotes sehen. Es macht nur den Unterschied zwischen „nicht eingerichtet" und „abhanden
gekommen" überhaupt sichtbar.

*Without the final rename an update deletes the emulator it was meant to update, and the
platform silently disappears from the agent. `/status` now also reports what is missing.*

## Entpackte AppImages brauchen `APPDIR` und `APPIMAGE`

`linuxdeploy` erzeugt bei manchen Emulatoren ein `AppRun.wrapped`, das das Programm **nur**
startet, wenn `$APPIMAGE` gesetzt ist:

```sh
if [ "${APPIMAGE}" != "" ]; then "${APPDIR}/usr/bin/Vita3K" $@ ; fi
```

Diese Variable setzt die AppImage-Laufzeit, wenn das Abbild sich selbst startet. Hier läuft
aber der **entpackte Baum** — dann ist sie leer, der Zweig wird übersprungen, und der Prozess
endet mit **Exit 0 und ohne jede Ausgabe**:

```
$ timeout 20 /config/emulators/vita3k/AppRun > out 2> err
exit=0    stdout: 0 Bytes    stderr: 0 Bytes
```

Das war das „öffnet kein Fenster" — und es sah nach einem defekten Emulator aus statt nach
einer Verpackungslücke. Mit gesetzten Variablen startet Vita3K normal.

Betroffen sind **vita3k, cemu und rpcs3**. Gesetzt wird es über den Helfer `apprun()` für
**alle** Emulatoren: `APPDIR` auf den entpackten Baum zu zeigen ist ohnehin richtig, und drei
Sonderfälle wären die Sorte Wissen, die beim nächsten neuen Emulator fehlt.

*Some extracted AppImages only run when `$APPIMAGE` is set and otherwise exit 0 with no
output at all. Set for every emulator rather than for the three known ones.*

## Controller: eine Kennung, acht Geräte

Alle acht Joystick-Geräte im Container sind **identisch** — `bus=0003 vendor=045e
product=028e`, „Microsoft X-Box 360 pad". Sie tragen deshalb dieselbe SDL-Kennung
`030081b85e0400008e02000000010000`. Das ist kein Zufall, sondern die Folge der zwei
Normierungen davor: Der Browser bildet jedes physische Pad auf das „Standard Gamepad" ab,
Selkies reicht das als ein virtuelles Xbox-Pad herein.

**Woran das schiefgeht:** Ein Emulator, der sich eine Kennung merkt, kann eine merken, die
es nicht mehr gibt. Bei xemu stand auf Port 1 — dem Platz von Spieler 1 —
`000081b84d6963726f736f6674205800`: Bustyp `0000` und der ASCII-Name statt Vendor/Product,
so bildet SDL eine Kennung für ein Gerät, das es **nicht identifizieren konnte**. Die Ports
2 bis 4 hatten die richtige.

Ob xemu in so einem Fall auf das erste verfügbare Pad zurückfällt, ist **nicht gemessen**.
Repariert wird es trotzdem: Eine Bindung, die ein abwesendes Gerät benennt, ist unabhängig
vom Rückfall falsch. `xemu_apply` legt Port 1 auf die gebrückte Kennung und lässt Ports 2
bis 4 in Ruhe — wer sie für einen zweiten Spieler gesetzt hat, behält das.

*All eight joystick devices are identical and share one SDL GUID. xemu had player 1 bound to
a GUID no present device carries — SDL's fallback form for a device it could not identify.
Whether xemu falls back to the first available pad is not measured; a binding naming an
absent device is wrong either way.*

## Vollbild: gemessen, nicht angenommen

Jeder Start misst nach dem Fensterschritt, **wie viel des Bildschirms der Emulator
übernommen hat**, und hilft nur nach, wenn zu wenig herauskommt:

```
[grundbild] Grundbild aufgenommen: 1920x1080, 75.0 % nicht schwarz
[fenster]   8 Fenster auf 1920x1080, ohne Rahmen, Panel ausgeblendet
[vollbild]  71.7 % vom Emulator -> F11 -> 100.0 %
```

**Die Fenstergröße beweist hier nichts.** `xdotool getwindowgeometry` meldete in jedem
Fall, der sich als falsch herausstellte, brav `1920x1080` — während das Bild kleiner war.
Gemessen wird deshalb der Bildinhalt.

**Und die bemalte Fläche allein beweist ebensowenig (#495).** Bis 2026-08-13 wurde in einer
`xwd -root`-Aufnahme der Rahmen der nicht-schwarzen Bildpunkte gesucht — aber ein
Hintergrundbild ist nicht schwarz. Am laufenden Host gemessen, drei Zustände:

| Zustand | alte Messung | neue Messung |
|---|---|---|
| leerer Desktop, kein Emulator | 99,28 % | **0,06 %** |
| xemu, Bild 1280 × 963 auf dem Desktop | 99,28 % | **74,87 %** |
| Flycast, echtes Vollbild | 73,56 % | **99,97 %** |

Die alte Zahl war also nicht bloß ungenau, sondern **verkehrt herum**: Der leere Desktop
stand über der Schwelle, ein wirklich bildschirmfüllender Emulator darunter.

Deshalb wird jetzt gegen ein **Grundbild** gemessen. Der Agent nimmt es zwischen dem
Beenden des Vortitels und dem Start des neuen auf — der einzige Augenblick, in dem der
Desktop wirklich leer ist. Ein Bildpunkt zählt als „noch Desktop", wenn er unverändert ist
**und** im Grundbild nicht schwarz war; schwarz auf schwarz ist keine Auskunft, das malt
ein Emulator genauso. Der Rest gehört dem Emulator.

Die Aufnahme **lehnt sich selbst ab**, wenn `_NET_CLIENT_LIST` außer Panel und Desktop noch
ein Fenster führt oder der Schirm fast ganz schwarz ist. Beides wäre eine perfekte
Täuschung: Ein Grundbild mit dem Spiel darin ließe jeden folgenden Start als „nichts
übernommen" erscheinen, ein schwarzes jeden als „alles übernommen". Fehlt das Grundbild,
unterbleibt die Korrektur und das Log sagt es (`[vollbild] nicht messbar`).

> **Zwei Fallen beim Lesen der Aufnahme, beide gemessen.**
>
> **Die Zeilenlänge ist aufgefüllt.** Der xwd-Kopf nennt `bits_per_pixel` 24 und
> `bytes_per_line` 7680 bei 1920 Punkten Breite — genutzt sind davon 1920 × 3 = 5760 Byte,
> der Rest ist Rand. Die Schrittweite muss deshalb aus `bits_per_pixel` kommen. Wer sie aus
> `bytes_per_line / Breite` rechnet, liest über die Zeile hinaus: das Bild erscheint auf
> drei Viertel der Breite gestaucht, rechts schwarz, und 25 % der Punkte lesen sich als
> reines Schwarz. *(Genau dieser Irrweg stand in einer Zwischenfassung dieses Abschnitts,
> mit reproduzierbaren Zahlen. Aufgefallen ist er erst, als das dekodierte Bild angesehen
> wurde statt nur gerechnet.)*
>
> **Bitgleichheit ist zu spröde.** Grundbild und Messbild entstehen bei verschiedenen
> Farbtiefen — der leere Desktop liefert 24 bpp, ein Emulator mit 32-Bit-Visual im Vollbild
> bringt `xwd -root` auf 32 bpp —, und der Verlauf des Hintergrundbildes wird dabei anders
> gerastert. Im sichtbaren Stück Hintergrundbild neben xemu sind nur **7,2 %** der Punkte
> bitgleich, 63,4 % liegen innerhalb von 8, 85,9 % innerhalb von 16; auf xemus weißer
> Fläche liegt bei Toleranz 16 **kein einziger**. Ohne Toleranz meldete die Messung für
> diesen Zustand 95,13 % statt 74,87 %. Die Toleranz steht auf **8**: 16 träfe xemus wahren
> Wert (59,4 %) besser, brächte Flycast aber auf 90,62 % — einen halben Punkt über der
> Schwelle.

Und der im Issue vorgeschlagene Weg, die Messung **auf die Fenstergeometrie zu
beschränken**, wurde nachgemessen und **verworfen**: xemus X-Fenster *ist* 1920 × 1080
(`xwininfo` bestätigt es), bemalt wird davon aber nur rund 1280 × 963. Der Rest bleibt
unberührt und zeigt weiter das Hintergrundbild — der Desktop liegt also *innerhalb* des
Fensters. Auf die Fenstergeometrie beschränkt kam derselbe Fehlwert heraus: **99,64 %**.

**Warum erst gemessen und dann F11 — nicht einfach immer F11:** F11 ist ein **Umschalter**.
Ein Emulator, bei dem der Fenstertrick schon gewirkt hat, fiele dadurch wieder heraus. Die
Messung ist also nicht zusätzliche Vorsicht, sondern das, was die Korrektur ungefährlich
macht. Und sie gilt für **jeden** Emulator, auch für die, die nie jemand ausprobiert hat —
sie brauchen keine vorab ausgefüllte Zeile in einer Tabelle.

> **Was die Fläche auch jetzt nicht kann (#493).** Ein Titel, der noch die Disc bootet, ist
> schwarz. Schwarz auf hell *ist* eine Änderung, schwarz auf schwarz nicht — der Bootschirm
> bleibt damit ein Anlass für ein F11, das dem Emulator sein eigenes Vollbild nähme.
> Deshalb gilt weiterhin: **ein Fenster mit `_NET_WM_STATE_FULLSCREEN` bekommt kein F11.**
> Nachgemessen: xemu, Azahar und Eden tragen den Zustand nicht, DuckStation, PCSX2 und
> Flycast schon.
>
> **Die alte Prüftabelle aus #429 ist damit hinfällig** (Azahar 53,3 %, Eden 88,6 %, xemu
> 960 von 1920). Ihre Zahlen stammen aus der Messung mit dem verschobenen Lesen und belegen
> nicht, was sie zu belegen scheinen. Neu erhoben ist bisher nur xemu.

*Every launch measures how much of the screen the emulator has taken over and only corrects
when it falls short. Window geometry proves nothing here — it reported 1920x1080 in every
case that turned out wrong — and neither does the painted area on its own: measured on the
running host, a bare desktop scored 99.28 % while a genuinely fullscreen Flycast scored
73.56 %. The number was inverted, not merely imprecise. The measurement now compares the
screen against a baseline picture of the empty desktop, taken by the agent between stopping
the previous title and starting the new one; a point counts as "still desktop" when it is
unchanged (within a per-channel tolerance of 8) AND was not black in the baseline. The
capture refuses itself while any application window is listed in `_NET_CLIENT_LIST` or
while the screen is nearly all black, because a baseline with the game in it would mark
every later launch as perfect. Two traps when reading the capture, both measured: the row
length is padded, so the pixel stride must come from `bits_per_pixel` and not from
`bytes_per_line / width` — the latter reads past the row and decodes the image squeezed
into three quarters of the width; and exact pixel equality is too brittle, because baseline
and measurement are captured at different colour depths and a gradient wallpaper dithers
differently (only 7.2 % of visibly unchanged wallpaper points are bit-identical). Finally,
restricting the measurement to the window geometry — the fix proposed in #495 — was
measured and rejected, because xemu leaves most of its own 1920x1080 window unpainted and
the wallpaper shows through inside it (99.64 %). F11 remains a toggle, so a window carrying
`_NET_WM_STATE_FULLSCREEN` is still left alone.*

## Was noch überrascht

**Init-Skripte gehören nach `/custom-cont-init.d`.** Der ältere Pfad
`/config/custom-cont-init.d` ist bei LinuxServer abgeschaltet — dort abgelegte
Skripte werden kommentarlos ignoriert. Das Compose hängt das Verzeichnis richtig ein.

**AppImages brauchen FUSE, Container haben keins.** Der naheliegende „Fix" wäre
`--cap-add SYS_ADMIN` — viel zu viel für einen Spielestarter. `init/20-emulators`
entpackt AppImages stattdessen (`--appimage-extract`) und startet `AppRun`.

**Ein Wii-U-Titel hat oben keine Startdatei.** Er trägt `code/`, `content/`, `meta/` —
nichts mit einer bekannten Endung. Der Start-Dienst löst deshalb `code/*.rpx` auf; der
Name ist je Titel anders (`Kinopio.rpx` bei Captain Toad), ein fester Pfad genügt nicht.
Liegen **mehrere** `.rpx` darin, sagt er ab statt zu raten.

Dabei wird bewusst **kein `glob`** benutzt: Bibliotheksnamen tragen eckige Klammern —
`Captain Toad Treasure Tracker [AKBP01]` — und `[AKBP01]` ist für `glob` eine
Zeichenklasse, kein Text. Das Muster passt dann auf nichts, und zwar lautlos.

**Updates und DLC werden abgelehnt, bevor Cemu ratlos wird.** Die ersten acht Hexziffern
der Titelkennung sagen, was vorliegt:

| Präfix | Bedeutung | startbar |
|---|---|---|
| `00050000` | Basisspiel | ja |
| `0005000E` | Update | nein — patcht ein Basisspiel |
| `0005000C` | DLC | nein |
| `0005001B` | Systemtitel | nein |

Sie steht im Klartext in `code/app.xml`. **Gelesen wird `app.xml`, nicht `meta.xml`** —
die beiden können sich widersprechen, und genau das war der Fall beim einzigen
Wii-U-Titel des Bestands: `meta.xml` behauptete `00050000…` (Spiel), `app.xml` sagte
`0005000E…` (Update). Cemu antwortet darauf mit `Unable to mount title` und nennt eine
Datei — eine Meldung, die zur Suche am Pfad verleitet, wo nichts ist.

*EN: a Wii U title has no boot file at its top level, so the launcher resolves
`code/*.rpx`; the name differs per title and several matches are refused rather than
guessed at. Deliberately without `glob`, because library folder names contain `[...]`,
which glob reads as a character class — the pattern then matches nothing, silently.
Updates (`0005000E`) and DLC (`0005000C`) are refused by name, read from `code/app.xml`
in plain text. `app.xml` rather than `meta.xml`, because the two can disagree — and did:
the only Wii U title here claims to be a game in `meta.xml` and is an update in
`app.xml`. Cemu's answer to that, `Unable to mount title`, names a file and hides the
cause.*

**„Der Emulator ordnet sein Pad selbst zu" ist eine Annahme, bis sie gemessen ist.** Für
Eden (Switch) stand das jahrelang so in der Tabelle — und stimmt nicht. In seiner
`qt-config.ini`:

```
player_0_button_a="engine:keyboard,code:67,toggle:0"
player_0_button_b="engine:keyboard,code:88,toggle:0"
player_0_lstick="engine:analog_from_button,…keyboard…"
```

70 `player_0_*`-Zeilen, **keine einzige `guid:`-Angabe**. Spieler 1 liegt auf der
Tastatur. Das Fehlerbild ist dasselbe wie bei RPCS3: Der Stream geht auf, das Spiel läuft,
der Controller tut nichts — von außen nicht von „Emulator kaputt" zu unterscheiden.

`launch-profile.py` **meldet das und repariert es nicht.** Edens Bindungssyntax steht nicht
im Programm (`strings` findet keine `engine:`-Zeichenketten), und sie zu erfinden ist genau
die Abkürzung, an der die DuckStation-Reparatur schon einmal gescheitert ist. Eine falsch
geschriebene Belegung wäre schlimmer als gar keine — sie sähe richtig aus.

Der Weg zur echten Reparatur ist derselbe wie bei Dolphin: Eden einmal in seiner Oberfläche
ein Pad zuordnen lassen und die entstandene Datei vergleichen. Das braucht einen Menschen,
nicht mehr Raten (#298).

**Ein Wert auf der Startzeile ist nicht dasselbe wie ein gesetzter Wert.** Flycast bekommt
seit jeher `-config config:pvr.rend=4` mit und läuft damit auf Vulkan — nachgemessen:

```
rend/vulkan/vulkan_context.cpp: Vulkan API 1.1. Device Intel(R) Arc(tm) A310 Graphics
```

Beim Beenden schreibt Flycast seine Konfiguration neu (Zeitstempel bestätigt), und darin
steht der Renderer **nicht**:

```
[window]
fullscreen = yes
height = 480 …
```

Ein `-config`-Wert ist für Flycast flüchtig. Die Folge ist keine Kleinigkeit: über den
Start-Dienst läuft es auf Vulkan, vom Desktop gestartet auf dem eingebauten Standard —
derselbe Emulator, dasselbe Spiel, zwei Verhaltensweisen, und die Ursache steht in einer
Zeile, die niemand sieht. `launch-profile.py` schreibt den Wert deshalb in `emu.cfg`.

Dass das trägt, ist geprüft und nicht angenommen: Wert eingetragen, Flycast gestartet,
beendet, Datei erneut gelesen — der Abschnitt stand noch da. Geprüft wird der **Wert**,
nicht der Schlüssel; genau daran ist die DuckStation-Reparatur einmal gescheitert (#304).

*EN: a value on the launch line is not the same as a value that is set. Flycast runs on
Vulkan when started through the service, but never writes that back — its rewritten
`emu.cfg` has no `[config]` section at all — so the same title runs on the built-in default
when started from the desktop. The profile now writes it into the file, verified by a full
launch/exit cycle, and checks the value rather than the key.*

**Ein Ruckeln sagt nichts über den Emulator, solange die Last daneben fehlt.** Der
Start-Dienst hält deshalb beim Start fest, was der Host sonst tat — Load, Kernzahl und die
fünf CPU-stärksten Prozesse. Sie stehen in `/status` als `host_load` und als Zeile im
Protokoll.

Warum das nötig ist, zeigt der Fall, der es ausgelöst hat (2026-08-13). Gemeldet wurde
*„es ruckelt extrem und läuft wohl auf der CPU statt auf der Arc"* — beides klang
plausibel, beides war falsch:

```
GL_RENDERER   Mesa Intel(R) Arc(tm) A310 Graphics (DG2)   ← sehr wohl auf der GPU
RCS (3D)      0,00 %                                      ← die nötige Einheit: FREI
VCS / VECS    21–29 % / 16–23 %                           ← Tdarr, nur Video-Einheiten

tdarr-ffmpeg 759 %   tdarr-ffmpeg 733 %   xemu 201 %
28 Kerne, Load 45,9
```

Zwei Umrechnungen belegten rund 15 Kerne. Xbox-Emulation ist CPU-gebunden — xemu bildet
einen Pentium III nach —, also rechnete es auf einer **leerlaufenden** 3D-Einheit und
verhungerte an der CPU.

**Die Prozessliste sieht nur den Container.** Der Dienst läuft in dessen PID-Namensraum:

```
ps IM Container:   sh selkies xfce4-panel xfdesktop Xvfb xfce4-session
ps AUF dem Host:   tdarr-ffmpeg tdarr-ffmpeg shfs find
```

Sie kann `tdarr-ffmpeg` also **gar nicht** nennen — ausgerechnet den Fall, für den das
Ganze gebaut wurde. Deshalb heißt sie `top_container` und trägt `top_scope`: Wer eine
harmlose Liste sieht und daraus auf eine ruhige Maschine schließt, liegt sonst genau
falsch (#531).

**Der Load trägt die Aussage.** `/proc/loadavg` ist nicht namensraumgetrennt und im
Container bitgleich zum Host (`38.47 39.89 41.99` gegen `38.47 39.89 41.99`). Er
beantwortet „war die Maschine beschäftigt" — und das ist die Frage.

**Genommen wird der Wert beim Start, nicht auf Nachfrage.** Wer hinterher misst, misst den
falschen Moment: Die Umrechnung, die das Ruckeln verursacht hat, kann längst fertig sein.
Bewertet wird nichts und abgelehnt wird nichts — ob eine Last zu hoch ist, hängt vom Titel
ab (#527).

*EN: a stutter says nothing about the emulator unless the load beside it is recorded. The
service captures load, core count and the top CPU consumers at launch, reported as
`host_load`. The case that prompted it: "it stutters, it must be on the CPU rather than the
Arc" — it was on the Arc, the 3D engine was idle, and two Tdarr transcodes were taking 15 of
28 cores while CPU-bound Xbox emulation starved. Captured at launch, because measuring later
measures the wrong moment; nothing is judged or refused.*

**xemu braucht eine Bibliothek, die nirgends auf dem Suchpfad liegt.** `libusb-1.0.so.0`
steckt weder im Abbild noch in xemus eigenem AppImage. `init/22-xemu-vorbereiten` leiht sie
aus einem anderen Emulator und legt sie nach `/config/lib` — aber der Lader kennt dieses
Verzeichnis nicht:

```
ldconfig -p | grep -c libusb   ->  0
/etc/ld.so.conf.d/*.conf       ->  kein Eintrag für /config
```

Ohne den Pfad endet xemu **sofort**:

```
error while loading shared libraries: libusb-1.0.so.0
```

Von außen ist das nicht von „der Emulator kann die Plattform nicht" zu unterscheiden — der
Stream geht auf und bleibt leer. Die Startzeile setzt deshalb `LD_LIBRARY_PATH=/config/lib`,
und zwar **nur für xemu**: Ein Eintrag in `ld.so.conf` gälte für jedes Programm im Container
und könnte Bibliotheken verdrängen, die ein anderes AppImage selbst mitbringt (#525).

*EN: xemu needs `libusb-1.0.so.0`, which neither the image nor its own AppImage provides.
The init borrows it into `/config/lib`, but nothing put that directory on the loader's path,
so xemu exited immediately — indistinguishable from "platform not supported". The launch
line now sets `LD_LIBRARY_PATH` for xemu alone rather than adding it to `ld.so.conf`, which
would affect every process in the container.*

**Root-eigene Reste sperren Emulatoren aus, ohne es zu sagen.** Der Dienst lief früher
als `root`; was er damals anlegte, gehört bis heute `root`, und der als `abc` laufende
Emulator kommt nicht daran. `init/30-agent` heilt das bei jedem Start — aber nur in den
Bäumen, die dort aufgezählt sind: `/config/.config`, `/config/.local/share` und
`/config/.cache`.

Der dritte fehlte lange, und das kostete zwei Fehldiagnosen (#509):

| Betroffen | Wirkung |
|---|---|
| `/config/.cache/Cemu` | Cemu zeigt einen modalen Dialog *„Cemu can't write to /config/.cache/Cemu!"* und kommt nie bis zu seiner Initialisierung — kein Protokoll, kein Fenster. Der Dialog reagiert auf **keine** Taste und keinen Klick. |
| `/config/.cache/mesa_shader_cache` | 3044 Dateien, nie beschreibbar. Jeder Emulator übersetzt seine Shader bei **jedem** Start neu. Das sieht aus wie „die erste Minute ruckelt eben". |

**Die Liste bleibt ausdrücklich und wird kein `chown -R /config`.** `/config/agent-token`
gehört root mit Absicht und muss `root:600` bleiben — es ist das Einzige zwischen einer
Anfrage und einem gestarteten Prozess auf dem Host.

*EN: the service used to run as root, so what it created then is still root-owned and the
emulator, running as `abc`, cannot touch it. `init/30-agent` heals this at every start,
but only in the trees listed there. `/config/.cache` was missing for a long time and cost
two misdiagnoses: Cemu opens a modal "can't write" dialog that no keystroke dismisses and
never initialises, and the Mesa shader cache — 3044 files — was never writable, so every
emulator recompiled its shaders on every run, which merely looks like a slow first minute.
The list stays explicit rather than becoming `chown -R /config`, because `/config/agent-token`
must remain root:600.*

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

### Aktualisieren — einzeln, und mit einem Weg zurück

**Jeder Emulator lässt sich für sich aktualisieren** (`⟳` in der Liste), zusätzlich zum
Sammelknopf. Ein Sammellauf lädt hunderte Megabyte für Emulatoren, die niemand benutzt,
und wer eine Regression sucht, will genau einen Schritt tun können.

Der Sammellauf erfasst dabei alles, was **installiert ist** — nicht nur, was über einen
`INSTALL_*`-Schalter eingeschaltet wurde. Vorher übersprang er jeden Emulator, der über
die Oberfläche kam, und meldete trotzdem Erfolg: Die Antwort lautete „gestartet", die
Fassung blieb unverändert.

**Der Rückweg reicht drei Fassungen weit.** Beim Aktualisieren rückt die abgelöste Fassung
auf Platz 1, die übrigen rutschen nach, die älteste fällt heraus. `↩` geht **einen Schritt**
zurück und ist wiederholbar; die Zahl daneben sagt, wie weit noch. Die zurückgesetzte
Fassung wird dabei verworfen — man geht ja zurück, *weil* sie kaputt ist.

Vorher gab es genau eine Fassung, und der Rückweg *tauschte* current und alt: zweimal
gedrückt war man wieder am Anfang. Schlimmer war der wahrscheinliche Fall — ein Update auf
eine bereits kaputte Fassung überschrieb die letzte gute, und ein defekter Emulator fällt
oft erst beim übernächsten Start auf.

Die `.url`-Marke wandert mit ihrer Fassung. Das ist kein Detail: Sie ist es, wogegen die
automatische Aktualisierung vergleicht — eine zurückgeholte Fassung ohne ihre Marke würde
beim nächsten Lauf sofort wieder auf die kaputte gehoben.

Die Zahl der aufgehobenen Fassungen steht in `EMU_GENERATIONEN` (Vorgabe `3`, `0` schaltet
das Aufheben ab). Jede kostet den vollen Platz des Emulators — hier 80 bis 400 MB.

## Was tatsächlich getestet ist

„Installiert" ist nicht „läuft". Diese Tabelle sagt, was **mit einem echten Titel
ausprobiert** wurde — Bild im Browser, Ton am Sink gemessen (nicht nach Gehör),
Controller im Spiel gedrückt.

| Plattform | Emulator | Bild | Ton | Controller | Anmerkung |
|---|---|---|---|---|---|
| PlayStation 1 | DuckStation | ✅¹ | ✅ | ✅ | von einem Menschen bestätigt (2026-08-10). ¹Am 2026-08-12/13 startete gar kein Titel — drei modale Fenster, seit #492 stehen alle drei ab. Danach stand das Spiel auf 640 × 480 in der Ecke; **behoben seit #493** — nicht der Fensterschritt war es, sondern ein F11, das DuckStations eigenes Vollbild abschaltete. Nach dem Ausrollen gemessen: **39 von 39 Messpunkten über 80 s** unverändert 1920 × 1080, Vollbildzustand durchgehend gesetzt |
| PlayStation 2 | PCSX2 | ✅ | ✅ | ✅ | |
| GameCube | Dolphin | ✅ | ✅ | ✅ | |
| Wii | Dolphin | ✅ | ✅ | (⁠—⁠) | Controller nicht eigens geprüft — gleicher Emulator und gleiche Belegung wie GameCube |
| PlayStation 3 | RPCS3 | ✅ | ✅ | ✅ | |
| Switch | Eden | ✅ | ✅ | (⁠—⁠) | Controller nicht eigens geprüft |
| Nintendo 3DS | Azahar | ✅ | ✅ | (⁠—⁠) | erst seit der Entschlüsselung (#354/#356); Vollbild an den Pixeln gemessen (#316); Controller nicht eigens geprüft |
| Dreamcast | Flycast | ✅ | ✅ | ✅ | Vollbild und **Vulkan** — seit #304 nicht mehr nur in der Startzeile, sondern **in `emu.cfg` geschrieben**: Flycast übernimmt einen `-config`-Wert NICHT, also lief es vom Desktop gestartet auf dem eingebauten Standard (siehe unten). Bild, Ton und Controller von einem Menschen bestätigt — Flycast belegt die Pads selbst, als einziger Emulator hier |
| Xbox | xemu | ✅ | ✅ | ✅ | braucht **COMPLEX 4627 + MCPX 1.0** — Retail-BIOS bleiben schwarz |
| Wii U | Cemu | — | — | — | Titel vorhanden seit #452/#455 — noch nicht gestartet |
| PS Vita | Vita3K | — | — | — | Titel vorhanden seit #452/#455; Vollbild und Vulkan stehen in der Konfiguration (#304); der Start übergibt seit #481 die **Titelkennung** statt des Pfades; seit #488 stehen die beiden Startdialoge ab, und der Titel bootet gemessen bis ins Ladefenster — ein Mensch hat ihn noch nicht gesehen; seit #489 beendet `/stop` ihn wirklich und `/status` findet sein Fenster |

Ein `—` heißt **ungeprüft**, nicht „defekt". Für Dreamcast, Wii U und PS Vita liegen
seit #452/#455 Titel bereit; sie sind ungeprüft, weil noch niemand sie gestartet hat —
nicht mehr, weil nichts da wäre.

### Zwei Fallen, die nach einem Defekt des Hosts aussehen

Beides sind **Titelprobleme**, keine Emulatorprobleme — der Emulator läuft in beiden
Fällen einwandfrei, nur das Spiel nicht:

- **3DS: verschlüsselte ROMs.** *Erledigt seit #354/#356 — der Host entschlüsselt beim
  Start selbst.* Vorher startete Azahar, aber jeder Titel scheiterte. Je nach
  Format anders: ein Cartridge-Dump zeigt den Dialog `App Encrypted`, ein eShop-Titel
  schreibt `Failed to determine system mode (Error 8)` ins Emulator-Log und öffnet gar
  kein Fenster, und ein `.cia` meldet `CIA must be installed before usage` — CIAs muss
  man erst installieren, sie starten nicht direkt.

  **Azahar entschlüsselt nicht selbst**, auch nicht mit vollständigem `aes_keys.txt` und
  `boot9.bin` — der Wunsch wurde upstream als *closed as not planned* abgelehnt
  (azahar-emu/azahar#2207). Es braucht **vorab entschlüsselte Dumps**.

  Ob eine Datei brauchbar ist, steht in ihrem Kopf und lässt sich ohne Emulator prüfen:
  Ein `.3ds`/`.cci` trägt bei `0x100` die Kennung `NCSD`, die erste Partition beginnt bei
  `0x4000` mit `NCCH` bei `0x4100`, und ab `0x188` liegen acht Flag-Bytes — **Bit 2 von
  Flag 7 (`0x04`, `NoCrypto`)** bedeutet unverschlüsselt. Der Streaming-Host prüft das
  **vor dem Start** und weist verschlüsselte Titel mit einer Begründung ab, statt einen
  leeren Stream zu öffnen (#299).
- **Wii: NKit-komprimierte ISOs.** Dolphin öffnet einen `NKit Warning`-Dialog statt des
  Spiels. Dieselbe Bibliothek in `.wbfs` startet ohne Zutun.

### 3DS: entschlüsseln, sonst geht nichts

Azahar spielt **nur entschlüsselte Dumps** und entschlüsselt nicht selbst — der Wunsch
wurde upstream als *closed as not planned* abgelehnt. In der hiesigen Bibliothek waren
**1248 von 1249 Abbildern verschlüsselt**, also praktisch alle.

Was funktioniert: **[3DS-Decrypt](https://github.com/aszuraz/3DS-Decrypt)** (Python +
`pycryptodome`). Es trägt die vier Retail-`KeyX` **fest im Quelltext** und braucht deshalb
**weder `aes_keys.txt` noch `boot9.bin`**. ROMs mit *Dev*-Schlüsseln entschlüsselt es nicht
— dafür stehen auskommentierte Werte im Skript; in dieser Bibliothek kam kein solcher Fall
vor. Azahar selbst braucht die Firmware sehr wohl, das erledigt `25-firmware`.

```bash
docker run --rm -v /pfad/zu/3DS-Decrypt:/tool:ro -v /pfad/zu/roms:/arbeit \
  python:3.12-slim sh -c "pip install -q pycryptodome && cd /arbeit && \
    python3 /tool/decrypt_3ds.py <datei>.3ds"
```

Danach ist das `NoCrypto`-Flag gesetzt und Azahar startet den Titel mit Namen im Fenster.

**Der Host macht das inzwischen selbst.** `init/23-3ds-entschluesseln` legt
`pycryptodome` und das Werkzeug nach `/config/tools/3ds-decrypt`. Beim Start eines
verschlüsselten Titels entschlüsselt der Agent **in einen Zwischenspeicher daneben** und
startet die Kopie:

| Schalter | Vorgabe | Bedeutung |
|---|---|---|
| `DECRYPT_3DS_CACHE` | `/config/3ds-entschluesselt` | wohin die entschlüsselten Kopien gehen |
| `DECRYPT_3DS_CACHE_GB` | `50` | Deckel; darüber wird nach letzter Nutzung verdrängt |
| `DECRYPT_3DS_URL` | GitHub-raw | woher das Werkzeug kommt |

`/status` meldet die Fähigkeit als `can_decrypt_3ds`. Romseerr fragt sie ab und sagt einen
verschlüsselten Titel **nicht mehr ab**, sondern kündigt die Wartezeit an.

**`.cia` ebenso, mit einem Unterschied: die Installation ist dauerhaft.** Der Host holt
zusätzlich `decrypt_cia.py` und meldet `can_install_cia`. Beim Start einer CIA wird
entschlüsselt, per `azahar --install` installiert und dann der installierte Titel gestartet
— beim **zweiten** Mal nur noch gestartet, denn die Installation liegt auf Azahars
SD-Karte und bleibt. Das Werkzeug für CIAs schreibt eine **neue** Datei
(`<name>-decrypted.cia`) statt in-place zu arbeiten; die Logik der Abbilder ließ sich
deshalb nicht wiederverwenden.

Nicht jede CIA ist ein Spiel. Entscheidend ist die Kategorie der Titel-ID:

| obere 32 Bit | Bedeutung | startbar |
|---|---|---|
| `0x00040000` | Anwendung | ja |
| `0x00040002` | Demo | ja |
| `0x0004000E` | Update | nein — gehört zu einem anderen Titel |
| `0x0004008C` | DLC | nein |

In dieser Bibliothek: 9 Anwendungen, 1 Demo, 13 Updates, 2 DLC. **Der Dateiname taugt
nicht** — bei zweien stand etwas anderes drin, als die Datei enthielt.

**Warum daneben und nicht an Ort und Stelle:** Das verschlüsselte Original ist es, was den
Titel identifizierbar macht — von 20 3DS-Titeln erkannte Hasheous **15** an ihrer
Prüfsumme, die beste Quote der ganzen Bibliothek. Würde man die Dateien ersetzen, wären
diese Metadaten weg. Der Deckel ist da, weil sonst nach und nach die ganze Plattform
doppelt läge; entschlüsselt wird nur, was auch gestartet wird.

**Was der erste Start wirklich kostet** — an einem echten Titel dieser Bibliothek gemessen
(`eShop-3DS-0022`, 128 MB):

| | |
|---|---|
| Entschlüsseln | **0,07 s** |
| Prüfsumme vorher → nachher | `04fa95e5…` → `bf5e3f0b…` |
| `NoCrypto`-Flag | `0x00` → `0x04` |

Entschlüsselt werden nur Kopf- und ExeFS-Bereiche, nicht das ganze Abbild. **Die Kosten
stecken vollständig im Kopieren** und wachsen mit der Abbildgröße — bei einem 4-GB-Titel
über die Freigabe sind das Minuten, bei diesem hier Sekunden. Jeder weitere Start desselben
Titels ist sofort da, solange die Kopie im Zwischenspeicher liegt.

Eine frühere Fassung dieser Zeile schätzte „einige Minuten" pauschal. Das war geraten.

**Vollbild: den INHALT messen, nicht den Rahmen.** Der Fenstertrick vergrößert die
X-Fensterhülle; ob der Emulator seinen Zeichenbereich mitwachsen lässt, steht damit nicht
fest — bei xemu tut er es nicht (#300). Die Fenstergeometrie meldet in beiden Fällen
1920x1080. Belastbar ist nur die Messung am Bild: `xwd` aufnehmen, in Graustufen wandeln
und den nicht-schwarzen Bereich bestimmen. Für Azahar und Eden nachgemessen — beide füllen.
**Mehrfach messen**: Eine Aufnahme 12 Sekunden nach dem Start traf einen Ladebildschirm und
zeigte 78 % der Breite; drei Proben danach zeigten 100 %.

*Measure the content, not the frame: the window trick resizes the X window, and the
geometry reads 1920x1080 either way. Sample repeatedly — a loading screen looks like a
rendering bug.*

> **NDecrypt hilft hier nicht.** Es ist der erste Suchtreffer, akzeptiert `aes_keys.txt`,
> meldet jede Partition als entschlüsselt — und lässt die Datei **byteweise unverändert**.
> Wer ihm glaubt, legt den Fall fälschlich als „nicht behebbar" ab. **Nachmessen:**
> Prüfsumme vorher/nachher und das `NoCrypto`-Flag.

**Renderer:** Azahar startet auf OpenGL. Für Vulkan in `qt-config.ini`
`graphics_api=2` — und **`graphics_api\default=false` dazu**, sonst gilt weiter der
eingebaute Standard und der Wert daneben wird beim nächsten Start überschrieben.
Dieselbe Falle gilt für jeden Qt-Schlüssel dort, auch für die Tastenbelegung.

**Gamepad:** Azahar ist auf die **Tastatur** voreingestellt — dieselbe Falle wie bei
RPCS3. Zwei Dinge sind dabei nicht offensichtlich: Die 3DS-Tasten sind gegenüber Xbox
**vertauscht** (A rechts, B unten), und der **Port ist nicht 0**. Im Container liegen
acht identische Pad-Geräte, unseres ist für SDL das dritte (`port:2`). Weil diese
Reihenfolge nicht stabil ist, überschreibt der Host eine vorhandene SDL-Belegung nie —
**Azahars eigenes Auto-Map ist die verlässliche Quelle**, denn nur der Emulator kennt
den Port.

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

**PS Vita: zwei Teile, und nur einer ist Handarbeit.** Vita3K verlangt die Firmware-PUP
**und** ein **Font-Paket**; fehlt eines, sagt es wörtlich `Firmware is not fully installed.`

| Teil | woher | landet in |
|---|---|---|
| Firmware (`PSVUPDAT.PUP`) | **selbst besorgen** und über *Install Firmware* einspielen | `vs0`, `os0` |
| Font-Paket (`PSP2UPDAT.PUP`) | **auch selbst besorgen** — die Schaltfläche *Download Firmware Font Package* öffnet nur einen Link | `sa0` |

**Vita3K lädt beides NICHT selbst.** Die Schaltfläche *Download Firmware Font Package* sieht
so aus, als täte sie es, und tut es nicht: Sie öffnet einen Browser auf einen Kurzlink. Am
laufenden Host gemessen — im Protokoll steht `Opening in existing browser session`, danach
startet Chromium und sonst passiert nichts.

Der Kurzlink zeigt auf einen unverschlüsselten Direktdownload:

```
https://bit.ly/2P2rb0r
  -> http://dus01.psp2.update.playstation.net/update/psp2/image/2019_0924/
     sd_8b5f60b56c3da8365b973dba570c53a5/PSP2UPDAT.PUP?dest=us
  56.768.512 Byte, Kopf `SCEUF`
```

Mit `curl` ist es ein Einzeiler; im Browser des Containers startete der Download nicht.
Beide PUPs landen in `firmware/psvita/` und werden über *File ▸ Install Firmware*
eingespielt — einzeln, erst die eine, dann die andere.

Der Status prüft deshalb **beide** Ablagen (`vs0` und `sa0`). Mit nur einer meldete er
„eingespielt", während der Emulator selbst widersprach (#484).

**Bereitgelegt ist nicht eingespielt.** Für **PS3 und PS Vita** ist die Firmware eine
`.PUP` — ein Update-Paket, das der Emulator *einspielen* muss und nie an Ort und Stelle
benutzt. Der Katalog nennt deshalb je Eintrag eine **Ablage**: das Verzeichnis, in dem die
Firmware *danach* liegt (`dev_flash` bei RPCS3, `vs0` bei Vita3K). Erst wenn dort etwas
liegt, meldet der Status `eingespielt`.

Fehlt diese Angabe, greift im Skript der Zweig *„ohne Ablage ist die Frage gegenstandslos"*
— und der Status ist **grün für eine Firmware, die der Emulator gar nicht hat**. Genau so
stand `psvita` auf `installed: true`, während `vs0`, `os0` und `sa0` leer waren: 133 MB
bereitgelegt, null eingespielt (#479). Aufgefallen ist es erst beim Startversuch, an
Vita3Ks „Welcome"-Fenster.

**Korrektur dazu (#488):** Dieses Fenster war *nicht* die Meldung über die fehlende
Firmware — das stand hier bis dahin und ist nachgemessen falsch. Vita3K zeigt es bei
jedem Start, solange `show-welcome: true` steht, auch bei vollständiger Firmware. Es hat
die Sache nur zufällig zur richtigen Zeit sichtbar gemacht. *EN: correction — that window
was not the missing-firmware message; Vita3K shows it on every launch while
`show-welcome: true`, complete firmware or not. It merely surfaced at the right moment.*

Für PS1, PS2, Dreamcast, Xbox, 3DS, Switch und Wii U gibt es keine Ablage, und das ist
richtig: Dort **ist** die Firmware die Datei im Verzeichnis, es gibt keinen zweiten Schritt.

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

### Drei modale Fenster, nicht eins — und das Profil lief gar nicht (#492)

Der Setup-Wizard oben ist nur der erste. Am 2026-08-13 startete **kein einziger
PSX-Titel**: statt des Spiels stand ein Fenster von 500 × 193 Pixeln da, *„Would you like
to create a launcher shortcut for DuckStation?"*. Ist das aus dem Weg, kommt sofort das
nächste — **„Automatic Updater"**, 651 × 474, mitten auf dem Spielfenster. Beide stehen
jetzt ab (`launch-profile.py --dialogs duckstation`):

| Schalter | Abschnitt | Wert | wofür |
|---|---|---|---|
| `NoDesktopFile` | `[Main]` | `true` | die Verknüpfungs-Abfrage |
| `CheckAtStartup` | `[AutoUpdater]` | `false` | die Update-Abfrage |

Beide Werte sind **gemessen, nicht abgelesen**, jeder mit Gegenprobe:

| `NoDesktopFile` | `CheckAtStartup` | Fenster |
|---|---|---|
| (fehlt) | (fehlt) | nur „DuckStation" 500 × 193 — **kein Spielfenster** |
| `true` | (fehlt) | Spiel **und** „Automatic Updater" 651 × 474 |
| `true` | `false` | Spiel, kein Dialog; `/status` meldet `window: "ok"` |
| `true` | `true` *(Gegenprobe)* | „Automatic Updater" wieder da |
| (entfernt) | `false` *(Gegenprobe)* | „DuckStation" wieder da, kein Spielfenster |

Den ersten Wert hat **DuckStation selbst geschrieben**: Der Dialog hat ein Kästchen
*„Don't ask again"*, und nach einem Klick darauf stand genau eine neue Zeile in der
`settings.ini` — sonst keine.

**Der eigentliche Fund liegt daneben.** `psx` fehlte in der Zuordnung
Plattform → Startprofil (`PROFILE_EMU` im Start-Dienst), seit sie mit #140 von einer auf
neun Plattformen wuchs. Das Profil für DuckStation gab es die ganze Zeit — **aufgerufen
hat es bei einem Start nie jemand**. Gamepad-Belegung und Erstlaufdialog standen auf dem
Host nur deshalb richtig, weil sie einmal von Hand gesetzt worden waren. Sichtbar wurde
die Lücke erst, als DuckStation ein neues Fenster aufmachte. Ein Test hält das jetzt
fest: **jeder Emulator im Startprofil muss an einer Plattform hängen.**

Was **nicht** geklärt ist: warum die Verknüpfungs-Abfrage am 2026-08-10 noch nicht kam.
Fassung und `settings.ini` sind seither unverändert; das bleibt **ungeprüft**.

*EN: the setup wizard is only the first of three. On 2026-08-13 no PSX title started at
all — a 500 × 193 window asked whether to create a launcher shortcut, and behind it sat
the automatic updater. Both are now switched off before the launch (`NoDesktopFile` in
`[Main]`, `CheckAtStartup` in `[AutoUpdater]`), each value measured with a counter-check;
DuckStation wrote the first one itself after "Don't ask again" was ticked. The real find
is next to it: `psx` had been missing from the platform → profile map since #140, so the
DuckStation profile was never applied on a launch — what was right on the host was right
by hand. A test now checks that every profile is reachable from some platform. Why the
shortcut prompt did not appear on 2026-08-10 is unmeasured.*

### Nicht der Fensterschritt war es, sondern das F11 danach (#493)

Nachdem die drei Dialoge abstanden, kam das Spiel ins Bild — aber nur in einem Viertel der
Fläche: DuckStation stand nach rund 14 Sekunden auf **640 × 480 in der Ecke**, mit
Titelleiste zurück, und blieb dort. Der Verdacht lag auf dem Fensterschritt
(`nur_emulator`), der jedes sichtbare Fenster aufzieht. **Der Verdacht war falsch.**

Gemessen wurde, indem dessen vier Aufrufe einzeln auf das Fenster angewandt wurden, ohne
Agenten daneben:

| Schritt | Geometrie | `_NET_WM_STATE` |
|---|---|---|
| Ausgangsstand | 1920 × 1080 | `_NET_WM_STATE_FULLSCREEN` |
| nach `_MOTIF_WM_HINTS` | 1920 × 1080 | `_NET_WM_STATE_FULLSCREEN` |
| nach `windowsize` | 1920 × 1080 | `_NET_WM_STATE_FULLSCREEN` |
| nach `windowmove` | 1920 × 1080 | `_NET_WM_STATE_FULLSCREEN` |
| nach `windowactivate` | 1920 × 1080 | `_NET_WM_STATE_FULLSCREEN` |
| nach `windowraise` | 1920 × 1080 | `_NET_WM_STATE_FULLSCREEN` |

Der Täter steht im Agent-Log, bei **jedem** PSX-Start mit denselben Zahlen:

```
[vollbild] 34.3 % bemalt -> F11 -> 99.3 %
```

Die 34,3 % messen kein zu kleines Fenster, sondern ein **schwarzes**: DuckStation bootet
zu diesem Zeitpunkt noch die Disc. F11 schaltet daraufhin das Vollbild ab, das der
Emulator selbst gesetzt hatte (`-fullscreen` in der Startzeile).

**Und der gemeldete Erfolg war keiner.** Die 99,3 % danach sind der freigelegte
XFCE-Desktop. Nachgemessen ohne jeden laufenden Emulator: **99,27782600308642 %** —
bitgleich dieselbe Zahl. Die Flächenmessung kann ein Spiel nicht vom Hintergrundbild
unterscheiden (#495).

> *Nachtrag zu dieser Zahl:* Sie ist der obere Anschlag dieser Messung, nicht eine
> Eigenschaft des Desktops — 1915 × 1075 von 1920 × 1080 ist der größte Rahmen, den ein
> 6er-Raster überhaupt aufspannen kann. Jede vollständig bemalte Fläche liefert sie, das
> Hintergrundbild ebenso wie ein bildschirmfüllender Emulator. Genau darum ging es: die
> beiden Zustände waren ununterscheidbar. Einzelheiten unter *Vollbild: gemessen, nicht
> angenommen*.

Behoben ist es dort, wo der Schaden entsteht, und emulatorunabhängig: **ein Fenster, das
`_NET_WM_STATE_FULLSCREEN` trägt, bekommt kein F11.** Der Fensterschritt bleibt
unverändert; ihn zu ändern gäbe es keinen gemessenen Grund.

Gegenprobe am laufenden Host, mit xemu — dem Fall, für den der Tastenweg gebaut wurde:

```
t=…214  WINDOW=44040241 X=2 Y=75 WIDTH=1920 HEIGHT=1080  STATE=[_NET_WM_STATE_FOCUSED]
```

Kein `_NET_WM_STATE_FULLSCREEN`. Der Wächter kann dort also gar nicht zuschlagen, und der
Fenstertrick zieht xemu weiterhin auf. **Was diese Gegenprobe nicht zeigt:** ob F11 danach
noch abgeht — die Flächenmessung lag mit 99,3 % über der Schwelle, F11 war also gar nicht
fällig. Diesen Pfad hält nur der Test fest, nicht eine Messung am Host.

**Die Vermutung des Issues, Flycast und PCSX2 hätten dasselbe Problem, ist widerlegt.**
Beide durchlaufen denselben Schritt, beide tragen den Vollbildzustand — und beide bleiben:

| Emulator | Fenster beim Start | nach dem Fenster- und Vollbildschritt |
|---|---|---|
| DuckStation (PS1) | 1920 × 1080, Vollbild | **640 × 480 auf 1,51** — F11 kam |
| PCSX2 (PS2) | 1920 × 1080, Vollbild | 1920 × 1080, Vollbild — F11 kam, wirkte nicht |
| Flycast (Dreamcast) | 1920 × 1080, Vollbild | 1920 × 1080, Vollbild — kein F11 |

PCSX2 bekam das F11 also ebenfalls zu Unrecht (`32.0 % bemalt -> F11 -> 32.0 %`) und hat
es nur ignoriert. Flycast entging ihm, weil sein Titel in dem Moment ein helles Bild
zeigte — Glück, keine Sicherheit.

**Zweiter Fund: `/status` sagte die Größe, die es nie nachgesehen hatte.** Gemessen,
während der Titel lief:

```
/status   "window": "ok", "1 Fenster auf 1920x1080, ohne Rahmen, Panel ausgeblendet"
xdotool   Position 1,51   Geometry 640x480
```

Die Zahl war die **Bildschirm**größe — das Ziel des Schrittes, nicht sein Ergebnis. Der
Befund nennt jetzt die gemessene Größe des größten Fensters, und zwar **nach** dem
Vollbildschritt, weil erst dort der Schaden entstand:

```
[fenster] 1 Fenster, ohne Rahmen, Panel ausgeblendet
[fenster] groesstes Fenster gemessen: 1920x1080
```

Was das **nicht** löst: Der Befund bleibt eine Momentaufnahme vom Start. `/status` misst
nicht bei jedem Abruf nach — der Dienst beantwortet Anfragen der Reihe nach, und ein
`xdotool`, das in seinen Timeout läuft, hielte auch `/stop` auf.

*EN: with the dialogs gone the game appeared, but at 640 × 480 in the corner. The window
step was not the culprit — measured, all four of its calls leave `_NET_WM_STATE_FULLSCREEN`
intact. The F11 afterwards is: the painted-area measurement reads a still-booting black
screen as 34.3 %, below the threshold, so it toggles off the fullscreen the emulator had
set itself. The 99.3 % it then reports as success is the bare XFCE desktop — measured with
no emulator running at all, the same value to the last digit (#495). The fix is
emulator-agnostic: a window carrying `_NET_WM_STATE_FULLSCREEN` gets no F11; xemu, Azahar
and Eden do not carry it and still get theirs. The issue's guess that Flycast and PCSX2
share the problem is refuted by measurement — PCSX2 was wrongly sent F11 too but ignored
it, and Flycast escaped only because its title happened to show a bright picture. Second
find: the verdict quoted the SCREEN size, not the window's; it is now measured after the
fullscreen step. It remains a snapshot taken at launch — /status does not re-measure per
request, because the service answers sequentially and a hanging xdotool would block /stop.*

## PS Vita (Vita3K): der Titel wird über seine **Kennung** gestartet

PS Vita ist die einzige Plattform hier, bei der der Start-Dienst **nicht den Pfad**
übergibt. Vita3K startet einen Titel über seine Titelkennung, und zwar nur, wenn er
**installiert** ist. Die eigene Hilfe sagt es:

```
-r, --installed-path TEXT:{PCSF00024}   Path to the installed app to run
```

Die geschweifte Menge ist die Liste der installierten Titel — `-r` prüft dagegen. Mit
einem Pfad endet der Start, bevor irgendein Fenster entsteht:

```
CLI parsing error: --installed-path: /roms/psvita/Gravity not in {PCSF00024}
[E] [main]: Failed to initialise config                            (Exit 4)
```

Der Start-Dienst liest die Kennung deshalb aus `sce_sys/param.sfo` des Titelordners
(`TITLE_ID`), sucht sie im Verzeichnis `ux0/app` von Vita3Ks Ablage — der Pfad steht als
`pref-path` in dessen `config.yml` — und setzt **sie** in die Startzeile ein. Geraten
wird nichts: der Ordner heißt `Gravity Rush (Europe).vpk`, die Kennung `PCSF00024`.

**Was nicht installiert ist, wird abgesagt statt gestartet.** Ohne `-r` öffnet Vita3K
seine Titelliste: der Start *gelingt*, der Stream zeigt einen Emulator, und nichts sagt,
warum kein Spiel kommt. Die Absage nennt die Kennung, damit man in Vita3K nachsehen kann.
**Installieren tut der Dienst nicht** — das ist ein Schritt in Vita3Ks eigener Oberfläche
(*File ▸ Install*), zu erreichen über den Desktop-Eintrag.

*EN: PS Vita is the one platform where the launch service does not pass a path. Vita3K
launches an INSTALLED title by its title id (`-r/--installed-path`), and validates it
against the set of installed ids — a path fails at CLI parsing with exit 4, before any
window appears. The service reads `TITLE_ID` from the title folder's `sce_sys/param.sfo`,
looks it up in `ux0/app` under Vita3K's `pref-path`, and substitutes that. Nothing is
guessed from the folder name. A title that is not installed is refused rather than
launched, because without `-r` Vita3K merely opens its title list: the launch succeeds
and no game appears. Installing is a step in Vita3K's own GUI (File ▸ Install).*

### Zwei modale Fenster fangen jeden Start ab — beide stehen ab (#488)

Die richtige Startzeile allein genügte nicht. Vita3K nimmt die Kennung an und zeigt
danach ein **Willkommensfenster**, das im Container niemand wegklickt; dahinter staut sich
jeder Start. Ist das aus dem Weg, legt sich das nächste davor: **„Update Available"**,
320 × 183 Pixel mitten auf dem Spielfenster.

Beide sitzen als Schalter in `<config>/.config/Vita3K/config.yml`, und der Start-Dienst
legt sie **vor** dem Start um (`launch-profile.py --dialogs vita3k`):

| Schalter | Wert | wofür |
|---|---|---|
| `show-welcome` | `false` | das Willkommensfenster |
| `check-for-updates-mode` | `0` | die Abfrage nach einer neuen Vita3K-Fassung |

Gemessen am laufenden Host, jeder Schalter mit Gegenprobe — die Fenster gehören der
**echten** Vita3K-PID, nicht der des Wrappers (#489):

| `show-welcome` | `check-for-updates-mode` | Fenster |
|---|---|---|
| `true` | `1` | nur `Welcome to Vita3K`, kein Spiel, 4,5 % CPU |
| `false` | `1` | Spiel + `Update Available` |
| `false` | `0` | Spiel, kein Dialog — 99,3 % der Fläche bemalt |
| `false` | `1` (Gegenprobe) | `Update Available` wieder da |

> Die Spalte „99,3 % der Fläche bemalt" belegt **nur, dass kein Dialog mehr im Weg stand**
> — nicht, dass der Titel den Schirm füllte. Ein leerer Desktop lieferte dieselbe Zahl
> (#495).

Dass `0` in Vita3Ks Quelltext „nie" heißt, wird hier **nicht** behauptet: der Wert ist
gemessen, nicht abgelesen. Belegt ist, dass der Dialog damit wegbleibt und Vita3K die `0`
annimmt.

**Zwei Fallen beim Nachstellen von Hand:** Vita3K schreibt seine `config.yml` schon beim
**Start** zurück — wer sie ändert, während der Emulator läuft, verliert die Änderung. Und
`warn-missing-firmware` bleibt bewusst auf `true`: es ist der dritte Dialog derselben
Klasse, hier folgenlos, weil die Firmware vollständig ist (#485/#486). Wer ihn vorsorglich
abschaltet, verliert die Warnung genau dann, wenn sie einmal berechtigt wäre.

*EN: the correct launch line was not enough. Vita3K accepts the title id and then shows a
**welcome window** nobody can dismiss in a container; every launch stalls behind it. With
that out of the way the next one takes its place: **"Update Available"**, 320 × 183 pixels
in the middle of the game window. Both are switches in
`<config>/.config/Vita3K/config.yml`, and the launch service flips them BEFORE the launch
(`launch-profile.py --dialogs vita3k`): `show-welcome: false` and
`check-for-updates-mode: 0`. Measured on the running host with a counter-check per switch
(and on the real Vita3K PID, not the wrapper's, see #489): `true`/`1` gives only the
welcome dialog at 4.5 % CPU and no game; `false`/`1` boots the game but puts "Update
Available" on top; `false`/`0` gives the game with no dialog and 99.3 % of the screen
painted (which proves only that no dialog was in the way — a bare desktop returned the same
number, #495); switching back to `1` brings the dialog back. It is NOT claimed that `0` is the
source's name for "never" — that value is measured, not read. Two traps when reproducing
by hand: Vita3K rewrites its `config.yml` at STARTUP, so an edit made while it runs is
lost; and `warn-missing-firmware` deliberately stays `true` — it is the third dialog of the
same class, harmless here because the firmware is complete (#485/#486), and switching it
off pre-emptively would remove the warning exactly when it becomes justified.*

### Der Start-Dienst verfolgt eine **Prozessgruppe**, nicht eine PID (#489)

`linuxdeploy` erzeugt bei Vita3K als einzigem Emulator ein `AppRun.wrapped`, das ein
**Shell-Skript** ist. Bei rpcs3, cemu und azahar ist dieselbe Datei ein **Symlink auf die
Programmdatei** und wird `exec`-t — nachgemessen, alle vier:

```
$ file -bL <emu>/AppRun.wrapped
vita3k   POSIX shell script          <- startet das Programm als KIND, ohne exec
rpcs3    ELF 64-bit LSB pie executable  (Symlink -> usr/bin/rpcs3)
cemu     ELF 64-bit LSB pie executable  (Symlink -> usr/bin/Cemu)
azahar   ELF 64-bit LSB pie executable  (Symlink -> usr/bin/azahar)
```

Der Dienst merkte sich damit bei Vita3K die PID der **Shell**, nicht die des Emulators —
am laufenden Host bei laufendem Spiel abgelesen:

```
  PID  PPID  PGID
 1414  1414  1414  python3 /opt/stream-agent.py          <- der Dienst
11616  1414  1414  /bin/sh …/AppRun.wrapped -r PCSF00024 <- verfolgt
11634 11616  1414  …/usr/bin/Vita3K -r PCSF00024         <- der Emulator
```

Das kostete **zwei** Zusagen:

| gemessen | vorher | jetzt |
|---|---|---|
| `/stop` | `{"ok": true}`, Vita3K lief mit `PPid 1` weiter und hielt die GPU | der ganze Baum ist weg |
| `/status` | `"window": "kein-fenster"` bei sichtbarem Spiel | das Fenster wird gefunden |

Zum zweiten Punkt, dieselbe Sitzung, zwei PIDs:

```
xdotool search --onlyvisible --pid 11616   (Wrapper)  -> nichts
xdotool search --onlyvisible --pid 11634   (Vita3K)   -> 46137351 [Vita3K v0.2.1 …]
                                                         46137358 [GRAVITY RUSH™ (PCSF00024)]
```

Behoben wird beides **emulatorunabhängig**, nicht mit einem Sonderweg für Vita3K:

- Jeder Start bekommt eine **eigene Sitzung** (`start_new_session`), `/stop` schickt
  SIGTERM und nötigenfalls SIGKILL an die **Gruppe**. Damit trifft es auch den nächsten
  Wrapper, den `linuxdeploy` erzeugt, ohne dass ihn jemand hier einträgt.
- Die Fensterprüfung fragt zusätzlich bei den **Kindprozessen** nach (`/proc`, keine
  weiteren Werkzeuge). Für die anderen Emulatoren ändert das nichts: deren `AppRun`
  `exec`-t, die verfolgte PID *ist* das Programm.

**Warum die eigene Sitzung nicht Beiwerk ist:** ohne sie steht der Emulator in der Gruppe
des Dienstes — oben alle drei in `1414`. Ein `killpg` darauf hätte den **Dienst selbst**
beendet. Der Code benutzt die Gruppe deshalb nur, wenn sie gleich der Kind-PID ist; sonst
fällt er auf das Signal an den einen Prozess zurück.

**Was bewusst offen bleibt:** das unquotierte `$@` im Wrapper zerlegt Argumente an
Leerzeichen (`--installed-path: x` statt `x PCSF00024`). Für die heutige Startzeile ist
das folgenlos — eine Titelkennung hat keine Leerzeichen. Behoben wäre es nur, indem man
`usr/bin/Vita3K` **direkt** startet, und das kostet zwei Dinge: den Qt-Hook aus
`apprun-hooks/` (setzt `QT_QPA_PLATFORMTHEME=gtk2`) und die Erkennung fehlender
Plattformen, die im Startbefehl nach einem `…/AppRun` sucht. Wer die Startzeile je auf den
**positionalen** Parameter umstellt (Pfad statt Kennung), muss vorher hier hinsehen.

*EN: Vita3K is the only emulator whose `AppRun.wrapped` is a shell script — for rpcs3, cemu
and azahar the same file is a symlink to the binary and gets `exec`'d. So the service was
tracking the **shell's** PID, not the emulator's (measured on the running host: agent 1414,
wrapper 11616, Vita3K 11634). That cost two promises: `/stop` answered `ok` while Vita3K
kept running orphaned at `PPid 1` holding the GPU, and `/status` reported `kein-fenster`
for a title that was visibly on screen — `xdotool --pid` on the wrapper found nothing while
the same query on the real PID found both the Vita3K window and `GRAVITY RUSH™`. Both are
fixed **without an emulator-specific path**: every launch gets its own session
(`start_new_session`) and `/stop` signals the process **group**, so it also catches the next
wrapper `linuxdeploy` produces; and the window check additionally asks the **child
processes** (via `/proc`). Nothing changes for the other emulators, whose `AppRun` `exec`s.
The new session is not decoration: without it the emulator sits in the agent's own group
(all three in `1414` above) and a `killpg` would have killed the service — the code
therefore only uses the group when it equals the child PID. Deliberately left alone: the
wrapper's unquoted `$@` splits arguments at spaces. That is harmless for today's launch
line (a title id has no spaces), and fixing it would mean launching `usr/bin/Vita3K`
directly — which drops the Qt hook from `apprun-hooks/` and breaks the missing-platform
check that looks for a `…/AppRun` in the launch command.*

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

### Wo er herkommt — und warum es dafür keinen Rückfall gibt

Gestartet wird **immer** `/opt/stream-agent.py`, die Einhängung von
`stack/stream-agent.py`. Was läuft, ist damit das, was im Repo steht.

Fehlt diese Datei, **bricht der Start ab**. Das ist Absicht. Früher wich `init/30-agent`
still auf `/config/stream-agent.py` aus — und das ist auf gewachsenen Installationen eine
Altfassung. Hier gemessen:

| Datei | Größe | Zeilen |
|---|---|---|
| `/opt/stream-agent.py` | 75.621 B | 1510 |
| `/config/stream-agent.py` | 6.703 B | 158 |

Die Altfassung kennt weder `psx` noch `psvita`, `ps3` oder `xbox` und verweist auf
Emulatorpfade, die es nicht mehr gibt. Sie hätte Anfragen beantwortet und **gesund
ausgesehen**: Der Stream kommt hoch, die Emulatortabelle ist falsch, und nichts im
Protokoll sagt warum.

**Ein Rückfall ist nur dann ein Netz, wenn das Hineinfallen sichtbar ist.** Ein Container,
der nicht hochkommt, ist in zehn Minuten repariert; einer, der falsch hochkommt, kostet
einen Tag. Wer die Meldung `[agent] FEHLT: /opt/stream-agent.py` sieht, prüft die
Bind-Mounts des Containers.

Liegt auf einer älteren Installation noch ein `/config/stream-agent.py` herum, kann es
weg — es wird von nichts mehr gelesen.

### Warum Vita3K an seinem Wrapper vorbei gestartet wird

Bei den meisten Emulatoren **ist** `AppRun.wrapped` das Programm und wird `exec`-t — die
Prozessnummer bleibt dieselbe. Bei Vita3K ist es ein Shell-Skript, das das Programm als
**Kind** startet:

```sh
#!/bin/sh
if [ "${APPIMAGE}" != "" ]; then
    export PATH="$APPDIR/usr/bin:$PATH"
    "${APPDIR}/usr/bin/Vita3K" $@        # kein exec, $@ ohne Anführungszeichen
fi
```

Der Start-Dienst merkt sich damit die Nummer der **Shell**, nicht die des Emulators. Drei
Folgen, alle nachgemessen:

| Folge | Bild |
|---|---|
| `/stop` wirkt nicht | Antwort `ok`, `/status` sagt `running: false` — der Emulator lebt als Waise weiter (PPid 1). Erst `kill -9` beendet ihn. Der Dienst hält sich für frei, der nächste Start läuft gegen einen Emulator, der die GPU noch hält. |
| Fensterprüfung irrt | `kein sichtbares Fenster zum Prozess` — dasselbe Werkzeug fand an der echten Nummer `Welcome to Vita3K`. |
| Leerzeichen zerfallen | `$@` unquotiert: aus `x PCSF00024` wird `x`. Für eine Titelkennung folgenlos, für einen Pfad nicht. |

`30-agent` startet deshalb `usr/bin/Vita3K` direkt und setzt `APPDIR`, `APPIMAGE` und den
`PATH` selbst — mehr tat der Wrapper nachweislich nicht.

**Dass nur Vita3K betroffen ist, ist eine Messung, keine Eigenschaft von AppImages.**
`linuxdeploy` erzeugt je nach Bauart mal ein Programm, mal ein Skript. `30-agent` prüft
deshalb bei jedem Start den Typ aller `AppRun.wrapped` und meldet es, wenn ein weiterer
Emulator einen Skript-Wrapper bekommt.

*EN: for most emulators `AppRun.wrapped` is the binary and gets exec'd, so the pid stays
the same. Vita3K's is a shell script that starts the binary as a child, so the service
tracks the shell: `/stop` reports ok while the emulator survives as an orphan and needs
`kill -9`, the window check looks at the wrong pid, and unquoted `$@` splits arguments.
The init now runs `usr/bin/Vita3K` directly and sets `APPDIR`, `APPIMAGE` and `PATH`
itself — all the wrapper did. Only Vita3K is affected today, which is a measurement, not a
property of AppImages, so the init checks every wrapper's type at start and says so when
another emulator gains one.*

*EN: the service always runs `/opt/stream-agent.py`, the bind mount of
`stack/stream-agent.py`, so what runs is what is checked out. If that file is missing the
init **aborts**. It used to fall back to `/config/stream-agent.py` silently, which on a
grown installation is a stale copy — measured here at 158 lines against 1510, with no
`psx`, `psvita`, `ps3` or `xbox` and hardcoded emulator paths that no longer exist. It
would have answered requests and looked healthy. A fallback is a safety net only when
falling into it is visible: a container that fails to start is a ten-minute fix, one that
starts wrong costs a day. A leftover `/config/stream-agent.py` can be deleted; nothing
reads it.*

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

### It tracks a process **group**, not a PID

A launch does not always end at the process the service starts. `linuxdeploy` gives Vita3K
— and only Vita3K — an `AppRun.wrapped` that is a **shell script** and runs the emulator as
a **child** without `exec`; for rpcs3, cemu and azahar the same file is a symlink to the
binary. Measured on the running host, with the game visibly up:

```
  PID  PPID  PGID
 1414  1414  1414  python3 /opt/stream-agent.py            <- the service
11616  1414  1414  /bin/sh …/AppRun.wrapped -r PCSF00024   <- the PID it tracked
11634 11616  1414  …/usr/bin/Vita3K -r PCSF00024           <- the emulator
```

Tracking the wrapper cost two promises: `/stop` answered `{"ok": true}` while Vita3K kept
running orphaned at `PPid 1`, still holding the GPU — and `/status` reported
`window: "kein-fenster"` for a title that was on screen, because `xdotool --pid` on the
wrapper finds nothing while the same query on PID 11634 finds both the Vita3K window and
`GRAVITY RUSH™ (PCSF00024)`.

Both are fixed **without an emulator-specific path**:

- every launch gets its **own session** (`start_new_session`), and `/stop` sends SIGTERM —
  then SIGKILL if needed — to the process **group**. That also catches the next wrapper
  `linuxdeploy` produces, with nobody having to list it here;
- the window check additionally asks the **child processes**, read from `/proc`.

Nothing changes for the other emulators: their `AppRun` `exec`s, so the tracked PID *is*
the program and has no children.

The new session is not decoration. Without it the emulator sits in the **agent's own**
process group — all three lines above share `1414` — and a `killpg` there would take down
the service itself. The code therefore only signals the group when it equals the child PID,
and otherwise falls back to signalling the tracked process alone.

Deliberately left alone: the wrapper's unquoted `$@` splits arguments at spaces
(`--installed-path: x` instead of `x PCSF00024`). That is harmless for today's launch line,
since a title id has no spaces. Fixing it would mean launching `usr/bin/Vita3K` directly,
which drops the Qt hook in `apprun-hooks/` and breaks the missing-platform check that looks
for a `…/AppRun` inside the launch command. Anyone switching the Vita launch line to the
**positional** parameter (a path instead of an id) has to look here first.

### A window already in fullscreen is left alone

The window step pulls every visible window to the full screen, and after it a painted-area
measurement decides whether to correct with F11 (see *Fullscreen: measured, not assumed*).
For DuckStation that correction was the damage: the title sat at 1920 × 1080 and dropped to
**640 × 480 in the corner** about 14 seconds in.

The window step was the obvious suspect and it is **not** the culprit. Measured by applying
its four calls one at a time to the window, with no agent alongside — `_MOTIF_WM_HINTS`,
`windowsize`, `windowmove`, `windowactivate`, `windowraise` — the window stayed 1920 × 1080
and kept `_NET_WM_STATE_FULLSCREEN` throughout. The F11 afterwards is the culprit, and the
agent log shows it with the same numbers on every PSX launch:

```
[vollbild] 34.3 % bemalt -> F11 -> 99.3 %
```

34.3 % does not measure a small window, it measures a **black** one — DuckStation is still
booting the disc. F11 then switches off the fullscreen the emulator had set itself via
`-fullscreen`. The 99.3 % reported as success is the uncovered XFCE desktop: measured with
no emulator running at all, the bare desktop read the same value to the last digit (#495).

*(That value, 99.27782600308642 %, is the ceiling of this measurement rather than a
property of the desktop: 1915 × 1075 of 1920 × 1080 is the largest box a 6-pixel raster can
span, so any fully painted surface returns it — wallpaper and fullscreen game alike. Which
is the point: the two states were indistinguishable. See* The fullness measurement compares
against a picture of the empty desktop *below.)*

The fix is emulator-agnostic: **a window carrying `_NET_WM_STATE_FULLSCREEN` gets no F11.**
The window step is unchanged; there is no measured reason to touch it.

Counter-checked on the running host with xemu, the case the keystroke route was built for:
its window reports `STATE=[_NET_WM_STATE_FOCUSED]` and no fullscreen atom, so the guard
cannot fire there and the window trick still pulls it up. What that counter-check does
**not** show is whether F11 still goes out afterwards — the painted share was 99.3 %, above
the threshold, so no F11 was due. Only the test covers that path, not a host measurement.

The issue's guess that Flycast and PCSX2 shared the problem is **refuted by measurement**:

| Emulator | at launch | after the window and fullscreen steps |
|---|---|---|
| DuckStation (PS1) | 1920 × 1080, fullscreen | **640 × 480 at 1,51** — F11 was sent |
| PCSX2 (PS2) | 1920 × 1080, fullscreen | 1920 × 1080, fullscreen — F11 sent, ignored |
| Flycast (Dreamcast) | 1920 × 1080, fullscreen | 1920 × 1080, fullscreen — no F11 |

Second find: `/status` quoted a size it had never looked at — `1 Fenster auf 1920x1080`
while `xdotool` reported 640 × 480. That number was the **screen** geometry, the aim of the
step rather than its outcome. The verdict now names the measured size of the largest
window, taken **after** the fullscreen step, because that is where the damage happened. It
is still a snapshot from launch time: `/status` does not re-measure per request, because
the service answers requests sequentially and a hanging `xdotool` would block `/stop` too.

### The fullness measurement compares against a picture of the empty desktop

Until 2026-08-13 the measurement looked for the bounding box of the non-black points in an
`xwd -root` capture. A wallpaper is not black, so it could not tell a game from an empty
desktop. Measured on the running host, three states:

| State | old measurement | new measurement |
|---|---|---|
| bare desktop, no emulator | 99.28 % | **0.06 %** |
| xemu, picture 1280 × 963 on the desktop | 99.28 % | **74.87 %** |
| Flycast, genuinely fullscreen | 73.56 % | **99.97 %** |

The old number was **inverted**, not merely imprecise: the bare desktop sat above the
threshold and a genuinely fullscreen emulator below it.

The measurement now compares the screen against a **baseline** capture of the empty
desktop. The agent takes it between stopping the previous title and starting the new one —
the only moment the desktop is actually empty — via `launch-profile.py --grundbild`. A
point counts as "still desktop" when it is unchanged **and** was not black in the baseline;
black on black says nothing, an emulator paints that too. Everything else belongs to the
emulator.

The capture refuses itself in two situations, and both guards are needed. If
`_NET_CLIENT_LIST` holds anything besides the panel and the desktop, a baseline would
contain the game and mark every later launch as "the emulator took nothing over". If the
screen is nearly all black, X or XFCE is still coming up and every later launch would score
100 %. Either way the old baseline stays and the log says so; with no baseline at all the
correction is skipped and the log reads `[vollbild] nicht messbar`.

Two side findings from the same measurement:

* **The row length is padded, and exact equality is too brittle.** The xwd header reports
  `bits_per_pixel` 24 and `bytes_per_line` 7680 for a 1920-point-wide screen, of which
  1920 × 3 = 5760 bytes carry image. The stride must come from `bits_per_pixel`; deriving
  it from `bytes_per_line / width` reads past the row and decodes the image squeezed into
  three quarters of the width with a black band on the right. *(That wrong turn was in an
  intermediate version of this section, with reproducible numbers behind it. It only showed
  up once the decoded image was looked at instead of merely computed.)* Separately, only
  **7.2 %** of the wallpaper points visibly unchanged next to xemu are bit-identical
  between the two captures, because the baseline is 24 bpp and a capture taken with a
  32-bit-visual window fullscreen is 32 bpp, which dithers the gradient differently. Points
  count as unchanged within a per-channel tolerance of 8; without it this state measured
  95.13 % instead of 74.87 %.
* **Restricting the measurement to the window geometry — the fix proposed in #495 — was
  measured and rejected.** xemu's X window really is 1920 × 1080 (`xwininfo` confirms it),
  but only about 1280 × 963 of it is ever painted. The rest is left untouched and still
  shows the wallpaper, so the desktop lies *inside* the window. Restricted to the window
  geometry the measurement returned the same wrong value: **99.64 %**.

The check table from #429 (Azahar 53.3 %, Eden 88.6 %, xemu 960 of 1920) proves less than
it appears to: its numbers come from a measurement that cannot tell a game from the
wallpaper. Only xemu has been measured again so far — 62.07 % before F11, 95.13 % after,
and the window then carried `_NET_WM_STATE_FULLSCREEN`, which it had not before. That also
settles the question #493 left open: F11 does still reach an emulator without a fullscreen
switch of its own.

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
| PlayStation 1 | DuckStation | ✅¹ | ✅ | ✅ | confirmed by a human (2026-08-10). ¹on 2026-08-12/13 no title started at all — three modal windows, all three switched off since #492. The game then sat at 640 × 480 in the corner; **fixed since #493** — not the window step but an F11 that switched off DuckStation's own fullscreen. Measured after the rollout: **39 of 39 samples over 80 s** unchanged at 1920 × 1080, fullscreen state held throughout |
| PlayStation 2 | PCSX2 | ✅ | ✅ | ✅ | |
| GameCube | Dolphin | ✅ | ✅ | ✅ | |
| Wii | Dolphin | ✅ | ✅ | (⁠—⁠) | controller not checked separately — same emulator and same mapping as GameCube |
| PlayStation 3 | RPCS3 | ✅ | ✅ | ✅ | |
| Switch | Eden | ✅ | ✅ | (⁠—⁠) | controller not checked separately |
| Nintendo 3DS | Azahar | ✅ | ✅ | (⁠—⁠) | only since decryption (#354/#356); fullscreen measured at the pixels (#316); controller not separately checked |
| Dreamcast | Flycast | ✅ | ✅ | ✅ | fullscreen and **Vulkan** — since #304 no longer only on the launch line but **written into `emu.cfg`**: Flycast does not adopt a `-config` value, so started from the desktop it ran on the built-in default (see below). Picture, sound and controller confirmed by a human — Flycast maps the pads by itself, the only emulator here that does |
| Xbox | xemu | ✅ | ✅ | ✅ | needs **COMPLEX 4627 + MCPX 1.0** — retail BIOS stays black |
| Wii U | Cemu | — | — | — | a title is in the library since #452/#455 — not launched yet |
| PS Vita | Vita3K | — | — | — | a title is in the library since #452/#455; fullscreen and Vulkan are set in the config (#304); since #481 the launch passes the **title id** instead of the path; since #488 both startup dialogs are switched off and the title was measured booting into its loading window — no human has seen it yet; since #489 `/stop` really ends it and `/status` finds its window |

A `—` means **untested**, not "broken". Dreamcast, Wii U and PS Vita have had content since
#452/#455; they are untested because nobody has launched them yet, not because there is
nothing to start.

### Two traps that look like a broken host

Both are **title** problems, not emulator problems — the emulator runs fine in both
cases, the game does not:

- **3DS: encrypted ROMs.** *Resolved by #354/#356 — the host decrypts at launch.*
  Previously Azahar started but every title failed, and differently per
  format: a cartridge dump shows an `App Encrypted` dialog, an eShop title writes
  `Failed to determine system mode (Error 8)` to the emulator log and opens no window at
  all, and a `.cia` reports `CIA must be installed before usage` — CIAs have to be
  installed first, they do not boot directly.

  **Azahar does not decrypt**, not even with a complete `aes_keys.txt` and `boot9.bin` —
  that request was closed upstream as *not planned* (azahar-emu/azahar#2207). Dumps must
  be decrypted beforehand.

  Whether a file is usable is written in its header and can be checked without the
  emulator: a `.3ds`/`.cci` carries `NCSD` at `0x100`, its first partition starts at
  `0x4000` with `NCCH` at `0x4100`, and eight flag bytes follow at `0x188` — **bit 2 of
  flag 7 (`0x04`, `NoCrypto`)** means unencrypted. The streaming host checks this
  **before launching** and rejects encrypted titles with a reason instead of opening an
  empty stream (#299).
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

**The host now decrypts by itself.** `init/23-3ds-entschluesseln` installs `pycryptodome`
and places the tool in `/config/tools/3ds-decrypt`. The tool carries the four retail `KeyX`
values **in its own source** and needs neither `aes_keys.txt` nor `boot9.bin` (ROMs with
*dev* keys are not covered). On launching an encrypted title the agent decrypts **into a
cache alongside** and starts the copy:

| Setting | Default | Meaning |
|---|---|---|
| `DECRYPT_3DS_CACHE` | `/config/3ds-entschluesselt` | where decrypted copies go |
| `DECRYPT_3DS_CACHE_GB` | `50` | cap; above it, least-recently-used copies are evicted |
| `DECRYPT_3DS_URL` | GitHub raw | where the tool comes from |

`/status` reports the capability as `can_decrypt_3ds`. Romseerr asks for it and no longer
refuses an encrypted title, announcing the wait instead.

**`.cia` likewise, with one difference: the installation is permanent.** The host also
fetches `decrypt_cia.py` and reports `can_install_cia`. Launching a CIA decrypts it,
installs it with `azahar --install` and then boots the installed title — the **second**
time it only boots, because the installation lives on Azahar's SD card and stays. The CIA
tool writes a **new** file (`<name>-decrypted.cia`) rather than working in place, so the
image logic could not be reused.

Not every CIA is a game. The title ID's category decides:

| upper 32 bits | meaning | bootable |
|---|---|---|
| `0x00040000` | application | yes |
| `0x00040002` | demo | yes |
| `0x0004000E` | update | no — belongs to another title |
| `0x0004008C` | DLC | no |

In this library: 9 applications, 1 demo, 13 updates, 2 DLC. **The filename is not
reliable** — in two cases it said something other than what the file contained.

**Why alongside rather than in place:** the encrypted original is what identifies the
title — of 20 3DS titles Hasheous matched **15** by checksum, the best rate in the whole
library. Replacing the files would throw those metadata away. The cap exists because the
platform would otherwise end up stored twice; only what is actually launched gets
decrypted.

**What the first launch actually costs** — measured on a real title from this library
(`eShop-3DS-0022`, 128 MB):

| | |
|---|---|
| decryption | **0.07 s** |
| checksum before → after | `04fa95e5…` → `bf5e3f0b…` |
| `NoCrypto` flag | `0x00` → `0x04` |

Only the header and ExeFS regions are rewritten, not the whole image. **The cost is
entirely in the copy** and scales with image size — minutes for a 4 GB title over the
share, seconds for this one. Every later launch of the same title is immediate, as long as
the copy is still in the cache.

An earlier version of this line guessed "several minutes". It was a guess.

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

**PS Vita: two parts, and only one is manual.** Vita3K wants the firmware PUP **and** a
**font package**; without either it says, verbatim, `Firmware is not fully installed.`

| part | where from | ends up in |
|---|---|---|
| firmware (`PSVUPDAT.PUP`) | **obtain it yourself**, then *Install Firmware* | `vs0`, `os0` |
| font package (`PSP2UPDAT.PUP`) | **obtain it too** — the *Download Firmware Font Package* button only opens a link | `sa0` |

**Vita3K fetches neither.** The *Download Firmware Font Package* button looks as though it
does and does not: it opens a browser on a shortened link. Measured on the running host —
the log says `Opening in existing browser session`, Chromium starts, and nothing else
happens.

The link resolves to a plain-HTTP direct download:

```
https://bit.ly/2P2rb0r
  -> http://dus01.psp2.update.playstation.net/update/psp2/image/2019_0924/
     sd_8b5f60b56c3da8365b973dba570c53a5/PSP2UPDAT.PUP?dest=us
  56,768,512 bytes, header `SCEUF`
```

`curl` handles it in one line; the container's browser never started the download. Both PUPs
go into `firmware/psvita/` and are installed one after the other via *File > Install
Firmware*.

The status therefore checks **both** Ablagen (`vs0` and `sa0`). With only one it reported
"installed" while the emulator itself disagreed (#484).

**Staged is not installed.** For **PS3 and PS Vita** the firmware is a `.PUP` — an update
package the emulator has to *install*, never used in place. The catalogue therefore names an
**Ablage** per entry: the directory the firmware ends up in afterwards (`dev_flash` for
RPCS3, `vs0` for Vita3K). Only once something is there does the status report `installed`.

Without that field the script takes the branch *"no Ablage, so the question is moot"* — and
the status is **green for firmware the emulator does not have**. That is exactly how
`psvita` read `installed: true` while `vs0`, `os0` and `sa0` were empty: 133 MB staged, none
installed (#479). It surfaced only on a launch attempt, as Vita3K's "Welcome" window — which
was the correct message, not the problem.

PS1, PS2, Dreamcast, Xbox, 3DS, Switch and Wii U have no Ablage, and rightly so: there the
firmware **is** the file in that directory, with no second step.

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
