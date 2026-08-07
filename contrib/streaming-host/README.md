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

## Certificate renewal

The `stream-certbot` sidecar renews every 12 hours into the same directory the
streaming host reads from; `init/40-cert-watch` notices the changed fingerprint and
reloads the web server. Deliberately **without a Docker socket** — a container that
can see the socket is effectively root on the host, which a reload does not justify.
