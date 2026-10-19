"""Read-only review of the coordinator-owned retirement-test correction."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(r'F:/MetodoBaseWeb-execution-20261018')
OUT = Path(__file__).resolve().parent
OLD = 'dd9877350aad3f483299c990a1e97aab63c83f5d'
NEW = 'a753b2cdf61a91133bd58c3159b0b35e02167396'
NAME = 'tests/test_landing_commercial.py'
FUNCTION = 'test_public_view_never_reads_credentials_fetches_private_data_or_writes'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def sha(data):
    return hashlib.sha256(data).hexdigest()

assert git('rev-parse', 'HEAD').decode().strip() == NEW
assert not git('status', '--porcelain', '--untracked-files=no').decode().strip()
names = git('diff', '--name-only', OLD, NEW).decode().splitlines()
assert [name for name in names if not name.startswith('docs/')] == [NAME]
before = git('show', OLD + ':' + NAME)
after = git('show', NEW + ':' + NAME)
tree_before, tree_after = ast.parse(before), ast.parse(after)
old_function = next(node for node in tree_before.body if isinstance(node, ast.FunctionDef) and node.name == FUNCTION)
new_function = next(node for node in tree_after.body if isinstance(node, ast.FunctionDef) and node.name == FUNCTION)
assert ast.dump(ast.Module(body=old_function.body[:-1], type_ignores=[])) == ast.dump(ast.Module(body=new_function.body[:-2], type_ignores=[]))
old_function.body = []
new_function.body = []
assert ast.dump(tree_before) == ast.dump(tree_after)
current = (ROOT / NAME).read_bytes()
assert current.replace(b'\r\n', b'\n') == after
red = OUT.parent / 'qa-integrated28-history-landing-20261019'
red_manifest_bytes = (red / 'serial-red-manifest.json').read_bytes()
assert sha(red_manifest_bytes) == 'ecceeed403106dfe780a728060dab0c2450ecb53ef8404c7a046d59bf4749884'
red_manifest = json.loads(red_manifest_bytes)
assert all(sha((red / name).read_bytes()) == value for name, value in red_manifest['files'].items())
summary = {
    'old_head': OLD, 'new_head': NEW, 'tracked_clean': True,
    'only_changed_nondocument_source': NAME, 'runtime_changed': False,
    'original_git_sha256': sha(before), 'final_git_sha256': sha(after), 'final_raw_sha256': sha(current),
    'preceding_function_statements_ast_identical': len(next(node for node in ast.parse(before).body if isinstance(node, ast.FunctionDef) and node.name == FUNCTION).body) - 1,
    'rest_of_module_ast_identical': True,
    'change': 'Coordinator-owned final physical-preservation assertion changed to absence, plus five additional 404 routes for each existing factory parameter. Existing six-route total includes original /landing.html. All original no-credentials/no-script/no-writes/CSS-hash controls remain identical.',
    'original_red_manifest_sha256': sha(red_manifest_bytes), 'original_red_files_verified': len(red_manifest['files']),
    'acceptance': 'Correction scope verified; broad regression acceptance remains pending fresh execution.',
}
with (OUT / 'test-fix-review.json').open('x', encoding='utf8', newline='\n') as stream:
    json.dump(summary, stream, ensure_ascii=False, indent=2); stream.write('\n')
with (OUT / 'test-fix.diff').open('xb') as stream:
    stream.write(git('diff', OLD, NEW, '--', NAME))
print(json.dumps(summary, ensure_ascii=False))
