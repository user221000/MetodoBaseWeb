"""Run the full maintained CI delta verifier and only the new Node23 contract."""
import json
from qa_support import *

before = photo('maintained-before')
result = run([str(PYTHON),'-X','utf8','tests/verify_history_landing_ci.py',
              '--output',str(OUT/'full-verifier')], 'maintained-full-verifier', timeout=240)
after = photo('maintained-after')
assert before == after
assert result.returncode == 0, 'Preserve full verifier original log before diagnosis'
report = json.loads((OUT/'full-verifier/review.json').read_text(encoding='utf8'))
assert len(report['unauthorized_delta_canaries']) == 13
assert len(report['new_inert_fixture_cases']) == 16
assert report['bash_blocks'] == 65 and len(report['references']) == 90
historical = json.loads((OUT/'full-verifier/historical-ci28/review.json').read_text(encoding='utf8'))
assert len(historical['reports']) == 21
assert historical['actual_fixture_marker'] == {'fixture':'personal-diary-ui','model_target_revision':'20261019_account_recovery','tables':26}
before_node = photo('node23-before')
node = subprocess.run(['node','tests/e2e/personal_history.cjs'],cwd=ROOT,env=environment(),capture_output=True,encoding='utf8',timeout=45)
with (OUT/'node23.json').open('x',encoding='utf8',newline='\n') as stream:
    stream.write(node.stdout)
with (OUT/'node23.stderr.log').open('x',encoding='utf8',newline='\n') as stream:
    stream.write(node.stderr)
assert node.returncode == 0
guard = run([str(PYTHON),'scripts/check_frontend_report.py',str(OUT/'node23.json'),
             '--format','counts','--minimum','23'], 'node23-guard')
after_node = photo('node23-after')
assert before_node == after_node == before
assert guard.returncode == 0
save(OUT/'maintained-summary.json', {'head':HEAD,'accepted':True,'sources':len(before['sources']),
    'packages':89,'readonly_node_dependencies':146,'all_four_photos_identical':True,
    'delta_cases':13,'inert_cases':16,'bash_blocks':65,'references':90,'node23_exit':0,
    'preserved_pg_report_count':21,'historical_ci28_marker':historical['actual_fixture_marker'],
    'scope':'Full maintained verifier and new Node23 only; no old162VM, browser, PostgreSQL, backend, image or Actions execution.'})
print(json.dumps({'accepted':True,'sources':len(before['sources']),'packages':89,'delta':13,'inert':16,'node':23}))
