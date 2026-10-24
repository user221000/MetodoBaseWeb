"""Current v9 boundaries; historical v8's 35 cases remain a separate version."""
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

import pytest

from scripts import reviewed_scan_locations as review
from tests.ci_web37.serial_security_transport import historical_source

ROOT = Path(__file__).resolve().parents[1]
OLD = 'scripts/data/reviewed_scan_locations_v8.zip'
CURRENT = 'scripts/data/reviewed_scan_locations_v9.zip'
OLD_DIGEST = 'a6b0027ddbf2d651d26dd98d611e04729cefaf7508f0ff8a1ed5ac8c2d76d47f'
CURRENT_DIGEST = 'dfa3fbfa3ff923a96cad28495bb76c46f17672fa62504af4ad53985d9a7060b4'
PROPOSAL = 'tests/fixtures/r05-v9-proposal.zip'
PROPOSAL_DIGEST = '0095694c3bd4f0344ecca792f15a7dfa9128320da4dd32b843c4565577860449'
LOADER8 = 'tests/fixtures/r05-v8-reader-original.py.RAW'
TEST8 = 'tests/fixtures/r05-v8-tests-original.py.RAW'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def archive(name, pin):
    raw = (ROOT / name).read_bytes()
    assert digest(raw) == pin
    result = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as source:
        for entry in source.infolist():
            assert entry.filename not in result
            assert not entry.is_dir() and not entry.flag_bits & 1
            result[entry.filename] = source.read(entry)
    return result


def proposal():
    values = archive(PROPOSAL, PROPOSAL_DIGEST)
    document = json.loads(values.pop('proposal.json'))
    assert all(name == 'objects/' + digest(raw) for name, raw in values.items())
    assert set(values) == {'objects/' + row['origin_object_sha256']
                           for row in document['witnesses'] if 'origin_object_sha256' in row}
    return document, values


def locations():
    document, _ = proposal()
    return [{'file': row['path'], 'line': line['number'], 'rule': rule,
             'file_sha256': row['source_digest'], 'physical_line_sha256': line['digest']}
            for row in document['files'] for line in row['lines'] for rule in line['rules']]


def test_v9_adds_only_eight_disjoint_records_and_preserves_all907_v8_records():
    old = json.loads(archive(OLD, OLD_DIGEST)['reviewed-locations.json'])
    new = json.loads(archive(CURRENT, CURRENT_DIGEST)['reviewed-locations.json'])
    document, _ = proposal()
    assert len(old['files']) == 907 and len(new['files']) == 915
    assert new['files'][:907] == old['files'] and new['files'][907:] == document['files']
    assert {r['path'] for r in old['files']}.isdisjoint(r['path'] for r in document['files'])
    assert {k: v for k, v in old.items() if k != 'files'} == {k: v for k, v in new.items() if k != 'files'}
    assert sum(len(r['lines']) for r in old['files']) == 57259
    assert sum(len(r['lines']) for r in new['files']) == 57271
    assert sum(len(x['rules']) for r in old['files'] for x in r['lines']) == 57267
    assert sum(len(x['rules']) for r in new['files'] for x in r['lines']) == 57281
    assert review._REVIEW_DATA_PATH == CURRENT and review._REVIEW_DATA_DIGEST == CURRENT_DIGEST


def test_current_loader_has_only_three_literal_changes_from_authenticated_v8():
    original = (ROOT / LOADER8).read_bytes()
    assert digest(original) == 'bca03e24026a60511312019fdb2c9bde39de598dc1c74097c7f660370fb68cf3'
    inverse = (ROOT / 'scripts/reviewed_scan_locations.py').read_bytes()
    for before, after in [(CURRENT, OLD), (CURRENT_DIGEST, OLD_DIGEST), ('registry v9', 'registry v8')]:
        assert inverse.count(before.encode()) == 1
        inverse = inverse.replace(before.encode(), after.encode())
    assert inverse == original


def test_historical_v8_bodies_change_only_two_explicit_source_bindings():
    original = (ROOT / TEST8).read_bytes()
    assert digest(original) == '0abd632d8bf73af6d262ccbfa88064f1bd2f990288d262bb34cb9fc4bbdb9de5'
    current = (ROOT / 'tests/test_secret_scan_finite_v8.py').read_bytes()
    for new, old in [
        ('from tests.ci_web37.r05_v8_transport import original_source, review',
         'from scripts import reviewed_scan_locations as review'),
        ('inverse = original_source()', 'inverse = (ROOT / "scripts/reviewed_scan_locations.py").read_bytes()'),
    ]:
        assert current.count(new.encode()) == 1
        current = current.replace(new.encode(), old.encode())
    assert current == original
    from tests.ci_web37.r05_v8_transport import original_source, review as historical
    assert original_source() == (ROOT / LOADER8).read_bytes()
    assert historical._REVIEW_DATA_PATH == OLD and historical._REVIEW_DATA_DIGEST == OLD_DIGEST


