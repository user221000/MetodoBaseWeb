"""Independent finite-registry attacks; only synthetic data and private fixtures."""
import copy
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from scripts import reviewed_scan_locations as registry


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pack(raw, compression=zipfile.ZIP_DEFLATED):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=compression) as archive:
        archive.writestr('reviewed-locations.json', raw)
    return out.getvalue()


@pytest.fixture
def case(tmp_path, monkeypatch):
    root = tmp_path / 'snapshot'
    root.mkdir()
    cfg = b'[extend]\nuseDefault=true\n'
    content = 'public peer metadata \u00e1\r\nsecond pinned line\n'.encode()
    name = 'docs/evidence/finite-peer.txt'
    source = root / name
    source.parent.mkdir(parents=True)
    source.write_bytes(content)
    (root / '.gitleaks.toml').write_bytes(cfg)
    data = {'schema': 1, 'version': '8.30.1', 'config_digest': digest(cfg), 'files': [
        {'path': name, 'source_digest': digest(content), 'scanner_digest': digest(content),
         'lines': [{'number': i, 'digest': digest(line), 'rules': ['peer-rule']}
                   for i, line in enumerate(content.split(b'\n')[:2], 1)]}]}
    path = root / registry._REVIEW_DATA_PATH
    path.parent.mkdir(parents=True)

    def write(value=None, raw=None, compression=zipfile.ZIP_DEFLATED, anchored=True):
        blob = pack(raw if raw is not None else json.dumps(value or data).encode(), compression)
        path.write_bytes(blob)
        if anchored:
            monkeypatch.setattr(registry, '_REVIEW_DATA_DIGEST', digest(blob))
        return blob

    write()
    hashes = {name: digest(content), '.gitleaks.toml': digest(cfg)}
    item = {'StartLine': 1, 'EndLine': 1, 'RuleID': 'peer-rule'}
    return root, hashes, item, data, write, name, source, path


@pytest.mark.parametrize('attack', [
    'extra_record_field', 'extra_line_field', 'float_schema', 'float_line',
    'negative_line', 'line_over_limit', 'empty_files', 'files_object', 'line_object',
    'rules_string', 'rule_too_long', 'rule_nonascii', 'upper_digest',
    'digest_trailing_lf', 'path_trailing_slash', 'path_double_slash',
    'path_parent_component', 'path_drive_relative', 'line_array_scalar',
])
def test_additional_schema_attacks_are_withheld(case, attack):
    root, hashes, _, data, write, _, _, _ = case
    record = data['files'][0]
    line = record['lines'][0]
    if attack == 'extra_record_field':
        record['extra'] = 'PEER_PRIVATE_MARKER'
    elif attack == 'extra_line_field':
        line['extra'] = 'PEER_PRIVATE_MARKER'
    elif attack == 'float_schema':
        data['schema'] = 1.0
    elif attack == 'float_line':
        line['number'] = 1.0
    elif attack == 'negative_line':
        line['number'] = -1
    elif attack == 'line_over_limit':
        line['number'] = 2_000_001
    elif attack == 'empty_files':
        data['files'] = []
    elif attack == 'files_object':
        data['files'] = {}
    elif attack == 'line_object':
        record['lines'] = {}
    elif attack == 'rules_string':
        line['rules'] = 'peer-rule'
    elif attack == 'rule_too_long':
        line['rules'] = ['a' * 129]
    elif attack == 'rule_nonascii':
        line['rules'] = ['peer-\u00e1']
    elif attack == 'upper_digest':
        record['source_digest'] = 'A' * 64
    elif attack == 'digest_trailing_lf':
        line['digest'] += '\n'
    elif attack == 'path_trailing_slash':
        record['path'] += '/'
    elif attack == 'path_double_slash':
        record['path'] = 'docs//finite-peer.txt'
    elif attack == 'path_parent_component':
        record['path'] = 'docs/../finite-peer.txt'
    elif attack == 'path_drive_relative':
        record['path'] = 'C:finite-peer.txt'
    else:
        record['lines'].append(42)
    write(data)
    with pytest.raises(RuntimeError, match='registry is invalid; output withheld') as caught:
        registry.load_reviewed_locations(root, hashes, '8.30.1')
    assert caught.value.__suppress_context__
    assert 'PEER_PRIVATE_MARKER' not in str(caught.value)


