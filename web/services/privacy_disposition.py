"""Bounded real deletes, exact self predicates and durable category outcomes."""
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from web.database.models import Base, Cliente, ClientProgress, PersonalDiaryDay, PrivacyDispositionItem, Usuario
from web.database.tenant_context import bind_verified_subject
from web.services.account_privacy import _request, bump, fail, summary
from web.services.privacy_policy import DELETABLE
from web.services import mfa_service as mfa

MAX_BATCH_ROWS=200


def owned_query(subject,category):
    if category=='personal_diary_days':
        return PersonalDiaryDay,select(PersonalDiaryDay.id).where(PersonalDiaryDay.user_id==subject)
    if category=='personal_client_progress':
        profiles=select(Cliente.id_cliente).where(Cliente.gym_id==subject)
        return ClientProgress,select(ClientProgress.id).where(ClientProgress.gym_id==subject,ClientProgress.id_cliente.in_(profiles))
    raise ValueError('No deletion executor for this category')


def lock_closed_subject(db,subject):
    query=select(Usuario).where(Usuario.id==subject)
    if db.get_bind().dialect.name=='postgresql':query=query.with_for_update(nowait=True)
    else:db.execute(update(Usuario).where(Usuario.id==subject).values(id=Usuario.id))
    user=db.scalar(query.execution_options(populate_existing=True))
    if user is None or user.activo or user.team_gym_id or user.role.value=='owner' or user.tipo!='usuario':
        fail(409,'privacy_closed_personal_subject_required')
    bind_verified_subject(db,subject)
    return user


def apply_batch(db,subject,request_id,expected_version,policy,*,now=None,batch_size=MAX_BATCH_ROWS):
    """No COMMIT. Trusted operator owns this same transaction and explicit policy."""
    if type(batch_size) is not int or not 1<=batch_size<=MAX_BATCH_ROWS:
        raise ValueError('Bounded disposition batch required')
    current=mfa.instant(now)
    lock_closed_subject(db,subject)
    row=_request(db,subject,request_id,expected_version=expected_version)
    if row.closed_at is None or row.policy_digest!=policy.digest():
        fail(409,'privacy_closed_policy_bound_request_required')
    decisions=policy.admit(Base.metadata.tables,now=current)
    items=db.scalars(select(PrivacyDispositionItem).where(PrivacyDispositionItem.request_id==row.id,
        PrivacyDispositionItem.subject_id==subject).order_by(PrivacyDispositionItem.category).with_for_update(nowait=True)).all()
    if {item.category for item in items} != set(decisions):
        fail(409,'privacy_disposition_inventory_incomplete')
    changed=False
    for item in items:
        if item.category not in DELETABLE:continue
        if decisions[item.category].action!='delete' or item.status not in {'pending','failed','deleted'}:continue
        model,query=owned_query(subject,item.category)
        identities=list(db.scalars(query.order_by(model.id).limit(batch_size)))
        ambiguous=False
        if item.category=='personal_client_progress':
            own_profiles=select(Cliente.id_cliente).where(Cliente.gym_id==subject)
            ambiguous=db.scalar(select(ClientProgress.id).where(ClientProgress.gym_id==subject,
                ~ClientProgress.id_cliente.in_(own_profiles)).limit(1)) is not None
        if item.status=='deleted' and not identities and not ambiguous:continue
        # begin_nested flushes prior pending work unconditionally. Such a
        # failure belongs to the caller transaction, never to this category.
        savepoint=db.begin_nested()
        try:
            # A savepoint prevents a rejected FK/append-only delete from
            # committing any part of this category or losing other outcomes.
            with savepoint:
                if identities:
                    result=db.execute(delete(model).where(model.id.in_(identities),model.id.in_(query)))
                    if result.rowcount!=len(identities):raise ValueError('Disposition rows changed')
            remaining=db.scalar(query.limit(1)) is not None
            item.deleted_rows+=len(identities)
            item.status='blocked' if ambiguous else ('pending' if remaining else 'deleted')
            item.reason='ownership_mismatch_requires_review' if ambiguous else ('bounded_batch_pending' if remaining else 'owned_rows_deleted')
        except IntegrityError:
            item.status,item.reason='blocked','foreign_key_or_append_only_hold'
        bump(item,current);changed=True
    statuses={item.status for item in items}
    if statuses=={'deleted'}:
        desired=('completed','all_inventory_categories_deleted')
    elif 'deleted' in statuses:
        desired=('partially_applied','unresolved_categories_remain')
    elif statuses & {'blocked','pending_confirmation','failed','retained_by_policy'}:
        desired=('blocked','unresolved_categories_remain')
    else:
        desired=('executing','bounded_batches_pending')
    if changed or (row.state,row.reason)!=desired:
        row.state,row.reason=desired
        bump(row,current)
    db.flush()
    return summary(db,row)
