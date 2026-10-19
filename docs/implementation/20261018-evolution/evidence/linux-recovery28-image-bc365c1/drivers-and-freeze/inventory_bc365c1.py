from pathlib import Path
import hashlib,importlib.util,json,re,shlex,subprocess,sys

sys.dont_write_bytecode=True
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=LAB/'evidence/recovery28-image-bc365c1'
HEAD='bc365c13b9af9e24129a56b4068059a67bb3afa0'
TAG='metodobase-lab:recovery28-bc365c1'
assert json.loads((OUT/'build-summary.json').read_text())['build_exit']==0
spec=importlib.util.spec_from_file_location('guest_access',LAB/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
inner='''import importlib.metadata as metadata
import hashlib,json,os,pathlib,platform,pyexpat,re,ssl,subprocess,sys
check=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True)
status=dict(line.split(':',1) for line in open('/proc/self/status') if ':' in line)
packages=sorted([{'name':p.metadata['Name'],'version':p.version} for p in metadata.distributions()],key=lambda p:p['name'].lower())
canonical=lambda name:re.sub(r'[-_.]+','-',name).lower()
assert len(packages)==len({canonical(p['name']) for p in packages})==55
pip_records=[{'name':p.metadata['Name'],'version':p.version,'path':str(p._path)} for p in metadata.distributions() if canonical(p.metadata['Name'])=='pip']
pip_paths=sorted(str(p) for p in pathlib.Path('/usr/local/lib/python3.12/site-packages').glob('pip*.dist-info'))
import pip
dpkg=subprocess.run(['dpkg-query','-W','-f=${binary:Package}\\t${Version}\\t${Architecture}\\n'],capture_output=True,text=True,check=True)
locks={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [pathlib.Path('/app/requirements_web.lock'),pathlib.Path('/usr/local/share/metodobase/requirements-container-bootstrap.lock')] if p.is_file()}
value={'python':platform.python_version(),'platform':platform.platform(),'machine':platform.machine(),'uid':os.getuid(),'gid':os.getgid(),
 'cap_eff':status['CapEff'].strip(),'no_new_privs':status['NoNewPrivs'].strip(),
 'pip_check_exit':check.returncode,'pip_check_output':check.stdout.strip(),'packages':packages,
 'pip_import_version':pip.__version__,'pip_metadata_records':pip_records,'pip_dist_info_paths':pip_paths,
 'os_release':pathlib.Path('/etc/os-release').read_text(),'debian_version':pathlib.Path('/etc/debian_version').read_text().strip(),
 'openssl':ssl.OPENSSL_VERSION,'expat':pyexpat.EXPAT_VERSION,'dpkg_query':dpkg.stdout,'installed_lock_hashes':locks}
print(json.dumps(value))
assert value['python']=='3.12.15' and value['machine']=='x86_64' and value['uid']==999
assert value['cap_eff']=='0000000000000000' and value['no_new_privs']=='1' and check.returncode==0
assert pip.__version__=='26.2.1' and len(pip_records)==1 and pip_records[0]['version']=='26.2.1'
assert pip_paths==['/usr/local/lib/python3.12/site-packages/pip-26.2.1.dist-info']
'''
remote='''import json,subprocess
def docker(*args):return subprocess.run(['sudo','-n','env','DOCKER_HOST=unix:///var/run/docker.sock','docker',*args],capture_output=True,text=True,check=True).stdout
image=json.loads(docker('image','inspect',TAG))[0]
assert image['Architecture']=='amd64' and image['Os']=='linux'
assert image['Config']['Labels']['org.opencontainers.image.revision']==HEAD
assert not image['Config'].get('Entrypoint')
identity=docker('create','--name','metodobase-r28-inventory-bc365c1','--network','none','--read-only','--cap-drop','ALL',
 '--security-opt','no-new-privileges','--no-healthcheck',TAG,'python','-B','-c',INNER).strip()
try:
 container=json.loads(docker('inspect',identity))[0];host=container['HostConfig']
 assert container['Image']==image['Id'] and host['NetworkMode']=='none' and host['ReadonlyRootfs'] and host['CapDrop']==['ALL']
 result=json.loads(docker('start','--attach',identity))
 final=json.loads(docker('inspect',identity))[0];assert final['State']['ExitCode']==0
 value={'image_id':image['Id'],'image_size':image['Size'],'image_user':image['Config']['User'],
 'image_source_labels':image['Config']['Labels'],'image_cmd':image['Config']['Cmd'],'image_architecture':image['Architecture'],'image_os':image['Os'],
 'container_id':identity,'network_mode':host['NetworkMode'],'readonly_rootfs':host['ReadonlyRootfs'],'cap_drop':host['CapDrop'],
 'security_opt':host['SecurityOpt'],'container_exit':final['State']['ExitCode'],'runtime_inventory':result}
 print(json.dumps(value))
finally:docker('rm',identity)
'''.replace('TAG',repr(TAG)).replace('HEAD',repr(HEAD)).replace('INNER',repr(inner))
compile(inner,'inner-inventory','exec');compile(remote,'remote-inventory','exec')
result=access.run('/opt/metodobase-lab/python/bin/python3.12 -c '+shlex.quote(remote),timeout=240)
(OUT/'inventory.log').write_bytes(result.stdout+result.stderr)
assert result.returncode==0,result.stderr
value=json.loads(result.stdout)
(OUT/'runtime-inventory.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
old=json.loads((LAB/'evidence/recovery28-image-92615d7/runtime-inventory.json').read_text())
canonical=lambda name:re.sub(r'[-_.]+','-',name).lower()
before={canonical(p['name']):p['version'] for p in old['runtime_inventory']['packages']}
after={canonical(p['name']):p['version'] for p in value['runtime_inventory']['packages']}
assert len(before)==len(after)==55 and before['pip']=='25.0.1' and after['pip']=='26.2.1'
assert {k:v for k,v in before.items() if k!='pip'}=={k:v for k,v in after.items() if k!='pip'}
repo=Path(r'F:\MetodoBaseWeb-image-security-20261019')
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()==HEAD and git('status','--porcelain=v1','--untracked-files=all')==b''
app=git('show',HEAD+':requirements_web.lock')
assert app==git('show','23e57e07b49bc0ac94cb66613d0c5fb857941683:requirements_web.lock')
assert app==git('show','92615d74ee3a4bd82333c4606cca7898eb324a88:requirements_web.lock')
bootstrap=git('show',HEAD+':requirements-container-bootstrap.lock')
assert bootstrap==git('show','23e57e07b49bc0ac94cb66613d0c5fb857941683:requirements-container-bootstrap.lock')
assert value['runtime_inventory']['installed_lock_hashes']['/usr/local/share/metodobase/requirements-container-bootstrap.lock']==hashlib.sha256(bootstrap).hexdigest()
def os_map(text):
    return {(name.split(':')[0],arch):version for name,version,arch in [line.split('\t') for line in text.splitlines()]}
prior=json.loads((LAB/'evidence/recovery28-image-abd559a-final/runtime-inventory.json').read_text())
prior_os=os_map(prior['runtime_inventory']['dpkg_query']);actual_os=os_map(value['runtime_inventory']['dpkg_query'])
assert len(prior_os)==len(actual_os)==87 and set(prior_os)==set(actual_os)
changed={name+'|'+arch:{'before':prior_os[(name,arch)],'after':version} for (name,arch),version in actual_os.items() if version!=prior_os[(name,arch)]}
assert changed=={'liblzma5|amd64':{'before':'5.8.1-1+deb13u1','after':'5.8.1-1+deb13u2'}},changed
(OUT/'os-package-change.json').write_text(json.dumps({'packages':87,'changed':changed,'other_86_os_versions_identical':True},indent=2)+'\n',encoding='utf-8')
summary={'source_commit':HEAD,'image_id':value['image_id'],'python':'3.12.15','actual_distributions':55,
 'pip_before':'25.0.1','pip_after':'26.2.1','other_54_distributions_exactly_unchanged':True,
 'only_one_pip_metadata_record':True,'no_pip_25_metadata_remains':True,'app_lock_unchanged_vs_23e_and_926':True,
 'bootstrap_lock_unchanged_vs_23e':True,'app_lock_sha256':hashlib.sha256(app).hexdigest(),
 'bootstrap_lock_sha256':hashlib.sha256(bootstrap).hexdigest(),'container_removed':True,
 'scope':'Runtime metadata and pip check only, overridden CMD and disabled healthcheck. No application startup, PostgreSQL test or OS vulnerability acceptance.'}
(OUT/'inventory-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
