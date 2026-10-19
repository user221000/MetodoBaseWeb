"""Close only recorded runtime28 resources; preserve all data and prior receipts."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, re, signal, subprocess, time

ROOT=Path('/home/lab/metodobase-runtime28-network-20261019')
OUT=ROOT/'closure'
assert os.geteuid()==0 and ROOT.resolve()==ROOT and not ROOT.is_symlink()
assert hashlib.sha256((ROOT/'network-contract.json').read_bytes()).hexdigest()=='9d0122561e9e506b23dfa2d090beadc2a498c50eba60d5a3e9c3795c6b3ea85d'
assert hashlib.sha256((ROOT/'firewall-rules.proposed.json').read_bytes()).hexdigest()=='74c12487861887e9d0daff862af1a5efd314ce0bb3bf07b63323e84d077b279d'
assert hashlib.sha256((ROOT/'bounded_tcp_proxy.py').read_bytes()).hexdigest()=='37337f6387f1fb5ce38204bcaa992f63df7c764725696708046d330d96fb557f'
state=json.loads((ROOT/'owned-state.json').read_text())
assert state['network_id']=='595405ad0e9a06b4418296eedb57f8457863e5a4240e4c3fb61beaff7d2fa5e2'
assert state['proxy_pids']=={'pg':2256,'redis':2257}
rules=json.loads((ROOT/'firewall-rules.proposed.json').read_text())
def call(*args,check=True):
    return subprocess.run(args,capture_output=True,text=True,check=check,timeout=40)
def save(name,value):
    p=OUT/name
    with p.open('x') as f:f.write(value if isinstance(value,str) else json.dumps(value,indent=2)+'\n')
    os.chmod(p,0o600)
assert not call('docker','ps','-aq').stdout.strip(), 'Container exists; no cleanup authorized'
network=json.loads(call('docker','network','inspect',state['network_id']).stdout)[0]
assert network['Name']=='metodobase-runtime28-internal' and network['Internal'] and not network['EnableIPv6']
assert network['Labels']=={'metodobase.lab.scope':'runtime28-native-20261019'}
assert not network['Containers'] and network['Options']['com.docker.network.bridge.name']=='mb28int'
for tool,key in [('iptables','ipv4_chain_rules'),('ip6tables','ipv6_chain_rules')]:
    for chain,entries in rules[key].items():
        current=call(tool,'-w','5','-S',chain).stdout.splitlines()
        assert len([line for line in current if line.startswith('-A ')])==len(entries)
        for entry in entries:call(tool,'-w','5','-C',chain,*entry)
for tool,jump in state['inserted_jumps']:call(tool,'-w','5','-C',*jump)
OUT.mkdir(mode=0o700)
save('network.before.json',network)
for tool in ['iptables','ip6tables']:save(tool+'.before.txt',call(tool+'-save','-c').stdout)
save('image-preserved.json',json.loads(call('docker','image','inspect','--format','{{json .Id}}','metodobase-lab:recovery28-bc365c1').stdout))
birth=int(next(line.split()[1] for line in Path('/proc/stat').read_text().splitlines() if line.startswith('btime ')))
created=datetime.fromisoformat(state['created_utc']).timestamp()
handles=[];identities=[]
try:
    for service,pid in state['proxy_pids'].items():
        fd=os.pidfd_open(pid)
        handles.append(fd)
        proc=Path('/proc')/str(pid)
        cmd=(proc/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
        assert cmd==[b'/opt/metodobase-lab/python/bin/python3.12',str(ROOT/'bounded_tcp_proxy.py').encode(),service.encode()]
        assert proc.stat().st_uid==int(call('id','-u','lab').stdout)
        ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])
        start=birth+ticks/os.sysconf('SC_CLK_TCK')
        assert created-2<=start<=created+30
        identities.append({'service':service,'pid':pid,'start_epoch':start,'cmdline_verified':True,'pidfd_held':True})
    for fd in handles:signal.pidfd_send_signal(fd,signal.SIGTERM)
    limit=time.monotonic()+10
    while time.monotonic()<limit:
        if all(not Path('/proc',str(pid)).exists() for pid in state['proxy_pids'].values()):break
        time.sleep(.1)
    assert all(not Path('/proc',str(pid)).exists() for pid in state['proxy_pids'].values())
finally:
    for fd in handles:os.close(fd)
for tool,jump in reversed(state['inserted_jumps']):call(tool,'-w','5','-D',*jump)
for tool,chain in reversed(state['created_chains']):
    call(tool,'-w','5','-F',chain)
    call(tool,'-w','5','-X',chain)
call('docker','network','rm',state['network_id'])
semantic={}
def normalized(text):
    rows=[]
    for row in text.splitlines():
        if row.startswith('#'):continue
        row=re.sub(r'\[[0-9]+:[0-9]+\]','[COUNTERS]',row)
        rows.append(row)
    return rows
for tool in ['iptables','ip6tables']:
    after=call(tool+'-save','-c').stdout
    save(tool+'.after.txt',after)
    assert 'MB28_' not in after and 'mb28int' not in after
    before=(ROOT/(tool+'.before.txt')).read_text()
    semantic[tool]={'equal_ignoring_counters_and_comments':normalized(before)==normalized(after),
                    'initial_rows':normalized(before),'final_rows':normalized(after)}
save('firewall-comparison.json',semantic)
assert call('docker','network','inspect',state['network_id'],check=False).returncode!=0
assert not call('docker','ps','-aq').stdout.strip()
for port in [15483,16379]:assert not call('ss','-H','-lnt',f'sport = :{port}').stdout.strip()
receipt={'finished_utc':datetime.now(timezone.utc).isoformat(),'owned_network_removed':True,'owned_proxy_processes_stopped':identities,
         'owned_firewall_chains_and_jumps_removed':True,'container_count':0,'image_unchanged_preserved':True,
         'firewall_semantic_comparison':{k:v['equal_ignoring_counters_and_comments'] for k,v in semantic.items()},
         'private_raw_and_guest_overlay_preserved':True,'unrelated_firewall_rules_mutated':False}
save('receipt.json',receipt)
print(json.dumps(receipt))
