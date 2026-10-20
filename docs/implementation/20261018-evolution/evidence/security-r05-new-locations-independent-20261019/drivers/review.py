"""Independent finite evidence replay; never execute historical drivers."""
from pathlib import Path, PurePosixPath
from collections import Counter
from types import SimpleNamespace
import ast, copy, hashlib, importlib.util, importlib.metadata, io, json, os, re, subprocess, sys, urllib.request, zipfile

R=Path(r'F:/mb-security-r05-classifier-peer-20261019')
A=Path(r'F:/mb-r05-review-classifier-20261019')
T=Path(r'C:/Users/Consu/AppData/Local/Temp')
P=T/'metodobase-sec-r05-new-peer-private-20261019'
PREFIX='docs/implementation/20261018-evolution/evidence/security-r05-new-locations-independent-20261019'
O=R/PREFIX
C=A/'docs/implementation/20261018-evolution/evidence/root-r05-new-locations-candidate-20261019'
REPORT=T/'metodobase-r05-reviewed-author-20261019/current-tree-scan.json'
BASE='a704f0706827d9e02392902737ed96ef4ce8d764'
CANDIDATE='8012dc7d5098ac9064cd87078bcec3ba88d86415'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda root,*a:subprocess.check_output(['git','--no-replace-objects','--literal-pathspecs',*a],cwd=root)
assert git(R,'rev-parse','HEAD').decode().strip()==BASE
assert git(A,'rev-parse','HEAD').decode().strip()==CANDIDATE
assert not git(R,'status','--porcelain','--untracked-files=no') and not git(A,'status','--porcelain','--untracked-files=no')
O.mkdir();(O/'.gitattributes').write_bytes(b'* -text\n')
save=lambda n,x:(O/n).write_bytes((json.dumps(x,indent=2,ensure_ascii=False)+'\n').encode())
def photo():
    names=git(R,'ls-files','-z','--','scripts','tests','web','api','core','config','requirements*','pyproject.toml').decode().split('\0')
    return {'sources':{n:sha((R/n).read_bytes()) for n in names if n and (R/n).is_file()},
        'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
        'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes()),
        'installed_v1':sha((R/'scripts/data/reviewed_scan_locations_v1.zip').read_bytes()),
        'candidate_files':{p.name:sha(p.read_bytes()) for p in C.iterdir() if p.is_file()}}
before=photo();assert len(before['packages'])==89;save('before.json',before)
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);assert pip.returncode==0
(O/'pip-before.RAW.log').write_bytes(pip.stdout+pip.stderr)
assert sha((C/'source.json').read_bytes())=='7b55e97858c3dadeaf62e89c4562ab8c92d80933036103ad9c9e3619c092703b'
assert sha((C/'manifest.json').read_bytes())=='196c94b7fd96acf147b7cc92eddf27ef67e1e759aba3b8f92a6e0d3fad642d0b'
source=json.loads((C/'source.json').read_bytes());manifest=json.loads((C/'manifest.json').read_bytes())
for name,meta in manifest.items():
    raw=(C/name).read_bytes();assert meta.get('digest',meta.get('sha256'))==sha(raw) and meta['bytes']==len(raw)
report_raw=REPORT.read_bytes();assert sha(report_raw)=='f273556e34d1796de1f8a01e17d58842be82c7a6ab2173bdeabb1a2d91714f8d'
report=json.loads(report_raw);assert report['source_stable'] and len(report['findings'])==14557
with zipfile.ZipFile(C/'candidate-evidence.zip') as z:
    entries=z.infolist();assert len({i.filename for i in entries})==len(entries)
    assert len(entries)<100 and sum(i.file_size for i in entries)<64*1024*1024
    for i in entries:
        assert not i.flag_bits&1 and i.file_size<=20*1024*1024 and i.compress_type in {0,8}
        assert not PurePosixPath(i.filename).is_absolute() and '..' not in PurePosixPath(i.filename).parts
    members={i.filename:z.read(i) for i in entries}
