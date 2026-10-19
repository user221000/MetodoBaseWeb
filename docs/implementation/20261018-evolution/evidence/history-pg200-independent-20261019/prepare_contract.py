"""Seal preparation only: source/package/host photos and pure driver checks, no PostgreSQL/HTTP."""
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime,timezone

ROOT=Path(r'F:/MetodoBaseWeb-execution-20261018');OUT=Path(__file__).resolve().parent
BASE=ROOT/'docs/implementation/20261018-evolution/evidence/qa-load-local-final-ack'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,value):
    with (OUT/name).open('x',encoding='utf8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

names=[name for name in git('ls-files','-z').decode().split('\0') if name and not name.startswith('docs/')]
sources={name:sha(ROOT/name) for name in sorted(names)}
baseline={p.name:sha(p) for p in sorted(BASE.iterdir()) if p.is_file()}
assert baseline['harness.py.txt']=='9c540d28b2382986a83b6aa5e667d4455dc1edfe0c49bafb1dffeea50d1207ec'
assert baseline['report.json']=='4afa41df33e07dcf903186ffb6b54970bd7c8bbac838efa820e221f939682b01'
report=json.loads((BASE/'report.json').read_text(encoding='utf8'))
assert len(report['scenarios'])==14 and sum(row['completed'] for row in report['scenarios'])==1400
samples=json.loads((BASE/'samples.json').read_text(encoding='utf8'))
subset={}
for c in [1,5]:
    rows=[row for row in samples if row['cohort']==4 and row['sample'].startswith('history-c'+str(c)+'-')]
    assert len(rows)==20 and all(row['history_rows_seeded']==1000 and row['records']==1000 and row['status']==200 and row['semantic_valid'] for row in rows)
    subset[str(c)]=rows
save('baseline-historical1000-selection.json',{'original_prefix':str(BASE),'original_files_sha256':baseline,
    'original_commit':report['commit'],'original_total_measured':1400,'selected_samples':subset,
    'comparison_limits':'Only40 old matching history/cohort1000 samples (20C1/20C5); old1000-row response versus current50-row page, different schema/data-distribution/host-contention. No p95 causality or SLO equivalence.'})

spec=importlib.util.spec_from_file_location('prepared_history200_driver',OUT/'run_history200.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.request_case('history',4,None)==('/api/usuario/historial',{'limit':50},'load-person-4')
rejected=[]
for name,index in [('history',0),('latest-plan',4),('export-25',4),('diary-30',4),('clients-25',4),('clients-100',4),('client-detail',4)]:
    try:module.request_case(name,index,None)
    except ValueError:rejected.append([name,index])
    else:raise AssertionError('Unselected request accepted')
row=lambda i:{'id':i,'fecha':'2026-01-01T00:00:00','kcal_objetivo':2000,'proteina_g':120,'carbs_g':250,'grasa_g':60,'tipo_plan':'opciones','tiene_pdf':False}
valid={'planes':[row(i) for i in range(50)],'next_cursor':'synthetic-only-position'}
assert module.validate_response('history',valid,4)
assert not module.validate_response('history',{'planes':valid['planes'][:49],'next_cursor':valid['next_cursor']},4)
assert not module.validate_response('history',{'planes':valid['planes']+[row(99)],'next_cursor':valid['next_cursor']},4)
assert not module.validate_response('history',{'planes':valid['planes'],'next_cursor':None},4)
assert not module.validate_response('history',{'planes':valid['planes'],'next_cursor':valid['next_cursor'],'plan':{}},4)
help_result=subprocess.run([sys.executable,'-X','utf8',str(OUT/'run_history200.py'),'--help'],cwd=ROOT,capture_output=True,encoding='utf8')
with (OUT/'driver-help.log').open('x',encoding='utf8',newline='\n') as f:f.write(help_result.stdout+help_result.stderr)
assert help_result.returncode==0
save('pure-preparation-checks.json',{'driver_sha256':sha(OUT/'run_history200.py'),'compile_passed':True,
    'help_exit':0,'only_selected_route_and_cohort':True,'other_route_and_cohort_rejections':rejected,
    'semantics':'50unique summary rows, exact public fields, nonempty bounded cursor;49/51/missingcursor/full-plan reject',
    'database_or_http_functions_called':False,'db_created':False,'http_requests_issued':0})

packages=sorted([p.metadata['Name'],p.version] for p in importlib.metadata.distributions());assert len(packages)==89
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,encoding='utf8',timeout=30)
with (OUT/'preparation-pip-check.log').open('x',encoding='utf8') as f:f.write(pip.stdout+pip.stderr)
assert pip.returncode==0
ps="@{ os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,TotalVisibleMemorySize,FreePhysicalMemory; cpu = Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,LoadPercentage } | ConvertTo-Json -Depth 4"
host=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,encoding='utf8',timeout=30);assert host.returncode==0
environment={'utc':datetime.now(timezone.utc).isoformat(),'head_at_preparation':git('rev-parse','HEAD').decode().strip(),
    'platform':platform.platform(),'python':platform.python_version(),'python_executable':sys.executable,
    'cpu_logical':os.cpu_count(),'host':json.loads(host.stdout),'packages':packages,'package_count':89,'pip_check_exit':0,
    'sources':sources,'source_count':len(sources),'private_pg_config':'Path known; values not read during preparation',
    'pg_endpoint':'127.0.0.1:55483','postgres_version_and_role_now':'Not connected or queried; verify at reserved execution window',
    'coordinator_resource_statement':'Backend all PG connections paused; TCG VM orderly off and no desktopbuild/Chrome/load during reserved window. This is coordinator statement, not a measurement of absent contention.',
    'load_started':False,'owned_database_created':False}
