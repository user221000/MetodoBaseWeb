"""Bind successful final replay and retained initial orchestration error."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


final = json.loads((root / 'final/summary.json').read_text())
assert len(final['cases']) == 7 and all(case['matched_contract'] for case in final['cases'])
manifest = {path.relative_to(root).as_posix(): sha(path) for path in sorted(root.rglob('*')) if path.is_file()}
with (root / 'package-manifest.json').open('x', encoding='utf8') as stream:
    json.dump({'files': manifest, 'count': len(manifest),
               'decision': 'Accepted at3978b3; original two baseline bypasses closed and docstring criterion enforced.',
               'initial_error': 'Only QA path separator lookup failed before executing any CLI/canary; source and error preserved.',
               'scope': 'Includes successful final7 CLI replay, unchanged sources/packages photos and first harness artifacts; excludes self.'}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'package_files': len(manifest), 'package_manifest_sha256': sha(root / 'package-manifest.json')}))
