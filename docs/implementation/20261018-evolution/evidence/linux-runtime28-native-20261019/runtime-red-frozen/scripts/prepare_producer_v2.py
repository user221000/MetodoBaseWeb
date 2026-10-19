from pathlib import Path
import difflib, hashlib, json

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/runtime28-native-20261019')
source = LAB / 'scripts/produce_private_runtime_roles.py'
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'eef2fbdb3c09dbb70436b227b9f37fd53254e6fceae563f585550cabb6eab0be'
text = raw.decode('utf-8')
old = "ADMIN_FILE = Path(r'C:\\Users\\Consu\\AppData\\Local\\Temp\\metodobase-qa-pg55483-private-ok6hrpyq\\env.json')"
new = "POINTER = Path(r'F:\\MetodoBaseWeb-linux-lab-20261019/evidence/runtime28-native-20261019/pg55484-instance-pointer.json')\nADMIN_FILE = Path(json.loads(POINTER.read_text())['private_admin_file'])"
assert text.count(old) == 1
text = text.replace(old, new)
begin = text.index('raw_admin = ADMIN_FILE.read_bytes()')
end = text.index('nonce = uuid.uuid4().hex', begin)
text = text[:begin] + '''raw_admin = ADMIN_FILE.read_bytes()
admin_values = json.loads(raw_admin)
assert admin_values['host'] == '127.0.0.1' and admin_values['port'] == 55484
assert admin_values['password'] and admin_values['database'] == 'postgres'
assert re.fullmatch(r'mb28_root_[0-9a-f]{32}', admin_values['username'])
pointer = json.loads(POINTER.read_text())
assert Path(admin_values['data_dir']).resolve() == Path(pointer['data_directory']).resolve()
assert Path(admin_values['private_root']).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
admin_connect = {'host': '127.0.0.1', 'port': 55484, 'dbname': 'postgres',
                 'user': admin_values['username'], 'password': admin_values['password']}
''' + text[end:]
text = text.replace('55483', '55484')
text = text.replace("prefix='metodobase-runtime28-private-'", "prefix='metodobase-runtime28-roles-private-'")
text = text.replace('psycopg2.connect(admin_dsn, connect_timeout=10', 'psycopg2.connect(**admin_connect, connect_timeout=10')
anchor = "        assert server_port == 55484\n"
assert text.count(anchor) == 1
text = text.replace(anchor, anchor + '''        assert admin_role == admin_values['username']
        cursor.execute('SHOW data_directory')
        assert Path(cursor.fetchone()[0]).resolve() == Path(admin_values['data_dir']).resolve()
        cursor.execute('SHOW server_version')
        assert cursor.fetchone()[0] == '17.11'
        cursor.execute('SELECT datname FROM pg_database ORDER BY datname')
        assert {row[0] for row in cursor.fetchall()} == {'postgres', 'template0', 'template1'}
        for system_database in ['postgres', 'template0', 'template1']:
            cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(system_database)))
''')
anchor = '        hba = cursor.fetchall()\n'
assert text.count(anchor) == 1
text = text.replace(anchor, anchor + '''        assert hba and all(row[6] == 'scram-sha-256' and row[7] is None for row in hba)
        other_database_access = {}
        for system_database in ['postgres', 'template0', 'template1']:
            cursor.execute("SELECT has_database_privilege(%s,%s,'CONNECT')", (app, system_database))
            other_database_access[system_database] = cursor.fetchone()[0]
        assert not any(other_database_access.values())
        report['application_other_database_connect_privileges'] = other_database_access
''')
anchor = '    restricted.rollback();restricted.close()\n'
assert text.count(anchor) == 1
text = text.replace(anchor, anchor + '''    other_database_denials = []
    for system_database in ['postgres', 'template1']:
        try:
            unwanted = psycopg2.connect(host='127.0.0.1', port=55484, dbname=system_database, user=app, password=passwords[app], connect_timeout=10)
        except psycopg2.OperationalError:
            other_database_denials.append({'database': system_database, 'actual_tcp_connection_denied': True})
        else:
            unwanted.close();raise AssertionError('Application connected to an unrelated database')
    report['actual_other_database_denials'] = other_database_denials
''')
compile(text, 'produce_private_runtime_roles_v2', 'exec')
target = LAB / 'scripts/produce_private_runtime_roles_v2.py'
with target.open('x', encoding='utf-8') as stream:
    stream.write(text)
dest = Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/linux-runtime28-native-20261019/credential-producer-v2-prepared')
dest.mkdir(exist_ok=False)
with (dest / target.name).open('xb') as stream:
    stream.write(target.read_bytes())
delta = ''.join(difflib.unified_diff(raw.decode().splitlines(True), text.splitlines(True), fromfile=source.name, tofile=target.name))
(dest / 'delta-from-unexecuted-v1.patch').write_text(delta, encoding='utf-8')
receipt = {'state': 'REVIEW_ONLY_NOT_EXECUTED', 'producer_v1_preserved_sha256': hashlib.sha256(raw).hexdigest(),
           'producer_v2_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
           'target': 'New owned SCRAM-only PG17.11 instance at127.0.0.1:55484; no old55483 credentials consumed',
           'sql_or_role_creation_executed': False, 'syntax_compiles': True,
           'limits': 'No migrations, grants on application tables or product startup by this producer. Private output remains outside evidence.'}
(dest / 'review-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps(receipt, indent=2))
