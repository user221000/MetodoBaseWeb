"""Owned namespace repair and complete credential-free canary; preserves initial red evidence."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, socket, subprocess, time

ROOT = Path('/home/lab/metodobase-runtime28-network-20261019')
OUT = ROOT / 'retry-v2'
OUT.mkdir(mode=0o700, exist_ok=False)
config = json.loads((ROOT / 'retry-v2-inputs.json').read_text())
initial_file = ROOT / 'owned-state.json'
assert hashlib.sha256(initial_file.read_bytes()).hexdigest() == config['initial_state_sha256']
initial = json.loads(initial_file.read_text())
assert initial['network_id'] == '595405ad0e9a06b4418296eedb57f8457863e5a4240e4c3fb61beaff7d2fa5e2'
assert initial['proxy_pids'] == {'pg': 2256, 'redis': 2257}
assert initial['canary_container'] is None and not initial['secret_consumption']
assert hashlib.sha256((ROOT / 'network-contract.json').read_bytes()).hexdigest() == '9d0122561e9e506b23dfa2d090beadc2a498c50eba60d5a3e9c3795c6b3ea85d'
assert hashlib.sha256((ROOT / 'firewall-rules.proposed.json').read_bytes()).hexdigest() == '74c12487861887e9d0daff862af1a5efd314ce0bb3bf07b63323e84d077b279d'
assert hashlib.sha256((ROOT / 'network_canary.py').read_bytes()).hexdigest() == config['canary_sha256']
assert os.geteuid() == 0

def call(*args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check, timeout=30)
def write(name, value):
    p = OUT / name
    p.write_text(value if isinstance(value, str) else json.dumps(value, indent=2) + '\n')
    os.chmod(p, 0o600)
rules = json.loads((ROOT / 'firewall-rules.proposed.json').read_text())
for tool, chainskey, jumpskey in [('iptables', 'ipv4_chain_rules', 'ipv4_jumps_insert_first'), ('ip6tables', 'ipv6_chain_rules', 'ipv6_jumps_insert_first')]:
    for chain, entries in rules[chainskey].items():
        lines = call(tool, '-w', '5', '-S', chain).stdout.splitlines()
        assert len(lines) == 1 + len(entries)
        for entry in entries:
            call(tool, '-w', '5', '-C', chain, *entry)
    for jump in rules[jumpskey]:
        call(tool, '-w', '5', '-C', jump[0], *jump[1:])
assert call('iptables', '-w', '5', '-S', 'INPUT').stdout.splitlines()[1] == '-A INPUT -i mb28int -j MB28_IN'
assert call('iptables', '-w', '5', '-S', 'OUTPUT').stdout.splitlines()[1] == '-A OUTPUT -j MB28_OUT'
assert set(call('iptables', '-w', '5', '-S', 'DOCKER-USER').stdout.splitlines()[1:3]) == {'-A DOCKER-USER -i mb28int -j MB28_FWD', '-A DOCKER-USER -o mb28int -j MB28_FWD'}
assert call('ip6tables', '-w', '5', '-S', 'OUTPUT').stdout.splitlines()[1] == '-A OUTPUT -j MB28_OUT6'
assert not call('docker', 'ps', '-q').stdout.strip()
network = json.loads(call('docker', 'network', 'inspect', initial['network_id']).stdout)[0]
assert network['Internal'] and not network['EnableIPv6'] and not network['Containers']
for service, pid in initial['proxy_pids'].items():
    command = (Path('/proc') / str(pid) / 'cmdline').read_bytes().split(b'\0')
    assert command[:3] == [b'/opt/metodobase-lab/python/bin/python3.12', str(ROOT / 'bounded_tcp_proxy.py').encode(), service.encode()]
write('iptables.before.txt', call('iptables-save', '-c').stdout)
write('ip6tables.before.txt', call('ip6tables-save', '-c').stdout)
body = (ROOT / 'network_canary.py').read_bytes()
loader = "from pathlib import Path;import sys,time\nwhile not Path('/tmp/network28-ready').exists():time.sleep(0.05)\ndata=sys.stdin.buffer.read(" + str(len(body)) + ")\nassert len(data)==" + str(len(body)) + "\nexec(compile(data,'network-canary-original','exec'))"
image = 'sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c'
command = ['docker', 'create', '-i', '--name', 'metodobase-network28-canary-v2',
    '--label', 'metodobase.lab.scope=runtime28-native-20261019',
    '--network', 'metodobase-runtime28-internal', '--ip', '172.30.28.2', '--dns', '127.0.0.1',
    '--dns-opt', 'timeout:1', '--dns-opt', 'attempts:1',
    '--sysctl', 'net.ipv6.conf.all.disable_ipv6=1', '--sysctl', 'net.ipv6.conf.default.disable_ipv6=1',
    '--tmpfs', '/tmp:rw,noexec,nosuid,size=4m,uid=999,gid=999',
    '--read-only', '--user', '999:999', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
    '--no-healthcheck', '--pids-limit', '64', '--memory', '256m', '--entrypoint', 'python', image, '-B', '-c', loader]
cid = call(*command).stdout.strip()
record = {'container_id': cid, 'image_id': image, 'command': command, 'secret_consumption': False, 'product_started': False}
write('state.json', record)
try:
    call('docker', 'start', cid)
    state = json.loads(call('docker', 'inspect', '--format', '{{json .State}}', cid).stdout)
    assert state['Running'] and state['Pid'] > 1
    pid = state['Pid'];target = Path('/proc') / str(pid)
    def identity():
        assert json.loads(call('docker', 'inspect', '--format', '{{json .Id}}', cid).stdout) == cid
        assert json.loads(call('docker', 'inspect', '--format', '{{json .Image}}', cid).stdout) == image
        assert json.loads(call('docker', 'inspect', '--format', '{{json .Config.Labels}}', cid).stdout)['metodobase.lab.scope'] == 'runtime28-native-20261019'
        current = json.loads(call('docker', 'inspect', '--format', '{{json .State}}', cid).stdout)
        assert current['Running'] and current['Pid'] == pid and current['StartedAt'] == state['StartedAt']
        networks = json.loads(call('docker', 'inspect', '--format', '{{json .NetworkSettings.Networks}}', cid).stdout)
        assert set(networks) == {'metodobase-runtime28-internal'} and networks['metodobase-runtime28-internal']['IPAddress'] == '172.30.28.2'
        cgroups = (target / 'cgroup').read_text()
        assert cid in cgroups
        netns = os.readlink(target / 'ns/net')
        assert netns != os.readlink('/proc/self/ns/net')
        birth = (target / 'stat').read_text().rsplit(')', 1)[1].split()[19]
        return {'pid': pid, 'started_at': current['StartedAt'], 'proc_starttime': birth, 'cgroups': cgroups, 'netns': netns, 'networks': networks}
    before_identity = identity()
    before4 = json.loads(call('nsenter', '--target', str(pid), '--net', 'ip', '-j', '-4', 'route', 'show').stdout)
    before6 = json.loads(call('nsenter', '--target', str(pid), '--net', 'ip', '-j', '-6', 'route', 'show').stdout)
    for route in before4:
        if route.get('dst') == 'default':
            assert route.get('gateway') == '172.30.28.1' and route.get('dev') == 'eth0'
            assert identity() == before_identity
            call('nsenter', '--target', str(pid), '--net', 'ip', '-4', 'route', 'del', 'default', 'via', '172.30.28.1', 'dev', 'eth0')
    after4 = json.loads(call('nsenter', '--target', str(pid), '--net', 'ip', '-j', '-4', 'route', 'show').stdout)
    after6 = json.loads(call('nsenter', '--target', str(pid), '--net', 'ip', '-j', '-6', 'route', 'show').stdout)
    assert not any(r.get('dst') == 'default' for r in after4 + after6)
    assert identity() == before_identity
    write('namespace-routes.json', {'identity': before_identity, 'ipv4_before': before4, 'ipv4_after': after4, 'ipv6_before': before6, 'ipv6_after': after6,
                                  'default_route_removed_by_owned_guest_root': True, 'no_host_namespace_mutation': True,
                                  'note': 'Docker20.10 Internal=true still supplied this default route; this additional LAB step is required again for the future runtime container before private stdin.'})
    call('docker', 'exec', '--user', '999:999', cid, 'python', '-B', '-c', "from pathlib import Path;Path('/tmp/network28-ready').touch(exist_ok=False)")
    with (OUT / 'canary.json').open('xb') as stdout, (OUT / 'canary.log').open('xb') as stderr:
        result = subprocess.run(['docker', 'attach', '--sig-proxy=false', cid], input=body, stdout=stdout, stderr=stderr, timeout=180)
    final_state = json.loads(call('docker', 'inspect', '--format', '{{json .State}}', cid).stdout)
    assert not final_state['Running'] and final_state['ExitCode'] == 0 and result.returncode == 0
    canary = json.loads((OUT / 'canary.json').read_text())
    counters = call('iptables', '-w', '5', '-L', 'MB28_IN', '-nvx').stdout
    reject = [line.split() for line in counters.splitlines() if 'REJECT' in line]
    assert len(reject) == 1 and int(reject[0][0]) >= 8
    output_probes = []
    for family, address in [(socket.AF_INET, ('192.0.2.1', 443)), (socket.AF_INET6, ('2001:db8::1', 443))]:
        with socket.socket(family, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            try:
                connection.connect(address)
                raise AssertionError('Unexpected guest external connectivity')
            except OSError as exc:
                output_probes.append({'family': family, 'address': address, 'errno': exc.errno, 'error_type': type(exc).__name__})
    out_counter = call('iptables', '-w', '5', '-L', 'MB28_OUT', '-nvx').stdout
    out_reject = [line.split() for line in out_counter.splitlines() if 'REJECT' in line]
    assert len(out_reject) == 1 and int(out_reject[0][0]) >= 1
    write('counters-and-output-probes.json', {'input_counters': counters, 'output_counters': out_counter,
                                           'ipv6_output_counters': call('ip6tables', '-w', '5', '-L', 'MB28_OUT6', '-nvx').stdout,
                                           'guest_output_probes': output_probes})
    write('iptables.after.txt', call('iptables-save', '-c').stdout)
    write('ip6tables.after.txt', call('ip6tables-save', '-c').stdout)
    record.update(gate_passed=True, finished_utc=datetime.now(timezone.utc).isoformat(),
                  namespace_default_route_removed=True, actual_canary=canary,
                  original_red_evidence_preserved=True, restrictive_gates_and_proxies_left_active=True)
finally:
    actual_id = json.loads(call('docker', 'inspect', '--format', '{{json .Id}}', cid).stdout)
    assert actual_id == cid
    call('docker', 'rm', '-f', cid)
    record['container_removed'] = True
    write('state.json', record)
assert record.get('gate_passed')
print(json.dumps({'gate_passed': True, 'container_removed': True, 'secret_consumption': False,
                  'product_started': False, 'default_route_removed_in_own_namespace': True}), flush=True)
