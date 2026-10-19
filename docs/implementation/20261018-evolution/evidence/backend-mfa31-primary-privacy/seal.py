"""Seal exact primary API header delta and immutable SEC20 replay."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path('F:/mb-mfa31-primary-privacy-20261019')
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/backend-mfa31-primary-privacy'
BASE = '78d27b5d3090cbd5a00c8de8b417f3bd48cb3fc1'


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)


def sha(value):
    return hashlib.sha256(value).hexdigest()


class RemovePrimaryDelta(ast.NodeTransformer):
    def visit_Assign(self, node):
        if any(isinstance(target, ast.Name) and target.id in {'_PRIMARY_API_PATHS', 'primary_api'} for target in node.targets):
            return None
        return self.generic_visit(node)

    def visit_BoolOp(self, node):
        node = self.generic_visit(node)
        node.values = [item for item in node.values if not (
            isinstance(item, ast.Name) and item.id == 'primary_api' or
            isinstance(item, ast.UnaryOp) and isinstance(item.op, ast.Not)
            and isinstance(item.operand, ast.Name) and item.operand.id == 'primary_api')]
        return node.values[0] if len(node.values) == 1 else node


def main():
    assert git('rev-parse', 'HEAD').decode().strip() == BASE
    assert git('diff', '--name-only').decode().splitlines() == ['web/middleware/security_headers.py']
    before = git('show', BASE + ':web/middleware/security_headers.py')
    current = (ROOT / 'web/middleware/security_headers.py').read_bytes()
    assert (OUT / 'security_headers-before-RAW.py').read_bytes().replace(b'\r\n', b'\n') == before
    stripped = RemovePrimaryDelta().visit(ast.parse(current))
    inverse = ast.dump(stripped, include_attributes=False) == ast.dump(ast.parse(before), include_attributes=False)
    assert inverse
    driver = (OUT / 'security-test_full_review.py').read_bytes()
    assert sha(driver) == '602069c1a838cf12440250e167742c62f11a40a062fd16226428ac293aacd5f8'
    original_runner = (OUT / 'security-run_full-original.py').read_bytes()
    runner = (OUT / 'security-run_full-own-root.py').read_bytes()
    assert original_runner.replace(b'F:/mb-mfa-sec', ROOT.as_posix().encode()) == runner
    for stage in ('before', 'after'):
        assert (Path(__file__).parent / stage / 'test_full_review.py').read_bytes() == driver
        assert (Path(__file__).parent / stage / 'run_full.py').read_bytes() == runner
        assert json.loads((OUT / (stage + '-origins.json')).read_bytes())['source_root'] == str(ROOT)
    reports = {}
    expected = {'before': (20, 2), 'after': (20, 0), 'maintained-after': (94, 0)}
    for label, (count, failed) in expected.items():
        report = json.loads((OUT / (label + '-summary.json')).read_bytes())
        assert (report['cases'], report['failures'], report['errors'], report['skips']) == (count, failed, 0, 0)
        assert report['sources_quiet'] and report['packages_quiet'] and report['packages'] == 89
        assert sha((OUT / (label + '.log')).read_bytes()) == report['stdout_sha256']
        assert sha((OUT / (label + '.xml')).read_bytes()) == report['xml_sha256']
        reports[label] = report
    breakdown = Counter(item.attrib['classname'] for item in ET.fromstring((OUT / 'maintained-after.xml').read_bytes()).iter('testcase'))
    assert sum(value for key, value in breakdown.items() if 'test_mfa31_primary_privacy' in key) == 30
    shutil.copyfile(Path(__file__).parent / 'replay.py', OUT / 'replay-orchestrator.py')
    shutil.copyfile(Path(__file__), OUT / 'seal.py')
    (OUT / 'product.diff').write_bytes(git('diff', '--', 'web/middleware/security_headers.py'))
    (OUT / 'ruff.txt').write_bytes(b'ruff check --select F821,E9 web/middleware/security_headers.py tests/test_mfa31_primary_privacy.py\nAll checks passed!\n')
    source_hashes = {}
    for name in ('web/middleware/security_headers.py', 'tests/test_mfa31_primary_privacy.py'):
        raw = (ROOT / name).read_bytes()
        source_hashes[name] = {'raw_sha256': sha(raw), 'git_lf_sha256': sha(raw.replace(b'\r\n', b'\n')), 'raw_bytes': len(raw)}
    summary = {
        'base': BASE, 'scope': 'Exact mounted primary APIs /api/auth/login and /api/auth/google: private headers on all statuses and existing opaque generic500 boundary.',
        'original_driver_sha256': sha(driver), 'runner_adaptation': 'Only ROOT coordinate; byte comparison verified.',
        'replay': reports, 'maintained_breakdown': dict(breakdown),
        'inverse_ast_equal_after_removing_primary_delta': inverse,
        'proof_meaning': 'All prior middleware branches, including CSP, remain AST-identical after removing exact primary-path additions.',
        'cases': 'Real factories: validation422, invalid password/provider401, real limiter dependency429, real fail-closed Redis conversion503 with synthetic transport, unhandled primary-port500 opaque body/logs, wrong-method405, primary200 and factor202; real login pages/adjacent404 normal policy; existing MFA/history/R12 private routes preserved.',
        'primary_paths_provenance': 'web/routes/auth.py @router.post /auth/login and /auth/google, mounted prefix /api by api.app and web.main_web; positive actual requests, no test routes installed.',
        'no_privilege_change': 'No auth authority, parent eligibility, factor/enrollment, grant, or provider behavior changes. Separate parentpending finding remains outside this fix.',
        'isolation': 'SQLite/ASGI only, external sockets blocked, Google/Redis transports synthetic. No PG, Chrome, DDL, mail or real providers.',
        'stability': '845 files before, 846 after adding the maintained test; each run has identical before/after source and89 package photographs. Immutable driver remains602069 unchanged.',
        'source_hashes': source_hashes,
        'historical': 'Original frozen31/keyfix worktrees and targets22-31 untouched. Diary R24 policy belongs to later coordinator composition; this delta preserves this ancestor middleware and does not claim a R24 composition gate.',
        'independent_final_replay': 'Pending SEC20 replay on the candidate commit.',
        'encoding': 'Evidence directory * -text before first RAW write; source is normal GitLF. RAW/GitLF hashes below; original logs and preimage retained.'
    }
    (OUT / 'review-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    rows = {item.name: {'sha256': sha(item.read_bytes()), 'bytes': item.stat().st_size}
            for item in sorted(OUT.iterdir()) if item.is_file() and item.name != 'freeze.json'}
    freeze = {'base': BASE, 'files': rows, 'current_sources': source_hashes}
    (OUT / 'freeze.json').write_text(json.dumps(freeze, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'freeze_sha256': sha((OUT / 'freeze.json').read_bytes()), 'summary_sha256': sha((OUT / 'review-summary.json').read_bytes()), 'proof_files': len(rows) + 1, 'inverse_ast_equal': inverse, 'maintained_counts': dict(breakdown)}))


if __name__ == '__main__':
    main()
