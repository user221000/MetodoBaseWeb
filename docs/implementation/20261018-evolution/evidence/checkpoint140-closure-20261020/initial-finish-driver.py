"""Finish the preserved checkpoint with one Git RAW read per CRLF path."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
T = Path('C:/Users/Consu/AppData/Local/Temp')
O = T/'metodobase-checkpoint140-20261020'
P = D/'evidence/checkpoint140-closure-20261020'
BASE = '52d2d30ff0096015a7ca94325bb1da3e6c1f4c6d'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
encode = lambda value: (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()


def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=R, capture_output=True, check=check)


assert git('rev-parse', 'HEAD').stdout.decode().strip() == BASE
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
prior = json.loads(git('show', BASE+':docs/implementation/20261018-evolution/TRAZABILIDAD.json').stdout)
criteria = lambda value: {row['id']: {key: row[key] for key in ('fuente', 'seccion', 'problema', 'criterio_exacto')} for row in value['requisitos']}
assert len(data['requisitos']) == 140 and criteria(data) == criteria(prior)
imports = json.loads((P/'imports.json').read_bytes())
paths = [path for entry in imports for path in entry['hashes']]
for name in ['SESION_NAVEGADOR_R31_CI_MAP.json', 'SESION_NAVEGADOR_R31_IMPLEMENTACION.md',
             'SESION_NAVEGADOR_R31_NATIVE_SNAPSHOT.json', 'SESION_NAVEGADOR_R31_NATIVE_CURRENT_MAP.json',
             'NOTIFICACIONES_R27_CONTRATO36.md', 'NOTIFICACIONES_R27_RUNBOOK.md', 'SESION_NAVEGADOR_R31_WIRE.json']:
    paths.append('docs/implementation/20261018-evolution/'+name)
check = git('diff', '--cached', '--check', check=False)
(O/'whitespace-cached-RAW.stdout').write_bytes(check.stdout)
cr, cache = set(), {}
for line in check.stdout.decode().splitlines():
    match = re.fullmatch(r'(.+):(\d+): trailing whitespace\.', line)
    if not match:
        continue
    path, num = match.group(1), int(match.group(2))
    assert path in paths, path
    if path not in cache:
        cache[path] = git('show', ':'+path).stdout.split(b'\n')
    value = cache[path][num-1]
    assert value.endswith(b'\r') and not value[:-1].endswith((b' ', b'\t'))
    cr.add(path)
attrs = git('show', ':.gitattributes').stdout.replace(b'\r\n', b'\n').rstrip(b'\n')+b'\n'
for path in sorted(cr):
    entry = (path+' whitespace=cr-at-eol\n').encode()
    if entry not in attrs:
        attrs += entry
(R/'.gitattributes').write_bytes(attrs)
git('-c', 'core.autocrlf=false', 'add', '--', '.gitattributes')
git('diff', '--cached', '--check')
untracked = json.loads((O/'untracked-before.json').read_bytes())
assert len(untracked) == 537 and all(sha((R/path).read_bytes()) == value for path, value in untracked.items())
assert all(git('show', ':'+path).stdout == (R/path).read_bytes() for path in paths)
assert all(path.startswith('docs/') or path == '.gitattributes' for path in git('diff', '--cached', '--name-only').stdout.decode().splitlines())
checked = subprocess.run([sys.executable, '-B', '-X', 'utf8', 'scripts/implementation_registry.py', '--check'], cwd=R, capture_output=True)
(O/'registry-final.stdout').write_bytes(checked.stdout)
(O/'registry-final.stderr').write_bytes(checked.stderr)
assert checked.returncode == 0
(P/'finish-driver.py').write_bytes(Path(__file__).read_bytes())
(P/'owned-loop-stop.json').write_bytes((O/'owned-loop-stop.json').read_bytes())
receipt = {'base': BASE, 'requirements': 140, 'previous_criteria_exact': 140,
    'proof_files_imported': sum(row['files'] for row in imports), 'docs_imported': 6,
    'existing_wire_preserved_exact': True, 'untracked_preserved': 537,
    'product_imported': False, 'MAIN_schema': 35, 'SEC19_verified_local': True,
    'global_acceptance': False, 'CRLF_paths_preserved': sorted(cr),
    'initial_refusal': 'The wire contract already existed, byteexact to final8a; preserved.',
    'owned_loop_stop': 'Only the attributed author Python read loop stopped after PID/birth validation. All staged work preserved; continuation caches Git RAWs per path.'}
(P/'receipt.json').write_bytes(encode(receipt))
git('-c', 'core.autocrlf=false', 'add', '-f', '--', P.relative_to(R).as_posix())
git('diff', '--cached', '--check')
git('commit', '-m', 'Close independent SEC19 and record frozen web browser and notification candidates')
assert not git('status', '--porcelain', '-uno').stdout.strip()
result = {'head': git('rev-parse', 'HEAD').stdout.decode().strip(), **receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps({key: value for key, value in result.items() if key != 'CRLF_paths_preserved'}))
