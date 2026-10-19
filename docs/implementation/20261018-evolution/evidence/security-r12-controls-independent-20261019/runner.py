from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).parent
label=sys.argv[1];assert label.replace('-','').isalnum()
out=HERE/(label+'.raw.json');err=HERE/(label+'.stderr.log');assert not out.exists() and not err.exists()
p=subprocess.run(['node',*sys.argv[2:]],cwd=HERE,capture_output=True)
out.write_bytes(p.stdout);err.write_bytes(p.stderr)
result=json.loads(p.stdout)
safe={'exit':p.returncode,'total':result['total'],'passed':result['passed'],'raw_sha256':hashlib.sha256(p.stdout).hexdigest(),
    'stderr_sha256':hashlib.sha256(p.stderr).hexdigest(),'results':result['results']}
(HERE/(label+'-safe.json')).write_text(json.dumps(safe,indent=2)+'\n',encoding='utf8')
print(json.dumps(safe));raise SystemExit(p.returncode)
