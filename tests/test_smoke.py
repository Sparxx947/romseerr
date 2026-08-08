"""Smoke-Tests / smoke tests für Romseerr.

Prüfen Verhalten (nicht nur Syntax): Health, Titel-Normalisierung/Dedup, Bibliotheks-Index,
Sperrliste, Setup-/Login-Fluss und dass das eingebettete JavaScript gültig ist.
"""
import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

import pytest


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_norm_strips_noise(appmod):
    # Endung, Sonderzeichen, Region/Klammern werden entfernt
    assert appmod.norm("Zelda!!!.sfc") == "zelda"
    # Zwei Schreibweisen desselben Spiels kollidieren -> Grundlage der Dedup
    assert appmod.norm("Chrono Trigger (USA).sfc") == appmod.norm("Chrono_Trigger.smc")


def test_in_library_roundtrip(appmod):
    snes = os.path.join(appmod.ROMS, "snes")
    os.makedirs(snes, exist_ok=True)
    open(os.path.join(snes, "Chrono Trigger (USA).sfc"), "w").close()
    appmod.build_index()
    assert appmod.in_library("Chrono Trigger", "snes") is True
    assert appmod.in_library("No Such Game 99999", "snes") is False


def test_index_persists_to_db(appmod):
    # nach build_index muss der Index aus der DB ladbar sein (Kern von #21)
    appmod.build_index()
    ts = appmod.load_index_from_db()
    assert ts is not None
    assert len(appmod.LIB["all"]) >= 1


def test_kv_store_roundtrip(appmod):
    """settings/issues/push liegen im SQLite-kv-Store — Schreiben/Lesen muss round-trippen."""
    appmod.save_settings({"general": {"app_name": "RTtest"}})
    assert appmod.load_settings().get("general", {}).get("app_name") == "RTtest"
    appmod.save_issues([{"id": "x1", "title": "t"}])
    assert appmod.load_issues()[0]["id"] == "x1"
    appmod.save_settings({})   # aufräumen / cleanup
    appmod.save_issues([])


def test_cfg_connection_override(appmod):
    """Verbindungswerte: Einstellung hat Vorrang vor Env-Default; URL wird getrimmt."""
    appmod.save_settings({})
    assert appmod.cfg("sab_url") == appmod._ENV_CONN["sab_url"]   # Fallback = Env
    appmod.save_settings({"connections": {"sab_url": "http://sab.example:8080/"}})
    assert appmod.cfg("sab_url") == "http://sab.example:8080"     # Override + rstrip
    appmod.save_settings({})


def test_blocklist(appmod):
    assert appmod.is_blocked("Pokemon Beta Build", ["beta"]) is True
    assert appmod.is_blocked("Super Mario World", ["beta"]) is False


def test_setup_and_login(client):
    st = client.get("/api/auth/status").get_json()
    if st["setup"]:
        r = client.post("/api/setup",
                        json={"username": "admin", "password": "pw123456", "display_name": "Admin"})
        assert r.status_code == 200
    r = client.post("/api/login", json={"username": "admin", "password": "pw123456"})
    assert r.status_code == 200
    assert client.get("/api/auth/status").get_json()["setup"] is False


def test_login_wrong_password_rejected(client):
    st = client.get("/api/auth/status").get_json()
    if st["setup"]:
        client.post("/api/setup",
                    json={"username": "admin", "password": "pw123456", "display_name": "Admin"})
    r = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code != 200


def test_login_rate_limited(appmod, client):
    """Nach zu vielen Fehlversuchen antwortet der Login mit 429 (Bruteforce-Schutz)."""
    codes = [client.post("/api/login", json={"username": "rl_probe", "password": "x"}).status_code
             for _ in range(appmod.LOGIN_MAX + 2)]
    assert 429 in codes, f"kein 429 nach {appmod.LOGIN_MAX} Fehlversuchen: {codes}"


def test_session_cookie_hardened(appmod):
    assert appmod.app.config["SESSION_COOKIE_SAMESITE"] == "Strict"
    assert appmod.app.config["SESSION_COOKIE_HTTPONLY"] is True


def test_retry_unknown_job_404(client):
    st = client.get("/api/auth/status").get_json()
    if st["setup"]:
        client.post("/api/setup", json={"username": "admin", "password": "pw123456", "display_name": "A"})
    client.post("/api/login", json={"username": "admin", "password": "pw123456"})
    assert client.post("/api/jobs/does-not-exist/retry").status_code == 404


def test_tls_upload_and_status(client):
    """TLS-Upload: ungültig -> 400; gültiges self-signed -> gespeichert, Status zeigt CN."""
    st = client.get("/api/auth/status").get_json()
    if st["setup"]:
        client.post("/api/setup", json={"username": "admin", "password": "pw123456", "display_name": "A"})
    client.post("/api/login", json={"username": "admin", "password": "pw123456"})
    assert client.post("/api/settings/tls", json={"cert": "x", "key": "y"}).status_code == 400
    try:
        import datetime
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        pytest.skip("cryptography nicht verfügbar")
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subj = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test.local")])
    crt = (x509.CertificateBuilder().subject_name(subj).issuer_name(subj)
           .public_key(k.public_key()).serial_number(x509.random_serial_number())
           .not_valid_before(datetime.datetime.utcnow())
           .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=30))
           .sign(k, hashes.SHA256()))
    cert_pem = crt.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                              serialization.NoEncryption()).decode()
    r = client.post("/api/settings/tls", json={"cert": cert_pem, "key": key_pem, "enabled": True, "port": 8443})
    assert r.status_code == 200
    info = client.get("/api/settings/tls").get_json()
    assert info["has_cert"] is True
    assert "test.local" in info["cn"]
    client.post("/api/settings/tls/remove")
    assert client.get("/api/settings/tls").get_json()["has_cert"] is False


def test_onboarded_flag_roundtrip(client):
    """Das onboarded-Flag (Steuerung des Erststart-Assistenten) muss speicher-/lesbar sein."""
    st = client.get("/api/auth/status").get_json()
    if st["setup"]:
        client.post("/api/setup", json={"username": "admin", "password": "pw123456", "display_name": "A"})
    client.post("/api/login", json={"username": "admin", "password": "pw123456"})
    client.post("/api/settings", json={"onboarded": True})
    assert client.get("/api/settings").get_json()["onboarded"] is True
    client.post("/api/settings", json={"onboarded": False})
    assert client.get("/api/settings").get_json()["onboarded"] is False


def test_private_messages(client):
    """DM zwischen zwei Nutzern: senden, ungelesen-Zähler, als gelesen markieren."""
    st = client.get("/api/auth/status").get_json()
    if st["setup"]:
        client.post("/api/setup", json={"username": "admin", "password": "pw123456", "display_name": "A"})
    client.post("/api/login", json={"username": "admin", "password": "pw123456"})
    client.post("/api/users", json={"username": "bob", "password": "bobpass1", "role": "user", "perms": ["request"]})
    assert client.post("/api/messages", json={"to": "bob", "body": "hallo bob"}).status_code == 200
    assert client.post("/api/messages", json={"to": "admin", "body": "self"}).status_code == 400   # an sich selbst
    assert client.post("/api/messages", json={"to": "bob", "body": "   "}).status_code == 400        # leer
    client.post("/api/logout")
    client.post("/api/login", json={"username": "bob", "password": "bobpass1"})
    d = client.get("/api/messages").get_json()
    assert d["unread"] == 1
    assert any(m["body"] == "hallo bob" and m["from"] == "admin" for m in d["messages"])
    client.post("/api/messages/read", json={"from": "admin"})
    assert client.get("/api/messages").get_json()["unread"] == 0
    client.post("/api/logout")
    client.post("/api/login", json={"username": "admin", "password": "pw123456"})
    client.delete("/api/users/bob")


def test_request_on_behalf(client):
    """Admin darf eine Anfrage im Namen eines anderen Nutzers stellen (for_user)."""
    st = client.get("/api/auth/status").get_json()
    if st["setup"]:
        client.post("/api/setup", json={"username": "admin", "password": "pw123456", "display_name": "A"})
    client.post("/api/login", json={"username": "admin", "password": "pw123456"})
    client.post("/api/users", json={"username": "carol", "password": "carolpw1", "role": "user", "perms": ["request"]})
    r = client.post("/api/download", json={"title": "ZZ OnBehalf 55123", "source": "archive",
                                           "ref": "x", "platform_slug": "snes", "for_user": "carol"})
    assert r.status_code == 200 and r.get_json().get("ok")
    jid = r.get_json()["id"]
    j = next((x for x in client.get("/api/jobs").get_json() if x["id"] == jid), None)
    assert j and j["user"] == "carol"
    client.delete("/api/users/carol")


def test_protected_endpoint_requires_auth(client):
    # ohne Login liefert eine geschützte API 401 (nicht 200)
    r = client.get("/api/users")
    assert r.status_code in (401, 403)


def test_openapi_covers_all_routes(appmod):
    """Jede registrierte Route muss in der OpenAPI-Spec dokumentiert sein (Drift-Schutz)."""
    paths = appmod.OPENAPI["paths"]
    missing = []
    for rule in appmod.app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        p = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", rule.rule)
        if p not in paths:
            missing.append(p)
    assert not missing, f"nicht in OpenAPI dokumentiert: {sorted(set(missing))}"


def test_openapi_yaml_in_sync(appmod):
    """docs/openapi.yaml muss aus app.OPENAPI erzeugt sein (kein Drift)."""
    try:
        import yaml
    except ImportError:
        pytest.skip("pyyaml nicht verfügbar")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "docs", "openapi.yaml")
    if not os.path.exists(path):
        pytest.skip("docs/openapi.yaml fehlt")
    on_disk = yaml.safe_load(open(path))
    assert on_disk == appmod.OPENAPI, "docs/openapi.yaml veraltet — `python scripts/build_openapi.py` neu ausführen"


def test_openapi_served(client):
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    spec = r.get_json()
    assert spec["openapi"].startswith("3.")
    assert "/health" in spec["paths"]
    assert "securitySchemes" in spec["components"]


def test_inline_js_parses():
    """Jede ausgelieferte .js-Datei muss gültiges JavaScript sein.

    Früher lag das Skript in einem NICHT-rohen Python-String (PAGE); dort wurde jeder
    Backslash-Escape von Python interpretiert — aus join('\\n') wurde ein echter Umbruch
    und damit ein unterminiertes Literal, das das ganze Skript lahmlegte. Seit #73 sind
    es echte Dateien, in denen das nicht mehr passieren kann; geprüft wird trotzdem,
    weil ein Syntaxfehler im 120-kB-Frontend sonst erst im Browser auffällt.
    """
    node = shutil.which("node")
    if not node:
        pytest.skip("node nicht verfügbar")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    jsdir = os.path.join(root, "static", "js")
    files = sorted(f for f in os.listdir(jsdir) if f.endswith(".js"))
    assert files, "keine JS-Dateien unter static/js"
    for fn in files:
        r = subprocess.run([node, "--check", os.path.join(jsdir, fn)],
                           capture_output=True, text=True)
        assert r.returncode == 0, f"{fn}: {r.stderr.strip()}"


