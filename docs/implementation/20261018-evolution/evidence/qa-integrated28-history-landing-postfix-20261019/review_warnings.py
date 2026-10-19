"""Read-only classification of warning messages across the preserved reports."""
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
RED = OUT.parent / 'qa-integrated28-history-landing-20261019'
paths = {
    'original_red_serial': RED / 'qa-integrated28-history-landing-serial.log',
    'postfix_serial': OUT / 'qa-integrated28-history-landing-postfix-serial.log',
    'postfix_n2_shuffle': OUT / 'qa-integrated28-history-landing-postfix-shuffle.log',
}
results = {}
for label, path in paths.items():
    text = path.read_text(encoding='utf8')
    messages = sorted(set((match.group('kind'), match.group('text'))
                          for line in text.splitlines()
                          if (match := re.search(r'(?P<kind>\w+Warning): (?P<text>.*)$', line))))
    count = re.search(r'(\d+) warnings?', text.strip().splitlines()[-1])
    assert count is not None
    results[label] = {'warning_count': int(count.group(1)), 'unique_class_and_messages': messages}
baseline = results['original_red_serial']['unique_class_and_messages']
assert len(baseline) == 6
assert all(value['unique_class_and_messages'] == baseline for value in results.values())
proof = {
    'reports': results, 'unique_class_and_messages_identical': True,
    'review': 'Six unchanged warning messages: existing GestorBDClientes deprecation, Starlette/httpx deprecation, Sentry propagate_traces deprecation, and three standalone API duplicate operationId warnings. The two additional n2 occurrences are worker import duplicates of the first two warnings; no new warning class or message appeared.',
}
with (OUT / 'warning-review.json').open('x', encoding='utf8', newline='\n') as stream:
    json.dump(proof, stream, ensure_ascii=False, indent=2); stream.write('\n')
print(json.dumps({'unique_messages_identical': True, 'counts': {name: value['warning_count'] for name, value in results.items()}}))
