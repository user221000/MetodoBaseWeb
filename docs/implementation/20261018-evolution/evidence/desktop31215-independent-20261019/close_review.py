"""Seal the independent unsigned artifact/payload review without installation claims."""
from datetime import datetime,timezone
import shutil
from run_bundle51 import *

EVI=Path(r'F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence')
AUTHOR=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-desktop31215-build66-20261019')
OLD=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-desktop-artifact27-independent-c22is1va')
bundle=json.loads((OUT/'bundle51-source.json').read_text(encoding='utf8'))
installer=json.loads((OUT/'installer27-source.json').read_text(encoding='utf8'))
runtime=json.loads((OUT/'runtime-review-v2.json').read_text(encoding='utf8'))
original_runtime=json.loads((OUT/'runtime-review.json').read_text(encoding='utf8'))
assert len(bundle['checks'])==51 and not bundle['failed_checks']
assert len(installer['checks'])==27 and not installer['failed_checks']
assert runtime['check_count']==15 and not runtime['failed'] and all(value['ok'] for value in runtime['checks'].values())
assert original_runtime['failed']==['bundled_python_DLL_version_resource_is_31215']
assert bundle['before']==bundle['after']==installer['before']==installer['after']
photo=bundle['after']
assert len(photo['tracked_sources'])==4433 and len(photo['bundle'])==1215 and len(photo['installer_inputs'])==4
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()==HEAD
assert not subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT).strip()
def info(path):return {'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}
assert all(info(ROOT/relative)==value for relative,value in photo['tracked_sources'].items())
assert all(info(ROOT/'dist/MetodoBase'/relative)==value for relative,value in photo['bundle'].items())
assert info(ROOT/'dist/MetodoBase_v2.0.0_win32.zip')=={'bytes':122441614,'sha256':'4966896c41e53b1b5df443045a0175626571a4bfd98731e200bcd299353ed353'}
setup=AUTHOR/'inno/compiled/MetodoBaseSetup_v2.0.0.exe'
assert info(setup)=={'bytes':89973261,'sha256':'5651f4189b7640edced7986db007a4a63f54ba00801658f31fa789587d219363'}
phases=['bundle-before','bundle-after','installer-before','installer-after','runtime-before','runtime-after','runtime-v2-before','runtime-v2-after']
package_photos=[json.loads((OUT/(phase+'-packages.json')).read_text(encoding='utf8')) for phase in phases]
assert all(value==package_photos[0] for value in package_photos)
assert all(value['count']==83 and value['pip_check_exit']==0 for value in package_photos)
for original,target in [(TEMP/'inno-author-authenticated-compatibility-view.json','inno-author-authenticated-compatibility-view.json'),
    (AUTHOR/'inno/summary.json','retained-author-inno-summary.json'),
    (AUTHOR/'inno/inventories-private.json','retained-author-inno-inventories.json'),
    (TEMP/'desktop-artifact27-independent-extractor-provenance.json','retained-extractor-provenance.json'),
    (TEMP/'desktop-artifact27-independent-extractor-signature.json','retained-extractor-signature.json')]:
    with (OUT/target).open('xb') as stream:stream.write(original.read_bytes())
adapter=json.loads((OUT/'historical-criteria-adaptation.json').read_text(encoding='utf8'))
assert all(value['all_other_AST_exact'] and value['check_calls_same_order'] for value in adapter.values())
modules=bundle['checks']['embedded_high_value_code_equals_source']['details']['modules']
diagnostic=bundle['checks']['independent_packaged_offscreen_diagnostic']['details']
signature=installer['checks']['new_installer_unsigned_candidate_explicit']['details']
summary={
 'status':'ACCEPTED within independent unsigned Windows x64 bundle/ZIP and compiled Inno payload review scope.',
 'closed_utc':datetime.now(timezone.utc).isoformat(),'source_commit':HEAD,'source_worktree':str(ROOT),
 'artifacts':{'zip':dict(path=str(ROOT/'dist/MetodoBase_v2.0.0_win32.zip'),**info(ROOT/'dist/MetodoBase_v2.0.0_win32.zip')),
              'setup':dict(path=str(setup),**info(setup)),
              'build_manifest':info(ROOT/'dist/MetodoBase/build-manifest.json')},
 'checks':{'historical_bundle_criteria':51,'historical_compiled_installer_payload_criteria':27,
           'additional_runtime_binary_package_checks':15,'total_unique_current_checks':93,'failed_current_checks':0,
           'maintained_source_suites_or_build_or_SCA_repeated':False},
 'historical_adaptation':{'originals_retained':True,'all_other_AST_exact':True,
        'changes_only':'Frozen paths/head,source count4433, expected ZIP andSetup byte sizes/hashes. New receipt compatibility view maps output.path to file and authenticates original119-tool dictionary before exposing tools. Criteria/assertion structure intact.',
        'proof':'historical-criteria-adaptation.json','receipt_proof':'inno-receipt-view-provenance.json'},
 'verified':{'tracked_source_files':4433,'source_worktree_and_index_exact_commit':True,'bundle_files':1215,
      'manifest_file_entries_without_self':1214,'installer_explicit_input_files':4,
      'zip_every_payload_byte_equals_bundle':True,'compiled_Setup_payload_every_byte_equals_bundle':True,
      'unexpected_app_payload_or_private_data_names':False,'OPS10_source_retained_and_excluded_casefold_from_bundle_ZIP_Setup':True,
      'embedded_project_modules_structural_comparison':len(modules),'all_embedded_project_modules_equal_source':True,
      'source_bundle_ZIP_inputs_git_settings_stable':True,'compiler_and_extractor_tools_stable':True,'compiler_tool_files':119,
      'effective_packages':83,'package_and_lock_photos':8,'pip_checks_exit_zero':8,'all_package_and_lock_photos_identical':True},
 'runtime':{'Python':'3.12.15','OpenSSL':'3.5.9','Expat':'2.8.5','PySide6_and_Qt':'6.8.3',
       'source_distribution':'Retained immutable Astral python-build-standalone release20261013, asset638902133, unstripped Windows x86_64 install_only.',
       'archive_sha256':'bbc902d4d187ac4914915bf538196a064b49109a33a104965b5164ced5b80a1e',
       'python_core_TLS_expat_binaries_exact_archive_and_extracted_reference':True,
       'DLL_file_version':'3.12.15','DLL_product_version':'3.12.15','fixed_version_tuple':[3,12,15150,1013],
       'five_Qt_native_binaries_equal_effective_locked_environment':True,
       'authentication_limit':'Retained release/API/checksum same-provider hash authentication; no PSF Windows installer origin or artifact signature verification claim.'},
 'original_SCA':{'packages':83,'original_report_sha256':'ca85f119c35388197de1c8854ef2e0b62c0b926a47646a56997c2a05d8d462f6',
       'effective_build_inventory_exact_match':True,'recorded_vulnerability_matches':0,'new_scan':False,
       'scope':'Retained original Python package OSV result; exhaustive native DLL CVE analysis not asserted.'},
 'actual_packaged_Qt_diagnostic':diagnostic,
 'installer':{'product_Setup_executed':False,'extractor_only_executed':True,
       'listing_integrity_test_and_extraction_exit_zero':True,'complete_app_payload_files':1215,
       'external_reconstructed_file_only':'install_script.iss','unsigned_candidate':True,'signature_directory':signature,
       'installation_upgrade_uninstall_tested':False,'HKCU_or_registry_modified_by_reviewer_commands':False},
 'own_harness_error_preserved':{'original_check':'bundled_python_DLL_version_resource_is_31215',
       'original_false_assumption':'VS_FIXEDFILEINFO third integer is15; authenticated source itself uses15150,1013 while FileVersion/ProductVersion strings are3.12.15.',
       'correction':'Exact full tuple equality to authenticated reference plus exact source/bundle FileVersion/ProductVersion strings3.12.15; archive/runtime guards retained.',
       'files':['review_runtime.py','runtime-first-console.log','runtime-review.json','DLL-resource-original-diagnostic.json','DLL-resource-harness-correction.json'],
       'original_console_encoding':'PowerShell captured console, preserved unchanged; corrected runtime output raw subprocess bytes.',
       'historical51_and27_repeated':False,'product_changes':False},
 'pending_outside_scope':['Discardable Windows install/upgrade/uninstall','Authorized signing and signature/identity verification',
      'Business login/registration/licensing authority flows and SEC01 decision','OS-level egress isolation measurement',
      'Exhaustive binary embedded-secret/native CVE analysis','Native Linux/macOS packaging'],
 'other_task_separate':'R12 core29 V1 partial95 green with three confirmed security defects, not accepted; desktop source66 does not include or accept29 API/core changes.'
}
save('final-summary.json',summary)
files={path.relative_to(OUT).as_posix():info(path) for path in sorted(OUT.rglob('*')) if path.is_file() and path.name!='final-manifest.json'}
assert not any('__pycache__' in name for name in files)
save('final-manifest.json',{'source_commit':HEAD,'file_count':len(files),'files':files})
for name,value in files.items():assert info(OUT/name)==value
print(json.dumps({'summary_sha256':sha((OUT/'final-summary.json').read_bytes()),
                  'manifest_sha256':sha((OUT/'final-manifest.json').read_bytes()),'files':len(files),'checks':93,
                  'sources':4433,'bundle':1215,'packages':83,'status':'accepted scoped unsigned artifact/payload'}))
