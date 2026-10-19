"""One owned PG restore30; private configuration stays in this child process."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path('F:/mb-history30-restore-20261019')
TEMP = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-history30-restore-author-ov6_28v2')
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/history30-restore-author-20261019'
RUN = TEMP / 'restore30-final'
RUN.mkdir(exist_ok=False)
(RUN / 'evidence').mkdir()
PRIVATE = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
configuration = json.loads(PRIVATE.read_text(encoding='utf-8-sig'))
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')
paths = subprocess.check_output(['git','--no-replace-objects','ls-files','-co','--exclude-standard','-z'], cwd=ROOT).decode().split('\0')[:-1]
paths = sorted(set(name for name in paths if not name.startswith(('docs/','dist/','build/')) and (ROOT/name).is_file()))
def photo():
    return {name:sha((ROOT/name).read_bytes()) for name in paths}
def packages():
    return sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())
before, packages_before = photo(), packages()
save('before-source.json',before)
save('before-packages.json',packages_before)
pip_before = subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-before.log').write_bytes(pip_before.stdout+pip_before.stderr)
assert pip_before.returncode == 0
quality = subprocess.run([sys.executable,'-m','ruff','check','--select','F,E9','tests/integration_personal_history_index_restore.py'],cwd=ROOT,capture_output=True)
(OUT/'quality.log').write_bytes(quality.stdout+quality.stderr)
assert quality.returncode == 0
environment = dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1')
for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','_METODOBASE_TEST_ROOT']:
    environment.pop(key,None)
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:
    environment[key] = configuration[key]
environment['METODOBASE_TEST_EVIDENCE_DIR'] = str(RUN/'evidence')
arguments = [sys.executable,'-X','utf8','-B','tests/run_isolated.py',
    'tests/integration_personal_history_index_restore.py::test_revision30_restore_preserves_history_index_and_all_revision26_27_28_29_contracts',
    '-q','--tb=short','--junitxml='+str(RUN/'tests.xml')]
started = time.monotonic()
with (RUN/'stdout.raw.log').open('xb') as stream, (RUN/'stderr.raw.log').open('xb') as errors:
    result = subprocess.run(arguments,cwd=ROOT,env=environment,stdout=stream,stderr=errors,timeout=300)
seconds = time.monotonic()-started
after, packages_after = photo(), packages()
save('after-source.json',after)
save('after-packages.json',packages_after)
pip_after = subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-after.log').write_bytes(pip_after.stdout+pip_after.stderr)
assert before == after and packages_before == packages_after and pip_after.returncode == 0
# Preserve RAW privately. Publish only filtered bytes with both hashes and an
# explicit redaction count; do not call a filtered copy byte-identical RAW.
secret_bytes = [str(configuration[key]).encode() for key in
                ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']]
from urllib.parse import urlsplit
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']:
    parsed = urlsplit(configuration[key])
    if parsed.password:
        secret_bytes.append(parsed.password.encode())
records = []
for source in sorted(RUN.rglob('*')):
    if not source.is_file():
        continue
    relative = source.relative_to(RUN).as_posix()
    raw = source.read_bytes()
    filtered, count = raw, 0
    for secret in sorted(set(secret_bytes),key=len,reverse=True):
        count += filtered.count(secret)
        filtered = filtered.replace(secret,b'[REDACTED_PRIVATE_CONNECTION]')
    filtered, matches = re.subn(rb'postgres(?:ql)?(?:\+psycopg2)?://[^\s\x22\x27<>]+',b'[REDACTED_POSTGRES_URL]',filtered)
    count += matches
    destination = OUT/'run'/relative
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(filtered)
    records.append({'path':relative,'raw_sha256':sha(raw),'published_sha256':sha(filtered),
                    'redactions':count,'published_exact_raw':raw==filtered})
save('output-classification.json',records)
created_path = RUN/'evidence/history-index30-author-owned-created.json'
closure = {'owned_names': [],'remaining':None,'independently_queried':False}
if created_path.is_file():
    names = json.loads(created_path.read_bytes())['names']
    assert len(names)==2 and re.fullmatch(r'metodobase_test_backup_[0-9a-f]{12}',names[0])
    assert names[1] == names[0].replace('metodobase_test_backup_','metodobase_test_restore_',1)
    import psycopg2
    with psycopg2.connect(configuration['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1),connect_timeout=5) as connection, connection.cursor() as cursor:
        cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)',(names,))
        remaining = [row[0] for row in cursor.fetchall()]
    closure = {'owned_names':names,'remaining':remaining,'independently_queried':True,
               'query_scope':'Exact two names recorded by the fixture, no enumeration or mutation of other resources'}
save('independent-owned-closure.json',closure)
cases = list(ET.parse(RUN/'tests.xml').iter('testcase')) if (RUN/'tests.xml').is_file() else []
summary = {
    'base':'ea66afbfe323cd5ac86e24705e2534b54c7bbe13','exit_code':result.returncode,
    'seconds':seconds,'cases':len(cases),
    'failures':sum(c.find('failure') is not None for c in cases),
    'errors':sum(c.find('error') is not None for c in cases),
    'skipped':sum(c.find('skipped') is not None for c in cases),
    'sources':len(paths),'packages':len(packages_before),
    'sources_and_packages_stable':before==after and packages_before==packages_after,
    'pip_checks_zero':pip_before.returncode==pip_after.returncode==0,
    'exact_two_owned_databases_absent':closure['independently_queried'] and closure['remaining']==[],
    'scope':'One synthetic PostgreSQL30 encrypted populated restore, all26-29 assertions plus physical history-index drift. No production recovery/RPO/RTO or latency claim.',
}
save('summary.json',summary)
print(json.dumps(summary))
assert result.returncode==0 and len(cases)==1 and not any(c.find(tag) is not None for c in cases for tag in ['failure','error','skipped'])
assert closure['independently_queried'] and closure['remaining']==[]
