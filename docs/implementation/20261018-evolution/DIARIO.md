# R14: diario persistido y consumo

Backend integrado en423296f, revisión `20261019_personal_diary` posterior a publicación26. Añade `personal_diary_days`:26 tablas de negocio y20 familias con RLS. La interfaz se integró después de corregir y revisar sus negativos de exportación/logout; permanecen otros criterios de R14 y de contexto del gimnasio.

`web/personal_diary_schemas.py` valida la selección de alimentos y cantidades del registro. `web/services/personal_diary_service.py` resuelve fecha local `America/Mexico_City` y una copia estructurada del alimento/menú procedente del plan del servidor. Rechaza fecha futura, rangos de consulta excesivos, números no finitos y selección que no pueda verificarse contra ese plan. No toma macros calculados por el navegador como autoridad ni convierte notas en restricciones clínicas.

Las rutas verifican principal vigente y pertenencia del plan antes de resolver una copia desde el servidor. La copia de consumo persiste aunque se borre o regenere el plan; no depende de una FK hacia el plan original. La fila es única por sujeto y fecha local, y PATCH exige versión con actualización atómica. Un GET de día ausente devuelve versión virtual0 sin crear filas. El calendario acepta hasta62 días y usa `America/Mexico_City`; agua0..20000ml, comidas64KiB y cuerpo de escritura16KiB tienen límites explícitos. No se acepta un `gym_id` arbitrario de la UI.

El contexto personal exige un principal válido sin el rol OWNER ambiguo del legado, o un miembro profesional vigente actuando en su espacio propio. La combinación histórica OWNER/tipo usuario se retiene con409 `diary_context_requires_review`; no se adopta cartera ni se cambia el rol automáticamente. El cierre de membresía invalida la sesión anterior y conserva el diario personal después de una nueva autenticación.

La exportación personal incluye una sexta colección `personal_diary`, con cursor de fecha exclusivo `after_diary`, límite1..200 y presupuesto128KiB por colección. Los totales provienen de los consumos registrados; marcar completado exige una copia almacenada y no convierte la acción en un diagnóstico clínico.

QA aceptó141 casos HTTP/SQLite,33 de migraciones/PostgreSQL y una restauración propia de27 poblada. Seguridad aceptó34 controles propios e históricos. Las78 fuentes del freeze permanecieron estables. La restauración preservó las26 tablas,20 familias RLS, cinco días de dos sujetos, agua/versiones/fechas/copias después de borrar un plan y todos los contratos anteriores de objetos, cuotas y relaciones. El fixture26 histórico permanece intacto; la aceptación de27 usa `tests/integration_diary_restore_review.py`. Evidencia: `evidence/qa-diary27-independent/qa-diary27-final-source.json` y `evidence/backend-diary-security-review/`.

QA revisó27 pruebas del autor y añadió ocho. Un JSON legado de5000 niveles reprodujo `RecursionError`; el lector ahora lo traduce al mismo409 `diary_source_unavailable` que otros cuerpos inválidos. Las35 pruebas finales independientes pasan con cuatro fuentes estables, en `evidence/personal-diary-values-independent-source.json`. La primera sonda de2000 niveles no reproducía el fallo en Python3.12 y se conserva como etapa, separada del caso rojo válido.

El diario previo de localStorage carece de identidad verificable en sus claves. No se importa, asigna a una cuenta, exporta ni elimina. La transición de ese legado requiere selección explícita de alcance y conserva los datos. No se inventó una política de conservación ni una promesa clínica de consumo/agua.

## Interfaz final integrada

e0f74da/06d291b/6abe08c conectan lectura/escritura CAS,conflictos/calendario y exportación al servidor. Un cambio de sesión/rol/equipo/SV o fallo Storage invalida caché,URLs,contadores y acciones antes de aceptar continuaciones. Guards tras controles cubren invalidación síncrona antes de clic. Logout requiere success===true emitido tras commit; mensaje histórico solo no confirma cierre. No se adopta/lee/elimina seguimiento localStorage sin identidad verificable.

162VM únicos,seguridad25controles yQA25grupos/12pantallas sobre57fuentes quiet;0pageErrors/axe/desborde del alcance. [QA](evidence/ux/diary-ui-bf46-independent-20261019-qa/run2/diary-ui-bf46-independent-source.json),[seguridad](evidence/ux/diary-ui-controls-security-source.json). Cuatro rojos606,dos guard87 y driveroriginal permanecen intactos; adaptación de positivos para nuevo ACK está documentada. Reload/cross-tab/escritores directos y accesibilidad integral del perfil siguen abiertos; no se acredita R14 completo por cerrar SEC04.
