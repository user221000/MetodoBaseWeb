from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile,urllib.request,re,difflib,tempfile
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019');OUT=LAB/'evidence/expat-sec10-preparation32-20261019';CACHE=LAB/'evidence/sca-native-triage31-20261019'
def sha(b):return hashlib.sha256(b).hexdigest()
release=json.loads((OUT/'primary/expat-release-latest.json').read_text());records=[]
for name in ['expat-2.9.0.tar.gz','expat-2.9.0.tar.gz.asc']:
    asset=next(a for a in release['assets'] if a['name']==name);assert not (OUT/'primary'/name).exists()
    with urllib.request.urlopen(asset['browser_download_url'],timeout=60) as r:raw=r.read();headers=dict(r.headers)
    assert len(raw)==asset['size'] and sha(raw)==asset['digest'].split(':',1)[1];(OUT/'primary'/name).write_bytes(raw);records.append({'file':name,'url':asset['browser_download_url'],'bytes':len(raw),'sha256':sha(raw),'headers':headers})
psf=CACHE/'primary/Python-3.12.15.tar.xz';assert sha(psf.read_bytes())=='c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a'
with tarfile.open(psf,mode='r:xz') as t:base={m.name[len('Python-3.12.15/'):]:t.extractfile(m).read() for m in t.getmembers() if m.isfile() and (m.name.startswith('Python-3.12.15/Modules/expat/') or m.name in ['Python-3.12.15/Modules/pyexpat.c','Python-3.12.15/Modules/_elementtree.c','Python-3.12.15/Include/pyexpat.h','Python-3.12.15/Modules/Setup.stdlib.in','Python-3.12.15/Makefile.pre.in','Python-3.12.15/configure.ac'])}
with tarfile.open(OUT/'primary/expat-2.9.0.tar.gz',mode='r:gz') as t:up={m.name[len('expat-2.9.0/'):]:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
refresh=base['Modules/expat/refresh.sh'].decode();lib_files=re.search(r'lib_files=\(\n(.*?)\n\)',refresh,re.S).group(1).split();assert len(lib_files)==23
payload={name:up['lib/'+name] for name in lib_files};payload['COPYING']=up['COPYING']
# Apply exactly the two existing integrations documented by CPython's refresh recipe.
header=payload['expat_external.h'].decode();needle='#  define Expat_External_INCLUDED 1';assert header.count(needle)==1
header=header.replace(needle,needle+'\n/* Namespace external symbols to allow multiple libexpat version to\n   co-exist. */\n#include "pyexpatns.h"');payload['expat_external.h']=header.encode()
xml=payload['xmlparse.c'].decode();old='#if defined(_WIN32)\n#  include "random_rand_s.h"\n#endif /* defined(_WIN32) */';new='#if defined(_WIN32) && ! defined(XML_POOR_ENTROPY)\n#  include "random_rand_s.h"\n#endif /* defined(_WIN32) && ! defined(XML_POOR_ENTROPY) */';assert xml.count(old)==1;xml=xml.replace(old,new)
old='#  ifdef _WIN32\n  if (writeRandomBytes_rand_s';new='#  if defined(_WIN32) && ! defined(XML_POOR_ENTROPY)\n  if (writeRandomBytes_rand_s';assert xml.count(old)==1;xml=xml.replace(old,new);payload['xmlparse.c']=xml.encode()
payload['expat_config.h']=base['Modules/expat/expat_config.h'];payload['pyexpatns.h']=base['Modules/expat/pyexpatns.h']
# Refresh bookkeeping truthfully records full upstream release, not a cosmetic version change.
new_refresh=refresh.replace('expected_libexpat_tag="R_2_8_5"','expected_libexpat_tag="R_2_9_0"').replace('expected_libexpat_version="2.8.5"','expected_libexpat_version="2.9.0"').replace('expected_libexpat_sha256="920dde485e15eda0cce8d2310b41d492c534e5e3d89ad407a0b4176dd2ff88fe"','expected_libexpat_sha256="16afbb9cefead2aa278105cf27d9f597bde7fbf3dbb85015857ca7ca6a4e89ba"');payload['refresh.sh']=new_refresh.encode()
assert set(payload)=={p.split('Modules/expat/',1)[1] for p in base if p.startswith('Modules/expat/')}
working=Path(tempfile.mkdtemp(prefix='metodobase-expat-sec10-source-preview32-'));dest=working/'Modules/expat';dest.mkdir(parents=True)
rows=[];diff=[]
for name,data in sorted(payload.items()):
    old=base['Modules/expat/'+name];(dest/name).write_bytes(data);rows.append({'path':'Modules/expat/'+name,'before_sha256':sha(old),'after_sha256':sha(data),'changed':old!=data,'origin':'CPython-specific retained' if name in ['expat_config.h','pyexpatns.h'] else ('CPython refresh bookkeeping' if name=='refresh.sh' else 'upstream2.9.0 + existing CPython integrations where required')})
    if old!=data:diff.append(''.join(difflib.unified_diff(old.decode().splitlines(keepends=True),data.decode().splitlines(keepends=True),fromfile='a/Modules/expat/'+name,tofile='b/Modules/expat/'+name)))
(OUT/'cpython-expat-2.9.0-refresh-preview.patch').write_text(''.join(diff),encoding='utf-8')
before_h=base['Modules/expat/expat.h'].decode();after_h=payload['expat.h'].decode();api=lambda s:sorted(set(re.findall(r'XMLCALL\s+(XML_[A-Za-z0-9_]+)\s*\(',s)))
assert api(before_h)==api(after_h)
capacity='if (len > EXPAT_SAFE_PTR_DIFF(parser->m_bufferLim, parser->m_bufferEnd))';assert capacity in payload['xmlparse.c'].decode().split('\nXML_ParseBuffer(',1)[1].split('\nXML_GetBuffer(',1)[0]
assert '#include "pyexpatns.h"' in payload['expat_external.h'].decode();assert sha(payload['expat_config.h'])==sha(base['Modules/expat/expat_config.h']) and sha(payload['pyexpatns.h'])==sha(base['Modules/expat/pyexpatns.h'])
elementtree=base['Modules/_elementtree.c'].decode();assert all('st->expat_capi->'+part+'_VERSION != XML_'+part+'_VERSION' in elementtree for part in ['MAJOR','MINOR','MICRO'])
receipt={'prepared_utc':datetime.now(timezone.utc).isoformat(),'preview_only':True,'temporary_source_preview':str(working),'psf_source_sha256':sha(psf.read_bytes()),'upstream_expat_release':'2.9.0','upstream_asset_sha256':'16afbb9cefead2aa278105cf27d9f597bde7fbf3dbb85015857ca7ca6a4e89ba','files':rows,'changed_count':sum(r['changed'] for r in rows),'public_xmlcall_api_names_equal':True,'public_xmlcall_api_name_count':len(api(after_h)),'capi_header_unchanged_sha256':sha(base['Include/pyexpat.h']),'consumers':['Modules/pyexpat.c compiles embedded Expat','Modules/_elementtree.c imports pyexpat.expat_CAPI and requires exact Expat major/minor/micro; rebuild together'],'native_binary_abi_acceptance':'PENDING Linux compiler, exact base sysconfig/header gates, linkage/imports and stdlib/application tests. Equal symbol names do not prove ABI compatibility.','patch_sha256':sha((OUT/'cpython-expat-2.9.0-refresh-preview.patch').read_bytes()),'downloads':records,'scope':'Only owned Temp source preview and new LAB evidence. No product WT, Dockerfile, locks, compilation, native load or image mutation.'}
(OUT/'refresh-preview-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in receipt.items() if k not in ['downloads','files']},indent=2))
