"""Frozen36 notification records; no contact, card, health or provider payloads."""
import sqlalchemy as sa

PREFERENCES="notification_preferences"
FACTS="notification_billing_facts"
OUTBOX="notification_outbox"
ATTEMPTS="notification_attempts"
TABLES=(PREFERENCES,FACTS,OUTBOX,ATTEMPTS)
PURPOSES=("account_period_end","confirmed_payment_issue")
STATES=("pending","leased","sending","retry_wait","accepted","suppressed","failed","uncertain")


def choices(column,values):
    return "CAST("+column+" AS TEXT) IN ("+",".join("CAST('"+v+"' AS TEXT)" for v in values)+")"


def common(instant):
    return [sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("user_id",sa.String(36),sa.ForeignKey("usuarios.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("context",sa.String(8),nullable=False),sa.Column("created_at",instant(),nullable=False)]


def bounds(prefix):
    return [sa.CheckConstraint("length(id)=36 AND length(user_id) BETWEEN 1 AND 36",name=prefix+"ids"),
        sa.CheckConstraint(choices("context",("personal","gym")),name=prefix+"context")]


def preference_table(metadata,instant=sa.DateTime):
    return sa.Table(PREFERENCES,metadata,*common(instant),
        sa.Column("purpose",sa.String(32),nullable=False),sa.Column("channel",sa.String(8),nullable=False),
        sa.Column("version",sa.Integer,nullable=False),sa.Column("enabled",sa.Boolean,nullable=False),
        sa.Column("interval_hours",sa.Integer,nullable=False),sa.Column("contact_hash",sa.String(64)),
        sa.Column("contact_version",sa.Integer,nullable=False),
        sa.Column("request_key",sa.String(36),nullable=False),sa.Column("request_hash",sa.String(64),nullable=False),
        sa.UniqueConstraint("user_id","context","purpose","version",name="uq_notification_preference_version"),
        sa.UniqueConstraint("user_id","request_key",name="uq_notification_preference_request"),
        sa.UniqueConstraint("user_id","id",name="uq_notification_preference_owner"),
        sa.CheckConstraint(choices("purpose",PURPOSES)+" AND channel='email'",name="ck_notification_preference_purpose"),
        sa.CheckConstraint("version BETWEEN 1 AND 2147483647 AND interval_hours IN (24,72,168)",name="ck_notification_preference_version"),
        sa.CheckConstraint("contact_version BETWEEN 0 AND 2147483647",name="ck_notification_preference_contact_version"),
        sa.CheckConstraint("(enabled AND contact_hash IS NOT NULL AND length(contact_hash)=64) OR (NOT enabled AND contact_hash IS NULL)",name="ck_notification_preference_contact"),
        sa.CheckConstraint("length(request_key)=36 AND length(request_hash)=64",name="ck_notification_preference_request"),
        *bounds("ck_notification_preference_"),sa.Index("ix_notification_preference_latest","user_id","context","purpose","version"))


def fact_table(metadata,instant=sa.DateTime):
    return sa.Table(FACTS,metadata,*common(instant),
        sa.Column("version",sa.Integer,nullable=False),
        sa.Column("request_key",sa.String(36),nullable=False),sa.Column("request_hash",sa.String(64),nullable=False),
        sa.Column("provider",sa.String(20),nullable=False),sa.Column("subscription_id",sa.Integer,nullable=False),
        sa.Column("resource_type",sa.String(30),nullable=False),sa.Column("resource_id",sa.String(255),nullable=False),
        sa.Column("invoice_id",sa.String(255)),sa.Column("source_hash",sa.String(64),nullable=False),
        sa.Column("subscription_status",sa.String(30),nullable=False),sa.Column("invoice_status",sa.String(20),nullable=False),
        sa.Column("currency",sa.String(3),nullable=False),sa.Column("amount_due",sa.Integer,nullable=False),
        sa.Column("amount_paid",sa.Integer,nullable=False),sa.Column("amount_remaining",sa.Integer,nullable=False),
        sa.Column("paid",sa.Boolean,nullable=False),sa.Column("refunded",sa.Boolean,nullable=False),
        sa.Column("period_start",instant()),sa.Column("period_end",instant()),sa.Column("due_at",instant()),
        sa.Column("fresh_until",instant(),nullable=False),
        sa.ForeignKeyConstraint(["provider","resource_type","resource_id"],["provider_subject_associations.provider","provider_subject_associations.resource_type","provider_subject_associations.resource_id"],name="fk_notification_fact_mapping",ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subscription_id"],["subscriptions.id"],name="fk_notification_fact_subscription",ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id","id",name="uq_notification_fact_owner"),
        sa.UniqueConstraint("user_id","context","version",name="uq_notification_fact_version"),
        sa.UniqueConstraint("user_id","request_key",name="uq_notification_fact_request"),
        sa.CheckConstraint("length(request_key)=36 AND length(request_hash)=64",name="ck_notification_fact_request"),
        sa.CheckConstraint("version BETWEEN 1 AND 2147483647",name="ck_notification_fact_version"),
        sa.CheckConstraint(choices("provider",("stripe","mercadopago")),name="ck_notification_fact_provider"),
        sa.CheckConstraint(choices("resource_type",("subscription","payment")),name="ck_notification_fact_resource"),
        sa.CheckConstraint("length(resource_id) BETWEEN 1 AND 255 AND length(source_hash)=64 AND (invoice_id IS NULL OR length(invoice_id) BETWEEN 1 AND 255)",name="ck_notification_fact_source"),
        sa.CheckConstraint("currency='mxn' AND amount_due BETWEEN 0 AND 2147483647 AND amount_paid BETWEEN 0 AND 2147483647 AND amount_remaining BETWEEN 0 AND 2147483647",name="ck_notification_fact_money"),
        sa.CheckConstraint("fresh_until>created_at AND ((period_start IS NULL AND period_end IS NULL) OR (period_start IS NOT NULL AND period_end IS NOT NULL AND period_start<period_end))",name="ck_notification_fact_instants"),
        sa.CheckConstraint(choices("invoice_status",("unknown","open","paid","void","uncollectible")),name="ck_notification_fact_invoice"),
        sa.CheckConstraint(choices("subscription_status",("active","canceled","past_due","trialing","unpaid","incomplete","incomplete_expired","paused","unknown")),name="ck_notification_fact_subscription"),
        *bounds("ck_notification_fact_"),sa.Index("ix_notification_fact_latest","user_id","context","created_at","id"))


def outbox_table(metadata,instant=sa.DateTime):
    return sa.Table(OUTBOX,metadata,*common(instant),
        sa.Column("purpose",sa.String(32),nullable=False),sa.Column("channel",sa.String(8),nullable=False),
        sa.Column("preference_id",sa.String(36),nullable=False),sa.Column("fact_id",sa.String(36),nullable=False),
        sa.Column("source_hash",sa.String(64),nullable=False),sa.Column("contact_hash",sa.String(64),nullable=False),
        sa.Column("contact_version",sa.Integer,nullable=False),
        sa.Column("request_key",sa.String(36),nullable=False),sa.Column("request_hash",sa.String(64),nullable=False),
        sa.Column("state",sa.String(12),nullable=False),sa.Column("version",sa.Integer,nullable=False),
        sa.Column("attempt_count",sa.Integer,nullable=False),sa.Column("next_attempt_at",instant(),nullable=False),
        sa.Column("lease_hash",sa.String(64)),sa.Column("lease_until",instant()),
        sa.Column("sending_at",instant()),sa.Column("accepted_at",instant()),sa.Column("provider_id",sa.String(256)),
        sa.Column("last_reason",sa.String(32)),sa.Column("updated_at",instant(),nullable=False),
        sa.Column("exclude_hash",sa.String(64),unique=True),sa.Column("exclude_expires_at",instant()),
        sa.Column("exclude_protocol",sa.Integer),sa.Column("exclude_purpose",sa.String(32)),
        sa.UniqueConstraint("user_id","id",name="uq_notification_outbox_owner"),
        sa.UniqueConstraint("user_id","request_key",name="uq_notification_outbox_request"),
        sa.UniqueConstraint("user_id","context","purpose","source_hash",name="uq_notification_outbox_source"),
        sa.ForeignKeyConstraint(["user_id","preference_id"],[PREFERENCES+".user_id",PREFERENCES+".id"],name="fk_notification_outbox_preference",ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id","fact_id"],[FACTS+".user_id",FACTS+".id"],name="fk_notification_outbox_fact",ondelete="RESTRICT"),
        sa.CheckConstraint(choices("purpose",PURPOSES)+" AND channel='email'",name="ck_notification_outbox_purpose"),
        sa.CheckConstraint(choices("state",STATES),name="ck_notification_outbox_state"),
        sa.CheckConstraint("version BETWEEN 1 AND 2147483647 AND attempt_count BETWEEN 0 AND 3",name="ck_notification_outbox_counters"),
        sa.CheckConstraint("contact_version BETWEEN 0 AND 2147483647",name="ck_notification_outbox_contact_version"),
        sa.CheckConstraint("length(source_hash)=64 AND length(contact_hash)=64 AND length(request_key)=36 AND length(request_hash)=64",name="ck_notification_outbox_hashes"),
        sa.CheckConstraint("(lease_hash IS NULL AND lease_until IS NULL) OR (lease_hash IS NOT NULL AND length(lease_hash)=64 AND lease_until IS NOT NULL)",name="ck_notification_outbox_lease"),
        sa.CheckConstraint("NOT ("+choices("state",("leased","sending"))+") OR (lease_hash IS NOT NULL AND lease_until IS NOT NULL)",name="ck_notification_outbox_live_lease"),
        sa.CheckConstraint("state<>'sending' OR (sending_at IS NOT NULL AND attempt_count>0)",name="ck_notification_outbox_sending"),
        sa.CheckConstraint("(state='accepted' AND accepted_at IS NOT NULL AND provider_id IS NOT NULL AND length(provider_id) BETWEEN 1 AND 256) OR (state<>'accepted' AND accepted_at IS NULL AND provider_id IS NULL)",name="ck_notification_outbox_acceptance"),
        sa.CheckConstraint("(exclude_hash IS NULL AND exclude_expires_at IS NULL AND exclude_protocol IS NULL AND exclude_purpose IS NULL) OR (exclude_hash IS NOT NULL AND length(exclude_hash)=64 AND exclude_expires_at IS NOT NULL AND exclude_protocol IS NOT NULL AND exclude_protocol=1 AND exclude_purpose IS NOT NULL AND exclude_purpose='notification_exclude')",name="ck_notification_outbox_exclude"),
        sa.CheckConstraint("created_at<=updated_at",name="ck_notification_outbox_instants"),
        *bounds("ck_notification_outbox_"),sa.Index("ix_notification_outbox_claim","user_id","state","next_attempt_at"))


def attempt_table(metadata,instant=sa.DateTime):
    return sa.Table(ATTEMPTS,metadata,*common(instant),
        sa.Column("outbox_id",sa.String(36),nullable=False),sa.Column("sequence",sa.Integer,nullable=False),
        sa.Column("kind",sa.String(16),nullable=False),sa.Column("attempt_no",sa.Integer,nullable=False),
        sa.Column("fence",sa.Integer,nullable=False),sa.Column("reason",sa.String(32),nullable=False),
        sa.Column("request_key",sa.String(36)),sa.Column("request_hash",sa.String(64)),
        sa.UniqueConstraint("user_id","request_key",name="uq_notification_attempt_request"),
        sa.UniqueConstraint("outbox_id","sequence",name="uq_notification_attempt_sequence"),
        sa.ForeignKeyConstraint(["user_id","outbox_id"],[OUTBOX+".user_id",OUTBOX+".id"],name="fk_notification_attempt_owner",ondelete="RESTRICT"),
        sa.CheckConstraint(choices("kind",("handoff","accepted","not_sent","uncertain","suppressed")),name="ck_notification_attempt_kind"),
        sa.CheckConstraint("sequence BETWEEN 1 AND 2147483647 AND attempt_no BETWEEN 0 AND 3 AND fence BETWEEN 1 AND 2147483647 AND length(reason) BETWEEN 1 AND 32",name="ck_notification_attempt_counters"),
        sa.CheckConstraint("(request_key IS NULL AND request_hash IS NULL) OR (request_key IS NOT NULL AND length(request_key)=36 AND request_hash IS NOT NULL AND length(request_hash)=64)",name="ck_notification_attempt_request"),
        *bounds("ck_notification_attempt_"),sa.Index("ix_notification_attempt_frequency","user_id","context","kind","created_at"))


def tables(metadata,instant=sa.DateTime):
    return preference_table(metadata,instant),fact_table(metadata,instant),outbox_table(metadata,instant),attempt_table(metadata,instant)
