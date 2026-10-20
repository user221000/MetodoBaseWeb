from pathlib import Path
import ctypes
from ctypes import wintypes
import hashlib,importlib.util,json,os,re,socket,subprocess,sys,time
import urllib.error,urllib.request

ROOT=Path('F:/mb-qa-browser31-20261020');TASK=Path(__file__).resolve().parent;P=TASK/'private'
PROFILE=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
NODE=Path('C:/Program Files/nodejs/node.exe');CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
DEPS=Path('F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
ORIGIN='http://127.0.0.1:8802'
sha=lambda data:hashlib.sha256(data).hexdigest()
def put(name,value):
    target=P/name;assert not target.exists(),name
    target.write_bytes(value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode())
def birth(pid):
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];api.OpenProcess.restype=wintypes.HANDLE
    api.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4;api.GetProcessTimes.restype=wintypes.BOOL
    api.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=api.OpenProcess(0x1000,False,int(pid))
    if not handle:return None
    try:
        created,exited,kernel,user=(wintypes.FILETIME() for _ in range(4))
        if not api.GetProcessTimes(handle,*[ctypes.byref(row) for row in (created,exited,kernel,user)]):return None
        return (created.dwHighDateTime<<32)|created.dwLowDateTime
    finally:api.CloseHandle(handle)
def inventory(label):
    script="""$rows=@(Get-CimInstance Win32_Process -Filter \"Name='chrome.exe' OR Name='msedge.exe' OR Name='python.exe' OR Name='node.exe'\" | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,@{Name='CreatedUTC';Expression={$_.CreationDate.ToUniversalTime().ToString('o')}}); $ports=@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object {$_.LocalPort -in 8776,8802} | Select-Object LocalAddress,LocalPort,OwningProcess); @{processes=$rows;listeners=$ports}|ConvertTo-Json -Depth 6 -Compress"""
    result=subprocess.run(['powershell','-NoProfile','-Command',script],capture_output=True)
    assert result.returncode==0
    value=json.loads(result.stdout.decode('utf-8-sig',errors='replace'))
    for row in value['processes']:row['birth']=birth(row['ProcessId'])
    put(label+'-inventory.raw',result.stdout+result.stderr);put(label+'-inventory.json',value)
    return value
def fingerprint_snapshot(label,lib):
    value=lib.snapshot(label)
    value.update({'profile_sha256':sha(PROFILE.read_bytes()),'node':{'path':str(NODE),'sha256':sha(NODE.read_bytes())},
        'chrome':{'path':str(CHROME),'sha256':sha(CHROME.read_bytes())},
        'node_files':{p.relative_to(DEPS).as_posix():sha(p.read_bytes()) for p in sorted(DEPS.rglob('*')) if p.is_file()},
        'fixture_sha256':sha((ROOT/'tests/e2e/mfa_browser35_postgres_server.py').read_bytes()),
        'launcher_sha256':sha(Path(__file__).read_bytes())})
    put(label+'-full.json',value);return value
def witness(value):
    assert value['fixture']=='native-browser-mfa35-restricted-PG'
    assert value['origin']==ORIGIN and value['dialect']=='postgresql'
    assert value['expected_runtime_revision']==value['actual_alembic_revision']=='20261020_nutrition_profile'
    assert value['metadata_table_count']==37 and value['physical_table_count']==38
    assert value['FORCE_RLS_tables']==28 and value['role_flags_and_owner_membership']==[False]*5
    assert value['application_role_restricted_nonowner'] is True
    assert value['fixture_pool_size']==5 and value['fixture_max_overflow']==0
    assert value['history_order_index']['columns']==['gym_id','id_cliente','fecha_generacion','id']
    # The server already compares the entire index object to immutable exact30.
    assert value['history_order_index']['indoption']==[0,0,1,1]
def own_chrome_rows(inventories,node_identities):
    known={}
    for item in inventories:
        for row in item['processes']:
            if row.get('birth') is not None:known[(row['ProcessId'],row['birth'])]=row
    own=[];rejected=[]
    for identity,row in known.items():
        if row['Name'].lower()!='chrome.exe':continue
        command=row.get('CommandLine') or ''
        match=re.search(r'--user-data-dir=(?:"([^"]+)"|(\S+))',command)
        if not match:continue
        profile=Path(match.group(1) or match.group(2)).resolve()
        if not profile.is_relative_to(P):continue
        current=row;chain=[];seen=set();valid=False
        while current['ProcessId'] not in seen:
            seen.add(current['ProcessId']);chain.append({'pid':current['ProcessId'],'birth':current['birth']})
            parent=current['ParentProcessId']
            if parent in node_identities:
                parent_birth=node_identities[parent]
                if current['birth']>=parent_birth:valid=True;chain.append({'pid':parent,'birth':parent_birth})
                break
            candidates=[other for (pid,started),other in known.items() if pid==parent and started<=current['birth']]
            if len(candidates)!=1:break
            current=candidates[0]
        record={'pid':identity[0],'birth':identity[1],'profile':str(profile),'parent_generation_chain':chain}
        (own if valid else rejected).append(record)
    return own,rejected

