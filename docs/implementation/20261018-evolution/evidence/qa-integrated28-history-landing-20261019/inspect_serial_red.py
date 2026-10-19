"""Freeze an unsuccessful broad serial without reclassifying any failed criterion."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(r'F:\MetodoBaseWeb-execution-20261018')
OUT = Path(__file__).resolve().parent
PREFIX = 'qa-integrated28-history-landing'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')


proof = json.loads((OUT / (PREFIX + '-source.json')).read_text())
assert proof['accepted'] is False and len(proof['runs']) == 1 and proof['runs'][0]['label'] == 'serial'
before = json.loads((OUT / 'before-serial-source.json').read_text())
after = json.loads((OUT / 'after-serial-source.json').read_text())
assert before['sources'] == after['sources'] and before['packages'] == after['packages']
tree = ET.parse(OUT / (PREFIX + '-serial.xml')).getroot()
failures = []
for case in tree.findall('.//testcase'):
    for tag in ['failure', 'error']:
        failure = case.find(tag)
        if failure is None:
            continue
        classname = case.attrib.get('classname', '')
        parts = classname.split('.')
        filename = None
        for count in range(len(parts), 0, -1):
            candidate = '/'.join(parts[:count]) + '.py'
            if (ROOT / candidate).is_file():
                filename = candidate + ('::' + '::'.join(parts[count:]) if parts[count:] else '')
                break
        assert filename, classname
        nodeid = filename + '::' + case.attrib['name']
        path = 'serial-red-trace-' + str(len(failures) + 1) + '.txt'
        (OUT / path).write_text(failure.text or '', encoding='utf8')
        failures.append({'nodeid': nodeid, 'kind': tag, 'message': failure.attrib.get('message', ''),
                         'trace': path, 'trace_sha256': sha(OUT / path)})
assert failures
review = {'accepted': False, 'head': proof['head'], 'serial': proof['runs'][0], 'failures': failures,
          'sources': before['source_count'], 'packages': before['package_count'],
          'source_and_packages_still_identical': True, 'pip_before_after': [before['pip_check_exit'], after['pip_check_exit']],
          'shuffle_started': False, 'critical_coverage_guard_started': False,
          'scope': 'Unmodified full serial original JUnit/log/coverage retained. No case filtered, no criterion reinterpreted, no test/product edits. Separate focused reproduction may follow coordinator review.'}
save('serial-red-review.json', review)
files = {path.relative_to(OUT).as_posix(): sha(path) for path in sorted(OUT.rglob('*')) if path.is_file()}
save('serial-red-manifest.json', {'files': files, 'count': len(files), 'scope': 'All original unsuccessful serial artifacts except this manifest; no acceptance claim.'})
print(json.dumps({'head': proof['head'], 'sources': before['source_count'], 'packages': before['package_count'],
                  'failures': failures, 'review_sha256': sha(OUT / 'serial-red-review.json'),
                  'manifest_sha256': sha(OUT / 'serial-red-manifest.json')}))
