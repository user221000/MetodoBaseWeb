from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,shlex,time

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=LAB/'evidence/python31215-base-preload-abd559a';OUT.mkdir(exist_ok=False)
PROVENANCE=LAB/'evidence/image-pip-base-primary-20261019/python31215-registry-provenance.json'
source=json.loads(PROVENANCE.read_text())
reference='python:3.12.15-slim@'+source['linux_amd64_manifest_digest']
spec=importlib.util.spec_from_file_location('guest_access',LAB/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
before=access.run('sudo docker ps --format "{{.ID}} {{.Names}}"',timeout=30)
(OUT/'before.log').write_bytes(before.stdout+before.stderr)
assert before.returncode==0 and not before.stdout.strip(),'Another running container detected'
started=time.monotonic();pull=access.run('sudo docker pull --platform=linux/amd64 '+shlex.quote(reference),timeout=1200)
(OUT/'pull.log').write_bytes(pull.stdout+pull.stderr)
assert pull.returncode==0,pull.returncode
inner='''import importlib.metadata as m,json,platform,ssl,sys,pyexpat
print(json.dumps({'python':platform.python_version(),'machine':platform.machine(),'openssl':ssl.OPENSSL_VERSION,
 'expat':pyexpat.EXPAT_VERSION,'pip':m.version('pip'),'os_release':open('/etc/os-release').read(),
 'packages':sorted([{'name':p.metadata['Name'],'version':p.version} for p in m.distributions()],key=lambda p:p['name'].lower())}))
'''
remote='''import json,subprocess
reference=REFERENCE
def docker(*args):return subprocess.check_output(['sudo','docker',*args],text=True)
image=json.loads(docker('image','inspect',reference))[0]
assert image['Os']=='linux' and image['Architecture']=='amd64' and image['Id']==EXPECTED_CONFIG
container=docker('create','--name','metodobase-base31215-inventory-abd559a','--network','none','--read-only',
 '--cap-drop','ALL','--security-opt','no-new-privileges',reference,'python','-c',INNER).strip()
try:
 raw=docker('start','--attach',container)
 state=json.loads(docker('inspect',container))[0]
 assert state['State']['ExitCode']==0
 observed=json.loads(raw);assert observed['python']=='3.12.15' and observed['machine']=='x86_64'
 os_packages=docker('run','--rm','--name','metodobase-base31215-dpkg-abd559a','--network','none','--read-only',
  '--cap-drop','ALL','--security-opt','no-new-privileges',reference,'dpkg-query','-W','-f=${binary:Package} ${Version}\\n')
 print(json.dumps({'reference':reference,'image_id':image['Id'],'repo_digests':image['RepoDigests'],'size':image['Size'],
  'platform':image['Os']+'/'+image['Architecture'],'runtime':observed,'os_package_inventory':os_packages,
  'container_id':container,'container_exit':state['State']['ExitCode'],'network':'none','rootfs_readonly':True,'cap_drop':['ALL'],'no_new_privileges':True}))
finally:docker('rm',container)
'''.replace('REFERENCE',repr(reference)).replace('EXPECTED_CONFIG',repr(source['config_digest'])).replace('INNER',repr(inner))
inventory=access.run('/opt/metodobase-lab/python/bin/python3.12 -c '+shlex.quote(remote),timeout=180)
(OUT/'inventory.log').write_bytes(inventory.stdout+inventory.stderr);assert inventory.returncode==0
observed=json.loads(inventory.stdout)
(OUT/'base-runtime-inventory.json').write_text(json.dumps(observed,indent=2)+'\n',encoding='utf-8')
report={'captured_utc':datetime.now(timezone.utc).isoformat(),'reference':reference,'pull_exit':pull.returncode,
        'inventory_exit':inventory.returncode,'runtime_python':observed['runtime']['python'],'image_id':observed['image_id'],
        'seconds':round(time.monotonic()-started,3),'scope':'Exact official Linux/amd64 base preload and metadata-only containers. No product code or application startup.'}
(OUT/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
