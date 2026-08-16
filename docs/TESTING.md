# Tests / Testing

*Deutsch zuerst, English below.*

---

## Deutsch

### Die vier Ebenen

| Ebene | Datei | Was sie sieht | Dauer |
|---|---|---|---|
| Unit | `tests/test_smoke.py` | `app` über den Flask-Testclient | ~5 s |
| Auslieferung | `tests/test_auslieferung.py` | echte HTTP-Köpfe: Komprimierung, Caching | <1 s |
| Vertrag | `tests/test_contract.py` | Antworten gegen `/api/openapi.json` | ~3 s |
| Browser | `tests/e2e/` | gerendertes HTML, JavaScript, Tastatur, Adresszeile | ~30 s |

Die oberen drei laufen im CI-Auftrag **Tests**, die Browserebene in einem eigenen Auftrag
**Browsertests**. Getrennt, damit der schnelle Teil schnell bleibt.

**Es gibt eine fünfte Sache, die kein Test ist, aber hierher gehört:** die Bilder der
Oberfläche. `scripts/screenshots.py` fährt dieselbe Wegwerf-Instanz hoch wie die
Browsertests, setzt einen Vorführstand und fotografiert 33 Ansichten nach `docs/img/`.
Sie laufen **nicht** in der CI — eine Browserinstallation je Lauf und ein Binärdiff je
Zusammenführung wären teurer als der Nutzen. Stattdessen prüft
`test_the_documentation_images_are_not_older_than_the_interface`, ob die Oberfläche
seither davongelaufen ist. Bewusst kein Bildvergleich: Chromium liefert für denselben
Inhalt keine bitgleichen Dateien, ein solcher Test wäre von Anfang an flatterhaft.

*A fifth thing that is not a test but belongs here: the interface screenshots.
`scripts/screenshots.py` starts the same throwaway instance the browser tests use, seeds a
demo state and photographs 33 views into `docs/img/`. It deliberately does not run in CI —
a browser install per run and a binary diff per merge would cost more than it returns.
Instead a test checks whether the interface has moved on since the images. No image
comparison: Chromium does not produce byte-identical files for identical content, so that
test would be flaky by construction.*

### Loslegen

```bash
pip install -r requirements.txt -r requirements-dev.txt
playwright install --with-deps chromium      # einmalig, rund 115 MB

pytest                       # alles, mit Abdeckungsboden
pytest --ignore=tests/e2e    # ohne Browser
pytest tests/e2e --no-cov    # nur Browser
```

Fehlt Playwright oder Schemathesis, überspringen sich die betroffenen Dateien per
`importorskip` — die Suite läuft dann trotzdem durch.

### Warum es die Browserebene gibt

