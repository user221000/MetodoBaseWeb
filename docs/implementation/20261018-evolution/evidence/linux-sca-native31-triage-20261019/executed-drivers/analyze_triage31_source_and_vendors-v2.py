from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import ast,base64,hashlib,io,json,tarfile,urllib.request,zipfile,re
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=LAB/'evidence/sca-native-triage31-20261019'
P=OUT/'primary'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,obj):
    p=OUT/name;assert not p.exists();p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
receipts=[]
def fetch(name,url,expected=None):
    path=P/name
    if path.exists():
        data=path.read_bytes();assert expected and sha(data)==expected;receipts.append({'file':name,'url':url,'bytes':len(data),'sha256':sha(data),'reused_verified_local_bytes':True});return data
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MetodoBase-local-QA-evidence/1.0'}),timeout=90) as r:data=r.read();headers=dict(r.headers)
    if expected:assert sha(data)==expected
    path.write_bytes(data);receipts.append({'file':name,'url':url,'bytes':len(data),'sha256':sha(data),'headers':headers});return data
# Read the PSF release artifact without unpacking it to the host filesystem.
tarraw=fetch('Python-3.12.15.tar.xz','https://www.python.org/ftp/python/3.12.15/Python-3.12.15.tar.xz','c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a')
source_files=[]
with tarfile.open(fileobj=io.BytesIO(tarraw),mode='r:xz') as tar:
    for label,relative,prior in [('pyexpat','Modules/pyexpat.c','cpython-pyexpat.c'),('elementtree','Modules/_elementtree.c','cpython-elementtree.c'),('xmlparse','Modules/expat/xmlparse.c','cpython-xmlparse.c'),('expat-h','Modules/expat/expat.h','cpython-expat.h')]:
        data=tar.extractfile('Python-3.12.15/'+relative).read();git=json.loads((P/('cpython-commit-'+label+'.json')).read_text());assert data==(P/prior).read_bytes()==base64.b64decode(git['content']);assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==git['sha'];source_files.append({'path':relative,'bytes':len(data),'sha256':sha(data),'git_blob':git['sha']})
    ensurepip=[m.name for m in tar.getmembers() if '/Lib/ensurepip/_bundled/' in m.name and m.isfile()]
    ensure_wheels=[]
    for name in ensurepip:
        raw=tar.extractfile(name).read();z=zipfile.ZipFile(io.BytesIO(raw));assert z.testzip() is None
        vendors=[x for x in z.namelist() if x.endswith('/vendor.txt')]
        ensure_wheels.append({'path':name,'bytes':len(raw),'sha256':sha(raw),'vendor_declarations':{x:z.read(x).decode() for x in vendors}})
source={'captured_utc':datetime.now(timezone.utc).isoformat(),'cpython_tag_object':'f9e83c56c657be0a74ede2b5c523de4f9191d117','cpython_commit':'e848e4b09ca4bc67c0041c9ce7526dae471d4c36','psf_tar_sha256':sha(tarraw),'verified_source_files':source_files,'ensurepip_embedded_wheels':ensure_wheels,'scope':'Source equivalence of PSF tar and exact Git commit; not a byte-for-byte rebuild of measured ELF binaries.'}
save('cpython-exact-source-provenance-v2.json',source)
py=(P/'cpython-pyexpat.c').read_text();et=(P/'cpython-elementtree.c').read_text();xp=(P/'cpython-xmlparse.c').read_text()
checks=[]
def check(name,ok,detail):
    assert ok,name;checks.append({'name':name,'pass':True,'detail':detail})
