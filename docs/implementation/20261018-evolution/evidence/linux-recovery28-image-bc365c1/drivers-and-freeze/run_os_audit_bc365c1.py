from pathlib import Path
import hashlib,importlib.util,json,shlex,sys

sys.dont_write_bytecode=True
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=LAB/'evidence/os-audit-bc365c1';OUT.mkdir(exist_ok=False)
IMAGE=LAB/'evidence/recovery28-image-bc365c1'
assert json.loads((IMAGE/'build-summary.json').read_text())['build_exit']==0
inventory=json.loads((IMAGE/'runtime-inventory.json').read_text())
database=json.loads((LAB/'evidence/image-pip-base-primary-20261019/os-audit-plan-primary/trivy-db-provenance.json').read_text())
baseline_manifest_path=Path(r'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence\linux-recovery28-image-abd559a\evidence-manifest.json')
baseline_manifest_bytes=baseline_manifest_path.read_bytes()
assert hashlib.sha256(baseline_manifest_bytes).hexdigest()=='fc0053a28039d61c8b7a82b99fd6f13b4a9ed595d9d8cd4711d96c1223aa6705'
baseline_manifest=json.loads(baseline_manifest_bytes)
baseline_summary_bytes=(LAB/'evidence/os-audit-abd559a/results/scan-summary.json').read_bytes()
assert hashlib.sha256(baseline_summary_bytes).hexdigest()==baseline_manifest['files']['os-audit/results/scan-summary.json']['sha256']
baseline_summary=json.loads(baseline_summary_bytes)
config={'image_id':inventory['image_id'],'source':'bc365c13b9af9e24129a56b4068059a67bb3afa0','database':database,
 'expected_db_files':baseline_summary['db_files_after'],'expected_scanner_sha256':'1f889576636db0623539cb339df7d06c40ebf39e7919489eafa1160e29808f19',
 'baseline_manifest_sha256':'fc0053a28039d61c8b7a82b99fd6f13b4a9ed595d9d8cd4711d96c1223aa6705'}
frame=json.dumps(config,separators=(',',':')).encode();(OUT/'audit-input.json').write_bytes(frame)
remote='''from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,json,os,shutil,subprocess,sys,tarfile,time,urllib.request
frame=sys.stdin.buffer.read();assert hashlib.sha256(frame).hexdigest()==INPUT_HASH
config=json.loads(frame);prior_root=Path('/home/lab/metodobase-os-audit-abd559a');root=Path('/home/lab/metodobase-os-audit-bc365c1');root.mkdir(mode=0o700,exist_ok=False)
provenance=json.loads((prior_root/'tool-provenance.json').read_text())
assert provenance['trivy-sigstore']['exit']==0 and provenance['cosign-artifact-openssl']['exit']==0
binary=prior_root/'trivy/trivy'
def file_info(p):
 with p.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
 return {'bytes':p.stat().st_size,'sha256':digest}
binary_before=file_info(binary);assert binary_before['sha256']==provenance['trivy_executable_sha256']==config['expected_scanner_sha256']
assert shutil.disk_usage(root).free>4*1024**3
def docker(*args):return subprocess.check_output(['sudo','-n','env','DOCKER_HOST=unix:///var/run/docker.sock','docker',*args],text=True)
assert not docker('ps','-q').strip(),'Running container: audit waits for idle Docker'
image=json.loads(docker('image','inspect',config['image_id']))[0]
assert image['Id']==config['image_id'] and image['Config']['Labels']['org.opencontainers.image.revision']==config['source']
dbconfig=config['database'];dbdir=root/'cache/db';dbdir.mkdir(parents=True,exist_ok=False)
prior_summary=json.loads((prior_root/'scan-summary.json').read_text())
assert prior_summary['input_bytes_stable'] and prior_summary['db_oci_reference']==dbconfig['pinned_reference']
assert prior_summary['db_files_after']==config['expected_db_files']
manifest_bytes=(prior_root/'db-oci-manifest.json').read_bytes()
assert 'sha256:'+hashlib.sha256(manifest_bytes).hexdigest()==dbconfig['digest']
manifest=json.loads(manifest_bytes);assert manifest['layers']==dbconfig['layers'] and len(manifest['layers'])==1
(root/'db-oci-manifest.json').write_bytes(manifest_bytes)
for name in ['metadata.json','trivy.db']:
 original=prior_root/'cache/db'/name
 assert file_info(original)==prior_summary['db_files_after'][name]
 shutil.copyfile(original,dbdir/name)
layer=manifest['layers'][0]
metadata=json.loads((dbdir/'metadata.json').read_text());assert metadata['Version']==2
db_before={p.name:file_info(p) for p in dbdir.iterdir() if p.is_file()}
assert db_before==prior_summary['db_files_after']==config['expected_db_files']
record={'image_id':image['Id'],'source_commit':config['source'],'db_oci_reference':dbconfig['pinned_reference'],
 'db_manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest(),'db_layer':{'bytes':layer['size'],'sha256':layer['digest'].split(':')[1]},'db_reuse':'Byte-exact copy of immutable previously verified OCI layer payload; no mutable-tag update or DB download.',
 'db_metadata':metadata,'db_files_before':db_before,'scanner_before':binary_before,
 'free_bytes_before_scan':shutil.disk_usage(root).free,'db_signature_limit':'OCI manifest/layer digests verified from primary GHCR; database signature not verified.'}
(root/'database-provenance.json').write_text(json.dumps(record,indent=2)+'\\n')
profile=root/'profile';profile.mkdir(mode=0o700);empty=root/'empty.ignore';empty.write_text('');temporary=root/'tmp';temporary.mkdir()
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
