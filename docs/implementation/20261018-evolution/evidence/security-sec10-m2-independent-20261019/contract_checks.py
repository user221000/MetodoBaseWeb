from pathlib import Path
import ast,hashlib,json,re
HERE=Path(__file__).parent;ROOT=Path('F:/mb-expat-m2-sec');CODE=ROOT/'runtime-source/expat-sec10'
PROOF=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/linux-expat-sec10-m2-prepared-20261019')
SOURCE=HERE/'pure-v2/prepared-positive/source';rows=[]
def check(name,condition):
    assert condition,name;rows.append({'name':name,'passed':True})
lock=json.loads((CODE/'source-pins.json').read_bytes())
keys={'python_version','base_image','psf_source_url','psf_source_sha256','upstream_fix_commit','cve','embedded_version_unchanged','source_relative_path','source_before_sha256','source_after_sha256','patch_sha256','expected_ext_suffix','expected_soabi','source_date_epoch','runtime_metadata_expected_distributions'}
check('Pinned metadata schema and critical provenance values agree',set(lock)==keys and type(lock['source_date_epoch']) is int and lock['source_date_epoch']==1790807318 and type(lock['runtime_metadata_expected_distributions']) is int and lock['runtime_metadata_expected_distributions']==54 and lock['python_version']=='3.12.15' and lock['embedded_version_unchanged']=='2.8.5')
cna=json.loads((PROOF/'reused-primary/CVE-2026-77214.json').read_bytes())
versions=[v for a in cna['containers']['cna']['affected'] for v in a['versions']]
check('Primary CNA range/fixed commit agrees with patch and preserved version',cna['cveMetadata']['cveId']==lock['cve'] and any(v.get('lessThanOrEqual')=='2.8.5' and v['status']=='affected' for v in versions) and any(v.get('version')==lock['upstream_fix_commit'] and v['status']=='unaffected' for v in versions))
et=(SOURCE/'Modules/_elementtree.c').read_text(encoding='utf8')
check('ElementTree capsule validates magic minimum size and all three version fields',all(s in et for s in ['strcmp(st->expat_capi->magic, PyExpat_CAPI_MAGIC)','(size_t)st->expat_capi->size < sizeof(struct PyExpat_CAPI)','st->expat_capi->MAJOR_VERSION != XML_MAJOR_VERSION','st->expat_capi->MINOR_VERSION != XML_MINOR_VERSION','st->expat_capi->MICRO_VERSION != XML_MICRO_VERSION']))
ns=(SOURCE/'Modules/expat/pyexpatns.h').read_text(encoding='utf8');external=(SOURCE/'Modules/expat/expat_external.h').read_text(encoding='utf8');config=(SOURCE/'Modules/expat/expat_config.h').read_text(encoding='utf8')
check('Namespace and Expat feature config are retained rather than replaced with a new release', '#include "pyexpatns.h"' in external and re.search(r'#define\s+XML_ParseBuffer\s+PyExpat_XML_ParseBuffer',ns) is not None and all(s in config for s in ['#define XML_NS 1','#define XML_DTD 1','#define XML_CONTEXT_BYTES 1024']))
code=(CODE/'rebuild_pyexpat.py').read_text(encoding='utf8');tree=ast.parse(code)
run=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess' and n.func.attr=='run')
check('Native smoke argv is isolated no-site and no shell invocation',isinstance(run.args[0],ast.List) and [ast.literal_eval(n) for n in run.args[0].elts[1:4]]==['-I','-S','-c'] and not any(k.arg=='shell' for k in run.keywords))
docker=(ROOT/'Dockerfile').read_text(encoding='utf8')
check('Same pinned base and runtime54 contract; no added installer/build tools copied',lock['base_image'] in docker and len([l for l in docker.splitlines() if l.startswith('COPY --from=expat-build')])==2 and 'COPY --from=expat-build /opt/' not in docker and 'COPY --from=expat-build /usr/local/bin' not in docker)
out=HERE/'contract-results.json';assert not out.exists();out.write_text(json.dumps({'scope':'Pinned valid candidate schema and static source/AST contract; not a promise to validate arbitrary future lock metadata','total':len(rows),'passed':len(rows),'results':rows},indent=2)+'\n',encoding='utf8');print(json.dumps({'total':len(rows),'passed':len(rows)}))
