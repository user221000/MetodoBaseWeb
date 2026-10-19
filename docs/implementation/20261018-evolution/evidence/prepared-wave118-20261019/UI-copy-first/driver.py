"""Replace internal security wording with account instructions, preserving behavior."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(r'F:\mb-mfa31-compose-20261019')
OUT = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa-ui31-copy-20261019')
BASE = '5e91115ef5e58159c04faf7fe6a26d37b22f1291'
CHANGES = {
    'web/templates/mfa_account_partial.html': {
        'El factor protege tu cuenta. No concede roles, acceso a otra cartera ni permisos adicionales.': 'Protege tu cuenta con una aplicación de autenticación y guarda tus códigos de recuperación.',
        'Para reemplazar un factor activo necesitas una primaria reciente y el factor vigente. Un token renovado no sustituye esa primaria.': 'Para cambiar el autenticador, verifica tu contraseña o tu cuenta de Google y confirma un código del método actual.',
        'Factor vigente': 'Método actual',
        'Prueba del método elegido': 'Código del método elegido',
        'Verificar primaria y solicitar este cambio': 'Verificar mi identidad y solicitar el cambio',
        'Sin todos los factores o códigos no hay un bypass por correo ni un operador simulado. No se promete recuperación externa disponible.': 'Guarda tus códigos en un lugar seguro. Si pierdes el autenticador y todos los códigos, actualmente no hay un método alternativo para recuperar el acceso.',
    },
    'web/static/js/mfa-login.js': {
        'La primaria fue válida. Confirma un factor para iniciar sesión.': 'Ahora confirma tu código para iniciar sesión.',
        'Comprobando la autenticación primaria…': 'Comprobando tus datos de acceso…',
        'Comprobando la primaria de Google…': 'Comprobando tu cuenta de Google…',
    },
    'web/static/js/mfa-ui.js': {
        'Se necesita una primaria reciente verificable. Usa tu contraseña o autentícate otra vez con Google; emitir un token nuevo no basta.': 'Vuelve a verificar tu identidad con tu contraseña o con Google para continuar.',
        'La sesión cambió. Se descartaron los secretos anteriores.': 'La sesión cambió. Se cerró la verificación anterior.',
        'No se pudo confirmar el almacenamiento de la sesión. No se muestra ningún secreto ni éxito.': 'No se pudo guardar la sesión de forma segura. Vuelve a iniciar sesión.',
        'Estado consultado. Cambiar el factor requiere una primaria reciente y tu confirmación.': 'Estado actualizado. Confirma tu identidad para hacer cambios.',
        'Verificando la primaria; el cambio aún no está confirmado…': 'Verificando tu identidad; el cambio aún no está confirmado…',
        'La semilla pendiente venció. Inicia otra verificación primaria.': 'La clave de configuración venció. Vuelve a verificar tu identidad.',
        'Factor revocado y sesión cerrada en este navegador. Las acciones protegidas volverán a requerir enrolamiento.': 'Autenticación en dos pasos desactivada y sesión cerrada. Para hacer cambios protegidos tendrás que activarla de nuevo.',
        'Escribe tu contraseña o usa el botón de Google para una primaria reciente.': 'Escribe tu contraseña o verifica tu cuenta con el botón de Google.',
        'Google no se pudo cargar. Puedes usar tu contraseña; la reautenticación real del proveedor debe estar configurada.': 'No se pudo cargar Google. Usa tu contraseña o vuelve a intentarlo.',
        'Esperando una primaria reciente del proveedor. No se confirmó ningún cambio.': 'Confirma tu cuenta de Google para continuar.',
        'Google no está configurado para una primaria reciente. Puedes usar tu contraseña; no se fabricará metadata del proveedor.': 'La verificación con Google no está disponible. Usa tu contraseña.',
    },
}
git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT)
assert git('rev-parse', 'HEAD').decode().strip() == BASE and not git('status', '--porcelain', '--untracked-files=no')
OUT.mkdir(exist_ok=False)
(OUT / 'driver.py').write_bytes(Path(__file__).read_bytes())
receipt = {'base': BASE, 'files': {}, 'scope': 'Presentation strings only, no controller state, API, selectors, timing, CSS, authorization or persistence changes. Original author freezes and screenshots remain unchanged.'}
for name, changes in CHANGES.items():
    path = ROOT / name
    before = path.read_bytes()
    assert before == git('show', BASE + ':' + name)
    after = before
    for old, new in changes.items():
        old_bytes, new_bytes = old.encode(), new.encode()
        assert after.count(old_bytes) == 1 and new_bytes not in after
        after = after.replace(old_bytes, new_bytes)
    inverse = after
    for old, new in reversed(list(changes.items())):
        assert inverse.count(new.encode()) == 1
        inverse = inverse.replace(new.encode(), old.encode())
    assert inverse == before
    (OUT / (path.name + '.before.raw')).write_bytes(before)
    (OUT / (path.name + '.after.raw')).write_bytes(after)
    path.write_bytes(after)
    receipt['files'][name] = {'before_sha256': hashlib.sha256(before).hexdigest(), 'after_sha256': hashlib.sha256(after).hexdigest(),
                            'literal_replacements': len(changes), 'inverse_bytes_exact': True}
for name in CHANGES:
    if name.endswith('.js'):
        subprocess.run([r'C:\Program Files\nodejs\node.exe', '--check', name], cwd=ROOT, check=True, capture_output=True)
assert set(git('diff', '--name-only', '-z').decode().split('\0')[:-1]) == set(CHANGES)
subprocess.run(['git', 'diff', '--check', '--', *CHANGES], cwd=ROOT, check=True, capture_output=True)
subprocess.run(['git', 'add', '--', *CHANGES], cwd=ROOT, check=True, capture_output=True)
subprocess.run(['git', 'commit', '-m', 'Explain MFA account steps with user-facing language'], cwd=ROOT, check=True, capture_output=True)
receipt['head'] = git('rev-parse', 'HEAD').decode().strip()
assert not git('status', '--porcelain', '--untracked-files=no')
(OUT / 'receipt.json').write_bytes((json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode())
print(json.dumps({'head': receipt['head'], 'files': len(CHANGES), 'literal_replacements': sum(len(c) for c in CHANGES.values()), 'inverse_bytes_exact': True}))
