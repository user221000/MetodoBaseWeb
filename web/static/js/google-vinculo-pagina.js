/* First-party GIS integration. Never paste, decode, serialize or persist a provider credential. */
(function(){
  'use strict';
  const root=document.getElementById('google-link-page');if(!root||!window.GoogleVinculo||typeof Api==='undefined'||!Api.googleLink)return;
  const get=suffix=>document.getElementById('google-link-'+suffix),clientId=root.dataset.googleClientId||'';
  const password=get('password'),factor=get('factor'),method=get('method'),box=get('button');
  let controller,displayed=null,googleReady=false,googleLoading=false,googleTicket=null,serial=0;
  const clear=()=>{password.value='';factor.value='';get('unlink-agree').checked=false;googleTicket=null;};
  const node=(tag,text)=>{const result=document.createElement(tag);result.textContent=text;return result;};
  function chooseFactor(){factor.value='';factor.required=method.value!=='none';get('factor-group').hidden=method.value==='none';factor.disabled=controller.view().busy||method.value==='none';factor.inputMode=method.value==='totp'?'numeric':'text';get('factor-label').textContent=method.value==='recovery'?'Código de recuperación sin usar':'Código actual de la aplicación';}
  function renderGoogle(){
    if(!googleReady||controller.view().phase!=='ready')return;
    box.replaceChildren();const state='google-link-'+(++serial);
    google.accounts.id.renderButton(box,{theme:'outline',size:'large',text:'continue_with',locale:'es',width:Math.min(400,box.clientWidth||280),state,click_listener:()=>{const attempt=controller.beginGoogle();if(attempt)googleTicket={attempt,state};}});
  }
  function render(value){
    const blocked=['invalidated','closed','closed_error','closing'].includes(value.phase);
    get('status').textContent=value.message;
    get('load').disabled=value.busy||blocked;get('more').disabled=value.busy||blocked;get('more').hidden=!value.next;
    get('cancel').disabled=blocked;get('provider').hidden=!['ready','google'].includes(value.phase)||!value.canLink;
    get('enable').hidden=googleReady;get('enable').disabled=value.busy||blocked||value.phase!=='ready'||!clientId||googleLoading;
    get('proof').hidden=!['proof','unlink'].includes(value.phase);
    get('confirm-panel').hidden=value.phase!=='confirm';get('confirm').disabled=value.busy||value.phase!=='confirm';
    for(const suffix of ['password','method','factor','unlink-agree','submit'])get(suffix).disabled=value.busy||blocked;
    factor.disabled=value.busy||blocked||method.value==='none';
    get('unlink-label').hidden=value.phase!=='unlink';get('submit').textContent=value.phase==='unlink'?'Confirmar la desvinculación seleccionada':'Verificar y preparar vínculo';
    get('selection').textContent=value.selected===null?'':'Seleccionaste el vínculo '+(value.selected+1)+' de esta consulta. Comprueba sus fechas antes de confirmar.';
    get('contact').textContent=value.contact?'Cuenta de Google elegida: '+value.contact:'';
    get('expiry').textContent=value.expires?'Confirma antes de '+value.expires+' (fecha y zona del servidor).':'';
    get('list').hidden=!value.items.length;
    if(displayed!==value.items){displayed=value.items;get('items').replaceChildren();value.items.forEach((item,index)=>{const li=document.createElement('li'),article=document.createElement('article');article.append(node('h3','Vínculo '+(index+1)),node('p',item.active?'Activo para el acceso con Google.':'Desvinculado: no permite iniciar sesión.'),node('p','Creado: '+item.created_at),node('p',item.revoked_at?'Desvinculado: '+item.revoked_at:'Sin fecha de desvinculación registrada.'));if(item.active){const button=node('button','Seleccionar vínculo '+(index+1)+' para desvincular');button.type='button';button.addEventListener('click',()=>{if(controller.selectUnlink(index))password.focus();});article.append(button);}li.append(article);get('items').append(li);});}
    for(const button of get('items').querySelectorAll('button'))button.disabled=value.busy||blocked;
    if(value.phase!=='google')googleTicket=null;
    if(blocked||['idle','error'].includes(value.phase))box.replaceChildren();
    if(value.phase==='ready'&&!value.busy)renderGoogle();
  }
  controller=GoogleVinculo.create({onClear:clear,onView:render});
  function showError(text){get('error').textContent=text;get('error').hidden=false;get('error').focus();}
  async function action(task){get('error').textContent='';get('error').hidden=true;const result=await task();if(!result&&['error','invalidated','closed_error'].includes(controller.view().phase))get('status').focus();else if(result&&['proof','unlink'].includes(controller.view().phase))password.focus();else if(result)get('status').focus();}
  get('load').addEventListener('click',()=>void action(()=>controller.load()));get('more').addEventListener('click',()=>void action(controller.more));get('confirm').addEventListener('click',()=>void action(controller.confirm));
  get('cancel').addEventListener('click',()=>{controller.cancel();get('error').textContent='';get('error').hidden=true;get('status').focus();});
  method.addEventListener('change',chooseFactor);
  get('proof').addEventListener('submit',event=>{event.preventDefault();const proof={password:password.value,method:method.value,factor:factor.value},agreed=get('unlink-agree').checked;void action(()=>controller.view().phase==='unlink'?controller.unlink(proof,agreed):controller.start(proof));});
  get('enable').addEventListener('click',()=>{
    if(googleLoading||googleReady||!clientId||controller.view().phase!=='ready')return;
    googleLoading=true;render(controller.view());const script=document.createElement('script');script.src='https://accounts.google.com/gsi/client';script.async=true;script.nonce=document.querySelector('script[nonce]')?.nonce||'';
    script.onerror=()=>{googleLoading=false;if(controller.view().phase!=='ready')return;render(controller.view());showError('No se pudo cargar Google. No se inició ningún vínculo. Puedes volver a cargar la opción explícitamente.');};
    script.onload=()=>{googleLoading=false;if(controller.view().phase!=='ready')return;try{
      google.accounts.id.initialize({client_id:clientId,ux_mode:'popup',auto_select:false,button_auto_select:false,essential_claims:'auth_time',callback:response=>{
        const ticket=googleTicket;if(!ticket||response.state!==ticket.state||controller.view().phase!=='google')return;googleTicket=null;
        if(controller.acceptGoogle(response.credential,ticket.attempt))password.focus();
      }});googleReady=true;render(controller.view());
    }catch(_){showError('Google no está disponible para esta verificación. No se preparó ningún vínculo.');}};
    document.head.appendChild(script);
  });
  function invalidate(){googleTicket=null;controller.invalidate();box.replaceChildren();get('error').textContent='';get('error').hidden=true;}
  window.addEventListener('metodobase-session-changed',invalidate);window.addEventListener('pagehide',invalidate);
  window.addEventListener('storage',event=>{if(event.key===null||['mb_token','mb_refresh_token'].includes(event.key))invalidate();});
  const timer=setInterval(()=>controller.expire(),1000);window.addEventListener('pagehide',()=>clearInterval(timer),{once:true});
  get('load').disabled=false;get('cancel').disabled=false;chooseFactor();render(controller.view());
  if(!clientId)get('provider-title').textContent='Google no está configurado. Puedes consultar o desvincular vínculos existentes con una prueba local válida.';
})();