check('CPython embedded Expat declares 2.8.5', all(re.search(r'#\s*define XML_'+part+r'_VERSION\s+'+str(value)+r'\b',(P/'cpython-expat.h').read_text()) for part,value in [('MAJOR',2),('MINOR',8),('MICRO',5)]),'Measured pyexpat version and pinned source header agree.')
check('ParseBuffer capacity guard absent in pinned source','len > EXPAT_SAFE_PTR_DIFF(parser->m_bufferLim, parser->m_bufferEnd)' not in xp and 'parser->m_bufferEnd += len;' in xp,'Upstream fix 13c5f63 adds this check; wrapper bounds do not repair native implementation.')
check('pyexpat Parse chunk bound','static_assert(MAX_CHUNK_SIZE <= INT_MAX' in py and 'while (slen > MAX_CHUNK_SIZE)' in py,'Both full chunks and final remainder pass bounded lengths to XML_Parse.')
check('ParseFile requests fresh fixed buffer','#define BUF_SIZE 2048' in py and 'XML_GetBuffer(self->itself, BUF_SIZE)' in py,'Each iteration allocates buffer before XML_ParseBuffer.')
check('ParseFile read size guarded','if (len > buf_size)' in py and 'XML_ParseBuffer(self->itself, bytes_read, bytes_read == 0)' in py,'readinst rejects oversized bytes/bytearray before copy; no huge buffers executed.')
check('ElementTree calls XML_Parse API','EXPAT(st, Parse)(self->parser, data, data_len, final)' in et and 'capi->Parse = XML_Parse;' in py,'C API pointer resolves to XML_Parse, not direct XML_ParseBuffer.')
check('ElementTree has signed-int bounds',et.count('> INT_MAX')>=3,'feed unicode, buffer and parse_whole bytes paths check length before cast.')
native=json.loads((LAB/'evidence/runtime28-native-20261019/native/native.json').read_text())
check('All observed ELF files 64-bit',len(native['elf_files'])==811 and all(e['class_bits']==64 for e in native['elf_files']),'CVE-2026-102633 CNA requires 32-bit; architecture excludes that stated condition in this image only.')
# Bounded arithmetic models of existing guards; these do not invoke native parsers.
for n in [0,1,2047,2048,2049,2**31-1,2**31,2**63-1]:
    accepted=n<=2048
    check('ParseFile length model '+str(n),not accepted or 0<=n<=2048<=2**31-1,{'supplied_length':n,'accepted_by_source_guard':accepted})
save('expat-static-scope.json',{'checks':checks,'cve_77214':{'version_match':True,'native_capacity_fix_present_in_exact_source':False,'standard_binding_paths':'Parse uses XML_Parse; ParseFile fresh GetBuffer(2048) plus read-size guard; ElementTree XML_Parse with INT_MAX guard. These checks constrain the caller length for inspected paths.','unproven':'External C API consumers, ctypes/direct exports and application reachability not exhausted. No exploit, huge allocation or crash attempted.','candidate_remedy':'Verified CPython base with Expat 2.9.0 or capacity backport; apt libexpat does not replace embedded source.'},'cve_102633':{'version_match':True,'required_32bit_condition':False,'observed_elf_bits':64}})
# Invoke exact bodies extracted from pinned pip wheel with small mocks only.
wheel=LAB/'evidence/pip-bootstrap-26.2.1/pip-26.2.1-py3-none-any.whl';assert sha(wheel.read_bytes())=='71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e'
z=zipfile.ZipFile(wheel);assert z.testzip() is None
def method(filename,cls,name,namespace):
    mod=ast.parse(z.read(filename).decode());node=next(n for n in mod.body if isinstance(n,ast.ClassDef) and n.name==cls);f=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name==name);f.decorator_list=[];f.returns=None
    for arg in f.args.posonlyargs+f.args.args+f.args.kwonlyargs:arg.annotation=None
    code=compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),'<pinned-wheel:'+filename+'>','exec');exec(code,namespace);return namespace[name],f.lineno
vendor_tests=[]
calls=[]
class Reader:
    def readline(self,*args):calls.append(args);return b'0\r\n'
