"""Admission and transport negatives for the explicit Google/mail HTTP fixture."""
import asyncio
import hashlib
import json
import os
from copy import deepcopy

import pytest

from tests.ci_web41 import google_mail_fixture_transition as transition
from tests.ci_web41.google_mail_http_fixture import WireMemory


@pytest.fixture
def admitted(tmp_path, monkeypatch):
    parent = json.loads((transition.ROOT / 'tests/ci_web41/current-fixture-map.json').read_text('utf8'))
    for name in transition.PHOTO_FILES:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((transition.ROOT / name).read_bytes())
    monkeypatch.setattr(transition, 'ROOT', tmp_path)
    return parent


def test_admission_changes_only_three_reviewed_hashes_without_mutating_parent(admitted):
    original = deepcopy(admitted)
    actual = transition.specification(admitted)
    expected = deepcopy(admitted)
    for name, (_, after) in transition.TRANSITIONS.items():
        expected['modules'][name]['source_sha256_LF'] = after
    assert actual == expected and admitted == original
    assert actual is not admitted and actual['modules'] is not admitted['modules']


@pytest.mark.parametrize('name', [transition.HELPER, *transition.TRANSITIONS, *transition.DEPENDENCIES])
def test_modified_consumer_or_transport_is_rejected_before_admission(admitted, name):
    path = transition.ROOT / name
    path.write_bytes(path.read_bytes() + b'\n# unreviewed mutation\n')
    with pytest.raises(ValueError, match='source differs'):
        transition.specification(admitted)


@pytest.mark.parametrize('name', list(transition.TRANSITIONS))
def test_changed_historical_map_is_rejected(admitted, name):
    admitted['modules'][name]['source_sha256_LF'] = '0' * 64
    with pytest.raises(ValueError, match='Historical Google fixture admission differs'):
        transition.specification(admitted)


@pytest.mark.parametrize('line_endings', ['lf', 'crlf'])
def test_uniform_checkout_frames_preserve_exact_reviewed_source(admitted, line_endings):
    for name in [transition.HELPER, *transition.TRANSITIONS]:
        path = transition.ROOT / name
        data = path.read_bytes().replace(b'\r\n', b'\n')
        path.write_bytes(data if line_endings == 'lf' else data.replace(b'\n', b'\r\n'))
    assert transition.specification(admitted)['modules']


@pytest.mark.parametrize('invalid', [b'one\r\ntwo\n', b'one\rtwo\n', b'x' * 131073],
                         ids=['mixed-newlines', 'bare-cr', 'oversized'])
def test_mixed_bare_cr_and_oversized_source_reject_even_matching_digest(tmp_path, monkeypatch, invalid):
    monkeypatch.setattr(transition, 'ROOT', tmp_path)
    (tmp_path / 'sample').write_bytes(invalid)
    digest = hashlib.sha256(invalid.replace(b'\r\n', b'\n')).hexdigest()
    with pytest.raises(ValueError):
        transition.require_source('sample', digest)


def test_hard_link_source_is_rejected(admitted):
    source = transition.ROOT / transition.HELPER
    os.link(source, transition.ROOT / 'aliased-helper')
    with pytest.raises(ValueError, match='not plain and bounded'):
        transition.specification(admitted)


def test_source_identity_change_during_read_is_rejected(admitted, monkeypatch):
    real_fstat = transition.os.fstat
    calls = 0

    def changed(fd):
        nonlocal calls
        result = real_fstat(fd)
        calls += 1
        if calls == 2:
            from types import SimpleNamespace
            return SimpleNamespace(st_dev=result.st_dev, st_ino=result.st_ino + 1,
                st_size=result.st_size, st_mtime_ns=result.st_mtime_ns,
                st_nlink=result.st_nlink, st_mode=result.st_mode, st_ctime_ns=result.st_ctime_ns)
        return result

    monkeypatch.setattr(transition.os, 'fstat', changed)
    with pytest.raises(ValueError, match='source differs'):
        transition.specification(admitted)


