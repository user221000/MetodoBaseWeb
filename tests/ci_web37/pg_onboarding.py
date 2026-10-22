"""R22 assertions unchanged; admin setup and restricted real HTTP are explicit."""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from tests.ci_web37.composition import fixture_function

ROOT = Path(__file__).resolve().parents[2]
PINS = {
    "tests/test_onboarding22_facts.py": "8261e5e6eb54dba97926cc090455eec458d77bfdfc84bb11264970cfd1e04100",
    "tests/test_security_onboarding22_peer.py": "5f6ef7dfbe19927602906582d01e82364e524171871843e98b1b80d87f113a61",
}
CASE = ContextVar("ci_web37_R22_direct_port_case", default=None)
OLD_IMPORT = "from web.database.engine import SessionLocal"
NEW_IMPORT = "from tests.ci_web37.pg_onboarding import direct_readonly_session as SessionLocal"


@pytest.fixture
def onboarding_owner(followup_db, isolated_database, monkeypatch):
    import conftest
    from web.database import engine as database

    admin, application = followup_db
    # Reuse the original persisted owner/password/token fixture. Only its
    # synthetic setup connection is administrative, never any HTTP dependency.
    with monkeypatch.context() as setup:
        setup.setattr(database, "_engine", admin)
        setup.setattr(database, "_SessionLocal", sessionmaker(bind=admin, expire_on_commit=True, autoflush=False))
        actor = fixture_function(conftest.test_gym_user)()
    with monkeypatch.context() as runtime:
        runtime.setattr(database, "_engine", application)
        runtime.setattr(database, "_SessionLocal", sessionmaker(bind=application, expire_on_commit=True, autoflush=False))
        token = CASE.set((admin, application, actor))
        try:
            yield actor
        finally:
            CASE.reset(token)


def setup_session(bind, *args, **kwargs):
    case = CASE.get()
    if case is None or bind is not case[1]:
        raise ValueError("R22 setup must name the actual restricted application engine")
    # This affects only the cloned test namespace's setup/retirement statements.
    # Application sessionmaker and real HTTP dependency code remain untouched.
    return Session(case[0], *args, **kwargs)


@contextmanager
def direct_readonly_session():
    from web.auth import verificar_token
    from web.database.tenant_context import bind_verified_subject

    case = CASE.get()
    if case is None:
        raise ValueError("The direct R22 port requires its own persisted actor fixture")
    verified = verificar_token(case[2]["access_token"])
    assert verified and verified["id"] == case[2]["id"]
    with Session(case[1]) as db:
        # Actual signature/current persisted identity verification precedes
        # this direct repository port. Its binding is before the SQL observer.
        bind_verified_subject(db, verified["id"])
        yield db


def export(name, module):
    from tests.ci_web37.fixtures import current37_witness, followup_db

    raw = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != PINS[name]:
        raise ValueError("Original R22 assertion source differs")
    source = raw.decode("utf8")
    if name.endswith("test_security_onboarding22_peer.py"):
        if source.count(OLD_IMPORT) != 1 or NEW_IMPORT in source:
            raise ValueError("The one direct R22 repository port import differs")
        source = source.replace(OLD_IMPORT, NEW_IMPORT)
        if source.replace(NEW_IMPORT, OLD_IMPORT).encode() != raw:
            raise ValueError("The direct repository port transport cannot invert exactly")
    namespace = {"__file__": str(ROOT / name), "__name__": module}
    exec(compile(source, str(ROOT / name), "exec"), namespace)  # noqa: S102
    namespace.update(Session=setup_session, followup_db=followup_db,
                     current37_witness=current37_witness, test_gym_user=onboarding_owner)
    return {key: value for key, value in namespace.items() if not key.startswith("__")}
