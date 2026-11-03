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


## Seguimiento posterior al CI de 31bd6317

Corte de preparación posterior: 2026-11-03T00:13:57.426363+00:00. La rama publicada llegó a `31bd63174b45e1e79b1e0fe8f4c7b6654a0457a7`; main permanece en `fc7950ec`. El cambio adicional de ese commit fue únicamente el modo Git de `entrypoint.sh`, 100644→100755, con todos los bytes idénticos a 35a6. QA verificó el contexto real: 562 archivos, 549 de aplicación y sonda original intacta. Seguridad vinculó el escaneo completo de 35a6 —16 022 archivos, 51 170 coincidencias clasificadas y cero restantes— mediante igualdad completa de paths/blobs/SHA256. No se afirma un segundo escaneo para el cambio de modo.

El [CI4](https://github.com/user221000/MetodoBaseWeb/actions/runs/41547902554) confirmó avances en su fuente de merge observada: PostgreSQL superó arranque, core (4/4) y restore (1/1); imagen superó construcción y sonda (549 fuentes, 57 distribuciones, tres módulos nativos y once casos XML). Falló después en pagos, antes de ejecutar sus cinco casos planeados, con OSError; el arranque de aplicación posterior a la sonda devolvió ValueError. Los mensajes privados no se recuperaron. El corte independiente 23:50:22 UTC conservó ocho trabajos aprobados, seis fallidos, siete en curso y dos todavía sin instancia. Los seriales aún no tenían resultado final; no se declara CI global aprobado.

La regresión nueva de frontend se reprodujo antes de ejecutar Legacy51: el manifiesto de admisión conservaba las huellas anteriores de los dos archivos UI ya revisados. Se preparó un delta de sólo esos dos registros (bytes/hash) y el digest exterior; conserva las 322 rutas, todos los programas, adaptadores, presupuestos, RAW y aserciones. El autor ejecutó los seis grupos originales: 77 comandos/1 254 ejecuciones; además, 27 tests originales. QA independiente aprobó 19 controles de admisión, incluidos negativos. El primer fixture reducido del autor omitió un documento y se conserva rechazado; la ejecución final completa es distinta. La interfaz no vuelve a cambiar.

La autorización del gate de pagos dependía del umask de otro step, que no se conserva entre procesos Bash. El código podía crear el ACK como 0644 y su propio lector exige 0600. La propuesta crea el archivo de forma exclusiva con 0600 desde el primer byte, verifica el padre privado y comprueba el archivo antes de escribir JSON. No cambia lector, contrato, caducidad, cuotas, reembolsos ni esquema. La incompatibilidad se reprodujo con modelo POSIX declarado y IO Windows; la máscara efectiva y el traceback de Actions no se obtuvieron, por lo que la atribución exacta del OSError remoto sigue siendo una inferencia. QA independiente aprobó 19 controles y Seguridad nueve propios con DACL Windows reales. Un fallo posterior a crear puede dejar un archivo privado vacío/parcial cerrado; no se declara rollback a ausencia y el lector lo rechaza.

Seguridad revisó las tres propuestas exactas en el recibo `ci4-proposals-security-review-v1.json`, SHA256 `ed83b674a22de4ab6b7c0e3b4d3e465d46ac50c2a8c1472128aed158f8514e77`. La integración cambia bytes y necesita commit, escaneo completo y CI propios antes de publicar. Los recibos de 35a6/31bd conservan su alcance anterior.

La investigación estática del arranque de imagen comprobó head 41, 44 tablas y el catálogo compilado. Esa ruta utiliza el servicio PostgreSQL del workflow; no usa el clúster al que se corrigió el socket Unix. El resumen ValueError no permite elegir entre validación, roles, comando, cierre, readiness o testigo. No se cambió startup a ciegas: queda pendiente una etapa/frame autenticada sin secretos o una reproducción operativa nueva y aislada.

La reproducción local previa construyó `--target runtime`; la etapa posterior `production` FROM scratch, el arranque completo, SBOM/SCA y la imagen del futuro candidato conservan su aceptación pendiente. VM y servidores propios se cerraron con sus recibos. Los monitores locales de CI también se retiraron; uno fue interrumpido y el siguiente cerró cooperativamente. Ninguno de esos cierres cambia el estado del workflow remoto. No se fusionó, desplegó, migró producción, cobró o envió correo real durante estas correcciones.
