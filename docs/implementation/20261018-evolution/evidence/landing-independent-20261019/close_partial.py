"""Freeze scoped R29/R34 evidence before author fixes; never overwrites histories."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def save(root, name, data):
    with (root / name).open('x', encoding='utf8') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


landing = json.loads((OUT / 'http-source.json').read_text())
red = json.loads((OUT / 'own-dynamic-with-composition/source.json').read_text())
assert landing['phases'][0]['junit'] == {'tests': 12, 'failures': 0, 'errors': 0, 'skipped': 0}
assert red['junit'] == {'tests': 2, 'failures': 2, 'errors': 0, 'skipped': 0}
save(OUT, 'partial-summary.json', {
    'head': landing['head'], 'decision': 'Pending:12 author HTTP pass;2 runtime billing-period consistency negatives fail. Browser not yet run.',
    'sources': 756, 'sources_stable_during_runs': True, 'packages': 89, 'packages_stable': True,
    'own_criterion_sha256': sha(OUT / 'test_landing_dynamic_review.py.txt'),
    'red_details': 'Cards follow changed runtime year/TST catalog; global note still says con periodo mensual in both factories.',
    'initial_harness_error': '2 external Temp setup errors retained; explicit author conftest fixes only test composition. Criterion bytes identical.',
    'author_and_coordinator_notified': True, 'no_product_or_ci_edits': True,
})
history = OUT.parent / 'history-independent-20261019'
save(history, 'partial-summary.json', {
    'head': '49eb44124d36a0d0aeaf732d7f720d969f1d517c',
    'decision': 'Partial:74 author Python and23 new VM pass; separate security500 negatives block final acceptance. Browser not yet run.',
    'backend': json.loads((history / 'backend74-49eb441/source.json').read_text()),
    'vm': json.loads((history / 'vm23-49eb441/source.json').read_text()),
    'preservation_sha256': sha(history / 'preservation.json'),
    'historical_runtime_sources_unchanged': 18, 'original_sql_assertions_unchanged': 7,
    'raw_tested_archives_authenticated': 2,
    'own_tests_prepared_not_executed': ['8 parameterized SQLite edge cases', '3 UI browser control/delivery cases'],
    'source_boundary': 'All photos close at49; later error-boundary fix must receive a separate source/photo and affected-case gate.',
    'no_product_or_ci_edits': True,
})
for root in [OUT, history]:
    files = {path.relative_to(root).as_posix(): sha(path) for path in sorted(root.rglob('*')) if path.is_file()}
    save(root, 'partial-manifest.json', {'files': files, 'count': len(files), 'scope': 'Frozen additive pre-fix evidence excluding this manifest itself.'})
    print(json.dumps({'prefix': root.name, 'files': len(files), 'summary_sha256': sha(root / 'partial-summary.json'),
                      'manifest_sha256': sha(root / 'partial-manifest.json')}))
