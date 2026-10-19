"""Place the exact candidate steps in image, preserving the failed YAML."""
from pathlib import Path
import importlib.util,json,yaml
ROOT=Path(r'F:\mb-r23-history30-20261019');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp');path=ROOT/'tests/verify_history_index_ci.py'
spec=importlib.util.spec_from_file_location('finish_guard',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=(TEMP/'metodobase-r23-ci-workflow-recover.py').read_text(encoding='utf8')
scope={};exec(compile(source[:source.index('rows=differences')],'recover-definitions','exec'),scope)
candidate=scope['candidate'];text=scope['scope']['text'];assert candidate.endswith(text)
candidate=candidate[:-len(text)];needle='  ci-success:\n';assert candidate.count(needle)==1
candidate=candidate.replace(needle,text+needle)
assert yaml.safe_load(candidate)==module.expected_workflow(module.baseline())
(ROOT/'.github/workflows/ci.yml').write_bytes(candidate.encode())
guard=path.read_text(encoding='utf8');assert guard.count("'len(reports)==28', 'len(reports)==27'")==1
guard=guard.replace("'len(reports)==28', 'len(reports)==27'","'len(reports)==29', 'len(reports)==28'")
guard=guard.replace("'current_index_PG_exact_cases': 9,","'current_index_PG_exact_cases': 9, 'current_followup_PG_exact_cases': 2,")
path.write_bytes(guard.encode())
print(json.dumps({'failed_candidate_preserved':True,'image_job_steps_appended':2,'ci_success_unchanged':True,'PG_reports':29,'old_report_count_mutant_updated_for_current29':True}))
