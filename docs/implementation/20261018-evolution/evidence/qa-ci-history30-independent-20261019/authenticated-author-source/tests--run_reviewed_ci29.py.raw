"""Run accepted CI29 checks against its exact historical source tree.

Later schema heads cannot satisfy CI29's literal revision/table assertions.
This runner extracts accepted schema29 commit fd636202045efa30b1430f4a9dd8ab287ec76357 as a local Git ancestor into a new owned directory;
it never rewrites historical assertions or supplies fabricated old metadata.
The optional restore mode executes the unchanged populated CI29 restore node ID
using that source/runtime and the caller's explicitly isolated test database.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'fd636202045efa30b1430f4a9dd8ab287ec76357'
RESTORE_NODES = (
    'tests/integration_client_link_restore.py::test_revision29_restore_preserves_member_links_and_all_revision26_27_28_contracts',
)


def canonical_name(raw: str, *, directory: bool = False) -> str:
    """Use one relative spelling on both Windows and POSIX before any write."""
    if directory and raw.endswith('/'):
        raw = raw[:-1]
    name = PurePosixPath(raw)
    assert raw and raw == name.as_posix() and not name.is_absolute()
    assert '..' not in name.parts and '\\' not in raw and ':' not in raw
    assert not any(ord(char) < 32 or ord(char) == 127 for char in raw)
    return raw


def tree_specification(repository: Path) -> tuple[dict, set[str]]:
    """Read original object IDs independently of archive attributes/replace refs."""
    listing = subprocess.check_output(
        ['git', '--no-replace-objects', 'ls-tree', '-r', '-z', '--long', REVISION], cwd=repository)
    assert listing and listing.endswith(b'\0'), 'Historical tree listing is incomplete'
    files = {}
    directories = set()
    local_names = set()
    for record in listing[:-1].split(b'\0'):
        metadata, separator, raw = record.partition(b'\t')
        assert separator
        match = re.fullmatch(rb'(100644|100755) blob ([0-9a-f]{40}) +([0-9]+)', metadata)
        assert match, 'Historical tree contains an unsupported object or mode'
        name = canonical_name(raw.decode('utf8'))
        local = os.path.normcase(name)
        assert name not in files and local not in local_names, 'Historical tree has aliased names'
        local_names.add(local)
        files[name] = (int(match[1], 8) & 0o777, match[2].decode('ascii'), int(match[3]))
        directories.update(parent.as_posix() for parent in PurePosixPath(name).parents if parent != PurePosixPath('.'))
    assert not set(files).intersection(directories), 'Historical file/directory collision'
    return files, directories


def validate_restore_environment() -> None:
    """Fail before archive/fixtures if isolated URLs or evidence storage are absent."""
    sys.path.insert(0, str(ROOT))
    from tests.isolation import validate_postgres_test_url
    for name in ['METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL']:
        validate_postgres_test_url(os.environ[name])
    evidence = Path(os.environ['METODOBASE_TEST_EVIDENCE_DIR']).resolve()
    if not evidence.is_dir():
        raise ValueError('The isolated restore evidence directory must already exist')


def materialize(repository: Path, destination: Path) -> dict:
    """Extract regular Git files from the pinned ancestor to an unused directory.

    The repository is read-only. Archive entries must remain within the owned
    destination; links and special files are rejected. No checkout, database,
    network access, deletion or mutation of another worktree is performed.
    """
    repository = repository.resolve(strict=True)
    destination = destination.resolve()
    subprocess.run(['git', '--no-replace-objects', 'merge-base', '--is-ancestor', REVISION, 'HEAD'],
                   cwd=repository, check=True, capture_output=True)
    commit = subprocess.check_output(['git', '--no-replace-objects', 'rev-parse', '--verify', REVISION + '^{commit}'],
                                     cwd=repository, text=True).strip()
    assert commit == REVISION
    expected, directories = tree_specification(repository)
    # Command-local settings change no repository/user configuration. Archive
    # must emit blob bytes, including on a Windows autocrlf checkout; never
    # normalize received bytes to excuse an object-ID mismatch.
    archive = subprocess.check_output(['git', '--no-replace-objects', '-c', 'tar.umask=0022',
                                       '-c', 'core.autocrlf=false', '-c', 'core.eol=lf',
                                       'archive', '--format=tar', REVISION], cwd=repository)
    destination.mkdir(parents=True, exist_ok=False)
    seen = set()
    seen_directories = set()
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as source:
        for entry in source:
            name = canonical_name(entry.name, directory=entry.isdir())
            target = (destination / Path(*PurePosixPath(name).parts)).resolve()
            assert target.is_relative_to(destination)
            if entry.isdir():
                assert name in directories and name not in seen_directories, 'Unexpected/duplicate historical directory'
                assert entry.mode == 0o755, 'Historical directory mode differs'
                seen_directories.add(name)
                target.mkdir(parents=True, exist_ok=True)
            else:
                assert entry.type in {tarfile.REGTYPE, tarfile.AREGTYPE} and entry.sparse is None, 'Historical archive contains a non-regular file'
                assert name in expected and name not in seen, 'Unexpected/duplicate historical file'
                mode, oid, size = expected[name]
                assert entry.mode == mode and entry.size == size, 'Historical archive mode/size differs from tree'
                stream = source.extractfile(entry)
                assert stream is not None
                content = stream.read(size + 1)
                assert len(content) == size, 'Historical blob is truncated'
                actual = hashlib.sha1(b'blob ' + str(size).encode('ascii') + b'\0' + content,
                                      usedforsecurity=False).hexdigest()
                assert actual == oid, 'Historical blob bytes differ from pinned tree'
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output:
                    output.write(content)
                target.chmod(mode)
                seen.add(name)
    assert seen == set(expected), 'Historical archive omitted pinned tree files'
    return {'pinned_commit': commit, 'files': len(seen),
            'archive_sha256': hashlib.sha256(archive).hexdigest(),
            'source_directory': str(destination), 'regular_files_only': True,
            'pinned_tree_blobs_verified': True, 'replacement_objects_disabled': True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--history-repository', type=Path, default=ROOT)
    parser.add_argument('--junitxml', type=Path)
    args = parser.parse_args()
    if args.junitxml:
        try:
            validate_restore_environment()
        except (KeyError, OSError, ValueError):
            parser.error('Historical restore requires explicit isolated PostgreSQL URLs and an existing evidence directory')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = materialize(args.history_repository, out / 'source')
    source = out / 'source'
    if args.junitxml:
        target = args.junitxml.resolve()
        assert not target.exists(), 'Refusing to overwrite an earlier restore report'
        command = [sys.executable, '-X', 'utf8', 'tests/run_isolated.py', *RESTORE_NODES,
                   '-q', '--tb=short', '--junitxml=' + str(target)]
        timeout = 240
        report['scope'] = 'The unchanged populated CI29 restore test under the exact accepted CI29 runtime'
    else:
        command = [sys.executable, '-X', 'utf8', 'tests/verify_member_links_ci.py',
                   '--output', str(out / 'review'), '--verify-only',
                   '--history-repository', str(args.history_repository)]
        timeout = 45
        report['scope'] = 'Historical CI29 wiring/assertions and actual revision29 ORM markers; no restore/browser/services'
    result = subprocess.run(command, cwd=source, capture_output=True, timeout=timeout, check=False)
    (out / 'stdout.log').write_bytes(result.stdout)
    (out / 'stderr.log').write_bytes(result.stderr)
    report['exit_code'] = result.returncode
    (out / 'receipt.json').write_bytes((json.dumps(report, indent=2) + '\n').encode('utf8'))
    print(json.dumps({'pinned_commit': REVISION, 'files': report['files'],
                      'exit_code': result.returncode, 'restore': bool(args.junitxml)}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
