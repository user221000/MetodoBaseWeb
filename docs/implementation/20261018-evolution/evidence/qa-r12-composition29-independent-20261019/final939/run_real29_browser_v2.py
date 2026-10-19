"""Own one loopback listener/one fresh PG DB/one Chrome; close exactly those."""
import ast,shutil,socket,time
from support import *
phase=TEMP/'browser-real29-v2';phase.mkdir(exist_ok=False)
port=8793;origin='http://127.0.0.1:'+str(port)
NODE_MODULES=Path(r'F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
CHROME=Path(r'C:/Program Files/Google/Chrome/Application/chrome.exe')
NODE=Path(shutil.which('node')).resolve()
for name in ['real29_server.py','run_real29_browser.py']:
    ast.parse((OUT/name).read_text(encoding='utf8'))
syntax=subprocess.run([str(NODE),'--check',str(OUT/'real29_browser.cjs')],capture_output=True)
assert syntax.returncode==0
with socket.socket() as probe:probe.bind(('127.0.0.1',port))
def fingerprints(ports,pid=None):
    script='$ErrorActionPreference="Stop"\n$ports=@('+','.join(str(v) for v in ports)+')\n'
    script+='$listeners=@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in $ports } | Select-Object LocalAddress,LocalPort,OwningProcess)\n'
    script+='$taskIds=@($listeners | ForEach-Object { $_.OwningProcess })\n'
    if pid is not None:script+='$taskIds+= '+str(pid)+'\n'
    script+='$processes=@($taskIds | Sort-Object -Unique | ForEach-Object { Get-CimInstance Win32_Process -Filter ("ProcessId="+$_) -ErrorAction SilentlyContinue | Select-Object ProcessId,ParentProcessId,CreationDate,ExecutablePath,CommandLine })\n'
    script+='[pscustomobject]@{listeners=$listeners;processes=$processes} | ConvertTo-Json -Depth 5 -Compress'
    result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',script],capture_output=True,check=True)
    data=json.loads(result.stdout.decode('utf-8-sig'))
    for row in data['processes']:
        row['CommandLine_sha256']=sha(row.pop('CommandLine','').encode())
    return data
foreign_before=fingerprints([8776,port]);assert not any(row['LocalPort']==port for row in foreign_before['listeners'])
def artifact_photo():
    packages={p.relative_to(NODE_MODULES).as_posix():sha(p.read_bytes()) for package in ['playwright-core','axe-core'] for p in sorted((NODE_MODULES/package).rglob('*')) if p.is_file()}
    return {'Node':{'path':str(NODE),'sha256':sha(NODE.read_bytes()),'version':subprocess.check_output([str(NODE),'--version'],text=True).strip()},
            'Chrome':{'path':str(CHROME),'sha256':sha(CHROME.read_bytes())},'Node_dependency_files':packages,
            'browser_source':{name:sha((OUT/name).read_bytes()) for name in ['real29_server.py','real29_browser.cjs','run_real29_browser.py']}}
artifacts_before=artifact_photo();save('browser-artifacts-before.json',artifacts_before)
before=photo('browser-before');save('browser-listeners-before.json',foreign_before)
environment=os.environ.copy();environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1')
for key in ['DATABASE_URL','METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT','PYTEST_XDIST_WORKER']:
    environment.pop(key,None)
server=None;server_exit=None;driver_exit=None;owned_fingerprint=None;started=time.monotonic();failure=None
log=(phase/'fixture.private.log').open('xb')
try:
    server=subprocess.Popen([str(PYTHON),'-X','utf8','-B',str(OUT/'real29_server.py'),'--root',str(ROOT),'--out',str(phase),
        '--config',str(PRIVATE),'--head',HEAD,'--port',str(port)],cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    for _ in range(600):
        if server.poll() is not None:raise RuntimeError('Own fixture exited before startup')
        if (phase/'startup.json').exists():
            marker=json.loads((phase/'startup.json').read_bytes())
            assert marker['fixture']=='r12-real-postgres29' and marker['head']==HEAD and marker['pid']==server.pid and marker['port']==port
            assert marker['executed_revision']==marker['model_target_revision']=='20261019_client_account_links'
            assert marker['application_role_restricted_nonowner'] is True and marker['R12_API_doubles'] is False
            try:
                import urllib.request
                with urllib.request.urlopen(origin+'/auth/accept-client-link',timeout=.5) as response:
                    if response.status==200:break
            except OSError:pass
        time.sleep(.1)
    else:raise TimeoutError('Own real29 startup/readiness timed out')
    owned_fingerprint=fingerprints([port],server.pid);save('browser-owned-running.json',owned_fingerprint)
    assert {row['OwningProcess'] for row in owned_fingerprint['listeners']}=={server.pid}
    assert any(row['ProcessId']==server.pid for row in owned_fingerprint['processes'])
    env=dict(environment,QA_BROWSER_PHASE=str(phase),QA_NODE_MODULES=str(NODE_MODULES),QA_CHROME=str(CHROME))
    with (phase/'driver.private.log').open('xb') as stream:
        driver=subprocess.run([str(NODE),str(OUT/'real29_browser.cjs')],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
    driver_exit=driver.returncode
except BaseException as caught:
    failure=type(caught).__name__
    with (phase/'orchestrator.private.log').open('x',encoding='utf8') as stream:stream.write(failure+': '+str(caught)+'\n')
finally:
    if server is not None and server.poll() is None:
        control=phase/'control.private.json';pending=phase/'stop.pending.private.json'
        pending.write_text(json.dumps({'id':'stop-'+str(server.pid),'action':'stop'})+'\n',encoding='utf8');pending.replace(control)
        try:server_exit=server.wait(timeout=35)
        except subprocess.TimeoutExpired:
            # Preserve all evidence. No termination/drop against uncertain process identity.
            failure=failure or 'OwnedFixtureShutdownTimeout'
    elif server is not None:server_exit=server.returncode
    log.close()
after=photo('browser-after');artifacts_after=artifact_photo();save('browser-artifacts-after.json',artifacts_after)
closed=fingerprints([8776,port],server.pid if server else None);save('browser-listeners-after.json',closed)
foreign_after={'listeners':[row for row in closed['listeners'] if row['LocalPort']==8776],
               'processes':[row for row in closed['processes'] if row['ProcessId'] in {value['OwningProcess'] for value in foreign_before['listeners'] if value['LocalPort']==8776}]}
foreign_original={'listeners':[row for row in foreign_before['listeners'] if row['LocalPort']==8776],
                  'processes':[row for row in foreign_before['processes'] if row['ProcessId'] in {value['OwningProcess'] for value in foreign_before['listeners'] if value['LocalPort']==8776}]}
public_names=['startup.json','http-trace.jsonl','browser-result.json','database-closure.json','final-identities.json']
outputs=[publish(phase/name,'browser-'+name) for name in public_names if (phase/name).exists()]
outputs += [publish(path,'browser-'+path.name) for path in sorted(phase.glob('*.png'))]
closure=json.loads((phase/'database-closure.json').read_bytes()) if (phase/'database-closure.json').exists() else None
browser=json.loads((phase/'browser-result.json').read_bytes()) if (phase/'browser-result.json').exists() else None
result={'head':HEAD,'server_exit':server_exit,'driver_exit':driver_exit,'orchestrator_error_class':failure,'runner_seconds':time.monotonic()-started,
 'source_helpers_packages_stable':before==after,'artifacts_stable':artifacts_before==artifacts_after,'source_count':before['source_count'],
 'helper_count':before['helper_count'],'packages':89,'Node_dependency_file_count':len(artifacts_before['Node_dependency_files']),
 'owned_pid':server.pid if server else None,'owned_pid_and_listener_absent':server is not None and server.poll() is not None and not any(row['LocalPort']==port for row in closed['listeners']) and not any(row['ProcessId']==server.pid for row in closed['processes']),
 'foreign8776_exact_fingerprint_preserved':foreign_after==foreign_original,'database_closure':closure,
 'criteria':{key:browser[key] for key in ['total','passed','expected_total']} if browser else None,'public_outputs':outputs,
 'scope':'Actual migrated29, restricted nonowner app, exact loopback HTTP and actual Chrome UI; only after-commit mail transport double. Synthetic four-meal source/PDF seed. No provider delivery or worker generation demonstrated here; maintained backend phase separate.'}
save('browser-result-summary.json',result)
print(json.dumps({key:result[key] for key in ['head','server_exit','driver_exit','orchestrator_error_class','source_count','helper_count','packages','Node_dependency_file_count','owned_pid_and_listener_absent','foreign8776_exact_fingerprint_preserved','criteria']}))
assert failure is None and server_exit==0 and driver_exit==0
assert before==after and artifacts_before==artifacts_after and result['owned_pid_and_listener_absent'] and result['foreign8776_exact_fingerprint_preserved']
assert closure and closure['count']==1 and closure['all_owned_absent']
assert browser and browser['total']==browser['passed']==browser['expected_total']==16
