"""Real current30 browser in one owned UUID, with owned-process closure proof."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from datetime import datetime,timezone

ROOT=Path('F:/mb-r23-focus-qa-20261019')
OUT=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/qa-r23-focus-independent-20261019/addon768')
assert sys.argv[1:]==['--execute-after-root-ack'], 'Resource window ACK required before any Chrome/PG execution'
OUT.mkdir(exist_ok=False)
(OUT/'.gitattributes').write_bytes(b'* -text\n')
TEMP=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r23-focus-independent-20261019')
RUN=TEMP/'r23-addon768-30'
RUN.mkdir(exist_ok=False)
head=subprocess.check_output(['git','--no-replace-objects','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert head=='ee361d5f173ca0e5b748b34be1bff2e8672042e1'
assert not subprocess.check_output(['git','--no-replace-objects','status','--porcelain','--untracked-files=no'],cwd=ROOT).strip()
configuration=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text(encoding='utf-8-sig'))
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def save(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
NODE=Path('C:/Program Files/nodejs/node.exe')
MODULES=Path('F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
assert sha(CHROME.read_bytes())=='6aa5d599bbc3a0b3842af9f44b18fd29989eb3cc21b4b3ec7489e12f36e9962e'
assert sha(NODE.read_bytes())=='ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32'
paths=subprocess.check_output(['git','--no-replace-objects','ls-files','-co','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')[:-1]
paths=sorted(set(name for name in paths if (ROOT/name).is_file()))
module_names=sorted(p.relative_to(MODULES).as_posix() for p in MODULES.rglob('*') if p.is_file())
assert len(module_names)==157
def photo():
    return {'outer_launcher_sha256':sha(Path(__file__).read_bytes()),'sources':{name:sha((ROOT/name).read_bytes()) for name in paths},'addon_browser_sha256':sha((TEMP/'addon768.cjs').read_bytes()),
            'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
            'owned_helpers':{p.name:sha(p.read_bytes()) for p in sorted(OUT.parent.glob('*.py'))},
            'node_modules':{name:sha((MODULES/name).read_bytes()) for name in module_names},
            'tools':{'chrome_sha256':sha(CHROME.read_bytes()),'node_sha256':sha(NODE.read_bytes()),'private_config_sha256':sha(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_bytes())}}
before=photo();save('before.json',before)
assert len(before['packages'])==89
pip_before=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-before.log').write_bytes(pip_before.stdout+pip_before.stderr);assert pip_before.returncode==0
env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',
         QA_CHROME=str(CHROME),QA_NODE_MODULES=str(MODULES))
for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','_METODOBASE_TEST_ROOT']:
    env.pop(key,None)
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:
    env[key]=configuration[key]
with socket.socket() as probe:
    assert probe.connect_ex(('127.0.0.1',8795))!=0
start=datetime.now(timezone.utc).isoformat()
started=time.monotonic()
known={};phase=None;owned_names=[];fixture_pid=None
def processes(filter_expression):
    command="Get-CimInstance Win32_Process -Filter '"+filter_expression+"' | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,@{Name='Created';Expression={$_.CreationDate.ToUniversalTime().ToString('o')}} | ConvertTo-Json -Depth 3 -Compress"
    value=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=15)
    assert value.returncode==0
    if not value.stdout.strip():return []
    rows=json.loads(value.stdout)
    return rows if isinstance(rows,list) else [rows]
from urllib.request import build_opener,HTTPRedirectHandler,Request
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
opener=build_opener(NoRedirect)
foreign_before=processes('Name="chrome.exe"')
fingerprint=lambda rows:sorted([row['ProcessId'],row['ParentProcessId'],row['Created'],Path(row['ExecutablePath']).name if row.get('ExecutablePath') else None] for row in rows)
save('foreign-chrome-before.json',fingerprint(foreign_before))
config_path=RUN/'pg-config.private.json';config_path.write_bytes((json.dumps({key:configuration[key] for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']})+'\n').encode('utf8'))
assert not config_path.read_bytes().startswith(b'\xef\xbb\xbf')
config_sha=sha(config_path.read_bytes())
startup_path=RUN/'startup.json';stop_path=RUN/'owned.stop';browser_out=RUN/'browser'
env.update(METODOBASE_E2E_URL='http://127.0.0.1:8795',FOLLOWUP_NODE_MODULES=str(MODULES),CHROME_PATH=str(CHROME),FOLLOWUP_STARTUP_REPORT=str(startup_path),QA_R23_ROOT=str(ROOT))
fixture=None;node=None;startup=None;error=None;fixture_code=None;node_code=None
parents=set();known={}
def observe():
    if not parents:return
    filters=' OR '.join('ParentProcessId='+str(pid) for pid in sorted(parents))
    rows=processes(filters)
    for row in rows:
        known[(row['ProcessId'],row['Created'])]=row;parents.add(row['ProcessId'])
    (RUN/'observed-processes.private.json').write_text(json.dumps(list(known.values()),indent=2)+'\n')
try:
    with (RUN/'fixture.stdout.raw.log').open('xb') as stdout,(RUN/'fixture.stderr.raw.log').open('xb') as stderr:
        fixture=subprocess.Popen([sys.executable,'-X','utf8','-B','tests/e2e/followup_server.py','--pg-config',str(config_path),'--report',str(startup_path),'--stop-file',str(stop_path),'--port','8795'],cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
        parents.add(fixture.pid)
        print(json.dumps({'phase':'R23-fixture-started','manager_pid':fixture.pid,'port':8795,'head':head}),flush=True)
        while time.monotonic()-started<180:
            observe()
            assert fixture.poll() is None,'Own fixture exited before readiness'
            if startup_path.exists():
                try:startup=json.loads(startup_path.read_bytes())
                except json.JSONDecodeError:startup=None
                if startup:
                    assert startup['runtime_revision']=='20261019_personal_history_index' and startup['model_tables']==29 and startup['actual_tables']==30
                    assert startup['application_role_restricted_nonowner'] is True
                    expected=json.loads((ROOT/'web/database/alembic/schema_targets/20261019_personal_history_index_postgresql.json').read_bytes())['history_order_index']
                    assert json.dumps(startup['history_order_index'],sort_keys=True)==json.dumps(expected,sort_keys=True)
                    assert startup['port']==8795 and re.fullmatch(r'metodobase_test_followup_[0-9a-f]{16}',startup['database'])
                    owned_names=[startup['database']]
                    assert all(sha((ROOT/name).read_bytes())==digest for name,digest in startup['sources'].items())
                    try:
                        with opener.open(Request('http://127.0.0.1:8795/health/ready'),timeout=3) as response:ready=response.status==200
                    except Exception:ready=False
                    if ready:break
            time.sleep(.3)
        else:raise AssertionError('Own fixture readiness deadline')
        print(json.dumps({'phase':'R23-ready-own-UUID','names':owned_names,'schema':30,'model_tables':29,'physical_tables':30}),flush=True)
        with (RUN/'browser.stdout.raw.log').open('xb') as stdout,(RUN/'browser.stderr.raw.log').open('xb') as stderr:
            node=subprocess.Popen([str(NODE),str(TEMP/'addon768.cjs'),str(browser_out)],cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
            parents.add(node.pid)
            while node.poll() is None:
                observe();assert time.monotonic()-started<360,'Owned browser deadline';time.sleep(.3)
            node_code=node.wait()
except Exception as exc:
    error={'class':type(exc).__name__,'message':str(exc)}
finally:
    if fixture is not None:
        stop_path.write_bytes(b'Own cooperative stop\n')
        fixture_code=fixture.wait(timeout=45)
    observe()
end=datetime.now(timezone.utc).isoformat()
chromes=[row for row in known.values() if (row.get('ExecutablePath')or'').lower()==str(CHROME).replace('/','\\').lower()]
profiles=set()
for row in chromes:
    found=re.search(r'--user-data-dir=(?:"([^"]+)"|(\S+))',row.get('CommandLine')or'')
    if found:
        profile=Path(found.group(1)or found.group(2));assert profile.is_relative_to(Path(os.environ['TEMP'])) and profile.name.startswith('playwright_chromiumdev_profile-');profiles.add(profile)
remaining=[]
if known:
    identities=set(known)
    remaining=[row for row in processes(' OR '.join('ProcessId='+str(pid) for pid,_born in identities)) if (row['ProcessId'],row['Created']) in identities]
foreign_after=processes('Name="chrome.exe"');foreign_ids={(row['ProcessId'],row['Created']) for row in foreign_before}
preserved_foreign=[row for row in foreign_after if (row['ProcessId'],row['Created']) in foreign_ids]
save('foreign-chrome-after.json',fingerprint(preserved_foreign));assert fingerprint(preserved_foreign)==fingerprint(foreign_before)
with socket.socket() as probe:listener_closed=probe.connect_ex(('127.0.0.1',8795))!=0
import psycopg2
db_remaining=[]
if owned_names:
    with psycopg2.connect(configuration['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1),connect_timeout=5) as connection,connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION READ ONLY');cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)',(owned_names,));db_remaining=[r[0] for r in cursor.fetchall()]
after=photo();save('after.json',after);assert before==after and sha(config_path.read_bytes())==config_sha
pip_after=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(OUT/'pip-after.log').write_bytes(pip_after.stdout+pip_after.stderr);assert pip_after.returncode==0
closure={'head':head,'start_utc':start,'end_utc':end,'fixture_exit':fixture_code,'browser_exit':node_code,'owned_database_names':owned_names,'remaining_owned_databases':db_remaining,'owned_processes':[{'pid':row['ProcessId'],'created':row['Created'],'parent':row['ParentProcessId'],'executable':Path(row['ExecutablePath']).name if row.get('ExecutablePath')else None} for row in known.values()],'remaining_exact_processes':remaining,'owned_chrome_processes':len(chromes),'owned_chrome_profiles':len(profiles),'owned_profiles_absent':[not p.exists() for p in profiles],'listener8795_closed':listener_closed,'private_utf8_no_BOM_config_SHA256':config_sha,'error':error}
save('resource-closure.json',closure)
assert startup is not None and len(owned_names)==1 and fixture_code==0 and db_remaining==[] and remaining==[] and listener_closed and chromes and len(profiles)==1 and all(not p.exists() for p in profiles)
report=json.loads((browser_out/'report.json').read_bytes())
classification=[];private_values=[configuration[key].encode() for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']]
public_names=['report.json','followup-768.png']
for name in public_names:
    source=browser_out/name
    if not source.exists():continue
    raw=source.read_bytes();assert all(v not in raw for v in private_values)
    target=OUT/'public'/name;target.parent.mkdir(exist_ok=True);target.write_bytes(raw);classification.append({'path':'public/'+name,'RAW_sha256':sha(raw),'redactions':0})
(OUT/'startup.raw.json').write_bytes(startup_path.read_bytes())
for name in ['fixture.stdout.raw.log','fixture.stderr.raw.log','browser.stdout.raw.log','browser.stderr.raw.log']:
    raw=(RUN/name).read_bytes();public=raw
    for value in private_values:public=public.replace(value,b'REDACTED_PRIVATE_URL')
    public=re.sub(rb'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}',b'REDACTED_SYNTHETIC_JWT',public)
    target=name if public==raw else name+'.sanitized';(OUT/target).write_bytes(public);classification.append({'path':target,'RAW_sha256':sha(raw),'published_sha256':sha(public),'RAW_exact':public==raw})
save('output-classification.json',classification)
passed=sum(r.get('passed')is True for r in report['results'])
summary={'head':head,'executed_revision':'20261019_personal_history_index','passed':passed,'total':len(report['results']),'browser_exit':node_code,'fixture_exit':fixture_code,'seconds':time.monotonic()-started,'sources':len(paths),'helpers':len(before['owned_helpers']),'packages':89,'Node_dependency_files':157,'sources_helpers_packages_tools_config_stable':True,'private_config_UTF8_no_BOM':True,'addon_browser_sha256':sha((TEMP/'addon768.cjs').read_bytes()),'startup_delta':report['startup_delta'],'page_errors':report['pageErrors'],'screens':report['screens'],'owned_UUID_absent':db_remaining==[],'owned_Chrome_profile_closed':all(not p.exists() for p in profiles),'listener8795_closed':listener_closed,'scope':'One independent additive768 CSSpx Chrome/control/reflow/scoped-axe check; extra own UUID and required fresh PUT state setup only. Original8 not repeated. No API doubles, whole-page axe, full R23 assignment/contact persistence, provider, worker, Actions/Linux or SLO claim.'}
save('summary.json',summary);print(json.dumps(summary),flush=True)
assert node_code==0 and error is None and passed==len(report['results'])==3 and not report['pageErrors'] and report['startup_delta']=={} and len(report['screens'])==1
