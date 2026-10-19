"""Keep the browser's revocation wait aligned with the reviewed account copy."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path(r'F:\mb-mfa31-compose-20261019')
out = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa-ui31-browser-copy-wait-20261019')
base = 'da34304aaf9066f45c6fc854cfd81d00e2fbc581'
name = 'tests/e2e/mfa_ui_browser.cjs'
git = lambda *args: subprocess.check_output(['git', *args], cwd=root)
assert git('rev-parse', 'HEAD').decode().strip() == base and not git('status', '--porcelain', '--untracked-files=no')
path = root / name
before = path.read_bytes()
assert git('hash-object', '--path=' + name, '--', name).strip() == git('rev-parse', base + ':' + name).strip()
old = b".textContent.includes('Factor revocado')"
new = ".textContent.includes('Autenticación en dos pasos desactivada y sesión cerrada.')".encode()
assert before.count(old) == 1 and new not in before
after = before.replace(old, new)
assert after.replace(new, old) == before
assert "Autenticación en dos pasos desactivada y sesión cerrada." in (root / 'web/static/js/mfa-ui.js').read_text(encoding='utf8')
out.mkdir(exist_ok=False)
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
(out / 'before.raw.cjs').write_bytes(before)
(out / 'after.raw.cjs').write_bytes(after)
path.write_bytes(after)
subprocess.run([r'C:\Program Files\nodejs\node.exe', '--check', name], cwd=root, check=True, capture_output=True)
assert git('diff', '--name-only', '-z').decode().split('\0')[:-1] == [name]
subprocess.run(['git', 'diff', '--check', '--', name], cwd=root, check=True, capture_output=True)
subprocess.run(['git', 'add', '--', name], cwd=root, check=True, capture_output=True)
subprocess.run(['git', 'commit', '-m', 'Align MFA revocation browser wait with account wording'], cwd=root, check=True, capture_output=True)
receipt = {'before': base, 'head': git('rev-parse', 'HEAD').decode().strip(),
           'before_RAW_sha256': hashlib.sha256(before).hexdigest(), 'after_RAW_sha256': hashlib.sha256(after).hexdigest(),
           'sole_change': 'One wait predicate literal follows the new revocation message; inverse bytes exact. Existing kit0, local sessionnull and every other assertion are unchanged.',
           'cause': 'Independent QA found the maintained author browser wait used the old text before launching Chrome. No browser failure or product regression is claimed; no browser executed by this correction.',
           'product_changed': False, 'node_syntax_exit': 0}
(out / 'receipt.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
assert not git('status', '--porcelain', '--untracked-files=no')
print(json.dumps(receipt))
