import json,sys
from pathlib import Path
p,mode,n,screens,kind=sys.argv[1:];n=int(n);screens=int(screens)
if mode=='missing-report':sys.exit(0)
if mode=='too-few':n-=1
if mode=='no-screens':screens=0
checks=[{'name':str(i),'passed':True} if kind=='named' else str(i) for i in range(n)]
r={'checks':checks,'pageErrors':['synthetic'] if mode=='page-error' else [],'screens':[str(i) for i in range(screens)]}
Path(p).parent.mkdir(parents=True,exist_ok=True)
Path(p).write_text(json.dumps(r))
