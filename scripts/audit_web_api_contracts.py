"""Inventory both web-serving factories with owned SQLite and providers disabled.

Run with the web Python and process TEMP/TMP/TMPDIR in E/F::

    python -B -X utf8 -m scripts.audit_web_api_contracts --output E:/.../api-audit

The dependency names are diagnostic evidence, not a proof of authorization.
No endpoint, external provider, desktop service or application lifespan is run.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def _dependencies(dependant) -> list[str]:
    found = set()
    pending = list(dependant.dependencies)
    while pending:
        item = pending.pop()
        call = item.call
        found.add(getattr(call, "__module__", "") + "." + getattr(call, "__qualname__", type(call).__name__))
        pending.extend(item.dependencies)
    return sorted(found)


def _snapshot(app, root: Path) -> tuple[dict, dict]:
    from fastapi.routing import APIRoute, iter_route_contexts

    spec = app.openapi()
    routes = []
    # FastAPI 0.146 includes routers lazily. Inspect effective contexts so paths,
    # inherited dependencies and duplicate registrations match the dispatcher.
    for route in iter_route_contexts(app.routes):
        if not isinstance(route.original_route, APIRoute):
            continue
        source = inspect.getsourcefile(route.endpoint)
        try:
            source = Path(source).resolve().relative_to(root).as_posix() if source else None
        except ValueError:
            source = None
        for method in sorted(route.methods):
            operation = spec.get("paths", {}).get(route.path, {}).get(method.lower(), {})
            routes.append({
                "method": method, "path": route.path, "in_schema": route.include_in_schema,
                "endpoint": route.endpoint.__module__ + "." + route.endpoint.__qualname__,
                "source": source, "tags": route.tags, "dependencies": _dependencies(route.dependant),
                "request_body": operation.get("requestBody"),
                "responses": operation.get("responses", {}),
                "security": operation.get("security", []),
            })
    routes.sort(key=lambda item: (item["path"], item["method"], item["endpoint"]))
    keys = Counter((item["method"], item["path"]) for item in routes)
    duplicates = [{"method": method, "path": path, "count": count}
                  for (method, path), count in sorted(keys.items()) if count > 1]
    bodyless = [{"method": item["method"], "path": item["path"], "endpoint": item["endpoint"]}
                for item in routes if item["in_schema"] and item["method"] in {"POST", "PUT", "PATCH"}
                and item["request_body"] is None]
    return {"title": app.title, "path_count": len(spec["paths"]),
            "openapi_operation_count": sum(len(v) for v in spec["paths"].values()),
            "effective_operation_count": len(routes), "duplicate_operations": duplicates,
            "mutation_operations_without_documented_body": bodyless, "routes": routes}, spec


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.drive.upper() not in {"E:", "F:"}:
        parser.error("Evidence destination must be on E: or F:")
    if destination.exists():
        parser.error("Use a fresh output directory; previous evidence is immutable")

    from tests.isolation import block_external_sockets, prepare_environment
    owned_root = prepare_environment(discard_inherited=True)
    block_external_sockets()
    print("Preparing owned SQLite schema", flush=True)
    from web.database.engine import get_engine
    from web.database.models import Base
    engine = get_engine()
    if engine.dialect.name != "sqlite":
        raise RuntimeError("Inventory requires owned synthetic SQLite")
    Base.metadata.create_all(engine)

    print("Importing web-serving factories", flush=True)
    from api.app import create_app as api_factory
    from web.main_web import create_app as web_factory
    root = Path(__file__).resolve().parents[1]
    destination.mkdir(parents=True)
    report = {"recorded_at_utc": datetime.now(UTC).isoformat(),
              "source_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "tracked_worktree_modified": bool(subprocess.check_output(
                  ["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, text=True).strip()),
              "versions": {name: importlib.metadata.version(name) for name in
                           ("fastapi", "pydantic", "sqlalchemy", "redis", "stripe", "mercadopago")},
              "owned_test_root": str(owned_root), "external_sockets_blocked": True,
              "lifespans_started": False, "factories": {}, "source_sha256": {}}
    for relative in ("api/app.py", "web/main_web.py", "scripts/audit_web_api_contracts.py"):
        report["source_sha256"][relative] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    try:
        for name, factory in (("api", api_factory), ("web", web_factory)):
            print("Inspecting " + name + " factory", flush=True)
            result, spec = _snapshot(factory(), root)
            report["factories"][name] = result
            (destination / (name + "-openapi.json")).write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
            for route in result["routes"]:
                if route["source"]:
                    report["source_sha256"][route["source"]] = hashlib.sha256((root / route["source"]).read_bytes()).hexdigest()
        api = {(r["method"], r["path"]) for r in report["factories"]["api"]["routes"]}
        web = {(r["method"], r["path"]) for r in report["factories"]["web"]["routes"]}
        report["factory_differences"] = {"api_only": sorted(api - web), "web_only": sorted(web - api)}
        (destination / "inventory.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"output": str(destination), "versions": report["versions"], "factories": {
            name: {k: value[k] for k in ("path_count", "openapi_operation_count", "effective_operation_count", "duplicate_operations")}
            for name, value in report["factories"].items()}}, ensure_ascii=False))
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
