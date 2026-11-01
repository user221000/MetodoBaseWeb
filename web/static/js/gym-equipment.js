/* Owner-managed machine inventory; authenticated RAM transport, no replay. */
(function(root){
  'use strict';
  const endpoint='/api/rutinas/equipamiento?context=gym';
  const basics=['barbell','bench','dumbbell','bodyweight'];
  const invalid=()=>Object.assign(Error('No pudimos validar el inventario del gimnasio.'),{code:'equipment_invalid_response'});
  const text=value=>typeof value==='string'&&value.length>0&&value.length<=200;
  const id=value=>typeof value==='string'&&/^[a-z][a-z0-9-]{0,63}$/.test(value);
  const normal=value=>value.toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  function validate(value){
    if(value?.version!==1||value.scope!=='gym'||typeof value.configured!=='boolean'||typeof value.can_edit!=='boolean'||!Number.isSafeInteger(value.revision)||value.revision<0||value.revision>2147483647)throw invalid();
    if(!Array.isArray(value.machines)||value.machines.length<1||value.machines.length>128||!Array.isArray(value.machine_ids)||value.machine_ids.length>value.machines.length)throw invalid();
    if(!Array.isArray(value.base_equipment)||value.base_equipment.length!==basics.length||new Set(value.base_equipment).size!==basics.length||!value.base_equipment.every(key=>basics.includes(key)))throw invalid();
    const known=new Set();
    for(const machine of value.machines){if(!id(machine.id)||known.has(machine.id)||!text(machine.label)||!text(machine.group))throw invalid();known.add(machine.id);}
    if(new Set(value.machine_ids).size!==value.machine_ids.length||!value.machine_ids.every(key=>known.has(key))||value.configured&&value.revision<1||!value.configured&&(value.revision!==0||value.machine_ids.length!==0))throw invalid();
    return value;
  }
  async function request(api,method='GET',body=undefined,fetcher=root.fetch.bind(root)){
    if(!['GET','PUT'].includes(method))throw invalid();
    await api.session.ready;
    const context=api.session.capture(),token=api.getToken();api.session.check(context);
    if(!token)throw Object.assign(Error('Inicia sesión para consultar las máquinas del gimnasio.'),{status:401});
    const options={method,headers:{Accept:'application/json',Authorization:'Bearer '+token},credentials:'omit',mode:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer'};
    if(method==='PUT'){
      if(!body||!Number.isSafeInteger(body.expected_revision)||body.expected_revision<0||body.expected_revision>2147483646||!Array.isArray(body.machine_ids)||body.machine_ids.length>128||new Set(body.machine_ids).size!==body.machine_ids.length||!body.machine_ids.every(id)||Object.keys(body).length!==2)throw invalid();
      options.headers['Content-Type']='application/json';options.body=JSON.stringify(body);
    }else if(body!==undefined)throw invalid();
    const response=await fetcher(endpoint,options);api.session.check(context);
    if(response.status===401)api.session.rejectUnauthorized(context,token);
    const raw=await response.text();api.session.check(context);
    if(new TextEncoder().encode(raw).byteLength>131072)throw invalid();
    let value;try{value=JSON.parse(raw);}catch{throw invalid();}
    if(!response.ok)throw Object.assign(Error(text(value?.detail?.message)?value.detail.message:'No pudimos consultar el inventario.'),{status:response.status,code:value?.detail?.code});
    return validate(value);
  }
  function mount(panel,api=(typeof Api!=='undefined'?Api:undefined)){
    const get=name=>panel.querySelector('[data-gym-equipment-'+name+']');
    const put=(parent,tag,value,className)=>{const node=document.createElement(tag);if(value!==undefined)node.textContent=value;if(className)node.className=className;parent.append(node);return node;};
    let record=null,selected=new Set(),epoch=0,dead=false,busy=false,conflicted=false,editSequence=0;
    function changed(){return record&&(!record.configured||JSON.stringify([...selected].sort())!==JSON.stringify([...record.machine_ids].sort()));}
    function controls(){
      const editable=record?.can_edit===true&&!busy&&!conflicted&&!dead;
      for(const input of get('list').querySelectorAll('input'))input.disabled=!editable;
      get('save').hidden=record?.can_edit!==true;get('save').disabled=!editable||!changed();get('clear').disabled=!editable||selected.size===0;
      get('reload').disabled=busy||dead;get('selected').textContent=selected.size+' máquina'+(selected.size===1?'':'s')+' seleccionada'+(selected.size===1?'':'s');
      get('conflict').hidden=!conflicted;get('readonly').hidden=!record||record.can_edit;
    }
    function draw(){
      get('list').replaceChildren();const query=normal(get('query').value.trim()),groups=new Map();
      for(const machine of record.machines){if(query&&!normal(machine.label+' '+machine.group).includes(query))continue;if(!groups.has(machine.group))groups.set(machine.group,[]);groups.get(machine.group).push(machine);}
      for(const [name,machines] of groups){
        const section=put(get('list'),'fieldset',undefined,'gym-equipment-group');put(section,'legend',name);const cards=put(section,'div',undefined,'gym-equipment-options');
        for(const machine of machines){const label=put(cards,'label',undefined,'gym-equipment-option'),input=put(label,'input');input.type='checkbox';input.value=machine.id;input.checked=selected.has(machine.id);put(label,'span',machine.label);input.addEventListener('change',()=>{if(dead||busy||conflicted||!record?.can_edit)return;if(input.checked)selected.add(machine.id);else selected.delete(machine.id);editSequence++;controls();get('status').textContent='Tienes cambios pendientes. Guarda para aplicarlos a las próximas rutinas.';});}
      }
      get('empty').hidden=groups.size!==0;controls();
    }
    function invalidate(){
      if(dead)return;dead=true;epoch++;record=null;selected.clear();busy=false;get('list').replaceChildren();get('query').value='';get('content').hidden=true;get('selected').textContent='';get('status').textContent='La sesión cambió. Abre la configuración desde tu cuenta.';get('reload').disabled=true;get('save').disabled=true;
    }
    async function load(){
      if(dead||busy)return;const ticket=++epoch;busy=true;record=null;selected.clear();conflicted=false;get('content').hidden=true;get('reload').disabled=true;get('status').textContent='Consultando las máquinas de tu gimnasio…';
      try{const value=await request(api);if(dead||ticket!==epoch)return;record=value;selected=new Set(value.machine_ids);editSequence=0;get('content').hidden=false;draw();get('status').textContent=value.configured?'Inventario guardado. Se aplicará a las próximas rutinas de tus clientes.':'Aún no hay máquinas guardadas. Hasta configurarlas, se usará sólo el equipo básico.';}
      catch(error){if(dead||ticket!==epoch)return;get('status').textContent=error.status===401?'Inicia sesión para consultar las máquinas.':error.status===403?'Este inventario no está disponible para tu cuenta.':'No pudimos consultar las máquinas. Vuelve a cargar el inventario.';}
      finally{if(!dead&&ticket===epoch){busy=false;controls();}}
    }
    async function save(){
      if(dead||busy||conflicted||!record?.can_edit||!changed())return;
      const ticket=++epoch,sequence=editSequence,body={machine_ids:[...selected].sort(),expected_revision:record.revision};busy=true;controls();get('status').textContent='Guardando máquinas disponibles…';
      try{
        const value=await request(api,'PUT',body);if(dead||ticket!==epoch)return;
        if(value.revision!==body.expected_revision+1||!value.configured||JSON.stringify([...value.machine_ids].sort())!==JSON.stringify(body.machine_ids))throw invalid();
        record=value;if(sequence===editSequence)selected=new Set(value.machine_ids);conflicted=false;draw();
        get('status').textContent=changed()?'Inventario guardado. Revisa los cambios que siguen pendientes.':'Máquinas guardadas. Las nuevas rutinas usarán este inventario.';
        root.dispatchEvent(new CustomEvent('metodobase-gym-equipment-changed'));
      }catch(error){if(dead||ticket!==epoch)return;conflicted=true;get('status').textContent=error.status===409?'El inventario cambió en otra sesión. Cárgalo de nuevo antes de guardar.':error.status===403?'Tu cuenta ya no puede editar este inventario. Vuelve a cargarlo.':'No pudimos confirmar el guardado. Vuelve a cargar el inventario antes de intentarlo otra vez.';}
      finally{if(!dead&&ticket===epoch){busy=false;controls();}}
    }
    get('query').addEventListener('input',()=>{if(record&&!dead)draw();});get('reload').addEventListener('click',load);get('save').addEventListener('click',save);
    get('clear').addEventListener('click',()=>{if(!record?.can_edit||busy||conflicted||dead)return;selected.clear();editSequence++;draw();get('status').textContent='Selección vacía. Guarda para usar sólo el equipo básico.';});
    root.addEventListener('metodobase-session-changed',invalidate);root.addEventListener('pagehide',invalidate);root.addEventListener('pageshow',event=>{if(event.persisted)invalidate();});load();
    return Object.freeze({invalidate});
  }
  const exported=Object.freeze({validate,request,mount});if(typeof module!=='undefined'&&module.exports)module.exports=exported;root.GymEquipment=exported;
  if(typeof document!=='undefined'){const start=()=>{const panel=document.querySelector('[data-gym-equipment]');if(panel)mount(panel);};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();}
})(typeof window==='undefined'?globalThis:window);
