"""Adversarial CI28 baseline-input probes in an exclusively owned Temp shadow.

The two mutations reproduce QA's cases without modifying real author files,
parsers, historical assertions, application data or the independent evidence.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SNAP=Path('docs/implementation/20261018-evolution/evidence/backend-recovery-ci28')


def sha(path,normalized=False):
    data=path.read_bytes()
    return hashlib.sha256(data.replace(b'\r\n',b'\n') if normalized else data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    metadata=json.loads((ROOT/SNAP/'baseline.json').read_text(encoding='utf8'))
    paths=['tests/verify_recovery_ci.py','.github/workflows/ci.yml','tests/e2e/personal_diary_server.py',
        str(SNAP/'ci27-baseline.yml'),str(SNAP/'diary27-fixture-before.py'),str(SNAP/'baseline.json'),
        *metadata['unchanged_files']]
    before={name:sha(ROOT/name) for name in paths}
    results=[]
    with tempfile.TemporaryDirectory(prefix='metodobase-ci28-baseline-trust-') as temporary:
        scratch=Path(temporary);shadow=scratch/'shadow';shadow.mkdir()
        for name in paths:
            target=shadow/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,target)
        def invoke(label,should_pass):
            environment=dict(os.environ,PYTHONPATH=str(ROOT))
            run=subprocess.run([sys.executable,'-X','utf8',str(shadow/'tests/verify_recovery_ci.py'),
                '--output',str(scratch/('probe-'+label)),'--verify-only'],cwd=shadow,env=environment,
                capture_output=True,text=True,encoding='utf8',timeout=30)
            (out/(label+'.log')).write_text(run.stdout+run.stderr,encoding='utf8')
            results.append({'case':label,'exit':run.returncode,'expected':'pass' if should_pass else 'reject',
                'matched_contract':(run.returncode==0)==should_pass})
        invoke('untouched-shadow',True)
        for name in ['tests/e2e/personal_diary_server.py',str(SNAP/'diary27-fixture-before.py')]:
            with (shadow/name).open('a',encoding='utf8') as stream:
                stream.write('\nCI28_UNAUTHORIZED_BASELINE_SENTINEL = True\n')
        assert sha(shadow/SNAP/'diary27-fixture-before.py',True)!=metadata['diary_fixture27_sha256']
        invoke('fixture-baseline-pair-tampered',False)
        for name in ['tests/e2e/personal_diary_server.py',str(SNAP/'diary27-fixture-before.py')]:
            shutil.copyfile(ROOT/name,shadow/name)
        historical='tests/verify_diary_ci.py'
        with (shadow/historical).open('a',encoding='utf8') as stream:
            stream.write('\nCI28_UNAUTHORIZED_HISTORICAL_SENTINEL = True\n')
        modified=json.loads(json.dumps(metadata))
        modified['unchanged_files'][historical]=sha(shadow/historical,True)
        (shadow/SNAP/'baseline.json').write_text(json.dumps(modified,indent=2)+'\n',encoding='utf8')
        invoke('historical-file-and-metadata-tampered',False)
        for name in [historical,str(SNAP/'baseline.json')]:
            shutil.copyfile(ROOT/name,shadow/name)
        target=shadow/'tests/e2e/personal_diary_server.py'
        source=target.read_text(encoding='utf8');first=ast.parse(source).body[0]
        assert isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and isinstance(first.value.value,str)
        remainder=''.join(source.splitlines(keepends=True)[first.end_lineno:])
        target.write_text("print('CI28_UNAUTHORIZED_FIRST_EXPRESSION')\n"+remainder,encoding='utf8')
        invoke('executable-first-expression-not-docstring',False)
        target.write_text('"""Allowed documentation-only update."""\n'+remainder,encoding='utf8')
        invoke('literal-docstring-only-update',True)
        with zipfile.ZipFile(out/'raw-shadow.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(scratch.rglob('*')):
                if path.is_file():archive.write(path,path.relative_to(scratch).as_posix())
    after={name:sha(ROOT/name) for name in paths}
    assert before==after,'Real author inputs changed'
    report={'scope':'Exact baseline-input trust mutations, full CLI verify-only in owned Temp shadows; no server/schema/PG/browser',
        'cases':results,'sources_before':before,'sources_after':after,'changedDuringCheck':False,
        'raw_archive_sha256':sha(out/'raw-shadow.zip'),'violations':sum(not row['matched_contract'] for row in results)}
    (out/'review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'cases':len(results),'violations':report['violations']}))
    return int(bool(report['violations']))


if __name__=='__main__':raise SystemExit(main())
