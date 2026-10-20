from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp')
P=T/'metodobase-sec-followup34-peer-private-20261019';O=R/'docs/implementation/20261018-evolution/evidence/security-followup34-independent-20261019'
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
original=T/'metodobase-sec-followup34-peer-sql-errors-20261019.py'
target=R/'tests/test_security_followup34_sql_errors_peer.py';assert not target.exists();target.write_bytes(original.read_bytes())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()=='80b9a44adf4daae160673b4d86a58cb06f809071'
def photo():
    names=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0')+['tests/'+target.name]
    return {'source':{n:sha((R/n).read_bytes()) for n in names if n and not n.startswith('docs/') and (R/n).is_file()},
        'packages':{d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())} for d in importlib.metadata.distributions()},
        'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
before=photo();save('sql-errors-before.json',before)
receipts=P/'SQL-error-receipts';receipts.mkdir()
cmd=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',str(target.relative_to(R)),'-q','--tb=short',
    '--basetemp='+str(P/'pytest-sql-errors'),'--junitxml='+str(P/'sql-errors.xml')]
environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',SEC_FOLLOWUP34_RECEIPTS=str(receipts))
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN','FOLLOWUP34_PRIVATE_LEASES']:environment.pop(key,None)
result=subprocess.run(cmd,cwd=R,env=environment,capture_output=True,timeout=360)
(P/'sql-errors-stdout.RAW.log').write_bytes(result.stdout);(P/'sql-errors-stderr.RAW.log').write_bytes(result.stderr)
cases=ET.parse(P/'sql-errors.xml').findall('.//testcase');rows=[{'case':c.get('classname')+'::'+c.get('name'),
    'outcome':next((k for k in ['failure','error','skipped'] if c.find(k)is not None),'passed')} for c in cases]
save('sql-errors-cases.STRUCTURAL.json',rows);after=photo();save('sql-errors-after.json',after)
summary={'exit':result.returncode,'cases':len(rows),'outcomes':{k:sum(r['outcome']==k for r in rows) for k in ['passed','failure','error','skipped']},
    'source_own_canary_92_metadata_bothPython_quiet':before==after,'PostgreSQL_profile_read':False}
save('sql-errors-summary.json',summary);print(json.dumps(summary));assert before==after
