"""Build only patched pyexpat against this exact base; never rebuild libpython."""
from pathlib import Path
import argparse,difflib,hashlib,json,os,platform,struct,subprocess,sys,sysconfig,tarfile,urllib.request

HERE=Path(__file__).resolve().parent
INSERT=("  if (len > EXPAT_SAFE_PTR_DIFF(parser->m_bufferLim, parser->m_bufferEnd)) {\n"
        "    parser->m_errorCode = XML_ERROR_INVALID_ARGUMENT;\n"
        "    return XML_STATUS_ERROR;\n  }\n\n")
ANCHOR="  // Detect and avoid integer overflow\n  if ((uint64_t)len > UINT64_MAX - parser->m_parseEndByteIndex)"
ABI_KEYS=('SOABI','EXT_SUFFIX','SIZEOF_VOID_P','Py_DEBUG','Py_ENABLE_SHARED','CC','CFLAGS','CCSHARED','LDSHARED','CONFIG_ARGS')
def digest(data):return hashlib.sha256(data).hexdigest()
def pins():return json.loads((HERE/'source-pins.json').read_text())
def backport(original,patch,lock):
    assert digest(original)==lock['source_before_sha256'],'Unexpected original source'
    assert digest(patch)==lock['patch_sha256'],'Unexpected patch bytes'
    text=original.decode('utf-8');assert text.count(ANCHOR)==1
    fixed=text.replace(ANCHOR,INSERT+ANCHOR).encode()
    pre='    parser->m_parsingStatus.parsing = XML_PARSING;\n  }\n\n'
    post=ANCHOR+' {\n    parser->m_errorCode = XML_ERROR_NO_MEMORY;\n'
    assert text.count(pre+post)==1
    start=text[:text.index(pre+post)].count('\n')+1
    expected=('--- a/Modules/expat/xmlparse.c\n+++ b/Modules/expat/xmlparse.c\n@@ -'+str(start)+',6 +'+str(start)+',11 @@ XML_ParseBuffer(XML_Parser parser, int len, int isFinal) {\n'+''.join(' '+line for line in pre.splitlines(keepends=True))+''.join('+'+line for line in INSERT.splitlines(keepends=True))+''.join(' '+line for line in post.splitlines(keepends=True))).encode()
    assert patch==expected and digest(fixed)==lock['source_after_sha256']
    return fixed
def source_files(archive,lock):
    assert digest(archive.read_bytes())==lock['psf_source_sha256'],'Unexpected PSF source'
    selected={};prefix='Python-3.12.15/'
    with tarfile.open(archive,mode='r:xz') as tar:
        for member in tar.getmembers():
            relative=member.name.removeprefix(prefix)
            wanted=(relative.startswith('Modules/expat/') or relative in ('Modules/pyexpat.c','Modules/clinic/pyexpat.c.h','Modules/_elementtree.c','Include/pyexpat.h'))
            if not member.name.startswith(prefix) or not wanted:continue
            assert not member.issym() and not member.islnk(),'Link in selected source'
            if not member.isfile():continue
            assert relative not in selected and '..' not in Path(relative).parts and not relative.startswith('/')
            assert member.size<1024*1024
            selected[relative]=tar.extractfile(member).read()
    assert len(selected)==31 and sum(map(len,selected.values()))<4*1024*1024
    assert digest(selected['Modules/clinic/pyexpat.c.h'])==lock['clinic_header_sha256'],'Unexpected Argument Clinic header'
    return selected
def prepare(archive,output,lock):
    selected=source_files(archive,lock);before={name:digest(data) for name,data in selected.items()}
    selected[lock['source_relative_path']]=backport(selected[lock['source_relative_path']],(HERE/'13c5f63.patch').read_bytes(),lock)
    output.mkdir(exist_ok=False,parents=True)
    for relative,data in selected.items():
        path=output/'source'/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    after={name:digest(data) for name,data in selected.items()};assert [p for p in before if before[p]!=after[p]]==['Modules/expat/xmlparse.c']
    record={'source_sha256':lock['psf_source_sha256'],'fix_commit':lock['upstream_fix_commit'],'cve':lock['cve'],'version':'2.8.5','before':before,'after':after,'changed_source_files':['Modules/expat/xmlparse.c'],'scope':'Exact five-line upstream capacity guard backport; no version/header/CAPI/config/namespace changes.'}
    (output/'source-preparation.json').write_text(json.dumps(record,indent=2)+'\n')
    return record
