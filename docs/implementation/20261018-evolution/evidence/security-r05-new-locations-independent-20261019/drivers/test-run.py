from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-r05-classifier-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp')
P=T/'metodobase-sec-r05-new-peer-private-20261019'
O=R/'docs/implementation/20261018-evolution/evidence/security-r05-new-locations-independent-20261019'
TEST=T/'metodobase-sec-r05-new-peer-canaries-20261019.py'
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
def photo():
    names=subprocess.check_output(['git','ls-files','-z','--','scripts','tests','web','api','core','config','requirements*','pyproject.toml'],cwd=R).decode().split('\0')
    binding=json.loads((O/'countercanary-input-binding.json').read_bytes())
    return {'sources':{n:sha((R/n).read_bytes()) for n in names if n and (R/n).is_file()},
        'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
        'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes()),
        'canary_source':sha(TEST.read_bytes()),'installed_v1':sha((R/'scripts/data/reviewed_scan_locations_v1.zip').read_bytes()),
        'private_candidate_snapshot':{name:sha((Path(binding['snapshot'])/name).read_bytes()) for name in binding['files']}}
before=photo();assert len(before['packages'])==89;save('tests-before.json',before)
cmd=[sys.executable,'-B','-m','pytest',str(TEST),'-q','--tb=short','--rootdir='+str(P),
    '--basetemp='+str(P/'pytest-final'),'--junitxml='+str(P/'tests.xml'),'-o','cache_dir='+str(P/'cache')]
result=subprocess.run(cmd,cwd=P,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=240)
(P/'tests-stdout.RAW.log').write_bytes(result.stdout);(P/'tests-stderr.RAW.log').write_bytes(result.stderr)
cases=ET.parse(P/'tests.xml').findall('.//testcase')
rows=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped'] if c.find(k)is not None),'passed')} for c in cases]
save('tests.STRUCTURAL.json',rows);after=photo();save('tests-after.json',after);assert before==after
summary={'exit':result.returncode,'cases':len(rows),'outcomes':{k:sum(r['outcome']==k for r in rows) for k in ['passed','failure','error','skipped']},
    'sources_89_bothPython_and_private_snapshot_quiet':True,'new_actual_scanner_runs':0,'installed_registry_changed':False,
    'scope':'One runtime replay covers14516pins;105negative controls cover15occurrences x7changes;7offline producer/receipt controls. Repeated semantic-review attempts are not added as test cases.'}
save('tests-summary.json',summary);print(json.dumps(summary))
