# Rotación de la clave de firma de sesiones

Procedimiento para B20 sobre el esquema37. El código utiliza una clave `SECRET_KEY` por generación de workers y tokens HMAC con issuer/audience verificados. La rotación se realiza mediante un corte coordinado y nueva autenticación; este procedimiento no incorpora otro formato de token ni afirma rotación sin interrupción.

## Preparar un corte concreto

1. Fijar commit, imagen/digest, instancia y responsables del entorno. Conservar el artefacto anterior para poder revertir código manteniendo la nueva clave. Revisar también workers que emitan o verifiquen tokens.
2. Crear una clave nueva aleatoria de al menos256 bits mediante el gestor de secretos autorizado del entorno. Registrar únicamente su identificador/versionado en ese gestor. Evitar claves en argumentos de shell, historial, tickets, capturas, logs, repositorio o evidencias.
3. Conservar por separado `MFA_ENCRYPTION_KEY`, claves de proveedores y claves de objetos. El cifrado MFA exige su propia clave independiente; cambiarla requiere un procedimiento de recifrado y custodia distinto.
4. Ensayar el corte con cuentas sintéticas en un entorno aislado. El comando reproducible de abajo comprueba API y SaaS sobre el esquema37; no conecta a producción ni modifica el gestor de secretos.

```powershell
python -B -X utf8 tests/run_isolated.py tests/test_auth_key_rotation37.py -q --tb=short
```

Guardar salida y JUnit en un directorio privado preparado antes de ejecutar. Registrar fuente, intérprete, dependencias, resultado y cambios de configuración por identificadores. La revisión local no autoriza un corte en producción.

## Ejecutar en el entorno autorizado

1. Abrir una ventana de mantenimiento para autenticación y detener coordinadamente todos los emisores/verificadores anteriores. Evitar generaciones con claves diferentes atendiendo tráfico simultáneamente.
2. Sustituir `SECRET_KEY` en el gestor del entorno y arrancar todos los workers con la imagen fijada. `init_auth()` captura la clave: editar una variable sin renovar el proceso no demuestra una rotación.
3. Conservar un token access y pruebas refresh sintéticos anteriores. Comprobar401 de recurso, refresh JSON y refresh cookie anteriores, sin credenciales en salida pública. Comprobar después login nuevo, identidad persistida, rotación refresh y MFA con un factor previamente enrolado. Una denegación de origen/CSRF por sí sola no demuestra rechazo criptográfico.
4. Verificar reautenticación y manejo de401 en el navegador. Las operaciones que quedaron con resultado ambiguo deben consultar su identificador/idempotencia existente antes de volver a generarlas.
5. Revisar cookies de sesión OAuth y cursores firmados: los anteriores pueden necesitar reiniciar su recorrido/paginación. Las claves HMAC de limitación por cuenta cambian; observar la nueva ventana sin vaciar Redis ni imprimir sus claves.
6. Registrar hora, generaciones retiradas/nuevas, identificador de versión del secreto, commit/digest y resultados sintéticos. Las contraseñas y el ciphertext MFA permanecen sujetos a sus mecanismos independientes.

## Recuperación y reversión

Revertir código conserva la clave nueva en todos los workers. Restaurar una clave de firma anterior puede volver a aceptar tokens antiguos todavía vigentes; el ensayo incluye un control que demuestra ese riesgo. Una clave sospechosa se retira del servicio y no se usa como mecanismo de recuperación. Si la nueva clave no puede utilizarse, preparar otra generación de clave y repetir el corte coordinado. No recuperar MFA mediante una contraseña administrativa o un bypass improvisado.

La rotación real, su custodia, disponibilidad y comprobación sobre todas las réplicas requieren el entorno y la autorización correspondientes. Los ensayos locales no prueban esos hechos operativos.
