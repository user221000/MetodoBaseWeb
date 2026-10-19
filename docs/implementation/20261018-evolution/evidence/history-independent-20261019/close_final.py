"""Close scoped independent R34 QA; retain all historical/failed harness artifacts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r'F:\MetodoBaseWeb-history-ui-20261019')
OUT = Path(__file__).resolve().parent
EVIDENCE = OUT.parent
HEAD = '57cdc0d51848203bdd89c0b9f0f3c426f1b285d8'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf8'))


def save(name, data):
    with (OUT / name).open('x', encoding='utf8') as stream:
        json.dump(data, stream, indent=2); stream.write('\n')


prior = load(OUT / 'partial-manifest.json')
assert all(sha(OUT / path) == value for path, value in prior['files'].items())
backend = load(OUT / 'backend74-49eb441/source.json')
vm = load(OUT / 'vm23-49eb441/source.json')
edges = load(OUT / 'own8-57cdc0d/summary.json')
assert backend['junit_or_vm'] == {'tests': 74, 'failure': 0, 'error': 0, 'skipped': 0}
assert vm['junit_or_vm'] == {'tests': 23, 'failure': 0, 'error': 0, 'skipped': 0}
assert edges['junit'] == {'tests': 8, 'failures': 0, 'errors': 0, 'skipped': 0}
author = load(OUT / 'browser57-first/author-browser/report.json')
own = load(OUT / 'browser57-own3/own-browser/report.json')
assert author['passed'] and len(author['checks']) == 10 and len(author['screens']) == 4 and author['pageErrors'] == []
assert own['passed'] and len(own['checks']) == 3 and own['pageErrors'] == []
for name in author['screens']:
    image = load(OUT / 'browser57-first/author-browser' / (name + '.json'))
    assert image['axe'] == [] and image['overflow'] is False
for name in ['browser57-first', 'browser57-own3']:
    closed = load(OUT / name / 'owned-process-close.json')
    assert closed['listener_gone'] and closed['owned_port_free'] and closed['foreign_ports_fingerprints_unchanged']
    photo = load(OUT / name / 'before.json'); after = load(OUT / name / 'after.json')
    assert photo == after and photo['head'] == HEAD
old_photo = load(OUT / 'backend74-49eb441/before.json')
changed = [path for path, value in old_photo['sources'].items() if sha(ROOT / path) != value]
assert changed == ['web/middleware/security_headers.py']
security = EVIDENCE / 'history-security-after-20261019/source.json'
assert sha(security) == 'ed85b0ea582f38626724e1e9afc0bc462fc373a058c8896af0f22bcdd82d9378'
(OUT / 'harness-final.py.txt').write_bytes((EVIDENCE / 'run_public_history_browser_review.py').read_bytes())
save('final-summary.json', {
    'decision': 'Accepted scoped R34 QA on frozen57; separate security boundary gate accepted. Integration with recovery28 remains coordinator-owned.',
    'head': HEAD, 'historical_backend_vm_head': '49eb44124d36a0d0aeaf732d7f720d969f1d517c',
    'validation': {'author_python': 74, 'own_sqlite_edges': 8, 'new_vm_unique': 23,
                   'author_browser_groups': 10, 'own_browser_groups': 3, 'author_axe_screens': 4,
                   'failures_errors_skips_in_accepted_tests': 0},
    'browser_author_ran_once': True,
    'browser_checks': author['checks'] + own['checks'],
    'sources': {'author_python_vm': 757, 'own_sqlite': edges['sources'], 'each_browser': 756,
                'packages': 89, 'readonly_node_dependencies': 146, 'all_phase_photos_stable': True,
                'pip_checks_zero': True},
    'only_previously_tested_source_changed_in_error_fix': changed,
    'preservation': {'sql_assertions_unchanged': 7, 'historical_runtime_sources_unchanged': 18,
                      'raw_archives_authenticated': 2, 'proof_sha256': sha(OUT / 'preservation.json')},
    'error_boundary_security_evidence': {'path': str(security), 'sha256': sha(security),
        'attribution': 'Separate independent security agent:2 original negatives,8 root and14 own checks passed on57. Not rerun or counted as our82 Python cases.'},
    'retained_harness_error': {
        'phase': 'browser57-first after all10 author groups passed',
        'mistake': 'The orchestration incorrectly required zero blocked origin attempts, although aborting those attempts is the isolation contract.',
        'observed': '6 external font attempts blocked; no external route/API request permitted.',
        'correction': 'Only orchestration guard-stat interpretation changed. All10 author assertions stay green and are not replayed. Own3 ran once on a new fixture primed by2 actual worker plans; own input bytes unchanged.',
        'original_runner_preserved': 'browser57-first/runner-first.py.txt'},
    'owned_processes': 'Both own8792 listener/launcher pairs closed with fingerprints, port absence and foreign8776/8777/8780/8781/8784 fingerprints unchanged.',
    'visual_review': '320px first-page screenshot inspected;50-row table stays in its contained horizontal scroller and explicit pagination controls remain visible. Full document overflow/axe scopes passed.',
    'scope': 'Real isolated SQLite HTTP/auth/worker/private PDF and browser interactions. Metadata target27 is accurate for this isolated worktree; no claim of an Alembic migration, recovery28 composition, PG performance, load, publication or broad suite.',
    'no_product_ci_author_edits_or_commits': True,
})
files = {path.relative_to(OUT).as_posix(): sha(path) for path in sorted(OUT.rglob('*')) if path.is_file()}
save('final-manifest.json', {'files': files, 'count': len(files), 'scope': 'All files under independent prefix including partial/harness-error records; excludes this manifest.'})
print(json.dumps({'summary_sha256': sha(OUT / 'final-summary.json'),
                  'manifest_sha256': sha(OUT / 'final-manifest.json'), 'files': len(files)}))