for meta in source['manifest_of_original_members']:
    raw=members[meta['path']];assert len(raw)==meta['bytes'] and sha(raw)==meta['digest']
rows=json.loads(members['candidate-rows.json']);assert len(rows)==14557
PHASES=['fingerprint','historical','artifact','evidence-v2','objectid','public-material','runtime-map','final15']
phase_rows={p:json.loads(members['phases/'+p+'/classified.json']) for p in PHASES}
assert sum(map(len,phase_rows.values()))==len(rows)
assert rows==[{**row,'candidate_phase':p} for p in PHASES for row in phase_rows[p]]
coords=lambda r:(r['file'],r['line'],r['rule'],r['fingerprint'],r['file_sha256'])
assert Counter(map(coords,rows))==Counter(map(coords,report['findings']))
dataset_raw=(C/'candidate-reviewed-locations.zip').read_bytes();assert sha(dataset_raw)=='74561c02264e7a611292fe77a828b95bc80b430f5b880f94efbe187c74a3e0fa'
with zipfile.ZipFile(io.BytesIO(dataset_raw)) as z:
    assert z.namelist()==['reviewed-locations.json'];data_raw=z.read(z.namelist()[0])
assert data_raw==members['candidate-reviewed-locations.json']
data=json.loads(data_raw);assert data['schema']==1 and data['version']=='8.30.1' and len(data['files'])==155
rawfiles={};snapfiles={};file_proofs={}
def canonical(n):
    return isinstance(n,str) and 0<len(n)<=1024 and not any(ord(c)<32 for c in n) and '\\' not in n and ':' not in n and not PurePosixPath(n).is_absolute() and all(c not in {'','.','..'} for c in n.split('/'))
for rec in data['files']:
    name=rec['path'];assert canonical(name)
    raw=(A/name).read_bytes();assert sha(raw)==rec['source_digest']==report['files'][name]
    enc='utf-32' if raw.startswith((b'\xff\xfe\0\0',b'\0\0\xfe\xff')) else 'utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else None
    payload=raw.decode(enc).encode() if enc else raw
    payload.decode('utf8',errors='strict');assert sha(payload)==rec['scanner_digest']
    transform=report['encoding_transforms'].get(name)
    assert bool(enc)==bool(transform)
    if enc:assert transform=={'source_encoding':enc,'scanner_encoding':'utf-8','scanner_sha256':sha(payload)}
    rawfiles[name]=raw;snapfiles[name]=payload
    file_proofs[name]={'RAW_SHA256':sha(raw),'scanner_SHA256':sha(payload),'source_encoding':enc,'physical_line_count':len(payload.split(b'\n'))}
assert len(rawfiles)==155
def physical(row):
    assert type(row['line']) is int and row['line']>0
    return snapfiles[row['file']].split(b'\n')[row['line']-1]
computedpins={}
for row in rows:
    assert row['file_sha256']==sha(rawfiles[row['file']])
    digest=sha(physical(row))
    if 'physical_line_sha256' in row:assert row['physical_line_sha256']==digest
    key=row['file'],row['line'],row['rule'];assert key not in computedpins or computedpins[key]==digest
    computedpins[key]=digest
pins={(rec['path'],line['number'],rule):line['digest'] for rec in data['files'] for line in rec['lines'] for rule in line['rules']}
assert pins==computedpins and len(pins)==14516
save('physical-file-binding.json',{'files':file_proofs,'occurrences':len(rows),'unique_pins':len(pins),
    'original_rows_without_line_digest':sum('physical_line_sha256' not in r for r in rows),
    'all_physical_line_bytes_include_CR':True,'all_dataset_pins_exact':True})

# Read only reachable object metadata. No Git historical payloads are printed,
# copied into public evidence or executed.
commits=set()
for name,raw in members.items():
    if name.endswith('/pinned-commits.json'):commits.update(json.loads(raw))
