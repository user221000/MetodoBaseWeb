"""Prepare Root-attested code bytes, then transport one closed current57 build."""
import argparse
import hashlib
import io
import json
import os
import re
import shlex
import subprocess
import tarfile
import types
from pathlib import Path, PurePosixPath

from . import authority, context
from .bridge_guest import (
    CODE_PATHS,
    CONTEXT_NAMES,
    MANIFEST_NAME,
    MAX_BUNDLE,
    MAX_PUBLIC,
    guest_path,
    json_object,
    sha,
    validate_archive,
    validate_manifest,
)

LAB = Path('F:/MetodoBaseWeb-linux-lab-20261019')
GUEST_ACCESS_SHA = '616b66b791140966dac837fbd58808291b165d4ae06011a1395279462f43b7a7'


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n'


def write_new(path, raw):
    with path.open('xb') as writer:
        writer.write(raw)
        writer.flush()
        os.fsync(writer.fileno())
    if path.read_bytes() != raw:
        raise ValueError('Bridge private write readback differs')


def read_pinned(path, expected, bound):
    path = authority.regular_file(Path(path))
    if path.stat().st_size > bound:
        raise ValueError('Bridge input exceeds bound')
    raw = path.read_bytes()
    if len(raw) > bound or sha(raw) != expected:
        raise ValueError('Root bridge input identity differs')
    return raw


def prepare(repository, source, context_private, private):
    """Future explicit host Git phase; guest verification is Root-attested."""
    repository = authority.regular_directory(Path(repository))
    context_private = authority.regular_directory(Path(context_private))
    contract = json_object(authority.regular_file(context_private / 'runtime-input-contract.json').read_bytes())
    if contract.get('source') != source:
        raise ValueError('Context FULL40 differs')
    context.validate_contract(context_private, contract)
    payloads = {name: authority.regular_file(context_private / name).read_bytes() for name in CONTEXT_NAMES}
    code = {}
    with context.git_policy():
        context.check_source(repository, source)
        listing = context.git(repository, 'ls-tree', '-z', source, '--', *CODE_PATHS)
        rows = listing.rstrip(b'\0').split(b'\0')
        for row in rows:
            head, separator, path = row.partition(b'\t')
            pieces = head.decode('ascii').split(' ')
            name = path.decode('utf8')
            if (not separator or len(pieces) != 3 or pieces[0] not in {'100644', '100755'}
                    or pieces[1] != 'blob' or re.fullmatch('[0-9a-f]{40}', pieces[2]) is None
                    or name not in CODE_PATHS or name in code):
                raise ValueError('Exact final-commit bridge code inventory differs')
            raw = context.source(repository, source, name)
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw,
                                usedforsecurity=False).hexdigest()
            if blob != pieces[2]:
                raise ValueError('Extracted code blob differs')
            payloads[name] = raw
            code[name] = {'bytes': len(raw), 'sha256': sha(raw), 'mode': pieces[0], 'git_blob': blob}
    manifest = {'schema': 'current57-root-attested-bridge-v1', 'source': source, 'code': code,
                'context': {name: {'bytes': len(payloads[name]), 'sha256': sha(payloads[name])}
                            for name in CONTEXT_NAMES}}
    manifest_raw = encoded(manifest)
    validate_manifest(manifest_raw, source)
    payloads[MANIFEST_NAME] = manifest_raw
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:', format=tarfile.USTAR_FORMAT) as archive:
        for name, body in sorted(payloads.items()):
            member = tarfile.TarInfo(name)
            member.size = len(body)
            member.mode = int(code[name]['mode'], 8) & 0o777 if name in code else 0o600
            archive.addfile(member, io.BytesIO(body))
    bundle = stream.getvalue()
    bootstrap = payloads['tests/ci_image57/bridge_guest.py']
    validate_archive(bundle, sha(bundle), sha(manifest_raw), source, sha(bootstrap))
    for name in CONTEXT_NAMES:
        if authority.regular_file(context_private / name).read_bytes() != payloads[name]:
            raise ValueError('Closed context changed during bridge preparation')
    private = Path(private)
    authority.private_directory(private, repository)
    write_new(private / 'bridge-transfer.tar', bundle)
    write_new(private / MANIFEST_NAME, manifest_raw)
    write_new(private / 'bridge_guest.py', bootstrap)
    receipt = {'schema': 'current57-bridge-preparation-v1', 'source': source,
               'bundle_sha256': sha(bundle), 'manifest_sha256': sha(manifest_raw),
               'bootstrap_sha256': sha(bootstrap), 'members': 23,
               'Root_attestation_required': True, 'guest_Git_required': False,
               'build_executed': False, 'SBOM_SCA_complete': False}
    write_new(private / 'preparation.private.json', encoded(receipt))
    return receipt


