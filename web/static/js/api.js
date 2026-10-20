/**
 * api.js — Cliente HTTP para MetodoBase API
 * Access sólo en RAM. Refresh sólo mediante cookie HttpOnly del mismo origen.
 * Los namespaces de acceso exacto mantienen su política sin refresh/replay.
 */

const API_BASE = '';  // mismo origen

const Api = (() => {

  let _refreshJob = null;
  const _storageErrors = new WeakSet();
  let _notifyingSession = false;
  function _notifySessionChanged() {
    // Event contains no values. State is consolidated before dispatch; a
    // listener may inspect/recover it, but must not cause recursive dispatch.
    if (_notifyingSession || typeof window.dispatchEvent !== 'function' || typeof Event !== 'function') return;
    _notifyingSession = true;
    try { window.dispatchEvent(new Event('metodobase-session-changed')); }
    catch { /* Notification infrastructure must not alter authenticated I/O. */ }
    finally { _notifyingSession = false; }
  }

  const _epochKey='mb_session_epoch',_lockName='metodobase.browser-session.v1';
  let _epoch=null,_invalidated=false,_hidden=false,_metadata=null,_readyState='pending',_readyPromise;
  let _channel=null;
  let _retainedLogin=null;
  const _acknowledged=new WeakMap();
  const _delivered=new WeakMap();
  let _credentials={pair:{token:'',refresh:''},revision:0,trusted:false};
  function getToken(){
    if(_readyState!=='ready'||_invalidated||_hidden||!_credentials.trusted)return '';
    try{return _currentCredentials().pair.token;}catch{return '';}
  }
  function _readEpoch(){try{return localStorage.getItem(_epochKey);}catch(error){throw _failStorage(error);}}
  function _readPair(){return _currentCredentials().pair;}
  function _samePair(left, right) {
    return left.token === right.token && left.refresh === right.refresh;
  }
  function _storageError(cause) {
    const error = new Error('No se pudo verificar el almacenamiento de la sesión. Vuelve a iniciar sesión.', cause ? { cause } : undefined);
    error.code = 'session_storage_error';
    // Preserve standard Storage error names for callers; never expose its message or values.
    if (cause && ['QuotaExceededError', 'SecurityError', 'InvalidStateError'].includes(cause.name)) error.name = cause.name;
    _storageErrors.add(error);
    return error;
  }
  function _failStorage(cause) {
    _metadata=null;
    _credentials = { pair:{token:'',refresh:''}, revision: _credentials.revision + 1, trusted: false };
    _notifySessionChanged();
    if (_storageErrors.has(cause)) return cause;
    return _storageError(cause);
  }
  function _requireTrusted() {
    if(_hidden||_invalidated)throw _sessionChanged();
    if (!_credentials.trusted) throw _storageError();
  }
  function _currentCredentials() {
    _requireTrusted();
    if(_readEpoch()!==_epoch){_invalidateSession();throw _sessionChanged();}
    return _credentials;
  }
  function _snapshot() {
    if(_readyState!=='ready')throw _browserError('browser_session_not_ready');
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
    if(!data||data.session_mode!=='browser'||typeof data.token!=='string'||!data.token||data.token.length>8192||/[^\x21-\x7e]/.test(data.token)||Object.hasOwn(data,'refresh_token')||(Object.hasOwn(data,'access_token')&&data.access_token!==data.token))throw _browserError('browser_protocol_invalid');
    return {token:data.token,refresh:''};
  }
  function saveTokens(data) {
    const ack=_acknowledged.get(data);if(!ack)throw _browserError('browser_protocol_invalid');
    _acknowledged.delete(data);_assertSnapshot(ack.snapshot);
    const nextRevision=_credentials.revision+1;_persistPair(ack.pair,_currentCredentials());
    _assertPair({revision:nextRevision},ack.pair);_remember(data);
  }
  function clearTokens() {
    _publishBoundary();
  }
  function _persistPair(next, source, remove = false, rotation = false) {
    if(_currentCredentials()!==source)throw _sessionChanged();
    _credentials={pair:remove?{token:'',refresh:''}:next,revision:source.revision+(rotation?0:1),trusted:true};
    if(!rotation)_notifySessionChanged();
  }
  function _browserError(code){return Object.assign(new Error(({browser_locks_unavailable:'Este navegador no permite coordinar la sesión de forma segura. Usa un navegador actualizado con Web Locks habilitado.',browser_protocol_invalid:'El servidor no confirmó el modo seguro de sesión del navegador. Vuelve a abrir la página cuando el servicio esté actualizado.',browser_session_not_ready:'La sesión todavía se está verificando. Espera a que termine la consulta.',browser_session_unconfirmed:'No se pudo confirmar la sesión. No repetiremos la operación automáticamente.'})[code]||'No se pudo verificar la sesión del navegador.'),{code});}
  function _remember(data){_metadata=Object.freeze(Object.fromEntries(['id','tipo','nombre','email','role','team_gym_id'].filter(key=>typeof data[key]==='string'||data[key]===null).map(key=>[key,data[key]])));}
  function _invalidateSession(){if(_invalidated)return;_invalidated=true;_metadata=null;_credentials={pair:{token:'',refresh:''},revision:_credentials.revision+1,trusted:_credentials.trusted};_notifySessionChanged();}
  function _publishBoundary(handle=null,silent=false){
    _currentCredentials();const next=crypto.randomUUID();_epoch=next;_metadata=null;_credentials={pair:{token:'',refresh:''},revision:_credentials.revision+1,trusted:true};
    try{localStorage.setItem(_epochKey,next);if(localStorage.getItem(_epochKey)!==next)throw _storageError();}catch(error){throw _failStorage(error);}
    if(handle){if(!_mfaContexts.has(handle))throw _sessionChanged();_mfaContexts.set(handle,{snapshot:{revision:_credentials.revision},pair:_credentials.pair});}
    try{_channel?.postMessage({epoch:next});}catch{/* Storage events plus synchronous epoch checks remain authoritative. */}
    const previous=_retainedLogin;_retainedLogin=handle?{handle,value:_mfaContexts.get(handle)}:null;
    try{if(!silent)_notifySessionChanged();}finally{_retainedLogin=previous;}
    return {revision:_credentials.revision};
  }
  async function _withCookieLock(snapshot,run){
    if(typeof navigator==='undefined'||typeof navigator.locks?.request!=='function')throw _browserError('browser_locks_unavailable');
    try{return await navigator.locks.request(_lockName,{mode:'exclusive'},async()=>{_assertSnapshot(snapshot);return run();});}
    catch(error){if(['SecurityError','NotSupportedError'].includes(error.name)&&typeof error.code!=='string')throw _browserError('browser_locks_unavailable');throw error;}
  }
  function _captureCookieBody(body){
    try{const encoded=JSON.stringify(body,(_key,value)=>{if((typeof value==='number'&&!Number.isFinite(value))||['undefined','function','symbol','bigint'].includes(typeof value))throw Error('invalid');return value;});if(!body||Array.isArray(body)||typeof body!=='object'||new TextEncoder().encode(encoded).byteLength>32768)throw Error('invalid');return JSON.parse(encoded);}catch{throw _browserError('browser_auth_invalid_input');}
  }
  async function _cookieFetch(path,body,bearer=null){
    let response,encoded=JSON.stringify(body);body=null;
    try{const pending=fetch(API_BASE+path,{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json','X-MetodoBase-Browser':'1',...(bearer?{Authorization:'Bearer '+bearer}:{})},body:encoded,credentials:'same-origin',mode:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer'});encoded=null;response=await pending;}catch{encoded=null;throw _browserError('browser_session_unconfirmed');}
    let data;try{data=await response.json();}catch{throw _browserError('browser_session_unconfirmed');}
    if(!response.ok){const detail=data?.detail,error=Object.assign(new Error(typeof detail==='string'?detail:detail?.message||'No se pudo confirmar la sesión.'),{status:response.status,code:detail?.code||null,retryAfter:response.headers.get('Retry-After')||null});throw error;}
    return {status:response.status,data};
  }
  function _takeLegacy(){
    let saved=null,failed=null;
    for(const name of ['localStorage','sessionStorage']){
      let store;try{store=window[name];const access=store.getItem('mb_token'),refresh=store.getItem('mb_refresh_token');if(refresh){if(typeof refresh!=='string'||refresh.length>8192||/[^\x21-\x7e]/.test(refresh)||(saved&&saved!==refresh))failed=_browserError('browser_protocol_invalid');else saved=refresh;}void access;}catch(error){failed=error;}
      if(store)for(const key of ['mb_token','mb_refresh_token','mb_nombre','mb_email','mb_tipo'])try{store.removeItem(key);}catch(error){failed=error;}
    }
    if(failed){saved=null;throw failed.code==='browser_protocol_invalid'?failed:_failStorage(failed);}return saved;
  }
  async function _bootstrap(){
    let legacy=null;
    try{
      legacy=_takeLegacy();_epoch=_readEpoch();
      if(_epoch===null){_epoch=crypto.randomUUID();localStorage.setItem(_epochKey,_epoch);}
      if(typeof _epoch!=='string'||!/^([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$/.test(_epoch))throw _storageError();
      if(localStorage.getItem(_epochKey)!==_epoch)throw _storageError();_credentials.trusted=true;
      if(typeof BroadcastChannel==='function')try{_channel=new BroadcastChannel(_lockName);_channel.onmessage=event=>{if(event.data&&Object.keys(event.data).length===1&&typeof event.data.epoch==='string'&&event.data.epoch!==_epoch)_invalidateSession();};}catch{/* Storage events and epoch comparisons still fence every private operation. */}
      const snapshot={revision:_credentials.revision};
      await _withCookieLock(snapshot,async()=>{
        let current=snapshot;
        if(legacy)current=_publishBoundary(null,true);
        try{const pending=_cookieFetch(legacy?'/api/auth/browser/migrate':'/api/auth/refresh',legacy?{refresh_token:legacy}:{});legacy=null;const reply=await pending;_assertSnapshot(current);const pair=_tokenPair(reply.data);_persistPair(pair,_credentials,false,true);_remember(reply.data);}
        catch(error){_assertSnapshot(current);if(error.status!==401||error.code!=='browser_session_unavailable')throw error;}
      });
      _currentCredentials();_readyState='ready';return Object.freeze({authenticated:!!_credentials.pair.token});
    }catch(error){legacy=null;_metadata=null;_credentials={..._credentials,pair:{token:'',refresh:''}};_readyState='error';if(['SecurityError','QuotaExceededError','InvalidStateError'].includes(error.name)&&typeof error.code!=='string')throw _failStorage(error);throw error;}
  }
  if (typeof window.addEventListener === 'function') {
    window.addEventListener('storage', event => {
      if(event.key===null||event.key===_epochKey||['mb_token','mb_refresh_token','mb_session_epoch'].includes(event.key))_invalidateSession();
    });
    window.addEventListener('pagehide',()=>{_hidden=true;_invalidateSession();});
    window.addEventListener('pageshow',event=>{if(event.persisted)_invalidateSession();});
  }

  function getLoginUrl() {
    return location.pathname.startsWith('/mi-')?'/login-usuario':'/login-gym';
  }

  async function _doRefresh(snapshot, source) {
    _assertPair(snapshot, source);
    return _withCookieLock(snapshot,async()=>{
      try{
        _assertPair(snapshot,source);const reply=await _cookieFetch('/api/auth/refresh',{});_assertPair(snapshot,source);
        _persistPair(_tokenPair(reply.data),_credentials,false,true);return true;
      }catch(error){
        if(['session_changed','session_storage_error'].includes(error.code))throw error;
        _assertPair(snapshot,source);
        if(error.status===401&&error.code==='browser_session_unavailable')_expire(snapshot,source);
        // Invalidate before unlocking: a queued tab must not rotate an uncertain cookie.
        _publishBoundary();throw error;
      }
    });
  }

  function _expire(snapshot, pair) {
    _assertPair(snapshot, pair);
    clearTokens();
    // The synchronous notification can explicitly recover another session.
    // Only the exact complete empty revision produced by this clear may
    // continue to the login page; never redirect a listener's replacement.
    const cleared = { revision: snapshot.revision + 1 };
    const empty = { token: '', refresh: '' };
    _assertPair(cleared, empty);
    const loginUrl = getLoginUrl();
    _assertPair(cleared, empty);
    window.location.href = loginUrl;
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

  async function _authenticatedFetch(path, options, snapshot, exactPair = null) {
    async function send(pair) {
      _assertPair(snapshot, pair);
      if(!pair.token)throw Object.assign(new Error('No hay un acceso confirmado. Inicia sesión para continuar.'),{code:'session_expired'});
      const headers = { ...options.headers };
      if (pair.token) headers.Authorization = `Bearer ${pair.token}`;
      else delete headers.Authorization;
      let response;
      try { response = await fetch(API_BASE + path, { ...options, headers }); }
      catch {
        if (exactPair) _assertPair(snapshot, exactPair); else _assertSnapshot(snapshot);
        throw new Error('Error de red: no se pudo conectar al servidor.');
      }
      if (exactPair) _assertPair(snapshot, exactPair); else _assertSnapshot(snapshot);
      return response;
    }
    // MFA proofs/grants bind one access. A401 must never rotate/replay them.
    if (exactPair) return send(exactPair);
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

  async function request(method, path, body = null, extraHeaders = {}, authenticated = true, policy = null) {
    const encodedBody=body===null?null:JSON.stringify(body),capturedHeaders={...extraHeaders};
    if(authenticated)await _readyPromise;
    const snapshot = authenticated ? (policy?.snapshot || _snapshot()) : null;
    const opts = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...capturedHeaders,
      },
      ...(policy ? {cache:'no-store',referrerPolicy:'no-referrer'} : {}),
    };
    if (encodedBody !== null) opts.body = encodedBody;

    let res;
    try {
      res = authenticated ? await _authenticatedFetch(path, opts, snapshot, policy?.pair || null) : await fetch(API_BASE + path, opts);
    } catch (networkErr) {
      if (networkErr.code === 'session_expired') throw networkErr;
      if (authenticated) { if (policy?.pair) _assertPair(snapshot, policy.pair); else _assertSnapshot(snapshot); }
      if (['session_changed','session_storage_error','browser_locks_unavailable','browser_protocol_invalid','browser_session_unconfirmed'].includes(networkErr.code)) throw networkErr;
      throw new Error('Error de red: no se pudo conectar al servidor.');
    }

    let data;
    try { data = await res.json(); }
    catch {
      if (authenticated) _assertSnapshot(snapshot);
      if (res.ok && res.status !== 204) throw new Error('El servidor devolvió una respuesta no válida. Intenta consultar de nuevo.');
      data = {};
    }
    if (authenticated) { if (policy?.pair) _assertPair(snapshot, policy.pair); else _assertSnapshot(snapshot); }

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
      err.retryAfter = res.headers.get('Retry-After') || null;
      err.requestId = (data.detail && data.detail.request_id) || res.headers.get('X-Request-ID') || null;
      if (errorCode) err.code = errorCode;
      if (upgradeUrl) err.upgradeUrl = upgradeUrl;
      throw err;
    }
    return policy?.includeStatus ? {status:res.status,data} : data;
  }

  // ── Clientes ──────────────────────────────────────────────────────────────

  const clientes = {
    catalogo: async()=>{await _readyPromise;const snapshot=_snapshot(),pair=_assertSnapshot(snapshot);return request('GET','/api/alimentos/catalogo',null,{},true,{snapshot,pair});},
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
      await _readyPromise;
      const snapshot = _snapshot();
      const context = await planes.contexto();
      _assertSnapshot(snapshot);
      let invalidated = false;
      const invalidate = (event) => {
        if (event.type === 'pagehide' || event.key === null || ['mb_token','mb_refresh_token','mb_session_epoch'].includes(event.key)) invalidated = true;
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
    contexto: async () => {
      await _readyPromise;
      const snapshot = _snapshot();
      const me = await auth.me();
      _assertSnapshot(snapshot);
      if (!me || typeof me.id !== 'string' || !me.id || !me.role) throw _sessionChanged();
      return Object.freeze({revision: snapshot.revision,
        subject: JSON.stringify([me.id, me.team_gym_id || null, me.role, me.session_version])});
    },
    validarContexto: (context) => { _assertSnapshot(context); },
    verificarContexto: async (context) => {
      _assertSnapshot(context);
      const current = await stats.contexto();
      _assertSnapshot(context);
      if (current.subject !== context.subject) throw _sessionChanged();
    },
    seguimiento: (context, limit = 50) => {
      _assertSnapshot(context);
      if (!Number.isSafeInteger(limit) || limit < 1 || limit > 100) throw new Error('Elige entre 1 y 100 clientes.');
      return request('GET', '/api/estadisticas/seguimiento?limit=' + limit);
    },
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
      await _readyPromise;
      const handle = mfa.capture();
      const data = await mfa.primaryPassword({ email, password }, handle);
      mfa.check(handle);
      if (!data.mfa_required) mfa.finishLogin(data,handle);
      return data;
    },
    loginUsuario: async (email, password) => {
      await _readyPromise;
      const handle = mfa.capture();
      const data = await mfa.primaryPassword({ email, password }, handle);
      mfa.check(handle);
      if (!data.mfa_required) mfa.finishLogin(data,handle);
      return data;
    },
    registro: async (payload) => {
      return _browserAccount('/api/auth/registro',payload);
    },
    me: async () => {await _readyPromise;const snapshot=_snapshot(),data=await request('GET','/api/auth/me');_assertSnapshot(snapshot);_remember(data);return data;},
    logout: async () => {
      try {
        await _readyPromise;const snapshot=_snapshot();
        return await _withCookieLock(snapshot,async()=>{
          const closed=_publishBoundary();let serverConfirmed=false;
          try{const reply=await _cookieFetch('/api/auth/browser/logout',{});_assertSnapshot(closed);if(reply.status!==200||reply.data?.success!==true||reply.data.session_mode!=='browser'||typeof reply.data.server_confirmed!=='boolean')throw _browserError('browser_protocol_invalid');serverConfirmed=reply.data.server_confirmed;}
          catch(error){_assertSnapshot(closed);if(error.code==='session_changed'||error.code==='session_storage_error')throw error;}
          return {state:'closed_local',server_confirmed:serverConfirmed,context:Object.freeze(closed)};
        });
      } catch (error) {
        if(error.code==='session_changed')return {state:'session_changed',server_confirmed:false};
        _invalidateSession();return {state:'closed_local',server_confirmed:false,context:null};
      }
    },
  };

  // Closed MFA wire. Handles contain no proof or access in their public shape.
  let _mfaContexts = new WeakMap(), _mfaOperations = new WeakMap(), _mfaGrants = new WeakMap();
  const _mfaBearer = value => typeof value === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value);
  const _mfaExpiry = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T.+(?:Z|[+-]\d\d:\d\d)$/.test(value) && Number.isFinite(Date.parse(value));
  function _mfaError(code='mfa_invalid_response') {
    return Object.assign(new Error('No se pudo confirmar esta verificación. Vuelve a consultar antes de continuar.'),{code});
  }
  function _mfaContext(handle) {
    const value = _mfaContexts.get(handle);
    if (!value) throw _sessionChanged();
    _assertPair(value.snapshot, value.pair);
    return value;
  }
  function _mfaReply(reply, allowChallenge = false) {
    const data = reply.data;
    if (allowChallenge && reply.status === 202) {
      if (!data || data.mfa_required !== true || !_mfaBearer(data.challenge) || !_mfaExpiry(data.expires_at) ||
          !Array.isArray(data.methods) || data.methods.length !== 2 || !['totp','recovery_code'].every(name=>data.methods.includes(name)) ||
          data.session_mode!=='browser'||Object.keys(data).some(key=>!['mfa_required','challenge','expires_at','methods','session_mode'].includes(key))) throw _mfaError();
      return data;
    }
    if (reply.status !== 200 || !data || data.mfa_required === true) throw _mfaError();
    _tokenPair(data);
    return data;
  }
  async function _mfaPublic(path, body, handle, allowChallenge) {
    body=_captureCookieBody(body);
    await _readyPromise;const context=_mfaContext(handle);
    try {
      return await _withCookieLock(context.snapshot,async()=>{
        _mfaContext(handle);const snapshot=_publishBoundary(handle);
        const reply=await _cookieFetch(path,body);_mfaContext(handle);
        const data=_mfaReply(reply,allowChallenge);
        if(reply.status===200)_acknowledged.set(data,{snapshot,pair:_tokenPair(data)});
        return data;
      });
    } catch(error) { _mfaContext(handle);throw error; }
  }
  async function _browserAccount(path,body){
    body=_captureCookieBody(body);
    await _readyPromise;const snapshot=_snapshot();
    return _withCookieLock(snapshot,async()=>{
      const started=_publishBoundary(),reply=await _cookieFetch(path,body);_assertSnapshot(started);
      if(reply.status!==200)throw _browserError('browser_protocol_invalid');
      const data=reply.data;_acknowledged.set(data,{snapshot:started,pair:_tokenPair(data)});saveTokens(data);_delivered.set(data,{snapshot:_snapshot(),pair:_credentials.pair});return data;
    });
  }
  async function _mfaRequest(path, body, handle, method='POST') {
    if(method==='POST')body=_captureCookieBody(body);
    const context = _mfaContext(handle);
    try {
      const value = method==='POST'?await _withCookieLock(context.snapshot,async()=>{_mfaContext(handle);const reply=await _cookieFetch(path,body,context.pair.token);_mfaContext(handle);return reply.data;}):await request(method,path,body,{},true,{snapshot:context.snapshot,pair:context.pair});
      _mfaContext(handle);return value;
    } catch(error) { _mfaContext(handle);throw error; }
  }
  const _mfaRules = [
    ['team.invite','POST',/^\/api\/gym\/team\/invite$/],
    ['team.resend','POST',/^\/api\/gym\/team\/[^/?#]+\/resend-invite$/],
    ['team.role','PATCH',/^\/api\/gym\/team\/[^/?#]+\/role$/],
    ['team.remove','DELETE',/^\/api\/gym\/team\/[^/?#]+$/],
    ['billing.checkout','POST',/^\/api\/(?:billing\/checkout|pagos\/stripe\/session)$/],
    ['billing.subscribe','POST',/^\/api\/billing\/stripe\/subscribe$/],
    ['billing.confirm','POST',/^\/api\/billing\/confirm-subscription$/],
    ['billing.portal','POST',/^\/api\/billing\/portal$/],
    ['billing.mp','POST',/^\/api\/(?:billing\/mp\/preference|pagos\/mp\/preference)$/],
  ];
  let _mfaUILoad = null;
  function _mfaUI() {
    if (typeof window.MfaUI?.authorize === 'function') return Promise.resolve(window.MfaUI);
    if (_mfaUILoad) return _mfaUILoad;
    _mfaUILoad = new Promise((resolve,reject)=>{
      if (typeof document === 'undefined') { reject(_mfaError('mfa_ui_unavailable')); return; }
      const script=document.createElement('script'),style=document.createElement('link');
      let settled=false;
      const finish=error=>{if(settled)return;settled=true;clearTimeout(timer);if(error){script.remove();reject(error);}else resolve(window.MfaUI);};
      const timer=setTimeout(()=>finish(_mfaError('mfa_ui_unavailable')),15000);
      style.rel='stylesheet';style.href='/static/css/mfa.css';document.head.appendChild(style);
      script.src='/static/js/mfa-ui.js?v=r31browser1';script.nonce=document.querySelector('script[nonce]')?.nonce || '';
      script.onload=()=>finish(typeof window.MfaUI?.authorize==='function'?null:_mfaError('mfa_ui_unavailable'));
      script.onerror=()=>finish(_mfaError('mfa_ui_unavailable'));document.head.appendChild(script);
    }).catch(error=>{_mfaUILoad=null;throw error;});
    return _mfaUILoad;
  }
  const mfa = {
    isPrimaryBoundary:handle=>!!handle&&_retainedLogin?.handle===handle,
    capture() {
      const snapshot=_snapshot(),pair=_assertSnapshot(snapshot),handle=Object.freeze({revision:snapshot.revision});
      _mfaContexts.set(handle,{snapshot,pair});return handle;
    },
    check(handle) { _mfaContext(handle); },
    async context() {
      await _readyPromise;
      const handle=mfa.capture(),me=await _mfaRequest('/api/auth/me',null,handle,'GET');_mfaContext(handle);
      if (!me || typeof me.id!=='string' || !me.id || typeof me.role!=='string' || !Number.isSafeInteger(me.session_version)) throw _mfaError();
      _mfaContexts.get(handle).subject=JSON.stringify([me.id,me.role,me.team_gym_id||null,me.session_version]);
      return {handle,me};
    },
    async verify(handle) {
      const previous=_mfaContext(handle).subject;
      const me=await _mfaRequest('/api/auth/me',null,handle,'GET');_mfaContext(handle);
      if (previous && previous!==JSON.stringify([me.id,me.role,me.team_gym_id||null,me.session_version])) throw _sessionChanged();
    },
    primaryPassword: (body,handle) => _mfaPublic('/api/auth/login',body,handle,true),
    primaryGoogle: (body,handle) => _mfaPublic('/api/auth/google',body,handle,true),
    loginVerify: (body,handle) => _mfaPublic('/api/auth/mfa/login/verify',body,handle,false),
    finishLogin(data,handle) {
      const context=_mfaContext(handle),next=_tokenPair(data);
      saveTokens(data);
      _assertPair({revision:context.snapshot.revision+1},next);
      return mfa.capture();
    },
    status: handle => _mfaRequest('/api/auth/mfa/status',null,handle,'GET'),
    reauth: (body,handle) => _mfaRequest('/api/auth/mfa/reauth',body,handle),
    enroll: (body,handle) => _mfaRequest('/api/auth/mfa/enroll',body,handle),
    confirm: (body,handle) => _mfaRequest('/api/auth/mfa/enroll/confirm',body,handle),
    regenerate: (body,handle) => _mfaRequest('/api/auth/mfa/recovery-codes/regenerate',body,handle),
    revoke: (body,handle) => _mfaRequest('/api/auth/mfa/revoke',body,handle),
    close(handle) {
      const context=_mfaContext(handle);clearTokens();
      _assertPair({revision:context.snapshot.revision+1},{token:'',refresh:''});return mfa.capture();
    },
    operation(method,path,body={},idempotencyKey=null) {
      if(typeof method!=='string'||typeof path!=='string')throw _mfaError('mfa_action_invalid');
      const rule=_mfaRules.find(row=>row[1]===method && row[2].test(path));
      if (!rule || (idempotencyKey!==null && (!['billing.checkout','billing.subscribe','billing.mp'].includes(rule[0]) || typeof idempotencyKey!=='string' || !/^[\x21-\x7e]{1,128}$/.test(idempotencyKey)))) throw _mfaError('mfa_action_invalid');
      const encoded=JSON.stringify(body,(_key,value)=>{
        if((typeof value==='number'&&!Number.isFinite(value))||['undefined','function','symbol','bigint'].includes(typeof value))throw _mfaError('mfa_action_invalid');
        return value;
      });
      if (!encoded || !body || Array.isArray(body) || typeof body!=='object') throw _mfaError('mfa_action_invalid');
      const context=mfa.capture(),handle=Object.freeze({action:rule[0],revision:context.revision});
      _mfaOperations.set(handle,{context,method,path,body:JSON.parse(encoded),idempotencyKey});return handle;
    },
    checkOperation(operation) {
      const value=_mfaOperations.get(operation);if(!value)throw _sessionChanged();_mfaContext(value.context);
    },
    async grant(operation,factor={}) {
      _assertSnapshot(operation);
      const value=_mfaOperations.get(operation);if(!value)throw _mfaError('mfa_action_invalid');_mfaContext(value.context);
      const body={method:value.method,path:value.path,body:value.body,...(value.idempotencyKey===null?{}:{idempotency_key:value.idempotencyKey}),...factor};
      if(Object.keys(factor).some(name=>!['code','recovery_code'].includes(name)) || Object.keys(factor).length>1)throw _mfaError('mfa_invalid_input');
      const reply=await _mfaRequest('/api/auth/mfa/step-up',body,value.context);_mfaContext(value.context);
      if(!reply || !_mfaBearer(reply.grant) || !_mfaExpiry(reply.expires_at) || reply.single_use!==true || reply.method!==value.method || reply.path!==value.path || reply.action!==operation.action)throw _mfaError();
      const handle=Object.freeze({action:operation.action});_mfaGrants.set(handle,{operation,proof:reply.grant});return handle;
    },
    async execute(operation,grant) {
      _assertSnapshot(operation);
      const value=_mfaOperations.get(operation),permit=_mfaGrants.get(grant);
      if(!value || !permit || permit.operation!==operation)throw _mfaError('mfa_grant_consumed');
      _mfaGrants.delete(grant);_mfaOperations.delete(operation);
      const context=_mfaContext(value.context),headers={'X-MFA-Grant':permit.proof,...(value.idempotencyKey===null?{}:{'Idempotency-Key':value.idempotencyKey})};
      permit.proof=null;
      return request(value.method,value.path,value.body,headers,true,{snapshot:context.snapshot,pair:context.pair});
    },
    async perform(method,path,body={},key=null) {
      const operation=mfa.operation(method,path,body,key),value=_mfaOperations.get(operation);
      try {
        let grant;
        try { grant=await mfa.grant(operation); }
        catch(error) {
          _mfaContext(value.context);
          if(!['mfa_fresh_verification_required','mfa_enrollment_required'].includes(error.code))throw error;
          const ui=await _mfaUI();_mfaContext(value.context);grant=await ui.authorize(operation,error);_mfaContext(value.context);
        }
        return await mfa.execute(operation,grant);
      } finally { _mfaOperations.delete(operation); }
    },
  };

  // ── Billing ────────────────────────────────────────────────────────────────

  if (typeof window.addEventListener === 'function') {
    const discardMfa=()=>{_mfaContexts=new WeakMap();_mfaOperations=new WeakMap();_mfaGrants=new WeakMap();if(_retainedLogin&&!_invalidated&&!_hidden&&_retainedLogin.value.snapshot.revision===_credentials.revision&&_samePair(_retainedLogin.value.pair,_credentials.pair))_mfaContexts.set(_retainedLogin.handle,_retainedLogin.value);};
    window.addEventListener('metodobase-session-changed',discardMfa);
    window.addEventListener('pagehide',discardMfa);
  }

  // Google subject association is purpose-closed and bound to one exact access.
  function _googleLinkBody(body, required, optional = []) {
    if (!body || typeof body !== 'object' || Array.isArray(body) ||
        required.some(key => !Object.prototype.hasOwnProperty.call(body,key)) ||
        Object.keys(body).some(key => !required.includes(key) && !optional.includes(key))) throw _mfaError('google_link_invalid_input');
  }
  function _googleLinkPrimary(body) {
    if (typeof body.password !== 'string' || !body.password ||
        (Object.prototype.hasOwnProperty.call(body,'code') && (typeof body.code !== 'string' || !/^\d{6}$/.test(body.code))) ||
        (Object.prototype.hasOwnProperty.call(body,'recovery_code') && (typeof body.recovery_code !== 'string' || !/^[A-Za-z0-9_-]{22}$/.test(body.recovery_code))) ||
        ('code' in body && 'recovery_code' in body)) throw _mfaError('google_link_invalid_input');
  }
  const googleLink = {
    capture: mfa.capture, check: mfa.check, context: mfa.context, verify: mfa.verify, close: mfa.close,
    status(handle, after = null) {
      if (after !== null && (typeof after !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(after))) throw _mfaError('google_link_invalid_input');
      return _mfaRequest('/api/auth/google/link/status'+(after === null ? '' : '?after='+after),null,handle,'GET');
    },
    start(body, handle) {
      _googleLinkBody(body,['password','google_credential'],['code','recovery_code']);_googleLinkPrimary(body);
      if (typeof body.google_credential !== 'string' || !body.google_credential) throw _mfaError('google_link_invalid_input');
      return _mfaRequest('/api/auth/google/link/start',body,handle);
    },
    confirm(body, handle) {
      _googleLinkBody(body,['intent','confirm']);
      if (!_mfaBearer(body.intent) || body.confirm !== true) throw _mfaError('google_link_invalid_input');
      return _mfaRequest('/api/auth/google/link/confirm',body,handle);
    },
    unlink(body, handle) {
      _googleLinkBody(body,['identity_id','expected_version','password'],['code','recovery_code']);_googleLinkPrimary(body);
      if (typeof body.identity_id !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(body.identity_id) || !Number.isSafeInteger(body.expected_version) || body.expected_version < 1 || body.expected_version > 2147483647) throw _mfaError('google_link_invalid_input');
      return _mfaRequest('/api/auth/google/link/unlink',body,handle);
    },
  };

  // Wire34: purpose-closed, exact-access operations. Nothing in the public
  // handle contains the key, request body, credentials or resource identity.
  let _followupOperations = new WeakMap();
  const _followupCauses = ['no_saved_plan','no_plan_in_window','plan_date_missing','membership_date_passed'];
  const _followupSteps = ['review_client_record','review_plan_history','review_membership_date'];
  const _followupInvalid = () => _mfaError('followup_invalid_input');
  function _followupId(value, uuid=false) {
    if (typeof value!=='string' || !value.length || value.length>36 || value.normalize('NFC')!==value || /[\p{C}/?#]/u.test(value) ||
        (uuid && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value))) throw _followupInvalid();
    return value;
  }
  function _followupVersion(value, zero=false) {
    if(!Number.isSafeInteger(value)||value<(zero?0:1)||value>2147483647)throw _followupInvalid();
    return value;
  }
  function _followupFields(body, fields) {
    if(!body||typeof body!=='object'||Array.isArray(body)||Object.keys(body).length!==fields.length||fields.some(k=>!Object.hasOwn(body,k)))throw _followupInvalid();
  }
  function _followupCommand(kind,body) {
    const fields={created:['client_id','cause','cause_evidence_hash','next_step','assignee_id','expected_active_task_id','confirm'],
      updated:['expected_version','next_step','assignee_id','confirm'],completed:['expected_version','outcome','confirm'],cancelled:['expected_version','reason','confirm']}[kind];
    if(!fields)throw _followupInvalid();_followupFields(body,fields);
    if(body.confirm!==true)throw _followupInvalid();
    if(kind==='created'){
      _followupId(body.client_id);
      if(!_followupCauses.includes(body.cause)||typeof body.cause_evidence_hash!=='string'||!/^[0-9a-f]{64}$/.test(body.cause_evidence_hash)||body.expected_active_task_id!==null)throw _followupInvalid();
    }else _followupVersion(body.expected_version);
    if(kind==='created'||kind==='updated'){
      if(!_followupSteps.includes(body.next_step))throw _followupInvalid();
      if(kind==='created'&&body.next_step!=='review_client_record'&&body.next_step!==(body.cause==='membership_date_passed'?'review_membership_date':'review_plan_history'))throw _followupInvalid();
      if(body.assignee_id!==null)_followupId(body.assignee_id);
    }
    if(kind==='completed'&&body.outcome!=='review_recorded')throw _followupInvalid();
    if(kind==='cancelled'&&!['created_in_error','no_longer_applicable','duplicate'].includes(body.reason))throw _followupInvalid();
    const encoded=JSON.stringify(body);if(new TextEncoder().encode(encoded).byteLength>8192)throw _followupInvalid();
    return JSON.parse(encoded);
  }
  async function _followupRequest(path,body,handle,method='GET',key=null) {
    const value=_mfaContext(handle);
    try {
      const result=await request(method,path,body,key===null?{}:{'Idempotency-Key':key},true,{snapshot:value.snapshot,pair:value.pair});
      _mfaContext(handle);return result;
    }catch(error){_mfaContext(handle);throw error;}
  }
  function _followupCursor(value) {
    if(typeof value!=='string'||!value.length||value.length>256||!/^[A-Za-z0-9_-]+$/.test(value))throw _followupInvalid();return value;
  }
  const followup = {
    capture:mfa.capture,check:mfa.check,session:mfa.context,verify:mfa.verify,
    contexto: handle => _followupRequest('/api/seguimiento/contexto',null,handle),
    candidates: (client,handle) => _followupRequest('/api/seguimiento/clientes/'+encodeURIComponent(_followupId(client))+'/candidatos',null,handle),
    tasks(handle,{status='open',after=null}={}) {
      if(!['open','completed','cancelled'].includes(status))throw _followupInvalid();
      return _followupRequest('/api/seguimiento/tareas?'+new URLSearchParams({status,limit:'50',...(after===null?{}:{after:_followupCursor(after)})}),null,handle);
    },
    task:(id,handle)=>_followupRequest('/api/seguimiento/tareas/'+_followupId(id,true),null,handle),
    history(id,handle,{afterVersion=0}={}) {
      return _followupRequest('/api/seguimiento/tareas/'+_followupId(id,true)+'/historial?'+new URLSearchParams({limit:'20',after_version:String(_followupVersion(afterVersion,true))}),null,handle);
    },
    assignees:(handle,after=null)=>_followupRequest('/api/seguimiento/responsables?limit=20'+(after===null?'':'&after='+encodeURIComponent(_followupId(after))),null,handle),
    metrics(handle,range=null) {
      const params=new URLSearchParams();if(range!==null){_followupFields(range,['from','through']);_progressRange(params,range);}
      return _followupRequest('/api/seguimiento/metricas'+(params.size?'?'+params:''),null,handle);
    },
    prepare(kind,id,body,handle) {
      _mfaContext(handle);const command=_followupCommand(kind,body);
      if(kind==='created'?id!==null:!_followupId(id,true))throw _followupInvalid();
      const path='/api/seguimiento/tareas'+(kind==='created'?'':'/'+id+({completed:'/completar',cancelled:'/cancelar'}[kind]||''));
      const key=crypto.randomUUID();_followupId(key,true);const operation=Object.freeze({kind});
      _followupOperations.set(operation,{handle,command,key,path,method:kind==='updated'?'PATCH':'POST',sent:false});return operation;
    },
    async send(operation) {
      const value=_followupOperations.get(operation);if(!value||value.sent)throw _followupInvalid();
      _mfaContext(value.handle);value.sent=true;
      const result=await _followupRequest(value.path,value.command,value.handle,value.method,value.key);
      if(!result?.operation||result.operation.request_key!==value.key)throw _mfaError('followup_invalid_response');
      return result;
    },
    discard: operation => _followupOperations.delete(operation),
  };
  if(typeof window.addEventListener==='function'){
    const discard=()=>{_followupOperations=new WeakMap();};
    window.addEventListener('metodobase-session-changed',discard);window.addEventListener('pagehide',discard);
  }

  // Nutrition35 is additive and purpose-closed. Exact access means a 401 never
  // rotates/replays a health declaration or substitutes another session.
  function _nutritionInput(){return _mfaError('nutrition_profile_invalid_input');}
  function _nutritionFields(value,keys){if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).length!==keys.length||keys.some(k=>!Object.hasOwn(value,k)))throw _nutritionInput();}
  function _nutritionDeclaration(value){
    _nutritionFields(value,['version','allergies','professional_review_requested']);
    if(value.version!==1||typeof value.professional_review_requested!=='boolean')throw _nutritionInput();
    const a=value.allergies;_nutritionFields(a,['version','status','foods','other_reported']);
    if(a.version!==1||!['not_reported','none_reported','reported'].includes(a.status)||typeof a.other_reported!=='boolean'||!Array.isArray(a.foods)||a.foods.length>250||new Set(a.foods).size!==a.foods.length||a.foods.some(v=>typeof v!=='string'||!v.length||v.length>128||/[\p{C}]/u.test(v))||(a.status==='reported')!==!!(a.foods.length||a.other_reported))throw _nutritionInput();
    return value;
  }
  function _nutritionBody(body,personal=false){
    const allowed=['edad','peso_kg','estatura_cm','sexo','grasa_corporal_pct','objetivo','nivel_actividad','notas','alimentos_excluidos','restricciones_nutricionales',...(personal?[]:['nombre','telefono','fecha_suscripcion','fecha_fin_suscripcion','plan_suscripcion_id','plan_numero','tipo_plan'])];
    if(!body||typeof body!=='object'||Array.isArray(body)||Object.keys(body).some(k=>!allowed.includes(k)))throw _nutritionInput();
    if(body.restricciones_nutricionales!==undefined&&body.restricciones_nutricionales!==null)_nutritionDeclaration(body.restricciones_nutricionales);
    const encoded=JSON.stringify(body,(_k,value)=>{if((typeof value==='number'&&!Number.isFinite(value))||['undefined','function','symbol','bigint'].includes(typeof value))throw _nutritionInput();return value;});
    if(new TextEncoder().encode(encoded).byteLength>32768)throw _nutritionInput();return JSON.parse(encoded);
  }
  async function _nutritionRequest(path,body,handle,method='GET'){
    const context=_mfaContext(handle);
    try{const result=await request(method,path,body,{},true,{snapshot:context.snapshot,pair:context.pair});_mfaContext(handle);return result;}
    catch(error){_mfaContext(handle);throw error;}
  }
  const nutrition={
    capture:mfa.capture,check:mfa.check,session:mfa.context,verify:mfa.verify,
    client:(key,handle)=>_nutritionRequest('/api/clientes/'+encodeURIComponent(_followupId(key)),null,handle),
    create:(body,handle)=>_nutritionRequest('/api/clientes',_nutritionBody(body),handle,'POST'),
    update:(key,body,handle)=>_nutritionRequest('/api/clientes/'+encodeURIComponent(_followupId(key)),_nutritionBody(body),handle,'PUT'),
    personal:handle=>_nutritionRequest('/api/usuario/perfil',null,handle),
    savePersonal:(body,handle)=>_nutritionRequest('/api/usuario/perfil',_nutritionBody(body,true),handle,'PUT'),
    catalog:handle=>_nutritionRequest('/api/alimentos/catalogo',null,handle),
    personalCatalog:handle=>_nutritionRequest('/api/usuario/catalogo-alimentos',null,handle),
  };

  // Own notification36 operations use the existing exact-access RAM fence.
  // Consent/queue/cancel never request a new MFA grant or refresh a session.
  let _notificationOperations=new WeakMap();
  const _notificationPurposes=['account_period_end','confirmed_payment_issue'];
  function _notificationInvalid(){return _mfaError('notification_invalid_input');}
  function _notificationFields(value,fields){if(!value||Object.prototype.toString.call(value)!=='[object Object]'||Object.keys(value).length!==fields.length||fields.some(key=>!Object.hasOwn(value,key)))throw _notificationInvalid();}
  function _notificationVersion(value,zero=false){if(!Number.isSafeInteger(value)||value<(zero?0:1)||value>2147483647)throw _notificationInvalid();}
  function _notificationContext(value){if(!['gym','personal'].includes(value))throw _notificationInvalid();return value;}
  function _notificationPurpose(value){if(!_notificationPurposes.includes(value))throw _notificationInvalid();return value;}
  function _notificationUUID(value){if(typeof value!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value))throw _notificationInvalid();return value;}
  async function _notificationRequest(path,handle,body=null,method='GET',key=null){
    const context=_mfaContext(handle);
    try{const value=await request(method,path,body,key?{'Idempotency-Key':key}:{},true,{snapshot:context.snapshot,pair:context.pair});_mfaContext(handle);return value;}
    catch(error){_mfaContext(handle);throw error;}
  }
  function _notificationPath(context,path){return '/api/notificaciones'+path+'?context='+_notificationContext(context);}
  const notifications36={
    check:mfa.check,session:mfa.context,verify:mfa.verify,
    context:(context,handle)=>_notificationRequest(_notificationPath(context,'/contexto'),handle),
    preferences:(context,handle)=>_notificationRequest(_notificationPath(context,'/preferencias'),handle),
    candidates:(context,handle)=>_notificationRequest(_notificationPath(context,'/candidatos'),handle),
    outbox:(context,handle,after=null)=>_notificationRequest(_notificationPath(context,'/outbox')+'&limit=20'+(after===null?'':'&after='+_notificationUUID(after)),handle),
    metrics:(context,handle,range=null)=>{
      const params=new URLSearchParams();if(range!==null){_notificationFields(range,['from','through']);try{_progressRange(params,range);}catch{throw _notificationInvalid();}}
      return _notificationRequest(_notificationPath(context,'/metricas')+(params.size?'&'+params:''),handle);
    },
    operation(kind,context,target,body,handle){
      _mfaContext(handle);let path,method;
      if(kind==='preference'){
        path='/preferencias/'+_notificationPurpose(target);method='PUT';_notificationFields(body,['expected_version','enabled','interval_hours','confirm']);
        _notificationVersion(body.expected_version,true);if(typeof body.enabled!=='boolean'||![24,72,168].includes(body.interval_hours))throw _notificationInvalid();
      }else if(kind==='observe'){if(target!==null)throw _notificationInvalid();path='/observar';method='POST';_notificationFields(body,[]);}
      else if(kind==='queue'){
        if(target!==null)throw _notificationInvalid();path='/outbox';method='POST';_notificationFields(body,['purpose','preference_id','expected_preference_version','fact_id','source_hash','confirm']);
        _notificationPurpose(body.purpose);_notificationUUID(body.preference_id);_notificationUUID(body.fact_id);_notificationVersion(body.expected_preference_version);
        if(typeof body.source_hash!=='string'||!/^[0-9a-f]{64}$/.test(body.source_hash))throw _notificationInvalid();
      }else if(kind==='cancel'){path='/outbox/'+_notificationUUID(target)+'/cancelar';method='POST';_notificationFields(body,['expected_version','confirm']);_notificationVersion(body.expected_version);}
      else throw _notificationInvalid();
      if(kind!=='observe'&&body.confirm!==true)throw _notificationInvalid();
      const encoded=JSON.stringify(body);if(new TextEncoder().encode(encoded).byteLength>8192)throw _notificationInvalid();
      const operation=Object.freeze({kind});_notificationOperations.set(operation,{path:_notificationPath(context,path),method,body:JSON.parse(encoded),key:_notificationUUID(crypto.randomUUID()),handle});return operation;
    },
    send(operation){const value=_notificationOperations.get(operation);if(!value)throw _notificationInvalid();_mfaContext(value.handle);return _notificationRequest(value.path,value.handle,value.body,value.method,value.key);},
    discard(operation){_notificationOperations.delete(operation);},
  };
  if(typeof window.addEventListener==='function')for(const event of ['metodobase-session-changed','pagehide'])window.addEventListener(event,()=>{_notificationOperations=new WeakMap();});

  // Own account37 operations. Removing this block restores the previous API RAW.
  const _accountClosures=new WeakMap();
  function _accountError(code='account_security_invalid_response',status=null,fields=[]) {
    return Object.assign(new Error('No se pudo confirmar esta operación de seguridad.'),{code,status,fields});
  }
  function _accountBody(value) {
    let body;try{body=_captureCookieBody(value);}catch{throw _accountError('account_security_invalid_input');}const keys=['reauthentication_token','new_password','confirm_password','code','recovery_code'];
    if(Object.keys(body).some(key=>!keys.includes(key))||!_mfaBearer(body.reauthentication_token)||typeof body.new_password!=='string'||typeof body.confirm_password!=='string'||body.new_password!==body.confirm_password||Array.from(body.new_password).length<12||new TextEncoder().encode(body.new_password).length>72||/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(body.new_password)||(body.code!==undefined&&!/^\d{6}$/.test(body.code))||(body.recovery_code!==undefined&&!/^[A-Za-z0-9_-]{22}$/.test(body.recovery_code))||(body.code!==undefined&&body.recovery_code!==undefined))throw _accountError('account_security_invalid_input');
    return body;
  }
  function _accountUnauthorized(context) {
    // A late rejection belongs to its captured access, never a newer actor.
    _assertPair(context.snapshot,context.pair);
    _invalidateSession();throw _sessionChanged();
  }
  async function _accountAuthority(handle,run) {
    const context=_mfaContext(handle);
    try{const value=await run();_mfaContext(handle);return value;}
    catch(error){_mfaContext(handle);if(error.status===401)_accountUnauthorized(context);throw error;}
  }
  async function _accountPost(path,body,context) {
    let response,encoded=JSON.stringify(body);body=null;
    const csrf=typeof document!=='undefined'?document.querySelector?.('meta[name="csrf-token"]')?.content:null;
    const headers={'Content-Type':'application/json','Accept':'application/json','X-MetodoBase-Browser':'1',Authorization:'Bearer '+context.pair.token};
    if(typeof csrf==='string'&&csrf&&csrf.length<=512&&!/[\r\n]/.test(csrf))headers['X-CSRF-Token']=csrf;
    try{const pending=fetch(API_BASE+path,{method:'POST',headers,body:encoded,credentials:'same-origin',mode:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer'});encoded=null;response=await pending;}catch{encoded=null;throw _accountError('account_security_unconfirmed');}
    if(response.status===401)_accountUnauthorized(context);
    let data;try{data=await response.json();}catch{throw _accountError('account_security_unconfirmed',response.status>=500?response.status:null);}
    if(!response.ok){const detail=data?.detail,known=['reauthentication_token','new_password','confirm_password','code','recovery_code'];throw _accountError(typeof detail?.code==='string'?detail.code:'account_security_rejected',response.status,Array.isArray(detail?.fields)?detail.fields.filter(key=>known.includes(key)):[]);}
    return data;
  }
  const accountSecurity=Object.freeze({
    async context(){
      await _readyPromise;const handle=mfa.capture();
      return _accountAuthority(handle,async()=>{
        const me=await _mfaRequest('/api/auth/me',null,handle,'GET');_mfaContext(handle);
        if(!me||typeof me.id!=='string'||!me.id||typeof me.role!=='string'||!Number.isSafeInteger(me.session_version))throw _mfaError();
        _mfaContexts.get(handle).subject=JSON.stringify([me.id,me.role,me.team_gym_id||null,me.session_version]);
        return {handle,me};
      });
    },
    check:handle=>mfa.check(handle),verify:handle=>_accountAuthority(handle,()=>mfa.verify(handle)),factorStatus:handle=>_accountAuthority(handle,()=>mfa.status(handle)),reauth:(body,handle)=>mfa.reauth(body,handle),
    status:handle=>{const context=_mfaContext(handle);return _accountAuthority(handle,()=>request('GET','/api/account/security',null,{},true,{snapshot:context.snapshot,pair:context.pair}));},
    async requestEmail(handle){
      const context=_mfaContext(handle);
      return _withCookieLock(context.snapshot,async()=>{
        _mfaContext(handle);const data=await _accountPost('/api/account/security/email/request',{},context);_mfaContext(handle);
        if(!data||!((data.email_verified===true&&data.delivery==='not_required')||(data.email_verified===false&&data.delivery==='provider_accepted'&&data.expires_in_seconds===1800))||Object.keys(data).some(key=>!['email_verified','delivery','expires_in_seconds'].includes(key)))throw _accountError();
        return data;
      });
    },
    async changePassword(value,handle){
      let body=_accountBody(value);value=null;const context=_mfaContext(handle);
      try{return await _withCookieLock(context.snapshot,async()=>{
        _mfaContext(handle);let state='changed';
        try{const pending=_accountPost('/api/account/security/password',body,context);body=null;const data=await pending;_mfaContext(handle);
          if(!data||data.code!=='account_password_changed'||data.reauthenticate!==true||data.sessions_revoked!==true||Object.keys(data).some(key=>!['code','reauthenticate','sessions_revoked'].includes(key)))throw _accountError();
        }catch(error){body=null;_mfaContext(handle);if(error.status&&error.status<500)throw error;state='unconfirmed';}
        _mfaContext(handle);const closed=_publishBoundary(),result=Object.freeze({state,server_confirmed:state==='changed'});_assertSnapshot(closed);_accountClosures.set(result,closed);return result;
      });}finally{body=null;}
    },
    checkClosed(result){const closed=_accountClosures.get(result);if(!closed)throw _sessionChanged();_assertSnapshot(closed);},
  });

  const billing = {
    config:       () => request('GET', '/api/billing/config'),
    subscription: () => request('GET', '/api/billing/subscription'),
    payments:     () => request('GET', '/api/billing/payments'),
    checkout: (plan, key) =>
      mfa.perform('POST', '/api/billing/checkout', {
        plan,
        success_url: '/suscripciones?result=success',
        cancel_url: '/suscripciones?result=canceled',
      }, key || null),
    stripeSubscribe: (plan, payment_method_id, key) =>
      mfa.perform('POST', '/api/billing/stripe/subscribe', {
        plan,
        payment_method_id,
      }, key || null),
    confirmSubscription: (subscription_id) =>
      mfa.perform('POST', '/api/billing/confirm-subscription', {
        subscription_id,
      }),
    mpPreference: (plan, key) =>
      mfa.perform('POST', '/api/billing/mp/preference', {
        plan,
        success_url: '/suscripciones?result=success',
        cancel_url: '/suscripciones?result=canceled',
      }, key || null),
    portal: () =>
      mfa.perform('POST', '/api/billing/portal', {
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
      await _readyPromise;
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
      await _readyPromise;
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
      const uuidCursors = ['purchase','generation','member_link','progress_consent'];
      for (const name of [...integerCursors,...uuidCursors,'diary']) {
        const value = cursors[name];
        if (value == null) continue;
        if (name === 'progress_consent' && (typeof value !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value))) throw new Error('No se pudo continuar la descarga. Empieza una descarga nueva.');
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
      await _readyPromise;
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
    publicar: (client, link, plan, linkVersion, publicationVersion, publicationId, context) => {
      if (!Number.isSafeInteger(plan) || plan < 1 || plan > 2147483647 || !Number.isSafeInteger(publicationVersion) || publicationVersion < 0 || publicationVersion > 2147483647) throw new Error('Selecciona un plan válido.');
      if (publicationVersion === 0 ? publicationId !== null : (typeof publicationId !== 'string' || _linkUUID(publicationId) !== publicationId.toLowerCase())) throw new Error('Vuelve a consultar la publicación antes de confirmar.');
      return _linkRequest('POST', _clientLinkPath(client) + '/' + _linkUUID(link) + '/publicaciones', {plan_id:plan,expected_link_version:_linkVersion(linkVersion),expected_publication_id:publicationId,expected_publication_version:publicationVersion}, context);
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

  function _progressInvalid() { return Object.assign(new Error('Vuelve a consultar el estado de progreso antes de continuar.'), {code:'progress_invalid_input'}); }
  function _progressUUID(value) {
    if (typeof value !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value)) throw _progressInvalid();
    return value;
  }
  function _progressVersion(value, initial = false) {
    if (!Number.isSafeInteger(value) || value < (initial ? 0 : 1) || value > 2147483647) throw _progressInvalid();
    return value;
  }
  function _progressRange(params, range) {
    if (range == null) return;
    if (!range || Object.keys(range).length !== 2 || typeof range.from !== 'string' || typeof range.through !== 'string') throw _progressInvalid();
    _personalDay(range.from); _personalDay(range.through);
    const days=(Date.parse(range.through+'T00:00:00Z')-Date.parse(range.from+'T00:00:00Z'))/86400000;
    if (days < 0 || days >= 62) throw _progressInvalid();
    params.set('from',range.from); params.set('through',range.through);
  }
  function _progressClient(client) {
    if (typeof client !== 'string' || !client || client.length > 128) throw _progressInvalid();
    return '/api/clientes/'+encodeURIComponent(client);
  }
  function _progressConsent(link) { return '/api/usuario/vinculos/'+_progressUUID(link)+'/progreso/consentimiento'; }
  function _progressRequest(method,path,body,context) {
    const pair=_assertSnapshot(context);
    let safeBody=null;
    if(body!==null){
      if(!body || typeof body!=='object' || Array.isArray(body)) throw _progressInvalid();
      const encoded=JSON.stringify(body,(_key,value)=>{
        if((typeof value==='number' && !Number.isFinite(value)) || ['undefined','function','symbol','bigint'].includes(typeof value)) throw _progressInvalid();
        return value;
      });
      if(new TextEncoder().encode(encoded).byteLength>8192) throw _progressInvalid();
      safeBody=JSON.parse(encoded);
    }
    _assertPair(context,pair);
    // Writes are one-shot and bound to the exact access; they never request an
    // MFA grant, rotate credentials, or replay after a401/ambiguous response.
    return request(method,path,safeBody,{},true,{snapshot:context,...(method==='GET'?{}:{pair})});
  }
  const progreso = {
    contexto: () => vinculos.contexto(),
    validarContexto: context => vinculos.validarContexto(context),
    verificarContexto: context => vinculos.verificarContexto(context),
    bootstrap: (context,after=null) => {
      const params=new URLSearchParams({limit:'100'});
      if(after!==null){if(typeof after!=='string'||!after.length||after.length>36)throw _progressInvalid();params.set('after',after);}
      return _progressRequest('GET','/api/usuario/progreso/contexto?'+params,null,context);
    },
    mediciones: (profile,context,{range=null,cursor=null}={}) => {
      const params=new URLSearchParams({source_profile_id:_progressUUID(profile),limit:'100'});_progressRange(params,range);
      if(cursor!==null){if(typeof cursor!=='string'||!cursor.length||cursor.length>512)throw _progressInvalid();params.set('cursor',cursor);}
      return _progressRequest('GET','/api/usuario/progreso/mediciones?'+params,null,context);
    },
    medicion: (key,context) => _progressRequest('GET','/api/usuario/progreso/mediciones/'+_progressUUID(key),null,context),
    guardarMedicion: (key,body,context) => {
      _progressVersion(body?.expected_version,true);_progressUUID(body?.source_profile_id);_personalDay(body?.measured_on);
      return _progressRequest('PUT','/api/usuario/progreso/mediciones/'+_progressUUID(key),body,context);
    },
    retirarMedicion: (key,version,context) => _progressRequest('POST','/api/usuario/progreso/mediciones/'+_progressUUID(key)+'/retirar',{expected_version:_progressVersion(version)},context),
    completados: (context,range=null) => {
      const params=new URLSearchParams();_progressRange(params,range);
      return _progressRequest('GET','/api/usuario/progreso/completados'+(params.size?'?'+params:''),null,context);
    },
    consentimientos: (context,after=null) => _progressRequest('GET','/api/usuario/progreso/consentimientos?limit=100'+(after===null?'':'&after='+_progressUUID(after)),null,context),
    consentimiento: (link,context) => _progressRequest('GET',_progressConsent(link),null,context),
    guardarConsentimiento: (link,body,context) => {
      _progressVersion(body?.expected_version,true);_progressVersion(body?.expected_link_version);
      if(body.expected_version===0 ? body.expected_consent_id!==null : !_progressUUID(body.expected_consent_id)) throw _progressInvalid();
      return _progressRequest('PUT',_progressConsent(link),body,context);
    },
    retirarConsentimiento: (link,id,version,context) => _progressRequest('POST',_progressConsent(link)+'/retirar',{expected_consent_id:_progressUUID(id),expected_version:_progressVersion(version)},context),
    profesional: (client,context,after=null) => _progressRequest('GET',_progressClient(client)+'/progreso?limit=100'+(after===null?'':'&after='+_progressVersion(after)),null,context),
    contextoCompartido: (client,link,context) => _progressRequest('GET',_progressClient(client)+'/vinculacion/'+_progressUUID(link)+'/progreso/contexto',null,context),
    compartido: (client,link,expected,context,{range=null,after=null}={}) => {
      const params=new URLSearchParams({expected_consent_id:_progressUUID(expected.id),expected_version:String(_progressVersion(expected.version)),expected_link_version:String(_progressVersion(expected.linkVersion)),limit:'100'});
      _progressRange(params,range);if(after!==null)params.set('after',_progressUUID(after));
      return _progressRequest('GET',_progressClient(client)+'/vinculacion/'+_progressUUID(link)+'/progreso?'+params,null,context);
    },
  };

  const team = {
    list: () => request('GET', '/api/gym/team'),
    invite: (data) => mfa.perform('POST', '/api/gym/team/invite', data),
    role: (id, role) => mfa.perform('PATCH', '/api/gym/team/' + encodeURIComponent(id) + '/role', {role}),
    remove: (id) => mfa.perform('DELETE', '/api/gym/team/' + encodeURIComponent(id), {}),
    resend: (id) => mfa.perform('POST', '/api/gym/team/' + encodeURIComponent(id) + '/resend-invite', {}),
    info: (token) => request('POST', '/api/auth/invite-info', {token}, {}, false),
    accept: (token, password) => _browserAccount('/api/auth/accept-invite',{token,password}),
  };
  const session=Object.freeze({get ready(){return _readyPromise;},identity:()=>getToken()&&_metadata?Object.freeze({..._metadata}):null,capture:()=>Object.freeze(_snapshot()),check:context=>{_assertSnapshot(context);},accepted:data=>{const value=_delivered.get(data);if(!value)throw _sessionChanged();_assertPair(value.snapshot,value.pair);return Object.freeze({...value.snapshot});},clientCount:async()=>{await _readyPromise;const snapshot=_snapshot(),pair=_assertSnapshot(snapshot);return request('GET','/api/clientes?limite=1',null,{},true,{snapshot,pair});}});
  _readyPromise=_bootstrap();_readyPromise.catch(()=>{});
  return { clientes, planes, stats, auth, billing, gym, usuario, vinculos, progreso, team, mfa, googleLink, followup, nutrition, notifications36, accountSecurity, session, getToken, clearTokens, saveTokens };
})();