save('preparation-environment.json',environment)
assert sources=={name:sha(ROOT/name) for name in sorted(names)}
assert baseline=={p.name:sha(p) for p in sorted(BASE.iterdir()) if p.is_file()}
contract={'status':'prepared_not_executed','source_head_at_preparation':environment['head_at_preparation'],
    'driver':'run_history200.py','driver_sha256':sha(OUT/'run_history200.py'),
    'measurement':{'route':'GET /api/usuario/historial','params':{'limit':50},'page':'first page, no cursor supplied',
        'persisted_plans':1000,'subjects':1,'profiles':1,'role':'VIEWER personal account',
        'concurrency':[1,5],'requests_each':100,'measured_http_total':200,'max_seconds_each':30,
        'order':'C1 then C5, bounded closed loop; identical scheduler/timeout/client clocks to accepted harness',
        'excluded_controls':{'auth_readiness':'Actual attempts enumerated separately','history_warmup':1,'explain':'After both scenarios; no HTTP'},
        'semantics':'HTTP200;50unique summaries with cursor; exact public fields; no JSON/private paths in response; no auth/route overrides'},
    'database':{'create':'Own UUID database only after root ACK','migration':'db_bootstrap head28 with migrator role',
        'application':'Same restricted app role; assert noSUPER/noBYPASS/noCREATEDB/noCREATEROLE',
        'seed':'Only1VIEWER+1profile+1000stored plans, same762-byte synthetic plan content; no other read flows/generator/PDF',
        'cleanup':'Own UUID DROP exact + verify absence, owned HTTP nonce/PID/parent verified and stopped; receipt contains name not URL'},
    'explain':{'source':'Exact summary SELECT and bind parameters captured in sole warmup before measured requests',
        'execution':'EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) after both measured scenarios, same restricted app engine and tenant_scope(load-person-4)',
        'checks':'SELECT only, LIMIT51, noCOUNT/no plan_json, real actual rows51; preserve full plan; no forced index/SLO assertion'},
    'baseline':{'immutable_total':1400,'matching_subset':40,'samples_each_concurrency':20,
        'preserved_prefix':str(BASE),'manifest':'baseline-historical1000-selection.json',
        'comparison':'Descriptive only; old unbounded1000-row response and now50-row page, sample sizes20vs100, schema/runtime/data-distribution/contention differ'},
    'slo_status':'PENDING: numerical objectives, arrival-rate/workload model and comparable production environment not agreed. No pass/fail latency target, causal p95 claim, production extrapolation, Linux/TCG/container benchmark or old7-flow rerun.',
    'execution_authorization':'WAITING for root explicit ACK. Mandatory nonexpired resource-window JSON matching expected HEAD; no DB/HTTP already run.',
    'safe_command_template':'<candidate-web-python> -X utf8 run_history200.py --private-env <private env.json> --output <owned new run dir> --requests 100 --seconds 30 --window-file <approved own Temp JSON> --expected-head <root frozen SHA>',
    'source_and_baseline_unchanged_during_preparation':True}
save('prepared-contract.json',contract)
manifest={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}
save('preparation-manifest.json',{'files':manifest,'count':len(manifest),'scope':'Preparation only; no PostgreSQL connection or HTTP execution. All current owned files except self.'})
print(json.dumps({'prepared':True,'driver_sha256':sha(OUT/'run_history200.py'),
    'contract_sha256':sha(OUT/'prepared-contract.json'),'manifest_sha256':sha(OUT/'preparation-manifest.json'),
    'sources':len(sources),'packages':89,'db_created':False,'http_requests':0}))
