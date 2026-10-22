from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path('F:/mb-product-analytics-r30-20261021')
OUT = Path(os.environ['TEMP']) / 'metodobase-r30-author-20261021' / 'rate-fixture-after'
OUT.mkdir()
def save(name, value):
    with (OUT/name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
def source():
    files = []
    for folder in ('web', 'api', 'core', 'src', 'tests', 'config'):
        files += list((ROOT/folder).rglob('*.py'))
    return {str(p.relative_to(ROOT)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(files) if '__pycache__' not in p.parts}
def packages():
    return {d.metadata['Name']: {'version':d.version,
        'metadata_sha256':hashlib.sha256((d.read_text('METADATA') or '').encode()).hexdigest()}
        for d in importlib.metadata.distributions()}
os.chdir(ROOT)
before, deps = source(), packages()
save('sources.before.json', before)
save('packages.before.json', deps)
with (OUT/'pip.before.private.log').open('xb') as stream:
    pipbefore = subprocess.run([sys.executable,'-m','pip','check'],stdout=stream,stderr=subprocess.STDOUT).returncode
with (OUT/'pytest.private.log').open('xb') as stream:
    result = subprocess.run([sys.executable,'-X','utf8','-B','tests/run_isolated.py',
        
        'tests/test_product_analytics_http.py::test_exact_privacy_paths_all_methods_and_neighbours_are_unchanged','-q','--maxfail=5','--junitxml='+str(OUT/'pytest.xml')],
        stdout=stream,stderr=subprocess.STDOUT).returncode
after, depsafter = source(), packages()
save('sources.after.json',after)
save('packages.after.json',depsafter)
with (OUT/'pip.after.private.log').open('xb') as stream:
    pipafter = subprocess.run([sys.executable,'-m','pip','check'],stdout=stream,stderr=subprocess.STDOUT).returncode
xml = ET.parse(OUT/'pytest.xml')
cases = xml.findall('.//testcase')
counts = {'cases':len(cases), 'failures':len(xml.findall('.//failure')), 'errors':len(xml.findall('.//error')),
          'skipped':len(xml.findall('.//skipped'))}
summary = {'exit':result,'counts':counts,'sources':len(before),'packages':len(deps),'source_quiet':before==after,
           'packages_quiet':deps==depsafter,'pip':[pipbefore,pipafter]}
save('summary.json',summary)
print(json.dumps(summary))
