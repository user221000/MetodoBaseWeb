# Delta CI28

Worktree aislado desde `92615d74ee3a4bd82333c4606cca7898eb324a88`. MAIN, composer y la rama del autor R16 no se modificaron.

CI exige21 reportes PostgreSQL distintos: conserva los19 anteriores y agrega `pytest-postgres-recovery-migrations.xml` y `pytest-postgres-recovery.xml`. Ambos comandos nuevos filtran explícitamente `-k postgresql`; corresponden a los6 casos de migración28 y11 de runtime ya aceptados localmente por QA. Este lote verifica su conexión a CI y no repite sus ejecuciones.

El reporte de restore conserva el probe pequeño26 y añade el nodo completo `tests/integration_recovery28_restore_review.py::test_revision28_restore_preserves_recovery_and_all_revision26_27_contracts`. La prueba completa27, los helpers y sus assertions permanecen intactos. El fixture de diario actual imprime `expected_head()` y CI exige literalmente `20261019_account_recovery`, con26 tablas y el mismo parser estructurado de metadata.

`tests/verify_recovery_ci.py` compara el YAML completo con una transformación cerrada del baseline27. Los snapshots Git `00d2114` y `8435bd0` tienen bytes idénticos; se conserva una copia cruda y su SHA256. Sólo admite los dos nuevos steps/reportes, el conteo estricto21, el nodo de restore28 y el literal de marker28. Para el fixture sólo admite import/call de `expected_head()` y el docstring de head actual; el resto de su AST debe coincidir.

El verificador histórico `tests/verify_diary_ci.py` sigue siendo criterio27. No se cambió para aceptar otro job PostgreSQL, ni se ejecuta sobre28. Tampoco se repiten los162 contratos VM o los91 canarios genéricos ya aceptados. Los scripts de parser/guard, los drivers browser17+4 y las pruebas/helpers de restore tienen sus hashes anteriores verificados.

Comprobaciones locales nuevas:

- Antes: el workflow27 crudo no satisface el nuevo contrato28; el fallo se conserva en `before.log`.
- Después:21 reportes producidos/exigidos y todos los paths referenciados presentes;63 bloques pasan `bash -n`.
- Cada reporte nuevo pasa el caso positivo y rechaza siete variantes: ausente, archivo vacío, XML malformado, cero casos, skip, failure y error. Se comprueban además omisión y duplicado del listado21.
- Ocho mutaciones del workflow son rechazadas: step ausente, reporte anterior omitido, guard XML relajado, filtro PostgreSQL eliminado, restore27, marker27, job ajeno cambiado y mínimo browser modificado.
- La expresión real del marker se evalúa aisladamente y produce head28/26 tablas, sin ejecutar el servidor ni crear esquema. La función Bash real se ensaya con procesos inertes: marker28 ejecuta ambos drivers sintéticos; marker27 impide ejecutarlos. Ambos casos registran el mismo PID al iniciar y limpiar.

`final-check/review.json` contiene los resultados y el hash de `canaries-raw.zip`, que conserva los reportes XML, scripts y eventos crudos de los procesos inertes. La primera tanda satisfactoria anterior a añadir los ocho canarios del delta se mantuvo en un directorio propio de Temp.

Ejecución reproducible: `python -X utf8 tests/verify_recovery_ci.py --output <directorio-nuevo>`. No requiere PostgreSQL, Docker ni navegador. El alcance observado es Windows local con Git Bash; no acredita ejecución de Actions, Linux, imagen remota, proveedor ni correo real. La revisión independiente de este commit sigue pendiente.
