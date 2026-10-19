# Clasificador finito de ubicaciones revisadas R05

Fuente f7b12a71a89de2e35b0035ccef147a673ad50d29. El registro v1 anclado
contiene 31.394 ubicaciones/reglas únicas de 31.564 ocurrencias revisadas de un
informe histórico. Exige SHA256 del archivo RAW y del snapshot, línea física
exacta conservando CR, regla, versión8.30.1 y configuración exacta. No usa
Match/Secret/Line, prefijos de directorio ni patrones genéricos de metadatos.
Registro ausente no clasifica; registro presente corrupto aborta. Los dos pins
anteriores se conservan. El informe mantiene exit bruto y añade exit efectivo.

110 pruebas focales actuales PASS (49 nuevas+61 anteriores), Ruff/pip0 y fuentes,
89 paquetes y ambos ejecutables Python exactos antes/después. Seguridad revisó
v1 por separado en a704f070. Los primeros intentos, su warning de dos EOF y la
corrección secuencial se retienen en author-evidence.zip. El directorio original
de ejecución no tiene atestación retroactiva de ACL al crearse; la copia privada
sí fue protegida y verificada antes del payload y tras readback.

El escaneo completo del predecesor17c9 sobre12.367archivos quedó estable y RED:
42.830 hallazgos brutos,28.273clasificados,14.557bloqueantes. Su informe sólo
contiene ubicaciones/hashes, sin secretos/matches. No es PASS de f7b ni del árbol
común33. El replay de31.564ubicaciones anteriores no es un escaneo nuevo. Las
16ubicaciones checksum con tres preimágenesWIP ausentes conservan la limitación
de procedencia descrita por el revisor; no se reconstruyeron ejecuciones RAW.

Las clasificaciones candidatas de las nuevas ubicaciones quedan fuera de este
registro hasta otra revisión independiente. R05 global sigue abierto. Sin
PostgreSQL,Chrome,Linux,desktop,proveedor real ni Actions en esta fase.
