"""The four current contexts do not admit other bytes, paths, lines or findings."""
import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from scripts import reviewed_scan_locations as review
from tests.ci_web39 import current_secret_locations as current

ROOT = Path(__file__).resolve().parents[1]


def snapshot(tmp_path, crlf=False):
    prior = current.read_registry(ROOT)
    document = current.read_current_registry(ROOT)
    names = {r['path'] for r in prior['parent_sources'] + prior['files'] + document['files']}
    names.update((current.REGISTRY, current.CURRENT_REGISTRY))
    hashes = {}
    for name in names:
        raw = (ROOT / name).read_bytes()
        if name in current.CURRENT_LOCATIONS:
            raw = raw.replace(b'\r\n', b'\n')
            if crlf:
                raw = raw.replace(b'\n', b'\r\n')
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        hashes[name] = current.digest(raw)
    return prior, document, hashes


def load(tmp_path, data):
    prior, document, hashes = data
    return current.adapted_loader(ROOT, prior, review, document)(tmp_path, hashes, '8.30.1')


def item(number, rule='generic-api-key'):
    # Deliberately hostile scanner text is never classification evidence.
    return {'StartLine': number, 'EndLine': number, 'RuleID': rule,
            'Secret': object(), 'Match': object(), 'Line': object()}


CONTEXTS = [(name, line) for name, numbers in current.CURRENT_LOCATIONS.items() for line in numbers]


@pytest.mark.parametrize('crlf', [False, True])
def test_exact_four_classify_once_under_both_explicit_transports(tmp_path, crlf):
    data = snapshot(tmp_path, crlf)
    adapter = load(tmp_path, data)
    for name, number in CONTEXTS:
        result = adapter.classify(item(number), name)
        assert result['file'] == name and result['line'] == number
        assert result['reason'] == current.CURRENT_REASON
        assert result['file_sha256'] == data[2][name]
        assert adapter.classify(item(number), name) is None


@pytest.mark.parametrize('name,number', CONTEXTS)
@pytest.mark.parametrize('fault', ['byte', 'snapshot', 'inventory', 'path', 'line', 'rule',
                                  'bool', 'multiline', 'utf16', 'bom', 'mixed'])
def test_changed_context_remains_blocking(tmp_path, name, number, fault):
    data = snapshot(tmp_path)
    target = tmp_path / name
    value = item(number)
    raw = target.read_bytes()
    if fault in {'byte', 'snapshot'}:
        target.write_bytes(raw + b'\n# changed\n')
        if fault == 'byte':
            data[2][name] = current.digest(target.read_bytes())
    elif fault == 'inventory':
        data[2][name] = '0' * 64
    elif fault == 'path':
        name += '.unknown'
        (tmp_path / name).write_bytes(raw)
        data[2][name] = current.digest(raw)
    elif fault == 'line':
        value = item(number + 1)
    elif fault == 'rule':
        value = item(number, 'unknown-rule')
    elif fault == 'bool':
        value['StartLine'] = True
    elif fault == 'multiline':
        value['EndLine'] += 1
    else:
        if fault == 'utf16':
            raw = raw.decode().encode('utf-16')
        elif fault == 'bom':
            raw = b'\xef\xbb\xbf' + raw
        else:
            raw = raw.replace(b'\n', b'\r\n', 1)
        target.write_bytes(raw)
        data[2][name] = current.digest(raw)
    assert load(tmp_path, data).classify(value, name) is None


@pytest.mark.parametrize('fault', ['extra', 'duplicate', 'missing', 'path', 'rule', 'bool',
                                  'frame', 'encoding', 'version', 'legacy'])
def test_new_schema_does_not_admit_extra_or_ambiguous_contexts(fault):
    data = copy.deepcopy(current.read_current_registry(ROOT))
    if fault == 'extra':
        data['extra'] = True
    elif fault == 'duplicate':
        data['files'][1] = copy.deepcopy(data['files'][0])
    elif fault == 'missing':
        data['files'].pop()
    elif fault == 'path':
        data['files'][0]['path'] = '../outside'
    elif fault == 'rule':
        data['files'][0]['frames'][0]['lines'][0]['rule'] = 'unknown-rule'
    elif fault == 'bool':
        data['files'][0]['frames'][0]['lines'][0]['number'] = True
    elif fault == 'frame':
        data['files'][0]['frames'][1] = copy.deepcopy(data['files'][0]['frames'][0])
    elif fault == 'encoding':
        data['files'][0]['frames'][0]['source_encoding'] = 'utf-16'
    elif fault == 'version':
        data['version'] = '8.30.2'
    else:
        data['legacy_extension_digest'] = '0' * 64
    with pytest.raises(RuntimeError, match='output withheld'):
        current.validate_current_registry(data)


@pytest.mark.parametrize('fault', ['digest', 'duplicate-key', 'extra-member', 'oversized'])
def test_new_archive_authentication_and_bounded_parse(tmp_path, monkeypatch, fault):
    raw = json.dumps(current.read_current_registry(ROOT)).encode()
    if fault == 'duplicate-key':
        raw = b'{"schema":1,"schema":2}'
    elif fault == 'oversized':
        raw = b' ' * (current.LIMIT + 1)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(current.MEMBER, raw)
        if fault == 'extra-member':
            archive.writestr('other.json', b'{}')
    payload = buffer.getvalue()
    target = tmp_path / current.CURRENT_REGISTRY
    target.parent.mkdir(parents=True)
    target.write_bytes(payload)
    if fault != 'digest':
        monkeypatch.setattr(current, 'CURRENT_REGISTRY_DIGEST', hashlib.sha256(payload).hexdigest())
    with pytest.raises(RuntimeError, match='output withheld'):
        current.read_current_registry(tmp_path)


def test_renewal_registry_change_inside_snapshot_aborts(tmp_path):
    data = snapshot(tmp_path)
    target = tmp_path / current.CURRENT_REGISTRY
    target.write_bytes(target.read_bytes() + b' ')
    with pytest.raises(RuntimeError, match='output withheld'):
        load(tmp_path, data)
