# Matriz162 por fuente

No se suman fases distintas ni se reetiquetan intentos rechazados.

| Gate | Fuente | Estado | Evidencia / límite |
|---|---|---|---|
| R05 fullscan | a02d7faa82283969767df02ee3ed24b2c9209079 | aceptado_acotado | 16240 archivos; 54213 raw=clasificadas;0 pendientes;615 untracked exactos. No cubre dc9f ni sustituye broad. |
| R05 focal62 | a02d7faa82283969767df02ee3ed24b2c9209079 | aceptado_acotado | 35v8+27v9=62PASS;186 fases;0F/E/skip/duplicados. Selección focal, no serial/n2/cobertura. |
| PG509 previo migration37 | fuente del intento76152, conservada en sus recibos | rechazado | Body pasó; teardown Owned sessions remain;53/27/Native no iniciados. 57 ausentes tras cierre normal posterior; el intento original sigue rechazado. |
| PG509 previo legacy-followup | 5617cd445f5f1448087a51d293c1c17281364a6f | rechazado | 2 cases/1ERRORteardown/0FAIL;18 receipts closed+1created original. 18 ya ausentes+1DROP normal exacto;19 ausencias frescas no convierten el gate en PASS. |
| Diagnóstico original legacy focal1 | 5617cd445f5f1448087a51d293c1c17281364a6f | observacion_aceptada | 3engines/6pools/3dispose;25checkout=25checkin;5PIDs;capture_completeTrue/errors0. No prueba retrospectiva de race o préstamo vivo. |
| Main focal13 | dc9f532a4ebbc458e65dfd567277dad28a3af072 | aceptado_acotado | 7 guardas+6contratos53=13PASS;39fases;0F/E/skip/duplicados. Pruebas puras/contratos, no13PG ni509. |
| PG focal1 cierre común | dc9f532a4ebbc458e65dfd567277dad28a3af072 | aceptado_acotado | 1PASS/1UUID normal;3pools/3Record/5DBAPI-PIDs/6dispose;errores0;final0. No causa histórica ni aceptación509. |
| PG509 actual93251 | dc9f532a4ebbc458e65dfd567277dad28a3af072 | en_curso_sin_resultado | 429+53+27, presupuesto71UUID; ejecución Root iniciada. No se afirma ningún resultado pendiente ni inicio/aceptación53/27/Native. |
| Native35/broad/imagen/Redis/carga/backup | requiere fuente y autoridad de cada gate | pendiente | Preparaciones y resultados históricos separados. Sin nueva aceptación física, HA, proveedor, publicación ni despliegue. |
