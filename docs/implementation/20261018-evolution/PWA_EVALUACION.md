# R35: evaluación inicial de acceso móvil

Revisión del 19 de octubre de2026 sobre MAIN3663a360, esquema30. Es una evaluación inicial en curso. Se conserva el criterio original: «Sólo tras retención y rendimiento básicos; instalar acceso y manejar conectividad con privacidad; no cachear planes sensibles sin política; construir si mejora uso medido». No equivale a implementación, a no aplicable o a una excepción de alcance.

La retención de uso del producto y la conservación de datos personales son comprobaciones distintas. Falta una baseline de uso/pilotos reales para medir beneficio de acceso rápido (R22/R30). R31 mantiene pendiente la política de conservación y copias. Esa falta no impide por sí sola estudiar una variante de acceso online sin nueva caché sanitaria; sí impide asumir permiso para persistir planes sensibles offline.

## Evidencia disponible

Un inventario de232 archivos web mantenidos y versionados no encuentra los patrones literales de registro de service worker, evento de instalación, apertura de Cache y enlace de manifest indicados en su reporte; tampoco archivos candidatos de manifest. El alcance es código fuente, sin examinar registros instalados en el navegador del usuario, código remoto ni todas las formas posibles de acceso dinámico a esas API. [Inventario y límites](evidence/r35-readiness-20261019/source-inventory.json).

Los recorridos QA de R12/R14 y los del autor R24 prueban tareas y anchos concretos, no retención de usuarios ni instalación en un teléfono. Las lecturas locales medidas en R34 pertenecen a su fuente histórica y hardware; no fijan capacidad o latencia universal. Continúa la investigación del pool de una conexión y faltan objetivos/entorno acordados para extrapolar.

## Referencias primarias verificadas

Chrome diferencia promoción e instalación: la documentación actual de su equipo enumera HTTPS, interacción y campos de manifest para la promoción; también indica que puede existir instalación sin satisfacer esos criterios. La posibilidad de instalar no prueba experiencia offline. [Guía de instalación, actualizada19sep2024 y consultada19oct2026](https://web.dev/articles/install-criteria). El anuncio de cambios del05dic2023 retiró el requisito de un fetch handler para la instalación desde menú; no usar un badge PWA antiguo de Lighthouse como aceptación actual. [Chrome](https://developer.chrome.com/blog/update-install-criteria).

El [manifest W3C, Working Draft16oct2026](https://www.w3.org/TR/2026/WD-appmanifest-20261016/) define metadatos de arranque y presentación; es un borrador, no una certificación de aplicación o privacidad. La [especificación Service Workers, Candidate Recommendation Draft17sep2026](https://www.w3.org/TR/2026/CRD-service-workers-20260917/) separa Cache del caché HTTP: su contenido requiere gestión explícita y no expira automáticamente. Una futura caché necesita inventario, límites y eliminación; los encabezados HTTP actuales no sustituyen ese diseño.

## Decisión provisional y prueba para revisarla

Se prepara como primera hipótesis un acceso online con metadatos públicos y URL de arranque fija, sin identificadores personales ni credenciales. No requiere introducir caché de planes o cola offline. Es una hipótesis de producto; todavía no se construyó ni se afirma que mejore uso medido.

Antes de elegir implementación, medir con participantes reales autorizados la dificultad de regresar al plan y al diario, tiempo hasta una tarea completada y retornos por cohorte con definición/denominadores explícitos. Registrar tamaño, observaciones faltantes y fuente, sin capturar contenido nutricional o atribuir causalidad a una comparación no controlada. Acordar qué mejora justificaría la inversión antes de interpretarla. No contactar participantes por iniciativa del agente.

Si la evidencia justifica construir, verificar instalación/apertura y navegación en dispositivos/navegadores realmente disponibles, sin llamar teléfono real a una emulación. Comprobar online/offline/reconexión con mensajes veraces: desconexión no confirma una escritura; un timeout exige reconsulta e idempotencia, sin replay automático de cobros o consumo. Verificar login/MFA, cambio de cuenta, revocación, teclado/foco, actualización/desinstalación y ausencia de contenido sensible en Cache/IndexedDB/Storage tras esos cambios. Usar perfiles propios aislados, nunca limpiar los del usuario.

Si posteriormente se propone offline sanitario, requiere una decisión de alcance y política específica antes de implementarlo, con supresión de copias y pruebas de revocación en dispositivos desconectados. El silencio no aprueba ese cambio. El resultado actual mantiene R35 en curso: evaluación técnica inicial y dependencias identificadas, evidencia de uso/decisión/experimento todavía pendiente.
