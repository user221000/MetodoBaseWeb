"""Execute exact23 VM commands and actual normalizers/parsers from frozen workflow."""
from support import *
import shlex,yaml
NODE=Path('C:/Program Files/nodejs/node.exe');before=photo('node-before');phase=TEMP/'node';phase.mkdir(exist_ok=False)
node_sha=sha(NODE.read_bytes());assert node_sha=='ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32'
workflow=yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_bytes());rows=[];node_count=0;normalizers=0;parsers=0
for step in workflow['jobs']['frontend-contracts']['steps']:
    for line in step.get('run','').splitlines():
        if not line.startswith(('node tests/e2e/','python scripts/check_frontend_report.py ','python tests/e2e/normalize_followup_report.py ')):continue
        parts=shlex.split(line);output=None
        if parts[0]=='node':
            assert parts.count('>')==1;i=parts.index('>');assert i==len(parts)-2;output=phase/parts[-1];parts=parts[:i];parts[0]=str(NODE);node_count+=1
        else:
            parts[0]=str(PYTHON)
            if 'normalize_followup_report.py' in line:normalizers+=1
            else:parsers+=1
        for i,arg in enumerate(parts[1:],1):
            if arg.startswith(('tests/','scripts/','web/')):parts[i]=str(ROOT/arg)
        result=subprocess.run(parts,cwd=phase,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',SESSION_EVENT_REVIEW_ROOT=str(ROOT)),capture_output=True,timeout=45)
        index=len(rows)
        if output is not None:
            with output.open('xb') as stream:stream.write(result.stdout)
        else:(phase/('command-'+str(index)+'.stdout.log')).write_bytes(result.stdout)
        (phase/('command-'+str(index)+'.stderr.log')).write_bytes(result.stderr)
        rows.append({'workflow_line':line,'exit':result.returncode,'node':output is not None});assert result.returncode==0,line
assert node_count==parsers==23 and normalizers==5
after=photo('node-after');assert before==after and sha(NODE.read_bytes())==node_sha
outputs=[publish(p,'node-'+p.name) for p in sorted(phase.iterdir()) if p.is_file()]
save('node-result.json',{'head':HEAD,'VM_modules':node_count,'shared_parsers':parsers,'actual_normalizers':normalizers,'minimum_assertion_executions':348,'legacy_executions':300,'legacy_unique_criteria':279,'additional_executions_no_dedup_claim':48,'commands':rows,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'node_sha256':node_sha,'stable':True,'outputs':outputs,'scope':'Actual local23 Node VM/controlled-DOM commands plus actual parsers/normalizers. No browser/layout/backend/provider claim.'})
print(json.dumps({'VM':node_count,'parsers':parsers,'normalizers':normalizers,'minimum_executions':348,'sources':before['source_count'],'packages':89,'stable':True}))
