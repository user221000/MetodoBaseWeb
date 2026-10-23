"""Bounded local HTTP characterization, never a production load generator.

Explicit invocation only; no latency/SLO assertion. Own migrated PostgreSQL UUID
database, real restricted-role app, real TCP HTTP, no auth/route overrides.
Provider configuration is cleared by tests.isolation before app imports.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import logging
import math
import os
from pathlib import Path
import platform
# The own EOF channel replaces process signals; no kill fallback.
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
CURRENT = ContextVar("load_observation", default=None)
COUNTS = (10, 50, 200, 500, 1000)

SCOPE = "actual37-http-seven-read-exclusive-v1"
WORKSPACE = Path("E:/MetodoBaseWorkspace")
REPOSITORY = Path("F:/MetodoBaseWeb-execution-20261018")
RUNNER = WORKSPACE / "envs/web92/Scripts/python.exe"
NAMES = ("latest-plan", "history", "export-25", "diary-30", "clients-25", "clients-100", "client-detail")
HELPERS = (
    "tests/isolation.py", "tests/account_security37_owned.py",
    "web/services/legacy_object_apply_boundary.py",
    "tests/billing13_legacy_apply37_pg_contract.py", "tests/billing13_legacy_apply37_pg_generation.py",
    "tests/ci_web37/prepare_collection.py", "tests/ci_google33/environment_photo.py",
    "tests/ci_image57/context.py", "scripts/scan_secrets.py",
    "tests/integration_schema_migrations.py", "tests/integration_provider_subjects.py",
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def validate_ack(value, contract, now=None):
    if (type(value) is not dict or set(value) != {"approved", "scope", "contract_sha256", "expires_at_UTC"}
            or value["approved"] is not True or value["scope"] != SCOPE or contract.get("schema") != SCOPE
            or type(value["contract_sha256"]) is not str or value["contract_sha256"] != digest(contract)
            or type(value["expires_at_UTC"]) is not str):
        raise ValueError("Fresh seven-read Root ACK binding differs")
    expiry = datetime.fromisoformat(value["expires_at_UTC"])
    instant = now or datetime.now(timezone.utc)
    if expiry.tzinfo is None or instant.tzinfo is None or not 0 < (expiry - instant).total_seconds() <= 8 * 3600:
        raise ValueError("Seven-read ACK is expired or exceeds eight hours")
    return value


def private_control(path):
    from web.services.legacy_object_apply_boundary import verify
    path = Path(path)
    if not path.is_absolute() or not path.is_relative_to(WORKSPACE):
        raise ValueError("Private controls must remain in E workspace")
    verify(path)
    for item in (path, *path.parents):
        value = item.lstat()
        if item.is_symlink() or getattr(value, "st_file_attributes", 0) & 0x400:
            raise ValueError("Private control alias rejected")
    raw = path.read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError("Private control exceeded its bound")
    def unique(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise ValueError("Duplicate private control field")
            result[name] = value
        return result
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique), hashlib.sha256(raw).hexdigest()


def build_contract(args):
    import re
    import tempfile
    from tests.billing13_legacy_apply37_pg_contract import validated_generation, pg_binary_directory
    from tests.ci_web37.pg_lease import profile
    if (os.name != "nt" or ROOT != REPOSITORY or Path(sys.executable).resolve() != RUNNER.resolve()
            or re.fullmatch("[0-9a-f]{40}", args.source) is None
            or type(args.requests) is not int or not 5 <= args.requests <= 200
            or type(args.seconds) is not int or not 5 <= args.seconds <= 30):
        raise ValueError("Explicit current FULL40 and E Web92 Windows runner required")
    output = Path(args.output)
    if (not output.is_absolute() or output.parent != WORKSPACE / "tmp"
            or re.fullmatch("metodobase-account37-author-pg-sevenread-[0-9a-f]{32}", output.name) is None
            or Path(tempfile.gettempdir()).resolve() != WORKSPACE / "tmp"):
        raise ValueError("Fresh dedicated E temporary UUID namespace required")
    for item in output.parents:
        if item.is_symlink() or getattr(item.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Private output ancestor alias rejected")
    _, profile_sha = private_control(args.private_env)
    config = profile(args.private_env, expected_sha256=profile_sha)
    if pg_binary_directory(config) != WORKSPACE / "tools/postgresql17/bin":
        raise ValueError("Pinned E PostgreSQL17 directory required")
    generation, generation_sha = private_control(args.generation)
    validated_generation(generation)
    photo = sources()
    if photo["HEAD"] != args.source:
        raise ValueError("Actual source HEAD differs from explicit FULL40")
    driver = Path(__file__).relative_to(ROOT).as_posix()
    pins = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (*HELPERS, driver)}
    return {"schema": SCOPE, "source_commit": args.source, "source_photo": photo,
            "driver_helper_RAW_sha256": pins, "profile_path": str(args.private_env), "profile_sha256": profile_sha,
            "generation_path": str(args.generation), "generation_sha256": generation_sha, "generation": generation,
            "server_port": 55483, "UUIDs": 1, "concurrent_UUIDs": 1, "output": str(output),
            "runner": str(RUNNER), "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
            "postgres_sha256": hashlib.sha256((pg_binary_directory(config) / "postgres.exe").read_bytes()).hexdigest(),
            "workload": {"counts": list(COUNTS), "requests": args.requests, "seconds": args.seconds,
                         "windows": [{"name": name, "concurrency": c} for c in (1, 5) for name in NAMES]},
            "closure": "owned37_planned_OID_normal_DROP_zero_sessions_fresh_absence"}


def checked_load_runtime(args):
    from tests.ci_web37.pg_lease import profile
    contract = build_contract(args)
    ack, _ = private_control(args.lease_ack)
    validate_ack(ack, contract)
    return contract, profile(args.private_env, expected_sha256=contract["profile_sha256"])


def allow_owned_drop(shutdown):
    if type(shutdown.get("server_started")) is not bool or type(shutdown.get("owned_server_stopped")) is not bool:
        raise ValueError("Explicit Boolean own-server lifecycle required")
    if shutdown["server_started"] is True and shutdown["owned_server_stopped"] is not True:
        raise RuntimeError("Own characterization server closure uncertain; UUID retained without DROP")


@contextmanager
def creation_generation_guard(args, shutdown):
    import psycopg2
    from psycopg2.extensions import cursor as Cursor
    from unittest.mock import patch
    from tests.billing13_legacy_apply37_pg_contract import check_generation
    contract, config = checked_load_runtime(args)
    connect = psycopg2.connect
    creations = 0
    class Guarded(Cursor):
        def execute(self, query, variables=None):
            nonlocal creations
            statement = query.as_string(self) if hasattr(query, "as_string") else str(query)
            if statement.lstrip().upper().startswith("CREATE DATABASE"):
                current, profile = checked_load_runtime(args)
                if current != contract or profile != config or creations != 0:
                    raise ValueError("Single UUID/source/profile/generation authority changed before CREATE")
                check_generation(contract, config, cursor=self)
                creations += 1
            if statement.lstrip().upper().startswith("DROP DATABASE"):
                allow_owned_drop(shutdown)  # Cleanup never requires an unexpired admission ACK.
            return super().execute(query, variables)
    def guarded_connect(*args, **kwargs):
        if kwargs.get("connection_factory") is not None or kwargs.get("cursor_factory") not in (None, Guarded):
            raise ValueError("A foreign cursor factory cannot bypass current characterization fences")
        kwargs["cursor_factory"] = Guarded
        return connect(*args, **kwargs)
    with patch.object(psycopg2, "connect", guarded_connect):
        yield


def current_environment_photo():
    from tests.ci_google33.environment_photo import interpreter, packages
    return {"interpreter": interpreter(), "packages": packages()}


def check_server_identity(server, identity):
    from tests.billing13_legacy_apply37_pg_contract import windows_process_identity
    if (identity is None or identity["nonce"] != server._load_nonce
            or server.pid not in (identity["pid"], identity["parent_pid"])
            or identity["argv"] != server.args[4:]):
        raise RuntimeError("Own characterization server identity differs")
    created, executable = windows_process_identity(identity["pid"])
    if created != identity["birth_filetime_100ns"] or str(executable) != identity["executable"]:
        raise RuntimeError("Own characterization server PID/birth/executable changed")


def shutdown_from_eof(stream, server):
    if stream.read(1) != b"":
        raise ValueError("Unexpected own shutdown channel bytes; no stop authorized")
    server.should_exit = True


def run_server_until_eof(application, args):
    import uvicorn
    server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", port=args.port,
                                          log_level="critical", access_log=False))
    threading.Thread(target=shutdown_from_eof, args=(sys.stdin.buffer, server), daemon=True).start()
    server.run()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def quantiles(values):
    """Nearest-rank p95, explicitly defined even for a small cohort."""
    values = sorted(values)
    if not values:
        return {"n": 0}
    return {"n": len(values), "min": values[0], "p50": values[math.ceil(.5 * len(values))-1],
            "p95": values[math.ceil(.95 * len(values))-1], "max": values[-1]}


def sources():
    from tests.ci_image57.context import git_policy
    from tests.ci_web37.prepare_collection import source_photo
    with git_policy():
        return source_photo()


def isolated_environment():
    from tests.isolation import prepare_environment, block_external_sockets
    for name in ("METODOBASE_TEST_DATABASE_URL", "METODOBASE_TEST_REDIS_URL", "PYTEST_XDIST_WORKER", "DB_POOL_SIZE", "DB_MAX_OVERFLOW"):
        os.environ.pop(name, None)
    root = prepare_environment(discard_inherited=True)
    block_external_sockets()
    return root


@contextmanager
def owned_database(args, shutdown):
    from tests.account_security37_owned import owned_database as original_owned
    from tests.billing13_legacy_apply37_pg_contract import check_generation
    contract, config = checked_load_runtime(args)
    os.environ.update(config)
    os.environ["ACCOUNT37_PRIVATE_LEASES"] = str(args.output / "leases")
    check_generation(contract, config)
    cleanup = {"owned_uuid_database_created": False, "owned_uuid_database_removed": False}
    name = None
    try:
        with creation_generation_guard(args, shutdown), original_owned("postgresql", args.output) as (url, admin):
            name = urlsplit(url).path.lstrip("/")
            cleanup["owned_uuid_database_created"] = True
            check_generation(contract, config, engine=admin)
            yield url, admin, cleanup
    finally:
        if name is not None:
            identifier = name.removeprefix("metodobase_test_account37_")
            receipt = json.loads((args.output / "leases" / ("lease-" + identifier + ".json")).read_bytes())
            cleanup["owned_uuid_database_removed"] = (receipt.get("state") == "closed_absent"
                and receipt.get("sessions_before_drop") == 0
                and receipt.get("absence_verified") == "fresh_control_connection")
            cleanup["lease"] = receipt


def seed(admin, restricted):
    """Synthetic stored data, not a generator/core/PDF benchmark or sale quota."""
    from sqlalchemy.orm import Session
    from web.auth import crear_access_token, identity_from_user, init_auth
    from web.database.models import Cliente, PlanGenerado, PersonalDiaryDay, Usuario, UserRole
    from web.services.personal_diary_service import local_today
    now = datetime.now(timezone.utc)
    plan = json.dumps({meal: {"proteinas": {"opciones": [{"alimento": "huevo", "gramos": 100,
            "equivalencia": "2 piezas", "macros": {"kcal": 140, "proteina": 12, "carbs": 1, "grasa": 10}}]},
            "vegetales": []} for meal in ("desayuno", "almuerzo", "comida", "cena")})
    with Session(admin) as db:
        for index, size in enumerate(COUNTS):
            person, gym = f"load-person-{index}", f"load-gym-{index}"
            for identity, kind, role in ((person, "usuario", UserRole.VIEWER), (gym, "gym", UserRole.OWNER)):
                db.add(Usuario(id=identity, email=identity+"@example.invalid", nombre="Synthetic",
                    password_hash="synthetic-not-a-login", tipo=kind, role=role, activo=True))
            db.flush()
            db.add(Cliente(id_cliente=f"load-self-{index}", gym_id=person, nombre="Synthetic self",
                edad=30, sexo="M", peso_kg=75, estatura_cm=175, activo=True))
            for number in range(250):
                db.add(Cliente(id_cliente=f"load-client-{index}-{number}", gym_id=gym,
                    nombre=f"Synthetic {number:04}", edad=30, sexo="M", peso_kg=75, estatura_cm=175,
                    nivel_actividad="moderada", objetivo="mantenimiento", activo=True,
                    fecha_suscripcion=(now-timedelta(days=number % 60)).replace(tzinfo=None),
                    fecha_fin_suscripcion=(now+timedelta(days=30-number % 60)).replace(tzinfo=None)))
            db.flush()
            for number in range(size):
                db.add(PlanGenerado(gym_id=person, id_cliente=f"load-self-{index}", plan_json=plan,
                    fecha_generacion=now-timedelta(days=number), tipo_plan="opciones",
                    kcal_objetivo=2000, proteina_g=120, carbs_g=250, grasa_g=60))
            for number in range(30):
                db.add(PersonalDiaryDay(user_id=person, local_date=local_today()-timedelta(days=number),
                    water_ml=1250, version=1, meals_json="{}"))
        db.commit()
    # Initialize the real signer exactly as app startup does. Merely importing
    # auth leaves its lazy SECRET_KEY empty and would create invalid seed tokens.
    os.environ["DATABASE_URL"] = restricted.url.render_as_string(hide_password=False)
    init_auth()
    tokens = {}
    with Session(restricted) as db:
        for prefix in ("load-person", "load-gym"):
            for index in range(5):
                identity = f"{prefix}-{index}"
                tokens[identity] = crear_access_token(identity_from_user(db.get(Usuario, identity), db))
    return tokens, {"personal_subjects": 5, "professional_owners": 5,
        "plans_per_personal_subject": list(COUNTS), "personal_plans": sum(COUNTS),
        "professional_clients_per_owner": 250, "professional_clients": 1250,
        "personal_profiles": 5, "diary_days_per_person": 30, "diary_days": 150,
        "plan_content_utf8_bytes": len(plan.encode()), "pdf_objects": 0,
        "data_origin": "synthetic ORM seed; no nutrition generation or historical account mutation",
        "commercial_note": "Portfolio read-size fixture; no Free entitlement or admission assertion"}


def process_snapshot(pid):
    """Windows counters for our server PID only; no third-party process reads."""
    if os.name != "nt":
        return {"available": False, "reason": "Windows counters unavailable on this platform"}
    import ctypes
    from ctypes import wintypes
    class FileTime(ctypes.Structure):
        _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]
    class Memory(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD),
            ("peak_working_set", ctypes.c_size_t), ("working_set", ctypes.c_size_t),
            ("peak_paged", ctypes.c_size_t), ("paged", ctypes.c_size_t),
            ("peak_nonpaged", ctypes.c_size_t), ("nonpaged", ctypes.c_size_t),
            ("pagefile", ctypes.c_size_t), ("peak_pagefile", ctypes.c_size_t)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(FileTime)] * 4
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Memory), wintypes.DWORD]
    handle = kernel.OpenProcess(0x1000 | 0x0010, False, pid)
    if not handle:
        return {"available": False, "reason": "Own process counters unavailable"}
    try:
        creation, exit_time, system, user = FileTime(), FileTime(), FileTime(), FileTime()
        memory = Memory()
        memory.cb = ctypes.sizeof(memory)
        if not kernel.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(system), ctypes.byref(user)) or not psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb):
            return {"available": False, "reason": "Own process counter read failed"}
        value = lambda stamp: (stamp.high << 32) | stamp.low
        return {"available": True, "cpu_seconds": (value(system)+value(user))/10_000_000,
                "rss_bytes": memory.working_set, "lifetime_peak_rss_bytes": memory.peak_working_set}
    finally:
        kernel.CloseHandle(handle)


def serve(args):
    from tests.isolation import prepare_environment, block_external_sockets, validate_postgres_test_url
    url = validate_postgres_test_url(os.environ["METODOBASE_TEST_DATABASE_URL"])
    contract, config = checked_load_runtime(args)
    from tests.billing13_legacy_apply37_pg_contract import check_generation
    parsed = urlsplit(url)
    identifier = parsed.path.removeprefix("/metodobase_test_account37_")
    if len(identifier) != 32 or any(c not in "0123456789abcdef" for c in identifier):
        raise ValueError("Exact parent-owned characterization UUID required")
    lease = json.loads((args.output / "leases" / ("lease-" + identifier + ".json")).read_bytes())
    if (lease.get("database") != parsed.path.lstrip("/") or lease.get("state") != "created"
            or parsed.port != 55483 or parsed.hostname != "127.0.0.1"
            or parsed.username != urlsplit(config["METODOBASE_TEST_POSTGRES_URL"]).username):
        raise ValueError("Server accepts only the exact created owned UUID/application role")
    check_generation(contract, config)
    os.environ["_METODOBASE_TEST_ROOT"] = str(args.output / "metodobase-test-data")
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    os.environ.update({"BASE_URL": f"http://127.0.0.1:{args.port}",
        "CORS_ORIGINS": f"http://127.0.0.1:{args.port}"})
    # No access/token/SQL logging; observer emits only bounded numeric counters.
    logging.disable(logging.CRITICAL)
    from sqlalchemy import event
    from web.database.engine import get_engine
    from web.main_web import create_app

    app = create_app()
    original_lifespan = app.router.lifespan_context
    output = Path(args.observer)
    active = {"http": 0, "pool": 0}
    active_lock = threading.Lock()
    write_lock = threading.Lock()

    def observe_sql(connection, cursor, statement, parameters, context, executemany):
        row = CURRENT.get()
        if row is not None:
            command = statement.lstrip().split(None, 1)[0].upper()
            row["sql_commands"][command] += 1
            context._load_started = time.perf_counter()

    def observe_sql_done(connection, cursor, statement, parameters, context, executemany):
        row = CURRENT.get()
        if row is not None and hasattr(context, "_load_started"):
            row["sql_ms"] += (time.perf_counter()-context._load_started)*1000

    def checked_out(dbapi, record, proxy):
        with active_lock:
            active["pool"] += 1
            peak = active["pool"]
        row = CURRENT.get()
        if row is not None:
            row["pool_checked_out_peak"] = max(peak, row["pool_checked_out_peak"])

    def checked_in(dbapi, record):
        with active_lock:
            active["pool"] -= 1

    @asynccontextmanager
    async def measured_lifespan(application):
        async with original_lifespan(application):
            engine = get_engine()
            original_get = engine.pool._do_get
            def timed_get():
                started = time.perf_counter()
                try:
                    return original_get()
                finally:
                    row = CURRENT.get()
                    if row is not None:
                        row["pool_acquire_ms"].append((time.perf_counter()-started)*1000)
            engine.pool._do_get = timed_get
            observers = [("before_cursor_execute", observe_sql), ("after_cursor_execute", observe_sql_done),
                         ("checkout", checked_out), ("checkin", checked_in)]
            for name, callback in observers:
                event.listen(engine, name, callback)
            from tests.billing13_legacy_apply37_pg_contract import windows_process_identity
            born, executable = windows_process_identity(os.getpid())
            write_json(args.ready, {"nonce": args.nonce, "pid": os.getpid(), "parent_pid": os.getppid(),
                "birth_filetime_100ns": born, "executable": str(executable), "argv": sys.argv,
                "pool_observed_QA": {"size": engine.pool.size(), "max_overflow": engine.pool._max_overflow,
                                     "timeout_seconds": engine.pool.timeout(), "workers": 1}})
            try:
                yield
            finally:
                for name, callback in observers:
                    event.remove(engine, name, callback)
                engine.pool._do_get = original_get
    app.router.lifespan_context = measured_lifespan

    class ObservedApplication:
        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                return await app(scope, receive, send)
            headers = dict(scope.get("headers", []))
            key = headers.get(b"x-load-sample", b"").decode("ascii", errors="ignore")
            if not key or len(key) > 80 or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in key):
                return await app(scope, receive, send)
            row = {"sample": key, "sql_commands": Counter(), "sql_ms": 0.0,
                "pool_acquire_ms": [], "pool_checked_out_peak": 0, "wire_body_bytes": 0}
            with active_lock:
                active["http"] += 1
                row["asgi_lifecycles_open_at_start"] = active["http"]
            token = CURRENT.set(row)
            started = time.perf_counter()
            async def observed_send(message):
                if message["type"] == "http.response.start":
                    row["status"] = message["status"]
                elif message["type"] == "http.response.body":
                    row["wire_body_bytes"] += len(message.get("body", b""))
                await send(message)
            try:
                await app(scope, receive, observed_send)
            finally:
                row["server_ms"] = (time.perf_counter()-started)*1000
                CURRENT.reset(token)
                with active_lock:
                    active["http"] -= 1
                with write_lock, output.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(row) + "\n")
    run_server_until_eof(ObservedApplication(), args)


def request_case(name, index, today):
    person = f"load-person-{index}"
    cases = {
        "latest-plan": ("/api/usuario/mi-plan", {}, person),
        "history": ("/api/usuario/historial", {}, person),
        "export-25": ("/api/usuario/privacidad/exportar", {"limit": 25}, person),
        "diary-30": ("/api/usuario/diario", {"start": (today-timedelta(days=29)).isoformat(), "end": today.isoformat()}, person),
        "clients-25": ("/api/clientes", {"limite": 25, "offset": 0}, f"load-gym-{index}"),
        "clients-100": ("/api/clientes", {"limite": 100, "offset": 100}, f"load-gym-{index}"),
        "client-detail": (f"/api/clientes/load-client-{index}-0", {}, f"load-gym-{index}"),
    }
    return cases[name]


def measure(base, name, concurrency, requests, seconds, tokens, today):
    import httpx
    started = time.perf_counter()
    # Stop admission three seconds early; each HTTP attempt has a 3s timeout.
    deadline = started + seconds - 3
    state = {"next": 0}
    lock = threading.Lock()
    rows = []
    def worker():
        local = []
        with httpx.Client(base_url=base, timeout=3, trust_env=False,
                          limits=httpx.Limits(max_connections=1, max_keepalive_connections=1)) as client:
            while time.perf_counter() < deadline:
                with lock:
                    if state["next"] >= requests:
                        break
                    number = state["next"]
                    state["next"] += 1
                index = number % 5
                path, params, identity = request_case(name, index, today)
                sample = f"{name}-c{concurrency}-{number}"
                row = {"sample": sample, "cohort": index, "history_rows_seeded": COUNTS[index]}
                tick = time.perf_counter()
                try:
                    response = client.get(path, params=params, headers={"Authorization": "Bearer "+tokens[identity],
                        "X-Load-Sample": sample, "Accept-Encoding": "identity"})
                    row.update(status=response.status_code, response_bytes=len(response.content))
                    data = response.json()
                    if name == "history":
                        row["records"] = len(data.get("planes", []))
                    elif name.startswith("clients-"):
                        row["records"] = len(data.get("clientes", []))
                        row["total"] = data.get("total")
                    elif name == "export-25":
                        row["records"] = len(data.get("plans", {}).get("records", []))
                        row["next_after"] = data.get("plans", {}).get("next_after") is not None
                    elif name == "diary-30":
                        row["records"] = len(data.get("days", []))
                    row["semantic_valid"] = validate_response(name, data, index)
                except Exception as error:
                    row["error_class"] = type(error).__name__
                    row["semantic_valid"] = False
                row["client_ms"] = (time.perf_counter()-tick)*1000
                local.append(row)
        return local
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for result in pool.map(lambda _: worker(), range(concurrency)):
            rows.extend(result)
    return {"name": name, "concurrency": concurrency, "offered_max_requests": requests,
        "admission_seconds": seconds-3, "scenario_max_seconds": seconds,
        "elapsed_seconds": time.perf_counter()-started, "samples": sorted(rows, key=lambda row: int(row["sample"].rsplit("-", 1)[1]))}


def validate_response(name, data, index):
    if name == "history":
        if type(data) is not dict or set(data) != {"planes", "next_cursor"}:
            return False
        rows = data["planes"]
        fields = {"id", "fecha", "kcal_objetivo", "proteina_g", "carbs_g", "grasa_g", "tipo_plan", "tiene_pdf"}
        if (type(rows) is not list or len(rows) != min(50, COUNTS[index])
                or any(type(row) is not dict or set(row) != fields or type(row["id"]) is not int
                       or row["tiene_pdf"] is not False for row in rows)
                or len({row["id"] for row in rows}) != len(rows)):
            return False
        return (data["next_cursor"] is None if COUNTS[index] <= 50 else
                type(data["next_cursor"]) is str and 1 <= len(data["next_cursor"]) <= 180)
    if name == "latest-plan":
        return data.get("plan_id") is not None and bool(data.get("plan"))
    if name.startswith("clients-"):
        limit = int(name.rsplit("-", 1)[1])
        return data.get("total") == 250 and len(data.get("clientes", [])) == limit
    if name == "client-detail":
        return data.get("id_cliente") == f"load-client-{index}-0"
    if name == "diary-30":
        return len(data.get("days", [])) == 30 and all(row.get("water_ml") == 1250 for row in data["days"])
    if name == "export-25":
        return (data.get("account", {}).get("id") == f"load-person-{index}"
            and data.get("scope", {}).get("personal_space") is True
            and len(data.get("profiles", {}).get("records", [])) == 1
            and len(data.get("plans", {}).get("records", [])) == min(25, COUNTS[index])
            and (data.get("plans", {}).get("next_after") is not None) == (COUNTS[index] > 25))
    return False


def summarize(scenario, observer):
    rows = scenario.pop("samples")
    for row in rows:
        if row["sample"] in observer:
            row["server"] = observer[row["sample"]]
    output = {**scenario, "completed": len(rows), "statuses": dict(Counter(str(row.get("status", "transport-error")) for row in rows)),
        "semantic_failures": sum(not row["semantic_valid"] for row in rows),
        "observer_missing": sum("server" not in row for row in rows)}
    for field in ("client_ms", "response_bytes"):
        output[field] = quantiles([row[field] for row in rows if field in row])
    for field in ("server_ms", "sql_ms", "wire_body_bytes", "pool_checked_out_peak", "asgi_lifecycles_open_at_start"):
        output[field] = quantiles([row["server"][field] for row in rows if "server" in row])
    output["sql_commands_per_request"] = {name: quantiles([row.get("server", {}).get("sql_commands", {}).get(name, 0) for row in rows])
        for name in sorted({name for row in rows for name in row.get("server", {}).get("sql_commands", {})})}
    output["pool_acquire_ms"] = quantiles([value for row in rows for value in row.get("server", {}).get("pool_acquire_ms", [])])
    output["by_cohort"] = {str(index): {"seeded_history": COUNTS[index],
        "client_ms": quantiles([row["client_ms"] for row in rows if row["cohort"] == index]),
        "response_bytes": quantiles([row["response_bytes"] for row in rows if row["cohort"] == index and "response_bytes" in row]),
        "records": sorted({row["records"] for row in rows if row["cohort"] == index and "records" in row})} for index in range(5)}
    return output, rows


def open_server_logs(output):
    from web.services.legacy_object_apply_boundary import verify
    paths = {name: Path(output) / ("server-" + name + ".private.log") for name in ("stdout", "stderr")}
    streams = {}
    try:
        for name, path in paths.items():
            streams[name] = path.open("xb")
            verify(path)  # Verify inherited User+SYSTEM2 before Popen can emit payload.
    except BaseException:
        for stream in streams.values():
            stream.close()
        raise
    return streams, {"paths": {name: str(path) for name, path in paths.items()},
                     "status": "private_empty_before_Popen", "parent_fds_closed": False,
                     "child_normal_closure_confirmed": False, "launcher_pid": None}


def close_server_logs(streams, record, shutdown):
    try:
        for stream in streams.values():
            try:
                stream.flush()
                os.fsync(stream.fileno())
            finally:
                stream.close()
    finally:
        for stream in streams.values():
            if not stream.closed:
                stream.close()
        record["parent_fds_closed"] = all(stream.closed for stream in streams.values())
    normal = shutdown["owned_server_stopped"] is True
    record["child_normal_closure_confirmed"] = normal
    if not normal:
        record["status"] = ("uncertain_child_no_log_readback" if shutdown["server_started"] is True
                            else "no_child_started_no_log_readback")
        return
    record["closed_logs"] = {}
    for name, value in record["paths"].items():
        path = Path(value)
        with path.open("rb") as reader:
            result = {"bytes": os.fstat(reader.fileno()).st_size,
                      "sha256": hashlib.file_digest(reader, "sha256").hexdigest()}
        record["closed_logs"][name] = {"path": value, **result}
    record["status"] = "normal_child_closed_parent_FDs_closed_then_full_log_readback"


def main(args):
    contract, _ = checked_load_runtime(args)
    from web.services.legacy_object_apply_boundary import create_private_directory
    create_private_directory(args.output)
    os.environ["_METODOBASE_TEST_ROOT"] = str(args.output / "metodobase-test-data")
    isolated_environment()
    from sqlalchemy import text
    from tests.integration_schema_migrations import run_migration
    from tests.integration_provider_subjects import application_engine
    from web.services.personal_diary_service import local_today
    from web.database.tenant_policy import verify_application_database_role
    before = sources()
    environment_before = current_environment_photo()
    report = {"scope": "Local Windows loopback TCP HTTP; synthetic migrated PostgreSQL; bounded closed-loop reads",
        "commit": args.source, "contract_sha256": digest(contract),
        "clock_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(), "processor": platform.processor(),
        "python": platform.python_version(), "cpu_logical": os.cpu_count(),
        "versions": {name: importlib.metadata.version(name) for name in ("fastapi", "uvicorn", "sqlalchemy", "httpx", "psycopg2-binary")},
        "bounds": {"concurrency": [1, 5], "requests_per_scenario": args.requests, "seconds_per_scenario": args.seconds},
        "pool": {"HTTP": "recorded after actual startup; QA only, no commercial capacity claim", "seed_restricted_pool": {"size": 1, "max_overflow": 0}},
        "limitations": ["No agreed SLO, pass/fail latency threshold, production extrapolation, Linux/container/Redis proof",
            "No CPU generation/PDF/PUT or durable-job queue measurement; existing stored-plan read paths only",
            "Closed-loop offered load; coordinated omission possible; no business arrival-rate model",
            "First request per route/identity excluded as warmup; OS and PostgreSQL cache not flushed",
            "SQLAlchemy event overhead included; SQL counters omit pre_ping and DB network protocol operations",
            "Pool _do_get timer includes connection creation/queue acquisition, excludes pre_ping; no worker queue timer",
            "Concurrency is client workers with at most five pending HTTP calls; ASGI lifecycles can overlap response-body completion during dependency cleanup",
            "Single shared local host/cluster; coordinated window reduces but cannot prove absence of host noise"]}
    server = None
    server_identity = None
    raw_scenarios = []
    shutdown = {"server_started": False, "owned_server_stopped": False, "stop_requested": False}
    report["server_shutdown"] = shutdown
    server_log_streams = None
    server_log_record = {"status": "not_started", "parent_fds_closed": True,
                         "child_normal_closure_confirmed": False}
    report["server_logs"] = server_log_record
    try:
        with owned_database(args, shutdown) as (url, admin, cleanup):
            report["cleanup"] = cleanup
            run_migration(url, "db_bootstrap.py", "--revision", "head")
            restricted = application_engine(url, admin)
            try:
                verify_application_database_role(restricted)
                with admin.connect() as db:
                    report["schema_revision"] = db.scalar(text("SELECT version_num FROM alembic_version"))
                    report["postgres_version"] = db.scalar(text("SHOW server_version"))
                    report["session_timezone"] = db.scalar(text("SHOW TimeZone"))
                tokens, report["seed"] = seed(admin, restricted)
                child_env = os.environ.copy()
                child_env["METODOBASE_TEST_DATABASE_URL"] = restricted.url.render_as_string(hide_password=False)
                with socket.socket() as available:
                    available.bind(("127.0.0.1", 0))
                    port = available.getsockname()[1]
                observer_file = args.output / "server-observations.jsonl"
                ready_file = args.output / "server-identity.json"
                nonce = uuid.uuid4().hex
                server_log_streams, server_log_record = open_server_logs(args.output)
                report["server_logs"] = server_log_record
                server = subprocess.Popen([sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()),
                    "--serve", "--port", str(port), "--observer", str(observer_file),
                    "--ready", str(ready_file), "--nonce", nonce, "--source", args.source,
                    "--private-env", str(args.private_env), "--generation", str(args.generation),
                    "--lease-ack", str(args.lease_ack), "--output", str(args.output),
                    "--requests", str(args.requests), "--seconds", str(args.seconds)], cwd=ROOT,
                    env=child_env, stdin=subprocess.PIPE, stdout=server_log_streams["stdout"], stderr=server_log_streams["stderr"],
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                server._load_nonce = nonce
                shutdown["server_started"] = True
                report["server_launcher"] = {"pid": server.pid, "argv": server.args, "nonce": nonce}
                server_log_record["launcher_pid"] = server.pid
                import httpx
                base = f"http://127.0.0.1:{port}"
                with httpx.Client(base_url=base, timeout=3, trust_env=False) as client:
                    ready = False
                    report["readiness"] = {"attempts": 0}
                    for _ in range(300):
                        report["readiness"]["attempts"] += 1
                        if server.poll() is not None:
                            raise RuntimeError("Own characterization server exited before readiness")
                        try:
                            response = client.get("/api/auth/me", headers={"Authorization": "Bearer "+tokens["load-person-0"]})
                            report["readiness"]["last_status"] = response.status_code
                            ready = response.status_code == 200
                        except httpx.TransportError:
                            pass
                        if ready:
                            break
                        time.sleep(.1)
                    if not ready:
                        raise RuntimeError("Own characterization server did not become ready")
                    server_identity = json.loads(ready_file.read_text(encoding="utf-8"))
                    if (server_identity["nonce"] != nonce or server.pid not in
                            (server_identity["pid"], server_identity["parent_pid"])):
                        raise RuntimeError("Own characterization child identity was not verified")
                    check_server_identity(server, server_identity)
                    report["pool"]["HTTP"] = server_identity["pool_observed_QA"]
                    report["server_identity"] = {**server_identity, "launcher_pid": server.pid,
                        "relation_verified": True, "counter_pid": server_identity["pid"]}
                    names = ("latest-plan", "history", "export-25", "diary-30", "clients-25", "clients-100", "client-detail")
                    report["warmup"] = []
                    for name in names:
                        for index in range(5):
                            path, params, identity = request_case(name, index, local_today())
                            response = client.get(path, params=params, headers={"Authorization": "Bearer "+tokens[identity], "Accept-Encoding": "identity"})
                            valid = response.status_code == 200 and validate_response(name, response.json(), index)
                            report["warmup"].append({"name": name, "cohort": index, "status": response.status_code, "semantic_valid": valid})
                            if not valid:
                                raise RuntimeError("Warmup did not satisfy real endpoint contract: "+name)
                for concurrency in (1, 5):
                    for name in names:
                        current, _ = checked_load_runtime(args)
                        if current != contract:
                            raise ValueError("Frozen characterization contract changed before a new window")
                        check_server_identity(server, server_identity)
                        process_before = process_snapshot(server_identity["pid"])
                        scenario = measure(base, name, concurrency, args.requests, args.seconds, tokens, local_today())
                        check_server_identity(server, server_identity)
                        process_after = process_snapshot(server_identity["pid"])
                        scenario["server_process_before"] = process_before
                        scenario["server_process_after"] = process_after
                        if process_before["available"] and process_after["available"]:
                            scenario["server_cpu_seconds"] = process_after["cpu_seconds"] - process_before["cpu_seconds"]
                        raw_scenarios.append(scenario)
                        print(json.dumps({"scenario": name, "concurrency": concurrency,
                            "completed": len(scenario["samples"]), "elapsed_seconds": round(scenario["elapsed_seconds"], 3)}), flush=True)
                # A client can receive the last body before ASGI finally writes
                # its observer row. Acknowledge all own rows before requesting EOF
                # the child; this control wait is outside measured scenarios.
                expected_observations = sum(len(row["samples"]) for row in raw_scenarios)
                flush_started = time.perf_counter()
                observed_count = 0
                while time.perf_counter()-flush_started < 2:
                    if observer_file.exists():
                        observed_count = observer_file.read_bytes().count(b"\n")
                    if observed_count == expected_observations:
                        break
                    time.sleep(.01)
                report["observer_flush"] = {"expected": expected_observations, "observed": observed_count,
                    "wait_seconds": time.perf_counter()-flush_started,
                    "acknowledged": observed_count == expected_observations}
                # Close only the verified own stdin; EOF requests normal shutdown.
                shutdown["stop_requested"] = True
                stop_own_server(server, server_identity)
                shutdown["owned_server_stopped"] = True
                report["owned_server_stopped"] = True
                server = None
            finally:
                if server is not None:
                    # No process signal fallback: the own pipe and nonce/birth bind this stop.
                    if shutdown["stop_requested"]:
                        raise RuntimeError("Own characterization closure uncertain; retained for manual review")
                    shutdown["stop_requested"] = True
                    stop_own_server(server, server_identity)
                    shutdown["owned_server_stopped"] = True
                    report["owned_server_stopped"] = True
                    server = None
                restricted.dispose()
                from web.database.engine import get_engine
                get_engine().dispose()
        observer = {row["sample"]: row for line in (args.output / "server-observations.jsonl").read_text(encoding="utf-8").splitlines()
                    if (row := json.loads(line))}
        summaries, samples = [], []
        for scenario in raw_scenarios:
            summary, rows = summarize(scenario, observer)
            summaries.append(summary)
            samples.extend(rows)
        report["scenarios"] = summaries
        report["outcome"] = "characterized" if ([(row["name"], row["concurrency"]) for row in summaries]
            == [(name, c) for c in (1, 5) for name in NAMES] and report["observer_flush"]["acknowledged"]
            and shutdown["owned_server_stopped"] is True) and all(row["completed"] > 0 and row["semantic_failures"] == 0 and row["observer_missing"] == 0
            and row["statuses"] == {"200": row["completed"]} and row["elapsed_seconds"] <= args.seconds for row in summaries) else "requires_review"
        write_json(args.output / "samples.json", samples)
    except Exception as error:
        report["outcome"] = "incomplete"
        report["error_class"] = type(error).__name__
        # The fixed internal error text never includes credentials or raw SQL.
        report["error_stage"] = str(error) if isinstance(error, RuntimeError) and str(error).startswith(("Own characterization", "Warmup")) else "See safe error class; private connection details omitted"
        raise
    finally:
        if server_log_streams is not None:
            close_server_logs(server_log_streams, server_log_record, shutdown)
        after = sources()
        report["source_count"] = len(before["files"])
        report["sources_stable"] = before == after
        environment_after = current_environment_photo()
        report["environment_stable"] = environment_before == environment_after
        write_json(args.output / "environment.json", {"before": environment_before, "after": environment_after,
                   "stable": report["environment_stable"]})
        write_json(args.output / "source.json", {"before": before, "after": after, "stable": before == after})
        write_json(args.output / "report.json", report)
    return 0 if report["outcome"] == "characterized" and report["sources_stable"] and report["environment_stable"] and report["cleanup"]["owned_uuid_database_removed"] else 1


def stop_own_server(server, identity):
    if identity is None:
        raise RuntimeError("Own characterization identity unconfirmed; retain process and UUID")
    check_server_identity(server, identity)
    if server.stdin is None:
        raise RuntimeError("Own characterization EOF channel absent; retain process and UUID")
    server.stdin.close()
    result = server.wait(timeout=10)
    if result != 0:
        raise RuntimeError("Own characterization normal EOF closure not confirmed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-env", type=Path)
    parser.add_argument("--source")
    parser.add_argument("--generation", type=Path)
    parser.add_argument("--lease-ack", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int)
    parser.add_argument("--observer", type=Path)
    parser.add_argument("--ready", type=Path)
    parser.add_argument("--nonce")
    arguments = parser.parse_args()
    if arguments.serve:
        serve(arguments)
    else:
        if (not arguments.private_env or not arguments.output or not arguments.source or not arguments.generation
                or not arguments.lease_ack or not 5 <= arguments.requests <= 200 or not 5 <= arguments.seconds <= 30):
            parser.error("Explicit private config/output and bounded requests5..200/seconds5..30 required")
        try:
            sys.exit(main(arguments))
        except Exception as failure:
            print(json.dumps({"outcome": "incomplete", "error_class": type(failure).__name__}), flush=True)
            sys.exit(1)
