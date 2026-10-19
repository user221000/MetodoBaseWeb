"""Create an explicit reviewed29 runner retaining the accepted archive validator."""
from pathlib import Path
import ast,hashlib,json,subprocess
root=Path(r'F:\mb-r12-history30-20261019')
pin='fd636202045efa30b1430f4a9dd8ab287ec76357'
subprocess.run(['git','merge-base','--is-ancestor',pin,'HEAD'],cwd=root,check=True,capture_output=True)
before=(root/'tests/run_reviewed_ci28.py').read_text(encoding='utf-8-sig').replace('\r\n','\n')
assert hashlib.sha256(before.encode()).hexdigest()=='58cf6c165d155d13120c3fe2ea50f1fac26960a3456c438418de45a2e040bbed'
source=before.replace('CI28','CI29').replace("REVISION = '66d9dec0e15dd873038bd248d3883daeeb27d4ca'","REVISION = '"+pin+"'")
tree=ast.parse(source);node=next(item for item in tree.body if isinstance(item,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='RESTORE_NODES' for target in item.targets))
lines=source.splitlines(keepends=True)
lines[node.lineno-1:node.end_lineno]=["RESTORE_NODES = (\n    'tests/integration_client_link_restore.py::test_revision29_restore_preserves_member_links_and_all_revision26_27_28_contracts',\n)\n"]
source=''.join(lines)
source=source.replace("'tests/verify_history_landing_ci.py',","'tests/verify_member_links_ci.py',")
needle="'--output', str(out / 'review'), '--verify-only']";assert source.count(needle)==1
source=source.replace(needle,"'--output', str(out / 'review'), '--verify-only',\n                   '--history-repository', str(args.history_repository)]")
source=source.replace('The two unchanged CI29 restore tests','The unchanged populated CI29 restore test')
source=source.replace('Historical CI29 wiring/assertions and actual old ORM marker','Historical CI29 wiring/assertions and actual revision29 ORM markers')
source=source.replace('The optional restore mode executes the two unchanged CI29 restore node IDs','The optional restore mode executes the unchanged populated CI29 restore node ID')
source=source.replace('This runner extracts a pinned local Git ancestor','This runner extracts accepted schema29 commit '+pin+' as a local Git ancestor')
old_tree=ast.parse(before);new_tree=ast.parse(source)
names=['canonical_name','tree_specification','validate_restore_environment','materialize'];rows=[]
for name in names:
    left=next(node for node in old_tree.body if isinstance(node,ast.FunctionDef) and node.name==name)
    right=next(node for node in new_tree.body if isinstance(node,ast.FunctionDef) and node.name==name)
    assert ast.dump(left,include_attributes=False)==ast.dump(right,include_attributes=False),name
    rows.append({'function':name,'AST_byte_equivalent':True})
target=root/'tests/run_reviewed_ci29.py';assert not target.exists();target.write_bytes(source.encode())
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci30-archive29-preparation-20261019.json');assert not out.exists()
out.write_text(json.dumps({'schema29_source_pin':pin,'accepted28_runner_LF_sha256':hashlib.sha256(before.encode()).hexdigest(),'new29_runner_LF_sha256':hashlib.sha256(source.encode()).hexdigest(),'unchanged_validation_functions':rows,'deltas':'Fixed reviewed29 ancestor and one unchanged populated29 restore; invoke accepted CI29 guard with actual read-only history repository to preserve its nested28 ancestry checks. No assertion rewrite or metadata substitution.'},indent=2)+'\n',encoding='utf8')
print(json.dumps({'historical29_pin':pin,'archive_validation_functions_unchanged':len(rows)}))
