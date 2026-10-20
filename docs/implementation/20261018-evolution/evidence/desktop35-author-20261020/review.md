# Declaraciones nutricionales en desktop: candidato local

Producto 0d20f6b55bd348edc3f140081f41f12b545b88bf sobre 55a3f4f9.
Son doce rutas de producto/pruebas. La fuente base y el soporte desktop se
conservan. No se modifican Alembic, web/API ni los constructores de dominio.

SQLite añade una columna nullable nutrition_restrictions_storage. NULL antiguo
sigue siendo información desconocida, sin afirmar ausencia de alergias. La
envoltura cerrada version1 contiene modo plain/cipher y payload JSON version1
con declaration y excluded_foods separados. Máximo 131072 bytes del JSON interior
y 262144 de envoltura. Rechaza claves duplicadas, formatos/IDs desconocidos,
corrupción y ciphertext sin clave. CryptoService protege los nuevos hechos
cuando se elige modo seguro; una clave ausente no autoriza plaintext. Un cambio
explícito tampoco rebaja ciphertext a plaintext. Esto no afirma cifrado global
del resto de campos o de archivos anteriores.

La escritura de perfil y snapshot usa una transacción BEGIN IMMEDIATE; omitir
declaración o pasar None conserva la celda anterior. La migración segura cifra
los snapshots existentes y revierte toda la transacción si una fila es inválida.
La actualización de perfil resuelve actualizar_cliente ausente y evita contar
esa edición como otro plan. Las búsquedas parciales se hidratan por ID antes de
editar. Los controles Qt permiten unknown/none/reported, other_reported, pedir
revisión y excluir alimentos del catálogo. Guardar el perfil sigue disponible
con una declaración que bloquea generación. Editar otros datos no reemplaza la
declaración precargada si el usuario no la cambió.

Los tres workers Qt reales reciben y comprueban los hechos antes de motor,
constructores y PDF. Los objetos parciales deben usar el snapshot persistido;
un snapshot explícito diferente requiere guardar/revisar el perfil. La escritura
para plan y el historial vuelven a comprobarlo bajo bloqueo SQLite. Un alta con
hechos nuevos requiere guardarlos explícitamente antes de registrar generación.
El flujo personal conserva el archivo de preferencias y sus campos ajenos,
añade una única clave versionada, protege según su modo de cifrado y usa replace
desde un archivo temporal único. Un archivo existente ilegible no se reinicia a
vacío. Un guardado no confirmado mantiene el formulario abierto. El worker
personal comprueba el snapshot antes de CPU, antes de PDF y antes del éxito.

No se mutan CATEGORIAS globales. El ensayo concurrente ejecutó dos constructores
de opciones reales con exclusiones diferentes, validó ambos planes y comprobó
igualdad global antes/después; PDF y señales fueron dobles de borde. Los tres
workers se invocaron con entradas/senales de prueba para demostrar que el guard
impide CPU/constructores/salida; no se atribuye una sesión visual completa. Qt
registro/perfil sí se montaron offscreen y sus handlers se ejecutaron.

Hay 100 PASS, cero errores/skips. La preimagen exacta 55a3 de gestor y diálogo
produjo cuatro RED esperados, incluido AttributeError en actualizar_cliente
(candidato QA-19). La misma aserción de aceptación y persistencia pasa después.
El upgrade usó una base real creada por el gestor antiguo y conservó filas e
historial. Se ensayaron rollback, cifrado, clave ausente, corrupción, omisión,
snapshot stale, listas/exclusiones, estados Qt y fallos de guardado. Pip 0/0;
1081 fuentes, 83 distribuciones, 8562 Python/pyi/METADATA y ambos Python quietos.
Ruff pasa en los tres archivos nuevos; 87 diagnósticos previos bajan a70 sin
diagnósticos nuevos. No se declara que todo el código heredado esté libre de lint.

Límites: un PDF que ya se exportó puede seguir en disco si el perfil cambia antes
del registro final; el SQL rechaza el historial/éxito, sin prometer atomicidad con
filesystem. Las comprobaciones de preferencias son snapshots, no una transacción
distribuida con PDF. El formato antiguo se actualiza sin borrar datos; no se ha
validado usar binarios antiguos que ignoran las nuevas declaraciones. No hay
validación clínica, instalador nuevo, prueba visual interactiva, PostgreSQL,
proveedor real ni aceptación independiente integrada en esta evidencia.

Los RAW finales seleccionados son exactos. Los inventarios completos de paquetes
y la salida del primer harness obsoleto están en la copia privada protegida antes
del payload y verificada después. No hay atestación retroactiva de ACL de los
directorios originales. El guard recursivo119 no sustituye un gitleaks global.
