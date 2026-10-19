from pathlib import Path
import hashlib
import json
import subprocess

repo = Path(r'F:\mb-r25-reviewed32-20261019')
root = Path(r'F:\mb-progress32-retirement-composed-20261019')
out = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-retirement32-common-compose-20261019')
base = '345aa7ce16f65fec9481b48cfcd63c33ff3835fc'
backend = 'fcfb55e5849e0e20b568be8729dcc1b8c6b1762e'
frontend = 'de216543a2eec05584168cdb888f627901b0e0b1'
clock = 'de506b6077ba055587f02e7d839387e7f5c56f84'
clock_base = '6a75d096ea3d63d9e78c76d33b7e243160b23364'
proof = 'docs/implementation/20261018-evolution/evidence/'
git = lambda *args, cwd=repo: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=cwd)
sha = lambda blob: hashlib.sha256(blob).hexdigest()
encode = lambda value: (json.dumps(value, indent=2) + '\n').encode()
assert not root.exists() and not out.exists()
assert git('rev-parse', 'HEAD').decode().strip() == base
assert not git('status', '--porcelain', '--untracked-files=no')

def inventory(ref):
    rows = {}
    for row in git('ls-tree', '-r', '-z', ref).split(b'\0'):
        if row:
            meta, name = row.split(b'\t', 1)
            rows[name.decode()] = meta.decode()
    return rows

expected = {
    backend: (base, {
        'web/progress_retirement_schemas.py', 'web/routes/progress_retirement.py',
        'web/services/progress_retirement.py', 'web/routes/personal_progress.py',
        'web/middleware/security_headers.py', 'tests/integration_progress_retirement.py',
        'tests/retirement32_owned.py', 'tests/test_progress_retirement_boundaries.py',
        'tests/test_progress_retirement_context.py', 'tests/test_progress_retirement_entrypoint_review.py',
        'tests/test_progress_retirement_headers.py', 'tests/test_progress_retirement_http.py'}),
    frontend: (base, {
        'web/routes/pages.py', 'web/templates/login_gym.html', 'web/templates/login_usuario.html',
        'web/templates/usuario_perfil.html', 'web/templates/retiro_consentimientos.html',
        'web/static/css/retiro-consentimientos.css', 'web/static/js/retiro-consentimientos.js',
        'web/static/js/retiro-consentimientos-pagina.js', 'tests/e2e/progress_retirement.cjs',
        'tests/e2e/progress_retirement_dom.cjs', 'tests/test_progress_retirement_ui.py',
        'tests/test_progress_retirement_ui_contract.py',
        'docs/implementation/20261018-evolution/RETIRO_CONSENTIMIENTOS_UI.md'}),
    clock: (clock_base, {'alembic.ini', 'tests/ci_mfa31/current_link_fixtures.py',
        'tests/mfa31_contract_client.py', 'tests/test_current_mfa31_fixture_clock.py',
        'tests/test_mfa31_contract_clock.py', 'tests/test_mfa31_contract_clock_keyword.py',
        'tests/test_bootstrap_outcome_logging.py'})}
before = inventory(base)
changes = {}
for ref, (parent, allowed) in expected.items():
    subprocess.run(['git', 'merge-base', '--is-ancestor', parent, ref], cwd=repo, check=True, capture_output=True)
    names = set(git('diff', '--name-only', '-z', parent, ref).decode().split('\0')[:-1])
    assert {name for name in names if not name.startswith(proof)} == allowed, ref
    changes[ref] = sorted(names)
for ref, names in changes.items():
    assert not any(set(names) & set(other) for key, other in changes.items() if key != ref), ref
out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
(out / 'before.json').write_bytes(encode({'base': base, 'Git_tree_entries': before}))

def run(label, command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True)
    (out / (label + '.stdout.raw.log')).write_bytes(result.stdout)
    (out / (label + '.stderr.raw.log')).write_bytes(result.stderr)
    assert result.returncode == 0, label

run('worktree', ['git', '-c', 'core.autocrlf=false', 'worktree', 'add', '-b',
    'implementation/retirement32-common-20261019', str(root), base], repo)
run('merge-backend', ['git', 'merge', '--ff-only', backend], root)
run('merge-frontend', ['git', 'merge', '--no-edit', frontend], root)
run('merge-clock-logging', ['git', 'merge', '--no-edit', clock], root)
head = git('rev-parse', 'HEAD', cwd=root).decode().strip()
after = inventory(head)
altered = set().union(*map(set, changes.values()))
assert set(after) == set(before) | altered
assert all(after[name] == meta for name, meta in before.items() if name not in altered)
for ref, names in changes.items():
    for name in names:
        blob = git('show', ref + ':' + name)
        assert git('show', head + ':' + name) == blob, name
        assert (root / name).read_bytes() == blob, name
assert git('rev-parse', 'HEAD').decode().strip() == base
assert not git('status', '--porcelain', '--untracked-files=no')
assert not git('status', '--porcelain', '--untracked-files=no', cwd=root)
receipt = {'base': base, 'head': head, 'exact_changes_by_source': changes,
    'other_Git_tree_entries_exact': len(set(before) - altered),
    'product_test_document_paths': sorted(set().union(*(allowed for _, allowed in expected.values()))),
    'scope': 'Composition only. Schema32 unchanged; no new runtime, browser, PostgreSQL or broad result is attributed here.'}
(out / 'receipt.json').write_bytes(encode(receipt))
print(json.dumps({key: value for key, value in receipt.items() if key not in {'exact_changes_by_source', 'product_test_document_paths'}}))
