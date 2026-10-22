from pathlib import Path
import ctypes
from ctypes import wintypes
import argparse,hashlib,importlib.util,json,os,re,socket,subprocess,sys,time
import urllib.error,urllib.request

ROOT=Path(__file__).resolve().parents[2];TASK=None;P=None
sys.path.insert(0,str(ROOT))
PROFILE=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
NODE=Path('C:/Program Files/nodejs/node.exe');CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
DEPS=Path('F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
ORIGIN='http://127.0.0.1:8802'
SELECTIONS={
    'new18':(('native37_account_notifications_qa_v4',18),),
    'r22addon2':(('native37_onboarding_r22_qa_v5',2),),
    'all20':(('native37_account_notifications_qa_v4',18),('native37_onboarding_r22_qa_v5',2)),
    'current35':(('mfa_ui_browser',11),('mfa_personal_browser',4),('native37_account_notifications_qa_v4',18),('native37_onboarding_r22_qa_v5',2)),
}
sha=lambda data:hashlib.sha256(data).hexdigest()

def selection_contract(selection,preflight,sql_ack):
    assert selection in SELECTIONS
    expected_groups=([15,18,2] if selection=='current35' else [minimum for _driver,minimum in SELECTIONS[selection]])
    for value in (preflight,sql_ack):
        assert value['selection']==selection
        assert type(value['expected_groups']) is list and all(type(item) is int for item in value['expected_groups'])
        assert value['expected_groups']==expected_groups
    return expected_groups

def progress_contract(file,expected):
    raw=file.read_bytes()
    assert raw.endswith(b'\n') and type(expected) is int and expected in (2,18)
    rows=[json.loads(line) for line in raw.splitlines()]
    assert len(rows)==expected*2
    previous=-1
    for index,row in enumerate(rows):
        assert set(row)=={'sequence','group','kind','elapsed_ms'}
        assert all(type(row[key]) is int for key in ('sequence','group','elapsed_ms'))
        assert row['sequence']==index+1 and row['group']==index//2+1
        assert row['kind']==('START' if index%2==0 else 'PASS')
        assert row['elapsed_ms']>=previous and row['elapsed_ms']>=0
        previous=row['elapsed_ms']
    return {'groups':expected,'events':len(rows),'complete':True,'raw_sha256':sha(raw)}
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
def status(pid,expected):
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];api.OpenProcess.restype=wintypes.HANDLE
    api.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];api.WaitForSingleObject.restype=wintypes.DWORD
    api.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=api.OpenProcess(0x1000|0x100000,False,pid)
    if not handle:
        error=ctypes.get_last_error();assert error in (87,1168);return {'pid':pid,'birth':expected,'state':'absent'}
    try:
        actual=birth(pid)
        if actual!=expected:return {'pid':pid,'birth':expected,'state':'original_absent_PID_reused'}
        wait=api.WaitForSingleObject(handle,0);assert wait==0,(pid,wait)
        return {'pid':pid,'birth':expected,'state':'terminated_exact_process_object','wait_zero':wait}
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
    return lib.photograph(ROOT,TASK,label,PROFILE,NODE,CHROME,DEPS)

