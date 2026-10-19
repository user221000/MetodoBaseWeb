from pathlib import Path
import base64,hashlib,io,json,re,struct,tarfile
HERE=Path(__file__).parent
ROOT=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/linux-sca-native31-triage-20261019')
LAB=Path('F:/MetodoBaseWeb-linux-lab-20261019/evidence/sca-native-triage31-20261019/primary')
def sha(b):return hashlib.sha256(b).hexdigest()
def readj(p):return json.loads(p.read_bytes())
CHECKS=[];FACTS={}
def require(value,message='static criterion failed'):
    if not value:raise AssertionError(message)
def check(name,fn):
    try:fn();CHECKS.append({'name':name,'passed':True})
    except Exception as error:CHECKS.append({'name':name,'passed':False,'error_class':type(error).__name__,'detail':str(error)[:200]})
def function(text,name):
    match=re.search(r'^'+re.escape(name)+r'\([^;]*?\)\s*\{',text,re.M|re.S)
    if match is None:match=re.search(r'\b'+re.escape(name)+r'\([^;]*?\)\s*\{',text,re.S)
    require(match is not None,name)
    end=re.search(r'^}',text[match.end():],re.M);require(end is not None)
    start=match.start();stop=match.end()+end.end();return text[start:stop],text[:start].count('\n')+1

provenance=readj(ROOT/'cpython-exact-source-provenance-v3.json')
sources={}
def source_chain():
    tarbytes=(LAB/'Python-3.12.15.tar.xz').read_bytes();require(sha(tarbytes)==provenance['psf_tar_sha256']=='c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a')
    tag=readj(ROOT/'primary/cpython-tag-3.12.15.json');annotated=readj(ROOT/'primary/cpython-annotated-tag-3.12.15.json')
    require(tag['object']['sha']==annotated['sha']==provenance['cpython_tag_object'])
    require(annotated['object']['sha']==provenance['cpython_commit'] and annotated['object']['type']=='commit')
    names={'Modules/pyexpat.c':'pyexpat','Modules/_elementtree.c':'elementtree','Modules/expat/xmlparse.c':'xmlparse','Modules/expat/expat.h':'expat-h'}
    with tarfile.open(fileobj=io.BytesIO(tarbytes),mode='r:xz') as t:
        for r in provenance['verified_source_files']:
            b=t.extractfile('Python-3.12.15/'+r['path']).read();require(len(b)==r['bytes'] and sha(b)==r['sha256'])
            api=readj(ROOT/('primary/cpython-commit-'+names[r['path']]+'.json'))
            require(api['path']==r['path'] and provenance['cpython_commit'] in api['url'])
            require(base64.b64decode(api['content'])==b)
            require(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==api['sha']==r['git_blob'])
            sources[r['path']]=b.decode()
    recipe=(ROOT/'reused-primary/official-python-source-Dockerfile.txt').read_text()
    require(provenance['psf_tar_sha256'] in recipe and 'PYTHON_VERSION 3.12.15' in recipe and '--with-system-expat' not in recipe)
    FACTS['cpython_source_equivalence']={'tag':annotated['sha'],'commit':annotated['object']['sha'],'tar_sha256':sha(tarbytes),'files':provenance['verified_source_files'],'no_local_gpg_or_binary_rebuild':True}
check('PSF tar and annotated tag/commit/four Git blobs match exact source; official recipe agrees',source_chain)

