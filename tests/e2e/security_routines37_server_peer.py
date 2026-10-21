"""New SaaS/SQLite37 native fixture; historical PG/33 fixtures stay untouched.

This file starts nothing on import. Execution requires a separately issued Root
lease. Offline --check-only validates only its argument/source shape.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVISION = "20261020_account_security"
PORT = 8812
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf8") as output:
        json.dump(value, output, indent=2)
        output.write("\n")


def require_lease(path, source, private):
    value = json.loads(path.read_bytes())
    expiry = datetime.fromisoformat(value["expires_at_UTC"])
    if expiry.tzinfo is None:
        raise ValueError("Root lease expiry must include its timezone")
    seconds = (expiry - datetime.now(UTC)).total_seconds()
    if (value["approved"] is not True or value["scope"] != "routines37-saas-sqlite-native-exclusive-v1"
            or value["source_commit"] != source or value["private_directory"] != str(private)
            or value["fixture_sha256"] != digest(Path(__file__).read_bytes())
            or value["port"] != PORT or type(value["port"]) is not int
            or expiry.tzinfo is None or not 0 < seconds <= 4 * 3600):
        raise ValueError("A fresh exact Root native-fixture lease is required")


def owned_private(path):
    path = path.absolute()
    if (path.resolve() != path or not path.is_dir() or path.is_symlink()
            or not path.name.startswith("metodobase-test-routines37-")
            or not path.is_relative_to(Path(os.environ["TEMP"]).resolve())):
        raise ValueError("Use a new explicit protected private Temp fixture root")
    if os.name == "nt":
        acl = subprocess.check_output(["icacls", str(path)])
        if b"(I)" in acl:
            raise ValueError("The launcher must disable private-directory ACL inheritance before payload")
    elif path.stat().st_mode & 0o777 != 0o700:
        raise ValueError("The private directory must be0700 before payload")
    return path


def retire(private, actor_key):
    metadata = json.loads((private / "metadata.private.json").read_bytes())
    if actor_key not in metadata["actors"]:
        raise ValueError("Only an explicitly seeded own fixture actor can be retired")
    database = Path(metadata["sqlite_database"])
    if not database.resolve().is_relative_to(private) or not database.is_file():
        raise ValueError("The retirement control cannot select another database")
    identifier = metadata["actors"][actor_key]["id"]
    with sqlite3.connect(database, timeout=5) as db:
        row = db.execute("SELECT session_version FROM usuarios WHERE id=?", (identifier,)).fetchone()
        if row is None or type(row[0]) is not int or row[0] >= 2147483647:
            raise ValueError("Own live fixture session version required")
        changed = db.execute("UPDATE usuarios SET session_version=session_version+1 WHERE id=? AND session_version=?",
                             (identifier, row[0])).rowcount
        if changed != 1:
            raise ValueError("Own fixture session changed concurrently")
    print(json.dumps({"retired_own_actor": True, "HTTP_auth_override": False, "changed_rows": 1}))


def serve(private, source):
    from tests.isolation import block_external_sockets, prepare_environment

    product = ["web", "api", "core", "config", "utils", "src", "static"]
    subprocess.run(["git", "--no-replace-objects", "diff", "--quiet", source, "--", *product], cwd=ROOT, check=True)
    for key in ("_METODOBASE_TEST_ROOT", "METODOBASE_TEST_DATABASE_URL", "METODOBASE_TEST_REDIS_URL",
                "PYTEST_XDIST_WORKER", "MFA_ENCRYPTION_KEY"):
        os.environ.pop(key, None)
    os.environ["_METODOBASE_TEST_ROOT"] = str(private)
    temporary = prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    base = "http://127.0.0.1:" + str(PORT)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", PORT))
    os.environ.update({"BASE_URL": base, "CORS_ORIGINS": base + ",http://testserver",
                       "MFA_ENCRYPTION_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode()})
    from sqlalchemy import event, inspect, text
    from sqlalchemy.orm import Session

    from tests.integration_schema_migrations import run_migration
    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import Base, UserRole, Usuario
    from web.database.schema_control import expected_head, verify_runtime_schema

    if expected_head() != REVISION or len(Base.metadata.tables) != 41:
        raise ValueError("This new fixture requires the explicit current37 schema contract")
    engine = get_engine()
    database = Path(engine.url.database).resolve()
    if engine.dialect.name != "sqlite" or not database.is_relative_to(temporary):
        raise ValueError("The fixture must own its isolated SQLite database")
    run_migration(str(engine.url), "db_bootstrap.py", "--revision", REVISION)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    engine.dispose()
    verify_runtime_schema(engine, expected_revision=REVISION)
    with engine.connect() as db:
        if (db.scalar(text("SELECT version_num FROM alembic_version")) != REVISION
                or len(inspect(db).get_table_names()) != 42
                or db.exec_driver_sql("PRAGMA foreign_key_check").all()):
            raise ValueError("The actual SQLite37 migration witness differs")
    password = "Synthetic-Routines37-" + uuid.uuid4().hex + "!"
    hashed = hash_password(password)
    actors = {}
    for key, audience, role in (("owner", "gym", UserRole.OWNER), ("personal", "usuario", UserRole.VIEWER),
                                ("viewer", "usuario", UserRole.VIEWER), ("personal_b", "usuario", UserRole.VIEWER)):
        actors[key] = {"id": str(uuid.uuid4()), "email": uuid.uuid4().hex + "@example.invalid",
                       "password": password, "audience": audience, "role": role.value}
    with Session(engine) as db:
        for key, values in actors.items():
            db.add(Usuario(id=values["id"], email=values["email"], nombre="Synthetic routine " + key,
                           password_hash=hashed, tipo="gym" if key == "owner" else "usuario",
                           role=UserRole(values["role"]),
                           team_gym_id=actors["owner"]["id"] if key == "viewer" else None))
        db.commit()
    runtime = {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for part in product
               for p in (ROOT / part).rglob("*") if p.is_file() and p.suffix in {".py", ".js", ".css", ".html", ".json"}}
    write(private / "metadata.private.json", {"origin": base, "source_commit": source,
          "sqlite_database": str(database), "actors": actors, "fixture": "new-routines37-SaaS-SQLite",
          "historical_PG_or_33_fixture_retargeted": False})
    write(private / "runtime-source.private.json", runtime)
    write(private / "startup.private.json", {"source_commit": source, "factory": "web.main_web",
          "revision": REVISION, "ORM_tables": 41, "physical_tables": 42, "dialect": "sqlite",
          "foreign_keys_clean": True, "port": PORT, "pid": os.getpid(), "runtime_files": len(runtime),
          "auth_dependency_overrides": 0, "external_providers": "off, sockets guarded", "PG_RLS_claimed": False})
    import uvicorn

    from web.main_web import create_app

    app = create_app()
    if app.dependency_overrides:
        raise ValueError("No authentication or product API dependency override is permitted")
    try:
        uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning", access_log=False)
    finally:
        engine.dispose()
        write(private / "fixture-closed.private.json", {"normal_return": True, "owned_engine_disposed": True})


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--private", type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--lease-ack", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--serve", action="store_true")
    mode.add_argument("--retire", choices=("owner", "personal", "viewer", "personal_b"))
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{40}", args.source) is None:
        raise ValueError("A complete frozen source commit is required")
    if args.check_only:
        print(json.dumps({"scope": "argument contract only; no SQL, sockets, server or Chrome", "port": PORT,
                          "revision": REVISION, "served": False}))
        return
    private = owned_private(args.private)
    require_lease(args.lease_ack, args.source, private)
    if args.retire:
        retire(private, args.retire)
    else:
        serve(private, args.source)


if __name__ == "__main__":
    main()
