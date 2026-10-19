from pathlib import Path
import ast
import hashlib
import json
import subprocess

root=Path(r'F:\mb-r25-progress32-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r25-router-mount-20261019')
assert not out.exists()
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
base=git('rev-parse','HEAD').decode().strip();assert base=='5637b4daed86fa6ce3024c521aafdb6742373b08'
paths=['api/app.py','web/main_web.py'];planned={}
old='    configure_observability(app)\n'
new='    from web.routes.personal_progress import router as personal_progress_router\n    app.include_router(personal_progress_router, prefix="/api")\n\n'+old
for name in paths:
    raw=(root/name).read_bytes();text=raw.decode();newline='\r\n' if '\r\n' in text else '\n'
    normalized=text.replace('\r\n','\n');original=git('show','HEAD:'+name)
    assert normalized.encode()==original
    assert normalized.count(old)==1 and 'personal_progress_router' not in normalized
    changed=normalized.replace(old,new);ast.parse(changed)
    assert changed.replace(new,old)==normalized
    planned[name]=(raw,original,changed.replace('\n',newline).encode())
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
receipt={'base':base,'coordination':'Backend explicitly confirmed no active photo/test/SQL window and reserved these two files for ROOT.',
 'commit':'Deferred to complete backend32 snapshot; no incomplete standalone import commit.',
 'sources':{}}
for name,(before,original,after) in planned.items():
    stem=name.replace('/','__')
    (out/(stem+'.before.RAW.py')).write_bytes(before)
    (out/(stem+'.before.GitLF.py')).write_bytes(original)
    (root/name).write_bytes(after);assert (root/name).read_bytes()==after
    (out/(stem+'.after.RAW.py')).write_bytes(after)
    receipt['sources'][name]={'before_RAW_sha256':hashlib.sha256(before).hexdigest(),
     'before_GitLF_sha256':hashlib.sha256(original).hexdigest(),'after_RAW_sha256':hashlib.sha256(after).hexdigest(),
     'after_GitLF_sha256':hashlib.sha256(after.replace(b'\r\n',b'\n')).hexdigest(),'full_inverse_exact_GitLF':True}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps({'mounted':paths,'router':'web.routes.personal_progress','prefix':'/api','scope':'Source wiring only; no HTTP/DDL/acceptance claim','proof':str(out)}))
