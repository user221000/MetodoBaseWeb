from pathlib import Path
from datetime import datetime, timezone
import argparse, importlib.util, json, os, struct

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE=LAB/'evidence/runtime28-native-20261019'
PRIVATE=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-runtime28-roles-private-lwdcn5wd')
parser=argparse.ArgumentParser()
parser.add_argument('action',choices=['prepare','attach','status','stop'])
parser.add_argument('mode',choices=['migrate','web'])
args=parser.parse_args()
spec=importlib.util.spec_from_file_location('access',LAB/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
command='sudo -n /opt/metodobase-lab/python/bin/python3.12 /home/lab/metodobase-runtime28-product-a781deb39fd74441baa6a37c1a0cab40/runtime_guest_control.py '+args.action+' '+args.mode
stdin=None
if args.action=='attach':
    prepared=json.loads((BASE/'runtime'/(args.mode+'-prepare.json')).read_text())
    assert prepared['prepared'] and prepared['network_gate_before_stdin']
    private=json.loads((PRIVATE/'private.json').read_text())
    assert private['nonce']=='a781deb39fd74441baa6a37c1a0cab40'
    raw=json.dumps(private['runtime_stdin'],separators=(',',':')).encode()
    frame=PRIVATE/(args.mode+'.frame')
    with frame.open('xb') as stream:stream.write(struct.pack('!I',len(raw))+raw)
    os.chmod(frame,0o600)
    stdin=frame.open('rb')
try:
    result=access.run(command,stdin=stdin,timeout=540 if args.mode=='migrate' and args.action=='attach' else 180)
finally:
    if stdin is not None:stdin.close()
out=BASE/'runtime'/(args.mode+'-'+args.action+'.json')
if result.returncode==0:
    value=json.loads(result.stdout)
    with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(value,indent=2))
else:
    # Controller traces contain only control metadata; product RAW logs stay private.
    with (BASE/'runtime'/(args.mode+'-'+args.action+'-control-error.log')).open('xb') as stream:stream.write(result.stdout+result.stderr)
    print(json.dumps({'exit':result.returncode,'mode':args.mode,'action':args.action,'product_logs':'private; not emitted'}))
raise SystemExit(result.returncode)
