import json,os,sys
from pathlib import Path
value=json.loads(Path(os.environ['CI_TEMPLATE']).read_bytes())
kind,target=sys.argv[1:3]
if kind=='marker':
    data=value['marker'];data['pid']=int(sys.argv[3])
    Path(target).write_text(json.dumps(data),encoding='utf8')
else:
    Path(target,'report.json').write_text(json.dumps(value['report']),encoding='utf8')
