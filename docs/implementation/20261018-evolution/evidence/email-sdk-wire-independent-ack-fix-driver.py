"""Real Resend/requests JSON serialization, intercepted after PreparedRequest."""
from pathlib import Path
import copy
import hashlib
import importlib.metadata
import inspect
import json
import logging
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).parent
MAIN=Path('F:/MetodoBaseWeb-execution-20261018')
EVIDENCE=MAIN/'docs/implementation/20261018-evolution/evidence'
sys.path.insert(0,str(MAIN))
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True)
block_external_sockets()
import requests
import resend
from resend.request import Request

sha=lambda data:hashlib.sha256(data).hexdigest()
current=MAIN/'web/services/email_service.py'
test=MAIN/'tests/test_email_sdk_contract.py'
raw=current.read_bytes()
assert sha(raw)==sys.argv[1]
assert sha(test.read_bytes())==sys.argv[2]
assert sha((MAIN/'tests/test_auth_telemetry_privacy.py').read_bytes())=='a66d2674d743df380dea5b6b8addcfad46e9aa03a75f92e1ce75a65773bae4e5'
commit=subprocess.run(['git','rev-parse','f34ae98'],cwd=MAIN,capture_output=True,check=True,text=True).stdout.strip()
original=subprocess.run(['git','show',commit+':web/services/email_service.py'],cwd=MAIN,capture_output=True,check=True).stdout
assert original.count(b'"from_": _FROM_EMAIL')==1
assert b'"from": _FROM_EMAIL' in raw and b'"from_": _FROM_EMAIL' not in raw
assert (ROOT/'email-service-before-exact-git.py').read_bytes()==original
(ROOT/'email-service-ack-after-exact-raw.py').write_bytes(raw)
assert importlib.metadata.version('resend')=='2.50.0'
dependencies=[MAIN/name for name in ['web/services/email_service.py','tests/test_email_sdk_contract.py','tests/test_auth_telemetry_privacy.py','web/settings.py',
    'web/storage/objects.py','tests/isolation.py','requirements_web.lock','requirements_web-windows.lock',
    'requirements-test.lock','requirements-test-windows.lock']]
sdk_paths=sorted({Path(inspect.getfile(resend.Emails)),Path(inspect.getfile(Request)),
    Path(inspect.getfile(type(resend.default_http_client))),Path(inspect.getfile(requests.sessions.Session)),
    Path(inspect.getfile(requests.models.PreparedRequest))})
source_before={str(p):sha(p.read_bytes()) for p in dependencies+sdk_paths}
(ROOT/'ack-sources-before.json').write_text(json.dumps(source_before,indent=2)+'\n',encoding='utf8')

def service(label,source):
    module=ModuleType('email_sdk_independent_'+label)
    exec(compile(source,str(ROOT/('email-service-'+label+'.py')),'exec'),module.__dict__)
    return module

modules={'before':service('before',original),'after':service('after',raw)}
results=[]
observations=[]
marker='synthetic-private-email-content-marker'
recipient='synthetic-recipient@example.invalid'
subject='Synthetic subject '+marker
body='<p>Synthetic body '+marker+'</p>'

class LogCollector(logging.Handler):
    def __init__(self):super().__init__();self.messages=[]
    def emit(self,record):self.messages.append(record.getMessage())

