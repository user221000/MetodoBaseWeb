"""Fresh-process asset URLs for both complete factories, with providers blocked."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]
REPORT_PREFIX = "STATIC_ASSET_FACTORY_REPORT="
FACTORIES = ("api.app", "web.main_web")
PAGES = ("/", "/login-gym", "/login-usuario", "/registro?tipo=gym",
         "/registro?tipo=usuario", "/configuracion", "/mi-perfil")


class Assets(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.assets = []
        self.scripts = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.scripts.append(attrs)
        url = attrs.get("src") if tag == "script" else attrs.get("href") if tag == "link" else None
        if url and url.startswith("/static/"):
            self.assets.append(url)


def _legacy_version(directory):
    """Independent copy of the pre-extraction Web cache-key algorithm."""
    digest = hashlib.md5(usedforsecurity=False)
    if directory.exists():
        for file in sorted(directory.rglob("*")):
            if file.is_file() and file.suffix in (".js", ".css"):
                digest.update(file.read_bytes())
    return digest.hexdigest()[:10]


def _probe(factory):
    # A child never reuses the controller's database, Redis, Jinja globals or
    # factory import order. All providers are disabled before any app import.
    sys.path.insert(0, str(ROOT))
    for key in ("_METODOBASE_TEST_ROOT", "METODOBASE_TEST_DATABASE_URL", "METODOBASE_TEST_REDIS_URL"):
        os.environ.pop(key, None)
    from tests.isolation import block_external_sockets, prepare_environment

    owned_root = prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    assert not any(name in sys.modules for name in FACTORIES)
    from web.database.engine import get_engine
    from web.database.models import Base

    engine = get_engine()
    assert engine.dialect.name == "sqlite"
    assert Path(engine.url.database).resolve().is_relative_to(owned_root)
    Base.metadata.create_all(engine)
    import importlib
    from fastapi.testclient import TestClient

    application = importlib.import_module(factory).create_app()
    other = next(name for name in FACTORIES if name != factory)
    assert other not in sys.modules, "Probe must not import the other factory"
    from web.routes.pages import templates

    report = {"factory": factory, "pid": os.getpid(), "other_factory_imported": False,
              "version": templates.env.globals.get("static_version"), "pages": {}, "assets": {}}
    try:
        with TestClient(application) as client:
            for path in PAGES:
                response = client.get(path)
                markup = Assets(response.text)
                report["pages"][path] = {"status": response.status_code,
                    "csp": response.headers.get("Content-Security-Policy"),
                    "cache_control": response.headers.get("Cache-Control"),
                    "assets": markup.assets, "scripts": markup.scripts}
            # Fetch exactly the URLs emitted in login, including their query.
            for url in report["pages"]["/login-gym"]["assets"]:
                if urlsplit(url).path in {"/static/js/api.js", "/static/js/mfa-login.js"}:
                    response = client.get(url)
                    report["assets"][url] = {"status": response.status_code,
                        "cache_control": response.headers.get("Cache-Control"),
                        "sha256": hashlib.sha256(response.content).hexdigest()}
            response = client.get("/api/auth/me")
            report["unauthenticated_me"] = {"status": response.status_code,
                "cache_control": response.headers.get("Cache-Control")}
    finally:
        engine.dispose()
    print(REPORT_PREFIX + json.dumps(report), flush=True)


@pytest.fixture(scope="module", params=FACTORIES)
def factory_report(request, record_testsuite_property):
    completed = subprocess.run([sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()),
                                "--probe", request.param],
                               cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True,
                               encoding="utf-8", timeout=90, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    lines = [line.removeprefix(REPORT_PREFIX) for line in completed.stdout.splitlines()
             if line.startswith(REPORT_PREFIX)]
    assert len(lines) == 1, "A completed factory report is mandatory: " + completed.stdout
    report = json.loads(lines[0])
    record_testsuite_property("static_asset_factory_" + request.param, json.dumps(report))
    return report


def test_fresh_factory_injects_exact_legacy_content_version(factory_report):
    assert factory_report["other_factory_imported"] is False
    assert factory_report["version"] == _legacy_version(ROOT / "web/static")


def test_auth_and_base_profile_assets_share_current_version(factory_report):
    expected = _legacy_version(ROOT / "web/static")
    for path, page in factory_report["pages"].items():
        assert page["status"] == 200, path
        assets = {urlsplit(url).path: parse_qs(urlsplit(url).query) for url in page["assets"]}
        assert assets, path
        stylesheets = ("/static/css/workspace.css",) if path == "/" else (
            "/static/css/design-system.css", "/static/css/workspace.css")
        for asset in stylesheets:
            assert assets[asset] == {"v": [expected]}, (path, asset)
        if path == "/":
            continue
        api_version = expected + ("-r31browser1-r27notify1-r37account1"
                                  if path in {"/configuracion", "/mi-perfil"} else "-r31browser1")
        assert assets["/static/js/api.js"] == {"v": [api_version]}, path
        if path.startswith(("/login-", "/registro")):
            assert assets["/static/js/mfa-login.js"] == {"v": [expected]}, path


def test_current_login_urls_serve_pinned_scripts_with_csp_and_private_auth(factory_report):
    nonces = set()
    for path, page in factory_report["pages"].items():
        nonce = re.search(r"'nonce-([^']+)'", page["csp"] or "")
        assert nonce, path
        nonces.add(nonce.group(1))
        assert page["scripts"] and all(script.get("nonce") == nonce.group(1)
                                       for script in page["scripts"]), path
        if path.startswith(("/login-", "/registro")):
            assert page["cache_control"] == "no-store", path
    assert len(nonces) == len(PAGES)
    assert len(factory_report["assets"]) == 2
    for url, response in factory_report["assets"].items():
        assert response["status"] == 200
        assert response["cache_control"] == "public, max-age=31536000, immutable"
        assert response["sha256"] == hashlib.sha256((ROOT / "web" / urlsplit(url).path.removeprefix("/")).read_bytes()).hexdigest()
    me = factory_report["unauthenticated_me"]
    assert me["status"] == 401
    assert "no-store" in me["cache_control"]


def test_static_cache_key_preserves_legacy_bytes_and_ignores_non_assets(tmp_path):
    from web.static_assets import compute_static_version

    assert compute_static_version(tmp_path / "missing") == _legacy_version(tmp_path / "missing")
    (tmp_path / "nested").mkdir()
    (tmp_path / "z.js").write_bytes(b"z\r\n")
    (tmp_path / "nested/a.css").write_bytes(b"a\n")
    (tmp_path / "a.js").write_bytes(b"first\n")
    (tmp_path / "ignored.JS").write_bytes(b"uppercase excluded")
    expected = _legacy_version(tmp_path)
    assert compute_static_version(tmp_path) == expected
    (tmp_path / "readme.txt").write_bytes(b"ignored")
    assert compute_static_version(tmp_path) == expected
    (tmp_path / "z.js").write_bytes(b"z\n")
    assert compute_static_version(tmp_path) != expected
    assert compute_static_version(tmp_path) == _legacy_version(tmp_path)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--probe" or sys.argv[2] not in FACTORIES:
        raise SystemExit("Expected --probe and a reviewed factory")
    _probe(sys.argv[2])
