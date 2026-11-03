"""Keep PostgreSQL startup diagnostics finite and private."""
import hashlib
import json
import os

import pytest

from tests.ci_web41 import pg_bootstrap_diagnostic as subject


SOURCE = '389b366fd34bcf93f1c8d3c6ad5d427db16dad84'
LINE = (b'2026-11-03 10:25:11.123 UTC [12345] FATAL:  could not create lock file '
        b'"/var/run/postgresql/.s.PGSQL.55483.lock": Permission denied\n')


def stage(**changes):
    return json.dumps(dict(schema=subject.SCHEMA, phase='pg_ctl_start',
                           exception_type='CalledProcessError', child_exit=1) | changes).encode()


def test_exact_error_is_a_diagnostic_without_publishing_private_log():
    private = LINE + b'PRIVATE_ACCOUNT_SECRET_CANARY\n'
    result = subject.project_startup_reason(stage(), private, SOURCE)
    assert result['category'] == 'unix_socket_lock_permission_denied'
    assert result['acceptance_evidence'] is False
    assert result['log_bytes'] == len(private)
    assert result['log_sha256'] == hashlib.sha256(private).hexdigest()
    assert 'PRIVATE_ACCOUNT' not in json.dumps(result)
    assert '/var/run' not in json.dumps(result)


@pytest.mark.parametrize('log', [
    LINE.replace(b'55483', b'55484'), LINE.replace(b'/var/run', b'/tmp'),
    b'injected ' + LINE, LINE.rstrip() + b' extra\n', LINE + LINE,
    LINE.replace(b'Permission denied', b'No space left on device'),
    b'PRIVATE_ACCOUNT_SECRET_CANARY',
])
def test_other_or_ambiguous_errors_remain_unknown(log):
    result = subject.project_startup_reason(stage(), log, SOURCE)
    assert result['category'] == 'unknown' and result['acceptance_evidence'] is False


@pytest.mark.parametrize('raw', [None, stage(phase='initdb'),
                                      stage(exception_type='AssertionError', child_exit=None)])
def test_log_cannot_replace_required_process_failure(raw):
    assert subject.project_startup_reason(raw, LINE, SOURCE)['category'] == 'unknown'


@pytest.mark.parametrize('log', ['', b'', b'x' * 65537], ids=['wrong-type', 'empty', 'oversize'])
def test_invalid_log_input_is_rejected(log):
    with pytest.raises(ValueError):
        subject.project_startup_reason(stage(), log, SOURCE)


def test_missing_log_and_malformed_stage_remain_distinct():
    assert subject.project_startup_reason(stage(), None, SOURCE)['category'] == 'unknown'
    with pytest.raises(ValueError):
        subject.project_startup_reason(stage(message='private'), LINE, SOURCE)


def test_bounded_file_read_and_missing_file(tmp_path):
    directory = tmp_path / 'ci37-pg-cluster-private'
    directory.mkdir()
    path = directory / 'postgresql.private.log'
    assert subject.read_startup_log(path) is None
    path.write_bytes(LINE)
    assert subject.read_startup_log(path) == LINE
    assert path.read_bytes() == LINE


def test_wrong_path_directory_oversize_and_hardlink_are_rejected(tmp_path):
    directory = tmp_path / 'ci37-pg-cluster-private'
    directory.mkdir()
    path = directory / 'postgresql.private.log'
    with pytest.raises(ValueError):
        subject.read_startup_log(tmp_path / 'postgresql.private.log')
    path.mkdir()
    with pytest.raises(ValueError):
        subject.read_startup_log(path)
    path.rmdir()
    path.write_bytes(b'x' * 65537)
    with pytest.raises(ValueError):
        subject.read_startup_log(path)
    path.write_bytes(LINE)
    os.link(path, directory / 'other.log')
    with pytest.raises(ValueError):
        subject.read_startup_log(path)


def test_growing_log_is_rejected_with_a_bounded_read(tmp_path, monkeypatch):
    directory = tmp_path / 'ci37-pg-cluster-private'
    directory.mkdir()
    path = directory / 'postgresql.private.log'
    path.write_bytes(LINE)
    original_open = subject.Path.open

    def opening(target, *args, **kwargs):
        if target == path and args == ('rb',):
            with original_open(path, 'ab') as stream:
                stream.write(b'x' * 65537)
        return original_open(target, *args, **kwargs)

    monkeypatch.setattr(subject.Path, 'open', opening)
    with pytest.raises(ValueError, match='grew or changed'):
        subject.read_startup_log(path)
