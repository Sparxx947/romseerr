# Mitarbeiten / Contributing

*Deutsch zuerst, English below.*

---

## Deutsch

### Dokumentation ist Pflicht — und zweisprachig

Jede Änderung, die das Verhalten berührt, wird dokumentiert: `README.md` **und**
`README.en.md`, bei API-Änderungen zusätzlich `docs/API.md`, bei Struktur- oder
Betriebsfragen `docs/ARCHITECTURE.md`. Kommentare im Quelltext erklären das **Warum**,
nicht das Was — das Was steht schon im Code.

Vier Dinge prüft die Testsuite selbst, und genau diese vier sind nie verrutscht:

| Prüfung | Test |
|---|---|
| Jede Route steht in der Spezifikation | `test_openapi_covers_all_routes` |
| Spezifikation und App stimmen überein | `test_openapi_yaml_in_sync` |
| Build-Argumente sind dokumentiert | `test_docs_explain_how_to_build_with_provenance` |
| Ältere Fassung betreiben ist dokumentiert | `test_the_readme_says_how_to_run_an_older_version` |

Seit #212 kommen zwei **Ratschen** dazu. Sie halten den erreichten Stand fest, statt ein
Ziel zu setzen: neuer Code darf ihn nicht verschlechtern, jede nachgebesserte Stelle hebt
den Boden.

- **Zweisprachige Kommentare** (`test_bilingual_comment_share_does_not_drop`): Der Anteil
  der Kommentarblöcke ab drei Zeilen mit englischem Teil darf nicht unter den heutigen
  Wert fallen. Praktisch heißt das: **ein neuer Block ab drei Zeilen braucht einen
  englischen Teil.** Wer bestehende nachbessert, hebt `DOC_EN_BODEN`.
- **Docstrings an Routen** (`test_new_routes_carry_a_docstring`): Die Zahl der
  Route-Handler ohne Docstring darf nicht steigen. Der Altbestand ist kein Auftrag für
  einen großen Durchgang, sondern Schuld, die beim nächsten Anfassen beglichen wird.

Die Erkennung „enthält einen englischen Teil" ist eine Heuristik. Sie wurde **vor** der
Einführung gegen alle Blöcke geprüft, mit einer unabhängig gebauten Kontrollregel: null
falsch negative Treffer. Das war die Bedingung — eine Prüfung, die grundlos anschlägt,
wird abgeschaltet, und dann steht die Regel schlechter da als ganz ohne Test. Wer die
Heuristik ändert, misst sie erneut und schreibt das Ergebnis in den Docstring.

**Was sich nicht prüfen lässt**, wird auch nicht so getan, als ob: ob ein Abschnitt
verständlich ist, ob ein Kommentar den entscheidenden Grund nennt, ob ein Beispiel
weiterhilft — das bleibt Sorgfalt. Die Ratschen sichern den Boden, nicht die Qualität.

### Eine Änderung an einer Ansicht ist erst fertig, wenn sie im Browser geöffnet war

**Das ist die Regel.** Ein bestandener Unit-Test sagt nichts über eine Seite, die nie
gerendert wurde.

