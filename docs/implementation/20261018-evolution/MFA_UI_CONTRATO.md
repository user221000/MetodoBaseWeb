# UI R32 / MFA: contrato y readiness

Base aislada `57335e5b4bcba3c76c97d47e481b526fb52874a6`, rama `implementation/mfa-ui-20261019`. No incorpora R24 ni backend31 WIP. Wire consumidor completo preservado RAW con SHA `ad9ed0c62d2b367f6224ff3339998f1621a0537cf9efb5082bcf1d5e032cda2e` en `evidence/mfa-ui/before`. Trece fuentes y cuatro inventarios estáticos de atributos/textos preceden cualquier edición; éstos no son SSR ni navegador ejecutado.

## Capas y ownership

- `api.js`: helpers MFA públicos/autenticados, contexto opaco RAM de revisión y acceso exacto, autorización y ejecución explícita de las nueve acciones/aliases cerrados. Request MFA y operación con grant no hacen refresh/replay. El transporte normal conserva su contrato. No interceptor de todo fetch.
- Login de contraseña/Google en ambas plantillas: controlador común RAM, respuesta202 pendiente sin tokens ni navegación, factor explícito y sólo commit central tras ACK válido. Cambios de cuenta, Storage, cancelación, expiración y pagehide descartan pruebas; reintento tras incertidumbre no repite ciegamente un challenge consumible.
- Parcial/JS/CSS MFA nuevos en configuración y perfil. Estado servidor, primaria reciente, alta/reemplazo, confirmación, kit y revocación. Semilla manual accesible local; no QR externo ni dependencia nueva de QR.
- `equipo.js`, `gym-suscripcion.js`: acciones existentes con misma intención/DTO/método/path/key y fences antes/después de await/DOM/destino. Prompt lazy first-party: carga fallida/cancelar no ejecutan negocio. No ampliar permisos ni inferir cartera de MFA.

## Kit y cierre

Confirmar/regenerar exige success, shown_once, reauthenticate y ocho códigos distintos con formato estricto. Contexto exacto anterior todavía vigente. Primero descartar challenge/proof/semilla/grants y cerrar la sesión central sin otra petición con access revocado; comprobar la revisión vacía exacta después de la notificación síncrona. Sólo después crear una vista efímera nueva del kit, vinculada a esa ACK/cierre. La invalidación propia no elimina prematuramente esa vista nueva. Cualquier sesión posterior, Storage defectuoso, cancelación o pagehide la destruye. No mostrar kit de una respuesta vieja a otro actor ni usar una relectura para reconstruirlo.

Un503 o respuesta inválida no confirma cambio ni rollback; puede haber commit y pérdida de ACK. Se descartan secretos inseguros y se ofrece login/consulta de estado. Pérdida de todos los factores/códigos no tiene bypass local, correo o soporte fingido.

## Google: fuente oficial y límite externo

Verificado2026-10-19: [GIS JavaScript reference, essential_claims](https://developers.google.com/identity/gsi/web/reference/js-reference#essential_claims) define un string y el ejemplo mínimo `essential_claims: "auth_time, amr"`. [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect) distingue auth_time de iat e indica que los claims deben habilitarse en configuración. La UI los solicita y permite proveedor o contraseña; nunca fabrica metadata. Un popup con sesión existente no garantiza por sí mismo primaria fresca. El backend valida firma, correo canónico persistido y edad; flujo Google real/configuración/operación de proveedor quedan como dependencia externa pendiente, sin atribuirla a dobles.

## Secretos, pruebas y estado

Challenge, proof, seed, URI, grant y recovery permanecen sólo en memoria/vista de propósito específico; nada en query/fragmento/atributos/Storage/console/analytics. Inputs permiten paste/autocomplete apropiado. No se agrega persistencia de metadata sanitaria o MFA; el acceso legacy en dos claves sigue el gestor central y R10/R31 conservan sus límites. El backend verifica permisos/actor/SV/generación/tenant/access/body/key: los handles no son autoridad local.

Pruebas iniciales `before/api-wire.json`: cuatro rojos, dos incompatibilidades concretas de login202 en helpers actuales y dos capacidades ausentes; transporte RAM, no HTTP31. Después: negativos propios, regresiones de transporte y consumidores montados con estados loading/empty/error/429/503/expiry/cancel; sin relajar pruebas históricas. HTTP31 y navegador real esperan commit backend y ventana del coordinador. No Chrome, PostgreSQL, QEMU, servicios, providers/envíos/cargos reales durante la preparación.
