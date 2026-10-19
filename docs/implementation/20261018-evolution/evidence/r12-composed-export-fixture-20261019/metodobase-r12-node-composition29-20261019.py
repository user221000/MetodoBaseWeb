"""Run maintained CI VM contracts and new R12 VM contracts on one composition."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

root=Path('F:/mb-r12-full29-20261019')
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r12-node-composition29-20261019')
out.mkdir(exist_ok=False)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert head=='9d0c5c469aa261f027f5ca7c413f477c9e521206'
names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1]
names=[name for name in names if not name.startswith('docs/') and (root/name).is_file()]
def photo():return {name:sha((root/name).read_bytes()) for name in sorted(names)}
before=photo()
(out/'before-source.json').write_bytes((json.dumps(before,indent=2)+'\n').encode())
node=Path(shutil.which('node')).resolve()
version=subprocess.check_output([str(node),'--version'],text=True).strip()
modules=['auth_refresh','auth_refresh_storage','auth_refresh_race_review','auth_refresh_security_review',
    'personal_operation','personal_operation_ambiguity_review','personal_diary_api','personal_diary_controller',
    'personal_logout','personal_logout_ack','personal_export_controls','personal_history',
    'member_link_context','member_link_fragment','member_link_api','member_link_consumers','member_link_export']
results=[]
for name in modules:
    result=subprocess.run([str(node),'tests/e2e/'+name+'.cjs'],cwd=root,capture_output=True,timeout=45)
    (out/(name+'.json')).write_bytes(result.stdout)
    (out/(name+'.stderr.log')).write_bytes(result.stderr)
    row={'module':name,'exit_code':result.returncode}
    try:
        data=json.loads(result.stdout)
        row['total']=data.get('total')
        row['passed']=data.get('passed')
        if 'report' in data and isinstance(data['report'],list):
            row['report_count']=len(data['report'])
            row['all_report_passed']=all(item.get('passed') is True for item in data['report'])
    except (json.JSONDecodeError,AttributeError):row['parseable_report']=False
    results.append(row)
after=photo();assert before==after
(out/'after-source.json').write_bytes((json.dumps(after,indent=2)+'\n').encode())
summary={'head':head,'Node_version':version,'Node_executable_sha256':sha(node.read_bytes()),'sources':len(names),'sources_stable':True,'results':results,'nonzero_exits':sum(row['exit_code']!=0 for row in results),'scope':'Only VM contracts; no browser or real R12 HTTP flow/provider calls.'}
(out/'summary.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
print(json.dumps(summary))
raise SystemExit(int(bool(summary['nonzero_exits'])))
