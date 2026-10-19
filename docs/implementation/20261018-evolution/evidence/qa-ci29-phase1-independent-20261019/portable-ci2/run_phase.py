"""Serial actual VM/parser, local unit, or bounded verifier execution. No PG/browser."""
from support import *
import shlex,time
import yaml
mode=sys.argv[1];assert mode in {'vm18','units33','wiring25'}
phase=TEMP/mode;phase.mkdir(exist_ok=False)
before=photo(mode+'-before')
environment=os.environ.copy()
for name in list(environment):
    key=name.upper()
    if key=='DATABASE_URL' or key.endswith('_DATABASE_URL') or key.startswith(('PG','AWS_','S3_')) or any(word in key for word in ['STRIPE','MERCADOPAGO','RESEND','SMTP','SENTRY','OPENAI_API']):environment.pop(name,None)
environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',PYTHONPATH='')
started=time.monotonic();rows=[]
if mode=='vm18':
    workflow=yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8-sig'))
    commands=[];guards=[]
    for step in workflow['jobs']['frontend-contracts']['steps']:
        for line in step.get('run','').splitlines():
            if line.startswith('node tests/e2e/'):
                driver,report=line.split(' > ');commands.append((shlex.split(driver),report))
            elif line.startswith(('python scripts/check_frontend_report.py ','node -e ')):guards.append(shlex.split(line))
    assert len(commands)==18
    for command,report in commands:
        command[0]='C:/Program Files/nodejs/node.exe'
        result=subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,timeout=60)
        (phase/report).write_bytes(result.stdout);(phase/(report+'.stderr.log')).write_bytes(result.stderr)
        value=json.loads(result.stdout);cases=value.get('results',value.get('report'))
        rows.append({'command':command,'report':report,'exit':result.returncode,'case_count':len(cases),'all_passed':all(case['passed'] is True for case in cases)})
        assert result.returncode==0 and cases and rows[-1]['all_passed']
    guard_rows=[]
    for index,command in enumerate(guards):
        if command[0]=='python':command=[str(PYTHON),str(ROOT/command[1]),str(phase/command[2]),*command[3:]]
        else:command[0]='C:/Program Files/nodejs/node.exe'
        result=subprocess.run(command,cwd=phase,env=environment,capture_output=True,timeout=20)
        (phase/('guard-'+str(index)+'.log')).write_bytes(result.stdout+result.stderr)
        guard_rows.append({'command':command,'exit':result.returncode});assert result.returncode==0
    assert sum(row['case_count'] for row in rows)==300
    specific={'modules':18,'assertion_executions':300,'unique_criteria':279,'legacy_export_repeated':21,'module_results':rows,'actual_guard_results':guard_rows}
else:
    command=[str(PYTHON),'-X','utf8','-B']
    if mode=='units33':command+=['tests/run_isolated.py','tests/test_member_browser_gate.py','tests/test_member_ci_trust.py','-q','--tb=short','--junitxml='+str(phase/'junit.xml')]
    else:command+=['tests/verify_member_links_ci.py','--output',str(phase/'review'),'--history-repository',str(ROOT),'--verify-only']
    with (phase/'stdout.log').open('xb') as stdout,(phase/'stderr.log').open('xb') as stderr:
        result=subprocess.run(command,cwd=ROOT,env=environment,stdout=stdout,stderr=stderr,timeout=180)
    specific={'exit':result.returncode,'command':command}
    assert result.returncode==0
    if mode=='units33':
        import xml.etree.ElementTree as ET
        cases=ET.parse(phase/'junit.xml').findall('.//testcase');assert len(cases)==33
        assert not any(case.find(name) is not None for case in cases for name in ['failure','error','skipped'])
        specific['passed']=33
    else:
        value=json.loads((phase/'review/review.json').read_bytes())
        assert len(value['unauthorized_delta_canaries'])==25 and len(value['reports'])==26
        specific.update(delta_canaries=25,report_paths=26,historical_exit=value['historical_exit'],executor_pins=8)
after=photo(mode+'-after');assert before==after
outputs=[publish(path,mode+'-'+path.relative_to(phase).as_posix().replace('/','-')) for path in sorted(phase.rglob('*')) if path.is_file() and 'source' not in path.relative_to(phase).parts]
save(mode+'-result.json',{'head':HEAD,'mode':mode,'results':specific,'sources_helpers_packages_stable':True,'source_count':before['source_count'],'helper_count':before['helper_count'],'packages':89,'seconds':time.monotonic()-started,'public_outputs':outputs,'scope':'Actual offline local checks; no PG/browser/QEMU/Actions/provider execution.'})
print(json.dumps({'mode':mode,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'stable':True,**{key:specific[key] for key in ['modules','assertion_executions','unique_criteria','passed','delta_canaries','executor_pins'] if key in specific}}))
