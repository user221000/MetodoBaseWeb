"""Current emitter/expiry/followup and all74 retained transport, plus frozen SEC10."""
from support import *
NODE=Path('C:/Program Files/nodejs/node.exe')
before=photo('node-before');phase=TEMP/'node';phase.mkdir(exist_ok=False)
node_sha=sha(NODE.read_bytes());assert node_sha=='ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32'
rows=[];env=dict(os.environ,SESSION_EVENT_REVIEW_ROOT=str(ROOT))
modules=[('session_revision_events',11),('session_expiry_fences',3),('dashboard_followup',20),('auth_refresh',None),('auth_refresh_storage',None),('auth_refresh_race_review',2),('auth_refresh_security_review',None),('SEC-frozen',10)]
for name,minimum in modules:
    source=TEMP/'security-driver-frozen-exact.cjs' if name=='SEC-frozen' else ROOT/'tests/e2e'/(name+'.cjs')
    if name=='SEC-frozen':assert sha(source.read_bytes())=='1c230a07b722e421123af6bf0ac688220b070c4438ad81fd15af326f6515f4b4'
    result=subprocess.run([str(NODE),str(source)],cwd=ROOT,env=env,capture_output=True,timeout=60)
    (phase/(name+'.json')).write_bytes(result.stdout);(phase/(name+'.stderr.log')).write_bytes(result.stderr)
    value=json.loads(result.stdout);cases=value.get('results',value.get('report',[]))
    assert result.returncode==0 and cases and all(case['passed']is True for case in cases)
    if minimum is not None:assert len(cases)==minimum
    rows.append({'driver':name,'source_sha256':sha(source.read_bytes()),'passed':len(cases),'total':len(cases),'exit':result.returncode,'scope':'Offline VM only; no real transport/browser/PG.'})
assert sum(r['passed'] for r in rows[3:7])==74
after=photo('node-after');assert before==after and sha(NODE.read_bytes())==node_sha
outputs=[publish(path,'node-'+path.name) for path in sorted(phase.iterdir()) if path.is_file()]
save('node-result.json',{'head':HEAD,'drivers':rows,'assertion_executions':sum(r['passed'] for r in rows),'retained_transport_assertions':74,'new_emitter':11,'expiry':3,'followup':20,'security_frozen':10,'sources_packages_helpers_stable':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'node_sha256':node_sha,'outputs':outputs})
print(json.dumps({'passed':sum(r['passed'] for r in rows),'drivers':len(rows),'legacy':74,'new':34,'SEC':10,'sources':before['source_count'],'packages':89,'stable':True}))
