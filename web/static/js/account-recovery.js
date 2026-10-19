/* Public recovery only: no authentication/storage SDK, bearer stays in memory. */
(() => {
  'use strict';
  const params = new URLSearchParams(window.location.hash.slice(1));
  let token = params.get('token') || '';
  window.history.replaceState(null, '', window.location.pathname);
  const requestForm = document.getElementById('recovery-request');
  const confirmForm = document.getElementById('recovery-confirm');
  const status = document.getElementById('recovery-status');
  const password = document.getElementById('recovery-password');
  const confirmation = document.getElementById('recovery-confirmation');
  const hasToken = /^[A-Za-z0-9_-]{43}$/.test(token) && [...params.keys()].length === 1;
  if (hasToken) { requestForm.hidden = true; confirmForm.hidden = false; }
  else if (token) { token = ''; status.textContent = 'El enlace no está disponible. Solicita uno nuevo.'; }
  const clearPasswords = () => { password.value = ''; confirmation.value = ''; };
  window.addEventListener('pagehide', () => { token = ''; clearPasswords(); });
  async function post(path, body) {
    const response = await fetch('/api/auth/password-reset/' + path, {
      method: 'POST', credentials: 'omit', cache: 'no-store',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
    });
    let data; try { data = await response.json(); } catch (_) { data = {}; }
    return {response, data};
  }
  requestForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (!requestForm.reportValidity()) return;
    const button = requestForm.querySelector('button'); button.disabled = true;
    status.textContent = 'Procesando solicitud…';
    try {
      const {response, data} = await post('request', {email: document.getElementById('recovery-email').value});
      status.textContent = response.status === 202 ? data.message :
        (data.detail?.message || 'La recuperación no está disponible. Reintenta más tarde.');
    } catch (_) { status.textContent = 'No se pudo confirmar la solicitud. Puedes intentarlo de nuevo.'; }
    finally { button.disabled = false; }
  });
  confirmForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (!confirmForm.reportValidity()) return;
    if (password.value !== confirmation.value || new TextEncoder().encode(password.value).length > 72) {
      status.textContent = 'Revisa que las contraseñas coincidan y ocupen hasta 72 bytes UTF-8.'; return;
    }
    const button = confirmForm.querySelector('button'); button.disabled = true;
    status.textContent = 'Guardando contraseña…';
    try {
      const {response, data} = await post('confirm', {token, new_password: password.value, confirm_password: confirmation.value});
      status.textContent = response.ok ? data.message :
        (data.detail?.message || 'No pudimos confirmar el cambio. Intenta iniciar sesión con la nueva contraseña o pide otro enlace.');
      if (response.ok || response.status === 400 || response.status === 503) {
        token = ''; clearPasswords(); confirmForm.hidden = true; requestForm.hidden = !response.ok ? false : true;
      }
    } catch (_) {
      token = ''; clearPasswords(); confirmForm.hidden = true; requestForm.hidden = false;
      status.textContent = 'No pudimos confirmar el cambio. Intenta iniciar sesión con la nueva contraseña o pide otro enlace.';
    } finally { button.disabled = false; }
  });
})();
