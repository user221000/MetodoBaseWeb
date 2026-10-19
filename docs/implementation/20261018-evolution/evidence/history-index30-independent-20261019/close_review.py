"""Freeze exact current functional acceptance and retained pre-fix evidence, without latency claims."""
from support import *

results={phase:json.loads((OUT/(phase+'-result.json')).read_bytes()) for phase in ['maintained112','own8']}
for phase,count in [('maintained112',112),('own8',8)]:
    assert results[phase]['exit']==0 and results[phase]['counts']==dict(collected=count,failed=0,errors=0,skipped=0,passed=count)
photos=[json.loads((OUT/(phase+'-'+side+'-photo.json')).read_bytes()) for phase in ['maintained112','own8'] for side in ['before','after']]
assert all(value==photos[0] for value in photos)
assert not git('status','--porcelain').strip() and git('rev-parse','HEAD').decode().strip()==HEAD
observations=json.loads((TEMP/'maintained112/ordered-query-postgresql.json').read_bytes())
work=[{'case':row['case'],'visited':row['plan_rows_visited'],'budget':row['max_candidates']} for row in observations]
assert [value['visited'] for value in work]==[51,52,51,51,51]
names=[name for result in results.values() for name in result['owned_absence']['exact_current_process_UUID_names']]
assert len(names)==len(set(names))==14 and all(result['owned_absence']['all_owned_absent'] for result in results.values())
preservation=json.loads((OUT/'source-preservation.json').read_bytes())
summary={'status':'ACCEPTED within frozen revision30 index/migration and personal summary reader functional scope.',
 'head':HEAD,'base':BASE,'owned_worktree':str(ROOT),'source_freeze_sha256':'d01f5b6b898a896d87a22ab6c6fde51ecd508848e6003d7b1e00a59bbad4e3aa',
 'source_freeze_manifest_sha256':'21b14926d7514fe877ddd344a1abcf666d413585c9b7126920721c8da8aa3d1b',
 'criteria':{'maintained_serial_full_selection':112,'independent':8,'total':120,'failed':0,'errors':0,'skipped':0},
 'serial_112_composition':'New16 migration/query +96 existing pagination/cursor/header/error regressions. One complete independent green run on frozen6ea; no author110+2 composition relabeled as one run.',
 'independent_cases':['SQLite/PG rollback/reupgrade with actual pending Link, Invitation and published source-bound Publication, all rows exact and23 RLS/member signatures intact.',
   'PostgreSQL operator class,predicate,timestamp NULL placement and INCLUDE drift each reject startup and downgrade; exact altered index,rows,guards andrevision30 remain unchanged.',
   'SQLite/PG mixed dated/tied/NULL pages compare to independently constructed seed oracle; exact terminal NULL cursor,date-to-NULL boundary,inactive client positive,deleted client and both cross-owner directions excluded; summary-only one SELECT per page.'],
 'query_work_observations':work,'planner_settings_changed_by_review':False,'statistics_costs_modified':False,
 'work_observation_limit':'Concrete synthetic1000-row distribution only; not a universal planner work bound or p95/SLO result. QEMU and other functional work may run concurrently.',
 'photos':{'full_tracked_sources_and_all_nonignored_source_files':photos[0]['source_count'],
           'own_untracked_helpers':photos[0]['helper_count'],'packages':89,'before_after_photos':4,'pip_checks_exit_zero':4,
           'all_full_sources_helpers_packages_identical':True},
 'preservation':{'RAW_sources_authenticated':13,'author_manifest_entries_authenticated':preservation['author_proof_blobs_verified'],
    'two_EOL_only_sources':'models.py/schema_control.py RAW CRLF to GitLF explicitly authenticated; AST identical. All other source blobs RAW exact.',
    'historical22_to29_targets_exact_git_blobs':18,'historical_v1_and_core_security_sources_unchanged':True,
    'target30':'Only one new index and its physical signature; every prior29 target field exact.',
    'maintained_historical_assertion_change':'Only old index-name literal retarget and one additive no-TEMPsort assert; all other pagination AST exact.',
    'before107_over_budget_original_retained':True,'old_SQLite_PG_targets_or_restore_fixtures_retargeted':False},
 'owned_resources':{'exact_UUID_databases_removed_and_absence_verified':14,'names':names,'owned_engines_disposed_by_fixtures':True,
                    'new_HTTP_listeners_or_browsers':0,'only_loopback_SQLite_synthetic_PG_no_external_sockets':True},
 'output_privacy':{'private_originals':str(TEMP),'public_outputs':[entry for result in results.values() for entry in result['public_outputs']],
                    'rule':'Public exactRAW copies when no completeJWT/privateDBURL; any sanitized derivative is explicitly labeled with original/public SHA. No credentials printed.'},
 'no_claim':['API29/restore29/UI29 composition','MAIN integration or production operation','HTTP latency/p95/SLO improvement','Universal physical rows bound','Other load flows/broad suite/browser/VM replays']}
save('final-summary.json',summary)
files={path.relative_to(OUT).as_posix():{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())} for path in sorted(OUT.rglob('*')) if path.is_file() and path.name!='final-manifest.json'}
assert not any('__pycache__' in name for name in files)
save('final-manifest.json',{'head':HEAD,'file_count':len(files),'files':files})
for name,value in files.items():assert sha((OUT/name).read_bytes())==value['sha256']
print(json.dumps({'summary_sha256':sha((OUT/'final-summary.json').read_bytes()),'manifest_sha256':sha((OUT/'final-manifest.json').read_bytes()),
                  'files':len(files),'criteria':120,'sources':photos[0]['source_count'],'helpers':photos[0]['helper_count'],'owned_absent':14}))
