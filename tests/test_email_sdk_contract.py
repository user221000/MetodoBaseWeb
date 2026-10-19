"""Pinned real SDK serialization against an in-memory HTTP contract, no delivery."""

import json
from types import SimpleNamespace

import pytest


@pytest.fixture
def sdk_transport(monkeypatch):
    import resend
    from web.services import email_service

    calls = []

    class ContractClient:
        failure = False
        response_payload = {'id': 'synthetic-local-contract-id'}

        def request(self, **kwargs):
            calls.append(kwargs)
            payload = kwargs['json']
            valid = payload.get('from') == email_service._FROM_EMAIL and 'from_' not in payload
            if valid and not self.failure:
                content, status = self.response_payload, 200
            else:
                content, status = {'name': 'validation_error', 'statusCode': 422,
                    'message': 'Synthetic transport failure; recipient must not appear in logs'}, 422
            return json.dumps(content).encode('utf-8'), status, {'content-type': 'application/json'}

    client = ContractClient()
    monkeypatch.setattr(resend, 'default_http_client', client)
    monkeypatch.setattr(resend, 'api_key', resend.api_key)
    monkeypatch.setattr(email_service, 'get_settings', lambda: SimpleNamespace(RESEND_API_KEY='synthetic-only'))
    return email_service, client, calls


@pytest.mark.parametrize('attachments', [None, [{'filename': 'synthetic.txt', 'content': [65, 66]}]])
def test_sender_uses_real_sdk_wire_field_and_retains_payload(sdk_transport, attachments):
    service, _, calls = sdk_transport
    assert service._send('synthetic@example.invalid', 'Synthetic subject', '<p>Synthetic</p>', attachments) is True
    assert len(calls) == 1
    assert calls[0]['method'].lower() == 'post'
    assert calls[0]['url'].endswith('/emails')
    payload = calls[0]['json']
    assert payload['from'] == service._FROM_EMAIL and 'from_' not in payload
    assert payload['to'] == ['synthetic@example.invalid']
    assert payload['subject'] == 'Synthetic subject' and payload['html'] == '<p>Synthetic</p>'
    assert payload.get('attachments') == attachments


def test_missing_configuration_never_calls_sdk(sdk_transport, monkeypatch):
    service, _, calls = sdk_transport
    monkeypatch.setattr(service, 'get_settings', lambda: SimpleNamespace(RESEND_API_KEY=''))
    assert service._send('synthetic@example.invalid', 'Synthetic', 'Synthetic') is False
    assert calls == []


def test_sdk_rejection_is_false_with_class_only_log(sdk_transport, caplog):
    service, client, calls = sdk_transport
    client.failure = True
    assert service._send('synthetic@example.invalid', 'Synthetic', 'Synthetic') is False
    assert len(calls) == 1
    assert 'transport failed class=' in caplog.text
    assert 'synthetic@example.invalid' not in caplog.text
    assert 'recipient must not appear' not in caplog.text


@pytest.mark.parametrize('response', [{}, {'id': None}, {'id': ''}, {'id': '  '},
    {'id': 17}, {'id': ['synthetic']}, {'id': 'x' * 257}, [], 17],
    ids=['missing', 'null', 'empty', 'blank', 'integer-id', 'list-id', 'oversize-id', 'list-body', 'integer-body'])
def test_unconfirmed_response_never_claims_acceptance(sdk_transport, caplog, response):
    service, client, calls = sdk_transport
    client.response_payload = response
    assert service._send('synthetic@example.invalid', 'Synthetic', 'Synthetic') is False
    assert len(calls) == 1
    assert 'delivery_sent' not in caplog.text and 'delivery_accepted' not in caplog.text