def test_all28_instances_have_exact_hashed_object_or_synthetic_constructor_provenance():
    document, objects = proposal()
    assert len(document['witnesses']) == 28
    for row in document['witnesses']:
        raw = historical_source(ROOT, row['file'])
        assert digest(raw) == row['file_sha256']
        physical = raw.split(b'\n')[row['line']-1]
        assert digest(physical) == row['physical_LF_line_sha256']
        span = physical[row['StartColumn']-1:row['EndColumn']]
        if row['kind'] in {'computed_source_SHA256', 'computed_lock_block_SHA256'}:
            values = re.findall(rb'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])', span)
            assert len(values) == 1 and digest(values[0]) == row['value_sha256']
            payload = objects['objects/' + row['origin_object_sha256']]
            assert digest(payload).encode() == values[0]
        elif row['kind'] == 'authenticated_Git_commit_OID':
            value = json.loads(raw)['runtime_binding_update']['prior_API_commit']
            assert digest(value.encode()) == row['value_sha256'] and value.encode() in span
            payload = objects['objects/' + row['origin_object_sha256']]
            frame = b'commit ' + str(len(payload)).encode() + b'\0' + payload
            assert hashlib.sha1(frame, usedforsecurity=False).hexdigest() == value
        else:
            assert row['kind'] == 'synthetic_fixture_prefix_not_complete_credential'
            assignment = next(n for n in ast.walk(ast.parse(raw))
                              if isinstance(n, ast.Assign) and n.lineno == row['line'])
            value = assignment.value
            assert isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add)
            assert isinstance(value.left, ast.BinOp) and isinstance(value.left.op, ast.Add)
            prefix, dynamic, suffix = value.left.left, value.left.right, value.right
            assert isinstance(prefix, ast.Constant) and type(prefix.value) is str
            assert isinstance(suffix, ast.Constant) and type(suffix.value) is str
            assert digest(prefix.value.encode()) == row['prefix_sha256'] and prefix.value.encode() in span
            assert isinstance(dynamic, ast.Attribute) and dynamic.attr == 'hex'
            call = dynamic.value
            assert isinstance(call, ast.Call) and not call.args and not call.keywords
            assert isinstance(call.func, ast.Attribute) and call.func.attr == 'uuid4'
            assert isinstance(call.func.value, ast.Name) and call.func.value.id == 'uuid'


def snapshot(tmp_path):
    document, _ = proposal()
    for name in (CURRENT, '.gitleaks.toml', *[r['path'] for r in document['files']]):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(historical_source(ROOT, name))
    return {path.relative_to(tmp_path).as_posix(): digest(path.read_bytes())
            for path in tmp_path.rglob('*') if path.is_file()}


@pytest.mark.parametrize('index', range(14))
def test_current14_location_rule_pairs_require_complete_source_and_line_pins(tmp_path, index):
    row = locations()[index]
    hashes = snapshot(tmp_path)
    finding = {'StartLine': row['line'], 'EndLine': row['line'], 'RuleID': row['rule'],
               'Match': object(), 'Secret': object(), 'Line': False}
    result = review.load_reviewed_locations(tmp_path, hashes, '8.30.1').classify(finding, row['file'])
    assert result == row | {'reason': 'finite independently reviewed non-credential evidence; registry v9'}


@pytest.mark.parametrize('fault', ['source-byte', 'source-byte-with-recount', 'inventory', 'path',
                                   'line', 'rule', 'archive', 'config', 'version'])
def test_new_registry_keeps_unreviewed_inputs_blocking(tmp_path, fault):
    row = locations()[0]
    hashes = snapshot(tmp_path)
    name, version = row['file'], '8.30.1'
    finding = {'StartLine': row['line'], 'EndLine': row['line'], 'RuleID': row['rule']}
    if fault.startswith('source-byte'):
        target = tmp_path / name
        target.write_bytes(target.read_bytes() + b' ')
        if fault == 'source-byte-with-recount':
            hashes[name] = digest(target.read_bytes())
    elif fault == 'inventory':
        hashes[name] = '0' * 64
    elif fault == 'path':
        name += '.unreviewed'
    elif fault == 'line':
        finding.update(StartLine=1, EndLine=1)
    elif fault == 'rule':
        finding['RuleID'] = 'unreviewed-new-rule'
    elif fault in {'archive', 'config'}:
        target = tmp_path / (CURRENT if fault == 'archive' else '.gitleaks.toml')
        target.write_bytes(target.read_bytes() + b' ')
    else:
        version = '8.30.2'
    if fault in {'archive', 'config', 'version'}:
        with pytest.raises(RuntimeError):
            review.load_reviewed_locations(tmp_path, hashes, version)
    else:
        assert review.load_reviewed_locations(tmp_path, hashes, version).classify(finding, name) is None
