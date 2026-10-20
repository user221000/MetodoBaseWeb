"""Restore36 fixture witnesses; no production sends, auth shortcut or old oracle edits."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import uuid

import pytest
from sqlalchemy import select,text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session,sessionmaker

from web.database.notification_schema_v1 import TABLES
from web.database.models import (Usuario,Cliente,Subscription,NotificationOutbox)
from web.database.tenant_context import tenant_scope
from web.notification_schemas import PreferenceWrite,QueueWrite,CancelWrite
from web.services import notifications as service,notification_worker as worker
from web.services.notification_domain import BillingSnapshot,SendResult


def historical33_tables(value):
    """Explicit structure projection only; full current36 is verified separately."""
    tables=deepcopy(value["tables"])
    for name in (*TABLES,"followup_tasks","followup_task_events"):tables.pop(name)
    users=tables["usuarios"]
    users["columns"]=[c for c in users["columns"] if c["name"]!="notification_contact_version"]
    users["checks"]=[c for c in users["checks"] if c["name"]!="ck_usuario_notification_contact_version"]
    clients=tables["clientes"]
    clients["columns"]=[c for c in clients["columns"] if c["name"]!="nutrition_restrictions_json"]
    clients["checks"]=[c for c in clients["checks"] if c["name"]!="ck_cliente_nutrition_declaration_bound"]
    return tables


def populate_notifications36(engine):
    """Trusted restore-only seed on an existing subject, no extra refresh/User rows.

    Independent HTTP cases prove primary/MFA acceptance. This fixture exercises
    real application transactions, synthetic typed source and memory send port.
    """
    from tests.test_nutrition35_profile_contract import declaration
    from web.services.nutrition_profiles import encode_declaration
    from web.services.provider_subjects import record_provider_subject
    from web.services.billing_integrity import price_in_cents
    from web.services.password_recovery import public_origin
    from web.settings import get_settings
    user="restore-release-gym";now=datetime.now(timezone.utc).replace(microsecond=0)-timedelta(days=2)
    start=now-timedelta(days=29);end=now+timedelta(days=29)
    with Session(engine) as db:
        assert db.scalar(select(Subscription).where(Subscription.gym_id==user)) is None
        source=Subscription(gym_id=user,plan="standard",provider="stripe",status="past_due",max_clientes=10,
            stripe_customer_id="cus_restore36",stripe_subscription_id="sub_restore36",
            current_period_start=start,current_period_end=end)
        db.add(source)
        record_provider_subject(db,"stripe","customer","cus_restore36",user,"synthetic-notification-restore")
        record_provider_subject(db,"stripe","subscription","sub_restore36",user,"synthetic-notification-restore")
        declared=encode_declaration(declaration(reported=True))
        db.scalar(select(Cliente).where(Cliente.gym_id==user,Cliente.id_cliente=="restore-release-client")).nutrition_restrictions_json=declared
        db.commit();sv=db.get(Usuario,user).session_version
    factory=sessionmaker(bind=engine,autoflush=False,expire_on_commit=True)
    expected={"id":user,"session_version":sv}
    pref=service.set_preference(expected,"gym","confirmed_payment_issue",PreferenceWrite(expected_version=0,
        enabled=True,confirm=True),str(uuid.uuid4()),factory=factory,now=now)["preference"]
    amount=price_in_cents("standard")
    class Source:
        enabled=True
        invoice="in_restore36_0"
        def read_billing(self,reference):
            return BillingSnapshot("stripe","subscription","sub_restore36",self.invoice,"past_due","open","mxn",
                amount,0,amount,False,False,start,end,now-timedelta(days=1))
    class Port:
        enabled=True
        result=SendResult("accepted","synthetic-restore36-ack")
        def __init__(self):self.calls=0
        def send(self,message):self.calls+=1;return self.result
    port=Port();source=Source();ids={}
    for index,state in enumerate(("accepted","uncertain","pending","suppressed")):
        at=now+timedelta(days=1 if index else 0,seconds=index)
        source.invoice="in_restore36_"+str(index)
        service.observe(expected,"gym",str(uuid.uuid4()),source,factory=factory,now=at)
        candidate=service.candidates(expected,"gym",factory=factory,now=at)["candidates"][1]
        row=service.queue(expected,"gym",QueueWrite(purpose=candidate["purpose"],preference_id=pref["id"],
            expected_preference_version=1,fact_id=candidate["fact_id"],source_hash=candidate["source_hash"],confirm=True),
            str(uuid.uuid4()),factory=factory,now=at)["outbox"]
        ids[state]=row["id"]
        if state in {"accepted","uncertain"}:
            port.result=SendResult("accepted","synthetic-restore36-ack") if state=="accepted" else SendResult("uncertain")
            result=worker.run_one(user,"gym",row["id"],public_origin(get_settings()),port,factory=factory,now=at)
            assert result["outbox"]["state"]==state
        elif state=="suppressed":
            service.cancel(expected,"gym",row["id"],CancelWrite(expected_version=1,confirm=True),
                str(uuid.uuid4()),factory=factory,now=at)
    assert port.calls==2
    return {"user":user,"foreign":"restore-foreign-gym","ids":ids,"declaration":declared,
        "preference_id":pref["id"],"counts":{"notification_preferences":1,"notification_billing_facts":4,
            "notification_outbox":4,"notification_attempts":5}}


def verify_restored_notifications36(admin,application,expected):
    """No successful mutation: full historical rows remain comparable afterwards."""
    from web.database.notification_policy import signature
    with application.connect() as db:
        assert db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user")).one()==(False,False,False,False)
        state=signature(db)
        assert len(state["functions"])==7 and all(not row[3] for row in state["functions"])
        assert len(state["triggers"])==10 and len(state["flags"])==4
        assert all(row[1] and row[2] for row in state["flags"])
        assert all(db.scalar(text("SELECT count(*) FROM "+name))==0 for name in TABLES)
    with tenant_scope(expected["user"]),Session(application) as db:
        for name,count in expected["counts"].items():assert db.scalar(text("SELECT count(*) FROM "+name))==count
        rows=db.scalars(select(NotificationOutbox).order_by(NotificationOutbox.id)).all()
        assert {row.state:row.id for row in rows}==expected["ids"]
        assert all(row.contact_version==0 for row in rows)
        assert all(row.exclude_hash is None or len(row.exclude_hash)==64 for row in rows)
        assert all(row.provider_id is None for row in rows if row.state!="accepted")
        assert db.scalar(select(Cliente).where(Cliente.gym_id==expected["user"],Cliente.id_cliente=="restore-release-client")).nutrition_restrictions_json==expected["declaration"]
        assert db.get(Usuario,expected["user"]).notification_contact_version==0
    for statement in ("UPDATE notification_preferences SET enabled=false","DELETE FROM notification_billing_facts",
                      "UPDATE notification_attempts SET reason='altered'","DELETE FROM notification_outbox"):
        with tenant_scope(expected["user"]),Session(application) as db:
            with pytest.raises(DBAPIError) as caught:db.execute(text(statement));db.commit()
            assert caught.value.orig.pgcode=="42501"
            db.rollback()
    with tenant_scope(expected["foreign"]),Session(application) as db:
        assert all(db.scalar(text("SELECT count(*) FROM "+name))==0 for name in TABLES)
    assert application.pool.checkedout()==0
    return {"counts":expected["counts"],"states":sorted(expected["ids"]),"role_flags_false":True,
        "forced_families":4,"invoker_functions":7,"triggers":10,"foreign_and_blank_empty":True,
        "declaration35_and_contact_epoch_preserved":True,"real_delivery":False}
