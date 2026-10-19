from pathlib import Path
from datetime import datetime,timezone
import json,os,subprocess,time

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
state=json.loads((LAB/'instance/state.json').read_text())
assert json.loads((LAB/'evidence/linux-tcg-guest-tool-provisioned.json').read_text())['docker_and_redis_prepared_inside_guest_only']
allowed={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TMP','TEMP','LANG','LC_ALL'}
env={k:v for k,v in os.environ.items() if k.upper() in allowed};profile=LAB/'instance/qemu-profile'
env.update(APPDATA=str(profile),LOCALAPPDATA=str(profile),USERPROFILE=str(profile),HOME=str(profile),PROGRAMDATA=str(profile))
ssh=[r'C:\Windows\System32\OpenSSH\ssh.exe','-F','NUL','-i',state['ssh_key_path_private_do_not_print'],
     '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
     '-o','UserKnownHostsFile='+str(LAB/'instance/ssh/known_hosts'),'-o','ConnectTimeout=10',
     '-p',str(state['ports']['ssh']),'lab@127.0.0.1']
smoke="""set -eu
sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends busybox-static
test ! -e /var/tmp/metodobase-container-root
sudo -n mkdir -p /var/tmp/metodobase-container-root/bin
sudo -n install -m 0755 /bin/busybox /var/tmp/metodobase-container-root/bin/busybox
sudo -n tar -C /var/tmp/metodobase-container-root -cf /var/tmp/metodobase-smoke-rootfs.tar .
sudo -n docker image import /var/tmp/metodobase-smoke-rootfs.tar metodobase-tcg-smoke:owned
sudo -n docker run --rm --pull=never --network=none --read-only --cap-drop=ALL --security-opt=no-new-privileges metodobase-tcg-smoke:owned /bin/busybox uname -s
sudo -n docker image inspect metodobase-tcg-smoke:owned --format '{{.Id}}' > /var/tmp/metodobase-smoke-image-id
sudo -n docker image rm metodobase-tcg-smoke:owned
"""
with (LAB/'evidence/linux-tcg-container-smoke.log').open('xb') as log:
    result=subprocess.run(ssh+[smoke],env=env,cwd=LAB/'instance',stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode==0,result.returncode
log_text=(LAB/'evidence/linux-tcg-container-smoke.log').read_text(encoding='utf-8')
assert '\nLinux\n' in log_text
remote="""python3 - <<'PY'
from pathlib import Path
import json,os,subprocess
def run(*cmd):return subprocess.check_output(cmd,text=True).strip()
nonce=Path('/var/tmp/metodobase-lab-nonce').read_text().strip()
key='metodobase:tcg:smoke:'+nonce
assert run('redis-cli','-h','127.0.0.1','PING')=='PONG'
assert run('redis-cli','-h','127.0.0.1','SET',key,nonce,'EX','60','NX')=='OK'
assert run('redis-cli','-h','127.0.0.1','GET',key)==nonce
assert run('redis-cli','-h','127.0.0.1','DEL',key)=='1'
python=json.loads(run('/opt/metodobase-lab/python/bin/python3.12','-c','import sys,ssl,json;print(json.dumps({"version":sys.version,"executable":sys.executable,"openssl":ssl.OPENSSL_VERSION}))'))
docker=json.loads(run('sudo','-n','docker','version','--format','{{json .}}'))
data={'system':os.uname().sysname,'kernel':os.uname().release,'architecture':os.uname().machine,'cpus':os.cpu_count(),
      'python':python,'docker':docker,'redis_version':run('redis-server','--version'),
      'redis_ping_set_get_delete_own_ttl_key':True,
      'packages':run('dpkg-query','-W','-f=${binary:Package} ${Version}\\n','docker.io','redis-server','containerd','runc','busybox-static','python3'),
      'guest_tcp_listeners':run('ss','-ltn'),'guest_unix_docker_socket':run('stat','-c','%F %a','/var/run/docker.sock'),
      'container_smoke_image_id':Path('/var/tmp/metodobase-smoke-image-id').read_text().strip(),
      'container_smoke_from_local_debian_busybox':True,'external_container_image_pulled':False,
      'container_network':'none','container_rootfs_readonly':True,'container_capabilities':'ALL dropped',
      'cloud_init':run('cloud-init','status'),'memory':Path('/proc/meminfo').read_text().splitlines()[:3],
      'disk':run('df','-h','/')}
print(json.dumps(data))
PY
"""
result=subprocess.run(ssh+[remote],env=env,cwd=LAB/'instance',capture_output=True,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode==0,(result.returncode,result.stderr.decode('utf-8','replace'))
guest=json.loads(result.stdout)
assert guest['system']=='Linux' and guest['architecture']=='x86_64' and guest['cpus']==2
assert guest['python']['version'].startswith('3.12.15') and guest['redis_ping_set_get_delete_own_ttl_key']
report={'captured_utc':datetime.now(timezone.utc).isoformat(),'ssh_host_key_checking':'strict, pinned from owned serial',
        'container_smoke_exit':0,'guest':guest,'product_code_exported':False,'product_tested':False,
        'windows_python_or_docker_changed':False,'scope':'TCG guest tooling and synthetic smoke only. No performance/latency claim; no product image built.'}
(LAB/'evidence/linux-tcg-guest-health-final.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
