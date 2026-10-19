import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
SOURCE = Path(r"F:\MetodoBaseWeb-desktop-20261019")
OUT = Path(r"C:\Users\Consu\AppData\Local\Temp\metodobase-desktop-backend-review-20261019-c3465452")
spec = importlib.util.spec_from_file_location("desktop_backend_probe", SOURCE / "build.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
environment = {k:v for k,v in os.environ.items() if not k.upper().startswith("GIT_")}
def git(root, *args):
    return subprocess.run(["git","-C",str(root),*args],env=environment,capture_output=True,check=True,text=True).stdout

reports=[]
for mode in ("assume-unchanged","skip-worktree"):
    with tempfile.TemporaryDirectory(prefix="metodobase-desktop-provenance-probe-") as temporary:
        root=Path(temporary)
        git(root,"init","-q")
        (root/"main.py").write_text("# committed synthetic code\n",encoding="utf-8")
        git(root,"add","main.py")
        git(root,"-c","user.name=Packaging Review","-c","user.email=packaging-review@example.invalid","commit","-qm","Synthetic source boundary")
        head=git(root,"rev-parse","HEAD").strip()
        committed=git(root,"show","HEAD:main.py").encode()
        git(root,"update-index","--"+mode,"main.py")
        (root/"main.py").write_text("# different unreviewed code; never executed\n",encoding="utf-8")
        module.BASE_DIR=root
        status=git(root,"status","--porcelain","--untracked-files=all")
        accepted=True
        try:
            snapshot=module.source_snapshot(head)
        except module.BuildError:
            accepted=False
            snapshot={}
        reports.append({"git_index_mode":mode,"status_clean":not status.strip(),"source_guard_accepted":accepted,
            "head_commit":head,"committed_sha256":hashlib.sha256(committed).hexdigest(),
            "working_sha256":hashlib.sha256((root/"main.py").read_bytes()).hexdigest(),
            "recorded_sha256":snapshot.get("main.py")})
(OUT/"desktop-packaging-backend-review.provenance.json").write_text(json.dumps(reports,indent=2)+"\n",encoding="utf-8")
print(json.dumps(reports,indent=2))
