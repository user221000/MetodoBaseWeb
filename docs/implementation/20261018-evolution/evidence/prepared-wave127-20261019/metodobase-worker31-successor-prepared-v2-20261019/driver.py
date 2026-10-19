from pathlib import Path
import ast
import hashlib
import json
import subprocess

main=Path(r'F:\MetodoBaseWeb-execution-20261018')
runtime=Path(r'F:\mb-mfa31-runtime-logging-20261019')
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
out=tmp/'metodobase-worker31-successor-prepared-v2-20261019'
assert not out.exists()
sha=lambda blob:hashlib.sha256(blob).hexdigest()
old=main/'docs/implementation/20261018-evolution/evidence/runtime31-f74a-logging-partial-public-20261019/drivers/smoke_observe_guest.py.txt'
tree=ast.parse(old.read_bytes())
values=[n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)]
assert len(values)==1
original=values[0]
bad=" assert all(r['relrowsecurity'] and r['relforcerowsecurity'] for r in rls if r['relname'].startswith('mfa_'))"
assert original.count(bad)==1
contract_name='web/database/alembic/schema_targets/20261019_mfa_postgresql.json'
contract=subprocess.check_output(['git','--no-replace-objects','show','f74a0a20e83b53ac7a5c8e8a0408f299940126f9:'+contract_name],cwd=runtime)
document=json.loads(contract)
forced=sorted(row[0] for row in document['tenant_security']['tables'] if row[1] and row[2])
assert len(forced)==25
replacement="\n".join([
 " contract_blob=Path('/app/"+contract_name+"').read_bytes()",
 " assert hashlib.sha256(contract_blob).hexdigest()=='"+sha(contract)+"'",
 " contract=json.loads(contract_blob)",
 " assert head=='20261019_mfa'",
 " observed_flags=[[r['relname'],r['relrowsecurity'],r['relforcerowsecurity']] for r in rls if r['relname']!='alembic_version']",
 " assert observed_flags==contract['tenant_security']['tables']",
])
successor=original.replace(bad,replacement)
ast.parse(successor)
assert successor.replace(replacement,bad)==original
assert "if r['relname'].startswith('mfa_')" not in successor
assert 'len(functions)==19' not in successor
# This is a prepared derivative, not an execution or replacement of prior RAW.
out.mkdir()
files={'driver.py':Path(__file__).read_bytes(),'original-worker-payload.EXTRACTED.py':original.encode(),
       'successor-worker-payload.py':successor.encode()}
receipt={'runtime_source':'f74a0a20e83b53ac7a5c8e8a0408f299940126f9',
 'image':'sha256:dc8fab52ffd440399baba71923aba008d54ebfbcf503d149b933b15f9ada62e3',
 'producer_manifest_sha256':'b757fe2f19dde492daadc98dc596775f16199ab6a425bec4a17c80fef2c8faa8',
 'original_guest_driver_sha256':sha(old.read_bytes()),'payload_derivation':'Python string value extracted from sealed driver AST; derived preparation bytes, not an original execution RAW file',
 'earlier_preparation_erratum':'v1 used RAW in the derived payload filename; v1 remains unchanged. This v2 corrects the label only, payload bytes and all assertions identical.',
 'full_payload_inverse_exact':True,'contract_path':contract_name,'contract_sha256':sha(contract),
 'expected_FORCED_RLS_tables':forced,
 'scope':'Preparation only. Replaces exactly one invalid prefix assertion with the frozen31 complete table-flag contract. Existing verify_runtime_schema checks the frozen policies/member functions. No universal public-function count. All other settings, PID1, role, head, source-hash and UID statements unchanged.',
 'execution':None,'requirements_for_execution':['new evidence prefix and immutable first failure','existing retained image; no build',
 'fresh owned UUID/roles and strict closure','actual production entrypoint and fresh PID1 fingerprint','VM/Chrome RAM lease and guard','no attribution to schema32 or job queue execution']}
files['receipt.json']=(json.dumps(receipt,indent=2)+'\n').encode()
for name,blob in files.items():
    with(out/name).open('xb')as handle:handle.write(blob)
print(json.dumps({'prepared':str(out),'successor_sha256':sha(successor.encode()),'contract_sha256':sha(contract),'executed':False}))
