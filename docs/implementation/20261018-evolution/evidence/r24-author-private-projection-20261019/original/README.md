# Evidencia de autor R24

No es aceptación independiente ni cierre completo R24. Contrato: `../../R24_PLAN_DIARIO_CONTRATO.md`.

| Ejecución | Resultado y alcance |
| --- | --- |
| `before/ui-contract`, `before/publication` | 2 SSR + 3 valores/HTTP rojos antes de implementar. Ambas factories. |
| `before/data-model` | 23 rojos por módulo puro aún inexistente, sin atribuir comportamiento previo. |
| `first-backend` | 80 verdes: tres iniciales R24 y regresiones dirigidas R14 de valores/persistencia. |
| `second-directed` | 82 verdes: anteriores + dos SSR de la nueva sección. |
| `expanded-sqlite` | 27 verdes y cuatro fallos del arnés nuevo, conservados. El caso OWNER gym requería403 existente, distinto de OWNER usuario409; el doble de pérdida de ACK debía observar `identity_map` tras el flush. No se cambió producto por esos errores. |
| `expanded-sqlite-corrected`, `final-sqlite` | 31/31 cada ejecución: fuente ajena/ID/versión/cuerpo inválidos, OWNER, CAS, pérdida de ACK real, revocación/snapshot retenido/remove y SSR. No sumar ejecuciones repetidas como casos únicos. |
| `pg.log/xml`, `pg/resource-and-source` | 2/2 HTTP ambas factories sobre UUID nuevo con migración30 real. Runtime no-super/no-bypass/no-owner, FORCE RLS y dos tenants; ninguna escritura profesional. UUID ausente al cerrar y doce fuentes quietas. |
| `data-model-after` | 23/23 cantidades/identidad/unidades/rangos puros. |
| `controls-first` | 11/14: tres expectativas erróneas del arnés usaban coma decimal; `es-MX` usa punto. Conservado; no cambio producto por ello. |
| `controls-after`, `controls-final` | 14/14 montado en DOM mínimo con transporte RAM. |
| `snapshot-vm` | 25/25: 18 criterios históricos sin cambiar + siete nuevas pruebas de procedencia. Junto23+14+25=62, sin duplicar esas18. |
| `controls-double-save-before` | 14/15: rojo real de dos registros secuenciales cuando termina tarde la segunda revalidación. Los cuerpos RAW antes de corregir están en `before-consumer-fixes`. |
| `controls-guarded-final` | 17/17: mismos quince + captura de selección antes del await y fecha vacía. Guard busy previo al await, finally y CAS/fecha observados. |

Los VM son modelos/consumidores montados en memoria, no HTTP ni navegador real. Los logs redirigidos por PowerShell conservan su codificación RAW, incluida BOM UTF16 donde corresponde. No se transcriben los cuerpos históricos para aparentar otra ejecución.

Excepción acotada de `git diff --check`: las cuatro líneas16/134 de los dos HTML SSR históricos en `before/ssr/{api-app,web-main_web}.html` contienen los espacios que emitió la plantilla original. Se conservan byte por byte; el producto actual pasa el chequeo. El manifiesto final registra también las dos correcciones de docstring solicitadas después del navegador, sin atribuirles ejecución de una suite nueva.

## Navegador real

`daily_plan_server.py` crea una única base UUID por ejecución, migra Alembic30, usa rol runtime restringido y registra VIEWER por HTTP. Las suscripciones sintéticas se preparan en esa base propia. Registro/auth/perfiles, cuotas, motor local, objetos/PDF, invitación/aceptación/publicación R12 y diario/export son reales. Sólo entrega de correo es no-send; el fragmento queda en canal privado Temp, nunca en evidencia entregable o endpoint privilegiado.

`browser-first`: tres grupos y cuatro capturas antes de una expectativa de `.check()` incompatible con el rollback visual previsto del CAS409. El arnés cambia a clic y conserva la aserción de conflicto.

