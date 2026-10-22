"""Bounded offline controls; synthetic report positives are not image acceptance."""
from pathlib import Path
import argparse, ast, copy, hashlib, io, json, os, struct, subprocess, sys, unittest, zipfile
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.ci_image57 import authority,context,probe,run,source_proof

ARTIFACT=None
SERIAL=0

def directory(label):
    global SERIAL
    SERIAL+=1
    path=ARTIFACT/(str(SERIAL)+'-'+label);path.mkdir()
    return path

def contract_and_report():
    tree=ast.parse(authority.raw('runtime_probe57-69d49.py.RAW'))
    values={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in {'EXPECTED_DISTS','MODULES'}}
    app={'web/example.py':'b'*64,**{name:'b'*64 for name in context.CORPUS}}
    app[context.CORPUS[3]]=context.CORPUS_SHA256;app[context.CORPUS[1]]=context.CORPUS_LICENSE_SHA256
    contract={'schema':'current-image57-input-v1','source':'a'*40,'app_hashes':app,
        'app_modes':{name:'100644' for name in app},'distributions':values['EXPECTED_DISTS'],'context_sha256':'b'*64}
    native={name:{'class_bits':64,'machine':62,'endian':'little','rpath':[],'runpath':[],
        'sha256':'c'*64,'ldd':'libc.so.6 => /lib/libc.so.6','exports':['PyInit_pyexpat'] if name=='pyexpat' else [],
        'needed':['libc.so.6'] if name!='psycopg2' else ['libpq.so.5']} for name in ('pyexpat','elementtree','psycopg2')}
    identities={'/bounded/'+str(i):'d'*64 for i in range(218)}
    report={'status':'PASS_RUNTIME_IMPORT_DIAGNOSTIC_ONLY','current_source_commit':contract['source'],
        'source_files_exact':len(app),'source_hashes':contract['app_hashes'].copy(),'source_modes':contract['app_modes'].copy(),
        'uid':999,'gid':999,'distributions':contract['distributions'].copy(),'current_runtime_distributions_expected':57,
        'imports':{name:{'version':version,'module':values['MODULES'][name]} for name,version in contract['distributions'].items()},
        'pip_and_ensurepip_and_bundled_wheels_absent':True,'build_tools_absent':True,'complete_product_acceptance':False,
        'application_startup_or_migrations_claimed':False,'security_or_OS71_or_SCA_closure_claimed':False,'SBOM_SCA_complete':False,
        'base_identity_files_unchanged':218,'small_xml_cases':[ast.literal_eval(node.args[0]) for node in ast.walk(tree)
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name)
            and node.func.value.id=='cases' and node.func.attr=='append' and node.args and isinstance(node.args[0],ast.Constant)],
        'capi_capsule_name':'pyexpat.expat_CAPI','libpq_compile':170011,'libpq_runtime':170011,'native':native,
        'expat_attestation':{'artifact_sha256':'c'*64,'base_exports':['PyInit_pyexpat'],'artifact_exports':['PyInit_pyexpat'],
            'compiler_commands':[['cc','-c','-fvisibility=hidden','-ffile-prefix-map=/expat-output=.'] for _ in range(4)]+[['cc','-shared']],
            'module_visibility_flags_selected':['-fvisibility=hidden'],'interpreter_libpython_elementtree_config_headers_before':identities.copy(),
            'interpreter_libpython_elementtree_config_headers_after':identities.copy(),'compiled_source':{'after':{str(i):'e'*64 for i in range(31)},'changed_source_files':['Modules/expat/xmlparse.c']}},
        'os_package_counts':{'before_native':87,'after_native':97,'runtime':97},'os_packages':{str(i):'1' for i in range(97)},
        'native_runtime_additions':{str(i):'1' for i in range(10)},
        'native_components_measured':{'CPython':{'version':'3.12.15','SOABI':'cpython-312-x86_64-linux-gnu'},
            'Expat':{'reported_version':'expat_2.8.5','source_patch':'13c5f63','version_not_cosmetically_rewritten':True}}}
    return contract,report