reachable=set(git(A,'rev-list','--all').decode().splitlines())
assert commits<=reachable and all(re.fullmatch('[0-9a-f]{40}',c) for c in commits)
rawlog=subprocess.run(['git','--no-replace-objects','log','-m','--raw','--no-abbrev','--no-renames','-z','--format=','--stdin'],input=('\n'.join(sorted(commits))+'\n').encode(),cwd=A,capture_output=True,check=True).stdout
chunks=rawlog.split(b'\0');pairs=set();i=0
while i<len(chunks):
    meta=chunks[i].lstrip(b'\n')
    if not meta:i+=1;continue
    assert meta.startswith(b':');fields=meta[1:].split();assert len(fields)==5
    name=chunks[i+1].decode()
    for mode,oid in [(fields[0],fields[2]),(fields[1],fields[3])]:
        if mode in {b'100644',b'100755'} and oid!=b'0'*40:pairs.add((oid.decode(),name))
    i+=2
map_witnesses=json.loads(members['phases/runtime-map/map-witnesses.json'])
oids={r['Git_blob_oid'] for p in ['historical','evidence-v2','objectid'] for r in phase_rows[p]}
oids.update(v['Git_blob_oid'] for w in map_witnesses for v in w['proofs'].values())
oids.update(h['Git_blob_oid'] for r in phase_rows['final15'] if 'witnesses' in r['proof'] for h in r['proof']['witnesses'] if 'Git_blob_oid' in h)
objects={}
process=subprocess.Popen(['git','--no-replace-objects','cat-file','--batch'],cwd=A,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
    for oid in sorted(oids):
        process.stdin.write((oid+'\n').encode());process.stdin.flush()
        header=process.stdout.readline().decode().split();assert header[:2]==[oid,'blob']
        n=int(header[2]);assert 0<=n<32*1024*1024
        payload=process.stdout.read(n);assert len(payload)==n and process.stdout.read(1)==b'\n'
        assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+payload).hexdigest()==oid
        variants={'Git_blob_bytes':sha(payload)}
        try:
            payload.decode('utf8')
            if b'\0' not in payload and b'\n' in payload and b'\r\n' not in payload:
                variants['derived_CRLF']=sha(payload.replace(b'\n',b'\r\n'))
        except UnicodeError:pass
        objects[oid]={'bytes':n,'variants':variants,'UTF16_BOM':payload.startswith((b'\xff\xfe',b'\xfe\xff'))}
finally:
    process.stdin.close();assert process.wait(timeout=30)==0 and not process.stderr.read()
def object_digest(oid,path,derivation,digest):
    if (oid,path) not in pairs:return False
    key='Git_blob_bytes' if derivation=='Git_blob_bytes' else 'derived_CRLF' if derivation.startswith('DERIVED_GitLF_to_CRLF_checksum_') else None
    return key is not None and objects[oid]['variants'].get(key)==digest