def invoke(module,mode='contract',attachment=None,configured=True,plan=False,ack_value=None):
    prepared=[]
    collector=LogCollector()
    module.logger.addHandler(collector)
    old_level=module.logger.level
    module.logger.setLevel(logging.INFO)
    def in_memory_send(session,request,**kwargs):
        # requests has already converted SDK kwargs to the actual JSON body.
        payload=json.loads(request.body)
        prepared.append({'method':request.method,'url':request.url,'payload':payload})
        if mode=='transport_exception':raise requests.ConnectionError(marker+' '+recipient)
        response=requests.Response()
        response.request=request
        response.headers['Content-Type']='application/json'
        if mode=='contract':
            good=payload.get('from')==module._FROM_EMAIL and 'from_' not in payload
            status=200 if good else 422
            content={'id':'synthetic-inmemory-id'} if good else {'name':'validation_error','message':marker+' '+recipient,'statusCode':422}
        elif mode=='ack_custom':status,content=200,copy.deepcopy(ack_value)
        elif mode=='malformed_ack':status,content=200,{}
        elif mode=='bad_json':
            status,content=200,None
            response._content=b'not-json '+marker.encode()
        else:
            status=int(mode)
            content={'name':'validation_error','message':marker+' '+recipient,'statusCode':status}
        response.status_code=status
        if content is not None or mode=='ack_custom':response._content=json.dumps(content).encode()
        return response
    original_attachment=copy.deepcopy(attachment)
    try:
        with patch.object(module,'get_settings',lambda:SimpleNamespace(RESEND_API_KEY='synthetic-only' if configured else '')),\
                patch.object(resend,'api_key',None),\
                patch.object(requests.sessions.Session,'send',in_memory_send):
            if plan:
                with patch.object(module,'Path',side_effect=AssertionError('Byte attachment must not touch a path')):
                    result=module.send_plan_generated(recipient,'Synthetic <b>client</b>\r\nname',pdf_path='never-open-synthetic-path',pdf_content=b'%PDF-1.7\nsynthetic')
            else:
                result=module._send(recipient,subject,body,attachments=attachment)
    finally:
        module.logger.removeHandler(collector)
        module.logger.setLevel(old_level)
    assert attachment==original_attachment
    safe_logs=all(value not in '\n'.join(collector.messages) for value in (recipient,marker,subject,body,'never-open-synthetic-path'))
    module._independent_lastlogs=collector.messages
    return result,prepared,safe_logs

for label,module in modules.items():
    for kind,attachment in [('plain',None),('attachment',[{'filename':'synthetic.txt','content':[65,66]}]),('private_pdf',None)]:
        result,calls,logs=invoke(module,attachment=attachment,plan=kind=='private_pdf')
        payload=calls[0]['payload']
        correct='from' in payload and 'from_' not in payload
        expected=label=='after'
        passed=len(calls)==1 and calls[0]['method']=='POST' and calls[0]['url']=='https://api.resend.com/emails' and result is expected and correct is expected and logs
        if kind=='plain':passed=passed and payload['to']==[recipient] and payload['subject']==subject and payload['html']==body
        if kind=='attachment':passed=passed and payload['attachments']==attachment
        if kind=='private_pdf':
            passed=passed and payload['attachments']==[{'filename':'plan.pdf','content':list(b'%PDF-1.7\nsynthetic')}]
            passed=passed and '\r' not in payload['subject'] and '\n' not in payload['subject'] and '&lt;b&gt;client&lt;/b&gt;' in payload['html']
        results.append({'source':label,'case':kind,'passed':passed,'returned':result,'prepared_from_present':correct,
            'prepared_body_keys':sorted(payload),'request_count':len(calls),'operational_logs_private':logs,'boundary':'real SDK + real RequestsClient + real PreparedRequest; Session.send returns memory response'})
    result,calls,logs=invoke(module,configured=False)
    results.append({'source':label,'case':'missing_configuration','passed':result is False and not calls and logs,'request_count':len(calls)})
    for mode in ('400','403','422','429','500','bad_json','transport_exception'):
        result,calls,logs=invoke(module,mode=mode)
        results.append({'source':label,'case':'failure_'+mode,'passed':result is False and len(calls)==1 and logs,'returned':result,'request_count':len(calls),'operational_logs_private':logs})
    result,calls,logs=invoke(module,mode='malformed_ack')
    observations.append({'source':label,'case':'successful_HTTP_without_provider_id','expected_confirmed':False,'actual_confirmed':result,
        'security_assertion_passed':result is False,'operational_logs_private':logs,
        'scope':'Synthetic HTTP200 empty object, SDK has no SendResponse runtime validation. Present in exact Git baseline and current; not introduced by sender-key patch. No real provider behavior claimed.'})


