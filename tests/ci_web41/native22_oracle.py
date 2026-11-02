"""Current41 inputs for three explicitly historical native-source oracles.

Only five named source reads may expose authenticated retained native11 RAW.
The current provider subject source is pinned separately and is never called
identical to its old body. No fixture, service admission or global module is
patched. The original source assertions and their function code stay intact.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import stat
import sys
from types import CodeType, FunctionType, ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCOPE = 'historical native22/retained11 source assertions only; current provider behavior is separate'
ORIGINAL = 'tests/ci_web37/native22_frames.py'
REPLAY = 'tests/ci_web37/replay.py'
PROVIDER = 'tests/integration_provider_subjects.py'
ORACLE = 'tests/test_current37_native_original22.py'
NATIVE_CONTROLS = 'tests/test_ci_web37_native22_frames.py'
REPLAY_CONTROLS = 'tests/test_ci_web37_replay_frames.py'
CONSUMERS = frozenset({ORACLE, NATIVE_CONTROLS, REPLAY_CONTROLS})
HOST_NAMES = frozenset({PROVIDER, 'tests/account_security37_owned.py',
    'tests/e2e/browser_native_session31.cjs', 'tests/integration_schema_migrations.py',
    'tests/e2e/browser_compat31.cjs'})
PROVIDER_FRAMES = frozenset({
    (10350, '6a9657cc32bc044a5c3cd6e0a4bfd0d6c678f0d874b3559f4dd6504b41345ccf'),
    (10529, 'f7f93d98a9fe112722e24ef0a90cd241ee8955a8bdd594d0123bd64cab215a19')})
SOURCE_FRAMES = {'tests/ci_web37/native22_frames.py': ((6126,
                                        '108cd30a94aca2f1292b8762b36356c9c67751d1a0ee3eaeb10f63c4b33a4593'),
                                       (6247,
                                        '8a5defc43fac91eb3c1b544cf39c891a748665827bb5ab93fcecc762e9dc27f3')),
 'tests/ci_web37/replay.py': ((10360, '3727a9a59b8f1f14306e82c3dd2985eef6992fba150e1e7995cb28271b3d0821'),
                              (10532, '58a898fb1ed607c12dafe3f12a984b9e88fdd18a07362d1258b66e0eacd1853a')),
 'tests/test_ci_web37_native22_frames.py': ((4639,
                                             '2975418d3fe294ba7f9f03cd6d90736819d06063261ba051e7aac4283e6c987a'),
                                            (4756,
                                             '34c72fc764f5aba28de6e0ab6b754ab95b29103c23e138518b2f69d0274d5051')),
 'tests/test_ci_web37_replay_frames.py': ((3677,
                                           'e3f783ee2470d58849cf5ba75a76ee59816e0259137e2e913e30a1f6376844ce'),
                                          (3762,
                                           '16d8c0e553e3c298cffba1e7f4b652caba5fb62a0f205396642cc039f17eee0d')),
 'tests/test_current37_native_original22.py': ((159,
                                                'f3438b3836a3e3c90ebaa222586bee2125fbca83c51d24521f526d74506b4ce1'),
                                               (163,
                                                '3a1d90d0f65758d304a706006a92f374c21bd5b8eccf617f2d766ab564eae4fd'))}
HOST_FRAMES = {'tests/account_security37_owned.py': ((5753,
                                        'a6548646a61c916dc9543720061df21765df15b0de49ae781ecbd8fff992ebf4'),
                                       (5859,
                                        '603febc40de96137e19e6de6affb64bccc898a2cbde1d8b7be841203934d2a2e')),
 'tests/e2e/browser_compat31.cjs': ((16015,
                                     '445853dabbd4d6c41c6d84b4eb38b455b93dffe00e7aafdc9a87d0d8d00c2d14'),
                                    (16136,
                                     '99b08d68b5ac886f2828508fba093489407e0f47ba2b73cf4e5d0628d95b265e')),
 'tests/e2e/browser_native_session31.cjs': ((7246,
                                             '3b1ae4ff8e934f15ac09d14ecac70de58cc37672c9ae6a71d2be769c2ae4d924'),
                                            (7316,
                                             '8e94959897264123b09d949a6d3e97266ecaf6cf2069ce0184f12fde7a4e5e01')),
 'tests/integration_provider_subjects.py': ((10350,
                                             '6a9657cc32bc044a5c3cd6e0a4bfd0d6c678f0d874b3559f4dd6504b41345ccf'),
                                            (10529,
                                             'f7f93d98a9fe112722e24ef0a90cd241ee8955a8bdd594d0123bd64cab215a19')),
 'tests/integration_schema_migrations.py': ((15414,
                                             'fd36441ac63e20a859c405138dd6c854240836c81ca6690de9039889f3545dae'),
                                            (15693,
                                             '419c0e07826f42501b801a5ab3cdf9798ef0955fc1db6ab4b5e13e0c6deb2a7d'))}
ORIGINAL_FRAMES = {'tests/account_security37_owned.py': (5859,
                                       '603febc40de96137e19e6de6affb64bccc898a2cbde1d8b7be841203934d2a2e'),
 'tests/e2e/browser_compat31.cjs': (16136,
                                    '99b08d68b5ac886f2828508fba093489407e0f47ba2b73cf4e5d0628d95b265e'),
 'tests/e2e/browser_native_session31.cjs': (7316,
                                            '8e94959897264123b09d949a6d3e97266ecaf6cf2069ce0184f12fde7a4e5e01'),
 'tests/integration_provider_subjects.py': (10188,
                                            '7342bbb301418fa14b99c461a748e7909aa7baa8c123b63d6bb2377c7bb104b1'),
 'tests/integration_schema_migrations.py': (15693,
                                            '419c0e07826f42501b801a5ab3cdf9798ef0955fc1db6ab4b5e13e0c6deb2a7d')}
ORACLE_REWRITTEN_SHA256 = '4668bbca0d8e88c6429e940c38afae429982be82308694711b633db40055dd65'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def plain(root, name):
    if type(name) is not str or name.startswith('/') or '\\' in name or ':' in name or any(
            part in {'', '.', '..'} for part in name.split('/')):
        raise ValueError('A native41 source name is not exact')
    root = Path(root)
    if root.resolve(strict=True) != root.absolute():
        raise ValueError('A native41 source root became an alias')
    root = root.resolve(strict=True)
    path = root / name
    for item in (path, *path.parents):
        info = item.lstat()
        if item.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('A native41 source became an alias')
        if item == root:
            break
    before = path.stat()
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or not 0 < before.st_size < 128 * 1024):
        raise ValueError('A bounded native41 source is required')
    raw = path.read_bytes()
    after = path.stat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if identity(before) != identity(after) or len(raw) != before.st_size:
        raise ValueError('A native41 source changed during read')
    return raw


def source(name):
    if type(name) is not str or name not in SOURCE_FRAMES:
        raise ValueError('Only explicit native41 source identities may be read')
    raw = plain(ROOT, name)
    if (len(raw), digest(raw)) not in SOURCE_FRAMES.get(name, ()):
        raise ValueError('A complete native41 historical consumer source differs')
    return raw


def authorities():
    from tests.ci_web37 import native22_frames, replay
    for name, module in ((ORIGINAL, native22_frames), (REPLAY, replay)):
        raw = source(name)
        if Path(module.__file__) != ROOT / name or module.ROOT != ROOT:
            raise ValueError('A native41 authority module differs')
        function_name = 'export' if name == ORIGINAL else 'retained_native11'
        function = getattr(module, function_name)
        reference = next(item for item in compile(raw, str(ROOT / name), 'exec', dont_inherit=True).co_consts
                         if isinstance(item, CodeType) and item.co_name == function_name)
        if (not isinstance(function, FunctionType) or function.__globals__ is not vars(module)
                or function.__code__ != reference):
            raise ValueError('A native41 authority callable differs')
    proof = native22_frames.OriginalFrames()
    retained = replay.retained_native11()
    if (set(HOST_FRAMES) != HOST_NAMES or set(ORIGINAL_FRAMES) != HOST_NAMES
            or set(HOST_FRAMES[PROVIDER]) != PROVIDER_FRAMES
            or set(retained) != set(replay.NATIVE11_GIT_LF)
            or set(retained) - set(native22_frames.ADDITIONAL_NAMES) != HOST_NAMES):
        raise ValueError('The exact five historical host paths differ')
    for name, (size, pin) in ORIGINAL_FRAMES.items():
        record = proof.manifest['helper_union'][name]
        if (record['bytes'], record['raw_sha256']) != (size, pin) or (len(retained[name]), digest(retained[name])) != (size, pin):
            raise ValueError('The fixed five original source identities differ')
    return native22_frames, replay, proof, retained


class _HistoricalRead:
    def __init__(self, root, name, replay, proof, retained):
        self.root, self.name, self.replay = root, name, replay
        self.proof, self.retained = proof, retained

    def read_bytes(self):
        if self.name not in HOST_NAMES:
            raise ValueError('Only five exact source reads have a historical view')
        observed = plain(self.root, self.name)
        original = self.retained.get(self.name)
        size, pin = ORIGINAL_FRAMES[self.name]
        if type(original) is not bytes or len(original) != size or digest(original) != pin:
            raise ValueError('The retained original source differs')
        allowed = HOST_FRAMES[self.name]
        if (len(observed), digest(observed)) not in allowed:
            raise ValueError('The exact current native41 host source differs')
        return original


class HistoricalRoot:
    def __init__(self, root, replay, proof, retained):
        self.root, self.replay, self.proof, self.retained = Path(root), replay, proof, retained

    def __truediv__(self, name):
        if type(name) is str and name in HOST_NAMES:
            return _HistoricalRead(self.root, name, self.replay, self.proof, self.retained)
        return self.root / name


def historical_root(root):
    _, replay, proof, retained = authorities()
    return HistoricalRoot(root, replay, proof, retained)


def export(root=None):
    original, replay, proof, retained = authorities()
    root = ROOT if root is None else Path(root)
    namespace = dict(vars(original), ROOT=HistoricalRoot(root, replay, proof, retained))
    function = FunctionType(original.export.__code__, namespace, original.export.__name__,
                            original.export.__defaults__, original.export.__closure__)
    function.__kwdefaults__ = original.export.__kwdefaults__
    return function()


class _SubjectView:
    def __init__(self):
        self.ROOT = ROOT

    def export(self):
        return export(self.ROOT)

    def __getattr__(self, name):
        if name not in {'NAMES', 'MANIFEST', 'FIXTURES', 'TEST_NAME', 'OriginalFrames'}:
            raise AttributeError('An unreviewed native22 subject attribute was requested')
        original, _, _, _ = authorities()
        return getattr(original, name)


class _ReplayView:
    def __init__(self):
        self.ROOT = historical_root(ROOT)

    def __getattr__(self, name):
        if name not in {'NATIVE11_GIT_LF', 'retained_native11', 'original_native_helper'}:
            raise AttributeError('An unreviewed retained11 replay attribute was requested')
        _, replay, _, _ = authorities()
        return getattr(replay, name)


def _clone(original, path, replacement, raw, config):
    name = path.relative_to(ROOT).as_posix()
    expected_name = name.removesuffix('.py').replace('/', '.')
    if (original.__name__ != expected_name or Path(original.__file__) != path
            or sys.modules.get(expected_name) is not original
            or name not in {NATIVE_CONTROLS, REPLAY_CONTROLS}):
        raise ValueError('Only exact native41 historical control modules may be cloned')
    # Pytest's actual imported test functions contain its ordinary rewritten
    # assertions. Authenticate the identical official rewrite with the same
    # active configuration; never substitute a different assertion body.
    from _pytest.assertion.rewrite import _rewrite_test
    _, reference_code = _rewrite_test(path, config)
    if source(name) != raw:
        raise ValueError('A historical consumer changed during its official assertion rewrite')
    compiled = {item.co_name: item for item in reference_code.co_consts
                if isinstance(item, CodeType)}
    companion = ModuleType(original.__name__)
    companion.__dict__.update(vars(original))
    attribute = 'subject' if name == NATIVE_CONTROLS else 'replay'
    companion.__dict__[attribute] = replacement
    if any(key.startswith('test_') and key not in compiled for key in vars(original)):
        raise ValueError('An unreviewed historical assertion was added')
    for key, reference in compiled.items():
        value = getattr(original, key, None)
        if (not isinstance(value, FunctionType) or value.__module__ != original.__name__
                or value.__code__ != reference):
            raise ValueError('An original historical assertion callable differs')
        copied = FunctionType(value.__code__, vars(companion), value.__name__, value.__defaults__, value.__closure__)
        copied.__kwdefaults__, copied.__qualname__ = value.__kwdefaults__, value.__qualname__
        copied.__dict__.update(value.__dict__)
        copied.__annotations__ = value.__annotations__.copy()
        companion.__dict__[key] = copied
    companion.__current41_historical_scope__ = SCOPE
    return companion


class Current41HistoricalModule(pytest.Module):
    def _getobj(self):
        path = Path(self.path)
        name = path.relative_to(ROOT).as_posix()
        raw = source(name)
        if name == ORACLE:
            text = raw.replace(b'\r\n', b'\n')
            old = b'from tests.ci_web37.native22_frames import export'
            if text.count(old) != 1:
                raise ValueError('The exact native22 consumer import differs')
            rewritten = text.replace(old, b'from tests.ci_web41.native22_oracle import export')
            if digest(rewritten) != ORACLE_REWRITTEN_SHA256:
                raise ValueError('The complete current41 oracle consumer source differs')
            module = ModuleType(name.removesuffix('.py').replace('/', '.'))
            module.__file__, module.__package__ = str(path), 'tests'
            exec(compile(rewritten, str(path), 'exec', dont_inherit=True), vars(module))
            module.__current41_historical_scope__ = SCOPE
            return module
        original = super()._getobj()
        if name == NATIVE_CONTROLS:
            return _clone(original, path, _SubjectView(), raw, self.config)
        if name == REPLAY_CONTROLS:
            return _clone(original, path, _ReplayView(), raw, self.config)
        raise ValueError('An unreviewed native41 historical consumer was requested')


def consumer_module(path, parent):
    path = Path(path)
    if path.resolve(strict=True) != path.absolute() or not path.is_relative_to(ROOT):
        raise ValueError('An actual native41 historical consumer path is required')
    name = path.relative_to(ROOT).as_posix()
    if name not in CONSUMERS:
        raise ValueError('Only three explicit historical source consumers are admitted')
    source(name)
    return Current41HistoricalModule.from_parent(parent, path=path)
