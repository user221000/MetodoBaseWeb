# R32 UI / composición31: entrega de autor

Esta entrega conecta MFA a ambos login y a la seguridad de la cuenta, y usa grants explícitos para las nueve acciones sensibles de equipo/facturación y sus aliases. No concede permisos locales ni cambia la cartera, la política de cuotas, DDL, CI o el transporte de Google. Pendiente revisión independiente QA/SEC; no integración, despliegue o certificación.

## Fuentes y composición

La preparación UI está en `fa48edf3568ab9c3e753c8cf5ef69c784f69e065`, worktree original `F:/mb-mfa-ui-20261019`, limpio y conservado. Su manifiesto VM `da18364f292abc51e9c7cca44db90c0be1c9d86027eadb10b16b22fea857cc7f` y ZIP RAW `8e9baa1ee7acce3f0d11b0b29ead84f50b610c12b868f9863102af15b6687f38` no se reescribieron.

La composición separada `F:/mb-mfa-ui31-20261019` parte de `46dc908dd82edaa369f4d095df5abe7703a60de1`: UI `933f19f` (cherry de fa48), aliases `2f67da6` (78d27), PRIMARY `dbce653` (8b64), elegibilidad `c562e81` (440e7). PRIMARY tuvo cuatro conflictos de vecindad del middleware: se conservaron todas las condiciones `diary_api` y se añadieron las condiciones `primary_api`. Root verificó por AST y reutilizó ese mismo cuerpo en su anchor backend `913cb66061ac754ad09344fc24e8f769b5722997`. `backend-composition-equivalence.json` compara los cuatro cuerpos exactos con el anchor; es equivalencia, no una afirmación de ancestry o aceptación independiente.

`1312d28` es follow-up exclusivo de etiquetas `for/id` de ambos login, con dos rojos SSR y diez verdes posteriores. No modifica controlador, auth o Storage. Fuera de esa asociación, las trece fuentes de producto UI son las mismas de fa48. El único delta Python UI de fa48 añade `GOOGLE_CLIENT_ID` público a dos TemplateResponse, con Settings local como los login existentes; no cambia settings ni endpoints backend.

## Funciones y contratos

- Login contraseña y Google202 dejan challenge sólo RAM. El usuario elige y verifica un factor explícito; sólo una ACK200 válida guarda mediante `Api.saveTokens`. Un fallo de destino después de guardar ofrece reconsultar, sin consumir otra prueba.
- Estado servidor, primaria reciente por contraseña o credencial Google, alta/reemplazo, confirmación, regeneración y revocación tienen estados de carga/error/incertidumbre. El manual TOTP muestra semilla sólo en su vista; no hay QR externo ni promesa de recuperación por soporte.
- Confirmar/regenerar valida ocho códigos únicos y la ACK de máquina, limpia la vista/pruebas antiguas y cierra localmente con contexto exacto. Después crea una vista efímera nueva. Cambio posterior de cuenta, Storage o pagehide la descartan. No se navega antes de que el kit pueda verse ni se muestra a otra identidad.
- El prompt lazy first-party es una llamada explícita de los helpers sensibles. Congela método/path/body/key en RAM y liga grant al access exacto/revisión. MFA y negocio con grant no refrescan ni se reenvían; cancelar, error o carga fallida no ejecutan negocio. El transporte ordinario conserva su comportamiento.
- Equipo y facturación verifican contexto canónico antes/después de awaits y limpian DOM/estado/keys ante invalidación síncrona. Un resultado ambiguo bloquea otra intención hasta consulta explícita. El retry de la misma compra conserva su key.

## Evidencia por tanda, sin sumar dobles

| Tanda | Resultado | Alcance |
|---|---|---|
| UI VM original |28 API +30 estado +8 consumidores +8 prompt verdes|Transportes RAM y DOM mínimo; cuatro suites propias. No HTTP31/browser|
| Transporte previo |33+26+13+2 verdes|74 casos existentes intactos; no se atribuyen como criterios MFA nuevos|
| Emisor/expiración |11+3+10 verdes|Regresión existente; mismo api.js final de fa48|
| Router/SSR |8 verdes y luego10 con etiquetas|Páginas sólo en ASGI, sin factory/MFA backend; dos casos nuevos de etiquetas|
| Puente Node↔ASGI31 |4/4 verdes|Módulos UI/API reales contra ambas factories, SQLite y auth/MFA/commits reales; pipes privados sin listener; sólo capability Stripe doblada|
| Chrome principal |11 grupos /9 pantallas|SQLite migrada31, login Gym, kit, recuperación, equipo, portal, regenerar/revocar, ACK tardía→B, Storage fault nombrado|
| Chrome personal focal |4 grupos /3 pantallas|Registro real VIEWER, login Usuario200/202, kit y recuperación, seguridad personal|

