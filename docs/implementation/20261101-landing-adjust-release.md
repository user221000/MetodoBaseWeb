# Landing adjust — publicación autorizada del 1 de noviembre de 2026

El usuario autorizó expresamente registrar los cambios como `landing adjust`, publicarlos en el repositorio y desplegarlos. Se prepara un worktree aislado desde `origin/main` (`18d855ff1d4e3892e30905aae117fcf1446e795e`) para conservar los cambios locales y los archivos históricos de la ejecución.

## Contenido de esta publicación

- Landing con titular «Planes nutricionales claros. Clientes bien acompañados.», hero esmeralda, CTA lima, secciones diferenciadas y diseño adaptable.
- Demostración interactiva de Clientes, Plan nutricional, Historial/PDF y Rutinas con datos ficticios identificados.
- Invitación compacta al registro que aparece al entrar, puede cerrarse y reabrirse y permite elegir negocio o cuenta personal.
- Conservación de la suscripción elegida en navegación por registro, acceso y seguridad/MFA mediante una lista de destinos permitidos. Es sólo intención de navegación; la contratación y los permisos siguen dependiendo del servidor.
- Contratos HTTP y del navegador adaptados al diseño, conservando el consumidor activo de CI de ocho controles y cuatro capturas.

El catálogo, precios, cuotas, backend, correo y pagos conservan la versión productiva base. En archivos de suscripción se incluyen únicamente los enlaces y la nota de continuidad; no se incluye el ajuste local separado de recuperación de pagos inciertos. Tampoco se incluyen los cambios locales de diagnóstico de correo, documentación OpenAPI o eliminación de rutas duplicadas.

## Evidencia y verificación

Los documentos [rediseño](20261101-landing-redesign.md) y [contraste y referencias](20261101-landing-contrast-copy.md) describen los ensayos locales previos y conservan sus referencias históricas. Sus afirmaciones «sin push/despliegue» corresponden al momento de esos ensayos. Esta publicación utiliza un candidato acotado que se vuelve a verificar por separado.

Evidencia de publicación: `E:/MetodoBaseWorkspace/evidence/landing-adjust-release-20261101-20261102T0240/`. El recibo de preparación enumera los archivos copiados completos y los tres cambios parciales de navegación, y fija los hashes del worktree original que debe conservarse. Los recibos nuevos identificarán el commit, la rama remota, el despliegue y la comprobación pública final. No se atribuye a esta publicación CI global, PostgreSQL/RLS, recepción de correo o compras reales.

## Operación y recuperación

Publicar únicamente el candidato revisado, con mensaje exacto `landing adjust`, en `main`; observar que Railway construya ese commit y supere `/health/ready`. Después verificar la portada pública, recursos versionados, demo y registro sin enviar formularios. Esta publicación no añade dependencias, variables de entorno, migraciones ni cambios de esquema.

Si falla el nuevo despliegue, conservar los recibos y el despliegue previo sano `25118f6d-1e08-479f-bc9b-1fbab061e6d8` sobre `18d855ff`. La recuperación es un revert explícito del commit de esta publicación o volver al despliegue previo; no restablecer ni sobrescribir el trabajo local pendiente. Los requisitos y estados globales del backlog conservan su alcance anterior.
