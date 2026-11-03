"""Current41 fixture admission; preserve every historical exclusion verbatim."""
from tests.ci_web39 import recipes as original


def _current41(selectors):
    changes = {"tests.ci_web39.composition": "tests.ci_web41.composition",
               "--web39-current-fixtures": "--web41-current-fixtures"}
    return tuple(changes.get(value, value) for value in selectors)


WEB_SELECTORS = original.WEB_SELECTORS
# These seven original PostgreSQL criteria execute in the required payments41
# gate. Their SQLite parameterization is invalid and is never a substitute.
POSTGRES_REPLACEMENTS = {
    "tests/test_stripe_postgres_authority_peer.py": (
        "test_pg_invoice_signed_retry_replay_preserves_other_tenant_and_quota[surface0]",
        "test_pg_invoice_signed_retry_replay_preserves_other_tenant_and_quota[surface1]",
        "test_pg_invoice_signed_retry_replay_preserves_other_tenant_and_quota[surface2]",
        "test_pg_concurrent_same_invoice_has_one_ledger_and_retryable_inbox_collision",
    ),
    "tests/test_stripe_postgres_refund_peer.py": (
        "test_pg_refund_updates_only_its_ledger_and_preserves_other_tenant_quota[surface0]",
        "test_pg_refund_updates_only_its_ledger_and_preserves_other_tenant_quota[surface1]",
        "test_pg_refund_updates_only_its_ledger_and_preserves_other_tenant_quota[surface2]",
    ),
}
CURRENT_RUNTIME_SELECTORS = (*_current41(original.CURRENT_RUNTIME_SELECTORS),
                             *("--ignore=" + name for name in POSTGRES_REPLACEMENTS))
SMOKE_SELECTORS = _current41(original.SMOKE_SELECTORS)
CONTROL_SELECTORS = _current41(original.CONTROL_SELECTORS)
SHUFFLE_SEED = original.SHUFFLE_SEED
require_native_expiry_replacement = original.require_native_expiry_replacement
require_scanner_safety_companion = original.require_scanner_safety_companion


def require_postgres_replacements(identities):
    from tests.ci_web41 import payments_contract
    peers = tuple(case for cases in POSTGRES_REPLACEMENTS.values() for case in cases)
    if (payments_contract.SCOPE != "payments41-pg-twelve-criteria-one-uuid-two-backends-v2"
            or peers != payments_contract.PEER_CASES or len(set(peers)) != 7
            or len(payments_contract.CURRENT_CASES) != 5
            or payments_contract.CASES != (*payments_contract.CURRENT_CASES, *peers)
            or len(set(payments_contract.CASES)) != 12
            or payments_contract.PLAN["cases"] != 12
            or not set(POSTGRES_REPLACEMENTS) <= set(payments_contract.BOUND)):
        raise ValueError("The mandatory exact twelve-case PostgreSQL replacement differs")
    modules = {row[0] for row in identities}
    originals = {name.removesuffix('.py').replace('/', '.') for name in POSTGRES_REPLACEMENTS}
    if modules & originals or "tests.test_current41_pg_peer_routing" not in modules:
        raise ValueError("PostgreSQL criteria must use their separately required owned gate")


def require_parent_companions(identities, originals=None):
    result = original.require_parent_companions(identities, originals)
    if originals is None:
        require_postgres_replacements(identities)
    return result
