"""File-only validation/statistics after the exclusive PostgreSQL window is closed."""
import hashlib
import json
import math
from pathlib import Path

OUT=Path(__file__).resolve().parent;RUN=OUT/'run-66d9dec-20261019T1112'
ROOT=Path(r'F:/MetodoBaseWeb-execution-20261018')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
def save(name,value):
    with (OUT/name).open('x',encoding='utf8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def q(values):
    values=sorted(values);n=len(values)
    return {'n':n,'min':values[0],'p50':values[math.ceil(.5*n)-1],'p95':values[math.ceil(.95*n)-1],'max':values[-1]}

prep=load(OUT/'preparation-manifest.json')
assert all(sha(OUT/name)==digest for name,digest in prep['files'].items())
old=load(OUT/'baseline-historical1000-selection.json')
base=Path(old['original_prefix'])
assert all(sha(base/name)==digest for name,digest in old['original_files_sha256'].items())
before,after=load(OUT/'execution-before-photo.json'),load(OUT/'execution-after-photo.json')
assert before==after and before['head']=='66d9dec0e15dd873038bd248d3883daeeb27d4ca'
assert before['driver_sha256']=='4592fb1782e6d19ee1ff61f65d59eb63583313e3d109875ae29a13c5082dca10'
report=load(RUN/'report.json');samples=load(RUN/'samples.json');cleanup=load(OUT/'execution-cleanup-confirmed.json')
assert report['outcome']=='characterized' and report['sources_stable'] and report['schema_revision']=='20261019_account_recovery'
assert report['seed']['personal_subjects']==report['seed']['personal_profiles']==1
assert report['seed']['personal_plans']==1000 and report['seed']['plan_content_utf8_bytes']==762
assert len(samples)==200 and len({row['sample'] for row in samples})==200
assert report['observer_flush']['expected']==report['observer_flush']['observed']==200 and report['observer_flush']['acknowledged']
assert report['excluded_http_controls']=={'auth_readiness_attempts':3,'history_warmup':1,'counted_in_measured_200':False}
assert report['cleanup']['owned_uuid_database_removed'] and cleanup['owned_uuid_database']['removed']
assert cleanup['os_postcheck']=={'processes':[],'listeners':[]}
comparisons=[]
for concurrency in [1,5]:
    selected=[row for row in samples if row['sample'].startswith('history-c'+str(concurrency)+'-')]
    historical=old['selected_samples'][str(concurrency)]
    assert len(selected)==100 and len(historical)==20
    assert all(row['cohort']==4 and row['history_rows_seeded']==1000 and row['status']==200
               and row['semantic_valid'] and row['records']==50 and row['response_bytes']==8161 and 'server' in row for row in selected)
    assert all(row['records']==1000 and row['response_bytes']==162773 for row in historical)
    comparisons.append({'concurrency':concurrency,
        'historical':{'n':20,'rows_returned':1000,'response_bytes':162773,'client_ms':q([r['client_ms'] for r in historical]),
            'source':'40 exact original matching cohort1000 samples selected without modifying baseline1400'},
        'current':{'n':100,'rows_returned':50,'response_bytes':8161,'client_ms':q([r['client_ms'] for r in selected]),
            'semantics_and_observer_complete':True},
        'inference':'Descriptive observations only. Response semantics, sample size, schema, dataset distribution and host contention differ; no causal speedup or SLO claim.'})
save('descriptive-comparison.json',{'baseline_total_preserved':1400,'baseline_matching_subset':40,'current_measured':200,
    'percentile_definition':'Nearest rank ceil(.95*n), no interpolation; original raw values preserved',
    'rows':comparisons,'no_old_flow_rerun':True,'no_other_new_measured_flow':True})

explain=load(RUN/'explain-analyze-buffers.json');query=explain['query'];plan=explain['plan'][0]
assert query['candidate_limit']==51 and query['selected_limit']==50
assert query['capture']=='first history warmup, before measured requests'
assert query['sql'].lstrip().upper().startswith('SELECT') and 'COUNT(' not in query['sql'].upper() and 'plan_json' not in query['sql'].lower()
assert explain['role']=={'superuser':False,'bypassrls':False,'createdb':False,'createrole':False}
assert explain['tenant']=='load-person-4' and explain['outside_measurement']
nodes=[]
def walk(node,depth=0):
    fields=['Node Type','Relation Name','Index Name','Join Type','Actual Rows','Actual Loops','Sort Key','Sort Method',
        'Sort Space Used','Sort Space Type','Shared Hit Blocks','Shared Read Blocks','Temp Read Blocks','Temp Written Blocks']
    nodes.append({'depth':depth,**{key:node[key] for key in fields if key in node}})
    for child in node.get('Plans',[]):walk(child,depth+1)
walk(plan['Plan'])
assert plan['Plan']['Actual Rows']==51
save('explain-reading.json',{'original_explain_sha256':sha(RUN/'explain-analyze-buffers.json'),
    'execution_time_ms':plan['Execution Time'],'planning_time_ms':plan['Planning Time'],'nodes':nodes,
    'observed':'Limit51 over top-N heapsort31kB over1000 rows. BitmapAnd of deleted/gym_id indexes; clientes indexed join repeated1000times.2120shared hits,0shared reads,0tempIO.',
    'current_declared_model_index':{'name':'ix_planes_gym_fecha','columns':['gym_id','fecha_generacion'],
        'source':'web/database/models.py:261; initial migration and frozen target28 retain the same two columns'},
    'index_not_used_in_this_plan':'ix_planes_gym_fecha',
    'interpretation':'Returned candidates and Python materialization bounded51; this observed database plan still scans/sorts1000 and repeats profile lookup1000. This is not proof of O(50) database work.',
    'decision_pending':'One hot synthetic1tenant plan is insufficient to choose physical DDL or attribute index causality. No index/migration changed or proposed by QA; further evaluation requires its own scope/window.'})

summary={'characterization_complete':True,'latency_slo_acceptance':False,'head':before['head'],'driver_sha256':before['driver_sha256'],
    'preparation_head_retained':'52af40007eed53d32d0dca06b06b44dcbf7c64f3','execution_head_addendum':load(OUT/'execution-head-addendum.json'),
    'source_count':737,'packages':89,'source_and_package_before_after_identical':True,'pip_checks':[0,0],
    'selection':{'route':'GET /api/usuario/historial?limit=50','subjects':1,'profiles':1,'stored_plans':1000,
        'concurrency':[1,5],'measured_each':100,'measured_total':200,'statuses':{'200':200},'semantic_failures':0,
        'observer_missing':0,'observations_acknowledged':200,'returned_rows_each':50,'response_bytes_each':8161},
    'excluded_controls':report['excluded_http_controls'],'readiness_note':'3 auth/readiness attempts, not3 guaranteed HTTP responses; only final response200 is asserted. Exactly1 history warmup excluded.',
    'descriptive_comparison':comparisons,'scenarios_original':report['scenarios'],
    'explain':{'file':'run-66d9dec-20261019T1112/explain-analyze-buffers.json','reading':'explain-reading.json',
        'after_measured_windows':True,'actual_rows':51,'same_restricted_role_and_tenant':True},
    'cleanup':cleanup,'schema_revision':report['schema_revision'],'postgres_version':report['postgres_version'],
    'baseline1400_unchanged':True,'preparation14_files_unchanged':True,
    'slo_and_followup_pending':['Agreed numerical objectives and representative arrival/workload model',
        'Comparable production environment/capacity evidence','Separate physical-index decision and controlled validation if authorized'],
    'limits':report['limitations'],'no_causal_p95_claim':True,'no_additional_pg_or_http_after_cleanup':True,
    'no_runtime_test_ci_or_git_mutation_by_qa':True,'scope':'One authorized Windows native PostgreSQL loopback characterization. No other routes, old1400 replay, migrations/index edits, providers, image/Linux/TCG/production performance acceptance.'}
save('final-summary.json',summary)
files={path.relative_to(OUT).as_posix():sha(path) for path in sorted(OUT.rglob('*')) if path.is_file()}
save('final-manifest.json',{'files':files,'count':len(files),'scope':'All preparation and execution artifacts in this prefix except self; no private env.json, URL or token serialized.'})
print(json.dumps({'characterization_complete':True,'head':before['head'],'measured':200,
    'p95_ms':[row['current']['client_ms']['p95'] for row in comparisons],
    'summary_sha256':sha(OUT/'final-summary.json'),'manifest_sha256':sha(OUT/'final-manifest.json'),'files':len(files)}))
