# Ejecución de Auditoría y faltantes

El usuario solicita desplegar agentes reales de coordinación, backend, frontend, QA, seguridad y operación, tomando como guía la [auditoría anterior](../../audits/20261102/AUDITORIA_Y_FALTANTES.md). El original entregado en E tiene SHA256 físico `696ef8c7f931ea438cbfafee51a16d5986db81c79dff9a8d8b670ee962c20aa6`; se conserva sin reescritura. La copia del repositorio conserva su texto; Git puede representar los saltos CRLF como LF y su huella se registra por separado. La matriz inicial enlaza los once pendientes con sus responsables y criterios; es un registro del comienzo, no una aprobación de cierre.

El código de partida actual es `fc7950ec341371b4354cba30ffd6c9a9860336fd`, posterior al corte `b10ab884` de la auditoría. La contratación Stripe sin configurar un factor de cuenta se conserva conforme a la petición posterior del usuario. No se restaura una política anterior al corregir pruebas o controles de CI.

## Decisiones y dependencias

El usuario ha definido que una devolución parcial mantiene el acceso hasta acabar el periodo ya pagado. La devolución completa conserva su tratamiento actual. Esto autoriza implementar y probar importe devuelto, saldo neto, estado visible y derechos sin extender fechas ni inventar cobros históricos. La aceptación de política no sustituye las pruebas del proveedor y la revisión independiente del cambio.

El ciclo externo Stripe requiere claves en modo prueba custodiadas fuera del chat y un entorno aislado. El inventario inicial sólo encontró claves live y ninguna instancia staging del proyecto autorizado. Las pruebas con SDK controlado permanecen clasificadas como tales; no se usan cobros reales o replay de eventos live para cerrar el ciclo sandbox.

La renovación de CI debe conservar el rechazo de entradas o hallazgos nuevos. Los controles antiguos, snapshots y RAW no se modifican para fingir un resultado exitoso: se crean contratos vigentes finitos, se prueban manipulaciones y se exige revisión ajena al autor. Una proyección de entradas históricas no se presenta como una construcción real de la imagen actual.

## Organización y evidencia

Root coordina dependencias y contratos. Los agentes trabajan en olas por el límite de concurrencia disponible. QA y seguridad revisan de forma independiente la parte que no hayan escrito; si seguridad redacta el registro de cuatro coincidencias públicas o sintéticas, QA valida ese registro.

El trabajo usa un release aislado en E y conserva 715 hashes de fuentes locales originales del worktree activo antes de comenzar. Los nuevos temporales, cachés, pruebas y recibos quedan en E/F. Las fuentes de referencia y los RAW previos se preservan. No se amplían permisos, cambian proveedores, crean cargos o publican migraciones sin preparar y revisar el resultado concreto.

Los estados finales enlazarán evidencia de la fuente actual, pruebas, riesgos y tareas que dependan de credenciales, custodia o decisiones externas. La auditoría original conserva su fecha; un estado nuevo se añade con su propia evidencia y no reescribe el resultado anterior.
