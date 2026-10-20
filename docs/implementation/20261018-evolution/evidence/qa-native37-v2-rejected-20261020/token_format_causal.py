from pathlib import Path
import ast,base64,hashlib,hmac,json,os,subprocess
from typing import Optional
ROOT=Path('F:/mb-qa-native37-20261020');P=Path(__file__).resolve().parent
source=(ROOT/'web/auth.py').read_bytes();tree=ast.parse(source.decode('utf-8-sig'))
functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('_sign','_make_token','_decode_token')]
assert len(functions)==3
namespace={'hmac':hmac,'hashlib':hashlib,'json':json,'base64':base64,'SECRET_KEY':os.urandom(32).hex(),'Optional':Optional}
exec(compile(ast.fix_missing_locations(ast.Module(body=functions,type_ignores=[])),'actual-web-auth-issuer-pure-extract','exec'),namespace)
payload={'id':'synthetic-parser-only','type':'access','sv':7}
token=namespace['_make_token'](payload);assert namespace['_decode_token'](token)==payload
assert len(token.split('.'))==2 and json.loads(base64.urlsafe_b64decode(token.split('.')[0]+'=='))==payload
private_input={'token':token,'expected_session_version':7}
with (P/'token-causal-input.private.json').open('xb') as out:out.write((json.dumps(private_input)+'\n').encode())
result=subprocess.run(['C:/Program Files/nodejs/node.exe',str(P/'parser-canary.cjs'),str(P/'legacy-token-parser.cjs')],
 input=(P/'token-causal-input.private.json').read_bytes(),capture_output=True)
with (P/'parser-before.stdout').open('xb') as out:out.write(result.stdout)
with (P/'parser-before.stderr').open('xb') as out:out.write(result.stderr)
value=json.loads(result.stdout);assert result.returncode==1 and value['passed']==0 and value['results'][0]['error_class']=='SyntaxError'
receipt={'source_auth_sha256':hashlib.sha256(source).hexdigest(),'actual_functions_AST_sha256':hashlib.sha256(ast.dump(ast.Module(body=functions,type_ignores=[]),include_attributes=False).encode()).hexdigest(),
 'actual_issuer_and_signature_verifying_decoder_used_pure':True,'same_payload_verified_by_actual_decoder':True,
 'actual_segments':2,'payload_position':0,'signature_position':1,'not_JWT_three_segments':True,
 'legacy_index1_canary':'RED_SyntaxError','private_input_sha256':hashlib.sha256((P/'token-causal-input.private.json').read_bytes()).hexdigest(),
 'parser_canary_sha256':hashlib.sha256((P/'parser-canary.cjs').read_bytes()).hexdigest(),
 'token_never_used_for_auth_or_published':True,'no_HTTP_PG_Chrome_or_service':True,
 'classification':'Harness token-format assumption. Native SyntaxError has matching site; original real token not persisted, so no reconstructed original-token claim.'}
with (P/'token-format-causal.json').open('xb') as out:out.write((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in receipt.items() if k not in ('private_input_sha256',)}))
