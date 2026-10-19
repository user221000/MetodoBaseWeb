from pathlib import Path
import ast
import json
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
old=tmp/'metodobase-checkpoint123-v3.py';new=tmp/'metodobase-checkpoint123-v4.py'
source=old.read_text(encoding='utf8')
before="assert set(doc)=={'source_head','attributes','entries'}"
after="""assert set(doc)=={'source_head','attributes','entries','count','phase_summary_SHA256'}
        assert doc['count']==len(doc['entries'])==25
        assert doc['phase_summary_SHA256']=='61ffbfb152cf8de21a42697ca089d03abddf06ae3de877627d40d7d84ed54891'"""
assert source.count(before)==1
source=source.replace(before,after)
needle="contents={'driver.py':Path(__file__).read_bytes()}"
replacement=needle+"\ncontents['preconditions/driver-v3-guard.py']=(tmp/'metodobase-checkpoint123-v3.py').read_bytes()\ncontents['preconditions/prepare-v4.py']=(tmp/'metodobase-checkpoint123-v4-prepare.py').read_bytes()\ncontents['preconditions/v3-guard-cause.json']=(json.dumps({'failed_before_any_writes':True,'cause':'The manifest metadata also includes count and phase_summary_SHA256; a guard inferred from a partial head read rejected the complete authenticated format.','correction':'Read actual complete top-level keys, preserve exact schema guard and authenticate count25 and phase-summary anchor explicitly.'},indent=2)+'\\n').encode()"
assert source.count(needle)==1
source=source.replace(needle,replacement)
ast.parse(source);assert not new.exists();new.write_bytes(source.encode())
print(json.dumps({'prepared':str(new),'closed_source_evidence_unchanged':True}))
