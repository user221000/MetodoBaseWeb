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

if __name__ == "__main__":
    raise SystemExit(main())
