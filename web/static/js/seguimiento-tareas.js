/* Wire34 state machine. Explicit intentions, no persistence or automatic writes. */
(function(root){
  'use strict';
  const causes=Object.freeze({no_saved_plan:'Sin plan guardado',no_plan_in_window:'Sin plan en la ventana de actividad',plan_date_missing:'Fecha del plan desconocida',membership_date_passed:'Fecha administrativa de membresía pasada'});
  const steps=Object.freeze({review_client_record:'Revisar ficha del cliente',review_plan_history:'Revisar historial de planes',review_membership_date:'Revisar fecha administrativa de membresía'});
  const statuses=Object.freeze({open:'Abierta',completed:'Revisión marcada completada',cancelled:'Cancelada'});
  const reasons=Object.freeze({created_in_error:'Creada por error',no_longer_applicable:'Ya no corresponde',duplicate:'Duplicada'});
  const bad=()=>Object.assign(Error('No se pudo verificar la respuesta de seguimiento.'),{code:'followup_invalid_response'});
  const integer=(v,low=0)=>Number.isSafeInteger(v)&&v>=low&&v<=2147483647;
  const text=(v,max=200)=>typeof v==='string'&&v.length>0&&v.length<=max&&!/[\p{C}]/u.test(v);
  const id=v=>text(v,36)&&v.normalize('NFC')===v;
  const uuid=v=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v);
  const instant=v=>typeof v==='string'&&/^\d{4}-\d\d-\d\dT.+(?:Z|[+-]\d\d:\d\d)$/.test(v)&&Number.isFinite(Date.parse(v));
  const day=v=>typeof v==='string'&&/^\d{4}-\d\d-\d\d$/.test(v)&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
  function shape(v,keys){if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).length!==keys.length||keys.some(k=>!Object.hasOwn(v,k)))throw bad();return v;}
  function flags(v,keys){shape(v,keys);if(keys.some(k=>typeof v[k]!=='boolean'))throw bad();return {...v};}
  function person(v){if(v===null)return null;shape(v,['id','display_name','eligible']);if(!id(v.id)||typeof v.eligible!=='boolean'||(v.eligible?!text(v.display_name):v.display_name!==null))throw bad();return {...v};}
  function client(v){shape(v,['id','display_name']);if(!id(v.id)||!text(v.display_name))throw bad();return {...v};}
  const allowed=(cause,step)=>step==='review_client_record'||step===(cause==='membership_date_passed'?'review_membership_date':'review_plan_history');
  function task(v){
    shape(v,['id','version','client','cause','priority','source','cause_currently_present','next_step','responsible','status','created_at','updated_at','outcome','cancel_reason','capabilities']);
    if(!uuid(v.id)||!integer(v.version,1)||!Object.hasOwn(causes,v.cause)||!integer(v.priority,1)||v.priority>4||!allowed(v.cause,v.next_step)||!Object.hasOwn(statuses,v.status)||typeof v.cause_currently_present!=='boolean'||!instant(v.created_at)||!instant(v.updated_at))throw bad();
    shape(v.source,['observed_at','plan_count','last_plan_at','membership_end']);
    if(!instant(v.source.observed_at)||!integer(v.source.plan_count)||(v.source.last_plan_at!==null&&!instant(v.source.last_plan_at))||(v.source.membership_end!==null&&!Number.isFinite(Date.parse(v.source.membership_end))))throw bad();
    if(v.outcome!==(v.status==='completed'?'review_recorded':null)||(v.status==='cancelled'?!Object.hasOwn(reasons,v.cancel_reason):v.cancel_reason!==null))throw bad();
    const capabilities=flags(v.capabilities,['edit','cancel','history','complete']);
    if(v.status!=='open'&&(capabilities.edit||capabilities.cancel||capabilities.complete))throw bad();
    return {...v,client:client(v.client),source:{...v.source},responsible:person(v.responsible),capabilities};
  }
  function context(v){
    shape(v,['scope','timezone','today','as_of','capabilities','limits']);
    if(!['gym','assigned'].includes(v.scope)||v.timezone!=='America/Mexico_City'||!day(v.today)||!instant(v.as_of))throw bad();
    const caps=flags(v.capabilities,['read_tasks','create_task','manage_tasks','read_assignees','read_metrics','complete_assigned']);
    if(!caps.read_tasks||(v.scope==='assigned'&&(caps.create_task||caps.manage_tasks||caps.read_assignees||caps.read_metrics)))throw bad();
    shape(v.limits,['tasks','history','assignees','report_days']);if(v.limits.tasks!==100||v.limits.history!==50||v.limits.assignees!==50||v.limits.report_days!==62)throw bad();
    return {...v,capabilities:caps,limits:{...v.limits}};
  }
  function page(v,scope){
    shape(v,['items','limit','next_after','scope','as_of']);
    if(!Array.isArray(v.items)||v.items.length>50||v.limit!==50||v.scope!==scope||!instant(v.as_of)||(v.next_after!==null&&(typeof v.next_after!=='string'||!/^[A-Za-z0-9_-]{1,256}$/.test(v.next_after))))throw bad();
    const items=v.items.map(task);if(new Set(items.map(x=>x.id)).size!==items.length)throw bad();return {...v,items};
  }
  function candidates(v,expected){
    shape(v,['client','observed_at','candidates']);const who=client(v.client);
    if(who.id!==expected||!instant(v.observed_at)||!Array.isArray(v.candidates)||v.candidates.length>4)throw bad();
    const seen=new Set(),items=v.candidates.map(c=>{shape(c,['cause','priority','cause_evidence_hash','observed_at','next_steps','open_task']);
      if(!Object.hasOwn(causes,c.cause)||seen.has(c.cause)||!integer(c.priority,1)||c.priority>4||typeof c.cause_evidence_hash!=='string'||!/^[0-9a-f]{64}$/.test(c.cause_evidence_hash)||!instant(c.observed_at)||!Array.isArray(c.next_steps)||c.next_steps.length!==2||new Set(c.next_steps).size!==2||c.next_steps.some(s=>!Object.hasOwn(steps,s)||!allowed(c.cause,s)))throw bad();
      seen.add(c.cause);const open=c.open_task===null?null:task(c.open_task);if(open&&(open.client.id!==expected||open.cause!==c.cause||open.status!=='open'))throw bad();return {...c,next_steps:[...c.next_steps],open_task:open};});
    return {...v,client:who,candidates:items};
  }
  function assignees(v){shape(v,['items','limit','next_after','scope','as_of']);if(v.scope!=='gym'||v.limit!==20||!instant(v.as_of)||!Array.isArray(v.items)||v.items.length>20||(v.next_after!==null&&!id(v.next_after)))throw bad();
    const seen=new Set(),items=v.items.map(p=>{shape(p,['id','display_name','role','eligible']);if(!id(p.id)||!text(p.display_name)||!['owner','admin','nutriologo'].includes(p.role)||p.eligible!==true||seen.has(p.id))throw bad();seen.add(p.id);return {...p};});
    if(v.next_after!==null&&(!items.length||v.next_after!==items[items.length-1].id))throw bad();return {...v,items};}
  function history(v,scope,after){shape(v,['items','limit','next_after','scope','as_of']);if(v.scope!==scope||v.limit!==20||!instant(v.as_of)||!Array.isArray(v.items)||v.items.length>20)throw bad();let last=after;
    const items=v.items.map(e=>{shape(e,['id','version','kind','occurred_at','actor','next_step','responsible','status','outcome','cancel_reason']);if(!uuid(e.id)||!integer(e.version,1)||e.version<=last||!['created','updated','completed','cancelled'].includes(e.kind)||!instant(e.occurred_at)||!Object.hasOwn(steps,e.next_step)||!Object.hasOwn(statuses,e.status)||e.outcome!==(e.status==='completed'?'review_recorded':null)||(e.status==='cancelled'?!Object.hasOwn(reasons,e.cancel_reason):e.cancel_reason!==null))throw bad();last=e.version;return {...e,actor:person(e.actor),responsible:person(e.responsible)};});
    if(v.next_after!==null&&(!items.length||v.next_after!==last))throw bad();return {...v,items};}
  function metrics(v){shape(v,['as_of','timezone','scope','range','state_now','event_period','sources','coverage','meaning']);shape(v.range,['from','through','inclusive']);shape(v.sources,['state','events']);shape(v.state_now,['open','unassigned']);shape(v.event_period,['created','completed_declarations','cancelled','assignment_changes']);
    if(!instant(v.as_of)||v.timezone!=='America/Mexico_City'||v.scope!=='gym'||!day(v.range.from)||!day(v.range.through)||v.range.inclusive!==true||v.range.through<v.range.from||(Date.parse(v.range.through)-Date.parse(v.range.from))/86400000>=62||v.sources.state!=='followup_tasks'||v.sources.events!=='followup_task_events'||v.coverage!=='current_active_clients_only'||v.meaning!=='actor_declarations_not_contact_delivery_payment_or_retention'||[...Object.values(v.state_now),...Object.values(v.event_period)].some(n=>!integer(n)))throw bad();return JSON.parse(JSON.stringify(v));}
  function ack(v,intention,command=null){
    const replay=v?.operation?.replayed===true;shape(v,replay?['ack','operation','task','read_required']:['ack','operation','task']);shape(v.operation,['id','request_key','replayed','applied_version','occurred_at']);
    if(v.ack!==true||!uuid(v.operation.id)||!uuid(v.operation.request_key)||typeof v.operation.replayed!=='boolean'||!integer(v.operation.applied_version,1)||!instant(v.operation.occurred_at))throw bad();
    const version=intention.kind==='created'?1:intention.version+1;if(v.operation.applied_version!==version)throw bad();
    if(replay){if(v.task!==null||v.read_required!==true)throw bad();return {operation:{...v.operation},task:null};}
    const row=task(v.task);if(row.version!==version||(intention.id&&row.id!==intention.id)||row.client.id!==intention.client||row.cause!==intention.cause||row.status!==({completed:'completed',cancelled:'cancelled'}[intention.kind]||'open')||row.updated_at!==v.operation.occurred_at)throw bad();
    if(command&&(['created','updated'].includes(intention.kind)?row.next_step!==command.next_step||(row.responsible?.id||null)!==command.assignee_id:intention.kind==='completed'?row.outcome!==command.outcome:row.cancel_reason!==command.reason))throw bad();
    return {operation:{...v.operation},task:row};
  }
  function create({api,onView=()=>{},clientId=null}){
    let handle=null,epoch=0,dead=false,operation=null,intention=null,needsConsultation=false;
    const state={phase:'idle',busy:false,message:'Consulta el estado para comenzar.',context:null,items:[],next:null,status:'open',asOf:null,detail:null,consultTask:null,candidates:null,assignees:[],assigneesNext:null,history:null,metrics:null,form:null};
    const view=()=>JSON.parse(JSON.stringify(state));
    function clearOperation(){if(operation)api.discard(operation);operation=null;intention=null;}
    function clear(){clearOperation();needsConsultation=false;state.context=null;state.items=[];state.next=null;state.detail=null;state.consultTask=null;state.candidates=null;state.assignees=[];state.assigneesNext=null;state.history=null;state.metrics=null;state.form=null;state.asOf=null;}
    function invalidate(){if(dead)return;dead=true;epoch++;handle=null;clear();state.busy=false;state.phase='invalidated';state.message='La sesión cambió o dejó de ser verificable. Abre esta vista desde tu cuenta.';onView(view());}
    function check(ticket=epoch){if(dead||ticket!==epoch||!handle)throw Object.assign(Error('Changed'),{code:'session_changed'});try{api.check(handle);}catch(e){invalidate();throw e;}}
    function emit(){if(handle&&!dead)check();onView(view());if(handle&&!dead)check();}
    async function verify(ticket){check(ticket);await api.verify(handle);check(ticket);}
    function fail(error,ticket,writing=false){if(ticket!==epoch||dead)return false;if(['session_changed','session_expired','session_storage_error','followup_identity_unavailable'].includes(error.code)||error.status===401){invalidate();return false;}
      if(writing){state.form=null;state.detail=null;state.phase=error.status===409?'conflict':'uncertain';state.message=error.status===409?'El servidor rechazó esta intención por un cambio de estado. Consulta antes de preparar otra acción.':'No pudimos confirmar el resultado. Puede haberse guardado. No repetiremos la operación; consulta el estado explícitamente.';}
      else{state.phase=error.status===403?'denied':'error';state.form=null;state.detail=null;state.message=error.status===403?'Tu cuenta no tiene permiso para esta consulta.':'No se pudo actualizar. Si hay datos anteriores, conservan su fecha y sus acciones están bloqueadas hasta una consulta válida.';}
      return false;
    }
    async function read(kind,arg=null,more=false){if(dead||state.busy)return false;const ticket=epoch,keepForm=kind==='assignees'&&state.phase==='form';state.busy=true;state.message='Consultando el estado autorizado…';
      try{emit();if(!handle){const session=await api.session();if(ticket!==epoch||dead)return false;handle=session.handle;check(ticket);}await verify(ticket);
        const ctx=context(await api.contexto(handle));check(ticket);
        let value;if(kind==='list'){const status=arg||state.status;value=page(await api.tasks(handle,{status,after:more?state.next:null}),ctx.scope);await verify(ticket);clearOperation();needsConsultation=false;state.context=ctx;state.items=value.items;state.next=value.next_after;state.status=status;state.asOf=value.as_of;state.detail=null;state.candidates=null;state.history=null;state.form=null;}
        else if(kind==='detail'){value=task(await api.task(arg,handle));await verify(ticket);clearOperation();needsConsultation=false;state.context=ctx;state.detail=value;state.consultTask=value.id;state.candidates=null;state.history=null;state.form=null;}
        else if(kind==='candidates'){if(!ctx.capabilities.create_task)throw Object.assign(bad(),{status:403});value=candidates(await api.candidates(clientId,handle),clientId);await verify(ticket);clearOperation();needsConsultation=false;state.context=ctx;state.candidates=value;state.detail=null;state.history=null;state.form=null;}
        else if(kind==='assignees'){if(!ctx.capabilities.read_assignees)throw Object.assign(bad(),{status:403});value=assignees(await api.assignees(handle,more?state.assigneesNext:null));await verify(ticket);state.context=ctx;state.assignees=value.items;state.assigneesNext=value.next_after;}
        else if(kind==='history'){if(!state.detail?.capabilities.history)throw bad();const selected=state.detail.id;value=history(await api.history(selected,handle,{afterVersion:more?state.history?.next_after||0:0}),ctx.scope,more?state.history?.next_after||0:0);await verify(ticket);if(state.detail?.id!==selected)throw bad();state.history=value;state.context=ctx;}
        else if(kind==='metrics'){if(!ctx.capabilities.read_metrics)throw Object.assign(bad(),{status:403});value=metrics(await api.metrics(handle,arg));await verify(ticket);state.metrics=value;state.context=ctx;}
        else throw bad();check(ticket);state.phase=keepForm?'form':needsConsultation?'consult_required':'ready';state.message=needsConsultation?'La consulta auxiliar no confirma el estado de la operación anterior. Consulta sus tareas o causas antes de preparar otra acción.':'Estado consultado. Cada acción requiere una confirmación explícita.';return true;
      }catch(error){return fail(error,ticket);}finally{if(ticket===epoch&&!dead){state.busy=false;try{emit();}catch{/* invalidated */}}}
    }
    function prepare(kind,index=null){if(dead||needsConsultation||state.busy||state.phase!=='ready')return false;try{check();let row=null;
      if(kind==='created'){if(!state.context?.capabilities.create_task||!state.candidates)return false;row=state.candidates.candidates[index];if(!row||row.open_task)return false;}
      else{row=state.detail;if(!row||!row.capabilities[{updated:'edit',completed:'complete',cancelled:'cancel'}[kind]])return false;}
      clearOperation();intention={kind,id:kind==='created'?null:row.id,version:kind==='created'?0:row.version,client:kind==='created'?state.candidates.client.id:row.client.id,cause:row.cause,evidence:kind==='created'?row.cause_evidence_hash:null};
      state.consultTask=intention.id;state.form={kind,client:kind==='created'?state.candidates.client.display_name:row.client.display_name,cause:row.cause,nextStep:kind==='created'?row.next_steps[0]:row.next_step,steps:kind==='created'?[...row.next_steps]:Object.keys(steps).filter(s=>allowed(row.cause,s)),assignee:kind==='created'?null:row.responsible?.id||null,version:intention.version};state.phase='form';state.message='Revisa y confirma la intención antes de guardarla.';emit();return true;
      }catch(error){return fail(error,epoch);}}
    function cancel(){if(dead||state.busy)return false;clearOperation();state.form=null;state.phase=state.context?'ready':'idle';state.message='Preparación cancelada. No se envió ninguna acción.';emit();return true;}
    async function submit(values){if(dead||state.busy||state.phase!=='form'||!intention||values?.confirm!==true)return false;const ticket=epoch,own={...intention};let dispatched=false;state.busy=true;
      try{check(ticket);const body=own.kind==='created'?{client_id:own.client,cause:own.cause,cause_evidence_hash:own.evidence,next_step:values.next_step,assignee_id:values.assignee_id,expected_active_task_id:null,confirm:true}:own.kind==='updated'?{expected_version:own.version,next_step:values.next_step,assignee_id:values.assignee_id,confirm:true}:own.kind==='completed'?{expected_version:own.version,outcome:'review_recorded',confirm:true}:{expected_version:own.version,reason:values.reason,confirm:true};
        state.message='Verificando esta intención antes de enviarla…';emit();check(ticket);
        await verify(ticket);check(ticket);operation=api.prepare(own.kind,own.id,body,handle);state.phase='saving';state.message='Guardando esta intención una sola vez…';emit();check(ticket);
        needsConsultation=true;dispatched=true;const result=ack(await api.send(operation),own,body);check(ticket);state.form=null;state.history=null;state.items=[];state.next=null;state.candidates=null;state.metrics=null;
        state.detail=result.task;state.consultTask=result.task?.id||own.id;state.phase='saved';state.message=result.task?'El servidor confirmó esta operación y su versión. Consulta para preparar otra acción.':'El servidor confirmó una operación ya registrada. Su respuesta no describe el estado actual: consulta explícitamente.';clearOperation();return true;
      }catch(error){if(!dispatched&&ticket===epoch&&!dead&&error.code==='followup_invalid_input'){if(operation)api.discard(operation);operation=null;state.phase='form';state.message='La intención no se envió. Revisa los campos y vuelve a confirmar.';return false;}return fail(error,ticket,true);}finally{if(ticket===epoch&&!dead){state.busy=false;try{emit();}catch{/* invalidated */}}}
    }
    return Object.freeze({view,check,invalidate,load:status=>read('list',status),more:()=>state.next?read('list',state.status,true):false,detail:id=>read('detail',id),candidates:()=>read('candidates'),assignees:(more=false)=>read('assignees',null,more),history:(more=false)=>read('history',null,more),metrics:range=>read('metrics',range),prepare,cancel,submit});
  }
  root.SeguimientoTareas=Object.freeze({create,task,context,candidates,page,history,metrics,ack,causes,steps,statuses,reasons});
})(typeof window==='undefined'?globalThis:window);
