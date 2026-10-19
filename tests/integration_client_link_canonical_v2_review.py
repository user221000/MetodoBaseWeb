"""Separate canonical29 regressions for the independent V1 security findings."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests import integration_client_link_canonical_postgres as shared

lab=shared.lab
clean_lab=shared.clean_lab
GA,GB,UA,TEAM,CA,CB=shared.GA,shared.GB,shared.UA,shared.TEAM,shared.CA,shared.CB
issue,accept,publish,consume_steps,tx=shared.issue,shared.accept,shared.publish,shared.consume_steps,shared.tx


@pytest.mark.parametrize('changed',['source_owner','actor_parent'])
def test_noncanonical_parent_cuts_current_recipient_grant(changed,lab):
    issued=issue(lab,gym=GA if changed=='source_owner' else GB,client=CA if changed=='source_owner' else CB,
        recipient=UA if changed=='source_owner' else TEAM)
    accept(lab,issued);identity=publish(lab,issued)
    with tx(lab,issued['actor']) as db:assert db.scalar(text('SELECT count(*) FROM client_plan_publications WHERE id=:id'),{'id':identity})==1
    with lab['admin'].begin() as db:db.execute(text('UPDATE usuarios SET team_gym_id=:parent WHERE id=:id'),{'parent':GB,'id':GA})
    try:
        with tx(lab,issued['actor']) as db:
            assert db.scalar(text('SELECT public.r12_canonical_gym(:id)'),{'id':GA}) is False
            assert db.scalar(text('SELECT count(*) FROM client_plan_publications WHERE id=:id'),{'id':identity})==0
    finally:
        with lab['admin'].begin() as db:db.execute(text('UPDATE usuarios SET team_gym_id=NULL WHERE id=:id'),{'id':GA})


@pytest.mark.parametrize('proof',['empty','wrong_purpose','valid'])
def test_owner_own_acceptance_requires_proof_until_deferred_commit(lab,proof):
    issued=issue(lab,recipient=GA)
    with tx(lab,GA,issued['token']) as db:
        consume_steps(db,issued)
        if proof=='empty':db.execute(text("SELECT set_config('app.client_invitation_digest','',true)"))
        elif proof=='wrong_purpose':db.execute(text("SELECT set_config('app.client_invitation_digest',:hash,true)"),{'hash':'f'*64})
        if proof=='valid':db.commit()
        else:
            with pytest.raises(DBAPIError):db.commit()
            db.rollback()
    with lab['admin'].connect() as db:
        assert db.scalar(text('SELECT status FROM client_account_links WHERE id=:id'),{'id':issued['link']})==('active' if proof=='valid' else 'pending')


@pytest.mark.parametrize('expression',[
    'public.r12_gym_scope(NULL)',
    'public.r12_proof(NULL::public.client_link_invitations)',
    'public.r12_pending_proof(NULL::public.client_account_links)',
    'public.r12_consumed_proof(NULL::public.client_account_links)',
    'public.r12_recipient(NULL::public.client_plan_publications)',
    'public.r12_unique_json(NULL::json)',
    "public.r12_unique_json('{}'::json,NULL)",
    "public.r12_keys('{}'::jsonb,NULL,ARRAY[]::text[])",
    "public.r12_keys('{}'::jsonb,ARRAY[]::text[],NULL)",
    "public.r12_number('0'::jsonb,NULL)",
    "public.r12_food(jsonb_build_object('alimento','synthetic','gramos',1),NULL)",
],ids=['scope-null','proof-null','pending-null','consumed-null','recipient-null','json-null','depth-null','allowed-null','required-null','positive-null','food-flag-null'])
def test_boolean_helpers_are_total_and_fail_closed_on_sql_null(lab,expression):
    with tx(lab,UA) as db:assert db.scalar(text('SELECT '+expression)) is False
