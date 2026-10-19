# R12: contrato de interfaz y preparación

Base de autoría: `66d9dec0e15dd873038bd248d3883daeeb27d4ca`, esquema28.
Worktree exclusivo: `F:/mb-r12-ui-20261019`, rama
`implementation/r12-member-ui-20261019`. Los comandos Git usan
`-c core.autocrlf=false -c core.longpaths=true`; no se cambia la configuración
compartida ni se escribe producto en MAIN.

Fuente normativa leída: `evidence/backend-r12-contract-v2.md`, SHA256
`3c28ccd2b784cbc028492ad5cb0ea427d74c3f488c241e7f57a24ecb14ff7a03`.
Backend confirmó que conserva sus rutas de la sección8 y que enviará ejemplos
estables aparte. Sus API/DTO todavía están en implementación: las pruebas VM
de esta fase son dobles de controlador, no pruebas HTTP ni E2E del producto.

## Pantallas y acciones

- `/clientes/{client_id}/vinculacion`: estado mínimo del vínculo del cliente
  autorizado. OWNER/ADMIN pueden solicitar una invitación a un correo escrito
  explícitamente, rotarla o revocar la relación. No se rellena el destinatario
  por coincidencia con el correo de Cliente, no se busca una cuenta por email y
  no se muestra bearer, enlace, hash ni existencia de una cuenta destinataria.
  Una respuesta202 se presenta como solicitud recibida, con entrega sin confirmar.
  Un reenvío es explícito y explica que invalida la invitación anterior.
- En esa misma página, OWNER/ADMIN/NUTRIOLOGO pueden seleccionar un Plan ID
  autorizado del cliente y publicar o reemplazar explícitamente con las
  versiones observadas. Generar, abrir o seleccionar un plan no publica nada.
  Retirar una publicación no borra el plan fuente. Se explica la diferencia
  entre publicación preparada para un vínculo pendiente y lectura disponible
  para un vínculo aceptado. VIEWER no obtiene botones de mutación.
- `/auth/accept-client-link`: página first-party con fragmento eliminado antes
  de cualquier I/O. El token vive sólo en memoria. La inspección autenticada no
  consume. Únicamente el contexto comprobado por el servidor muestra gimnasio,
  etiqueta del destinatario, caducidad y versión. Aceptar requiere confirmación
  explícita y no cambia cuenta, rol, equipo ni perfil. Sin sesión, los enlaces
  normales de login/registro explican que se debe volver a abrir el enlace
  original del correo después; no se transporta el bearer por return_to,
  query, Storage ni parámetros de registro.
- `/mis-vinculos`: lista acotada, con carga de otra página por acción, de los
  vínculos activos propios. Se elige un contexto de gimnasio explícito; menú y
  PDF pertenecen a la publicación exacta de ese vínculo. Un OWNER legítimo puede
  ser destinatario de su propio gimnasio o de otro sin adoptar cartera. Una
  publicación retirada falla visiblemente y no se sustituye por la más reciente.
  Desvincularse requiere confirmación y conserva cuenta, sesiones y datos
  personales. El perfil/diario/planes personales siguen en sus rutas actuales.

El nuevo contexto de API debe capturar revisión local y la identidad canónica
persistida (`id`, `tipo`, `role`, `team_gym_id`, `session_version`) de `/auth/me`.
No se usará `Api.usuario.contexto()` para R12: ese helper delimita el espacio
personal existente y excluye OWNER profesionales. R12 no elimina esa barrera.
Las capacidades recibidas sólo gobiernan la presentación; la API autoriza cada
recurso y mutación. Una heurística de rol o un identificador de URL no conceden
autoridad.

## Estados y protección de datos

Cada pantalla distingue consulta, acción en curso, resultado confirmado,
resultado incierto, conflicto, sin publicación, acceso no disponible y error
recuperable. Un fallo de red o ACK incierto no afirma aceptación, envío,
revocación o publicación: ofrece reconsultar. No hay repetición automática de
mutaciones ni de correo. Para emisión, el mismo intento conserva su clave sólo
en memoria; un destinatario nuevo exige una intención explícita distinta después
de resolver el intento anterior. Un conflicto de versión exige reconsulta y una
nueva confirmación; no reenvía un DTO actualizado silenciosamente.

