from pathlib import Path
import hashlib,json,subprocess,sys
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-expat-m2-native-validation-20261019')
OLD=Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/linux-container-libpq-sec09-prepared-20261019/apt-primary/updates.InRelease')
sys.path.insert(0,str(LAB/'scripts'))
import guest_access
assert hashlib.sha256(OLD.read_bytes()).hexdigest()=='1ff5b5841ba7a91e3e4c1f43a5a0886d0a5987f1ab03c5fa3a04dbca0c6e7edf'
with OLD.open('rb') as stream:
 r=guest_access.run('umask 077; test ! -e /var/tmp/metodobase-expat-m2-native-20261019/refresh-review && mkdir -m 700 /var/tmp/metodobase-expat-m2-native-20261019/refresh-review && cat > /var/tmp/metodobase-expat-m2-native-20261019/refresh-review/old-updates.InRelease',stdin=stream,timeout=30)
assert r.returncode==0,r.stderr.decode()
remote="""python3 - <<'PY'
from pathlib import Path
import subprocess,json,re,hashlib,datetime
root=Path('/var/tmp/metodobase-expat-m2-native-20261019')
out=root/'refresh-review';home=out/'gpgv-home';home.mkdir(mode=0o700)
file=out/'old-updates.InRelease';key=root/'apt-failure-v2/debian-archive-keyring.gpg'
assert hashlib.sha256(file.read_bytes()).hexdigest()=='1ff5b5841ba7a91e3e4c1f43a5a0886d0a5987f1ab03c5fa3a04dbca0c6e7edf'
r=subprocess.run(['gpgv','--homedir',str(home),'--status-fd','1','--keyring',str(key),str(file)],capture_output=True)
(out/'old-updates.gpgv.stdout').write_bytes(r.stdout);(out/'old-updates.gpgv.stderr').write_bytes(r.stderr)
signers=re.findall(r'^\\[GNUPG:\\] VALIDSIG ([0-9A-F]+)',r.stdout.decode(),re.M)
assert r.returncode==0 and set(signers)=={'4CB50190207B4758A3F73A796ED0E7B82643E131','B8E5F13176D2A7A75220028078DBA3BC47EF2265'}
report={'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'Preserved old signed index verified with same immutable-base keyring as current index','sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'gpgv_exit':r.returncode,'signers':signers,'stdout':r.stdout.decode(),'stderr':r.stderr.decode(),'keyring_sha256':hashlib.sha256(key.read_bytes()).hexdigest()}
(out/'old-updates-signature.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps(report))
PY
"""
r=guest_access.run(remote,timeout=45)
(OUT/'old-index-signature-raw.log').write_bytes(r.stdout+b'\nSTDERR\n'+r.stderr)
assert r.returncode==0,r.stderr.decode()
(OUT/'old-index-signature-source.json').write_bytes(r.stdout)
print(json.dumps({k:v for k,v in json.loads(r.stdout).items() if k not in ('stdout','stderr')}))

