"""Close the independent integrated28 broad gate after both runs complete."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3

OUT = Path(__file__).resolve().parent
HEAD = 'dd9877350aad3f483299c990a1e97aab63c83f5d'
PREFIX = 'qa-integrated28-history-landing'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((OUT / name).read_text(encoding='utf8'))


def save(name, value):
    with (OUT / name).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')


proof = load(PREFIX + '-source.json')
assert proof['accepted'] and proof['error'] is None and proof['head'] == HEAD
labels = ['before-serial', 'after-serial', 'before-shuffle', 'after-shuffle']
photos = [load(label + '-source.json') for label in labels]
assert len(photos) == 4 and all(photo['head'] == HEAD for photo in photos)
assert all(photo['sources'] == photos[0]['sources'] and photo['packages'] == photos[0]['packages']
           and photo['pip_check_exit'] == 0 and photo['package_count'] == 89 for photo in photos)
outcomes = load('case-outcomes.json')
assert outcomes['identical'] and len(outcomes['cases']) == proof['runs'][0]['junit']['collected']
assert set(tuple(value) for value in outcomes['cases'].values()).issubset({(), ('skipped',)})
for run in proof['runs']:
    assert run['exit'] == run['junit']['failures'] == run['junit']['errors'] == 0
    assert run['source_stable'] and run['packages_stable']
    assert len(run['junit']['skipped']) <= 1
    assert all(row['node'] == proof['only_allowed_skip'] for row in run['junit']['skipped'])

coverage = load(PREFIX + '-coverage.json')
guard = load(PREFIX + '-coverage-guard.json'); assert guard['exit'] == 0
gates = {}
files = {path.replace('\\', '/'): value for path, value in coverage['files'].items()}
for name in ['core/nutrition_validation.py', 'core/food_catalog.py', 'web/profile_schemas.py']:
    data = files[name]['summary']
    lines = 100 * data['covered_lines'] / data['num_statements']
    branches = 100 * data['covered_branches'] / data['num_branches']
    assert lines >= 95 and branches >= 90
    gates[name] = {'line_percent': lines, 'branch_percent': branches,
                   'covered_lines': data['covered_lines'], 'statements': data['num_statements'],
                   'covered_branches': data['covered_branches'], 'branches': data['num_branches']}

databases = []
for run in proof['runs']:
    base = Path(run['temporary_test_root'])
    expected_workers = ['main'] if run['label'] == 'serial' else ['gw0', 'gw1']
    for worker in expected_workers:
        path = base / worker / 'suite.db'; assert path.is_file()
        with sqlite3.connect('file:' + path.as_posix() + '?mode=ro', uri=True) as db:
            assert db.execute('PRAGMA query_only=ON').fetchone() is None
            integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
            tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            fields = {row[1] for row in db.execute('PRAGMA table_info(usuarios)')}
            assert integrity == 'ok' and len(tables) == 26 and 'personal_diary_days' in tables
            assert {'password_reset_hash', 'password_reset_expires_at', 'password_reset_session_version'}.issubset(fields)
        databases.append({'phase': run['label'], 'worker': worker, 'path': str(path), 'integrity_check': integrity,
                          'business_tables': len(tables), 'personal_diary_present': True, 'recovery_three_columns_present': True,
                          'inspection': 'Read-only SQLite connection after suite exit; metadata fixture, no Alembic migration claim.'})
save('sqlite-evidence.json', {'databases': databases})

timings = []
for run in proof['runs']:
    text = (OUT / (PREFIX + '-' + run['label'] + '.log')).read_text(encoding='utf8')
    last = text.strip().splitlines()[-1]
    warnings = re.findall(r'(\d+) warnings?', last)
    timings.append({'phase': run['label'], 'runner_seconds': run['seconds'],
                    'pytest_summary': last, 'warnings': int(warnings[-1]) if warnings else 0})

summary = {
    'accepted': True, 'head': HEAD, 'product_parent': '6270658',
    'source_count': photos[0]['source_count'], 'package_count': 89,
    'four_source_and_package_photos_identical': True, 'pip_checks_before_after_each_phase': [0, 0, 0, 0],
    'runs': proof['runs'], 'nodeids_and_outcomes_identical_between_runs': True,
    'timings': timings, 'critical_coverage_gates': gates,
    'coverage_scope': '95% line/90% branch gate for the three listed nutrition contract modules; no100% whole-application coverage claim.',
    'real_sqlite_databases': databases,
    'skip_policy': 'Only the existing Windows symlink-creation privilege boundary may skip. No new skip was accepted; actual identity/reason remain in each original JUnit.',
    'prior_evidence': 'No prior2064/1813 totals added, no historical report rewritten, no unexecuted CI/PG/browser/desktop criterion closed.',
    'scope': 'Windows candidate Python3.12, maintained integrated MAIN source frozen. Actual SaaS regression selection and original CI exclusions, serial coverage plus n2 shuffle20261018. Fresh isolated SQLite and socket guard; no provider, PG mutation, load/SLO, Linux/TCG/image/Actions or publication claim.',
    'pending_separate_work': ['Coordinator resource window before200 PostgreSQL history HTTP requests', 'Independent CI candidate review on isolated history-ci worktree'],
    'no_product_test_or_git_mutations': True,
}
save('final-summary.json', summary)
manifest = {path.relative_to(OUT).as_posix(): sha(path) for path in sorted(OUT.rglob('*')) if path.is_file()}
save('evidence-manifest.json', {'files': manifest, 'count': len(manifest), 'scope': 'All files in this new broad gate prefix except this self-referential manifest.'})
print(json.dumps({'accepted': True, 'sources': photos[0]['source_count'], 'packages': 89,
                  'serial': proof['runs'][0]['junit'], 'shuffle': proof['runs'][1]['junit'],
                  'summary_sha256': sha(OUT / 'final-summary.json'),
                  'manifest_sha256': sha(OUT / 'evidence-manifest.json'), 'files': len(manifest)}))
