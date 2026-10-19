"""Reconcile known legacy shapes and make onboarding templates idempotent.

The target is a frozen, reviewed structural contract, not the live ORM. Every
operation is Alembic DDL/data work; no create_all/stamp fallback is permitted.
Existing UUID configuration/license IDs survive in legacy_id. Unknown columns
or missing tables abort instead of being discarded. RLS activation is R04.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from alembic import op
import sqlalchemy as sa

from web.database.alembic.schema_contract_v1 import schema_signature

revision = "20261018_schema_reconciliation"
down_revision = "20261018_billing_integrity"
branch_labels = None
depends_on = None

_NAMING = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
           "uq": "uq_%(table_name)s_%(column_0_name)s"}
_DEFAULTS = (("1 Semana", 7, 150.0), ("1 Mes", 30, 500.0), ("3 Meses", 90, 1200.0),
             ("6 Meses", 180, 2000.0), ("1 Año", 365, 3500.0))
# PostgreSQL's reflected ANY/ARRAY casts are not stable when reused as DDL.
# Keep the original frozen constraint expressions for these two declarations.
_CHECK_DDL = {"ck_user_sub_plan": "plan IN ('starter', 'pro')",
              "ck_user_sub_status": "status IN ('active', 'canceled')"}
_ID_DEFAULTS = {"gym_settings": "nextval('gym_settings_id_seq'::regclass)",
                "gym_licenses": "nextval('gym_licenses_id_seq'::regclass)"}
_SEQUENCE_OWNERS = {"gym_settings": "ALTER SEQUENCE gym_settings_id_seq OWNED BY gym_settings.id",
                    "gym_licenses": "ALTER SEQUENCE gym_licenses_id_seq OWNED BY gym_licenses.id"}
_POLICY_DDL = {
    "clientes": "CREATE POLICY tenant_isolation_clientes ON clientes FOR ALL USING (gym_id = current_setting('app.current_tenant', TRUE)) WITH CHECK (gym_id = current_setting('app.current_tenant', TRUE))",
    "planes_generados": "CREATE POLICY tenant_isolation_planes ON planes_generados FOR ALL USING (gym_id = current_setting('app.current_tenant', TRUE)) WITH CHECK (gym_id = current_setting('app.current_tenant', TRUE))",
    "subscriptions": "CREATE POLICY tenant_isolation_subscriptions ON subscriptions FOR ALL USING (gym_id = current_setting('app.current_tenant', TRUE)) WITH CHECK (gym_id = current_setting('app.current_tenant', TRUE))",
    "payments": "CREATE POLICY tenant_isolation_payments ON payments FOR ALL USING (gym_id = current_setting('app.current_tenant', TRUE)) WITH CHECK (gym_id = current_setting('app.current_tenant', TRUE))",
}


def _type(label: str):
    """Parse the closed type vocabulary in this migration's frozen contracts."""
    if label.startswith("VARCHAR("):
        return sa.String(int(re.fullmatch(r"VARCHAR\((\d+)\)", label).group(1)))
    return {"INTEGER": sa.Integer, "FLOAT": sa.Float, "DOUBLE PRECISION": sa.Float,
            "TEXT": sa.Text, "BOOLEAN": sa.Boolean, "TIMESTAMP": sa.DateTime,
            "DATETIME": sa.DateTime, "JSON": sa.JSON}[label]()


@contextmanager
def _batch(table):
    with op.batch_alter_table(table, naming_convention=_NAMING) as batch:
        yield batch


