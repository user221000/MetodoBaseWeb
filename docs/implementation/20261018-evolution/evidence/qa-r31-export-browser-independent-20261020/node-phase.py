from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
ROOT=Path('F:/mb-qa-browser31-20261020')
TASK=Path(__file__).resolve().parent;PRIVATE=TASK/'private'
NODE=Path('C:/Program Files/nodejs/node.exe')
DEPS=Path('F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
sha=lambda b:hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('r31_frozen_snapshot_library',Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-nutrition35-saas-20261020/phase.py'))
lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib);lib.ROOT=ROOT;lib.TASK=TASK;lib.PRIVATE=PRIVATE
def snapshot(label):
    result=lib.snapshot(label)
    result['node']={'path':str(NODE),'sha256':sha(NODE.read_bytes()),'version':subprocess.check_output([str(NODE),'--version'],text=True).strip()}
    result['Node_dependency_files']={str(p.relative_to(DEPS)):sha(p.read_bytes()) for p in sorted(DEPS.rglob('*')) if p.is_file()}
    assert len(result['Node_dependency_files'])==157
    result['QA_helpers']={p.name:sha(p.read_bytes()) for p in TASK.iterdir() if p.is_file() and p.suffix in {'.py','.cjs'}}
    (PRIVATE/(label+'-full.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
def env():
    result={key:value for key,value in os.environ.items() if key in {'SystemRoot','SYSTEMROOT','WINDIR','COMSPEC','PATHEXT','PATH'}}
    result.update({'TEMP':str(PRIVATE),'TMP':str(PRIVATE),'QA_R31_ROOT':str(ROOT),'QA_R31_PRIVATE':str(PRIVATE),'PYTHONDONTWRITEBYTECODE':'1'})
    return result
def execute(label,args,environment):
    with (PRIVATE/(label+'.stdout')).open('wb') as out,(PRIVATE/(label+'.stderr')).open('wb') as err:
        result=subprocess.run(args,cwd=ROOT,env=environment,stdout=out,stderr=err)
    return result.returncode
before=snapshot('before');lib.pipcheck('before')
print(json.dumps({'started':True,'head':before['head'],'source_files':len(before['source']),'packages':len(before['packages']),'Node_files':157}),flush=True)
expected={'current33_export_context':17,'current33_export_controls':21,'current33_member_link_export':32,'progress_export':38}
checks=[];all_names=[];business=[]
substitutions=[('Api.saveTokens(','__browserInvalidate('),('e.api.saveTokens(','e.invalidate('),("[...legacy.keys(),'mb_token','mb_refresh_token'].sort()","[...legacy.keys(),'mb_session_epoch'].sort()"),("if(key==='mb_token'){const error=Error('SYNTHETIC PRIVATE STORAGE')","if(key==='mb_session_epoch'){const error=Error('SYNTHETIC PRIVATE STORAGE')")]
for name,count in expected.items():
    assert execute(name+'-capture',[str(NODE),str(TASK/'capture-expanded.cjs'),name],env())==0
    current=env();current['BROWSER31_EXPORT_DEBUG_SOURCE']=str(PRIVATE/(name+'-compiled.cjs'))
    exit_code=execute(name,[str(NODE),'tests/e2e/browser_export_compat31.cjs',name],current)
    report=json.loads((PRIVATE/(name+'.stdout')).read_bytes())
    report_path=PRIVATE/(name+'.json');report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    parser=execute(name+'-parser',[sys.executable,'scripts/check_frontend_report.py',str(report_path),'--format','counts','--minimum',str(count)],env())
    assert exit_code==parser==0 and report['total']==report['passed']==count
    original=(PRIVATE/(name+'-original-expanded.cjs')).read_text(encoding='utf-8');compiled=(PRIVATE/(name+'-compiled.cjs')).read_text(encoding='utf-8')
    marker='const cases=[];';assert original.count(marker)==compiled.count(marker)==1
    original_cases=original[original.index(marker):];new_cases=compiled[compiled.index(marker):]
    allowed_cases=original_cases
    for old,new in substitutions:allowed_cases=allowed_cases.replace(old,new)
    assert allowed_cases==new_cases, name
    changes=report['browser_compatibility']['changed_transport_assertions'];assert len(changes)==1
    business.append({'wrapper':name,'entire_business_section_exact_except_four_inventoried_transport_substitutions':True,'business_assertion_calls':report['browser_compatibility']['business_assertions_preserved'],'normative_assertion_executions_changed':len(changes),'expanded_sha256':sha(original.encode()),'compiled_sha256':sha(compiled.encode())})
    all_names.extend(row['case'] for row in report['results'])
    checks.append({'name':name,'total':count,'passed':count,'exit_code':exit_code,'actual_parser_exit':parser,'report_sha256':sha(report_path.read_bytes())})
assert len(all_names)==108 and len(set(all_names))==49
negatives=[]
for mode in ('credential_write','drop_url_cleanup','consumer_throw','report_count'):
    current=env();current['QA_R31_MUTATION']=mode;receipt=PRIVATE/(mode+'-mutation.json');current['QA_R31_MUTATION_RECEIPT']=str(receipt)
    code=execute('mutant-'+mode,[str(NODE),'--require',str(TASK/'mutate-read.cjs'),'tests/e2e/browser_export_compat31.cjs','current33_export_context'],current)
    proof=json.loads(receipt.read_bytes());assert proof['applications']>0
    try:
        report=json.loads((PRIVATE/('mutant-'+mode+'.stdout')).read_bytes())
    except (ValueError,UnicodeError):report=None
    if report is not None:
        path=PRIVATE/('mutant-'+mode+'.json');path.write_text(json.dumps(report,indent=2),encoding='utf-8')
        parser=execute('mutant-'+mode+'-parser',[sys.executable,'scripts/check_frontend_report.py',str(path),'--format','counts','--minimum','17'],env())
        assert parser!=0
        failed=report['total']-report['passed']
    else:
        parser=None;failed=None
    assert code!=0
    negatives.append({'mode':mode,'mutation_applied':True,'exit_code':code,'parser_exit':parser,'reported_failed_cases':failed,'no_successful_report':True,'disk_product_mutated':False,'receipt_sha256':sha(receipt.read_bytes())})
after=snapshot('after');lib.pipcheck('after')
stable={key:before[key]==after[key] for key in before};assert all(stable.values()),stable
summary={'source_head':before['head'],'baseline_commands':checks,'replay_executions':108,'unique_case_names':49,'overlap_not_new_cases':True,'business_integrity':business,'counterexamples':negatives,'stable':stable,'source_files':len(before['source']),'packages':len(before['packages']),'installed_files':len(before['installed']),'Node_files':157,'pip_before':0,'pip_after':0,'scope':'Current source VM/DOM/Blob/Storage/Lock/cookie doubles only. No native browser, live server, PG, or SLO acceptance.'}
(TASK/'node-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({'closed':True,'replay_executions':108,'unique_case_names':49,'negative_counterexamples_rejected':len(negatives),'stable':stable}),flush=True)
