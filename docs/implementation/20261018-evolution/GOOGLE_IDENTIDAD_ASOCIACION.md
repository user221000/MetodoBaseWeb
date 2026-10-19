# Identidad Google por sujeto persistido (revisión 33)

La clave de acceso externa es `(issuer canónico, sub)`. El correo del proveedor
es contacto presentado, no una autoridad para elegir una cuenta ya existente.
Un correo nuevo puede crear un contenedor vacío junto con su asociación en una
transacción; no adopta perfiles, clientes, pertenencias, planes o derechos. Una
coincidencia de correo existente exige vinculación local explícita. Cambiar el
correo declarado por el mismo sujeto no cambia el contacto local ni la cuenta.

La reproducción original de SEC17 usa el puerto tokeninfo anterior y conserva
cuatro rechazos faltantes y cuatro controles. Primero se reparó la asociación
con ese transporte, sin alterar los ocho criterios. La implementación final usa
`google-auth[pyjwt]==2.62.0` con JWT RSA y JWKS firmados de prueba. Su mapeo
de transporte documenta el cambio de tokeninfo a JWKS; no representa un bypass
criptográfico del proveedor ni un incidente sobre cuentas reales.

## Autoridad y protocolo

El login resuelve únicamente una asociación activa, recarga la identidad
persistida y conserva los controles MFA, padre, actividad y versión de sesión.
El alta nueva publica usuario y asociación juntos; las colisiones UNIQUE
abortan sin emitir una sesión antes del ACK. El proveedor se verifica antes de
abrir la transacción de cuenta. Ninguna URL proviene del token o de su `kid`.

Vincular exige una sesión actual, conocimiento reciente de la contraseña local,
factor actual cuando está habilitado y una afirmación Google con `auth_time`
real de menos de 300 segundos. No se usa `iat` como sustituto. Cada intento
cuenta en el presupuesto durable actor/propósito antes de consultar el proveedor
y antes de las operaciones que pueden hacer rollback. El puerto IP conserva
Redis fail-closed de producción. No se retienen locks durante la espera HTTPS.

El intento contiene sólo hashes y prueba persistida de actor, issuer/sub,
propósito, acceso exacto, SV y generación del factor. Caduca en el mínimo de
cinco minutos, frescura de Google y expiración del acceso. Confirmar consume ese
intento una vez, publica la asociación, incrementa SV y revoca refresh en una
transacción. No devuelve tokens de sesión. Desvincular exige la identidad y
versión observadas, contraseña y factor actuales; revoca la fila y avanza su
versión, sin borrar historia. Un sujeto revocado no pasa a otra cuenta. El mismo
dueño puede solicitar una revinculación explícita. El límite MAX de SV se
rechaza antes de consumir la prueba.

No se puede desvincular un contenedor Google-only por la mera presencia de un
hash de contraseña generado y desconocido. La recuperación local 28 conserva su
contrato propio; no acredita cuál era un `sub` histórico no almacenado. Una
cuenta legacy Google-only sin continuidad verificable sigue pendiente de un
procedimiento seguro. No hay backfill por correo, operador ficticio ni permiso
de suplantación.

## Tablas y funciones reales

`auth_external_identities` y `google_link_intents` son dos tablas de control de
autenticación, separadas de pagos. La primera permite la búsqueda exacta por un
sujeto ya verificado antes de conocer el actor local. La segunda requiere actor
e intento opaco exactos. Siguen la frontera de control plane existente de
usuarios, refresh y pruebas MFA: no declaran RLS universal ni seguridad frente
a SQL arbitrario con todas las credenciales de autenticación de la aplicación.
Un GUC no prueba una identidad del proveedor.

La revisión sí añade **dos funciones PostgreSQL**: `r33_identity_immutable()` y
`r33_intent_immutable()`. Ambas devuelven `trigger`, son `SECURITY INVOKER`, con
`search_path=pg_catalog, public`; no son RPC, accessor ni `SECURITY DEFINER`.
Dos triggers PG las ejecutan antes de UPDATE/DELETE. SQLite tiene cuatro
triggers equivalentes. Las claves de propietario/issuer/sub/creación nunca se
reescriben ni borran. La revocación/reactivación sólo cambia estado y versión;
el intento sólo puede pasar de no consumido a consumido una vez. No se concede
DDL a la aplicación. La llamada SQL directa a funciones `RETURNS trigger` es
rechazada por PostgreSQL, aun con EXECUTE por defecto; no afirma que un ACL
inexistente sea una restricción adicional.

El target 33 firma definición, argumentos, retorno, lenguaje, invoker/definer,
configuración de búsqueda, volatilidad, paralelismo, ACL, triggers y flags de
ambas tablas. Añade un testigo portable: propietario de cada función igual al
propietario de su tabla, sin fijar el nombre de un migrador sintético. El gate
canónico conserva las firmas predecesoras y rechaza drift. Los targets 22–32
no se regeneran ni se retargetean. El resultado esperado es 35 tablas de
negocio más `alembic_version`, 26 familias FORCE RLS y dos tablas nuevas fuera
de RLS. Las firmas agregadas atestiguan 26 funciones PG y 12 triggers no
internos (incluidos los predecesores).

La migración comprueba exactamente 32 antes de añadir 33; no infiere datos.
Rollback vacío vuelve a 32 exacto. Si hay historia de identidad o intentos,
downgrade se rechaza y requiere una restauración revisada.

## Transporte, UI y límites

La biblioteca oficial verifica firma, algoritmo, audiencia y tiempos. El
servicio limita el JWKS a 128 KiB antes de parsear, HTTPS fijo, timeout de diez
segundos y sin redirects. Se inspeccionó el código de la versión instalada:
2.62.0 usa `PyJWKSet.from_dict`; el transporte de pruebas no oculta una segunda
salida de red por `PyJWKClient`. Los tres paquetes nuevos se fijan con hashes
en locks web/test que ya incluían PyJWT. El entorno WEB89 compartido permanece
intacto; las pruebas finales usan un entorno propio de 92 distribuciones.
La imagen/SBOM final y el proveedor real se verifican en su gate separado.

La página exacta `/cuenta/google` y su slash llevan no-store/no-referrer y CSP
GIS cerrada. Sólo las cuatro rutas exactas de vinculación admiten la frontera
first-party correspondiente, en todos los estados. Las páginas vecinas y
políticas previas siguen sus contratos. El wire v1 y su adenda son las entradas
del consumidor UI; no se guardan credenciales ni intentos en URL o Storage.

GIS usa `essential_claims: 'auth_time'` (string), según la referencia oficial.
La configuración del proveedor debe habilitar el claim. Elegir cuenta o pedir
consentimiento no prueba frescura; faltar el claim falla cerrado. No se realizó
ningún cambio en Console, envío, conexión Google real ni despliegue.

Las sesiones de las rutas nuevas son propias y cierran antes de publicar la
respuesta. Ante close fallido se invalida únicamente esa sesión. Si close e
invalidate fallan ambos, se devuelve 503 sin afirmar éxito; la prueba retiene
la sesión para medir el límite de un checkout propio y luego lo limpia. No se
dispone el engine compartido. ACK perdido, rollback o limpieza incierta nunca
retornan prueba, seed ni tokens como éxito confirmado; no hay retry/readback
automático del escritor.

Fuentes primarias: [Google ID token verification](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token),
[GIS JS reference](https://developers.google.com/identity/gsi/web/reference/js-reference#essential_claims),
[OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect),
[google-auth ID token API](https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.id_token.html).
