from support import *
import xml.etree.ElementTree as ET
mode=sys.argv[1];assert mode in ['focal21','regression98']
phase=TEMP/mode;phase.mkdir();origin=phase/'origin';origin.mkdir();env=environment();env.update(QA_HISTORY30_MODULE_ORIGIN_OUT=str(origin),R24_FAILURE_OUTPUT=str(phase/'proofs'))
modules=['tests/test_diary_private_headers.py',str(TEMP/'test_r24_failure_privacy.py'),str(TEMP/'test_r24_own_http_v3.py')]if mode=='focal21'else ['tests/test_personal_diary_values.py','tests/test_personal_diary_persistence.py','tests/test_personal_diary_boundaries.py','tests/integration_client_link_http.py::test_http_explicit_publication_and_exact_old_pdf_replacement','tests/integration_client_link_http.py::test_member_get_plan_list_and_export_have_no_business_dml_or_commit','tests/integration_client_link_http.py::test_publication_lost_commit_ack_requires_fresh_exact_observation_before_replacement']
before=photo(mode+'-before');own={p.name:sha(p.read_bytes())for p in TEMP.glob('test_*.py')};args=[str(PYTHON),'-X','utf8','-B','tests/run_isolated.py','-p','qa_r24_origin','--rootdir='+str(ROOT),'--import-mode=importlib',*modules,'-q','--tb=short','--junitxml='+str(phase/'junit.xml')]
if mode=='regression98':args+=['-k','not postgresql']
with (phase/'stdout.raw.log').open('xb')as stdout,(phase/'stderr.raw.log').open('xb')as stderr:result=subprocess.run(args,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=1800)
save(mode+'-child-exit.json',{'exit':result.returncode,'command':args})
after=photo(mode+'-after');assert before==after and own=={p.name:sha(p.read_bytes())for p in TEMP.glob('test_*.py')}
cases=ET.parse(phase/'junit.xml').findall('.//testcase');nonpass=[{'name':c.get('name'),'classname':c.get('classname')}for c in cases if any(c.find(t)is not None for t in ['failure','error','skipped'])]
counts={}
for case in cases:counts[case.get('classname')]=counts.get(case.get('classname'),0)+1
outputs=[publish(p,mode+'-'+p.relative_to(phase).as_posix().replace('/','--'))for p in sorted(phase.rglob('*'))if p.is_file()]
save(mode+'-result.json',{'head':HEAD,'exit':result.returncode,'total':len(cases),'passed':len(cases)-len(nonpass),'nonpass':nonpass,'module_counts':counts,'source_files':before['source_count'],'packages':89,'source_helpers_packages_stable':True,'own_tests_before_after':own,'outputs':outputs})
print(json.dumps({'mode':mode,'exit':result.returncode,'total':len(cases),'passed':len(cases)-len(nonpass),'nonpass':nonpass,'module_counts':counts,'sources':before['source_count'],'packages':89,'stable':True}),flush=True)
assert result.returncode==0 and not nonpass
assert len(cases)==(21 if mode=='focal21'else 98)
