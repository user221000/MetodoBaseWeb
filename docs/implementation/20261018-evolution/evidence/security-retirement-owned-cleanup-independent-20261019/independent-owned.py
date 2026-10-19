"""Review-only exclusive own UUID database lease; no destructive fallback."""
from contextlib import contextmanager
from datetime import datetime, timezone
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import uuid
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine


def process_birth():
    created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.GetCurrentProcess.restype = wintypes.HANDLE
    api.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    api.GetProcessTimes.restype = wintypes.BOOL
    handle = api.GetCurrentProcess()
    assert api.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user))
    return (created.dwHighDateTime << 32) | created.dwLowDateTime


@contextmanager
def owned_database(dialect, directory):
    assert dialect == 'postgresql', 'This independent lease is PostgreSQL only'
    import psycopg2
    from psycopg2 import sql
    from tests.isolation import validate_postgres_test_url
    source = validate_postgres_test_url(os.environ['METODOBASE_TEST_MIGRATOR_URL'])
    parsed = urlsplit(source)
    assert parsed.hostname in {'127.0.0.1', 'localhost'} and parsed.port == 55483
    root = Path(os.environ['SEC32_PRIVATE_LEASES']).resolve()
    assert root.name == 'leases' and root.parent.name == 'metodobase-sec-retirement-cleanup-peer-private-20261019'
    root.mkdir(parents=True, exist_ok=True)
    identifier = uuid.uuid4().hex
    name = 'metodobase_test_seccleanup_' + identifier
    path = root / ('lease-' + identifier + '.json')
    state = {'plan_id': identifier, 'database': name, 'planned_at': datetime.now(timezone.utc).isoformat(),
        'launcher_pid': os.getpid(), 'launcher_birth_filetime': process_birth(), 'state': 'planned',
        'initial_creation': 'exclusive_xb_before_CREATE'}
    encode = lambda: (json.dumps(state, indent=2) + '\n').encode()
    previous = encode()
    with path.open('xb') as receipt:
        receipt.write(previous);receipt.flush();os.fsync(receipt.fileno())
    def save():
        nonlocal previous
        assert path.resolve().parent == root
        data = encode()
        with path.open('r+b') as receipt:
            assert receipt.read() == previous, 'Owned receipt changed; no overwrite permitted'
            receipt.seek(0);receipt.write(data);receipt.truncate();receipt.flush();os.fsync(receipt.fileno())
        previous = data
    control = psycopg2.connect(source.replace('postgresql+psycopg2://', 'postgresql://', 1))
    control.autocommit = True
    engine = None
    created = False
    try:
        with control.cursor() as db:
            db.execute('SELECT pg_backend_pid(),current_user,pg_postmaster_start_time(),inet_server_addr()::text,inet_server_port()')
            pid, owner, postmaster, host, port = db.fetchone()
            assert port == 55483 and host in {'127.0.0.1/32', '127.0.0.1'}
            state.update(control_backend_pid=pid, expected_owner=owner, postmaster_start=postmaster.isoformat(), server_host=host, server_port=port)
            save()
            db.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(name)))
            created = True
            db.execute('SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s', (name,))
            oid, actual_owner = db.fetchone()
            assert actual_owner == owner
            state.update(oid=oid, state='created', created_at=datetime.now(timezone.utc).isoformat(),
                launcher_birth_after_CREATE=process_birth())
            assert state['launcher_birth_after_CREATE'] == state['launcher_birth_filetime']
            save()
        url = urlunsplit(parsed._replace(path='/' + name))
        engine = create_engine(url, pool_size=1, max_overflow=0)
        yield url, engine
    finally:
        if engine is not None:engine.dispose()
        try:
            if created:
                with control.cursor() as db:
                    db.execute('SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s', (name,))
                    assert db.fetchone() == (state['oid'], state['expected_owner']), 'Owned DB changed; retained'
                    db.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=%s', (name,))
                    count = db.fetchone()[0]
                    state['sessions_before_drop'] = count;save()
                    assert count == 0, 'Owned sessions remain; no termination or FORCE DROP permitted'
                    db.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
                with psycopg2.connect(source.replace('postgresql+psycopg2://', 'postgresql://', 1)) as fresh, fresh.cursor() as db:
                    db.execute('SELECT count(*) FROM pg_database WHERE datname=%s', (name,))
                    assert db.fetchone()[0] == 0
                state.update(state='closed_absent', closed_at=datetime.now(timezone.utc).isoformat(), absence_verified='fresh_control_connection')
                save()
        finally:control.close()
