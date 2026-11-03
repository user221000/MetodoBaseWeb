"""Current41 historical source views are finite; current behavior remains separate."""
from copy import deepcopy
import importlib
from pathlib import Path
import socket
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

from tests.ci_web41 import native22_oracle as subject, source_companion

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def database_schema():
    """No application fixtures or database are used by these source controls."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture(scope='module')
def authority():
    return subject.authorities()


def test_exact_five_host_sources_are_checked_before_retained_bytes_are_returned(authority):
    original, replay, proof, retained = authority
    assert len(subject.HOST_NAMES) == 5 and len(subject.CONSUMERS) == 3
    assert set(retained) - set(original.ADDITIONAL_NAMES) == subject.HOST_NAMES
    assert len(original.ADDITIONAL_NAMES) == 6
    view = subject.HistoricalRoot(ROOT, replay, proof, retained)
    for name in sorted(subject.HOST_NAMES):
        actual = (ROOT / name).read_bytes()
        assert (len(actual), subject.digest(actual)) in subject.HOST_FRAMES[name]
        result = (view / name).read_bytes()
        assert result is retained[name]
        assert (len(result), subject.digest(result)) == subject.ORIGINAL_FRAMES[name]
    assert (view / subject.PROVIDER).read_bytes() != (ROOT / subject.PROVIDER).read_bytes()


def test_original22_assertions_keep_exact_function_code_and_no_global_source_or_module_is_patched(authority, monkeypatch):
    original, replay, _, _ = authority
    from tests import test_security_native35_v7_peer as old
    native_root, replay_root = original.ROOT, replay.ROOT
    old_export = original.export
    module_ids = {name: value for name, value in sys.modules.items() if name in {original.__name__, replay.__name__, old.__name__}}
    function = getattr(old, original.TEST_NAME)

    def forbidden(*_args, **_kwargs):
        pytest.fail('Historical source assertions must not launch any process or socket')

    for name in ('Popen', 'run', 'check_output'):
        monkeypatch.setattr(subprocess, name, forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    copied = subject.export()[original.TEST_NAME]
    assert copied.__code__ is function.__code__
    assert copied.__defaults__ == function.__defaults__
    assert copied.__kwdefaults__ == function.__kwdefaults__
    assert copied.__dict__ == function.__dict__
    copied()
    assert original.ROOT is native_root and replay.ROOT is replay_root
    assert original.export is old_export
    assert all(sys.modules[name] is module for name, module in module_ids.items())


@pytest.mark.parametrize('name', sorted(subject.HOST_NAMES))
@pytest.mark.parametrize('fault', ['byte', 'length', 'move', 'recount-original'])
def test_no_other_byte_location_or_recounted_original_claim_can_enter_the_view(tmp_path, authority, name, fault):
    _, replay, proof, retained = authority
    target = tmp_path / name
    target.parent.mkdir(parents=True)
    actual = (ROOT / name).read_bytes()
    target.write_bytes(actual)
    copied_retained = dict(retained)
    fake_proof = SimpleNamespace(manifest=deepcopy(proof.manifest))
    view = subject.HistoricalRoot(tmp_path, replay, fake_proof, copied_retained)
    assert (view / name).read_bytes() == retained[name]
    if fault == 'byte':
        target.write_bytes(bytes([actual[0] ^ 1]) + actual[1:])
    elif fault == 'length':
        target.write_bytes(actual + b'\n')
    elif fault == 'move':
        moved = tmp_path / ('moved/' + name)
        moved.parent.mkdir(parents=True)
        target.rename(moved)
    else:
        copied_retained[name] += b'\n'
        record = fake_proof.manifest['helper_union'][name]
        record.update(bytes=len(copied_retained[name]), raw_sha256=subject.digest(copied_retained[name]))
    with pytest.raises((ValueError, OSError)):
        (view / name).read_bytes()


@pytest.mark.parametrize('fault', ['byte', 'length', 'mixed-lines'])
def test_whole_consumer_source_is_pinned_without_generic_newline_admission(tmp_path, monkeypatch, fault):
    name = subject.ORACLE
    target = tmp_path / name
    target.parent.mkdir(parents=True)
    actual = (ROOT / name).read_bytes()
    target.write_bytes(actual)
    monkeypatch.setattr(subject, 'ROOT', tmp_path)
    assert subject.source(name) == actual
    if fault == 'byte':
        target.write_bytes(bytes([actual[0] ^ 1]) + actual[1:])
    elif fault == 'length':
        target.write_bytes(actual + b'\n')
    else:
        lf = actual.replace(b'\r\n', b'\n')
        target.write_bytes(lf.replace(b'\n', b'\r\n', 1))
    with pytest.raises(ValueError, match='complete native41'):
        subject.source(name)


@pytest.mark.parametrize('name', ['tests/new.py', '../tests/other.py', 'tests/ci_web37/Native22_frames.py'])
def test_unknown_source_names_are_rejected_before_file_io(monkeypatch, name):
    monkeypatch.setattr(subject, 'plain', lambda *_: pytest.fail('Unknown identity reached file I/O'))
    with pytest.raises(ValueError, match='explicit native41 source identities'):
        subject.source(name)


def test_wrong_consumer_cannot_instantiate_a_pytest_collector():
    with pytest.raises(ValueError, match='three explicit'):
        subject.consumer_module(ROOT / 'tests/test_google33_http.py', None)


def test_wrong_module_and_replaced_callable_cannot_enter_a_historical_clone(pytestconfig, monkeypatch):
    path = ROOT / subject.NATIVE_CONTROLS
    raw = subject.source(subject.NATIVE_CONTROLS)
    fake = ModuleType('tests.unreviewed')
    fake.__file__ = str(path)
    with pytest.raises(ValueError, match='exact native41 historical control modules'):
        subject._clone(fake, path, subject._SubjectView(), raw, pytestconfig)
    original = importlib.import_module('tests.test_ci_web37_native22_frames')
    name = 'test_original22_assertions_execute_without_Git_process_or_network'
    def changed():
        return None
    changed.__module__ = original.__name__
    monkeypatch.setattr(original, name, changed)
    with pytest.raises(ValueError, match='assertion callable differs'):
        subject._clone(original, path, subject._SubjectView(), raw, pytestconfig)


def test_one_changed_archive_byte_cannot_supply_original_frames(tmp_path, authority):
    original, replay, _, _ = authority
    raw = (original.FIXTURES / 'native11-retained-originals.zip').read_bytes()
    (tmp_path / 'native11-retained-originals.zip').write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    with pytest.raises(ValueError, match='finite archive differs'):
        replay.retained_native11(tmp_path)


def test_other_paths_and_unknown_facade_attributes_have_no_historical_transport(authority):
    _, replay, proof, retained = authority
    with pytest.raises(ValueError, match='five exact'):
        subject._HistoricalRead(ROOT, 'tests/new.py', replay, proof, retained).read_bytes()
    for obj in (subject._SubjectView(), subject._ReplayView()):
        with pytest.raises(AttributeError):
            getattr(obj, 'service_admission')


def test_current41_native35_binding_uses_the_original39_provider_with_all_identity_checks():
    from tests.ci_web41 import composition
    from tests import test_security_native35_v7_peer as original
    compiled = source_companion.source_bytes('tests/ci_web41/composition.py').decode()
    assert 'from tests.ci_web39 import native35_control_fixtures' in compiled
    assert 'tests/ci_web39/native35_control_fixtures.py' in compiled
    assert 'tests.ci_web41.native35_control_fixtures' not in compiled
    assert compiled.count('tests.ci_web39.native35_control_fixtures') == 2
    namespace, bindings = composition.clone_namespace(original, composition.native35_entry())
    fixture = composition.fixture_function(namespace.historical_profile_input)
    assert fixture.__module__ == 'tests.ci_web39.native35_control_fixtures'
    assert bindings['original_module_unmodified'] is True
    assert bindings['fixture_bindings'][0]['current_provider'] == 'tests.ci_web39.native35_control_fixtures.historical_profile_input'