def witness(value):
    assert value['fixture']=='native-browser-account37-restricted-PG'
    assert value['origin']==ORIGIN and value['dialect']=='postgresql'
    assert value['expected_runtime_revision']==value['actual_alembic_revision']=='20261020_account_security'
    assert value['metadata_table_count']==41 and value['physical_table_count']==42
    assert value['FORCE_RLS_tables']==32 and value['role_flags_and_owner_membership']==[False]*5
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
    global TASK,P,PROFILE,NODE,CHROME,DEPS
    parser=argparse.ArgumentParser(description='Windows independent native37 functional diagnostic; no Linux/Actions claim')
    parser.add_argument('--private-root',type=Path,required=True)
    parser.add_argument('--pg-config',type=Path,required=True)
    parser.add_argument('--node',type=Path,default=NODE)
    parser.add_argument('--chrome',type=Path,default=CHROME)
    parser.add_argument('--dependencies',type=Path,default=DEPS)
    parser.add_argument('--selection',choices=tuple(SELECTIONS),default='all20')
    args=parser.parse_args();TASK=args.private_root.resolve();P=TASK/'private';PROFILE=args.pg_config.resolve();NODE=args.node.resolve();CHROME=args.chrome.resolve();DEPS=args.dependencies.resolve()
    assert os.name=='nt' and P.is_dir() and not P.is_symlink()
    assert TASK.name.startswith('metodobase-account37-author-pg-')
    preflight=json.loads((TASK/'native-preflight.json').read_bytes())
    sql_ack=json.loads((TASK/'native-sql-ack.json').read_bytes())
    expected_groups=selection_contract(args.selection,preflight,sql_ack)
    assert sql_ack['granted'] is True and sql_ack['UUIDs']==1
    assert sql_ack['source_head']==preflight['source_head'] and sql_ack['launcher_sha256']==sha(Path(__file__).read_bytes())
    assert preflight['source_head']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert sha(PROFILE.read_bytes())==preflight['profile_sha256']
    assert (TASK/'native-preflight.json').is_file() and not (P/'before-full.json').exists()
    assert not list((TASK/'leases').iterdir())
    with socket.socket() as check:check.bind(('127.0.0.1',8802))
    from tests.e2e import native37_environment_qa as lib
    assert Path(lib.__file__).resolve().is_relative_to(ROOT)
    before=fingerprint_snapshot('before',lib);lib.pipcheck(ROOT,TASK,'before')
    assert before['source']==preflight['source_RAW_sha256']
    assert before['packages']==preflight['packages']
    assert sha(json.dumps(before['installed'],sort_keys=True,separators=(',',':')).encode())==preflight['installed_map_sha256']
    initial=inventory('before');histories=[initial];node_ids={};reports=[]
    server=None;server_result=None;failure=None;server_identity=None;produced=None;stop_timeout=False
    server_out=(P/'server.stdout').open('xb');server_err=(P/'server.stderr').open('xb')
    try:
        env=os.environ.copy();env.update({'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'})
        server=subprocess.Popen([sys.executable,'-B','-X','utf8','tests/e2e/native37_postgres_server_qa_v6.py','--pg-config',str(PROFILE),'--private',str(P),'--port','8802'],cwd=ROOT,env=env,stdout=server_out,stderr=server_err)
        server_identity={'pid':server.pid,'birth':birth(server.pid)};put('server-identity.json',server_identity)
        print(json.dumps({'phase':'fixture_starting','source':before['head'],'own_pid':server.pid,'planned_UUID_count':1}),flush=True)
        deadline=time.monotonic()+120
        while not (P/'startup.json').exists():
            if server.poll() is not None:raise RuntimeError('Fixture exited before structured startup')
            if time.monotonic()>deadline:raise TimeoutError('Fixture structured startup deadline')
            time.sleep(.2)
        produced=json.loads((P/'startup.json').read_bytes());witness(produced)
        assert birth(produced['pid'])==produced['process_birth']
        chain_inventory=inventory('startup-process-chain');histories.append(chain_inventory)
        if produced['pid']!=server_identity['pid']:
            actual=[row for row in chain_inventory['processes'] if row['ProcessId']==produced['pid'] and row['birth']==produced['process_birth']]
            redirectors=[row for row in chain_inventory['processes'] if row['ProcessId']==server_identity['pid'] and row['birth']==server_identity['birth']]
            assert len(actual)==len(redirectors)==1
            assert actual[0]['ParentProcessId']==server_identity['pid']
            assert actual[0]['birth']>=redirectors[0]['birth']
            assert Path(actual[0]['ExecutablePath']).resolve()==Path(sys._base_executable).resolve()
            assert 'tests/e2e/native37_postgres_server_qa_v6.py' in actual[0]['CommandLine'].replace('\\','/')
            assert str(P).replace('\\','/') in actual[0]['CommandLine'].replace('\\','/')
            put('venv-worker-generation.json',{'root':server_identity,'worker':{'pid':produced['pid'],'birth':produced['process_birth']},'exact_parent_generation_verified':True,'actual_executable_is_frozen_python_base':True})
        else:
            assert produced['process_birth']==server_identity['birth']
        deadline=time.monotonic()+30
        while True:
            try:
                with urllib.request.urlopen(ORIGIN+'/login-gym',timeout=2) as response:
                    assert response.status==200
                break
            except (urllib.error.URLError,TimeoutError):
                if server.poll() is not None or time.monotonic()>deadline:raise
                time.sleep(.2)
        put('readiness.json',{'request':'GET login-gym loopback','status':200,'excluded_from_browser_groups':True,'structured_witness_validated':True})
        lease_rows=[json.loads(path.read_bytes()) for path in sorted((TASK/'leases').glob('lease-*.json'))]
        assert len(lease_rows)==1 and lease_rows[0]['state']=='created'
        put('created-lease-at-startup.json',lease_rows[0])
        ram=[]
        for sample in range(2):
            command="$x=Get-CimInstance Win32_OperatingSystem; [pscustomobject]@{utc=[DateTime]::UtcNow.ToString('o');physical_GiB=[math]::Round($x.FreePhysicalMemory/1MB,3);virtual_GiB=[math]::Round($x.FreeVirtualMemory/1MB,3)} | ConvertTo-Json -Compress"
            result=subprocess.check_output(['powershell','-NoProfile','-Command',command]);put('RAM-'+str(sample)+'.raw.json',result)
            memory=json.loads(result);assert memory['physical_GiB']>=2.4;ram.append(memory)
            if sample==0:time.sleep(2)
        put('ready-before-Chrome.json',{'source_head':before['head'],'launcher_sha256':sha(Path(__file__).read_bytes()),'startup_sha256':sha((P/'startup.json').read_bytes()),'schema37_witness_validated':True,'UUID_created_receipt_immediate_primitive':True,'RAM':ram,'Chrome_started':False,'lease_count':1,'selection':args.selection,'expected_groups':expected_groups})
        print(json.dumps({'phase':'ready_waiting_ROOT_Chrome_ACK','source':before['head'],'RAM':ram,'Chrome_started':False}),flush=True)
        deadline=time.monotonic()+300
        while not (TASK/'native-chrome-ack.json').exists():
            if server.poll() is not None:raise RuntimeError('Fixture stopped while awaiting ROOT Chrome ACK')
            if time.monotonic()>deadline:raise TimeoutError('No ROOT Chrome ACK; stop own fixture without browser')
            time.sleep(.25)
        ack=json.loads((TASK/'native-chrome-ack.json').read_bytes());assert ack['source_head']==before['head'] and ack['launcher_sha256']==sha(Path(__file__).read_bytes()) and ack['granted'] is True
        selection_contract(args.selection,preflight,ack)
        assert ack['startup_sha256']==sha((P/'startup.json').read_bytes())
        assert not (P/'stop').exists()
        for driver,minimum in SELECTIONS[args.selection]:
            target=P/('native37-own-output' if minimum==18 else ('native37-r22-output' if minimum==2 else driver+'-output'));assert not target.exists()
            browser_env=env.copy();browser_env.update({'METODOBASE_E2E_DEPENDENCIES':str(DEPS),'CHROME_PATH':str(CHROME),
                'METODOBASE_E2E_URL':ORIGIN,'METODOBASE_EVIDENCE_BATCH':'qa-native37-'+driver,'TEMP':str(P),'TMP':str(P),'QA37_PRIVATE':str(P),
                'NATIVE31_BROWSER_OUTPUT':str(target),'NATIVE31_PRODUCER_WITNESS':str(P/'startup.json')})
            with (P/(driver+'.stdout')).open('xb') as output,(P/(driver+'.stderr')).open('xb') as error:
                command=([str(NODE),'tests/e2e/native37_mfa_compat_qa_v6.cjs',driver] if minimum in (11,4) else [str(NODE),'tests/e2e/'+driver+'.cjs'])
                child=subprocess.Popen(command,cwd=ROOT,env=browser_env,stdout=output,stderr=error)
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
                put(driver+'-child-exit.json',{'pid':child.pid,'birth':identity['birth'],'exit_code':code})
            report=json.loads((target/'report.json').read_bytes())
            reports.append({'driver':driver,'exit_code':code,'complete':report.get('complete'),'checks':len(report.get('checks',[])),
                'screens':len(report.get('screens',[])),'report_sha256':sha((target/'report.json').read_bytes()),'scope':('Original MFA groups replayed through authentic37 cookie companion; not new groups' if minimum in (11,4) else ('18 groups with explicit serialized password ACK order' if minimum==18 else 'Two additive R22 preparation/profile navigation groups'))})
            print(json.dumps({'phase':'native_driver_finished',**reports[-1]}),flush=True)
            assert code==0 and report['complete'] is True and len(report['checks'])==minimum
            if minimum in (11,4):
                assert report['browser_session_composition']['producer_witness']['sha256']==sha((P/'startup.json').read_bytes())
            else:
                assert report['producer_witness_sha256']==sha((P/'startup.json').read_bytes())
                assert report['progress']=={'completed':minimum,'expected':minimum,'terminal_failure':False,'complete':True}
                journal=P/('native37-groups.private.ndjson' if minimum==18 else 'native37-r22-groups.private.ndjson')
                put(driver+'-progress-validated.json',progress_contract(journal,minimum))
            assert report.get('pageErrors')==[]
    except BaseException as error:
        failure=type(error).__name__
        import traceback
        put('launcher-failure-trace.raw',traceback.format_exc().encode())
        put('launcher-failure.json',{'error_class':failure,'phase':'See private original stdout/stderr; no response payload projected'})
    finally:
        if server is not None:
            if server.poll() is None:(P/'stop').write_bytes(b'owned stop request\n')
            try:server_result=server.wait(timeout=45)
            except subprocess.TimeoutExpired:
                put('server-stop-timeout.json',{'pid':server.pid,'birth':server_identity['birth'],'still_same_process':birth(server.pid)==server_identity['birth'],'no_kill_or_FORCEDROP_performed':True})
                stop_timeout=True
        server_out.close();server_err.close()
    if stop_timeout:
        inventory('retained-after-timeout')
        retained=fingerprint_snapshot('retained-after-timeout',lib);lib.pipcheck(ROOT,TASK,'retained-after-timeout')
        stable={key:before[key]==retained[key] for key in before}
        assert all(stable.values())
        put('phase-retained-timeout-summary.json',{'verdict':'REJECTED','normal_server_exit':False,
            'server_stop_timeout':True,'manual_cleanup_required':True,'owned_resource_retained':True,
            'no_termination_DROP_cancellation_performed':True,'reports':reports,'stable':stable})
        print(json.dumps({'phase':'REJECTED_retained_own_server_timeout','no_automatic_retry':True}),flush=True)
        return 1
    assert server_result==0, 'Fixture must exit zero; no native acceptance with finalizer failure'
    close=json.loads((P/'close.json').read_bytes())
    assert close['normal_owned_context_closed'] is True
    final=inventory('after');histories.append(final)
    owned,rejected=own_chrome_rows(histories,node_ids)
    process_statuses=[status(row['pid'],row['birth']) for row in owned]
    for pid,started in node_ids.items():process_statuses.append(status(pid,started))
    if server_identity:process_statuses.append(status(server_identity['pid'],server_identity['birth']))
    if produced:process_statuses.append(status(produced['pid'],produced['process_birth']))
    assert all(row['state'] in {'absent','terminated_exact_process_object','original_absent_PID_reused'} for row in process_statuses)
    remaining=[]
    old_chrome={(row['ProcessId'],row['birth']) for row in initial['processes'] if row['Name'].lower()=='chrome.exe'}
    new_chrome={(row['ProcessId'],row['birth']) for row in final['processes'] if row['Name'].lower()=='chrome.exe'}
    assert new_chrome-old_chrome==set(),'New browser identity remains; no automatic cleanup of unowned processes'
    for row in initial['processes']:
        if row['Name'].lower() not in {'chrome.exe','msedge.exe'}:continue
        if row['birth'] is not None:assert birth(row['ProcessId'])==row['birth'],'Pre-existing foreign browser changed independently; no cleanup permitted'
    foreign_before={(row['ProcessId'],row['birth']) for row in initial['processes'] if row['Name'].lower() in {'chrome.exe','msedge.exe'} and row['birth'] is not None}
    foreign_after={(row['ProcessId'],row['birth']) for row in final['processes'] if row['Name'].lower() in {'chrome.exe','msedge.exe'} and row['birth'] is not None}
    assert foreign_before<=foreign_after
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
    put('resource-closure.json',{'normal_server_exit':server_result,'process_statuses':process_statuses,'owned_UUIDs':[row['database'] for row in leases],
        'zero_sessions_before_normal_DROP':True,'fresh_independent_absence':True,'owned_Chrome_processes_observed':owned,
        'rejected_generation_attributions':rejected,'owned_Chrome_remaining':remaining,'foreign_browsers_preserved':True,
        'foreign_listener8776_preserved':True,'own_port8802_closed':True,'no_forced_DROP_or_foreign_cancellation':True})
    after=fingerprint_snapshot('after',lib);lib.pipcheck(ROOT,TASK,'after')
    stable={key:before[key]==after[key] for key in before};assert all(stable.values()),[key for key,ok in stable.items() if not ok]
    summary={'source_head':before['head'],'selection':args.selection,'expected_groups':expected_groups,'reports':reports,'launcher_failure_class':failure,'server_exit':server_result,
        'stable':stable,'source_files':len(before['source']),'packages':len(before['packages']),'installed_files':len(before['installed']),
        'Node_files':len(before['node_files']),'pip_before':0,'pip_after':0,'owned_UUID_count':1,'normal_owned_closure':True,
        'scope':('Explicit current Main37 runtime with CSS fix; original11+4 MFA replay then18 account/notifications then2 R22 groups on one dedicated UUID; current35 is accepted only if all four raw reports, finalizers and resource gates pass.' if args.selection=='current35' else 'Explicit current Main37 runtime; unchanged finite new18, r22addon2 or all20 selection. Original15 MFA are not selected.')+' Current37 restricted PG/cookie HTTP, named real response delivery holds/loss and local mail/GIS/Stripe SDK doubles. No provider delivery, Actions, Linux, deployment, global WCAG, capacity or SLO claim.'}
    (TASK/'phase-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary),flush=True)
    return 0 if failure is None else 1

if __name__=='__main__':raise SystemExit(main())
