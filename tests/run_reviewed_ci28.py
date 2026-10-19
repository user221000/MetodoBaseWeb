"""Run accepted CI28 checks against its exact historical source tree.

Later schema heads cannot satisfy CI28's literal revision/table assertions.
This runner extracts a pinned local Git ancestor into a new owned directory;
it never rewrites historical assertions or supplies fabricated old metadata.
The optional restore mode executes the two unchanged CI28 restore node IDs
using that source/runtime and the caller's explicitly isolated test database.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REVISION = '66d9dec0e15dd873038bd248d3883daeeb27d4ca'
RESTORE_NODES = (
    'tests/integration_backup_restore_postgres.py::test_encrypted_pg_restore_preserves_rows_constraints_and_private_objects',
    'tests/integration_recovery28_restore_review.py::test_revision28_restore_preserves_recovery_and_all_revision26_27_contracts',
)


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
    subprocess.run(['git', 'merge-base', '--is-ancestor', REVISION, 'HEAD'],
                   cwd=repository, check=True, capture_output=True)
    commit = subprocess.check_output(['git', 'rev-parse', REVISION + '^{commit}'],
                                     cwd=repository, text=True).strip()
    assert commit == REVISION
    archive = subprocess.check_output(['git', 'archive', '--format=tar', REVISION], cwd=repository)
    destination.mkdir(parents=True, exist_ok=False)
    count = 0
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as source:
        for entry in source:
            name = PurePosixPath(entry.name)
            assert not name.is_absolute() and '..' not in name.parts and '\\' not in entry.name
            target = (destination / Path(*name.parts)).resolve()
            assert target.is_relative_to(destination)
            if entry.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                assert entry.isfile(), 'Historical archive contains a non-regular file'
                target.parent.mkdir(parents=True, exist_ok=True)
                stream = source.extractfile(entry)
                assert stream is not None
                target.write_bytes(stream.read())
                count += 1
    return {'pinned_commit': commit, 'files': count,
            'archive_sha256': hashlib.sha256(archive).hexdigest(),
            'source_directory': str(destination), 'regular_files_only': True}


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
        report['scope'] = 'The two unchanged CI28 restore tests under the exact accepted CI28 runtime'
    else:
        command = [sys.executable, '-X', 'utf8', 'tests/verify_history_landing_ci.py',
                   '--output', str(out / 'review'), '--verify-only']
        timeout = 45
        report['scope'] = 'Historical CI28 wiring/assertions and actual old ORM marker; no restore/browser/services'
    result = subprocess.run(command, cwd=source, capture_output=True, timeout=timeout)
    (out / 'stdout.log').write_bytes(result.stdout)
    (out / 'stderr.log').write_bytes(result.stderr)
    report['exit_code'] = result.returncode
    (out / 'receipt.json').write_bytes((json.dumps(report, indent=2) + '\n').encode('utf8'))
    print(json.dumps({'pinned_commit': REVISION, 'files': report['files'],
                      'exit_code': result.returncode, 'restore': bool(args.junitxml)}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
