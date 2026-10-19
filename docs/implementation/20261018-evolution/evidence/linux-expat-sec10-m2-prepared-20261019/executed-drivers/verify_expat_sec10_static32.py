from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,importlib.util,json,subprocess,sys,tempfile
WT=Path(r'F:\mb-container-expat-sec10-20261019');HERE=WT/'runtime-source/expat-sec10';LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019');OUT=LAB/'evidence/expat-sec10-preparation32-20261019';CACHE=LAB/'evidence/sca-native-triage31-20261019'
def sha(b):return hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('expat_source_builder',HERE/'build.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
archive=CACHE/'primary/Python-3.12.15.tar.xz';lock=module.pins();selected=module.source_files(archive,lock);original=selected['Modules/expat/xmlparse.c'];patch=(HERE/'13c5f63.patch').read_bytes();rows=[]
def check(name,value):assert value,name;rows.append({'name':name,'pass':True})
check('Selected source tar exact',sha(archive.read_bytes())==lock['psf_source_sha256'])
signature=json.loads((OUT/'psf-signature-verification.json').read_text());check('Detached PSF GPG signature valid and fingerprint pinned',signature['verify_exit']==0 and '7169605F62C751356D054A26A821E680E5FA6305' in signature['validsig_status'])
upstream=json.loads((CACHE/'primary/expat-fix-77214-commit.json').read_text());upatch=next(x['patch'] for x in upstream['files'] if x['filename']=='expat/lib/xmlparse.c');added=lambda raw:[line[1:] for line in raw.splitlines() if line.startswith('+') and not line.startswith('+++')]
check('Patch adds same five lines as immutable upstream commit',added(patch.decode())==added(upatch) and len(added(upatch))==5)
check('Patch contains no source deletions',not [s for s in patch.decode().splitlines() if s.startswith('-') and not s.startswith('---')])
fixed=module.backport(original,patch,lock);check('Patched source exact expected hash',sha(fixed)==lock['source_after_sha256'])
check('Guard is inside correct ParseBuffer function',module.INSERT in fixed.decode().split('\nXML_ParseBuffer(',1)[1].split('\nXML_GetBuffer(',1)[0])
for name in ('Modules/expat/expat.h','Modules/expat/expat_config.h','Modules/expat/pyexpatns.h','Include/pyexpat.h'):
    check('Retained '+name,sha(selected[name])==sha(module.source_files(archive,lock)[name]))
check('Declared version remains 2.8.5',all(needle in selected['Modules/expat/expat.h'].decode() for needle in ['XML_MAJOR_VERSION 2','XML_MINOR_VERSION 8','XML_MICRO_VERSION 5']))
et=selected['Modules/_elementtree.c'].decode();check('ElementTree imports same capsule and checks all three version fields','"pyexpat", "expat_CAPI"' in et and all('st->expat_capi->'+s+'_VERSION != XML_'+s+'_VERSION' in et for s in ('MAJOR','MINOR','MICRO')))
check('C API Parse pointer unchanged source',b'capi->Parse = XML_Parse;' in selected['Modules/pyexpat.c'])
for name,source,diff in [('already applied',fixed,patch),('source byte mutation',b' '+original,patch),('patch byte mutation',original,patch+b'\n')]:
    try:module.backport(source,diff,lock)
    except AssertionError:rows.append({'name':'Reject '+name,'pass':True})
    else:raise AssertionError('Accepted '+name)
out=Path(tempfile.mkdtemp(prefix='metodobase-expat-sec10-static32-'))/'prepared';prep=module.prepare(archive,out,lock);check('Only one C file changed after preparation',prep['changed_source_files']==['Modules/expat/xmlparse.c'])
docker=(WT/'Dockerfile').read_text(encoding='utf-8');check('Build copies only replacement pyexpat module','COPY --from=expat-build /expat-output/pyexpat.cpython-312-x86_64-linux-gnu.so /usr/local/lib/python3.12/lib-dynload/pyexpat.cpython-312-x86_64-linux-gnu.so' in docker and 'COPY --from=expat-build /expat-output/_elementtree' not in docker)
check('Builder uses previously pinned backend stage','FROM psycopg-build AS expat-build' in docker and '/opt/psycopg-build-tools/bin/python -I /tmp/metodobase-expat-sec10/build.py --build' in docker)
build_source=(HERE/'build.py').read_bytes();compile(build_source,str(HERE/'build.py'),'exec');check('Builder Python compiles only',True)
locks=[]
for rel in subprocess.check_output(['git','-C',str(WT),'ls-files','*lock'],text=True).splitlines():
    raw=(WT/rel).read_bytes();base=subprocess.check_output(['git','-C',str(WT),'show','HEAD:'+rel]);assert raw.replace(b'\r\n',b'\n')==base.replace(b'\r\n',b'\n');locks.append({'path':rel,'checkout_sha256':sha(raw),'git_blob':subprocess.check_output(['git','-C',str(WT),'rev-parse','HEAD:'+rel],text=True).strip()})
check('All twelve existing locks unchanged',len(locks)==12)
original_docker=subprocess.check_output(['git','-C',str(WT),'show','HEAD:Dockerfile']).decode();check('Runtime installer path guard preserved',"scripts.is_dir() and not scripts.is_symlink() and scripts.resolve()==scripts" in docker and docker[docker.index('# Runtime does not install packages'):]==original_docker[original_docker.index('# Runtime does not install packages'):])
receipt={'verified_utc':datetime.now(timezone.utc).isoformat(),'checks':rows,'checks_passed':len(rows),'source_prepare_output':str(out),'source_preparation_sha256':sha((out/'source-preparation.json').read_bytes()),'builder_sha256':sha(build_source),'patch_sha256':sha(patch),'source_before_sha256':sha(original),'source_after_sha256':sha(fixed),'unchanged_locks':locks,'native_compilation_executed':False,'m1_preview_failure':{'script':str(LAB/'scripts/prepare_expat_sec10_refresh32.py'),'sha256':sha((LAB/'scripts/prepare_expat_sec10_refresh32.py').read_bytes()),'exception':'KeyError lib/xcsinc.c removed upstream2.9.0; preview not accepted','additional_integration_changes':'New property and 64-bit APIs and removed XML_ATTR_INFO need namespace/config/API review; M2 authorized instead.'},'scope':'Pure source preparation, hashes, immutable upstream hunk comparison, bounded negative canaries and Python compile only. No C/compiler execution, native import, QEMU/image build or product tests.'}
(OUT/'m2-static-verification.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({'checks':len(rows),'locks':len(locks),'source_after_sha256':sha(fixed),'builder_sha256':sha(build_source)},indent=2))
