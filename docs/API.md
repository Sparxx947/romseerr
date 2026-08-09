# Romseerr API

Zweisprachige Kurzanleitung. Die **vollständige, maschinenlesbare** Spezifikation liefert die
App selbst:

- **Interaktiv:** `GET /api/docs` (Redoc)
- **OpenAPI 3.1 (JSON):** `GET /api/openapi.json`
- **Im Repo:** [`docs/openapi.yaml`](openapi.yaml) (aus `app.OPENAPI` erzeugt via
  `python scripts/build_openapi.py`)

Bilingual quick guide. The **complete, machine-readable** spec is served by the app itself
(`/api/docs`, `/api/openapi.json`); the repo copy is [`docs/openapi.yaml`](openapi.yaml).

---

## Deutsch

### Basis-URL
Alles läuft unter derselben Herkunft wie die Oberfläche, z. B. `http://<host>:8770`.
Antworten sind JSON (außer HTML-Seiten und PWA-Assets).

### Authentifizierung
Zwei Wege — beide gleichwertig für die meisten Endpunkte:

1. **Session-Cookie** (interaktiv): `POST /api/login` mit `{"username","password"}` setzt ein
   signiertes Cookie. Ersteinrichtung: `POST /api/setup` (nur solange kein Benutzer existiert).
2. **API-Key** (programmatisch, **Admin-äquivalent**): im Admin-Bereich → *Allgemein* anzeigen.
   Übergabe per Header **`X-Api-Key: <key>`** oder Query **`?apikey=<key>`**.

```bash
# API-Key im Header
curl -H "X-Api-Key: $KEY" http://host:8770/api/jobs

# oder als Query-Parameter
curl "http://host:8770/api/jobs?apikey=$KEY"

# Session-basiert (Cookie-Jar)
curl -c jar -X POST http://host:8770/api/login \
     -H 'Content-Type: application/json' -d '{"username":"admin","password":"…"}'
curl -b jar http://host:8770/api/search?q=zelda
```

### Berechtigungen
Über den reinen Login hinaus gibt es feingranulare Rechte (Admins haben implizit alle):
`request`, `autoapprove`, `manage_requests`, `manage_users`, `manage_issues`,
`manage_settings`, `quota_exempt`. Fehlt ein Recht, antwortet die API mit **403**;
ohne gültige Session/Key mit **401**.

### Konventionen
- Request-Bodies sind JSON (`Content-Type: application/json`).
- Erfolg: meist `{"ok": true, …}`. Fehler: `{"error": "…"}` mit passendem HTTP-Status.
- `/api/forgot` antwortet **generisch** (verrät nicht, ob ein Konto existiert).

### Endpunkt-Gruppen
| Gruppe | Beispiele |
|---|---|
| System | `GET /health`, `GET /api/version`, `GET /metrics`, `GET /api/auth/status` |
| Auth | `POST /api/setup`, `/api/login`, `/api/logout`, `/api/forgot`, `/api/reset` |
| Suche | `GET /api/search`, `/api/discover/rows`, `/api/detail`, `/api/platforms`, `/api/coverage`, `/api/ra/status` |
| Anfragen | `POST /api/download`, `GET /api/jobs`, `POST /api/jobs/{id}/approve\|deny\|retry\|reimport`, `DELETE /api/jobs/{id}`, `POST /api/wishlist/import` |
| Probleme | `GET/POST /api/issues`, `/api/issues/{id}/comment\|close` |
| Profil | `GET/POST /api/profile`, `/api/profile/password` |
| Push | `GET /api/push/pubkey`, `POST /api/push/subscribe` |
Schreibende Benutzer-Endpunkte antworten mit **400**, wenn nach der Änderung kein Admin
mit Passwort übrig bliebe — das gilt für `PATCH /api/users/{u}` (Rolle entziehen) ebenso
wie für `DELETE /api/users/{u}`. Eine vollständig leere Benutzerliste ist erlaubt und
führt zur Ersteinrichtung.

| Admin | `/api/users`, `/api/settings`, `/api/blocklist`, `/api/logs`, `/api/apikey`, `/api/export`, `/api/import` |
| Diagnose | `GET /api/services/status`, `GET /api/config/warnings`, `GET /api/usenet/check` |
| Aufräumen | `GET /api/leftovers`, `POST /api/leftovers/remove`, `POST /api/jobs/{jid}/reimport` |

