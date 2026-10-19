"""Verify fixture-only privacy adaptation and unchanged independent wire criteria."""
import ast,copy,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).parent
main=Path('F:/MetodoBaseWeb-execution-20261018')
evidence=main/'docs/implementation/20261018-evolution/evidence'
name='tests/test_auth_telemetry_privacy.py'
original=subprocess.run(['git','show','f34ae98:'+name],cwd=main,capture_output=True,check=True).stdout
current=(main/name).read_bytes()
assert hashlib.sha256(current).hexdigest()=='a66d2674d743df380dea5b6b8addcfad46e9aa03a75f92e1ce75a65773bae4e5'
before,after=ast.parse(original),ast.parse(current)
assertions=lambda tree:[ast.dump(node,include_attributes=False) for node in ast.walk(tree) if isinstance(node,ast.Assert)]
assert assertions(before)==assertions(after)
expected=ast.parse('if outcome == "sent":\n    transport.Emails.send.return_value = {"id": "synthetic-provider-ack"}').body[0]
after_without_fixture=copy.deepcopy(after)
function=next(node for node in after_without_fixture.body if isinstance(node,ast.FunctionDef) and node.name=='test_email_logs_omit_recipient_subject_body_and_attachments')
matches=[node for node in function.body if ast.dump(node,include_attributes=False)==ast.dump(expected,include_attributes=False)]
assert len(matches)==1
function.body.remove(matches[0])
assert ast.dump(before,include_attributes=False)==ast.dump(after_without_fixture,include_attributes=False)
old_driver=(root/'review.py').read_text('utf8')
new_driver=(root/'ack_review.py').read_text('utf8')
start='for label,module in modules.items():'
end="    result,calls,logs=invoke(module,mode='malformed_ack')"
old_loop=old_driver.split(start,1)[1].split(end,1)[0]
new_loop=new_driver.split(start,1)[1].split(end,1)[0]
assert old_loop==new_loop
target=evidence/'email-sdk-wire-independent-ack-assertions.json'
record={'scope':'Independent exact AST test adaptation and wire-criteria continuity; no product or historical tests edited',
    'privacy_baseline_commit':subprocess.run(['git','rev-parse','f34ae98'],cwd=main,capture_output=True,check=True,text=True).stdout.strip(),
    'privacy_baseline_git_sha256':hashlib.sha256(original).hexdigest(),'privacy_current_raw_sha256':hashlib.sha256(current).hexdigest(),
    'privacy_assertion_count':len(assertions(before)),'all_assertions_identical':True,
    'only_ast_change':'if outcome == sent: transport.Emails.send.return_value = {id: synthetic-provider-ack}',
    'independent_22_wire_loop_identical':True,'wire_loop_sha256':hashlib.sha256(old_loop.encode()).hexdigest()}
target.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
(evidence/'email-sdk-wire-independent-ack-privacy-before-exact-git.py').write_bytes(original)
(evidence/'email-sdk-wire-independent-ack-privacy-after-exact-raw.py').write_bytes(current)
print(json.dumps(record))
