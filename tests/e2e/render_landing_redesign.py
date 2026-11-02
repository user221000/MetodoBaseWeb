"""Export actual isolated public HTTP responses for the offline Chromium contract."""
import hashlib
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))

from tests.isolation import block_external_sockets, prepare_environment


def main():
    out = Path(os.environ["METODOBASE_LANDING_QA_OUTPUT"]).resolve()
    if out.drive.upper() not in {"E:", "F:"} or out.exists():
        raise RuntimeError("Use a fresh evidence directory on E/F")
    owned = prepare_environment(discard_inherited=True)
    block_external_sockets()
    from fastapi.testclient import TestClient

    from core.plan_catalog import get_individual_plan_catalog, get_plan_catalog
    from web.database.engine import get_engine
    from web.database.models import Base
    from web.main_web import create_app

    engine = get_engine()
    if engine.dialect.name != "sqlite" or not Path(engine.url.database).resolve().is_relative_to(owned):
        raise RuntimeError("Renderer requires its own SQLite")
    Base.metadata.create_all(engine)
    out.mkdir(parents=True)
    responses = {}
    with TestClient(create_app()) as client:
        for url, name in (("/", "landing.html"), ("/registro?tipo=gym", "registro.html")):
            response = client.get(url)
            if response.status_code != 200:
                raise RuntimeError("Public render did not return 200")
            (out / name).write_bytes(response.content)
            responses[name] = {"status": response.status_code, "headers": dict(response.headers)}
    engine.dispose()
    sources = ["web/templates/landing.html", "web/static/css/landing.css", "web/static/js/landing.js",
               "web/routes/pages.py", "core/plan_catalog.py", "web/templates/registro.html",
               "web/static/js/subscription-choice.js", "web/static/js/mfa-login.js", "web/static/js/api.js",
               "tests/e2e/render_landing_redesign.py", "tests/e2e/landing_redesign_ui.cjs"]
    (out / "render.json").write_text(json.dumps({
        "scope": "Real isolated Web factory GET responses, no listening server; browser serves these bytes",
        "own_database": str(owned), "external_sockets_blocked": True,
        "responses": responses,
        "catalogue": {"business": {key: plan for key, plan in get_plan_catalog("web").items() if plan["audiencia"] == "gym"},
                     "personal": get_individual_plan_catalog()},
        "sources": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Exported real landing/registration responses with CSP headers and current catalogue.")


if __name__ == "__main__":
    main()

