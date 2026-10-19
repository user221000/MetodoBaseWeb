"""Seal scoped SEC12 proof; no tests, database, or provider operations."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path('F:/mb-mfa31-keys-fix-20261019')
HERE = Path(__file__).parent
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/backend-mfa31-alias-key-fix'
BASE = '56e810b3a0518231ba013cab29d68ee0aba0bacd'


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def assertions(source, name):
    node = next(item for item in ast.parse(source).body if isinstance(item, ast.FunctionDef) and item.name == name)
    return [ast.dump(item, include_attributes=False) for item in ast.walk(node) if isinstance(item, ast.Assert)]


def main():
    assert git('rev-parse', 'HEAD').decode().strip() == BASE
    original = (OUT / 'security-test_action_keys.py').read_bytes()
    assert sha(original) == '59f9284b5bda012c9e502ca87b3f598832a115356e6e666c16149a67841c6566'
    assert (HERE / 'before/test_action_keys.py').read_bytes() == original == (HERE / 'after/test_action_keys.py').read_bytes()
    old_runner = (OUT / 'security-run_action_keys-original.py').read_bytes()
    runner = (HERE / 'before/run_action_keys.py').read_bytes()
    assert old_runner.replace(b'F:/mb-mfa-sec', ROOT.as_posix().encode()) == runner
    assert runner == (HERE / 'after/run_action_keys.py').read_bytes() == (OUT / 'replay-runner.py').read_bytes()
    maintained = (ROOT / 'tests/test_mfa31_payment_alias_keys.py').read_bytes()
    pairs = [
        ('test_alias_exact_observed_idempotency_key_can_be_consumed', 'test_deployed_payment_route_exact_observed_key_can_be_consumed'),
        ('test_alias_rejects_an_added_key_absent_from_observed_grant', 'test_deployed_payment_route_rejects_added_key_absent_from_observed_grant'),
        ('test_canonical_checkout_preserves_exact_key_and_rejects_a_changed_key', 'test_canonical_checkout_preserves_exact_key_and_rejects_a_changed_key'),
    ]
    assertion_counts = []
    for old, new in pairs:
        before, after = assertions(original, old), assertions(maintained, new)
        assert after[:len(before)] == before
        assertion_counts.append({'original_function': old, 'maintained_function': new, 'original_asserts_preserved': len(before)})
    original_product = git('show', BASE + ':api/routes/pagos.py')
    assert (OUT / 'api-pagos-before-RAW.py').read_bytes().replace(b'\r\n', b'\n') == original_product
    tracked_changes = git('diff', '--name-only').decode().splitlines()
    assert tracked_changes == ['api/routes/pagos.py'], tracked_changes
    parent_root = Path('F:/mb-mfa31-20261019')
    parent_status = subprocess.check_output(['git', '--no-replace-objects', 'status', '--porcelain'], cwd=parent_root)
    assert parent_status == b''
    labels = ['before', 'after', 'maintained-after', 'maintained-mounted-after', 'maintained-route-inventory-after']
    reports = {label: json.loads((OUT / (label + '-summary.json')).read_bytes()) for label in labels}
    expected = {'before': (5, 4), 'after': (5, 0), 'maintained-after': (10, 4), 'maintained-mounted-after': (12, 10), 'maintained-route-inventory-after': (12, 0)}
    for label, (count, failed) in expected.items():
        report = reports[label]
        assert (report['cases'], report['failures'], report['errors'], report['skips']) == (count, failed, 0, 0)
        assert report['sources_quiet'] and report['packages_quiet'] and report['packages'] == 89
        assert sha((OUT / (label + '.log')).read_bytes()) == report['stdout_sha256']
        assert sha((OUT / (label + '.xml')).read_bytes()) == report['xml_sha256']
    for label in ['before', 'after']:
        origins = json.loads((OUT / (label + '-origins.json')).read_bytes())
        assert origins['source_root'] == str(ROOT)
    shutil.copyfile(HERE / 'replay.py', OUT / 'replay-orchestrator.py')
    shutil.copyfile(Path(__file__), OUT / 'seal.py')
    (OUT / 'ruff.txt').write_bytes(b'ruff check --select F821,E9 api/routes/pagos.py tests/test_mfa31_payment_alias_keys.py\nAll checks passed!\n')
    (OUT / 'product.diff').write_bytes(git('diff', '--', 'api/routes/pagos.py'))
    current_paths = ['api/routes/pagos.py', 'tests/test_mfa31_payment_alias_keys.py']
    current = {}
    for name in current_paths:
        raw = (ROOT / name).read_bytes()
        current[name] = {'raw_sha256': sha(raw), 'git_lf_sha256': sha(raw.replace(b'\r\n', b'\n')), 'raw_bytes': len(raw)}
    summary = {
        'base': BASE, 'scope': 'SEC12 financial aliases Idempotency-Key binding; product delta only api/routes/pagos.py',
        'immutable_security_driver_sha256': sha(original), 'runner_change': 'ROOT coordinate only; byte comparison verified',
        'assertions': assertion_counts, 'current_sources': current,
        'immutable_replay': {'before': reports['before'], 'after': reports['after']},
        'maintained_current': reports['maintained-route-inventory-after'],
        'maintained_failed_preconditions': {
            'maintained-after': 'Four Web alias 404 responses: aliases are not mounted in Web; test route precondition incorrect, not product regression.',
            'maintained-mounted-after': 'Ten harness AttributeError exceptions: current FastAPI _IncludedRouter lacks path; fixed inventory to public application.openapi paths, criteria unchanged.'
        },
        'coverage': {'api.app': ['real Stripe legacy alias', 'real MP legacy alias', 'canonical Stripe control'],
                     'web.main_web': ['real canonical Stripe checkout', 'real canonical MP preference', 'canonical Stripe control', 'unmounted aliases 404 and no business port']},
        'counting': 'Immutable 5 and maintained 12 overlap; they are not 17 unique requirements.',
        'durability': 'Grant consumed_at read from a separate real SQLite Session; mismatch retains unused grant; exact request commits and replay does not reach the synthetic port.',
        'isolation': 'Real factories/auth/MFA/rate/SQLite; external sockets blocked. Billing ports alone synthetic. No PostgreSQL, Chrome, provider/mail calls, model/DDL/target/wire changes.',
        'source_stability': '845 non-doc sources and 89 package versions were identical before/after each run; module origins point at this worktree.',
        'frozen_author_worktree': {'path': str(parent_root), 'head': BASE, 'porcelain': ''},
        'independent_final_replay': 'Pending coordinator/security review of this candidate; author replay is not independent acceptance.',
        'encoding': 'RAW evidence directory has * -text. Product/test are normal Git text; both RAW and Git LF hashes recorded. All previous failed logs/XML and immutable source remain unmodified.'
    }
    (OUT / 'review-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    rows = {}
    for item in sorted(OUT.iterdir()):
        if item.is_file() and item.name != 'freeze.json':
            rows[item.name] = {'sha256': sha(item.read_bytes()), 'bytes': item.stat().st_size}
    freeze = {'base': BASE, 'files': rows, 'product_and_maintained_sources': current}
    (OUT / 'freeze.json').write_text(json.dumps(freeze, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'freeze_sha256': sha((OUT / 'freeze.json').read_bytes()), 'summary_sha256': sha((OUT / 'review-summary.json').read_bytes()), 'proof_files': len(rows) + 1, 'original_assertions_preserved': sum(x['original_asserts_preserved'] for x in assertion_counts)}))


if __name__ == '__main__':
    main()
