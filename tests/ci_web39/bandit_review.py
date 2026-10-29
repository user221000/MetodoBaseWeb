"""Source-bound technical review for exactly26 current39 Bandit occurrences.

No application imports, risk acceptance, historical registry edits or scanner
suppression. A separate explicit Root approval is required by apply_review.
"""
from __future__ import annotations

import ast
import copy
from collections import Counter
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys

CONTEXT = "current39-child2-signed-APT-exact-OS-CA-and-static-SQL-only"
POLICY_MODULES = frozenset({"web.database.followup_policy", "web.database.notification_policy",
                            "web.database.product_analytics_policy_v2"})
CALLER_DIRS = ("api", "core", "web", "src", "utils", "config", "runtime-source", "scripts")
CALLER_ROOTS = ("api_server.py", "db_bootstrap.py")
VARIANTS = ("captured_main_raw", "authenticated_git_objects")
MAX_BYTES = 4 * 1024**2


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def ast_text(node):
    """Preserve the312 dump; fill only311's absent empty PEP695 field."""
    clone = copy.deepcopy(node)
    legacy = {
        ast.FunctionDef: ("name", "args", "body", "decorator_list", "returns", "type_comment"),
        ast.AsyncFunctionDef: ("name", "args", "body", "decorator_list", "returns", "type_comment"),
        ast.ClassDef: ("name", "bases", "keywords", "body", "decorator_list"),
    }
    for item in ast.walk(clone):
        fields = legacy.get(type(item))
        if fields is None:
            continue
        actual = tuple(item._fields)
        require(actual in (fields, (*fields, "type_params")), "Reviewed AST definition fields differ")
        if actual == fields:
            require(not hasattr(item, "type_params"), "Unexpected AST generic field outside its fieldset")
            item._fields = (*fields, "type_params")
            item.type_params = []
        else:
            require(type(getattr(item, "type_params", None)) is list and not item.type_params,
                    "Generic type parameters are outside this finite AST review")
    return ast.dump(clone, include_attributes=False)


AST311_FOLLOWUP_FRAMES = (('c9cec515ec38b6325443f85a0059329a06f70aa92117a6a44fc75795360e5a59', 13923), ('a26dc56d4d0f4a421cc479ec4f01b511b2117d71048b96eb5cfc184a2ed81a64', 13739))
AST311_FOLLOWUP_ANCHORS = ({'function': '_source', 'ast_sha256': 'bfe1ba3c677ba1be4f471dca16d188b6eff486f7988b911a651d89c53fee286d', 'fragment_sha256': '81e35e3a2359ef72f83788ea56311c7f1f5cf0196359b6206fdff1349801736a', 'function_ast_sha256': 'b485d6b20dd4c293733665ee71c9ff418e4eeea539d75a6fc2bee93024e960fc', 'native311_span': [31, 11, 36, 97], 'reviewed312_span': [31, 15, 32, 74]}, {'function': '_transition', 'ast_sha256': '864f464d7cf72aef1fc9738c5e3a4e7c44d523f7a1828c9224ad18ff413a905d', 'fragment_sha256': '3d2b3b3c29d7564d27b0c5a0f288d6da9c63ab672a5f067958193fd44a891b19', 'function_ast_sha256': '74fb91b09861723a0247e900b3f32e85aeddd0b5c19910e8b3a3dfcd424a57b5', 'native311_span': [66, 11, 74, 145], 'reviewed312_span': [66, 15, 70, 108]}, {'function': '_sqlite', 'ast_sha256': 'b0f44c76438cdb270fb12ee927df97e6b4ab6b3a5ee069f84584022999f11a49', 'fragment_sha256': '6937c235f86f5cab6f34e65dbe74af7b9406c2d3f632bf2b6a32b7be66ece0cb', 'function_ast_sha256': '11231c51fe6e6737854b9d8fb7e883ec252f3c263ab7f249918de3b7f189b594', 'native311_span': [91, 22, 101, 14], 'reviewed312_span': [91, 26, 92, 30]}, {'function': '_postgres', 'ast_sha256': 'd674e2543ef1052ee5a471f1287040345a70232c322cdace081edcbddec93662', 'fragment_sha256': '55756a913af738ea34be04c2237fcc7cd139cf7ce2aaff27f77f7c70270b43c9', 'function_ast_sha256': 'eb0cf89a81ac7beb3313d8633612cd83a0c7cbe4eb36b70efe9e283d6d8452d0', 'native311_span': [119, 22, 143, 17], 'reviewed312_span': [119, 26, 125, 18]})


