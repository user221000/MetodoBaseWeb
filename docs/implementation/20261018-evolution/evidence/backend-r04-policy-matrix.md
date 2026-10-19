# R04: matriz previa a activar políticas

Estado: propuesta aprobada por alcance; mecanismos de contexto implementados, sin nueva activación RLS todavía. El coordinador revisa canales, roles y excepciones antes de añadir la migración local. No se ejecuta activación en producción ni se afirma RLS universal.

Autoridad: el middleware usa la identidad canónica que relee usuario, sesión, rol y equipo persistidos. `/api/usuario/*` usa el ID personal; rutas profesionales usan primero team_gym_id y después el ID propio. No se acepta tenant por header, email, body o query. Cada transacción PostgreSQL instala SET LOCAL; ausencia instala cadena vacía y las políticas no conceden filas. Fallos de instalación se propagan. Hooks del engine cubren conexiones y sesiones directas; after_begin de Session conserva el sujeto explícito de callbacks a través de commits.

| Tabla | Columna de autoridad | Política propuesta y canales |
|---|---|---|
| clientes | gym_id | Igualdad con tenant para SELECT/INSERT/UPDATE/DELETE. Profesional en equipo; perfil personal separado. |
| planes_generados | gym_id | Igualdad. Worker explícito y validación adicional del cliente; incluye historial/descarga. |
| client_progress | gym_id | Igualdad. Acceso sólo mediante cliente del tenant y RBAC. |
| subscriptions | gym_id | Igualdad. Lectura profesional/personal; callback enlazado con compra verificada. |
| payments | gym_id | Igualdad. Historial sujeto autorizado y callback verificado. |
| stripe_customers | gym_id | Igualdad. Checkout/Elements/portal; no lookup global de customer. |
| invoices | gym_id | Igualdad. Servicio de facturación sujeto autorizado. |
| checkout_sessions | gym_id | Igualdad. Identidad comercial del sujeto autorizado. |
| gym_profiles | gym_id | Igualdad. Perfil/branding y onboarding del usuario recién persistido. |
| gym_branding | gym_id | Igualdad. Configuración del gimnasio autorizado y worker de PDF. |
| gym_settings | gym_id | Igualdad. Repositorios bajo contexto profesional explícito. |
| gym_licenses | gym_id | Igualdad. Licencia persistida del gimnasio autorizado. |
| planes_suscripcion | gym_id | Igualdad. Lectura comercial y upsert de onboarding explícito. |
| audit_log | gym_id nullable | Igualdad para filas de tenant; NULL sin acceso por rol de aplicación. Auth previo al login tiene su plano separado. |
| user_subscriptions | user_id | Igualdad con sujeto personal, también si pertenece a equipo. Reserva y reconciliación enlazadas. |
| generation_reservations | user_id | Igualdad con sujeto personal; replay no puede cambiar identidad de sesión. |
| license_activations | gym_id nullable | Familia 17. NULL histórico sin acceso; vínculo con GymLicense sólo por SHA256 exacto de clave única, sin modificar derechos/fechas/estados. Nuevas operaciones requieren propietario y licencia persistida autorizada; contención SEC01 a cargo del coordinador. |

Las políticas nuevas deben reemplazar las cuatro históricas por una definición conocida, y usar ENABLE más FORCE. Una base nueva y otra con c4 activo deben llegar a las mismas definiciones/banderas. Ninguna función SECURITY DEFINER concede lectura global. `set_tenant` histórico se reconcilia a SECURITY INVOKER y configuración local a la transacción. El rol de ejecución debe ser NOSUPERUSER/NOBYPASSRLS; la migración usa un rol separado. Startup verificará estos requisitos y no aceptará SQLite explícito en producción.

| Tabla de control fuera de RLS | Motivo, actor y consultas autorizadas | Contención requerida |
|---|---|---|
| usuarios | Login por email, verificación por ID y sv, refresh, alta e invitación ocurren antes de conocer tenant. Auth y servicio de equipo leen identidad. | Predicados explícitos email/ID; listas de equipo filtran asociación persistida y RBAC. Revocación no elimina perfil personal. Regresiones negativas de rutas/roles/cuentas. No se ofrece listado global al usuario. |
| refresh_tokens | Rotación por jti y usuario autenticado; revocación por user_id. Necesario antes de abrir tenant de petición. | Token criptográfico y usuario activo/sv; rotación condicional y transacción. Nunca listado público. |
| purchase_intents | Callbacks firmados y proveedor autenticado requieren descubrir sujeto antes de consultar Subscription bajo RLS. | Lookup sólo por ID de intención del proveedor o customer exacto/provider; un solo sujeto. Precio, moneda, referencia y cuenta se verifican antes de derechos. Requests ya acotados no pueden enlazarse a otro sujeto. No endpoints de listado global. |
| stripe_webhook_events | Inbox compartido identifica reintentos de notificaciones anteriores al tenant. | Firma y resource ID antes del acceso; consulta por event_id y servicio de purga acotado. No payload crudo ni endpoint de lectura pública. |
| auth_audit_log | Éxitos/fallos previos al login pueden carecer de usuario/gym. Seguridad registra y consulta intentos exactos por email/usuario o gym. | Sin listado global en rutas de usuario; consultas de gym con predicado y permiso, datos mínimos y retención separada. No afirmar que este historial tiene aislamiento RLS. |
| provider_subject_associations | Asociación mínima por proveedor, tipo de recurso e ID exacto, necesaria para callbacks Stripe anteriores a PurchaseIntent. | PK compuesta evita colisiones entre proveedores; provenance/source_ref obligatorios. Backfill sólo desde Subscription/StripeCustomer persistidos y conflicto de sujetos aborta. No contiene derechos, importes ni datos personales. Sólo lookup exacto de callback verificado o registro de compra verificada; no listado público. Bind rechaza sujeto distinto del ambiente o sesión. |

Canales adaptados antes de la activación: workers web/API llevan tenant_scope explícito; Stripe resuelve intención o asociación mínima histórica antes del bind y después consulta mapping bajo RLS. Refund/invoice sin referencia usa customer exacto asociado; cancelación usa subscription exacta, incluso sin PurchaseIntent ni metadata. La asociación por sí sola nunca concede derechos: el reconciler mantiene la evidencia R01. MP verifica recurso/referencia/importe/moneda antes del bind y vuelve a consultar proveedor bajo lock. Registro y Google enlazan el sujeto recién persistido antes de crear perfil/defaults. Las invitaciones públicas válidas pueden enlazar el equipo sólo después de verificar digest y vencimiento, para leer su nombre. Los scopes y sesiones no cambian de cuenta durante su vida.

Preparación antes de activar: 20261018_provider_subjects añade únicamente la asociación mínima, los dos vínculos nullable de LicenseActivation y expira nullable. No activa RLS. La verificación estructural usa un contrato por revisión: R03 conserva su fixture/manifiesto de 22 tablas inmutable; preparación tiene fixture/manifiesto nuevo de 23 tablas. Los ensayos históricos usan --revision explícita; despliegue conserva head predeterminado. La contención del bypass previo de licencias por prefijo debe pasar revisión y pruebas antes de crear la migración de activación.

Evidencia inicial del autor: backend-r04-context-first.log (9 pruebas) y backend-r04-adapter-first.log (96 regresiones). No son aceptación PostgreSQL de políticas. QA prepara base UUID propia, rol restringido, sesiones directas, commits/rollbacks, pool de una conexión, ausencia de tenant, error SET LOCAL y perfil personal de miembro. La cuota B2B atómica y sus tres dimensiones se implementan después de cerrar R04.
