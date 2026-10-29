"""Three reviewed public source locations; the historical V9 reader stays intact."""
from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import types
import zipfile
import zlib
from pathlib import Path, PurePosixPath

REGISTRY = 'tests/ci_web39/fixtures/secrets-public3-v1.zip'
REGISTRY_DIGEST = 'd14f0f4ccef03e341b1512d3dc20d93c32191139e63c4b057d25902c5b9b565e'
MEMBER = 'reviewed-public-locations.json'
LIMIT = 1024 * 1024
SCHEMA = 'current39-public-source-fingerprints-v1'
REASON = 'finite current39 review: exact public source fingerprint, not a credential'


def invalid():
    raise RuntimeError('Current39 reviewed source boundary is invalid; output withheld') from None


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            invalid()
        result[key] = value
    return result


def canonical(name):
    return (isinstance(name, str) and 0 < len(name) < 1024
            and not any(ord(c) < 32 for c in name) and ':' not in name and '\\' not in name
            and not PurePosixPath(name).is_absolute()
            and all(p not in {'', '.', '..'} for p in name.split('/')))


def source_path(root, name):
    if not canonical(name):
        invalid()
    root = Path(root).resolve(strict=True)
    path = root / name
    for current in (path, *path.parents):
        if current == root:
            break
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            invalid()
    if not path.resolve(strict=True).is_relative_to(root) or not path.is_file():
        invalid()
    return path


def is_digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def read_registry(root):
    """Authenticate bytes before bounded decompression and strict parsing."""
    try:
        path = source_path(root, REGISTRY)
        if path.stat().st_size > LIMIT:
            invalid()
        payload = path.read_bytes()
        if digest(payload) != REGISTRY_DIGEST:
            invalid()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            if len(members) != 1:
                invalid()
            member = members[0]
            if (member.filename != MEMBER or member.is_dir() or member.flag_bits & 1
                    or member.file_size > LIMIT or member.compress_size > LIMIT
                    or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}):
                invalid()
            raw = archive.read(member)
        if len(raw) > LIMIT:
            invalid()
        data = json.loads(raw.decode('utf8'), object_pairs_hook=unique,
                          parse_constant=lambda _: invalid())
        validate_registry(data)
        return data
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, UnicodeError,
            RecursionError, zipfile.BadZipFile, zlib.error, EOFError):
        invalid()


def validate_registry(data):
    fields = {'schema', 'version', 'config_digest', 'parent_registry_digest',
              'review_source_commit', 'parent_sources', 'files', 'provenance'}
    if (type(data) is not dict or set(data) != fields or data['schema'] != SCHEMA
            or data['version'] != '8.30.1' or not is_digest(data['config_digest'])
            or not is_digest(data['parent_registry_digest'])
            or re.fullmatch('[0-9a-f]{40}', str(data['review_source_commit'])) is None
            or type(data['parent_sources']) is not list or len(data['parent_sources']) != 4
            or type(data['files']) is not list or len(data['files']) != 3
            or type(data['provenance']) is not dict):
        invalid()
    names = set()
    for parent in data['parent_sources']:
        if (type(parent) is not dict or set(parent) != {'path', 'frames'}
                or not canonical(parent['path']) or parent['path'] in names
                or type(parent['frames']) is not list or not 0 < len(parent['frames']) <= 2):
            invalid()
        names.add(parent['path'])
        seen = set()
        for frame in parent['frames']:
            if (type(frame) is not dict or set(frame) != {'bytes', 'digest'}
                    or type(frame['bytes']) is not int or not 0 < frame['bytes'] <= LIMIT
                    or not is_digest(frame['digest']) or frame['digest'] in seen):
                invalid()
            seen.add(frame['digest'])
    if names != {'scripts/scan_secrets.py', 'scripts/reviewed_scan_locations.py',
                  'scripts/data/reviewed_scan_locations_v9.zip', '.gitleaks.toml'}:
        invalid()
    names = set()
    for record in data['files']:
        if (type(record) is not dict or set(record) != {'path', 'git_blob', 'frames'}
                or not canonical(record['path']) or record['path'] in names
                or re.fullmatch('[0-9a-f]{40}', str(record['git_blob'])) is None
                or type(record['frames']) is not list or len(record['frames']) != 2):
            invalid()
        names.add(record['path'])
        seen = set()
        for frame in record['frames']:
            if (type(frame) is not dict or set(frame) != {'source_bytes', 'source_digest',
                    'scanner_digest', 'source_encoding', 'line', 'line_digest', 'rule'}
                    or type(frame['source_bytes']) is not int or not 0 < frame['source_bytes'] <= LIMIT
                    or not is_digest(frame['source_digest']) or frame['source_digest'] in seen
                    or frame['scanner_digest'] != frame['source_digest']
                    or frame['source_encoding'] != 'utf-8' or type(frame['line']) is not int
                    or frame['line'] <= 0 or not is_digest(frame['line_digest'])
                    or frame['rule'] != 'generic-api-key'):
                invalid()
            seen.add(frame['source_digest'])
    if names != {'tests/ci_web39/new38_sources.py', 'tests/ci_web38/node-current38.json',
                  'tests/ci_web39/node-current39.json'}:
        invalid()


