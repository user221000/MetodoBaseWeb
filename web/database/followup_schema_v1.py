"""Frozen revision34 table contract. Events own the atomic task projection.

No names, contacts, notes, payments or health text are stored in this ledger.
RESTRICT preserves history pending a separately reviewed whole-scope purge.
"""
import sqlalchemy as sa

MAX_VERSION = 2147483647
TASKS = "followup_tasks"
EVENTS = "followup_task_events"
CAUSES = ("no_saved_plan", "no_plan_in_window", "plan_date_missing", "membership_date_passed")
STEPS = ("review_client_record", "review_plan_history", "review_membership_date")
# Shared, typed projection columns copied by the event trigger, never free JSON.
SNAPSHOT = (
    "gym_id", "client_id", "cause", "cause_evidence_hash", "observed_at", "plan_count",
    "last_plan_at", "membership_end", "priority_at_creation", "next_step", "assignee_id",
    "status", "version", "created_by", "created_at", "updated_at", "completed_by",
    "completed_at", "outcome", "cancelled_by", "cancelled_at", "cancel_reason",
)
IMMUTABLE = SNAPSHOT[:9] + ("created_by", "created_at")


def _in(column, choices):
    # Explicit TEXT literals survive pg_dump/reparse without relaxing contractv1.
    return "CAST(" + column + " AS TEXT) IN (" + ",".join("CAST('" + v + "' AS TEXT)" for v in choices) + ")"


def _hex(column, length):
    remainder = column
    for digit in "0123456789abcdef":
        remainder = "replace("+remainder+",'"+digit+"','')"
    return f"length({column})={length} AND {remainder}=''"


def _uuid(column):
    return (f"length({column})=36 AND substr({column},9,1)='-' AND substr({column},14,1)='-' AND "
        f"substr({column},19,1)='-' AND substr({column},24,1)='-' AND " + _hex(f"replace({column},'-','')", 32))


def snapshot_columns(instant_type=sa.DateTime):
    return [
        sa.Column("gym_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_id", sa.String(36), nullable=False),
        sa.Column("cause", sa.String(32), nullable=False),
        sa.Column("cause_evidence_hash", sa.String(64), nullable=False),
        sa.Column("observed_at", instant_type(), nullable=False),
        sa.Column("plan_count", sa.Integer(), nullable=False),
        sa.Column("last_plan_at", instant_type()), sa.Column("membership_end", sa.DateTime()),
        sa.Column("priority_at_creation", sa.Integer(), nullable=False),
        sa.Column("next_step", sa.String(32), nullable=False),
        sa.Column("assignee_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="RESTRICT")),
        sa.Column("status", sa.String(12), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", instant_type(), nullable=False), sa.Column("updated_at", instant_type(), nullable=False),
        sa.Column("completed_by", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="RESTRICT")),
        sa.Column("completed_at", instant_type()), sa.Column("outcome", sa.String(24)),
        sa.Column("cancelled_by", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="RESTRICT")),
        sa.Column("cancelled_at", instant_type()), sa.Column("cancel_reason", sa.String(32)),
    ]


