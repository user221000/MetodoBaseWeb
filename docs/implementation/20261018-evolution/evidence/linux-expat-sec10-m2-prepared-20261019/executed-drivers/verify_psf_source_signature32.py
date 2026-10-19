from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,tempfile
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019');OUT=LAB/'evidence/expat-sec10-preparation32-20261019';GPG=Path(r'C:\Program Files\Git\usr\bin\gpg.exe')
SOURCE=LAB/'evidence/sca-native-triage31-20261019/primary/Python-3.12.15.tar.xz';KEY=OUT/'primary/python-release-key.asc';SIG=OUT/'primary/Python-3.12.15.tar.xz.asc';FPR='7169605F62C751356D054A26A821E680E5FA6305'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE)=='c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a';assert sha(KEY)=='1de2bbd31e2dd10aab4098c3ab2f937c530d924ddbfa2dd091f0c7cfb2ee182a';assert sha(SIG)=='e80124b35dabf82264f254dbb291697df96768f6e4ee0e43d7e8f110a9ea50b6';assert sha(GPG)=='a5140c85353e8399da8d6bd7e3741524cd76a4e69be88af12042b1c9ef022984'
home=Path(tempfile.mkdtemp(prefix='metodobase-expat-sec10-gpg32-repeat-'))
def mpath(p):return '/'+p.drive[0].lower()+'/'+p.relative_to(p.anchor).as_posix()
base=[str(GPG),'--homedir',mpath(home),'--no-options','--batch','--no-auto-key-retrieve','--no-autostart'];kw={'capture_output':True,'text':True,'creationflags':subprocess.CREATE_NO_WINDOW}
imp=subprocess.run(base+['--import',mpath(KEY)],**kw);assert imp.returncode==0,imp.stderr
verify=subprocess.run(base+['--status-fd','1','--verify',mpath(SIG),mpath(SOURCE)],**kw);assert verify.returncode==0,verify.stderr
valid=[line for line in verify.stdout.splitlines() if line.startswith('[GNUPG:] VALIDSIG ')];assert len(valid)==1 and FPR in [valid[0].split()[2],valid[0].split()[-1]]
(OUT/'psf-signature-repeat.log').write_text(verify.stdout+'\nSTDERR\n'+verify.stderr,encoding='utf-8')
r={'verified_utc':datetime.now(timezone.utc).isoformat(),'exit':0,'validsig':valid[0],'primary_fingerprint_reference':'Pinned official Python base Dockerfile ENV GPG_KEY '+FPR,'public_key_distributor_url':'https://keys.openpgp.org/vks/v1/by-fingerprint/'+FPR,'hashes':{str(p):sha(p) for p in [SOURCE,KEY,SIG,GPG]},'gpg_home_own':str(home),'argv':base+['--status-fd','1','--verify',mpath(SIG),mpath(SOURCE)],'scope':'Existing GPG; public verification in isolated own keyring with no agent/keyserver/global changes. No packages or source/native builds.'};(OUT/'psf-signature-repeat-receipt.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps({'exit':0,'validsig':valid[0]}))
