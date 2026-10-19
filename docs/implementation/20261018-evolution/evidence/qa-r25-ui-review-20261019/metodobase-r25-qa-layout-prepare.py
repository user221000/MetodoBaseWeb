from pathlib import Path
import ast
TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
source=(TEMP/'metodobase-r25-qa-browser-v3-run.py').read_text(encoding='utf8')
source=source.replace('qa-ui-browser-v3-20261019','qa-ui-layout-before-20261019').replace('qa-r25-ui-browser-v3-independent-20261019','qa-r25-ui-layout-before-independent-20261019').replace('qa-browser-v3.cjs','qa-layout.cjs')
ast.parse(source)
with (TEMP/'metodobase-r25-qa-layout-before-run.py').open('x',encoding='utf8',newline='\n') as stream:stream.write(source)
print('Layout runner parsed; independent legibility criterion fixed before product repair')
