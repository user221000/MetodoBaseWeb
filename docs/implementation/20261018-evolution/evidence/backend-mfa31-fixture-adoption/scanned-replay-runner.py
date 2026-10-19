"""Bounded fixture adoption; private raw outputs and scanned public projection."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path('F:/mb-mfa31-fixtures-20261019')
HERE = Path(__file__).parent
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/backend-mfa31-fixture-adoption'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def photo():
    names = subprocess.check_output(['git', '--no-replace-objects', 'ls-files', '-co', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')[:-1]
    return {'source': {name: sha((ROOT / name).read_bytes()) for name in sorted(set(names)) if not name.startswith('docs/') and (ROOT / name).is_file()},
        'packages': sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions())}


SECRET_PATTERNS = [
    rb'[0-9]{1,15}\.[0-9a-f]{64}\.[0-9a-f]{64}',
    rb'[A-Za-z0-9_-]+\.[0-9a-fA-F]{64}',
    rb'otpauth://[^\s\"\'<>]+',
    rb'(?i)(?:token|grant|challenge|recovery_code|secret)[=\"\x27:\s]+[A-Za-z0-9_-]{22,}',
]


def projected(raw):
    counts = []
    for pattern in SECRET_PATTERNS:
        raw, count = re.subn(pattern, b'[REDACTED-PRIVATE-CAPABILITY]', raw)
        counts.append(count)
    assert all(re.search(pattern, raw) is None for pattern in SECRET_PATTERNS)
    return raw, counts


def main():
    label, *selection = sys.argv[1:]
    assert selection and not (OUT / (label + '-summary.json')).exists()
    before = photo()
    xml_path = HERE / (label + '.private.xml')
    command = [sys.executable, '-X', 'utf8', '-B', 'tests/run_isolated.py', *selection,
        '-q', '--tb=short', '--junitxml=' + str(xml_path)]
    env = {**os.environ, 'PYTHON_DOTENV_DISABLED': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    for key in ('DATABASE_URL', 'MIGRATOR_DATABASE_URL', 'METODOBASE_TEST_DATABASE_URL',
                'METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL', 'METODOBASE_TEST_REDIS_URL'):
        env.pop(key, None)
    result = subprocess.run(command, cwd=ROOT, capture_output=True, env=env, timeout=360)
    raw = result.stdout + result.stderr
    (HERE / (label + '.private.log')).write_bytes(raw)
    xml = xml_path.read_bytes()
    cases = list(ET.fromstring(xml).iter('testcase'))
    after = photo()
    rows = [{'module': item.get('classname'), 'case': item.get('name'),
             'result': next((key for key in ('failure', 'error', 'skipped') if item.find(key) is not None), 'passed')}
            for item in cases]
    projection, counts = projected(raw)
    xml_projection, xml_counts = projected(xml)
    (OUT / (label + '-projected.log')).write_bytes(projection)
    (OUT / (label + '-projected.xml')).write_bytes(xml_projection)
    report = {'label': label, 'selection': selection, 'exit': result.returncode, 'cases': len(cases),
              'counts': {key: sum(row['result'] == key for row in rows) for key in ('passed', 'failure', 'error', 'skipped')},
              'rows': rows, 'source_quiet': before == after, 'source_files': len(before['source']), 'packages': len(before['packages']),
              'raw_log_private_sha256': sha(raw), 'raw_xml_private_sha256': sha(xml),
              'projected_log_sha256': sha(projection), 'projected_xml_sha256': sha(xml_projection),
              'redactions': {'log': counts, 'xml': xml_counts},
              'scope': 'Opt-in test fixture adoption. SQLite/HTTP real MFA and business routes; captured mail only. No PG/Chrome/provider.'}
    for suffix, value in [('before', before), ('after', after), ('summary', report)]:
        (OUT / (label + '-' + suffix + '.json')).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')
    assert before == after
    print(json.dumps({key: report[key] for key in ('label', 'exit', 'cases', 'counts', 'source_quiet', 'packages', 'redactions')}))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
