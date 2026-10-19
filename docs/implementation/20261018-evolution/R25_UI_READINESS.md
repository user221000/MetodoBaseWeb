# R25 UI: contrato de preparación

Base aislada `809eab28c40c112cb6e3c9d8caceebae28683abd`, rama `implementation/r25-progress-ui-20261019`. No se modifica candidata31 ni otro worktree. Contrato de diseño backend commit `a1f9579561c943381f544ae6eaabf1700e82c8b3`, cuerpo RAW `879d093b45f40f519113c02638f2cbcd649d593708f7978cec1d4fb543099611` preservado en `evidence/r25-ui/before`. API32, accesor SQL y migración todavía no son capacidades aceptadas de esta base.

El criterio R25 exige medidas/adherencia con fecha/fuente/permisos y sin gráficos ficticios o conclusiones médicas. UX-10 obliga a separar menú, selección, consumo registrado y marcas de completado. UX-02 no autoriza derivación clínica ni reglas de alergia. UX-17 exige llamar a cada acción por lo que confirmó realmente. No se cambia el criterio original ni se declara cumplimiento por una pantalla.

## Hallazgos antes de editar

`ClientProgress` existe y la exportación lee filas propias con doble dueño. No hay rutas/UI de medidas o consentimiento montadas en la candidata31. `before/pages-missing.log/xml` conserva dos rojos de páginas y controles ausentes: GET `/mi-progreso` y `/clientes/synthetic-progress-client/progreso` responden404. No es un ModuleNotFound ni una negación de la historia legacy. La fixture del canario usa la factory web real con SQLite de pruebas preparada por metadata; no es una migración32 o prueba PG.

El consumidor de exportación actual conoce siete datasets y un presupuesto933888. No se afirma que consuma el octavo hasta tener DTO/scope/budget32 exactos y probarlo. El ledger MFA, diario, plan publicado y sus controles permanecen fuera del delta.

## Ownership y capas autorizadas

- Páginas nuevas personal/profesional, módulos de datos/control/UI/CSS separados y pruebas propias. `pages.py` sólo SSR focal de las dos páginas, con headers privados.
- Enlaces mínimos desde perfil/lista de clientes/vínculos, sin retocar los consumidores de diario/R24/MFA. La falta de capacidad se muestra por respuesta del servidor; un tipo/rol local no concede acceso.
- `Api.js` sólo helpers de progreso al final y cursores de exportación. No se cambia request/refresh, contextos opacos ni los métodos/grants MFA. Las lecturas reutilizan contexto canónico; mutaciones usan la política existente one-shot de request con revisión/access exacto, sin refresh/replay y sin pedir MFA.
- `usuario-privacidad.js` sólo octavo dataset `progress_consents`, cursor `after_progress_consent` y scope/presupuesto/record exactos acordados con backend. No se amplía a cartera/contactos ni se reexportan colecciones agotadas.

## Recorrido personal

Bootstrap32 suministra fecha civil America/Mexico_City y perfiles propios paginados. Se elige perfil explícitamente; no se crea/adopta uno al leer ni se infiere por email, rol o filas. OWNER ambiguo muestra revisión y no adopta cartera; un OWNER legítimo conserva R12 sin recibir capacidad personal nueva.

Medidas: fecha declarada, fuente, kg/porcentaje y autoría declarada separados de fecha de registro. Datos legacy son sólo lectura y su fecha histórica nunca pasa a ser fecha de medición verificada. La UI no deriva masa magra, diagnósticos o metas. Tabla accesible con cifras reales; tendencia sólo con suficientes fechas válidas de datos declarados, sin unir/inventar días faltantes, zeros u observaciones. Una tabla sigue disponible aunque no haya gráfico.

La creación retiene UUID e intención en RAM antes del primer PUT. Un resultado ambiguo requiere GET del mismo key y lectura fresca; no genera otra clave ni reenvía la mutación automáticamente. Conflictos muestran el estado actual y conservan el borrador sólo en RAM para comparación/nueva confirmación explícita. Retirar es un estado del registro, no una promesa de eliminación o retención.

Los completados muestran contadores observados y su base: X de Y snapshots registrados marcados completados. Denominador0 produce proporción no disponible; días ausentes no son0% ni cuatro comidas supuestas. No se presenta como adherencia clínica, consumo por abrir menú o conclusión automática. Si el agregado seguro no está aceptado/disponible, se muestra estado explícito sin gráfico de sustitución.

## Consentimiento y retirada

Ninguna categoría marcada por defecto. Vínculo exacto y su versión, perfil personal explícito si se comparten medidas, categorías weight/body_fat/lean_mass/completion, fecha inicial y fecha final o ongoing marcado de forma expresa. Texto/protocolo `progress_share_v1`. Se confirma la selección completa antes de guardar, con CAS de último id+version y versión de vínculo. No se envía actor/gym elegidos por el cliente.

