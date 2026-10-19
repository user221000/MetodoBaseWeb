"""Classify finite retained metadata, never claim to recover missing WIP bytes."""
from pathlib import Path
import ast,hashlib,json
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp');PRIVATE=TEMP/'metodobase-sec-gitleaks-peer-private-20261019'
SOURCE=Path(r'F:/mb-progress-retirement-ui-20261019');EVIDENCE=SOURCE/'docs/implementation/20261018-evolution/evidence'
sha=lambda b:hashlib.sha256(b).hexdigest()
def function(raw,name):return next(n for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.FunctionDef) and n.name==name)
public_mfa=EVIDENCE/'backend-mfa31-author/run-pg-initial-unguarded.py'
retained_mfa=TEMP/'metodobase-mfa31-author-20261019/run_pg.py'
a=function(public_mfa.read_bytes(),'photo');b=function(retained_mfa.read_bytes(),'photo')
assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
public_alias=EVIDENCE/'backend-mfa31-alias-key-fix/replay-orchestrator.py'
retained_alias=TEMP/'metodobase-mfa31-alias-author-ybbtkfsn/replay.py'
assert public_alias.read_bytes()==retained_alias.read_bytes()
c=function(public_alias.read_bytes(),'photograph')
expected="hashlib.sha256((ROOT / name).read_bytes()).hexdigest()"
for node in [a,b,c]:
    assert len(node.args.args)==0 and len(node.body)==2 and isinstance(node.body[1],ast.Return) and isinstance(node.body[1].value,ast.DictComp)
    assert isinstance(node.body[1].value.key,ast.Name) and node.body[1].value.key.id=='name'
    assert ast.unparse(node.body[1].value.value)==expected
    assert not any(isinstance(n,ast.Name) and n.id in {'config','os','environ','SECRET_KEY','token','credential'} for n in ast.walk(node))
freeze=json.loads((EVIDENCE/'backend-mfa31-author/freeze.json').read_bytes())
rows=json.loads((PRIVATE/'unresolved-v3.STRUCTURAL.json').read_bytes());expected_values=json.loads((PRIVATE/'expected-source-checksums.private.json').read_bytes())
proofs=[]
for row in rows:
    if row['value_type']!='hex64' or row.get('matched_field_structure') in {'Apia','current_api_sha256'}:continue
    path=SOURCE/row['file'];raw=path.read_bytes();assert sha(raw)==row['file_sha256']
    # These retained source photographs are UTF8 JSON, with physical CRLF
    # accepted only as a checkout representation after checking the raw pin.
    text=raw.decode('utf8');data=json.loads(text)
    assert all(isinstance(k,str) and isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v) for k,v in data.items())
    assert text.replace('\r\n','\n')==json.dumps(data,indent=2)+'\n'
    target=next(k for k,v in data.items() if sha(v.encode())==row['matched_value_sha256'])
    assert target in expected_values and data[target]==expected_values[target]
    filename=path.name
    suffix='-source-before.json' if filename.endswith('-source-before.json') else '-source-after.json'
    assert filename.endswith(suffix);label=filename[:-len(suffix)]
    before=path.with_name(label+'-source-before.json');after=path.with_name(label+'-source-after.json');summary=path.with_name(label+'-summary.json')
    x=json.loads(before.read_bytes());y=json.loads(after.read_bytes());receipt=json.loads(summary.read_bytes())
    assert x==y and receipt['source_files']==len(x) and receipt['packages']==89
    if 'backend-mfa31-alias-key-fix' in row['file']:
        assert receipt['sources_quiet'] and receipt['packages_quiet'] and receipt['label']==label
        root=TEMP/'metodobase-mfa31-alias-author-ybbtkfsn'
        log=path.with_name(label+'.log');assert sha(log.read_bytes())==receipt['stdout_sha256']
        raw_kind='public_replay_orchestrator_exact_to_retained_replay'
        producer_hash=sha(public_alias.read_bytes());producer_function_hash=sha(ast.dump(c).encode())
        execution_link={'public_summary_sha256':sha(summary.read_bytes()),'public_log_sha256_matches_summary':True,'before_after_dictionaries_equal':True,'source_count':len(x),'packages':89}
    else:
        assert receipt['source_stable'] and receipt['packages_stable']
        private_log=TEMP/'metodobase-mfa31-author-20261019'/(label+'.raw.log')
        assert sha(private_log.read_bytes())==receipt['log_raw_sha256']
        # freeze.json records these complete metadata files before Git freeze.
        key=path.relative_to(SOURCE).as_posix();entry=freeze['proofs'][key]
        frozen_hash=entry['raw_sha256']
        assert frozen_hash in {sha(raw),sha(raw.replace(b'\r\n',b'\n'))}
        raw_kind='frozen_initial_public_photo_AST_equals_retained_final_photo_AST'
        producer_hash=sha(public_mfa.read_bytes());producer_function_hash=sha(ast.dump(a).encode())
        execution_link={'public_summary_sha256':sha(summary.read_bytes()),'retained_raw_log_sha256_matches_summary':True,'freeze_receipt_metadata_file_pin_matches':True,'before_after_dictionaries_equal':True,'source_count':len(x),'packages':89}
    proof={'kind':'verified_producer_checksum_metadata_missing_original_WIP_source','producer_binding':raw_kind,'public_producer_sha256':producer_hash,
        'photo_function_ast_sha256':producer_function_hash,'source_path':target,'dict_value_algorithm':expected,'no_configuration_or_token_passthrough_in_photo':True,
        'whole_metadata_file_sha256':sha(raw),'physical_line_sha256':row['physical_line_sha256'],'execution_receipt':execution_link,
        'limitation':'Original WIP source bytes at this checksum are unavailable. This establishes the finite pinned value as producer checksum metadata, not recomputation of its preimage, reconstructed execution RAW, a reproduced historical test, or complete historical QA lineage.'}
    proofs.append({**row,'proof':proof})
assert len(proofs)==16
target=PRIVATE/'producer-proofs.STRUCTURAL.json';target.write_text(json.dumps(proofs,indent=2)+'\n',encoding='utf8')
print(json.dumps({'locations':len(proofs),'source_paths':sorted({p['proof']['source_path'] for p in proofs}),'pure_SHA256_generator_verified':True,'configuration_passthrough':False,'original_WIP_source_recomputed':False}))
