"""Finite current41 source companion; see source-companions.json."""
from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from tests.ci_web41.source_companion import populate as _populate
_populate(globals(), __file__)

from tests.ci_web41.node_contracts import (
    node_gate as node_gate,
    current_node_gate as current_node_gate,
    additional_node_gate as additional_node_gate,
    new_node_gate as new_node_gate,
    privacy_node_gate as privacy_node_gate,
)
from tests.ci_web41.web_failure_projection import project_files as _project_files

_original_observe_junit = globals()["observe_junit"]
_runner_root = globals()["ROOT"]


def observe_junit(path, expected):
    """Preserve every original outcome; diagnostics never accept or retry it."""
    result = _original_observe_junit(path, expected)
    if not result["identities_exact"] or any(result[key] for key in ("failed", "errors", "skipped")):
        try:
            result["failure_locations"] = _project_files(_runner_root, path, expected)
        except Exception:  # noqa: BLE001 -- fixed privacy-preserving diagnostic rejection
            result["failure_locations"] = {"diagnostic_available": False, "reason": "projection_rejected"}
    return result


if __name__ == "__main__":
    raise SystemExit(main())
