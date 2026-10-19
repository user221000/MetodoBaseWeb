"""Reproduce mutable-baseline verifier trust gaps only in a synthetic Temp shadow."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(r'F:\MetodoBaseWeb-recovery-ci-20261019')
OUT = Path(__file__).resolve().parent
SNAP = Path('docs/implementation/20261018-evolution/evidence/backend-recovery-ci28')


def sha(path, normalized=False):
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b'\r\n', b'\n') if normalized else data).hexdigest()


def main():
    frozen = json.loads((OUT / 'before.json').read_text())
    assert all(sha(ROOT / path) == expected for path, expected in frozen['sources'].items())
    scratch = Path(json.loads((OUT / 'owned-scratch.json').read_text())['path'])
    shadow = scratch / 'baseline-trust-shadow'
    shadow.mkdir(exist_ok=False)
    metadata = json.loads((ROOT / SNAP / 'baseline.json').read_text())
    paths = ['tests/verify_recovery_ci.py', '.github/workflows/ci.yml', 'tests/e2e/personal_diary_server.py',
             str(SNAP / 'ci27-baseline.yml'), str(SNAP / 'diary27-fixture-before.py'),
             str(SNAP / 'baseline.json'), *metadata['unchanged_files']]
    for path in paths:
        target = shadow / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    results = []

    def invoke(label):
        environment = dict(os.environ, PYTHONPATH=str(ROOT))
        result = subprocess.run([sys.executable, '-X', 'utf8', str(shadow / 'tests/verify_recovery_ci.py'),
                                 '--output', str(scratch / ('baseline-trust-' + label)), '--verify-only'],
                                cwd=shadow, env=environment, capture_output=True, text=True,
                                encoding='utf8', timeout=30)
        (OUT / ('baseline-trust-' + label + '.log')).write_text(result.stdout + result.stderr, encoding='utf8')
        return result

    positive = invoke('untouched-shadow')
    assert positive.returncode == 0, positive.stderr
    results.append({'case': 'untouched-shadow', 'exit': positive.returncode, 'expected': 'pass'})

    # Neither author files nor actual historical files are touched. Both input copies receive the same unauthorized AST.
    for path in [shadow / 'tests/e2e/personal_diary_server.py', shadow / SNAP / 'diary27-fixture-before.py']:
        with path.open('a', encoding='utf8') as stream:
            stream.write('\nCI28_UNAUTHORIZED_BASELINE_SENTINEL = True\n')
    tampered_hash = sha(shadow / SNAP / 'diary27-fixture-before.py', normalized=True)
    assert tampered_hash != metadata['diary_fixture27_sha256']
    fixture = invoke('fixture-baseline-pair-tampered')
    assert fixture.returncode == 0, fixture.stderr
    results.append({'case': 'fixture-and-baseline-same-unauthorized-statement',
                    'exit': fixture.returncode, 'expected': 'reject', 'unexpectedly_accepted': True,
                    'declared_historical_fixture_sha256': metadata['diary_fixture27_sha256'],
                    'actual_tampered_snapshot_sha256': tampered_hash,
                    'observation': 'Full CLI accepts an unauthorized fixture AST when the unpinned historical fixture copy is changed with it.'})

    shutil.copyfile(ROOT / 'tests/e2e/personal_diary_server.py', shadow / 'tests/e2e/personal_diary_server.py')
    shutil.copyfile(ROOT / SNAP / 'diary27-fixture-before.py', shadow / SNAP / 'diary27-fixture-before.py')
    immutable_path = 'tests/verify_diary_ci.py'
    with (shadow / immutable_path).open('a', encoding='utf8') as stream:
        stream.write('\nCI28_UNAUTHORIZED_HISTORICAL_SENTINEL = True\n')
    metadata['unchanged_files'][immutable_path] = sha(shadow / immutable_path, normalized=True)
    (shadow / SNAP / 'baseline.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf8')
    historical = invoke('historical-file-and-metadata-tampered')
    assert historical.returncode == 0, historical.stderr
    results.append({'case': 'historical-file-and-unpinned-metadata-updated',
                    'exit': historical.returncode, 'expected': 'reject', 'unexpectedly_accepted': True,
                    'observation': 'Full CLI accepts a changed historical verifier if its expected hash is also changed in unpinned baseline.json.'})
    assert all(sha(ROOT / path) == expected for path, expected in frozen['sources'].items())
    proof = {'head': frozen['head'], 'cases': results,
             'current_author_baselines_authentic_by_independent_git_review': True,
             'actual_author_sources_and_historical_fixtures_unchanged': True,
             'reproduction': 'Byte-exact copied verifier plus minimal input shadow in exclusively owned Temp; actual models only imported for pure marker evaluation; no server, schema, browser, or PG.',
             'recommendation': 'Pin baseline.json to an accepted digest in verifier code, then enforce its historical fixture digest before AST comparison; preserve existing immutable verifier/parser.'}
    with (OUT / 'baseline-trust-red.json').open('x', encoding='utf8') as stream:
        json.dump(proof, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'positive_shadow': 1, 'unexpected_baseline_tamper_acceptances': 2,
                      'proof_sha256': sha(OUT / 'baseline-trust-red.json')}))


if __name__ == '__main__':
    main()