def authenticate_sources(root, document):
    result = {}
    for record in document['parent_sources']:
        path = source_path(root, record['path'])
        if path.stat().st_size not in {f['bytes'] for f in record['frames']}:
            invalid()
        raw = path.read_bytes()
        if not any(len(raw) == f['bytes'] and digest(raw) == f['digest'] for f in record['frames']):
            invalid()
        result[record['path']] = raw
    if (digest(result['.gitleaks.toml']) != document['config_digest']
            or digest(result['scripts/data/reviewed_scan_locations_v9.zip'])
            != document['parent_registry_digest']):
        invalid()
    return result


def authenticate_module(module, path, raw):
    """Compare live exports to authenticated source without changing modules."""
    if (type(module.__file__) is not str or module.__file__ != str(path)
            or type(module.__name__) is not str):
        invalid()
    expected = {'__name__': module.__name__, '__file__': str(path),
                '__package__': module.__package__}
    exec(compile(raw, str(path), 'exec'), expected)
    actual = vars(module)
    public = {k for k in expected if not k.startswith('__')}
    if {k for k in actual if not k.startswith('__')} != public:
        invalid()

    def function(a, b):
        if (not isinstance(a, types.FunctionType) or a.__code__ != b.__code__
                or any(type(value) is not str for value in (
                    a.__code__.co_filename, a.__name__, a.__qualname__, a.__module__))
                or a.__code__.co_filename != str(path)
                or a.__name__ != b.__name__ or a.__qualname__ != b.__qualname__
                or a.__module__ != b.__module__
                or a.__globals__ is not actual or a.__closure__ is not None):
            invalid()
        constant(a.__defaults__, b.__defaults__)
        constant(a.__kwdefaults__, b.__kwdefaults__)
        constant(a.__annotations__, b.__annotations__)

    def constant(a, b):
        if type(a) is not type(b):
            invalid()
        if type(b) in {str, int, bool, type(None)}:
            if a != b:
                invalid()
        elif type(b) is dict:
            if (any(type(k) is not str for k in a) or set(a) != set(b)):
                invalid()
            for key in b:
                constant(a[key], b[key])
        elif type(b) is tuple:
            if len(a) != len(b):
                invalid()
            for x, y in zip(a, b):
                constant(x, y)
        elif type(b) is frozenset:
            if any(type(v) is not str for v in a) or a != b:
                invalid()
        elif isinstance(b, Path):
            if str(a) != str(b):
                invalid()
        elif isinstance(b, re.Pattern):
            if a.pattern != b.pattern or a.flags != b.flags:
                invalid()
        elif a is not b:
            # Imported modules, functions, classes and future features use identity.
            invalid()

    for name in public:
        a, b = actual[name], expected[name]
        if isinstance(b, types.FunctionType) and b.__globals__ is expected:
            function(a, b)
        elif isinstance(b, type) and b.__module__ == module.__name__:
            if (type(a) is not type(b) or set(vars(a)) != set(vars(b))
                    or len(a.__bases__) != len(b.__bases__)
                    or any(x is not y for x, y in zip(a.__bases__, b.__bases__))):
                invalid()
            for key, value in vars(b).items():
                if isinstance(value, types.FunctionType):
                    function(vars(a)[key], value)
                elif key in {'__module__', '__qualname__', '__doc__'}:
                    constant(vars(a)[key], value)
        else:
            constant(a, b)


class CurrentLocations:
    def __init__(self, legacy, current):
        self.legacy = legacy
        self.current = current
        self.used = set()

    def classify(self, item, name):
        result = self.legacy.classify(item, name)
        if result is not None:
            return result
        result = self.current.classify(item, name)
        if result is None:
            return None
        location = (name, result['line'], result['rule'])
        if location in self.used:
            return None
        self.used.add(location)
        return result | {'reason': REASON}


def adapted_loader(root, document, review_module):
    def load(snapshot, source_hashes, version):
        # Original admission of V9, config and scanner version happens first.
        legacy = review_module.load_reviewed_locations(snapshot, source_hashes, version)
        authenticate_sources(snapshot, document)
        files = {}
        for record in document['files']:
            frame = next((f for f in record['frames']
                          if f['source_digest'] == source_hashes.get(record['path'])), None)
            if frame is not None:
                files[record['path']] = {'source_digest': frame['source_digest'],
                    'scanner_digest': frame['scanner_digest'],
                    'lines': {(frame['line'], frame['rule']): frame['line_digest']}}
        return CurrentLocations(legacy, review_module.ReviewedLocations(snapshot, source_hashes, files))
    return load
