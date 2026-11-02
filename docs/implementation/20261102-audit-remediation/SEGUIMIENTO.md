# Seguimiento de auditoría y matriz de cierre

Fecha: 2 de noviembre de 2026. Corte de preparación: 16:52 America/Mexico_City (22:52 UTC). Ámbito: servicio web. Base revisada: `efa07ff94b5d3d8cd66c24fd312f60abd0506e08`.

Esta ejecución continúa la [auditoría original](../../audits/20261102/AUDITORIA_Y_FALTANTES.md), su [seguimiento anterior](../../audits/20261102/SEGUIMIENTO_Y_FALTANTES.md) y la entrega externa de las 13:09 UTC. Conserva los once pendientes y los 167 criterios del backlog. El recibo externo de publicación identifica el commit final; este documento describe la preparación anterior a su CI.

## Cambios preparados y revisados

En Clientes y Planes, las pestañas activas tenían texto oscuro sobre fondo verde. Se fija texto blanco dentro del espacio de aplicación. La medición independiente pasó de 3,04 a 6,47 de contraste. La página Planes también podía lanzar un TypeError al invalidar la sesión después de que el shell retirase su contenido. Las operaciones DOM toleran ahora nodos ausentes; la invalidación global, el incremento del epoch, la limpieza de enlaces y las comprobaciones de actor y respuesta tardía se conservan.

El clúster PostgreSQL usado por CI41 deshabilita sockets Unix y conserva TCP en 127.0.0.1. La reproducción Linux PostgreSQL 17.11 mostró fallo de permisos con el socket predeterminado y arranque correcto con el ajuste, incluyendo SCRAM, rol restringido, fsync, synchronous_commit y parada normal. Es una reproducción de ese mecanismo en Debian, no una lectura de la causa privada del runner Noble de GitHub. Los helpers y RAW históricos permanecen intactos.

Los diagnósticos de CI añaden ubicaciones acotadas del arranque PostgreSQL y módulos de pruebas fallidos. El proyector web sólo publica rutas Git, símbolos estáticos comprobados por AST, contadores y hashes. Los parámetros, mensajes, cuerpos de assertion y datos del entorno quedan fuera. Una proyección rechazada conserva el fallo original. Las pruebas que fallaron no se convierten en aprobadas ni se repiten automáticamente.

## Equipo, contratos y evidencia

Se usaron agentes reales en oleadas, con coordinación y hasta tres hijos simultáneos. La autoría de cada propuesta se revisó por otro agente. Los archivos compartidos se integraron únicamente desde coordinación después de congelar manifests. Los cambios de frontend y las pruebas de operación utilizaron worktrees o recursos propios.

| Responsabilidad | Trabajo y evidencia |
|---|---|
| Coordinación y arquitectura | Alcance, ownership, contratos, composición de ocho archivos CI y dos UI, revisión de cápsula operativa y decisiones de publicación. Registro externo: `audit-remediation-20261102T220303Z`. |
| Backend y datos | Corrección de arranque PostgreSQL y diagnóstico finito; 43 pruebas focales del autor y reproducción Linux con cierre ACPI de su VM. Manifest `7b6f3bb7…`. |
| Frontend y UX/UI | Dos correcciones de interfaz; seis recorridos reales con login local, diez capturas, generación, historial, cuota y PDF; focos de navegación y sesión tardía. Informe `FRONTEND_FINAL.json`, SHA256 `630c11d1bb663e25eef826d954bbdf5d063efbbb0c471f71e3a3076cabe791a9`. |
| QA y automatización | Observación final independiente de CI3; autoría del proyector revisada por seguridad; otro agente QA verificó la integración y frontend. CI: 68 pruebas y 50 subcasos; 220 contratos retenidos; colección oficial de 8 537 seleccionados y tres deseleccionados. Frontend: once controles focales y tres complementarios. |
| Seguridad y privacidad | Revisión independiente de los ocho archivos CI y dos UI, Git real, privacidad, XML y consumidores reales del diagnóstico. Se conservan epochs, permisos y límites. El prototipo anterior de diagnóstico de imagen se rechazó para integración por faltar controles del consumidor. |
| Operación y documentación | Preparación de reproducción local de la imagen mediante una cápsula vinculada a Git d98, VM y Docker propios, sin arrancar aplicación o proveedores. El resultado operativo posterior tiene recibo externo; no se anticipa aquí aprobación de build/probe. |

