from pathlib import Path
from datetime import datetime, timezone
import base64, hashlib, json, os, re, subprocess, time

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
state=json.loads((LAB/'instance/state.json').read_text())
serial_path=Path(state['serial_log'])
ready=('METODOBASE_LAB_READY_'+state['nonce']).encode()
started=time.monotonic();host_key=None
while time.monotonic()-started<45:
    serial=serial_path.read_bytes() if serial_path.exists() else b''
    key=re.search(rb'METODOBASE_HOST_KEY (ssh-ed25519 [A-Za-z0-9+/=]+)',serial)
    if ready in serial and key:
        host_key=key.group(1).decode('ascii');break
    time.sleep(3)
if host_key is None:
    print(json.dumps({'ready':False,'serial_bytes':len(serial),'elapsed_seconds':round(time.monotonic()-started,3)}))
    raise SystemExit(2)
known=LAB/'instance/ssh/known_hosts'
known.write_text('[127.0.0.1]:'+str(state['ports']['ssh'])+' '+host_key+'\n',encoding='ascii')
allowed={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TMP','TEMP','LANG','LC_ALL'}
env={k:v for k,v in os.environ.items() if k.upper() in allowed}
profile=LAB/'instance/qemu-profile'
env.update(APPDATA=str(profile),LOCALAPPDATA=str(profile),USERPROFILE=str(profile),HOME=str(profile),PROGRAMDATA=str(profile))
remote="""python3 - <<'PY'
import json,platform,os,subprocess
from pathlib import Path
result={'system':platform.system(),'uname':list(os.uname()),'identity':subprocess.check_output(['id'],text=True).strip(),
        'lab_nonce':Path('/var/tmp/metodobase-lab-nonce').read_text().strip(),
        'os_release':Path('/etc/os-release').read_text(),
        'memory':Path('/proc/meminfo').read_text().splitlines()[:3],
        'disk':subprocess.check_output(['df','-h','/'],text=True),
        'cloud_init':subprocess.run(['cloud-init','status'],capture_output=True,text=True).stdout.strip(),
        'virtualization':subprocess.run(['systemd-detect-virt'],capture_output=True,text=True).stdout.strip(),
        'sudo_noninteractive':subprocess.run(['sudo','-n','true']).returncode}
print(json.dumps(result))
PY
"""
command=[r'C:\Windows\System32\OpenSSH\ssh.exe','-F','NUL','-i',state['ssh_key_path_private_do_not_print'],
         '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
         '-o','UserKnownHostsFile='+str(known),'-o','ConnectTimeout=8','-p',str(state['ports']['ssh']),
         'lab@127.0.0.1',remote]
result=subprocess.run(command,env=env,cwd=LAB/'instance',capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
(LAB/'evidence/linux-tcg-ssh-initial.log').write_bytes(result.stdout+b'\n'+result.stderr)
assert result.returncode==0,(result.returncode,result.stderr.decode('utf-8','replace'))
guest=json.loads(result.stdout)
assert guest['system']=='Linux' and guest['lab_nonce']==state['nonce'] and guest['sudo_noninteractive']==0
assert 'uid=1000(lab)' in guest['identity'] and guest['uname'][4]=='x86_64'
host_fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(base64.b64decode(host_key.split()[1])).digest()).decode().rstrip('=')
report={'captured_utc':datetime.now(timezone.utc).isoformat(),'ready':True,'pid':state['pid'],'ssh_port':state['ports']['ssh'],
        'ssh_bind':'127.0.0.1','strict_host_key_checking':True,'known_host_key_source':'Owned QEMU serial log from pinned guest image',
        'host_key_fingerprint':host_fingerprint,'ssh_exit':result.returncode,'guest':guest,
        'private_key_content_disclosed':False,'host_filesystem_shared':False,'product_code_exported':False,
        'scope':'Guest Linux and owned key-only SSH proven; no product tests or performance claims.'}
(LAB/'evidence/linux-tcg-guest-ssh-ready.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
