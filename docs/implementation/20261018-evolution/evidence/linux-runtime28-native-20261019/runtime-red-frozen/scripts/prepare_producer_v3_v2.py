from pathlib import Path
import difflib, hashlib, json

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/runtime28-native-20261019')
source = LAB / 'scripts/produce_private_runtime_roles_v2.py'
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'a83978e713330a715b0ce5f6b6f7443e044239e16a9cb6b2c607185dda86195b'
text = raw.decode().replace('\r\n', '\n')
anchor = "from psycopg2 import extensions, sql\n"
assert text.count(anchor) == 1
text = text.replace(anchor, anchor + '''
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
''')
anchor = '    admin.autocommit = True\n'
assert text.count(anchor) == 1
text = text.replace(anchor, anchor + '''    try:
        rejected_admin = psycopg2.connect(host='127.0.0.1', port=55484, dbname='postgres', user=admin_values['username'], password=secrets.token_hex(32), connect_timeout=5)
    except psycopg2.OperationalError as exc:
        report['classified_wrong_bootstrap_password'] = classified_private_failure(exc, 'password_authentication_failed')
    else:
        rejected_admin.close();raise AssertionError('Wrong bootstrap password authenticated')
    report['bootstrap_known_positive_after_negative'] = known_positive(admin_values['username'], admin_values['password'], 'postgres')
''')
old = """        except psycopg2.OperationalError:
            other_database_denials.append({'database': system_database, 'actual_tcp_connection_denied': True})
"""
new = """        except psycopg2.OperationalError as exc:
            classification = classified_private_failure(exc, 'database_permission_denied')
            assert known_positive(app, passwords[app], database)
            other_database_denials.append({'database': system_database, 'actual_tcp_connection_denied': True,
                                          'classification': classification, 'known_positive_after_negative': True})
"""
assert text.count(old) == 1
text = text.replace(old, new)
old = """    except psycopg2.OperationalError:
        report['wrong_password_rejected'] = True
"""
new = """    except psycopg2.OperationalError as exc:
        report['wrong_password_rejected'] = classified_private_failure(exc, 'password_authentication_failed')
        report['application_known_positive_after_wrong_password'] = known_positive(app, passwords[app], database)
"""
assert text.count(old) == 1
text = text.replace(old, new)
target = LAB / 'scripts/produce_private_runtime_roles_v3.py'
compile(text, str(target), 'exec')
with target.open('x', encoding='utf-8') as stream:
    stream.write(text)
dest = Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/linux-runtime28-native-20261019/credential-producer-v3')
dest.mkdir(exist_ok=False)
with (dest / target.name).open('xb') as stream:
    stream.write(target.read_bytes())
(dest / 'delta-from-unexecuted-v2.patch').write_text(''.join(difflib.unified_diff(raw.decode().splitlines(True), text.splitlines(True), fromfile=source.name, tofile=target.name)), encoding='utf-8')
receipt = {'producer_v2_preserved_sha256': hashlib.sha256(raw).hexdigest(), 'producer_v3_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
           'change': 'Classify expected authentication/permission denial privately and prove known positive SELECT1 after each negative TCP connection.',
           'state': 'Prepared under root authorization; execution receipt separate'}
(dest / 'source-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps(receipt, indent=2))
