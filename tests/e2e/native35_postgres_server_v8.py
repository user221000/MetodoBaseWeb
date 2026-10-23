"""Owned current37 fixture for independent native account/notifications/MFA tests; no provider I/O.

Uses the actual SaaS factory, password/MFA/cookie APIs and runtime engine.
The only provider seams match the historical MFA fixture: no-send mail and
a synthetic Stripe SDK portal URL, blocked by the browser before network.
"""
from pathlib import Path
import argparse
import base64
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import os
import socket
import sys
import threading
import uuid
from types import SimpleNamespace

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
REVISION = "20261020_account_security"


def module_origins():
    origins = {}
    for name, module in list(sys.modules.items()):
        if name.split(".")[0] not in {"web", "api", "core", "tests", "config", "src", "scripts"}:
            continue
        file = getattr(module, "__file__", None)
        if file:
            path = Path(file).resolve()
            if not path.is_relative_to(ROOT):
                raise RuntimeError("Fixture module escaped its frozen source root")
            origins[name] = path.relative_to(ROOT).as_posix()
    from web.database.models import Base
    assert Path(sys.modules[Base.__module__].__file__).resolve().is_relative_to(ROOT)
    return origins


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-config", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--port", type=int, choices=[8802], default=8802)
    args = parser.parse_args()
    for selected in (args.private, args.pg_config):
        assert selected.is_absolute() and selected.is_relative_to(Path("E:/MetodoBaseWorkspace")) and ".." not in selected.parts
    private = args.private.resolve()
    assert private.is_dir() and private.name == "private"
    assert private.parent.name.startswith("metodobase-account37-author-pg-")
    assert not private.is_symlink() and not (private / "startup.json").exists()
    sys.path.insert(0, str(ROOT))
    from tests.e2e.native35_guard_v8 import (
        PrivateStop,
        private_json,
        require_ack,
        stop_receipt,
    )
    from tests.e2e.native35_generation_v8 import creation_generation_guard
    require_ack(private.parent, "sql")
    preflight = private_json(private.parent / "native-preflight.json", 8 * 1024 * 1024)
    assert args.pg_config==Path(preflight["profile_path"])
    # Keep the authentic global Temp root for the immutable37 lease guard.
    for key in ("_METODOBASE_TEST_ROOT", "METODOBASE_TEST_DATABASE_URL", "METODOBASE_TEST_REDIS_URL",
                "METODOBASE_TEST_MIGRATOR_URL", "METODOBASE_TEST_POSTGRES_URL", "PYTEST_XDIST_WORKER", "MFA_ENCRYPTION_KEY"):
        os.environ.pop(key, None)
    from tests.isolation import block_external_sockets, prepare_environment, validate_postgres_test_url
    os.environ["_METODOBASE_TEST_ROOT"] = str(private / "metodobase-test-native37")
    temporary = prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    base = "http://127.0.0.1:" + str(args.port)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", args.port))
    profile = json.loads(args.pg_config.read_bytes())
    for name, alias in (("METODOBASE_TEST_MIGRATOR_URL", "migrator_url"), ("METODOBASE_TEST_POSTGRES_URL", "app_url")):
        value = profile.get(name, profile.get(alias))
        assert isinstance(value, str)
        validate_postgres_test_url(value)
        os.environ[name] = value
    os.environ.update({"ACCOUNT37_PRIVATE_LEASES": str(private.parent / "leases"),
        "BASE_URL": base, "CORS_ORIGINS": base + ",http://testserver",
        "MFA_ENCRYPTION_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode(),
        "DB_POOL_SIZE": "5", "DB_MAX_OVERFLOW": "0",
        "RESEND_API_KEY": "synthetic-native37-private-capture-no-send",
        "GOOGLE_CLIENT_ID": "synthetic-native37-sdk-boundary"})
    # Bounded fixture concurrency is not a capacity claim or a pool1 diagnosis.
    # Every engine is disposed before the owned primitive checks zero sessions.
    from sqlalchemy import inspect, text
    from sqlalchemy.orm import Session
    from tests.account_security37_owned import owned_database, process_birth
    from tests.integration_schema_migrations import run_migration
    from tests.integration_provider_subjects import application_engine
    from web.database.models import Base, Cliente, PlanGenerado, Subscription, UserRole, Usuario
    assert len(Base.metadata.tables) == 41
    origin_before = module_origins()
    (private / "module-origins-before.json").write_text(json.dumps(origin_before, indent=2), encoding="utf-8")
    runtime = None
    closed = False
    fixture_birth = process_birth()
    identity = {"pid": os.getpid(), "process_birth": fixture_birth, "generation": uuid.uuid4().hex, "source_commit": preflight["source_head"]}
    with (private / "native35-instance.private.json").open("xb") as receipt:
        receipt.write((json.dumps(identity) + "\n").encode())
    server_started = server_returned = watcher_joined = False
    stop_guard = None
    server_error_class = None
    try:
        require_ack(private.parent, "sql")
        with creation_generation_guard(private.parent), owned_database("postgresql", private / "database") as (url, admin), ExitStack() as cleanup:
            run_migration(url, "db_bootstrap.py", "--revision", REVISION)
            granted = application_engine(url, admin)
            try:
                application_url = granted.url.render_as_string(hide_password=False)
            finally:
                granted.dispose()
            os.environ["DATABASE_URL"] = application_url
            from web.database.engine import get_engine
            runtime = get_engine()
            cleanup.callback(runtime.dispose)
            assert runtime.dialect.name == "postgresql" and runtime.pool.size() == 5 and runtime.pool._max_overflow == 0
            from web.database.schema_control import expected_head, verify_runtime_schema
            from web.database.alembic.history_index_contract_v1 import expected_history_index, history_index_signature
            verify_runtime_schema(runtime)
            with runtime.connect() as connection:
                revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
                physical = len(inspect(connection).get_table_names())
                index = history_index_signature(connection)
                flags = tuple(connection.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,"
                    "pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER') "
                    "FROM pg_roles WHERE rolname=current_user")).one())
                force = connection.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace "
                    "AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))
                nonowner = connection.scalar(text("SELECT datdba<>(SELECT oid FROM pg_roles WHERE rolname=current_user) "
                    "FROM pg_database WHERE datname=current_database()"))
            assert expected_head() == revision == REVISION and physical == 42
            assert flags == (False,) * 5 and force == 32 and nonowner is True
            assert index == expected_history_index("postgresql")
            from web.auth import hash_password
            password = "Synthetic-MFA-UI-Password-2026!"
            hashed = hash_password(password)
            now = datetime.now(timezone.utc)
            with Session(admin) as db:
                for name in ("owner", "other"):
                    db.add(Usuario(id="synthetic-mfa-ui-" + name, email="mfa-ui-" + name + "@example.invalid",
                        nombre="Synthetic " + name, apellido="", password_hash=hashed, tipo="gym", role=UserRole.OWNER,
                        activo=True, session_version=0, fecha_registro=now))
                db.flush()
                db.add(Subscription(gym_id="synthetic-mfa-ui-owner", plan="clinica", status="active", provider="stripe",
                    stripe_customer_id="cus_synthetic_mfa_ui", current_period_end=now + timedelta(days=30)))
                db.commit()
            actors = {}
            with Session(admin) as db:
                for audience, role in (("gym", UserRole.OWNER), ("usuario", UserRole.VIEWER)):
                    for label in ("a", "b"):
                        identifier = str(uuid.uuid4())
                        email = "native37-" + audience + "-" + label + "-" + uuid.uuid4().hex + "@example.invalid"
                        db.add(Usuario(id=identifier, email=email, nombre="Synthetic native37 " + label,
                            apellido="", password_hash=hashed, tipo="gym" if audience == "gym" else "usuario",
                            role=role, activo=True, session_version=0, fecha_registro=now))
                        actors[audience + "_" + label] = {"id": identifier, "email": email, "audience": audience,
                            "password": password, "new_password": "Synthetic-Native37-New-Password-2026!"}
                db.commit()
            # Dedicated R22 actors: no shared/native18 credentials, grants or profile assumptions.
            onboarding_actors = {}
            with Session(admin) as db:
                for audience, role in (("gym", UserRole.OWNER), ("usuario", UserRole.VIEWER)):
                    identifier = str(uuid.uuid4())
                    email = "native37-r22-" + audience + "-" + uuid.uuid4().hex + "@example.invalid"
                    db.add(Usuario(id=identifier, email=email, nombre="Synthetic R22 preparation",
                        apellido="", password_hash=hashed, tipo=audience, role=role,
                        activo=True, session_version=0, fecha_registro=now))
                    db.flush()
                    if audience == "usuario":
                        db.add(Cliente(id_cliente=str(uuid.uuid4()), gym_id=identifier,
                            nombre="Synthetic incomplete personal profile", email=email,
                            edad=None, peso_kg=None, estatura_cm=None, objetivo=None,
                            alimentos_excluidos="[]", nutrition_restrictions_json=None))
                    onboarding_actors[audience] = {"id": identifier, "email": email,
                        "audience": audience, "password": password}
                db.commit()
            (private / "metadata.private.json").write_text(json.dumps({"origin": base, "actors": actors,
                "onboarding_actors": onboarding_actors,
                "mail_directory": str(private / "mail"), "scope": "Private fixture metadata; never issuer API or public endpoint"}, indent=2), encoding="utf-8")
            import stripe
            from web.services import email_service, stripe_service
            email_service._send = lambda *_args, **_kwargs: False
            # The only account mail transport is local capture after actual durable issue.
            # No public route exposes the proof, and no provider is contacted.
            from web.services import account_security
            mail_directory = private / "mail"
            mail_directory.mkdir(exist_ok=False)
            mail_lock = threading.Lock()
            def capture_account_mail(recipient, link):
                with mail_lock:
                    index = len(list(mail_directory.glob("packet-*.json")))
                    path = mail_directory / ("packet-" + str(index) + ".json")
                    with path.open("xb") as packet:
                        packet.write((json.dumps({"recipient": recipient, "link": link}) + "\n").encode())
                        packet.flush()
                        os.fsync(packet.fileno())
                return True  # Local transport acceptance only; no delivery claim.
            account_security._send_verification = capture_account_mail
            stripe_service._init_stripe = lambda: True
            stripe.billing_portal.Session.create = lambda **_kwargs: SimpleNamespace(url="https://billing.stripe.com/synthetic-no-provider")
            runtime_hashes = {}
            for directory in ("web", "api", "core", "config"):
                for path in (ROOT / directory).rglob("*"):
                    if path.is_file() and path.suffix in {".py", ".js", ".html", ".css", ".json"}:
                        runtime_hashes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            startup = {**identity, "fixture": "native-browser-account37-restricted-PG", "origin": base, "pid": os.getpid(),
                "process_birth": fixture_birth, "temporary_root": str(temporary), "dialect": "postgresql",
                "expected_runtime_revision": expected_head(), "actual_alembic_revision": revision,
                "metadata_table_count": len(Base.metadata.tables), "physical_table_count": physical,
                "FORCE_RLS_tables": force, "role_flags_and_owner_membership": list(flags),
                "application_role_restricted_nonowner": nonowner, "history_order_index": index,
                "runtime_raw_sha256": runtime_hashes, "fixture_pool_size": 5, "fixture_max_overflow": 0,
                "schema_preparation": "Owned UUID explicit37 migration; actual runtime get_engine/restricted role; exact physical signature/index",
                "config_classification": {"signing": "testing only", "mfa_key": "ephemeral never reported",
                    "providers": "no-send general mail; account mail private capture; synthetic Stripe/GIS SDK boundaries, no external sockets"},
                "python_packages": sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions() if d.metadata["Name"])}
            (private / "startup.json").write_text(json.dumps(startup, indent=2), encoding="utf-8")
            print(json.dumps(startup), flush=True)
            import uvicorn
            from web.main_web import create_app
            # Private shutdown observation only. No query/params/locals or forced cancellation.
            import asyncio
            import traceback
            diagnostic_directory = private / "shutdown-diagnostics"
            diagnostic_directory.mkdir(exist_ok=False)
            def await_chain(task):
                result, seen = [], set()
                current = task.get_coro()
                for _index in range(10):
                    if current is None or id(current) in seen:
                        break
                    seen.add(id(current))
                    frame = next((getattr(current, key, None) for key in ("cr_frame", "gi_frame", "ag_frame")
                                  if getattr(current, key, None) is not None), None)
                    row = {"type": type(current).__name__[:80]}
                    if frame is not None:
                        row.update(file=frame.f_code.co_filename, function=frame.f_code.co_name, line=frame.f_lineno)
                    result.append(row)
                    current = next((getattr(current, key, None) for key in ("cr_await", "gi_yieldfrom", "ag_await")
                                    if getattr(current, key, None) is not None), None)
                return result
            def shutdown_checkpoint(stage):
                tasks = []
                try:
                    current = asyncio.current_task()
                    for task in list(asyncio.all_tasks())[:80]:
                        frames = [{"file": frame.f_code.co_filename, "function": frame.f_code.co_name,
                            "line": frame.f_lineno} for frame in task.get_stack(limit=8)]
                        tasks.append({"task_identity": id(task), "current_diagnostic_task": task is current,
                            "done": task.done(), "cancelled": task.cancelled(), "frames": frames, "await_chain": await_chain(task)})
                except RuntimeError:
                    pass  # Watcher/main outside the ASGI loop still records bounded thread frames.
                threads = [{"thread_identity": identifier,
                    "frames": [{"file": item.filename, "function": item.name, "line": item.lineno}
                        for item in traceback.extract_stack(frame, limit=8)]}
                    for identifier, frame in list(sys._current_frames().items())[:80]]
                try:
                    active_server = server
                except NameError:
                    active_server = None
                server_state_counts = None
                if active_server is not None:
                    server_state_counts = {"connections": len(active_server.server_state.connections),
                        "tasks": len(active_server.server_state.tasks),
                        "listeners_serving": [listener.is_serving() for listener in getattr(active_server, "servers", [])[:4]]}
                path = diagnostic_directory / (stage + ".json")
                with path.open("xb") as receipt:
                    receipt.write((json.dumps({"stage": stage, "tasks": tasks, "threads": threads,
                        "private_frame_metadata_only": True, "no_locals_SQL_params_values": True, "server_state_counts": server_state_counts}) + "\n").encode())
            class ObservedServer(uvicorn.Server):
                async def shutdown(self, sockets=None):
                    shutdown_checkpoint("uvicorn-shutdown-enter")
                    async def observe_pending_shutdown():
                        for seconds in (1, 4, 10, 15):
                            await asyncio.sleep(seconds)
                            shutdown_checkpoint("uvicorn-shutdown-pending-" + str(seconds))
                    observation = asyncio.create_task(observe_pending_shutdown())
                    try:
                        await super().shutdown(sockets=sockets)
                        shutdown_checkpoint("uvicorn-shutdown-returned")
                    finally:
                        observation.cancel()
                        try:
                            await observation
                        except asyncio.CancelledError:
                            pass
            server = ObservedServer(uvicorn.Config(create_app(), host="127.0.0.1", port=args.port,
                log_level="warning", access_log=False))
            stop_guard = PrivateStop(private, os.getpid(), identity["generation"], identity["source_commit"], fixture_birth, lambda: (os.getpid(), process_birth()))
            watcher_done = threading.Event()
            def watch_stop():
                while not watcher_done.wait(0.1):
                    if stop_guard.inspect():
                        shutdown_checkpoint("stop-file-detected")
                        server.should_exit = True
                        return
            watcher = threading.Thread(target=watch_stop, daemon=True)
            watcher.start()
            try:
                server_started = True
                server.run()
                server_returned = True
                shutdown_checkpoint("server-run-returned")
            finally:
                shutdown_checkpoint("fixture-finalizer-enter")
                watcher_done.set()
                watcher.join(timeout=2)
                assert not watcher.is_alive()
                watcher_joined = True
                (private / "module-origins-after.json").write_text(json.dumps(module_origins(), indent=2), encoding="utf-8")
                assert runtime.pool.checkedout() == 0
                with Session(admin) as db:
                    from web.auth import verify_password
                    from web.database.models import MfaCredential
                    complete_report = private / "native37-own-output" / "report.json"
                    complete = complete_report.is_file() and json.loads(complete_report.read_bytes()).get("complete") is True
                    final = []
                    for label, values in actors.items():
                        row = db.get(Usuario, values["id"])
                        assert row.role == (UserRole.OWNER if values["audience"] == "gym" else UserRole.VIEWER)
                        assert row.team_gym_id is None and row.tipo == ("gym" if values["audience"] == "gym" else "usuario")
                        if complete:
                            assert row.session_version == (1 if label == "usuario_b" else 2)
                            assert verify_password(values["password"] if label == "usuario_b" else values["new_password"], row.password_hash)
                            assert db.get(MfaCredential, row.id).enabled_at is not None
                        final.append({"id": row.id, "session_version": row.session_version,
                            "role": row.role.value, "team_gym_id": row.team_gym_id,
                            "notification_contact_version": row.notification_contact_version,
                            "email_verified": row.email_verified_at is not None,
                            "pending_contact_hash_present": row.email_verification_hash is not None})
                    # The R22 addon opens/navigates only: it must never create a client/plan or save health fields.
                    for audience, values in onboarding_actors.items():
                        user = db.get(Usuario, values["id"])
                        assert user.role == (UserRole.OWNER if audience == "gym" else UserRole.VIEWER)
                        assert user.team_gym_id is None and user.tipo == audience and user.activo is True
                        clients = db.query(Cliente).filter(Cliente.gym_id == user.id).all()
                        assert len(clients) == (0 if audience == "gym" else 1)
                        assert db.query(PlanGenerado).filter(PlanGenerado.gym_id == user.id).count() == 0
                        for client in clients:
                            assert (client.edad, client.peso_kg, client.estatura_cm, client.objetivo) == (None,) * 4
                            assert client.alimentos_excluidos == "[]" and client.nutrition_restrictions_json is None
                    (private / "r22-seed-preservation.json").write_text(json.dumps({
                        "dedicated_actors": 2, "owner_clients": 0, "personal_profile_rows": 1,
                        "no_saved_plans_or_health_field_changes": True}), encoding="utf-8")
                    (private / "final-actors.private.json").write_text(json.dumps(final, indent=2), encoding="utf-8")
                runtime.dispose()
                runtime = None
                shutdown_checkpoint("fixture-runtime-disposed")
        closed = True
        shutdown_checkpoint("owned-context-closed")
    except BaseException as error:
        server_error_class = type(error).__name__
        raise
    finally:
        if runtime is not None:
            runtime.dispose()
        (private / "close.json").write_text(json.dumps({**identity, **stop_receipt(closed, server_started, server_returned, watcher_joined, stop_guard, server_error_class), "fixture": "native-browser-account37-restricted-PG",
            "pid": os.getpid(), "process_birth": fixture_birth, "normal_owned_context_closed": closed,
            "external_providers_used": False, "scope": "Functional fixture only; no Actions/Linux/deployment/capacity claim"}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
