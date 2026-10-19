from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib, json

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE = Path(r'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence')
DEST = BASE / 'linux-recovery28-image-bc365c1'
prior = BASE / 'linux-recovery28-image-abd559a'
manifest = prior / 'evidence-manifest.json'
assert hashlib.sha256(manifest.read_bytes()).hexdigest() == 'fc0053a28039d61c8b7a82b99fd6f13b4a9ed595d9d8cd4711d96c1223aa6705'
matrix_file = prior / 'os-audit/triage-matrix/matrix-73.json'
old = {r['id']: r for r in json.loads(matrix_file.read_text(encoding='utf-8'))}
scan = json.loads((DEST / 'os-audit/results/scan.json').read_text(encoding='utf-8'))
by_id = {}
for target in scan['Results']:
    for item in target.get('Vulnerabilities', []):
        by_id.setdefault(item['VulnerabilityID'], []).append(item)
assert len(by_id) == 71
assert set(old) - set(by_id) == {'DSA-6549-1', 'TEMP-1147318-639065'}
rows = []
for key, findings in sorted(by_id.items()):
    original = old[key]
    rows.append({'id': key, 'source_package': original['source_package'],
                 'current_scanner_entries': len(findings),
                 'binary_packages': sorted({r['PkgName'] for r in findings}),
                 'current_scanner_statuses': dict(Counter(r['Status'] for r in findings)),
                 'primary_url': original['primary_url'],
                 'debian_trixie': original['debian_trixie'],
                 'tracker_explicit_upstream_fix_links': original['tracker_explicit_upstream_fix_links'],
                 'newer_debian_fixed_releases': original['newer_debian_fixed_releases'],
                 'prior_applicability_classification_for_review': original['applicability_classification'],
                 'review_state': 'OPEN; no accepted exception or product reachability conclusion',
                 'evidence_limit': 'Prior component probes apply to the prior image. Other 86 OS package versions match; current application search is a separate partial query, not a complete call graph.'})
groups = Counter(r['source_package'] for r in rows)
report = {'generated_utc': datetime.now(timezone.utc).isoformat(),
          'image_id': scan['Metadata']['ImageID'],
          'source_commit': 'bc365c13b9af9e24129a56b4068059a67bb3afa0',
          'prior_manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
          'prior_matrix_sha256': hashlib.sha256(matrix_file.read_bytes()).hexdigest(),
          'closed_from_current_scan_only': [
              {'id': key, 'reason': 'Same-DB scan no longer reports this XZ alias after verified liblzma5 u2 backport. No global ignore added.'}
              for key in ['DSA-6549-1', 'TEMP-1147318-639065']],
          'remaining_ids': len(rows), 'remaining_entries': sum(r['current_scanner_entries'] for r in rows),
          'remaining_source_groups': len(groups), 'ids_per_source_group': dict(sorted(groups.items())),
          'scope': 'Carries all remaining findings forward without risk acceptance. Debian primary snapshot and applicability notes remain linked to the sealed prior evidence.',
          'rows': rows}
data = (json.dumps(report, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
for p in [LAB / 'evidence/os-audit-bc365c1/triage-carry-forward.json', DEST / 'os-audit/triage-carry-forward.json']:
    with p.open('xb') as stream:
        stream.write(data)
source = Path(__file__)
with (DEST / 'drivers-and-freeze' / source.name).open('xb') as stream:
    stream.write(source.read_bytes())
print(json.dumps({'remaining_ids': len(rows), 'remaining_source_groups': len(groups),
                  'entries': report['remaining_entries'], 'sha256': hashlib.sha256(data).hexdigest()}))
