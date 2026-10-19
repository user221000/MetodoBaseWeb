# SCA por componente y artefacto

Imagen histórica99c, sin construir un sustituto en este lote. Se conservan164 entradas/71 IDs OS,811 ELF y55 paquetes PyPI con0 avisos en aquel alcance. Estos números no cubren automáticamente librerías embebidas, vendors o build.

Seguridad confirma Expat2.8.5 embebido y la cadena PSF/tag/commit/blobs: XML_ParseBuffer carece del fix13c5f63 de CVE-2026-77214. Los wrappers con buffers acotados no son reparación ni prueba de ausencia global de alcanzabilidad. Se registraSEC10; no se ejecutó PoC ni se afirmó explotación de la app.

SQLite CVE-2026-50812 permanece abierto: faltar apply_v3 no basta, pues el fix afecta sessionApplyOneOp compartido y tiene testapply_v2. FuenteDebian3.46.1-7+deb13u2/patchset/ELF fueron verificados por Seguridad sin afirmar crash/caller. Zlib85091 presenta un desajuste concreto entre rango y versión/implementación observados; no se autoriza excepción ni se cierra27171. Las13 CNA OpenSSL se evalúan por copia: cryptography4.0.3 está en el límite fijo, psycopg3.5.8 en rango y Debian3.5.7u3 tiene su backport documentado.

Dockerd038 prepara libpq de fuente; af548 prepara retirar pip/ensurepip completos. La revisión detectó scripts parent sin validar: antes1/3, c02 después3/3 y seis controles independientes adicionales. Es aceptación estática; no54 paquetes reales, linkage, SCA nuevo o arranque. Se conservan el rechazo y los freezes inmutables. Los vendors del build y wheel ensurepip se inventarían por separado, aunque no lleguen al runtime final.

[Triage](evidence/linux-sca-native31-triage-20261019/REVISION.md), [revisión independiente](evidence/security-native31-sca-independent-20261019/source.json), [fix de rutas](evidence/backend-container-installer-scripts-fix-review-20261019/review.md). Falta corregir componentes aplicables, construir y revisar el artefacto exacto antes de promoverlo.
