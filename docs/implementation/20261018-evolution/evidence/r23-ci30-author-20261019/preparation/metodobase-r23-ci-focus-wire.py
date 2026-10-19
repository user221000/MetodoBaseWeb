"""Include the new focus regression and rebind final helper byte anchors."""
import ast,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(r'F:\mb-r23-history30-20261019');path=ROOT/'tests/verify_history_index_ci.py'
spec=importlib.util.spec_from_file_location('focus_wire_guard',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
minimums=dict(module.FOLLOWUP_VM_MINIMA);assert len(minimums)==4;minimums['dashboard_followup_focus']=4
step=dict(module.FOLLOWUP_VM_STEP)
step['run']=''.join('node tests/e2e/'+name+'.cjs > followup-contracts-'+name+'.raw.json\n'
    'python tests/e2e/normalize_followup_report.py followup-contracts-'+name+'.raw.json followup-contracts-'+name+'.json --kind counts --minimum '+str(minimum)+'\n'
    'python scripts/check_frontend_report.py followup-contracts-'+name+'.json --format counts --minimum '+str(minimum)+'\n' for name,minimum in minimums.items())
workflow=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf8')
before=''.join('          '+line+'\n' for line in module.FOLLOWUP_VM_STEP['run'].splitlines());after=''.join('          '+line+'\n' for line in step['run'].splitlines());assert workflow.count(before)==1;workflow=workflow.replace(before,after)
source=path.read_text(encoding='utf8');tree=ast.parse(source);edits=[]
values={'FOLLOWUP_VM_MINIMA':minimums,'FOLLOWUP_VM_STEP':step}
for node in tree.body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in values:
        name=node.targets[0].id;edits.append((node.lineno-1,node.end_lineno,name+' = '+repr(values[name])+'\n'))
lines=source.splitlines(keepends=True)
for start,end,text in sorted(edits,reverse=True):lines[start:end]=[text]
source=''.join(lines).replace("'current_VM_executions_in22': 344, 'additional_checks_no_dedup_claim': 44","'current_VM_executions_in23': 348, 'additional_checks_no_dedup_claim': 48")
tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED_CURRENT_GATES' for t in n.targets));pins=ast.literal_eval(node.value)
pins['tests/e2e/dashboard_followup_focus.cjs']='pending'
for name in pins:pins[name]=hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
lines=source.splitlines(keepends=True);lines[node.lineno-1:node.end_lineno]=['PINNED_CURRENT_GATES = '+repr(pins)+'\n'];source=''.join(lines);ast.parse(source)
path.write_bytes(source.encode());(ROOT/'.github/workflows/ci.yml').write_bytes(workflow.encode())
print(json.dumps({'VM_modules':23,'VM_execution_minima':348,'legacy18_unique_only':279,'additional_checks_no_dedup_claim':48,'PG_reports':29,'pinned_helpers':len(pins)}))
