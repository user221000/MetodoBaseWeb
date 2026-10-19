from pathlib import Path
import importlib.util,json,shlex,sys

sys.dont_write_bytecode=True
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=LAB/'evidence/os-audit-abd559a/apt-metadata-probe';OUT.mkdir(exist_ok=False)
image=json.loads((LAB/'evidence/recovery28-image-abd559a-final/runtime-inventory.json').read_text())['image_id']
inner='''from pathlib import Path
import hashlib,json,os,subprocess,sys
sources="""Types: deb
URIs: https://deb.debian.org/debian
Suites: trixie trixie-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

Types: deb
URIs: https://security.debian.org/debian-security
Suites: trixie-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
"""
path=Path('/tmp/metodobase.sources');path.write_text(sources)
options=['-o','Dir::Etc::sourcelist='+str(path),'-o','Dir::Etc::sourceparts=-','-o','APT::Sandbox::User=root',
 '-o','Acquire::AllowInsecureRepositories=false','-o','Acquire::AllowDowngradeToInsecureRepositories=false','-o','APT::Get::AllowUnauthenticated=false']
record={'source_definition':sources,'keyring_sha256':hashlib.sha256(Path('/usr/share/keyrings/debian-archive-keyring.gpg').read_bytes()).hexdigest(),'commands':{}}
def run(label,args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=240,cwd='/tmp');record['commands'][label]={'command':args,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr};assert p.returncode==0,(label,p.stderr);return p.stdout
run('update',['apt-get',*options,'-o','Debug::Acquire::gpgv=true','update'])
run('policy',['apt-cache',*options,'policy','liblzma5'])
metadata=run('show-exact',['apt-cache',*options,'show','liblzma5=5.8.1-1+deb13u2'])
run('simulate',['apt-get',*options,'--simulate','--only-upgrade','--no-install-recommends','install','liblzma5=5.8.1-1+deb13u2'])
run('download',['apt-get',*options,'download','liblzma5=5.8.1-1+deb13u2'])
debs=list(Path('/tmp').glob('*.deb'));assert len(debs)==1
package=debs[0];digest=hashlib.sha256(package.read_bytes()).hexdigest()
assert 'SHA256: '+digest in metadata and 'Version: 5.8.1-1+deb13u2' in metadata
record['package']={'name':package.name,'bytes':package.stat().st_size,'sha256':digest,'metadata_sha_matches_download':True}
record['inrelease']={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'content':p.read_text()} for p in Path('/var/lib/apt/lists').glob('*InRelease')}
record['apt_list_hashes']={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in Path('/var/lib/apt/lists').iterdir() if p.is_file() and p.name!='lock'}
record['scope']='Throwaway metadata/download probe only; no package installation, no app startup, no product image mutation.'
print(json.dumps(record))
'''
remote='''import json,subprocess
def docker(*args):return subprocess.run(['sudo','-n','env','DOCKER_HOST=unix:///var/run/docker.sock','docker',*args],capture_output=True,text=True,check=True).stdout
assert not docker('ps','-q').strip()
identity=docker('create','--name','metodobase-liblzma-metadata-abd559a','--user','0','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--no-healthcheck',
 '--tmpfs','/tmp:rw,nosuid,nodev,size=32m','--tmpfs','/var/lib/apt/lists:rw,nosuid,nodev,size=256m','--tmpfs','/var/cache/apt:rw,nosuid,nodev,size=32m',IMAGE,'python','-B','-c',INNER).strip()
try:
 output=docker('start','--attach',identity);value=json.loads(output)
 final=json.loads(docker('inspect',identity))[0];assert final['State']['ExitCode']==0
 value.update(image_id=IMAGE,container_id=identity,container_exit=final['State']['ExitCode'],container_removed=True)
 print(json.dumps(value))
finally:docker('rm','--force',identity)
'''.replace('IMAGE',repr(image)).replace('INNER',repr(inner))
compile(inner,'apt-probe-inner','exec');compile(remote,'apt-probe-remote','exec')
spec=importlib.util.spec_from_file_location('guest_access',LAB/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
result=access.run('/opt/metodobase-lab/python/bin/python3.12 -c '+shlex.quote(remote),timeout=900)
(OUT/'probe.log').write_bytes(result.stdout+result.stderr)
assert result.returncode==0,result.stderr
record=json.loads(result.stdout);(OUT/'apt-metadata.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exit':result.returncode,'image_id':image,'package':record['package'],'container_removed':record['container_removed']}))