native=readj(ROOT/'reused-primary/native811.json')
def expat_match():
    cna=readj(HERE/'fresh-primary/CVE-2026-77214.raw.json')['containers']['cna']
    require(cna['affected'][0]['versions'][0]['lessThanOrEqual']=='2.8.5')
    header=sources['Modules/expat/expat.h'];require(all(re.search(r'#\s*define\s+XML_'+k+r'_VERSION\s+'+v+r'\b',header) for k,v in [('MAJOR','2'),('MINOR','8'),('MICRO','5')]))
    body,line=function(sources['Modules/expat/xmlparse.c'],'XML_ParseBuffer')
    require('parser->m_bufferEnd += len' in body)
    require(not re.search(r'len\s*>\s*EXPAT_SAFE_PTR_DIFF\(parser->m_bufferLim,\s*parser->m_bufferEnd\)',body))
    fix=readj(ROOT/'primary/expat-fix-77214-commit.json');require(fix['sha']=='13c5f63a7f1c52c2feee3b16a1134d4fb68e9ea0')
    require(any('len > EXPAT_SAFE_PTR_DIFF(parser->m_bufferLim, parser->m_bufferEnd)' in f.get('patch','') for f in fix['files']))
    require(native['versions']['expat']=='expat_2.8.5')
    elf=next(r for r in native['elf_files'] if r['path']==native['imports']['pyexpat']['file']);require(elf['needed']==['libc.so.6'])
    FACTS['expat']={'decision':'ACCEPT component finding; no global application reachability/exploit claim','source_function_start_line':line,'measured_pyexpat':elf['path'],'measured_elf_sha256':elf['sha256'],'version':native['versions']['expat'],'fix_absent_in_exact_expected_source':True,'embedded_linkage_supported_by_needed':elf['needed']}
check('Expat inclusive affected boundary and missing capacity fix in correct function corroborate measured embedded version',expat_match)
def wrapper_scope():
    p=sources['Modules/pyexpat.c'];e=sources['Modules/_elementtree.c']
    require('#define BUF_SIZE 2048' in p)
    readbody,readline=function(p,'readinst');require(readbody.index('if (len > buf_size)')<readbody.index('memcpy(buf, ptr, len)'))
    parsefile=p[p.index('for (;;) {',p.index('pyexpat_xmlparser_ParseFile_impl')):] if 'pyexpat_xmlparser_ParseFile_impl' in p else p[p.index('for (;;) {',p.index('BUF_SIZE 2048')):]
    require(parsefile.index('XML_GetBuffer(self->itself, BUF_SIZE)')<parsefile.index('readinst(buf, BUF_SIZE, readmethod)')<parsefile.index('XML_ParseBuffer(self->itself, bytes_read'))
    require('1048576' in p and 'INT_MAX' in p and 'XML_Parse(self->itself' in p)
    require('capi.Parse = XML_Parse;' in p and 'EXPAT(st, Parse)' in e and e.count('INT_MAX')>=3)
    models=[{'length':n,'accepted_by_readinst_size_guard':0<=n<=2048} for n in [0,1,2047,2048,2049,2**31-1,2**31]]
    require([x['accepted_by_readinst_size_guard'] for x in models]==[True,True,True,True,False,False,False])
    FACTS['wrapper_scope']={'readinst_start_line':readline,'length_models':models,'decision':'ACCEPT bounded inspected standard callers only; REJECT global unreachability or native fix inference','model_is_not_C_execution':True}
check('Inspected Python wrappers acquire capacity before parse and reject oversized file reads before copy',wrapper_scope)

def ar_members(data):
    require(data[:8]==b'!<arch>\n');offset=8;out={}
    while offset<len(data):
        header=data[offset:offset+60];require(len(header)==60 and header[58:60]==b'`\n');size=int(header[48:58]);name=header[:16].decode().strip().rstrip('/');offset+=60;out[name]=data[offset:offset+size];offset+=size+(size%2)
    return out
def deb_elf(name):
    members=ar_members((LAB/name).read_bytes());data=next(v for k,v in members.items() if k.startswith('data.tar'))
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as t:
        candidates=[(r.name,t.extractfile(r).read()) for r in t if r.isfile() and ('.so.' in r.name)]
    hits=[(name,b,row) for name,b in candidates for row in native['elf_files'] if row['sha256']==sha(b)]
    require(len(hits)==1);return hits[0]
def symbols(data):
    require(data[:6]==b'\x7fELF\x02\x01');offset=struct.unpack_from('<Q',data,40)[0];entsize,count=struct.unpack_from('<HH',data,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*entsize) for i in range(count)];out=set()
    for s in sections:
        if s[1]!=11:continue
        st=sections[s[6]];strings=data[st[4]:st[4]+st[5]]
        for i in range(s[4],s[4]+s[5],s[9]):
            idx,info,other,section,value,size=struct.unpack_from('<IBBHQQ',data,i)
            if section and idx:out.add(strings[idx:].split(b'\0',1)[0].decode())
    return out
