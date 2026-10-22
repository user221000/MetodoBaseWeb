"""Finite source binding of the reviewed57 probe, preserving native functions."""
import ast, hashlib, json, re
from . import authority

def function_bytes(data):
    lines=data.decode('utf8').splitlines(keepends=True)
    return {node.name:''.join(lines[node.lineno-1:node.end_lineno]).encode('utf8')
        for node in ast.parse(data).body if isinstance(node,ast.FunctionDef)}

def bind(contract):
    validate_input_structure(contract)
    original=authority.raw('runtime_probe57-69d49.py.RAW')
    tree=ast.parse(original)
    assignments={n.targets[0].id:n for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
    if ast.literal_eval(assignments['EXPECTED_DISTS'].value)!=contract['distributions']:
        raise ValueError('Probe57 distribution authority differs')
    node=assignments['EXPECTED_APP']
    if node.lineno!=node.end_lineno:raise ValueError('Probe57 finite binding line differs')
    lines=original.decode('utf8').splitlines(keepends=True)
    line=lines[node.lineno-1];ending=line[len(line.rstrip('\r\n')):]
    lines[node.lineno-1]='EXPECTED_APP='+repr(contract['app_hashes'])+ending
    data=''.join(lines).encode('utf8')
    old=b'144c2a81362376e914bcfc490814b415f404c1d4'
    if data.count(old)!=1 or data.count(b'Exact current144R30 image')!=1:
        raise ValueError('Probe57 finite source labels differ')
    data=data.replace(old,contract['source'].encode('ascii')).replace(b'Exact current144R30 image',b'Exact explicit-source current57 image')
    mode_gate=("report['source_modes']={p.relative_to('/app').as_posix():format(stat.S_IMODE(p.stat().st_mode)|stat.S_IFREG,'o') for p in Path('/app').rglob('*') if p.is_file()}\n"
        +"assert report['source_modes']=="+repr(contract['app_modes'])+"\n")
    if data.count(b'print(json.dumps(report))')!=1:raise ValueError('Probe57 report framing differs')
    data=data.replace(b'print(json.dumps(report))',mode_gate.encode('utf8')+b'print(json.dumps(report))')
    if function_bytes(data)!=function_bytes(original):raise ValueError('Original native probe57 function bytes differ')
    compile(data,'bound-current57-probe.py','exec')
    return data

def require(condition,message):
    if not condition:raise ValueError(message)

def validate_input_structure(contract):
    from . import context
    require(type(contract) is dict and contract.get('schema')=='current-image57-input-v1','Current57 input contract absent')
    require(type(contract.get('source')) is str and re.fullmatch('[0-9a-f]{40}',contract['source']) is not None,'Current57 explicit source differs')
    original=ast.parse(authority.raw('runtime_probe57-69d49.py.RAW'))
    values={node.targets[0].id:ast.literal_eval(node.value) for node in original.body
            if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in {'EXPECTED_DISTS','MODULES'}}
    values['XML_CASES']=[ast.literal_eval(node.args[0]) for node in ast.walk(original)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name)
        and node.func.value.id=='cases' and node.func.attr=='append' and node.args and isinstance(node.args[0],ast.Constant)]
    require(contract.get('distributions')==values['EXPECTED_DISTS'] and len(contract['distributions'])==57,'Current57 dependency catalog differs')
    hashes=contract.get('app_hashes');modes=contract.get('app_modes')
    require(type(hashes) is dict and bool(hashes) and type(modes) is dict and set(modes)==set(hashes),'Current57 APP hash/mode inventory differs')
    for name,value in hashes.items():
        authority.canonical_name(name)
        require(name.startswith(context.APP_PREFIXES) or name in context.APP_FILES,'Current57 nonapplication path in APP inventory')
        require(type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None and modes[name] in {'100644','100755'},'Current57 APP byte/mode identity differs')
    require(set(context.CORPUS)<=hashes.keys() and hashes[context.CORPUS[3]]==context.CORPUS_SHA256
            and hashes[context.CORPUS[1]]==context.CORPUS_LICENSE_SHA256,'Current57 mandatory B19 corpus absent or changed')
    return values

