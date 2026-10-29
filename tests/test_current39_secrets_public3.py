"""Exact public-location extension; original scan and V9 contracts remain active."""
import ast
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import types
import zipfile

import pytest

from scripts import reviewed_scan_locations as review
from scripts import scan_secrets as original
from tests.ci_web39 import current_secret_locations as current
from tests.ci_web39 import scan_secrets as cli

ROOT = Path(__file__).resolve().parents[1]


def document():
    return current.read_registry(ROOT)


def snapshot(tmp_path):
    data = document()
    names = [r['path'] for r in data['parent_sources']] + [r['path'] for r in data['files']]
    hashes = {}
    for name in names:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = (ROOT / name).read_bytes()
        target.write_bytes(raw)
        hashes[name] = current.digest(raw)
    return data, hashes


def finding(record, frame):
    return {'StartLine': frame['line'], 'EndLine': frame['line'], 'RuleID': frame['rule'],
            'Match': object(), 'Secret': object(), 'Line': object()}


def loader(tmp_path, data):
    return current.adapted_loader(ROOT, data, review)


def test_registry_authenticates_three_public_values_from_original_payloads():
    data = document()
    provenance = data['provenance']
    now = base64.b64decode(provenance['current_api']['bytes_base64'], validate=True)
    assert current.digest(now) == provenance['current_api']['sha256']
    source = ast.parse((ROOT / data['files'][0]['path']).read_bytes())
    assignment = next(n for n in source.body if isinstance(n, ast.Assign)
                      and n.lineno == data['files'][0]['frames'][0]['line'])
    assert ast.literal_eval(assignment.value) == current.digest(now)
    prior = base64.b64decode(provenance['prior_commit']['bytes_base64'], validate=True)
    object_id = hashlib.sha1(b'commit ' + str(len(prior)).encode() + b'\0' + prior,
                            usedforsecurity=False).hexdigest()
    assert object_id == provenance['prior_commit']['object_id']
    old = base64.b64decode(provenance['prior_api']['bytes_base64'], validate=True)
    for record in data['files'][1:]:
        value = json.loads((ROOT / record['path']).read_bytes())['runtime_binding_update']
        assert value['prior_API_commit'] == object_id
        assert value['prior_API_normalized_lf_sha256'] == current.digest(old)


@pytest.mark.parametrize('index', range(3))
@pytest.mark.parametrize('crlf', [False, True])
def test_exact_six_file_frames_classify_once_and_ignore_scanner_values(tmp_path, index, crlf):
    data, hashes = snapshot(tmp_path)
    record = data['files'][index]
    path = tmp_path / record['path']
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    if crlf:
        raw = raw.replace(b'\n', b'\r\n')
    path.write_bytes(raw)
    hashes[record['path']] = current.digest(raw)
    frame = next(f for f in record['frames'] if f['source_digest'] == hashes[record['path']])
    adapter = loader(tmp_path, data)(tmp_path, hashes, '8.30.1')
    item = finding(record, frame)
    result = adapter.classify(item, record['path'])
    assert result == {'file': record['path'], 'line': frame['line'], 'rule': frame['rule'],
        'file_sha256': frame['source_digest'], 'physical_line_sha256': frame['line_digest'],
        'reason': current.REASON}
    assert adapter.classify(item, record['path']) is None


def test_legacy_is_first_and_result_is_untouched():
    expected = {'sentinel': object()}
    calls = []
    old = types.SimpleNamespace(classify=lambda *a: calls.append('old') or expected)
    new = types.SimpleNamespace(classify=lambda *a: calls.append('new'))
    assert current.CurrentLocations(old, new).classify({}, 'name') is expected
    assert calls == ['old']


@pytest.mark.parametrize('fault', ['byte', 'snapshot', 'inventory', 'line', 'rule', 'start',
    'end', 'boolean', 'multiline', 'path', 'mixed', 'bom', 'utf16', 'utf32', 'new-adjacent'])
def test_changed_source_location_or_encoding_never_classifies(tmp_path, fault):
    data, hashes = snapshot(tmp_path)
    record = data['files'][0]
    path = tmp_path / record['path']
    frame = next(f for f in record['frames'] if f['source_digest'] == hashes[record['path']])
    item = finding(record, frame)
    name = record['path']
    raw = path.read_bytes()
    if fault in {'byte', 'snapshot', 'new-adjacent'}:
        path.write_bytes(raw + (b' ' if fault != 'new-adjacent' else b'\nunknown = True\n'))
        if fault != 'snapshot':
            hashes[name] = current.digest(path.read_bytes())
    elif fault == 'inventory':
        hashes[name] = '0' * 64
    elif fault == 'line':
        path.write_bytes(b'\n' + raw)
        hashes[name] = current.digest(path.read_bytes())
    elif fault == 'rule':
        item['RuleID'] = 'unknown-rule'
    elif fault == 'start':
        item['StartLine'] += 1
    elif fault == 'end':
        item['EndLine'] += 1
    elif fault == 'boolean':
        item['StartLine'] = True
    elif fault == 'multiline':
        item['EndLine'] += 2
    elif fault == 'path':
        name += '.unreviewed'
        (tmp_path / name).write_bytes(raw)
        hashes[name] = current.digest(raw)
    elif fault == 'mixed':
        raw = raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n', 1)
        path.write_bytes(raw)
        hashes[name] = current.digest(raw)
    else:
        text = raw.decode('utf8')
        path.write_bytes((b'\xef\xbb\xbf' + raw) if fault == 'bom' else text.encode(fault))
        hashes[name] = current.digest(path.read_bytes())
    assert loader(tmp_path, data)(tmp_path, hashes, '8.30.1').classify(item, name) is None


