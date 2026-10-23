"""Root-attested current57 capsule bootstrap; no Git, SSH or second builder."""
import argparse
import hashlib
import importlib
import io
import json
import os
import re
import stat
import sys
import tarfile
from pathlib import Path, PurePosixPath

CODE_PATHS = (
    'tests/__init__.py', 'tests/ci_image57/__init__.py',
    'tests/ci_image57/run.py', 'tests/ci_image57/authority.py',
    'tests/ci_image57/authority_pins.py', 'tests/ci_image57/context.py',
    'tests/ci_image57/source_proof.py', 'tests/ci_image57/probe.py',
    'tests/ci_image57/bridge.py', 'tests/ci_image57/bridge_guest.py',
    'tests/ci_image57/fixtures/image_context.py.RAW',
    'tests/ci_image57/fixtures/raw_git.py.RAW',
    'tests/ci_image57/fixtures/evidence.py.RAW',
    'tests/ci_image57/fixtures/private_producer.py.RAW',
    'tests/ci_image57/fixtures/publication.py.RAW',
    'tests/ci_image57/fixtures/container_inputs.py.RAW',
    'tests/ci_image57/fixtures/container-inputs.json.RAW',
    'tests/ci_image57/fixtures/runtime_probe57-69d49.py.RAW',
)
CONTEXT_NAMES = ('source-context.tar', 'source-manifest.json',
                 'source-objects.zip', 'runtime-input-contract.json')
MANIFEST_NAME = 'bridge-manifest.json'
MAX_BUNDLE = 100 * 1024**2
MAX_MANIFEST = 2 * 1024**2
MAX_PUBLIC = 4 * 1024**2


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def json_object(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate bridge JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def validate_manifest(raw, source):
    if len(raw) > MAX_MANIFEST or re.fullmatch('[0-9a-f]{40}', source) is None:
        raise ValueError('Bounded manifest and FULL40 required')
    value = json_object(raw)
    if (type(value) is not dict or set(value) != {'schema', 'source', 'code', 'context'}
            or value['schema'] != 'current57-root-attested-bridge-v1' or value['source'] != source
            or type(value['code']) is not dict or set(value['code']) != set(CODE_PATHS)
            or type(value['context']) is not dict or set(value['context']) != set(CONTEXT_NAMES)):
        raise ValueError('Exact bridge manifest differs')
    for row in value['code'].values():
        if (type(row) is not dict or set(row) != {'bytes', 'sha256', 'mode', 'git_blob'}
                or type(row['bytes']) is not int or not 0 <= row['bytes'] <= MAX_MANIFEST
                or row['mode'] not in {'100644', '100755'}
                or type(row['sha256']) is not str or re.fullmatch('[0-9a-f]{64}', row['sha256']) is None
                or type(row['git_blob']) is not str or re.fullmatch('[0-9a-f]{40}', row['git_blob']) is None):
            raise ValueError('Exact code row differs')
    for row in value['context'].values():
        if (type(row) is not dict or set(row) != {'bytes', 'sha256'}
                or type(row['bytes']) is not int or not 0 <= row['bytes'] <= 64 * 1024**2
                or type(row['sha256']) is not str or re.fullmatch('[0-9a-f]{64}', row['sha256']) is None):
            raise ValueError('Exact context row differs')
    return value


def validate_archive(raw, bundle_sha, manifest_sha, source, bootstrap_sha):
    if len(raw) > MAX_BUNDLE or sha(raw) != bundle_sha:
        raise ValueError('Root bundle identity differs')
    payloads = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        members = archive.getmembers()
        expected = set(CODE_PATHS) | set(CONTEXT_NAMES) | {MANIFEST_NAME}
        if len(members) != 23 or {m.name for m in members} != expected:
            raise ValueError('Exact 23-member capsule required')
        for member in members:
            if (member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE} or member.issparse() or member.name in payloads or member.pax_headers
                    or member.size < 0 or member.size > MAX_BUNDLE):
                raise ValueError('Regular unique capsule members required')
            with archive.extractfile(member) as reader:
                payloads[member.name] = reader.read(member.size + 1)
            if len(payloads[member.name]) != member.size:
                raise ValueError('Capsule member length differs')
        manifest_raw = payloads[MANIFEST_NAME]
        if sha(manifest_raw) != manifest_sha:
            raise ValueError('Root manifest identity differs')
        manifest = validate_manifest(manifest_raw, source)
        if manifest['code']['tests/ci_image57/bridge_guest.py']['sha256'] != bootstrap_sha:
            raise ValueError('Executing bootstrap binding differs')
        for member in members:
            if member.name == MANIFEST_NAME:
                expected_mode = 0o600
            else:
                code = member.name in manifest['code']
                row = (manifest['code'] if code else manifest['context'])[member.name]
                body = payloads[member.name]
                if len(body) != row['bytes'] or sha(body) != row['sha256']:
                    raise ValueError('Capsule bytes differ from Root manifest')
                if code:
                    blob = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body,
                                        usedforsecurity=False).hexdigest()
                    if blob != row['git_blob']:
                        raise ValueError('Declared code blob differs')
                expected_mode = int(row['mode'], 8) & 0o777 if code else 0o600
            if member.mode != expected_mode:
                raise ValueError('Capsule mode differs')
    contract = json_object(payloads['runtime-input-contract.json'])
    if type(contract) is not dict or contract.get('source') != source:
        raise ValueError('Closed context source differs')
    return manifest, payloads


