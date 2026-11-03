"""Scan the exact production image, including its measured embedded XML/SSL.

Private image/logs stay on the runner. Public results contain component names,
advisory identifiers and hashes only. Findings never become an implicit waiver.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import urllib.request
import uuid

TOOLS = {
    "syft": ("1.56.0", 31413058, "1c2493cfcf52d3367d6cb25780d9190c111c2219c34c820574c43e8bae15c528"),
    "grype": ("0.121.1", 32660292, "bc3ea3f9e6fd56ac781c08c6c5e614271b79f438200757f6932085c19b0a4657"),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    with path.open("x", encoding="utf8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def db_files(root):
    return {path.relative_to(root).as_posix(): {"bytes": path.stat().st_size, "sha256": sha(path)}
            for path in sorted(root.rglob("*")) if path.is_file()}


def validate_db(value, now):
    built = datetime.fromisoformat(value["built"].replace("Z", "+00:00"))
    age = (now - built).total_seconds()
    require(value.get("valid") is True and 0 <= age < 86400,
            "Vulnerability database must be valid and younger than24 hours")
    return age


def summary(value, exitcode):
    require(exitcode in (0, 2) and isinstance(value.get("matches"), list), "Scanner did not complete")
    rows = value["matches"]
    severities = Counter(row["vulnerability"]["severity"] for row in rows)
    high = any(severities[name] for name in ("High", "Critical"))
    ignored = value.get("ignoredMatches", [])
    require(isinstance(ignored, list), "Ignored-match inventory is absent or malformed")
    require((exitcode == 2) == high, "Scanner threshold status differs from its findings")
    return {"exitcode": exitcode, "matches": len(rows), "severity": dict(severities),
            "advisories": sorted({row["vulnerability"]["id"] for row in rows}),
            "packages": sorted({row["artifact"]["name"] for row in rows}),
            "findings": [{"package": row["artifact"]["name"], "version": row["artifact"].get("version"),
                          "type": row["artifact"].get("type"), "advisory": row["vulnerability"]["id"],
                          "severity": row["vulnerability"]["severity"],
                          "fix": row["vulnerability"].get("fix", {})} for row in rows],
            "ignored_matches": len(ignored), "added_exclusions": 0,
            "accepted": exitcode == 0 and not ignored}


def install_tool(name, root):
    version, size, expected = TOOLS[name]
    url = f"https://github.com/anchore/{name}/releases/download/v{version}/{name}_{version}_linux_amd64.tar.gz"
    with urllib.request.urlopen(url, timeout=90) as response:
        raw = response.read(size + 1)
    require(len(raw) == size and hashlib.sha256(raw).hexdigest() == expected, "Pinned scanner release differs")
    archive_path = root / (name + ".tar.gz")
    archive_path.write_bytes(raw)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        members = [member for member in archive if member.name == name]
        require(len(members) == 1 and members[0].isfile() and 0 < members[0].size < 200 * 1024**2,
                "Pinned scanner binary member differs")
        binary = archive.extractfile(members[0]).read(200 * 1024**2)
    require(len(binary) == members[0].size, "Scanner binary is truncated")
    target = root / name
    with target.open("xb") as stream:
        stream.write(binary)
    target.chmod(0o700)
    return target, {"version": version, "archive_sha256": expected, "binary_sha256": sha(target)}


NATIVE_PROBE = r'''import hashlib,json,os,re
from pathlib import Path
import pyexpat,_elementtree
from cryptography.hazmat.backends.openssl.backend import backend
from cryptography.hazmat.bindings import _rust
root=Path('/usr/local/share/metodobase/native-20261103')
provenance=json.loads((root/'build-provenance.json').read_bytes())
hashes={name:hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() for name,module in [('pyexpat',pyexpat),('_elementtree',_elementtree),('cryptography_rust',_rust)]}
assert os.getuid()==os.getgid()==999
assert pyexpat.EXPAT_VERSION=='expat_2.10.0'
for name in ('pyexpat','_elementtree'):
 assert provenance['artifacts'][name]['sha256']==hashes[name]
text=backend.openssl_version_text()
match=re.fullmatch(r'OpenSSL ([0-9]+\.[0-9]+\.[0-9]+)(?: .*)?',text)
assert match is not None
print(json.dumps(dict(uid=os.getuid(),expat='2.10.0',openssl=match.group(1),elf_sha256=hashes,build_provenance_sha256=hashlib.sha256((root/'build-provenance.json').read_bytes()).hexdigest())))
'''


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--source", required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    require(os.name == "posix" and os.environ.get("GITHUB_ACTIONS") == "true", "Owned Linux CI runner required")
    require(re.fullmatch("[0-9a-f]{40}", args.source) and re.fullmatch("sha256:[0-9a-f]{64}", args.image_id),
            "Exact source and image identities required")
    runner = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    for path in (args.private, args.output):
        require(path.is_absolute() and path.resolve() == path and path.is_relative_to(runner) and not path.exists(),
                "Fresh runner-owned evidence paths required")
    require(args.private != args.output and not args.output.is_relative_to(args.private)
            and not args.private.is_relative_to(args.output), "Public and private evidence must be separate")
    args.private.mkdir(mode=0o700)
    args.output.mkdir(mode=0o755)
    config = args.private / "empty-config.yaml"
    config.write_text("{}\n", encoding="utf8")
    cache = args.private / "grype-cache"
    env = dict({key: value for key, value in os.environ.items() if not key.startswith(("GRYPE_", "SYFT_"))},
               GRYPE_DB_CACHE_DIR=str(cache), GRYPE_CHECK_FOR_APP_UPDATE="false",
               SYFT_CHECK_FOR_APP_UPDATE="false", GRYPE_DB_AUTO_UPDATE="false")

    def command(label, command_args, *, accepted=(0,), timeout=600, stdout_path=None):
        out = stdout_path or args.private / (label + ".stdout")
        with out.open("xb") as stdout, (args.private / (label + ".stderr")).open("xb") as stderr:
            result = subprocess.run(command_args, stdout=stdout, stderr=stderr, env=env, timeout=timeout)
        require(result.returncode in accepted, "Image security command failed; original diagnostics retained privately")
        return result.returncode, out

    _, inspection = command("image", ["docker", "image", "inspect", args.image_id])
    image = json.loads(inspection.read_bytes())[0]
    require(image["Id"] == args.image_id and image["Config"]["Labels"]["org.opencontainers.image.revision"] == args.source,
            "Image source binding differs")
    require(shutil.disk_usage(args.private).free > image["Size"] + 8 * 1024**3, "Image and vulnerability DB disk reserve absent")
    tools, tools_metadata = {}, {}
    for name in TOOLS:
        tools[name], tools_metadata[name] = install_tool(name, args.private)
    tar = args.private / "image.private.tar"
    command("image-save", ["docker", "save", args.image_id], stdout_path=tar)
    with tarfile.open(tar, "r:") as archive:
        manifest = json.load(archive.extractfile("manifest.json"))
        require(len(manifest) == 1, "One actual Docker image is required")
        config_raw = archive.extractfile(manifest[0]["Config"]).read(2 * 1024**2)
        require("sha256:" + hashlib.sha256(config_raw).hexdigest() == args.image_id, "Saved image identity differs")
    sbom = args.private / "image.syft.json"
    command("syft", [str(tools["syft"]), "--config", str(config), "docker-archive:" + str(tar),
                     "--scope", "all-layers", "-o", "json=" + str(sbom)])
    require(sbom.is_file() and sbom.stat().st_size < 64 * 1024**2, "Bounded actual image SBOM missing")
    inventory = json.loads(sbom.read_bytes())
    require(isinstance(inventory.get("artifacts"), list) and inventory["artifacts"], "Empty image SBOM")
    owner = uuid.uuid4().hex
    cid = None
    cidfile = args.private / "native.cid"

    def inspect(label):
        require(isinstance(cid, str) and re.fullmatch("[a-f0-9]{64}", cid), "Owned container ID is malformed")
        _, path = command(label, ["docker", "container", "inspect", cid])
        item = json.loads(path.read_bytes())[0]
        require(item["Id"] == cid and item["Image"] == args.image_id
                and item["Config"]["Labels"]["metodobase.sca.owner"] == owner, "Container ownership differs")
        host = item["HostConfig"]
        require(host["ReadonlyRootfs"] is True and host["NetworkMode"] == "none" and host["CapDrop"] == ["ALL"]
                and host["SecurityOpt"] == ["no-new-privileges:true"] and host["Privileged"] is False
                and host["Memory"] == 512 * 1024**2 and host["NanoCpus"] == 1000000000 and host["PidsLimit"] == 128
                and item["Config"]["User"] == "999:999", "Native probe isolation differs")
        return item

    try:
        _, created = command("native-create", ["docker", "create", "--name", "metodobase-sca-" + owner,
            "--cidfile", str(cidfile),
            "--label", "metodobase.sca.owner=" + owner, "--network", "none", "--read-only", "--user", "999:999",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--memory", "512m", "--cpus", "1",
            "--pids-limit", "128", "--entrypoint", "python", args.image_id, "-I", "-B", "-c", NATIVE_PROBE])
        cid = created.read_text().strip()
        require(re.fullmatch("[a-f0-9]{64}", cid), "Owned container identity absent")

        inspect("native-before")
        _, result_path = command("native-start", ["docker", "start", "--attach", cid], timeout=90)
        native = json.loads(result_path.read_bytes())
        closed = inspect("native-closed")
        require(closed["State"]["Running"] is False and closed["State"]["ExitCode"] == 0
                and closed["State"]["OOMKilled"] is False, "Native probe failed to close normally")
    finally:
        if cid is None and cidfile.exists():
            require(cidfile.is_file() and not cidfile.is_symlink() and cidfile.stat().st_size <= 65,
                    "Owned CID recovery file differs")
            cid = cidfile.read_text().strip()
        if cid is not None:
            owned = inspect("native-cleanup")
            if owned["State"]["Running"]:
                command("native-stop", ["docker", "stop", "--time", "30", cid], timeout=60)
            command("native-remove", ["docker", "rm", cid])
    supplement = args.private / "native.cdx.json"
    write(supplement, {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1, "components": [
        {"type": "library", "name": "libexpat", "version": native["expat"],
         "cpe": "cpe:2.3:a:libexpat_project:libexpat:" + native["expat"] + ":*:*:*:*:*:*:*"},
        {"type": "library", "name": "openssl", "version": native["openssl"],
         "cpe": "cpe:2.3:a:openssl:openssl:" + native["openssl"] + ":*:*:*:*:*:*:*"}]})
    grype = [str(tools["grype"]), "--config", str(config)]
    command("db-update", [*grype, "db", "update"], timeout=900)
    _, status = command("db-status", [*grype, "db", "status", "-o", "json"])
    database = json.loads(status.read_bytes())
    age = validate_db(database, datetime.now(timezone.utc))
    frozen = db_files(cache)
    require(bool(frozen), "Vulnerability database file inventory is empty")
    scans = {}
    for name, source in (("image", sbom), ("embedded", supplement)):
        result = args.private / (name + ".grype.json")
        exitcode, _ = command(name + "-scan", [*grype, "sbom:" + str(source), "--fail-on", "high", "-o", "json"],
                              accepted=(0, 2), stdout_path=result, timeout=900)
        scans[name] = summary(json.loads(result.read_bytes()), exitcode) | {"sha256": sha(result)}
    require(frozen == db_files(cache), "Vulnerability database changed during matching")
    age_end = validate_db(database, datetime.now(timezone.utc))
    require(all(sha(tools[name]) == tools_metadata[name]["binary_sha256"] for name in tools), "Scanner binary changed")
    report = {"source": args.source, "image_id": args.image_id, "image_tar_sha256": sha(tar),
              "sbom_sha256": sha(sbom), "supplement_sha256": sha(supplement), "components": len(inventory["artifacts"]),
              "tools": tools_metadata, "database_built": database["built"], "database_age_seconds_at_start": age,
              "database_age_seconds_at_end": age_end,
              "package_inventory": [{key: item.get(key) for key in ("name", "version", "type", "purl")}
                                    for item in inventory["artifacts"]],
              "database_files": frozen, "database_frozen": True, "native": native, "scans": scans,
              "cpe_mapping": "Canonical vendor/product; versions from measured runtime, not a claim of exact NVD dictionary entries",
              "scope": "Principal and embedded scan matches remain separate, not additive unique vulnerability counts",
              "accepted": all(item["accepted"] for item in scans.values()), "new_subscription": False}
    write(args.output / "summary.json", report)
    print(json.dumps({"source": args.source, "image_id": args.image_id, "accepted": report["accepted"], "scans": scans}))
    return 0 if report["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
