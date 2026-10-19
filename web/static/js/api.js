/**
 * api.js — Cliente HTTP para MetodoBase API
 * Incluye token Bearer en cada petición.
 * Auto-refresh: si recibe 401, intenta renovar con refresh token antes de redirigir.
 */

const API_BASE = '';  // mismo origen

const Api = (() => {

  let _isRefreshing = false;
  let _refreshQueue = [];

  function getToken() {
    return localStorage.getItem('mb_token') || '';
  }

  function getRefreshToken() {
    return localStorage.getItem('mb_refresh_token') || '';
  }

  function saveTokens(data) {
    if (data.token) localStorage.setItem('mb_token', data.token);
    if (data.refresh_token) localStorage.setItem('mb_refresh_token', data.refresh_token);
  }

  function clearTokens() {
    localStorage.removeItem('mb_token');
    localStorage.removeItem('mb_refresh_token');
  }

  function getLoginUrl() {
    var tipo = localStorage.getItem('mb_tipo');
    return tipo === 'usuario' ? '/login-usuario' : '/login-gym';
  }

  async function _doRefresh() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    try {
      const res = await fetch(API_BASE + '/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) return false;

      const data = await res.json();
      saveTokens(data);
      return true;
    } catch {
      return false;
    }
  }

  async function _handleRefresh() {
    if (_isRefreshing) {
      // Esperar a que termine el refresh en curso
      return new Promise((resolve) => {
        _refreshQueue.push(resolve);
      });
    }

    _isRefreshing = true;
    const success = await _doRefresh();
    _isRefreshing = false;

    // Resolver todas las peticiones que estaban esperando
    _refreshQueue.forEach(resolve => resolve(success));
    _refreshQueue = [];

    return success;
  }

  async function request(method, path, body = null, extraHeaders = {}, authenticated = true) {
    const token = authenticated ? getToken() : '';
    const opts = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...extraHeaders,
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    };
    if (body !== null) opts.body = JSON.stringify(body);

    let res;
    try {
      res = await fetch(API_BASE + path, opts);
    } catch (networkErr) {
      throw new Error('Error de red: no se pudo conectar al servidor.');
    }

    // 401 → intentar refresh antes de redirigir
    if (res.status === 401 && authenticated) {
      const refreshed = await _handleRefresh();
      if (refreshed) {
        // Reintentar la petición original con el nuevo token
        const newToken = getToken();
        opts.headers['Authorization'] = `Bearer ${newToken}`;
        try {
          res = await fetch(API_BASE + path, opts);
        } catch (networkErr) {
          throw new Error('Error de red: no se pudo conectar al servidor.');
        }
        if (res.status === 401) {
          clearTokens();
          window.location.href = getLoginUrl();
          throw new Error('Sesión expirada.');
        }
      } else {
        clearTokens();
        window.location.href = getLoginUrl();
        throw new Error('Sesión expirada.');
      }
    }

    let data;
    try { data = await res.json(); }
    catch {
      if (res.ok && res.status !== 204) throw new Error('El servidor devolvió una respuesta no válida. Intenta consultar de nuevo.');
      data = {};
    }

    if (!res.ok) {
      let msg;
      let errorCode = null;
      let upgradeUrl = null;
      if (Array.isArray(data.detail)) {
        msg = data.detail.map(e => e.msg || JSON.stringify(e)).join('; ');
      } else if (data.detail && typeof data.detail === 'object') {
        // Structured error from backend (subscription_guard, feature_gate, etc.)
        msg = data.detail.message || data.detail.detail || JSON.stringify(data.detail);
        errorCode = data.detail.code || null;
        upgradeUrl = data.detail.upgrade_url || null;
      } else {
        msg = data.detail || data.message || `HTTP ${res.status}`;
      }
      const err = new Error(msg);
      err.status = res.status;
      err.requestId = (data.detail && data.detail.request_id) || res.headers.get('X-Request-ID') || null;
      if (errorCode) err.code = errorCode;
      if (upgradeUrl) err.upgradeUrl = upgradeUrl;
      throw err;
    }
    return data;
  }

  // ── Clientes ──────────────────────────────────────────────────────────────

  const clientes = {
    listar: (q = '', limite = 300, filter = '') => {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      if (filter) params.set('filter', filter);
      params.set('limite', limite);
      return request('GET', `/api/clientes?${params}`);
    },

    obtener: (id) => request('GET', `/api/clientes/${id}`),

    crear: (data) => request('POST', '/api/clientes', data),

    actualizar: (id, data) => request('PUT', `/api/clientes/${id}`, data),

    eliminar: (id) => request('DELETE', `/api/clientes/${id}`),
  };

  // ── Planes ────────────────────────────────────────────────────────────────

  const planes = {
    listar: (limite = 50, offset = 0, periodo = '') => {
      const params = new URLSearchParams({ limite, offset });
      if (periodo) params.set('periodo', periodo);
      return request('GET', `/api/planes?${params}`);
    },

    resumen: () => request('GET', '/api/planes/resumen'),

    generar: (id_cliente, plan_numero = 1, tipo_plan = 'menu_fijo', operationKey) => {
      if (typeof operationKey !== 'string' || !operationKey.trim()) {
        throw new Error('Falta identificar la solicitud. Vuelve a preparar el plan.');
      }
      return request('POST', '/api/generar-plan', { id_cliente, plan_numero, tipo_plan },
        { 'Idempotency-Key': operationKey });
    },

    contexto: async () => {
      const me = await request('GET', '/api/auth/me');
      if (!me || typeof me.id !== 'string' || !me.id || !me.role) {
        throw new Error('No se pudo verificar la cuenta actual.');
      }
      return JSON.stringify([me.id, me.team_gym_id || null, me.role, me.session_version]);
    },

    descargarPorPlan: (planId) => {
      if (!Number.isSafeInteger(planId) || planId < 1 || planId > 2147483647) throw new Error('El plan no es válido.');
      return planes._descargar(`/api/planes/${planId}/pdf`, `plan_${planId}.pdf`);
    },

    // Compatibilidad para vistas que solicitan explícitamente el último plan.
    descargar: (id_cliente) => planes._descargar(
      `/api/descargar-pdf/${encodeURIComponent(id_cliente)}`, 'ultimo_plan.pdf'),

    _descargar: async (path, filename) => {
      const context = await planes.contexto();
      let invalidated = false;
      const invalidate = (event) => {
        if (event.type === 'pagehide' || event.key === null || ['mb_token', 'mb_refresh_token'].includes(event.key)) invalidated = true;
      };
      window.addEventListener('storage', invalidate);
      window.addEventListener('pagehide', invalidate);
      try {
      async function _fetchPdf(tkn) {
        return fetch(path, {
          headers: tkn ? { 'Authorization': `Bearer ${tkn}` } : {},
          cache: 'no-store',
        });
      }

      let res = await _fetchPdf(getToken());

      // 401 → intentar refresh y reintentar
      if (res.status === 401) {
        const refreshed = await _handleRefresh();
        if (refreshed) {
          res = await _fetchPdf(getToken());
        }
        if (!refreshed || res.status === 401) {
          clearTokens();
          window.location.href = getLoginUrl();
          throw new Error('Sesión expirada.');
        }
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(typeof err.detail === 'string' ? err.detail : 'No se pudo descargar este plan.');
      }
      const blob = await res.blob();
      if (!res.headers.get('Content-Type')?.toLowerCase().startsWith('application/pdf') ||
          blob.size === 0 || await blob.slice(0, 5).text() !== '%PDF-') {
        throw new Error('El servidor no devolvió un PDF válido.');
      }
      if (invalidated || await planes.contexto() !== context || invalidated) {
        throw new Error('La sesión cambió. Vuelve a abrir el plan desde tu cuenta.');
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      const cleanup = () => { URL.revokeObjectURL(url); window.removeEventListener('pagehide', cleanup); };
      window.addEventListener('pagehide', cleanup, { once: true });
      setTimeout(cleanup, 2000);
      } finally {
        window.removeEventListener('storage', invalidate);
        window.removeEventListener('pagehide', invalidate);
      }
    },
  };

  // ── Estadísticas ──────────────────────────────────────────────────────────

  const stats = {
    obtener: (periodo) => {
      const params = periodo ? `?periodo=${periodo}` : '';
      return request('GET', `/api/estadisticas${params}`);
    },
    objetivos:    () => request('GET', '/api/estadisticas/objetivos'),
    planesTiempo: () => request('GET', '/api/estadisticas/planes-tiempo'),
    suscripciones:() => request('GET', '/api/estadisticas/suscripciones'),
  };

  // ── Auth ──────────────────────────────────────────────────────────────────

  const auth = {
    loginGym: async (email, password) => {
      const data = await request('POST', '/api/auth/login', { email, password });
      saveTokens(data);
      return data;
    },
    loginUsuario: async (email, password) => {
      const data = await request('POST', '/api/auth/login', { email, password });
      saveTokens(data);
      return data;
    },
    registro: async (payload) => {
      const data = await request('POST', '/api/auth/registro', payload);
      saveTokens(data);
      return data;
    },
    me:     () => request('GET',  '/api/auth/me'),
    logout: async () => {
      try {
        await request('POST', '/api/auth/logout');
      } catch { /* ignore — clear tokens anyway */ }
      clearTokens();
    },
  };

  // ── Billing ────────────────────────────────────────────────────────────────

  const billing = {
    config:       () => request('GET', '/api/billing/config'),
    subscription: () => request('GET', '/api/billing/subscription'),
    payments:     () => request('GET', '/api/billing/payments'),
    checkout: (plan, key) =>
      request('POST', '/api/billing/checkout', {
        plan,
        success_url: '/suscripciones?result=success',
        cancel_url: '/suscripciones?result=canceled',
      }, key ? { 'Idempotency-Key': key } : {}),
    stripeSubscribe: (plan, payment_method_id) =>
      request('POST', '/api/billing/stripe/subscribe', {
        plan,
        payment_method_id,
      }),
    confirmSubscription: (subscription_id) =>
      request('POST', '/api/billing/confirm-subscription', {
        subscription_id,
      }),
    mpPreference: (plan, key) =>
      request('POST', '/api/billing/mp/preference', {
        plan,
        success_url: '/suscripciones?result=success',
        cancel_url: '/suscripciones?result=canceled',
      }, key ? { 'Idempotency-Key': key } : {}),
    portal: () =>
      request('POST', '/api/billing/portal', {
        return_url: '/suscripciones',
      }),
  };

  // ── Gym Profile ─────────────────────────────────────────────────────────────

  const gym = {
    getProfile: () => request('GET', '/api/gym/profile'),

    updateProfile: (data) => request('PUT', '/api/gym/profile', data),

    getLogoBlob: () => gym._logoRequest('GET'),

    uploadLogo: (file) => gym._logoRequest('POST', file),

    _logoRequest: async (method, file = null) => {
      const token = getToken();
      const formData = file ? new FormData() : null;
      if (file) formData.append('file', file);
      const opts = {
        method,
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        ...(formData ? { body: formData } : {}),
        cache: 'no-store',
        referrerPolicy: 'no-referrer',
      };
      let res = await fetch(API_BASE + '/api/gym/logo', opts);
      if (res.status === 401) {
        const refreshed = await _handleRefresh();
        if (refreshed) {
          opts.headers['Authorization'] = `Bearer ${getToken()}`;
          res = await fetch(API_BASE + '/api/gym/logo', opts);
        }
        if (!refreshed || res.status === 401) {
          clearTokens();
          window.location.href = getLoginUrl();
          throw new Error('Sesión expirada.');
        }
      }
      if (res.ok && method === 'GET') {
        const mime = (res.headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
        if (!['image/png', 'image/jpeg', 'image/webp'].includes(mime)) throw new Error('El servidor no devolvió una imagen válida.');
        const blob = await res.blob();
        if (!blob.size || blob.size > 2 * 1024 * 1024) throw new Error('El logo guardado no tiene un tamaño válido.');
        return blob;
      }
      let data;
      try { data = await res.json(); }
      catch { throw new Error('El servidor no confirmó la carga del logo.'); }
      if (!res.ok) {
        const detail = data && data.detail;
        const error = new Error(typeof detail === 'string' ? detail : detail && typeof detail.message === 'string' ? detail.message : 'No se pudo acceder al logo.');
        error.status = res.status;
        if (detail && typeof detail.code === 'string') error.code = detail.code;
        throw error;
      }
      return data;
    },

    // ── Planes de suscripción ──
    listarPlanes: () => request('GET', '/api/gym/planes-suscripcion'),
    actualizarPlan: (planId, data) => request('PUT', `/api/gym/planes-suscripcion/${planId}`, data),
  };

  // ── Usuario Individual ────────────────────────────────────────────────────

  const usuario = {
    exportarDatos: (cursors = {}) => {
      const params = new URLSearchParams({limit:'100'});
      const integerCursors = ['profile','plan','measurement'];
      const uuidCursors = ['purchase','generation'];
      for (const name of [...integerCursors,...uuidCursors]) {
        const value = cursors[name];
        if (value == null) continue;
        if (integerCursors.includes(name) ? !Number.isSafeInteger(value) || value < 0 : typeof value !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) {
          throw new Error('No se pudo continuar la descarga. Empieza una descarga nueva.');
        }
        params.set('after_'+name,String(value));
      }
      return request('GET','/api/usuario/privacidad/exportar?'+params, null, {'Cache-Control':'no-store'});
    },
    perfil:         () => request('GET', '/api/usuario/perfil'),
    guardarPerfil:  (data) => request('PUT', '/api/usuario/perfil', data),
    miPlan:         () => request('GET', '/api/usuario/mi-plan'),
    generarPlan:    () => request('POST', '/api/usuario/generar-plan'),
    historial:      () => request('GET', '/api/usuario/historial'),
    suscripcion:    () => request('GET', '/api/usuario/suscripcion'),
    cambiarPlan:    (plan) => request('POST', '/api/usuario/suscripcion', { plan }),
    billingConfig:  () => request('GET', '/api/usuario/billing-config'),
    checkout: (key) => request('POST', '/api/usuario/checkout', {
      success_url: '/mi-suscripcion?result=success',
      cancel_url: '/mi-suscripcion?result=canceled',
    }, { 'Idempotency-Key': key }),
    portal: () => request('POST', '/api/usuario/billing-portal', { return_url: '/mi-suscripcion' }),
    stripeSubscribe: (plan, payment_method_id) =>
      request('POST', '/api/usuario/stripe-subscribe', { plan, payment_method_id }),
    confirmSubscription: (subscription_id) =>
      request('POST', '/api/usuario/confirm-subscription', { subscription_id }),
    mpPreference:   (plan, key) =>
      request('POST', '/api/usuario/mp-preference', {
        plan,
        success_url: '/mi-suscripcion?result=success',
        cancel_url: '/mi-suscripcion?result=canceled',
      }, key ? { 'Idempotency-Key': key } : {}),
  };

  const team = {
    list: () => request('GET', '/api/gym/team'),
    invite: (data) => request('POST', '/api/gym/team/invite', data),
    role: (id, role) => request('PATCH', '/api/gym/team/' + encodeURIComponent(id) + '/role', {role}),
    remove: (id) => request('DELETE', '/api/gym/team/' + encodeURIComponent(id)),
    resend: (id) => request('POST', '/api/gym/team/' + encodeURIComponent(id) + '/resend-invite'),
    info: (token) => request('POST', '/api/auth/invite-info', {token}, {}, false),
    accept: (token, password) => request('POST', '/api/auth/accept-invite', {token,password}, {}, false),
  };
  return { clientes, planes, stats, auth, billing, gym, usuario, team, clearTokens, saveTokens };
})();

