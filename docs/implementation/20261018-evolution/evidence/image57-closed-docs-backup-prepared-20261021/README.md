Respaldo RAW preparado para revisión; no se ejecutó sparse checkout ni se eliminó, movió o reconfiguró ningún archivo fuente.

Los scopes aprobados son únicamente:

- `F:/mb-mfa-ci31-20261019/docs`: 9.211 archivos, 426.085.590 bytes.
- `F:/mb-expat-call-visibility-20261019/docs`: 4.037 archivos, 160.995.277 bytes.
- `F:/mb-container-runtime-tools-20261019/docs`: 4.017 archivos, 160.781.562 bytes.

Los 17.265 archivos suman 747.862.429 bytes (0,696 GiB). El ZIP privado conserva sus bytes físicos, incluidos los CRLF que difieren de los blobs Git. Cada miembro pasó lectura completa de CRC, SHA256 y modo; una segunda lectura de las fuentes y los snapshots Git/índice/sparse quedaron iguales. Los scopes Docs no tienen archivos ignorados o sin seguimiento. Las cachés ignoradas fuera de Docs se registraron mediante estado Git y permanecen intactas; no se leyeron sus contenidos. No se accedió a los archivos sin seguimiento de Main.

El ZIP se encuentra bajo el nuevo root privado `C:/Users/Consu/AppData/Local/Temp/metodobase-closed-docs-backup-private-20261021`, creado con el productor Root144 y readback WinAPI de dos ACE antes de cualquier payload. `summary.json` identifica el ZIP y sus hashes; `source.json` fija los manifiestos privados y los estados anteriores/posteriores. C: conservó 3.368.951.808 bytes libres al cierre, por encima del mínimo de 2 GiB.

Se conserva el primer rechazo del preflight: inicialmente exigía ausencia de ignorados en todo el WT y encontró cachés fuera de Docs. No había creado el ZIP ni alterado fuentes. La guarda final distingue el scope Docs limpio del estado de esas cachés externas, sin ampliar el respaldo ni aprobar su borrado. `preflight-history.json` fija los hashes de esa preimagen y del recibo.

Una eventual exclusión sparse de Docs requiere revisión de Root. Tendrá que preservar las reglas existentes `/*`, `!/venv/` y `!/.venv-test/`, todos los archivos ajenos a Docs y este respaldo; no hay autorización de VM en este recibo.
