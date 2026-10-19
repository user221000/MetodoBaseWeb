"""Canonical VM report rows, preserving first interface failure and assertions."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
root=Path('F:/mb-r12-ci29-20261019')
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-report-format-v2-20261019');out.mkdir(exist_ok=False)
old=root/'docs/implementation/20261018-evolution/evidence/r12-composed-export-fixture-20261019/before17'
modules={'member_link_context':26,'member_link_fragment':15,'member_link_api':23,'member_link_consumers':16}
rows=[]
for name,minimum in modules.items():
    (out/(name+'-before.json')).write_bytes((old/(name+'.json')).read_bytes())
    before=subprocess.run([sys.executable,'scripts/check_frontend_report.py',str(out/(name+'-before.json')),
                           '--format','counts','--minimum',str(minimum)],cwd=root,capture_output=True)
    assert before.returncode==1
    (out/(name+'-before-guard.log')).write_bytes(before.stdout+before.stderr)
    relative='tests/e2e/'+name+'.cjs';path=root/relative
    raw=subprocess.check_output(['git','show','HEAD:'+relative],cwd=root)
    current=path.read_bytes().replace(b'\r\n',b'\n')
    original=raw.decode('utf8');needle='results.push({name,passed:'
    assert original.count(needle)==2
    intermediate=original.replace(needle,'results.push({case:name,passed:')
    assert current.decode('utf8') in [original,intermediate]
    changed=intermediate
    if name=='member_link_context':
        label="test(name+' synchronously clears resource scopes'"
        replacement="test(name+(name==='storage'?' key='+String(event.key):'')+' synchronously clears resource scopes'"
        assert changed.count(label)==1;changed=changed.replace(label,replacement)
        assert changed.replace(replacement,label).replace('results.push({case:name,passed:',needle)==original
    else:assert changed.replace('results.push({case:name,passed:',needle)==original
    (out/(name+'-before.cjs')).write_bytes(raw);path.write_bytes(changed.encode())
    result=subprocess.run(['node',str(path)],cwd=root,capture_output=True,timeout=45)
    (out/(name+'-after.json')).write_bytes(result.stdout);(out/(name+'-after.stderr.log')).write_bytes(result.stderr)
    after=subprocess.run([sys.executable,'scripts/check_frontend_report.py',str(out/(name+'-after.json')),
                          '--format','counts','--minimum',str(minimum)],cwd=root,capture_output=True)
    (out/(name+'-after-guard.log')).write_bytes(after.stdout+after.stderr)
    rows.append({'module':name,'minimum':minimum,'before_guard_exit':before.returncode,'Node_exit':result.returncode,
                 'after_guard_exit':after.returncode,'all_assertions_byte_unchanged':True,
                 'old_Git_sha256':hashlib.sha256(raw).hexdigest(),'new_raw_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(out/'review.json').write_bytes((json.dumps({'scope':'Only canonical case output key and two distinct Storage event labels; no assertion/product changes',
                                         'errata':'V1 stopped after context: row key repaired but historical Storage labels duplicated. Original26passed preserved. V2 labels event.key explicitly.',
                                         'results':rows,'cases':sum(modules.values())},indent=2)+'\n').encode())
assert all(row['Node_exit']==row['after_guard_exit']==0 for row in rows),rows
workflow=root/'.github/workflows/ci.yml';text=workflow.read_text(encoding='utf8')
anchor='      - uses: actions/upload-artifact@v4\n';start=text.index('  postgres:\n');stop=text.index('  redis:\n')
block=text[start:stop];assert block.count(anchor)==1
block=block.replace(anchor,'      - name: Current member link reports retain all selected PostgreSQL cases\n        run: python tests/check_member_link_reports.py\n'+anchor)
workflow.write_bytes((text[:start]+block+text[stop:]).encode())
print(json.dumps({'report_interfaces_repaired':len(rows),'unchanged_VM_assertions_green':sum(modules.values())}))
