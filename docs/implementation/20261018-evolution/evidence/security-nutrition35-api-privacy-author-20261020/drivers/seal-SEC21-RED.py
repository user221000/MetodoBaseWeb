from pathlib import Path, PurePosixPath
import ast, hashlib, io, json, re, subprocess, tarfile, zipfile
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-nutrition35-api-peer-private-20261019'
O=R/'docs/implementation/20261018-evolution/evidence/security-nutrition35-api-error-red-independent-20261020';O.mkdir(exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
(O/'.gitattributes').write_bytes(b'* -text\n')
D=P/'malformed-envelope';summary=json.loads((D/'summary.json').read_bytes());assert summary['outcomes']=={'passed':2,'failure':4,'error':0,'skipped':0}
assert (D/'before.json').read_bytes()==(D/'after.json').read_bytes()
for n in ['before.json','after.json','pip-before.RAW.log','pip-after.RAW.log','cases.STRUCTURAL.json','summary.json','argv.json']:(O/n).write_bytes((D/n).read_bytes())
(O/'original-driver.py').write_bytes((T/'metodobase-sec-nutrition35-api-peer-run-20261019.py').read_bytes())
own='tests/test_security_nutrition35_error_privacy_peer.py';raw=(R/own).read_bytes();assert sha(raw)=='21b224280ef10843f4076d6107649f11318e1428259441f26a72941216a2b2ca'
bindings=[]
for path in ['web/nutrition_http.py','web/routes/clientes.py','api/routes/clientes.py','web/middleware/security_headers.py',own]:
 b=(R/path).read_bytes();bindings.append({'path':path,'RAW_SHA256':sha(b),'bytes':len(b),'CRLF_count':b.count(b'\r\n')})
save('source.json',{'reviewed_commit':'f7c11d103c0a10c9896a1193106e7b889369e91c','role':'independent peer; no product edits','verdict':'RED malformed declaration envelope reflects submitted health input','cases':6,'passed':2,'failed':4,'errors':0,'skips':0,'canary_SHA256':sha(raw),'auth':'real password and MFA through maintained identity fixtures; no identity override','factories':['api.app','web.main_web'],'runtime':'SQLite target35, no PostgreSQL SQL or profile reads','source_packages92_bothPython_Node_quiet':True,'pip_check_before_after':0,'global_acceptance':False,'third_party_disclosure_or_auth_bypass_claimed':False,'bindings':bindings})
save('private-original-bindings.json',{'private_parent_protected_before_payload':True,'parent_principals':['current Windows user','SYSTEM'],'files':[{'name':n,'bytes':(D/n).stat().st_size,'SHA256':sha((D/n).read_bytes())}for n in ['stdout.RAW.log','stderr.RAW.log','result.xml']],'RAW_normalized_or_reconstructed':False})
(O/'review.md').write_bytes('''Independent RED review of frozen f7c11d, SQLite35 and both HTTP factories. Four original cases fail: POST and PUT /api/clientes accept a JSON array envelope containing the new declaration field, reject it with422, and reflect the submitted declaration in FastAPI validation details. The two object-envelope controls pass and redact the same synthetic input. The failure occurs before the no-store/no-referrer and persistence assertions, which are not attributed as executed on failing cases. Root cause: NutritionRoute redacts only an error.body dict with the declaration key, or a path ending in /perfil. The list body fails that test and the default validation handler includes its input. This violates the wire invariant that validation errors never echo declaration values. No third-party disclosure, identity bypass, or real medical data is claimed. Real primary/password and MFA fixture authentication remains intact. No product changes, PostgreSQL, provider, Chrome, VM, Desktop or dependency install. Source,92 package METADATA and both Python/Node binaries are quiet; pip check0. Original stdout/stderr/XML remain private with original bytes and hashes. This is a confirmed narrow RED, not global API/UI35 acceptance.\n'''.encode())
scanner=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name=='scan');digest=sha(ast.dump(scanner).encode());assert digest=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath);exec(compile(ast.Module(body=[scanner],type_ignores=[]),'unchanged-scanner119','exec'),ns)
save('public-safety-scan.json',{'scanner119_AST_SHA256':digest,'unchanged':True,'JWT_guard':True,'files_pass':True})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())}for p in sorted(O.rglob('*'))if p.is_file()and p.name!='manifest.json'})
for p in list(O.rglob('*'))+[R/own]:
 if p.is_file():
  b=p.read_bytes();ns['scan'](b,p.name);assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}',b)
print(json.dumps({'files':sum(p.is_file()for p in O.rglob('*')),'source_SHA256':sha((O/'source.json').read_bytes()),'manifest_SHA256':sha((O/'manifest.json').read_bytes())}))
