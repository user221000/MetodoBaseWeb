"""Owned composition29 evidence, complete source/helper/package and output receipts."""
import sys
sys.dont_write_bytecode=True
import ast
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(r'F:\mb-r23-qa30-20261019')
OUT=Path(__file__).resolve().parent
TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r23-composition30-independent-20261019')
HEAD='8d806a7fdcf2fbb1d39a7c91b9afcdbeedd9c10b'
API='72edeb474df72c9c78249ec7eac723a10b18f8fe'
CORE='6ec3f04fab18d21f28c63bb864a9398f23e5dcce'
MAIN_BASE='a40d5d'
PYTHON=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-candidate-web-20261018/Scripts/python.exe')
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def save(name,value):
    with (OUT/name).open('x',encoding='utf8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,default=str);stream.write('\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def photo(label):
    assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain').strip()
    names=sorted(set(n for n in git('ls-files','-co','--exclude-standard','-z').decode().split('\0') if n))
    sources={name:sha((ROOT/name).read_bytes()) for name in names}
    helpers={path.name:sha(path.read_bytes()) for path in sorted(OUT.glob('*.py'))}
    packages=sorted([d.metadata['Name'],d.version] for d in importlib.metadata.distributions());assert len(packages)==89
    result=subprocess.run([str(PYTHON),'-m','pip','check'],capture_output=True,timeout=30)
    with (OUT/(label+'-pip.log')).open('xb') as stream:stream.write(result.stdout+result.stderr)
    assert result.returncode==0
    value={'head':HEAD,'sources':sources,'source_count':len(sources),'new_helpers':helpers,'helper_count':len(helpers),
           'packages':packages,'package_count':89,'pip_check_exit':0}
    save(label+'-photo.json',value);return value

PATTERNS=[('COMPLETE_SYNTHETIC_JWT',re.compile(rb'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}')),
 ('PRIVATE_DATABASE_URL',re.compile(rb'postgres(?:ql)?(?:\+psycopg2)?://[^\s\x22\x27<>]+')),
 ('INVITATION_FRAGMENT',re.compile(rb'(?<=#token=)[A-Za-z0-9_-]{43}')),
 ('INVITATION_BODY',re.compile(rb'(?<=\x22token\x22: \x22)[A-Za-z0-9_-]{43}'))]
def publish(source,name):
    raw=source.read_bytes();public=raw;counts={}
    for label,pattern in PATTERNS:
        counts[label]=len(pattern.findall(public))
        public=pattern.sub(lambda match:('REDACTED_'+label+'_SHA256_'+sha(match.group())).encode(),public)
    target=name if public==raw else name+'.sanitized'
    with (OUT/target).open('xb') as stream:stream.write(public)
    return {'private_original':str(source),'original_sha256':sha(raw),'public_file':target,
            'public_sha256':sha(public),'public_is_RAW_exact':raw==public,'redactions':counts}
