/* Public contact-only confirmation. No Api bootstrap, identity or Storage. */
(function () {
    'use strict';
    const form = document.getElementById('email-confirmation');
    const button = document.getElementById('confirm-email');
    const status = document.getElementById('confirmation-status');
    const fragment = new URLSearchParams(location.hash.slice(1));
    let proof = fragment.getAll('token').length === 1 && [...fragment.keys()].every(key => key === 'token')
        ? fragment.get('token') : null;
    try {
        history.replaceState(null, '', location.pathname);
    } catch (_) {
        proof = null;
    }
    if (!proof || !/^[A-Za-z0-9_-]{43}$/.test(proof)) {
        proof = null;
        status.textContent = 'El enlace no está disponible. Solicita uno nuevo desde tu cuenta.';
        return;
    }
    button.disabled = false;
    status.textContent = 'Pulsa el botón para confirmar tu correo.';
    let pending = false;
    form.addEventListener('submit', async function (event) {
        event.preventDefault();
        if (pending || !proof) return;
        pending = true;
        button.disabled = true;
        const token = proof;
        proof = null;
        try {
            const response = await fetch('/api/account/security/email/confirm', {
                method: 'POST', credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer',
                headers: { 'Content-Type': 'application/json', 'X-MetodoBase-Browser': '1' },
                body: JSON.stringify({ token })
            });
            const result = await response.json();
            status.textContent = response.ok && result.code === 'account_email_confirmed' && result.email_verified === true
                ? 'Correo confirmado. Puedes volver a tu cuenta.'
                : response.status >= 500
                    ? 'No pudimos confirmar la operación. Consulta el estado desde tu cuenta antes de solicitar otro enlace.'
                    : 'El enlace no está disponible. Solicita uno nuevo desde tu cuenta.';
        } catch (_) {
            status.textContent = 'No pudimos confirmar la operación. Consulta el estado desde tu cuenta antes de solicitar otro enlace.';
        }
    });
    addEventListener('pagehide', function () { proof = null; button.disabled = true; });
}());
