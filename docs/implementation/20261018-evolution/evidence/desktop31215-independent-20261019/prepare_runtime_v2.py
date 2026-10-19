"""Preserve original numeric-resource assumption; bind version strings and fixed bytes to authenticated source."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=Path(r'F:/mb-d31215-20261019')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
command="""Get-Item -LiteralPath 'F:/mb-d31215-20261019/dist/MetodoBase/_internal/python312.dll','C:/Users/Consu/AppData/Local/Temp/metodobase-python31215-windows-provenance-20261019/runtime/python/python312.dll' | ForEach-Object { [pscustomobject]@{ Path=$_.FullName; FileVersion=$_.VersionInfo.FileVersion; ProductVersion=$_.VersionInfo.ProductVersion; Fixed=@($_.VersionInfo.FileMajorPart,$_.VersionInfo.FileMinorPart,$_.VersionInfo.FileBuildPart,$_.VersionInfo.FilePrivatePart) } } | ConvertTo-Json -Compress"""
raw=subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-Command',command])
values=json.loads(raw)
assert len(values)==2 and all(value['FileVersion']=='3.12.15' and value['ProductVersion']=='3.12.15' and value['Fixed']==[3,12,15150,1013] for value in values)
(OUT/'DLL-resource-original-diagnostic.json').write_bytes(raw)
original=(OUT/'review_runtime.py').read_text(encoding='utf8')
replacement="version==binary_version(RUNTIME/'python312.dll')==[3,12,15150,1013] and all(value['FileVersion']=='3.12.15' and value['ProductVersion']=='3.12.15' for value in json.loads((OUT/'DLL-resource-original-diagnostic.json').read_bytes()))"
assert original.count('version[:3]==[3,12,15]')==1
adapted=original.replace('version[:3]==[3,12,15]',replacement)
for old,new in [('runtime-before','runtime-v2-before'),('runtime-after','runtime-v2-after'),('runtime-review.json','runtime-review-v2.json')]:
    assert adapted.count(old)==1
    adapted=adapted.replace(old,new)
target=OUT/'review_runtime_v2.py';target.write_text(adapted,encoding='utf8',newline='\n')
proof={'original_sha256':sha((OUT/'review_runtime.py').read_bytes()),'adapted_sha256':sha(target.read_bytes()),
       'original_false_assumption':'The third VS_FIXEDFILEINFO integer equals micro version15. The authenticated source DLL itself has third15150/fourth1013 while both version strings are3.12.15.',
       'correction':'Compare full bundled fixed tuple to authenticated source DLL and exact observed tuple; require both DLL FileVersion/ProductVersion strings3.12.15. Existing archive SHA/source/runtime version checks stay intact.',
       'original_failure_preserved':['review_runtime.py','runtime-first-console.log','runtime-review.json'],
       'additional_changes':'Only new phase labels/output filename to preserve original. No historical51/27 checks or product edited/repeated.',
       'diagnostic_sha256':sha(raw),'version_resources':values,'new_runtime_checks_replayed':'Read-only own checks only; failure correction justifies rerun. No Qt packaged diagnostic, source test suite, SCA or build rerun.'}
(OUT/'DLL-resource-harness-correction.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
print(json.dumps({'v2_driver_sha256':proof['adapted_sha256'],'diagnostic_sha256':sha(raw)}))
