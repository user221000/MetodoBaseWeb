"""Prepared for review. Explicit execution creates only newly attributed UUID QA objects."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit, urlunsplit
import argparse, csv, hashlib, ipaddress, io, json, os, re, secrets, subprocess, sys, tempfile, uuid

POINTER = Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/runtime28-native-20261019/pg55484-instance-pointer.json')
ADMIN_FILE = Path(json.loads(POINTER.read_text())['private_admin_file'])
LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/runtime28-native-20261019')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--execute-owned-setup', action='store_true')
args = parser.parse_args()
assert args.execute_owned_setup, 'Review-only producer: explicit execution switch required'
import psycopg2
from psycopg2 import extensions, sql

def classified_private_failure(exc, expected):
    code = getattr(exc, 'pgcode', None) or getattr(getattr(exc, 'diag', None), 'sqlstate', None)
    allowed = {'password_authentication_failed': ('28P01', 'password authentication failed'),
               'database_permission_denied': ('42501', 'permission denied for database')}
    expected_code, constant = allowed[expected]
    if code == expected_code:
        return {'category': expected, 'method': 'sqlstate', 'sqlstate': code}
    # The text is examined only privately and never returned, logged or published.
    assert code is None and constant in str(exc).lower(), 'Negative connection failed for an unclassified reason'
    return {'category': expected, 'method': 'private_constant_match', 'sqlstate': None}

def known_positive(role, password, database):
    connection = psycopg2.connect(host='127.0.0.1', port=55484, dbname=database, user=role, password=password, connect_timeout=10)
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_user,1')
        assert cursor.fetchone() == (role, 1)
    connection.rollback();connection.close()
    return True

raw_admin = ADMIN_FILE.read_bytes()
admin_values = json.loads(raw_admin)
assert admin_values['host'] == '127.0.0.1' and admin_values['port'] == 55484
assert admin_values['password'] and admin_values['database'] == 'postgres'
assert re.fullmatch(r'mb28_root_[0-9a-f]{32}', admin_values['username'])
pointer = json.loads(POINTER.read_text())
assert Path(admin_values['data_dir']).resolve() == Path(pointer['data_directory']).resolve()
assert Path(admin_values['private_root']).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
admin_connect = {'host': '127.0.0.1', 'port': 55484, 'dbname': 'postgres',
                 'user': admin_values['username'], 'password': admin_values['password']}
nonce = uuid.uuid4().hex
database = 'metodobase_test_runtime28_' + nonce
migrator = 'mb28_m_' + nonce
app = 'mb28_a_' + nonce
assert all(len(name) <= 63 and re.fullmatch('[a-z0-9_]+', name) for name in [database, migrator, app])
private = Path(tempfile.mkdtemp(prefix='metodobase-runtime28-roles-private-'))
# Windows chmod alone does not establish a private ACL: remove inherited access
# and retain only this user's SID and SYSTEM, on this newly owned directory.
who = subprocess.check_output(['whoami', '/user', '/fo', 'csv', '/nh'], text=True)
sid = next(csv.reader(io.StringIO(who)))[1]
assert re.fullmatch(r'S-1-[0-9-]+', sid)
subprocess.run(['icacls', str(private), '/inheritance:r', '/grant:r', '*' + sid + ':(OI)(CI)F',
                '*S-1-5-18:(OI)(CI)F'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
passwords = {migrator: secrets.token_hex(32), app: secrets.token_hex(32)}
def runtime_url(role):
    return 'postgresql+psycopg2://' + role + ':' + quote(passwords[role], safe='') + '@172.30.28.1:15483/' + database
runtime = {'WEB_SECRET_KEY': secrets.token_hex(32), 'METODO_BASE_SALT': secrets.token_hex(32),
           'DATABASE_URL': runtime_url(app), 'MIGRATOR_DATABASE_URL': runtime_url(migrator),
           'STRIPE_SECRET_KEY': 'sk_live_lab28_' + secrets.token_hex(32),
           'STRIPE_PUBLISHABLE_KEY': 'pk_live_lab28_' + secrets.token_hex(32),
           'STRIPE_WEBHOOK_SECRET': 'whsec_lab28_' + secrets.token_hex(32)}
for key in ['STRIPE_PRICE_STANDARD', 'STRIPE_PRICE_GYM_COMERCIAL', 'STRIPE_PRICE_CLINICA', 'STRIPE_PRICE_PRO_USUARIO']:
    runtime[key] = 'price_lab28_' + secrets.token_hex(16)
secret_file = private / 'private.json'
secret_payload = {'nonce': nonce, 'database': database, 'migrator_role': migrator, 'application_role': app,
                  'passwords': passwords, 'runtime_stdin': runtime}
with secret_file.open('x', encoding='utf-8') as stream:
    json.dump(secret_payload, stream)
os.chmod(secret_file, 0o600)
journal_file = private / 'ownership-journal.json'
journal = {'nonce': nonce, 'database': database, 'migrator_role': migrator, 'application_role': app,
           'host': '127.0.0.1', 'port': 55484, 'created_roles': [], 'created_database': False,
           'private_file': str(secret_file), 'state': 'PREPARED_BEFORE_SQL'}
def persist():
    journal_file.write_text(json.dumps(journal, indent=2) + '\n', encoding='utf-8')
    os.chmod(journal_file, 0o600)
persist()
report = {'nonce': nonce, 'database': database, 'migrator_role': migrator, 'application_role': app,
          'created_roles': [], 'created_database': False, 'passwords_or_dsns_emitted': False,
          'provider_values': 'Synthetic structurally valid QA values; no provider authentication or traffic',
          'private_location': str(private)}
try:
    admin = psycopg2.connect(**admin_connect, connect_timeout=10, application_name='metodobase_runtime28_owned_setup')
    admin.autocommit = True
    try:
        rejected_admin = psycopg2.connect(host='127.0.0.1', port=55484, dbname='postgres', user=admin_values['username'], password=secrets.token_hex(32), connect_timeout=5)
    except psycopg2.OperationalError as exc:
        report['classified_wrong_bootstrap_password'] = classified_private_failure(exc, 'password_authentication_failed')
    else:
        rejected_admin.close();raise AssertionError('Wrong bootstrap password authenticated')
    report['bootstrap_known_positive_after_negative'] = known_positive(admin_values['username'], admin_values['password'], 'postgres')
    with admin.cursor() as cursor:
        cursor.execute('SELECT inet_server_port(), current_database(), current_user')
        server_port, admin_database, admin_role = cursor.fetchone()
        assert server_port == 55484
        assert admin_role == admin_values['username']
        cursor.execute('SHOW data_directory')
        assert Path(cursor.fetchone()[0]).resolve() == Path(admin_values['data_dir']).resolve()
        cursor.execute('SHOW server_version')
        assert cursor.fetchone()[0] == '17.11'
        cursor.execute('SELECT datname FROM pg_database ORDER BY datname')
        assert {row[0] for row in cursor.fetchall()} == {'postgres', 'template0', 'template1'}
        for system_database in ['postgres', 'template0', 'template1']:
            cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(system_database)))
        report['admin_target_verified'] = {'port': server_port, 'database': admin_database, 'role': admin_role}
        cursor.execute('SELECT 1 FROM pg_roles WHERE rolname = ANY(%s)', ([migrator, app],))
        assert cursor.fetchone() is None
        cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s', (database,))
        assert cursor.fetchone() is None
        for role in [migrator, app]:
            verifier = extensions.encrypt_password(passwords[role], role, admin, algorithm='scram-sha-256')
            assert verifier.startswith('SCRAM-SHA-256$')
            cursor.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT CONNECTION LIMIT 16 PASSWORD %s').format(sql.Identifier(role)), (verifier,))
            journal['created_roles'].append(role);persist()
        cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0 ENCODING 'UTF8'").format(sql.Identifier(database), sql.Identifier(migrator)))
        journal['created_database'] = True;persist()
        cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(database)))
        cursor.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}, {}').format(sql.Identifier(database), sql.Identifier(migrator), sql.Identifier(app)))
        cursor.execute('SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, rolinherit, rolcanlogin FROM pg_roles WHERE rolname=ANY(%s) ORDER BY rolname', ([migrator, app],))
        flags = cursor.fetchall()
        assert len(flags) == 2 and all(not any(row[1:7]) and row[7] for row in flags)
        report['role_flags'] = flags
        cursor.execute("SELECT rolname, rolpassword LIKE 'SCRAM-SHA-256$%%' FROM pg_authid WHERE rolname=ANY(%s) ORDER BY rolname", ([migrator, app],))
        report['scram_verifiers'] = cursor.fetchall()
        assert all(row[1] for row in report['scram_verifiers'])
        cursor.execute('SELECT line_number,type,database,user_name,address,netmask,auth_method,error FROM pg_hba_file_rules ORDER BY line_number')
        hba = cursor.fetchall()
        assert hba and all(row[6] == 'scram-sha-256' and row[7] is None for row in hba)
        other_database_access = {}
        for system_database in ['postgres', 'template0', 'template1']:
            cursor.execute("SELECT has_database_privilege(%s,%s,'CONNECT')", (app, system_database))
            other_database_access[system_database] = cursor.fetchone()[0]
        assert not any(other_database_access.values())
        report['application_other_database_connect_privileges'] = other_database_access
        matched = []
        for role in [migrator, app]:
            for row in hba:
                line, kind, databases, users, address, netmask, method, error = row
                assert error is None
                if kind not in ['host', 'hostssl', 'hostnossl'] or not address or not netmask:
                    continue
                if kind == 'hostssl' and not admin.info.ssl_in_use:
                    continue
                if kind == 'hostnossl' and admin.info.ssl_in_use:
                    continue
                try:
                    network = ipaddress.ip_network(address + '/' + netmask, strict=False)
                except ValueError:
                    continue
                if ipaddress.ip_address('127.0.0.1') not in network:
                    continue
                if not ('all' in databases or database in databases) or not ('all' in users or role in users):
                    continue
                assert method == 'scram-sha-256', 'Matching QA TCP HBA is not explicit SCRAM'
                matched.append({'role': role, 'line': line, 'type': kind, 'method': method});break
            else:
                raise AssertionError('No explicit matching loopback SCRAM HBA rule')
        report['matching_loopback_hba'] = matched
    admin.close()
    owner = psycopg2.connect(host='127.0.0.1', port=55484, dbname=database, user=migrator, password=passwords[migrator], connect_timeout=10)
    with owner:
        with owner.cursor() as cursor:
            cursor.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
            cursor.execute(sql.SQL('ALTER SCHEMA public OWNER TO {}').format(sql.Identifier(migrator)))
            cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(app)))
    owner.close()
    restricted = psycopg2.connect(host='127.0.0.1', port=55484, dbname=database, user=app, password=passwords[app], connect_timeout=10)
    with restricted.cursor() as cursor:
        cursor.execute("SELECT current_user, (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()), has_database_privilege(current_user,current_database(),'CREATE'), has_database_privilege(current_user,current_database(),'TEMP'), has_schema_privilege(current_user,'public','CREATE'), pg_has_role(current_user,%s,'MEMBER')", (migrator,))
        permissions = cursor.fetchone()
        assert permissions[0] == app and permissions[1] == migrator and not any(permissions[2:])
        report['application_nonowner_and_denied_create_temp_membership'] = permissions
        denials = []
        statements = [('set_role_owner', sql.SQL('SET ROLE {}').format(sql.Identifier(migrator))),
                      ('create_role', sql.SQL('CREATE ROLE {}').format(sql.Identifier('mb28_denied_' + nonce))),
                      ('create_public_table', sql.SQL('CREATE TABLE public.{}(id integer)').format(sql.Identifier('mb28_denied_' + nonce))),
                      ('create_temp_table', sql.SQL('CREATE TEMP TABLE {}(id integer)').format(sql.Identifier('mb28_denied_' + nonce)))]
        for label, statement in statements:
            cursor.execute('SAVEPOINT denial_canary')
            try:
                cursor.execute(statement)
            except psycopg2.Error as exc:
                code = exc.pgcode
                cursor.execute('ROLLBACK TO SAVEPOINT denial_canary')
                assert code == '42501'
                denials.append({'operation': label, 'sqlstate': code})
            else:
                cursor.execute('ROLLBACK TO SAVEPOINT denial_canary')
                raise AssertionError('Application privilege canary unexpectedly succeeded')
        report['actual_permission_denials'] = denials
    restricted.rollback();restricted.close()
    other_database_denials = []
    for system_database in ['postgres', 'template1']:
        try:
            unwanted = psycopg2.connect(host='127.0.0.1', port=55484, dbname=system_database, user=app, password=passwords[app], connect_timeout=10)
        except psycopg2.OperationalError as exc:
            classification = classified_private_failure(exc, 'database_permission_denied')
            assert known_positive(app, passwords[app], database)
            other_database_denials.append({'database': system_database, 'actual_tcp_connection_denied': True,
                                          'classification': classification, 'known_positive_after_negative': True})
        else:
            unwanted.close();raise AssertionError('Application connected to an unrelated database')
    report['actual_other_database_denials'] = other_database_denials
    try:
        invalid = psycopg2.connect(host='127.0.0.1', port=55484, dbname=database, user=app, password=secrets.token_hex(32), connect_timeout=10)
    except psycopg2.OperationalError as exc:
        report['wrong_password_rejected'] = classified_private_failure(exc, 'password_authentication_failed')
        report['application_known_positive_after_wrong_password'] = known_positive(app, passwords[app], database)
    else:
        invalid.close();raise AssertionError('Incorrect own-role password unexpectedly authenticated')
    assert ADMIN_FILE.read_bytes() == raw_admin
    journal['state'] = 'OWNED_ROLES_READY_NO_MIGRATION';persist()
    report.update(created_roles=journal['created_roles'], created_database=True,
                  private_admin_input_unchanged=True, real_tcp_scram_logins_verified=True,
                  product_migration_or_startup=False)
except Exception as exc:
    journal['state'] = 'PARTIAL_REQUIRES_OWNED_REVIEW';journal['failure_type'] = type(exc).__name__;persist()
    report.update(failure_type=type(exc).__name__, created_roles=journal['created_roles'], created_database=journal['created_database'])
    # Deliberately omit exception text, SQL and connection strings from publication.
    (private / 'failure-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'state': 'FAILED_PRIVATE_REVIEW_REQUIRED', 'failure_type': type(exc).__name__, 'private_location': str(private)}))
    raise SystemExit(1)
(private / 'sanitized-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'state': 'OWNED_ROLES_READY_NO_MIGRATION', 'private_location': str(private),
                  'nonce': nonce, 'real_tcp_scram_logins_verified': True, 'secret_values_emitted': False}))
