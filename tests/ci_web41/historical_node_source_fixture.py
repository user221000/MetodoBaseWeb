"""Explicit historical Node unit inputs, separate from current Node execution.

Authenticate all current counterparts before recovering the complete Git52
input graph. Original maps, guards, programs and criteria remain unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path

from tests.ci_web37 import node_current
from tests.ci_web39 import new38_sources

SOURCE_COMMIT = "52c97010793865e6e155d928c4ef1eb88b1a0bdc"
CURRENT_SOURCE_COMMIT = "560fd71f115cf4704073bc9e3f15577dee7a8c9f"
MAX_BYTES = 2 * 1024 * 1024
MAP_PINS = {
    "tests/ci_web38/node-new38.json": {
        "bytes": 7669,
        "git_blob": "59ad92e33f65e86abf6d88c853a4e811c8e83720",
        "sha256": "b3a583ab6c704cfb77bd46af0127bdabd07ea36e0a92416c6597401df2f9c04c"
    },
    "tests/ci_web39/node-new38-current39.json": {
        "bytes": 10538,
        "git_blob": "24592c4654a099e33d37d8ac92a8fc90e5f68b35",
        "sha256": "8d6c78ffd0bb465c44aa897fd95cafe737625a3a55b49567a8e1bac33b9faf8d"
    },
    "tests/ci_web39/node-routines-onboarding39.json": {
        "bytes": 17431,
        "git_blob": "5e7da124239d776fac7d7be887782fa76d0c4d46",
        "sha256": "d24e6adf221ade25f84282b64afa705bf0a1c8fd8646c0ff40096e5698365036"
    }
}
HISTORICAL_PINS = {
    "core/routine_catalog.py": {
        "bytes": 9475,
        "git_blob": "3137474ea08419c2aca0b1ceeec0fcc344c68273",
        "sha256": "c55fe4905b631fad34d692ec183e05fba7950d693c649e529d684673f7090eac"
    },
    "tests/ci_web37/fixtures/security-browser31-6ee27e3c.cjs.RAW": {
        "bytes": 15161,
        "git_blob": "33056598789034d004377bc063853456e478eaa7",
        "sha256": "4c8581ac6280f67fbfb201a6cfa30ea41b72948a3cf3bd493fe1bc3d3f320602"
    },
    "tests/e2e/account_security37_transport.cjs": {
        "bytes": 10233,
        "git_blob": "5434e090257758f4cd19ccddd3329bd3f1fa01a7",
        "sha256": "7e9fd4998a0abe9534da96c070c33d70c28870dd05f59d1bc80901835bb80cbb"
    },
    "tests/e2e/browser_harness31.cjs": {
        "bytes": 2428,
        "git_blob": "d4ecd1ff8d205c09af0dcf62cb745b8561a4b32a",
        "sha256": "5e67436a274ec0c42a96a7c65107225f9d5b5cde742fd87d5281cba1db620956"
    },
    "tests/e2e/browser_offline31.cjs": {
        "bytes": 828,
        "git_blob": "1fe2744273b53bac1eb5cb5d1c33ebb527381c6d",
        "sha256": "527ff6bf0fe18c05bc8f92302ad3d9d2d782b3fc0c3460cf145b18639c415f9d"
    },
    "tests/e2e/browser_session31.cjs": {
        "bytes": 30621,
        "git_blob": "c4603bca6741ca27e7c2b54a5ae55330224ad6a4",
        "sha256": "b94d2ce9647270c02ec58bf607ae0a5a807e328586ffb78d6c14b0431f7a6250"
    },
    "tests/e2e/ci_web37_offline.cjs": {
        "bytes": 1383,
        "git_blob": "52515f2d12098ce58911a4c14e74768aa63d3ea1",
        "sha256": "5062d2e2e42fbcd673ad15563e5bf6a55ebc7b0bc019488597d75c2e27c8e20d"
    },
    "tests/e2e/new-password-minimum-review.cjs": {
        "bytes": 9820,
        "git_blob": "396e1dd1cadd055c23b41c684bfb9f416e13d5b8",
        "sha256": "208241b27b78e5f47a39969b4a799c5dcdce94826b41ea8dba38d20464136eb4"
    },
    "tests/e2e/onboarding22_facts.cjs": {
        "bytes": 3397,
        "git_blob": "362ca1114c6e857273ce98bb737e9f7606d6be1d",
        "sha256": "084731b5e3bd157421be72ef50f08b2e3920f99e22fe005c9386def249ba16aa"
    },
    "tests/e2e/onboarding22_personal.cjs": {
        "bytes": 2995,
        "git_blob": "3b7567ba701e84db5c15eb3b793fe798766a0299",
        "sha256": "13d4a32436216fafa607d5ae56966b3d89249af2c57dc4585f3cce360e6ff3e5"
    },
    "tests/e2e/product-analytics-v2-review.cjs": {
        "bytes": 8731,
        "git_blob": "a16d3fc596aed3fc217df3819ab1f3b4e458dc66",
        "sha256": "8195c8b9f9eadbde8eef4e5e62b22f9536781218b123a9c163c954444651dc9e"
    },
    "tests/e2e/routines_access_fences.cjs": {
        "bytes": 2295,
        "git_blob": "8c614e5bdca24d22ceb46dd1f593862997495678",
        "sha256": "26367fae59d9583a17801da9d569da074a288d40a962a89453aee11dab5f42bf"
    },
    "tests/e2e/routines_navigation.cjs": {
        "bytes": 3625,
        "git_blob": "bc0b11451a571f1e812a95b7cdcc0d1db219d55c",
        "sha256": "57310c65db31ed8b922c1ec06cece9f5136cbcdebddf90cf601ddaa12e0d6cc8"
    },
    "tests/e2e/routines_panel.cjs": {
        "bytes": 7213,
        "git_blob": "94fc6bdacd63cd65e51845415aaaabee0e429a7b",
        "sha256": "13bd0718e7a64156a679af625c105c79d5de3d7296d45bb6d142c4b949aec59d"
    },
    "tests/e2e/security_onboarding22_peer.cjs": {
        "bytes": 14231,
        "git_blob": "7c17c073e0653b1b6cd39b108550e5a7718eaa2e",
        "sha256": "5b152e16b9a570b8a0303f6efbbd61ea3397296be7295509fcba9bd5a53d0a0d"
    },
    "tests/e2e/security_routines_dom_peer.cjs": {
        "bytes": 8018,
        "git_blob": "04468f08f63ddca108dc687c12a9e33eebb3da62",
        "sha256": "39c2ae0eaaedf2bb6b7bdabd42716b16c3dbdab7dcdb2eed609458404acecc3a"
    },
    "tests/e2e/security_routines_transport_peer.cjs": {
        "bytes": 3897,
        "git_blob": "240453639687e3d966f545016786162ef60767da",
        "sha256": "22c05682cb9fbff7ef3f9c4782d40d33a31e26284a1cdd9865ff27bbc7b024ec"
    },
    "web/static/js/accept-invite.js": {
        "bytes": 6359,
        "git_blob": "53b8c81b4cfc285fd9584d41bba0b0119bff4e26",
        "sha256": "7b75ff8b10bfcbb1d5fa3237833960fce843e912ca3949c37c639479e7aca84d"
    },
    "web/static/js/account-recovery.js": {
        "bytes": 4373,
        "git_blob": "7be96c27278ea9db4f892ebc31ab8d7f16cd0ea0",
        "sha256": "721e0615647fbf4beb379cc1a98992f1d189a43f5c968d5ef156592dec9143ec"
    },
    "web/static/js/account-security37.js": {
        "bytes": 15159,
        "git_blob": "7d0f370c5f26d9af623eb3e487d5b18e5f66c5ca",
        "sha256": "6a748bc58dd8de98e4b9d1828013a7969f248dfeeb6f606388dcc729b2ed7098"
    },
    "web/static/js/api.js": {
        "bytes": 93383,
        "git_blob": "eb6bf83d7184065196a1439cc8dca4f242c5bf87",
        "sha256": "1c3b263f359d9b37ede6893134f212879b05615f56f0c143922c3d4c1c2b6f82"
    },
    "web/static/js/auth-guard.js": {
        "bytes": 4624,
        "git_blob": "c9a6c0cc897471f5a9a7055282cf2a51ffb742f1",
        "sha256": "52887e05c3456c9f8815946b54bf1ec37720d295e62771d1473b4620a092131a"
    },
    "web/static/js/main.js": {
        "bytes": 10484,
        "git_blob": "1c38b048d6f7aefd462abe9a38a01f02e907a205",
        "sha256": "e70a2ca02e796a402fa8a7537af37b3f37745c5bedafa02e9922947d7e7df87a"
    },
    "web/static/js/product-analytics-v2.js": {
        "bytes": 4160,
        "git_blob": "64f2b2e2e959b1cbf387de48c51325ab0c2fdf4f",
        "sha256": "287fc62c5c7810c128361193a46969318cbf9f6fe1fa5984fb02bed7a3fc39c5"
    },
    "web/static/js/rutinas.js": {
        "bytes": 12199,
        "git_blob": "edd34419f3f5b678b954d25d5253ac00a7957442",
        "sha256": "dd19370f76a737fdeabe6ae52f6e72ef2d83d74f72fab7a465093a707f8a1be3"
    },
    "web/static/js/session-shell.js": {
        "bytes": 1756,
        "git_blob": "624389d42c01d023d7e2449e1847e231f214865a",
        "sha256": "8822a957f3807f252a5b051f5a9a127e1cc2775f5b4358251bf70a30a8f7926b"
    },
    "web/static/js/usuario-plan-operacion.js": {
        "bytes": 6254,
        "git_blob": "5ff8acd7c918c73c11285f196b9edd9f7eef5fb3",
        "sha256": "0f3adf6cfdc9edb4b02839814c3ff7f6ffc932014bf63a3631189fa32aa50217"
    },
    "web/templates/accept_invite.html": {
        "bytes": 2891,
        "git_blob": "2f9da43568332e5b6189cfa901f2b4494071d77b",
        "sha256": "b56be1dee4c6deeee823439305a869ca73b05350880d6a393504c8ef243581a8"
    },
    "web/templates/account_recovery.html": {
        "bytes": 1890,
        "git_blob": "f412ed630f8dad10dc6f92efeed258c3588f9584",
        "sha256": "d82ddbe27853b4794a72f7f4e6b4093bb1fb3d567ab7d5f562b53df182dd635b"
    },
    "web/templates/registro.html": {
        "bytes": 9804,
        "git_blob": "9b639005642ce2f6e4481ca8dd403b1874153fa1",
        "sha256": "65f20a1478e8f60a6eddabaf4fabc1b9651cc5177cf6bb8bb746fc5ab6f7c519"
    },
    "web/templates/usuario_mi_plan.html": {
        "bytes": 40884,
        "git_blob": "f4f1745f175566772018d3ad9f35c2c33d2d9fbc",
        "sha256": "ac889684dd9517e847de475d772f43d1cf7cd8a2f53fff1817781e67b17926db"
    }
}
CURRENT_CHANGED_PINS = {
    "core/routine_catalog.py": {
        "bytes": 46152,
        "git_blob": "8ae6d3b208a07fd331d6f14f9150903940d1df86",
        "sha256": "d9f17ccc297b829c728ecbed22892ebfd6b8fb4eb77d27daefe2043a470bdc97"
    },
    "tests/e2e/new-password-minimum-review.cjs": {
        "bytes": 10381,
        "git_blob": "cf8b6770ece8a501c37a1c8b19f18c7e996211b0",
        "sha256": "325d036772fbbd37cd48fd6039090b930db9d52e1041625f7c89b8519c15525d"
    },
    "tests/e2e/routines_panel.cjs": {
        "bytes": 8384,
        "git_blob": "9210f644041c655510bbbe9e69f0ae31a1aba519",
        "sha256": "f71e5cc59a651db0dc6232006bcbdeaff92c67b43445cf27682982c884409cc2"
    },
    "tests/e2e/security_routines_dom_peer.cjs": {
        "bytes": 8632,
        "git_blob": "4c5d87205246e7d043b8be3ef552d597120bf821",
        "sha256": "524ed988f44a482898a959b621f39edbfd4eb79dace153b0df9867ef643ba249"
    },
    "web/static/js/api.js": {
        "bytes": 104485,
        "git_blob": "39cc4d04f83db632fd5d23dfa3139dfd5b970690",
        "sha256": "433234a42970c2827bca3bb55d46c6d0ab151ce5e270b9e15a1df8b89d6d5b75"
    },
    "web/static/js/main.js": {
        "bytes": 10424,
        "git_blob": "2237774109d1a14acb994d9fc99e9f791b4f8cdc",
        "sha256": "36a2fa18b5eda28c9ad9b6e5aa0c29565e90a1253013fdc30761da4af9537403"
    },
    "web/static/js/rutinas.js": {
        "bytes": 41742,
        "git_blob": "5b38530eeb3bc1595a34af8f7cab10d27920eb7d",
        "sha256": "516f9df2ddf40ca652352f6b0bc658b104b469e1c908db7131c1b31c96671978"
    },
    "web/templates/accept_invite.html": {
        "bytes": 2973,
        "git_blob": "6ae4f8a0966a0b8773efa92caba58dcb3e30b455",
        "sha256": "6ecc1829c237aeb26b9b3ab78a9976818b0356fb9fdb4de9953ef84f77fffd52"
    },
    "web/templates/account_recovery.html": {
        "bytes": 1972,
        "git_blob": "f237e06c97cde86734cb5caa569ddb370b66d29c",
        "sha256": "5ea9ccf25e1aecd96397a3003827c80d2fc419145a5ed67d0504a7b85177addd"
    },
    "web/templates/registro.html": {
        "bytes": 9931,
        "git_blob": "fc4518394978982ae9007644b954a7352c2a141f",
        "sha256": "cf55e09df1d85e88460203df237d9601eb587480b129648c238ef6228c0f62a0"
    },
    "web/templates/usuario_mi_plan.html": {
        "bytes": 42542,
        "git_blob": "f60535ca4fd12e177b49d76f69acbe4346e192db",
        "sha256": "047c5a7a670b96c201ec416ed5aab7a2ef0de5ed5e8fa3333fa1b65214c1b23c"
    }
}


def record(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                                     usedforsecurity=False).hexdigest()}


def canonical(raw):
    if type(raw) is not bytes:
        raise ValueError("Historical Node source requires bytes")
    lf = raw.replace(b"\r\n", b"\n")
    if b"\r" in lf or raw not in (lf, lf.replace(b"\n", b"\r\n")) or lf.startswith(b"\xef\xbb\xbf"):
        raise ValueError("Only complete uniform LF/CRLF source frames are admitted")
    return lf


def directory(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path or not path.is_dir():
        raise ValueError("An existing canonical absolute source directory is required")
    if any(component.is_symlink() for component in (path, *path.parents)):
        raise ValueError("Source directory links are refused")
    return path


def read_source(root, name):
    path = root / name
    for component in (path, *path.parents):
        if component == root:
            break
        if component.is_symlink():
            raise ValueError("Node fixture source links are refused")
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_BYTES:
        raise ValueError("A bounded regular single-link source is required")
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_nlink")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(MAX_BYTES + 1)
        finished = os.fstat(stream.fileno())
    after = path.stat()
    if (len(raw) != before.st_size or len(raw) > MAX_BYTES
            or any(getattr(before, key) != getattr(after, key) for key in fields)
            or any(getattr(opened, key) != getattr(finished, key) for key in fields)
            or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)):
        raise ValueError("Node source changed while being read")
    return raw


def descriptors(payloads):
    if any(record(canonical(payloads[name])) != pin for name, pin in MAP_PINS.items()):
        raise ValueError("An immutable historical Node descriptor differs")
    additional = json.loads(canonical(payloads["tests/ci_web39/node-routines-onboarding39.json"]))
    new38 = json.loads(canonical(payloads[new38_sources.CURRENT_MAP]))
    new_inputs = {name: pin for row in new38["phases"].values() for name, pin in row["input_files"].items()}
    if (len(additional["input_files"]) != 21 or len(new_inputs) != 14
            or set(additional["input_files"]) | set(new_inputs) != set(HISTORICAL_PINS)
            or len(HISTORICAL_PINS) != 31 or len(CURRENT_CHANGED_PINS) != 11):
        raise ValueError("The exact35 bindings and31 historical Node paths are required")
    for name, pin in additional["input_files"].items():
        if pin["sha256"] != HISTORICAL_PINS[name]["sha256"]:
            raise ValueError("An original additional Node binding differs")
    for name, pin in new_inputs.items():
        if any(pin[key] != HISTORICAL_PINS[name][key] for key in ("bytes", "sha256", "git_blob")):
            raise ValueError("An original38 Node binding differs")
    return additional, new38


def validate_payloads(payloads):
    if type(payloads) is not dict or set(payloads) != {*MAP_PINS, *HISTORICAL_PINS}:
        raise ValueError("The exact34-file historical Node fixture namespace is required")
    descriptors(payloads)
    for name, pin in HISTORICAL_PINS.items():
        if record(canonical(payloads[name])) != pin:
            raise ValueError("An original historical Node source differs")


def git_blob(repository, oid, size):
    if re.fullmatch("[0-9a-f]{40}", oid) is None or type(size) is not int or not 0 < size <= MAX_BYTES:
        raise ValueError("A bounded original Git blob identity is required")
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment.update(GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0",
                       GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    command = ["git", "--no-replace-objects", "-C", str(repository), "cat-file"]
    measured = subprocess.run([*command, "-s", oid], env=environment, capture_output=True,
                              check=True, timeout=15).stdout
    if measured != str(size).encode() + b"\n":
        raise ValueError("The historical Node Git blob size differs")
    raw = subprocess.run([*command, "blob", oid], env=environment, capture_output=True,
                         check=True, timeout=15).stdout
    if len(raw) != size:
        raise ValueError("The historical Node Git payload size differs")
    return raw


def historical_payloads(repository):
    repository = directory(repository)
    actual = {name: read_source(repository, name) for name in (*MAP_PINS, *HISTORICAL_PINS)}
    descriptors(actual)
    for name, pin in HISTORICAL_PINS.items():
        expected = CURRENT_CHANGED_PINS.get(name, pin)
        if record(canonical(actual[name])) != expected:
            raise ValueError("An authenticated current Node counterpart differs")
    historical = {name: canonical(actual[name]) for name in MAP_PINS}
    for name, pin in HISTORICAL_PINS.items():
        historical[name] = git_blob(repository, pin["git_blob"], pin["bytes"])
    validate_payloads(historical)
    if any(read_source(repository, name) != raw for name, raw in actual.items()):
        raise ValueError("A current Node source changed during fixture preparation")
    return historical


def validate_fixture(root):
    root = directory(root)
    entries = list(root.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise ValueError("Node fixture source links are refused")
    names = {*MAP_PINS, *HISTORICAL_PINS}
    if {path.relative_to(root).as_posix() for path in entries if not path.is_dir()} != names:
        raise ValueError("The exact34-file historical Node fixture namespace is required")
    payloads = {name: read_source(root, name) for name in names}
    validate_payloads(payloads)
    additional, _ = descriptors(payloads)
    rows = node_current.require_additional_sources(root, additional)
    mapping = new38_sources.load_mapping(root)
    for entry in mapping["phases"].values():
        new38_sources.require_sources(root, entry)
    return rows, mapping


def materialize(repository, destination):
    destination = Path(destination)
    if (not destination.is_absolute() or destination.exists()
            or directory(destination.parent) / destination.name != destination):
        raise ValueError("A new canonical absolute fixture destination is required")
    payloads = historical_payloads(repository)
    destination.mkdir(mode=0o700)
    for name, raw in payloads.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    validate_fixture(destination)
    return destination
