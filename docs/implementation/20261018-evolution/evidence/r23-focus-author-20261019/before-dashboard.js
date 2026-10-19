/* Operational facts, bounded reads and explicit navigation. No client storage or analytics. */
(() => {
  'use strict';
  const causes = Object.freeze({
    no_saved_plan: 'Sin plan guardado', no_plan_in_window: 'Sin plan en la ventana de actividad',
    plan_date_missing: 'Fecha de plan desconocida', membership_date_passed: 'Fecha de membresía pasada',
  });
  const sessionCodes = new Set(['session_changed','session_expired','session_storage_error']);
  const changed = () => Object.assign(new Error('La sesión cambió. Vuelve a abrir el dashboard.'), {code:'session_changed'});
  function create(api, render = () => {}) {
    let context = null, ticket = 0;
    const state = {items:[], metrics:null, asOf:null, windowDays:null, hasMore:false, busy:false, invalid:false, error:'', limit:50};
    function clear() { state.items=[]; state.metrics=null; state.asOf=null; state.windowDays=null; state.hasMore=false; }
    function invalidate() {
      ticket++; context=null; clear(); state.busy=false; state.invalid=true;
      state.error='La sesión cambió o no se pudo verificar. Vuelve a abrir el dashboard.'; render(state);
    }
    function check(own = ticket) {
      if (state.invalid || own !== ticket || !context) throw changed();
      try { api.validarContexto(context); } catch (error) { invalidate(); throw error; }
    }
    function notify() { if (context && !state.invalid) check(); render(state); if (context && !state.invalid) check(); }
    async function verify(own) { check(own); await api.verificarContexto(context); check(own); }
    function parse(body, limit) {
      const integer = value => Number.isSafeInteger(value) && value >= 0;
      if (!body || !Array.isArray(body.items) || body.items.length>limit || typeof body.has_more!=='boolean' ||
          !Number.isFinite(Date.parse(body.as_of)) || !integer(body.window_days) || body.window_days<1 ||
          body.payment_evidence!=='unavailable' || body.responsibility!=='not_recorded' ||
          !body.capabilities || typeof body.capabilities.prepare_plan!=='boolean' || typeof body.capabilities.review_client!=='boolean' ||
          !body.metrics || !['plans_saved','generation_operations_completed','pdf_metadata_ready'].every(name=>integer(body.metrics[name]))) throw new Error('No se pudo verificar el seguimiento recibido.');
      const seen = new Set();
      const items = body.items.map(row => {
        if (!row || typeof row.id_cliente!=='string' || !row.id_cliente || row.id_cliente.length>36 || seen.has(row.id_cliente) ||
            typeof row.nombre!=='string' || row.nombre.length>200 || !Array.isArray(row.causes) || !row.causes.length ||
            !row.causes.every(name=>Object.hasOwn(causes,name)) || row.responsible!==null ||
            !integer(row.priority) || row.priority<1 || row.priority>4 ||
            (row.last_plan_at!==null && !Number.isFinite(Date.parse(row.last_plan_at))) ||
            (row.elapsed_days!==null && !integer(row.elapsed_days)) ||
            (row.membership_end!==null && (typeof row.membership_end!=='string' || !Number.isFinite(Date.parse(row.membership_end))))) throw new Error('No se pudo verificar el seguimiento recibido.');
        seen.add(row.id_cliente);
        return {id_cliente:row.id_cliente,nombre:row.nombre,causes:[...row.causes],priority:row.priority,
          last_plan_at:row.last_plan_at,elapsed_days:row.elapsed_days,membership_end:row.membership_end,
          prepare:body.capabilities.prepare_plan,review:body.capabilities.review_client};
      });
      return {items, metrics:{...body.metrics},asOf:body.as_of,windowDays:body.window_days,hasMore:body.has_more};
    }
    async function load(limit = state.limit) {
      if (state.busy || state.invalid || !Number.isSafeInteger(limit) || limit<1 || limit>100) return;
      const own = ticket; state.busy=true; state.error='';
      try {
        notify(); if (own!==ticket || state.invalid) return;
        if (!context) { const received=await api.contexto(); if (own!==ticket || state.invalid) return; context=received; }
        await verify(own); check(own);
        const body = await api.seguimiento(context, limit);
        check(own); await verify(own); check(own);
        const next = parse(body,limit); check(own); Object.assign(state,next,{limit}); notify();
      } catch (error) {
        if (own!==ticket || state.invalid) return;
        if (sessionCodes.has(error.code)) { invalidate(); return; }
        try { if(context)check(own); } catch { return; }
        // Retain the previous confirmed rows on a recoverable read failure.
        state.error=error.status===403 ? 'Tu cuenta no tiene permiso para consultar estas estadísticas.' : 'No se pudo actualizar. Los datos anteriores, si aparecen, no se han actualizado. Vuelve a intentar.';
      } finally {
        if (own===ticket && !state.invalid) { state.busy=false; try { notify(); } catch { /* already invalidated */ } }
      }
    }
    async function navigate(id, action, go) {
      const own=ticket;
      try {
        check(own); await verify(own); check(own);
        const row=state.items.find(item=>item.id_cliente===id);
        if (!row || !((action==='prepare' && row.prepare) || (action==='review' && row.review))) return;
        check(own); go(action==='prepare' ? '/generar-plan?id='+encodeURIComponent(id) : '/clientes');
      } catch(error) {
        if(own!==ticket || state.invalid)return;
        if(sessionCodes.has(error.code))invalidate();
        else {state.error='No se pudo confirmar el acceso. Vuelve a consultar antes de abrir el cliente.';notify();}
      }
    }
    return {state,load,navigate,invalidate,check};
  }
  window.DashboardFollowup={create};
  const root=document.getElementById('followup-section'); if(!root)return;
  const status=document.getElementById('followup-status'), error=document.getElementById('followup-error');
  const list=document.getElementById('followup-list'), metrics=document.getElementById('followup-metrics');
  const refresh=document.getElementById('followup-refresh'), limit=document.getElementById('followup-limit');
  let controller;
  function text(tag,value) {const node=document.createElement(tag);node.textContent=value;return node;}
  function render(state) {
    if (controller && !state.invalid && state.asOf) {try{controller.check();}catch{return;}}
    root.setAttribute('aria-busy',String(state.busy)); refresh.disabled=state.busy||state.invalid; limit.disabled=state.busy||state.invalid;
    error.textContent=state.error; error.hidden=!state.error;
    status.textContent=state.invalid ? 'Seguimiento descartado por cambio de sesión.' : state.busy ? 'Consultando seguimiento…' :
      !state.asOf ? 'Seguimiento sin confirmar.' : 'Consulta de '+new Date(state.asOf).toLocaleString('es-MX')+'. Ventana: '+state.windowDays+' días. '+state.items.length+' clientes mostrados.'+
      (state.hasMore ? ' Hay más clientes: esta lista está limitada a '+state.limit+'.' : ' No hay más clientes en estas causas.');
    list.replaceChildren();metrics.replaceChildren();
    if(!state.asOf)return;
    for (const [key,label] of [['plans_saved','Planes guardados'],['generation_operations_completed','Operaciones de generación confirmadas'],['pdf_metadata_ready','PDF con metadatos listos']]) {
      const item=text('p',label+': '+state.metrics[key]);metrics.append(item);
    }
    if(!state.items.length){list.append(text('li','No se encontraron clientes en estas causas. Esto no confirma pagos ni seguimiento realizado.'));return;}
    for(const row of state.items){
      const item=document.createElement('li');item.className='followup-item';
      item.append(text('h3',row.nombre),text('p',row.causes.map(name=>causes[name]).join(' · ')));
      item.append(text('p',row.last_plan_at ? 'Último plan guardado: '+new Date(row.last_plan_at).toLocaleString('es-MX')+' ('+row.elapsed_days+' días transcurridos).' : 'No hay una fecha de plan verificable.'));
      if(row.membership_end)item.append(text('p','Fin de membresía registrado: '+row.membership_end.replace('T',' ')+'. No confirma cobro.'));
      item.append(text('p','Responsable: no asignado; el sistema no registra una asignación.'));
      item.append(text('p',row.causes[0]==='membership_date_passed' ? 'Próximo paso: revisar la fecha administrativa con el cliente.' : 'Próximo paso: revisar la ficha y el historial antes de decidir si hace falta otro plan.'));
      const actions=document.createElement('div');actions.className='followup-actions';
      for(const [action,label,allowed] of [['review','Abrir clientes',row.review],['prepare','Revisar cliente y preparar plan',row.prepare]])if(allowed){
        const button=text('button',label);button.type='button';button.className='btn btn-outline btn-sm';
        button.setAttribute('aria-label',label+' — '+row.nombre);
        button.addEventListener('click',()=>controller.navigate(row.id_cliente,action,url=>location.assign(url)));actions.append(button);
      }
      item.append(actions);list.append(item);
    }
  }
  controller=create(Api.stats,render);
  refresh.addEventListener('click',()=>controller.load(Number(limit.value)));
  window.addEventListener('storage',event=>{if(event.key===null || ['mb_token','mb_refresh_token'].includes(event.key))controller.invalidate();});
  window.addEventListener('metodobase-session-changed',()=>controller.invalidate());
  window.addEventListener('pagehide',()=>controller.invalidate());
  window.addEventListener('pageshow',event=>{if(event.persisted)controller.invalidate();});
  (async()=>{if(window.SessionIdentity)await SessionIdentity.ready;if(!controller.state.invalid)controller.load();})();
})();
