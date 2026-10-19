from pathlib import Path
import hashlib,json,sys
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
RUN=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-expat-m2-native-validation-20261019')
PROOF=Path(r'F:\mb-container-apt-refresh-sec10-20261019/docs/implementation/20261018-evolution/evidence/apt-metadata-sec10-refresh-20261019')
sys.path.insert(0,str(LAB/'scripts'))
import guest_access
remote="""python3 - <<'PY'
import hashlib,io,json,subprocess,tarfile,shutil
from pathlib import Path
reference='python:3.12.15-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe'
name='metodobase-expat-keyring-base-proof-20261019'
def run(*args):return subprocess.check_output(args)
base=json.loads(run('sudo','-n','docker','image','inspect',reference))[0]
assert any(item.endswith('@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe') for item in base['RepoDigests'])
created=run('sudo','-n','docker','create','--name',name,'--network','none','--read-only','--cap-drop','ALL',reference,'/bin/true').decode().strip()
inspected=json.loads(run('sudo','-n','docker','inspect',created))[0]
assert inspected['State']['Status']=='created' and not inspected['State']['Running'] and inspected['Image']==base['Id']
def copy(path):
 raw=run('sudo','-n','docker','cp',created+':'+path,'-')
 with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
  entries=tar.getmembers();assert len(entries)==1
  member=entries[0]
  if member.issym():
   assert path=='/usr/share/keyrings/debian-archive-keyring.gpg' and member.linkname=='debian-archive-keyring.pgp'
   return copy('/usr/share/keyrings/debian-archive-keyring.pgp')
  assert member.isfile() and member.size<200000
  return tar.extractfile(member).read()
key=copy('/usr/share/keyrings/debian-archive-keyring.gpg')
assert hashlib.sha256(key).hexdigest()=='506b815cbb32d9b6066b4a2aa524071e071761e7e7f68c3ac74f3061ba852017'
assert key==Path('/var/tmp/metodobase-expat-m2-native-20261019/apt-failure-v2/debian-archive-keyring.gpg').read_bytes()
failed=json.loads(run('sudo','-n','docker','inspect','7cbc85823cba'))[0]
failedimage=json.loads(run('sudo','-n','docker','image','inspect',failed['Image']))[0]
assert failedimage['RootFS']['Layers'][:len(base['RootFS']['Layers'])]==base['RootFS']['Layers']
assert not failed['State']['Running'] and failed['State']['ExitCode']==1
gpgv=Path(shutil.which('gpgv'))
record={'immutable_base_reference':reference,'immutable_base_image_id':base['Id'],'repo_digests':base['RepoDigests'],
'base_layers':base['RootFS']['Layers'],'keyring_resolved_path':'/usr/share/keyrings/debian-archive-keyring.pgp',
'keyring_alias':'/usr/share/keyrings/debian-archive-keyring.gpg','keyring_bytes':len(key),'keyring_sha256':hashlib.sha256(key).hexdigest(),
'keyring_identical_to_failed_container':True,'base_proof_container_id':created,'base_proof_container_never_started':True,
'failed_container_id':failed['Id'],'failed_container_state':{k:failed['State'][k] for k in ('Running','ExitCode','StartedAt','FinishedAt')},
'failed_container_inspect_sha256':hashlib.sha256(json.dumps(failed,sort_keys=True).encode()).hexdigest(),'failed_image_id':failed['Image'],
'failed_image_extends_pinned_base_layers':True,'gpgv_path':str(gpgv),'gpgv_sha256':hashlib.sha256(gpgv.read_bytes()).hexdigest(),
'gpgv_version':run(str(gpgv),'--version').decode().splitlines()[0],
'gpgv_package':run('dpkg-query','-W','-f=$'+'{Version}','gpgv').decode(),'no_keyserver_or_global_keyring_used':True,'no_build_retry':True}
print(json.dumps(record))
PY
"""
r=guest_access.run(remote,timeout=60)
(RUN/'base-keyring-attestation-raw.log').write_bytes(r.stdout+b'\nSTDERR\n'+r.stderr)
assert r.returncode==0,r.stderr.decode()
(PROOF/'base-keyring-receipt-source.json').write_bytes(r.stdout)
(PROOF/'base-dpkg-invariance-source.json').write_bytes((RUN/'base-dpkg-invariance-source.json').read_bytes())
print(json.dumps({k:v for k,v in json.loads(r.stdout).items() if k not in ('base_layers','repo_digests')}))

