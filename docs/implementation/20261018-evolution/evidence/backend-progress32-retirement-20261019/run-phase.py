"""Exclusive closed receipts; provider URLs are read privately only in child."""
from pathlib import Path
import hashlib, importlib.metadata, json, os, subprocess, sys

ROOT=Path(sys.argv[1]);OUT=Path(sys.argv[2]);args=sys.argv[3:]
OUT.mkdir(exist_ok=False)
def write(name,blob):
    with (OUT/name).open('xb') as f:f.write(blob)
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
if '--postgres' in args:
    args.remove('--postgres')
    os.environ.update(json.loads(Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_bytes()))
    from tests import progress32_fixtures
    from tests.retirement32_owned import owned_database
    old=progress32_fixtures.owned_database
    progress32_fixtures.owned_database=lambda dialect,directory:owned_database(dialect,directory) if dialect=='postgresql' else old(dialect,directory)
    os.environ['RETIREMENT32_PRIVATE_LEASES']=str(Path(__file__).parent/'leases')
def snapshot():
    paths=[p for stem in ['web','api','core','config','tests'] for p in (ROOT/stem).rglob('*.py') if '__pycache__' not in p.parts]
    packages={d.metadata['Name'].lower().replace('_','-'):{'version':d.version,'METADATA':hashlib.sha256((d.read_text('METADATA') or '').encode()).hexdigest()} for d in importlib.metadata.distributions()}
    assert len(packages)==89
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'packages':packages,'python':hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),'base':hashlib.sha256(Path(sys._base_executable).read_bytes()).hexdigest()}
before=snapshot();write('before.json',(json.dumps(before,indent=2)+'\n').encode())
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);write('pip-before.raw.log',pip.stdout+pip.stderr);assert pip.returncode==0
import pytest
result=pytest.main(args+['--junitxml='+str(OUT/'results.xml'),'-o','cache_dir='+str(OUT/'pytest-cache')])
after=snapshot();write('after.json',(json.dumps(after,indent=2)+'\n').encode());assert before==after
pip2=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);write('pip-after.raw.log',pip2.stdout+pip2.stderr);assert pip2.returncode==0
write('quiet.json',(json.dumps({'exact':True,'sources':len(before['sources']),'packages':len(before['packages']),'pip_before':pip.returncode,'pip_after':pip2.returncode,'exit':result},indent=2)+'\n').encode())
raise SystemExit(result)
