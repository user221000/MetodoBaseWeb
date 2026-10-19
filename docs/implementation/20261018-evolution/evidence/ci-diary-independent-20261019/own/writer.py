import json,sys
from pathlib import Path
p,kind,n,screens,fault=sys.argv[1:]
r={'checks':[{'name':'own-'+str(i)} if kind=='named' else 'own-'+str(i) for i in range(int(n))],'pageErrors':['synthetic'] if fault=='errors' else [],'screens':['own-'+str(i) for i in range(int(screens))]}
Path(p).write_text(json.dumps(r))
