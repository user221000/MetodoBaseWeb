# Preparación local de Railway

Este directorio contiene una definición candidata para revisión OPS08. No se instaló `.railway/railway.ts`, no existe un digest candidato probado y el manifiesto de ejemplo no selecciona recursos. La definición rechaza `apply`; para convertirla en infraestructura aplicable se necesita otra revisión del paquete final.

Instalación y validación local:

```powershell
cd infra/railway
npm.cmd ci --ignore-scripts --no-audit --no-fund
npm.cmd run check
npm.cmd test
node verify-cli.mjs 'C:/Users/Consu/AppData/Roaming/npm/node_modules/@railway/cli/bin/railway.exe'
```

`package-lock.json` fija el SDK y TypeScript. `tooling.json` fija la versión y el SHA256 del ejecutable nativo observado; no acredita su procedencia mediante un archivo de publicación del proveedor. El wrapper npm de CLI 5.59.0 arrastra `tar 6.2.1` vulnerable y se excluyó del lock. No se ejecutaron scripts de instalación ni se modificó la instalación global. El verificador ejecuta únicamente versión y ayuda después de comparar bytes.

La misma definición recibe el entorno seleccionado mediante `ctx.environment`/`environmentId`. Una entrada importada identifica producción existente o un entorno aislado ya autorizado y materializado. La definición no crea entornos, bases, roles, Redis, buckets, volúmenes ni dominios. Un `partial` propuesto acota la propiedad al servicio web; su nombre y adopción siguen sujetos a comprobar la propiedad remota existente.

Un manifiesto local ignorado proporciona el inventario completo de nombres de variables, configuración importada sin valores, etag, hash del import, IDs exactos y digest de la imagen probada. Los secretos existentes se expresan con `preserve()`. `METODOBASE_ENV=production` es la única variable pública fijada para ensayar también los controles de arranque en el entorno aislado. `DATABASE_URL` y `MIGRATOR_DATABASE_URL` permanecen separadas: no se enlazan a la URL propietaria del servicio Postgres. Preservarlas no demuestra que sus permisos ya sean correctos.

La evaluación del SDK y sus pruebas no consultan Railway. El procedimiento externo pendiente está en [RAILWAY_IAC.md](../../docs/implementation/20261018-evolution/RAILWAY_IAC.md). No use el ejemplo como inventario de producción ni rellene las marcas de revisión para eludir un requisito que aún no se cumplió.
