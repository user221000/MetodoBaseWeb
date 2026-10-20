"""Independent current V5 artifact/loader review, not a new full secret scan.

The 750 named-source semantic witnesses already reviewed are not re-audited.
This checks the actual active loader, exact finite data union and new boundaries.
"""
import ast
import hashlib
import io
import json
import subprocess
import zipfile
from functools import cache
from pathlib import Path

import pytest

from scripts import reviewed_scan_locations as review

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "c60b7f4554c2e640faad805571d00fc0973fd45c"
SCAN_SOURCE = "8d6b18521c719ff789ebd32c493457b6810b2b48"
PROPOSAL = "docs/implementation/20261018-evolution/evidence/security-r05-753-independent-20261020/finite-proposal.zip"
CRLF_PATHS = ("docs/implementation/20261018-evolution/CUENTA_SEGURIDAD37_UI_IMPLEMENTACION.json",
              "docs/implementation/20261018-evolution/NOTIFICACIONES_R27_UI_IMPLEMENTACION.json",
              "tests/e2e/notifications36_bootstrap.cjs")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@cache
def git(commit, path):
    return subprocess.check_output(["git", "--no-replace-objects", "show", commit+":"+path], cwd=ROOT)


@cache
def data(path):
    with zipfile.ZipFile(ROOT/path) as archive:
        return json.loads(archive.read("reviewed-locations.json"))


@cache
def proposal():
    with zipfile.ZipFile(ROOT/PROPOSAL) as archive:
        return json.loads(archive.read("proposal.json"))


def test_loader_algorithm_is_ast_exact_after_only_three_declared_literal_changes():
    before = ast.parse(git(SOURCE+"^", "scripts/reviewed_scan_locations.py"))
    after = ast.parse((ROOT/"scripts/reviewed_scan_locations.py").read_bytes())
    replacements = {"scripts/data/reviewed_scan_locations_v5.zip": "scripts/data/reviewed_scan_locations_v4.zip",
                    "5b847d2d632721d043199ec5658b48e96dc6796712b4692e1a79b68fa3b932f6":
                    "6fe9473bbe1ab1902853b8f2b29d92f43972de81ce67612b3afc2c624f74cb13",
                    "finite independently reviewed non-credential evidence; registry v5":
                    "finite independently reviewed non-credential evidence; registry v4"}

    class Restore(ast.NodeTransformer):
        changed = 0

        def visit_Constant(self, node):
            if isinstance(node.value, str) and node.value in replacements:
                self.changed += 1
                return ast.Constant(replacements[node.value])
            return node

    restore = Restore()
    assert ast.dump(restore.visit(after), include_attributes=False) == ast.dump(before, include_attributes=False)
    assert restore.changed == 3
    for path in ("scripts/scan_secrets.py", ".gitleaks.toml",
                 "scripts/data/reviewed_scan_locations_v3.zip", "scripts/data/reviewed_scan_locations_v4.zip"):
        assert git(SOURCE, path) == git(SOURCE+"^", path)


def test_v4_history_test_changes_only_two_registry_reader_arguments_without_assert_changes():
    path = "tests/test_secret_scan_finite_v4.py"
    before = ast.parse(git(SOURCE+"^", path))
    after = ast.parse((ROOT/path).read_bytes())

    class Restore(ast.NodeTransformer):
        changed = 0

        def visit_Call(self, node):
            self.generic_visit(node)
            if (isinstance(node.func, ast.Name) and node.func.id == "registry" and len(node.args) == 1
                    and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value == "scripts/data/reviewed_scan_locations_v4.zip"):
                self.changed += 1
                node.args[0] = ast.Attribute(ast.Name("review", ast.Load()), "_REVIEW_DATA_PATH", ast.Load())
            return node

    restore = Restore()
    assert ast.dump(restore.visit(after), include_attributes=False) == ast.dump(before, include_attributes=False)
    assert restore.changed == 2


