"""Exact CI33 composition: unchanged30, explicit31/32 history, real current33."""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

from tests.ci_mfa31.workflow import capture, upload
from tests.ci_mfa31.workflow import expected_workflow as version31_workflow

ROOT=Path(__file__).resolve().parents[2]
HIST31='de506b6077ba055587f02e7d839387e7f5c56f84'
CURRENT_REPORT_COMMANDS=(
 ('member-services',['tests/integration_current33_member_services.py'],''),
 ('member-http',['tests/integration_current33_member_http.py'],''),
 ('member-races',['tests/integration_current33_member_races.py'],''),
 ('r24-publication',['tests/integration_current33_r24_publication.py'],''),
 ('r24-race',['tests/integration_current33_r24_race.py'],''),
 ('mfa-services',['tests/integration_current33_mfa_postgres.py'],''),
 ('followup',['tests/integration_current33_followup.py'],''),
 ('rls-worker',['tests/integration_current33_rls.py'],''),
 ('privacy-export',['tests/integration_current33_privacy.py'],''),
 ('diary',['tests/integration_current33_diary.py'],''),
 ('progress',['tests/integration_current33_progress_postgres.py'],''),
 ('progress-adversarial',['tests/integration_current33_progress_adversarial.py'],''),
 ('progress-retirement',['tests/integration_current33_progress_retirement.py'],''),
 ('google-migrations',['tests/integration_google33_migrations.py'],' -k postgresql'),
 ('google-guards',['tests/integration_google33_guards.py'],''),
 ('google-services-races',['tests/integration_google33_postgres.py'],''),
 ('google-onboarding',['tests/integration_google33_onboarding.py'],''),
 ('google-conflict-window',['tests/integration_current33_google_conflict_window.py'],''),
 ('google-signup-races',['tests/integration_current33_google_signup_races.py'],''),
 ('restore',['tests/integration_google33_restore.py'],''),
)
HISTORICAL32_REPORT_COMMANDS=(
 ('migrations',['tests/integration_progress32_migrations.py'],' -k postgresql'),
 ('progress',['tests/integration_progress32_postgres.py'],''),
 ('adversarial',['tests/integration_progress32_reader_adversarial.py'],''),
 ('retirement',['tests/integration_progress_retirement.py'],''),
 ('restore',['tests/integration_progress32_restore.py'],''),
)
NEW_VM={'progress_export':38,'progress_retirement':36,'progress_retirement_dom':9,
        'google_link_api':10,'google_link_state':28,'google_link_dom':8,'google_link_login_review':3}


def materializer(schema,label):
    return {'name':'Materialize exact version'+schema+' Git blobs and detached source context',
        'working-directory':'${{ github.workspace }}',
        'run':'python -X utf8 tests/ci_google33/history.py --schema '+schema+
              ' --history-repository "$GITHUB_WORKSPACE" --output "$RUNNER_TEMP/'+label+'"'}


def historical(job,schema,label):
    value=copy.deepcopy(job)
    value['defaults']={'run':{'shell':'bash','working-directory':'${{ runner.temp }}/'+label+'/source'}}
    checkout=next(s for s in value['steps'] if s.get('uses')=='actions/checkout@v4')
    checkout['with']={'fetch-depth':0}
    # Materialize after tools setup, before any dependency install/run gate.
    first=next(i for i,s in enumerate(value['steps']) if 'run' in s)
    value['steps'].insert(first,materializer(schema,label))
    for step in value['steps']:
        if 'run' in step and 'tests/ci_google33/history.py' not in step['run']:
            if step.get('working-directory')=='${{ github.workspace }}':
                step['working-directory']='${{ runner.temp }}/'+label+'/source'
            step['run']=step['run'].replace('$GITHUB_WORKSPACE', '$RUNNER_TEMP/'+label+'/source')
        if step.get('uses')=='actions/upload-artifact@v4':
            step['with']['name']='historical'+schema+'-'+step['with']['name']
    return value


