# Controles de seguridad y privacidad del lote A

Fecha de referencia: 2026-10-18, America/Mexico_City. Agente responsable: seguridad; coordinador: PM/arquitectura. Base Git `daa25efbf51d154710bad625025b345fa9ec9252`, rama `implementation/20261018-execution`. Los cambios aún no están desplegados. La revisión parte de la lectura completa de los siete informes obligatorios; sus resultados históricos no se presentan como validación del candidato.

## Fuentes primarias verificadas

Se consultaron sus páginas oficiales durante esta ejecución; la versión fijada evita referencias ambiguas a ramas móviles. Estos marcos orientan controles seleccionados. No constituyen una declaración de cumplimiento integral L2, AA, NIST, legal ni clínica.

| Fuente | Versión/estado observado | Uso acotado |
|---|---|---|
| [OWASP ASVS](https://owasp.org/projects/asvs) | La página oficial identifica 5.0.0 como estable. Se fijan requisitos al tag v5.0.0. | Objetivo L2 del proyecto, con controles aún abiertos. |
| [ASVS autorización](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x17-V8-Authorization.md) | v5.0.0-8.1.1, 8.2.1, 8.2.2, 8.2.3, 8.3.1, 8.3.2, 8.4.1 | Política explícita por función/objeto/campo, aplicación en servidor, cambios de autorización y tenant. |
| [ASVS autenticación](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x15-V6-Authentication.md) | v5.0.0-6.3.4 | Consistencia entre caminos de autenticación. MFA, recuperación y política completa siguen abiertos. |
| [ASVS sesiones](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x16-V7-Session-Management.md) | v5.0.0-7.4.1, 7.4.2 | Terminación efectiva en backend y cuentas desactivadas/borradas. Inventario y terminación selectiva de sesiones quedan abiertos. |
| [ASVS errores](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x25-V16-Security-Logging-and-Error-Handling.md) | v5.0.0-16.5.1, 16.5.3 | Respuestas sin detalles internos y denegación ante fallos. |
| [OWASP API Security Top 10](https://api-security.owasp.org/editions/2023/en/0x11-t10/) | Edición 2023 | API1/2/3/4/5/6/8/9/10: objetos, identidad, campos, cuotas, funciones, cobros, configuración e inventario. |
| [NIST SSDF publicaciones](https://csrc.nist.gov/projects/ssdf/publications), [SP800-218 final](https://csrc.nist.gov/pubs/sp/800/218/final) | 1.1 final (2022). El catálogo oficial también identifica 1.2, SP800-218r1, como borrador del 2025-12-17. | Base estable 1.1; revisión separada, pruebas reproducibles y artefactos identificables. No se trata el borrador como final. |
| [NIST SP800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html) | Revisión 4; página publicada en agosto 2025 | Referencia técnica de autenticadores, revocación y sesiones; no se asigna AAL al producto. |
| [WCAG2.2](https://www.w3.org/TR/WCAG22/) | Recomendación W3C vigente enlazada, 2024-12-12 | Objetivo AA: 1.4.3, 1.4.10, 2.1.1, 2.4.7/11, 2.5.8, 3.3.1/2/8 y 4.1.2/3. Requiere pruebas del recorrido y revisión manual. |
| [Stripe webhooks](https://docs.stripe.com/webhooks) | Documentación viva consultada; SDK/cuenta/API deben fijarse en evidencia de runtime | Firma con cuerpo original; tolerancia de antigüedad por defecto del SDK de 5 minutos; duplicados y orden no garantizado; reconciliación. |
| [MercadoPago Webhooks](https://www.mercadopago.com.mx/developers/en/docs/checkout-pro-preferences/additional-content/notifications/webhooks) | Documentación viva del proveedor, Checkout Pro | Vincular x-signature, x-request-id y data.id autenticado. La política local de antigüedad es control del producto; debe admitir reintentos legítimos. |

## Amenazas y controles aplicables

| Control / requisitos | Amenaza y límite de confianza | Implementación o trabajo actual | Prueba/evidencia y revisión |
|---|---|---|---|
| S01 / R02, B06/B07/B22, QA-05 | Un rol inválido o permiso desconocido asciende a owner; VIEWER usa alta de clientes. | `web/services/permissions.py:111` deniega roles desconocidos y permisos sin registro. `web/routes/clientes.py:78` exige create/cliente además de cuota. `auth_deps.py` deja de inferir privilegios desde tipo. ASVS8.2.1/8.3.1. | `tests/test_identity_security.py`: permisos no registrados en cuatro roles; roles inválidos en tipos gym/usuario; alta VIEWER 403 sin fila nueva. QA y backend revisan independientemente. Matriz completa de todos los recursos aún pendiente. |
| S02 / R02/R10, B06/B08/B20 | Token firmado conserva permisos de una membresía antigua o de usuario desactivado. | `web/auth.py:565` construye principal persistido; password, Google, refresh e invitación lo consumen. `:443` consulta estado/rol actual y compara membresía y versión de sesión. ASVS6.3.4/8.3.2/7.4.2. | Tests de login+refresh, Google miembro, Google desactivado, cambio a VIEWER, borrado/desactivación y desvinculación. Google usa transporte falso; proveedor real pendiente. |
| S03 / R10, B08 | Logout sólo borra navegador; refresh concurrente resucita una sesión. | `web/auth.py:546` incrementa session_version y revoca refresh en una transacción; `:485` no emite par de una versión distinta tras rotación. Access breve incluso remember. ASVS7.4.1. | Tests logout access/refresh, carrera intercalada logout/refresh, epoch legacy0 y TTL. La carrera es intercalación determinista; falta estrés multiproceso/PostgreSQL. |
| S04 / R10/R31, B20, API9 | Endpoint administrativo público comparte secreto de firma. | Se eliminó `/api/admin/fix-user-tipo` del router. No se rotó ninguna clave real. | Test 404 y tipo de usuario inalterado. Operación administrativa futura necesita identidad, autorización y auditoría propias. |
| S05 / R01, B01/02/03/13/14/15/16/17 | Preferencias/redirect o evento falsificado concede pago; cuota se consume varias veces. | Backend implementó reconciliación/pagos; seguridad revisó firma, sujeto, precio/moneda/importe, intención, duplicados, orden y cuota atómica. ASVS8.2.3 y API4/6/10. | Revisión independiente local y 97 regresiones: [security-review.md](security-review.md). Dobles de frontera no prueban entrega sandbox, cobros ni conciliación real. |
| S06 / R06/R33, B09/B22/B23 | Medidas no finitas; catálogo compartido mezcla restricciones; exclusión total restaura alimentos; texto clínico promete garantías. | Root implementó validación y nutrición. Seguridad revisó entradas compartidas, ausencia de asignación privilegiada, catálogo por solicitud y resultado final. | Revisión local y gate de 37 casos identidad/nutrición: [security-review.md](security-review.md). Revisión nutricional profesional separada; no se declara aptitud clínica. |
| S07 / R02/R06/R20, B22 | SQL/excepciones filtran datos personales, rutas o credenciales. | Clientes devuelve códigos públicos `client_create_failed`/`client_update_failed`; logs conservan sólo clase del error. Registro usa respuesta estable. Root/backend corrigen otras rutas propias. ASVS16.5.1/16.5.3. | Falta prueba integrada de cada handler afectado y request_id. No basta buscar str(exc); revisar respuesta y logs. |
| S08 / R04/R07/R31, B04/B05/B11 | Tenant del navegador es autoridad, contexto se pierde tras commit, conexión reutilizada filtra datos/archivos. | Auth usa pertenencia persistida; repositorios deben filtrar propietario. No se habilitó RLS. ASVS8.2.2/8.4.1. | PostgreSQL restringido, dos gyms, ausencia de tenant, pool, worker, webhook y descargas siguen pendientes; SQLite no acredita RLS. |
| S09 / R31, B20, UX-03 | Tokens/diario en almacenamiento JS, contenido no confiable alcanza innerHTML. | Inventario abajo; root cambió renderTags a nodos/textContent y DTO valida IDs. CSP nonce existe, no sustituye escape ni prueba de sinks. | No se ejecutó exploit XSS. Falta política de migración de tokens y datos, exportar/borrar/retención. |

Responsabilidad de implementación: backend S05/datos, root S06/UX/operación, seguridad S01–S04/S07 en archivos asignados. QA valida integración. La revisión independiente de los controles escritos por seguridad corresponde a backend; este archivo no constituye su aprobación.

## Política de sesión del candidato

1. `Usuario.session_version` empieza en 0. La migración compartida de backend debe instalar el campo antes de iniciar el nuevo código. Altas nuevas de gimnasio persisten OWNER explícito. El backfill autorizado sólo afecta tipo gym sin equipo con rol VIEWER histórico; no eleva individuos ni miembros.
2. Nuevos access usan ACCESS_TOKEN_EXPIRE_MINUTES (15 por defecto). Remember-me sólo amplía refresh (30 días por defecto; normal7). Access/refresh nuevos incluyen versión1, issuer `metodobase`, audience `metodobase-web` y sv; se rechazan expiraciones malformadas/no finitas.
3. Cada uso de access consulta usuario activo, rol y equipo persistidos. Una baja/cambio de equipo invalida el token; un rol reducido se aplica en la siguiente petición. Si falla la BD no se concede acceso desde claims antiguos. No existe caché de autorización que retrase revocación.
4. Logout incrementa sv y revoca todos los refresh en la misma transacción. La rotación de refresh vuelve a comprobar la misma versión antes de emitir el par. Reutilizar refresh revocado invalida todas las sesiones del usuario.
5. Transición compatible: token legacy sin sv equivale a sv0. Puede operar mientras la cuenta permanezca en0; logout lo invalida. Los access legacy pueden conservar su expiración larga anterior. Requiere decisión de cutover/expiración y ensayo staging antes del release; no se forzó cierre de sesiones reales ni rotación de claves.
6. Persisten límites de B20: formato HMAC propio, sin key-id/rotación programada ni inventario por dispositivo. Se agregaron verificaciones de contexto; no se afirma que equivalgan a una biblioteca revisada. Tokens siguen en localStorage hasta completar R31. MFA, recuperación y verificación email siguen abiertos.

## Inventario mínimo de datos R31

| Conjunto y ubicación | Finalidad técnica observada / acceso previsto | Pendiente verificable |
|---|---|---|
| `Usuario` (`models.py:48`): nombre, apellido, email, hash de contraseña, roles, invitaciones; `RefreshToken`: usuario, jti, tiempos, revocación. | Identificación, autenticación y pertenencia. Sólo usuario y gestores autorizados según función. | Invitaciones hasheadas, recuperación, inventario de sesiones, retención, exportación y borrado sin secretos. |
| `Cliente` (`models.py:163`): contactos, edad, sexo, medidas, objetivos, actividad, exclusiones y notas libres. | Elaborar perfil/plan; contener información potencial de salud. Propietario personal o equipo autorizado del gym. | Finalidad/consentimientos y permisos de soporte acordados; minimización de notas; acceso por campo/rol y trazabilidad. No usar en analítica general. |
| `PlanGenerado` (`models.py:216`), PDF/JSON; `ClientProgress` (`models.py:498`). | Plan e historial de medidas, potencialmente sensibles. | Retención y borrado en BD, archivos, objetos, caché y copias; no cachear públicamente planes privados. |
| `StripeCustomer`, `Subscription`, `UserSubscription`, `Payment`, `Invoice`, `CheckoutSession`. | Referencias de proveedor, estado comercial y comprobantes. No guardar PAN/CVC. | Obligaciones de retención financiera requieren decisión y asesoría legal; separar eliminación/anónimo de evidencias contables. |
| `AuditLog`/`AuthAuditLog`, logs/Sentry/métricas; perfil/branding con teléfono/dirección/email/logo. | Operación y trazabilidad; datos de contacto pueden identificar personas. | Campos permitidos, acceso, protección y plazos por destino; eliminar payloads sensibles de logs. |
| `localStorage`: mb_token, mb_refresh_token, mb_nombre, diario/agua/comidas por fecha; `base_usuario.html` limpia todo al salir. | Sesión y seguimiento local actual. | Particionar propietario/contexto, persistencia de diario, fechas locales, migración y eliminación segura. No confundir clear local con borrado del servidor. |

No existe todavía evidencia de exportación ni borrado integral de cuenta en los routers inspeccionados. No se decidió un plazo de retención por conveniencia técnica. Producto/usuario deben definir conservación; revisión legal externa y revisión nutricional profesional requieren personas reales y evidencia propia.

## Superficie web y límites de revisión

`main_web.py` configura CORS con lista por entorno y credenciales, CSRF firmado con excepciones Bearer/auth/webhooks y CSP con nonce. Las APIs reciben Cache-Control no-store desde security_headers. Se inspeccionó código; no se validaron respuestas de producción en esta ejecución. La migración futura a cookies HttpOnly requiere diseñar CSRF/origen y despliegue compatible, no sólo cambiar dónde se guarda un token.

Se observó concatenación de alimentos_excluidos en innerHTML/data-food de `usuario_perfil.html:200`; debe corregirse con DOM/textContent y validación estructurada. No se confirmó ejecución de JavaScript ni se afirma explotación. Archivos/logo y rutas de descarga necesitan revisión independiente en R07 con tipo real, tamaño, nombres, autorización y persistencia; middleware existente no acredita ese control.

## Resultado y puerta de revisión

- Antes: `security-before.log` registra 12 fallidas y 3 aprobadas de las primeras 15 regresiones; confirma que las pruebas detectan los defectos corregidos.
- Después: `security-after.log` registra 37 aprobadas (25 identidad y 12 nutrición); se ejecutó con `python -X utf8 tests/run_isolated.py tests/test_identity_security.py tests/test_nutrition_safety.py -q --tb=short` y venv temporal de QA, SQLite sintético en memoria, proveedores deshabilitados. Dos warnings de deprecación (Starlette TestClient y Config Pydantic) no se ocultaron.
- Backend revisó auth independientemente: [backend-auth-review.md](backend-auth-review.md). La revisión de seguridad del código de root y sus límites están en [security-review.md](security-review.md). Falta QA sobre estado integrado y evidencia PostgreSQL/imagen/staging. Estos resultados locales no cierran por sí solos R02/R10/R31 ni el objetivo L2.
- Para aceptar: revisor distinto del autor inspecciona diff y cambios de esquema, repite regresiones sobre huella congelada, verifica 401/403/404 y ausencia de datos sensibles, comprueba compatibilidad legacy y registra observaciones/resolución. Cambios posteriores relevantes invalidan sólo la evidencia afectada.
- No se conectó Railway, BD real, Google, Stripe ni MercadoPago; no se envió correo, se cargó tarjeta, modificaron derechos reales, migró producción o rotó un secreto real.
