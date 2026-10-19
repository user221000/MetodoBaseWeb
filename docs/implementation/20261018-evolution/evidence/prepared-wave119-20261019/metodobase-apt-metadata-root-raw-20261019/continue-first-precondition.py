"""Finish read-only provenance after correcting the base-versus-native package scope."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shlex
import sys

sys.dont_write_bytecode=True
lab=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-apt-metadata-root-raw-20261019')
assert out.is_dir() and not (out/'receipt.json').exists()
image=json.loads((out/'base-image.inspect.json').read_bytes())[0]
container=json.loads((out/'base-container.inspect.json').read_bytes())[0]
failed=json.loads((out/'failed-container.inspect.json').read_bytes())[0]
assert image['Id']==container['Image']=='sha256:df18428df8a0f9189c84e7424d214b4c50092af1f9dca5842a00c41c39bda316'
assert container['State']['Status']=='created' and container['State']['StartedAt'].startswith('0001-01-01')
assert not failed['State']['Running'] and failed['State']['ExitCode']==1
assert hashlib.sha256((out/'base-keyring.raw').read_bytes()).hexdigest()=='506b815cbb32d9b6066b4a2aa524071e071761e7e7f68c3ac74f3061ba852017'


def packages(path):
    rows={}
    for stanza in path.read_text(encoding='utf8').split('\n\n'):
        fields={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in stanza.splitlines() if ':' in line and not line.startswith((' ','\t'))}
        if not fields:
            continue
        assert fields['Status']=='install ok installed'
        name=fields['Package']+(':'+fields['Architecture'] if fields.get('Multi-Arch')=='same' else '')
        assert name not in rows
        rows[name]=fields['Version']
    return rows


original=packages(out/'base-dpkg-status.raw')
actual=packages(out/'failed-dpkg-status.raw')
before=dict(line.split('\t') for line in (out/'failed-native-before.tsv.raw').read_text(encoding='utf8').splitlines())
assert len(original)==len(actual)==len(before)==87 and actual==before
changes={name:{'base':original.get(name),'failed_native':actual.get(name)} for name in set(original)|set(actual) if original.get(name)!=actual.get(name)}
assert changes=={'liblzma5:amd64':{'base':'5.8.1-1','failed_native':'5.8.1-1+deb13u2'}},changes
spec=importlib.util.spec_from_file_location('owned_guest_access',lab/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)
result=access.run(shlex.join(['sudo','docker','image','inspect',failed['Image']]),timeout=40)
(out/'failed-parent-image.inspect.json').write_bytes(result.stdout)
(out/'failed-parent-image.inspect.json.stderr').write_bytes(result.stderr)
assert result.returncode==0
parent=json.loads(result.stdout)[0]
assert parent['Id']==failed['Image']
base_layers=image['RootFS']['Layers']
assert parent['RootFS']['Layers'][:len(base_layers)]==base_layers
(out/'continue.py').write_bytes(Path(__file__).read_bytes())
receipt={'role':'root independent read-only collector; D60 author is ops_deployment',
         'base_never_started_verified_from_raw':True,'failed_parent_extends_pinned_base_layers':True,
         'keyring_sha256':hashlib.sha256((out/'base-keyring.raw').read_bytes()).hexdigest(),
         'failed_native_before_vs_after_packages_exact':87,'original_base_to_failed_native_changes':changes,
         'first_guard_failure':'Original collector incorrectly required original public base dpkg/status bytes equal the native parent, despite the explicit liblzma security upgrade in Dockerfile. All7read-only captures completed before that final guard. Corrected scope compares native-before.tsv with actual native status:87identical. Original raw/driver retained.',
         'no_build_or_container_mutations':True,
         'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir()) if p.is_file()}}
(out/'root-readonly-receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps({'receipt':str(out/'root-readonly-receipt.json'),'packages_exact':87,'original_base_changes':changes,'parent_layer_prefix_exact':True,'base_never_started':True}))
