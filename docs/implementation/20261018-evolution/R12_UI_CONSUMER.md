# R12: consumer funcional, previo a composición29

Base66 y checkpoint de contexto `146d873` en el worktree aislado
`F:/mb-r12-ui-20261019`. Se fija la adenda API v1 RAW SHA256
`407eedd99955b33d8d267ac8421b1cac4ad674f65c38f0c12afca1dd9617499a`,
sin modificar el contrato v2. Este lote no integra backend29 ni MAIN.

Las tres páginas están montadas en la rama UI: profesional por cliente,
aceptación first-party y lista/reader del destinatario. Las entradas nuevas de
navegación abren ese espacio separado. Cada fila de un plan profesional propone
su Plan ID exacto; no lo publica. El servidor sigue verificando cliente/dueño,
capacidades, versiones y destinatario. No se añaden permisos a auth/me ni se
convierten vínculos en acceso a cartera, equipo, diario o export personal.

La emisión captura correo y request_key en memoria; un ACK perdido conserva
esa misma solicitud. No permite editar su destinatario en un reintento ni
manda correo automáticamente. Rotación, revocación, publicación, reemplazo y
retirada requieren acción y versiones observadas; un resultado incierto
bloquea nuevas mutaciones hasta reconsultar. Las confirmaciones distinguen
solicitud recibida de entrega de correo. Aceptar es un botón aparte de
inspeccionar; login/registro normales no aceptan ni transportan el bearer.

La lista lee una página de cien, conserva filas/cursor al fallar y carga otra
sólo por clic. El reader construye nodos con textContent para las cuatro comidas
fijas o por opciones y no registra consumo. Una cuenta OWNER legítima puede
ser destinataria sin cambiar sus permisos personales. La retirada de un
consentimiento conocido no depende de poder descargar su publicación.

PDF siempre usa link_id/publication_id y el transporte autorizado actual,
nunca pdf_url del DTO, ruta profesional, object key o latest. Valida MIME,
firma y hasta64MiB por streaming antes de crear Blob. Revisión y contexto
canónico se validan antes/después de awaits y antes de Blob/descarga/DOM. Cambiar
cuenta o contexto descarta respuestas y limpia estado/URLs; los escritores sin
evento siguen limitados al siguiente check, como documenta readiness.

## Evidencia y límites de esta foto

- 76 VM: 26 contexto, 15 fragmento exacto, 20 helpers/stream PDF y15 consumers
  con DOM mínimo. Transportes/Storage de estas pruebas son sintéticos.
- 10 HTTP de composición de las tres páginas/estáticos y rutas únicas, ambas
  factories en base28. No ejercitan API29.
- Navegador: cuatro grupos/cinco pantallas a1440/390/320, axe AA0, desborde0 y
  pageerrors0. Registro VIEWER/OWNER, auth y páginas son HTTP reales base28;
  todos los recursos R12, menú, recibos y PDF son dobles declarados. No acredita
  email exacto, grants, cuotas, worker, triggers ni aislamiento29.
- El primer navegador falló en preparación: esperaba Api en login, que no lo
  carga; no alcanzó R12. Driver original RAW y reporte conservados. El primer
  VM DOM falló por confundir data-client-id con id en su parser; sólo ese
  harness se corrigió. El primer test HTTP de unicidad no expandía los routers
  lazy de FastAPI; sus asserts se conservaron al usar el iterador efectivo.
- Después del navegador se movió la validación del borrador al guard de sesión
  y se añadió novalidate. Los dos cuerpos anteriores se recuperaron invirtiendo
  exactamente ese patch en copias, con SHA idénticos al startup del fixture.
  El nuevo canario VM impide incluso leer ese borrador tras cambio de cuenta.
  El navegador registrado es anterior a ese delta; no se presenta como browser
  final del candidato compuesto. Las 76 VM y10 HTTP finales sí usan el cuerpo
  actual. La siguiente tanda real29 debe cubrir el cuerpo final.

El fixture8782 preparó exclusivamente metadata ORM SQLite temporal de revisión
esperada `20261019_account_recovery` (26 tablas); no ejecutó migración29. Chrome
cerró y se detuvo sólo su listener identificado PID29452/sesión45711. No se
tocaron8776 ni otros servicios. QEMU/Ops quedó reservado al coordinador después.

Backend debe entregar commits coreV2/API/restore congelados antes de la
composición autorizada. Siguen pendientes auth/consumo/email proof y
publicación/PDF/worker reales, destinos OWNER propio/externo, revocación,
errores y revisión independiente. La integración del séptimo conjunto de
exportación fue autorizada después como delta separado; este commit no afirma
que el controlador de exportación lo incluya. R14/R25 siguen pendientes de
contrato e integración específicos.
