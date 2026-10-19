Preparación Linux local mediante QEMU TCG completada el 19 de octubre de 2026. El guest arrancó, aceptó SSH con clave exclusiva y host key fijada, ejecutó Python 3.12.15, un contenedor sintético y una comprobación Redis. **Esto prepara el laboratorio para un candidato exacto; no acredita build, tests ni rendimiento del producto.**

| Elemento | Resultado observado |
| --- | --- |
| Laboratorio | `F:\MetodoBaseWeb-linux-lab-20261019`, separado del producto |
| QEMU | Portable extraído, versión real `11.1.0 (v11.1.0-12130-ge470268ff4)`; 3389 archivos estables |
| Aceleración / recursos | `-accel tcg,thread=multi`, 2 vCPU, 2048 MiB; QMP y guest confirman los límites |
| Guest | Debian GNU/Linux 12, Linux `6.1.0-53-cloud-amd64`, x86_64; cloud-init `done` |
| Disco | Golden QCOW2 de 3 GiB virtuales, sin cambios y en sólo lectura; overlay nuevo de 12 GiB |
| SSH | Usuario `lab`, clave Ed25519 exclusiva, autenticación por clave; host key fijada desde la consola serial propia |
| Fingerprint del guest | `SHA256:ZoToWYiwd59rwP1QdToj2ORaV47SVmVvkV1WnJ5gjVA` |
| Proceso activo al cierre | PID `29456`; SSH `127.0.0.1:53105`, QMP `127.0.0.1:53106` |
| Python del laboratorio Linux | `3.12.15`, `/opt/metodobase-lab/python/bin/python3.12`; pip 26.2.1 |
| Docker del guest | `20.10.24+dfsg1`, API 1.41, desde paquetes Debian |
| Redis del guest | 7.0.15; PING y SET/GET/DEL de una clave exclusiva con TTL aprobados |

