# Preparación web de Node, workflow y PostgreSQL

Fuente de código congelada: `e47f01c1a2a979bf430f93745c67bef9b0a65c75`.
Base ya integrada por Root: `da6a2be53820a97e75332903bc4d5d95f1502784`.
El inventario `minimal-delta14.json` liga las14 rutas no-doc a sus blobs Git y
SHA256 RAW:4 modificadas y10 nuevas. No hay delta de api/web/core/src/utils/config.
Los resultados se atribuyen a su commit de ejecución, no a una aprobación global.

| Fase | Fuente ejecutada | Resultado y alcance |
| --- | --- | --- |
| Replay serial inicial |735469bb |RECHAZADO en colección, exit2; ninguna prueba ejecutada |
| Corrección11 preimágenes Native |da6a2be5 |6/6:5 controles propios y el criterio original22 intacto |
| Colección del replay corregido |da6a2be5 |5536 identidades;0 módulos con fixtures pendientes; sin ejecución |
| UI27/37 adicional |60660846 |13 programas/147 criterios ordenados exactos;28 entradas ligadas |
| Rutinas y onboarding adicionales |686fe3af |8 programas/94 criterios;21 entradas ligadas |
| Controles del reporte adicional |686fe3af |5/5; tipado, orden, duplicados, scope y cuerpo de las aserciones |
| Storage SDK sin proveedor |f85f9e85 |40/40;0 fallos/errores/skips; identidades exactas |
| Scope histórico31 |aa7eab5b |3/3 y una sonda de namespace original; sin ejecutar la suite31 |
| PostgreSQL53 plan |5ea63e72 |53 identidades recolectadas, sin SQL |
| Autorización y fuente PG53 |5ea63e72 |5/5 controles puros, sin SQL |
| Publisher CI de PostgreSQL |e47f01c1 |2/2: cinco contextos rechazados antes de tools/SQL/payload; control válido sólo llega al marcador de versión |

Las fases con runner estándar Node/storage/plan53 hicieron pip check0/0 y
fotografiaron antes/después los92 paquetes, el intérprete y157 archivos de tres
paquetes Node. Los controles focales conservaron esas mismas fotos sin cambios;
no se les atribuye un pip check que no ejecutaron. Todas las raíces nuevas usan
`scan_secrets._private_evidence`: dos ACE User/SYSTEM protegidas y verificadas
antes del payload. Se conservan por separado el intento focal inicial sin XML
que rechazó un nombre de directorio de datos incorrecto y su corrección del
productor. No se convierte ese intento en PASS.

La primera materialización de replay convirtió11 helpers históricos de CRLF a
LF y fue rechazada antes de fixtures. La corrección recupera sus preimágenes
físicas retenidas; no reconstruye originales ausentes. El manifiesto22 auténtico
liga su SHA256/tamaño; el materializador liga además los11 blobs GitLF exactos.
Los20 helpers del host quedan RAW exactos; alembic.ini/db_bootstrap.py conservan
GitLF y su companion de lectura de dos rutas. Fuente original, manifiesto22 y
aserciones no cambiaron. El ZIP finito de las11 preimágenes tiene SHA256
`ced0218aa2a14fbf753d94e986cdaf7e33aa52df5f0e5019a0a9a16d4614c349`.

Los147 criterios conservaron sus13 programas y etiquetas; sólo se actualizó
explícitamente el binding de api.js desde e218801c al API actual con navegación
mis-rutinas y rechazo de acceso exacto. Los94 adicionales no repiten legacy51
ni esos13:92 etiquetas y dos grupos de aserciones originales de
routines_access_fences.cjs, cuyo reporte sólo emite dos contadores. Esos dos
grupos requieren el cuerpo fuente ligado por SHA y regiones, scope y enteros
exactos; no se infieren de un contador genérico. El catálogo se obtiene de la
función pura actual get_routine_program(),13 ejercicios, sin base de datos.

