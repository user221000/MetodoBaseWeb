import hashlib, importlib.util, json, os
from pathlib import Path
import subprocess, sys, tempfile
import xml.etree.ElementTree as ET

sys.dont_write_bytecode=True
SOURCE=Path(r"F:\MetodoBaseWeb-desktop-20261019")
OUT=Path(r"C:\Users\Consu\AppData\Local\Temp\metodobase-desktop-backend-review-20261019-c3465452")
spec=importlib.util.spec_from_file_location("desktop_filter_probe",SOURCE/"build.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
environment={k:v for k,v in os.environ.items() if not k.upper().startswith("GIT_")}
def git(root,*args):
    return subprocess.run(["git","-C",str(root),*args],env=environment,capture_output=True,text=True,check=True).stdout
with tempfile.TemporaryDirectory(prefix="metodobase-desktop-filter-probe-") as temporary:
    parent=Path(temporary)
    root=parent/"source"
    root.mkdir()
    git(root,"init","-q")
    cleaner=parent/"synthetic_clean_filter.py"
    cleaner.write_text("import sys\nsys.stdout.buffer.write(sys.stdin.buffer.read())\n",encoding="utf-8")
    # Executed only by this synthetic repository's Git filter; never product code.
    command='"'+sys.executable.replace("\\","/")+'" "'+str(cleaner).replace("\\","/")+'"'
    git(root,"config","filter.review.clean",command)
    (root/".gitattributes").write_text("main.py filter=review\n",encoding="utf-8")
    committed=b"# committed synthetic code\n"
    (root/"main.py").write_bytes(committed)
    git(root,"add",".")
    git(root,"-c","user.name=Packaging Review","-c","user.email=packaging-review@example.invalid","commit","-qm","Synthetic filtered source")
    head=git(root,"rev-parse","HEAD").strip()
    cleaner.write_text("import sys\nsys.stdin.buffer.read()\nsys.stdout.buffer.write("+repr(committed)+")\n",encoding="utf-8")
    (root/"main.py").write_bytes(b"# different unreviewed code; never executed\n")
    module.BASE_DIR=root
    accepted=True
    try:
        snapshot=module.source_snapshot(head)
    except module.BuildError:
        snapshot={}
        accepted=False
    report={"scope":"Temporary Git repo only; local synthetic clean filter; no build/GUI",
        "git_flags":git(root,"ls-files","-v").splitlines(),
        "status_clean":not git(root,"status","--porcelain","--untracked-files=all").strip(),
        "source_guard_accepted":accepted,"committed_sha256":hashlib.sha256(committed).hexdigest(),
        "working_sha256":hashlib.sha256((root/"main.py").read_bytes()).hexdigest(),
        "recorded_sha256":snapshot.get("main.py")}
(OUT/"desktop-packaging-backend-review.filter-provenance.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
summaries=[]
for path in sorted((SOURCE/"docs/implementation/20261018-evolution/evidence").glob("pytest-desktop-packaging*.xml")):
    tree=ET.fromstring(path.read_bytes())
    summaries.append({"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "suites":[dict(node.attrib) for node in tree.iter("testsuite")],
        "failures":[{"name":case.attrib.get("name"),"messages":[(failure.attrib.get("message") or "")[:250] for failure in case.findall("failure")]}
                    for case in tree.iter("testcase") if case.find("failure") is not None]})
(OUT/"desktop-packaging-backend-review.xml-artifacts.json").write_text(json.dumps(summaries,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"filter_probe":report,"xml_artifacts_examined":len(summaries)},indent=2))
