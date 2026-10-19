"""Adversarial canonical cursor encodings, with a synthetic signing key only."""
import base64
from datetime import datetime
import json

import pytest

from web.services import personal_history_cursor as cursor

ARGS = {'secret':'synthetic-history-signing-key-only','subject':'synthetic-subject','profile':'synthetic-profile'}


@pytest.mark.parametrize('stamp', [None, datetime(1, 1, 1), datetime(2026, 10, 19, 1, 2, 3, 456789)])
def test_cursor_roundtrip_preserves_nulls_and_literal_stored_timestamps(stamp):
    value = cursor.encode_position(stamp, 2147483647, **ARGS)
    assert cursor.decode_position(value, **ARGS) == (stamp, 2147483647)
    assert 'subject' not in value and 'profile' not in value
    payload = base64.urlsafe_b64decode(value.split('.')[0]+'='*(-len(value.split('.')[0])%4))
    assert b'subject' not in payload and b'profile' not in payload


@pytest.mark.parametrize('payload', [
    [True,None,1], [2,None,1], [1,None,True], [1,None,0], [1,None,2147483648], [1,None,'1'],
    [1,False,1], [1,'2026-01-01T00:00:00Z',1], [1,'2026-02-30T00:00:00.000000',1],
    [1,'2026-01-01T00:00:00.000000+00:00',1], [1,None,1,2], {'v':1},
])
def test_even_validly_signed_wrong_types_and_shapes_are_rejected(payload):
    raw = json.dumps(payload,separators=(',',':')).encode()
    value = cursor._pack(raw)+'.'+cursor._pack(cursor._signature(raw,**ARGS))
    with pytest.raises(ValueError): cursor.decode_position(value,**ARGS)


def test_equivalent_but_noncanonical_json_or_base64_is_rejected():
    raw = b'[1, null, 1]'
    value = cursor._pack(raw)+'.'+cursor._pack(cursor._signature(raw,**ARGS))
    with pytest.raises(ValueError): cursor.decode_position(value,**ARGS)
    valid = cursor.encode_position(None,1,**ARGS)
    with pytest.raises(ValueError): cursor.decode_position(valid+'=',**ARGS)


def test_oversize_input_is_rejected_before_base64_or_json(monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('Oversize cursor reached decoding')
    monkeypatch.setattr(cursor.base64,'b64decode',forbidden)
    monkeypatch.setattr(cursor.json,'loads',forbidden)
    with pytest.raises(ValueError): cursor.decode_position('x'*181,**ARGS)


@pytest.mark.parametrize('field', ['secret','subject','profile'])
def test_signature_is_bound_to_all_context_fields(field):
    value = cursor.encode_position(None,1,**ARGS)
    with pytest.raises(ValueError): cursor.decode_position(value,**{**ARGS,field:'synthetic-other'})


def test_empty_configuration_never_creates_a_fallback_signing_key():
    with pytest.raises(RuntimeError): cursor.encode_position(None,1,**{**ARGS,'secret':''})
