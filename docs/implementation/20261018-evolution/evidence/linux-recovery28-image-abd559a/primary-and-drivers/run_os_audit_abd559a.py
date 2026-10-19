from pathlib import Path
import hashlib,importlib.util,json,shlex,sys

sys.dont_write_bytecode=True
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=LAB/'evidence/os-audit-abd559a'
IMAGE=LAB/'evidence/recovery28-image-abd559a-final'
assert json.loads((IMAGE/'build-summary.json').read_text())['build_exit']==0
inventory=json.loads((IMAGE/'runtime-inventory.json').read_text())
database=json.loads((LAB/'evidence/image-pip-base-primary-20261019/os-audit-plan-primary/trivy-db-provenance.json').read_text())
config={'image_id':inventory['image_id'],'source':'abd559a9ea3227e6c3bdb141241c11f7196c7682','database':database}
frame=json.dumps(config,separators=(',',':')).encode();(OUT/'audit-input.json').write_bytes(frame)
remote='''from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,json,os,shutil,subprocess,sys,tarfile,time,urllib.request
frame=sys.stdin.buffer.read();assert hashlib.sha256(frame).hexdigest()==INPUT_HASH
config=json.loads(frame);root=Path('/home/lab/metodobase-os-audit-abd559a')
provenance=json.loads((root/'tool-provenance.json').read_text())
assert provenance['trivy-sigstore']['exit']==0 and provenance['cosign-artifact-openssl']['exit']==0
binary=root/'trivy/trivy'
def file_info(p):
 with p.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
 return {'bytes':p.stat().st_size,'sha256':digest}
binary_before=file_info(binary);assert binary_before['sha256']==provenance['trivy_executable_sha256']
assert shutil.disk_usage(root).free>4*1024**3
def docker(*args):return subprocess.check_output(['sudo','-n','env','DOCKER_HOST=unix:///var/run/docker.sock','docker',*args],text=True)
assert not docker('ps','-q').strip(),'Running container: audit waits for idle Docker'
image=json.loads(docker('image','inspect',config['image_id']))[0]
assert image['Id']==config['image_id'] and image['Config']['Labels']['org.opencontainers.image.revision']==config['source']
dbconfig=config['database'];dbdir=root/'cache/db';dbdir.mkdir(parents=True,exist_ok=False)
request=urllib.request.Request('https://ghcr.io/token?service=ghcr.io&scope=repository%3Aaquasecurity%2Ftrivy-db%3Apull',headers={'User-Agent':'MetodoBase-local-QA/1.0'})
with urllib.request.urlopen(request,timeout=60) as response:token=json.load(response)['token']
def request(url):return urllib.request.Request(url,headers={'User-Agent':'MetodoBase-local-QA/1.0','Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.manifest.v1+json'})
url='https://ghcr.io/v2/aquasecurity/trivy-db/manifests/'+dbconfig['digest']
with urllib.request.urlopen(request(url),timeout=60) as response:manifest_bytes=response.read()
assert 'sha256:'+hashlib.sha256(manifest_bytes).hexdigest()==dbconfig['digest']
manifest=json.loads(manifest_bytes);assert manifest['layers']==dbconfig['layers'] and len(manifest['layers'])==1
(root/'db-oci-manifest.json').write_bytes(manifest_bytes)
layer=manifest['layers'][0];archive=root/'db-layer.tar.gz';digest=hashlib.sha256();size=0
with urllib.request.urlopen(request('https://ghcr.io/v2/aquasecurity/trivy-db/blobs/'+layer['digest']),timeout=120) as response,archive.open('xb') as stream:
 while chunk:=response.read(1024*1024):
  stream.write(chunk);digest.update(chunk);size+=len(chunk);assert size<=layer['size']
assert size==layer['size'] and 'sha256:'+digest.hexdigest()==layer['digest']
seen=set()
with tarfile.open(archive,mode='r|gz') as tar:
 for member in tar:
  assert member.name in ('trivy.db','metadata.json') and member.name not in seen and member.isfile()
  assert 0<member.size<2*1024**3;seen.add(member.name)
  with tar.extractfile(member) as source,(dbdir/member.name).open('xb') as target:
   while chunk:=source.read(1024*1024):target.write(chunk)
assert seen=={'trivy.db','metadata.json'}
metadata=json.loads((dbdir/'metadata.json').read_text());assert metadata['Version']==2
db_before={p.name:file_info(p) for p in dbdir.iterdir() if p.is_file()}
record={'image_id':image['Id'],'source_commit':config['source'],'db_oci_reference':dbconfig['pinned_reference'],
 'db_manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest(),'db_layer':{'bytes':size,'sha256':digest.hexdigest()},
 'db_metadata':metadata,'db_files_before':db_before,'scanner_before':binary_before,
 'free_bytes_before_scan':shutil.disk_usage(root).free,'db_signature_limit':'OCI manifest/layer digests verified from primary GHCR; database signature not verified.'}
(root/'database-provenance.json').write_text(json.dumps(record,indent=2)+'\\n')
profile=root/'profile';empty=root/'empty.ignore';empty.write_text('');temporary=root/'tmp';temporary.mkdir()
command=['sudo','-n','env','-i','PATH=/usr/bin:/bin','LANG=C.UTF-8','HOME='+str(profile),'TMPDIR='+str(temporary),'XDG_CACHE_HOME='+str(profile/'cache'),
 'XDG_CONFIG_HOME='+str(profile/'config'),'DOCKER_HOST=unix:///var/run/docker.sock','GOMAXPROCS=2','GOMEMLIMIT=1073741824',
 str(binary),'image','--config','','--disable-telemetry','--skip-version-check','--cache-dir',str(root/'cache'),'--skip-db-update','--skip-java-db-update','--offline-scan',
 '--scanners','vuln','--pkg-types','os','--image-src','docker','--list-all-pkgs','--ignorefile',str(empty),
 '--format','json','--output',str(root/'scan.json'),'--exit-code','1','--parallel','1','--timeout','20m',image['Id']]
started=time.monotonic()
with (root/'scan.log').open('xb') as log:
 process=subprocess.Popen(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
 print(json.dumps({'stage':'os-scan','driver_pid':os.getpid(),'scanner_sudo_pid':process.pid,'image_id':image['Id'],'db':dbconfig['pinned_reference']}),flush=True)
 exit_code=process.wait(timeout=1300)
record.update(command=command,exit=exit_code,seconds=round(time.monotonic()-started,3),finished_utc=datetime.now(timezone.utc).isoformat(),
 db_files_after={p.name:file_info(p) for p in dbdir.iterdir() if p.is_file()},scanner_after=file_info(binary),free_bytes_after=shutil.disk_usage(root).free)
if (root/'scan.json').is_file():
 result=json.loads((root/'scan.json').read_text())
 record['os']=result['Metadata'].get('OS')
 record['targets']=[{'target':r.get('Target'),'class':r.get('Class'),'type':r.get('Type'),'packages':len(r.get('Packages',[])),'vulnerabilities':len(r.get('Vulnerabilities',[]))} for r in result.get('Results',[])]
 vulnerabilities=[v for r in result.get('Results',[]) for v in r.get('Vulnerabilities',[])]
 record['vulnerability_entries']=len(vulnerabilities);record['unique_vulnerability_ids']=sorted({v['VulnerabilityID'] for v in vulnerabilities})
 record['fix_available_entries']=sum(bool(v.get('FixedVersion')) for v in vulnerabilities)
 record['severity_counts']={s:sum(v['Severity']==s for v in vulnerabilities) for s in ['UNKNOWN','LOW','MEDIUM','HIGH','CRITICAL']}
 assert all(r.get('Class')=='os-pkgs' for r in result.get('Results',[]))
 assert result['Metadata']['ImageID']==image['Id'] and result['Metadata']['OS']['Family']=='debian'
record['input_bytes_stable']=record['db_files_before']==record['db_files_after'] and record['scanner_before']==record['scanner_after']
(root/'scan-summary.json').write_text(json.dumps(record,indent=2)+'\\n')
assert record['input_bytes_stable'] and exit_code in (0,1)
assert (root/'scan.json').is_file()
print(json.dumps({k:record[k] for k in ['image_id','exit','seconds','vulnerability_entries','fix_available_entries','severity_counts','input_bytes_stable']}),flush=True)
'''.replace('INPUT_HASH',repr(hashlib.sha256(frame).hexdigest()))
compile(remote,'remote-os-audit','exec')
spec=importlib.util.spec_from_file_location('guest_access',LAB/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
with (OUT/'audit-input.json').open('rb') as stream:
    result=access.run('/opt/metodobase-lab/python/bin/python3.12 -c '+shlex.quote(remote),stdin=stream,timeout=1800)
(OUT/'audit-driver.log').write_bytes(result.stdout+result.stderr)
print((result.stdout+result.stderr).decode('utf-8','replace'))
raise SystemExit(result.returncode)
