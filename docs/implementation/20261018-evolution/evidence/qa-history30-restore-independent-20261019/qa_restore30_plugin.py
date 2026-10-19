"""Additive checks after actual restore, on the same two UUIDs; maintained test unchanged."""
import hashlib,importlib,json,os
from pathlib import Path

NODE='test_revision30_restore_preserves_history_index_and_all_revision26_27_28_29_contracts'
def pytest_runtest_setup(item):
    if item.name!=NODE:return
    from scripts import backup_restore
    original=backup_restore.restore_backup
    def checked(*args,**kwargs):
        result=original(*args,**kwargs)
        inspect_actual_restored_database(kwargs['database_url'])
        return result
    backup_restore.restore_backup=checked

def inspect_actual_restored_database(url):
    import pytest
    from sqlalchemy import MetaData,create_engine,event,func,select,text
    from sqlalchemy.orm import Session,sessionmaker
    from tests.integration_provider_subjects import application_engine
    from web.database import engine as database
    from web.database.alembic.schema_contract_v1 import schema_signature
    from web.database.alembic.security_contract_v1 import tenant_security_signature
    from web.database.alembic.member_link_security_v1 import member_link_security_signature
    from web.database.alembic.history_index_contract_v1 import INDEX_NAME,create_history_index,expected_history_index,history_index_signature
    from web.database.models import ClientAccountLink,ClientLinkInvitation,ClientPlanPublication
    from web.database.schema_control import verify_runtime_schema
    out=Path(os.environ['METODOBASE_TEST_EVIDENCE_DIR']);rows=[];admin=create_engine(url);app=None
    def snapshot():
        metadata=MetaData();metadata.reflect(bind=admin)
        with admin.connect() as connection:return {table.name:[dict(row) for row in connection.execute(select(table).order_by(*table.primary_key.columns)).mappings()] for table in metadata.sorted_tables}
    digest=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()
    def write():
        (out/'qa-restored-negative-controls.json').write_text(json.dumps({'scope':'Additive actual restored30 controls on the existing owned target, before maintained author assertions continue. No source/test edits, new DB or provider calls.','results':rows,'passed':sum(row['passed'] for row in rows),'total':len(rows)},indent=2)+'\n',encoding='utf8')
    def passed(case,**safe):rows.append({'case':case,'passed':True,**safe});write()
    try:
        verify_runtime_schema(admin)
        with admin.connect() as connection:
            canonical=history_index_signature(connection);structural=schema_signature(connection);security=tenant_security_signature(connection);members=member_link_security_signature(connection)
        assert canonical==expected_history_index('postgresql')
        baseline=snapshot();baseline_hash=digest(baseline)
        assert len(baseline['refresh_tokens'])==8
        with pytest.raises(RuntimeError,match='revision'):verify_runtime_schema(admin,expected_revision='20261019_client_account_links')
        passed('actual-restored30-default-accepts-explicit-historical29-rejects-before-mutation',rows_sha256=baseline_hash,physical_refresh_tokens=8)
        app=application_engine(url,admin)
        with app.connect() as connection:
            flags=tuple(connection.exec_driver_sql('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user').one())
            assert flags==(False,False,False,False)
            assert connection.exec_driver_sql("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)").scalar_one()==0
            assert connection.exec_driver_sql("SELECT current_setting('app.current_tenant',true)").scalar_one()==''
        with Session(app) as session:
            assert all(session.scalar(select(func.count()).select_from(model))==0 for model in [ClientAccountLink,ClientLinkInvitation,ClientPlanPublication])
        passed('restored-three-member-families-deny-blank-context-on-nonowner-restricted-role',role_flags=list(flags))
        def coherent():
            assert digest(snapshot())==baseline_hash
            with admin.connect() as connection:
                assert schema_signature(connection)==structural
                assert tenant_security_signature(connection)==security
                assert member_link_security_signature(connection)==members
        def restore_index():
            with admin.begin() as connection:
                connection.exec_driver_sql('DROP INDEX '+INDEX_NAME);create_history_index(connection)
                assert history_index_signature(connection)==canonical
            verify_runtime_schema(admin);coherent()
        # New restore-specific NULL ordering canary, unlike the author's ASC-only canary.
        with admin.begin() as connection:
            connection.exec_driver_sql('DROP INDEX '+INDEX_NAME)
            connection.exec_driver_sql('CREATE INDEX '+INDEX_NAME+' ON planes_generados (gym_id,id_cliente,fecha_generacion DESC NULLS FIRST,id DESC NULLS LAST) WHERE deleted_at IS NULL')
            wrong=history_index_signature(connection);assert wrong=={**canonical,'indoption':[0,0,3,1]}
            assert schema_signature(connection)==structural
        try:
            with pytest.raises(RuntimeError,match='history ordering'):verify_runtime_schema(admin)
            coherent();passed('restored-NULLS-FIRST-drift-rejected-with-identical-v1-rows-and-security',indoption=wrong['indoption'])
            with pytest.MonkeyPatch.context() as scoped:
                scoped.setattr(database,'_engine',app);scoped.setattr(database,'_SessionLocal',sessionmaker(bind=app,autoflush=False))
                for factory in ['web.main_web','api.app']:
                    executed=[]
                    def observed(connection,cursor,sql,parameters,context,executemany):
                        if sql.lstrip().split(' ',1)[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}:executed.append(sql.split(' ',1)[0])
                    event.listen(app,'before_cursor_execute',observed)
                    try:
                        with pytest.raises(RuntimeError,match='history ordering'):importlib.import_module(factory).create_app()
                    finally:event.remove(app,'before_cursor_execute',observed)
                    assert executed==[];coherent()
                    passed(factory+'-rejects-restored-drift-before-DML-cleanup-or-DDL',mutating_statements=0,all_rows_unchanged=True)
        finally:restore_index()
        with admin.begin() as connection:
            connection.exec_driver_sql('DROP INDEX '+INDEX_NAME)
            connection.exec_driver_sql('CREATE INDEX '+INDEX_NAME+' ON planes_generados (gym_id,id_cliente,fecha_generacion DESC NULLS LAST,id DESC NULLS LAST) WHERE deleted_at IS NOT NULL')
        try:
            with pytest.raises(RuntimeError):verify_runtime_schema(admin)
            assert digest(snapshot())==baseline_hash
            passed('restored-index-for-deleted-rows-cannot-stand-in-for-live-history')
        finally:restore_index()
        with admin.begin() as connection:connection.exec_driver_sql('ALTER TABLE client_account_links DISABLE TRIGGER r12_guard_link')
        try:
            with pytest.raises(RuntimeError,match='guards'):verify_runtime_schema(admin)
            assert digest(snapshot())==baseline_hash
            with admin.connect() as connection:assert history_index_signature(connection)==canonical
            passed('restored30-still-detects-disabled-member29-guard-with-canonical-history-index')
        finally:
            with admin.begin() as connection:connection.exec_driver_sql('ALTER TABLE client_account_links ENABLE TRIGGER r12_guard_link')
        verify_runtime_schema(admin);coherent()
        passed('all-restored-rows-and-both-security-families-exact-after-own-canaries',rows_sha256=baseline_hash,canonical_index=True,physical_refresh_tokens=8)
    except BaseException as error:
        rows.append({'case':'additive-restore-control-failure','passed':False,'failure_class':type(error).__name__});write();raise
    finally:
        if app is not None:app.dispose()
        admin.dispose()