def build(output,lock,prepared):
    assert sys.platform=='linux' and platform.machine()=='x86_64','Linux/amd64 build only'
    assert sys.version_info[:3]==(3,12,15) and struct.calcsize('P')==8
    abi={key:sysconfig.get_config_var(key) for key in ABI_KEYS}
    assert abi['SOABI']==lock['expected_soabi'] and abi['EXT_SUFFIX']==lock['expected_ext_suffix']
    assert abi['Py_DEBUG']==0 and abi['Py_ENABLE_SHARED']==1
    for name in ('CC','CXX','CFLAGS','CPPFLAGS','LDFLAGS','LDSHARED','AR','ARFLAGS'):
        assert not os.environ.get(name),'Unreviewed compiler environment override: '+name
    from importlib import metadata
    assert metadata.version('setuptools')=='84.0.0' and metadata.version('pip')=='26.2.1'
    include=Path(sysconfig.get_path('include'));assert include==Path('/usr/local/include/python3.12') and include.resolve()==include
    source=output/'source'
    assert digest((include/'pyexpat.h').read_bytes())==prepared['before']['Include/pyexpat.h']
    stdlib=Path(sysconfig.get_path('stdlib'));assert stdlib==Path('/usr/local/lib/python3.12')
    original=stdlib/'lib-dynload'/('pyexpat'+lock['expected_ext_suffix'])
    elementtree=stdlib/'lib-dynload'/('_elementtree'+lock['expected_ext_suffix'])
    assert digest(original.read_bytes())=='11eb83c00b747bb59c11ae229d437eee4a4757892cf41b2cee9cace7f87443f4'
    assert digest(elementtree.read_bytes())=='c6b51ba83831280f2e4302859f491e4b0f59dd4c2268e457b59fcddb028d8032'
    identities=[Path(sys.executable).resolve(),Path('/usr/local/lib/libpython3.12.so.1.0'),elementtree,Path(sysconfig.get_config_h_filename()),Path(sysconfig.get_makefile_filename())]
    identities+=sorted(include.rglob('*.h'))
    base_before={str(p):digest(p.read_bytes()) for p in identities}
    # setuptools' compiler helper consumes the installed base sysconfig. No setup
    # configuration, package install or build-isolation dependency download occurs.
    from setuptools._distutils.ccompiler import new_compiler
    from setuptools._distutils.sysconfig import customize_compiler
    compiler=new_compiler();customize_compiler(compiler);commands=[];spawn=compiler.spawn
    def recorded_spawn(command,**kwargs):commands.append(list(command));return spawn(command,**kwargs)
    compiler.spawn=recorded_spawn
    source_paths=[source/'Modules'/name for name in ('pyexpat.c','expat/xmlparse.c','expat/xmlrole.c','expat/xmltok.c')]
    objects=compiler.compile([str(p) for p in source_paths],output_dir=str(output/'objects'),include_dirs=[str(include),str(include/'internal'),str(source/'Modules/expat')],macros=[('HAVE_EXPAT_CONFIG_H','1')],extra_postargs=['-g0','-ffile-prefix-map='+str(output)+'=.'])
    artifact=output/('pyexpat'+lock['expected_ext_suffix']);compiler.link_shared_object(objects,str(artifact),libraries=['m'])
    raw=artifact.read_bytes();assert raw[:6]==b'\x7fELF\x02\x01' and int.from_bytes(raw[18:20],'little')==62
    base_after={str(p):digest(p.read_bytes()) for p in identities};assert base_before==base_after
    # Small valid/invalid documents and existing guarded Python APIs only. Never
    # invoke XML_ParseBuffer with a mismatched native allocation/length.
    smoke="""import io,json,sys,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import pyexpat,_elementtree,xml.etree.ElementTree as ET
assert Path(pyexpat.__file__).resolve()==Path(sys.argv[1])/sys.argv[2]
assert pyexpat.EXPAT_VERSION=='expat_2.8.5'
xml=b'<root><child>safe</child></root>'
p=pyexpat.ParserCreate();p.Parse(xml[:10],False);p.Parse(xml[10:],True)
p=pyexpat.ParserCreate();p.ParseFile(io.BytesIO(xml))
root=ET.fromstring(xml);assert root.find('child').text=='safe'
assert ET.parse(io.BytesIO(xml)).getroot().tag=='root'
class Oversize:
 def read(self,n):return b'x'*(n+1)
try:pyexpat.ParserCreate().ParseFile(Oversize())
except ValueError:pass
else:raise AssertionError('Oversized ParseFile read accepted')
try:ET.fromstring(b'<root>')
except ET.ParseError:pass
else:raise AssertionError('Malformed XML accepted')
print(json.dumps({'pyexpat':pyexpat.__file__,'expat_version':pyexpat.EXPAT_VERSION,'elementtree_sha256':hashlib.sha256(Path(_elementtree.__file__).read_bytes()).hexdigest(),'small_cases':6}))
"""
    checked=subprocess.run([sys.executable,'-I','-S','-c',smoke,str(output),artifact.name],capture_output=True,text=True,timeout=30)
    (output/'small-binding-tests.log').write_text(checked.stdout+'\nSTDERR\n'+checked.stderr);assert checked.returncode==0,checked.stderr
    result={'compiled_source':prepared,'abi':abi,'compiler_commands':commands,'artifact':artifact.name,'artifact_sha256':digest(raw),'artifact_bytes':len(raw),'interpreter_libpython_elementtree_config_headers_before':base_before,'interpreter_libpython_elementtree_config_headers_after':base_after,'base_quiet':True,'build_tools':{'pip':metadata.version('pip'),'setuptools':metadata.version('setuptools')},'small_binding_tests':json.loads(checked.stdout),'limits':'Compiled artifact/source attestation only; no product startup, OS71/SEC09 closure, broad XML reachability assertion or scanner ignore.'}
    (output/'build-provenance.json').write_text(json.dumps(result,indent=2)+'\n')
    sbom={'bomFormat':'CycloneDX','specVersion':'1.6','version':1,'components':[{'type':'library','name':'Expat embedded in pyexpat','version':'2.8.5','pedigree':{'commits':[{'uid':lock['upstream_fix_commit'],'url':'https://github.com/libexpat/libexpat/commit/'+lock['upstream_fix_commit']}],'patches':[{'type':'backport','diff':{'url':'13c5f63.patch'}}]},'properties':[{'name':'metodobase:patched-source-sha256','value':lock['source_after_sha256']},{'name':'metodobase:pyexpat-elf-sha256','value':digest(raw)},{'name':'metodobase:patch-target','value':lock['cve']}]}]}
    (output/'sbom.json').write_text(json.dumps(sbom,indent=2)+'\n')
    for name in ('source-pins.json','13c5f63.patch'): (output/name).write_bytes((HERE/name).read_bytes())
    (output/'COPYING.expat').write_bytes((source/'Modules/expat/COPYING').read_bytes())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--build',action='store_true');args=ap.parse_args();lock=pins()
    if args.build:
        assert sys.platform=='linux','Build disabled on host Windows'
        assert args.output==Path('/expat-output'),'Unexpected owned build output'
    archive=args.archive
    if archive is None:
        assert args.build,'Preparation requires an explicitly supplied pinned archive'
        archive=Path('/tmp/psf-expat-sec10.tar.xz');assert not archive.exists()
        with urllib.request.urlopen(lock['psf_source_url'],timeout=60) as response:raw=response.read(20829825)
        assert len(raw)==20829824 and digest(raw)==lock['psf_source_sha256'];archive.write_bytes(raw)
    os.environ['SOURCE_DATE_EPOCH']=str(lock['source_date_epoch']);os.environ['PYTHONHASHSEED']='0'
    prepared=prepare(archive,args.output,lock)
    if args.build:build(args.output,lock,prepared)
if __name__=='__main__':main()
