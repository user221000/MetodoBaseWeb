"""Independent adversarial30 contracts. Only local files and subprocesses."""
from support import *
import shutil,xml.etree.ElementTree as ET
sys.path.insert(0,str(ROOT))
from tests import verify_history_index_ci as guard
from tests import check_history_index_reports as checker
import yaml
before=photo('own-before');phase=TEMP/'own';phase.mkdir(exist_ok=False);rows=[]
old=guard.baseline();workflow=yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_bytes())
# Real CLI rejects changed primaries and paired snapshot self-confirmation.
for label,changes in [
 ('fake-runner29',{'tests/run_reviewed_ci29.py':b'print("FAKE29_EXECUTED")\n'}),
 ('empty-checker30',{'tests/check_history_index_reports.py':b'REPORTS = {}\n'}),
 ('empty-physical-witness',{'web/database/alembic/history_index_contract_v1.py':b'def expected_history_index(_): return {}\n'}),
 ('paired-snapshot-and-baseline',{})]:
    case=phase/label;case.mkdir();copy=case/'repository';copy.mkdir()
    names=set(guard.PINNED_CURRENT_GATES)|{'tests/verify_history_index_ci.py','tests/ci_history_index30/ci29-before.yml','tests/ci_history_index30/baseline.json','.github/workflows/ci.yml'}
    for name in names:
        target=copy/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    if label=='paired-snapshot-and-baseline':
        name='tests/ci_history_index30/ci29-before.yml';raw=(copy/name).read_bytes()+b'\n# paired changed snapshot\n';changes[name]=raw
        baseline=json.loads((copy/'tests/ci_history_index30/baseline.json').read_bytes());baseline['workflow_sha256']=sha(raw.replace(b'\r\n',b'\n'))
        changes['tests/ci_history_index30/baseline.json']=(json.dumps(baseline,indent=2)+'\n').encode()
    for name,body in changes.items():(copy/name).write_bytes(body)
    result=subprocess.run([str(PYTHON),'-X','utf8','-B',str(copy/'tests/verify_history_index_ci.py'),'--output',str(case/'gate'),'--verify-only'],cwd=copy,capture_output=True,timeout=15)
    (case/'stdout.log').write_bytes(result.stdout);(case/'stderr.log').write_bytes(result.stderr)
    assert result.returncode!=0 and b'FAKE29_EXECUTED' not in result.stdout and not (case/'gate/historical-ci29').exists()
    rows.append({'case':label,'passed':True,'actual_CLI_exit':result.returncode,'rejected_before_historical_exec':True})
# Actual generic28-report command must reject omission of any legacy report.
parts,reports=guard.verify_workflow(workflow,old)
for label in ['all28-positive','legacy-quota-omitted','legacy-restore28-empty','old26-instead28','new-index-error']:
    directory=phase/label;directory.mkdir()
    for name in reports:
        root=ET.Element('testsuite');ET.SubElement(root,'testcase',classname='synthetic.acceptance',name='local-case')
        if label=='legacy-restore28-empty' and name=='pytest-postgres-restore.xml':root.clear()
        if label=='new-index-error' and name=='pytest-postgres-history-index.xml':ET.SubElement(root[0],'error')
        if not(label=='legacy-quota-omitted' and name=='pytest-postgres-quota.xml'):ET.ElementTree(root).write(directory/name)
    selected=parts[3:-2] if label=='old26-instead28' else parts[3:]
    result=subprocess.run([str(PYTHON),parts[1],parts[2],*selected],cwd=directory,capture_output=True,timeout=10)
    (directory/'stdout.log').write_bytes(result.stdout);(directory/'stderr.log').write_bytes(result.stderr)
    assert (result.returncode==0)==(label=='all28-positive')
    rows.append({'case':label,'passed':True,'generic28_report_command_exit':result.returncode})
# Exact checker positive and equal-count/dialect/case substitutions.
for label in ['actual-nine-positive','mixed-SQLite-one-case','same-count-query-replaced','old29-restore-substituted','same-id-duplicate-newcase','root-level-skip']:
    directory=phase/label;directory.mkdir()
    for name,ids in checker.REPORTS.items():
        suite=ET.Element('testsuite')
        for module,node in sorted(ids):ET.SubElement(suite,'testcase',classname=module,name=node)
        if label=='mixed-SQLite-one-case' and name.endswith('history-index.xml'):suite[0].set('name',suite[0].get('name').replace('postgresql','sqlite'))
        if label=='same-count-query-replaced' and name.endswith('history-index.xml'):
            query=next(c for c in suite if c.get('classname')==checker.QUERY);query.set('classname',checker.MIGRATIONS);query.set('name','different_migration[postgresql]')
        if label=='old29-restore-substituted' and name.endswith('index-restore.xml'):suite[0].set('classname','tests.integration_client_link_restore');suite[0].set('name','test_revision29_restore_preserves_member_links_and_all_revision26_27_28_contracts')
        if label=='same-id-duplicate-newcase' and name.endswith('history-index.xml'):suite[-1].set('classname',suite[0].get('classname'));suite[-1].set('name',suite[0].get('name'))
        if label=='root-level-skip' and name.endswith('index-restore.xml'):ET.SubElement(suite,'skipped')
        ET.ElementTree(suite).write(directory/name)
    result=subprocess.run([str(PYTHON),'-X','utf8','-B',str(ROOT/'tests/check_history_index_reports.py'),'--directory',str(directory)],cwd=ROOT,capture_output=True,timeout=10)
    (directory/'stdout.log').write_bytes(result.stdout);(directory/'stderr.log').write_bytes(result.stderr)
    assert (result.returncode==0)==(label=='actual-nine-positive');rows.append({'case':label,'passed':True,'actual_checker_exit':result.returncode})
# Historical contracts cannot be routed through current default or fabricated env.
for label,mutation in [
 ('force-restore29-current',lambda w:next(s for s in w['jobs']['postgres']['steps'] if s.get('name','').startswith('Current revision29 populated restore')).update(run='python tests/integration_client_link_restore.py')),
 ('remove-restore28-gate',lambda w:w['jobs']['postgres']['steps'].remove(next(s for s in w['jobs']['postgres']['steps'] if 'tests/run_reviewed_ci28.py' in s.get('run','')))),
 ('seed-false-schema29-env',lambda w:next(s for s in w['jobs']['postgres']['steps'] if s.get('name','').startswith('Current revision29 populated restore')).update(env={'EXPECTED_SCHEMA_HEAD':'20261019_client_account_links'})),
 ('current-browser29-pin',lambda w:next(s for s in w['jobs']['image']['steps'] if s==guard.BROWSER_STEP).update(run=guard.BROWSER_STEP['run'].replace('run_member_link_browser.py','old_member_link_browser.py')))]:
    candidate=deepcopy(workflow);mutation(candidate)
    try:guard.verify_workflow(candidate,old)
    except AssertionError:rejected=True
    else:rejected=False
    assert rejected;rows.append({'case':label,'passed':True})
after=photo('own-after');assert before==after
outputs=[]
for path in sorted(phase.rglob('*')):
    rel=path.relative_to(phase)
    if path.is_file() and 'repository' not in rel.parts:outputs.append(publish(path,'own-'+rel.as_posix().replace('/','--')))
save('own-result.json',{'head':HEAD,'passed':len(rows),'total':len(rows),'cases':rows,'sources_helpers_packages_stable':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'outputs':outputs,'scope':'Independent local CLI/parser/workflow negative controls only; no Chrome/PG/Actions/SLO.'})
print(json.dumps({'passed':len(rows),'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'no_real_Chrome_or_PG':True}))
