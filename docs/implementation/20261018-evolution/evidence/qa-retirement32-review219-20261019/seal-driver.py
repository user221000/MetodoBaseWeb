from pathlib import Path,PurePosixPath
import ast,hashlib,io,json,re,subprocess,tarfile,zipfile
import xml.etree.ElementTree as ET
ROOT=Path(r'F:\mb-retirement32-public-qa-20261019');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp');EV=ROOT/'docs/implementation/20261018-evolution/evidence'
HEAD='219f89a5ee0196061fea5b67e36ae07daf7f4316';SHA=lambda raw:hashlib.sha256(raw).hexdigest()
source=ast.parse((TEMP/'metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'));fn=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='scan');exec(compile(ast.Module(body=[fn],type_ignores=[]),'<reviewed-token-scanner>','exec'))
def write(path,raw):
    scan(raw,path.name)
    with path.open('xb') as stream:stream.write(raw)
def dump(path,value):write(path,(json.dumps(value,indent=2)+'\n').encode())
links=[]
for kind in ('http','http-v2','browser'):
    phase=TEMP/('metodobase-retirement32-qa-'+kind+'-20261019');out=EV/('qa-retirement32-'+kind+'-independent-20261019')
    before=json.loads((phase/'before.private.json').read_bytes());after=json.loads((phase/'after.private.json').read_bytes());assert before==after and before['head']==HEAD and before['pip_check']==0
    write(out/'source-environment-before.json',(phase/'before.private.json').read_bytes())
    dump(out/'quiet.json',{'source_head':HEAD,'before_SHA256':SHA((phase/'before.private.json').read_bytes()),'after_SHA256':SHA((phase/'after.private.json').read_bytes()),'RAW_exact_equal':True,'runtime_sources':len(before['runtime_raw_sha256']),
        'distribution_name_version_metadata':len(before['packages']),'pip_check_before':0,'pip_check_after':0,'scope':'Runtime RAW hashes,89 installed distribution name/version metadata, Python/Node/Chrome binaries and own drivers/test as recorded. Browser also records3 Node package.json. Not a hash of all installed distribution bytes.'})
    if kind!='browser':
        cases=[{'class':case.get('classname'),'name':case.get('name'),'failed':case.find('failure') is not None,'error':case.find('error') is not None,'skipped':case.find('skipped') is not None} for case in ET.parse(phase/'results.xml').iter('testcase')]
        dump(out/'cases.structural.json',{'cases':cases,'count':len(cases),'passed':sum(not(c['failed'] or c['error'] or c['skipped']) for c in cases),'errors':sum(c['error'] for c in cases),'failed':sum(c['failed'] for c in cases)})
        dump(out/'harness-assumptions.json',{'initial':'Initial16 comprised8 SSR passes,4 new harness cookie assertions failing and4 creation-helper setup errors. The cookie is the pre-existing unprivileged _csrf, not an issued session. api.app historically omits team creation.',
            'correction':'Only helper assumptions changed: permit exclusively existing _csrf cookie; create genuine invitation/accept/link/grant genealogy through real supported web factory over SAME migrated DB, then execute purpose operations on actual target factory. No auth/router/DDL/limiter/product edit.',
            'preservation':'All4 test-function ASTs unchanged. Initial sources, stdout/stderr/JUnit remain private and hash-bound. Corrected8 functional HTTP passed; no reset of10actor/30IP counters.'})
        if kind=='http-v2':write(out/'helper-preservation.json',(TEMP/'metodobase-retirement32-qa-http-v2-preparation.json').read_bytes())
    else:
        receipt=json.loads((out/'browser-receipt.json').read_bytes());report=json.loads((out/'browser-report.json').read_bytes())
        assert receipt['completed'] and receipt['server_exit']==0 and receipt['listener_closed'] and not receipt['direct_owned_processes_remaining'] and not receipt['observed_node_browser_generations_remaining']
        assert report['complete'] and report['browser_close_returned'] and not report['pageErrors'] and not report['transportViolations'] and len(report['checks'])==13 and len(report['screens'])==9
        assert all(not screen['overflow'] and not screen['violations'] for screen in report['screens'])
        marker=json.loads((phase/'startup.private.json').read_bytes())
        dump(out/'startup-sanitized.json',{key:marker[key] for key in ('fixture','pid','port','origin','revision','model_tables','physical_tables')})
        dump(out/'manual-visual-review.json',{'inspected':['factor-selected-320.png','uncertain-real503-390.png'],'observed':'Legible mobile form/card content; visible focus on fresh password after selection and on the503 error alert; primary/factor boxes empty at the observed action boundaries; categories/periods distinguish the selected local item. No page overflow or clipped action labels. Native single-line email can scroll within its input.',
            'scope':'Manual local screenshots plus9 scoped axeAA/reflow checks. No screen-reader session, global compliance or other-source attribution.'})
        dump(out/'witness-scope.json',{'actual_genealogy':'Owner fresh MFA -> exact action grant -> real team invite -> public acceptance -> real member login -> explicit independent professional link -> consent grant -> parent OFF. B/C own MFA enroll/login before OFF; A password-only. No direct team_gym_id assignment.',
            'faults':'Only parent OFF administrative SQL stimulus and one-shot COMMIT ACK error after an actual withdrawal COMMIT; rollback/close are real and no retained-Session tuple is injected. A late actual metadata response is delayed only in delivery.',
            'secrets':'UI fetch omits cookies/Authorization; no Storage calls, unchanged incidental existing session and no secrets in serialized DOM. Actual proofs remain in form/request/private harness memory only. Public JSON contains shape/counts, no raw request bodies, factor code, seed, kit or token.',
            'budgets':'Per actor database attempts remain≤10; browser purpose calls plus one external CAS stimulus remain≤30 for one IP. No limiter clear or forced time reset. HTTP separate dedicated actors test both exact real limits.',
            'cleanup':'Own cooperative stop, server0/listener64004 absent,9 observed Node/Chrome generations absent. Foreign Chrome and8776 untouched. SQLite/logs/process inventories private; no memory-erasure claim.'})
    archive=TEMP/(phase.name+'-originals-private.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as bundle:
        for item in phase.iterdir():
            if item.is_file():bundle.write(item,item.name)
    dump(out/'private-originals.json',{'archive_name':archive.name,'bytes':archive.stat().st_size,'SHA256':SHA(archive.read_bytes()),'uploaded':False,'contents':'Original RAW stdout/stderr/JUnit/photos; browser adds startup/SQLite identity, captured offline delivery proof, own controls and complete private process generations/command lines. No raw private artifacts published.'})
    files=[]
    for item in sorted(out.iterdir()):
        if item.is_file():raw=item.read_bytes();scan(raw,item.name);files.append({'path':item.name,'bytes':len(raw),'SHA256':SHA(raw)})
    dump(out/'manifest.json',{'source_head':HEAD,'files':files});links.append({'prefix':out.name,'files':len(files),'manifest_SHA256':SHA((out/'manifest.json').read_bytes())})
out=EV/'qa-retirement32-review219-20261019';out.mkdir(exist_ok=False);write(out/'.gitattributes',b'* -text\n')
for name in ('metodobase-retirement32-qa-http-v2-prepare.py','metodobase-retirement32-qa-browser-prepare.py','metodobase-retirement32-qa-http-v2-preparation.json'):
    write(out/name,(TEMP/name).read_bytes())
dump(out/'review.json',{'source_head':HEAD,'status':'PASS_SCOPED_FUNCTIONAL_HTTP_UI_ONLY','VM':'36controller+9DOM synthetic replays45/45; not actual HTTP acceptance.8 existing SSR replay passed.',
    'own_HTTP':'8 own criteria=4×both factories all passed after correcting two creation/cookie helper assumptions;4 semantic test functions AST unchanged. Real eligible invite genealogy, parent OFF, new proof/factor each operation, no authority substitution, uncertain COMMIT, old TOTP, neighbors and exact local10actor/30IP accumulation without reset.',
    'browser':'13 actual groups and9 screenshots incl320/390/768/1440 shell; real password/factor actions, exact selected CAS, actual503 COMMIT-ACK loss and409 concurrent retirement, manual fresh discovery, late response/identity events.0 scoped axeAA,0 overflow,0 pageerrors. Storage0access, unrelated session intact; no session authority issued.',
    'source':'344 runtime RAW paths,89 installed name/version metadata and binaries quiet; each HTTP photo also verifies RAW equals indexed GitLF. Pips0. Browser observed the same runtime hashes with own driver/binary metadata quiet. No every-distribution-byte claim.',
    'resources':'Browser/own server closed cooperatively; port64004 absent,9 Node/Chrome generations absent, lease returned before seal. No PG, VM, provider send or foreign resource mutation.',
    'limits':'Browser belongs only to219f89. SEC18 retained-Session cleanup edge is outside these positive functional gates; a new227 HTTP replay and separate security peer handle that delta. No global R25/MFA/privacy/clinical/production/SLO acceptance. Google-only and lost-all-factor recovery are explicitly outside this purpose.',
    'evidence':links})
write(out/'seal-driver.py',Path(__file__).read_bytes())
files=[{'path':item.name,'bytes':item.stat().st_size,'SHA256':SHA(item.read_bytes())} for item in sorted(out.iterdir()) if item.is_file()]
dump(out/'manifest.json',{'source_head':HEAD,'files':files})
print(json.dumps({'source_head':HEAD,'review_manifest_SHA256':SHA((out/'manifest.json').read_bytes()),'evidence':links},indent=2))
