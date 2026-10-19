from pathlib import Path
from datetime import datetime, timezone
import hashlib, io, json, os, secrets, socket, stat, subprocess, sys, time

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
TOOL=LAB/'tools/qemu'
INSTANCE=LAB/'instance'
BASE=LAB/'downloads/debian-12-genericcloud-amd64-20261006-2623.qcow2'

def digest(p, algorithm='sha256'):
    with p.open('rb') as f:return hashlib.file_digest(f,algorithm).hexdigest()

def save(name,data):
    (LAB/'evidence'/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

def no_links(paths):
    all_paths=set()
    for p in paths:all_paths.update((p,*p.parents))
    for p in all_paths:
        assert not p.is_symlink() and not(getattr(p.lstat(),'st_file_attributes',0)&0x400),p

verified=json.loads((LAB/'evidence/linux-tcg-qemu-verified.json').read_text())
assert verified['stable_tools'] and verified['archive_paths_and_sizes_match']
for name in ('qemu-img.exe','qemu-system-x86_64.exe'):
    assert digest(TOOL/name)==verified['files'][name]['sha256']
assert digest(BASE,'sha512')=='a09170d17e13af43da61774666f520e3bbec0f8bd96b4db37c15f3426fb327ccad950b80dbe78c09aa5ca90ce5015e99334b0ba5188fd4018736bc3fb5f0882c'
no_links([LAB,INSTANCE,TOOL,BASE])
profile=INSTANCE/'qemu-profile';profile.mkdir(exist_ok=True)
allowed={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TMP','TEMP','LANG','LC_ALL'}
env={k:v for k,v in os.environ.items() if k.upper() in allowed}
env.update(APPDATA=str(profile),LOCALAPPDATA=str(profile),USERPROFILE=str(profile),HOME=str(profile))

def run(command,timeout=30):
    result=subprocess.run(command,cwd=INSTANCE,env=env,capture_output=True,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,(command,result.returncode,result.stderr.decode('utf-8','replace'))
    return result

image_info=run([str(TOOL/'qemu-img.exe'),'info','--output=json',str(BASE)])
metadata=json.loads(image_info.stdout)
assert metadata['format']=='qcow2' and metadata['virtual-size']==3*1024**3
assert not metadata.get('backing-filename') and not metadata.get('data-file')
checked=run([str(TOOL/'qemu-img.exe'),'check','-f','qcow2',str(BASE)],timeout=60)
save('linux-tcg-base-image-check.json',{'metadata':metadata,'check_output':checked.stdout.decode('utf-8','replace'),'exit':0,'source_sha512':digest(BASE,'sha512')})
os.chmod(BASE,stat.S_IREAD)

ssh=INSTANCE/'ssh';ssh.mkdir(exist_ok=True)
key=ssh/'id_ed25519'
assert not any(ssh.iterdir()),'Private SSH directory must be empty before key generation'
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
private_key=Ed25519PrivateKey.generate()
key.write_bytes(private_key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.OpenSSH,serialization.NoEncryption()))
key.with_suffix('.pub').write_bytes(private_key.public_key().public_bytes(serialization.Encoding.OpenSSH,serialization.PublicFormat.OpenSSH)+b' metodobase-tcg-local-lab\n')
del private_key
pub=key.with_suffix('.pub').read_text().strip()
assert pub.startswith('ssh-ed25519 ') and 'PRIVATE' not in pub
fingerprint=run([r'C:\Windows\System32\OpenSSH\ssh-keygen.exe','-lf',str(key.with_suffix('.pub'))]).stdout.decode().strip()
nonce=secrets.token_hex(20)
seed=INSTANCE/'seed';seed.mkdir()
user_data='''#cloud-config
hostname: metodobase-tcg
manage_etc_hosts: true
users:
  - name: lab
    gecos: Local isolated test lab
    groups: [sudo]
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    lock_passwd: true
    ssh_authorized_keys:
      - PUBLIC_KEY
ssh_pwauth: false
disable_root: true
package_update: false
package_upgrade: false
runcmd:
  - [sh, -c, "uname -a > /var/tmp/metodobase-boot-uname.txt"]
  - [sh, -c, "printf 'NONCE\\n' > /var/tmp/metodobase-lab-nonce"]
  - [sh, -c, "printf 'METODOBASE_LAB_READY_NONCE\\n' > /dev/ttyS0"]
  - [sh, -c, "printf 'METODOBASE_HOST_KEY ' > /dev/ttyS0; cat /etc/ssh/ssh_host_ed25519_key.pub > /dev/ttyS0"]
'''.replace('PUBLIC_KEY',pub).replace('NONCE',nonce)
metadata_text='instance-id: metodobase-tcg-'+nonce+'\nlocal-hostname: metodobase-tcg\n'
network='version: 2\nethernets:\n  labnic:\n    match:\n      macaddress: "52:54:00:19:10:19"\n    dhcp4: true\n    dhcp6: false\n'
for name,text in [('user-data',user_data),('meta-data',metadata_text),('network-config',network)]:
    (seed/name).write_text(text,encoding='utf-8',newline='\n')
wheel=LAB/'downloads/pycdlib-1.22.0-py3-none-any.whl'
assert digest(wheel)=='bfa0b3631345a14b2741fe088398b6b8dc2838442ea607fd07d027dcc67b9e94'
sys.path.insert(0,str(LAB/'tools/pycdlib'))
import pycdlib
iso=pycdlib.PyCdlib();iso.new(interchange_level=3,joliet=3,rock_ridge='1.09',vol_ident='CIDATA')
for index,name in enumerate(('user-data','meta-data','network-config')):
    iso.add_file(str(seed/name),iso_path='/SEED'+str(index)+'.;1',rr_name=name,joliet_path='/'+name)
iso_path=INSTANCE/'seed.iso';iso.write(str(iso_path));iso.close()
reader=pycdlib.PyCdlib();reader.open(str(iso_path))
for name in ('user-data','meta-data','network-config'):
    buf=io.BytesIO();reader.get_file_from_iso_fp(buf,rr_path='/'+name);assert buf.getvalue()==(seed/name).read_bytes()
reader.close()
overlay=INSTANCE/'disk-overlay.qcow2';assert not overlay.exists()
created=run([str(TOOL/'qemu-img.exe'),'create','-f','qcow2','-F','qcow2','-b',str(BASE),str(overlay),'12G'])

reserved=[]
for purpose in ('ssh','qmp'):
    connection=socket.socket();connection.bind(('127.0.0.1',0));reserved.append((purpose,connection.getsockname()[1],connection))
ports={purpose:port for purpose,port,_ in reserved}
serial=LAB/'evidence/guest-serial.log'
command=[str(TOOL/'qemu-system-x86_64.exe'),'-name','metodobase-linux-tcg-local-lab',
         '-no-user-config','-nodefaults','-L',str(TOOL/'share'),'-machine','q35','-accel','tcg,thread=multi',
         '-cpu','max','-smp','2','-m','2048','-display','none','-monitor','none',
         '-qmp','tcp:127.0.0.1:'+str(ports['qmp'])+',server=on,wait=off',
         '-serial','file:'+str(serial),'-boot','order=c','-no-reboot',
         '-drive','file='+str(overlay)+',if=virtio,format=qcow2,cache=writeback,discard=unmap',
         '-drive','file='+str(iso_path)+',if=virtio,format=raw,readonly=on',
         '-object','rng-builtin,id=rng0','-device','virtio-rng-pci,rng=rng0',
         '-netdev','user,id=net0,hostfwd=tcp:127.0.0.1:'+str(ports['ssh'])+'-:22',
         '-device','virtio-net-pci,netdev=net0,mac=52:54:00:19:10:19','-rtc','base=utc']
for _,_,connection in reserved:connection.close()
stdout=(LAB/'evidence/qemu-stdout.log').open('xb');stderr=(LAB/'evidence/qemu-stderr.log').open('xb')
process=subprocess.Popen(command,cwd=INSTANCE,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,
                         creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
time.sleep(2)
assert process.poll() is None,(process.returncode,(LAB/'evidence/qemu-stderr.log').read_text())
state={'started_utc':datetime.now(timezone.utc).isoformat(),'pid':process.pid,'command':command,'ports':ports,
       'source_image':str(BASE),'source_sha512':digest(BASE,'sha512'),'overlay':str(overlay),'overlay_virtual_bytes':12*1024**3,
       'seed_iso':str(iso_path),'seed_iso_sha256':digest(iso_path),'nonce':nonce,'ssh_username':'lab',
       'ssh_key_path_private_do_not_print':str(key),'ssh_public_fingerprint':fingerprint,
       'serial_log':str(serial),'creationflags':'CREATE_NO_WINDOW|CREATE_NEW_PROCESS_GROUP',
       'resources':{'vcpus':2,'memory_mib':2048,'acceleration':'tcg,thread=multi'},
       'scope':'Local software-emulated test guest only. NAT egress for apt/pip preparation. SSH/QMP bound only 127.0.0.1; no host filesystem shared. No product code exported.'}
(INSTANCE/'state.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
save('linux-tcg-boot-start.json',{k:v for k,v in state.items() if k!='ssh_key_path_private_do_not_print'})
print(json.dumps({'pid':process.pid,'ports':ports,'resources':state['resources'],'source_readonly':True,'seed_roundtrip_verified':True,'private_key_not_disclosed':True},indent=2))
