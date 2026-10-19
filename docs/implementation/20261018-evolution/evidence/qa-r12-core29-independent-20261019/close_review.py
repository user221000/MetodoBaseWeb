"""Freeze partial V1 core review, original harness errors and exact scoped evidence."""
import shutil
import xml.etree.ElementTree as ET
from qa_core_support import *

phase_names=['author55','own','own-isolated','preservation18']
photos=[json.loads((OUT/(phase+'-'+side+'-source.json')).read_text(encoding='utf8'))
        for phase in phase_names for side in ['before','after']]
assert all(value==photos[0] for value in photos)
assert len(photos)==8 and photos[0]['source_count']==739 and photos[0]['package_count']==89
assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain').decode().strip()
results={name:json.loads((OUT/(name+'-result.json')).read_text(encoding='utf8')) for name in phase_names}
for name,count in [('author55',55),('own-isolated',22),('preservation18',18)]:
    assert results[name]['exit']==0 and results[name]['counts']==dict(collected=count,failed=0,errors=0,skipped=0,passed=count)
assert results['own']['counts']==dict(collected=22,failed=0,errors=22,skipped=0,passed=0)
verified_owned=[]
for phase in ['author55','own-isolated','preservation18']:
    receipt=results[phase]['owned_database_receipt']
    assert receipt['all_exact_owned_names_absent']
    verified_owned.extend(receipt['created_owned_names'])
assert len(verified_owned)==len(set(verified_owned))==10
source=OUT/'test_r12_core29_review.py'
temp=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-r12-core29-independent-20261019')/source.name
assert source.read_bytes()==temp.read_bytes()
archived=OUT/'reviewed-author-exact-raw.zip'
with archived.open('xb') as stream: stream.write(RAW.read_bytes())
assert sha(archived.read_bytes())=='a1ea7f6e011fa571354f2dc865d8689b039e186a7542720a64c664ebf96ecc8a'
timings={}
for phase in ['author55','own-isolated','preservation18']:
    suites=ET.parse(OUT/(phase+'.xml')).getroot().findall('.//testsuite')
    timings[phase]={'pytest_seconds':sum(float(suite.attrib.get('time','0')) for suite in suites),
                    'runner_seconds':results[phase]['seconds']}
