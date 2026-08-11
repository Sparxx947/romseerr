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
