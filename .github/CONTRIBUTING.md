# Contributing / Mitwirken

Danke, dass du zu Romseerr beitragen möchtest! / Thanks for contributing to Romseerr!

## Deutsch

### Zweigmodell

| Zweig | Was drin ist | Wer schreibt |
|---|---|---|
| **`dev`** | Entwicklungsstand, Standardzweig | Feature-Branch → PR → `dev` |
| **`main`** | **genau der aktuelle Release**, sonst nichts | nur der Release-Lauf |

`main` ist kein Zweig, auf dem gearbeitet wird — es ist ein **Zeiger auf den zuletzt
veröffentlichten Stand**. Wer das Projekt nachbaut und `main` auscheckt, bekommt
etwas, das als Release durchgetestet wurde, nicht den Zwischenstand von gestern Abend.

Weil `dev` den Inhalt von `main` immer vollständig enthält, ist jede Bewegung von
`main` ein **Fast-Forward**. Erzwungene Pushes sind dort gesperrt — und das ist kein
Hindernis, sondern der Beweis, dass das Modell hält: schlägt das Vorspulen fehl, ist
etwas an `dev` vorbei auf `main` gelangt, und der Release-Lauf bricht laut ab.

### Workflow
1. **Feature-Branch** von `dev` erstellen (`feat/…`, `fix/…`, `ci/…`, `docs/…`).
2. Änderungen committen — **Conventional Commits auf Englisch**
   (`feat(scope): …`, `fix(scope): …`). Der Release-Bot leitet daraus Version & Changelog ab.
3. **Pull Request gegen `dev`** öffnen. `dev` ist geschützt: PR-Pflicht, kein Force-Push
   und **alle Status-Checks müssen grün sein** (Lint, Tests, Docker-Build, Bandit,
   Gitleaks, Trivy, Content-Policy).
4. Nach dem Merge (Squash) räumt der Bot den Branch auf.

### Wie ein Release entsteht
1. Der Bot sammelt die Commits auf `dev` und hält einen **Release-PR** offen
   (Version in `version.txt`, Abschnitt im `CHANGELOG.md`).
2. Diesen PR mergen = Release: Tag und GitHub-Release entstehen.
3. Der Lauf spult danach **`main` auf genau diesen Commit** vor.

Die Version wird **nicht von Hand** gesetzt. Auf `dev` steht in `version.txt` eine
Entwicklungsmarke (`…-dev`); den echten Wert schreibt der Bot im Release-PR. Maßgeblich
ist `.release-please-manifest.json` — dort steht, worauf zuletzt veröffentlicht wurde.

### Versionszweige — bewusst erst bei Bedarf

Es gibt **keine** `release/x.y`-Zweige, und das ist eine Entscheidung, keine Lücke.
Sie lohnen sich, wenn mehrere Versionen **gleichzeitig gepflegt** werden müssen — wenn
also jemand auf einer alten Version festsitzt und trotzdem Fixes braucht. Solange das
nicht so ist, kosten sie Cherry-Picks und einen weiteren grün zu haltenden Zweig, ohne
etwas zu kaufen.

Der Aufschub ist gratis: Weil jeder Release ein Tag hat, lässt sich ein Versionszweig
in dem Moment, in dem er zum ersten Mal gebraucht wird, rückwirkend exakt schneiden.

```bash
git switch -c release/1.0 v1.0.0     # Fix drauf, taggen als v1.0.1
```

### Lokal entwickeln & testen
```bash
pip install -r requirements.txt pytest
# Tests laufen gegen temporäre Verzeichnisse, nie gegen echte Daten:
pytest -q
```
Die App liest ihre Datenpfade aus `ROMSEERR_CONFIG` (Default `/config`) und
`ROMSEERR_ROMS` (Default `/roms`). Für einen lokalen Lauf `cp .env.example .env` und
Werte setzen; der komplette Stack liegt in `docker-compose.yml`.

### Konventionen
- **Doku zweisprachig** (Deutsch **und** Englisch), z. B. im `CHANGELOG.md`.
- Neue Funktion → wenn möglich einen **Smoke-Test** in `tests/` ergänzen.
- Das eingebettete JavaScript liegt in Python-Strings (`PAGE`): **Backslash-Escapes
  verdoppeln** (`\\n`), sonst zerbricht das Skript. Der Test `test_inline_js_parses` wacht darüber.
- **Keine Geheimnisse** committen (`.env`, Keys, Tokens). Gitleaks scannt jeden PR.

### Was hier NICHT hineingehört

Romseerr ist **Werkzeug** — es beschafft, hostet und verlinkt keine Inhalte. Dieses
Repository enthält deshalb nie:

