/* Explicit, bounded history pages. Rows and opaque positions live only in memory. */
(() => {
  'use strict';
  const sessionCodes = new Set(['session_changed','session_expired','session_storage_error']);
  function create(options) {
    const personal = options.personal;
    let rows = [], next = null, loaded = false, busy = false, invalid = false, epoch = 0;
    let error = '', restartRequired = false;
    const changed = () => Object.assign(new Error('La sesión cambió. Vuelve a abrir el historial desde tu cuenta.'), {code:'session_changed'});
    function invalidate(reason = changed()) {
      if (invalid) return;
      invalid = true; epoch++; rows = []; next = null; loaded = false; busy = false; error = ''; restartRequired = false;
      options.onInvalidated?.(reason);
      personal.invalidate(reason);
    }
    function check(ticket = epoch) {
      if (invalid || ticket !== epoch) throw changed();
      try { personal.check(); }
      catch (reason) { invalidate(reason); throw reason; }
    }
    const view = () => ({rows:rows.slice(), loaded, busy, hasMore:next !== null, error, restartRequired, invalid});
    function emit(ticket) {
      check(ticket); options.onChange?.(view()); check(ticket);
    }
    async function load() {
      if (invalid || busy || restartRequired || (loaded && next === null)) return;
      const ticket = epoch, position = next;
      try {
        check(ticket); busy = true; error = ''; emit(ticket);
        // Controls can synchronously invalidate the context; never continue with a stale position.
        check(ticket);
        const data = await personal.read(context => Api.usuario.historial(context, {cursor:position, limit:50}));
        check(ticket);
        if (!data || !Array.isArray(data.planes) || data.planes.length > 50 ||
            !(data.next_cursor === null || (typeof data.next_cursor === 'string' && data.next_cursor.length > 0 && data.next_cursor.length <= 180)) ||
            (data.next_cursor !== null && (data.next_cursor === position || data.planes.length === 0)) ||
            data.planes.some(row => !row || !PersonalPlanOperation.validPlanId(row.id))) throw new Error('El servidor devolvió una página incompleta.');
        const ids = new Set(rows.map(row => row.id));
        const additions = [];
        for (const row of data.planes) {
          check(ticket);
          if (!ids.has(row.id)) { ids.add(row.id); additions.push({...row}); }
        }
        check(ticket); rows = rows.concat(additions); next = data.next_cursor; loaded = true;
        busy = false; restartRequired = false; emit(ticket);
      } catch (reason) {
        if (invalid || ticket !== epoch) return;
        if (sessionCodes.has(reason.code)) { invalidate(reason); return; }
        try { check(ticket); } catch { return; }
        busy = false; restartRequired = reason.code === 'history_cursor_invalid';
        error = restartRequired ? 'No se pudo continuar esta consulta. Actualiza el historial para consultar desde el inicio.' :
          'No se pudieron cargar los planes. Se conservan los que ya consultaste. Puedes volver a intentar.';
        try { emit(ticket); } catch { /* Context invalidation already clears the view. */ }
      }
    }
    async function restart() {
      if (invalid || busy) return;
      try { check(); } catch { return; }
      rows = []; next = null; loaded = false; error = ''; restartRequired = false;
      return load();
    }
    window.addEventListener('storage', event => {
      if (event.key === null || ['mb_token','mb_refresh_token'].includes(event.key)) invalidate();
    });
    window.addEventListener('metodobase-session-changed', event => invalidate(Object.assign(changed(), {code:event.detail?.code || 'session_changed'})));
    window.addEventListener('pagehide', () => invalidate(), {once:true});
    return {load, restart, check, invalidate, get view() { return view(); }};
  }
  window.PersonalHistory = Object.freeze({create});
})();