def ast_parse(source, *args, **kwargs):
    """Project four reviewed311 f-string coordinates in a private AST copy.

    No source, finding descriptor, proposal anchor or global AST is rewritten.
    Every other source and the native312 parser retain their ordinary result.
    """
    native = ast.parse(source, *args, **kwargs)
    if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 11) or type(source) is not bytes:
        return native
    if (digest(source), len(source)) not in AST311_FOLLOWUP_FRAMES:
        return native
    tree = native
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    targets = []
    for anchor in AST311_FOLLOWUP_ANCHORS:
        matches = []
        for node in ast.walk(tree):
            if type(node) is not ast.Constant or type(node.value) is not str:
                continue
            span = [getattr(node, key, None) for key in ("lineno", "col_offset", "end_lineno", "end_col_offset")]
            if span != anchor["native311_span"]:
                continue
            if digest(ast_text(node).encode()) != anchor["ast_sha256"] or digest(node.value.encode()) != anchor["fragment_sha256"]:
                continue
            joined = parents.get(node)
            if type(joined) is not ast.JoinedStr or [getattr(joined, key, None) for key in (
                    "lineno", "col_offset", "end_lineno", "end_col_offset")] != anchor["native311_span"]:
                continue
            function = node
            while function is not None and type(function) not in (ast.FunctionDef, ast.AsyncFunctionDef):
                function = parents.get(function)
            if (function is not None and function.name == anchor["function"]
                    and digest(ast_text(function).encode()) == anchor["function_ast_sha256"]):
                matches.append(node)
        require(len(matches) == 1, "The exact reviewed311 f-string coordinate anchor differs")
        node = matches[0]
        start, first, end, last = anchor["reviewed312_span"]
        # Only the already authenticated RAW/Git frames reach this branch.
        # Columns count UTF8 bytes; normalize physical CRLF exactly as Python's
        # tokenizer does, without changing the source file or its authority.
        lines = source.replace(b"\r\n", b"\n").split(b"\n")
        require(all(type(value) is int for value in (start, first, end, last))
                and 1 <= start <= end <= len(lines)
                and 0 <= first <= len(lines[start - 1]) and 0 <= last <= len(lines[end - 1])
                and (start != end or first <= last), "Reviewed312 UTF8 slice coordinates differ")
        pieces = lines[start - 1:end]
        literal = (pieces[0][first:last] if start == end else
                   b"\n".join([pieces[0][first:], *pieces[1:-1], pieces[-1][:last]]))
        require(literal.decode("utf8") == node.value,
                "Reviewed312 UTF8 literal slice differs from the native Constant value")
        targets.append((node, anchor["reviewed312_span"]))
    require(len(targets) == 4 and len({id(node) for node, _span in targets}) == 4,
            "All four distinct311 coordinate projections are required")
    # All source, node, parent, function and literal-span checks finish on
    # the native tree before a copy is made; the native AST stays untouched.
    tree = copy.deepcopy(native)
    originals, copies = list(ast.walk(native)), list(ast.walk(tree))
    require(len(originals) == len(copies) and all(type(a) is type(b) for a, b in zip(originals, copies)),
            "Private AST copy differs")
    mapping = {id(a): b for a, b in zip(originals, copies)}
    for node, span in targets:
        copied = mapping[id(node)]
        for key, value in zip(("lineno", "col_offset", "end_lineno", "end_col_offset"), span):
            setattr(copied, key, value)
    return tree


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def canonical(name):
    require(type(name) is str, "Bandit path must be text")
    name = name.replace("\\", "/").removeprefix("./")
    path = PurePosixPath(name)
    require(name and name == path.as_posix() and not path.is_absolute() and ":" not in name
            and all(part not in {"", ".", ".."} for part in name.split("/"))
            and all(ord(c) >= 32 and ord(c) != 127 for c in name), "Bandit path is not canonical")
    return name


def read_source(root, name):
    require(canonical(name) == name, "Stored source binding is not canonical")
    path = root / name
    require(path.resolve(strict=True).is_relative_to(root), "Source escapes its reviewed root")
    for item in (path, *path.parents):
        info = item.lstat()
        require(not item.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400,
                "Source binding alias rejected")
        if item == root:
            break
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= MAX_BYTES,
            "Bounded regular source required")
    raw = path.read_bytes()
    after = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_nlink)
    require(identity(before) == identity(after) and len(raw) == before.st_size, "Reviewed source changed during read")
    return raw


def caller_paths(root):
    paths = set(CALLER_ROOTS)
    for directory in CALLER_DIRS:
        paths.update(path.relative_to(root).as_posix() for path in (root / directory).rglob("*.py"))
    return sorted(paths)


