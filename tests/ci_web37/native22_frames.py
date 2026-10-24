"""Two authenticated old Windows frames for one unchanged native source oracle.

The host retains canonical Git LF. Only the original22 helper-byte assertion
sees the separately retained Windows preimages of these two named paths.
"""
import hashlib
import json
from pathlib import Path
from types import FunctionType

from tests.ci_web37.git_recipe import OID, ObjectProof

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).with_name("fixtures")
ANCHOR = "b21b62c0711b3e277399bbe0a2686d1f89ab3249"
MANIFEST = "tests/e2e/native37_transitive_qa_v6.json"
NAMES = ("alembic.ini", "db_bootstrap.py")
FIXTURE_SHA256 = "f6f5a21fed26f73e32ef2d7b202a19b09e601d54522a2e309f1be5944b428a08"
TEST_NAME = "test_derived_harness_has_exact_full_inverse_and_original22_RAW_are_unchanged"
TEST_SOURCE_SHA256 = {
    "7b1d9bd8b19fdb679a50f66c1a1af2940d7766cfaa4a02b24a77ad92a2fd0a4a",
    "226d9b782dadf983a28cd9e8e9af6afb988c8c6a3ed5ec6a0178900e425bbbcd",
    "b283b8a12cac4570a1957f8531394536bb690ead6212f506817dc93989d63c70",
}


class Native22Proof(ObjectProof):
    def root_tree(self, commit):
        if commit != ANCHOR:
            raise ValueError("Native22 commit authority differs")
        first = self.get(commit, "commit").split(b"\n", 1)[0]
        if not first.startswith(b"tree ") or OID.fullmatch(first[5:].decode("ascii")) is None:
            raise ValueError("Native22 original root tree differs")
        return first[5:].decode("ascii")


class OriginalFrames:
    def __init__(self, directory=FIXTURES):
        raw = (directory / "native22-original-objects.zip").read_bytes()
        if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
            raise ValueError("Native22 finite object fixture differs")
        self.proof = Native22Proof(raw)
        self.manifest_bytes = self.proof.blob(ANCHOR, MANIFEST)
        self.manifest = json.loads(self.manifest_bytes)
        if len(self.manifest["helper_union"]) != 22:
            raise ValueError("Native22 original inventory differs")
        self.git_lf = {name: self.proof.blob(ANCHOR, name) for name in NAMES}
        self.original = {}
        for name in NAMES:
            frame = (directory / ("native22-original-" + name + ".RAW")).read_bytes()
            if hashlib.sha256(frame).hexdigest() != self.manifest["helper_union"][name]["raw_sha256"]:
                raise ValueError("Native22 retained Windows preimage differs")
            self.original[name] = frame
        if self.proof.used != self.proof.objects.keys():
            raise ValueError("Native22 object fixture contains an unused authority")

    def original_frame(self, name, observed):
        if type(name) is not str or name not in NAMES or type(observed) is not bytes:
            raise ValueError("Native22 transport permits only its two exact paths")
        if observed != self.git_lf[name]:
            raise ValueError("Native22 host is not its exact authenticated Git LF source")
        return self.original[name]


class _OriginalPath:
    def __init__(self, root, name, proof):
        self.root, self.name, self.proof = root, name, proof

    def read_bytes(self):
        return self.proof.original_frame(self.name, (self.root / self.name).read_bytes())


class _OriginalRoot:
    def __init__(self, root, proof):
        self.root, self.proof = root, proof

    def __truediv__(self, name):
        return _OriginalPath(self.root, name, self.proof) if name in NAMES else self.root / name


def export():
    from tests import test_security_native35_v7_peer as original
    if hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest() not in TEST_SOURCE_SHA256:
        raise ValueError("Native V7 original assertion source differs")
    proof = OriginalFrames()
    if (ROOT / MANIFEST).read_bytes() != proof.manifest_bytes:
        raise ValueError("Native22 current manifest is not the authenticated original")
    for name, record in proof.manifest["helper_union"].items():
        if name in NAMES:
            proof.original_frame(name, (ROOT / name).read_bytes())
        elif hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != record["raw_sha256"]:
            raise ValueError("An untransported original20 helper changed")
    value = getattr(original, TEST_NAME)
    namespace = dict(vars(original), ROOT=_OriginalRoot(ROOT, proof))
    copied = FunctionType(value.__code__, namespace, value.__name__, value.__defaults__, value.__closure__)
    copied.__kwdefaults__ = value.__kwdefaults__
    copied.__dict__.update(value.__dict__)
    copied.__annotations__ = dict(value.__annotations__)
    return {TEST_NAME: copied}
