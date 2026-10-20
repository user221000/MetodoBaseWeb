# QA nativa37: contrato de ejecución independiente

Producto: Main `cd423ab0961898ce94fd2574cb4d6452cf8338b3`, equivalente a Main5666 más los tres CSS de `78aa202c3648e260b2e113523b8421c0ac812d5b`. La WT QA tiene evidencia propia y fuentes de test adicionales; no se atribuyen al HEAD de producto anterior. Se comprobarán todos los blobs de `api/`, `web/`, `core/`, `config/`, `src/` y `utils/` contra ese Main antes de la ejecución.

## Recursos y fronteras

Una sola UUID PostgreSQL nueva mediante `tests/account_security37_owned.py`, sin modificar esa primitiva. El recibo fsync `planned` precede a CREATE; inmediatamente después registra OID/owner y PID/generación. La aplicación utiliza el rol restringido sin superuser, bypass, createdb, createrole ni membership del owner, y no es owner. Revisión `20261020_account_security`, 41 tablas ORM y 42 físicas, FORCE RLS32 e índice30 exacto. La fixture de navegador usa el engine real con pool5/overflow0 por su bootstrap concurrente; no es una prueba pool1 ni una afirmación de capacidad o solución de R34.

PG55483 es de uso exclusivo sólo después del ACK de Root. No HBA, roles globales, FORCE DROP, cancelaciones ajenas, Redis, VM, desktop, instalación, envío ni proveedores reales. El cierre exige cero sesiones, DROP normal y ausencia desde nueva conexión. El servidor propio escucha sólo `127.0.0.1:8802`. Chrome se autoriza aparte, después de witness y dos muestras frescas con RAM física libre >=2.4GiB. Perfiles y todos los payloads se crean bajo padre privado con DACL previa. Procesos se atribuyen por PID+nacimiento+perfil+ruta y generación del padre; se preservan Chrome y listener8776 ajenos.

La captura local de correo reemplaza únicamente el transporte después del commit real. Escribe el enlace en archivos privados, nunca en issuer API, stdout público o endpoint administrativo. La aceptación local no acredita entrega. La doble respuesta de Stripe se mantiene sólo para el grupo histórico de portal y la navegación exterior se bloquea. GIS se cumple localmente como doble SDK para render/cancelación/callback obsoleto; no se acepta identidad Google ni se contacta a Google. Las demás operaciones HTTP, autenticación, MFA, cookies, autorización y persistencia son reales. No se cambian GUC, principal, reloj, factor ni cuerpos de aserción.

## Gate adicional histórico: 15 grupos

Los originales `mfa_ui_browser.cjs` (11 grupos) y `mfa_personal_browser.cjs` (4 grupos) permanecen byte exactos. `browser_native_compat37_qa.cjs` deriva explícitamente del companion31 actual, limita selección a esos dos drivers y cambia etiquetas de alcance35 a37; conserva sus cambios normativos R31 ya documentados y todas las aserciones de negocio. No se permite JWT/refresh/identidad en Storage. Es un replay, no 15 grupos nuevos. `pageErrors == []`, scope de axe y masking de semillas/kits quedan intactos.

## Dieciocho grupos nuevos, orden finito

