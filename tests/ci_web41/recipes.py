"""Current41 fixture admission; preserve every historical exclusion verbatim."""
from tests.ci_web39 import recipes as original


def _current41(selectors):
    changes = {"tests.ci_web39.composition": "tests.ci_web41.composition",
               "--web39-current-fixtures": "--web41-current-fixtures"}
    return tuple(changes.get(value, value) for value in selectors)


WEB_SELECTORS = original.WEB_SELECTORS
CURRENT_RUNTIME_SELECTORS = _current41(original.CURRENT_RUNTIME_SELECTORS)
SMOKE_SELECTORS = _current41(original.SMOKE_SELECTORS)
CONTROL_SELECTORS = _current41(original.CONTROL_SELECTORS)
SHUFFLE_SEED = original.SHUFFLE_SEED
require_native_expiry_replacement = original.require_native_expiry_replacement
require_scanner_safety_companion = original.require_scanner_safety_companion
require_parent_companions = original.require_parent_companions
