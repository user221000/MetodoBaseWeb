"""Only authenticated fixture metadata constants adapt preserved51+27 criteria."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

MAIN=Path(r'F:/MetodoBaseWeb-execution-20261018')
EVI=MAIN/'docs/implementation/20261018-evolution/evidence'
OUT=Path(__file__).resolve().parent
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-desktop31215-independent-20261019')
ROOT=Path(r'F:/mb-d31215-20261019')
AUTHOR=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-desktop31215-build66-20261019')
OLD=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-desktop-artifact27-independent-c22is1va')
HEAD='66d9dec0e15dd873038bd248d3883daeeb27d4ca'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def save(name,value):
    with (OUT/name).open('x',encoding='utf8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

receipt=json.loads((AUTHOR/'inno/summary.json').read_text(encoding='utf8'))
inventories=json.loads((AUTHOR/'inno/inventories-private.json').read_text(encoding='utf8'))
assert receipt['source_commit']==HEAD and receipt['exit']==0
for section in ['bundle','inputs','tools']:
    assert inventories[section+'_before']==inventories[section+'_after']
assert sha(canonical(inventories['tools_before']))==receipt['tool_inventory_sha256']
assert len(inventories['tools_before'])==receipt['tool_files']==119
normalized=deepcopy(receipt)
for entry in normalized['outputs']:
    assert 'file' not in entry
    entry['file']=entry['path']
normalized['tools']=inventories['tools_before']
normalized_path=TEMP/'inno-author-authenticated-compatibility-view.json'
normalized_path.write_text(json.dumps(normalized,indent=2)+'\n',encoding='utf8')
save('inno-receipt-view-provenance.json',{'raw_receipt_sha256':sha((AUTHOR/'inno/summary.json').read_bytes()),
     'raw_inventories_sha256':sha((AUTHOR/'inno/inventories-private.json').read_bytes()),
     'normalized_receipt_sha256':sha(normalized_path.read_bytes()),
     'tool_inventory_authentication':'Exact before/after tool dictionary equality and canonical SHA equals frozen receipt aggregate,119 entries.',
     'mapping':{'outputs.file':'Exact unchanged outputs.path value','tools':'Authenticated inventories.tools_before'},
     'criteria_changed':False})
for name in ['desktop-artifact27-independent-extractor-provenance.json','desktop-artifact27-independent-extractor-signature.json']:
    shutil.copyfile(EVI/name,TEMP/name)
shutil.copyfile(OLD/'innounp-2.67.11-pinned.zip',TEMP/'innounp-2.67.11-pinned.zip')
(TEMP/'extractor').mkdir()
shutil.copyfile(OLD/'extractor/innounp.exe',TEMP/'extractor/innounp.exe')
assert sha((TEMP/'extractor/innounp.exe').read_bytes())=='1c8453c198dd3fe7947f3705e59d2294ddce3dfa9f96a737e94449b119f44181'
assert sha((TEMP/'innounp-2.67.11-pinned.zip').read_bytes())=='851772538a041229102ad9964542d49dc00c74002e3091a70469c079ae368f52'

def assignment_value(tree,name):
    node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
    if isinstance(node.value,ast.Call):return ast.literal_eval(node.value.args[0])
    return ast.literal_eval(node.value)

def adapt(kind,source,mapping):
    original=source.read_bytes()
    (OUT/(kind+'-historical-original.txt')).write_bytes(original)
    text=original.decode('utf8');before=ast.parse(text)
    lines=text.splitlines(keepends=True);offsets=[];offset=0
    for line in lines:offsets.append(offset);offset+=len(line)
    replacements=[];deltas=[]
    for node in ast.walk(before):
        if not isinstance(node,ast.Constant):continue
        key=(type(node.value).__name__,node.value)
        if key not in mapping:continue
        replacement=mapping[key]
        start=offsets[node.lineno-1]+node.col_offset
        end=offsets[node.end_lineno-1]+node.end_col_offset
        replacements.append((start,end,repr(replacement)))
        deltas.append({'line':node.lineno,'old':node.value,'new':replacement})
    assert {(type(d['old']).__name__,d['old']) for d in deltas}==set(mapping)
    adapted=text
    for start,end,replacement in sorted(replacements,reverse=True):adapted=adapted[:start]+replacement+adapted[end:]
    after=ast.parse(adapted)
    expected=deepcopy(before)
    for node in ast.walk(expected):
        if isinstance(node,ast.Constant) and (type(node.value).__name__,node.value) in mapping:
            node.value=mapping[(type(node.value).__name__,node.value)]
    assert ast.dump(expected,include_attributes=False)==ast.dump(after,include_attributes=False)
    old_checks=[n.args[0].value for n in ast.walk(before) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='check' and isinstance(n.args[0],ast.Constant)]
    new_checks=[n.args[0].value for n in ast.walk(after) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='check' and isinstance(n.args[0],ast.Constant)]
    assert old_checks==new_checks
    target=OUT/(kind+'-adapted.py');target.write_text(adapted,encoding='utf8',newline='\n')
    return {'historical_raw_sha256':sha(original),'adapted_sha256':sha(target.read_bytes()),
            'only_AST_changes':deltas,'all_other_AST_exact':True,'check_calls_same_order':True}

proof={}
for kind,name in [('bundle51','desktop-artifact27-independent-review-script.txt'),('installer27','desktop-artifact27-independent-installer-review-script.txt')]:
    path=EVI/name;tree=ast.parse(path.read_text(encoding='utf8'))
    mapping={('str',assignment_value(tree,'ROOT')):str(ROOT),('str',assignment_value(tree,'OUT')):str(TEMP),
             ('str',assignment_value(tree,'COMMIT')):HEAD,
             ('str',assignment_value(tree,'EXPECTED_ZIP')):'4966896c41e53b1b5df443045a0175626571a4bfd98731e200bcd299353ed353'}
    if kind=='bundle51':
        mapping.update({('int',2595):4433,('int',122492985):122441614})
    else:
        mapping.update({('str',assignment_value(tree,'RECEIPT')):str(normalized_path),
          ('str',assignment_value(tree,'SETUP')):str(AUTHOR/'inno/compiled/MetodoBaseSetup_v2.0.0.exe'),
          ('int',89965414):89973261,
          ('str','25ed92b1a29b0675a1eecc15dc10a4432ed1046fb7734631ec828164f055d06d'):'5651f4189b7640edced7986db007a4a63f54ba00801658f31fa789587d219363'})
    proof[kind]=adapt(kind,path,mapping)
save('historical-criteria-adaptation.json',proof)
print(json.dumps({kind:details['adapted_sha256'] for kind,details in proof.items()}))
