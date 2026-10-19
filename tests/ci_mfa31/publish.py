"""Publish explicit structural projections; raw logs and factors stay private.

This is an additional publication boundary, not the test acceptance parser.
Each input is a named regular file. ZIP members are expanded in memory under
strict size/path limits while scanning; no archive is extracted to a disk path.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.run_reviewed_ci30 import canonical_name, new_directory

# The product uses both two-part signed opaque values and three-part JWT/CSRF
# values. No scanner output includes a matched value or its surrounding line.
TOKEN = re.compile(rb'(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}(?:\.[A-Za-z0-9_-]{20,})?(?![A-Za-z0-9_-])')
CSRF = re.compile(rb'(?<![A-Za-z0-9_.-])[0-9]{9,13}\.[a-f0-9]{64}\.[a-f0-9]{64}(?![A-Za-z0-9_.-])')
FACTOR = re.compile(rb'(?i)(?:otpauth://|"(?:secret|recovery_codes|reauthentication_token|challenge|grant|refresh_token|access_token)"\s*:)')


def scan(raw: bytes, *, depth: int = 0) -> None:
    if len(raw) > 32 * 1024 * 1024 or TOKEN.search(raw) or CSRF.search(raw) or FACTOR.search(raw):
        raise ValueError('Private authentication material or oversized public input')
    if raw.startswith(b'PK\x03\x04') or zipfile.is_zipfile(io.BytesIO(raw)):
        if depth >= 2:
            raise ValueError('Nested archive limit exceeded')
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names, size = set(), 0
            for member in archive.infolist():
                name = canonical_name(member.filename.rstrip('/') if member.is_dir() else member.filename)
                kind = member.external_attr >> 16 & 0o170000
                if name.casefold() in names or member.flag_bits & 1 or kind not in {0, 0o100000, 0o040000}:
                    raise ValueError('Unsafe ZIP publication member')
                names.add(name.casefold())
                size += member.file_size
                if size > 32 * 1024 * 1024:
                    raise ValueError('Expanded ZIP publication limit exceeded')
                if not member.is_dir():
                    scan(archive.read(member), depth=depth + 1)


def xml_projection(raw: bytes) -> bytes:
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Unexpected XML declaration')
    source = ET.fromstring(raw)
    suites = [source] if source.tag == 'testsuite' else source.findall('testsuite')
    if source.tag not in {'testsuite', 'testsuites'} or not suites:
        raise ValueError('Expected JUnit report')
    root = ET.Element('testsuites')
    def public_identity(value, ordinal):
        try:
            scan(value.encode('utf8'))
            return value
        except ValueError:
            # A parametrized test can put a factor directly in its JUnit name.
            # Raw full-node gates run first. Public metadata retains status and
            # ordinal, while the raw report SHA binds the withheld identity.
            return 'private-parameter-withheld-' + str(ordinal)
    for original in suites:
        attributes = {key: original.get(key, '') for key in ('tests', 'failures', 'errors', 'skipped')}
        attributes['name'] = public_identity(original.get('name', ''), 0)
        suite = ET.SubElement(root, 'testsuite', attributes)
        for ordinal, item in enumerate(original.findall('testcase')):
            case = ET.SubElement(suite, 'testcase', {key: public_identity(item.get(key, ''), ordinal)
                                                   for key in ('classname', 'name')})
            for tag in ('failure', 'error', 'skipped'):
                if item.find(tag) is not None:
                    ET.SubElement(case, tag, {'message': 'Private diagnostics withheld'})
    return ET.tostring(root, encoding='utf8', xml_declaration=True)


def json_projection(raw: bytes) -> bytes:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('A named JSON report must be an object')
    result = {'raw_sha256': hashlib.sha256(raw).hexdigest(), 'projection': 'Counters only; private raw remains on runner'}
    for key in ('passed', 'total', 'expected_total', 'complete', 'completed', 'database_absent', 'listener_closed'):
        if key in value and type(value[key]) in {int, bool}:
            result[key] = value[key]
    for key in ('checks', 'results', 'screens', 'pageErrors', 'page_errors', 'report'):
        if isinstance(value.get(key), list):
            result[key + '_count'] = len(value[key])
            if all(isinstance(row, dict) and type(row.get('passed')) is bool for row in value[key]):
                result[key + '_passed'] = sum(row['passed'] for row in value[key])
    if len(result) == 2:
        raise ValueError('Report has no supported public counters')
    return (json.dumps(result, indent=2) + '\n').encode('utf8')


def publish(directory: Path, output: Path, names: list[str]) -> list[dict]:
    if not names or len(names) != len(set(name.casefold() for name in names)):
        raise ValueError('Publication requires an explicit distinct allowlist')
    checked = []
    for name in names:
        canonical_name(name)
        source = directory / name
        if not source.is_file() or source.is_symlink() or source.resolve() != source.absolute():
            raise ValueError('Publication input is missing, special or aliased')
        raw = source.read_bytes()
        # Raw XML/JSON can contain failed assertion diagnostics. The projection
        # removes those before scanning. ZIP publication itself is scanned raw.
        if name in {'coverage.xml', 'coverage.json'}:
            # Coverage contains source filenames/line counters, not assertion
            # diagnostics. Preserve the actual metrics and scan the full bytes.
            projected = raw
        elif name.endswith('.xml'):
            projected = xml_projection(raw)
        elif name.endswith('.json'):
            projected = json_projection(raw)
        elif name.endswith('.zip'):
            projected = raw
        else:
            raise ValueError('No reviewed projection for this file type')
        scan(projected)
        checked.append((name, raw, projected))
    if output.is_relative_to(directory):
        raise ValueError('Public output must be separate from private inputs')
    output = new_directory(output)
    manifest = []
    for name, raw, projected in checked:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(projected)
        manifest.append({'path': name, 'raw_sha256': hashlib.sha256(raw).hexdigest(),
                         'public_sha256': hashlib.sha256(projected).hexdigest(), 'bytes': len(projected)})
    (output / 'publication.json').write_bytes((json.dumps({'files': manifest, 'private_raw_uploaded': False,
        'token_two_and_three_parts_scanned': True, 'nested_zip_members_scanned': True}, indent=2) + '\n').encode())
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--files', required=True, nargs='+')
    args = parser.parse_args()
    try:
        files = publish(args.directory.absolute(), args.output.absolute(), args.files)
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile):
        parser.exit(1, 'Public artifact projection failed; diagnostics and authentication values withheld\n')
    print(json.dumps({'public_files': len(files), 'private_raw_uploaded': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