Las doce pantallas tienen cero hallazgos axe AA en los bloques nuevos revisados y cero overflow. Cero pageerrors en ambos drivers. Anchuras320/390/768/1440, comprobación de teclado/foco y lectura visual de panel/prompt; no se declara prueba con lector de pantalla, axe de toda página ni entrega de proveedor.

Chrome principal tiene tres dobles explícitos: el primer403 de frescura del prompt es una denegación más estricta para abrir la vista (factor/grant/invitación finales sí pasan por servidor); la respuesta real confirm ya commiteada se retiene durante loginB; getItem lanza SecurityError de forma deliberada. Stripe se dobla sólo en el SDK portal y cualquier navegación fuera del origen se aborta antes de red. Correo `_send` devuelve False, y la UI declara entrega no confirmada. Google está sin configurar en esta fixture: los escenarios Google202 son VM de contrato, no proveedor real ni claims fabricados.

## Causalidad conservada

La primera tanda de puente dio2 verdes/2 rojos. El harness seleccionó TOTP por defecto y entregó un recovery22: el controlador lo rechazó localmente antes de enviar el factor (último status202). Se preservaron fuente/log/XML y dos diagnósticos seguros; sólo se añadió la selección explícita `recovery_code`, manteniendo las condiciones de las aserciones. Producto runtime no cambió durante las tandas HTTP; `http-source-closure.json` limita los dos cambios a harness/diagnóstico.

El primer Chrome midió el login durante su animación de opacidad y registró un rojo de contraste. Frame, inventario y reporte permanecen intactos. Esperar animaciones finitas antes de axe dio cero hallazgos con el mismo CSS/producto. No se atribuye a un defecto permanente ni se ocultó la primera salida. Las etiquetas sí fueron un defecto semántico distinto, con su before/fix separado. No se cambió CSS para obtener verde.

Los rojos y errores propios de la etapa VM están descritos en `mfa-ui/VM_AUTHOR_REPORT.md`, sin volver a atribuirlos al backend o al navegador.

## Runtime y cierre

Fixture propia8802: `db_bootstrap.main(['--revision','20261019_mfa'])` ejecutó las migraciones reales en SQLite Temp y verificó firmas/index30; revisión SQL `20261019_mfa`,32 tablas modelo/33 físicas con alembic_version. No fue create_all ni sólo expected_head. No acredita PG/RLS ni operación Linux.

`server-startup.json` y `browser-source-closure.json`:299 fuentes runtime quietas,89 paquetes Python,157 archivos Node y3 binarios sin cambios. Los cuatro productos backend coinciden con913cb, incluido header GitLF `66e6527291b449ee219e7201aa1fbba9af061e45a3bbe6979a2e70ada62bd25c`. El driver guarda su SHA RAW por ejecución. El prefix31 tiene `* -text` desde antes de sus proofs; UTF16 de PowerShell se conserva como RAW y no se normaliza para hashes.

Los contextos/Chrome propios cerraron en finally. El inventario Chrome ajeno inicial se preservó íntegro y no quedaron PIDs Chrome nuevos. El servidor hijo13816 y launcher10044 se cerraron sólo tras comprobar identidad, ancestry y commandlines; ambos ausentes y8802 sin listener. La primera comprobación demasiado estricta de ejecutable detuvo el cierre sin matar nada; luego se verificó la cadena venv→CPython y se cerró de forma acotada. SQLite Temp sintética se conserva; no se afirma haber borrado datos ni recursos ajenos. No PG, QEMU, build o proveedor durante esta etapa.

## Límites abiertos

Falta QA/SEC independiente de esta UI y composición. Google real requiere configuración de claims y primaria reciente verificable del proveedor; solicitar `essential_claims: "auth_time, amr"` no fabrica auth_time ni permite usar iat. Hay referencia oficial/fecha/extracto mínimo en el contrato UI.

R10/R31 conservan el límite del par legacy en dos claves, escritores de metadata existentes y falta de atomicidad durable entre pestañas/reload. No se añade persistencia de proof/seed/kit/grant. No se declara AAL2, resistencia al phishing de TOTP, recuperación administrativa disponible, clave/backup operativos, avisos de factor entregados, despliegue ni certificación. Los handles/roles de UI no sustituyen la autorización del servidor.
