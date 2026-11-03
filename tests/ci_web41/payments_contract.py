"""A separate finite payments41 PostgreSQL budget, with source/profile/Root ACK."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

from tests.ci_web41 import pg_contract as current

ROOT = current.ROOT
SCOPE = "payments41-pg-twelve-criteria-one-uuid-two-backends-v2"
MODULE = "tests/integration_payment41_qa_postgres.py"
CURRENT_CASES = (
    "test_partial_full_replay_and_other_tenant_quota",
    "test_old_partial_and_full_keep_new_paid_renewal",
    "test_partial_never_extends_same_paid_invoice_or_resets_usage",
    "test_concurrent_signed_refund_has_two_backends_and_one_cumulative_fact",
    "test_actual_personal_team_history_is_own_and_rls_protected",
)
PEER_CASES = (
    "test_pg_invoice_signed_retry_replay_preserves_other_tenant_and_quota[surface0]",
    "test_pg_invoice_signed_retry_replay_preserves_other_tenant_and_quota[surface1]",
    "test_pg_invoice_signed_retry_replay_preserves_other_tenant_and_quota[surface2]",
    "test_pg_concurrent_same_invoice_has_one_ledger_and_retryable_inbox_collision",
    "test_pg_refund_updates_only_its_ledger_and_preserves_other_tenant_quota[surface0]",
    "test_pg_refund_updates_only_its_ledger_and_preserves_other_tenant_quota[surface1]",
    "test_pg_refund_updates_only_its_ledger_and_preserves_other_tenant_quota[surface2]",
)
CASES = (*CURRENT_CASES, *PEER_CASES)
PLAN = {"cases": 12, "UUIDs": 1, "concurrent_UUIDs": 1, "application_pool": 2,
        "application_workers": 2, "max_overflow": 0, "database_admin_pool": 1,
        "control_observer_connections": 1, "historical_core_restore_budgets_unchanged": True}
BOUND = (MODULE, "tests/ci_web41/payments_contract.py", "tests/ci_web41/payments_fixtures.py",
         "tests/ci_web41/run_payments.py", "tests/test_payment41_qa_peer.py",
         "tests/test_stripe_invoice_authority_peer.py", "tests/test_stripe_refund_ledger_peer.py",
         "tests/test_stripe_postgres_authority_peer.py", "tests/test_stripe_postgres_refund_peer.py",
         "tests/test_current41_pg_peer_routing.py", "tests/test_current41_payments_contract.py")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_contract(profile, generation):
    from tests.billing13_legacy_apply37_pg_contract import generation as observed_generation, private_workspace, pg_binary_directory
    from tests.ci_web37.pg_lease import profile as read_profile
    from web.services.legacy_object_apply_boundary import verify
    from web.database.schema_control import expected_head
    if expected_head() != "20261102_payment_refund_facts":
        raise ValueError("The separate payments gate requires genuine41")
    paths = [Path(path).resolve(strict=True) for path in (profile, generation)]
    for path in paths:
        if not path.is_relative_to(private_workspace()):
            raise ValueError("Payments41 authorities must remain private")
        verify(path)
    config = read_profile(paths[0])
    pg_binary_directory(config)
    files = current.source_files({"module": MODULE})
    for name in BOUND:
        raw = (ROOT / name).read_bytes()
        files[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    return {"schema": SCOPE, "revision": "20261102_payment_refund_facts", "plan": PLAN,
            "cases": list(CASES), "module": MODULE, "files": files, "FileSetDigest": digest(files),
            "profile_path": str(paths[0]), "profile_sha256": hashlib.sha256(paths[0].read_bytes()).hexdigest(),
            "generation_path": str(paths[1]), "generation_sha256": hashlib.sha256(paths[1].read_bytes()).hexdigest(),
            "generation": observed_generation(paths[1]), "server_port": 55483,
            "closure": "one_owned_UUID_OID_bound_normal_DROP_zero_sessions_and_fresh_absence"}


def require_ack(path, value):
    from tests.billing13_legacy_apply37_pg_contract import private_workspace
    from web.services.legacy_object_apply_boundary import verify
    path = Path(path)
    if not path.is_absolute() or not path.resolve(strict=True).is_relative_to(private_workspace()):
        raise ValueError("A private source/profile/generation-bound Root payments41 ACK is required")
    verify(path)
    raw = path.read_bytes()
    data = json.loads(raw)
    if (set(data) != {"approved", "scope", "contract_sha256", "expires_at_UTC"}
            or data["approved"] is not True or data["scope"] != SCOPE
            or value.get("schema") != SCOPE or data["contract_sha256"] != digest(value)):
        raise ValueError("Payments41 Root ACK differs")
    expiry = datetime.fromisoformat(data["expires_at_UTC"])
    if expiry.tzinfo is None or not 0 < (expiry - datetime.now(UTC)).total_seconds() <= 8 * 3600:
        raise ValueError("Payments41 Root ACK expired or exceeds eight hours")
    return hashlib.sha256(raw).hexdigest()


def authorize_ci(profile, generation, target):
    """The reviewed ephemeral Actions bootstrap owns this finite CI authority."""
    import os
    from datetime import timedelta
    from tests.ci_web41.ci_cluster import require_ci
    from tests.ci_web41.pg_control import check_control_generation
    from tests.ci_web37.pg_lease import profile as read_profile
    from tests.ci_web38.prepare_collection import source_photo
    root, temporary, _ = require_ci()
    if source_photo()["HEAD"] != os.environ["GITHUB_SHA"]:
        raise ValueError("Only the exact reviewed CI commit may authorize payments41")
    if root != ROOT or Path(target).parent != temporary / "ci37-pg-cluster-private":
        raise ValueError("Only the already-owned ephemeral CI namespace may hold this ACK")
    value = build_contract(profile, generation)
    check_control_generation(value, read_profile(profile))
    from web.services.legacy_object_apply_boundary import verify
    verify(Path(target).parent, directory=True)
    # Each Actions step has its own umask. Create the authorization private
    # from its first byte, without relying on the earlier cluster shell.
    def private_opener(name, flags):
        return os.open(name, flags, 0o600)
    with open(target, "x", encoding="utf8", opener=private_opener) as output:
        verify(Path(target))
        json.dump({"approved": True, "scope": SCOPE, "contract_sha256": digest(value),
                   "expires_at_UTC": (datetime.now(UTC) + timedelta(hours=4)).isoformat()}, output, indent=2)
        output.write("\n")
