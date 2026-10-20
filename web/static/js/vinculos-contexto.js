/* R12 lifecycle only. No resource DTO, authority, bearer or data is persisted here. */
(() => {
  'use strict';
  const sessionCodes = new Set(['session_changed', 'session_storage_error', 'session_expired']);
  const changed = () => Object.assign(new Error('La sesión o el contexto cambió. Vuelve a abrir esta página desde tu cuenta.'), {code:'session_changed'});

  function create(options = {}) {
    const api = options.api || Api.vinculos;
    let context = null, invalid = false, epoch = 0;
    const scopes = new Set();
    function invalidate(error = changed()) {
      if (invalid) return error;
      invalid = true; epoch++; context = null;
      for (const scope of scopes) {
        try { scope.invalidate(error); } catch { /* Clear every sibling scope even if a consumer fails. */ }
      }
      options.onInvalidated?.(error);
      return error;
    }
    function check(ticket = epoch) {
      if (invalid || !context || ticket !== epoch) throw changed();
      try { api.validarContexto(context); }
      catch (error) { throw invalidate(error); }
    }
    async function verify(ticket = epoch) {
      check(ticket);
      try { await api.verificarContexto(context); check(ticket); }
      catch (error) {
        // A late network failure must not become an error message in a new account.
        check(ticket);
        if (sessionCodes.has(error.code)) invalidate(error);
        throw error;
      }
    }
    async function read(task) {
      const ticket = epoch;
      await verify(ticket); check(ticket);
      let result;
      try {
        result = await task(context);
      } catch (error) {
        check(ticket);
        if (sessionCodes.has(error.code)) { invalidate(error); throw error; }
        await verify(ticket); check(ticket);
        throw error;
      }
      check(ticket);
      await verify(ticket); check(ticket);
      return result;
    }
    function render(task) {
      check(); task(); check();
    }
    function scope(onInvalidated) {
      check();
      let active = true;
      const self = {
        check() { if (!active) throw Object.assign(changed(), {code:'member_context_changed'}); check(); },
        invalidate(error = changed()) {
          if (!active) return;
          active = false; scopes.delete(self); onInvalidated?.(error);
        },
        async read(task) {
          self.check();
          const result = await read(async value => {
            self.check(); const data = await task(value); self.check(); return data;
          });
          self.check(); return result;
        },
        render(task) { self.check(); task(); self.check(); },
      };
      scopes.add(self);
      return self;
    }
    window.addEventListener('storage', event => {
      if (event.key === null || ['mb_token','mb_refresh_token','mb_session_epoch'].includes(event.key)) invalidate();
    });
    window.addEventListener('metodobase-session-changed', event => invalidate(
      Object.assign(changed(), {code:sessionCodes.has(event.detail?.code) ? event.detail.code : 'session_changed'})));
    window.addEventListener('pagehide', () => invalidate(), {once:true});
    return {
      async start() {
        const ticket = epoch;
        if (invalid || context) throw changed();
        try {
          const initial = await api.contexto();
          if (invalid || ticket !== epoch) throw changed();
          context = initial; check(ticket); return initial.me;
        } catch (error) { throw invalidate(error); }
      },
      check, verify, read, render, scope, invalidate,
      get active() { return !invalid && !!context; },
    };
  }
  window.MemberLinkContext = Object.freeze({create});
})();
