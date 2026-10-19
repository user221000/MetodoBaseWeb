from pathlib import Path
import importlib.util,json,shlex,subprocess,sys

sys.dont_write_bytecode=True
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019');OUT=LAB/'evidence/os-audit-abd559a/component-applicability-v2';OUT.mkdir(exist_ok=False)
image=json.loads((LAB/'evidence/recovery28-image-abd559a-final/runtime-inventory.json').read_text())['image_id']
inner='''from pathlib import Path
import ctypes,gzip,hashlib,json,os,platform,sqlite3,stat,subprocess,sys,_lzma
names=['/usr/bin/mount','/usr/bin/nsenter','/usr/bin/infocmp','/usr/lib/systemd/systemd-homed','/usr/lib/systemd/systemd-oomd',
 '/usr/lib/systemd/systemd-journald','/usr/bin/systemd-tmpfiles','/usr/bin/getfacl','/usr/bin/setfacl','/usr/bin/chacl','/usr/bin/getfattr',
 '/usr/bin/setfattr','/usr/bin/bzip2recover','/usr/bin/apt-key','/usr/bin/login','/usr/bin/chfn','/usr/bin/chsh','/usr/bin/su',
 '/usr/bin/newuidmap','/usr/sbin/init','/usr/sbin/sulogin','/usr/bin/tar','/usr/sbin/rmt']
paths={}
for name in names:
 p=Path(name);paths[name]={'exists':p.exists(),'symlink':p.is_symlink()}
 if p.exists():paths[name].update(mode=oct(stat.S_IMODE(p.stat().st_mode)),resolved=str(p.resolve()))
perl=subprocess.run(['perl','-e','print join("\\n",@INC)'],capture_output=True,text=True,check=True)
perl_modules={name:[str(Path(base)/name) for base in perl.stdout.splitlines() if (Path(base)/name).is_file()] for name in ['Archive/Tar.pm','File/Temp.pm','Pod/Text.pm']}
ldd=subprocess.run(['ldd',_lzma.__file__],capture_output=True,text=True,check=True)
connection=sqlite3.connect(':memory:');options=sorted(p[0] for p in connection.execute('pragma compile_options'));connection.close()
sqlite=ctypes.CDLL('libsqlite3.so.0');symbols={name:hasattr(sqlite,name) for name in ['sqlite3changeset_apply_v3','sqlite3changeset_apply_v2','sqlite3changegroup_add','sqlite3_zipfile_init']}
changelog=Path('/usr/share/doc/libssl3t64/changelog.Debian.gz')
openssl_changes=gzip.decompress(changelog.read_bytes()).decode('utf-8') if changelog.is_file() else 'Not present in slim image; package-installed file list is not a physical presence guarantee.'
record={'python':platform.python_version(),'kernel':platform.release(),'uid':os.getuid(),'paths':paths,
 'fstab':Path('/etc/fstab').read_text(),'perl_inc':perl.stdout.splitlines(),'perl_modules':perl_modules,
 'lzma_extension':_lzma.__file__,'lzma_extension_linkage':ldd.stdout,'sqlite_runtime_version':sqlite3.sqlite_version,
 'sqlite_compile_options':options,'sqlite_exported_symbols':symbols,'openssl_debian_changelog_first_30000_chars':openssl_changes[:30000],
 'openssl_changelog_compressed_sha256':hashlib.sha256(changelog.read_bytes()).hexdigest() if changelog.is_file() else None,
 'scope':'Read-only component/metadata probe, SQLite in-memory compile-options query only. No application or PostgreSQL startup; no malformed inputs or exploit execution. Absence of a component is evidence for review, not an automatic exception.'}
print(json.dumps(record))
'''
remote='''import json,subprocess
def docker(*args):
 p=subprocess.run(['sudo','-n','env','DOCKER_HOST=unix:///var/run/docker.sock','docker',*args],capture_output=True,text=True)
 assert p.returncode==0,{'command':args,'stdout':p.stdout,'stderr':p.stderr}
 return p.stdout
assert not docker('ps','-q').strip()
identity=docker('create','--name','metodobase-component-metadata-abd559a','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--no-healthcheck',IMAGE,'python','-B','-c',INNER).strip()
try:
 result=json.loads(docker('start','--attach',identity));final=json.loads(docker('inspect',identity))[0];assert final['State']['ExitCode']==0
 result.update(image_id=IMAGE,container_exit=0,container_removed=True);print(json.dumps(result))
finally:docker('rm','--force',identity)
'''.replace('IMAGE',repr(image)).replace('INNER',repr(inner))
compile(inner,'component-metadata-inner','exec');compile(remote,'component-metadata-remote','exec')
spec=importlib.util.spec_from_file_location('guest_access',LAB/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
result=access.run('/opt/metodobase-lab/python/bin/python3.12 -c '+shlex.quote(remote),timeout=240)
(OUT/'probe.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0,result.stderr
record=json.loads(result.stdout);(OUT/'component-metadata.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
repo=Path(r'F:\MetodoBaseWeb-image-pip-20261019')
command=['rg','-n','-i','--glob','*.py','--glob','*.sh','lzma|archive::tar|infocmp|systemd-homed|nsenter|X-mount|acl_get_file|acl_set_file|\\bmount\\b','config','core','src','api','web','utils','entrypoint.sh','db_bootstrap.py']
search=subprocess.run(command,cwd=repo,capture_output=True,text=True);assert search.returncode in (0,1)
(OUT/'application-source-search.json').write_text(json.dumps({'source_commit':'abd559a9ea3227e6c3bdb141241c11f7196c7682','command':command,'exit':search.returncode,'stdout':search.stdout,'stderr':search.stderr,'interpretation':'Only FastAPI static mount() and a documentation word matched. No direct calls to the queried OS/XZ components found in these application paths. Transitive/native/operational reachability remains unproven.'},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'image_id':image,'component_probe_exit':0,'container_removed':True,'paths':len(record['paths']),'perl_modules':record['perl_modules'],'sqlite_runtime_version':record['sqlite_runtime_version']}))
