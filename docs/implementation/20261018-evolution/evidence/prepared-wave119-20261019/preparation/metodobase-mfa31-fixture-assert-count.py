"""Read-only diagnosis of the coordinator assertion-inventory precondition."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

root = Path(r'F:\mb-mfa31-compose-20261019')
driver = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-fixture-compose.py')
source = driver.read_text(encoding='utf8')
assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=root)
marker = "assert sum(row['approved_status_assert_changes']"
assert source.count(marker) == 1
namespace = {}
exec(compile(source.split(marker)[0], str(driver), 'exec'), namespace)
inventory = {}
for name in namespace['assertions']:
    old = ast.parse(subprocess.check_output(['git', 'show', namespace['AUTHOR_BASE'] + ':' + name], cwd=root))
    inventory[name] = {'full_module_assert_nodes': sum(isinstance(node, ast.Assert) for node in ast.walk(old)),
                       'per_function_inventory': namespace['assertions'][name]}
print(json.dumps({'failed_driver_sha256': hashlib.sha256(driver.read_bytes()).hexdigest(), 'inventory': inventory,
                  'source_clean': not bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=root)),
                  'merge_not_started': not namespace['OUT'].exists()}))
