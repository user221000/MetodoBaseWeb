from pathlib import Path
import ast,hashlib,json,subprocess
TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp');OLD=Path(r'F:\mb-retirement32-public-qa-20261019');ROOT=Path(r'F:\mb-retirement32-cleanup-qa-20261019')
HEAD='2273616eb218adfdd30680e111da50a4599a8c53';BEFORE='219f89a5ee0196061fea5b67e36ae07daf7f4316'
raw=(OLD/'tests/test_qa_retirement32_public.py').read_bytes();assert raw==(TEMP/'metodobase-retirement32-qa-http-v2.py').read_bytes()
with (ROOT/'tests/test_qa_retirement32_public.py').open('xb') as stream:stream.write(raw)
git=lambda *args:subprocess.check_output(['git',*args],cwd=ROOT)
names=git('diff','--name-only',BEFORE,HEAD,'--','web','api','core','config','db_bootstrap.py').decode().splitlines();assert names==['web/routes/progress_retirement.py']
before=git('show',BEFORE+':web/routes/progress_retirement.py');after=git('show',HEAD+':web/routes/progress_retirement.py')
def outside(raw):return [ast.dump(node,include_attributes=False) for node in ast.parse(raw).body if not(isinstance(node,ast.FunctionDef) and node.name=='_execute')]
assert outside(before)==outside(after)
source=(TEMP/'metodobase-retirement32-qa-http-v2-run.py').read_text(encoding='utf8')
source=source.replace(str(OLD),str(ROOT)).replace(BEFORE,HEAD).replace('qa-http-v2-20261019','qa-cleanup-http-20261019').replace('qa-retirement32-http-v2-independent-20261019','qa-retirement32-cleanup-http-independent-20261019')
source=source.replace('This run repeats only the8 own HTTP cases after correcting the incidental-CSRF and creation-factory harness assumptions.','This run repeats the exact8 own HTTP cases with RAW test unchanged after the sole _execute cleanup repair. No Chrome run or inherited Chrome acceptance is claimed for227.')
ast.parse(source)
with (TEMP/'metodobase-retirement32-qa-cleanup-run.py').open('x',encoding='utf8',newline='\n') as stream:stream.write(source)
proof={'before_source':BEFORE,'after_source':HEAD,'owned_test_RAW_exact':True,'owned_test_SHA256':hashlib.sha256(raw).hexdigest(),'runtime_changed_paths':names,'entire_module_AST_outside_execute_exact':True,'browser_source_remains':BEFORE,'no_product_QA_edit':True}
with (TEMP/'metodobase-retirement32-qa-cleanup-preservation.json').open('x',encoding='utf8') as stream:json.dump(proof,stream,indent=2)
print('Cleanup8HTTP prepared with RAW-identical test; only_execute AST differs')