def main():
    assert (TASK/'preflight-current.json').is_file() and not (P/'before-full.json').exists()
    assert not list((TASK/'leases').iterdir())
    with socket.socket() as check:check.bind(('127.0.0.1',8802))
    spec=importlib.util.spec_from_file_location('qa_native35_snapshot',Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-nutrition35-saas-20261020/phase.py'))
    lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib);lib.ROOT=ROOT;lib.TASK=TASK;lib.PRIVATE=P
    before=fingerprint_snapshot('before',lib);lib.pipcheck('before')
    initial=inventory('before');histories=[initial];node_ids={};reports=[]
    server=None;server_result=None;failure=None
    server_out=(P/'server.stdout').open('xb');server_err=(P/'server.stderr').open('xb')
    try:
        env=os.environ.copy();env.update({'TEMP':str(P),'TMP':str(P),'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'})
        server=subprocess.Popen([sys.executable,'-B','-X','utf8','tests/e2e/mfa_browser35_postgres_server.py','--pg-config',str(PROFILE),'--private',str(P),'--port','8802'],cwd=ROOT,env=env,stdout=server_out,stderr=server_err)
        server_identity={'pid':server.pid,'birth':birth(server.pid)};put('server-identity.json',server_identity)
        print(json.dumps({'phase':'fixture_starting','source':before['head'],'own_pid':server.pid,'planned_UUID_count':1}),flush=True)
        deadline=time.monotonic()+120
        while not (P/'startup.json').exists():
            if server.poll() is not None:raise RuntimeError('Fixture exited before structured startup')
            if time.monotonic()>deadline:raise TimeoutError('Fixture structured startup deadline')
            time.sleep(.2)
        produced=json.loads((P/'startup.json').read_bytes());witness(produced)
        assert produced['pid']==server_identity['pid'] and produced['process_birth']==server_identity['birth']
        deadline=time.monotonic()+30
        while True:
            try:
                response=urllib.request.urlopen(ORIGIN+'/login-gym',timeout=2)
                assert response.status==200;break
            except (urllib.error.URLError,TimeoutError):
                if server.poll() is not None or time.monotonic()>deadline:raise
                time.sleep(.2)
        put('readiness.json',{'request':'GET login-gym loopback','status':200,'excluded_from_browser_groups':True,'structured_witness_validated':True})
        for driver,minimum in [('mfa_ui_browser',11),('mfa_personal_browser',4)]:
            target=P/(driver+'-output');assert not target.exists()
            browser_env=env.copy();browser_env.update({'METODOBASE_E2E_DEPENDENCIES':str(DEPS),'CHROME_PATH':str(CHROME),
                'METODOBASE_E2E_URL':ORIGIN,'METODOBASE_EVIDENCE_BATCH':'qa-native35-'+driver,
                'NATIVE31_BROWSER_OUTPUT':str(target),'NATIVE31_PRODUCER_WITNESS':str(P/'startup.json')})
            with (P/(driver+'.stdout')).open('xb') as output,(P/(driver+'.stderr')).open('xb') as error:
                child=subprocess.Popen([str(NODE),'tests/e2e/browser_native_compat31.cjs',driver],cwd=ROOT,env=browser_env,stdout=output,stderr=error)
                identity={'pid':child.pid,'birth':birth(child.pid)};node_ids[child.pid]=identity['birth'];put(driver+'-node-identity.json',identity)
                print(json.dumps({'phase':'native_driver_started','driver':driver,'pid':child.pid}),flush=True)
                deadline=time.monotonic()+420;counter=0
                while child.poll() is None:
                    if time.monotonic()>deadline:
                        put(driver+'-timeout.json',{'pid':child.pid,'birth':identity['birth'],'still_same_process':birth(child.pid)==identity['birth'],'automatic_foreign_cleanup':False})
                        raise TimeoutError('Native driver deadline; exact identity retained for coordinated own cleanup')
                    histories.append(inventory(driver+'-live-'+str(counter)));counter+=1
                    time.sleep(1)
                code=child.wait()
            report=json.loads((target/'report.json').read_bytes())
            reports.append({'driver':driver,'exit_code':code,'complete':report.get('complete'),'checks':len(report.get('checks',[])),
                'screens':len(report.get('screens',[])),'report_sha256':sha((target/'report.json').read_bytes()),'scope':'Original groups replayed through current cookie companion; not newly invented unique groups'})
            print(json.dumps({'phase':'native_driver_finished',**reports[-1]}),flush=True)
            assert code==0 and report['complete'] is True and len(report['checks'])==minimum
            assert report['browser_session_composition']['producer_witness']['sha256']==sha((P/'startup.json').read_bytes())
            assert report.get('pageErrors')==[]
    except BaseException as error:
        failure=type(error).__name__
        put('launcher-failure.json',{'error_class':failure,'phase':'See private original stdout/stderr; no response payload projected'})
    finally:
        if server is not None:
            if server.poll() is None:(P/'stop').write_bytes(b'owned stop request\n')
            try:server_result=server.wait(timeout=45)
            except subprocess.TimeoutExpired:
                put('server-stop-timeout.json',{'pid':server.pid,'birth':server_identity['birth'],'still_same_process':birth(server.pid)==server_identity['birth'],'no_kill_or_FORCEDROP_performed':True})
                raise
        server_out.close();server_err.close()
    final=inventory('after');histories.append(final)
    owned,rejected=own_chrome_rows(histories,node_ids)
    remaining=[row for row in owned if birth(row['pid'])==row['birth']]
    assert remaining==[]
    old_chrome={(row['ProcessId'],row['birth']) for row in initial['processes'] if row['Name'].lower()=='chrome.exe'}
    new_chrome={(row['ProcessId'],row['birth']) for row in final['processes'] if row['Name'].lower()=='chrome.exe'}
    assert new_chrome-old_chrome==set(),'New browser identity remains; no automatic cleanup of unowned processes'
    for row in initial['processes']:
        if row['Name'].lower() not in {'chrome.exe','msedge.exe'}:continue
        if row['birth'] is not None:assert birth(row['ProcessId'])==row['birth'],'Pre-existing foreign browser changed independently; no cleanup permitted'
    old_port={(r['LocalAddress'],r['LocalPort'],r['OwningProcess']) for r in initial['listeners'] if r['LocalPort']==8776}
    new_port={(r['LocalAddress'],r['LocalPort'],r['OwningProcess']) for r in final['listeners'] if r['LocalPort']==8776}
    assert old_port==new_port and not any(r['LocalPort']==8802 for r in final['listeners'])
    leases=[json.loads(path.read_bytes()) for path in sorted((TASK/'leases').glob('lease-*.json'))]
    assert len(leases)==1
    assert all(row['state']=='closed_absent' and row['sessions_before_drop']==0 and row['absence_verified']=='fresh_control_connection' for row in leases)
    import psycopg2
    profile=json.loads(PROFILE.read_bytes());url=profile.get('METODOBASE_TEST_MIGRATOR_URL',profile.get('migrator_url'))
    with psycopg2.connect(url.replace('postgresql+psycopg2://','postgresql://',1)) as control,control.cursor() as cursor:
        for row in leases:
            cursor.execute('SELECT count(*) FROM pg_database WHERE datname=%s',(row['database'],));assert cursor.fetchone()[0]==0
            cursor.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=%s',(row['database'],));assert cursor.fetchone()[0]==0
    put('resource-closure.json',{'normal_server_exit':server_result,'owned_UUIDs':[row['database'] for row in leases],
        'zero_sessions_before_normal_DROP':True,'fresh_independent_absence':True,'owned_Chrome_processes_observed':owned,
        'rejected_generation_attributions':rejected,'owned_Chrome_remaining':remaining,'foreign_browsers_preserved':True,
        'foreign_listener8776_preserved':True,'own_port8802_closed':True,'no_forced_DROP_or_foreign_cancellation':True})
    after=fingerprint_snapshot('after',lib);lib.pipcheck('after')
    stable={key:before[key]==after[key] for key in before};assert all(stable.values()),[key for key,ok in stable.items() if not ok]
    summary={'source_head':before['head'],'reports':reports,'launcher_failure_class':failure,'server_exit':server_result,
        'stable':stable,'source_files':len(before['source']),'packages':len(before['packages']),'installed_files':len(before['installed']),
        'Node_files':len(before['node_files']),'pip_before':0,'pip_after':0,'owned_UUID_count':1,'normal_owned_closure':True,
        'scope':'Fresh native original MFA groups, current35 actual restricted PG/cookie HTTP. Named delivery/error holds and Stripe SDK response synthetic; no providers, Actions, Linux, deployment, global WCAG, capacity or SLO claim.'}
    (TASK/'phase-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary),flush=True)
    return 0 if failure is None else 1

if __name__=='__main__':raise SystemExit(main())
