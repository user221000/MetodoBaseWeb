"""Prepare a fresh independent broad run; never change the preserved red run."""
import hashlib
import json
from pathlib import Path
import re
import sys

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / 'qa-integrated28-history-landing-20261019'
OLD_HEAD = 'dd9877350aad3f483299c990a1e97aab63c83f5d'
OLD_PREFIX = 'qa-integrated28-history-landing'
NEW_PREFIX = 'qa-integrated28-history-landing-postfix'
PINS = {
    'review_integrated28.py': '4cd426570885a04139e8747c17bc93381a13c70ce403360a7ee96ffec93fad8f',
    'close_review.py': '6ca0e86c2b8fde1ba9751a3d81fd0848b09125e2fbe069ea283ec332fb5f0d3b',
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(name, value):
    with (OUT / name).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

head = sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}', head) and head != OLD_HEAD
proof = {'head': head, 'original_red_head': OLD_HEAD, 'adaptations': {}}
for name, pinned in PINS.items():
    original = (SOURCE / name).read_bytes()
    assert sha(original) == pinned
    text = original.decode('utf8')
    assert text.count(OLD_HEAD) == 1
    modified = text.replace(OLD_HEAD, head).replace(OLD_PREFIX, NEW_PREFIX)
    if name == 'review_integrated28.py':
        assert modified.count('HEADdd98773') == 1
        modified = modified.replace('HEADdd98773', 'HEAD' + head[:7])
        modified = modified.replace('metodobase-test-qa-integrated28-', 'metodobase-test-qa-integrated28-postfix-')
    else:
        anchor = "    'accepted': True, 'head': HEAD, 'product_parent': '6270658',"
        assert modified.count(anchor) == 1
        modified = modified.replace(anchor, anchor + "\n    'original_red_run': {'head': '" + OLD_HEAD + "', 'evidence': '../qa-integrated28-history-landing-20261019/serial-red-manifest.json', 'retained': True, 'not_counted_in_acceptance': True},")
    target = OUT / name
    with target.open('x', encoding='utf8', newline='\n') as stream:
        stream.write(modified)
    proof['adaptations'][name] = {
        'source_sha256': pinned, 'target_sha256': sha(target.read_bytes()),
        'changes': 'Frozen HEAD and fresh output/Temp prefix only; close summary also names immutable original red run. Selection, checks, skip policy and coverage thresholds unchanged.',
    }
save('runner-adaptation.json', proof)
print(json.dumps(proof, ensure_ascii=False))
