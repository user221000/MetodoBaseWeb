"""Adapt manifest key spelling without changing any producer evidence or hash."""
from pathlib import Path
import hashlib
import json

tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
old=tmp/'metodobase-checkpoint119.py'
new=tmp/'metodobase-checkpoint119-v2.py'
source=old.read_text(encoding='utf8')
needle="return [{'path':name,**({'sha256':meta} if isinstance(meta,str) else meta)} for name,meta in value.items()]"
replacement="""result=[]
    for name,meta in value.items():
        if isinstance(meta,str):meta={'sha256':meta}
        else:
            meta=dict(meta)
            assert ('sha256' in meta) != ('SHA256' in meta)
            if 'SHA256' in meta:meta['sha256']=meta.pop('SHA256')
        result.append({'path':name,**meta})
    return result"""
assert source.count(needle)==1
source=source.replace(needle,replacement)
needle="""    assert not target.exists()
    target.mkdir()
    (target/'.gitattributes').write_bytes(b'* -text\\n')"""
replacement="""    existing=target.exists()
    if not existing:
        target.mkdir()
        (target/'.gitattributes').write_bytes(b'* -text\\n')
    else:
        assert (target/'.gitattributes').read_bytes()==b'* -text\\n'
        assert (target/'manifest.json').read_bytes()==manifest"""
assert source.count(needle)==1
source=source.replace(needle,replacement)
needle="""        path.write_bytes(blob)
    (target/'manifest.json').write_bytes(manifest)"""
replacement="""        if existing:assert path.read_bytes()==blob
        else:path.write_bytes(blob)
    if not existing:(target/'manifest.json').write_bytes(manifest)"""
assert source.count(needle)==1
source=source.replace(needle,replacement)

# Main prose is replaced before any registry mutation; identifiers and paths remain exact.
start=source.index("(RUN/'ENTREGA.md').write_text('''")
end=source.index("appendices={",start)
source=source[:start]+"""(RUN/'ENTREGA.md').write_text('''# Entrega candidata en curso

Checkpoint 119: 112 requisitos. Los 92 originales y los 110 criterios previos permanecen exactos. MAIN sigue en esquema 30, con 2597 aprobadas y una omisión de symlinks en Windows por cada modo: serial con cobertura y dos workers con orden mezclado.

MFA 31 está aislado en 4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae. Tiene aceptación de backend 440 acotada, revisión QA de diez VM y cuatro flujos HTTP y su repetición en PostgreSQL, quince grupos Chrome sobre c669, restauración poblada sobre 4a y corrección UX-19 focal de tres casos y dos adicionales. Los replays no son casos nuevos. Fixtures DAB y CI 31 siguen en revisión e integración; falta la regresión amplia actual y una imagen común.

D60 sólo tiene aceptación de metadata APT. Compilación, ABI, linkage, SCA y los 71 identificadores OS siguen pendientes. Desktop continúa soportado. Free: diez clientes, un plan por cliente al día y diez totales por gimnasio al día.

No es una entrega final. Sin push, PR, despliegue, cargos ni comunicaciones reales. [Estado](ESTADO.md), [validación](VALIDACION.md), [riesgos](RIESGOS.md), [registro](TRAZABILIDAD.md).
''',encoding='utf8')
"""+source[end:]
assert not new.exists()
new.write_bytes(source.encode())
out=tmp/'metodobase-checkpoint119-publication-precondition-20261019'
out.mkdir(exist_ok=False)
(out/'.gitattributes').write_bytes(b'* -text\n')
(out/'original-driver.py').write_bytes(old.read_bytes())
(out/'prepare-v2.py').write_bytes(Path(__file__).read_bytes())
(out/'cause.json').write_bytes((json.dumps({'original_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
 'failure':'KeyError sha256: restore producer uses uppercase SHA256; all prior manifest hashes remained exact.',
 'state':'No registry/docs/staging/commit mutation occurred. Two author proof directories had been copied successfully and remain byte exact.',
 'correction':'Accept exactly one of SHA256/sha256 when decoding map entries, without rewriting source evidence; reuse existing copy only after byte equality. Keep original driver and failed precondition cause.',
 'v2_sha256':hashlib.sha256(new.read_bytes()).hexdigest()},indent=2)+'\n').encode())
print(json.dumps({'prepared':str(new),'original_preserved':True}))
