"""Correct report-shape postprocessing, without executing any Node test again."""
from support import *
phase=TEMP/'node17'
before=json.loads((OUT/'node17-before-photo.json').read_bytes())
after=json.loads((OUT/'node17-after-photo.json').read_bytes())
assert before==after
rows=[];reports={}
for path in sorted(phase.glob('*.json')):
    data=json.loads(path.read_bytes());cases=data.get('results',data.get('report'))
    assert isinstance(cases,list) and cases
    assert all(case.get('passed') is True for case in cases)
    assert data.get('total',len(cases))==len(cases) and data.get('passed',len(cases))==len(cases)
    rows.append({'module':path.stem,'passed':len(cases),'total':len(cases),'report_array':'results' if 'results' in data else 'report',
                 'raw_sha256':sha(path.read_bytes()),'stderr_bytes':(phase/(path.stem+'.stderr.log')).stat().st_size})
    reports[path.stem]=cases
legacy=reports['personal_export_controls'];wrapped=reports['member_link_export']
assert wrapped[:len(legacy)]==legacy and len(legacy)==21
total=sum(row['total'] for row in rows)
assert len(rows)==17 and total==297
outputs=[publish(path,'node17-'+path.name) for path in sorted(phase.iterdir()) if path.is_file()]
value={'head':HEAD,'modules':rows,'assertion_executions':297,'passed_assertion_executions':297,
 'duplicate_legacy_export_assertions':21,'unique_criteria':276,'full_sources_helpers_packages_stable':True,
 'sources':before['source_count'],'helpers_during_execution':before['helper_count'],'packages':89,
 'original_driver_exit':1,'driver_exception':'KeyError: report, after all17 modules and both matching source photos',
 'original_driver_sha256':sha((OUT/'run_node17.py').read_bytes()),
 'correction':'Read each retained array by its actual results/report key; count race report2 with no top-level totals; verify21 repeated arrays byte-equivalent. No tests rerun.',
 'per_process_exit_status':'Original driver kept return codes only in memory and did not persist them before the postprocessing error. All17 complete reports assert success; no individual exit-code claim is reconstructed.',
 'public_outputs':outputs,'scope':'17 serial Node VM modules on939,297 successful assertions/276 unique criteria. Not actual HTTP/browser/provider execution.'}
save('node17-result-corrected.json',value)
print(json.dumps({'modules':len(rows),'passed_assertions':297,'unique_criteria':276,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'source_photos_equal':True,'test_reruns':0}))
