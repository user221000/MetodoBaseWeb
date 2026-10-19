from pathlib import Path
import ast
import json
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
old=tmp/'metodobase-r17-author-proof-seal.py';new=tmp/'metodobase-r17-author-proof-seal-v2.py'
source=old.read_text(encoding='utf8')
for before,after in [
 ("},ensure_ascii=False,indent=2)+'\\n').encode())","},ensure_ascii=False,indent=2)+'\\n').encode()"),
 ("for n,b in sorted(private.items())}},indent=2)+'\\n').encode())","for n,b in sorted(private.items())}},indent=2)+'\\n').encode()")]:
    assert source.count(before)==1
    source=source.replace(before,after)
needle="blobs['driver.py']=Path(__file__).read_bytes()"
replacement=needle+"\nblobs['preconditions/seal-v1-syntax-error.py']=(tmp/'metodobase-r17-author-proof-seal.py').read_bytes()\nblobs['preconditions/seal-v2-prepare.py']=(tmp/'metodobase-r17-author-proof-seal-v2-prepare.py').read_bytes()"
assert source.count(needle)==1
source=source.replace(needle,replacement)
ast.parse(source);assert not new.exists();new.write_bytes(source.encode())
print(json.dumps({'prepared':str(new),'previous_failure':'SyntaxError before any execution or publication'}))
