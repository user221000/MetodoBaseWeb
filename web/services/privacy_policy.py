"""Explicit versioned technical policy. No retention periods or allow-all default."""
from datetime import datetime
from hashlib import sha256
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

INVENTORY = {
    'personal_diary_days': ('personal_diary_days',),
    'personal_client_progress': ('client_progress',),
    'account_and_credentials': ('usuarios','refresh_tokens','mfa_authorizations','mfa_credentials','mfa_recovery_codes','auth_external_identities','google_link_intents'),
    'personal_and_professional_records': ('clientes','planes_generados','generation_reservations','gym_generation_reservations','gym_profiles','gym_settings','gym_branding'),
    'links_and_append_only_history': ('client_account_links','client_link_invitations','client_plan_publications','progress_consents','followup_tasks','followup_task_events','product_analytics_facts'),
    'billing_and_legal_records': ('checkout_sessions','invoices','payments','purchase_intents','stripe_customers','stripe_webhook_events','subscriptions','user_subscriptions','provider_subject_associations','planes_suscripcion','gym_licenses','license_activations'),
    'notifications_and_audit': ('audit_log','auth_audit_log','notification_attempts','notification_billing_facts','notification_outbox','notification_preferences'),
    'private_objects': ('stored_objects',),
    'external_backups_and_processors': (),
}
DELETABLE = frozenset({'personal_diary_days','personal_client_progress'})
INTERNAL = frozenset({'privacy_requests','privacy_disposition_items'})


class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True,frozen=True)
    category: str = Field(pattern=r'^[a-z_]{1,64}$')
    action: Literal['delete','retain','block','external_confirmation']
    basis_id: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,64}$')


class PrivacyPolicy(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True,frozen=True)
    policy_id: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,64}$')
    version: int = Field(ge=1,le=2147483647)
    valid_from: datetime
    valid_through: datetime
    catalogue_tables: tuple[str,...]
    decisions: tuple[Decision,...]
    external_holds_reviewed: bool
    hold_codes: tuple[str,...]

    @model_validator(mode='after')
    def closed_contract(self):
        if (self.valid_from.utcoffset() is None or self.valid_through.utcoffset() is None
                or self.valid_from >= self.valid_through):
            raise ValueError('An explicit aware policy validity window is required')
        categories = [row.category for row in self.decisions]
        if set(categories) != set(INVENTORY) or len(categories) != len(set(categories)):
            raise ValueError('Every known category needs exactly one explicit decision')
        if any(row.action == 'delete' and row.category not in DELETABLE for row in self.decisions):
            raise ValueError('No executor is implemented for that delete category')
        if len(self.catalogue_tables) != len(set(self.catalogue_tables)):
            raise ValueError('Duplicate catalogue table')
        if any(not code or len(code)>64 or not code.isascii() for code in self.hold_codes):
            raise ValueError('Invalid hold code')
        return self

    def digest(self):
        return sha256(json.dumps(self.model_dump(mode='json'),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

    def admit(self, tables, *, now):
        if (now.utcoffset() is None or not self.valid_from <= now < self.valid_through
                or set(tables)-INTERNAL != set(self.catalogue_tables)
                or set(self.catalogue_tables) != {table for group in INVENTORY.values() for table in group}
                or not self.external_holds_reviewed or self.hold_codes):
            raise ValueError('Policy validity, inventory or holds remain unresolved')
        return {row.category:row for row in self.decisions}


def load_policy(provider, *, subject_id, now, tables):
    """A trusted explicit injection, never a client-selected policy or default."""
    if provider is None:
        raise ValueError('No operational privacy policy has been supplied')
    value = provider(subject_id=subject_id,now=now)
    if not isinstance(value,PrivacyPolicy):
        raise ValueError('The provider did not return a typed privacy policy')
    value.admit(tables,now=now)
    return value
