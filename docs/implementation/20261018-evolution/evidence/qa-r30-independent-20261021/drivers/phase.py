import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('F:/mb-qa-product-analytics-r30-20261021')
OUT = Path(__file__).parent
VENV = Path(sys.executable).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT)


def photo():
    names = set(git('ls-files', '--', 'api', 'web', 'core', 'tests', 'config', 'utils', 'src', 'servicios', 'conftest.py', 'db_bootstrap.py').decode().splitlines())
    names.update(git('ls-files', '--others', '--exclude-standard', '--', 'tests').decode().splitlines())
    source = {name: sha((ROOT / name).read_bytes()) for name in sorted(names) if (ROOT / name).is_file()}
    runtime = {'PYTHON_BINARY': sha(Path(sys.executable).read_bytes())}
    records = {}
    for dist in importlib.metadata.distributions():
        identity = dist.metadata['Name'] + ':' + dist.version
        record = Path(dist._path) / 'RECORD'
        assert record.is_file()
        records[identity] = sha(record.read_bytes())
        runtime[identity + '/METADATA'] = sha((Path(dist._path) / 'METADATA').read_bytes())
        for row in csv.reader(record.read_text(encoding='utf8').splitlines()):
            path = Path(dist.locate_file(row[0])).resolve()
            assert path.is_relative_to(VENV)
            if path.is_file() and path.suffix != '.pyc':
                runtime[str(path.relative_to(VENV)).replace('\\', '/')] = sha(path.read_bytes())
    assert len(records) == 92
    return {'source': source, 'records': records, 'runtime_installed': runtime}


phase = sys.argv[1]
directory = OUT / phase
directory.mkdir(exist_ok=False)
for driver in ('phase.py', 'offline.py'):
    (directory / driver).write_bytes((OUT / driver).read_bytes())
before = photo()
(directory / 'before.json').write_text(json.dumps(before, sort_keys=True, indent=2) + '\n')
head = git('rev-parse', 'HEAD').decode().strip()
for name in ['web/product_analytics_domain.py', 'web/product_analytics_baseline.py',
             'web/services/product_analytics.py', 'web/routes/product_analytics.py',
             'web/middleware/security_headers.py', 'api/app.py', 'web/main_web.py',
             *git('ls-files', '--others', '--exclude-standard', '--', 'tests').decode().splitlines()]:
    target = directory / 'source' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((ROOT / name).read_bytes())
started = time.monotonic()
with (directory / 'stdout.log').open('wb') as stdout, (directory / 'stderr.log').open('wb') as stderr:
    result = subprocess.run([sys.executable, '-X', 'utf8', str(OUT / 'offline.py'), *sys.argv[2:],
                             '-q', '--tb=short', '--junitxml=' + str(directory / 'junit.xml')], cwd=ROOT,
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), stdout=stdout, stderr=stderr, check=False)
after = photo()
(directory / 'after.json').write_text(json.dumps(after, sort_keys=True, indent=2) + '\n')
report = {'phase': phase, 'head': head, 'returncode': result.returncode, 'elapsed': time.monotonic() - started,
          'source_files': len(before['source']), 'RECORD_distributions': len(before['records']),
          'runtime_installed_entries': len(before['runtime_installed']), 'quiet': before == after,
          'before_sha256': sha((directory / 'before.json').read_bytes())}
(directory / 'result.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
print(json.dumps(report))
raise SystemExit(result.returncode or (0 if before == after else 71))
