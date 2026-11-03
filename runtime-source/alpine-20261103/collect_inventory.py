"""Bounded, secret-free Alpine exploration. No production acceptance is issued.

Build helpers run only inside the pinned Linux/amd64 image. The collector reads
package/ELF metadata and probes dependency imports without importing the app.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import os
import platform
import re
import shutil
import signal
import ssl
import struct

# Fixed argument vectors, no shell; command() constrains the executable too.
import subprocess  # nosec B404
import sys
import sysconfig
import tarfile
import time
import urllib.parse
import urllib.request
import zipfile
from importlib import metadata
from pathlib import Path

SOURCE = Path("/opt/alpine-source")
EVIDENCE = Path("/opt/alpine-evidence")
APK = "/sbin/apk"
MAX_JSON = 16 * 1024 * 1024
MAX_PUBLICATION = 64 * 1024 * 1024
MAX_LOG = 2 * 1024 * 1024
MAX_FILE = 512 * 1024 * 1024
MAX_DOWNLOAD_TOTAL = 384 * 1024 * 1024
DOWNLOAD_HOSTS = frozenset({"dl-cdn.alpinelinux.org", "files.pythonhosted.org"})
MAX_REDIRECT_HOPS = 5


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    require(len(raw) <= MAX_JSON, "JSON output bound exceeded")
    path.write_bytes(raw)


def publication_size(output: Path, evidence: Path) -> int:
    """Apply Root's per-JSON and aggregate public-artifact limits."""
    paths = [output]
    for path in evidence.rglob("*"):
        require(not path.is_symlink(), "Public artifact symlink forbidden")
        if path.is_file():
            paths.append(path)
    total = 0
    for path in paths:
        require(
            path.is_file() and not path.is_symlink(), "Public artifact must be regular"
        )
        size = path.stat().st_size
        if path.suffix == ".json":
            require(size <= MAX_JSON, "Public JSON bound exceeded")
        total += size
        require(total <= MAX_PUBLICATION, "Public artifact aggregate bound exceeded")
    return total


def pins() -> dict:
    return json.loads((SOURCE / "source-pins.json").read_text())


def linux_guard() -> None:
    require(
        sys.platform == "linux" and platform.machine() == "x86_64",
        "Native Linux/amd64 required",
    )
    require(platform.python_version() == "3.13.18", "Pinned CPython required")


def clean_env() -> dict[str, str]:
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "LANG": "C.UTF-8",
        "HOME": "/nonexistent",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PIP_CONFIG_FILE": "/dev/null",
    }


def command(
    argv: list[str], log: Path, *, timeout: int = 120, success: bool = True
) -> dict:
    """Commands are fixed public build/probe inputs; ambient credentials are absent."""
    log.parent.mkdir(parents=True, exist_ok=True)
    require(argv[0] in {APK, sys.executable}, "Unapproved build/probe executable")
    started = time.monotonic()
    with log.open("wb") as stream:
        # argv is fixed or authenticated public package metadata; shell=False.
        process = subprocess.Popen(  # nosec B603
            argv,
            stdout=stream,
            stderr=subprocess.STDOUT,
            env=clean_env(),
            start_new_session=True,
        )
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
    require(log.stat().st_size <= MAX_LOG, "Command output bound exceeded")
    result = {
        "argv": argv,
        "returncode": process.returncode,
        "timed_out": timed_out,
        "seconds": round(time.monotonic() - started, 3),
        "log_sha256": digest(log),
        "log_bytes": log.stat().st_size,
    }
    if success:
        require(
            not timed_out and process.returncode == 0,
            "Required command failed; inspect public receipt log",
        )
    return result