`browser-second`: seis grupos antes de que la instrumentación axe asumiera un script con nonce inexistente en la página R12. Se corrigió sólo la inyección de inspección mediante Playwright.evaluate; no CSP ni producto.

`browser-final` (nombre histórico, ejecución **parcial**): ocho grupos y seis capturas sin axe/desborde/pageerrors, después falla la confirmación de eliminar consumo. `remove-mounted-before` fue un probe inválido del arnés (login no monta Api). `remove-mounted-product-before` ya usa formulario real: cero PATCH, estado guardando y snapshot presente. Causa de producto: descripción del borrador no contemplaba `remove_meal`; se corrige y se conserva el cuerpo anterior RAW.

**`browser-guarded-final`: 11/11 grupos, seis capturas**, cero axe AA/overflow/pageerrors en los bloques examinados. Personal320/390/768/1440 y publicación390/768. Incluye:

- Cuatro comidas de worker real, gramos reales, compra explícita sin DML, teclado Space/Enter y error503 de lectura expresamente doblado.
- Consumo personal persistido, dos cuentas, PDF exacto autorizado, dos contextos CAS, confirmación perdida tras commit real y reconsulta sin replay automático.
- Fuente R12 realmente aceptada/publicada: dos clics durante una respuesta GET real retenida producen una revalidación y una PATCH; contexto exacto, agua y otra comida preservados.
- Export propio con `source_context`, aislamiento del otro actor, retirada bloqueando nuevo consumo, snapshot retenido, eliminación propia explícita después de retirada.
- Respuesta tardía de fuente tras cambio de cuenta, invalidación síncrona, logout/revocación y login reales conservando snapshot propio y bytes legacy sin leer/importar/borrar.

No se alteran aserciones de los cinco rojos iniciales. Los fallos propios y cambios posteriores del arnés están diferenciados; no se presentan los ocho grupos antiguos como pruebas de la fuente nueva.

Cada directorio `browser-*-resource` conserva startup/cierre y ausencia de su UUID. El último corresponde al fixture PID21040:282 fuentes idénticas. `browser-support-before/after` verifica157 archivos Node y tres binarios. El soporte-before se capturó después del primer recorrido parcial y antes de las siguientes ejecuciones. El reporte se escribe tras cerrar todos los contextos y `browser.close()`: no se capturó inventario nativo de PID de Chrome y no se afirma que se cerraran navegadores ajenos. Puerto8800 sin listener al cerrar. No se tocó8776,8795, procesos del usuario, HBA, roles globales ni esquemas compartidos.

Las capturas incluyen atributos/textos HTML RAW de cada bloque. Los chequeos manuales de teclado y fuente CSS no equivalen a validación por lector de pantalla. No existe evidencia Linux/desktop/producción ni revisión clínica real. Sustituciones nuevas y retención R31 siguen pendientes.

## Reproducción acotada

Python candidato y Node/Chrome constan por hash en los manifiestos. Invocar desde esta rama aislada, sin importar configuración de producción:

```powershell
python -X utf8 tests/run_isolated.py tests/test_publication_diary_consumption.py tests/test_daily_plan_ui_contract.py -q
node tests/e2e/daily_plan_data.cjs
node tests/e2e/daily_plan_controls.cjs
node tests/e2e/daily_plan_snapshot.cjs
```

PG dirigido requiere las variables sintéticas privadas de55483 y `R24_PG_OUTPUT` en un directorio nuevo; `tests/run_isolated.py tests/integration_daily_plan_publication.py` crea y cierra únicamente su UUID. El launcher browser recibe `--private <TempNuevo> --config <envPrivadoSintético>`; su origen es8800 exacto. El driver recibe `R24_PRIVATE` y `R24_BROWSER_OUTPUT` nuevo. Después de su finally, crear el archivo privado `stop`, esperar la salida del proceso propio y comprobar `resource.json` (UUID ausente) y `close.json` (fuentes idénticas). No copiar `fixture.private.json` ni `mail.private.json` al entregable.
