from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent
report=json.loads((root/'ci-desktop-routing-independent-source.json').read_text())
code=(root/'desktop_junit_guard_exact.py').read_text()
for case in report['desktopJUnitGuardCanaries']:
 result=subprocess.run([sys.executable,'-c',code],cwd=root/case['name'],capture_output=True)
 assert (result.returncode==0)==(case['exit']==0),case['name']
print('9 exact desktop JUnit guard canaries matched')
