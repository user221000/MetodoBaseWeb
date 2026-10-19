"""Freeze the ownership fix and replay the independent before/after criteria."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
root=Path('F:/mb-r12-ui-fix29-20261019')
before_root=Path('F:/mb-r12-full29-20261019')
qa=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/qa-r12-composition29-independent-20261019/final939')
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r12-controls-author-v3-20261019');out.mkdir(exist_ok=False)
sha=lambda value:hashlib.sha256(value).hexdigest()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert head==subprocess.check_output(['git','rev-parse','HEAD'],cwd=before_root,text=True).strip()=='93975691e02daac966b871e218db76e4a3dd0114'
driver=(qa/'control_scope_review_v2.cjs').read_bytes()
assert sha(driver)=='51f9a1bc7a3b7a90d906017920ece2c5c54f37275aa2d9ed9728ba6c4f374c1d'
target=root/'tests/e2e/member_link_controls.cjs';assert target.read_bytes()==driver
old=(before_root/'web/static/js/vinculos-ui.js').read_bytes()
assert sha(old)=='fe109ac13ae8584530efc8c98ee1137031c7442fb9dfb7fa3efe49536625c5de'
assert old==subprocess.check_output(['git','show','HEAD:web/static/js/vinculos-ui.js'],cwd=root)
assert sha(old.replace(b'\n',b'\r\n'))=='b582e61feaa9753e6460e077d6387d4207a8cf33efea49dbb92ea720d23f7653'
(out/'vinculos-ui-before.js').write_bytes(old)
paths=['web/static/js/vinculos-ui.js','web/static/js/vinculos-profesional.js','web/static/js/vinculos-lectura.js','web/static/js/vinculos-invitacion.js','tests/e2e/member_link_consumers.cjs']
for relative in paths:
    (out/(Path(relative).name+'.before')).write_bytes((before_root/relative).read_bytes())
fixture=root/'tests/e2e/member_link_consumers.cjs'
original=subprocess.check_output(['git','show','HEAD:tests/e2e/member_link_consumers.cjs'],cwd=root).decode()
old_query="querySelectorAll(selector){const out=[];for(const x of this.children){if(selector==='[data-mutation]'&&x.dataset.mutation)out.push(x);out.push(...x.querySelectorAll(selector));}return out;}"
new_query="querySelectorAll(selector){const tags=selector.split(',').map(s=>s.toUpperCase());const out=[];for(const x of this.children){if((selector==='[data-mutation]'&&x.dataset.mutation)||tags.includes(x.tagName))out.push(x);out.push(...x.querySelectorAll(selector));}return out;}"
assert original.count(old_query)==1
assert fixture.read_text(encoding='utf8').replace(new_query,old_query)==original
names=set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1])
names.add('tests/e2e/member_link_controls.cjs');names=sorted(names)
def photo():return {name:sha((root/name).read_bytes()) for name in names}
def save(name,value):(out/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
first=photo();save('before-source.json',first)
node=Path(shutil.which('node')).resolve()
rows=[]
for phase,source,expected in [('before',out/'vinculos-ui-before.js',1),('after',root/'web/static/js/vinculos-ui.js',0)]:
    result=subprocess.run([str(node),str(target),str(source)],cwd=root,capture_output=True,timeout=20)
    (out/(phase+'.json')).write_bytes(result.stdout);(out/(phase+'.stderr.log')).write_bytes(result.stderr)
    data=json.loads(result.stdout);assert result.returncode==expected and data['total']==3
    assert data['passed']==(1 if phase=='before' else 3)
    rows.append({'phase':phase,'exit_code':result.returncode,'total':3,'passed':data['passed']})
result=subprocess.run([str(node),'tests/e2e/member_link_consumers.cjs'],cwd=root,capture_output=True,timeout=30)
(out/'consumer16.json').write_bytes(result.stdout);(out/'consumer16.stderr.log').write_bytes(result.stderr)
data=json.loads(result.stdout);assert result.returncode==0 and data['total']==data['passed']==16
for name in [*paths,'tests/e2e/member_link_controls.cjs']:
    result=subprocess.run([str(node),'--check',name],cwd=root,capture_output=True,timeout=15)
    (out/(Path(name).name+'.syntax.log')).write_bytes(result.stdout+result.stderr);assert result.returncode==0
after=photo();save('after-source.json',after);assert first==after
receipt={'parent':head,'Node':subprocess.check_output([str(node),'--version'],text=True).strip(),'Node_executable_sha256':sha(node.read_bytes()),
         'independent_driver_RAW_sha256':sha(driver),'all_source_files':len(names),'all_sources_stable':True,
         'before_after_same_three_assertions':rows,'old_consumer16_all_green':True,'existing_consumer_assertions_byte_unchanged':True,
         'only_product_files':paths[:4],'fixture_change':'Generic native tag selectors supported in existing minimal DOM; exact inverse retains all sixteen old assertions.',
         'scope':'Author VM/Node syntax only. The real PG browser export criterion remains independently red until QA replays a clean frozen fix.',
         'source_freeze':{name:{'RAW_sha256':sha((root/name).read_bytes()),'LF_sha256':sha((root/name).read_bytes().replace(b'\r\n',b'\n'))} for name in [*paths,'tests/e2e/member_link_controls.cjs']}}
save('review.json',receipt)
print(json.dumps({'before':'2 red/1 green','after':'3 green','existing_consumers':'16 green','source_files':len(names),'sources_stable':True}))
