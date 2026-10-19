from pathlib import Path
import hashlib,json,re
p=Path(r'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence\qa-r24-independent-20261019\r24-sqlite-SSR--api-app-attrs-text.json')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-checkpoint115-refusal-20261019');out.mkdir(exist_ok=False)
findings=[]
def walk(value,path):
    if isinstance(value,dict):
        for key,item in value.items():walk(item,path+[key])
    elif isinstance(value,list):
        for index,item in enumerate(value):walk(item,path+[index])
    elif isinstance(value,str):
        raw=value.encode()
        for m in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',raw):
            start=m.start()
            if start>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',raw[start-30:start]):
                findings.append({'JSON_path':path,'string_bytes':len(raw),'suffix_offset':start,'suffix_bytes':65,'value_or_surroundings_emitted':False})
walk(json.loads(p.read_bytes()),[])
receipt={'refused_file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'findings':findings,'effect':'Stopped before copying proof to wave115, changing ledger or staging any files; no raw matching value emitted. QA advised. File remains untracked in owned execution clone pending private review; immutable manifest not rewritten.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps(receipt))
