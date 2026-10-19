# R14 backend: revisión independiente de seguridad

Se revisó el commit autor `a5a6bf147f05e1f559357d45e314e5a10815c47b` en copia aislada. No se modificó producto, migraciones, fixtures históricas, fuentes del autor ni main. No se confirmó un bloqueador nuevo de privacidad o integridad dentro de este alcance. Esta conclusión no acepta restore27, composición de navegador, integración ni producción.

El contrato principal leído fue `DIARIO_PERSISTENCIA_PROPUESTA.md` del checkout de coordinación: ese documento no estaba en el commit autor. El contrato técnico y la congelación del autor se leyeron de su propio checkout. Sus 20 fuentes propias, 14 dependencias y 44 archivos históricos coinciden con la congelación de huella `6d8c832fc84121cf4f540790bd5376588cd203084b6dd330075109b46359ff5d`.

## Resultado y alcance de los canarios

Los gates independientes suman **34 casos distintos verdes**: 25 canarios HTTP/SQLite propios, 3 casos históricos OWNER/cursors intactos, 2 transiciones de membresía y 4 casos PostgreSQL nuevos. La prueba histórica `test_owner_authority_excludes_portfolio_even_with_individual_persisted_type` conserva sus bytes. No se reescribieron expectativas históricas para ampliar OWNER.

Se comprobó que selección vacía no evita el doble dueño ni la exclusión de fuentes borradas. Un snapshot ya autorizado sobrevive a reasignar el origen y permite completar la comida histórica, pero el origen reasignado no autoriza consumo nuevo ni vuelve a exportarse como plan propio. PATCH masivo no creó días; el cursor por fecha no seleccionó otra cuenta.

El ACK perdido real en SQLite produjo 503, conservó el commit realizado y obligó a releer: repetir con versión anterior recibió 409, sin duplicado ni sustitución del agua. El fallo de rollback se mantuvo como guardado no confirmado. Los errores sintéticos con SQL/parámetros no aparecieron en respuesta ni en logs capturados.

El límite HTTP exacto de 16 KiB se aceptó y el primer byte adicional rechazó toda la operación conservando el día. Una prueba ASGI directa comprobó que un Content-Length pequeño no evita la guarda ni permite leer el siguiente chunk o alcanzar el parser. Esto comprueba la frontera de aplicación, no un límite de memoria del servidor HTTP. Una fila sintética dentro del CHECK de caracteres, pero fuera del límite UTF-8, fue rechazada por GET, exportación y PATCH sin truncarla ni sobrescribirla. También se rechazaron miembros JSON duplicados del snapshot.

En PostgreSQL restringido, un hook de coordinación cambió rol, actividad o invitación mediante SQL real justo antes del UPDATE de lock. El servicio revalidó bajo el lock, denegó los tres casos y no creó filas. Una Session ya comprometida no pudo cambiar de sujeto para leer diario ni exportar; mantuvo afinidad con su sujeto original y la conexión reutilizada sin contexto no vio filas. No se simuló el resultado de ninguna consulta de negocio.

La comparación independiente de targets SQLite/PostgreSQL confirma que sólo se añade `personal_diary_days` y sus entradas de seguridad; las tablas previas, políticas previas y helper de tenant son idénticos. El nuevo esquema tiene 26 tablas de negocio y 20 familias de tenant. Los cuatro casos PostgreSQL finales utilizaron bases UUID nuevas realmente migradas; los intentos de preparación anteriores usaron otras bases UUID propias y también se eliminaron. No se reinició el cluster ni se cambiaron roles o bases compartidas.

## Membresía profesional y espacio personal

El canario adicional guardó agua y snapshot mientras la identidad era miembro profesional, retiró la membresía, comprobó 401 del bearer anterior y volvió a entrar mediante password login real. La nueva versión de sesión conserva usuario activo, adopta VIEWER/tipo usuario sin team_gym_id y permite recuperar/exportar el diario completo. La cartera del antiguo gimnasio queda fuera. El propietario conserva su propio acceso.

SaaS usa DELETE HTTP real de equipo. La API independiente no monta gestión de equipo y ya reserva sus adaptadores profesionales de clientes a OWNER; su preparación usa el servicio real `revoke_membership`, con OWNER persistido y tenant explícito. La autenticación posterior y las rutas personales siguen siendo HTTP reales en ambas composiciones. Se distingue esta revocación, que conserva identidad e historia, de la cuenta inactiva o el OWNER ambiguo, que deben denegarse.

## Fuentes, errores de harness y evidencia

`source.json` liga las 78 fuentes originales, sus huellas RAW del autor y de la copia, los dos drivers nuevos y la prueba OWNER histórica. Once archivos fueron convertidos entre LF/CRLF por Git; se probó igualdad normalizada y se registraron ambas huellas sin sustituir las originales. Los 28 casos iniciales de límites/HTTP conservan una copia del prefijo exacto probado, ligada por SHA; el archivo final sólo añade el recorrido de membresía, probado por separado. El driver PG final permaneció estable durante su gate final.

Se conservan por separado los errores de preparación: la primera comprobación suponía igualdad RAW entre checkouts; el primer wrapper PG omitió una variable privada y produjo cuatro errores de setup; un canario de invitación esperaba 401 cuando el servicio ya denegaba correctamente con 403; y el comparador de targets suponía listas de políticas PostgreSQL en metadatos SQLite que sólo contienen dialecto. En el recorrido de membresía, los dos primeros intentos API esperaron acceso profesional 200 y luego un endpoint de equipo que no existe. Se conservaron fuentes, trazas y XML; se corrigió sólo el harness. No fueron fallos del producto ni se usaron como evidencia verde.

Un fallo de pytest incluyó un bearer de la fixture sintética en sus argumentos. Toda copia publicada redacta esos tokens y cualquier URL/password privado. Los RAW originales permanecen sólo en Temp; el manifiesto registra hash anterior, hash publicado y conteos de redacción. Se decodificaron logs PowerShell UTF-16 a UTF-8 LF, con esa transformación identificada; no se cambió la historia de fuentes.

Observación menor reproducida: `decode_meals` acepta recorded_at consciente con offset no nulo, aunque el contrato describe un sello UTC. El API no acepta ese campo y las escrituras públicas generan UTC mediante `_clock`. No se demostró fuga, pérdida ni alteración mediante HTTP; se deja explícito como precisión del validador, sin atribuir cierre adicional.

## Repetición

Con el entorno candidato aislado, el driver HTTP completo final contiene 27 casos propios y los tres casos históricos se ejecutan sin modificación:

```text
python -X utf8 tests/run_isolated.py tests/test_personal_diary_security_review.py tests/test_privacy_export_review.py -q --tb=short
```

Para PostgreSQL, coordinar primero el uso del cluster sintético 55483 y cargar exclusivamente la configuración privada de QA sin publicarla. Cada fixture crea y elimina sólo su base UUID:

```text
python -X utf8 tests/run_isolated.py tests/integration_personal_diary_security_review.py -q --tb=short
```

No se usa proveedor, correo real, usuario real ni red externa. La revisión no sustituye los gates del autor, la revisión independiente de QA ni el restore poblado27 coordinado por separado.
