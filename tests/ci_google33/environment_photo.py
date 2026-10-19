"""Read-only fingerprints of installed distributions and interpreter binaries."""
from __future__ import annotations

import hashlib
import importlib.metadata
import sys
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def packages():
    rows = []
    for distribution in importlib.metadata.distributions():
        records = []
        missing = []
        for relative in sorted(distribution.files or [], key=str):
            if Path(relative).suffix in {'.pyc', '.pyo'}:
                continue
            source = Path(distribution.locate_file(relative))
            if source.is_file():
                records.append(str(relative) + '\0' + digest(source))
            else:
                missing.append(str(relative))
        rows.append({'name': distribution.metadata['Name'], 'version': distribution.version,
                     'installed_files': len(records), 'missing_record_files': missing,
                     'installed_files_sha256': hashlib.sha256('\n'.join(records).encode()).hexdigest()})
    return sorted(rows, key=lambda row: (row['name'].casefold(), row['version']))


def interpreter():
    backing = Path(sys._base_executable)
    directory = backing.parent
    names = [Path(sys.executable), backing, *directory.glob('python*.dll'), *directory.glob('python*.so*')]
    return {str(path): digest(path) for path in sorted(set(names)) if path.is_file()}