def caller_inventory(root, payloads=None):
    rows = []
    for name in caller_paths(root):
        raw = payloads[name] if payloads is not None else read_source(root, name)
        for node in ast.walk(ast_parse(raw, filename=name)):
            selected = False
            if isinstance(node, ast.ImportFrom):
                selected = (node.module in POLICY_MODULES or node.module == "web.database" and any(
                    alias.name in {item.rsplit(".", 1)[1] for item in POLICY_MODULES} for alias in node.names))
            elif isinstance(node, ast.Import):
                selected = any(alias.name in POLICY_MODULES for alias in node.names)
            elif isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
                selected = type(node.args[0].value) is str and node.args[0].value in POLICY_MODULES
            if selected:
                rows.append({"path": name, "line": node.lineno, "ast": ast_text(node)})
    return sorted(rows, key=lambda row: (row["path"], row["line"], row["ast"]))


def fingerprint(finding):
    require(type(finding.get("code")) is str, "Bandit source excerpt required")
    code = "\n".join(re.sub(r"^\d+\s", "", line).strip() for line in finding["code"].splitlines()).strip()
    return canonical(finding["filename"]) + ":" + finding["test_id"] + ":" + digest(code.encode())


def descriptor(finding):
    require(type(finding) is dict, "Typed finding required")
    values = [finding.get(key) for key in ("line_number", "col_offset", "end_col_offset")]
    lines = finding.get("line_range")
    require(all(type(v) is int and v >= 0 for v in values)
            and type(lines) is list and lines and all(type(v) is int and v > 0 for v in lines)
            and type(finding.get("test_id")) is str and type(finding.get("test_name")) is str,
            "Exact typed Bandit span required")
    return (canonical(finding["filename"]), finding["test_id"], finding["test_name"], *values, tuple(lines),
            finding.get("issue_severity"), finding.get("issue_confidence"), fingerprint(finding))


def expected_descriptor(row):
    return (row["path"], row["rule"], row["test_name"], row["line"], row["column"], row["end_column"],
            tuple(row["bandit_line_range"]), row["severity"], row["confidence"], row["fingerprint"])


def report_frame(report, rows):
    """Match one complete native312 or exact observed311 descriptor multiset.

    Both frames retain the existing26 findings and their original fingerprints;
    the scanner RAW is never rewritten or treated as an incomplete set.
    """
    observed = Counter(descriptor(item) for item in report["results"])
    reviewed = Counter(expected_descriptor(row) for row in rows)
    if observed == reviewed:
        return "reviewed312_exact_descriptors"
    require(sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 11), "The exact26 finding multiset differs")
    alternate, projected = [], 0
    for row in rows:
        current = list(expected_descriptor(row))
        matched = [anchor for anchor in AST311_FOLLOWUP_ANCHORS
                   if row["path"] == "web/database/followup_policy.py"
                   and row["function"] == anchor["function"]
                   and [row["line"], row["column"], row["end_line"], row["end_column"]] == anchor["reviewed312_span"]
                   and all(row[key] == anchor[key] for key in ("ast_sha256", "fragment_sha256", "function_ast_sha256"))]
        require(len(matched) <= 1, "Ambiguous311 descriptor anchor")
        if matched:
            current[4], current[5] = matched[0]["native311_span"][1], matched[0]["native311_span"][3]
            projected += 1
        alternate.append(tuple(current))
    require(projected == 4 and observed == Counter(alternate), "The exact26 finding multiset differs")
    return "observed311_exact_four_offset_alternative"


