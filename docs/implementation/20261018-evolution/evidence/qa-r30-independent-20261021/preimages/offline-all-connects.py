"""Offline-only QA runner: no PostgreSQL/Redis or TCP endpoints are allowed."""
import os
from pathlib import Path
import socket
import sys

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


def deny_connect(*_args, **_kwargs):
    raise RuntimeError('Independent offline QA rejects every socket connection')


deny_connect._metodobase_guard = True
socket.socket.connect = deny_connect
socket.socket.connect_ex = deny_connect
import psycopg2

psycopg2.connect = deny_connect
import pytest

raise SystemExit(pytest.main(sys.argv[1:] + ['-o', 'cache_dir=' + str(temporary / '.pytest_cache')]))