def zlib_scope():
    cna=readj(HERE/'fresh-primary/CVE-2026-85091.raw.json')['containers']['cna'];v=cna['affected'][0]['versions'][0];require(v['version']=='1.3.1.2' and v['lessThanOrEqual']=='1.3.2')
    with tarfile.open(LAB/'zlib_1.3.dfsg+really1.3.1.orig.tar.gz',mode='r:gz') as t:
        gz=next(t.extractfile(r).read() for r in t if r.name.endswith('/gzwrite.c'))
    require(gz==(ROOT/'primary/zlib-v1.3.1-gzwrite.c').read_bytes())
    require(b'gz_vacate' not in gz and b'state->again' not in gz)
    with tarfile.open(LAB/'zlib_1.3.dfsg+really1.3.1-1.debian.tar.xz',mode='r:xz') as t:
        series=t.extractfile('debian/patches/series').read().decode();require(not [l for l in series.splitlines() if l.strip() and not l.lstrip().startswith('#')])
    filename,b,elf=deb_elf('zlib1g_1_1.3.dfsg+really1.3.1-1+b1.deb');require(native['versions']['zlib_runtime']=='1.3.1')
    FACTS['zlib85091']={'decision':'ACCEPT specific published range/source mismatch; not an exception or all-zlib safety claim','runtime':'1.3.1','published_range':['1.3.1.2','1.3.2'],'gz_vacate_and_again_absent_in_exact_orig':True,'debian_patch_series_empty':True,'observed_elf':elf['path'],'deb_member':filename,'elf_sha256':sha(b),'CVE-2026-27171':'REMAINS OPEN; independent vulnerability and no blind upgrade to1.3.2'}
check('zlib85091 published range excludes measured1.3.1 and introduced nonblocking implementation absent; exact deb ELF agrees',zlib_scope)
def sqlite_scope():
    cna=readj(HERE/'fresh-primary/CVE-2026-50812.raw.json')['containers']['cna'];require(cna['affected'][0]['versions'][0]['version']=='n/a')
    fix=readj(ROOT/'primary/sqlite-applyv3-fix-commit.json')
    cpatch=next(x['patch'] for x in fix['files'] if x['filename']=='ext/session/sqlite3session.c');test=next(x['patch'] for x in fix['files'] if x['filename']=='ext/session/session9.test')
    require('sessionApplyOneOp' in cpatch and 'sqlite3changeset_apply_v2 db' in test)
    old=(ROOT/'primary/sqlite-3.46.1-session.c').read_bytes();debian=(HERE/'fresh-primary/debian-orig-sqlite3session.c').read_bytes();require(old==debian)
    body,line=function(old.decode(),'sessionApplyOneOp');require('if( p->abPK[i] || (bPatchset==0 && pOld) )' in body)
    binding,bindline=function(old.decode(),'sessionBindValue');require('sqlite3_value_type(pVal)' in binding)
    patchset=readj(HERE/'sqlite-debian-patches.json');require(not patchset['candidate_fix_patches'])
    with tarfile.open(HERE/'fresh-primary/sqlite3_3.46.1-7+deb13u2.debian.tar.xz',mode='r:xz') as t:
        rules=t.extractfile('debian/rules').read().decode();require('-DSQLITE_ENABLE_SESSION' in rules)
        patches='\n'.join(t.extractfile('debian/patches/'+p.split()[0]).read().decode() for p in patchset['series'])
        require('sessionApplyOneOp' not in patches and 'sessionBindValue' not in patches and 'sqlite3_value_type(sqlite3_value' not in patches)
    # Tiny logical counterexample only: not a changeset, parser, C execution or crash.
    pk=True;patchset_flag=True;pold=False
    require((pk or ((not patchset_flag) and pold)) is True and (pold and (pk or not patchset_flag)) is False)
    filename,b,elf=deb_elf('libsqlite3-0_3.46.1-7+deb13u2.deb');exports=symbols(b)
    require('sqlite3changeset_apply_v2' in exports and 'sqlite3changeset_apply_v3' not in exports)
    FACTS['sqlite50812']={'decision':'REJECT exclusion/no-applicability inferred from missing apply_v3; keep under investigation/open','measured':'3.46.1','v3_absent':True,'v2_exported':True,'shared_pre_fix_condition_present_in_debian_orig':True,'sessionApplyOneOp_line':line,'sessionBindValue_line':bindline,'upstream_fix_regression_calls_v2':True,'exact_debian_patchset_has_no_identified_fix':True,'debian_source_gpg_verified':False,'debian_build_enables_session':True,'deb_member':filename,'observed_elf':elf['path'],'elf_sha256':sha(b),'limits':'No malformed changeset, segfault, memory PoC or application reachability demonstrated'}
