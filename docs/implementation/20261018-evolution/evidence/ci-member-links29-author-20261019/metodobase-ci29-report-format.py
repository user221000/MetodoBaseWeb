"""Reproduce and repair report serialization only; keep every VM assertion."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
root=Path('F:/mb-r12-ci29-20261019')
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-report-format-20261019')
out.mkdir(exist_ok=False)
old=root/'docs/implementation/20261018-evolution/evidence/r12-composed-export-fixture-20261019/before17'
modules={'member_link_context':26,'member_link_fragment':15,'member_link_api':23,'member_link_consumers':16}
rows=[]
for name,minimum in modules.items():
    content=(old/(name+'.json')).read_bytes();(out/(name+'-before.json')).write_bytes(content)
    before=subprocess.run([sys.executable,'scripts/check_frontend_report.py',str(out/(name+'-before.json')),
                           '--format','counts','--minimum',str(minimum)],cwd=root,capture_output=True)
    assert before.returncode==1
    (out/(name+'-before-guard.log')).write_bytes(before.stdout+before.stderr)
    path=root/'tests/e2e'/(name+'.cjs')
    raw=path.read_bytes();(out/(name+'-before.cjs')).write_bytes(raw)
    source=raw.decode('utf8');needle='results.push({name,passed:'
    assert source.count(needle)==2,name
    changed=source.replace(needle,'results.push({case:name,passed:')
    assert changed.replace('results.push({case:name,passed:',needle)==source
    path.write_bytes(changed.encode())
    result=subprocess.run(['node',str(path)],cwd=root,capture_output=True,timeout=45)
    assert result.returncode==0
    (out/(name+'-after.json')).write_bytes(result.stdout)
    (out/(name+'-after.stderr.log')).write_bytes(result.stderr)
    after=subprocess.run([sys.executable,'scripts/check_frontend_report.py',str(out/(name+'-after.json')),
                          '--format','counts','--minimum',str(minimum)],cwd=root,capture_output=True)
    (out/(name+'-after-guard.log')).write_bytes(after.stdout+after.stderr)
    assert after.returncode==0
    rows.append({'module':name,'minimum':minimum,'before_guard_exit':1,'after_guard_exit':0,
                 'all_assertions_byte_unchanged':True,'old_raw_sha256':hashlib.sha256(raw).hexdigest(),
                 'new_raw_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
workflow=root/'.github/workflows/ci.yml'
text=workflow.read_text(encoding='utf8')
anchor='      - uses: actions/upload-artifact@v4\n'
start=text.index('  postgres:\n');stop=text.index('  redis:\n')
block=text[start:stop];assert block.count(anchor)==1
block=block.replace(anchor,'      - name: Current member link reports retain all selected PostgreSQL cases\n        run: python tests/check_member_link_reports.py\n'+anchor)
workflow.write_bytes((text[:start]+block+text[stop:]).encode())
(out/'review.json').write_bytes((json.dumps({'scope':'VM output key only, name to canonical case; no assertion/product changes',
                                         'results':rows,'cases':sum(modules.values()),'all_green':True},indent=2)+'\n').encode())
print(json.dumps({'report_interfaces_repaired':len(rows),'VM_assertions_green_unchanged':sum(modules.values())}))
