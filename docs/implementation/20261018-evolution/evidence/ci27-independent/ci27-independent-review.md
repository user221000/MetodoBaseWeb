# Revisión independiente del delta CI27

Aceptado localmente. El workflow conserva los 17 reportes PostgreSQL anteriores y requiere además `pytest-postgres-diary-migrations.xml` y `pytest-postgres-diary.xml`, sin duplicados. Los comandos que los producen coinciden con los 19 argumentos obligatorios del guard.

Se ejecutaron **15 canarios del guard exacto**: los 19 XML válidos se aceptan; cada reporte nuevo se rechaza si falta, no contiene casos, tiene cero bytes, contiene un skip, failure o error, o tiene XML malformado. Los 60 bloques Bash pasan comprobación de sintaxis y las 73 referencias a scripts existen.

La colección local confirma 97 casos desktop para Windows y 95 con el filtro Linux. La diferencia son exactamente los dos casos nativos de Windows que ya estaban excluidos; los 12 casos OPS10 están presentes en ambas selecciones. Los comandos nuevos coleccionan 12 casos de migración, 13 de diario y revisión de seguridad, y 2 de restauración. Esto acredita selección y referencias desde Windows; no acredita ejecución en Linux ni ejecución PostgreSQL.

El comando de restauración conserva el probe histórico explícito y añade el caso poblado de revisión 27. El módulo histórico de revisión 26 no se modifica. Los archivos del guard frontend y sus pruebas conservan los hashes de la aceptación independiente anterior. El XML del autor acredita 97 aprobaciones desktop sin fallos, errores ni omisiones; esta revisión no repite esa ejecución ni las pruebas PostgreSQL ya aceptadas.

La primera ejecución se conserva completa: 80 fuentes estables, 15 canarios aprobados y las mismas colecciones. Para reproducir la comparación cuando cambie HEAD, `review_ci27_fixed_base.py` fija expresamente el baseline `0c55b167fa8cca49142d3f2b591034e3343e1328`. Solo cambia la referencia del baseline, el directorio de salida y su propia inclusión en el inventario respecto del runner inicial. La repetición en `final/` conserva **81 fuentes estables** y vuelve a aprobar todos los controles. No se modificó producto ni evidencia anterior.

La evidencia definitiva es `final/ci27-independent-source.json`; los canarios y los cinco logs de colección quedan junto a ella. No se ejecutaron Actions, imagen, navegador ni proveedores externos en este control focal.
