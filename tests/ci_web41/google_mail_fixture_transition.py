"""Finite Google/email evolution in a coordinated, quiet CI checkout.

Before/after photos reject checkout drift. These checks do not claim isolation
against an arbitrary writer replacing Python files after a validated read.
"""
import hashlib
import os
import stat
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRANSITIONS = {
    'tests/test_google33_http.py': (
        '465a7ddfa0c9498997476bf7903753a3b13f0b79ccf4378ecdbaba1444630412',
        'b1a1fb9fda9a3c6d5353a6245ecf3e90c3d53a4b53184508f078020bcbb92967'),
    'tests/test_google33_headers.py': (
        'f639ecf7d2ab2ee626edbf4cd230ce4eaf7be2207684d69a2dae733953f80882',
        '27ca79e6aadc0a3b222500f813a4fb3ad55224199521fa038d54ed8b8083df43'),
    'tests/test_google33_conflict_window.py': (
        '47d066e94998c632952467507b4e7324a935f567978593ab6c99d787d15e0bf6',
        '47ed0932c71825f0a148d673affbe9c3a2c643cfe98871ab144e81172f3a8378'),
    'tests/test_account_security37_critical_edges.py': (
        '6e139738a8a5e5a02ef704cbfc945215cdd4d5d3ea6afab1f9055871591a8ab7',
        'a3d07502e18f2ad77d05377b69546feac581bb49437252d04ab2670d48a11af7'),
    'tests/test_google33_recovery.py': (
        '5ceeb9ca2faf2ab40b1e37bc091f72ecf954d6e791c30d3c487586bffb8b9735',
        '2bce0392f62a0f9dae4ce2c1a79b982bf4f9ca4d9b4a175b7be4a7dbde9b66d7'),
}
HELPER = 'tests/ci_web41/google_mail_http_fixture.py'
HELPER_SHA256 = '6ef3cff2b85a84384f57ed6dcc28f8dfaa16c54e210106bb45f87a56c99840e0'
DEPENDENCIES = {
    'tests/test_google_email_login.py': '5c037226f6929b62f3795d4d50bc1258ecc284397691891265cf8f929aca2b39',
}
PHOTO_FILES = (HELPER, *TRANSITIONS, *DEPENDENCIES,
               'tests/ci_web41/google_mail_fixture_transition.py',
               'tests/ci_web41/composition.py', 'tests/test_current41_google_mail_fixture.py')


def source_bytes(name):
    path = ROOT / name
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or path.resolve(strict=True) != path.absolute() or info.st_size > 131072):
        raise ValueError('Current Google mail fixture source is not plain and bounded')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(131073)
        finished = os.fstat(stream.fileno())
    after = path.lstat()
    identities = [(item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns,
                   item.st_nlink, item.st_mode) for item in (info, opened, finished, after)]
    lf = raw.replace(b'\r\n', b'\n')
    if (len(set(identities)) != 1 or info.st_ctime_ns != after.st_ctime_ns
            or opened.st_ctime_ns != finished.st_ctime_ns or len(raw) != info.st_size
            or len(raw) > 131072 or raw not in (lf, lf.replace(b'\n', b'\r\n'))
            or b'\r' in lf):
        raise ValueError('Current Google mail fixture source differs')
    return raw


def require_source(name, expected):
    raw = source_bytes(name)
    if hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest() != expected:
        raise ValueError('Current Google mail fixture source differs')


def source_photo():
    return {name: hashlib.sha256(source_bytes(name)).hexdigest() for name in PHOTO_FILES}


def require_quiet(expected):
    if source_photo() != expected:
        raise ValueError('Current Google mail fixture checkout changed during execution')


def specification(parent):
    for name, expected in DEPENDENCIES.items():
        require_source(name, expected)
    require_source(HELPER, HELPER_SHA256)
    result = deepcopy(parent)
    for name, (before, after) in TRANSITIONS.items():
        if parent['modules'][name]['source_sha256_LF'] != before:
            raise ValueError('Historical Google fixture admission differs')
        require_source(name, after)
        result['modules'][name]['source_sha256_LF'] = after
    return result
