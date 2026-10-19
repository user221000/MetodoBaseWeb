# MFA31: cuatro canarios PostgreSQL independientes

Fuente original56 exacta, sin overlays ni correcciones posteriores. Una DB UUID propia, migrada realmente a31, con rol app NOSUPER/NOBYPASS/nonowner y FORCE RLS en las dos familias nuevas. Cuatro casos verdes; no es replay de los17 PG del autor ni aceptación de restore31.

El pool de una conexión utiliza el mismo backend: el actor personal de MFA queda separado de otro tenant profesional. Session y Connection, commit/rollback y setting de sesión persistente quedan sombreados por LOCAL vacío al BEGIN; una reasignación de dueño falla42501. No se atribuye protección contra SQL arbitrario de una aplicación comprometida.

Una cuenta bloqueada provoca409 NOWAIT sin consumir proof/recovery ni crear refresh; la misma prueba funciona tras liberar. Otra intercalación confirma verify-login mientras logout real espera el lock Usuario: pg_blocking_pids observó la dependencia. Tras ambos commits, access/refresh devueltos quedan inválidos, ningún refresh activo y factor/challenge consumidos una vez. Las dos hebras se unieron y los engines se cerraron.

Otro caso hace cruzar el vencimiento entre búsqueda inicial y búsqueda bajo lock:400 sin consumir factor/proof ni crear sesión. Es control de relectura temporal; no se afirma una espera de NOWAIT. DB propia eliminada sin FORCE y con cero conexiones; una conexión posterior comprobó ausencia DB y PIDs propios. No roles/HBA/catálogos globales, otras DB, Chrome, providers ni benchmarks.