def remote_command(guest_python, bootstrap, source, bundle_sha, manifest_sha,
                   bootstrap_sha, guest_root, docker, tag=None):
    guest_path(guest_root)
    for executable in (guest_python, docker):
        path = PurePosixPath(executable)
        if (not path.is_absolute() or str(path) != executable or '..' in path.parts
                or any(ord(c) < 32 or ord(c) == 127 for c in executable)):
            raise ValueError('Explicit canonical Linux executables required')
    command = [guest_python, '-I', '-B', '-X', 'utf8', '-c', bootstrap.decode('utf8'),
               '--source', source, '--bundle-sha256', bundle_sha,
               '--manifest-sha256', manifest_sha, '--bootstrap-sha256', bootstrap_sha,
               '--guest-root', guest_root, '--docker', docker, '--authorized-single-build-probe']
    if tag is not None:
        command += ['--tag', tag]
    return shlex.join(command)


def load_guest_access():
    path = LAB / 'scripts/guest_access.py'
    raw = read_pinned(path, GUEST_ACCESS_SHA, 64 * 1024)
    module = types.ModuleType('current57_existing_guest_access')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)  # noqa: S102 - pinned existing helper bytes
    return module


def transport(command, environment, bundle_path, private, timeout):
    """Wait only; a timeout retains the uncertain child, with no cleanup."""
    if type(timeout) not in {float, int} or type(timeout) is bool or not 0 < timeout <= 3600:
        raise ValueError('Explicit bounded SSH wait required')
    child = None
    with bundle_path.open('rb') as source, (private / 'ssh-stdout.private.log').open('xb') as out, \
            (private / 'ssh-stderr.private.log').open('xb') as errors:
        try:
            child = subprocess.Popen(command, stdin=source, stdout=out, stderr=errors,
                                     cwd=LAB / 'instance', env=environment,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            write_new(private / 'ssh-child.private.json', encoded({'pid': child.pid, 'argv': command,
                      'automatic_retry_or_cleanup': False, 'uncertain_child_requires_manual_review': True}))
            try:
                status = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                return {'closed': False, 'pid': child.pid, 'manual_review_required': True}
        finally:
            out.flush()
            os.fsync(out.fileno())
            errors.flush()
            os.fsync(errors.fileno())
    # Child is known closed and every parent log FD is closed before path reads.
    logs = {}
    for name in ('ssh-stdout.private.log', 'ssh-stderr.private.log'):
        path = private / name
        with path.open('rb') as reader:
            size = path.stat().st_size
            head = reader.read(MAX_PUBLIC + 1)
        logs[name] = {'bytes': size, 'bounded': len(head) <= MAX_PUBLIC}
    return {'closed': True, 'pid': child.pid, 'exit': status, 'logs': logs}


def execute(args):
    if args.authorized_single_build_probe is not True:
        raise ValueError('Separate Root single-build authorization required')
    bundle = read_pinned(args.bundle, args.bundle_sha256, MAX_BUNDLE)
    manifest = read_pinned(args.manifest, args.manifest_sha256, 2 * 1024**2)
    bootstrap = read_pinned(args.bootstrap, args.bootstrap_sha256, 2 * 1024**2)
    _, payloads = validate_archive(bundle, args.bundle_sha256, args.manifest_sha256,
                                    args.source, args.bootstrap_sha256)
    if payloads[MANIFEST_NAME] != manifest or payloads['tests/ci_image57/bridge_guest.py'] != bootstrap:
        raise ValueError('External manifest/bootstrap differs from closed capsule')
    remote = remote_command(args.guest_python, bootstrap, args.source, args.bundle_sha256,
                            args.manifest_sha256, args.bootstrap_sha256, args.guest_root, args.docker, args.tag)
    private = Path(args.private_root)
    authority.private_directory(private, Path(__file__).resolve().parents[2])
    access = load_guest_access()
    command, environment = access.configuration()
    state = transport(command + [remote], environment, Path(args.bundle), private, args.timeout_seconds)
    if not state['closed']:
        write_new(private / 'manual-review.private.json', encoded(state))
        return {'accepted': False, 'manual_review_required': True, 'child_known_closed': False}
    write_new(private / 'ssh-closure.private.json', encoded(state))
    if (state['exit'] != 0 or any(not row['bounded'] for row in state['logs'].values())
            or (private / 'ssh-stderr.private.log').stat().st_size != 0):
        raise ValueError('Bridge transport rejected; all artifacts retained')
    raw = (private / 'ssh-stdout.private.log').read_bytes()
    result = json_object(raw)
    if (type(result) is not dict or set(result) != {'schema', 'source', 'accepted', 'bundle_sha256',
                                                 'manifest_sha256', 'build_probe'}
            or result['schema'] != 'current57-bridge-result-v1' or result['accepted'] is not True
            or result['source'] != args.source or result['bundle_sha256'] != args.bundle_sha256
            or result['manifest_sha256'] != args.manifest_sha256 or type(result['build_probe']) is not dict):
        raise ValueError('Exact completed guest result differs')
    probe = result['build_probe']
    if (probe.get('source_commit') != args.source or type(probe.get('builds_attempted')) is not int
            or probe['builds_attempted'] != 1 or type(probe.get('runtime_probes_attempted')) is not int
            or probe['runtime_probes_attempted'] != 1 or probe.get('SBOM_SCA_complete') is not False):
        raise ValueError('One current build/probe result required')
    write_new(private / 'bridge-complete.private.json', raw)
    return {'accepted': True, 'source': args.source, 'builds_attempted': 1,
            'runtime_probes_attempted': 1, 'SBOM_SCA_complete': False}


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    phases = parser.add_subparsers(dest='phase', required=True)
    prepare_parser = phases.add_parser('prepare', allow_abbrev=False)
    prepare_parser.add_argument('--repository', type=Path, required=True)
    prepare_parser.add_argument('--source', required=True)
    prepare_parser.add_argument('--context-private', type=Path, required=True)
    prepare_parser.add_argument('--private-root', type=Path, required=True)
    execute_parser = phases.add_parser('execute', allow_abbrev=False)
    for name in ('bundle', 'manifest', 'bootstrap', 'private-root'):
        execute_parser.add_argument('--' + name, type=Path, required=True)
    for name in ('source', 'bundle-sha256', 'manifest-sha256', 'bootstrap-sha256',
                 'guest-python', 'guest-root', 'docker'):
        execute_parser.add_argument('--' + name, required=True)
    execute_parser.add_argument('--tag')
    execute_parser.add_argument('--timeout-seconds', type=float, required=True)
    execute_parser.add_argument('--authorized-single-build-probe', action='store_true', required=True)
    args = parser.parse_args(argv)
    try:
        result = (prepare(args.repository, args.source, args.context_private, args.private_root)
                  if args.phase == 'prepare' else execute(args))
    except Exception:  # noqa: BLE001 - opaque publication boundary; retain private artifacts
        print('{"accepted":false,"manual_review_required":true}')
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get('accepted', True) else 2


if __name__ == '__main__':
    raise SystemExit(main())
