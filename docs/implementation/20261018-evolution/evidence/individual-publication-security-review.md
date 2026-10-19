# Revisión independiente de publicación individual, revisión26

Fuentes revisadas: `backend-individual-publication-final-source.json`, digest del conjunto `a621ebad709be5b75e3327d240f91437394076f12ade83116eead569a16bd9c6`. Los19 SHA del manifiesto coinciden con los archivos revisados. Revisión26 es una revisión de esquema; conserva25 tablas de negocio y19 familias tenant. Este agente no edita esos19 archivos.

## Observaciones de contrato

La ruta toma el sujeto de la identidad autenticada y pasa su reserva como parámetro interno distinto del ledger profesional. El worker y el repositorio rechazan parámetros de ambos protocolos a la vez. La publicación individual bloquea la fila canónica de Usuario y vuelve a leer reserva/estado; el CAS del repositorio exige usuario, protocolo1, estado reserved y ausencia de asociación/marcador. La misma transacción guarda Plan, referencia de objeto listo y completed/persisted; el worker usa la publicación de PDF privada existente. El repositorio también mantiene compatibilidad para callers sin objeto, por lo que no debe afirmarse que cualquier llamada interna al repositorio demuestra por sí sola la existencia de un PDF.

La compensación hace rollback protegido y lee de nuevo el estado bajo el bloqueo de cuenta. Conserva consumo completed/persisted aunque el FK del Plan haya quedado NULL; no reconstruye asociaciones legacy ni libera protocolo0 ambiguo. Una liberación sólo descuenta el periodo capturado y su estado evita repetir el descuento. El delta final usa `sub.mes_actual` en débito y reserva, conservando las regresiones independientes del cambio de mes. Fallos de rollback/consulta/commit devuelven503 estable sin SQL o representación de excepción. Estas observaciones de código complementan los gates PostgreSQL/restore asignados a QA; no los repiten ni sustituyen.

En el freeze anterior, el logger del catch general de la ruta incluía `user_id`; el de compensación ya registraba sólo clase. El delta del lector descrito al final también retira ese identificador del catch general, sin autorizar una afirmación sobre todos los logs de la aplicación. Después de un resultado publicado, un error de entrega todavía puede presentarse al usuario como400/500 genérico; la contabilización sigue conservada, pero la recuperación UX e idempotencia del cliente personal requieren el seguimiento correspondiente.

## Bloqueo de asociación legacy

[Tres negativos propios](../../../../tests/test_individual_publication_security_review.py), [resultado](individual-publication-security-before.log), [JUnit](individual-publication-security-before.xml), [huella](individual-publication-security-before-source.json):2 fallos/1 aprobado,3.57s;22 fuentes estables. El test usa router personal, ORM y DB SQLite aislados con identidad sustituida explícitamente por el fixture de billing. No es otro ensayo de JWT/RLS ni de explotación productiva.

La fixture crea una asociación legacy incoherente que los FK de una sola columna permiten: reserva completed de A → Plan con `gym_id=A` → Cliente con `gym_id=B`. Su JSON lleva un marcador sintético. El repositorio nuevo no genera ese estado; la prueba no atribuye un origen histórico concreto ni afirma que todas las filas legacy estén dañadas.

El replay busca Plan por ID+gym+deleted_at pero omite el dueño del Cliente: retorna200 y el JSON ambiguo. El verificador `finish_generation(success=True)` usa la misma condición incompleta y lo acepta. La corrección propuesta es comprobar la pertenencia y disponibilidad del Cliente mediante el mismo doble predicado que ya usa la lectura de PDF. Debe conservar consumo y solicitar revisión ante asociación ambigua, sin adoptar otro Plan ni fabricar reparación histórica.

El tercer caso usa otro Usuario existente como caller de compensación y demuestra que no modifica la reserva ni los contadores de A o B. Root aceptó el bloqueo legacy y asignó el cambio de producto a backend. Las tres pruebas y los artefactos rojos se conservan sin modificar para repetirlos contra una huella nueva.

No hubo operación de proveedor, envío de correo, migración productiva, reconciliación histórica ni cambio de retención. El dictamen de esa primera etapa quedó condicionado: la conservación de créditos seguía respaldada por los ensayos anteriores, pero los dos negativos impedían aceptar la autorización de replay y verificación legacy.

## Repetición independiente del lector corregido

Backend entregó [un freeze nuevo](backend-individual-reader-source.json), digest `246ff3f117f7518cb06b02811ce3c9a2952dd16b0b9d5a261bb145ebb03de621`. Sólo cambian dos archivos de producto respecto al freeze anterior: `generation_quota.py` y `usuario.py`. Los modelos, DDL, targets y fixtures mantienen sus hashes. Se revisaron los20 archivos del manifest y los dos tests independientes listados; las tres pruebas de esta revisión conservan exactamente el SHA registrado en el resultado rojo.

El lector compartido une Plan con Cliente por identificador y exige `Plan.gym_id=subject`, `Cliente.gym_id=subject` y `deleted_at IS NULL` en ambos. Permite el historial de clientes inactivos. Replay, verificación de éxito y retorno final usan ese mismo límite, con `populate_existing` para no reutilizar una proyección ORM obsoleta. El retorno final vuelve a consultar después de finish, de modo que una asociación eliminada o mezclada durante ese intervalo se indica como no disponible sin devolver su JSON ni liberar consumo. El catch general de generación registra únicamente clase técnica.

[Resultado independiente](individual-publication-security-after.log), [JUnit](individual-publication-security-after.xml), [fuentes](individual-publication-security-after-source.json):13 aprobadas en4.29s,24 fuentes estables. Incluye las3 pruebas negativas intactas y10 casos autor del lector: propio/inactivo, soft-delete de Plan/Cliente, mezcla/Plan extranjero, cambios después de verificar y log clasificado. No se repitieron por rutina los gates PostgreSQL, migraciones, restore ni navegador que ejecuta QA.

Se acepta el delta del lector para el alcance de código/SQLite aislado registrado: los dos negativos de autorización quedan resueltos sin modificar sus expectativas ni reparar asociaciones históricas. La evidencia roja se conserva. La aceptación de composición PostgreSQL y navegador, la recuperación UX y los demás requisitos abiertos permanecen separados.
