from pathlib import Path
import hashlib
import json
import subprocess

tmp = Path(r'C:\Users\Consu\AppData\Local\Temp')
root = Path(r'F:\mb-mfa31-compose-20261019')
original = tmp / 'metodobase-mfa-ui31-copy.py'
blob = original.read_bytes()
assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=root)
first = tmp / 'metodobase-mfa-ui31-copy-20261019'
assert {p.name for p in first.iterdir()} == {'driver.py'}
assert (first / 'driver.py').read_bytes() == blob
needle = b"    assert before == git('show', BASE + ':' + name)"
assert blob.count(needle) == 1
replacement = b"    assert git('hash-object', '--path=' + name, '--', name).strip() == git('rev-parse', BASE + ':' + name).strip()"
refined = blob.replace(needle, replacement).replace(b"metodobase-mfa-ui31-copy-20261019'", b"metodobase-mfa-ui31-copy-v2-20261019'")
assert refined.count(replacement) == 1 and needle not in refined
target = tmp / 'metodobase-mfa-ui31-copy-v2.py'
with target.open('xb') as output:
    output.write(refined)
receipt = {'first_driver_sha256': hashlib.sha256(blob).hexdigest(), 'refined_driver_sha256': hashlib.sha256(refined).hexdigest(),
           'cause': 'First driver required checkout bytes equal Git blob; Windows checkout is CRLF. It stopped on the first precondition before any source write. Refined guard compares filtered working object ID with the original Git blob; raw preimages and inverse byte proof remain byte exact, not normalized.',
           'source_clean_after_first': True, 'first_output_driver_only': True}
(first / 'precondition-cause.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps(receipt))
