# Sicherheit / Security

*(English below)*

## Was dieses Projekt ist — und was das für dich bedeutet

Romseerr ist ein selbstgehostetes Einzelprojekt eines Betreibers, kein Produkt mit
Bereitschaftsdienst. Es hat seit **v1.4.0** stabile Releases; davor war alles eine Vorabversion. Das ist keine Ausrede, sondern eine Angabe, mit der du rechnen können sollst:
Meldungen werden gelesen und ernst genommen, aber es gibt keine zugesagte Reaktionszeit.

## Was gemeldet werden sollte

Alles, womit jemand **mehr erreicht, als seine Rolle erlaubt** — oder womit ein Betreiber
etwas anderes tut, als er glaubt:

- eine Route, die ohne das nötige Recht antwortet (die Schleuse ist `_guard` als
  `before_request`; die Decorators sind Tiefenstaffelung, nicht die Sperre)
- ein Pfad, der aus der Bibliothek herausführt, besonders am Streaming-Host
- eine ausgehende Adresse, die trotz der SSRF-Prüfung ins private Netz zeigt
- ein Geheimnis, das im Klartext in einer Antwort, einem Export oder einem Protokoll landet
- ein Download, der den eingestellten Proxy umgeht

## Was hier ausdrücklich **kein** Sicherheitsfehler ist

- **Der API-Schlüssel ist admin-äquivalent.** Das ist so gebaut und dokumentiert.
- **`/metrics` ist nicht öffentlich**, sondern hängt an derselben Schleuse wie die API — das
  ist Absicht, weil Metriken Nutzungsmuster verraten.
- **Ein einzelner Betreiber sieht alles.** Es gibt keine Mandantentrennung und keinen Anspruch
  darauf.
- **`pip install` ohne `--require-hashes`.** OpenSSF Scorecard meldet das siebenmal
  (`pipCommand not pinned by hash`). Bewusst abgelehnt, mit Messung — Begründung unten.

### Abgelehnt: Hash-Pinning für pip (#718, entschieden 2026-08-16)

