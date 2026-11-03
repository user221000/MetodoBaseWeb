"""Publish only a finite phase/exception code from historical37 bootstrap.

This standalone diagnostic does not execute PostgreSQL or decide acceptance.
The workflow authenticates this helper's complete Git blob before invocation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import stat

SOURCE = '878082b242cdfa23e1e4c134f675c12b535a2cd7'
SCHEMA = 'historical37-bootstrap-stage-v1'
STAGES = frozenset(('imports', 'source_photo', 'ancestry', 'versions', 'initdb', 'pg_ctl_start',
                    'catalogue_roles', 'contracts42953', 'generation27', 'contract27', 'source_quiet'))
EXCEPTIONS = frozenset(('CalledProcessError', 'AssertionError', 'ValueError', 'OSError', 'KeyError',
                       'FileNotFoundError', 'PermissionError', 'TypeError', 'RuntimeError', 'OTHER'))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate diagnostic field')
        result[key] = value
    return result


def project(raw, helper_source):
    if not isinstance(helper_source, str) or not re.fullmatch('[0-9a-f]{40}', helper_source):
        raise ValueError('Exact helper source is required')
    result = {'source_commit': SOURCE, 'helper_source_commit': helper_source,
              'schema': SCHEMA, 'acceptance_evidence': False, 'diagnostic_available': False,
              'phase': 'unknown', 'exception_type': 'unknown', 'child_exit': None}
    if raw is None:
        return result
    if type(raw) is not bytes or not 0 < len(raw) <= 1024:
        raise ValueError('Bounded diagnostic bytes are required')
    value = json.loads(raw, object_pairs_hook=unique_object)
    if (type(value) is not dict or set(value) != {'schema', 'phase', 'exception_type', 'child_exit'}
            or value['schema'] != SCHEMA or type(value['phase']) is not str or value['phase'] not in STAGES
            or type(value['exception_type']) is not str or value['exception_type'] not in EXCEPTIONS):
        raise ValueError('Finite bootstrap diagnostic contract differs')
    code = value['child_exit']
    if value['exception_type'] == 'CalledProcessError':
        if type(code) is not int or code == 0 or not -255 <= code <= 255:
            raise ValueError('Expected a nonzero bounded child exit code')
    elif code is not None:
        raise ValueError('Non-process exception cannot carry a child exit')
    return result | value | {'diagnostic_available': True}


def read(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=False) != path.absolute():
        raise ValueError('Unaliased absolute diagnostic path required')
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 1024:
        raise ValueError('Expected one bounded regular diagnostic file')
    with path.open('rb') as stream:
        raw = stream.read(1025)
    if len(raw) > 1024:
        raise ValueError('Diagnostic grew beyond its byte bound')
    after = path.lstat()
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
    if identity(before) != identity(after):
        raise ValueError('Diagnostic changed during read')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--helper-source', required=True)
    args = parser.parse_args()
    print(json.dumps(project(read(args.input), args.helper_source), sort_keys=True))


if __name__ == '__main__':
    main()
