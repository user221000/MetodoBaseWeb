"""Repair the two independently reproduced CI1 trust bypasses in an isolated WT."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(r'F:\mb-ci29-trust-fix-20261019')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='ce1afda202fd27a3433ba8247d374d8e496cb5b0'
path=root/'tests/verify_member_links_ci.py';before=path.read_bytes();source=before.decode().replace('\r\n','\n')
pins={name:hashlib.sha256((root/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for name in ['tests/check_member_link_reports.py','tests/run_reviewed_ci28.py']}
anchor="REVISION = '20261019_client_account_links'"
assert source.count(anchor)==1
insertion='PINNED_CURRENT_GATES = '+repr(pins)+'\n'+'''EXPECTED_CURRENT_REPORTS = {
    'pytest-postgres-member-migrations.xml': (5, ('tests.integration_client_link_migrations',)),
    'pytest-postgres-member-services.xml': (16, ('tests.integration_client_link_services',)),
    'pytest-postgres-member-http.xml': (34, ('tests.integration_client_link_http',)),
    'pytest-postgres-member-races.xml': (4, ('tests.integration_client_link_service_races',
                                            'tests.integration_client_link_publication_cas')),
    'pytest-postgres-member-restore.xml': (1, ('tests.integration_client_link_restore',)),
}
'''
source=source.replace(anchor,insertion+anchor)
anchor='def baseline() -> dict:\n'
assert source.count(anchor)==1
source=source.replace(anchor,'''def authenticate_current_gates() -> None:
    # Independent literals bind executable helpers before they are imported/run.
    for name, digest in PINNED_CURRENT_GATES.items():
        assert hashlib.sha256(normalized(ROOT / name)).hexdigest() == digest, name


def baseline() -> dict:
    authenticate_current_gates()
''')
anchor='    from tests.check_member_link_reports import REPORTS\n    rows = []'
assert source.count(anchor)==1
source=source.replace(anchor,'''    authenticate_current_gates()
    from tests.check_member_link_reports import REPORTS
    assert REPORTS == EXPECTED_CURRENT_REPORTS and len(REPORTS) == 5
    rows = []''')
anchor='    return rows\n\n\ndef inert_cases'
assert source.count(anchor)==1
source=source.replace(anchor,"    assert len(rows) == 55, 'Current report probes were reduced'\n"+anchor)
path.write_bytes(source.encode())
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci29-trust-preparation-20261019.json');assert not out.exists()
out.write_text(json.dumps({'base':'ce1afda202fd27a3433ba8247d374d8e496cb5b0','pins':pins,'before_sha256':hashlib.sha256(before).hexdigest(),'after_LF_sha256':hashlib.sha256(source.encode()).hexdigest(),'existing_criteria_preserved':True},indent=2)+'\n',encoding='utf8')
print(json.dumps({'pins':pins,'prepared':True}))
