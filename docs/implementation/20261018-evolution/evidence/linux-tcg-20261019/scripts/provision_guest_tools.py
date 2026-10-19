from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import hashlib,json,os,posixpath,subprocess,tarfile,time

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
state=json.loads((LAB/'instance/state.json').read_text())
ready=json.loads((LAB/'evidence/linux-tcg-guest-ssh-ready.json').read_text())
assert ready['ready'] and ready['pid']==state['pid'] and ready['strict_host_key_checking']
archive=LAB/'downloads/cpython-3.12.15+20261013-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz'
expected='178d3d83b6e8e99285a65d3fce9c16b87952cc5efdb4d1a0e3ff3be18ff0fc9c'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
with tarfile.open(archive,'r:gz') as source:
    members=source.getmembers();names=set()
    for member in members:
        p=PurePosixPath(member.name)
        assert not p.is_absolute() and '..' not in p.parts and p.parts[0]=='python'
        assert member.name not in names;names.add(member.name)
        assert member.isfile() or member.isdir() or member.issym() or member.islnk()
        if member.issym() or member.islnk():
            resolved=posixpath.normpath(posixpath.join(posixpath.dirname(member.name),member.linkname)) if member.issym() else posixpath.normpath(member.linkname)
            assert resolved=='python' or resolved.startswith('python/'),(member.name,member.linkname)
allowed={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TMP','TEMP','LANG','LC_ALL'}
env={k:v for k,v in os.environ.items() if k.upper() in allowed}
profile=LAB/'instance/qemu-profile'
env.update(APPDATA=str(profile),LOCALAPPDATA=str(profile),USERPROFILE=str(profile),HOME=str(profile),PROGRAMDATA=str(profile))
ssh=[r'C:\Windows\System32\OpenSSH\ssh.exe','-F','NUL','-i',state['ssh_key_path_private_do_not_print'],
     '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
     '-o','UserKnownHostsFile='+str(LAB/'instance/ssh/known_hosts'),'-o','ConnectTimeout=10',
     '-p',str(state['ports']['ssh']),'lab@127.0.0.1']

def run(label,remote,stdin=None,timeout=1800):
    started=time.monotonic()
    print(json.dumps({'stage':label,'started_utc':datetime.now(timezone.utc).isoformat()}),flush=True)
    with (LAB/'evidence'/('linux-tcg-'+label+'.log')).open('xb') as log:
        process=subprocess.run(ssh+[remote],stdin=stdin,stdout=log,stderr=subprocess.STDOUT,env=env,cwd=LAB/'instance',
                               timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
    record={'stage':label,'exit':process.returncode,'seconds':round(time.monotonic()-started,3)}
    (LAB/'evidence'/('linux-tcg-'+label+'-receipt.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record),flush=True)
    assert process.returncode==0,record

transfer="set -eu\numask 077\nmkdir -p /home/lab/bootstrap\ncat > /home/lab/bootstrap/python312.tar.gz.partial\nprintf '%s  %s\\n' '"+expected+"' /home/lab/bootstrap/python312.tar.gz.partial | sha256sum -c -\nmv /home/lab/bootstrap/python312.tar.gz.partial /home/lab/bootstrap/python312.tar.gz\n"
with archive.open('rb') as stream:run('python312-transfer',transfer,stdin=stream,timeout=180)
install="""set -eu
sudo -n mkdir -p /opt/metodobase-lab
sudo -n tar --no-same-owner --no-same-permissions -xzf /home/lab/bootstrap/python312.tar.gz -C /opt/metodobase-lab
/opt/metodobase-lab/python/bin/python3.12 -V
/opt/metodobase-lab/python/bin/python3.12 -m pip --version
sudo -n env DEBIAN_FRONTEND=noninteractive apt-get update
sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends docker.io redis-server ca-certificates git python3-venv
sudo -n systemctl enable --now docker.service redis-server.service
sudo -n docker version
sudo -n docker info
redis-cli ping
ss -ltnp
"""
run('guest-tool-install',install,timeout=1800)
report={'finished_utc':datetime.now(timezone.utc).isoformat(),'python_version':'3.12.15','python_archive_sha256':expected,
        'python_archive_members_validated':len(members),'docker_and_redis_prepared_inside_guest_only':True,
        'windows_python_environment_changed':False,'product_locks_changed':False,'product_build_run':False,
        'scope':'Preparation only. Linux Python 3.12.15 is separate from existing Windows Python 3.12.13. No application or benchmark run.'}
(LAB/'evidence/linux-tcg-guest-tool-provisioned.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
