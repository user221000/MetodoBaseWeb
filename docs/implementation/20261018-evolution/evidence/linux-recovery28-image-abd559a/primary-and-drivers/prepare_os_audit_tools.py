from pathlib import Path
import hashlib,importlib.util,json,shlex,subprocess,sys

sys.dont_write_bytecode=True
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
PRIMARY=LAB/'evidence/image-pip-base-primary-20261019/os-audit-plan-primary'
OUT=LAB/'evidence/os-audit-abd559a';OUT.mkdir(exist_ok=False)
cosign=json.loads((PRIMARY/'cosign-pins-complete.json').read_text())
trivy=json.loads((PRIMARY/'plan-pins.json').read_text())
assets={**cosign['assets'],**{k:v for k,v in trivy['assets'].items() if k in ['trivy_0.76.0_Linux-64bit.tar.gz','trivy_0.76.0_Linux-64bit.tar.gz.sigstore.json']}}
config={'assets':assets,'root':'/home/lab/metodobase-os-audit-abd559a'}
frame=json.dumps(config,separators=(',',':')).encode()
(OUT/'tool-input.json').write_bytes(frame)
remote='''import base64,hashlib,json,os,pathlib,shutil,subprocess,sys,tarfile,time,urllib.request
data=sys.stdin.buffer.read();assert hashlib.sha256(data).hexdigest()==INPUT_HASH
config=json.loads(data);root=pathlib.Path(config['root']);assert not root.exists();root.mkdir(mode=0o700)
assert shutil.disk_usage(root).free>4*1024**3
record={'free_bytes_before':shutil.disk_usage(root).free,'assets':{}}
for name,asset in config['assets'].items():
 assert pathlib.PurePosixPath(name).name==name
 target=root/name;digest=hashlib.sha256();size=0
 request=urllib.request.Request(asset['browser_download_url'],headers={'User-Agent':'MetodoBase-local-QA/1.0'})
 with urllib.request.urlopen(request,timeout=120) as response,target.open('xb') as stream:
  while chunk:=response.read(1024*1024):stream.write(chunk);digest.update(chunk);size+=len(chunk)
 assert size==asset['size'] and 'sha256:'+digest.hexdigest()==asset['digest'],name
 record['assets'][name]={'bytes':size,'sha256':digest.hexdigest(),'source':asset['browser_download_url']}
 (root/'downloads.json').write_text(json.dumps(record,indent=2)+'\\n')
profile=root/'profile';profile.mkdir(mode=0o700)
env={'PATH':'/usr/bin:/bin','HOME':str(profile),'XDG_CACHE_HOME':str(profile/'cache'),'XDG_CONFIG_HOME':str(profile/'config')}
bundle=json.loads((root/'cosign-linux-amd64-kms.sigstore.json').read_text())
signature=root/'cosign-kms.signature';signature.write_bytes(base64.b64decode(bundle['messageSignature']['signature'],validate=True))
def run(name,args,timeout=300):
 p=subprocess.run(args,capture_output=True,env=env,timeout=timeout)
 (root/(name+'.log')).write_bytes(p.stdout+p.stderr)
 record[name]={'exit':p.returncode,'command':args}
 (root/'tool-provenance.json').write_text(json.dumps(record,indent=2)+'\\n')
 assert p.returncode==0,name
 return p
run('cosign-artifact-openssl',['/usr/bin/openssl','dgst','-sha256','-verify',str(root/'release-cosign.pub'),'-signature',str(signature),str(root/'cosign-linux-amd64')])
(root/'cosign-linux-amd64').chmod(0o700)
cosign=str(root/'cosign-linux-amd64')
version=run('cosign-version',[cosign,'version']);assert b'v3.1.3' in version.stdout+version.stderr
run('cosign-keyless-self',[cosign,'verify-blob',str(root/'cosign-linux-amd64'),'--bundle',str(root/'cosign-linux-amd64.sigstore.json'),'--certificate-identity','keyless@projectsigstore.iam.gserviceaccount.com','--certificate-oidc-issuer','https://accounts.google.com'])
run('trivy-sigstore',[cosign,'verify-blob',str(root/'trivy_0.76.0_Linux-64bit.tar.gz'),'--bundle',str(root/'trivy_0.76.0_Linux-64bit.tar.gz.sigstore.json'),'--certificate-identity','https://github.com/aquasecurity/trivy/.github/workflows/reusable-release.yaml@refs/tags/v0.76.0','--certificate-oidc-issuer','https://token.actions.githubusercontent.com'])
destination=root/'trivy';destination.mkdir()
with tarfile.open(root/'trivy_0.76.0_Linux-64bit.tar.gz') as archive:
 names=[]
 for member in archive.getmembers():
  p=pathlib.PurePosixPath(member.name);names.append(member.name)
  assert not p.is_absolute() and '..' not in p.parts and (member.isfile() or member.isdir())
 assert len(names)==len(set(names))
 archive.extractall(destination,filter='data')
binary=destination/'trivy';assert binary.is_file() and not binary.is_symlink();binary.chmod(0o700)
record['trivy_executable_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
version=run('trivy-version',[str(binary),'--version']);assert b'0.76.0' in version.stdout
record.update(free_bytes_after=shutil.disk_usage(root).free,cosign_bootstrap_limit='OpenSSL artifact signature verified against public key pinned from primary release. Complete Sigstore TUF artifact-key root chain not independently reconstructed. Keyless self-verification is supplementary, not an independent bootstrap.')
(root/'tool-provenance.json').write_text(json.dumps(record,indent=2)+'\\n')
print(json.dumps({'status':'tools-verified','root':str(root),'trivy_executable_sha256':record['trivy_executable_sha256'],'cosign_artifact_signature_exit':record['cosign-artifact-openssl']['exit'],'trivy_sigstore_exit':record['trivy-sigstore']['exit'],'free_bytes_after':record['free_bytes_after']}))
'''.replace('INPUT_HASH',repr(hashlib.sha256(frame).hexdigest()))
compile(remote,'remote-tool-preparation','exec')
spec=importlib.util.spec_from_file_location('guest_access',LAB/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
with (OUT/'tool-input.json').open('rb') as stream:
    result=access.run('/opt/metodobase-lab/python/bin/python3.12 -c '+shlex.quote(remote),stdin=stream,timeout=900)
(OUT/'prepare.log').write_bytes(result.stdout+result.stderr)
print((result.stdout+result.stderr).decode('utf-8','replace'))
raise SystemExit(result.returncode)
