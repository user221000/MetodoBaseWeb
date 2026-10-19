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

## OPS09 — Procedencia del empaquetado desktop

Dos negativos independientes demostraron que flags Git podían ocultar cambios de fuente aceptados por el empaquetador. La receta ahora compara bytes con blobs y conserva tratamiento exacto para controles binarios y CR aislado.94 controles QA y39 del artefacto9f aceptan este alcance local:1688 fuentes exactas, integridad ZIP e inicialización Qt. No acredita instalación, firma ni todos los flujos de negocio. [Evidencia independiente](evidence/desktop-artifact-independent-review.md).

## SEC03 — HTML persistido en drawer de clientes

El nombre de un cliente se interpretaba como HTML en el drawer. La reproducción mostró modificación del DOM; CSP bloqueó el handler y no se afirma ejecución activa. La construcción con nodos/textContent/dataset se integró en0fa124e después de12 controles browser QA y22 fuentes estables. El resto de renderers sigue bajo R23. [Alcance y pruebas](DRAWER_TEXTO.md).

## OPS10 — Referencia de diseño dentro del artefacto

La revisión del ZIP9f encontró `assets/design-reference.png`, sin uso de producto, con nombres/correos cuya procedencia no está acreditada. No se afirma que sean identidades reales. La exclusión exacta bca89bb conserva el original y supera97 pruebas QA y tres CLI propios. Reemplazo7bde30b verificado51bundle/ZIP/Qt y27payloadInno; criterio local cerrado. Instalación/firma/distribución y otros criterios siguen separados. [Revisión](evidence/desktop-ops10-independent/desktop-ops10-independent-source.json).

## SEC04 — Exportación atraviesa el cambio de sesión

En UI606, una continuación del consumidor podía preparar una parte de A después de que el helper real resolviera y la sesión cambiara a B. Un evento de fallo de Storage también conservaba el archivo preparado y sus acciones. La reproducción VM es sintética; no afirma incidente con usuarios reales. La interfaz se integró después de cercar DTO/Blob/descarga por revisión e identidad canónica,invalidar caché de forma síncrona y corregir dos guardspreclic adicionales. Seguridad25VM/QA25grupos revisan la corrección; criterio local cerrado,otros alcances de sesión abiertos. Los negativos originales y la adaptación aditiva de ACKlogout permanecen intactos. [Revisión independiente](evidence/ux/diary-ui-security-independent-review.md).

## SEC05 — Metadata privada en metricas

La revision local confirma almacenamiento de ruta concreta y direccion/encabezado de cliente en memoria y errores recientes. La heuristica de agrupacion tampoco identifica correctamente las rutas declaradas. Corrección integrada7bde30b tras15propios+63replay independientes;12rojos/3controles contra blob previo,18fuentes quiet. Quince casos preservados en suite con AST idéntico; criterio local cerrado, R17/R31 completos abiertos. No afirma incidente con datos reales. [Contrato y alcance](METRICAS_PRIVACIDAD.md).

## SEC06 — JSON falso del escáner aceptado como vacío

Seguridad reprodujo enab4490b cuatro reportes JSON malformados que se convertían en lista vacía con exit0. El control de objeto no vacío fallaba cerrado. El binario real8.30.1 escribe[] seguido deLF al no hallar coincidencias. Fix41708e5 elimina únicamente la normalización `or []`; el driver independiente intacto pasó de1/5 a5/5 y ocho controles adicionales pasaron. Suite mantenida61/61; revisión7fuentes quietas. Integrado31ebb2f, criterio local verificado; no declara limpias otras fuentes. [Aceptación](evidence/secrets-wrapper-independent-review.json).

## QA-11 — Referencias históricas mutables del verificador CI28

