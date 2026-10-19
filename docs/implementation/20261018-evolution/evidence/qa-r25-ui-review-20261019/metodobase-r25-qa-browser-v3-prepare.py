from pathlib import Path
import ast,json,subprocess
TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
code=(TEMP/'metodobase-r25-qa-browser-v2.cjs').read_text(encoding='utf8')
old="await page.locator('#measurement-date').focus();await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.id),'measurement-weight');await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.id),'measurement-fat');"
new="await page.locator('#measurement-date').focus();const dateTabSequence=[];for(let index=0;index<6;index++){await page.keyboard.press('Tab');const focused=await page.evaluate(()=>document.activeElement.id);dateTabSequence.push(focused);if(focused==='measurement-weight')break;}assert.equal(dateTabSequence.at(-1),'measurement-weight');report.dateTabSequence=dateTabSequence;await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.id),'measurement-fat');"
assert code.count(old)==1;code=code.replace(old,new)
dest=TEMP/'metodobase-r25-qa-browser-v3.cjs'
with dest.open('x',encoding='utf8',newline='\n') as stream:stream.write(code)
runner=(TEMP/'metodobase-r25-qa-browser-v2-run.py').read_text(encoding='utf8')
runner=runner.replace('qa-ui-browser-v2-20261019','qa-ui-browser-v3-20261019').replace('qa-r25-ui-browser-v2-independent-20261019','qa-r25-ui-browser-v3-independent-20261019').replace('qa-browser-v2.cjs','qa-browser-v3.cjs')
ast.parse(runner)
with (TEMP/'metodobase-r25-qa-browser-v3-run.py').open('x',encoding='utf8',newline='\n') as stream:stream.write(runner)
assert subprocess.run([r'C:\Program Files\nodejs\node.exe','--check',str(dest)],capture_output=True).returncode==0
with (TEMP/'metodobase-r25-qa-browser-v3-harness-correction.json').open('x',encoding='utf8') as stream:json.dump({'before':'One Tab incorrectly assumed a native date input has one focus segment. Actual focused id remained measurement-date.',
    'after':'At most6 actual Tab presses must leave native date segments and reach weight; the next Tab must reach body-fat. Focus sequence is recorded. Other business and access assertions unchanged. Prior raw report/screens preserved.'},stream,indent=2)
print('Parsed new bounded native-date keyboard harness')
