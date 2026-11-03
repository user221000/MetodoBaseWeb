"""Publish only a complete, bounded Alpine exploration receipt.

The caller verifies checkout HEAD before building and passes that same commit
and the exact inspected IID here. This module reads the eleven copied source
inputs, never imports them, executes nothing and makes no release/SCA claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import urllib.parse
from pathlib import Path, PurePosixPath

MAX_FILE = 16 * 1024**2
MAX_TOTAL = 64 * 1024**2
MAX_FILES = 287
MAX_LOG = 2 * 1024**2
BASE = "python:3.13.18-alpine3.24@sha256:7712cfd23e0501f5cb58faa5e6e0d515c9939bdbce866921799b31e696a1d13c"
SCHEMA = "metodobase-alpine-runtime-exploration-v1"
SOURCE_DIR = "runtime-source/alpine-20261103"
PROFILES = {"web": (999, 57, "Dockerfile.alpine", "requirements-container.lock"),
            "backup": (10001, 11, "Dockerfile.backup.alpine", "requirements-backup.lock")}
INPUTS = {"requirements-container-bootstrap.lock", "requirements-container-build.lock",
          "requirements-container-psycopg.lock", "requirements-container.lock", "requirements-backup.lock",
          "apk-build.lock.json", "apk-runtime-web.lock.json", "apk-runtime-backup.lock.json"}
BUILD_FILES = {"bootstrap.log", "build-tools-install.log", "psycopg-wheel.log", "built-wheel.lock",
               "application-download.log", "application-install.json", "application-install.log",
               "pip-check.log", "pg-config-version.txt", "build-tools.txt"}
APK_FILES = {"index-verified.log", "index-empty-trust-rejected.log", "resolved-urls.log",
             "before-installed.txt", "installation.log", "after-installed.txt", "APKINDEX.tar.gz", "receipt.json"}
INVENTORY_FIELDS = {"schema", "profile", "release_accepted", "source_sha256", "base", "uid", "gid",
                    "distributions", "apk", "apk_database_sha256", "elf", "elf_errors", "import_checks",
                    "function_checks", "native", "ca", "receipts", "limitations", "elf_scope", "public_artifact_bounds"}
COMMAND_FIELDS = {"argv", "returncode", "timed_out", "seconds", "log_sha256", "log_bytes"}
APK_KEYS = set("CPVASIoDpcULt")
FUNCTION_PROBES = {
    "psycopg_libpq": "import json,psycopg2; from psycopg2 import extensions; print(json.dumps({'compile':psycopg2.__libpq_version__,'runtime':extensions.libpq_version()}))",
    "stdlib_xml_sqlite": "import json,pyexpat,sqlite3; print(json.dumps({'expat':pyexpat.EXPAT_VERSION,'sqlite':sqlite3.sqlite_version}))",
    "pillow_features": "from PIL import features; print(features.get_supported())",
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def hex_value(value, size=64):
    require(type(value) is str and re.fullmatch("[0-9a-f]{" + str(size) + "}", value) is not None,
            "Invalid typed digest")
    return value


def integer(value, lower=0, upper=None):
    require(type(value) is int and value >= lower and (upper is None or value <= upper), "Invalid typed integer")


def text(value):
    require(type(value) is str and "\0" not in value, "Invalid text")


def exact(value, keys):
    require(type(value) is dict and set(value) == set(keys), "Object fields differ")


def same(value, expected):
    if type(value) is not type(expected):
        return False
    if type(expected) is dict:
        return set(value) == set(expected) and all(same(value[key], item) for key, item in expected.items())
    if type(expected) is list:
        return len(value) == len(expected) and all(same(first, second) for first, second in zip(value, expected))
    return value == expected


def strings(value):
    require(type(value) is list and all(type(item) is str and "\0" not in item for item in value), "Invalid text list")


def hashes(value):
    require(type(value) is dict, "Invalid hash map")
    for name, digest in value.items():
        text(name)
        hex_value(digest)


def canonical(value):
    text(value)
    path = PurePosixPath(value)
    require(value and value == path.as_posix() and not path.is_absolute() and ":" not in value
            and all(part not in {"", ".", ".."} for part in value.split("/"))
            and all(32 <= ord(char) < 127 for char in value), "Noncanonical relative path")
    return value


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_nlink)


def same_file(path_info, descriptor_info):
    # Windows reports creation time through lstat but change time through
    # fstat. Preserve both complete within-API identities across the read;
    # compare every other field between APIs. POSIX keeps all seven fields.
    first, second = identity(path_info), identity(descriptor_info)
    if os.name == "nt":
        return first[:5] + first[6:] == second[:5] + second[6:]
    return first == second


def plain(info):
    require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
            "Filesystem alias rejected")


def directory(path):
    require(type(path) is Path or isinstance(path, Path), "Directory path required")
    require(path.is_absolute() and path == path.absolute(), "Absolute directory required")
    for current in (path, *path.parents):
        info = current.lstat()
        plain(info)
        require(stat.S_ISDIR(info.st_mode), "Regular directory required")
    require(path.resolve(strict=True) == path, "Directory resolution differs")
    if os.name == "nt":
        require(path.drive.upper() in {"E:", "F:"}, "Local project paths must remain on E/F")
    return path


def read(path, observed):
    """One bounded read with descriptor/path identity checks; never read_bytes."""
    directory(path.parent)
    before = path.lstat()
    plain(before)
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= MAX_FILE,
            "Bounded regular file required")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        require(same_file(before, opened), "File changed before open")
        raw = stream.read(MAX_FILE + 1)
        after_descriptor = os.fstat(stream.fileno())
    after = path.lstat()
    require(identity(before) == identity(after) and identity(opened) == identity(after_descriptor)
            and len(raw) == before.st_size and len(raw) <= MAX_FILE, "File changed during bounded read")
    previous = observed.get(path)
    require(previous is None or previous == identity(before), "File changed between reads")
    observed[path] = identity(before)
    return raw


def quiet(observed):
    for path, expected in observed.items():
        directory(path.parent)
        info = path.lstat()
        plain(info)
        require(identity(info) == expected, "Input changed after validation")


def json_object(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    def invalid(_value):
        raise ValueError("Nonfinite JSON number")

    def finite(value):
        result = float(value)
        require(math.isfinite(result), "Nonfinite JSON number")
        return result

    value = json.loads(raw.decode("utf8"), object_pairs_hook=pairs, parse_constant=invalid, parse_float=finite)
    require(type(value) is dict, "JSON object required")
    return value


def repository_inputs(repository, profile, observed):
    raw = read(repository / SOURCE_DIR / "source-pins.json", observed)
    pins = json_object(raw)
    require(pins.get("schema") == "metodobase-alpine-exploration-source-pins-v1"
            and pins.get("release_accepted") is False and type(pins.get("source_generation")) is int
            and pins["source_generation"] == 2 and pins.get("python_version") == "3.13.18"
            and pins.get("base") == BASE, "Reviewed exploration source differs")
    exact(pins["input_sha256"], INPUTS)
    hashes(pins["input_sha256"])
    uid, count, recipe, lock = PROFILES[profile]
    expected = pins["profiles"][profile]
    require(type(expected["uid"]) is int and type(expected["gid"]) is int
            and expected["uid"] == expected["gid"] == uid and expected["lock"] == lock,
            "Reviewed profile identity differs")
    require(type(expected["distributions"]) is dict and len(expected["distributions"]) == count,
            "Reviewed distribution count differs")
    for name, version in expected["distributions"].items():
        text(name)
        text(version)
    strings(expected["import_probes"])
    require(len(set(expected["import_probes"])) == len(expected["import_probes"]), "Duplicate import probe")
    require(type(pins["build_bounds"]["max_public_json_bytes"]) is int
            and pins["build_bounds"]["max_public_json_bytes"] == MAX_FILE
            and type(pins["build_bounds"]["max_publication_bytes"]) is int
            and pins["build_bounds"]["max_publication_bytes"] == MAX_TOTAL, "Reviewed byte bounds differ")
    payloads = {"source-pins.json": raw,
                "collect_inventory.py": read(repository / SOURCE_DIR / "collect_inventory.py", observed),
                "recipe.Dockerfile": read(repository / recipe, observed)}
    for name, digest in pins["input_sha256"].items():
        path = repository / SOURCE_DIR / name if name.endswith(".json") else repository / name
        payloads[name] = read(path, observed)
        require(sha(payloads[name]) == digest, "Reviewed source input hash differs")
    require(len(payloads) == 11, "Eleven copied source inputs required")
    return pins, expected, payloads


def allowed_paths(profile):
    fixed = {"inventory.json", "image.iid", "dependency-evidence/base.json",
             "dependency-evidence/build/base.json", "dependency-evidence/build/wheels.json"}
    fixed.update("dependency-evidence/build/python-build/" + name for name in BUILD_FILES)
    phases = ["dependency-evidence/apk-runtime-" + profile, "dependency-evidence/build/apk-build"]
    for prefix in phases:
        fixed.update(prefix + "/" + name for name in APK_FILES)
    directories = {str(parent) for name in fixed for parent in PurePosixPath(name).parents if str(parent) != "."}
    return fixed, phases, directories


def scan(root, profile):
    fixed, phases, directories = allowed_paths(profile)
    found = set()

    def visit(path):
        entries = []
        with os.scandir(path) as stream:
            for entry in stream:
                entries.append(entry)
                require(len(entries) <= MAX_FILES + len(directories), "Directory entry count exceeded")
        for entry in sorted(entries, key=lambda item: item.name):
            child = path / entry.name
            name = canonical(child.relative_to(root).as_posix())
            info = child.lstat()
            plain(info)
            if stat.S_ISDIR(info.st_mode):
                require(name in directories, "Unexpected evidence directory")
                visit(child)
            else:
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "Nonregular evidence rejected")
                allowed = name in fixed
                if not allowed:
                    for prefix in phases:
                        match = re.fullmatch(re.escape(prefix) + r"/package-([0-9]{3})-verified[.]log", name)
                        allowed = allowed or match is not None and int(match[1]) <= 127
                require(allowed, "Unexpected evidence file")
                found.add(name)
                require(len(found) <= MAX_FILES, "Evidence file count exceeded")

    visit(root)
    require(fixed <= found, "Required evidence file missing")
    return found


def apk_rows(value):
    require(type(value) is list, "APK records required")
    names = set()
    for row in value:
        require(type(row) is dict and {"P", "V", "A"} <= set(row) <= APK_KEYS, "APK record fields differ")
        for key, item in row.items():
            text(item)
            require(type(key) is str, "APK metadata key differs")
        require(row["P"] and row["V"] and row["A"] and row["P"] not in names, "APK identity differs")
        names.add(row["P"])
    return {row["P"]: row["V"] for row in value}


def apk_database(raw):
    rows = []
    for block in raw.decode("utf8").split("\n\n"):
        row = {}
        for line in block.splitlines():
            if len(line) > 2 and line[1] == ":" and line[0] in APK_KEYS:
                require(line[0] not in row, "Duplicate APK database field")
                row[line[0]] = line[2:]
        if "P" in row:
            rows.append(row)
    apk_rows(rows)
    return rows


def command_result(value, log=None, argv=None, positive=None):
    require(type(value) is dict and COMMAND_FIELDS <= set(value), "Command result fields differ")
    if positive is not None:
        exact(value, COMMAND_FIELDS)
    strings(value["argv"])
    require(type(value["returncode"]) is int and type(value["timed_out"]) is bool,
            "Command outcome types differ")
    require(type(value["seconds"]) in (int, float) and math.isfinite(value["seconds"])
            and value["seconds"] >= 0, "Command duration differs")
    integer(value["log_bytes"], 0, MAX_LOG)
    hex_value(value["log_sha256"])
    if log is not None:
        require(len(log) == value["log_bytes"] and sha(log) == value["log_sha256"], "Command log hash differs")
    if argv is not None:
        require(value["argv"] == argv, "Native command vector differs")
    if positive is not None:
        require(not value["timed_out"] and ((value["returncode"] == 0) is positive), "Native command outcome differs")


def apk_receipt(prefix, phase, lock, pins, bodies):
    value = json_object(bodies[prefix + "/receipt.json"])
    exact(value, {"schema", "release_accepted", "lock_sha256", "keyring", "index", "solver", "packages",
                  "installation", "before", "after", "base_package_artifacts_verified_by_this_step"})
    require(value["schema"] == "metodobase-alpine-apk-receipt-v1" and value["release_accepted"] is False
            and value["base_package_artifacts_verified_by_this_step"] is False, "APK receipt scope differs")
    require(value["lock_sha256"] == pins["input_sha256"]["apk-" + phase + ".lock.json"], "APK lock hash differs")
    require(type(value["keyring"]) is list, "APK keyring required")
    keys = {}
    for row in value["keyring"]:
        exact(row, {"name", "sha256"})
        require(row["name"] not in keys, "Duplicate APK key")
        keys[row["name"]] = hex_value(row["sha256"])
    require(keys == pins["apk_keyring"], "APK keyring differs")
    index = value["index"]
    exact(index, {*pins["apk_index"], "actual_sha256", "verification", "empty_trust_negative_control"})
    require(all(index[key] == expected for key, expected in pins["apk_index"].items()), "APK index pin differs")
    archive = bodies[prefix + "/APKINDEX.tar.gz"]
    require(type(index["bytes"]) is int and len(archive) == index["bytes"]
            and sha(archive) == index["sha256"] == index["actual_sha256"], "APK index archive differs")
    work = "/opt/apk-work/" + phase
    base_args = ["/sbin/apk", "--keys-dir", work + "/keys", "--repositories-file", "/dev/null", "--repository",
                 work + "/repository", "--network=no", "--cache-dir", work + "/cache"]
    command_result(index["verification"], bodies[prefix + "/index-verified.log"], [*base_args, "update"], True)
    negative = ["/sbin/apk", "--keys-dir", work + "/empty-keyring", "--repositories-file", "/dev/null", "--repository",
                work + "/repository", "--network=no", "--cache-dir", work + "/negative-cache", "update"]
    command_result(index["empty_trust_negative_control"], bodies[prefix + "/index-empty-trust-rejected.log"], negative, False)
    roots = [row["name"] + "=" + row["version"] for row in lock["roots"]]
    command_result(value["solver"], bodies[prefix + "/resolved-urls.log"], [*base_args, "fetch", "--recursive", "--url", *roots], True)
    command_result(value["installation"], bodies[prefix + "/installation.log"], [*base_args, "add", *roots], True)
    packages = value["packages"]
    require(type(packages) is list and 1 <= len(packages) <= 128, "APK package count differs")
    package_names, added_versions = set(), set()
    expected_logs = set()
    for number, row in enumerate(packages):
        exact(row, {"filename", "url", "bytes", "sha256", "signed_index_metadata", "verification"})
        metadata = row["signed_index_metadata"]
        apk_rows([metadata])
        filename = metadata["P"] + "-" + metadata["V"] + ".apk"
        require(row["filename"] == filename and filename not in package_names and "/" not in filename
                and "\\" not in filename, "APK package filename differs")
        require(row["url"] == pins["apk_index"]["url"].rsplit("/", 1)[0] + "/" + filename,
                "APK package origin differs")
        integer(row["bytes"], 1, 128 * 1024**2)
        require(type(metadata.get("S")) is str and metadata["S"].isdigit() and int(metadata["S"]) == row["bytes"],
                "APK package byte count differs")
        hex_value(row["sha256"])
        log = prefix + f"/package-{number:03d}-verified.log"
        expected_logs.add(log)
        command_result(row["verification"], bodies[log], ["/sbin/apk", "--keys-dir", work + "/keys", "verify",
                       work + "/repository/x86_64/" + filename], True)
        package_names.add(filename)
        added_versions.add((metadata["P"], metadata["V"]))
    actual_logs = {name for name in bodies if name.startswith(prefix + "/package-")}
    require(actual_logs == expected_logs, "APK verification log set differs")
    before, after = apk_rows(value["before"]), apk_rows(value["after"])
    require(before == pins["base_packages"] and all(after.get(name) == version for name, version in before.items()),
            "APK baseline versions differ")
    require(all(after.get(row["name"]) == row["version"] for row in lock["roots"]), "APK installed root differs")
    require(all((name, after[name]) in added_versions for name in after.keys() - before.keys()), "APK addition lacks receipt")
    if phase.startswith("runtime"):
        require(not ({"libgcc", "libstdc++"} & (after.keys() - before.keys())), "Unreviewed C++ runtime addition")
    require(apk_database(bodies[prefix + "/before-installed.txt"]) == value["before"]
            and apk_database(bodies[prefix + "/after-installed.txt"]) == value["after"], "APK database receipt differs")


def elf_rows(rows):
    require(type(rows) is list, "ELF list required")
    keys = {"path", "sha256", "bytes", "machine", "interpreter", "needed", "soname", "rpath", "runpath",
            "private_wheel_library", "cpp_version_strings", "direct_resolution_candidates"}
    paths = set()
    for row in rows:
        exact(row, keys)
        path = row["path"]
        text(path)
        require(any(path.startswith(prefix + "/") for prefix in ("/bin", "/sbin", "/lib", "/usr", "/opt"))
                and path not in paths, "ELF path differs")
        paths.add(path)
        hex_value(row["sha256"])
        integer(row["bytes"], 1, 512 * 1024**2)
        integer(row["machine"])
        require(row["interpreter"] is None or type(row["interpreter"]) is str, "ELF interpreter differs")
        require(type(row["private_wheel_library"]) is bool, "ELF private-library type differs")
        for key in ("needed", "soname", "rpath", "runpath", "cpp_version_strings"):
            strings(row[key])
        exact(row["direct_resolution_candidates"], set(row["needed"]))
        for candidates in row["direct_resolution_candidates"].values():
            strings(candidates)


def probes(value, expected, profile):
    imports = value["import_checks"]
    require(type(imports) is list and [row.get("module") for row in imports if type(row) is dict] == expected["import_probes"]
            and len(imports) == len(expected["import_probes"]), "Import probe inventory differs")
    for number, row in enumerate(imports):
        exact(row, {*COMMAND_FIELDS, "module", "log", "diagnostic", "success"})
        command_result(row)
        require(type(row["diagnostic"]) is str and len(row["diagnostic"]) <= 16384, "Import diagnostic bound differs")
        require(type(row["success"]) is bool and row["success"] == (row["returncode"] == 0 and not row["timed_out"])
                and row["log"] == f"import-{number:02d}.log", "Import outcome coherence differs")
        code = "import importlib; importlib.import_module(" + repr(row["module"]) + "); print('IMPORT_OK')"
        require(row["argv"] == ["/usr/local/bin/python", "-I", "-B", "-c", code], "Import command differs")
    functions = value["function_checks"]
    expected_names = ["psycopg_libpq", "stdlib_xml_sqlite"] + (["pillow_features"] if profile == "web" else [])
    require(type(functions) is list and [row.get("name") for row in functions if type(row) is dict] == expected_names
            and len(functions) == len(expected_names), "Function probe inventory differs")
    for row in functions:
        exact(row, {*COMMAND_FIELDS, "name", "diagnostic"})
        command_result(row)
        require(type(row["diagnostic"]) is str and len(row["diagnostic"]) <= 16384, "Function diagnostic bound differs")
        require(row["argv"] == ["/usr/local/bin/python", "-I", "-B", "-c", FUNCTION_PROBES[row["name"]]],
                "Function command differs")


def inventory(value, profile, pins, expected, payloads, bodies):
    exact(value, INVENTORY_FIELDS)
    uid, count, _recipe, _lock = PROFILES[profile]
    require(value["schema"] == SCHEMA and value["profile"] == profile and value["release_accepted"] is False
            and value["base"] == BASE, "Inventory scope differs")
    require(type(value["uid"]) is int and type(value["gid"]) is int and value["uid"] == value["gid"] == uid,
            "Inventory identity differs")
    expected_hashes = {name: sha(raw) for name, raw in payloads.items()}
    require(value["source_sha256"] == expected_hashes and type(value["source_sha256"]) is dict,
            "Eleven source byte hashes differ")
    distributions = value["distributions"]
    require(type(distributions) is list and len(distributions) == count, "Distribution count differs")
    actual = {}
    for row in distributions:
        exact(row, {"name", "version", "metadata_sha256"})
        text(row["name"])
        text(row["version"])
        hex_value(row["metadata_sha256"])
        require(row["name"] not in actual, "Duplicate runtime distribution")
        actual[row["name"]] = row["version"]
    require(actual == expected["distributions"], "Exact runtime distributions differ")
    apk_rows(value["apk"])
    hex_value(value["apk_database_sha256"])
    runtime_prefix = "dependency-evidence/apk-runtime-" + profile
    runtime = json_object(bodies[runtime_prefix + "/receipt.json"])
    require(same(value["apk"], runtime["after"])
            and value["apk_database_sha256"] == sha(bodies[runtime_prefix + "/after-installed.txt"]),
            "Runtime APK inventory and final database receipt differ")
    elf_rows(value["elf"])
    require(type(value["elf_errors"]) is list, "ELF errors required")
    for row in value["elf_errors"]:
        exact(row, {"path", "error_type"})
        text(row["path"])
        require(type(row["error_type"]) is str and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]{0,63}", row["error_type"]),
                "ELF error type differs")
    probes(value, expected, profile)
    native = value["native"]
    exact(native, {"python", "soabi", "ext_suffix", "headers_sha256", "interpreter_sha256", "ssl"})
    require(native["python"] == pins["python_version"], "Native Python differs")
    for key in ("soabi", "ext_suffix", "ssl"):
        text(native[key])
    hashes(native["headers_sha256"])
    require(native["interpreter_sha256"] == pins["base_interpreter"]["sha256"], "Native interpreter differs")
    ca = value["ca"]
    exact(ca, {"bundle_path", "sha256", "default_context_ca_der_sha256", "default_verify_paths", "acceptance", "SPKI_and_certifi_policy_proof_pending"})
    text(ca["bundle_path"])
    hex_value(ca["sha256"])
    require(type(ca["default_context_ca_der_sha256"]) is list, "CA observation list differs")
    for digest in ca["default_context_ca_der_sha256"]:
        hex_value(digest)
    exact(ca["default_verify_paths"], {"cafile", "capath", "openssl_cafile_env", "openssl_cafile", "openssl_capath_env", "openssl_capath"})
    require(type(ca["default_verify_paths"]) is dict and all(type(name) is str and (item is None or type(item) is str)
            for name, item in ca["default_verify_paths"].items()), "CA default paths differ")
    require(ca["acceptance"] is False and ca["SPKI_and_certifi_policy_proof_pending"] is True,
            "CA observation cannot grant acceptance")
    receipts = {name.removeprefix("dependency-evidence/"): sha(raw) for name, raw in bodies.items()
                if name.startswith("dependency-evidence/")}
    require(value["receipts"] == receipts and type(value["receipts"]) is dict, "Complete receipt hash universe differs")
    require(value["limitations"] == pins["pending_acceptance"], "Exploration limitations differ")
    exact(value["public_artifact_bounds"], {"max_json_bytes", "max_publication_bytes"})
    require(type(value["public_artifact_bounds"]["max_json_bytes"]) is int
            and type(value["public_artifact_bounds"]["max_publication_bytes"]) is int
            and value["public_artifact_bounds"] == {"max_json_bytes": MAX_FILE, "max_publication_bytes": MAX_TOTAL},
            "Inventory byte bounds differ")
    require(same(value["elf_scope"], {"roots": ["/bin", "/sbin", "/lib", "/usr", "/opt"],
            "private_libraries_included": True, "static_parser_errors_are_not_absence": True,
            "direct_candidates_are_not_complete_loader_resolution": True, "dlopen_and_PBDS_source_provenance_pending": True}),
            "ELF observation limitations differ")


def evidence(profile, pins, expected, payloads, bodies):
    expected_hashes = {name: sha(raw) for name, raw in payloads.items()}
    for name in ("dependency-evidence/base.json", "dependency-evidence/build/base.json"):
        value = json_object(bodies[name])
        exact(value, {"release_accepted", "base", "apk", "apk_database_sha256", "ca", "interpreter", "source_sha256"})
        require(value["release_accepted"] is False and value["base"] == BASE
                and apk_rows(value["apk"]) == pins["base_packages"]
                and value["apk_database_sha256"] == pins["base_apk_database_sha256"]
                and same(value["ca"], pins["base_ca"]) and same(value["interpreter"], pins["base_interpreter"])
                and value["source_sha256"] == expected_hashes, "Base receipt differs")
    for phase, prefix in (("runtime-" + profile, "dependency-evidence/apk-runtime-" + profile),
                          ("build", "dependency-evidence/build/apk-build")):
        lock = json_object(payloads["apk-" + phase + ".lock.json"])
        require(lock.get("profile") == phase and lock.get("release_accepted") is False,
                "APK source lock scope differs")
        apk_receipt(prefix, phase, lock, pins, bodies)
    wheels = json_object(bodies["dependency-evidence/build/wheels.json"])
    exact(wheels, {"profile", "release_accepted", "wheels", "psycopg_source", "external_artifact_urls_measured"})
    require(wheels["profile"] == profile and wheels["release_accepted"] is False
            and wheels["external_artifact_urls_measured"] is False and wheels["psycopg_source"] == pins["psycopg_source"],
            "Wheel receipt scope differs")
    require(type(wheels["wheels"]) is list and len(wheels["wheels"]) == len(expected["distributions"]), "Wheel count differs")
    by_name, by_filename = {}, {}
    for row in wheels["wheels"]:
        exact(row, {"filename", "bytes", "sha256", "name", "version", "metadata_sha256", "origin", "embedded_library_members"})
        text(row["filename"])
        require(re.fullmatch(r"[A-Za-z0-9_.+-]+[.]whl", row["filename"]) is not None, "Wheel metadata filename differs")
        integer(row["bytes"], 1)
        hex_value(row["sha256"])
        hex_value(row["metadata_sha256"])
        text(row["name"])
        text(row["version"])
        normalized = re.sub(r"[-_.]+", "-", row["name"]).lower()
        require(normalized not in by_name and row["filename"] not in by_filename, "Duplicate wheel identity")
        require(row["origin"] == ("reviewed psycopg source build" if normalized == "psycopg2" else "hash-locked PyPI wheel"),
                "Wheel metadata origin differs")
        strings(row["embedded_library_members"])
        by_name[normalized] = row
        by_filename[row["filename"]] = row
    require({name: row["version"] for name, row in by_name.items()} == expected["distributions"], "Wheel distributions differ")
    expected_lock = ("psycopg2==2.9.13 --hash=sha256:" + by_name["psycopg2"]["sha256"] + "\n").encode()
    require(bodies["dependency-evidence/build/python-build/built-wheel.lock"] == expected_lock, "Built wheel lock differs")
    report = json_object(bodies["dependency-evidence/build/python-build/application-install.json"])
    require(report.get("version") == "1" and type(report.get("pip_version")) is str
            and type(report.get("environment")) is dict and type(report.get("install")) is list
            and len(report["install"]) == len(expected["distributions"]), "Pip installation report differs")
    installed = {}
    for item in report["install"]:
        require(type(item) is dict and type(item.get("metadata")) is dict and type(item.get("download_info")) is dict,
                "Pip installation metadata differs")
        name, version = item["metadata"].get("name"), item["metadata"].get("version")
        text(name)
        text(version)
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        require(normalized not in installed, "Duplicate pip distribution")
        installed[normalized] = version
        info = item["download_info"]
        text(info.get("url"))
        parsed = urllib.parse.urlsplit(info["url"])
        filename = urllib.parse.unquote(parsed.path).removeprefix("/opt/wheels/")
        require(parsed.scheme == "file" and parsed.netloc == "" and parsed.path.startswith("/opt/wheels/")
                and filename in by_filename and by_name[normalized] is by_filename[filename], "Pip installed wheel origin differs")
        require(type(info.get("archive_info")) is dict and type(info["archive_info"].get("hashes")) is dict
                and info["archive_info"]["hashes"].get("sha256") == by_filename[filename]["sha256"],
                "Pip wheel hash differs")
    require(installed == expected["distributions"], "Pip installed distributions differ")


def publish(*, extracted, public, repository, profile, source, image_id):
    require(profile in PROFILES, "Unknown profile")
    hex_value(source, 40)
    require(type(image_id) is str and re.fullmatch(r"sha256:[0-9a-f]{64}", image_id), "Invalid image IID")
    extracted, public, repository = directory(extracted), directory(public), directory(repository)
    require(not public.is_relative_to(extracted) and not extracted.is_relative_to(public)
            and not public.is_relative_to(repository) and not extracted.is_relative_to(repository),
            "Publication boundaries overlap")
    require({path.name for path in public.iterdir()} == {"context.json"}, "Only prior context may be public")
    observed = {}
    context_raw = read(public / "context.json", observed)
    context = json_object(context_raw)
    exact(context, {"schema", "profile", "source_commit", "run_id", "attempt", "release_accepted", "purpose"})
    require(context["schema"] == "alpine-exploration-context-v1" and context["profile"] == profile
            and context["source_commit"] == source and context["release_accepted"] is False
            and type(context["run_id"]) is str and re.fullmatch(r"[0-9]+", context["run_id"])
            and type(context["attempt"]) is str and re.fullmatch(r"[1-9][0-9]*", context["attempt"])
            and context["purpose"] == "Dependency inventory only; no application deployment or release approval.",
            "Prior context identity differs")
    pins, expected, payloads = repository_inputs(repository, profile, observed)
    found = scan(extracted, profile)
    bodies, records, total = {}, {}, 0
    for name in sorted(found):
        body = read(extracted / name, observed)
        total += len(body)
        require(total <= MAX_TOTAL, "Aggregate extracted byte bound exceeded")
        bodies[name] = body
        records[name] = {"bytes": len(body), "sha256": sha(body)}
    require(bodies["image.iid"] in {image_id.encode(), (image_id + "\n").encode()}, "Extracted image IID differs")
    value = json_object(bodies["inventory.json"])
    inventory(value, profile, pins, expected, payloads, bodies)
    evidence(profile, pins, expected, payloads, bodies)
    receipt = {"schema": "alpine-exploration-extraction-v2", "source_commit": source, "profile": profile,
               "image_id": image_id, "release_accepted": False, "files": records, "total_extracted_bytes": total,
               "trust": "Caller verifies checkout HEAD and exact stopped image IID; copied source byte hashes checked here. No release, ABI or SCA acceptance."}
    raw = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    require(len(raw) <= MAX_FILE, "Publication receipt bound exceeded")
    # The public budget includes the context which already exists and the
    # receipt written last, in addition to every validated extracted body.
    require(len(bodies) + 2 <= MAX_FILES, "Complete public file count exceeded")
    require(len(context_raw) + total + len(raw) <= MAX_TOTAL, "Complete public byte bound exceeded")
    quiet(observed)
    require(scan(extracted, profile) == found and {path.name for path in public.iterdir()} == {"context.json"},
            "Publication inventory changed before write")
    # No candidate bytes reach public until all names, bodies and provenance
    # have passed. A receipt is written last; context-only is not acceptance.
    for name, body in bodies.items():
        destination = public / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        directory(destination.parent)
        with destination.open("xb") as stream:
            stream.write(body)
    with (public / "extraction-receipt.json").open("xb") as stream:
        stream.write(raw)
    quiet(observed)
    return receipt


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise ValueError("Invalid publication arguments")


def main(argv=None):
    parser = Parser(description=__doc__, allow_abbrev=False)
    for name in ("extracted", "public", "repository"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--image-id", required=True)
    try:
        result = publish(**vars(parser.parse_args(argv)))
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError, OverflowError):
        print(json.dumps({"status": "failed", "reason": "alpine_publication_rejected", "release_accepted": False}))
        return 2
    print(json.dumps({"status": "published", "profile": result["profile"], "files": len(result["files"]),
                      "release_accepted": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
