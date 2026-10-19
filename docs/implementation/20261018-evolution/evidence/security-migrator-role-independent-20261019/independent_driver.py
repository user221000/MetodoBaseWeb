"""Own desired-success baseline plus ACL/RLS reparenting and DDL negatives."""
from pathlib import Path
import importlib.util,json,os,sys
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

HERE=Path(__file__).parent
DRIVER=Path('F:/mb-mig-sec/tests/integration_restricted_migrator.py')
spec=importlib.util.spec_from_file_location('private_migrator_review_fixture',DRIVER)
driver=importlib.util.module_from_spec(spec);sys.modules[spec.name]=driver;spec.loader.exec_module(driver)
owned_roles=driver.owned_roles

def test_original_empty_production_path_requires_success_without_cluster_role_creation(owned_roles,monkeypatch):
    case=owned_roles;root=Path(os.environ.get('MIGRATOR_REVIEW_SOURCE_ROOT','F:/mb-mig-sec'))
    monkeypatch.setattr(driver,'ROOT',root)
    evidence=Path(os.environ['METODOBASE_TEST_ROLE_EVIDENCE'])
    previous=set(evidence.glob('sqlstate-*.json'))
    result=driver.cli(case)
    diagnostics=[json.loads(p.read_bytes()) for p in set(evidence.glob('sqlstate-*.json'))-previous]
    with case['migrator'].connect() as db:
        tables=db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r'"))
        alembic_present=bool(db.scalar(text("SELECT to_regclass('public.alembic_version')")))
        legacy_preserved=driver.legacy_state(db)==case['legacy_before']
    report={'source_root':str(root),'exit':result.returncode,'public_tables':tables,'alembic_present':alembic_present,
        'legacy_state_preserved':legacy_preserved,'diagnostics':diagnostics,'stdout_or_credentials_published':False}
    (evidence/'own-empty-path-observation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    assert result.returncode==0
    assert legacy_preserved
    driver.verify_runtime_schema(case['migrator'],expected_revision=driver.REVISION)

def test_restricted_runtime_cannot_reparent_own_row_or_gain_ddl_helper_or_migrator(owned_roles):
    case=owned_roles;assert driver.cli(case).returncode==0
    with case['migrator'].begin() as db:
        for suffix in ('a','b'):
            db.execute(text("INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,activo,fecha_registro,role,session_version) VALUES(:id,:email,'synthetic','Synthetic','','gym',true,'2026-10-19','OWNER',0)"),
                {'id':'security-'+suffix,'email':'security-'+suffix+'@example.invalid'})
            db.execute(text("SELECT set_config('app.current_tenant',:tenant,true)"),{'tenant':'security-'+suffix})
            db.execute(text("INSERT INTO clientes(id_cliente,gym_id,nombre,activo) VALUES(:id,:gym,'Synthetic',true)"),{'id':'security-client-'+suffix,'gym':'security-'+suffix})
    failures=[]
    with case['app'].begin() as db:
        assert db.execute(text('SELECT id_cliente FROM clientes')).all()==[]
        db.execute(text("SELECT set_config('app.current_tenant','security-a',true)"))
        assert db.execute(text('SELECT id_cliente FROM clientes')).all()==[('security-client-a',)]
        for kind,statement in [
            ('reparent',"UPDATE clientes SET gym_id='security-b' WHERE id_cliente='security-client-a'"),
            ('schema_create','CREATE TABLE public.security_denied_table(id integer)'),
            ('helper_escalation','ALTER FUNCTION public.set_tenant(text) SECURITY DEFINER'),
            ('set_role_migrator','SET ROLE '+db.dialect.identifier_preparer.quote(case['names']['migrator'])),
        ]:
            with pytest.raises(DBAPIError) as denied:
                with db.begin_nested():db.execute(text(statement))
            assert denied.value.orig.pgcode=='42501'
            failures.append({'kind':kind,'sqlstate':denied.value.orig.pgcode})
        assert db.execute(text("DELETE FROM clientes WHERE id_cliente='security-client-b'")).rowcount==0
        assert db.execute(text("SELECT gym_id FROM clientes WHERE id_cliente='security-client-a'")).scalar_one()=='security-a'
        assert not db.scalar(text("SELECT prosecdef FROM pg_proc WHERE oid='public.set_tenant(text)'::regprocedure"))
        assert db.scalar(text("SELECT to_regclass('public.security_denied_table')")) is None
    with case['migrator'].begin() as db:
        for suffix in ('a','b'):
            db.execute(text("SELECT set_config('app.current_tenant',:tenant,true)"),{'tenant':'security-'+suffix})
            assert db.execute(text('SELECT gym_id FROM clientes')).all()==[('security-'+suffix,)]
        assert db.scalar(text("SELECT count(*) FROM pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) a WHERE c.relnamespace='public'::regnamespace AND a.grantee=(SELECT oid FROM pg_roles WHERE rolname='metodobase_app')"))==0
    destination=Path(os.environ['METODOBASE_TEST_ROLE_EVIDENCE'])/('own-runtime-negatives-'+case['state']+'.json')
    destination.write_text(json.dumps({'negative_checks':failures,'foreign_delete_rows':0,'source_owners_preserved':True,'legacy_automatic_acl':0},indent=2)+'\n',encoding='utf8')
