from pathlib import Path
import json
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
old=tmp/'metodobase-checkpoint119-resume.py'
new=tmp/'metodobase-checkpoint119-resume-v2.py'
source=old.read_text(encoding='utf8')
needle='guards=[n for n in prelude if isinstance(n,ast.Assert)]\nassert len(guards)==1 and "status" in ast.unparse(guards[0])'
replacement='guards=[n for n in prelude if isinstance(n,ast.Assert) and "status" in ast.unparse(n)]\nassert len(guards)==1'
assert source.count(needle)==1
source=source.replace(needle,replacement)
needle="(refused/'resume-driver.py').write_bytes(Path(__file__).read_bytes())"
replacement=needle+"\n(refused/'resume-initial-driver.py').write_bytes((TMP/'metodobase-checkpoint119-resume.py').read_bytes())\n(refused/'resume-prepare.py').write_bytes((TMP/'metodobase-checkpoint119-resume-v2-prepare.py').read_bytes())"
assert source.count(needle)==1
source=source.replace(needle,replacement)
assert not new.exists()
new.write_bytes(source.encode())
print(json.dumps({'correction':'Select the single original clean-tree guard by AST expression; retain the other freeze-hash guard. Initial resume stopped before writes.'}))
