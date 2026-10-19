# CI29 archive: árbol original y blobs exactos antes de ejecutar historia

Entrega de autor desde1dc87ef5, sin composición CI2 ni integración MAIN. Cambios:
tests/run_reviewed_ci28.py; sólo su nuevo hash en PINNED_CURRENT_GATES de
verify_member_links_ci.py; regresiones propias. Checker/criterios/historia66,
workflow, aserciones históricas, modelo, API y DB quedan intactos.

El driver independiente02b7ef original se conserva en before-exact.zip. La copia
de ejecución sólo cambia tres asignaciones de paths(root/out/temp) a recursos
propios; AST restante idéntica. Antes repite7/10: replace-ref sustituye código,
export-ignore omite una fixture y C:/escape se remapea dentro del destino. Ese
último caso no demuestra escritura exterior. Después los mismos10criterios pasan.
El clon atacante y su replace-ref se crearon exclusivamente en Temp propia;
ninguna configuración/ref de fuente original o QA se modifica.

Cada lectura Git usa --no-replace-objects: merge-base, rev-parse, ls-tree y
archive. La identidad del árbol viene de ls-tree -r -z --long sobre el pin66,
independiente del tar. Sólo modos100644/100755 y objetos blob, OID SHA1 completo,
tamaño decimal y paths relativos canónicos; rechaza colon, backslash, controles,
absolutos, componentes padre y alias locales. Directorios sólo los derivados del
árbol. Cada archivo debe aparecer una vez, nombre/modo/tamaño exactos, y hash
Git SHA1(headerblob+bytes) idéntico al OID. El conjunto final debe ser completo.
SHA1 aquí implementa el protocolo de objeto Git, no un algoritmo nuevo de tokens.
[Git ls-tree](https://git-scm.com/docs/git-ls-tree).

El tar no es autoridad de contenido. export-ignore/subst se detectan como omisión
o bytes distintos y rechazan la extracción antes de ejecutar historia. Replacements
se ignoran en todas las lecturas: el canario final materializa el verificador real
39395c92, no el stub, y valida4433blobs. Los atributos de exportación son parte
del comportamiento documentado de archive, por eso el manifest del árbol se lee
separadamente. [Git archive](https://git-scm.com/docs/git-archive).

Se preserva el primer candidato: sus negativos10/10 aún no acreditaban positivo.
El ensayo positivo encontró core.autocrlf=true en Windows convirtiendo .coveragerc
225bytes de objeto a238bytes tar. No se normalizan bytes recibidos para fingir
coincidencia. Overrides efímeros -c core.autocrlf=false/core.eol=lf/tar.umask=0022
producen bytes/modos canónicos sin escribir configuración. Un atributo externo
que cambie realmente contenido sigue rechazado. Las entradas validadas se crean
con exclusividad, sin overwrite; árboles parciales fallidos no se borran.

Pruebas propias14 con repositorios Git reales de Temp: positivo con autocrlf y
modo ejecutable, atributos omitidos/sustituidos, bytes/mode/size alterados, archivo
duplicado/ausente/extra, directorio extra/duplicado y tree listing incompleto,
symlink/gitlink no admitidos. Las4trustunits anteriores se ejecutan sin cambios:
18passed/0skip en7.47s. Los fallos dejan el primer blob válido en el árbol parcial.
Config y refs de los repos propios se comparan antes/después de materialize.

Positivo real:4433archivos del pin66 verificados y guard histórico puro exit0,
con sus fuentes/aserciones originales. Guard actual --verify-only también exit0,
26reports/20canarios delta; no ejecuta de nuevo los55canarios de report ni27inertes,
PG o Chrome.789fuentes/89paquetes quietos en las tres tandas finales y pip check0.
Ruff F/E9 pasa. El checker conserva su hash y el verifier sólo cambia el hash del
runner: semantic-proof.json demuestra igualdad completa del resto.

Esto no acepta Actions ni CIglobal, ni repite navegador/DB/runtime. QA independiente
revisará este commit y root compondrá con CI2 preservando sus seis helpers y ocho
anchors totales. Pin66 y sus aserciones no se reescriben; no se hace checkout sobre
otra rama, fetch, configuración global, delete ni reparación de repositorio.
