"""Bounded independent QA phases; private PG configuration exists only in child memory."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(r'F:\MetodoBaseWeb-recovery-compose-20261019')
OUT=Path(__file__).resolve().parent
PRIVATE=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-qa-pg55483-private-ok6hrpyq\env.json')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def snapshot():
    paths=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True).stdout.decode().split('\0')
    directories={'api','core','web','src','utils','config','ui_desktop','design_system','scripts','tests','assets','fonts','static','infra','.github'}
    sources={name:sha(ROOT/name) for name in paths if name and (name.split('/')[0] in directories or '/' not in name)}
    for name in ['tests/test_recovery28_review.py','tests/integration_recovery28_restore_review.py','tests/recovery28_restore_helpers.py']:
        if (ROOT/name).is_file():sources[name]=sha(ROOT/name)
    packages=sorted(({'name':row.metadata['Name'],'version':row.version} for row in importlib.metadata.distributions()),key=lambda row:row['name'].lower())
    assert len(packages)==89
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    return {'head':head,'sources':sources,'packages':packages}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['directed','sqlite','postgres','own','restore'])
    parser.add_argument('--label',required=True)
    args=parser.parse_args()
    out=OUT/args.label
    out.mkdir(exist_ok=False)
    before=snapshot();save(out/'before.json',before)
    check=subprocess.run([sys.executable,'-m','pip','check'],cwd=ROOT,capture_output=True,text=True)
    (out/'pip-before.log').write_text(check.stdout+check.stderr,encoding='utf8');assert check.returncode==0
    environment=os.environ.copy()
    for key in ['_METODOBASE_TEST_ROOT','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN','PYTEST_XDIST_WORKER']:
        environment.pop(key,None)
    environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',METODOBASE_TEST_EVIDENCE_DIR=str(out))
    if args.phase in {'postgres','restore'}:
        # Do not print this dictionary or put its values in evidence.
        private=json.loads(PRIVATE.read_bytes())
        allowed={'METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN'}
        assert set(private)==allowed,'Unexpected private configuration fields'
        environment.update(private)
    if args.phase=='directed':
        old=ET.parse(ROOT/'docs/implementation/20261018-evolution/evidence/backend-recovery-freeze-directed.xml')
        modules=set()
        for case in old.findall('.//testcase'):
            parts=case.attrib['classname'].split('.')
            while parts:
                path='/'.join(parts)+'.py'
                if (ROOT/path).is_file():modules.add(path);break
                parts.pop()
            else:raise AssertionError('Historical JUnit module cannot be resolved')
        nodes=sorted(modules)
        expected=181
    elif args.phase=='sqlite':nodes=['tests/integration_account_recovery_migrations.py','-k','sqlite'];expected=6
    elif args.phase=='postgres':nodes=['tests/integration_password_recovery_postgres.py','tests/integration_account_recovery_migrations.py','-k','postgresql'];expected=17
    elif args.phase=='own':nodes=['tests/test_recovery28_review.py'];expected=None
    else:nodes=['tests/integration_recovery28_restore_review.py'];expected=1
    command=[sys.executable,'-X','utf8','tests/run_isolated.py',*nodes,'-q','--tb=short','--junitxml='+str(out/'result.xml')]
    save(out/'command.json',{'phase':args.phase,'command':command,'expected_cases':expected})
    started=time.monotonic()
    with (out/'result.log').open('xb') as log:result=subprocess.run(command,cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT)
    after=snapshot();save(out/'after.json',after)
    check_after=subprocess.run([sys.executable,'-m','pip','check'],cwd=ROOT,capture_output=True,text=True)
    (out/'pip-after.log').write_text(check_after.stdout+check_after.stderr,encoding='utf8')
    tree=ET.parse(out/'result.xml')
    cases=tree.findall('.//testcase')
    counts={'tests':len(cases),'failure':len(tree.findall('.//failure')),'error':len(tree.findall('.//error')),'skipped':len(tree.findall('.//skipped'))}
    report={'phase':args.phase,'head':before['head'],'exit':result.returncode,'seconds':round(time.monotonic()-started,3),'junit':counts,
            'source_count':len(before['sources']),'source_stable':before['sources']==after['sources'],
            'packages':89,'packages_stable':before['packages']==after['packages'],'pip_check_before_after':[check.returncode,check_after.returncode],
            'scope':'Fresh isolated SQLite; PG phases use dedicated loopback config in child memory and UUID-owned fixtures. No provider or deployment.'}
    save(out/'source.json',report)
    print(json.dumps(report))
    assert result.returncode==0 and counts['failure']==counts['error']==counts['skipped']==0
    if expected is not None:assert len(cases)==expected
    assert report['source_stable'] and report['packages_stable'] and check_after.returncode==0


if __name__=='__main__':main()
