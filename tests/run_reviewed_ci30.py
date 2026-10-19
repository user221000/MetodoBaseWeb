"""Materialize authentic CI30 blobs and run its unchanged checks on source30.

The destination is new and private. Git attributes, archive filters, replace
refs and checkout line-ending conversion never supply source bytes. This is a
historical execution, separate from the current MFA31 acceptance jobs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
REVISION = '57335e5b4bcba3c76c97d47e481b526fb52874a6'
TREE = '31bebf83a760a500420f6552628d6a3a022b8832'
FILES = 6591
REGULAR_BYTES = 233299475
BASELINE_SHA256 = 'd918b51ac07a37b2c3b7bd3269303c1adf6139a0949b89753f705479e63d6270'
WORKFLOW_SHA256 = '5f74662c11611e3041d87a8cbd4a6a8c6828606da7c46e1d2446af6b1e36ab9b'
DEVICES = re.compile(r'(?i)(?:con|prn|aux|nul|com[1-9\u00b9\u00b2\u00b3]|lpt[1-9\u00b9\u00b2\u00b3])(?:\..*)?\Z')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def trusted_baseline() -> dict:
    raw = (ROOT / 'tests/ci_mfa31/baseline.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == BASELINE_SHA256, 'CI30 trust metadata differs')
    result = json.loads(raw)
    require((result['historical30_commit'], result['tree'], result['files'], result['regular_bytes'])
            == (REVISION, TREE, FILES, REGULAR_BYTES), 'CI30 constants differ')
    workflow = (ROOT / 'tests/ci_mfa31/ci30-before.yml').read_bytes()
    require(hashlib.sha256(workflow).hexdigest() == WORKFLOW_SHA256, 'CI30 workflow snapshot differs')
    require(len(result['helpers23_sha256']) == 23, 'CI30 helper inventory differs')
    for name, expected in result['helpers23_sha256'].items():
        # A Windows checkout may use CRLF. Historical materialization below
        # compares original raw Git blobs, never normalized output bytes.
        raw = (ROOT / canonical_name(name)).read_bytes().replace(b'\r\n', b'\n')
        require(hashlib.sha256(raw).hexdigest() == expected, 'An immutable CI22-30 helper differs')
    return result


def canonical_name(raw: str) -> str:
    path = PurePosixPath(raw)
    require(bool(raw) and raw == path.as_posix() and not path.is_absolute(), 'Noncanonical Git path')
    require(not any(char in raw for char in '\\:<>"|?*') and unicodedata.normalize('NFC', raw) == raw,
            'Ambiguous Git path')
    require(not any(unicodedata.category(char) in {'Cc', 'Cf', 'Cs'} for char in raw), 'Control character in Git path')
    for part in path.parts:
        require(part not in {'.', '..'} and not part.endswith((' ', '.')) and not DEVICES.fullmatch(part),
                'Unsafe Windows/POSIX Git component')
    return raw


def regular_directory(path: Path) -> None:
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and not path.is_symlink()
            and not (getattr(info, 'st_file_attributes', 0) & 0x400), 'Directory is linked or special')
    require(path.resolve(strict=True) == path.absolute(), 'Directory has an aliased ancestor')


def new_directory(path: Path) -> Path:
    """Reject existing targets and reparse ancestors before creating own paths."""
    path = path.absolute()
    require('..' not in path.parts, 'Output has a lexical parent alias')
    require(not path.exists() and not path.is_symlink(), 'Output already exists')
    missing = []
    parent = path
    while not parent.exists():
        require(not parent.is_symlink(), 'Output ancestor is a dangling link')
        missing.append(parent)
        parent = parent.parent
    for ancestor in (parent, *parent.parents):
        regular_directory(ancestor)
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        regular_directory(directory)
    return path


def git_environment() -> dict:
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith('GIT_')}
    environment.update(GIT_NO_REPLACE_OBJECTS='1', GIT_CONFIG_NOSYSTEM='1',
                       GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0',
                       GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    return environment


def git(repository: Path, *arguments: str) -> bytes:
    return subprocess.check_output(['git', '--no-replace-objects', *arguments],
                                   cwd=repository, env=git_environment(), stderr=subprocess.PIPE)


def tree_specification(repository: Path) -> dict:
    require(git(repository, 'rev-parse', '--verify', REVISION + '^{commit}').strip().decode() == REVISION,
            'Historical commit is absent')
    require(git(repository, 'rev-parse', '--verify', REVISION + '^{tree}').strip().decode() == TREE,
            'Historical tree differs')
    subprocess.run(['git', '--no-replace-objects', 'merge-base', '--is-ancestor', REVISION, 'HEAD'],
                   cwd=repository, env=git_environment(), check=True, capture_output=True)
    listing = git(repository, 'ls-tree', '-r', '-z', '--long', REVISION)
    require(bool(listing) and listing.endswith(b'\0'), 'Incomplete Git tree listing')
    files, names, directories = {}, set(), {}
    for record in listing[:-1].split(b'\0'):
        metadata, separator, raw = record.partition(b'\t')
        match = re.fullmatch(rb'(100644|100755) blob ([0-9a-f]{40}) +([0-9]+)', metadata)
        require(bool(separator and match), 'Unsupported Git mode/object')
        name = canonical_name(raw.decode('utf8'))
        key = name.casefold()
        require(key not in names, 'Case-folded Git path collision')
        names.add(key)
        files[name] = (int(match[1], 8) & 0o777, match[2].decode('ascii'), int(match[3]))
        for parent in PurePosixPath(name).parents:
            if parent != PurePosixPath('.'):
                spelling = parent.as_posix()
                require(directories.get(spelling.casefold(), spelling) == spelling,
                        'Case-folded Git directory alias')
                directories[spelling.casefold()] = spelling
    require(not names.intersection(directories), 'Git file/directory collision')
    require(len(files) == FILES and sum(item[2] for item in files.values()) == REGULAR_BYTES,
            'Historical file count/byte count differs')
    return files


def read_exact(stream, length: int) -> bytes:
    result = bytearray()
    while len(result) < length:
        block = stream.read(length - len(result))
        require(bool(block), 'Truncated Git batch output')
        result.extend(block)
    return bytes(result)


def materialize(repository: Path, destination: Path, manifest: Path) -> dict:
    repository = repository.resolve(strict=True)
    expected = tree_specification(repository)
    require(not destination.absolute().is_relative_to(repository), 'Historical output cannot be inside the working tree')
    destination = new_directory(destination)
    records = []
    # Request one object at a time so neither pipe can fill while its peer is
    # waiting. No shell, Git archive, checkout filters or attributes are used.
    process = subprocess.Popen(['git', '--no-replace-objects', 'cat-file', '--batch'], cwd=repository,
                               env=git_environment(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    try:
        for name, (mode, oid, size) in expected.items():
            process.stdin.write((oid + '\n').encode('ascii'))
            process.stdin.flush()
            header = process.stdout.readline(200)
            require(header == f'{oid} blob {size}\n'.encode('ascii'), 'Git object header differs')
            target = destination.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            for parent in (target.parent, *target.parent.parents):
                if parent == destination.parent:
                    break
                regular_directory(parent)
            blob = hashlib.sha1(b'blob ' + str(size).encode('ascii') + b'\0', usedforsecurity=False)
            sha = hashlib.sha256()
            remaining = size
            with target.open('xb') as output:
                while remaining:
                    data = read_exact(process.stdout, min(remaining, 1024 * 1024))
                    output.write(data)
                    blob.update(data)
                    sha.update(data)
                    remaining -= len(data)
            require(read_exact(process.stdout, 1) == b'\n' and blob.hexdigest() == oid,
                    'Historical blob differs from pinned Git object')
            require(target.stat().st_size == size, 'Written historical file has wrong size')
            target.chmod(mode)
            records.append({'path': name, 'mode': oct(mode), 'git_blob': oid, 'size': size,
                            'sha256': sha.hexdigest()})
        process.stdin.close()
        require(process.wait(timeout=30) == 0 and not process.stdout.read(1), 'Git batch did not close cleanly')
        require(not process.stderr.read(), 'Git batch produced a diagnostic')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    raw = (json.dumps(records, indent=2) + '\n').encode('utf8')
    with manifest.open('xb') as stream:
        stream.write(raw)
    return {'commit': REVISION, 'tree': TREE, 'files': len(records), 'regular_bytes': REGULAR_BYTES,
            'source_directory': str(destination), 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
            'regular_git_blobs_only': True, 'replacement_objects_disabled': True,
            'attributes_or_archive_not_used': True}


def execute(command: list[str], source: Path, out: Path, name: str, timeout: int, environment=None) -> None:
    with (out / (name + '.stdout.log')).open('xb') as stdout, (out / (name + '.stderr.log')).open('xb') as stderr:
        result = subprocess.run(command, cwd=source, env=environment, stdout=stdout, stderr=stderr,
                                timeout=timeout, check=False)
    require(result.returncode == 0, 'An unchanged historical CI30 gate failed: ' + name)


def historical_checks(source: Path, out: Path, repository: Path, *, include_vm: bool) -> dict:
    execute([sys.executable, '-X', 'utf8', 'tests/verify_history_index_ci.py', '--output', str(out / 'review'),
             '--history-repository', str(repository)], source, out, 'ci30-full', 240)
    review = json.loads((out / 'review/review.json').read_bytes())
    # The unchanged verifier itself retains all old assertions and checks these
    # canaries. These independent counts reject a truncated historical run.
    for key, count in [('unauthorized_delta_canaries', 33), ('current_report_canaries', 55),
                       ('index_report_canaries', 24), ('followup_report_canaries', 12),
                       ('current_inert_fixture_cases', 27)]:
        require(len(review[key]) == count, 'Historical CI30 canary scope differs: ' + key)
    result = {'workflow_canaries': 33, 'member_report_canaries': 55, 'index_report_canaries': 24,
              'followup_report_canaries': 12, 'inert_fixture_cases': 27, 'vm_executed': False}
    if include_vm:
        import yaml
        workflow = yaml.safe_load((source / '.github/workflows/ci.yml').read_bytes())
        blocks = [step['run'] for step in workflow['jobs']['frontend-contracts']['steps'] if 'run' in step]
        require(len(blocks) == 6, 'Historical frontend run-block count differs')
        bash = os.environ.get('METODOBASE_CI_BASH') or (
            'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash'))
        require(bool(bash), 'Bash is required for the unchanged historical VM gates')
        environment = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', ''))
        for index, block in enumerate(blocks):
            script = out / f'ci30-vm-{index}.sh'
            script.write_bytes(('set -euo pipefail\n' + block).encode('utf8'))
            execute([bash, script.as_posix()], source, out, f'ci30-vm-{index}', 180, environment)
        files = []
        for block in blocks:
            for line in block.splitlines():
                if line.startswith('node tests/') and ' > ' in line:
                    files.append(line.split(' > ')[1])
        totals = []
        for name in files:
            data = json.loads((source / name).read_bytes())
            if 'report' in data and 'total' not in data:
                require(all(item['passed'] is True for item in data['report']), 'Historical VM case failed')
                totals.append(len(data['report']))
            else:
                require(type(data['total']) is int and data['passed'] == data['total'], 'Historical VM counters differ')
                totals.append(data['total'])
        require(len(files) == len(set(files)) == 23 and sum(totals) == 348, 'Historical VM execution inventory differs')
        result.update(vm_executed=True, vm_modules=len(files), vm_assertion_executions=sum(totals))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--history-repository', type=Path, default=ROOT)
    parser.add_argument('--materialize-only', action='store_true')
    parser.add_argument('--include-vm', action='store_true')
    args = parser.parse_args()
    require(not (args.materialize_only and args.include_vm), 'VM checks cannot be materialize-only')
    trusted_baseline()
    repository = args.history_repository.resolve(strict=True)
    require(not args.output.absolute().is_relative_to(repository), 'Output cannot be in the repository')
    out = new_directory(args.output)
    report = materialize(repository, out / 'source', out / 'source-manifest.json')
    if not args.materialize_only:
        report['historical_gates'] = historical_checks(out / 'source', out, repository, include_vm=args.include_vm)
    report['scope'] = 'Authentic historical CI30; current MFA31 acceptance remains separate'
    (out / 'receipt.json').write_bytes((json.dumps(report, indent=2) + '\n').encode('utf8'))
    print(json.dumps({'commit': REVISION, 'files': FILES, 'regular_bytes': REGULAR_BYTES,
                      'materialize_only': args.materialize_only, 'historical_gates': report.get('historical_gates')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
