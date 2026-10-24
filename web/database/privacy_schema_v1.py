"""Revision39 durable requests/dispositions, without health or token payloads."""
import uuid
from sqlalchemy import (CheckConstraint, Column, ForeignKey, ForeignKeyConstraint,
    Index, Integer, String, Table, UniqueConstraint, func)

REQUESTS = 'privacy_requests'
ITEMS = 'privacy_disposition_items'


def request_table(metadata, instant):
    return Table(REQUESTS, metadata,
        Column('id', String(32), primary_key=True, default=lambda: uuid.uuid4().hex),
        Column('subject_id', String(36), ForeignKey('usuarios.id', ondelete='RESTRICT'), nullable=False),
        Column('idempotency_key', String(36), nullable=False),
        Column('intent', String(24), nullable=False),
        Column('state', String(24), nullable=False, default='requested', server_default='requested'),
        Column('version', Integer, nullable=False, default=1, server_default='1'),
        Column('policy_id', String(64)), Column('policy_version', Integer), Column('policy_digest', String(64)),
        Column('reason', String(64), nullable=False, default='policy_required', server_default='policy_required'),
        Column('closed_at', instant), Column('created_at', instant, nullable=False, server_default=func.current_timestamp()),
        Column('updated_at', instant, nullable=False, server_default=func.current_timestamp()),
        UniqueConstraint('subject_id', 'idempotency_key', name='uq_privacy_request_key'),
        UniqueConstraint('id', 'subject_id', name='uq_privacy_request_subject'),
        CheckConstraint("intent='erase_personal_data'", name='ck_privacy_intent'),
        CheckConstraint("state IN ('requested','blocked','eligible','executing','partially_applied','completed')", name='ck_privacy_state'),
        CheckConstraint('version BETWEEN 1 AND 2147483647', name='ck_privacy_request_version'),
        CheckConstraint("(policy_id IS NULL AND policy_version IS NULL AND policy_digest IS NULL) OR (policy_id IS NOT NULL AND policy_version IS NOT NULL AND policy_digest IS NOT NULL AND length(policy_id) BETWEEN 1 AND 64 AND policy_version>0 AND length(policy_digest)=64)", name='ck_privacy_policy'),
        CheckConstraint("state NOT IN ('eligible','executing','partially_applied','completed') OR closed_at IS NOT NULL",name='ck_privacy_closed_execution'),
        Index('ix_privacy_subject', 'subject_id', 'id'))


def item_table(metadata, instant):
    return Table(ITEMS, metadata,
        Column('id', String(32), primary_key=True, default=lambda: uuid.uuid4().hex),
        Column('request_id', String(32), nullable=False), Column('subject_id', String(36), nullable=False),
        Column('category', String(64), nullable=False),
        Column('status', String(24), nullable=False), Column('reason', String(64), nullable=False),
        Column('version', Integer, nullable=False, default=1, server_default='1'),
        Column('deleted_rows', Integer, nullable=False, default=0, server_default='0'),
        Column('updated_at', instant, nullable=False, server_default=func.current_timestamp()),
        ForeignKeyConstraint(['request_id','subject_id'], ['privacy_requests.id','privacy_requests.subject_id'],
            name='fk_privacy_item_request', ondelete='RESTRICT'),
        UniqueConstraint('request_id','category', name='uq_privacy_item_category'),
        CheckConstraint("status IN ('pending','deleted','retained_by_policy','blocked','pending_confirmation','failed')", name='ck_privacy_item_status'),
        CheckConstraint("status<>'deleted' OR category IN ('personal_diary_days','personal_client_progress')",name='ck_privacy_implemented_delete'),
        CheckConstraint('version BETWEEN 1 AND 2147483647 AND deleted_rows>=0', name='ck_privacy_item_version'),
        CheckConstraint('length(category) BETWEEN 1 AND 64 AND length(reason) BETWEEN 1 AND 64', name='ck_privacy_item_labels'),
        Index('ix_privacy_item_subject', 'subject_id','request_id'))