original_fixed_key_source=(ROOT/'email-service-after-exact-raw.py').read_bytes()
assert sha(original_fixed_key_source)=='9a70a3bc4ec2c8912540f04d479de121d6ad70f29f18c898abe98892aa3c5f6a'
original_fixed_key=service('original_fixed_key',original_fixed_key_source)
limit=int(sys.argv[3])
ack_results=[]
ack_samples=[('empty_object',{},False),('empty_array',[],False),('null',None,False),('boolean',True,False),
    ('string','synthetic',False),('missing_id',{'unexpected':marker},False),('null_id',{'id':None},False),
    ('numeric_id',{'id':123},False),('boolean_id',{'id':True},False),('array_id',{'id':[]},False),
    ('object_id',{'id':{}},False),('empty_id',{'id':''},False),('blank_id',{'id':' \t\n'},False),
    ('oversized_id',{'id':'x'*(limit+1)},False),('valid_id',{'id':'synthetic-inmemory-valid-id'},True),
    ('boundary_id',{'id':'x'*limit},True),('valid_id_private_extra',{'id':'synthetic-inmemory-id','private':marker},True)]
for name,value,expected in ack_samples:
    result,calls,logs=invoke(modules['after'],mode='ack_custom',ack_value=value)
    events=modules['after']._independent_lastlogs
    accepted_log=any('accepted' in event.lower() for event in events)
    no_delivery_claim=not any('delivery_sent' in event or 'delivered' in event.lower() for event in events)
    passed=result is expected and len(calls)==1 and logs and no_delivery_claim and accepted_log is expected
    ack_results.append({'case':name,'expected':expected,'returned':result,'passed':passed,'operational_logs_private':logs,
        'no_delivery_claim':no_delivery_claim,'accepted_event':accepted_log})
old_result,_,old_logs=invoke(original_fixed_key,mode='ack_custom',ack_value={})
assert old_result is True and old_logs
assert all(row['passed'] for row in ack_results),json.dumps([row for row in ack_results if not row['passed']])

source_after={str(p):sha(p.read_bytes()) for p in dependencies+sdk_paths}
assert source_before==source_after
assert all(row['passed'] for row in results)
record={'scope':'Independent sender-key wire acceptance only; in-memory requests boundary, no sockets/provider/mail/real key',
    'baseline_commit':commit,'baseline_exact_git_sha256':sha(original),'current_raw_sha256':sha(raw),
    'root_test_raw_sha256':sha(test.read_bytes()),'scope_delta':'Additive acknowledgement fix; original key-only acceptance remains preserved separately',
    'sdk_version':importlib.metadata.version('resend'),'requests_version':importlib.metadata.version('requests'),
    'sources_before':source_before,'sources_after':source_after,'source_stable':source_before==source_after,
    'driver_sha256':sha(Path(__file__).read_bytes()),'total':len(results),'passed':sum(row['passed'] for row in results),
    'results':results,'ack_total':len(ack_results),'ack_passed':sum(row['passed'] for row in ack_results),'ack_results':ack_results,'id_length_bound':limit,'original_fixed_key_sha256':sha(original_fixed_key_source),'original_fixed_key_empty_ack_still_true':old_result,'baseline_and_fixed_ack_observations':observations,
    'limits':['No real email sent, accepted, delivered or domain verification claimed.','R16 provider verification, observability and recovery remain open.','Original fixed-key empty-ack negative remains frozen and reproducibly red; new acknowledgement gate is separate and additive.']}
(EVIDENCE/'email-sdk-wire-independent-ack-fix.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
(ROOT/'ack-record.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps({'wire_total':record['total'],'wire_passed':record['passed'],'source_stable':record['source_stable'],
    'baseline_expected_wire_rejections':3,'current_expected_wire_acceptances':3,'ack_total':len(ack_results),'ack_passed':sum(row['passed'] for row in ack_results),'original_fixed_key_empty_ack_still_true':old_result}))
