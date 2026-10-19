"""Build a new gate runner from the accepted27 orchestration without editing it."""
from pathlib import Path

OUT = Path(__file__).resolve().parent
OLD = OUT.parent / 'qa-integrated27-final-20261019/review_integrated27.py'
source = OLD.read_text(encoding='utf8')
source = source.replace('integrated revision27 candidate', 'integrated revision28/history/landing candidate')
source = source.replace('qa-integrated27-final', 'qa-integrated28-history-landing')
source = source.replace('metodobase-test-qa-integrated27-', 'metodobase-test-qa-integrated28-')
source = source.replace('7bde30b1877f3b4471ef5a75c47839ceaec209a9', 'dd9877350aad3f483299c990a1e97aab63c83f5d')
source = source.replace('HEAD7bde30b', 'HEADdd98773')
source = source.replace('"api", "core", "web"', '".github", "api", "core", "web"')
needle = '"METODOBASE_TEST_MIGRATOR_URL", "METODOBASE_TEST_POSTGRES_URL", "METODOBASE_TEST_PG_BIN"):'
assert source.count(needle) == 1
source = source.replace(needle, '"METODOBASE_TEST_MIGRATOR_URL", "METODOBASE_TEST_POSTGRES_URL", "METODOBASE_TEST_PG_BIN", "METODOBASE_HISTORY_EXPLAIN_OUTPUT"):')
needle = '''        assert len(counts["skipped"]) == 1 and counts["skipped"][0]["node"] == KNOWN_SKIP
        assert "Host does not grant symlink creation" in counts["skipped"][0]["message"]'''
assert source.count(needle) == 1
source = source.replace(needle, '''        assert len(counts["skipped"]) <= 1
        assert all(row["node"] == KNOWN_SKIP and "Host does not grant symlink creation" in row["message"] for row in counts["skipped"])''')
needle = '''    assert runs[0]["junit"]["passed"] == runs[1]["junit"]["passed"]
    accepted = True'''
assert source.count(needle) == 1
source = source.replace(needle, '''    assert runs[0]["junit"]["passed"] == runs[1]["junit"]["passed"]
    def outcomes(path):
        cases = ET.parse(path).getroot().findall('.//testcase')
        result = {}
        for case in cases:
            node = case.attrib.get('classname', '') + '::' + case.attrib['name']
            assert node not in result, 'Duplicate JUnit node: ' + node
            tags = tuple(tag for tag in ('skipped', 'failure', 'error') if case.find(tag) is not None)
            result[node] = tags
        return result
    serial_outcomes = outcomes(OUT / 'qa-integrated28-history-landing-serial.xml')
    shuffle_outcomes = outcomes(OUT / 'qa-integrated28-history-landing-shuffle.xml')
    assert serial_outcomes == shuffle_outcomes, 'Collected case identities/outcomes differ between serial and shuffled runs'
    save('case-outcomes.json', {'identical': True, 'cases': serial_outcomes})
    accepted = True''')
source = source.replace('"historical_1813_evidence": "preserved; no earlier evidence files used as output"',
                        '"all_prior_acceptance_evidence": "preserved; no earlier case totals reused or summed"')
target = OUT / 'review_integrated28.py'
with target.open('x', encoding='utf8', newline='\n') as stream:
    stream.write(source)
print(str(target))
