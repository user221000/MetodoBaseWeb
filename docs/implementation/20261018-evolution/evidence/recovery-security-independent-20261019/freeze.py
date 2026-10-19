from pathlib import Path
import hashlib,json,subprocess,sys
r=Path(__file__).parent;a=Path('F:/MetodoBaseWeb-recovery-20261019');sha=lambda b:hashlib.sha256(b).hexdigest()
mp=a/'docs/implementation/20261018-evolution/evidence/backend-recovery-source.json';raw=mp.read_bytes()
assert sha(raw)=='6a508f91806301d3b3c25f472c0f0b7cc4b9b0fcbbe2046c5eb30a1cc166e446'
m=json.loads(raw);sources={n:sha((a/n).read_bytes()) for n in m['sources']};assert sources==m['sources']
assert subprocess.run(['git','rev-parse','HEAD'],cwd=a,capture_output=True,check=True,text=True).stdout.strip()=='35a3c133c194b8f6c8864314500db42031b79e59'
assert not subprocess.run(['git','status','--porcelain'],cwd=a,capture_output=True,check=True,text=True).stdout
proofs={name:sha((a/'docs/implementation/20261018-evolution/evidence'/name).read_bytes()) for name in ['backend-recovery-author-review.json','backend-recovery-implementation.md','backend-recovery-preservation-proof.json','backend-recovery-seed-defaults-proof.json']}
record={'commit':'35a3c133c194b8f6c8864314500db42031b79e59','author_manifest_sha256':sha(raw),'source_count':len(sources),'sources':sources,'proofs':proofs,'clean':True}
(r/('sources-'+sys.argv[1]+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf8');print(json.dumps({'phase':sys.argv[1],'sources':len(sources),'clean':True}))
