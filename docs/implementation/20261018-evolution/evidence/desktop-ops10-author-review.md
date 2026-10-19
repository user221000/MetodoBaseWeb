OPS10 corregido y congelado para revisión independiente, sin build. Fuente del hallazgo: [revisión independiente del artefacto histórico](desktop-artifact-independent-review.md), cuyo bundle 9f3f32e incluye una referencia de diseño con nombres/correos de procedencia desconocida. No se afirma que esas identidades sean reales.

Commit exclusivo: `aca7bfb04750483f77945cb606690225ba94ae32`, sobre `3f7977314a64da41cf96865a32caa7a4a30a4cd3`, en `F:/MetodoBaseWeb-desktop-20261019`. El worktree quedó limpio y el commit contiene sólo `build.py` y `tests/test_desktop_packaging_ops10.py`.

La receta omite exactamente `assets/design-reference.png` al seleccionar recursos rastreados por Git. El inventario de bundle rechaza exactamente `_internal/assets/design-reference.png`, por lo que generación/verificación de manifiesto y publicación de ZIP también lo rechazan, incluso si el manifiesto fabricado declara hashes y conjunto coherentes. Se aplica casefold al recorrido completo, conforme a la comparación de rutas portable existente. La detección de colisiones de mayúsculas existente se conserva antes de omitir recursos. No se añaden filtros genéricos por basename ni se restringen otros nombres o ubicaciones.

Se buscó literalmente `design-reference` en `main.py`, `ui_desktop`, `core`, `src` y `config`, sin coincidencias. El archivo original sigue en Git y sus bytes permanecen intactos: SHA-256 `0b8d1fd04431cc6307e7227a423a88fdf5f8017374ed6d7342a7e03f3e1db267`. No se alteró UI, runtime de negocio, CI, lock, instalador ni migración.

Los 12 casos nuevos prueban la exclusión en el repositorio real, el inventario de dos repositorios Git temporales con variación de mayúsculas, cuatro superficies de aceptación de bundles/manifiestos fabricados con dos variantes de ruta y un control positivo para otros nombres/ubicaciones. El control positivo permite `assets/examples/design-reference.png` y `assets/design-reference-v2.png`, demostrando que la regla apunta al recurso exacto.

| Verificación | Resultado |
| --- | --- |
| Antes del parche de producto | 11 canarios fallidos, 1 control positivo aprobado |
| Después, mismo archivo de pruebas por bytes | 12 aprobados |
| Suite mantenida: receta, revisión, procedencia, wrappers y OPS10 | 97 aprobados en 19.80 s |
| Diff y commit | Dos archivos, worktree limpio; sin errores de whitespace |
| Referencia original e histórico bundle/ZIP 9f | Bytes conservados |
| Build / instalador / publicación | No ejecutados |

Se usó el intérprete temporal fijado `C:/Users/Consu/AppData/Local/Temp/metodobase-desktop-package-20261019/Scripts/python.exe`, con `-B -m pytest`, caché de pytest desactivada y basetemp separado para cada pasada. Los artefactos de prueba son sintéticos y nunca se lanzan.

Evidencia conservada: [baseline de fuentes y canario](desktop-ops10-author-before-source.json), [canario anterior exacto](desktop-ops10-author-before-canary.txt), [log rojo](desktop-ops10-author-before.log), [JUnit rojo](desktop-ops10-author-before.xml), [log verde dirigido](desktop-ops10-author-after.log), [JUnit verde dirigido](desktop-ops10-author-after.xml), [suite completa](desktop-ops10-author-complete.log), [JUnit completo](desktop-ops10-author-complete.xml), [freeze y conservación del histórico](desktop-ops10-author-freeze-source.json) y [hashes de evidencia](desktop-ops10-author-evidence-manifest.json).

Pendiente: revisión independiente de QA del delta, integración por root y nuevo build sobre el commit integrado y congelado que root seleccione. El artefacto 9f anterior conserva su estado histórico de integridad/Qt aceptados y distribución pendiente. Este parche de fuente no acredita que ya exista un nuevo candidato sin el recurso. Los pendientes de licencia/autoridad SEC01, instalador, firma, flujos de negocio y validación nativa Linux/macOS se mantienen.

