"""Resolve minimal exact provider identities; never grant rights from a link."""
from sqlalchemy.orm import Session
from web.database.models import ProviderSubjectAssociation
from web.database.tenant_context import bind_verified_subject


def provider_subject(db: Session, provider: str, resource_type: str, resource_id: str) -> str | None:
    """Lookup one authenticated provider resource; there is no public listing."""
    if not isinstance(resource_id, str) or not resource_id or len(resource_id) > 255:
        raise ValueError("Invalid provider resource identity")
    row = db.get(ProviderSubjectAssociation, (provider, resource_type, resource_id))
    return row.subject_id if row else None


def record_provider_subject(db: Session, provider: str, resource_type: str, resource_id: str,
                            subject_id: str, source_ref: str) -> None:
    """Stage a provider-verified purchase link; caller owns the transaction.

    An existing resource cannot move to another subject. A link records
    identity only: it never changes subscription state, money or quota.
    """
    bind_verified_subject(db, subject_id)
    existing = provider_subject(db, provider, resource_type, resource_id)
    if existing is not None:
        if existing != subject_id:
            raise ValueError("Provider resource is associated with another subject")
        return
    db.add(ProviderSubjectAssociation(provider=provider, resource_type=resource_type,
        resource_id=resource_id, subject_id=subject_id, provenance="verified_purchase", source_ref=source_ref))
    db.flush()
