from pathlib import Path
import ast,hashlib,json
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp');old=tmp/'test_metodobase_mfa_diary_composed_headers_v2.py';raw=old.read_bytes();text=raw.decode()
assert hashlib.sha256(raw).hexdigest()=='454c492de9fb51f91c264c260c62cf0ae1a22426113da6f36f258499eef35980'
needle="""            # Both parents apply default API no-store when no downstream cache
            # policy exists; only diary/MFA force override of a supplied policy.
            headers.pop('Cache-Control')"""
replacement="""            # Match the real historical handler's explicit no-store header
            # (web/routes/usuario.py), while diary/MFA test an unsafe override.
            headers['Cache-Control'] = 'no-store'"""
assert text.count(needle)==1;text=text.replace(needle,replacement)
asserts=lambda b:[ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(b)) if isinstance(n,ast.Assert)]
assert asserts(raw)==asserts(text)
target=tmp/'test_metodobase_mfa_diary_composed_headers_v3.py';assert not target.exists();target.write_bytes(text.encode());digest=hashlib.sha256(target.read_bytes()).hexdigest()
driver=(tmp/'metodobase-mfa31-header-own-replay.py').read_text().replace('metodobase-mfa31-header-own-replay-20261019','metodobase-mfa31-header-own-v3-20261019').replace('test_metodobase_mfa_diary_composed_headers_v2.py',target.name).replace('454c492de9fb51f91c264c260c62cf0ae1a22426113da6f36f258499eef35980',digest)
script=tmp/'metodobase-mfa31-header-own-v3.py';assert not script.exists();script.write_bytes(driver.encode())
record={'v2_sha256':hashlib.sha256(raw).hexdigest(),'v3_sha256':digest,'all10asserts_AST_unchanged':True,'v2_failure':'Generic API default no-store,max-age=0 differs from exact no-store expected by this fixture. No product regression; exact history route explicitly supplies no-store in usuario.py419/432. V3 fixture now supplies that actual historical handler policy.','product_changed':False,'no_prior_raw_rewritten':True}
(tmp/'metodobase-mfa31-header-v3-causality.json').write_bytes((json.dumps(record,indent=2)+'\n').encode());print(json.dumps(record))
