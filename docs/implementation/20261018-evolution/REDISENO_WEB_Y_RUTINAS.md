# Rediseño web y rutinas — ampliación autorizada el 2026-10-21

El usuario solicita continuar los pendientes anteriores con los mismos agentes,
rediseñar toda la plataforma con una estética deportiva inspirada en Smart Fit,
conservar los colores actuales de la landing y añadir un panel de rutinas Push,
Pull y Legs generalizadas. Esta decisión autoriza ahora las rutinas, que antes
eran una opción futura. El alcance sigue siendo únicamente el servicio web.

La identidad visual conserva fondo #0c1117, texto #edf2f7, acento #f7cd67,
apoyo #7de5d3, tarjetas #14212c y texto secundario #bcc8d5. La inspiración
afecta jerarquía, tipografía, composición, navegación y componentes. No se
copian marca, imágenes ni promesas comerciales de terceros. Landing, acceso,
registro, panel de gimnasio/equipo, portal personal, clientes, planes, generación,
cuenta, facturación, seguimiento, recordatorios y errores deben ser coherentes.

Las rutas nuevas son /rutinas para gimnasio/equipo y /mis-rutinas para el portal
personal, con variantes de slash final. Son shells sin información de cuenta.
GET /api/rutinas/catalogo?context=gym|personal requiere identidad persistida
vigente y contexto canónico. El catálogo es de sólo lectura, disponible en todos
los planes y no consume cuotas nutricionales. No crea una tabla ni una migración.
No adopta clientes ni acepta un gym_id del navegador como autoridad.

El catálogo v1 presenta tres sesiones genéricas, ejercicios con series,
repeticiones, descanso, técnica, equipo y alternativas. Incluye selección de
sesión, ejemplo de distribución en tres días no consecutivos, temporizador
reiniciable en RAM e impresión. No registra cumplimiento ni presenta resultados
personales inventados. No constituye prescripción clínica ni promete que una
división PPL de tres días satisfaga por sí sola toda la frecuencia recomendada.

Backend es dueño del catálogo, routers, wrappers y recursos específicos de
rutinas. Frontend es dueño del sistema visual, bases y páginas existentes.
Coordinación monta ambos routers en web.main_web y api.app y conecta la
navegación y sesión. QA y seguridad independientes revisan después; las pruebas
de navegador cubren 320/390/768/1440, interacción, foco, errores y sesión.

Fuentes consultadas: [Smart Fit México](https://www.smartfit.com.mx/),
[CDC](https://www.cdc.gov/physical-activity-basics/guidelines/adults.html),
[ACSM 2026](https://acsm.org/resistance-training-guidelines-update-2026/) y
[Gobierno de Victoria](https://www.betterhealth.vic.gov.au/health/healthyliving/resistance-training-health-benefits).
