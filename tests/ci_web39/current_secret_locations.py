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
CURRENT_REGISTRY = 'tests/ci_web39/fixtures/secrets-current4-v2.zip'
CURRENT_REGISTRY_DIGEST = 'd52ca65dc26f2bb979584bd9382ea833c815056847fddc64661e14d3e4fdcb91'
CURRENT_SCHEMA = 'current40-reviewed-four-locations-v2'
CURRENT_LOCATIONS = {
    'Dockerfile': (352,),
    'tests/e2e/mfa_account_ui_current.cjs': (26,),
    'tests/test_billing_email_verification.py': (140, 246),
}
CURRENT_REASON = 'finite current40 review: public build fingerprint or synthetic fixture; four exact locations'


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
    def __init__(self, legacy, current, reason=REASON):
        self.legacy = legacy
        self.current = current
        self.reason = reason
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
        return result | {'reason': self.reason}


def read_current_registry(root):
    """Read a separately pinned, bounded renewal; never alter the V9 or public3 data."""
    try:
        path = source_path(root, CURRENT_REGISTRY)
        if path.stat().st_size > LIMIT:
            invalid()
        payload = path.read_bytes()
        if digest(payload) != CURRENT_REGISTRY_DIGEST:
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
        validate_current_registry(data)
        return data
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, UnicodeError,
            RecursionError, zipfile.BadZipFile, zlib.error, EOFError):
        invalid()


def validate_current_registry(data):
    fields = {'schema', 'version', 'config_digest', 'parent_registry_digest',
              'legacy_extension_digest', 'review_source_commit', 'files', 'provenance'}
    if (type(data) is not dict or set(data) != fields or data['schema'] != CURRENT_SCHEMA
            or data['version'] != '8.30.1' or not is_digest(data['config_digest'])
            or not is_digest(data['parent_registry_digest'])
            or data['legacy_extension_digest'] != REGISTRY_DIGEST
            or re.fullmatch('[0-9a-f]{40}', str(data['review_source_commit'])) is None
            or type(data['files']) is not list or len(data['files']) != 3
            or type(data['provenance']) is not dict):
        invalid()
    names = set()
    for record in data['files']:
        if (type(record) is not dict or set(record) != {'path', 'git_blob', 'frames'}
                or record['path'] not in CURRENT_LOCATIONS or record['path'] in names
                or re.fullmatch('[0-9a-f]{40}', str(record['git_blob'])) is None
                or type(record['frames']) is not list or len(record['frames']) != 2):
            invalid()
        names.add(record['path'])
        seen = set()
        for frame in record['frames']:
            if (type(frame) is not dict or set(frame) != {'source_bytes', 'source_digest',
                    'scanner_digest', 'source_encoding', 'lines'}
                    or type(frame['source_bytes']) is not int or not 0 < frame['source_bytes'] <= LIMIT
                    or not is_digest(frame['source_digest']) or frame['source_digest'] in seen
                    or frame['scanner_digest'] != frame['source_digest']
                    or frame['source_encoding'] != 'utf-8' or type(frame['lines']) is not list
                    or len(frame['lines']) != len(CURRENT_LOCATIONS[record['path']])):
                invalid()
            seen.add(frame['source_digest'])
            lines = set()
            for line in frame['lines']:
                if (type(line) is not dict or set(line) != {'number', 'digest', 'rule'}
                        or type(line['number']) is not int
                        or line['number'] not in CURRENT_LOCATIONS[record['path']]
                        or line['number'] in lines or not is_digest(line['digest'])
                        or line['rule'] != 'generic-api-key'):
                    invalid()
                lines.add(line['number'])
    if names != set(CURRENT_LOCATIONS):
        invalid()


def adapted_loader(root, document, review_module, current_document=None, canonical_document=None):
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
        result = CurrentLocations(legacy, review_module.ReviewedLocations(snapshot, source_hashes, files))
        if current_document is None:
            if canonical_document is not None:
                invalid()
            return result
        # Authenticate the new registry again inside the immutable snapshot.
        if (read_current_registry(snapshot) != current_document
                or current_document['config_digest'] != document['config_digest']
                or current_document['parent_registry_digest'] != document['parent_registry_digest']
                or digest(source_path(snapshot, REGISTRY).read_bytes()) != REGISTRY_DIGEST):
            invalid()
        renewed = {}
        for record in current_document['files']:
            frame = next((f for f in record['frames']
                          if f['source_digest'] == source_hashes.get(record['path'])), None)
            if frame is not None:
                renewed[record['path']] = {'source_digest': frame['source_digest'],
                    'scanner_digest': frame['scanner_digest'],
                    'lines': {(line['number'], line['rule']): line['digest']
                              for line in frame['lines']}}
        result = CurrentLocations(result, review_module.ReviewedLocations(snapshot, source_hashes, renewed),
                                  CURRENT_REASON)
        if canonical_document is None:
            return result
        if (read_canonical_registry(snapshot) != canonical_document
                or canonical_document['config_digest'] != document['config_digest']
                or canonical_document['authority_digest'] != document['parent_registry_digest']):
            invalid()
        return CanonicalFrames(result, legacy, snapshot, source_hashes, canonical_document)
    return load


