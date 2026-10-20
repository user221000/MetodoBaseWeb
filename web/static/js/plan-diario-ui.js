/* Bounded source draft. Existing transports own authentication; no direct fetch/Storage. */
(() => {
  'use strict';
  const names={desayuno:'Desayuno',almuerzo:'Almuerzo',comida:'Comida',cena:'Cena'};
  const groups={proteinas:'Proteínas',carbohidratos:'Carbohidratos',grasas:'Grasas'};
  const number=value=>new Intl.NumberFormat('es-MX',{maximumSignificantDigits:15}).format(value);
  const node=(tag,value,parent)=>{const el=document.createElement(tag);if(value!==undefined)el.textContent=value;if(parent)parent.append(el);return el;};
  const foodText=food=>food.label.replace(/_/g,' ')+' · '+number(food.grams)+' g'+(food.equivalence?' · '+food.equivalence:'');
  function renderMenu(root,source,check){
    check();root.replaceChildren();
    for(const meal of PlanDayData.menu(source.plan)){
      check();const section=node('section',undefined,root);section.className='plan-menu-meal';node('h3',names[meal.name],section);
      if(!meal.available){node('p',meal.reason,section);continue;}
      if(meal.kind==='fixed'){const list=node('ul',undefined,section);for(const food of meal.foods)node('li',foodText(food),list);}
      else{node('p','Opciones incluidas en la fuente. Consultarlas no registra consumo ni selecciona una combinación.',section);
        for(const [group,label]of Object.entries(groups)){node('h4',label,section);const list=node('ul',undefined,section);
          for(const food of meal.groups[group])node('li',foodText(food),list);if(!meal.groups[group].length)node('li','Sin opciones registradas en este grupo.',list);}
        if(meal.vegetables.length){node('h4','Vegetales incluidos',section);const list=node('ul',undefined,section);for(const food of meal.vegetables)node('li',foodText(food),list);}
      }
    }check();
  }
  function mount(options){
    const root=options.root,find=id=>root.querySelector('#'+id),context=options.context;
    let source=null,menu=[],chosen={},known=[],epoch=0,invalid=false,busy=false;
    const status=find('shopping-status'),items=find('shopping-items'),build=find('shopping-build');
    const recorded=find('shopping-recorded-items'),recordedStatus=find('shopping-recorded-status');
    function check(ticket=epoch){if(invalid||ticket!==epoch)throw new Error('El contexto cambió. Vuelve a consultar la fuente.');context.check();}
    function controls(){
      if(!invalid){try{check();}catch{invalidate();return;}}
      build.disabled=invalid||busy||!source;find('shopping-start').disabled=invalid||busy;find('shopping-end').disabled=invalid||busy;
      root.setAttribute('aria-busy',String(busy));
      for(const el of root.querySelectorAll('#shopping-meals input'))el.disabled=invalid||busy;
    }
    function invalidate(){const first=!invalid;invalid=true;if(first)epoch++;source=null;chosen={};menu=[];busy=false;
      for(const id of ['shopping-meals','shopping-items','shopping-recorded-items'])find(id).replaceChildren();
      for(const id of ['shopping-start','shopping-end'])find(id).value='';
      find('plan-source-label').textContent='Fuente descartada por cambio de contexto.';recordedStatus.textContent='';status.textContent='La sesión o la fuente cambió. Vuelve a abrir esta página.';controls();if(first)options.onInvalidated?.();}
    function discard(){check();items.replaceChildren();status.textContent='Borrador sin preparar. Tus cambios no registran consumo.';}
    function selectors(){
      check();const target=find('shopping-meals');target.replaceChildren();
      for(const meal of menu){
        check();
        const box=node('fieldset',undefined,target);node('legend',names[meal.name],box);
        if(!meal.available){node('p',meal.reason,box);continue;}
        const select=(food,group,index,fixed=false)=>{
          const label=node('label',undefined,box);label.className='plan-option';const input=node('input',undefined,label);
          input.type=fixed||group==='vegetales'?'checkbox':'radio';input.name='shopping-'+meal.name+'-'+group;
          input.dataset.meal=meal.name;input.dataset.group=group;input.value=String(index);
          input.checked=fixed?chosen[meal.name]?.include_fixed_menu===true:group==='vegetales'?chosen[meal.name]?.include_vegetables===true:chosen[meal.name]?.[group]===index;
          node('span',fixed?'Elegir el menú fijo completo: '+meal.foods.map(foodText).join(' · '):group==='vegetales'?'Incluir los vegetales mostrados: '+meal.vegetables.map(foodText).join(' · '):foodText(food),label);
          input.addEventListener('change',()=>{try{check();const selection=chosen[meal.name]||={};
            if(fixed)selection.include_fixed_menu=input.checked;else if(group==='vegetales')selection.include_vegetables=input.checked;else selection[group]=index;
            discard();}catch{invalidate();}});
        };
        if(meal.kind==='fixed'){select(null,'fixed',0,true);continue;}
        for(const [group,label]of Object.entries(groups)){node('p',label,box);meal.groups[group].forEach((food,index)=>select(food,group,index));}
        if(meal.vegetables.length)select(null,'vegetales',0);
      }check();
    }
    function setSource(value,today){
      if(invalid)return;check();source=value;chosen={};items.replaceChildren();recorded.replaceChildren();menu=PlanDayData.menu(value.plan,known);
      find('plan-source-label').textContent=value.label;selectors();
      if(today){find('shopping-start').value=today;find('shopping-end').value=today;}
      status.textContent='Fuente consultada. Elige explícitamente las porciones y el periodo; nada está registrado.';controls();
    }
    async function current(){
      const ticket=epoch;check(ticket);let latest;
      try{latest=await options.readSource();check(ticket);}catch(error){
        if([403,404].includes(error.status)){invalidate();options.onSourceUnavailable?.(error);}throw error;
      }
      if(!latest||!source||latest.key!==source.key){chosen={};items.replaceChildren();find('shopping-meals').replaceChildren();source=null;menu=[];controls();options.onSourceUnavailable?.();throw new Error('La fuente cambió o ya no está disponible. Vuelve a consultar el plan; el borrador se descartó.');}
      return ticket;
    }
    function drawList(target,rows){target.replaceChildren();for(const row of rows)node('li',row.label.replace(/_/g,' ')+' · '+number(row.grams)+' '+row.unit,target);if(!rows.length)node('li','No hay cantidades seleccionadas o registradas para sumar.',target);}
    build.addEventListener('click',async()=>{
      if(busy||invalid)return;busy=true;controls();const ticket=epoch;if(invalid)return;
      try{await current();check(ticket);const result=PlanDayData.shopping(PlanDayData.select(menu,chosen),find('shopping-start').value,find('shopping-end').value);
        check(ticket);drawList(items,result.items);status.textContent='Borrador de compra, '+result.start+' al '+result.end+': '+result.days+' días repitiendo sólo esta selección. No se registró consumo.';check(ticket);
      }catch(error){if(ticket===epoch&&!invalid){try{check(ticket);}catch{invalidate();return;}status.textContent=error.message;status.focus();}}
      finally{if(ticket===epoch&&!invalid){busy=false;controls();}}
    });
    for(const id of ['shopping-start','shopping-end'])find(id).addEventListener('change',()=>{try{discard();recorded.replaceChildren();recordedStatus.textContent='';}catch{invalidate();}});
    find('shopping-recorded-section').hidden=!options.readRecorded;
    find('shopping-read-recorded').addEventListener('click',async()=>{
      if(busy||invalid||!options.readRecorded)return;const ticket=epoch;busy=true;controls();if(invalid)return;
      try{const start=find('shopping-start').value,end=find('shopping-end').value;PlanDayData.shopping([],start,end);
        const calendar=await options.readRecorded(start,end);check(ticket);if(!calendar)throw new Error('No se pudo consultar el consumo registrado.');
        const value=PlanDayData.recorded(calendar);check(ticket);drawList(recorded,value.items);recordedStatus.textContent=value.recordedMeals+' comidas registradas en '+start+' al '+end+'. El completado no cambia sus cantidades.';
      }catch(error){if(ticket===epoch&&!invalid){try{check(ticket);}catch{invalidate();return;}recordedStatus.textContent='No se pudo consultar. No se presenta una lista vacía como éxito.';}}
      finally{if(ticket===epoch&&!invalid){busy=false;controls();}}
    });
    window.addEventListener('metodobase-session-changed',()=>invalidate());window.addEventListener('pagehide',()=>invalidate());
    window.addEventListener('storage',event=>{if(event.key===null||['mb_token','mb_refresh_token','mb_session_epoch'].includes(event.key))invalidate();});
    return{setSource,invalidate,check,current,
      setCatalog(ids){check();known=ids;if(source){menu=PlanDayData.menu(source.plan,known);if(items.children.length){items.replaceChildren();status.textContent='Catálogo confirmado. Vuelve a preparar el borrador con tus porciones elegidas.';}}},
      selection(meal){check();return JSON.parse(JSON.stringify(chosen[meal]||{}));},
      get source(){return source;},get active(){return !invalid;}};
  }
  window.PlanDayUI=Object.freeze({renderMenu,mount,number,node});
})();
