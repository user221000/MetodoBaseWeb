"""Read only the exact preserved local image/containers for independent provenance review."""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import shlex
import sys
import tarfile

sys.dont_write_bytecode=True
lab=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-apt-metadata-root-raw-20261019')
base='399a539cec64b995e2f41e1cd810f3d345c72263ca8e0e84a5924391f2bce9b7'
failed='7cbc85823cbad56b4e4b6d0f53342a53b605149639e9dfa3fb930477dc5d9cd5'
reference='python@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe'
spec=importlib.util.spec_from_file_location('owned_guest_access',lab/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)
out.mkdir(exist_ok=False)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
commands=[
 ('base-image.inspect.json',['sudo','docker','image','inspect',reference]),
 ('base-container.inspect.json',['sudo','docker','inspect','--type','container',base]),
 ('failed-container.inspect.json',['sudo','docker','inspect','--type','container',failed]),
 ('base-keyring.tar',['sudo','docker','cp','-L',base+':/usr/share/keyrings/debian-archive-keyring.gpg','-']),
 ('base-dpkg-status.tar',['sudo','docker','cp','-L',base+':/var/lib/dpkg/status','-']),
 ('failed-dpkg-status.tar',['sudo','docker','cp','-L',failed+':/var/lib/dpkg/status','-']),
 ('failed-native-before.tsv.tar',['sudo','docker','cp','-L',failed+':/usr/local/share/metodobase/native-runtime/before.tsv','-']),
]
records={}
for name,args in commands:
    result=access.run(shlex.join(args),timeout=40)
    (out/name).write_bytes(result.stdout)
    (out/(name+'.stderr')).write_bytes(result.stderr)
    records[name]={'exit':result.returncode,'bytes':len(result.stdout),'sha256':hashlib.sha256(result.stdout).hexdigest()}
    assert result.returncode==0,name
image=json.loads((out/'base-image.inspect.json').read_bytes())
container=json.loads((out/'base-container.inspect.json').read_bytes())
failure=json.loads((out/'failed-container.inspect.json').read_bytes())
assert len(image)==len(container)==len(failure)==1
assert image[0]['Id']=='sha256:df18428df8a0f9189c84e7424d214b4c50092af1f9dca5842a00c41c39bda316'
assert reference in image[0]['RepoDigests']
assert container[0]['Id']==base and container[0]['Image']==image[0]['Id']
assert container[0]['State']['Status']=='created' and not container[0]['State']['Running']
assert container[0]['State']['StartedAt'].startswith('0001-01-01')
assert failure[0]['Id']==failed and not failure[0]['State']['Running'] and failure[0]['State']['ExitCode']==1
tar_members={}
for name in ['base-keyring.tar','base-dpkg-status.tar','failed-dpkg-status.tar','failed-native-before.tsv.tar']:
    with tarfile.open(fileobj=io.BytesIO((out/name).read_bytes())) as archive:
        members=archive.getmembers()
        assert len(members)==1 and members[0].isfile() and members[0].size<1_000_000
        data=archive.extractfile(members[0]).read()
        extracted=name.removesuffix('.tar')+'.raw'
        (out/extracted).write_bytes(data)
        tar_members[name]={'member':members[0].name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'raw_file':extracted}
assert tar_members['base-keyring.tar']['sha256']=='506b815cbb32d9b6066b4a2aa524071e071761e7e7f68c3ac74f3061ba852017'
assert (out/'base-dpkg-status.raw').read_bytes()==(out/'failed-dpkg-status.raw').read_bytes()
receipt={'role':'root independent read-only collector, not author of D60', 'base_container':base,'failed_container':failed,'immutable_base_reference':reference,
         'base_never_started_verified_from_raw':True,'base_image_id':image[0]['Id'],'base_vs_failed_dpkg_status_bytes_identical':True,
         'commands':records,'tar_members':tar_members,
         'scope':'Only inspect/cp of exact already preserved owned image and stopped containers. No Docker pull/build/create/start/remove, VM lifecycle, host/global keyring, PG, Chrome, provider or production operations. RAW private for independent security review; no final artifact acceptance.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps({'receipt':str(out/'receipt.json'),'commands':len(records),'all_exit0':True,'keyring_sha256':tar_members['base-keyring.tar']['sha256'],
                  'base_never_started':True,'base_and_failed_dpkg_bytes_identical':True}))
