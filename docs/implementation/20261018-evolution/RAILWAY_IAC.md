# OPS08: preparación de Infrastructure as Code

Estado: preparación local revisable. No se ejecutaron `init`, `link`, `pull`, `migrate`, `plan`, `apply`, despliegues, creación de recursos ni cambios de variables. No hay una imagen candidata final ni un entorno aislado creado. La configuración actual `railway.toml` se conserva.

La [guía oficial de Railway](https://docs.railway.com/infrastructure-as-code) confirma el corte de Config as Code el 1 de diciembre de 2026 y la incompatibilidad de gestionar simultáneamente un servicio mediante ambos sistemas. TypeScript es la superficie GA. La fecha requiere completar la transición, pero no autoriza cambiar producción.

## Inventario observado

Consulta de sólo lectura: `status --project joyful-quietude --environment production --json`, reducida en memoria a IDs y nombres antes de escribir evidencia. Proyecto `joyful-quietude`, ID `5b6dc7c5-1bb0-47b3-9409-5cdf574a34ba`; sólo aparece el entorno `production` (`56977cda-fbff-4a31-82c3-a88502eacf59`). Los servicios son `MetodoBaseWeb` (`66552210-e97e-47f3-946b-87ab0674ae75`) y `Postgres` (`a69e2c12-1eb2-446f-9b1a-6f4b87db043e`).

Esta consulta no es un inventario nuevo de valores, permisos, volúmenes o buckets. La auditoría histórica registra un volumen PostgreSQL y ningún montaje del servicio web; no se revalidaron esos detalles con esta consulta. La presencia histórica de `REDIS_URL` no acredita un Redis disponible ni su titularidad. No se deduce un entorno staging de una rama local.

## Definición preparada

[infra/railway/railway.ts](../../../infra/railway/railway.ts) es la única entrada de autoría y se seleccionaría con `--file`. No está en la ruta de autodescubrimiento `.railway/railway.ts`. Su módulo [candidate.ts](../../../infra/railway/candidate.ts) propone el parcial estable `metodobase-web` y declara exclusivamente el servicio web. El nombre todavía no fue adoptado ni comparado con propiedad remota existente.

Una sola definición selecciona un destino ya importado por nombre e ID del contexto. Producción exige sus IDs observados; cualquier entorno aislado exige una entrada separada con ID propio y servicio existente. No se usa el nombre `staging` como autorización ni se declara un nuevo entorno.

El candidato requiere imagen de registro con digest SHA256, commit y huella de su evidencia. Rechaza etiquetas mutables, credenciales en la referencia y valores ausentes. El mismo campo `candidateImage` se utiliza para todos los destinos, de modo que no se reconstruye una imagen distinta para promoción. No se asignó un digest ficticio al ejemplo.

Los ajustes expresados son pre-deploy bloqueante `python db_bootstrap.py`, inicio mediante `/app/entrypoint.sh`, salud `/health/ready` con 120 segundos, una réplica y reinicio ON_FAILURE con 5 intentos. Se conservan otros campos importados de despliegue. Los tests comprueban que estos ajustes reemplazan los equivalentes antiguos. La imagen existente define usuario non-root y retira la URL migradora antes de ejecutar el servidor; el ensayo de imagen Linux sigue pendiente.

Todos los nombres de variables del import completo se expresan con `preserve()`, salvo `METODOBASE_ENV=production`, valor público fijado para ejecutar también los controles productivos en el ensayo aislado. Las URLs app y migradora son dos secretos distintos; no se enlaza `DATABASE_URL` al output propietario de `Postgres`. Conservarlas no valida su rol. Sus privilegios y destino deben pasar los controles R04 y el ensayo de migración antes de servir tráfico.

Se rechazan valores inline y configuración legacy todavía asociada. Un montaje o configuración de red requiere ampliar la revisión del import antes de incorporarlo: este paquete no los elimina, migra ni crea. La omisión de recursos en una definición total puede borrarlos; el [contrato de parciales](https://docs.railway.com/infrastructure-as-code/reference) restringe esa propiedad, pero no demuestra que los campos omitidos del servicio sean inocuos. El diff real debe revisar también esas propiedades.

## Herramientas y validación local

Node 24.21.0; SDK `railway 3.16.0`; TypeScript 5.9.3; `@types/node 24.19.2`. [package-lock.json](../../../infra/railway/package-lock.json) fija las dependencias y sus integridades. Instalación con `--ignore-scripts`: typecheck aprobado y 23 pruebas Node aprobadas. Las pruebas evalúan el SDK con datos de import, imagen y entorno aislado expresamente sintéticos; verifican configuración resultante y negativos de identidad, adopción, digest, inventario y recursos externos. No son un plan del proveedor.

El ejecutable nativo Windows x64 observado es CLI 5.59.0, SHA256 `1ec0e51315e542dd7530965a3187ec0780cfcda5e607f0498b48a39e7923e956`. [verify-cli.mjs](../../../infra/railway/verify-cli.mjs) compara bytes antes de ejecutar sólo versión y ayuda. No se verificó su archivo de distribución original. No se cambió el CLI global. Su wrapper npm exige `tar 6.2.1`, que la consulta SCA señaló con vulnerabilidades críticas; se retiró esa cadena del lock local. El audit final del pequeño entorno SDK informa 0 vulnerabilidades conocidas en 6 dependencias, sin generalizarlo al runtime Python ni al CLI nativo.

No se utilizan campos recientes de tracing: la referencia exige CLI 5.63 o posterior y el candidato rechaza esos campos y cualquier ajuste importado fuera de su superficie revisada. La evaluación local aprobada acredita tipos y salida del SDK; no ejecuta el compilador Rust, el reconciliador remoto ni la carga nativa de autoría de CLI 5.59.

Hay dos límites comprobados mediante el código oficial [eval.rs de v5.59.0](https://github.com/railwayapp/cli/blob/v5.59.0/src/iac/eval.rs) y [saved_plan.rs de v5.59.0](https://github.com/railwayapp/cli/blob/v5.59.0/src/iac/saved_plan.rs): la autoría TypeScript se evalúa en un proceso Node, y el artefacto fijado vincula el árbol `.railway/` al aplicar. Por ello, no se presenta este directorio `infra/railway` como paquete final compatible con la aplicación de planes fijados. Cambiar `--source-tree` para ocultar esa diferencia no resuelve el contrato. El SDK instalado busca la versión nativa por `env._` durante ese loader; Windows necesita una prueba explícita de ese camino, no sólo `tsc`.

## Secuencia externa pendiente

1. Obtener un import nuevo del destino correctamente seleccionado y una consulta de propiedad de parciales, con valores conservados en Railway. Revisar el conjunto completo de nombres, etag, identidad, recursos y ajustes. No usar `--include-variables`, `--decrypt-variables` ni `--show-values`. La [referencia CLI](https://docs.railway.com/cli/config) documenta esos modos y el plan redactado.
2. Acordar y autorizar la adopción del servicio legacy, el destino aislado y los recursos con coste. Verificar privilegios de app/migrador, Redis y almacenamiento durable sin imprimir secretos. No se elimina `railway.toml` ni se despeja su asociación remota durante esta preparación.
3. Construir y probar Linux, migración/restore del head final y rollback compatible; registrar un digest real y evidencia. Preparar el manifiesto completo a partir del import, sin atribuir al audit histórico el carácter de inventario completo actual.
4. Preparar el árbol final de autoría para probar carga CLI, resolución SDK, preservación de variables, dominios/montajes y pinning del artefacto. El manifiesto del candidato debe quedar vinculado a los mismos bytes revisados; un archivo local mutable fuera del árbol final no basta para aplicar.
5. Revisar un `config plan` nuevo: ningún borrado o cambio ajeno, mismo digest entre entornos y sólo diferencias acordadas. Un plan antiguo o un etag cambiado exige nueva revisión. La aplicación y el despliegue necesitan autorización sobre ese resultado concreto y revisable.

La definición actual bloquea `apply` incluso si se entrega un manifiesto. Quitar ese bloqueo forma parte de la revisión final, no de ejecutar estas pruebas. `legacyConfigDetached`, etag y huellas del manifiesto son referencias de revisión local; no sustituyen una comprobación contra el estado remoto ni un mecanismo de autorización del proveedor.
