from pathlib import Path
import hashlib, importlib.util, io, json, shlex, tarfile

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE=LAB/'evidence/runtime28-native-20261019'
OUT=BASE/'runtime'
OUT.mkdir(exist_ok=False)
original=(BASE/'scripts/private_stdin_entrypoint.py').read_bytes()
assert hashlib.sha256(original).hexdigest()=='12003f93c40840ea092eab29f837b77caa5cba969cb20d1a47b720045d139df6'
text=original.decode().replace('import argparse, json, os, re, sys','import argparse, json, os, re, struct, sys')
old="raw = sys.stdin.buffer.read(65537)\nassert len(raw) <= 65536, 'Private bootstrap frame too large'"
new="header = sys.stdin.buffer.read(4)\nassert len(header) == 4, 'Private frame header incomplete'\nsize = struct.unpack('!I', header)[0]\nassert 1 <= size <= 65536, 'Private bootstrap frame too large'\nraw = sys.stdin.buffer.read(size)\nassert len(raw) == size, 'Private frame incomplete'"
assert text.count(old)==1
text=text.replace(old,new)
assert "PORT='8000'," in text
text=text.replace("PORT='8000',", "PORT='8000', WEB_WORKERS='2',")
compile(text,'private-stdin-entrypoint-v2','exec')
target=BASE/'scripts/private_stdin_entrypoint_v2.py'
with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
members={'helpers/private_stdin_entrypoint_v2.py':target.read_bytes(),
         'helpers/attest_web_process.py':(BASE/'scripts/attest_web_process.py').read_bytes(),
         'runtime_guest_control.py':(BASE/'scripts/runtime_guest_control.py').read_bytes(),
         'network_canary.py':(BASE/'scripts/network_canary.py').read_bytes()}
for name,data in members.items():compile(data,name,'exec')
context=json.loads((LAB/'evidence/recovery28-image-bc365c1/context-files.json').read_text())
source_names=['entrypoint.sh','db_bootstrap.py','web/main_web.py','config/settings.py','web/database/schema_control.py',
              'web/database/tenant_policy.py','web/database/alembic/versions/20261019_account_recovery.py']
source_pins={'/app/'+name:context[name]['sha256'] for name in source_names}
gate=BASE/'network-retry-v3-target55484/state.json'
assert json.loads(gate.read_text())['gate_passed']
inputs={'files':{name:hashlib.sha256(data).hexdigest() for name,data in members.items()},
        'network_gate_state_sha256':hashlib.sha256(gate.read_bytes()).hexdigest(),
        'product_sources':source_pins,'original_bootstrap_preserved_sha256':hashlib.sha256(original).hexdigest(),
        'bootstrap_v2_changes':'Bounded 4-byte length stdin frame and explicit2 LAB web workers; production validators/entrypoint unmodified.'}
members['inputs.json']=(json.dumps(inputs,indent=2)+'\n').encode()
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w') as archive:
    for name,data in sorted(members.items()):
        item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o444;item.mtime=0
        archive.addfile(item,io.BytesIO(data))
payload=buffer.getvalue();sha=hashlib.sha256(payload).hexdigest()
transport=OUT/'nonsecret-artifacts.tar';transport.write_bytes(payload)
spec=importlib.util.spec_from_file_location('access',LAB/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
prepare=r'''from pathlib import Path
import hashlib,io,sys,tarfile
data=sys.stdin.buffer.read();assert hashlib.sha256(data).hexdigest()==EXPECTED
root=Path('/home/lab/metodobase-runtime28-product-a781deb39fd74441baa6a37c1a0cab40');assert not root.exists()
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
 names=[]
 for m in archive.getmembers():
  p=Path(m.name);names.append(m.name)
  assert m.isfile() and not p.is_absolute() and '..' not in p.parts and ':' not in m.name and '\\' not in m.name
 assert len(names)==len(set(names))==len({n.casefold() for n in names})==5
 root.mkdir(mode=0o700)
 archive.extractall(root,filter='data')
print('NONSECRET_RUNTIME_ARTIFACTS_READY')
'''.replace('EXPECTED',repr(sha))
with transport.open('rb') as stream:result=access.run('/opt/metodobase-lab/python/bin/python3.12 -c '+shlex.quote(prepare),stdin=stream,timeout=60)
(OUT/'artifact-transfer.log').write_bytes(result.stdout+result.stderr)
assert result.returncode==0
(OUT/'artifact-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'nonsecret_artifact_transport_sha256':sha,'bootstrap_v2_sha256':inputs['files']['helpers/private_stdin_entrypoint_v2.py'],
                  'production_code_modified':False,'secret_consumption':False}))
