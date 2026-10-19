/* Measurement intent in RAM. A transport ambiguity never creates a second record key. */
(() => {
  'use strict';
  const fail=code=>Object.assign(new Error('Consulta el resultado de esta operación antes de preparar otro registro.'),{code});
  function create({write,read,matches,check,uuid=()=>crypto.randomUUID(),onState=()=>{}}){
    let intent=null,busy=false,closed=false,status='idle',record=null,epoch=0;
    function assert(ticket=epoch){if(closed||ticket!==epoch)throw fail('session_changed');check();}
    function emit(){assert();onState({status,busy,record,hasIntent:intent!==null});assert();}
    function invalidate(){closed=true;epoch++;intent=null;record=null;busy=false;status='invalid';}
    function newIntent(){assert();if(busy||!['idle','confirmed'].includes(status))throw fail('progress_operation_pending');intent=null;record=null;status='idle';emit();}
    async function submit(payload){
      assert();if(busy)throw fail('progress_busy');
      if(intent){
        if(status!=='missing'||JSON.stringify(payload)!==intent.serialized)throw fail('progress_operation_pending');
      }else{
        if(status!=='idle')throw fail('progress_operation_pending');
        const key=uuid();if(typeof key!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(key))throw fail('progress_invalid_input');
        // The caller supplies a validated, fixed-shape input. Clone before any await.
        const serialized=JSON.stringify(payload);intent={key,serialized,payload:JSON.parse(serialized)};
      }
      busy=true;status='saving';const ticket=epoch;
      try{
        emit();const result=await write(intent.key,JSON.parse(intent.serialized));assert(ticket);
        if(!matches(result,intent.payload)){status='conflict';throw fail('progress_version_conflict');}
        record=result;status='confirmed';return result;
      }catch(error){assert(ticket);if(status!=='conflict')status='unconfirmed';throw error;}
      finally{if(!closed&&ticket===epoch){busy=false;emit();}}
    }
    async function readBack(){
      assert();if(busy)throw fail('progress_busy');if(!intent||!['unconfirmed','conflict','missing'].includes(status))throw fail('progress_operation_pending');
      busy=true;const ticket=epoch;
      try{
        emit();const result=await read(intent.key);assert(ticket);
        if(result===null){record=null;status='missing';return null;}
        if(!matches(result,intent.payload)){record=result;status='conflict';throw fail('progress_version_conflict');}
        record=result;status='confirmed';return result;
      }catch(error){assert(ticket);if(status!=='conflict')status='unconfirmed';throw error;}
      finally{if(!closed&&ticket===epoch){busy=false;emit();}}
    }
    return Object.freeze({submit,readBack,newIntent,invalidate,get busy(){return busy;},get status(){return status;}});
  }
  window.ProgresoMedicion=Object.freeze({create});
})();
