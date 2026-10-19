"""Correct only own AST harness assumption: approved pin is the existing REVISION constant."""
from support import *
text=(OUT/'source_preservation_eol.py').read_text(encoding='utf8')
old="isinstance(kw.value,ast.Constant) and kw.value.value=='20261019_account_recovery'"
new="isinstance(kw.value,ast.Name) and kw.value.id=='REVISION'"
assert text.count(old)==1
text=text.replace(old,new)
old="with (OUT/('composition-'+name.replace('/','_')+'.diff')).open('xb') as stream:\n                stream.write(git('diff',API,HEAD,'--',name))"
new="delta=git('diff',API,HEAD,'--',name)\n            destination=OUT/('composition-'+name.replace('/','_')+'.diff')\n            if destination.exists():assert destination.read_bytes()==delta\n            else:destination.write_bytes(delta)"
assert text.count(old)==1
text=text.replace(old,new)
original=Path(r'F:/MetodoBaseWeb-member-link-20261019/docs/implementation/20261018-evolution/evidence/backend-r12-api-final-freeze.json')
assert sha(original.read_bytes())=='22d2259a51820521e09039fe6442af8b10b416bc5fc8810b4622293f2b14fec4'
with (OUT/'authenticated-original-backend-freeze.json').open('xb') as stream:stream.write(original.read_bytes())
proof=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-r12-api-commit-proof.json')
with (OUT/'retained-backend-commit-proof.json').open('xb') as stream:stream.write(proof.read_bytes())
target=OUT/'source_preservation_pins.py';target.write_text(text,encoding='utf8',newline='\n')
save('source-pin-harness-correction.json',{'original_eol_helper_sha256':sha((OUT/'source_preservation_eol.py').read_bytes()),
 'corrected_helper_sha256':sha(target.read_bytes()),'cause':'Expected the pin argument as a string literal; exact approved eef delta uses existing REVISION name.',
 'criterion':'Remove exactly one expected_revision=REVISION keyword, require complete previous AST equality. No product/test criterion changed.',
 'partial_existing_diff_outputs':'Retained exact bytes and reverified, never overwritten.',
 'raw_original_freeze_sha256':sha(original.read_bytes()),'actual_handoff_proof_file_sha256':sha(proof.read_bytes()),
 'scope':'Preparation stopped before any DB/test creation in both failed assertions. Historical and current source files untouched.'})