`GET /api/usenet/check` misst den Usenet-Weg stufenweise durch (Suche, SAB-Kategorie,
Warteschlange, Einsammelordner) und lädt dabei **nichts** herunter. Die letzte Stufe
nennt Romseerrs und SABnzbds Sicht auf den Ordner mit den fertigen Downloads
nebeneinander — laufen sie auseinander, läuft der Download durch und wird nie
eingesammelt. Eine weitere Stufe je Indexer (`step: "indexer:<Name>"`) holt **eine**
Datei ab und meldet, ob wirklich eine NZB kommt; das zählt beim Indexer als Abruf gegen
sein Stundenlimit. Antwort: `{"ok": bool, "steps": [{"step", "ok", "info"}]}`.

`GET /api/leftovers` lists downloads a failed import left behind;
`POST /api/leftovers/remove` clears one (`{"jid": "…"}`) or all (`{"all": true}`).
Only paths resolving inside a collect directory and carrying the `romseerr_` prefix are
ever deleted — a path from the request is never used, and folders owned by a running job
are not listed at all. `POST /api/jobs/{jid}/reimport` re-reads a kept download without
fetching it again (state `error` only) — unlike `/retry`, which downloads the whole
release a second time. `DELETE /api/jobs/{jid}` removes a finished request (active ones are
refused with 400); `{"files": true}` deletes a kept download along with it, otherwise the
response reports `files_left`. `clear-finished` accepts `{"states": [...]}`. `POST /api/jobs/{jid}/retry` counts attempts and switches source from the third one; with none left it answers **409** with `exhausted: true` instead of re-queueing.

Details (Parameter, Bodies, Antworten) → `/api/docs`.

### Export / Import
`GET /api/export` liefert ein versioniertes JSON-Dokument (Einstellungen, Benutzer & Rechte,
Anfragen, Wunschlisten) — **ohne Geheimnisse**. An deren Stelle steht `__REDACTED__`, damit der
Import „war gesetzt, kenne ich aber nicht" von „war leer" unterscheiden kann.

Sollen Geheimnisse mit, geht das nur über `POST /api/export` mit
`{"secrets":"encrypt","passphrase":"…"}` — die Passphrase gehört nicht in eine URL. Sie werden
dann mit PBKDF2-SHA256 (200 000 Runden) + Fernet verschlüsselt beigelegt.

`POST /api/import` verlangt `document` **und** `mode` (`merge` oder `replace`) — es gibt bewusst
keinen Standard. Abgelehnt wird: fremdes oder fehlendes Schema, eine neuere Schema-Version,
eine falsche Passphrase und jeder Import, der **keinen Administrator mit Kennwort** übrig ließe.
`__REDACTED__` bedeutet auch im `replace`-Modus „behalte den bestehenden Wert".

### Metriken (Prometheus)
`GET /metrics` liefert Betriebsmetriken im Prometheus-Textformat (0.0.4). Der Endpunkt ist
**nicht** öffentlich — Metriken verraten Nutzungsmuster —, sondern hängt an derselben
Schleuse wie die API. Ein Scraper nutzt daher den API-Key:

```yaml
scrape_configs:
  - job_name: romseerr
    static_configs: [{targets: ["romseerr:8770"]}]
    params:
      apikey: ["<API-Key aus Einstellungen>"]
```

Enthalten sind Anfragen je Zustand, Warteschlangen-Tiefe und Alter des ältesten wartenden
Eintrags, Import-Ausgänge als Zähler (`result`/`reason`), Wunschlisten-Größe, Zeitpunkt des
letzten Durchlaufs je Hintergrund-Worker, Bibliotheks-Kennzahlen und `romseerr_build_info`.
Es gibt bewusst **keine Label je Titel oder Nutzer** — die Kardinalität würde sonst mit der
Bibliothek wachsen.

---

## English

### Base URL
Everything is served from the same origin as the UI, e.g. `http://<host>:8770`. Responses are
JSON (except HTML pages and PWA assets).

### Authentication
Two equivalent options for most endpoints:

1. **Session cookie** (interactive): `POST /api/login` with `{"username","password"}`. First-run:
   `POST /api/setup` (only while no user exists).
2. **API key** (programmatic, **admin-equivalent**): show it in Admin → *General*. Pass it via
   header **`X-Api-Key: <key>`** or query **`?apikey=<key>`**.

See the curl examples above.

