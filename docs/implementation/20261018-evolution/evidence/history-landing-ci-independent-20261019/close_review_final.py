"""Validate actual browser gates and seal this independent CI review."""
from qa_support import *

load=lambda p:json.loads(Path(p).read_text(encoding='utf8'))

def actual_gate(command,label):
    receipt=OUT/(label+'-receipt.json')
    if receipt.is_file():
        previous=load(receipt)
        assert previous['command']==[str(value) for value in command] and previous['exit']==0
        return 0
    return run(command,label).returncode
initial=load(OUT/'maintained-before.json')
for label in ['maintained-after','node23-before','node23-after','primary-before','primary-after','inert-own-before','inert-own-after']:
    assert load(OUT/(label+'.json'))==initial
maintained=load(OUT/'maintained-summary.json');assert maintained['accepted']
primary=load(OUT/'primary-input-summary.json');assert primary['accepted'] and len(primary['cases'])==10
inert=load(OUT/'own-inert-summary.json');assert inert['accepted'] and len(inert['cases'])==20
browsers=[]
prior=None
for kind,checks,fixture,port in [('history',10,'personal-history-ui',8780),('landing',8,'public-landing',8781)]:
    folder=OUT/('browser-'+kind+'-28')
    summary=load(folder/'summary.json');assert summary['head']==HEAD and summary['failure'] is None
    assert summary['results'][0]['checks']==checks and summary['results'][0]['screens']==4
    assert summary['results'][0]['exit']==0 and summary['own_pid_closed_and_foreign_listeners_untouched']
    manifest=load(folder/'manifest.json')
    assert all(sha((folder/name).read_bytes())==value for name,value in manifest['files'].items())
    a,b=load(folder/'before.json'),load(folder/'after.json');assert a==b
    assert a['packages']==initial['packages'] and a['readonly_node_dependencies']==initial['node_dependencies']
    assert all(a['sources'][name]==digest for name,digest in initial['sources'].items() if name in a['sources'])
    foreign_before,foreign_after=load(folder/'foreign-before.json'),load(folder/'foreign-after.json')
    assert foreign_before==foreign_after
    if prior is not None:assert prior==foreign_before
    prior=foreign_after
    close=load(folder/'owned-process-close.json')
    assert close['listener_gone'] and close['owned_port_free'] and close['failure'] is None
    guard1=actual_gate([str(PYTHON),'scripts/check_browser_fixture_startup.py',str(folder/'server.log'),
               '--fixture',fixture,'--tables','26','--revision','20261019_account_recovery'],kind+'-actual-startup-guard')
    guard2=actual_gate([str(PYTHON),'scripts/check_frontend_report.py',str(folder/'author-browser/report.json'),
               '--format','strings','--minimum',str(checks),'--minimum-screens','4'],kind+'-actual-report-guard')
    assert guard1==guard2==0
    report=load(folder/'author-browser/report.json')
    assert report['passed'] is True and report['pageErrors']==[]
    assert len(report['checks'])==len(set(report['checks']))==checks
    screens=[]
    for name in report['screens']:
        scan=load(folder/'author-browser'/(name+'.json'))
        assert scan['overflow'] is False and scan['axe' if kind=='history' else 'violations']==[]
        image=folder/'author-browser'/(name+'.png');assert image.is_file() and image.stat().st_size>0
        screens.append({'name':name,'zero_axe_violations':True,'overflow':False,'png_sha256':sha(image.read_bytes())})
    network=load(folder/'author-browser/network-guard.json')
    assert network['exactOrigin']=='http://127.0.0.1:'+str(port) and network['maxRedirects']==0
    assert type(network['blockedOtherOrigins']) is int and network['blockedOtherOrigins']>=0
    startup=load(folder/'startup.json')
    assert startup['fixture']==fixture and startup['tables']==26 and startup['model_target_revision']=='20261019_account_recovery'
    browsers.append({'kind':kind,'checks':checks,'screens':screens,'seconds':summary['results'][0]['seconds'],
        'source_count':summary['sources'],'packages':89,'node_dependency_files':146,
        'actual_startup_and_report_guards_exit':[0,0],'actual_model_target':startup['model_target_revision'],
        'page_errors':[],'network_guard':network,'own_listener_pid':close['start_fingerprint']['ProcessId'],
        'owned_listener_and_launcher_closed':True,'foreign_listeners_unchanged':True,
        'shutdown':'Deliberate owner Stop-Process after successful driver; raw launcher exit retained, no graceful-shutdown claim.',
        'fixture_authentication':load(folder/'fixture-target28-review.json'),
        'summary_sha256':sha((folder/'summary.json').read_bytes()),'manifest_sha256':sha((folder/'manifest.json').read_bytes())})
final=photo('closure-final');assert final==initial
summary={'accepted':True,'head':HEAD,'candidate_base':'a753b2cdf61a91133bd58c3159b0b35e02167396',
    'qa_closure_observation_correction':load(OUT/'closure-harness-diagnostic.json'),
    'runtime_delta_from_accepted_main':False,'common_sources':len(initial['sources']),'packages':89,'node_dependency_files':146,
    'common_source_package_and_dependency_photos_identical':True,'all_pip_checks_exit':0,
    'maintained':maintained,'primary_cli_own':{'cases':10,'negative':7,'positive':3},
    'actual_function_own_inert':{'cases':20,'negative':18,'positive':2,'all_owned_children_reaped':True},
    'historical_preservation':load(OUT/'static-preservation.json'),'browsers':browsers,
    'only_evidence_and_owned_temp_written':True,'candidate_source_and_git_unchanged':True,
    'scope':'Independent local Windows Python/Git Bash/Node and real single-Chrome sequential loopback fixtures, current ORM metadata target28. No migration execution, old17browser/162VM/broad/PG repeat, Linux/Actions/container build/performance/publication acceptance.'}
save(OUT/'final-summary.json',summary)
files={path.relative_to(OUT).as_posix():sha(path.read_bytes()) for path in sorted(OUT.rglob('*')) if path.is_file()}
save(OUT/'final-manifest.json',{'files':files,'count':len(files),'scope':'Every file in this independent evidence prefix except this self-referential manifest.'})
print(json.dumps({'accepted':True,'head':HEAD,'sources':len(initial['sources']),'packages':89,'browser_groups':[10,8],
    'summary_sha256':sha((OUT/'final-summary.json').read_bytes()),'manifest_sha256':sha((OUT/'final-manifest.json').read_bytes()),'files':len(files)}))
