"""Strict SSH access only to the owned local TCG guest; no broad host share."""
from pathlib import Path
import argparse,json,os,subprocess,sys

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')

def configuration():
    state=json.loads((LAB/'instance/state.json').read_text())
    profile=LAB/'instance/qemu-profile'
    allowed={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TMP','TEMP','LANG','LC_ALL'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed}
    env.update(APPDATA=str(profile),LOCALAPPDATA=str(profile),USERPROFILE=str(profile),HOME=str(profile),PROGRAMDATA=str(profile))
    key=Path(state['ssh_key_path_private_do_not_print']);known=LAB/'instance/ssh/known_hosts'
    assert key.resolve().is_relative_to((LAB/'instance/ssh').resolve()) and key.is_file()
    command=[r'C:\Windows\System32\OpenSSH\ssh.exe','-F','NUL','-i',str(key),'-o','IdentitiesOnly=yes',
             '-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(known),
             '-o','ConnectTimeout=10','-p',str(state['ports']['ssh']),'lab@127.0.0.1']
    return command,env

def run(remote,*,stdin=None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60):
    command,env=configuration()
    return subprocess.run(command+[remote],stdin=stdin,stdout=stdout,stderr=stderr,cwd=LAB/'instance',env=env,
                          timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--command',required=True,help='Shell command inside the owned guest only')
    parser.add_argument('--stdin-file',type=Path,help='One explicit input file; no host directory shared')
    parser.add_argument('--timeout',type=float,default=60)
    args=parser.parse_args()
    assert 0<args.timeout<=3600
    if args.stdin_file:
        with args.stdin_file.open('rb') as stream:result=run(args.command,stdin=stream,timeout=args.timeout)
    else:result=run(args.command,timeout=args.timeout)
    sys.stdout.buffer.write(result.stdout);sys.stderr.buffer.write(result.stderr)
    raise SystemExit(result.returncode)
