# Transporte del runner SQLite38

Esta etapa añade el runner y la colección que estaban pendientes en el corte
inicial de `README.md`. No cambia los seis archivos congelados de aquella etapa.
Todos los archivos37 y sus oráculos permanecen intactos; las derivaciones completas
e inversas están en las evidencias externas de preparación.

Las diferencias son explícitas: plugin/flags/mapa38, head38, revisión38 del
observador de fixtures y referencias a sus compañeros nuevos. Los validadores
JUnit, identidades, rechazos de skip/failure/error/duplicados, fuente quieta,
paquetes, pip check, cobertura, filtro web, journal, aislamiento y orden n2 son
los originales. El resultado agrega un digest completo de archivos y distingue
el HEAD Git base de los bytes38 todavía sin commit. No declara un replay de PG,
Native, Node o una historia anterior por ejecutar este transporte.

Sólo después de que Root revise/capture targets38 genuinos y abra la ventana de
validación, los comandos preparados son (con directorios nuevos, sin reutilizar):

```powershell
& $Web92 -I -B -X utf8 tests/ci_web38/prepare_collection.py --current38 --private $PrivateCollection
& $Web92 -I -B -X utf8 tests/ci_web38/run_web.py --suite smoke --private $PrivateSmoke --output $PublicSmoke --private-as-child-temp
& $Web92 -I -B -X utf8 tests/ci_web38/run_web.py --suite serial --private $PrivateSerial --output $PublicSerial --private-as-child-temp
& $Web92 -I -B -X utf8 tests/ci_web38/run_web.py --suite parallel --private $PrivateParallel --output $PublicParallel --private-as-child-temp
```

`Web92` es el Python revisado y TEMP/TMP/TMPDIR deben configurarse en E antes de
arrancarlo. Estos ejemplos son una receta, no comandos ya ejecutados ni autoridad
para abrir recursos. La colección produce oracle, bindings seleccionados y
recibos por namespace sin ejecutar fixtures. Deben revisarse sus identidades y
dependencias antes de la corrida broad, en lugar de tomar el inventario AST74
como una colección real.

La opción Node del runner conserva los mapas y funciones37 originales; no se
puede aceptar como actual38 hasta revisar sus nuevos bindings. La lectura OpsCI
identificó cambios legítimos en tres dependencias del mapa node-current37
(12/13 comandos) y dos del mapa routines-onboarding (6/8). Sus nuevos CJS se
revisan aparte. Las fases históricas mantienen su fuente/versiones y no se
reclasifican38. PG38 y restauración de hechos nuevos son otra familia pendiente,
sin cambiar el núcleo genérico backup_restore por una sospecha no reproducida.

Se añade `tests/test_ci_web38_composition.py` por transporte de los controles37:
misma lógica/aserciones y proveedor38 explícito, sin editar el módulo histórico.
No se ha ejecutado este módulo ni el runner. Sólo se compilaron las fuentes y se
comprobaron las inversas completas/definiciones no afectadas con AST.
