/**
 * api.js — Cliente HTTP para MetodoBase API
 * Incluye token Bearer en cada petición. Redirige al login si recibe 401.
 */

const API_BASE = '';  // mismo origen

const Api = (() => {

  function getToken() {
    return localStorage.getItem('mb_token') || '';
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

    // Sesión expirada → redirigir al inicio
    if (res.status === 401) {
      localStorage.removeItem('mb_token');
      window.location.href = '/';
      throw new Error('Sesión expirada.');
    }

    const data = await res.json();

    if (!res.ok) {
      const msg = data.detail || data.message || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  // ── Clientes ──────────────────────────────────────────────────────────────

  const clientes = {
    listar: (q = '', limite = 100) => {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
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
    generar: (id_cliente, plan_numero = 1) =>
      request('POST', '/api/generar-plan', { id_cliente, plan_numero }),

    descargar: (id_cliente) => {
      const token = getToken();
      window.open(`/api/descargar-pdf/${id_cliente}`, '_blank');
    },

    descargarPdf: (id_cliente) => {
      window.open(`/api/descargar-pdf/${id_cliente}`, '_blank');
    },
  };

  // ── Estadísticas ──────────────────────────────────────────────────────────

  const stats = {
    obtener:     () => request('GET', '/api/estadisticas'),
    objetivos:   () => request('GET', '/api/estadisticas/objetivos'),
    planesTiempo:() => request('GET', '/api/estadisticas/planes-tiempo'),
  };

  // ── Auth ──────────────────────────────────────────────────────────────────

  const auth = {
    loginGym:     (email, password) => request('POST', '/api/auth/login-gym',    { email, password }),
    loginUsuario: (email, password) => request('POST', '/api/auth/login-usuario', { email, password }),
    registro:     (data)            => request('POST', '/api/auth/registro',      data),
    me:           ()                => request('GET',  '/api/auth/me'),
  };

  return { clientes, planes, stats, auth };
})();

