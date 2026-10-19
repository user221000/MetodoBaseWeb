from pathlib import Path
import hashlib,json,re,sys
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-expat-m2-native-validation-20261019')
sys.path.insert(0,str(LAB/'scripts'))
import guest_access,lab_control
assert lab_control.process_identity(lab_control.state())
raw=(OUT/'native-build-raw.log').read_text(encoding='utf-8',errors='replace')
container=re.findall(r'Running in ([0-9a-f]{12,64})',raw)[-1]
assert re.fullmatch('[0-9a-f]{12,64}',container)
remote="""python3 - <<'PY'
from pathlib import Path
import hashlib,io,json,re,subprocess,tarfile,shutil
root=Path('/var/tmp/metodobase-expat-m2-native-20261019')
out=root/'apt-failure-v2';out.mkdir(mode=0o700)
container='"""+container+"""'
def run(*args):return subprocess.check_output(args)
before=json.loads(run('sudo','-n','docker','inspect',container))[0]
assert not before['State']['Running'] and before['State']['ExitCode']==1
def copy(path):
 raw=run('sudo','-n','docker','cp',container+':'+path,'-')
 with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
  members=tar.getmembers();assert len(members)==1
  if members[0].issym():
   assert path=='/usr/share/keyrings/debian-archive-keyring.gpg'
   assert members[0].linkname=='debian-archive-keyring.pgp'
   return copy('/usr/share/keyrings/debian-archive-keyring.pgp')
  assert members[0].isfile()
  assert members[0].size<500000
  return tar.extractfile(members[0]).read()
key=out/'debian-archive-keyring.gpg'
key.write_bytes(copy('/usr/share/keyrings/debian-archive-keyring.gpg'))
home=out/'gpgv-home';home.mkdir(mode=0o700)
lock=root/'context/requirements-container-apt-metadata.lock'
entries=[]
for row in lock.read_text().splitlines():
 if not row or row.startswith('#'):continue
 expected,path=row.split(None,1);path=path.strip()
 assert re.fullmatch('[0-9a-f]{64}',expected) and path.startswith('/var/lib/apt/lists/') and path.endswith('_InRelease')
 data=copy(path);file=out/Path(path).name;file.write_bytes(data)
 actual=hashlib.sha256(data).hexdigest()
 headers={}
 for line in data.decode('utf-8').splitlines():
  if ': ' in line:
   k,v=line.split(': ',1)
   if k in ('Origin','Label','Suite','Codename','Date','Valid-Until'):headers[k]=v
 gpgv=subprocess.run(['gpgv','--homedir',str(home),'--status-fd','1','--keyring',str(key),str(file)],capture_output=True)
 (out/(file.name+'.gpgv.stdout')).write_bytes(gpgv.stdout)
 (out/(file.name+'.gpgv.stderr')).write_bytes(gpgv.stderr)
 fingerprints=re.findall(r'^\\[GNUPG:\\] VALIDSIG ([0-9A-F]+)',gpgv.stdout.decode(),re.M)
 entries.append({'path':path,'bytes':len(data),'expected_sha256':expected,'actual_sha256':actual,'matches_pin':expected==actual,'signed_headers':headers,'gpgv_exit':gpgv.returncode,'validsig_fingerprints':fingerprints})
after=json.loads(run('sudo','-n','docker','inspect',container))[0]
assert before['State']==after['State']
report={'status':'PREIMAGE_APT_INDEX_HASH_DRIFT','failed_container_id':before['Id'],'container_was_not_started_for_diagnostics':True,'state':{k:before['State'][k] for k in ('Running','ExitCode','StartedAt','FinishedAt')},
'keyring_sha256':hashlib.sha256(key.read_bytes()).hexdigest(),'indices':entries,
'docker_images':run('sudo','-n','docker','image','ls','--no-trunc','--format','{{.ID}} {{.Repository}}:{{.Tag}} {{.Size}}').decode(),
'docker_containers':run('sudo','-n','docker','ps','-a','--no-trunc','--format','{{.ID}} {{.Names}} {{.Status}}').decode(),
'image_iid_file_exists':(root/'expat-build.iid').exists(),'target_image_exists':bool(run('sudo','-n','docker','image','ls','-q','metodobase-lab:expat-sec10-m2-7c013f1').strip()),
'disk_free_bytes':shutil.disk_usage('/').free,'locks_changed':False,'retries_to_bypass_pin':False}
(root/'failure-diagnostics.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps(report))
PY
"""
result=guest_access.run(remote,timeout=60)
(OUT/'failure-diagnostics-raw.log').write_bytes(result.stdout+b'\nSTDERR\n'+result.stderr)
assert result.returncode==0,result.stderr.decode('utf-8','replace')
report=json.loads(result.stdout)
(OUT/'failure-diagnostics-source.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':report['status'],'index_results':report['indices'],'target_image_exists':report['target_image_exists'],'guest_free_bytes':report['disk_free_bytes']},indent=2))

