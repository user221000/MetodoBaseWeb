import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

root = Path('F:/MetodoBaseWeb-history-ui-20261019')
out = Path(__file__).resolve().parent
driver = out / 'test_history_headers.py'
sha = lambda b: hashlib.sha256(b).hexdigest()
expected = 'e2cc888f0919aa890003e040b093d0f672db633c009fb3b769e2e403f5058755'
assert sha(driver.read_bytes()) == expected
paths = ['api/app.py', 'web/routes/usuario.py', 'web/services/personal_history_cursor.py',
         'web/static/js/api.js', 'web/static/js/usuario-historial.js',
         'web/templates/usuario_historial.html', 'web/middleware/security_headers.py',
         'tests/test_personal_history_pagination.py', 'conftest.py', 'tests/run_isolated.py']
photo = lambda: {p: sha((root / p).read_bytes()) for p in paths}
before = photo()
head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, check=True, text=True).stdout.strip()
assert head == '49eb44124d36a0d0aeaf732d7f720d969f1d517c'
command = [sys.executable, 'tests/run_isolated.py', '-p', 'conftest', '--confcutdir=' + str(out),
           str(driver), '-q', '--junitxml=' + str(out / 'after-root.xml')]
run = subprocess.run(command, cwd=root, capture_output=True, timeout=90)
(out / 'after-root.log').write_bytes(run.stdout + run.stderr)
after = photo()
document = ET.parse(out / 'after-root.xml').getroot()
suites = [document] if document.tag == 'testsuite' else list(document)
counts = {k: sum(int(s.get(k, '0')) for s in suites) for k in ['tests', 'errors', 'failures', 'skipped']}
value = {'head': head, 'driver_sha256': expected, 'before': before, 'after': after,
         'sources_stable': before == after, 'exit': run.returncode, 'counts': counts,
         'scope': 'original eight root response-header assertions replayed after49eb441; not a broad R34 review',
         'artifacts': {p.name: sha(p.read_bytes()) for p in [driver, out / 'after-root.log', out / 'after-root.xml']}}
(out / 'after-root-source.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'exit': run.returncode, 'counts': counts, 'sources_stable': before == after}))
assert before == after and run.returncode == 0 and counts == {'tests': 8, 'errors': 0, 'failures': 0, 'skipped': 0}
