from pathlib import Path,PurePosixPath
import hashlib,importlib.util,io,json,shlex,sys,tarfile

sys.dont_write_bytecode=True
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
stage=sys.argv[1];assert stage in ('tools','results')
OUT=LAB/'evidence/os-audit-abd559a'/stage;OUT.mkdir(exist_ok=False)
names={'tools':['downloads.json','tool-provenance.json','cosign-artifact-openssl.log','cosign-version.log','cosign-keyless-self.log',
 'trivy-sigstore.log','trivy-version.log','cosign-linux-amd64-kms.sigstore.json','cosign-linux-amd64.sigstore.json',
 'trivy_0.76.0_Linux-64bit.tar.gz.sigstore.json','release-cosign.pub','cosign-kms.signature','cosign_checksums.txt'],
 'results':['db-oci-manifest.json','database-provenance.json','scan.log','scan.json','scan-summary.json','empty.ignore','cache/db/metadata.json']}[stage]
remote='''from pathlib import Path
import sys,tarfile
root=Path('/home/lab/metodobase-os-audit-abd559a')
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as archive:
 for name in NAMES:
  path=root/name;assert path.is_file() and not path.is_symlink()
  archive.add(path,arcname=name,recursive=False)
'''.replace('NAMES',repr(names))
spec=importlib.util.spec_from_file_location('guest_access',LAB/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
result=access.run('/opt/metodobase-lab/python/bin/python3.12 -c '+shlex.quote(remote),timeout=120)
(OUT/'collection.log').write_bytes(result.stderr);assert result.returncode==0
manifest={}
with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
    members=archive.getmembers()
    assert sorted(p.name for p in members)==sorted(names) and len(names)==len({p.casefold() for p in names})
    for member in members:
        path=PurePosixPath(member.name)
        assert not path.is_absolute() and '..' not in path.parts and ':' not in member.name and '\\' not in member.name and member.isfile()
        target=OUT/member.name;target.parent.mkdir(exist_ok=True,parents=True)
        data=archive.extractfile(member).read();target.write_bytes(data)
        manifest[member.name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
(OUT/'collection-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'stage':stage,'files':len(manifest),'manifest_sha256':hashlib.sha256((OUT/'collection-manifest.json').read_bytes()).hexdigest()}))
