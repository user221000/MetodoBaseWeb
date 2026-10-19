(() => {
  'use strict';
  const {node,page,uuid,version,date} = VinculosUI;
  const list = document.getElementById('member-links-list'), panel = document.getElementById('member-publication');
  const summary = document.getElementById('member-publication-summary'), meals = document.getElementById('member-publication-meals');
  const pdf = document.getElementById('member-publication-pdf'), leave = document.getElementById('member-link-leave');
  const more = document.getElementById('member-links-more');
  let records=[],next=null,selected=null,scope=null,result=null,mutationUnconfirmed=false;
  function clearPublication() {result=null;panel.hidden=true;summary.replaceChildren();meals.replaceChildren();pdf.hidden=true;leave.hidden=true;ui.releaseDownloads();}
  function clear() {scope?.invalidate();scope=null;records=[];next=null;selected=null;list.replaceChildren();clearPublication();more.hidden=true;document.getElementById('member-home').hidden=true;}
  function controls() {more.hidden=!next;pdf.hidden=!result?.publication||result.capabilities?.download_published_pdf!==true;leave.hidden=!selected||selected.capabilities?.revoke_link!==true;leave.disabled=mutationUnconfirmed;list.querySelectorAll('[data-mutation]').forEach(button=>{button.disabled=mutationUnconfirmed;});}
  const ui=VinculosUI.setup({status:'member-links-status',error:'member-links-error',clear,controls});
  function rowValid(row) {return row&&uuid(row.link_id)&&version(row.version)&&row.status==='active'&&row.context?.kind==='gym_member'&&row.context.link_id===row.link_id&&typeof row.context.gym_name==='string'&&typeof row.context.client_display_name==='string'&&row.capabilities?.read_published_plan===true;}
  async function load(reset=true) {
    const position=reset?null:next;if(!reset&&!position)return;
    if(reset){scope?.invalidate();scope=null;selected=null;clearPublication();}
    ui.status('Consultando tus vínculos…');
    const data=page(await ui.context.read(context=>Api.vinculos.listar(context,position)));
    if(!data.items.every(rowValid)||(position&&data.next_after===position))throw new Error('Invalid member links');
    ui.context.render(()=>{
      const seen=new Set(reset?[]:records.map(row=>row.link_id));records=reset?[]:records;
      for(const row of data.items)if(!seen.has(row.link_id)){seen.add(row.link_id);records.push(row);}
      next=data.next_after;mutationUnconfirmed=false;list.replaceChildren();
      if(!records.length)node('p','Aún no tienes vínculos activos disponibles. Abre el enlace de invitación del correo para revisar uno nuevo.',list);
      for(const row of records){
        ui.context.check();const card=node('section',undefined,list);card.className='link-card';
        node('h3',row.context.gym_name,card);node('p','Destinatario: '+row.context.client_display_name,card);
        const button=node('button','Consultar plan de este vínculo',card);button.type='button';
        button.addEventListener('click',()=>ui.run(()=>select(row)));
        if(row.capabilities.revoke_link===true){const unlink=node('button','Desvincularme de este vínculo',card);unlink.type='button';unlink.dataset.mutation='true';unlink.addEventListener('click',()=>ui.run(()=>removeLink(row),true));}
      }
      controls();ui.status('Vínculos consultados. Elige uno para ver su publicación vigente.');
    });
  }
  function food(parent,name,grams,equivalence) {
    if(typeof name!=='string'||name.length>200||!Number.isFinite(grams)||grams<=0)throw new Error('Invalid published food');
    node('li',name+' · '+grams+' g'+(typeof equivalence==='string'&&equivalence?' · '+equivalence:''),parent);
  }
  function renderMenu(plan) {
    if(!plan||typeof plan!=='object')throw new Error('Missing published menu');
    const names={desayuno:'Desayuno',almuerzo:'Almuerzo',comida:'Comida',cena:'Cena'};
    for(const [key,label]of Object.entries(names)){
      scope.check();const meal=plan[key];if(!meal||typeof meal!=='object')throw new Error('Invalid published meal');
      const section=node('section',undefined,meals);node('h3',label,section);
      if(meal.tipo_plan==='opciones'){
        node('p','Opciones publicadas por el profesional. Consultarlas no registra consumo.',section);
        for(const [group,label]of [['proteinas','Proteínas'],['carbohidratos','Carbohidratos'],['grasas','Grasas']]){
          const options=meal[group]?.opciones;if(!Array.isArray(options)||options.length>256)throw new Error('Invalid published options');
          node('h4',label,section);const ul=node('ul',undefined,section);for(const value of options)food(ul,value.alimento,value.gramos,value.equivalencia);
        }
        if(!Array.isArray(meal.vegetales)||meal.vegetales.length>32)throw new Error('Invalid published vegetables');
        if(meal.vegetales.length){node('h4','Vegetales',section);const ul=node('ul',undefined,section);for(const value of meal.vegetales)food(ul,value.alimento,value.gramos,value.equivalencia);}
      }else{
        const values=meal.alimentos;if(!values||typeof values!=='object'||Array.isArray(values)||!Object.keys(values).length||Object.keys(values).length>256)throw new Error('Invalid fixed published meal');
        const ul=node('ul',undefined,section);for(const [name,grams]of Object.entries(values))food(ul,name,grams);
      }
    }
  }
  async function select(row) {
    ui.context.check();scope?.invalidate();selected=row;clearPublication();scope=ui.context.scope(clearPublication);
    ui.status('Consultando el plan de este vínculo…');
    const data=await scope.read(context=>Api.vinculos.plan(row.link_id,context));scope.check();
    if(!data||data.context?.kind!=='gym_member'||data.context.link_id!==row.link_id||data.link?.status!=='active'||!version(data.link.version)||!data.capabilities)throw new Error('Invalid publication context');
    if(data.publication!==null&&(!uuid(data.publication?.id)||!version(data.publication.version)||data.publication.plan_schema_version!==1))throw new Error('Invalid publication');
    try{scope.render(()=>{
      result=data;selected={...row,version:data.link.version,capabilities:data.capabilities};
      node('h3',data.context.gym_name,summary);node('p','Destinatario: '+data.context.client_display_name,summary);
      if(data.publication){
        node('p','Publicado: '+date(data.publication.published_at)+'. Este contenido pertenece a esta publicación concreta.',summary);
        const target=data.publication.meta?.kcal_objetivo;
        if(target!==null&&target!==undefined&&Number.isFinite(target))node('p','Objetivo del plan: '+target+' kcal. No representa consumo registrado.',summary);
        renderMenu(data.publication.plan);
        if(data.capabilities.download_published_pdf!==true)node('p','El PDF no está disponible para esta publicación.',summary);
      }else node('p','El profesional aún no ha publicado un plan para este vínculo.',summary);
      panel.hidden=false;controls();ui.status('Contexto consultado. Tu perfil y diario personales se conservan separados.');
    });}catch(error){clearPublication();throw error;}
  }
  pdf.addEventListener('click',()=>ui.run(async()=>{
    scope?.check();if(!scope||!selected||!result?.publication||result.capabilities.download_published_pdf!==true)return;
    const exact=result.publication.id,link=selected.link_id;
    ui.status('Preparando el PDF de esta publicación…');
    const blob=await scope.read(context=>Api.vinculos.pdf(link,exact,context));scope.check();
    scope.render(()=>ui.download(blob));
  }));
  async function removeLink(row) {
    ui.context.check();if(mutationUnconfirmed||!row||row.capabilities.revoke_link!==true)return;
    if(!window.confirm('¿Desvincularte de este contexto? Se conservan tu cuenta, sesiones, diario y planes personales.'))return;
    ui.context.check();mutationUnconfirmed=true;controls();
    const receipt=await ui.context.read(context=>Api.vinculos.desvincular(row.link_id,row.version,context));ui.context.check();
    if(receipt?.status!=='revoked'||receipt.link_id!==row.link_id)throw new Error('Invalid unlink receipt');
    await load();ui.status('Vínculo retirado. Tu cuenta y datos personales se conservan.');
  }
  leave.addEventListener('click',()=>ui.run(()=>removeLink(selected),true));
  document.getElementById('member-links-refresh').addEventListener('click',()=>ui.run(()=>load()));
  more.addEventListener('click',()=>ui.run(()=>load(false)));
  (async()=>{try{
    const me=await ui.context.start();ui.context.check();const home=document.getElementById('member-home');
    home.href=me.team_gym_id?'/equipo/inicio':me.tipo==='gym'?'/dashboard':'/mi-plan';home.hidden=false;
    await ui.run(()=>load());
  }catch{/* Lifecycle clears all private views on failure. */}})();
})();