@pytest.mark.parametrize('compression', [zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA])
def test_unapproved_compression_fails_before_content_use(case, compression):
    root, hashes, _, _, write, _, _, _ = case
    write(compression=compression)
    with pytest.raises(RuntimeError, match='output withheld'):
        registry.load_reviewed_locations(root, hashes, '8.30.1')


@pytest.mark.parametrize('location', ['root', 'record', 'line'])
def test_duplicate_keys_in_every_object_are_rejected(case, location):
    root, hashes, _, data, write, _, _, _ = case
    raw = json.dumps(data).encode()
    needle = {'root': b'"schema": 1', 'record': b'"path": ', 'line': b'"number": 1'}[location]
    replacement = {'root': b'"schema":1,"schema":1', 'record': b'"path":"PEER_PRIVATE_MARKER","path": ', 'line': b'"number":1,"number":1'}[location]
    assert needle in raw
    write(raw=raw.replace(needle, replacement, 1))
    with pytest.raises(RuntimeError, match='output withheld') as caught:
        registry.load_reviewed_locations(root, hashes, '8.30.1')
    assert 'PEER_PRIVATE_MARKER' not in str(caught.value)


@pytest.mark.parametrize('count,accepted', [(100_000, True), (100_001, False)])
def test_total_pin_limit_at_real_boundary(case, count, accepted):
    root, hashes, _, data, write, _, _, _ = case
    original = data['files'][0]['lines'][0]
    rows = []
    remaining = count
    while remaining:
        n = min(128, remaining)
        rows.append({'number': len(rows) + 1, 'digest': original['digest'], 'rules': ['r' + str(i) for i in range(n)]})
        remaining -= n
    data['files'][0]['lines'] = rows
    write(data)
    if accepted:
        parsed = registry.load_reviewed_locations(root, hashes, '8.30.1')
        assert sum(len(f['lines']) for f in parsed.files.values()) == count
    else:
        with pytest.raises(RuntimeError, match='output withheld'):
            registry.load_reviewed_locations(root, hashes, '8.30.1')


@pytest.mark.parametrize('count,accepted', [(2000, True), (2001, False)])
def test_file_count_limit_at_real_boundary(case, count, accepted):
    root, hashes, _, data, write, _, _, _ = case
    row = data['files'][0]
    data['files'] = [{**copy.deepcopy(row), 'path': 'files/' + str(i) + '.txt'} for i in range(count)]
    write(data)
    if accepted:
        assert len(registry.load_reviewed_locations(root, hashes, '8.30.1').files) == count
    else:
        with pytest.raises(RuntimeError, match='output withheld'):
            registry.load_reviewed_locations(root, hashes, '8.30.1')


def test_next_scan_cannot_reuse_previous_accepted_file_cache(case):
    root, hashes, item, _, _, name, source, _ = case
    first = registry.load_reviewed_locations(root, hashes, '8.30.1')
    assert first.classify(item, name) is not None
    source.write_bytes(source.read_bytes() + b'new unreviewed suffix\n')
    second = registry.load_reviewed_locations(root, hashes, '8.30.1')
    assert second.classify(item, name) is None
    assert first.checked is not second.checked


def test_matching_source_hash_cannot_mask_wrong_copied_bytes(case):
    root, hashes, item, _, _, name, source, _ = case
    source.write_bytes(b'new content\n')
    loaded = registry.load_reviewed_locations(root, hashes, '8.30.1')
    assert loaded.classify(item, name) is None


def test_absent_source_cannot_be_classified(case):
    root, hashes, item, _, _, name, source, _ = case
    source.unlink()
    assert registry.load_reviewed_locations(root, hashes, '8.30.1').classify(item, name) is None


