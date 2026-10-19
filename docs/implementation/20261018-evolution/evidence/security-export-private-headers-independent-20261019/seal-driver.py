from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

ROOT=Path(r'F:\mb-security-export-headers-peer-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-export-private-headers-independent-20261019'
HEAD='2002959122f142162192a122fad7ba2cafbb12b1'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert not git('status','--porcelain','--untracked-files=no')
assert (OUT/'.gitattributes').read_bytes()==b'* -text\n'
assert not (OUT/'manifest.json').exists() and not (OUT/'source.json').exists()
s=json.loads((OUT/'summary.json').read_bytes())
assert s['outcomes']=={'passed':20,'failure':0,'error':0,'skipped':0}
assert s['exit']==s['pip_before']==s['pip_after']==0 and s['sources_packages_python_exact']
assert json.loads((OUT/'before.json').read_bytes())==json.loads((OUT/'after.json').read_bytes())
cases=json.loads((OUT/'cases.STRUCTURAL.json').read_bytes())
assert len(cases)==len({c['case'] for c in cases})==20
qa=[c for c in cases if c['case'].startswith('tests.security_export_headers_qa_original::')]
assert len(qa)==2 and all('test_eighth_export_cursor_is_lowercase_only_and_does_not_authorize_other_actor[' in c['case'] for c in qa)
assert sha((OUT/'security_export_headers_qa_original.py').read_bytes())=='44941ef6403aa7ef628d50bb551019c9cce3412d97c00d9d4cf3f5f28866df2b'
(OUT/'seal-driver.py').write_bytes(Path(__file__).read_bytes())
review='''Revisión independiente: PASS_EXPORT_PRIVATE_HEADERS_SCOPED

Fuente2002959122f142162192a122fad7ba2cafbb12b1 contra b7f8e129251dfd5216f811ba77d0b6183ca76735. Se autenticaron los13 primarios RAW declarados por source.json del autor y los dos blobs GitLF de middleware/test. El producto cambia sólo web/middleware/security_headers.py. Una inversa independiente de todo el archivo, además de su AST completo, recupera exactamente el middleware GitLF del parent; no se modifica auth, factor, DTO, cursor, persistencia, router, DDL, lector, catálogo, UI ni CI.

El conjunto fijo contiene exactamente /api/usuario/privacidad/exportar y la variante con un solo slash final. Esa clasificación se une a los límites ya existentes para excepción privada500, Referrer-Policy y Cache-Control. Sigue siendo un exporter GET-only y el slash conserva su redirect; la política CSP normal con nonce permanece. No se amplía el prefijo de privacidad ni se acepta CSP arbitraria del downstream.

Primera ejecución independiente20/20 verde, sin fallo/error/skip y sin ajustes posteriores. Se repitieron los dos casos del canario QA con el archivo RAW exacto44941ef6403aa7ef628d50bb551019c9cce3412d97c00d9d4cf3f5f28866df2b. Usan las dos fábricas reales, SQLite migrada32, registro/login reales y permisos de consentimiento/export; la entrada uppercase sigue siendo422 y ahora mantiene no-referrer/no-store/nosniff. No se cambió su aserción ni se sustituyó auth.

Dieciocho canarios propios añaden HEAD/OPTIONS/DELETE405 y sus redirects307 reales con query preservada; fallos reales del exporter donde el generic handler a su vez lanza o devuelve503 inválido; respuestas202/303/429/503 con headers downstream hostiles en ambos paths exactos; y cuatro vecinos que mantienen la política general. Los ocho casos HTTP reales incluyen los dos QA; las otras doce pruebas son unidades explícitas de middleware, con rutas sintéticas que no se presentan como rutas de producto. La respuesta500 de fallback fue opaca frente al sentinel sintético, conservó headers privados y no devolvió proyección. No se afirma seguridad general de logs ni una fuga real de PII.

Los10313 archivos observados (10311 tracked más las dos fuentes propias/copia QA),89 metadatos de distribución y SHA del ejecutable Python permanecieron idénticos durante la prueba. pipcheck devolvió0 antes y después. Los metadatos de paquetes no constituyen hash de todos los bytes instalados. JUnit/stdout/stderr originales quedan privados con recibos de hash; el público sólo contiene IDs/outcomes y demás proyecciones escaneadas. Ningún archivo de producto cambió en el worktree revisor.

Aceptación sólo de esta corrección focal de headers privados. No se reatribuye aceptación a una composición posterior ni se cierran R25/R31 globales, retiro cuando auth del parent no funciona, UI, suite completa, logging separado, PostgreSQL/restore, Chrome, QEMU, proveedor, producción o revisión clínica. El defecto de origen es cobertura incompleta de headers en errores, sin afirmar divulgación de datos personales.
'''
(OUT/'review.md').write_bytes(review.encode('utf8'))
source={'source_head':HEAD,'parent':'b7f8e129251dfd5216f811ba77d0b6183ca76735',
    'verdict':'PASS_EXPORT_PRIVATE_HEADERS_SCOPED','cases':20,'same_QA_cases':2,'own_cases':18,
    'actual_migrated32_SQLite_factory_cases':8,'explicit_middleware_unit_cases':12,
    'QA_source_sha256':'44941ef6403aa7ef628d50bb551019c9cce3412d97c00d9d4cf3f5f28866df2b',
    'author_source_sha256':'8bb645d7b00373eb031b25f516ac0a7824c14e82752cb131adcb55a3be9b18bb',
    'product_files_changed_by_peer':0,'scope':'Focal middleware export privacy only; no global R25/R31, PG, browser, VM, provider, production or data-disclosure claim.'}
(OUT/'source.json').write_bytes((json.dumps(source,indent=2)+'\n').encode())
scanner=ast.parse(Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'))
fn=next(n for n in scanner.body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<maintained-public-scanner>','exec'))
for p in OUT.rglob('*'):
    if p.is_file():scan(p.read_bytes(),p.relative_to(OUT).as_posix())
manifest={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
    for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in {'.gitattributes','manifest.json'}}
(OUT/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
files=[p.relative_to(ROOT).as_posix() for p in sorted(OUT.rglob('*')) if p.is_file()]
subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*files],cwd=ROOT,check=True,capture_output=True)
for name in files:assert git('show',':'+name)==(ROOT/name).read_bytes(),name
subprocess.run(['git','commit','-m','Record independent export privacy header security review'],cwd=ROOT,check=True,capture_output=True)
print(json.dumps({'commit':git('rev-parse','HEAD').decode().strip(),'files':len(files),
    'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'source_sha256':sha((OUT/'source.json').read_bytes())}))
