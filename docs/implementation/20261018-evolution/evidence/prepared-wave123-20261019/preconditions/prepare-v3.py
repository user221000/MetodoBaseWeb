from pathlib import Path
import ast
import json
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
old=tmp/'metodobase-checkpoint123-v2.py';new=tmp/'metodobase-checkpoint123-v3.py'
source=old.read_text(encoding='utf8')
needle="doc=json.loads(blob);rows=doc.get('files',doc)"
replacement="""doc=json.loads(blob)
    if prefix=='qa-mfa31-current-fixtures-peer-independent-20261019':
        assert set(doc)=={'source_head','attributes','entries'}
        assert doc['source_head']=='79dce040a9d79b51c1971bf4a99338a06c2ac659'
        rows=doc['entries']
    else:rows=doc.get('files',doc)"""
assert source.count(needle)==1
source=source.replace(needle,replacement)
needle="contents={'driver.py':Path(__file__).read_bytes()}"
replacement=needle+"\ncontents['preconditions/driver-v2-manifest-format.py']=(tmp/'metodobase-checkpoint123-v2.py').read_bytes()\ncontents['preconditions/prepare-v3.py']=(tmp/'metodobase-checkpoint123-v3-prepare.py').read_bytes()\ncontents['preconditions/manifest-format-cause.json']=(json.dumps({'failed_before_any_writes':True,'cause':'The QA peer producer uses entries with separate metadata. Treating its top-level metadata as files raised TypeError.','correction':'Authenticate the same pinned manifest and select its exact entries schema, with expected metadata keys and source head. No evidence bytes modified.'},indent=2)+'\\n').encode()"
assert source.count(needle)==1
source=source.replace(needle,replacement)
ast.parse(source);assert not new.exists();new.write_bytes(source.encode())
print(json.dumps({'prepared':str(new),'closed_source_evidence_unchanged':True}))
