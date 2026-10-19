from pathlib import Path
import zipfile,hashlib,json,shutil
root=Path(__file__).parent
author=Path('F:/MetodoBaseWeb-diary-ui-20261019')
archive=author/'docs/implementation/20261018-evolution/evidence/ux/diary-ui-controls-fix-raw-before.zip'
with zipfile.ZipFile(archive) as z:
 names=z.namelist()
 matches=[n for n in names if n=='usuario-privacidad-87.js']
 assert len(matches)==1,matches
 raw=z.read(matches[0]);assert hashlib.sha256(raw).hexdigest()=='2d94a7569689cf5018c88424506204cc6d961707240b13bceab0b5be9c312302'
 for name in ['web/static/js/api.js','web/static/js/usuario-diario.js','web/static/js/usuario-privacidad.js','web/static/js/usuario-plan-operacion.js','web/templates/base_usuario.html']:
  target=root/'baseline87'/name;target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(raw if name.endswith('usuario-privacidad.js') else (author/name).read_bytes())
 (root/'baseline87-provenance.json').write_text(json.dumps({'archive':str(archive),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_member':matches[0],'raw_consumer_sha256':hashlib.sha256(raw).hexdigest(),'other_four_sources':'Copied current only after identity with preserved 87 source hashes was asserted below.'},indent=2)+'\n',encoding='utf8')
 old=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-diary-ui-security-fix-review-20261019/extras-candidate/extras.json').read_text())['sourceBefore']
 assert all(hashlib.sha256((root/'baseline87'/name).read_bytes()).hexdigest()==digest for name,digest in old.items())
 print('Exact raw baseline87 five source hashes verified.')
