from pathlib import Path
import hashlib,json
root=Path(r'F:\mb-r12-ci29-20261019')
source=Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/qa-r12-composition29-independent-20261019/afterec/portable')
mapping={'real29_server.py':'member_link_postgres_server.py','real29_browser.cjs':'member_link_browser.cjs','normalize_browser_report.py':'normalize_member_link_report.py'}
rows=[]
for old,new in mapping.items():
    raw=(source/old).read_bytes(); output=raw.replace(b'\r\n',b'\n')
    if old=='real29_server.py':
        before=b"assert not subprocess.check_output(['git','status','--porcelain'],cwd=root).strip()"
        after=b"assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root).strip()"
        assert output.count(before)==1
        output=output.replace(before,after)
        assert output.replace(after,before)==raw.replace(b'\r\n',b'\n')
    (root/'tests/e2e'/new).write_bytes(output)
    rows.append({'original':old,'current':'tests/e2e/'+new,'original_raw_sha256':hashlib.sha256(raw).hexdigest(),'current_LF_sha256':hashlib.sha256(output).hexdigest(),'delta':'Only tracked-clean check permits unrelated generated CI reports' if old=='real29_server.py' else 'Only checkout newline normalization; assertions byte exact'})
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci29-portable-preparation-20261019.json')
assert not out.exists();out.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
print(json.dumps(rows))