| | |
|---|---|
| ROMs, Abbilder, Spielinhalte | nicht unser Eigentum |
| BIOS, Firmware, Konsolen-Schlüssel | dasselbe, und für die meisten Plattformen aus keiner autorisierten Quelle beziehbar |
| Emulator-Binärdateien | Lizenzen sind unterschiedlich — wir holen sie von den Projekten |
| **URLs zu Inhaltsquellen** | die trägt der Betreiber in den Einstellungen ein, nicht wir |
| Prüfsummenlisten als Erkennungshilfe für fremde Kopien | die eigene Sicherung prüfen ist in Ordnung, ein Nachschlagewerk für fremde Dateien nicht |

Was hineingehört: Parser, Abrufe von **offiziellen Projektquellen**, und Mechanismen,
über die ein Betreiber seine **eigenen** Quellen angibt.

Ein CI-Lauf prüft das bei jedem Pull Request. Beiträge, die dagegen verstoßen, werden
geschlossen — das steht hier, damit niemand die Arbeit erst investiert und es dann
erfährt.

## English

### Branch model

| Branch | Contents | Who writes |
|---|---|---|
| **`dev`** | development trunk, default branch | feature branch → PR → `dev` |
| **`main`** | **exactly the current release**, nothing else | the release run only |

`main` is not a branch you work on — it is a **pointer to what was last published**.
Check it out and you get something that went through a release, not last night's
work in progress.

Because `dev` always contains all of `main`, every move of `main` is a **fast-forward**.
Force-pushes are blocked there, and that is not an obstacle but the proof that the model
holds: if the fast-forward fails, something reached `main` outside `dev`, and the release
run fails loudly instead of rewriting history.

### Workflow
1. Create a **feature branch** off `dev` (`feat/…`, `fix/…`, `ci/…`, `docs/…`).
2. Commit using **English Conventional Commits** (`feat(scope): …`). The release bot
   derives version & changelog from these.
3. Open a **pull request against `dev`**. `dev` is protected: PR required, no force-push,
   and **all status checks must pass** (lint, tests, docker build, Bandit, Gitleaks,
   Trivy, content policy).
4. Squash-merge; the bot deletes the branch.

### How a release happens
1. The bot collects commits on `dev` and keeps a **release PR** open (version in
   `version.txt`, a section in `CHANGELOG.md`).
2. Merging that PR is the release: tag and GitHub release are created.
3. The run then fast-forwards **`main` to exactly that commit**.

Versions are **never set by hand**. `version.txt` on `dev` carries a development marker
(`…-dev`); the real value is written by the bot in the release PR. The source of truth is
`.release-please-manifest.json`.

### Version branches — deliberately deferred

There are **no** `release/x.y` branches, and that is a decision rather than an omission.
They earn their keep when several versions must be **maintained in parallel** — someone
stuck on an old version who still needs fixes. Until that is true they cost cherry-picks
and another branch to keep green, and buy nothing.

Deferring is free: every release is tagged, so a version branch can be cut retroactively
at the exact moment it is first needed.

```bash
git switch -c release/1.0 v1.0.0     # fix on top, tag as v1.0.1
```

### Develop & test locally
```bash
pip install -r requirements.txt pytest
pytest -q
```
Data paths come from `ROMSEERR_CONFIG` (default `/config`) and `ROMSEERR_ROMS`
(default `/roms`). For a local run, `cp .env.example .env` and fill in values; the full
stack is in `docker-compose.yml`.

### Conventions
- **Bilingual docs** (German **and** English), e.g. in `CHANGELOG.md`.
- New feature → add a **smoke test** under `tests/` where feasible.
- The embedded JavaScript lives inside Python strings (`PAGE`): **double your backslash
  escapes** (`\\n`) or the script breaks. `test_inline_js_parses` guards this.
- **Never commit secrets** (`.env`, keys, tokens). Gitleaks scans every PR.

### What does not belong here

Romseerr is **tooling** — it does not host, obtain or link to content. This
repository therefore never contains:

| | |
|---|---|
| ROMs, disc images, game content | not ours to distribute |
| BIOS, firmware, console keys | the same, and unobtainable from any authorised source for most platforms |
| Emulator binaries | licences vary — we fetch them from the projects instead |
| **URLs to content sources** | the operator supplies those in settings, not us |
| Checksum lists serving to identify someone else's copy | verifying your own dump is fine; a lookup table for other people's files is not |

What does belong: parsers, fetchers pointed at **official project releases**, and
mechanisms through which an operator supplies their **own** sources.

CI checks this on every pull request. Contributions that cross the line are closed —
stated here so nobody invests the work first and finds out afterwards.
