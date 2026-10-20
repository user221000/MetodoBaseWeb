from pathlib import Path
import hashlib, importlib.metadata, json, os, subprocess, sys, time, xml.etree.ElementTree as ET

ROOT=Path('F:/mb-qa-followup34-sqlfix-20261020')
TASK=Path(__file__).resolve().parent
PRIVATE=TASK/'private'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot(label):
    names=subprocess.check_output(['git','-C',str(ROOT),'ls-files','-z']).decode().split('\0')
    source={name:digest(ROOT/name) for name in names if name and not name.startswith('docs/') and (ROOT/name).is_file()}
    extras=subprocess.check_output(['git','-C',str(ROOT),'ls-files','--others','--exclude-standard','-z']).decode().split('\0')
    for name in extras:
        if name and not name.startswith('docs/') and (ROOT/name).suffix.lower() in {'.py','.js','.cjs','.mjs','.json','.txt','.lock','.toml','.ini','.yaml','.yml'}:
            source[name]=digest(ROOT/name)
    packages=[]
    installed={}
    for distribution in importlib.metadata.distributions():
        packages.append([distribution.metadata['Name'],distribution.version])
        for file in distribution.files or []:
            path=Path(distribution.locate_file(file)).resolve()
            if path.is_file() and path.suffix not in {'.pyc','.pyo'}:
                installed[str(path)]=digest(path)
    helpers={p.name:digest(p) for p in TASK.glob('*.py')}
    result={'head':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'source':source,'packages':sorted(packages),'installed':installed,'python':{'path':sys.executable,'sha256':digest(Path(sys.executable))},'helpers':helpers}
    (PRIVATE/(label+'-snapshot.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

def pipcheck(label):
    r=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,cwd=ROOT)
    (PRIVATE/(label+'-pip.stdout')).write_bytes(r.stdout)
    (PRIVATE/(label+'-pip.stderr')).write_bytes(r.stderr)
    assert r.returncode==0
    return r.returncode

def main():
    before=snapshot('before')
    pipcheck('before')
    print(json.dumps({'started':True,'source_files':len(before['source']),'packages':len(before['packages']),'installed_files':len(before['installed']),'helpers':len(before['helpers'])}),flush=True)
    runs=[]
    for stage in ('maintained','own'):
        start=time.monotonic()
        with (PRIVATE/(stage+'.stdout')).open('wb') as out,(PRIVATE/(stage+'.stderr')).open('wb') as err:
            result=subprocess.run([sys.executable,'-B','-X','utf8',str(TASK/'runner.py'),stage],cwd=ROOT,stdout=out,stderr=err)
        report=ET.parse(PRIVATE/(stage+'.xml')).getroot()
        suites=list(report) if report.tag=='testsuites' else [report]
        total={key:sum(int(s.get(key,0)) for s in suites) for key in ('tests','failures','errors','skipped')}
        total.update({'stage':stage,'exit_code':result.returncode,'elapsed_s':round(time.monotonic()-start,3)})
        runs.append(total)
        print(json.dumps(total),flush=True)
    after=snapshot('after')
    pipcheck('after')
    comparisons={key:before[key]==after[key] for key in before}
    assert all(comparisons.values()), comparisons
    summary={'source_head':before['head'],'runs':runs,'stable':comparisons,'source_files':len(before['source']),'packages':len(before['packages']),'installed_files':len(before['installed']),'pip_before':0,'pip_after':0}
    (TASK/'phase-result.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({'closed':True,'stable':comparisons}),flush=True)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
