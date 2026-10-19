"""Prepare a bounded CI29 workflow and immutable CI28 inputs."""
import hashlib
import json
from pathlib import Path
import subprocess
root=Path('F:/mb-r12-ci29-20261019')
pin='66d9dec0e15dd873038bd248d3883daeeb27d4ca'
old=subprocess.check_output(['git','show',pin+':.github/workflows/ci.yml'],cwd=root)
path=root/'.github/workflows/ci.yml'
assert path.read_bytes().replace(b'\r\n',b'\n')==old
snapshot=root/'tests/ci_member_links29';snapshot.mkdir(exist_ok=False)
(snapshot/'ci28-before.yml').write_bytes(old)
sha=lambda value:hashlib.sha256(value).hexdigest()
files=['tests/verify_history_landing_ci.py','tests/verify_recovery_ci.py','tests/verify_diary_ci.py',
       'scripts/check_frontend_report.py','scripts/check_browser_fixture_startup.py']
metadata={'commit':pin,'workflow_sha256':sha(old),'unchanged_files':{name:sha((root/name).read_bytes().replace(b'\r\n',b'\n')) for name in files}}
(snapshot/'baseline.json').write_bytes((json.dumps(metadata,indent=2)+'\n').encode())
text=old.decode('utf8')
old_guard='      - name: History and landing CI delta preserves reviewed CI28 and all acceptance gates\n        run: python -X utf8 tests/verify_history_landing_ci.py --output "$RUNNER_TEMP/history-landing-ci"\n'
new_guard='      - name: Member link CI29 preserves reviewed historical gates and requires current contracts\n        run: python -X utf8 tests/verify_member_links_ci.py --output "$RUNNER_TEMP/member-links-ci"\n'
assert text.count(old_guard)==1;text=text.replace(old_guard,new_guard)
start=text.index('  test-web:\n');stop=text.index('  frontend-contracts:\n')
block=text[start:stop];needle='      - uses: actions/checkout@v4\n'
assert block.count(needle)==1
text=text[:start]+block.replace(needle,needle+'        with:\n          fetch-depth: 0\n')+text[stop:]
start=text.index('  postgres:\n');stop=text.index('  redis:\n')
block=text[start:stop];assert block.count(needle)==1
block=block.replace(needle,needle+'        with:\n          fetch-depth: 0\n')
old_restore='        run: python -X utf8 tests/run_isolated.py tests/integration_backup_restore_postgres.py::test_encrypted_pg_restore_preserves_rows_constraints_and_private_objects tests/integration_recovery28_restore_review.py::test_revision28_restore_preserves_recovery_and_all_revision26_27_contracts -q --tb=short --junitxml=pytest-postgres-restore.xml'
new_restore='        run: python -X utf8 tests/run_reviewed_ci28.py --output "$RUNNER_TEMP/reviewed-ci28-restore" --junitxml=pytest-postgres-restore.xml'
assert block.count(old_restore)==1;block=block.replace(old_restore,new_restore)
steps=[
('Member link migration preserves exact revision28, guards and rollback','tests/integration_client_link_migrations.py','member-migrations'),
('Member link service authorization and bounded projection under restricted role','tests/integration_client_link_services.py','member-services'),
('Member link real HTTP and worker contracts across both factories','tests/integration_client_link_http.py','member-http'),
('Member proof races and exact publication identity CAS','tests/integration_client_link_service_races.py tests/integration_client_link_publication_cas.py','member-races'),
('Current revision29 populated restore preserves all prior contracts and member links','tests/integration_client_link_restore.py','member-restore')]
newsteps=''.join('      - name: '+title+'\n        run: python -X utf8 tests/run_isolated.py '+modules+(' -k postgresql' if suffix!='member-restore' else '')+' -q --tb=short --junitxml=pytest-postgres-'+suffix+'.xml\n' for title,modules,suffix in steps)
anchor='      - name: Required PostgreSQL acceptance cannot silently become skips or missing reports\n'
assert block.count(anchor)==1;block=block.replace(anchor,newsteps+anchor)
assert block.count("len(reports)==21 and len(set(reports))==21")==1
block=block.replace("len(reports)==21 and len(set(reports))==21, 'Expected 21 distinct PostgreSQL reports'","len(reports)==26 and len(set(reports))==26, 'Expected 26 distinct PostgreSQL reports'")
line='          pytest-postgres-recovery-migrations.xml pytest-postgres-recovery.xml\n'
assert block.count(line)==1
block=block.replace(line,line+'          '+' '.join('pytest-postgres-'+suffix+'.xml' for _,_,suffix in steps)+'\n')
text=text[:start]+block+text[stop:]
vm=[('member_link_context',26),('member_link_fragment',15),('member_link_api',23),('member_link_consumers',16),('member_link_export',32)]
vmstep='      - name: Member link API, context, fragment, consumers and seven-collection export contracts\n        run: |\n'+''.join('          node tests/e2e/'+name+'.cjs > '+name.replace('_','-')+'.json\n          python scripts/check_frontend_report.py '+name.replace('_','-')+'.json --format counts --minimum '+str(count)+'\n' for name,count in vm)
start=text.index('  frontend-contracts:\n');stop=text.index('  test-desktop:\n')
block=text[start:stop];anchor='      - uses: actions/upload-artifact@v4\n';assert block.count(anchor)==1
block=block.replace(anchor,vmstep+anchor)
line='            personal-history-contracts.json\n';assert block.count(line)==1
block=block.replace(line,line+'            member-link-*.json\n')
text=text[:start]+block+text[stop:]
needle='--tables 26 --revision 20261019_account_recovery';assert text.count(needle)==1
text=text.replace(needle,'--tables 29 --revision 20261019_client_account_links')
path.write_bytes(text.encode('utf8'))
print(json.dumps({'workflow_sha256':sha(old),'baseline_sha256':sha((snapshot/'baseline.json').read_bytes()),'new_PG_reports':5,'total_PG_reports':26,'VM_minima':vm,'historical_pin':pin}))
