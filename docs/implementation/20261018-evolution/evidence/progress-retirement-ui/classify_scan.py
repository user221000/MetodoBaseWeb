"""Classify exactly two whole source fingerprints, not arbitrary scanner hits."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

root = Path.cwd()
folder = root / 'docs/implementation/20261018-evolution/evidence/progress-retirement-ui'
report_path = folder / 'secret-scan.json'
data = report_path.read_bytes()
report = json.loads(data)
freeze_bytes = (folder / 'freeze.json').read_bytes()
assert hashlib.sha256(freeze_bytes).hexdigest() == 'ff3331e4131ec3cfedf0c4f33fa5cf9181e38f1d2bb91974dcbbe7ee35570313'
freeze = json.loads(freeze_bytes)
freeze_name = (folder / 'freeze.json').relative_to(root).as_posix()
locations = [item for item in report['findings'] if item['file'] == freeze_name]
expected = {72: 'web/static/js/api.js', 80: 'web/static/js/plan-publicacion-consumo.js'}
assert len(locations) == len(expected) and {item['line'] for item in locations} == set(expected)
private = Path(tempfile.mkdtemp(prefix='metodobase-retirement-ui-scan-'))
classified = []
with zipfile.ZipFile(private / 'protected-source-raw.zip', 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
    for item in locations:
        line = freeze_bytes.decode().splitlines()[item['line'] - 1]
        match = re.fullmatch(r'\s*"([^"]+)": "([0-9a-f]{64})",?', line)
        assert match is not None
        name, digest = match.groups()
        assert name == expected[item['line']] and freeze['protected_unchanged'][name] == digest
        source = (root / name).resolve()
        assert source.is_relative_to(root)
        raw = source.read_bytes()
        git = subprocess.run(['git', 'show', freeze['base'] + ':' + name], capture_output=True, check=True).stdout
        assert hashlib.sha256(raw).hexdigest() == digest == hashlib.sha256(git).hexdigest()
        zipped.writestr(name, raw)
        classified.append({'file': item['file'], 'line': item['line'], 'rule': item['rule'], 'source': name, 'source_sha256': digest, 'method': 'Whole immutable freeze line equals existing committed source SHA256 verified against RAW and base Git blob; exact bodies preserved in private ZIP; not a scanner allowlist'})
with zipfile.ZipFile(private / 'protected-source-raw.zip') as zipped:
    assert zipped.testzip() is None
    for item in classified:
        assert hashlib.sha256(zipped.read(item['source'])).hexdigest() == item['source_sha256']
full_report = private / 'secret-scan-full.json'
full_report.write_bytes(data)
assert full_report.read_bytes() == data
summary = {'command': 'python -X utf8 scripts/scan_secrets.py --gitleaks C:/Users/Consu/AppData/Local/Temp/metodobase-gitleaks-8.30.1/gitleaks.exe --report docs/implementation/20261018-evolution/evidence/progress-retirement-ui/secret-scan.json', 'scanner_exit_code': report['exit_code'], 'source_stable': report['source_stable'], 'files': len(report['files']), 'raw_findings': report['raw_finding_count'], 'existing_runner_classified': report['classified_finding_count'], 'remaining_before_review': report['remaining_finding_count'], 'own_findings': len(locations), 'own_fingerprint_classifications': classified, 'other_existing_file_findings': report['remaining_finding_count'] - len(locations), 'global_scan_accepted': False, 'full_report_private': str(full_report), 'full_report_bytes': len(data), 'full_report_sha256': hashlib.sha256(data).hexdigest(), 'protected_raw_zip': str(private / 'protected-source-raw.zip'), 'protected_raw_zip_sha256': hashlib.sha256((private / 'protected-source-raw.zip').read_bytes()).hexdigest(), 'reason_full_report_external': 'Preserve complete sanitized inherited-location output without duplicating it in feature commit; values are not exposed', 'no_scanner_or_allowlist_changes': True}
(folder / 'secret-scan-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf8')
assert report_path.resolve().is_relative_to(root)
report_path.unlink()  # Exact own generated file, after byte-exact private preservation.
print(json.dumps({'own_verified': len(classified), 'other_existing_file_findings': summary['other_existing_file_findings'], 'sources': [item['source'] for item in classified], 'full_report_private': str(full_report), 'full_report_sha256': summary['full_report_sha256']}))
