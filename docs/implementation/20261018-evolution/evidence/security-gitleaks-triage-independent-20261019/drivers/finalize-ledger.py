"""Finite reviewed locations and a streaming quiet check; no scanner change."""
from pathlib import Path,PurePosixPath
from collections import Counter,defaultdict
import hashlib,json,subprocess
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp')
PRIVATE=TEMP/'metodobase-sec-gitleaks-peer-private-20261019'
ROOT=Path(r'F:/mb-security-gitleaks-triage-peer-20261019')
SOURCE=Path(r'F:/mb-progress-retirement-ui-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-gitleaks-triage-independent-20261019'
REPORT=TEMP/'metodobase-retirement-ui-scan-7c_07ul3/secret-scan-full.json'
PIN='0e5d0cfc77c1626912beca8c9b39e91fe56464e9e9cc71502947e44288b09352'
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
def streamsha(path):
    h=hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
report_raw=REPORT.read_bytes();assert sha(report_raw)==PIN
report=json.loads(report_raw)
base=json.loads((OUT/'independent-verified-checksum-locations.json').read_bytes())
additional=json.loads((OUT/'additional-classified-locations.STRUCTURAL.json').read_bytes())
producer=json.loads((PRIVATE/'producer-proofs.STRUCTURAL.json').read_bytes())
assert len(base)==31282 and len(additional)==266 and len(producer)==16
old_pending=json.loads((OUT/'unresolved-locations.STRUCTURAL.json').read_bytes())
fields=('file','line','rule','file_sha256')
key=lambda row:tuple(row[k] for k in fields)
assert Counter(map(key,producer))==Counter(map(key,old_pending))
save('producer-proofs.STRUCTURAL.json',producer)
final=additional+producer
save('additional-final-classified-locations.STRUCTURAL.json',final)
save('original-source-unavailable.STRUCTURAL.json',[{'file':p['file'],'line':p['line'],'rule':p['rule'],'file_sha256':p['file_sha256'],'physical_line_sha256':p['physical_line_sha256'],'original_source_path':p['proof']['source_path'],'limitation':p['proof']['limitation']} for p in producer])
assert Counter(map(key,base+final))==Counter(map(key,report['findings']))
ledger=[];groups=defaultdict(list)
for row in base+final:groups[row['file']].append(row)
for name,rows in groups.items():
    assert PurePosixPath(name).as_posix()==name and not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
    raw=(SOURCE/name).read_bytes();assert sha(raw)==report['files'][name]
    transform=report['encoding_transforms'].get(name)
    text=raw.decode(transform['source_encoding'] if transform else 'utf-8',errors='strict')
    if transform:assert sha(text.encode())==transform['scanner_sha256']
    lines=text.split('\n')
    for row in rows:
        line=lines[row['line']-1]
        old_expected=sha(line.rstrip('\r').encode()) if row.get('proof_type') else sha(line.encode())
        assert row['physical_line_sha256']==old_expected
        ledger.append({'file':name,'file_sha256':row['file_sha256'],'start_line':row['line'],'end_line':row['line'],'rule_id':row['rule'],'physical_line_sha256':sha(line.encode()),'proof_type':row.get('proof_type') or row['proof']['kind']})
ledger_data={'schema':1,'input_report_sha256':PIN,'binary_version':'8.30.1','binary_sha256':'17157e2ee8b76fc8b1d8bee607a250e34b8a8023c8bc81822d4b5ee4d78fcb7c','config_sha256':'fade668c58cf3310a4bde299c32c051cd271bf2cf648634bf45e67d19a372099','count':len(ledger),'physical_line_digest_definition':'SHA256 of exact decoded physical line UTF8 bytes, split on LF retaining CR, without LF terminator. Independently recomputed here. Earlier 31282-checksum receipts remove trailing CR in their separate physical_line_sha256 field; those fields must not be substituted.','encodings':{name:report['encoding_transforms'].get(name,{'source_encoding':'utf-8','scanner_encoding':'utf-8','scanner_sha256':report['files'][name]}) for name in groups},'scope':'Only 31564 reviewed remaining findings in fixed report; original two fragment pins are separate. Only raw file digest observed at this snapshot; no alternative LF/CRLF/BOM file digests approved by this ledger. No scanner implementation or global acceptance.','locations':ledger}
save('finite-reviewed-location-ledger.json',ledger_data)
before=json.loads((OUT/'attempt-initial/source-before.json').read_bytes())
assert before['scanned_files']==report['files']
after={};changed=[]
for i,(name,digest) in enumerate(report['files'].items(),1):
    path=SOURCE/name;assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(SOURCE)
    actual=streamsha(path);after[name]=actual
    if actual!=digest:changed.append(name)
    if i%2000==0:print(json.dumps({'streamed_files':i}),flush=True)
paths=subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z'],cwd=SOURCE).decode().split('\0')
observed={name for name in paths if name and (SOURCE/name).is_file()}
added=sorted(observed-set(report['files']));missing=sorted(set(report['files'])-observed)
save('source-set-delta.json',{'initial_existing_files':len(report['files']),'final_existing_files':len(observed),'added_outside_fixed_report_scope':added,'missing_original_files':missing,'original_files_changed':changed,'initial_complete_tree_photo_not_claimed_for_newly_present_paths':True})
assert not changed and not missing
authentication=json.loads((OUT/'input-authentication.json').read_bytes())
for phase,files in authentication['phase_files'].items():
    for name,entry in files.items():assert streamsha(TEMP/phase/name)==entry['sha256']
save('source-after.json',{'source':before['source'],'scanned_files':after,'files':len(after),'changed_files':changed,'original_fixed_report_existing_file_set_contained':True,'whole_existing_file_set_exact':not added,'added_paths_outside_fixed_report_scope':added,'fixed_input_phase_files_quiet':True,'read_mode':'Streaming SHA256 over original bytes; no archive extraction, historical payload output, or source mutation.'})
snapshot=PRIVATE/'focal-snapshot'
entries=list(snapshot.rglob('*'));regular=[p for p in entries if p.is_file()]
for path in regular:
    name=path.relative_to(snapshot).as_posix()
    if name=='.gitleaks.toml':expected='fade668c58cf3310a4bde299c32c051cd271bf2cf648634bf45e67d19a372099'
    else:expected=report['encoding_transforms'].get(name,{}).get('scanner_sha256',report['files'][name])
    assert streamsha(path)==expected
save('focal-scope-correction.json',{'original_summary_files_field_counts_entries_including_directories':True,'entries':len(entries),'regular_files_including_exact_config':len(regular),'source_files_excluding_config':len(regular)-1,'snapshot_bytes_match_fixed_report_or_explicit_reported_encoding_transform':True,'original_exit':1,'original_findings':993,'all_fixed282_reproduced':True,'not_a_full_tree_scan':True})
summary={'original_remaining_input':31564,'original_root_checksums_independently_verified':31282,'additional_locations_verified':282,'remaining_unclassified_secret_triage':0,'total_verified_false_positive_locations':31564,'additional_by_proof_kind':Counter(row['proof']['kind'] for row in final),'original_WIP_source_unavailable_locations':16,'original_WIP_source_unavailable_paths':sorted({p['proof']['source_path'] for p in producer}),'historical_WIP_preimages_recomputed':False,'global_R05_acceptance':False,'scanner_or_allowlist_changes':False,'original_raw_gitleaks_exit':1,'original_two_fragment_pins_not_reclassified':True,'provisional_266_16_files_preserved':True,'all_10378_scanned_source_files_quiet':True}
save('final-disposition-summary.json',summary)
print(json.dumps(summary),flush=True)
