"""Preserve the accepted harness and adapt it explicitly to the composed CI28 source."""
import difflib
from qa_support import *

original=MAIN/'docs/implementation/20261018-evolution/evidence/run_public_history_browser_review.py'
raw=original.read_bytes()
assert sha(raw)=='afa48d677a07b53019615d759f041e51ffbb7bd99d76e7e67c7ae46f9e7bcd6e'
text=raw.decode('utf8')
source=text
text=text.replace('import argparse\n','import argparse\nimport ast\n',1)
rootline=next(line for line in text.splitlines() if line.lstrip().startswith("root = Path(r'F:"))
text=text.replace(rootline,"    root = Path(r'F:\\MetodoBaseWeb-history-ci-20261019')",1)
assert text.count("startup['model_target_revision'] == '20261019_personal_diary'")==1
text=text.replace("startup['model_target_revision'] == '20261019_personal_diary'","startup['model_target_revision'] == '20261019_account_recovery'",1)
start=text.index('    for path, data in [(fixture_path, fixture_raw), (driver_path, driver_raw)]:\n')
end=text.index('    server_text = ',start)
replacement='''    historical_fixture_raw = fixture_raw
    for path, data in [(fixture_path, historical_fixture_raw), (driver_path, driver_raw)]:
        assert sha(data) == manifest['sources'][path]['raw_sha256']
    fixture_raw = (root / fixture_path).read_bytes()
    fixture_git = subprocess.check_output(['git', 'show', args.head + ':' + fixture_path], cwd=root)
    driver_git = subprocess.check_output(['git', 'show', args.head + ':' + driver_path], cwd=root)
    assert fixture_raw.replace(b'\\r\\n', b'\\n') == fixture_git
    assert driver_raw.replace(b'\\r\\n', b'\\n') == driver_git
    assert driver_git == (root / driver_path).read_bytes().replace(b'\\r\\n', b'\\n')
    old_tree = ast.parse(historical_fixture_raw)
    current_tree = ast.parse(fixture_raw)
    target_change = 'No AST change from authenticated author fixture'
    if ast.dump(old_tree) != ast.dump(current_tree):
        class RestoreHistoricalTarget(ast.NodeTransformer):
            imports = 0
            calls = 0
            def visit_ImportFrom(self, node):
                if node.module == 'web.database.schema_control':
                    assert [(entry.name, entry.asname) for entry in node.names] == [('expected_head', None)]
                    self.imports += 1
                    return None
                return node
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name) and node.func.id == 'expected_head':
                    assert not node.args and not node.keywords
                    self.calls += 1
                    return ast.Constant('20261019_personal_diary')
                return self.generic_visit(node)
        transform = RestoreHistoricalTarget()
        restored = transform.visit(current_tree)
        assert transform.imports == transform.calls == 1
        assert ast.dump(restored) == ast.dump(old_tree), 'Fixture behavior changed beyond dynamic target marker'
        target_change = 'Only expected_head import and marker call replace historical revision27 literal'
    save(out, 'fixture-target28-review.json', {
        'head': args.head, 'historical_fixture_raw_sha256': sha(historical_fixture_raw),
        'current_fixture_raw_sha256': sha(fixture_raw), 'current_fixture_git_sha256': sha(fixture_git),
        'current_driver_git_sha256': sha(driver_git), 'driver_raw_sha256': sha(driver_raw),
        'fixture_review': target_change, 'driver_assertions_unchanged': True,
        'scope': 'New composed target28 fixture authenticated against current HEAD; original author snapshot and its target27 acceptance remain intact.'})
'''
text=text[:start]+replacement+text[end:]
target=OUT/'run_browser28.py'
with target.open('x',encoding='utf8',newline='\n') as stream:stream.write(text)
with (OUT/'browser-harness.diff').open('x',encoding='utf8',newline='\n') as stream:
    stream.writelines(difflib.unified_diff(source.splitlines(keepends=True),text.splitlines(keepends=True),fromfile='accepted-browser-harness',tofile='new-composed-CI28-harness'))
save(OUT/'browser-runner-adaptation.json',{'source_sha256':sha(raw),'target_sha256':sha(target.read_bytes()),
    'harness_changes':['Candidate worktree selected explicitly','Require actual current target28 marker','Authenticate current fixture against current Git HEAD; prove exact AST preservation except prior authorized dynamic-target delta'],
    'driver_changes':'Only own port/output directory as in the accepted harness; exact reversal proven at run. No assertion change.',
    'network_policy':'Existing exact-origin/maxRedirects0 wrapper unchanged except origin environment; foreign listeners re-photographed each phase.',
    'execution':'Two fresh fixtures run sequentially with full owned PID closure between; no old browser17 or VM162 replay.'})
print(json.dumps({'runner_sha256':sha(target.read_bytes()),'path':str(target)}))