def _integer_id(table: str) -> None:
    """Preserve historic UUID ids while adopting the integer ORM contract."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {item["name"]: item for item in inspector.get_columns(table)}
    if "legacy_id" not in columns:
        op.add_column(table, sa.Column("legacy_id", sa.String(36), nullable=True))
    if isinstance(columns["id"]["type"], sa.Integer):
        return
    for other in inspector.get_table_names():
        if any(fk["referred_table"] == table and "id" in fk["referred_columns"] for fk in inspector.get_foreign_keys(other)):
            raise RuntimeError("Historic identifier conversion requires review of incoming foreign keys")
    record = sa.table(table, sa.column("id"), sa.column("legacy_id"))
    conn.execute(record.update().values(legacy_id=sa.cast(record.c.id, sa.String(36))))
    ids = conn.execute(sa.select(record.c.id).order_by(record.c.id)).scalars().all()
    if conn.dialect.name == "sqlite":
        for number, old_id in enumerate(ids, 1):
            conn.execute(record.update().where(record.c.id == old_id).values(id=str(number)))
        with _batch(table) as batch:
            batch.alter_column("id", existing_type=columns["id"]["type"], type_=sa.Integer(), existing_nullable=False)
        return
    op.add_column(table, sa.Column("reconciled_id", sa.Integer(), nullable=True))
    revised = sa.table(table, sa.column("id"), sa.column("reconciled_id"))
    for number, old_id in enumerate(ids, 1):
        conn.execute(revised.update().where(revised.c.id == old_id).values(reconciled_id=number))
    op.drop_constraint(inspector.get_pk_constraint(table)["name"], table, type_="primary")
    op.drop_column(table, "id")
    op.alter_column(table, "reconciled_id", new_column_name="id", nullable=False)
    op.create_primary_key(table + "_pkey", table, ["id"])
    sequence_name = table + "_id_seq"
    sa.Sequence(sequence_name).create(conn, checkfirst=True)
    integer_record = sa.table(table, sa.column("id"))
    next_id = sa.select(sa.func.coalesce(sa.func.max(integer_record.c.id), 0) + 1).scalar_subquery()
    conn.execute(sa.select(sa.func.setval(sequence_name, next_id, False)))
    conn.execute(sa.text(_SEQUENCE_OWNERS[table]))
    op.alter_column(table, "id", server_default=sa.text(_ID_DEFAULTS[table]))


def _membership_data() -> None:
    """Backfill recognized templates; only remove exact duplicate copies."""
    conn = op.get_bind()
    catalog = sa.table("planes_suscripcion", sa.column("id"), sa.column("gym_id"), sa.column("nombre"),
                       sa.column("duracion_dias"), sa.column("precio"), sa.column("moneda"), sa.column("activo"),
                       sa.column("template_key"), sa.column("created_at"), sa.column("updated_at"))
    users = sa.table("usuarios", sa.column("id"), sa.column("tipo"), sa.column("team_gym_id"))
    gym_ids = conn.execute(sa.select(users.c.id).where(users.c.tipo == "gym", users.c.team_gym_id.is_(None))).scalars()
    for gym_id in gym_ids:
        rows = conn.execute(sa.select(catalog).where(catalog.c.gym_id == gym_id).order_by(catalog.c.id)).mappings().all()
        if not rows:
            now = datetime.now(timezone.utc)
            for name, duration, price in _DEFAULTS:
                conn.execute(catalog.insert().values(gym_id=gym_id, nombre=name, duracion_dias=duration,
                    precio=price, moneda="MXN", activo=True, template_key="duration_" + str(duration), created_at=now, updated_at=now))
            continue
        for name, duration, _ in _DEFAULTS:
            candidates = [row for row in rows if row["nombre"] == name and row["duracion_dias"] == duration]
            if not candidates:
                continue
            canonical = candidates[0]
            conn.execute(catalog.update().where(catalog.c.id == canonical["id"]).values(template_key="duration_" + str(duration)))
            for duplicate in candidates[1:]:
                if (duplicate["precio"], duplicate["moneda"], duplicate["activo"]) == (canonical["precio"], canonical["moneda"], canonical["activo"]):
                    conn.execute(catalog.delete().where(catalog.c.id == duplicate["id"]))


def _reconcile_columns(table, target) -> None:
    actual = {item["name"]: item for item in sa.inspect(op.get_bind()).get_columns(table)}
    expected = {item["name"]: item for item in target["columns"]}
    if set(actual) - set(expected):
        raise RuntimeError("Unknown schema columns require explicit reconciliation")
    for name, column in expected.items():
        if name not in actual:
            if not column["nullable"]:
                raise RuntimeError("Missing required column requires a reviewed backfill")
            op.add_column(table, sa.Column(name, _type(column["type"]), nullable=True))
            continue
        current = actual[name]
        changes = {}
        if str(current["type"]) != column["type"]:
            # Frozen differences widen existing string fields; UUID PK conversion
            # is handled separately, preserving its original identifier.
            if not isinstance(current["type"], sa.String) or not column["type"].startswith("VARCHAR(") or _type(column["type"]).length < current["type"].length:
                raise RuntimeError("Unexpected type conversion requires data review")
            changes["type_"] = _type(column["type"])
        if current["nullable"] != column["nullable"]:
            changes["nullable"] = column["nullable"]
        if current.get("default") != column["default"]:
            changes["server_default"] = sa.text(column["default"]) if column["default"] is not None else None
        if changes:
            with _batch(table) as batch:
                batch.alter_column(name, existing_type=current["type"], existing_nullable=current["nullable"], **changes)


def _reconcile_constraints(table, target) -> None:
    inspector = sa.inspect(op.get_bind())
    unique = inspector.get_unique_constraints(table)
    for item in unique:
        if sorted(item["column_names"]) not in target["unique"]:
            with _batch(table) as batch:
                batch.drop_constraint(item.get("name") or "uq_" + table + "_" + item["column_names"][0], type_="unique")
    present = [sorted(item["column_names"]) for item in sa.inspect(op.get_bind()).get_unique_constraints(table)]
    for columns in target["unique"]:
        if columns not in present:
            with _batch(table) as batch:
                batch.create_unique_constraint("uq_r03_" + table + "_" + "_".join(columns), columns)
    actual_checks = {item["name"]: item["sqltext"] for item in sa.inspect(op.get_bind()).get_check_constraints(table)}
    for check in target["checks"]:
        if actual_checks.get(check["name"]) == check["sql"]:
            continue
        with _batch(table) as batch:
            if check["name"] in actual_checks:
                batch.drop_constraint(check["name"], type_="check")
            batch.create_check_constraint(check["name"], _CHECK_DDL.get(check["name"], check["sql"]))
    foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys(table)
    for expected in target["foreign_keys"]:
        if any(item["constrained_columns"] == expected["columns"] and item["referred_table"] == expected["table"] and item["referred_columns"] == expected["referred_columns"] and (item.get("options") or {}) == expected["options"] for item in foreign_keys):
            continue
        with _batch(table) as batch:
            batch.create_foreign_key("fk_r03_" + table + "_" + expected["columns"][0], expected["table"], expected["columns"], expected["referred_columns"], **expected["options"])


def _reconcile_indexes(table, target) -> None:
    actual = [item for item in sa.inspect(op.get_bind()).get_indexes(table) if not item.get("duplicates_constraint")]
    desired = {item["name"]: item for item in target["indexes"]}
    for item in actual:
        expected = desired.get(item["name"])
        if expected is None or item["column_names"] != expected["columns"] or bool(item["unique"]) != expected["unique"]:
            op.drop_index(item["name"], table_name=table)
    existing_names = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table)}
    for name, item in desired.items():
        if name not in existing_names:
            options = {}
            if item["where"]:
                options[op.get_bind().dialect.name + "_where"] = sa.text(item["where"])
            op.create_index(name, table, item["columns"], unique=item["unique"], **options)


def upgrade() -> None:
    """Reconcile frozen known schema shapes without changing active RLS flags."""
    conn = op.get_bind()
    target_path = Path(__file__).resolve().parents[1] / "schema_targets" / ("20261018_reconciled_" + conn.dialect.name + ".json")
    contract = json.loads(target_path.read_text(encoding="utf-8"))
    target = contract["signature"]
    if schema_signature(conn) not in contract["accepted_sources"].values():
        raise RuntimeError("Source schema differs from reviewed migration paths; explicit drift reconciliation required")
    available = set(sa.inspect(conn).get_table_names()) - {"alembic_version"}
    if available != set(target["tables"]):
        raise RuntimeError("Unknown or missing tables require explicit schema reconciliation")
    for table in ("gym_settings", "gym_licenses"):
        _integer_id(table)
    for table, specification in target["tables"].items():
        _reconcile_columns(table, specification)
    _membership_data()
    for table, specification in target["tables"].items():
        _reconcile_constraints(table, specification)
        _reconcile_indexes(table, specification)
    if conn.dialect.name == "postgresql":
        for table, policy in (("clientes", "tenant_isolation_clientes"), ("planes_generados", "tenant_isolation_planes"),
                              ("subscriptions", "tenant_isolation_subscriptions"), ("payments", "tenant_isolation_payments")):
            exists = conn.execute(sa.text("SELECT 1 FROM pg_policies WHERE schemaname=current_schema() AND tablename=:table AND policyname=:policy"), {"table": table, "policy": policy}).first()
            if not exists:
                conn.execute(sa.text(_POLICY_DDL[table]))
    if schema_signature(conn) != target:
        raise RuntimeError("Reconciled schema does not match its frozen contract")


def downgrade() -> None:
    """Schema/identifier reconciliation is reversed only through verified restore."""
    raise RuntimeError("R03 rollback requires the verified pre-migration backup/restore procedure")
