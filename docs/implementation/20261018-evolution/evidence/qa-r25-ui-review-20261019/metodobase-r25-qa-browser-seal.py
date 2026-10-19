from pathlib import Path,PurePosixPath
import ast,hashlib,io,json,re,subprocess,tarfile,zipfile
TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp');ROOT=Path(r'F:\mb-r25-qa-ui-20261019')
EV=ROOT/'docs/implementation/20261018-evolution/evidence';SHA=lambda raw:hashlib.sha256(raw).hexdigest()
tree=ast.parse((TEMP/'metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'))
function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='scan')
exec(compile(ast.Module(body=[function],type_ignores=[]),'<reviewed-token-scanner>','exec'))
def write(path,raw):
    scan(raw,path.name)
    with path.open('xb') as stream:stream.write(raw)
def dump(path,value):write(path,(json.dumps(value,indent=2)+'\n').encode())
rows=[]
for suffix,phase_suffix in [('',''),('-v2','-v2'),('-v3','-v3'),('-layout-before','-layout-before')]:
    public_name='qa-r25-ui-browser'+suffix+'-independent-20261019' if suffix!='-layout-before' else 'qa-r25-ui-layout-before-independent-20261019'
    private_name='metodobase-r25-qa-ui-browser'+phase_suffix+'-20261019' if suffix!='-layout-before' else 'metodobase-r25-qa-ui-layout-before-20261019'
    out=EV/public_name;phase=TEMP/private_name
    before=json.loads((phase/'before.private.json').read_bytes());after=json.loads((phase/'after.private.json').read_bytes());assert before==after
    receipt=json.loads((out/'browser-receipt.json').read_bytes());report=json.loads((out/'browser-report.json').read_bytes())
    assert receipt['server_exit']==0 and receipt['listener_closed'] and receipt['direct_owned_processes_remaining']==[]
    assert receipt['observed_node_browser_generations_remaining']==[] and report['browser_close_returned'] is True
    assert report.get('head',report.get('source_head'))=='b7f8e129251dfd5216f811ba77d0b6183ca76735'
    write(out/'source-environment-before.json',(phase/'before.private.json').read_bytes())
    marker=json.loads((phase/'startup.private.json').read_bytes())
    dump(out/'startup-sanitized.json',{key:marker[key] for key in ('fixture','pid','port','origin','revision','model_tables','physical_tables')})
    dump(out/'source-environment-quiet.json',{'before_SHA256':SHA((phase/'before.private.json').read_bytes()),'after_SHA256':SHA((phase/'after.private.json').read_bytes()),'exact_equal':True,
        'runtime_sources':len(before['runtime_raw_sha256']),'python_distribution_name_version_metadata':len(before['packages']),
        'node_package_json_metadata':len(before['node_package_json_sha256']),'pip_check_before':before.get('pip_check'),'pip_check_after':after.get('pip_check'),
        'scope':'RAW hashes of337 tracked runtime sources, Python/Node/Chrome binaries, exact own drivers and89 distribution name/version metadata plus3 installed Node package.json. No hash of every installed Python byte.'})
    correction='No harness correction in this run.'
    if suffix=='':correction='Initial harness stopped on isDisabled(FIELDSET), whose installed Playwright native-control allowlist excludes FIELDSET. No axe or write-flow acceptance in this execution.'
    elif suffix=='-v2':correction='Second harness used actual fieldset.disabled and descendant input. Four personal axe/reflow views passed, then a single-Tab assumption failed inside native date segments. Preserved; no product defect inferred from this keyboard expectation.'
    elif suffix=='-v3':correction='Same business flow with at most6 Tabs to leave native date segments.14 actual groups and12 scoped axe/reflow screenshots passed. These technical gates do not accept mobile table legibility; the independent later layout canary found4 actual UX reds.'
    else:correction='Independent actual mobile layout found4 real reds. Numeric+unit and civil-date text have4-6 fragments; region has no internal horizontal overflow. This is a product UX finding, not a harness correction. Body overflow0 and region labelling/focus already passed.'
    dump(out/'review-notes.json',{'classification':correction,'no_product_edit':True,'all_prior_runs_preserved':True,
        'credentials_or_private_process_inventory_published':False,'sqlite':'Own real migration32 and runtime verification; synthetic persisted accounts/profiles/subscription, real HTTP password login. No provider sends or artificial authentication dependency.',
        'cleanup':'Own private stop command makes uvicorn return; exact observed Node/Chrome generations absent. No forced signal or RAM erasure claim. Existing user Chrome/8776 untouched.'})
    if suffix in ('-v2','-v3'):
        item=TEMP/('metodobase-r25-qa-browser'+suffix+'-harness-correction.json');write(out/'harness-correction.json',item.read_bytes())
    if suffix=='-layout-before':
        write(out/'layout-parser.py',(ROOT/'tests/check_progress32_layout_qa.py').read_bytes())
        checked=subprocess.run([str(Path(__import__('sys').executable)),str(ROOT/'tests/check_progress32_layout_qa.py'),str(out/'browser-report.json'),'--source-head',before['head'],'--expect','before-red'],capture_output=True)
        assert checked.returncode==0;write(out/'layout-parser-before.json',checked.stdout)
    archive=TEMP/(private_name+'-originals-private.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as bundle:
        for item in phase.iterdir():
            if item.is_file():bundle.write(item,item.name)
    dump(out/'private-originals-receipt.json',{'archive_name':archive.name,'bytes':archive.stat().st_size,'SHA256':SHA(archive.read_bytes()),'uploaded':False,
        'contents':'Original logs, real startup/SQLite path and synthetic identities, process inventories/command lines and generations, before/after photos, private delivery proof and control receipts. Kept private.'})
    files=[]
    for item in sorted(out.iterdir()):
        if item.is_file():
            raw=item.read_bytes();scan(raw,item.name);files.append({'path':item.name,'bytes':len(raw),'SHA256':SHA(raw)})
    dump(out/'manifest.json',{'source_head':before['head'],'files':files})
    rows.append({'prefix':public_name,'files':len(files),'manifest_SHA256':SHA((out/'manifest.json').read_bytes())})
print(json.dumps(rows,indent=2))
