"""Freeze index30 code and exact/explicitly redacted author evidence."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path('F:/mb-hidx-20261019')
TEMP=Path('C:/Users/Consu/AppData/Local/Temp')
EV=ROOT/'docs/implementation/20261018-evolution/evidence/history30-author-20261019'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=ROOT,**kwargs)
BASE='aa9c3b84a9489f2ed845827c37ccaa77cc3ceb06'
assert git('rev-parse','HEAD',text=True).strip()==BASE
assert not git('diff','--cached','--name-only')
source_names=sorted(set(git('ls-files','-m','-o','--exclude-standard','-z').decode().split('\0')[:-1]))
assert len(source_names)==13
source_bytes={name:(ROOT/name).read_bytes() for name in source_names}
EV.mkdir(exist_ok=False)
(EV/'.gitattributes').write_bytes(b'* -text\n')
folders={
    'before14':TEMP/'metodobase-history30-final-base-test-20261019',
    'diagnostic1':TEMP/'metodobase-history30-query-diagnostic-20261019',
    'after_query1':TEMP/'metodobase-history30-query-after-null-order-20261019',
    'final112_before_index_assertion':TEMP/'metodobase-history30-author-final-gates-20261019',
    'index_assertion_after2':TEMP/'metodobase-history30-index-expectation-focal-20261019',
}
private=TEMP/'metodobase-history30-all-author-raw-20261019.zip'
assert not private.exists()
with ZipFile(private,'x',ZIP_DEFLATED) as archive:
    for label,directory in folders.items():
        for path in sorted(directory.rglob('*')):
            if path.is_file():archive.writestr(label+'/'+path.relative_to(directory).as_posix(),path.read_bytes())
jwt=re.compile(rb'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}')
derivatives=[]
raw_copies=0
for label,directory in folders.items():
    destination=EV/label;destination.mkdir()
    for path in sorted(directory.rglob('*')):
        if not path.is_file():continue
        original=path.read_bytes()
        public,count=jwt.subn(b'SYNTHETIC_JWT_REDACTED',original)
        output=destination/path.relative_to(directory)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_bytes(public)
        if count:
            derivatives.append({'public':output.relative_to(EV).as_posix(),'private_original':str(path),
                'original_sha256':sha(original),'public_derivative_sha256':sha(public),
                'synthetic_JWT_occurrences_redacted':count,'rule':'Complete ephemeral synthetic JWTs from failed TestClient fixture repr only. Original bytes remain in private sealed ZIP. No claim public derivative is RAW.'})
        else:raw_copies+=1
summaries={label:json.loads((path/'summary.json').read_bytes()) for label,path in folders.items()}
assert (summaries['before14']['cases'],summaries['before14']['failures'])==(14,1)
assert (summaries['diagnostic1']['cases'],summaries['diagnostic1']['failures'])==(1,1)
assert (summaries['after_query1']['cases'],summaries['after_query1']['failures'])==(1,0)
assert (summaries['final112_before_index_assertion']['cases'],summaries['final112_before_index_assertion']['failures'])==(112,2)
assert (summaries['index_assertion_after2']['cases'],summaries['index_assertion_after2']['failures'])==(2,0)
for summary in summaries.values():
    assert summary['errors']==summary['skipped']==0 and summary['sources_stable'] and summary['packages_stable'] and summary['pip_checks_zero']
final_sources=json.loads((folders['final112_before_index_assertion']/'after-source.json').read_bytes())
focal_sources=json.loads((folders['index_assertion_after2']/'after-source.json').read_bytes())
changed=[name for name in final_sources if final_sources[name]!=focal_sources[name]]
assert changed==['tests/test_personal_history_pagination.py'],changed
assert final_sources.keys()==focal_sources.keys()
closures=[json.loads(line) for line in (folders['final112_before_index_assertion']/'owned-database-closures.jsonl').read_text().splitlines()]
assert len(closures)==8 and all(row['removed_and_absence_checked'] for row in closures)
observed=json.loads((folders['after_query1']/'ordered-query-postgresql.json').read_bytes())
assert [row['plan_rows_visited'] for row in observed]==[51,52,51,51,51]
before_zip=TEMP/'metodobase-history30-before-null-order-fix-20261019.zip'
assert sha(before_zip.read_bytes())=='d5e91c886e40714bc95b29962372db3fc1028336844162b46e90ceefa1507ed3'
shutil.copyfile(before_zip,EV/'candidate-before-null-order-fix.zip')
scripts=['metodobase-history30-final-base-test-20261019.py','metodobase-history30-query-diagnostic-20261019.py','metodobase-history30-query-after-null-order-20261019.py','metodobase-history30-author-final-gates-20261019.py','metodobase-history30-index-expectation-focal-20261019.py','metodobase-history30-before-null-order-fix-20261019.py']
(EV/'drivers').mkdir()
for name in scripts:shutil.copyfile(TEMP/name,EV/'drivers'/name)
shutil.copyfile(TEMP/'metodobase-history30-index-expectation-proof-20261019.json',EV/'index-expectation-AST-proof.json')
shutil.copyfile(TEMP/'metodobase-history30-pagination-before-index-expectation-20261019.py',EV/'pagination-test-before-index-expectation.py')
shutil.copyfile(__file__,EV/'freeze-driver.py')
receipt={
    'state':'AUTHOR_CANDIDATE_READY_FOR_INDEPENDENT_QA; not integrated',
    'base_commit':BASE,'predecessor_core':'1aacbcb5e9d0a1ba0b2a08d5c3650e4bd9ff7ce6',
    'restore_stable_predicates_commit':'6ec3f04fab18d21f28c63bb864a9398f23e5dcce',
    'source_files':{name:{'bytes':len(raw),'sha256':sha(raw)} for name,raw in source_bytes.items()},
    'author_current_criteria':112,'one_all_green_112_run':False,
    'composition':'Same final product:110green in112run plus two old-index-assertion cases retargeted and replayed green; the only changed source is that maintained test. No test dropped/filtered from final count. Independent full112 replay requested.',
    'run_summaries':summaries,'only_source_changed_between112_and2':changed,
    'actual_final_owned_pg_databases_removed_and_absence_checked':8,
    'query_work_observations':[{'case':row['case'],'plan_rows_visited':row['plan_rows_visited'],'budget':row['max_candidates']} for row in observed],
    'true_before_defect':'Undated branch used backward primary key, visited107plan rows>102budget in mixed tied corpus. Same criterion after explicit id DESC NULLS LAST and full branch ordering passed; no planner knobs/statistics-cost adjustments.',
    'quality':{'lint':0,'syntax':0,'parsed_Python':486,'security':0,'historical_Bandit_findings':6,'new_Bandit_findings':0},
    'native_SQLite_and_PG_migration30_rollback_drift':True,
    'exact_public_RAW_copies':raw_copies,'explicit_redacted_derivatives':derivatives,
    'private_exact_RAW_zip':str(private),'private_exact_RAW_zip_sha256':sha(private.read_bytes()),
    'limits':['No API29/restore29/UI acceptance','No HTTP p95/SLO or universal planner work bound','No MAIN merge/production operation','Code passed under photographed working bytes; staging receipt discloses any EOL-only differences'],
}
(EV/'freeze.json').write_bytes((json.dumps(receipt,indent=2,ensure_ascii=False)+'\n').encode())
manifest={p.relative_to(EV).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(EV.rglob('*')) if p.is_file()}
(EV/'manifest.json').write_bytes((json.dumps({'files':manifest,'file_count':len(manifest)},indent=2)+'\n').encode())
for name,raw in source_bytes.items():assert (ROOT/name).read_bytes()==raw
subprocess.run(['git','-c','core.autocrlf=true','add','--',*source_names],cwd=ROOT,check=True,capture_output=True)
proof_names=sorted(p.relative_to(ROOT).as_posix() for p in EV.rglob('*') if p.is_file())
for offset in range(0,len(proof_names),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*proof_names[offset:offset+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',EV.relative_to(ROOT).as_posix()],cwd=ROOT,check=True,capture_output=True)
eol=[]
for name,raw in source_bytes.items():
    blob=git('show',':'+name)
    if blob!=raw:
        assert blob==raw.replace(b'\r\n',b'\n'),name
        if name.endswith('.py'):
            assert ast.dump(ast.parse(blob.decode('utf-8')),include_attributes=False)==ast.dump(ast.parse(raw.decode('utf-8')),include_attributes=False)
        eol.append({'path':name,'RAW_sha256':sha(raw),'Git_LF_sha256':sha(blob),'only_CRLF_to_LF':True})
stage=EV/'staging-EOL-receipt.json'
stage.write_bytes((json.dumps({'source_EOL_only_paths':eol,'all_other_source_Git_blobs_RAW_exact':True,'proof_files_Git_RAW_or_explicit_derivative_exact':True,'author_tests_were_on_photographed_RAW_bytes':True},indent=2)+'\n').encode())
subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',stage.relative_to(ROOT).as_posix()],cwd=ROOT,check=True,capture_output=True)
proof_names.append(stage.relative_to(ROOT).as_posix());proof_names.sort()
buffer=git('cat-file','--batch',input=''.join(':'+name+'\n' for name in proof_names).encode())
cursor=0
for name in proof_names:
    end=buffer.index(b'\n',cursor);parts=buffer[cursor:end].split();assert parts[1]==b'blob'
    size=int(parts[2]);cursor=end+1
    assert buffer[cursor:cursor+size]==(ROOT/name).read_bytes(),name
    cursor+=size+1
assert cursor==len(buffer)
assert not git('diff','--cached','--check','--',*source_names,stderr=subprocess.STDOUT)
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(source_names+proof_names)
subprocess.run(['git','commit','-m','Bound ordered personal history with verified revision30 index'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'freeze_sha256':sha((EV/'freeze.json').read_bytes()),'manifest_sha256':sha((EV/'manifest.json').read_bytes()),'source_paths':len(source_names),'proofs_byte_preserved':len(proof_names),'EOL_only_source_paths':len(eol),'public_derivative_count':len(derivatives),'product_mutation_in_MAIN':False}))
