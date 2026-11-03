# Publicación y recuperación del esquema de devoluciones

Este procedimiento prepara una decisión operativa revisable. No ejecuta una migración, rollback o restauración en producción. El punto de partida observado es código `fc7950ec` y esquema40 `20261031_gym_equipment`; el candidato exige esquema41 `20261102_payment_refund_facts`.

Antes de publicar se deben vincular commit, imagen, entorno, base y revisión reales; completar las pruebas exigidas y disponer de una copia cifrada verificable, su clave custodiada por separado y un ensayo aislado. La imagen40 rechaza41 y la imagen41 rechaza40: la publicación requiere una ventana coordinada y no se presenta como una transición sin interrupción. El único ensayo autorizado en esta ejecución restaura en cuarentena local, sin DDL ni escrituras de filas productivas.

| Estado real al decidir | Recuperación admisible |
|---|---|
| Esquema40, antes del nuevo DDL | Puede recuperarse una imagen40 verificada; no requiere downgrade ni restaurar datos. Comprobar readiness, identidad y recorridos críticos. |
| Esquema41, las tres columnas nuevas globalmente NULL | Revisar una ventana de recuperación separada. Sólo con lectura global acreditada de cero hechos y escritores controlados puede evaluarse el downgrade genuino41→40, cuyo guard se conserva. Después verificar contrato40 e imagen compatible. |
| Esquema41, cualquier hecho de devolución observado | Mantener41 y corregir hacia delante con una imagen compatible. El downgrade rechaza descartar esos hechos. No reinstalar automáticamente la imagen40 ni restaurar una instantánea antigua sobre datos posteriores. |

La inspección necesaria para el segundo caso es de sólo lectura, usando el canal administrativo autorizado con visibilidad global. Un error o un resultado filtrado por RLS no equivale a cero:

```sql
SELECT count(*) FROM public.payments
WHERE refund_amount_cents IS NOT NULL
   OR refund_observed_at IS NOT NULL
   OR stripe_charge_id IS NOT NULL;
```

Se conservan inbox, pagos, consumos, cuentas y solicitudes de privacidad. No se borran observaciones para superar el guard del downgrade, no se hace `stamp` para eludir contratos y no se termina una conexión ajena para completar un ensayo. Una restauración de producción requeriría un plan separado de conciliación que preserve lo ocurrido después de la instantánea.

El ensayo de esta ejecución exporta una única instantánea SQL consistente de lectura y obtiene sólo objetos actuales ligados a descriptores, con límites de número y bytes e integridad verificada. Cifra los artefactos y los logs, restaura en PostgreSQL propio de loopback, contrasta filas y objetos, aplica41 sólo allí y comprueba RLS y el rol restringido. No ejecuta workers, correo o jobs contra los datos restaurados. El cierre exige cero sesiones, DROP normal de la base propia, ausencia fresca del OID y parada normal del servidor propio. Los restos del clúster permanecen bajo ACL privada; no se afirma borrado seguro.

Los procesos nativos de PostgreSQL reciben sólo contexto Windows mínimo y parámetros libpq explícitos; no heredan la clave de cifrado ni secretos de la aplicación. Railway/SSH usa además PROGRAMDATA, requerido por el cliente Windows existente, sin ampliar el entorno de PostgreSQL. Alembic recibe una conexión y URL explícitas de la base local, entorno testing y carpeta de datos en E para impedir un fallback SQLite bajo C.

El resultado del ensayo debe indicar sus tiempos medidos y fallos conservados. Un ensayo exitoso de una instantánea no fija un RPO/RTO, activa un calendario, configura PITR o recupera cuarenta objetos históricos ausentes. Esas obligaciones mantienen responsable y criterio propio en el seguimiento de auditoría.
