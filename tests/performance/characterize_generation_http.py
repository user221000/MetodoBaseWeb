"""Explicit bounded generation/PDF/local-object measurement; not a production load tool.

No application import or operation occurs on import. Root must bind a final
source/workload/profile/generation and issue a new ACK before execution.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from tests.performance.generation_observer import CURRENT, CaptureRejected, Recorder, install_application_hooks, quantiles

SCOPE = "current-head-generation-pdf-local-exclusive-v1"
WORKSPACE = Path("E:/MetodoBaseWorkspace")
REPOSITORY = Path("F:/MetodoBaseWeb-execution-20261018")
RUNNER = WORKSPACE / "envs/web92/Scripts/python.exe"
HELPERS = (
    "tests/isolation.py", "tests/account_security37_owned.py", "tests/ci_web37/pg_close.py",
    "web/services/legacy_object_apply_boundary.py", "tests/billing13_legacy_apply37_pg_contract.py",
    "tests/billing13_legacy_apply37_pg_generation.py", "tests/ci_web37/prepare_collection.py",
    "tests/ci_google33/environment_photo.py", "tests/ci_image57/context.py", "scripts/scan_secrets.py",
    "tests/integration_schema_migrations.py", "tests/integration_provider_subjects.py",
    "tests/performance/generation_observer.py",
    "web/services/product_analytics_v2.py",
    "tests/ci_web39/pg_control.py",
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
    # A daemon must not retain BufferedReader's lock during failed startup.
    if os.read(stream.fileno(), 1) != b"":
        raise ValueError("Unexpected own shutdown channel bytes; no stop authorized")
    server.should_exit = True


def run_server_until_eof(application, args):
    import uvicorn
    server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", port=args.port,
                                          log_level="critical", access_log=False))
    threading.Thread(target=shutdown_from_eof, args=(sys.stdin.buffer, server), daemon=True).start()
    server.run()
    if not server.started:
        raise CaptureRejected("Own application startup did not complete")


def generation_routes(application, expected_endpoint):
    """Inspect mounted routes in dispatch order, including lazy router prefixes."""
    from fastapi.routing import _iter_routes_with_context
    from starlette.routing import Match
    routes = list(_iter_routes_with_context(application.routes))
    scope = {"type": "http", "method": "POST", "path": "/api/generar-plan", "root_path": ""}
    first = next(((route, context) for route, context in routes
                  if (context or route).matches(scope)[0] is Match.FULL), None)
    if (first is None or getattr(first[0], "endpoint", None) is not expected_endpoint
            or (first[1].path if first[1] else getattr(first[0], "path", None)) != scope["path"]):
        raise ValueError("Actual first generation adapter differs")
    selected = [(route, context.path if context else getattr(route, "path", None))
                for route, context in routes
                if (context.path if context else getattr(route, "path", None)) == "/api/generar-plan"
                and "POST" in getattr(route, "methods", set())]
    if not selected or selected[0][0].endpoint is not expected_endpoint:
        raise ValueError("Actual first generation adapter differs")
    return [{"path": path, "module": route.endpoint.__module__, "name": route.endpoint.__name__}
            for route, path in selected]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def publish_worker_identity(args):
    """Publish our native identity before contract/app/lifespan operations."""
    from web.services.legacy_object_apply_boundary import verify
    from tests.billing13_legacy_apply37_pg_contract import windows_process_identity
    if (args.output.parent != WORKSPACE / "tmp"
            or re.fullmatch("metodobase-account37-author-pg-generation-[0-9a-f]{32}", args.output.name) is None
            or args.factory not in {"web", "api"}
            or re.fullmatch("[0-9a-f]{32}", args.nonce or "") is None
            or args.ready != args.output / (args.factory + "-ready.json")):
        raise ValueError("Exact parent-owned early identity destination required")
    verify(args.output, directory=True)
    birth, executable = windows_process_identity(os.getpid())
    path = args.output / (args.factory + "-worker-identity.json")
    with path.open("x", encoding="utf8") as stream:
        verify(path)  # User+SYSTEM before this first payload.
        json.dump({"nonce": args.nonce, "pid": os.getpid(), "parent_pid": os.getppid(),
            "birth_filetime_100ns": birth, "executable": str(executable), "argv": sys.argv}, stream)
        stream.flush(); os.fsync(stream.fileno())
    path.with_suffix(".closed").touch(exist_ok=False)


def record_worker_error(args, error):
    """First failure only; full traceback stays in the private owned E output."""
    from web.services.legacy_object_apply_boundary import verify
    path = args.output / (args.factory + "-worker-error.private.json")
    if path.exists():
        return
    with path.open("x", encoding="utf8") as stream:
        verify(path)
        json.dump({"error_class": type(error).__name__, "traceback": traceback.format_exc(),
                   "application_startup_accepted": False}, stream)
        stream.flush(); os.fsync(stream.fileno())
    path.with_suffix(".closed").touch(exist_ok=False)


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
    from tests.ci_web37.pg_close import owned_database as original_owned
    from tests.billing13_legacy_apply37_pg_contract import check_generation
    from tests.ci_web39.pg_control import check_control_generation
    contract, config = checked_load_runtime(args)
    os.environ.update(config)
    os.environ["ACCOUNT37_PRIVATE_LEASES"] = str(args.output / "leases")
    check_control_generation(contract, config)
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


def stop_own_server(server, identity):
    if identity is None:
        raise RuntimeError("Own characterization identity unconfirmed; retain process and UUID")
    if server.poll() is None:
        check_server_identity(server, identity)
        if server.stdin is None:
            raise RuntimeError("Own characterization EOF channel absent; retain process and UUID")
        server.stdin.close()
    elif server.stdin is not None and not server.stdin.closed:
        server.stdin.close()
    result = server.wait(timeout=10)
    # The venv launcher may be a different PID from the actual Python worker.
    # Reopen only that early, attributed worker and check its native exit object.
    import ctypes
    from ctypes import wintypes as W
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    kernel.OpenProcess.restype = W.HANDLE
    kernel.GetProcessTimes.argtypes = [W.HANDLE] + [ctypes.POINTER(W.FILETIME)] * 4
    kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
    kernel.WaitForSingleObject.restype = W.DWORD
    kernel.CloseHandle.argtypes = [W.HANDLE]
    handle = kernel.OpenProcess(0x1000 | 0x100000, False, identity["pid"])
    if not handle:
        if ctypes.get_last_error() != 87:
            raise RuntimeError("Own worker exit object is inaccessible; retain ownership")
    else:
        try:
            stamps = [W.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *map(ctypes.byref, stamps)):
                raise RuntimeError("Own worker birth is unavailable; retain ownership")
            birth = stamps[0].dwHighDateTime << 32 | stamps[0].dwLowDateTime
            if birth == identity["birth_filetime_100ns"] and kernel.WaitForSingleObject(handle, 0) != 0:
                raise RuntimeError("Own worker is still alive after launcher exit; retain ownership")
        finally:
            kernel.CloseHandle(handle)
    return result


def workload(args):
    value, raw_sha = private_control(args.workload)
    if (type(value) is not dict or set(value) != {"schema", "cells"}
            or value["schema"] != "local-generation-characterization-cells-v1"
            or type(value["cells"]) is not list or not value["cells"]):
        raise ValueError("Explicit Root generation cells required")
    total = 0
    for row in value["cells"]:
        if (type(row) is not dict or set(row) != {"factory", "subject", "type", "excluded_food", "samples", "concurrency"}
                or row["factory"] not in {"web", "api"} or row["subject"] not in {"gym", "individual"}
                or row["type"] not in {"menu_fijo", "opciones"}
                or type(row["samples"]) is not int or row["samples"] < 1
                or type(row["concurrency"]) is not int or row["concurrency"] not in {1, 2}
                or not (row["excluded_food"] is None or
                        (type(row["excluded_food"]) is str and 0 < len(row["excluded_food"]) <= 100))
                or (row["subject"] == "individual" and (row["factory"] != "web" or row["type"] != "opciones"))):
            raise ValueError("Unsupported or unbounded generation cell")
        total += row["samples"]
    if total > args.max_generations or 2 * total + 2 * len(value["cells"]) + 40 > args.max_http:
        raise ValueError("Planned cells exceed generation/HTTP budget including controls/readiness")
    if args.max_object_bytes < len({row["factory"] for row in value["cells"]}):
        raise ValueError("Each selected factory requires a positive share of the global object budget")
    for factory in {row["factory"] for row in value["cells"]}:
        ramp = [row["concurrency"] for row in value["cells"] if row["factory"] == factory]
        if ramp != sorted(ramp):
            raise ValueError("Each requested factory ramp must preserve C1 before C2")
    return value, raw_sha


def build_contract(args):
    from tests.billing13_legacy_apply37_pg_contract import validated_generation, pg_binary_directory
    from tests.ci_web37.pg_lease import profile
    from web.database.schema_control import expected_head
    if (os.name != "nt" or ROOT != REPOSITORY or Path(sys.executable).resolve() != RUNNER.resolve()
            or re.fullmatch("[0-9a-f]{40}", args.source or "") is None
            or type(args.seconds) is not int or not 1 <= args.seconds <= 1800
            or type(args.max_http) is not int or not 1 <= args.max_http <= 300
            or type(args.max_generations) is not int or not 1 <= args.max_generations <= 100
            or type(args.max_object_bytes) is not int or not 1 <= args.max_object_bytes <= 64 * 1024**2):
        raise ValueError("Explicit current source/E Web92 and bounded Root workload required")
    if (args.output.parent != WORKSPACE / "tmp"
            or re.fullmatch("metodobase-account37-author-pg-generation-[0-9a-f]{32}", args.output.name) is None
            or Path(tempfile.gettempdir()).resolve() != WORKSPACE / "tmp"):
        raise ValueError("Fresh direct E temporary UUID namespace required")
    for path in args.output.parents:
        if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Output ancestor alias rejected")
    _, profile_sha = private_control(args.private_env)
    config = profile(args.private_env, expected_sha256=profile_sha)
    if pg_binary_directory(config) != WORKSPACE / "tools/postgresql17/bin":
        raise ValueError("Current E PostgreSQL17 directory required")
    generation, generation_sha = private_control(args.generation)
    validated_generation(generation)
    cells, workload_sha = workload(args)
    photo = sources()
    if photo["HEAD"] != args.source:
        raise ValueError("Actual source differs from Root FULL40")
    pins = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (*HELPERS, Path(__file__).relative_to(ROOT).as_posix())}
    return {"schema": SCOPE, "source_commit": args.source, "source_photo": photo,
            "expected_schema_revision": expected_head(), "driver_helper_RAW_sha256": pins,
            "profile_path": str(args.private_env), "profile_sha256": profile_sha,
            "generation_path": str(args.generation), "generation_sha256": generation_sha,
            "generation": generation, "workload_path": str(args.workload), "workload_sha256": workload_sha,
            "workload": cells, "server_port": 55483, "UUIDs": 1, "concurrent_UUIDs": 1,
            "output": str(args.output), "runner": str(RUNNER),
            "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
            "postgres_sha256": hashlib.sha256((pg_binary_directory(config) / "postgres.exe").read_bytes()).hexdigest(),
            "bounds": {"seconds": args.seconds, "HTTP": args.max_http,
                       "generations": args.max_generations, "object_bytes": args.max_object_bytes,
                       "maximum_client_concurrency": 2},
            "closure": "same_cursor_before_CREATE_common_close_original_owner_normal_DROP_fresh_absence"}


def checked_load_runtime(args):
    from tests.ci_web37.pg_lease import profile
    contract = build_contract(args)
    grant, _ = private_control(args.lease_ack)
    validate_ack(grant, contract)
    return contract, profile(args.private_env, expected_sha256=contract["profile_sha256"])


def seed_generation(admin, restricted, cells, deadline):
    """One legitimate Free generation per fresh tenant/client; no quota waiver."""
    from sqlalchemy.orm import Session
    from web.auth import crear_access_token, identity_from_user, init_auth
    from web.database.models import Cliente, Usuario, UserRole
    from src.alimentos_base import ALIMENTOS_BASE
    from core.nutrition_restrictions import NutritionRestrictions
    jobs, tokens = [], {}
    for cell_number, cell in enumerate(cells):
        food = cell["excluded_food"]
        if food is not None and food not in ALIMENTOS_BASE:
            raise ValueError("Excluded food must exist in the actual bound catalogue")
        for number in range(cell["samples"]):
            if time.monotonic() >= deadline:
                raise CaptureRejected("Capture deadline exhausted before another synthetic identity")
            owner, client = str(uuid.uuid4()), str(uuid.uuid4())
            sample = uuid.uuid4().hex
            declaration = NutritionRestrictions.from_profile(ALIMENTOS_BASE).declaration_payload()
            synthetic_input = {"edad": 30, "sexo": "M", "peso_kg": 75, "estatura_cm": 175,
                               "grasa_corporal_pct": 20, "nivel_actividad": "moderada",
                               "objetivo": "mantenimiento", "restrictions": declaration,
                               "excluded_foods": [] if food is None else [food]}
            jobs.append({"sample": sample, "download_sample": sample + "-pdf", "control_sample": sample + "-foreign",
                         "replay_sample": sample + "-replay",
                         "cell": cell_number, "ordinal": number, "owner": owner, "client": client,
                         "factory": cell["factory"], "subject": cell["subject"], "type": cell["type"],
                         "exclusion": "none" if food is None else "one_valid_food",
                          "synthetic_input_SHA256": digest(synthetic_input),
                          "effective_exclusions_SHA256": digest([] if food is None else [food]),
                          "catalogue_RAW_SHA256": hashlib.sha256((ROOT / "src/alimentos_base.py").read_bytes()).hexdigest(),
                         "concurrency": cell["concurrency"]})
            with Session(admin) as db:
                db.add(Usuario(id=owner, email=sample + "@example.invalid", nombre="Synthetic R34",
                               password_hash="synthetic-not-a-login", activo=True,
                               tipo="usuario" if cell["subject"] == "individual" else "gym",
                               role=UserRole.VIEWER if cell["subject"] == "individual" else UserRole.OWNER))
                db.flush()
                db.add(Cliente(id_cliente=client, gym_id=owner, nombre="Synthetic R34", edad=30,
                               sexo="M", peso_kg=75, estatura_cm=175, grasa_corporal_pct=20,
                               nivel_actividad="moderada", objetivo="mantenimiento", activo=True,
                               nutrition_restrictions_json=json.dumps(declaration),
                               alimentos_excluidos=json.dumps([] if food is None else [food])))
                db.commit()
    os.environ["DATABASE_URL"] = restricted.url.render_as_string(hide_password=False)
    init_auth()
    principals = {}
    with Session(restricted) as db:
        for job in jobs:
            identity = identity_from_user(db.get(Usuario, job["owner"]), db)
            tokens[job["owner"]] = crear_access_token(identity)
            principals[job["owner"]] = {key: identity[key]
                for key in ("id", "tipo", "role", "team_gym_id", "session_version")}
    # The final analytics candidate supplies this real append-only declaration API.
    # Missing API/schema rejects the new run; no fabricated column or fallback.
    from web.services.product_analytics_v2 import origin
    for job in jobs:
        if time.monotonic() >= deadline:
            raise CaptureRejected("Capture deadline exhausted before demo declaration")
        with Session(restricted) as fresh:
            origin(fresh, principals[job["owner"]],
                   "personal" if job["subject"] == "individual" else "gym",
                   None if job["subject"] == "individual" else job["client"],
                   value="demo", expected_version=0)
    return jobs, tokens


def retain(reason):
    """Keep the active Python stack, Popen/FDs and owned DB on uncertain close."""
    del reason
    while True:
        try:
            time.sleep(60)
        except BaseException:
            pass


def serve(args):
    from tests.isolation import prepare_environment, block_external_sockets, validate_postgres_test_url
    contract, config = checked_load_runtime(args)
    if (type(args.deadline) is not float or not math.isfinite(args.deadline)
            or not 0 < args.deadline - time.monotonic() <= args.seconds
            or type(args.port) is not int or not 0 < args.port < 65536
            or not re.fullmatch("[0-9a-f]{32}", args.nonce or "")
            or args.ready != args.output / (args.factory + "-ready.json")):
        raise ValueError("Exact bounded original parent child arguments required")
    from tests.ci_web39.pg_control import check_control_generation
    url = validate_postgres_test_url(os.environ["METODOBASE_TEST_DATABASE_URL"])
    parsed = urlsplit(url)
    identifier = parsed.path.removeprefix("/metodobase_test_account37_")
    if not re.fullmatch("[0-9a-f]{32}", identifier):
        raise ValueError("Exact parent owned UUID required")
    lease = json.loads((args.output / "leases" / ("lease-" + identifier + ".json")).read_bytes())
    if (lease["database"] != parsed.path.lstrip("/") or lease["state"] != "created"
            or parsed.port != 55483 or parsed.hostname != "127.0.0.1"
            or parsed.username != urlsplit(config["METODOBASE_TEST_POSTGRES_URL"]).username):
        raise ValueError("Child accepts only its created UUID/restricted app role")
    check_control_generation(contract, config)
    os.environ["_METODOBASE_TEST_ROOT"] = str(args.output / "metodobase-test-data")
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    os.environ.update(BASE_URL=f"http://127.0.0.1:{args.port}", CORS_ORIGINS=f"http://127.0.0.1:{args.port}")
    logging.disable(logging.CRITICAL)
    assignment_raw = (args.output / "assignments.json").read_bytes()
    if hashlib.sha256(assignment_raw).hexdigest() != args.assignments_sha256:
        raise ValueError("Parent assignment bytes differ")
    assignments = json.loads(assignment_raw)
    jobs = [row for row in assignments if row["factory"] == args.factory]
    if len(jobs) != sum(row["samples"] for row in contract["workload"]["cells"] if row["factory"] == args.factory):
        raise ValueError("Closed selected assignment count differs")
    factories = {row["factory"] for row in assignments}
    labels = {}
    for row in jobs:
        base = {key: row[key] for key in ("factory", "subject", "type", "exclusion", "cell", "ordinal", "concurrency",
                                        "synthetic_input_SHA256", "catalogue_RAW_SHA256")}
        labels[row["sample"]] = base | {"operation": "generation"}
        labels[row["download_sample"]] = base | {"operation": "download"}
        labels[row["control_sample"]] = base | {"operation": "foreign_read_control"}
        labels[row["replay_sample"]] = base | {"operation": "idempotent_replay"}
    recorder = Recorder(maximum_generations=len(jobs), deadline=args.deadline,
                        maximum_object_bytes=args.max_object_bytes // len(factories))
    from sqlalchemy import event
    from web.database.engine import get_engine
    from web.database.schema_control import verify_runtime_schema
    from web.storage.local import LocalObjectStore
    from web.storage.runtime import get_object_store
    module = __import__("web.main_web" if args.factory == "web" else "api.app", fromlist=["create_app"])
    application = module.create_app()
    expected_module = "web.routes.planes" if args.factory == "web" else "api.routes.planes"
    generation_endpoint = __import__(expected_module, fromlist=["generar_plan"]).generar_plan
    original_lifespan = application.router.lifespan_context
    active, active_lock = {"pool": 0, "ASGI": 0, "HTTP": 0}, threading.Lock()
    maximum_http = 2 * len(jobs) + 2 * len({row["cell"] for row in jobs}) + 20

    def sql_before(connection, cursor, statement, parameters, context, executemany):
        del connection, cursor, parameters, executemany
        row = CURRENT.get()
        if row is not None:
            row.counter("SQL_" + statement.lstrip().split(None, 1)[0].upper())
            context._r34_begin = time.perf_counter_ns()

    def sql_after(connection, cursor, statement, parameters, context, executemany):
        del connection, cursor, statement, parameters, executemany
        if CURRENT.get() is not None and hasattr(context, "_r34_begin"):
            CURRENT.get().counter("SQL_cursor_elapsed_ns", time.perf_counter_ns() - context._r34_begin)

    def checkout(connection, record, proxy):
        del connection, record, proxy
        with active_lock:
            active["pool"] += 1
            if CURRENT.get() is not None:
                CURRENT.get().counter("pool_checkouts")
                CURRENT.get().counters["pool_peak"] = max(CURRENT.get().counters.get("pool_peak", 0), active["pool"])

    def checkin(connection, record):
        del connection, record
        with active_lock:
            active["pool"] -= 1

    @asynccontextmanager
    async def lifespan(app):
        instrumentation_closed = False
        async with original_lifespan(app):
            engine = get_engine()
            verify_runtime_schema(engine, require_revision=True)
            store = get_object_store()
            if type(store) is not LocalObjectStore:
                raise ValueError("Real LocalObjectStore required, no SDK/fallback")
            if not store.root.is_relative_to(args.output / "metodobase-test-data"):
                raise ValueError("Local objects must remain in the owned E test root")
            from tests.performance.generation_observer import Patches
            with Patches() as patches, install_application_hooks(recorder):
                patches.set(engine.pool, "_do_get", recorder.wrap("pool.acquire", engine.pool._do_get))
                callbacks = (("before_cursor_execute", sql_before), ("after_cursor_execute", sql_after),
                             ("checkout", checkout), ("checkin", checkin))
                for name, callback in callbacks:
                    event.listen(engine, name, callback)
                from tests.billing13_legacy_apply37_pg_contract import windows_process_identity
                birth, executable = windows_process_identity(os.getpid())
                routes = generation_routes(application, generation_endpoint)
                write_json(args.ready, {"nonce": args.nonce, "pid": os.getpid(), "parent_pid": os.getppid(),
                           "birth_filetime_100ns": birth, "executable": str(executable), "argv": sys.argv,
                           "factory": args.factory, "routes": routes,
                           "pool_observed_QA": {"size": engine.pool.size(), "max_overflow": engine.pool._max_overflow,
                                                "timeout_seconds": engine.pool.timeout(), "workers": 1},
                           "local_object_root": str(store.root), "schema_revision": contract["expected_schema_revision"]})
                args.ready.with_suffix(".closed").touch(exist_ok=False)
                try:
                    yield
                finally:
                    failures = []
                    for name, callback in callbacks:
                        try:
                            event.remove(engine, name, callback)
                        except BaseException as error:
                            failures.append(type(error).__name__)
                    if active["pool"] or active["ASGI"] or active["HTTP"] > maximum_http or failures:
                        raise CaptureRejected("Application lifecycles/pool/listener closure incomplete")
                    engine.dispose()
            instrumentation_closed = True
        if instrumentation_closed is not True:
            raise CaptureRejected("Instrumentation did not exit normally")
        # A late hook restoration or original lifespan error must leave this
        # positive receipt absent, even when uvicorn would still return exit0.
        write_json(args.output / (args.factory + "-observer-closed.json"),
                   {"generations": recorder.generations, "PUT_attempted_bytes": recorder.object_bytes,
                    "lifecycles_open": active["ASGI"], "pool_loans": active["pool"],
                    "HTTP_requests": active["HTTP"],
                    "listeners_removed": True, "normal_lifespan_closed": True})

    application.router.lifespan_context = lifespan

    class ObservedApplication:
        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                try:
                    return await application(scope, receive, send)
                except BaseException as error:
                    if scope["type"] == "lifespan":
                        record_worker_error(args, error)
                    raise
            with active_lock:
                active["HTTP"] += 1
                if active["HTTP"] > maximum_http:
                    raise CaptureRejected("Per-factory share of HTTP budget exhausted")
            identifier = dict(scope.get("headers", [])).get(b"x-generation-sample", b"").decode("ascii")
            if identifier not in labels:
                return await application(scope, receive, send)
            with recorder.sample(identifier, labels[identifier]) as row:
                with active_lock:
                    active["ASGI"] += 1
                    row.counter("ASGI_open_at_start", active["ASGI"])
                async def observed_send(message):
                    if message["type"] == "http.response.start":
                        row.counter("HTTP_status", message["status"])
                    elif message["type"] == "http.response.body":
                        row.counter("response_body_bytes", len(message.get("body", b"")))
                    await send(message)
                try:
                    with recorder.span("ASGI_lifecycle_including_background"):
                        await application(scope, receive, observed_send)
                finally:
                    with active_lock:
                        active["ASGI"] -= 1
                    path = args.output / "observations" / (identifier + ".json")
                    with path.open("x", encoding="utf8", newline="\n") as stream:
                        json.dump(row.snapshot(), stream, sort_keys=True)
                        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
                    # The parent reads the row only after this closed marker exists.
                    path.with_suffix(".closed").touch(exist_ok=False)
    run_server_until_eof(ObservedApplication(), args)


class HTTPBudget:
    def __init__(self, maximum, deadline):
        self.maximum, self.deadline, self.used = maximum, deadline, 0
        self.lock = threading.Lock()

    def request(self, client, method, path, *, limit, **kwargs):
        if not path.startswith("/") or path.startswith("//"):
            raise CaptureRejected("Only same-loopback relative HTTP paths allowed")
        with self.lock:
            remaining = self.deadline - time.monotonic()
            if self.used >= self.maximum or remaining <= 0:
                raise CaptureRejected("HTTP/deadline budget exhausted before request")
            self.used += 1
        started = time.perf_counter_ns()
        with client.stream(method, path, timeout=remaining, **kwargs) as response:
            body = bytearray()
            for part in response.iter_bytes():
                body.extend(part)
                if len(body) > limit:
                    raise CaptureRejected("Bounded HTTP body exceeded")
            return {"status": response.status_code, "body": bytes(body),
                    "content_type": response.headers.get("content-type", ""),
                    "elapsed_ms": (time.perf_counter_ns() - started) / 1_000_000}


def wait_observation(output, identifier, deadline):
    path = output / "observations" / (identifier + ".json")
    while not path.with_suffix(".closed").exists():
        if time.monotonic() >= deadline:
            raise CaptureRejected("Complete ASGI/background observation absent at deadline")
        time.sleep(.025)
    row = json.loads(path.read_bytes())
    spans = row["spans"]
    if (row["sample"] != identifier or row["capture_errors"] or not spans
            or len({span["id"] for span in spans}) != len(spans)
            or any(span["elapsed_ns"] < 0 for span in spans)):
        raise CaptureRejected("Observation correlation/identity differs")
    ids = {span["id"] for span in spans}
    if any(span["parent"] is not None and span["parent"] not in ids for span in spans):
        raise CaptureRejected("Observed span parent missing")
    return row


def verify_publication(admin, job, plan_id, downloaded, key):
    """Independent control-plane oracle; HTTP still uses the restricted app."""
    from sqlalchemy.orm import Session
    from web.database.models import (PlanGenerado, StoredObject, GymGenerationReservation,
                                     GenerationReservation, UserSubscription, ProductAnalyticsFact)
    with Session(admin) as db:
        plan = db.get(PlanGenerado, plan_id)
        if (plan is None or plan.gym_id != job["owner"] or plan.id_cliente != job["client"]
                or plan.tipo_plan != job["type"] or not plan.pdf_object_id):
            raise CaptureRejected("Actual published Plan ownership/type differs")
        document = db.get(StoredObject, plan.pdf_object_id)
        if (document is None or document.status != "ready" or document.gym_id != job["owner"]
                or document.kind != "plan_pdf" or document.storage_backend != "local"
                or document.byte_size != len(downloaded)
                or document.sha256 != hashlib.sha256(downloaded).hexdigest()
                or not downloaded.startswith(b"%PDF-")):
            raise CaptureRejected("Actual PDF/descriptor/local object differs")
        model = GymGenerationReservation if job["subject"] == "gym" else GenerationReservation
        query = db.query(model).filter(model.request_key == key)
        query = query.filter(model.gym_id == job["owner"]) if job["subject"] == "gym" else query.filter(model.user_id == job["owner"])
        reservation = query.one()
        if reservation.status != "completed" or reservation.plan_id != plan_id or reservation.persisted_at is None:
            raise CaptureRejected("Published consumption/marker not completed exactly")
        if db.query(PlanGenerado).filter_by(gym_id=job["owner"]).count() != 1:
            raise CaptureRejected("Fresh synthetic tenant published more than one Plan")
        owner_rows = db.query(model).filter(model.gym_id == job["owner"]) if job["subject"] == "gym" else db.query(model).filter(model.user_id == job["owner"])
        if owner_rows.count() != 1:
            raise CaptureRejected("Fresh synthetic tenant consumed more than one reservation")
        if job["subject"] == "individual":
            if db.query(UserSubscription).filter_by(user_id=job["owner"]).one().planes_usados_mes != 1:
                raise CaptureRejected("Actual individual monthly debit differs")
        fact = db.query(ProductAnalyticsFact).filter_by(owner_id=job["owner"],
            context="personal" if job["subject"] == "individual" else "gym",
            client_id=None if job["subject"] == "individual" else job["client"],
            event_type="plan_saved", source_id=str(plan_id), source_version=1).one()
        if fact.origin != "demo":
            raise CaptureRejected("Actual committed Plan fact lacks its declared synthetic origin")
        return {"plan_id": plan_id, "object_SHA256": document.sha256, "PDF_bytes": len(downloaded),
                "plan_JSON_SHA256": hashlib.sha256(plan.plan_json.encode()).hexdigest(),
                "reservation_completed": True, "published_marker": True, "source_fact_origin": "demo"}


def retained_publication_state(admin, jobs, shutdown):
    """Observe real business state after all own HTTP children closed, never repair it."""
    from sqlalchemy.orm import Session
    from web.database.models import PlanGenerado, StoredObject, GymGenerationReservation, GenerationReservation
    rows = []
    with Session(admin) as db:
        for job in jobs:
            model = GymGenerationReservation if job["subject"] == "gym" else GenerationReservation
            query = db.query(model).filter(model.request_key == "r34-" + job["sample"])
            query = query.filter(model.gym_id == job["owner"]) if job["subject"] == "gym" else query.filter(model.user_id == job["owner"])
            reservations = query.all()
            plans = db.query(PlanGenerado).filter_by(gym_id=job["owner"]).all()
            objects = db.query(StoredObject).filter_by(gym_id=job["owner"]).all()
            rows.append({"sample": job["sample"], "reservations": [
                {"status": row.status, "plan_id": row.plan_id, "persisted_marker": row.persisted_at is not None}
                for row in reservations], "plan_count": len(plans),
                "objects": [{"status": row.status, "bytes": row.byte_size, "sha256": row.sha256}
                            for row in objects]})
    return {"server_started": shutdown["server_started"],
            "own_server_normal_closure": shutdown["owned_server_stopped"],
            "repair_or_refund": False, "samples": rows}


def perform_generation(base, job, tokens, admin, args, budget, control):
    import httpx
    identifier = job["sample"]
    key = "r34-" + identifier
    headers = {"Authorization": "Bearer " + tokens[job["owner"]],
               "X-Generation-Sample": identifier, "Idempotency-Key": key}
    path = "/api/generar-plan" if job["subject"] == "gym" else "/api/usuario/generar-plan"
    payload = {"id_cliente": job["client"], "plan_numero": 1, "tipo_plan": job["type"]} if job["subject"] == "gym" else None
    with httpx.Client(base_url=base, trust_env=False, follow_redirects=False) as client:
        generated = budget.request(client, "POST", path, limit=4 * 1024**2, headers=headers, json=payload)
        if generated["status"] != 200:
            raise CaptureRejected("Real generation did not return200; no retry or quota waiver")
        response = json.loads(generated["body"])
        plan_id, pdf_url = response.get("plan_id"), response.get("pdf_url")
        if type(plan_id) is not int or plan_id <= 0 or type(pdf_url) is not str:
            raise CaptureRejected("Actual generation response identity missing")
        observation = wait_observation(args.output, identifier, budget.deadline)
        required = {"generation", "client_lock.acquire", "generation.build", "core." + job["type"],
                    "render." + job["type"], "object.publish_pending", "object.local.PUT", "plan.stage", "transaction.commit"}
        if (not required <= {span["name"] for span in observation["spans"]}
                or observation["counters"].get("generation_calls") != 1
                or observation["counters"].get("executor_starts") != 1):
            raise CaptureRejected("Mandatory delegated generation spans missing")
        download_headers = {"Authorization": headers["Authorization"], "X-Generation-Sample": job["download_sample"]}
        downloaded = budget.request(client, "GET", pdf_url, limit=64 * 1024**2, headers=download_headers)
        if downloaded["status"] != 200 or not downloaded["content_type"].startswith("application/pdf"):
            raise CaptureRejected("Authorized actual PDF download failed")
        downloaded_observation = wait_observation(args.output, job["download_sample"], budget.deadline)
        proof = verify_publication(admin, job, plan_id, downloaded["body"], key)
        catalogue = observation["facts"].get("core_catalogue", {})
        if (catalogue.get("excluded_sha256") != job["effective_exclusions_SHA256"]
                or catalogue.get("excluded_count") != (0 if job["exclusion"] == "none" else 1)):
            raise CaptureRejected("Actual core catalogue exclusion differs from the bound synthetic input")
        if observation["facts"].get("rendered_PDF") != {"bytes": proof["PDF_bytes"], "sha256": proof["object_SHA256"]}:
            raise CaptureRejected("Closed renderer bytes differ from published and downloaded PDF")
        with (args.output / "samples" / (identifier + "-publication.json")).open("x", encoding="utf8") as stream:
            json.dump({"sample": identifier, "POST_ms": generated["elapsed_ms"],
                       "PDF_GET_ms": downloaded["elapsed_ms"], "publication": proof}, stream)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        foreign = None
        replay_result = None
        if control:
            other = next(owner for owner in tokens if owner != job["owner"])
            foreign = budget.request(client, "GET", pdf_url, limit=1024**2,
                                     headers={"Authorization": "Bearer " + tokens[other],
                                              "X-Generation-Sample": job["control_sample"]})
            if foreign["status"] not in {403, 404}:
                raise CaptureRejected("Foreign tenant PDF access accepted")
            wait_observation(args.output, job["control_sample"], budget.deadline)
            replay = budget.request(client, "POST", path, limit=4 * 1024**2,
                                    headers=headers | {"X-Generation-Sample": job["replay_sample"]}, json=payload)
            if replay["status"] != 200 or json.loads(replay["body"]) != response:
                raise CaptureRejected("Same authenticated idempotency key did not replay the exact result")
            replay_observation = wait_observation(args.output, job["replay_sample"], budget.deadline)
            if (replay_observation["counters"].get("generation_calls", 0) != 0
                    or any(span["name"].startswith(("core.", "render."))
                           or span["name"] == "object.local.PUT" for span in replay_observation["spans"])):
                raise CaptureRejected("Idempotent replay performed new core/render/PUT")
            verify_publication(admin, job, plan_id, downloaded["body"], key)
            replay_result = {"elapsed_ms": replay["elapsed_ms"], "exact_result": True,
                             "new_core_render_PUT": False, "observation": replay_observation}
        result = {"sample": identifier, "cell": job["cell"], "factory": job["factory"],
                "subject": job["subject"], "type": job["type"], "exclusion": job["exclusion"],
                "generation_process_phase": observation["labels"]["generation_process_phase"],
                "POST_ms": generated["elapsed_ms"], "PDF_GET_ms": downloaded["elapsed_ms"],
                "publication": proof, "generation_observation": observation,
                "download_observation": downloaded_observation,
                "idempotent_hot_client_replay_separate": replay_result,
                "foreign_read_denied": None if foreign is None else True}
        # Preserve each completed measurement even if another concurrent sample fails.
        with (args.output / "samples" / (identifier + ".json")).open("x", encoding="utf8") as stream:
            json.dump(result, stream, sort_keys=True)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        return result


def preserve_generation(base, job, tokens, admin, args, budget, control):
    try:
        return perform_generation(base, job, tokens, admin, args, budget, control)
    except BaseException as error:
        # Keep the first failed request identity/class, never exception text or bearer.
        with (args.output / "samples" / (job["sample"] + "-error.json")).open("x", encoding="utf8") as stream:
            json.dump({"sample": job["sample"], "cell": job["cell"],
                       "accepted": False, "error_class": type(error).__name__}, stream)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        raise


def run_factory(args, factory, jobs, tokens, admin, restricted, budget, shutdown):
    import httpx
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    ready = args.output / (factory + "-ready.json")
    worker_identity = args.output / (factory + "-worker-identity.json")
    nonce = uuid.uuid4().hex
    child_env = os.environ.copy()
    child_env["METODOBASE_TEST_DATABASE_URL"] = restricted.url.render_as_string(hide_password=False)
    child_env["_METODOBASE_TEST_ROOT"] = str(args.output / "metodobase-test-data")
    argv = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()),
            "--source", args.source, "--private-env", str(args.private_env), "--generation", str(args.generation),
            "--lease-ack", str(args.lease_ack), "--workload", str(args.workload), "--output", str(args.output),
            "--seconds", str(args.seconds), "--max-http", str(args.max_http),
            "--max-generations", str(args.max_generations), "--max-object-bytes", str(args.max_object_bytes),
            "--serve", "--factory", factory, "--port", str(port), "--ready", str(ready),
            "--nonce", nonce, "--deadline", str(budget.deadline)]
    argv += ["--assignments-sha256", hashlib.sha256((args.output / "assignments.json").read_bytes()).hexdigest()]
    # Original mechanism, separate per-server path, no stdout/DEVNULL diagnostic loss.
    logs_dir = args.output / (factory + "-server")
    from web.services.legacy_object_apply_boundary import create_private_directory
    create_private_directory(logs_dir)
    streams, log_record = open_server_logs(logs_dir)
    process, identity, failure, rows = None, None, None, []
    shutdown.update(server_started=False, owned_server_stopped=False, stop_requested=False,
                    observer_accepted=False, server_exit_code=None)
    base = f"http://127.0.0.1:{port}"
    try:
        process = subprocess.Popen(argv, cwd=ROOT, env=child_env, stdin=subprocess.PIPE,
                                   stdout=streams["stdout"], stderr=streams["stderr"],
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        process._load_nonce = nonce
        shutdown["server_started"] = True
        while not ready.with_suffix(".closed").exists():
            if identity is None and worker_identity.with_suffix(".closed").exists():
                identity = json.loads(worker_identity.read_bytes())
                check_server_identity(process, identity)
            if process.poll() is not None or time.monotonic() >= budget.deadline:
                raise CaptureRejected("Server readiness absent; original process retained")
            time.sleep(.05)
        identity = json.loads(ready.read_bytes())
        check_server_identity(process, identity)
        with httpx.Client(base_url=base, trust_env=False) as client:
            for attempt in range(20):
                try:
                    response = budget.request(client, "GET", "/health/ready", limit=1024**2)
                    if response["status"] == 200 and json.loads(response["body"]).get("ready") is True:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.1)
            else:
                raise CaptureRejected("Actual application readiness unconfirmed")
        start_process = process_snapshot(identity["pid"])
        cells = sorted({row["cell"] for row in jobs if row["factory"] == factory})
        for cell in cells:
            checked_load_runtime(args)  # Fresh source/profile/generation/ACK before another cell.
            selected = [row for row in jobs if row["cell"] == cell]
            with ThreadPoolExecutor(max_workers=selected[0]["concurrency"]) as executor:
                futures = [executor.submit(preserve_generation, base, job, tokens, admin, args, budget, index == 0)
                           for index, job in enumerate(selected)]
                rows.extend(future.result() for future in futures)
        end_process = process_snapshot(identity["pid"])
        return rows, {"factory": factory, "identity": identity,
                      "process_before": start_process, "process_after": end_process,
                      "CPU_RSS_scope": "actual server PID, includes instrumentation/background; not PostgreSQL/client"}
    except BaseException as error:
        failure = error
        raise
    finally:
        closure_error = None
        if process is not None:
            # Request EOF even after publication/measurement error. Never hash live logs.
            try:
                if identity is None and worker_identity.with_suffix(".closed").exists():
                    identity = json.loads(worker_identity.read_bytes())
                    # The child may already have exited. stop_own_server verifies
                    # the early attributed worker's native exit, without signalling.
                    if (identity["nonce"] != nonce or process.pid not in (identity["pid"], identity["parent_pid"])
                            or identity["argv"] != argv[4:]):
                        raise CaptureRejected("Closed early worker identity binding differs")
                shutdown["server_exit_code"] = stop_own_server(process, identity)
                shutdown["owned_server_stopped"] = True
                shutdown["stop_requested"] = True
                if shutdown["server_exit_code"] != 0:
                    raise CaptureRejected("Own application child exited unsuccessfully")
                closed = json.loads((args.output / (factory + "-observer-closed.json")).read_bytes())
                if (closed["normal_lifespan_closed"] is not True or closed["lifecycles_open"] != 0
                        or closed["pool_loans"] != 0 or closed["listeners_removed"] is not True):
                    raise CaptureRejected("Observer/process closure rejected")
                shutdown["observer_accepted"] = True
            except BaseException as error:
                # The whole frame keeps original Popen/FDs/owned context, even if diagnostics fail.
                if shutdown["owned_server_stopped"] is not True:
                    retain("server_closure_uncertain")
                closure_error = error
        close_server_logs(streams, log_record, shutdown)
        log_record["application_observer_accepted"] = shutdown.get("observer_accepted", False)
        log_record["server_exit_code"] = shutdown.get("server_exit_code")
        write_json(logs_dir / "closed-logs.json", log_record)
        if failure is not None:
            write_json(logs_dir / "first-error.json", {"error_class": type(failure).__name__})
        if closure_error is not None:
            write_json(logs_dir / "rejected-child-close.json", {"error_class": type(closure_error).__name__,
                       "physical_child_waited": True, "application_observer_accepted": False})
            if failure is None:
                raise closure_error


def main(args):
    started = time.monotonic()
    contract, _ = checked_load_runtime(args)
    from web.services.legacy_object_apply_boundary import create_private_directory
    create_private_directory(args.output)
    create_private_directory(args.output / "observations")
    create_private_directory(args.output / "samples")
    os.environ["_METODOBASE_TEST_ROOT"] = str(args.output / "metodobase-test-data")
    isolated_environment()
    from sqlalchemy import text
    from tests.integration_schema_migrations import run_migration
    from tests.integration_provider_subjects import application_engine
    from web.database.tenant_policy import verify_application_database_role
    before, environment_before = sources(), current_environment_photo()
    report = {"schema": "local-generation-characterization-result-v1", "source": args.source,
              "contract_SHA256": digest(contract), "accepted": False, "SLO": None,
              "schema_revision": None, "factory_observations": [], "samples": [],
              "bounds": contract["bounds"], "cold_definition": "first actual generation per process, not OS/PG cache cold",
              "scope": "real core/PDF/local PUT/read, authenticated restricted PG; no remote S3/mail/broker/arrival-rate claim"}
    budget = HTTPBudget(args.max_http, started + args.seconds)
    shutdown = {"server_started": False, "owned_server_stopped": False, "stop_requested": False}
    error = None
    jobs = []
    try:
        if time.monotonic() >= budget.deadline:
            raise CaptureRejected("Capture deadline exhausted before UUID admission")
        with owned_database(args, shutdown) as (url, admin, cleanup):
            report["cleanup"] = cleanup
            if time.monotonic() >= budget.deadline:
                raise CaptureRejected("Capture deadline exhausted before migration")
            run_migration(url, "db_bootstrap.py", "--revision", "head")
            restricted = application_engine(url, admin)
            try:
                verify_application_database_role(restricted)
                with admin.connect() as connection:
                    revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
                    if revision != contract["expected_schema_revision"]:
                        raise CaptureRejected("Migrated schema is not the bound current head")
                    report["schema_revision"] = revision
                    report["PostgreSQL_version"] = connection.scalar(text("SHOW server_version"))
                    report["PostgreSQL_timezone"] = connection.scalar(text("SHOW TimeZone"))
                jobs, tokens = seed_generation(admin, restricted, contract["workload"]["cells"], budget.deadline)
                # Assignment file contains labels/own synthetic IDs, never bearer tokens.
                write_json(args.output / "assignments.json", jobs)
                for factory in sorted({row["factory"] for row in jobs}):
                    rows, observation = run_factory(args, factory, jobs, tokens, admin, restricted, budget, shutdown)
                    report["samples"].extend(rows)
                    report["factory_observations"].append(observation)
                expected = sum(row["samples"] for row in contract["workload"]["cells"])
                if len(report["samples"]) != expected or time.monotonic() >= budget.deadline:
                    raise CaptureRejected("Sample/deadline integrity rejected")
                for cell in range(len(contract["workload"]["cells"])):
                    for process_phase in ("first_generation", "subsequent_generation"):
                        selected = [row for row in report["samples"] if row["cell"] == cell
                                    and row["generation_process_phase"] == process_phase]
                        report.setdefault("descriptive_cells", []).append({"cell": cell,
                            "generation_process_phase": process_phase,
                            "POST_ms": quantiles([row["POST_ms"] for row in selected]),
                            "PDF_GET_ms": quantiles([row["PDF_GET_ms"] for row in selected]),
                            "phases": {phase: quantiles([span["elapsed_ns"] / 1_000_000
                                         for row in selected for span in row["generation_observation"]["spans"]
                                         if span["name"] == phase])
                                       for phase in sorted({span["name"] for row in selected
                                           for span in row["generation_observation"]["spans"]})}})
                report["accepted"] = True
            except BaseException:
                if jobs and (shutdown["server_started"] is False or shutdown["owned_server_stopped"] is True):
                    # The HTTP child is normally closed; an HTTP timeout alone never
                    # authorizes refund, pending cleanup or a new generation.
                    try:
                        report["state_after_first_failure"] = retained_publication_state(admin, jobs, shutdown)
                    except BaseException as state_error:
                        report["state_after_first_failure"] = {"observed": False,
                                                               "error_class": type(state_error).__name__}
                raise
            finally:
                restricted.dispose()
        close_records = list((args.output / "pool-close").glob("*.json"))
        if len(close_records) != 1 or json.loads(close_records[0].read_bytes())["accepted"] is not True:
            raise CaptureRejected("Original/common one-UUID normal closure rejected")
    except BaseException as failure:
        error = failure
        report.update(accepted=False, error_class=type(failure).__name__)
    finally:
        after, environment_after = sources(), current_environment_photo()
        report.update(source_quiet=before == after, environment_quiet=environment_before == environment_after,
                      HTTP_requests=budget.used, elapsed_seconds=time.monotonic() - started,
                      deadline_exceeded=time.monotonic() >= budget.deadline,
                      in_flight_or_cleanup_never_force_killed=True)
        report["accepted"] = bool(report["accepted"] and report["source_quiet"] and report["environment_quiet"]
                                  and not report["deadline_exceeded"]
                                  and report.get("cleanup", {}).get("owned_uuid_database_removed"))
        write_json(args.output / "source-before-after.json", {"before": before, "after": after})
        write_json(args.output / "environment-before-after.json", {"before": environment_before, "after": environment_after})
        write_json(args.output / "report.json", report)
    if error is not None:
        print(json.dumps({"accepted": False, "error_class": type(error).__name__}))
        return 1
    print(json.dumps({"accepted": report["accepted"], "samples": len(report["samples"]), "SLO": None}))
    return int(not report["accepted"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("private-env", "generation", "lease-ack", "workload", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source", required=True)
    for name in ("seconds", "max-http", "max-generations", "max-object-bytes"):
        parser.add_argument("--" + name, type=int, required=True)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--factory", choices=("web", "api"))
    parser.add_argument("--port", type=int)
    parser.add_argument("--ready", type=Path)
    parser.add_argument("--nonce")
    parser.add_argument("--deadline", type=float)
    parser.add_argument("--assignments-sha256")
    arguments = parser.parse_args()
    if arguments.serve:
        if not all((arguments.factory, arguments.port, arguments.ready, arguments.nonce,
                    arguments.deadline, arguments.assignments_sha256)):
            parser.error("Explicit parent-owned child arguments required")
        publish_worker_identity(arguments)
        try:
            serve(arguments)
        except BaseException as error:
            record_worker_error(arguments, error)
            raise
    else:
        raise SystemExit(main(arguments))
