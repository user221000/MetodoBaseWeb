from pathlib import Path
import hashlib,importlib.metadata,json,re,subprocess
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-gitleaks-peer-private-20261019')
SOURCE=Path(r'F:/mb-progress-retirement-ui-20261019');sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=SOURCE)
contexts=json.loads((PRIVATE/'unresolved-context.STRUCTURAL.json').read_bytes())
report=json.loads((PRIVATE.parent/'metodobase-retirement-ui-scan-7c_07ul3/secret-scan-full.json').read_bytes())
wanted={};records={}
for item in contexts:
    raw=(SOURCE/item['file']).read_bytes();transform=report['encoding_transforms'].get(item['file']);v=json.loads(raw.decode(transform['source_encoding'] if transform else 'utf8'))
    fields=item['field_paths'];field=fields[0];value=v
    for part in field:value=value[part]
    assert sha(value.encode())==item['matched_value_sha256']
    name=field[-1]
    if name=='current_api_sha256':name='web/static/js/api.js'
    wanted[value]=name
proofs={};objects={};paths=sorted(n for n in set(wanted.values()) if n.startswith(('web/','tests/')))
commits=git('rev-list','--all').decode().splitlines()
log=git('log','-m','--raw','--no-abbrev','--no-renames','-z','--format=',*commits,'--',*paths)
chunks=log.split(b'\0');i=0
while i<len(chunks):
    meta=chunks[i].lstrip(b'\n')
    if not meta:i+=1;continue
    f=meta[1:].split();assert meta.startswith(b':') and len(f)==5
    path=chunks[i+1].decode()
    for mode,oid in [(f[0],f[2]),(f[1],f[3])]:
        if mode in {b'100644',b'100755'} and oid!=b'0'*40:objects.setdefault(oid.decode(),set()).add(path)
    i+=2
for oid,names in objects.items():
    raw=git('cat-file','blob',oid)
    variants={'Git_blob_bytes_observed_now':raw}
    try:
        raw.decode('utf8',errors='strict')
        if b'\0' not in raw:
            if raw.startswith(b'\xef\xbb\xbf'):raw=raw[3:]
            lf=raw.replace(b'\r\n',b'\n')
            variants['DERIVED_UTF8_BOM_plus_GitLF_checksum_not_execution_RAW']=b'\xef\xbb\xbf'+lf
            variants['DERIVED_UTF8_BOM_plus_CRLF_checksum_not_execution_RAW']=b'\xef\xbb\xbf'+lf.replace(b'\n',b'\r\n')
            variants['DERIVED_CRLF_checksum_not_execution_RAW']=lf.replace(b'\n',b'\r\n')
            if lf.endswith(b'\n'):
                variants['DERIVED_one_terminal_LF_removed_checksum_not_execution_RAW']=lf[:-1]
            variants['DERIVED_one_terminal_LF_added_checksum_not_execution_RAW']=lf+b'\n'
    except UnicodeError:pass
    for derivation,data in variants.items():
        value=sha(data)
        if value in wanted and wanted[value] in names:proofs[value]={'kind':'public_Git_source_checksum_observed_with_later_ref_set','path':wanted[value],'oid':oid,'derivation':derivation,'later_ref_set_count':len(commits)}
try:
    d=importlib.metadata.distribution('pytz');path=d.locate_file('pytz/zoneinfo/Pacific/Apia');content=path.read_bytes();value=sha(content)
    if value in wanted:proofs[value]={'kind':'exact_installed_public_pytz_zoneinfo_bytes','path_suffix':'pytz/zoneinfo/Pacific/Apia','distribution':'pytz','version':d.version,'sha256':value,'observation':'Current installed binary bytes observed after scanner review, not historical execution RAW.'}
except (importlib.metadata.PackageNotFoundError,FileNotFoundError):pass
result={'later_pinned_commits':commits,'git_metadata_only_log_sha256':sha(log),'public_blobs_read_in_memory':len(objects),
    'proofs_by_matched_value_sha256':{sha(value.encode()):proof for value,proof in proofs.items()},
    'unresolved_unique_values':len(set(wanted)-set(proofs)),
    'unresolved_paths':sorted({wanted[value] for value in set(wanted)-set(proofs)}),'scope':'Checksums only; all additional newline/BOM transformations are DERIVED, not reconstructions of execution RAW; later refs do not assert availability at the prior scan time.'}
(PRIVATE/'late-hashes.STRUCTURAL.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({'public_blobs':len(objects),'additional_unique_checksums_proven':len(proofs),'unresolved_paths':result['unresolved_paths'],'proofs':list(proofs.values())},indent=2))
