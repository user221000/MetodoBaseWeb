from pathlib import Path
import ast
TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
source=(TEMP/'metodobase-r25-qa-layout-after-run.py').read_text(encoding='utf8')
source=source.replace('qa-ui-layout-after-20261019','qa-ui-axe-after-20261019').replace('qa-r25-ui-layout-after-independent-20261019','qa-r25-ui-axe-after-independent-20261019').replace('metodobase-r25-qa-layout.cjs','metodobase-r25-qa-axe-after.cjs')
ast.parse(source)
with (TEMP/'metodobase-r25-qa-axe-after-run.py').open('x',encoding='utf8',newline='\n') as stream:stream.write(source)
print('Affected-view renderer runner parsed')
