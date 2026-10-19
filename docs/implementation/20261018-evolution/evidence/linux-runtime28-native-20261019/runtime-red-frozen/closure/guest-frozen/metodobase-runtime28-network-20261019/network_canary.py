import json, os, pathlib, socket, struct, time

def exchange(host, port, payload, limit=128):
    with socket.create_connection((host, port), timeout=8) as connection:
        connection.settimeout(8)
        connection.sendall(payload)
        return connection.recv(limit)

pg = exchange('172.30.28.1', 15483, struct.pack('!II', 8, 80877103), 1)
assert pg in (b'S', b'N'), 'Allowed PostgreSQL proxy did not answer SSLRequest'
redis = exchange('172.30.28.1', 16379, b'*1\r\n$4\r\nPING\r\n')
assert redis == b'+PONG\r\n', 'Allowed Redis proxy did not answer PING'
denied = []
for host, port in [('172.30.28.1', 22), ('172.30.28.1', 6379), ('172.30.28.1', 55483),
                   ('172.30.28.1', 2375), ('10.0.2.2', 55483), ('192.0.2.1', 443)]:
    try:
        with socket.create_connection((host, port), timeout=2):
            raise AssertionError('Unexpected connectivity to forbidden destination')
    except OSError as exc:
        denied.append({'host': host, 'port': port, 'error_type': type(exc).__name__, 'errno': exc.errno})
try:
    socket.getaddrinfo('unresolvable.runtime28.invalid', 443)
    raise AssertionError('Unexpected external DNS resolution')
except socket.gaierror as exc:
    dns = {'query': 'unresolvable.runtime28.invalid', 'failed': True, 'errno': exc.errno}
with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as connection:
    connection.settimeout(2)
    try:
        connection.connect(('2001:db8::1', 443))
        raise AssertionError('Unexpected external IPv6 connectivity')
    except OSError as exc:
        ipv6 = {'failed': True, 'error_type': type(exc).__name__, 'errno': exc.errno}
route = pathlib.Path('/proc/net/route').read_text()
assert not any(row.split()[1] == '00000000' for row in route.splitlines()[1:]), 'Unexpected default route'
assert pathlib.Path('/proc/sys/net/ipv6/conf/all/disable_ipv6').read_text().strip() == '1'
status = pathlib.Path('/proc/self/status').read_text()
assert 'CapEff:\t0000000000000000' in status and 'NoNewPrivs:\t1' in status
assert not pathlib.Path('/var/run/docker.sock').exists()
print(json.dumps({'allowed_postgres_ssl_request': pg.decode(), 'allowed_redis_ping': True,
                  'forbidden_destinations_denied': denied, 'dns': dns, 'ipv6': ipv6,
                  'route': route, 'resolv_conf': pathlib.Path('/etc/resolv.conf').read_text(),
                  'status': status, 'uid': os.getuid(), 'docker_socket_present': False,
                  'scope': 'Protocol and OS network boundary probes without passwords, SQL or product startup.'}, indent=2))
