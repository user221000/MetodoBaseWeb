from pathlib import Path
import codecs
import hashlib
import json
import re
import subprocess
import tempfile
import tomllib

root = Path('F:/MetodoBaseWeb-execution-20261018')
run = root / 'docs/implementation/20261018-evolution/evidence'
candidate_dir = Path(tempfile.mkdtemp(prefix='metodobase-r21-crlf-author-'))
base_bytes = (root / '.gitleaks.toml').read_bytes()
assert hashlib.sha256(base_bytes).hexdigest() == 'd4e281f02f629737cf17f136fd0fb9cf375feea54c42dc3fc6d024262e03cbbc'
base = base_bytes.decode('utf-8')
parsed = tomllib.loads(base)
compact = {pattern for rule in parsed['rules'] for group in rule['allowlists']
           for pattern in group['regexes'] if pattern.startswith(r'^\{')}
fixed = base
compact_replacements = 0
for pattern in compact:
    assert pattern.endswith('$') and not pattern.endswith(r'\r?$')
    compact_replacements += fixed.count("'''" + pattern + "'''")
    fixed = fixed.replace("'''" + pattern + "'''", "'''" + pattern[:-1] + r"\r?$" + "'''")
assert compact_replacements == 17

report = json.loads((run / 'secrets-protocol26-reviewed-c6fda6a.json').read_text(encoding='utf-8'))
initial = json.loads((run / 'secrets-protocol26-initial.json').read_text(encoding='utf-8'))
source_report_path = 'docs/implementation/20261018-evolution/evidence/secrets-protocol26-initial.json'
source_lines = (root / source_report_path).read_text(encoding='utf-8').splitlines()
groups = {}
verified = []
for finding in report['findings']:
    if finding['file'] != source_report_path:
        continue
    line = source_lines[finding['line'] - 1]
    pair = re.fullmatch(r'\s*"([^"\r\n]+)"\s*:\s*"([a-f0-9]{64})",?\s*', line)
    assert pair, 'A new finding is not a file-digest pair; requires manual review'
    name, digest = pair.groups()
    assert initial['files'][name] == digest
    blob = subprocess.run(['git','show','2f8b7f9:'+name], cwd=root, check=True, capture_output=True).stdout
    variants = {'git_blob': blob, 'checkout_crlf': blob.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')}
    matches = [variant for variant, value in variants.items() if hashlib.sha256(value).hexdigest() == digest]
    assert matches, 'Claimed public digest must match the original committed file bytes'
    groups.setdefault(finding['rule'], set()).add(r'^\s*"' + re.escape(name) + r'"\s*:\s*"' + digest + r'",?\s*$')
    verified.append({'rule':finding['rule'], 'line':finding['line'], 'path':name, 'public_sha256':digest, 'verified_variants':matches})
assert len(verified) == 45

for rule, patterns in groups.items():
    fragment = '\r\n    [[rules.allowlists]]\r\n'
    fragment += '    description = "Exact public file digests in the preserved protocol26 initial scan"\r\n'
    fragment += '    condition = "AND"\r\n'
    fragment += "    paths = ['''(?:^|/)" + re.escape(source_report_path) + "$''']\r\n"
    fragment += '    regexTarget = "line"\r\n    regexes = [\r\n'
    fragment += ''.join("        '''" + pattern + "''',\r\n" for pattern in sorted(patterns))
    fragment += '    ]\r\n'
    if rule == 'generic-api-key':
        marker = '[[rules]]\r\nid = "sentry-access-token"'
        assert fixed.count(marker) == 1
        fixed = fixed.replace(marker, fragment + '\r\n' + marker)
    elif rule == 'sentry-access-token':
        fixed += fragment
    else:
        raise AssertionError('Unexpected detector rule')

new_bytes = fixed.encode('utf-8')
candidate = candidate_dir / 'candidate-crlf-and-scan-report.toml'
candidate.write_bytes(new_bytes)
new_parsed = tomllib.loads(fixed)
assert [r['id'] for r in new_parsed['rules']] == [r['id'] for r in parsed['rules']]

# A byte-preserving fixture uses the reviewed compact line without normalizing
# the source's actual CRLF. A minimal Git repo is only an owned scanner fixture.
log_name = 'docs/implementation/20261018-evolution/evidence/ux/auth-refresh-browser-server.log'
source_blob = subprocess.run(['git','show','c6fda6a:'+log_name], cwd=root, check=True, capture_output=True).stdout
if source_blob.startswith(codecs.BOM_UTF16_LE) or source_blob.startswith(codecs.BOM_UTF16_BE):
    content = source_blob.decode('utf-16')
else:
    content = source_blob.decode('utf-8-sig')
line = next(line for line in content.splitlines() if line.startswith('{"fixture":'))
python = 'C:/Users/Consu/AppData/Local/Temp/metodobase-candidate-web-20261018/Scripts/python.exe'
scanner = 'C:/Users/Consu/AppData/Local/Temp/metodobase-gitleaks-8.30.1/gitleaks.exe'
results = []
for config_name, config_bytes in (('before',base_bytes), ('after',new_bytes)):
    for label, value in (
        ('utf8-lf', (line+'\n').encode('utf-8')),
        ('utf8-crlf', (line+'\r\n').encode('utf-8')),
        ('utf16le-crlf', codecs.BOM_UTF16_LE+(line+'\r\n').encode('utf-16-le')),
        ('utf16be-crlf', codecs.BOM_UTF16_BE+(line+'\r\n').encode('utf-16-be')),
        ('utf8bom-crlf', codecs.BOM_UTF8+(line+'\r\n').encode('utf-8')),
    ):
        fixture = candidate_dir / (config_name+'-'+label)
        fixture.mkdir()
        subprocess.run(['git','init','-q',str(fixture)],check=True,capture_output=True)
        (fixture / 'scripts').mkdir()
        (fixture / 'scripts/scan_secrets.py').write_bytes((root / 'scripts/scan_secrets.py').read_bytes())
        (fixture / '.gitleaks.toml').write_bytes(config_bytes)
        log = fixture / log_name
        log.parent.mkdir(parents=True)
        log.write_bytes(value)
        output = candidate_dir / (config_name+'-'+label+'.json')
        result = subprocess.run([python,'-X','utf8',str(fixture/'scripts/scan_secrets.py'),'--gitleaks',scanner,'--report',str(output)],cwd=fixture,capture_output=True,timeout=60)
        body = json.loads(output.read_text(encoding='utf-8'))
        findings = body['findings']
        assert body['source_stable'] and all(f['file']==log_name for f in findings)
        if config_name == 'after' or label == 'utf8-lf':
            assert result.returncode == 0 and not findings
        else:
            assert result.returncode == 1 and findings
        results.append({'config':config_name,'bytes':label,'exit':result.returncode,'findings':len(findings),'stable':body['source_stable']})

proof={'scope':'Author coordinator fix only; independent canaries/review and full exact-commit scan still required.',
       'base_raw_sha256':hashlib.sha256(base_bytes).hexdigest(),
       'candidate_raw_sha256':hashlib.sha256(new_bytes).hexdigest(),
       'candidate_lf_sha256':hashlib.sha256(new_bytes.replace(b'\r\n',b'\n')).hexdigest(),
       'candidate_path':str(candidate),'compact_patterns_with_optional_cr':compact_replacements,
       'new_exact_scan_report_pairs':len(verified),'verified_pairs':verified,'byte_preserving_wrapper_results':results,
       'cause':'Prior canaries wrote LF; compact whole-line patterns omitted optional CR while wrapper preserves CRLF when transcoding BOM. Newline-only correction keeps complete-line anchors and does not permit extra content.'}
(run / 'secrets-protocol26-crlf-author-review.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:proof[key] for key in ('candidate_path','candidate_raw_sha256','candidate_lf_sha256','compact_patterns_with_optional_cr','new_exact_scan_report_pairs')}))
