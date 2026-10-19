"""Independent read-only source, package and local subprocess receipts."""
from __future__ import annotations
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(r'F:/MetodoBaseWeb-history-ci-20261019')
MAIN = Path(r'F:/MetodoBaseWeb-execution-20261018')
OUT = Path(__file__).resolve().parent
HEAD = '57dba41a87de4f7a743e6b68c0378f1629b7bb72'
PYTHON = Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-candidate-web-20261018/Scripts/python.exe')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(path, value):
    with Path(path).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def photo(label):
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    assert git('rev-parse', 'HEAD').decode().strip() == HEAD
    assert not git('status', '--porcelain').decode().strip()
    names = {name for name in git('ls-files', '-z').decode().split('\0') if name and not name.startswith('docs/')}
    baseline = ROOT / 'docs/implementation/20261018-evolution/evidence/backend-recovery-ci28'
    names.update(path.relative_to(ROOT).as_posix() for path in baseline.rglob('*')
                 if path.is_file() and path.suffix in {'.py','.json','.yml'})
    metadata = json.loads((baseline/'baseline.json').read_text(encoding='utf8'))
    names.update(metadata['unchanged_files'])
    sources = {name: sha((ROOT/name).read_bytes()) for name in sorted(names)}
    packages = sorted([entry.metadata['Name'], entry.version] for entry in importlib.metadata.distributions())
    node = {path.relative_to(MAIN).as_posix(): sha(path.read_bytes())
            for package in ['playwright-core','axe-core']
            for path in sorted((MAIN/'tests/e2e/node_modules'/package).rglob('*')) if path.is_file()}
    assert len(packages) == 89 and len(node) == 146
    check = subprocess.run([str(PYTHON),'-m','pip','check'], cwd=ROOT, capture_output=True, encoding='utf8', timeout=30)
    (OUT/(label+'-pip.log')).write_text(check.stdout+check.stderr, encoding='utf8')
    assert check.returncode == 0
    result = {'head':HEAD, 'sources':sources,'source_count':len(sources),'packages':packages,
              'package_count':89,'node_dependencies':node,'node_dependency_files':146,'pip_check_exit':0}
    save(OUT/(label+'.json'), result)
    return result

def environment():
    env = os.environ.copy()
    for name in ('METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN',
                 'METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','METODOBASE_HISTORY_EXPLAIN_OUTPUT',
                 '_METODOBASE_TEST_ROOT','PYTEST_XDIST_WORKER'):
        env.pop(name,None)
    env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    return env

def run(command, label, *, cwd=ROOT, timeout=180):
    result = subprocess.run(command,cwd=cwd,env=environment(),capture_output=True,encoding='utf8',timeout=timeout)
    with (OUT/(label+'.log')).open('x',encoding='utf8',newline='\n') as stream:
        stream.write(result.stdout+result.stderr)
    save(OUT/(label+'-receipt.json'), {'command':[str(x) for x in command], 'cwd':str(cwd),
                                    'exit':result.returncode, 'utc':datetime.now(timezone.utc).isoformat()})
    return result
