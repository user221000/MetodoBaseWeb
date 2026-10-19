"""Keep case identities and untouched criteria accountable across the owned fix."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
RED = OUT.parent / 'qa-integrated28-history-landing-20261019'
PREFIX = 'qa-integrated28-history-landing'

def load(root, name):
    return json.loads((root / name).read_text(encoding='utf8'))

def cases(path):
    result = {}
    for case in ET.parse(path).getroot().findall('.//testcase'):
        node = case.attrib.get('classname', '') + '::' + case.attrib['name']
        assert node not in result
        result[node] = [tag for tag in ('skipped', 'failure', 'error') if case.find(tag) is not None]
    return result

original_manifest = load(RED, 'serial-red-manifest.json')
assert all(hashlib.sha256((RED / name).read_bytes()).hexdigest() == digest
           for name, digest in original_manifest['files'].items())
old = load(RED, 'before-serial-source.json')
new = load(OUT, 'before-serial-source.json')
assert set(old['sources']) == set(new['sources'])
changed = {name: {'before': digest, 'after': new['sources'][name]}
           for name, digest in old['sources'].items() if digest != new['sources'][name]}
assert set(changed) == {'tests/test_landing_commercial.py'}
assert old['packages'] == new['packages'] and old['package_count'] == new['package_count'] == 89
original = cases(RED / (PREFIX + '-serial.xml'))
serial = cases(OUT / (PREFIX + '-postfix-serial.xml'))
shuffle = cases(OUT / (PREFIX + '-postfix-shuffle.xml'))
assert set(original) == set(serial) == set(shuffle)
assert serial == shuffle
differences = {node: {'original': outcome, 'postfix': serial[node]}
               for node, outcome in original.items() if outcome != serial[node]}
expected = {
    'tests.test_landing_commercial::test_public_view_never_reads_credentials_fetches_private_data_or_writes[web.main_web]',
    'tests.test_landing_commercial::test_public_view_never_reads_credentials_fetches_private_data_or_writes[api.app]',
}
assert set(differences) == expected
assert all(row == {'original': ['failure'], 'postfix': []} for row in differences.values())
summary = {
    'original_red_preserved': True, 'original_red_files_verified': len(original_manifest['files']),
    'changed_sources': changed, 'installed_packages_identical': True, 'package_count': 89,
    'collected_nodeids_identical_across_original_serial_postfix_serial_and_shuffle': True,
    'collected': len(original), 'only_outcome_changes': differences,
    'every_other_original_case_outcome_unchanged': True,
    'skip_outcomes_identical': {node: outcome for node, outcome in original.items() if outcome == ['skipped']},
    'scope': 'These original failures remain failures in their immutable report. The new outcome belongs only to the coordinator-owned corrected test on the new HEAD. No runtime code changed between the two freezes.',
}
with (OUT / 'red-to-postfix-review.json').open('x', encoding='utf8', newline='\n') as stream:
    json.dump(summary, stream, ensure_ascii=False, indent=2); stream.write('\n')
print(json.dumps(summary, ensure_ascii=False))
