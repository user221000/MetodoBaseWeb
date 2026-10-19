"""Read-only closure of the already initialized own instance; never reinitializes it."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, secrets, subprocess
import psycopg2

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/runtime28-native-20261019')
OUT = LAB / 'pg55484-setup'
pointer = json.loads((LAB / 'pg55484-instance-pointer.json').read_text())
admin = json.loads(Path(pointer['private_admin_file']).read_text())
pid = pointer['postmaster_pid']
assert pid == 1216 and pointer['port'] == 55484 and admin['port'] == 55484
data = Path(pointer['data_directory']).resolve()
assert data == Path(admin['data_dir']).resolve()
assert data.is_relative_to(Path(admin['private_root']).resolve())
command = 'Get-CimInstance Win32_Process -Filter "ProcessId=' + str(pid) + '" | Select-Object ProcessId,ExecutablePath,CommandLine,CreationDate,ParentProcessId | ConvertTo-Json -Compress'
process = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-NonInteractive', '-Command', command], creationflags=subprocess.CREATE_NO_WINDOW))
assert process['ProcessId'] == pid and Path(process['ExecutablePath']).resolve() == Path(pointer['postgres_executable']).resolve()
assert str(data).casefold() in process['CommandLine'].casefold() and '55484' in process['CommandLine']
listeners = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-NonInteractive', '-Command',
    'Get-NetTCPConnection -LocalPort 55484 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress'], creationflags=subprocess.CREATE_NO_WINDOW))
if isinstance(listeners, dict):
    listeners = [listeners]
assert listeners and all(r['LocalAddress'] == '127.0.0.1' and r['OwningProcess'] == pid for r in listeners)
connection = psycopg2.connect(host='127.0.0.1', port=55484, user=admin['username'], password=admin['password'], dbname='postgres', connect_timeout=5)
with connection.cursor() as cursor:
    cursor.execute('SET TRANSACTION READ ONLY')
    cursor.execute('SELECT version(),host(inet_server_addr()),inet_server_port(),current_user')
    version, host, port, role = cursor.fetchone()
    assert re.match(r'^PostgreSQL 17\.11(?:\s|,)', version) and host == '127.0.0.1' and port == 55484 and role == admin['username']
    cursor.execute("SELECT name,setting FROM pg_settings WHERE name IN ('data_directory','listen_addresses','port','password_encryption','ssl','log_statement') ORDER BY name")
    settings = dict(cursor.fetchall())
    assert Path(settings['data_directory']).resolve() == data
    assert settings['listen_addresses'] == '127.0.0.1' and settings['port'] == '55484' and settings['password_encryption'] == 'scram-sha-256'
    cursor.execute('SELECT line_number,type,address,netmask,auth_method,error FROM pg_hba_file_rules ORDER BY line_number')
    hba = cursor.fetchall();assert hba and all(row[4] == 'scram-sha-256' and row[5] is None for row in hba)
    cursor.execute('SELECT datname FROM pg_database ORDER BY datname')
    databases = [r[0] for r in cursor.fetchall()];assert set(databases) == {'postgres','template0','template1'}
connection.rollback();connection.close()
try:
    invalid = psycopg2.connect(host='127.0.0.1', port=55484, user=admin['username'], password=secrets.token_hex(32), dbname='postgres', connect_timeout=5)
except psycopg2.OperationalError:
    wrong_password_rejected = True
else:
    invalid.close();raise AssertionError('Wrong own-admin password authenticated')
pidfile = (data / 'postmaster.pid').read_text().splitlines()
assert int(pidfile[0]) == pid and Path(pidfile[1]).resolve() == data and pidfile[3] == '55484'
baseline = json.loads((OUT / 'tool-files.before.json').read_text())
install = Path(pointer['source_existing_installation_read_only'])
current = {}
for rel in baseline:
    path = install / rel
    assert path.is_file() and not path.is_symlink() and not (getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    current[rel] = {'bytes': path.stat().st_size, 'sha256': digest}
assert current == baseline
(OUT / 'tool-files.after.json').write_text(json.dumps(current, indent=2) + '\n', encoding='utf-8')
summary = {'finished_utc': datetime.now(timezone.utc).isoformat(), 'version': version,
           'pid': pid, 'process_identity': process, 'listeners': listeners, 'data_directory': str(data),
           'host': host, 'port': port, 'settings': settings, 'hba': hba, 'databases': databases,
           'wrong_admin_password_rejected': wrong_password_rejected, 'tools_before_after_identical': True,
           'tool_files': len(current), 'new_instance_initialized_once': True, 'private_initdb_pwfile_deleted': not (Path(admin['private_root']) / 'initdb-password.txt').exists(),
           'product_roles_created': False, 'product_database_created': False, 'product_started': False,
           'old55483_modified': False,
           'initial_controller_failure': 'Initial equality compared inet::text containing /32 to a bare IPv4. Preserved initial script and read-only diagnostic; host(inet_server_addr()) now validates the exact loopback address.',
           'scope': 'New owned local SCRAM-only PG17.11 instance ready for separately reviewed role producer; no product startup or deployment acceptance.'}
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
