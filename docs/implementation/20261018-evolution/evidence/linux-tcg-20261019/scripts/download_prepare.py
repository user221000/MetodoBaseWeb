from pathlib import Path
from datetime import datetime, timezone
import concurrent.futures, hashlib, json, os, re, urllib.request, time

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
JOBS = [
    ('qemu-w64-setup-20260811.exe', 'https://qemu.weilnetz.de/w64/qemu-w64-setup-20260811.exe',
     '5bcf9eed634e8575a37b74f445af41a2fe4106da512d0c30c368301d4c105037fdfab40a5287367a28a957624cddebbc8c07e16c88ab6634f554cdf3d16bf543'),
    ('debian-12-genericcloud-amd64-20261006-2623.qcow2',
     'https://cloud.debian.org/images/cloud/bookworm/20261006-2623/debian-12-genericcloud-amd64-20261006-2623.qcow2',
     'a09170d17e13af43da61774666f520e3bbec0f8bd96b4db37c15f3426fb327ccad950b80dbe78c09aa5ca90ce5015e99334b0ba5188fd4018736bc3fb5f0882c'),
]

def check_root():
    assert LAB.resolve() == LAB and LAB.is_dir()
    for p in (LAB, *LAB.parents):
        assert not p.is_symlink() and not (getattr(p.lstat(), 'st_file_attributes', 0) & 0x400), str(p)

def download(job):
    name, url, expected = job
    check_root()
    target = LAB / 'downloads' / name
    partial = target.with_suffix(target.suffix + '.partial')
    assert not target.exists() and not partial.exists(), str(target)
    start = time.monotonic()
    h512 = hashlib.sha512(); h256 = hashlib.sha256(); size = 0
    with urllib.request.urlopen(url, timeout=60) as response, partial.open('xb') as output:
        length = int(response.headers.get('Content-Length', '0'))
        final_url = response.url
        assert final_url.startswith('https://') and 0 < length < 1024**3
        while block := response.read(1024*1024):
            output.write(block); h512.update(block); h256.update(block); size += len(block)
            assert size <= length
            if size % (32*1024*1024) == 0:
                print(json.dumps({'download': name, 'bytes': size, 'expected_bytes': length}), flush=True)
    assert size == length and h512.hexdigest() == expected, name
    partial.rename(target)
    record = {'file': str(target), 'url': url, 'resolved_https_url': final_url, 'bytes': size,
              'sha512': h512.hexdigest(), 'expected_sha512': expected, 'sha256': h256.hexdigest(),
              'digest_matches_primary': True, 'seconds': round(time.monotonic()-start, 3)}
    (LAB/'evidence'/(name+'.download.json')).write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record), flush=True)
    return record

if __name__ == '__main__':
    check_root()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(download, JOBS))
    report = {'finished_utc': datetime.now(timezone.utc).isoformat(), 'files': results,
              'scope': 'Downloads only; neither installer nor downloaded tools executed.'}
    (LAB/'evidence/linux-tcg-downloads.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
