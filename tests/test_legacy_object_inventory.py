"""Inventory never grants provenance, resolves ambiguity or writes its source."""
from datetime import datetime
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

from PIL import Image
import pytest
from sqlalchemy import create_engine,event,text
from sqlalchemy.orm import Session

from web.services import legacy_object_inventory as inventory


@pytest.fixture
def legacy_source(tmp_path):
    from web.database.models import Base,Usuario,UserRole,Cliente
    source=tmp_path/'legacy.db'
    engine=create_engine('sqlite:///'+source.as_posix())
    Base.metadata.create_all(engine)
    with engine.begin() as db:
        db.execute(text('CREATE TABLE alembic_version(version_num VARCHAR(32) PRIMARY KEY)'))
        db.execute(text("INSERT INTO alembic_version VALUES('20261018_stored_objects')"))
    with Session(engine) as db:
        for suffix in ('a','b'):
            db.add(Usuario(id='inventory-'+suffix,email='inventory-'+suffix+'@example.invalid',nombre='Synthetic',
                password_hash='unused',tipo='gym',role=UserRole.OWNER))
        db.flush()
        for suffix in ('a','b'):
            db.add(Cliente(gym_id='inventory-'+suffix,id_cliente='inventory-client-'+suffix,nombre='Synthetic'))
        db.commit()
    pdf=tmp_path/'private-pdfs';pdf.mkdir()
    logo=tmp_path/'legacy-web'/'web/static/uploads/logos';logo.mkdir(parents=True)
    output=tmp_path/'private-manifests';output.mkdir(mode=0o700)
    try:
        yield engine,inventory.InventoryRoots(pdf,logo),output
    finally:
        engine.dispose()


def plan(engine,path,*,owner='a',client=None,deleted=False,new=False):
    from web.database.models import PlanGenerado,StoredObject
    with Session(engine) as db:
        reference=None
        if new:
            row=StoredObject(gym_id='inventory-'+owner,kind='plan_pdf',key='opaque-review-key',
                content_type='application/pdf',byte_size=20,sha256='a'*64,storage_backend='local',status='ready')
            db.add(row);db.flush();reference=row.id
        row=PlanGenerado(gym_id='inventory-'+owner,id_cliente='inventory-client-'+(client or owner),
            ruta_pdf=str(path),pdf_object_id=reference,deleted_at=datetime(2026,1,1) if deleted else None)
        db.add(row);db.flush();identity=row.id;db.commit();return identity


def run(case,**kwargs):
    engine,roots,output=case
    target=output/'inventory.jsonl'
    with inventory.readonly_inventory_connection(engine) as db:
        summary=inventory.write_inventory(db,roots,target,page_size=1,**kwargs)
    return summary,[json.loads(line) for line in target.read_text(encoding='utf-8').splitlines()]


def entries(records):
    return [r for r in records if r['record']=='entry']