# Additional transport frames for previously approved V9 locations only.
# This does not modify the original V9 registry, reader or its decisions.
CANONICAL_REGISTRY = 'tests/ci_web39/fixtures/secrets-canonical2250-v1.zip'
CANONICAL_REGISTRY_DIGEST = '553f4db293f68231119c33f0e303ffd7ea7835e02d96c16573d41a2ac096707e'
CANONICAL_MEMBER = 'reviewed-canonical-frames.json'
CANONICAL_SCHEMA = 'current41-finite-canonical-V9-frames-v1'
CANONICAL_LIMIT = 4 * 1024 * 1024
CANONICAL_PARENT_DIGEST = 'dfa3fbfa3ff923a96cad28495bb76c46f17672fa62504af4ad53985d9a7060b4'
CANONICAL_REASON = 'finite canonical V9 framing: exact whole source, physical line and scanner span'


def canonical_span(item):
    fields = ('StartLine', 'EndLine', 'StartColumn', 'EndColumn')
    values = tuple(item.get(key) for key in fields)
    if (any(type(value) is not int or not 0 < value <= 2_000_000 for value in values)
            or values[0] != values[1] or values[2] > values[3]
            or not isinstance(item.get('RuleID'), str)
            or item['RuleID'] not in {'generic-api-key', 'sentry-access-token'}):
        return None
    return (*values, item['RuleID'])


def validate_canonical_registry(data):
    fields = {'schema', 'version', 'config_digest', 'authority_digest',
              'authority_source_commit', 'review_source_commit', 'files'}
    if (type(data) is not dict or set(data) != fields or data['schema'] != CANONICAL_SCHEMA
            or data['version'] != '8.30.1' or not is_digest(data['config_digest'])
            or data['authority_digest'] != CANONICAL_PARENT_DIGEST
            or data['authority_source_commit'] != 'fc7950ec341371b4354cba30ffd6c9a9860336fd'
            or data['review_source_commit'] != '2009fb8a0dd2e4a3865981088423ce7651efa9ea'
            or type(data['files']) is not list or len(data['files']) != 90):
        invalid()
    names = set()
    budgets = {'Git-LF': 0, 'approved-V9-CRLF': 0}
    for record in data['files']:
        if (type(record) is not dict or set(record) != {'path', 'git_blob',
                'authority_source_digest', 'authority_scanner_digest', 'frames'}
                or not canonical(record['path']) or record['path'] in names
                or re.fullmatch('[0-9a-f]{40}', str(record['git_blob'])) is None
                or not is_digest(record['authority_source_digest'])
                or not is_digest(record['authority_scanner_digest'])
                or type(record['frames']) is not list or len(record['frames']) != 2):
            invalid()
        names.add(record['path'])
        transports = set()
        digests = set()
        for frame in record['frames']:
            if (type(frame) is not dict or set(frame) != {'transport', 'source_bytes',
                    'source_digest', 'scanner_digest', 'source_encoding', 'findings'}
                    or not isinstance(frame['transport'], str)
                    or frame['transport'] not in budgets or frame['transport'] in transports
                    or type(frame['source_bytes']) is not int
                    or not 0 < frame['source_bytes'] <= 16 * 1024 * 1024
                    or not is_digest(frame['source_digest']) or frame['source_digest'] in digests
                    or frame['scanner_digest'] != frame['source_digest']
                    or frame['source_encoding'] != 'utf-8'
                    or type(frame['findings']) is not list or not frame['findings']):
                invalid()
            transports.add(frame['transport'])
            digests.add(frame['source_digest'])
            if (frame['transport'] == 'approved-V9-CRLF'
                    and (frame['source_digest'] != record['authority_source_digest']
                         or frame['scanner_digest'] != record['authority_scanner_digest'])):
                invalid()
            spans = set()
            for finding in frame['findings']:
                if (type(finding) is not dict or set(finding) != {'start_line', 'end_line',
                        'start_column', 'end_column', 'rule', 'line_digest', 'authority_line_digest'}
                        or not is_digest(finding['line_digest'])
                        or not is_digest(finding['authority_line_digest'])):
                    invalid()
                span = canonical_span({'StartLine': finding['start_line'], 'EndLine': finding['end_line'],
                    'StartColumn': finding['start_column'], 'EndColumn': finding['end_column'], 'RuleID': finding['rule']})
                if span is None or span in spans:
                    invalid()
                spans.add(span)
            budgets[frame['transport']] += len(spans)
    if budgets != {'Git-LF': 2250, 'approved-V9-CRLF': 2250}:
        invalid()


