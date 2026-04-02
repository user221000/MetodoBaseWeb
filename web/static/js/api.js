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

  async function request(method, path, body = null) {
    const token = getToken();
    const opts = {
      method,
      headers: {
        'Content-Type': 'application/json',
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
    if (res.status === 401) {
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

    const data = await res.json();

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

    generar: (id_cliente, plan_numero = 1, tipo_plan = 'menu_fijo') =>
      request('POST', '/api/generar-plan', { id_cliente, plan_numero, tipo_plan }),

    descargar: async (id_cliente) => {
      async function _fetchPdf(tkn) {
        return fetch(`/api/descargar-pdf/${id_cliente}`, {
          headers: tkn ? { 'Authorization': `Bearer ${tkn}` } : {},
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
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `plan_${id_cliente}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
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
    checkout: (plan) =>
      request('POST', '/api/billing/checkout', {
        plan,
        success_url: '/suscripciones?result=success',
        cancel_url: '/suscripciones?result=canceled',
      }),
    stripeSubscribe: (plan, payment_method_id) =>
      request('POST', '/api/billing/stripe/subscribe', {
        plan,
        payment_method_id,
      }),
    confirmSubscription: (subscription_id) =>
      request('POST', '/api/billing/confirm-subscription', {
        subscription_id,
      }),
    mpPreference: (plan) =>
      request('POST', '/api/billing/mp/preference', {
        plan,
        success_url: '/suscripciones?result=success',
        cancel_url: '/suscripciones?result=canceled',
      }),
    portal: () =>
      request('POST', '/api/billing/portal', {
        return_url: '/suscripciones',
      }),
  };

  // ── Gym Profile ─────────────────────────────────────────────────────────────

  const gym = {
    getProfile: () => request('GET', '/api/gym/profile'),

    updateProfile: (data) => request('PUT', '/api/gym/profile', data),

    uploadLogo: async (file) => {
      const token = getToken();
      const formData = new FormData();
      formData.append('file', file);
      const opts = {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        body: formData,
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
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
      return data;
    },

    // ── Planes de suscripción ──
    listarPlanes: () => request('GET', '/api/gym/planes-suscripcion'),
    actualizarPlan: (planId, data) => request('PUT', `/api/gym/planes-suscripcion/${planId}`, data),
  };

  // ── Usuario Individual ────────────────────────────────────────────────────

  const usuario = {
    perfil:         () => request('GET', '/api/usuario/perfil'),
    guardarPerfil:  (data) => request('PUT', '/api/usuario/perfil', data),
    miPlan:         () => request('GET', '/api/usuario/mi-plan'),
    generarPlan:    () => request('POST', '/api/usuario/generar-plan'),
    historial:      () => request('GET', '/api/usuario/historial'),
    suscripcion:    () => request('GET', '/api/usuario/suscripcion'),
    cambiarPlan:    (plan) => request('POST', '/api/usuario/suscripcion', { plan }),
    billingConfig:  () => request('GET', '/api/usuario/billing-config'),
    stripeSubscribe: (plan, payment_method_id) =>
      request('POST', '/api/usuario/stripe-subscribe', { plan, payment_method_id }),
    confirmSubscription: (subscription_id) =>
      request('POST', '/api/usuario/confirm-subscription', { subscription_id }),
    mpPreference:   (plan) =>
      request('POST', '/api/usuario/mp-preference', {
        plan,
        success_url: '/mi-suscripcion?result=success',
        cancel_url: '/mi-suscripcion?result=canceled',
      }),
  };

  return { clientes, planes, stats, auth, billing, gym, usuario, clearTokens, saveTokens };
})();

