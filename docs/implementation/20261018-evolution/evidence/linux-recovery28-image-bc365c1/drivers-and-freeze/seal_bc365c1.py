from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
ROOT = Path(r'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence')
DEST = ROOT / 'linux-recovery28-image-bc365c1'
PRIOR = ROOT / 'linux-recovery28-image-abd559a'
PIN = 'fc0053a28039d61c8b7a82b99fd6f13b4a9ed595d9d8cd4711d96c1223aa6705'

def info(p):
    with p.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': p.stat().st_size, 'sha256': digest}

def safe(p):
    assert p.resolve().is_relative_to(ROOT.resolve())
    for a in (p, *p.parents):
        if a.exists():
            assert not a.is_symlink() and not (getattr(a.lstat(), 'st_file_attributes', 0) & 0x400)

prior_manifest_path = PRIOR / 'evidence-manifest.json'
assert info(prior_manifest_path)['sha256'] == PIN
prior_manifest = json.loads(prior_manifest_path.read_text(encoding='utf-8'))
assert len(prior_manifest['files']) == 197
for rel, expected in prior_manifest['files'].items():
    p = PRIOR / rel
    safe(p)
    assert info(p) == expected, rel
carry = json.loads((DEST / 'os-audit/triage-carry-forward.json').read_text(encoding='utf-8'))
matrix_record = prior_manifest['files']['os-audit/triage-matrix/matrix-73.json']
assert carry['prior_matrix_sha256'] == matrix_record['sha256']
prior_check = {'verified_utc': datetime.now(timezone.utc).isoformat(),
               'prior_manifest_sha256': PIN, 'prior_file_count': 197,
               'all_prior_manifest_members_byte_exact': True,
               'carry_forward_matrix_hash_matches_pinned_prior_manifest': True,
               'scope': 'Read-only verification of preserved baseline evidence. No prior file was rewritten.'}
with (DEST / 'prior-evidence-continuity.json').open('x', encoding='utf-8') as stream:
    json.dump(prior_check, stream, indent=2)
    stream.write('\n')

readme_path = DEST / 'README.md'
prose = readme_path.read_text(encoding='utf-8', errors='strict')
assert 'se construy\u00f3 correctamente' in prose
assert 'auditor\u00eda OS sigue roja' in prose
assert '\ufffd' not in prose and '\u00c3' not in prose and '\u00c2' not in prose
assert '?' not in prose
links = []
for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', prose):
    if target.startswith('https://'):
        continue
    p = readme_path.parent / target.split('#', 1)[0]
    safe(p)
    assert p.is_file(), target
    links.append(target)

self_dest = DEST / 'drivers-and-freeze' / Path(__file__).name
with self_dest.open('xb') as stream:
    stream.write(Path(__file__).read_bytes())
files = {}
for p in sorted(DEST.rglob('*')):
    safe(p)
    if p.is_file():
        rel = p.relative_to(DEST).as_posix()
        assert rel not in ('evidence-manifest.json', 'evidence-manifest.sha256')
        files[rel] = info(p)
manifest = {'created_utc': datetime.now(timezone.utc).isoformat(),
            'audited_commit': 'bc365c13b9af9e24129a56b4068059a67bb3afa0',
            'main_source_base': 'a753b2cdf61a91133bd58c3159b0b35e02167396',
            'image_id': 'sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c',
            'prior_manifest_sha256': PIN,
            'file_count': len(files), 'readme_sha256': files['README.md']['sha256'],
            'scope': 'Exact corrected MAIN-based image: build pass, 55-distribution Python SCA zero; OS remains open at 164 entries/71 IDs after two XZ aliases removed. No app runtime acceptance.',
            'files': files}
manifest_path = DEST / 'evidence-manifest.json'
with manifest_path.open('x', encoding='utf-8') as stream:
    json.dump(manifest, stream, indent=2)
    stream.write('\n')
manifest_sha = info(manifest_path)['sha256']
with (DEST / 'evidence-manifest.sha256').open('x', encoding='ascii') as stream:
    stream.write(manifest_sha + '  evidence-manifest.json\n')
for rel, expected in files.items():
    assert info(DEST / rel) == expected, rel
summary = {'manifest_path': str(manifest_path), 'manifest_sha256': manifest_sha,
           'readme_path': str(readme_path), 'readme_sha256': files['README.md']['sha256'],
           'file_count': len(files), 'all_manifest_members_rehashed': True,
           'readme_utf8_and_local_links_verified': True, 'local_link_count': len(links),
           'prior_197_files_rehashed_and_preserved': True}
with (LAB / 'evidence/closure-bc365c1/sealed-evidence.json').open('x', encoding='utf-8') as stream:
    json.dump(summary, stream, indent=2)
    stream.write('\n')
print(json.dumps(summary, indent=2))
