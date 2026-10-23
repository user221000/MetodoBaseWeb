"""Seven inert metadata borders; no authentic context, process, SSH or VM."""
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy
import hashlib
import inspect
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.ci_image57 import authority, preflight as p


class Current57PreflightOffline(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='metodobase-current57-preflight-inert-')
        self.addCleanup(temporary.cleanup)
        self.base=authority.private_directory(Path(temporary.name)/'private',ROOT)
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(p,'E_HOME',self.base))
        self.stack.enter_context(patch.object(p,'HISTORICAL_TEMP',self.base/'historical-temp'))
        self.folder=self.base/'context';self.folder.mkdir()
        self.lab=self.base/'model-lab';(self.lab/'instance').mkdir(parents=True);(self.lab/'scripts').mkdir()
        self.stack.enter_context(patch.object(p,'LAB',self.lab))
        self.source='a'*40
        self.manifest={'source_commit':self.source,'archive_sha256':hashlib.sha256(b'INERT_NOT_A_TAR').hexdigest()}
        self.contract={'source':self.source,'context_sha256':self.manifest['archive_sha256']}
        self.records={'web/model.py':{'raw_sha256':'d'*64,'mode':'100644'}}
        raws={'runtime-input-contract.json':json.dumps(self.contract).encode(),
            'source-manifest.json':json.dumps(self.manifest).encode(),
            'source-context.tar':b'INERT_NOT_A_TAR','source-objects.zip':b'INERT_NOT_A_PROOF'}
        for name,raw in raws.items():
            p.write_raw(self.folder/name,raw)
        self.args=SimpleNamespace(source=self.source,input_contract=self.folder/'runtime-input-contract.json',
            contract_sha256=hashlib.sha256(raws['runtime-input-contract.json']).hexdigest(),
            context_manifest=self.folder/'source-manifest.json',manifest_sha256=hashlib.sha256(raws['source-manifest.json']).hexdigest(),
            context_sha256=self.manifest['archive_sha256'],lease=self.base/'lease.json',lease_sha256='e'*64,
            private=self.base/'observation',output=self.base/'public',authorized_read_only_preflight=True)
        self.state={'pid':123,'nonce':'c'*40,'command':[str(self.base/'qemu-model.exe'),'-accel','tcg,thread=multi'],
            'overlay':str(self.base/'overlay-model.qcow2'),
            'resources':{'vcpus':2,'memory_mib':2048,'acceleration':'tcg,thread=multi'}}
        self.state_raw=json.dumps(self.state).encode();p.write_raw(self.lab/'instance/state.json',self.state_raw)
        now=datetime.now(timezone.utc)
        self.lease={'schema':'current57-readonly-lease-v1','source':self.source,
            'input_contract_sha256':self.args.contract_sha256,'manifest_sha256':self.args.manifest_sha256,
            'context_sha256':self.args.context_sha256,'state_sha256':hashlib.sha256(self.state_raw).hexdigest(),
            'lab_helpers':p.LAB_HELPERS.copy(),'generation':'b'*32,
            'issued_utc':(now-timedelta(minutes=1)).isoformat(),'expires_utc':(now+timedelta(minutes=10)).isoformat(),
            'pid':123,'birth_filetime':123456789,'executable':self.state['command'][0],
            'exe_sha256':'f'*64,'argv':self.state['command'].copy(),'nonce':self.state['nonce'],
            'overlay':{'path':self.state['overlay'],'volume':7,'inode':8}}
        raw=json.dumps(self.lease).encode();p.write_raw(self.args.lease,raw)
        self.args.lease_sha256=hashlib.sha256(raw).hexdigest()

    def validator(self):
        return patch.object(p.context,'validate_contract',return_value=(self.manifest,self.records))

    def facts(self):
        return {'system':'Linux','machine':'x86_64','free_bytes':4*1024**3,
            'mem_available_KiB':1500*1024,'running_containers':[],'cached_native_image_id':p.CACHE_ID,
            'lab_nonce':self.state['nonce'],'source_transferred':False,'image_built':False}

    def model_execution(self,*,facts=None,identity_error=False,returncode=0):
        """Only explicit inert ports; no original LAB helper/native transport runs."""
        events=[];owner=self
        class Identity:
            def __init__(self,lease):
                owner.assertEqual(lease,owner.lease);events.append('handle-open')
            def __enter__(self):return self
            def verify(self,process):
                events.append('identity')
                if identity_error:raise ValueError('INERT_IDENTITY_REJECTED')
                owner.assertEqual(process,{'inert_process':True})
            def __exit__(self,*_):events.append('handle-close')
        def remote(command,*,stdin,timeout):
            events.append('remote-inert')
            self.assertEqual(command,'python3 -');self.assertEqual(timeout,45);self.assertEqual(stdin.read(),p.REMOTE)
            return SimpleNamespace(returncode=returncode,stdout=json.dumps(facts or self.facts()).encode(),stderr=b'INERT_DIAGNOSTIC')
        def load(name):
            events.append('load-'+name)
            if name=='lab_control':return SimpleNamespace(process_identity=lambda state:{'inert_process':True})
            return SimpleNamespace(run=remote)
        original=p.file_snapshot
        def snapshot(path,*,limit):
            if Path(path).parent==self.lab/'scripts':
                return b'INERT_HELPER_METADATA_ONLY',{'sha256':p.LAB_HELPERS[Path(path).stem],'metadata':('inert',)}
            return original(path,limit=limit)
        def seal(private,public,result,acl):
            events.append('seal-inert')
            public.mkdir();p.write_raw(public/'summary.json',json.dumps(result).encode())
            return result
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(self.validator())
        stack.enter_context(patch.object(p,'WindowsIdentity',Identity))
        stack.enter_context(patch.object(p,'load',side_effect=load))
        stack.enter_context(patch.object(p,'file_snapshot',side_effect=snapshot))
        stack.enter_context(patch.object(p.authority,'evidence',return_value={
            'boundary_before_payload':lambda private:'INERT_BOUNDARY_PORT_ONLY','seal':seal}))
        return events

    def test_I01_explicit_source_and_all_root_pins(self):
        with self.validator() as validator:
            checked=p.validate_inputs(self.args)
            self.assertEqual(checked[0],self.contract);validator.assert_called_once_with(self.folder,self.contract)
        for field,bad in [('source','HEAD'),('source','A'*40),('contract_sha256','0'*64),
                          ('manifest_sha256','0'*64),('context_sha256','0'*64)]:
            args=copy.copy(self.args);setattr(args,field,bad)
            with self.subTest(field=field,bad=bad),self.validator(),self.assertRaises(ValueError):p.validate_inputs(args)

    def test_I02_closed_current_validator_is_mandatory_without_git(self):
        with (self.validator() as validator,patch.object(subprocess,'run',side_effect=AssertionError('NO_PROCESS')),
                patch.object(subprocess,'check_output',side_effect=AssertionError('NO_PROCESS'))):
            _,_,records,_=p.validate_inputs(self.args)
            self.assertEqual(len(records),1);validator.assert_called_once()
        with (patch.object(p.context,'validate_contract',side_effect=ValueError('INERT_BAD_CORPUS_OR_MEMBERSHIP')),
                self.assertRaisesRegex(ValueError,'INERT_BAD_CORPUS')):p.validate_inputs(self.args)

    def test_I03_private_path_alias_and_absence_errors(self):
        p.roots(self.args,self.folder,self.args.lease)
        parent=authority.private_directory(self.base/'overlap-model',ROOT)
        args=copy.copy(self.args);args.private=parent/'private';args.output=self.base/'other-public'
        with self.assertRaisesRegex(ValueError,'Evidence roots overlap'):p.roots(args,parent,args.lease)
        (self.base/'historical-temp').mkdir()
        with self.assertRaises(ValueError):p.e_path(self.base/'historical-temp'/'new')
        source=self.folder/'runtime-input-contract.json';alias=self.folder/'same-file.json'
        os.link(source,alias)
        with self.assertRaises(ValueError):p.e_path(source,file=True)
        with patch.object(Path,'lstat',side_effect=PermissionError('INERT_METADATA_DENIED')),self.assertRaises(PermissionError):p.absent(self.base/'missing')

    def test_I04_exact_seventeen_field_lease_and_bounded_authority(self):
        self.assertEqual(len(p.LEASE_KEYS),17)
        p.validate_lease(self.lease,self.args,self.state_raw,self.state)
        mutants=[]
        for key in p.LEASE_KEYS:
            value=copy.deepcopy(self.lease);del value[key];mutants.append(value)
        for key,bad in [('pid',True),('pid',123.0),('birth_filetime',True),('birth_filetime',123456789.0),
                        ('generation','B'*32),('nonce','c'*32),('state_sha256','0'*64),('argv',['foreign']),('expires_utc','2000-01-01T00:00:00Z'),
                        ('issued_utc','2020-01-01T00:00:00'),('exe_sha256','F'*64)]:
            value=copy.deepcopy(self.lease);value[key]=bad;mutants.append(value)
        value=copy.deepcopy(self.lease);value['overlay']['inode']=8.0;mutants.append(value)
        value=copy.deepcopy(self.lease);value['overlay']['volume']=True;mutants.append(value)
        value=copy.deepcopy(self.lease);value['extra']=False;mutants.append(value)
        value=copy.deepcopy(self.lease);value['expires_utc']=(datetime.now(timezone.utc)+timedelta(hours=5)).isoformat();mutants.append(value)
        for index,value in enumerate(mutants):
            with self.subTest(index=index),self.assertRaises((ValueError,KeyError,TypeError)):p.validate_lease(value,self.args,self.state_raw,self.state)
        native=inspect.getsource(p.WindowsIdentity)
        for term in ('OpenProcess','GetProcessId','GetProcessTimes','QueryFullProcessImageNameW','WaitForSingleObject','GetFileInformationByHandle','CommandLineToArgvW'):
            self.assertIn(term,native)
        self.assertNotIn("digest(overlay)",native)

    def test_I05_guest_resource_and_state_limits_preserved(self):
        self.assertEqual(p.validate_guest(self.facts())['free_bytes'],4*1024**3)
        for key,bad in [('free_bytes',2499*1024**2),('free_bytes',True),('mem_available_KiB',True),
                        ('mem_available_KiB',1024**2-1),('running_containers',['foreign']),('machine','aarch64'),('cached_native_image_id','foreign')]:
            value=self.facts();value[key]=bad
            with self.subTest(key=key,bad=bad),self.assertRaises(ValueError):p.validate_guest(value)
        state=copy.deepcopy(self.state);state['resources']['memory_mib']=2048.0
        raw=json.dumps(state).encode();lease=copy.deepcopy(self.lease);lease['state_sha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):p.validate_lease(lease,self.args,raw,state)
        self.assertFalse(p.EXTERNAL_PREREQUISITES['measured_by_this_runner'])

    def test_I06_identity_precedes_one_inert_remote_and_spans_response(self):
        events=self.model_execution()
        result=p.execute(self.args)
        self.assertEqual(events,['handle-open','load-lab_control','identity','load-guest_access','remote-inert','identity','handle-close','seal-inert'])
        self.assertFalse(result['native_QEMU_generation_claimed'])
        self.assertEqual(result['Root_lease_generation'],self.lease['generation'])
        self.assertEqual((self.args.private/'remote-readonly.py').read_bytes(),p.REMOTE)
        for key in ('VM_started_by_this_runner','source_transferred','image_built','SQL_Redis_Chrome_started','build_authorized','SBOM_SCA_complete'):
            self.assertIs(result[key],False)
        self.assertNotIn('nonce',result);self.assertNotIn('argv',result)

    def test_I07_failure_retention_projection_and_cli_rejection(self):
        events=self.model_execution(identity_error=True)
        with self.assertRaisesRegex(ValueError,'INERT_IDENTITY'):p.execute(self.args)
        self.assertNotIn('remote-inert',events);self.assertEqual(events[-1],'handle-close')
        self.assertTrue((self.args.private/'lease.private.json').is_file());self.assertFalse(self.args.output.exists())
        entry=ROOT/'tests/run_current_image57_preflight.py'
        result=subprocess.run([sys.executable,'-I','-B',str(entry)],capture_output=True,check=False)
        self.assertNotEqual(result.returncode,0)
        result=subprocess.run([sys.executable,'-I','-B',str(entry),'--help'],capture_output=True,check=False)
        self.assertEqual(result.returncode,0);self.assertIn(b'--lease-sha256',result.stdout)


if __name__=='__main__':
    unittest.main(verbosity=2)
