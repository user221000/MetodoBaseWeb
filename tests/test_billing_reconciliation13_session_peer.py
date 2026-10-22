"""Independent ownership and multi-resource boundaries for the private job."""
import json

import pytest
from sqlalchemy import select,update

from tests import test_billing_reconciliation13 as author
from web.database.models import Usuario
from web.database.tenant_context import current_tenant
from web.services import billing_reconciliation as service

account37_engine=author.account37_engine
billing_case=author.billing_case


@pytest.mark.parametrize('apply',[False,True],ids=['plan','apply'])
def test_rejecting_an_active_borrowed_session_must_not_rollback_or_close_it(billing_case,apply):
    case=billing_case
    db=case.factory()
    marker='Independent caller pending transaction'
    token=current_tenant.set(case.foreign)
    try:
        db.execute(update(Usuario).where(Usuario.id==case.foreign).values(nombre=marker))
        assert db.in_transaction()
        result=service.run(author.manifest(case),apply=apply,factory=lambda:db,
            reader_factory=lambda *_:pytest.fail('Rejected factory reached provider'))
        assert result['unconfirmed']==1 and result['next_cursor'] and not result['complete']
        assert current_tenant.get()==case.foreign
        # The factory violated the fresh-session contract. Reject it without
        # taking ownership of a caller's already running transaction.
        assert db.in_transaction(), 'Rejected borrowed transaction was rolled back or closed'
        assert db.scalar(select(Usuario.nombre).where(Usuario.id==case.foreign))==marker
    finally:
        db.rollback()
        db.close()
        current_tenant.reset(token)


@pytest.mark.parametrize('apply',[False,True],ids=['plan','apply'])
def test_session_factory_is_constructed_in_neutral_context_and_caller_restored(billing_case,apply):
    case=billing_case
    observed=[]
    reader=author.ProviderFacts(case)
    def factory():
        observed.append(current_tenant.get())
        return case.factory()
    token=current_tenant.set(case.foreign)
    try:
        result=service.run(author.manifest(case),apply=apply,factory=factory,reader_factory=reader.factory)
        assert observed==[''] and current_tenant.get()==case.foreign
    finally:
        current_tenant.reset(token)
    assert result['reconciled' if apply else 'planned']==1 and result['complete']


@pytest.mark.parametrize('page_limit',[1,2])
def test_manual_foreign_resource_cannot_starve_or_authorize_the_next_selected_resource(billing_case,page_limit):
    case=billing_case
    reader=author.ProviderFacts(case)
    document=json.loads(author.manifest(case))
    document['resources']=[{**document['resources'][0],'subject_id':case.foreign},document['resources'][0]]
    raw=json.dumps(document).encode()
    result=service.run(raw,apply=True,factory=case.factory,reader_factory=reader.factory,max_items=page_limit)
    assert result['manual']==1 and result['visited']==page_limit
    if page_limit==1:
        assert not reader.calls and not result['complete'] and result['next_cursor']
        result=service.run(raw,apply=True,factory=case.factory,reader_factory=reader.factory,
            cursor=result['next_cursor'],max_items=1)
    assert result['reconciled']==1 and result['complete'] and result['next_cursor'] is None
    assert author.facts(case)['subscription'][1]=='active'
