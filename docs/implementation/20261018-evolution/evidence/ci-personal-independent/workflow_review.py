"""Independent frozen-workflow parser and inert fixture-function checks."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,yaml
ROOT=Path(r"F:\MetodoBaseWeb-execution-20261018")
OUT=Path(__file__).resolve().parent
BASH=r"C:\Program Files\Git\bin\bash.exe"
workflow=(ROOT/".github/workflows/ci.yml").read_text(encoding='utf8')
data=yaml.safe_load(workflow)
blocks=[]
for job_name,job in data['jobs'].items():
    for index,step in enumerate(job.get('steps',[])):
        if 'run' not in step:continue
        path=OUT/('syntax-'+str(len(blocks))+'.sh');path.write_text(step['run'],encoding='utf8')
        result=subprocess.run([BASH,'-n',path.as_posix()],capture_output=True,text=True)
        blocks.append({'job':job_name,'step':index,'exit':result.returncode,'stderr':result.stderr})
assert all(row['exit']==0 for row in blocks)
references=sorted(set(re.findall(r'(?:scripts|tests)/[A-Za-z0-9_./-]+\.(?:py|cjs)',workflow)))
assert all((ROOT/path).is_file() for path in references)
old=subprocess.check_output(['git','show','HEAD:.github/workflows/ci.yml'],cwd=ROOT,text=True)
old_calls=[line.strip() for line in old.splitlines() if line.strip().startswith('run_browser_fixture tests/')]
new_calls=[line.strip() for line in workflow.splitlines() if line.strip().startswith('run_browser_fixture tests/')]
assert len(old_calls)==5 and new_calls[:5]==old_calls
assert len(new_calls)==6 and new_calls[-1].endswith('15 named 8')
node_guard=lambda value:next(line.strip() for line in value.splitlines() if 'Number.isSafeInteger' in line)
assert node_guard(old)==node_guard(workflow)
block=next(step['run'] for step in data['jobs']['image']['steps'] if step.get('name','').startswith('Generation, private branding'))
function=block[block.index('run_browser_fixture() {'):block.index('\nbrowser_evidence=')]
(OUT/'exact-fixture-function.sh').write_text(function+'\n',encoding='utf8')
writer=OUT/'write_synthetic_report.py'
writer.write_text("""import json,sys
from pathlib import Path
path,kind,minimum,screens,bad=sys.argv[1:]
n=int(minimum)
report={'checks':['check-'+str(i) for i in range(n)],'pageErrors':[]}
if kind=='named':report['checks']=[{'name':name} for name in report['checks']]
if int(screens):report['screens']=['screen-'+str(i) for i in range(int(screens))]
if bad=='1':report['pageErrors']=['Synthetic failure']
Path(path).write_text(json.dumps(report),encoding='utf8')
""",encoding='utf8')
prefix='set -euo pipefail\nbrowser_fixture_pid=\'\'\nkill() { printf \'%s\\n\' "$1" >> "$QA_KILLS"; builtin kill "$@"; }\ntrap \'if [ -n "${browser_fixture_pid:-}" ]; then kill "$browser_fixture_pid" 2>/dev/null || true; fi\' EXIT\npython() {\n if [[ "$1" == \'-X\' ]]; then\n  if [[ "${QA_SERVER_EXIT:-0}" == 1 ]]; then return 0; fi\n  exec /usr/bin/sleep 20\n else\n  "$QA_PYTHON" "$QA_GUARD" "${@:2}"\n fi\n}\nnode() {\n if [[ "${QA_DRIVER_FAIL:-0}" == 1 ]]; then return 7; fi\n if [[ "${QA_REPORT_MISSING:-0}" == 1 ]]; then return 0; fi\n "$QA_PYTHON" "$QA_WRITER" "$expected_report" "$report_format" "$minimum_checks" "$minimum_screens" "${QA_REPORT_BAD:-0}"\n}\ncurl() { [[ "${QA_NOT_READY:-0}" != 1 ]]; }\nsleep() { :; }\n'

scenarios=[('healthy-strings',{},0,'strings',0),('healthy-named',{},0,'named',8),
 ('serial-reuse',{},0,'strings',0),('driver-failure',{'QA_DRIVER_FAIL':'1'},7,'strings',0),
 ('missing-report',{'QA_REPORT_MISSING':'1'},1,'strings',0),('bad-report',{'QA_REPORT_BAD':'1'},1,'named',8),
 ('not-ready',{'QA_NOT_READY':'1'},1,'strings',0),('server-exited',{'QA_SERVER_EXIT':'1'},1,'named',8)]
results=[]
for name,changes,expected,kind,screens in scenarios:
    cwd=OUT/('bash-'+name);cwd.mkdir();(cwd/'docs/implementation/20261018-evolution/evidence/ux').mkdir(parents=True)
    calls='run_browser_fixture synthetic_fixture.py 9999 synthetic_driver.cjs report.json 15 '+kind+' '+str(screens)+'\n'
    if name=='serial-reuse':calls+='run_browser_fixture synthetic_fixture.py 9999 second_driver.cjs second.json 15 strings 0\n'
    script=cwd/'probe.sh';script.write_text(prefix+'\n'+function+'\n'+calls,encoding='utf8')
    env=dict(os.environ,QA_PYTHON=Path(sys.executable).as_posix(),QA_GUARD=(ROOT/'scripts/check_frontend_report.py').as_posix(),QA_WRITER=writer.as_posix(),QA_KILLS=(cwd/'kills.txt').as_posix(),**changes)
    run=subprocess.run([BASH,script.as_posix()],cwd=cwd,env=env,capture_output=True,text=True,timeout=15)
    killed=(cwd/'kills.txt').read_text().splitlines() if (cwd/'kills.txt').exists() else []
    row={'case':name,'exit':run.returncode,'expectedExit':expected,'matched':run.returncode==expected,'killCalls':len(killed),'stderr':run.stderr}
    if expected==0:assert len(killed)==(2 if name=='serial-reuse' else 1)
    assert row['matched'],row
    results.append(row)
entrypoints=(ROOT/'tests/test_desktop_entrypoints.py').read_text(encoding='utf8')
assert entrypoints.count('@pytest.mark.skipif(sys.platform != "win32"')==2
sample=OUT/'windows-only-in-linux.xml'
sample.write_text('<testsuites><testsuite><testcase><skipped message="Windows batch semantics require Windows"/></testcase></testsuite></testsuites>',encoding='utf8')
no_skips=next(step['run'] for step in data['jobs']['test-web']['steps'] if step.get('name')=='Required SaaS cases cannot silently become skips')
code=no_skips.split('python -c "',1)[1].rsplit('"',1)[0].replace("'pytest-web.xml'",repr(str(sample)))
rejected=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
assert rejected.returncode!=0
summary={'bashBlocks':blocks,'scriptReferences':references,'fivePreviousFixtureCallsUnchanged':True,
 'previousNodeGuardByteIdentical':True,'fixtureFunctionSha256':hashlib.sha256(function.encode()).hexdigest(),
 'syntheticFixtureBoundaryCases':results,'scope':'Bash -n plus exact function with inert shell stubs and own sleep children; no browser/server TCP or external I/O. CLI guard itself real.',
 'platformRoutingObservation':{'twoWindowsCasesSkipOnLinuxBySourceCondition':True,'exactUnchangedNoSkipsGuardRejectsSyntheticJUnit':True,'linuxSuiteExecuted':False}}
(OUT/'workflow-independent-review.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print('Bash syntax',len(blocks),'references',len(references),'fixture boundaries',len(results),'all matched')
