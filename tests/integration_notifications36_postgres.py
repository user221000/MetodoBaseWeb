"""Current36 real HTTP, restricted FORCE role and pool1 transaction boundaries."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import select,func,text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session,sessionmaker

from tests.notifications36_fixtures import owned_database,REVISION
from tests.followup34_http import followup_http
from tests.integration_schema_migrations import run_migration
from tests.integration_provider_subjects import application_engine
from tests.test_notifications36_http import (
    test_verified_provider_observation_durable_queue_and_explicit_optout as current_queue,
    test_paid_cancelled_refunded_and_missing_due_are_not_arrears as current_unknown,
)
from tests.test_notifications36_worker import prepared,origin,Port
from tests.test_notifications36_exclusion_scope import (
    test_foreign_real_login_does_not_select_or_disable_its_own_preference as foreign_bearer,
    test_contact_roundtrip_permanently_invalidates_old_exclusion as contact_roundtrip,
)
from tests.test_notifications36_fact_metrics import (
    test_conflicting_provider_period_supersedes_previous_fact_with_unknown as fact_conflict,
    test_renewal_counts_distinct_verified_paid_periods_and_refund_correction as fact_metrics,
    test_failed_reobservation_does_not_keep_previous_fresh_source_eligible as observation_failure,
)
from web.database.models import Usuario,NotificationPreference,NotificationOutbox
from web.database.tenant_context import tenant_scope
from web.database.notification_policy import signature
from web.services import notifications as service,notification_worker as worker
from web.services.notification_domain import secret_hash,SendResult


@pytest.fixture(scope="module")
def followup_db(tmp_path_factory):
    with owned_database("postgresql",tmp_path_factory.mktemp("notification36-pg")) as (url,admin):
        run_migration(url,"db_bootstrap.py","--revision",REVISION)
        application=application_engine(url,admin)
        try:yield admin,application
        finally:application.dispose()


notification_http=followup_http


@pytest.mark.parametrize("scenario",[current_queue,current_unknown,foreign_bearer,contact_roundtrip],ids=["queue-optout","typed-unknown","foreign-bearer","contact-roundtrip"])
def test_current_http_criteria_under_restricted_role(notification_http,monkeypatch,scenario):
    scenario(notification_http,monkeypatch)
    assert notification_http["engine"].pool.checkedout()==0


@pytest.mark.parametrize("scenario",[fact_conflict,fact_metrics,current_queue,current_unknown,observation_failure],ids=["fact-coherence","paid-metrics","observation-queue","observation-unknown","observation-failed"])
def test_fact_and_observation_delta_under_restricted_role(notification_http,monkeypatch,scenario):
    scenario(notification_http,monkeypatch)
    assert notification_http["engine"].pool.checkedout()==0


def test_real_role_four_flags_force_and_unknown_tenant_are_closed(followup_db):
    admin,application=followup_db
    with application.connect() as c:
        assert c.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user")).one()==(False,False,False,False)
        assert c.scalar(text("SELECT count(*) FROM pg_tables t JOIN pg_class c ON c.oid=(quote_ident(t.schemaname)||'.'||quote_ident(t.tablename))::regclass WHERE t.schemaname='public' AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)"))==0
        security=signature(c)
        assert len(security["flags"])==4 and all(row[1] and row[2] for row in security["flags"])
        assert c.scalar(select(func.count()).select_from(NotificationPreference))==0
        assert c.scalar(select(func.count()).select_from(NotificationOutbox))==0
        assert c.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))==32
    assert application.pool.checkedout()==0


def test_history_dml_is_denied_without_widening_any_owner(notification_http,monkeypatch):
    c=notification_http;identifier=prepared(c,monkeypatch)
    for sql in ("UPDATE notification_preferences SET enabled=false", "DELETE FROM notification_preferences", "DELETE FROM notification_outbox"):
        with tenant_scope(c["user"]),Session(c["engine"]) as db:
            with pytest.raises(DBAPIError) as caught:db.execute(text(sql));db.commit()
            assert caught.value.orig.pgcode=="42501"
            db.rollback()
    with tenant_scope(c["member"]),Session(c["engine"]) as db:
        assert db.get(NotificationOutbox,identifier) is None
    assert c["engine"].pool.checkedout()==0


def test_capability_session_value_never_survives_commit_rollback_or_pool_reuse(notification_http,monkeypatch):
    from urllib.parse import urlsplit,parse_qs
    c=notification_http;identifier=prepared(c,monkeypatch);port=Port()
    worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"])
    token=parse_qs(urlsplit(port.messages[0].exclusion_url).fragment)["token"][0]
    digest=secret_hash("notification_exclude36:v1",token)
    for finish in ("commit","rollback"):
        with c["engine"].connect() as db:
            db.execute(text("SELECT set_config('app.notification_exclude_digest',:digest,false)"),{"digest":digest})
            assert db.scalar(select(func.count()).select_from(NotificationOutbox))==1
            getattr(db,finish)()
        with c["engine"].connect() as db:
            assert db.scalar(text("SELECT current_setting('app.notification_exclude_digest',true)"))==""
            assert db.scalar(select(func.count()).select_from(NotificationOutbox))==0
    assert c["engine"].pool.checkedout()==0


def test_parallel_claims_are_fenced_on_a_single_connection_pool(notification_http,monkeypatch):
    c=notification_http;identifier=prepared(c,monkeypatch)
    def claim():
        try:return worker.claim(c["user"],"gym",identifier,factory=c["factory"])
        except HTTPException as error:return error.status_code
    with ThreadPoolExecutor(max_workers=2) as threads:replies=list(threads.map(lambda _:claim(),range(2)))
    assert sum(isinstance(row,worker.Claim) for row in replies)==1 and replies.count(409)==1
    assert c["engine"].pool.checkedout()==0


def test_ack_lost_after_real_sending_commit_never_exposes_message_or_sends(notification_http,monkeypatch):
    c=notification_http;identifier=prepared(c,monkeypatch);now=datetime.now(timezone.utc)
    claimed=worker.claim(c["user"],"gym",identifier,factory=c["factory"],now=now)
    class LostAck(Session):
        def commit(self):super().commit();raise RuntimeError("Synthetic sending commit ACK lost")
    factory=sessionmaker(bind=c["engine"],class_=LostAck,expire_on_commit=True,autoflush=False)
    with pytest.raises(HTTPException) as caught:worker.prepare_handoff(claimed,origin(),factory=factory,now=now)
    assert caught.value.status_code==503
    with Session(c["admin"]) as db:
        assert db.get(NotificationOutbox,identifier).state=="sending"
    recovered=worker.recover_expired_sending(c["user"],"gym",identifier,factory=c["factory"],now=now+timedelta(seconds=61))
    assert recovered["outbox"]["state"]=="uncertain"
    with pytest.raises(HTTPException):worker.finish(claimed,SendResult("accepted","late-ack"),factory=c["factory"],now=now+timedelta(seconds=61))
    assert c["engine"].pool.checkedout()==0


def test_write_under_repeatable_read_is_rejected_but_plain_read_is_allowed(notification_http):
    from web.notification_schemas import PreferenceWrite
    c=notification_http
    with Session(c["admin"]) as db:sv=db.get(Usuario,c["user"]).session_version
    expected={"id":c["user"],"session_version":sv}
    connection=c["engine"].execution_options(isolation_level="REPEATABLE READ")
    factory=sessionmaker(bind=connection,expire_on_commit=True,autoflush=False)
    with pytest.raises(HTTPException) as caught:
        service.set_preference(expected,"gym","account_period_end",PreferenceWrite(expected_version=0,enabled=True,confirm=True),str(uuid.uuid4()),factory=factory)
    assert caught.value.status_code==503
    assert service.preferences(expected,"gym",factory=factory)["items"][0]["version"]==0
    assert c["engine"].pool.checkedout()==0
