# R12: séptimo conjunto de exportación

Delta separado del consumer `93f7483`. Backend y coordinación confirmaron el
contrato adicional durante esta fase; la adenda API v1 RAW407eedd9 se conserva
intacta. No se afirma que esa adenda anterior ya contuviera todos los campos de
scope ahora acordados ni que backend29 esté compuesto en esta rama.

Se incluye `member_links:{records,next_after}` con `after_member_link` UUID y
limit compartido1..200. Se preserva el caso del cursor recibido. Scope exige
`coverage:account_persisted_personal_space_and_active_member_link_metadata` y
`member_links:active_recipient_metadata_only`, format_version1. No se acepta
silenciosamente un servidor de seis conjuntos ni se declara completo si el
séptimo tiene continuación. Si un conjunto ya terminó, las partes posteriores
lo omiten y el manifiesto lo referencia como incluido antes.

Los registros admiten sólo id/status/version/gym_name/client_display_name/
accepted_at/publication; publicación nula o id/version/published_at. Deben ser
vínculos activos propios autorizados. Se rechazan campos extra como invitación,
recipient_user_id, objeto, ruta o descriptor y no se recopila contenido de planes
profesionales/PDF. Cada sección tiene un límite de131072 bytes UTF8 y el payload
total933888; un exceso rechaza la parte entera antes de construir Blob. Un
error conserva las partes ya preparadas, contadores y cursor anterior para un
reintento explícito. Los datos/cursores no se escriben en Storage.

El nuevo bloque de `/mis-vinculos` usa el contexto canónico `Api.vinculos`
independiente del espacio personal. OWNER profesional legítimo puede exportar
metadatos propios con `personal_space:false` y los seis conjuntos personales
vacíos; una respuesta que contradiga esa barrera se rechaza íntegra. No cambia
su perfil, cartera, rol ni los permisos de exportación del servidor. El bloque
existente del perfil mantiene su contexto personal y añade el séptimo conjunto
y una explicación visible de su alcance. No se promete exportación de vínculos
revocados, borrado, conservación o entrega de archivos al usuario.

## Comprobaciones

El driver nuevo compila las21 aserciones anteriores (17 contexto y4 controles)
sin editar sus fuentes o aserciones: sólo adapta el DTO/fixture aditivo en
memoria. Añade11 casos propios de cursor, filtrado por partes, OWNER, esquema,
error/reintento, Unicode y presupuestos. Resultado final32/32.

Se preservan el primer before5/29, un replay pareado del driver31 sobre copias
RAW del consumer93 (6/31) y el negativo adicional OWNER31/32 sobre la versión
previa al rechazo de scope contradictorio. Los reportes no se confunden como
una sola ejecución con número constante de casos. ZIPs contienen los cuerpos
ejecutados y el driver; no se inventa historia Git.

Los diez tests HTTP de composición de páginas/estáticos en ambas factories
también pasan con el bloque nuevo, en base28. No prueban respuestas reales del
export29. Syntax Node pasa. No se abrió Chrome durante QEMU/Ops; accesibilidad,
descargas y autorización reales del séptimo conjunto requieren la futura
composición del backend congelado y revisión independiente. El historial del
consumer93 y sus pruebas de navegador sintéticas permanecen intactos.
