"""Preserve the exact before/after focus regression and isolate its commit."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
root=Path(r'F:\mb-r23-history30-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r23-focus-author-20261019');out.mkdir(exist_ok=False)
git=lambda *args,**kw:subprocess.check_output(['git',*args],cwd=root,**kw)
base=git('rev-parse','HEAD',text=True).strip();assert base=='8d806a7fdcf2fbb1d39a7c91b9afcdbeedd9c10b'
old=git('show',base+':web/static/js/dashboard-seguimiento.js');(out/'before-dashboard.js').write_bytes(old)
rows=[]
for mode in ['before','after']:
    environment=dict(os.environ)
    if mode=='before':environment['FOLLOWUP_FOCUS_SOURCE']=str(out/'before-dashboard.js')
    else:environment.pop('FOLLOWUP_FOCUS_SOURCE',None)
    result=subprocess.run([r'C:\Program Files\nodejs\node.exe','tests/e2e/dashboard_followup_focus.cjs'],cwd=root,env=environment,capture_output=True,check=False)
    (out/(mode+'.json')).write_bytes(result.stdout);(out/(mode+'.stderr.log')).write_bytes(result.stderr)
    value=json.loads(result.stdout);rows.append({'mode':mode,'exit':result.returncode,'passed':value['passed'],'total':value['total']})
assert rows==[{'mode':'before','exit':1,'passed':3,'total':4},{'mode':'after','exit':0,'passed':4,'total':4}]
ev=root/'docs/implementation/20261018-evolution/evidence/r23-focus-author-20261019';ev.mkdir(exist_ok=False);(ev/'.gitattributes').write_bytes(b'* -text\n')
for path in out.iterdir():shutil.copyfile(path,ev/path.name)
shutil.copyfile(__file__,ev/'driver.py')
sha=lambda value:hashlib.sha256(value).hexdigest()
sources=['web/static/js/dashboard-seguimiento.js','tests/e2e/dashboard_followup_focus.cjs','docs/implementation/20261018-evolution/R23_FOCO.md']
freeze={'base':base,'scope':'Only the focus fix, unchanged native disabled/session fences and four controlled DOM regressions. No browser or PG claimed. Independent original768 replay pending.','results':rows,'sources':{name:{'raw_sha256':sha((root/name).read_bytes()),'git_lf_sha256':sha((root/name).read_bytes().replace(b'\r\n',b'\n'))} for name in sources},'files':{path.name:{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())} for path in ev.iterdir() if path.is_file()}}
(ev/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n',encoding='utf8')
raw=[path.relative_to(root).as_posix() for path in ev.iterdir() if path.is_file()]
subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*raw],cwd=root,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*raw],cwd=root,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=true','add','--',*sources],cwd=root,check=True,capture_output=True)
changed=set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]);assert changed==set(raw+sources)
for name in raw+sources:
    expected=(root/name).read_bytes();expected=expected if name in raw else expected.replace(b'\r\n',b'\n')
    assert git('show',':'+name)==expected,name
subprocess.run(['git','commit','-m','Retain refresh focus without stealing user navigation or expired session focus'],cwd=root,check=True,stdout=subprocess.DEVNULL)
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'freeze_sha256':sha((ev/'freeze.json').read_bytes()),'results':rows,'uncommitted_CI_preparation_excluded':True}))
