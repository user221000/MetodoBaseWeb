"""Record exact revision: use current reachable433 only; cache physical bytes."""
from pathlib import Path
import ast,hashlib,json,subprocess,sys
T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-r05-new-peer-private-20261019'
O=Path(r'F:/mb-security-r05-classifier-peer-20261019/docs/implementation/20261018-evolution/evidence/security-r05-new-locations-independent-20261019')
prior=T/'metodobase-sec-r05-new-peer-review-20261019.py';raw=prior.read_bytes();source=raw.decode()
with (P/'attempt1-driver.RAW.py').open('xb') as f:f.write(raw)
with (P/'attempt1-before.RAW.json').open('xb') as f:f.write((O/'before.json').read_bytes())
(P/'attempt1-tool-receipt.json').write_bytes((json.dumps({'kind':'Recorded tool result text, not reconstructed process stdout/stderr RAW','exit':1,'exception':'AssertionError','source_line':99,'assertion':'commits <= currently reachable refs; failed for two retained commit IDs from earlier427 list','no_payloads_printed':True},indent=2)+'\n').encode())
replacements=[
    ("O.mkdir();", "O.mkdir(exist_ok=True);"),
    ("def physical(row):", "physical_lines={name:content.split(b'\\n') for name,content in snapfiles.items()}\ndef physical(row):"),
    ("return snapfiles[row['file']].split(b'\\n')[row['line']-1]", "return physical_lines[row['file']][row['line']-1]"),
    ("assert commits<=reachable and all(re.fullmatch('[0-9a-f]{40}',c) for c in commits)",
     "assert all(re.fullmatch('[0-9a-f]{40}',c) for c in commits)\noriginal_pinned_count=len(commits);ignored_noncurrent_refs=sorted(commits-reachable)\ncommits &= reachable\nassert len(commits)==433 and len(ignored_noncurrent_refs)==2\nsave('reachable-ref-scope.json',{'original_union':original_pinned_count,'current_reachable_used':len(commits),'earlier_pins_no_longer_current':ignored_noncurrent_refs,'ignored_refs_not_used_for_any_proof':True})"),
]
revised=source
for old,new in replacements:assert revised.count(old)==1;revised=revised.replace(old,new,1)
inverse=revised
for old,new in reversed(replacements):inverse=inverse.replace(new,old,1)
assert inverse==source
(O/'replay-adapter-binding.json').write_bytes((json.dumps({'original_driver_SHA256':hashlib.sha256(raw).hexdigest(),'executed_revision_SHA256':hashlib.sha256(revised.encode()).hexdigest(),'full_inverse_exact':True,'changes':'Only retain already-created evidence directory, cache identical physical split bytes, and restrict historical witnesses to433 currently reachable commits instead of435 union. Two old detached refs not used. No semantic classification assertions weakened.'},indent=2)+'\n').encode())
exec(compile(revised,str(prior)+':v2_current433_cached_physical','exec'),{'__name__':'__main__'})
