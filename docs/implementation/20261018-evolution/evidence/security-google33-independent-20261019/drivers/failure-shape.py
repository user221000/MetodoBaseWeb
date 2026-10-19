from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET
p=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-google33-peer-private-20261019/pg-functional.xml')
for case in ET.parse(p).findall('.//testcase'):
    failure=case.find('failure')
    if failure is None:continue
    m=failure.get('message','');text=failure.text or ''
    print(json.dumps({'case':case.get('name'),'message_sha256':hashlib.sha256(m.encode()).hexdigest(),'line_count':len(m.splitlines()),'exception_types':re.findall(r'\b([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception))\b',m),'code_states':re.findall(r'\b(?:42501|55P03|23505|23503|0A000)\b',m),'static_assert_lines':[line for line in text.splitlines() if line.lstrip().startswith('assert ') and not re.search('credential|intent|token|password',line,re.I)],'timeout_or_barrier':'BrokenBarrier' in m or 'timeout' in m.lower(),'session_variable_error':"'NoneType'" in m}))