def test_no_frontend_left_in_python():
    """Kein HTML/CSS/JS mehr in app.py — das ist die eigentliche Zusage von #73. (#73)"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(root, "app.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    offenders = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            v = n.value
            if re.search(r"<(script|style)\b", v, re.I) or "<!doctype html" in v.lower():
                offenders.append(v[:60])
    assert not offenders, f"Frontend-Bruchstücke in app.py: {offenders}"


def test_assets_are_content_hashed_and_cacheable(appmod, client):
    """Gehashte URL + `immutable`; ein falscher Hash liefert NICHT dieselbe Datei. (#73)"""
    url = appmod.asset_url("js/index.js")
    assert url.startswith("/assets/") and url.endswith("/js/index.js")
    r = client.get(url)
    assert r.status_code == 200
    assert r.mimetype == "application/javascript"
    assert "immutable" in r.headers.get("Cache-Control", "")
    assert "max-age=31536000" in r.headers.get("Cache-Control", "")
    # Hash haengt am Inhalt
    assert appmod.asset_url("js/index.js") != appmod.asset_url("js/login.js")
    # falscher Hash -> 404, sonst waere `immutable` gelogen
    assert client.get("/assets/deadbeefcafe/js/index.js").status_code == 404
    assert client.get("/assets/%s/gibts/nicht.js" % url.split("/")[2]).status_code == 404


def test_pages_reference_external_assets_only(client):
    """Die ausgelieferten Seiten enthalten keine Inline-Blöcke mehr — damit wird eine CSP
    ohne `unsafe-inline` überhaupt erst möglich. (#73)"""
    for path in ("/login", "/reset"):
        html = client.get(path).get_data(as_text=True)
        assert "<style>" not in html and "__ASSET:" not in html
        assert re.search(r"<script(?![^>]*\bsrc=)", html) is None, f"Inline-Script in {path}"
        assert "/assets/" in html


def test_service_worker_served_at_root_without_long_cache(client):
    """Der Service-Worker muss unter / liegen (Geltungsbereich) und darf nicht
    festgenagelt werden. (#73)"""
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert b"addEventListener" in r.data
    assert "immutable" not in r.headers.get("Cache-Control", "")


def test_wishlist_roundtrip(appmod):
    """Wunschliste: Hinzufügen ist dedupliziert und per-Nutzer, Entfernen greift."""
    appmod.kv_put("wishlist", {})
    appmod.wishlist_add("alice", "Chrono Trigger", "snes")
    appmod.wishlist_add("alice", "Chrono Trigger", "snes")   # Dublette
    appmod.wishlist_add("bob", "Zelda", "")
    wl = appmod.load_wishlist()
    assert len(wl.get("alice", [])) == 1
    assert wl["alice"][0]["title"] == "Chrono Trigger"
    assert len(wl.get("bob", [])) == 1
    appmod.wishlist_remove("alice", "Chrono Trigger", "snes")
    assert appmod.load_wishlist().get("alice", []) == []
    appmod.kv_put("wishlist", {})   # aufräumen / cleanup


def test_design_setting_roundtrip(appmod, client):
    """Design-Auswahl: global (default_design) und pro Nutzer persistieren; ungültige Werte fallen zurück."""
    appmod.save_settings({"general": {"app_name": "Romseerr", "default_lang": "de", "default_design": "glass"}})
    assert appmod.load_settings()["general"]["default_design"] == "glass"
    # ungültiges Design -> Fallback (leer) beim Speichern über die Route
    appmod.save_users({"admin": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "admin"; sess["role"] = "admin"
    r = client.post("/api/profile", json={"design": "glass"})
    assert r.get_json()["ok"] is True
    assert appmod.load_users()["admin"]["design"] == "glass"
    client.post("/api/profile", json={"design": "bogus"})
    assert appmod.load_users()["admin"]["design"] == ""
    appmod.save_settings({}); appmod.save_users({})   # aufräumen / cleanup


def test_wishlist_title_matching():
    """Wunschlisten-Abgleich: alle Wörter des Wunschtitels müssen als Token vorkommen."""
    import importlib, app as _app
    assert _app.wishlist_title_matches("Chrono Trigger", "Chrono Trigger (USA)")
    assert _app.wishlist_title_matches("mario kart", "Super Mario Kart (Europe)")
    assert not _app.wishlist_title_matches("Mario", "Dr. Robotnik Machine")   # kein Treffer
    assert not _app.wishlist_title_matches("Zelda II", "The Legend of Zelda")  # 'ii' fehlt
    assert not _app.wishlist_title_matches("", "irgendwas")


def test_non_admin_cannot_escalate(appmod, client):
    """Ein manage_users-Nutzer (Rolle user) darf sich nicht zum Admin machen."""
    appmod.save_users({
        "boss": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)},
        "helper": {"pw": "x", "role": "user", "perms": ["request", "manage_users"]},
    })
    with client.session_transaction() as sess:
        sess["user"] = "helper"; sess["role"] = "user"
    # Rollenwechsel zu admin muss scheitern (403)
    r = client.patch("/api/users/helper", json={"role": "admin"})
    assert r.status_code == 403
    assert appmod.load_users()["helper"]["role"] == "user"
    # privilegierte Rechte dürfen nicht dazukommen
    client.patch("/api/users/helper", json={"perms": ["request", "manage_users", "manage_settings"]})
    assert "manage_settings" not in appmod.load_users()["helper"]["perms"]
    # bestehendes manage_users bleibt erhalten
    assert "manage_users" in appmod.load_users()["helper"]["perms"]
    appmod.save_users({})   # aufräumen / cleanup


def test_logs_bad_n_no_500(appmod, client):
    """/api/logs mit nicht-numerischem n darf nicht mit 500 crashen."""
    appmod.save_users({"a": {"pw": "x", "role": "admin"}})
    with client.session_transaction() as sess:
        sess["user"] = "a"; sess["role"] = "admin"
    assert client.get("/api/logs?n=abc").status_code == 200
    appmod.save_users({})


def test_jobs_visibility_per_user(appmod, client):
    """Ohne manage_requests sieht ein Nutzer nur die eigenen Anfragen; ein Manager alle."""
    appmod.save_users({
        "boss": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)},
        "lena": {"pw": "x", "role": "user", "perms": ["request"]},
    })
    with appmod.JOBS_LOCK:
        appmod.JOBS[:] = [
            {"id": "1", "title": "Boss Game", "user": "boss", "state": "queued", "source": "", "ref": "", "platform": "", "size": 0},
            {"id": "2", "title": "Lena Game", "user": "lena", "state": "queued", "source": "", "ref": "", "platform": "", "size": 0},
        ]
        appmod.save_jobs()
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    titles = [j["title"] for j in client.get("/api/jobs").get_json()]
    assert titles == ["Lena Game"]            # nur die eigene
    with client.session_transaction() as sess:
        sess["user"] = "boss"; sess["role"] = "admin"
    titles = sorted(j["title"] for j in client.get("/api/jobs").get_json())
    assert titles == ["Boss Game", "Lena Game"]   # Manager sieht alle
    with appmod.JOBS_LOCK:
        appmod.JOBS[:] = []; appmod.save_jobs()
    appmod.save_users({})


def _staging(appmod, jid, files):
    import os
    folder = os.path.join(appmod.STAGING, f"test_{jid}")
    os.makedirs(folder, exist_ok=True)
    for name, data in files.items():
        with open(os.path.join(folder, name), "wb") as f: f.write(data)
    return folder


def test_import_only_rom_extensions(appmod):
    """import_folder importiert nur bekannte ROM-Endungen; Nicht-ROM-Müll wird übersprungen. (#61)"""
    import os
    job = appmod.new_job({"title": "T1", "source": "archive", "ref": "r", "platform_slug": "gb", "size": 0},
                         user="", approved=False)
    jid = job["id"]
    folder = _staging(appmod, jid, {"game.gb": b"\x00" * 32, "junk.exe": b"MZ", "music.ogg": b"OggS"})
    appmod.import_folder(jid, folder)
    assert appmod.get_job(jid)["state"] == "done"
    found = [f for _, _, fs in os.walk(appmod.ROMS) for f in fs]
    assert "game.gb" in found
    assert "junk.exe" not in found and "music.ogg" not in found
    with appmod.JOBS_LOCK:
        appmod.JOBS[:] = [x for x in appmod.JOBS if x["id"] != jid]; appmod.save_jobs()


def test_import_all_junk_errors(appmod):
    """Enthält ein Item gar keine ROM, endet der Job als Fehler statt 'done'. (#61)"""
    job = appmod.new_job({"title": "T2", "source": "archive", "ref": "r", "platform_slug": "Mixed", "size": 0},
                         user="", approved=False)
    jid = job["id"]
    folder = _staging(appmod, jid, {"setup.exe": b"MZ", "lib.dll": b"MZ", "data.win": b"x"})
    appmod.import_folder(jid, folder)
    assert appmod.get_job(jid)["state"] == "error"
    with appmod.JOBS_LOCK:
        appmod.JOBS[:] = [x for x in appmod.JOBS if x["id"] != jid]; appmod.save_jobs()


def test_dl_name_and_find_output(appmod, tmp_path):
    """Download-Name traegt den Titel; find_output findet den Ordner ueber das jid-Praefix. (#64)"""
    import os
    jid = "1786095257002"
    assert appmod.dl_name(jid, "Super Mario Bros. 2 (Japan)").startswith(f"romseerr_{jid}__")
    assert appmod.dl_name(jid, "") == f"romseerr_{jid}"          # ohne Titel
    base = str(tmp_path)
    os.mkdir(os.path.join(base, f"romseerr_{jid}__Super.Mario"))  # mit Titel-Suffix
    os.mkdir(os.path.join(base, "romseerr_9999999999999"))         # fremder Job
    assert appmod.find_output(base, jid).endswith("__Super.Mario")
    # exakter Name ohne Titel
    base2 = str(tmp_path / "b2"); os.mkdir(base2); os.mkdir(os.path.join(base2, f"romseerr_{jid}"))
    assert appmod.find_output(base2, jid).endswith(f"romseerr_{jid}")
    # kein passender Ordner
    assert appmod.find_output(str(tmp_path / "nope"), jid) is None


def test_api_version_public(client, appmod):
    """/api/version ist ohne Anmeldung lesbar und meldet die Version aus version.txt (#76)."""
    r = client.get("/api/version")
    assert r.status_code == 200
    d = r.get_json()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert d["version"] == open(os.path.join(root, "version.txt")).read().strip()
    assert d["version"] != "0.0.0"           # version.txt wurde wirklich gelesen
    assert "commit" in d and "built_at" in d  # im Quell-Checkout None, aber vorhanden
    assert "latest" not in d                  # ohne ?check=1 kein Netzzugriff


def test_api_version_semver_compare(appmod):
    """Der Versionsvergleich für den Update-Hinweis ordnet numerisch, nicht lexikalisch."""
    assert appmod._semver("v1.10.0") > appmod._semver("1.9.9")
    assert appmod._semver("1.0.0-beta.1") == appmod._semver("1.0.0")   # Suffix ignoriert
    assert appmod._semver("krumm") == (0, 0, 0)


def test_metrics_requires_auth(client):
    """/metrics ist nicht öffentlich und antwortet einem Scraper mit 401, nicht mit einem
    Redirect auf /login (der als HTTP 200 mit HTML ankäme und wie Erfolg aussähe). (#74)"""
    client.post("/api/logout")
    r = client.get("/metrics")
    assert r.status_code == 401
    assert b"<html" not in r.data.lower()


