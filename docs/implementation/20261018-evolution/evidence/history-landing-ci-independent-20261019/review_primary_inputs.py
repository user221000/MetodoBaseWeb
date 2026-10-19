"""Exercise the real CLI against owned mutable-primary shadow copies."""
import ast
import copy
import shutil
import tempfile
import yaml
from qa_support import *

BASE = 'a753b2cdf61a91133bd58c3159b0b35e02167396'
before = photo('primary-before')
changed = [name for name in git('diff','--name-only',BASE,HEAD).decode().splitlines() if not name.startswith('docs/')]
assert changed == ['.github/workflows/ci.yml','tests/ci_history_landing28/README.md',
                   'tests/ci_history_landing28/ci28-before.yml','tests/verify_history_landing_ci.py']
snapshot = ROOT/'tests/ci_history_landing28/ci28-before.yml'
assert snapshot.read_bytes().replace(b'\r\n',b'\n') == git('show',BASE+':.github/workflows/ci.yml')
for name in ['tests/verify_recovery_ci.py','tests/verify_diary_ci.py','scripts/check_frontend_report.py',
             'scripts/check_browser_fixture_startup.py','tests/integration_diary_restore_review.py',
             'tests/integration_recovery28_restore_review.py']:
    assert (ROOT/name).read_bytes().replace(b'\r\n',b'\n') == git('show',BASE+':'+name)
old = yaml.safe_load(snapshot.read_text(encoding='utf8'))
new = yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_text(encoding='utf8'))
assert old['jobs']['postgres'] == new['jobs']['postgres']
old_browser = next(step['run'] for step in old['jobs']['image']['steps'] if 'run_browser_fixture() {' in step.get('run',''))
new_browser = next(step['run'] for step in new['jobs']['image']['steps'] if 'run_browser_fixture() {' in step.get('run',''))
old_calls = [line for line in old_browser.splitlines() if line.startswith('run_browser_fixture ')]
new_calls = [line for line in new_browser.splitlines() if line.startswith('run_browser_fixture ')]
assert len(old_calls)==7 and len(new_calls)==9 and new_calls[:7] == old_calls
assert new_browser.startswith(old_browser)
function = old_browser[old_browser.index('run_browser_fixture() {'):old_browser.index('\nbrowser_evidence=')]
assert function == new_browser[new_browser.index('run_browser_fixture() {'):new_browser.index('\nbrowser_evidence=')]
save(OUT/'static-preservation.json', {'head':HEAD,'only_nondocument_delta':changed,
     'ci28_snapshot_matches_main_before_extension':True,'historical_verifiers_parsers_restores_unchanged':True,
     'original_browser_calls_unchanged':old_calls,'actual_fixture_function_sha256':sha(function.encode()),
     'pg_job_entire_tree_unchanged':old['jobs']['postgres']==new['jobs']['postgres'],
     'new_browser_calls':new_calls[7:],'scope':'Static preservation; no execution of old fixtures/VM/PG/restore claimed.'})

shadow = Path(tempfile.mkdtemp(prefix='metodobase-history-ci-primary-'))
for name in before['sources']:
    target=shadow/name; target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/name,target)
originals={name:(shadow/name).read_bytes() for name in before['sources']}
workflow='.github/workflows/ci.yml'
ci28='tests/ci_history_landing28/ci28-before.yml'
recovery='tests/verify_recovery_ci.py'
meta='docs/implementation/20261018-evolution/evidence/backend-recovery-ci28/baseline.json'
fixture='tests/e2e/personal_diary_server.py'
fixture27='docs/implementation/20261018-evolution/evidence/backend-recovery-ci28/diary27-fixture-before.py'
diary='tests/verify_diary_ci.py'
rows=[]

def write_yaml(name, obj):
    (shadow/name).write_text(yaml.safe_dump(obj,sort_keys=False),encoding='utf8')

