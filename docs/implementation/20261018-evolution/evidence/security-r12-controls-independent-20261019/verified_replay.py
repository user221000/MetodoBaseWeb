from pathlib import Path
import json,subprocess,sys
HERE=Path(__file__).parent
cases=[('verified-qa3-before',['F:/mb-r12-controls-s/tests/e2e/member_link_controls.cjs','F:/mb-r12-last-s/web/static/js/vinculos-ui.js'],3,1,1),
    ('verified-qa3-after',['F:/mb-r12-controls-s/tests/e2e/member_link_controls.cjs','F:/mb-r12-controls-s/web/static/js/vinculos-ui.js'],3,3,0),
    ('verified-own-before',[str(HERE/'security_controls.cjs'),'F:/mb-r12-last-s'],12,0,1),
    ('verified-own-after',[str(HERE/'security_controls.cjs'),'F:/mb-r12-controls-s'],12,12,0),
    ('verified-old16-after',['F:/mb-r12-controls-s/tests/e2e/member_link_consumers.cjs'],16,16,0)]
summary=[]
for label,args,total,passed,expected_exit in cases:
    result=subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/'run.py'),label,*args],capture_output=True)
    (HERE/(label+'-runner.log')).write_bytes(result.stdout+result.stderr)
    report=json.loads((HERE/(label+'-safe.json')).read_bytes())
    assert report['total']==total and report['passed']==passed and report['exit']==expected_exit==result.returncode,label
    summary.append({'label':label,'total':total,'passed':passed,'expected_exit':expected_exit,'actual_exit':result.returncode})
(HERE/'verified-replay-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
print(json.dumps(summary))
