"""One actual17-module serial run; retain duplicated legacy assertions explicitly."""
import shutil,time
from support import *
phase=TEMP/'node17';phase.mkdir(exist_ok=False)
before=photo('node17-before')
node=Path(shutil.which('node')).resolve()
node_before={'executable':str(node),'sha256':sha(node.read_bytes()),'version':subprocess.check_output([str(node),'--version'],text=True).strip()}
modules=['auth_refresh','auth_refresh_storage','auth_refresh_race_review','auth_refresh_security_review',
 'personal_operation','personal_operation_ambiguity_review','personal_diary_api','personal_diary_controller',
 'personal_logout','personal_logout_ack','personal_export_controls','personal_history',
 'member_link_context','member_link_fragment','member_link_api','member_link_consumers','member_link_export']
rows=[];reports={};started=time.monotonic()
for name in modules:
    result=subprocess.run([str(node),'tests/e2e/'+name+'.cjs'],cwd=ROOT,capture_output=True,timeout=60)
    (phase/(name+'.json')).write_bytes(result.stdout)
    (phase/(name+'.stderr.log')).write_bytes(result.stderr)
    data=json.loads(result.stdout);reports[name]=data
    cases=data.get('report',data.get('results',[]))
    rows.append({'module':name,'exit':result.returncode,'total':data.get('total'),'passed':data.get('passed'),
                 'report_cases':len(cases),'all_cases_passed':all(case.get('passed') is True for case in cases)})
after=photo('node17-after')
assert node_before['sha256']==sha(node.read_bytes())
legacy=reports['personal_export_controls']['report']
wrapped=reports['member_link_export']['report']
assert wrapped[:len(legacy)]==legacy
outputs=[publish(path,'node17-'+path.name) for path in sorted(phase.iterdir()) if path.is_file()]
total=sum(row['total'] for row in rows)
value={'head':HEAD,'node':node_before,'runner_seconds':time.monotonic()-started,'results':rows,
       'assertion_executions':total,'duplicate_legacy_export_assertions':len(legacy),'unique_criteria':total-len(legacy),
       'sources_helpers_packages_stable':before==after,'sources':before['source_count'],'helpers':before['helper_count'],
       'packages':89,'outputs':outputs,'scope':'Actual serial17 Node VM reports on939. These are VM contracts, not HTTP/browser/provider execution.'}
save('node17-result.json',value)
print(json.dumps({key:value[key] for key in ['head','assertion_executions','duplicate_legacy_export_assertions','unique_criteria','sources_helpers_packages_stable','sources','helpers','packages']}))
assert total==297 and len(legacy)==21 and total-len(legacy)==276
assert before==after and all(row['exit']==0 and row['passed']==row['total'] and row['all_cases_passed'] for row in rows)
