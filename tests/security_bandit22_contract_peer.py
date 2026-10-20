"""Finite review-candidate matching only: applies no Bandit/baseline exception."""
import ast
import hashlib
from collections import Counter
from pathlib import Path, PurePosixPath

POLICY_MODULES = {"web.database.followup_policy", "web.database.notification_policy"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(name):
    if not isinstance(name, str):
        raise TypeError("Finding path is not text")
    value = name.replace("\\", "/").removeprefix("./")
    if (not value or ":" in value or PurePosixPath(value).is_absolute()
            or any(part in {"", ".", ".."} for part in value.split("/"))
            or any(ord(char) < 32 for char in value)):
        raise ValueError("Finding path is not canonical")
    return value


def caller_inventory(root):
    rows = []
    for directory in ("web", "api", "core", "src", "utils", "config", "scripts", "runtime-source"):
        for file in sorted((root/directory).rglob("*.py")):
            for node in ast.walk(ast.parse(file.read_bytes())):
                selected = False
                if isinstance(node, ast.ImportFrom):
                    selected = (node.module in POLICY_MODULES or (node.module == "web.database" and any(
                        alias.name in {"followup_policy", "notification_policy"} for alias in node.names)))
                elif isinstance(node, ast.Import):
                    selected = any(alias.name in POLICY_MODULES for alias in node.names)
                elif isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
                    selected = isinstance(node.args[0].value, str) and node.args[0].value in POLICY_MODULES
                if selected:
                    rows.append({"path": file.relative_to(root).as_posix(), "line": node.lineno,
                                 "ast": ast.dump(node, include_attributes=False)})
    return sorted(rows, key=lambda row: (row["path"], row["line"], row["ast"]))


def descriptor(finding):
    values = [finding.get(key) for key in ("line_number", "col_offset", "end_col_offset")]
    lines = finding.get("line_range")
    if (any(type(value) is not int or value < 0 for value in values)
            or type(lines) is not list or not lines or any(type(value) is not int or value < 1 for value in lines)
            or not isinstance(finding.get("test_id"), str)):
        raise ValueError("Finding span is not exact typed metadata")
    return (canonical(finding.get("filename")), finding["test_id"], *values, tuple(lines))


def expected_descriptor(row):
    return (row["path"], row["rule"], row["line"], row["column"], row["end_column"], tuple(row["bandit_line_range"]))


def validate_candidate(report, root, proposal, *, context=None):
    """Verify explicit source-bound review matches; never authorize an ignore.

    The caller must independently establish build isolation before using the
    stated context. This function cannot prove an OS/container boundary.
    """
    root = Path(root).resolve()
    if context != proposal["context_required"]:
        raise ValueError("Native findings require the explicit reviewed build context")
    rows = proposal["occurrences"]
    if (proposal["approval"] != "proposal_only_no_baseline_change" or len(rows) != 22
            or len({row["occurrence_id"] for row in rows}) != 22
            or report.get("errors") != [] or type(report.get("results")) is not list):
        raise ValueError("Finite review inventory differs")
    current = Counter(descriptor(item) for item in report["results"])
    expected = Counter(expected_descriptor(row) for row in rows)
    if current != expected:
        raise ValueError("Finding multiset differs; no candidate applies")
    sources = {}
    for name, expected_hash in {**proposal["dependency_bindings"], **proposal["source_bindings"]}.items():
        if canonical(name) != name:
            raise ValueError("Source binding is not canonical")
        target = root/name
        if target.is_symlink() or not target.resolve().is_relative_to(root):
            raise ValueError("Source binding escapes its root")
        raw = target.read_bytes()
        if digest(raw) != expected_hash:
            raise ValueError("Exact source/dependency bytes differ")
        sources[name] = raw
    if caller_inventory(root) != proposal["caller_inventory"]:
        raise ValueError("Reviewed static caller inventory differs")
    for row in rows:
        tree = ast.parse(sources[row["path"]])
        parents = {}
        for parent in ast.walk(tree):
            parents.update((child, parent) for child in ast.iter_child_nodes(parent))
        matches = []
        for node in ast.walk(tree):
            if (type(node).__name__ != row["ast_type"] or getattr(node, "lineno", None) != row["line"]
                    or getattr(node, "col_offset", None) != row["column"]
                    or getattr(node, "end_lineno", None) != row["end_line"]
                    or getattr(node, "end_col_offset", None) != row["end_column"]):
                continue
            if digest(ast.dump(node, include_attributes=False).encode()) != row["ast_sha256"]:
                continue
            fragment = node.value if isinstance(node, ast.Constant) else ast.get_source_segment(sources[row["path"]].decode("utf8"), node)
            if not isinstance(fragment, str) or digest(fragment.encode()) != row["fragment_sha256"]:
                continue
            parent = node
            while parent is not None and not isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parent = parents.get(parent)
            if parent is not None and parent.name == row["function"] and digest(ast.dump(parent, include_attributes=False).encode()) == row["function_ast_sha256"]:
                matches.append(node)
        if len(matches) != 1:
            raise ValueError("Exact reviewed AST fragment differs")
    return {"reviewed_occurrences": 22, "approved": False, "exceptions_applied": 0,
            "status": "source_match_proposal_only"}