for label in ['positive','snapshot-and-primary-synchronized','historical-verifier-changed',
              'historical-metadata-and-verifier-synchronized','historical-fixture-pair-synchronized',
              'historical-fixture-snapshot-only','primary-unrelated-change',
              'snapshot-comment-only','snapshot-crlf-positive','primary-comment-positive']:
    for name in [workflow,ci28,recovery,meta,fixture,fixture27,diary]:
        (shadow/name).write_bytes(originals[name])
    expected=True; reason=None
    if label=='snapshot-and-primary-synchronized':
        a=copy.deepcopy(old);b=copy.deepcopy(new)
        a['jobs']['postgres']['runs-on']=b['jobs']['postgres']['runs-on']='windows-latest'
        write_yaml(ci28,a);write_yaml(workflow,b)
        expected=False;reason='Reviewed CI28 snapshot changed'
    elif label=='historical-verifier-changed':
        (shadow/recovery).write_bytes(originals[recovery]+b'\n# independent mutable-primary sentinel\n')
        expected=False;reason='Historical verifier changed'
    elif label=='historical-metadata-and-verifier-synchronized':
        (shadow/diary).write_bytes(originals[diary]+b'\nprint("independent unauthorized statement")\n')
        data=json.loads(originals[meta]);data['unchanged_files'][diary]=sha((shadow/diary).read_bytes().replace(b'\r\n',b'\n'))
        (shadow/meta).write_text(json.dumps(data),encoding='utf8')
        expected=False;reason='Reviewed baseline metadata changed'
    elif label=='historical-fixture-pair-synchronized':
        for name in [fixture,fixture27]:
            text=originals[name].decode('utf8')
            parsed=ast.parse(text);end=parsed.body[0].end_lineno
            lines=text.splitlines(keepends=True);lines.insert(end,'print("independent fixture sentinel")\n')
            (shadow/name).write_text(''.join(lines),encoding='utf8')
        data=json.loads(originals[meta]);data['diary_fixture27_sha256']=sha((shadow/fixture27).read_bytes().replace(b'\r\n',b'\n'))
        (shadow/meta).write_text(json.dumps(data),encoding='utf8')
        expected=False;reason='Reviewed baseline metadata changed'
    elif label=='historical-fixture-snapshot-only':
        (shadow/fixture27).write_bytes(originals[fixture27]+b'\n# independent changed reference\n')
        expected=False;reason='Historical diary fixture changed'
    elif label=='primary-unrelated-change':
        obj=copy.deepcopy(new);obj['jobs']['postgres']['runs-on']='windows-latest';write_yaml(workflow,obj)
        expected=False;reason='Workflow differs beyond the authorized history/landing delta'
    elif label=='snapshot-comment-only':
        (shadow/ci28).write_bytes(originals[ci28]+b'\n# independent changed reference\n')
        expected=False;reason='Reviewed CI28 snapshot changed'
    elif label=='snapshot-crlf-positive':
        (shadow/ci28).write_bytes(originals[ci28].replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
    elif label=='primary-comment-positive':
        (shadow/workflow).write_bytes(originals[workflow]+b'\n# independent document-only primary edit\n')
    target=OUT/'primary-cli'/label;target.parent.mkdir(exist_ok=True)
    command=[str(PYTHON),'-X','utf8',str(shadow/'tests/verify_history_landing_ci.py'),
             '--output',str(target),'--verify-only']
    result=run(command,'primary-'+label,cwd=shadow,timeout=45)
    assert (result.returncode==0)==expected,(label,result.returncode)
    full=result.stdout+result.stderr
    historic=target/'historical-ci28.log'
    if historic.is_file():full+='\n'+historic.read_text(encoding='utf8')
    assert reason is None or reason in full,(label,reason)
    rows.append({'case':label,'exit':result.returncode,'expected_success':expected,
                 'required_rejection_reason':reason,'shadow_file_sha256':{name:sha((shadow/name).read_bytes())
                   for name in [workflow,ci28,recovery,meta,fixture,fixture27,diary]}})
after=photo('primary-after');assert before==after
save(OUT/'primary-input-summary.json', {'head':HEAD,'accepted':True,'cases':rows,'shadow_root':str(shadow),
    'sources_stable':len(before['sources']),'packages':89,
    'scope':'Actual maintained CLI and historical subprocess against owned Temp shadow. Historical criteria and primaries in the candidate/MAIN were not edited. Three positive controls include normalized EOL and primary YAML comments.'})
print(json.dumps({'primary_cli_cases':len(rows),'negatives':sum(not row['expected_success'] for row in rows),'accepted':True}))
