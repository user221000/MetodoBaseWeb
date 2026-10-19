import sys,os,json,hashlib,subprocess,importlib.metadata,re
from pathlib import Path
ROOT=Path('F:/mb-r24-qa-20261019');OUT=Path(__file__).resolve().parents[1];TOOLS=OUT/'review-tools';TEMP=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r24-independent-20261019')
HEAD='9bfa76dee0dcda846d9d29ac79d0192289ebd2f2';PYTHON=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-candidate-web-20261018/Scripts/python.exe');PRIVATE=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def save(name,value):
    with (OUT/name).open('x',encoding='utf8',newline='\n')as stream:json.dump(value,stream,indent=2,ensure_ascii=False,default=str);stream.write('\n')
def git(*args):return subprocess.check_output(['git','--no-replace-objects',*args],cwd=ROOT)
def photo(label):
    assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain').strip()
    names=sorted(set(n for n in git('ls-files','-co','--exclude-standard','-z').decode().split('\0')if n))
    sources={name:sha((ROOT/name).read_bytes())for name in names}
    helpers={p.relative_to(TOOLS).as_posix():sha(p.read_bytes())for p in TOOLS.rglob('*')if p.is_file()}
    packages=sorted([d.metadata['Name'],d.version]for d in importlib.metadata.distributions());assert len(packages)==89
    result=subprocess.run([str(PYTHON),'-m','pip','check'],capture_output=True,timeout=30);assert result.returncode==0
    (OUT/(label+'-pip.log')).write_bytes(result.stdout+result.stderr)
    value={'head':HEAD,'sources':sources,'source_count':len(sources),'explicit_review_tools':helpers,'packages':packages,'package_count':89,'pip_exit':0};save(label+'-photo.json',value);return value
def environment(pg=False):
    env=os.environ.copy()
    for name in list(env):
        key=name.upper()
        if key=='DATABASE_URL'or key.endswith('_DATABASE_URL')or key.startswith(('PG','AWS_','S3_','METODOBASE_TEST_','_METODOBASE_TEST'))or any(x in key for x in ['STRIPE','MERCADOPAGO','RESEND','SMTP','SENTRY','OPENAI_API']):env.pop(name,None)
    env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',PYTHONPATH=str(ROOT)+os.pathsep+str(TOOLS))
    if pg:
        configuration=json.loads(PRIVATE.read_text(encoding='utf-8-sig'))
        for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:env[key]=configuration[key]
    return env
def publish(path,name):
    raw=path.read_bytes();public=raw
    patterns=[('PRIVATE_URL',rb'postgres(?:ql)?(?:\+psycopg2)?://[^\s\x22\x27<>]+'),('JWT',rb'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}'),('HMAC2',rb'(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{43}\.[A-Za-z0-9_-]{43}(?![A-Za-z0-9_-])'),('FRAGMENT',rb'(?<=#token=)[A-Za-z0-9_-]{43}')]
    for label,pattern in patterns:public=re.sub(pattern,lambda m:('REDACTED_'+label+'_SHA256_'+sha(m.group())).encode(),public)
    target=name if raw==public else name+'.sanitized';(OUT/target).write_bytes(public)
    return {'original_private':str(path),'original_sha256':sha(raw),'public':target,'public_sha256':sha(public),'RAW_exact':raw==public}
