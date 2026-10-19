from pathlib import Path
import hashlib,importlib.metadata,json,os,socket,subprocess,sys,time
from urllib.request import urlopen
ROOT=Path(r'F:\mb-r25-qa-ui-20261019');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
PHASE=TEMP/'metodobase-r25-qa-ui-layout-before-20261019'
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/qa-r25-ui-layout-before-independent-20261019'
NODE=Path(r'C:\Program Files\nodejs\node.exe');CHROME=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
MODULES=Path(r'F:\MetodoBaseWeb-execution-20261018\tests\e2e\node_modules')
SERVER=TEMP/'metodobase-r25-qa-browser-server.py';BROWSER=TEMP/'metodobase-r25-qa-layout.cjs'
SHA=lambda raw:hashlib.sha256(raw).hexdigest()
def dump(path,data):
    with path.open('x',encoding='utf8',newline='\n') as stream:json.dump(data,stream,indent=2);stream.write('\n')
def ps(command):return subprocess.check_output(['powershell','-NoProfile','-Command',command],text=True,encoding='utf8')
def processes():
    values=json.loads(ps('Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,CreationDate,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3'))
    return {str(row['ProcessId']):row for row in values}
def fingerprint(pid,inventory):
    row=inventory[str(pid)].copy();parent=inventory.get(str(row['ParentProcessId']))
    row['executable_sha256']=SHA(Path(row['ExecutablePath']).read_bytes()) if row['ExecutablePath'] else None
    row['parent_identity']=None if parent is None else {key:parent[key] for key in ('ProcessId','ParentProcessId','CreationDate','ExecutablePath','CommandLine')}
    return row
def photo():
    paths=subprocess.check_output(['git','ls-files','-z','--','web','api','core','config','db_bootstrap.py'],cwd=ROOT).decode().split('\0')[:-1]
    return {'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'tracked_status':subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True),
        'runtime_raw_sha256':{name:SHA((ROOT/name).read_bytes()) for name in paths},
        'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions() if d.metadata['Name']),
        'binaries':{str(p):SHA(p.read_bytes()) for p in (Path(sys.executable),NODE,CHROME)},
        'driver_raw_sha256':{p.name:SHA(p.read_bytes()) for p in (SERVER,BROWSER,Path(__file__))},
        'pip_check':subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True).returncode,
        'node_package_json_sha256':{str(p.relative_to(MODULES)):SHA(p.read_bytes()) for p in MODULES.rglob('package.json')}}
