from pathlib import Path
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp');source=tmp/'metodobase-main30-regression.py';text=source.read_text()
pairs=[('metodobase-main30-regression-first-20261019','metodobase-main-r23-r24-regression-first-20261019'),('6d4e8b411a3f55dde0df250225b506e35f1f57e9','eea8f773fba9b7f92241958139fcefa23b9ee1d4'),('timeout=900','timeout=1200'),("'No PG/Redis/Linux/Actions/image claim.'","'No PG/Redis/Linux/Actions/image claim.'")]
for old,new in pairs:
    assert old in text or old==new
    text=text.replace(old,new)
needle="    result=subprocess.run(command,cwd=root,env=environment,capture_output=True,timeout=1200)"
replacement="""    timed_out=False
    try:
        result=subprocess.run(command,cwd=root,env=environment,capture_output=True,timeout=1200)
    except subprocess.TimeoutExpired as error:
        timed_out=True
        result=subprocess.CompletedProcess(command,None,error.stdout or b'',error.stderr or b'')"""
assert text.count(needle)==1;text=text.replace(needle,replacement)
text=text.replace("'exit':result.returncode,'seconds':", "'exit':result.returncode,'timed_out':timed_out,'seconds':")
text=text.replace("Both required broad SaaS modes on merged schema30", "Both required broad SaaS modes on merged R23/R24/SEC11 schema30")
text+='''
assert coverage.returncode==0
for result in results:
    assert result['exit']==0 and not result['timed_out'] and not result['failures'],result['mode']
    assert result['cases']>=2492 and len(result['skips'])==1,result['mode']
baseline=out.parent/'metodobase-main30-regression-first-20261019'
preservation={}
for mode in ['serial','shuffle']:
    def ids(folder):
        return {(case.get('classname'),case.get('name')) for case in ET.parse(folder/(mode+'.xml')).findall('.//testcase')}
    previous=ids(baseline);current=ids(out);missing=previous-current
    preservation[mode]={'baseline_unique_ids':len(previous),'current_unique_ids':len(current),'missing':sorted(missing)}
(out/'baseline-case-preservation.json').write_text(json.dumps(preservation,indent=2)+'\\n',encoding='utf8')
assert all(not row['missing'] for row in preservation.values())
'''
target=tmp/'metodobase-main-r23-r24-regression.py';assert not target.exists();target.write_bytes(text.encode());print('Prepared new composed-source broad regression driver; old gate unchanged.')
