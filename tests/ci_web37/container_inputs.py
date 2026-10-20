"""Authenticate the finite native recipe and the complete current web lock."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]
RECIPE_SOURCE = "72c44a1834d7bd9803b4b8846c6c87e85a53bfd3"


def lock_blocks(raw):
    raw = raw.replace(b"\r\n", b"\n")
    starts = []
    hashes = []
    offset = 0
    for physical in raw.splitlines(keepends=True):
        line = physical.decode("utf8").strip()
        if line and not line.startswith("#"):
            if line.startswith("--hash="):
                if not starts or re.fullmatch(r"--hash=sha256:[0-9a-f]{64}(?:\s*\\)?", line) is None:
                    raise ValueError("Unsupported authenticated dependency hash line")
                hashes[-1] += 1
            else:
                try:
                    requirement = Requirement(line.removesuffix("\\").strip())
                except InvalidRequirement as error:
                    raise ValueError("Unsupported active dependency lock entry") from error
                pins = list(requirement.specifier)
                if (requirement.url is not None or requirement.marker is not None or len(pins) != 1
                        or pins[0].operator != "==" or "*" in pins[0].version):
                    raise ValueError("Each active dependency must have one exact unconditional version")
                starts.append((offset, str(canonicalize_name(requirement.name)), pins[0].version))
                hashes.append(0)
        offset += len(physical)
    blocks = {}
    versions = {}
    for index, (start, name, version) in enumerate(starts):
        if name in blocks:
            raise ValueError("Duplicate canonical current container distribution")
        blocks[name] = raw[start:starts[index + 1][0] if index + 1 < len(starts) else len(raw)]
        versions[name] = version
        if hashes[index] == 0:
            raise ValueError("A current dependency has no authenticated hash")
    if not starts:
        raise ValueError("Current container dependency inventory is absent")
    return blocks, versions


def verify_current_lock(web, container, contract):
    web_blocks, web_versions = lock_blocks(web)
    blocks, versions = lock_blocks(container)
    if len(web_blocks) != 57 or web_versions.get("psycopg2-binary") != "2.9.13":
        raise ValueError("Current web dependency inventory differs")
    expected = {name: block for name, block in web_blocks.items() if name != "psycopg2-binary"}
    if blocks != expected or len(blocks) != 56:
        raise ValueError("All current56 nonbinary-adapter package/version/hash blocks must be preserved")
    expected_versions = {**versions, "psycopg2": "2.9.13"}
    if (type(contract.get("runtime_distribution_count")) is not int
            or contract["runtime_distribution_count"] != 57 or contract["distributions"] != expected_versions
            or contract["native_recipe_source"] != RECIPE_SOURCE
            or contract["web_lock_raw_sha256"] != hashlib.sha256(web.replace(b"\r\n", b"\n")).hexdigest()):
        raise ValueError("Current57 runtime exact name/version contract differs")
    return expected_versions


def verify():
    manifest = json.loads((ROOT / "tests/ci_web37/container-inputs.json").read_bytes())
    if manifest["native_recipe_source"] != RECIPE_SOURCE:
        raise ValueError("Native recipe source differs")
    for name, pin in manifest["source_files"].items():
        original = subprocess.check_output(["git", "--no-replace-objects", "show", RECIPE_SOURCE + ":" + name], cwd=ROOT)
        if hashlib.sha256(original).hexdigest() != pin["raw_sha256"]:
            raise ValueError("Original native recipe Git source differs")
        if name != "Dockerfile" and (ROOT / name).read_bytes().replace(b"\r\n", b"\n") != original:
            raise ValueError("An unchanged native recipe source differs")
    for name, pin in manifest["candidate_files"].items():
        raw = (ROOT / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin["raw_sha256"]:
            raise ValueError("A current container input RAW source differs")
    versions = verify_current_lock((ROOT / "requirements_web.lock").read_bytes(),
                                   (ROOT / "requirements-container.lock").read_bytes(),
                                   json.loads((ROOT / "runtime-source/container37-contract.json").read_bytes()))
    return {"scope": "source_inputs_only_no_image_VM_APT_or_runtime_execution",
            "native_recipe_source": RECIPE_SOURCE, "web_lock_blocks_preserved": 56,
            "runtime_distribution_count": len(versions), "container_inputs": len(manifest["candidate_files"]),
            "current_image_built": False, "independent_security_review_required": True}


if __name__ == "__main__":
    print(json.dumps(verify()))
