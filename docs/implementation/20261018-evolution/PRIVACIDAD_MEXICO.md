# Borrador interno: privacidad y operación en México

Estado: dependiente de datos del negocio y revisión jurídica. No es un aviso público, no habilita nuevos tratamientos y no crea promesas operativas.

Fecha de contraste:23-10-2026. México es el mercado inicial confirmado por el usuario. Se conserva el alcance exclusivo web. Este texto es una propuesta documental/funcional separada; no cambia criterios, estados o políticas canónicas, ni certifica cumplimiento. Requiere completar decisiones comerciales y revisión jurídica antes de publicar un aviso o habilitar nuevos tratamientos. No se inventan responsable, domicilio, contacto, proveedores, fundamento de excepción ni duración de conservación.

## Marco de referencia para el servicio web

El mercado inicial confirmado es México. Para un operador privado se contrastó la LFPDPPP de20-03-2025, texto oficial con reforma14-11-2025. La autoridad indicada por esa ley es la Secretaría Anticorrupción y Buen Gobierno; no se ofrecerá al usuario un procedimiento del INAI extinguido ni se confundirá el régimen de particulares con el de sujetos obligados. Deben validarse por separado los roles contractuales del operador y de cada gimnasio/profesional. [Ley vigente](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf), [decreto de2025](https://sidof.segob.gob.mx/notas/docFuente/5752569), [organización de la autoridad](https://sidof.segob.gob.mx/notas/docFuente/5752650).

El criterio de diseño requiere aviso antes de recopilar; en captura digital, versión simplificada con categorías, finalidades y medios de limitación, enlazada al integral (arts14–16). Para información que revele salud debe resolverse consentimiento expreso/escrito y su mecanismo, o excepción jurídicamente documentada (arts2,7–9). El trámite ARCO necesita persona/departamento y canal verificable, además de la exportación parcial:20días hábiles para determinar y15para ejecutar si procede; ampliación única justificada (arts2,29,31). Transferencias se revisan conforme arts35–36. Un incidente significativo exige comunicación inmediata al titular, sin trasladar automáticamente una regla extranjera72h (art19). [Texto oficial](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf).

La documentación técnica ya preserva correctamente los límites: exportar no es atender íntegramente ARCO; revocar progreso no es consentir todo tratamiento; soft delete no es supresión; TTL de tokens no es política de retención; restore no prueba purga. Esos límites siguen vigentes. No se cambia la evidencia histórica ni se afirma un gate de privacidad nuevo.

## Delta observado y mejora concreta

| Área | Evidencia física leída | Cambio propuesto | Dependencia para cerrarlo |
|---|---|---|---|
| Aviso público | registro.html no contiene enlace/aviso; RegistroRequest no recibe versión/finalidad. La búsqueda en templates y rutas revisadas sólo identifica permisos de progreso/exportación. | Preparar página pública versionada y bloque simplificado en registro y antes del perfil/cliente/diario que recabe datos. Enlazarla también desde el perfil. No considerar un checkbox general como prueba suficiente. | Identidad/domicilio/contacto y mapa real de finalidades/roles. |
| Datos que revelen salud | NutritionProfileUpdate admite edad, peso, estatura, grasa, objetivo y notas; modelos incluyen medidas/planes/diario. | Revisar clasificación por campo/contexto y justificar finalidad. Recabar decisión específica antes del tratamiento que la requiera; conservar sujeto, finalidad, versión/hash del texto, acción autenticada y fecha, sin copiar contenido clínico al log. | Revisión del fundamento/excepciones y mecanismo escrito/autenticación; decidir menores. |
| Consentimiento acotado | ProgressConsent/progress_share gestionan categorías/periodo/vínculo y revocación; PRIVACIDAD.md declara que no son aviso general. | Mantenerlos separados. Una nueva evidencia de tratamiento no se deduce de login, Google, email confirmado, una invitación ni datos legados. No hacer backfill de aceptaciones. | Texto/finalidades aprobados y decisión jurídica sobre el mecanismo; implementación posterior autorizada. |
| ARCO real | privacy.py expone GET personal paginado; documentos/PDF, algunas categorías y contenido grande requieren canal autorizado. | Instalar el procedimiento de abajo con expediente, acreditación, calendario y resolución. El JSON sirve como material de una respuesta, no como cierre automático del caso. | Responsable operativo/contacto y canal seguro; capacidad para reunir categorías excluidas. |
| Encargados/terceros | Inventario técnico contiene hosting/objetos, correo, telemetría y cobros; región/contratos reales no constan. | Completar la matriz propuesta, por flujo y destinatario. No llamar transferencia a toda remisión ni llamar encargado a todo SDK. | Contratos y servicios efectivamente utilizados, países, subcontratación, borrado y salidas. |
| Conservación/cancelación | Ruta DELETE de cliente se denomina soft delete; PRIVACIDAD.md registra datos/objetos/backups persistentes y purgas pendientes. | Aprobar conservación por categoría/finalidad, bloqueo y eliminación verificable en DB/objetos/copies; controlar que restore no reactive una supresión vigente. | Plazos/fundamentos contractuales/fiscales/sanitarios aplicables, custodios y ejecución posterior. |
| Incidentes | Hay minimización técnica y alertas locales; las fuentes revisadas no acreditan canal operativo mexicano de notificación a titulares. | Añadir triage, evaluación de afectación, decisión/acuse de comunicación y responsables de contacto. No asumir que un log o un notifier demuestra recepción. | Personas/canal/proveedor real de comunicación y revisión de obligaciones específicas. |

Estas filas son referencias del paquete, no nuevos IDs del registro de trazabilidad.

## Candidato de aviso: estructura lista para completar, no publicar con blancos

**Aviso de privacidad de [NOMBRE COMPLETO O RAZÓN SOCIAL DEL RESPONSABLE], versión [VERSIÓN/FECHA].** Domicilio para notificaciones:[DOMICILIO COMPLETO]. Contacto de datos personales:[CANAL OPERATIVO VERIFICADO]. Aplicación:[DOMINIO PUBLICADO]. Para la cartera profesional, identificar además [RESPONSABLE DEL GIMNASIO/PROFESIONAL Y ALCANCE DEL OPERADOR], según el contrato real.

**Datos y finalidades.** Completar una lista cerrada por formulario: cuenta/contacto; información técnica de sesión y seguridad; perfil y planes nutricionales; medidas/progreso; diario; cobros y facturación cuando se utilicen. Marcar expresamente las categorías que revelen salud. Explicar para cada una su finalidad concreta y si necesita consentimiento. Separar cualquier finalidad secundaria confirmada y su mecanismo de negativa; no añadir marketing por suposición ni declarar que no existe sin revisión del negocio.

**Compartir y proveedores.** Incorporar destinatario/categoría, datos, finalidad, país y rol aprobados en la matriz. Distinguir proveedores por cuenta del responsable de receptores que decidan fines propios. Identificar los vínculos opcionales con el profesional y su revocación; no prometer que revocar retira las copias ya comunicadas. No usar una frase global «nunca compartimos datos».

**Tus opciones.** Describir [CANAL ARCO Y ACREDITACIÓN], limitación de uso/divulgación y revocación del consentimiento aplicable. Informar de consecuencias reales y restricciones justificadas, sin reducir el trámite a poder iniciar sesión. La descarga del perfil tiene un alcance técnico declarado; no sustituye las demás solicitudes.

**Conservación y cambios.** Publicar [CRITERIOS/PLAZOS APROBADOS POR CATEGORÍA Y EXCEPCIONES] y [MEDIO DE COMUNICACIÓN DE CAMBIOS], después de comprobar que operación/código pueden cumplirlos. Explicar cookies de sesión y almacenamiento realmente utilizado, sin prometer que logout elimina la información del servidor o el diario local histórico. Mantener acceso al aviso integral y a versiones utilizadas para evidencia.

Los [Lineamientos oficiales del aviso](https://sidof.segob.gob.mx/notas/docFuente/5284966) detallan identidad, finalidades diferenciadas, transferencias, revocación, derechos, mecanismos automáticos y cambios. Sus referencias antiguas y su antiguo mínimo del simplificado no deben copiarse sin contrastar la nueva ley: el art16 vigente remite a las fraccionesI–IV del art15. La estructura anterior usa esas categorías; falta el contenido del negocio, no se rellena con una plantilla comercial ajena.

## Procedimiento ARCO propuesto para operación

1. Recibir por [CANAL] y registrar folio, fecha de recepción, derecho, medio de respuesta y responsable del caso. No pedir de entrada copias clínicas ni documentos de identidad por correo sin canal seguro.
2. Acreditar titular/representante por un medio proporcional revisado; la falta de acceso a la cuenta no autoriza a descartar el caso. Separar el expediente de la telemetría general y limitar acceso por caso/tenant. No habilitar búsquedas universales por email ni bypassRLS.
3. Identificar categorías y custodios: cuenta, espacio personal, cartera profesional, objetos, diario, consentimientos, registros y proveedores. Revisar datos de terceros; entregar sólo lo autorizado. Contenido marcado para revisión en exportación entra en la lista de trabajo, no se omite silenciosamente.
4. Asignar vencimientos y seguimiento conforme al calendario jurídico aplicable y comunicar determinación. Conservar motivo/soporte de negativa total o parcial, así como cualquier ampliación justificada; no inventar un SLA contractual para sustituir plazos legales.
5. Ejecutar resolución por categoría: acceso, corrección, oposición o cancelación con bloqueo/retenciones justificadas. Para borrado, un fallo de objeto o destino deja el caso pendiente, no «completado». Verificar efectos en destinatarios que sigan tratando datos y en restauraciones posteriores.
6. Comunicar resultado por canal acreditado y guardar evidencia mínima de entrega/ejecución. Aprobar retención del propio expediente y de su acreditación; no conservar documentos indefinidamente ni asumir que un email enviado fue recibido.

## Matriz contractual y de incidentes que puede completarse ahora

Una fila por finalidad/flujo real: responsable que decide finalidad; encargado o tercero receptor; datos mínimos; sistema/país; instrucciones/contrato; subencargados autorizados; seguridad/confidencialidad; asistenciaARCO; incidentes/avisos; salida/devolución/supresión; evidencia contractual. Para cuenta/cobros, servicio personal y cartera del gimnasio, la respuesta puede ser distinta. Tener una misma base/tenant no determina por sí solo el rol legal. Los arts49–54 del [Reglamento publicado por Cámara como vigente](https://www.diputados.gob.mx/LeyesBiblio/regley/Reg_LFPDPPP.pdf) desarrollan esa relación y nube; aplicar el detalle compatible con la ley nueva, sin reutilizar autoridades/numeración de2010. La ubicación extranjera tampoco decide sola si es remisión o transferencia.

En incidente, abrir caso, contener y preservar evidencia sin contenido de salud en logs generales; evaluar categorías/personas/impacto; escalar a [RESPONSABLE]; documentar la decisión y comunicación aplicable; coordinar encargados y comprobar acuses. Las rutas, interlocutores y canales externos quedan pendientes del negocio. No se ha contactado a ninguna autoridad, proveedor o titular.

## Orden finito de aplicación posterior

Primero completar datos del negocio y mapa por dominio; después revisar aviso/consentimiento y contratos con asesoría local. Root podrá incorporar este anexo y el registro de decisiones sin afirmar que ya están implementados. La implementación posterior puede acotarse a página pública+enlaces y expediente/registro específico revisado; no se añade hoy código, tablas, checkboxes, purgas, envíos o pruebas. La política de conservación y el plan de cancelación requieren autorización separada y resultado verificable. No se cierran R20/R31 ni se cambia ningún total del registro por este análisis.
