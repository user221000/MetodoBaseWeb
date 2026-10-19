from support import *
NODE=Path('C:/Program Files/nodejs/node.exe');phase=TEMP/'node';phase.mkdir();before=photo('node-before');outputs=[];rows=[]
for name,count in [('daily_plan_data',23),('daily_plan_controls',17),('daily_plan_snapshot',25)]:
    result=subprocess.run([str(NODE),str(ROOT/('tests/e2e/'+name+'.cjs'))],cwd=ROOT,capture_output=True,timeout=60)
    (phase/(name+'.json')).write_bytes(result.stdout);(phase/(name+'.stderr.log')).write_bytes(result.stderr)
    data=json.loads(result.stdout);assert result.returncode==0 and len(data['results'])==count and all(r['passed']is True for r in data['results'])
    rows.append({'module':name,'exit':result.returncode,'assertion_executions':count})
after=photo('node-after');assert before==after
for p in sorted(phase.iterdir()):outputs.append(publish(p,'node-'+p.name))
save('node-result.json',{'head':HEAD,'modules':rows,'executions':65,'new_criteria':47,'legacy18_reexecuted_and_declared':True,'no_global_dedup_claim':True,'sources':before['source_count'],'packages':89,'stable':True,'outputs':outputs,'scope':'Pure and controlled DOM VM; no HTTP/browser/network.'})
print(json.dumps({'modules':3,'executions':65,'new':47,'legacy':18,'sources':before['source_count'],'packages':89,'stable':True}))
