/* Own preferences and declared queue state. No scheduler, delivery or debt inference. */
(function(root){
 'use strict';
 const purposes=['account_period_end','confirmed_payment_issue'];
 const labels={account_period_end:'Fin del periodo de mi cuenta',confirmed_payment_issue:'Incidencia de pago confirmada'};
 const states={pending:'Pendiente',leased:'Reservada para revisión',sending:'En curso; no se puede retirar el envío en vuelo',retry_wait:'Espera técnica',accepted:'Aceptada por proveedor; entrega no acreditada',suppressed:'Detenida',failed:'Fallida',uncertain:'Resultado incierto; no reenviar'};
 const invalid=()=>Object.assign(Error('No se pudo validar el estado de recordatorios.'),{code:'notification_invalid_response'});
 const copy=value=>JSON.parse(JSON.stringify(value));
 const object=value=>value&&typeof value==='object'&&!Array.isArray(value);
 const uuid=value=>typeof value==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value);
 const counter=(value,zero=false)=>Number.isSafeInteger(value)&&value>=(zero?0:1)&&value<=2147483647;
 const time=value=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}T.+(?:Z|[+-]\d\d:\d\d)$/.test(value)&&Number.isFinite(Date.parse(value));
 function preference(value,context){
  if(!object(value)||value.context!==context||!purposes.includes(value.purpose)||value.channel!=='email'||!counter(value.version,true)||typeof value.enabled!=='boolean'||![24,72,168].includes(value.interval_hours)||(value.version===0?(value.id!==null||value.enabled||value.updated_at!==null):(!uuid(value.id)||!time(value.updated_at))))throw invalid();return copy(value);
 }
 function preferenceList(value,context){
  if(!object(value)||!Array.isArray(value.items)||value.items.length!==2)throw invalid();const rows=value.items.map(row=>preference(row,context));if(new Set(rows.map(row=>row.purpose)).size!==2)throw invalid();return rows;
 }
 function contextDTO(value,context){
  if(!object(value)||value.context!==context||value.delivery_enabled!==false||value.timezone!=='America/Mexico_City'||!Array.isArray(value.purposes)||value.purposes.length!==2||!purposes.every(p=>value.purposes.includes(p))||!Array.isArray(value.channels)||value.channels.length!==1||value.channels[0]!=='email'||value.frequency?.minimum_hours!==24||value.frequency?.maximum_handoffs_7d!==3)throw invalid();return copy(value);
 }
 function candidates(value,context){
  if(!object(value)||value.context!==context||!['unknown','verified'].includes(value.source_state)||!time(value.observed_at)||!Array.isArray(value.candidates)||value.candidates.length!==2)throw invalid();
  const rows=value.candidates.map(row=>{
   if(!object(row)||!purposes.includes(row.purpose)||typeof row.eligible!=='boolean'||row.preference?.purpose!==row.purpose)throw invalid();preference(row.preference,context);
   if(value.source_state==='unknown'?(row.eligible||row.fact_id!==null||row.source_hash!==null):(!uuid(row.fact_id)||typeof row.source_hash!=='string'||!/^[0-9a-f]{64}$/.test(row.source_hash)))throw invalid();return copy(row);
  });if(new Set(rows.map(row=>row.purpose)).size!==2)throw invalid();return{...copy(value),candidates:rows};
 }
 function outbox(value,context){
  if(!object(value)||!uuid(value.id)||value.context!==context||!purposes.includes(value.purpose)||value.channel!=='email'||!Object.hasOwn(states,value.state)||!counter(value.version)||!counter(value.attempt_count,true)||!time(value.created_at)||!time(value.updated_at)||!object(value.capabilities)||typeof value.capabilities.cancel!=='boolean'||value.capabilities.cancel!==['pending','leased','retry_wait','uncertain'].includes(value.state))throw invalid();return copy(value);
 }
 function outboxPage(value,context,after=null){
  if(!object(value)||!Array.isArray(value.items)||value.items.length>20||(value.next_after!==null&&!uuid(value.next_after)))throw invalid();
  const items=value.items.map(row=>outbox(row,context));let previous=after;for(const row of items){if(previous!==null&&row.id<=previous)throw invalid();previous=row.id;}
  if(value.next_after!==null&&(!items.length||value.next_after!==items.at(-1).id))throw invalid();return{items,next_after:value.next_after};
 }
 function metrics(value){
  if(!object(value)||value.timezone!=='America/Mexico_City'||value.attribution!=='observed_facts_only_no_email_causality'||!object(value.outbox_states)||Object.keys(value.outbox_states).some(key=>!Object.hasOwn(states,key)||!counter(value.outbox_states[key],true))||!counter(value.verified_paid_period_advances,true))throw invalid();
  for(const day of[value.from,value.through])if(typeof day!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(day)||!Number.isFinite(Date.parse(day+'T00:00:00Z'))||new Date(day+'T00:00:00Z').toISOString().slice(0,10)!==day)throw invalid();
  const span=(Date.parse(value.through)-Date.parse(value.from))/86400000;if(span<0||span>=62)throw invalid();return copy(value);
 }
 function acknowledgement(reply,kind,context){
  if(!object(reply)||typeof reply.replayed!=='boolean'||typeof reply.read_required!=='boolean'||(reply.replayed&&!reply.read_required))throw invalid();
  if(reply.replayed&&kind!=='preference'&&kind!=='observe'){if(!uuid(reply.operation_result?.id))throw invalid();}
  else if(kind==='preference')preference(reply.preference,context);
  else if(kind==='observe'){if(reply.observed!==true||!uuid(reply.fact_id)||reply.read_required!==true)throw invalid();}
  else outbox(reply.outbox,context);
 }
 function message(error,writing=false){
  if(writing&&(!error.status||error.status>=500))return 'Resultado incierto. Puede haberse aplicado. Conservamos esta intención en memoria; no repetimos ni consultamos automáticamente.';
  return({notification_context_forbidden:'Esta cuenta no tiene autorización para este contexto. No se habilitaron recordatorios.',notification_conflict:'La versión o la intención cambió. Consulta el estado actual antes de preparar otra operación.',notification_source_changed:'La fuente o el contacto cambió. Consulta el estado; no se presume una incidencia de pago.',notification_frequency_limited:'Se alcanzó una barrera de frecuencia. No se registró una confirmación; consulta el estado antes de continuar.',notification_backlog_limited:'Hay demasiadas intenciones abiertas. Consulta la lista antes de continuar.',notification_disabled:'La consulta del proveedor está desactivada. No se acreditó una causa de recordatorio.',notification_unavailable:'El recurso no está disponible. Consulta el estado actual.',notification_invalid_input:'Revisa la selección, la confirmación y las fechas.',notification_invalid_response:'El servidor no devolvió un estado válido. No se ha confirmado ningún cambio.'})[error.code]||'No pudimos consultar o confirmar esta operación. Consulta el estado actual para continuar.';
 }
 function create({api,context,onView=()=>{}}){
  if(!['gym','personal'].includes(context))throw invalid();let handle=null,pending=null,epoch=0,dead=false;
  const state={phase:'idle',busy:false,context,preferences:[],candidates:null,outbox:{items:[],next_after:null},metrics:null,queriedAt:null,message:'Consulta tus preferencias y el estado registrado.',retry:false};
  function view(){return copy(state);}
  function check(ticket=epoch){if(dead||ticket!==epoch||!handle)throw Object.assign(Error('La sesión cambió.'),{code:'session_changed'});api.check(handle);}
  function emit(){onView(view());}
  function invalidate(){if(dead)return;dead=true;epoch++;if(pending)api.discard(pending.operation);pending=null;handle=null;state.preferences=[];state.candidates=null;state.outbox={items:[],next_after:null};state.metrics=null;state.queriedAt=null;state.busy=false;state.retry=false;state.phase='invalidated';state.message='La sesión cambió. Los datos y las intenciones de esta página se descartaron. Abre la página desde tu cuenta.';emit();}
  function fail(error,ticket,writing=false){
   if(dead||ticket!==epoch)return;if(['session_changed','session_expired','session_storage_error'].includes(error.code)||error.status===401){invalidate();return;}
   state.phase=writing?'unconfirmed':'error';if(writing&&pending)pending.retryable=!error.status||error.status>=500||error.status===429;state.retry=!!pending?.retryable;state.message=message(error,writing);if(error.status===403){state.preferences=[];state.candidates=null;state.outbox={items:[],next_after:null};state.metrics=null;state.queriedAt=null;state.retry=false;}
  }
  async function load(){
   if(dead||state.busy)return false;const ticket=++epoch;state.busy=true;state.retry=false;state.phase='loading';state.message='Consultando el estado registrado…';emit();
   try{
    if(!handle){const session=await api.session();if(dead||ticket!==epoch)return false;handle=session.handle;}
    check(ticket);await api.verify(handle);check(ticket);
    const values=await Promise.allSettled([api.context(context,handle),api.preferences(context,handle),api.candidates(context,handle),api.outbox(context,handle),api.metrics(context,handle)]);check(ticket);
    const failed=values.find(value=>value.status==='rejected');if(failed)throw failed.reason;
    const [scope,prefs,source,list,counts]=values.map(value=>value.value);contextDTO(scope,context);
    const next={preferences:preferenceList(prefs,context),candidates:candidates(source,context),outbox:outboxPage(list,context),metrics:metrics(counts)};
    await api.verify(handle);check(ticket);if(pending)api.discard(pending.operation);pending=null;Object.assign(state,next);state.queriedAt=new Date().toISOString();state.phase='ready';state.message='Estado consultado. Los envíos están desactivados. Una preferencia activada no confirma autorización de envío ni entrega.';return true;
   }catch(error){fail(error,ticket);return false;}finally{if(!dead&&ticket===epoch){state.busy=false;emit();}}
  }
  async function send(){
   if(dead||state.busy||!pending)return false;const ticket=epoch;state.busy=true;state.retry=false;state.phase='writing';state.message='Enviando esta intención una sola vez…';emit();
   try{check(ticket);const reply=await api.send(pending.operation);check(ticket);acknowledgement(reply,pending.kind,context);api.discard(pending.operation);pending=null;state.phase='read_required';state.message='El servidor reconoció la operación. Consulta el estado actual para ver su resultado. No se envió un correo desde esta pantalla.';return true;}
   catch(error){fail(error,ticket,true);return false;}finally{if(!dead&&ticket===epoch){state.busy=false;emit();}}
  }
  function start(kind,target,body){if(dead||state.busy||state.phase!=='ready'||pending)throw invalid();check();pending={kind,operation:api.operation(kind,context,target,body,handle)};return send();}
  function savePreference(purpose,enabled,interval,confirmed){
   const pref=state.preferences.find(row=>row.purpose===purpose);if(!pref||confirmed!==true||typeof enabled!=='boolean'||![24,72,168].includes(interval)||(!enabled&&pref.version===0))throw Object.assign(invalid(),{code:'notification_invalid_input'});
   return start('preference',purpose,{expected_version:pref.version,enabled,interval_hours:interval,confirm:true});
  }
  function queue(purpose,confirmed){
   const row=state.candidates?.candidates.find(value=>value.purpose===purpose),pref=state.preferences.find(value=>value.purpose===purpose);
   if(confirmed!==true||state.candidates?.source_state!=='verified'||row?.eligible!==true||!pref?.enabled||row.preference.id!==pref.id||row.preference.version!==pref.version)throw Object.assign(invalid(),{code:'notification_invalid_input'});
   return start('queue',null,{purpose,preference_id:pref.id,expected_preference_version:pref.version,fact_id:row.fact_id,source_hash:row.source_hash,confirm:true});
  }
  function cancel(id,confirmed){const row=state.outbox.items.find(value=>value.id===id);if(confirmed!==true||!row?.capabilities.cancel)throw Object.assign(invalid(),{code:'notification_invalid_input'});return start('cancel',id,{expected_version:row.version,confirm:true});}
  async function page(){
   if(dead||state.busy||state.phase!=='ready'||!state.outbox.next_after)return false;const ticket=epoch,after=state.outbox.next_after;state.busy=true;emit();
   try{check(ticket);const value=await api.outbox(context,handle,after);check(ticket);state.outbox=outboxPage(value,context,after);state.message='Página consultada. No se recorrieron más páginas automáticamente.';return true;}catch(error){fail(error,ticket);return false;}finally{if(!dead&&ticket===epoch){state.busy=false;emit();}}
  }
  async function readMetrics(range){
   if(dead||state.busy||state.phase!=='ready')return false;const ticket=epoch;state.busy=true;emit();
   try{check(ticket);const value=await api.metrics(context,handle,range);check(ticket);state.metrics=metrics(value);state.message='Métricas consultadas: hechos observados, sin atribución al correo.';return true;}catch(error){fail(error,ticket);return false;}finally{if(!dead&&ticket===epoch){state.busy=false;emit();}}
  }
  return Object.freeze({view,load,invalidate,savePreference,queue,cancel,page,readMetrics,observe(confirmed){if(confirmed!==true)throw Object.assign(invalid(),{code:'notification_invalid_input'});return start('observe',null,{});},retry(){if(!state.retry)return false;return send();}});
 }
 function mount(element,{api=Api.notifications36}={}){
  const get=id=>element.querySelector('[data-notification-'+id+']'),context=element.dataset.notificationContext;let controller;
  const text=(tag,value,parent)=>{const node=document.createElement(tag);node.textContent=value;parent.append(node);return node;};
  function action(label,run,parent){const button=text('button',label,parent);button.type='button';button.className='notification-button';button.addEventListener('click',()=>attempt(run));return button;}
  function attempt(run){try{Promise.resolve(run()).catch(showError);}catch(error){showError(error);}}
  function showError(error){get('status').textContent=message(error);get('status').setAttribute('role','alert');get('status').focus();}
  function render(state){
   const hadFocus=element.contains(document.activeElement),writable=state.phase==='ready'&&!state.busy;get('status').textContent=state.message;get('status').setAttribute('role',['error','unconfirmed','invalidated'].includes(state.phase)?'alert':'status');get('refresh').disabled=state.busy||state.phase==='invalidated';get('retry').hidden=!state.retry;get('retry').disabled=state.busy;get('time').textContent=state.queriedAt?'Última consulta: '+new Date(state.queriedAt).toLocaleString('es-MX'):'Sin consulta confirmada';
   get('preferences').replaceChildren();for(const pref of state.preferences){
    const form=document.createElement('form');form.className='notification-card';get('preferences').append(form);text('h3',labels[pref.purpose],form);text('p','Declaración guardada: '+(pref.enabled?'activada':'desactivada')+'. Versión '+pref.version+'.',form);
    const enabledLabel=text('label','',form),enabled=document.createElement('input');enabled.type='checkbox';enabled.checked=pref.enabled;enabledLabel.append(enabled,document.createTextNode(' Quiero registrar esta preferencia de correo para mi cuenta.'));
    const intervalLabel=text('label','Intervalo mínimo elegido',form),interval=document.createElement('select');intervalLabel.append(interval);for(const value of[24,72,168]){const option=text('option',value===24?'24 horas':value===72?'72 horas':'7 días',interval);option.value=String(value);}interval.value=String(pref.interval_hours);
    const confirmLabel=text('label','',form),confirm=document.createElement('input');confirm.type='checkbox';confirmLabel.append(confirm,document.createTextNode(' Confirmo guardar esta selección.'));
    const save=text('button','Guardar preferencia',form);save.type='submit';save.className='notification-button';for(const input of[enabled,interval,confirm,save])input.disabled=!writable;save.disabled=!writable||(!pref.enabled&&pref.version===0);enabled.addEventListener('change',()=>{save.disabled=!writable||(!enabled.checked&&pref.version===0);confirm.checked=false;});interval.addEventListener('change',()=>{confirm.checked=false;});
    form.addEventListener('submit',event=>{event.preventDefault();attempt(()=>controller.savePreference(pref.purpose,enabled.checked,Number(interval.value),confirm.checked));});
   }
   get('source').textContent=state.candidates?.source_state==='verified'?'Hay una observación verificada. La elegibilidad depende de cada propósito y se revalida en el servidor.':'Fuente desconocida o no disponible. No acredita una incidencia de pago ni una deuda.';
   get('queue').replaceChildren();for(const purpose of purposes){const candidate=state.candidates?.candidates.find(row=>row.purpose===purpose),pref=state.preferences.find(row=>row.purpose===purpose),section=document.createElement('section');get('queue').append(section);text('h3',labels[purpose],section);text('p',candidate?.eligible?'La fuente observada cumple esta causa; la preferencia y el contacto se revalidarán.':'No se acreditó esta causa para registrar una intención.',section);const label=text('label','',section),confirm=document.createElement('input');confirm.type='checkbox';label.append(confirm,document.createTextNode(' Confirmo registrar una intención; no es un envío.'));const button=action('Registrar intención',()=>controller.queue(purpose,confirm.checked),section);confirm.disabled=button.disabled=!writable||!candidate?.eligible||!pref?.enabled;}
   get('observe').disabled=!writable;get('observe-confirm').disabled=!writable;get('outbox').replaceChildren();if(!state.outbox.items.length)text('li',state.queriedAt?'No hay intenciones en esta página consultada.':'La lista aún no está disponible.',get('outbox'));
   for(const row of state.outbox.items){const item=document.createElement('li');item.className='notification-card';get('outbox').append(item);text('h3',labels[row.purpose],item);text('p',states[row.state],item);text('p','Intentos declarados: '+row.attempt_count+'. Actualizada: '+new Date(row.updated_at).toLocaleString('es-MX')+'.',item);if(row.capabilities.cancel){const label=text('label','',item),confirm=document.createElement('input');confirm.type='checkbox';label.append(confirm,document.createTextNode(' Confirmo detener esta intención.'));const button=action('Detener intención',()=>controller.cancel(row.id,confirm.checked),item);confirm.disabled=button.disabled=!writable;}}
   get('next').hidden=!state.outbox.next_after;get('next').disabled=!writable;get('metrics').replaceChildren();if(state.metrics){text('p','Periodo '+state.metrics.from+' a '+state.metrics.through+' · '+state.metrics.timezone,get('metrics'));text('p','Avances entre periodos pagados verificados: '+state.metrics.verified_paid_period_advances+'.',get('metrics'));for(const [key,value]of Object.entries(state.metrics.outbox_states))text('p',states[key]+': '+value,get('metrics'));}
   for(const input of get('metrics-form').querySelectorAll('input,button'))input.disabled=!writable;
   if(state.phase==='invalidated'){get('observe-confirm').checked=false;get('from').value='';get('through').value='';}
   if(hadFocus&&!element.contains(document.activeElement))get('status').focus();
  }
  controller=create({api,context,onView:render});get('refresh').addEventListener('click',()=>controller.load());get('retry').addEventListener('click',()=>controller.retry());get('observe').addEventListener('click',()=>attempt(()=>controller.observe(get('observe-confirm').checked)));get('next').addEventListener('click',()=>controller.page());get('metrics-form').addEventListener('submit',event=>{event.preventDefault();attempt(()=>controller.readMetrics({from:get('from').value,through:get('through').value}));});
  const invalidate=()=>controller.invalidate();for(const event of['metodobase-session-changed','pagehide'])root.addEventListener(event,invalidate);root.addEventListener('pageshow',event=>{if(event.persisted)invalidate();});root.addEventListener('storage',event=>{if(event.key===null||event.key==='mb_session_epoch')invalidate();});render(controller.view());controller.load();return controller;
 }
 root.Notifications36=Object.freeze({create,mount,preference,preferenceList,contextDTO,candidates,outboxPage,metrics,acknowledgement,labels,states});
 if(typeof document!=='undefined'){const start=()=>{const element=document.querySelector('[data-notifications36]');if(element)mount(element);};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();}
})(typeof window==='undefined'?globalThis:window);