free=int(ps('(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory').strip())*1024
assert free>=int(2.4*1024**3),'Need at least2.4GiB free before our one Chrome; no process started'
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT).strip()
PHASE.mkdir(exist_ok=False);OUT.mkdir(exist_ok=False);(OUT/'.gitattributes').write_bytes(b'* -text\n')
before=photo();dump(PHASE/'before.private.json',before);assert before['head']=='b7f8e129251dfd5216f811ba77d0b6183ca76735'
initial=processes();dump(PHASE/'processes-before.private.json',initial)
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
log=(PHASE/'fixture.private.log').open('xb')
server=subprocess.Popen([sys.executable,'-X','utf8','-B',str(SERVER),'--phase',str(PHASE),'--root',str(ROOT),'--port',str(port)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
node=None;owned=[];node_tree={};receipt={'source_head':before['head'],'port':port,'ram_before_bytes':free,'completed':False}
try:
    for index in range(1800):
        assert server.poll() is None,'Fixture stopped before startup; private log preserved'
        if (PHASE/'startup.private.json').exists():
            try:
                with urlopen('http://127.0.0.1:'+str(port)+'/health/ready',timeout=1) as response:
                    if response.status==200:break
            except OSError:pass
        time.sleep(.1)
    else:raise TimeoutError('Fixture readiness')
    inventory=processes();owned=[fingerprint(int(pid),inventory) for pid,row in inventory.items() if row['ProcessId']==server.pid or row['ParentProcessId']==server.pid]
    dump(PHASE/'server-owned.private.json',owned)
    marker=json.loads((PHASE/'startup.private.json').read_bytes());assert marker['pid'] in [row['ProcessId'] for row in owned]
    assert marker['revision']=='20261019_personal_progress' and marker['model_tables']==33 and marker['physical_tables']==34
    env=dict(os.environ,QA_R25_PHASE=str(PHASE),QA_R25_PUBLIC=str(OUT),QA_SOURCE_HEAD=before['head'],QA_NODE_MODULES=str(MODULES),QA_CHROME=str(CHROME))
    browser_log=(PHASE/'browser.private.log').open('xb')
    node=subprocess.Popen([str(NODE),str(BROWSER)],cwd=ROOT,env=env,stdout=browser_log,stderr=subprocess.STDOUT)
    dump(PHASE/'node-owned.private.json',fingerprint(node.pid,processes()))
    deadline=time.monotonic()+600
    while node.poll() is None and time.monotonic()<deadline:
        inventory=processes();members={node.pid}
        changed=True
        while changed:
            additions={row['ProcessId'] for row in inventory.values() if row['ParentProcessId'] in members}
            changed=not additions.issubset(members);members.update(additions)
        for pid in members:
            if str(pid) in inventory:
                row=inventory[str(pid)];key=str(pid)+':'+str(row['CreationDate'])
                if key not in node_tree:node_tree[key]=fingerprint(pid,inventory)
        time.sleep(1)
    if node.poll() is None:raise TimeoutError('Owned Node/browser still running; retained for attributed recovery')
    receipt['browser_exit']=node.returncode;browser_log.close();dump(PHASE/'node-browser-tree.private.json',node_tree)
    assert receipt['browser_exit']==0,'Browser criteria failed; original artifacts preserved'
    receipt['completed']=True
except BaseException as error:receipt['failure_class']=type(error).__name__
finally:
    if node is not None and node.poll() is None:
        receipt['node_still_running']=True
        # No broad kill or process signal: explicit ownership recovery remains.
    if server.poll() is None:
        inventory=processes();dump(PHASE/'server-before-cooperative-stop.private.json',[fingerprint(row['ProcessId'],inventory) for row in owned if str(row['ProcessId']) in inventory])
        index=0
        while (PHASE/('control-'+str(index)+'.private.json')).exists():index+=1
        dump(PHASE/('control-'+str(index)+'.private.json'),{'action':'stop'})
        try:server.wait(timeout=45)
        except subprocess.TimeoutExpired:receipt['server_still_running']=True
    receipt['server_exit']=server.poll();log.close()
    with socket.socket() as sock:sock.settimeout(.5);receipt['listener_closed']=sock.connect_ex(('127.0.0.1',port))!=0
    final=processes();dump(PHASE/'processes-after.private.json',final)
    own_left=[]
    for pid,row in final.items():
        if pid in initial and row['CreationDate']==initial[pid]['CreationDate']:continue
        if row['ProcessId']==server.pid or row['ParentProcessId']==server.pid or (node and (row['ProcessId']==node.pid or row['ParentProcessId']==node.pid)):
            own_left.append({'pid':row['ProcessId'],'creation':row['CreationDate']})
    receipt['direct_owned_processes_remaining']=own_left
    receipt['observed_node_browser_generations']=len(node_tree)
    receipt['observed_node_browser_generations_remaining']=[key for key,row in node_tree.items() if str(row['ProcessId']) in final and final[str(row['ProcessId'])]['CreationDate']==row['CreationDate']]
    after=photo();dump(PHASE/'after.private.json',after);receipt['source_packages_binaries_drivers_node_metadata_equal']=before==after
    receipt['runtime_source_count']=len(before['runtime_raw_sha256']);receipt['distribution_metadata_count']=len(before['packages']);receipt['node_package_metadata_count']=len(before['node_package_json_sha256'])
    receipt['closure_file_present']=(PHASE/'closure.private.json').exists()
    receipt['scope']='Cooperative uvicorn stop via own private control, actual listener absence; browser/context close returned. Source photo covers tracked runtime prefixes plus bootstrap; full tracked tree separately covered phase one. No forced signals or RAM erasure claim.'
    if receipt['completed']:
        assert receipt['listener_closed'] and receipt['server_exit']==0 and not own_left and not receipt['observed_node_browser_generations_remaining'] and before==after and receipt['closure_file_present']
    dump(OUT/'browser-receipt.json',receipt)
    for name,source in [('browser-driver.cjs',BROWSER),('server-driver.py',SERVER),('runner.py',Path(__file__))]:
        with (OUT/name).open('xb') as stream:stream.write(source.read_bytes())
print(json.dumps(receipt))
sys.exit(0 if receipt['completed'] else 1)
