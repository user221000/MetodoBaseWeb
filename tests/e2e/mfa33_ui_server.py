"""Own loopback fixture; real password/MFA/auth/SQL, no external capability.

SQLite is migrated explicitly to31 in Temp. It does not prove PostgreSQL RLS.
The only provider seam is Stripe portal SDK, plus a no-send
email boundary. No helper endpoint exposes factors or authentication material.
"""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.isolation import block_external_sockets, prepare_environment


def main():
    for key in ("_METODOBASE_TEST_ROOT", "METODOBASE_TEST_DATABASE_URL", "METODOBASE_TEST_REDIS_URL",
                "PYTEST_XDIST_WORKER", "MFA_ENCRYPTION_KEY"):
        os.environ.pop(key, None)
    temporary = prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    port = 8802
    base = "http://127.0.0.1:" + str(port)
    # Check ownership before any app startup; never steal an existing listener.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    os.environ.update({"BASE_URL": base, "CORS_ORIGINS": base + ",http://testserver",
                       "MFA_ENCRYPTION_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode()})
    from sqlalchemy import inspect, text
    from sqlalchemy.orm import Session
    import stripe
    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import Base, Usuario, UserRole, Subscription
    from web.database.schema_control import expected_head, verify_runtime_schema
    from web.services import email_service, stripe_service

    engine = get_engine()
    if engine.dialect.name != "sqlite" or not Path(engine.url.database).resolve().is_relative_to(temporary):
        raise RuntimeError("MFA UI requires its own temporary SQLite")
    from db_bootstrap import main as bootstrap
    if bootstrap(["--revision", "20261019_google_subjects"]) != 0:
        raise RuntimeError("Own SQLite migration31 did not complete")
    verify_runtime_schema(engine, expected_revision="20261019_google_subjects")
    with engine.connect() as connection:
        actual_revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        physical_tables = len(inspect(connection).get_table_names())
    password = "Synthetic-MFA-UI-Password-2026!"
    hashed = hash_password(password)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        for name in ("owner", "other"):
            identifier = "synthetic-mfa-ui-" + name
            db.add(Usuario(id=identifier, email="mfa-ui-" + name + "@example.invalid", nombre="Synthetic " + name,
                           apellido="", password_hash=hashed, tipo="gym", role=UserRole.OWNER,
                           activo=True, session_version=0, fecha_registro=now))
        db.flush()
        db.add(Subscription(gym_id="synthetic-mfa-ui-owner", plan="clinica", status="active", provider="stripe",
                            stripe_customer_id="cus_synthetic_mfa_ui", current_period_end=now + timedelta(days=30)))
        db.commit()
    email_service._send = lambda *_args, **_kwargs: False
    stripe_service._init_stripe = lambda: True
    stripe.billing_portal.Session.create = lambda **_kwargs: SimpleNamespace(url="https://billing.stripe.com/synthetic-no-provider")
    root = Path(__file__).resolve().parents[2]
    runtime = {}
    for directory in ("web", "api", "core", "config"):
        for source in (root / directory).rglob("*"):
            if source.is_file() and source.suffix in {".py", ".js", ".html", ".css", ".json"}:
                runtime[str(source.relative_to(root)).replace("\\", "/")] = hashlib.sha256(source.read_bytes()).hexdigest()
    from web.database.alembic.schema_contract_v1 import schema_signature
    from web.database.google_identity_policy import signature as google_signature
    with engine.connect() as connection:
        assert connection.exec_driver_sql('PRAGMA foreign_key_check').all()==[]
        sqlite_witness={'database_kind':'sqlite','runtime_revision':actual_revision,
            'model_tables':len(Base.metadata.tables),'actual_tables':physical_tables,'foreign_keys_clean':True,
            'schema_sha256':hashlib.sha256(json.dumps(schema_signature(connection),sort_keys=True,default=list).encode()).hexdigest(),
            'google_identity_signature_sha256':hashlib.sha256(json.dumps(google_signature(connection),sort_keys=True,default=list).encode()).hexdigest()}
    startup = {"sqlite_witness":sqlite_witness,"fixture": "mfa-ui33", "origin": base, "pid": os.getpid(), "temporary_root": str(temporary),
               "expected_runtime_revision": expected_head(), "actual_alembic_revision": actual_revision,
               "metadata_table_count": len(Base.metadata.tables), "physical_table_count": physical_tables,
               "schema_preparation": "db_bootstrap.main --revision20261019_google_subjects; real upgrade and runtime signature/index verification",
               "config_classification": {"signing": "testing-only", "mfa_key": "random ephemeral never reported",
                                         "providers": "off except synthetic Stripe SDK boundary; no network"},
               "runtime_raw_sha256": runtime,
               "python_packages": sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions() if d.metadata["Name"])}
    # Startup JSON contains no pair, code, seed, proof, grant or provider key.
    print(json.dumps(startup), flush=True)
    import uvicorn
    from web.main_web import create_app
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