def test_attributes_are_exactly_three_finite_crlf_materializations_with_unchanged_git_blobs():
    old = git(SOURCE+"^", ".gitattributes")
    suffix = ("".join(path+" text eol=crlf\n" for path in CRLF_PATHS)+
              "".join(path+" whitespace=cr-at-eol\n" for path in CRLF_PATHS)).encode()
    assert git(SOURCE, ".gitattributes") == old+suffix
    for path in CRLF_PATHS:
        raw = git(SOURCE, path)
        assert raw == git(SOURCE+"^", path) and b"\r" not in raw
        assert (ROOT/path).read_bytes() == raw.replace(b"\n", b"\r\n")


def test_active_v5_zip_is_the_exact_v4_union_plus_the_reviewed_twenty_file_proposal():
    assert review._REVIEW_DATA_PATH == "scripts/data/reviewed_scan_locations_v5.zip"
    assert sha((ROOT/review._REVIEW_DATA_PATH).read_bytes()) == review._REVIEW_DATA_DIGEST == (
        "5b847d2d632721d043199ec5658b48e96dc6796712b4692e1a79b68fa3b932f6")
    old = data("scripts/data/reviewed_scan_locations_v4.zip")
    current = data(review._REVIEW_DATA_PATH)
    before = {row["path"]: row for row in old["files"]}
    after = {row["path"]: row for row in current["files"]}
    added = {row["path"]: row for row in proposal()["files"]}
    assert len(before) == 877 and len(after) == 897 and len(added) == 20
    assert not before.keys() & added.keys() and after == before | added
    canonical = lambda row: json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    assert all(canonical(after[path]) == canonical(row) for path, row in before.items())
    assert sum(len(pin["rules"]) for row in old["files"] for pin in row["lines"]) == 56285
    assert sum(len(pin["rules"]) for row in current["files"] for pin in row["lines"]) == 57038
    for key in ("schema", "version", "config_digest"):
        assert old[key] == current[key]


def prepared(destination, names):
    destination.mkdir(exist_ok=True)
    hashes = {}
    for name in names:
        raw = (ROOT/name).read_bytes()
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        hashes[name] = sha(raw)
    config = (ROOT/".gitleaks.toml").read_bytes()
    (destination/".gitleaks.toml").write_bytes(config)
    hashes[".gitleaks.toml"] = sha(config)
    target = destination/review._REVIEW_DATA_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((ROOT/review._REVIEW_DATA_PATH).read_bytes())
    return hashes


class UntrustedFinding(dict):
    def get(self, key, default=None):
        assert key not in {"Secret", "Match", "Line", "File"}, "Untrusted scanner payload was consulted"
        return super().get(key, default)


def test_all753_proposed_pins_classify_through_the_actual_active_loader(tmp_path):
    hashes = prepared(tmp_path, [row["path"] for row in proposal()["files"]])
    registry = review.load_reviewed_locations(tmp_path, hashes, "8.30.1")
    count = 0
    for record in proposal()["files"]:
        assert hashes[record["path"]] == record["source_digest"]
        for pin in record["lines"]:
            for rule in pin["rules"]:
                finding = UntrustedFinding(StartLine=pin["number"], EndLine=pin["number"], RuleID=rule,
                                           Secret=object(), Match=object(), Line=object(), File="untrusted")
                value = registry.classify(finding, record["path"])
                assert value is not None and value["physical_line_sha256"] == pin["digest"]
                assert value["file_sha256"] == record["source_digest"]
                assert value["reason"].endswith("registry v5")
                count += 1
    assert count == 753


def point(category):
    for row in proposal()["witnesses"]:
        if category == "literal" and row["kind"] == "exact_VM_namespace_identity_assertion":
            return row
        if category in {"current", "historical"} and row["kind"] == "recomputed_named_source_SHA256" and (
                row["witness"]["git_commit"] == SCAN_SOURCE) is (category == "current"):
            return row
    raise AssertionError("Actual reviewed category missing")


@pytest.mark.parametrize("category", ["current", "historical", "literal"])
@pytest.mark.parametrize("fault", ["missing-inventory", "false-inventory", "missing-file", "wrong-rule",
                                  "boolean-start", "boolean-end", "float-start", "multiline", "copy-path",
                                  "other-line", "physical-byte", "adjacent-byte", "eol-flip", "utf8-bom", "utf16"])
