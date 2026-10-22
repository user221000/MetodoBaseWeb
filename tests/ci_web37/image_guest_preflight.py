"""Read the already leased owned guest; never start, upload, build or clean."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.scan_secrets import _private_evidence as private_directory
from tests.ci_web37.evidence import boundary_before_payload, seal, write

LAB = Path("F:/MetodoBaseWeb-linux-lab-20261019")
SOURCE = "f0608fb086b08bbd59ce595e9a906c58308d3328"
CONTEXT_SHA256 = "9e9655e4ead53e579bd9c23f13bdf43c395c174c8c2e30ad29e441f5740d0f01"
CACHE_TAG = "metodobase-lab:expat-sec10-m2-72c44a1"
CACHE_ID = "sha256:a2b7e06ec1971f6519395aa1cd08c54f6d18c2bf26749abf3d65513f86337e7f"
LAB_HELPERS = {
    "lab_control": "b5729b9ad3746bc9d18fc50f8ed14ad5acb2015326a8b9f856aadb745d1cf7d0",
    "guest_access": "616b66b791140966dac837fbd58808291b165d4ae06011a1395279462f43b7a7",
}


def load(name):
    path = LAB / "scripts" / (name + ".py")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LAB_HELPERS[name]:
        raise ValueError("The reviewed owned lab access helper differs")
    module = ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)  # noqa: S102
    return module


def validate_guest(value):
    if (value["system"] != "Linux" or value["machine"] != "x86_64"
            or type(value["free_bytes"]) is not int or value["free_bytes"] < 2500 * 1024 * 1024
            or type(value["mem_available_KiB"]) is not int or value["mem_available_KiB"] < 1024 * 1024
            or value["running_containers"] != [] or value["cached_native_image_id"] != CACHE_ID):
        raise ValueError("The fresh guest resource/cache contract differs; no build is authorized")
    return {key: value[key] for key in ("system", "machine", "free_bytes", "mem_available_KiB",
                                      "running_containers", "cached_native_image_id")}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context-manifest", type=Path, required=True)
    parser.add_argument("--authorized-read-only-preflight", action="store_true", required=True)
    args = parser.parse_args()
    private = private_directory(args.private)
    acl = boundary_before_payload(private)
    manifest = json.loads(args.context_manifest.read_bytes())
    archive = args.context_manifest.parent / "source-context.tar"
    if (manifest["source_commit"] != SOURCE or manifest["archive_sha256"] != CONTEXT_SHA256
            or manifest["current57_critical_inputs_exact"] != 12 or len(manifest["files"]) != 469
            or manifest["runtime_distributions_expected"] != 57
            or hashlib.sha256(archive.read_bytes()).hexdigest() != CONTEXT_SHA256):
        raise ValueError("The prepared current37 source context differs")
    state = json.loads((LAB / "instance/state.json").read_bytes())
    if (state["resources"] != {"vcpus": 2, "memory_mib": 2048, "acceleration": "tcg,thread=multi"}
            or type(state["resources"]["vcpus"]) is not int or type(state["resources"]["memory_mib"]) is not int):
        raise ValueError("The leased VM resource definition differs")
    lifecycle = load("lab_control")
    if lifecycle.process_identity(state) is None:
        raise ValueError("The owned guest must already be started under a separate Root lease")
    guest_access = load("guest_access")
    remote = """import json,os,platform,subprocess
from pathlib import Path
def capture(argv):
    result=subprocess.run(argv,capture_output=True,text=True,check=True)
    return result.stdout
stats=os.statvfs('/var/lib/docker')
memory=dict((key,int(value.strip().split()[0])) for key,value in
    (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()))
images=json.loads(capture(['sudo','-n','docker','image','inspect','CACHE_TAG']))
assert len(images)==1
value={'system':platform.system(),'machine':platform.machine(),
    'free_bytes':stats.f_bavail*stats.f_frsize,'mem_available_KiB':memory['MemAvailable'],
    'running_containers':capture(['sudo','-n','docker','ps','-q']).splitlines(),
    'cached_native_image_id':images[0]['Id'],
    'docker_version':capture(['sudo','-n','docker','version','--format','{{.Server.Version}}']).strip(),
    'docker_space':capture(['sudo','-n','docker','system','df']),
    'lab_nonce':Path('/var/tmp/metodobase-lab-nonce').read_text().strip(),
    'source_transferred':False,'image_built':False}
print(json.dumps(value))
""".replace("CACHE_TAG", CACHE_TAG).encode()
    (private / "remote-readonly.py").write_bytes(remote)
    with (private / "remote-readonly.py").open("rb") as payload:
        result = guest_access.run("python3 -", stdin=payload, timeout=45)
    (private / "guest.stdout.private.json").write_bytes(result.stdout)
    (private / "guest.stderr.private.log").write_bytes(result.stderr)
    if result.returncode != 0:
        raise ValueError("The owned guest read-only preflight failed; originals retained")
    value = json.loads(result.stdout)
    if value["lab_nonce"] != state["nonce"]:
        raise ValueError("The SSH guest is not the owned leased instance")
    checked = validate_guest(value)
    result = {"scope": "read-only owned guest preflight; stop here before any build",
              "source_commit": SOURCE, "source_context_sha256": CONTEXT_SHA256,
              "runtime_distributions_expected": 57, "guest": checked,
              "VM_resources": state["resources"], "owned_PID": state["pid"],
              "VM_started_by_this_runner": False, "source_transferred": False,
              "image_built": False, "historical33_image_rebuilt": False,
              "SQL_Redis_Chrome_started": False, "build_authorized": False}
    write(private / "lifecycle-inputs.json", {"state_resources": state["resources"],
        "lab_control_sha256": hashlib.sha256((LAB / "scripts/lab_control.py").read_bytes()).hexdigest(),
        "guest_access_sha256": hashlib.sha256((LAB / "scripts/guest_access.py").read_bytes()).hexdigest()})
    print(json.dumps(seal(private, args.output, result, acl)))


if __name__ == "__main__":
    main()