pattern=re.compile(r'\s*"([^"\\]+)"\s*:\s*"([0-9a-f]{64})"\s*,?\s*')
tracked=set(git(A,'ls-tree','-r','--name-only','-z','f7b12a71a89de2e35b0035ccef147a673ad50d29').decode().split('\0'))
public_targets={};artifact_witnesses={};verified=[]
for p in ['fingerprint','historical','artifact','evidence-v2']:
    for row in phase_rows[p]:
        line=physical(row).decode();match=pattern.fullmatch(line);assert match
        path,digest=match.groups();assert canonical(path)
        if p=='fingerprint':
            assert path==row['source_path'] and digest==row['source_sha256'] and path in tracked
            if path not in public_targets:public_targets[path]=sha((A/path).read_bytes())
            assert public_targets[path]==digest==report['files'][path]
        elif p in {'historical','evidence-v2'}:
            assert path==row['public_source_path'] and digest==row['sha256']
            assert object_digest(row['Git_blob_oid'],path,row['derivation'],digest)
        else:
            assert path==row['metadata_source_path'] and digest==row['checksum']
            proof=row['proof'];target=proof['public_artifact'];assert target in tracked
            if proof['kind']=='Exact_scanned_frozen_public_artifact_bytes':
                payload=(A/target).read_bytes();assert sha(payload)==proof['artifact_sha256']==digest==report['files'][target]
            else:
                assert proof['kind']=='Exact_member_bytes_in_frozen_public_Git_archive'
                coord=target,proof['member']
                if coord not in artifact_witnesses:
                    archive=(A/target).read_bytes();assert sha(archive)==proof['archive_sha256']
                    assert archive==git(A,'show','f7b12a71a89de2e35b0035ccef147a673ad50d29:'+target)
                    with zipfile.ZipFile(io.BytesIO(archive)) as z:
                        info=z.infolist();assert len(info)<=20000 and len({i.filename for i in info})==len(info)
                        member=z.getinfo(proof['member']);assert member.file_size<=32*1024*1024 and not member.flag_bits&1
                        assert canonical(member.filename) and member.compress_type in {0,8}
                        payload=z.read(member);assert len(payload)==proof['member_bytes']
                        artifact_witnesses[coord]=sha(payload)
                assert artifact_witnesses[coord]==proof['member_sha256']==digest
        verified.append((p,row))

tree_cache={}
for row in phase_rows['objectid']:
    match=re.fullmatch(r'\s*"([^"\\]+)"\s*:\s*"([a-f0-9]{40})"\s*,?\s*',physical(row).decode());assert match
    path,oid=match.groups();assert path==row['metadata_path'] and oid==row['Git_blob_oid'] and canonical(path)
    commit=row['witness_commit'];assert commit in reachable
    if commit not in tree_cache:
        tree_cache[commit]={entry.split(b'\t',1)[1].decode():entry.split(b'\t',1)[0].split()[2].decode() for entry in git(A,'ls-tree','-r','-z',commit).split(b'\0') if entry}
    assert tree_cache[commit][path]==oid and objects[oid]['variants']['Git_blob_bytes']==row['object_content_digest']
    verified.append(('objectid',row))

url='https://raw.githubusercontent.com/python/cpython/v3.12.13/Include/internal/pycore_token.h'
with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MetodoBase independent finite checksum review'}),timeout=20) as response:
    assert response.status==200 and response.geturl()==url
    header=response.read(65537);assert len(header)<=65536
(P/'public-cpython-header.downloaded').write_bytes(header)
keyproof_path=Path(r'F:/mb-security-gitleaks-triage-peer-20261019/docs/implementation/20261018-evolution/evidence/security-gitleaks-triage-independent-20261019/public-key-proof.STRUCTURAL.json')
keyproof=json.loads(keyproof_path.read_bytes());key=(A/keyproof['retained_path']).read_bytes()
assert sha(key)==keyproof['retained_key_sha256']=='1de2bbd31e2dd10aab4098c3ab2f937c530d924ddbfa2dd091f0c7cfb2ee182a'
for row in phase_rows['public-material']:
    proof=row['proof'];line=physical(row).decode()
    if proof['kind'].startswith('exact public'):
        match=re.fullmatch(r'\s*"GPG_KEY=([A-F0-9]{40})",?\s*',line);assert match
        assert keyproof['public_primary_fingerprints']==[match[1]]
        assert proof['retained_public_key_digest']==sha(key) and proof['reused_independent_proof_digest']==sha(keyproof_path.read_bytes())
    else:
        match=pattern.fullmatch(line);assert match and match[1]=='/usr/local/include/python3.12/internal/pycore_token.h'
        assert match[2]==sha(header)==proof['downloaded_public_digest'] and proof['public_source_url']==url
    verified.append(('public-material',row))

