# Actualización parcial del perfil web: QA-20

API ahora guarda los campos válidos enviados sin calcular con información
todavía ausente. El recálculo anterior fallaba en objetivoNULL y sus claves de
macros no eran persistidas por el repositorio ni retornadas por esta ruta.
Generación mantiene su propia validación del perfil completo. SaaS conserva su
comportamiento; la edición no rellena datos, cambia permisos o consume cuota.

La misma prueba corregida de ocho casos produce dos fallos antes y ocho pases
después. Los cuatro fallos adicionales iniciales fueron un framing erróneo:
legacyNULL se serializa como declaración desconocida canónica. Se conserva la
preimagen y se comprueba que el valor anterior permanece exacto.

La primera composición posterior conserva 57 pases y14 errores de setup:
fixtures34 contra ORM35. El compañero35 usa las mismas aserciones originales
con bootstrap35, sin alterar las pruebas34, y pasa14/14. La fase final contiene
22 pases (8+14), fuente y92 distribuciones/Python estables; no sumar replays.
Ruff de fuentes nuevas y pip check salen0. Sólo actualizar_cliente cambia en
el AST del módulo API. QA independiente continúa; no aceptación PostgreSQL,
Chrome, MAIN ni despliegue. Trabajo limitado al servicio web.

Los originales completos se conservan en archivo privado protegido antes del
payload y verificado por readback; las ACL iniciales de carpetas anteriores no
se atestan retroactivamente. XML público es proyección estructural explícita.