QA reprodujo dos bypass de `--verify-only`: modificar a la vez el fixture y su snapshot, o un archivo histórico y su hash enbaseline.json. El autor encontró además sustitución del docstring por una expresión ejecutable descartada por la comparación. Los snapshots auténticos5db sí coinciden con Git; no se afirma modificación de CI remoto. Fix3978 fija referencia y snapshot, y admite sólo docstring literal. Cinco focales de autor y7CLIindependientes pasan: se rechazan los dos bypass originales y print/número/f-string, con controles intacto/documental verdes;764fuentes/89paquetes quietos. Integrado5ba98c6/7cf4e6c; criterio local verificado. [Dos negativos originales](evidence/recovery-ci28-independent-20261019/baseline-trust-red.json),[aceptación](evidence/recovery-ci28-fix-independent-20261019/final/summary.json).

## SEC07 — Cabeceras privadas ausentes en errores de historial

Root reprodujo5rojos/3controles en71 y8verdes en49. Seguridad confirmó después dos500 sin cabeceras al fallar el SELECT, sin cursor ni planes en la respuesta. Fix57cdc0d añade boundary focal: respuesta500 genérica con no-store/no-referrer, conservando handlers/CSP y rutas ajenas. Seguridad acepta24/24:2negativos originales intactos,8root y14propios;20fuentes estables. Integradofdfc9cb; composición con recuperación28 aprobó36/36 y616fuentes estables. Criterio local verificado, R34 completo sigue abierto. [Revisión](evidence/history-security-after-20261019/source.json),[composición](evidence/history-recovery28-main-composition-20261019/summary.json).

## SEC08 — Componentes heredados vulnerables en runtime y artefactos

La primera imagen real5eb6d300, de fuente92615d7, compila y contiene55distribuciones/CPython3.12.13. El SCA OSV de ese inventario devuelve12entradas que representan6avisos únicos, todos de pip25.0.1 heredado; no se demuestra explotación. pip-audit no cubre CPython ni paquetes Debian. [Inventario](evidence/linux-recovery28-image-92615d7/runtime-inventory.json),[SCA anterior](evidence/linux-recovery28-image-92615d7/sca-before/summary.json).

La [publicación oficial de Python3.12.15](https://www.python.org/downloads/release/python-31215/) incluye correcciones de seguridad posteriores a3.12.13. [OSV PYSEC-2026-3721](https://osv.dev/vulnerability/PYSEC-2026-3721) requiere pip26.2; el candidato fija26.2.1 desde PyPI por hash. El worktree aislado23e57e0/abd559a actualiza base común por digest linux/amd64 y bootstrap pip antes de deps/runtime. Su build y auditoría OS siguen en curso; no se declara limpio ni integrado.

Aceptación añadida: inventariar cada artefacto soportado, preservar anteriores, corregir con fuentes y pines verificables, reconstruir sin metadata duplicada, pip check y SCA real; revisar CPython/OS por separado y pasar regresiones independientes. Windows3.12.13 y los instaladores históricos permanecen sin actualizar: una imagen Linux nueva no los valida. Responsable operación/seguridad, tareasR09/R18/R21/R31; estado en_curso local, sin excepción general, release ni despliegue.

## SEC09 — OpenSSL vendorizado de psycopg2 fuera de la cobertura Debian y PyPI

La imagen `99c846bd28b0` carga OpenSSL 3.5.8 del wheel psycopg2-binary, separado de `_ssl` Debian con backports y de cryptography 4.0.3. Trece [registros primarios CNA](evidence/linux-runtime28-native-20261019/native-openssl-sec09/evidence-manifest.json) incluyen 3.5.8 en su rango afectado. El [inventario ELF](evidence/linux-runtime28-native-20261019/native/native.json) identifica rutas, hashes y enlaces efectivos. No se ha demostrado explotación; condiciones de API, protocolo, arquitectura y compilación requieren evaluación por aviso. Los 71 IDs OS y el resultado OSV de 55 distribuciones PyPI mantienen su alcance separado.

Cierre: corregir el componente efectivo con procedencia fijada; reconstruir, inventariar y revisar SBOM/SCA, PostgreSQL y arranque con rol restringido, con aceptación independiente. No hay excepción de riesgo ni imagen corregida aceptada. Responsable: operación y seguridad. Estado: en curso; ver registro SEC09.
