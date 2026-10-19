"""Verify only the authorized CI28 delta from the accepted CI27 snapshot.

verify_diary_ci.py is an immutable historical CI27 verifier. Its assertions are
not applicable to the new PostgreSQL job and are neither edited nor executed
against CI28 here. This entrypoint does not run Node162, old91 guards, backend
tests, PostgreSQL, a real fixture/browser, Docker, Actions or remote services.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile

import yaml

ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT=ROOT/'docs/implementation/20261018-evolution/evidence/backend-recovery-ci28'
BASELINE_SHA='3f513336461e525fb42df810ca52fa9a6409d4ba1d61ac0eda14c50c31750e5e'
BASELINE_METADATA_SHA='ec3b455cef7a4a3bdb5a21640aa94e2edc8854909c54e79074629018e118f47e'
REVISION='20261019_account_recovery'
PREVIOUS='20261019_personal_diary'
NEW_REPORTS=('pytest-postgres-recovery-migrations.xml','pytest-postgres-recovery.xml')
MIGRATION_STEP={'name':'Account recovery migration preserves revision27 and rejects schema drift',
    'run':'python -X utf8 tests/run_isolated.py tests/integration_account_recovery_migrations.py -k postgresql -q --tb=short --junitxml='+NEW_REPORTS[0]}
RUNTIME_STEP={'name':'Account recovery HTTP, one-use races and uncertain commits under restricted role',
    'run':'python -X utf8 tests/run_isolated.py tests/integration_password_recovery_postgres.py -k postgresql -q --tb=short --junitxml='+NEW_REPORTS[1]}
RESTORE_NODE='tests/integration_recovery28_restore_review.py::test_revision28_restore_preserves_recovery_and_all_revision26_27_contracts'


def normalized(path):
    return Path(path).read_bytes().replace(b'\r\n',b'\n')


def save(out,name,value):
    (out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')


def baseline():
    raw=normalized(SNAPSHOT/'ci27-baseline.yml')
    assert hashlib.sha256(raw).hexdigest()==BASELINE_SHA,'Historical CI27 snapshot changed'
    return yaml.safe_load(raw)


def baseline_metadata():
    raw=normalized(SNAPSHOT/'baseline.json')
    assert hashlib.sha256(raw).hexdigest()==BASELINE_METADATA_SHA,'Reviewed baseline metadata changed'
    return json.loads(raw)


def expected_workflow(old):
    expected=copy.deepcopy(old)
    steps=expected['jobs']['postgres']['steps']
    restore=next(step for step in steps if step.get('name','').startswith('Encrypted PostgreSQL'))
    index=steps.index(restore)
    steps[index:index]=[MIGRATION_STEP,RUNTIME_STEP]
    assert restore['run'].count('tests/integration_diary_restore_review.py')==1
    restore['run']=restore['run'].replace('tests/integration_diary_restore_review.py',RESTORE_NODE)
    guard=next(step for step in steps if step.get('name','').startswith('Required PostgreSQL acceptance'))
    prefix='reports=list(map(Path,sys.argv[1:])); '
    assert guard['run'].count(prefix)==1
    guard['run']=guard['run'].replace(prefix,prefix+"assert len(reports)==21 and len(set(reports))==21, 'Expected 21 distinct PostgreSQL reports'; ")
    guard['run']+=' '+' '.join(NEW_REPORTS)
    browser=next(step for step in expected['jobs']['image']['steps'] if 'run_browser_fixture() {' in step.get('run',''))
    needle='--tables 26 --revision '+PREVIOUS
    assert browser['run'].count(needle)==1
    browser['run']=browser['run'].replace(needle,'--tables 26 --revision '+REVISION)
    return expected


def verify_workflow(workflow,old):
    assert workflow==expected_workflow(old),'Workflow differs beyond the authorized CI28 delta'
    steps=workflow['jobs']['postgres']['steps']
    guard=next(step['run'] for step in steps if step.get('name','').startswith('Required PostgreSQL acceptance'))
    parts=shlex.split(guard)
    assert parts[:2]==['python','-c']
    reports=parts[3:]
    assert len(reports)==len(set(reports))==21
    old_guard=next(step['run'] for step in old['jobs']['postgres']['steps'] if step.get('name','').startswith('Required PostgreSQL acceptance'))
    old_reports=shlex.split(old_guard)[3:]
    assert len(old_reports)==19 and reports==old_reports+list(NEW_REPORTS)
    produced=[name for step in steps for name in re.findall(r'--junitxml=(pytest-postgres-[a-z-]+\.xml)',step.get('run',''))]
    assert len(produced)==21 and set(produced)==set(reports)
    return parts, reports


def verify_fixture(path):
    raw=normalized(SNAPSHOT/'diary27-fixture-before.py')
    assert hashlib.sha256(raw).hexdigest()==baseline_metadata()['diary_fixture27_sha256'],'Historical diary fixture changed'
    old=ast.parse(raw)
    current=ast.parse(Path(path).read_text(encoding='utf8'))
    restored=copy.deepcopy(current)
    assert (isinstance(restored.body[0],ast.Expr) and isinstance(restored.body[0].value,ast.Constant)
        and isinstance(restored.body[0].value.value,str)),'Fixture must start with a literal docstring'
    restored.body[0]=copy.deepcopy(old.body[0])  # Only its current-head docstring changes.
    imports=0
    class Restore27(ast.NodeTransformer):
        def visit_ImportFrom(self,node):
            nonlocal imports
            if node.module=='web.database.schema_control':
                assert [(value.name,value.asname) for value in node.names]==[('expected_head',None)]
                imports+=1
                return None
            return node
        def visit_Call(self,node):
            if isinstance(node.func,ast.Name) and node.func.id=='expected_head':
                assert not node.args and not node.keywords
                self.calls+=1
                return ast.Constant(PREVIOUS)
            return self.generic_visit(node)
        calls=0
    transform=Restore27();restored=transform.visit(restored)
    assert imports==transform.calls==1 and ast.dump(restored)==ast.dump(old),'Fixture changed beyond its marker/import/docstring'
    # Evaluate only the three actual marker expressions, not main()/HTTP/DDL.
    sys.path.insert(0,str(ROOT))
    from tests.isolation import prepare_environment,block_external_sockets
    prepare_environment(discard_inherited=True);block_external_sockets()
    from web.database.models import Base
    from web.database.schema_control import expected_head
    dictionaries=[node for node in ast.walk(current) if isinstance(node,ast.Dict)
        and any(isinstance(key,ast.Constant) and key.value=='model_target_revision' for key in node.keys)]
    assert len(dictionaries)==1
    marker={}
    for key,value in zip(dictionaries[0].keys,dictionaries[0].values):
        if isinstance(key,ast.Constant) and key.value in {'fixture','model_target_revision','tables'}:
            expression=ast.Expression(value)
            marker[key.value]=eval(compile(expression,'actual-diary-marker-expression','eval'),
                {'__builtins__':{'len':len},'Base':Base,'expected_head':expected_head})
    assert marker=={'fixture':'personal-diary-ui','model_target_revision':REVISION,'tables':26}
    return marker


def report_cases(parts,reports,out):
    rows=[]
    positive='<testsuite tests="1"><testcase name="synthetic"/></testsuite>'
    mutations={'positive':positive,'missing':None,'empty':'','malformed':'<testsuite',
        'zero':'<testsuite tests="0"/>','skip':'<testsuite><testcase><skipped/></testcase></testsuite>',
        'failure':'<testsuite><testcase><failure/></testcase></testsuite>',
        'error':'<testsuite><testcase><error/></testcase></testsuite>'}
    for report in NEW_REPORTS:
        for phase,content in mutations.items():
            directory=out/(report.removesuffix('.xml')+'-'+phase);directory.mkdir()
            for name in reports:(directory/name).write_text(positive,encoding='utf8')
            if content is None:(directory/report).unlink()
            else:(directory/report).write_text(content,encoding='utf8')
            run=subprocess.run([sys.executable,*parts[1:]],cwd=directory,capture_output=True,text=True,timeout=15)
            assert (run.returncode==0)==(phase=='positive'),(report,phase,run.returncode)
            rows.append({'report':report,'case':phase,'exit':run.returncode})
    directory=out/'guard-count';directory.mkdir()
    for name in reports:(directory/name).write_text(positive,encoding='utf8')
    for label,names in [('omitted',reports[:-1]),('duplicate',reports[:-1]+[reports[0]])]:
        run=subprocess.run([sys.executable,'-c',parts[2],*names],cwd=directory,capture_output=True,text=True,timeout=15)
        assert run.returncode!=0,label
        rows.append({'report':'all21','case':label,'exit':run.returncode})
    return rows


def delta_cases(workflow,old):
    results=[]
    for name in ('missing-new-step','missing-old-report','weakened-xml-guard','includes-sqlite',
            'old-restore27','old-browser-marker27','unrelated-job','changed-browser-minimum'):
        candidate=copy.deepcopy(workflow)
        steps=candidate['jobs']['postgres']['steps']
        guard=next(step for step in steps if step.get('name','').startswith('Required PostgreSQL acceptance'))
        migration=next(step for step in steps if step.get('name')==MIGRATION_STEP['name'])
        restore=next(step for step in steps if step.get('name','').startswith('Encrypted PostgreSQL'))
        browser=next(step for step in candidate['jobs']['image']['steps'] if 'run_browser_fixture() {' in step.get('run',''))
        if name=='missing-new-step':steps.remove(migration)
        elif name=='missing-old-report':guard['run']=guard['run'].replace('pytest-postgres-rls.xml ','')
        elif name=='weakened-xml-guard':guard['run']=guard['run'].replace("('skipped','failure','error')","('skipped',)")
        elif name=='includes-sqlite':migration['run']=migration['run'].replace(' -k postgresql','')
        elif name=='old-restore27':restore['run']=restore['run'].replace(RESTORE_NODE,'tests/integration_diary_restore_review.py')
        elif name=='old-browser-marker27':browser['run']=browser['run'].replace('--revision '+REVISION,'--revision '+PREVIOUS)
        elif name=='unrelated-job':candidate['jobs']['redis']['runs-on']='windows-latest'
        elif name=='changed-browser-minimum':browser['run']=browser['run'].replace('17 named 8 tests/e2e/personal_export_context_browser','16 named 8 tests/e2e/personal_export_context_browser')
        assert candidate!=workflow,name
        try:verify_workflow(candidate,old)
        except AssertionError:results.append({'case':name,'rejected':True})
        else:raise AssertionError('Unauthorized delta accepted: '+name)
    return results


def inert_cases(function,bash,out):
    writer=out/'write_inert_report.py'
    writer.write_text("import json,sys\nfrom pathlib import Path\np,kind,n,screens=sys.argv[1:]\nn=int(n);screens=int(screens)\nPath(p).write_text(json.dumps({'checks':[{'name':str(i)} if kind=='named' else str(i) for i in range(n)],'pageErrors':[],'screens':[str(i) for i in range(screens)]}))\n",encoding='utf8')
    prefix=r'''set -euo pipefail
browser_fixture_pid=''
kill() { if [[ "$1" != '-0' ]]; then printf 'cleanup %s\n' "$1" >> "$CI_EVENTS"; fi; builtin kill "$@"; }
trap 'if [ -n "${browser_fixture_pid:-}" ]; then kill "$browser_fixture_pid" 2>/dev/null || true; fi' EXIT
python() {
 if [[ "$1" == '-X' ]]; then
  printf 'start %s\n' "$BASHPID" >> "$CI_EVENTS"
  printf '{"fixture":"personal-diary-ui","tables":26,"model_target_revision":"%s"}\n' "$CI_REVISION"
  exec /usr/bin/sleep 30
 elif [[ "$1" == 'scripts/check_browser_fixture_startup.py' ]]; then
  "$CI_PYTHON" "$CI_STARTUP" "${@:2}"
 else
  "$CI_PYTHON" "$CI_GUARD" "${@:2}"
 fi
}
node() {
 printf 'driver %s\n' "$browser_fixture_pid" >> "$CI_EVENTS"
 if [[ "$1" == first.cjs ]]; then
  "$CI_PYTHON" "$CI_WRITER" "$expected_report" "$report_format" "$minimum_checks" "$minimum_screens"
 else
  "$CI_PYTHON" "$CI_WRITER" "$second_report" "$second_format" "$second_minimum" "$second_screens"
 fi
}
curl() { return 0; }
sleep() { /usr/bin/sleep 0.01; }
'''
    results=[]
    for name,revision,expected,drivers in [('head28',REVISION,0,2),('head27-rejected',PREVIOUS,1,0)]:
        directory=out/('inert-'+name);directory.mkdir()
        (directory/'docs/implementation/20261018-evolution/evidence/ux').mkdir(parents=True)
        script=directory/'probe.sh'
        call='run_browser_fixture fixture.py 9999 first.cjs first.json 17 named 8 second.cjs second.json 4 strings 4 personal-diary-ui\n'
        script.write_text(prefix+function+'\n'+call,encoding='utf8')
        environment=dict(os.environ,CI_PYTHON=Path(sys.executable).as_posix(),
            CI_GUARD=(ROOT/'scripts/check_frontend_report.py').as_posix(),
            CI_STARTUP=(ROOT/'scripts/check_browser_fixture_startup.py').as_posix(),
            CI_WRITER=writer.as_posix(),CI_EVENTS=(directory/'events.txt').as_posix(),CI_REVISION=revision)
        result=subprocess.run([bash,script.as_posix()],cwd=directory,env=environment,capture_output=True,text=True,timeout=20)
        assert result.returncode==expected,(name,result.returncode,result.stderr)
        events=(directory/'events.txt').read_text().splitlines()
        starts=[row for row in events if row.startswith('start ')]
        cleanup=[row for row in events if row.startswith('cleanup ')]
        calls=[row for row in events if row.startswith('driver ')]
        assert len(starts)==len(cleanup)==1 and starts[0].split()[1]==cleanup[0].split()[1],events
        assert len(calls)==drivers and all(row.split()[1]==starts[0].split()[1] for row in calls),events
        results.append({'case':name,'exit':result.returncode,'events':events,'owned_process_cleanup':True})
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workflow',type=Path,default=ROOT/'.github/workflows/ci.yml')
    parser.add_argument('--fixture',type=Path,default=ROOT/'tests/e2e/personal_diary_server.py')
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    old=baseline();workflow=yaml.safe_load(args.workflow.read_text(encoding='utf8'))
    parts,reports=verify_workflow(workflow,old)
    metadata=baseline_metadata()
    for name,value in metadata['unchanged_files'].items():
        assert hashlib.sha256(normalized(ROOT/name)).hexdigest()==value,name
    marker=verify_fixture(args.fixture)
    if args.verify_only:
        save(out,'review.json',{'reports':reports,'actual_fixture_marker':marker,'authorized_delta_only':True})
        return
    bash=os.environ.get('METODOBASE_CI_BASH') or ('C:/Program Files/Git/bin/bash.exe' if os.name=='nt' else shutil.which('bash'))
    assert bash
    blocks=[step['run'] for job in workflow['jobs'].values() for step in job.get('steps',[]) if 'run' in step]
    for block in blocks:
        run=subprocess.run([bash,'-n'],input=block,capture_output=True,text=True,timeout=15)
        assert run.returncode==0,run.stderr
    refs=sorted(set(re.findall(r'(?:scripts|tests)/[A-Za-z0-9_./-]+\.(?:py|cjs)',args.workflow.read_text(encoding='utf8'))))
    assert all((ROOT/name).is_file() for name in refs)
    browser=next(value for value in blocks if 'run_browser_fixture() {' in value)
    function=browser[browser.index('run_browser_fixture() {'):browser.index('\nbrowser_evidence=')]
    (out/'actual-fixture-function.sh').write_text(function+'\n',encoding='utf8')
    report={'scope':'Local CI28 wiring/report-parser canaries and inert Git Bash processes; no Actions/Linux image/browser/PG/backend execution',
        'baseline27_verifier':'preserved unchanged, intentionally not executed against28',
        'prior162_VM_and91_generic_canaries':'preserved unchanged, not repeated',
        'reports':reports,'actual_fixture_marker':marker,'authorized_delta_only':True,
        'unchanged_files':metadata['unchanged_files'],'bash_blocks':len(blocks),'references':refs,
        'unauthorized_delta_canaries':delta_cases(workflow,old)}
    # Keep generated reports/process probes together without adding hundreds
    # of duplicate positive XML files to the repository. All entries below
    # are created by this verifier in its own temporary directory.
    with tempfile.TemporaryDirectory(prefix='metodobase-recovery-ci28-') as temporary:
        scratch=Path(temporary)
        report['new_report_canaries']=report_cases(parts,reports,scratch)
        report['inert_fixture_cases']=inert_cases(function,bash,scratch)
        with zipfile.ZipFile(out/'canaries-raw.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(scratch.rglob('*')):
                if path.is_file():archive.write(path,path.relative_to(scratch).as_posix())
    report['raw_archive_sha256']=hashlib.sha256((out/'canaries-raw.zip').read_bytes()).hexdigest()
    save(out,'review.json',report)
    print(json.dumps({'reports':len(reports),'report_canaries':len(report['new_report_canaries']),
        'inert_fixture_cases':len(report['inert_fixture_cases']),'delta_canaries':len(report['unauthorized_delta_canaries']),
        'bash_blocks':len(blocks)}))


if __name__=='__main__':main()
