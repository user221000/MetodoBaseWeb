/* One personal generation intent, in memory only. The server owns quota and identity. */
(() => {
  'use strict';
  const sessionCodes = new Set(['session_changed', 'session_expired', 'session_storage_error']);
  const validPlanId = id => Number.isSafeInteger(id) && id > 0 && id <= 2147483647;
  function create(options = {}) {
    let context = null, invalid = false, epoch = 0, operation = null, attempt = 0;
    let state = 'idle';
    const notify = (message = '') => options.onState?.({state, message});
    const changed = () => Object.assign(new Error('La sesión cambió. Vuelve a abrir esta página desde tu cuenta.'), {code:'session_changed'});
    function invalidate(error = changed()) {
      if (!invalid) {
        invalid = true; epoch++; attempt++; operation = null; context = null; state = 'invalidated';
        options.onInvalidated?.(error); notify(error.message);
      }
      return error;
    }
    function check(ticket = epoch) {
      if (invalid || !context || ticket !== epoch) throw changed();
      try { Api.usuario.validarContexto(context); }
      catch (error) { throw invalidate(error); }
    }
    async function verify(ticket = epoch) {
      check(ticket);
      try { await Api.usuario.verificarContexto(context); check(ticket); }
      catch (error) { if (sessionCodes.has(error.code)) invalidate(error); throw error; }
    }
    async function read(task) {
      const ticket = epoch;
      await verify(ticket); check(ticket);
      try {
        const result = await task(context);
        await verify(ticket); check(ticket);
        return result;
      } catch (error) {
        if (sessionCodes.has(error.code)) invalidate(error);
        throw error;
      }
    }
    function classify(error) {
      if (['generation_in_progress'].includes(error.code)) return ['pending', 'La solicitud sigue pendiente. Puedes consultar tu historial o volver a consultar esta misma solicitud.'];
      if (['generation_reconciliation_required', 'generation_result_unavailable'].includes(error.code)) return ['reconciliation', 'No se pudo confirmar el resultado. Consulta el historial; evita iniciar otra generación mientras se revisa.'];
      if (['generation_failed', 'generation_unavailable'].includes(error.code)) return ['failed', 'Esta solicitud no pudo completarse. Revisa tu perfil antes de iniciar otra generación.'];
      if (error.code === 'monthly_plan_limit') return ['quota', 'Has utilizado los planes disponibles de este mes. Consulta tu suscripción y tu historial.'];
      if (error.status === 400 && !error.code) return ['profile', error.message];
      return ['unconfirmed', 'No se pudo confirmar si tu plan quedó listo. Consulta el historial o reintenta la misma solicitud.'];
    }
    async function generate(newIntent = false) {
      if (invalid || state === 'submitting') return;
      if (newIntent) {
        if (!['completed','failed','profile'].includes(state)) return;
        operation = null; state = 'idle';
      } else if (['completed','failed','profile','quota'].includes(state)) return;
      if (!operation) {
        if (state !== 'idle') return;
        operation = {key:crypto.randomUUID()};
      }
      const current = operation, ticket = epoch, ownAttempt = ++attempt;
      state = 'submitting'; notify('Generando tu plan. Mantén esta página abierta.');
      let timer;
      try {
        await verify(ticket); check(ticket);
        const response = await Promise.race([
          Api.usuario.generarPlan(current.key, context),
          new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('No se confirmó la respuesta.')), options.timeoutMs || 90000); }),
        ]);
        await verify(ticket); check(ticket);
        if (ownAttempt !== attempt || current !== operation) return;
        if (!response || !validPlanId(response.plan_id) || !response.plan || typeof response.plan !== 'object' || Array.isArray(response.plan) || !Object.keys(response.plan).length) {
          throw new Error('El servidor devolvió un resultado incompleto.');
        }
        state = 'completed';
        options.onResult?.(response);
        notify(response.tiene_pdf ? 'Tu plan está listo. Puedes descargar el PDF de este plan.' : 'Tu plan está listo. El PDF no está disponible.');
      } catch (error) {
        if (sessionCodes.has(error.code)) { invalidate(error); return; }
        if (invalid || ticket !== epoch || ownAttempt !== attempt || current !== operation) return;
        try { check(ticket); } catch { return; }
        [state, current.message] = classify(error); notify(current.message);
      } finally { clearTimeout(timer); }
    }
    const storageChanged = event => {
      if (event.key === null || ['mb_token','mb_refresh_token'].includes(event.key)) invalidate();
    };
    window.addEventListener('storage', storageChanged);
    window.addEventListener('pagehide', () => invalidate(), {once:true});
    return {
      async start() {
        const ticket = epoch;
        try {
          const initial = await Api.usuario.contexto();
          if (invalid || ticket !== epoch) throw changed();
          context = initial; notify(); return initial.me;
        } catch (error) { throw invalidate(error); }
      },
      read, verify, check, invalidate, generate,
      get context() { return context; },
      get active() { return !invalid && !!context; },
      get state() { return state; },
      validPlanId,
    };
  }
  window.PersonalPlanOperation = Object.freeze({create, validPlanId});
})();