def test_valid_sources_are_streamed_hashed_and_still_require_provenance_review(legacy_source,caplog):
    from web.database.models import GymProfile
    engine,roots,_=legacy_source
    data=b'%PDF-synthetic-inventory'
    path=roots.pdf/'Private Client Filename.pdf';path.write_bytes(data)
    identity=plan(engine,path)
    image=BytesIO();Image.new('RGB',(4,4),'red').save(image,format='PNG')
    (roots.logo/'synthetic.png').write_bytes(image.getvalue())
    with Session(engine) as db:
        db.add(GymProfile(gym_id='inventory-a',logo_url='/static/uploads/logos/synthetic.png'));db.commit()
    statements=[]
    def observe(conn,cursor,statement,parameters,context,many):
        statements.append(statement.lstrip().split(None,1)[0].upper())
    event.listen(engine,'before_cursor_execute',observe)
    before=hashlib.sha256(Path(engine.url.database).read_bytes()).hexdigest()
    try:
        summary,records=run(legacy_source)
    finally:
        event.remove(engine,'before_cursor_execute',observe)
    assert summary['complete'] and summary['legacy_entries']==2
    assert len(records[0]['source_database_fingerprint'])==64
    assert not set(statements)&{'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}
    assert hashlib.sha256(Path(engine.url.database).read_bytes()).hexdigest()==before
    pdf=next(e for e in entries(records) if e['kind']=='plan_pdf')
    assert pdf['row_id']==identity and pdf['relative_path']==path.name
    assert pdf['byte_size']==len(data) and pdf['sha256']==hashlib.sha256(data).hexdigest()
    assert pdf['status']=='review_required' and pdf['issues']==['historical_provenance_unverified']
    assert len(pdf['source_fingerprint'])==len(pdf['file_fingerprint'])==64
    assert path.read_bytes()==data
    assert all(r.get('status')=='review_required' for r in records)
    assert str(roots.pdf) not in json.dumps(records) and str(roots.logo) not in json.dumps(records)
    assert path.name not in caplog.text and str(roots.pdf) not in caplog.text


def test_all_repeated_normalized_paths_are_ambiguous_even_same_owner_or_shadowed(legacy_source):
    engine,roots,_=legacy_source
    path=roots.pdf/'shared.pdf';path.write_bytes(b'%PDF-shared')
    alias=str(roots.pdf)+os.sep+'.'+os.sep+'shared.pdf'
    ids=[plan(engine,path),plan(engine,alias),plan(engine,'shared.pdf',owner='b')]
    shadow=plan(engine,path,new=True)
    summary,records=run(legacy_source)
    assert summary['excluded_new_references']==1
    rows=entries(records)
    assert {r['row_id'] for r in rows}==set(ids) and shadow not in {r['row_id'] for r in rows}
    assert all('ambiguous_path' in r['issues'] and r['path_reference_count']==4 for r in rows)
    assert all(r['sha256'] is None and r['status']=='review_required' for r in rows)


def test_path_case_follows_the_host_filesystem_normalization(legacy_source):
    engine,roots,_=legacy_source
    lower,upper=roots.pdf/'case.pdf',roots.pdf/'CASE.PDF'
    lower.write_bytes(b'%PDF-lower');upper.write_bytes(b'%PDF-upper')
    plan(engine,lower);plan(engine,upper,owner='b')
    _,records=run(legacy_source)
    assert all(('ambiguous_path' in row['issues'])==(os.name=='nt') for row in entries(records))


@pytest.mark.parametrize('condition,expected',[
    ('missing','missing_file'),('invalid','invalid_file_type'),('empty','invalid_size'),
    ('oversized','invalid_size'),('outside','outside_root'),('traversal','path_traversal'),
    ('directory','not_regular_file'),('symlink','symlink_or_junction')])
def test_invalid_paths_and_files_are_rejected_without_association(legacy_source,condition,expected,monkeypatch):
    engine,roots,_=legacy_source
    path=roots.pdf/'entry.pdf'
    if condition=='invalid':path.write_bytes(b'not a PDF')
    elif condition=='empty':path.write_bytes(b'')
    elif condition=='oversized':
        path.write_bytes(b'%PDF-too-big');monkeypatch.setattr(inventory,'MAX_PDF_BYTES',8)
    elif condition=='outside':path=roots.pdf.parent/'outside.pdf';path.write_bytes(b'%PDF-outside')
    elif condition=='traversal':
        (roots.pdf/'entry.pdf').write_bytes(b'%PDF-valid');(roots.pdf/'sub').mkdir();path=roots.pdf/'sub/../entry.pdf'
    elif condition=='directory':path.mkdir()
    elif condition=='symlink':
        target=roots.pdf/'original.pdf';target.write_bytes(b'%PDF-original')
        try:
            path.symlink_to(target)
        except OSError as error:
            if os.name!='nt' or error.winerror!=1314:
                raise
            # Windows without the symlink privilege still supports real NTFS
            # directory junctions. Exercise the same reparse/alias rejection.
            directory=roots.pdf/'junction-target';directory.mkdir()
            (directory/'entry.pdf').write_bytes(b'%PDF-original')
            junction=roots.pdf/'junction-link'
            result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',
                'New-Item -ItemType Junction -Path $env:METODOBASE_TEST_JUNCTION_PATH -Target $env:METODOBASE_TEST_JUNCTION_TARGET | Out-Null'],
                env=dict(os.environ,METODOBASE_TEST_JUNCTION_PATH=str(junction),METODOBASE_TEST_JUNCTION_TARGET=str(directory)),
                capture_output=True,timeout=15)
            assert result.returncode==0
            path=junction/'entry.pdf'
    plan(engine,path)
    _,records=run(legacy_source)
    row=entries(records)[0]
    assert expected in row['issues'] and row['sha256'] is None


