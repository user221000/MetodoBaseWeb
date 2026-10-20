from pathlib import Path
import hashlib,json,re,subprocess,sys
R=Path('F:/MetodoBaseWeb-execution-20261018')
D=R/'docs/implementation/20261018-evolution'
O=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint141-20261020')
BASE='b17c08efe9c7debff3d98321b59e164ee42803e5'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
encode=lambda obj:(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
def git(*args,check=True):return subprocess.run(['git',*args],cwd=R,capture_output=True,check=check)
assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
assert not git('diff','--cached','--name-only').stdout.strip()
proof=D/'evidence/checkpoint141-closure-20261020'
imports=json.loads((proof/'imports.json').read_bytes())
paths=[p for e in imports for p in e['hashes']]
untracked=json.loads((O/'untracked-before.json').read_bytes())
new=[(ident,)for ident in ['SEC25','QA-25','QA-26','QA-27']]
p=D/'TRAZABILIDAD.json'
d=json.loads(p.read_bytes())
for row in d['requisitos']:
 row['evidencia']=[v.replace('root-sec25-money36-author-20261020/summary.json','root-sec25-money36-author-20261020/phases.json')for v in row['evidencia']]
p.write_bytes(encode(d))
(proof/'resume-driver.py').write_bytes(Path(__file__).read_bytes())
(proof/'framing-correction.json').write_bytes(encode({'initial_registry_check':'failed before staging; SEC25 evidence reference named summary.json instead of existing phases.json','change':'reference only, producer RAW unchanged'}))
checked = subprocess.run([sys.executable, '-B', '-X', 'utf8', 'scripts/implementation_registry.py', '--render', '--check'], cwd=R, capture_output=True)
(O/'registry.stdout').write_bytes(checked.stdout)
(O/'registry.stderr').write_bytes(checked.stderr)
assert checked.returncode == 0
git('-c', 'core.autocrlf=false', 'add', '-f', '--', *paths, proof.relative_to(R).as_posix())
controls = ['TRAZABILIDAD.json', 'TRAZABILIDAD.md', 'ESTADO.md', 'ENTREGA.md', 'VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md', 'NUEVOS_HALLAZGOS.md']
git('-c', 'core.autocrlf=true', 'add', '--renormalize', '--', *[(D/name).relative_to(R).as_posix() for name in controls])
check = git('diff', '--cached', '--check', check=False)
(O/'whitespace-before.stdout').write_bytes(check.stdout)
cached = {}
cr = set()
for line in check.stdout.decode().splitlines():
    match = re.fullmatch(r'(.+):(\d+): trailing whitespace\.', line)
    if match:
        path, num = match.group(1), int(match.group(2))
        assert path in paths, path
        if path not in cached:
            cached[path] = git('show', ':'+path).stdout.split(b'\n')
        value = cached[path][num-1]
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
assert all(sha((R/path).read_bytes()) == digest for path, digest in untracked.items())
assert all(git('show', ':'+path).stdout == (R/path).read_bytes() for path in paths)
assert all(path.startswith('docs/') or path == '.gitattributes' for path in git('diff', '--cached', '--name-only').stdout.decode().splitlines())
receipt = {'base': BASE, 'requirements': 144, 'previous_criteria_exact': 140, 'new_ids': [item[0] for item in new], 'proof_files_imported': len(paths), 'untracked_preserved': 537, 'product_imported': False, 'MAIN_schema': 35, 'R31_product_integrated': True, 'MAIN_HTTP': {'passed':110, 'failed':0}, 'native_browser_accepted': False, 'global_acceptance': False, 'CRLF_paths_preserved': sorted(cr)}
(proof/'receipt.json').write_bytes(encode(receipt))
git('-c', 'core.autocrlf=false', 'add', '-f', '--', proof.relative_to(R).as_posix())
git('diff', '--cached', '--check')
git('commit', '-m', 'Record integrated web session and preserve rejected native and isolated account notification evidence')
assert not git('status', '--porcelain', '-uno').stdout.strip()
result = {'head': git('rev-parse', 'HEAD').stdout.decode().strip(), **receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
