/* Recipient snapshot to its existing personal diary; never a professional profile adoption. */
(() => {
  'use strict';
  function mount(options){
    const root=options.root,el=id=>root.querySelector('#'+id),scope=options.scope,shopping=options.shopping;
    const message=el('publication-diary-status'),save=el('publication-diary-save'),date=el('publication-diary-day');
    const records=el('publication-diary-records'),retry=el('publication-diary-retry'),discard=el('publication-diary-discard');
    let active=true,context=null,controller=null,epoch=0,operationBusy=false,lastState=null;
    const changed=()=>Object.assign(new Error('El contexto cambió. Vuelve a consultar la publicación.'),{code:'session_changed'});
    function scopeCheck(ticket=epoch){if(!active||ticket!==epoch)throw changed();scope.check();}
    function check(ticket=epoch){scopeCheck(ticket);if(!context)throw changed();Api.usuario.validarContexto(context);}
    function invalidate(){if(!active)return;active=false;epoch++;context=null;date.value='';records.replaceChildren();message.textContent='El registro se descartó por cambio de contexto.';
      for(const control of root.querySelectorAll('input,button,select'))control.disabled=true;controller?.invalidate(changed());}
    const personal={check,invalidate,
      async read(task){const ticket=epoch;check(ticket);const value=await scope.read(()=>task(context));check(ticket);
        await scope.read(()=>Api.usuario.verificarContexto(context));check(ticket);return value;},
      async verify(){const ticket=epoch;check(ticket);await scope.read(()=>Api.usuario.verificarContexto(context));check(ticket);}};
    function text(tag,value,parent){return PlanDayUI.node(tag,value,parent);}
    function render(day){
      check();records.replaceChildren();
      text('p','Consumo personal del '+day.local_date+': '+PlanDayUI.number(day.totals.kcal)+' kcal registradas. El completado es una marca distinta.',records);
      if(!Object.keys(day.meals).length)text('p','Sin comidas registradas para esta fecha.',records);
      for(const [name,meal]of Object.entries(day.meals)){
        const section=text('section',undefined,records);text('h4',name+(meal.completed?' · completada':' · registrada'),section);
        text('p','Fuente: '+(meal.source_context?'publicación del '+meal.source_context.published_at:'plan personal #'+meal.source_plan_id)+' · registro '+meal.recorded_at,section);
        const list=text('ul',undefined,section);for(const food of meal.foods)text('li',food.food_id.replace(/_/g,' ')+' · '+PlanDayUI.number(food.grams)+' g',list);
        const remove=text('button','Eliminar este consumo personal',section);remove.type='button';remove.disabled=!controller.writable;remove.dataset.removeConsumed='true';
        remove.addEventListener('click',async()=>{try{check();if(controller.writable&&window.confirm('¿Eliminar únicamente este consumo personal de '+name+'?'))await controller.save({operation:'remove_meal',meal:name});}catch{invalidate();}});
      }
    }
    function controls(update){
      date.disabled=!active||operationBusy||update.busy||['loading','review','invalidated'].includes(update.state);
      save.disabled=!active||operationBusy||!controller?.writable;
      el('publication-diary-meal').disabled=!active||operationBusy||update.busy||['loading','review','invalidated'].includes(update.state);
      for(const button of records.querySelectorAll('[data-remove-consumed]'))button.disabled=!active||!controller?.writable;
      el('publication-diary-reload').disabled=!active||operationBusy||update.busy||update.state==='loading';
      retry.hidden=!update.hasDraft;retry.disabled=!update.canRetry;discard.hidden=!update.hasDraft;discard.disabled=update.busy;
    }
    function state(update){
      lastState=update;message.textContent=update.message;date.value=update.selected||'';if(update.today)date.max=update.today;controls(update);
      if(['error','conflict','unconfirmed','review','invalidated'].includes(update.state))message.focus();
    }
    controller=PersonalDiary.create({personal,onView:render,onClear:()=>records.replaceChildren(),onState:state});
    el('publication-consumption').hidden=false;
    if(options.canRecord!==true){
      message.textContent='Este vínculo permite leer el plan, pero no crea un espacio personal de diario. El registro requiere un contexto personal confirmado por el servidor.';
      for(const control of el('publication-consumption').querySelectorAll('input,button,select'))control.disabled=true;
      return{invalidate};
    }
    async function sourceCheck(){const ticket=epoch;check(ticket);await shopping.current();check(ticket);shopping.check();}
    save.addEventListener('click',async()=>{
      if(!active||operationBusy||!controller.writable)return;
      operationBusy=true;if(lastState)controls(lastState);
      try{
        check();const selectedDay=controller.selected,selectedVersion=controller.day.version,meal=el('publication-diary-meal').value,selections=shopping.selection(meal);
        await sourceCheck();check();const source=shopping.source;
        if(controller.selected!==selectedDay||controller.day?.version!==selectedVersion)throw new Error('El día cambió. Revisa el diario antes de registrar esta selección.');
        message.textContent='Solicitando el registro explícito de esta selección; aún no está confirmado.';
        await controller.save({operation:'publication_meal',source_kind:'publication',link_id:source.link_id,
          publication_id:source.publication_id,expected_link_version:source.link_version,
          expected_publication_version:source.publication_version,meal,selections});
      }catch(error){if(active){try{check();}catch{invalidate();return;}message.textContent=error.message;message.focus();}}
      finally{operationBusy=false;if(active){try{check();if(lastState)controls(lastState);}catch{invalidate();}}}
    });
    date.addEventListener('change',async()=>{
      try{check();}catch{invalidate();return;}
      try{PersonalDiary.dateParts(date.value);}catch{date.value=controller.selected||'';message.textContent='Elige una fecha válida. No se cambió el día ni se registró consumo.';message.focus();return;}
      await controller.select(date.value);
    });
    el('publication-diary-reload').addEventListener('click',()=>{try{check();return controller.reconsult();}catch{invalidate();}});
    discard.addEventListener('click',()=>{try{check();controller.discard();}catch{invalidate();}});
    retry.addEventListener('click',async()=>{try{await sourceCheck();check();await controller.retry();}catch(error){if(active){message.textContent=error.message;message.focus();}}});
    for(const control of el('publication-consumption').querySelectorAll('input,button,select'))control.disabled=true;
    (async()=>{const ticket=epoch;try{
      const value=await scope.read(()=>Api.usuario.contexto());scopeCheck(ticket);context=value;check(ticket);await controller.bootstrap();check(ticket);
    }catch(error){if(active){try{scopeCheck(ticket);}catch{invalidate();return;}message.textContent='No se pudo confirmar el diario personal. Vuelve a consultar la publicación; no se registró consumo.';
      for(const control of el('publication-consumption').querySelectorAll('input,button,select'))control.disabled=true;}}})();
    return{invalidate};
  }
  window.PublicationConsumption=Object.freeze({mount});
})();
