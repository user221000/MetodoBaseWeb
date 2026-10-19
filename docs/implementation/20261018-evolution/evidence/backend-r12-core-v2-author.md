# R12: núcleo29 V2 después de revisión independiente

V1 ad712416 queda histórico e inmutable, con su freeze72b2bce y RAW ZIP
a1ea7f6e011fa571354f2dc865d8689b039e186a7542720a64c664ebf96ecc8a.
Los55 criterios de autor y95 de QA V1 no cerraban la revisión de autoridad:
seguridad encontró tres rojos PG reales. No se atribuye una fuga HTTP ni un
incidente live. No se modifica MAIN ni se ejecutan proveedores/correos.

Driver independiente original a51dde94ef7e2a7197c063ceb0b37c95d030c6cf05279bc8f3e0b2ad237fffdb
y sus asserts no se editaron. Evidencia de seguridad:
`security-r12-core29-independent-20261019/source.json`, SHA
f02414062e52b8d0bb12475270b4a96a749bc6924bfb0deb0a9abeb70ee6a767.

## Fallos y corrección

1. Un owner del recurso con team_gym_id noNULL dejaba visible una publicación
   al destinatario aunque canonical_gym devolviera false. La política de lectura
   de destinatario ahora reutiliza ese predicado canónico completo.
2. El padre profesional del destinatario podía convertirse en miembro de otro
   owner sin invalidar actor_valid. Su comprobación ahora incluye team NULL e
   invitation_token NULL, igual que el owner canónico y el lock de concesión.
3. Un OWNER aceptaba su propia invitación con proof válido, retiraba el GUC
   antes del commit y éste prosperaba. Gscope permitía releer la invitación y
   `IF NOT proof(NULL)` no rechazaba UNKNOWN. proof ahora devuelve false para
   ausencia de capacidad y todos los guards negativos de helpers usan
   `IS NOT TRUE`, incluido el guard diferido de consistencia.

Gscope no se confunde con elegibilidad de nueva concesión. El retiro propio,
revocación profesional/invalidación y withdraw siguen funcionando bajo su
alcance anterior aunque el owner de la fuente esté inactivo. No se añade un
grant al destinatario ni una restauración automática de links al reactivar.

Se auditó todo el vocabulario PL/pgSQL nuevo, no sólo las tres muestras:

| Grupo | Tratamiento de NULL y evidencia |
|---|---|
| actor/canonical/lock | EXISTS y FOUND son booleanos noNULL; padres/owner requieren contexto canónico completo. |
| scope/proof/pending/consumed/recipient | COALESCE(false) en la salida; ninguna capacidad ausente produce UNKNOWN. |
| guard_link/guard_invitation/guard_publication/check_pair | Los12 checks negativos de helpers usan IS NOT TRUE. FOUND noNULL, tuplas IS DISTINCT FROM y columnas NOT NULL/FK/CHECK conservan sus barreras; no se usa UNKNOWN como aprobación. |
| require_rc | IS DISTINCT FROM read committed también rechaza un valor ausente. |
| invalidación | Predicados IS FALSE/IS NOT NULL/IS DISTINCT FROM son totales; no nuevo requisito de owner activo y no nuevo lock inverso a Usuario. |
| unique_json/keys/number/food/project_plan | Los19 checks negativos de helpers usan IS NOT TRUE; argumentos SQL NULL de JSON/depth/arrays/flags se rechazan. JSON literal null sigue siendo JSON válido, pero no un menú válido. |

Los otros siete rojos de la regresión propia son contratos auxiliares de
booleanos totales, no siete accesos indebidos adicionales demostrados. La
suite propia corregida conservó10 fallos/6 controles antes del cambio. El
primer driver tenía un literal JSON que SQLAlchemy interpretó como bind; su
RAW se preservó antes de sustituir únicamente ese renderer por jsonb_build_object.

Preimágenes:

- Inicial completa ZIP03e084270d0f2e8a356b861f4c81a8a53c01f7b7b59be45d13e0fa70963f556b.
- Driver corregido + before10/6 ZIPd438760b0da133c328a7caedf22a8a153c5ad0c12c342bdb717bc8cc19889c78.
- Los logs/XML anteriores y los tres drivers independientes permanecen sin
  sobrescribir; las nuevas ejecuciones usan nombres nuevos.

## Gate de autor y alcance del delta

71 criterios PG verdes:55 anteriores +16 de regresión/NULL. Otros5 criterios de
migración PG verdes (cinco SQLite no seleccionados porque su SQL no cambió).
Huellas de24 fuentes/artefactos capturadas antes y después: sin cambios durante
ambas tandas. Ver `backend-r12-core-v2-gate-source.json` y logs/XML separados.
Los tiempos son técnicos locales con build desktop concurrente, sin claim SLO.

Sólo cambian dos módulos SQL nuevos y el target PostgreSQL29. No cambian tablas,
modelos,20 políticas históricas, targets22–28, target SQLite29, RLSfamilias23,
triggers ni vocabularios anteriores. No nueva revisión30 ni índice de rendimiento.
La nueva firma29 registra los cuerpos de helpers corregidos; la firma física
de tablas y la sección de seguridad histórica se comparan iguales a V1.

Esto es freeze de autor para repetir la revisión independiente del núcleo.
API/servicios/UI/restore29 permanecen separados y no quedan aceptados por71/5.
