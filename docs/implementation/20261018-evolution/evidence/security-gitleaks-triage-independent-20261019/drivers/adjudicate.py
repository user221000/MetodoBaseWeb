from pathlib import Path
from collections import Counter,defaultdict
import ast,hashlib,json,re,subprocess,zipfile
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp');PRIVATE=TEMP/'metodobase-sec-gitleaks-peer-private-20261019'
ROOT=Path(r'F:/mb-security-gitleaks-triage-peer-20261019');SOURCE=Path(r'F:/mb-progress-retirement-ui-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-gitleaks-triage-independent-20261019'
FOCAL=PRIVATE/'focal-snapshot';sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT,stderr=subprocess.DEVNULL)
report=json.loads((TEMP/'metodobase-retirement-ui-scan-7c_07ul3/secret-scan-full.json').read_bytes())
rows=json.loads((TEMP/'metodobase-gitleaks-historical-evidence-triage-20261019/unclassified-locations.json').read_bytes())
raw=json.loads((PRIVATE/'focal-redacted.json').read_bytes());wanted=Counter((r['file'],r['line'],r['rule']) for r in rows)
initial=json.loads((OUT/'attempt-initial/source-before.json').read_bytes());assert initial['scanned_files']==report['files']
tracked=set(git('ls-tree','-r','--name-only','-z','de216543a2eec05584168cdb888f627901b0e0b1').decode().split('\0')[:-1])
public_hashes=defaultdict(list)
for name,digest in report['files'].items():
    if name in tracked:public_hashes[digest].append(name)
known={};objects={};locations=[];unknown=[];hex_values=Counter();cache={};verified_pool={}
verified=json.loads((OUT/'independent-verified-checksum-locations.json').read_bytes())
assert len(verified)==31282
verified_hashes={v['checksum_sha256']:v for v in verified}
for phase in ['metodobase-gitleaks-fingerprint-triage-20261019','metodobase-gitleaks-historical-fingerprint-triage-20261019','metodobase-gitleaks-public-artifact-triage-20261019','metodobase-gitleaks-historical-evidence-triage-20261019']:
    for row in json.loads((TEMP/phase/'classified.json').read_bytes()):
        digest=row.get('source_sha256') or row.get('sha256') or row.get('checksum')
        assert sha(digest.encode()) in verified_hashes
        verified_pool[digest]=verified_hashes[sha(digest.encode())]
def actual_public_file(value):
    if value not in public_hashes:return None
    for name in public_hashes[value]:
        if name not in cache:cache[name]=sha((SOURCE/name).read_bytes())
        if cache[name]==value:return {'kind':'exact_frozen_public_file_SHA256','path':name,'sha256':value}
    return None
