from pathlib import Path,PurePosixPath
import ast,hashlib,io,json,re,subprocess,sys,tarfile,zipfile
ROOT=Path(r'F:\mb-r25-qa-ui-after-20261019');OLD=Path(r'F:\mb-r25-qa-ui-20261019');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
EV=ROOT/'docs/implementation/20261018-evolution/evidence';OLD_EV=OLD/'docs/implementation/20261018-evolution/evidence'
HEAD='345aa7ce16f65fec9481b48cfcd63c33ff3835fc';PREVIOUS='2c8ee350aaa8d0d95b5c6346dc355b3efc3d0040';SHA=lambda raw:hashlib.sha256(raw).hexdigest()
scanner=ast.parse((TEMP/'metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'))
fn=next(n for n in scanner.body if isinstance(n,ast.FunctionDef) and n.name=='scan');exec(compile(ast.Module(body=[fn],type_ignores=[]),'<reviewed-token-scanner>','exec'))
def write(path,raw):
    scan(raw,path.name)
    with path.open('xb') as stream:stream.write(raw)
def dump(path,value):write(path,(json.dumps(value,indent=2)+'\n').encode())
git=lambda root,*args:subprocess.check_output(['git',*args],cwd=root)
assert git(ROOT,'rev-parse','HEAD').decode().strip()==HEAD and not git(ROOT,'status','--porcelain','--untracked-files=no').strip()
links=[]
for suffix in ('http','layout','axe'):
    phase=TEMP/('metodobase-r25-qa-ui-'+suffix+'-after-20261019');out=EV/('qa-r25-ui-'+suffix+'-after-independent-20261019')
    before=json.loads((phase/'before.private.json').read_bytes());after=json.loads((phase/'after.private.json').read_bytes());assert before==after and before['head']==HEAD and before['pip_check']==0
    write(out/'source-environment-before.json',(phase/'before.private.json').read_bytes())
    dump(out/'source-environment-quiet.json',{'head':HEAD,'before_SHA256':SHA((phase/'before.private.json').read_bytes()),'after_SHA256':SHA((phase/'after.private.json').read_bytes()),'exact_equal':True,'pip_check_before':0,'pip_check_after':0,
        'runtime_source_count':len(before['runtime_raw_sha256']),'distribution_name_version_metadata':len(before['packages']),
        'scope':'337 tracked runtime RAW hashes and89 distribution name/version metadata. HTTP also pins Python/test; browser additionally pins Node/Chrome/own drivers and3 Node package.json metadata. No hash of all installed distribution bytes.'})
    if suffix=='http':
        summary=json.loads((out/'summary.json').read_bytes());assert summary['exit']==0 and len(summary['cases'])==2 and all(not(c['failed'] or c['error'] or c['skipped']) for c in summary['cases'])
        write(out/'canary-preservation.json',(TEMP/'metodobase-r25-qa-after-canary-preservation.json').read_bytes())
        dump(out/'scope-clarification.json',{'accepted':'The exact2 export422 canaries now pass on both factories, with no-store and no-referrer;7 function ASTs unchanged from preserved finding.',
            'historical_note':'The copied launcher retains a historical initial_harness_reds note in summary.json. That note is historical context, not the status of this2-case run. No replay of the prior10 independent HTTP controls,22 author HTTP or2 SSR is claimed here.'})
    else:
        receipt=json.loads((out/'browser-receipt.json').read_bytes());report=json.loads((out/'browser-report.json').read_bytes())
        assert receipt['completed'] and receipt['server_exit']==0 and receipt['listener_closed'] and receipt['direct_owned_processes_remaining']==[] and receipt['observed_node_browser_generations_remaining']==[]
        assert report['complete'] and report['pageErrors']==[] and report['browser_close_returned']
        marker=json.loads((phase/'startup.private.json').read_bytes())
        dump(out/'startup-sanitized.json',{key:marker[key] for key in ('fixture','pid','port','origin','revision','model_tables','physical_tables')})
        if suffix=='layout':
            original=(OLD_EV/'qa-r25-ui-layout-before-independent-20261019/browser-driver.cjs').read_bytes();assert (out/'browser-driver.cjs').read_bytes()==original
            checked=subprocess.run([sys.executable,str(ROOT/'tests/check_progress32_layout_qa.py'),str(out/'browser-report.json'),'--source-head',HEAD,'--expect','after-green'],cwd=ROOT,capture_output=True)
            assert checked.returncode==0;write(out/'layout-parser-after.json',checked.stdout);write(out/'layout-parser.py',(ROOT/'tests/check_progress32_layout_qa.py').read_bytes())
            dump(out/'same-canary.json',{'before_driver_RAW_SHA256':SHA(original),'after_driver_RAW_SHA256':SHA((out/'browser-driver.cjs').read_bytes()),'RAW_exact':True,'parser_RAW_equals_before':(ROOT/'tests/check_progress32_layout_qa.py').read_bytes()==(OLD_EV/'qa-r25-ui-layout-before-independent-20261019/layout-parser.py').read_bytes(),
                'before':'0/4 criteria on b7; numeric/civil-date tokens fragmented and no region scroll. Prior red evidence unchanged.',
                'after':'4/4 on345; tokens1fragment, actual region overflow+ArrowRight+focus, body0. Same4 criteria and same browser driver/parser.'})
        else:
            assert len(report['views'])==8 and all(not view['overflow'] and not view['violations'] for view in report['views'])
            dump(out/'manual-visual-review.json',{'inspected_local_images':['professional-affected-1440.png','personal-affected-320.png'],
                'observations':'Visible civil dates remain whole and the desktop professional view displays88.25kg native versus71.5kg shared with a distinct1-of-1 counter. Mobile keeps the table inside its labelled horizontal region; the separate exact canary proves keyboard scrolling and unbroken offscreen numbers. No whole-page horizontal overflow. Long rows require horizontal movement inside the region.',
                'limits':'Manual screenshot inspection plus scoped axe AA, not a screen-reader session or global accessibility conformance. No new14-group business-flow acceptance.'})
    archive=TEMP/(phase.name+'-originals-private.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as bundle:
        for item in phase.iterdir():
            if item.is_file():bundle.write(item,item.name)
    dump(out/'private-originals-receipt.json',{'archive_name':archive.name,'bytes':archive.stat().st_size,'SHA256':SHA(archive.read_bytes()),'uploaded':False,'contents':'Raw logs/JUnit, private real startup/SQLite identity, before/after photos and, for browser, full process generations/command lines plus own stop receipts and delivery proof. No raw private files published.'})
    files=[]
    for item in sorted(out.iterdir()):
        if item.is_file():
            raw=item.read_bytes();scan(raw,item.name);files.append({'path':item.name,'bytes':len(raw),'SHA256':SHA(raw)})
    dump(out/'manifest.json',{'source_head':HEAD,'files':files});links.append({'prefix':out.name,'files':len(files),'manifest_SHA256':SHA((out/'manifest.json').read_bytes())})
out=EV/'qa-r25-ui-after-review-20261019';out.mkdir(exist_ok=False);write(out/'.gitattributes',b'* -text\n')
before_runtime=json.loads((TEMP/'metodobase-r25-qa-ui-layout-before-20261019/before.private.json').read_bytes())['runtime_raw_sha256']
after_runtime=json.loads((TEMP/'metodobase-r25-qa-ui-layout-after-20261019/before.private.json').read_bytes())['runtime_raw_sha256']
assert set(before_runtime)==set(after_runtime)
different=[name for name in before_runtime if before_runtime[name]!=after_runtime[name]]
assert set(different)=={'web/middleware/security_headers.py','web/static/css/progreso.css'}
dump(out/'runtime-before-after-preservation.json',{'previous_source':'b7f8e129251dfd5216f811ba77d0b6183ca76735','after_source':HEAD,'runtime_paths':len(before_runtime),'exactly_equal_RAW_paths':len(before_runtime)-len(different),'changed_paths':different,
    'changed':{name:{'before_RAW_SHA256':before_runtime[name],'after_RAW_SHA256':after_runtime[name]} for name in different},'no_QA_product_edits':True})
old_links=[]
for prefix in ('qa-r25-ui-http-replay-independent-20261019','qa-r25-ui-layout-before-independent-20261019','qa-r25-ui-review-20261019'):
    name='docs/implementation/20261018-evolution/evidence/'+prefix+'/manifest.json';raw=(OLD/name).read_bytes();assert git(OLD,'show',PREVIOUS+':'+name)==raw
    old_links.append({'commit':PREVIOUS,'prefix':prefix,'manifest_SHA256':SHA(raw)})
write(out/'canary-preservation.json',(TEMP/'metodobase-r25-qa-after-canary-preservation.json').read_bytes())
for name in ('metodobase-r25-qa-after-prepare.py','metodobase-r25-qa-axe-after-prepare.py'):
    write(out/name,(TEMP/name).read_bytes())
dump(out/'review.json',{'source_head':HEAD,'status':'PASS_SCOPED_REPAIRS_ONLY','http':'Same2 export422 cases: prior2red ->2green;7 functions AST unchanged. No re-attribution of prior additional HTTP/SSR/VM gates.',
    'mobile':'Same4 layout cases: prior0/4 ->4/4 with browser driver/parser RAW identical. Numeric+unit and civil date are1fragment, labelled focusable internal region actually scrolls with ArrowRight, bodyoverflow0.',
    'affected_views':'8 fresh actual views at320/390/768/1440, personal/professional; actual API setup populated all affected table types.0 scoped axeAA violations,0 whole-page overflow,0 pageerrors; observed numeric/date/timestamp tokens1fragment. These views are not the prior14 business groups.',
    'manual':'Local professional1440 and personal320 screenshots inspected; figures/date labels readable and source histories separated. Horizontal table scrolling is intentional and tested.',
    'resources':'Both browser runs closed context/browser and uvicorn cooperatively; each9 observed Node/Chrome generations absent, own ports55343 and55408 closed, no own process/listener retained. RAM/Chrome lease returned to root before seal; no forced signal, foreign process or VM mutation.',
    'source':'337 runtime RAW sources/89 installed name-version metadata quiet each phase; pipcheck0 before/after. Node/Chrome/own drivers and3 Node package.json quiet per browser.335 runtime RAW paths exact from priorb7; only author headers/CSS differ.',
    'limits':'No PostgreSQL/RLS, clinical/provider, production, SLO or globalR25 acceptance. Parent-authority withdrawal design remains outside this repaired-header/mobile gate. Prior b7/2c8 evidence remains immutable.',
    'after_evidence':links,'before_evidence':old_links})
write(out/'seal-driver.py',Path(__file__).read_bytes())
files=[{'path':item.name,'bytes':item.stat().st_size,'SHA256':SHA(item.read_bytes())} for item in sorted(out.iterdir()) if item.is_file()]
dump(out/'manifest.json',{'source_head':HEAD,'files':files})
print(json.dumps({'after_evidence':links,'review_manifest_SHA256':SHA((out/'manifest.json').read_bytes()),'runtime_changed_paths':different},indent=2))
