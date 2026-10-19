from pathlib import Path
from collections import Counter
import hashlib,json

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE=LAB/'evidence/os-audit-abd559a/results'
NEW=LAB/'evidence/os-audit-bc365c1/results'
before_bytes=(BASE/'scan.json').read_bytes();after_bytes=(NEW/'scan.json').read_bytes()
assert hashlib.sha256(before_bytes).hexdigest()=='a0daa5160bafc780f35dc5149f8d3894f9e0865e87ff446b2ff089422e374b0f'
before=json.loads(before_bytes);after=json.loads(after_bytes)
baseline=json.loads((BASE/'scan-summary.json').read_text());current=json.loads((NEW/'scan-summary.json').read_text())
assert baseline['input_bytes_stable'] and current['input_bytes_stable']
assert baseline['db_oci_reference']==current['db_oci_reference']=='ghcr.io/aquasecurity/trivy-db@sha256:ae8f987b86b4434aad25eec383b63d3c754433148870545d3b4013bc3786a4e7'
assert baseline['db_files_after']==current['db_files_before']==current['db_files_after']
fields=['VulnerabilityID','PkgName','InstalledVersion','FixedVersion','Status','Severity']
def rows(value):return [v for result in value['Results'] for v in result.get('Vulnerabilities',[])]
old_rows=rows(before);new_rows=rows(after)
old=Counter(tuple(v.get(k) for k in fields) for v in old_rows)
new=Counter(tuple(v.get(k) for k in fields) for v in new_rows)
removed=old-new;added=new-old
expected={'DSA-6549-1','TEMP-1147318-639065'}
assert not added and sum(removed.values())==2
assert {row[0] for row in removed}==expected and all(row[1]=='liblzma5' for row in removed)
assert len(old_rows)==166 and len(new_rows)==164
assert len({p['VulnerabilityID'] for p in new_rows})==71
assert {p['VulnerabilityID'] for p in old_rows}-expected=={p['VulnerabilityID'] for p in new_rows}
assert not any(p.get('FixedVersion') for p in new_rows)
for result in [before,after]:assert len(result['Results'])==1 and result['Results'][0]['Class']=='os-pkgs' and len(result['Results'][0]['Packages'])==87
inventory=json.loads((LAB/'evidence/recovery28-image-bc365c1/runtime-inventory.json').read_text())
assert after['Metadata']['ImageID']==inventory['image_id']==current['image_id']
report={'before_image_id':before['Metadata']['ImageID'],'after_image_id':after['Metadata']['ImageID'],
 'before_scan_sha256':hashlib.sha256(before_bytes).hexdigest(),'after_scan_sha256':hashlib.sha256(after_bytes).hexdigest(),
 'database_reference':current['db_oci_reference'],'database_files_exactly_same':True,'before_entries':166,'after_entries':164,
 'before_identifiers':73,'after_identifiers':71,'removed_entries':[dict(zip(fields,row)) for row in removed],
 'new_entries':0,'all_other_164_entries_exact_same_fields':True,'all_other_71_identifiers_retained':True,'after_fix_available_entries':0,
 'after_severity_counts':dict(Counter(p['Severity'] for p in new_rows)),'after_status_counts':dict(Counter(p['Status'] for p in new_rows)),
 'exceptions_or_filters_added':False,'scope':'XZ backport removes exactly its DSA/TEMP entries. Remaining findings stay open. No OS-green, exploitability or application-runtime acceptance.'}
(NEW.parent/'comparison-to-abd559a.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
