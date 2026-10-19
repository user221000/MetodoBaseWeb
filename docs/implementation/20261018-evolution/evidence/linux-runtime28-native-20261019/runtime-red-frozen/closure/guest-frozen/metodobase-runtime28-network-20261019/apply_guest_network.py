"""Owned guest network/proxy/canary only; no credentials or application startup."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, ipaddress, json, os, socket, subprocess, sys, time

ROOT = Path('/home/lab/metodobase-runtime28-network-20261019')
assert ROOT.is_dir() and (ROOT / 'inputs.json').is_file()
inputs = json.loads((ROOT / 'inputs.json').read_text())
contract_path = ROOT / 'network-contract.json'
rules_path = ROOT / 'firewall-rules.proposed.json'
assert hashlib.sha256(contract_path.read_bytes()).hexdigest() == '9d0122561e9e506b23dfa2d090beadc2a498c50eba60d5a3e9c3795c6b3ea85d'
assert hashlib.sha256(rules_path.read_bytes()).hexdigest() == '74c12487861887e9d0daff862af1a5efd314ce0bb3bf07b63323e84d077b279d'
for name, digest in inputs['files'].items():
    p = ROOT / name
    assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT.resolve())
    assert hashlib.sha256(p.read_bytes()).hexdigest() == digest
rules = json.loads(rules_path.read_text())
contract = json.loads(contract_path.read_text())
assert os.geteuid() == 0

def call(*args, text=True, check=True):
    return subprocess.run(args, capture_output=True, text=text, check=check, timeout=30)

def write(name, value):
    p = ROOT / name
    if isinstance(value, str):
        p.write_text(value)
    else:
        p.write_text(json.dumps(value, indent=2) + '\n')
    os.chmod(p, 0o600)

assert not call('docker', 'ps', '-q').stdout.strip()
assert call('ip', '-j', 'link', 'show', 'mb28int', check=False).returncode != 0
ids = call('docker', 'network', 'ls', '-q').stdout.split()
inventory = json.loads(call('docker', 'network', 'inspect', *ids).stdout)
wanted = ipaddress.ip_network('172.30.28.0/28')
for network in inventory:
    assert network['Name'] != 'metodobase-runtime28-internal'
    for ipam in network.get('IPAM', {}).get('Config') or []:
        subnet = ipam.get('Subnet')
        if subnet and ':' not in subnet:
            assert not wanted.overlaps(ipaddress.ip_network(subnet))
routes = json.loads(call('ip', '-j', '-4', 'route').stdout)
for row in routes:
    dest = row.get('dst', 'default')
    if dest != 'default':
        assert not wanted.overlaps(ipaddress.ip_network(dest, strict=False))
connections = call('ss', '-H', '-ntp', 'state', 'established').stdout
for line in connections.splitlines():
    fields = line.split()
    # ss omits the state field when explicitly selected: recv/send/local/peer/process.
    endpoints = [s for s in fields if ':' in s and not s.startswith('users:')]
    assert len(endpoints) >= 2
    local, peer = endpoints[0], endpoints[1]
    if local.startswith(('127.', '[::1]')) and peer.startswith(('127.', '[::1]')):
        continue
    assert local.endswith(':22') and peer.startswith('10.0.2.2:'), 'Unowned external established connection'
for host, port in [('172.30.28.1', 15483), ('172.30.28.1', 16379)]:
    # No bridge exists yet: ensure no wildcard/other existing listener uses these ports.
    assert not call('ss', '-H', '-lnt', f'sport = :{port}').stdout.strip()
assert call('ss', '-H', '-lnt', 'sport = :55483').stdout.strip()
assert call('ss', '-H', '-lnt', 'sport = :6379').stdout.strip()
for tool, key in [('iptables', 'ipv4_chain_rules'), ('ip6tables', 'ipv6_chain_rules')]:
    for chain in rules[key]:
        assert call(tool, '-w', '5', '-S', chain, check=False).returncode != 0, 'Firewall chain collision'
assert call('iptables', '-w', '5', '-S', 'DOCKER-USER').returncode == 0
write('iptables.before.txt', call('iptables-save', '-c').stdout)
write('ip6tables.before.txt', call('ip6tables-save', '-c').stdout)
write('preflight.json', {'networks': inventory, 'routes': routes, 'established_connections': connections,
                         'reviewed_contract_sha256': hashlib.sha256(contract_path.read_bytes()).hexdigest()})
state = {'created_utc': datetime.now(timezone.utc).isoformat(), 'network_id': None,
         'created_chains': [], 'inserted_jumps': [], 'proxy_pids': {}, 'canary_container': None,
         'product_started': False, 'secret_consumption': False}
write('owned-state.json', state)

try:
    state['network_id'] = call('docker', 'network', 'create', '--driver', 'bridge', '--internal',
        '--subnet', '172.30.28.0/28', '--gateway', '172.30.28.1',
        '--opt', 'com.docker.network.bridge.name=mb28int',
        '--opt', 'com.docker.network.bridge.enable_ip_masquerade=false',
        '--label', 'metodobase.lab.scope=runtime28-native-20261019', 'metodobase-runtime28-internal').stdout.strip()
    write('owned-state.json', state)
    inspected = json.loads(call('docker', 'network', 'inspect', state['network_id']).stdout)[0]
    assert inspected['Internal'] is True and inspected['EnableIPv6'] is False
    assert inspected['Options']['com.docker.network.bridge.name'] == 'mb28int'
    write('network.json', inspected)
    for tool, chainskey, jumpskey in [('iptables', 'ipv4_chain_rules', 'ipv4_jumps_insert_first'),
                                      ('ip6tables', 'ipv6_chain_rules', 'ipv6_jumps_insert_first')]:
        for chain, entries in rules[chainskey].items():
            call(tool, '-w', '5', '-N', chain)
            state['created_chains'].append([tool, chain]);write('owned-state.json', state)
            for entry in entries:
                call(tool, '-w', '5', '-A', chain, *entry)
        for jump in rules[jumpskey]:
            call(tool, '-w', '5', '-I', jump[0], '1', *jump[1:])
            state['inserted_jumps'].append([tool, jump]);write('owned-state.json', state)
    # Proxies need no credentials and are deliberately non-root.
    uid = int(call('id', '-u', 'lab').stdout)
    gid = int(call('id', '-g', 'lab').stdout)
    os.chmod(ROOT, 0o755)
    os.chmod(ROOT / 'bounded_tcp_proxy.py', 0o555)
    for service in ['pg', 'redis']:
        log = (ROOT / (service + '-proxy.log')).open('xb')
        os.chmod(ROOT / (service + '-proxy.log'), 0o600)
        p = subprocess.Popen(['/opt/metodobase-lab/python/bin/python3.12', str(ROOT / 'bounded_tcp_proxy.py'), service],
                             stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             user=uid, group=gid, extra_groups=[], start_new_session=True)
        log.close()
        state['proxy_pids'][service] = p.pid;write('owned-state.json', state)
        time.sleep(0.5)
        assert p.poll() is None, service + ' proxy failed'
    write('listeners.json', {'listeners': call('ss', '-H', '-lntp').stdout})
    before_counters = call('iptables', '-w', '5', '-L', 'MB28_IN', '-nvx').stdout
    image = contract['image_id']
    command = ['docker', 'create', '-i', '--name', 'metodobase-network28-canary',
        '--label', 'metodobase.lab.scope=runtime28-native-20261019',
        '--network', 'metodobase-runtime28-internal', '--ip', '172.30.28.2',
        '--dns', '127.0.0.1', '--dns-opt', 'timeout:1', '--dns-opt', 'attempts:1',
        '--sysctl', 'net.ipv6.conf.all.disable_ipv6=1', '--sysctl', 'net.ipv6.conf.default.disable_ipv6=1',
        '--read-only', '--user', '999:999', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
        '--no-healthcheck', '--pids-limit', '64', '--memory', '256m', '--entrypoint', 'python', image, '-B', '-']
    cid = call(*command).stdout.strip()
    state['canary_container'] = cid;write('owned-state.json', state)
    with (ROOT / 'network_canary.py').open('rb') as stdin, (ROOT / 'canary.json').open('xb') as stdout, (ROOT / 'canary.log').open('xb') as stderr:
        result = subprocess.run(['docker', 'start', '-a', '-i', cid], stdin=stdin, stdout=stdout, stderr=stderr, timeout=180)
    canary_state = json.loads(call('docker', 'inspect', '--format', '{{json .State}}', cid).stdout)
    assert canary_state['ExitCode'] == result.returncode
    call('docker', 'rm', cid)
    state['canary_container'] = None;write('owned-state.json', state)
    assert result.returncode == 0, 'Network canary failed; preserve logs and gates'
    canary = json.loads((ROOT / 'canary.json').read_text())
    after_counters = call('iptables', '-w', '5', '-L', 'MB28_IN', '-nvx').stdout
    rejected = [line.split() for line in after_counters.splitlines() if 'REJECT' in line]
    assert len(rejected) == 1 and int(rejected[0][0]) >= 4
    write('input-counters.json', {'before': before_counters, 'after': after_counters})
    # This addresses OUTPUT used by host-side DNS forwarding, not just container routes.
    external = []
    for family, destination in [(socket.AF_INET, ('192.0.2.1', 443)), (socket.AF_INET6, ('2001:db8::1', 443))]:
        with socket.socket(family, socket.SOCK_STREAM) as test:
            test.settimeout(2)
            try:
                test.connect(destination)
                raise AssertionError('Unexpected guest external connectivity')
            except OSError as exc:
                external.append({'family': family, 'destination': destination, 'errno': exc.errno, 'error_type': type(exc).__name__})
    output_counters = call('iptables', '-w', '5', '-L', 'MB28_OUT', '-nvx').stdout
    rejected = [line.split() for line in output_counters.splitlines() if 'REJECT' in line]
    assert len(rejected) == 1 and int(rejected[0][0]) >= 1
    write('guest-output-probes.json', {'probes': external, 'ipv4_counters': output_counters,
                                      'ipv6_counters': call('ip6tables', '-w', '5', '-L', 'MB28_OUT6', '-nvx').stdout})
    write('iptables.after.txt', call('iptables-save', '-c').stdout)
    write('ip6tables.after.txt', call('ip6tables-save', '-c').stdout)
    state['gate_passed'] = True;state['finished_utc'] = datetime.now(timezone.utc).isoformat();write('owned-state.json', state)
    print(json.dumps({'network_gate_passed': True, 'network_id': state['network_id'], 'proxy_pids': state['proxy_pids'],
                      'allowed_protocols': ['PostgreSQL SSLRequest without authentication', 'Redis PING'],
                      'forbidden_destination_attempts_denied': len(canary['forbidden_destinations_denied']),
                      'secret_consumption': False, 'product_started': False}), flush=True)
except Exception as exc:
    state['failure_type'] = type(exc).__name__;state['failure'] = str(exc);write('owned-state.json', state)
    # Preserve restrictive gates and explicit ownership state for controlled repair/teardown.
    raise
