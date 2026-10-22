"""Observe fixture bodies and explicit targets without executing any fixture."""
from __future__ import annotations

import ast
import hashlib
import inspect
import textwrap


def fixture_contract(function):
    try:
        source = textwrap.dedent(inspect.getsource(function)).replace("\r\n", "\n")
    except (OSError, TypeError):
        return {"module": function.__module__, "function": function.__qualname__,
                "source_unavailable": True, "requires_review": True}
    tree = ast.parse(source)
    targets = []
    unresolved = False
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        if not isinstance(call.func, ast.Name) or call.func.id != "run_migration":
            continue
        values = []
        for node in call.args:
            value = node.value if isinstance(node, ast.Constant) else None
            if isinstance(node, ast.Name):
                candidate = function.__globals__.get(node.id)
                if isinstance(candidate, str) and candidate.startswith("2026"):
                    value = candidate
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.args and not node.keywords:
                from web.database import schema_control
                # Resolve only the approved pure product revision reader. An
                # arbitrary fixture/global callable is never invoked here.
                if function.__globals__.get(node.func.id) is schema_control.expected_head:
                    value = schema_control.expected_head()
            values.append(value)
        if "--revision" in values:
            index = values.index("--revision") + 1
            target = values[index] if index < len(values) else None
            if isinstance(target, str) and target.startswith("2026"):
                targets.append(target)
            else:
                unresolved = True
    return {"module": function.__module__, "function": function.__qualname__,
            "source_sha256_LF": hashlib.sha256(source.encode()).hexdigest(),
            "explicit_migration_targets": sorted(set(targets)),
            "unresolved_explicit_target": unresolved,
            "requires_review": unresolved or any(target != "20261020_account_security" for target in targets)}
