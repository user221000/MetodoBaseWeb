from pathlib import Path, PurePosixPath
import ast, hashlib, io, json, re, tarfile, zipfile
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-nutrition35-api-peer-private-20261019'
O=R/'docs/implementation/20261018-evolution/evidence/security-nutrition35-private-headers-red-independent-20261020';O.mkdir(exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode());(O/'.gitattributes').write_bytes(b'* -text\n')
for phase,expected in [('own-http-security',{'passed':9,'failure':3,'error':0,'skipped':0}),('affected-maintained',{'passed':44,'failure':2,'error':0,'skipped':0})]:
 D=P/phase;assert json.loads((D/'summary.json').read_bytes())['outcomes']==expected;assert (D/'before.json').read_bytes()==(D/'after.json').read_bytes()
 for n in ['before.json','after.json','pip-before.RAW.log','pip-after.RAW.log','cases.STRUCTURAL.json','summary.json','argv.json']:(O/(phase+'-'+n)).write_bytes((D/n).read_bytes())
old=(P/'own-http-initial-canary.RAW.py').read_bytes();new=(R/'tests/test_security_nutrition35_http_peer.py').read_bytes();assert sha(old)=='70e2f58c2c20b92013fe22719d9eba28dedeaf258ab087bf14d5de553c32a17c'
framing=b'''    if c["factory_name"] == "api.app":
        # The legacy API's get_usuario_gym remains OWNER-only for this read.
        assert read.status_code == 403 and "allergies" not in read.text
    else:
        assert read.status_code == 200 and read.json()["restricciones_nutricionales"] == payload
'''
assert new.replace(framing,b'    assert read.status_code == 200 and read.json()["restricciones_nutricionales"] == payload\n',1)==old
fn=lambda b:next(n for n in ast.parse(b).body if isinstance(n,ast.FunctionDef)and n.name=='test_unexpected_profile_failure_keeps_private_error_headers')
assert ast.dump(fn(old))==ast.dump(fn(new))
(O/'initial-own-http-canary.RAW.py').write_bytes(old);(O/'actual-current-replay-driver.RAW.py').write_bytes((P/'affected-maintained-driver.RAW.py').read_bytes())
save('framing-inverse.json',{'initial_SHA256':sha(old),'current_SHA256':sha(new),'inverse_byte_exact':True,'SEC22_function_AST_exact':True,'change':'Only viewer detail-read framing: api.app uses unchanged OWNER-only get_usuario_gym and must deny403; SaaS permits viewer read200. All mutation denies, privacy and persistence assertions preserved.','product_defect_for_viewer_framing':False})
save('private-original-bindings.json',{phase:[{'name':n,'bytes':(P/phase/n).stat().st_size,'SHA256':sha((P/phase/n).read_bytes())}for n in ['stdout.RAW.log','stderr.RAW.log','result.xml']]for phase in ['own-http-security','affected-maintained']})
save('source.json',{'reviewed_source_commit':'cdf103a28fe33e32cfeaac825d338d1901a5295e','frozen_base35':'f7c11d103c0a10c9896a1193106e7b889369e91c','finding':'SEC22','verdict':'2RED: unexpected profile read500 lacks private headers in both factories','HTTP_original_unique_cases':12,'initial_own_results':{'passed':9,'harness_framing_failure':1,'product_header_failures':2},'after_framing':{'maintained_passed':34,'own_passed':10,'same_header_failures':2},'real_auth_password_MFA':True,'header_canary_function_AST_unchanged':True,'error_body_generic_no_sentinel_reflection':True,'third_party_value_disclosure_claimed':False,'product_changed_since_SEC21':False,'PG_SQL_or_profile_reads':False,'global_acceptance':False})
(O/'review.md').write_bytes('''SEC22 independent RED on cdf103a2 (frozen35 f7c11d plus only SEC21 route-error patch). Real password/MFA HTTP fixtures use SQLite35. The same two GET /api/clientes/{id} cases inject a RuntimeError with a synthetic marker into the repository read after authentication. Both responses are opaque500 and do not echo the marker, but lack Cache-Control no-store. The route wrapper lets unexpected exceptions escape; the outer generic error response bypasses private response headers. This is a header-boundary defect under injected failure, not observed disclosure of health values or an identity bypass. Initial12owncases:9PASS,2headerRED,1harnessframingFAIL. The latter incorrectly expected the legacy API to permit a viewer detail read; get_usuario_gym still requires OWNER, while SaaS allows viewer reads. Only that read segment is adapted to API403/SaaS200, with an exact inverse. The two SEC22 functions retain exact AST/assertions; all mutation denies and persistence/privacy checks remain. The subsequent46cases are34maintainedPASS+10ownPASS+the same2SEC22RED, zero errors/skips. Sources,92package METADATA, both Python and Node binaries are quiet in both phases; pip check0. Original initial canary and stdout/stderr/XML remain private and exact. No PostgreSQL, private SQL profile, Chrome, VM, Desktop, live provider or installation. No global35 acceptance.\n'''.encode())
scanner=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name=='scan');digest=sha(ast.dump(scanner).encode());assert digest=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath);exec(compile(ast.Module(body=[scanner],type_ignores=[]),'unchanged-scanner119','exec'),ns)
save('public-safety-scan.json',{'scanner119_AST_SHA256':digest,'unchanged':True,'JWT_guard':True,'files_pass':True})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())}for p in sorted(O.rglob('*'))if p.is_file()and p.name!='manifest.json'})
for p in list(O.rglob('*'))+[R/'tests/test_security_nutrition35_http_peer.py',R/'tests/e2e/security_nutrition35_peer.cjs']:
 if p.is_file():
  b=p.read_bytes();ns['scan'](b,p.name);assert not re.search(rb'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}',b)
print(json.dumps({'files':sum(p.is_file()for p in O.rglob('*')),'source_SHA256':sha((O/'source.json').read_bytes()),'manifest_SHA256':sha((O/'manifest.json').read_bytes())}))
