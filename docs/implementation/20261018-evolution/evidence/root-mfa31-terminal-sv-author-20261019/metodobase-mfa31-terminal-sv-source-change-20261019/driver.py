"""Separate valid identity range from capacity for factor session revocation."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

root=Path(r'F:\mb-mfa31-terminal-sv-20261019');tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
out=tmp/'metodobase-mfa31-terminal-sv-source-change-20261019'
before_phase=tmp/'metodobase-mfa31-terminal-sv-before-20261019'
report=json.loads((before_phase/'summary.json').read_bytes())
assert report['cases']==14 and report['passed']==4 and report['failed']==10 and report['errors']==report['skipped']==0
assert report['sources_packages_python_exact'] and report['pip_before']==report['pip_after']==0
assert not out.exists()
git=lambda *args:subprocess.check_output(['git',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()=='809eab28c40c112cb6e3c9d8caceebae28683abd'
assert not git('status','--porcelain','--untracked-files=no')
test=(root/'tests/test_mfa31_terminal_session_version.py').read_bytes()
assert hashlib.sha256(test).hexdigest()==report['test_source_sha256']
blobs={};edits={}
name='web/services/mfa_service.py';raw=(root/name).read_bytes();text=raw.decode();newline='\r\n' if '\r\n' in text else '\n'
normalized=text.replace('\r\n','\n');assert normalized.encode()==git('show','HEAD:'+name)
changes=[
 ('not 0 <= user.session_version < MAX_SV','not 0 <= user.session_version <= MAX_SV'),
 ('        "mfa_unconfirmed": "No pudimos confirmar la operación. Consulta el estado o inicia sesión de nuevo.",',
  '        "mfa_unconfirmed": "No pudimos confirmar la operación. Consulta el estado o inicia sesión de nuevo.",\n        "mfa_session_version_exhausted": "La cuenta necesita revisión antes de cambiar sus opciones de seguridad.",'),
 ('def _revoke_sessions(db, user):\n    user.session_version += 1',
  'def _require_session_capacity(user):\n    if type(user.session_version) is not int or not 0 <= user.session_version < MAX_SV:\n        fail(409, "mfa_session_version_exhausted")\n\n\ndef _revoke_sessions(db, user):\n    _require_session_capacity(user)\n    user.session_version += 1'),
]
for function,first in [('enroll','key = configuration()'),('confirm_enrollment','key = configuration()'),('change_factor','configuration()')]:
    node=next(node for node in ast.parse(normalized).body if isinstance(node,ast.FunctionDef) and node.name==function)
    segment='\n'.join(normalized.splitlines()[node.lineno-1:node.end_lineno])
    anchor='    user, _ = lock_actor(db, expected)\n'
    assert segment.count(anchor)==1
    changed=segment.replace(anchor,anchor+'    _require_session_capacity(user)\n')
    changes.append((segment,changed))
for old,new in changes:
    assert normalized.count(old)==1,old
    normalized=normalized.replace(old,new)
ast.parse(normalized)
inverse=normalized
for old,new in reversed(changes):
    assert inverse.count(new)==1
    inverse=inverse.replace(new,old)
assert inverse==text.replace('\r\n','\n')
edits[name]=normalized.replace('\n',newline).encode();blobs[name]=raw
name='web/static/js/mfa-ui.js';raw=(root/name).read_bytes();text=raw.decode()
old="mfa_busy:'Hay una verificación en curso. Espera o descártala.',"
new=old+"mfa_session_version_exhausted:'La cuenta necesita revisión antes de cambiar sus opciones de seguridad. No se modificó el segundo factor.',"
assert text.count(old)==1 and text.replace('\r\n','\n').encode()==git('show','HEAD:'+name)
changed=text.replace(old,new);assert changed.replace(new,old)==text
edits[name]=changed.encode();blobs[name]=raw
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
(out/'test-source-before.RAW.py').write_bytes(test)
receipt={'base':'809eab28c40c112cb6e3c9d8caceebae28683abd','before_cases':14,'before_failed':10,'before_controls_passed':4,
 'source_inverse_exact':True,'schema_unchanged':31,'transport_and_factor_proof_unchanged':True,'changes':{}}
for name,after in edits.items():
    stem=name.replace('/','__');(out/(stem+'.before.RAW')).write_bytes(blobs[name])
    (out/(stem+'.before.GitLF')).write_bytes(git('show','HEAD:'+name))
    (root/name).write_bytes(after);(out/(stem+'.after.RAW')).write_bytes(after)
    receipt['changes'][name]={'before_sha256':hashlib.sha256(blobs[name]).hexdigest(),'after_sha256':hashlib.sha256(after).hexdigest()}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps({'changed':list(edits),'before_preserved':True,'inverse_exact':True,'capacity':'Fail409 before beginning/changing factor and again before increment; identity accepts inclusive MAX.'}))
