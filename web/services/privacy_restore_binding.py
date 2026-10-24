"""Bind byte destination, migration connection and every suppression session."""
from contextlib import nullcontext
import ipaddress
from pathlib import Path
import stat
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url


def destination(options):
    url=options.get('database_url');sqlite=options.get('sqlite_destination')
    if bool(url)==bool(sqlite):
        raise ValueError('Exactly one explicit application restore destination required')
    if sqlite:
        path=Path(sqlite)
        if not path.is_absolute() or path!=path.resolve():
            raise ValueError('An absolute nonalias SQLite destination is required')
        return {'dialect':'sqlite','sqlite_path':path.as_posix()}
    value=make_url(url)
    if (value.get_backend_name()!='postgresql' or not value.host or not value.port
            or value.database!=options.get('expected_database')):
        raise ValueError('Explicit PostgreSQL host/port/database binding required')
    host=value.host
    if host!='localhost':
        try:ipaddress.ip_address(host)
        except ValueError:raise ValueError('A numeric endpoint is required for this restore binding') from None
    tls={'sslmode','sslcert','sslkey','sslrootcert','sslcrl','sslcrldir','ssl_min_protocol_version','ssl_max_protocol_version','channel_binding'}
    if set(value.query)-tls:raise ValueError('Connection authority overrides are forbidden')
    return {'dialect':'postgresql','host':host,'port':value.port,'database':value.database}


def observe(connection,target):
    if connection.dialect.name!=target['dialect']:
        raise ValueError('Restore connection dialect differs')
    if target['dialect']=='sqlite':
        rows=connection.exec_driver_sql('PRAGMA database_list').mappings().all()
        if any(row['name'] not in {'main','temp'} for row in rows):raise ValueError('Attached restore databases are forbidden')
        main=next(row for row in rows if row['name']=='main')
        path=Path(main['file'])
        if path.resolve(strict=True).as_posix()!=target['sqlite_path']:
            raise ValueError('The effective SQLite file is not the byte restore destination')
        for node in (path,*path.parents):
            info=node.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:
                raise ValueError('Restore file aliases are forbidden')
        info=path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise ValueError('Single owned SQLite file required')
        return {**target,'device':info.st_dev,'inode':info.st_ino}
    driver=connection.connection.driver_connection
    parameters=driver.get_dsn_parameters()
    if (parameters.get('dbname')!=target['database'] or parameters.get('host')!=target['host']
            or parameters.get('port')!=str(target['port'])):
        raise ValueError('Effective PostgreSQL destination differs from byte recovery')
    row=connection.execute(text('SELECT current_database(),inet_server_addr()::text,inet_server_port(),pg_postmaster_start_time(),(SELECT oid FROM pg_database WHERE datname=current_database())')).one()
    if row[0]!=target['database'] or row[2]!=target['port']:
        raise ValueError('The actual PostgreSQL endpoint/database differs')
    return {**target,'server_address':row[1],'server_start':row[3].isoformat(),'database_oid':row[4]}


def restored_binding(target,options):
    """Observe the explicit destination itself, before independent callbacks."""
    url=options.get('database_url') if target['dialect']=='postgresql' else 'sqlite:///'+target['sqlite_path']
    engine=create_engine(url,pool_size=1,max_overflow=0)
    try:
        with engine.connect() as connection:return observe(connection,target)
    finally:engine.dispose()


def require_binding(connection,binding):
    target={key:binding[key] for key in ('dialect','sqlite_path')} if binding['dialect']=='sqlite' else {key:binding[key] for key in ('dialect','host','port','database')}
    if observe(connection,target)!=binding:raise ValueError('Restore physical identity/generation changed')


def verify_application_connection(connection):
    # Reuse the existing guard against the SAME effective connection, including
    # NOSUPERUSER/NOBYPASSRLS and membership of a table DDL-owner role.
    from web.database.tenant_policy import verify_application_database_role
    class SameConnection:
        dialect=connection.dialect
        def connect(self):return nullcontext(connection)
    verify_application_database_role(SameConnection())


def migrate_bound(engine,binding):
    """No independent migration callback can silently select another database."""
    from alembic import command
    from web.database.schema_control import alembic_config,expected_head,verify_runtime_schema
    with engine.begin() as connection:
        require_binding(connection,binding)
        config=alembic_config();config.attributes['connection']=connection
        command.upgrade(config,expected_head())
        require_binding(connection,binding)
    verify_runtime_schema(engine)
