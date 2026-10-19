from pathlib import Path, PurePosixPath
import ast, hashlib, importlib.metadata, io, json, os, re, subprocess, sys, tarfile, zipfile
import xml.etree.ElementTree as ET

R=Path(r'F:/mb-progress32-retirement-20261019');P=Path(__file__).parent
E=R/'docs/implementation/20261018-evolution/evidence/backend-progress32-retirement-20261019'
BASE='345aa7ce16f65fec9481b48cfcd63c33ff3835fc'
PRIVATE=P.parent/'metodobase-retirement32-private-sealed-20261019'
sha=lambda b:hashlib.sha256(b).hexdigest()
dump=lambda v:(json.dumps(v,ensure_ascii=True,indent=2)+'\n').encode()
def write(path,blob):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(blob)
    assert path.read_bytes()==blob
def git(*args):return subprocess.check_output(['git','--no-replace-objects',*args],cwd=R)
sources=['web/progress_retirement_schemas.py','web/routes/progress_retirement.py','web/services/progress_retirement.py',
    'web/routes/personal_progress.py','web/middleware/security_headers.py','tests/retirement32_owned.py',
    'tests/test_progress_retirement_http.py','tests/test_progress_retirement_boundaries.py',
    'tests/test_progress_retirement_entrypoint_review.py','tests/test_progress_retirement_headers.py',
    'tests/test_progress_retirement_context.py','tests/integration_progress_retirement.py']
assert git('rev-parse','HEAD').decode().strip()==BASE
assert set(git('diff','--name-only',BASE).decode().splitlines())=={'web/routes/personal_progress.py','web/middleware/security_headers.py'}
assert sha((E/'wire-v1.md').read_bytes())=='5b6de9c0ecbb9bdf070a1ef6831d5f22f2ac11bddf32c54f3787b99d315bc706'
source={n:(R/n).read_bytes() for n in sources}

# Every original function is unchanged; only registration and exact privacy paths are added.
old_route=git('show',BASE+':web/routes/personal_progress.py')
route_ast=ast.parse(source['web/routes/personal_progress.py'])
route_ast.body=[n for n in route_ast.body if not(isinstance(n,ast.ImportFrom) and n.module=='web.routes.progress_retirement')
    and not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='router.include_router')]
assert ast.dump(route_ast)==ast.dump(ast.parse(old_route))
old_header=git('show',BASE+':web/middleware/security_headers.py')
header=source['web/middleware/security_headers.py'].replace(b'\r\n',b'\n')
node=next(n for n in ast.parse(header).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='_RETIREMENT_PRIVATE_PATHS')
lines=header.splitlines(keepends=True)
inverse=b''.join(lines[:node.lineno-1]+lines[node.end_lineno:]).replace(b' or request.url.path in _RETIREMENT_PRIVATE_PATHS',b'')
assert inverse==old_header
protected=git('ls-tree','-r','--name-only',BASE,'--','web/database','web/auth.py','web/auth_deps.py','web/services/mfa_service.py','tests/ci_mfa31').decode().splitlines()
protected_proof={}
for name in protected:
    blob=git('show',BASE+':'+name);actual=(R/name).read_bytes()
    assert actual==blob or actual.replace(b'\r\n',b'\n')==blob
    protected_proof[name]={'Git_sha256':sha(blob),'RAW_sha256':sha(actual),'GitLF_or_RAW_exact':True}

public={'seal-driver.py':Path(__file__).read_bytes(),'run-phase.py':(P/'run_phase.py').read_bytes(),
 'archive-acl.ps1':(P/'archive-acl.ps1').read_bytes(),'run-original-canary.py':(P/'run.py').read_bytes(),
 'original-parent-canary.py':(P/'test_parent_boundary_original.py').read_bytes(),
 'parent-boundary.json':(P/'baseline-parent-boundary.json').read_bytes(),
 'preimages/personal_progress.GitLF.py':old_route,'preimages/security_headers.GitLF.py':old_header,
 'preimages/progress_retirement.before-ambient-fix.RAW.py':(P/'progress_retirement.route.before-ambient-fix.RAW.py').read_bytes(),
 'preimages/security_headers.after50.before-page.RAW.py':(P/'security_headers.after-sqlite50.before-SSR.RAW.py').read_bytes(),
 'inverse-and-historical-preservation.json':dump({'personal_progress_full_AST_inverse':True,'existing_function_assertions_unchanged':True,
    'security_headers_full_GitLF_inverse':True,'unchanged_database_auth_mfa_ci_helpers':protected_proof,
    'schema_revision':'20261019_personal_progress','no_DDL_or_target_mutation':True}),
}
phases={'before-entrypoints':(4,0,4,0), 'postgres-first':(10,10,0,0), 'postgres-failure-final':(4,4,0,0),
    'sqlite-delta-final':(52,52,0,0),'ambient-before':(2,1,1,0),'ambient-after':(10,10,0,0),
    'postgres-ambient-after':(2,2,0,0)}
