# Riesgos activos

| ID | Impacto / probabilidad razonada | Mitigación | Responsable | Estado |
|---|---|---|---|---|
| EX-01 | Cobros/permisos actuales altos; defectos reproducidos localmente | Contener R01/R02 y exigir regresiones/revisión independiente | Backend / seguridad | en_curso |
| EX-02 | Pérdida de información al migrar; esquema de producción sin Alembic según histórico | Snapshot sintético, reconciliación explícita, backup/restore, no stamp ciego | Datos / operación | pendiente |
| EX-03 | Restaurar un alimento excluido; código actual lo permite | Catálogo inmutable por solicitud, resultado final verificado, errores cerrados | Coordinación / QA | en_curso |
| EX-04 | Validación clínica/legal no disponible; ninguna revisión profesional ejecutada | Limitar promesas, registrar dictamen externo sin sustituirlo con agentes | Usuario / profesionales | pendiente |
| EX-05 | Dependencias/imágenes no reproducibles; manifiestos históricos divergentes | Target Linux/Windows, lock, SBOM y escaneo efectivos | QA / operación | pendiente |
| EX-06 | Confundir resultado local con despliegue o sandbox; no hay evidencia nueva live | Estado por entorno y artefacto, aprobación final sólo cuando paquete concreto exista | Coordinación | activo |
| EX-07 | Tres pruebas Free 5/10 responden a decisión no documentada | Conservar expectativas, solicitar decisión comercial cuando contrato esté inventariado | Usuario / producto | pendiente |
