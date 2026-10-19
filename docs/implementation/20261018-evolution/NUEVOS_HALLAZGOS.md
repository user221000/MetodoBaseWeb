# Hallazgos añadidos durante la implementación

## OPS08 — Transición obligatoria de configuración Railway

Detectado el 18 de octubre de 2026 al verificar el contrato real de pre-deploy de R03. La [documentación oficial de Railway](https://docs.railway.com/config-as-code) identifica Config as Code como obsoleto y mantiene `railway.toml`/`railway.json` para servicios que ya lo utilizan hasta el **1 de diciembre de 2026**, con corte definitivo. Los servicios nuevos deben utilizar [Infrastructure as Code](https://docs.railway.com/infrastructure-as-code). Esta condición no estaba en los siete informes originales.

Impacto: corregir preDeployCommand en el archivo existente es una transición local útil, pero por sí sola no prepara una operación posterior a esa fecha. No se debe crear staging nuevo suponiendo que heredará el mecanismo antiguo. No se eliminó la configuración actual ni se aplicó infraestructura por esta observación.

Aceptación añadida: inventariar la configuración efectiva sin exponer valores; preparar una definición IaC compatible para el servicio existente y el entorno aislado; fijar herramientas, comparar el diff previsto y validar sintaxis/contratos; verificar pre-deploy, digest, salud, secretos por referencia, volúmenes y rollback en staging autorizado antes del corte. No crear recursos con coste, aplicar IaC ni desplegar sin la autorización correspondiente.

Responsable: coordinación/operación. Tareas vinculadas: R03, R18, R20. Estado: pendiente; la preparación local puede continuar y la aplicación externa necesita un paquete revisable y autorización. Esta entrada no modifica la auditoría histórica ni declara probado el comportamiento futuro del proveedor.

## SEC01 — Activación desktop sin autoridad verificable

Detectado al inventariar excepciones de R04. `api/routes/licencias.py` publica activar/estado sin autenticación y deriva un plan pagado de STR/PRO/CLN, concediendo365 días y sobrescribiendo la activación de un hardware existente. No verifica emisión, compra ni identidad. La validación online de desktop también acepta una caída de red sin demostrar licencia local válida. No se ejecutaron esos flujos contra un servicio externo.

Prioridad P0 de contención local. Aceptación añadida: ninguna clave inventada por prefijo concede acceso; la activación/consulta requiere autoridad emitida y propietario autorizado, no coincidencia de email; hardware de otro gimnasio no se sobrescribe; periodo y límites provienen del contrato emitido, repetición no los inventa y revocación/caducidad se respeta. La falta de red no vuelve válida una licencia desconocida. Se mantienen las licencias locales existentes que pasan su verificación, con compatibilidad y reconciliación histórica documentadas. Pruebas antes/después, dos propietarios, concurrencia y revisión independiente.

Autor root; backend añadió vínculos nullable y backfill por clave emitida coincidente en la preparación R04. Los registros sin autoridad verificable se conservan. Contención local aceptada por QA: 40 pruebas, incluidas autoridad JWT persistida y dos errores Unicode reproducidos y corregidos. Estado: en revisión; concurrencia PostgreSQL, puente remoto autenticado y autoridad criptográfica legacy siguen abiertos en [LICENCIAS.md](LICENCIAS.md). Tareas vinculadas R01/R04/R09/R31; sin activación productiva ni nueva decisión de precios/dispositivos.

## SEC02 — Refresh tardío cruza una sesión nueva

Confirmado sobre0459b0f mediante dos pruebas independientes de máquina de estados en `tests/e2e/auth_refresh_race_review.cjs`, con transporte y tokens sintéticos en memoria. Si la cuenta cambia antes de un401, el helper refresca la identidad nueva y reenvía el DTO de la operación anterior. Si cambia mientras espera el refresh anterior, la respuesta tardía sobrescribe el par de tokens nuevo. [Reproducción y huella](evidence/ux/auth-refresh-race-before-source.json). No demuestra un incidente productivo, navegación real ni acceso de servidor fuera de sus permisos.

Prioridad P0. Aceptación: petición, refresh, reintento y respuesta ligados a sesión inicial; todo cambio de cuenta invalida operaciones anteriores sin limpiar ni reemplazar tokens nuevos. Refresh habitual, varios401 concurrentes, rotación propia y error deben resolver todos los consumidores. Login/registro públicos no refrescan por401. Comprobar también PDF/logo y logout. Pruebas antes/después, navegador y revisión independiente. Frontend implementa la corrección central; QA/seguridad la revisarán. Tareas R10/R19/R31. No renumera los92 IDs originales ni requiere datos o llamadas reales.

Seguimiento: seguridad encontró un rojo adicional en candidato275 por escritura parcial de Storage, capaz de mezclar accessB/refreshA y reenviar DTO deB bajoA. API347 añade bloqueo de confianza por instancia y pasó74 VM independientes; navegador actual sigue en revisión. El cuerpo275 se conservó en copia con SHA exacto mediante inversión de parches propios, sin inventar commit Git. [Contrato, evidencia y límites](SESIONES_HTTP.md). R10, recarga y atomicidad entre pestañas permanecen abiertos.
