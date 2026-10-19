"""Add a current DOM fixture while retaining the exact sixteen accepted consumer cases."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path(r'F:\mb-mfa31-compose-20261019')
out = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-member-consumers31-prepare-20261019')
base = '2010a6c56187fe0cf3389da7ffc4cdd09e00f968'
git = lambda *args: subprocess.check_output(['git', *args], cwd=root)
assert git('rev-parse', 'HEAD').decode().strip() == base and not git('status', '--porcelain', '--untracked-files=no')
old_path = root / 'tests/e2e/member_link_consumers.cjs'
old = old_path.read_text(encoding='utf8')
marker = 'const tests=[];const test=(n,f)=>tests.push([n,f]);'
assert old.count(marker) == 1
cases = old[old.index(marker):]
header = r'''/* Current31 fixture: actual R12 consumers plus actual R24 companion modules.
 * The sixteen test callbacks below are exact copies of the accepted v1 cases.
 * APIv1 transport remains an explicit double; no HTTP or browser claim.
 * Rendered include IDs and companion loading follow the real template. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),A='11111111-1111-4111-8111-111111111111',B='22222222-2222-4222-8222-222222222222';
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const flush=async()=>{for(let i=0;i<12;i++)await new Promise(setImmediate);};
const capabilities={issue_invitation:true,rotate_invitation:true,revoke_link:true,publish_plan:true,withdraw_publication:true};
const context={kind:'gym_member',link_id:A,gym_name:'Synthetic gym',client_display_name:'Synthetic member'};
const row={link_id:A,status:'active',version:7,context,capabilities:{read_published_plan:true,revoke_link:true}};
const fixed=()=>Object.fromEntries(['desayuno','almuerzo','comida','cena'].map(k=>[k,{kcal_objetivo:100,kcal_real:100,alimentos:{'Literal <img src=x onerror=alert(1)>':100}}]));
class Element{
  constructor(tag,doc){this.tagName=tag.toUpperCase();this.doc=doc;this.children=[];this.listeners={};this.hidden=false;this.disabled=false;this.dataset={};this.value='';this._text='';}
  set textContent(v){this._text=String(v);this.children=[];}get textContent(){return this._text+this.children.map(x=>x.textContent).join('');}
  set innerHTML(_){throw new Error('Consumer must not insert JSON as HTML');}
  append(...nodes){for(const x of nodes){x.parent=this;this.children.push(x);}}appendChild(x){this.append(x);}
  replaceChildren(...nodes){this.children=[];this._text='';this.append(...nodes);}
  setAttribute(k,v){this[k]=String(v);}getAttribute(k){return this[k]??null;}
  addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);}
  async fire(name){const event={preventDefault(){},currentTarget:this,target:this};for(const fn of this.listeners[name]||[])await fn(event);await flush();}
  click(){if(this.tagName==='A')this.doc.downloads.push({href:this.href,name:this.download});else return this.fire('click');}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);}
  focus(){this.doc.activeElement=this;}reportValidity(){return this.value.includes('@');}
  all(){return this.children.flatMap(child=>[child,...child.all()]);}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  querySelectorAll(selector){
    const selectors=selector.split(',').map(value=>value.trim()),out=[];
    for(const selected of selectors){
      const parts=selected.split(/\s+/);
      if(parts.length>1){for(const parent of this.querySelectorAll(parts[0]))out.push(...parent.querySelectorAll(parts.slice(1).join(' ')));continue;}
      for(const element of this.all()){
        const data=/^\[data-([a-z-]+)\]$/.exec(selected);
        const key=data?.[1].replace(/-([a-z])/g,(_match,letter)=>letter.toUpperCase());
        if(selected.startsWith('#')?element.id===selected.slice(1):data?element.dataset[key]!==undefined:element.tagName.toLowerCase()===selected.toLowerCase())out.push(element);
      }
    }
    return [...new Set(out)];
  }
}
function template(name,seen=[]){
  assert(/^[a-z_]+\.html$/.test(name));assert(!seen.includes(name)&&seen.length<5);
  return fs.readFileSync(path.join(root,'web/templates',name),'utf8').replace(/\{%\s*include\s+["']([a-z_]+\.html)["']\s*%\}/g,(_match,child)=>template(child,[...seen,name]));
}
function mountMarkup(markup,doc,ids){
  const stack=[doc.body],voids=new Set(['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']);
  for(const match of markup.replace(/<!--[\s\S]*?-->/g,'').matchAll(/<(\/?)([a-z][a-z0-9]*)(\s[^>]*?)?\s*(\/?)>/g)){
    const tag=match[2].toLowerCase();
    if(match[1]){for(let i=stack.length-1;i>0;i--)if(stack[i].tagName.toLowerCase()===tag){stack.length=i;break;}continue;}
    const element=new Element(tag,doc),attributes=match[3]||'';
    for(const attribute of attributes.matchAll(/([a-zA-Z][a-zA-Z0-9_-]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)){
      const name=attribute[1],value=attribute[2]??attribute[3]??attribute[4]??'';element.setAttribute(name,value);
      if(name==='id'){assert(!ids[value]);element.id=value;ids[value]=element;}
      if(name==='hidden'||name==='disabled'||name==='checked')element[name]=true;
      if(name.startsWith('data-'))element.dataset[name.slice(5).replace(/-([a-z])/g,(_match,letter)=>letter.toUpperCase())]=value;
    }
    stack.at(-1).append(element);if(!voids.has(tag)&&!match[4])stack.push(element);
  }
}
function env(kind){
  const name={invitation:'accept_client_link.html',professional:'cliente_vinculacion.html',reader:'usuario_vinculos.html'}[kind];
  const markup=template(name),ids={},events={},calls=[],urls=[],revoked=[];
  const doc={downloads:[],createElement(tag){return new Element(tag,doc);},getElementById:id=>ids[id],querySelectorAll:selector=>doc.body.querySelectorAll(selector)};
  doc.body=new Element('body',doc);mountMarkup(markup,doc,ids);
  if(ids['professional-link-page'])ids['professional-link-page'].dataset.clientId='synthetic-client';
  const e={doc,ids,calls,urls,revoked,revision:0,handlers:{},keyCount:0};
  const me={id:'synthetic-a',tipo:'usuario',role:'viewer',team_gym_id:null,session_version:1};
  const api={contexto:async()=>({revision:e.revision,subject:'synthetic-a',me}),validarContexto:c=>{if(c.revision!==e.revision)throw Object.assign(new Error('Synthetic session switch'),{code:'session_changed'});},verificarContexto:async c=>api.validarContexto(c)};
  const defaults={estado:{client_id:'synthetic-client',capabilities,items:[],next_after:null},listar:{items:[row],next_after:null},plan:{context,link:{status:'active',version:7},capabilities:{read_published_plan:true,download_published_pdf:true,revoke_link:true},publication:{id:B,version:3,source_plan_id:41,plan_schema_version:1,plan:fixed(),meta:{kcal_objetivo:400},published_at:'2026-10-19T18:00:00Z'}},inspeccionar:{status:'pending',version:4,expires_at:'2026-10-26T18:00:00Z',link_id:A,context,can_accept:true},aceptar:{link_id:A,status:'active',version:7,context},emitir:{invitation_id:B,link_id:A,status:'pending',link_status:'pending',version:1,link_version:1,expires_at:'2026-10-26T18:00:00Z',delivery_status:'not_confirmed'},pdf:new Blob(['%PDF-synthetic'],{type:'application/pdf'})};
  for(const name of ['estado','listar','plan','inspeccionar','aceptar','emitir','rotar','revocar','publicar','retirar','desvincular','pdf'])api[name]=async(...args)=>{calls.push({name,args});return e.handlers[name]?e.handlers[name](...args):defaults[name];};
  const box={document:doc,Api:{vinculos:api},Blob,URLSearchParams,console,location:{search:''},
    URL:{createObjectURL:()=>{const value='blob:synthetic-'+urls.length;urls.push(value);e.onURL?.();return value;},revokeObjectURL:u=>revoked.push(u)},
    crypto:{randomUUID:()=>{e.keyCount++;return '33333333-3333-4333-8333-'+String(e.keyCount).padStart(12,'0');}},
    addEventListener:(name,fn)=>{(events[name]??=[]).push(fn);},setTimeout:()=>1,clearTimeout:()=>{},confirm:()=>true,
    takeClientLinkInvitation:()=>({token:'S'.repeat(43),state:'ready'}),
  };box.window=box;vm.createContext(box);
  const consumer={invitation:'vinculos-invitacion.js',professional:'vinculos-profesional.js',reader:'vinculos-lectura.js'}[kind];
  e.load=()=>{
    const files=['vinculos-contexto.js','vinculos-ui.js',...(kind==='reader'?['usuario-diario.js','plan-diario-datos.js','plan-diario-ui.js','plan-publicacion-consumo.js']:[]),consumer];
    const actual=[...markup.matchAll(/src="\/static\/js\/([^"?]+\.js)(?:\?[^\"]*)?"/g)].map(match=>match[1]);
    let last=-1;for(const file of files){const position=actual.indexOf(file);assert(position>last,'Fixture companion order must follow the actual template');last=position;vm.runInContext(fs.readFileSync(path.join(root,'web/static/js',file),'utf8'),box);}
    if(kind==='reader'){assert.equal(typeof box.PlanDayUI.mount,'function');assert.equal(typeof box.PublicationConsumption.mount,'function');}
  };
  e.emit=(name,event={})=>{for(const fn of events[name]||[])fn(event);};e.text=()=>doc.body.textContent;e.box=box;
  return e;
}
'''
target = root / 'tests/e2e/member_link_consumers31.cjs'
assert not target.exists()
content = header + cases
assert content[content.index(marker):] == cases
out.mkdir(exist_ok=False)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
with target.open('x', encoding='utf8', newline='\n') as output:
    output.write(content)
(out/'before-source.raw.cjs').write_bytes(old_path.read_bytes())
(out/'prepared.raw.cjs').write_bytes(target.read_bytes())
subprocess.run([r'C:\Program Files\nodejs\node.exe','--check',str(target)],cwd=root,check=True,capture_output=True)
receipt = {'base':base,'original_helper_raw_sha256':hashlib.sha256(old_path.read_bytes()).hexdigest(),
           'new_fixture_raw_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'test_callback_and_runner_suffix_exact':True,
           'suffix_sha256':hashlib.sha256(cases.encode()).hexdigest(),
           'scope':'Prepared current fixture only. All16 callbacks unchanged, actual R24 companions and rendered includes instead of passive causal stubs. Original accepted helper and source30 archive untouched. No acceptance before execution.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps(receipt))
