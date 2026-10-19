from pathlib import Path
import ast,hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-google33-peer-private-20261019';O=R/'docs/implementation/20261018-evolution/evidence/security-google33-independent-20261019'
WEB=T/'metodobase-candidate-web-20261018/Scripts/python.exe';AUTHOR=T/'metodobase-google33-author-aamidzkr';BASE='3587b3b3eee3a58367624472d7c0683baa8f10e0'
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()==BASE
original=(AUTHOR/'test_security_google_subject_peer.py').read_bytes();assert sha(original)=='35ec9a45d7a9307d53bb7ddb97b23e738218ff9504315225b33385214454ce22'
mapped=(R/'tests/test_google33_association_security.py').read_bytes()
class Normalize(ast.NodeTransformer):
    def visit_Constant(self,node):
        if node.value=='fixed_https_tokeninfo':return ast.copy_location(ast.Constant('fixed_https_jwks'),node)
        return node
    def visit_Name(self,node):
        if node.id=='CREDENTIAL':return ast.copy_location(ast.Call(func=ast.Name(id='signed_credential',ctx=ast.Load()),args=[],keywords=[]),node)
        return node
def assertions(raw):
    out={}
    for node in ast.parse(raw).body:
        if isinstance(node,ast.FunctionDef) and node.name.startswith('test_'):
            out[node.name]=[ast.dump(Normalize().visit(n),include_attributes=False) for n in ast.walk(node) if isinstance(n,ast.Assert)]
    return out
a,b=assertions(original),assertions(mapped);assert a==b and len(a)==3
save('original8-assertion-binding.json',{'original_raw_sha256':sha(original),'mapped_source_sha256':sha(mapped),'test_functions':{k:len(v) for k,v in a.items()},'all_original_assertions_AST_equal_after_only_transport_field_and_credential_expression_mapping':True,'transport_field_normalization':['fixed_https_tokeninfo','fixed_https_jwks'],'schema_fixture_mapping':'progress_db now current33 google_db; original progress_http retained','eight_cases':'two factories x (two business canaries plus two parametrized provider controls)','provider':'Real signed RSA JWTs; only HTTP JWKS transport synthetic. No principal or signature/crypto override.'})
def envphoto():
    return {'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
def sourcephoto():
    paths=subprocess.check_output(['git','ls-files','-z','--','web','api','core','config','tests','scripts','requirements*','Dockerfile','db_bootstrap.py','pyproject.toml'],cwd=R).decode().split('\0')
    return {n:sha((R/n).read_bytes()) for n in paths if n and (R/n).is_file()}
webcode="from pathlib import Path;import hashlib,importlib.metadata,json,sys;h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();print(json.dumps({'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python':h(sys.executable),'base_python':h(sys._base_executable)}))"
def webphoto():return json.loads(subprocess.check_output([str(WEB),'-B','-c',webcode]))
before={'source':sourcephoto(),'author92':envphoto(),'web89':webphoto()};assert len(before['author92']['packages'])==92 and len(before['web89']['packages'])==89
save('sqlite-before.json',before)
for label,exe in [('author92',sys.executable),('web89',str(WEB))]:
    check=subprocess.run([exe,'-m','pip','check'],capture_output=True);assert check.returncode==0;(O/('pip-'+label+'-before.raw.log')).write_bytes(check.stdout+check.stderr)
names=['tests/test_google33_association_security.py','tests/test_google33_http.py','tests/test_google33_headers.py','tests/test_google33_mfa_reauth_contract.py','tests/test_google33_identity_contract.py','tests/test_google33_recovery.py','tests/test_google_link_ui.py','tests/test_google_link_ui_contract.py']
receipts=P/'sqlite-association-receipts';receipts.mkdir()
command=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',*names,'-q','--tb=short','--basetemp='+str(P/'pytest-sqlite'),'--junitxml='+str(P/'sqlite.xml')]
run=subprocess.run(command,cwd=R,env=dict(os.environ,SEC_GOOGLE_PRIVATE_RECEIPTS=str(receipts),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=360)
(P/'sqlite-stdout.RAW.log').write_bytes(run.stdout);(P/'sqlite-stderr.RAW.log').write_bytes(run.stderr)
cases=ET.parse(P/'sqlite.xml').findall('.//testcase');rows=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped'] if c.find(k)is not None),'passed')} for c in cases];save('sqlite-cases.STRUCTURAL.json',rows)
after={'source':sourcephoto(),'author92':envphoto(),'web89':webphoto()};save('sqlite-after.json',after)
for label,exe in [('author92',sys.executable),('web89',str(WEB))]:
    check=subprocess.run([exe,'-m','pip','check'],capture_output=True);assert check.returncode==0;(O/('pip-'+label+'-after.raw.log')).write_bytes(check.stdout+check.stderr)
summary={'exit':run.returncode,'cases':len(rows),'outcomes':{k:sum(r['outcome']==k for r in rows) for k in ['passed','failure','error','skipped']},'source_author92_WEB89_bothPython_quiet':before==after,'source_files':len(before['source'])};save('sqlite-summary.json',summary);print(json.dumps(summary))
assert before==after