def read_canonical_registry(root):
    """Read a mandatory pinned finite bridge; no missing/tampered fallback."""
    try:
        path = source_path(root, CANONICAL_REGISTRY)
        if path.stat().st_size > CANONICAL_LIMIT:
            invalid()
        payload = path.read_bytes()
        if digest(payload) != CANONICAL_REGISTRY_DIGEST:
            invalid()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            if len(members) != 1:
                invalid()
            member = members[0]
            if (member.filename != CANONICAL_MEMBER or member.is_dir() or member.flag_bits & 1
                    or member.file_size > CANONICAL_LIMIT or member.compress_size > CANONICAL_LIMIT
                    or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}):
                invalid()
            raw = archive.read(member)
        if len(raw) > CANONICAL_LIMIT:
            invalid()
        data = json.loads(raw.decode('utf8'), object_pairs_hook=unique,
                          parse_constant=lambda _: invalid())
        validate_canonical_registry(data)
        return data
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, UnicodeError,
            RecursionError, zipfile.BadZipFile, zlib.error, EOFError):
        invalid()


class CanonicalFrames:
    """Exact authority for90 registered paths; unchanged delegation elsewhere."""

    def __init__(self, previous, authority, snapshot, source_hashes, document):
        validate_canonical_registry(document)
        self.previous = previous
        self.snapshot = Path(snapshot)
        self.source_hashes = source_hashes
        self.registered = {record['path'] for record in document['files']}
        self.files = {}
        self.checked = {}
        self.used = set()
        for record in document['files']:
            original = authority.files.get(record['path'])
            if (original is None or original['source_digest'] != record['authority_source_digest']
                    or original['scanner_digest'] != record['authority_scanner_digest']):
                invalid()
            for frame in record['frames']:
                for finding in frame['findings']:
                    if (original['lines'].get((finding['start_line'], finding['rule']))
                            != finding['authority_line_digest']):
                        invalid()
            chosen = next((frame for frame in record['frames']
                           if frame['source_digest'] == source_hashes.get(record['path'])), None)
            if chosen is not None:
                self.files[record['path']] = chosen

    def classify(self, item, name):
        if name not in self.registered:
            return self.previous.classify(item, name)
        # Registered paths have no legacy fallback: their explicit frame and
        # complete span own admission, including on Windows CRLF.
        frame = self.files.get(name)
        span = canonical_span(item)
        if (frame is None or span is None or self.source_hashes.get(name) != frame['source_digest']
                or (name, span) in self.used):
            return None
        finding = next((row for row in frame['findings'] if
            (row['start_line'], row['end_line'], row['start_column'], row['end_column'], row['rule']) == span), None)
        if finding is None:
            return None
        try:
            path = source_path(self.snapshot, name)
            info = path.stat()
            identity = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            if info.st_nlink != 1 or info.st_size != frame['source_bytes']:
                return None
            if name not in self.checked:
                content = path.read_bytes()
                content.decode('utf8', errors='strict')
                after = path.stat()
                after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                if digest(content) != frame['scanner_digest'] or identity != after_identity:
                    return None
                numbers = {row['start_line'] for row in frame['findings']}
                self.checked[name] = (identity, {
                    number: digest(line) for number, line in enumerate(content.split(b'\n'), 1)
                    if number in numbers})
            original_identity, lines = self.checked[name]
            if original_identity != identity or lines.get(span[0]) != finding['line_digest']:
                return None
        except (OSError, RuntimeError, UnicodeError):
            return None
        self.used.add((name, span))
        return {'file': name, 'line': span[0], 'rule': span[4], 'file_sha256': frame['source_digest'],
                'physical_line_sha256': finding['line_digest'], 'start_column': span[2],
                'end_column': span[3], 'reason': CANONICAL_REASON}
