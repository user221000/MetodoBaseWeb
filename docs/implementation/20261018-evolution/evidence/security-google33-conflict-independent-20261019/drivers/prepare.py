from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
import sys

R = Path(r'F:/mb-security-google33-conflict-peer-20261019')
AUTHOR = Path(r'F:/mb-google33-conflict-window-20261019')
OLD = Path(r'F:/mb-security-google33-peer-20261019')
T = Path(r'C:/Users/Consu/AppData/Local/Temp')
PREFIX = 'docs/implementation/20261018-evolution/evidence/security-google33-conflict-independent-20261019'
REDPREFIX = 'docs/implementation/20261018-evolution/evidence/security-google33-independent-20261019'
RED = '0bf1d0a8c5a3470173faa36b094076843b76dd6f'
COMMON = '3587b3b3eee3a58367624472d7c0683baa8f10e0'
BASE = '707b32605c254466982f25a368b046a0445a3f71'
FIX = sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}', FIX)
git = lambda root, *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=root)
sha = lambda b: hashlib.sha256(b).hexdigest()
assert git(AUTHOR, 'rev-parse', 'HEAD').decode().strip() == FIX
assert not git(AUTHOR, 'status', '--porcelain', '--untracked-files=no')
assert not R.exists()
subprocess.run(['git', '-c', 'core.autocrlf=false', 'worktree', 'add', '--detach', str(R), FIX], cwd=AUTHOR, check=True, capture_output=True)
O = R / PREFIX
O.mkdir()
(O / '.gitattributes').write_bytes(b'* -text\n')
save = lambda n, x: (O / n).write_bytes((json.dumps(x, indent=2) + '\n').encode())
oldphoto = json.loads((OLD / REDPREFIX / 'sqlite-before.json').read_bytes())['source']
differences = [name for name, digest in oldphoto.items() if sha((R / name).read_bytes()) != digest]
assert differences == ['web/services/google_link.py']
canaries = {}
for name in ['test_security_google33_peer.py', 'test_security_google33_postgres_peer.py', 'test_security_google33_canonical_race_peer.py']:
    raw = git(OLD, 'show', RED + ':' + REDPREFIX + '/canaries/' + name)
    (R / 'tests' / name).write_bytes(raw)
    canaries[name] = sha(raw)
raw = git(OLD, 'show', RED + ':' + REDPREFIX + '/canaries/initial-race-autoflush-true.RAW.py')
name = 'test_security_google33_postgres_true_peer.py'
(R / 'tests' / name).write_bytes(raw)
canaries[name] = sha(raw)
name = 'test_security_google33_conflict_peer.py'
raw = (T / 'metodobase-sec-google33-conflict-peer-faults-20261019.py').read_bytes()
(R / 'tests' / name).write_bytes(raw)
canaries[name] = sha(raw)

oldraw = git(OLD, 'show', COMMON + ':web/services/google_link.py')
newraw = (R / 'web/services/google_link.py').read_bytes()
oldtree, newtree = ast.parse(oldraw), ast.parse(newraw)
dump = lambda node: ast.dump(node, include_attributes=False)
oldfuncs = {n.name: n for n in oldtree.body if isinstance(n, ast.FunctionDef)}
newfuncs = {n.name: n for n in newtree.body if isinstance(n, ast.FunctionDef)}
assert set(newfuncs) == set(oldfuncs) | {'_write_conflicts'}
assert all(dump(oldfuncs[name]) == dump(newfuncs[name]) for name in oldfuncs if name not in {'confirm', 'resolve_or_register'})

class FlattenNew(ast.NodeTransformer):
    def visit_With(self, node):
        assert len(node.items) == 1 and isinstance(node.items[0].context_expr, ast.Call)
        assert node.items[0].context_expr.func.id == '_write_conflicts'
        return node.body

class FlattenOriginalTry(ast.NodeTransformer):
    def visit_Try(self, node):
        assert len(node.handlers) == 1 and node.handlers[0].type.id == 'IntegrityError'
        assert not node.orelse and not node.finalbody
        return node.body

assert dump(oldfuncs['confirm']) == dump(FlattenNew().visit(newfuncs['confirm']))
assert dump(FlattenOriginalTry().visit(oldfuncs['resolve_or_register'])) == dump(FlattenNew().visit(newfuncs['resolve_or_register']))
helper = newfuncs['_write_conflicts']
assert len(helper.body) == 2 and len(helper.decorator_list) == 1 and helper.decorator_list[0].id == 'contextmanager'
handler_try = helper.body[1]
assert len(handler_try.body) == 1 and isinstance(handler_try.body[0].value, ast.Yield)
assert len(handler_try.handlers) == 1 and handler_try.handlers[0].type.id == 'IntegrityError'
assert not handler_try.orelse and not handler_try.finalbody
assert [dump(n) for n in handler_try.handlers[0].body] == [dump(n) for n in ast.parse('rollback(db)\nfail(409,"google_link_conflict")').body]
newtree.body = [n for n in newtree.body if not (isinstance(n, ast.ImportFrom) and n.module == 'contextlib') and not (isinstance(n, ast.FunctionDef) and n.name == '_write_conflicts')]
assert dump(oldtree) == dump(newtree)
save('static-boundary-inverse.json', {
    'original_blob_SHA256': sha(oldraw), 'new_checkout_RAW_SHA256': sha(newraw),
    'all_other_functions_AST_exact': True, 'confirm_body_exact_after_only_unwrap': True,
    'resolve_body_exact_after_unwrap_and_original_first_flush_try_normalization': True,
    'whole_module_AST_inverse_exact_after_only_documented_changes': True,
    'helper': 'Only IntegrityError -> rollback -> 409; rollback failure propagates 503; no retry/query/adoption',
    'mutation_coverage': ['confirm new/revived binding, consume intent, session revocation, audit, commit',
        'new-account add/first flush/binding/profile+memberships/current identity/audit/commit'],
    'preexisting_identity_checks_unchanged': True, 'start_unlink_and_owned_cleanup_unchanged': True,
})
save('frozen-source-binding.json', {
    'reviewed_commit': FIX, 'fix_base_commit': BASE, 'original_common_commit': COMMON,
    'immutable_RED_peer_commit': RED, 'immutable_RED_source_SHA256': '3f48208b43f137fbf9e918f3c5c5feaab4c1828712369f35abb7078d4ba03d36',
    'immutable_RED_manifest_SHA256': '4e01165cdd3f64159ea6d202d07afdb0dfb1cac60f13c9c6bf71fd3c654e14f6',
    '845_old_selected_sources_changed': differences,
    'new_maintained_fault_test_SHA256': sha((R / 'tests/test_google33_conflict_window.py').read_bytes()),
    'peer_canaries': canaries, 'old_canary_bytes_and_assertions_unchanged': True,
    'checkout': 'core.autocrlf=false; product checkout compared to old selected RAW source photos',
    'no_SQL_during_preparation': True,
})
print(json.dumps({'worktree': str(R), 'commit': FIX, 'old_selected_source_changes': differences,
    'peer_canaries': canaries, 'static_boundary_inverse': 'PASS', 'SQL': False}))
