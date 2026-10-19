(() => {
  'use strict';
  const {node,page,uuid,version,date} = VinculosUI;
  const root = document.getElementById('professional-link-page'), client = root.dataset.clientId;
  const items = document.getElementById('professional-link-items'), form = document.getElementById('link-invite-form');
  const email = document.getElementById('link-recipient'), retry = document.getElementById('link-issue-retry');
  const more = document.getElementById('professional-link-more'), controls = document.getElementById('professional-link-controls');
  let records = [], next = null, caps = {}, operation = null, blocked = false;
  function clear() { records=[];next=null;caps={};operation=null;email.value='';items.replaceChildren();form.hidden=true;controls.hidden=true; }
  function applyControls() {
    form.hidden = !caps.issue_invitation || records.some(row=>row.status !== 'revoked');
    email.disabled = !!operation;
    document.getElementById('link-issue').disabled = blocked || !!operation;
    retry.hidden = !operation; retry.disabled = !operation;
    more.hidden = !next;
    items.querySelectorAll('[data-mutation]').forEach(button=>{button.disabled=blocked;});
  }
  const ui = VinculosUI.setup({status:'professional-link-status',error:'professional-link-error',clear,controls:applyControls});
  const selectedPlan = new URLSearchParams(location.search).get('plan_id');
  function validRow(row) {
    return row && uuid(row.link_id) && version(row.version) && ['pending','active','revoked'].includes(row.status) &&
      (row.publication === null || (uuid(row.publication?.id) && version(row.publication.version)));
  }
  async function load(reset=true) {
    const position = reset ? null : next;
    if (!reset && !position) return;
    ui.status('Consultando el estado del vínculo…');
    const data = page(await ui.context.read(context=>Api.vinculos.estado(client,context,position)));
    ui.context.check();
    if (data.client_id !== client || !data.capabilities || !['issue_invitation','rotate_invitation','revoke_link','publish_plan','withdraw_publication'].every(key=>typeof data.capabilities[key]==='boolean') || !data.items.every(validRow) || (position && data.next_after === position)) throw new Error('Invalid client link state');
    ui.context.render(()=>{
      const seen = new Set(reset ? [] : records.map(row=>row.link_id));
      records = reset ? [] : records;
      for (const row of data.items) if (!seen.has(row.link_id)) {seen.add(row.link_id);records.push(row);}
      caps = data.capabilities;next=data.next_after;blocked=false;controls.hidden=false;render();
      ui.status(records.length ? 'Estado consultado. Generar planes no publica ni envía invitaciones automáticamente.' : 'Este cliente aún no tiene un vínculo.');
    });
  }
  function action(button,label,task) {
    button.type='button';button.textContent=label;button.dataset.mutation='true';
    button.addEventListener('click',()=>ui.run(async()=>{
      ui.context.check(); if(blocked)return;
      if(!window.confirm(label+'? Revisa el contexto antes de confirmar.'))return;
      ui.context.check(); blocked=true;
      await task();ui.context.check();await load();
    },true));
  }
  function render() {
    items.replaceChildren();
    for(const row of records) {
      ui.context.check(); const card=node('section',undefined,items);card.className='link-card';
      node('h2',row.status==='active'?'Vínculo aceptado':row.status==='pending'?'Invitación pendiente':'Vínculo revocado',card);
      const status={pending:'Pendiente de aceptación',expired:'Vencida',consumed:'Utilizada',revoked:'Revocada'};
      node('p','Invitación: '+(status[row.invitation_status]||'No disponible')+'. Vigencia: '+date(row.expires_at)+'.',card);
      node('p',row.publication ? 'Plan publicado: '+row.publication.source_plan_id+'. '+(row.status==='active'?'Disponible para esta cuenta destinataria.':'Se mostrará sólo al aceptar el vínculo.') : 'Sin plan publicado.',card);
      if(row.status==='revoked')continue;
      const actions=node('div',undefined,card);actions.className='link-actions';
      if(caps.rotate_invitation && ['pending','expired'].includes(row.invitation_status) && uuid(row.invitation_id) && version(row.invitation_version)) {
        action(node('button',undefined,actions),'Reenviar e invalidar el enlace anterior',async()=>{
          const data=await ui.context.read(context=>Api.vinculos.rotar(client,row.invitation_id,row.invitation_version,context));
          if(data?.status!=='pending'||data.link_id!==row.link_id)throw new Error('Invalid rotation receipt');
          ui.status('Solicitud de reenvío recibida; entrega del correo sin confirmar.');
        });
      }
      if(caps.revoke_link)action(node('button',undefined,actions),'Revocar este vínculo',async()=>{
        const data=await ui.context.read(context=>Api.vinculos.revocar(client,row.link_id,row.version,context));
        if(data?.status!=='revoked'||data.link_id!==row.link_id)throw new Error('Invalid revoke receipt');
        operation=null;email.value='';
      });
      if(caps.publish_plan) {
        const label=node('label','Número del plan a publicar',card);const input=node('input',undefined,label);
        input.type='number';input.min='1';input.max='2147483647';input.step='1';input.inputMode='numeric';input.setAttribute('aria-label','Número del plan a publicar para este vínculo');
        if(selectedPlan && /^\d+$/.test(selectedPlan))input.value=selectedPlan;
        node('p','Selecciona el número de un plan de este cliente desde el historial. Sólo se compartirá al confirmar; reemplazar retira la publicación anterior.',card);
        action(node('button',undefined,card),row.publication?'Reemplazar el plan publicado':'Publicar este plan',async()=>{
          const plan=Number(input.value);
          const data=await ui.context.read(context=>Api.vinculos.publicar(client,row.link_id,plan,row.version,row.publication?.version||0,context));
          if(!uuid(data?.publication_id)||data.link_id!==row.link_id||data.source_plan_id!==plan)throw new Error('Invalid publication receipt');
        });
      }
      if(caps.withdraw_publication && row.publication)action(node('button',undefined,card),'Retirar la publicación',async()=>{
        const data=await ui.context.read(context=>Api.vinculos.retirar(client,row.link_id,row.publication.id,row.publication.version,context));
        if(data?.status!=='withdrawn'||data.publication_id!==row.publication.id)throw new Error('Invalid withdrawal receipt');
      });
    }
    applyControls();ui.context.check();
  }
  async function issue() {
    if(!operation)return;
    blocked=true;applyControls();ui.context.check();
    const data=await ui.context.read(context=>Api.vinculos.emitir(client,operation.email,operation.key,context));
    if(!data||!uuid(data.link_id)||!uuid(data.invitation_id)||data.status!=='pending'||data.delivery_status!=='not_confirmed')throw new Error('Invalid invitation receipt');
    await load();
    ui.status('Solicitud de invitación recibida; entrega del correo sin confirmar. El destinatario debe aceptar el enlace.');
  }
  form.addEventListener('submit',event=>{
    event.preventDefault();if(ui.busy)return;
    return ui.run(async()=>{
      ui.context.check();if(blocked||!caps.issue_invitation||operation||!email.reportValidity())return;
      operation={email:email.value.trim(),key:crypto.randomUUID()};await issue();
    },true);
  });
  retry.addEventListener('click',()=>ui.run(issue,true));
  document.getElementById('professional-link-refresh').addEventListener('click',()=>ui.run(()=>load()));
  more.addEventListener('click',()=>ui.run(()=>load(false)));
  (async()=>{try{await ui.context.start();await ui.run(()=>load());}catch{/* Lifecycle clears the screen and reports a session failure. */}})();
})();