Revisión/identidad se comprueban antes y después de cada await, antes de procesar
DTO, renderizar, crear Blob o iniciar descarga. Eventos de sesión/Storage,
cambio de contexto y pagehide invalidan sincrónicamente el estado; un fallo
Storage invalida cuando la comprobación lo detecta. Se cancela la continuidad y
se limpian nodos privados, cachés y URLs propias. Un escritor sin evento se
detecta en el siguiente check; no se promete observación inmediata de escritores
legacy externos. Los controles pueden invalidar sincrónicamente: se vuelve a
comprobar el ticket después de dibujarlos. No se guarda información sanitaria, token ni claves de
operación en localStorage/sessionStorage; las claves legacy no se leen, importan,
reasignan o borran.

El menú se construye con nodos y textContent, nunca innerHTML de JSON. PDF sólo
por link_id/publication_id y Bearer al reader de socio, con MIME/firma/tamaño
acotados, Blob temporal y revocación propia. No se acepta URL arbitraria,
object key, presign, ruta profesional o fallback latest.

Las pantallas nuevas tendrán etiquetas visibles, estado anunciado, errores
enfocables, controles nativos y confirmaciones operables con teclado; el foco
se devuelve al control de origen. El menú no presenta registrar consumo ni
compartir diario/progreso: R14/R25 necesitan integración y consentimiento
adicionales y siguen abiertos.

## Condiciones para conectar y validar

Antes del consumer HTTP se fijarán con backend: DTO exacto del estado
profesional, paginación/keyset de listas, versiones de invitación/link/publicación,
estructura normalizada de menú/meta, disponibilidad y límite de PDF, claves de
errores y semántica de replay. No se inventan campos a partir del ejemplo
abreviado `plan:{}` del contrato. Se reserva helpers `Api.vinculos`, páginas,
templates y módulos nuevos; enlaces focales en navegación/clientes se añaden
después del contrato definitivo. No se cambia transporte, auth global, cuotas,
DDL, perfil, diario ni exportación.

Tras commit/freeze backend y autorización de composición, una fixture aislada
nueva ejecutará auth/API/worker/PDF reales con cuentas sintéticas y correo
doblado, sin proveedor. Los casos incluyen no auto-publicar, invitación sin
cuenta y registro real, replay/doble clic, token erróneo/rotado/vencido,
destinatario incorrecto, OWNER externo/propio, sesión tardía, versión cambiada,
plan/PDF exacto, retirada/revocación y conservación personal. VM cubre fences y
errores del controlador; navegador móvil/desktop/teclado/axe tiene evidencia
separada. No se abrirá Chrome mientras siga la compilación PyInstaller
coordinada por root. No se reutilizan listeners ajenos ni se presenta un doble
como E2E real.

## Checkpoint de preparación: contexto y fragmento

Se añadió exclusivamente el contexto de `Api.vinculos` y su exportación pública;
el resto del cuerpo RAW de `api.js` es idéntico a base66. El contexto se obtiene
de auth/me y no concede una capacidad de recurso. Un OWNER/tipoUsuario ambiguo
no es normalizado: la API R12 aún debe rechazarlo conforme al contrato.

El lifecycle nuevo admite scopes descartables por vínculo y verifica identidad
antes/después de sus awaits y al renderizar. Las 26 pruebas VM del contexto usan
el Api real con fetch/Storage sintéticos. Las 15 de fragmento ejecutan el primer
script inline exacto del template de aceptación; prueban limpieza inmediata,
URL que no se puede limpiar, token en query, duplicados, formato, pagehide y
login/registro sin bearer ni aceptación automática. Son 41 casos de preparación.

El template es una shell todavía no montada y su consumer de recurso está
pendiente del DTO definitivo. No hay resultado HTTP/E2E ni lectura/publicación
R12 implementada que se pueda atribuir a este checkpoint. Backend confirmó que
su política first-party admite nonce al principio del head, antes de los assets
propios. El documento HTML inicial ya fue solicitado: la limpieza no puede
borrar registros históricos ni deshacer una query que un enlace ajeno añadió.