check('SQLite v3 absence cannot exclude shared v2 pre-fix logic; exact Debian orig/patches and measured ELF confirm counterevidence',sqlite_scope)
def openssl_scope():
    def ver(s):return tuple(int(v) for v in s.split('.'))
    rows=[]
    for file in sorted((HERE/'fresh-primary').glob('CVE-2026-*.raw.json')):
        if file.stem.split('.')[0] in ['CVE-2026-77214','CVE-2026-85091','CVE-2026-50812']:continue
        cna=readj(file)['containers']['cna'];ranges=[v for a in cna['affected'] for v in a['versions'] if v.get('status')=='affected' and v.get('versionType')=='semver']
        def affected(version):return any(ver(v['version'])<=ver(version)<ver(v['lessThan']) for v in ranges)
        require(affected('4.0.2') and not affected('4.0.3') and affected('3.5.8') and not affected('3.5.9'))
        cve=readj(file)['cveMetadata']['cveId'];rows.append({'id':cve,'4.0.2':True,'4.0.3':False,'3.5.8':True,'3.5.9':False})
    require(len(rows)==13)
    selection=readj(ROOT/'reused-primary/openssl-debian-backports-selection.json');require(selection['installed_package_version']=='3.5.7-1~deb13u3')
    require({r['id'] for r in selection['rows']}=={r['id'] for r in rows})
    changelog=(ROOT/'reused-primary/debian-openssl-installed-changelog.txt').read_text();require(all(r['id'] in changelog for r in rows))
    require(all(r['trixie']['fixed_version']=='3.5.7-1~deb13u3' for r in selection['rows']))
    dsa=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/linux-container-libpq-sec09-prepared-20261019/primary-docs/debian-dsa6531.html').read_bytes();require(sha(dsa)=='7e4f42d72f86e2c7fec15d702375cd4c68890becb19b9fb2a8463dc535a8fe60')
    require(all(r['id'].encode() in dsa for r in rows) and b'3.5.7-1~deb13u3' in dsa)
    require(native['versions']['cryptography_openssl'].startswith('OpenSSL 4.0.3'))
    FACTS['openssl13']={'decision':'ACCEPT per-component boundaries/backport only; no generic native safety claim','boundary_assertions':52,'rows':rows,'custom_1x_branches':'preserved in raw CNA; not coerced into numeric semver','debian_backport':'DSA6531 + installed changelog + exact3.5.7-1~deb13u3','dsa_sha256':sha(dsa),'psycopg_3.5.8':'13 CNA range matches remain SEC09 open','cryptography_4.0.3':'exact fixed boundary outside these13 numeric ranges'}
check('All13 fresh OpenSSL CNA branches preserve fixed4.0.3 boundary and affected3.5.8; exact Debian u3 backport supported',openssl_scope)

out=HERE/'source-review-results.json';require(not out.exists());out.write_text(json.dumps({'scope':'Static source/hash/ELF metadata and tiny arithmetic/boolean models only; no application/C execution/build/VM/install/PoC','checks':CHECKS,'passed':sum(r['passed'] for r in CHECKS),'total':len(CHECKS),'claims':FACTS},indent=2)+'\n',encoding='utf8')
print(json.dumps({'total':len(CHECKS),'passed':sum(r['passed'] for r in CHECKS),'failed':[r for r in CHECKS if not r['passed']],'decisions':{k:v.get('decision') for k,v in FACTS.items() if isinstance(v,dict) and 'decision' in v}}))
raise SystemExit(0 if all(r['passed'] for r in CHECKS) else 1)
