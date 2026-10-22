Plan congelado para revisar antes de autorizar un arranque de VM. Este plan no
se ha ejecutado. El runner de lectura no arranca o apaga VM, sube archivos,
ejecuta SQL/Redis/Chrome, instala paquetes ni construye imágenes.

El contexto preparado corresponde a f0608fb086b08bbd59ce595e9a906c58308d3328:
469 blobs RAW, 21.770.001 bytes de contenido y tar de 22.138.880 bytes. Su SHA256
es 9e9655e4ead53e579bd9c23f13bdf43c395c174c8c2e30ad29e441f5740d0f01.
Hay doce inputs Docker actuales verificados y catálogo esperado57.

Recursos existentes: overlay de 12 GiB virtuales, aproximadamente 7,30 GiB
asignados según la última inspección offline; TCG con 2 vCPU y 2048 MiB.
Antes del arranque Root debe tomar dos muestras frescas de RAM y disco. El
presupuesto propuesto es al menos 4,5 GiB de RAM host disponible, 2 GiB libres
en cada volumen C/F y ninguna fase Chrome/PG/Redis/N2 simultánea. Son requisitos
de coordinación, no resultados actuales de guest.

Una vez concedido un lease exclusivo breve, el controlador ya existente y
verificado del laboratorio puede iniciar la VM. Después:

```text
python -B -X utf8 tests/ci_web37/image_guest_preflight.py --authorized-read-only-preflight --context-manifest C:/Users/Consu/AppData/Local/Temp/metodobase-test-ci37-image-context-private-20261020-v3/source-manifest.json --private <privado-nuevo-absoluto> --output <publico-nuevo-absoluto>
```

El runner valida identidad QEMU/overlay, helpers de acceso por SHA exacto,
nonce SSH del guest, x86_64, al menos 2500 MiB libres en Docker, MemAvailable
de 1 GiB, cero contenedores en ejecución y cache nativa exacta72:
`metodobase-lab:expat-sec10-m2-72c44a1`, ID
`sha256:a2b7e06ec1971f6519395aa1cd08c54f6d18c2bf26749abf3d65513f86337e7f`.
df, Docker system df y versión se conservan privados. Se detiene ahí. El
controlador `lab_control.py shutdown` solicita apagado normal sólo de esta VM;
después se verifica que su PID y listeners desaparecieron. No se termina una
VM ajena ni se invoca un apagado de Windows.

Tras revisar ese recibo se necesita un lease distinto para subir este único
tar y construir la imagen actual37/57 con cache, sin `--pull`, con etiqueta de
revisión f060 y directorio remoto nuevo. La cache72 sólo acredita preparación
nativa histórica; no acredita runtime57. El incremento presupuestado deberá
contrastarse con df/cache frescos antes de decidir un build. No se reconstruye
la imagen33 ni se limpia cache/evidencia histórica para hacer espacio.

Las cinco comprobaciones físicas33 seguirán usando su fuente auténtica e006
materializada (42,4 MB, sin imagen) con el owner externo37. El restore poblado37
conserva los 75 criterios históricos por separado. El launcher QA Windows que
importa pytest no constituye aceptación de Linux o de la imagen actual. Los
gates nativos Linux, runtime57, inventario, SBOM y SCA actuales siguen pendientes.