@pytest.mark.parametrize('name', ['scripts/scan_secrets.py', 'scripts/reviewed_scan_locations.py',
    'scripts/data/reviewed_scan_locations_v9.zip', '.gitleaks.toml'])
def test_any_changed_parent_aborts_before_classification(tmp_path, name):
    data, hashes = snapshot(tmp_path)
    target = tmp_path / name
    target.write_bytes(target.read_bytes() + b' ')
    hashes[name] = current.digest(target.read_bytes())
    with pytest.raises(RuntimeError, match='output withheld'):
        loader(tmp_path, data)(tmp_path, hashes, '8.30.1')


def test_other_scanner_version_aborts(tmp_path):
    data, hashes = snapshot(tmp_path)
    with pytest.raises(RuntimeError, match='output withheld'):
        loader(tmp_path, data)(tmp_path, hashes, '8.30.2')


def test_main_keeps_its_code_and_only_one_private_global_changes():
    before = dict(vars(original))
    f = cli.delegated_main()
    assert f.__code__ is original.main.__code__
    assert f.__globals__ is not vars(original)
    assert [k for k in f.__globals__ if f.__globals__[k] is not vars(original)[k]] == [
        'load_reviewed_locations']
    assert vars(original) == before
    assert original.load_reviewed_locations is review.load_reviewed_locations


@pytest.mark.parametrize('name,module', [('scripts/scan_secrets.py', original),
    ('scripts/reviewed_scan_locations.py', review)])
def test_authenticated_git_lf_transport_retains_live_original_code(name, module):
    raw = (ROOT / name).read_bytes().replace(b'\r\n', b'\n')
    parent = next(p for p in document()['parent_sources'] if p['path'] == name)
    assert any(f['digest'] == current.digest(raw) and f['bytes'] == len(raw)
               for f in parent['frames'])
    current.authenticate_module(module, ROOT / name, raw)


@pytest.mark.parametrize('fault', ['scanner-code', 'scanner-global', 'loader-code',
    'reader-constant', 'reader-method', 'reader-extra', 'scanner-root',
    'scanner-filename', 'reader-filename', 'method-filename', 'module-path-alias',
    'import-equality-proxy', 'constant-equality-proxy', 'module-file-text-proxy',
    'code-filename-text-proxy', 'function-name-text-proxy', 'qualname-text-proxy',
    'function-module-text-proxy', 'module-name-text-proxy', 'defaults-tuple-proxy',
    'kwdefaults-dict-proxy', 'annotations-dict-proxy'])
def test_live_source_function_or_globals_substitution_rejects(monkeypatch, fault):
    class EqualProxy:
        def __eq__(self, other):
            return True

        def __ne__(self, other):
            return False

    class EqualDict(dict):
        def __eq__(self, other):
            return True

        def __ne__(self, other):
            return False

    class EqualText(str):
        def __eq__(self, other):
            return True

        def __ne__(self, other):
            return False

    class EqualTuple(tuple):
        def __eq__(self, other):
            return True

        def __ne__(self, other):
            return False

    if fault == 'scanner-code':
        monkeypatch.setattr(original, 'main', lambda: 0)
    elif fault == 'scanner-global':
        monkeypatch.setattr(original, 'load_reviewed_locations', lambda *a: None)
    elif fault == 'loader-code':
        monkeypatch.setattr(review, 'load_reviewed_locations', lambda *a: None)
    elif fault == 'reader-constant':
        monkeypatch.setattr(review, '_LIMIT', 1)
    elif fault == 'reader-method':
        monkeypatch.setattr(review.ReviewedLocations, 'classify', lambda *a: {})
    elif fault == 'reader-extra':
        monkeypatch.setattr(review, 'unreviewed', True, raising=False)
    elif fault == 'scanner-root':
        monkeypatch.setattr(original, 'ROOT', ROOT / 'unreviewed')
    elif fault == 'module-path-alias':
        monkeypatch.setattr(original, '__file__', str(ROOT / 'scripts/../scripts/scan_secrets.py'))
    elif fault == 'import-equality-proxy':
        monkeypatch.setattr(original, 'subprocess', EqualProxy())
    elif fault == 'constant-equality-proxy':
        monkeypatch.setattr(original, '_FRAGMENT_FINGERPRINT_PINS', EqualDict())
    elif fault == 'module-file-text-proxy':
        monkeypatch.setattr(original, '__file__', EqualText('unreviewed.py'))
    elif fault == 'code-filename-text-proxy':
        monkeypatch.setattr(original.main, '__code__',
            original.main.__code__.replace(co_filename=EqualText('unreviewed.py')))
    elif fault in {'function-name-text-proxy', 'qualname-text-proxy',
                   'function-module-text-proxy'}:
        field = {'function-name-text-proxy': '__name__', 'qualname-text-proxy': '__qualname__',
                 'function-module-text-proxy': '__module__'}[fault]
        monkeypatch.setattr(original.main, field, EqualText('unreviewed'))
    elif fault == 'module-name-text-proxy':
        monkeypatch.setattr(original, '__name__', EqualText('unreviewed'))
    elif fault == 'defaults-tuple-proxy':
        monkeypatch.setattr(original.main, '__defaults__', EqualTuple())
    elif fault == 'kwdefaults-dict-proxy':
        monkeypatch.setattr(original.main, '__kwdefaults__', EqualDict())
    elif fault == 'annotations-dict-proxy':
        monkeypatch.setattr(original.main, '__annotations__', EqualDict())
    else:
        function = {'scanner-filename': original.main,
            'reader-filename': review.load_reviewed_locations,
            'method-filename': review.ReviewedLocations.classify}[fault]
        monkeypatch.setattr(function, '__code__', function.__code__.replace(co_filename='unreviewed.py'))
    with pytest.raises(RuntimeError, match='output withheld'):
        cli.delegated_main()