def cli(entry,contract,report,folder,suffix):
    c=folder/('contract-'+suffix+'.json');r=folder/('report-'+suffix+'.json')
    raw=json.dumps(contract).encode();c.write_bytes(raw);r.write_bytes(json.dumps(report).encode())
    value=subprocess.run([sys.executable,'-I','-B','-X','utf8',str(entry),'check-report','--contract',str(c),
        '--contract-sha256',hashlib.sha256(raw).hexdigest(),'--source',contract['source'],'--report',str(r)],capture_output=True)
    (folder/('cli-'+suffix+'.stdout.private')).write_bytes(value.stdout)
    (folder/('cli-'+suffix+'.stderr.private')).write_bytes(value.stderr)
    return value.returncode

def cli_canaries(entry,folder):
    contract,report=contract_and_report()
    if cli(entry,contract,report,folder,'positive')!=0:raise ValueError('Actual checker CLI rejects bounded valid structural report')
    bads=[{},dict(report,uid=True),dict(report,source_hashes={}),dict(report,source_modes={}),dict(report,distributions={}),dict(report,base_identity_files_unchanged=0)]
    for index,bad in enumerate(bads):
        if cli(entry,contract,bad,folder,'negative-'+str(index))==0:raise ValueError('Actual checker CLI false success')

def merkle_fixture(folder):
    blobs={'Dockerfile':b'FROM scratch\nCOPY web /app/web\n','.dockerignore':b'docs\n',
           'web/a.py':b'bounded source\n','web/nested/run.sh':b'#!/bin/sh\nexit 0\n'}
    objects={}
    def add(kind,payload):
        oid=source_proof.object_id(kind,payload);objects[oid]=(kind,payload);return oid
    def tree(rows):
        return add('tree',b''.join(mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(oid) for mode,name,oid in rows))
    blob_ids={name:source_proof.object_id('blob',raw) for name,raw in blobs.items()}
    nested=tree([('100755','run.sh',blob_ids['web/nested/run.sh'])])
    web=tree([('100644','a.py',blob_ids['web/a.py']),('40000','nested',nested)])
    root=tree([('100644','.dockerignore',blob_ids['.dockerignore']),('100644','Dockerfile',blob_ids['Dockerfile']),('40000','web',web)])
    commit=add('commit',('tree '+root+'\n\nbounded fixture\n').encode())
    records={name:{'mode':'100755' if name.endswith('.sh') else '100644','git_blob':blob_ids[name]} for name in blobs}
    def close(path,values):
        with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as output:
            for oid,(kind,payload) in sorted(values.items()):output.writestr('objects/'+oid,source_proof.frame(kind,payload))
    path=folder/'source-objects.zip';close(path,objects)
    return path,commit,records,blobs['Dockerfile'],objects,close

