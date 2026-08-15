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

## Wie melden

Über **GitHub Security Advisories** am Repository — direkt hier:
<https://github.com/Sparxx947/romseerr/security/advisories/new> (*Security → Report a
vulnerability*). Das hält den Fund nicht öffentlich, bis er behoben ist. Ein normales Issue geht auch — dann ist er
allerdings sofort für alle sichtbar, und das ist deine Entscheidung, nicht meine.

**Bitte keine Zugangsdaten, Token oder Adressen aus deiner Installation mitschicken.** Ein
Fehlerbericht wandert schneller weiter, als einem lieb ist; die Einstellungen-Ausgabe ist
genau deshalb maskiert.

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

## How to report

Through **GitHub Security Advisories** on the repository — directly here:
<https://github.com/Sparxx947/romseerr/security/advisories/new> (*Security → Report a
vulnerability*), which keeps the finding private until it is fixed. A normal issue works too,
but then it is public immediately — your call, not mine.

**Please do not include credentials, tokens or addresses from your installation.** A bug
report travels further than one expects; the settings export is masked for exactly that
reason.

## How it is handled

A confirmed finding gets an issue labelled `security`, a test that reproduces it, and the fix.
The test is the part that matters: without it the same fault returns at the next refactor and
nobody notices.

Static checks run on every PR (CodeQL, Bandit, Trivy, Gitleaks). A **dismissed** CodeQL alert
here always carries a reason naming the guard and the test that covers it — "false positive"
on its own does not count.