1. Gym: navegación propia de recordatorios, contexto opuesto403, fuente desconocida y cero escritura automática.
2. Gym: guardar preferencia sólo con confirmación explícita, un PUT y consulta manual posterior.
3. Gym: métricas propias y consulta de proveedor explícita rechazada503 por DisabledPort; sin outbox ni envío.
4. Gym: enlace real de propósito recibido sólo en captura privada; GET público limpia fragmento sin POST, confirmación explícita, sin autoridad/cookie refresh nueva y contacto actualizado tras consulta manual.
5. Gym: contraseña primaria y MFA vigente reales; terminal, access/refresh anteriores401 persistidos y nuevo login202+factor real.
6. Personal: navegación propia de recordatorios, contexto opuesto403, fuente desconocida y cero escritura automática.
7. Personal: preferencia explícita y consulta manual posterior.
8. Personal: métricas y proveedor desactivado, sin envío.
9. Personal: mismo protocolo público de confirmación de contacto sin otorgar sesión.
10. Personal: contraseña+factor vigente, revocación persistida y nuevo login202+factor.
11. Pérdida de entrega de ACK de un PUT real ya confirmado: cero replay automático; retry explícito conserva key/cuerpo y versión única.
12. ACK de preferencia real retenido hasta otro login/cookie: no render de éxito antiguo, no adopción de B por la página invalidada; B real sigue autorizado.
13. ACK de password real retenido hasta login B: A anterior401, ninguna notificación terminal falsa/limpieza de B; B se demuestra por HTTP y no por adopción en el tab viejo.
14. ACK de emisión de correo real perdido: no autoresend ni token en DTO, una sola captura privada, relectura explícita.
15. Doble GIS declarado: cancelación y edición invalidan callback anterior antes de cualquier POST de reautenticación.
16. Navegación real/pagehide/atrás: no restauración de inputs privados ni envío implícito; sin credenciales o identidad en Storage.
17. Exportación personal HTTP/descarga real: cuenta propia, sin otros actores o campos de secretos; cambio a B limpia DOM y ObjectURLs.
18. Páginas reales de ambos roles: reflow320/390/768/1440 en cuenta y320/390 en recordatorios, oráculo geométrico inmutable y axeAA sólo de las secciones medidas.

Los actores nuevos son cuatro UUID sintéticas, dos OWNER de gimnasio y dos VIEWER personales, independientes de los actores fijos requeridos por los originales15. El estado de ambos contextos se modifica mediante autenticación real, no mediante overrides. El montador de notificaciones cubre preferencias y fuente desconocida; no demuestra cola elegible con proveedor verificado, entrega, adopción de cartera ni R27 completo. R37 no equivale a restauración ni a certificación MFA/UI global.

## Entradas, outputs y reproducción

Fixture mantenida:

`python -B -X utf8 tests/e2e/native37_postgres_server_qa.py --pg-config <JSON privado> --private <TASK/private> --port 8802`

Launcher diagnóstico Windows:

`python -B -X utf8 tests/e2e/run_native37_qa.py --private-root <TASK> --pg-config <JSON privado> --dependencies <node_modules readonly> --node <node.exe> --chrome <chrome.exe>`

`TASK` es nuevo bajo Temp auténtico, con nombre que empieza `metodobase-account37-author-pg-`; `TASK/private` y `TASK/leases` existen con DACL antes del payload. No se cambia TEMP/TMP del servidor: la primitiva37 verifica la raíz auténtica. Node recibe TEMP/TMP privados para sus perfiles. No se sobrescriben outputs cerrados.

Antes de cualquier CREATE, el launcher exige `native-preflight.json` y `native-sql-ack.json` que enlazan fuente, hash del launcher, perfil y límite de una UUID. Tras startup y readiness, produce `ready-before-Chrome.json`, dos muestras RAM y espera `native-chrome-ack.json`, enlazado a la misma fuente/launcher. Sin ese ACK no arranca Chrome. Readiness queda excluida de los grupos. Los dos drivers históricos se invocan mediante el companion37; el tercer driver es `native37_account_notifications_qa.cjs`. Se ejecutan en serie y se detiene el avance si falla un grupo; no hay retry automático.

`startup.json` es un witness tipado de revisión/tablas/familias/rol/índice/origen/runtime. `metadata.private.json`, `mail/*`, datos descargados, tokens, keys, stdout/stderr y trazas son privados. Cada driver produce `report.json`, capturas enmascaradas y conteos; los fallos se conservan. `close.json`, `resource-closure.json` y el recibo de lease verifican el cierre. Antes/después se congelan fuente completa, Python/base, 92 distribuciones, alcance de 8084 archivos instalados, 157 archivos Node, binarios, perfil y pip check. Se publican sólo proyecciones escaneadas y hashes de los originales privados; no datos de salud, credenciales, enlaces privados o kits.

Este ensayo es local Windows. No afirma ejecución de Actions, Linux, contenedor, WCAG global, proveedor real, carga, p95, capacidad o SLO. El before/after móvil geométrico separado es DOM inerte con CSS/markup reales; no sustituye este gate funcional nativo.
