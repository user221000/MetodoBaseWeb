# Integridad de los baselines del verificador CI28

Delta aislado sobre `5db0732`, sin modificar MAIN, composer, workflow, fixture actual, parsers, verifier27, contratos PostgreSQL ni sus snapshots revisados.

Los dos probes de QA se reprodujeron con CLI `--verify-only` en copias Temp: modificar simultáneamente el fixture y su snapshot permitía el mismo AST ajeno; modificar verifier27 y su hash en `baseline.json` también se aceptaba. `before/review.json` conserva ambas aceptaciones indebidas. La evidencia independiente original permanece intacta; su JSON tiene SHA256 `9eb643fc03ccb2294cea6a7d109a923348358fc18010ee2b956af0e70b40a3f0`.

El verificador ahora fija el SHA256 del manifiesto revisado (`ec3b455cef7a4a3bdb5a21640aa94e2edc8854909c54e79074629018e118f47e`) antes de usar sus hashes. Comprueba además el SHA del snapshot del fixture antes de parsear/comparar su AST. La normalización permitida sigue siendo exclusivamente CRLF a LF para checkouts equivalentes.

La revisión focal detectó otra omisión en la misma comparación: se descartaba cualquier primer `ast.Expr`, aunque fuese una llamada ejecutable en lugar del docstring permitido. `docstring-before.json` conserva su aceptación en una sombra. Ahora sólo se admite `Expr(Constant(str))` antes de aplicar la excepción documental; no se ejecutó el fixture manipulado.

`final-trust/review.json` demuestra cinco casos: control intacto y cambio literal del docstring aceptados; los dos ataques de QA y la sustitución por una llamada rechazados. Todos los archivos reales copiados al ensayo conservaron sus hashes. Los ZIP incluyen copias y salidas crudas; contienen únicamente fuentes y datos sintéticos del ensayo.

El replay final del verificador autor también pasa:21 reportes,18 canarios del guard,8 mutaciones rechazadas,2 procesos Bash inertes con limpieza del PID y63 bloques sintácticamente válidos. No se repitieron PostgreSQL, broad/backend,162 VM,91 canarios históricos ni navegador. Los parsers y assertions históricos permanecen sin cambios.

Reproducción: `python -X utf8 tests/verify_recovery_ci_baseline_trust.py --output <directorio-nuevo>`. Este commit sigue pendiente de revisión independiente. El alcance observado es local Windows; no acredita Actions, Linux remoto, despliegue ni ejecución de servicios externos.
