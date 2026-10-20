"""Consume a separate, expiring approval for exactly22 source-bound findings."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "tests/ci_web37/bandit22-approval.json"
PROPOSAL = "tests/data/security_bandit22_contract_candidate.json"
MATCHER = "tests/security_bandit22_contract_peer.py"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def apply_registry(report, root, registry, *, context, bandit_version, today=None):
    """Fail closed until Root approves the candidate; prove no OS isolation."""
    root = Path(root).resolve()
    today = datetime.now(UTC).date() if today is None else today
    if type(today) is not date:
        raise ValueError("Approval evaluation requires an exact UTC date")
    issued = date.fromisoformat(registry["reviewed_on"])
    expires = date.fromisoformat(registry["expires_on"])
    if (type(registry.get("schema")) is not int or registry["schema"] != 1 or registry.get("approval") != "approved"
            or not issued <= today <= expires or expires - issued != timedelta(days=30)
            or registry.get("tool_version") != {"bandit": "1.9.4"} or bandit_version != "1.9.4"
            or registry.get("old_baseline_entries_reapproved") != 0):
        raise ValueError("Finite Bandit approval is pending, expired or has a different tool contract")
    reviewers = registry["reviewers"]
    if (len(reviewers) != 2 or reviewers[0] != {
            "role": "independent_security", "source_commit": "fc08d2f7fe876eb224938e108b2bdda2a0b9a57e",
            "decision": "finite_triage_22_only"}
            or reviewers[1] != {"role": "root", "decision": "approved_finite_22_context_only"}):
        raise ValueError("The independent and Root approval records differ")
    proposal_raw = (root / PROPOSAL).read_bytes()
    matcher_raw = (root / MATCHER).read_bytes()
    if (digest(proposal_raw) != registry["proposal_git_lf_sha256"]
            or digest(matcher_raw) != registry["matcher_git_lf_sha256"]):
        raise ValueError("The immutable proposal or independent matcher differs")
    matcher = {"__file__": str(root / MATCHER), "__name__": "ci_web37_bandit22_literal_matcher"}
    exec(compile(matcher_raw, str(root / MATCHER), "exec"), matcher)  # noqa: S102
    canonical, validate_candidate = matcher["canonical"], matcher["validate_candidate"]
    proposal = json.loads(proposal_raw)
    ids = [row["occurrence_id"] for row in proposal["occurrences"]]
    if (registry["occurrence_ids"] != ids or len(ids) != 22 or len(set(ids)) != 22
            or registry["context_required"] != proposal["context_required"]
            or context != registry["context_required"]):
        raise ValueError("The occurrence IDs or reviewed entry context differ")
    bindings = {**proposal["dependency_bindings"], **proposal["source_bindings"]}
    if (registry["binding_entry_counts"] != {"sources": 5, "dependencies": 13, "unique_paths": 17}
            or set(registry["bindings"]) != set(bindings)
            or registry["source_variants"] != ["captured_main_raw", "authenticated_git_lf"]):
        raise ValueError("The finite source binding inventory differs")
    variants = {"captured_main_raw": {}, "authenticated_git_lf": {}}
    for name, pin in registry["bindings"].items():
        if canonical(name) != name or pin["captured_main_raw_sha256"] != bindings[name]:
            raise ValueError("The source binding is not the independent captured source")
        target = root / name
        if target.is_symlink() or not target.resolve().is_relative_to(root):
            raise ValueError("The finite source binding escapes its root")
        raw = target.read_bytes()
        variants["captured_main_raw"][name] = pin["captured_main_raw_sha256"]
        variants["authenticated_git_lf"][name] = pin["git_lf_sha256"]
        if digest(raw) == pin["git_lf_sha256"]:
            oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                               usedforsecurity=False).hexdigest()
            if oid != pin["git_blob"] or len(raw) != pin["git_bytes"] or b"\r" in raw:
                raise ValueError("Authenticated Git LF source frame differs")
    observed = {name: digest((root / name).read_bytes()) for name in bindings}
    matching = [name for name, value in variants.items() if observed == value]
    if not matching:
        raise ValueError("Source is neither the exact captured RAW set nor the authenticated Git LF set")
    selected = variants[matching[0]]
    # This is a separate finite reviewed binding. The proposal on disk and all
    # rule/span/AST/fragment/caller identities stay unchanged.
    candidate = copy.deepcopy(proposal)
    for group in ("source_bindings", "dependency_bindings"):
        candidate[group] = {name: selected[name] for name in candidate[group]}
    for row in candidate["occurrences"]:
        row["source_raw_sha256"] = selected[row["path"]]
    result = validate_candidate(report, root, candidate, context=context)
    if result != {"reviewed_occurrences": 22, "approved": False, "exceptions_applied": 0,
                  "status": "source_match_proposal_only"}:
        raise ValueError("The independent matcher no longer has proposal-only semantics")
    return {"approved_occurrences": 22, "source_variant": matching[0],
            "historical_baseline_reapproved": 0, "OS_isolation_proven": False,
            "scope": "finite_static_SQL_and_verified_isolated_Docker_build_entry_only"}