### Permissions
Write operations on users return **400** if the change would leave no admin with a password
(`PATCH /api/users/{u}`, `DELETE /api/users/{u}`). An entirely empty user list is allowed and
triggers first-run setup.

Fine-grained permissions beyond login (admins implicitly have all): `request`, `autoapprove`,
`manage_requests`, `manage_users`, `manage_issues`, `manage_settings`, `quota_exempt`. Missing a
permission returns **403**; missing/invalid auth returns **401**.

### Conventions
- JSON request bodies (`Content-Type: application/json`).
- Success is usually `{"ok": true, …}`; errors are `{"error": "…"}` with an appropriate HTTP
  status. `/api/forgot` responds generically (does not reveal whether an account exists).

`GET /api/leftovers` listet Downloads, die ein fehlgeschlagener Import liegen gelassen
hat; `POST /api/leftovers/remove` entfernt einen (`{"jid": "…"}`) oder alle
(`{"all": true}`). Gelöscht wird nur, was unterhalb eines Sammelordners liegt und das
`romseerr_`-Präfix trägt — ein Pfad aus dem Request wird nie verwendet. Ordner laufender
Aufträge erscheinen gar nicht erst.

`POST /api/jobs/{jid}/reimport` liest einen liegengebliebenen Download **erneut ein**,
ohne ihn neu zu holen (nur im Zustand `error`, nur solange die Dateien da sind). Nicht zu
verwechseln mit `POST /api/jobs/{jid}/retry`, das den kompletten Download wiederholt.

`DELETE /api/jobs/{jid}` entfernt eine **abgeschlossene** Anfrage; laufende werden mit
400 abgewiesen. Mit `{"files": true}` wird ein noch vorhandener Download mitgelöscht,
sonst meldet die Antwort `files_left: true` — der Auftrag ist das Einzige, was den Ordner
noch einem Titel zuordnet. `POST /api/jobs/clear-finished` nimmt optional
`{"states": ["error"]}`, um nur eine Gruppe zu räumen.

`POST /api/jobs/{jid}/retry` zählt die Versuche mit und wechselt **ab dem dritten** die
Quelle. Gibt es keine passende mehr, antwortet er mit **409** und `exhausted: true` und
stellt den Auftrag *nicht* erneut ein. Ein geglückter Import setzt `tries` zurück.

### Diagnostics
`GET /api/services/status`, `GET /api/config/warnings` and `GET /api/usenet/check` (all
`manage_settings`). The last one measures the usenet path stage by stage — search, SAB
category, queue, collect folder — and downloads **nothing**. Its final stage prints
Romseerr's and SABnzbd's view of the completed-downloads folder side by side: if they
diverge, downloads finish and are never picked up. One further stage per indexer
(`step: "indexer:<name>"`) fetches **one** file and reports whether an actual NZB comes
back — this counts as a grab against that indexer's hourly limit. Response:
`{"ok": bool, "steps": [{"step", "ok", "info"}]}`.

Full details (parameters, bodies, responses) live in the interactive docs at `/api/docs`.

### Export / import
`GET /api/export` returns a versioned JSON document (settings, users & permissions, requests,
wishlists) **without secrets** — `__REDACTED__` stands in their place so an import can tell
"was set, but I do not know it" from "was empty".

To include secrets, use `POST /api/export` with `{"secrets":"encrypt","passphrase":"…"}` — a
passphrase does not belong in a URL. They are then attached encrypted with PBKDF2-SHA256
(200,000 iterations) + Fernet.

`POST /api/import` requires `document` **and** `mode` (`merge` or `replace`); there is
deliberately no default. Rejected: a foreign or missing schema, a newer schema version, a wrong
passphrase, and any import that would leave **no admin with a password**. `__REDACTED__` means
"keep the existing value" even in `replace` mode.

### Metrics (Prometheus)
`GET /metrics` serves operational metrics in the Prometheus text format (0.0.4). The endpoint is
**not** public — metrics leak usage patterns — it sits behind the same gate as the API, so a
scraper authenticates with the API key:

```yaml
scrape_configs:
  - job_name: romseerr
    static_configs: [{targets: ["romseerr:8770"]}]
    params:
      apikey: ["<API key from settings>"]
```

Exposed: requests by state, queue depth and age of the oldest waiting item, import outcomes as a
counter (`result`/`reason`), wishlist size, last-run timestamp per background worker, library
figures and `romseerr_build_info`. There are deliberately **no per-title or per-user labels** —
cardinality would otherwise grow with the library.
