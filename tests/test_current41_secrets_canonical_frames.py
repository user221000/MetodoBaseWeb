"""Exact V9 framing admits no extra source byte, coordinate or rule."""
import hashlib
import io
import json
import zipfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.ci_web39 import current_secret_locations as current

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def database_schema():
    """Source/scan contracts only; no database or application services."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture(scope='module')
def document():
    return current.read_canonical_registry(ROOT)


@pytest.fixture(scope='module')
def authority():
    raw = (ROOT / 'scripts/data/reviewed_scan_locations_v9.zip').read_bytes()
    assert current.digest(raw) == current.CANONICAL_PARENT_DIGEST
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        data = json.loads(archive.read('reviewed-locations.json'))
    return SimpleNamespace(files={row['path']: {
        'source_digest': row['source_digest'], 'scanner_digest': row['scanner_digest'],
        'lines': {(line['number'], rule): line['digest'] for line in row['lines'] for rule in line['rules']},
    } for row in data['files']})


def item(row):
    return {'StartLine': row['start_line'], 'EndLine': row['end_line'],
            'StartColumn': row['start_column'], 'EndColumn': row['end_column'],
            'RuleID': row['rule'], 'Secret': 'never_authority', 'Match': 'never_authority'}


def case(tmp_path, document, authority, transport='Git-LF', all_files=False):
    records = document['files'] if all_files else document['files'][:1]
    hashes = {}
    for record in records:
        frame = next(row for row in record['frames'] if row['transport'] == transport)
        original = (ROOT / record['path']).read_bytes()
        # Only fixture construction transforms bytes, after proving one entire
        # known frame; the production reader never normalizes a source.
        assert current.digest(original) in {row['source_digest'] for row in record['frames']}
        content = original.replace(b'\r\n', b'\n')
        if transport == 'approved-V9-CRLF':
            content = content.replace(b'\n', b'\r\n')
        assert current.digest(content) == frame['source_digest']
        path = tmp_path / record['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        hashes[record['path']] = frame['source_digest']
    # A permissive previous classifier must never bypass a registered span.
    previous = SimpleNamespace(classify=lambda *_: {'reason': 'unchanged previous V9'})
    bridge = current.CanonicalFrames(previous, authority, tmp_path, hashes, document)
    record = records[0]
    frame = next(row for row in record['frames'] if row['transport'] == transport)
    return bridge, record['path'], frame, hashes


@pytest.mark.parametrize('transport', ['Git-LF', 'approved-V9-CRLF'])
def test_all2250_exact_spans_and_both_complete_frames_are_classified_once(tmp_path, document, authority, transport):
    bridge, _, _, _ = case(tmp_path, document, authority, transport, all_files=True)
    total = 0
    for record in document['files']:
        frame = next(row for row in record['frames'] if row['transport'] == transport)
        for row in frame['findings']:
            result = bridge.classify(item(row), record['path'])
            assert result['reason'] == current.CANONICAL_REASON
            assert result['file_sha256'] == frame['source_digest']
            assert result['physical_line_sha256'] == row['line_digest']
            assert bridge.classify(item(row), record['path']) is None
            total += 1
    assert total == 2250


@pytest.mark.parametrize('transport', ['Git-LF', 'approved-V9-CRLF'])
@pytest.mark.parametrize('fault', ['start-line', 'end-line', 'start-column', 'end-column',
                                  'rule', 'bool', 'missing-column', 'source-hash',
                                  'other-byte', 'same-line-injection', 'moved-line', 'missing-file'])
def test_registered_paths_never_fall_back_to_previous_on_any_unreviewed_input(tmp_path, document, authority, transport, fault):
    bridge, name, frame, hashes = case(tmp_path, document, authority, transport)
    finding = item(frame['findings'][0])
    path = tmp_path / name
    if fault in {'start-line', 'end-line', 'start-column', 'end-column'}:
        key = {'start-line': 'StartLine', 'end-line': 'EndLine', 'start-column': 'StartColumn', 'end-column': 'EndColumn'}[fault]
        finding[key] += 1
    elif fault == 'rule':
        finding['RuleID'] = 'not-reviewed'
    elif fault == 'bool':
        finding['StartLine'] = True
    elif fault == 'missing-column':
        del finding['EndColumn']
    elif fault == 'source-hash':
        hashes[name] = '0' * 64
    elif fault == 'missing-file':
        path.unlink()
    elif fault == 'moved-line':
        path.write_bytes(b'\n' + path.read_bytes())
    elif fault == 'same-line-injection':
        content = path.read_bytes()
        path.write_bytes(content.replace(b'\n', b' unreviewed\n', 1))
    else:
        content = path.read_bytes()
        path.write_bytes(bytes([content[0] ^ 1]) + content[1:])
    assert bridge.classify(finding, name) is None


def test_only_outside90_paths_delegate_without_changing_historical_reader(tmp_path, document, authority):
    bridge, name, frame, hashes = case(tmp_path, document, authority)
    assert bridge.classify(item(frame['findings'][0]), 'new-unreviewed-path') == {'reason': 'unchanged previous V9'}
    # A known registered name with a missing/unknown complete source never
    # inherits the permissive previous classifier.
    hashes.clear()
    assert bridge.classify(item(frame['findings'][0]), name) is None


def test_five_frame_specific_column_changes_are_not_interchangeable(tmp_path, document, authority):
    changes = 0
    for record in document['files']:
        a, b = record['frames']
        def key(row):
            return (row['start_line'], row['end_line'], row['start_column'], row['end_column'], row['rule'])
        if {key(row) for row in a['findings']} != {key(row) for row in b['findings']}:
            changes += 1
            subset = dict(document, files=[record] + [row for row in document['files'] if row is not record])
            for transport, wrong_frame in [('Git-LF', b), ('approved-V9-CRLF', a)]:
                bridge, name, actual, _ = case(tmp_path / f'{changes}-{transport}', subset, authority, transport)
                actual_keys = {key(row) for row in actual['findings']}
                wrong = next(row for row in wrong_frame['findings'] if key(row) not in actual_keys)
                assert bridge.classify(item(wrong), name) is None
                assert bridge.classify(item(actual['findings'][0]), name)['reason'] == current.CANONICAL_REASON
    assert changes == 5


@pytest.mark.parametrize('fault', ['missing', 'tampered'])
def test_current_cli_registry_source_is_mandatory_and_byte_pinned(tmp_path, fault):
    if fault == 'tampered':
        target = tmp_path / current.CANONICAL_REGISTRY
        target.parent.mkdir(parents=True)
        target.write_bytes((ROOT / current.CANONICAL_REGISTRY).read_bytes() + b'x')
    with pytest.raises(RuntimeError, match='output withheld'):
        current.read_canonical_registry(tmp_path)


@pytest.mark.parametrize('fault', ['authority', 'line-digest', 'duplicate-span', 'column-bool', 'extra-field', 'config-version'])
def test_mutated_authority_or_ambiguous_finite_data_never_becomes_admission(tmp_path, document, authority, fault):
    data = deepcopy(document)
    record = data['files'][0]
    frame = record['frames'][0]
    if fault == 'authority':
        record['authority_source_digest'] = '0' * 64
    elif fault == 'line-digest':
        frame['findings'][0]['authority_line_digest'] = '0' * 64
    elif fault == 'duplicate-span':
        frame['findings'].append(deepcopy(frame['findings'][0]))
    elif fault == 'column-bool':
        frame['findings'][0]['start_column'] = True
    elif fault == 'extra-field':
        data['unreviewed'] = True
    else:
        data['version'] = '8.30.2'
    with pytest.raises(RuntimeError, match='output withheld'):
        current.CanonicalFrames(SimpleNamespace(classify=lambda *_: None), authority, tmp_path, {}, data)


def test_old_adapter_branch_has_no_new_registry_dependency():
    assert current.adapted_loader.__defaults__ == (None, None)
    assert hashlib.sha256((ROOT / 'scripts/data/reviewed_scan_locations_v9.zip').read_bytes()).hexdigest() == current.CANONICAL_PARENT_DIGEST