def validate_report(report,contract):
    trusted=validate_input_structure(contract)
    require(type(report) is dict,'Image57 runtime report absent')
    require(report.get('status')=='PASS_RUNTIME_IMPORT_DIAGNOSTIC_ONLY','Image57 probe status differs')
    require(report.get('current_source_commit')==contract['source'],'Image57 runtime source differs')
    require(type(report.get('source_files_exact')) is int and report['source_files_exact']==len(contract['app_hashes']), 'Image57 source count differs')
    require(report.get('source_hashes')==contract['app_hashes'],'Image57 complete source hashes differ')
    require(report.get('source_modes')==contract['app_modes'],'Image57 complete source modes differ')
    require(type(report.get('uid')) is int and type(report.get('gid')) is int and report['uid']==report['gid']==999,'Image57 nonroot identity differs')
    require(report.get('distributions')==contract['distributions'] and len(report['distributions'])==57,'Image57 complete distribution inventory differs')
    require(type(report.get('current_runtime_distributions_expected')) is int and report['current_runtime_distributions_expected']==57,'Image57 typed inventory differs')
    imports=report.get('imports')
    require(type(imports) is dict and set(imports)==set(contract['distributions']),'Image57 complete import inventory differs')
    require(all(type(item) is dict and item.get('version')==contract['distributions'][name] and item.get('module')==trusted['MODULES'][name] for name,item in imports.items()),'Image57 import versions or modules differ')
    for key in ('pip_and_ensurepip_and_bundled_wheels_absent','build_tools_absent'):
        require(report.get(key) is True,'Image57 runtime exclusion postcondition absent')
    for key in ('complete_product_acceptance','application_startup_or_migrations_claimed','security_or_OS71_or_SCA_closure_claimed','SBOM_SCA_complete'):
        require(report.get(key) is False,'Image57 scope boundary differs')
    require(type(report.get('base_identity_files_unchanged')) is int and report['base_identity_files_unchanged']==218,'Image57 base identity inventory differs')
    cases=report.get('small_xml_cases')
    require(type(cases) is list and cases==trusted['XML_CASES'] and len(cases)==len(set(cases))==11,'Image57 bounded XML inventory differs')
    require(report.get('capi_capsule_name')=='pyexpat.expat_CAPI' and report.get('libpq_compile')==report.get('libpq_runtime')==170011,'Image57 native API identity differs')
    native=report.get('native')
    require(type(native) is dict and set(native)=={'pyexpat','elementtree','psycopg2'},'Image57 native inventory differs')
    for item in native.values():
        require(item.get('class_bits')==64 and item.get('machine')==62 and item.get('endian')=='little' and item.get('rpath')==item.get('runpath')==[], 'Image57 ELF or linkage differs')
        require(re.fullmatch('[0-9a-f]{64}',item.get('sha256','')) is not None and bool(item.get('ldd')) and 'not found' not in item['ldd'],'Image57 native digest or dynamic dependency differs')
    require(native['pyexpat']['exports']==['PyInit_pyexpat'] and native['pyexpat']['needed']==['libc.so.6'] and 'libpq.so.5' in native['psycopg2']['needed'],'Image57 native export or dependency boundary differs')
    provenance=report.get('expat_attestation',{})
    require(provenance.get('artifact_sha256')==native['pyexpat']['sha256'] and provenance.get('base_exports')==provenance.get('artifact_exports')==['PyInit_pyexpat'],'Image57 real Expat attestation differs')
    commands=provenance.get('compiler_commands',[])
    require(type(commands) is list and len(commands)==5 and all(type(c) is list and c for c in commands),'Image57 real compiler argv absent')
    require(all('-c' in command and '-fvisibility=hidden' in command and '-ffile-prefix-map=/expat-output=.' in command for command in commands[:4]) and '-c' not in commands[4] and '-shared' in commands[4],'Image57 compile/link commands differ')
    require(provenance.get('module_visibility_flags_selected')==['-fvisibility=hidden'],'Image57 selected visibility differs')
    require(provenance.get('interpreter_libpython_elementtree_config_headers_before')==provenance.get('interpreter_libpython_elementtree_config_headers_after') and len(provenance.get('interpreter_libpython_elementtree_config_headers_after',{}))==218,'Image57 full base identity attestation differs')
    compiled=provenance.get('compiled_source',{})
    require(len(compiled.get('after',{}))==31 and compiled.get('changed_source_files')==['Modules/expat/xmlparse.c'],'Image57 exact PSF input inventory differs')
    require(report.get('os_package_counts')=={'before_native':87,'after_native':97,'runtime':97} and len(report.get('os_packages',{}))==97 and len(report.get('native_runtime_additions',{}))==10,'Image57 measured OS inventory differs')
    components=report.get('native_components_measured',{})
    require(components.get('CPython',{}).get('version')=='3.12.15' and components['CPython'].get('SOABI')=='cpython-312-x86_64-linux-gnu','Image57 interpreter ABI differs')
    require(components.get('Expat',{}).get('reported_version')=='expat_2.8.5' and components['Expat'].get('source_patch')=='13c5f63' and components['Expat'].get('version_not_cosmetically_rewritten') is True,'Image57 real patched Expat identity differs')
    return {'source':contract['source'],'source_files':len(contract['app_hashes']),'distributions':57,'native_modules':3,'xml_cases':11,'runtime_import_diagnostic_only':True}

def validate_container(value,image_id,source,nonce):
    require(type(value) is dict and value.get('Image')==image_id,'Image57 exact runtime image differs')
    config=value.get('Config',{});host=value.get('HostConfig',{})
    require(config.get('User')=='999:999' and config.get('Labels',{}).get('metodobase.ci57.nonce')==nonce and config['Labels'].get('org.opencontainers.image.revision')==source,'Image57 container ownership differs')
    require(host.get('NetworkMode')=='none' and host.get('ReadonlyRootfs') is True and host.get('Privileged') is False,'Image57 network/filesystem boundary differs')
    require(host.get('CapDrop')==['ALL'] and not host.get('CapAdd') and 'no-new-privileges:true' in host.get('SecurityOpt',[]),'Image57 capabilities differ')
    require(host.get('Memory')==512*1024**2 and host.get('NanoCpus')==1000000000 and host.get('PidsLimit')==128,'Image57 runtime resource limits differ')
    require(not value.get('Mounts') and not host.get('Binds') and not host.get('PortBindings'),'Image57 unexpected host share or port')
    return value['Id']
