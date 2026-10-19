"""Source-only PWA readiness inventory; never inspect browser/private stores."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018');OUT=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r35-readiness-20261019');OUT.mkdir(exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a,**k:subprocess.check_output(['git',*a],cwd=ROOT,**k)
names=git('ls-files','-z','--','web').decode().split('\0')[:-1]
patterns={'registration':r'serviceWorker\s*\.\s*register','install_prompt':r'beforeinstallprompt','cache_open':r'caches\s*\.\s*open','manifest_link':r'rel\s*=\s*[\x22\x27]manifest[\x22\x27]'}
before={name:sha((ROOT/name).read_bytes()) for name in names};hits=[]
for name in names:
    if Path(name).suffix not in {'.py','.js','.cjs','.css','.html','.json','.webmanifest'}:continue
    text=(ROOT/name).read_text(encoding='utf-8-sig')
    for label,pattern in patterns.items():
        for match in re.finditer(pattern,text,re.I):hits.append({'file':name,'line':text.count('\n',0,match.start())+1,'pattern':label})
manifests=[name for name in names if name.endswith('.webmanifest') or Path(name).name=='manifest.json']
after={name:sha((ROOT/name).read_bytes()) for name in names};assert before==after
data={'head':git('rev-parse','HEAD',text=True).strip(),'files':before,'file_count':len(names),'source_stable':True,'patterns':patterns,'hits':hits,'manifest_candidates':manifests,'scope':'Source-only search of tracked maintained web tree with listed literal patterns; no live browser, installed-app or remote/CDN source inspection and no claim that user/browser has no registrations.'}
(OUT/'source-inventory.json').write_bytes((json.dumps(data,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in data.items() if k!='files'}))
