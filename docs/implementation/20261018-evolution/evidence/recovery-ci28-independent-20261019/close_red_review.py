"""Freeze additive red-baseline proof without overwriting the green evidence."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(r'F:\MetodoBaseWeb-recovery-ci-20261019')
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    with (OUT / name).open('x', encoding='utf8') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


before = json.loads((OUT / 'before.json').read_text())
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == before['head']
assert all(sha(ROOT / path) == value for path, value in before['sources'].items())
packages = sorted([dist.metadata['Name'], dist.version] for dist in importlib.metadata.distributions())
assert packages == before['packages']
scratch = Path(json.loads((OUT / 'owned-scratch.json').read_text())['path'])
with zipfile.ZipFile(OUT / 'baseline-trust-raw.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(scratch.rglob('*')):
        if path.is_file() and (path.is_relative_to(scratch / 'baseline-trust-shadow') or
                              any(part.startswith('baseline-trust-') for part in path.relative_to(scratch).parts)):
            archive.write(path, path.relative_to(scratch).as_posix())
save('red-review-closure.json', {
    'head': before['head'], 'sources': len(before['sources']), 'sources_still_quiet_after_red_probe': True,
    'packages': len(packages), 'packages_stable_after_red_probe': True,
    'decision': 'Do not integrate CI28 verifier until both baseline-tamper negatives reject.',
    'passed': 'Author18 JUnit+8delta+2inert/63Bash; independent55 JUnit+7delta+5inert, owned PIDs closed after wait.',
    'open': ['Tampered fixture snapshot pair accepted despite declared historical fixture digest mismatch.',
             'Tampered historical verifier accepted when unpinned baseline.json changes its expected hash.'],
    'original_baselines_authentic_by_independent_git_comparison': True,
    'before_sha256': sha(OUT / 'before.json'),
    'green_summary_sha256': sha(OUT / 'summary.json'),
    'red_reproduction_sha256': sha(OUT / 'baseline-trust-red.json'),
    'raw_shadow_sha256': sha(OUT / 'baseline-trust-raw.zip'),
    'author_and_coordinator_notified': True,
    'next_scope': 'Pin baseline.json and verify historical fixture hash before AST; replay only the two negative probes plus inert/author verifier justified by that delta.',
    'no_product_ci_author_edits_or_commits': True,
})
files = {path.relative_to(OUT).as_posix(): sha(path) for path in sorted(OUT.rglob('*')) if path.is_file()}
save('red-review-manifest.json', {'files': files, 'count': len(files), 'scope': 'Additive closure including original green manifest; excludes this manifest itself.'})
print(json.dumps({'sources': len(before['sources']), 'packages': len(packages),
                  'closure_sha256': sha(OUT / 'red-review-closure.json'),
                  'manifest_sha256': sha(OUT / 'red-review-manifest.json'), 'files': len(files)}))
