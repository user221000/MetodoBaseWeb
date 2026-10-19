"""Clear obsolete account summaries after committed MFA changes and local closure."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

root=Path(r'F:\mb-mfa31-compose-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-summary-fix-20261019')
canary=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-summary-independent-20261019\own_summary.cjs')
base='102f75f28dc7ba7688ed24d97d658b7826ab16c4'
name='web/static/js/mfa-ui.js'
git=lambda *args:subprocess.check_output(['git',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
assert hashlib.sha256(canary.read_bytes()).hexdigest()=='b704b6b2a8c8296306fcf9176b10fbfb13dec058100297ff3443fb9c7bda7239'
before=(root/name).read_bytes()
assert git('hash-object','--path='+name,'--',name).strip()==git('rev-parse',base+':'+name).strip()
out.mkdir(exist_ok=False)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
(out/'frozen-independent-canary.raw.cjs').write_bytes(canary.read_bytes())
(out/'mfa-ui.before.raw.js').write_bytes(before)
env={**os.environ,'MFA_SUMMARY_REVIEW_ROOT':str(root)}


def run(label):
    result=subprocess.run([r'C:\Program Files\nodejs\node.exe',str(canary)],cwd=root,env=env,capture_output=True,timeout=40,check=False)
    (out/(label+'.stdout.raw.json')).write_bytes(result.stdout)
    (out/(label+'.stderr.raw.log')).write_bytes(result.stderr)
    return result,json.loads(result.stdout)


initial,data_before=run('before')
assert initial.returncode==1 and data_before['total']==3 and data_before['passed']==0
newline=b'\r\n' if b'\r\n' in before else b'\n'
old_kit=b'    },onKit(codes,closed){'+newline
new_kit=old_kit+b"      Api.mfa.check(closed);get('mfa-account-summary').textContent='';"+newline
old_closed=b"      Api.mfa.check(closed);form.hidden=true;confirmation.hidden=true;get('mfa-account-google').hidden=true;state.textContent='Autenticaci"
new_closed=b"      Api.mfa.check(closed);get('mfa-account-summary').textContent='';form.hidden=true;confirmation.hidden=true;get('mfa-account-google').hidden=true;state.textContent='Autenticaci"
assert before.count(old_kit)==before.count(old_closed)==1
after=before.replace(old_kit,new_kit).replace(old_closed,new_closed)
assert after.replace(new_kit,old_kit).replace(new_closed,old_closed)==before
(root/name).write_bytes(after)
(out/'mfa-ui.after.raw.js').write_bytes(after)
subprocess.run([r'C:\Program Files\nodejs\node.exe','--check',name],cwd=root,check=True,capture_output=True)
result,data_after=run('after')
assert result.returncode==0 and data_after['total']==data_after['passed']==3
assert hashlib.sha256(canary.read_bytes()).hexdigest()=='b704b6b2a8c8296306fcf9176b10fbfb13dec058100297ff3443fb9c7bda7239'
assert git('diff','--name-only','-z').decode().split('\0')[:-1]==[name]
subprocess.run(['git','diff','--check','--',name],cwd=root,check=True,capture_output=True)
subprocess.run(['git','add','--',name],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Discard obsolete MFA account summary after confirmed changes'],cwd=root,check=True,capture_output=True)
receipt={'before':base,'head':git('rev-parse','HEAD').decode().strip(),'before_cases':{'total':3,'passed':0},'after_cases':{'total':3,'passed':3},
         'driver_sha256':hashlib.sha256(canary.read_bytes()).hexdigest(),'before_RAW_sha256':hashlib.sha256(before).hexdigest(),'after_RAW_sha256':hashlib.sha256(after).hexdigest(),
         'inverse_raw_bytes_exact':True,'scope':'UX-19: clear the previously queried summary in actual onKit/onClosed only after checking the ephemeral closed context. No request, refresh, primary/factor authority, kit validation, storage or business operation changed. Frozen peer canary confirms current mounted UI, eight-code kit or revoke0, local closure, no auth/me request after closure. No new browser/HTTP/PG execution by this fix.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps(receipt))
