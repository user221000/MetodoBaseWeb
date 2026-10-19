"""Revision32 synthetic ownership leases, no force-drop or shared-schema writes."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine

PREVIOUS = "20261019_mfa"
REVISION = "20261019_personal_progress"


@contextmanager
def owned_database(dialect, directory):
    """Plan before CREATE; attribute exact UUID/OID, close pools, no-force DROP.

    Unclosed sessions or attribution mismatch retain the DB and fail visibly.
    No HBA/global role change, no kill/terminate, no inference from name alone.
    """
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if dialect=="sqlite":
        url="sqlite:///"+(directory/(uuid.uuid4().hex+".db")).as_posix()
        engine=create_engine(url,connect_args={"check_same_thread":False})
        try:yield url,engine
        finally:engine.dispose()
        return
    import psycopg2
    from psycopg2 import sql
    from tests.isolation import validate_postgres_test_url
    source=validate_postgres_test_url(os.environ["METODOBASE_TEST_MIGRATOR_URL"])
    parsed=urlsplit(source);plan_id=uuid.uuid4().hex;name="metodobase_test_progress_"+plan_id
    receipt={"plan_id":plan_id,"database":name,"launcher_pid":os.getpid(),"planned_at":datetime.now(timezone.utc).isoformat(),"state":"planned"}
    receipts=Path(os.environ.get("R25_EVIDENCE_DIR",str(directory)))
    receipts.mkdir(parents=True,exist_ok=True);path=receipts/("lease-"+plan_id+".json")
    def save():path.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    save();control=psycopg2.connect(source.replace("postgresql+psycopg2://","postgresql://",1));control.autocommit=True
    engine=None;created=False
    try:
        with control.cursor() as db:
            db.execute("SELECT pg_backend_pid(),current_user");pid,owner=db.fetchone()
            receipt.update(control_backend_pid=pid,expected_owner=owner);save()
            db.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
            created=True
            db.execute("SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s",(name,));oid,actual_owner=db.fetchone()
            assert actual_owner==owner
            receipt.update(oid=oid,state="created",created_at=datetime.now(timezone.utc).isoformat());save()
        url=urlunsplit(parsed._replace(path="/"+name));engine=create_engine(url,pool_size=1,max_overflow=0)
        yield url,engine
    finally:
        if engine is not None:engine.dispose()
        try:
            if created:
                with control.cursor() as db:
                    db.execute("SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s",(name,));row=db.fetchone()
                    assert row==(receipt["oid"],receipt["expected_owner"]),"Owned database identity changed; retained"
                    db.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=%s",(name,));sessions=db.fetchone()[0]
                    receipt["sessions_before_drop"]=sessions;save()
                    assert sessions==0,"Owned sessions remain; no force-drop permitted"
                    db.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
                # Fresh control connection independently verifies absence.
                with psycopg2.connect(source.replace("postgresql+psycopg2://","postgresql://",1)) as fresh, fresh.cursor() as db:
                    db.execute("SELECT count(*) FROM pg_database WHERE datname=%s",(name,));assert db.fetchone()[0]==0
                receipt.update(state="closed_absent",closed_at=datetime.now(timezone.utc).isoformat());save()
        finally:control.close()


def signature(connection):
    from web.database.alembic.schema_contract_v1 import schema_signature
    from web.database.alembic.security_contract_v1 import tenant_security_signature
    from web.database.alembic.member_link_security_v1 import member_link_security_signature
    from web.database.alembic.history_index_contract_v1 import history_index_signature
    from web.database.progress_policy import signature as progress_signature
    return {"signature":schema_signature(connection),"tenant_security":tenant_security_signature(connection),
        "member_link_security":member_link_security_signature(connection),"history_order_index":history_index_signature(connection),
        "progress_security":progress_signature(connection)}
