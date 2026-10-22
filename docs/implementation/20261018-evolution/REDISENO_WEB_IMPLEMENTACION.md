# Rediseño visual web — 21 de octubre de 2026

Base: `713bd3d39a37ed6bef0f344a67a6bfbfccbaa4b3`. Autoría aislada en `F:/mb-web-redesign-20261021`; MAIN y la referencia original no se editaron.

La landing existente determina la paleta: fondo `#0c1117`, amarillo `#f7cd67`, texto `#edf2f7`, secundario `#bcc8d5` y apoyo `#7de5d3`. Se conserva su catálogo renderizado, precios, límites, procedencia del ejemplo y destinos. La inspiración solicitada se limita a jerarquía, estructura y claridad de [Smart Fit México](https://www.smartfit.com.mx/) y su [presentación de la aplicación](https://www.smartfit.com.mx/smartfitapp), consultadas el 21 de octubre de 2026. No se incorporaron sus marcas, imágenes, textos, promociones ni precios.

## Cambio

`design-system.css` comparte tokens con los selectores profesionales y personales existentes. Unifica navegación, formularios, tarjetas, tablas, estados vacíos, suscripciones, equipo, generación, perfil, diario, progreso, recordatorios y seguridad. Las bases cargan el acabado después del CSS específico; los componentes conservan sus selectores y funcionamiento. Las páginas independientes reciben el mismo sistema sin adoptar autoridad de otra área.

El menú móvil ocupa espacio en el flujo y mantiene sus manejadores originales, teclado y estado ARIA. El panel conserva datos consultados y estados de espera; el hero no promete una duración de generación. Los accesos comparten una presentación factual del proceso, sin los clientes, importes y macros ficticios de sus antiguas muestras. Las tipografías son locales; se retiraron las peticiones de Google Fonts. GIS, sus nonces y los scripts de aplicación permanecen intactos.

Los enlaces nuevos `/rutinas` y `/mis-rutinas` corresponden al contrato coordinado con el panel PPL de backend. Su implementación y la clasificación de rutas de `api.js`/`auth-guard.js` se componen por separado. Esta rama no modifica esos módulos, endpoints, permisos, modelos, cuotas ni escritorio.

## Evidencia y límites

La evidencia reside en `evidence/web-redesign-20261021/`. `before-source.json` y `baseline-contract.json` proceden de Git713 y su checkout inicial. Los 47 controles finales conservan todos los IDs previos, formularios, data attributes y cuerpos de scripts de 43 plantillas; también comparan literalmente expresiones de catálogo y destinos de landing. El primer control detectó la pérdida de `preview-month`; se restauró antes del navegador y se conserva su XML rojo.

El navegador usó Jinja y CSS reales, estados estáticos no confirmados y sólo los manejadores originales de menú. Interceptó todas las solicitudes, sin servidor, API, autenticación, SQL, proveedores ni fuentes externas. La primera matriz dio 70/88: detectó ARIA de grupo, foco de región de tabla, imágenes decorativas y contraste en perfil/error. `browser-first/` conserva ese resultado y sus capturas. `browser-after-a11y/` dio 88/88. La inspección manual detectó además el fondo raíz claro de una página corta de progreso; se hizo explícito el lienzo oscuro.

`final-matrix.json` reúne **88 casos únicos**: 84 de `browser-canvas-check/` más los cuatro de `browser-landing-final/`, tras hacer explícito también el fondo raíz de landing. No se suman repeticiones como casos independientes. Los 88 pasan a 320/390/768/1440 px, sin overflow de documento, errores de JavaScript ni hallazgos axe WCAG A/AA en esos estados. Enter/Escape, apertura/cierre y foco visible del menú se comprueban en las tres anchuras móviles. La línea base Git conserva ocho casos y cuatro capturas en `browser-baseline/`.

No es aceptación de los estados dinámicos, identidades, datos o flujos autenticados. QA debe revisar la composición con API, roles, panel PPL, tablas pobladas, diálogos y errores reales. No se declara uso de lector de pantalla ni conformidad global. Los navegadores propios terminaron cooperativamente; no se tocaron sesiones o servicios ajenos. No hay nuevas dependencias.

## Reproducción

Con Python web92 y Node/dependencias de `tests/e2e` ya instaladas:

```powershell
python -X utf8 -m pytest tests/test_visual_redesign_contract.py -q --noconftest
python -X utf8 tests/e2e/visual_redesign_render.py --output C:/Temp/visual-render-NUEVO
$env:METODOBASE_E2E_DEPENDENCIES='F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules'
$env:METODOBASE_VISUAL_RENDER='C:/Temp/visual-render-NUEVO'
$env:METODOBASE_VISUAL_OUTPUT='C:/Temp/visual-proof-NUEVO'
$env:CHROME_PATH='C:/Program Files/Google/Chrome/Application/chrome.exe'
node tests/e2e/visual_redesign_browser.cjs
```

El directorio de salida debe ser nuevo. Leer el JSON de resultados y exigir `complete` y todos los `cases[].passed`; el transporte del harness conserva también los resultados rojos. `--baseline` renderiza Git713; `METODOBASE_VISUAL_CASES=landing` limita un replay focal sin alterar aserciones. Los archivos existentes conservan CRLF de checkout y GitLF mediante stage finito con `core.autocrlf=true --renormalize`; los nuevos declaran LF y la evidencia conserva sus bytes.

## Checkpoint151 — 2026-10-21

Aceptación autenticada independiente focal50325:3loginsUIpassword+MFA,4contextos×4anchuras16capturas,37criterios y2PDF;0pageErrors/axe/overflow. Rootvioowner390/personal1440 yQA cuatrovistasrepresentativas. Evidencia security-routines-native37-execution-20261021. Los35flujos anteriores completos siguen enrefreeze,no se atribuyen a estas16capturas.