for w in map_witnesses:
    raw=rawfiles[w['file']];line=snapfiles[w['file']].split(b'\n')[w['line']-1]
    if w['file'].endswith('/drivers/runtime_probe.py.txt'):
        assignment=next(n for n in ast.parse(raw).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='EXPECTED_APP')
        assert assignment.lineno==w['line'];mapping=ast.literal_eval(assignment.value)
    else:mapping=json.loads(line)['runtime_raw_sha256']
    assert set(mapping)==set(w['proofs']) and len(mapping)==w['pairs']==w['verified'] and not w['missing_paths']
    assert sha(line)==w['physical_line_digest']
    for path,digest in mapping.items():
        proof=w['proofs'][path];assert canonical(path) and re.fullmatch('[a-f0-9]{64}',digest)
        assert proof['digest']==digest and object_digest(proof['Git_blob_oid'],path,proof['derivation'],digest)
    verified.extend(('runtime-map',row) for row in phase_rows['runtime-map'] if (row['file'],row['line'])==(w['file'],w['line']))

# Prove only the pure producer function; never import/run the historical adapter.
producer_path=T/'metodobase-mfa31-browser-v2-independent-20261019/server_adapter.py'
producer=producer_path.read_bytes();producer_digest=sha(producer)
assert producer_digest=='db2749e19ca871d3e1df3e1b113085c8f6d8c115f9c4b155434f8535d65ab9ee'
function=next(n for n in ast.walk(ast.parse(producer)) if isinstance(n,ast.FunctionDef) and n.name=='config_hashes')
expected="""def config_hashes():
    settings = get_settings()
    return {name: hashlib.sha256(str(os.environ.get(name, '') if name == 'DATABASE_URL' else getattr(settings, name)).encode()).hexdigest() for name in ['SECRET_KEY', 'MFA_ENCRYPTION_KEY', 'DATABASE_URL', 'BASE_URL', 'GOOGLE_CLIENT_ID', 'STRIPE_SECRET_KEY', 'REDIS_URL']}
"""
assert ast.dump(function)==ast.dump(ast.parse(expected).body[0])
names=['SECRET_KEY','MFA_ENCRYPTION_KEY','DATABASE_URL','BASE_URL','GOOGLE_CLIENT_ID','STRIPE_SECRET_KEY','REDIS_URL']
synthetic={n:'Independent synthetic only '+n for n in names};synthetic['STRIPE_SECRET_KEY']='';synthetic['REDIS_URL']=''
scope={'hashlib':hashlib,'get_settings':lambda:SimpleNamespace(**synthetic),'os':SimpleNamespace(environ={'DATABASE_URL':synthetic['DATABASE_URL']})}
exec(compile(ast.Module(body=[function],type_ignores=[]),'only-pure-synthetic-function','exec'),scope)
assert scope['config_hashes']()=={n:sha(v.encode()) for n,v in synthetic.items()}
Q='docs/implementation/20261018-evolution/evidence/qa-mfa31-browser-v2-independent-20261019/'
receipts={n:json.loads((A/(Q+n)).read_bytes()) for n in ['before.json','after.json','preflight-frozen.json']}
assert all(v['helpers']['server_adapter.py']==producer_digest for v in receipts.values())
ready=json.loads((A/(Q+'owned-ready.json')).read_bytes());closure=json.loads((A/(Q+'resource-closure.json')).read_bytes())
log=json.loads((A/(Q+'server.stdout.raw.log')).read_bytes().split(b'\n')[1])
assert ready==closure['actual_server_ready']==log
assert set(ready['config_hashes'])==set(names) and all(re.fullmatch('[a-f0-9]{64}',v) for v in ready['config_hashes'].values())
for row in phase_rows['final15']:
    proof=row['proof'];line=physical(row)
    if proof['kind'].startswith('pinned pure'):
        assert proof['producer_sha256']==producer_digest and proof['private_original_configuration_preimages_recomputed'] is False
        assert len(proof['producer_source_receipts'])==3
        for item in proof['producer_source_receipts']:assert sha((A/item['path']).read_bytes())==item['digest']
        acceptable={ready['config_hashes'][n].encode() for n in (names if row['file'].endswith('server.stdout.raw.log') else ['SECRET_KEY','MFA_ENCRYPTION_KEY','STRIPE_SECRET_KEY'])}
        assert set(re.findall(rb'[a-f0-9]{64}',line))<=acceptable
    elif proof['kind'].startswith('exact SHA256'):
        assert proof['digest'].encode() in line
        hits=[h for h in proof['witnesses'] if h['derivation']=='Git_blob_bytes'];assert hits
        for hit in hits:
            oid=hit['Git_blob_oid'];assert objects[oid]['variants']['Git_blob_bytes']==proof['digest']
            assert objects[oid]['UTF16_BOM'] and any((oid,p) in pairs for p in hit['paths'])
    elif proof['kind'].startswith('SHA256 of retained public'):
        assert proof['digest']==sha(key) and sha((A/proof['witness']).read_bytes())==proof['digest'] and proof['digest'].encode() in line
    else:
        loop=ast.parse(line.decode()+'\n    pass\n').body[0];assert isinstance(loop,ast.For)
        entries=ast.literal_eval(loop.iter);assert len(entries)==len(proof['witnesses'])==2
        for entry,item in zip(entries,proof['witnesses'],strict=True):
            assert entry[2]==item['digest']==sha((A/item['path']).read_bytes())
    verified.append(('final15',row))
