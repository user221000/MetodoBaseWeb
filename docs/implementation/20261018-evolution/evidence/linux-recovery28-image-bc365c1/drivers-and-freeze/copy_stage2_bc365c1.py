from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
DEST = Path(r'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence\linux-recovery28-image-bc365c1')
PLAN = []
for p in sorted((LAB / 'evidence/os-audit-bc365c1/results').rglob('*')):
    if p.is_file():
        PLAN.append((p, DEST / 'os-audit/results' / p.relative_to(LAB / 'evidence/os-audit-bc365c1/results')))
for name in ['audit-driver.log', 'comparison-to-abd559a.json']:
    PLAN.append((LAB / 'evidence/os-audit-bc365c1' / name, DEST / 'os-audit' / name))
for p in sorted((LAB / 'evidence/closure-bc365c1').iterdir()):
    assert p.is_file()
    PLAN.append((p, DEST / 'closure' / p.name))
for name in ['close_bc365c1.py', 'copy_stage2_bc365c1.py']:
    PLAN.append((LAB / 'evidence/image-security-bc365c1-primary' / name, DEST / 'drivers-and-freeze' / name))

def safe(p, root):
    assert p.resolve().is_relative_to(root.resolve())
    for a in (p, *p.parents):
        if a.exists():
            assert not a.is_symlink() and not (getattr(a.lstat(), 'st_file_attributes', 0) & 0x400)

records = []
for source, target in PLAN:
    safe(source, LAB)
    safe(target, DEST)
    assert source.is_file() and not target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    with target.open('xb') as stream:
        stream.write(data)
    digest = hashlib.sha256(data).hexdigest()
    assert target.read_bytes() == data
    records.append({'source': str(source), 'destination': target.relative_to(DEST).as_posix(),
                    'bytes': len(data), 'sha256': digest})
receipt = {'copied_utc': datetime.now(timezone.utc).isoformat(), 'files': records,
           'os_audit_complete': True, 'vm_left_running': True,
           'scope': 'Copies closed raw audit and lifecycle evidence. Existing stage-1 evidence is preserved.'}
with (DEST / 'copy-receipt-stage2-os-closure.json').open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps({'copied_files': len(records), 'destination': str(DEST)}))
