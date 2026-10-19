from pathlib import Path
import ast
import hashlib
import json

tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
old=tmp/'metodobase-mfa31-composed-terminal-sv-regression.py'
target=tmp/'metodobase-mfa31-reviewed-regression.py'
assert not target.exists()
source=old.read_text(encoding='utf8')
edits={
    "root=Path(r'F:\\mb-mfa31-compose-20261019')":"root=Path(r'F:\\mb-mfa31-reviewed-common-20261019')",
    "out=tmp/('metodobase-mfa31-composed-'+mode+'-terminal-sv-20261019')":"out=tmp/('metodobase-mfa31-reviewed-'+mode+'-20261019')",
    "assert result.returncode==0 and not failures and len(cases)>=2598":"assert result.returncode==0 and not failures and len(cases)==3057",
}
for before,after in edits.items():
    assert source.count(before)==1,before
    source=source.replace(before,after)
source+='''
terminal=ET.parse(tmp/'metodobase-mfa31-composed-serial-terminal-sv-20261019/results.xml').findall('.//testcase')
terminal_ids={identity(c) for c in terminal}
current_ids={identity(c) for c in cases}
assert len(current_ids)==len(cases)==3057
assert len(terminal_ids)==3047 and terminal_ids.issubset(current_ids)
extra=current_ids-terminal_ids
expected={'tests.test_current_mfa31_fixture_clock':2,'tests.test_mfa31_contract_clock':5,
          'tests.test_mfa31_contract_clock_keyword':1,'tests.test_bootstrap_outcome_logging':2}
assert len(extra)==10
assert {module:sum(value.startswith(module+'::') for value in extra) for module in expected}==expected
(out/'case-preservation.json').write_bytes((json.dumps({'baseline3047_preserved':True,
    'current3057_unique':True,'new10_case_ids':sorted(extra),'expected_new_modules':expected},indent=2)+'\\n').encode())
'''
ast.parse(source)
target.write_bytes(source.encode())
print(json.dumps({'driver':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                  'prepared_only':True,'expected_cases':3057,'old3047_subset_required':True}))