def test_file_change_during_read_is_rejected_by_fd_fingerprints(legacy_source,monkeypatch):
    engine,roots,_=legacy_source
    path=roots.pdf/'changing.pdf';path.write_bytes(b'%PDF-before')
    plan(engine,path)
    original=inventory.os.read
    changed=[]
    def mutate(fd,size):
        block=original(fd,size)
        if block and not changed:
            changed.append(True)
            previous=path.stat();path.write_bytes(b'%PDF-after!')
            os.utime(path,ns=(previous.st_atime_ns,previous.st_mtime_ns+1_000_000_000))
        return block
    monkeypatch.setattr(inventory.os,'read',mutate)
    _,records=run(legacy_source)
    assert changed and 'file_changed' in entries(records)[0]['issues'],entries(records)[0]
    assert entries(records)[0]['sha256'] is None


@pytest.mark.parametrize('ctime_changes',[False,True])
def test_distinct_path_and_fd_ctime_semantics_do_not_hide_real_fd_changes(legacy_source,monkeypatch,ctime_changes):
    _,roots,_=legacy_source
    path=roots.pdf/'ctime.pdf';data=b'%PDF-stable-api-clocks';path.write_bytes(data)
    path_time=path.stat().st_ctime_ns
    original=inventory.os.fstat
    calls=[]
    def fd_metadata(fd):
        result=original(fd);calls.append(True)
        return SimpleNamespace(st_dev=result.st_dev,st_ino=result.st_ino,st_size=result.st_size,
            st_mtime_ns=result.st_mtime_ns,st_mode=result.st_mode,
            st_ctime_ns=path_time+1_000_000+(1_000_000 if ctime_changes and len(calls)>1 else 0))
    monkeypatch.setattr(inventory.os,'fstat',fd_metadata)
    result=inventory._read_file(path,roots.pdf,'plan_pdf')
    if ctime_changes:
        assert result['issues']==['file_changed']
    else:
        assert result['issues']==[] and result['sha256']==hashlib.sha256(data).hexdigest()


def test_mixed_and_deleted_associations_do_not_read_bytes(legacy_source,monkeypatch):
    from web.database.models import Cliente
    engine,roots,_=legacy_source
    paths=[roots.pdf/(label+'.pdf') for label in ('mixed','deleted','deleted-client')]
    for path in paths:path.write_bytes(b'%PDF-private')
    plan(engine,paths[0],owner='a',client='b')
    plan(engine,paths[1],deleted=True)
    plan(engine,paths[2],owner='b')
    with Session(engine) as db:
        db.query(Cliente).filter_by(id_cliente='inventory-client-b').one().deleted_at=datetime(2026,1,1)
        db.commit()
    monkeypatch.setattr(inventory,'_read_file',lambda *args:pytest.fail('Rejected association must not open bytes'))
    _,records=run(legacy_source)
    assert 'mixed_tenant_reference' in entries(records)[0]['issues']
    assert 'deleted_plan' in entries(records)[1]['issues']
    assert 'deleted_client' in entries(records)[2]['issues']