def validate_candidate(report, root, proposal, *, context, bandit_version):
    require(context == CONTEXT == proposal.get("context_required") and bandit_version == "1.9.4",
            "Current39 source context or Bandit version differs")
    require(proposal.get("schema") == "current39-bandit26-proposal-v1"
            and proposal.get("approval") == "proposal_only_no_exceptions_applied"
            and proposal.get("existing_baseline_entries_reapproved") == 0,
            "Current39 proposal-only review required")
    rows = proposal["occurrences"]
    require(type(rows) is list and len(rows) == 26 and len({row["occurrence_id"] for row in rows}) == 26,
            "All26 unique current occurrences required")
    require(Counter(row["classification"] for row in rows) == {
                "technical_static_SQL_false_positive": 24, "conditional_verified_Docker_build_only": 2},
            "The exact24 SQL and2 conditional native review scopes are required")
    require(type(report) is dict and report.get("errors") == [] and type(report.get("results")) is list,
            "A complete error-free Bandit report required")
    selected_report = report_frame(report, rows)
    root = Path(root).resolve(strict=True)
    paths = caller_paths(root)
    require(paths == proposal["caller_source_inventory"], "Reviewed caller source file inventory differs")
    bindings = proposal["bindings"]
    require(set(paths) <= set(bindings) and len(set(row["path"] for row in rows)) == 6
            and set(row["path"] for row in rows) == set(proposal["source_paths"])
            and set(proposal["dependency_paths"]) <= set(bindings)
            and set(proposal["source_paths"]) <= set(bindings), "Finite source/dependency inventory differs")
    payloads = {name: read_source(root, name) for name in bindings}
    observed = {name: digest(raw) for name, raw in payloads.items()}
    variants = [variant for variant in VARIANTS if all(
        observed[name] == pin[variant + "_sha256"] for name, pin in bindings.items())]
    require(variants, "Source is neither the entire reviewed RAW universe nor exact Git object universe")
    selected = variants[0]
    for name, raw in payloads.items():
        pin = bindings[name]
        expected_size = pin["captured_bytes"] if selected == VARIANTS[0] else pin["git_bytes"]
        require(len(raw) == expected_size, "Source frame length differs")
        if selected == VARIANTS[1]:
            oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False).hexdigest()
            require(oid == pin["git_blob"], "Authenticated Git object source differs")
    require(caller_inventory(root, payloads) == proposal["caller_inventory"], "Current policy caller closure differs")
    for row in rows:
        identity = {key: value for key, value in row.items() if key != "occurrence_id"}
        require(digest(encoded(identity)) == row["occurrence_id"], "Current occurrence identity differs")
        tree = ast_parse(payloads[row["path"]], filename=row["path"])
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        matches = []
        for node in ast.walk(tree):
            if (type(node).__name__ != row["ast_type"] or getattr(node, "lineno", None) != row["line"]
                    or getattr(node, "col_offset", None) != row["column"]
                    or getattr(node, "end_lineno", None) != row["end_line"]
                    or getattr(node, "end_col_offset", None) != row["end_column"]):
                continue
            if digest(ast_text(node).encode()) != row["ast_sha256"]:
                continue
            fragment = node.value if isinstance(node, ast.Constant) else ast.get_source_segment(
                payloads[row["path"]].decode("utf-8-sig"), node)
            if type(fragment) is not str or digest(fragment.encode()) != row["fragment_sha256"]:
                continue
            function = node
            while function is not None and not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function = parents.get(function)
            if function is not None and function.name == row["function"] and digest(
                    ast_text(function).encode()) == row["function_ast_sha256"]:
                matches.append(node)
        require(len(matches) == 1, "Current reviewed AST/dataflow anchor differs")
    # Re-read every binding after matching; the original source snapshot remains
    # authoritative even when a scanner or another process touched a file.
    require(all(read_source(root, name) == raw for name, raw in payloads.items()), "Current source changed during review")
    return {"reviewed_occurrences": 26, "approved": False, "exceptions_applied": 0,
            "status": "current39_source_match_proposal_only", "source_variant": selected,
            "report_variant": selected_report}


def apply_review(report, root, proposal, approval, *, context, bandit_version, today=None):
    today = datetime.now(UTC).date() if today is None else today
    require(type(today) is date, "Exact UTC approval evaluation date required")
    issued, expiry = date.fromisoformat(approval["reviewed_on"]), date.fromisoformat(approval["expires_on"])
    require(approval.get("schema") == 1 and type(approval.get("schema")) is int
            and approval.get("approval") == "approved" and issued <= today <= expiry
            and expiry - issued == timedelta(days=30) and approval.get("bandit_version") == bandit_version == "1.9.4"
            and approval.get("context_required") == context == CONTEXT
            and approval.get("historical_baseline_entries_reapproved") == 0,
            "Current26 Root approval is pending, expired or has a different contract")
    require(approval["reviewers"] == [{"role": "independent_security", "source_commit": proposal["review_source_commit"],
                                      "decision": "finite_current26_technical_triage"},
                                     {"role": "root", "decision": "approved_finite_current26_context_only"}],
            "Separate independent and explicit Root review required")
    require(approval["proposal_canonical_sha256"] == digest(encoded(proposal))
            and approval["matcher_sha256"] == digest(Path(__file__).read_bytes())
            and approval["occurrence_ids"] == [row["occurrence_id"] for row in proposal["occurrences"]],
            "Approved proposal, matcher or occurrence inventory differs")
    checked = validate_candidate(report, root, proposal, context=context, bandit_version=bandit_version)
    return {"approved_occurrences": 26, "source_variant": checked["source_variant"],
            "historical_baseline_reapproved": 0, "OS_isolation_proven": False,
            "report_variant": checked["report_variant"],
            "scope": "current26_static_SQL_and_verified_Docker_source_entry_only"}