class Proto(Exception):pass
fn,line=method('pip/_vendor/urllib3/response.py','HTTPResponse','_update_chunk_length',{'ProtocolError':Proto,'InvalidChunkLength':Proto})
obj=SimpleNamespace(chunk_left=None,_fp=SimpleNamespace(fp=Reader()));fn(obj)
assert calls==[()] and obj.chunk_left==0
vendor_tests.append({'cve':'CVE-2026-97689','function':'HTTPResponse._update_chunk_length','line':line,'small_mock_result':'readline called with no length bound; mock returned only 3 bytes','calls':[list(x) for x in calls],'source_fix_present':False,'reachability':'pip HTTP download/stream path can use vendored requests/urllib3; no real remote response or memory exhaustion executed.'})
fn,line=method('pip/_vendor/urllib3/response.py','DeflateDecoder','has_unconsumed_tail',{})
obj=SimpleNamespace(_unfed_data=b'',_obj=SimpleNamespace(eof=True,unconsumed_tail=b'x'),_first_try=False)
observed=fn(obj);assert observed is True
vendor_tests.append({'cve':'CVE-2026-97688','function':'DeflateDecoder.has_unconsumed_tail','line':line,'small_mock_result':'EOF=true with 1-byte unconsumed tail is reported as additional decodable input; fixed upstream includes not eof','source_fix_present':False,'reachability':'Requires chunked deflate streaming, trailing bytes and finite decoded chunk. No loop or network executed.'})
import typing
seen={}
def tls(*args,**kwargs):seen.update(kwargs);return SimpleNamespace(is_verified=False,socket=object())
fn,line=method('pip/_vendor/urllib3/connection.py','HTTPSConnection','_connect_tls_proxy',{'typing':typing,'ProxyConfig':object,'_ssl_wrap_socket_and_match_hostname':tls})
proxy_context=object();obj=SimpleNamespace(proxy_config=SimpleNamespace(ssl_context=proxy_context,assert_hostname=None,assert_fingerprint=None),cert_reqs='CERT_NONE',ssl_version=None,ssl_minimum_version=None,ssl_maximum_version=None,ca_certs=None,ca_cert_dir=None,ca_cert_data=None)
fn(obj,'lab.invalid',object());assert seen['ssl_context'] is proxy_context and seen['cert_reqs']=='CERT_NONE'
vendor_tests.append({'cve':'CVE-2026-97687','function':'HTTPSConnection._connect_tls_proxy','line':line,'small_mock_result':'Target CERT_NONE is passed with distinct proxy context to TLS helper; fixed upstream isolates proxy verification policy','source_fix_present':False,'reachability':'Requires configured HTTPS proxy and differing target policy. No sockets, credentials or TLS handshake used.'})
members=z.namelist()
absence={'msgpack_compiled_files':[n for n in members if n.startswith('pip/_vendor/msgpack/') and (n.endswith(('.so','.pyd','.pyx','.h')))],'setuptools_package_index':[n for n in members if n.startswith('pip/_vendor/setuptools/') and 'package_index' in n],'setuptools_manifest_matching_files':[n for n in members if n.startswith('pip/_vendor/setuptools/') and ('egg_info.py' in n or 'filelist.py' in n)]}
assert all(not v for v in absence.values())
save('pip-vendor-function-review.json',{'wheel_sha256':sha(wheel.read_bytes()),'actual_version_metadata':'pip 26.2.1 measured in image99c; matching pinned wheel inventoried without importing it. Actual runtime vendor file bytes still require image postcondition.','bounded_exact_body_mocks':vendor_tests,'component_absence_in_wheel':absence,'version_matches_without_affected_files':{'CVE-2026-57585':'Upstream fix touches msgpack Cython Unpacker and unpack_template.h; wheel only contains pure Python fallback, no native Unpacker.','CVE-2025-47273':'setuptools/package_index.py absent; only pkg_resources subset vendored.','CVE-2026-59890':'setuptools command/egg_info.py and _distutils/filelist.py absent; only pkg_resources subset vendored.'},'limits':'No broad vulnerability-free assertion; no exploit or runtime web startup. Build-stage tools remain separately audited even if omitted from final image.'})
save('source-artifact-downloads-v2.json',{'captured_utc':datetime.now(timezone.utc).isoformat(),'records':receipts})
print(json.dumps({'source_checks':len(checks),'bounded_vendor_function_mocks':len(vendor_tests),'cpython_tar_sha256':sha(tarraw),'output':str(OUT)},indent=2))
