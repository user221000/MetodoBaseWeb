# Revisión independiente R30: hechos observados y baseline provisional

Candidato revisado: `e6852cfd59d9df0f715f81e9299e7c4e5cb00d88`, sobre
`5efd3962ec9529e901273533d17ff1b19f0f1f39`. Trabajo independiente en rama
`qa/product-analytics-r30-independent-20261021`; no se editó la WT del autor
ni MAIN. Sólo servicio web, fuentes sintéticas y proveedores cerrados.

El código y los tests quedan congelados en
`59b64e029e06e1cdff69f7f4702aa8d664b65f66`. El único archivo de producto
modificado frente al candidato es `web/product_analytics_domain.py`.
No hay cambios de rutas, autenticación, MFA, roles, permisos, esquema,
contrato JSON, UI, planes comerciales o desktop.

## QA-34: coherencia del helper provisional

Se reprodujeron tres contradicciones al entregar al helper `build_baseline`
un informe modificado con su hash recalculado: D7 maduro con ancla de esa
semana; D30 maduro con D7 inmaduro; y semana visible del ancla con cero
publicaciones. El resultado inicial fue **3 RED y 1 control PASS**.

Un borde posterior reprodujo un ancla en el lunes siguiente a un `through`
dominical ya cerrado. Ese lunes a medianoche es un límite exclusivo. El
canario fue **1 RED y 2 controles PASS**: el instante exacto de `as_of` sí es
válido si su día está incluido, y el microsegundo anterior al corte exclusivo
sí se conserva.

La corrección sólo exige consecuencias derivables de `anchor_week` y del
período: no publicaciones anteriores al ancla, al menos su propia publicación
en esa semana si está visible, D30 maduro implica D7 maduro, y madurez
compatible con los extremos posibles de la semana. Rechaza el ancla posterior
al último día incluido. Los extremos civiles se convierten a UTC antes de
sumar las ventanas de días transcurridos.

No se inventa el instante del ancla. Se conservan ambos estados posibles
dentro de una misma semana, el ancla anterior a `from`, el corte parcial de
`through`, los límites al microsegundo y una semana histórica de México de
169 horas por el cambio de horario.

Estos contraejemplos pertenecen al **helper puro** y a su validación de
coherencia; no son una entrada de la API, un bypass de autorización ni un
defecto reproducido en las lecturas reales del informe. El artefacto sigue
`unreviewed`, `business_baseline_established=false` y `targets=null`. Los
hashes no acreditan origen. No hay importador ni completitud semántica
prometida para un baseline poblacional o de negocio real.

## Revisión y controles ejecutados

Se leyeron los siete archivos de producto, los cinco archivos de pruebas del
autor, el contrato y sus manifiestos. La autorización vuelve a cargar el actor
y su padre persistidos. El contrato canónico permite miembros de equipo con
`tipo=gym`; no se añadió una restricción por intuición. El control independiente
comprueba ADMIN gym/personal con la misma identidad, fuentes separadas y sin
identificadores en el resultado.

El lector empieza con ContextVar vacío, abre una sola Session propia y enlaza
el sujeto verificado. Confirma rollback y close antes de devolver el informe,
restaura el contexto ambiental y no sustituye la factory global. Una factory
fallida o un esquema ausente, inesperado o con varios heads produce 503 opaco,
sin fabricar un informe vacío. Los controles verifican checkout cero y uso
posterior normal del recurso propio.

El presupuesto se comprueba tras filtrar el sujeto: 10 000 hechos propios
caben en 13 semanas aunque haya 10 001 ajenos; ese segundo sujeto recibe 413.
Un período excesivo se rechaza antes de crear la Session. El helper conserva
el límite de 64 KiB y valores NULL hasta completar la ventana observada.

HTTP utiliza registro, password y MFA reales de fixtures actuales37, sin
reemplazar dependencias de identidad. Ambas factories mantienen no-store,
no-referrer y CSP fija en ruta exacta y slash, incluidos errores opacos de
lector RuntimeError/HTTP500/HTTP503 y falta de autenticación. No salen cuerpos
ni cabeceras privadas de las excepciones. Vecinos y GIS conservan su política.

| Ejecución | Resultado |
| --- | --- |
| Dominio tras primera corrección | 56 PASS: 24 nuevos y 32 existentes |
| Replay independiente previo al borde exclusivo | 40 PASS |
| Replay independiente final, una sola ejecución | **43 PASS**: 27 puros, 8 SQLite y 8 HTTP |
| Ruff final, dominio y cuatro companions | 0 hallazgos |
| Inversa de patch de producto, sólo comprobación | PASS |

Los conteos manuales enviados antes como 41 y 25+31 se corrigieron a los
resultados efectivos del JUnit. Los 113 IDs del autor son composición de sus
fases; no se presentan como una ejecución independiente ni como un único run.

## Aislamiento y límites de la evidencia

WEB92 permaneció de sólo lectura: 92 RECORD, 8 177 entradas instaladas y
1 191 fuentes en las fotos finales antes/después, sin diferencias. El harness
elimina URLs heredadas de DB/Redis y bloquea conexiones de aplicación,
connect_ex y psycopg2. Sólo permite la llamada exacta de socketpair desde
`BaseProactorEventLoop._make_self_pipe`, con ambos sockets y peer loopback
propios, necesaria para el IPC interno de asyncio en Windows. No se abrió
servidor ni se accedió a endpoints de PostgreSQL/Redis.

Los errores iniciales de preparación quedaron conservados y separados:
config, utils y src ausentes en el sparse QA; y bloqueo del self-pipe antes de
entrar al ASGI. No se atribuyen a producto. Las copias exactas por ejecución de
los drivers comienzan en `http-ipc-corrected`; no se afirma ese congelado para
las versiones previas de `phase.py` editadas durante la preparación. El
canario privado del último borde no estaba entre las fuentes de la WT en su
primer RED; su RAW y su AST íntegro se conservaron y se compararon con los
tres tests incorporados.

La evidencia privada recibió DACL protegida antes del primer payload y tiene
archivo RAW de 166 miembros con lectura de retorno idéntica. La proyección
pública usa scanner119, controles JWT/HMAC/credenciales y hashes de archivos.
El `diff --check` focal de producto, tests y texto es limpio. El diff completo
señala los CRLF de la preimagen RAW del dominio, conservados con `-text` para
no alterar su identidad; no se presenta ese diff histórico como limpio.
Ver [manifest.json](evidence/qa-r30-independent-20261021/manifest.json),
[freeze.json](evidence/qa-r30-independent-20261021/freeze.json) y
[atribución](evidence/qa-r30-independent-20261021/failure-attribution.json).

No se ejecutó PostgreSQL, Chrome, VM, Redis, n2, instalaciones, desktop ni
proveedores reales. La lectura estática del SQLAlchemy/psycopg2 instalado
confirma que las opciones se aplican antes de `conn.begin` y que readonly
se configura en la conexión. **No equivale a comprobar PostgreSQL**:
REPEATABLE READ, read-only, set_config/RLS y reutilización del pool requieren
su lease y prueba real posterior. Replay ROOT y peer también son posteriores.
No se cierra R30 completo ni se establece un baseline real.
