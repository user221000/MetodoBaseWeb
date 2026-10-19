"""Preserve failed147; make Windows spawn import inert and replay only original race node."""
from support import *
original=(OUT/'launch.py').read_text(encoding='utf8')
prefix,body=original.split('mode=sys.argv[1]',1)
body='mode=sys.argv[1]'+body
needle="elif mode=='UI10':files=['tests/test_r12_ui_pages.py']"
assert body.count(needle)==1
body=body.replace(needle,needle+"\nelif mode=='race1':files=['tests/integration_client_link_service_races.py::test_two_processes_consume_one_proof_once_under_restricted_role[postgresql]']")
guarded=prefix+'def launch_main():\n'+''.join('    '+line if line.strip() else line for line in body.splitlines(keepends=True))+"\nif __name__=='__main__':\n    launch_main()\n"
target=OUT/'launch_guarded.py';target.write_text(guarded,encoding='utf8',newline='\n')
original_runner=(OUT/'run_phase.py').read_text(encoding='utf8')
adapted=original_runner.replace("'UI10':(10,0,0)","'UI10':(10,0,0),'race1':(1,0,1)")
assert adapted!=original_runner and adapted.count("str(OUT/'launch.py')")==1
adapted=adapted.replace("str(OUT/'launch.py')","str(OUT/'launch_guarded.py')")
(OUT/'run_guarded_phase.py').write_text(adapted,encoding='utf8',newline='\n')
save('Windows-spawn-harness-correction.json',{'original_failed_phase':'backend147','original_failure_nodeid':'tests/integration_client_link_service_races.py::test_two_processes_consume_one_proof_once_under_restricted_role[postgresql]',
 'raw_outputs_preserved':str(TEMP/'backend147'),'original_counts':{'passed':144,'failed':1,'skipped':2},
 'root_cause':'Both multiprocessing.spawn children reexecuted unguarded launch.py, interpreted pytest argv as a phase and raised Unknown frozen bounded phase before reaching the product worker readiness point.',
 'original_launch_sha256':sha((OUT/'launch.py').read_bytes()),'guarded_launch_sha256':sha(target.read_bytes()),
 'correction':'Wrap actual launcher execution in launch_main guarded by __name__==__main__; module import is inert for Windows spawn. Exact original failed PG node runs alone; no assertion/product changes.',
 'original_147_not_relabelled_as_one_green_run':True,'source_and_package_photos_for_original_stable':True,'original_four_UUID_absent':True})
print(json.dumps({'guarded_launcher_sha256':sha(target.read_bytes()),'targeted_replay':'original PG race node only'}))