Las fechas del consentimiento pueden ser futuras. Un intervalo fijo requiere fin igual o posterior al inicio; ongoing exige fin null explícito. No se aplica aquí el límite de 62 días ni el tope today de las consultas. Autorizar fechas futuras no crea observaciones ni permite registrar medidas futuras. La fecha de una medida y los intervalos de consulta sí terminan como máximo en today suministrado por servidor.

Adenda coordinada con backend: GET `/api/usuario/progreso/consentimientos` pagina últimos eventos propios por link_id aun cuando la fuente/vínculo estén inactivos u ocultos. Devuelve link_id, consentimiento mínimo propio y capabilities.withdraw; no nombre/contacto privado de fuente. Esto permite descubrir retiro después de reload/logout, sin IDs en Storage y sin usar export como autoridad. La retirada usa sólo CAS propio y permanece accesible sin MFA/paywall. No se interpreta un evento histórico como permiso actual.

Si cambian alcance, perfil, fuente o versiones, la UI reconsulta y exige nueva intención explícita; no sobrescribe ni interpreta una nueva vinculación como continuidad del permiso anterior.

## Lectura profesional

Readonly en ficha exacta del gimnasio, identidad/rol persistidos y derecho canónico `progresion_clientes` vigente (actualmente Clínica), todos verificados por servidor. Sin tiers/precios locales o CTA de pago aparente. Se distinguen historia nativa y proyección del vínculo autorizado. No hay acceso recíproco del socio ni acciones profesionales de modificación del progreso.

Sólo categorías/fechas/perfil consentidos y una proyección mínima; nada de alimentos, agua, notas, contactos o plan. Permiso ausente, fuente oculta, revisión de datos corruptos, falta de derecho, conflicto e indisponibilidad no se presentan como cero registros válidos. No se conserva una copia profesional del agregado.

## Estados, sesión y verificación pendiente

Carga/vacío/error/conflicto/incertidumbre separados. Busy antes de await; fences antes/después de await, parse/render y cambios de controles; invalidación síncrona vacía borradores, DTO, tablas, gráficos y selecciones. Sin salud/cursor/key de operación en Storage/cache/analytics/logs. Logout/nueva sesión no recupera datos por heurística.

Antes de consumer estricto se espera adenda JSON de backend: perfiles/cursor, records y snapshots, consentimiento/capabilities, intervalos permitidos y export8 con presupuesto. Dobles VM se declararán como contrato cliente, nunca como API32/PG aceptada. SSR/casos puros pueden avanzar. HTTP real espera freeze/backend compuesto; Chrome/PG requieren ventana root. No proveedores, envíos, cargos, producción o CI.

## Preparación verificable, todavía sin API32

Se añadieron las dos páginas SSR con encabezados privados y enlaces focales desde perfil, clientes y vínculos. Los módulos nuevos trabajan sobre una interfaz interna normalizada; no adivinan el DTO de la API. La ausencia de `Api.progreso` muestra indisponibilidad, nunca una tabla vacía que aparente una consulta exitosa. Ninguna página inicia una mutación al abrirse.

`progreso-datos.js` valida fechas civiles, límites técnicos ya documentados, selección explícita de perfil, categorías y contadores observados. `progreso-vista.js` usa nodos de texto, tablas con caption y regiones desplazables por teclado. Su diagrama son puntos de observaciones reales, sin unirlos ni rellenar fechas; no representa conclusión clínica. `progreso-controlador.js` reutiliza `MemberLinkContext`, protege los controles que invalidan de forma síncrona y limpia datos ante los eventos ya existentes. `progreso-operacion.js` conserva una intención de medición en RAM: un resultado incierto exige reconsulta por la misma clave; sólo una acción explícita posterior a confirmación prepara otra. El mapeo de errores definitivos del servidor, correcciones CAS y parser de records quedan pendientes del DTO32, no se deducen de un HTTP400 genérico.

Gates de esta fase: 18 casos puros, 12 lifecycle con el módulo de contexto real y API doblada, 10 de intención con callbacks doblados, 12 semánticos DOM y dos SSR reales. Son 52 VM y dos HTTP de páginas; no son API32, PG, navegador ni axe. El primer intento de lifecycle imprimió 12 verdes pero terminó con rechazo de Promise no observada en el propio harness: invalidaba antes de que entrara el callback retenido. `lifecycle-first.json` se conserva sin reatribuirlo como fallo de producto. El harness corregido espera una señal explícita de entrada y observa el rechazo antes de liberarlo; `lifecycle-after-harness-gate.json` termina con exit0. No cambió el módulo de producto para esa corrección del harness.
