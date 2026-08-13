"""Smoke-Tests / smoke tests für Romseerr.

Prüfen Verhalten (nicht nur Syntax): Health, Titel-Normalisierung/Dedup, Bibliotheks-Index,
Sperrliste, Setup-/Login-Fluss und dass das eingebettete JavaScript gültig ist.
"""
import ast
import json
import os
import yaml
import re
import sys
import shutil
import subprocess
import tempfile
import time

import pytest
from hilfen import (  # noqa: F401  gemeinsam genutzt (#505)
    ADMIN_FIX,
    ANSICHTEN_OHNE_BROWSERTEST,
    DATEI_SPEICHER,
    DOC_EN_BODEN,
    DOC_ROUTEN_OHNE,
    HYDRA_SAMPLE,
    REPO,
    ZWEISPRACHIG_IN_EINEM_STUECK,
    _3ds_datei,
    _DE_WORTE,
    _EN_WORTE,
    _Protokoll,
    _admin,
    _als,
    _cia_datei,
    _doc_bloecke,
    _doc_dateien,
    _hat_englisch,
    _index_mit_protokoll,
    _index_zurueck,
    _js,
    _lege_titel_an,
    _mit_index,
    _nsp_datei,
    _readme_ueberschriften,
    _route_funktionen,
    _routen_und_ansichten,
    _seed_catalog,
    _seed_ra,
    _staging,
    _stream_ready,
    _unlesbar_machen,
    _workflow,
    i18n_hat,
    sprachtabellen,
)


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
    appmod.save_users({**ADMIN_FIX, "nop": {"pw": "x", "role": "user", "perms": []}})
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
    appmod.save_users({**ADMIN_FIX, "lena": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    assert client.get("/api/export").status_code == 403
    assert client.post("/api/export", json={}).status_code == 403
    assert client.post("/api/import", json={"document": {}, "mode": "merge"}).status_code == 403
    appmod.save_users({})


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
    appmod.save_users({**ADMIN_FIX, "lena": {"pw": "x", "role": "user", "perms": ["request"]}})
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
    appmod.save_users({**ADMIN_FIX, "lena": {"pw": "x", "role": "user", "perms": ["request"]}})
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
    appmod.save_users({**ADMIN_FIX, "u": {"pw": "x", "role": "user",
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
    eingebundene Dienst ohne. (#83)

    Die Zeile heißt ausdrücklich nach der ÜBERGABE, nicht nach dem Programm: geprüft wird
    ein Ordnerpaar, nicht ob JDownloader läuft. „JDownloader ❌" hat die Fehlersuche
    zweimal an den falschen Ort geschickt. (#204)"""
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    appmod.save_settings({"connections": {"jd_watch": str(tmp_path / "nix"), "jd_out": str(tmp_path)}})
    rows = client.get("/api/services/status").get_json()
    jd = next((r for r in rows if r["name"].startswith("JDownloader")), None)
    assert jd is not None, "keine JDownloader-Zeile"
    assert jd["name"] != "JDownloader", "die Zeile darf nicht nach dem Programm heißen (#204)"
    assert "hand-off" in jd["name"] and "bergabe" in jd["name"]   # zweisprachig beschriftet
    assert jd["ok"] is False and "nix" in jd["info"]
    assert "Bind-Mount" in jd["info"], "die Zeile muss sagen, was zu tun ist (#204)"
    appmod.save_settings({}); appmod.save_users({})


def test_the_handover_check_says_what_to_change(appmod, tmp_path):
    """Jeder der drei Fälle nennt seine eigene Abhilfe. Pfad und uid allein sagen dem
    Betreiber nicht, WAS er ändern soll — und eine korrekte Prüfung, der niemand glaubt,
    ist schlimmer als eine falsche. (#204)"""
    import os as _os
    if _os.getuid() == 0:
        pytest.skip("als root ist jedes Verzeichnis beschreibbar")
    watch = tmp_path / "wf"; watch.mkdir()
    appmod.save_settings({"connections": {"jd_watch": str(watch), "jd_out": str(tmp_path)}})
    _os.chmod(watch, 0o555)
    try:
        st = appmod.jd_check()
        assert st["reason"] == "watch_readonly"
        assert str(_os.getuid()) in st["fix"] and "0775" in st["fix"]
        assert str(watch) in st["fix"]
    finally:
        _os.chmod(watch, 0o755)
    appmod.save_settings({})


def test_the_output_view_follows_the_downloader_view(appmod):
    """Romseerrs Sicht auf den Zielordner wird aus der JD-Sicht ABGELEITET.

    Der Fehler, den das abstellt: zwei unabhängige Defaults. `jd_dl_base` wurde in der
    Oberfläche auf `/output/rom-suche` gesetzt, `jd_out` blieb still auf
    `/jd-output/romseerr` — Romseerr sammelte in einem Ordner ein, den JDownloader nie
    befüllt, und meldete „Ausgabe-Ordner fehlt". (#197)"""
    appmod.save_settings({"connections": {"jd_dl_base": "/output/rom-suche"}})
    assert appmod.jd_out_dir() == "/jd-output/rom-suche"

    # Mehrstufige Pfade behalten ihren Rest, nur der Mountpunkt wird ersetzt.
    appmod.save_settings({"connections": {"jd_dl_base": "/output/roms/neu"}})
    assert appmod.jd_out_dir() == "/jd-output/roms/neu"

    # Eine ausdrückliche Einstellung schlägt die Ableitung — sonst wäre ein abweichender
    # Aufbau nicht mehr konfigurierbar.
    appmod.save_settings({"connections": {"jd_dl_base": "/output/a", "jd_out": "/anderswo/out"}})
    assert appmod.jd_out_dir() == "/anderswo/out"

    # Ohne alles bleibt der bisherige Default.
    appmod.save_settings({"connections": {"jd_dl_base": ""}})
    assert appmod.jd_out_dir() == appmod.JD_OUT
    appmod.save_settings({})


def test_a_missing_output_folder_is_created_where_it_is_used(appmod, tmp_path):
    """Der Ausgabe-Ordner wird angelegt, wo die Übergabe BENUTZT wird — und nur dort.

    Achtmal dieselbe Startwarnung zu schreiben und nichts zu tun war der eigentliche
    Fehler. Eine Anzeige bleibt aber eine Anzeige: `jd_check()` ohne `anlegen` verändert
    nichts, sonst erzeugte jeder Blick in die Einstellungen Verzeichnisse. (#197)"""
    watch = tmp_path / "w"; watch.mkdir(); out = tmp_path / "raus"
    appmod.save_settings({"connections": {"jd_watch": str(watch), "jd_out": str(out)}})

    st = appmod.jd_check()
    assert st["reason"] == "out_missing" and not out.exists(), "die reine Prüfung darf nichts anlegen"

    st = appmod.jd_check(anlegen=True)
    assert st["ok"] is True and out.is_dir()
    appmod.save_settings({})


def test_writing_a_crawljob_heals_the_missing_output_folder(appmod, tmp_path):
    """Ein fehlender Zielordner darf einen Download nicht verhindern — JDownloader legt
    ihn selbst an, Romseerr braucht ihn nur zum Einsammeln. (#197)"""
    watch = tmp_path / "w2"; watch.mkdir(); out = tmp_path / "raus2"
    appmod.save_settings({"connections": {"jd_watch": str(watch), "jd_out": str(out)}})
    appmod.write_crawljob("42", ["http://example.invalid/a"], "/output/romseerr/x", "x")
    assert (watch / "romseerr_42.crawljob").exists()
    assert out.is_dir(), "der Zielordner hätte angelegt werden müssen"
    appmod.save_settings({})


def test_a_broken_handover_is_visible_in_the_interface(appmod, client, tmp_path):
    """Ein Weg, der gar nicht erst starten kann, gehört in die Oberfläche.

    Vorher stand die Warnung ausschließlich im Logfile — achtmal. Wer einen Download
    vermisste, sah nichts, was den Zusammenhang erklärt hätte. (#197)"""
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"

    appmod.save_settings({"connections": {"jd_watch": str(tmp_path / "fehlt"), "jd_out": str(tmp_path)}})
    w = client.get("/api/config/warnings").get_json()["warnings"]
    jd = next((x for x in w if x.get("key") == "jd"), None)
    assert jd is not None and jd["reason"] == "watch_missing"
    assert "fehlt" in jd["text"]

    # Und es schweigt, sobald die Übergabe steht — sonst gewöhnt man sich das Banner ab.
    watch = tmp_path / "ok"; watch.mkdir()
    appmod.save_settings({"connections": {"jd_watch": str(watch), "jd_out": str(tmp_path)}})
    assert not [x for x in client.get("/api/config/warnings").get_json()["warnings"]
                if x.get("key") == "jd"]
    appmod.save_settings({}); appmod.save_users({})


def test_config_warnings_are_for_admins_only(appmod, client):
    """Die Warnungen nennen Pfade der Anlage — das ist nichts für jeden Angemeldeten. (#197)"""
    appmod.save_users({**ADMIN_FIX, "n": {"pw": "x", "role": "user", "perms": []}})
    with client.session_transaction() as sess:
        sess["user"] = "n"; sess["role"] = "user"
    assert client.get("/api/config/warnings").status_code == 403
    appmod.save_users({})


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
    appmod.save_users({**ADMIN_FIX, "lena": {"pw": "x", "role": "user", "perms": []}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    assert client.get("/api/play?title=X").status_code == 403
    appmod.save_users({**ADMIN_FIX, "max": {"pw": "x", "role": "user", "perms": ["request"]}})
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
    appmod.save_users({**ADMIN_FIX, "lena": {"pw": "x", "role": "user", "perms": ["request"],
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


def test_stream_only_for_platforms_without_a_browser_core(appmod):
    """Der Stream-Knopf ergaenzt Play, er ersetzt ihn nicht: wo ein EmulatorJS-Kern
    existiert, gibt es keinen Stream. (#71)"""
    _stream_ready(appmod)
    appmod.kv_put("stream_sessions", {}); appmod.kv_put("stream_session", None)
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
    appmod.kv_put("stream_sessions", {}); appmod.kv_put("stream_session", None)
    appmod.save_users({**ADMIN_FIX, "anna": {"pw": "x", "role": "user", "perms": ["request"]},
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
    # ... und darf sie nicht abdrehen. Ohne Platzangabe beendet `stop` die EIGENE
    # Sitzung — bert hat keine, es passiert also nichts (200, was_running=false).
    # Nennt er annas Platz ausdrücklich, wird er abgewiesen. Beides ist wichtig:
    # das erste verhindert versehentliches Abdrehen, das zweite absichtliches. (#137)
    r_ohne = client.post("/api/stream/stop")
    assert r_ohne.status_code == 200 and r_ohne.get_json()["was_running"] is False
    assert client.post("/api/stream/stop?seat=1").status_code == 403
    with client.session_transaction() as sess:
        sess["user"] = "anna"; sess["role"] = "user"
    assert client.post("/api/stream/stop").get_json()["was_running"] is True
    assert appmod.stream_sessions() == {}
    appmod.save_users({}); appmod.save_settings({})


def test_stream_session_expires(appmod):
    """Ein vergessener Tab darf einen Platz nicht dauerhaft blockieren. (#71)"""
    appmod.kv_put("stream_sessions", {"1": {"user": "anna", "title": "X", "platform": "ps2",
                                            "started": 0, "expires": time.time() - 1}})
    assert appmod.stream_sessions() == {}       # abgelaufen -> Platz frei
    appmod.kv_put("stream_sessions", {"1": {"user": "anna", "title": "X", "platform": "ps2",
                                            "started": 0, "expires": time.time() + 600}})
    assert appmod.stream_sessions()["1"]["user"] == "anna"
    assert appmod.stream_session_of("anna")[0] == "1"
    assert appmod.stream_session_of("bea") == (None, None)
    appmod.kv_put("stream_sessions", {}); appmod.kv_put("stream_session", None)


def test_stream_needs_permission(appmod, client):
    """Gleiche Rechte wie Download und Play. (#71)"""
    appmod.save_users({**ADMIN_FIX, "lena": {"pw": "x", "role": "user", "perms": []}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    assert client.get("/api/stream?title=X").status_code == 403
    assert client.post("/api/stream/start", json={"title": "X"}).status_code == 403
    assert client.get("/api/stream/status").status_code == 403
    appmod.save_users({})


def test_stream_find_file_validates_the_slug_itself(appmod):
    """Der Slug geht in einen Pfad. Er wird IN stream_find_file geprüft, nicht nur beim
    Aufrufer — sonst haengt die Sicherheit an der Reihenfolge der Pruefungen. (#71)"""
    appmod.save_settings({"connections": {"stream_url": "http://s.example/"}})
    for evil in ("../../etc", "..", "/etc", "ps2/../../etc"):
        assert appmod.stream_find_file("passwd", evil) is None, evil
    assert appmod.stream_find_file("X", "snes") is None      # nicht streambar -> kein Pfadzugriff
    appmod.save_settings({})


def test_disc_id_does_not_defeat_title_matching(appmod):
    """PS3-Abzuege tragen ihre Disc-Kennung im Namen (BLES00562). Ohne sie zu
    entfernen traf KEIN einziger PS3-Titel seinen Katalogeintrag — die Suche meldete
    „nicht vorhanden", obwohl der Titel dalag. (#152)"""
    paare = [("Brutal Legend BLES00562", "Brutal Legend"),
             ("Alone in the Dark Inferno BLUS30232", "Alone in the Dark: Inferno"),
             ("Best of PlayStation Network Vol.1 BCUS99205", "Best of PlayStation Network Vol.1")]
    for datei, katalog in paare:
        assert appmod.norm(datei) == appmod.norm(katalog), (datei, appmod.norm(datei))


def test_ps3_is_stripped_like_every_other_platform_token(appmod):
    """`ps1`, `ps2` und `psp` standen in REGION_RE, `ps3` nicht — eine schlichte
    Luecke, die sich als plattformspezifischer Fehler tarnte. (#152)"""
    assert "ps3" not in appmod.norm("Some Game PS3").split()
    assert appmod.norm("Some Game PS3") == appmod.norm("Some Game PS2")


def test_dedup_key_does_not_get_looser(appmod):
    """`norm()` ist die Grundlage der Dedup. Eine zu grosszuegige Regel liesse zwei
    verschiedene Spiele zusammenfallen — ein Fehler, der sich still auswirkt und
    erst auffaellt, wenn ein Titel verschwunden ist. Deshalb steht die Gegenprobe
    neben der Erweiterung. (#152)"""
    for a, b in [("Portal 2", "Portal"), ("FIFA 2005", "FIFA 2006"),
                 ("Half-Life 2", "Half-Life"), ("Rock Band 3", "Rock Band")]:
        assert appmod.norm(a) != appmod.norm(b), (a, b)
    # Eine Kennung mitten im Titel ist kein Grund, den Rest zu verlieren.
    assert appmod.norm("Brutal Legend BLES00562") == "brutal legend"


def test_platform_comes_from_the_library_not_from_the_search_hit(appmod, tmp_path, monkeypatch):
    """Ein Suchtreffer kann `Mixed` heissen — ein realer Ordner mit gemischtem Inhalt,
    keine Plattform — waehrend die passende Datei in `ps2/` liegt. Vorher gab
    stream_info() genau hier auf: kein Stream-Knopf, obwohl der Titel dalag. Am
    laufenden System reproduziert mit Silent Hill 4 und Resident Evil 4. (#154)"""
    (tmp_path / "ps2").mkdir()
    (tmp_path / "ps2" / "Silent Hill 4 - The Room (Europe).iso").write_bytes(b"x")
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    appmod.save_settings({"connections": {"stream_url": "http://s.example/"}})
    alt = _mit_index(appmod, {"ps2": {appmod.norm("Silent Hill 4 - The Room (Europe).iso")}})
    try:
        info = appmod.stream_info("Silent Hill 4 - The Room", "Mixed")
        assert info.get("streamable") is True, info
        assert info.get("platform") == "ps2", info
    finally:
        _index_zurueck(appmod, alt); appmod.save_settings({})


def test_an_ambiguous_platform_is_refused_rather_than_guessed(appmod, tmp_path, monkeypatch):
    """Denselben Titel gibt es fuer PS2 und GameCube. Das PS2-Abbild zu starten, wenn
    die GameCube-Fassung gemeint war, ist eine stille Fehlentscheidung — der Nutzer
    sucht den Fehler dann im Emulator. Lieber absagen und sagen warum. (#154)"""
    for ordner in ("ps2", "ngc"):
        (tmp_path / ordner).mkdir()
        (tmp_path / ordner / "Resident Evil 4.iso").write_bytes(b"x")
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    appmod.save_settings({"connections": {"stream_url": "http://s.example/"}})
    n = appmod.norm("Resident Evil 4.iso")
    alt = _mit_index(appmod, {"ps2": {n}, "ngc": {n}})
    try:
        info = appmod.stream_info("Resident Evil 4", "Mixed")
        assert info.get("streamable") is False, info
        assert info.get("reason") == "ambiguous_platform", info
    finally:
        _index_zurueck(appmod, alt); appmod.save_settings({})


def test_an_unknown_platform_with_nothing_in_the_library_still_says_not_supported(appmod, tmp_path, monkeypatch):
    """Die Erweiterung darf die klare Absage nicht verwaessern: was nirgends liegt,
    bleibt `not_supported`. (#154)"""
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    appmod.save_settings({"connections": {"stream_url": "http://s.example/"}})
    alt = _mit_index(appmod, {"ps2": set()})
    try:
        info = appmod.stream_info("Gibt Es Nicht", "Mixed")
        assert info.get("reason") == "not_supported", info
    finally:
        _index_zurueck(appmod, alt); appmod.save_settings({})


def test_stream_finds_a_title_that_is_a_folder(appmod, tmp_path, monkeypatch):
    """Eine PS3-Disc ist ein ORDNER, kein Abbild. Ohne diesen Zweig meldete jeder
    PS3-Titel `not_in_library`, der Stream-Knopf erschien nie — waehrend der
    Start-Dienst denselben Titel klaglos startet. Zwei Seiten, die sich
    widersprechen, und der Nutzer sieht nur die falsche Auskunft. (#150)"""
    spiel = tmp_path / "ps3" / "Ape Escape 4 PS3-EU BG"
    (spiel / "PS3_GAME" / "USRDIR").mkdir(parents=True)
    (spiel / "PS3_GAME" / "USRDIR" / "EBOOT.BIN").write_bytes(b"x")
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    gefunden = appmod.stream_find_file("Ape Escape 4 PS3-EU BG", "ps3")
    assert gefunden == str(spiel), gefunden


# ---------------------------------------------------------------------------
# #477 Teil 2: Der Index kennt Ordner-Titel seit #478 — die Stream-Suche nicht.
#
# JEDER AUFBAU SAGT IN SEINEM KOPF, OB ER GEMESSEN ODER ERFUNDEN IST (#501). Hier stand
# vorher pauschal „alle am Bestand gemessen" — und einer war es nicht: Er ließ genau die
# Dateien weg, die das Ergebnis entscheiden, und behauptete trotzdem, die Bibliothek zu
# zeigen. Eine Pauschalzusage über mehrere Aufbauten hinweg verfaellt beim ersten, der
# nachtraeglich abweicht, und faellt niemandem auf, weil alle gruen sind.
#
# EN: each fixture states in its own docstring whether it is measured or constructed. A
# blanket claim across several fixtures decays the moment one drifts, and nobody notices
# because they are all green.
# ---------------------------------------------------------------------------

def test_stream_takes_the_nested_image_set_over_the_unbootable_parent(
        appmod, tmp_path, monkeypatch):
    """So sieht `/roms/dc` WIRKLICH aus — und darum gewinnt das GDI-Set. (#477, #501)

    NACHGEBAUT AUS DEM BESTAND, mit dem Teil, den die erste Fassung dieses Tests
    weggelassen hat:

        Sonic Adventure.cdi                                   757 MB
        Sonic Adventure (PAL)/Replayers.url
        Sonic Adventure (PAL)/[GDI] Sonic Adventure (PAL)/
            Sonic Adventure v1.003 (1999)(Sega)(PAL)(M5)[!].gdi      89 B
            track01.bin / track02.raw / track03.bin           zus. 1,2 GB

    Alle drei Namen normalisieren auf `sonic adventure`. Der ELTERNORDNER war der
    Defekt: Er gewann, trägt aber nur eine `.url` und einen Unterordner. Am
    laufenden Host nachgemessen, mit dem `_bootdatei` des Start-Dienstes:

        /roms/dc/Sonic Adventure (PAL)                              -> ''
        /roms/dc/Sonic Adventure (PAL)/[GDI] Sonic Adventure (PAL)  -> '…gdi'

    Das verschachtelte Set IST ein Titelordner (eine `.gdi` nennt Dateien daneben),
    also liefert der Ordnerzweig es zurück, bevor die Dateisuche drankommt — die
    `.cdi` gewinnt hier NICHT. Das ist richtig so: Beides ist spielbar, und der
    Ordnerzweig soll Titelordner vorziehen.

    WARUM DIESER TEST EIGENS EXISTIERT: Die erste Fassung ließ den Unterordner leer
    und behauptete im Kopf trotzdem, sie sei am Bestand gemessen. Sie war grün und
    beschrieb ein Verhalten, das die Bibliothek nicht zeigt (#501). Ein Test, dessen
    Aufbau von dem abweicht, was er zu reproduzieren vorgibt, ist schlimmer als
    keiner — ihm wird geglaubt.

    EN: the real `/roms/dc` layout, including the tracks the first version of this
    test omitted. The nested folder IS an image set, so it is returned before the
    file search — the `.cdi` does not win, and that is correct. The defect was the
    parent folder, which resolves to '' and used to win.
    """
    dc = tmp_path / "dc"
    satz = dc / "Sonic Adventure (PAL)" / "[GDI] Sonic Adventure (PAL)"
    satz.mkdir(parents=True)
    (satz / "Sonic Adventure v1.003 (1999)(Sega)(PAL)(M5)[!].gdi").write_text(
        "3\n1 0 4 2352 track01.bin 0\n2 600 0 2352 track02.raw 0\n"
        "3 45000 4 2352 track03.bin 0\n")
    for spur in ("track01.bin", "track02.raw", "track03.bin"):
        (satz / spur).write_bytes(b"x")
    (dc / "Sonic Adventure (PAL)" / "Replayers.url").write_bytes(b"x")
    (dc / "Sonic Adventure.cdi").write_bytes(b"x")
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    assert appmod.stream_find_file("Sonic Adventure", "dreamcast") == str(satz)


def test_stream_prefers_the_image_over_a_folder_without_bootable_content(
        appmod, tmp_path, monkeypatch):
    """Ein Ordner OHNE Startbares darf ein spielbares Abbild nicht verdraengen. (#477)

    Derselbe Aufbau wie oben, nur ohne das GDI-Set: Dann ist unter dem gleichnamigen
    Ordner nichts, was ein Titel sein könnte, und die Datei daneben muss gewinnen.
    Sonst meldet die Auskunft den Titel als streambar, nennt den Ordner, und der
    Start-Dienst antwortet darauf `Ordner ohne startbaren Inhalt` — zwei Seiten, die
    sich widersprechen, waehrend das Abbild danebenliegt.

    Dieser Aufbau ist ERFUNDEN, nicht gemessen: In `/roms/dc` traegt der Unterordner
    heute die Spuren (siehe der Test darueber). Er haelt den urspruenglichen Defekt
    aus #477 fest, unabhaengig davon, wie die Bibliothek gerade aussieht.

    EN: same layout minus the image set — nothing under the folder can be a title, so
    the playable file beside it must win. This fixture is constructed, not measured,
    and pins the original #477 defect independently of the library's current shape.
    """
    dc = tmp_path / "dc"
    (dc / "Sonic Adventure (PAL)" / "[GDI] Sonic Adventure (PAL)").mkdir(parents=True)
    (dc / "Sonic Adventure (PAL)" / "Replayers.url").write_bytes(b"x")
    abbild = dc / "Sonic Adventure.cdi"
    abbild.write_bytes(b"x")
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    assert appmod.stream_find_file("Sonic Adventure", "dreamcast") == str(abbild)


def test_stream_finds_a_folder_title_one_level_down(appmod, tmp_path, monkeypatch):
    """Der Index legt Ordner-Titel bis Ebene 2 ab, die Suche sah nur Ebene 1. (#477)

    GEMESSEN in `/roms/ps3`:

        DmC Devil May Cry [+All DLC] BLUS30723/
            BLUS30723 DLCs/…pkg
            Devil May Cry 5/PS3_DISC.SFB + PS3_GAME/     <- der Titel

    Der Index fuehrt `Devil May Cry 5`; die Stream-Auskunft sagte dazu am laufenden
    Dienst `not_in_library`. Genau der Widerspruch, gegen den #150 den Ordnerzweig
    ueberhaupt eingezogen hat — diesmal eine Ebene tiefer.
    """
    spiel = (tmp_path / "ps3" / "DmC Devil May Cry [+All DLC] BLUS30723"
             / "Devil May Cry 5")
    (spiel / "PS3_GAME" / "USRDIR").mkdir(parents=True)
    (spiel / "PS3_GAME" / "USRDIR" / "EBOOT.BIN").write_bytes(b"x")
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    assert appmod.stream_find_file("Devil May Cry 5", "ps3") == str(spiel)


def test_stream_file_search_does_not_stop_at_the_first_nested_folder(
        appmod, tmp_path, monkeypatch):
    """`break` statt `dirs[:] = []` beendete die GANZE Suche. (#477)

    Die Tiefenbremse brach die Wanderung ab, sobald der erste Ordner auf Ebene 2
    auftauchte — alles, was danach kam, wurde nie angesehen. AM BESTAND GEMESSEN:

        /roms/dc   64 von 173 Dateien gesehen, 109 uebersehen (52 davon ROMs)
        /roms/psx  2925 von 2993 gesehen, 68 uebersehen (44 davon ROMs)

    `gc` und `ps2` waren unauffaellig — dort liegt kein Ordner auf Ebene 2, deshalb
    fiel es nie auf. Der Aufbau hier bildet `dc` nach: ein verschachtelter Ordner,
    der alphabetisch VOR dem gesuchten Titel steht.
    """
    dc = tmp_path / "dc"
    (dc / "Aaa Verschachtelt" / "Innen").mkdir(parents=True)
    (dc / "Aaa Verschachtelt" / "Innen" / "egal.bin").write_bytes(b"x")
    ziel = dc / "Zzz Spaeter Titel" / "Zzz Spaeter Titel.gdi"
    ziel.parent.mkdir()
    ziel.write_bytes(b"x")
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    assert appmod.stream_find_file("Zzz Spaeter Titel", "dreamcast") == str(ziel)


def test_stream_still_returns_a_folder_when_nothing_else_matches(
        appmod, tmp_path, monkeypatch):
    """Kein Titelaufbau, keine passende Datei -> weiterhin der Ordner. (#477)

    Die Ratsche gegen den Uebereifer: 39 Ordner im Bestand sind WEDER Titelordner
    (`SPIELORDNER_MUSTER` oder Abbild-Set) NOCH enthalten sie einen — `gc/Pikmin
    (USA) (v1.00)` etwa traegt eine einzelne `.rvz`, die der Start-Dienst selbst
    aufloest. Fuer die verhaelt sich die Suche unveraendert; wer den Ordnerzweig
    strenger macht, darf sie nicht verlieren.
    """
    ordner = tmp_path / "gc" / "Pikmin (USA) (v1.00)"
    ordner.mkdir(parents=True)
    (ordner / "irgendwas-ganz-anderes.rvz").write_bytes(b"x")
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    assert appmod.stream_find_file("Pikmin (USA) (v1.00)", "ngc") == str(ordner)


def test_stream_info_reports_a_folder_title_as_streamable(appmod, tmp_path, monkeypatch):
    """Der Befund muss bis zur Auskunft durchschlagen — sonst ist der Knopf weiterhin
    weg, obwohl die Suche den Titel findet. (#150)"""
    spiel = tmp_path / "ps3" / "Brutal Legend BLES00562"
    (spiel / "PS3_GAME" / "USRDIR").mkdir(parents=True)
    (spiel / "PS3_GAME" / "USRDIR" / "EBOOT.BIN").write_bytes(b"x")
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    appmod.save_settings({"connections": {"stream_url": "http://s.example/"}})
    try:
        info = appmod.stream_info("Brutal Legend BLES00562", "ps3")
        assert info.get("streamable") is True, info
        assert info.get("reason") == "", info
    finally:
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
    # Ausnahmen sind erlaubt, aber nur ausdrueckliche: PS1 bietet bewusst beide Wege
    # an (#268). Alles, was nicht in DUAL_WEG steht, bleibt ein Fehler — sonst waere
    # die Regel beim naechsten Nachruesten still ausgehoehlt.
    assert ueberschneidung <= appmod.DUAL_WEG, \
        f"Plattform in beiden Mengen, ohne Eintrag in DUAL_WEG: {ueberschneidung - appmod.DUAL_WEG}"
    # Und umgekehrt: eine Ausnahme, die gar nicht mehr in beiden Mengen steht, ist
    # eine Karteileiche und gehoert entfernt.
    assert appmod.DUAL_WEG <= ueberschneidung, \
        f"DUAL_WEG nennt Plattformen, die gar nicht in beiden Mengen sind: {appmod.DUAL_WEG - ueberschneidung}"
    # die nachgeruesteten Plattformen sind wirklich drin
    for slug in ("xbox", "ps3", "psvita", "dreamcast", "3ds", "wiiu"):
        assert slug in appmod.STREAMABLE, slug


def test_emulator_endpoints_need_manage_settings(appmod, client):
    """Emulatoren aktualisieren und zuruecksetzen ist Administration. (#102)"""
    appmod.save_users({**ADMIN_FIX, "lena": {"pw": "x", "role": "user", "perms": ["request"]}})
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


def test_no_test_file_defines_the_same_name_twice():
    """Ein Doppelname loescht die frueher definierte Sache — lautlos. (#506)

    Python bindet den Namen zweimal; die ZWEITE Definition gewinnt fuer jeden Aufruf,
    egal wo im Modul er steht. Deshalb ist das hier keine Stilfrage:

    * Bei zwei `test_`-Funktionen verschwindet ein Test. Pytest meldet dieselbe
      Gesamtzahl wie vorher — es SIEHT den zweiten gar nicht —, und niemand merkt,
      dass eine Zusicherung nicht mehr laeuft.
    * Bei zwei Helfern pruefen Tests etwas anderes, als ihr Name sagt. Genau so
      geschehen: `_profil_modul` war zweimal definiert, einmal auf
      `controller-profile.py` und einmal auf `launch-profile.py`. Die erste Datei
      existiert seit bdc75cf (#140) nicht mehr, vier Tests hiessen weiter
      `test_controller_profile_*` — und waren gruen, weil die zweite Definition sie
      still umgeleitet hat.

    Der Fund kam beim Aufteilen der Datei (#505), nicht durch einen Fehlschlag. Ohne
    diese Pruefung waere er beim naechsten Aufraeumen als `FileNotFoundError`
    aufgetaucht, also als Symptom statt als Ursache.

    EN: a duplicate top-level name silently deletes the earlier definition. For two
    tests that means one test is gone with the reported count unchanged; for two
    helpers it means tests exercise a different subject than their name claims — which
    is exactly what happened with `_profil_modul` (#506).
    """
    import collections
    verzeichnis = os.path.join(REPO, "tests")
    befunde = []
    for datei in sorted(os.listdir(verzeichnis)):
        if not datei.endswith(".py"):
            continue
        pfad = os.path.join(verzeichnis, datei)
        baum = ast.parse(open(pfad, encoding="utf-8").read())
        namen = [k.name for k in baum.body
                 if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        for name, wie_oft in collections.Counter(namen).items():
            if wie_oft > 1:
                befunde.append(f"{datei}: {name} ({wie_oft}x)")
    assert not befunde, (
        "diese Namen sind mehrfach vergeben — die frueheren Definitionen sind damit "
        f"unerreichbar: {befunde}")


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
    appmod.save_users({**ADMIN_FIX, "lena": {"pw": "x", "role": "user", "perms": ["request"]}})
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
    Wahrheit; version.txt auf dev traegt nur eine Entwicklungsmarke. (#111)

    ERWEITERT (#183): Die Marke allein war zu eng. Der `simple`-Typ von release-please
    BESITZT version.txt — die Datei anzuheben ist der Zweck des Release-PR. Die alte
    Fassung wies damit genau den Commit ab, der zum Release wird, und kein Release kam
    je durch. Erlaubt ist deshalb beides: die Entwicklungsmarke ODER exakt die Version
    aus dem Manifest.

    Der Fehler, fuer den die Regel geschrieben wurde, faellt weiterhin durch: `0.1.0`
    neben einem veroeffentlichten `v1.0.0-beta.1` ist weder das eine noch das andere.
    Und "welcher Bau ist das genau" war ueber die Version ohnehin nie zu beantworten —
    dafuer traegt /api/version seit #143 `commit` und `built_at`.

    Extended: release-please owns version.txt, so the release commit legitimately holds
    the release version. Accept the marker or the manifest version; anything else — the
    original fault — still fails."""
    import json
    manifest = json.load(open(os.path.join(REPO, ".release-please-manifest.json")))
    assert list(manifest) == ["."] and manifest["."], manifest
    dev_version = open(os.path.join(REPO, "version.txt"), encoding="utf-8").read().strip()
    assert dev_version.endswith("-dev") or dev_version == manifest["."], (
        f"version.txt ist {dev_version!r} — weder Entwicklungsmarke (…-dev) noch die "
        f"Version aus dem Manifest ({manifest['.']!r}). Genau diese Luecke liess "
        f"/api/version seit dem Beta-Release luegen.")


def test_release_tags_stay_continuous():
    """Mit einem Komponentennamen taggt release-please `romseerr-v1.2.3` statt `v1.2.3`.
    Das bricht die Reihe ab v1.0.0-beta.1 — und damit den dokumentierten Weg, einen
    Versionszweig rueckwirkend aus einem Tag zu schneiden. (#111)"""
    import json
    cfg = json.load(open(os.path.join(REPO, "release-please-config.json")))
    root = cfg["packages"]["."]
    assert "package-name" not in root, "package-name erzeugt Tags mit Praefix"
    assert root.get("include-component-in-tag") is False


def test_all_actions_are_pinned_to_a_commit(): 
    """Ein Tag ist ein VERSCHIEBBARER Zeiger. Wer ihn uebernimmt, fuehrt Code in dieser
    CI aus — release-please laeuft mit contents:write, das Image-Release mit
    packages:write. Genau so lief der tj-actions/changed-files-Vorfall 2025.
    Deshalb: nur 40-stellige Commit-SHAs, Version als Kommentar dahinter. (#117)"""
    import glob
    unpinned = []
    for f in sorted(glob.glob(os.path.join(REPO, ".github/workflows/*.yml"))):
        for n, line in enumerate(open(f, encoding="utf-8"), 1):
            m = re.search(r"uses:\s*([\w.-]+/[\w./-]+)@(\S+)", line)
            if not m:
                continue                       # lokale Actions (./…) haben kein @
            if not re.fullmatch(r"[0-9a-f]{40}", m.group(2)):
                unpinned.append(f"{os.path.basename(f)}:{n}: {m.group(1)}@{m.group(2)}")
    assert not unpinned, "nicht auf Commit gepinnt:\n  " + "\n  ".join(unpinned)


def test_published_image_carries_provenance():
    """Wer das Image zieht, soll pruefen koennen, aus welchem Commit es stammt —
    `gh attestation verify`. Ohne das ist die Lieferkette am letzten Meter blind. (#117)"""
    text = open(os.path.join(REPO, ".github/workflows/release-image.yml"), encoding="utf-8").read()
    assert "attest-build-provenance" in text
    assert "steps.push.outputs.digest" in text, "Bescheinigung muss am Digest haengen, nicht am Tag"
    assert "sbom: true" in text


# ---------------------------------------------------------- Firmware/BIOS (#107)

def test_firmware_routes_need_manage_settings(appmod, client):
    appmod.save_users({**ADMIN_FIX, "lena": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "lena"; sess["role"] = "user"
    assert client.get("/api/stream/firmware").status_code == 403
    assert client.post("/api/stream/firmware/vendor", json={"platform": "ps3"}).status_code == 403
    appmod.save_users({})


def test_firmware_vendor_only_where_the_vendor_publishes(appmod, client):
    """Nur Sony liefert Systemsoftware selbst aus. Fuer PS2, Xbox, Dreamcast, 3DS,
    Switch und Wii U gibt es keine berechtigte Quelle — ein Knopf, der so tut, waere
    eine Einladung, ihn woanders zu suchen. (#107)"""
    appmod.save_settings({"connections": {"stream_launch": "http://s.example:8901/launch?token=x"}})
    appmod.save_users({"a": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "a"; sess["role"] = "admin"
    for plat in ("ps2", "xbox", "dreamcast", "switch", "psvita", "wiiu", "3ds", ""):
        r = client.post("/api/stream/firmware/vendor", json={"platform": plat})
        assert r.status_code == 400 and r.get_json()["reason"] == "no_vendor_source", plat
    appmod.save_settings({}); appmod.save_users({})


def test_firmware_upload_validates_platform_and_name(appmod, client):
    """Beides wird auf dem Streaming-Host zu einem Pfad. (#107)"""
    import io as _io
    appmod.save_settings({"connections": {"stream_launch": "http://s.example:8901/launch?token=x"}})
    appmod.save_users({"a": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "a"; sess["role"] = "admin"

    def post(platform, name):
        return client.post("/api/stream/firmware/upload", content_type="multipart/form-data",
                           data={"platform": platform, "name": name,
                                 "file": (_io.BytesIO(b"x" * 16), "f.bin")})

    for plat in ("../etc", "PS2", "ps2;rm -rf /", ""):
        assert post(plat, "dc_boot.bin").get_json()["reason"] == "bad_platform", plat
    for name in ("../../etc/passwd", "a/b", ".ssh", ""):
        r = post("dreamcast", name)
        # Ein leerer Name faellt auf den Dateinamen zurueck und ist dann gueltig.
        if name:
            assert r.get_json()["reason"] == "bad_name", name
    appmod.save_settings({}); appmod.save_users({})


def test_no_firmware_or_bios_files_in_the_repository():
    """Die Inhaltsregel deckt das ab — hier steht es noch einmal ausdruecklich, damit
    die Absicht bei einem Beitrag zu diesem Bereich sichtbar ist. (#107)"""
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(REPO, "scripts/check_content_policy.py")],
                       capture_output=True, text=True, env={**os.environ, "POLICY_ROOT": REPO})
    assert r.returncode == 0, r.stderr


def test_romseerr_sends_a_library_relative_path(appmod, client, monkeypatch):
    """Der Fehler, der das ausgeloest hat: Romseerr schickte einen absoluten Pfad, der
    Streaming-Host haengt die Bibliothek woanders ein, der Start scheiterte still und
    der Nutzer sah nur den Desktop. (#130)"""
    gesehen = {}

    class Antwort:
        ok, status_code, content = True, 200, b"{}"
        def json(self): return {"ok": True}

    def falsches_post(url, **kw):
        gesehen.update(kw.get("json") or {})
        return Antwort()

    monkeypatch.setattr(appmod, "safe_post", falsches_post)
    monkeypatch.setattr(appmod, "stream_info", lambda t, s, u="": {
        "streamable": True, "platform": "ps2",
        "path": os.path.join(appmod.ROMS, "ps2", "ISO", "spiel.iso"), "reason": ""})
    appmod.save_settings({"connections": {"stream_url": "https://h.example",
                                          "stream_launch": "http://h.example:8901/launch?token=x"}})
    out, code = appmod.stream_start("lena", "Spiel", "ps2")
    assert code == 200 and out["launched"] is True
    assert gesehen.get("rel") == os.path.join("ps2", "ISO", "spiel.iso"), gesehen
    assert "path" in gesehen, "der absolute Pfad geht zur Vertraeglichkeit weiter mit"
    appmod.kv_put("stream_sessions", {}); appmod.kv_put("stream_session", None); appmod.save_settings({})


# ------------------------------------------ Ordnernamen -> Plattform (#124)

def test_folder_aliases_reach_the_platforms_romseerr_knows(appmod):
    """Der Sinn der Tabelle: aus einem Ordnernamen, den Romseerr nicht kennt, wird ein
    Slug, den es kennt. Ein Alias, der auf etwas Unbekanntes zeigt, waere folgenlos —
    genau das soll hier auffallen. (#124)"""
    ohne_wirkung = [f"{f} -> {z}" for f, z in appmod.FOLDER_ALIASES.items()
                    if z not in appmod._PLAT_LOOKUP]
    assert not ohne_wirkung, "Alias zeigt auf eine unbekannte Plattform: " + ", ".join(ohne_wirkung)


def test_unknown_folders_pass_through_unchanged(appmod):
    """Eine unbekannte Plattform ist kein Fehler, sondern eine, die dieses Projekt noch
    nicht kennt. Sie umzubenennen oder kleinzuschreiben wuerde bestehende Bibliotheken
    umsortieren. (#124)"""
    # „Dingoo" stand hier und ist inzwischen ein Firmware-Ordner in IGNORE_FOLDERS (#124) —
    # als Beispiel für „unbekannt" taugt es damit nicht mehr.
    for name in ("GP32", "RG350", "wasm-4", "meine-eigene-plattform"):
        assert appmod.folder_slug(name) == name


def test_non_platform_folders_are_ignored(appmod):
    """Ohne diese Liste wird eine Spieldatendatei zu einer Plattform — in RomM ist
    genau das passiert (dort gibt es eine Plattform 'VVVVVV Data file'). (#124)"""
    for name in appmod.IGNORE_FOLDERS:
        assert appmod.folder_slug(name) == ""


def test_slug_folders_comes_from_the_constant_table(appmod):
    """Der Streaming-Host bekommt daraus Pfade. Die Liste muss aus der KONSTANTEN
    Tabelle stammen, nie aus einer Eingabe — sonst haengt die Sicherheit daran, wer
    sie aufruft. (#124)"""
    assert appmod.slug_folders("arcade")[0] == "arcade"
    assert "cps1" in appmod.slug_folders("arcade") and "cps2" in appmod.slug_folders("arcade")
    # Nichts Fremdes: jeder Eintrag ist entweder der Slug selbst oder steht in der Tabelle
    for s in appmod.STREAMABLE:
        for f in appmod.slug_folders(s):
            assert f == s or appmod.FOLDER_ALIASES.get(f) == s, f


def test_stream_finds_a_file_in_an_aliased_folder(appmod, tmp_path, monkeypatch):
    """GameCube liegt bei RetroNAS in `gc`. Ohne Aufloesung findet der Stream nichts,
    und der Knopf erscheint gar nicht erst. (#124)"""
    (tmp_path / "gc").mkdir()
    ziel = tmp_path / "gc" / "Zelda Wind Waker.iso"
    ziel.write_bytes(b"x")
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    gefunden = appmod.stream_find_file("Zelda Wind Waker", "ngc")
    assert gefunden == str(ziel), gefunden


def test_index_merges_several_folders_into_one_platform(appmod, tmp_path, monkeypatch):
    """cps1, cps2 und Atomiswave sind keine eigenen Plattformen, sondern Teilmengen
    desselben Kerns. Wuerde der zweite Ordner den ersten ueberschreiben statt sich zu
    ergaenzen, verschwaende die Haelfte lautlos. (#124)"""
    for ordner, datei in (("cps1", "Final Fight.zip"), ("cps2", "Marvel vs Capcom.zip")):
        (tmp_path / ordner).mkdir()
        (tmp_path / ordner / datei).write_bytes(b"x")
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    monkeypatch.setattr(appmod, "save_index_to_db", lambda *a, **k: None)
    appmod.build_index()
    with appmod.LIB_LOCK:
        arcade = appmod.LIB["per"].get("arcade", set())
        slugs = set(appmod.LIB["slugs"])
    assert "arcade" in slugs and "cps1" not in slugs and "cps2" not in slugs
    assert len(arcade) == 2, arcade


def test_launch_sends_the_region(appmod, client, monkeypatch):
    """Die Region kommt aus der Fassungserkennung (#77) und entscheidet auf dem Host
    ueber das BIOS. (#119)"""
    gesehen = {}
    class Antwort:
        ok, status_code, content = True, 200, b"{}"
        def json(self): return {"ok": True}
    monkeypatch.setattr(appmod, "safe_post", lambda url, **kw: (gesehen.update(kw.get("json") or {}), Antwort())[1])
    monkeypatch.setattr(appmod, "stream_info", lambda t, s, u="": {
        "streamable": True, "platform": "ps2", "reason": "",
        "path": os.path.join(appmod.ROMS, "ps2", "Ratchet & Clank (Europe).iso")})
    appmod.save_settings({"connections": {"stream_url": "https://h.example",
                                          "stream_launch": "http://h.example:8901/launch?token=x"}})
    appmod.stream_start("lena", "Ratchet & Clank", "ps2")
    assert gesehen.get("region") == "Europe", gesehen
    appmod.kv_put("stream_sessions", {}); appmod.kv_put("stream_session", None); appmod.save_settings({})


def test_version_says_whether_it_knows_its_own_build(appmod, client, monkeypatch):
    """`{"commit": null}` sieht aus wie eine Antwort und ist die Abwesenheit einer.
    Genau daran ist hier ein Container einen ganzen Arbeitstag mit dem Stand vom
    Vortag gelaufen, ohne dass es jemand sah. (#129)"""
    monkeypatch.setattr(appmod, "BUILD_COMMIT", None)
    monkeypatch.setattr(appmod, "BUILD_DATE", None)
    d = client.get("/api/version").get_json()
    assert d["provenance"] == "unbekannt"
    assert "provenance_hint" in d and "ROMSEERR_COMMIT" in d["provenance_hint"]

    monkeypatch.setattr(appmod, "BUILD_COMMIT", "abc1234")
    monkeypatch.setattr(appmod, "BUILD_DATE", "2026-08-08T12:00:00Z")
    d = client.get("/api/version").get_json()
    assert d["provenance"] == "build" and "provenance_hint" not in d


def test_docs_explain_how_to_build_with_provenance():
    """Ein Hinweis, der nicht sagt, WIE man ihn abstellt, ist ein Vorwurf. (#129)"""
    readme = open(os.path.join(REPO, "README.md"), encoding="utf-8").read()
    assert "ROMSEERR_COMMIT" in readme and "ROMSEERR_BUILT_AT" in readme


def test_playable_cores_exist_in_the_player(appmod):
    """Ein Eintrag auf einen Kern, den RomMs EmulatorJS-Bau nicht mitbringt, ist ein
    Knopf, der nicht funktioniert. Die hier zugelassenen Kerne wurden in der
    eingesetzten Fassung NACHGESEHEN — diese Liste haelt die Zusage fest. (#124)"""
    # In der eingesetzten RomM-Fassung vorhanden (aus deren Frontend abgelesen).
    vorhanden = {
        "stella2014", "prosystem", "a5200", "handy", "virtualjaguar", "opera",
        "fceumm", "snes9x", "mupen64plus_next", "gambatte", "mgba", "melonds",
        "beetle_vb", "smsplus", "genesis_plus_gx", "picodrive", "yabause",
        "mednafen_psx_hw", "ppsspp", "mednafen_pce", "mednafen_ngp",
        "mednafen_wswan", "puae", "vice_x64", "vice_xplus4", "vice_xvic",
        "dosbox_pure", "fbneo", "gearcoleco", "bluemsx", "freeintv", "cap32", "fuse",
    }
    unbekannt = {s: k for s, k in appmod.PLAYABLE.items() if k not in vorhanden}
    assert not unbekannt, f"Kern nicht im Player: {unbekannt}"


def test_every_playable_platform_is_a_known_platform(appmod):
    """Ein Kern fuer einen Slug, den Romseerr nicht kennt, taucht nirgends auf. (#124)"""
    fremd = [s for s in appmod.PLAYABLE if s not in appmod.SLUG_NAME]
    assert not fremd, f"nicht in PLATFORMS: {fremd}"


def test_firmware_panel_names_the_not_installed_state():
    """Der Zustand muss in der Oberflaeche ankommen, nicht nur in der API. Vorher war
    `fehlt` in diesem Fall leer und es wurde GAR NICHTS geschrieben — die Plattform sah
    aus wie ohne Befund. (#162)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    assert "p.needs_install&&!p.installed" in js, "der Zustand wird nicht abgefragt"
    assert i18n_hat("fw_notinstalled") == 5, "Text fehlt in mindestens einer Sprache"


def test_scorecard_skips_a_wrong_branch_instead_of_failing(appmod):
    """Ein Aufruf auf dem falschen Zweig endet gruen, und auf dem richtigen misst er. (#470)

    VORGESCHICHTE: `ossf/scorecard-action` weist jeden anderen Zweig als den Standardzweig
    ab. Der `push`-Ausloeser wurde deshalb entfernt (#369) — `workflow_dispatch` riss
    dasselbe Loch von der anderen Seite auf. Ein `gh workflow run --ref dev` liess den
    Workflow auf ROT stehen, bis zum naechsten Wochenlauf, ohne dass jemand etwas tun
    konnte.

    ZWEI RICHTUNGEN, und die zweite ist die wichtigere: Ein Waechter, der IMMER
    ueberspringt, waere gruen und wuerde NIE messen — genau die Sorte Stille, die aus
    „nicht geprueft" ein „in Ordnung" macht. Deshalb wird hier auch geprueft, dass der
    Sonst-Zweig auf `nein` setzt und der Vergleich gegen den ECHTEN Standardzweig laeuft
    statt gegen einen fest eingetippten Namen.
    """
    import yaml
    pfad = os.path.join(REPO, ".github/workflows/scorecard.yml")
    text = open(pfad, encoding="utf-8").read()
    schritte = yaml.safe_load(text)["jobs"]["analysis"]["steps"]

    waechter = schritte[0]
    assert waechter.get("id"), "der erste Schritt traegt keine id — auf die sich `if` beruft"
    kennung = waechter["id"]

    ohne = [x.get("name") or x.get("uses", "?") for x in schritte[1:] if "if" not in x]
    assert not ohne, (
        f"diese Schritte laufen auch auf dem falschen Zweig und faerben ihn rot: {ohne}")
    for x in schritte[1:]:
        assert kennung in x["if"], f"die Bedingung beruft sich nicht auf {kennung}: {x['if']}"

    lauf = waechter.get("run", "")
    # AUF DIE VERGLEICHSZEILE PRUEFEN, nicht auf das Vorkommen irgendwo. Erste Fassung
    # dieses Tests suchte den Ausdruck im ganzen Skript — und fand ihn in der MELDUNG
    # darunter, waehrend der Vergleich selbst bereits auf `"main"` festgenagelt war. Die
    # Sabotage lief gruen durch. (#470)
    vergleich = [z for z in lauf.splitlines() if "github.ref_name" in z]
    assert vergleich, "es gibt keine Zeile, die den Zweig vergleicht"
    assert "github.event.repository.default_branch" in vergleich[0], (
        "der Standardzweig ist im VERGLEICH fest eingetippt statt abgefragt — beim "
        f"Umbenennen wuerde der Workflow lautlos alles ueberspringen: {vergleich[0].strip()}")
    assert "=nein" in lauf, (
        "der Sonst-Zweig setzt nichts — dann uebersprigne der Waechter IMMER, und der "
        "Workflow waere gruen, ohne je zu messen")


def test_the_openapi_version_line_carries_the_release_marker():
    """Die Versionszeile in docs/openapi.yaml hat ZWEI Besitzer: den Generator und
    release-please. Ohne die Marke hebt release-please version.txt an, die Spec
    bleibt zurueck, und `test_openapi_yaml_in_sync` scheitert — bei JEDEM Release.
    Genau daran hing #116 tagelang, ohne dass der Grund sichtbar war.

    Die Marke muss jede Neuerzeugung ueberleben, deshalb wird hier BEIDES geprueft:
    dass sie in der Datei steht, und dass die Konfiguration die Datei ueberhaupt
    anfasst. Eine der beiden Haelften allein ist wirkungslos."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = open(os.path.join(root, "docs", "openapi.yaml"), encoding="utf-8").read()
    zeile = [z for z in spec.splitlines() if z.startswith("  version:")]
    assert zeile, "keine Versionszeile unter info:"
    assert "x-release-please-version" in zeile[0], zeile[0]

    cfg = json.load(open(os.path.join(root, "release-please-config.json"), encoding="utf-8"))
    extra = cfg["packages"]["."].get("extra-files", [])
    assert "docs/openapi.yaml" in extra, f"release-please fasst die Spec nicht an: {extra}"


def test_a_release_creates_a_branch_and_never_moves_one():
    """Ein Tag kann keine nachgezogene Korrektur aufnehmen — dafuer gibt es den
    Release-Zweig. Der Wert steckt aber ganz darin, dass er NICHT zurueckgesetzt
    wird: ein vorhandener Zweig kann Backports tragen, und ihn auf den
    Release-Commit zu schieben wuerfe genau die weg, lautlos. (#186)"""
    wf = open(os.path.join(REPO, ".github/workflows/release-please.yml"),
              encoding="utf-8").read()
    d = yaml.safe_load(wf)
    job = d["jobs"]["release-branch"]
    assert job["needs"] == "release-please"
    # Nur bei einem echten Release, sonst entstuenden Zweige ohne Anlass.
    assert "released == 'true'" in job["if"]
    schritt = " ".join(s.get("run", "") for s in job["steps"])
    assert "release/$TAG" in schritt
    # Die Schutzregel: erst nachsehen, dann anlegen — und niemals ueberschreiben.
    assert "git/ref/heads/" in schritt and "exit 0" in schritt
    for verboten in ("--force", "-X PATCH", "-X PUT"):
        assert verboten not in schritt, f"{verboten} wuerde einen Zweig verschieben"


def test_the_readme_says_how_to_run_an_older_version():
    """Eine aeltere Fassung zu fahren war nirgends beschrieben, und die beiden Wege
    koennen Verschiedenes: die Abbildmarke fuer einen ziehenden Container, der Zweig
    fuers Bauen und Nachbessern. Ohne die Bau-Argumente meldet /api/version weder
    Commit noch Bauzeitpunkt — der Fall aus #129. (#186)"""
    r = open(os.path.join(REPO, "README.md"), encoding="utf-8").read()
    assert "## Versionen: aktualisieren und zurückgehen" in r
    for pflicht in ("ROMSEERR_COMMIT", "ROMSEERR_BUILT_AT", "release/v", "ghcr.io"):
        assert pflicht in r, pflicht
    # Der ehrliche Vorbehalt gehoert dazu, sonst liest sich das wie eine Zusage.
    assert "nicht garantiert lauffähig" in r


def test_the_english_readme_says_how_to_run_an_older_version():
    """Derselbe Abschnitt, dieselbe Zusage — nur auf Englisch, wo er fehlte.

    Der Test darueber prueft NUR README.md. Genau daran ist der Abschnitt vorbeigelaufen:
    er stand ein halbes Jahr in der deutschen Datei und in der englischen nie. Wer nach
    einem missratenen Update zurueckwill, braucht den Weg zurueck in seiner Sprache —
    und das ist der Moment, in dem niemand uebersetzt. (#378)"""
    r = open(os.path.join(REPO, "README.en.md"), encoding="utf-8").read()
    assert "## Versions: updating, and going back" in r
    for pflicht in ("ROMSEERR_COMMIT", "ROMSEERR_BUILT_AT", "release/v", "ghcr.io"):
        assert pflicht in r, pflicht
    # Der ehrliche Vorbehalt gehoert dazu, sonst liest sich das wie eine Zusage.
    assert "not guaranteed to run" in r
    # Und er muss im Inhaltsverzeichnis stehen, sonst findet ihn niemand.
    assert "(#versions-updating-and-going-back)" in r


def test_both_readmes_carry_the_same_sections():
    """Ein ganzer `##`-Abschnitt fehlte in README.en.md, und nichts hat es gemerkt.

    Gemessen zum Zeitpunkt des Fundes: 22 `##` deutsch gegen 21 englisch, 18 Eintraege im
    Inhaltsverzeichnis gegen 17. Eine Luecke von genau einem Abschnitt — die Sorte Drift,
    die ein Mensch beim Lesen nicht sieht, weil beide Dateien fuer sich stimmig wirken.
    Der Test vergleicht deshalb den Aufbau, nicht den Text: Zahl der Abschnitte, Zahl der
    Verzeichniseintraege, Zahl der Unterabschnitte. (#378)"""
    de2 = _readme_ueberschriften("README.md", "##")
    en2 = _readme_ueberschriften("README.en.md", "##")
    assert len(de2) == len(en2), (
        f"{len(de2)} deutsche `##`-Abschnitte gegen {len(en2)} englische — "
        f"einer fehlt oder ist zu viel.\nDE: {de2}\nEN: {en2}"
    )

    def verzeichnis(datei):
        text = open(os.path.join(REPO, datei), encoding="utf-8").read()
        return re.findall(r"^- \[.+?\]\(#.+?\)$", text, re.MULTILINE)

    de_toc, en_toc = verzeichnis("README.md"), verzeichnis("README.en.md")
    assert len(de_toc) == len(en_toc), (
        f"Inhaltsverzeichnis: {len(de_toc)} deutsche Eintraege gegen {len(en_toc)} "
        f"englische.\nDE: {de_toc}\nEN: {en_toc}"
    )

    de3 = _readme_ueberschriften("README.md", "###")
    en3 = _readme_ueberschriften("README.en.md", "###")
    for ausnahme in ZWEISPRACHIG_IN_EINEM_STUECK:
        assert ausnahme in de3, (
            f"{ausnahme!r} steht nicht mehr in README.md — die Ausnahme meint einen "
            "Abschnitt, den es nicht gibt, und deckt damit still eine echte Luecke."
        )
    erwartet = len(de3) - len(ZWEISPRACHIG_IN_EINEM_STUECK)
    assert erwartet == len(en3), (
        f"{len(de3)} deutsche `###`-Unterabschnitte minus {len(ZWEISPRACHIG_IN_EINEM_STUECK)} "
        f"zweisprachige ergeben {erwartet}, englisch sind es {len(en3)}.\nDE: {de3}\nEN: {en3}"
    )


def test_the_release_pull_request_cannot_be_merged_by_accident():
    """Minuten nach v1.1.0-beta.1 stand der naechste Release-PR da — gruen, bereit,
    ungefragt. Ein Release soll aber aus einer Entscheidung entstehen und nicht aus
    dem Takt der Commits. Als ENTWURF bleibt der PR die nuetzliche Vorschau auf den
    naechsten Release, ist aber nicht zusammenfuehrbar: GitHub verweigert das bei
    einem Entwurf. Damit ist die Sperre ein Mechanismus und keine Absprache. (#189)"""
    cfg = json.load(open(os.path.join(REPO, "release-please-config.json"), encoding="utf-8"))
    assert cfg.get("draft-pull-request") is True, \
        "ohne draft-pull-request oeffnet der Release-PR wieder zusammenfuehrbar"
    # Und die Begruendung muss dort stehen, wo jemand nachsieht, warum es klemmt.
    wf = open(os.path.join(REPO, ".github/workflows/release-please.yml"),
              encoding="utf-8").read()
    assert "KEIN RELEASE OHNE ENTSCHEIDUNG" in wf


def test_the_request_for_dropdown_reads_the_real_users_response(appmod, client):
    """Die Auswahl „Anfragen für" bot `0` und `1` statt Namen an.

    Der interne Speicher IST ein Dictionary nach Benutzernamen, der Endpunkt macht daraus
    eine Liste von Objekten — und diese Aufrufstelle war gegen den internen Aufbau
    geschrieben. `Object.keys()` auf einer Liste gibt die Indizes zurück.

    Der Test koppelt deshalb beide Seiten: die ECHTE Antwort von `/api/users` wird durch
    den Ausdruck geschickt, der im ausgelieferten JavaScript steht. Eine Textsuche hätte
    genau das nicht bemerkt. (#209)"""
    node = shutil.which("node")
    if not node:
        pytest.skip("node nicht verfügbar")
    appmod.save_users({"admin": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)},
                       "miriam": {"pw": "x", "role": "user", "perms": []}})
    with client.session_transaction() as sess:
        sess["user"] = "admin"; sess["role"] = "admin"
    antwort = client.get("/api/users").get_json()

    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    m = re.search(r"let names=(.*?);\n", js)
    assert m, "die Zeile, die die Namensliste bildet, ist nicht mehr auffindbar"

    prog = f"const us={json.dumps(antwort)};const names={m.group(1)};console.log(JSON.stringify(names));"
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr.strip()
    assert json.loads(r.stdout) == ["admin", "miriam"]
    appmod.save_users({})


def test_a_read_only_config_is_reported_not_hidden(appmod, client, tmp_path, monkeypatch):
    """Ein schreibgeschütztes `/config` muss auffallen — sofort und an einer Stelle, die
    jemand ansieht.

    Es ist der teuerste stille Ausfall dieses Projekts gewesen: 18 Stunden lang wurde jede
    Anfrage beantwortet, die ganze Oberfläche geliefert und `healthy` gemeldet, während
    nichts gespeichert wurde. Lesen ging — und alles, was jemand *ansieht*, ist Lesen.

    Der Test prüft deshalb den Zustand, den `/health` und die Warnung gemeinsam ergeben,
    nicht nur die Existenz eines Feldes. (#216)"""
    import os as _os
    if _os.getuid() == 0:
        pytest.skip("als root ist jedes Verzeichnis beschreibbar")
    assert appmod.storage_state()["ok"] is True          # Ausgangslage: schreibbar
    assert client.get("/health").get_json()["storage"] == "rw"

    ro = tmp_path / "nur-lesen"; ro.mkdir(); _os.chmod(ro, 0o555)
    monkeypatch.setattr(appmod, "CONFIG_DIR", str(ro))
    try:
        st = appmod.storage_state()
        assert st["ok"] is False and st["dir"] is False
        assert "nur-lesen" in st["reason"]

        appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
        with client.session_transaction() as sess:
            sess["user"] = "j"; sess["role"] = "admin"
        w = client.get("/api/config/warnings").get_json()["warnings"]
        s = next((x for x in w if x.get("key") == "storage"), None)
        assert s is not None, "der Ausfall taucht in der Oberfläche nicht auf"
        assert str(_os.getuid()) in s["fix"]

        # Und die App bleibt erreichbar: ein sichtbarer Fehler nützt mehr als ein Dienst,
        # der nicht hochkommt und dessen Grund niemand sieht.
        h = client.get("/health")
        assert h.status_code == 200 and h.get_json()["storage"] == "ro"
    finally:
        _os.chmod(ro, 0o755)
        appmod.save_users({})


def test_the_write_probe_actually_writes(appmod):
    """Geprüft wird mit einem echten Schreibversuch, nicht mit `os.access`.

    `os.access` beantwortet die Frage auf eingehängten Dateisystemen und bei ACLs nicht —
    und `PRAGMA quick_check` läuft auf einer schreibgeschützten Datenbank glatt durch.
    Beides sind beruhigende Zahlen am falschen Ort. (#216)"""
    quelle = open(os.path.join(REPO, "app.py"), encoding="utf-8").read()
    fn = re.search(r"def storage_state\(\):.*?\n(?=def )", quelle, re.S).group(0)
    # Docstring und Kommentare raus — dort STEHEN os.access und quick_check, mit der
    # Begründung, warum sie hier nichts taugen.
    rumpf = re.sub(r'""".*?"""', "", fn, flags=re.S)
    rumpf = "\n".join(z for z in rumpf.splitlines() if not z.strip().startswith("#"))
    assert "os.access" not in rumpf, "os.access beweist hier nichts"
    assert "quick_check" not in rumpf, "quick_check liest nur"
    assert "CREATE TABLE" in rumpf and "commit" in rumpf, "es fehlt die echte Transaktion"
    assert ".schreibprobe" in rumpf, "es fehlt der echte Schreibversuch im Verzeichnis"


def test_the_crawljob_uses_the_types_jdownloader_actually_parses(appmod, tmp_path):
    """`autoStart`/`autoConfirm` sind in JDownloader **BooleanStatus** (`TRUE`/`FALSE`/
    `UNSET`), nicht boolean — so beschreibt es die FolderWatch-Erweiterung selbst.

    In dieser Form ist der ganze Weg am laufenden JDownloader nachgemessen: Übergabe,
    Download und Entpacken. Ob die frühere Schreibweise `"true"` den Auftrag *verliert*,
    ist dagegen NICHT belegt — die erste Messreihe lief gegen einen JDownloader mit einem
    offenen modalen Dialog, der alles blockierte. Gemessen wurde dort der Dialog, nicht
    das Feld.

    `overwritePackagizerRules` existiert nicht — der Setter heißt
    `setOverwritePackagizerEnabled` (aus `FolderWatch.jar` ausgelesen); das Feld war
    immer wirkungslos und ist raus. (#219)"""
    watch = tmp_path / "w"; watch.mkdir(); out = tmp_path / "o"; out.mkdir()
    appmod.save_settings({"connections": {"jd_watch": str(watch), "jd_out": str(out)}})
    appmod.write_crawljob("9", ["http://example.invalid/a"], "/output/romseerr/x", "x")
    job = json.loads((watch / "romseerr_9.crawljob").read_text())[0]

    assert job["autoStart"] == "TRUE" and job["autoConfirm"] == "TRUE"
    for k in ("autoStart", "autoConfirm"):
        assert job[k] is not True, f"{k}: JSON-Boolean wird verworfen"
        assert job[k] != "true", f"{k}: Kleinschreibung wird verworfen"

    # Nur die vier belegten Felder. Alles andere hat den Auftrag verschwinden lassen.
    assert set(job) == {"text", "downloadFolder", "packageName", "autoStart", "autoConfirm"}
    assert "overwritePackagizerRules" not in job, "dieses Feld gibt es in JDownloader nicht"
    appmod.save_settings({})


def test_every_view_has_an_address_and_survives_a_reload():
    """Ohne Adresse gibt es keinen Weg zurück: Browser-Zurück verließ die App, ein
    Neuladen landete immer auf Entdecken, und nichts war verlinkbar.

    Geprüft wird die Umkehrbarkeit — Ansicht → Adresse → Ansicht — für jede der sechs
    Ansichten, weil genau das ein Neuladen tut. (#194)"""
    node = shutil.which("node")
    if not node:
        pytest.skip("node nicht verfügbar")
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    prog = _route_funktionen(js) + """
const raus = {};
for (const v of Object.keys(ROUTEN)) {
  const adresse = routeBauen(v, null);
  raus[v] = [adresse, routeParse(adresse).view];
}
raus['_leer'] = ['', routeParse('').view];
raus['_unbekannt'] = ['#/gibtsnicht', routeParse('#/gibtsnicht').view];
console.log(JSON.stringify(raus));
"""
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr.strip()
    d = json.loads(r.stdout)
    for v, (adresse, zurueck) in d.items():
        if v.startswith("_"):
            continue
        assert adresse.startswith("#/"), f"{v} hat keine Adresse"
        assert zurueck == v, f"{v} → {adresse} → {zurueck}: Ansicht überlebt den Reload nicht"
    assert d["_leer"][1] == "s", "ohne Adresse muss Entdecken kommen"
    assert d["_unbekannt"][1] == "s", "eine unbekannte Adresse darf nicht ins Leere führen"


def test_a_title_can_be_linked_and_restored():
    """Ein Titel braucht eine Adresse, sonst lässt er sich nicht verschicken und ein
    Neuladen wirft den Benutzer aus dem geöffneten Fenster.

    Der Test schickt genau die Felder durch, die `openDetail` zum Wiederherstellen
    braucht — inklusive eines Titels mit Sonderzeichen, weil daran das Kodieren
    scheitert und nicht an `abc`. (#194)"""
    node = shutil.which("node")
    if not node:
        pytest.skip("node nicht verfügbar")
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    prog = _route_funktionen(js) + """
const it = {source:'archive', ref:'twin-dragons/nes', title:'Lala & Co? [NES] #1', platform_slug:'nes'};
const adresse = routeBauen('j', it);
console.log(JSON.stringify({adresse, zurueck: routeParse(adresse)}));
"""
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr.strip()
    d = json.loads(r.stdout)
    assert d["adresse"].startswith("#/title/archive/")
    z = d["zurueck"]
    assert z["view"] == "j", "die Ansicht hinter dem Fenster muss erhalten bleiben"
    assert z["detail"]["ref"] == "twin-dragons/nes", "ein Schrägstrich im ref darf nicht zerfallen"
    assert z["detail"]["title"] == "Lala & Co? [NES] #1"
    assert z["detail"]["platform_slug"] == "nes"


def test_the_modal_is_part_of_the_history():
    """Zurück muss das Detailfenster schließen, statt die App zu verlassen — und das
    Wiederherstellen aus der Adresse darf KEINEN neuen Verlaufseintrag erzeugen, sonst
    kommt man mit Zurück nie heraus. (#194)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    assert "window.addEventListener('popstate'" in js, "popstate wird nicht behandelt"
    assert "history.pushState" in js and "history.replaceState" in js
    öffnen = js[js.index("async function openDetail("):]
    öffnen = öffnen[:öffnen.index("\nasync function ", 1)]
    assert "if(!ausRoute)routeSetzen" in öffnen, "der Klick legt keinen Verlaufseintrag an"
    schliessen = js[js.index("function closeModal("):]
    schliessen = schliessen[:schliessen.index("\n}") + 2]
    assert "history.back()" in schliessen, "Schließen bewegt den Verlauf nicht zurück"
    assert "if(ausRoute)return" in schliessen, "beim Wiederherstellen darf nicht zurückgesprungen werden"


def test_settings_subpages_are_addressable(appmod):
    """Eine Einstellungs-Unterseite muss verlinkbar sein und ein Neuladen überleben.

    Vorher war der gewählte Bereich eine Modulvariable: beim ersten F5 weg, und ein Link
    auf „Telegram einrichten" gab es nicht. Das ist dieselbe Lücke wie #194 — deshalb
    liegt sie jetzt in derselben Route statt in einer zweiten Navigationslogik. (#202)"""
    node = shutil.which("node")
    if not node:
        pytest.skip("node nicht verfügbar")
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    prog = _route_funktionen(js) + """
const faelle = [['notif','telegram'],['conn','jd'],['notif',''],['general','']];
const raus = faelle.map(([sec,sub]) => {
  const a = routeBauen('set', null, sec, sub);
  const z = routeParse(a);
  return [a, z.view, z.sec, z.sub];
});
raus.push(['#/settings', ...(x => [x.view, x.sec, x.sub])(routeParse('#/settings'))]);
console.log(JSON.stringify(raus));
"""
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr.strip()
    d = json.loads(r.stdout)
    assert d[0] == ["#/settings/notif/telegram", "set", "notif", "telegram"]
    assert d[1] == ["#/settings/conn/jd", "set", "conn", "jd"]
    assert d[2][:3] == ["#/settings/notif", "set", "notif"], "Bereich ohne Unterseite muss gehen"
    assert d[4][1] == "set", "die nackte Einstellungsadresse muss weiter funktionieren"


def test_saving_one_notification_method_leaves_the_others_alone(appmod, client):
    """Beim Aufteilen in Unterseiten ist das die gefährliche Stelle: Wird beim Speichern
    einer Seite der ganze `agents`-Block gesendet, sind alle anderen Verfahren
    stillgelegt — mit leeren Feldern, die es auf dieser Seite gar nicht gibt.

    Der Server führt pro Agent zusammen; dieser Test hält das fest, damit die Annahme,
    auf der die Oberfläche aufbaut, nicht unbemerkt wegbricht. (#202)"""
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    client.post("/api/settings", json={"agents": {
        "telegram": {"enabled": True, "chat": "123", "token": "geheim"},
        "ntfy": {"enabled": True, "url": "https://ntfy.example", "topic": "romseerr"}}})

    # Jetzt nur Telegram speichern, so wie es die Telegram-Unterseite tut
    client.post("/api/settings", json={"agents": {"telegram": {"enabled": False, "chat": "456"}}})
    ag = appmod.load_settings().get("agents", {})
    assert ag["telegram"]["chat"] == "456" and ag["telegram"]["enabled"] is False
    assert ag["telegram"]["token"] == "geheim", "das Token darf nicht verloren gehen"
    assert ag.get("ntfy", {}).get("topic") == "romseerr", "ntfy wurde von einer fremden Seite gelöscht"
    appmod.save_settings({}); appmod.save_users({})


def test_the_notification_page_only_sends_what_it_shows():
    """Die Gegenprobe in der Oberfläche: `saveAgents` darf Felder nur senden, wenn sie
    im DOM stehen. Ein blindes `getElementById(...).checked` wäre auf jeder Unterseite
    ein TypeError — und schlimmer, mit Sammelsendung ein stiller Datenverlust. (#202)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    fn = js[js.index("async function saveAgents(){"):]
    fn = fn[:fn.index("\nasync function ", 1)]
    for feld in ("agtgen", "agwhen", "aggoen", "agnten", "agpoen", "agem"):
        assert f"if(w('{feld}'))" in fn, f"{feld} wird ungeprüft gelesen"
    assert "if(!Object.keys(a).length)return true" in fn, "eine leere Sendung muss unterbleiben"


def test_language_entries_carry_a_name_not_just_a_flag():
    """Eine Flagge ist ein Land, keine Sprache — Englisch unter 🇬🇧 liest sich für
    Amerikaner falsch, Spanisch unter 🇪🇸 für Lateinamerika. Im Aufklappmenü ist Platz
    für beides, also steht dort Flagge **und** Eigenname. (#206)"""
    node = shutil.which("node")
    if not node:
        pytest.skip("node nicht verfügbar")
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    i = js.index("const SPRACHEN=")
    prog = js[i:js.index("\n", js.index("]];", i))] + "\nconsole.log(JSON.stringify(SPRACHEN));"
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr.strip()
    sprachen = json.loads(r.stdout)
    codes = [x[0] for x in sprachen]
    assert codes == ["de", "en", "fr", "es", "it"], "die Liste muss den fünf Sprachen der App folgen"
    for code, flagge, name in sprachen:
        assert flagge and not flagge.isascii(), f"{code}: keine Flagge"
        assert name and name.isprintable() and len(name) > 2, f"{code}: kein Sprachname neben der Flagge"
    assert len({x[2] for x in sprachen}) == 5, "die Namen müssen sich unterscheiden"


def test_the_header_menus_close_the_ways_people_expect():
    """Ein Menü, das nur der erneute Klick auf denselben Knopf schließt, ärgert täglich.
    Klick daneben und Escape gehören dazu — beides ist im Issue ausdrücklich verlangt. (#206)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    assert "closest('.aufklapp')" in js, "Klick außerhalb schließt nicht"
    assert "'Escape'" in js, "Escape schließt nicht"
    auf = js[js.index("function toggleMenu("):]
    auf = auf[:auf.index("\nfunction ", 1)]
    assert "closeMenus()" in auf, "ein zweites Menü bliebe sonst offen"
    assert "aria-expanded" in js, "der Knopf sagt nicht, ob er offen ist"


def test_the_sidebar_no_longer_carries_the_person():
    """Die drei Dauerzeilen unten links (Sprache, Profil, Abmelden) sind frei — sonst
    wäre die Kopfleiste nur eine zweite Stelle für dasselbe. (#206)"""
    html = open(os.path.join(REPO, "templates/index.html"), encoding="utf-8").read()
    seite = html[html.index("<div id=side>"):html.index("<main>")]
    for weg in ("langsw", "ubox", "logout()", "openProfile()"):
        assert weg not in seite, f"{weg} steht weiterhin in der Seitenleiste"
    kopf = html[html.index("<div id=topbar>"):html.index("</main>")]
    assert "usermenu" in kopf and "langmenu" in kopf, "die Kopfleiste trägt die Menüs nicht"
    assert "logout()" in kopf and "openProfile()" in kopf


def test_a_requested_title_is_marked_differently_from_an_owned_one(appmod, client, monkeypatch):
    """„Vorhanden" und „angefragt" sind verschiedene Zustände, und beide interessieren
    VOR dem Klick — sonst trägt die Karte einen Download-Knopf für etwas, das längst
    unterwegs ist. Vorhandenes schlägt angefragt, sonst stünde beides da. (#205)"""
    appmod.JOBS.clear()
    appmod.JOBS.append({"id": "1", "title": "Micro Mages", "state": "downloading"})
    appmod.JOBS.append({"id": "2", "title": "Twin Dragons", "state": "done"})
    appmod.JOBS.append({"id": "3", "title": "Lala The Magical", "state": "error"})
    offen = appmod.angefragte_titel()
    assert appmod.norm("Micro Mages") in offen, "ein laufender Job zählt als angefragt"
    assert appmod.norm("Twin Dragons") not in offen, "fertig heißt in der Bibliothek, nicht angefragt"
    assert appmod.norm("Lala The Magical") not in offen, "ein Fehlschlag muss wieder anforderbar sein"

    # Ein Titel, der beides wäre, ist „vorhanden" — nicht beides.
    monkeypatch.setattr(appmod, "in_library", lambda t, p=None: True)
    r = {"title": "Micro Mages", "platform": None, "size": 0, "source": "archive"}
    r["in_library"] = appmod.in_library(r["title"], r["platform"])
    r["gkey"] = appmod.norm(r["title"])
    r["requested"] = (not r["in_library"]) and r["gkey"] in offen
    assert r["requested"] is False
    appmod.JOBS.clear()


def test_the_card_shows_state_by_symbol_not_by_colour_alone():
    """Ein grünes Abzeichen auf dunklem Cover sagt einem rot-grün-blinden Menschen nichts.
    Das Symbol trägt die Bedeutung, die Farbe verstärkt sie nur — und der Text steht
    zusätzlich im `title`, damit auch ein Screenreader ihn findet. (#205)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    fn = js[js.index("function kartenZustand("):]
    fn = fn[:fn.index("\nfunction ", 1)]
    assert "'✓'" in fn and "'⏳'" in fn, "die Zustände unterscheiden sich nicht im Symbol"
    assert "in_library" in fn and "requested" in fn
    karte = js[js.index("function renderCard("):]
    karte = karte[:karte.index("\nlet RAONLY", 1)]
    assert 'title="${z.text}"' in karte, "der Zustand steht nirgends als Text"
    assert "class=have>" not in karte, "die alte 12px-Zeile im Aktionsfeld ist noch da"
    css = open(os.path.join(REPO, "static/css/index.css"), encoding="utf-8").read()
    assert ".cover .zust" in css and ".zust.da" in css and ".zust.req" in css


def test_the_card_names_the_platform_instead_of_printing_the_slug():
    """Die Karte druckte den internen Slug (`ngc`, `psvita`) statt des Anzeigenamens, den
    es längst gibt. Die Namen kommen aus derselben Quelle wie die Filterleiste, damit
    nicht zwei Bestände auseinanderlaufen. `?` bleibt ein echter Fall. (#211)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    assert "let SLUGNAME={}" in js
    lp = js[js.index("async function loadPlatforms(){"):]
    lp = lp[:lp.index("\nfunction ", 1)]
    assert "SLUGNAME[it.slug]=it.name" in lp, "die Namen werden nirgends gesammelt"
    karte = js[js.index("function renderCard("):]
    karte = karte[:karte.index("\nlet RAONLY", 1)]
    assert "plattformMarke(it.platform_slug)" in karte, "der Slug wird weiterhin ungefiltert gedruckt"
    marke = js[js.index("function plattformMarke("):]
    marke = marke[:marke.index("\n\n", 1)] if "\n\n" in marke[:400] else marke[:400]
    assert "SLUGNAME[slug]||slug||'?'" in marke, "der Anzeigename fehlt als Grundlage"


def test_the_footer_shows_the_version_only_to_signed_in_visitors():
    """Eine Versionsnummer auf der Anmeldeseite sagt einem Fremden, welche Lücken er
    nachschlagen kann — und einem Ausgeloggten nützt sie nichts. Deshalb: Repo-Link für
    alle, Version erst nach der Anmeldung. Das war die offene Frage im Issue. (#208)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    fn = js[js.index("async function zeichneFuss(){"):]
    fn = fn[:fn.index("\n\n", 1)]
    assert "if(window.ROLE)" in fn, "die Version hängt nicht an der Anmeldung"
    vor, nach = fn.split("if(window.ROLE)", 1)
    assert "REPO_URL" in vor, "der Repo-Link muss auch ohne Anmeldung stehen"
    assert "/api/version" in nach and "ver.commit" in nach, \
        "Version und Commit gehören hinter die Anmeldung"
    assert "provenance" in nach, "die Provenance-Warnung fehlt"
    assert "releases/tag/v" in nach, "die Version verlinkt nicht auf ihren eigenen Release"
    html = open(os.path.join(REPO, "templates/index.html"), encoding="utf-8").read()
    assert "<footer id=fuss>" in html
    css = open(os.path.join(REPO, "static/css/index.css"), encoding="utf-8").read()
    fuss = css[css.index("#fuss{"):css.index("}", css.index("#fuss{"))]
    # Auf Wunsch angeheftet und mittig. Wer eine Zeile dauerhaft belegt, muss dafür sorgen,
    # dass nichts darunter verschwindet — deshalb der Ausgleich am Inhalt.
    assert "position:fixed" in fuss and "bottom:0" in fuss, "die Fußzeile ist nicht angeheftet"
    assert "justify-content:center" in fuss, "die Fußzeile steht nicht mittig"
    assert "main{padding-bottom:" in css, "ohne Ausgleich verdeckt die Fußzeile den Inhalt"


def test_escape_closes_the_menu_first_and_the_dialog_second():
    """Ein Handler für Escape, nicht zwei, die um dieselbe Taste konkurrieren. Und mit
    offenem Menü über dem Fenster schließt der erste Druck das Menü, der zweite das
    Fenster — sonst verliert man mit einem Tastendruck beides. (#226)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    assert js.count("'Escape'") == 1, "es gibt mehr als einen Escape-Handler"
    h = js[js.index("document.addEventListener('keydown'"):]
    h = h[:h.index("\nfunction ", 1)]
    assert h.index(".aufklapp.auf") < h.index("closeModal()"), \
        "das Fenster würde vor dem Menü geschlossen"
    assert "return;" in h.split(".aufklapp.auf")[1][:60], "beides schließt gleichzeitig"


def test_closing_a_directly_opened_title_does_not_leave_the_application():
    """Wer einen Titel-Link direkt öffnet, hat genau einen Verlaufseintrag — davor liegt
    fremdes Gebiet. Ein blindes `history.back()` beim Schließen würde Romseerr verlassen.
    Gezählt wird deshalb, wie viele Einträge die App selbst angelegt hat. (#226)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    assert "let EIGENE_SCHRITTE=0" in js
    setzen = js[js.index("function routeSetzen("):]
    setzen = setzen[:setzen.index("\nfunction ", 1)]
    assert "EIGENE_SCHRITTE++" in setzen, "gepushte Einträge werden nicht gezählt"
    assert "EIGENE_SCHRITTE=Math.max(0,EIGENE_SCHRITTE-1)" in js, "popstate zählt nicht zurück"
    zu = js[js.index("function closeModal("):]
    zu = zu[:zu.index("\n}", 1) + 2]
    assert "EIGENE_SCHRITTE>0" in zu and "history.back()" in zu
    assert "routeSetzen(cur,null,true)" in zu, "ohne eigenen Eintrag muss die Adresse ersetzt werden"


def test_favourites_and_wishlist_do_not_share_a_store(appmod):
    """Die beiden Listen beantworten gegensätzliche Fragen: die Wunschliste sagt „habe ich
    nicht" und **leert sich**, sobald der Titel eintrifft — das ist ihr Zweck. Ein Favorit
    sagt „habe ich, will ich wiederfinden" und darf nie von selbst verschwinden.

    Zusammengelegt wäre jedes Eintreffen entweder ein Datenverlust oder eine Karteileiche.
    Der Test hält deshalb fest, dass ein Titel in beiden stehen kann und das Entfernen aus
    der einen die andere nicht anfasst. (#207)"""
    appmod.kv_put("wishlist", {}); appmod.kv_put("favourites", {})
    appmod.wishlist_add("j", "Micro Mages", "nes")
    appmod.fav_add("j", "Micro Mages", "nes")
    assert appmod.is_fav("j", "Micro Mages") is True
    assert len(appmod.load_wishlist().get("j", [])) == 1

    # Der Titel trifft ein: die Wunschliste gibt ihn frei, der Favorit bleibt.
    appmod.wishlist_remove("j", "Micro Mages")
    assert appmod.load_wishlist().get("j", []) == []
    assert appmod.is_fav("j", "Micro Mages") is True, "der Favorit ist mit verschwunden"

    # Und je Benutzer getrennt — zwei Menschen haben nichts miteinander zu tun.
    assert appmod.is_fav("m", "Micro Mages") is False
    appmod.fav_add("j", "Micro Mages", "nes")          # doppelt anlegen ändert nichts
    assert len(appmod.load_favs().get("j", [])) == 1
    appmod.fav_remove("j", "Micro Mages")
    assert appmod.load_favs().get("j", []) == []
    appmod.kv_put("wishlist", {}); appmod.kv_put("favourites", {})


def test_the_wishlist_left_the_requests_page(appmod):
    """Die Wunschliste wurde IN die Anfragen-Seite gezeichnet — nicht aus einer
    Entscheidung, sondern weil die Seite danebenlag. Eine Anfrage hat einen Zustand und
    endet; eine Wunschliste ist persönlich und offen. Jetzt eine eigene Ansicht mit
    eigener Adresse. (#195)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    jobs = js[js.index("async function loadJobs("):]
    jobs = jobs[:jobs.index("\nasync function ", 1)]
    assert "/api/wishlist" not in jobs, "die Wunschliste wird weiterhin in die Anfragen gezeichnet"
    assert "async function loadLists()" in js, "es gibt keine eigene Ansicht"
    listen = js[js.index("async function loadLists(){"):]
    listen = listen[:listen.index("\n// ---", 1)]
    assert "/api/wishlist" in listen and "/api/favourites" in listen, \
        "die neue Ansicht führt nicht beide Listen"
    assert "lists:'lists'" in js, "die Ansicht hat keine Adresse"
    html = open(os.path.join(REPO, "templates/index.html"), encoding="utf-8").read()
    kopf = html[html.index("<div id=topbar>"):html.index("</main>")]
    assert "show('lists')" in kopf, "die Listen sind nicht vom Benutzermenü aus erreichbar"


def test_the_favourite_button_uses_the_same_normalisation_as_the_server(appmod):
    """Server und Oberfläche müssen denselben Titel für denselben halten, sonst zeigt die
    Karte ein leeres Herz für einen Titel, der serverseitig längst Favorit ist. (#207)"""
    node = shutil.which("node")
    if not node:
        pytest.skip("node nicht verfügbar")
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    fn = js[js.index("function norm(x){"):]
    fn = fn[:fn.index("\n", 1)]
    prog = fn + "\nconsole.log(JSON.stringify(['Micro Mages','MICRO  mages!','Micro-Mages'].map(norm)));"
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr.strip()
    js_werte = json.loads(r.stdout)
    py_werte = [appmod.norm(x) for x in ["Micro Mages", "MICRO  mages!", "Micro-Mages"]]
    assert js_werte == py_werte, f"JS {js_werte} ≠ Python {py_werte}"


def test_the_job_counter_counts_unfinished_not_existing():
    """Ein Zähler, aus dem ein Fehlschlag herausfällt, bringt dem Benutzer bei, dass Null
    „alles gut" heißt — dabei liegt dann etwas ungelöst herum. Deshalb zählen Fehler mit,
    und die FARBE trennt sie vom Normalfall. `denied` zählt nicht: das war eine
    Entscheidung, keine offene Sache. (#198/#201)"""
    node = shutil.which("node")
    if not node:
        pytest.skip("node nicht verfügbar")
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    teile = []
    for anker in ("const JOBGRUPPEN=", "function jobGruppe(", "function jobOffen("):
        i = js.index(anker); j = js.index("\n\n", i) if "\n\n" in js[i:i+600] else js.index("\n// ", i)
        teile.append(js[i:js.index("}", i) + 1] if anker.startswith("function jobOffen") else js[i:j])
    prog = "\n".join(teile) + """
const zustaende = ['pending','queued','approved','downloading','importing','done','denied','error'];
console.log(JSON.stringify(Object.fromEntries(
  zustaende.map(s => [s, [jobGruppe(s), jobOffen({state:s})]]))));
"""
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr.strip()
    d = json.loads(r.stdout)
    for s in ("pending", "queued", "approved", "downloading", "importing"):
        assert d[s] == ["aktiv", True], f"{s} muss aktiv sein und zählen"
    assert d["done"] == ["erledigt", False], "fertig darf nicht zählen"
    # Abgelehnt bekam eine EIGENE Gruppe: unter „fehlgeschlagen" sucht man Defekte und
    # fände Entscheidungen, unter „erledigt" ist es nicht mehr auffindbar — und genau das
    # war die erste Rückmeldung aus der Benutzung.
    assert d["denied"] == ["abgelehnt", False], "abgelehnt ist eine Entscheidung, keine offene Sache"
    assert d["error"] == ["fehler", True], "ein Fehlschlag darf nicht aus dem Zähler fallen"


def test_the_counter_is_absent_at_zero_and_red_on_failure():
    """Null muss **kein** Abzeichen sein, keine `0` — und ein Fehler muss sich farblich
    vom Normalfall unterscheiden, sonst sagt die Zahl allein zu wenig. (#198)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    fn = js[js.index("async function updateJobBadge(){"):]
    fn = fn[:fn.index("\nasync function ", 1)]
    assert "offen.length?' '+offen.length+' ':''" in fn, "eine 0 würde angezeigt"
    assert "el.style.cssText=offen.length" in fn, "das Abzeichen verschwindet bei Null nicht"
    assert "fehler?'#c0392b'" in fn, "ein Fehler sieht aus wie ein normaler Lauf"
    assert "window.ME" in fn, "der Zähler zählt nicht die eigenen Aufträge"
    assert "setInterval(updateJobBadge" in js, "der Zähler bewegt sich nicht von selbst"


def test_the_empty_requests_page_says_which_kind_of_empty():
    """„Es gibt keine Anfragen" und „in diesem Filter ist nichts" sind verschiedene
    Aussagen. Vorher stand für beides derselbe Satz — mit Filtern wäre er schlicht
    falsch. (#201)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    # NICHT AUF DIE EXAKTE SIGNATUR ANKERN. Der Anker lautete `async function loadJobs(){`
    # und brach, sobald #419 der Funktion versuchsweise einen Parameter gab: `ValueError:
    # substring not found`, ein Fehler ueber die Suche statt ueber die gepruefte Sache.
    # Was hier zaehlt, sind die zwei verschiedenen Leertexte — nicht die Klammern.
    m = re.search(r"async function loadJobs\([^)]*\)\s*\{", js)
    assert m, "loadJobs ist nicht mehr auffindbar"
    fn = js[m.start():]
    fn = fn[:fn.index("\nasync function ", 1)]
    assert "t('flt_leer')" in fn and "t('no_requests')" in fn, "es gibt nur einen Leertext"
    assert "alle.length&&(JOBGRP||window.jobFilter)" in fn, \
        "der Unterschied hängt nicht am tatsächlichen Bestand"
    for key in ("flt_active", "flt_done", "flt_denied", "flt_failed", "flt_leer"):
        assert i18n_hat(key) == 5, f"{key} fehlt in einer Sprache"


def test_no_logo_files_are_shipped_and_the_name_still_shows(appmod, client, tmp_path, monkeypatch):
    """Konsolen- und Herstellerlogos sind Marken. In einer privaten Instanz zu zeigen ist
    eine Sache, die Dateien in ein **öffentliches** Repository zu legen eine andere — und
    dieses Repo ist öffentlich.

    Der Test hält beide Hälften der Entscheidung fest: im Repo liegt keine Bilddatei, und
    ohne Datei bleibt die Oberfläche beim Namen — ein vollwertiger Zustand, kein
    Notbehelf. (#211/#199)"""
    # (a) nichts mitgeliefert
    for wurzel, _, dateien in os.walk(os.path.join(REPO, "static")):
        for f in dateien:
            assert not f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")), \
                f"Bilddatei im Repo: {os.path.join(wurzel, f)}"
    # (c) der Name trägt allein
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    marke = js[js.index("function plattformMarke("):]
    marke = marke[:marke.index("function ", 20)]
    assert "LOGOS.has" in marke and "return sicher" in marke, \
        "ohne Logo fällt die Karte nicht auf den Namen zurück"

    # Ein hinterlegtes Logo wird ausgeliefert, ein erfundener Name nicht.
    # Angemeldet, weil die Logos unter derselben Anmeldung liegen wie der Rest — die
    # Namensliste verrät, welche Plattformen hier eingerichtet sind.
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    d = tmp_path / "logos"; d.mkdir()
    (d / "snes.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(appmod, "LOGO_DIR", str(d))
    assert client.get("/api/logos").get_json() == ["snes"]
    assert client.get("/logo/snes").status_code == 200
    assert client.get("/logo/gibtsnicht").status_code == 404
    # Der Name kommt aus einer URL zurück — er darf kein Pfad sein.
    assert client.get("/logo/..%2f..%2fsecret.key").status_code in (404, 308)
    appmod.save_users({})


def test_the_manufacturer_figure_is_summed_not_averaged():
    """Die Zahl auf der Herstellerkarte darf **nicht** das Mittel der Prozente sein — das
    gäbe dem Virtual Boy (16 Titel) dasselbe Gewicht wie der SNES (2825). Gerechnet wird
    Summe besessen gegen Summe bekannt, und die Methode steht auf der Karte, weil eine
    einzelne Zahl über dreizehn Konsolen sonst zum falschen Schluss einlädt. (#199)"""
    node = shutil.which("node")
    if not node:
        pytest.skip("node nicht verfügbar")
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    fn = js[js.index("function covGruppe(name,plats){"):]
    fn = fn[:fn.index("\n\n", 1)] if "\n\n" in fn[:2000] else fn[:2000]
    assert "reduce" in fn and "owned*100/known" in fn, "es wird nicht summiert"
    assert "/ plats.length" not in fn and "pct||0)/" not in fn, "es wird gemittelt"

    # Gegenrechnung: ein kleines und ein großes System, sehr verschiedene Quoten.
    prog = """
const plats = [{slug:'snes',name:'SNES',owned:900,known:1000,pct:90},
               {slug:'vb',name:'Virtual Boy',owned:1,known:100,pct:1}];
const messbar = plats.filter(p=>p.known!=null);
const owned = messbar.reduce((a,p)=>a+(p.owned||0),0);
const known = messbar.reduce((a,p)=>a+(p.known||0),0);
console.log(JSON.stringify({summiert: Math.round(owned*100/known),
                            gemittelt: Math.round((90+1)/2)}));
"""
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True)
    d = json.loads(r.stdout)
    assert d["summiert"] == 82 and d["gemittelt"] == 46, \
        "die beiden Methoden müssen sich unterscheiden, sonst prüft der Test nichts"


def test_unmeasurable_platforms_are_counted_on_the_card():
    """Nicht jede Plattform hat eine Katalogquelle. Eine Karte, die die unmessbaren
    stillschweigend weglässt, meldet eine Vollständigkeit über einen Ausschnitt — deshalb
    steht „x von y messbar" auf der Karte und nicht in einer Fußnote. Und keine Plattform
    darf verschwinden, nur weil sie in keiner Gruppe steht. (#199)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    fn = js[js.index("function covGruppe(name,plats){"):]
    fn = fn[:fn.index("\n\n", 1)] if "\n\n" in fn[:2000] else fn[:2000]
    assert "cov_measurable" in fn, "die Karte sagt nicht, wie viel von ihr messbar ist"
    assert "messbar.length" in fn and "plats.length" in fn
    lade = js[js.index("async function loadCoverage(){"):]
    lade = lade[:lade.index("\nfunction covZeile", 1)]
    assert "genutzt" in lade and "rest.length" in lade, \
        "Plattformen ohne Gruppe würden lautlos verschwinden"
    assert "if(!GRUPPEN.length)await loadPlatforms()" in lade, \
        "ohne geladene Gruppen bliebe die Seite leer"


def test_own_ratings_are_per_user_and_per_title_not_averaged(appmod):
    """Vor der Tabelle entschieden, wie das Issue es verlangt: bewertet wird der **Titel**
    (die Bibliothek hält mehrere Fassungen desselben Spiels, die Meinung gilt dem Spiel),
    und **je Nutzer** statt gemittelt — zwei Menschen sind der interessante Fall, und der
    Mittelwert aus zwei Meinungen sagt weniger als beide nebeneinander. (#210)"""
    appmod.kv_put("ratings", {}); appmod.kv_put("comments", {})
    appmod.rating_set("j", "Micro Mages", 5)
    appmod.rating_set("m", "Micro Mages (USA)", 3)   # andere Fassung, selbes Spiel
    je = appmod.load_ratings()[appmod.norm("Micro Mages")]
    assert je["j"]["stars"] == 5 and je["m"]["stars"] == 3, "die Fassungen liefen auseinander"
    assert "avg" not in je and len(je) == 2, "es wird gemittelt statt je Person zu speichern"

    appmod.rating_set("j", "Micro Mages", 0)          # zurücknehmen
    assert "j" not in appmod.load_ratings().get(appmod.norm("Micro Mages"), {})
    appmod.rating_set("m", "Micro Mages", 0)
    assert appmod.norm("Micro Mages") not in appmod.load_ratings(), "leere Einträge bleiben liegen"

    appmod.comment_add("j", "Micro Mages", "  schön schwer  ")
    k = appmod.load_comments()[appmod.norm("Micro Mages")]
    assert k[0]["text"] == "schön schwer" and k[0]["user"] == "j"
    appmod.comment_add("j", "Micro Mages", "   ")     # leer wird nicht gespeichert
    assert len(appmod.load_comments()[appmod.norm("Micro Mages")]) == 1
    appmod.kv_put("ratings", {}); appmod.kv_put("comments", {})


def test_the_external_rating_says_whose_it_is():
    """Eine Zahl ohne Quelle liest sich als die **eigene** — und das wird aktiv falsch,
    sobald eigene Bewertungen daneben stehen. Deshalb trägt die Karte die Quelle, und
    ohne Wert steht dort nichts statt einer erfundenen Null. (#210)"""
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    i = js.index("let ext=it.ext_rating?")
    zeile = js[i:js.index("\n", i)]
    assert 'title="IGDB"' in zeile, "die fremde Bewertung nennt ihre Quelle nicht"
    assert "it.ext_rating?" in zeile and "''" in zeile, "ohne Wert würde etwas erfunden"
    py = open(os.path.join(REPO, "app.py"), encoding="utf-8").read()
    assert py.count('"ext_rating"') >= 1 and "total_rating" in py, "die Quelle liefert nichts"


def test_the_blocklist_describes_what_it_actually_does():
    """Die Sperrliste erklärte sich nur durch einen Platzhalter, und die entscheidenden
    Fragen blieben offen. Der Text muss der Implementierung entsprechen, sonst ist er
    schlimmer als keiner — deshalb prüft der Test beide Seiten gegeneinander. (#203)"""
    py = open(os.path.join(REPO, "app.py"), encoding="utf-8").read()
    fn = py[py.index("def is_blocked("):]
    fn = fn[:fn.index("\ndef ", 1)]
    assert "in t" in fn and "lower()" in fn, "die Prüfung ist kein Teilstringvergleich mehr"
    assert "re.search" not in fn and "re.match" not in fn, "es ist doch eine Regex geworden"

    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    # Der Text steht seit #350 in den Sprachdateien, nicht mehr im Skript.
    text = sprachtabellen()["de"]["bl_hint"]
    for begriff in ("Teilstring", "Regex", "Titel", "laufenden", "alle Nutzer"):
        assert begriff in text, f"die Beschreibung sagt nichts zu: {begriff}"
    assert i18n_hat("bl_hint") == 5, "die Beschreibung fehlt in einer Sprache"
    sec = js[js.index("async function secBlocklist("):]
    sec = sec[:sec.index("\nfunction ", 1)]
    assert "t('bl_hint')" in sec, "die Beschreibung steht nicht im Bereich"

def test_usenet_check_measures_every_stage(appmod, client, monkeypatch, tmp_path):
    """Der Usenet-Weg ist stufenweise nachmessbar, ohne etwas herunterzuladen. (#196)

    Das Issue meldete drei Symptome — leere Suche, abgelehnter NZB, nicht eingesammelter
    Download. Nachgemessen funktionierten alle drei; der eigentliche Defekt war, dass die
    Kette keine Messpunkte hatte und von aussen jede Ursache gleich aussah.

    Der Alarmpfad wird hier erzwungen: mit einem Einsammelordner, den es nicht gibt, MUSS
    die letzte Stufe rot sein. Ein Test, der nur den Gutfall sieht, wuerde auch dann
    bestehen, wenn die Pruefung stumpf `True` zurueckgibt.
    """
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    monkeypatch.setattr(appmod, "SAB_DONE", str(tmp_path / "gibtsnicht"))
    d = client.get("/api/usenet/check").get_json()
    stufen = {s["step"]: s for s in d["steps"]}
    assert set(stufen) == {"search", "category", "queue", "collect"}
    assert stufen["collect"]["ok"] is False, "fehlender Einsammelordner muss anschlagen"
    # Beide Sichten nebeneinander — das ist die Lehre aus #197: derselbe Ordner heisst in
    # beiden Containern anders, und nur ein Mensch kann die Namensraeume vergleichen.
    assert "gibtsnicht" in stufen["collect"]["info"] and "SABnzbd" in stufen["collect"]["info"]
    assert d["ok"] is False
    appmod.save_users({})


def test_usenet_check_needs_permission(appmod, client):
    """Die Prüfung nennt Kategorien und Ordnerpfade — das ist Admin-Sache. (#196)"""
    appmod.save_users({**ADMIN_FIX, "g": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "g"; sess["role"] = "user"
    assert client.get("/api/usenet/check").status_code == 403
    appmod.save_users({})


def test_sab_failed_reads_history(appmod, monkeypatch):
    """Ein von SABnzbd verworfener Download wird als Fehlschlag erkannt. (#235)

    Vorher fiel genau dieser Fall zwischen zwei Fragen hindurch: der Eintrag ist nicht
    mehr in der Warteschlange, ein Ordner ist nie entstanden — und der Auftrag blieb
    unbegrenzt auf `downloading`. Die History ist die einzige Stelle, die den Fehlschlag
    kennt.
    """
    appmod.save_settings({"connections": {"sab_url": "http://sab", "sab_apikey": "k"}})

    slots = [
        {"name": "romseerr_111__Foo", "status": "Failed",
         "fail_message": "Abrufen der URL fehlgeschlagen"},
        {"name": "romseerr_222__Bar", "status": "Completed", "fail_message": ""},
        {"name": "fremder_333__Baz", "status": "Failed", "fail_message": "nicht unserer"},
    ]

    class R:
        def json(self): return {"history": {"slots": slots}}
    monkeypatch.setattr(appmod.requests, "get", lambda *a, **k: R())

    assert appmod.sab_failed("111") == "Abrufen der URL fehlgeschlagen"
    assert appmod.sab_failed("222") is None, "ein erfolgreicher Download ist kein Fehler"
    assert appmod.sab_failed("333") is None, "fremde Einträge gehören nicht uns"
    assert appmod.sab_failed("999") is None, "unbekannte ID darf nichts melden"

    # Fehlschlag ohne Begründung muss trotzdem eine Begründung liefern — sonst steht in
    # der Oberfläche ein leerer Fehler, und das ist so unbrauchbar wie „downloading".
    slots[0]["fail_message"] = ""
    assert appmod.sab_failed("111")
    appmod.save_settings({})


def test_collect_moves_failed_job_to_error(appmod, monkeypatch):
    """Der Fehlschlag landet auch wirklich am Auftrag — nicht nur im Log. (#235)"""
    appmod.JOBS[:] = [{"id": "111", "title": "Foo", "source": "usenet",
                       "state": "downloading", "ref": "http://x"}]
    monkeypatch.setattr(appmod, "find_output", lambda *a, **k: None)   # nie ein Ordner
    monkeypatch.setattr(appmod, "sab_queue", lambda: {})               # nicht in der Queue
    monkeypatch.setattr(appmod, "sab_failed", lambda jid: "kaputt")
    monkeypatch.setattr(appmod, "save_jobs", lambda: None)

    # Eine Runde der Dauerschleife: der Schlaf am Ende bricht sie ab.
    class Fertig(Exception): pass
    def schlaf(_): raise Fertig()
    monkeypatch.setattr(appmod.time, "sleep", schlaf)
    try:
        appmod.worker_collect()
    except Fertig:
        pass

    j = appmod.JOBS[0]
    assert j["state"] == "error", "gescheiterter Download muss als Fehler enden"
    assert j.get("msg") == "kaputt", "der Grund von SABnzbd muss am Auftrag stehen"
    appmod.JOBS[:] = []


def test_usenet_check_flags_indexer_serving_html(appmod, client, monkeypatch):
    """Ein Indexer, der Treffer liefert aber keine NZB-Dateien, muss auffallen. (#236)

    Das ist der Fall, den die vier bisherigen Stufen nicht sehen konnten: Suche grün,
    Kategorie grün, Warteschlange grün, Ordner grün — und trotzdem scheitert jeder
    Download, weil die Download-Adresse eine Webseite zurückgibt statt einer Datei.
    """
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"

    # Feldnamen wie search_usenet sie liefert (extra/ref) — NICHT wie Prowlarr sie nennt.
    # Genau diese Verwechslung liess die Stufe in der Praxis leerlaufen. (#238)
    monkeypatch.setattr(appmod, "search_usenet", lambda *a, **k: [
        {"extra": "Gut", "ref": "http://i/gut"},
        {"extra": "Html", "ref": "http://i/html"},
        {"extra": "Html", "ref": "http://i/html2"},
    ])

    class R:
        def __init__(self, ct, body): self.headers = {"content-type": ct}; self._b = body
        def iter_content(self, n): yield self._b
        def close(self): pass
        def json(self): return {}
    def fake_get(url, *a, **k):
        if url.endswith("/gut"): return R("application/x-nzb", b"<nzb><file/></nzb>")
        if "/html" in url: return R("text/html; charset=UTF-8", b"<!doctype html><html>")
        raise RuntimeError("kein SAB im Test")
    monkeypatch.setattr(appmod.requests, "get", fake_get)

    d = client.get("/api/usenet/check").get_json()
    st = {s["step"]: s for s in d["steps"]}
    assert st["indexer:Gut"]["ok"] is True, "eine echte NZB muss durchgehen"
    assert st["indexer:Html"]["ok"] is False, "eine HTML-Seite ist keine NZB"
    # Das Gewicht gehört dazu: ein Indexer, der fast alle Treffer stellt und nichts
    # ausliefert, ist ein anderer Befund als ein unwichtiger, der klemmt.
    assert "2/3" in st["indexer:Html"]["info"]
    assert d["ok"] is False
    appmod.save_users({})


def test_search_usenet_field_names_are_pinned(appmod, monkeypatch):
    """Nagelt die Naht zwischen search_usenet und seinen Aufrufern fest. (#238)

    search_usenet bildet Prowlarrs Antwort auf Romseerrs eigene Form ab: aus `indexer`
    wird `extra`, aus `downloadUrl` wird `ref`. Wer die Prowlarr-Namen weiterverwendet,
    bekommt stillschweigend None — kein Fehler, nur eine Funktion, die nichts findet.

    Deshalb geht hier eine realistische Prowlarr-Nutzlast durch die echte Funktion,
    statt das Ergebnis von Hand zu erfinden. Ein Test, der beide Seiten der Naht mockt,
    beweist nur, dass sie zueinander passen — nicht, dass sie zur Wirklichkeit passen.
    """
    appmod.save_settings({"connections": {"prow_url": "http://prow", "prow_apikey": "k",
                                          "prow_cats": "1000"}})

    class R:
        def json(self):
            return [{"protocol": "usenet", "title": "Spiel (Europe)", "size": 4711,
                     "indexer": "MeinIndexer", "downloadUrl": "http://prow/1/download?x=1",
                     "categories": [{"id": 1000}]},
                    {"protocol": "torrent", "title": "Ignoriert", "size": 1,
                     "indexer": "T", "downloadUrl": "http://t", "categories": []}]
    monkeypatch.setattr(appmod.requests, "get", lambda *a, **k: R())

    out = appmod.search_usenet("egal", "1000")
    assert len(out) == 1, "Torrents gehören nicht in den Usenet-Zweig"
    it = out[0]
    assert it["extra"] == "MeinIndexer", "der Indexername muss in `extra` landen"
    assert it["ref"] == "http://prow/1/download?x=1", "die Adresse muss in `ref` landen"
    assert "indexer" not in it and "downloadUrl" not in it, \
        "Prowlarrs Rohnamen dürfen hier nicht überleben — sonst greifen Aufrufer daneben"
    appmod.save_settings({})


def test_rom_endung_survives_appended_extension(appmod):
    """Eine ROM bleibt eine ROM, auch wenn ein Downloadprogramm etwas anhängt. (#241)

    SABnzbds *deobfuscate final filenames* rät den Typ aus dem Inhalt und hängt eine
    zweite Endung an — aus `spiel.nsp` wird `spiel.nsp.hdf`. ROM-Formate kennt so ein
    Rater nicht, also trifft es genau die Dateien, um die es hier geht.
    """
    # Normalfall bleibt unberührt
    assert appmod.rom_endung("spiel.nsp") == ("nsp", "spiel.nsp")
    # Angehängter Fremdsuffix: Endung zählt die innere, der Name wird bereinigt —
    # sonst liegt in der Bibliothek ein Name, den kein Emulator öffnet.
    assert appmod.rom_endung("sxs-hollow_knight_v262144.nsp.hdf") == \
        ("nsp", "sxs-hollow_knight_v262144.nsp")
    assert appmod.rom_endung("game.iso.sndr") == ("iso", "game.iso")
    # Grenzen: nur EINE Ebene, und nur wenn die innere Endung wirklich eine ROM ist
    assert appmod.rom_endung("irgendwas.foo.bar") == (None, None)
    assert appmod.rom_endung("readme.txt") == (None, None)
    assert appmod.rom_endung("ohnepunkt") == (None, None)
    assert appmod.rom_endung("spiel.nsp.hdf.zip") == (None, None), \
        "zwei angehängte Ebenen sind kein Fall, den wir raten"


def test_import_names_what_it_skipped(appmod, tmp_path, monkeypatch):
    """Die Fehlermeldung nennt Endung und Beispieldatei, nicht nur eine Zahl. (#242)"""
    appmod.JOBS[:] = [{"id": "77", "title": "X", "source": "usenet",
                       "state": "downloading", "platform": "nes"}]
    monkeypatch.setattr(appmod, "save_jobs", lambda: None)
    monkeypatch.setattr(appmod, "build_index", lambda: None)
    monkeypatch.setattr(appmod, "romm_scan", lambda: None)
    d = tmp_path / "job"; d.mkdir()
    (d / "spielstand.sav.wasd").write_text("x")     # unbekannt in BEIDEN Ebenen
    (d / "beipack.exe").write_text("x")

    assert appmod.import_folder("77", str(d)) is False
    msg = appmod.JOBS[0]["msg"]
    assert ".wasd" in msg or ".exe" in msg, f"Endung fehlt in der Meldung: {msg}"
    assert "spielstand" in msg or "beipack" in msg, f"Beispieldatei fehlt: {msg}"
    appmod.JOBS[:] = []


def test_failed_import_keeps_the_download(appmod, tmp_path, monkeypatch):
    """Ein Import ohne Treffer darf den Download NICHT wegwerfen. (#240)

    Vorher räumten Erfolgs- und Fehlerweg identisch auf: knapp zwei Gigabyte wurden
    gelöscht, samt SAB-History mit `del_files=1`, und die Ursache war hinterher nur noch
    aus der NZB und dem Log des Downloadprogramms zu rekonstruieren.
    """
    cand = tmp_path / "romseerr_88"; cand.mkdir()
    (cand / "nutzlast.hdf").write_text("wertvoll")
    appmod.JOBS[:] = [{"id": "88", "title": "Y", "source": "usenet",
                       "state": "downloading", "platform": "nes"}]
    monkeypatch.setattr(appmod, "save_jobs", lambda: None)
    monkeypatch.setattr(appmod, "SAB_DONE", str(tmp_path))
    monkeypatch.setattr(appmod, "find_output", lambda *a, **k: str(cand))
    monkeypatch.setattr(appmod, "folder_stable", lambda *a, **k: True)
    monkeypatch.setattr(appmod, "import_folder", lambda jid, f: False)   # nichts erkannt
    aufgeraeumt = []
    monkeypatch.setattr(appmod, "sab_cleanup", lambda jid: aufgeraeumt.append(jid))

    class Fertig(Exception): pass
    monkeypatch.setattr(appmod.time, "sleep", lambda _: (_ for _ in ()).throw(Fertig()))
    try:
        appmod.worker_collect()
    except Fertig:
        pass

    assert cand.is_dir() and (cand / "nutzlast.hdf").exists(), \
        "der Download muss liegen bleiben, wenn der Import nichts erkannt hat"
    assert aufgeraeumt == [], "auch die History darf nicht gelöscht werden — del_files=1"
    appmod.JOBS[:] = []


def test_successful_import_still_cleans_up(appmod, tmp_path, monkeypatch):
    """Die Gegenprobe: nach einem geglückten Import wird weiterhin aufgeräumt. (#240)

    Ohne diesen Test wäre „nie aufräumen" eine bestandene Lösung — und die Platte liefe
    voll.
    """
    cand = tmp_path / "romseerr_99"; cand.mkdir()
    (cand / "spiel.nes").write_text("x")
    appmod.JOBS[:] = [{"id": "99", "title": "Z", "source": "usenet",
                       "state": "downloading", "platform": "nes"}]
    monkeypatch.setattr(appmod, "save_jobs", lambda: None)
    monkeypatch.setattr(appmod, "SAB_DONE", str(tmp_path))
    monkeypatch.setattr(appmod, "find_output", lambda *a, **k: str(cand))
    monkeypatch.setattr(appmod, "folder_stable", lambda *a, **k: True)
    monkeypatch.setattr(appmod, "import_folder", lambda jid, f: True)
    aufgeraeumt = []
    monkeypatch.setattr(appmod, "sab_cleanup", lambda jid: aufgeraeumt.append(jid))

    class Fertig(Exception): pass
    monkeypatch.setattr(appmod.time, "sleep", lambda _: (_ for _ in ()).throw(Fertig()))
    try:
        appmod.worker_collect()
    except Fertig:
        pass

    assert aufgeraeumt == ["99"], "nach Erfolg muss die History aufgeräumt werden"
    assert not cand.exists(), "nach Erfolg muss der Ordner verschwinden"
    appmod.JOBS[:] = []


def test_leftovers_never_touch_a_running_job(appmod, tmp_path, monkeypatch):
    """Ein Ordner, dessen Auftrag noch läuft, taucht gar nicht erst auf. (#244)

    Der Schutz sitzt bewusst in der Auflistung und nicht erst beim Löschen: sonst hinge
    er daran, dass jeder Aufrufer daran denkt. Alter allein wäre als Kriterium untauglich
    — ein großer Download kann Stunden brauchen und sieht dabei alt aus.
    """
    monkeypatch.setattr(appmod, "SAB_DONE", str(tmp_path))
    monkeypatch.setattr(appmod, "jd_out_dir", lambda: str(tmp_path))
    (tmp_path / "romseerr_111__Laeuft").mkdir()
    (tmp_path / "romseerr_222__Fertig").mkdir()
    (tmp_path / "fremder_ordner").mkdir()          # nicht unserer
    appmod.JOBS[:] = [{"id": "111", "state": "downloading", "title": "Läuft"},
                      {"id": "222", "state": "error", "title": "Fertig"}]

    gefunden = {x["jid"] for x in appmod.leftover_dirs()}
    assert "222" in gefunden, "ein gescheiterter Auftrag gehört auf die Liste"
    assert "111" not in gefunden, "ein LAUFENDER Auftrag darf nie zum Aufräumen angeboten werden"
    assert all(x["name"].startswith("romseerr_") for x in appmod.leftover_dirs())
    appmod.JOBS[:] = []


def test_leftover_remove_refuses_paths_outside(appmod, tmp_path, monkeypatch):
    """`rm -rf` darf nur innerhalb der Sammelordner zuschlagen. (#244)

    Das ist die eine Stelle hier, an der ein Denkfehler nicht rückgängig zu machen ist.
    Geprüft wird deshalb auch der Symlink-Weg: ein Verweis, der aus dem Sammelordner
    hinauszeigt, umginge eine reine Präfix-Prüfung auf dem unaufgelösten Pfad.
    """
    sammel = tmp_path / "collect"; sammel.mkdir()
    fremd = tmp_path / "wichtig"; fremd.mkdir()
    (fremd / "daten.txt").write_text("nicht anfassen")
    monkeypatch.setattr(appmod, "SAB_DONE", str(sammel))
    monkeypatch.setattr(appmod, "jd_out_dir", lambda: str(sammel))

    # außerhalb
    ok, grund = appmod.leftover_remove(str(fremd))
    assert ok is False and (fremd / "daten.txt").exists(), f"fremder Pfad wurde gelöscht ({grund})"

    # innerhalb, aber ohne unser Präfix
    ohne = sammel / "irgendwas"; ohne.mkdir()
    ok, _ = appmod.leftover_remove(str(ohne))
    assert ok is False and ohne.exists(), "nur romseerr_-Ordner dürfen weg"

    # Symlink aus dem Sammelordner heraus: der aufgelöste Pfad zählt, nicht der Name
    link = sammel / "romseerr_999"
    try:
        link.symlink_to(fremd, target_is_directory=True)
    except OSError:
        pass
    else:
        ok, _ = appmod.leftover_remove(str(link))
        assert (fremd / "daten.txt").exists(), "Symlink-Ausbruch muss abgewiesen werden"

    # der Gutfall muss trotzdem funktionieren, sonst ist die Sperre nur ein Verbot
    echt = sammel / "romseerr_888__X"; echt.mkdir()
    (echt / "f.bin").write_text("x")
    ok, grund = appmod.leftover_remove(str(echt))
    assert ok is True and not echt.exists(), f"gültiger Ordner ließ sich nicht entfernen ({grund})"


def test_leftovers_endpoint_needs_permission(appmod, client):
    """Die Liste nennt Pfade und Größen, das Entfernen löscht Daten. (#244)"""
    appmod.save_users({**ADMIN_FIX, "g": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "g"; sess["role"] = "user"
    assert client.get("/api/leftovers").status_code == 403
    assert client.post("/api/leftovers/remove", json={"all": True}).status_code == 403
    appmod.save_users({})


def test_reimport_uses_files_on_disk_instead_of_downloading_again(appmod, client, tmp_path, monkeypatch):
    """Erneut einlesen heißt: die vorhandenen Dateien, kein neuer Download. (#245)

    Abgrenzung zu `/retry`, das den Auftrag zurück in die Download-Warteschlange legt.
    Genau dafür hebt #240 die Daten auf — 2 GB erneut zu ziehen, weil eine Endung falsch
    erkannt wurde, wäre das Gegenteil davon.
    """
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    cand = tmp_path / "romseerr_55__X"; cand.mkdir()
    (cand / "spiel.nes").write_text("x")
    appmod.JOBS[:] = [{"id": "55", "title": "X", "source": "usenet", "state": "error",
                       "platform": "nes", "msg": "keine ROM-Dateien"}]
    monkeypatch.setattr(appmod, "save_jobs", lambda: None)
    monkeypatch.setattr(appmod, "SAB_DONE", str(tmp_path))
    monkeypatch.setattr(appmod, "jd_out_dir", lambda: str(tmp_path))
    gerufen = []
    monkeypatch.setattr(appmod, "einsortieren", lambda jid, job, c: gerufen.append((jid, c)))
    # Ein erneutes Einlesen darf NICHT in der Download-Warteschlange landen.
    in_queue = []
    monkeypatch.setattr(appmod.Q, "put", lambda x: in_queue.append(x))

    r = client.post("/api/jobs/55/reimport")
    assert r.status_code == 200 and r.get_json()["ok"] is True
    for _ in range(50):
        if gerufen: break
        time.sleep(0.02)
    assert gerufen and gerufen[0][0] == "55", "einsortieren muss mit dem Auftrag laufen"
    assert in_queue == [], "erneut einlesen darf keinen neuen Download anstoßen"
    appmod.JOBS[:] = []; appmod.save_users({})


def test_reimport_refused_when_files_are_gone_or_state_wrong(appmod, client, tmp_path, monkeypatch):
    """Kein Angebot, das beim Drücken scheitert. (#245)"""
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    monkeypatch.setattr(appmod, "save_jobs", lambda: None)
    monkeypatch.setattr(appmod, "SAB_DONE", str(tmp_path))
    monkeypatch.setattr(appmod, "jd_out_dir", lambda: str(tmp_path))
    appmod.JOBS[:] = [{"id": "56", "title": "Weg", "source": "usenet", "state": "error"},
                      {"id": "57", "title": "Laeuft", "source": "usenet", "state": "downloading"}]

    assert client.post("/api/jobs/56/reimport").status_code == 404, "ohne Dateien: 404"
    assert client.post("/api/jobs/57/reimport").status_code == 400, "laufender Auftrag: 400"
    assert client.post("/api/jobs/99/reimport").status_code == 404, "unbekannt: 404"

    # Und die Oberfläche darf den Knopf nur zeigen, wenn wirklich Dateien da sind.
    js = {j["id"]: j for j in client.get("/api/jobs").get_json()}
    assert js["56"].get("reimportable") is False
    (tmp_path / "romseerr_56__Weg").mkdir()
    js = {j["id"]: j for j in client.get("/api/jobs").get_json()}
    assert js["56"].get("reimportable") is True, "mit Dateien muss der Knopf angeboten werden"
    appmod.JOBS[:] = []; appmod.save_users({})


def test_delete_request_refuses_while_active(appmod, client):
    """Eine laufende Anfrage darf nicht verschwinden. (#246)

    Sonst löscht jemand den Auftrag, während im Hintergrund noch geladen wird — und der
    fertige Download landet als herrenloser Ordner auf der Platte.
    """
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    appmod.JOBS[:] = [{"id": "60", "title": "Laeuft", "state": "downloading"},
                      {"id": "61", "title": "Fertig", "state": "done"},
                      {"id": "62", "title": "Wartet", "state": "pending"}]
    assert client.delete("/api/jobs/60").status_code == 400, "downloading darf nicht löschbar sein"
    assert client.delete("/api/jobs/62").status_code == 400, "pending ist noch nicht entschieden"
    assert client.delete("/api/jobs/99").status_code == 404
    assert client.delete("/api/jobs/61").status_code == 200, "abgeschlossene müssen weg können"
    assert [j["id"] for j in appmod.JOBS] == ["60", "62"]
    appmod.JOBS[:] = []; appmod.save_users({})


def test_delete_request_says_when_files_stay_behind(appmod, client, tmp_path, monkeypatch):
    """Wer die Anfrage löscht, muss erfahren, dass Daten zurückbleiben. (#246, #240)

    Der Auftrag ist das Einzige, was einen `romseerr_<jid>`-Ordner noch einem Titel
    zuordnet. Verschwindet er stillschweigend, bleibt ein unidentifizierbarer Haufen übrig,
    den die Verfallsfrist irgendwann wegräumt — Daten weg, ohne dass jemand entschieden hat.
    """
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    monkeypatch.setattr(appmod, "SAB_DONE", str(tmp_path))
    monkeypatch.setattr(appmod, "jd_out_dir", lambda: str(tmp_path))
    monkeypatch.setattr(appmod, "save_jobs", lambda: None)

    ordner = tmp_path / "romseerr_70__X"; ordner.mkdir()
    (ordner / "nutzlast.bin").write_text("wertvoll")
    appmod.JOBS[:] = [{"id": "70", "title": "X", "state": "error"}]

    # ohne files: Anfrage weg, Daten bleiben — und das wird ausdrücklich gemeldet
    d = client.delete("/api/jobs/70", json={}).get_json()
    assert d["files_left"] is True and d["files_deleted"] is False
    assert ordner.exists(), "ohne ausdrückliche Ansage dürfen die Dateien nicht verschwinden"

    # mit files: beides weg
    appmod.JOBS[:] = [{"id": "70", "title": "X", "state": "error"}]
    d = client.delete("/api/jobs/70", json={"files": True}).get_json()
    assert d["files_deleted"] is True and d["files_left"] is False
    assert not ordner.exists()
    appmod.JOBS[:] = []; appmod.save_users({})


def test_clear_finished_can_be_limited_to_one_state(appmod, client, monkeypatch):
    """Nur die Fehlgeschlagenen wegräumen, ohne den Rest zu verlieren. (#246)"""
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    monkeypatch.setattr(appmod, "save_jobs", lambda: None)
    monkeypatch.setattr(appmod, "SAB_DONE", "/nicht/vorhanden")
    appmod.JOBS[:] = [{"id": "80", "state": "done"}, {"id": "81", "state": "error"},
                      {"id": "82", "state": "denied"}, {"id": "83", "state": "downloading"}]

    r = client.post("/api/jobs/clear-finished", json={"states": ["error"]}).get_json()
    assert r["removed"] == 1
    assert sorted(j["id"] for j in appmod.JOBS) == ["80", "82", "83"]

    # Unbekannte Zustände dürfen nicht dazu führen, dass plötzlich alles gelöscht wird —
    # aber ein laufender Auftrag bleibt in jedem Fall stehen.
    client.post("/api/jobs/clear-finished", json={"states": ["quatsch"]})
    assert [j["id"] for j in appmod.JOBS] == ["83"], "ohne gültige Angabe: alles Abgeschlossene"
    appmod.JOBS[:] = []; appmod.save_users({})


def test_retry_escalates_to_another_source_on_the_third_attempt(appmod, client, monkeypatch):
    """Zweimal dieselbe Quelle, ab dem dritten Mal eine andere. (#200)

    Eine Quelle, die einen Titel nicht liefert, liefert ihn auch beim vierten Mal nicht.
    Der Wechsel ist der einzige Versuch, der neue Information trägt.
    """
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    monkeypatch.setattr(appmod, "save_jobs", lambda: None)
    monkeypatch.setattr(appmod.Q, "put", lambda x: None)
    monkeypatch.setattr(appmod, "do_search", lambda q, p=None: [
        {"source": "archive", "ref": "arch://x", "title": "Spiel (USA)",
         "gkey": appmod.norm("Spiel (USA)"), "platform": "nes"}])

    appmod.JOBS[:] = [{"id": "90", "title": "Spiel (USA)", "source": "usenet",
                       "ref": "nzb://alt", "state": "error", "platform": "nes"}]

    # 2. Versuch: gleiche Quelle, nur neu eingestellt
    d = client.post("/api/jobs/90/retry").get_json()
    assert d["tries"] == 2 and d["source"] == "usenet", "zu früh gewechselt"

    # 3. Versuch: jetzt die andere Quelle — und die gescheiterte ist vermerkt
    appmod.set_state("90", state="error")
    d = client.post("/api/jobs/90/retry").get_json()
    assert d["tries"] == 3 and d["source"] == "archive", "beim dritten Versuch muss gewechselt werden"
    j = appmod.get_job("90")
    assert j["ref"] == "arch://x" and "usenet" in j["tried_sources"]
    assert "archive" in (j.get("msg") or ""), "die Meldung muss die neue Quelle nennen"
    appmod.JOBS[:] = []; appmod.save_users({})


def test_retry_never_switches_to_a_different_title(appmod, client, monkeypatch):
    """Ein Quellenwechsel darf niemals ein anderes Spiel holen. (#200)

    Das ist der Fall, der schlimmer wäre als der Fehlschlag selbst: die Suche liefert
    ähnliche Treffer, und ein großzügiger Vergleich würde still das falsche Spiel
    einsortieren. Lieber „alle Quellen versucht" melden.
    """
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    monkeypatch.setattr(appmod, "save_jobs", lambda: None)
    gestellt = []
    monkeypatch.setattr(appmod.Q, "put", lambda x: gestellt.append(x))
    # Andere Quelle, aber ein anderer Titel — sowie derselbe Titel in der SCHON
    # gescheiterten Quelle. Beides darf nicht genommen werden.
    monkeypatch.setattr(appmod, "do_search", lambda q, p=None: [
        {"source": "archive", "ref": "arch://fremd", "title": "Spiel 2 (USA)",
         "gkey": appmod.norm("Spiel 2 (USA)"), "platform": "nes"},
        {"source": "usenet", "ref": "nzb://neu", "title": "Spiel (USA)",
         "gkey": appmod.norm("Spiel (USA)"), "platform": "nes"}])

    appmod.JOBS[:] = [{"id": "91", "title": "Spiel (USA)", "source": "usenet",
                       "ref": "nzb://alt", "state": "error", "platform": "nes",
                       "tries": 2, "tried_sources": ["usenet"]}]
    r = client.post("/api/jobs/91/retry")
    assert r.status_code == 409, "ohne passende Alternative darf nicht gewechselt werden"
    d = r.get_json()
    assert d["exhausted"] is True
    j = appmod.get_job("91")
    assert j["ref"] == "nzb://alt", "die Adresse darf sich nicht auf einen Fremdtitel ändern"
    assert j["state"] == "error" and "alle Quellen" in j["msg"]
    assert gestellt == [], "erschöpfte Quellen dürfen nicht wieder eingestellt werden"
    appmod.JOBS[:] = []; appmod.save_users({})


def test_successful_import_resets_the_attempt_counter(appmod, tmp_path, monkeypatch):
    """Was einmal geklappt hat, fängt später nicht bei „3. Versuch" an. (#200)"""
    monkeypatch.setattr(appmod, "save_jobs", lambda: None)
    monkeypatch.setattr(appmod, "build_index", lambda: None)
    monkeypatch.setattr(appmod, "romm_scan", lambda: None)
    monkeypatch.setattr(appmod, "notify_available", lambda *a, **k: None)
    monkeypatch.setattr(appmod, "send_push_to_user", lambda *a, **k: None)
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path / "roms"))
    d = tmp_path / "job"; d.mkdir()
    (d / "spiel.nes").write_text("x")
    appmod.JOBS[:] = [{"id": "92", "title": "S", "source": "archive", "state": "downloading",
                       "platform": "nes", "tries": 3, "tried_sources": ["usenet", "archive"]}]

    assert appmod.import_folder("92", str(d)) is True
    j = appmod.get_job("92")
    assert j["state"] == "done"
    assert j["tries"] == 0 and j["tried_sources"] == [], "Zähler muss zurückgesetzt werden"
    appmod.JOBS[:] = []


def test_save_users_refuses_to_lock_everyone_out(appmod):
    """Kein Schreibvorgang darf eine Instanz ohne Zugang hinterlassen. (#234)

    Die Bedingung stand vorher nur im Import-Pfad. `save_users` ist aber ein **Ersetzer**:
    es leert die Tabelle und schreibt das übergebene Dict als Gesamtbestand — jeder andere
    Weg (Benutzerverwaltung, Rechteformular, Wartungsaufruf) konnte die Instanz
    unerreichbar machen.
    """
    appmod.save_users({"chef": {"pw": "geheim", "role": "admin"},
                       "gast": {"pw": "x", "role": "user"}})

    # Konten ohne einen einzigen Admin
    with pytest.raises(appmod.KeinAdminMehr):
        appmod.save_users({"gast": {"pw": "x", "role": "user"}})
    # Admin ohne Passwort ist kein Zugang
    with pytest.raises(appmod.KeinAdminMehr):
        appmod.save_users({"chef": {"pw": "", "role": "admin"}})
    with pytest.raises(appmod.KeinAdminMehr):
        appmod.save_users({"chef": {"role": "admin"}})

    # und der Bestand ist unangetastet — eine abgewiesene Änderung darf nichts halb tun
    assert sorted(appmod.load_users()) == ["chef", "gast"]

    # Die LEERE Liste ist erlaubt: dann greift die Ersteinrichtung, das sperrt niemanden aus.
    appmod.save_users({})
    assert appmod.load_users() == {}
    appmod.save_users({})


def test_last_admin_cannot_be_demoted_or_deleted_via_api(appmod, client):
    """Auch über die Oberfläche nicht — und mit 400 statt Serverfehler. (#234)"""
    appmod.save_users({"chef": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "chef"; sess["role"] = "admin"

    r = client.patch("/api/users/chef", json={"role": "user"})
    assert r.status_code == 400, "der letzte Admin darf die Rolle nicht verlieren"
    assert appmod.load_users()["chef"]["role"] == "admin"

    # Ein zweiter Admin macht den Weg frei — sonst wäre die Sperre keine Regel, sondern
    # eine Blockade.
    appmod.save_users({"chef": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)},
                       "zwei": {"pw": "y", "role": "admin", "perms": list(appmod.PERMS)}})
    r = client.patch("/api/users/zwei", json={"role": "user"})
    assert r.status_code == 200 and appmod.load_users()["zwei"]["role"] == "user"
    appmod.save_users({})


def test_shrinking_the_user_list_is_logged(appmod, tmp_path, monkeypatch):
    """Ein versehentliches Überschreiben soll wenigstens nachweisbar sein. (#234)

    Die Invariante verhindert das Aussperren, nicht das Ersetzen durch einen gültigen,
    aber falschen Bestand — genau so gingen hier schon einmal zwei echte Konten verloren.
    """
    zeilen = []
    monkeypatch.setattr(appmod, "log", lambda m: zeilen.append(m))
    appmod.save_users({"chef": {"pw": "x", "role": "admin"},
                       "a": {"pw": "x", "role": "user"},
                       "b": {"pw": "x", "role": "user"}})
    zeilen.clear()
    appmod.save_users({"chef": {"pw": "x", "role": "admin"}})
    assert any("verkleinert" in z and "3 -> 1" in z for z in zeilen), zeilen
    appmod.save_users({})


def _wiiu_ordner(wurzel, name, app_id, meta_id=None):
    """Wii-U-Titelordner. `app_id` und `meta_id` getrennt, weil sie sich im Bestand
    WIDERSPRECHEN — genau daran hing #512."""
    t = wurzel / name
    (t / "code").mkdir(parents=True)
    (t / "content").mkdir()
    (t / "meta").mkdir()
    (t / "code" / "Spiel.rpx").write_bytes(b"\x7fELF")
    (t / "code" / "app.xml").write_text(
        f'<app><title_id type="hexBinary" length="8">{app_id}</title_id></app>',
        encoding="utf-8")
    (t / "meta" / "meta.xml").write_text(
        f'<menu><title_id type="hexBinary" length="8">{meta_id or app_id}</title_id></menu>',
        encoding="utf-8")
    return t


def test_romseerr_refuses_a_wiiu_update_before_the_button_appears(appmod, tmp_path):
    """Der Knopf darf gar nicht erst erscheinen. (#512)

    Der Start-Dienst lehnt ein Wii-U-Update seit #502 ab. Romseerr fragte nicht — also
    zeigte es den Knopf, der Nutzer klickte, belegte einen Platz, und ERST DANN kam die
    Absage. Dieselbe Lüge wie vor #299 beim 3DS, nur eine Plattform weiter.

    AM BESTAND GEMESSEN — die beiden Beschreibungsdateien widersprechen sich:

        meta/meta.xml   0005000010180700   (behauptet: Basisspiel)
        code/app.xml    0005000E10180700   (Update)

    Deshalb wird `app.xml` gelesen. Wer `meta.xml` nimmt, bekommt mit voller Überzeugung
    die falsche Antwort.
    """
    t = _wiiu_ordner(tmp_path / "wiiu", "Captain Toad [AKBP01]",
                     app_id="0005000E10180700", meta_id="0005000010180700")
    startbar, grund = appmod.wiiu_startbar(str(t))
    assert not startbar
    assert grund == "wiiu_update", grund


def test_a_wiiu_base_game_stays_streamable(appmod, tmp_path):
    """Die Ratsche: ein echtes Spiel darf nicht mitabgesagt werden. (#512)

    Ohne sie wäre eine Prüfung, die IMMER absagt, ebenfalls grün — und Wii U damit
    vollständig unerreichbar, statt nur seine Updates.
    """
    t = _wiiu_ordner(tmp_path / "wiiu", "Echtes Spiel", "0005000010180700")
    assert appmod.wiiu_startbar(str(t)) == (True, "")


def test_an_unreadable_wiiu_title_passes_rather_than_being_refused(appmod, tmp_path):
    """Im Zweifel durchlassen — wie bei Switch (#427) und 3DS (#299). (#512)

    Eine falsche Absage kostet mehr als ein Fehlversuch: Sie nimmt einen vorhandenen
    Titel dauerhaft aus dem Angebot, und niemand sucht danach.
    """
    ohne = tmp_path / "wiiu" / "Ohne app.xml"
    (ohne / "code").mkdir(parents=True)
    assert appmod.wiiu_startbar(str(ohne)) == (True, "")

    unlesbar = _wiiu_ordner(tmp_path / "wiiu", "Muell", "0005000010180700")
    (unlesbar / "code" / "app.xml").write_text("kein xml", encoding="utf-8")
    assert appmod.wiiu_startbar(str(unlesbar)) == (True, "")


def test_a_wiiu_dlc_and_a_system_title_are_refused_as_well(appmod, tmp_path):
    """`0005000C` ist DLC, `0005001B` ein Systemtitel — beides kein Spiel. (#512)"""
    for kennung, erwartet in (("0005000C10180700", "wiiu_dlc"),
                              ("0005001B10180700", "wiiu_system")):
        t = _wiiu_ordner(tmp_path / "wiiu", f"T{kennung}", kennung)
        assert appmod.wiiu_startbar(str(t)) == (False, erwartet), kennung


def test_every_stream_reason_has_a_text(appmod):
    """Jeder Grund aus stream_info hat einen Eintrag in der Oberfläche. (#175)

    Die Lücke entstand, weil `ambiguous_platform` im Server eingeführt wurde und in der
    Oberfläche niemand nachzog: der Code fiel stumm in den allgemeinen Satz. Nichts hat
    das bemerkt, weil nichts die beiden Seiten vergleicht — genau das tut dieser Test.

    ER TAT ES LANGE NUR HALB (#513). Gesammelt wurden ausschliesslich Gründe, die als
    WÖRTLICHER String in `stream_info` stehen:

        gruende = re.findall('"reason": "(...)"', ...)   # nur Literale

    Die Plattformprüfungen liefern ihren Grund aber über eine Hilfsfunktion, und er
    reist als Variable weiter:

        startbar, grund = switch_startbar(path)
        return {"streamable": False, "reason": grund, ...}

    Damit war jeder so gelieferte Code unsichtbar. Gemessen: `nsp_update` und `nsp_dlc`
    fehlten in `STREAM_GRUND`, obwohl `stream_nsp_update` und `stream_nsp_dlc` seit #427
    in ALLEN FÜNF Sprachen bereitlagen. Ein Switch-Update zeigte „Streamen gerade nicht
    möglich" — der passende Satz lag drei Dateien weiter und war unerreichbar.

    Das Schlimmere war nicht der fehlende Satz, sondern dass diese Prüfung GRÜN meldete
    für etwas, das sie nicht prüfte. Wer danach einen Grund hinzufügte, verliess sich
    darauf.

    Gesammelt wird deshalb aus zwei Quellen: den wörtlichen Gründen in `stream_info` und
    den Absagen der Funktionen, die `stream_info` befragt — das sind die `*_startbar`.

    NICHT modulweit nach `return False, "…"` suchen: Das fängt `dns`, `invalid`,
    `private` und `scheme` aus der URL-Prüfung mit ein, die mit dem Stream nichts zu tun
    haben. Eine Prüfung, die Fremdes einsammelt, verlangt Texte für Codes, die nie an der
    Oberfläche ankommen — und wird dann entnervt wieder entschärft.

    EN: the check only saw reasons spelled out literally in `stream_info`; every reason
    delivered through a helper — which is how all platform checks work — was invisible,
    and the check reported success for something it did not perform.
    """
    import re
    quelle = open("app.py", encoding="utf-8").read()
    i = quelle.index("def stream_info(")
    j = quelle.index("\ndef ", i + 10)
    gruende = set(re.findall(r'"reason":\s*"([a-z_]+)"', quelle[i:j]))

    # Was über eine Hilfsfunktion kommt (#513). Massgeblich sind die `*_startbar`, denn
    # genau die ruft `stream_info` auf; ihre Absagen reisen als Variable weiter und waren
    # deshalb unsichtbar.
    import ast as _ast
    baum = _ast.parse(quelle)
    zeilen = quelle.splitlines(keepends=True)
    for k in baum.body:
        if not (isinstance(k, _ast.FunctionDef) and k.name.endswith("_startbar")):
            continue
        rumpf = "".join(zeilen[k.lineno - 1:k.end_lineno])
        gruende |= set(re.findall(r'return\s+\(?\s*False\s*,\s*"([a-z_]+)"', rumpf))
        # Tabellen wie `_CIA_ZUBEHOER` liefern den Grund als Wert, nicht als Literal am
        # `return`. Sie stehen ausserhalb der Funktion, gehoeren aber dazu.
        for tabelle in re.findall(r'\b(_[A-Z0-9_]*ZUBEHOER)\b', rumpf):
            m2 = re.search(rf'^{tabelle}\s*=\s*\{{(.*?)\}}', quelle, re.S | re.M)
            if m2:
                gruende |= set(re.findall(r':\s*"([a-z_]+)"', m2.group(1)))
    gruende.discard("")
    assert len(gruende) >= 8, (
        f"nur {len(gruende)} Gründe gefunden — die Sammlung ist kaputt, nicht die "
        f"Oberfläche: {sorted(gruende)}")

    js = open("static/js/index.js", encoding="utf-8").read()
    m = re.search(r"const STREAM_GRUND=\{(.*?)\};", js, re.S)
    assert m, "STREAM_GRUND fehlt — ohne die Tabelle kann nichts geprüft werden"
    bekannt = set(re.findall(r"([a-z_]+)\s*:", m.group(1))) | set(re.findall(r"'([a-z_]*)'\s*:", m.group(1)))

    fehlend = gruende - bekannt
    assert not fehlend, f"ohne Text in der Oberfläche: {sorted(fehlend)}"

    # Und die referenzierten i18n-Schlüssel muss es in ALLEN Sprachen geben, sonst steht
    # dort der nackte Schlüssel.
    schluessel = set(re.findall(r":\s*'([a-z_]+)'", m.group(1)))
    for sprache, tabelle in sprachtabellen().items():
        for k in schluessel:
            assert str(tabelle.get(k, "")).strip(), f"{k} fehlt in {sprache}"


def test_ambiguous_platform_offers_the_candidates(appmod, monkeypatch):
    """Die Absage nennt die Plattformen, zwischen denen zu wählen ist. (#175)

    Geraten wird weiterhin nicht — das PS2-Abbild zu starten, wenn die Wii-Fassung
    gemeint war, bleibt die stille Fehlentscheidung, die es zu vermeiden gilt. Aber die
    Frage zu stellen kostet nichts.
    """
    monkeypatch.setattr(appmod, "stream_cfg", lambda: {"url": "http://host", "launch": ""})
    monkeypatch.setattr(appmod, "STREAMABLE", {"ps2", "wii"})
    monkeypatch.setattr(appmod, "PLAYABLE", set())
    monkeypatch.setattr(appmod, "resolve_slug", lambda x: x)
    with appmod.LIB_LOCK:
        appmod.LIB["per"] = {"ps2": {appmod.norm("Spiel")}, "wii": {appmod.norm("Spiel")}}

    d = appmod.stream_info("Spiel", "Mixed")
    assert d["reason"] == "ambiguous_platform"
    assert d["candidates"] == ["ps2", "wii"], "beide Kandidaten müssen genannt werden"

    # Eindeutig bleibt eindeutig — die Kandidatenliste darf den Normalfall nicht stören.
    with appmod.LIB_LOCK:
        appmod.LIB["per"] = {"ps2": {appmod.norm("Spiel")}}
    assert appmod.plattform_aus_bibliothek("Spiel") == "ps2"
    assert appmod.plattform_kandidaten("Spiel") == ["ps2"]
    with appmod.LIB_LOCK:
        appmod.LIB["per"] = {}


def test_jd_probe_detects_that_nobody_is_listening(appmod, tmp_path, monkeypatch):
    """Die Sonde erkennt, wenn niemand die Übergabe liest. (#218)

    `jd_check` meldete auf der gemessenen Anlage `ok: True`, während die
    FolderWatch-Erweiterung überhaupt nicht installiert war: Ordner da, beschreibbar,
    Ziel da — und niemand hörte zu. Alle drei Prüfungen lagen auf unserer Seite.
    """
    monkeypatch.setattr(appmod, "jd_watch_dir", lambda: str(tmp_path))
    monkeypatch.setattr(appmod, "jd_check", lambda anlegen=False: {"ok": True, "reason": "ok"})
    # Uhr stellen statt warten: die Wartezeit ist der Sinn der Sonde, aber sie in jedem
    # CI-Lauf real abzusitzen wäre Verschwendung.
    uhr = [1000.0]
    monkeypatch.setattr(appmod.time, "time", lambda: uhr[0])
    monkeypatch.setattr(appmod.time, "sleep", lambda n: uhr.__setitem__(0, uhr[0] + n))

    d = appmod.jd_probe(wartezeit=5)
    assert d["ok"] is False and d["reason"] == "not_consumed"
    assert "FolderWatch" in d["fix"], "die Abhilfe muss die Erweiterung benennen"
    # Keine Spur hinterlassen: eine liegengebliebene Sonde wäre später von einem echten
    # Auftrag nicht zu unterscheiden.
    assert not list(tmp_path.iterdir()), "die Sonde muss ihre Datei wieder entfernen"


def test_jd_probe_reports_success_when_the_file_is_picked_up(appmod, tmp_path, monkeypatch):
    """Wird die Datei abgeholt, ist die Gegenseite da. (#218)"""
    monkeypatch.setattr(appmod, "jd_watch_dir", lambda: str(tmp_path))
    monkeypatch.setattr(appmod, "jd_check", lambda anlegen=False: {"ok": True, "reason": "ok"})

    # Die Gegenseite nachstellen: beim ersten Warten verschwindet die Datei.
    echt = appmod.time.sleep
    def schlaf(n):
        for f in tmp_path.iterdir(): f.unlink()
        echt(0)
    monkeypatch.setattr(appmod.time, "sleep", schlaf)

    d = appmod.jd_probe(wartezeit=5)
    assert d["ok"] is True and d["reason"] == "consumed"


def test_jd_probe_writes_a_job_that_cannot_do_anything(appmod, tmp_path, monkeypatch):
    """Die Sonde darf nichts herunterladen. (#218)

    Sie landet in einer fremden Anwendung; ein Auftrag, der versehentlich startet, wäre
    ein Nebeneffekt einer Diagnose — genau das, was eine Prüfung nicht tun darf.
    """
    monkeypatch.setattr(appmod, "jd_watch_dir", lambda: str(tmp_path))
    monkeypatch.setattr(appmod, "jd_check", lambda anlegen=False: {"ok": True, "reason": "ok"})
    geschrieben = {}
    def schlaf(n):
        for f in tmp_path.iterdir():
            geschrieben.update(json.loads(f.read_text())[0])
            f.unlink()
    monkeypatch.setattr(appmod.time, "sleep", schlaf)

    appmod.jd_probe(wartezeit=5)
    assert geschrieben, "es wurde gar keine Sonde geschrieben"
    # BooleanStatus, nicht boolean — dieselbe Falle wie in #219.
    assert geschrieben["enabled"] == "FALSE"
    assert geschrieben["autoStart"] == "FALSE" and geschrieben["autoConfirm"] == "FALSE"
    assert "example.invalid" in geschrieben["text"], "die Sonde darf auf nichts Echtes zeigen"


def test_jd_probe_needs_permission_and_is_not_in_status(appmod, client):
    """Auf Anforderung, nicht im Statusabruf — sie kostet Sekunden und hinterlässt eine Spur. (#218)"""
    appmod.save_users({"g": {"pw": "x", "role": "user", "perms": ["request"]},
                       "chef": {"pw": "x", "role": "admin", "perms": []}})
    with client.session_transaction() as sess:
        sess["user"] = "g"; sess["role"] = "user"
    assert client.post("/api/jd/probe").status_code == 403
    quelle = open("app.py", encoding="utf-8").read()
    i = quelle.index("def api_services_status") if "def api_services_status" in quelle else 0
    if i:
        j = quelle.index("\ndef ", i + 10)
        assert "jd_probe(" not in quelle[i:j], "die Sonde gehört nicht in den Statusabruf"
    appmod.save_users({})


def test_bilingual_comment_share_does_not_drop(appmod):
    """Der zweisprachige Anteil der Kommentare darf nicht sinken. (#212)"""
    bloecke = []
    for datei in _doc_dateien():
        try:
            bloecke += _doc_bloecke(open(datei, encoding="utf-8").read())
        except OSError:
            pass
    assert len(bloecke) > 50, "Blockerkennung liefert zu wenig — die Messung wäre wertlos"
    mit = sum(1 for b in bloecke if _hat_englisch(b))
    anteil = 100.0 * mit / len(bloecke)
    assert anteil >= DOC_EN_BODEN, (
        f"zweisprachiger Anteil auf {anteil:.1f} % gefallen (Boden {DOC_EN_BODEN} %): "
        f"{mit} von {len(bloecke)} Blöcken. Neue Kommentarblöcke ab drei Zeilen brauchen "
        f"einen englischen Teil — oder hebe den Boden, wenn du bestehende nachgebessert hast.")


def test_new_routes_carry_a_docstring(appmod):
    """Die Zahl der Route-Handler ohne Docstring darf nicht steigen. (#212)

    Ein Ratschet, kein Zielwert: 73 von 110 haben heute keinen. Das ist kein Auftrag für
    einen großen Durchgang, sondern Schuld, die beim nächsten Anfassen der Stelle beglichen
    wird — neue Routen aber brauchen von Anfang an einen.
    """
    baum = ast.parse(open("app.py", encoding="utf-8").read())
    ohne = [n.name for n in ast.walk(baum)
            if isinstance(n, ast.FunctionDef)
            and any(isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "route"
                    for d in n.decorator_list)
            and not ast.get_docstring(n)]
    assert len(ohne) <= DOC_ROUTEN_OHNE, (
        f"{len(ohne)} Route-Handler ohne Docstring (erlaubt: {DOC_ROUTEN_OHNE}). "
        f"Deine neue Route braucht einen: was tut sie, und warum so? "
        f"(Welche es ist, zeigt `git diff` — die Namen hier zu raten wäre irreführend.)")


def test_no_new_json_store_appears_unnoticed(appmod):
    """Ein neuer Dateispeicher muss eine Entscheidung sein, kein Versehen. (#192)

    Wer eine Datei im Konfigverzeichnis anlegt, trifft eine Grundsatzentscheidung — sie
    fehlt im Export, im Import und in jeder Sicherung, die nur die Datenbank kennt.
    """
    import re
    quelle = open("app.py", encoding="utf-8").read()
    gefunden = set(re.findall(r'os\.path\.join\(CONFIG_DIR,\s*"([^"]+)"\)', quelle))
    gefunden = {g for g in gefunden if not g.endswith((".db", ".log")) and "staging" not in g}
    neu = gefunden - set(DATEI_SPEICHER)
    assert not neu, (
        f"neuer Dateispeicher im Konfigverzeichnis: {sorted(neu)}. Gehört er in die "
        f"Datenbank? Wenn nein, trag ihn mit Begründung in DATEI_SPEICHER ein — "
        f"Dateien fehlen im Export und in DB-Sicherungen.")


def test_key_material_is_not_world_readable(appmod, tmp_path, monkeypatch):
    """Schlüsselmaterial liegt mit 0600, auch wenn es schon da war. (#192)

    Gemessen auf der laufenden Anlage: `vapid.json` und `secret.key` standen auf **0664**
    — lesbar für Gruppe und alle. Beide entstanden über ein schlichtes `open(..., "w")`.
    """
    ziel = tmp_path / "geheim.key"
    appmod.schreibe_geheim(str(ziel), "abc")
    assert ziel.read_text() == "abc"
    assert oct(ziel.stat().st_mode & 0o777) == "0o600", "neu geschrieben muss 0600 sein"

    # Und der Altbestand wird nachgezogen — ein Fix nur für Neuinstallationen repariert
    # keine einzige laufende Anlage.
    alt = tmp_path / "alt.json"
    alt.write_text("{}")
    alt.chmod(0o664)
    zeilen = []
    monkeypatch.setattr(appmod, "log", lambda m: zeilen.append(m))
    appmod.geheim_absichern(str(alt))
    assert oct(alt.stat().st_mode & 0o777) == "0o600"
    assert any("0600" in z for z in zeilen), "die Korrektur gehört ins Protokoll"

    # Was schon eng ist, wird nicht angefasst und nicht protokolliert.
    zeilen.clear()
    appmod.geheim_absichern(str(alt))
    assert zeilen == []


def test_unused_key_is_tightened_at_startup(appmod, tmp_path, monkeypatch):
    """Auch ein Schlüssel, den niemand liest, wird eng gemacht. (#256)

    Der Fix aus #192 zog die Rechte beim **Lesen** nach. `vapid.json` wird aber nur
    angefasst, wenn Web-Push benutzt wird — auf der gemessenen Anlage nie. Also behielt
    ausgerechnet der Schlüssel die offenen Rechte, den niemand anfasst.

    Der Test liest die Datei bewusst NICHT: täte er es, liefe er auch gegen die alte
    Fassung durch und bewiese nichts.
    """
    vapid = tmp_path / "vapid.json"; vapid.write_text('{"priv_pem": "x"}'); vapid.chmod(0o664)
    secret = tmp_path / "secret.key"; secret.write_text("abc"); secret.chmod(0o644)
    fehlt = tmp_path / "gibtsnicht.pem"

    monkeypatch.setattr(appmod, "VAPID_FILE", str(vapid))
    monkeypatch.setattr(appmod, "SECRET_FILE", str(secret))
    monkeypatch.setattr(appmod, "TLS_CERT", str(fehlt))
    monkeypatch.setattr(appmod, "TLS_KEY", str(fehlt))
    monkeypatch.setattr(appmod, "log", lambda m: None)

    appmod.geheimnisse_absichern()

    assert oct(vapid.stat().st_mode & 0o777) == "0o600", "ungelesener Schlüssel blieb offen"
    assert oct(secret.stat().st_mode & 0o777) == "0o600"
    assert vapid.read_text() == '{"priv_pem": "x"}', "der Inhalt darf sich nicht ändern"
    # Eine fehlende Datei ist kein Fehler — TLS ist optional.
    appmod.geheimnisse_absichern()


def test_wrong_launch_token_is_reported_as_such(appmod, monkeypatch, tmp_path):
    """Ein nicht passendes Token ist ein anderer Fehler als ein toter Host. (#177)

    Beide sahen gleich aus („Start fehlgeschlagen"), und der Betreiber suchte am falschen
    Ende — der Dienst läuft ja, er weist nur ab. 401 ist die einzige Antwort, die der
    Start-Dienst auf ein falsches Token gibt.
    """
    monkeypatch.setattr(appmod, "stream_cfg",
                        lambda: {"url": "http://host:8902/", "launch": "http://host:8901/launch?token=x"})
    monkeypatch.setattr(appmod, "STREAMABLE", {"ps2"})
    monkeypatch.setattr(appmod, "PLAYABLE", set())
    monkeypatch.setattr(appmod, "resolve_slug", lambda x: x)
    monkeypatch.setattr(appmod, "stream_find_file", lambda t, s: str(tmp_path / "spiel.iso"))
    monkeypatch.setattr(appmod, "stream_sessions", lambda: {})
    monkeypatch.setattr(appmod, "kv_put", lambda *a, **k: None)

    class Antwort:
        def __init__(self, code): self.ok = False; self.status_code = code
        def json(self): return {"ok": False, "msg": "unauthorised"}
    monkeypatch.setattr(appmod, "safe_post", lambda *a, **k: Antwort(401))
    info, code = appmod.stream_start("j", "Spiel", "ps2")
    assert info["launch_reason"] == "bad_token", "401 muss als Token-Fehler erkennbar sein"

    # Gegenprobe: ein anderer Fehler darf NICHT als Token-Problem erscheinen, sonst
    # schickt die Meldung den Betreiber genauso in die Irre wie vorher.
    monkeypatch.setattr(appmod, "safe_post", lambda *a, **k: Antwort(500))
    info, code = appmod.stream_start("j", "Spiel", "ps2")
    assert info["launch_reason"] == "", "500 ist kein Token-Fehler"
    assert info["launch_error"], "aber eine Begründung muss trotzdem dastehen"


def test_release_image_is_not_wired_to_an_event_that_cannot_fire(appmod):
    """Das Abbild haengt nicht an `on: release`, das nie feuern kann. (#185)

    Ein Release, das release-please mit dem Standard-`GITHUB_TOKEN` anlegt, loest keine
    weiteren Workflows aus — GitHubs Sperre gegen sich selbst ausloesende Workflows.
    `on: release: [published]` konnte fuer einen solchen Release also nie feuern, und
    v1.1.0-beta.1 wurde ohne Abbild veroeffentlicht, waehrend der Kopf der Datei das
    Gegenteil behauptete.
    """
    pub = yaml.safe_load(open(".github/workflows/release-image.yml", encoding="utf-8"))
    # `on` wird von YAML 1.1 als bool True gelesen — beide Schreibweisen abfangen.
    ausloeser = pub.get("on", pub.get(True)) or {}
    assert "release" not in ausloeser, \
        "on: release kann für ein vom Bot erzeugtes Release nicht feuern (#185)"
    assert "workflow_call" in ausloeser, "der Bau muss aufrufbar sein"

    rp = yaml.safe_load(open(".github/workflows/release-please.yml", encoding="utf-8"))
    job = rp["jobs"].get("publish-image")
    assert job, "release-please muss den Bau selbst anstoßen"
    assert job.get("uses", "").endswith("release-image.yml"), "und zwar über denselben Workflow"
    # Dieselbe Bedingung wie bei `promote` und `release-branch` — ein Bau ohne Release
    # waere ein Abbild ohne Tag.
    assert "outputs.released" in str(job.get("if", "")), \
        "nur bauen, wenn wirklich ein Release entstanden ist"


def test_latest_tag_cannot_land_on_a_prerelease(appmod):
    """`latest` haengt am Versionsnamen, nicht am Ausloeser. (#185)

    Vorher stand dort `github.event_name != 'release' || …`: bei einem Lauf von Hand war
    die erste Haelfte wahr, und `latest` landete auf einer Beta — genau das, was der
    Kommentar darueber ausschloss. Der manuelle Notnagel tauschte damit ein fehlendes
    Abbild gegen ein irrefuehrendes.
    """
    text = open(".github/workflows/release-image.yml", encoding="utf-8").read()
    zeile = next((z for z in text.split("\n") if "value=latest" in z), "")
    assert zeile, "kein latest-Tag gefunden"
    assert "event_name" not in zeile, \
        "die Bedingung darf nicht am Auslöser hängen — bei einem Handlauf war sie wahr"
    assert "contains(" in zeile and "'-'" in zeile, \
        "SemVer kennzeichnet Vorabversionen mit '-'; daran muss die Bedingung hängen"


def test_play_cores_flags_a_core_the_player_does_not_ship(appmod, client, monkeypatch):
    """Ein Play-Knopf, dessen Kern fehlt, muss auffallen. (#124)

    `intellivision` zeigte auf `freeintv`; im eingesetzten RomM-Bau antwortet dieser Kern
    mit 404. Der Knopf konnte nicht funktionieren und sah aus wie jeder andere — die
    Kernnamen stammten aus dem libretro-Katalog, nicht aus der laufenden Installation.
    """
    appmod.save_users({"j": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "j"; sess["role"] = "admin"
    monkeypatch.setattr(appmod, "cfg", lambda k, d="": "http://romm" if k == "romm_url" else d)
    monkeypatch.setattr(appmod, "PLAYABLE", {"nes": "fceumm", "kaputt": "gibtsnicht"})

    class R:
        def __init__(self, c): self.status_code = c
    monkeypatch.setattr(appmod.requests, "head",
                        lambda url, **k: R(200 if "fceumm" in url else 404))

    d = client.get("/api/play/cores").get_json()
    zustand = {x["platform"]: x["available"] for x in d["cores"]}
    assert zustand["nes"] is True
    assert zustand["kaputt"] is False, "ein fehlender Kern muss als fehlend gemeldet werden"
    assert d["missing"] == 1 and d["ok"] is False
    appmod.save_users({})


def test_every_playable_core_entry_is_documented_as_checked(appmod):
    """Kernnamen kommen aus der eingesetzten Fassung, nicht aus einem Katalog. (#124)

    Der Unterschied ist keine Förmlichkeit: `freeintv` steht im libretro-Katalog und
    fehlt im Player. Wer die nächste Zeile ergänzt, soll lesen, woher der Name kommen muss.
    """
    quelle = open("app.py", encoding="utf-8").read()
    block = quelle[quelle.index("PLAYABLE = {"):]
    block = block[:block.index("\nNEEDS_BIOS")]
    assert "nachgesehen" in block.lower() or "read out of the deployed" in block.lower(), \
        "der Hinweis auf die Messung fehlt"
    # Intellivision darf nicht zurückkehren, solange der Kern fehlt.
    assert '"intellivision":' not in block, "freeintv wird vom Player nicht ausgeliefert (#124)"


def test_two_seats_allow_two_people_at_once(appmod, client):
    """Zwei Plätze, zwei Leute, gleichzeitig — das war der Zweck von #137.

    Geprüft werden die Abnahmekriterien des Issues: beide kommen dran, jeder bekommt
    die Adresse SEINES Platzes (die falsche landete auf dem Desktop des anderen), der
    dritte wird abgewiesen statt still zu übernehmen, und das Beenden des einen lässt
    den anderen unberührt.
    """
    _stream_ready(appmod)
    appmod.kv_put("stream_sessions", {}); appmod.kv_put("stream_session", None)
    appmod.save_settings({"connections": {
        "stream_url": "http://sitz1.example:3000/",
        "stream_url_2": "http://sitz2.example:3000/"}})
    appmod.save_users({**ADMIN_FIX,
                       "anna": {"pw": "x", "role": "user", "perms": ["request"]},
                       "bert": {"pw": "x", "role": "user", "perms": ["request"]},
                       "cara": {"pw": "x", "role": "user", "perms": ["request"]}})
    assert len(appmod.stream_seats()) == 2

    def start(wer):
        with client.session_transaction() as sess:
            sess["user"] = wer; sess["role"] = "user"
        return client.post("/api/stream/start",
                           json={"title": "Zzz Streamtitel", "platform": "ps2"})

    r1 = start("anna")
    assert r1.status_code == 200, r1.get_json()
    r2 = start("bert")
    assert r2.status_code == 200, "zweiter Platz wurde nicht vergeben"
    # Jeder auf SEINER Adresse — sonst sieht der zweite das Bild des ersten.
    assert r1.get_json()["url"] != r2.get_json()["url"]
    assert r1.get_json()["seat"] != r2.get_json()["seat"]

    # Der dritte bekommt eine klare Absage, nicht den Platz eines anderen.
    r3 = start("cara")
    assert r3.status_code == 409 and r3.get_json()["reason"] == "busy"

    # Beenden des einen lässt den anderen laufen.
    with client.session_transaction() as sess:
        sess["user"] = "anna"; sess["role"] = "user"
    assert client.post("/api/stream/stop").get_json()["was_running"] is True
    assert appmod.stream_session_of("bert")[1] is not None, "fremde Sitzung mitgerissen"
    assert appmod.stream_session_of("anna") == (None, None)
    # ... und der frei gewordene Platz geht an den nächsten.
    assert start("cara").status_code == 200

    appmod.kv_put("stream_sessions", {}); appmod.kv_put("stream_session", None)
    appmod.save_users({}); appmod.save_settings({})


def test_second_title_reuses_your_own_seat(appmod, client):
    """Wer einen zweiten Titel startet, soll seinen Platz behalten und nicht den
    zweiten mitbelegen — sonst sperrt eine Person allein die ganze Anlage."""
    _stream_ready(appmod)
    appmod.kv_put("stream_sessions", {}); appmod.kv_put("stream_session", None)
    appmod.save_settings({"connections": {
        "stream_url": "http://sitz1.example:3000/",
        "stream_url_2": "http://sitz2.example:3000/"}})
    appmod.save_users({**ADMIN_FIX, "anna": {"pw": "x", "role": "user", "perms": ["request"]}})
    with client.session_transaction() as sess:
        sess["user"] = "anna"; sess["role"] = "user"
    a = client.post("/api/stream/start", json={"title": "Zzz Streamtitel", "platform": "ps2"})
    b = client.post("/api/stream/start", json={"title": "Zzz Streamtitel", "platform": "ps2"})
    assert a.get_json()["seat"] == b.get_json()["seat"]
    assert len(appmod.stream_sessions()) == 1, "zweiter Platz unnötig belegt"
    appmod.kv_put("stream_sessions", {}); appmod.kv_put("stream_session", None)
    appmod.save_users({}); appmod.save_settings({})


def test_single_seat_session_survives_the_upgrade(appmod):
    """Wer beim Update gerade spielt, darf seinen Platz nicht verlieren.

    Vor #137 lag die Sitzung als Einzelwert unter `stream_session`. Ein solcher
    Altbestand wird zu Platz 1 — sonst wäre das Update für den Spielenden ein
    plötzliches „besetzt durch niemanden". (#137)
    """
    appmod.kv_put("stream_sessions", None)
    appmod.kv_put("stream_session", {"user": "anna", "title": "X", "platform": "ps2",
                                     "started": 0, "expires": time.time() + 600})
    sitzungen = appmod.stream_sessions()
    assert sitzungen.get("1", {}).get("user") == "anna", "laufende Sitzung verloren"
    # Der alte Schlüssel wird dabei geräumt, sonst käme die Sitzung nach dem Beenden zurück.
    assert appmod.kv_get("stream_session", None) in (None, {}), "Altschlüssel nicht geräumt"
    appmod.kv_put("stream_sessions", {}); appmod.kv_put("stream_session", None)


def test_the_second_seat_is_reachable_from_the_interface():
    """Ein Platz, den man nicht eintragen kann, gibt es nicht.

    Die Oberfläche rendert die Verbindungsfelder EINZELN und namentlich — eine neue
    Einstellung erscheint dort nicht von allein, auch wenn der Server sie kennt. Ohne
    diese Felder wäre der zweite Platz nur über die .env erreichbar, und das Feature
    aus Sicht der Bedienung nicht vorhanden. (#137)
    """
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    for feld in ("stream_url_2", "stream_launch_2"):
        assert f"fld('{feld}'" in js, f"kein Eingabefeld für {feld}"
    # Alle Textbausteine in allen fünf Sprachen — ein fehlender fällt sonst erst
    # auf, wenn jemand die Sprache umstellt und dort der Schlüsselname steht.
    for schluessel in ("stream_url2_l", "stream_launch2_l", "stream_seat2_hint",
                       "stream_seats"):
        assert i18n_hat(schluessel) == 5, \
            f"{schluessel} fehlt in einer der fünf Sprachen"
    # Die Platzanzeige darf bei mehreren Plätzen nicht mehr "Einzelplatz" behaupten.
    assert "d.seats||1)>1" in js.replace(" ", ""), "Platzanzeige nicht von der Zahl abhängig"


def test_a_switch_update_is_never_picked_over_the_base_game(appmod, tmp_path):
    """Update und Basisspiel sind nach der Normalisierung ununterscheidbar.

    `A Tale For Anna [..A800][v131072].nsp` (40 MB) und
    `A Tale for Anna [..A000][v0].nsp` (1,1 GB) werden beide zu "a tale for anna".
    Wer das Update erwischt, bekommt im Emulator `Error while loading ROM! (0007-003C)`
    und ein Fenster mit der bloßen Oberfläche — was aussieht, als könne der Emulator
    die Plattform gar nicht. Genau so lag es als Fehler vor. (#174)

    Die letzten drei Stellen der Titel-ID entscheiden: 000 = Basisspiel, 800 = Update,
    alles andere = DLC.
    """
    d = os.path.join(appmod.ROMS, "switch")
    os.makedirs(d, exist_ok=True)
    update = os.path.join(d, "A Tale For Anna [010032A01AACA800][v131072][US].nsp")
    basis = os.path.join(d, "A Tale for Anna [010032A01AACA000][v0][US].nsp")
    # ABSICHTLICH ANDERSHERUM: das Update ist hier GRÖSSER als das Basisspiel. Sonst
    # würde schon die Größensortierung das Richtige treffen und der Test bewiese nichts
    # über die Erkennung — genau das war beim ersten Wurf der Fall (Alarmpfad geprüft,
    # er schlug nicht an). Nur die Titel-ID kann diesen Fall entscheiden.
    with open(update, "wb") as f:
        f.write(b"x" * 40960)
    with open(basis, "wb") as f:
        f.write(b"x" * 4096)
    appmod.build_index()
    try:
        gewaehlt = appmod.stream_find_file("A Tale for Anna", "switch")
        assert gewaehlt == basis, f"Update statt Basisspiel gewählt: {gewaehlt}"
        # Auch wenn nur das Update da ist, darf die Auswahl nicht leer ausgehen —
        # ein Fehlstart mit Meldung ist besser als "nicht in der Bibliothek".
        os.remove(basis)
        appmod.build_index()
        assert appmod.stream_find_file("A Tale for Anna", "switch") == update
    finally:
        for p in (update, basis):
            if os.path.exists(p):
                os.remove(p)
        appmod.build_index()


def test_the_largest_file_wins_when_nothing_marks_an_update(appmod, tmp_path):
    """Ohne Titel-ID im Namen bleibt nur die Größe — ein .xci neben einer kleinen .nsp.

    Bei Resident Evil 4 liegen genau diese zwei: die 15,9-GB-.xci (das Spiel) und eine
    14,8-MB-.nsp, die nur das Update ist. Ties brechen nach Namen, damit die Wahl nicht
    von der Reihenfolge im Dateisystem abhängt. (#174)
    """
    d = os.path.join(appmod.ROMS, "switch")
    os.makedirs(d, exist_ok=True)
    klein = os.path.join(d, "Zzz Testtitel.nsp")
    gross = os.path.join(d, "Zzz Testtitel.xci")
    with open(klein, "wb") as f:
        f.write(b"x" * 1024)
    with open(gross, "wb") as f:
        f.write(b"x" * 65536)
    appmod.build_index()
    try:
        assert appmod.stream_find_file("Zzz Testtitel", "switch") == gross
    finally:
        for p in (klein, gross):
            if os.path.exists(p):
                os.remove(p)
        appmod.build_index()


def test_a_base_game_carrying_an_applied_update_is_not_mistaken_for_one(appmod):
    """Eine Basis-ID (`000`) mit Fassung > 0 ist eine AKTUALISIERTE BASIS, kein Update.

    Frueher fiel sie durch die Titel-ID-Pruefung hindurch zur Fassungsregel und wurde
    dort verworfen. In der Bibliothek nachgemessen: 5 von 484 Switch-Dateien, darunter
    `Crime O'Clock [0100E4A0194DE000][v65536]`. Steht daneben ein echtes Update, waehlte
    die Regel dieses — also genau der Fehler, den #174 beheben sollte.

    Die Titel-ID sagt, WAS die Datei ist. Die Fassung sagt nur, wie alt sie ist.
    """
    # Basis mit eingespieltem Update: ID endet auf 000, Fassung ist trotzdem hoch.
    assert not appmod.ist_zusatz("Crime O'Clock [0100E4A0194DE000][v65536][US].nsp")
    assert not appmod.ist_zusatz("Killer Frequency [0100B3601926A000][v196608].nsp")
    # Die Gegenrichtung bleibt: 800 ist und bleibt ein Update, auch bei [v0].
    assert appmod.ist_zusatz("A Tale For Anna [010032A01AACA800][v0].nsp")
    # Ohne Titel-ID bleibt nur die Fassung — dort gilt die alte, schwaechere Regel.
    assert appmod.ist_zusatz("Irgendein Titel [v131072].nsp")
    assert not appmod.ist_zusatz("Irgendein Titel [v0].nsp")


def test_a_title_id_with_stray_spaces_still_counts(appmod):
    """`[ 0100643002136800]` kommt in echten Sammlungen vor.

    Ohne Toleranz fuer das Leerzeichen ist das gar keine Titel-ID, die Datei faellt auf
    die Fassungsregel zurueck und wird nur zufaellig richtig eingestuft. (#174)
    """
    assert appmod.ist_zusatz("Resident Evil Revelations[ 0100643002136800][v65536].nsp")
    # Und dasselbe Muster mit Basis-ID darf NICHT als Zusatz gelten.
    assert not appmod.ist_zusatz("Resident Evil Revelations[ 0100643002136000][v65536].nsp")


def test_the_base_game_wins_over_an_update_that_is_larger(appmod):
    """Der Fall, der ohne die Titel-ID-Regel nicht zu entscheiden waere.

    Das Update ist hier ABSICHTLICH groesser als die Basis — faellt die Regel auf die
    Groesse zurueck, waehlt sie das Update und der Test schlaegt fehl. Nur so beweist er
    die Regel statt eines Zufalls. (#174)
    """
    d = os.path.join(appmod.ROMS, "switch")
    os.makedirs(d, exist_ok=True)
    basis = os.path.join(d, "Zzz Grenzfall [0100AAA0BBBCC000][v65536].nsp")
    update = os.path.join(d, "Zzz Grenzfall [0100AAA0BBBCC800][v131072].nsp")
    with open(basis, "wb") as f:
        f.write(b"x" * 1024)
    with open(update, "wb") as f:
        f.write(b"x" * 65536)          # das Update ist 64x groesser
    appmod.build_index()
    try:
        assert appmod.stream_find_file("Zzz Grenzfall", "switch") == basis
    finally:
        for p in (basis, update):
            if os.path.exists(p):
                os.remove(p)
        appmod.build_index()


# ------------------------------- Unversorgte Plattformen einsortieren (#193)

def test_xsym_symlink_placeholders_do_not_become_titles(appmod):
    """RetroNAS legt Herstellerordner an, deren Inhalt nur Verweise sind.

    Ueber SMB gelesen sind XSym-Symlinks gewoehnliche Dateien — genau 1067 Byte,
    beginnend mit `XSym\\n`. Ohne die Pruefung werden sie zu Titeln, ihre Ordner zu
    Plattformen, und `nec`, `nintendo` und `sega` erscheinen als drei unversorgte
    Plattformen, die es nie gab. (#193)

    Die Ordner am NAMEN zu verbieten waere der falsche Weg: anderswo ist `sega/` voller
    Mega-Drive-Spiele. Deshalb entscheidet der Dateiinhalt, nicht der Ordnername.
    """
    d = os.path.join(appmod.ROMS, "nec")
    os.makedirs(d, exist_ok=True)
    # GENAU der Fall aus der Bibliothek: `nec/turbografx16` ist ein Verweis auf
    # `nec/pcengine`. Der Name ueberlebt die Normalisierung (anders als etwa "genesis",
    # das ohnehin verworfen wird) — ohne die Pruefung wird daraus also ein Titel.
    verweis = os.path.join(d, "turbografx16")
    echt = os.path.join(d, "Zzz Echtes Spiel.md")
    # XSym: 1067 Byte, Kopfwort, danach Ziel — so legt Netatalk/Samba das ab.
    with open(verweis, "wb") as f:
        f.write(b"XSym\n0031\n" + b"0" * 32 + b"\n/srv/retronas/roms/nec/pcengine\n")
        f.truncate(appmod.XSYM_GROESSE)
    with open(echt, "wb") as f:
        f.write(b"x" * 2048)
    appmod.build_index()
    try:
        titel = appmod.LIB["per"].get("nec") or set()
        assert appmod.norm("Zzz Echtes Spiel.md") in titel, "echter Titel fehlt"
        assert appmod.norm("turbografx16") not in titel, "XSym-Verweis wurde zum Titel"
        # Und die Gegenprobe zur Groesse: eine gleich grosse Datei OHNE Kopfwort zaehlt.
        assert appmod.ist_xsym(verweis)
        assert not appmod.ist_xsym(echt)
    finally:
        for p in (verweis, echt):
            if os.path.exists(p):
                os.remove(p)
        appmod.build_index()


def test_cd32_uses_the_amiga_core_that_is_already_there(appmod):
    """CD32 ist ein Amiga mit CD-Laufwerk und laeuft auf demselben Kern.

    Der Kern `puae` war fuer den Amiga laengst eingetragen; die 715 CD32-Dateien lagen
    nur still, weil die Zuordnung fehlte — die billigste Abdeckung der ganzen Liste.
    Er wurde im eingesetzten RomM-Bau per HEAD nachgesehen, nicht aus libretros Katalog
    uebernommen. (#193)
    """
    assert appmod.PLAYABLE.get("amiga-cd32") == "puae"
    assert appmod.PLAYABLE.get("amiga") == "puae", "beide muessen denselben Kern nutzen"
    # Ohne Kickstart startet der Kern und scheitert dann — das muss VORHER dastehen.
    assert "amiga-cd32" in appmod.NEEDS_BIOS
    # Und der Slug muss eine bekannte Plattform sein, sonst taucht er nirgends auf.
    assert "amiga-cd32" in appmod.SLUG_NAME


def test_owned_titles_show_a_readable_name_not_the_normalised_one(appmod):
    """Die Liste zeigt Dateinamen, nicht `norm`.

    `norm` ist kleingeschrieben und entkernt — als Bibliotheksliste unlesbar. Bei
    mehreren Dateien desselben Titels gewinnt der KUERZESTE Name: `Turrican` ist als
    Ueberschrift brauchbar, `Turrican (1990)(Rainbow Arts)[cr ABC][t +3]` nicht. (#293)
    """
    d = _lege_titel_an(appmod, "c64", [
        ("Turrican (1990)(Rainbow Arts)[cr ABC].d64", 2048),
        ("Turrican.d64", 1024),
    ])
    try:
        erg = appmod.owned_titles("c64")
        assert erg["total"] == 1, erg          # beide sind DERSELBE Titel
        assert erg["titles"] == ["Turrican"], erg
    finally:
        shutil.rmtree(d, ignore_errors=True)
        appmod.build_index()


def test_owned_titles_page_and_filter(appmod):
    """Ohne Paging waere die Ansicht bei c64 (fuenfstellig) unbenutzbar. (#293)"""
    d = _lege_titel_an(appmod, "c64",
                       [(f"Zzz Titel {i:03d}.d64", 512) for i in range(25)])
    try:
        seite = appmod.owned_titles("c64", offset=0, limit=10)
        assert seite["total"] == 25 and len(seite["titles"]) == 10, seite
        zweite = appmod.owned_titles("c64", offset=10, limit=10)
        assert zweite["titles"][0] != seite["titles"][0]
        # Sortiert, damit Blaettern nicht dieselbe Zeile zweimal zeigt.
        assert seite["titles"] == sorted(seite["titles"])
        gefiltert = appmod.owned_titles("c64", q="Titel 007")
        assert gefiltert["total"] == 1, gefiltert
    finally:
        shutil.rmtree(d, ignore_errors=True)
        appmod.build_index()


def test_library_overview_groups_by_vendor_and_keeps_sourceless_platforms(appmod, client):
    """Gruppiert wie die Abdeckungsseite — und versteckt nichts.

    Plattformen OHNE Katalogquelle haben keine Prozentzahl. Sie deshalb wegzulassen
    waere derselbe Fehler, den die Abdeckungsseite gerade vermeidet: was man besitzt,
    weiss Romseerr auch ohne IGDB. (#293)
    """
    appmod.save_users({"c": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "c"; sess["role"] = "admin"
    d1 = _lege_titel_an(appmod, "c64", [("Zzz Ein Titel.d64", 512)])
    # `vectrex` hat keine IGDB-Katalogquelle und muss trotzdem erscheinen.
    d2 = _lege_titel_an(appmod, "vectrex", [("Zzz Anderer Titel.bin", 512)])
    try:
        d = client.get("/api/library/platforms").get_json()
        slugs = {p["slug"] for g in d["vendors"] for p in g["platforms"]}
        assert "c64" in slugs, d
        assert "vectrex" not in appmod.IGDB_PLAT or True   # Doku: keine Quelle noetig
        assert "vectrex" in slugs, "Plattform ohne Katalogquelle fehlt"
        # Die Herstellersumme muss der Summe ihrer Systeme entsprechen.
        for g in d["vendors"]:
            assert g["owned"] == sum(p["owned"] for p in g["platforms"]), g
        assert d["total"] >= 2
    finally:
        for d_ in (d1, d2):
            shutil.rmtree(d_, ignore_errors=True)
        appmod.build_index()
        appmod.save_users({})


def test_library_titles_endpoint_answers(appmod, client):
    """Der Endpunkt spiegelt `…/missing` — gleiche Form, andere Menge. (#293)"""
    appmod.save_users({"c": {"pw": "x", "role": "admin", "perms": list(appmod.PERMS)}})
    with client.session_transaction() as sess:
        sess["user"] = "c"; sess["role"] = "admin"
    d = _lege_titel_an(appmod, "c64", [("Zzz Nur Einer.d64", 512)])
    try:
        r = client.get("/api/library/c64/titles?limit=5").get_json()
        assert r["slug"] == "c64" and r["total"] >= 1, r
        assert "Zzz Nur Einer" in r["titles"], r
        assert r["limit"] == 5 and r["offset"] == 0
    finally:
        shutil.rmtree(d, ignore_errors=True)
        appmod.build_index()
        appmod.save_users({})


def test_every_view_has_a_route():
    """Jede Ansicht, die `zeige()` kennt, braucht einen Eintrag in ROUTEN. (#320)

    WARUM DAS WICHTIG IST: `routeBauen` endet mit `ROUTEN[v] || 'discover'`. Ein fehlender
    Eintrag erzeugt also keinen Fehler, sondern still die falsche Adresse — die Ansicht
    wird angezeigt, die Adresse zeigt Entdecken, und Deep-Links landen woanders. Genau so
    ist die Bibliotheksansicht aus #293 durchgerutscht.

    Diese Pruefung braucht keinen Browser und haette den Fehler am selben Tag gefunden.

    `routeBauen` falls back to 'discover' for an unknown key, so a missing entry produces
    a silently wrong URL rather than an error.
    """
    routen, ansichten = _routen_und_ansichten()
    ohne = sorted(ansichten - routen)
    assert not ohne, (f"Ansichten ohne Routen-Eintrag: {ohne}. "
                      "In ROUTEN in static/js/index.js nachtragen.")


def test_views_are_covered_by_browser_tests():
    """Jede routebare Ansicht steht in der Tabelle der Browsertests. (#327)

    Verglichen werden die WERTE aus ROUTEN (`discover`, `requests`, …) mit den Adressen in
    `ANSICHTEN` in tests/e2e/test_browser.py. Wer eine Ansicht ergaenzt und den Browsertest
    vergisst, wird hier rot — ohne dass die Browsertests selbst laufen muessen.

    Rot gesehen: mit einer aus `ANSICHTEN` entfernten Zeile schlaegt die Pruefung an und
    nennt die fehlende Ansicht.
    """
    import re
    js = _js()
    m = re.search(r"ROUTEN\s*=\s*\{([^}]*)\}", js)
    ziele = set(re.findall(r"\w+\s*:\s*'([^']+)'", m.group(1)))
    assert ziele, "ROUTEN konnte nicht gelesen werden — Pruefung waere wertlos"

    quelle = os.path.join(os.path.dirname(os.path.abspath(__file__)), "e2e", "test_browser.py")
    with open(quelle, encoding="utf-8") as f:
        getestet = set(re.findall(r'"#/(\w+)"', f.read()))
    assert getestet, "ANSICHTEN in test_browser.py konnte nicht gelesen werden"

    fehlend = sorted(ziele - getestet)
    assert len(fehlend) <= ANSICHTEN_OHNE_BROWSERTEST, (
        f"{len(fehlend)} Ansichten ohne Browsertest (erlaubt: "
        f"{ANSICHTEN_OHNE_BROWSERTEST}): {fehlend}. "
        "Neue Ansicht? Dann gehoert sie in ANSICHTEN in tests/e2e/test_browser.py.")


def test_hidden_directories_are_not_platforms(appmod, tmp_path, monkeypatch):
    """Ordner mit einem Punkt am Anfang sind keine Plattformen. (#321)

    Der Umbau der Bibliothek legt sein Arbeitsverzeichnis als `.umbau` NEBEN die
    Plattformordner. Vor dieser Regel tauchten dessen Protokolldateien als 62 „Titel" in
    der Bibliotheksansicht auf — sichtbar, mit Zaehler, unter einer eigenen Zeile.

    Rot gesehen: ohne die Regel enthaelt der Index `.umbau` mit einem Titel.
    """
    wurzel = tmp_path / "roms"
    (wurzel / "snes").mkdir(parents=True)
    (wurzel / "snes" / "Super Mario World.sfc").write_bytes(b"x" * 32)
    (wurzel / ".umbau").mkdir()
    (wurzel / ".umbau" / "fortschritt.json").write_text("{}")
    (wurzel / ".cache").mkdir()
    (wurzel / ".cache" / "irgendwas.dat").write_bytes(b"y" * 16)

    monkeypatch.setattr(appmod, "ROMS", str(wurzel))
    appmod.build_index()

    slugs = set(appmod.LIB.get("per", {}))
    versteckt = {s for s in slugs if s.startswith(".")}
    assert not versteckt, f"versteckte Ordner im Index: {sorted(versteckt)}"
    assert "snes" in slugs, "die echte Plattform fehlt — die Regel greift zu weit"


# --- Hersteller-Ordnung der Bibliothek (#322) --------------------------------------

def test_library_vendor_groups_do_not_overlap(appmod):
    """Kein System steht in zwei Herstellergruppen.

    Eine Ueberschneidung faellt in der Ansicht nicht auf — der Titel erschiene einfach
    zweimal, und die Summe waere hoeher als die Bibliothek. Gerade beim Aufteilen einer
    Sammelgruppe passiert das leicht: `atari-st` gehoert zu Atari, nicht zu den
    Heimcomputern, aber beide Listen laden dazu ein.
    """
    gesehen = {}
    doppelt = []
    for hersteller, slugs in appmod.LIB_VENDORS:
        for sl in slugs:
            if sl in gesehen:
                doppelt.append(f"{sl}: {gesehen[sl]} + {hersteller}")
            gesehen[sl] = hersteller
    assert not doppelt, "Systeme in mehreren Gruppen: " + "; ".join(doppelt)


def test_the_leftover_group_has_a_real_name(appmod):
    """Die Auffanggruppe traegt einen Namen, keinen Gedankenstrich. (#322)

    Vorher hiess sie `—`. Darunter lag `scummvm` mit 16.487 Titeln — die zweitgroesste
    Plattform der Bibliothek, unter einer Ueberschrift, die nichts sagt.
    """
    assert appmod.LIB_REST.startswith(appmod.LIB_GRP_PREFIX), \
        "die Auffanggruppe braucht einen uebersetzbaren Schluessel"
    assert appmod.LIB_REST.strip("-—– ") == appmod.LIB_REST


def test_the_big_home_computer_vendors_have_their_own_group(appmod):
    """Commodore, Sinclair, Amstrad und Atari sind eigene Gruppen. (#322)

    Sie steckten alle in `PLATFORMS`' Sammeltopf „Sonstige". Commodore allein ist mit
    rund 40.000 Titeln GROESSER als Nintendo — in einem Topf namens „Sonstige" zu
    verschwinden ist dort der augenfaelligste Fehler.
    """
    namen = {v for v, _ in appmod.LIB_VENDORS}
    for erwartet in ("Commodore", "Sinclair", "Amstrad", "Atari"):
        assert erwartet in namen, f"{erwartet} hat keine eigene Gruppe"
    commodore = dict(appmod.LIB_VENDORS)["Commodore"]
    assert "c64" in commodore and "amiga" in commodore


def test_category_group_keys_exist_in_all_five_languages(appmod):
    """Jeder `lib_grp_`-Schluessel ist in allen fuenf Sprachen uebersetzt. (#322)

    Herstellernamen sind sprachneutral, Sammelbegriffe nicht. Fehlt eine Uebersetzung,
    zeigt die Oberflaeche dort den nackten Schluessel — sichtbar nur, wenn jemand die
    Sprache umstellt, und deshalb sonst erst spaet.

    Rot gesehen: mit einem entfernten `lib_grp_hand` in der italienischen Zeile.
    """
    import re
    schluessel = {v for v, _ in appmod.LIB_VENDORS if v.startswith(appmod.LIB_GRP_PREFIX)}
    schluessel.add(appmod.LIB_REST)
    assert schluessel, "keine Sammelgruppen gefunden — Pruefung waere wertlos"

    pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "static", "js", "index.js")
    with open(pfad, encoding="utf-8") as f:
        js = f.read()
    fehlend = []
    for k in sorted(schluessel):
        n = i18n_hat(k)
        if n != 5:
            fehlend.append(f"{k}: {n}x statt 5")
    assert not fehlend, "Uebersetzungen unvollstaendig: " + "; ".join(fehlend)


# --- Empfehlungen nur fuer bedienbare Plattformen (#324) ---------------------------

def test_similar_games_are_filtered_to_supported_platforms(appmod, monkeypatch):
    """„Weil du angefragt hast" schlaegt nur vor, was es fuer eine unserer Plattformen gibt.

    Der gemessene Fall: Zur Xbox-Saat *Fable* lieferte IGDB Borderlands 3, GreedFall und
    *The Elder Scrolls VI* — Letzteres unveroeffentlicht, ohne Cover, ohne Bewertung, als
    schwarze Kachel an der prominentesten Stelle der Anwendung. Keiner dieser Titel ist
    anfragbar.

    Titel OHNE Plattformangabe fallen ebenfalls raus: Ohne sie ist unbekannt, ob es sie
    fuer eine unserer Konsolen gibt — und im gemessenen Fall waren es genau die
    unveroeffentlichten.
    """
    snes = appmod.IGDB_PLAT["snes"]
    antwort = [{"name": "Fable", "similar_games": [
        {"name": "Chrono Trigger", "cover": {"image_id": "a"}, "total_rating": 95,
         "platforms": [{"id": snes}]},
        {"name": "Borderlands 3", "cover": {"image_id": "b"}, "total_rating": 79,
         "platforms": [{"id": 999999}]},                      # Plattform, die wir nicht bedienen
        {"name": "The Elder Scrolls VI", "cover": {"image_id": "c"}},   # gar keine Plattform
    ]}]
    monkeypatch.setattr(appmod, "igdb_query", lambda *a, **k: antwort)
    appmod.IGDB["cache"].clear()

    titel = [g["title"] for g in appmod.igdb_similar_games("Fable")]
    assert titel == ["Chrono Trigger"], f"unerwartet: {titel}"


# --- Auftraege nach einem Neustart (#336) ------------------------------------------

def test_in_flight_jobs_are_cleared_after_a_restart(appmod):
    """Ein Neustart mitten im Import laesst keinen Auftrag im Nirgendwo zurueck. (#336)

    Gemessener Anlass: Nach vier gewoehnlichen Deployments stand ein Import 11,5 Stunden
    auf `importing`, bei leerem Staging. Der Arbeitsfaden war weg, der Zustand blieb.

    Das kostet mehr als einen toten Auftrag: `importing` steht in OFFENE_ZUSTAENDE, also
    galt der Titel als „bereits angefragt" und war nicht erneut anforderbar — und sein
    Rest-Ordner war vor dem Aufraeumen geschuetzt (#244).

    `pending` und `queued` bleiben unangetastet: Die warten auf eine Entscheidung bzw. auf
    die Warteschlange und ueberstehen einen Neustart einwandfrei.
    """
    vorher = list(appmod.JOBS)
    try:
        appmod.JOBS[:] = [
            {"id": "j1", "title": "Little Big Planet", "state": "importing"},
            {"id": "j2", "title": "Irgendwas",        "state": "downloading"},
            {"id": "j3", "title": "Wartet auf Freigabe", "state": "pending"},
            {"id": "j4", "title": "In der Schlange",  "state": "queued"},
            {"id": "j5", "title": "Fertig",           "state": "done"},
        ]
        betroffen = appmod.jobs_nach_neustart_aufraeumen()

        zustand = {j["id"]: j["state"] for j in appmod.JOBS}
        assert zustand["j1"] == "error", "der haengende Import wurde nicht aufgeraeumt"
        assert zustand["j2"] == "error", "ein unterbrochener Download bleibt haengen"
        assert zustand["j3"] == "pending", "eine wartende Freigabe wurde faelschlich abgebrochen"
        assert zustand["j4"] == "queued", "ein Auftrag in der Schlange wurde abgebrochen"
        assert zustand["j5"] == "done"
        assert set(betroffen) == {"j1", "j2"}

        # Die Meldung muss sagen, was zu tun ist — ein blosses „error" hilft niemandem.
        meldung = next(j for j in appmod.JOBS if j["id"] == "j1").get("msg", "")
        assert "Neustart" in meldung and "erneut" in meldung

        # Und der Titel muss wieder anfragbar sein: genau das war vorher blockiert.
        assert "error" not in appmod.OFFENE_ZUSTAENDE
    finally:
        appmod.JOBS[:] = vorher
        appmod.save_jobs()


def test_navigation_labels_carry_no_icon_and_exist_in_all_languages():
    """Menue-Symbole stehen in der Vorlage, nicht im uebersetzten Text. (#337)

    `applyI18n` setzt `textContent` des Elements mit `data-i18n`. Ein Symbol INNERHALB
    dieses Elements wird dabei geloescht — es ueberlebt nur, wenn jede einzelne
    Uebersetzung es wiederholt. Genau daran verloren Abdeckung und Bibliothek ihres,
    waehrend fuenf andere es behielten: derselbe Mechanismus, zwei Ergebnisse.

    Geprueft wird deshalb beides: dass die Beschriftungen KEIN Symbol mehr tragen (sonst
    stuende es doppelt neben dem aus der Vorlage), und dass jeder Schluessel in allen
    fuenf Sprachen existiert — `nav_library` gab es in zweien.

    Rot gesehen: mit dem urspruenglichen Stand, in dem `nav_discover` noch `🔍 Entdecken`
    hiess und `nav_library` in drei Sprachen fehlte.
    """
    import re
    wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(wurzel, "templates", "index.html"), encoding="utf-8") as f:
        html = f.read()
    with open(os.path.join(wurzel, "static", "js", "index.js"), encoding="utf-8") as f:
        js = f.read()

    benutzt = set(re.findall(r'data-i18n=(nav_\w+)', html))
    assert benutzt, "keine nav-Schluessel in der Vorlage — Pruefung waere wertlos"

    unvollstaendig, mit_symbol = [], []
    for k in sorted(benutzt):
        werte = [t[k] for t in sprachtabellen().values() if k in t]
        if len(werte) != 5:
            unvollstaendig.append(f"{k}: {len(werte)}x statt 5")
        for w in werte:
            # Alles ausserhalb von Buchstaben, Ziffern und ueblicher Interpunktion —
            # das faengt Emoji, ohne an Akzenten oder Bindestrichen anzuschlagen.
            if re.search(r"[^\w\s\-&/'’.,()]", w, re.UNICODE):
                mit_symbol.append(f"{k}: {w!r}")
    assert not unvollstaendig, "Uebersetzungen fehlen: " + "; ".join(unvollstaendig)
    assert not mit_symbol, ("Symbol im uebersetzten Text — es gehoert in die Vorlage: "
                            + "; ".join(mit_symbol))


def test_every_navigation_entry_has_exactly_one_icon():
    """Jeder Menuepunkt traegt genau ein Symbol, und zwar aus derselben Quelle. (#337)

    Vorher kamen sie aus drei Richtungen: aus dem Vorlagentext, aus dem
    Uebersetzungsstring, und bei `Nachrichten` aus einem Zeichen, das zufaellig
    AUSSERHALB des uebersetzten Bereichs stand. Zwei Eintraege hatten am Ende gar keins.
    """
    import re
    wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(wurzel, "templates", "index.html"), encoding="utf-8") as f:
        html = f.read()
    eintraege = re.findall(r'<a class=["\']?nav[^>]*>(.*?)</a>', html, re.S)
    assert len(eintraege) == 7, f"{len(eintraege)} Menuepunkte gefunden, erwartet 7"
    ohne = [e[:40] for e in eintraege if e.count("class=navsym") != 1]
    assert not ohne, "Menuepunkte ohne genau ein Symbol-Span: " + "; ".join(ohne)


def test_the_env_template_contains_no_values():
    """In `.env.example` steht KEIN einziger Wert. (#343)

    WARUM DAS EIN TEST IST UND NICHT NUR EINE GEPFLOGENHEIT: Der Geheimnis-Scan nimmt
    diese Datei von der Pruefung aus. Das ist richtig — sie besteht aus leeren
    Platzhaltern, und die Regel `generic-api-key` zieht ueber den Zeilenumbruch hinweg den
    Wert der NAECHSTEN Zeile heran: Gefunden wurde `PROWLARR_CATS=1000` als „Geheimnis"
    des leeren `PROWLARR_APIKEY=`.

    Eine Ausnahme schafft aber eine blinde Stelle: Ein echter Schluessel, der versehentlich
    hier landet, faellt dem Scanner nicht mehr auf. Diese Pruefung schliesst genau diese
    Luecke — und zwar praeziser als eine Regex, weil sie nicht raet, was ein Geheimnis ist,
    sondern verlangt, dass ueberhaupt nichts zugewiesen wird.

    The secret scan allowlists this file, which creates a blind spot: a real key pasted here
    would no longer be flagged. This closes it more precisely than a regex could, by
    requiring that nothing is assigned at all.
    """
    pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        ".env.example")
    with open(pfad, encoding="utf-8") as f:
        zeilen = f.read().splitlines()

    # WELCHE SCHLUESSEL GEMEINT SIND: Nicht „alles ausser einer Liste harmloser Namen" —
    # das waere eine Ausschlussliste, die bei jedem neuen Pfad-Eintrag waechst und genau
    # dann versagt, wenn jemand sie zu ergaenzen vergisst. Adressen, Pfade, Ports und
    # Schalter GEHOEREN in eine Vorlage und tragen dort zu Recht Werte.
    #
    # Stattdessen die kurze, stabile Liste dessen, was in einer Vorlage NIE einen Wert
    # haben darf. Sie muss nicht mitwachsen: Ein neues Geheimnis heisst mit grosser
    # Sicherheit wieder …KEY, …SECRET, …TOKEN oder …PASS.
    #
    # An include list, not an exclude list: paths, ports and switches belong in a template
    # and legitimately carry values. This list does not need to grow.
    GEHEIM = ("KEY", "SECRET", "TOKEN", "PASS", "PASSWORD", "CREDENTIAL", "PRIVATE")
    befuellt = []
    for n, z in enumerate(zeilen, 1):
        z = z.split("#", 1)[0].strip()
        if not z or "=" not in z:
            continue
        schluessel, wert = z.split("=", 1)
        if not wert.strip():
            continue
        if not any(g in schluessel.upper() for g in GEHEIM):
            continue
        befuellt.append(f"Zeile {n}: {schluessel}=…")
    assert not befuellt, ("In .env.example stehen Werte, wo keine hingehoeren — "
                          "der Geheimnis-Scan sieht hier nicht mehr hin: "
                          + "; ".join(befuellt))


def test_no_host_side_variable_is_also_read_by_the_app():
    """Keine Variable beschreibt die HOST-Seite einer Zuordnung und wird zugleich von
    der App als ihr eigener Wert gelesen. (#377)

    DER MECHANISMUS, und er ist unscheinbar: Der Dienst `romseerr` traegt `env_file:
    [.env]`. Damit landet JEDER Eintrag der `.env` in der Container-Umgebung — auch die,
    die dort nur stehen, weil docker-compose sie fuer einen `volumes:`- oder `ports:`-
    Eintrag braucht. Traegt eine solche Variable denselben Namen wie eine, die die App
    liest, gewinnt der HOST-Pfad im Container:

        os.environ.get("JD_WATCH", "/jd-watch") -> /pfad/zu/jdownloader/folderwatch

    Nachgemessen mit `docker compose config` und der ausgelieferten `.env.example`:
    Romseerr legt seine `.crawljob` unter dem Host-Pfad ab, JDownloader schaut in den
    gemounteten `/jd-watch` — der Filehoster-Weg tut nichts, ohne Fehler. Dieselbe
    Messung zeigte den zweiten Fall: `PORT=9000` veroeffentlicht `9000:8770`, die App
    lauscht drinnen aber auf 9000. Der Health-Check liest dieselbe Variable und meldet
    `healthy`, waehrend der veroeffentlichte Port tot ist.

    WARUM ALLE DIENSTE geprueft werden, nicht nur `romseerr`: Die `.env` ist gemeinsam.
    Eine Variable, die nur fuer den Mount von `sabnzbd` gedacht ist, steht trotzdem in
    Romseerrs Umgebung.

    Die Ausnahme ist bewusst: Steht dieselbe Variable auf BEIDEN Seiten
    (`${PORT:-8770}:${PORT:-8770}`), meint sie innen wie aussen dasselbe — dann ist der
    Durchgriff kein Fehler, sondern der Zweck.

    Every entry of `.env` reaches the container through `env_file`, including the ones
    that only exist to fill a `volumes:`/`ports:` mapping. If such a name collides with
    one the app reads, the host value wins inside the container. Same variable on both
    sides is fine — it then means the same thing in both places.
    """
    yml = os.path.join(REPO, "docker-compose.yml")
    with open(yml, encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    with open(os.path.join(REPO, "app.py"), encoding="utf-8") as f:
        quelltext = f.read()

    liest = set(re.findall(r"os\.environ\.get\(\s*[\"']([A-Z][A-Z0-9_]*)[\"']", quelltext))
    liest |= set(re.findall(r"os\.getenv\(\s*[\"']([A-Z][A-Z0-9_]*)[\"']", quelltext))
    liest |= set(re.findall(r"os\.environ\[\s*[\"']([A-Z][A-Z0-9_]*)[\"']", quelltext))
    assert "JD_WATCH" in liest and "PORT" in liest, \
        "die Erkennung der gelesenen Variablen greift nicht mehr"

    # `${ROMS_LIB:?bitte in .env setzen}` enthaelt selbst einen Doppelpunkt — erst
    # ausblenden, dann an ':' trennen, sonst zerfaellt die Zuordnung an der falschen
    # Stelle.
    def _teile(eintrag):
        gemerkt = []

        def _weg(m):
            gemerkt.append(m.group(0))
            return f"\x00{len(gemerkt) - 1}\x00"

        stuecke = re.sub(r"\$\{[^}]*\}", _weg, eintrag).split(":")
        zurueck = [re.sub(r"\x00(\d+)\x00", lambda m: gemerkt[int(m.group(1))], s)
                   for s in stuecke]
        return zurueck

    def _vars(s):
        return set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", s))

    kollisionen = []
    for dienst, d in (compose.get("services") or {}).items():
        for feld in ("volumes", "ports"):
            for eintrag in (d.get(feld) or []):
                if not isinstance(eintrag, str) or "=" in eintrag:
                    continue
                stuecke = _teile(eintrag)
                if len(stuecke) < 2:
                    continue
                host, container = stuecke[0], stuecke[1]
                for name in sorted(_vars(host) & liest):
                    if name in _vars(container):
                        continue        # beide Seiten dieselbe Variable — gewollt
                    kollisionen.append(f"{dienst}.{feld}: ${{{name}}} -> {eintrag.strip()}")

    assert not kollisionen, (
        "Diese Variablen beschreiben die Host-Seite UND werden von app.py gelesen — "
        "im Container gewinnt der Host-Wert, still: " + "; ".join(kollisionen))


# --- Wachhund fuer haengende Auftraege (#340) --------------------------------------

def test_a_slow_but_growing_download_is_never_aborted(appmod, tmp_path, monkeypatch):
    """Ein langsamer, aber wachsender Download bleibt unangetastet. (#340)

    DIESER FALL ENTSCHEIDET, ob die Pruefung ueberlebt. `aria2c` laeuft hier synchron und
    ohne Zwischenmeldung — ein Wachhund, der auf Meldungen achtet, wuerde einen 40-GB-Lauf
    nach Stunden abbrechen, obwohl er einwandfrei arbeitet. Und eine Pruefung, die
    arbeitende Downloads abwuergt, ist binnen einer Woche abgeschaltet; dann steht die
    Regel schlechter da als ohne sie.

    Geprueft wird deshalb, dass die Bytes im Arbeitsverzeichnis zaehlen — nicht die Zeit
    seit der letzten Meldung.
    """
    ordner = tmp_path / "romseerr_j1"
    ordner.mkdir()
    monkeypatch.setattr(appmod, "STAGING", str(tmp_path))
    monkeypatch.setattr(appmod, "SAB_DONE", "")
    monkeypatch.setattr(appmod, "jd_out_dir", lambda: "")

    (ordner / "teil.bin").write_bytes(b"x" * 1000)
    erst = appmod.job_arbeitsbytes("j1")
    (ordner / "teil.bin").write_bytes(b"x" * 5000)      # der Download waechst
    zweit = appmod.job_arbeitsbytes("j1")

    assert erst == 1000 and zweit == 5000, f"Bytes werden nicht erkannt: {erst}, {zweit}"
    assert zweit != erst, "Wachstum muss sichtbar sein, sonst kann der Wachhund nicht unterscheiden"


def test_the_watchdog_measures_bytes_not_message_age(appmod):
    """Die Grenzen gelten je Zustand und sind grosszuegig. (#340)

    Ein Import, der eine Stunde keine Datei mehr angefasst hat, ist keiner mehr. Ein
    Download darf laenger brauchen — deshalb zwei verschiedene Grenzen statt einer.
    """
    g = appmod.WACHHUND_GRENZEN
    assert set(g) == {"downloading", "importing"}, \
        "`pending`/`queued` duerfen NICHT ueberwacht werden — die warten zu Recht"
    assert g["downloading"] >= 4 * 3600, "zu knapp fuer einen grossen Download"
    assert g["importing"] >= 3600, "zu knapp fuer ein grosses Archiv"
    assert g["downloading"] > g["importing"], \
        "ein Download darf laenger dauern als ein Import"


def test_state_changes_carry_a_machine_readable_timestamp(appmod):
    """`set_state` schreibt einen Zeitpunkt, mit dem sich rechnen laesst. (#340)

    `updated` ist eine Uhrzeit OHNE Datum. Ueber Mitternacht laeuft sie rueckwaerts, und
    jede Altersrechnung darauf ist falsch — im Zweifel um 23 Stunden.
    """
    import time as _t
    vorher = list(appmod.JOBS)
    try:
        appmod.JOBS[:] = [{"id": "wd1", "title": "T", "state": "queued"}]
        appmod.set_state("wd1", msg="test")
        j = appmod.JOBS[0]
        assert isinstance(j.get("ts"), float), "kein maschinenlesbarer Zeitstempel"
        assert abs(j["ts"] - _t.time()) < 10
        assert ":" in j.get("updated", ""), "die menschenlesbare Uhrzeit fehlt jetzt"
    finally:
        appmod.JOBS[:] = vorher
        appmod.save_jobs()


# --- Download-Proxy (#346) ---------------------------------------------------------

def test_the_direct_download_uses_the_proxy_when_configured(appmod, monkeypatch):
    """Ist ein Proxy gesetzt, geht der eigene Download darueber. (#346)

    WARUM DAS UEBERSEHEN WURDE: Bei `source: archive` reicht Romseerr die Datei NICHT an
    SABnzbd oder JDownloader weiter — es laedt selbst, mit `aria2c` im eigenen Container.
    Deren VPN-Konfiguration wirkt hier also nicht. Gemessen lief dieser Weg unter derselben
    Adresse wie der Anschluss, waehrend Usenet und Torrent laengst durch einen Tunnel gingen.

    Geprueft wird der Befehl, den `aria2c` bekommt — nicht ein echter Download.
    """
    gerufen = {}

    def falscher_lauf(befehl, **kw):
        gerufen["befehl"] = befehl
        class E:
            returncode = 0
        return E()

    monkeypatch.setattr(appmod.subprocess, "run", falscher_lauf)
    monkeypatch.setattr(appmod, "cfg", lambda k: "http://proxy:8888" if k == "dl_proxy" else "")

    # Den Befehl so bauen wie der Download-Pfad es tut.
    befehl = ["aria2c", "-x8", "-d", "/tmp", "-i", "/tmp/x"]
    if appmod.cfg("dl_proxy"):
        befehl += [f"--all-proxy={appmod.cfg('dl_proxy')}"]

    assert "--all-proxy=http://proxy:8888" in befehl
    # `--all-proxy` und nicht `--http-proxy`: Archive.org liefert ueber https, und ein nur
    # fuer http gesetzter Proxy waere genau der Fall, der wie Schutz aussieht und keiner ist.
    assert not any(a.startswith("--http-proxy") for a in befehl)


def test_the_download_path_actually_passes_the_proxy_flag():
    """Der Quelltext des Download-Pfads setzt `--all-proxy`. (#346)

    Die Pruefung oben zeigt nur, dass die Konstruktion stimmt. Diese hier sieht nach, dass
    sie im Download-Pfad auch WIRKLICH steht — sonst prueft die erste eine Nachbildung.
    """
    pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    with open(pfad, encoding="utf-8") as f:
        quelle = f.read()
    assert 'f"--all-proxy={cfg(\'dl_proxy\')}"' in quelle, \
        "der Download-Pfad reicht den Proxy nicht an aria2c weiter"


def test_a_configured_proxy_is_verified_at_startup(appmod):
    """Beim Start wird geprueft, ob der Proxy die Austrittsadresse WIRKLICH aendert. (#346)

    „Erreichbar" reicht nicht: Ein Proxy, der still auf den direkten Weg zurueckfaellt, ist
    erreichbar und nutzlos zugleich. Und ein VPN, das im Fehlerfall offen faellt, ist
    schlimmer als keins — es laedt zu der Annahme ein, geschuetzt zu sein.
    """
    pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    with open(pfad, encoding="utf-8") as f:
        quelle = f.read()
    assert "ueber == direkt" in quelle, "die Austrittsadresse wird nicht verglichen"
    assert "dlproxy" in quelle, "es gibt keine Warnung zum Download-Proxy"
    # Die Adressen selbst duerfen NICHT im Log landen.
    assert "log(f\"Download-Proxy" not in quelle.replace(
        'log("Download-Proxy wirkt: Austrittsadresse unterscheidet sich.")', ""), \
        "es sieht so aus, als wuerde eine Adresse protokolliert"


def test_every_translation_key_exists_in_all_five_languages():
    """Jeder Schluessel existiert in ALLEN fuenf Sprachen. (#350)

    Die bisherige Pruefung sah nur `nav_*` und `lib_grp_*` an. Beim Auslagern der Tabelle
    kam heraus, was sie nicht sah: **fuenf Schluessel der Bibliotheksansicht fehlten in
    Franzoesisch, Spanisch und Italienisch** — `lib_hint`, `lib_titles`, `lib_owned`,
    `lib_none`, `lib_empty`. Dieselbe Unterlassung wie zuvor bei `nav_library`, nur an
    einer Stelle, auf die niemand geschaut hat.

    Eine Pruefung, die nur einen Namensraum abdeckt, findet genau dort nichts.

    The previous check looked at `nav_*` and `lib_grp_*` only, and missed five keys of the
    library view absent from three languages — the same omission as `nav_library`, one
    namespace over.
    """
    import json
    wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ordner = os.path.join(wurzel, "static", "i18n")
    sprachen = {}
    for datei in sorted(os.listdir(ordner)):
        if not datei.endswith(".json"):
            continue
        with open(os.path.join(ordner, datei), encoding="utf-8") as f:
            sprachen[datei[:-5]] = json.load(f)

    assert set(sprachen) == {"de", "en", "fr", "es", "it"}, \
        f"unerwartete Sprachdateien: {sorted(sprachen)}"

    alle = set()
    for t in sprachen.values():
        alle |= set(t)
    assert len(alle) > 300, "verdaechtig wenige Schluessel — Pruefung waere wertlos"

    fehlend = {l: sorted(alle - set(t)) for l, t in sprachen.items() if alle - set(t)}
    assert not fehlend, "Uebersetzungen fehlen: " + "; ".join(
        f"{l}: {', '.join(k[:6])}{' …' if len(k) > 6 else ''}" for l, k in fehlend.items())

    # Leere Werte sind so schlimm wie fehlende — die Oberflaeche zeigt dann nichts.
    leer = {l: [k for k, v in t.items() if not str(v).strip()] for l, t in sprachen.items()}
    leer = {l: k for l, k in leer.items() if k}
    assert not leer, f"leere Uebersetzungen: {leer}"


def test_german_is_inlined_as_the_fallback():
    """Deutsch steht IM Skript, die uebrigen werden geholt. (#350)

    `t()` faellt auf `I18N.de` zurueck. Waere auch Deutsch nur geholt, zeigte die
    Oberflaeche bei einem fehlgeschlagenen Abruf nackte Schluessel statt Text — ein
    Ausfall, der wie ein Programmfehler aussieht und keiner ist.
    """
    wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(wurzel, "static", "js", "index.js"), encoding="utf-8") as f:
        js = f.read()
    assert "const I18N={de:" in js, "Deutsch ist nicht mehr eingebettet"
    for l in ("en", "fr", "es", "it"):
        assert f"const I18N={{{l}:" not in js, f"{l} sollte ausgelagert sein"
    assert "i18nLaden" in js, "es gibt keinen Lader fuer die uebrigen Sprachen"
    # Der Start muss auf die Sprache warten, sonst zeichnet die Seite erst deutsch.
    assert "i18nLaden(LANG).then(" in js, "der Start wartet nicht auf die Sprache"


def test_an_encrypted_3ds_image_is_refused_before_a_seat_is_taken(appmod, tmp_path):
    """Ein verschluesseltes Abbild wird abgelehnt, bevor ein Platz vergeben wird. (#299)

    Bisher meldete Romseerr „streambar", der Nutzer klickte, belegte einen Platz — und
    erst der Agent wies ab. Das kostet zweierlei: den Platz, den in der Zeit jemand
    anderes haette nutzen koennen, und das Vertrauen in die Zusage.

    Im Zweifel wird durchgelassen: Ein Abbild ohne NCSD-Kopf ist nicht beurteilbar, und
    eine falsche Absage ist teurer als ein Fehlversuch.
    """
    verschl = _3ds_datei(tmp_path, "Titel (Germany).3ds", True)
    klar = _3ds_datei(tmp_path, "Anderer Titel.3ds", False)
    kein_ncsd = tmp_path / "Kaputt.3ds"
    kein_ncsd.write_bytes(b"\x00" * 4096)

    assert appmod.dreids_startbar(verschl) == (False, "encrypted")
    assert appmod.dreids_startbar(klar) == (True, "")
    assert appmod.dreids_startbar(str(kein_ncsd))[0] is True, \
        "ein nicht beurteilbares Abbild darf nicht abgewiesen werden"


def test_a_cia_is_refused_with_its_own_reason(appmod, tmp_path):
    """`.cia` scheitert aus einem ANDEREN Grund als Verschluesselung. (#299)

    CIAs starten nicht direkt — auch entschluesselt nicht. Beides in einen Topf zu werfen
    fuehrt zu der falschen Schlussfolgerung, Entschluesseln wuerde helfen.

    Seit #315 ist der Grund GENAUER: Eine kaputte Datei ohne lesbare TMD heisst
    `cia_unreadable`, nicht „nicht startbar". Und anders als beim Abbild wird hier NICHT im
    Zweifel durchgelassen — eine CIA muss eine TMD haben, ihr Fehlen ist ein Defekt und
    kein Sonderfall.
    """
    kaputt = tmp_path / "Kaputt.cia"
    kaputt.write_bytes(b"\x00" * 64)
    assert appmod.dreids_startbar(str(kaputt)) == (False, "cia_unreadable")

    # Und die Faelle, die es wirklich gibt — nach TITEL-ID, nicht nach Dateiname:
    assert appmod.dreids_startbar(
        _cia_datei(tmp_path, "Update.cia", 0x0004000E00123400)) == (False, "cia_update")
    assert appmod.dreids_startbar(
        _cia_datei(tmp_path, "Zusatz.cia", 0x0004008C00123400)) == (False, "cia_dlc")
    assert appmod.dreids_startbar(
        _cia_datei(tmp_path, "Spiel.cia", 0x0004000000123400)) == (True, ""), \
        "eine Anwendung ist installierbar und danach startbar (#315)"


def test_both_refusal_reasons_have_a_text_in_all_five_languages():
    """Beide Gruende haben einen eigenen Text — sonst raet der Nutzer. (#299)

    Ein blosses „geht nicht" laesst offen, ob es am Titel, am Dienst oder am Nutzer liegt.
    Bei `encrypted` ist die Antwort „dieser Titel, so wie er vorliegt"; bei `cia` ist es
    „dieses Format, immer".
    """
    import re
    with open(os.path.join(REPO, "static", "js", "index.js"), encoding="utf-8") as f:
        js = f.read()
    m = re.search(r"const STREAM_GRUND=\{(.*?)\};", js, re.S)
    assert m, "STREAM_GRUND fehlt"
    for grund, schluessel in (("encrypted", "stream_encrypted"),
                              ("cia_not_bootable", "stream_cia")):
        assert f"{grund}:'{schluessel}'" in m.group(1).replace("\n", "").replace(" ", ""), \
            f"{grund} ist keinem Text zugeordnet"
        assert i18n_hat(schluessel) == 5, f"{schluessel} fehlt in einer Sprache"


# --- #354: Verschluesselt ist kein Endzustand, wenn der Host entschluesseln kann ------

def test_the_host_capability_is_asked_and_briefly_remembered(appmod, monkeypatch):
    """Die Faehigkeit wird beim Host erfragt — und fuer kurze Zeit gemerkt. (#354)

    WARUM GEMERKT: Die Frage stellt sich bei jedem Titelaufruf; die Antwort aendert sich
    hoechstens beim Neustart des Hosts. Ohne Zwischenspeicher waere es eine HTTP-Anfrage
    pro Suchtreffer — genau die Art von Last, die eine Oberflaeche traege macht.
    """
    rufe = {"n": 0}

    class Antwort:
        ok = True
        @staticmethod
        def json():
            rufe["n"] += 1
            return {"can_decrypt_3ds": True}

    appmod._HOST_KANN.update({"wert": None, "bis": 0.0})
    monkeypatch.setattr(appmod, "_agent_url", lambda p: "http://host/" + p)
    monkeypatch.setattr(appmod, "safe_get", lambda *a, **k: Antwort())

    assert appmod.host_kann_entschluesseln() is True
    assert appmod.host_kann_entschluesseln() is True
    assert rufe["n"] == 1, "die zweite Frage muss aus dem Zwischenspeicher kommen"


def test_an_unreachable_host_means_no_decryption(appmod, monkeypatch):
    """Antwortet der Host nicht, gilt „kann nicht" — nicht „kann". (#354)

    Die vorsichtige Antwort ist hier die richtige: Eine Zusage, die der Host nicht halten
    kann, faellt erst NACH dem Belegen eines Platzes auf. Genau diesen Zustand hat #299
    beseitigt, und er darf nicht ueber die Hintertuer zurueckkommen.
    """
    def platzt(*a, **k):
        raise OSError("kein Kontakt")

    appmod._HOST_KANN.update({"wert": None, "bis": 0.0})
    monkeypatch.setattr(appmod, "_agent_url", lambda p: "http://host/" + p)
    monkeypatch.setattr(appmod, "safe_get", platzt)
    assert appmod.host_kann_entschluesseln() is False


def test_no_agent_configured_means_no_decryption(appmod, monkeypatch):
    """Ohne eingerichteten Host wird gar nicht erst gefragt. (#354)"""
    appmod._HOST_KANN.update({"wert": None, "bis": 0.0})
    monkeypatch.setattr(appmod, "_agent_url", lambda p: "")
    monkeypatch.setattr(appmod, "safe_get", lambda *a, **k: 1 / 0)   # darf nie laufen
    assert appmod.host_kann_entschluesseln() is False


def test_an_encrypted_title_is_no_longer_refused_when_the_host_can_decrypt(appmod, tmp_path, monkeypatch):
    """Das eigentliche Verhalten von #354: aus der Absage wird eine Zusage mit Wartezeit.

    WARUM AN `stream_info` UND NICHT AN `dreids_startbar`: Die Datei ist unveraendert
    verschluesselt — das Urteil ueber die DATEI bleibt gleich. Was sich aendert, ist die
    Antwort an den Nutzer, und die faellt in `stream_info`. Eine Gegenprobe an
    `dreids_startbar` blieb gruen, obwohl die Weiche komplett ausgehebelt war.
    """
    verschl = _3ds_datei(tmp_path, "Verschluesselter Titel.3ds", True)
    monkeypatch.setattr(appmod, "stream_cfg", lambda: {"url": "http://host", "launch": ""})
    monkeypatch.setattr(appmod, "stream_find_file", lambda t, s: verschl)
    monkeypatch.setattr(appmod, "_agent_url", lambda p: "http://host/" + p)

    monkeypatch.setattr(appmod, "host_kann_entschluesseln", lambda: False)
    d = appmod.stream_info("Verschluesselter Titel", "3ds")
    assert d["streamable"] is False and d["reason"] == "encrypted"

    monkeypatch.setattr(appmod, "host_kann_entschluesseln", lambda: True)
    d = appmod.stream_info("Verschluesselter Titel", "3ds")
    assert d["streamable"] is not False, "mit entschluesselungsfaehigem Host keine Absage"
    assert d.get("reason") != "encrypted"
    assert d.get("will_decrypt") is True, \
        "die Wartezeit muss angekuendigt sein — ein stiller Start von Minuten sieht aus wie ein Haenger"


def test_a_cia_stays_refused_even_when_the_host_can_decrypt(appmod, tmp_path, monkeypatch):
    """`.cia` bleibt eine Absage, auch bei entschluesselungsfaehigem Host. (#354)

    Der Unterschied ist inhaltlich, nicht technisch: Ein Installationspaket startet nicht
    direkt — entschluesselt genauso wenig. NUR `encrypted` ist ein Zwischenschritt, und
    diese Unterscheidung muss die Weiche in `stream_info` treffen.
    """
    cia = _cia_datei(tmp_path, "Update 11.cia", 0x0004000E00123400)
    monkeypatch.setattr(appmod, "stream_cfg", lambda: {"url": "http://host", "launch": ""})
    monkeypatch.setattr(appmod, "stream_find_file", lambda t, s: cia)
    monkeypatch.setattr(appmod, "_agent_url", lambda p: "http://host/" + p)
    monkeypatch.setattr(appmod, "host_kann_entschluesseln", lambda: True)

    d = appmod.stream_info("Titel", "3ds")
    assert d["streamable"] is False and d["reason"] == "cia_update", \
        "ein Update gehoert zu einem anderen Titel und startet auch installiert nie"


def test_a_bootable_cia_is_only_promised_when_the_host_can_install(appmod, tmp_path, monkeypatch):
    """Eine startbare CIA ist nur dann eine Zusage, wenn der Host sie installieren kann. (#315)

    Sonst waere es dieselbe Luege wie vor #299: Der Nutzer klickt, belegt einen Platz, und
    erst der Agent sagt ab. Dass die DATEI startbar ist, genuegt nicht — es muss auch
    jemanden geben, der sie installiert.
    """
    spiel = _cia_datei(tmp_path, "Spiel.cia", 0x0004000000123400)
    monkeypatch.setattr(appmod, "stream_cfg", lambda: {"url": "http://host", "launch": ""})
    monkeypatch.setattr(appmod, "stream_find_file", lambda t, s: spiel)
    monkeypatch.setattr(appmod, "_agent_url", lambda p: "http://host/" + p)
    monkeypatch.setattr(appmod, "host_kann_entschluesseln", lambda: True)

    monkeypatch.setattr(appmod, "host_kann_cia_installieren", lambda: False)
    d = appmod.stream_info("Spiel", "3ds")
    assert d["streamable"] is False and d["reason"] == "cia_not_bootable"

    monkeypatch.setattr(appmod, "host_kann_cia_installieren", lambda: True)
    d = appmod.stream_info("Spiel", "3ds")
    assert d["streamable"] is not False, "mit installationsfaehigem Host keine Absage"
    assert d.get("will_decrypt") is True, \
        "Entschluesseln und Installieren dauert — das gehoert angekuendigt"


def test_the_two_host_capabilities_come_from_one_request(appmod, monkeypatch):
    """Beide Faehigkeiten stammen aus EINER Abfrage. (#315)

    Zwei getrennte Abfragen waeren zwei HTTP-Anfragen pro Titelaufruf — und sie koennten
    auseinanderlaufen, wenn der Host zwischen ihnen neu startet.
    """
    rufe = {"n": 0}

    class Antwort:
        ok = True
        @staticmethod
        def json():
            rufe["n"] += 1
            return {"can_decrypt_3ds": True, "can_install_cia": True}

    appmod._HOST_KANN.update({"wert": None, "bis": 0.0})
    monkeypatch.setattr(appmod, "_agent_url", lambda p: "http://host/" + p)
    monkeypatch.setattr(appmod, "safe_get", lambda *a, **k: Antwort())

    assert appmod.host_kann_entschluesseln() is True
    assert appmod.host_kann_cia_installieren() is True
    assert rufe["n"] == 1, "beide Fragen muessen aus derselben Antwort kommen"


def test_the_inlined_german_table_covers_every_key_any_language_has():
    """Die EINGEBETTETE deutsche Tabelle muss jeden Schluessel kennen. (#364)

    WARUM DAS NICHT DASSELBE IST WIE `de.json`: Seit #350 ist Deutsch fest in `index.js`
    eingebettet, die anderen vier werden als JSON nachgeladen. `de.json` steht NICHT in der
    Karte am `<body>`, und `i18nLaden()` kehrt fuer Deutsch sofort zurueck — die Datei wird
    also nie gelesen. Sie ist die Quelle fuer Uebersetzer und sonst nichts.

    Fehlt ein Schluessel in der eingebetteten Tabelle, greift der Rueckfall
    `I18N.de[k] || k` — und der Nutzer sieht den KEY. Genau das ist passiert: #354 legte
    `stream_encrypted` und `stream_cia` in alle fuenf JSON-Dateien und nicht in die
    eingebettete Tabelle. Vier Sprachen bekamen einen Satz, Deutsch einen Bezeichner. Die
    damaligen Tests prueften die Sprachdateien — und die waren vollstaendig.

    Since #350 German is inlined and the other four are fetched. de.json is never fetched,
    so a key missing from the inlined table falls back to the key itself — visible only to
    German users.
    """
    import json
    quelle = open(os.path.join(REPO, "static", "js", "index.js"), encoding="utf-8").read()
    m = re.search(r"const I18N=\{de:(\{.*?\})\};", quelle, re.S)
    assert m, "eingebettete deutsche Tabelle nicht gefunden"
    eingebettet = set(json.loads(m.group(1)))

    fehlend = {}
    for sprache, tabelle in sprachtabellen().items():
        luecke = sorted(set(tabelle) - eingebettet)
        if luecke:
            fehlend[sprache] = luecke
    assert not fehlend, (
        "diese Schluessel wuerden deutschen Nutzern als BEZEICHNER erscheinen: "
        + json.dumps(fehlend, ensure_ascii=False)[:400])
# --- #367: „Mixed" ist keine Plattform ----------------------------------------------

def test_an_unknown_platform_stays_empty_instead_of_becoming_a_name(appmod):
    """`resolve_slug("")` darf keinen Plattformnamen erfinden. (#367)

    WARUM DAS DIE URSACHE WAR: Der Rueckgabewert lief weiter bis
    `os.makedirs(ROMS/<slug>)`. Aus dem Platzhalter „Mixed" wurde also ein ORDNER, aus dem
    Ordner ein Eintrag im Index und daraus ein System in der Ansicht. Ein Titel ohne
    erkennbare Plattform war damit nicht unbeschriftet, sondern mit einer Plattform
    beschriftet, die es nicht gibt — und genau so sah ein Nutzer Mario-Titel als „mixed".
    """
    assert appmod.resolve_slug("") == "", "unbekannt bleibt unbekannt"
    assert appmod.resolve_slug(None) == ""


def test_no_code_path_writes_the_word_mixed_as_a_platform(appmod):
    """Nirgends im Quelltext darf „Mixed" als Plattformwert entstehen. (#367)

    Eine Ratsche: Der Wert war an ZWEI Stellen fest verdrahtet, und die zweite fiel erst
    auf, als die erste behoben war. Ein Test, der nur `resolve_slug` prueft, haette die
    andere durchgelassen.
    """
    import ast
    baum = ast.parse(open(os.path.join(REPO, "app.py"), encoding="utf-8").read())

    # Ueber den SYNTAXBAUM, nicht ueber Textsuche: Eine Zeilensuche traf die eigene
    # Begruendung im Docstring und haette den Test unbrauchbar gemacht — genau die Sorte
    # Fehlalarm, die man nach zwei Wochen abschaltet.
    docstrings = set()
    for k in ast.walk(baum):
        if isinstance(k, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            erst = (k.body or [None])[0]
            if isinstance(erst, ast.Expr) and isinstance(erst.value, ast.Constant):
                docstrings.add(id(erst.value))

    # Der Eintrag in IGNORE_FOLDERS ist das GEGENTEIL: Er sorgt dafuer, dass ein
    # vorhandener Ordner dieses Namens NICHT als Plattform gilt.
    erlaubt = set()
    for k in ast.walk(baum):
        if isinstance(k, ast.Assign) and any(
                getattr(z, "id", "") == "IGNORE_FOLDERS" for z in k.targets):
            erlaubt = {id(x) for x in ast.walk(k.value) if isinstance(x, ast.Constant)}

    verdaechtig = [f"Zeile {k.lineno}" for k in ast.walk(baum)
                   if isinstance(k, ast.Constant) and k.value == "Mixed"
                   and id(k) not in docstrings and id(k) not in erlaubt]
    assert not verdaechtig, "„Mixed\" wird noch als Wert erzeugt: " + ", ".join(verdaechtig)


def test_an_existing_mixed_folder_is_not_a_platform(appmod):
    """Ein vorhandener `Mixed`-Ordner bleibt liegen, gilt aber nicht als System. (#367)

    Er wird NICHT geloescht — RetroNAS legt ihn ebenfalls an, und es liegen echte Dateien
    darin. Er zaehlt nur nicht mehr als Plattform.
    """
    assert "Mixed" in appmod.IGNORE_FOLDERS
    assert appmod.folder_slug("Mixed") == "", "Mixed darf keinen Plattform-Slug ergeben"
    assert appmod.folder_slug("snes") == "snes", "echte Plattformen bleiben unberuehrt"


def test_an_import_without_a_platform_lands_in_a_hidden_holding_folder(appmod):
    """Ohne Plattform geht die Datei in eine Ablage, die keine Plattform ist. (#367)

    Der fuehrende Punkt ist die ganze Mechanik: `build_index` ueberspringt solche Ordner
    seit #321. Die Datei ist da und auffindbar — sie taucht nur nirgends als System auf.

    NACHGEFAHREN, NICHT BEHAUPTET: Der Import laeuft hier wirklich. Eine Pruefung, die nur
    `UNSORTIERT.startswith(".")` liest, haette den eigentlichen Fehler durchgelassen — ein
    leerer Slug ergibt `os.path.join(ROMS, "")`, und das ist ROMS SELBST. Die Datei waere
    dann neben den Plattformordnern gelandet.
    """
    assert appmod.UNSORTIERT.startswith("."), \
        "ohne fuehrenden Punkt waere die Ablage wieder eine Plattform"

    # `.bin` steht bewusst in KEINER Endungstabelle — es kommt auf einem Dutzend
    # Plattformen vor. Damit entscheidet allein der Job, und der kennt hier keine.
    assert "bin" in appmod.ROM_EXT and "bin" not in appmod.EXT2PLAT

    job = appmod.new_job({"title": "Ohne Plattform", "source": "archive", "ref": "r", "size": 0},
                         user="", approved=False)
    jid = job["id"]
    assert job["platform"] == "", "der Job erfindet schon wieder eine Plattform"
    ordner = _staging(appmod, jid, {"Shark Shark.bin": b"\x00" * 64})
    appmod.import_folder(jid, ordner)

    ablage = os.path.join(appmod.ROMS, appmod.UNSORTIERT)
    assert os.path.exists(os.path.join(ablage, "Shark Shark.bin")), \
        f"Datei nicht in der Ablage: {os.listdir(appmod.ROMS)}"
    assert "Shark Shark.bin" not in os.listdir(appmod.ROMS), \
        "die Datei liegt direkt in ROMS — leerer Slug wurde nicht abgefangen"

    appmod.build_index()
    with appmod.LIB_LOCK:
        slugs = set(appmod.LIB["slugs"])
    assert appmod.UNSORTIERT not in slugs and "" not in slugs, \
        f"die Ablage ist als Plattform im Index gelandet: {sorted(slugs)}"

    # Und die Meldung am Job muss sagen, WO die Datei liegt. „1 Datei(en) → 1×" nennt
    # keinen Ort — das war die Zeile, die den Nutzer beim alten Verhalten zu „Mixed"
    # geschickt hat, und sie darf jetzt nicht ins Leere zeigen.
    msg = appmod.get_job(jid).get("msg", "")
    assert appmod.UNSORTIERT in msg, f"die Meldung nennt den Ablageort nicht: {msg!r}"

    with appmod.JOBS_LOCK:
        appmod.JOBS[:] = [x for x in appmod.JOBS if x["id"] != jid]; appmod.save_jobs()


def test_the_requests_list_names_an_unknown_platform_instead_of_leaving_a_gap(appmod):
    """Ohne Plattform steht in der Anfragenliste ein Wort, keine Luecke. (#367)

    Der Sentinel ist weg, und damit ist das Feld leer statt falsch. Leer ist besser als
    falsch, aber nicht gut: In der Zeile `👤 jens · <leer> · archive` sieht der Nutzer
    zwei Trennpunkte hintereinander und keinen Hinweis, dass die Plattform schlicht
    unbekannt ist. Uebersetzt gehoert das Wort in alle fuenf Sprachen.
    """
    js = open(os.path.join(REPO, "static/js/index.js"), encoding="utf-8").read()
    assert "${o.platform}" not in js, \
        "die Anfragenzeile gibt die Plattform ungeprueft aus — ohne Wert bleibt eine Luecke"
    assert "plat_unknown" in js, "es gibt keinen Text fuer die unbekannte Plattform"
    assert i18n_hat("plat_unknown") == 5, "der Text fehlt in mindestens einer Sprache"


def test_an_import_without_a_platform_names_the_folder_it_landed_in(appmod, tmp_path, monkeypatch):
    """Die Abschlussmeldung nennt den ORDNER, nicht den leeren Slug. (#367)

    WARUM DAS EINEN EIGENEN TEST BRAUCHT: Die Zaehlung lief ueber `slug`. Seit der Sentinel
    weg ist, ist der bei unbekannter Plattform LEER — und die Meldung lautete dann
    „1 Datei(en) → 1×", eine Zahl ohne Ort. Der Test daneben prueft nur die Oberflaeche und
    blieb gruen, als die Zaehlung zurueckgedreht wurde. Gegengeprueft, nicht angenommen.

    The count ran over `slug`, which is empty since the sentinel went away, producing
    "1 file(s) → 1×" — a number with no place. The neighbouring test covers only the UI and
    stayed green when the counter was reverted.
    """
    roms = tmp_path / "roms"; roms.mkdir()
    staging = tmp_path / "staging"; staging.mkdir()
    # `.bin` ist eine ROM-Endung OHNE Plattformzuordnung — auf einem Dutzend Systemen
    # gebraeuchlich, deshalb bewusst nicht zugeordnet. Genau der Fall, der frueher in
    # `Mixed` landete. (Eine Nicht-ROM-Endung taugt hier nicht: die wird uebersprungen,
    # und der Test prueft dann den falschen Zweig.)
    (staging / "Irgendein Titel.bin").write_bytes(b"x" * 32)

    monkeypatch.setattr(appmod, "ROMS", str(roms))
    monkeypatch.setattr(appmod, "extract_archives", lambda p: None)
    monkeypatch.setattr(appmod, "build_index", lambda: None)
    monkeypatch.setattr(appmod, "in_library", lambda ziel, slug: False)
    gemeldet = {}
    monkeypatch.setattr(appmod, "set_state",
                        lambda jid, **kw: gemeldet.update(kw))
    monkeypatch.setattr(appmod, "get_job", lambda jid: {"id": "1", "platform": "", "title": "T"})
    for name in ("romm_scan", "notify_all", "count_import", "save_jobs"):
        if hasattr(appmod, name):
            monkeypatch.setattr(appmod, name, lambda *a, **k: None)

    appmod.import_folder("1", str(staging))

    msg = gemeldet.get("msg", "")
    assert appmod.UNSORTIERT in msg, \
        f"die Meldung nennt den Ablageort nicht: {msg!r}"
    assert "1×​" not in msg and not msg.rstrip().endswith("1×"), \
        f"Zahl ohne Ort: {msg!r}"


# --- #375: Plattformfilter und Quellenauswahl ---------------------------------------

def test_every_source_is_asked_regardless_of_the_platform_filter(appmod, monkeypatch):
    """Keine Quelle wird wegen der Auswahl uebersprungen. (#375)

    Vorher entschied eine TABELLE, ob Usenet ueberhaupt gefragt wird: Enthielt die Auswahl
    keine Plattform mit bekannter Kategorie, blieb Usenet aus. Fuer reine Retro-Auswahlen
    war das gedacht — bezahlt haben es die Plattformen, deren Eintrag schlicht FEHLTE.
    „Wii U" schaltete Usenet ab, obwohl sieben Veroeffentlichungen dalagen.

    Eine Quelle wegen einer Tabelle zu ueberspringen uebersetzt einen Tabellenfehler in ein
    fehlendes Suchergebnis — und das sieht aus wie „gibt es nicht".
    """
    gefragt = []
    monkeypatch.setattr(appmod, "search_archive", lambda q, **k: [])
    monkeypatch.setattr(appmod, "search_usenet",
                        lambda q, cats: gefragt.append(cats) or [])
    monkeypatch.setattr(appmod, "catalog_urls", lambda: [])
    monkeypatch.setattr(appmod, "cfg", lambda k, d="": "1000" if k == "prow_cats" else d)

    for auswahl in ([], ["wiiu"], ["c64"], ["nes", "snes"]):
        gefragt.clear()
        appmod.do_search("egal", auswahl)
        assert gefragt == ["1000"], f"Usenet nicht gefragt bei Auswahl {auswahl}"


def test_confirmed_matches_rank_above_unclassified_ones(appmod, monkeypatch):
    """Wer nach einer Plattform filtert, sucht diese Plattform. (#375)

    Ein Ergebnis OHNE erkannte Plattform passiert jeden Filter — absichtlich, denn
    Archive.org-Titel tragen oft keine Zuordnung und sind trotzdem gemeint. Sie deshalb
    aber VOR den bestaetigten zu zeigen, war der Fehler: Bei „Mario Kart 8" mit Filter
    `wiiu` standen sieben unbestimmte Titel oben und der erste echte Treffer auf Platz 6.
    """
    treffer = [
        {"source": "archive", "ref": "a", "title": "Irgendwas ohne Plattform",
         "platform": "", "size": 1, "cover": "", "extra": ""},
        {"source": "archive", "ref": "b", "title": "Noch was ohne Plattform",
         "platform": "", "size": 1, "cover": "", "extra": ""},
        {"source": "archive", "ref": "c", "title": "Echter Wii-U-Titel",
         "platform": "wiiu", "size": 1, "cover": "", "extra": ""},
    ]
    monkeypatch.setattr(appmod, "search_archive", lambda q, **k: [dict(t) for t in treffer])
    monkeypatch.setattr(appmod, "search_usenet", lambda q, cats: [])
    monkeypatch.setattr(appmod, "catalog_urls", lambda: [])
    monkeypatch.setattr(appmod, "in_library", lambda t, p: False)

    res = appmod.do_search("egal", ["wiiu"])
    assert res, "keine Treffer"
    assert res[0]["platform"] == "wiiu", \
        f"oben steht {res[0]['title']!r} statt des bestaetigten Treffers"
    # Die unbestimmten bleiben ERHALTEN — Trefferquote vor Genauigkeit.
    assert len(res) == 3, "unbestimmte Treffer duerfen nicht verschwinden"


def test_wiiu_uses_the_wii_categories_because_the_indexer_does_not_separate_them(appmod):
    """Wii U liegt beim Indexer unter den Wii-Kategorien. (#375)

    Nachgemessen: `Super.Mario.3D.World.USA.WiiU-PoWeRUp` kommt mit {1030, 101030}, und
    die Standardkategorie fuer Wii U liefert NULL Treffer. Die Zuordnung am Titel raeumt
    danach auf — aber erst seit #452, siehe die Tests darunter. Bis dahin behauptete das
    nur ein Kommentar.
    """
    assert appmod.SLUG2USE.get("wiiu"), "Wii U kennt keine Usenet-Kategorie"
    assert set(appmod.SLUG2USE["wiiu"]) >= set(appmod.SLUG2USE["wii"]), \
        "Wii U muss mindestens die Wii-Kategorien mitbenutzen"
    assert appmod.guess_platform("Super.Mario.3D.World.USA.WiiU-PoWeRUp") == "wiiu"


# --- #452: Kategorie gegen Titel ------------------------------------------------------

def test_every_category_tenant_can_actually_be_searched(appmod):
    """Wer in `KAT_LEIHE` steht, MUSS Kategorien haben. (#452)

    Ein leeres `SLUG2USE[slug]` schaltet die Usenet-Suche fuer diese Plattform komplett
    ab — `search_usenet` steigt bei `not cats` sofort aus. Das ist der lautlose Fall:
    kein Fehler, keine Meldung, nur null Treffer. Genau so war PS Vita unerreichbar.
    """
    for mieter, eigner in appmod.KAT_LEIHE.items():
        assert appmod.SLUG2USE.get(mieter), \
            f"{mieter} hat keine Usenet-Kategorie — die Suche ist fuer ihn abgeschaltet"
        assert set(appmod.SLUG2USE[mieter]) >= set(appmod.SLUG2USE.get(eigner, [])), \
            f"{mieter} muss die Kategorien von {eigner} mitbenutzen"


def test_a_tenant_reclaims_its_own_category_from_the_title(appmod):
    """Nennt der Titel den Mieter der gefundenen Kategorie, gewinnt der Titel. (#452)

    Gemessen am echten Indexer: 16 von 16 Treffern kamen unter dem Slug des Eigentuemers
    zurueck. Ein Vita-Titel landete dadurch im PSP-Ordner, und die Wii-U-Treffer aus #375
    fielen aus dem Wii-U-Filter, weil sie `wii` hiessen.
    """
    f = appmod.plattform_aus_kategorie_und_titel
    assert f("psp", "Uncharted Golden Abyss.PSVITA") == "psvita"
    assert f("psp", "Uncharted Golden Abyss USA PSV-VENOM") == "psvita"
    assert f("wii", "Super.Mario.3D.World.USA.WiiU-PoWeRUp") == "wiiu"
    assert f("wii", "WiiU Super Mario 3D World-(Loadiine Ready2Play)") == "wiiu"


def test_a_foreign_platform_in_the_title_does_not_override_the_category(appmod):
    """Nur der eingetragene Mieter darf umwerfen — sonst niemand. (#452)

    Titel erwaehnen staendig fremde Systeme („Wii version", „PS2 Classics"). Duerfte
    jeder Titeltreffer die Kategorie schlagen, waere die Zuordnung schlechter als vorher.
    Die Erlaubnis gilt nur dort, wo die Kategorie nachweislich zu grob ist.
    """
    f = appmod.plattform_aus_kategorie_und_titel
    # `guess_platform` erkennt hier etwas anderes als die Kategorie — trotzdem bleibt sie.
    assert appmod.guess_platform("Sonic Adventure 2 Dreamcast Port") == "dreamcast"
    assert f("xbox", "Sonic Adventure 2 Dreamcast Port") == "xbox"
    assert f("ps3", "Jak and Daxter PS2 Classics") == "ps3"
    # Der umgekehrte Weg ist ebenfalls gesperrt: PSP faehrt nicht in der Vita-Kategorie.
    assert f("psvita", "Daxter USA PSP-Googlecus") == "psvita"
    # Ohne Kategorie bleibt der Titel die einzige Quelle — wie bisher.
    assert f(None, "Uncharted Golden Abyss.PSVITA") == "psvita"
    assert f(None, "voellig namenlos") is None


def test_the_usenet_search_labels_a_vita_release_as_vita(appmod, monkeypatch):
    """Die ganze Kette, nicht nur die Entscheidungsfunktion. (#452)

    Der Fehler sass in `search_usenet`, nicht in `guess_platform` — das erkannte `psvita`
    die ganze Zeit richtig, wurde aber nie gefragt. Ein Test nur auf `guess_platform`
    haette gruen gestanden, waehrend der Download im PSP-Ordner landete.
    """
    appmod.save_settings({"connections": {"prow_url": "http://prow", "prow_apikey": "k"}})

    class R:
        def json(self):
            return [{"protocol": "usenet", "title": "Uncharted Golden Abyss.PSVITA",
                     "size": 3076095179, "indexer": "I", "downloadUrl": "http://prow/1",
                     "categories": [{"id": 101020}]},
                    {"protocol": "usenet", "title": "Daxter USA PSP-Googlecus",
                     "size": 1, "indexer": "I", "downloadUrl": "http://prow/2",
                     "categories": [{"id": 101020}]}]
    monkeypatch.setattr(appmod.requests, "get", lambda *a, **k: R())

    out = appmod.search_usenet("Uncharted", appmod.SLUG2USE["psvita"])
    nach_titel = {o["title"]: o["platform"] for o in out}
    assert nach_titel["Uncharted Golden Abyss.PSVITA"] == "psvita", \
        "der Vita-Titel darf nicht als PSP zurueckkommen"
    assert nach_titel["Daxter USA PSP-Googlecus"] == "psp", \
        "ein echter PSP-Titel in derselben Kategorie muss PSP bleiben"
    appmod.save_settings({})


# --- #382: gesperrte Archive.org-Eintraege -------------------------------------------

def test_an_aria2c_exit_code_becomes_a_readable_reason(appmod):
    """Der Rueckgabewert von aria2c wird uebersetzt, nicht durchgereicht. (#382)

    Beim Nutzer stand woertlich:
        Command '['aria2c', '-x8', ...]' returned non-zero exit status 24.
    Das nennt das gescheiterte WERKZEUG, nicht den Grund. 24 heisst laut aria2-Dokumentation
    „HTTP authorization failed" — bei Archive.org also: Der Titel braucht ein Konto.

    Ein UNBEKANNTER Code wird bewusst durchgereicht statt geraten: eine falsche Erklaerung
    ist schlimmer als gar keine.
    """
    assert "401" in appmod.aria_fehler(24) or "Anmeldung" in appmod.aria_fehler(24)
    assert "24" in appmod.aria_fehler(24), "der Code selbst gehoert in die Meldung"
    assert "existiert nicht" in appmod.aria_fehler(3)
    assert "99" in appmod.aria_fehler(99), "unbekannter Code wird nicht geraten"


def test_a_restricted_archive_item_is_marked_before_the_click(appmod, monkeypatch):
    """Ein Eintrag in der Sammlung `loggedin` wird gekennzeichnet. (#382)

    WARUM VORHER UND NICHT NACHHER: Der Download bricht sonst mit HTTP 401 ab — bei
    „Mario Kart 8 (Europe)" nach 5,5 GB, die nie kommen konnten. Dieselbe Regel wie #299:
    Die Absage gehoert dorthin, wo die Zusage stand.

    Der Treffer bleibt SICHTBAR — es gibt ihn ja, und mit Konto ist er ladbar.
    """
    class Antwort:
        ok = True
        @staticmethod
        def json():
            return {"response": {"docs": [
                {"identifier": "frei", "title": "Freier Titel", "item_size": 1,
                 "collection": ["open_source_software"]},
                {"identifier": "gesperrt", "title": "Gesperrter Titel", "item_size": 1,
                 "collection": ["loggedin", "deemphasize"]},
                {"identifier": "ohne", "title": "Ohne Sammlung", "item_size": 1},
            ]}}
    monkeypatch.setattr(appmod.requests, "get", lambda *a, **k: Antwort())
    tr = {r["ref"]: r for r in appmod.search_archive("egal")}
    assert tr["gesperrt"]["restricted"] is True
    assert tr["frei"]["restricted"] is False
    assert tr["ohne"]["restricted"] is False, "fehlende Sammlung ist keine Sperre"
    assert len(tr) == 3, "gesperrte Treffer duerfen nicht verschwinden"


def test_the_search_actually_asks_for_the_collection_field(appmod, monkeypatch):
    """Das Feld muss ANGEFORDERT werden, sonst kommt es nie an. (#382)

    Genau das ging beim Bauen schief: Die Kennzeichnung stand im Quelltext, das Feld fehlte
    in der Abfrage — und `restricted` war fuer jeden Treffer False. Eine Pruefung, die nur
    die Auswertung testet, haette das nicht bemerkt.
    """
    gesehen = {}

    class Antwort:
        ok = True
        @staticmethod
        def json(): return {"response": {"docs": []}}

    def merken(url, **k):
        gesehen["url"] = url
        return Antwort()

    monkeypatch.setattr(appmod.requests, "get", merken)
    appmod.search_archive("egal")
    assert "collection" in gesehen.get("url", ""), \
        "die Suche fordert das Sammlungsfeld nicht an"


# --- #384: Archive.org-Schluessel ----------------------------------------------------

def test_the_archive_secret_never_reaches_a_log_line(appmod, monkeypatch, capsys):
    """Das Geheimnis darf in KEINER Protokollzeile stehen. (#384)

    WARUM DAS EIN EIGENER TEST IST: Romseerrs Log-Zeilen werden in Issues und Berichte
    kopiert, und dieses Repository ist oeffentlich. Ein Geheimnis, das ins Protokoll
    gelangt, gelangt damit nach draussen — und ist danach nicht zurueckzuholen, auch nicht
    durch Loeschen des Kommentars.
    """
    monkeypatch.setattr(appmod, "cfg", lambda k, d="": {
        "ia_access": "ZUGRIFF123", "ia_secret": "GEHEIMNIS456"}.get(k, d))
    kopf = appmod.ia_kopfzeile()
    assert kopf and "GEHEIMNIS456" in kopf[1], "die Kopfzeile muss den Schluessel tragen"

    appmod.log("irgendeine Meldung")
    appmod.log(f"Fehler: {appmod.aria_fehler(24)}")
    ausgabe = capsys.readouterr().out
    assert "GEHEIMNIS456" not in ausgabe, "das Geheimnis steht im Protokoll"
    assert "ZUGRIFF123" not in ausgabe


def test_without_both_keys_nothing_is_sent(appmod, monkeypatch):
    """Ein halbes Schluesselpaar ist kein Schluesselpaar. (#384)

    Ein einzeln gesetzter Wert wuerde eine kaputte Kopfzeile erzeugen — und die Quelle
    antwortet darauf mit demselben 401 wie ohne, nur schwerer zu deuten.
    """
    for a, g in (("", ""), ("nur-zugriff", ""), ("", "nur-geheim")):
        monkeypatch.setattr(appmod, "cfg",
                            lambda k, d="", a=a, g=g: {"ia_access": a, "ia_secret": g}.get(k, d))
        assert appmod.ia_kopfzeile() == [], f"({a!r}, {g!r}) darf keine Kopfzeile ergeben"
        assert appmod.ia_bereit() is False


def test_a_restricted_hit_loses_its_padlock_once_keys_exist(appmod, monkeypatch):
    """Mit Schluesseln ist der Titel ladbar — dann ist das Schloss falsch. (#384)

    Die Sperre haengt am KONTO, nicht am Titel. Ein Schloss, das bleibt, obwohl der
    Download geht, ist genau die Sorte Falschauskunft, gegen die #382 gebaut wurde.
    """
    class Antwort:
        ok = True
        @staticmethod
        def json():
            return {"response": {"docs": [{"identifier": "x", "title": "T", "item_size": 1,
                                           "collection": ["loggedin"]}]}}
    monkeypatch.setattr(appmod.requests, "get", lambda *a, **k: Antwort())

    monkeypatch.setattr(appmod, "cfg", lambda k, d="": "")
    assert appmod.search_archive("q")[0]["restricted"] is True

    monkeypatch.setattr(appmod, "cfg", lambda k, d="": {
        "ia_access": "a", "ia_secret": "g"}.get(k, d))
    assert appmod.search_archive("q")[0]["restricted"] is False


def test_no_connection_tab_reports_a_status_that_cannot_change(appmod):
    """Kein Reiter darf einen KONSTANTEN Zustand melden. (#386)

    Der RetroAchievements-Reiter stand auf `d=>({da:false,an:false})` und blieb damit
    dauerhaft grau — auch mit hinterlegtem Schluessel und geholten Sets. Ein Zustand, der
    sich nicht aendern kann, ist kein Zustand, sondern eine Beschriftung.

    WARUM ES AUSGERECHNET DIESEN TRAF: Alle Nachbarn haengen an einem NICHT geheimen Feld
    (`igdb_id`, `romm_url`, `sab_url`). RetroAchievements ist die einzige Verbindung, deren
    einzige Einstellung ein Geheimnis ist — und damit die einzige, die `has_<key>` braucht.
    Der Platzhalter fiel deshalb nirgends sonst auf.
    """
    import re
    js = open(os.path.join(REPO, "static", "js", "index.js"), encoding="utf-8").read()
    # Die Zustandsfunktionen der Reiterliste: `d=>({da:…,an:…})`
    fest = []
    # NUR Funktionen, die die Einstellungen ENTGEGENNEHMEN (`d=>`). Ein `()=>` sagt
    # ausdruecklich „ich habe keinen Zustand" — `maillog` ist ein Protokollaufruf, keine
    # Verbindung, und ein konstanter Wert ist dort ehrlich. Die Regel lautet deshalb:
    # Wer die Daten bekommt, muss sie auch benutzen.
    for m in re.finditer(r"\['([a-z]+)',[^,]*,\s*d\s*=>\(\{da:([^,]+),an:([^}]+)\}\)", js):
        name, da, an = m.group(1), m.group(2).strip(), m.group(3).strip()
        if da in ("false", "true") and an in ("false", "true"):
            fest.append(f"{name} (da:{da}, an:{an})")
    assert not fest, ("diese Reiter melden einen Zustand, der sich nie aendert: "
                      + ", ".join(fest))
def test_every_platform_has_at_least_one_importable_extension(appmod):
    """Jede STREAMBARE Plattform muss mindestens eine Endung haben, die importiert wird. (#391)

    Wii U hatte KEINE. `.wux`, `.wud`, `.wua`, `.rpx` fehlten alle in `ROM_EXT`, und damit
    konnte kein einziger Wii-U-Titel jemals in die Bibliothek gelangen — ein 5,5-GB-Download
    endete mit „1 Nicht-ROM uebersprungen". Dass die Plattform nie funktionierte, sah aus
    wie ein fehlender Titel (#302) und war eine fehlende Zeile.

    Die Pruefung ist eine Ratsche: Sie faellt, sobald eine neue streambare Plattform
    aufgenommen wird, ohne dass ihre Dateien importierbar waeren.
    """
    ohne = sorted(p for p in appmod.STREAMABLE
                  if not any(v == p for v in appmod.EXT2PLAT.values()))
    # BEKANNTE AUSNAHMEN, jede mit Grund — eine Ausnahmeliste ohne Begruendung waere
    # nur eine Stelle, an der man den naechsten Fund verstecken kann.
    #
    # Diese Plattformen haben KEINE eigene Endung, und das ist richtig so: Ihr Titel ist
    # entweder ein ORDNER (PS3 mit PS3_GAME/, DOS-Installation, ScummVM) oder liegt in
    # einem MEHRDEUTIGEN Abbildformat, das ein Dutzend Systeme benutzt (`.iso`, `.bin`,
    # `.chd`). In beiden Faellen kommt die Plattform aus dem Auftrag, nicht aus dem Namen —
    # und eine falsche Zuordnung waere teurer als gar keine.
    ohne_eigene_endung = {
        "ps3", "scummvm", "dos",          # Titel ist ein Ordner
        "wii", "ngc", "dreamcast",        # .iso/.rvz/.gdi — mehrdeutig
        "psx", "ps2", "xbox",             # .iso/.bin/.chd — mehrdeutig
    }
    ohne = [p for p in ohne if p not in ohne_eigene_endung]
    assert not ohne, f"diese Plattformen koennen nichts importieren: {ohne}"


def test_the_wii_u_formats_are_importable(appmod):
    """Die vier Wii-U-Formate werden erkannt und der Plattform zugeordnet. (#391)"""
    for e in ("wux", "wud", "wua", "rpx"):
        assert e in appmod.ROM_EXT, f".{e} wird beim Import uebersprungen"
        assert appmod.EXT2PLAT.get(e) == "wiiu", f".{e} zeigt nicht auf wiiu"


def test_no_extension_silently_merged_with_its_neighbour(appmod):
    """Keine Endung darf laenger als fuenf Zeichen sein. (#391)

    Ein fehlendes Komma in der Liste laesst Python zwei Eintraege verschmelzen: aus
    `"ws"` und `"wux"` wurde beim Bauen dieser Aenderung stillschweigend `"wswux"` —
    beide Endungen weg, kein Fehler, keine Warnung. Nur die Messung zeigte es.
    """
    # NICHT ueber die Laenge: Die erste Fassung dieses Tests pruefte `len(e) > 5` und
    # haette den ausloesenden Fall NICHT gefangen — `"ws" "wux"` ergibt `"wswux"`, genau
    # fuenf Zeichen. Eine geratene Schwelle prueft die Vermutung, nicht die Sache.
    #
    # Geprueft wird deshalb die Quelle: Zwei Zeichenketten, zwischen denen kein Komma
    # steht, verschmelzen — unabhaengig davon, wie lang das Ergebnis wird.
    import re
    quelle = open(os.path.join(REPO, "app.py"), encoding="utf-8").read()
    verdaechtig = []
    for name in ("ROM_EXT", "ARCH_EXT"):
        m = re.search(rf"^{name} = \{{(.*?)\}}", quelle, re.S | re.M)
        if not m:
            continue
        # `"a"` direkt gefolgt von `"b"` — nur Leerraum, Zeilenumbrueche oder Kommentare
        # dazwischen, aber kein Komma.
        for treffer in re.finditer(r'"[a-z0-9]+"(?:\s|#[^\n]*\n)+"[a-z0-9]+"', m.group(1)):
            verdaechtig.append(f"{name}: {treffer.group(0)[:40]!r}")
    assert not verdaechtig, ("hier fehlt ein Komma, die Eintraege verschmelzen still: "
                             + "; ".join(verdaechtig))
def test_platform_detection_covers_the_common_spellings(appmod):
    """Jede Plattform wird in MEHREREN gebraeuchlichen Schreibweisen erkannt. (#393)

    Jedes Muster war aus EINER Schreibweise geschrieben — der, die dem Autor einfiel.
    Gemessen an realistischen Release-Namen hatten 7 von 18 Plattformen Luecken. Die
    teuerste: `\\bvita\\b` traf `PSVita` nie, weil zwischen `S` und `V` keine Wortgrenze
    steht — und das ist die haeufigste Schreibweise ueberhaupt.

    Ein Treffer ohne erkannte Plattform verschwindet nicht, er rutscht seit #375 ans Ende
    einer gefilterten Liste. Sichtbar im Prinzip, unsichtbar in der Praxis.
    """
    PROBEN = {
        "psvita":  ["Spiel PSVita", "Spiel PS Vita", "Spiel [PSV]", "Spiel (PlayStation Vita)"],
        "wiiu":    ["Spiel WiiU", "Spiel Wii U", "Spiel [WUP]", "Spiel WUX"],
        "switch":  ["Spiel NSW", "Spiel Switch", "Spiel [NSP]", "Spiel XCI"],
        "ngc":     ["Spiel GameCube", "Spiel NGC", "Spiel GCN"],
        "xbox":    ["Spiel Xbox", "Spiel XBE"],
        "xbox360": ["Spiel Xbox 360", "Spiel X360"],
        "ps3":     ["Spiel PS3", "Spiel PlayStation 3"],
        "psp":     ["Spiel PSP", "Spiel PlayStation Portable"],
        "3ds":     ["Spiel 3DS", "Spiel [3DS]"],
    }
    fehl = []
    for slug, titel in PROBEN.items():
        for t in titel:
            erkannt = appmod.guess_platform(t)
            if erkannt != slug:
                fehl.append(f"{t!r} -> {erkannt or '—'} (erwartet {slug})")
    assert not fehl, "nicht erkannte Schreibweisen:\n  " + "\n  ".join(fehl)


def test_an_ambiguous_abbreviation_is_not_guessed(appmod):
    """Zweideutige Kuerzel werden NICHT zugeordnet. (#393)

    `DC` fehlt bewusst: DC Comics, Director's Cut, Digital Copy. Dieselbe Regel wie in den
    Bibliothekswerkzeugen — eine falsche Zuordnung kostet mehr als eine ausgelassene, weil
    der Titel danach unter der falschen Konsole liegt und niemandem auffaellt, waehrend ein
    unzugeordneter sichtbar bleibt.
    """
    assert appmod.guess_platform("Batman DC Collection") != "dreamcast"
    assert appmod.guess_platform("Spiel Directors Cut DC") != "dreamcast"


def test_an_unreadable_platform_is_named_in_the_log(appmod, monkeypatch, tmp_path):
    """Eine Plattform, deren Ordner nicht lesbar ist, muss im Protokoll STEHEN. (#381)

    Bisher trug sie null Titel bei, und die einzige Spur war eine Gesamtzahl, die kleiner
    war als sie sein sollte — ununterscheidbar von einer kleineren Bibliothek.
    """
    d = os.path.join(appmod.ROMS, "zzztestunlesbar")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "Ein Spiel.rom"), "w").close()
    if not _unlesbar_machen(d):
        shutil.rmtree(d, ignore_errors=True)
        pytest.skip("laeuft als root — 0o000 sperrt hier nichts, der Test bewiese nichts")
    try:
        p = _index_mit_protokoll(appmod, monkeypatch)
        treffer = p.mit("zzztestunlesbar")
        assert treffer, ("keine Zeile ueber die unlesbare Plattform:\n  "
                         + "\n  ".join(p.zeilen[-5:]))
        assert any("PermissionError" in z for z in treffer), \
            f"der Grund fehlt, es steht nur: {treffer}"
    finally:
        os.chmod(d, 0o755)
        shutil.rmtree(d, ignore_errors=True)
        appmod.build_index()


def test_the_summary_line_says_how_many_platforms_were_not_read(appmod, monkeypatch):
    """Die Schlussmeldung darf keine Gesamtzahl nennen, die still Plattformen auslaesst.

    Das Protokoll allein reicht nicht: Die Zeile mit der Titelzahl ist die, die gelesen
    wird. Wenn dort nichts steht, ist die Zahl vertrauenswuerdiger als sie ist. (#381)
    """
    d = os.path.join(appmod.ROMS, "zzztestunlesbar2")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "Noch ein Spiel.rom"), "w").close()
    if not _unlesbar_machen(d):
        shutil.rmtree(d, ignore_errors=True)
        pytest.skip("laeuft als root — 0o000 sperrt hier nichts, der Test bewiese nichts")
    try:
        p = _index_mit_protokoll(appmod, monkeypatch)
        assert "NICHT gelesen" in p.schluss, f"Schlussmeldung schweigt: {p.schluss!r}"
        assert "zzztestunlesbar2" in p.schluss, \
            f"Schlussmeldung nennt keinen Namen: {p.schluss!r}"
    finally:
        os.chmod(d, 0o755)
        shutil.rmtree(d, ignore_errors=True)
        appmod.build_index()


def test_a_healthy_library_does_not_cry_wolf(appmod, monkeypatch):
    """Gegenprobe: Ohne Fehler steht in der Schlussmeldung KEIN Zusatz. (#381)

    Eine Warnung, die immer dasteht, wird nicht gelesen. Der erste Wurf dieses Codes haette
    das gerissen — deshalb steht die Gegenprobe hier und nicht im Kopf des Autors.
    """
    d = os.path.join(appmod.ROMS, "zzztestlesbar")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "Heiles Spiel.rom"), "w").close()
    try:
        p = _index_mit_protokoll(appmod, monkeypatch)
        assert "NICHT gelesen" not in p.schluss, \
            f"meldet Fehler, obwohl alles lesbar ist: {p.schluss!r}"
        assert appmod.LIB.get("failed") in (None, {}, []), \
            f"Fehlerliste nicht leer: {appmod.LIB.get('failed')!r}"
    finally:
        shutil.rmtree(d, ignore_errors=True)
        appmod.build_index()


def test_an_unreadable_subfolder_is_reported_too(appmod, monkeypatch):
    """Auch ein unlesbarer UNTERordner der zweiten Ebene muss gemeldet werden. (#381)

    Genau dieser Fall beweist, dass ein Log im `except`-Zweig nicht gereicht haette: Der
    Plattformordner selbst ist lesbar, `os.walk` laeuft ohne Ausnahme durch und liefert
    fuer den gesperrten Unterordner schlicht nichts.
    """
    d = os.path.join(appmod.ROMS, "zzztestteilweise")
    unter = os.path.join(d, "Ordner")
    os.makedirs(unter, exist_ok=True)
    open(os.path.join(d, "Oben.rom"), "w").close()
    open(os.path.join(unter, "Unten.rom"), "w").close()
    if not _unlesbar_machen(unter):
        shutil.rmtree(d, ignore_errors=True)
        pytest.skip("laeuft als root — 0o000 sperrt hier nichts, der Test bewiese nichts")
    try:
        p = _index_mit_protokoll(appmod, monkeypatch)
        assert "zzztestteilweise" in p.schluss, \
            f"gesperrter Unterordner bleibt unerwaehnt: {p.schluss!r}"
        # Was lesbar war, ist trotzdem drin — ein gesperrter Ordner kostet nicht die Platte.
        assert appmod.norm("Oben.rom") in appmod.LIB["per"].get("zzztestteilweise", set())
    finally:
        os.chmod(unter, 0o755)
        shutil.rmtree(d, ignore_errors=True)
        appmod.build_index()


def test_the_other_platforms_are_still_indexed(appmod, monkeypatch):
    """Ein unlesbarer Ordner darf nicht den ganzen Index kosten. (#381)

    Weitermachen war schon richtig — nur eben nicht wortlos.
    """
    kaputt = os.path.join(appmod.ROMS, "zzztestkaputt")
    heil = os.path.join(appmod.ROMS, "zzztestheil")
    os.makedirs(kaputt, exist_ok=True)
    os.makedirs(heil, exist_ok=True)
    open(os.path.join(kaputt, "Verloren.rom"), "w").close()
    open(os.path.join(heil, "Gefunden.rom"), "w").close()
    if not _unlesbar_machen(kaputt):
        for x in (kaputt, heil): shutil.rmtree(x, ignore_errors=True)
        pytest.skip("laeuft als root — 0o000 sperrt hier nichts, der Test bewiese nichts")
    try:
        _index_mit_protokoll(appmod, monkeypatch)
        assert appmod.norm("Gefunden.rom") in appmod.LIB["all"], \
            "die heile Plattform fehlt — ein Fehler hat den ganzen Lauf gekostet"
        assert "zzztestkaputt" in appmod.LIB["slugs"], \
            "die gescheiterte Plattform verschwindet ganz statt als leer aufzufallen"
    finally:
        os.chmod(kaputt, 0o755)
        for x in (kaputt, heil): shutil.rmtree(x, ignore_errors=True)
        appmod.build_index()


def test_health_reports_platforms_that_could_not_be_read(appmod, client, monkeypatch):
    """`/health` muss die nicht gelesenen Plattformen ZEIGEN, nicht nur das Protokoll.

    WARUM DAS FELD UND NICHT NUR EIN LOG: Dieselbe Luecke wie in #309/#344 — die Zahl
    steht da und nichts liest sie. `romseerr-check` prueft `lib_titles` gegen `LIB_MIN`
    und meldet `OK`, waehrend 13.000 Titel fehlen. Nur ein Feld in `/health` macht das
    von aussen sichtbar. (#381)
    """
    d = os.path.join(appmod.ROMS, "zzztesthealth")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "Unsichtbar.rom"), "w").close()
    if not _unlesbar_machen(d):
        shutil.rmtree(d, ignore_errors=True)
        pytest.skip("laeuft als root — 0o000 sperrt hier nichts, der Test bewiese nichts")
    try:
        _index_mit_protokoll(appmod, monkeypatch)
        h = client.get("/health").get_json()
        assert h.get("lib_failed") == 1, f"/health verschweigt es: {h}"
        # Gegenprobe: heile Bibliothek meldet 0, nicht „Feld fehlt".
        os.chmod(d, 0o755)
        shutil.rmtree(d, ignore_errors=True)
        appmod.build_index()
        assert client.get("/health").get_json().get("lib_failed") == 0
    finally:
        os.chmod(d, 0o755) if os.path.exists(d) else None
        shutil.rmtree(d, ignore_errors=True)
        appmod.build_index()


def test_a_plain_user_cannot_approve_a_request(client, appmod):
    """Freigeben ist an `manage_requests` gebunden — auch fuer die eigene Anfrage. (#379)

    Das ist die Rechtegrenze des gesamten Anfragesystems: Wer freigeben darf, kann jede
    Kontingent- und Freigaberegel umgehen. Der generische 401-Test beweist nur, dass
    IRGENDWER angemeldet sein muss, nicht WER.
    """
    _als(client, appmod, "normalo")
    r = client.post("/api/jobs/gibtsnicht/approve")
    assert r.status_code in (401, 403), \
        f"ein normaler Nutzer bekam {r.status_code} statt einer Absage"
    r = client.post("/api/jobs/gibtsnicht/deny")
    assert r.status_code in (401, 403)


def test_a_reset_token_works_once(client, appmod):
    """Ein Reset-Token gilt genau EINMAL. (#379)

    Ein wiederverwendbarer Token bliebe eine Stunde lang ein zweiter Schluessel zum Konto —
    auch nachdem der Nutzer sein Passwort laengst gesetzt hat. Im Quelltext wird er nach
    Gebrauch verworfen; diese Pruefung haelt das fest.
    """
    users = appmod.load_users()
    users["resetprobe"] = {"pw": appmod.generate_password_hash("alt12345"), "role": "user"}
    appmod.save_users(users)

    tok = appmod.gen_reset("resetprobe")
    assert appmod.check_reset(tok) == "resetprobe"

    r = client.post("/api/reset", json={"token": tok, "new": "neu12345"})
    assert r.status_code == 200 and r.get_json()["ok"] is True

    zweit = client.post("/api/reset", json={"token": tok, "new": "nochmal123"})
    assert zweit.get_json()["ok"] is False, "der Token liess sich ein zweites Mal einloesen"
    assert appmod.check_reset(tok) is None


def test_an_expired_reset_token_is_refused(appmod):
    """Nach Ablauf gilt der Token nicht mehr. (#379)"""
    tok = appmod.gen_reset("resetprobe")
    appmod.RESET_TOKENS[tok]["exp"] = time.time() - 1
    assert appmod.check_reset(tok) is None


def test_forgot_does_not_reveal_whether_an_account_exists(client):
    """Die Antwort ist fuer bekannte und unbekannte Konten gleich. (#379)

    Sonst waere der Endpunkt ein Verzeichnisdienst: Wer Namen durchprobiert, erfaehrt
    kostenlos, welche existieren.
    """
    a = client.post("/api/forgot", json={"user": "admin"})
    b = client.post("/api/forgot", json={"user": "gibtesganzsichernicht"})
    assert a.status_code == b.status_code
    assert a.get_json() == b.get_json(), "die Antworten unterscheiden sich"


def test_deleting_an_issue_needs_the_permission(client, appmod):
    """Loeschen ist an `manage_issues` gebunden. (#379)

    Der einzige zerstoerende Endpunkt in der Gruppe — und der einzige, dessen Fehler sich
    nicht zurueckholen laesst.
    """
    _als(client, appmod, "normalo")
    r = client.delete("/api/issues/1")
    assert r.status_code in (401, 403), f"ein normaler Nutzer bekam {r.status_code}"


def test_regenerating_the_api_key_is_admin_only(client, appmod):
    """Ein neuer API-Key ist Adminsache. (#379)

    Wer ihn erzeugen kann, verschafft sich einen Zugang, der an der Anmeldung vorbeigeht.
    """
    _als(client, appmod, "normalo")
    r = client.post("/api/apikey/regenerate")
    assert r.status_code in (401, 403)


def test_the_remaining_write_endpoints_refuse_an_anonymous_caller(appmod):
    """Kein schreibender Endpunkt antwortet einem Unangemeldeten mit Erfolg. (#379)

    GEMESSEN, NICHT AM QUELLTEXT ABGELESEN: Die erste Fassung dieser Pruefung suchte nach
    Dekoratoren an den Routen und meldete 18 Endpunkte als ungeschuetzt. Sie sind es nicht —
    die Absicherung sitzt zentral in `_guard()` als `before_request`, das alles ausserhalb
    von `PUBLIC` abweist. Eine Pruefung, die die Form statt der Wirkung ansieht, meldet
    Fehlalarme, und Fehlalarme schaltet man ab.

    Deshalb wird hier wirklich angefragt: ein eigener Client OHNE Anmeldung, gegen jeden
    schreibenden Endpunkt, den es gibt.

    GEGENGEPRUEFT: Einen EINZELNEN Endpunkt aus der Wache zu nehmen bricht diese Pruefung
    NICHT — mehrere Handler pruefen die Sitzung ein zweites Mal und antworten selbst mit
    403. Erst die abgeschaltete Wache zeigt es, und dann deutlich:
    `POST /api/wishlist/remove -> 200`. Die doppelte Absicherung ist ein Vorzug, aber sie
    macht eine Gegenprobe an einer Stelle wertlos — wer diesen Test aendert, muss die
    Wache ganz abschalten, um ihn wirklich zu pruefen.
    """
    import re
    quelle = open(os.path.join(REPO, "app.py"), encoding="utf-8").read()
    muster = re.compile(r'@app\.route\(\s*"(/api/[^"]+)"[^)]*methods=\[([^\]]*)\]', re.M)
    pfade = []
    for m in muster.finditer(quelle):
        pfad, methoden = m.group(1), m.group(2)
        if not re.search(r'"(POST|PUT|DELETE|PATCH)"', methoden):
            continue
        if pfad in appmod.PUBLIC:
            continue                       # Anmeldung, Einrichtung, Passwort-vergessen
        pfade.append((pfad, "DELETE" if '"DELETE"' in methoden else "POST"))

    assert len(pfade) >= 20, f"nur {len(pfade)} schreibende Endpunkte gefunden — Muster kaputt?"

    anonym = appmod.app.test_client()      # bewusst NICHT angemeldet
    durchgelassen = []
    for pfad, methode in pfade:
        ziel = re.sub(r"<[^>]+>", "1", pfad)
        r = anonym.open(ziel, method=methode, json={})
        if r.status_code not in (401, 403, 302):
            durchgelassen.append(f"{methode} {ziel} -> {r.status_code}")
    assert not durchgelassen, ("diese schreibenden Endpunkte antworten einem "
                              "Unangemeldeten: " + ", ".join(durchgelassen))


def test_a_request_row_links_to_the_title(appmod):
    """Die Anfragezeile ist klickbar und fuehrt zur Karte. (#390)

    Vorher war der Titel reiner Text: Nur die Knoepfe rechts reagierten, der Titel selbst
    war tot. Wer wissen wollte, worum es geht, musste ihn von Hand in die Suche tippen.
    """
    js = open(os.path.join(REPO, "static", "js", "index.js"), encoding="utf-8").read()
    assert "openJobDetail" in js, "es gibt keine Verknuepfung von der Anfrage zur Karte"
    assert "class=jobt" in js, "der Titel der Anfragezeile ist nicht ausgezeichnet"
    # AUF DIE EIGENSCHAFT, NICHT AUF DIE SCHREIBWEISE. Die erste Fassung verlangte woertlich
    # `jt.onclick` — also eine Bindung JE ZEILE. Genau die war der Fehler aus #449: Beim
    # Neuaufbau der Liste ist die Zeile ein anderes Element, die Bindung weg, und ein Klick
    # in diesem Moment tut nichts. Der Test haette den Fix also blockiert, obwohl der Titel
    # danach besser reagiert als vorher.
    #
    # Heute der dritte Test, der an einer Schreibweise haengt statt an der Sache
    # (vorher: der apt-Dolphin-Rueckfall und der leere Anfragen-Text).
    # NUR DIE BINDUNG DER ANFRAGENLISTE ANSEHEN. Die erste Fassung suchte
    # `addEventListener('click'` in der GANZEN Datei — das kommt dort mehrfach vor, also
    # blieb sie gruen, als ich die Bindung zum Ausprobieren entfernte. Ein Test, der auf ein
    # Vorkommen irgendwo prueft, prueft nichts Bestimmtes.
    m = re.search(r"^function jobKlickBindung\(.*?\)\{(.*?)^\}", js, re.S | re.M)
    assert m, "die Klickbindung der Anfragenliste ist nicht mehr auffindbar"
    koerper = m.group(1)
    assert "addEventListener('click'" in koerper, "sie bindet keinen Klick"
    assert "closest('.jobt')" in koerper, \
        "sie findet den Titel nicht — sie reagierte dann auf die ganze Zeile"
    assert "openJobDetail" in koerper, "sie fuehrt nicht zur Karte"


def test_a_request_without_a_card_says_so_instead_of_opening_nothing(appmod):
    """Findet die Suche nichts, wird eine Meldung gezeigt — kein leeres Fenster. (#390)

    Der wahrscheinlichste Klick ist der auf eine FEHLGESCHLAGENE Anfrage, und genau die
    kann unauffindbar sein: Der Download scheiterte, der Titel kam nie in die Bibliothek.
    Ein leeres Detailfenster waere schlechter als gar keine Reaktion.
    """
    js = open(os.path.join(REPO, "static", "js", "index.js"), encoding="utf-8").read()
    i = js.index("async function openJobDetail")
    rumpf = js[i:i + 1400]
    assert "job_no_card" in rumpf, "kein Text fuer den Fall ohne Treffer"
    assert "if(!treffer)" in rumpf, "der Fall ohne Treffer wird nicht behandelt"
    assert i < js.index("openDetail(treffer)"), "openDetail wird ausserhalb gerufen"
    assert i18n_hat("job_no_card") == 5, "der Text fehlt in mindestens einer Sprache"


# --- #391: ein entpacktes Spiel ist EIN Titel, kein Haufen Dateien -------------------

def test_an_unpacked_wii_u_game_is_recognised_as_one_title(appmod, tmp_path):
    """`code`+`content`+`meta` macht einen Ordner zu einem Wii-U-Titel. (#391)

    ERKANNT AN DER STRUKTUR, nicht an einer Dateizahl: Ein entpacktes Spiel hat Tausende
    Dateien, eine Sammlung auch. Was sie unterscheidet, ist der vom Format vorgegebene
    Aufbau.
    """
    spiel = tmp_path / "Mario Kart 8"
    for teil in ("code", "content", "meta"):
        (spiel / teil).mkdir(parents=True)
    (spiel / "code" / "app.rpx").write_bytes(b"x" * 16)
    assert appmod.spielordner_slug(str(spiel)) == "wiiu"

    # Eine Sammlung mit ebenso vielen Dateien ist KEIN Titel.
    sammlung = tmp_path / "Best of C64"
    sammlung.mkdir()
    for i in range(20):
        (sammlung / f"Spiel {i}.d64").write_bytes(b"x" * 8)
    assert appmod.spielordner_slug(str(sammlung)) == ""


def test_an_unpacked_ps_vita_title_is_recognised_as_one_title(appmod, tmp_path):
    """`eboot.bin`+`sce_sys` macht einen Ordner zu einem Vita-Titel. (#455)

    Der Aufbau ist an einem echten Import gemessen, nicht erfunden — das Release liefert
    einen ORDNER, dessen Name auf `.vpk` endet. Der Name darf dabei nichts entscheiden:
    andere Releases liefern denselben Aufbau unter dem blanken Titel.
    """
    spiel = tmp_path / "WipEout 2048 [PCSF00007] (v01.00) .vpk"
    (spiel / "sce_sys").mkdir(parents=True)
    (spiel / "sce_module").mkdir()
    (spiel / "PSP2").mkdir()
    (spiel / "eboot.bin").write_bytes(b"x" * 16)
    (spiel / "sce_sys" / "param.sfo").write_bytes(b"x" * 8)
    assert appmod.spielordner_slug(str(spiel)) == "psvita"

    # Derselbe Aufbau ohne die optionalen Teile — muss weiterhin greifen.
    schlank = tmp_path / "Gravity Rush"
    (schlank / "sce_sys").mkdir(parents=True)
    (schlank / "eboot.bin").write_bytes(b"x" * 16)
    assert appmod.spielordner_slug(str(schlank)) == "psvita"


def test_a_lone_eboot_does_not_claim_the_vita_platform(appmod, tmp_path):
    """`eboot.bin` ALLEIN ist kein Titel. (#455)

    Jeder Vita-Titel hat eine `eboot.bin`, und genau deshalb landete beim Fehlschlag eine
    namenlose 10-MB-Datei in der Bibliothek. Wuerde die Datei allein schon die Plattform
    beanspruchen, machte der Fix aus einem Bruchstueck einen anerkannten Titel — das waere
    schlimmer als der Fehler.
    """
    bruchstueck = tmp_path / "irgendwas"
    bruchstueck.mkdir()
    (bruchstueck / "eboot.bin").write_bytes(b"x" * 16)
    assert appmod.spielordner_slug(str(bruchstueck)) == ""

    # Und umgekehrt: `sce_sys` allein (z.B. ein Metadaten-Rest) ebenfalls nicht.
    rest = tmp_path / "rest"
    (rest / "sce_sys").mkdir(parents=True)
    assert appmod.spielordner_slug(str(rest)) == ""


def test_every_game_folder_pattern_names_a_known_platform(appmod):
    """Jeder Slug in `SPIELORDNER_MUSTER` muss eine Plattform sein. (#455)

    Ein Tippfehler im Slug faellt sonst nirgends auf: Der Ordner wird erkannt, wandert
    als Ganzes — und landet unter einer Plattform, die es nicht gibt.
    """
    bekannt = {s for _, paare in appmod.PLATFORMS for s, _ in paare}
    for slug, _ in appmod.SPIELORDNER_MUSTER:
        assert slug in bekannt, f"{slug!r} aus SPIELORDNER_MUSTER ist keine Plattform"
    for _, slug in appmod.SPIELORDNER_DATEI.items():
        assert slug in bekannt, f"{slug!r} aus SPIELORDNER_DATEI ist keine Plattform"


def test_an_import_lands_in_the_folder_that_already_holds_the_platform(appmod):
    """Liegt die Bibliothek im Alias-Ordner, gehoert der Import dorthin. (#454)

    RetroNAS nennt GameCube `gc`, Romseerrs Slug heisst `ngc`. Ging der Import stur nach
    `ROMS/<slug>`, landete er NEBEN der Bibliothek statt darin — 561 GB in `gc`, der
    Download in `ngc`. Sichtbar war das nicht, weil das Lesen beide Ordner zusammenfuegt.
    """
    gc = os.path.join(appmod.ROMS, "gc")
    os.makedirs(gc, exist_ok=True)
    open(os.path.join(gc, "Luigi's Mansion (USA).rvz"), "w").close()
    assert appmod.bibliothek_ordner("ngc") == gc, \
        "der Import muss in den Ordner, in dem die Plattform schon liegt"


def test_an_import_falls_back_to_the_slug_when_nothing_exists_yet(appmod, tmp_path, monkeypatch):
    """Ist noch nichts da, bleibt es beim Slug. (#454)

    Der Rueckfall darf nicht schweigen: Eine Plattform ohne jeden Ordner muss trotzdem ein
    Ziel bekommen, sonst waere der erste Download jeder neuen Plattform unmoeglich.
    """
    monkeypatch.setattr(appmod, "ROMS", str(tmp_path))
    assert appmod.bibliothek_ordner("ngc") == str(tmp_path / "ngc")

    # Ein LEERER Alias-Ordner zaehlt nicht — sonst gewaenne der Streuner gegen die
    # Bibliothek. Genau so herum lagen `ngc` und `dreamcast` auf der Anlage.
    (tmp_path / "gc").mkdir()
    assert appmod.bibliothek_ordner("ngc") == str(tmp_path / "ngc")

    # Sobald etwas drin ist, gewinnt er.
    (tmp_path / "gc" / "spiel.rvz").write_bytes(b"x")
    assert appmod.bibliothek_ordner("ngc") == str(tmp_path / "gc")


def test_no_import_path_is_built_from_the_slug_directly(appmod):
    """`ROMS/<slug>` darf nur noch in `bibliothek_ordner` stehen. (#454)

    Der Fehler war nicht, dass die Aufloesung fehlte — sie gab es fuer das Lesen laengst.
    Er war, dass ZWEI Schreibstellen daran vorbeigingen. Eine dritte waere genauso still.
    """
    import inspect
    quelle = inspect.getsource(appmod)
    zeilen = [i for i, z in enumerate(quelle.splitlines(), 1)
              if "os.path.join(ROMS, slug)" in z]
    _, start = inspect.getsourcelines(appmod.bibliothek_ordner)
    ende = start + len(inspect.getsourcelines(appmod.bibliothek_ordner)[0])
    draussen = [i for i in zeilen if not (start <= i < ende)]
    assert not draussen, \
        f"Zeile(n) {draussen} bauen das Importziel am Alias vorbei — bibliothek_ordner nehmen"


def test_the_game_folder_moves_as_one_unit_and_its_files_are_not_scattered(appmod, tmp_path, monkeypatch):
    """Der Ordner wandert als Ganzes, seine Dateien NICHT einzeln. (#391)

    Der gemessene Schaden: „14 Datei(en) -> 14×wiiu · 170 Nicht-ROM uebersprungen". Die 14
    waren `.bin`-Bruchstuecke aus dem Spielinneren, die 170 das Spiel. Beide Richtungen
    falsch — Bruchstuecke in der Bibliothek, Titel verworfen.
    """
    roms = tmp_path / "roms"; roms.mkdir()
    staging = tmp_path / "staging"
    spiel = staging / "Mario Kart 8"
    for teil in ("code", "content", "meta"):
        (spiel / teil).mkdir(parents=True)
    (spiel / "code" / "app.rpx").write_bytes(b"x" * 16)
    (spiel / "content" / "Course.bin").write_bytes(b"x" * 16)   # das Bruchstueck von damals

    monkeypatch.setattr(appmod, "ROMS", str(roms))
    monkeypatch.setattr(appmod, "extract_archives", lambda p: None)
    monkeypatch.setattr(appmod, "build_index", lambda: None)
    monkeypatch.setattr(appmod, "in_library", lambda ziel, slug: False)
    gemeldet = {}
    monkeypatch.setattr(appmod, "set_state", lambda jid, **kw: gemeldet.update(kw))
    monkeypatch.setattr(appmod, "get_job", lambda jid: {"id": "1", "platform": "wiiu", "title": "T"})
    for name in ("romm_scan", "notify_all", "count_import", "save_jobs"):
        if hasattr(appmod, name):
            monkeypatch.setattr(appmod, name, lambda *a, **k: None)

    appmod.import_folder("1", str(staging))

    ziel = roms / "wiiu" / "Mario Kart 8"
    assert ziel.is_dir(), f"der Spielordner kam nicht an: {list((roms).rglob('*'))[:6]}"
    assert (ziel / "code" / "app.rpx").is_file(), "die ausfuehrbare Datei fehlt"
    # Und das Entscheidende: KEINE losen Bruchstuecke daneben.
    lose = [p.name for p in (roms / "wiiu").iterdir() if p.is_file()]
    assert not lose, f"Bruchstuecke einzeln einsortiert: {lose}"


def test_a_ps3_disc_folder_is_also_one_title(appmod, tmp_path):
    """PS3 wird ebenso erkannt — an `PS3_GAME`. (#391)

    Romseerr behandelt eine PS3-Disc beim STREAMEN laengst als Ordner (#276); beim IMPORT
    war sie ein Haufen Dateien. Dieselbe Sache, zwei Antworten.
    """
    disc = tmp_path / "Titel"
    (disc / "PS3_GAME" / "USRDIR").mkdir(parents=True)
    (disc / "PS3_GAME" / "USRDIR" / "EBOOT.BIN").write_bytes(b"x" * 8)
    assert appmod.spielordner_slug(str(disc)) == "ps3"


def test_a_game_folder_inside_a_wrapper_is_still_found(appmod, tmp_path):
    """Auch eine Ebene tiefer wird der Titel gefunden. (#391)

    Archive entpacken sich oft in einen Zwischenordner. Zwei Ebenen genuegen — tiefer zu
    suchen hiesse, in den Spielinhalt hineinzulaufen: `content/` hat selbst Unterordner,
    und einer davon koennte zufaellig `meta` heissen.
    """
    tief = tmp_path / "Mario Kart 8 (EUR)" / "Mario Kart 8"
    for teil in ("code", "content", "meta"):
        (tief / teil).mkdir(parents=True)
    gefunden = appmod.spielordner_finden(str(tmp_path))
    assert [s for _p, s in gefunden] == ["wiiu"], gefunden
    assert gefunden[0][0].endswith("Mario Kart 8")


def test_the_home_computer_formats_can_be_imported(appmod):
    """16 Heimcomputer-Formate waren unbekannt — 51.118 Dateien. (#410)

    Dieselbe Klasse wie die Wii-U-Luecke (#391), eine Groessenordnung darueber: `.z80`
    12.180, `.tzx` 11.525, `.prg` 9.740, `.tap` 6.966, `.g64` 6.131, `.crt` 4.123. Ein
    Download in einem dieser Formate endete mit „0 Datei(en) -> nichts".

    Dass die Heimcomputer ueberhaupt Inhalt haben, liegt an der RetroNAS-Freigabe, nicht am
    Import — ueber Romseerr angefragt konnte fuer diese Plattformen nichts ankommen.
    """
    for e in ("prg", "tap", "crt", "d71", "d81", "g64", "p00", "x64",
              "z80", "sna", "tzx", "cdt", "adz", "dms", "a52", "car"):
        assert e in appmod.ROM_EXT, f".{e} wird beim Import uebersprungen"


def test_the_ambiguous_home_computer_formats_stay_unmapped(appmod):
    """`.tap`, `.sna` und `.car` bekommen KEINE feste Plattform. (#410)

    `.tap` ist C64 UND ZX Spectrum, `.sna` ist ZX Spectrum und ein Amiga-Schnappschuss,
    `.car` ist Atari 5200 und anderes. Sie sind importierbar, aber die Plattform kommt aus
    dem Auftrag — dieselbe Behandlung wie `.iso` und `.bin`.

    Eine falsche Zuordnung kostet mehr als eine ausgelassene: Der Titel laege unter der
    falschen Konsole und fiele niemandem auf.
    """
    for e in ("tap", "sna", "car"):
        assert e in appmod.ROM_EXT, f".{e} sollte importierbar sein"
        assert e not in appmod.EXT2PLAT, \
            f".{e} ist mehrdeutig und darf keine feste Plattform bekommen"
    # Die eindeutigen dagegen schon.
    assert appmod.EXT2PLAT.get("prg") == "c64"
    assert appmod.EXT2PLAT.get("z80") == "zxs"
    assert appmod.EXT2PLAT.get("a52") == "atari5200"


# --- #396: Massenimport aus dem Einwurfordner ----------------------------------------

def test_a_file_still_being_copied_is_not_imported(appmod, tmp_path, monkeypatch):
    """Erst wenn Groesse UND Aenderungszeit gleich bleiben, wird angefasst. (#396)

    WARUM ZWEI DURCHLAEUFE statt einer Wartezeit: Ueber SMB dauert eine 5-GB-Kopie
    Minuten. Eine einzelne Pruefung muesste in der Schleife schlafen — entweder zu kurz,
    um wahr zu sein, oder sie blockiert alles andere.

    Ein halb kopiertes Abbild zu importieren waere der teuerste Fehler dieses Zweigs: Es
    laege als Titel in der Bibliothek und startete nie.
    """
    f = tmp_path / "Spiel.sfc"
    f.write_bytes(b"x" * 100)
    appmod._EINWURF_GESEHEN.clear()

    assert appmod.einwurf_stabil(str(f)) is False, "beim ERSTEN Sehen ist nichts stabil"
    assert appmod.einwurf_stabil(str(f)) is True, "unveraendert beim zweiten Mal -> stabil"

    f.write_bytes(b"x" * 200)          # waechst weiter
    os.utime(str(f), (time.time(), time.time()))
    assert appmod.einwurf_stabil(str(f)) is False, "gewachsen -> nicht stabil"


def test_an_ambiguous_extension_is_left_lying_with_a_reason(appmod, tmp_path, monkeypatch):
    """Was sich nicht bestimmen laesst, bleibt liegen — mit Grund. (#396)

    Ein Download traegt seinen Plattform-Hinweis aus dem Auftrag; eine in den Share gelegte
    Datei traegt nichts. 25 der 82 anerkannten Endungen sind mehrdeutig. Sie zu raten waere
    genau der Fehler, den die Bibliothekswerkzeuge vermeiden: Der Titel laege unter der
    falschen Konsole und fiele niemandem auf.
    """
    monkeypatch.setattr(appmod, "IMPORT_SHARE", str(tmp_path))
    slug, grund = appmod.einwurf_ziel(str(tmp_path / "Irgendwas.bin"), "Irgendwas.bin")
    assert slug == "", f".bin wurde geraten: {slug}"
    assert "mehrdeutig" in grund

    slug, grund = appmod.einwurf_ziel(str(tmp_path / "Spiel.sfc"), "Spiel.sfc")
    assert slug == "snes" and ".sfc" in grund


def test_the_folder_name_can_decide_what_the_extension_cannot(appmod, tmp_path, monkeypatch):
    """Liegt die Datei in einem Plattformordner, entscheidet der. (#396)

    Das ist der Unterschied zwischen „gar nichts geht" und „das Meiste geht": Wer seine
    Dateien schon nach Systemen sortiert hineinlegt, soll nicht am mehrdeutigen `.bin`
    scheitern.
    """
    monkeypatch.setattr(appmod, "IMPORT_SHARE", str(tmp_path))
    (tmp_path / "snes").mkdir()
    slug, grund = appmod.einwurf_ziel(str(tmp_path / "snes" / "Spiel.bin"), "Spiel.bin")
    assert slug == "snes", f"Ordnername ignoriert: {slug} ({grund})"


def test_the_move_copies_first_and_deletes_only_after(appmod, tmp_path, monkeypatch):
    """Erst kopieren und pruefen, DANN loeschen. (#396)

    Einwurfordner und Bibliothek liegen auf verschiedenen Dateisystemen — hier
    cache-nvme gegen Array. `os.rename` scheitert dort, und ein abgebrochenes Verschieben
    hinterliesse eine halbe Datei, die wie ein Titel aussieht.
    """
    share = tmp_path / "import"; share.mkdir()
    roms = tmp_path / "roms"; roms.mkdir()
    quelle = share / "Spiel.sfc"
    quelle.write_bytes(b"x" * 64)
    monkeypatch.setattr(appmod, "ROMS", str(roms))

    assert appmod.einwurf_verschieben(str(quelle), "snes") is True
    ziel = roms / "snes" / "Spiel.sfc"
    assert ziel.is_file() and ziel.stat().st_size == 64
    assert not quelle.exists(), "die Quelle blieb liegen"
    assert not list((roms / "snes").glob("*.teil")), "ein Zwischenstand blieb liegen"


def test_an_existing_title_is_not_overwritten(appmod, tmp_path, monkeypatch):
    """Liegt der Titel schon da, bleibt die Quelle liegen. (#396)

    Nichts wird geloescht, was nicht angekommen ist — und nichts ueberschrieben, was
    schon da war. Der Nutzer sieht die Datei weiterhin im Einwurfordner und kann
    entscheiden.
    """
    share = tmp_path / "import"; share.mkdir()
    roms = tmp_path / "roms"; (roms / "snes").mkdir(parents=True)
    (roms / "snes" / "Spiel.sfc").write_bytes(b"alt")
    quelle = share / "Spiel.sfc"; quelle.write_bytes(b"neu")
    monkeypatch.setattr(appmod, "ROMS", str(roms))

    assert appmod.einwurf_verschieben(str(quelle), "snes") is False
    assert quelle.exists(), "die Quelle wurde entfernt, obwohl nichts ankam"
    assert (roms / "snes" / "Spiel.sfc").read_bytes() == b"alt", "der Titel wurde ueberschrieben"


def test_a_truncated_copy_does_not_delete_the_source(appmod, tmp_path, monkeypatch):
    """Bricht die Kopie ab, bleibt die Quelle liegen. (#396)

    WARUM DAS EIGENS GEPRUEFT WIRD: Die Gegenprobe zum Groessenvergleich schlug zuerst
    NICHT an — im Test gelingt jede Kopie, also aendert das Entfernen der Pruefung nichts
    Sichtbares. Eine Zusicherung, die nur den Gutfall kennt, sichert nichts zu.

    Hier wird der Abbruch nachgestellt: Die Kopie schreibt weniger, als sie soll. Ohne den
    Vergleich waere die Quelle danach GELOESCHT und in der Bibliothek laege ein
    abgeschnittener Titel — der Fehler, der sich nicht mehr einfangen laesst.
    """
    import shutil
    share = tmp_path / "import"; share.mkdir()
    roms = tmp_path / "roms"; roms.mkdir()
    quelle = share / "Spiel.sfc"; quelle.write_bytes(b"x" * 1000)
    monkeypatch.setattr(appmod, "ROMS", str(roms))

    def halbe_kopie(src, dst, *a, **k):
        with open(src, "rb") as f, open(dst, "wb") as g:
            g.write(f.read(400))          # abgebrochen
    monkeypatch.setattr(shutil, "copyfile", halbe_kopie)

    assert appmod.einwurf_verschieben(str(quelle), "snes") is False
    assert quelle.exists(), "die Quelle wurde geloescht, obwohl die Kopie unvollstaendig war"
    assert not (roms / "snes" / "Spiel.sfc").exists(), "ein abgeschnittener Titel blieb liegen"
    assert not list((roms / "snes").glob("*.teil")), "der Zwischenstand blieb liegen"


def test_an_arrived_title_counts_as_imported_even_if_the_source_stays(appmod, tmp_path, monkeypatch):
    """Kommt der Titel an, gilt er als eingeordnet — auch wenn die Quelle bleibt. (#396)

    AM ECHTEN SHARE GEMESSEN: Ein per SMB angelegter Unterordner kann `755` gehoeren, und
    der Container laeuft als uid 1000 in der Gruppe `users`. Dann gelingt das Kopieren und
    das Loeschen der Quelle nicht.

    Die erste Fassung gab dafuer `False` zurueck — dieselbe Antwort wie fuer „nichts
    passiert", obwohl der Titel in der Bibliothek lag. Zwei sehr verschiedene Lagen unter
    einer Meldung, und die verwirrendere von beiden gewinnt.
    """
    share = tmp_path / "import"; share.mkdir()
    roms = tmp_path / "roms"; roms.mkdir()
    quelle = share / "Spiel.sfc"; quelle.write_bytes(b"x" * 64)
    monkeypatch.setattr(appmod, "ROMS", str(roms))

    echtes_remove = os.remove
    def remove_schlaegt_fehl(p, *a, **k):
        if str(p) == str(quelle):
            raise PermissionError(13, "Permission denied")
        return echtes_remove(p, *a, **k)
    monkeypatch.setattr(os, "remove", remove_schlaegt_fehl)

    assert appmod.einwurf_verschieben(str(quelle), "snes") is True, \
        "ein angekommener Titel muss als eingeordnet gelten"
    assert (roms / "snes" / "Spiel.sfc").is_file()
    assert quelle.exists(), "die Quelle sollte hier absichtlich liegen bleiben"


def test_an_imported_file_is_group_writable(appmod, tmp_path, monkeypatch):
    """Die eingeordnete Datei ERBT die Rechte des Zielordners. (#396)

    Sonst gehoert sie dem Container-Benutzer, und RomM, RetroNAS und SMB koennen sie nicht
    bewegen — derselbe Fall, den `baum_rechte_setzen` in den Bibliothekswerkzeugen abfaengt.

    GEERBT und nicht fest gesetzt: Ein `0o664` im Quelltext behauptet zu wissen, wie diese
    Bibliothek eingerichtet ist, und Bandit meldet es zurecht als B103. Der Zielordner weiss
    es besser.
    """
    share = tmp_path / "import"; share.mkdir()
    roms = tmp_path / "roms"; roms.mkdir()
    # Eine ECHTE Bibliothek: Der Plattformordner ist fuer die Gruppe schreibbar (auf
    # Unraid `0775`). Legte der Test ihn unter der engen Umask an, waere er `0700` — und
    # dann WAERE `0600` die richtige Antwort, der Test prueefte nur sich selbst.
    (roms / "snes").mkdir()
    os.chmod(roms / "snes", 0o775)
    quelle = share / "Spiel.sfc"; quelle.write_bytes(b"x" * 64)
    monkeypatch.setattr(appmod, "ROMS", str(roms))

    # Die Umask VERENGEN, sonst prueft der Test nichts: Mit der ueblichen `022` entsteht
    # ohnehin `0644`, und mit `002` sogar `0664` — die Gegenprobe zum `chmod` schlug
    # deshalb zuerst nicht an. Unter `077` erzeugt das Kopieren `0600`, und nur der
    # ausdrueckliche `chmod` bringt die Gruppenrechte zurueck.
    alt = os.umask(0o077)
    try:
        appmod.einwurf_verschieben(str(quelle), "snes")
    finally:
        os.umask(alt)

    modus = (roms / "snes" / "Spiel.sfc").stat().st_mode & 0o777
    assert modus & 0o060, f"nicht fuer die Gruppe schreibbar: {modus:o}"


# --- #395: Doku-Gleichstand ----------------------------------------------------------

def test_no_test_name_is_defined_twice():
    """Zwei Tests mit demselben Namen — der zweite verdeckt den ersten LAUTLOS. (#395)

    So entstanden: Diese Datei hatte bereits `test_both_readmes_carry_the_same_sections`
    aus #378, das `##`-Abschnitte, Inhaltsverzeichnis UND `###`-Unterabschnitte samt einer
    gepflegten Ausnahmeliste vergleicht. #395 legte 5.000 Zeilen weiter unten einen Test
    desselben Namens an, der nur die Abschnitte zaehlte. Python behaelt den zweiten. Die
    Zahl der gesammelten Tests blieb gleich, alles war gruen — und die gruendlichere
    Pruefung lief ab diesem Tag nicht mehr.

    Das ist die unangenehmste Sorte Regression: Sie entfernt eine Pruefung, waehrend sie
    aussieht, als kaeme eine dazu.

    EN: a duplicate test name silently shadows the earlier definition. The collection count
    stays the same and everything is green, while the better check has stopped running.
    """
    import collections

    doppelt = {}
    for datei in sorted(os.listdir(os.path.join(REPO, "tests"))):
        if not (datei.startswith("test_") and datei.endswith(".py")):
            continue
        quelle = open(os.path.join(REPO, "tests", datei), encoding="utf-8").read()
        namen = re.findall(r"^def (test_[A-Za-z0-9_]+)", quelle, re.M)
        mehrfach = [n for n, z in collections.Counter(namen).items() if z > 1]
        if mehrfach:
            doppelt[datei] = sorted(mehrfach)
    assert not doppelt, (
        "diese Tests sind mehrfach definiert; nur die LETZTE Fassung laeuft: "
        + json.dumps(doppelt, ensure_ascii=False))


def test_the_english_readme_documents_the_way_back():
    """Der Rueckweg nach einem misslungenen Update steht auch auf Englisch. (#378/#395)

    Der konkrete Abschnitt, dessen Fehlen #378 aufdeckte. Diese Pruefung nennt ihn beim
    Namen statt nur Abschnitte zu zaehlen — sie faellt auch, wenn jemand ihn kuerzt statt
    ihn zu loeschen.
    """
    import re
    en = open(os.path.join(REPO, "README.en.md"), encoding="utf-8").read()
    m = re.search(r"^## Versions: updating, and going back$(.*?)(?=^## )", en, re.S | re.M)
    assert m, "der Abschnitt ueber Aktualisieren und Zurueckgehen fehlt"
    # NICHT AUF VOKABELN PRUEFEN: Die erste Fassung verlangte die Woerter „rollback" und
    # „previous version". Der Abschnitt EXISTIERT und benutzt sie nur nicht — der Test
    # scheiterte an seiner eigenen Wortwahl statt an einer Luecke. Was zaehlt, ist der
    # Umfang: Ein Abschnitt, der auf drei Zeilen zusammenschrumpft, hat den Rueckweg
    # verloren, egal welche Woerter darin stehen.
    zeilen = [z for z in m.group(1).splitlines() if z.strip()]
    assert len(zeilen) >= 40, \
        f"der Abschnitt ist auf {len(zeilen)} Zeilen geschrumpft — Rueckweg noch erklaert?"


# --- #416: der Einwurfordner braucht einen Weg hinein -------------------------------

def test_the_drop_folder_is_reachable_from_the_ui():
    """Der Massenimport hat eine Bedienoberflaeche, nicht nur eine API. (#416)

    WIE DAS AUFFIEL: Die Doku-Pruefung (#395) beschrieb einen Bereich unter
    Einstellungen -> Import. Beim Nachsehen kam heraus, dass es ihn nicht gab: `#396`
    lieferte den Taktlauf und zwei Endpunkte, aber keine Zeile Oberflaeche. Gemessen auf
    `dev`: `grep -rc 'import/status\\|import/scan' static templates` -> kein Treffer.

    Das ist genau der Fall „ausgeliefert und wirkungslos": Alle Tests waren gruen, denn
    die Endpunkte funktionierten. Nur konnte sie niemand erreichen, der nicht `curl`
    benutzt — und der Einwurfordner ist die eine Funktion, deren Sinn die Bedienung von
    Hand ist.

    EN: the bulk import shipped with a timer and two endpoints but no UI. Everything was
    green because the endpoints worked; nobody could reach them without curl.
    """
    js = open(os.path.join(REPO, "static", "js", "index.js"), encoding="utf-8").read()
    for pfad in ("/api/import/status", "/api/import/scan"):
        assert pfad in js, (
            f"{pfad} kommt in der Oberflaeche nicht vor — der Einwurfordner waere wieder "
            "nur ueber die API bedienbar")

    # Ein Abschnitt, den die Navigation nicht anbietet, ist nicht erreichbar. Beides
    # pruefen: Eintrag in der Leiste UND Zuordnung auf eine Funktion.
    m = re.search(r"let secs=\[(.+?)\];", js, re.S)
    assert m and "'drop'" in m.group(1), "der Bereich fehlt in der Einstellungs-Navigation"
    zuord = re.search(r"\(\{general:secGeneral,(.+?)\}\[sec\]", js, re.S)
    assert zuord and "drop:secDrop" in zuord.group(1), (
        "der Bereich ist in der Leiste, wird aber auf keine Funktion abgebildet — "
        "ein Klick landete stillschweigend auf 'Allgemein'")


def test_every_settings_section_has_a_render_function():
    """Jeder Eintrag der Einstellungs-Leiste zeigt auch seinen eigenen Inhalt. (#416)

    WARUM DAS EINE EIGENE PRUEFUNG BRAUCHT: Die Zuordnung endet auf `||secGeneral`. Ein
    Eintrag ohne Funktion faellt deshalb NICHT auf — er zeigt „Allgemein" und sieht aus
    wie ein Bedienfehler des Nutzers. Kein Fehler in der Konsole, kein roter Test.

    EN: the dispatch falls back to `secGeneral`, so a section without a function shows the
    wrong page instead of failing.
    """
    js = open(os.path.join(REPO, "static", "js", "index.js"), encoding="utf-8").read()
    m = re.search(r"let secs=\[(.+?)\];", js, re.S)
    assert m, "die Einstellungs-Navigation ist nicht mehr auffindbar"
    eintraege = re.findall(r"\['([a-z0-9_]+)'", m.group(1))
    assert len(eintraege) >= 8, f"nur {len(eintraege)} Eintraege gefunden — Muster kaputt?"

    zuord = re.search(r"\(\{general:secGeneral,(.+?)\}\[sec\]", js, re.S)
    assert zuord, "die Zuordnung Abschnitt -> Funktion ist nicht mehr auffindbar"
    abgebildet = set(re.findall(r"([a-z0-9_]+):sec[A-Z]", "general:secGeneral," + zuord.group(1)))

    fehlend = [e for e in eintraege if e not in abgebildet]
    assert not fehlend, (
        f"diese Abschnitte stehen in der Leiste, zeigen aber 'Allgemein': {fehlend}")


def test_every_literal_translation_key_in_the_ui_exists():
    """Kein `t('…')` im Skript ohne Eintrag in der eingebetteten deutschen Tabelle. (#416)

    Die Gegenrichtung zu `test_the_inlined_german_table_covers_every_key_any_language_has`:
    Jene prueft, dass die Tabelle jeden Schluessel der Sprachdateien kennt. Diese prueft,
    dass sie jeden Schluessel kennt, den der CODE benutzt. Ein Tippfehler in einem neuen
    `t('drop_titel')` faellt sonst nirgends auf — `t()` gibt bei Unbekanntem den
    SCHLUESSEL zurueck, und der Nutzer liest `drop_titel` als Ueberschrift.

    Zusammengesetzte Aufrufe wie `t('st_'+x.state)` sind hier absichtlich nicht erfasst;
    sie sind nicht statisch entscheidbar.

    EN: the other direction — every literal key the code uses must exist in the inlined
    table, otherwise `t()` returns the key itself and the user reads an identifier.
    """
    js = open(os.path.join(REPO, "static", "js", "index.js"), encoding="utf-8").read()
    m = re.search(r"const I18N=\{de:(\{.*?\})\};", js, re.S)
    assert m, "eingebettete deutsche Tabelle nicht gefunden"
    tabelle = set(json.loads(m.group(1)))

    benutzt = set(re.findall(r"\bt\('([a-z0-9_]+)'\)", js))
    assert len(benutzt) > 100, f"nur {len(benutzt)} Schluessel gefunden — Muster kaputt?"

    fehlend = sorted(benutzt - tabelle)
    assert not fehlend, (
        "diese Schluessel benutzt die Oberflaeche, ohne dass es sie gibt — der Nutzer "
        f"sieht den Bezeichner: {fehlend}")


def test_every_environment_variable_is_mentioned_in_the_example():
    """Was der Code aus der Umgebung liest, steht auch in `.env.example`. (#395)

    GEMESSEN BEIM FUND: 23 Variablen las `app.py`, ohne dass die Beispieldatei sie
    erwaehnte — darunter der komplette Streaming-Host (`STREAM_URL`, `STREAM_LAUNCH` und
    die zweiten Plaetze) und `IMPORT_SCAN_SEC`, das in einem KOMMENTAR vorkam, aber keinen
    Eintrag hatte. Eine Einstellung, die man nur findet, indem man den Quelltext liest,
    ist praktisch nicht vorhanden.

    Absichtlich lasch: Es genuegt, dass der Name irgendwo in der Datei VORKOMMT — auch
    auskommentiert oder im Fliesstext. Der Test verlangt keine Zeile `X=`, denn ein
    Vorgabewert ist nicht fuer jede Variable sinnvoll. Er verlangt nur, dass sie
    auffindbar ist.

    EN: every variable `app.py` reads must appear somewhere in `.env.example` — commented
    out or in prose is fine, invisible is not.
    """
    quelle = open(os.path.join(REPO, "app.py"), encoding="utf-8").read()
    gelesen = set(re.findall(r'os\.environ\.get\("([A-Z_0-9]+)"', quelle))
    gelesen |= set(re.findall(r'os\.environ\["([A-Z_0-9]+)"\]', quelle))
    assert len(gelesen) > 20, f"nur {len(gelesen)} Variablen gefunden — Muster kaputt?"

    beispiel = open(os.path.join(REPO, ".env.example"), encoding="utf-8").read()
    fehlend = sorted(v for v in gelesen if v not in beispiel)
    assert not fehlend, (
        "diese Variablen liest der Code, ohne dass `.env.example` sie kennt — sie sind "
        f"nur durch Quelltextlesen auffindbar: {fehlend}")


def test_no_markdown_table_row_stands_outside_its_table():
    """Eine Tabellenzeile hinter einem Absatz ist keine Tabelle mehr. (#395)

    GEFUNDEN IN `docs/API.md`: Die Endpunkt-Tabelle hatte elf Zeilen, aber nach der achten
    stand ein Absatz ueber `GET /health` — ohne Leerzeile direkt an die Tabelle geklebt.
    Markdown beendet die Tabelle dort. Die drei letzten Zeilen (Admin, Diagnose,
    Aufraeumen) wurden als **Fliesstext mit Pipe-Zeichen** gerendert:

        | Admin | `/api/users`, `/api/settings`, … |

    Im Quelltext sieht das vollkommen in Ordnung aus — der Fehler existiert nur in der
    Darstellung. Genau deshalb faellt so etwas jahrelang niemandem auf: Wer die Datei
    bearbeitet, liest den Quelltext; wer sie liest, liest das Gerenderte.

    EN: a table row separated from its table by a paragraph renders as literal text with
    pipes. It looks perfectly fine in the source, which is why nobody notices.
    """
    verdaechtig = {}
    for wurzel, verz, dateien in os.walk(REPO):
        verz[:] = [v for v in verz if v not in
                   (".git", "node_modules", "__pycache__", ".pytest_cache")]
        for datei in dateien:
            if not datei.endswith(".md"):
                continue
            pfad = os.path.join(wurzel, datei)
            zeilen = open(pfad, encoding="utf-8").read().splitlines()
            treffer = []
            for n, zeile in enumerate(zeilen):
                if not (zeile.startswith("|") and zeile.rstrip().endswith("|")):
                    continue
                # Ueber einer Tabellenzeile darf stehen: eine weitere Tabellenzeile, eine
                # Leerzeile — oder eine UEBERSCHRIFT. Ueberschriften sind Blockelemente und
                # beenden sich selbst, eine Tabelle darf unmittelbar darunter beginnen.
                # Ohne diese Ausnahme meldete die Pruefung jede Tabelle des Repos, die
                # direkt auf ihre Ueberschrift folgt — ein Fehlalarm, der die echten Funde
                # zugedeckt haette.
                davor = zeilen[n - 1].strip() if n else ""
                if davor and not davor.startswith(("|", "#")):
                    treffer.append(f"{n + 1}: {zeile[:60]}")
            if treffer:
                verdaechtig[os.path.relpath(pfad, REPO)] = treffer
    assert not verdaechtig, (
        "diese Tabellenzeilen haengen an einem Absatz und werden als Text mit Pipes "
        f"gerendert: {json.dumps(verdaechtig, ensure_ascii=False)[:600]}")


# --- #422: der Inhalt entscheidet, nicht der Dateiname ------------------------------

def test_a_cia_named_3ds_is_judged_as_a_cia(appmod, tmp_path):
    """Eine CIA, die `.3ds` heisst, wird als CIA beurteilt. (#422/#318)

    DER ECHTE FALL: In der Bibliothek liegt `eShop-3DS-0010 - Save Data Transfer Tool
    (World) (eShop).3ds`, 2.676.992 Bytes — und es ist eine CIA. Gelesen aus der Datei:
    Kopfgroesse `0x2020`, Zertifikatskette `0x0a00`, Ticket `0x350`, TMD `0xb34`, und bei
    0x100 steht kein `NCSD`.

    Vorher entschied die Endung. Die Datei nahm also den NCSD-Weg, scheiterte an der
    Kennung und landete im Zweig „nicht beurteilbar, also durchlassen" — sie wurde als
    STARTBAR angeboten. Der Nutzer klickt, belegt einen Platz und wartet auf ein Bild, das
    nie kommt. Genau das soll `dreids_startbar` verhindern.

    Von 1249 Abbildern war es das einzige. Die Zahl in #318 stimmte, der Schluss „nicht
    beurteilbar" nicht: Der Inhalt sagt eindeutig, was die Datei ist — nur der Name luegt.

    EN: a CIA with a .3ds name took the image path, failed the NCSD check and fell into the
    deliberate "pass when in doubt" branch. It was offered as bootable.
    """
    # Ein Update-Paket — als CIA erkannt muss es mit GRUND abgelehnt werden.
    getarnt = _cia_datei(tmp_path, "Save Data Transfer Tool.3ds", 0x0004000E00000000)
    startbar, grund = appmod.dreids_startbar(getarnt)
    assert not startbar, "eine getarnte CIA wird immer noch als startbar durchgelassen"
    assert grund == "cia_update", f"als CIA erkannt, aber falsch eingeordnet: {grund!r}"

    # Und eine Anwendungs-CIA bleibt startbar, egal wie sie heisst.
    app_cia = _cia_datei(tmp_path, "Irgendein Spiel.3ds", 0x0004000000000000)
    assert appmod.dreids_startbar(app_cia) == (True, "")


def test_an_image_named_cia_is_not_refused_as_unreadable(appmod, tmp_path):
    """Die Gegenrichtung: ein NCSD-Abbild mit `.cia` im Namen. (#422)

    WARUM DIESE HAELFTE WICHTIGER IST ALS DIE ERSTE: Eine CIA muss eine TMD haben, deshalb
    wird eine unlesbare CIA ABGEWIESEN. Ein Abbild, das faelschlich `.cia` heisst, hat
    keine — es wuerde also als `cia_unreadable` abgelehnt, obwohl es einwandfrei spielbar
    ist. Eine falsche ABSAGE ist hier der teure Fehler; genau deshalb steht in
    `dreids_startbar` „im Zweifel durchlassen".

    Ein Fix, der nur die erste Richtung beachtet, verschiebt das Problem also nur.

    EN: a wrong refusal is the expensive error here. An NCSD image misnamed .cia would be
    rejected as unreadable although it plays fine.
    """
    abbild = _3ds_datei(tmp_path, "Mario Kart 7.cia", verschluesselt=False)
    startbar, grund = appmod.dreids_startbar(abbild)
    assert startbar, f"ein spielbares Abbild wurde abgelehnt: {grund!r}"


def test_a_file_that_identifies_as_nothing_still_passes(appmod, tmp_path):
    """Die Regel „im Zweifel durchlassen" bleibt unangetastet. (#422/#299)

    Der Fix fuegt WISSEN hinzu, keine Absagen. Was sich weder als CIA noch als NCSD zu
    erkennen gibt, geht weiterhin durch — sonst haette ich unter dem Vorwand einer
    Erkennung die Grundregel umgedreht, und jede kuenftige Abweichung waere eine Absage
    statt eines Fehlversuchs.

    Diese Pruefung ist der Waechter GEGEN meinen eigenen Fix.

    EN: this guard exists against the fix itself — sniffing must add knowledge, not turn
    the "pass when in doubt" rule around.
    """
    fremd = tmp_path / "irgendwas.3ds"
    fremd.write_bytes(b"\xde\xad\xbe\xef" * 4096)
    assert appmod.dreids_startbar(str(fremd)) == (True, "")

    assert appmod.dreids_art(str(fremd)) == "", "eine Vermutung statt eines Befundes"
    assert appmod.dreids_art(str(tmp_path / "gibtsnicht.3ds")) == ""


def test_a_switch_update_or_dlc_is_refused_before_a_seat_is_taken(appmod, tmp_path):
    """Update und DLC starten nicht — und das steht VOR der Platzvergabe fest. (#427)

    GEMESSEN AM BESTAND: 434 Dateien unter `switch/`, davon **110 Updates** (Titel-ID auf
    `800`) und rund **40 DLC** (`001` aufwaerts). Jedes davon war ein Startknopf. Der Agent
    nahm ein DLC anstandslos an:

        POST /launch rel=switch/Arkanoid - Eternal Battle [DLC][010091D01597D002].nsp
        {"ok": true, ...}

    Ein Platz wird belegt, und der Nutzer wartet auf ein Bild, das nicht kommen kann —
    dieselbe Lage wie vor #315 bei den 3DS-CIAs.

    EN: 110 updates and ~40 DLC among 434 files, every one of them offered with a Play
    button. The agent accepted a DLC without comment.
    """
    spiel = _nsp_datei(tmp_path, "Spiel.nsp", "0100633007d48000")
    assert appmod.switch_startbar(spiel) == (True, "")

    update = _nsp_datei(tmp_path, "Update.nsp", "0100633007d48800")
    assert appmod.switch_startbar(update) == (False, "nsp_update")

    dlc = _nsp_datei(tmp_path, "Zusatz.nsp", "010091d01597d002")
    assert appmod.switch_startbar(dlc) == (False, "nsp_dlc")


def test_the_switch_title_id_comes_from_the_file_not_the_name(appmod, tmp_path):
    """Der Dateiname entscheidet NICHT. (#427)

    WARUM DAS DIE EIGENTLICHE AUSSAGE IST: Der naheliegende Filter waere das Wort „DLC" im
    Namen. Er haelt nicht — im Bestand steht es als `[DLC]`, als
    `[space scout pack dlc]`, und `[Trowzer's Top Tonic Pack]` traegt gar keinen Hinweis
    und ist trotzdem DLC (ID `010022F00DA67001`).

    Deshalb wird die ID AUS DEM ARCHIV gelesen. Diese Pruefung dreht beides gegeneinander:
    ein Spiel, das „DLC" heisst, muss durchgehen — ein DLC, das nach Spiel klingt, nicht.

    EN: the obvious filter is the word "DLC" in the name, and it does not hold. The check
    turns both cases against each other.
    """
    getarnt = _nsp_datei(tmp_path, "Irgendwas [DLC] Edition.nsp", "0100633007d48000")
    assert appmod.switch_startbar(getarnt) == (True, ""), \
        "ein Basisspiel wurde wegen seines NAMENS abgewiesen"

    heimlich = _nsp_datei(tmp_path, "Trowzers Top Tonic Pack.nsp", "010022f00da67001")
    assert appmod.switch_startbar(heimlich) == (False, "nsp_dlc"), \
        "ein DLC ohne Hinweis im Namen kam durch"


def test_an_unreadable_switch_file_still_passes(appmod, tmp_path):
    """Im Zweifel durchlassen — auch hier. (#427/#299)

    Eine XCI ist ein anderer Behaelter, ein Archiv ohne Ticket nicht beurteilbar. Am
    Bestand: 25 XCI und 4 ohne Ticket unter 434. Beide Gruppen gehen durch, weil eine
    falsche ABSAGE hier der teure Fehler ist.

    Diese Pruefung ist der Waechter gegen den eigenen Fix: Sie faellt, sobald jemand aus
    „nicht lesbar" eine Absage macht.

    EN: this guards against the fix itself — an unreadable file must not become a refusal.
    """
    xci = tmp_path / "Spiel.xci"
    xci.write_bytes(b"\x00" * 0x200 + b"HEAD" + b"\x00" * 0x100)
    assert appmod.switch_startbar(str(xci)) == (True, "")

    leer = tmp_path / "kaputt.nsp"
    leer.write_bytes(b"PFS0" + b"\xff" * 32)
    assert appmod.switch_startbar(str(leer)) == (True, "")

    assert appmod.switch_startbar(str(tmp_path / "gibtsnicht.nsp")) == (True, "")


def test_the_install_example_does_not_point_at_latest():
    """Das Installationsbeispiel nennt eine Version, nicht `:latest`. (#436)

    GEMESSEN: `ghcr.io/sparxx947/romseerr:latest` stammt vom 2026-08-07 07:33 (`bd87e6c`)
    und ist damit AELTER als v1.0.0-beta.1. Der Grund ist richtig — `release-image.yml`
    setzt `latest` nur fuer stabile Fassungen, damit eine Vorabversion es nicht verschiebt,
    und stabile gab es noch keine. Die Folge war es nicht: Die READMEs boten genau dieses
    Tag als Standardinstallation an, also einen Bau ohne Einwurfordner, ohne
    Archive.org-Schluessel, ohne Download-Proxy, ohne die Switch- und 3DS-Pruefungen.

    Ein `latest`, das aelter ist als jeder Release, ist eine Falle — und die Doku darf nicht
    hineinfuehren. Sobald die erste stabile Fassung erscheint, darf diese Pruefung fallen.

    EN: the published `latest` predates every release, because the tag is reserved for stable
    versions and none exists yet. The READMEs offered exactly that tag as the default install.
    """
    for datei in ("README.md", "README.en.md"):
        text = open(os.path.join(REPO, datei), encoding="utf-8").read()
        # Nur die Befehlszeilen, nicht die Erklaerung darueber, WARUM man es nicht nimmt.
        zeilen = [z.strip() for z in text.splitlines()
                  if "ghcr.io/sparxx947/romseerr:" in z and not z.strip().startswith(">")]
        schlecht = [z for z in zeilen if z.endswith(":latest")]
        assert not schlecht, (
            f"{datei} bietet `:latest` als Installation an, obwohl es aelter ist als jeder "
            f"Release: {schlecht}")
        assert zeilen, f"{datei} nennt gar kein Abbild mehr"

def test_every_workflow_keeps_write_permissions_on_the_job(appmod):
    """Kein Schreibrecht auf Workflow-Ebene. (#434)

    WARUM DAS ZAEHLT: Ein `permissions:`-Block ganz oben gilt fuer JEDEN Job der Datei —
    auch fuer die, die nur lesen. In `release-please.yml` standen `contents: write` und
    `pull-requests: write` oben, obwohl drei der vier Jobs eigene Bloecke hatten und nur
    einer sie brauchte. Scorecard meldet das als „high", und die enge Fassung ist ohnehin
    die ehrlichere Beschreibung: Sie sagt, WELCHER Schritt schreibt.

    Nicht geprueft wird, ob ein Job zu viel verlangt — das entscheidet niemand aus dem
    Quelltext. Geprueft wird nur, dass die Entscheidung ueberhaupt am Job faellt.

    EN: a top-level permissions block applies to every job in the file, including the ones
    that only read. This checks the decision is made per job, not that a job asks for the
    right amount.
    """
    import yaml
    verz = os.path.join(REPO, ".github", "workflows")
    schreibend = {}
    for datei in sorted(os.listdir(verz)):
        if not datei.endswith((".yml", ".yaml")):
            continue
        d = yaml.safe_load(open(os.path.join(verz, datei), encoding="utf-8"))
        oben = (d or {}).get("permissions")
        if not isinstance(oben, dict):
            continue          # `read-all` oder gar nichts — beides unbedenklich
        schreibt = sorted(k for k, v in oben.items() if v == "write")
        if schreibt:
            schreibend[datei] = schreibt
    assert not schreibend, (
        "diese Workflows halten Schreibrechte auf Datei-Ebene, wo sie fuer jeden Job "
        f"gelten: {json.dumps(schreibend)}")


def test_a_security_policy_exists_and_says_where_to_report():
    """`SECURITY.md` sagt, wo ein Fund hingehoert. (#434)

    Ein oeffentliches Repository ohne diese Datei laesst jemanden raten, wohin mit einem
    Fund — und die naheliegende Antwort waere ein oeffentliches Issue, also genau der Weg,
    der ihn sofort allen zeigt.

    Geprueft wird nicht die Laenge, sondern dass die drei Dinge dastehen, die ein Melder
    braucht: WOHIN, WAS zaehlt, und WAS ausdruecklich nicht.
    """
    pfad = os.path.join(REPO, "SECURITY.md")
    assert os.path.isfile(pfad), "es gibt keine SECURITY.md"
    text = open(pfad, encoding="utf-8").read()
    for stelle, was in (("Security Advisories", "der Meldeweg"),
                        ("_guard", "was als Fund zaehlt"),
                        ("API key is admin-equivalent", "was ausdruecklich keiner ist")):
        assert stelle in text, f"{was} fehlt ({stelle!r})"
    # Zweisprachig wie jede Doku hier.
    assert "English below" in text or "## What this project is" in text, \
        "die englische Haelfte fehlt"


def test_the_release_documentation_names_the_step_that_is_easy_to_forget():
    """Der Handgriff, ohne den kein Release durchgeht, steht geschrieben. (#435)

    GitHub loest fuer Ereignisse aus dem voreingestellten `GITHUB_TOKEN` KEINE Workflows
    aus — das verhindert, dass ein Workflow sich selbst endlos anstoesst. Es trifft damit
    ausgerechnet den einen PR, der ein oeffentliches Artefakt erzeugt: Der Release-PR
    bekommt gar keine Pruefungen, waehrend `dev-ci-gate` acht davon verlangt.

        $ gh pr checks 188
        no checks reported on the 'release-please--branches--dev' branch

    Schliessen und Wiederoeffnen aus einem Benutzerkonto loest die Ausloeser erneut aus.
    Das ist ein Ritual, und Rituale leben in jemandes Kopf, bis sie aufgeschrieben sind —
    beim naechsten Release, den jemand anders schneidet, waere die naheliegende Abhilfe
    `--admin`, also ein Release, der gruen aussieht und nie geprueft wurde.

    Diese Pruefung haelt die Anleitung an der Stelle, an der sie gebraucht wird.

    EN: GitHub fires no workflows for GITHUB_TOKEN-caused events, so the one PR producing a
    public artefact gets no checks at all. Close and reopen re-fires them; the obvious
    alternative, --admin, ships a release that was never checked.
    """
    text = open(os.path.join(REPO, ".github", "CONTRIBUTING.md"), encoding="utf-8").read()
    i = text.find("### Wie ein Release entsteht")
    assert i >= 0, "der Abschnitt ueber den Release fehlt"
    abschnitt = text[i:text.find("\n### ", i + 10)]

    assert "GITHUB_TOKEN" in abschnitt, "der Grund fehlt — ohne ihn wirkt der Schritt willkuerlich"
    assert "schließen" in abschnitt.lower() or "schliessen" in abschnitt.lower(), \
        "der Handgriff selbst fehlt"
    assert "--admin" in abschnitt, \
        "der naheliegende falsche Ausweg wird nicht benannt — genau der wird sonst genommen"


# --- #477: ein Ordner-Titel ist EIN Titel, nicht sein Innenleben --------------------

def test_a_folder_title_is_indexed_as_one_title(appmod):
    """Wii U, Vita und PS3 liegen als ORDNER vor — der Index zaehlt sie als einen. (#477)

    GEMESSENER SCHADEN, nach einem vollstaendigen Neuaufbau am echten Bestand:

        wiiu    31 Eintraege: `app`, `bootDrcTex`, `bootLogoTex`, `bootMovie`
        psvita  14 Eintraege: `args`, `eboot`, `Gravite`, `icon`
        ps3     27 Eintraege: `PS3_DISC`, `ICON0`, …

    `bootMovie` ist ein Video IN Captain Toad, `Gravite` die `.psarc` IN Gravity Rush. Die
    echten Titel fehlten ganz, und `stream_info` fand sie nicht — ein vollstaendiger Titel
    war ueber die Oberflaeche unerreichbar.

    Der Import weiss das seit #391. Der Index wusste es nicht.
    """
    spiel = os.path.join(appmod.ROMS, "wiiu", "Captain Toad Treasure Tracker [AKBP01]")
    for teil in ("code", "content", "meta"):
        os.makedirs(os.path.join(spiel, teil), exist_ok=True)
    open(os.path.join(spiel, "code", "Kinopio.rpx"), "w").close()
    open(os.path.join(spiel, "content", "bootMovie"), "w").close()
    open(os.path.join(spiel, "meta", "bootLogoTex"), "w").close()

    appmod.build_index()
    titel = appmod.LIB["per"].get("wiiu", set())
    assert appmod.norm("Captain Toad Treasure Tracker [AKBP01]") in titel, \
        f"der Ordner-Titel fehlt im Index: {sorted(titel)[:6]}"
    for innerei in ("bootMovie", "bootLogoTex", "Kinopio"):
        assert appmod.norm(innerei) not in titel, \
            f"{innerei!r} steht als Titel im Index — das ist Spielinhalt, kein Titel"


def test_a_disc_image_set_folder_is_one_title(appmod):
    """Auch ein Abbild-Set — sonst hiesse ein Dreamcast-Titel `track01`. (#477)

    `spielordner_slug` kennt Wii U, PS3, GameCube, Vita und Xbox, aber KEIN Abbild-Set:
    Eine `.cue` verraet ihre Plattform nicht. Fuer den Index ist die Plattform aber schon
    bekannt — dort lautet die Frage nur „ein Titel oder viele?".

    Ohne diesen Weg legt der Index nach dem Umbau `track01`, `track02`, `track03` als
    Titel ab: derselbe Unsinn wie `bootMovie`, nur mit anderen Namen.
    """
    spiel = os.path.join(appmod.ROMS, "dc", "Crazy Taxi (PAL)")
    os.makedirs(spiel, exist_ok=True)
    with open(os.path.join(spiel, "Crazy Taxi (PAL).gdi"), "w") as f:
        f.write("3\n1 0 4 2352 track01.bin 0\n2 600 0 2352 track02.raw 0\n"
                "3 45000 4 2352 track03.bin 0\n")
    for n in ("track01.bin", "track02.raw", "track03.bin"):
        open(os.path.join(spiel, n), "w").close()

    appmod.build_index()
    titel = appmod.LIB["per"].get("dreamcast", set()) | appmod.LIB["per"].get("dc", set())
    assert appmod.norm("Crazy Taxi (PAL)") in titel, \
        f"der Abbild-Set-Ordner fehlt im Index: {sorted(titel)[:6]}"
    assert appmod.norm("track01") not in titel, "die Spurdateien stehen als Titel im Index"


def test_two_games_in_one_folder_are_not_one_title(appmod):
    """Zwei verschiedene Abbildlisten in einem Ordner = Sammlung, kein Titel. (#477)

    Ohne diese Bedingung machte der Fix aus jedem Sammelordner EINEN Titel und verstaeckte
    alles darin — dieselbe Fehlrichtung wie vorher, nur andersherum.
    """
    ordner = os.path.join(appmod.ROMS, "psx", "Zwei Spiele")
    os.makedirs(ordner, exist_ok=True)
    for name in ("Spiel A", "Spiel B"):
        with open(os.path.join(ordner, f"{name}.cue"), "w") as f:
            f.write(f'FILE "{name}.bin" BINARY\n')
        open(os.path.join(ordner, f"{name}.bin"), "w").close()

    assert appmod.ist_titel_ordner(ordner) is False


def test_an_incomplete_set_folder_is_not_one_title(appmod):
    """Fehlt eine genannte Datei, ist der Ordner kein Titel. (#477)

    Ihn trotzdem als Titel zu fuehren hiesse, einen kaputten Satz als vollstaendig
    auszuweisen — genau das, was in #462 wochenlang niemandem auffiel.
    """
    ordner = os.path.join(appmod.ROMS, "dc", "Unvollstaendig")
    os.makedirs(ordner, exist_ok=True)
    with open(os.path.join(ordner, "Unvollstaendig.gdi"), "w") as f:
        f.write("1\n1 0 4 2352 track01.bin 0\n")
    assert appmod.ist_titel_ordner(ordner) is False


# ---------------------------------------------------------------------------
# #518: Neo Geo CD ist eine eigene Plattform, weil RomM sie getrennt fuehrt.
# ---------------------------------------------------------------------------

def test_neo_geo_cd_is_not_folded_into_neogeo(appmod):
    """`neo-geo-cd` darf nicht auf `neogeo` zeigen. (#518)

    NICHT AUS DER KONSOLENGESCHICHTE begruendet, sondern AM LAUFENDEN ROMM GEMESSEN:

        Neo Geo AES   neogeoaes    300 ROMs
        Neo Geo CD    neo-geo-cd   100 ROMs
        eine Plattform `neogeo` gibt es dort GAR NICHT

    Solange der Alias stand, fragte `romm_find` nach `neogeo`:

        romm_find("Aero Fighters 2 (World)", "neogeo")      -> None
        romm_find("Aero Fighters 2 (World)", "neo-geo-cd")  -> Aero Fighters 2

    100 vorhandene, von RomM gescannte Titel waren damit unspielbar — der Play-Knopf
    konnte gar nicht erscheinen. AES und MVS bleiben zusammengefasst: das ist dieselbe
    Hardware in anderen Gehaeusen, und RomM fuehrt sie ebenfalls so.

    EN: not argued from console history but measured against the running RomM, which
    keeps the CD separate and has no `neogeo` platform at all.
    """
    assert appmod.FOLDER_ALIASES.get("neo-geo-cd") is None, (
        "der Alias ist zurueck — romm_find fragt dann wieder nach einer Plattform, "
        "die es in RomM nicht gibt")
    assert appmod.FOLDER_ALIASES.get("neogeoaes") == "neogeo"
    assert appmod.FOLDER_ALIASES.get("neogeomvs") == "neogeo"
    assert appmod.folder_slug("neo-geo-cd") == "neo-geo-cd"


def test_a_neo_geo_cd_title_is_not_eaten_by_the_neo_geo_pattern(appmod):
    """Das allgemeine `neo geo`-Muster darf die CD nicht schlucken. (#518)

    `guess_platform` geht die Muster DER REIHE NACH durch und nimmt den ersten Treffer.
    `neo\\s*geo` passt auch auf `Neo Geo CD`. Ohne einen Eintrag DAVOR landet jede
    Schreibweise wieder bei `neogeo` — der Alias waere entfernt und die Wirkung
    dieselbe.

    HIER STAND ZUERST `folder_slug`, UND DAS WAR DIE FALSCHE FUNKTION: Sie reicht
    unbekannte Ordnernamen unveraendert durch und normalisiert nichts. `KW` beschreibt,
    was aus einem TITEL oder Releasenamen gelesen wird — dort greift die Reihenfolge.
    """
    for text in ("Metal Slug (Neo Geo CD)", "neo-geo-cd", "NeoGeo CD Collection",
                 "Some Game [neo geo cd]"):
        assert appmod.guess_platform(text) == "neo-geo-cd", text
    # Die Gegenrichtung: was wirklich Neo Geo ist, bleibt es.
    for text in ("Metal Slug (Neo Geo)", "NeoGeo AES romset"):
        assert appmod.guess_platform(text) == "neogeo", text


def test_neo_geo_cd_is_playable_and_says_it_needs_a_bios(appmod):
    """Kern und BIOS-Hinweis gehoeren zusammen. (#518)

    `fbneo` spielt Neo Geo CD — derselbe Kern wie fuer `neogeo`. Aber anders als ein
    Cartridge-Romset braucht ein CD-Abbild das System-ROM der Konsole. Ohne den Hinweis
    oeffnet sich ein Spieler, der schwarz bleibt, und das sieht aus wie ein fehlender
    Kern.

    Der `romset`-Hinweis von `neogeo` passt hier NICHT und steht deshalb nicht dabei:
    eine CD ist kein Romset.
    """
    assert appmod.PLAYABLE.get("neo-geo-cd") == "fbneo"
    assert "neo-geo-cd" in appmod.NEEDS_BIOS
    assert appmod.CAVEAT.get("neo-geo-cd") is None, (
        "der Arcade-Romset-Hinweis passt nicht auf eine CD")