class Offline57(unittest.TestCase):
    def test_01_original_byte_authorities(self):
        for name in authority.PINS:self.assertTrue(authority.raw(name))
        from tests.ci_web37.git_recipe import load
        self.assertEqual(len(load().objects),21)

    def test_02_bound_probe_functions_raw_unchanged(self):
        contract,_=contract_and_report();bound=probe.bind(contract)
        self.assertEqual(probe.function_bytes(bound),probe.function_bytes(authority.raw('runtime_probe57-69d49.py.RAW')))
        self.assertIn(b"report['source_modes']",bound)
        self.assertIn(contract['source'].encode(),bound)

    def test_03_complete_synthetic_structural_report(self):
        contract,report=contract_and_report();self.assertEqual(probe.validate_report(report,contract)['distributions'],57)

    def test_04_meaningful_report_mutants(self):
        contract,report=contract_and_report()
        mutants=[dict(report,uid=True),dict(report,current_source_commit='f'*40),dict(report,source_modes={}),
            dict(report,source_files_exact=True),dict(report,imports={}),dict(report,small_xml_cases=['same']*11),
            dict(report,build_tools_absent=False),dict(report,SBOM_SCA_complete=True)]
        for field in ('base_identity_files_unchanged','pip_and_ensurepip_and_bundled_wheels_absent','current_runtime_distributions_expected'):
            value=copy.deepcopy(report);del value[field];mutants.append(value)
        value=copy.deepcopy(report);value['expat_attestation']['compiler_commands']=[];mutants.append(value)
        value=copy.deepcopy(report);value['native']['pyexpat']['exports']=['PyInit_pyexpat','XML_Parse'];mutants.append(value)
        value=copy.deepcopy(report);value['expat_attestation']['compiled_source']['after'].pop('0');mutants.append(value)
        value=copy.deepcopy(report);value['imports']['psycopg2']['module']='different_module';mutants.append(value)
        value=copy.deepcopy(report);value['small_xml_cases'][0]='different_unproven_action';mutants.append(value)
        for i,value in enumerate(mutants):
            with self.subTest(index=i),self.assertRaises((ValueError,KeyError,TypeError)):probe.validate_report(value,contract)

    def test_05_real_cli_positive_and_negatives(self):
        cli_canaries(ROOT/'tests/run_current_image57.py',directory('checker'))

    def test_06_main_false_success_mutant_detected(self):
        target=directory('main-mutant')
        (target/'tests/ci_image57').mkdir(parents=True)
        (target/'tests/__init__.py').write_bytes(b'')
        for source in (ROOT/'tests/ci_image57').glob('*.py'):(target/'tests/ci_image57'/source.name).write_bytes(source.read_bytes())
        entry=target/'tests/run_current_image57.py';entry.write_bytes((ROOT/'tests/run_current_image57.py').read_bytes())
        path=target/'tests/ci_image57/check_report.py';tree=ast.parse(path.read_bytes())
        selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main'];self.assertEqual(len(selected),1)
        selected[0].body=[ast.Return(value=ast.Constant(value=0))]
        path.write_text(ast.unparse(ast.fix_missing_locations(tree))+'\n',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'false success'):cli_canaries(entry,directory('mutant-cli-results'))

    def test_07_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):context.json_object(b'{"uid":999,"uid":0}')

    def test_08_path_rejections(self):
        for name in ('.','../x','/absolute','docs//x','web/x.','web/CON.txt','web/COM0','web/x:y','web/a\\b','web/x\x00'):
            with self.subTest(name=name),self.assertRaises(ValueError):authority.canonical_name(name)

    def test_09_corpus_actual_shape_and_mutants(self):
        payload=b'a'*32+b'b'*32;license_raw=b'bounded-license'
        value={'format':'sorted-unique-sha256-digests-32-byte-records','unique_digests':2,'payload_bytes':64,
            'payload_sha256':hashlib.sha256(payload).hexdigest(),'license_sha256':hashlib.sha256(license_raw).hexdigest()}
        self.assertEqual(context.validate_corpus(value,payload,license_raw,b'*.sha256bin -text\n')['unique_digests'],2)
        for data in (payload[:-1],payload[::-1],b'a'*64):
            changed=dict(value,payload_sha256=hashlib.sha256(data).hexdigest(),payload_bytes=len(data))
            with self.assertRaises(ValueError):context.validate_corpus(changed,data,license_raw,b'*.sha256bin -text\n')
        with self.assertRaises(ValueError):context.validate_corpus(value,payload,license_raw,b'*.sha256bin text\n')

    def test_10_source_ack_requires_full_commit(self):
        with context.git_policy(),self.assertRaises(ValueError):context.check_source(ROOT,'HEAD')

    def test_11_git_environment_restored(self):
        original=dict(os.environ)
        with context.git_policy():self.assertEqual(os.environ['GIT_NO_REPLACE_OBJECTS'],'1')
        self.assertEqual(dict(os.environ),original)

    def test_12_container_boundary_rejections(self):
        row={'Id':'1'*64,'Image':'sha256:'+'2'*64,'Config':{'User':'999:999','Labels':{'metodobase.ci57.nonce':'owned','org.opencontainers.image.revision':'a'*40}},
            'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,'CapDrop':['ALL'],'CapAdd':None,
                'SecurityOpt':['no-new-privileges:true'],'Memory':512*1024**2,'NanoCpus':1000000000,'PidsLimit':128,'Binds':None,'PortBindings':None},'Mounts':[]}
        self.assertEqual(probe.validate_container(row,row['Image'],'a'*40,'owned'),row['Id'])
        for key,value in [('NetworkMode','bridge'),('ReadonlyRootfs',False),('CapAdd',['NET_ADMIN']),('Memory',0),('Privileged',True),('Binds',['/var/run/docker.sock:/var/run/docker.sock'])]:
            changed=copy.deepcopy(row);changed['HostConfig'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):probe.validate_container(changed,row['Image'],'a'*40,'owned')

    def test_13_source_merkle_consumer_without_Git(self):
        folder=directory('source-proof');path,source,records,docker,objects,close=merkle_fixture(folder)
        with patch.object(subprocess,'check_output',side_effect=AssertionError('Consumer invoked Git')):
            checked=source_proof.verify(path,source,records,docker)
        self.assertEqual(checked['objects'],len(objects));self.assertFalse(checked['consumer_Git_required'])
        variants=[]
        changed=copy.deepcopy(records);changed.pop('web/a.py');variants.append((source,changed,docker))
        changed=copy.deepcopy(records);changed['web/a.py']['mode']='100755';variants.append((source,changed,docker))
        variants.append(('f'*40,records,docker));variants.append((source,records,b'FROM scratch\nCOPY web/a.py /app/a.py\n'))
        for revision,rows,recipe in variants:
            with self.assertRaises(ValueError):source_proof.verify(path,revision,rows,recipe)
        missing=dict(objects);missing.pop(next(oid for oid,(kind,payload) in objects.items() if kind=='tree'))
        short=folder/'missing.zip';close(short,missing)
        with self.assertRaises(ValueError):source_proof.verify(short,source,records,docker)
        extra=dict(objects);extra[source_proof.object_id('tree',b'')]=('tree',b'')
        extra_path=folder/'unreachable.zip';close(extra_path,extra)
        with self.assertRaises(ValueError):source_proof.verify(extra_path,source,records,docker)

    def test_14_B19_identity_is_mandatory(self):
        actual=context.json_object((ROOT/context.CORPUS[2]).read_bytes());context.require_current_corpus(actual)
        for key,value in [('payload_sha256','0'*64),('unique_digests',2),('payload_bytes',True),('license_sha256','0'*64)]:
            changed=dict(actual);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):context.require_current_corpus(changed)
        contract,report=contract_and_report();folder=directory('contract-cli')
        altered=[]
        value=copy.deepcopy(contract);value['app_hashes'].pop(context.CORPUS[3]);value['app_modes'].pop(context.CORPUS[3]);altered.append(value)
        value=copy.deepcopy(contract);value['source']='HEAD';altered.append(value)
        value=copy.deepcopy(contract);value['distributions']['psycopg2']='0.0.0';altered.append(value)
        for index,value in enumerate(altered):
            changed=copy.deepcopy(report);changed['current_source_commit']=value['source']
            changed['source_hashes']=value['app_hashes'];changed['source_modes']=value['app_modes'];changed['source_files_exact']=len(value['app_hashes'])
            changed['distributions']=value['distributions']
            self.assertNotEqual(cli(ROOT/'tests/run_current_image57.py',value,changed,folder,str(index)),0)

    def test_15_no_Docker_call_before_closed_context_guard(self):
        contract,_=contract_and_report()
        with patch.object(run,'prepare_context_directory',side_effect=ValueError('Synthetic closed-context rejection')),patch.object(subprocess,'check_output') as child:
            with self.assertRaisesRegex(ValueError,'closed-context'):run.build_probe(directory('bad-context'),contract,'docker','metodobase-ci57:bounded')
            child.assert_not_called()

    def test_16_first_build_failure_is_not_retried(self):
        folder=directory('build-failure');contract,_=contract_and_report()
        with patch.object(run,'prepare_context_directory',return_value=folder),patch.object(subprocess,'check_output',return_value=b''),patch.object(subprocess,'run',return_value=SimpleNamespace(returncode=7)) as child:
            with self.assertRaisesRegex(ValueError,'first build failed'):run.build_probe(folder,contract,'docker','metodobase-ci57:bounded')
            self.assertEqual(child.call_count,1)
            command=child.call_args.args[0]
            self.assertIn('--pull=false',command);self.assertIn('--platform=linux/amd64',command)
            self.assertNotIn('--rm',command)
        self.assertTrue((folder/'docker-build.private.log').is_file())

    def test_17_complete_simulated_build_probe_process_contract(self):
        folder=directory('simulated-build-probe');contract,report=contract_and_report()
        nonce='1'*32;image='sha256:'+'2'*64;container='3'*64;commands=[]
        inspected={'Id':container,'Image':image,'Config':{'User':'999:999','Labels':{'metodobase.ci57.nonce':nonce,'org.opencontainers.image.revision':contract['source']}},
            'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,'CapDrop':['ALL'],'CapAdd':None,'SecurityOpt':['no-new-privileges:true'],
                          'Memory':512*1024**2,'NanoCpus':1000000000,'PidsLimit':128,'Binds':None,'PortBindings':None},'Mounts':[],'State':{'Running':False,'ExitCode':0}}
        def checked(command,**kwargs):
            commands.append(command)
            if command[1:4]==['image','ls','--quiet']:return b''
            if command[1:3]==['image','inspect']:return json.dumps([{'Id':image,'Config':{'Labels':inspected['Config']['Labels']}}]).encode()
            if command[1]=='create':return (container+'\n').encode()
            if command[1:3]==['container','inspect']:return json.dumps([inspected]).encode()
            raise AssertionError('Unexpected simulated Docker command')
        def child(command,**kwargs):
            commands.append(command)
            if command[1]=='build':Path(command[command.index('--iidfile')+1]).write_text(image,encoding='ascii')
            elif command[1]=='start':kwargs['stdout'].write(json.dumps(report).encode())
            else:raise AssertionError('Unexpected simulated child')
            return SimpleNamespace(returncode=0)
        with patch.object(run,'prepare_context_directory',return_value=folder),patch.object(run.uuid,'uuid4',return_value=SimpleNamespace(hex=nonce)),patch.object(subprocess,'check_output',side_effect=checked),patch.object(subprocess,'run',side_effect=child):
            result=run.build_probe(folder,contract,'docker','metodobase-ci57:bounded')
        self.assertEqual(result['image_id'],image);self.assertEqual(result['runtime_probes_attempted'],1)
        self.assertTrue(result['container_retained_without_rm']);self.assertFalse(result['application_started'])
        create=next(command for command in commands if command[1]=='create')
        self.assertEqual(create[create.index('--network')+1],'none');self.assertIn('--read-only',create)
        self.assertNotIn('--rm',create);self.assertEqual(sum(command[1]=='build' for command in commands),1)

    def test_18_publication_tokens_and_expanded_ZIP(self):
        scan=authority.publication();scan(b'bounded public projection')
        two=b'A'*24+b'.'+b'B'*24
        csrf=b'1234567890.'+b'a'*64+b'.'+b'b'*64
        for value in (two,csrf,b'otpauth://synthetic'):
            with self.assertRaises(ValueError):scan(value)
        def archive(value):
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as closed:closed.writestr('bounded.txt',value)
            return out.getvalue()
        scan(archive(b'bounded safe text'))
        with self.assertRaises(ValueError):scan(archive(two))
        # Advertise an oversized expanded member; reject before allocation/read.
        expanded=bytearray(archive(b'x'));central=expanded.index(b'PK\x01\x02')
        struct.pack_into('<I',expanded,central+24,32*1024**2+1)
        with self.assertRaisesRegex(ValueError,'Expanded ZIP'):scan(bytes(expanded))

if __name__=='__main__':
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--artifact-root',type=Path,required=True);args=parser.parse_args()
    ARTIFACT=authority.regular_directory(args.artifact_root)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Offline57))
    (ARTIFACT/'unit-result.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'synthetic_report_positive_scope':'Parser structure only, not image runtime','Docker_VM_or_product_executed':False})+'\n',encoding='utf8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
