from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import hashlib, json, re, urllib.request, zipfile

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
REPO = Path(r'F:\MetodoBaseWeb-image-security-20261019')
OUT = LAB / 'evidence/runtime28-native-20261019/pytest-tools'
OUT.mkdir(exist_ok=False)
TARGET = OUT / 'unpacked'
TARGET.mkdir()
lock = (REPO / 'requirements-test.lock').read_bytes()
text = lock.decode('utf-8')
rows = []
seen = set()
for name in ['pytest', 'iniconfig', 'packaging', 'pluggy', 'pygments']:
    match = re.search(r'(?m)^' + name + r'==([^\s]+)', text)
    assert match, name
    version = match.group(1)
    end = re.search(r'(?m)^[A-Za-z0-9_]', text[match.end():])
    block = text[match.start():match.end() + end.start()] if end else text[match.start():]
    pins = set(re.findall(r'--hash=sha256:([0-9a-f]{64})', block))
    url = f'https://pypi.org/pypi/{name}/{version}/json'
    request = urllib.request.Request(url, headers={'User-Agent': 'MetodoBase-local-QA/1'})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
        assert response.status == 200
    (OUT / f'{name}-{version}.pypi.json').write_bytes(raw)
    meta = json.loads(raw)
    wheels = [r for r in meta['urls'] if r['packagetype'] == 'bdist_wheel' and r['filename'].endswith('-py3-none-any.whl')]
    assert len(wheels) == 1, (name, len(wheels))
    wheel = wheels[0]
    assert wheel['digests']['sha256'] in pins, name
    assert wheel['url'].startswith('https://files.pythonhosted.org/')
    with urllib.request.urlopen(wheel['url'], timeout=90) as response:
        data = response.read()
    assert len(data) == wheel['size']
    assert hashlib.sha256(data).hexdigest() == wheel['digests']['sha256']
    path = OUT / wheel['filename']
    path.write_bytes(data)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        members = archive.infolist()
        names = [m.filename for m in members]
        assert len(names) == len(set(names)) == len({n.casefold() for n in names})
        for item in members:
            p = PurePosixPath(item.filename)
            assert not p.is_absolute() and '..' not in p.parts and '\\' not in item.filename and ':' not in item.filename
            assert not (item.external_attr >> 16) & 0o170000 == 0o120000
            assert all(not part.endswith(('.', ' ')) and not any(ord(c) < 32 for c in part) for part in p.parts)
            assert all(part.split('.')[0].casefold() not in {'con', 'prn', 'aux', 'nul', *('com'+str(i) for i in range(1,10)), *('lpt'+str(i) for i in range(1,10))} for part in p.parts)
            if item.is_dir():
                continue
            assert item.filename.casefold() not in seen
            seen.add(item.filename.casefold())
            target = TARGET / item.filename
            assert target.resolve().is_relative_to(TARGET.resolve()) and not target.exists()
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(archive.read(item))
    rows.append({'name': name, 'version': version, 'primary_metadata_url': url,
                 'metadata_sha256': hashlib.sha256(raw).hexdigest(), 'filename': path.name,
                 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                 'wheel_url': wheel['url'], 'hash_matches_existing_test_lock': True, 'crc_verified': True})
report = {'prepared_utc': datetime.now(timezone.utc).isoformat(),
          'source_commit': 'bc365c13b9af9e24129a56b4068059a67bb3afa0',
          'requirements_test_lock_sha256': hashlib.sha256(lock).hexdigest(),
          'packages': rows, 'unpacked_files': len(seen),
          'scope': 'Pure Python pytest tooling only, extracted into an owned lab directory. No install or dependency change in the product image or Windows environments. PyPI digests verified; no package signature claim.'}
(OUT / 'provenance.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
