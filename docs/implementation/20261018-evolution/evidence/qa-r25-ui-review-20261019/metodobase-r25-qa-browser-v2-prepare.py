from pathlib import Path
import ast,hashlib,json,subprocess
TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
original=TEMP/'metodobase-r25-qa-browser-initial-syntax-error.cjs'
before=original.read_text(encoding='utf-8-sig')
assert "meal:'desayuno',completed:true}}})).status()" in before
code=before.replace("meal:'desayuno',completed:true}}})).status()","meal:'desayuno',completed:true}})).status()")
old="assert.equal(await page.locator('#measurement-fields').isDisabled(),true);"
new="assert.equal(await page.locator('#measurement-fields').evaluate(fieldset=>fieldset.disabled),true);assert.equal(await page.locator('#measurement-weight').isDisabled(),true);"
assert code.count(old)==1;code=code.replace(old,new)
dest=TEMP/'metodobase-r25-qa-browser-v2.cjs'
with dest.open('x',encoding='utf8',newline='\n') as stream:stream.write(code)
runner=(TEMP/'metodobase-r25-qa-browser-run.py').read_text(encoding='utf8')
runner=runner.replace("metodobase-r25-qa-ui-browser-20261019'","metodobase-r25-qa-ui-browser-v2-20261019'")
runner=runner.replace("qa-r25-ui-browser-independent-20261019'","qa-r25-ui-browser-v2-independent-20261019'")
runner=runner.replace("metodobase-r25-qa-browser.cjs'","metodobase-r25-qa-browser-v2.cjs'")
runner=runner.replace("'node_package_json_sha256':", "'pip_check':subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True).returncode,\n        'node_package_json_sha256':")
rdest=TEMP/'metodobase-r25-qa-browser-v2-run.py';ast.parse(runner)
with rdest.open('x',encoding='utf8',newline='\n') as stream:stream.write(runner)
bundle=Path(r'F:\MetodoBaseWeb-execution-20261018\tests\e2e\node_modules\playwright-core\lib\coreBundle.js')
text=bundle.read_text(encoding='utf8');index=text.index('function getAriaDisabled')
proof={'initial_browser_failure':'isDisabled(FIELDSET) is false in installed Playwright even if disabled property is true. No product source changed.',
    'installed_bundle_SHA256':hashlib.sha256(bundle.read_bytes()).hexdigest(),'bounded_source':text[index:index+800],
    'changes':'New driver derives from original UTF8 pre-syntax-fix source to avoid the first PowerShell rewrite encoding; fixes the extra closing brace and uses actual DOM fieldset.disabled plus descendant input isDisabled. All business assertions unchanged.'}
with (TEMP/'metodobase-r25-qa-browser-v2-harness-correction.json').open('x',encoding='utf8') as stream:json.dump(proof,stream,indent=2)
result=subprocess.run([r'C:\Program Files\nodejs\node.exe','--check',str(dest)],capture_output=True)
assert result.returncode==0,result.stderr
print('New browser and runner parsed; old prefix untouched')
