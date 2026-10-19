"""Independent pure port boundary; no HTTP, database connection or provider."""
import inspect
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest


@pytest.fixture
def portal(monkeypatch):
    from web.services import stripe_service as service
    assert Path(service.__file__).resolve().is_relative_to(Path.cwd().resolve())
    calls=[]
    class Query:
        def filter(self,*criteria):
            assert len(criteria)==1
            return self
        def first(self):return SimpleNamespace(stripe_customer_id='cus_synthetic_review')
    class Database:
        def query(self,model):
            assert model is service.Subscription
            return Query()
    monkeypatch.setattr(service,'_init_stripe',lambda:True)
    monkeypatch.setattr(service,'get_settings',lambda:SimpleNamespace(BASE_URL='https://app.example.invalid'))
    monkeypatch.setattr(service.stripe.billing_portal.Session,'create',lambda **kw:calls.append(kw) or SimpleNamespace(url='https://provider.example.invalid/portal'))
    return inspect.unwrap(service.create_portal_session),Database(),calls


@pytest.mark.parametrize('value',['@outside.example.invalid/path','https://outside.example.invalid/path','//outside.example.invalid/path','\\outside.example.invalid/path','/\\outside.example.invalid/path','/dash\nboard','/dash\x7fboard',''],ids=['authority','scheme','network-path','backslash','slash-backslash','control','DEL','empty'])
def test_nonrelative_or_unsafe_return_is_rejected_before_external_port(portal,value):
    create,db,calls=portal
    with pytest.raises(ValueError):create(db,'owned-synthetic-gym',value)
    assert calls==[]


@pytest.mark.parametrize('value',['/usuario','/dashboard','/suscripciones?result=return#estado'],ids=['personal','B2B','query-fragment'])
def test_reviewed_relative_paths_preserve_exact_origin_and_content(portal,value):
    create,db,calls=portal
    assert create(db,'owned-synthetic-gym',value)=={'url':'https://provider.example.invalid/portal'}
    assert len(calls)==1 and calls[0]['return_url']=='https://app.example.invalid'+value
    assert urlsplit(calls[0]['return_url']).hostname=='app.example.invalid'
