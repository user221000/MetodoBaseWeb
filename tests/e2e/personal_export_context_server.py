"""Reuse the frozen diary fixture with only its two loopback port literals adapted.

Product imports, isolated metadata preparation, real registration and socket
guard remain in the original fixture. This is not a migration launcher.
"""
import hashlib
import json
from pathlib import Path


if __name__ == '__main__':
    fixture = Path(__file__).with_name('personal_diary_server.py')
    root = fixture.resolve().parents[2]
    frozen = json.loads((root / 'docs/implementation/20261018-evolution/evidence/ux/diary-ui-source.json').read_text(encoding='utf8'))
    digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
    if digest != frozen['sources']['tests/e2e/personal_diary_server.py']['sha256']:
        raise RuntimeError('The historical fixture body changed')
    source = fixture.read_text(encoding='utf8')
    if source.count('http://127.0.0.1:8776') != 1 or source.count('port=8776') != 1:
        raise RuntimeError('Unexpected fixture port locations')
    adapted = source.replace('http://127.0.0.1:8776', 'http://127.0.0.1:8777').replace('port=8776', 'port=8777')
    print(json.dumps({'fixture_composition':'consumer-context-followup','port':8777,
        'original_fixture_sha256':digest,'adaptation':'two loopback port literals only; metadata-only SQLite, no migration claim'}),flush=True)
    namespace = {'__file__':str(fixture.resolve()),'__name__':'diary_context_fixture'}
    exec(compile(adapted,str(fixture.resolve()),'exec'),namespace)
    namespace['main']()
