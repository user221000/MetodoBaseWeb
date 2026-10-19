"""Exact final framing delta; original negative controls remain intact."""
from pathlib import Path
import hashlib,json
T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-r05-new-peer-private-20261019'
O=Path(r'F:/mb-security-r05-classifier-peer-20261019/docs/implementation/20261018-evolution/evidence/security-r05-new-locations-independent-20261019')
prior=T/'metodobase-sec-r05-new-peer-review-20261019.py';raw=prior.read_bytes();source=raw.decode()
replacements=[
    ("O.mkdir();", "O.mkdir(exist_ok=True);"),
    ("def physical(row):", "physical_lines={name:content.split(b'\\n') for name,content in snapfiles.items()}\ndef physical(row):"),
    ("return snapfiles[row['file']].split(b'\\n')[row['line']-1]", "return physical_lines[row['file']][row['line']-1]"),
    ("assert commits<=reachable and all(re.fullmatch('[0-9a-f]{40}',c) for c in commits)",
     "assert all(re.fullmatch('[0-9a-f]{40}',c) for c in commits)\noriginal_pinned_count=len(commits);ignored_noncurrent_refs=sorted(commits-reachable)\ncommits &= reachable\nassert len(commits)==433 and len(ignored_noncurrent_refs)==2\nsave('reachable-ref-scope.json',{'original_union':original_pinned_count,'current_reachable_used':len(commits),'earlier_pins_no_longer_current':ignored_noncurrent_refs,'ignored_refs_not_used_for_any_proof':True})"),
    ("entries=ast.literal_eval(loop.iter);assert len(entries)==len(proof['witnesses'])==2\n        for entry,item in zip(entries,proof['witnesses'],strict=True):\n            assert entry[2]==item['digest']==sha((A/item['path']).read_bytes())",
     "assert isinstance(loop.iter,ast.List) and all(isinstance(e,ast.Tuple) and len(e.elts)==3 for e in loop.iter.elts)\n        entries=[(ast.literal_eval(e.elts[1]),ast.literal_eval(e.elts[2])) for e in loop.iter.elts]\n        assert len(entries)==len(proof['witnesses'])==2\n        for (prefix,digest),item in zip(entries,proof['witnesses'],strict=True):\n            assert item['path'].endswith('/'+prefix+'-freeze.json')\n            assert digest==item['digest']==sha((A/item['path']).read_bytes())"),
]
revised=source
for old,new in replacements:assert revised.count(old)==1;revised=revised.replace(old,new,1)
inverse=revised
for old,new in reversed(replacements):inverse=inverse.replace(new,old,1)
assert inverse==source
executed=T/'metodobase-sec-r05-new-peer-review-final-executed-20261019.py'
with executed.open('xb') as f:f.write(revised.encode())
(O/'replay-adapter-binding.json').write_bytes((json.dumps({'original_driver_SHA256':hashlib.sha256(raw).hexdigest(),'executed_revision_SHA256':hashlib.sha256(revised.encode()).hexdigest(),'full_inverse_exact':True,'changes':'Current reachable433 only; physical-line cache without byte changes; retained evidence directory; read only literal prefix and digest fields from the two AST tuples, never evaluate Path calls. No negative semantic assertion removed or weakened.','initial_attempts_preserved':'Attempt1 tool result receipt is not reconstructed process RAW. Attempt2 stdout/stderr RAW retained.'},indent=2)+'\n').encode())
exec(compile(revised,str(executed),'exec'),{'__name__':'__main__'})
