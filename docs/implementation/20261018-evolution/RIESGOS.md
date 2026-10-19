# Riesgos activos

| ID | Impacto / probabilidad razonada | Mitigación | Responsable | Estado |
|---|---|---|---|---|
| EX-01 | Cobros/permisos actuales altos; defectos reproducidos localmente | Contener R01/R02 y exigir regresiones/revisión independiente | Backend / seguridad | en_curso |
| EX-02 | Pérdida de información al migrar; esquema de producción sin Alembic según histórico | Snapshot sintético, reconciliación explícita, backup/restore, no stamp ciego | Datos / operación | pendiente |
| EX-03 | Restaurar un alimento excluido; código actual lo permite | Catálogo inmutable por solicitud, resultado final verificado, errores cerrados | Coordinación / QA | en_curso |
| EX-04 | Validación clínica/legal no disponible; ninguna revisión profesional ejecutada | Limitar promesas, registrar dictamen externo sin sustituirlo con agentes | Usuario / profesionales | pendiente |
| EX-05 | Dependencias/imágenes no reproducibles; manifiestos históricos divergentes | Target Linux/Windows, lock, SBOM y escaneo efectivos | QA / operación | pendiente |
| EX-06 | Confundir resultado local con despliegue o sandbox; no hay evidencia nueva live | Estado por entorno y artefacto, aprobación final sólo cuando paquete concreto exista | Coordinación | activo |
| EX-07 | La divergencia Free web/desktop tenía tres dimensiones comerciales | Usuario confirmó 10 clientes, 1 plan por cliente/día y 10 totales por gimnasio/día; catálogo único y 46 pruebas independientes. Falta consumo B2B atómico e integración UI | Backend / QA | decisión_resuelta; integración_abierta |
| EX-08 | Redis caído permitía continuar acciones sensibles; login ignoraba ventana900s y era local por proceso | Rechazo503, fallback de lecturas acotado, Lua atómico y dependencia compartida. Falta revisión independiente y ejecución Redis real | Coordinación / backend / QA | en_curso |
