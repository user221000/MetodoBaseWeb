"""Bounded independent QA proof projection; no provider, SQL or network calls."""
import ast
from collections import Counter
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path('F:/mb-qa-product-analytics-r30-20261021')
PRIVATE = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-r30-independent-20261021')
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/qa-r30-independent-20261021'
AUTHOR = 'e6852cfd59d9df0f715f81e9299e7c4e5cb00d88'
FREEZE = '59b64e029e06e1cdff69f7f4702aa8d664b65f66'
PHASES = ('baseline-red', 'baseline-corrected', 'reader-http-before', 'http-sparse-corrected',
          'coherence-after', 'http-final', 'http-ipc-corrected', 'final-independent', 'exclusive-red', 'final-closed')
PRODUCT = ('web/product_analytics_domain.py', 'web/product_analytics_baseline.py',
           'web/services/product_analytics.py', 'web/routes/product_analytics.py',
           'web/middleware/security_headers.py', 'api/app.py', 'web/main_web.py')
TESTS = tuple('tests/test_qa_r30_' + suffix + '.py' for suffix in
              ('baseline_consistency', 'baseline_bounds', 'reader_boundaries', 'http_boundaries'))
sha = lambda raw: hashlib.sha256(raw).hexdigest()
git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)
json_bytes = lambda value: (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
assert git('rev-parse', 'HEAD').decode().strip() == FREEZE
assert not git('status', '--porcelain')
assert git('diff', '--name-only', AUTHOR, FREEZE, '--', 'api', 'web', 'core').decode().splitlines() == ['web/product_analytics_domain.py']

scanner_source = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint119-prepare.py').read_bytes()
node = next(item for item in ast.parse(scanner_source).body if isinstance(item, ast.FunctionDef) and item.name == 'scan')
namespace = {'re': re, 'io': io, 'tarfile': tarfile, 'zipfile': zipfile, 'PurePosixPath': PurePosixPath}
exec(compile(ast.Module(body=[node], type_ignores=[]), 'scanner119', 'exec'), namespace)


def scan(raw, name):
    namespace['scan'](raw, name)
    assert not re.search(rb'eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', raw), name
    assert not re.search(rb'[A-Za-z0-9_-]{30,}\.[0-9]{9,12}\.[a-f0-9]{64}', raw), name
    assert not re.search(rb'(?:postgres(?:ql)?|redis)://[^\s]+:[^\s]+@', raw), name


def save(name, value):
    raw = value if isinstance(value, bytes) else json_bytes(value)
    scan(raw, name)
    target = OUT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    assert target.read_bytes() == raw


def cases(path):
    result = []
    for row in ET.parse(path).findall('.//testcase'):
        result.append({'id': row.attrib['classname'] + '::' + row.attrib['name'],
            'status': 'failure' if row.find('failure') is not None else
                      'error' if row.find('error') is not None else
                      'skip' if row.find('skipped') is not None else 'pass'})
    return result


final_photo = json.loads((PRIVATE / 'final-closed/after.json').read_bytes())
all_cases = {}
for phase in PHASES:
    directory = PRIVATE / phase
    before = json.loads((directory / 'before.json').read_bytes())
    after = json.loads((directory / 'after.json').read_bytes())
    summary = json.loads((directory / 'result.json').read_bytes())
    assert before == after and summary['quiet'] is True
    assert before['records'] == final_photo['records'] and before['runtime_installed'] == final_photo['runtime_installed']
    assert len(before['records']) == 92 and len(before['runtime_installed']) == 8177
    all_cases[phase] = cases(directory / 'junit.xml')
assert Counter(row['status'] for row in all_cases['baseline-corrected']) == {'failure': 3, 'pass': 1}
assert Counter(row['status'] for row in all_cases['exclusive-red']) == {'failure': 1, 'pass': 2}
assert Counter(row['status'] for row in all_cases['final-closed']) == {'pass': 43}
assert len(set(row['id'] for row in all_cases['final-closed'])) == 43

for name in PRODUCT + TESTS:
    assert sha((ROOT / name).read_bytes()) == final_photo['source'][name], name

original = (PRIVATE / 'baseline-corrected/source/tests/test_qa_r30_baseline_consistency.py').read_bytes()
assert original == (ROOT / TESTS[0]).read_bytes()
pre = ast.parse((PRIVATE / 'extra_counterexample.py').read_bytes())
post = ast.parse((ROOT / TESTS[1]).read_bytes())
exclusive_asserts = {}
for before in (item for item in pre.body if isinstance(item, ast.FunctionDef) and item.name.startswith('test_')):
    after = next(item for item in post.body if isinstance(item, ast.FunctionDef) and item.name == before.name)
    first, last = (ast.dump(item, include_attributes=False) for item in (before, after))
    assert first == last, before.name
    exclusive_asserts[before.name] = sha(first.encode())

diff = git('diff', AUTHOR, FREEZE, '--', 'web/product_analytics_domain.py')
(PRIVATE / 'product.patch').write_bytes(diff)
check = subprocess.run(['git', 'apply', '--reverse', '--check', '-'], cwd=ROOT, input=diff, capture_output=True)
assert check.returncode == 0
(PRIVATE / 'reverse-check.stdout').write_bytes(check.stdout)
(PRIVATE / 'reverse-check.stderr').write_bytes(check.stderr)
lint = subprocess.run(['C:/Users/Consu/AppData/Local/Temp/metodobase-qa-20261018/Scripts/python.exe', '-B',
    '-m', 'ruff', 'check', '--no-cache', 'web/product_analytics_domain.py', *TESTS], cwd=ROOT, capture_output=True)
(PRIVATE / 'ruff.stdout').write_bytes(lint.stdout)
(PRIVATE / 'ruff.stderr').write_bytes(lint.stderr)
assert lint.returncode == 0

acl_initial = json.loads((PRIVATE / 'acl-initial.json').read_text(encoding='utf-8-sig'))
acl_final = json.loads((PRIVATE / 'acl-final.json').read_text(encoding='utf-8-sig'))
assert acl_initial['Protected'] is True and acl_initial['Payload'] == 'none before this record'
assert acl_final == {'AreAccessRulesProtected': True, 'Rules': 2}

# Seal only this owned evidence directory; never enumerate the environment.
files = {path.relative_to(PRIVATE).as_posix(): path.read_bytes() for path in sorted(PRIVATE.rglob('*'))
         if path.is_file()}
assert not any(Path(name).suffix == '.pyc' for name in files)
assert len(files) < 250 and all(len(raw) < 10_000_000 for raw in files.values())
inventory = {name: {'bytes': len(raw), 'sha256': sha(raw)} for name, raw in files.items()}
archive = PRIVATE / 'raw.tar'
with archive.open('xb') as stream:
    with tarfile.open(fileobj=stream, mode='w') as packed:
        for name, raw in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            info.mtime = 0
            info.mode = 0o600
            packed.addfile(info, io.BytesIO(raw))
with tarfile.open(archive, 'r') as packed:
    restored = {row.name: packed.extractfile(row).read() for row in packed.getmembers() if row.isfile()}
assert restored == files
receipt = {'scope': 'owned independent QA RAW only; archive excludes itself and this subsequent receipt',
    'members': len(files), 'archive_bytes': archive.stat().st_size, 'archive_sha256': sha(archive.read_bytes()),
    'inventory': inventory, 'readback_equal': True, 'protected_DACL_before_payload': True,
    'initial_acl_record_sha256': sha((PRIVATE / 'acl-initial.json').read_bytes()),
    'final_acl_record_sha256': sha((PRIVATE / 'acl-final.json').read_bytes())}
(PRIVATE / 'raw-receipt.json').write_bytes(json_bytes(receipt))

assert not OUT.exists()
OUT.mkdir(parents=True)
save('.gitattributes', b'* -text\n')
for phase in PHASES:
    directory = PRIVATE / phase
    summary = json.loads((directory / 'result.json').read_bytes())
    save('runs/' + phase + '.json', {**summary, 'cases': all_cases[phase],
        'counts': dict(Counter(row['status'] for row in all_cases[phase])),
        'RAW': {name: {'bytes': (directory / name).stat().st_size, 'sha256': sha((directory / name).read_bytes())}
                for name in ('before.json', 'after.json', 'stdout.log', 'stderr.log', 'junit.xml')},
        'per_run_drivers': {name: sha((directory / name).read_bytes()) for name in ('phase.py', 'offline.py')
                           if (directory / name).is_file()}})
save('source.json', {name: {'RAW_sha256': sha((ROOT / name).read_bytes()),
    'Git_sha256': sha(git('show', FREEZE + ':' + name))} for name in PRODUCT + TESTS})
save('final-cases.json', {'phase': 'final-closed', 'unique_ids': 43, 'counts': {'pass': 43},
    'composition': 'Single final run: 27 pure baseline, 8 SQLite reader, 8 authentic API/SaaS HTTP cases',
    'cases': all_cases['final-closed']})
save('failure-attribution.json', {
    'baseline-red': '4 setup errors: missing config in sparse QA; no product body ran',
    'baseline-corrected': '3 semantic helper counterexamples fail, 1 genuine report control passes; no API input or provenance claim',
    'reader-http-before': '8 SQLite passes plus 8 HTTP setup errors: sparse QA missing utils',
    'http-sparse-corrected': '8 HTTP setup errors: sparse QA missing src',
    'coherence-after': '56 pass: 24 new pure helper cases plus 32 existing domain regressions',
    'http-final': '8 HTTP setup errors before ASGI: absolute connect guard blocks Windows Proactor self-pipe',
    'http-ipc-corrected': '8 pass after exact internal socketpair allowance; application TCP and psycopg2 stay denied',
    'final-independent': '40 pass on first fix; earlier manual agent counts 41 and 25+31 were mistaken and explicitly corrected',
    'exclusive-red': '1 helper counterexample fails, 2 exact-boundary controls pass; private companion source retained; this companion outside WT was not part of the1191 source photo',
    'final-closed': '43 pass on final freeze after exclusive cutoff condition; no further product edits',
    'runner_provenance': 'Per-run phase/offline RAW copies start at http-ipc-corrected. Earlier phase.py versions were edited in place and are not claimed frozen per run; pre-driver-copy phase.py and original offline guard are retained.',
    'scope': 'Synthetic/private observed facts only. No API production defect, fabricated baseline, population cohort, importer, source attestation, or real-world business measurement is asserted.'})
save('proof-preservation.json', {'original_three_RED_and_control_RAW_unchanged': True,
    'exclusive_counterexample_and_two_positive_full_function_AST_equal': exclusive_asserts,
    'product_reverse_patch_check': check.returncode, 'ruff_focal': lint.returncode,
    'changed_product_paths': ['web/product_analytics_domain.py'], 'no_API_auth_or_MFA_delta': True,
    'private_RAW_archive': {key: value for key, value in receipt.items() if key != 'inventory'},
    'private_RAW_inventory_sha256': sha(json_bytes(inventory))})
save('product.patch', diff)
save('preimages/domain.before.raw.py', (PRIVATE / 'baseline-corrected/source/web/product_analytics_domain.py').read_bytes())
save('preimages/exclusive-counterexample.before.py', (PRIVATE / 'extra_counterexample.py').read_bytes())
save('preimages/offline-all-connects.py', (PRIVATE / 'preimages/offline-all-connects.py').read_bytes())
save('preimages/phase-pre-driver-photo.py', (PRIVATE / 'preimages/phase-pre-driver-photo.py').read_bytes())
for name in ('phase.py', 'offline.py', 'seal.py'):
    save('drivers/' + name, (PRIVATE / name).read_bytes())
save('freeze.json', {'author': AUTHOR, 'independent_code_tests': FREEZE,
    'commits': ['6ec07aba7fabe0c359723a8b368b945792d561fc', 'c60df3d6f23b0ec034a459fc13370dfef7ebef76',
                'a6a604c65607841e355e2efccd9c172ec4f9bce0', FREEZE],
    'author_original_113_claim': '113 distinct IDs composed by author phases; not rerun or represented as one113 run here',
    'own_final': {'pass': 43, 'fail': 0, 'error': 0, 'skip': 0},
    'before_after': {'source_files': 1191, 'RECORD_distributions': 92, 'runtime_installed_entries': 8177,
        'quiet': True, 'final_before_sha256': sha((PRIVATE / 'final-closed/before.json').read_bytes()),
        'final_after_sha256': sha((PRIVATE / 'final-closed/after.json').read_bytes())},
    'pending': ['ROOT replay/peer', 'real PostgreSQL snapshot/read-only/RLS/pool reuse after dedicated lease'],
    'not_executed': ['PostgreSQL', 'Chrome', 'VM', 'Redis', 'n2', 'installs', 'desktop', 'real providers', 'real data']})
payloads = {path.relative_to(OUT).as_posix(): path.read_bytes() for path in sorted(OUT.rglob('*')) if path.is_file()}
for name, raw in payloads.items():
    scan(raw, name)
save('scan.json', {'scanner119_function_sha256': sha(ast.dump(node, include_attributes=False).encode()),
    'scanner119_source_sha256': sha(scanner_source), 'recursive119_and_JWT_HMAC_URL_credential_scan': 'PASS',
    'payload_files_checked_before_scan_manifest': len(payloads), 'private_archive_published': False})
entries = {path.relative_to(OUT).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
           for path in sorted(OUT.rglob('*')) if path.is_file()}
save('manifest.json', {'files': entries})
for name, meta in entries.items():
    assert sha((OUT / name).read_bytes()) == meta['sha256'] and (OUT / name).stat().st_size == meta['bytes']
print(json.dumps({'code_test_freeze': FREEZE, 'final_pass': 43, 'public_payloads': len(entries),
    'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()), 'private_RAW_members': len(files),
    'private_RAW_archive_sha256': receipt['archive_sha256']}))
