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

## Der Start-Dienst

`stream-agent.py` nimmt von Romseerr entgegen, welche Datei zu starten ist. Er
startet Prozesse — entsprechend ist er gebaut:

* ohne Token startet er **gar nicht**, Anfragen ohne Token bekommen `401`
* **keine Shell**: die Argumentliste geht unverändert an `execve`
* der Pfad wird über `realpath` aufgelöst und muss **innerhalb** der Bibliothek
  liegen — sonst wäre er ein Fernstart für beliebige Dateien

Er gehört **nicht ins offene Netz**.

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
