"""Own image lifecycle; secret bytes only flow from stdin to the container pipe."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, subprocess, sys, time

ROOT = Path('/home/lab/metodobase-runtime28-product-a781deb39fd74441baa6a37c1a0cab40')
PRIVATE = ROOT / 'private'
IMAGE = 'sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c'
NETWORK = 'metodobase-runtime28-internal'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('action',choices=['prepare','attach','status','stop'])
parser.add_argument('mode',choices=['migrate','web'])
args=parser.parse_args()
assert os.geteuid()==0
PRIVATE.mkdir(mode=0o700,exist_ok=True);os.chmod(PRIVATE,0o700)
inputs=json.loads((ROOT/'inputs.json').read_text())
for rel,digest in inputs['files'].items():
    path=ROOT/rel
    assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT.resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
def call(*command,check=True,timeout=30):
    return subprocess.run(command,capture_output=True,text=True,check=check,timeout=timeout)
def output(name,value):
    p=ROOT/name;p.write_text(json.dumps(value,indent=2)+'\n');os.chmod(p,0o600)
def inspect(cid,field):
    return json.loads(call('docker','inspect','--format','{{json '+field+'}}',cid).stdout)
statefile=ROOT/(args.mode+'-state.json')
if args.action=='prepare':
    assert not statefile.exists()
    green=Path('/home/lab/metodobase-runtime28-network-20261019/retry-v3-target55484/state.json')
    assert hashlib.sha256(green.read_bytes()).hexdigest()==inputs['network_gate_state_sha256']
    gate=json.loads(green.read_text());assert gate['gate_passed'] and gate['container_removed']
    network=json.loads(call('docker','network','inspect',NETWORK).stdout)[0]
    assert network['Id']=='595405ad0e9a06b4418296eedb57f8457863e5a4240e4c3fb61beaff7d2fa5e2'
    assert network['Internal'] and not network['EnableIPv6'] and not network['Containers']
    assert call('iptables','-w','5','-S','INPUT').stdout.splitlines()[1]=='-A INPUT -i mb28int -j MB28_IN'
    assert call('iptables','-w','5','-S','OUTPUT').stdout.splitlines()[1]=='-A OUTPUT -j MB28_OUT'
    assert set(call('iptables','-w','5','-S','DOCKER-USER').stdout.splitlines()[1:3])=={'-A DOCKER-USER -i mb28int -j MB28_FWD','-A DOCKER-USER -o mb28int -j MB28_FWD'}
    assert call('ip6tables','-w','5','-S','OUTPUT').stdout.splitlines()[1]=='-A OUTPUT -j MB28_OUT6'
    loader="from pathlib import Path;import runpy,sys,time\nwhile not Path('/tmp/runtime28-ready').exists():time.sleep(.05)\nsys.argv=['/qa/private_stdin_entrypoint_v2.py',"+repr(args.mode)+"]\nrunpy.run_path('/qa/private_stdin_entrypoint_v2.py',run_name='__main__')"
    command=['docker','create','-i','--name','metodobase-runtime28-'+args.mode,
       '--label','metodobase.lab.scope=runtime28-native-20261019','--label','metodobase.lab.uuid=a781deb39fd74441baa6a37c1a0cab40',
       '--network',NETWORK,'--ip','172.30.28.2','--dns','127.0.0.1','--dns-opt','timeout:1','--dns-opt','attempts:1',
       '--sysctl','net.ipv6.conf.all.disable_ipv6=1','--sysctl','net.ipv6.conf.default.disable_ipv6=1',
       '--read-only','--user','999:999','--cap-drop','ALL','--security-opt','no-new-privileges',
       '--tmpfs','/tmp:rw,noexec,nosuid,size=64m,uid=999,gid=999','--tmpfs','/data:rw,noexec,nosuid,size=128m,uid=999,gid=999',
       '--mount','type=bind,src='+str(ROOT/'helpers')+',dst=/qa,readonly',
       '--no-healthcheck','--pids-limit','256','--memory','768m','--cpus','2',
       '--entrypoint','python',IMAGE,'-B','-c',loader]
    cid=call(*command).stdout.strip()
    record={'container_id':cid,'mode':args.mode,'image_id':IMAGE,'command':command,'private_stdin_sent':False,'container_removed':False}
    output(statefile.name,record)
    call('docker','start',cid)
    initial=inspect(cid,'.State');assert initial['Running'] and initial['Pid']>1
    pid=initial['Pid'];proc=Path('/proc')/str(pid)
    def identity():
        assert inspect(cid,'.Id')==cid and inspect(cid,'.Image')==IMAGE
        labels=inspect(cid,'.Config.Labels');assert labels['metodobase.lab.uuid']=='a781deb39fd74441baa6a37c1a0cab40'
        state=inspect(cid,'.State');assert state['Pid']==pid and state['Running'] and state['StartedAt']==initial['StartedAt']
        nets=inspect(cid,'.NetworkSettings.Networks');assert set(nets)=={NETWORK} and nets[NETWORK]['IPAddress']=='172.30.28.2'
        cgroup=(proc/'cgroup').read_text();assert cid in cgroup
        ns=os.readlink(proc/'ns/net');assert ns!=os.readlink('/proc/self/ns/net')
        return {'pid':pid,'started_at':state['StartedAt'],'proc_starttime':(proc/'stat').read_text().rsplit(')',1)[1].split()[19],
                'cgroups':cgroup,'netns':ns,'networks':nets}
    ident=identity()
    before4=json.loads(call('nsenter','--target',str(pid),'--net','ip','-j','-4','route','show').stdout)
    before6=json.loads(call('nsenter','--target',str(pid),'--net','ip','-j','-6','route','show').stdout)
    for route in before4:
        if route.get('dst')=='default':
            assert route['gateway']=='172.30.28.1' and route['dev']=='eth0' and identity()==ident
            call('nsenter','--target',str(pid),'--net','ip','-4','route','del','default','via','172.30.28.1','dev','eth0')
    after4=json.loads(call('nsenter','--target',str(pid),'--net','ip','-j','-4','route','show').stdout)
    after6=json.loads(call('nsenter','--target',str(pid),'--net','ip','-j','-6','route','show').stdout)
    assert not any(r.get('dst')=='default' for r in after4+after6) and identity()==ident
    checks="import hashlib,json,pathlib;expected="+repr(inputs['product_sources'])+";actual={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in expected};assert actual==expected;print(json.dumps(actual))"
    source_hashes=json.loads(call('docker','exec','--user','999:999',cid,'python','-B','-c',checks).stdout)
    output(args.mode+'-namespace.json',{'identity':ident,'ipv4_before':before4,'ipv4_after':after4,'ipv6_before':before6,'ipv6_after':after6,
                                      'private_stdin_sent':False,'product_source_hashes':source_hashes})
    # Execute the complete original credential-free gate inside this exact runtime
    # namespace before it is allowed to receive the private frame.
    with (ROOT/'network_canary.py').open('rb') as stream:
        gate=subprocess.run(['docker','exec','-i','--user','999:999',cid,'python','-B','-'],stdin=stream,capture_output=True,timeout=120)
    assert gate.returncode==0, 'Exact runtime namespace network gate failed'
    output(args.mode+'-network-gate.json',json.loads(gate.stdout))
    call('docker','exec','--user','999:999',cid,'python','-B','-c',"from pathlib import Path;Path('/tmp/runtime28-ready').touch(exist_ok=False)")
    host=inspect(cid,'.HostConfig')
    record.update(prepared=True,identity=ident,network_gate_before_stdin=True,
                  flags={k:host[k] for k in ['NetworkMode','ReadonlyRootfs','CapDrop','SecurityOpt','Binds','Memory','PidsLimit']})
    output(statefile.name,record)
    print(json.dumps({'prepared':True,'mode':args.mode,'container_id':cid,'network_gate_before_stdin':True}),flush=True)
elif args.action=='attach':
    record=json.loads(statefile.read_text());cid=record['container_id']
    assert record['prepared'] and record['network_gate_before_stdin'] and not record['private_stdin_sent']
    assert inspect(cid,'.Id')==cid and inspect(cid,'.Image')==IMAGE and inspect(cid,'.State')['Running']
    stdout=(PRIVATE/(args.mode+'.stdout.raw.log')).open('xb');stderr=(PRIVATE/(args.mode+'.stderr.raw.log')).open('xb')
    os.chmod(PRIVATE/(args.mode+'.stdout.raw.log'),0o600);os.chmod(PRIVATE/(args.mode+'.stderr.raw.log'),0o600)
    if args.mode=='migrate':
        result=subprocess.run(['docker','attach','--sig-proxy=false',cid],stdin=sys.stdin.buffer,stdout=stdout,stderr=stderr,timeout=420)
        actual=inspect(cid,'.State');assert not actual['Running'] and actual['ExitCode']==0 and result.returncode==0
        record.update(private_stdin_sent=True,exit=actual['ExitCode'],migration_completed=True)
    else:
        process=subprocess.Popen(['docker','attach','--sig-proxy=false',cid],stdin=sys.stdin.buffer,stdout=stdout,stderr=stderr,start_new_session=True)
        record.update(private_stdin_sent=True,attach_pid=process.pid)
    stdout.close();stderr.close();output(statefile.name,record)
    print(json.dumps({'mode':args.mode,'container_id':cid,'private_stdin_sent':True,'migration_completed':record.get('migration_completed',False)}),flush=True)
elif args.action=='status':
    record=json.loads(statefile.read_text());cid=record['container_id']
    assert inspect(cid,'.Id')==cid and inspect(cid,'.Image')==IMAGE
    print(json.dumps({'mode':args.mode,'container_id':cid,'state':inspect(cid,'.State')}))
elif args.action=='stop':
    record=json.loads(statefile.read_text());cid=record['container_id']
    assert inspect(cid,'.Id')==cid and inspect(cid,'.Image')==IMAGE
    assert inspect(cid,'.Config.Labels')['metodobase.lab.uuid']=='a781deb39fd74441baa6a37c1a0cab40'
    if inspect(cid,'.State')['Running']:
        call('docker','stop','--time','30',cid,timeout=45)
    record['final_state']=inspect(cid,'.State')
    call('docker','rm',cid);record['container_removed']=True;output(statefile.name,record)
    print(json.dumps({'mode':args.mode,'container_removed':True,'final_state':record['final_state']}))
