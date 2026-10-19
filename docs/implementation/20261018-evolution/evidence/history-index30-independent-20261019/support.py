"""Full source/helper, dependency and raw-output receipts for frozen history30."""
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

ROOT=Path(r'F:/mb-hidx30-qa-20261019')
AUTHOR=Path(r'F:/mb-hidx-20261019')
OUT=Path(__file__).resolve().parent
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-history-index30-independent-20261019')
HEAD='6ea19e6b96e08a42c52f03db37a16fb9915eabba'
BASE='aa9c3b84a9489f2ed845827c37ccaa77cc3ceb06'
PYTHON=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-candidate-web-20261018/Scripts/python.exe')
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
FREEZE='docs/implementation/20261018-evolution/evidence/history30-author-20261019'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def save(name,value):
    with (OUT/name).open('x',encoding='utf8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,default=str);stream.write('\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def photo(label):
    assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain').strip()
    names=sorted(set(name for name in git('ls-files','-co','--exclude-standard','-z').decode().split('\0') if name))
    sources={name:sha((ROOT/name).read_bytes()) for name in names}
    helpers={p.name:sha(p.read_bytes()) for p in sorted(OUT.glob('*.py'))}
    packages=sorted([d.metadata['Name'],d.version] for d in importlib.metadata.distributions());assert len(packages)==89
    result=subprocess.run([str(PYTHON),'-m','pip','check'],capture_output=True,timeout=30)
    with (OUT/(label+'-pip.log')).open('xb') as stream:stream.write(result.stdout+result.stderr)
    assert result.returncode==0
    value={'head':HEAD,'sources':sources,'source_count':len(sources),'untracked_own_helpers':helpers,
           'helper_count':len(helpers),'packages':packages,'package_count':89,'pip_check_exit':0}
    save(label+'-photo.json',value);return value

JWT=re.compile(rb'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}')
DBURL=re.compile(rb'postgres(?:ql)?(?:\+psycopg2)?://[^\s\x22\x27<>]+')
def publish_raw_or_sanitized(source,name):
    raw=source.read_bytes();counts={}
    public=raw
    for label,pattern in [('synthetic_complete_JWT',JWT),('private_database_URL',DBURL)]:
        matches=pattern.findall(public);counts[label]=len(matches)
        public=pattern.sub(lambda match:('REDACTED_'+label.upper()+'_SHA256_'+sha(match.group())).encode(),public)
    target=name if public==raw else name+'.sanitized'
    with (OUT/target).open('xb') as stream:stream.write(public)
    return {'private_original':str(source),'raw_sha256':sha(raw),'public_file':target,
            'public_sha256':sha(public),'public_is_RAW_exact':public==raw,'redacted_occurrences':counts}
