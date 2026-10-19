from pathlib import Path
import importlib.util,json
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE=LAB/'evidence/runtime28-native-20261019'
OUT=BASE/'closure';OUT.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('access',LAB/'scripts/guest_access.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
with (BASE/'scripts/close_owned_guest_network.py').open('rb') as source:
    r=a.run('sudo -n /opt/metodobase-lab/python/bin/python3.12 -B -',stdin=source,timeout=180)
(OUT/'guest-teardown.stdout.json').write_bytes(r.stdout)
(OUT/'guest-teardown.stderr.log').write_bytes(r.stderr)
print(json.dumps({'exit':r.returncode,'receipt':r.stdout.decode() if r.returncode==0 else 'see nonsecret control log'}))
raise SystemExit(r.returncode)
