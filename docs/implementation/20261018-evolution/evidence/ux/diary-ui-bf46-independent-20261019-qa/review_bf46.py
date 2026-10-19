"""Independent own-fixture browser and VM review for the frozen UI bf46."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler

ROOT = Path(r"F:\MetodoBaseWeb-diary-ui-20261019")
MAIN = Path(r"F:\MetodoBaseWeb-execution-20261018")
CODEDIR = Path(__file__).resolve().parent
OUT = Path(os.environ.get("QA_BF46_OUTPUT", str(CODEDIR)))
OUT.mkdir(parents=True, exist_ok=True)
MANIFEST = ROOT / "docs/implementation/20261018-evolution/evidence/ux/diary-ui-controls-fix-source.json"
PYTHON = Path(r"C:\Users\Consu\AppData\Local\Temp\metodobase-candidate-web-20261018\Scripts\python.exe")
BASE_PYTHON = Path(r"C:\Users\Consu\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\python.exe")
PORT = 8789
BASE = "http://127.0.0.1:8789"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def text(name, value):
    with (OUT / name).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def ps(command):
    result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def process(identity):
    if identity is None:
        return None
    result = ps("$OutputEncoding=[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); Get-CimInstance Win32_Process -Filter 'ProcessId = " + str(identity) + "' | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Compress")
    return None if not result else json.loads(result)


def listener(port):
    result = ps("Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object LocalPort -eq " + str(port) + " | Select-Object -ExpandProperty OwningProcess | ConvertTo-Json -Compress")
    return None if not result else json.loads(result)


def write_adapted(name, original, replacements):
    source = original.read_bytes().decode("utf-8")
    modified = source
    for old, new, expected in replacements:
        assert modified.count(old) == expected, (name, old, modified.count(old), expected)
        modified = modified.replace(old, new)
    recovered = modified
    for old, new, _ in reversed(replacements):
        recovered = recovered.replace(new, old)
    assert recovered == source, "Adaptation altered more than declared port/directory literals"
    target = OUT / name
    with target.open("xb") as stream:
        stream.write(modified.encode("utf-8"))
    return {"original_path": str(original), "original_sha256": sha(original), "adapted_path": str(target),
            "adapted_sha256": sha(target), "exact_reversal_proved": True,
            "changes": [{"old": old, "new": new, "count": count} for old, new, count in replacements]}


assert sha(MANIFEST) == "cfecc433a12a796cf7014a62311002535cb82fd787a90e62a8c76cbcba19ef7d"
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
expected = {name: data["sha256"] for name, data in manifest["sources"].items()}
expected.update(manifest["read_only_dependencies"])
assert len(expected) == 57
assert {name: sha(ROOT / name) for name in expected} == expected
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
assert head == "bf46e163f82a318873c4da6b460609520eb80d85"
save("source-before.json", expected)
own_historical = MAIN / "docs/implementation/20261018-evolution/evidence/ux/diary-ui-independent-20261019-qa/own-browser-review.cjs"
assert sha(own_historical) == "4fec8cb6be582ed449cae33bc94b3313a3ff524700e7d0604b49a1697a41d143"
historical_proofs = MAIN / "docs/implementation/20261018-evolution/evidence/ux/diary-ui-independent-20261019-qa"
historical_hashes = {path.name: sha(path) for path in historical_proofs.iterdir() if path.is_file()}
save("historical-proofs-before.json", historical_hashes)
foreign_before = {str(port): process(listener(port)) for port in (8776, 8777)}
assert listener(PORT) is None, "Own fixture port is already occupied"
with socket.socket() as probe:
    probe.bind(("127.0.0.1", PORT))
save("foreign-processes-before.json", foreign_before)
adaptations = {}
fixture = ROOT / "tests/e2e/personal_diary_server.py"
adaptations["server"] = write_adapted("server-adapted.py", fixture, [("http://127.0.0.1:8776", BASE, 1), ("port=8776", "port=8789", 1)])
server_script = "from pathlib import Path\nsource=Path(" + repr(str(OUT / "server-adapted.py")) + ").read_bytes().decode('utf-8')\nexec(compile(source," + repr(str(fixture)) + ",'exec'),{'__file__':" + repr(str(fixture)) + ",'__name__':'__main__'})\n"
text("run_server.py", server_script)
for label, filename, old_base, count, output_literal in [
    ("browser-replay", "personal_diary.cjs", "http://127.0.0.1:8776", 2,
     "path.resolve(__dirname,'../../docs/implementation/20261018-evolution/evidence/ux/diary-ui-browser-'+(process.env.METODOBASE_EVIDENCE_BATCH||new Date().toISOString().replace(/\\D/g,'')))"),
    ("browser-author4", "personal_export_context_browser.cjs", "http://127.0.0.1:8777", 1,
     "path.resolve(__dirname,'../../docs/implementation/20261018-evolution/evidence/ux/diary-ui-consumer-fix-browser-'+(process.env.METODOBASE_EVIDENCE_BATCH||Date.now()))"),
]:
    target = OUT / label
    target.mkdir()
    adaptations[label] = write_adapted(label + "-adapted.cjs", ROOT / "tests/e2e" / filename,
                                      [(old_base, BASE, count), (output_literal, json.dumps(str(target)), 1)])
(OUT / "browser-own4").mkdir()
adaptations["browser-own4"] = write_adapted("browser-own4-adapted.cjs", own_historical,
    [("http://127.0.0.1:8778", BASE, 1), ("out=__dirname", "out=" + json.dumps(str(OUT / "browser-own4")), 1)])
save("adaptations.json", adaptations)
environment = dict(os.environ, NODE_PATH=str(MAIN / "tests/e2e/node_modules"), CHROME_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe")
vm_names = ["auth_refresh", "auth_refresh_storage", "auth_refresh_security_review", "auth_refresh_race_review",
            "personal_logout", "personal_diary_controller", "personal_diary_api", "personal_operation",
            "personal_operation_ambiguity_review", "personal_export_context", "personal_logout_ack", "personal_export_controls"]
vm = []
for name in vm_names:
    started = time.monotonic()
    result = subprocess.run(["node", "tests/e2e/" + name + ".cjs"], cwd=ROOT, env=environment, capture_output=True, encoding="utf-8", timeout=60)
    text(name + ".log", result.stdout + result.stderr)
    body = json.loads(result.stdout)
    total = body.get("total", len(body.get("report", [])))
    passed = body.get("passed", sum(row["passed"] for row in body.get("report", [])))
    assert result.returncode == 0 and passed == total, (name, passed, total)
    vm.append({"test": name, "passed": passed, "total": total, "exit": result.returncode, "seconds": round(time.monotonic() - started, 3)})
assert sum(row["total"] for row in vm) == 179
assert vm[-1]["total"] == 21 and vm[-3]["total"] == 17
save("vm-results.json", {"observations": 179, "unique_cases": 162, "reused_in_controls_driver": 17, "results": vm})
print("VM: 162 unique cases passed; 179 observations including 17 reused controls cases", flush=True)
server = None
owned = None
startup = None
browser_results = []
closed = False
failure = None
server_log = (OUT / "server.log").open("xb")
try:
    server = subprocess.Popen([str(PYTHON), "-X", "utf8", str(OUT / "run_server.py")], cwd=ROOT, env=environment, stdout=server_log, stderr=subprocess.STDOUT)
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, message, headers, newurl):
            raise HTTPError(request.full_url, code, "Own fixture redirect rejected", headers, fp)
    opener = build_opener(ProxyHandler({}), NoRedirect())
    for _ in range(160):
        assert server.poll() is None, "Own fixture exited before readiness"
        lines = (OUT / "server.log").read_bytes().decode("utf-8").splitlines()
        for line in lines:
            if line.startswith('{"fixture": "personal-diary-ui"'):
                startup = json.loads(line)
        if startup:
            with opener.open(BASE + "/health/ready", timeout=2) as response:
                assert response.status == 200
            break
        time.sleep(0.1)
    assert startup and startup["tables"] == 26 and startup["model_target_revision"] == "20261019_personal_diary"
    owned_pid = listener(PORT)
    owned = process(owned_pid)
    assert owned and owned["ProcessId"] == owned_pid
    assert owned["ProcessId"] == server.pid or owned["ParentProcessId"] == server.pid
    assert str(OUT / "run_server.py").lower() in owned["CommandLine"].lower()
    assert Path(owned["ExecutablePath"]).resolve() in {PYTHON.resolve(), BASE_PYTHON.resolve()}
    save("server-process-identity.json", {"launcher_pid": server.pid, "listener": owned})
    save("server-startup.json", startup)
    print("Own fixture8789 ready; metadata-only26 tables and real VIEWER HTTP registration", flush=True)
    for label, filename in [("browser-replay", "personal_diary.cjs"), ("browser-author4", "personal_export_context_browser.cjs"), ("browser-own4", None)]:
        started = time.monotonic()
        output = OUT / label
        env = dict(environment, QA_BROWSER_OUTPUT=str(output), QA_DRIVER_SOURCE=str(OUT / (label + "-adapted.cjs")),
                   QA_DRIVER_FILENAME=str(ROOT / "tests/e2e" / filename) if filename else str(output / "own-browser-review.cjs"))
        result = subprocess.run(["node", str(CODEDIR / "browser_network_guard.cjs")], cwd=ROOT, env=env, capture_output=True, encoding="utf-8", timeout=180)
        text(label + ".log", result.stdout + result.stderr)
        report_path = output / ("own-browser-report.json" if label == "browser-own4" else "report.json")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        browser_results.append({"group": label, "exit": result.returncode, "checks": len(report["checks"]),
                                "passed": report.get("passed"), "screens": len(report.get("screens", [])),
                                "page_errors": report["pageErrors"], "seconds": round(time.monotonic() - started, 3)})
        save(label + "-result.json", browser_results[-1])
        assert result.returncode == 0 and report.get("passed") is True, (label, report.get("error"))
        assert len(report["checks"]) == (17 if label == "browser-replay" else 4)
        assert report["pageErrors"] == []
        print(label + ": " + str(len(report["checks"])) + " passed", flush=True)
except BaseException as error:
    failure = {"class": type(error).__name__, "detail": str(error)}
finally:
    if owned:
        current = process(owned["ProcessId"])
        assert current == owned, "Own process fingerprint changed before shutdown"
        ps("Stop-Process -Id " + str(owned["ProcessId"]) + " -ErrorAction Stop")
    if server:
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            own_parent = process(server.pid)
            assert str(OUT / "run_server.py").lower() in own_parent["CommandLine"].lower()
            server.terminate()
            server.wait(timeout=10)
    server_log.close()
    closed = listener(PORT) is None
    foreign_after = {str(port): process(listener(port)) for port in (8776, 8777)}
    save("foreign-processes-after.json", foreign_after)
    after = {name: sha(ROOT / name) for name in expected}
    save("source-after.json", after)
    historical_after = {path.name: sha(path) for path in historical_proofs.iterdir() if path.is_file()}
    save("historical-proofs-after.json", historical_after)
    runtime_changes = [] if startup is None else [name for name, digest in startup["sources"].items() if sha(ROOT / name) != digest]
    summary = {"head": head, "manifest_sha256": sha(MANIFEST), "status": "accepted" if failure is None else "blocked",
               "sources": len(expected), "sources_unchanged": after == expected, "runtime_changes": runtime_changes,
               "historical_proofs_unchanged": historical_after == historical_hashes,
               "own_port": PORT, "own_listener_closed": closed, "foreign_processes_unchanged": foreign_before == foreign_after,
               "vm_unique": 162, "vm_observations": 179, "browser": browser_results, "failure": failure,
               "scope": "Own temporary metadata-only SQLite, no-send welcome boundary, Python external-socket guard; browser/API exact origin and redirect0. No PG, Alembic, provider, OS network sandbox, Linux, Actions or integration claim."}
    save("diary-ui-bf46-independent-source.json", summary)
    assert after == expected and runtime_changes == [] and historical_after == historical_hashes
    assert closed and foreign_before == foreign_after
if failure:
    raise AssertionError(failure)
print(json.dumps({"accepted": True, "browser_groups": sum(row["checks"] for row in browser_results),
                  "vm_unique": 162, "source_report_sha256": sha(OUT / "diary-ui-bf46-independent-source.json")}))
