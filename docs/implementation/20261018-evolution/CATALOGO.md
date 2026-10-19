# Catálogo vigente del candidato local

Fuente ejecutable: `core/plan_catalog.py`; los adaptadores web/desktop añaden únicamente IDs de precio del proveedor. Cada proyección es una copia independiente. Precios en MXN, unidades menores enteras y periodo mensual explícito. Ninguna configuración de precio ausente concede acceso.

El usuario aprobó el 18 de octubre de 2026 **Free: 10 clientes, 1 plan por cliente al día y 10 planes totales por gimnasio al día**, conservando soporte desktop. Ambos consumidores reciben esos límites. No se borran clientes existentes para ajustar el catálogo. La cuota mensual Free de 20 y Standard de 100 procede del contrato anterior de FeatureGate; no se cambió mediante la decisión sobre el límite diario. Los planes superiores conservan sus valores anteriores mientras no exista otra decisión comercial.

La suscripción individual es otro producto: Starter permite 1 plan mensual y Pro permite 5, a 79 MXN/mes, según el contrato personal existente. `get_individual_plan_catalog()` proyecta esta regla; `pro_usuario` no aparece en el selector de licencias de gimnasio de desktop.

`core/subscription_policy.py` resuelve el derecho B2B: sólo planes de gimnasio conocidos y estados active/trialing vigentes. Un periodo vencido o estado past_due no concede prestaciones pagadas. Los registros heredados sin fecha conservan el comportamiento previo hasta una reconciliación explícita; esto no crea un periodo de gracia nuevo. Las fechas históricas sin zona se interpretan UTC. El guard y FeatureGate consumen la misma función.

Revisión independiente: [46 pruebas](evidence/pytest-catalog-final-decision.xml) y [huellas estables](evidence/catalog-final-decision-source.json), incluidas pruebas con base real de FeatureGate, vencimientos, trial, valores desconocidos y copias del catálogo. Los mocks antiguos ahora declaran explícitamente fechas nulas en lugar de generar objetos MagicMock como timestamps; sus expectativas comerciales permanecen iguales.

R09 continúa abierto hasta verificar UI/API y consumo atómico B2B. El catálogo no sustituye una reserva transaccional de cuota. Las decisiones de impuestos, gracia y cambios de precios siguen sin inventarse. No se ha desplegado esta versión.