def test_missing_config_with_present_registry_aborts(case):
    root, hashes, _, _, _, _, _, _ = case
    (root / '.gitleaks.toml').unlink()
    with pytest.raises(RuntimeError, match='output withheld'):
        registry.load_reviewed_locations(root, hashes, '8.30.1')


def test_fields_resembling_scanner_secrets_never_supply_evidence(case):
    root, hashes, item, _, _, name, _, _ = case

    class Forbidden:
        def __str__(self):
            raise AssertionError('secret field was consulted')

    item.update(Match=Forbidden(), Secret=Forbidden(), Line=Forbidden(), Fingerprint=Forbidden())
    result = registry.load_reviewed_locations(root, hashes, '8.30.1').classify(item, name)
    assert result is not None
    assert not {'Match', 'Secret', 'Line', 'Fingerprint'} & result.keys()


@pytest.mark.parametrize('attack', ['changed_source_after_scan', 'new_file_after_scan', 'missing_dataset', 'corrupt_dataset', 'rule_neighbor', 'endline_neighbor'])
def test_main_withholds_or_blocks_despite_other_reviewed_findings(case, monkeypatch, tmp_path, capsys, attack):
    from scripts import scan_secrets as scanner
    root, _, item, _, _, name, source, data_path = case
    tool = tmp_path / 'scanner.exe'
    tool.write_bytes(b'peer synthetic scanner boundary; never executed')
    report = tmp_path / 'sanitized.json'
    names = ['.gitleaks.toml', name, registry._REVIEW_DATA_PATH]
    if attack == 'missing_dataset':
        data_path.unlink()
        names.remove(registry._REVIEW_DATA_PATH)
    elif attack == 'corrupt_dataset':
        data_path.write_bytes(b'PEER_PRIVATE_MARKER')
    monkeypatch.setattr(scanner, 'ROOT', root)
    monkeypatch.setattr(sys, 'argv', ['peer', '--gitleaks', str(tool), '--report', str(report)])

    def run(argv, **kw):
        if argv[0] == 'git':
            return subprocess.CompletedProcess(argv, 0, stdout=('\0'.join(names) + '\0').encode())
        if argv[1] == 'version':
            return subprocess.CompletedProcess(argv, 0, stdout='8.30.1\n')
        copied = Path(argv[2])
        findings = [{**item, 'File': str(copied / name), 'Secret': 'PEER_PRIVATE_MARKER', 'Match': 'PEER_PRIVATE_MARKER'}]
        if attack in {'rule_neighbor', 'endline_neighbor'}:
            other = dict(findings[0])
            other['RuleID' if attack == 'rule_neighbor' else 'EndLine'] = 'unreviewed-peer-rule' if attack == 'rule_neighbor' else 2
            findings.append(other)
        Path(argv[argv.index('--report-path') + 1]).write_bytes(json.dumps(findings).encode())
        if attack == 'changed_source_after_scan':
            source.write_bytes(source.read_bytes() + b'unreviewed suffix\n')
        elif attack == 'new_file_after_scan':
            (root / 'new.txt').write_bytes(b'new')
            names.append('new.txt')
        return subprocess.CompletedProcess(argv, 1, stdout='PEER_PRIVATE_MARKER', stderr='PEER_PRIVATE_MARKER')

    monkeypatch.setattr(scanner.subprocess, 'run', run)
    if attack == 'corrupt_dataset':
        with pytest.raises(RuntimeError, match='output withheld') as caught:
            scanner.main()
        assert 'PEER_PRIVATE_MARKER' not in str(caught.value)
        assert not report.exists()
    else:
        expected = 2 if attack.endswith('after_scan') else 1
        assert scanner.main() == expected
        result = json.loads(report.read_bytes())
        assert result['exit_code'] == 1 and result['effective_exit_code'] == expected
        assert result['classified_finding_count'] == (0 if attack == 'missing_dataset' else 1)
        assert result['remaining_finding_count'] == (0 if attack.endswith('after_scan') else 1)
        assert 'PEER_PRIVATE_MARKER' not in report.read_text()
    output = capsys.readouterr()
    assert 'PEER_PRIVATE_MARKER' not in output.out + output.err