@pytest.mark.parametrize('name', transition.PHOTO_FILES)
def test_late_checkout_change_rejects_final_publication(admitted, name):
    photo = transition.source_photo()
    transition.require_quiet(photo)
    path = transition.ROOT / name
    original = path.read_bytes()
    newline = b'\r\n' if b'\r\n' in original else b'\n'
    path.write_bytes(original + newline + b'# late checkout drift' + newline)
    with pytest.raises(ValueError, match='checkout changed during execution'):
        transition.require_quiet(photo)


def test_changed_fstat_ctime_rejects_same_size_and_restored_mtime(admitted, monkeypatch):
    real_fstat = transition.os.fstat
    calls = 0

    def changed(fd):
        nonlocal calls
        from types import SimpleNamespace
        result = real_fstat(fd)
        calls += 1
        return SimpleNamespace(st_dev=result.st_dev, st_ino=result.st_ino,
            st_size=result.st_size, st_mtime_ns=result.st_mtime_ns,
            st_nlink=result.st_nlink, st_mode=result.st_mode,
            st_ctime_ns=result.st_ctime_ns + (1 if calls == 2 else 0))

    monkeypatch.setattr(transition.os, 'fstat', changed)
    with pytest.raises(ValueError, match='source differs'):
        transition.specification(admitted)


def test_wire_fixed_window_counts_are_atomic_and_expiry_never_slides():
    from web.rate_limiter_redis import _FIXED_WINDOW_LUA
    wire = WireMemory()

    async def scenario():
        results = await asyncio.gather(*(wire.eval(_FIXED_WINDOW_LUA, 1, 'actor', 60) for _ in range(32)))
        assert sorted(item[0] for item in results) == list(range(1, 33))
        assert {item[1] for item in results} == {60}
        wire.now = 30000
        assert await wire.eval(_FIXED_WINDOW_LUA, 1, 'actor', 60) == [33, 30]
        assert await wire.eval(_FIXED_WINDOW_LUA, 1, 'other', 60) == [1, 60]
        wire.now = 60000
        assert await wire.eval(_FIXED_WINDOW_LUA, 1, 'actor', 60) == [1, 60]

    asyncio.run(scenario())


@pytest.mark.parametrize('kind', ['rate', 'otp'])
def test_wire_transport_failure_propagates(kind):
    from web.rate_limiter_redis import _FIXED_WINDOW_LUA
    from web.services.google_email_login import CONSUME_LUA
    wire = WireMemory()
    wire.fail_eval = True
    args = (_FIXED_WINDOW_LUA, 1, 'actor', 60) if kind == 'rate' else (CONSUME_LUA, 1, 'otp', 'digest', 3)
    with pytest.raises(ConnectionError):
        asyncio.run(wire.eval(*args))


def test_wire_rejects_unrecognized_lua_instead_of_approximating_it():
    with pytest.raises(AssertionError):
        asyncio.run(WireMemory().eval('return {1}', 1, 'key', 60))


def test_wire_otp_wrong_code_preserves_expiry_and_success_consumes_once():
    from web.services.google_email_login import CONSUME_LUA
    wire = WireMemory()

    async def scenario():
        payload = json.dumps({'code_digest': 'correct', 'attempts': 0,
                              'payload': 'signed-payload', 'signature': 'signature'})
        assert await wire.set('otp', payload, ex=60, nx=True)
        wire.now = 10000
        assert await wire.eval(CONSUME_LUA, 1, 'otp', 'wrong', 3) == [0]
        assert wire.rows['otp'][1] == 60000
        assert await wire.eval(CONSUME_LUA, 1, 'otp', 'correct', 3) == [1, 'signed-payload', 'signature']
        assert await wire.eval(CONSUME_LUA, 1, 'otp', 'correct', 3) == [0]

    asyncio.run(scenario())