phase_results={}
def structural(xml):
    cases=ET.fromstring(xml).findall('.//testcase')
    return [{'case':c.get('classname','')+'::'+c.get('name',''),'outcome':next((k for k in ['failure','error','skipped'] if c.find(k) is not None),'passed')} for c in cases]
for phase,expected in phases.items():
    folder=P/phase;raw=(folder/'results.xml').read_bytes();cases=structural(raw)
    observed=(len(cases),sum(c['outcome']=='passed' for c in cases),sum(c['outcome']=='failure' for c in cases),sum(c['outcome']=='error' for c in cases))
    assert observed==expected and not any(c['outcome']=='skipped' for c in cases)
    quiet=json.loads((folder/'quiet.json').read_bytes());assert quiet['exact'] and quiet['packages']==89 and quiet['pip_before']==quiet['pip_after']==0
    assert (folder/'before.json').read_bytes()==(folder/'after.json').read_bytes()
    phase_results[phase]={'cases':len(cases),'passed':observed[1],'failures':observed[2],'errors':observed[3],
        'original_xml_sha256':sha(raw),'quiet':quiet}
    for name in ['before.json','after.json','quiet.json','pip-before.raw.log','pip-after.raw.log']:
        public[phase+'/'+name]=(folder/name).read_bytes()
    public[phase+'/cases.STRUCTURAL.json']=dump(cases)
assert (P/'test_entrypoint_exact.py').read_bytes()==source['tests/test_progress_retirement_entrypoint_review.py']
public['same-entrypoint-canary.py']=(P/'test_entrypoint_exact.py').read_bytes()

early={}
for name in ['baseline-original','http-first','http-complete-first','sqlite-final-first']:
    raw=(P/(name+'.xml')).read_bytes();cases=structural(raw)
    early[name]={'cases':len(cases),'passed':sum(c['outcome']=='passed' for c in cases),
        'failures':sum(c['outcome']=='failure' for c in cases),'errors':sum(c['outcome']=='error' for c in cases),
        'xml_sha256':sha(raw),'pre_post_source_environment_snapshot_captured':False}
    public[name+'/cases.STRUCTURAL.json']=dump(cases)
assert early['http-complete-first']['passed']==28 and early['http-complete-first']['failures']==2 and early['http-complete-first']['errors']==0
assert early['sqlite-final-first']['passed']==50
public['early-phases.json']=dump({'observations':early,'erratum':'The first30 contain2 test failures (not pytest setup errors) caused by fixture invitation_token uniqueness in a shared module DB. Assertions stayed unchanged; later50 pass. No product defect or retrospective cause of any historical main broad run is asserted. Early phases do not claim unrecorded pre/post quiet. The initial seal driver incorrectly expected error tags and stopped before archive/public writes; its source is retained privately.'})

leases=[json.loads(p.read_bytes()) for p in (P/'leases').glob('*.json')]
assert len(leases)==4 and len({l['database'] for l in leases})==4
for lease in leases:
    assert lease['state']=='closed_absent' and lease['sessions_before_drop']==0
    assert lease['initial_creation']=='exclusive_xb_before_CREATE' and lease['absence_verified']=='fresh_control_connection'
    assert lease['launcher_birth_filetime']==lease['launcher_birth_after_CREATE']
public['resource-closure.json']=dump({'owned_only':leases,'scope':'Only these four attributed UUIDs; no claim about other catalog databases or historical unattributed residues.'})

# Archive only allowlisted reports/source/receipts, never directories with data.
private={}
for file in P.iterdir():
    if file.is_file() and file.suffix in {'.py','.json','.xml','.log','.ps1'}:
        private[file.name]=file.read_bytes()
for phase in phases:
    for file in (P/phase).iterdir():
        if file.is_file() and file.suffix in {'.json','.xml','.log'}:private[phase+'/'+file.name]=file.read_bytes()
for file in (P/'leases').glob('*.json'):private['leases/'+file.name]=file.read_bytes()
def acl(mode):
    run=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(P/'archive-acl.ps1'),'-Mode',mode,'-PrivateRoot',str(PRIVATE)],capture_output=True,timeout=30)
    write(P/('acl-'+mode+'.stdout.raw.log'),run.stdout);write(P/('acl-'+mode+'.stderr.raw.log'),run.stderr)
    assert run.returncode==0
    return json.loads(run.stdout.decode('utf-8-sig'))
