"""Isolate missing companion globals without changing products, old assertions or archives."""
from pathlib import Path
import hashlib
import json
import subprocess

TMP = Path(r'C:\Users\Consu\AppData\Local\Temp')
OUT = TMP / 'metodobase-member-vm-causality-20261019'
SOURCES = {
    'historical30': Path(r'F:\MetodoBaseWeb-linux-lab-20261019\evidence\mfa-ci31-historical-offline2-20261019\source'),
    'current31': Path(r'F:\mb-mfa31-compose-20261019'),
}
OUT.mkdir(exist_ok=False)
(OUT / 'driver.py').write_bytes(Path(__file__).read_bytes())
loader = OUT / 'causal-loader.cjs'
loader.write_text("""'use strict';
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const root=path.resolve(process.argv[2]),mode=process.argv[3];
const filename=path.join(root,'tests/e2e/member_link_consumers.cjs');
const original=fs.readFileSync(filename,'utf8');
const needle='};box.window=box;vm.createContext(box);';
const injection='};box.PlanDayUI={mount(){return {setSource(){},invalidate(){}};}};box.PublicationConsumption={mount(){return {invalidate(){}};}};box.window=box;vm.createContext(box);';
if(original.split(needle).length!==2)throw Error('Unexpected frozen fixture shape');
if(!['original','missing-globals-only'].includes(mode))throw Error('Unexpected probe mode');
const content=mode==='original'?original:original.replace(needle,injection);
if(mode!=='original'&&content.replace(injection,needle)!==original)throw Error('Probe changed original assertions');
const entry=new Module(filename,module);entry.filename=filename;entry.paths=Module._nodeModulePaths(path.dirname(filename));entry._compile(content,filename);
""", encoding='utf8')
paths = ['tests/e2e/member_link_consumers.cjs', 'web/templates/usuario_vinculos.html',
         'web/static/js/vinculos-contexto.js', 'web/static/js/vinculos-ui.js', 'web/static/js/vinculos-lectura.js',
         'web/static/js/plan-diario-datos.js', 'web/static/js/plan-diario-ui.js', 'web/static/js/plan-publicacion-consumo.js']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = {name: {path: sha(root/path) for path in paths} for name, root in SOURCES.items()}
reports = {}
for name, root in SOURCES.items():
    reports[name] = {}
    for mode in ['original', 'missing-globals-only']:
        result = subprocess.run([r'C:\Program Files\nodejs\node.exe', str(loader), str(root), mode],
                                cwd=root, capture_output=True, timeout=30, check=False)
        (OUT/(name+'-'+mode+'.stdout.json')).write_bytes(result.stdout)
        (OUT/(name+'-'+mode+'.stderr.log')).write_bytes(result.stderr)
        data = json.loads(result.stdout)
        reports[name][mode] = {'exit': result.returncode, 'total': data['total'], 'passed': data['passed'],
                              'failed_cases': [row['case'] for row in data['results'] if not row['passed']]}
after = {name: {path: sha(root/path) for path in paths} for name, root in SOURCES.items()}
assert before == after
summary = {'reports': reports, 'before': before, 'after': after,
           'all_targeted_sources_unchanged': True,
           'scope': 'Causality only: original fixed-API DOM lacks two globals newly required by R24. Passive companion mount stubs allow old reader assertions to execute. This does NOT validate actual shopping/consumption behavior, browser, HTTP, CI acceptance or make the historical original test green. No source/archive/assertion files changed.'}
(OUT/'summary.json').write_bytes((json.dumps(summary, indent=2)+'\n').encode())
print(json.dumps({'reports': reports, 'all_targeted_sources_unchanged': True, 'scope': summary['scope']}))
for report in reports.values():
    assert report['original']['passed'] == 13 and report['original']['total'] == 16 and report['original']['exit'] == 1
    assert report['missing-globals-only']['passed'] == 16 and report['missing-globals-only']['exit'] == 0
