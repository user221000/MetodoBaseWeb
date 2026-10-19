"""Read-only source/package receipts for the isolated R12 core worktree."""
import sys
sys.dont_write_bytecode=True
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(r'F:/MetodoBaseWeb-r12-core29-qa-20261019')
MAIN=Path(r'F:/MetodoBaseWeb-execution-20261018')
OUT=Path(__file__).resolve().parent
HEAD='ad71241628021941ed927b066d2d6e8e72ddef2c'
BASE='7cf4e6c996708f580054a798406ccdc3336a0fa6'
PYTHON=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-candidate-web-20261018/Scripts/python.exe')
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
RAW=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-r12-canonical29-core-exact-raw.zip')
sha=lambda value:hashlib.sha256(value).hexdigest()
def save(name,value):
    with (OUT/name).open('x',encoding='utf8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def photo(label):
    assert git('rev-parse','HEAD').decode().strip()==HEAD
    assert not git('status','--porcelain').decode().strip()
    names={name for name in git('ls-files','-z').decode().split('\0') if name and not name.startswith('docs/')}
    freeze=ROOT/'docs/implementation/20261018-evolution/evidence/backend-r12-canonical29-freeze.json'
    names.update(json.loads(freeze.read_text(encoding='utf8'))['sources_after_tests_sha256'])
    names.add(freeze.relative_to(ROOT).as_posix())
    sources={name:sha((ROOT/name).read_bytes()) for name in sorted(names)}
    packages=sorted([d.metadata['Name'],d.version] for d in importlib.metadata.distributions());assert len(packages)==89
    result=subprocess.run([str(PYTHON),'-m','pip','check'],cwd=ROOT,capture_output=True,encoding='utf8',timeout=30)
    with (OUT/(label+'-pip.log')).open('x',encoding='utf8') as stream:stream.write(result.stdout+result.stderr)
    assert result.returncode==0
    value={'head':HEAD,'sources':sources,'source_count':len(sources),'packages':packages,'package_count':89,'pip_check_exit':0}
    save(label+'-source.json',value);return value
