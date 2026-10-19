# Decisiones de ejecución

1. Trabajar sobre clon aislado y preservar original sin Git. Commit base cotejado por contenido; no se inventa historial.
2. Mantener FastAPI/Jinja/SQLAlchemy y compatibilidad de consumidores existentes mediante parámetros opcionales. No migrar de framework.
3. Pro sólo procede de un estado del proveedor verificado y reconciliado. Un redirect o preferencia nunca concede derechos. No fijar periodos de gracia ni precios nuevos sin decisión comercial.
4. Las exclusiones explícitas se aplican a todos los planes comerciales. El catálogo de generación se copia y congela por solicitud, se pasa explícitamente a los selectores, y se valida el resultado antes de PDF/persistencia. Las notas libres no constituyen reglas clínicas.
5. Decisiones explícitas del usuario: Free permite 10 clientes, un plan por cliente al día y diez planes totales al día por gimnasio; desktop continúa soportado. Los tres límites se comparten entre web/desktop. Se aclararon por separado las dimensiones cliente y total gym antes de cambiar cuotas. Corregir tests inseguros exige evidencia del contrato; no se alteran expectativas para ocultar discrepancias.
6. Revocación: nueva versión de sesión persistida y lookup de estado/rol/team. Compatibilidad temporal para tokens previos documentada; ninguna rotación o cierre live en esta ejecución.
7. RLS se activa sólo después de reconciliar esquema y demostrar contexto en cada transacción con rol restringido en PostgreSQL aislado.

Pendientes de decisión externa: gracia/reembolsos/impuestos; retención/borrado de copias; proveedor/infraestructura con coste; política clínica y dictamen profesional; participantes de piloto. Los límites Free ya están resueltos. El silencio no autoriza cambios de derechos ni gastos.
