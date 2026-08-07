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
| System | `GET /health`, `GET /api/auth/status` |
| Auth | `POST /api/setup`, `/api/login`, `/api/logout`, `/api/forgot`, `/api/reset` |
| Suche | `GET /api/search`, `/api/discover/rows`, `/api/detail`, `/api/platforms` |
| Anfragen | `POST /api/download`, `GET /api/jobs`, `POST /api/jobs/{id}/approve\|deny` |
| Probleme | `GET/POST /api/issues`, `/api/issues/{id}/comment\|close` |
| Profil | `GET/POST /api/profile`, `/api/profile/password` |
| Push | `GET /api/push/pubkey`, `POST /api/push/subscribe` |
| Admin | `/api/users`, `/api/settings`, `/api/blocklist`, `/api/logs`, `/api/apikey` |

Details (Parameter, Bodies, Antworten) → `/api/docs`.

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
Fine-grained permissions beyond login (admins implicitly have all): `request`, `autoapprove`,
`manage_requests`, `manage_users`, `manage_issues`, `manage_settings`, `quota_exempt`. Missing a
permission returns **403**; missing/invalid auth returns **401**.

### Conventions
- JSON request bodies (`Content-Type: application/json`).
- Success is usually `{"ok": true, …}`; errors are `{"error": "…"}` with an appropriate HTTP
  status. `/api/forgot` responds generically (does not reveal whether an account exists).

Full details (parameters, bodies, responses) live in the interactive docs at `/api/docs`.
