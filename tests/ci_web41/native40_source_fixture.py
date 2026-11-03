"""Authenticate current19, then recover only the original production40 inputs.

The thirteenth parent web lock is verified before selecting the declared twelve
historical inputs. No APT-stage inverse, source rewrite or runtime acceptance is
performed. Current19 runtime/scanner gates remain separate obligations.
"""
from __future__ import annotations

from tests.ci_image57 import authority, context, production_child, technical_child


def production40_inputs(root):
    """Return exact historical production inputs after the complete current guard."""
    actual = technical_child.read_payloads(root)
    if type(actual) is not dict or len(actual) != 19 or set(actual) != set(technical_child.PINS):
        raise ValueError("The complete nineteen current source inputs are required")
    restored = technical_child.inverse(actual)
    manifest = context.json_object(authority.raw("container-inputs.json.RAW"))["candidate_files"]
    expected = {**technical_child.PARENT_PINS,
                "requirements_web.lock": technical_child.LOCK_INVERSES["requirements_web.lock"]["parent_pin"]}
    if set(manifest) != set(technical_child.PARENT_PINS) or len(manifest) != 12 or set(restored) != set(expected):
        raise ValueError("The exact twelve-plus-web historical source inventory differs")
    if any(technical_child.record(restored[name]) != pin for name, pin in expected.items()):
        raise ValueError("A restored historical input, including the web lock, differs")
    selected = {name: restored[name] for name in manifest}
    parent, transition = context.native_parent_payloads(selected)
    if transition != production_child.transition(context.native_transition()):
        raise ValueError("The historical production40 transition differs")
    if (any(set(pin) != {"bytes", "raw_sha256"} for pin in manifest.values())
            or any({key: technical_child.record(parent[name])[key] for key in pin} != pin
                   for name, pin in manifest.items())):
        raise ValueError("The original native parent authority differs")
    return selected
