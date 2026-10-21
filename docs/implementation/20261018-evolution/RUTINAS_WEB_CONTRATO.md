# Panel web de rutinas generales · contrato v1

Base de autor: `713bd3d39a37ed6bef0f344a67a6bfbfccbaa4b3`. Ampliación explícita web del 21-10-2026; sin desktop, migración, nuevas tablas, cuotas ni permisos comerciales.

## Superficie y autoridad

`GET /rutinas[/]` y `GET /mis-rutinas[/]` entregan shells inertes sin catálogo, identidad, perfil ni secretos. Extienden las bases profesionales y personales respectivamente. La navegación usa el arranque de sesión real de la aplicación; no se pretende autenticar una navegación HTML con un Bearer en RAM.

`GET /api/rutinas/catalogo?context=gym|personal` requiere `get_usuario_actual` y vuelve a consultar ocho campos persistidos de elegibilidad. Identidad activa/no borrada, invitación NULL, rol reconocido y SV entero 0..2147483647 vigente. El padre de equipo debe seguir siendo propietario canónico activo de tipo gym, sin equipo ni invitación. `gym`: propietario canónico o miembro ADMIN/NUTRIOLOGO/VIEWER válido; `personal`: usuario no OWNER de tipo usuario o miembro válido. Un OWNER/tipo usuario ambiguo no adopta espacio personal ni cartera. No se crean Cliente, Plan, membresía o capacidades nuevas.

La respuesta es `{version:1, scope:'gym'|'personal', program:{...}}`; el programa es idéntico para todos y se construye de datos canónicos server en `core/routine_catalog.py`. `program` contiene `id`, `title`, `audience`, `summary`, `schedule`, `warmup`, `starting_point`, `cautions`, `guideline_note`, `sessions`, `sources`. Cada sesión tiene `id/name/label/focus/description/exercises`; cada ejercicio, `id/name/sets:{minimum:1,maximum:2}/repetitions/rest_seconds/equipment/cues/alternative:{name,equipment,cue}`. Tres sesiones ordenadas: push/pull/legs; 4/4/5 ejercicios. El ejemplo JSON completo congelado está en la evidencia de autor.

Falta o invalidez de sesión: 401; contexto no autorizado: 403 `routine_context_forbidden`; parámetro ausente o inválido: 422 `routine_invalid_context`; fallo de lectura o limpieza propia: 503 `routine_unavailable`, opaco. Ninguna mutación está montada (405). La operación no hace commit ni DML; cierra su Session antes de publicar respuesta e intenta invalidarla si el cierre falla. No reetiqueta sesiones ajenas ni dispone del engine.

## Comportamiento de la interfaz

Tres días no consecutivos de una semana repetible, incluyendo domingo/lunes. El orden cronológico asigna Push → Pull → Legs. Inicialmente lunes/miércoles/viernes; una selección incompleta o consecutiva muestra el error sin fabricar calendario válido. Sólo RAM, sin persistencia ni marcado de completado.

Detalles nativos de ejercicio accesibles por teclado, técnica básica, equipo y una alternativa que sustituye al ejercicio. Temporizador local de 60/90/120 segundos con inicio, pausa y reinicio; preparar el descanso de un ejercicio no inicia el reloj. Su estado se descarta ante cambio de sesión o salida. No se registran series, tiempo de entrenamiento ni progreso. Imprimir muestra las tres sesiones y sus detalles; no constituye historial guardado.

El transporte espera `Api.session.ready`, captura/comprueba la revisión y obtiene el acceso de `Api.getToken()` en RAM; petición GET a ruta fija, sin cookies, redirects, refresh o replay automático. Respuesta invalidada por cambio de sesión se rechaza. No Storage ni interpolación HTML de datos; no hay identificador de cliente, selección de tenant o URL arbitraria en el transporte.

CSS de componente consume `--mb-*` con fallback a las variables existentes; paleta/base/nav son de Frontend. Negro/blanco sólo para impresión. Ajustes de menú y clasificación personal de `/mis-rutinas[/]` en auth-guard/api.js pertenecen a ROOT, fuera de este delta. Las dos factories montan el router API y `pages_router`; no se modifica pages.py ni bases.

## Contenido y límites

El contador tiene `role="timer"` y `aria-live="off"`; los mensajes de inicio,
pausa y fin conservan un `status` separado con anuncios corteses. Esto evita
convertir cada actualización visual del reloj en una notificación automática.
Se sigue la semántica de [WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/#timer)
y [ARIA in HTML](https://www.w3.org/TR/html-aria/#el-output). Las pruebas de rol
y región viva no equivalen a una prueba ejecutada con lector de pantalla.

Ejemplo orientativo de organización para adultos sanos principiantes: empezar con una serie, considerar dos sólo con técnica y recuperación adecuadas, 8–12 repeticiones, carga manejable, sin exigir fallo; calentamiento suave y práctica del movimiento. Parar ante dolor y pedir orientación ante lesiones, síntomas o condiciones de salud. No diagnóstico, tratamiento, personalización, prescripción nutricional ni promesa de resultados.

La división PPL tres días no se presenta como cumplimiento de la recomendación de trabajar cada gran grupo al menos dos días por semana ni como sustituto del ejercicio aeróbico. Las fuentes respaldan principios generales, no una validación individual de este catálogo. Consultadas el 21-10-2026:

- [ACSM, actualización de fuerza 2026](https://acsm.org/resistance-training-guidelines-update-2026/).
- [CDC, actividad física en adultos](https://www.cdc.gov/physical-activity-basics/guidelines/adults.html).
- [Gobierno de Victoria, iniciarse en fuerza](https://www.betterhealth.vic.gov.au/health/healthyliving/resistance-training-health-benefits).

## Verificación y revisión

Pruebas de autor dirigidas: HTTP real sobre SQLite37 y ambas factories, registro/contraseña/enrolamiento/TOTP/challenge/recovery existentes, roles persistidos, revocación y padre, ausencia de DML, proyección mínima y fallo de cierre. Node puro usa el catálogo Python real, calendario circular, pausa/reinicio, transporte, sesión cambiada y arranque con `const Api` léxico tanto en DOMContentLoaded como documento completo. Dobles sólo en pruebas puras de transporte/temporizador; no se simula identidad de aceptación HTTP.

Sin PostgreSQL, navegador, Redis, VM, proveedor ni envío. Responsive real 320/390/768/1440, impresión real, composición de diseño global, QA y Seguridad independientes quedan para la ventana que coordine ROOT. No se atribuye esa aceptación al autor ni se repiten suites históricas completas para este catálogo de lectura.
