from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile
from datetime import datetime, timezone

root=Path(r'F:\mb-r25-reviewed32-20261019')
target=Path(r'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence\root-google-subject-contract-review-20261019')
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
sha=lambda data:hashlib.sha256(data).hexdigest()
assert not target.exists()
assert git('rev-parse','HEAD').decode().strip()=='345aa7ce16f65fec9481b48cfcd63c33ff3835fc'
assert not git('status','--porcelain','--untracked-files=no')
names=['web/services/google_identity.py','web/routes/auth.py','web/services/mfa_service.py','web/database/models.py']
files={name:(root/name).read_bytes() for name in names}
trees={name:ast.parse(blob) for name,blob in files.items()}
primary=next(n for n in trees[names[0]].body if isinstance(n,ast.ClassDef) and n.name=='VerifiedGooglePrimary')
primary_fields=[n.target.id for n in primary.body if isinstance(n,ast.AnnAssign)]
assert primary_fields==['email','authenticated_at']
login=next(n for n in trees[names[1]].body if isinstance(n,ast.AsyncFunctionDef) and n.name=='google_login')
reauth=next(n for n in trees[names[2]].body if isinstance(n,ast.FunctionDef) and n.name=='reauthenticate')
user=next(n for n in trees[names[3]].body if isinstance(n,ast.ClassDef) and n.name=='Usuario')
user_attributes=sorted({target.id for n in user.body if isinstance(n,ast.Assign) for target in n.targets if isinstance(target,ast.Name)})
source={'status':'STATIC_CONTRACT_REVIEW_REQUIRES_INDEPENDENT_SECURITY_CANARY',
    'source':'345aa7ce16f65fec9481b48cfcd63c33ff3835fc','retrieved_utc':datetime.now(timezone.utc).isoformat(),
    'files':{name:{'raw_sha256':sha(blob),'git_lf_sha256':sha(git('show','HEAD:'+name))} for name,blob in files.items()},
    'VerifiedGooglePrimary_fields':primary_fields,'Usuario_declared_attributes':user_attributes,
    'google_login_function_ast_sha256':sha(ast.dump(login,include_attributes=False).encode()),
    'reauthenticate_function_ast_sha256':sha(ast.dump(reauth,include_attributes=False).encode()),
    'observations':[
        'Provider verification calls fixed HTTPS Google tokeninfo, then checks configured aud and email_verified. A missing local issuer/exp check alone does not prove signature or expiry bypass: the provider endpoint supplies validation authority.',
        'Existing account lookup in google_login uses normalized email. VerifiedGooglePrimary and MFA reauthentication compare email/auth_time without a persisted Google subject binding in this path.',
        'Google-only accounts receive an unknown random password hash at creation. The new limited-retirement password flow cannot claim to support such accounts until a reviewed alternative exists.'],
    'hypothesis':'Email-based automatic association can exceed Google authority for third-party email without hd and does not retain the stable provider sub. Requires independent security reproduction and migration/linking design; no production exploit shown.',
    'decision':'New retirement scope accepts only an actually verified password and existing factor, with explicit fail-closed handling for unavailable primary. Do not weaken general authentication or invent subject backfill.',
    'limits':['Static code and provider-document contract review only. No token, provider call with credentials, account linkage, live data, schema change, authorization bypass or new test result.']}
research={'references':[
    {'title':'Verify the Google ID token on your server side','url':'https://developers.google.com/identity/gsi/web/guides/verify-google-id-token',
     'consulted_utc':source['retrieved_utc'],'facts':[
        'Google recommends associating the stable sub with the local account instead of using email as its identifier.',
        'For third-party email without hd, email_verified can reflect an older verification and Google does not establish current ownership of that email.',
        'The document recommends libraries for production verification and describes tokeninfo as a development/debugging validation endpoint.']},
    {'title':'OpenID Connect','url':'https://developers.google.com/identity/openid-connect/openid-connect',
     'consulted_utc':source['retrieved_utc'],'facts':['Google documents signature, audience, issuer and expiration validation and recommends local verification for production.']}],
    'interpretation':'Separate the account-association concern from a cryptographic validation claim. Provider responses mocked with impossible verified claims cannot establish a real-provider bypass.'}
definition=next(n for n in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
blobs={'driver.py':Path(__file__).read_bytes(),'source.json':(json.dumps(source,indent=2)+'\n').encode(),
       'provider-contract.json':(json.dumps(research,indent=2)+'\n').encode(),'.gitattributes':b'* -text\n'}
for name,blob in blobs.items():scan(blob,name)
target.mkdir();(target/'.gitattributes').write_bytes(blobs.pop('.gitattributes'))
for name,blob in blobs.items():
    with (target/name).open('xb') as handle:handle.write(blob)
manifest={path.name:{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())} for path in target.iterdir()}
(target/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
print(json.dumps({'prefix':str(target),'manifest_sha256':sha((target/'manifest.json').read_bytes()),'status':source['status']}))
