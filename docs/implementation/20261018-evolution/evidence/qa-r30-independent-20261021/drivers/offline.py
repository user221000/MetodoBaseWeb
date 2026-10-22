"""Offline-only QA runner: no PostgreSQL/Redis or TCP endpoints are allowed."""
import os
from pathlib import Path
import socket
import sys
import asyncio.proactor_events

sys.dont_write_bytecode = True
root = Path('F:/mb-qa-product-analytics-r30-20261021')
sys.path.insert(0, str(root))
for key in list(os.environ):
    upper = key.upper()
    if upper.startswith('PG') or any(value in upper for value in ('DATABASE_URL', 'REDIS')):
        os.environ.pop(key, None)
os.environ.pop('_METODOBASE_TEST_ROOT', None)
from tests.isolation import prepare_environment

temporary = prepare_environment(discard_inherited=True)
assert os.environ['DATABASE_URL'].startswith('sqlite:///')


original_connect = socket.socket.connect
ipc_pairs = []


def deny_connect(sock, address):
    # CPython Windows emulates the event loop self-pipe with a private pair.
    # No application call, provider, chosen port, or other caller is admitted.
    frame = sys._getframe(1)
    parent = frame.f_back
    if (frame.f_code is socket._fallback_socketpair.__code__
            and parent.f_code is asyncio.proactor_events.BaseProactorEventLoop._make_self_pipe.__code__
            and frame.f_locals.get('csock') is sock
            and address == (frame.f_locals.get('addr'), frame.f_locals.get('port'))
            and address[0] in {'127.0.0.1', '::1'}
            and frame.f_locals['lsock'].getsockname()[:2] == address):
        ipc_pairs.append(True)
        return original_connect(sock, address)
    raise RuntimeError('Independent offline QA rejects every socket connection')


deny_connect._metodobase_guard = True
socket.socket.connect = deny_connect
def deny_provider(*_args, **_kwargs):
    raise RuntimeError('Independent offline QA rejects provider/socket-ex connections')


socket.socket.connect_ex = deny_provider
import psycopg2

psycopg2.connect = deny_provider
import pytest

result = pytest.main(sys.argv[1:] + ['-o', 'cache_dir=' + str(temporary / '.pytest_cache')])
print('OFFLINE_QA: application TCP rejected; PostgreSQL rejected; Windows self-pipe pairs=' + str(len(ipc_pairs)))
raise SystemExit(result)
