from pathlib import Path
import json,collections,hashlib,re,ast
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp');PRIVATE=TEMP/'metodobase-sec-gitleaks-peer-private-20261019'
raw=json.loads((PRIVATE/'focal-redacted.json').read_bytes());rows=json.loads((TEMP/'metodobase-gitleaks-historical-evidence-triage-20261019/unclassified-locations.json').read_bytes())
root=PRIVATE/'focal-snapshot';wanted=collections.Counter((r['file'],r['line'],r['rule']) for r in rows)
result=[]
for item in raw:
    name=Path(item['File']).relative_to(root).as_posix() if Path(item['File']).is_absolute() else item['File']
    identity=(name,item['StartLine'],item['RuleID'])
    if identity not in wanted:continue
    line=(root/name).read_text(encoding='utf8').split('\n')[item['StartLine']-1]
    span=line[item['StartColumn']-1:item['EndColumn']]
    parsed={'file':name,'line':item['StartLine'],'rule':item['RuleID'],'columns':[item['StartColumn'],item['EndColumn']],
        'span_length':len(span),'span_sha256':hashlib.sha256(span.encode()).hexdigest(),'span_hex64':len(span)==64 and bool(re.fullmatch('[a-f0-9]{64}',span)),
        'hex_lengths':[len(m[0]) for m in re.finditer('[a-fA-F0-9]{16,}',span)],
        'redacted_match_length':len(item.get('Match','')),'redacted_match_marker_count':item.get('Match','').count('REDACTED'),
        'span_structural_tokens':[t for t in ['request_key','sha256','SHA256','hash','token','GPG','VALIDSIG','KEY','key','api','source','fingerprint','crc','python','exe','opclass'] if t in span]}
    try:
        tree=ast.parse((root/name).read_text(encoding='utf8'))
        overlapping=[k for n in ast.walk(tree) if isinstance(n,ast.Call) for k in n.keywords if k.lineno==item['StartLine'] and k.col_offset<item['EndColumn'] and k.end_col_offset>=item['StartColumn']]
        parsed['overlapping_keyword_fields']=[k.arg for k in overlapping]
    except Exception:pass
    result.append(parsed)
assert collections.Counter((r['file'],r['line'],r['rule']) for r in result)==wanted
(PRIVATE/'remaining-columns-and-shapes.STRUCTURAL.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({'fixed_findings_reproduced_exact':len(result),'by_span_tokens':collections.Counter(t for row in result for t in row['span_structural_tokens']),
    'nonhex_span_shapes':collections.Counter(str(r['hex_lengths']) for r in result),'selected':[r for r in result if r['file'].endswith('test_client_link_models.py') or 'psf-signature' in r['file'] or r['file'].endswith('checkpoint116-driver.py')]},indent=2))
