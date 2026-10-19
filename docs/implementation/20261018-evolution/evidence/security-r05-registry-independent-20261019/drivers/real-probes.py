"""Actual pinned gitleaks over private finite candidates; preserve redacted RAW."""
from pathlib import Path
import contextlib,hashlib,io,json,os,subprocess,sys
ROOT=Path(r'F:/mb-security-r05-classifier-peer-20261019');sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-r05-classifier-peer-private-20261019';OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-r05-registry-independent-20261019'
from scripts import scan_secrets as scanner
from scripts import reviewed_scan_locations as registry
sha=lambda b:hashlib.sha256(b).hexdigest()
tool=T/'metodobase-gitleaks-8.30.1/gitleaks.exe';assert sha(tool.read_bytes())=='17157e2ee8b76fc8b1d8bee607a250e34b8a8023c8bc81822d4b5ee4d78fcb7c'
name='tests/test_client_link_models.py';original=(Path(r'F:/mb-progress-retirement-ui-20261019')/name).read_bytes()
binding=json.loads((OUT/'dataset-ledger-binding.json').read_bytes());assert sha(original)==binding['source_hashes'][name]
assert not original.startswith((b'\xff\xfe',b'\xfe\xff',b'\xef\xbb\xbf'))
cfg=(ROOT/'.gitleaks.toml').read_bytes();dataset=(ROOT/registry._REVIEW_DATA_PATH).read_bytes();real_run=subprocess.run
labels=['exact','append_new_credential','neighbor_copy','new_evidence_credential','utf8_bom','utf16_le','utf32_be','newline_variant','missing_dataset','corrupt_dataset','config_comment','source_changed_after_scan']
results=[]
for label in labels:
    own=P/'real-probes'/label;root=own/'candidate';root.mkdir(parents=True);source=root/name;source.parent.mkdir(parents=True);source.write_bytes(original)
    (root/'.gitleaks.toml').write_bytes(cfg);data=root/registry._REVIEW_DATA_PATH;data.parent.mkdir(parents=True);data.write_bytes(dataset)
    fake_value=sha(os.urandom(32));fake_line=('api_key = "'+fake_value+'"\n').encode()
    if label=='append_new_credential':source.write_bytes(original+fake_line)
    elif label=='neighbor_copy':
        source.unlink();(root/'tests/peer_copy.py').write_bytes(original)
    elif label=='new_evidence_credential':
        extra=root/'docs/evidence/unreviewed-peer.txt';extra.parent.mkdir(parents=True);extra.write_bytes(fake_line)
    elif label=='utf8_bom':source.write_bytes(b'\xef\xbb\xbf'+original)
    elif label=='utf16_le':source.write_bytes(b'\xff\xfe'+original.decode().encode('utf-16-le'))
    elif label=='utf32_be':source.write_bytes(b'\0\0\xfe\xff'+original.decode().encode('utf-32-be'))
    elif label=='newline_variant':
        changed=original.replace(b'\r\n',b'\n') if b'\r\n' in original else original.replace(b'\n',b'\r\n');assert changed!=original;source.write_bytes(changed)
    elif label=='missing_dataset':data.unlink()
    elif label=='corrupt_dataset':data.write_bytes(dataset+b'corrupted peer boundary')
    elif label=='config_comment':(root/'.gitleaks.toml').write_bytes(cfg+b'\n# peer changed config\n')
    for argv in [['git','init','-q',str(root)],['git','-C',str(root),'add','--all']]:
        r=real_run(argv,capture_output=True);assert r.returncode==0
    copied_raw=[]
    def wrapped(argv,**kw):
        r=real_run(argv,**kw)
        if len(argv)>1 and str(argv[0])==str(tool) and argv[1]=='dir':
            raw=Path(argv[argv.index('--report-path')+1]);assert raw.is_file()
            payload=raw.read_bytes();(own/'gitleaks-redacted.RAW.json').write_bytes(payload)
            (own/'gitleaks-stdout.RAW.log').write_bytes(r.stdout or b'');(own/'gitleaks-stderr.RAW.log').write_bytes(r.stderr or b'')
            copied_raw.append({'sha256':sha(payload),'bytes':len(payload),'exit':r.returncode})
            if label=='source_changed_after_scan':source.write_bytes(original+b'\n# post-scan own mutation\n')
        return r
    scanner.ROOT=root;sys.argv=['peer-real','--gitleaks',str(tool),'--report',str(own/'sanitized-report.json')]
    stream=io.StringIO();error=None;exit_code=None
    scanner.subprocess.run=wrapped
    try:
        with contextlib.redirect_stdout(stream):exit_code=scanner.main()
    except RuntimeError as exc:error=str(exc)
    finally:scanner.subprocess.run=real_run
    (own/'wrapper-stdout.RAW.log').write_bytes(stream.getvalue().encode())
    report=own/'sanitized-report.json'
    row={'case':label,'gitleaks_binary_sha256':sha(tool.read_bytes()),'actual_scan':bool(copied_raw),'actual_redacted_RAW':copied_raw,'wrapper_exit':exit_code,'report_exists':report.exists(),'error_is_sanitized_withheld':error=='Reviewed scanner location registry is invalid; output withheld' if error else False}
    if label in {'corrupt_dataset','config_comment'}:
        assert error and row['error_is_sanitized_withheld'] and not report.exists() and not copied_raw
    else:
        assert not error and copied_raw
        result=json.loads(report.read_bytes());row.update(raw_findings=result['raw_finding_count'],classified=result['classified_finding_count'],remaining=result['remaining_finding_count'],raw_exit=result['exit_code'],effective_exit=result['effective_exit_code'],source_stable=result['source_stable'],sanitized_report_sha256=sha(report.read_bytes()),encoding_transforms=len(result['encoding_transforms']))
        assert result['exit_code']==1 and result['raw_finding_count']>=2
        if label=='exact':assert exit_code==0 and result['remaining_finding_count']==0 and result['classified_finding_count']==result['raw_finding_count']
        elif label=='source_changed_after_scan':assert exit_code==2 and not result['source_stable'] and result['remaining_finding_count']==0
        elif label=='new_evidence_credential':assert exit_code==1 and result['classified_finding_count']>=2 and result['remaining_finding_count']>=1
        else:assert exit_code==1 and result['classified_finding_count']==0 and result['remaining_finding_count']==result['raw_finding_count']
        if label=='append_new_credential':assert result['raw_finding_count']>=3
    results.append(row)
    (OUT/'actual-gitleaks-probes.STRUCTURAL.json').write_bytes((json.dumps(results,indent=2)+'\n').encode())
print(json.dumps({'actual_gitleaks_cases':sum(r['actual_scan'] for r in results),'registry_rejected_before_scan':sum(not r['actual_scan'] for r in results),'all_cases':len(results),'values_published':False,'result':'PASS'}))
