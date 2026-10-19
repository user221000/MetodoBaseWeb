# Candidato de runtime sin instaladores

Commit congelado `af548f71a8a763ba523853e85903a9ab8cf2b0a7`, padre `d038f1c3860296f42ba41ce9ee64a8a4e6300ebc`, worktree `F:/mb-container-runtime-tools-20261019`, limpio. Sólo añade once líneas al Dockerfile; los doce locks permanecen idénticos. Dockerfile Git/LF SHA256 `c923b779d7e6c97c5ac180c68a7373a2b3fc2f2854453c0bff6f4ce07e6a2ea1`.

La etapa runtime no instala paquetes ni crea venvs. Se revisaron 205 archivos en total del contrato runtime: módulos de las seis carpetas, entrypoint, db_bootstrap y Dockerfile. Hay cero imports de pip, ensurepip o venv; los dos tokens pip encontrados sólo aparecen en un mensaje de diagnóstico de bcrypt. Este análisis corresponde a la fuente congelada d038: repetirlo sobre la composición final que integre nuevos cambios de producto.

Después de todos los COPY, antes de USER appuser, la instrucción nueva comprueba rutas stdlib/purelib, resolve de los roots, directorios sin symlinks y pip 26.2.1. Elimina únicamente las rutas fijas del pip instalado, su dist-info exacto, todo ensurepip y los tres scripts pip. Comprueba después la ausencia de specs pip/ensurepip, wheels bajo /usr/local, metadatos/scripts residuales incluidos symlinks, y exactamente 54 distribuciones sin pip/setuptools/wheel. Emite sus nombres/versiones en runtime-python-metadata.json. Ninguna eliminación se ejecutó en el host.

Las etapas de build conservan pip 26.2.1, setuptools 84 y /opt/psycopg-build-tools, pip check y la procedencia del wheel compilado. Su inventario/SCA debe cubrir vendors y el asset ensurepip. La exclusión de la etapa final no declara seguras esas herramientas.

Validación estática propia: 19 guardas; seis mutantes rechazados; nueve bloques RUN verificados con bash -n; seis snippets Python compilados sin ejecutarse. La revisión inicial falló por quitar las continuaciones del shell en el harness; se conserva sin aceptación, y v2 mantiene el shell exacto. No hubo Docker, QEMU ni ejecución de un RUN.

Gates de aceptación pendientes: revisión SEC independiente; build Linux de la composición exacta; invariante real de 54 distribuciones con las otras versiones idénticas; ausencia física de pip/ensurepip/wheels/scripts; imports/linkage, migración y pruebas funcionales pertinentes; SCA real runtime y build/vendors; escaneo OS completo sin ignores. La imagen 99c roja y las evidencias originales se conservan. No hay cierre de SEC09, Expat ni de los 71 IDs OS.
