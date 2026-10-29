"""Current39 SQLite selectors; all original historical exclusions stay literal.

PG/history/Node source contracts are still the original separate gates. This file
only substitutes the explicit SQLite companion plugin and its opt-in flag.
"""
from tests.ci_web37 import recipes as historical
from tests.ci_web39.native_parent_inputs import MODULES, require_parent_companions as require_parent_companions


def _current39(selectors):
    substitutions={name.replace('.', '/')+'.py':pin['companion'].replace('.', '/')+'.py'
                   for name,pin in MODULES.items()}
    substitutions.update({"tests.ci_web37.composition": "tests.ci_web39.composition",
                          "--web37-current-fixtures": "--web39-current-fixtures"})
    return tuple(substitutions.get(item, item)
                 for item in selectors)


WEB_SELECTORS = historical.WEB_SELECTORS
CURRENT_RUNTIME_SELECTORS = (*_current39(historical.CURRENT_RUNTIME_SELECTORS),
    *("--ignore="+name.replace('.', '/')+'.py' for name in MODULES))
SMOKE_SELECTORS = _current39(historical.SMOKE_SELECTORS)
CONTROL_SELECTORS = _current39(historical.CONTROL_SELECTORS)
SHUFFLE_SEED = historical.SHUFFLE_SEED
require_native_expiry_replacement = historical.require_native_expiry_replacement
require_scanner_safety_companion = historical.require_scanner_safety_companion
