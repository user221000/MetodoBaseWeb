# R24: porciones, consumo explícito y compra por periodo

Base de autor: `efbc020226c4d9100feefb639823d21c3eba4610`, rama aislada `implementation/r24-daily-plan-20261019`. No modifica MAIN, `api.js`, DDL, migraciones, MFA, cuotas, proveedores o CI. R24 permanece **parcial**: faltan nuevas sustituciones con restricciones y verificación final; R33 no constituye validación clínica independiente y R31 no define aquí un plazo de retención.

## Criterios y recorrido anterior

Se conservan los criterios originales de `docs/audit/2026-10-18/ROADMAP_PRIORIZADO.md` (R24) y `ux/INFORME_UX.md` (UX02, UX10, UX17). La copia RAW y el inventario antes de editar están en `evidence/r24/before/raw-source.zip` y `source.json`. El SSR de ambas factories es evidencia de HTML servidor, sin presentarlo como navegador ejecutado.

Antes: `/mi-plan` redondeaba gramos y mostraba una cantidad recomendada inventada para vegetales. No había una compra por periodo; el lector R12 sólo permitía consultar. R14 ya separaba snapshots registrados de la marca de completado y ya persistía agua/diario por sujeto propio. Se conserva esa separación. La selección del menú fijo no estaba representada en el DTO. Los cinco rojos HTTP/SSR y los 23 rojos por ausencia del nuevo módulo puro se preservan con sus alcances distintos.

## Fuentes y presentación

`/mi-plan` utiliza el resultado personal autorizado existente (`GET /api/usuario/mi-plan`), `plan_id`, `meta.fecha` y catálogo personal actual. `/mis-vinculos` utiliza exclusivamente la publicación vigente leída por `GET /api/usuario/vinculos/{link_id}/plan`: `link.version`, `publication.id/version/source_plan_id/published_at`. El profesional publica por la acción R12 existente; generar, consultar o abrir un selector no publica ni registra consumo.

Cuatro comidas: desayuno, almuerzo, comida y cena. Se muestran gramos numéricos finitos positivos y equivalencias como texto de la fuente. Una comida sin estructura verificable muestra indisponibilidad; no se infiere una receta o una porción. Se retiran las recomendaciones genéricas y promesas de aplicar exclusiones de la plantilla tocada: preferencias guardadas no acreditan restricciones o alergias verificadas. No se añade orientación clínica.

Los módulos nuevos utilizan el transporte cercado existente. Antes/después de cada await y antes de renderizar se comprueban contexto, identidad persistida/revisión y vigencia de la operación. El evento central de sesión, Storage y pagehide descartan inmediatamente fuente, selección, listas y fechas en RAM. No guardan DTO sanitario, cantidades, borradores o claves de operación en Storage. Las claves legacy sin identidad no se leen/importan/asignan/eliminan.

## Compra por periodo

El usuario elige expresamente las opciones/vegetales o el menú fijo completo y el periodo inclusivo. Se multiplica esa selección una vez por día del periodo; es un borrador de compra, no una recomendación de repetir el menú ni un consumo guardado. La ventana de hasta 62 días reutiliza el límite técnico del calendario R14 y evita iteraciones/transferencias sin cota; no es una política comercial.

Sólo se agrupan identidad de catálogo confirmada igual + unidad `g` + gramos finitos. Si no hay identidad confirmada, incluso etiquetas iguales permanecen como partidas separadas. No se parsean equivalencias, platos libres, medidas caseras o gramos escritos como texto. El catálogo confirmado no cambia la elección ni mueve el foco. Un error de revalidación se muestra como tal; no autoriza calcular usando una fuente retirada. Un cambio de publicación exige nueva consulta y elección.

La consulta separada de alimentos registrados usa el calendario personal autorizado y suma únicamente snapshots guardados, aunque `completed=false`. No usa opciones del plan simplemente mostrado. Los totales nutricionales de consumo siguen viniendo del servidor; el borrador no inventa macros.

## Consumo de publicación: operación aditiva sin DDL

`PATCH /api/usuario/diario/{YYYY-MM-DD}` añade:

```json
{
  "operation": "publication_meal",
  "source_kind": "publication",
  "expected_version": 0,
  "link_id": "00000000-0000-0000-0000-000000000001",
  "publication_id": "00000000-0000-0000-0000-000000000002",
  "expected_link_version": 2,
  "expected_publication_version": 1,
  "meal": "desayuno",
  "selections": {"proteinas": 0, "include_vegetables": false}
}
```

