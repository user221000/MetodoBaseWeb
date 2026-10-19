from pathlib import Path
import hashlib,json,subprocess,sys
r=Path(__file__).parent;a=Path('F:/MetodoBaseWeb-metrics-20261019')
sha=lambda b:hashlib.sha256(b).hexdigest()
p=a/'docs/implementation/20261018-evolution/evidence/metrics-privacy-root-source.json';raw=p.read_bytes();manifest=json.loads(raw)
sources={name:sha((a/name).read_bytes()) for name in manifest['sources']}
assert sources==manifest['sources']
assert subprocess.run(['git','rev-parse','HEAD'],cwd=a,capture_output=True,check=True,text=True).stdout.strip()=='2b58139ca534fb245095be926d9d00c33ba09504'
assert not subprocess.run(['git','status','--porcelain'],cwd=a,capture_output=True,check=True,text=True).stdout
review_dependencies=['web/middleware/__init__.py','web/rate_limiter_redis.py','web/rate_limiter.py','web/settings.py','conftest.py','tests/run_isolated.py','requirements-test-windows.lock','docs/implementation/20261018-evolution/METRICAS_PRIVACIDAD.md']
sources.update({name:sha((a/name).read_bytes()) for name in review_dependencies})
baseline=subprocess.run(['git','show','2b58139^:web/middleware/metrics.py'],cwd=a,capture_output=True,check=True).stdout
if sys.argv[1]=='before':(r/'baseline-metrics.py').write_bytes(baseline)
else:assert (r/'baseline-metrics.py').read_bytes()==baseline
record={'author_commit':'2b58139ca534fb245095be926d9d00c33ba09504','author_manifest_sha256':sha(raw),'sources':sources,'source_count':len(sources),'tracked_and_untracked_clean':True,'baseline_git_blob_bytes_sha256':sha(baseline),'baseline_normalized_LF_sha256':sha(baseline.replace(b'\r\n',b'\n')),'author_recorded_original_metrics_sha256':manifest['original_metrics_sha256'],'hash_scope':'Raw worktree vs Git blob hashes retain their own byte boundaries; no equivalence inferred from text alone.'}
(r/('sources-'+sys.argv[1]+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps({'phase':sys.argv[1],'sources':len(sources),'clean':True,'baseline_git_blob_sha256':sha(baseline)}))
