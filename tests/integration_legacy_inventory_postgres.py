"""Global inventory requires an existing audit role and one read-only snapshot."""
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database,run_migration
from tests.integration_provider_subjects import application_engine
from web.services import legacy_object_inventory as inventory


@pytest.fixture
def global_source(migration_database,tmp_path):
    from web.database.models import Usuario,UserRole,Cliente,PlanGenerado
    url,admin=migration_database
    run_migration(url,'db_bootstrap.py','--revision','head')
    pdf=tmp_path/'private-pdf';pdf.mkdir()
    logo=tmp_path/'legacy/web/static/uploads/logos';logo.mkdir(parents=True)
    out=tmp_path/'private-inventory';out.mkdir(mode=0o700)
    source=pdf/'shared.pdf';source.write_bytes(b'%PDF-global-review')
    with Session(admin) as db:
        for suffix in ('a','b'):
            db.add(Usuario(id='global-'+suffix,email='global-'+suffix+'@example.invalid',nombre='Synthetic',
                password_hash='unused',tipo='gym',role=UserRole.OWNER))
        db.flush()
        for suffix in ('a','b'):
            db.add(Cliente(gym_id='global-'+suffix,id_cliente='global-client-'+suffix,nombre='Synthetic'))
        db.flush()
        db.add(PlanGenerado(gym_id='global-a',id_cliente='global-client-a',ruta_pdf=str(source)))
        db.commit()
    yield admin,inventory.InventoryRoots(pdf,logo),out,source,url


@pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)
def test_existing_operational_role_sees_both_tenants_but_cannot_write(global_source):
    from web.database.models import PlanGenerado
    admin,roots,out,path,_=global_source
    with Session(admin) as db:
        db.add(PlanGenerado(gym_id='global-b',id_cliente='global-client-b',ruta_pdf=str(path)));db.commit()
    with inventory.readonly_inventory_connection(admin) as db:
        assert db.scalar(text('SHOW transaction_isolation'))=='repeatable read'
        assert db.scalar(text('SHOW transaction_read_only'))=='on'
        summary=inventory.write_inventory(db,roots,out/'global.jsonl',page_size=1)
        assert summary['legacy_entries']==2
        with pytest.raises(DBAPIError) as denied:
            db.execute(text("UPDATE usuarios SET nombre='forbidden' WHERE id='global-a'"))
        assert denied.value.orig.pgcode=='25006'
    records=[json.loads(line) for line in (out/'global.jsonl').read_text().splitlines()]
    rows=[r for r in records if r['record']=='entry']
    assert {r['tenant_id'] for r in rows}=={'global-a','global-b'}
    assert all('ambiguous_path' in r['issues'] for r in rows)
    with Session(admin) as db:
        assert db.scalar(text("SELECT nombre FROM usuarios WHERE id='global-a'"))=='Synthetic'


@pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)
def test_application_role_cannot_report_a_partial_global_inventory(global_source):
    admin,roots,out,_,url=global_source
    app=application_engine(url,admin)
    restricted=create_engine(app.url,connect_args={'options':'-c search_path=public,pg_catalog'})
    app.dispose()
    try:
        # An operational source may contain drift. Never trust a lookalike
        # public catalog table when deciding whether FORCE RLS can hide rows.
        with admin.begin() as db:
            db.execute(text('CREATE TABLE public.pg_roles(rolsuper boolean,rolbypassrls boolean,rolname name)'))
            db.execute(text('INSERT INTO public.pg_roles VALUES(true,true,:role)'),{'role':restricted.url.username})
            db.execute(text('GRANT SELECT ON public.pg_roles TO PUBLIC'))
        with pytest.raises(inventory.InventoryError,match='global_visibility_required'):
            with inventory.readonly_inventory_connection(restricted) as db:
                inventory.write_inventory(db,roots,out/'must-not-exist.jsonl')
        assert not (out/'must-not-exist.jsonl').exists()
    finally:
        restricted.dispose()


@pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)
def test_both_streaming_passes_use_the_same_repeatable_read_snapshot(global_source,monkeypatch):
    from web.database.models import PlanGenerado
    admin,roots,out,path,_=global_source
    original=inventory._references
    passes=[]
    def concurrent_insert(connection,page_size):
        passes.append(True)
        number=len(passes)
        yield from original(connection,page_size)
        if number==1:
            with Session(admin) as writer:
                writer.add(PlanGenerado(gym_id='global-b',id_cliente='global-client-b',ruta_pdf=str(path)))
                writer.commit()
    monkeypatch.setattr(inventory,'_references',concurrent_insert)
    with inventory.readonly_inventory_connection(admin) as db:
        summary=inventory.write_inventory(db,roots,out/'snapshot.jsonl',page_size=1)
    assert len(passes)==2 and summary['legacy_entries']==1 and summary['scanned_rows']==1
    records=[json.loads(line) for line in (out/'snapshot.jsonl').read_text().splitlines()]
    assert records[-1]['complete'] is True
    with Session(admin) as db:
        assert db.query(PlanGenerado).count()==2
