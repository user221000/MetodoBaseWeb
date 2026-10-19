from pathlib import Path
import os,sys,json,hashlib,subprocess,importlib.metadata,time
root=Path("F:/mb-followup34-20261019");out=Path(__file__).parent
os.chdir(root);sys.path.insert(0,str(root));sys.dont_write_bytecode=True
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
def snap():
    files=subprocess.check_output(["git","--no-replace-objects","ls-files","-co","--exclude-standard","-z"],cwd=root).decode().split("\0")
    source={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sorted(set(files)) if name and (root/name).is_file() and not name.startswith("docs/") and name!="followup34-author-temp.json"}
    packages={d.metadata["Name"]:{"version":d.version,"metadata_sha256":hashlib.sha256((d.read_text("METADATA") or "").encode()).hexdigest()} for d in importlib.metadata.distributions()}
    return {"source":source,"packages":packages,"python":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(sys.executable),Path(sys._base_executable))}}
def save(name,value):
    with (out/name).open("x",encoding="utf-8") as f:json.dump(value,f,indent=2,sort_keys=True)
before=snap();save("sqlite-final-before.json",before)
pip1=subprocess.run([sys.executable,"-m","pip","check"],capture_output=True,text=True);save("sqlite-final-pip-before.json",{"returncode":pip1.returncode,"output":pip1.stdout})
import pytest
started=time.time()
code=pytest.main(["tests/test_followup34_http.py","tests/test_followup34_boundaries.py","tests/test_followup34_domain.py","tests/test_followup34_mechanisms.py","tests/test_followup34_races.py","tests/integration_followup34_migrations.py","-k","not postgresql","-q","--tb=short","--maxfail=1","--junitxml="+str(out/"sqlite-final.xml"),"-o","cache_dir="+str(out/"pytest-final-cache")])
after=snap();save("sqlite-final-after.json",after)
pip2=subprocess.run([sys.executable,"-m","pip","check"],capture_output=True,text=True);save("sqlite-final-pip-after.json",{"returncode":pip2.returncode,"output":pip2.stdout})
save("sqlite-final-receipt.json",{"exit_code":code,"duration_seconds":time.time()-started,"source_count":len(before["source"]),"package_count":len(before["packages"]),"quiet":before==after,"pip_before":pip1.returncode,"pip_after":pip2.returncode,"scope":"75 author SQLite cases, 5 PostgreSQL deselected; no PostgreSQL connection"})
raise SystemExit(code)