Los conjuntos se solapan y no se suman como cobertura global. La colección descubre pruebas; no equivale a ejecutar sus 8 537 criterios. La aceptación local de los dos cambios UI no acredita todos los recorridos, PostgreSQL/RLS o capacidad comercial.

QA de CI conservó idénticos los 16 020 archivos antes y después de su campaña. El peer UI reprodujo contraste y TypeError desde fuente auténtica, verificó el payload en Chrome y comprobó sesión/actor con datos propios. Su caso de historial vacío no prueba aislamiento de filas o PDF persistidos; las comprobaciones del autor que sí los contienen se atribuyen a su informe separado.

Los primeros instrumentos de navegador usaban inyección de localStorage obsoleta y tuvieron errores de selectores y cierre por hilo. Se preservaron sus rechazos. Las ejecuciones finales usaron login real y un loop principal. Uvicorn consumió su gracia de diez segundos y Windows registró avisos de conexión; los supervisores esperaron salida del servidor y se comprobó ausencia de PID/puertos, sin force kill. Esto no significa un cierre sin avisos.

## Resultado real del CI anterior

[CI3 de la base EFA](https://github.com/user221000/MetodoBaseWeb/actions/runs/41447205601) terminó a las 07:57:07 America/Mexico_City (13:57:07 UTC): **23 trabajos, diez aprobados, doce fallidos y uno omitido**. El corte anterior de las 13:09 UTC permanece histórico.

Los seriales se ejecutaron: Python 3.12 reportó 8 317 passed, 147 failed, 17 errors y un skipped; Python 3.11 reportó 8 316, 148, 17 y uno, respectivamente. Son contadores reportados y pueden incluir distintas fases de una identidad. Sus mensajes privados no se recuperaron ni se les atribuye una causa inventada. El diagnóstico nuevo permitirá localizar módulos en una ejecución posterior; no corrige por sí mismo esos fallos.

Ruff y la sintaxis de 1 216 archivos pasaron en la integración local. Bandit observó las 31 ubicaciones conocidas, pero rechazó el nuevo checkout Windows por no coincidir íntegramente con ninguno de los dos universos de bytes revisados. Ese resultado permanece rechazado. Antes de publicar se debe comprobar el payload Git canónico del commit exacto, con las reglas finitas existentes, y repetir el escaneo completo de secretos. No se hereda el PASS de EFA ni se relajan pins.

## Pendientes y publicación

La [matriz de esta ejecución](MATRIZ_SEGUIMIENTO.csv) conserva las prioridades y siguientes acciones anteriores, y añade el avance de esta ola. PEND-06 y PEND-07 avanzan con correcciones y evidencia; no quedan cerrados globalmente. Stripe sandbox sigue identificado pero sin claves de prueba o acceso autenticado disponibles. PEND-02 continúa condicionado a un caso demostrado y PEND-03 no se reabre.

La rama sigue destinada a revisión. No se fusiona a main, migra producción o despliega este candidato durante la preparación. La política aprobada de devoluciones parciales conserva acceso hasta el fin ya pagado y no se modifica por estos cambios de CI/UI. Su publicación requiere el ciclo real de Stripe, comprobaciones de la fuente e imagen finales y la ventana compatible 40→41.

Los recibos de esta ola están bajo `E:/MetodoBaseWorkspace/evidence/` en los directorios `audit-remediation-20261102T220303Z`, `remediation-backend-20261102T2203`, `remediation-qa-20261102T2203`, `remediation-qa-independent-20261102T2232`, `remediation-security-20261102T2203`, `remediation-security-final-20261102T2240`, `remediation-frontend-20261102T2203` y `remediation-operations-20261102T2203`. Sus logs privados, bases y objetos de prueba no forman parte de la documentación pública.