IDs canónicos UUID minúsculos, versiones enteras estrictas. `include_fixed_menu:true` es una selección explícita alternativa; no puede mezclarse con grupos/vegetales. Sólo estructura fija numérica e identidades de catálogo resolubles generan snapshot. No se aceptan alimentos, macros, totales, usuario, gimnasio o perfil en el cuerpo. Los menús de opciones y la selección vacía explícita preexistente R14 conservan su contrato; abrir nunca escribe un cero.

Servidor: barrera personal persistida primero; cuentas actor/gimnasio/parent ordenadas como R12, después vínculo y publicación bajo locks compatibles. Revalida actor destinatario aceptado, fuente canónica, vínculo activo y versiones/ID exactos; usa la proyección inmutable validada por SHA y FKs de la publicación, no el Plan profesional bruto ni un modelo con dueño inventado. No modifica cartera. Fecha y CAS son R14, con día de Ciudad de México del servidor. Extrae el DTO exacto antes del único commit; no depende de lecturas ORM lazy tras limpiar contexto.

El reader añade `capabilities.record_personal_consumption` sin ampliar los permisos del vínculo. OWNER legítimo puede leer su publicación autorizada, pero el vínculo no crea ni adopta un espacio personal de diario. `share_personal_diary` sigue siendo `false`.

Snapshot: formato anterior intacto; opcional `source_context` con exactamente `kind,link_id,publication_id,link_version,publication_version,published_at`. Sólo alimentos elegidos/gramos/macros y metadatos mínimos, sin plan completo/notas/perfil profesional. Decoder estricto dual y export personal existente incluyen ese contexto sólo dentro del snapshot propio; presupuestos existentes sin aumento.

Retirada/revocación impide nuevas lecturas o consumo desde la fuente, también al reintentar; no borra retroactivamente un hecho personal ya confirmado. El usuario puede `remove_meal` explícito con `expected_version` y comida para retirar su propio snapshot sin necesitar acceso actual a esa fuente. Se conservan agua y otras comidas. R14 determina la persistencia existente; no se añade plazo de retención.

CAS409 conserva sólo borrador RAM, requiere reconsulta y decisión explícita. Una confirmación perdida503 o transporte ambiguo puede haber hecho commit: reconsulta antes de otra escritura, sin replay automático. Fuente ajena/retirada404, prueba obsoleta409, contenido no verificable409 y cuerpo inválido422 no crean un día. El servidor sigue siendo la autoridad; el browser sólo facilita estas operaciones.

## Sustituciones pendientes y propuesta concreta

La interfaz dice que nuevas sustituciones no están disponibles. Las alternativas ya incluidas en la fuente son opciones de esa fuente, sin certificación clínica nueva.

Un lote futuro deberá definir una consulta autenticada de candidatos ligada al mismo contexto/ID/versión de fuente y restricciones estructuradas persistidas (incluyendo la semántica de alergias/exclusiones). Debe verificar catálogo canónico y todas las restricciones por request y nuevamente al confirmar el resultado, con rechazo si fuente/restricciones cambiaron. La elección de un candidato no podrá mutar una publicación profesional ni reemplazar el consentimiento/publicación R12. Necesita pruebas de restricciones adversarias y revisión profesional real R33; ninguna de esas garantías se sustituye por copy, ranking local o notas libres.

## Verificación y límites

La [proyección pública del autor](evidence/r24-author-private-projection-20261019/manifest.json) conserva rojo/verde, fuentes, SSR, cantidades puras, consumidores en memoria y HTTP SQLite/PostgreSQL con migración30 real. Cuatro valores CSRF de SSR sintético se sustituyeron únicamente en esta proyección; los RAW originales permanecen privados y sus hashes se vinculan en projection.json. Los dos ZIP de código se inspeccionaron por entrada y se conservan byte a byte. Los casos VM no son HTTP. Las capturas/axe pertenecen únicamente al bloque inspeccionado y anchos declarados; revisión manual de teclado/foco no equivale a lector de pantalla. Cada base PostgreSQL propia registra cierre y ausencia. Los contratos R12, perfil independiente, PDF exacto y calendario R14 se conservan; no se repite una suite amplia ni se atribuye soporte Linux/desktop/producción.