def test_metrics_exposition(appmod, client):
    """Textformat, feste Zustandsreihe, Zähler und Worker-Herzschlag. (#74)"""
    appmod.save_users({"m": {"pw": "x", "role": "admin"}})
    appmod.beat("collect")
    appmod.count_import("success")
    appmod.count_import("failure", "no_rom_files")
    appmod.count_import("failure", "voellig frei erfunden")   # muss auf "other" fallen
    with client.session_transaction() as sess:
        sess["user"] = "m"; sess["role"] = "admin"
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.mimetype == "text/plain"
    body = r.get_data(as_text=True)
    for name in ("romseerr_requests", "romseerr_queue_depth", "romseerr_queue_oldest_age_seconds",
                 "romseerr_imports_total", "romseerr_wishlist_entries", "romseerr_library_titles",
                 "romseerr_worker_last_run_timestamp_seconds", "romseerr_build_info"):
        assert f"# TYPE {name} " in body, f"{name} fehlt"
    # jeder Job-Zustand hat eine Zeitreihe, auch wenn gerade 0 Jobs darin sind
    for st in appmod.JOB_STATES:
        assert f'romseerr_requests{{state="{st}"}}' in body
    # Wert nicht festnageln — andere Tests importieren ebenfalls; die Zeitreihe muss da sein
    assert re.search(r'romseerr_imports_total\{result="failure",reason="no_rom_files"\} \d+', body)
    assert 'reason="other"' in body               # unbekannter Grund wird gedeckelt
    assert 'reason="voellig frei erfunden"' not in body
    assert 'worker="collect"' in body
    assert f'version="{appmod.VERSION}"' in body
    # Kardinalität: kein Titel-/Nutzer-Label
    assert "title=" not in body and "user=" not in body
    appmod.save_users({})


def test_metrics_import_counter_single_outcome(appmod):
    """Ein Import erzeugt genau EINEN Zählerausschlag, nicht einen je Datei. (#74)"""
    before = sum(appmod.IMPORTS.values())
    job = appmod.new_job({"title": "M1", "source": "archive", "ref": "r", "platform_slug": "gb", "size": 0},
                         user="", approved=False)
    jid = job["id"]
    folder = _staging(appmod, jid, {"a.gb": b"\x01" * 32, "b.gb": b"\x02" * 32, "junk.exe": b"MZ"})
    appmod.import_folder(jid, folder)
    assert sum(appmod.IMPORTS.values()) == before + 1
    with appmod.JOBS_LOCK:
        appmod.JOBS[:] = [x for x in appmod.JOBS if x["id"] != jid]; appmod.save_jobs()


def test_wishlist_parse_lines(appmod):
    """Zerlegung: Kommentare raus, Semikolon/Tab trennen, Komma NUR vor echter Plattform. (#80)"""
    rows = appmod.parse_wishlist_text(
        "# Kommentar\n"
        "Chrono Trigger\n"
        "Super Metroid;snes\n"
        "Pokemon Crystal;Game Boy\n"
        "Metroid Fusion\tgba\n"
        "Castlevania,psx\n"
        "Sonic 3 & Knuckles, Collectors Edition\n"
        "   \n"
    )
    got = [(t, p) for t, p, _raw in rows]
    assert got == [
        ("Chrono Trigger", ""),
        ("Super Metroid", "snes"),
        ("Pokemon Crystal", "gb"),          # Anzeigename -> Slug
        ("Metroid Fusion", "gba"),
        ("Castlevania", "psx"),
        ("Sonic 3 & Knuckles, Collectors Edition", ""),   # Komma bleibt Teil des Titels
    ]


