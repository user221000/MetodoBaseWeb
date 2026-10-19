import json,sys
from pathlib import Path
path,kind,minimum,screens,bad=sys.argv[1:]
n=int(minimum)
report={'checks':['check-'+str(i) for i in range(n)],'pageErrors':[]}
if kind=='named':report['checks']=[{'name':name} for name in report['checks']]
if int(screens):report['screens']=['screen-'+str(i) for i in range(int(screens))]
if bad=='1':report['pageErrors']=['Synthetic failure']
Path(path).write_text(json.dumps(report),encoding='utf8')