for item in raw:
    name=Path(item['File']).relative_to(FOCAL).as_posix() if Path(item['File']).is_absolute() else item['File']
    identity=(name,item['StartLine'],item['RuleID'])
    if identity not in wanted:continue
    text=(FOCAL/name).read_bytes().decode('utf8');line=text.split('\n')[item['StartLine']-1]
    span=line[item['StartColumn']-1:item['EndColumn']]
    redacted=item['Match'];assert redacted.count('REDACTED')==1
    prefix,suffix=redacted.split('REDACTED')
    byte_span=line.encode()[item['StartColumn']-1:item['EndColumn']].decode('utf8',errors='replace')
    candidates=[(span,'character_columns'),(byte_span,'UTF8_byte_columns'),
        (line[max(0,item['StartColumn']-2):item['EndColumn']-1],'character_columns_minus_one'),
        (line.encode()[max(0,item['StartColumn']-2):item['EndColumn']-1].decode('utf8',errors='replace'),'UTF8_byte_columns_minus_one')]
    exact=[(candidate,method) for candidate,method in candidates if candidate.startswith(prefix) and (not suffix or candidate.endswith(suffix))]
    if not exact:
        rec={'file':name,'line':item['StartLine'],'rule':item['RuleID'],'file_sha256':report['files'][name],'columns':[item['StartColumn'],item['EndColumn']],
            'value_type':'unmapped_span','matched_field_structure':'not_reconstructed','proof':None,'reason':'No exact prefix/suffix reconstruction from redacted match at reported character or UTF8-byte columns; do not classify a partial fragment.'}
        unknown.append(rec);locations.append(rec);continue
    def original(candidate):return candidate[len(prefix):len(candidate)-len(suffix) if suffix else None]
    preferred=[pair for pair in exact if re.fullmatch('[a-fA-F0-9]{40}|[a-f0-9]{64}',original(pair[0]))]
    if preferred:exact=preferred
    span,mapping=exact[0]
    value=span[len(prefix):len(span)-len(suffix) if suffix else None]
    assert value and len(value)==len(span)-len(prefix)-len(suffix)
    field=prefix.strip().strip('\"\' :=').strip()
    rec={'file':name,'line':item['StartLine'],'rule':item['RuleID'],'file_sha256':report['files'][name],
        'columns':[item['StartColumn'],item['EndColumn']],'physical_line_sha256':sha(line.encode()),'matched_value_sha256':sha(value.encode()),'matched_value_bytes':len(value.encode()),'matched_field_structure':field,'column_mapping':mapping,'proof':None}
    if re.fullmatch('[a-f0-9]{64}',value):
        rec['value_type']='hex64';hex_values[64]+=1
        rec['proof']=actual_public_file(value)
        if rec['proof'] is None and value in verified_pool:
            old=verified_pool[value]
            rec['proof']={'kind':'checksum_previously_independently_verified','proof_type':old['proof_type'],'source_path':old.get('source_path'),'Git_blob_oid':old.get('Git_blob_oid'),'derivation':old.get('derivation'),'artifact':old.get('artifact')}
    elif re.fullmatch('[a-fA-F0-9]{40}',value):
        rec['value_type']='hex40';hex_values[40]+=1
        if value not in objects:
            try:kind=git('cat-file','-t',value).decode().strip()
            except subprocess.CalledProcessError:kind=None
            objects[value]=kind
        if objects[value] in {'commit','blob','tree','tag'}:rec['proof']={'kind':'existing_public_Git_object_identifier','object_type':objects[value],'oid':value}
    else:
        rec['value_type']='other'
        try:
            tree=ast.parse(text);nodes=[n for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value==value]
            parents={child:parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
            context=[]
            for n in nodes:
                if n.lineno!=item['StartLine']:continue
                p=parents.get(n);chain=[]
                for depth in range(4):
                    if p is None:break
                    if isinstance(p,ast.keyword):chain.append({'kind':'keyword','name':p.arg})
                    elif isinstance(p,ast.Call):chain.append({'kind':'call','callee':ast.unparse(p.func)})
                    elif isinstance(p,ast.FunctionDef):chain.append({'kind':'function','name':p.name})
                    else:chain.append({'kind':type(p).__name__})
                    p=parents.get(p)
                context.append(chain)
            rec['ast_literal_context']=context
        except Exception:pass
    if rec['proof']:known[identity+(tuple(rec['columns']),)]=rec
    else:unknown.append(rec)
    locations.append(rec)
assert len(locations)==282
(PRIVATE/'adjudication-v3.STRUCTURAL.json').write_text(json.dumps(locations,indent=2)+'\n',encoding='utf8')
(PRIVATE/'unresolved-v3.STRUCTURAL.json').write_text(json.dumps(unknown,indent=2)+'\n',encoding='utf8')
print(json.dumps({'reviewed':len(locations),'verified_current_or_Git_OID':len(known),'unresolved':len(unknown),'hex_value_lengths':hex_values,'unresolved_fields':Counter((r['value_type']+':'+r['matched_field_structure']) for r in unknown),'nonhex_contexts':[r for r in unknown if r['value_type']=='other']},indent=2))
