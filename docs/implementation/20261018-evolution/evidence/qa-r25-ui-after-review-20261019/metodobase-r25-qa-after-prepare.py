from pathlib import Path
import ast,hashlib,json,subprocess
TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp');OLD=Path(r'F:\mb-r25-qa-ui-20261019');ROOT=Path(r'F:\mb-r25-qa-ui-after-20261019')
HEAD='345aa7ce16f65fec9481b48cfcd63c33ff3835fc';SHA=lambda raw:hashlib.sha256(raw).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==HEAD
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT).strip()
for name in ('tests/test_qa_progress32_independent.py','tests/check_progress32_layout_qa.py','tests/e2e/progress32_layout_qa.cjs'):
    raw=subprocess.check_output(['git','show','2c8ee350aaa8d0d95b5c6346dc355b3efc3d0040:'+name],cwd=OLD)
    with (ROOT/name).open('xb') as stream:stream.write(raw)
frozen=(OLD/'docs/implementation/20261018-evolution/evidence/qa-r25-ui-http-replay-independent-20261019/independent-test.py').read_bytes()
current=(ROOT/'tests/test_qa_progress32_independent.py').read_bytes()
fn=lambda raw:[ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
assert fn(frozen)==fn(current) and len(fn(current))==7
original_layout=(TEMP/'metodobase-r25-qa-layout.cjs').read_bytes();assert original_layout==(ROOT/'tests/e2e/progress32_layout_qa.cjs').read_bytes()
http=(TEMP/'metodobase-r25-qa-ui-http-replay.py').read_text(encoding='utf8')
http=http.replace(str(OLD),str(ROOT)).replace('qa-ui-http-replay-20261019','qa-ui-http-after-20261019').replace('qa-r25-ui-http-replay-independent-20261019','qa-r25-ui-http-after-independent-20261019').replace('b7f8e129251dfd5216f811ba77d0b6183ca76735',HEAD)
http=http.replace("'test_sha256':SHA(TEST.read_bytes()),", "'pip_check':subprocess.run([sys.executable,'-m','pip','check'],capture_output=True).returncode,'test_sha256':SHA(TEST.read_bytes()),")
http=http.replace("'-q','tests/test_qa_progress32_independent.py',", "'-q','tests/test_qa_progress32_independent.py::test_eighth_export_cursor_is_lowercase_only_and_does_not_authorize_other_actor',")
http=http.replace("12 independent controls, real registration/login/factories/migrated SQLite32.","Exact2 prior export422 canaries, actual registration/login/both factories/migrated SQLite32. No replay of the other10 controls is claimed on this source.")
ast.parse(http)
with (TEMP/'metodobase-r25-qa-ui-http-after.py').open('x',encoding='utf8',newline='\n') as stream:stream.write(http)
runner=(TEMP/'metodobase-r25-qa-layout-before-run.py').read_text(encoding='utf8')
runner=runner.replace(str(OLD),str(ROOT)).replace('qa-ui-layout-before-20261019','qa-ui-layout-after-20261019').replace('qa-r25-ui-layout-before-independent-20261019','qa-r25-ui-layout-after-independent-20261019').replace('b7f8e129251dfd5216f811ba77d0b6183ca76735',HEAD)
ast.parse(runner)
with (TEMP/'metodobase-r25-qa-layout-after-run.py').open('x',encoding='utf8',newline='\n') as stream:stream.write(runner)
proof={'source_head':HEAD,'previous_qa_commit':'2c8ee350aaa8d0d95b5c6346dc355b3efc3d0040','http_7_function_ASTs_exact':True,'http_current_test_SHA256':SHA(current),'http_frozen_test_SHA256':SHA(frozen),'layout_driver_RAW_exact':True,'layout_driver_SHA256':SHA(original_layout),'layout_parser_SHA256':SHA((ROOT/'tests/check_progress32_layout_qa.py').read_bytes()),'no_product_edit':True}
with (TEMP/'metodobase-r25-qa-after-canary-preservation.json').open('x',encoding='utf8') as stream:json.dump(proof,stream,indent=2)
print('After worktree and exact canaries prepared; both launchers parsed')
