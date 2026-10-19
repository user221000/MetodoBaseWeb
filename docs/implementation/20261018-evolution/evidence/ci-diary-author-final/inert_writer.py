import json,sys
from pathlib import Path
p,kind,n,screens,bad=sys.argv[1:]
n=int(n);screens=int(screens)
r={'checks':[{'name':str(i)} if kind=='named' else str(i) for i in range(n)],'pageErrors':[],'screens':[str(i) for i in range(screens)]}
if bad=='malformed':Path(p).write_text('{');raise SystemExit(0)
if bad=='checks':r['checks'].pop()
if bad=='screens':r['screens'].pop()
Path(p).write_text(json.dumps(r))
