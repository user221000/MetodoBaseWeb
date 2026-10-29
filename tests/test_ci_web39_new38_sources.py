"""Current39 bindings preserve original38 programs and refuse source drift.

These source/admission controls execute no Node process, browser or database.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from tests.ci_web39 import new38_sources as guard

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = json.loads((ROOT / guard.HISTORICAL_MAP).read_bytes())
CURRENT = json.loads((ROOT / guard.CURRENT_MAP).read_bytes())
INPUTS = sorted({name for entry in ORIGINAL['phases'].values() for name in entry['input_files']})


@pytest.fixture(scope='session', autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def tree(root, *, crlf=False):
    for name in (guard.HISTORICAL_MAP, guard.CURRENT_MAP, *INPUTS):
        raw = (ROOT / name).read_bytes().replace(b'\r\n', b'\n')
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw.replace(b'\n', b'\r\n') if crlf else raw)
    return root


def write_mapping(root, mapping):
    (root / guard.CURRENT_MAP).write_text(json.dumps(mapping), encoding='utf8')


def check_all(root):
    mapping = guard.load_mapping(root)
    for entry in mapping['phases'].values():
        guard.require_sources(root, entry)
    return mapping


@pytest.mark.parametrize('crlf', [False, True])
def test_exact_original38_programs_and_labels_pass_on_current39_Git_inputs_in_uniform_host_frames(tmp_path, crlf):
    mapping = check_all(tree(tmp_path, crlf=crlf))
    assert mapping['source_scope'] == guard.SOURCE_SCOPE
    assert len(INPUTS) == 14
    for phase, original in ORIGINAL['phases'].items():
        current = mapping['phases'][phase]
        assert current['script'] == original['script']
        assert current['preloader'] == original['preloader']
        assert current['expected_cases'] == original['expected_cases']
        assert current['cases'] == original['cases'] == guard.CASES[phase]
        assert set(current['input_files']) == set(original['input_files'])
        program = (tmp_path / original['script']).read_bytes().replace(b'\r\n', b'\n')
        assert hashlib.sha256(program).hexdigest() == original['input_files'][original['script']]['sha256']


@pytest.mark.parametrize('name', INPUTS)
def test_each_program_API_helper_and_other_transitive_body_change_is_rejected(tmp_path, name):
    root = tree(tmp_path)
    target = root / name
    raw = target.read_bytes()
    target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(ValueError, match='direct/transitive canonical Git source'):
        check_all(root)


@pytest.mark.parametrize('framing', ['bare-CR', 'mixed-LF-CRLF'])
def test_text_transport_rejects_bare_CR_and_mixed_endings(tmp_path, framing):
    root = tree(tmp_path)
    path = root / 'tests/e2e/browser_harness31.cjs'
    raw = path.read_bytes()
    assert raw.count(b'\n') > 1
    path.write_bytes(raw.replace(b'\n', b'\r' if framing == 'bare-CR' else b'\r\n', 1))
    with pytest.raises(ValueError, match='uniform LF or CRLF'):
        check_all(root)


@pytest.mark.parametrize('fault', [
    'scope', 'input-commit', 'extra-phase', 'missing-phase', 'ordered-labels',
    'duplicate-label', 'untyped-count', 'program-pin', 'missing-transitive',
    'extra-transitive', 'API-pin', 'helper-pin', 'preloader', 'case-ID-scope',
])
def test_descriptor_cannot_expand_scope_or_relax_original_programs_and_criteria(tmp_path, fault):
    root = tree(tmp_path)
    mapping = copy.deepcopy(CURRENT)
    entry = mapping['phases']['node-product38']
    if fault == 'scope':
        mapping['source_scope'] = 'historical38 sources accepted'
    elif fault == 'input-commit':
        mapping['canonical_input_Git_commit'] = '0' * 40
    elif fault == 'extra-phase':
        mapping['phases']['unreviewed'] = copy.deepcopy(entry)
    elif fault == 'missing-phase':
        mapping['phases'].pop('node-password38')
    elif fault == 'ordered-labels':
        entry['expected_cases'].reverse()
    elif fault == 'duplicate-label':
        entry['expected_cases'][1] = entry['expected_cases'][0]
    elif fault == 'untyped-count':
        entry['cases'] = 13.0
    elif fault == 'program-pin':
        mapping['original38_program_pins']['node-product38']['original_RAW_sha256'] = '0' * 64
    elif fault == 'missing-transitive':
        entry['input_files'].pop(guard.API_PATH)
    elif fault == 'extra-transitive':
        entry['input_files']['web/static/js/unreviewed.js'] = copy.deepcopy(entry['input_files'][guard.API_PATH])
    elif fault == 'API-pin':
        entry['input_files'][guard.API_PATH]['sha256'] = '0' * 64
    elif fault == 'helper-pin':
        entry['input_files']['tests/e2e/browser_harness31.cjs']['sha256'] = '0' * 64
    elif fault == 'preloader':
        entry['preloader'] = 'tests/e2e/unreviewed.cjs'
    else:
        entry['preparation_case_ids_not_requirement_IDs'] = False
    write_mapping(root, mapping)
    with pytest.raises(ValueError):
        check_all(root)


@pytest.mark.parametrize('field,value', [('git_blob', '0' * 40), ('bytes', 1), ('bytes', True)])
def test_correct_SHA_cannot_hide_false_Git_blob_size_or_untyped_size(tmp_path, field, value):
    root = tree(tmp_path)
    mapping = copy.deepcopy(CURRENT)
    for entry in mapping['phases'].values():
        entry['input_files'][guard.API_PATH][field] = value
    write_mapping(root, mapping)
    with pytest.raises(ValueError):
        check_all(root)


def test_original38_descriptor_is_immutable_even_if_new_descriptor_rehashes_it(tmp_path):
    root = tree(tmp_path)
    original = copy.deepcopy(ORIGINAL)
    original['phases']['node-product38']['expected_cases'][0] = 'unreviewed criterion'
    raw = json.dumps(original).encode()
    (root / guard.HISTORICAL_MAP).write_bytes(raw)
    current = copy.deepcopy(CURRENT)
    current['original38_mapping']['sha256_LF'] = hashlib.sha256(raw).hexdigest()
    current['original38_mapping']['git_blob'] = guard.git_blob(raw)
    write_mapping(root, current)
    with pytest.raises(ValueError, match='authenticated historical38'):
        guard.load_mapping(root)


def test_duplicate_JSON_fields_are_not_silently_shadowed(tmp_path):
    root = tree(tmp_path)
    raw = (root / guard.CURRENT_MAP).read_bytes()
    (root / guard.CURRENT_MAP).write_bytes(b'{"schema":"unreviewed",' + raw[1:])
    with pytest.raises(ValueError, match='Duplicate current39 Node descriptor field'):
        guard.load_mapping(root)


@pytest.mark.parametrize('phase', list(guard.CASES))
def test_runner_refuses_drift_before_starting_its_Node_process(tmp_path, monkeypatch, phase):
    from tests.ci_web39 import run_web
    root = tree(tmp_path)
    target = root / guard.API_PATH
    target.write_bytes(target.read_bytes() + b'\n// unreviewed API body\n')
    monkeypatch.setattr(run_web, 'ROOT', root)
    monkeypatch.setattr(run_web, 'execute', lambda *args, **kwargs: pytest.fail('Node must not start before source admission'))
    with pytest.raises(ValueError, match='direct/transitive canonical Git source'):
        run_web.new_node_gate(tmp_path / 'inert-private', {}, phase)
