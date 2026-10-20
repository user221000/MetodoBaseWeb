"""Original SEC19 assertions, explicitly composed with current35 restricted PG."""
import json
import pytest
from sqlalchemy import inspect,text
from tests.integration_nutrition35_postgres import followup_db,followup_http,blank_pool
from tests.test_followup34_lock_projection import test_moved_assignee_lock_never_fetches_other_context_contact_fields
from web.database.schema_control import verify_runtime_schema

@pytest.fixture(autouse=True)
def exact35_restricted_pool_witness(followup_http,record_property):
    case=followup_http;engine=case['engine']
    assert engine.dialect.name=='postgresql'
    assert engine.pool.size()==1 and engine.pool._max_overflow==0
    with engine.connect() as db:
        flags=tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER') FROM pg_roles WHERE rolname=current_user")).one())
        assert flags==(False,False,False,False,False)
        forced=db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))
        tables=len(inspect(db).get_table_names())
        head=db.scalar(text('SELECT version_num FROM alembic_version'))
        assert forced==28 and tables==38 and head=='20261020_nutrition_profile'
    # This check gets its own checkout; never nest it inside a pool1 connection.
    verify_runtime_schema(engine)
    record_property('PG35_restricted_witness',json.dumps({'dialect':'postgresql','flags4_and_membership':[False]*5,'FORCE_RLS_tables':forced,'physical_tables':tables,'head':head,'pool_size':1,'max_overflow':0,'factory':case['factory_name']}))
    yield
    blank_pool(engine)
