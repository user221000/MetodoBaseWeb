"""Preserve the reporting mistake, verify exact UUID absence, then tidy new helpers."""
from pathlib import Path
import ast,hashlib,json,subprocess,sys,zipfile
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
root=Path(r'F:\mb-r12-history30-20261019');temp=Path(r'C:\Users\Consu\AppData\Local\Temp');out=temp/'metodobase-ci30-closure-quality-20261019';out.mkdir(exist_ok=False)
pg=temp/'metodobase-ci30-current-pg-first-20261019';history=temp/'metodobase-ci30-archive29-first-20261019'
summary=json.loads((pg/'summary.json').read_bytes());assert len(summary['results'])==4 and all(r['exit']==0 for r in summary['results']) and summary['sources_packages_stable']
configuration=json.loads((temp/'metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text(encoding='utf-8-sig'))
owned=[]
for directory,filename in [(pg/'private-evidence','history-index30-author-owned-created.json'),(history/'private-restore-evidence','client-link29-author-owned-created.json')]:
    values=json.loads((directory/filename).read_bytes())['names'];assert len(values)==2
    assert all(name.startswith(('metodobase_test_backup_','metodobase_test_restore_')) for name in values)
    owned.extend(values)
assert len(set(owned))==4
engine=create_engine(make_url(configuration['METODOBASE_TEST_MIGRATOR_URL']).set(database='postgres'));rows=[]
try:
    with engine.connect() as db:
        db.exec_driver_sql('SET TRANSACTION READ ONLY')
        for name in owned:rows.append({'database':name,'count':db.execute(text('SELECT count(*) FROM pg_database WHERE datname=:name'),{'name':name}).scalar_one()})
finally:engine.dispose()
assert all(row['count']==0 for row in rows)
(out/'independent-four-UUID-absence.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
(out/'reporting-error-note.json').write_text(json.dumps({'original_wrapper_exit':1,'cause':'Wrapper looked for personal-history30-author-owned-created.json; maintained fixture actually emits history-index30-author-owned-created.json. No test, fixture or assertion changed. Original summary and empty closure are preserved.','actual_tests':{'index_PG':8,'restore30_PG':1,'units':74,'report_parser_exit':0},'recovery':'Read only catalog query for exactly four fixture-generated historical29/current30 UUID names; all absent. No tests repeated, no DDL, DML or deletion.'},indent=2)+'\n',encoding='utf8')
names=['tests/run_reviewed_ci29.py','tests/verify_history_index_ci.py','tests/check_history_index_reports.py','tests/test_history_index_ci_trust.py']
with zipfile.ZipFile(out/'before-quality-source-exact.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in names:archive.writestr(name,(root/name).read_bytes())
quality=temp/'metodobase-qa-20261018/Scripts/python.exe'
result=subprocess.run([str(quality),'-m','ruff','check',*names],cwd=root,capture_output=True,check=False)
(out/'ruff-before.log').write_bytes(result.stdout+result.stderr);assert result.returncode==1
# Explicitly collect nonzero subprocess outcomes; never ask Ruff to suppress them.
for name in ['tests/run_reviewed_ci29.py','tests/verify_history_index_ci.py']:
    source=(root/name).read_text(encoding='utf8');lines=source.splitlines(keepends=True);offsets=[0]
    for line in lines:offsets.append(offsets[-1]+len(line))
    positions=[]
    for node in ast.walk(ast.parse(source)):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='subprocess' and node.func.attr=='run' and not any(k.arg=='check' for k in node.keywords):
            positions.append(offsets[node.end_lineno-1]+node.end_col_offset-1)
    for position in sorted(positions,reverse=True):
        assert source[position]==')';source=source[:position]+', check=False'+source[position:]
    ast.parse(source);(root/name).write_bytes(source.encode())
result=subprocess.run([str(quality),'-m','ruff','check','--select','I','--fix',*names],cwd=root,capture_output=True,check=False)
(out/'ruff-import-fix.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
# Rebind only changed executable hashes; historical helper28/checker29 stay exact.
path=root/'tests/verify_history_index_ci.py';source=path.read_text(encoding='utf8');tree=ast.parse(source)
node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED_CURRENT_GATES' for t in n.targets));pins=ast.literal_eval(node.value)
for name in pins:pins[name]=hashlib.sha256((root/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
lines=source.splitlines(keepends=True);lines[node.lineno-1:node.end_lineno]=['PINNED_CURRENT_GATES = '+repr(pins)+'\n'];path.write_bytes(''.join(lines).encode())
result=subprocess.run([str(quality),'-m','ruff','check',*names],cwd=root,capture_output=True,check=False)
(out/'ruff-after.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
(out/'after-quality-source.json').write_text(json.dumps({name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names},indent=2)+'\n',encoding='utf8')
print(json.dumps({'four_exact_UUIDs_absent':True,'no_test_replayed_for_reporting_correction':True,'ruff_after_exit':result.returncode,'quality_files':len(names)}))
