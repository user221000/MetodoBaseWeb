from pathlib import Path
import hashlib
import json

source=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-expat-de69-native-validation-20261019')
raw=(source/'native-outputs/expat-output/build-provenance.json').read_bytes()
record=json.loads(raw)
build=(source/'native-build-receipt.json').read_bytes()
assert json.loads(build)['exit_code']==0
assert record['compiler_commands']==[] and record['small_binding_tests']['small_cases']==6
assert record['compiled_source']['before']['Modules/clinic/pyexpat.c.h']=='5e730198b2e3b644a96b411d5e594654d23146110b880a6ee9961fc919d90acb'
out=Path(r'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence\root-native-provenance-gap-20261019')
assert not out.exists()
out.mkdir();(out/'.gitattributes').write_bytes(b'* -text\n')
(out/'build-provenance.RAW.json').write_bytes(raw)
(out/'native-build-receipt.RAW.json').write_bytes(build)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
receipt={'finding':'OPS09','result':'PROVENANCE_GAP','compiled_target_exit':0,
 'recorded_compiler_commands':0,'helper_small_cases':6,'source':'de69a85e7903f1a7217b054c0edb269dd5560999',
 'scope':'Root read-only verification of the exact local native exports supplied by Operations. No direct VM interaction, no independent runtime/ABI/linkage acceptance; diagnostics remain separate. Empty compiler argv is not reconstructed from a console log.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
sha=lambda b:hashlib.sha256(b).hexdigest()
(out/'manifest.json').write_bytes((json.dumps({'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(out.iterdir()) if p.is_file()}},indent=2)+'\n').encode())
print(json.dumps({'manifest_sha256':sha((out/'manifest.json').read_bytes())}))
