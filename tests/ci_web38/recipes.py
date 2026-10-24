"""Current38 SQLite selectors; all original historical exclusions stay literal.

PG/history/Node source contracts are still the original separate gates. This file
only substitutes the explicit SQLite companion plugin and its opt-in flag.
"""
from tests.ci_web37 import recipes as historical


def _current38(selectors):
    return tuple({"tests.ci_web37.composition": "tests.ci_web38.composition",
                  "--web37-current-fixtures": "--web38-current-fixtures"}.get(item, item)
                 for item in selectors)


WEB_SELECTORS = historical.WEB_SELECTORS
CURRENT_RUNTIME_SELECTORS = _current38(historical.CURRENT_RUNTIME_SELECTORS)
SMOKE_SELECTORS = _current38(historical.SMOKE_SELECTORS)
CONTROL_SELECTORS = _current38(historical.CONTROL_SELECTORS)
SHUFFLE_SEED = historical.SHUFFLE_SEED
require_native_expiry_replacement = historical.require_native_expiry_replacement
require_scanner_safety_companion = historical.require_scanner_safety_companion
