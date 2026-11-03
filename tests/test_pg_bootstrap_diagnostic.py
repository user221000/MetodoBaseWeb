"""Reject diagnostic data that could expose free-form provider/SQL arguments."""
import json

import pytest

from tests.ci_web41 import pg_bootstrap_diagnostic as subject

SOURCE = 'f0a1e3d687334514c3d691b6fb305935ef6da3c5'


def raw(**changes):
    value = dict(schema=subject.SCHEMA, phase='pg_ctl_start', exception_type='CalledProcessError', child_exit=1)
    return json.dumps(value | changes).encode()


def test_original_failure_phase_and_exit_are_reported_without_acceptance():
    value = subject.project(raw(), SOURCE)
    assert value['phase'] == 'pg_ctl_start' and value['exception_type'] == 'CalledProcessError'
    assert value['child_exit'] == 1 and value['diagnostic_available'] is True
    assert value['acceptance_evidence'] is False and value['source_commit'] == subject.SOURCE


@pytest.mark.parametrize('changes', [
    {'phase': 'SQL ' + 'private value'}, {'phase': None}, {'exception_type': 'private message'},
    {'child_exit': True}, {'child_exit': 0}, {'child_exit': 256}, {'child_exit': -256},
    {'child_exit': '1'}, {'child_exit': None}, {'schema': 'other'}, {'message': 'private value'},
    {'exception_type': 'AssertionError', 'child_exit': 1},
])
def test_unbounded_or_inconsistent_fields_are_rejected(changes):
    with pytest.raises(ValueError):
        subject.project(raw(**changes), SOURCE)


def test_duplicate_field_cannot_replace_an_earlier_value():
    value = raw()[:-1] + b',"phase":"initdb"}'
    with pytest.raises(ValueError, match='Duplicate'):
        subject.project(value, SOURCE)


def test_missing_diagnostic_is_explicitly_unknown(tmp_path):
    value = subject.project(subject.read(tmp_path / 'absent.json'), SOURCE)
    assert value['diagnostic_available'] is False and value['phase'] == 'unknown'
    assert value['acceptance_evidence'] is False


def test_signal_exit_and_nonprocess_exception_remain_distinct():
    assert subject.project(raw(child_exit=-9), SOURCE)['child_exit'] == -9
    assert subject.project(raw(exception_type='PermissionError', child_exit=None), SOURCE)['child_exit'] is None


def test_oversized_raw_and_invalid_helper_identity_are_rejected():
    with pytest.raises(ValueError):
        subject.project(b' ' * 1025, SOURCE)
    with pytest.raises(ValueError):
        subject.project(raw(), SOURCE + 'unexpected')


def test_read_rejects_directory_and_preserves_original_file(tmp_path):
    with pytest.raises(ValueError):
        subject.read(tmp_path)
    path = tmp_path / 'stage.json'
    original = raw()
    path.write_bytes(original)
    assert subject.read(path) == original and path.read_bytes() == original


def test_growing_input_is_read_with_a_fixed_bound(tmp_path, monkeypatch):
    path = tmp_path / 'growing.json'
    path.write_bytes(raw())
    original_open = subject.Path.open

    class Reader:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def read(self, size):
            assert size == 1025
            return self.stream.read(size)

    def opening(target, *args, **kwargs):
        if target == path and args == ('rb',):
            with original_open(path, 'ab') as stream:
                stream.write(b'x' * 2048)
            return Reader(original_open(target, *args, **kwargs))
        return original_open(target, *args, **kwargs)

    monkeypatch.setattr(subject.Path, 'open', opening)
    with pytest.raises(ValueError, match='grew beyond'):
        subject.read(path)
