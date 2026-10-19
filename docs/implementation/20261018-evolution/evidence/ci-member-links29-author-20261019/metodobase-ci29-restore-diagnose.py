import json,re
from pathlib import Path
import xml.etree.ElementTree as ET
path=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-historical-restore-v2-20261019/tests.xml')
def safe(value):
    value=re.sub(r'postgres(?:ql)?(?:\+psycopg2)?://[^\s\]\)\"\']+','[WITHHELD_DATABASE_URL]',value)
    value=re.sub(r'[A-Za-z0-9_-]{30,}\.[a-f0-9]{64}','[WITHHELD_TOKEN]',value)
    return value
for case in ET.parse(path).findall('.//testcase'):
    for kind in ['failure','error']:
        value=case.find(kind)
        if value is not None:print(json.dumps({'test':case.get('name'),'kind':kind,'message':safe(value.get('message',''))[:1000],'trace':safe(value.text or '')[-5500:]},ensure_ascii=True))
