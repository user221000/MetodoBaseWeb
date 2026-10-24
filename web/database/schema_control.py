"""Read-only schema signatures and startup gates; never repair schema at runtime."""
import json
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.schema_contract_v2 import schema_signatures_equal
from web.database.alembic.policy_contract_v2 import policy_signatures_equal

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_CONTRACTS = {
    "20261018_schema_reconciliation": "20261018_reconciled",
    "20261018_provider_subjects": "20261018_prepared",
    "20261018_tenant_isolation": "20261018_isolated",
    "20261018_gym_generation_quota": "20261018_gym_quota",
    "20261018_stored_objects": "20261018_stored_objects",
    "20261018_individual_publication": "20261018_individual_publication",
    "20261019_personal_diary": "20261019_personal_diary",
    "20261019_account_recovery": "20261019_account_recovery",
    "20261019_client_account_links": "20261019_client_account_links",
    "20261019_personal_history_index": "20261019_personal_history_index",
    "20261019_mfa": "20261019_mfa",
    "20261019_personal_progress": "20261019_personal_progress",
    "20261019_google_subjects": "20261019_google_subjects",
    "20261019_followup_tasks": "20261019_followup_tasks",
    "20261020_nutrition_profile": "20261020_nutrition_profile",
    "20261020_notifications": "20261020_notifications",
    "20261020_account_security": "20261020_account_security",
    "20261023_product_facts": "20261023_product_facts",
    "20261023_privacy_disposition": "20261023_privacy_disposition",
}


def alembic_config() -> Config:
    """Resolve migration paths independently of the process working directory."""
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "web" / "database" / "alembic"))
    return config


def expected_head() -> str:
    """Require one migration head, failing explicitly on an unresolved branch."""
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()
    if len(heads) != 1:
        raise RuntimeError("Migration history must have exactly one head")
    return heads[0]


def verify_legacy_signature(connection) -> None:
    """Accept only the exact frozen legacy schema before assigning its revision."""
    path = Path(__file__).parent / "schema_baselines" / ("20260402_orm_" + connection.dialect.name + ".json")
    if not path.is_file():
        raise RuntimeError("No reviewed legacy schema baseline for this dialect")
    expected = json.loads(path.read_text(encoding="utf-8"))
    if schema_signature(connection) != expected["signature"]:
        raise RuntimeError("Legacy schema differs from reviewed baseline; reconcile drift before adoption")


def verify_runtime_schema(engine, *, require_revision: bool = True, expected_revision: str | None = None) -> None:
    """Fail before traffic when migrations or required application columns are missing.

    Only isolated unit SQLite fixtures may opt out of revision bookkeeping. They
    still require all application columns. PostgreSQL always requires exact head.
    """
    from web.database.models import Base
    with engine.connect() as connection:
        inspector = inspect(connection)
        if require_revision or connection.dialect.name == "postgresql":
            actual = MigrationContext.configure(connection).get_current_heads()
            required = expected_revision or expected_head()
            if actual != (required,):
                raise RuntimeError("Database revision does not match application; run reviewed migrations")
            if required not in SCHEMA_CONTRACTS:
                raise RuntimeError("No frozen schema contract for the requested revision")
            target_path = Path(__file__).parent / "alembic" / "schema_targets" / (SCHEMA_CONTRACTS[required] + "_" + connection.dialect.name + ".json")
            contract = json.loads(target_path.read_text(encoding="utf-8"))
            if not schema_signatures_equal(schema_signature(connection), contract["signature"]):
                raise RuntimeError("Database structure differs from the reviewed application schema")
            if "tenant_security" in contract:
                from web.database.tenant_policy import tenant_security_signature
                if not policy_signatures_equal(tenant_security_signature(connection), contract["tenant_security"]):
                    raise RuntimeError("Database tenant policies differ from the reviewed application boundary")
            if "member_link_security" in contract:
                from web.database.alembic.member_link_security_v1 import member_link_security_signature
                if member_link_security_signature(connection) != contract["member_link_security"]:
                    raise RuntimeError("Database member link guards differ from the reviewed application boundary")
            if "history_order_index" in contract:
                from web.database.alembic.history_index_contract_v1 import history_index_signature
                if history_index_signature(connection) != contract["history_order_index"]:
                    raise RuntimeError("Database history ordering differs from the reviewed index")
            if "progress_security" in contract:
                from web.database.progress_policy import signature as progress_signature
                if progress_signature(connection) != contract["progress_security"]:
                    raise RuntimeError("Database progress authority differs from the reviewed contract")
            if "google_identity_security" in contract:
                from web.database.google_identity_policy import signature as google_signature
                if google_signature(connection) != contract["google_identity_security"]:
                    raise RuntimeError("Database Google authentication binding differs from the reviewed contract")
            if "followup_security" in contract:
                from web.database.followup_policy import signature as followup_signature
                if followup_signature(connection) != contract["followup_security"]:
                    raise RuntimeError("Database follow-up projection/history differs from the reviewed contract")
            if "notification_security" in contract:
                from web.database.notification_policy import signature as notification_signature
                if notification_signature(connection) != contract["notification_security"]:
                    raise RuntimeError("Database notification authority differs from the reviewed contract")
            if "product_analytics_security" in contract:
                from web.database.product_analytics_policy_v2 import signature as product_signature
                if not policy_signatures_equal(product_signature(connection), contract["product_analytics_security"]):
                    raise RuntimeError("Database product fact authority differs from the reviewed contract")
            if "privacy_security" in contract:
                from web.database.privacy_policy_v1 import signature as privacy_signature
                if privacy_signature(connection) != contract["privacy_security"]:
                    raise RuntimeError("Database privacy authority differs from the reviewed contract")
            if expected_revision is not None:
                # Explicit historical migration acceptance uses that revision's
                # frozen model, not the current application's newer metadata.
                return
        available = set(inspector.get_table_names())
        for table in Base.metadata.sorted_tables:
            if table.name not in available:
                raise RuntimeError("Database is missing an application table")
            actual_columns = {column["name"] for column in inspector.get_columns(table.name)}
            if not set(table.columns.keys()).issubset(actual_columns):
                raise RuntimeError("Database is missing application columns")
