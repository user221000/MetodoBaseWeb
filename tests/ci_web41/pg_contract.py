"""Finite current41 source companion; see source-companions.json."""
from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from tests.ci_web41.source_companion import populate as _populate
_populate(globals(), __file__)

# The catalogue authenticates this predecessor at import; keep its actual
# bytes in the phase's before/after source set as well.
BOUND = (*BOUND,
    "tests/ci_web39/pg_contract.py",
    "tests/test_stripe_refund_ledger_author.py",
    "tests/current41_stripe_refund_ledger_author.py",
    "tests/test_stripe_refund_ledger_peer.py",
    "tests/current41_stripe_refund_ledger_peer.py",
    "tests/test_stripe_webhook_version_contract.py",
    "tests/current41_stripe_webhook_version_contract.py",
)