def expected_workflow():
    old=version31_workflow();result=copy.deepcopy(old);jobs=result['jobs']
    # Preserve every required31 component as explicitly attributed history.
    jobs['historical31-postgres']=historical(old['jobs']['current-postgres'],'31','historical31-postgres')
    jobs['historical31-image']=historical(old['jobs']['current-image'],'31','historical31-image')
    jobs['historical31-frontend']=historical(old['jobs']['frontend-contracts'],'31','historical31-frontend')
    jobs['historical31-web']=historical(old['jobs']['test-web'],'31','historical31-web')
    for step in jobs['historical31-image']['steps']:
        if 'run' in step and 'history.py' not in step['run']:
            step['run']=step['run'].replace('${{ github.sha }}',HIST31)
    # The original verifier is also executed against its real31 ORM/head.
    jobs['historical31-wiring']={'runs-on':'ubuntu-latest','needs':'quality','steps':[
        {'uses':'actions/checkout@v4','with':{'fetch-depth':0}},
        {'uses':'actions/setup-python@v5','with':{'python-version':'3.12'}},
        materializer('31','historical31-wiring'),
        {'run':'python -m pip install --require-hashes -r requirements-test.lock','working-directory':'${{ runner.temp }}/historical31-wiring/source'},
        {'name':'Original complete CI31 verifier and205 parser/trust controls; source31 only',
         'working-directory':'${{ runner.temp }}/historical31-wiring/source',
         'run':'python -X utf8 tests/verify_mfa31_ci.py --output "$RUNNER_TEMP/historical31-wiring-review"'}]}
    hist32=historical(old['jobs']['current-postgres'],'32','historical32-postgres')
    # Full32 evidence uses portable CI33 ownership infrastructure without edits
    # to the32 source or business bodies; the runner labels it historical32.
    hist32['steps']=hist32['steps'][:5]+[
        {'name':'Historical32 fresh CI role and schema32 bootstrap','run':'python -X utf8 tests/prepare_postgres.py'},
        {'name':'Historical32 complete progress/migrations/retirement/populated restore contracts',
         'working-directory':'${{ github.workspace }}',
         'run':'python -X utf8 tests/ci_google33/run_postgres.py --schema 32 --source "$RUNNER_TEMP/historical32-postgres/source" --private "$RUNNER_TEMP/historical32-private" --output "$RUNNER_TEMP/historical32-public"'},
        upload('historical32-postgres-tests','${{ runner.temp }}/historical32-public',
               [name for label,_,_ in HISTORICAL32_REPORT_COMMANDS for name in (
                   'pytest-historical32-'+label+'.xml','pytest-historical32-'+label+'.witnesses.json')]+['runtime-summary.json'])]
    jobs['historical32-postgres']=hist32
    web=jobs['test-web']['steps']
    verifier=next(s for s in web if 'tests/verify_mfa31_ci.py' in s.get('run',''))
    verifier.update(name='Current33 complete wiring/source-preservation/trust canaries',
        run='python -X utf8 tests/verify_google33_ci.py --output "$RUNNER_TEMP/google33-ci-wiring"')
    web.insert(web.index(verifier)+1,{'name':'R05 complete110 and exact49 reviewed-location critical identities',
        'run':capture('python -X utf8 tests/run_isolated.py tests/test_secret_scan_reviewed_locations.py tests/test_secret_scan_fragment_pins.py tests/test_secret_scan_safety.py -q --junitxml=pytest-r05-full110.xml\npython -X utf8 tests/check_google33_r05.py --report pytest-r05-full110.xml', 'web-private',999)})
    web.insert(web.index(verifier)+2,{'name':'ROOT QA17 four original signup rollback/uncertainty criteria on real SQLite HTTP',
        'run':capture('python -X utf8 tests/run_isolated.py tests/test_google33_conflict_window.py -q --junitxml=pytest-google33-root-qa17.xml', 'web-private',1000)})
    next(step for step in web if 'publish.py' in step.get('run',''))['run']+=' "pytest-r05-full110.xml"'
    next(step for step in web if 'publish.py' in step.get('run',''))['run']+=' "pytest-google33-root-qa17.xml"'
    next(step for step in web if step.get('uses')=='actions/upload-artifact@v4')['with']['path']+='\n${{ runner.temp }}/web-public/pytest-r05-full110.xml'
    next(step for step in web if step.get('uses')=='actions/upload-artifact@v4')['with']['path']+='\n${{ runner.temp }}/web-public/pytest-google33-root-qa17.xml'
    frontend=jobs['frontend-contracts']['steps']
    for step in frontend:
        if 'run' in step:
            step['run']=step['run'].replace('tests/e2e/personal_export_context.cjs','tests/e2e/current33_export_context.cjs').replace(
                'tests/e2e/personal_export_controls.cjs','tests/e2e/current33_export_controls.cjs').replace(
                'tests/e2e/member_link_export.cjs','tests/e2e/current33_member_link_export.cjs')
            step['run']=step['run'].replace('-current31','-current33')
        if step.get('uses')=='actions/upload-artifact@v4':
            step['with']['path']=step['with']['path'].replace('-current31','-current33')
    vm_lines=[];new_files=[]
    for module,minimum in NEW_VM.items():
        filename=module.replace('_','-')+'-current33.json';new_files.append(filename)
        if module=='progress_export':
            vm_lines.append('node tests/e2e/'+module+'.cjs > '+filename)
        else:
            raw=filename.replace('.json','.raw.json')
            vm_lines.extend(['node tests/e2e/'+module+'.cjs > '+raw,
                'python tests/ci_google33/normalize_vm.py '+raw+' '+filename+' --label-field '+
                ('code' if module=='google_link_login_review' else 'name')+' --minimum '+str(minimum)])
        vm_lines.append('python scripts/check_frontend_report.py '+filename+' --format counts --minimum '+str(minimum))
    frontend.insert(-2,{'name':'Current33 progress/export/retirement and explicit GoogleUI VM contracts',
        'run':capture('\n'.join(vm_lines),'frontend33-private',0)})
    projection_step=frontend[-2]
    projection_step['run']+=' '+' '.join('"'+f+'"' for f in new_files)
    artifact=frontend[-1]['with'];artifact['path']+='\n'+'\n'.join('${{ runner.temp }}/frontend-public/'+f for f in new_files)
    # New current jobs replace every31 runtime frame, rather than appending a
    # Google file while old current jobs continue to require head31.
    current=copy.deepcopy(old['jobs']['current-postgres'])
    current['steps']=current['steps'][:4]+[
        {'name':'Current33 real migrations and fresh CI restricted role','run':'python -X utf8 tests/prepare_postgres.py'},
        {'name':'All current33 full identities and measured head/role/FK/function/GUC witnesses',
         'run':'python -X utf8 tests/ci_google33/run_postgres.py --schema 33 --source "$GITHUB_WORKSPACE" --private "$RUNNER_TEMP/current33-private" --output "$RUNNER_TEMP/current33-public"'},
        upload('current33-postgres-tests','${{ runner.temp }}/current33-public',
               [name for label,_,_ in CURRENT_REPORT_COMMANDS for name in (
                   'pytest-current33-'+label+'.xml','pytest-current33-'+label+'.witnesses.json')]+['runtime-summary.json'])]
    jobs['current-postgres']=current
    image=copy.deepcopy(old['jobs']['current-image'])
    for step in image['steps']:
        if 'run' in step:step['run']=step['run'].replace('current31','current33').replace('Current31','Current33').replace('tests/ci_mfa31/','tests/ci_google33/')
        if step.get('uses')=='actions/upload-artifact@v4':
            step['with']={key:value.replace('current31','current33') if isinstance(value,str) else value for key,value in step['with'].items()}
            step['with']['path']+='\n${{ runner.temp }}/current33-browser-public/browser-runtime-inventory.json'
    jobs['current-image']=image
    # All publication calls use the current strict scanner/projection, while
    # historical jobs deliberately execute their frozen publisher on source31.
    for name,job in jobs.items():
        if name.startswith('historical'):continue
        for step in job['steps']:
            if 'run' in step:step['run']=step['run'].replace('tests/ci_mfa31/publish.py','tests/ci_google33/publish.py')
    jobs['ci-success']['needs']=[name for name in jobs if name!='ci-success']
    return result


def write(path):
    class LiteralDumper(yaml.SafeDumper):pass
    def string(dumper,value):return dumper.represent_scalar('tag:yaml.org,2002:str',value,style='|' if '\n' in value else None)
    LiteralDumper.add_representer(str,string)
    path.write_bytes(yaml.dump(expected_workflow(),Dumper=LiteralDumper,sort_keys=False,width=120).encode())


if __name__=='__main__':write(ROOT/'.github/workflows/ci.yml')
