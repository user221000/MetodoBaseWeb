from pathlib import Path
import ctypes
from ctypes import wintypes
import hashlib,importlib.util,json,os,socket,subprocess,sys,time,traceback,urllib.request,urllib.error

ROOT=Path('F:/mb-qa-browser31-20261020');T=Path(__file__).resolve().parent;P=T/'private'
NODE=Path('C:/Program Files/nodejs/node.exe');CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe');DEPS=Path('F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
sha=lambda data:hashlib.sha256(data).hexdigest()
spec=importlib.util.spec_from_file_location('qa_frozen_resource_library',Path('C:/Users/Consu/AppData/Local/Temp/metodobase-followup34-author-native-mfa35-qa-20261020-v2/launch.py'))
resources=importlib.util.module_from_spec(spec);spec.loader.exec_module(resources);resources.P=P
def status(pid,expected):
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];api.OpenProcess.restype=wintypes.HANDLE
    api.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];api.WaitForSingleObject.restype=wintypes.DWORD
    api.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=api.OpenProcess(0x1000|0x100000,False,pid)
    if not handle:
        error=ctypes.get_last_error();assert error in (87,1168);return {'pid':pid,'birth':expected,'state':'absent'}
    try:
        actual=resources.birth(pid)
        if actual!=expected:return {'pid':pid,'birth':expected,'state':'original_absent_PID_reused'}
        wait=api.WaitForSingleObject(handle,0);assert wait==0,(pid,wait)
        return {'pid':pid,'birth':expected,'state':'terminated_exact_process_object','wait_zero':wait}
    finally:api.CloseHandle(handle)
def snapshot(label,lib):
    data=lib.snapshot(label);data.update({'Node':{'sha256':sha(NODE.read_bytes())},'Chrome':{'sha256':sha(CHROME.read_bytes())},'Python_base':{'path':sys._base_executable,'sha256':sha(Path(sys._base_executable).read_bytes())},'Node_files':{p.relative_to(DEPS).as_posix():sha(p.read_bytes()) for p in sorted(DEPS.rglob('*')) if p.is_file()},'JS_helpers':{p.name:sha(p.read_bytes()) for p in T.glob('*.cjs')}})
    (P/(label+'-full.json')).write_text(json.dumps(data,indent=2),encoding='utf-8');return data