def checks(prefix):
    return [
        sa.CheckConstraint(_in("cause", CAUSES), name=prefix+"cause"),
        sa.CheckConstraint(_in("next_step", STEPS), name=prefix+"step"),
        sa.CheckConstraint("next_step='review_client_record' OR (cause='membership_date_passed' AND next_step='review_membership_date') OR (cause<>'membership_date_passed' AND next_step='review_plan_history')", name=prefix+"cause_step"),
        sa.CheckConstraint(_in("status", ("open", "completed", "cancelled")), name=prefix+"status"),
        sa.CheckConstraint("version BETWEEN 1 AND 2147483647 AND priority_at_creation BETWEEN 1 AND 4 AND plan_count BETWEEN 0 AND 2147483647", name=prefix+"counters"),
        sa.CheckConstraint(_hex("cause_evidence_hash", 64)+" AND length(client_id) BETWEEN 1 AND 36", name=prefix+"source"),
        sa.CheckConstraint("length(gym_id) BETWEEN 1 AND 36 AND length(created_by) BETWEEN 1 AND 36 AND "
            "(assignee_id IS NULL OR length(assignee_id) BETWEEN 1 AND 36) AND "
            "(completed_by IS NULL OR length(completed_by) BETWEEN 1 AND 36) AND "
            "(cancelled_by IS NULL OR length(cancelled_by) BETWEEN 1 AND 36)", name=prefix+"references"),
        sa.CheckConstraint("observed_at<=created_at AND created_at<=updated_at", name=prefix+"instants"),
        sa.CheckConstraint("(status='open' AND completed_by IS NULL AND completed_at IS NULL AND outcome IS NULL AND cancelled_by IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) OR "
            "(status='completed' AND assignee_id IS NOT NULL AND completed_by IS NOT NULL AND completed_at IS NOT NULL AND completed_at=updated_at AND outcome IS NOT NULL AND outcome='review_recorded' AND cancelled_by IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) OR "
            "(status='cancelled' AND cancelled_by IS NOT NULL AND cancelled_at IS NOT NULL AND cancelled_at=updated_at AND cancel_reason IS NOT NULL AND (cancel_reason='created_in_error' OR cancel_reason='no_longer_applicable' OR cancel_reason='duplicate') AND completed_by IS NULL AND completed_at IS NULL AND outcome IS NULL)", name=prefix+"state"),
    ]


def task_table(metadata, instant_type=sa.DateTime):
    return sa.Table(TASKS, metadata,
        sa.Column("id", sa.String(36), primary_key=True), *snapshot_columns(instant_type),
        sa.Column("current_event_id", sa.String(36), sa.ForeignKey(EVENTS+".id", ondelete="RESTRICT", use_alter=True,
            name="fk_followup_current_event"), nullable=False),
        sa.ForeignKeyConstraint(["gym_id", "client_id"], ["clientes.gym_id", "clientes.id_cliente"], name="fk_followup_client_owner", ondelete="RESTRICT"),
        sa.UniqueConstraint("gym_id", "id", name="uq_followup_task_owner"),
        sa.CheckConstraint(_uuid("id"), name="ck_followup_task_id"), *checks("ck_followup_task_"),
        sa.Index("uq_followup_open_cause", "gym_id", "client_id", "cause", unique=True,
                 sqlite_where=sa.text("status='open'"), postgresql_where=sa.text("status='open'")),
        sa.Index("ix_followup_task_page", "gym_id", "created_at", "id"),
        sa.Index("ix_followup_assigned_page", "gym_id", "assignee_id", "created_at", "id"))


def event_table(metadata, instant_type=sa.DateTime):
    return sa.Table(EVENTS, metadata,
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("task_id", sa.String(36), nullable=False),
        *snapshot_columns(instant_type), sa.Column("actor_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_role", sa.String(12), nullable=False), sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("request_key", sa.String(36), nullable=False), sa.Column("request_hash", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["gym_id", "task_id"], [TASKS+".gym_id", TASKS+".id"],
            name="fk_followup_event_task", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"),
        sa.UniqueConstraint("task_id", "version", name="uq_followup_event_version"),
        sa.UniqueConstraint("gym_id", "actor_id", "request_key", name="uq_followup_event_request"),
        sa.CheckConstraint(_uuid("id")+" AND "+_uuid("request_key")+" AND "+_hex("request_hash", 64), name="ck_followup_event_keys"),
        sa.CheckConstraint("length(actor_id) BETWEEN 1 AND 36", name="ck_followup_event_actor"),
        sa.CheckConstraint(_in("kind", ("created", "updated", "completed", "cancelled")), name="ck_followup_event_kind"),
        sa.CheckConstraint(_in("actor_role", ("owner", "admin", "nutriologo")), name="ck_followup_event_role"),
        *checks("ck_followup_event_"), sa.Index("ix_followup_event_page", "gym_id", "task_id", "version"))


def tables(metadata):
    return task_table(metadata), event_table(metadata)
