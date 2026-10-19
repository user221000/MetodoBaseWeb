"""New templates cross the actual pinned SDK into an in-memory HTTP client."""
import pytest
from tests.test_email_sdk_contract import sdk_transport


@pytest.mark.parametrize('accepted',[True,False])
def test_reset_template_uses_ack_without_leaking_bearer_outside_html(sdk_transport,caplog,accepted):
    service,client,calls=sdk_transport
    client.response_payload={'id':'synthetic-reset-id'} if accepted else {}
    token='s'*43
    link='https://recovery.example.invalid/auth/reset-password#token='+token
    result=service.send_password_reset('synthetic@example.invalid','<script>private</script>',link)
    assert result is accepted and len(calls)==1
    call=calls[0]
    assert call['method'].lower()=='post' and call['url'].endswith('/emails')
    assert token not in call['url'] and token not in str(call.get('headers',{}))
    body=call['json']
    assert body['from']==service._FROM_EMAIL and 'from_' not in body
    assert body['to']==['synthetic@example.invalid']
    assert token in body['html'] and '<script>private</script>' not in body['html']
    assert '&lt;script&gt;private&lt;/script&gt;' in body['html']
    assert body.get('attachments') is None
    assert token not in caplog.text and 'synthetic@example.invalid' not in caplog.text
    assert 'delivered' not in caplog.text


def test_changed_notification_contains_no_reset_bearer_or_password(sdk_transport):
    service,client,calls=sdk_transport
    assert service.send_password_changed('synthetic@example.invalid','<private>') is True
    body=calls[0]['json']
    assert 'token=' not in body['html'] and 'reset-password' not in body['html']
    assert '&lt;private&gt;' in body['html'] and '<private>' not in body['html']
