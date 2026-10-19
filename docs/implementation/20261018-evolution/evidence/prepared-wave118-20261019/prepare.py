"""Preserve UI composition and replay evidence without changing original freezes."""
from pathlib import Path
import hashlib
import io
import json
import re
import zipfile

ROOT = Path(r'F:\MetodoBaseWeb-execution-20261018')
UI = Path(r'F:\mb-mfa-ui31-20261019')
TMP = Path(r'C:\Users\Consu\AppData\Local\Temp')
DEST = ROOT / 'docs/implementation/20261018-evolution/evidence/prepared-wave118-20261019'
SHA = lambda b: hashlib.sha256(b).hexdigest()


def sensitive(blob):
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])', blob):
        start = match.start()
        if start >= 30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}', blob[start-30:start]):
            return True
    return bool(re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+', blob))


check = TMP / 'metodobase-mfa-ui31-copy-check-20261019'
summary = json.loads((check / 'summary.json').read_bytes())
assert summary['head'] == 'da34304aaf9066f45c6fc854cfd81d00e2fbc581'
assert summary['sources_packages_node_quiet'] and summary['HTTP_SSR_cases'] == 14
assert summary['HTTP_SSR_counts'] == {'failure': 0, 'error': 0, 'skipped': 0}
assert all(row['exit'] == 0 for row in summary['results'])
assert sum(row['passed'] for row in summary['VM'].values()) == 74
DEST.mkdir(exist_ok=False)
(DEST / '.gitattributes').write_bytes(b'* -text\n')


def capture(path, name, digest=None):
    blob = path.read_bytes()
    assert not sensitive(blob), path.name
    if digest:
        assert SHA(blob) == digest
    target = DEST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)


capture(Path(__file__), 'prepare.py')
capture(UI / 'docs/implementation/20261018-evolution/evidence/mfa-ui/vm-source.json', 'ui-author-vm-source.json',
        'da18364f292abc51e9c7cca44db90c0be1c9d86027eadb10b16b22fea857cc7f')
capture(UI / 'docs/implementation/20261018-evolution/evidence/mfa-ui31/source.json', 'ui-author-final-source.json',
        '789a5f590c33bb45bb92c13175f9e1f2c5823557f737ad0f3a588b9849e46621')
capture(UI / 'docs/implementation/20261018-evolution/evidence/mfa-ui31/AUTHOR_REPORT.md', 'ui-author-report.md')
for folder, prefix in [('metodobase-mfa-ui31-compose-preflight-20261019', 'UI-preflight'),
                       ('metodobase-mfa-ui31-compose-20261019', 'UI-composition'),
                       ('metodobase-mfa-ui31-copy-20261019', 'UI-copy-first'),
                       ('metodobase-mfa-ui31-copy-v2-20261019', 'UI-copy-v2'),
                       ('metodobase-mfa-ui31-copy-check-20261019', 'UI-copy-check')]:
    for path in sorted((TMP / folder).rglob('*')):
        if path.is_file():
            capture(path, prefix + '/' + path.relative_to(TMP / folder).as_posix())
capture(TMP / 'metodobase-mfa-ui31-copy-v2-prepare.py', 'UI-copy-prepare.py')
receipt = {'candidate_head': summary['head'], 'composition': '913 backend +087 frozen UI ->5e91115 automatic tree, no conflicts;24product/test paths exact incoming and5backend files exact before.',
           'copy': 'da343 changes20literal presentation strings in3UI files; inverse raw bytes exact and node--check passed. Initial CRLF precondition failure stopped before any source edit; original driver and cause retained.',
           'root_replay': '74existing MFA VM +14existing SSR/HTTP cases passed,679source/test files and89packages plus Node binary unchanged. No independent or browser acceptance from this replay.',
           'author_scope': 'Author original74VM, maintained74transport/24emitter-expiry,10SSR,4ASGIbridges and15Chrome groups/12screens remain on their documented freezes. Masked kit screenshot reviewed visually. Google/PG/independent UI remain outside author browser scope.',
           'main_product_changed': False, 'original_proofs_modified': False}
(DEST / 'receipt.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
manifest = {'files': {p.relative_to(DEST).as_posix(): {'bytes': p.stat().st_size, 'sha256': SHA(p.read_bytes())}
                      for p in sorted(DEST.rglob('*')) if p.is_file()}}
(DEST / 'manifest.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode())
print(json.dumps({'files': len(manifest['files']) + 1, 'manifest_sha256': SHA((DEST / 'manifest.json').read_bytes()),
                  'candidate_head': summary['head'], 'main_product_changed': False}))
