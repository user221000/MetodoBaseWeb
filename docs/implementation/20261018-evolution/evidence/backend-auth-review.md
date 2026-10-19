# Revisión independiente de identidad y autorización

Revisor: agente backend/datos, distinto del autor agente seguridad. Entorno local sintético Windows/Python 3.12.13. Revisión del diff integrado de `web/auth.py`, `web/auth_deps.py`, `web/routes/auth.py`, `web/routes/clientes.py`, `web/routes/team.py`, `web/services/permissions.py` y `config/settings.py`.

Resultado: sin observaciones altas/críticas nuevas en el alcance de contención revisado. La identidad persistida sustituye los permisos del token en cada acceso. Una reducción de rol cambia el permiso efectivo; una cuenta inactiva, eliminada o cuya pertenencia difiere del token deja de autenticar. Login por contraseña y Google, canje y refresh consumen el mismo transformador. La ruta pública de mantenimiento desaparece, el alta de clientes exige su permiso y las acciones/roles desconocidos no conceden permisos.

Se revisó la carrera de refresh con logout: la segunda lectura de versión impide renovar después de la revocación; si la revocación ocurre después de esa lectura, cualquier token emitido conserva la versión antigua y la comprobación persistida lo rechaza. La transacción de logout aumenta versión y revoca refresh juntos. El corto TTL de access se conserva al recordar sesión.

Validación independiente ejecutada: `python -X utf8 tests/run_isolated.py tests/test_identity_security.py -q --tb=short`, **25 passed**, dos avisos de dependencias/deprecación. Resultado completo: [backend-auth-review.log](backend-auth-review.log). Los proveedores no recibieron solicitudes; las cuentas y conexiones pertenecen a SQLite efímero.

Límites: esta revisión no cierra R02/R10/R32 completos. Sigue pendiente la matriz integrada completa de recursos/roles, PostgreSQL con privilegios restringidos, pruebas de navegador y revocación concurrente real entre procesos. Aceptar tokens históricos con versión cero es una transición conservadora explícita; formato HMAC propio, inventario/rotación de claves, almacenamiento de tokens en navegador, MFA y política de recuperación requieren sus entregas y validación separadas. No se afirma una auditoría de penetración ni cumplimiento normativo.
