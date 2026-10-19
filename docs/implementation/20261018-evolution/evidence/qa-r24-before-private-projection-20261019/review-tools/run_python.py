from support import *
import xml.etree.ElementTree as ET
mode=sys.argv[1];assert mode in ['r24-sqlite','regression','pg2']
phase=TEMP/mode;phase.mkdir();origin=phase/'origin';origin.mkdir();env=environment(mode=='pg2');env.update(QA_HISTORY30_MODULE_ORIGIN_OUT=str(origin),R24_RAW_OUTPUT=str(phase/'SSR'),R24_PG_OUTPUT=str(phase/'PG'))
modules=['tests/test_publication_diary_consumption.py','tests/test_daily_plan_ui_contract.py']if mode=='r24-sqlite'else ['tests/integration_daily_plan_publication.py']if mode=='pg2'else ['tests/test_personal_diary_values.py','tests/test_personal_diary_persistence.py','tests/test_personal_diary_boundaries.py','tests/integration_client_link_http.py::test_http_explicit_publication_and_exact_old_pdf_replacement','tests/integration_client_link_http.py::test_member_get_plan_list_and_export_have_no_business_dml_or_commit','tests/integration_client_link_http.py::test_publication_lost_commit_ack_requires_fresh_exact_observation_before_replacement']
before=photo(mode+'-before');args=[str(PYTHON),'-X','utf8','-B','tests/run_isolated.py','-p','qa_r24_origin',*modules,'-q','--tb=short','--junitxml='+str(phase/'junit.xml')]
if mode=='regression':args+=['-k','not postgresql']
with (phase/'stdout.raw.log').open('xb')as stdout,(phase/'stderr.raw.log').open('xb')as stderr:result=subprocess.run(args,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=300)
save(mode+'-child-exit.json',{'exit':result.returncode,'command':args})
after=photo(mode+'-after');assert before==after
cases=ET.parse(phase/'junit.xml').findall('.//testcase');outcomes={'total':len(cases),'failed':sum(c.find('failure')is not None for c in cases),'errors':sum(c.find('error')is not None for c in cases),'skipped':sum(c.find('skipped')is not None for c in cases)}
counts={}
for case in cases:counts[case.get('classname')]=counts.get(case.get('classname'),0)+1
outputs=[publish(p,mode+'-'+p.relative_to(phase).as_posix().replace('/','--'))for p in sorted(phase.rglob('*'))if p.is_file()]
save(mode+'-result.json',{'head':HEAD,'exit':result.returncode,'cases':outcomes,'module_counts':counts,'source_files':before['source_count'],'packages':89,'source_helpers_packages_stable':True,'outputs':outputs})
print(json.dumps({'mode':mode,'exit':result.returncode,'cases':outcomes,'module_counts':counts,'sources':before['source_count'],'packages':89,'stable':True}),flush=True)
assert result.returncode==0 and outcomes['failed']==outcomes['errors']==outcomes['skipped']==0
if mode=='r24-sqlite':assert len(cases)==31
if mode=='pg2':assert len(cases)==2
