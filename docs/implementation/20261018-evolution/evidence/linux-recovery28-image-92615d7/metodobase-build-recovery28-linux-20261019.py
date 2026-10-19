import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import time

sys.dont_write_bytecode = True
lab = Path('F:/MetodoBaseWeb-linux-lab-20261019')
repo = Path('F:/MetodoBaseWeb-execution-20261018')
head = '92615d74ee3a4bd82333c4606cca7898eb324a88'
out = lab / 'evidence' / 'recovery28-image-92615d7'
out.mkdir(exist_ok=False)
paths = ['Dockerfile', '.dockerignore', 'requirements_web.lock', 'config', 'core', 'src',
         'api', 'web', 'utils', 'static', 'fonts', 'entrypoint.sh', 'alembic.ini', 'db_bootstrap.py']
archive = out / 'build-context.tar'
with archive.open('wb') as stream:
    subprocess.run(['git', 'archive', '--format=tar', head, *paths], cwd=repo, stdout=stream, check=True)
sha = lambda b: hashlib.sha256(b).hexdigest()
archive_hash = sha(archive.read_bytes())
members = {}
with tarfile.open(archive) as source:
    for member in source.getmembers():
        path = Path(member.name)
        assert not path.is_absolute() and '..' not in path.parts
        assert member.isdir() or member.isfile(), 'No links or special files allowed'
        assert not any(part == '.git' or part.startswith('.env') for part in path.parts)
        if member.isfile():
            assert member.name not in members
            members[member.name] = sha(source.extractfile(member).read())
assert members['entrypoint.sh'] == sha(subprocess.run(['git', 'show', head + ':entrypoint.sh'], cwd=repo, check=True, capture_output=True).stdout)
(out / 'input-files-private.json').write_text(json.dumps(members, indent=2) + '\n', encoding='utf-8')
spec = importlib.util.spec_from_file_location('guest_access', lab / 'scripts' / 'guest_access.py')
access = importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)
remote = '/home/lab/metodobase-recovery28-92615d7'
code = """import hashlib,io,pathlib,sys,tarfile
data=sys.stdin.buffer.read()
assert hashlib.sha256(data).hexdigest()==EXPECTED
root=pathlib.Path(DESTINATION)
root.mkdir(exist_ok=False)
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
 for member in archive.getmembers():
  p=pathlib.PurePosixPath(member.name)
  assert not p.is_absolute() and '..' not in p.parts and (member.isdir() or member.isfile())
  assert not any(part=='.git' or part.startswith('.env') for part in p.parts)
 archive.extractall(root,filter='data')
print('owned_context_verified')
""".replace('EXPECTED', repr(archive_hash)).replace('DESTINATION', repr(remote))
with archive.open('rb') as stream:
    transfer = access.run('/opt/metodobase-lab/python/bin/python3.12 -c ' + shlex.quote(code), stdin=stream, timeout=300)
(out / 'transfer.log').write_bytes(transfer.stdout + transfer.stderr)
assert transfer.returncode == 0
tag = 'metodobase-lab:recovery28-92615d7'
command = 'sudo docker build --label org.opencontainers.image.revision=' + head + ' --tag ' + tag + ' ' + remote
started = time.monotonic()
run = access.run(command, timeout=3000)
(out / 'build.log').write_bytes(run.stdout + run.stderr)
elapsed = time.monotonic() - started
summary = {'source_commit': head, 'context_scope': paths, 'archive_sha256': archive_hash,
           'archive_bytes': archive.stat().st_size, 'file_count': len(members),
           'source_inventory_sha256': sha(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()),
           'image_tag': tag, 'build_exit': run.returncode, 'build_seconds': elapsed,
           'archive_stable': sha(archive.read_bytes()) == archive_hash,
           'scope': 'isolated accepted recovery28 product composition; no main release or runtime validation',
           'artifact_sha256': {p.name: sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}}
(out / 'build-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'exit': run.returncode, 'elapsed_seconds': elapsed, 'file_count': len(members), 'archive_bytes': archive.stat().st_size}))
raise SystemExit(run.returncode)
