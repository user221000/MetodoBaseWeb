"""Configure synthetic test data before importing application modules.

The ordinary suite uses SQLite files below a fresh temporary directory. A
PostgreSQL URL must be explicitly supplied as METODOBASE_TEST_DATABASE_URL;
only loopback hosts and dedicated test database/user names are accepted.
External providers stay disabled and outbound sockets fail before connecting.
This is an in-process guard, not an operating-system network sandbox.
"""
from __future__ import annotations

import os
from pathlib import Path
import socket
import tempfile
from urllib.parse import unquote, urlsplit

_LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def validate_postgres_test_url(url: str) -> str:
    """Reject remote/non-test destinations without exposing URL credentials."""
    parsed = urlsplit(url)
    if (parsed.scheme not in {"postgresql", "postgresql+psycopg2", "postgres"}
            or parsed.hostname not in _LOOPBACK
            or not unquote(parsed.path.lstrip("/")).startswith("metodobase_test")
            or not unquote(parsed.username or "").startswith("metodobase_test")):
        raise ValueError("PostgreSQL tests require loopback and dedicated metodobase_test database/user")
    if parsed.query or parsed.fragment:
        raise ValueError("PostgreSQL test URL cannot contain connection overrides")
    return url


def validate_redis_test_url(url: str) -> str:
    """Allow only the explicit dedicated Redis integration endpoint.

    Ordinary REDIS_URL is always cleared. Query parameters can override the
    parsed database/connection options in redis-py, so none are accepted.
    """
    message = "Redis tests require redis loopback port 56379 database 15 without overrides"
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == "redis" and parsed.hostname in _LOOPBACK
                 and parsed.port == 56379 and parsed.path == "/15"
                 and not parsed.query and not parsed.fragment)
    except ValueError:
        raise ValueError(message) from None
    if not valid:
        raise ValueError(message)
    return url


def prepare_environment(*, discard_inherited: bool = False) -> Path:
    """Install configuration before app imports; return this worker's root.

    The launcher discards inherited production configuration. Direct pytest
    rejects an inherited DATABASE_URL. xdist workers receive separate files.
    """
    run_root = os.environ.get("_METODOBASE_TEST_ROOT")
    if not run_root:
        if os.environ.get("DATABASE_URL") and not discard_inherited:
            raise ValueError("Inherited DATABASE_URL rejected; run python -X utf8 tests/run_isolated.py")
        run_root = tempfile.mkdtemp(prefix="metodobase-test-")
        os.environ["_METODOBASE_TEST_ROOT"] = run_root
    root = Path(run_root).resolve()
    if not root.is_relative_to(Path(tempfile.gettempdir()).resolve()) or not root.name.startswith("metodobase-test-"):
        raise ValueError("Test data root must be a dedicated temporary directory")
    worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
    if worker != "main" and (not worker.startswith("gw") or not worker[2:].isdigit()):
        raise ValueError("Invalid test worker identifier")
    worker_root = root / worker
    for dirname in ("home", "appdata", "localappdata", "config", "registros", "output", "planes"):
        (worker_root / dirname).mkdir(parents=True, exist_ok=True)
    postgres_url = os.environ.get("METODOBASE_TEST_DATABASE_URL", "")
    redis_url = os.environ.get("METODOBASE_TEST_REDIS_URL", "")
    if redis_url:
        validate_redis_test_url(redis_url)
    if postgres_url:
        validate_postgres_test_url(postgres_url)
        if worker != "main":
            raise ValueError("PostgreSQL tests require a dedicated database per worker; run serially")
    for key in list(os.environ):
        normalized = key.upper()
        if (normalized.startswith("PG") or normalized.endswith("_DATABASE_URL")
                or normalized == "BACKUP_ENCRYPTION_KEY"
                or normalized.startswith(("AWS_", "S3_", "OBJECT_STORAGE_"))
                or any(part in normalized for part in ("STRIPE", "MERCADOPAGO", "RESEND", "SMTP", "SENTRY", "RAILWAY", "REDIS", "GOOGLE_CLIENT", "OPENAI_API"))):
            os.environ[key] = ""
    os.environ.update({
        "PYTHON_DOTENV_DISABLED": "1", "METODOBASE_ENV": "testing",
        "METODOBASE_DATA_DIR": str(worker_root), "METODOBASE_TEST_CONFIG": str(worker_root / "config"),
        "APPDATA": str(worker_root / "appdata"), "LOCALAPPDATA": str(worker_root / "localappdata"),
        "USERPROFILE": str(worker_root / "home"), "XDG_DATA_HOME": str(worker_root / "home"),
        "DATABASE_URL": postgres_url or "sqlite:///" + (worker_root / "suite.db").as_posix(),
        "METODOBASE_TEST_DATABASE_URL": postgres_url,
        "METODOBASE_TEST_REDIS_URL": redis_url,
        "DB_PATH": str(worker_root / "legacy.db"),
        "OBJECT_STORAGE_BACKEND": "local",
        "OBJECT_STORAGE_LOCAL_ROOT": str(worker_root / "private_objects"),
        "AWS_EC2_METADATA_DISABLED": "true",
        "WEB_SECRET_KEY": "local-tests-only-signing-key-at-least-thirty-two-characters",
        "METODO_BASE_SALT": "local-tests-only-salt", "METODO_BASE_MASTER_KEY": "",
        "BASE_URL": "http://127.0.0.1:8765", "CORS_ORIGINS": "http://127.0.0.1:8765,http://testserver",
        "RATE_LIMIT_ENABLED": "false", "METRICS_ENABLED": "false", "ALERT_ENABLED": "false",
        "QT_QPA_PLATFORM": "offscreen", "METODOBASE_SEED_DEMO": "0",
        "SENTRY_DSN": "", "RESEND_API_KEY": "", "REDIS_URL": "", "GOOGLE_CLIENT_ID": "",
        "STRIPE_SECRET_KEY": "", "STRIPE_WEBHOOK_SECRET": "", "STRIPE_PUBLISHABLE_KEY": "",
        "MERCADOPAGO_ACCESS_TOKEN": "", "MERCADOPAGO_WEBHOOK_SECRET": "",
        "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1",
    })
    return worker_root


def block_external_sockets() -> None:
    """Block TCP connections outside loopback, including connect_ex callers."""
    if getattr(socket.socket.connect, "_metodobase_guard", False):
        return
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def check(address):
        if isinstance(address, tuple) and address[0] not in _LOOPBACK:
            raise RuntimeError("Test isolation blocked an external network destination")

    def connect(sock, address):
        check(address)
        return original_connect(sock, address)

    def connect_ex(sock, address):
        check(address)
        return original_connect_ex(sock, address)

    connect._metodobase_guard = True
    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
