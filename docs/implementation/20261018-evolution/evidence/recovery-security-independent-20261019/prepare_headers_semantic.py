from pathlib import Path
r=Path(__file__).parent
old=(r/'test_recovery_headers_security.py').read_text(encoding='utf8')
assert old.count(' privacy(response)')==1
new=old.replace(' privacy(response)'," assert 'no-store' in [item.strip().lower() for item in response.headers['cache-control'].split(',')]\n assert response.headers['referrer-policy']=='no-referrer'")
(r/'test_recovery_headers_semantic_security.py').write_text(new,encoding='utf8',newline='\n')
print('New additive semantic cache-control variant; original exact-string test retained unchanged. Referrer assertion unchanged.')
