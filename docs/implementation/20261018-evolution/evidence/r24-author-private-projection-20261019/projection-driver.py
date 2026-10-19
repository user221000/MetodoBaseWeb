"""Preserve safe original evidence; redact only four independently identified CSRF values."""
from pathlib import Path,PurePosixPath
import hashlib,io,json,re,subprocess,zipfile
root=Path(r'F:\MetodoBaseWeb-execution-20261018');author=Path(r'F:\mb-r24-plan-20261019');source=author/'docs/implementation/20261018-evolution/evidence/r24'
dest=root/'docs/implementation/20261018-evolution/evidence/r24-author-private-projection-20261019'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=author,text=True).strip()=='adc80c7edb6314a7851b9447bccb092a62c142d5'
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=author)
metadata=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r24-after-privacy-independent-20261019\check_author_csrf_metadata.json')
identified={r['path']:r for r in json.loads(metadata.read_bytes())['files']};assert len(identified)==4
def sensitive(blob):
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',blob):
        p=match.start()
        if p>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',blob[p-30:p]):return True
    return bool(re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+|eyJ[A-Za-z0-9_-]{15,8192}\.[A-Za-z0-9_-]{10,8192}\.[A-Za-z0-9_-]{10,8192}',blob))
archives=[]
def scan_archive(blob,name,depth=0):
    assert depth<3
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        entries=archive.infolist();assert sum(r.file_size for r in entries)<=50*1024*1024
        for row in entries:
            key=PurePosixPath(row.filename);assert not key.is_absolute() and '..' not in key.parts and not re.match(r'^[A-Za-z]:',row.filename)
            if row.is_dir():continue
            value=archive.read(row);assert not sensitive(value),(name,row.filename)
            if zipfile.is_zipfile(io.BytesIO(value)):scan_archive(value,name+'!'+row.filename,depth+1)
        archives.append({'path':name,'sha256':sha(blob),'entries':len(entries),'all_entries_scanned':True,'expanded_bytes':sum(r.file_size for r in entries)})
files={};redacted={};original={}
for path in sorted(source.rglob('*')):
    if not path.is_file():continue
    name=path.relative_to(source).as_posix();blob=path.read_bytes();original[name]=sha(blob)
    if name in identified:
        assert sha(blob)==identified[name]['RAW_sha256']
        value,count=re.subn(rb'[0-9]{9,16}\.[A-Fa-f0-9]{64}\.[a-f0-9]{64}',b'[REDACTED_SYNTHETIC_CSRF]',blob)
        assert count==1 and not sensitive(value),name
        redacted[name]={'RAW_sha256':sha(blob),'public_sha256':sha(value),'replacements':count,'reason':'Synthetic SSR CSRF timestamp.nonce64.HMAC64, retained only in original private author worktree/commit; no value printed.'}
        blob=value
    else:assert not sensitive(blob),name
    if zipfile.is_zipfile(io.BytesIO(blob)):scan_archive(blob,name)
    assert path.suffix.lower() not in {'.sqlite','.sqlite3','.db','.7z','.rar','.gz'},name
    files[name]=blob
assert set(redacted)==set(identified) and len(archives)==2
dest.mkdir(exist_ok=False);(dest/'.gitattributes').write_bytes(b'* -text\n')
for name,blob in files.items():
    target=dest/'original'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
    assert sha((source/name).read_bytes())==original[name]
record={'author_commit':'adc80c7edb6314a7851b9447bccb092a62c142d5','original_RAW_files':len(files),'unchanged_RAW_files':len(files)-4,'redacted_files':redacted,'archives':archives,'independent_metadata_sha256':sha(metadata.read_bytes()),'original_final_source_sha256':sha((source/'final-source.json').read_bytes()),'scope':'Original author source/commit/RAW are unchanged and kept local/private. Public projection has its own manifest. Four SSR payloads differ exactly by one CSRF value each; historical metadata in original/ describes its original frozen source and does not authenticate this new projection. No result/assertion changed and no test rerun. This prefix is preparation only; integration/independent final source acceptance remain separate.'}
(dest/'projection.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
(dest/'projection-driver.py').write_bytes(Path(__file__).read_bytes())
(dest/'independent-identification.json').write_bytes(metadata.read_bytes())
manifest={'files':{p.relative_to(dest).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(dest.rglob('*')) if p.is_file()}}
(dest/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
print(json.dumps({'manifest_sha256':sha((dest/'manifest.json').read_bytes()),'files':len(manifest['files'])+1,'original_RAW_files':len(files),'redacted':4,'archives_scanned':archives}))
