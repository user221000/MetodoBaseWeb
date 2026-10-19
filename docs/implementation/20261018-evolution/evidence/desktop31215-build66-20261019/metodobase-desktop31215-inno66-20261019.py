import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

temp=Path('C:/Users/Consu/AppData/Local/Temp')
source=Path('F:/mb-d31215-20261019')
main=Path('F:/MetodoBaseWeb-execution-20261018')
out=temp/'metodobase-desktop31215-build66-20261019/inno'
out.mkdir(exist_ok=False)
compiled=out/'compiled';compiled.mkdir()
toolroot=Path(json.loads((temp/'metodobase-inno673-current-20261019.json').read_text(encoding='utf-8'))['directory'])
compiler=toolroot/'compiler/ISCC.exe'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
prior=json.loads((main/'docs/implementation/20261018-evolution/evidence/desktop-inno673-compile7bde-source.json').read_text(encoding='utf-8'))
assert sha(compiler.read_bytes())==prior['tools']['ISCC.exe']
download=json.loads((toolroot/'download-proof.json').read_text(encoding='utf-8'))
assert sha((toolroot/'innosetup-6.7.3.exe').read_bytes())==download['sha256']
spec=importlib.util.spec_from_file_location('frozen_desktop_build66',source/'build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
commit='66d9dec0e15dd873038bd248d3883daeeb27d4ca'
before=build.source_snapshot(commit)
bundle=source/'dist/MetodoBase'
manifest=build.verify_manifest(bundle)
assert manifest['source_commit']==commit
inputs=source/'dist/installer-inputs'
inventory=lambda directory:{p.relative_to(directory).as_posix():sha(p.read_bytes()) for p in directory.rglob('*') if p.is_file()}
bundle_before=inventory(bundle);inputs_before=inventory(inputs);tools_before=inventory(toolroot/'compiler')
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TMP','TEMP','NUMBER_OF_PROCESSORS'}}
profile=out/'private-profile'
env.update(USERPROFILE=str(profile/'home'),APPDATA=str(profile/'appdata'),LOCALAPPDATA=str(profile/'localappdata'))
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
command=[str(compiler),'/Q','/O'+str(compiled),str(inputs/'installer-entry.iss')]
clock=time.monotonic()
with (out/'compile.log').open('xb') as stream:
    result=subprocess.run(command,cwd=source,env=env,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW,stdout=stream,stderr=subprocess.STDOUT,timeout=360)
after=build.source_snapshot(commit)
bundle_after=inventory(bundle);inputs_after=inventory(inputs);tools_after=inventory(toolroot/'compiler')
outputs=[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'PE_magic':p.read_bytes()[:2]==b'MZ'} for p in compiled.iterdir() if p.is_file()]
summary={'source_commit':commit,'compiler_version':'6.7.3','compiler_sha256':sha(compiler.read_bytes()),'official_installer_sha256':download['sha256'],'original_installer_signature':'Valid Pyrsys B.V. per retained pinned provenance; installer bytes rehashed, no new signature execution claimed','command':command,'exit':result.returncode,'seconds':round(time.monotonic()-clock,3),'outputs':outputs,'source_count':len(before),'sources_stable':before==after,'bundle_files':len(bundle_before),'bundle_stable':bundle_before==bundle_after,'inputs_stable':inputs_before==inputs_after,'tools_stable':tools_before==tools_after,'tool_files':len(tools_before),'tool_inventory_sha256':sha(json.dumps(tools_before,sort_keys=True,separators=(',',':')).encode()),'scope':'Actual Inno compilation for CPython3.12.15 desktop bundle, isolated compiler profile and hidden process. No Setup execution, install/upgrade/uninstall, signing, OS network isolation or independent payload review yet.'}
(out/'inventories-private.json').write_text(json.dumps({'bundle_before':bundle_before,'bundle_after':bundle_after,'inputs_before':inputs_before,'inputs_after':inputs_after,'tools_before':tools_before,'tools_after':tools_after},indent=2)+'\n',encoding='utf-8')
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary),flush=True)
assert result.returncode==0 and len(outputs)==1 and outputs[0]['PE_magic']
assert before==after and bundle_before==bundle_after and inputs_before==inputs_after and tools_before==tools_after
