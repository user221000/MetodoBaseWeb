from pathlib import Path
import hashlib
import json

tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
old=tmp/'metodobase-checkpoint121-v2.py'
new=tmp/'metodobase-checkpoint121-v3.py'
source=old.read_text(encoding='utf8')
assert not new.exists()
for previous,current in [('OPS08','OPS11'),('OPS09','OPS12'),('OPS10','OPS13')]:
    source=source.replace(previous,current)
source=source.replace('117','118').replace('veinticinco hallazgos','veintiséis hallazgos')
needle="reviews=["
addition="""extra=Path(r'F:\\MetodoBaseWeb-linux-lab-20261019\\evidence\\expat-sec10-de69-native-diagnostic-20261019')
extra_manifest=(extra/'manifest.json').read_bytes()
assert SHA(extra_manifest)=='9a7abd7b4b054144daa059577371507b796b2a2e63344e566a86833fe0c88542'
extra_target=EV/extra.name
assert not extra_target.exists()
extra_target.mkdir();(extra_target/'.gitattributes').write_bytes(b'* -text\\n')
for name,meta in json.loads(extra_manifest).items():
    blob=(extra/name).read_bytes()
    assert SHA(blob)==meta['sha256'] and len(blob)==meta['bytes']
    scan(blob,name)
    out=extra_target/name
    assert out.resolve().is_relative_to(extra_target.resolve())
    out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(blob)
(extra_target/'manifest.json').write_bytes(extra_manifest)
assert SHA((extra_target/'source.json').read_bytes())=='ba64804ae9f2ccbcb638d73dfbe68630e295821076f98efaa4dcfdee95502b09'
reviews=[
 ('expat-sec10-de69-native-diagnostic-20261019','manifest.json','9a7abd7b4b054144daa059577371507b796b2a2e63344e566a86833fe0c88542'),"""
assert source.count(needle)==1
source=source.replace(needle,addition)
needle="refusal.mkdir(exist_ok=False);(refusal/'.gitattributes').write_bytes(b'* -text\\n')"
replacement="""assert refusal.exists() and (refusal/'.gitattributes').read_bytes()==b'* -text\\n'"""
assert source.count(needle)==1
source=source.replace(needle,replacement)
needle="if p.is_file():(refusal/p.name).write_bytes(p.read_bytes());raw.add(refusal/p.name)"
replacement="if p.is_file():\n        assert (refusal/p.name).read_bytes()==p.read_bytes();raw.add(refusal/p.name)"
assert source.count(needle)==1
source=source.replace(needle,replacement)
needle="data=json.loads((RUN/'TRAZABILIDAD.json').read_bytes())"
replacement="""errata=EV/'checkpoint121-id-correction-20261019'
assert not errata.exists()
errata.mkdir();(errata/'.gitattributes').write_bytes(b'* -text\\n')
for name in ['metodobase-checkpoint121-v2.py','metodobase-checkpoint121-v3-prepare.py']:
    (errata/name).write_bytes((TMP/name).read_bytes())
(errata/'correction.json').write_bytes((json.dumps({
 'failed_before_registry_or_document_writes':True,
 'cause':'OPS08, OPS09 and OPS10 already identify three different earlier findings. A uniqueness assertion rejected the attempted duplicate IDs before registry writes.',
 'new_allocation':{'OPS11':'Missing Clinic input','OPS12':'Empty real compiler argv trace','OPS13':'Additional dynamic ELF exports'},
 'immutable_receipt_correction':{'path':'root-native-provenance-gap-20261019/receipt.json','printed_id':'OPS09','canonical_new_id':'OPS12'},
 'earlier_OPS08_OPS09_OPS10_criteria_preserved':True,
 'closed_evidence_bytes_unchanged':True},indent=2)+'\\n').encode())
raw.update(p for p in errata.iterdir() if p.is_file())
"""+needle
assert source.count(needle)==1
source=source.replace(needle,replacement)
needle="]\nfor ident,problem,criterion,tasks,source,commit in discoveries:"
replacement=""" ('OPS13','El pyexpat reconstruido exporta 93 símbolos dinámicos frente a PyInit_pyexpat como único símbolo de la base.',
  'Conservar las imágenes y pruebas previas; derivar la visibilidad mínima de la configuración auténtica de la base, comprobar que sólo se exporta PyInit_pyexpat y validar C API, linkage y bindings con revisión independiente antes de aceptar el artefacto.',
  ['R18','R20','R21','SEC10'], 'expat-sec10-de69-native-diagnostic-20261019/source.json','de69a85e7903f1a7217b054c0edb269dd5560999'),
]
assert len({row[0] for row in discoveries})==len(discoveries)
assert not ({row[0] for row in discoveries}&set(before))
for ident,problem,criterion,tasks,source,commit in discoveries:"""
assert source.count(needle)==1
source=source.replace(needle,replacement)
source=source.replace("if ident=='OPS12':","if ident in {'OPS12','OPS13'}:")
source=source.replace('QA-15, OPS11 y OPS12','QA-15, OPS11, OPS12 y OPS13')
source=source.replace('OPS13 reservado mientras cierra su evidencia.','OPS13 registrado con evidencia nativa cerrada.')
source=source.replace('OPS13 queda reservado mientras sella evidencia y causa.','OPS13 queda registrado con evidencia nativa y causa selladas.')
source=source.replace('OPS13 se añadirá con la evidencia nativa cerrada.','OPS13 conserva la diferencia real de símbolos y su causa: falta -fvisibility=hidden de la configuración interna de la base.')
source=source.replace('MAIN sólo registra cinco hallazgos','MAIN sólo registra seis hallazgos')
source=source.replace('Los173PG comenzaron en ventana propia; aún sin resultado.','Los173PG comenzaron en ventana propia; 75 nodos aprobados, ejecución restante pendiente.')
source=source.replace('adaptación local en curso sin modificar asserts.','adaptación79dce040 ya probó54casos originales y2controles, conservando58asserts; revisión independiente pendiente.')
source=source.replace('correcciónaislada sinasserts cambiados.','correcciónaislada79dce040 con54originales+2controles verdes y58asserts exactos; revisión independiente pendiente.')
source=source.replace('la adaptación aislada conserva las 58 aserciones de esos módulos.','la adaptación aislada79dce040 conserva las 58 aserciones y aprobó54casos originales más2controles; falta revisión independiente.')
source=source.replace('están en ejecución en una ventana propia; no se adelanta su resultado.','están en ejecución en una ventana propia, con75nodos aprobados y el resto pendiente.')
source=source.replace('Seguridad está revisando métodos y errores, autorización y privacidad.','Seguridad confirmó12controles verdes y12rojos: OPTIONS405 y lectorGET500 omiten cabeceras privadas en ambas factories y las tres rutas. Los cuerpos permanecen opacos, sin fuga demostrada. Se conserva el before antes de corregirlo.')
source=source.replace("'root-native-provenance-gap-20261019/receipt.json'],","'root-native-provenance-gap-20261019/receipt.json','checkpoint121-id-correction-20261019/correction.json','expat-sec10-de69-native-diagnostic-20261019/source.json'],")
new.write_bytes(source.encode())
print(json.dumps({'prepared':str(new),'sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'new_ids':['QA-13','QA-14','QA-15','OPS11','OPS12','OPS13']}))