@pytest.mark.parametrize('fault', ['extra-file', 'duplicate-file', 'missing-file',
    'duplicate-frame', 'extra-frame', 'path', 'line-bool', 'rule', 'version', 'encoding'])
def test_registry_schema_rejects_unknown_or_ambiguous_records(fault):
    data = copy.deepcopy(document())
    row = data['files'][0]
    if fault == 'extra-file':
        data['files'].append(copy.deepcopy(row))
    elif fault == 'duplicate-file':
        data['files'][1] = copy.deepcopy(row)
    elif fault == 'missing-file':
        data['files'].pop()
    elif fault == 'duplicate-frame':
        row['frames'][1] = copy.deepcopy(row['frames'][0])
    elif fault == 'extra-frame':
        row['frames'].append(copy.deepcopy(row['frames'][0]))
    elif fault == 'path':
        row['path'] = '../unreviewed'
    elif fault == 'line-bool':
        row['frames'][0]['line'] = True
    elif fault == 'rule':
        row['frames'][0]['rule'] = 'unknown-rule'
    elif fault == 'version':
        data['version'] = '8.30.2'
    else:
        row['frames'][0]['source_encoding'] = 'utf-16'
    with pytest.raises(RuntimeError, match='output withheld'):
        current.validate_registry(data)


@pytest.mark.parametrize('fault', ['digest', 'invalid-zip', 'extra-member', 'member',
    'duplicate-key', 'json', 'nan', 'oversized'])
def test_bounded_archive_rejects_malformed_or_rehashed_ambiguous_payloads(tmp_path, monkeypatch, fault):
    data = document()
    raw = json.dumps(data).encode()
    if fault == 'duplicate-key':
        raw = b'{"schema":1,"schema":2}'
    elif fault == 'json':
        raw = b'not JSON'
    elif fault == 'nan':
        raw = b'{"schema":NaN}'
    elif fault == 'oversized':
        raw = b' ' * (current.LIMIT + 1)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('wrong.json' if fault == 'member' else current.MEMBER, raw)
        if fault == 'extra-member':
            archive.writestr('other.json', b'{}')
    payload = buffer.getvalue() if fault != 'invalid-zip' else b'not ZIP'
    target = tmp_path / current.REGISTRY
    target.parent.mkdir(parents=True)
    target.write_bytes(payload)
    if fault != 'digest':
        monkeypatch.setattr(current, 'REGISTRY_DIGEST', current.digest(payload))
    with pytest.raises(RuntimeError, match='output withheld'):
        current.read_registry(tmp_path)


@pytest.mark.parametrize('name', ['../outside', '/outside', 'C:/outside', 'a\\b', 'a//b', 'a/./b'])
def test_source_path_aliases_reject_before_read(tmp_path, name):
    with pytest.raises(RuntimeError, match='output withheld'):
        current.source_path(tmp_path, name)


def test_source_symlink_or_reparse_point_rejects_without_read(monkeypatch, tmp_path):
    target = tmp_path / 'source'
    target.write_text('public fixture', encoding='utf8')
    original_lstat = Path.lstat

    def lstat(path):
        real = original_lstat(path)
        if path == target:
            return types.SimpleNamespace(st_mode=real.st_mode, st_file_attributes=0x400)
        return real

    monkeypatch.setattr(Path, 'lstat', lstat)
    with pytest.raises(RuntimeError, match='output withheld'):
        current.source_path(tmp_path, 'source')
