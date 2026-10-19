"""Capture raw own runtime review output without PowerShell stream conversion."""
from run_bundle51 import *
with (OUT/'runtime-v2-original.log').open('xb') as stream:
    result=subprocess.run([sys.executable,'-X','utf8','-B',str(OUT/'review_runtime_v2.py')],
                          cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=180,
                          env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',PYTHONUTF8='1'))
print(json.dumps({'runtime_v2_exit':result.returncode}))
raise SystemExit(result.returncode)
