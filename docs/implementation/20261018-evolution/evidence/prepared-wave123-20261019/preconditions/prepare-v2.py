from pathlib import Path
import ast
import json
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
old=tmp/'metodobase-checkpoint123.py';new=tmp/'metodobase-checkpoint123-v2.py'
source=old.read_text(encoding='utf8')
before="'parallel':'Not started; runs only after serial acceptance or an explicit new diagnostic need.'},indent=2)+'\\n').encode())"
after=before[:-1]
assert source.count(before)==1
source=source.replace(before,after)
needle="contents={'driver.py':Path(__file__).read_bytes()}"
replacement=needle+"\ncontents['preconditions/driver-v1-SyntaxError.py']=(tmp/'metodobase-checkpoint123.py').read_bytes()\ncontents['preconditions/prepare-v2.py']=Path(r'C:\\Users\\Consu\\AppData\\Local\\Temp\\metodobase-checkpoint123-v2-prepare.py').read_bytes()"
assert source.count(needle)==1
source=source.replace(needle,replacement)
ast.parse(source);assert not new.exists();new.write_bytes(source.encode())
print(json.dumps({'prepared':str(new),'previous_failure':'SyntaxError before execution; no registry/docs/stage/commit changes'}))
