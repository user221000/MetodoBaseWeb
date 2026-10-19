from pathlib import Path
import hashlib
import json
import subprocess

tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
root = Path(r'F:\mb-mfa31-compose-20261019')
original = tmp / 'metodobase-mfa31-fixture-compose.py'
blob = original.read_bytes()
assert hashlib.sha256(blob).hexdigest() == '23a0c1a2c464d562e13c43fbf280a28c936c71767754a5f703c9a88bd5000488'
assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=root)
assert not (tmp / 'metodobase-mfa31-fixture-compose-20261019').exists()
needle = b"assert sum(row['original_asserts_exact'] for name, row in assertions.items() if 'team_' in name) == 109"
assert blob.count(needle) == 1
refined = blob.replace(needle, needle[:-3] + b'110')
refined = refined.replace(b'metodobase-mfa31-fixture-compose-20261019', b'metodobase-mfa31-fixture-compose-v2-20261019')
marker = b"(OUT / 'receipt.json').write_bytes"
assert refined.count(marker) == 1
explanation = b"receipt['assert_inventory_scope'] = 'Root counts all module functions including invite helper:110of111 original team/entitlement asserts exact plus1 approved status change. Author109of110 covers test functions only and excludes that unchanged helper assertion. Diary66of66 exact. No semantic assertion filter or comparison changed.'\n"
refined = refined.replace(marker, explanation + marker)
target = tmp / 'metodobase-mfa31-fixture-compose-v2.py'
with target.open('xb') as output:
    output.write(refined)
cause = {'original_driver_sha256': hashlib.sha256(blob).hexdigest(), 'refined_driver_sha256': hashlib.sha256(refined).hexdigest(),
         'cause': 'Original precondition expected author test-function count109, while root loop includes the unchanged invite helper assertion. Read-only inspection independently found module102+9 original asserts,110exact+1approved change. Original guard stopped before OUT creation or merge. New guard fixes inventory scope only; all per-function exact assertion comparisons remain.',
         'source_clean': True, 'merge_started_on_first_attempt': False}
(tmp / 'metodobase-mfa31-fixture-compose-count-cause.json').write_bytes((json.dumps(cause, indent=2) + '\n').encode())
print(json.dumps(cause))
