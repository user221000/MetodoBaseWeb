/**
 * api.js — Cliente HTTP para MetodoBase API
 * Incluye token Bearer en cada petición.
 * Auto-refresh: si recibe 401, intenta renovar con refresh token antes de redirigir.
 */

const API_BASE = '';  // mismo origen

const Api = (() => {

  let _refreshJob = null;
  const _storageErrors = new WeakSet();

  function getToken() {
    return localStorage.getItem('mb_token') || '';
  }

  function getRefreshToken() {
    return localStorage.getItem('mb_refresh_token') || '';
  }

  function _readPair() {
    try { return { token: getToken(), refresh: getRefreshToken() }; }
    catch (error) { throw _failStorage(error); }
  }
  function _samePair(left, right) {
    return left.token === right.token && left.refresh === right.refresh;
  }
  let _credentials = { pair: { token: '', refresh: '' }, revision: 0, trusted: false };
  try { _credentials.pair = _readPair(); _credentials.trusted = true; }
  catch { /* The API remains available for explicit recovery; authenticated I/O stays blocked. */ }
  function _storageError(cause) {
    const error = new Error('No se pudo verificar el almacenamiento de la sesión. Vuelve a iniciar sesión.', cause ? { cause } : undefined);
    error.code = 'session_storage_error';
    // Preserve standard Storage error names for callers; never expose its message or values.
    if (cause && ['QuotaExceededError', 'SecurityError', 'InvalidStateError'].includes(cause.name)) error.name = cause.name;
    _storageErrors.add(error);
    return error;
  }
  function _failStorage(cause) {
    _credentials = { ..._credentials, revision: _credentials.revision + 1, trusted: false };
    if (_storageErrors.has(cause)) return cause;
    return _storageError(cause);
  }
  function _requireTrusted() {
    if (!_credentials.trusted) throw _storageError();
  }
  function _currentCredentials() {
    const pair = _readPair();
    if (!_samePair(pair, _credentials.pair)) {
      _credentials = { pair, revision: _credentials.revision + 1, trusted: _credentials.trusted };
    }
    return _credentials;
  }
  function _snapshot() {
    _requireTrusted();
    return { revision: _currentCredentials().revision };
  }
  function _sessionChanged() {
    const error = new Error('La sesión cambió. Vuelve a abrir esta página desde tu cuenta.');
    error.code = 'session_changed';
    return error;
  }
  function _assertSnapshot(snapshot) {
    _requireTrusted();
    const current = _currentCredentials();
    if (current.revision !== snapshot.revision) throw _sessionChanged();
    return current.pair;
  }
  function _assertPair(snapshot, pair) {
    if (!_samePair(_assertSnapshot(snapshot), pair)) throw _sessionChanged();
  }
  function _tokenPair(data) {
    if (!data || typeof data.token !== 'string' || !data.token || typeof data.refresh_token !== 'string' || !data.refresh_token) {
      throw new Error('El servidor no confirmó las credenciales de la sesión.');
    }
    return { token: data.token, refresh: data.refresh_token };
  }
  function saveTokens(data) {
    const pair = _tokenPair(data);
    _persistPair(pair, _currentCredentials());
  }
  function clearTokens() {
    _persistPair({ token: '', refresh: '' }, _currentCredentials(), true);
  }
  function _persistPair(next, source, remove = false, rotation = false) {
    const observed = _readPair();
    if (_credentials !== source || !_samePair(observed, source.pair)) {
      _currentCredentials(); throw _sessionChanged();
    }
    const attempt = { pair: source.pair, revision: source.revision + (rotation ? 0 : 1), trusted: false };
    _credentials = attempt;
    try {
      if (remove) localStorage.removeItem('mb_token');
      else localStorage.setItem('mb_token', next.token);
      if (_credentials !== attempt || !_samePair(_readPair(), { token: next.token, refresh: source.pair.refresh })) {
        throw _sessionChanged();
      }
      if (remove) localStorage.removeItem('mb_refresh_token');
      else localStorage.setItem('mb_refresh_token', next.refresh);
      if (_credentials !== attempt || !_samePair(_readPair(), next)) throw _sessionChanged();
      _credentials = { pair: next, revision: attempt.revision, trusted: true };
    } catch (error) {
      // A newer explicit complete recovery wins; no rollback or compensating writes.
      if (_credentials !== attempt && _credentials.trusted) throw _sessionChanged();
      throw _failStorage(error);
    }
  }
  if (typeof window.addEventListener === 'function') {
    window.addEventListener('storage', event => {
      if (event.key === null || ['mb_token', 'mb_refresh_token'].includes(event.key)) {
        try {
          _credentials = { pair: _readPair(), revision: _credentials.revision + 1, trusted: _credentials.trusted };
        } catch { /* Read failure already made the credential state untrusted. */ }
      }
    });
  }

  function getLoginUrl() {
    var tipo = localStorage.getItem('mb_tipo');
    return tipo === 'usuario' ? '/login-usuario' : '/login-gym';
  }

  async function _doRefresh(snapshot, source) {
    _assertPair(snapshot, source);
    if (!source.refresh) return false;
    try {
      const res = await fetch(API_BASE + '/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: source.refresh }),
        cache: 'no-store',
      });
      _assertPair(snapshot, source);
      if (!res.ok) return false;
      const data = await res.json();
      _assertPair(snapshot, source);
      const next = _tokenPair(data);
      // Only this confirmed rotation may preserve the logical session revision.
      _persistPair(next, _credentials, false, true);
      return true;
    } catch (error) {
      if (error.code === 'session_changed' || error.code === 'session_storage_error') throw error;
      _assertPair(snapshot, source);
      return false;
    }
  }

  function _expire(snapshot, pair) {
    _assertPair(snapshot, pair);
    clearTokens();
    window.location.href = getLoginUrl();
    const error = new Error('Sesión expirada.');
    error.code = 'session_expired';
    throw error;
  }

  async function _handleRefresh(snapshot, sentPair) {
    const current = _assertSnapshot(snapshot);
    // A concurrent request may already have rotated this same session.
    if (!_samePair(current, sentPair)) return current;
    let job = _refreshJob;
    if (!job || job.revision !== snapshot.revision || !_samePair(job.source, current)) {
      job = { revision: snapshot.revision, source: current };
      _refreshJob = job;
      job.promise = _doRefresh(snapshot, current).finally(() => {
        if (_refreshJob === job) _refreshJob = null;
      });
    }
    const success = await job.promise;
    _assertSnapshot(snapshot);
    if (!success) _expire(snapshot, job.source);
    return _assertSnapshot(snapshot);
  }

  async function _authenticatedFetch(path, options, snapshot) {
    async function send(pair) {
      _assertPair(snapshot, pair);
      const headers = { ...options.headers };
      if (pair.token) headers.Authorization = `Bearer ${pair.token}`;
      else delete headers.Authorization;
      let response;
      try { response = await fetch(API_BASE + path, { ...options, headers }); }
      catch {
        _assertSnapshot(snapshot);
        throw new Error('Error de red: no se pudo conectar al servidor.');
      }
      _assertSnapshot(snapshot);
      return response;
    }
    let sentPair = _assertSnapshot(snapshot);
    let response = await send(sentPair);
    if (response.status === 401) {
      await _handleRefresh(snapshot, sentPair);
      sentPair = _assertSnapshot(snapshot);
      response = await send(sentPair);
      if (response.status === 401) _expire(snapshot, sentPair);
    }
    return response;
  }

  async function request(method, path, body = null, extraHeaders = {}, authenticated = true) {
    const snapshot = authenticated ? _snapshot() : null;
    const opts = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...extraHeaders,
      },
    };
    if (body !== null) opts.body = JSON.stringify(body);

    let res;
    try {
      res = authenticated ? await _authenticatedFetch(path, opts, snapshot) : await fetch(API_BASE + path, opts);
    } catch (networkErr) {
      if (networkErr.code === 'session_expired') throw networkErr;
      if (authenticated) _assertSnapshot(snapshot);
      if (networkErr.code === 'session_changed') throw networkErr;
      throw new Error('Error de red: no se pudo conectar al servidor.');
    }

    let data;
    try { data = await res.json(); }
    catch {
      if (authenticated) _assertSnapshot(snapshot);
      if (res.ok && res.status !== 204) throw new Error('El servidor devolvió una respuesta no válida. Intenta consultar de nuevo.');
      data = {};
    }
    if (authenticated) _assertSnapshot(snapshot);

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
      const snapshot = _snapshot();
      const context = await planes.contexto();
      _assertSnapshot(snapshot);
      let invalidated = false;
      const invalidate = (event) => {
        if (event.type === 'pagehide' || event.key === null || ['mb_token', 'mb_refresh_token'].includes(event.key)) invalidated = true;
      };
      window.addEventListener('storage', invalidate);
      window.addEventListener('pagehide', invalidate);
      try {
      const res = await _authenticatedFetch(path, { cache: 'no-store' }, snapshot);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        _assertSnapshot(snapshot);
        throw new Error(typeof err.detail === 'string' ? err.detail : 'No se pudo descargar este plan.');
      }
      const blob = await res.blob();
      _assertSnapshot(snapshot);
      const signature = await blob.slice(0, 5).text();
      _assertSnapshot(snapshot);
      if (!res.headers.get('Content-Type')?.toLowerCase().startsWith('application/pdf') ||
          blob.size === 0 || signature !== '%PDF-') {
        throw new Error('El servidor no devolvió un PDF válido.');
      }
      if (invalidated || await planes.contexto() !== context || invalidated) {
        throw new Error('La sesión cambió. Vuelve a abrir el plan desde tu cuenta.');
      }
      _assertSnapshot(snapshot);
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
      const snapshot = _snapshot();
      const data = await request('POST', '/api/auth/login', { email, password }, {}, false);
      _assertSnapshot(snapshot);
      saveTokens(data);
      return data;
    },
    loginUsuario: async (email, password) => {
      const snapshot = _snapshot();
      const data = await request('POST', '/api/auth/login', { email, password }, {}, false);
      _assertSnapshot(snapshot);
      saveTokens(data);
      return data;
    },
    registro: async (payload) => {
      const snapshot = _snapshot();
      const data = await request('POST', '/api/auth/registro', payload, {}, false);
      _assertSnapshot(snapshot);
      saveTokens(data);
      return data;
    },
    me:     () => request('GET',  '/api/auth/me'),
    logout: async () => {
      const snapshot = _snapshot();
      let serverConfirmed = false;
      try {
        const result = await request('POST', '/api/auth/logout');
        serverConfirmed = !!result && result.success === true;
      } catch (error) {
        if (error.code === 'session_storage_error') throw error;
        // A failed POST is not proof of server revocation. A newer session wins.
      }
      if (_currentCredentials().revision !== snapshot.revision) return {state:'session_changed',server_confirmed:false};
      clearTokens();
      _requireTrusted();
      const closed = _currentCredentials();
      if (closed.pair.token || closed.pair.refresh) return {state:'session_changed',server_confirmed:false};
      return {state:'closed_local',server_confirmed:serverConfirmed,context:Object.freeze({revision:closed.revision})};
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
      const snapshot = _snapshot();
      const formData = file ? new FormData() : null;
      if (file) formData.append('file', file);
      const opts = {
        method,
        ...(formData ? { body: formData } : {}),
        cache: 'no-store',
        referrerPolicy: 'no-referrer',
      };
      const res = await _authenticatedFetch('/api/gym/logo', opts, snapshot);
      if (res.ok && method === 'GET') {
        const mime = (res.headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
        if (!['image/png', 'image/jpeg', 'image/webp'].includes(mime)) throw new Error('El servidor no devolvió una imagen válida.');
        const blob = await res.blob();
        _assertSnapshot(snapshot);
        if (!blob.size || blob.size > 2 * 1024 * 1024) throw new Error('El logo guardado no tiene un tamaño válido.');
        return blob;
      }
      let data;
      try { data = await res.json(); }
      catch { _assertSnapshot(snapshot); throw new Error('El servidor no confirmó la carga del logo.'); }
      _assertSnapshot(snapshot);
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

  function _personalRequest(method, path, body, headers, context) {
    if (context) _assertSnapshot(context);
    return request(method, path, body, headers);
  }
  function _personalDay(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('Elige una fecha válida.');
    const [year,month,day] = value.split('-').map(Number);
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    if (year < 1 || month < 1 || month > 12 || day < 1 || day > [31,leap?29:28,31,30,31,30,31,31,30,31,30,31][month-1]) throw new Error('Elige una fecha válida.');
    return value;
  }
  const usuario = {
    contexto: async () => {
      const snapshot = _snapshot();
      const me = await auth.me();
      _assertSnapshot(snapshot);
      if (!me || typeof me.id !== 'string' || !me.id || !me.role ||
          (me.tipo !== 'usuario' && !me.team_gym_id)) throw _sessionChanged();
      return Object.freeze({ revision: snapshot.revision,
        subject: JSON.stringify([me.id, me.team_gym_id || null, me.role, me.session_version]), me });
    },
    validarContexto: (context) => { _assertSnapshot(context); },
    verificarContexto: async (context) => {
      _assertSnapshot(context);
      const current = await usuario.contexto();
      _assertSnapshot(context);
      if (current.subject !== context.subject) throw _sessionChanged();
      return current.me;
    },
    diarioHoy: (context) => _personalRequest('GET', '/api/usuario/diario', null, {}, context),
    diarioDia: (day, context) => _personalRequest('GET', '/api/usuario/diario/' + _personalDay(day), null, {}, context),
    diarioCalendario: (start, end, context) => {
      _personalDay(start); _personalDay(end);
      const days = (Date.parse(end+'T00:00:00Z') - Date.parse(start+'T00:00:00Z')) / 86400000;
      if (days < 0 || days >= 62) throw new Error('Consulta un periodo de hasta 62 días.');
      const params = new URLSearchParams({start,end});
      return _personalRequest('GET', '/api/usuario/diario?' + params, null, {}, context);
    },
    guardarDiario: (day, operation, context) => _personalRequest('PATCH', '/api/usuario/diario/' + _personalDay(day), operation, {}, context),
    exportarDatos: (cursors = {}, context) => {
      const params = new URLSearchParams({limit:'100'});
      const integerCursors = ['profile','plan','measurement'];
      const uuidCursors = ['purchase','generation','member_link'];
      for (const name of [...integerCursors,...uuidCursors,'diary']) {
        const value = cursors[name];
        if (value == null) continue;
        if (name === 'diary') _personalDay(value);
        else if (integerCursors.includes(name) ? !Number.isSafeInteger(value) || value < 0 : typeof value !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) {
          throw new Error('No se pudo continuar la descarga. Empieza una descarga nueva.');
        }
        params.set('after_'+name,String(value));
      }
      return _personalRequest('GET','/api/usuario/privacidad/exportar?'+params, null, {'Cache-Control':'no-store'},context);
    },
    perfil:         (context) => _personalRequest('GET', '/api/usuario/perfil', null, {}, context),
    guardarPerfil:  (data, context) => _personalRequest('PUT', '/api/usuario/perfil', data, {}, context),
    miPlan:         (context) => _personalRequest('GET', '/api/usuario/mi-plan', null, {}, context),
    catalogo:       (context) => _personalRequest('GET', '/api/usuario/catalogo-alimentos', null, {}, context),
    generarPlan:    (key, context) => {
      if (typeof key !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(key)) {
        throw new Error('No se pudo identificar la solicitud. Vuelve a abrir tu plan.');
      }
      return _personalRequest('POST', '/api/usuario/generar-plan', null, { 'Idempotency-Key': key }, context);
    },
    historial: (context, options = {}) => {
      const limit = options.limit ?? 50, cursor = options.cursor ?? null;
      if (!Number.isSafeInteger(limit) || limit < 1 || limit > 200 ||
          (cursor !== null && (typeof cursor !== 'string' || cursor.length < 1 || cursor.length > 180))) {
        throw new Error('No se pudo continuar el historial. Vuelve a consultar desde el inicio.');
      }
      const params = new URLSearchParams();
      if (limit !== 50) params.set('limit', String(limit));
      if (cursor !== null) params.set('cursor', cursor);
      return _personalRequest('GET', '/api/usuario/historial' + (params.size ? '?' + params : ''), null, {}, context);
    },
    descargarPlan: (planId, context) => {
      if (!Number.isSafeInteger(planId) || planId < 1 || planId > 2147483647) throw new Error('El plan no es válido.');
      if (context) _assertSnapshot(context);
      return planes._descargar(`/api/usuario/descargar-pdf?plan_id=${planId}`, `mi_plan_${planId}.pdf`);
    },
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

  // R12 resource context is separate from the personal profile and professional tenant.
  // Receiving a link does not make either of those spaces available.
  const vinculos = {
    contexto: async () => {
      const snapshot = _snapshot();
      const me = await auth.me();
      _assertSnapshot(snapshot);
      if (!me || typeof me.id !== 'string' || !me.id ||
          !['usuario', 'gym'].includes(me.tipo) ||
          !['owner', 'admin', 'nutriologo', 'viewer'].includes(me.role) ||
          !Number.isSafeInteger(me.session_version) || me.session_version < 0 ||
          !(me.team_gym_id == null || (typeof me.team_gym_id === 'string' && me.team_gym_id))) {
        throw _sessionChanged();
      }
      return Object.freeze({ revision: snapshot.revision,
        subject: JSON.stringify([me.id, me.tipo, me.role, me.team_gym_id || null, me.session_version]),
        me: Object.freeze({ ...me }) });
    },
    validarContexto: context => { _assertSnapshot(context); },
    verificarContexto: async context => {
      _assertSnapshot(context);
      const current = await vinculos.contexto();
      _assertSnapshot(context);
      if (current.subject !== context.subject) throw _sessionChanged();
      return current.me;
    },
    estado: (client, context, after = null) => _linkRequest('GET', _clientLinkPath(client) + _linkPage(after), null, context),
    emitir: (client, recipient_email, request_key, context) => _linkRequest('POST', _clientLinkPath(client) + '/invitaciones', {recipient_email, request_key}, context),
    rotar: (client, invitation, version, context) => _linkRequest('POST', _clientLinkPath(client) + '/invitaciones/' + _linkUUID(invitation) + '/reenviar', {expected_version:_linkVersion(version)}, context),
    revocar: (client, link, version, context) => _linkRequest('DELETE', _clientLinkPath(client) + '/' + _linkUUID(link), {expected_version:_linkVersion(version)}, context),
    publicar: (client, link, plan, linkVersion, publicationVersion, context) => {
      if (!Number.isSafeInteger(plan) || plan < 1 || plan > 2147483647 || !Number.isSafeInteger(publicationVersion) || publicationVersion < 0 || publicationVersion > 2147483647) throw new Error('Selecciona un plan válido.');
      return _linkRequest('POST', _clientLinkPath(client) + '/' + _linkUUID(link) + '/publicaciones', {plan_id:plan,expected_link_version:_linkVersion(linkVersion),expected_publication_version:publicationVersion}, context);
    },
    retirar: (client, link, publication, version, context) => _linkRequest('DELETE', _clientLinkPath(client) + '/' + _linkUUID(link) + '/publicaciones/' + _linkUUID(publication), {expected_version:_linkVersion(version)}, context),
    inspeccionar: (token, context) => _linkRequest('POST', '/api/usuario/vinculaciones/invitacion', {token:_linkToken(token)}, context),
    aceptar: (token, version, context) => _linkRequest('POST', '/api/usuario/vinculaciones/aceptar', {token:_linkToken(token),expected_version:_linkVersion(version),confirm:true}, context),
    listar: (context, after = null) => _linkRequest('GET', '/api/usuario/vinculos' + _linkPage(after), null, context),
    plan: (link, context) => _linkRequest('GET', '/api/usuario/vinculos/' + _linkUUID(link) + '/plan', null, context),
    desvincular: (link, version, context) => _linkRequest('DELETE', '/api/usuario/vinculos/' + _linkUUID(link), {expected_version:_linkVersion(version)}, context),
    pdf: async (link, publication, context) => {
      _assertSnapshot(context);
      await vinculos.verificarContexto(context); _assertSnapshot(context);
      const res = await _authenticatedFetch('/api/usuario/vinculos/' + _linkUUID(link) + '/publicaciones/' + _linkUUID(publication) + '/pdf', {cache:'no-store',referrerPolicy:'no-referrer'}, context);
      _assertSnapshot(context);
      if (!res.ok) throw Object.assign(new Error('No se pudo descargar esta publicación. Vuelve a consultar el vínculo.'), {status:res.status});
      const length = res.headers.get('Content-Length');
      if (res.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase() !== 'application/pdf' || (length !== null && (!/^\d+$/.test(length) || Number(length) > 67108864))) throw new Error('El servidor no devolvió un PDF válido.');
      if (!res.body?.getReader) throw new Error('No se pudo leer esta descarga.');
      const reader = res.body.getReader(), chunks = [];
      let bytes = 0;
      try {
        while (true) {
          const part = await reader.read(); _assertSnapshot(context);
          if (part.done) break;
          bytes += part.value.byteLength;
          if (bytes > 67108864) throw new Error('El PDF supera el tamaño permitido.');
          chunks.push(part.value);
        }
      } catch (error) { try { await reader.cancel(); } catch {} throw error; }
      finally { reader.releaseLock(); }
      _assertSnapshot(context);
      if (!bytes) throw new Error('El PDF no está disponible para esta descarga.');
      const blob = new Blob(chunks, {type:'application/pdf'});
      const signature = await blob.slice(0,5).text(); _assertSnapshot(context);
      if (signature !== '%PDF-') throw new Error('El servidor no devolvió un PDF válido.');
      await vinculos.verificarContexto(context); _assertSnapshot(context);
      return blob;
    },
  };

  function _linkUUID(value) {
    if (typeof value !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) throw new Error('El vínculo no es válido.');
    return value;
  }
  function _linkVersion(value) {
    if (!Number.isSafeInteger(value) || value < 1 || value > 2147483647) throw new Error('Vuelve a consultar el estado antes de confirmar.');
    return value;
  }
  function _linkToken(value) {
    if (typeof value !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(value)) throw new Error('Vuelve a abrir el enlace original del correo.');
    return value;
  }
  function _clientLinkPath(client) {
    if (typeof client !== 'string' || !client || client.length > 128) throw new Error('El cliente no es válido.');
    return '/api/clientes/' + encodeURIComponent(client) + '/vinculacion';
  }
  function _linkPage(after) {
    return '?limit=100' + (after === null ? '' : '&after=' + _linkUUID(after));
  }
  function _linkRequest(method, path, body, context) {
    _assertSnapshot(context);
    return request(method, path, body, {'Cache-Control':'no-store'});
  }

  const team = {
    list: () => request('GET', '/api/gym/team'),
    invite: (data) => request('POST', '/api/gym/team/invite', data),
    role: (id, role) => request('PATCH', '/api/gym/team/' + encodeURIComponent(id) + '/role', {role}),
    remove: (id) => request('DELETE', '/api/gym/team/' + encodeURIComponent(id)),
    resend: (id) => request('POST', '/api/gym/team/' + encodeURIComponent(id) + '/resend-invite'),
    info: (token) => request('POST', '/api/auth/invite-info', {token}, {}, false),
    accept: (token, password) => request('POST', '/api/auth/accept-invite', {token,password}, {}, false),
  };
  return { clientes, planes, stats, auth, billing, gym, usuario, vinculos, team, clearTokens, saveTokens };
})();

