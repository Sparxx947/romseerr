# Contributing / Mitwirken

Danke, dass du zu Romseerr beitragen möchtest! / Thanks for contributing to Romseerr!

## Deutsch

### Workflow
1. **Feature-Branch** von `main` erstellen (`feat/…`, `fix/…`, `ci/…`, `docs/…`).
2. Änderungen committen — **Conventional Commits auf Englisch**
   (`feat(scope): …`, `fix(scope): …`). Der Release-Bot leitet daraus Version & Changelog ab.
3. **Pull Request** öffnen. `main` ist geschützt: PR-Pflicht, kein Force-Push und **alle
   Status-Checks müssen grün sein** (Lint, Tests, Docker-Build, Bandit, Gitleaks, Trivy).
4. Nach dem Merge (Squash) räumt der Bot den Branch auf.

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

### Workflow
1. Create a **feature branch** off `main` (`feat/…`, `fix/…`, `ci/…`, `docs/…`).
2. Commit using **English Conventional Commits** (`feat(scope): …`). The release bot
   derives version & changelog from these.
3. Open a **pull request**. `main` is protected: PR required, no force-push, and **all
   status checks must pass** (lint, tests, docker build, Bandit, Gitleaks, Trivy).
4. Squash-merge; the bot deletes the branch.

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
