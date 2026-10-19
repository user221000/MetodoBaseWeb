"""Preserve the pre-existing unconfirmed empty-ack contract as an actual red."""
from pathlib import Path
import json
root=Path(__file__).parent
record=json.loads((root/'record.json').read_text('utf8'))
results=record['separate_preexisting_unconfirmed_ack_observations']
summary={'scope':'Separate R16 pre-existing negative; not a regression of sender-key patch or real provider response',
    'total':len(results),'passed':sum(row['security_assertion_passed'] for row in results),
    'results':results}
summary['exit_code']=0 if summary['passed']==summary['total'] else 1
target=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/email-sdk-wire-independent-ack-negative.json')
target.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
print(json.dumps({'total':summary['total'],'passed':summary['passed'],'exit_code':summary['exit_code'],'both_sources_return_true_without_id':all(row['actual_confirmed'] for row in results)}))
raise SystemExit(summary['exit_code'])
