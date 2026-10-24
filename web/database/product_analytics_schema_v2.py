"""Revision38 typed, linkable product facts; no contacts, health or free payload.

Origin is a declaration about data, never payment, consent or account rights.
The ledger is append-only. Source keys permit authorization and deduplication;
they are pseudonymous identifiers, not anonymous data.
"""
import uuid

from sqlalchemy import (CheckConstraint, Column, ForeignKey, ForeignKeyConstraint,
                        Index, Integer, String, Table, UniqueConstraint, func)

TABLE = "product_analytics_facts"
ORIGINS = ("unknown", "demo", "customer")
EVENTS = ("origin_declared", "plan_saved", "client_link_accepted",
          "plan_assignment_published", "plan_assignment_withdrawn",
          "assigned_plan_http200")


def fact_table(metadata, instant_type):
    return Table(TABLE, metadata,
        Column("id", String(32), primary_key=True, default=lambda: uuid.uuid4().hex),
        Column("owner_id", String(36), ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        Column("context", String(8), nullable=False),
        Column("client_id", String(36), nullable=True),
        Column("event_type", String(32), nullable=False),
        Column("source_id", String(36), nullable=False),
        Column("source_version", Integer, nullable=False),
        Column("origin", String(8), nullable=False),
        Column("occurred_at", instant_type, nullable=False, server_default=func.current_timestamp()),
        ForeignKeyConstraint(["owner_id", "client_id"], ["clientes.gym_id", "clientes.id_cliente"],
                             name="fk_product_fact_client", ondelete="RESTRICT"),
        CheckConstraint("length(id)=32 AND length(source_id) BETWEEN 1 AND 36", name="ck_product_fact_ids"),
        CheckConstraint("context IN ('gym','personal') AND ((context='gym' AND client_id IS NOT NULL) OR (context='personal' AND client_id IS NULL))", name="ck_product_fact_context"),
        CheckConstraint("origin IN ('unknown','demo','customer')", name="ck_product_fact_origin"),
        CheckConstraint("event_type IN ('origin_declared','plan_saved','client_link_accepted','plan_assignment_published','plan_assignment_withdrawn','assigned_plan_http200')", name="ck_product_fact_type"),
        CheckConstraint("source_version BETWEEN 1 AND 2147483647", name="ck_product_fact_version"),
        CheckConstraint("context='gym' OR event_type IN ('origin_declared','plan_saved')", name="ck_product_fact_personal"),
        UniqueConstraint("owner_id", "context", "event_type", "source_id", "source_version", name="uq_product_fact_source"),
        Index("ix_product_fact_report", "owner_id", "context", "occurred_at"),
        Index("ix_product_fact_origin", "owner_id", "context", "client_id", "event_type", "source_version"))