**Was fehlt:** Nicht die Versionen — `requirements.txt` führt alle 26 Pakete samt
transitiver Hülle exakt gepinnt, der Bau läuft mit `--no-deps`, damit pip nichts selbst
auflösen kann, und `pip check` macht eine unvollständige Liste zum Baufehler statt zum
`ImportError` im Betrieb (#380). Das Basisabbild hängt am Digest (#717). Es fehlt allein
`--hash=sha256:…` je Datei.

**Was ein Hash zusätzlich abdeckte:** ein *republiziertes* Artefakt — gleiche Version,
anderer Inhalt. PyPI-Dateien sind pro (Name, Version, Datei) unveränderlich, es bliebe also
ein kompromittiertes PyPI selbst oder ein Proxy im Transportweg, der TLS bricht.

**Warum trotzdem nein — der Grund ist gemessen, nicht geschätzt.** Der naheliegende
Mittelweg („Hashes nur in `requirements.txt`, CI-Werkzeuge und Init-Skript in Ruhe lassen")
**bricht Dependabot**. Belegt am Quelltext von `dependabot-core`,
`python/lib/dependabot/python/file_updater.rb`:

```ruby
return :pip_compile if changed_req_files.any? { |f| f.end_with?(".in") }
:requirements
```

Der Pfad hängt an einer `.in`-Datei. Nur `PipCompileFileUpdater` kennt
`update_hashes_if_required`; der `RequirementFileUpdater`, der unsere handgepflegte Datei
bearbeitet, erzeugt **keine** Hashes neu. Ein Bump hübe also die Version an und ließe die
alten Hashes stehen — jeder Dependabot-PR wäre rot mit
`THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE`, bis jemand von Hand
nachzieht. Bei einem Projekt, in dem Aktualisierungen mehrmals wöchentlich über Dependabot
ankommen (#554, #585), ist das kein Zusatzaufwand, sondern ein dauerhaft kaputter Weg.

**Der einzige gangbare Vollausbau** wäre, `requirements.in` einzuführen und `requirements.txt`
als echte `pip-compile`-Ausgabe zu führen. Gemessen: Die Datei wächst von 62 auf **1007
Zeilen**, und der handgepflegte Abschnitt — der begründet, was `app.py` überhaupt importiert —
verliert seinen Platz. Der Gegenwert bleibt die enge Bedrohung von oben.

**Was das nicht heißt:** „gewinnt nichts". Es heißt „zu wenig Gewinn für diesen Preis". Wer
das später anders gewichtet, findet hier die Zahlen und in #718 die Messung.

## Wie melden

Über **GitHub Security Advisories** am Repository — direkt hier:
<https://github.com/Sparxx947/romseerr/security/advisories/new> (*Security → Report a
vulnerability*). Das hält den Fund nicht öffentlich, bis er behoben ist. Ein normales Issue geht auch — dann ist er
allerdings sofort für alle sichtbar, und das ist deine Entscheidung, nicht meine.

**Bitte keine Zugangsdaten, Token oder Adressen aus deiner Installation mitschicken.** Ein
Fehlerbericht wandert schneller weiter, als einem lieb ist; die Einstellungen-Ausgabe ist
genau deshalb maskiert.

**Unterstützt wird jeweils die neueste Version auf `main`.** Ältere Releases bekommen keine
Rückportierungen — es gibt genau einen Zweig, auf dem veröffentlicht wird.

## Wie damit umgegangen wird

Ein bestätigter Fund bekommt ein Issue mit dem Label `security`, eine Prüfung, die ihn
nachstellt, und den Fix. Die Prüfung ist der Teil, der zählt: Ohne sie kommt derselbe Fehler
beim nächsten Umbau zurück, und niemand merkt es.

Statische Prüfungen laufen bei jedem PR (CodeQL, Bandit, Trivy, Gitleaks). Eine
**abgewiesene** CodeQL-Meldung trägt hier immer eine Begründung, die die Schutzmaßnahme und
den Test benennt — „false positive" allein gilt nicht.

---

## What this project is

Romseerr is a self-hosted single-maintainer project, not a product with an on-call rota. There
have been stable releases since **v1.4.0**; everything before that was a pre-release. That is not an excuse
but a figure to plan with: reports are read and taken seriously, and there is no promised
response time.

## Worth reporting

Anything that lets someone **do more than their role allows**, or makes an operator do
something other than what they believe:

- a route answering without the permission it needs (the gate is `_guard` as a
  `before_request` hook; the per-route decorators are defence in depth, not the lock)
- a path escaping the library, especially on the streaming host
- an outbound address reaching a private network despite the SSRF check
- a secret appearing in clear text in a response, an export or a log
- a download bypassing the configured proxy

## Explicitly **not** a vulnerability here

- **The API key is admin-equivalent.** By design, and documented.
- **`/metrics` is not public** but sits behind the same gate as the API — deliberate, because
  metrics reveal usage patterns.
- **A single operator sees everything.** There is no tenancy separation and no claim to one.
- **`pip install` without `--require-hashes`.** OpenSSF Scorecard reports this seven times
  (`pipCommand not pinned by hash`). Deliberately declined, with measurements — see below.

### Declined: hash pinning for pip (#718, decided 2026-08-16)

**What is missing:** not the versions. `requirements.txt` carries all 26 packages including
the transitive closure, exactly pinned; the build runs `--no-deps` so pip cannot resolve
anything itself; and `pip check` turns an incomplete list into a build failure rather than a
runtime `ImportError` (#380). The base image is pinned by digest (#717). What is missing is
`--hash=sha256:…` per file.

**What a hash would add:** defence against a *republished* artefact — same version, different
content. PyPI files are immutable per (name, version, file), so what remains is a compromised
PyPI itself, or a proxy in the transport that breaks TLS.

**Why no anyway — measured, not estimated.** The obvious middle path ("hashes only in
`requirements.txt`, leave the CI tools and the init script alone") **breaks Dependabot**.
Evidenced in the `dependabot-core` source, `python/lib/dependabot/python/file_updater.rb`:

```ruby
return :pip_compile if changed_req_files.any? { |f| f.end_with?(".in") }
:requirements
```

The path hinges on a `.in` file. Only `PipCompileFileUpdater` knows
`update_hashes_if_required`; the `RequirementFileUpdater` that handles our hand-kept file does
**not** regenerate hashes. A bump would raise the version and leave the old hashes in place —
every Dependabot PR red with `THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS
FILE` until someone catches up by hand. In a project where updates arrive through Dependabot
several times a week (#554, #585) that is not extra effort, it is a permanently broken path.

**The only viable full build-out** would be introducing `requirements.in` and keeping
`requirements.txt` as genuine `pip-compile` output. Measured: the file grows from 62 to **1007
lines**, and the hand-kept section — the one that records what `app.py` actually imports —
loses its place. The return is still the narrow threat above.

**This does not mean "gains nothing".** It means "too little gain for this price". Anyone
weighing it differently later will find the numbers here and the measurements in #718.

## How to report

Through **GitHub Security Advisories** on the repository — directly here:
<https://github.com/Sparxx947/romseerr/security/advisories/new> (*Security → Report a
vulnerability*), which keeps the finding private until it is fixed. A normal issue works too,
but then it is public immediately — your call, not mine.

**Please do not include credentials, tokens or addresses from your installation.** A bug
report travels further than one expects; the settings export is masked for exactly that
reason.

**The latest version on `main` is supported.** Older releases get no backports — there is
exactly one branch that publishes.

## How it is handled

A confirmed finding gets an issue labelled `security`, a test that reproduces it, and the fix.
The test is the part that matters: without it the same fault returns at the next refactor and
nobody notices.

Static checks run on every PR (CodeQL, Bandit, Trivy, Gitleaks). A **dismissed** CodeQL alert
here always carries a reason naming the guard and the test that covers it — "false positive"
on its own does not count.
