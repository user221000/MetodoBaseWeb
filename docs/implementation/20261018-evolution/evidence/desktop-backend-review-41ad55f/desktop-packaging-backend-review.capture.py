import hashlib,json,subprocess
from pathlib import Path
root=Path.cwd()
out=Path(r"C:\Users\Consu\AppData\Local\Temp\metodobase-desktop-backend-review-20261019-c3465452")
before=json.loads((out/"desktop-packaging-backend-review.before.json").read_text(encoding="utf-8-sig"))
records=[{"path":row["path"],"sha256":hashlib.sha256((root/row["path"]).read_bytes()).hexdigest()} for row in before["sources"]]
changed=[row["path"] for row,old in zip(records,before["sources"]) if row["sha256"]!=old["sha256"]]
report={"commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
    "status":subprocess.check_output(["git","status","--porcelain"],text=True).splitlines(),
    "source_count":len(records),"source_stable":not changed,"changed_sources":changed,"sources":records,
    "source_digest":hashlib.sha256(json.dumps(records,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
    "tests":{"passed":58,"seconds":7.02,"no_build_no_gui":True},
    "finding":{"priority":"P1","file":"build.py","line":252,"issue":"Source guard accepts modified tracked bytes hidden by assume-unchanged/skip-worktree",
        "reproduced_variants":2,"live_incident_claimed":False},
    "probes":[{"path":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(out.glob("desktop-packaging-backend-review.provenance.*"))]}
assert report["source_stable"] and report["source_count"]==19 and not report["status"]
assert report["commit"]=="41ad55f1a238422a2f7c86a64ad2469977e7ff8a"
(out/"desktop-packaging-backend-review.after.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["commit","source_count","source_stable","changed_sources","source_digest","tests"]}))