def guest_path(text):
    path = PurePosixPath(text)
    if (text != path.as_posix() or len(path.parts) != 4 or path.parts[:3] != ('/', 'home', 'lab')
            or re.fullmatch('metodobase-ci57-[0-9a-f]{32}', path.name) is None):
        raise ValueError('Fresh owned guest directory required')
    return Path(text)


def fresh_guest_root(text):
    path = guest_path(text)
    if os.name != 'posix' or os.getuid() == 0:
        raise ValueError('Non-root Linux execution required')
    for parent in reversed(path.parents):
        value = parent.lstat()
        if not stat.S_ISDIR(value.st_mode) or stat.S_ISLNK(value.st_mode):
            raise ValueError('Guest ancestor differs')
    os.mkdir(path, 0o700)
    value = path.lstat()
    if stat.S_IMODE(value.st_mode) != 0o700 or value.st_uid != os.getuid():
        raise ValueError('Guest private boundary differs')
    return path


def write_new(path, raw, mode=0o600):
    with path.open('xb') as writer:
        writer.write(raw)
        writer.flush()
        os.fsync(writer.fileno())
    path.chmod(mode)
    if path.read_bytes() != raw:
        raise ValueError('Guest write readback differs')


def extract_verified(root, manifest, payloads):
    for name, body in sorted(payloads.items()):
        target = root / name
        missing = []
        parent = target.parent
        while parent != root and not parent.exists():
            missing.append(parent)
            parent = parent.parent
        for parent in reversed(missing):
            parent.mkdir(mode=0o700)
        row = manifest['code'].get(name)
        write_new(target, body, int(row['mode'], 8) & 0o777 if row else 0o600)


def verify_inputs(root, payloads):
    for name, raw in payloads.items():
        target = root / name
        value = target.lstat()
        if not stat.S_ISREG(value.st_mode) or stat.S_ISLNK(value.st_mode) or target.read_bytes() != raw:
            raise ValueError('Closed bridge inputs changed')


def invoke_api(root, manifest, docker, tag):
    if 'tests' in sys.modules:
        raise ValueError('Fresh isolated interpreter required')
    sys.path.insert(0, str(root))
    context = importlib.import_module('tests.ci_image57.context')
    run = importlib.import_module('tests.ci_image57.run')
    contract = json_object((root / 'runtime-input-contract.json').read_bytes())
    if contract.get('source') != manifest['source']:
        raise ValueError('Context FULL40 differs')
    context.validate_contract(root, contract)
    return run.build_probe(root, contract, docker, tag)


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    for name in ('source', 'bundle-sha256', 'manifest-sha256', 'bootstrap-sha256', 'guest-root', 'docker'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--tag')
    parser.add_argument('--authorized-single-build-probe', action='store_true', required=True)
    args = parser.parse_args(argv)
    root = None
    try:
        if not PurePosixPath(args.docker).is_absolute():
            raise ValueError('Explicit absolute Docker required')
        raw = sys.stdin.buffer.read(MAX_BUNDLE + 1)
        manifest, payloads = validate_archive(raw, args.bundle_sha256, args.manifest_sha256,
                                              args.source, args.bootstrap_sha256)
        root = fresh_guest_root(args.guest_root)
        extract_verified(root, manifest, payloads)
        result = invoke_api(root, manifest, args.docker, args.tag)
        verify_inputs(root, payloads)
        complete = {'schema': 'current57-bridge-result-v1', 'source': args.source, 'accepted': True,
                    'bundle_sha256': args.bundle_sha256, 'manifest_sha256': args.manifest_sha256,
                    'build_probe': result}
        output = json.dumps(complete, sort_keys=True).encode() + b'\n'
        if len(output) > MAX_PUBLIC:
            raise ValueError('Bridge result publication exceeds bound')
        write_new(root / 'bridge-result.private.json', output)
        sys.stdout.buffer.write(output)
        return 0
    except Exception as error:  # noqa: BLE001 - retain failure privately; publish no diagnostic payload
        if root is not None:
            write_new(root / 'bridge-failure.private.json',
                      json.dumps({'accepted': False, 'error_class': type(error).__name__,
                                  'automatic_retry_or_cleanup': False}).encode() + b'\n')
        print('{"accepted":false,"manual_review_required":true}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
