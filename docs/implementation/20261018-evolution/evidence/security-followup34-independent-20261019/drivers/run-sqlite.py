from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp')
P=T/'metodobase-sec-followup34-peer-private-20261019'
O=R/'docs/implementation/20261018-evolution/evidence/security-followup34-independent-20261019'
BASE='80b9a44adf4daae160673b4d86a58cb06f809071';sha=lambda b:hashlib.sha256(b).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()==BASE
assert not subprocess.check_output(['git','status','--porcelain'],cwd=R)
O.mkdir();(O/'.gitattributes').write_bytes(b'* -text\n')
save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
def photo():
    names=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0')
    return {'source':{n:sha((R/n).read_bytes()) for n in names if n and not n.startswith('docs/') and (R/n).is_file()},
        'packages':{d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())} for d in importlib.metadata.distributions()},
        'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes()),
        'wire_SHA256':sha((R/'docs/implementation/20261018-evolution/SEGUIMIENTO_TAREAS_WIRE34.json').read_bytes())}
before=photo();assert len(before['packages'])==92 and before['wire_SHA256']=='33bfe88f33705cb33b70c2ef2b57951e9ee59cb7176466143e93d3822fd83f91'
save('author-sqlite-before.json',before)
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);assert pip.returncode==0
(O/'pip-before.RAW.log').write_bytes(pip.stdout+pip.stderr)
files=['tests/test_followup34_http.py','tests/test_followup34_boundaries.py','tests/test_followup34_domain.py',
    'tests/test_followup34_mechanisms.py','tests/test_followup34_races.py','tests/integration_followup34_migrations.py']
cmd=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',*files,'-k','not postgresql','-q','--tb=short',
    '--basetemp='+str(P/'pytest-author-sqlite'),'--junitxml='+str(P/'author-sqlite.xml')]
environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN','FOLLOWUP34_PRIVATE_LEASES']:
    environment.pop(key,None)
result=subprocess.run(cmd,cwd=R,env=environment,capture_output=True,timeout=480)
(P/'author-sqlite-stdout.RAW.log').write_bytes(result.stdout);(P/'author-sqlite-stderr.RAW.log').write_bytes(result.stderr)
cases=ET.parse(P/'author-sqlite.xml').findall('.//testcase')
rows=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped'] if c.find(k)is not None),'passed')} for c in cases]
save('author-sqlite-cases.STRUCTURAL.json',rows);after=photo();save('author-sqlite-after.json',after)
summary={'exit':result.returncode,'cases':len(rows),'outcomes':{k:sum(r['outcome']==k for r in rows) for k in ['passed','failure','error','skipped']},
    'source_92_metadata_bothPython_wire_quiet':before==after,'PostgreSQL_cases_selected':False,'PostgreSQL_profile_read':False,'new_dependencies':False}
save('author-sqlite-summary.json',summary);print(json.dumps(summary));assert before==after