def test_index_limit_closes_incomplete_manifest_and_raises(legacy_source):
    engine,roots,output=legacy_source
    for number in (1,2):
        path=roots.pdf/(str(number)+'.pdf');path.write_bytes(b'%PDF-unique');plan(engine,path)
    with pytest.raises(inventory.InventoryError,match='path_index_limit_exceeded'):
        run(legacy_source,max_paths=1)
    records=[json.loads(line) for line in (output/'inventory.jsonl').read_text().splitlines()]
    assert records[-1]['record']=='footer' and records[-1]['complete'] is False
    assert records[-1]['legacy_entries']==0


@pytest.mark.parametrize('query',['host=other.invalid','port=1','dbname=other','user=app','options=-c+role%3Dapp'])
def test_cli_rejects_driver_authority_overrides_before_engine_creation(query,monkeypatch):
    from scripts import inventory_legacy_objects as cli
    monkeypatch.setattr(cli,'create_engine',lambda *a,**k:pytest.fail('No engine before target validation'))
    with pytest.raises(inventory.InventoryError,match='database_query_override_rejected'):
        cli.create_inventory_engine('postgresql://audit:synthetic-secret@127.0.0.1:55482/expected?'+query,'expected')


@pytest.mark.parametrize('url',[
    'postgresql://audit@127.0.0.1:55482',
    'postgresql://audit@/expected',
    'postgresql://127.0.0.1:55482/expected',
    'postgresql://audit@127.0.0.1:55482/other'])
def test_missing_or_different_explicit_database_authority_fails_before_connect(url,monkeypatch):
    from scripts import inventory_legacy_objects as cli
    monkeypatch.setattr(cli,'create_engine',lambda *a,**k:pytest.fail('No defaults or alternative target'))
    with pytest.raises(inventory.InventoryError,match='database_target_mismatch'):
        cli.create_inventory_engine(url,'expected')


def test_cli_argument_errors_do_not_echo_paths_or_credentials(capsys):
    from scripts import inventory_legacy_objects as cli
    assert cli.main(['--database-url','postgresql://audit:private-secret@private.invalid/private-db'])==2
    result=capsys.readouterr().err
    assert json.loads(result)['error_code']=='invalid_inventory_arguments'
    assert 'private-secret' not in result and 'private.invalid' not in result


def test_cli_validates_private_output_before_connecting_and_never_uses_app_default(legacy_source,monkeypatch,capsys):
    from scripts import inventory_legacy_objects as cli
    _,roots,output=legacy_source
    monkeypatch.setenv('DATABASE_URL','postgresql://app:synthetic-private@production.invalid/forbidden')
    monkeypatch.delenv('LEGACY_INVENTORY_DATABASE_URL',raising=False)
    monkeypatch.setattr(cli,'create_inventory_engine',lambda *a:pytest.fail('Must not connect'))
    code=cli.main(['--expected-database','anything','--pdf-root',str(roots.pdf),'--logo-root',str(roots.logo),
        '--manifest',str(roots.pdf/'unsafe-manifest.jsonl')])
    assert code==2
    first=capsys.readouterr().err
    code=cli.main(['--expected-database','anything','--pdf-root',str(roots.pdf),'--logo-root',str(roots.logo),
        '--manifest',str(output/'private.jsonl')])
    second=capsys.readouterr().err
    assert code==2 and 'explicit_inventory_database_required' in second
    assert 'synthetic-private' not in first+second


def test_cli_reads_existing_sqlite_uri_without_source_changes(legacy_source,monkeypatch,capsys):
    from scripts import inventory_legacy_objects as cli
    engine,roots,output=legacy_source
    path=roots.pdf/'cli.pdf';path.write_bytes(b'%PDF-cli');plan(engine,path)
    source=Path(engine.url.database).resolve()
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setenv('LEGACY_INVENTORY_DATABASE_URL',str(engine.url))
    code=cli.main(['--expected-database',str(source),'--pdf-root',str(roots.pdf),'--logo-root',str(roots.logo),
        '--manifest',str(output/'cli.jsonl'),'--page-size','1'])
    assert code==0
    assert json.loads(capsys.readouterr().out)['legacy_entries']==1
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
