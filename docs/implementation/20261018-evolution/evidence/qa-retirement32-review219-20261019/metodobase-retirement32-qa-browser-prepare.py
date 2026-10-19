from pathlib import Path
import ast,subprocess
TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
code=TEMP/'metodobase-retirement32-qa-browser.cjs';text=code.read_text(encoding='utf8')
text=text.replace('Database witnesses keep SV/role/parent/password authority,','Database witnesses keep SV/role/parent authority,')
old="const actual=await route.fetch();assert.equal(actual.status(),200);enteredResolve();await release;try{await route.fulfill({response:actual});}catch{}"
new="try{const actual=await route.fetch();enteredResolve(actual.status());await release;try{await route.fulfill({response:actual});}catch{}}catch{enteredResolve(null);}"
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace("await get('query').click();await entered;assert.equal", "await get('query').click();assert.equal(await entered,200);assert.equal")
code.write_text(text,encoding='utf8',newline='\n')
assert subprocess.run([r'C:\Program Files\nodejs\node.exe','--check',str(code)],capture_output=True).returncode==0
source=(TEMP/'metodobase-r25-qa-layout-after-run.py').read_text(encoding='utf8')
source=source.replace(r'F:\mb-r25-qa-ui-after-20261019',r'F:\mb-retirement32-public-qa-20261019')
source=source.replace('metodobase-r25-qa-ui-layout-after-20261019','metodobase-retirement32-qa-browser-20261019').replace('qa-r25-ui-layout-after-independent-20261019','qa-retirement32-browser-independent-20261019')
source=source.replace('metodobase-r25-qa-browser-server.py','metodobase-retirement32-qa-browser-server.py').replace('metodobase-r25-qa-layout.cjs','metodobase-retirement32-qa-browser.cjs')
source=source.replace('345aa7ce16f65fec9481b48cfcd63c33ff3835fc','219f89a5ee0196061fea5b67e36ae07daf7f4316')
ast.parse(source)
with (TEMP/'metodobase-retirement32-qa-browser-run.py').open('x',encoding='utf8',newline='\n') as stream:stream.write(source)
print('Real retirement browser and owned runner parsed')
