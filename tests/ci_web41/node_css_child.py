"""Finite contrast CSS child for the Node source guard, never for Node reads.

The parent manifest and all original programs remain unchanged. Only the local
comparison buffer is inverted after the complete current stylesheet passes.
"""
from __future__ import annotations

import hashlib
import stat
from pathlib import Path

CSS_PATH = "web/static/css/workspace.css"
CURRENT_BYTES = 14161
CURRENT_SHA256 = "01e4a3a6f3cdf4f2a906cf82cfe874990f35995df7681f4d00452333b57c22b3"
PARENT_BYTES = 14075
PARENT_SHA256 = "9c79f2245ec6d73d77ede10c2fe116dd49a5499e1074316d850c498131323509"
PARENT_GUARD_SHA256 = "93d66ed5576c2ce407c71ef6cc24ea0e380c662ecaca90809b5cb22b62fbfc9e"
PARENT_BINDING_SHA256 = "c16b4091445f755c44a02c1a65a94116340112a682fea2391b2e154620173eac"
SOURCE_SCOPE = "current41-contrast-CSS-child-original-Node-programs-and-obligations"
SELECTORS = (b".mb-standalone .team-muted", b".mb-standalone .invite-details dt")
DECLARATION = b"color:var(--mb-muted);"
RULE = b".mb-standalone .team-muted,.mb-standalone .invite-details dt {color:var(--mb-muted);}\n"

# Each exact direct source adaptation has a single inverse. Everything else in
# the guard, all51 commands, and all865 normative labels are preserved wholesale.
GUARD_EDITS = (
    ("from tests.ci_web37.node_current import validate, validate_additional\n",
     "from tests.ci_web37.node_current import validate, validate_additional\nfrom tests.ci_web41 import node_css_child\n"),
    ("def require_sources(root: Path = ROOT):\n",
     "def require_sources(root: Path = ROOT):\n    node_css_child.require_guard_source(Path(__file__))\n"),
    ('        if len(source) != pin["bytes"] or digest(source) != pin["sha256"]:\n',
     '        if name == node_css_child.CSS_PATH:\n            source = node_css_child.parent_buffer(source)\n        if len(source) != pin["bytes"] or digest(source) != pin["sha256"]:\n'),
    ('            "source_scope": SOURCE_SCOPE, "direct_transitive_bound_sources": len(bindings["input_files"]),\n',
     '            "source_scope": node_css_child.SOURCE_SCOPE, "parent_source_scope": SOURCE_SCOPE,\n            "css_source_child": node_css_child.source_receipt((ROOT / node_css_child.CSS_PATH).read_bytes()),\n            "direct_transitive_bound_sources": len(bindings["input_files"]),\n'),
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(raw: bytes) -> bytes:
    if type(raw) is not bytes:
        raise ValueError("The CSS child requires exact source bytes")
    lf = raw.replace(b"\r\n", b"\n")
    if raw not in (lf, lf.replace(b"\n", b"\r\n")) or b"\r" in lf or lf.startswith(b"\xef\xbb\xbf"):
        raise ValueError("The CSS child requires uniform LF/CRLF without BOM")
    return lf


def parent_buffer(raw: bytes) -> bytes:
    """Validate the actual child, then invert only this in-memory guard value."""
    source = canonical(raw)
    if len(source) != CURRENT_BYTES or digest(source) != CURRENT_SHA256:
        raise ValueError("The complete current contrast stylesheet differs")
    if source.count(RULE) != 1:
        raise ValueError("Exactly one reviewed contrast rule is required")
    selectors, declarations = RULE.rstrip(b"\n").split(b" {", 1)
    if tuple(selectors.split(b",")) != SELECTORS or declarations != DECLARATION + b"}":
        raise ValueError("The exact two contrast selectors and declaration differ")
    parent = source.replace(RULE, b"", 1)
    if len(parent) != PARENT_BYTES or digest(parent) != PARENT_SHA256:
        raise ValueError("The exact contrast inverse does not recover the parent")
    return parent


def parent_guard_source(raw: bytes) -> bytes:
    source = canonical(raw).decode("utf8")
    for before, after in reversed(GUARD_EDITS):
        if source.count(after) != 1:
            raise ValueError("A finite Node CSS guard adaptation differs")
        source = source.replace(after, before, 1)
    parent = source.encode("utf8")
    if digest(parent) != PARENT_GUARD_SHA256:
        raise ValueError("The whole original Node source guard differs")
    return parent


def require_guard_source(path: Path) -> None:
    info = path.lstat()
    if (path.name != "node_contracts.py" or not stat.S_ISREG(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & 1024 or info.st_nlink != 1
            or path.resolve(strict=True) != path.absolute() or info.st_size > 65536):
        raise ValueError("The Node CSS guard must be a bounded plain source file")
    with path.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("The Node CSS guard source grew beyond its bound")
    parent_guard_source(raw)


def source_receipt(raw: bytes) -> dict:
    """Recheck the executed stylesheet and name its real identity separately."""
    parent = parent_buffer(raw)
    return {
        "scope": SOURCE_SCOPE,
        "stylesheet": CSS_PATH,
        "executed_css_physical_sha256": digest(raw),
        "executed_css_canonical_lf_sha256": CURRENT_SHA256,
        "executed_css_canonical_lf_bytes": CURRENT_BYTES,
        "executed_css_frame": "CRLF" if b"\r\n" in raw else "LF",
        "parent_guard_buffer_sha256": digest(parent),
        "parent_guard_buffer_bytes": len(parent),
        "parent_binding_manifest_sha256": PARENT_BINDING_SHA256,
        "inverse": "Remove exactly one authenticated two-selector contrast rule from the guard buffer only",
        "inverse_removed_bytes": len(RULE),
        "selectors": [value.decode() for value in SELECTORS],
        "declaration": DECLARATION.decode(),
        "filesystem_source_rewritten": False,
        "Node_source_reads_redirected": False,
        "historical_RAW39_PASS_claim": False,
        "native_browser_acceptance": False,
    }
