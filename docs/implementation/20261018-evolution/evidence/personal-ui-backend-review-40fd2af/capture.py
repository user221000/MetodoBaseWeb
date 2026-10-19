import hashlib,json,subprocess
from pathlib import Path
root=Path.cwd()
out=Path(r"C:\Users\Consu\AppData\Local\Temp\metodobase-personal-ui-backend-review-20261019")
before=json.loads((out/"personal-ui-backend-review.before.json").read_text(encoding="utf-8-sig"))
records=[{"path":row["path"],"sha256":hashlib.sha256((root/row["path"]).read_bytes()).hexdigest()} for row in before["sources"]]
assert records==before["sources"]
base=subprocess.check_output(["git","show","6d33b9e:web/services/generation_quota.py"]).decode().replace("\r\n","\n")
current=(root/"web/services/generation_quota.py").read_text(encoding="utf-8").replace("\r\n","\n")
assert base.split("def _lock_account",1)[1]==current.split("def _lock_account",1)[1]
report={"commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"status":subprocess.check_output(["git","status","--porcelain"],text=True).splitlines(),
    "sources":records,"source_stable":True,"quota_lock_compensation_suffix_unchanged":True,
    "tests":{"directed_passed":42,"directed_seconds":7.30,"query_probe_passed":1,"query_probe_seconds":3.67,
        "query_counts_with_1_and_25_plans":[2,2]},
    "findings":[],"limits":["History pagination remains explicitly deferred; no new DB/DDL/provider behavior claimed","GUI/browser not rerun by this backend-only review"]}
assert report["commit"]=="40fd2af0bb73326181093e59e9d3f3e6f5fbd441" and not report["status"]
(out/"personal-ui-backend-review.after.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"source_stable":True,"quota_suffix_unchanged":True,"sources":len(records),"tests":report["tests"]}))