summary={
    'status':'PARTIAL: tested scope green; overall revision29 core acceptance blocked by three independently reproduced security defects on this V1 freeze.',
    'head':HEAD,'owned_worktree':str(ROOT),'base':BASE,
    'author_freeze_sha256':'72b2bce34fba31d74e24aaa2d06d910d47d0f27308855b9f75b689d367a7acc6',
    'author_exact_raw_zip_sha256':sha(archived.read_bytes()),
    'executed_criteria':{'maintained_canonical_and_projection_root_owner_lock':55,'independent_SQL':22,
                         'new29_model_and_migration_preservation':18,'total_passed':95,'failed':0,'errors':0,'skipped':0,
                         'postgres_criteria':82,'sqlite_criteria':13},
    'timings':timings,
    'independent_driver_sha256':sha(source.read_bytes()),'temp_copy_byte_identical':True,
    'independent_criteria':[
       'OWNER accepts own and external invitation with correct proof without adopting profile/role/team/SV/password/email.',
       'Explicit recipient predicate excludes another recipient in the OWNER professional gym scope.',
       'All four fixed/options meals and ten metadata fields equal independently seeded source; stored canonical SHA matches exact stored UTF8.',
       'Structurally valid forged meal or metadata with coherent SHA is rejected with23514 and exact source-mismatch reason.',
       'Exact pg_blocking_pids edge proves invitation row wait; real DB clock expiry after that wait denies42501 with pending pair intact.',
       'Client/Plan/Object invalidation while owner inactive remains withdrawn after source and owner reactivation.',
       'Own recipient revokes link while source owner inactive; another actor cannot mutate; reactivation does not restore publication access.',
       'Direct SQL publication waiting on actual Plan source retains owner share lock; concurrent owner NOWAIT gets55P03; later owner deactivation hides the publication.',
       'All six partial PDF descriptor NULL cases fail; historical20 RLS families equal pre29 and new3 are forced.',
       'Disabled guard trigger and SECURITY DEFINER function drift fail real startup verification; exact restoration passes.'
    ],
    'source_and_packages':{'maintained_plus_freeze_sources':739,'packages':89,'photos':8,'pip_checks':8,
                           'all_sources_and_packages_identical':True,'all_pip_checks_exit':0,
                           'no_product_or_maintained_test_changes':True},
    'preservation':{'historical22_to28_schema_target_files_byte_unchanged':16,
                    'schema_contract_v1_security_contract_v1_tenant_policy_unchanged':True,
                    'models_AST_exact_except_three_new_classes_and_two_unique_constraints':True,
                    'tenant_context_AST_exact_except_one_digest_clear':True,
                    'old20_RLS_families_equal_after_real28_to29_upgrade':True,
                    'new29_model_and_migration_cases':'8 SQLite model +5 SQLite migration +5 PostgreSQL migration; exact28 prerequisite, populated/empty preserve/repeat, unknown drift stops before newDDL, injected rollback, startup signature drift.'},
    'original_harness_errors':{'phase':'own','collected':22,'setup_errors':22,'product_criteria_executed':0,
        'preserved':['own-original.log','own.xml','own-result.json','run_own.py','launch_pg_tests.py'],
        'cause':'Evidence driver under MAIN loaded ancestor MAIN conftest, causing mixed29 tests/28 schema_control modules.',
        'correction':'Exact driver bytes copied to Temp outside repository; explicit frozen worktree rootdir/config/importlib and module-origin guard.',
        'assertions_changed':False,'failed_attempt_cleanup_limit':'Generator finally executed exact DROP on its own DB on setup failure, but original observation plugin only recorded yielded fixtures and did not capture this failed setup DB name; do not count it among ten independently verified absences.'},
    'other_preparation_error':{'source_preservation.py':'Original raw contract hash check failed because checkout CRLF differed from authenticated LF. Preserved original; additive source_preservation_eol.py authenticates normalized contract and records both exact raw hashes. No test or DB action before this preparation correction.'},
    'owned_resources':{'verified_exact_owned_UUID_databases_absent':verified_owned,'verified_database_count':10,
                       'engines_disposed_by_fixtures':True,'new_http_listeners':0,'browsers':0,
                       'providers':'External sockets blocked by maintained isolated runner; only synthetic metadata/SQL, no PDF object download or real provider contacts.'},
    'security_blockers_external_independent_review':[
        'Resource OWNER team_gym_id becomes nonNULL after publication: canonical=false but recipient still reads publication.',
        'Recipient professional parent OWNER has nonNULL team_gym_id: actor remains eligible and still reads.',
        'OWNER own-gym valid consume then clear proof GUC before commit can commit because NOT NULL from r12_proof is not true.'
    ],
    'security_blocker_provenance':'Reported by /root/security_privacy_next against exact frozen ad712416; separate immutable driver prefix SHAa51dde94. This QA did not duplicate or claim those executions. Backend confirmed V2 correction pending; V1 worktree remains untouched.',
    'not_accepted_or_executed':['API/HTTP/routes/services/export integration','full revision29 acceptance','restore29','full broad or historical PG gates','browser/VM suites','performance/SLO/load measurement','desktop package']
}
save('final-summary.json',summary)
files={str(path.relative_to(OUT)).replace('\\','/'):{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}
       for path in sorted(OUT.rglob('*')) if path.is_file() and path.name!='final-manifest.json'}
assert not any('__pycache__' in name for name in files)
save('final-manifest.json',{'head':HEAD,'status':'PARTIAL/BLOCKED security V1','file_count':len(files),'files':files})
for name,value in files.items():
    assert sha((OUT/name).read_bytes())==value['sha256']
print(json.dumps({'summary_sha256':sha((OUT/'final-summary.json').read_bytes()),
                  'manifest_sha256':sha((OUT/'final-manifest.json').read_bytes()),'files':len(files),
                  'tested_passed':95,'status':'PARTIAL/BLOCKED security V1','sources':739,'packages':89,
                  'independent_driver_sha256':sha(source.read_bytes()),'owned_verified_absent':10}))
