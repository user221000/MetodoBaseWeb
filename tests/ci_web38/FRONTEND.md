# Focos y frontend del runner38

Esta hija del runner1173 conecta los mapas nuevos revisados en rutas38 y añade
cinco opciones al mismo runner. No modifica los mapas/validadores37 ni los
selectores serial, parallel o history.

| Opción | Selección | Alcance |
| --- | --- | --- |
| product38-sqlite | test_product_analytics_v2.py | agregado v2; sin companion de fixtures |
| password38-sqlite | test_new_password_policy.py + test_new_password_policy_http.py | objetos Root originales, composición38 |
| observer38-pure | test_generation_characterization_observer.py | callbacks puros; no companion ni fixtures SQL |
| node-product38 | product-analytics-v2-review.cjs | 13 labels nuevos, VM/DOM/transport doubles |
| node-password38 | new-password-minimum-review.cjs | 25 labels nuevos Unicode/handlers/Api |

Los focos pytest usan el collector independiente, JUnit exacto, scope/journal,
source/env photo y pip check originales, sin nueva cobertura global. El módulo
observer trae sus fixtures autouse no-SQL. El módulo de agregado conserva el
conftest unitario heredado; ese bootstrap no acredita una migración física.

`node` conserva su función/51 scripts/865 obligaciones literales. `node-current`
usa node-current38.json con los mismos13 comandos/147 labels; `node-routines-
onboarding` usa node-routines-onboarding38.json con8/94. Sólo se transportan los
3+2 pins de dependencias que cambió el producto. Se conservan todos los scripts,
datos positivos y validadores originales. Los nuevos13/25 están en fases
separadas, sin sumarlos retroactivamente a147/94/865.

`node-new38.json` conserva los labels ordenados y el cierre RAW de entradas que
revisó OpsCI/Artifact. El runner exige esas entradas antes y después del proceso,
exit0 y node_cases original; usa browser_offline31 para prohibir red/procesos
del harness. Child_environment elimina BROWSER31_SOURCE y SEC_BROWSER_SOURCE;
el gate de rutinas también elimina ROUTINES_AUTH_GUARD_SOURCE. La Api leída es la
de este checkout, no una ruta heredada del entorno. Nada de Node demuestra RLS,
HTTP real, navegador nativo o lectura humana.

Estado de esta hija: fuente/AST/inversas/RAW bindings preparados, sin Node,
pytest, SQL, imports SUT ni servicios ejecutados. Cualquier resultado futuro
debe citar fuente física completa más HEAD base sin atribuir la beta sin commit
al producto878, y conservar los fallos originales si los hay.
