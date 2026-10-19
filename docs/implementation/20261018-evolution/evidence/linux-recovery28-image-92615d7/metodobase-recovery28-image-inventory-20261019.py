import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import sys

sys.dont_write_bytecode=True
lab=Path('F:/MetodoBaseWeb-linux-lab-20261019')
out=lab/'evidence/recovery28-image-92615d7'
assert json.loads((out/'build-summary.json').read_text())['build_exit']==0
spec=importlib.util.spec_from_file_location('guest_access',lab/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)
inner='''import importlib.metadata as metadata
import json,os,platform,subprocess,sys
check=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True)
status=dict(line.split(':',1) for line in open('/proc/self/status') if ':' in line)
value={'python':platform.python_version(),'platform':platform.platform(),'uid':os.getuid(),'gid':os.getgid(),
       'cap_eff':status['CapEff'].strip(),'no_new_privs':status['NoNewPrivs'].strip(),
       'pip_check_exit':check.returncode,'pip_check_output':check.stdout.strip(),
       'packages':sorted([{'name':p.metadata['Name'],'version':p.version} for p in metadata.distributions()],key=lambda p:p['name'].lower())}
print(json.dumps(value))
assert value['python']=='3.12.13' and value['uid']!=0 and value['cap_eff']=='0000000000000000' and value['no_new_privs']=='1'
assert check.returncode==0
'''
remote='''import json,subprocess
tag='metodobase-lab:recovery28-92615d7'
def docker(*args):
 return subprocess.run(['sudo','docker',*args],capture_output=True,text=True,check=True).stdout
image=json.loads(docker('image','inspect',tag))[0]
identity=docker('create','--name','metodobase-r28-inventory-20261019','--network','none','--read-only',
                '--cap-drop','ALL','--security-opt','no-new-privileges',tag,'python','-c',INNER).strip()
try:
 container=json.loads(docker('inspect',identity))[0]
 assert container['Image']==image['Id']
 host=container['HostConfig']
 assert host['NetworkMode']=='none' and host['ReadonlyRootfs'] and host['CapDrop']==['ALL']
 result=json.loads(docker('start','--attach',identity))
 final=json.loads(docker('inspect',identity))[0]
 assert final['State']['ExitCode']==0
 value={'image_id':image['Id'],'image_size':image['Size'],'image_user':image['Config']['User'],
        'image_source_labels':image['Config']['Labels'],'image_cmd':image['Config']['Cmd'],
        'container_id':identity,'network_mode':host['NetworkMode'],'readonly_rootfs':host['ReadonlyRootfs'],
        'cap_drop':host['CapDrop'],'security_opt':host['SecurityOpt'],'container_exit':final['State']['ExitCode'],
        'runtime_inventory':result}
 print(json.dumps(value))
finally:
 docker('rm',identity)
'''.replace('INNER',repr(inner))
result=access.run('/opt/metodobase-lab/python/bin/python3.12 -c '+shlex.quote(remote),timeout=180)
(out/'inventory.log').write_bytes(result.stdout+result.stderr)
assert result.returncode==0
value=json.loads(result.stdout)
(out/'runtime-inventory.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exit':result.returncode,'image_id':value['image_id'],'python':value['runtime_inventory']['python'],
                 'uid':value['runtime_inventory']['uid'],'pip_check_exit':value['runtime_inventory']['pip_check_exit'],
                 'packages':len(value['runtime_inventory']['packages'])}))
