"""Focused independent controls for LF authentication and mutable runtime report specs."""
from support import *
from unittest.mock import patch
import importlib.util
import tempfile
sys.path.insert(0,str(ROOT))
from tests import verify_member_links_ci as guard
from tests import check_member_link_reports as checker
before=photo('own-controls-before')
phase=TEMP/'own-controls';phase.mkdir(exist_ok=False)
original=guard.ROOT
crlf=phase/'CRLF-authenticated'
for name in guard.PINNED_CURRENT_GATES:
    target=crlf/name;target.parent.mkdir(exist_ok=True,parents=True)
    target.write_bytes((ROOT/name).read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
try:
    guard.ROOT=crlf
    guard.authenticate_current_gates()
finally:guard.ROOT=original
rows=[{'case':'genuine-CRLF-helpers-accepted-under-LF-contract','passed':True}]
expected=dict(checker.REPORTS)
lowered=dict(expected)
target='pytest-postgres-member-services.xml'
lowered[target]=(expected[target][0]-1,expected[target][1])
for label,replacement in [('cached-runtime-table-erased',{}),('cached-runtime-minimum-reduced',lowered)]:
    with patch.object(checker,'REPORTS',replacement),patch.object(guard.subprocess,'run',side_effect=RuntimeError('checker must not execute')) as execute:
        try:guard.report_canaries(phase/label)
        except AssertionError:rejected=True
        else:rejected=False
        rows.append({'case':label+'-rejected-before-execution','passed':rejected and not execute.called})
after=photo('own-controls-after')
assert before==after and all(row['passed'] for row in rows)
report={'head':HEAD,'results':rows,'total':len(rows),'passed':sum(row['passed'] for row in rows),'source_helpers_packages_stable':True,'source_count':before['source_count'],'helper_count':before['helper_count'],'packages':89,'scope':'No PG/browser/Actions. Runtime table modifications are process-local and restored.'}
save('own-controls-result.json',report)
print(json.dumps({key:report[key] for key in ['total','passed','source_count','helper_count','packages']}))
