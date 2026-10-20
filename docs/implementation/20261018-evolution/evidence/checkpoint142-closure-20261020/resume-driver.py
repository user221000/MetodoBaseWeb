from pathlib import Path
import hashlib,json,re,subprocess,sys
R=Path('F:/MetodoBaseWeb-execution-20261018')
D=R/'docs/implementation/20261018-evolution'
O=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint142-20261020')
BASE='4775eff5619b695266c63661d8cb0323100e3703'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
encode=lambda obj:(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
git=lambda *args:subprocess.check_output(['git',*args],cwd=R)
assert git('rev-parse','HEAD').decode().strip()==BASE
assert not git('diff','--cached','--name-only').strip()
proof=D/'evidence/checkpoint142-closure-20261020'
imports=json.loads((proof/'imports.json').read_bytes())
paths=[name for row in imports for name in row['hashes']]
extra=['docs/implementation/20261018-evolution/'+name for name in ['CUENTA_SEGURIDAD37_WIRE.json','CUENTA_SEGURIDAD37.md','CUENTA_SEGURIDAD37_PG_PLAN.json','NOTIFICACIONES_R27_COHERENCIA_MONETARIA36.md']]
untracked=json.loads((O/'untracked-before.json').read_bytes())
p=D/'TRAZABILIDAD.json';d=json.loads(p.read_bytes())
for row in d['requisitos']:
 row['evidencia']=[name.replace('backend-account-security37-pg-author-20261020/summary.json','backend-account-security37-pg-author-20261020/gates.json')for name in row['evidencia']]
p.write_bytes(encode(d))
old=json.loads(git('show',BASE+':docs/implementation/20261018-evolution/TRAZABILIDAD.json'))
by_id={row['id']:row for row in d['requisitos']}
assert len(by_id)==144 and all(all(by_id[row['id']][key]==row[key]for key in ['fuente','seccion','problema','criterio_exacto'])for row in old['requisitos'])
(proof/'resume-driver.py').write_bytes(Path(__file__).read_bytes())
(proof/'framing-correction.json').write_bytes(encode({'initial_registry_check':'failed before staging: account37 PG producer uses gates.json, not summary.json','correction':'reference only; producer RAW unchanged'}))
checked = subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True)
(O/'registry.stdout').write_bytes(checked.stdout);(O/'registry.stderr').write_bytes(checked.stderr)
assert checked.returncode == 0
git('-c','core.autocrlf=false','add','-f','--',*paths,*extra,proof.relative_to(R).as_posix())
controls = ['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md']
git('-c','core.autocrlf=true','add','--renormalize','--',*[(D/name).relative_to(R).as_posix() for name in controls])
check = subprocess.run(['git','diff','--cached','--check'],cwd=R,capture_output=True)
(O/'whitespace-before.stdout').write_bytes(check.stdout)
cached,cr = {},set()
for line in check.stdout.decode().splitlines():
    match = re.fullmatch(r'(.+):(\d+): trailing whitespace\.',line)
    if match:
        name,number = match.group(1),int(match.group(2))
        assert name in paths+extra,name
        if name not in cached:cached[name] = git('show',':'+name).split(b'\n')
        raw = cached[name][number-1]
        assert raw.endswith(b'\r') and not raw[:-1].endswith((b' ',b'\t'))
        cr.add(name)
attrs = git('show',':.gitattributes').replace(b'\r\n',b'\n').rstrip()+b'\n'
for name in sorted(cr):
    entry = (name+' whitespace=cr-at-eol\n').encode()
    if entry not in attrs:attrs += entry
(R/'.gitattributes').write_bytes(attrs)
git('-c','core.autocrlf=false','add','--','.gitattributes')
git('diff','--cached','--check')
assert all(sha((R/name).read_bytes()) == digest for name,digest in untracked.items())
assert all(git('show',':'+name) == (R/name).read_bytes() for name in paths+extra)
assert all(name.startswith('docs/') or name == '.gitattributes' for name in git('diff','--cached','--name-only').decode().splitlines())
receipt = {'base':BASE,'requirements':144,'previous_criteria_exact':144,'proof_files_imported':sum(row['files']for row in imports),'docs_imported':len(extra),'untracked_preserved':537,'product_imported':False,'MAIN_schema':35,'native_diagnostic_passed':2,'original_native_15_accepted':False,'global_acceptance':False,'CRLF_paths_preserved':sorted(cr)}
(proof/'receipt.json').write_bytes(encode(receipt))
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
git('diff','--cached','--check')
git('commit','-m','Record reviewed web DOM repair and isolated account PostgreSQL and finite scanner candidates')
assert not git('status','--porcelain','-uno').strip()
result = {'head':git('rev-parse','HEAD').decode().strip(),**receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
