# Foco al actualizar el seguimiento

El addon independiente de768px encontró que el botón nativo se deshabilitaba durante la consulta y perdía el foco al rehabilitarse. El uso por teclado original funcionaba; la nueva regresión comprueba además la continuidad del foco. El rojo y sus recursos cerrados se conservan.

Se conserva el botón disabled para impedir solicitudes repetidas. Al terminar se restaura el foco sólo si la acción empezó en ese botón, el usuario no cambió de control ni expresó otra intención, el contexto sigue válido y el control continúa conectado y habilitado. No se devuelve el foco a un contexto de sesión invalidado. Cuatro casos DOM controlados cubren restauración, movimiento a otro control, intención de pulsar el fondo y cambio de sesión; el addon real original sigue pendiente de replay independiente.