def test_active_v5_rejects_each_new_category_boundary(tmp_path, category, fault):
    selected = point(category)
    assert (selected["kind"] == "exact_VM_namespace_identity_assertion") is (category == "literal")
    name = selected["file"]
    hashes = prepared(tmp_path, [name])
    target = tmp_path/name
    original = target.read_bytes()
    finding = UntrustedFinding(StartLine=selected["line"], EndLine=selected["line"], RuleID=selected["rule"])
    if fault == "missing-inventory":
        del hashes[name]
    elif fault == "false-inventory":
        hashes[name] = "0"*64
    elif fault == "missing-file":
        target.unlink()
    elif fault == "wrong-rule":
        finding["RuleID"] = "unreviewed-rule"
    elif fault in {"boolean-start", "boolean-end", "float-start", "multiline", "other-line"}:
        if fault in {"boolean-start", "boolean-end"}:
            finding["StartLine" if fault == "boolean-start" else "EndLine"] = True
        elif fault == "float-start":
            finding["StartLine"] = float(selected["line"])
        elif fault == "multiline":
            finding["EndLine"] += 1
        else:
            finding["StartLine"] = finding["EndLine"] = 2000001
    elif fault == "copy-path":
        name += ".unreviewed"
        (tmp_path/name).write_bytes(original)
        hashes[name] = sha(original)
    elif fault == "physical-byte":
        lines = original.split(b"\n")
        lines[selected["line"]-1] += b" "
        target.write_bytes(b"\n".join(lines))
    elif fault == "adjacent-byte":
        target.write_bytes(original+b" ")
    elif fault == "eol-flip":
        changed = original.replace(b"\r\n", b"\n") if b"\r\n" in original else original.replace(b"\n", b"\r\n")
        assert changed != original
        target.write_bytes(changed)
    elif fault == "utf8-bom":
        target.write_bytes(b"\xef\xbb\xbf"+original)
    else:
        target.write_bytes(b"\xff\xfe"+original.decode("utf8").encode("utf-16-le"))
    assert review.load_reviewed_locations(tmp_path, hashes, "8.30.1").classify(finding, name) is None


@pytest.mark.parametrize("name", CRLF_PATHS)
@pytest.mark.parametrize("inventory", ["original", "updated"])
def test_three_finite_crlf_files_do_not_authorize_general_lf_normalization(tmp_path, name, inventory):
    hashes = prepared(tmp_path, [name])
    record = next(row for row in proposal()["files"] if row["path"] == name)
    pin = record["lines"][0]
    target = tmp_path/name
    target.write_bytes(target.read_bytes().replace(b"\r\n", b"\n"))
    if inventory == "updated":
        hashes[name] = sha(target.read_bytes())
    finding = {"StartLine": pin["number"], "EndLine": pin["number"], "RuleID": pin["rules"][0]}
    assert review.load_reviewed_locations(tmp_path, hashes, "8.30.1").classify(finding, name) is None


@pytest.mark.parametrize("fault", ["changed-byte", "trailing-data", "repacked", "different-member"])
def test_v5_container_pin_rejects_even_structurally_valid_unreviewed_registries(tmp_path, fault):
    hashes = prepared(tmp_path, [])
    target = tmp_path/review._REVIEW_DATA_PATH
    raw = target.read_bytes()
    if fault == "changed-byte":
        raw = bytes([raw[0]^1])+raw[1:]
    elif fault == "trailing-data":
        raw += b"unreviewed registry bytes"
    else:
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as old:
            member = old.read("reviewed-locations.json")
        with zipfile.ZipFile(output,"w") as new:
            new.writestr("reviewed-locations.json" if fault == "repacked" else "other.json", member)
        raw = output.getvalue()
    assert sha(raw) != review._REVIEW_DATA_DIGEST
    target.write_bytes(raw)
    with pytest.raises(RuntimeError, match="output withheld"):
        review.load_reviewed_locations(tmp_path, hashes, "8.30.1")
