/* Private branding previews live only in memory. URLs never contain tokens. */
(function () {
  'use strict';
  const section = document.getElementById('gym-logo-section');
  if (!section) return;
  const fields = {
    'cfg-nombre': 'nombre_negocio', 'cfg-direccion': 'direccion',
    'cfg-ciudad': 'ciudad', 'cfg-estado': 'estado', 'cfg-telefono': 'telefono',
    'cfg-web': 'sitio_web', 'cfg-rfc': 'rfc', 'cfg-instagram': 'instagram',
    'cfg-facebook': 'facebook', 'cfg-tiktok': 'tiktok',
  };
  const picker = document.getElementById('logo-picker');
  const input = document.getElementById('logo-input');
  const reload = document.getElementById('logo-reload');
  const image = document.getElementById('logo-img');
  const placeholder = document.getElementById('logo-placeholder');
  const status = document.getElementById('logo-upload-status');
  const errorBox = document.getElementById('logo-error');
  const save = document.getElementById('btn-guardar');
  const types = ['image/png', 'image/jpeg', 'image/webp'];
  const maxBytes = 2 * 1024 * 1024;
  let epoch = 0, context = null, current = null, invalidated = false;
  let busy = false, profileLoaded = false, previewUrl = null;

  function clearPreview() {
    image.removeAttribute('src'); image.hidden = true;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null; placeholder.hidden = false;
  }
  function canUpdate() {
    return !!current && Array.isArray(current.permissions) && current.permissions.some(value => Array.isArray(value) && value[0] === 'update' && value[1] === 'gym_profile');
  }
  function controls() {
    picker.disabled = input.disabled = busy || invalidated || !canUpdate();
    reload.disabled = busy || invalidated;
    save.disabled = busy || invalidated || !profileLoaded || !canUpdate();
    Object.keys(fields).forEach(id => { document.getElementById(id).disabled = busy || invalidated || !profileLoaded || !canUpdate(); });
    section.setAttribute('aria-busy', String(busy));
  }
  function fail(message) {
    errorBox.textContent = message; errorBox.hidden = false; errorBox.focus();
  }
  function invalidate() {
    epoch++; invalidated = true; busy = false; context = current = null;
    profileLoaded = false; clearPreview(); input.value = '';
    Object.keys(fields).forEach(id => { document.getElementById(id).value = ''; });
    document.getElementById('planes-grid').replaceChildren();
    document.getElementById('planes-loading').textContent = 'La sesión cambió. Abre de nuevo la configuración.';
    document.getElementById('successMsg').style.display = 'none';
    document.getElementById('errorMsg').style.display = 'none';
    placeholder.textContent = 'Vista previa no disponible';
    status.textContent = 'La sesión cambió. Abre de nuevo la configuración desde tu cuenta.';
    errorBox.hidden = true; controls();
  }
  async function verify(expected) {
    if (invalidated || expected !== epoch) throw new Error('La sesión cambió.');
    const me = await Api.auth.me();
    if (invalidated || expected !== epoch) throw new Error('La sesión cambió.');
    if (!me || typeof me.id !== 'string' || !me.id || typeof me.role !== 'string') throw new Error('No se pudo verificar la cuenta actual.');
    const next = JSON.stringify([me.id, me.team_gym_id || null, me.role, me.session_version]);
    if (context && context !== next) { invalidate(); throw new Error('La sesión cambió.'); }
    context = next; current = me; return me;
  }
  function validateProfile(profile) {
    if (!profile || profile.gym_id !== (current.team_gym_id || current.id)) {
      invalidate(); throw new Error('No se pudo verificar el perfil de esta cuenta.');
    }
    if (typeof profile.has_private_logo !== 'boolean' || typeof profile.logo_url !== 'string') throw new Error('El servidor no devolvió un perfil válido.');
  }
  function legacyPath(value) {
    let url;
    try { url = new URL(value, location.origin); } catch { throw new Error('No se pudo verificar el logo existente.'); }
    if (url.origin !== location.origin || url.username || url.password || url.search || url.hash ||
        !/^\/static\/uploads\/logos\/[a-z0-9_-]+\.(png|jpe?g|webp)$/i.test(url.pathname)) {
      throw new Error('No se pudo verificar el logo existente. Puedes subir una imagen nueva.');
    }
    return url.pathname;
  }
  async function validateImage(blob) {
    if (!(blob instanceof Blob) || !types.includes(blob.type.toLowerCase()) || !blob.size || blob.size > maxBytes) throw new Error('El servidor no devolvió una imagen PNG, JPG o WebP válida de hasta 2 MB.');
    let decoded;
    try {
      decoded = await createImageBitmap(blob);
      if (!decoded.width || !decoded.height || decoded.width * decoded.height > 16000000) throw new Error('Invalid dimensions');
    } catch { throw new Error('No se pudo verificar la imagen del logo.'); }
    finally { if (decoded) decoded.close(); }
  }
  async function preview(profile, expected) {
    clearPreview();
    if (!profile.has_private_logo && !profile.logo_url) {
      placeholder.textContent = 'Sin logo'; status.textContent = 'No hay un logo configurado.'; return;
    }
    let blob;
    if (profile.has_private_logo) {
      // A missing private object never falls back to a legacy URL.
      blob = await Api.gym.getLogoBlob();
    } else {
      const response = await fetch(legacyPath(profile.logo_url), { cache: 'no-store', referrerPolicy: 'no-referrer' });
      if (!response.ok) throw new Error('No se pudo cargar el logo existente.');
      blob = await response.blob();
    }
    await verify(expected);
    await validateImage(blob);
    await verify(expected);
    clearPreview(); previewUrl = URL.createObjectURL(blob);
    image.src = previewUrl; image.hidden = false; placeholder.hidden = true;
    try {
      await image.decode();
      await verify(expected);
      if (!image.naturalWidth || !image.naturalHeight) throw new Error('Image not displayed');
    } catch {
      clearPreview(); throw new Error('No se pudo mostrar la vista previa del logo. Vuelve a consultar el logo guardado.');
    }
    status.textContent = 'Vista previa del logo guardado.';
  }
  async function load() {
    if (busy || invalidated) return;
    const expected = epoch; busy = true; errorBox.hidden = true;
    status.textContent = 'Consultando el logo guardado...'; controls();
    try {
      await verify(expected);
      const profile = await Api.gym.getProfile();
      await verify(expected); validateProfile(profile);
      if (!profileLoaded) Object.entries(fields).forEach(([id, name]) => { document.getElementById(id).value = typeof profile[name] === 'string' ? profile[name] : ''; });
      profileLoaded = true;
      await preview(profile, expected);
    } catch (error) {
      try { await verify(expected); } catch { /* Previous-account responses never update this page. */ }
      if (!invalidated && expected === epoch) { clearPreview(); status.textContent = 'No se pudo mostrar la vista previa.'; fail(error.message || 'No se pudo cargar el logo.'); }
    } finally { if (!invalidated && expected === epoch) { busy = false; controls(); } }
  }
  async function upload(file) {
    if (!file || busy || invalidated || !canUpdate()) return;
    const expected = epoch; busy = true; errorBox.hidden = true; input.value = '';
    status.textContent = 'Subiendo el logo...'; controls();
    let attempted = false, confirmed = false;
    try {
      if (!types.includes(file.type.toLowerCase()) || !file.size || file.size > maxBytes) throw new Error('Elige una imagen PNG, JPG o WebP de hasta 2 MB.');
      await verify(expected); clearPreview();
      attempted = true;
      const result = await Api.gym.uploadLogo(file);
      await verify(expected);
      if (!result || result.success !== true || result.has_private_logo !== true || result.logo_url !== '/api/gym/logo') throw new Error('No se pudo confirmar la carga del logo.');
      confirmed = true;
      await preview(result, expected);
      status.textContent = 'Logo guardado. Vista previa actualizada.';
    } catch (error) {
      try { await verify(expected); } catch { /* Invalidation clears the old preview and form. */ }
      if (!invalidated && expected === epoch) {
        if (attempted) clearPreview();
        status.textContent = confirmed ? 'El logo fue guardado; su vista previa no está disponible.' : 'No se confirmó una nueva carga.';
        fail(confirmed ? 'No se pudo cargar el logo guardado. Vuelve a consultar la vista previa.' : attempted && (!error.status || error.status >= 500)
          ? 'No se pudo confirmar la carga. Consulta el logo guardado antes de volver a subirlo.' : error.message || 'No se pudo subir el logo.');
      }
    } finally { if (!invalidated && expected === epoch) { busy = false; controls(); } }
  }
  picker.addEventListener('click', () => { if (!busy && !invalidated && canUpdate()) input.click(); });
  input.addEventListener('change', () => { const file = input.files[0]; input.value = ''; upload(file); });
  reload.addEventListener('click', load);
  save.addEventListener('click', async () => {
    if (busy || invalidated || !profileLoaded || !canUpdate()) return;
    for (const id of Object.keys(fields)) if (!document.getElementById(id).reportValidity()) return;
    const expected = epoch, payload = {};
    Object.entries(fields).forEach(([id, name]) => { payload[name] = document.getElementById(id).value.trim(); });
    const success = document.getElementById('successMsg'), error = document.getElementById('errorMsg');
    success.style.display = error.style.display = 'none'; busy = true; controls();
    try {
      await verify(expected);
      const result = await Api.gym.updateProfile(payload);
      await verify(expected);
      if (!result || result.success !== true) throw new Error('No se pudo confirmar la actualización del perfil.');
      validateProfile(result.profile);
      success.textContent = 'Perfil actualizado. Los datos se usarán en los próximos PDFs.'; success.style.display = 'block';
    } catch (failure) {
      try { await verify(expected); } catch { /* Discard stale data before showing an error. */ }
      if (!invalidated && expected === epoch) { error.textContent = failure.message || 'No se pudo actualizar el perfil.'; error.style.display = 'block'; error.focus(); }
    } finally { if (!invalidated && expected === epoch) { busy = false; controls(); } }
  });
  window.addEventListener('storage', event => { if (event.key === null || ['mb_token', 'mb_refresh_token'].includes(event.key)) invalidate(); });
  window.addEventListener('pagehide', invalidate);
  window.addEventListener('pageshow', event => { if (event.persisted) invalidate(); });
  window.GymBranding = { verifyAccount: () => verify(epoch), canUpdate, isActive: () => !invalidated };
  controls(); load();
})();
