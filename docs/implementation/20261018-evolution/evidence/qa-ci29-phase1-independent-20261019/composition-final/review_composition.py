"""Focal source-composition acceptance; authenticate existing full/root evidence without rerun."""
from support import *
import xml.etree.ElementTree as ET
from unittest.mock import patch
import yaml
CI2='67ae4664ed091f05568f49e366a67d6846d8a728';ARCHIVE='98ef40f0604ce730a1757940c4a551dd83f87fa2';PROOF='fd636202045efa30b1430f4a9dd8ab287ec76357'
blob=lambda revision,name:git('show',revision+':'+name)
before=photo('composition-before')
verifier='tests/verify_member_links_ci.py';runner='tests/run_reviewed_ci28.py';unit='tests/test_reviewed_ci28_archive.py'
old_digest=b'ae535aab4f27b0ea2f76da4ef6068129c2a7520326012c77c1142a1a6cea14e6';new_digest=b'58cf6c165d155d13120c3fe2ea50f1fac26960a3456c438418de45a2e040bbed'
assert blob(HEAD,verifier)==blob(CI2,verifier).replace(old_digest,new_digest)
assert blob(HEAD,runner)==blob(ARCHIVE,runner) and blob(HEAD,unit)==blob(ARCHIVE,unit)
changed=git('diff','--name-only',CI2,HEAD).decode().splitlines();maintained=[name for name in changed if not name.startswith('docs/')]
assert set(maintained)=={verifier,runner,unit}
assert not git('diff','--name-only','6c9347d226f57b967f4bb881ab005920f6c9b238',HEAD,'--','web','api','core','tests/e2e','.github/workflows/ci.yml').strip()
proof_changes=git('diff','--name-only',HEAD,PROOF).decode().splitlines()
prefix='docs/implementation/20261018-evolution/evidence/ci-member-links29-composition-author-20261019/'
assert len(proof_changes)==24 and all(name.startswith(prefix) for name in proof_changes)
manifest_raw=blob(PROOF,prefix+'manifest.json');assert sha(manifest_raw)=='06c52a03e6a1a4c5a8fb4d5bbeb4949b537024912d026624de3dcb1b9560251c'
manifest=json.loads(manifest_raw);assert len(manifest['files'])==23
for name,value in manifest['files'].items():
    actual=blob(PROOF,prefix+name);assert len(actual)==value['bytes'] and sha(actual)==value['sha256']
author_report=json.loads(blob(PROOF,prefix+'guard-review.json'))
assert len(author_report['reports'])==26 and len(set(author_report['reports']))==26
assert len(author_report['unauthorized_delta_canaries'])==25
assert len(author_report['current_report_canaries'])==55 and len(author_report['current_inert_fixture_cases'])==27
assert author_report['historical_exit']==0
cases=ET.fromstring(blob(PROOF,prefix+'unit.xml')).findall('.//testcase')
assert len(cases)==47 and not any(case.find(kind) is not None for case in cases for kind in ['skipped','failure','error'])
old_receipt=json.loads(blob(PROOF,prefix+'historical-receipt.json'))
assert old_receipt['files']==4433 and old_receipt['pinned_tree_blobs_verified'] is True and old_receipt['replacement_objects_disabled'] is True and old_receipt['exit_code']==0
root_summary=json.loads(blob(PROOF,prefix+'summary.json'));assert all(row['exit']==0 for row in root_summary['results']) and root_summary['files']==5347 and root_summary['packages']==89
assert blob(PROOF,prefix+'before.json')==blob(PROOF,prefix+'after.json')
sys.path.insert(0,str(ROOT))
from tests import verify_member_links_ci as guard
assert len(guard.PINNED_CURRENT_GATES)==8 and guard.PINNED_CURRENT_GATES[runner]==new_digest.decode()
guard.authenticate_current_gates()
old=guard.baseline();workflow=yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8-sig'))
_,reports=guard.verify_workflow(workflow,old);assert len(reports)==26
markers=guard.actual_fixture_markers();assert len(markers)==3 and all(row['tables']==29 and row['model_target_revision']=='20261019_client_account_links' for row in markers)
phase=TEMP/'anchors';phase.mkdir(exist_ok=False)
for name in guard.PINNED_CURRENT_GATES:
    target=phase/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
with patch.object(guard,'ROOT',phase):
    guard.authenticate_current_gates()
    target=phase/runner;current=target.read_bytes();target.write_bytes(blob(CI2,runner))
    try:
        try:guard.authenticate_current_gates()
        except AssertionError as error:rejected=str(error)==runner
        else:rejected=False
    finally:target.write_bytes(current)
    assert rejected
    guard.authenticate_current_gates()
after=photo('composition-after');assert before==after
save('composition-source-and-proof-review.json',{'head':HEAD,'proof_only_head':PROOF,'root_manifest_sha256':sha(manifest_raw),'root_RAW_blobs_authenticated':23,'root_full_guard_evidence':{'reports':26,'delta':25,'report_canaries':55,'inert':27,'unit_passed':47,'historical_blobs':4433},'root_attribution_preserved':True,'QA_reexecuted_root_full_or_unit':False,'focal_current_executions':{'eight_current_anchors_authenticate':True,'old_vulnerable_archive_runner_rejected_under_composed_anchor':True,'actual_workflow_matches_closed_expected_delta':True,'report_count':26,'three_actual_ORM_marker_expressions_29':True},'composition_preservation':{'verifier_entire_body_is_exact_CI2_with_only_runner_digest_replaced':True,'runner_and_newunit_exact_archive98_blobs':True,'maintained_diff_from67':maintained,'web_api_core_e2e_workflow_identical_to_real_browser6c':True,'proof_commit_only24evidence_files':True},'source_helpers_packages_stable':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'scope':'Focal independent source/pin/workflow/actual ORM marker checks, and authentication of author full47/guard evidence. No new archive extraction, broad/PG/Chrome/Actions/Linux/image/SLO claim.'})
print(json.dumps({'head':HEAD,'proof_head':PROOF,'focal_passed':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'author_full_guard_authenticated':True,'global_CI29_local_suitable_for_integration':True}))
