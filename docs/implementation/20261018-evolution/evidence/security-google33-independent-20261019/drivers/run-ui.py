from pathlib import Path
import hashlib,json,subprocess
R=Path(r'F:/mb-security-google33-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-google33-peer-private-20261019';O=R/'docs/implementation/20261018-evolution/evidence/security-google33-independent-20261019';node=Path(r'C:/Program Files/nodejs/node.exe');sha=lambda b:hashlib.sha256(b).hexdigest()
names=['tests/e2e/google_link_state.cjs','tests/e2e/google_link_api.cjs','tests/e2e/google_link_dom.cjs','tests/e2e/google_link_login_review.cjs','web/static/js/google-vinculo.js','web/static/js/google-vinculo-pagina.js','web/static/js/api.js','web/templates/cuenta_google.html']
before={n:sha((R/n).read_bytes()) for n in names};node_before=sha(node.read_bytes());reports=[]
for name in names[:4]+[str(T/'metodobase-sec-google33-peer-ui-20261019.cjs')]:
    label=Path(name).stem;run=subprocess.run([str(node),name],cwd=R,capture_output=True,timeout=60)
    (P/(label+'-stdout.RAW.log')).write_bytes(run.stdout);(P/(label+'-stderr.RAW.log')).write_bytes(run.stderr)
    parsed=json.loads(run.stdout);reports.append({'source':name,'exit':run.returncode,'report':parsed})
after={n:sha((R/n).read_bytes()) for n in names};assert before==after and node_before==sha(node.read_bytes())
report={'node_sha256':node_before,'node_version':subprocess.check_output([str(node),'--version']).decode().strip(),'sources':before,'source_and_binary_quiet':True,'artifacts':reports,'scope':'Synthetic Node VM controller/API/DOM doubles, not Chromium or live Google acceptance.'}
(O/'ui-node-replays.STRUCTURAL.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({'artifacts':len(reports),'exits':[r['exit'] for r in reports],'node_and_sources_quiet':True}));assert all(r['exit']==0 for r in reports)
