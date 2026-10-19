from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, json
import psycopg2

BASE=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/runtime28-native-20261019')
PRIVATE=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-runtime28-roles-private-lwdcn5wd')
private=json.loads((PRIVATE/'private.json').read_text())
assert private['nonce']=='a781deb39fd74441baa6a37c1a0cab40'
source=Path(r'F:\MetodoBaseWeb-image-security-20261019/web/database/alembic/versions/c4f8e9d2a3b1_enable_rls_policies_multi_tenant.py')
data=source.read_bytes();tree=ast.parse(data)
sqls=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'CREATE ROLE metodobase_app' in n.value]
assert len(sqls)==1
role=private['migrator_role']
connection=psycopg2.connect(host='127.0.0.1',port=55484,dbname=private['database'],user=role,password=private['passwords'][role],connect_timeout=10)
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_user,inet_server_port(),rolsuper,rolcreaterole,rolcreatedb,rolbypassrls FROM pg_roles WHERE rolname=current_user')
        actual=cursor.fetchone();assert actual[0]==role and actual[1]==55484 and not any(actual[2:])
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        public_tables=[r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT to_regclass('public.alembic_version'),EXISTS(SELECT 1 FROM pg_roles WHERE rolname='metodobase_app')")
        marker,global_role=cursor.fetchone();assert marker is None and not global_role and not public_tables
        cursor.execute('SAVEPOINT original_statement_diagnostic')
        try:
            cursor.execute(sqls[0])
        except psycopg2.Error as exc:
            code=exc.pgcode;error_class=type(exc).__name__
            cursor.execute('ROLLBACK TO SAVEPOINT original_statement_diagnostic')
            assert code=='42501'
        else:
            cursor.execute('ROLLBACK TO SAVEPOINT original_statement_diagnostic')
            raise AssertionError('Original role side effect unexpectedly succeeded')
        cursor.execute('SELECT current_user,1');assert cursor.fetchone()==(role,1)
        cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='metodobase_app')")
        assert cursor.fetchone()[0] is False
finally:
    connection.rollback();connection.close()
report={'diagnosed_utc':datetime.now(timezone.utc).isoformat(),'image_id':'sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c',
        'image_source':'bc365c13b9af9e24129a56b4068059a67bb3afa0','migration_file':source.name,
        'migration_source_sha256':hashlib.sha256(data).hexdigest(),'original_statement':sqls[0],
        'actual_migration_exit':1,'actual_container_oom_killed':False,
        'same_original_statement_sqlstate':code,'same_original_statement_exception_class':error_class,
        'migrator_nosuper_nocreaterole_nocreatedb_nobypass':True,
        'known_positive_after_negative':True,'public_tables_after_original_cli_rollback':public_tables,
        'alembic_version_relation_after_original_cli':None,'legacy_global_role_exists':False,
        'diagnostic_transaction_rolled_back':True,'marker28_reached':False,'product_web_started':False,
        'scope':'Real product migration is incompatible with a fresh instance and a dedicated NOCREATEROLE migration owner. Negative replay is diagnostic only, not an alternative acceptance path. No privileges, source, roles or image were repaired.'}
(BASE/'runtime/migration-role-boundary-red.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
