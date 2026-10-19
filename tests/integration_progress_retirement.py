"""One owned32 UUID, restricted app pool1, real HTTP and independent locks."""
# ruff: noqa: F811 -- pytest fixture parameters intentionally use fixture names
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from tests.integration_provider_subjects import application_engine
from tests.integration_schema_migrations import run_migration
from tests.retirement32_owned import owned_database
from tests.test_progress_retirement_http import (  # noqa:F401
    METADATA,
    WITHDRAW,
    enrollment,
    progress_http,
    query,
    retired_scope,
    snapshot,
    test_commit_ack_loss_does_not_return_success_or_refund_factor,
    withdrawal,
)


@pytest.fixture(scope="module")
def progress_db(tmp_path_factory):
    if not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.skip("Explicit owned PostgreSQL profile required")
    with owned_database("postgresql", tmp_path_factory.mktemp("retirement-pg32")) as (url, admin):
        run_migration(url, "db_bootstrap.py", "--revision", "20261019_personal_progress")
        app = application_engine(url, admin)
        try:
            with app.connect() as db:
                assert tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user")).one()) == (False, False, False, False)
                assert db.scalar(text("SELECT pg_get_userbyid(datdba)<>current_user FROM pg_database WHERE datname=current_database()"))
                assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relname IN ('mfa_credentials','mfa_recovery_codes','progress_consents') AND relrowsecurity AND relforcerowsecurity")) == 3
            yield admin, app
        finally:
            app.dispose()


def blank(app):
    assert app.pool.checkedout() == 0
    with app.connect() as db:
        assert tuple(db.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true)")).one()) == ("", "", "")
        assert db.scalar(text("SELECT count(*) FROM progress_consents")) == 0


def test_real_http_pool1_two_subjects_and_factor_context_reuse(retired_scope):
    c = retired_scope; _, codes = enrollment(c)
    before = snapshot(c)
    result = c["client_http"].post(METADATA, json=query(c, factor={"recovery_code": codes[0]}))
    assert result.status_code == 200 and result.json()["items"][0]["link_id"] == c["link"]
    blank(c["engine"])
    other = {"method": "password", "email": c["emails"]["other"], "password": "Synthetic progress password 42!"}
    empty = c["client_http"].post(METADATA, json={"primary": other})
    assert empty.status_code == 200 and empty.json()["items"] == []
    assert c["client_http"].post(WITHDRAW, json=withdrawal(c, primary=other)).status_code == 404
    blank(c["engine"])
    assert c["client_http"].post(WITHDRAW, json=withdrawal(c, factor={"recovery_code": codes[1]})).status_code == 200
    after = snapshot(c)
    assert {k: v for k, v in before.items() if k != "events"} == {k: v for k, v in after.items() if k != "events"}
    blank(c["engine"])


def test_account_lock_prevents_parallel_factor_replay_and_state_changes(retired_scope):
    from fastapi import HTTPException

    from web.database.models import Usuario
    from web.database.tenant_context import configure_tenant_engine
    from web.progress_retirement_schemas import Metadata
    from web.services import progress_retirement as service
    c = retired_scope; _, codes = enrollment(c)
    entered, release = Event(), Event()
    def hold(connection, cursor, statement, parameters, context, many):
        if "max(progress_consents.version)" in statement:
            entered.set()
            assert release.wait(12)
    secondary = configure_tenant_engine(create_engine(c["engine"].url, pool_size=1, max_overflow=0))
    event.listen(c["engine"], "before_cursor_execute", hold)
    try:
        with ThreadPoolExecutor(max_workers=1) as workers:
            future = workers.submit(c["client_http"].post, METADATA,
                json=query(c, factor={"recovery_code": codes[0]}))
            assert entered.wait(12)
            with Session(c["admin"]) as db, pytest.raises(DBAPIError) as busy:
                db.scalar(select(Usuario).where(Usuario.id == c["person"]).with_for_update(nowait=True))
            assert getattr(busy.value.orig, "pgcode", None) == "55P03"
            with Session(secondary) as db, pytest.raises(HTTPException) as parallel:
                service.perform(db, Metadata.model_validate(query(c, factor={"recovery_code": codes[0]})), operation="metadata")
            assert parallel.value.status_code == 409 and parallel.value.detail["code"] == "progress_retirement_busy"
            release.set()
            assert future.result(timeout=15).status_code == 200
    finally:
        release.set()
        event.remove(c["engine"], "before_cursor_execute", hold)
        secondary.dispose()
    assert c["client_http"].post(METADATA, json=query(c, factor={"recovery_code": codes[0]})).status_code == 401
    blank(c["engine"])


