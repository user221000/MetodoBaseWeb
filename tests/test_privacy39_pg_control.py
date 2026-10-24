"""Portable control-order canaries with native/DBAPI doubles, not real PG."""
from types import SimpleNamespace
import pytest
from tests.ci_web39 import pg_control
from tests import billing13_legacy_apply37_pg_contract as original


@pytest.fixture(scope='session',autouse=True)
def database_schema():yield


@pytest.fixture(autouse=True)
def isolated_database():yield


def controls(monkeypatch,tmp_path,*,bad=None,check_error=False,connect_error=False):
    import psycopg2
    monkeypatch.setattr(pg_control,'os',SimpleNamespace(name='nt'))
    events=[];binary=tmp_path/'pg'
    value={'generation':{'postmaster_pid':71,'master_creation_filetime_100ns':711}}
    profile={'METODOBASE_TEST_MIGRATOR_URL':'postgresql+psycopg2://synthetic:synthetic@127.0.0.1:55483/metodobase_test_control'}
    def identity(pid):
        assert pid==71;events.append('native')
        return (712 if bad=='birth' else 711),(tmp_path/'foreign/postgres.exe' if bad=='exe' else binary/'postgres.exe')
    def directory(config):assert config is profile;events.append('binary');return binary
    monkeypatch.setattr(original,'windows_process_identity',identity)
    monkeypatch.setattr(original,'pg_binary_directory',directory)
    class Cursor:
        def __enter__(self):events.append('cursor_enter');return self
        def __exit__(self,*_):events.append('cursor_close')
    cursor=Cursor()
    class Connection:
        def __init__(self):self.autocommit=False;self.closed=0
        def cursor(self):assert self.autocommit is True;return cursor
        def close(self):self.closed+=1;events.append('physical_close')
    connection=Connection()
    def connect(url,**kwargs):
        assert 'native' in events and 'binary' in events
        events.append('connect');assert kwargs=={'connect_timeout':5}
        assert url.startswith('postgresql://')
        if connect_error:raise RuntimeError('synthetic connect failure')
        return connection
    def check(actual,config,**kwargs):
        assert actual is value and config is profile and kwargs=={'cursor':cursor}
        events.append('same_cursor_c6')
        if check_error:raise ValueError('synthetic generation mismatch')
    monkeypatch.setattr(psycopg2,'connect',connect);monkeypatch.setattr(original,'check_generation',check)
    return value,profile,events,connection


@pytest.mark.parametrize('bad',['birth','exe'])
def test_native_mismatch_prevents_connect(monkeypatch,tmp_path,bad):
    value,profile,events,connection=controls(monkeypatch,tmp_path,bad=bad)
    with pytest.raises(ValueError):pg_control.check_control_generation(value,profile)
    assert 'connect' not in events and connection.closed==0


def test_native_then_timeout_autocommit_same_cursor_and_exact_physical_close(monkeypatch,tmp_path):
    value,profile,events,connection=controls(monkeypatch,tmp_path)
    pg_control.check_control_generation(value,profile)
    assert events==['native','binary','connect','cursor_enter','same_cursor_c6','cursor_close','physical_close']
    assert connection.closed==1


def test_generation_failure_closes_the_same_control_without_retry(monkeypatch,tmp_path):
    value,profile,events,connection=controls(monkeypatch,tmp_path,check_error=True)
    with pytest.raises(ValueError):pg_control.check_control_generation(value,profile)
    assert events.count('connect')==1 and events.count('same_cursor_c6')==1 and connection.closed==1
    assert events[-2:]==['cursor_close','physical_close']


def test_connect_failure_has_no_unknown_descriptor_to_close_or_retry(monkeypatch,tmp_path):
    value,profile,events,connection=controls(monkeypatch,tmp_path,connect_error=True)
    with pytest.raises(RuntimeError):pg_control.check_control_generation(value,profile)
    assert events==['native','binary','connect'] and connection.closed==0
