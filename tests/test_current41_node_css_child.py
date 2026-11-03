"""The contrast child changes only a verified Node guard comparison buffer."""
from pathlib import Path

import pytest

from tests.ci_web41 import node_css_child as child

ROOT = Path(__file__).resolve().parents[1]


def css():
    return child.canonical((ROOT / child.CSS_PATH).read_bytes())


@pytest.mark.parametrize("frame", ["LF", "CRLF"])
def test_actual_css_is_validated_and_only_returned_guard_buffer_is_inverted(frame):
    physical = (ROOT / child.CSS_PATH).read_bytes()
    source = css()
    if frame == "CRLF":
        source = source.replace(b"\n", b"\r\n")
    parent = child.parent_buffer(source)
    assert len(parent) == 14075
    assert child.digest(parent) == child.PARENT_SHA256
    assert parent == css().replace(child.RULE, b"", 1)
    assert len(child.RULE) == 86
    assert (ROOT / child.CSS_PATH).read_bytes() == physical


@pytest.mark.parametrize("change", [
    "prefix", "suffix", "delete-rule", "duplicate-rule", "first-selector", "second-selector",
    "variable", "color", "declaration", "neighbor", "position", "BOM", "mixed", "bare-CR",
])
def test_unknown_children_are_rejected_before_any_parent_comparison(change):
    original = css()
    mutations = {
        "prefix": b" " + original,
        "suffix": original + b" ",
        "delete-rule": original.replace(child.RULE, b"", 1),
        "duplicate-rule": original + child.RULE,
        "first-selector": original.replace(b".mb-standalone .team-muted,", b".mb-app .team-muted,", 1),
        "second-selector": original.replace(b".mb-standalone .invite-details dt", b".mb-standalone .invite-details dd", 1),
        "variable": original.replace(child.RULE, child.RULE.replace(b"--mb-muted", b"--mb-text"), 1),
        "color": original.replace(child.RULE, child.RULE.replace(b"var(--mb-muted)", b"#A39C93"), 1),
        "declaration": original.replace(child.RULE, child.RULE.replace(b";}", b";display:none;}"), 1),
        "neighbor": original.replace(child.RULE, b"/* unreviewed */\n" + child.RULE, 1),
        "position": original.replace(child.RULE, b"", 1) + child.RULE,
        "BOM": b"\xef\xbb\xbf" + original,
        "mixed": original.replace(b"\n", b"\r\n", 1),
        "bare-CR": original.replace(b"\n", b"\r", 1),
    }
    changed = mutations[change]
    assert changed != original
    with pytest.raises(ValueError):
        child.parent_buffer(changed)


@pytest.mark.parametrize("value", [None, True, "css", bytearray(b"css")])
def test_only_exact_source_bytes_are_admitted(value):
    with pytest.raises(ValueError, match="exact source bytes"):
        child.parent_buffer(value)


@pytest.mark.parametrize("field", ["SELECTORS", "DECLARATION", "PARENT_SHA256", "PARENT_BYTES"])
def test_actual_child_cannot_validate_changed_semantic_or_parent_declarations(monkeypatch, field):
    value = {"SELECTORS": (b".mb-app .team-muted", child.SELECTORS[1]),
             "DECLARATION": b"color:red;", "PARENT_SHA256": "0" * 64,
             "PARENT_BYTES": child.PARENT_BYTES + 1}[field]
    monkeypatch.setattr(child, field, value)
    with pytest.raises(ValueError):
        child.parent_buffer(css())


@pytest.mark.parametrize("frame", ["LF", "CRLF"])
def test_entire_guard_has_exact_parent_inverse_with_no_other_changes(tmp_path, frame):
    source = child.canonical((ROOT / "tests/ci_web41/node_contracts.py").read_bytes())
    if frame == "CRLF":
        source = source.replace(b"\n", b"\r\n")
    parent = child.parent_guard_source(source)
    assert child.digest(parent) == child.PARENT_GUARD_SHA256
    restored = parent.decode()
    for before, after in child.GUARD_EDITS:
        assert restored.count(before) == 1
        restored = restored.replace(before, after, 1)
    assert restored.encode() == child.canonical(source)
    target = tmp_path / "node_contracts.py"
    target.write_bytes(source)
    child.require_guard_source(target)


@pytest.mark.parametrize(("before", "after"), [
    ("    node_css_child.require_guard_source(Path(__file__))\n", ""),
    ("source = node_css_child.parent_buffer(source)", "source = source"),
    ('len(source) != pin["bytes"]', 'len(source) == pin["bytes"]'),
    ('"legacy51": 865', '"legacy51": 864'),
    ("len(commands) != 51", "len(commands) != 50"),
    (child.PARENT_BINDING_SHA256, "0" * 64),
    ('"historical_RAW39_PASS_claim": False', '"historical_RAW39_PASS_claim": True'),
    ("require_sources()\n    write", "write"),
])
def test_guard_policy_inventory_pre_post_admission_and_honest_receipt_cannot_drift(before, after):
    source = child.canonical((ROOT / "tests/ci_web41/node_contracts.py").read_bytes()).decode()
    assert before in source
    changed = source.replace(before, after, 1)
    assert changed != source
    with pytest.raises(ValueError):
        child.parent_guard_source(changed.encode())


def test_guard_file_rejects_unbounded_source_and_wrong_name(tmp_path):
    wrong = tmp_path / "other.py"
    wrong.write_bytes((ROOT / "tests/ci_web41/node_contracts.py").read_bytes())
    with pytest.raises(ValueError, match="bounded plain"):
        child.require_guard_source(wrong)
    big = tmp_path / "node_contracts.py"
    big.write_bytes(b" " * 65537)
    with pytest.raises(ValueError, match="bounded plain"):
        child.require_guard_source(big)


@pytest.mark.parametrize("frame", ["LF", "CRLF"])
def test_receipt_keeps_executed_child_identity_separate_from_parent_guard(frame):
    source = css()
    if frame == "CRLF":
        source = source.replace(b"\n", b"\r\n")
    receipt = child.source_receipt(source)
    assert receipt["executed_css_physical_sha256"] == child.digest(source)
    assert receipt["executed_css_canonical_lf_sha256"] == child.CURRENT_SHA256
    assert receipt["parent_guard_buffer_sha256"] == child.PARENT_SHA256
    assert receipt["executed_css_canonical_lf_sha256"] != receipt["parent_guard_buffer_sha256"]
    assert receipt["executed_css_frame"] == frame
    assert receipt["parent_binding_manifest_sha256"] == child.PARENT_BINDING_SHA256
    assert receipt["scope"] == child.SOURCE_SCOPE
    for flag in ("filesystem_source_rewritten", "Node_source_reads_redirected",
                 "historical_RAW39_PASS_claim", "native_browser_acceptance"):
        assert receipt[flag] is False
