from pathlib import Path
import hashlib,json,re,subprocess,tempfile,tomllib

root=Path('F:/MetodoBaseWeb-execution-20261018')
evidence=root/'docs/implementation/20261018-evolution/evidence'
base=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r21-crlf-author-tm5xq_14/candidate-crlf-and-scan-report.toml').read_bytes()
assert hashlib.sha256(base).hexdigest()=='88b5a53a0364c30983fed1adb1f97a76b02af26ad223fc43cd4d00e4830a8f75'
report_name='docs/implementation/20261018-evolution/evidence/secrets-protocol26-reviewed-c6fda6a.json'
report_bytes=(root/report_name).read_bytes()
report=json.loads(report_bytes)
temporary=Path(tempfile.mkdtemp(prefix='metodobase-r21-report-followup-'))
fixture=temporary/'fixture'; fixture.mkdir()
subprocess.run(['git','init','-q',str(fixture)],check=True,capture_output=True)
(fixture/'scripts').mkdir(); (fixture/'scripts/scan_secrets.py').write_bytes((root/'scripts/scan_secrets.py').read_bytes())
(fixture/'.gitleaks.toml').write_bytes(base)
target=fixture/report_name; target.parent.mkdir(parents=True); target.write_bytes(report_bytes)
python='C:/Users/Consu/AppData/Local/Temp/metodobase-candidate-web-20261018/Scripts/python.exe'
scanner='C:/Users/Consu/AppData/Local/Temp/metodobase-gitleaks-8.30.1/gitleaks.exe'
def scan(label):
    output=temporary/(label+'.json')
    result=subprocess.run([python,'-X','utf8',str(fixture/'scripts/scan_secrets.py'),'--gitleaks',scanner,'--report',str(output)],cwd=fixture,capture_output=True,timeout=60)
    body=json.loads(output.read_text()); assert body['source_stable']
    return result.returncode,body['findings']
before_exit,findings=scan('before')
assert before_exit==1 and findings and all(item['file']==report_name for item in findings)
lines=report_bytes.decode('utf-8').splitlines(); groups={}; verified=[]
for finding in findings:
    pair=re.fullmatch(r'\s*"([^"\r\n]+)"\s*:\s*"([a-f0-9]{64})",?\s*',lines[finding['line']-1])
    assert pair, 'Non fingerprint requires manual triage'
    name,digest=pair.groups(); assert report['files'][name]==digest
    blob=subprocess.run(['git','show','c6fda6a:'+name],cwd=root,check=True,capture_output=True).stdout
    variants={'git_blob':blob,'checkout_crlf':blob.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')}
    matches=[label for label,value in variants.items() if hashlib.sha256(value).hexdigest()==digest]
    assert matches, 'Fingerprint must match public committed bytes'
    groups.setdefault(finding['rule'],set()).add(r'^\s*"'+re.escape(name)+r'"\s*:\s*"'+digest+r'",?\s*$')
    verified.append({'rule':finding['rule'],'line':finding['line'],'path':name,'public_sha256':digest,'verified_variants':matches})
text=base.decode('utf-8')
for rule,patterns in groups.items():
    fragment='\r\n    [[rules.allowlists]]\r\n    description = "Exact public file digests of the preserved c6fda6a scan report"\r\n    condition = "AND"\r\n'
    fragment+="    paths = ['''(?:^|/)"+re.escape(report_name)+"$''']\r\n    regexTarget = \"line\"\r\n    regexes = [\r\n"
    fragment+=''.join("        '''"+pattern+"''',\r\n" for pattern in sorted(patterns))+'    ]\r\n'
    if rule=='generic-api-key':
        marker='[[rules]]\r\nid = "sentry-access-token"'; assert text.count(marker)==1; text=text.replace(marker,fragment+'\r\n'+marker)
    elif rule=='sentry-access-token':text+=fragment
    else:raise AssertionError('Unexpected rule')
candidate=temporary/'candidate-final-report.toml'; candidate.write_bytes(text.encode('utf-8')); tomllib.loads(text)
(fixture/'.gitleaks.toml').write_bytes(candidate.read_bytes())
after_exit,after_findings=scan('after'); assert after_exit==0 and not after_findings
proof={'scope':'Author coordinator: only new exact report-path fingerprint pairs; independent review/canaries and full frozen-tree scan still pending.','base_raw_sha256':hashlib.sha256(base).hexdigest(),'candidate_path':str(candidate),'candidate_raw_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'candidate_lf_sha256':hashlib.sha256(candidate.read_bytes().replace(b'\r\n',b'\n')).hexdigest(),'source_commit':'c6fda6a','source_report':report_name,'source_report_sha256':hashlib.sha256(report_bytes).hexdigest(),'verified_pairs':verified,'before':{'exit':before_exit,'findings':len(findings)},'after':{'exit':after_exit,'findings':len(after_findings)},'limit':'No future report path allowance. Final scan evidence will bind its scanned commit; a later documentary commit does not retroactively become the scanned tree.'}
(evidence/'secrets-protocol26-report-followup-author.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:proof[key] for key in ('candidate_path','candidate_raw_sha256','candidate_lf_sha256','before','after')}))
