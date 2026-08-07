"""Smoke-Tests / smoke tests für Romseerr.

Prüfen Verhalten (nicht nur Syntax): Health, Titel-Normalisierung/Dedup, Bibliotheks-Index,
Sperrliste, Setup-/Login-Fluss und dass das eingebettete JavaScript gültig ist.
"""
import ast
import os
import re
import shutil
import subprocess
import tempfile

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
    """Der interpretierte PAGE/LOGIN/RESET-JS-Block muss gültiges JavaScript sein.

    Guard gegen die Klasse Fehler, bei der ein Backslash-Escape im nicht-rohen
    Python-String (z. B. join('\\n')) zu echtem Zeilenumbruch wird und das gesamte
    Inline-Skript zerbricht. `python -m py_compile` fängt das NICHT.
    """
    node = shutil.which("node")
    if not node:
        pytest.skip("node nicht verfügbar")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tree = ast.parse(open(os.path.join(root, "app.py")).read())
    checked = 0
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str) and n.targets
                and isinstance(n.targets[0], ast.Name)):
            continue
        if n.targets[0].id not in ("PAGE", "LOGIN_PAGE", "RESET_PAGE"):
            continue
        m = re.search(r"<script>([\s\S]*?)</script>", n.value.value)
        if not m:
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(m.group(1))
            path = f.name
        try:
            r = subprocess.run([node, "--check", path], capture_output=True, text=True)
            assert r.returncode == 0, f"{n.targets[0].id}: {r.stderr.strip()}"
        finally:
            os.unlink(path)
        checked += 1
    assert checked >= 1, "kein <script>-Block gefunden"


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