Der Anlass ist gemessen, nicht befürchtet: Elf Fehler (#319–#324, #328–#330) saßen in
einem **grünen Build**, drei davon in Code, der am selben Tag geschrieben worden war. Alle
elf waren binnen Minuten sichtbar, sobald die Seite tatsächlich geöffnet wurde. Der
Testclient rendert kein HTML, führt kein JavaScript aus und kennt weder Tastatur noch
Adresszeile — er kann diese Klasse von Fehlern gar nicht sehen.

Praktisch heißt das:

| Was geändert wird | Was dazugehört |
|---|---|
| Eine Ansicht, ein Bedienelement, die Navigation | ein Test in `tests/e2e/`, der die Seite lädt |
| Eine Route oder ihre Antwort | die Spezifikation mitziehen — `tests/test_contract.py` prüft sie gegen den laufenden Server |
| Auslieferung, Köpfe, Caching | `tests/test_auslieferung.py` |

Vier Werkzeuge stehen dafür bereit (`requirements-dev.txt`):

- **Playwright** — echter Browser, Tastatur, Adresszeile, Konsolenfehler
- **axe-core** — Kontrast, fehlende Namen, ARIA. **Nicht** anklickbare `div`s ohne Rolle;
  dafür gibt es keine Regel. Das prüft nur ein Tastaturdurchlauf.
- **Schemathesis** — erzeugt Fälle aus `/api/openapi.json` und hält den Vertrag
- **coverage** — als dritte Ratsche, Boden 69 % (`pytest.ini`)

Bekannte, noch nicht behobene Fehler stehen als `xfail(strict=True)` mit Issue-Nummer in
der Suite. So bleibt CI grün, der Befund bleibt festgehalten, und wer den Fehler behebt,
wird von der Ratsche daran erinnert, den Marker zu entfernen. `xfail_strict` ist global
gesetzt — ein stiller Selbstheiler bleibt nicht unbemerkt.

**Zwei Fallen, beide bereits zugeschlagen:**

- **Ein Test, der nichts findet, besteht.** Der Tastaturtest für die Bibliothek fand auf
  der leeren Instanz keine Zeilen und war inhaltsleer wahr. Wer etwas sucht, prüft auch,
  dass es etwas zu suchen gab — dafür gibt es `bibliothek_gefuellt`.
- **`get_by_role` findet nur, was eine Rolle hat.** Ein `<a>` ohne `href` hat keine. Fünf
  Prüfungen haben sich deshalb selbst übersprungen und trotzdem Grün gemeldet. Ein `skip`
  im Testkörper ist fast immer der falsche Zweig — besser ein `assert`.

### Weiteres

- Commits nach [Conventional Commits](https://www.conventionalcommits.org), auf Englisch.
- Issues und Pull Requests auf Englisch; die Oberfläche spricht fünf Sprachen
  (de, en, fr, es, it) — ein neuer Text gehört in **alle fünf**.
- Neue Prüfungen müssen mindestens einmal **rot** gesehen worden sein. Ein Test, der nur
  den Gutfall kennt, besteht auch gegen kaputten Code.

---

## English

### Documentation is mandatory — and bilingual

Every behaviour-affecting change is documented: `README.md` **and** `README.en.md`, plus
`docs/API.md` for API changes and `docs/ARCHITECTURE.md` for structural or operational
ones. Source comments explain the **why**, not the what — the code already says the what.

Four things the test suite checks itself, and those four have never drifted:
route coverage in the spec, spec/app agreement, documented build arguments, and documented
instructions for running an older version.

Since #212 there are two **ratchets**. They hold today's level rather than setting a
target: new code may not lower it, and every improvement raises the floor.

- **Bilingual comments** (`test_bilingual_comment_share_does_not_drop`): the share of
  comment blocks of three or more lines carrying an English part may not fall below its
  current value. In practice: **a new block of three or more lines needs an English part.**
  Improve existing ones and raise `DOC_EN_BODEN`.
- **Docstrings on routes** (`test_new_routes_carry_a_docstring`): the number of route
  handlers without a docstring may not grow. The existing ones are not a task for one big
  pass — they are debt paid the next time that code is touched anyway.

Detecting "has an English part" is a heuristic. It was validated **before** being enabled,
against every block, using an independently built control rule: zero false negatives. That
was the condition — a check that fires for the wrong reason gets disabled within a week,
and then the rule is worse off than with no test at all. If you change the heuristic,
measure it again and record the result in its docstring.

**What cannot be checked is not pretended to be**: whether a section is understandable,
whether a comment names the decisive reason, whether an example helps. That stays a matter
of care. The ratchets secure the floor, not the quality.

### A change to a view is not finished until it has been opened in a browser

**That is the rule.** A passing unit test says nothing about a page that never rendered.

The reason is measured, not feared: eleven defects (#319–#324, #328–#330) sat in a **green
build**, three of them in code written the same day, and all eleven were visible within
minutes of actually opening the page. The test client renders no HTML, runs no JavaScript
and has neither a keyboard nor an address bar — it cannot see this class of defect at all.

| What you change | What comes with it |
|---|---|
| A view, a control, the navigation | a test in `tests/e2e/` that loads the page |
| A route or its response | update the spec — `tests/test_contract.py` checks it against the running server |
| Delivery, headers, caching | `tests/test_auslieferung.py` |

Four tools are available (`requirements-dev.txt`): **Playwright** (real browser, keyboard,
address bar, console errors), **axe-core** (contrast, missing names, ARIA — **not**
clickable `div`s without a role; no rule covers those, only a keyboard walk does),
**Schemathesis** (generates cases from `/api/openapi.json`) and **coverage** as a third
ratchet with a 69 % floor.

Known, unfixed defects live in the suite as `xfail(strict=True)` carrying their issue
number: CI stays green, the finding stays recorded, and whoever fixes it is told by the
strict marker to remove it. `xfail_strict` is set globally.

**Two traps, both already sprung:**

- **A test that finds nothing passes.** The library keyboard test found no rows on an
  empty instance and was vacuously true. If you search for something, assert that there
  was something to search — that is what `bibliothek_gefuellt` is for.
- **`get_by_role` only finds what has a role.** An `<a>` without `href` has none. Five
  checks skipped themselves and still reported green. A `skip` inside a test body is
  almost always the wrong branch; prefer an `assert`.

### Also

- Commits follow Conventional Commits, in English.
- Issues and pull requests in English; the interface speaks five languages
  (de, en, fr, es, it) — a new string belongs in **all five**.
- A new check must have been seen **failing** at least once. A test that only knows the
  good case passes against broken code too.
