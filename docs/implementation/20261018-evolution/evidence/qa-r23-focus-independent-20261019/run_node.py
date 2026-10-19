"""Focal20+4 maintained and six own intent/session/focus lifecycle checks."""
from support import *
NODE=Path('C:/Program Files/nodejs/node.exe');before=photo('node-before');phase=TEMP/'node';phase.mkdir(exist_ok=False)
node_sha=sha(NODE.read_bytes());assert node_sha=='ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32'
rows=[]
for name,path,count in [('dashboard20',ROOT/'tests/e2e/dashboard_followup.cjs',20),('focus4',ROOT/'tests/e2e/dashboard_followup_focus.cjs',4),('own6',OUT/'own_focus_controls.cjs',6)]:
    env=dict(os.environ,QA_FOCUS_ROOT=str(ROOT),FOLLOWUP_FOCUS_SOURCE=str(ROOT/'web/static/js/dashboard-seguimiento.js'))
    result=subprocess.run([str(NODE),str(path)],cwd=ROOT,env=env,capture_output=True,timeout=45)
    (phase/(name+'.json')).write_bytes(result.stdout);(phase/(name+'.stderr.log')).write_bytes(result.stderr)
    report=json.loads(result.stdout);assert result.returncode==0 and report['passed']==report['total']==count and all(row['passed'] is True for row in report['results'])
    rows.append({'name':name,'passed':count,'total':count,'exit':result.returncode,'source_sha256':sha(path.read_bytes())})
after=photo('node-after');assert before==after and sha(NODE.read_bytes())==node_sha
outputs=[publish(path,'node-'+path.name) for path in sorted(phase.iterdir()) if path.is_file()]
save('node-result.json',{'head':HEAD,'drivers':rows,'assertion_executions':30,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'stable':True,'node_sha256':node_sha,'outputs':outputs,'scope':'Only offline DOM/consumer checks; no HTTP53, PG2, original browser8 or R12 16 rerun.'})
print(json.dumps({'head':HEAD,'passed':30,'maintained':24,'own':6,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'stable':True}))
