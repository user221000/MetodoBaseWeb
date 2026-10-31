# Interfaz de negocio y espacio personal

La revisión simplifica los paneles del servicio web sin cambiar sus contratos de datos. La capa común `workspace.css` unifica las pantallas de negocio, usuario, acceso, registro y páginas auxiliares con superficies claras, navegación verde, tipografía del sistema, formularios legibles y una acción principal por sección.

Los títulos y enlaces usan lenguaje directo. Las explicaciones secundarias se agrupan en `details` nativos; diario, declaración de alergias, cuotas y condiciones de autorización conservan su lugar antes de la acción correspondiente. Sobre mis datos y Lista de compras se pueden desplegar por teclado desde Mi plan. Guardar el perfil se llama Guardar perfil: esa acción no promete generar un plan.

`workspace-shell.js` es el único controlador del menú móvil en ambos paneles. Gestiona foco, Escape, elementos ocultos, `inert`, bloqueo de desplazamiento y el cambio a escritorio. Se incluye un enlace para saltar al contenido. El anillo del registro diario se apila a 480 px para no desbordar cuando el perfil está completo.

## Criterios de diseño

- Texto base de 16 px; etiquetas legibles, títulos cortos y ayudas a demanda.
- Controles principales de al menos 44 px; foco visible y movimiento reducido.
- Texto normal con contraste de al menos 4.5:1 en la paleta principal y en los estados de aviso/error.
- Pruebas de escritorio y móvil de 390 y 320 px, con datos sintéticos y estados de perfil incompleto y completo.

Referencias: [WCAG 2.2, contraste](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [tamaño de objetivos](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html). Son criterios aplicados a esta revisión; no se declara una certificación de accesibilidad completa.

## Verificación y límites

La evidencia de esta intervención se conserva en `E:/MetodoBaseWorkspace/evidence/ux-ui-and-leads-20261030-96e970a9963b456eb939a43786f35b83/`. Incluye contratos de IDs y controles, compilación de scripts, navegador real y acciones mediante la fábrica real sobre SQLite temporal. Los escenarios UI históricos se componen con el esquema actual mediante un plugin de prueba externo: ejecuta la migración real exclusivamente en bases SQLite temporales propias, sin modificar sus fixtures históricos ni reducir la verificación de esquema del producto.

La auditoría detectó una ventana de inconsistencia al crear, editar y desactivar clientes: el finalizador de la dependencia podía confirmar la transacción después de enviar la respuesta HTTP. Estas tres rutas ahora confirman antes del éxito y deshacen los cambios explícitamente si fallan. El rollback también evita que el finalizador confirme cambios después de que `NutritionRoute` haya convertido el error a una respuesta. Se mantienen los filtros de gimnasio, permisos, bloqueo de capacidad y baja lógica. La regresión observa otra conexión en `http.response.start` y un fallo de commit previo a durabilidad; no promete resolver un ACK perdido tras un commit ya duradero. Referencia del ciclo de dependencias: [FastAPI, dependencias con yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/).

Resultados conservados: 131 escenarios UI/HTTP sobre el esquema actual; seis regresiones de confirmación de clientes y once casos de cuota; contratos de 311 IDs de negocio y 405 hooks personales/compartidos; 60 vistas de navegador con escritorio, 390 y 320 px, más replay final de 42 controles tras corregir el desborde. Se ejecutaron acciones personales de perfil, agua, medición y temporizador, y 13 flujos de negocio, incluidos búsqueda, actualización, generación, descarga PDF, historial y baja con lectura inmediata. Los conteos de replays se conservan separados: no se suman como casos distintos.

Los pagos, correos y cuentas de terceros no se usan para probar escrituras. Los flujos dependientes de proveedor conservan sus bloqueos y requieren verificación específica de sus credenciales/configuración. No se habilitan envíos de recordatorios ni se presentan fechas administrativas como cobros confirmados. No hay cambios de esquema o migraciones de producción en esta entrega.

La propuesta local anterior de One Slice está archivada con sus bytes y recibos en `font-draft-preserved/` dentro de la evidencia. El usuario aún no dispone de licencia comercial; esta entrega usa fuentes del sistema y no publica la fuente ni su importación.

La prospección adicional se entrega por separado del código y de los 40 contactos anteriores. Sólo se incluyen contactos comerciales publicados; los nombres profesionales y sus cargos se distinguen de una propiedad empresarial no acreditada. Los enlaces y notas documentan el alcance de Maps y LinkedIn. No se envían mensajes ni se hacen llamadas.
