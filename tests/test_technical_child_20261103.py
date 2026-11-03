"""Source-only successor controls; no Docker/build/runtime acceptance."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import subprocess

import pytest

from tests.ci_image57 import authority, context, production_child, source_proof, technical_child as child
from tests.ci_web39 import quality, verify_quality

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture(scope='module')
def payloads():
    return child.read_payloads(ROOT)


def test_all19_current_inputs_invert_to_exact12_git_parent_and_original_web(payloads):
    parent = child.inverse(payloads)
    assert len(payloads) == 19 and len(parent) == 13
    for name, pin in child.PARENT_PINS.items():
        expected = subprocess.check_output(['git', 'show', child.SOURCE_BASIS + ':' + name], cwd=ROOT)
        assert child.record(parent[name]) == pin and parent[name] == expected
    expected = subprocess.check_output(['git', 'show', child.SOURCE_BASIS + ':requirements_web.lock'], cwd=ROOT)
    assert parent['requirements_web.lock'] == expected
    restored, transition = context.native_parent_payloads(payloads)
    assert transition == child.transition(production_child.transition(context.native_transition()))
    historical = context.json_object(authority.raw('container-inputs.json.RAW'))['candidate_files']
    assert all(child.record(restored[name])['raw_sha256'] == pin['raw_sha256'] for name, pin in historical.items())


@pytest.mark.parametrize('name', tuple(child.PINS))
@pytest.mark.parametrize('fault', ['body', 'size', 'CRLF'])
def test_every_current_native_input_rejects_unreviewed_bytes_before_inverse(payloads, name, fault):
    value = dict(payloads)
    raw = value[name]
    value[name] = (bytes([raw[0] ^ 1]) + raw[1:] if fault == 'body' else
                   raw + b'\n' if fault == 'size' else raw.replace(b'\n', b'\r\n'))
    assert value[name] != raw
    with pytest.raises(ValueError):
        context.native_parent_payloads(value)


@pytest.mark.parametrize('fault', ['missing', 'extra', 'mixed_parent_lock', 'mixed_parent_docker', 'bool_size', 'blob'])
def test_finite_membership_and_authenticated_fields_reject(payloads, fault):
    value = dict(payloads)
    if fault == 'missing':
        value.pop(child.ACTIVE_SOURCE_PINS)
    elif fault == 'extra':
        value[child.NATIVE_PREFIX + 'unreviewed.py'] = b'unreviewed'
    elif fault.startswith('mixed_parent'):
        name = 'Dockerfile' if fault.endswith('docker') else 'requirements-container.lock'
        value[name] = child.inverse(payloads)[name]
    else:
        records = {name: child.record(raw) for name, raw in value.items()}
        records['Dockerfile']['bytes' if fault == 'bool_size' else 'git_blob'] = True if fault == 'bool_size' else '0' * 40
        with pytest.raises(ValueError):
            child.pins(records)
        return
    with pytest.raises(ValueError):
        context.native_parent_payloads(value)


def test_legacy12_and_current19_authentication_remain_separate(payloads):
    original = {name: raw for name, raw in child.inverse(payloads).items() if name in child.PARENT_PINS}
    records = {name: child.record(raw) for name, raw in original.items()}
    pins, transition = context.native_pins(records)
    assert len(pins) == 12 and transition == production_child.transition(context.native_transition())
    assert len(context.native_pins({name: child.record(raw) for name, raw in payloads.items()})[0]) == 19
    for source in (records, {name: child.record(raw) for name, raw in payloads.items()}):
        source = dict(source, **{'runtime-source/unreviewed.py': child.record(b'not reviewed')})
        with pytest.raises(ValueError):
            context.native_pins(source)
    assert not child.is_transition({'schema': child.SCHEMA})
    with pytest.raises(ValueError):
        child.inverse(original)


@pytest.mark.parametrize('fault', ['file', 'directory', 'removed'])
def test_physical_six_input_namespace_is_closed(tmp_path, payloads, fault):
    for name, raw in payloads.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    directory = tmp_path / child.NATIVE_PREFIX
    if fault == 'file':
        (directory / 'unreviewed').write_bytes(b'x')
    elif fault == 'directory':
        (directory / 'ignored').mkdir()
    else:
        (tmp_path / child.ACTIVE_SOURCE_PINS).unlink()
    with pytest.raises(ValueError):
        child.read_payloads(tmp_path)


def test_quality_source_admits_current19_and_original21_proof_without_runtime_claim():
    value = quality.native_source_inputs(ROOT)
    assert value['native_input_count'] == 19 and value['inherited_input_count'] == 10
    assert value['parent_native_merkle_objects'] == 21 and value['runtime_distributions_expected'] == 57
    assert child.is_transition(value['native_input_transition'])
    assert value['scope'] == 'source_inputs_only_no_build_runtime_OS_isolation_or_SCA_acceptance'


def test_quality_copy_carries_all19_source_inputs_byte_exact(tmp_path, payloads):
    target = authority.private_directory(tmp_path / 'source', ROOT)
    records = verify_quality.copy_source(ROOT, target)
    for name, raw in payloads.items():
        assert (target / name).read_bytes() == raw and records[name]['sha256'] == hashlib.sha256(raw).hexdigest()
    assert quality.native_source_inputs(target) == quality.native_source_inputs(ROOT)


def test_native_origins_are_exact7_plus38_with_one_namespace_header_adaptation():
    _, lock = child.details()
    prepared = child.expected_prepared(lock)
    assert len(lock['psf_selected_sha256']) == 7 and len(lock['expat_selected_sha256']) == 38 and len(prepared) == 45
    assert prepared['Modules/_elementtree.c'] == lock['psf_selected_sha256']['Modules/_elementtree.c']
    assert prepared['Modules/expat/expat_external.h'] == lock['namespace_adaptation']['after_sha256']
    assert lock['compile_sources']['_elementtree'] == ['Modules/_elementtree.c']
    assert len(lock['compile_sources']['pyexpat']) == 5
    assert len(lock['base_file_sha256']) == 219 and len(lock['ca_trust']['ca_der_sha256']) == 148
    invalid = deepcopy(lock)
    invalid['expat_selected_sha256']['../unreviewed.c'] = 'a' * 64
    with pytest.raises(ValueError):
        child.expected_prepared(invalid)


def test_original_docker_copy_parser_includes_every_one_of19_critical_inputs(payloads):
    sources = source_proof.copy_sources(payloads['Dockerfile'])
    selected = set()
    for name in sources:
        path = ROOT / name
        if path.is_dir():
            selected.update(p.relative_to(ROOT).as_posix() for p in path.rglob('*') if p.is_file())
        else:
            selected.add(path.relative_to(ROOT).as_posix())
    assert set(child.PINS) <= selected
    assert {name for name in selected if name.startswith('runtime-source/')} == {
        name for name in child.PINS if name.startswith('runtime-source/')}


def test_current_quality_adds_remote_backup_to_all_three_gates_without_changing_parent_scope():
    from tests.ci_web37 import quality as parent
    assert quality.CURRENT_OPERATIONAL == (*parent.OPERATIONAL, 'scripts/backup_remote.py')
    assert 'scripts/backup_remote.py' not in parent.OPERATIONAL
    assert quality.maintained_targets() == [*parent.RUNTIME, *parent.OPERATIONAL, 'scripts/backup_remote.py']
    assert ROOT / 'scripts/backup_remote.py' in quality.syntax_paths()
    source = (ROOT / 'tests/ci_web39/quality.py').read_text(encoding='utf8')
    assert source.count('*maintained_targets()') == 2
