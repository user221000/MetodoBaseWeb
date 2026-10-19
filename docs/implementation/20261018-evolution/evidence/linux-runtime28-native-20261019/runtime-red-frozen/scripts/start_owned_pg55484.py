"""Creates one private loopback-only SCRAM PostgreSQL instance; no product roles."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, io, json, os, re, secrets, socket, subprocess, tempfile, time, uuid

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT = LAB / 'evidence/runtime28-native-20261019/pg55484-setup'
OUT.mkdir(exist_ok=False)
BIN = Path(r'C:\Program Files\PostgreSQL\17\bin')
INSTALL = BIN.parent
ROOT_TEMP = Path(tempfile.gettempdir()).resolve()
SOURCE = LAB / 'evidence/runtime28-native-20261019/pg55483-readonly.json'
assert Path(json.loads(SOURCE.read_text())['binary_directory']).resolve() == BIN.resolve()
def info(p):
    with p.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': p.stat().st_size, 'sha256': digest}
def snapshot():
    records = {}
    for folder in ['bin', 'lib', 'share']:
        for p in sorted((INSTALL / folder).rglob('*')):
            assert p.resolve().is_relative_to((INSTALL / folder).resolve())
            assert not p.is_symlink() and not (getattr(p.lstat(), 'st_file_attributes', 0) & 0x400)
            if p.is_file():
                records[p.relative_to(INSTALL).as_posix()] = info(p)
    return records
before = snapshot()
(OUT / 'tool-files.before.json').write_text(json.dumps(before, indent=2) + '\n', encoding='utf-8')
version = subprocess.check_output([str(BIN / 'postgres.exe'), '--version'], creationflags=subprocess.CREATE_NO_WINDOW, text=True).strip()
assert version == 'postgres (PostgreSQL) 17.11', version
with socket.socket() as port:
    port.bind(('127.0.0.1', 55484))
nonce = uuid.uuid4().hex
private = Path(tempfile.mkdtemp(prefix='metodobase-runtime28-pg55484-')).resolve()
assert private.is_relative_to(ROOT_TEMP) and private != ROOT_TEMP
who = subprocess.check_output(['whoami', '/user', '/fo', 'csv', '/nh'], text=True)
sid = next(csv.reader(io.StringIO(who)))[1]
assert re.fullmatch(r'S-1-[0-9-]+', sid)
subprocess.run(['icacls', str(private), '/inheritance:r', '/grant:r', '*' + sid + ':(OI)(CI)F',
                '*S-1-5-18:(OI)(CI)F'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
data = private / 'data'
profile = private / 'profile';profile.mkdir()
username = 'mb28_root_' + nonce
password = secrets.token_hex(32)
pwfile = private / 'initdb-password.txt'
with pwfile.open('x', encoding='ascii') as stream:
    stream.write(password + '\n')
os.chmod(pwfile, 0o600)
admin_file = private / 'admin.json'
with admin_file.open('x', encoding='utf-8') as stream:
    json.dump({'host': '127.0.0.1', 'port': 55484, 'username': username, 'password': password,
               'database': 'postgres', 'data_dir': str(data), 'private_root': str(private), 'nonce': nonce}, stream)
os.chmod(admin_file, 0o600)
allowed = {'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TMP', 'TEMP'}
env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
env.update(PATH=str(BIN) + os.pathsep + r'C:\Windows\System32', HOME=str(profile), USERPROFILE=str(profile),
           APPDATA=str(profile), LOCALAPPDATA=str(profile), PROGRAMDATA=str(profile),
           PGPASSFILE=str(private / 'ambient-password-disabled'), PGSYSCONFDIR=str(profile))
init_command = [str(BIN / 'initdb.exe'), '-D', str(data), '--encoding=UTF8', '--locale=C',
                '--auth-host=scram-sha-256', '--auth-local=scram-sha-256', '--username=' + username, '--pwfile=' + str(pwfile)]
with (private / 'initdb.stdout.log').open('xb') as stdout, (private / 'initdb.stderr.log').open('xb') as stderr:
    init = subprocess.run(init_command, cwd=private, env=env, stdin=subprocess.DEVNULL,
                          stdout=stdout, stderr=stderr, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
for name in ['initdb.stdout.log', 'initdb.stderr.log']:
    # Only sanitized tool output leaves the private directory.
    text = (private / name).read_text(errors='replace').replace(password, '[PRIVATE_REDACTED]')
    (OUT / name).write_text(text, encoding='utf-8')
assert init.returncode == 0
assert pwfile.resolve().is_relative_to(private) and not pwfile.is_symlink()
pwfile.unlink()
command = [str(BIN / 'postgres.exe'), '-D', str(data), '-h', '127.0.0.1', '-p', '55484',
           '-c', 'password_encryption=scram-sha-256', '-c', 'shared_buffers=32MB', '-c', 'max_connections=20',
           '-c', 'ssl=off', '-c', 'log_statement=none', '-c', 'log_min_duration_statement=-1',
           '-c', 'log_connections=off', '-c', 'log_disconnections=off']
with (private / 'server.stdout.log').open('xb') as stdout, (private / 'server.stderr.log').open('xb') as stderr:
    process = subprocess.Popen(command, cwd=data, env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                               creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
pointer = {'created_utc': datetime.now(timezone.utc).isoformat(), 'private_admin_file': str(admin_file),
           'private_root': str(private), 'data_directory': str(data), 'port': 55484, 'host': '127.0.0.1',
           'postmaster_pid': process.pid, 'postgres_executable': str(BIN / 'postgres.exe'),
           'postgres_executable_sha256': before['bin/postgres.exe']['sha256'],
           'nonce': nonce, 'command': command, 'source_existing_installation_read_only': str(INSTALL)}
pointer_file = LAB / 'evidence/runtime28-native-20261019/pg55484-instance-pointer.json'
with pointer_file.open('x', encoding='utf-8') as stream:
    json.dump(pointer, stream, indent=2);stream.write('\n')
import psycopg2
deadline = time.monotonic() + 60
connection = None
while time.monotonic() < deadline:
    assert process.poll() is None, 'Owned PostgreSQL exited; inspect private logs'
    try:
        connection = psycopg2.connect(host='127.0.0.1', port=55484, user=username, password=password,
                                      dbname='postgres', connect_timeout=2, application_name='runtime28_owned_bootstrap')
        break
    except psycopg2.OperationalError:
        time.sleep(0.5)
assert connection is not None
with connection.cursor() as cursor:
    cursor.execute('SELECT version(), inet_server_addr()::text, inet_server_port(), current_user')
    actual_version, host, port, role = cursor.fetchone()
    assert 'PostgreSQL 17.11 ' in actual_version and host == '127.0.0.1' and port == 55484 and role == username
    cursor.execute("SELECT name,setting FROM pg_settings WHERE name IN ('data_directory','listen_addresses','port','password_encryption','ssl','log_statement') ORDER BY name")
    settings = dict(cursor.fetchall())
    assert Path(settings['data_directory']).resolve() == data.resolve()
    assert settings['listen_addresses'] == '127.0.0.1' and settings['port'] == '55484' and settings['password_encryption'] == 'scram-sha-256'
    cursor.execute('SELECT line_number,type,address,netmask,auth_method,error FROM pg_hba_file_rules ORDER BY line_number')
    hba = cursor.fetchall()
    assert hba and all(row[4] == 'scram-sha-256' and row[5] is None for row in hba)
    cursor.execute('SELECT datname FROM pg_database ORDER BY datname')
    databases = [r[0] for r in cursor.fetchall()]
    assert set(databases) == {'postgres', 'template0', 'template1'}
connection.rollback();connection.close()
try:
    invalid = psycopg2.connect(host='127.0.0.1', port=55484, user=username, password=secrets.token_hex(32), dbname='postgres', connect_timeout=5)
except psycopg2.OperationalError:
    incorrect_password_rejected = True
else:
    invalid.close();raise AssertionError('Incorrect own-admin password authenticated')
pidfile = (data / 'postmaster.pid').read_text().splitlines()
assert int(pidfile[0]) == process.pid and Path(pidfile[1]).resolve() == data.resolve() and pidfile[3] == '55484'
after = snapshot()
(OUT / 'tool-files.after.json').write_text(json.dumps(after, indent=2) + '\n', encoding='utf-8')
assert before == after
summary = {'finished_utc': datetime.now(timezone.utc).isoformat(), 'version': actual_version, 'pid': process.pid,
           'port': port, 'host': host, 'data_directory': str(data), 'settings': settings, 'hba': hba,
           'databases': databases, 'wrong_admin_password_rejected': incorrect_password_rejected,
           'private_acl': 'Inherited grants removed; current user SID and SYSTEM only',
           'initdb_pwfile_deleted_after_success': True, 'tools_before_after_identical': True,
           'tool_files': len(before), 'private_admin_file': str(admin_file),
           'product_roles_created': False, 'product_database_created': False, 'product_started': False,
           'old_55483_instance_or_hba_mutated': False,
           'scope': 'New owned local PG17.11 SCRAM instance only; native libraries of this Windows tool are separate from the Linux product image audit.'}
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
