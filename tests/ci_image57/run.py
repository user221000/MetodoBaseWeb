"""Explicit current57 context/build/probe phases; no services or product startup."""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, stat, subprocess, sys, tarfile, uuid
from . import authority,context,probe

def digest(path):
    with path.open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()

def prepare_context_directory(private,contract):
    manifest,records=context.validate_contract(private,contract)
    target=private/'docker-context';target.mkdir(mode=0o700)
    with tarfile.open(private/'source-context.tar','r:') as archive:
        for member in archive.getmembers():
            path=target/authority.canonical_name(member.name)
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as writer,archive.extractfile(member) as reader:shutil.copyfileobj(reader,writer)
            path.chmod(int(records[member.name]['mode'],8)&0o777)
            if digest(path)!=records[member.name]['raw_sha256']:raise ValueError('Docker context extraction readback differs')
    return target

def build_probe(private,contract,docker,tag):
    # This function is implemented for a later explicit CI/runtime lease.
    # Offline verification never invokes it or a Docker executable.
    nonce=uuid.uuid4().hex
    tag=tag or 'metodobase-ci57:'+contract['source'][:12]+'-'+nonce[:12]
    if re.fullmatch(r'metodobase-ci57:[a-z0-9][a-z0-9_.-]{0,100}',tag) is None:raise ValueError('Current57 owned tag required')
    def call(*args):return subprocess.check_output([docker,*args])
    target=prepare_context_directory(private,contract);iid=private/'runtime.iid'
    if call('image','ls','--quiet','--no-trunc',tag).strip():raise ValueError('Owned image tag already exists; no retry')
    command=[docker,'build','--pull=false','--platform=linux/amd64','--target','runtime','--iidfile',str(iid),
        '--label','org.opencontainers.image.revision='+contract['source'],'--label','metodobase.ci57.nonce='+nonce,'-t',tag,str(target)]
    with (private/'docker-build.private.log').open('xb') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        log.flush();os.fsync(log.fileno())
    if result.returncode:raise ValueError('Current57 first build failed; preserved, no retry')
    image_id=iid.read_text(encoding='ascii').strip()
    if re.fullmatch('sha256:[0-9a-f]{64}',image_id) is None:raise ValueError('Actual immutable image identity absent')
    inspect_raw=call('image','inspect',image_id);(private/'image-inspect.private.json').write_bytes(inspect_raw)
    inspect=context.json_object(inspect_raw)
    if (type(inspect) is not list or len(inspect)!=1 or inspect[0]['Id']!=image_id
            or inspect[0]['Config']['Labels']['org.opencontainers.image.revision']!=contract['source']
            or inspect[0]['Config']['Labels']['metodobase.ci57.nonce']!=nonce):raise ValueError('Actual built image source/ownership differs')
    bound=probe.bind(contract);(private/'bound-runtime-probe57.raw.py').write_bytes(bound)
    name='metodobase-ci57-'+nonce
    authority.evidence()['write'](private/'runtime-ownership.private.json',
        {'nonce':nonce,'image_id':image_id,'tag':tag,'source':contract['source'],'container_name':name,
         'automatic_retry_or_cleanup':False})
    container_id=call('create','--interactive','--name',name,'--network','none','--read-only','--user','999:999',
        '--cap-drop','ALL','--security-opt','no-new-privileges:true','--memory','512m','--cpus','1','--pids-limit','128',
        '--env','PYTHONDONTWRITEBYTECODE=1','--label','metodobase.ci57.nonce='+nonce,
        '--label','org.opencontainers.image.revision='+contract['source'],'--entrypoint','python',image_id,'-').decode('ascii').strip()
    if re.fullmatch('[0-9a-f]{64}',container_id) is None:raise ValueError('Owned container identity absent')
    (private/'container-id.private.txt').write_text(container_id+'\n',encoding='ascii')
    before=call('container','inspect',container_id);(private/'container-before.private.json').write_bytes(before)
    before_value=context.json_object(before)
    if type(before_value) is not list or len(before_value)!=1:raise ValueError('Actual container inspect inventory differs')
    if probe.validate_container(before_value[0],image_id,contract['source'],nonce)!=container_id:raise ValueError('Owned container ID differs')
    with (private/'runtime-report.private.json').open('xb') as report,(private/'runtime-stderr.private.log').open('xb') as errors:
        result=subprocess.run([docker,'start','--attach','--interactive',container_id],input=bound,stdout=report,stderr=errors)
    after=call('container','inspect',container_id);(private/'container-after.private.json').write_bytes(after)
    after_value=context.json_object(after)
    if type(after_value) is not list or len(after_value)!=1:raise ValueError('Completed container inventory differs')
    probe.validate_container(after_value[0],image_id,contract['source'],nonce)
    if result.returncode or after_value[0]['State']['Running'] is not False or after_value[0]['State']['ExitCode']!=0:
        raise ValueError('Current57 first runtime probe failed; retained container and RAW, no retry')
    checked=probe.validate_report(context.json_object((private/'runtime-report.private.json').read_bytes()),contract)
    return checked|{'image_id':image_id,'tag':tag,'container_id':container_id,'builds_attempted':1,'runtime_probes_attempted':1,
        'probe_sha256':hashlib.sha256(bound).hexdigest(),'source_context_sha256':contract['context_sha256'],
        'source_commit':contract['source'],'application_started':False,'SBOM_SCA_complete':False,
        'container_retained_without_rm':True,'historical_image_or_cache_pruned':False}

def main(argv=None):
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--source',required=True)
    parser.add_argument('--private-root',type=Path,required=True)
    parser.add_argument('--public-root',type=Path,required=True)
    phases=parser.add_mutually_exclusive_group(required=True)
    phases.add_argument('--prepare-only',action='store_true')
    phases.add_argument('--build-probe',action='store_true')
    parser.add_argument('--docker',default='docker')
    parser.add_argument('--tag')
    args=parser.parse_args(argv)
    authority.regular_directory(args.repository)
    authority.regular_directory(args.public_root.parent)
    if (not args.public_root.is_absolute() or args.public_root.exists()
            or args.public_root.resolve().is_relative_to(args.repository.resolve())
            or args.public_root.resolve().is_relative_to(args.private_root.resolve())):
        raise ValueError('Fresh public root must be outside repository and private evidence')
    contract,acl=context.prepare(args.repository,args.source,args.private_root)
    bound=probe.bind(contract)
    (args.private_root/'prepared-runtime-probe57.raw.py').write_bytes(bound)
    if args.prepare_only:
        result={'scope':'Offline current57 source context and unchanged native probe preparation only',
            'source':args.source,'source_context_sha256':contract['context_sha256'],'context_files':contract['context_files'],
            'app_files':len(contract['app_hashes']),'distributions':57,'native_inputs':12,'native_merkle_objects':21,
            'bound_probe_sha256':hashlib.sha256(bound).hexdigest(),'image_built':False,'runtime_probe_executed':False,
            'final_candidate_source_pin':False,'SBOM_SCA_complete':False}
    else:result=build_probe(args.private_root,contract,args.docker,args.tag)
    evidence=authority.evidence();evidence['seal'](args.private_root,args.public_root,result,acl)
    print(json.dumps(result))
    return 0
