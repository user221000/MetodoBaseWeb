"""Prepared in-container process attestation: emits booleans, never env values."""
from pathlib import Path
import json, os

rows = []
for directory in Path('/proc').iterdir():
    if not directory.name.isdigit():
        continue
    try:
        cmd = (directory / 'cmdline').read_bytes().split(b'\0')
        display = [p.decode(errors='replace') for p in cmd if p]
        if not any('web/main_web.py' in p or 'spawn_main' in p or 'uvicorn' in p for p in display):
            continue
        fields = (directory / 'environ').read_bytes().split(b'\0')
        names = {p.split(b'=', 1)[0] for p in fields if b'=' in p}
        status = (directory / 'status').read_text()
        uid = next(line.split()[1:] for line in status.splitlines() if line.startswith('Uid:'))
        rows.append({'pid': int(directory.name), 'command': display, 'uid_fields': uid,
                     'migrator_database_url_present': b'MIGRATOR_DATABASE_URL' in names,
                     'application_database_url_present': b'DATABASE_URL' in names})
    except (FileNotFoundError, ProcessLookupError):
        continue
assert any(r['pid'] == 1 and any(p.endswith('web/main_web.py') for p in r['command'])
           for r in rows), 'Expected real web PID1 is absent'
assert rows and not any(r['migrator_database_url_present'] for r in rows), 'Migration credential leaked to web process'
assert all(r['application_database_url_present'] for r in rows)
assert all(r['uid_fields'][0] == '999' for r in rows)
print(json.dumps({'web_processes': rows, 'all_migrator_credentials_absent': True,
                  'scope': 'Actual Linux processes only; environment names tested, no values emitted.'}, indent=2))