@pytest.mark.parametrize("change", ["sv", "active"])
def test_revalidation_after_durable_admission_never_uses_stale_primary_context(retired_scope, monkeypatch, change):
    from web.database import engine as database
    from web.database.models import Usuario
    c = retired_scope
    class Changing(Session):
        def commit(self):
            admission = any(getattr(row, "event_type", None) == "progress_retirement_attempt" for row in self.new)
            super().commit()
            if admission:
                with Session(c["admin"]) as update:
                    actor = update.get(Usuario, c["person"])
                    if change == "sv": actor.session_version += 1
                    else: actor.activo = False
                    update.commit()
    monkeypatch.setattr(database, "_SessionLocal", sessionmaker(bind=c["engine"], class_=Changing, expire_on_commit=True))
    result = c["client_http"].post(WITHDRAW, json=withdrawal(c))
    assert result.status_code == 401 and result.json()["detail"]["code"] == "progress_retirement_verification_failed"
    assert [r[1] for r in snapshot(c)["events"]] == ["grant"]
    blank(c["engine"])


def test_aborted_sql_restores_pool_and_factor_but_admission_is_durable(retired_scope):
    from web.database.models import MfaRecoveryCode
    from web.services.mfa_crypto import opaque_digest
    c = retired_scope; _, codes = enrollment(c)
    def aborted(connection, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO progress_consents"):
            cursor.execute("SELECT 1/0")
    event.listen(c["engine"], "before_cursor_execute", aborted)
    try:
        failed = c["client_http"].post(WITHDRAW, json=withdrawal(c, factor={"recovery_code": codes[0]}))
    finally:
        event.remove(c["engine"], "before_cursor_execute", aborted)
    assert failed.status_code == 503 and failed.json()["detail"]["code"] == "progress_retirement_unconfirmed"
    assert [r[1] for r in snapshot(c)["events"]] == ["grant"]
    with Session(c["admin"]) as db:
        assert db.scalar(select(MfaRecoveryCode.used_at).where(MfaRecoveryCode.code_hash == opaque_digest("recovery", codes[0]))) is None
        assert db.scalar(text("SELECT count(*) FROM auth_audit_log WHERE user_id=:id AND event_type='progress_retirement_attempt'"), {"id": c["person"]}) == 1
    blank(c["engine"])
    assert c["client_http"].post(WITHDRAW, json=withdrawal(c, factor={"recovery_code": codes[0]})).status_code == 200
    blank(c["engine"])


def test_pool1_exhaustion_fails_closed_without_consuming_factor_or_erasing_budget(retired_scope, monkeypatch):
    c = retired_scope; _, codes = enrollment(c)
    assert c["client_http"].post(METADATA, json=query(c, factor={"recovery_code": codes[0]})).status_code == 200
    monkeypatch.setattr(c["engine"].pool, "_timeout", 0.05)
    with c["engine"].connect():
        failed = c["client_http"].post(METADATA, json=query(c, factor={"recovery_code": codes[1]}))
    assert failed.status_code == 503 and "items" not in failed.json()
    blank(c["engine"])
    assert c["client_http"].post(METADATA, json=query(c, factor={"recovery_code": codes[1]})).status_code == 200
    with Session(c["admin"]) as db:
        assert db.scalar(text("SELECT count(*) FROM auth_audit_log WHERE user_id=:id AND event_type='progress_retirement_attempt'"), {"id": c["person"]}) == 2
    blank(c["engine"])


def test_incidental_bearer_context_is_ignored_on_new_session_and_pool_is_clean(retired_scope):
    from tests.test_progress_retirement_context import (
        test_incidental_other_bearer_does_not_select_or_block_primary_subject,
    )
    test_incidental_other_bearer_does_not_select_or_block_primary_subject(retired_scope)
    blank(retired_scope["engine"])
