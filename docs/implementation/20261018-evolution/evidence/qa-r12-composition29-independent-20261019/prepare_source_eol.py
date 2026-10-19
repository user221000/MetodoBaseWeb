"""Additive source-receipt adapter; preserve original failed raw-EOL assumption."""
from support import *
original=(OUT/'source_preservation.py').read_text(encoding='utf8')
assert original.count('freeze_sha=sha(path.read_bytes())')==1
adapted=original.replace('freeze_sha=sha(path.read_bytes())','freeze_sha=sha(path.read_bytes().replace(b"\\r\\n",b"\\n"))')
assert adapted.count("'26889:'")==1
adapted=adapted.replace("'26889:'","'e6924e192e99850a1044602bc87b2d2c10bae14b:'")
target=OUT/'source_preservation_eol.py'
target.write_text(adapted,encoding='utf8',newline='\n')
save('source-freeze-EOL-provenance.json',{'original_driver_sha256':sha((OUT/'source_preservation.py').read_bytes()),
     'adapted_driver_sha256':sha(target.read_bytes()),
     'freeze_checkout_RAW_sha256':'26a609ffe971cdeb676b44606ac55bdb88f0951fc773b22b2c395b98deca2c9a',
     'authenticated_Git_LF_sha256':'22d2259a51820521e09039fe6442af8b10b416bc5fc8810b4622293f2b14fec4',
     'only_freeze_byte_difference':'CRLF checkout vs LF Git blob; all JSON values unchanged.',
     'actual_freeze_introducing_commit':'e6924e192e99850a1044602bc87b2d2c10bae14b',
     'parent_handoff_short_reference':'26889 does not exist as a Git object in this shared repository; actual history for same pinned freeze resolves e6924e192.',
     'failed_preparation_scope':'Original source-preservation assertion stopped before reading RAW ZIP or creating DB/running tests; original helper retained unchanged.',
     'criteria_or_product_changes':False})
print(json.dumps({'source_metadata_adapter':'prepared','Git_LF_freeze_sha256':'22d2259a51820521e09039fe6442af8b10b416bc5fc8810b4622293f2b14fec4'}))
