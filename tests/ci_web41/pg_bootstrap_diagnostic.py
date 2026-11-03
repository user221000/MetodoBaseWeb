"""Publish only a finite phase/exception code from historical37 bootstrap.

This standalone diagnostic does not execute PostgreSQL or decide acceptance.
The workflow authenticates this helper's complete Git blob before invocation.
"""
from __future__ import annotations

import argparse
import hashlib
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


def read_startup_log(path):
    path = Path(path)
    if (not path.is_absolute() or path.resolve(strict=False) != path.absolute()
            or path.name != 'postgresql.private.log'
            or path.parent.name != 'ci37-pg-cluster-private'):
        raise ValueError('Explicit historical37 private startup log required')
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or not 0 < before.st_size <= 65536):
        raise ValueError('Bounded regular startup log required')
    with path.open('rb') as stream:
        raw = stream.read(65537)
    after = path.lstat()
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
    if len(raw) > 65536 or identity(before) != identity(after):
        raise ValueError('Startup log grew or changed during read')
    return raw


def project_startup_reason(stage_raw, log_raw, helper_source):
    stage = project(stage_raw, helper_source)
    result = {'schema': 'historical37-startup-reason-v1', 'source_commit': SOURCE,
              'helper_source_commit': helper_source, 'acceptance_evidence': False,
              'category': 'unknown', 'log_sha256': None, 'log_bytes': 0}
    if log_raw is None:
        return result
    if type(log_raw) is not bytes or not 0 < len(log_raw) <= 65536:
        raise ValueError('Bounded startup log bytes required')
    result.update(log_sha256=hashlib.sha256(log_raw).hexdigest(), log_bytes=len(log_raw))
    if (not stage['diagnostic_available'] or stage['phase'] != 'pg_ctl_start'
            or stage['exception_type'] != 'CalledProcessError'):
        return result
    # A diagnostic category only: no PostgreSQL message, path or user content is
    # published, and matching a line cannot turn a failed bootstrap into PASS.
    prefix = rb'^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:.]+ UTC \[[0-9]+\] FATAL:  '
    expected = (rb'could not create lock file "/var/run/postgresql/\.s\.PGSQL\.55483\.lock": '
                rb'Permission denied\r?$')
    if len(re.findall(prefix + expected, log_raw, re.MULTILINE)) == 1:
        result['category'] = 'unix_socket_lock_permission_denied'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--helper-source', required=True)
    parser.add_argument('--startup-log', type=Path)
    args = parser.parse_args()
    raw = read(args.input)
    print(json.dumps(project(raw, args.helper_source), sort_keys=True))
    if args.startup_log is not None:
        print(json.dumps(project_startup_reason(raw, read_startup_log(args.startup_log), args.helper_source), sort_keys=True))


if __name__ == '__main__':
    main()
