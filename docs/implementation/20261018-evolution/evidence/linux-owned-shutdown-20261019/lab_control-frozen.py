"""Owned VM lifecycle only. Never invokes a Windows shutdown command."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, socket, subprocess, time

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
STATE=LAB/'instance/state.json'

def state():return json.loads(STATE.read_text())

def process_identity(s):
    command=['powershell','-NoProfile','-NonInteractive','-Command',
        'Get-CimInstance Win32_Process -Filter "ProcessId='+str(int(s['pid']))+'" -ErrorAction SilentlyContinue | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress']
    result=subprocess.run(command,capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
    if not result.stdout.strip():return None
    process=json.loads(result.stdout)
    assert Path(process['ExecutablePath']).resolve()==Path(s['command'][0]).resolve(),'PID belongs to another executable'
    commandline=process['CommandLine'].casefold()
    assert str(s['overlay']).casefold() in commandline and str(s['seed_iso']).casefold() in commandline
    assert '-name metodobase-linux-tcg-local-lab' in commandline and '-accel tcg,thread=multi' in commandline
    expected=json.loads((LAB/'evidence/linux-tcg-qemu-verified.json').read_text())['files']['qemu-system-x86_64.exe']['sha256']
    with Path(process['ExecutablePath']).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected
    return process

def qmp(s,commands):
    assert process_identity(s),'Owned QEMU process is not running'
    with socket.create_connection(('127.0.0.1',s['ports']['qmp']),timeout=5) as connection:
        connection.settimeout(5);stream=connection.makefile('rwb',buffering=0)
        greeting=json.loads(stream.readline());answers={'greeting':greeting}
        for name in ['qmp_capabilities',*commands]:
            stream.write((json.dumps({'execute':name,'id':name})+'\n').encode())
            while True:
                answer=json.loads(stream.readline())
                if answer.get('id')==name:
                    assert 'error' not in answer,answer
                    answers[name]=answer;break
    return answers

def start(s):
    assert not process_identity(s),'Owned QEMU already running'
    for key in ('source_image','overlay','seed_iso'):
        p=Path(s[key]);assert p.resolve().is_relative_to(LAB.resolve()) and p.is_file()
        for parent in (p,*p.parents):assert not parent.is_symlink() and not(getattr(parent.lstat(),'st_file_attributes',0)&0x400)
    with Path(s['source_image']).open('rb') as stream:assert hashlib.file_digest(stream,'sha512').hexdigest()==s['source_sha512']
    assert s['resources']=={'vcpus':2,'memory_mib':2048,'acceleration':'tcg,thread=multi'}
    command=s['command'].copy()
    assert command[command.index('-accel')+1]=='tcg,thread=multi'
    for port in s['ports'].values():
        with socket.socket() as test:test.bind(('127.0.0.1',port))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    serial=LAB/'evidence'/('guest-serial-'+stamp+'.log')
    command[command.index('-serial')+1]='file:'+str(serial)
    allowed={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TMP','TEMP','LANG','LC_ALL'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed};profile=LAB/'instance/qemu-profile'
    env.update(APPDATA=str(profile),LOCALAPPDATA=str(profile),USERPROFILE=str(profile),HOME=str(profile),PROGRAMDATA=str(profile))
    with (LAB/'evidence'/('qemu-restart-stdout-'+stamp+'.log')).open('xb') as stdout, (LAB/'evidence'/('qemu-restart-stderr-'+stamp+'.log')).open('xb') as stderr:
        process=subprocess.Popen(command,cwd=LAB/'instance',env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,
                                 creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
    time.sleep(2);assert process.poll() is None
    s.update(pid=process.pid,command=command,serial_log=str(serial),restarted_utc=datetime.now(timezone.utc).isoformat())
    STATE.write_text(json.dumps(s,indent=2)+'\n',encoding='utf-8')
    return {'pid':process.pid,'ports':s['ports'],'reused_owned_overlay':True,'source_image_unchanged':True}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['status','shutdown','start'])
    args=parser.parse_args();s=state()
    if args.action=='status':result=qmp(s,['query-status','query-memory-size-summary','query-block'])
    elif args.action=='shutdown':result=qmp(s,['system_powerdown'])
    else:result=start(s)
    print(json.dumps(result,indent=2))
