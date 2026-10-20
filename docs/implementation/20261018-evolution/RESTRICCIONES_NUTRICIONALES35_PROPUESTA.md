# R33: declaración estructurada y límite de automatización

Estado: precursor de dominio probado localmente; propuesta de integración35.
La aplicación actual sigue en33 y el backend34 todavía se valida. Este documento
no describe una API, migración, UI o aprobación profesional ya disponibles.

`core/nutrition_restrictions.py` recibe el catálogo explícito, las exclusiones
existentes, una declaración de alergias y una solicitud de revisión profesional.
No interpreta notas, nombres de alimentos como ingredientes, diagnósticos o
factores de facturación. Los alimentos declarados son identificadores del catálogo;
no constituyen una taxonomía de alérgenos ni una garantía sobre contaminación
cruzada. `other_reported` permite declarar otra alergia sin capturar texto clínico.

La declaración cerrada versión1 contiene `version`, `status`, `foods` y
`other_reported`. `status` admite `not_reported`, `none_reported` o `reported`.
El primero conserva la información desconocida del legado. El segundo registra
lo declarado por la persona; no acredita ausencia de alergias. `reported` exige
al menos un alimento o `other_reported=true`. Se rechazan contradicciones,
coerciones, alimentos desconocidos, más de250 entradas y propiedades adicionales,
incluidas supuestas aprobaciones profesionales. Las copias internas son inmutables.

Una alergia declarada o una solicitud de revisión profesional impide generar
automáticamente, independientemente de plan, rol o precio. El encargo exige dejar
fuera del automatismo clínico aquello que no tenga validación profesional real.
El motor disponible no tiene ese modelo validado: ninguna bandera enviada por la
UI puede habilitarlo. El trabajo posterior de especialistas requiere su evidencia
propia y una evolución revisada del contrato. No se simula aquí ese dictamen.

Las exclusiones explícitas actuales siguen usando el catálogo inmutable de cada
solicitud. Una categoría sin alternativas conserva su error de dominio. No se
restauran alimentos excluidos. La declaración desconocida mantiene el uso básico
existente sin presentarlo como adecuación clínica.

La aplicación35 propuesta persistirá una declaración versionada junto al perfil,
sin duplicar `alimentos_excluidos`. Los campos omitidos o null de una actualización
parcial no borrarán declaraciones existentes. Una edición explícita debe guardar
un objeto completo válido. La exportación personal incluirá los datos propios;
no se añadirán estos campos a analítica, logs o mensajes de seguimiento.

El adaptador verificará el límite antes de reservar cuota y nuevamente en el
worker. Antes de publicar deberá comparar las restricciones capturadas con las
actuales bajo la autorización y bloqueo de escritura del cliente. El dominio
incluye `require_current`: un cambio produce `nutrition_restrictions_changed`,
sin adoptar silenciosamente los nuevos datos. Su digest es dato sensible derivado;
no se envía a logs o analítica. La integración debe comprobar compensación de
cuotas, objetos pendientes y ausencia de publicación ante cambio o error.

La DDL35 está reservada a coordinación y esperará el candidato34 identificable.
No se modifica la cadena Alembic ni los contratos22–34 para este precursor.
API/UI, PostgreSQL, desktop, carrera de publicación y revisión independiente
siguen pendientes. La prueba local del precursor y regresiones existentes no
constituye revisión clínica ni aceptación integrada deR33.

La segunda fase local conecta ambos constructores del motor a la declaración
capturada de `ClienteEvaluacion`. El guard se ejecuta antes de seeds, ajustes,
rotación y filesystem; un catálogo suministrado no lo evita. Las exclusiones
del perfil se combinan con las del catálogo sin restaurar alimentos ni alterar
datos compartidos. La declaración queda fuera de repr. Diez regresiones de esa
frontera fallan antes y pasan después; la fase final tiene79 casos verdes,
incluidos dos planes reales que conservan ambas listas de exclusiones. No es
todavía persistencia, API, UI o aceptación de desktop.

El objeto de perfil propuesto `restricciones_nutricionales` contiene exactamente
`version: 1`, `allergies` (la declaración cerrada anterior) y
`professional_review_requested` booleano estricto. No repite exclusiones. Los
métodos puros `from_declaration` y `declaration_payload` validan esa forma y
devuelven copias independientes; no añaden campos de aprobación profesional.