Elf Fehler (#319–#324, #328–#330) saßen in einem grünen Build. Der Testclient rendert kein
HTML, führt kein JavaScript aus und kennt weder Tastatur noch Adresszeile; er kann diese
Klasse gar nicht sehen. Darunter waren eine Navigation, die per Tastatur nicht erreichbar
ist, eine Ansicht ohne Routen-Eintrag und Assets ohne Komprimierung.

### Was welches Werkzeug kann — und was nicht

**Playwright** fährt einen echten Browser. Tastatur, Adresszeile, Konsolenfehler,
Fenstergrößen.

**`tests/e2e/bildmessung.py`** liest die Pixel eines Element-Screenshots — ein kleiner
PNG-Dekoder auf `zlib`, ohne Pillow und ohne numpy. Gebraucht wird er dort, wo Kästen
nicht genügen: `getBoundingClientRect()` beschreibt Kästen, nicht das, was man sieht. In
#659 saß das × eines Knopfes 3 px zu weit rechts und 5,5 px zu tief, während jeder
gemessene Kasten für sich plausibel aussah — der Zeilenkasten war schlicht höher als der
Inhaltsbereich, der ihn hielt. `tintenraender()` gibt die Ränder um die hellen Pixel
zurück und `None`, wenn nichts über der Schwelle liegt; ein Aufrufer, der das für
„mittig" nähme, bestünde inhaltsleer.

Für Flächen statt Zeichen kamen in #657 zwei weitere Funktionen dazu. `zeilensprung()`
vergleicht zwei Pixelzeilen **Spalte für Spalte** — ein Mittelwert würde eine Kante
verstecken, die nur über einen Teil der Breite geht. Damit ließ sich zeigen, dass der
Aurora-Schleier an der Unterkante der Kopfleiste um 84 Farbeinheiten sprang und danach um
0 (Median). `zeilenspanne()` ist die Gegenprobe dazu und genauso wichtig: Eine Naht ist
auch dann sprungfrei, wenn der Verlauf **ganz fehlt** — ein gelöschter Schleier bestünde
jede Nahtprüfung. Erst die Spanne über eine Zeile belegt, dass an der Stelle überhaupt
etwas zu sehen ist.

Die Rahmenzeile wird dabei bewusst übersprungen: `#side` trägt ein `border-bottom` von
1 px, und das ist eine gewollte Trennlinie. Gemessen wird deshalb zwei Zeilen darüber
gegen eine Zeile darunter — sonst misst die Prüfung den Rahmen und nicht den Verlauf.

**axe-core** prüft Kontrast, fehlende Namen, ARIA und Dokumentstruktur. Es hat **keine
Regel** für ein `div` mit Klick-Behandler ohne Rolle — nachgeprüft in der Regelliste,
entgegen mehrerer verbreiteter Anleitungen. Ein reiner axe-Lauf hätte die
Bibliotheksansicht als sauber gemeldet. Diese Lücke schließt nur ein Tastaturdurchlauf.

**Schemathesis** erzeugt Fälle aus der Spezifikation. Aktiv sind vier Prüfungen; drei
weitere sind bewusst aus, weil sie hier aus dem falschen Grund anschlagen — die Begründung
steht im Kopf von `tests/test_contract.py`.

**Lighthouse** hält im CI ein Transferbudget auf der Anmeldeseite. Bewusst ein Budget und
kein Punktestand: Punktestände schwanken auf geteilten Läufern, und was grundlos rot wird,
wird abgeschaltet.

### Bekannte Fehler in der Suite

Sie stehen als `xfail(strict=True)` mit Issue-Nummer. CI bleibt grün, der Befund bleibt
festgehalten — und wer den Fehler behebt, wird von der Ratsche daran erinnert, den Marker
zu entfernen. `xfail_strict` ist in `pytest.ini` global gesetzt.

### Drei Ratschen

Sie halten den erreichten Stand, statt ein Ziel zu setzen:

| Ratsche | Wo | Heute |
|---|---|---|
| Abdeckung | `pytest.ini` | 69 % Boden (gemessen: 70 %) |
| Ansichten ohne Browsertest | `test_views_are_covered_by_browser_tests` | 1 (`lists`) |
| Ansicht ohne Routen-Eintrag | `test_every_view_has_a_route` | `xfail` auf #320 |

### Fallen, die hier schon zugeschlagen haben

- **Ein Test, der nichts findet, besteht.** Der Tastaturtest fand auf der leeren Instanz
  keine Bibliothekszeilen und war inhaltsleer wahr. Dafür gibt es `bibliothek_gefuellt`.
- **`get_by_role` findet nur, was eine Rolle hat.** Ein `<a>` ohne `href` hat keine; fünf
  Prüfungen haben sich selbst übersprungen und Grün gemeldet. Deshalb `menuepunkt()`.
- **Zwei Instanzen, nicht eine.** Die Browsertests legen den ersten Benutzer an. Liefe das
  auf derselben Instanz wie die Unit-Tests, wäre `test_setup_and_login` reihenfolge-
  abhängig kaputt. Dafür gibt es `servermod`.
- **Der Einführungsdialog fängt den Fokus** — korrekt für ein Modal. Wer ihn stehen lässt,
  misst ihn statt der Seite. Die Fixture `seite` schließt ihn.
- **`--cov=app` sammelt nichts**, sobald `app.py` zweimal geladen wird. Deshalb `--cov=.`
  plus `.coveragerc`.
- **Ein Test kann am Interpreter hängen, unter dem er startet.** `requirements.txt`
  beschreibt das Abbild (`python:3.14-slim`), aber `tests/test_abhaengigkeiten.py` wertete
  die Marker der Pakete gegen den laufenden Python aus. Auf 3.12 verlangen `aiohttp` und
  `aiosignal` `typing_extensions` hinter `python_version < "3.13"` — dort war die Hülle 27
  Pakete groß, im Abbild 26, und `test_transitive_huelle_ist_vollstaendig` schlug lokal
  fehl, während dieselbe Prüfung in der CI grün blieb. Das rote Kreuz war nicht das
  Problem, sondern der naheliegende Schluss: Wer `typing-extensions` nachträgt, liefert
  dem Abbild ein Paket, das dort niemand braucht. Seit #667 stehen die Marker auf der
  Fassung aus dem `Dockerfile`; wo sich das nicht messen lässt, wird mit Begründung
  übersprungen statt still grün gemeldet. (#667)

### Eine Zahl, ein Ort: die Python-Fassung des Abbilds

Sie steht im `Dockerfile` und sonst nirgends. Sie ist hier schon zweimal auseinander-
gelaufen — in #588 zwischen `Dockerfile` und den Workflows, in #667 zwischen `Dockerfile`
und `scripts/lock_requirements.py`, das mit `ZIEL_PYTHON = "3.12"` weiter für die alte
Fassung auflöste. Gemessen: 27 Pakete für 3.12 gegen 26 für 3.14. Zwei Prüfungen halten
das jetzt zusammen — `test_ci_tests_the_python_the_image_runs` für die Workflows und
`test_der_generator_zielt_auf_die_python_fassung_des_abbilds` für den Generator.

---

## English

### The four levels

| Level | File | What it sees | Runtime |
|---|---|---|---|
| Unit | `tests/test_smoke.py` | `app` through the Flask test client | ~5 s |
| Delivery | `tests/test_auslieferung.py` | real HTTP headers: compression, caching | <1 s |
| Contract | `tests/test_contract.py` | responses against `/api/openapi.json` | ~3 s |
| Browser | `tests/e2e/` | rendered HTML, JavaScript, keyboard, address bar | ~30 s |

The first three run in the **Tests** CI job, the browser level in its own **Browsertests**
job, so the fast part stays fast.

### Getting started

```bash
pip install -r requirements.txt -r requirements-dev.txt
playwright install --with-deps chromium      # once, about 115 MB

pytest                       # everything, with the coverage floor
pytest --ignore=tests/e2e    # without a browser
pytest tests/e2e --no-cov    # browser only
```

Without Playwright or Schemathesis installed, the affected files skip themselves via
`importorskip` and the suite still completes.

### Why the browser level exists

Eleven defects (#319–#324, #328–#330) sat in a green build. The test client renders no
HTML, runs no JavaScript and has neither a keyboard nor an address bar, so it cannot see
this class at all. Among them: navigation unreachable by keyboard, a view with no route
entry, and uncompressed assets.

### What each tool can and cannot do

**Playwright** drives a real browser: keyboard, address bar, console errors, viewports.

**`tests/e2e/bildmessung.py`** reads the pixels of an element screenshot — a small
`zlib`-based PNG decoder, no Pillow and no numpy. It is for the cases where boxes are not
enough: `getBoundingClientRect()` describes boxes, not what you see. In #659 a button's ×
sat 3 px right and 5.5 px low while every measured box looked plausible on its own — the
line box was simply taller than the content box holding it. `tintenraender()` returns the
margins around the bright pixels, and `None` when nothing clears the threshold; a caller
treating that as "centred" would pass vacuously.

For areas rather than glyphs, #657 added two more. `zeilensprung()` compares two pixel rows
**column by column** — an average would hide an edge that only spans part of the width. It
showed the Aurora glow jumping 84 colour units across the header's bottom edge, and 0
(median) afterwards. `zeilenspanne()` is its counter-check and matters just as much: a seam
is also step-free when the gradient is **gone entirely**, so a deleted glow would satisfy
any seam assertion. Only the span across one row proves there is something to see.

The border row is skipped on purpose: `#side` carries a deliberate 1 px `border-bottom`, so
the comparison runs two rows above against one row below — otherwise the check measures the
divider instead of the gradient.

**axe-core** covers contrast, missing names, ARIA and document structure. It has **no
rule** for a `div` carrying a click handler without a role — verified against the rule
reference, contrary to several widely repeated guides. An axe-only run would have reported
the library view as clean. Only a keyboard walk closes that gap.

**Schemathesis** generates cases from the spec. Four checks are enabled; three are
deliberately off because they fire for the wrong reason here — the reasoning is in the
header of `tests/test_contract.py`.

**Lighthouse** holds a transfer budget on the login page in CI. A budget, not a score:
scores fluctuate on shared runners, and a gate that goes red for no reason gets disabled.

### Known defects inside the suite

They live as `xfail(strict=True)` carrying their issue number. CI stays green, the finding
stays recorded, and whoever fixes it is told by the strict marker to remove it.
`xfail_strict` is set globally in `pytest.ini`.

### Three ratchets

They hold the level reached rather than stating a target:

| Ratchet | Where | Today |
|---|---|---|
| Coverage | `pytest.ini` | 69 % floor (measured: 70 %) |
| Views without a browser test | `test_views_are_covered_by_browser_tests` | 1 (`lists`) |
| View without a route entry | `test_every_view_has_a_route` | `xfail` on #320 |

### Traps that already sprung here

- **A test that finds nothing passes.** The keyboard test found no library rows on an
  empty instance and was vacuously true. Hence `bibliothek_gefuellt`.
- **`get_by_role` only finds what has a role.** An `<a>` without `href` has none; five
  checks skipped themselves and reported green. Hence `menuepunkt()`.
- **Two instances, not one.** The browser tests create the first user. On the same
  instance as the unit tests that makes `test_setup_and_login` order-dependent. Hence
  `servermod`.
- **The onboarding dialog traps focus** — correct for a modal. Left open, you measure it
  instead of the page. The `seite` fixture dismisses it.
- **`--cov=app` collects nothing** once `app.py` is loaded twice. Hence `--cov=.` plus
  `.coveragerc`.
- **A test can depend on the interpreter it is started with.** `requirements.txt`
  describes the image (`python:3.14-slim`), but `tests/test_abhaengigkeiten.py` evaluated
  the packages' environment markers against the running Python. On 3.12 `aiohttp` and
  `aiosignal` require `typing_extensions` behind `python_version < "3.13"` — the hull was
  27 packages there against 26 in the image, and `test_transitive_huelle_ist_vollstaendig`
  failed locally while the same check stayed green in CI. The red cross was not the
  problem; the obvious conclusion was. Adding `typing-extensions` would ship the image a
  package nothing there needs. Since #667 the markers are evaluated against the version in
  the `Dockerfile`, and where that cannot be measured the test skips with a stated reason
  instead of quietly reporting green. (#667)

### One number, one place: the image's Python version

It lives in the `Dockerfile` and nowhere else. It has drifted apart twice here — in #588
between the `Dockerfile` and the workflows, in #667 between the `Dockerfile` and
`scripts/lock_requirements.py`, which kept resolving for the old version via
`ZIEL_PYTHON = "3.12"`. Measured: 27 packages for 3.12 against 26 for 3.14. Two checks now
hold it together — `test_ci_tests_the_python_the_image_runs` for the workflows and
`test_der_generator_zielt_auf_die_python_fassung_des_abbilds` for the generator.