La [página oficial de QEMU](https://www.qemu.org/download/) remite a Stefan Weil para los binarios Windows. Se descargó `qemu-w64-setup-20260811.exe`, 206615928 bytes, y se exigió su SHA-512 publicado: `5bcf9eed634e8575a37b74f445af41a2fe4106da512d0c30c368301d4c105037fdfab40a5287367a28a957624cddebbc8c07e16c88ab6634f554cdf3d16bf543`. El [proveedor](https://qemu.weilnetz.de/w64/) describe estos binarios como experimentales y advierte que su certificado está caducado. Authenticode devolvió `UnknownError`, con certificado caducado el 9 de diciembre de 2023: **no se afirma firma válida**.

Se utilizó el 7-Zip 26.02 ya existente, SHA-256 `83967f1b02b43c4efeda302795722c809e0e81b8307de73558d10484d5676a7d`, sólo para listado y extracción NSIS dentro del laboratorio. Se verificaron 3389 rutas únicas y sin colisiones casefold, enlaces ni rutas inseguras, además de los tamaños declarados. La entrada de desinstalador generada por NSIS no declara tamaño; se registra esa excepción del formato. El instalador y el desinstalador QEMU no se ejecutaron. El árbol completo de herramientas permaneció idéntico después de arrancar y provisionar el guest.

La imagen inmutable seleccionada es `debian-12-genericcloud-amd64-20261006-2623.qcow2`, 349896704 bytes, del [directorio Debian fechado](https://cloud.debian.org/images/cloud/bookworm/20261006-2623/). Su SHA-512 coincide con el publicado: `a09170d17e13af43da61774666f520e3bbec0f8bd96b4db37c15f3426fb327ccad950b80dbe78c09aa5ca90ce5015e99334b0ba5188fd4018736bc3fb5f0882c`. El índice ofrece SHA512SUMS plano y no enumera una firma separada; no se logró una verificación OpenPGP. El límite queda explícito: checksum de la fuente primaria por HTTPS, sin identidad GPG acreditada. La comprobación QCOW2 pasó sin reparación, no hay backing file externo y QMP confirma que el golden se abrió en sólo lectura.

El [seed NoCloud](https://docs.cloud-init.io/en/latest/reference/datasources/nocloud.html) usa ISO9660 etiquetado CIDATA con user-data, meta-data y network-config. Se creó con pycdlib 1.22.0, wheel extraído sólo en el laboratorio y verificado contra SHA-256 de PyPI; el contenido del ISO se comprobó por lectura de vuelta. La clave privada SSH quedó únicamente en el laboratorio, con ACL restringida al usuario actual. No se copió al repositorio ni se imprimió. La host key se obtuvo de la consola serial y SSH utiliza `StrictHostKeyChecking=yes`, `IdentitiesOnly=yes` y un known_hosts propio; el nonce del guest coincide con el seed.

El intérprete Linux procede de [python-build-standalone 20261013](https://github.com/astral-sh/python-build-standalone/releases/tag/20261013), publicación inmutable: archivo de 34340172 bytes, SHA-256 `178d3d83b6e8e99285a65d3fce9c16b87952cc5efdb4d1a0e3ff3be18ff0fc9c`, igual al digest del asset. Se transfirió únicamente ese archivo mediante stdin SSH y se volvió a verificar su hash dentro del guest. **Linux 3.12.15 es un intérprete separado de Windows 3.12.13**; no se actualizaron los entornos Windows ni locks del producto.

APT preparó Docker, Redis y herramientas dentro del guest. La prueba real de Docker importó un rootfs sintético desde busybox-static de Debian y ejecutó `uname -s` con red deshabilitada, raíz de sólo lectura, todas las capabilities retiradas y no-new-privileges. Terminó con salida 0 y `Linux`; se retiró únicamente la imagen propia. No se descargó una imagen de contenedor externa. La prueba Redis usó 127.0.0.1 del guest y una clave derivada del nonce, con TTL y borrado exacto posterior. No hubo acceso a datos, proveedores o servicios de producción.

Windows no recibió cambios de BIOS, WSL, Hyper-V, características de virtualización, PATH global ni registro, ni se reinició. QEMU se lanzó oculto con CREATE_NO_WINDOW y sólo comparte dos archivos de disco propios y el seed en sólo lectura; no hay carpeta del host compartida. Los únicos listeners Windows de su PID son los dos loopback indicados. El guest tiene salida NAT para descargas de preparación; **no se afirma aislamiento de egreso del sistema operativo**. Los listeners internos del guest no son listeners públicos del host. Las referencias a KVM dentro del kernel guest no cambian el uso explícito de TCG en el proceso Windows.

Se conservaron dos pasadas fallidas anteriores al arranque: Windows OpenSSH devolvía 255 al faltar PROGRAMDATA en el entorno reducido. El diagnóstico de sólo lectura aisló esa variable y ahora apunta a un perfil propio. La clave se generó con cryptography ya disponible en el intérprete de herramientas. Las erratas y scripts iniciales son evidencia de entorno, no fallos de producto.

El control operativo está en `F:\MetodoBaseWeb-linux-lab-20261019\scripts\lab_control.py`. Valida PID, ejecutable y hash, command line con overlay/seed propios y TCG. `status` se ejecutó; `shutdown` solicita apagado ACPI del guest mediante QMP y `start` prepara su relanzamiento con el overlay propio. **Apagado y relanzamiento posteriores están preparados, todavía sin ensayar.** No contienen un comando para apagar o reiniciar Windows. `guest_access.py` permite un comando o un archivo stdin explícito por SSH hacia este único guest local; se verificó con `uname -s`.

Ejemplos con el intérprete Windows de herramientas ya existente:

```powershell
& 'C:\Users\Consu\AppData\Local\Temp\metodobase-desktop-package-20261019\Scripts\python.exe' -B 'F:\MetodoBaseWeb-linux-lab-20261019\scripts\lab_control.py' status
& 'C:\Users\Consu\AppData\Local\Temp\metodobase-desktop-package-20261019\Scripts\python.exe' -B 'F:\MetodoBaseWeb-linux-lab-20261019\scripts\guest_access.py' --command 'uname -a'
```

No se exportaron fuentes de producto, no se resolvió aún FROM/digest de una imagen de producto, no se construyó candidato alguno y Compose v2 no está provisionado. El siguiente trabajo necesita un commit congelado explícito, exportación de archivos tracked sin .env y validación Linux de sus locks existentes. TCG no se usará para afirmar p95, capacidad o equivalencia de rendimiento con hardware nativo.

Evidencia principal: [salud SSH inicial](linux-tcg-guest-ssh-ready.json), [salud final y pruebas sintéticas](linux-tcg-guest-health-final.json), [estabilidad final y golden readonly](linux-tcg-environment-final.json), [listeners Windows finales](linux-tcg-host-final-listeners.json), [procedencia de fuentes e índices](linux-tcg-primary-index-provenance.json), [errata preboot](linux-tcg-preboot-environment-errata.json) y [manifiesto SHA-256](linux-tcg-evidence-manifest.json). Los logs serial/QMP son fotografías con fecha; el overlay activo no se presenta como un artefacto inmutable. No hubo commits en este subproyecto.
