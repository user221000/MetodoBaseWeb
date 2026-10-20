"""Fixed-input independent verification. Historical payloads remain in memory."""
from collections import Counter
from pathlib import Path,PurePosixPath
import hashlib,json,re,subprocess,sys,zipfile
ROOT=Path(r'F:/mb-security-gitleaks-triage-peer-20261019')
SOURCE=Path(r'F:/mb-progress-retirement-ui-20261019')
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp')
PRIVATE=TEMP/'metodobase-sec-gitleaks-peer-private-20261019'
PREFIX='docs/implementation/20261018-evolution/evidence/security-gitleaks-triage-independent-20261019'
OUT=ROOT/PREFIX
REPORT=TEMP/'metodobase-retirement-ui-scan-7c_07ul3/secret-scan-full.json'
PIN='0e5d0cfc77c1626912beca8c9b39e91fe56464e9e9cc71502947e44288b09352'
PHASES=['metodobase-gitleaks-fingerprint-triage-20261019','metodobase-gitleaks-historical-fingerprint-triage-20261019','metodobase-gitleaks-public-artifact-triage-20261019','metodobase-gitleaks-historical-evidence-triage-20261019']
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
def save(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
def canonical(name):
    assert isinstance(name,str) and '\\' not in name and ':' not in name
    p=PurePosixPath(name);assert not p.is_absolute() and p.as_posix()==name and all(x not in {'.','..',''} for x in p.parts)
    return name
FIELDS=['file','line','rule','fingerprint','file_sha256']
def key(row):return tuple(row[k] for k in FIELDS)
report_blob=REPORT.read_bytes();assert sha(report_blob)==PIN
report=json.loads(report_blob);assert report['source_stable'] and not report['changed_files'] and len(report['findings'])==31564
assert report['version']=='8.30.1' and report['binary_sha256']=='17157e2ee8b76fc8b1d8bee607a250e34b8a8023c8bc81822d4b5ee4d78fcb7c'
tracked={}
for item in git('ls-tree','-r','-z','de216543a2eec05584168cdb888f627901b0e0b1').split(b'\0'):
    if item:
        meta,name=item.split(b'\t');mode,kind,oid=meta.decode().split();tracked[name.decode()]=(mode,kind,oid)
cache={};textcache={}
def payload(name):
    canonical(name)
    if name not in cache:
        path=SOURCE/name;assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(SOURCE)
        data=path.read_bytes();assert sha(data)==report['files'][name]
        cache[name]=data
    return cache[name]
def text(name):
    if name not in textcache:
        raw=payload(name);transform=report['encoding_transforms'].get(name)
        if transform:
            encoding='utf-32' if raw.startswith((b'\xff\xfe\0\0',b'\0\0\xfe\xff')) else 'utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else None
            assert encoding==transform['source_encoding'] and transform['scanner_encoding']=='utf-8'
            decoded=raw.decode(encoding,errors='strict');assert sha(decoded.encode())==transform['scanner_sha256']
        else:decoded=raw.decode('utf8',errors='strict')
        textcache[name]=decoded
    return textcache[name]
PATTERN=re.compile(r'\s*"(?P<path>[^"\\]+)"\s*:\s*"(?P<digest>[0-9a-f]{64})"\s*,?\s*')
def physical(row):
    assert type(row['line']) is int and row['line']>0
    assert row['file_sha256']==report['files'][row['file']]
    line=text(row['file']).split('\n')[row['line']-1]
    match=PATTERN.fullmatch(line);assert match and row['file'].startswith('docs/implementation/20261018-evolution/evidence/')
    return line,match['path'],match['digest']
assert git('rev-parse','HEAD').decode().strip()=='de216543a2eec05584168cdb888f627901b0e0b1'
if not OUT.exists():OUT.mkdir()
assert {p.name for p in OUT.iterdir()}<={'.gitattributes','attempt-initial'}
(OUT/'.gitattributes').write_bytes(b'* -text\n')
rows_by_phase=[json.loads((TEMP/name/'classified.json').read_bytes()) for name in PHASES]
unclassified=json.loads((TEMP/PHASES[-1]/'unclassified-locations.json').read_bytes())
assert list(map(len,rows_by_phase))==[5669,15045,1835,8733] and len(unclassified)==282
assert sum((Counter(map(key,rows)) for rows in rows_by_phase),Counter())+Counter(map(key,unclassified))==Counter(map(key,report['findings']))
save('input-authentication.json',{'report_sha256':PIN,'phase_files':{phase:{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in (TEMP/phase).iterdir() if p.is_file()} for phase in PHASES},'partition_exact':True,'counts':list(map(len,rows_by_phase))+[282]})
object_data={};history_pairs={};pinned_receipts={}
for index in [1,3]:
    folder=TEMP/PHASES[index];commits=json.loads((folder/'pinned-commits.json').read_bytes())
    assert len(commits)==len(set(commits)) and all(re.fullmatch('[a-f0-9]{40}',c) for c in commits)
    wanted=sorted({r['public_source_path'] for r in rows_by_phase[index]})
    log=git('log','-m','--raw','--no-abbrev','--no-renames','-z','--format=',*commits,'--',*wanted)
    chunks=log.split(b'\0');pairs=set();i=0
    while i<len(chunks):
        meta=chunks[i].lstrip(b'\n')
        if not meta:i+=1;continue
        assert meta.startswith(b':');parts=meta[1:].split();assert len(parts)==5
        path=chunks[i+1].decode();canonical(path)
        for mode,oid in [(parts[0],parts[2]),(parts[1],parts[3])]:
            if mode in {b'100644',b'100755'} and oid!=b'0'*40:pairs.add((oid.decode(),path))
        i+=2
    history_pairs[index]=pairs
    pinned_receipts[PHASES[index]]={'pinned_commits':commits,'raw_metadata_only_log_sha256':sha(log),'oid_path_pairs':len(pairs)}
save('history-metadata-only.json',pinned_receipts)
proofs=[];counts=Counter();verified_artifacts=set()
for phase_index,rows in enumerate(rows_by_phase):
    for row in rows:
        line,target,digest=physical(row);canonical(target)
        result={'file':row['file'],'line':row['line'],'rule':row['rule'],'file_sha256':row['file_sha256'],'physical_line_sha256':sha(line.rstrip('\r').encode()),'proof_type':PHASES[phase_index]}
        if phase_index==0:
            assert target==row['source_path'] and digest==row['source_sha256']
            assert target in tracked and tracked[target][0] in {'100644','100755'} and sha(payload(target))==digest
            assert result['physical_line_sha256']==row['physical_line_sha256']
            result.update(source_path=target,checksum_sha256=sha(digest.encode()))
        elif phase_index in {1,3}:
            oid=row['Git_blob_oid'];assert target==row['public_source_path'] and digest==row['sha256'] and (oid,target) in history_pairs[phase_index]
            if oid not in object_data:
                data=git('cat-file','blob',oid);assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid
                object_data[oid]=data
            data=object_data[oid];derivation=row['derivation']
            if derivation=='DERIVED_GitLF_to_CRLF_checksum_not_historical_RAW':
                data.decode('utf8',errors='strict');assert b'\0' not in data and b'\n' in data and b'\r\n' not in data
                data=data.replace(b'\n',b'\r\n')
            else:assert derivation=='Git_blob_bytes'
            assert sha(data)==digest;counts[derivation]+=1
            result.update(source_path=target,Git_blob_oid=oid,derivation=derivation,checksum_sha256=sha(digest.encode()))
        else:
            proof=row['proof'];assert target==row['metadata_source_path'] and digest==row['checksum']
            artifact=canonical(proof['public_artifact']);assert artifact in tracked and tracked[artifact][0] in {'100644','100755'}
            artifact_key=(json.dumps(proof,sort_keys=True),digest)
            if artifact_key not in verified_artifacts:
                data=payload(artifact)
                if proof['kind']=='Exact_scanned_frozen_public_artifact_bytes':assert sha(data)==proof['artifact_sha256']==digest
                else:
                    assert proof['kind']=='Exact_member_bytes_in_frozen_public_Git_archive' and data==git('show','de216543a2eec05584168cdb888f627901b0e0b1:'+artifact)
                    assert sha(data)==proof['archive_sha256']
                    with zipfile.ZipFile(SOURCE/artifact) as archive:
                        member=archive.getinfo(proof['member']);assert member.file_size<=32*1024*1024 and len(archive.infolist())<=20000
                        body=archive.read(member);assert len(body)==proof['member_bytes'] and sha(body)==proof['member_sha256']==digest
                verified_artifacts.add(artifact_key)
            result.update(artifact=artifact,proof_kind=proof['kind'],checksum_sha256=sha(digest.encode()))
        proofs.append(result)
save('independent-verified-checksum-locations.json',proofs)
save('checksum-verification-summary.json',{'verified':len(proofs),'phase_counts':list(map(len,rows_by_phase)),'history_blob_payloads_read_only_in_memory':len(object_data),'historical_derivations':counts,'history_payloads_written':False,'unclassified_locations':len(unclassified)})
save('source-before.json',{'source':'de216543a2eec05584168cdb888f627901b0e0b1','checked_files_first_read':{name:sha(data) for name,data in cache.items()},'tracked_tree_files':len(tracked),'pinned_report_files':len(report['files']),'tracked_not_in_scan':sorted(set(tracked)-set(report['files'])),'report_sha256':PIN,'scope':'Hashes captured when each file used by triage was first read. Not a new full-tree scan or simultaneous photograph of every deliverable file.'})
FOCAL=PRIVATE/'focal-snapshot';FOCAL.mkdir()
for name in sorted({r['file'] for r in unclassified}|{'.gitleaks.toml'}):
    path=FOCAL/name;path.parent.mkdir(parents=True,exist_ok=True)
    content=text(name).encode() if name in report['encoding_transforms'] else payload(name)
    with path.open('xb') as output:output.write(content)
tool=TEMP/'metodobase-gitleaks-8.30.1/gitleaks.exe';assert sha(tool.read_bytes())==report['binary_sha256']
ignore=PRIVATE/'empty.gitleaksignore';ignore.write_bytes(b'')
raw=PRIVATE/'focal-redacted.json'
command=[str(tool),'dir',str(FOCAL),'--config',str(FOCAL/'.gitleaks.toml'),'--redact=100','--no-banner','--no-color','--log-level=error','--ignore-gitleaks-allow','--gitleaks-ignore-path',str(ignore),'--max-decode-depth=5','--max-archive-depth=0','--report-format=json','--report-path',str(raw),'--timeout=120']
run=subprocess.run(command,capture_output=True,timeout=135,cwd=PRIVATE,env={k:v for k,v in __import__('os').environ.items() if not k.upper().startswith('GITLEAKS_')})
(PRIVATE/'focal-stdout.redacted.raw.log').write_bytes(run.stdout);(PRIVATE/'focal-stderr.redacted.raw.log').write_bytes(run.stderr)
assert run.returncode==1 and raw.exists()
findings=json.loads(raw.read_bytes());assert isinstance(findings,list)
safe=[]
for item in findings:
    name=Path(item['File']).relative_to(FOCAL).as_posix() if Path(item['File']).is_absolute() else canonical(item['File'])
    safe.append({'file':name,'line':item['StartLine'],'end_line':item['EndLine'],'start_column':item['StartColumn'],'end_column':item['EndColumn'],'rule':item['RuleID'],'redacted_secret':item.get('Secret')=='REDACTED','fragment':item.get('Fragment',None)})
save('focal-columns.STRUCTURAL.json',safe)
save('focal-summary.json',{'exit':run.returncode,'binary_sha256':sha(tool.read_bytes()),'config_sha256':sha((FOCAL/'.gitleaks.toml').read_bytes()),'files':len(list(FOCAL.rglob('*'))),'findings':len(safe),'fixed_report_remaining':len(unclassified),'raw_redacted_report_sha256':sha(raw.read_bytes()),'redact':100,'scope':'Only files containing the fixed282 remaining locations; no global scan, no allowlist change, private snapshot.'})
print(json.dumps({'verified_checksum_locations':len(proofs),'remaining':len(unclassified),'focal_findings':len(safe),'phase_counts':list(map(len,rows_by_phase)),'historical_derivations':counts}),flush=True)
