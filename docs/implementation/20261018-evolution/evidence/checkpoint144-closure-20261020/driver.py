"""Record integrated account37 and its bounded independent acceptance."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
O = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint144-20261020')
BASE = 'e8afd3f14334d5273d9d6a043a6400e933e51b15'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
enc = lambda obj: (json.dumps(obj, ensure_ascii=False, indent=2)+'\n').encode()
git = lambda *args: subprocess.check_output(['git', *args], cwd=R)
assert git('rev-parse', 'HEAD').decode().strip() == BASE
assert not git('status', '--porcelain', '-uno').strip() and not O.exists()
O.mkdir()
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
criteria = lambda value: {row['id']: {key: row[key] for key in ['fuente', 'seccion', 'problema', 'criterio_exacto']} for row in value['requisitos']}
old = criteria(data); assert len(old) == 145
untracked = {name: sha((R/name).read_bytes()) for name in git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0') if name and (R/name).is_file()}
assert len(untracked) == 537
(O/'untracked-before.json').write_bytes(enc(untracked))
paragraph = ('La rama principal local ya integra cuenta y esquema37 sobre notificaciones36/UI27. Los27 archivos de producto coinciden con la composición revisada3c3; el wire37 y las primitivas MFA/R31 se conservan. QA-28 queda verificado localmente: un401 de recurso retira acceso RAM y proyecciones al recibir cabeceras, con fence de la identidad capturada. No refresca ni repite, no retira una sesiónB nueva y no afirma revocación global. Una contraseña primaria incorrecta y los errores403/422 siguen siendo corregibles. Seguridad independiente pasa48 casos propios (42VM y6HTTP) más10DOM del autor. ROOT conserva todos los RED originales y residuales.\n\n'
    'Sobre la integración real1e01 pasan234 casos pytest mixtos: servicios, HTTP y migraciones SQLite; incluyen los replays R31 deliberados. No son234 casos HTTP ni criterios semánticos nuevos. Fuentes1315/Python/92 versiones instaladas/Node permanecen estables. La selección Node inicial pasa126; el companion18 no ejecuta aserciones por checkout CRLF distinto de su GitLF congelado. Un atributo de checkout exacto conserva ese blob y sus aserciones; después pasa18 en88ff. La página pública pasa8VM, comprobando ocho líneas PASS y su JSON final; el parser genérico que esperaba un único JSON quedó rechazado y preservado. Se aceptan152 resultados Node seleccionados repartidos en fases, sin sumarle las repeticiones. Se corrige también el encuadre de143: los78 casos de36 eran mixtos, no78HTTP.\n\n'
    'QA PostgreSQL37 independiente pasa30 casos funcionales,12HTTP correctivos y un restore poblado. El alias del primer gate no comprobaba el pool real de doce HTTP; ese alcance se rechazó y la repetición corrigió sólo la composición del fixture. El primer restore falló porque su semilla pendiente sufría un reset histórico que incrementaSV; se conserva el fallo y sólo se cambió la semilla, manteniendo75 aserciones históricas y las nuevas. Ocho UUID cerraron porDROP normal, cero sesiones y ausencia fresca. Las fotos de1279 fuentes,92 distribuciones y8084 archivos instalados permanecieron estables. Este gate deQA está ligado a su fuente5806, con backend actual exacto; no constituye nueva ejecuciónPG desdeMAIN.\n\n'
    'UX-09/R13 tiene16 reproducciones geométricas RED en Chrome con DOM inerte declarado y sin SQL. El autor congeló una reparación en tres CSS78aa, con4 contratos SSR antes/después y sin cambiar scripts o plantillas. QA prepara su replay y el navegador completo37:15 grupos R31 y18 nuevos, fixture actual y proveedores dobles declarados. Ese gate final todavía no empezó; no se atribuye a37 la aceptación nativa anterior de35.\n\n'
    'R05 conserva el escaneo real405 RED11016. Seguridad propuso11015 ubicaciones y ROOT revisa su vinculación. Para la última ubicación se localizó el productor histórico exacto y la comprobación independiente original de los24 checksums; no se recuperó ni reconstruyó auth-guard. La adenda independiente admite esa procedencia con1positivo/10negativos. V4 sólo se prepara:877 rutas y56285pins,641 registros v3 intactos y85 sustituciones explícitas conservadas en el ZIP histórico. No está integrado ni equivale a un escaneo final aprobado. CI37/suite amplia, imagen actual con ExpatM2 y navegador37 siguen en curso.\n\n'
    'Los145 criterios permanecen exactos, incluidos los92 originales; los537 archivos untracked están intactos. Free:10 clientes,1 plan por cliente al día,10 planes totales por gimnasio al día y mensual20 sin cambio. Alcance exclusivo del servicio web. Sin push, PR, despliegue, cargos ni envíos reales. Retención, países, SLO y piloto conservan las decisiones externas pendientes, sin repetir consultas ya realizadas.')
for row in data['requisitos']:
    ident = row['id']
    if ident == 'QA-28':
        row['estado'] = row['implementacion'] = row['validacion'] = 'verificado'
        row['bloqueo'] = None
        row['commits'].extend(['12b4b11322060255eb7ca894520ea0652fe33543', '28e78c67c1761d25a1d79771ae356208eeecc88e', '5666a9ba8e03741ae6e983b6d21dfd93de466836', BASE])
        row['pruebas'].append('Final ROOT144Node/16HTTP en candidato12b4 y seguridad48propios+10DOM PASS. ActualMAIN234pytest mixtos y126Node inicial+18LFcheckout+8página pública en fases; canarias originales, residual4GETRED y relojes15+3companion preservados. Sin nativo37/proveedor real.')
        row['evidencia'].extend(['evidence/root-account37-qa28-author-20261020/phases.json', 'evidence/security-account37-ui401-body-independent-20261020/headers401-red-result.json', 'evidence/security-account37-ui401-independent-20261020/http-result.json', 'evidence/root-main37-current-20261020/summary.json'])
        row['revisor'] = 'Seguridad independiente28e:42VM propios+6HTTP real y10DOM; crítico12b4 acotado al namespace37. ROOT verifica integración real y conserva errores de framing sin debilitar aserciones.'
    if ident in {'R16', 'B19', 'UX-15', 'R31', 'R27', 'R26', 'R19'}:
        row['observaciones'].append('Checkpoint144: cuenta37 integrada5666 con QA-28 corregido/peer58; ROOTactual234pytest mixtos yNode126+18+8fases. PeerPG37:30funcionales+12HTTPcorrectivos+restorepoblado75históricosintactos,8UUIDcerradasnormalmente; alcancefuente5806. Native37/CIimagen/proveedorrealpendientes; no cierre completo del padre.')
        row['evidencia'].extend(['evidence/root-main37-current-20261020/summary.json', 'evidence/qa-account37-pg-restore-independent-20261020/final-phase-summary.json'])
    if ident in {'R05', 'QA-01', 'QA-07', 'OPS07'}:
        row['observaciones'].append('Checkpoint144: escaneo405RED11016 conserva vigencia. Propuesta11015+adendaproductor histórico1 (AST24SHAreadbytes/outputoriginal6d09/QA24recompute130.434sdespués) sin recuperar/reconstruirfuente. V4enpreparación877rutas56285pins/641oldexact85reemplazados; nointegrado/fullscanPASS. CIamplia/imagen37enpreparación.')
    if ident in {'R13', 'UX-09'}:
        row['observaciones'].append('Checkpoint144: QA16/16REDgeométricoChromeinertesinSQL; autor78aa tresCSS y4SSRcriteriosbefore/after, sin cambios scripts/templates. Peerafter/nativo37pendientes; cambio aúnnointegrado.')
assert criteria(data) == old
(D/'TRAZABILIDAD.json').write_bytes(enc(data))
for name in ['VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md', 'NUEVOS_HALLAZGOS.md', 'CUENTA_SEGURIDAD37.md']:
    path = D/name; assert b'## Checkpoint144' not in path.read_bytes()
    text = paragraph if name != 'NUEVOS_HALLAZGOS.md' else 'QA-28 verificado localmente:1e01/12b4 y revisión independiente28e. Todos los RED se conservan, incluidos cuatro GET retenidos hastaJSON en el candidato intermedio. Fix final retira alheader401 con fence exacto; MFAglobal/reauthcorrigible intactos. La corrección de checkoutLF y los parsers de evidencia son framing, no defectos de producto ni criterios nuevos.'
    path.write_bytes(path.read_bytes().rstrip()+('\n\n## Checkpoint144\n\n'+text+'\n').encode())
state = (D/'ESTADO.md').read_text(encoding='utf8'); history = state[state.index('## Observaciones hist\u00f3ricas'):]
(D/'ESTADO.md').write_bytes(('# Estado de implementación\n\nCheckpoint144 local: esquema37 y145 requisitos.\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n\n'+history+'\n## Checkpoint144\n\n'+paragraph+'\n').encode())
(D/'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n').encode())
checked = subprocess.run([sys.executable, '-B', '-X', 'utf8', 'scripts/implementation_registry.py', '--render', '--check'], cwd=R, capture_output=True)
(O/'registry.stdout').write_bytes(checked.stdout); (O/'registry.stderr').write_bytes(checked.stderr); assert checked.returncode == 0
proof = D/'evidence/checkpoint144-closure-20261020'; proof.mkdir()
(proof/'.gitattributes').write_bytes(b'* -text\n'); (proof/'driver.py').write_bytes(Path(__file__).read_bytes())
receipt = {'base': BASE, 'requirements': 145, 'previous_criteria_exact': 145, 'untracked_preserved': 537, 'product_changed': False,
    'MAIN_schema': 37, 'pytest_mixed_current': 234, 'Node_accepted_across_phases': 152, 'QA28_verified_local': True,
    'native37_or_CI_or_global_R05_accepted': False, 'fresh_scan_remaining': 11016}
(proof/'receipt.json').write_bytes(enc(receipt))
git('-c', 'core.autocrlf=false', 'add', '-f', '--', proof.relative_to(R).as_posix())
names = ['TRAZABILIDAD.json', 'TRAZABILIDAD.md', 'ESTADO.md', 'ENTREGA.md', 'VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md', 'NUEVOS_HALLAZGOS.md', 'CUENTA_SEGURIDAD37.md']
git('-c', 'core.autocrlf=true', 'add', '--renormalize', '--', *[(D/name).relative_to(R).as_posix() for name in names])
git('diff', '--cached', '--check')
assert all(sha((R/name).read_bytes()) == digest for name, digest in untracked.items())
assert all(name.startswith('docs/') for name in git('diff', '--cached', '--name-only').decode().splitlines())
git('commit', '-m', 'Record integrated web37 account review current regressions and remaining delivery work')
assert not git('status', '--porcelain', '-uno').strip()
result = {'head': git('rev-parse', 'HEAD').decode().strip(), **receipt}
(O/'result.json').write_bytes(enc(result)); print(json.dumps(result))