create=acl('create');verify=acl('verify');archive=PRIVATE/'originals.zip';st=archive.stat();assert st.st_size==0
with archive.open('r+b') as file:
    opened=os.fstat(file.fileno());assert (opened.st_ino,opened.st_dev,opened.st_size)==(st.st_ino,st.st_dev,0)
    with zipfile.ZipFile(file,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,blob in sorted(private.items()):z.writestr(name,blob)
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist())==set(private) and len(z.namelist())==len(private)
    for name,blob in private.items():assert z.read(name)==blob
final=acl('final')
public['private-originals.json']=dump({'path':str(archive),'sha256':sha(archive.read_bytes()),'bytes':archive.stat().st_size,
    'exclusive_empty_creation_and_ACL_before_payload':True,'ACL_create':create,'ACL_verify':verify,'ACL_final':final,
    'members':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in private.items()},
    'excluded':'No SQLite/data files, caches, environment configuration, private profile contents or pytest temporary directories.'})
public['source.json']=dump({'parent':BASE,'sources':{n:{'RAW_sha256':sha(b),'GitLF_sha256':sha(b.replace(b'\r\n',b'\n'))} for n,b in source.items()},
    'phases':phase_results,'functional_SQLite50_separate':True,'PostgreSQL16_in_three_focal_batches':True,
    'no_bearer_mint_or_MFA_dependency_override_as_acceptance':True,'no_provider_mail_browser_VM_or_production':True,
    'wire_v1_RAW_sha256':sha((E/'wire-v1.md').read_bytes()),'security_and_QA_acceptance':'Pending independent review',
    'remaining':'Google-only/lost-all-factors require separate reviewed recovery. No general parent/auth relaxation. No attribution of any live incident.'})
public['review.md']=('''# Purpose-limited own retirement, author freeze

The two actual factory routes prove a password again, then consume an existing
active TOTP/recovery factor in the same transaction as minimal own metadata or
an exact append-only withdrawal. No token, profile, grant, role, session version
or general session is created. A separate confirmed actor admission and the
IP/account limiter precede the operation, so rollback/CAS cannot erase budgets.

The unchanged SEC diagnostic reproduces parentOFF401/401/source404. Four new
entrypoint criteria fail404 before and pass afterwards. Functional SQLite50
pass; final delta52 pass includes the exact four and unchanged MFA/export
privacy criteria. PG10+4+2 pass under restricted roles/pool1 on three UUIDs;
the fourth UUID belongs to the original diagnostic. All four receipts show
exclusive creation, sessions0, no FORCE and fresh independent absence checks.

An incidental foreign bearer caused API503 while Web200: preserved1red/1green.
The local wrapper now creates/closes its new Session under empty ContextVar and
restores the prior value in finally, including failure. The same criteria and
added malformed/expired/no-header, wrong-primary, existing-session and close
failure controls pass10; real PG2 checks actor isolation and clean pool reuse.
The SQL service itself did not change after the first14PG criteria. Earlier
run source snapshots are not retroactively claimed where not captured.

Only exact API paths/slashes and the separately developed public SSR page get
the fixed private policy. Wire v1 remains immutable. Google is explicitly
unavailable for this purpose because no persisted subject association exists;
this is not a claim of provider signature bypass or delivery/recovery operation.

No DDL/targets22..32/auth/MFA/global helper mutation. Existing router functions
have a complete AST inverse; header changes have a complete GitLF inverse.
The late-registration lint-only comment was added after delta52; its AST is
unchanged. Security/QA and composed UI acceptance remain pending.
''').encode()
scanner_file=P.parent/'metodobase-checkpoint119-prepare.py'
definition=next(n for n in ast.parse(scanner_file.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'exact-checkpoint119-scan','exec'))
public['scanner-source.json']=dump({'path':str(scanner_file),'sha256':sha(scanner_file.read_bytes()),'function_AST_unmodified':True})
for name,blob in public.items():scan(blob,name)
for path in E.rglob('*'):
    if path.is_file():scan(path.read_bytes(),path.relative_to(E).as_posix())
for name,blob in public.items():write(E/name,blob)
manifest={p.relative_to(E).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in E.rglob('*') if p.is_file()}
payload=dump({'files':manifest,'scanner119':'PASS','proof_RAW_attributes':'* -text created before first proof write'})
scan(payload,'manifest.json');write(E/'manifest.json',payload)
for name,blob in source.items():assert (R/name).read_bytes()==blob
for path in E.rglob('*'):
    if path.is_file():scan(path.read_bytes(),path.relative_to(E).as_posix())
write(P/'seal-result.json',dump({'manifest_sha256':sha(payload),'source_sha256':sha(public['source.json']),
    'files':len(manifest)+1,'private_originals_sha256':sha(archive.read_bytes()),'private_original_members':len(private)}))
print((P/'seal-result.json').read_text())
