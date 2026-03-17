/**
 * api.js — Cliente HTTP para MetodoBase API
 * Todos los métodos retornan Promise con el JSON ya parseado.
 */

const API_BASE = '';  // mismo origen

const Api = (() => {

  async function request(method, path, body = null) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body !== null) opts.body = JSON.stringify(body);

    const res = await fetch(API_BASE + path, opts);
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
      window.open(`/api/descargar-pdf/${id_cliente}`, '_blank');
    },

    descargarPdf: (id_cliente) => {
      window.open(`/api/descargar-pdf/${id_cliente}`, '_blank');
    },
  };

  // ── Estadísticas ──────────────────────────────────────────────────────────

  const stats = {
    obtener: () => request('GET', '/api/estadisticas'),
  };

  return { clientes, planes, stats };
})();
