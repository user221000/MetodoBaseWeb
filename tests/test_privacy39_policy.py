"""Finite technical policies use synthetic decisions, never legal defaults."""
from datetime import datetime,timedelta,timezone
import hashlib
import hmac
import json
import pytest
from web.services.privacy_policy import PrivacyPolicy,INVENTORY,INTERNAL,DELETABLE,load_policy
from web.services.privacy_suppression import canonical,authenticate_registry

NOW=datetime(2026,10,23,12,tzinfo=timezone.utc)
TABLES={name for group in INVENTORY.values() for name in group}|set(INTERNAL)


def synthetic_policy(**changes):
    value={'policy_id':'synthetic-no-legal-authority','version':1,'valid_from':NOW-timedelta(hours=1),
        'valid_through':NOW+timedelta(hours=1),'catalogue_tables':tuple(sorted(TABLES-set(INTERNAL))),
        'decisions':tuple({'category':name,'action':'delete' if name in DELETABLE else 'block',
            'basis_id':'synthetic-test-only'} for name in INVENTORY),
        'external_holds_reviewed':True,'hold_codes':()}
    value.update(changes)
    return PrivacyPolicy.model_validate(value)


def registry_bytes(*,key=b'R'*32,**changes):
    value={'schema':'metodobase-privacy-suppressions-v1','registry_id':'synthetic-external-log','generation':7,
        'issued_at':NOW.isoformat(),'valid_through':(NOW+timedelta(minutes=30)).isoformat(),
        'coverage_through':NOW.isoformat(),'entries':[]}
    value.update(changes)
    return canonical({'payload':value,'hmac_sha256':hmac.new(key,canonical(value),hashlib.sha256).hexdigest()})


def admit_registry(raw,**changes):
    values={'registry_id':'synthetic-external-log','minimum_generation':7,'required_as_of':NOW,
        'max_age':timedelta(minutes=5),'now':NOW}
    values.update(changes)
    return authenticate_registry(raw,b'R'*32,**values)


def test_policy_absence_unknown_tables_unresolved_holds_expiry_are_closed():
    with pytest.raises(ValueError):load_policy(None,subject_id='self',now=NOW,tables=TABLES)
    policy=synthetic_policy()
    assert set(policy.admit(TABLES,now=NOW))==set(INVENTORY)
    for tables,now in ((TABLES|{'unclassified_health_table'},NOW),(TABLES,NOW+timedelta(days=1))):
        with pytest.raises(ValueError):policy.admit(tables,now=now)
    for changes in ({'external_holds_reviewed':False},{'hold_codes':('unresolved_processor',)}):
        with pytest.raises(ValueError):synthetic_policy(**changes).admit(TABLES,now=NOW)


def test_policy_cannot_delete_unimplemented_append_only_or_object_category():
    for name in set(INVENTORY)-DELETABLE:
        decisions=tuple({'category':category,'action':'delete' if category==name else 'block','basis_id':'synthetic'} for category in INVENTORY)
        with pytest.raises(ValueError):synthetic_policy(decisions=decisions)


@pytest.mark.parametrize('changes',[{'minimum_generation':8},{'required_as_of':NOW+timedelta(seconds=1)},
    {'registry_id':'different'},{'now':NOW+timedelta(hours=1)},{'max_age':timedelta(0)}])
def test_external_watermark_generation_identity_age_and_expiry_are_mandatory(changes):
    with pytest.raises(ValueError):admit_registry(registry_bytes(),**changes)


@pytest.mark.parametrize('raw',[b'',b'{}',b'{"payload":{},"payload":{},"hmac_sha256":"x"}',b'{"payload":NaN,"hmac_sha256":"x"}'])
def test_missing_ambiguous_or_invalid_registry_is_not_activation_authority(raw):
    with pytest.raises(ValueError):admit_registry(raw)


def test_authenticated_registry_rejects_tamper_and_cross_subject_duplicate():
    value=json.loads(registry_bytes());value['payload']['generation']=8
    with pytest.raises(ValueError):admit_registry(canonical(value))
    entry={'subject_id':'self','request_id':'a'*32,'minimum_session_version':1,'closed_at':NOW.isoformat(),
        'policy_digest':synthetic_policy().digest(),'categories':sorted(DELETABLE)}
    with pytest.raises(ValueError):admit_registry(registry_bytes(entries=[entry,entry]))
    assert admit_registry(registry_bytes()).generation==7
