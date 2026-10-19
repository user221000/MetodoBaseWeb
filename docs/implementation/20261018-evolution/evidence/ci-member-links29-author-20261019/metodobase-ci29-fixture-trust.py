"""Bind current marker fixtures to the reviewed source, including pair tampering."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
root=Path('F:/mb-r12-ci29-20261019')
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-fixture-trust-20261019');out.mkdir(exist_ok=False)
sha=lambda value:hashlib.sha256(value).hexdigest()
baseline=root/'tests/ci_member_links29/baseline.json';verifier=root/'tests/verify_member_links_ci.py'
old_baseline=baseline.read_bytes();old_verifier=verifier.read_bytes()
(out/'baseline-before.json').write_bytes(old_baseline);(out/'verifier-before.py').write_bytes(old_verifier)
data=json.loads(old_baseline)
fixtures=['tests/e2e/personal_diary_server.py','tests/e2e/personal_history_server.py','tests/e2e/landing_server.py']
for name in fixtures:
    raw=(root/name).read_bytes().replace(b'\r\n',b'\n')
    assert raw==subprocess.check_output(['git','show',data['commit']+':'+name],cwd=root)
    assert name not in data['unchanged_files'];data['unchanged_files'][name]=sha(raw)
new_baseline=(json.dumps(data,indent=2)+'\n').encode();new_sha=sha(new_baseline)
needle="BASELINE_SHA = '"+sha(old_baseline)+"'";replacement="BASELINE_SHA = '"+new_sha+"'"
assert old_verifier.decode().count(needle)==1
new_verifier=old_verifier.decode().replace(needle,replacement).encode()
assert new_verifier.decode().replace(replacement,needle).encode()==old_verifier
baseline.write_bytes(new_baseline);verifier.write_bytes(new_verifier)
shadow=out/'owned-shadow';shadow.mkdir()
paths=['tests/ci_member_links29/baseline.json','tests/ci_member_links29/ci28-before.yml',*data['unchanged_files']]
for name in paths:
    target=shadow/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,target)
spec=importlib.util.spec_from_file_location('ci29_fixture_trust',verifier);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.ROOT=shadow;module.SNAPSHOT=shadow/'tests/ci_member_links29'
module.baseline();rows=[{'case':'unchanged-shadow','accepted':True}]
for name in fixtures:
    path=shadow/name;original=path.read_bytes();path.write_bytes(original+b'\nCI29_UNAUTHORIZED_FIXTURE_SENTINEL = True\n')
    for pair in [False,True]:
        if pair:
            changed=json.loads(new_baseline);changed['unchanged_files'][name]=sha(path.read_bytes().replace(b'\r\n',b'\n'))
            (shadow/'tests/ci_member_links29/baseline.json').write_bytes((json.dumps(changed,indent=2)+'\n').encode())
        try:module.baseline()
        except AssertionError:rows.append({'fixture':name,'pair_metadata_changed':pair,'rejected':True})
        else:raise AssertionError('Changed fixture trust anchor accepted')
        (shadow/'tests/ci_member_links29/baseline.json').write_bytes(new_baseline)
    path.write_bytes(original)
assert baseline.read_bytes()==new_baseline and verifier.read_bytes()==new_verifier
(out/'review.json').write_bytes((json.dumps({'baseline_sha256':new_sha,'three_fixtures_exact_pinned_source':True,
    'only_verifier_change':'BASELINE_SHA literal; all guard behavior and assertions byte unchanged','cases':rows},indent=2)+'\n').encode())
print(json.dumps({'baseline_sha256':new_sha,'trust_canaries':len(rows),'negative_rejected':6}))
