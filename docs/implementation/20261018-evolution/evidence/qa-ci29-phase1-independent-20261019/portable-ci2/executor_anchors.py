"""Reject each of eight mutated executable bodies against authenticated current literals."""
from support import *
from unittest.mock import patch
sys.path.insert(0,str(ROOT))
from tests import verify_member_links_ci as guard
before=photo('executor-anchors-before')
phase=TEMP/'executor-anchors';phase.mkdir(exist_ok=False)
assert len(guard.PINNED_CURRENT_GATES)==8
for name,digest in guard.PINNED_CURRENT_GATES.items():
    raw=(ROOT/name).read_bytes();assert sha(raw.replace(b'\r\n',b'\n'))==digest
    target=phase/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
rows=[]
with patch.object(guard,'ROOT',phase):
    guard.authenticate_current_gates()
    for name in guard.PINNED_CURRENT_GATES:
        target=phase/name;original=target.read_bytes();target.write_bytes(b'SYNTHETIC_PRIMARY_SUBSTITUTION\n')
        try:
            try:guard.authenticate_current_gates()
            except AssertionError as error:rejected=str(error)==name
            else:rejected=False
        finally:target.write_bytes(original)
        assert rejected;rows.append({'case':name,'passed':True,'body_never_executed':True})
    guard.authenticate_current_gates()
after=photo('executor-anchors-after');assert before==after
save('executor-anchors-result.json',{'head':HEAD,'passed':len(rows),'total':8,'results':rows,'source_helpers_packages_stable':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'scope':'Only current primary-authentication calls, no mutated body execution or subprocess.'})
print(json.dumps({'passed':len(rows),'total':8,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89}))