def main():
    assert (T/'preflight.json').exists() and not (P/'before-full.json').exists()
    with socket.socket() as check:check.bind(('127.0.0.1',8802))
    entry=importlib.util.spec_from_file_location('qa_diagnostic_snapshot',Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-nutrition35-saas-20261020/phase.py'));lib=importlib.util.module_from_spec(entry);entry.loader.exec_module(lib);lib.ROOT=ROOT;lib.TASK=T;lib.PRIVATE=P
    before=snapshot('before',lib);lib.pipcheck('before');initial=resources.inventory('before');history=[initial]
    server=child=None;failed=None;report=None;child_identity=None;server_identity=None;worker_identity=None
    env=os.environ.copy();env.update({'TEMP':str(P),'TMP':str(P),'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'});env.pop('QA_OBSERVER_UNIT',None)
    for key in ('METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_DATABASE_URL'):env.pop(key,None)
    try:
        with (P/'server.stdout').open('xb') as output,(P/'server.stderr').open('xb') as error:
            server=subprocess.Popen([sys.executable,'-B','-X','utf8',str(T/'sqlite_server.py')],cwd=ROOT,env=env,stdout=output,stderr=error)
        server_identity={'pid':server.pid,'birth':resources.birth(server.pid)}
        print(json.dumps({'phase':'SQLite35_fixture_starting','source':before['head'],'pid':server.pid,'PG':False}),flush=True)
        limit=time.monotonic()+120
        while not (P/'startup.json').exists():
            if server.poll() is not None or time.monotonic()>limit:raise RuntimeError('No structured SQLite startup')
            time.sleep(.2)
        witness=json.loads((P/'startup.json').read_bytes());assert witness['dialect']=='sqlite' and witness['no_PG_or_RLS_claim'] is True
        assert witness['expected_runtime_revision']==witness['actual_alembic_revision']=='20261020_nutrition_profile'
        assert witness['metadata_table_count']==37 and witness['physical_table_count']==38
        worker_identity={'pid':witness['pid'],'birth':witness['birth']};assert resources.birth(witness['pid'])==witness['birth']
        middle=resources.inventory('startup-chain');history.append(middle)
        if worker_identity['pid']!=server_identity['pid']:
            workers=[row for row in middle['processes'] if row['ProcessId']==worker_identity['pid'] and row['birth']==worker_identity['birth']]
            assert len(workers)==1 and workers[0]['ParentProcessId']==server_identity['pid'] and workers[0]['birth']>=server_identity['birth']
            assert Path(workers[0]['ExecutablePath']).resolve()==Path(sys._base_executable).resolve()
        (P/'worker-generation.json').write_text(json.dumps({'redirector':server_identity,'worker':worker_identity,'parent_generation_verified':True},indent=2),encoding='utf-8')
        limit=time.monotonic()+30
        while True:
            try:
                assert urllib.request.urlopen('http://127.0.0.1:8802/login-gym',timeout=2).status==200;break
            except (urllib.error.URLError,TimeoutError):
                if time.monotonic()>limit or server.poll() is not None:raise
                time.sleep(.2)
        browserenv=env.copy();browserenv.update({'METODOBASE_E2E_DEPENDENCIES':str(DEPS),'CHROME_PATH':str(CHROME),'QA_OBSERVATION_FILE':str(P/'pageerror-observations.ndjson'),'QA_DIAGNOSTIC_OUTPUT':str(P/'output')})
        with (P/'diagnose.stdout').open('xb') as output,(P/'diagnose.stderr').open('xb') as error:
            child=subprocess.Popen([str(NODE),'--require',str(T/'observe.cjs'),str(T/'diagnose.cjs')],cwd=ROOT,env=browserenv,stdout=output,stderr=error)
            child_identity={'pid':child.pid,'birth':resources.birth(child.pid)}
            print(json.dumps({'phase':'minimal_diagnostic_started','pid':child.pid,'original15_replayed':False}),flush=True)
            count=0;limit=time.monotonic()+240
            while child.poll() is None:
                if time.monotonic()>limit:raise TimeoutError('Own diagnostic deadline; no automatic foreign cleanup')
                history.append(resources.inventory('live-'+str(count)));count+=1;time.sleep(1)
        code=child.wait();report=json.loads((P/'output/report.json').read_bytes())
    except BaseException as error:
        failed=type(error).__name__;(P/'launcher-failure.raw').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        if server is not None:
            if server.poll() is None:(P/'stop').write_bytes(b'owned stop\n')
            server_code=server.wait(timeout=45)
    final=resources.inventory('after');history.append(final)
    ids={child_identity['pid']:child_identity['birth']} if child_identity else {}
    own,rejected=resources.own_chrome_rows(history,ids);states=[status(row['pid'],row['birth']) for row in own]
    for identity in (server_identity,worker_identity,child_identity):
        if identity:states.append(status(identity['pid'],identity['birth']))
    old={(row['ProcessId'],row['birth']) for row in initial['processes'] if row['Name'].lower()=='chrome.exe'}
    new={(row['ProcessId'],row['birth']) for row in final['processes'] if row['Name'].lower()=='chrome.exe'};assert new-old==set()
    for row in initial['processes']:
        if row['Name'].lower() in ('chrome.exe','msedge.exe') and row['birth'] is not None:assert resources.birth(row['ProcessId'])==row['birth']
    ports=lambda value:{(row['LocalAddress'],row['LocalPort'],row['OwningProcess']) for row in value['listeners'] if row['LocalPort']==8776}
    assert ports(initial)==ports(final) and not any(row['LocalPort']==8802 for row in final['listeners'])
    (P/'closure.json').write_text(json.dumps({'processes':states,'PG_used':False,'own8802closed':True,'foreign8776_and_browsers_preserved':True,'no_kill':True,'normal_server_exit':server_code,'ambiguous_attributions':rejected},indent=2),encoding='utf-8')
    after=snapshot('after',lib);lib.pipcheck('after');stable={key:before[key]==after[key] for key in before};assert all(stable.values())
    summary={'source_head':before['head'],'diagnostic_report':report,'launcher_failure':failed,'stable':stable,'source_files':len(before['source']),'packages':len(before['packages']),'installed_files':len(before['installed']),'Node_files':len(before['Node_files']),'pip_before':0,'pip_after':0,'PG_used':False,'own_processes_closed':True,'original15_replayed':False,'scope':'Minimal two navigation/boundary scenarios only. Original11 rejection remains unchanged; personal4 not executed by this diagnostic.'}
    (T/'phase-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps({'source':before['head'],'checks':len(report['checks']) if report else 0,'error_classes':report['pageErrors'] if report else [],'launcher_failure':failed,'PG':False,'closure':True,'stable':stable}),flush=True)

if __name__=='__main__':main()
