"""Seal strict-NULL actor/parent eligibility, preserving original SEC6 criteria."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path('F:/mb-mfa31-parent-canonical-20261019')
HERE = Path(__file__).parent
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/backend-mfa31-parent-canonical'
ORIGINAL = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-mfa31-security-full-20261019')
BASE = '8b64e86c8c377770a295df6e8cbbcdd4464b7d3a'
PRODUCTS = ('web/services/mfa_actions.py', 'web/services/mfa_service.py')


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def invitation_check(node, owners):
    return (isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.IsNot)
        and isinstance(node.left, ast.Attribute) and node.left.attr == 'invitation_token'
        and isinstance(node.left.value, ast.Name) and node.left.value.id in owners
        and len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Constant)
        and node.comparators[0].value is None)


class RemoveStrictNullDelta(ast.NodeTransformer):
    def visit_Compare(self, node):
        return node.left if invitation_check(node, {'user'}) else self.generic_visit(node)

    def visit_BoolOp(self, node):
        node = self.generic_visit(node)
        node.values = [item for item in node.values if not invitation_check(item, {'parent', 'owner'})]
        return node.values[0] if len(node.values) == 1 else node


def main():
    assert git('rev-parse', 'HEAD').decode().strip() == BASE
    assert git('diff', '--name-only').decode().splitlines() == list(PRODUCTS)
    inverse = {}
    for name in PRODUCTS:
        old = git('show', BASE + ':' + name)
        assert (OUT / (Path(name).name + '-before-RAW.py')).read_bytes().replace(b'\r\n', b'\n') == old
        current = (ROOT / name).read_bytes()
        equivalent = ast.dump(RemoveStrictNullDelta().visit(ast.parse(current)), include_attributes=False) == ast.dump(ast.parse(old), include_attributes=False)
        assert equivalent
        inverse[name] = equivalent
    driver = (OUT / 'security-test_parent_scope.py').read_bytes()
    assert sha(driver) == '4d0d35179c3ef1bc10f2023a4a6ac67d6310f09d597ddbc6adfaa4a154ed385f'
    native_full = (ORIGINAL / 'run_full.py').read_bytes()
    native_parent = (ORIGINAL / 'run_parent_scope.py').read_bytes()
    (OUT / 'security-run_full-base-original.py').write_bytes(native_full)
    (OUT / 'security-run_parent_scope-original.py').write_bytes(native_parent)
    selected_runner = native_full.replace(b'test_full_review.py', b'test_parent_scope.py')
    assert selected_runner == (OUT / 'security-run_full-original.py').read_bytes()
    runner = selected_runner.replace(b'F:/mb-mfa-sec', ROOT.as_posix().encode())
    assert runner == (OUT / 'security-run_full-own-root.py').read_bytes()
    for stage in ('before', 'after', 'security-final'):
        assert (HERE / stage / 'test_parent_scope.py').read_bytes() == driver
        assert (HERE / stage / 'run_full.py').read_bytes() == runner
        assert json.loads((OUT / (stage + '-origins.json')).read_bytes())['source_root'] == str(ROOT)
    expected = {'before': (6, 2), 'after': (6, 0), 'maintained-after': (10, 2),
                'actor-before': (4, 4), 'maintained-final': (12, 0), 'security-final': (6, 0)}
    reports = {}
    for label, (count, failed) in expected.items():
        report = json.loads((OUT / (label + '-summary.json')).read_bytes())
        assert (report['cases'], report['failures'], report['errors'], report['skips']) == (count, failed, 0, 0)
        assert report['sources_quiet'] and report['packages_quiet'] and report['packages'] == 89
        assert sha((OUT / (label + '.log')).read_bytes()) == report['stdout_sha256']
        assert sha((OUT / (label + '.xml')).read_bytes()) == report['xml_sha256']
        reports[label] = report
    own_name = 'tests/test_mfa31_parent_canonical.py'
    own_before = json.loads((OUT / 'actor-before-source-before.json').read_bytes())[own_name]
    assert own_before == sha((ROOT / own_name).read_bytes())
    before_actor = [item for item in ET.fromstring((OUT / 'actor-before.xml').read_bytes()).iter('testcase')]
    after_actor = [item for item in ET.fromstring((OUT / 'maintained-final.xml').read_bytes()).iter('testcase') if item.attrib['name'].startswith('test_actor_empty_invitation')]
    assert len(before_actor) == len(after_actor) == 4
    assert {item.attrib['name'] for item in before_actor} == {item.attrib['name'] for item in after_actor}
    assert all(item.find('failure') is not None for item in before_actor)
    assert all(item.find('failure') is None and item.find('error') is None for item in after_actor)
    shutil.copyfile(HERE / 'replay.py', OUT / 'replay-orchestrator.py')
    shutil.copyfile(Path(__file__), OUT / 'seal.py')
    (OUT / 'product.diff').write_bytes(git('diff', '--', *PRODUCTS))
    (OUT / 'ruff.txt').write_bytes(b'ruff check --select F821,E9 web/services/mfa_service.py web/services/mfa_actions.py tests/test_mfa31_parent_canonical.py\nAll checks passed!\n')
    source_hashes = {}
    for name in (*PRODUCTS, own_name):
        raw = (ROOT / name).read_bytes()
        source_hashes[name] = {'raw_sha256': sha(raw), 'git_lf_sha256': sha(raw.replace(b'\r\n', b'\n')), 'raw_bytes': len(raw)}
    summary = {
        'base': BASE, 'scope': 'SEC13 strict NULL eligibility only: actor current_identity and its canonical gym parent; authorize rechecks source owner.',
        'semantics': 'invitation_token must be SQL NULL. Empty non-NULL strings are ambiguous synthetic historical states, not invitations issued by a legitimate API.',
        'original_driver_sha256': sha(driver), 'inverse_ast': inverse,
        'inverse_meaning': 'Removing parent/owner strict-NULL checks and restoring the former actor truthiness condition reproduces ancestor ASTs exactly; locks/order/binding/commit/protocols unchanged.',
        'replays': reports,
        'actor_empty_before': '4 real HTTP negatives on parent-only preimage: OWNER could still read MFAstatus200 (grant already denied by owner check), ADMIN could issue team.invite grant200; same4 assert nodes pass within final12, identical maintained source hash.',
        'parent_consumption': 'Web real team route: preissued grant cannot be consumed when parent token becomes empty or64chars; independent SQLite Session confirms unused grant and unchanged account count, synthetic invitation port not called.',
        'direct_authorizer': 'OWNER/ADMIN identity snapshots + canonical parent with NULL/empty/full token; real persisted rows and SQLite write lock, no fake Session.',
        'preserved_harness_failure': 'maintained-after2 failures were API team invite404: route not mounted there. Preserved10-case log/preimage; consumer follows real Web-only route with OpenAPI assertion. Step-up issue is exercised by SEC6 and own actor4 on both real factories. No artificial routes installed.',
        'runner_adaptation': 'Same original run_full preparation used by native run_parent_scope; own expanded runner selects test_parent_scope.py and ROOT coordinate. Output artefact names remain full.xml/origins.json rather than native parent-scope.xml/parent-origins.json; criteria/imports unchanged. Both native scripts and selected expansion preserved RAW.',
        'stability': 'Each run source847(or846 before maintained test) and89 installed package photographs identical before/after. Original driver byte exact. Module origins are this worktree.',
        'isolation': 'SQLite/ASGI only; external sockets blocked; no PostgreSQL, Chrome, mail, real provider, authglobal, DDL, targets, roles, ledger, CI or UI changes.',
        'eligibility_not_revocation': 'This delta rejects invalid actor/parent at current issue/consumption; it does not invent a role migration, account merge, permanent invitation revocation or new recovery authority.',
        'independent_final_replay': 'Pending SEC6 and its additional strict-NULL negatives on this candidate.',
        'encoding': 'Prefix * -text before first RAW write. RAW blobs preserved; source uses normal GitLF and both hashes are recorded.',
        'source_hashes': source_hashes
    }
    (OUT / 'review-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    rows = {item.name: {'sha256': sha(item.read_bytes()), 'bytes': item.stat().st_size}
        for item in sorted(OUT.iterdir()) if item.is_file() and item.name != 'freeze.json'}
    (OUT / 'freeze.json').write_text(json.dumps({'base': BASE, 'files': rows, 'current_sources': source_hashes}, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'freeze_sha256': sha((OUT / 'freeze.json').read_bytes()), 'summary_sha256': sha((OUT / 'review-summary.json').read_bytes()), 'proof_files': len(rows) + 1, 'inverse_ast': inverse, 'actor_before4_same_after4': True}))


if __name__ == '__main__':
    main()