El workflow cambia sólo test-web, frontend-contracts, historical31-web y
current-postgres respecto a da6a. Test-web conecta serial/cobertura, n2 con
semilla20261018, físicas35 con modelos35 auténticos, fases R05 congeladas
60+48+15 y storageSDK. Frontend conecta legacy51/865 obligaciones únicas,
13/147 actuales y8/94 adicionales con Node24. Sólo se publican summaries y
cobertura proyectada; logs, XML bruto y ZIP originales quedan privados.

Historical31 invoca su run_isolated.py original desde un wrapper externo,
verificando HEAD31 y bytes de los blobs originales antes/después. Añade las
exclusiones de login Desktop, test_desktop*.py y licencia offline, más el guard
externo ci_web37.scope. No carga fixtures37 ni modelos actuales en fuente31.
La sonda hija confirmó que el namespace tests sigue siendo el original. Los
criterios web compartidos Free10 y los viewports web amplios permanecen.

PG53 conserva literalmente el módulo QA a9a0258b, SHA256 RAW
`22fb989fed797d93e0f965e78a83b6faf74e0ccab21bde2e537334c38931c8a3`.
Su runner separado exige perfil y ACK de fuente/53 identidades, un UUID, pool5
overflow0 y cierre normal/fresca ausencia. No cambia el catálogo429 ni69 UUID
históricos. La composición futura tiene70 acumulados y máximo dos simultáneos,
sin atribuir otra vez la aceptación local429 o53 ya realizada por sus dueños.

El candidato de workflow usa un cluster nativo nuevo, privado y loopback55483:
un service Docker bridge no cumple el inet_server_addr original. El bootstrap
es exclusivo de GitHub Actions, HEAD/workspace exactos y usuario no-root; genera
dos ACKs distintos con expiración4h. El migrador es privilegiado sólo para este
CLUSTER DE PRUEBA (SUPERUSER/BYPASSRLS/CREATEDB/CREATEROLE); la aplicación tiene
cuatro flags falsos y ninguna membresía. No es una política de roles de
producción. El cierre usa PID+birth ticks+boot ID+pidfile+exe y pg_ctl smart,
sin terminación/FORCE. Este código aún requiere revisión Root y ejecución Linux.

Se fijó ubuntu-24.04 porque GitHub anunció la migración de ubuntu-latest a26.04
entre19Oct y19Nov2026. El repositorio oficial PGDG conserva todas las versiones;
su índice lista server/client/libpq5 `17.11-1.pgdg24.04+2`. El candidato valida
fingerprint PGDG completo, Signed-By y versiones exactas, sin trusted=yes ni
allow-unauthenticated. allow-downgrades sólo permite resolver esos tres paquetes
con versión explícita en la VM efímera CI; no se ejecutó APT en este trabajo.

Fuentes primarias consultadas: [PostgreSQL Ubuntu y Signed-By](https://www.postgresql.org/download/linux/ubuntu/),
[archivo PGDG](https://apt-archive.postgresql.org/),
[índice de los tres paquetes17.11](https://apt-archive.postgresql.org/pub/repos/apt/pool/main/p/postgresql-17/index.html),
[anuncio de GitHub](https://github.blog/changelog/2026-09-17-ubuntu-26-generally-available-and-latest-migration/),
[imagen Ubuntu24.04 de20261018](https://raw.githubusercontent.com/actions/runner-images/ubuntu24/20261018.339/images/ubuntu/Ubuntu2404-Readme.md).

No hay aceptación Linux/Actions/CI global. Root mantiene HOLD de serial/n2/SQL/
VM mientras integra B19/B13/B20 y congela el runtime final. El replay preparado
da6a/5536 permanece inmóvil; no debe atribuirse a esa futura fuente. Faltan su
refreeze/colección/serial/n2, cobertura observada por área, revisión/runtime del
puente PG CI y sustitución de current-image33 por el entrypoint57 de Artifact.
Se conserva el gate original de cobertura nutrición95/90; los datos futuros de
auth/browser_session/MFA/cuenta, cuotas/billing/RLS y R30/PPL serán observados
sin inventar umbrales. No hubo SQL, Chrome, VM, Redis, Desktop, APT ni mutaciones
remotas por esta preparación. El R05 broad847 RED y las fases históricas
auténticas permanecen como tales.