def download_origin(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    require(
        parsed.scheme == "https"
        and parsed.hostname in DOWNLOAD_HOSTS
        and parsed.username is None
        and parsed.password is None
        and parsed.port in {None, 443}
        and not parsed.fragment,
        "Download requires credential-free official HTTPS origin",
    )
    return parsed.hostname


class PinnedHTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject an unsafe hop before urllib opens the redirected request."""

    max_repeats = MAX_REDIRECT_HOPS
    max_redirections = MAX_REDIRECT_HOPS

    def __init__(self, origin: str) -> None:
        require(origin in DOWNLOAD_HOSTS, "Unapproved redirect origin")
        self.origin = origin
        self.accepted_hops = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require(
            download_origin(req.full_url) == self.origin
            and download_origin(newurl) == self.origin,
            "Unexpected redirect origin",
        )
        require(self.accepted_hops < MAX_REDIRECT_HOPS, "Redirect hop bound exceeded")
        self.accepted_hops += 1
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(
    url: str, destination: Path, expected_bytes: int, sha256: str | None = None
) -> None:
    origin = download_origin(url)
    require(0 < expected_bytes <= 128 * 1024 * 1024, "Download bound invalid")
    # A fresh opener bounds the entire chain and checks every hop before follow.
    opener = urllib.request.build_opener(PinnedHTTPSRedirectHandler(origin))
    with opener.open(url, timeout=60) as response:
        require(
            download_origin(response.geturl()) == origin,
            "Unexpected download origin",
        )
        raw = response.read(expected_bytes + 1)
    require(len(raw) == expected_bytes, "Download length mismatch")
    if sha256 is not None:
        require(hashlib.sha256(raw).hexdigest() == sha256, "Download SHA256 mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)


def apk_records(raw: str) -> list[dict[str, str]]:
    result = []
    for block in raw.split("\n\n"):
        row = {}
        for line in block.splitlines():
            if len(line) > 2 and line[1] == ":" and line[0] in "CPVASIoDpcULt":
                row.setdefault(line[0], line[2:])
        if "P" in row:
            require("V" in row and "A" in row, "Invalid APK package record")
            result.append(row)
    require(
        len({row["P"] for row in result}) == len(result), "Duplicate APK package names"
    )
    return result


def installed() -> list[dict[str, str]]:
    return apk_records(Path("/lib/apk/db/installed").read_text())


def verify_inputs() -> None:
    linux_guard()
    contract = pins()
    for name, expected in contract["input_sha256"].items():
        require(
            digest(SOURCE / name) == expected, "Reviewed source input hash mismatch"
        )
    actual = {row["P"]: row["V"] for row in installed()}
    require(
        actual == contract["base_packages"],
        "Base APK inventory differs from observed OCI digest",
    )
    require(
        digest(Path("/lib/apk/db/installed")) == contract["base_apk_database_sha256"],
        "Base APK database bytes differ",
    )
    ca = Path(contract["base_ca"]["path"])
    require(
        ca.stat().st_size == contract["base_ca"]["bytes"]
        and digest(ca) == contract["base_ca"]["sha256"],
        "Official base CA bundle differs",
    )
    ca_link = contract["base_ca"]["default_symlink"]
    require(
        Path(ca_link["path"]).is_symlink()
        and os.readlink(ca_link["path"]) == ca_link["target"],
        "Official CA symlink differs",
    )
    require(
        digest(Path(contract["base_interpreter"]["path"]))
        == contract["base_interpreter"]["sha256"],
        "Official base interpreter differs",
    )
    write_json(
        EVIDENCE / "base.json",
        {
            "release_accepted": False,
            "base": contract["base"],
            "apk": installed(),
            "apk_database_sha256": digest(Path("/lib/apk/db/installed")),
            "ca": contract["base_ca"],
            "interpreter": contract["base_interpreter"],
            "source_sha256": {
                p.name: digest(p) for p in sorted(SOURCE.iterdir()) if p.is_file()
            },
        },
    )


def install_apk(lock_name: str) -> None:
    linux_guard()
    require(
        lock_name
        in {
            "apk-build.lock.json",
            "apk-runtime-web.lock.json",
            "apk-runtime-backup.lock.json",
        },
        "Unknown APK lock",
    )
    contract = pins()
    lock = json.loads((SOURCE / lock_name).read_text())
    phase = lock["profile"]
    work = Path("/opt/apk-work") / phase
    require(not work.exists(), "APK build workspace must be new")
    root = work / "repository"
    repository = root / "x86_64"
    repository.mkdir(parents=True)
    receipt = EVIDENCE / ("apk-" + phase)
    receipt.mkdir(parents=True)
    (work / "cache").mkdir()
    (work / "negative-cache").mkdir()
    trusted = work / "keys"
    trusted.mkdir()
    key_receipts = []
    for name, expected in contract["apk_keyring"].items():
        origin = Path("/etc/apk/keys") / name
        require(
            origin.is_file() and not origin.is_symlink(),
            "APK key must be a regular file",
        )
        require(digest(origin) == expected, "Base APK key hash mismatch")
        shutil.copyfile(origin, trusted / name)
        (trusted / name).chmod(0o444)
        key_receipts.append({"name": name, "sha256": digest(trusted / name)})
    trusted.chmod(0o555)
    index_pin = contract["apk_index"]
    index = repository / "APKINDEX.tar.gz"
    download(index_pin["url"], index, index_pin["bytes"], index_pin["sha256"])
    base_args = [
        APK,
        "--keys-dir",
        str(trusted),
        "--repositories-file",
        "/dev/null",
        "--repository",
        str(root),
        "--network=no",
        "--cache-dir",
        str(work / "cache"),
    ]
    # apk update authenticates the real signed local index before it is parsed here.
    positive = command([*base_args, "update"], receipt / "index-verified.log")
    empty = work / "empty-keyring"
    empty.mkdir()
    negative = command(
        [
            APK,
            "--keys-dir",
            str(empty),
            "--repositories-file",
            "/dev/null",
            "--repository",
            str(root),
            "--network=no",
            "--cache-dir",
            str(work / "negative-cache"),
            "update",
        ],
        receipt / "index-empty-trust-rejected.log",
        success=False,
    )
    require(
        negative["returncode"] != 0 and not negative["timed_out"],
        "Unsigned trust boundary did not reject",
    )
    with tarfile.open(index, "r:gz") as archive:
        member = archive.getmember("APKINDEX")
        require(
            member.isfile() and member.size <= 32 * 1024 * 1024,
            "APK index bound invalid",
        )
        stream = archive.extractfile(member)
        require(stream is not None, "Missing APK index")
        rows = apk_records(stream.read().decode("utf-8"))
    by_filename = {f"{r['P']}-{r['V']}.apk": r for r in rows}
    for requested in lock["roots"]:
        row = next((r for r in rows if r["P"] == requested["name"]), None)
        require(
            row is not None and row["V"] == requested["version"],
            "Pinned APK root unavailable",
        )
    roots = [r["name"] + "=" + r["version"] for r in lock["roots"]]
    resolve = command(
        [*base_args, "fetch", "--recursive", "--url", *roots],
        receipt / "resolved-urls.log",
    )
    urls = (receipt / "resolved-urls.log").read_text().splitlines()
    names = []
    for line in urls:
        if line.endswith(".apk"):
            filename = urllib.parse.unquote(
                urllib.parse.urlsplit(line).path.rsplit("/", 1)[-1]
            )
            require(
                filename in by_filename,
                "Solver returned package outside pinned signed index",
            )
            names.append(filename)
    names = sorted(set(names))
    require(0 < len(names) <= 128, "APK closure count outside bound")
    require(
        sum(int(by_filename[n]["S"]) for n in names) <= MAX_DOWNLOAD_TOTAL,
        "APK closure byte bound",
    )
    packages = []
    for number, name in enumerate(names):
        row = by_filename[name]
        artifact = repository / name
        url = index_pin["url"].rsplit("/", 1)[0] + "/" + name
        download(url, artifact, int(row["S"]))
        verified = command(
            [APK, "--keys-dir", str(trusted), "verify", str(artifact)],
            receipt / f"package-{number:03d}-verified.log",
        )
        packages.append(
            {
                "filename": name,
                "url": url,
                "bytes": artifact.stat().st_size,
                "sha256": digest(artifact),
                "signed_index_metadata": row,
                "verification": verified,
            }
        )
    before = installed()
    (receipt / "before-installed.txt").write_bytes(
        Path("/lib/apk/db/installed").read_bytes()
    )
    install = command(
        [*base_args, "add", *roots], receipt / "installation.log", timeout=180
    )
    after = installed()
    before_versions = {r["P"]: r["V"] for r in before}
    after_versions = {r["P"]: r["V"] for r in after}
    require(
        all(after_versions.get(k) == v for k, v in before_versions.items()),
        "Existing base package changed",
    )
    require(
        all(after_versions.get(r["name"]) == r["version"] for r in lock["roots"]),
        "APK root install mismatch",
    )
    if phase.startswith("runtime"):
        require(
            not (
                {"libgcc", "libstdc++"}
                & (after_versions.keys() - before_versions.keys())
            ),
            "Unexpected C++ runtime addition; retain dependency failure for review",
        )
    for name in after_versions.keys() - before_versions.keys():
        require(
            any(
                p["signed_index_metadata"]["P"] == name
                and p["signed_index_metadata"]["V"] == after_versions[name]
                for p in packages
            ),
            "Installed addition lacks verified package receipt",
        )
    (receipt / "after-installed.txt").write_bytes(
        Path("/lib/apk/db/installed").read_bytes()
    )
    shutil.copyfile(index, receipt / "APKINDEX.tar.gz")
    write_json(
        receipt / "receipt.json",
        {
            "schema": "metodobase-alpine-apk-receipt-v1",
            "release_accepted": False,
            "lock_sha256": digest(SOURCE / lock_name),
            "keyring": key_receipts,
            "index": {
                **index_pin,
                "actual_sha256": digest(index),
                "verification": positive,
                "empty_trust_negative_control": negative,
            },
            "solver": resolve,
            "packages": packages,
            "installation": install,
            "before": before,
            "after": after,
            "base_package_artifacts_verified_by_this_step": False,
        },
    )
    # Build-only download workspace; no archives are exported as public CI artifacts.
    require(work.resolve().parent == Path("/opt/apk-work"), "APK workspace boundary")
    shutil.rmtree(work)


def fetch_psycopg() -> None:
    source = pins()["psycopg_source"]
    download(
        source["url"],
        Path("/opt/native-source/psycopg2-2.9.13.tar.gz"),
        source["bytes"],
        source["sha256"],
    )


def wheel_receipt(profile: str) -> None:
    wheels = []
    for path in sorted(Path("/opt/wheels").glob("*.whl")):
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, "Wheel zip corruption")
            require(
                all(
                    not n.startswith("/") and ".." not in Path(n).parts
                    for n in archive.namelist()
                ),
                "Unsafe wheel path",
            )
            records = [
                n for n in archive.namelist() if n.endswith(".dist-info/METADATA")
            ]
            require(len(records) == 1, "Wheel metadata is ambiguous")
            raw = archive.read(records[0])
            fields = dict(
                line.split(": ", 1)
                for line in raw.decode().splitlines()
                if line.startswith(("Name: ", "Version: "))
            )
            wheels.append(
                {
                    "filename": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": digest(path),
                    "name": fields["Name"],
                    "version": fields["Version"],
                    "metadata_sha256": hashlib.sha256(raw).hexdigest(),
                    "origin": "reviewed psycopg source build"
                    if path.name.startswith("psycopg2-")
                    else "hash-locked PyPI wheel",
                    "embedded_library_members": [
                        n for n in archive.namelist() if ".libs/" in n
                    ],
                }
            )
    expected = pins()["profiles"][profile]["distributions"]
    actual = {
        re.sub(r"[-_.]+", "-", row["name"]).lower(): row["version"] for row in wheels
    }
    require(
        actual == expected and len(wheels) == len(expected),
        "Wheel inventory differs from reviewed profile",
    )
    write_json(
        EVIDENCE / "wheels.json",
        {
            "profile": profile,
            "release_accepted": False,
            "wheels": wheels,
            "psycopg_source": pins()["psycopg_source"],
            "external_artifact_urls_measured": False,
        },
    )


def strip_installers() -> None:
    linux_guard()
    site = Path(sysconfig.get_path("purelib"))
    require(
        site == Path("/usr/local/lib/python3.13/site-packages")
        and site.resolve() == site,
        "Installer removal boundary mismatch",
    )
    targets = [
        site / "pip",
        *site.glob("pip-*.dist-info"),
        Path("/usr/local/lib/python3.13/ensurepip"),
    ]
    require(
        len(targets) == 3 and all(p.is_dir() and not p.is_symlink() for p in targets),
        "Unexpected installer inventory",
    )
    for target in targets:
        shutil.rmtree(target)
    for name in ("pip", "pip3", "pip3.13"):
        Path("/usr/local/bin", name).unlink(missing_ok=True)


def elf_record(path: Path) -> dict:
    """Read ELF64 little-endian program/dynamic tables, including private DSOs.

    Resolution candidates are evidence, not a complete emulation of musl's
    inherited search scopes or dlopen. Import/function tests remain necessary.
    """
    require(path.stat().st_size <= MAX_FILE, "ELF size limit exceeded")
    with (
        path.open("rb") as stream,
        mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as raw,
    ):
        require(raw[:6] == b"\x7fELF\x02\x01", "Unsupported ELF class/endian")
        require(len(raw) >= 64, "Truncated ELF header")
        machine = struct.unpack_from("<H", raw, 18)[0]
        phoff = struct.unpack_from("<Q", raw, 32)[0]
        entry_size, count = struct.unpack_from("<HH", raw, 54)
        require(
            entry_size >= 56
            and count <= 4096
            and phoff + count * entry_size <= len(raw),
            "Invalid ELF program table",
        )
        segments = [
            struct.unpack_from("<IIQQQQQQ", raw, phoff + i * entry_size)
            for i in range(count)
        ]

        def string(offset: int, end: int) -> str:
            require(0 <= offset < end <= len(raw), "Invalid ELF string bounds")
            stop = raw.find(b"\0", offset, min(end, offset + 65536))
            require(stop >= 0, "Unterminated ELF string")
            return raw[offset:stop].decode("utf-8", errors="strict")

        def offset_for(address: int) -> int:
            for segment in segments:
                if segment[0] == 1 and segment[3] <= address < segment[3] + segment[5]:
                    return segment[2] + address - segment[3]
            raise RuntimeError("ELF virtual address has no file segment")

        dynamic = []
        interpreter = None
        for segment in segments:
            offset, size = segment[2], segment[5]
            require(offset + size <= len(raw), "ELF segment out of bounds")
            if segment[0] == 3:
                interpreter = string(offset, offset + size)
            if segment[0] == 2:
                require(
                    size <= 1024 * 1024 and size % 16 == 0, "Invalid ELF dynamic table"
                )
                for location in range(offset, offset + size, 16):
                    tag, value = struct.unpack_from("<qQ", raw, location)
                    if tag == 0:
                        break
                    dynamic.append((tag, value))
        tags = dict(dynamic)
        strings = offset_for(tags[5]) if 5 in tags else 0
        end = strings + tags.get(10, 0)
        names = lambda tag: [
            string(strings + value, end) for key, value in dynamic if key == tag
        ]
        return {
            "path": str(path),
            "sha256": digest(path),
            "bytes": len(raw),
            "machine": machine,
            "interpreter": interpreter,
            "needed": names(1),
            "soname": names(14),
            "rpath": names(15),
            "runpath": names(29),
            "private_wheel_library": any(part.endswith(".libs") for part in path.parts),
            "cpp_version_strings": sorted(
                {m.decode() for m in re.findall(rb"(?:GLIBCXX|CXXABI)_[0-9.]+", raw)}
            ),
        }


def inventory_elf() -> tuple[list[dict], list[dict]]:
    rows, errors = [], []
    visited = set()
    for root in ("/bin", "/sbin", "/lib", "/usr", "/opt"):
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs.sort()
            for name in sorted(files):
                path = Path(directory) / name
                if path.is_symlink() or not path.is_file():
                    continue
                require(len(visited) < 100000, "Filesystem scan file bound exceeded")
                identity = (path.stat().st_dev, path.stat().st_ino)
                if identity in visited:
                    continue
                visited.add(identity)
                with path.open("rb") as stream:
                    is_elf = stream.read(4) == b"\x7fELF"
                if is_elf:
                    try:
                        rows.append(elf_record(path))
                    except (OSError, RuntimeError, ValueError, struct.error) as exc:
                        errors.append(
                            {"path": str(path), "error_type": type(exc).__name__}
                        )
    for row in rows:
        directories = []
        for group in row["runpath"] or row["rpath"]:
            directories.extend(
                group.replace("${ORIGIN}", str(Path(row["path"]).parent))
                .replace("$ORIGIN", str(Path(row["path"]).parent))
                .split(":")
            )
        directories.extend(["/lib", "/usr/local/lib", "/usr/lib"])
        row["direct_resolution_candidates"] = {
            name: sorted(
                {
                    str((Path(folder) / name).resolve())
                    for folder in directories
                    if folder.startswith("/")
                    and "$" not in folder
                    and (Path(folder) / name).is_file()
                }
            )
            for name in row["needed"]
        }
    return rows, errors


def collect(profile: str, output: Path) -> None:
    linux_guard()
    contract = pins()
    expected = contract["profiles"][profile]
    require(
        os.getuid() == expected["uid"] and os.getgid() == expected["gid"],
        "Runtime identity mismatch",
    )
    distributions = []
    for dist in metadata.distributions():
        name = re.sub(r"[-_.]+", "-", dist.metadata["Name"]).lower()
        raw = (dist.read_text("METADATA") or "").encode()
        distributions.append(
            {
                "name": name,
                "version": dist.version,
                "metadata_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    actual = {r["name"]: r["version"] for r in distributions}
    require(
        actual == expected["distributions"] and len(distributions) == len(actual),
        "Runtime distribution inventory differs",
    )
    elf, elf_errors = inventory_elf()
    import_checks = []
    for number, module in enumerate(expected["import_probes"]):
        code = (
            "import importlib; importlib.import_module("
            + repr(module)
            + "); print('IMPORT_OK')"
        )
        log = output.parent / f"import-{number:02d}.log"
        result = command(
            [sys.executable, "-I", "-B", "-c", code], log, timeout=20, success=False
        )
        import_checks.append(
            {
                "module": module,
                **result,
                "log": log.name,
                "diagnostic": log.read_text(errors="replace")[-16384:],
                "success": result["returncode"] == 0 and not result["timed_out"],
            }
        )
    function_checks = []
    probes = {
        "psycopg_libpq": "import json,psycopg2; from psycopg2 import extensions; print(json.dumps({'compile':psycopg2.__libpq_version__,'runtime':extensions.libpq_version()}))",
        "stdlib_xml_sqlite": "import json,pyexpat,sqlite3; print(json.dumps({'expat':pyexpat.EXPAT_VERSION,'sqlite':sqlite3.sqlite_version}))",
    }
    if profile == "web":
        probes["pillow_features"] = (
            "from PIL import features; print(features.get_supported())"
        )
    for number, (name, code) in enumerate(probes.items()):
        log = output.parent / f"function-{number:02d}.log"
        result = command(
            [sys.executable, "-I", "-B", "-c", code], log, timeout=20, success=False
        )
        function_checks.append(
            {
                "name": name,
                **result,
                "diagnostic": log.read_text(errors="replace")[-16384:],
            }
        )
    context = ssl.create_default_context()
    ca = Path("/etc/ssl/cert.pem").resolve()
    ssl_observation = {
        "bundle_path": str(ca),
        "sha256": digest(ca),
        "default_context_ca_der_sha256": sorted(
            hashlib.sha256(v).hexdigest()
            for v in context.get_ca_certs(binary_form=True)
        ),
        "default_verify_paths": ssl.get_default_verify_paths()._asdict(),
        "acceptance": False,
        "SPKI_and_certifi_policy_proof_pending": True,
    }
    headers = {
        str(p): digest(p)
        for p in sorted(Path(sysconfig.get_path("include")).rglob("*"))
        if p.is_file()
    }
    write_json(
        output,
        {
            "schema": "metodobase-alpine-runtime-exploration-v1",
            "profile": profile,
            "release_accepted": False,
            "source_sha256": {
                p.name: digest(p) for p in sorted(SOURCE.iterdir()) if p.is_file()
            },
            "base": contract["base"],
            "uid": os.getuid(),
            "gid": os.getgid(),
            "distributions": sorted(distributions, key=lambda r: r["name"]),
            "apk": installed(),
            "apk_database_sha256": digest(Path("/lib/apk/db/installed")),
            "elf": elf,
            "elf_errors": elf_errors,
            "import_checks": import_checks,
            "function_checks": function_checks,
            "native": {
                "python": platform.python_version(),
                "soabi": sysconfig.get_config_var("SOABI"),
                "ext_suffix": sysconfig.get_config_var("EXT_SUFFIX"),
                "headers_sha256": headers,
                "interpreter_sha256": digest(Path(sys.executable).resolve()),
                "ssl": ssl.OPENSSL_VERSION,
            },
            "ca": ssl_observation,
            "receipts": {
                str(p.relative_to(EVIDENCE)): digest(p)
                for p in sorted(EVIDENCE.rglob("*"))
                if p.is_file()
            },
            "limitations": contract["pending_acceptance"],
            "public_artifact_bounds": {
                "max_json_bytes": MAX_JSON,
                "max_publication_bytes": MAX_PUBLICATION,
            },
            "elf_scope": {
                "roots": ["/bin", "/sbin", "/lib", "/usr", "/opt"],
                "private_libraries_included": True,
                "static_parser_errors_are_not_absence": True,
                "direct_candidates_are_not_complete_loader_resolution": True,
                "dlopen_and_PBDS_source_provenance_pending": True,
            },
        },
    )
    publication_size(output, EVIDENCE)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "verify-inputs",
            "apk-install",
            "fetch-psycopg",
            "wheel-receipt",
            "strip-installers",
            "collect",
        ],
    )
    parser.add_argument("--profile", choices=["web", "backup"])
    parser.add_argument("--lock")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    linux_guard()
    if args.action == "verify-inputs":
        verify_inputs()
    elif args.action == "apk-install":
        install_apk(args.lock)
    elif args.action == "fetch-psycopg":
        fetch_psycopg()
    elif args.action == "wheel-receipt":
        require(args.profile is not None, "Profile required")
        wheel_receipt(args.profile)
    elif args.action == "strip-installers":
        strip_installers()
    else:
        require(
            args.profile is not None
            and args.output == Path("/inventory/inventory.json"),
            "Explicit profile/output required",
        )
        collect(args.profile, args.output)


if __name__ == "__main__":
    main()
