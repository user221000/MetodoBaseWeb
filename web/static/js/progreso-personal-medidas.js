/* Explicit personal measurements. The server owns source authorization and every CAS. */
(() => {
  'use strict';
  function mount(host){
    const get=id=>document.getElementById(id),data=ProgresoDatos,dto=ProgresoRespuestas,view=ProgresoVista,form=get('measurement-form'),select=get('progress-profile');
    let bootstrap=null,profiles=[],selected=null,rows=[],next=null,query=null,operation=null,editing=null,reconciled=null,pendingRetire=null,retryPayload=null;
    const pending=()=>pendingRetire!==null||operation&&['saving','unconfirmed','missing','conflict'].includes(operation.status);
    function clear(){operation?.invalidate();operation=null;bootstrap=null;profiles=[];selected=null;rows=[];next=null;query=null;editing=null;reconciled=null;pendingRetire=null;retryPayload=null;form.reset();get('measurement-query').reset();get('measurement-table').replaceChildren();get('measurement-trend').replaceChildren();get('measurement-reconciliation').replaceChildren();get('measurement-status').textContent='';get('measurement-query-status').textContent='';while(select.options.length>1)select.remove(1);select.value='';get('progress-measurements').hidden=true;}
    host.onClear(clear);
    function controls(){
      if(!host.active)return;get('measurement-more').hidden=next===null;get('measurement-more').disabled=host.busy||pending();
      get('measurement-fields').disabled=host.busy||!selected?.canRecord||bootstrap?.capabilities.recordMeasurements!==true||!!pendingRetire||!!operation&&operation.status!=='idle';
      select.disabled=host.busy||!!pending();get('measurement-cancel').hidden=!editing||!!pending();
      get('measurement-readback').hidden=!pendingRetire&&!(operation&&['unconfirmed','missing','conflict'].includes(operation.status));
      get('measurement-retry').hidden=operation?.status!=='missing'||retryPayload===null;
      get('measurement-metric').disabled=host.busy||!selected;get('measurement-query').querySelector('fieldset').disabled=host.busy||!selected;
      get('measurement-new').hidden=operation?.status!=='confirmed';get('measurement-review').hidden=operation?.status!=='conflict'||!reconciled?.canEdit;
      get('measurement-legend').textContent=editing?'Corregir el registro consultado':'Registrar una medida declarada';
    }
    host.onControls(controls);
    function setProfiles(items){profiles=items;if(selected)selected=profiles.find(row=>row.id===selected.id)||{...selected,canRecord:false};host.render(()=>{const current=selected?.id||'';while(select.options.length>1)select.remove(1);const shown=selected&&!profiles.some(row=>row.id===selected.id)?[...profiles,selected]:profiles;for(const profile of shown){const option=view.node('option',profile.displayName+(profile.canRecord?'':' · sólo consulta o revisión'));option.value=profile.id;select.append(option);}select.value=current;});}
    function configure(value){bootstrap=value;host.render(()=>{get('progress-measurements').hidden=false;get('measurement-date').max=value.today;get('measurement-from').max=value.today;get('measurement-through').max=value.today;});setProfiles(value.profiles.items);}
    const options=(profile=selected)=>({today:bootstrap.today,profile:profile.id,canMutate:bootstrap.capabilities.recordMeasurements===true&&profile.canRecord});
    function display(){if(!selected)return;host.render(()=>{view.measurements(get('measurement-table'),rows,{caption:'Medidas de '+selected.displayName+(query?' · '+query.from+' a '+query.through:''),withdraw:row=>host.action(()=>retire(row)),edit:row=>host.action(()=>edit(row))});get('measurement-empty').hidden=rows.length!==0;view.trend(get('measurement-trend'),rows,get('measurement-metric').value);controls();});}
    async function load(reset=true){
      host.check();if(!selected)return;const profile=selected,position=reset?null:next;if(!reset&&position===null)return;
      const range=reset?data.queryRange(get('measurement-from').value,get('measurement-through').value,bootstrap.today):query;
      host.render(()=>{get('measurement-query-status').textContent='Consultando medidas de este perfil y periodo…';});
      let result;try{result=await host.read(context=>Api.progreso.mediciones(profile.id,context,{range,cursor:position}),raw=>dto.measurements(raw,options(profile)));host.check();}
      catch(error){host.check();host.render(()=>{if([403,404].includes(error.status)||['progress_scope_changed','progress_source_requires_review','progress_response_unavailable'].includes(error.code)){rows=[];next=null;get('measurement-table').replaceChildren();get('measurement-trend').replaceChildren();get('measurement-empty').hidden=true;}get('measurement-query-status').textContent=query?'No se confirmó la nueva consulta. La tabla conservada corresponde a '+query.from+' a '+query.through+'.':'No se confirmó una consulta de medidas. No se mostrarán cifras sustitutas.';});throw error;}
      if(selected!==profile)throw Object.assign(new Error('changed'),{code:'progress_context_changed'});if(position!==null&&result.nextAfter===position)throw Object.assign(new Error('cursor'),{code:'progress_response_unavailable'});
      host.render(()=>{const seen=new Set(reset?[]:rows.map(row=>row.key));rows=reset?[]:rows;for(const row of result.rows)if(!seen.has(row.key)){seen.add(row.key);rows.push(row);}next=result.nextAfter;query={from:result.fromDate,through:result.throughDate};get('measurement-from').value=result.fromDate;get('measurement-through').value=result.throughDate;get('measurement-query-status').textContent='Consulta confirmada: '+result.fromDate+' a '+result.throughDate+'.';});display();
    }
    function newOperation(profile,fixedKey=null){
      operation?.invalidate();reconciled=null;retryPayload=null;
      operation=ProgresoMedicion.create({check:host.check,...(fixedKey?{uuid:()=>fixedKey}:{}),
        write:(key,payload)=>host.read(context=>Api.progreso.guardarMedicion(key,payload,context),raw=>{const value=dto.measurement(raw,options(profile));if(value.recordKey!==key)throw Object.assign(new Error('key'),{code:'progress_response_unavailable'});return value;}),
        read:key=>host.read(async context=>{try{return await Api.progreso.medicion(key,context);}catch(error){if(error.status===404&&error.code==='progress_source_unavailable')return null;throw error;}},raw=>{if(raw===null)return null;const value=dto.measurement(raw,options(profile));if(value.recordKey!==key)throw Object.assign(new Error('key'),{code:'progress_response_unavailable'});return value;}),
        matches:(record,payload,key)=>record.recordKey===key&&record.sourceProfileId===payload.source_profile_id&&record.sourceKind==='self_reported'&&!record.withdrawn&&record.measuredOn===payload.measured_on&&record.version===payload.expected_version+1&&Object.keys(data.units).every(metric=>(record.values[metric]??null)===(payload.values[metric]??null)),
        onState(value){host.render(()=>{const labels={idle:'Prepara una medida. No se guardará hasta que confirmes.',saving:'Guardando este registro…',unconfirmed:'Resultado no confirmado. Mantén esta página y consulta este mismo registro; no se reenviará automáticamente.',missing:'No se encontró el registro en la consulta actual. Puedes confirmar de nuevo la misma intención y clave; no se preparará otra.',conflict:'El registro actual difiere de la intención. Revisa los datos antes de preparar una corrección.',confirmed:'Se confirmó el estado de este registro. La tabla mantiene su periodo de consulta.'};get('measurement-status').textContent=labels[value.status]||'';reconciled=value.record;if(value.record)view.measurements(get('measurement-reconciliation'),[value.record],{caption:'Estado consultado de este registro'});else get('measurement-reconciliation').replaceChildren();controls();});},
      });
    }
    async function save(){
      host.check();if(!selected||!bootstrap.capabilities.recordMeasurements||!selected.canRecord)return;const profile=selected;
      const input=data.measurement({source_profile_id:profile.id,measured_on:get('measurement-date').value,values:{peso_kg:get('measurement-weight').value,grasa_corporal_pct:get('measurement-fat').value,masa_magra_kg:get('measurement-lean').value}},bootstrap.today),payload={expected_version:editing?.version||0,...input};
      if(!operation)newOperation(profile,editing?.recordKey||null);retryPayload=JSON.parse(JSON.stringify(payload));await operation.submit(payload);host.check();await load(true);
    }
    async function edit(row){
      host.check();if(pending())throw Object.assign(new Error('pending'),{code:'progress_operation_pending'});const profile=selected;
      const current=await host.read(context=>Api.progreso.medicion(row.recordKey,context),raw=>dto.measurement(raw,options(profile)));host.check();if(!current.canEdit||current.recordKey!==row.recordKey)throw Object.assign(new Error('source'),{code:'progress_source_unavailable'});
      host.render(()=>{editing=current;newOperation(profile,current.recordKey);get('measurement-date').value=current.measuredOn;get('measurement-weight').value=current.values.peso_kg??'';get('measurement-fat').value=current.values.grasa_corporal_pct??'';get('measurement-lean').value=current.values.masa_magra_kg??'';get('measurement-status').textContent='Revisa esta corrección y confírmala. Aún no se ha guardado.';controls();get('measurement-date').focus();});
    }
    async function retire(row){
      host.check();if(pending())throw Object.assign(new Error('pending'),{code:'progress_operation_pending'});const profile=selected;pendingRetire={key:row.recordKey,version:row.version,profile};host.render(()=>{get('measurement-status').textContent='Solicitando retirar este registro…';controls();});
      const result=await host.read(context=>Api.progreso.retirarMedicion(row.recordKey,row.version,context),raw=>dto.measurement(raw,options(profile)));host.check();if(result.recordKey!==row.recordKey||!result.withdrawn||result.version!==row.version+1)throw Object.assign(new Error('ack'),{code:'progress_unconfirmed'});
      pendingRetire=null;host.render(()=>{get('measurement-status').textContent='Retirada confirmada. Esto no afirma eliminación ni un plazo de retención.';view.measurements(get('measurement-reconciliation'),[result],{caption:'Registro retirado'});});await load(true);
    }
    async function readBack(){
      if(pendingRetire){const pending=pendingRetire,result=await host.read(context=>Api.progreso.medicion(pending.key,context),raw=>dto.measurement(raw,options(pending.profile)));host.check();if(result.recordKey!==pending.key)throw Object.assign(new Error('key'),{code:'progress_response_unavailable'});pendingRetire=null;host.render(()=>{view.measurements(get('measurement-reconciliation'),[result],{caption:'Estado actual tras consultar la retirada'});get('measurement-status').textContent=result.withdrawn?'El estado actual indica que el registro está retirado.':'El registro sigue disponible. Revisa su versión actual antes de confirmar otra retirada.';});await load(true);return;}
      if(!operation)return;await operation.readBack();host.check();if(operation.status==='confirmed')await load(true);
    }
    form.addEventListener('submit',event=>{event.preventDefault();host.action(save);});get('measurement-query').addEventListener('submit',event=>{event.preventDefault();host.action(()=>load(true));});get('measurement-more').addEventListener('click',()=>host.action(()=>load(false)));get('measurement-readback').addEventListener('click',()=>host.action(readBack));
    select.addEventListener('change',()=>host.action(async()=>{if(pending()){host.render(()=>{select.value=selected?.id||'';});throw Object.assign(new Error('pending'),{code:'progress_operation_pending'});}const profile=profiles.find(row=>row.id===select.value)||null;operation?.invalidate();operation=null;editing=null;selected=profile;rows=[];next=null;query=null;host.render(()=>{form.reset();select.value=profile?.id||'';get('measurement-reconciliation').replaceChildren();get('measurement-table').replaceChildren();get('measurement-trend').replaceChildren();get('measurement-status').textContent='';controls();});if(!profile)return;if(!/^[0-9a-f-]{36}$/.test(profile.id))throw Object.assign(new Error('legacy'),{code:'progress_source_requires_review'});await load(true);}));
    get('measurement-new').addEventListener('click',()=>host.action(async()=>{operation?.newIntent();operation?.invalidate();operation=null;editing=null;reconciled=null;host.render(()=>{form.reset();get('measurement-reconciliation').replaceChildren();get('measurement-status').textContent='Prepara una nueva medida y confirma sus datos.';controls();get('measurement-date').focus();});}));
    get('measurement-review').addEventListener('click',()=>host.action(async()=>{if(operation?.status!=='conflict'||!reconciled)return;const current=reconciled;operation.invalidate();operation=null;await edit(current);}));
    get('measurement-cancel').addEventListener('click',()=>host.action(async()=>{if(pending())return;operation?.invalidate();operation=null;editing=null;host.render(()=>{form.reset();get('measurement-status').textContent='Borrador descartado. No se ha enviado una corrección.';controls();});}));
    get('measurement-metric').addEventListener('change',()=>host.action(async()=>{display();}));
    get('measurement-retry').addEventListener('click',()=>host.action(async()=>{if(operation?.status!=='missing'||retryPayload===null)return;await operation.submit(retryPayload);host.check();await load(true);}));
    return Object.freeze({configure,setProfiles,controls,load,clear});
  }
  window.ProgresoMedidasUI=Object.freeze({mount});
})();
