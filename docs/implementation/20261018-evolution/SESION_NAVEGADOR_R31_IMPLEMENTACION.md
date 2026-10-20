# Sesión web del navegador R31 — fase offline del autor

El cliente conserva el access sólo en RAM y renueva mediante la cookie HttpOnly del servidor. Bootstrap, migración única, autenticación y cierre esperan el mismo Web Lock hasta consumir JSON. El epoch sin secretos invalida RAM y DOM de otras pestañas, que requieren abrir de nuevo la cuenta para adoptar otra identidad. No se añaden refresh/replay/readback a namespaces privados.

La fuente de producto coincide byte a byte con `bee520a8a0c9654239dd04fa54696bd098c51faf`. Esta fase añade la composición versionable de pruebas y el mapa por comando/caso. No modifica backend ni desktop.

Validación del autor: **51 comandos / 925 ejecuciones Node PASS**, **865 obligaciones del mapa verificadas**, **56 SSR PASS** en ambas factories. Los 45 JS parsean; Ruff y pip check dan0. 1127 fuentes,92 distribuciones y binarios permanecen idénticos durante el gate. Los4 comandos export de ROOT suman108 ejecuciones y49 nombres distintos; no representan108 criterios independientes.

El [mapa CI](SESION_NAVEGADOR_R31_CI_MAP.json) conserva los comandos, NodeIDs y motivos de cada cambio normativo. `python tests/e2e/run_browser31_ci.py --output <directorio-nuevo>` ejecuta los criterios offline actuales, verifica los nombres/cantidades/hashes y guarda diagnósticos RAW privados. ROOT mantiene la edición de `.github`. Los archivos históricos conservan sus bytes; no se les atribuye PASS bajo el transporte nuevo.

Contrato: [wire R31](SESION_NAVEGADOR_R31_WIRE.json). Evidencia: [fuente](evidence/browser-session31-author-offline-20261020/source.json), [clasificación](evidence/browser-session31-author-offline-20261020/classification.json), [preservación](evidence/browser-session31-author-offline-20261020/preservation.json), [manifiesto](evidence/browser-session31-author-offline-20261020/manifest.json).

Esta evidencia usa VM/DOM mínimo, dobles de cookie/Storage/Web Locks y SSR inerte real. Backend HTTP, Chrome, foco/layout/axe, PG y QA independiente requieren pruebas separadas. La migración de los arneses nativos directos y transitivos de CI sigue pendiente como fase distinta; no se declara CI global verde ni compatibilidad universal de unload.
