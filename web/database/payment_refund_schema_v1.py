"""Nullable provider refund observations; no inferred historical monetary facts."""
import sqlalchemy as sa

RANGE = ("refund_amount_cents IS NULL OR (refund_amount_cents >= 0 "
         "AND refund_amount_cents <= amount_cents "
         "AND refund_amount_cents = CAST(refund_amount_cents AS BIGINT))")
COHERENCE = ("(refund_amount_cents IS NULL AND refund_observed_at IS NULL AND stripe_charge_id IS NULL) OR "
    "(refund_amount_cents IS NOT NULL AND refund_observed_at IS NOT NULL AND stripe_charge_id IS NOT NULL "
    "AND length(stripe_charge_id) BETWEEN 4 AND 255 AND "
    "((refund_amount_cents = 0 AND status = 'succeeded') OR "
    "(refund_amount_cents > 0 AND refund_amount_cents < amount_cents AND status = 'partially_refunded') OR "
    "(refund_amount_cents = amount_cents AND status = 'refunded')))")


def columns(datetime_type):
    return (
        sa.Column("refund_amount_cents", sa.Integer(),
                  sa.CheckConstraint(RANGE, name="ck_payment_refund_amount"), nullable=True),
        sa.Column("refund_observed_at", datetime_type, nullable=True),
        sa.Column("stripe_charge_id", sa.String(255),
                  sa.CheckConstraint(COHERENCE, name="ck_payment_refund_fact"), nullable=True),
    )
