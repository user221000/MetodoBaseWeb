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
          body.payment_evidence!=='unavailable' || !['not_recorded','per_cause_tasks'].includes(body.responsibility) ||
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
        let tasks=null;
        if(body.responsibility==='per_cause_tasks'){
          if(body.task_coverage!=='current_open_tasks_by_cause'||!Array.isArray(row.per_cause_tasks)||row.per_cause_tasks.length>4||!Array.isArray(row.cause_candidates)||row.cause_candidates.length>4)throw new Error('No se pudo verificar el seguimiento recibido.');
          const used=new Set();tasks=row.per_cause_tasks.map(value=>{
            if(!value||typeof value.id!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value.id)||!integer(value.version)||value.version<1||value.version>2147483647||!Object.hasOwn(causes,value.cause)||used.has(value.cause)||value.status!=='open'||!['review_client_record','review_plan_history','review_membership_date'].includes(value.next_step)||!value.capabilities||!['edit','cancel','complete','history'].every(k=>typeof value.capabilities[k]==='boolean'))throw new Error('No se pudo verificar el seguimiento recibido.');
            used.add(value.cause);const person=value.responsible;
            if(person!==null&&(!person||typeof person.id!=='string'||!person.id||person.id.length>36||typeof person.eligible!=='boolean'||(person.eligible?(typeof person.display_name!=='string'||!person.display_name||person.display_name.length>200):person.display_name!==null)))throw new Error('No se pudo verificar el seguimiento recibido.');
            return {id:value.id,cause:value.cause,next_step:value.next_step,responsible:person===null?null:{id:person.id,eligible:person.eligible,display_name:person.display_name}};
          });
          const candidates=new Set();for(const value of row.cause_candidates){if(!value||!row.causes.includes(value.cause)||candidates.has(value.cause)||!integer(value.priority)||value.priority<1||value.priority>4||typeof value.cause_evidence_hash!=='string'||!/^[0-9a-f]{64}$/.test(value.cause_evidence_hash)||!Number.isFinite(Date.parse(value.observed_at))||!Array.isArray(value.next_steps)||value.next_steps.length!==2||!value.next_steps.every(s=>s==='review_client_record'||s===(value.cause==='membership_date_passed'?'review_membership_date':'review_plan_history')))throw new Error('No se pudo verificar el seguimiento recibido.');candidates.add(value.cause);}
        }
        return {id_cliente:row.id_cliente,nombre:row.nombre,causes:[...row.causes],priority:row.priority,
          last_plan_at:row.last_plan_at,elapsed_days:row.elapsed_days,membership_end:row.membership_end,
          prepare:body.capabilities.prepare_plan,review:body.capabilities.review_client,tasks};
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
        if (!row || !((action==='prepare' && row.prepare) || (action==='review' && row.review) || (action==='tasks' && row.tasks!==null))) return;
        check(own); go(action==='tasks'?'/clientes/'+encodeURIComponent(id)+'/seguimiento':action==='prepare' ? '/generar-plan?id='+encodeURIComponent(id) : '/clientes');
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
      if(row.tasks===null)item.append(text('p','Responsabilidad: no disponible en esta respuesta.'));
      else for(const cause of row.causes){const task=row.tasks.find(t=>t.cause===cause);item.append(text('p',causes[cause]+': '+(task?'Responsable: '+(task.responsible===null?'Sin asignar':task.responsible.eligible?task.responsible.display_name:'Ya no disponible')+'. Próximo paso: '+({review_client_record:'revisar ficha',review_plan_history:'revisar historial de planes',review_membership_date:'revisar fecha administrativa'})[task.next_step]+'.':'Sin tarea abierta registrada en esta consulta.')));}
      item.append(text('p',row.causes[0]==='membership_date_passed' ? 'Próximo paso: revisar la fecha administrativa con el cliente.' : 'Próximo paso: revisar la ficha y el historial antes de decidir si hace falta otro plan.'));
      const actions=document.createElement('div');actions.className='followup-actions';
      for(const [action,label,allowed] of [['review','Abrir clientes',row.review],['prepare','Revisar cliente y preparar plan',row.prepare]])if(allowed){
        const button=text('button',label);button.type='button';button.className='btn btn-outline btn-sm';
        button.setAttribute('aria-label',label+' — '+row.nombre);
        button.addEventListener('click',()=>controller.navigate(row.id_cliente,action,url=>location.assign(url)));actions.append(button);
      }
      if(row.tasks!==null){const button=text('button','Consultar causas y preparar tarea');button.type='button';button.className='btn btn-outline btn-sm';button.setAttribute('aria-label','Consultar tareas de '+row.nombre);button.addEventListener('click',()=>controller.navigate(row.id_cliente,'tasks',url=>location.assign(url)));actions.append(button);}
      item.append(actions);list.append(item);
    }
  }
  controller=create(Api.stats,render);
  refresh.addEventListener('click',async()=>{
    const restore=document.activeElement===refresh;
    let moved=false;
    const focusChanged=event=>{if(event.target!==refresh && event.target!==document.body)moved=true;};
    const userMoved=()=>{moved=true;};
    // Native disabled prevents a second request but also blurs the button.
    // Restore only the initiating keyboard position, preserving a deliberate
    // focus change or session invalidation while the read was pending.
    const pending=controller.load(Number(limit.value));
    document.addEventListener('focusin',focusChanged);
    document.addEventListener('pointerdown',userMoved,true);
    document.addEventListener('keydown',userMoved,true);
    try {await pending;} finally {
      document.removeEventListener('focusin',focusChanged);
      document.removeEventListener('pointerdown',userMoved,true);
      document.removeEventListener('keydown',userMoved,true);
      if(restore && !moved && !controller.state.invalid && refresh.isConnected && !refresh.disabled &&
          (document.activeElement===document.body || document.activeElement===null))refresh.focus({preventScroll:true});
    }
  });
  window.addEventListener('storage',event=>{if(event.key===null || ['mb_token','mb_refresh_token'].includes(event.key))controller.invalidate();});
  window.addEventListener('metodobase-session-changed',()=>controller.invalidate());
  window.addEventListener('pagehide',()=>controller.invalidate());
  window.addEventListener('pageshow',event=>{if(event.persisted)controller.invalidate();});
  (async()=>{if(window.SessionIdentity)await SessionIdentity.ready;if(!controller.state.invalid)controller.load();})();
})();
