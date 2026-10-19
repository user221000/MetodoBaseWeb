"""Exclusive pre-CREATE attribution for current33 and preserved fixture bodies.

Historical helper files are never edited. An old fixture's FORCE request is
executed only as ordinary DROP after exact ownOID and zero-session checks.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import re

import psycopg2
from psycopg2.extensions import connection as PGConnection,cursor as PGCursor

ORIGINAL=psycopg2.connect
OWNED={}
INSTALLED=False
NAMES=r'metodobase_test_(?:(?:migrations|rls)_[0-9a-f]{12}|followup_[0-9a-f]{16}|(?:google|progress|retirement)_[0-9a-f]{32})'


def birth():
    if os.name!='nt':
        value=Path('/proc/self/stat').read_text(encoding='ascii')
        return {'pid':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'start_ticks':int(value[value.rindex(')')+2:].split()[19])}
    api=ctypes.WinDLL('kernel32',use_last_error=True);api.GetCurrentProcess.restype=ctypes.c_void_p
    times=[ctypes.c_ulonglong() for _ in range(4)]
    assert api.GetProcessTimes(ctypes.c_void_p(api.GetCurrentProcess()),*[ctypes.byref(t) for t in times])
    return {'pid':os.getpid(),'creation_filetime':times[0].value}


def root():
    value=Path(os.environ['CI33_LEASE_DIRECTORY']).absolute()
    assert value.is_dir() and not value.is_symlink() and value.resolve()==value
    return value


def dsn():
    from tests.isolation import validate_postgres_test_url
    value=validate_postgres_test_url(os.environ['METODOBASE_TEST_MIGRATOR_URL'])
    from urllib.parse import urlsplit
    parts=urlsplit(value);assert parts.hostname in {'127.0.0.1','localhost'} and parts.port==55483
    return value.replace('postgresql+psycopg2://','postgresql://',1)


def state(name):
    db=ORIGINAL(dsn(),connect_timeout=5)
    try:
        with db.cursor() as c:
            c.execute('SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s',(name,));database=c.fetchone()
            c.execute('SELECT pid,backend_start FROM pg_stat_activity WHERE datname=%s ORDER BY pid',(name,));sessions=c.fetchall()
        return database,sessions
    finally:db.close()


def write(path,value,previous=None):
    raw=(json.dumps(value,indent=2)+'\n').encode()
    assert path.parent==root() and not path.is_symlink()
    with path.open('xb' if previous is None else 'r+b') as out:
        if previous is not None:
            assert out.read()==previous,'Own exclusive lease changed; no overwrite permitted';out.seek(0)
        out.write(raw);out.truncate();out.flush();os.fsync(out.fileno())
    return raw


def parse_ddl(query):
    if re.match(r'^\s*(CREATE|ALTER|DROP)\s+(ROLE|USER)\b',query,re.I) or 'pg_terminate_backend' in query.lower():
        raise AssertionError('Current33 forbids global role changes and backend termination')
    create=re.fullmatch(r'CREATE DATABASE "?('+NAMES+r')"?(?: TEMPLATE template0)?',query,re.I)
    drop=re.fullmatch(r'DROP DATABASE(?: IF EXISTS)? "?('+NAMES+r')"?(?: WITH \(FORCE\))?',query,re.I)
    if re.match(r'^\s*(CREATE|DROP)\s+DATABASE\b',query,re.I):assert create or drop,'Database DDL outside explicit UUID contract'
    return create,drop


class Cursor(PGCursor):
    def execute(self,query,variables=None):
        rendered=query.as_string(self.connection) if hasattr(query,'as_string') else query
        if isinstance(rendered,bytes):rendered=rendered.decode()
        create,drop=parse_ddl(rendered) if isinstance(rendered,str) else (None,None)
        if create:
            name=create.group(1);assert name not in OWNED and state(name)==(None,[])
            path=root()/(name+'.json');identity=birth()
            lease={'database':name,'state':'exclusive_before_CREATE','launcher':identity,
                'guard_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'created':False,'oid':None}
            previous=write(path,lease)
            result=super().execute(query,variables)
            database,sessions=state(name);assert database is not None and sessions==[] and birth()==identity
            lease.update(created=True,oid=database[0],owner=database[1],state='created_exact_OID')
            previous=write(path,lease,previous);OWNED[name]=(lease,previous)
            return result
        if drop:
            name=drop.group(1);assert name in OWNED,'DROP lacks exact process-owned lease'
            lease,previous=OWNED[name];database,sessions=state(name)
            assert database==(lease['oid'],lease['owner']) and sessions==[] and birth()==lease['launcher']
            lease.update(sessions_before_drop=0,original_requested_FORCE='FORCE' in rendered.upper(),state='zero_sessions_before_ordinary_DROP')
            previous=write(root()/(name+'.json'),lease,previous)
            clean=re.sub(r' WITH \(FORCE\)$','',rendered,flags=re.I)
            result=super().execute(clean,variables)
            assert state(name)==(None,[])
            lease.update(state='closed_fresh_absent',executed_FORCE=False,backend_termination=False)
            write(root()/(name+'.json'),lease,previous);del OWNED[name]
            return result
        return super().execute(query,variables)


class Connection(PGConnection):
    def cursor(self,*args,**kwargs):
        kwargs.setdefault('cursor_factory',Cursor);return super().cursor(*args,**kwargs)


def connect(*args,**kwargs):
    kwargs.setdefault('connection_factory',Connection);return ORIGINAL(*args,**kwargs)


def install():
    global INSTALLED
    if not INSTALLED:root();psycopg2.connect=connect;INSTALLED=True
