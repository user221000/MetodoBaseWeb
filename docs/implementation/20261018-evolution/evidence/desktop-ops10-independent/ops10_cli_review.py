"""Validate a coherent synthetic old bundle via the actual safe CLI default."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(r"F:\MetodoBaseWeb-desktop-20261019")
OUT=Path(__file__).resolve().parent
allowed={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TMP','TEMP','LANG','LC_ALL'}
env={key:value for key,value in os.environ.items() if key.upper() in allowed}
env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
checks=[]
for name,forbidden in [('positive',None),('forbidden-exact','_internal/assets/design-reference.png'),('forbidden-casefold','_INTERNAL/ASSETS/DESIGN-REFERENCE.PNG')]:
    bundle=OUT/name/'MetodoBase'
    files={'MetodoBase.exe':b'Inert bytes. Never execute this file.',
        '_internal/fonts/Inter/Inter-Regular.ttf':b'font',
        '_internal/ui_desktop/pyside/styles/amarillo_neon.qss':b'QWidget {}',
        '_internal/PySide6/plugins/platforms/qwindows.dll':b'plugin',
        '_internal/PySide6/plugins/platforms/qoffscreen.dll':b'plugin',
        '_internal/assets/examples/design-reference.png':b'allowed other exact path',
        '_internal/assets/design-reference-v2.png':b'allowed other exact basename'}
    if forbidden:files[forbidden]=b'Synthetic unapproved reference, no real names/emails'
    for relative,value in files.items():
        path=bundle/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
    # Build a coherent manifest without calling the newly hardened writer.
    mapping={path.relative_to(bundle).as_posix():{'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for path in bundle.rglob('*') if path.is_file()}
    (bundle/'build-manifest.json').write_text(json.dumps({'schema':1,'platform':'win32','files':mapping}),encoding='utf8')
    photo=lambda:{p.relative_to(bundle).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.rglob('*') if p.is_file()}
    before=photo()
    result=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'validate_build.py'),'--bundle',str(bundle)],cwd=OUT,env=env,capture_output=True,text=True,timeout=10)
    if forbidden:
        assert result.returncode==1
        assert result.stderr.strip()=='Private data or unsafe name in bundle'
    else:
        assert result.returncode==0,result.stderr
        assert json.loads(result.stdout)=={'gui_executed':False,'manifest_verified':True}
    assert photo()==before
    checks.append({'case':name,'exit':result.returncode,'matched':True,'bundleUnchanged':True})
report={'scope':'Actual validate_build.py CLI with inert synthetic files and coherent forged old-contract manifest; no GUI flag, no build/compiler/provider. Original reference pixels never copied/read into output.','checks':checks}
(OUT/'ops10-cli-independent.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('CLI',len(checks),'all matched; no GUI requested')
