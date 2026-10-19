# Validación

Entorno inicial: Windows 10 build 19045, PowerShell 5.1; Python objetivo local 3.12.13 instalado por uv (predeterminado del host 3.14.6); uv 0.11.26; Git 2.55; Node 24.21. Herramientas Linux/imagen aún sin comprobar. PostgreSQL 17.11 instalado fuera de PATH; QA prepara cluster exclusivo, sin usar el servicio existente. Docker CLI disponible; daemon no disponible al inspeccionar.

QA conserva baseline en snapshot del commit base, con SQLite temporal y bloqueo de conexiones externas. Consulte `evidence/baseline-source.json` y archivos baseline generados por QA. No se reutiliza como aprobación de cambios posteriores.

Regresiones de cobro: ocho casos escritos y fallidos antes de corregir, según `evidence/backend-before.log`. Resultado posterior pendiente de integración y revisión.

Registro: `python -X utf8 scripts/implementation_registry.py --check` verifica 92 IDs, campos, fuentes y sincronización Markdown/JSON. El registro no demuestra que los comportamientos estén implementados.

Pendientes: suite completa actual; ramas de dominios críticos; PostgreSQL restringido/RLS; migraciones desde vacío/snapshots; restore medido; sandbox de pagos y entrega de correo reales de prueba; imagen Linux/SBOM/SCA; navegador/axe/teclado/viewports; lector de pantalla; concurrencia multiproceso; validaciones clínica/legal y piloto. No se declaran aprobados ni sustituidos por mocks.