def test_wishlist_preview_writes_nothing(appmod, client):
    """Die Vorschau darf NICHTS schreiben — sie ist ein Prüfschritt, kein Abschicken. (#80)"""
    appmod.kv_put("wishlist", {})
    appmod.save_users({"imp": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "imp"; sess["role"] = "admin"
    r = client.post("/api/wishlist/import", json={"text": "Zzz Testspiel Eins\nZzz Testspiel Zwei;snes"})
    assert r.status_code == 200
    d = r.get_json()
    assert d["total"] == 2
    assert appmod.load_wishlist().get("imp", []) == []      # nichts geschrieben
    # ohne IGDB-Zugang wird NICHT "nicht gefunden" behauptet
    assert d["checked"] is False
    assert all(e["status"] == "unverified" for e in d["entries"])
    appmod.kv_put("wishlist", {}); appmod.save_users({})


def test_wishlist_import_confirm_and_dedup(appmod, client):
    """Bestätigter Import schreibt; derselbe Import zweimal erzeugt keine Dubletten. (#80)"""
    appmod.kv_put("wishlist", {})
    appmod.save_users({"imp": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "imp"; sess["role"] = "admin"
    body = {"confirm": True, "entries": [{"title": "Zzz Testspiel Eins", "platform": "snes"},
                                         {"title": "Zzz Testspiel Zwei", "platform": "snes"}]}
    d = client.post("/api/wishlist/import", json=body).get_json()
    assert d["added"] == 2 and d["skipped"] == 0
    d2 = client.post("/api/wishlist/import", json=body).get_json()
    assert d2["added"] == 0 and d2["skipped"] == 2
    assert len(appmod.load_wishlist()["imp"]) == 2
    appmod.kv_put("wishlist", {}); appmod.save_users({})


def test_wishlist_import_skips_library_titles(appmod, client):
    """Was schon in der Bibliothek liegt, landet nicht auf der Wunschliste. (#80)"""
    snes = os.path.join(appmod.ROMS, "snes")
    os.makedirs(snes, exist_ok=True)
    open(os.path.join(snes, "Chrono Trigger (USA).sfc"), "w").close()
    appmod.build_index()
    appmod.kv_put("wishlist", {})
    appmod.save_users({"imp": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "imp"; sess["role"] = "admin"
    d = client.post("/api/wishlist/import", json={"text": "Chrono Trigger;snes"}).get_json()
    assert d["entries"][0]["status"] == "in_library"
    r = client.post("/api/wishlist/import",
                    json={"confirm": True, "entries": [{"title": "Chrono Trigger", "platform": "snes"}]})
    assert r.get_json()["added"] == 0
    appmod.kv_put("wishlist", {}); appmod.save_users({})


def test_wishlist_import_size_cap_and_empty(appmod, client):
    """Größenbegrenzung mit lesbarer Meldung statt unbegrenzter Schleife. (#80)"""
    appmod.save_users({"imp": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "imp"; sess["role"] = "admin"
    assert client.post("/api/wishlist/import", json={"text": "   "}).status_code == 400
    assert client.post("/api/wishlist/import", json={"text": "x" * 200_001}).status_code == 413
    many = "\n".join(f"Spiel Nummer {i}" for i in range(appmod.WISH_IMPORT_MAX + 25))
    d = client.post("/api/wishlist/import", json={"text": many}).get_json()
    assert d["truncated"] is True
    assert d["total"] == appmod.WISH_IMPORT_MAX
    appmod.save_users({})


def test_wishlist_import_requires_permission(appmod, client):
    """Ohne `request`-Recht kein Import — dieselbe Regel wie beim Einzel-Hinzufügen. (#80)"""
    appmod.save_users({"nop": {"pw": "x", "role": "user", "perms": []}})
    with client.session_transaction() as sess:
        sess["user"] = "nop"; sess["role"] = "user"
    assert client.post("/api/wishlist/import", json={"text": "Chrono Trigger"}).status_code == 403
    appmod.save_users({})


def test_wishlist_example_file_is_importable(appmod, client):
    """Die angebotene Beispieldatei muss selbst ein gültiger Import sein. (#80)"""
    appmod.save_users({"imp": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "imp"; sess["role"] = "admin"
    r = client.get("/api/wishlist/example.csv")
    assert r.status_code == 200
    assert "attachment" in r.headers.get("Content-Disposition", "")
    rows = appmod.parse_wishlist_text(r.get_data(as_text=True))
    assert len(rows) >= 7
    titles = [t for t, _p, _r in rows]
    assert "Chrono Trigger" in titles
    assert ("Super Metroid", "snes") in [(t, p) for t, p, _r in rows]
    assert ("Pokemon Crystal", "gb") in [(t, p) for t, p, _r in rows]
    assert not any(t.startswith("#") for t in titles)     # keine Kommentarzeile als Titel
    appmod.save_users({})


def _admin(appmod, client, name="exp"):
    appmod.save_users({name: {"pw": "hash-des-kennworts", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = name; sess["role"] = "admin"


def test_export_omits_secrets_by_default(appmod, client):
    """Ein Export ist eine Datei, die herumgereicht wird — ohne Passphrase KEIN Klartext. (#75)"""
    appmod.save_settings({"apikey": "geheimer-api-key", "smtp": {"host": "mail.example", "pass": "smtp-geheim"},
                          "discord": {"enabled": True, "url": "https://discord.example/webhook/geheim"},
                          "connections": {"sab_url": "http://sab.example:8080", "sab_apikey": "sab-geheim"}})
    _admin(appmod, client)
    doc = client.get("/api/export").get_json()
    raw = json.dumps(doc)
    for secret in ("geheimer-api-key", "smtp-geheim", "sab-geheim", "discord.example/webhook/geheim",
                   "hash-des-kennworts"):
        assert secret not in raw, f"Geheimnis im Klartext exportiert: {secret}"
    assert doc["schema"] == appmod.EXPORT_SCHEMA
    assert doc["secrets"]["mode"] == "omitted"
    assert doc["settings"]["apikey"] == appmod.REDACTED
    assert doc["settings"]["connections"]["sab_url"] == "http://sab.example:8080"   # kein Geheimnis, bleibt lesbar
    appmod.save_settings({}); appmod.save_users({})


def test_export_import_roundtrip_encrypted(appmod, client):
    """Round-Trip mit Passphrase: exportieren, alles löschen, importieren, Zustand stimmt. (#75)"""
    pytest.importorskip("cryptography")
    appmod.save_settings({"apikey": "key-A", "general": {"app_name": "Vorher"},
                          "connections": {"sab_apikey": "sab-A"}})
    appmod.save_users({"boss": {"pw": "hash-A", "role": "admin", "perms": list(appmod.PERMS)},
                       "lena": {"pw": "hash-B", "role": "user", "perms": ["request"]}})
    appmod.kv_put("wishlist", {"lena": [{"title": "Zzz Wunsch", "platform": "snes", "added": 1}]})
    with client.session_transaction() as sess:
        sess["user"] = "boss"; sess["role"] = "admin"
    doc = client.post("/api/export", json={"secrets": "encrypt", "passphrase": "geheime-passphrase"}).get_json()
    assert doc["secrets"]["mode"] == "encrypted"
    assert "key-A" not in json.dumps(doc) and "hash-A" not in json.dumps(doc)

    # alles wegwerfen -> frischer Zustand
    appmod.save_settings({}); appmod.kv_put("wishlist", {})
    appmod.save_users({"tmp": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "tmp"; sess["role"] = "admin"
    r = client.post("/api/import", json={"document": doc, "mode": "replace",
                                         "passphrase": "geheime-passphrase"})
    assert r.status_code == 200, r.get_json()
    assert appmod.load_settings()["apikey"] == "key-A"
    assert appmod.load_settings()["connections"]["sab_apikey"] == "sab-A"
    assert appmod.load_settings()["general"]["app_name"] == "Vorher"
    users = appmod.load_users()
    assert set(users) == {"boss", "lena"} and users["boss"]["pw"] == "hash-A"
    assert appmod.load_wishlist()["lena"][0]["title"] == "Zzz Wunsch"
    appmod.save_settings({}); appmod.save_users({}); appmod.kv_put("wishlist", {})


def test_import_wrong_passphrase_rejected(appmod, client):
    """Falsche Passphrase -> klare Fehlermeldung, kein halb übernommener Zustand. (#75)"""
    pytest.importorskip("cryptography")
    appmod.save_settings({"apikey": "key-X"})
    _admin(appmod, client)
    doc = client.post("/api/export", json={"secrets": "encrypt", "passphrase": "richtige-passphrase"}).get_json()
    appmod.save_settings({"apikey": "unveraendert"})
    r = client.post("/api/import", json={"document": doc, "mode": "merge", "passphrase": "falsch-falsch"})
    assert r.status_code == 400
    assert "assphrase" in r.get_json()["msg"]
    assert appmod.load_settings()["apikey"] == "unveraendert"   # nichts angefasst
    appmod.save_settings({}); appmod.save_users({})


def test_import_rejects_unknown_or_newer_schema(appmod, client):
    """Unbekannte oder neuere Schema-Version wird mit klarer Meldung abgelehnt. (#75)"""
    _admin(appmod, client)
    newer = {"app": "romseerr", "schema": appmod.EXPORT_SCHEMA + 1, "settings": {}}
    r = client.post("/api/import", json={"document": newer, "mode": "merge"})
    assert r.status_code == 400 and "neuer" in r.get_json()["msg"]
    r = client.post("/api/import", json={"document": {"app": "romseerr"}, "mode": "merge"})
    assert r.status_code == 400
    r = client.post("/api/import", json={"document": {"app": "etwas-anderes", "schema": 1}, "mode": "merge"})
    assert r.status_code == 400
    appmod.save_users({})


def test_import_requires_explicit_mode(appmod, client):
    """`mode` muss der Aufrufer wählen — kein stiller Standard zwischen merge und replace. (#75)"""
    _admin(appmod, client)
    doc = client.get("/api/export").get_json()
    assert client.post("/api/import", json={"document": doc}).status_code == 400
    assert client.post("/api/import", json={"document": doc, "mode": "irgendwas"}).status_code == 400
    appmod.save_users({})


def test_import_keeps_existing_secrets(appmod, client):
    """REDACTED heißt „behalte, was da ist" — ein Export ohne Geheimnisse darf den
    laufenden API-Key nicht wegwischen, auch nicht im replace-Modus. (#75)"""
    appmod.save_settings({"apikey": "laufender-key", "general": {"app_name": "Alt"}})
    _admin(appmod, client)
    doc = client.get("/api/export").get_json()
    doc["settings"]["general"]["app_name"] = "Neu"
    r = client.post("/api/import", json={"document": doc, "mode": "replace"})
    assert r.status_code == 200
    assert appmod.load_settings()["apikey"] == "laufender-key"
    assert appmod.load_settings()["general"]["app_name"] == "Neu"
    appmod.save_settings({}); appmod.save_users({})


def test_import_refuses_to_lock_everyone_out(appmod, client):
    """Ein Import, der keinen Administrator mit Kennwort übrig ließe, wird abgelehnt. (#75)"""
    _admin(appmod, client)
    doc = {"app": "romseerr", "schema": appmod.EXPORT_SCHEMA,
           "users": {"nur_user": {"pw": "h", "role": "user", "perms": ["request"]}}}
    r = client.post("/api/import", json={"document": doc, "mode": "replace"})
    assert r.status_code == 400 and "dmin" in r.get_json()["msg"]
    assert "exp" in appmod.load_users()      # bestehender Admin unangetastet
    appmod.save_users({})


def test_export_import_admin_only(appmod, client):
    """Beide Richtungen nur für Admins. (#75)"""
    appmod.save_users({"lena": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    assert client.get("/api/export").status_code == 403
    assert client.post("/api/export", json={}).status_code == 403
    assert client.post("/api/import", json={"document": {}, "mode": "merge"}).status_code == 403
    appmod.save_users({})


def _seed_catalog(appmod, slug, names):
    """Katalog-Momentaufnahme direkt setzen — die Tests fassen IGDB nie an."""
    from contextlib import closing as _closing
    with appmod.DB_LOCK, _closing(appmod.db_conn()) as c, c:
        c.execute("DELETE FROM catalog WHERE slug=?", (slug,))
        c.executemany("INSERT INTO catalog(slug,norm,name) VALUES(?,?,?)",
                      [(slug, appmod.norm(n), n) for n in names])


def test_coverage_counts_and_missing(appmod, client):
    """Abdeckung = Katalog minus Bibliothek; die fehlenden Titel sind abrufbar. (#78)"""
    gba = os.path.join(appmod.ROMS, "gba")
    os.makedirs(gba, exist_ok=True)
    open(os.path.join(gba, "Metroid Fusion (USA).gba"), "w").close()
    open(os.path.join(gba, "Golden Sun (Europe).gba"), "w").close()
    appmod.build_index()
    _seed_catalog(appmod, "gba", ["Metroid Fusion", "Golden Sun", "Advance Wars", "Mario Kart Super Circuit"])
    appmod.refresh_coverage_counts()

    cov = {p["slug"]: p for p in appmod.coverage_overview()}
    assert cov["gba"]["known"] == 4
    assert cov["gba"]["owned"] == 2
    assert cov["gba"]["pct"] == 50.0
    assert cov["gba"]["source"] == appmod.CATALOG_SOURCE
    assert cov["gba"]["snapshot"]                      # jede Zahl nennt ihren Stand

    d = appmod.missing_titles("gba")
    assert d["total"] == 2
    assert sorted(d["titles"]) == ["Advance Wars", "Mario Kart Super Circuit"]
    # Filter + Pagination
    assert appmod.missing_titles("gba", q="Advance")["total"] == 1
    assert len(appmod.missing_titles("gba", offset=1, limit=1)["titles"]) == 1


def test_coverage_no_snapshot_is_not_zero_percent(appmod, client):
    """Ohne Momentaufnahme wird KEINE Prozentzahl behauptet — 0 % wäre die falscheste Zahl. (#78)"""
    _seed_catalog(appmod, "gba", ["Irgendwas"])
    appmod.refresh_coverage_counts()
    rows = {p["slug"]: p for p in appmod.coverage_overview()}
    assert rows["saturn"]["known"] is None and rows["saturn"]["pct"] is None
    assert rows["gba"]["known"] == 1


def test_coverage_endpoint_and_missing_route(appmod, client):
    """Die Routen liefern Zahlen samt Quelle/Stand und die paginierte Fehlliste. (#78)"""
    appmod.save_users({"c": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "c"; sess["role"] = "admin"
    _seed_catalog(appmod, "nes", ["Zzz Alpha", "Zzz Beta", "Zzz Gamma"])
    appmod.refresh_coverage_counts()
    d = client.get("/api/coverage").get_json()
    assert d["source"] == appmod.CATALOG_SOURCE
    nes = next(p for p in d["platforms"] if p["slug"] == "nes")
    assert nes["known"] == 3 and nes["snapshot"]
    m = client.get("/api/coverage/nes/missing?limit=2").get_json()
    assert m["total"] == 3 and len(m["titles"]) == 2
    assert m["source"] == appmod.CATALOG_SOURCE
    # krumme Parameter dürfen nicht mit 500 enden
    assert client.get("/api/coverage/nes/missing?offset=abc&limit=xyz").status_code == 200
    appmod.save_users({})


def test_coverage_refresh_needs_permission_and_source(appmod, client):
    """Katalogabruf nur mit manage_settings und nur mit konfigurierter Quelle. (#78)"""
    appmod.save_users({"lena": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    assert client.post("/api/coverage/refresh", json={}).status_code == 403
    appmod.save_users({"c": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "c"; sess["role"] = "admin"
    # Plattform ohne Katalogquelle -> klare Absage statt stiller Nulllauf
    assert client.post("/api/coverage/refresh", json={"slug": "gibtsnicht"}).status_code == 400
    # ohne IGDB-Zugang ebenfalls klare Absage
    assert client.post("/api/coverage/refresh", json={}).status_code == 400
    appmod.save_users({})


def _seed_ra(appmod, rows):
    """RA-Sets direkt setzen — die Tests fassen RetroAchievements nie an."""
    from contextlib import closing as _closing
    with appmod.DB_LOCK, _closing(appmod.db_conn()) as c, c:
        c.execute("DELETE FROM ra_games")
        c.executemany("INSERT INTO ra_games(slug,norm,ra_id,title,achievements,points) VALUES(?,?,?,?,?,?)",
                      [(s, appmod.norm(t), i, t, a, p) for s, t, i, a, p in rows])


def test_ra_lookup_exact_only(appmod):
    """Zuordnung nur bei exaktem normalisiertem Treffer — ein Fehlgriff wäre schlimmer
    als gar keine Angabe. Mehrdeutige Treffer werden verworfen. (#79)"""
    _seed_ra(appmod, [("snes", "Super Metroid", 100, 68, 550),
                      ("gba", "Metroid Fusion", 200, 60, 500),
                      ("nes", "Doppelgaenger Spiel", 300, 10, 50),
                      ("snes", "Doppelgaenger Spiel", 301, 12, 60)])
    hit = appmod.ra_lookup("Super Metroid (USA).sfc", "snes")
    assert hit and hit["id"] == 100 and hit["achievements"] == 68
    assert hit["url"] == "https://retroachievements.org/game/100"
    assert appmod.ra_lookup("Super Metroid", "gba") is None          # falsche Plattform
    assert appmod.ra_lookup("Super Metro", "snes") is None           # kein Fuzzy
    assert appmod.ra_lookup("Doppelgaenger Spiel") is None           # mehrdeutig -> nichts
    assert appmod.ra_lookup("Doppelgaenger Spiel", "nes")["id"] == 300
    assert appmod.ra_has_set("Metroid Fusion", "gba") is True
    _seed_ra(appmod, [])


def test_ra_absent_without_key_and_without_set(appmod, client):
    """Kein Key oder kein Set -> die Detailseite lässt den Abschnitt weg, ohne Fehler. (#79)"""
    _seed_ra(appmod, [])
    appmod.save_users({"r": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "r"; sess["role"] = "admin"
    d = client.get("/api/detail?title=Voellig+Unbekanntes+Spiel&source=&ref=").get_json()
    assert "achievements" not in d
    assert "error" not in d
    appmod.save_users({})


def test_ra_detail_shows_set(appmod, client):
    """Mit Set erscheint der Block samt Anzahl und Link. (#79)"""
    _seed_ra(appmod, [("snes", "Super Metroid", 100, 68, 550)])
    appmod.save_users({"r": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "r"; sess["role"] = "admin"
    d = client.get("/api/detail?title=Super+Metroid&platform=snes&source=&ref=").get_json()
    assert d["achievements"]["achievements"] == 68
    assert d["achievements"]["url"].endswith("/game/100")
    assert "progress" not in d["achievements"]      # ohne verknüpftes Konto kein Fortschritt
    _seed_ra(appmod, []); appmod.save_users({})


def test_ra_key_is_a_secret(appmod):
    """Der RA-Key gehört zu den maskierten Verbindungswerten und darf nie im Klartext
    im Export landen. (#79 + #75)"""
    assert "ra_key" in appmod.CONN_SECRET
    assert "ra_key" in appmod.CONN_KEYS
    appmod.save_settings({"connections": {"ra_key": "ra-geheim-xyz"}})
    assert "ra-geheim-xyz" not in json.dumps(appmod.build_export())
    appmod.save_settings({})


def test_ra_profile_account_roundtrip(appmod, client):
    """Das RA-Konto ist freiwillig und pro Nutzer speicherbar. (#79)"""
    appmod.save_users({"r": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "r"; sess["role"] = "admin"
    assert client.post("/api/profile", json={"ra_user": "Spieler123"}).get_json()["ok"] is True
    assert client.get("/api/profile").get_json()["ra_user"] == "Spieler123"
    appmod.save_users({})


def test_ra_refresh_requires_key_and_permission(appmod, client):
    """Ohne Key klare Absage, ohne manage_settings 403. (#79)"""
    appmod.save_settings({})
    appmod.save_users({"lena": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    assert client.post("/api/ra/refresh").status_code == 403
    appmod.save_users({"r": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "r"; sess["role"] = "admin"
    assert client.post("/api/ra/refresh").status_code == 400
    appmod.save_users({})


def test_ra_console_aliases_cover_platforms(appmod):
    """Jeder Alias-Slug muss eine echte Plattform sein — ein Tippfehler wäre sonst
    ein stiller Blindgänger. (#79)"""
    unknown = [s for s in appmod.RA_ALIASES if s not in appmod.SLUG_NAME]
    assert not unknown, f"RA_ALIASES kennt Slugs, die es nicht gibt: {unknown}"


def test_parse_release_conventions(appmod):
    """Region, Sprache, Revision und Dump-Status aus den üblichen Namenskonventionen. (#77)"""
    pr = appmod.parse_release

    v = pr("Chrono Trigger (USA).sfc")
    assert v["regions"] == ["USA"] and v["known"] is True

    v = pr("Super Mario World (Europe) (Rev 1).sfc")
    assert v["regions"] == ["Europe"] and v["revision"] == "Rev 1"

    v = pr("Terranigma (Germany) (En,De,Fr,Es).sfc")
    assert v["regions"] == ["Germany"]
    assert set(v["languages"]) == {"en", "de", "fr", "es"}

    # GoodTools: EIN Buchstabe ist Region, ZWEI sind Sprache — genau hier geht Raten schief
    assert pr("Zelda (E) [!].nes")["regions"] == ["Europe"]
    assert pr("Zelda (En).nes")["languages"] == ["en"]

    v = pr("Star Fox 2 (Japan) (Proto).sfc")
    assert v["dump"] == "prototype" and v["regions"] == ["Japan"]
    assert pr("Irgendwas (Beta).md")["dump"] == "beta"
    assert pr("Irgendwas (Demo).md")["dump"] == "demo"
    assert pr("Irgendwas (Unl).nes")["dump"] == "unlicensed"

    v = pr("Mother 3 (Japan) [T+Eng1.3].gba")
    assert v["dump"] in ("translation", "hack")

    # Mehrere Regionen in einem Tag
    assert pr("Spiel (USA, Europe).bin")["regions"] == ["USA", "Europe"]


def test_parse_release_never_invents(appmod):
    """Ein unlesbarer Name wird zu „unspezifiziert" — nie zu einem falschen Etikett. (#77)"""
    v = appmod.parse_release("irgendwas_kryptisches_2024.bin")
    assert v["regions"] == [] and v["languages"] == [] and v["revision"] == "" and v["dump"] == ""
    assert v["known"] is False
    assert appmod.variant_label(v) == ""
    assert appmod.parse_release("")["known"] is False


def test_variant_rank_follows_preference_not_a_ladder(appmod):
    """Die Reihenfolge der Regionen IST die Vorliebe — es wird nicht nach „Qualität" sortiert. (#77)"""
    pr, rank = appmod.parse_release, appmod.variant_rank
    prefs = {"regions": ["Japan", "USA"], "lang": "", "prerelease": False}
    jp, us, eu = pr("X (Japan).sfc"), pr("X (USA).sfc"), pr("X (Europe).sfc")
    assert rank(jp, prefs) < rank(us, prefs) < rank(eu, prefs)
    # umgekehrte Vorliebe kehrt die Reihenfolge um — keine feste Rangordnung im Code
    prefs2 = {"regions": ["USA", "Japan"], "lang": "", "prerelease": False}
    assert rank(us, prefs2) < rank(jp, prefs2)
    # Vorabfassungen hinten, solange nicht ausdrücklich gewollt
    beta = pr("X (Japan) (Beta).sfc")
    assert rank(jp, prefs) < rank(beta, prefs)
    prefs3 = {"regions": ["Japan"], "lang": "", "prerelease": True}
    assert rank(beta, prefs3) < rank(pr("X (Europe).sfc"), prefs3)
    # Sprachwunsch schlägt bei gleicher Region durch
    prefs4 = {"regions": ["Europe"], "lang": "de", "prerelease": False}
    assert rank(pr("X (Europe) (De).sfc"), prefs4) < rank(pr("X (Europe) (En).sfc"), prefs4)


def test_variant_prefs_layering(appmod):
    """Nutzer schlägt Instanz schlägt Standard; unsinnige Eingaben werden verworfen. (#77)"""
    appmod.save_settings({}); appmod.save_users({})
    assert appmod.variant_prefs()["regions"] == appmod.DEFAULT_VARIANT_PREFS["regions"]
    appmod.save_settings({"variant": {"regions": ["Japan"], "lang": "ja", "prerelease": False}})
    assert appmod.variant_prefs()["regions"] == ["Japan"]
    appmod.save_users({"u": {"pw": "x", "role": "user",
                             "variant": {"regions": ["USA"], "lang": "", "prerelease": True}}})
    p = appmod.variant_prefs("u")
    assert p["regions"] == ["USA"] and p["prerelease"] is True
    assert p["lang"] == "ja"      # nicht gesetzt -> Instanzwert bleibt stehen
    # Unsinn fällt raus, statt gespeichert zu werden
    san = appmod.sanitize_variant_prefs({"regions": ["Mordor", "USA"], "lang": "klingonisch", "prerelease": "ja"})
    assert san == {"regions": ["USA"], "lang": "", "prerelease": True}
    appmod.save_settings({}); appmod.save_users({})


def test_request_records_variant(appmod, client):
    """Die angefragte Fassung UND der Wunsch werden an der Anfrage festgehalten. (#77)"""
    appmod.save_users({"v": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "v"; sess["role"] = "admin"
    r = client.post("/api/download", json={"title": "Zzz Fassungstest (Europe) (Rev 1)",
                                           "source": "archive", "ref": "x", "platform_slug": "snes"})
    jid = r.get_json()["id"]
    job = appmod.get_job(jid)
    assert job["variant"]["regions"] == ["Europe"]
    assert job["variant"]["revision"] == "Rev 1"
    assert job["variant_label"].startswith("Europe")
    assert job["variant_wanted"]["regions"]          # was gewünscht war, ist belegt
    with appmod.JOBS_LOCK:
        appmod.JOBS[:] = [x for x in appmod.JOBS if x["id"] != jid]; appmod.save_jobs()
    appmod.save_users({})


def test_unparseable_release_is_still_requestable(appmod, client):
    """Ein nicht lesbarer Release-Name bleibt anfragbar und wird nicht etikettiert. (#77)"""
    appmod.save_users({"v": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "v"; sess["role"] = "admin"
    r = client.post("/api/download", json={"title": "zzz_kryptisch_9981", "source": "archive",
                                           "ref": "x", "platform_slug": "snes"})
    assert r.get_json()["ok"] is True
    job = appmod.get_job(r.get_json()["id"])
    assert job["variant"]["known"] is False
    assert job["variant_label"] == ""
    with appmod.JOBS_LOCK:
        appmod.JOBS[:] = [x for x in appmod.JOBS if x["id"] != job["id"]]; appmod.save_jobs()
    appmod.save_users({})


def test_long_hostile_titles_stay_fast(appmod):
    """Titel kommen aus fremden Indexern: viele unbalancierte Klammern dürfen die
    Klammer-Regexe nicht quadratisch werden lassen (CodeQL py/polynomial-redos)."""
    import time as _t
    evil = "(" * 40000 + "Spiel"
    t0 = _t.perf_counter()
    appmod.norm(evil); appmod.parse_release(evil); appmod.clean_query(evil)
    assert _t.perf_counter() - t0 < 1.0
    assert appmod.parse_release(evil)["known"] is False


def test_jd_check_distinguishes_missing_from_readonly(appmod, tmp_path):
    """„fehlt" und „nicht beschreibbar" sind verschiedene Fehler mit verschiedenen
    Lösungen — die Dienstanzeige muss sie auseinanderhalten. (#83)"""
    import os as _os
    watch = tmp_path / "watch"; out = tmp_path / "out"
    appmod.save_settings({"connections": {"jd_watch": str(watch), "jd_out": str(out)}})

    st = appmod.jd_check()
    assert st["ok"] is False and st["reason"] == "watch_missing"

    watch.mkdir()
    st = appmod.jd_check()
    assert st["ok"] is False and st["reason"] == "out_missing"   # Watch da, Ausgabe fehlt

    out.mkdir()
    assert appmod.jd_check()["ok"] is True

    if _os.getuid() != 0:      # als root ist alles beschreibbar, dann sagt der Fall nichts aus
        _os.chmod(watch, 0o555)
        try:
            st = appmod.jd_check()
            assert st["ok"] is False and st["reason"] == "watch_readonly"
            assert str(_os.getuid()) in st["info"]
        finally:
            _os.chmod(watch, 0o755)
    appmod.save_settings({})


def test_crawljob_failure_ends_the_job(appmod, tmp_path):
    """Ein fehlgeschlagener .crawljob-Schreibversuch muss den Job beenden, statt ihn für
    immer auf `downloading` stehen zu lassen. (#83)"""
    appmod.save_settings({"connections": {"jd_watch": str(tmp_path / "gibtsnicht"),
                                          "jd_out": str(tmp_path)}})
    with pytest.raises(RuntimeError) as e:
        appmod.write_crawljob("123", ["http://example.invalid/x"], "/output/x", "x")
    assert "nicht moeglich" in str(e.value) or "not possible" in str(e.value)
    appmod.save_settings({})


def test_crawljob_written_when_paths_are_good(appmod, tmp_path):
    """Bei brauchbaren Pfaden landet die Datei im konfigurierten Watch-Ordner. (#83)"""
    watch = tmp_path / "w"; watch.mkdir(); out = tmp_path / "o"; out.mkdir()
    appmod.save_settings({"connections": {"jd_watch": str(watch), "jd_out": str(out)}})
    appmod.write_crawljob("777", ["http://example.invalid/a", "http://example.invalid/b"],
                          "/output/romseerr/x", "romseerr_777__X")
    f = watch / "romseerr_777.crawljob"
    assert f.exists()
    d = json.loads(f.read_text())
    assert d[0]["packageName"] == "romseerr_777__X"
    assert d[0]["text"].count("\n") == 1          # beide Links, einer je Zeile
    appmod.save_settings({})


def test_jd_paths_are_configurable(appmod):
    """jd_watch/jd_out kommen aus den Einstellungen, mit den Konstanten als Default. (#83)"""
    appmod.save_settings({})
    assert appmod.jd_watch_dir() == appmod.JD_WATCH
    assert appmod.jd_out_dir() == appmod.JD_OUT
    appmod.save_settings({"connections": {"jd_watch": "/anderswo/watch", "jd_out": "/anderswo/out"}})
    assert appmod.jd_watch_dir() == "/anderswo/watch"
    assert appmod.jd_out_dir() == "/anderswo/out"
    assert "jd_watch" in appmod.CONN_KEYS and "jd_out" in appmod.CONN_KEYS
    assert "jd_watch" not in appmod.CONN_SECRET      # Pfade sind keine Geheimnisse
    appmod.save_settings({})


def test_jdownloader_appears_in_service_status(appmod, client, tmp_path):
    """JDownloader hat jetzt eine Zeile in der Dienstübersicht — vorher war er der einzige
    eingebundene Dienst ohne. (#83)"""
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    appmod.save_settings({"connections": {"jd_watch": str(tmp_path / "nix"), "jd_out": str(tmp_path)}})
    rows = client.get("/api/services/status").get_json()
    jd = next((r for r in rows if r["name"] == "JDownloader"), None)
    assert jd is not None, "keine JDownloader-Zeile"
    assert jd["ok"] is False and "nix" in jd["info"]
    appmod.save_settings({}); appmod.save_users({})


HYDRA_SAMPLE = {
    "name": "Beispielquelle",
    "downloads": [
        {"title": "Chrono Trigger (USA)", "uris": ["https://hoster.invalid/f/abc"],
         "uploadDate": "2026-01-02", "fileSize": "12 MB"},
        {"title": "Super Metroid (Europe)",
         "uris": ["https://cdn.invalid/files/supermetroid.zip"],
         "uploadDate": "2026-01-03", "fileSize": "3 MB"},
        {"title": "Nur Torrent", "uris": ["magnet:?xt=urn:btih:deadbeef"],
         "uploadDate": "2026-01-04", "fileSize": "1 MB"},
        {"title": "Ohne Links", "uris": [], "uploadDate": "", "fileSize": ""},
    ],
}


def test_catalog_urls_only_from_settings(appmod):
    """Die Quellen kommen ausschließlich aus der Konfiguration — im Repo steht keine. (#63)"""
    appmod.save_settings({})
    assert appmod.catalog_urls() == []
    assert appmod._ENV_CONN["catalog_urls"] == ""      # kein eingebauter Anbieter
    appmod.save_settings({"connections": {"catalog_urls":
        "https://a.invalid/s.json\nnicht-eine-url\n  https://b.invalid/s.json  "}})
    assert appmod.catalog_urls() == ["https://a.invalid/s.json", "https://b.invalid/s.json"]
    appmod.save_settings({})


def test_split_uris_routes_by_kind(appmod):
    """URIs sind gemischt: magnet -> nicht zuständig, direktes HTTP -> selbst laden,
    Filehoster -> JDownloader. (#63)"""
    direct, hoster, magnet = appmod.split_uris([
        "https://cdn.invalid/game.zip",
        "https://mega.nz/file/abc",
        "magnet:?xt=urn:btih:x",
        "https://1fichier.com/?abc",
    ])
    assert direct == ["https://cdn.invalid/game.zip"]
    assert "https://mega.nz/file/abc" in hoster and "https://1fichier.com/?abc" in hoster
    assert magnet == ["magnet:?xt=urn:btih:x"]


def test_catalog_parse_matches_hydra_schema(appmod, monkeypatch):
    """Parser gegen das belegte Katalog-JSON-Schema (Hydra-Validator v2.1.0):
    {name, downloads:[{title, uris[], uploadDate, fileSize}]} — alles Strings. (#63)"""
    class FakeResp:
        ok = True
        status_code = 200
        def json(self): return HYDRA_SAMPLE
    monkeypatch.setattr(appmod, "safe_get", lambda *a, **k: FakeResp())
    name, n = appmod.fetch_catalog_source("https://beispiel.invalid/s.json")
    assert name == "Beispielquelle"
    assert n == 3          # "Ohne Links" faellt raus, Magnet-Eintrag bleibt in der DB
    appmod.save_settings({"connections": {"catalog_urls": "https://beispiel.invalid/s.json"}})
    hits = appmod.search_filehoster("Chrono Trigger")
    assert len(hits) == 1
    assert hits[0]["source"] == "filehoster"          # genau das war vorher unerreichbar
    assert hits[0]["ref"] == "https://hoster.invalid/f/abc"
    assert "Beispielquelle" in hits[0]["extra"]
    # Ein Eintrag mit NUR Magnet erscheint nicht — dafuer ist dieser Zweig nicht zustaendig
    assert appmod.search_filehoster("Nur Torrent") == []
    appmod.save_settings({})


def test_catalog_rejects_foreign_json(appmod, monkeypatch):
    """Eine Quelle, die kein Katalog-JSON ist, muss klar scheitern statt still 0 zu liefern. (#63)"""
    class FakeResp:
        ok = True
        status_code = 200
        def json(self): return {"irgendwas": [1, 2, 3]}
    monkeypatch.setattr(appmod, "safe_get", lambda *a, **k: FakeResp())
    with pytest.raises(RuntimeError) as e:
        appmod.fetch_catalog_source("https://falsch.invalid/s.json")
    assert "Katalog-JSON" in str(e.value) or "catalogue" in str(e.value)


def test_catalog_status_reports_staleness_and_jd(appmod, client):
    """Der Stand je Quelle gehört sichtbar hin (Linkfäule), ebenso der JDownloader-Zustand. (#63)"""
    appmod.save_users({"c": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "c"; sess["role"] = "admin"
    appmod.save_settings({})
    d = client.get("/api/catalog/status").get_json()
    assert d["configured"] == 0
    assert "jd" in d and "ok" in d["jd"]
    assert client.post("/api/catalog/refresh").status_code == 400   # ohne Quelle klare Absage
    appmod.save_users({})


def test_filehoster_search_requires_all_tokens(appmod):
    """Mehrwort-Suche: alle Token müssen treffen, obwohl nur das erste in SQL steht. (#63)"""
    from contextlib import closing as _closing
    with appmod.DB_LOCK, _closing(appmod.db_conn()) as c, c:
        c.execute("DELETE FROM fh_items")
        c.executemany("INSERT INTO fh_items(norm,title,uris,size,uploaded,src,url) VALUES(?,?,?,?,?,?,?)",
                      [(appmod.norm(t), t, '["https://h.invalid/x"]', "1", "", "S", "u")
                       for t in ("Chrono Trigger (USA)", "Chrono Cross", "Super Metroid")])
    assert sorted(r["title"] for r in appmod.search_filehoster("Chrono")) == \
        ["Chrono Cross", "Chrono Trigger (USA)"]
    assert [r["title"] for r in appmod.search_filehoster("Chrono Trigger")] == ["Chrono Trigger (USA)"]
    assert appmod.search_filehoster("Chrono Zelda") == []
    with appmod.DB_LOCK, _closing(appmod.db_conn()) as c, c:
        c.execute("DELETE FROM fh_items")


def test_play_never_offered_for_platforms_without_a_core(appmod):
    """PS2, GameCube, Wii, Dreamcast und Switch haben keinen EmulatorJS-Kern und bekommen
    auch nie einen — der Play-Knopf darf dort NIEMALS erscheinen. (#69)"""
    appmod.save_settings({"connections": {"romm_url": "http://romm.invalid"}})
    for slug in ("ps2", "ngc", "wii", "wiiu", "switch", "dreamcast", "3ds", "ps3", "xbox360", "psvita"):
        d = appmod.play_info("Irgendein Spiel", slug)
        assert d["playable"] is False, f"{slug} darf nicht spielbar sein"
        assert d["reason"] == "no_core"
        assert slug not in appmod.PLAYABLE
    # und PSP ist umgekehrt sehr wohl dabei
    assert "psp" in appmod.PLAYABLE
    appmod.save_settings({})


def test_play_always_gives_a_reason(appmod, monkeypatch):
    """Jede Absage nennt ihren Grund — ein Knopf, der nichts tut, ist schlimmer als keiner. (#69)"""
    appmod.save_settings({})
    assert appmod.play_info("X", "snes")["reason"] == "no_romm"      # RomM gar nicht verbunden
    appmod.save_settings({"connections": {"romm_url": "http://romm.invalid"}})
    monkeypatch.setattr(appmod, "romm_find", lambda *a, **k: None)
    assert appmod.play_info("X", "snes")["reason"] == "not_in_library"
    monkeypatch.setattr(appmod, "romm_find",
                        lambda *a, **k: {"id": 5, "name": "X", "platform": "psx",
                                         "size": appmod.PLAY_MAX_BYTES + 1})
    d = appmod.play_info("X", "psx")
    assert d["playable"] is False and d["reason"] == "too_large"
    assert d["limit"] == appmod.PLAY_MAX_BYTES        # die Grenze steht in der Antwort
    appmod.save_settings({})


def test_play_url_points_at_romm_player(appmod, monkeypatch):
    """Aufgeloest wird auf RomMs eigene Spieler-Route /rom/<id>/ejs. (#69)"""
    appmod.save_settings({"connections": {"romm_url": "http://romm.invalid"}})
    monkeypatch.setattr(appmod, "romm_find",
                        lambda *a, **k: {"id": 42, "name": "Super Metroid",
                                         "platform": "snes", "size": 3 * 1024 * 1024})
    d = appmod.play_info("Super Metroid", "snes")
    assert d["playable"] is True
    assert d["url"] == "http://romm.invalid/rom/42/ejs"
    assert d["core"] == "snes9x"
    assert d["needs_bios"] is False
    # BIOS-Bedarf wird vorher gemeldet, nicht erst vor schwarzem Bildschirm
    monkeypatch.setattr(appmod, "romm_find",
                        lambda *a, **k: {"id": 7, "name": "Y", "platform": "psx", "size": 100})
    assert appmod.play_info("Y", "psx")["needs_bios"] is True
    assert appmod.play_info("Y", "psx")["playable"] is True
    appmod.save_settings({})


def test_play_endpoint_needs_request_permission(appmod, client):
    """Der Knopf folgt denselben Rechten wie der Download. (#69)"""
    appmod.save_users({"lena": {"pw": "x", "role": "user", "perms": []}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    assert client.get("/api/play?title=X").status_code == 403
    appmod.save_users({"max": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "max"; sess["role"] = "user"
    assert client.get("/api/play?title=X&platform=ps2").get_json()["reason"] in ("no_core", "no_romm")
    assert client.get("/api/play?title=").status_code == 400
    appmod.save_users({})


def test_url_allowed_refuses_internal_targets(appmod):
    """Ausgehende Anfragen an selbst gesetzte URLs: privat/Loopback/Link-Local nur mit
    ausdrücklicher Admin-Einstellung, andere Schemata nie. (#89)"""
    appmod.save_settings({})
    for bad, why in (("file:///etc/passwd", "scheme"), ("ftp://host/x", "scheme"),
                     ("gopher://host/x", "scheme"), ("nicht mal eine url", "scheme")):
        ok, reason = appmod.url_allowed(bad)
        assert ok is False and reason == why, bad
    for bad in ("http://127.0.0.1:8080/x", "http://localhost/x", "https://[::1]/x",
                "http://169.254.169.254/latest/meta-data/", "http://10.0.0.5/",
                "http://192.168.1.1/admin", "http://172.16.4.4/"):
        ok, reason = appmod.url_allowed(bad)
        assert ok is False and reason in ("private", "dns"), f"{bad} -> {reason}"
    # Ausdrückliche Freigabe (viele betreiben ihr Ziel im selben Netz)
    appmod.save_settings({"allow_private_webhooks": True})
    ok, _ = appmod.url_allowed("http://192.168.1.1/admin")
    assert ok is True
    # ... aber ein fremdes Schema bleibt auch dann verboten
    assert appmod.url_allowed("file:///etc/passwd")[0] is False
    appmod.save_settings({})


def test_safe_request_refuses_before_sending(appmod, monkeypatch):
    """Die Absage passiert VOR dem Absenden — es darf kein Paket rausgehen. (#89)"""
    appmod.save_settings({})
    called = []
    monkeypatch.setattr(appmod.requests, "request", lambda *a, **k: called.append(a) or None)
    with pytest.raises(PermissionError):
        appmod.safe_post("http://127.0.0.1:9/x", json={"a": 1})
    with pytest.raises(PermissionError):
        appmod.safe_post("file:///etc/passwd")
    assert called == [], "es wurde trotz Absage gesendet"


def test_safe_request_rechecks_redirects(appmod, monkeypatch):
    """Eine Umleitung auf ein internes Ziel muss ebenfalls scheitern — sonst genügt ein
    Redirect, um die Prüfung der Ausgangs-URL zu umgehen. (#89)"""
    appmod.save_settings({})
    monkeypatch.setattr(appmod, "url_allowed",
                        lambda u: (False, "private") if "127.0.0.1" in u else (True, ""))

    class Redirect:
        is_redirect = True
        headers = {"Location": "http://127.0.0.1:8080/intern"}
    monkeypatch.setattr(appmod.requests, "request", lambda *a, **k: Redirect())
    with pytest.raises(PermissionError):
        appmod.safe_post("https://extern.example/hook")


def test_errors_are_categories_not_exception_text(appmod):
    """Antworten tragen eine Fehlerart, keinen rohen Ausnahmetext (der verriete Pfade
    und Hostnamen). (#89)"""
    assert appmod.err_kind(appmod.requests.Timeout("verbindung zu /interner/pfad")) == "timeout"
    assert "erreichbar" in appmod.err_kind(appmod.requests.ConnectionError("host geheim.intern"))
    assert appmod.err_kind(ValueError("json kaputt bei /config/romseerr.db")).startswith("ungueltige")
    # Entscheidend: der Originaltext der Ausnahme taucht nirgends auf
    for txt in ("/interner/pfad", "geheim.intern", "/config/romseerr.db"):
        for e in (appmod.requests.Timeout(txt), appmod.requests.ConnectionError(txt), ValueError(txt)):
            assert txt not in appmod.err_kind(e)


def test_personal_webhook_test_blocks_internal_targets(appmod, client):
    """Der kritische Fall: ein GEWÖHNLICHER angemeldeter Nutzer darf den Server nicht
    auf interne Adressen schicken. (#89)"""
    appmod.save_settings({})
    appmod.save_users({"lena": {"pw": "x", "role": "user", "perms": ["request"],
                                "webhook": "http://127.0.0.1:8080/intern"}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    r = client.post("/api/profile/notify-test", json={"url": "http://127.0.0.1:8080/intern"})
    assert r.status_code == 400
    msg = r.get_json()["msg"]
    assert "privat" in msg.lower() or "private" in msg.lower()
    appmod.save_users({})


def test_no_exception_text_reaches_responses(appmod, client):
    """Kein Ausnahmetext in einer Antwort — die Meldungen sind bewusst geschriebene
    Nutzertexte, alles andere gehört ins Log. (#89)"""
    appmod.save_users({"a": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "a"; sess["role"] = "admin"
    # Import mit kaputtem Dokument: klare Meldung, aber keine Interna
    r = client.post("/api/import", json={"document": {"app": "romseerr", "schema": 999}, "mode": "merge"})
    assert r.status_code == 400
    msg = r.get_json()["msg"]
    assert "Schema 999" in msg                     # nützliche Auskunft bleibt
    assert "Traceback" not in msg and "/config" not in msg and "app.py" not in msg
    # TLS-Upload mit Unsinn: generische Meldung, keine Dateipfade
    r = client.post("/api/settings/tls", json={"cert": "kein pem", "key": "auch nicht"})
    assert r.status_code == 400
    m2 = r.get_json()["msg"]
    assert "/" not in m2.replace(" / ", "")        # kein Pfad (der Sprachtrenner zählt nicht)
    appmod.save_users({})


def _stream_ready(appmod, slug="ps2", name="Zzz Streamtitel.iso"):
    d = os.path.join(appmod.ROMS, slug)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, name), "w").close()
    appmod.build_index()
    appmod.save_settings({"connections": {"stream_url": "http://stream.example:3000/"}})


def test_stream_only_for_platforms_without_a_browser_core(appmod):
    """Der Stream-Knopf ergaenzt Play, er ersetzt ihn nicht: wo ein EmulatorJS-Kern
    existiert, gibt es keinen Stream. (#71)"""
    _stream_ready(appmod)
    appmod.kv_put("stream_session", None)
    for slug in ("snes", "psx", "gba", "n64"):
        assert appmod.stream_info("X", slug)["reason"] == "use_play", slug
    for slug in ("ps2", "ngc", "wii", "switch"):
        assert slug in appmod.STREAMABLE
        assert slug not in appmod.PLAYABLE       # sonst widersprechen sich #69 und #71
    assert appmod.stream_info("X", "amiga")["reason"] == "use_play"
    appmod.save_settings({})


def test_stream_requires_a_file_and_a_host(appmod):
    """Ohne Host kein Knopf, ohne Datei kein Stream. (#71)"""
    appmod.save_settings({})
    assert appmod.stream_info("Zzz Streamtitel", "ps2")["reason"] == "no_host"
    _stream_ready(appmod)
    assert appmod.stream_info("Gibt Es Nicht 9912", "ps2")["reason"] == "not_in_library"
    d = appmod.stream_info("Zzz Streamtitel", "ps2")
    assert d["streamable"] is True and d["path"].endswith("Zzz Streamtitel.iso")
    appmod.save_settings({})


def test_stream_is_single_seat(appmod, client):
    """Einzelplatz: die zweite Sitzung wird mit 409 und dem Namen des Belegers abgewiesen,
    nicht mit einem stillen Fehlschlag. (#71)"""
    _stream_ready(appmod)
    appmod.kv_put("stream_session", None)
    appmod.save_users({"anna": {"pw": "x", "role": "user", "perms": ["request"]},
                       "bert": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "anna"; sess["role"] = "user"
    r = client.post("/api/stream/start", json={"title": "Zzz Streamtitel", "platform": "ps2"})
    assert r.status_code == 200 and r.get_json()["streamable"] is True
    # derselbe Nutzer darf erneut starten
    assert client.post("/api/stream/start",
                       json={"title": "Zzz Streamtitel", "platform": "ps2"}).status_code == 200
    with client.session_transaction() as sess:
        sess["user"] = "bert"; sess["role"] = "user"
    r = client.post("/api/stream/start", json={"title": "Zzz Streamtitel", "platform": "ps2"})
    assert r.status_code == 409
    d = r.get_json()
    assert d["reason"] == "busy" and d["busy_user"] == "anna"
    # ... und darf sie nicht einfach abdrehen
    assert client.post("/api/stream/stop").status_code == 403
    with client.session_transaction() as sess:
        sess["user"] = "anna"; sess["role"] = "user"
    assert client.post("/api/stream/stop").get_json()["was_running"] is True
    assert appmod.stream_session() is None
    appmod.save_users({}); appmod.save_settings({})


def test_stream_session_expires(appmod):
    """Ein vergessener Tab darf den Einzelplatz nicht dauerhaft blockieren. (#71)"""
    appmod.kv_put("stream_session", {"user": "anna", "title": "X", "platform": "ps2",
                                     "started": 0, "expires": time.time() - 1})
    assert appmod.stream_session() is None      # abgelaufen -> Platz frei
    appmod.kv_put("stream_session", {"user": "anna", "title": "X", "platform": "ps2",
                                     "started": 0, "expires": time.time() + 600})
    assert appmod.stream_session()["user"] == "anna"
    appmod.kv_put("stream_session", None)


def test_stream_needs_permission(appmod, client):
    """Gleiche Rechte wie Download und Play. (#71)"""
    appmod.save_users({"lena": {"pw": "x", "role": "user", "perms": []}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    assert client.get("/api/stream?title=X").status_code == 403
    assert client.post("/api/stream/start", json={"title": "X"}).status_code == 403
    assert client.get("/api/stream/status").status_code == 403
    appmod.save_users({})


def test_stream_agent_refuses_paths_outside_the_library(appmod):
    """Der Start-Dienst darf ausschliesslich Dateien aus der Bibliothek starten —
    sonst waere er ein Fernstart fuer beliebige Dateien. (#71)"""
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "contrib", "streaming-host", "stream-agent.py")
    os.environ["STREAM_AGENT_TOKEN"] = "testtoken"
    os.environ["STREAM_ROMS"] = appmod.ROMS
    spec = importlib.util.spec_from_file_location("stream_agent", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Ohne konfigurierten Emulator lehnt der Dienst schon vorher ab — dann wuerde der
    # Test die PFADPRUEFUNG gar nicht erreichen und faelschlich gruen sein.
    mod.EMULATORS["ps2"] = "/bin/true %s"
    ok, msg = mod.launch("/etc/passwd", "ps2")
    assert ok is False and "ausserhalb" in msg
    ok, msg = mod.launch(os.path.join(appmod.ROMS, "gibt-es-nicht.iso"), "ps2")
    assert ok is False and "nicht gefunden" in msg
    ok, msg = mod.launch(os.path.join(appmod.ROMS, "x.iso"), "voellig-unbekannt")
    assert ok is False and "kein Emulator" in msg


def test_stream_find_file_validates_the_slug_itself(appmod):
    """Der Slug geht in einen Pfad. Er wird IN stream_find_file geprüft, nicht nur beim
    Aufrufer — sonst haengt die Sicherheit an der Reihenfolge der Pruefungen. (#71)"""
    appmod.save_settings({"connections": {"stream_url": "http://s.example/"}})
    for evil in ("../../etc", "..", "/etc", "ps2/../../etc"):
        assert appmod.stream_find_file("passwd", evil) is None, evil
    assert appmod.stream_find_file("X", "snes") is None      # nicht streambar -> kein Pfadzugriff
    appmod.save_settings({})


def test_no_private_infrastructure_details_in_repo():
    """Das Repo ist öffentlich. Keine Adressen, Hostnamen oder Anlagenpfade darin.

    Nicht als Mahnung gedacht, sondern als Bremse: so etwas rutscht beim Kopieren
    aus einer laufenden Installation mit, und GitHub zeigt den Bearbeitungsverlauf —
    nachträglich löschen hilft dann nicht mehr.

    Beispieladressen in Doku und Tests sind erlaubt, aber sie stehen NAMENTLICH
    unten. Eine neue Adresse aufzunehmen ist damit eine bewusste Entscheidung und
    kein Versehen — genau das ist der Zweck.
    """
    BEISPIELE = {
        "192.168.1.1", "192.168.1.10",   # Doku: „so sieht eine LAN-Adresse aus"
        "10.0.0.5", "172.16.4.4",        # SSRF-Tests: abzulehnende Ziele
        "127.0.0.1",
    }
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    muster = [
        (r"\b192\.168\.\d{1,3}\.\d{1,3}\b", "private IPv4 (192.168.x.x)"),
        (r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "private IPv4 (10.x.x.x)"),
        (r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b", "private IPv4 (172.16-31.x.x)"),
        # zusammengesetzt, sonst findet der Test sein eigenes Suchmuster
        ("/mnt" + "/user/", "NAS-Sharepfad einer konkreten Anlage"),
        (r"dns_[a-z0-9]+_api_token\s*=\s*[A-Za-z0-9_\-]{20,}", "echter API-Token"),
    ]
    erlaubt_dirs = {".git", "node_modules", "__pycache__", "data", ".pytest_cache", ".ruff_cache"}
    treffer = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in erlaubt_dirs]
        for fn in filenames:
            if fn.endswith((".png", ".jpg", ".jpeg", ".ico", ".pyc", ".gz", ".zip", ".svg")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                text = open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for pat, was in muster:
                for m in re.finditer(pat, text):
                    if m.group(0) in BEISPIELE:
                        continue
                    zeile = text[:m.start()].count("\n") + 1
                    treffer.append(f"{os.path.relpath(p, root)}:{zeile} {was}: {m.group(0)}")
    assert not treffer, ("Anlagendaten im oeffentlichen Repo gefunden:\n  "
                         + "\n  ".join(treffer)
                         + "\n\nEntweder entfernen, oder — wenn es wirklich ein Beispiel ist —"
                           " oben in BEISPIELE aufnehmen.")


def test_streamable_and_playable_stay_disjoint(appmod):
    """#69 und #71 duerfen sich nicht widersprechen: wo ein Browser-Kern existiert,
    gibt es keinen Stream-Knopf. Beim Nachruesten von Plattformen ist genau das die
    Stelle, an der man es kaputt macht. (#101)"""
    ueberschneidung = appmod.STREAMABLE & set(appmod.PLAYABLE)
    assert not ueberschneidung, f"Plattform in beiden Mengen: {ueberschneidung}"
    # die nachgeruesteten Plattformen sind wirklich drin
    for slug in ("xbox", "ps3", "psvita", "dreamcast", "3ds", "wiiu"):
        assert slug in appmod.STREAMABLE, slug


def test_emulator_endpoints_need_manage_settings(appmod, client):
    """Emulatoren aktualisieren und zuruecksetzen ist Administration. (#102)"""
    appmod.save_users({"lena": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    assert client.get("/api/stream/emulators").status_code == 403
    assert client.post("/api/stream/emulators/update").status_code == 403
    assert client.post("/api/stream/emulators/rollback", json={"name": "pcsx2"}).status_code == 403
    appmod.save_users({})


def test_rollback_name_is_validated(appmod, client):
    """Der Name geht in eine Argumentliste auf dem Streaming-Host — er wird hier
    geprueft und nicht erst dort. (#102)"""
    appmod.save_settings({"connections": {"stream_url": "http://s.example/",
                                          "stream_launch": "http://s.example:8901/launch?token=x"}})
    appmod.save_users({"a": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "a"; sess["role"] = "admin"
    for boes in ("../etc", "pcsx2; rm -rf /", "PCSX2", "", "a" * 40, "/absolut"):
        r = client.post("/api/stream/emulators/rollback", json={"name": boes})
        assert r.status_code == 400, f"durchgelassen: {boes!r}"
        assert r.get_json()["reason"] == "bad_name"
    appmod.save_settings({}); appmod.save_users({})


def test_content_policy_holds_for_this_repo():
    """Das Repository enthält nur Werkzeug — keine Inhalte, Firmware oder Schlüssel.

    Schnelles Signal beim Entwickeln. Die eigentliche Schranke ist der Workflow
    „Content policy", der dasselbe Skript aus dem HAUPTZWEIG holt — ein Beitrag
    kann seine eigene Prüfung damit nicht aufweichen. (#108)
    """
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pfad = os.path.join(root, "scripts", "check_content_policy.py")
    spec = importlib.util.spec_from_file_location("content_policy", pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Wurzel ausdruecklich uebergeben: pytest kann aus jedem Verzeichnis laufen.
    assert mod.main([], root=root) == 0, "siehe Ausgabe oben / see output above"


def test_content_policy_actually_catches_things(tmp_path):
    """Ein Prüfer, der nie anschlägt, beweist nichts. Hier wird er zum Anschlagen
    gebracht — je Fundart einmal, und einmal etwas Erlaubtes zur Gegenprobe. (#108)"""
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "content_policy2", os.path.join(root, "scripts", "check_content_policy.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    d = str(tmp_path)
    (tmp_path / "spiel.iso").write_bytes(b"x")
    (tmp_path / "scph39001.bin").write_bytes(b"x")
    (tmp_path / "prod.keys").write_text("x")
    (tmp_path / "gross.bin").write_bytes(b"\0" * (mod.MAX_BYTES + 1))
    # Zusammengesetzt, sonst meldet der Pruefer diese Datei selbst — die Beispiele
    # SIND ja genau das, wonach er sucht. / Assembled, or the checker flags this file.
    boese_host = "https://beispiel-" + "roms.example.net/pack.zip"
    boese_datei = "https://cdn.beispiel.example/d/spiel." + "iso"
    (tmp_path / "quelle.md").write_text("hol es bei " + boese_host)
    (tmp_path / "direkt.md").write_text(boese_datei)
    # Gegenprobe: offizielle Projektquelle und ein interner Dienstname sind erlaubt
    (tmp_path / "sauber.md").write_text(
        "https://api.github.com/repos/x/y/releases und http://sabnzbd:8080/api")

    for name in ("spiel.iso", "scph39001.bin", "prod.keys", "gross.bin",
                 "quelle.md", "direkt.md"):
        assert mod.check_file(d, name), f"nicht erkannt / not caught: {name}"
    assert mod.check_file(d, "sauber.md") == [], "Fehlalarm auf erlaubter Adresse"


def test_emulator_catalog_endpoints_need_manage_settings(appmod, client):
    """Katalog und Installation sind Administration. (#106)"""
    appmod.save_users({"lena": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    assert client.get("/api/stream/emulators/catalog").status_code == 403
    assert client.post("/api/stream/emulators/install", json={"name": "pcsx2"}).status_code == 403
    appmod.save_users({})


def test_install_name_is_validated(appmod, client):
    """Der Name geht in eine Argumentliste auf dem Streaming-Host. (#106)"""
    appmod.save_settings({"connections": {"stream_url": "http://s.example/",
                                          "stream_launch": "http://s.example:8901/launch?token=x"}})
    appmod.save_users({"a": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "a"; sess["role"] = "admin"
    for boes in ("../etc", "pcsx2; rm -rf /", "PCSX2", "", "/absolut", "a" * 40):
        r = client.post("/api/stream/emulators/install", json={"name": boes})
        assert r.status_code == 400 and r.get_json()["reason"] == "bad_name", f"durchgelassen: {boes!r}"
    appmod.save_settings({}); appmod.save_users({})


def test_agent_url_derivation(appmod):
    """Aus der /launch-Adresse samt Token werden die uebrigen Endpunkte abgeleitet —
    der Betreiber soll nicht vier URLs eintragen muessen. (#106)"""
    appmod.save_settings({"connections": {"stream_launch": "http://h:8901/launch?token=geheim"}})
    assert appmod._agent_url("catalog") == "http://h:8901/catalog?token=geheim"
    assert appmod._agent_url("install") == "http://h:8901/install?token=geheim"
    appmod.save_settings({"connections": {"stream_launch": "http://h:8901/launch"}})
    assert appmod._agent_url("catalog") == "http://h:8901/catalog"
    appmod.save_settings({})
    assert appmod._agent_url("catalog") is None


# --------------------------------------------------------------- Zweigmodell (#111)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _workflow(name):
    import yaml
    p = os.path.join(REPO, ".github", "workflows", name)
    # "on:" ist in YAML 1.1 der Wahrheitswert True — deshalb nicht nach "on" suchen.
    return yaml.safe_load(open(p, encoding="utf-8"))


def test_release_runs_on_dev_and_only_fast_forwards_main():
    """`main` ist ein Zeiger auf den Release, kein Arbeitszweig. Der Release-Lauf darf
    ihn nur VORSPULEN — ein --force hier wuerde genau die Garantie aufheben, wegen der
    das Modell ueberhaupt gebaut wurde. (#111)"""
    wf = _workflow("release-please.yml")
    assert wf[True]["push"]["branches"] == ["dev"], "Release-Bot muss auf dev hoeren"
    rp = wf["jobs"]["release-please"]["steps"][0]
    assert rp["with"]["target-branch"] == "dev"
    text = open(os.path.join(REPO, ".github/workflows/release-please.yml"), encoding="utf-8").read()
    assert "--is-ancestor" in text, "Vorspulen muss geprueft werden, nicht angenommen"
    assert "push --force" not in text and "-f origin" not in text and "+refs/" not in text, \
        "main darf niemals erzwungen ueberschrieben werden"


def test_ci_also_guards_main():
    """Der Release-Commit wird auf dev geprueft — aber main soll eigene gruene Laeufe
    haben, sonst steht der ausgelieferte Zweig ohne Nachweis da. (#111)"""
    for name in ("ci.yml", "security.yml", "content-policy.yml"):
        branches = _workflow(name)[True]["push"]["branches"]
        assert "dev" in branches and "main" in branches, f"{name}: {branches}"


def test_content_policy_checker_comes_from_the_target_branch():
    """Nie aus dem PR selbst — sonst senkt ein Beitrag seine eigene Schranke. Und nicht
    aus dem Standardzweig, sonst pruefte ein Release-PR nach der falschen Regel. (#111)"""
    text = open(os.path.join(REPO, ".github/workflows/content-policy.yml"), encoding="utf-8").read()
    assert "github.base_ref || github.ref_name" in text
    assert "github.event.repository.default_branch" not in text


def test_version_manifest_matches_the_last_release():
    """Die Version kam aus version.txt und war 0.1.0, waehrend v1.0.0-beta.1 veroeffentlicht
    war — /api/version log damit seit dem Beta-Release. Das Manifest ist jetzt die
    Wahrheit; version.txt auf dev traegt nur eine Entwicklungsmarke. (#111)"""
    import json
    manifest = json.load(open(os.path.join(REPO, ".release-please-manifest.json")))
    assert list(manifest) == ["."] and manifest["."], manifest
    dev_version = open(os.path.join(REPO, "version.txt"), encoding="utf-8").read().strip()
    assert dev_version.endswith("-dev"), \
        f"version.txt auf dev muss als Entwicklungsstand erkennbar sein, ist {dev_version!r}"


def test_release_tags_stay_continuous():
    """Mit einem Komponentennamen taggt release-please `romseerr-v1.2.3` statt `v1.2.3`.
    Das bricht die Reihe ab v1.0.0-beta.1 — und damit den dokumentierten Weg, einen
    Versionszweig rueckwirkend aus einem Tag zu schneiden. (#111)"""
    import json
    cfg = json.load(open(os.path.join(REPO, "release-please-config.json")))
    root = cfg["packages"]["."]
    assert "package-name" not in root, "package-name erzeugt Tags mit Praefix"
    assert root.get("include-component-in-tag") is False
