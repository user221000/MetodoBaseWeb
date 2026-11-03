"""Render the real billing templates without starting an app or opening a database."""
from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    destination = args.out.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(repo))
    from core.plan_catalog import get_individual_plan_catalog, get_plan_catalog
    from web.static_assets import compute_static_version

    env = Environment(loader=FileSystemLoader(repo / "web/templates"),
                      autoescape=select_autoescape(["html"]))
    env.globals.update(csrf_token=lambda request: "isolated-csrf",
                       static_version=compute_static_version(repo / "web/static"))
    for audience, template, route in [
        ("gym", "suscripciones.html", "/suscripciones"),
        ("usuario", "usuario_suscripcion.html", "/mi-suscripcion"),
    ]:
        request = SimpleNamespace(state=SimpleNamespace(csp_nonce="isolated-render"),
                                  url=SimpleNamespace(path=route))
        html = env.get_template(template).render(
            request=request, plan_catalog=get_plan_catalog("web"),
            individual_plans=get_individual_plan_catalog())
        (destination / f"{audience}.html").write_text(html, encoding="utf-8")
    print("Rendered both billing panels; no app, database, mailbox or provider.")


if __name__ == "__main__":
    main()