assert Counter((p,coords(r)) for p,r in verified)==Counter((r['candidate_phase'],coords(r)) for r in rows)

ledger=[{'file':r['file'],'line':r['line'],'rule':r['rule'],'RAW_SHA256':r['file_sha256'],
         'scanner_SHA256':file_proofs[r['file']]['scanner_SHA256'],'physical_line_SHA256':sha(physical(r)),
         'proof_phase':p} for p,r in verified]
save('independent-ledger.json',ledger)
save('semantic-replay-summary.json',{'occurrences_verified':len(verified),'unique_pins':len(computedpins),'files':len(rawfiles),
    'phase_counts':Counter(p for p,r in verified),'public_current_targets':len(public_targets),
    'historical_blob_objects':len(objects),'pinned_commits':len(commits),'path_object_pairs':len(pairs),
    'archive_member_witnesses':len(artifact_witnesses),'object_inventory_witness_trees':len(tree_cache),
    'runtime_maps':len(map_witnesses),'runtime_pairs':sum(w['pairs'] for w in map_witnesses),
    'private_configuration_preimages_recomputed':False,'producer_only_AST_and_copied_digests_verified':True,
    'producer_AST_SHA256':sha(ast.dump(function).encode()),'pure_producer_source_SHA256':producer_digest,
    'public_header_URL':url,'public_header_SHA256':sha(header),'public_header_bytes':len(header),
    'public_key_retained_SHA256':sha(key),'new_scanner_execution':False,'registry_installed':False})
baseline=P/'snapshot';baseline.mkdir()
for name,payload in snapfiles.items():
    path=baseline/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
config=(A/'.gitleaks.toml').read_bytes();assert sha(config)==data['config_digest']
(baseline/'.gitleaks.toml').write_bytes(config);(baseline/'candidate-reviewed-locations.zip').write_bytes(dataset_raw)
save('countercanary-input-binding.json',{'snapshot':str(baseline),'files':file_proofs,'candidate_digest':sha(dataset_raw),
    'configuration_digest':sha(config),'final15_coordinates':[{'file':r['file'],'line':r['line'],'rule':r['rule']} for r in phase_rows['final15']],
    'producer_AST_SHA256':sha(ast.dump(function).encode()),'producer_source_SHA256':producer_digest})
after=photo();save('after-semantic.json',after);assert after==before
assert REPORT.read_bytes()==report_raw and producer_path.read_bytes()==producer
print(json.dumps({'semantic_occurrences':len(verified),'unique_pins':len(pins),'files':len(rawfiles),'source_packages_Python_quiet':True,
    'producer_preimages_reconstructed':False,'registry_installed':False,'new_scan':False}))
