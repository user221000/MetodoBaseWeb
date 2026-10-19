La matriz conserva las 166 entradas: 67 CVEs, cinco IDs TEMP y un DSA, agrupados en 73 identificadores y 21 paquetes fuente. DSA-6549-1 y TEMP-1147318-639065 corresponden a una misma GHSA de XZ; no son dos defectos ni dos paquetes. No hay excepciones aceptadas.

El estado `fixed` del scanner significa que existe corrección para la versión vulnerable instalada. `resolved` en Debian describe la disponibilidad en la distribución; no confirma instalación en la imagen examinada. Los otros 71 identificadores siguen `open` en trixie; dos entradas Perl están `fix_deferred` en el scanner.

La presencia de bibliotecas no prueba que toda vulnerabilidad de su paquete fuente afecte al binario. Las ausencias medidas son propuestas para revisión, sin borrar hallazgos ni aplicar ignores. `matrix-73.json` conserva todos los enlaces de parches explícitos y versiones corregidas en sid/forky; esos enlaces son evidencia citada por el tracker, no una prueba de backport o compatibilidad binaria en trixie.

| Paquete fuente | IDs / entradas | Estado scanner (entradas) | Evidencia y trabajo de aplicabilidad |
|---|---:|---|---|
| acl | 2 / 2 | affected: 2 | libacl está presente. getfacl/setfacl/chacl no existen físicamente. El ID de funciones de biblioteca requiere analizar llamadores y rutas bajo privilegios; el ID de CLI tiene evidencia de componente ausente para revisión. |
| apt | 1 / 2 | affected: 2 | apt-key no existe físicamente. Debian describe una condición de keyring URI; revisar esa condición antes de aceptar no aplicabilidad. APT sigue presente. |
| attr | 1 / 1 | affected: 1 | Solo se inventaría libattr; getfattr/setfattr no existen físicamente. La vulnerabilidad descrita es de esas utilidades. Propuesta de no aplicabilidad pendiente de revisión, conservando el resultado bruto. |
| bash | 1 / 1 | affected: 1 | La escalada descrita requiere transición entre identidades y shell. Falta demostrar el flujo real y revisar la referencia upstream; no hay cierre por ejecutar como UID 999. |
| bzip2 | 1 / 1 | affected: 1 | La biblioteca está presente; bzip2recover no existe físicamente. El defecto descrito es de esa utilidad. No se aplica una excepción automática. |
| coreutils | 4 / 4 | affected: 4 | Riesgos de utilidades concretas sobre argumentos/archivos controlados y, en algunos casos, operaciones privilegiadas. Se requieren revisión de llamadas operativas y parches del mantenedor; una nota de baja relevancia no elimina el hallazgo. |
| dash | 2 / 2 | affected: 2 | Se requieren condiciones del matcher o argumentos de printf/echo y verificar las opciones de compilación. El shell existe en la imagen; no se probaron entradas malformadas. |
| diffutils | 1 / 1 | affected: 1 | La condición afecta diff3 y su programa diff. Se cita corrección upstream; falta demostrar si ese flujo recibe datos externos en operación. |
| gcc-14 | 2 / 6 | affected: 6 | Solo hay bibliotecas de runtime, no el compilador/headers. erase_if puede estar instanciado en consumidores nativos; actualizar libstdc++ no prueba que un binario ya compilado quede corregido. Revisar SBOM/compilación de extensiones y el parche GCC 14. |
| glibc | 21 / 42 | affected: 42 | libc6/libc-bin están presentes y CPython depende de libc. Hay condiciones distintas de regex, locale, conversión o APIs por ID. Varias tienen parches o versión Debian posterior; no se extrapola cierre desde un único caso ni desde aislamiento del laboratorio. |
| ncurses | 2 / 8 | affected: 8 | infocmp existe y el HIGH corresponde a esa utilidad. El otro ID involucra tparm/libtinfo. Faltan revisión de entradas y uso; el entorno web sin TTY no demuestra por sí solo ausencia de la ruta. |
| pam | 1 / 4 | affected: 4 | Se requiere pam_userdb y un servicio que autentique por esa ruta. Hay bibliotecas/PAM; no se verificó la configuración completa de despliegue ni se ejercitó autenticación. |
| perl | 4 / 4 | fix_deferred: 2, affected: 2 | perl-base incluye File::Temp y el motor regex. Archive::Tar y Pod::Text no se encuentran en @INC. Los IDs de esos módulos tienen evidencia de ausencia; los otros requieren revisión. fix_deferred continúa abierto aunque haya parche upstream. |
| shadow | 3 / 6 | affected: 6 | su/chfn/chsh SUID están presentes; newuidmap está ausente. Revisar configuración de login/btmp/subuid y operaciones administrativas. La ausencia de SSH en la imagen no resuelve automáticamente estos IDs. |
| sqlite3 | 4 / 4 | affected: 4 | SQLite real 3.46.1. sqlite3changeset_apply_v3 y sqlite3_zipfile_init no están exportados; apply_v2 y changegroup_add sí. Revisar cada ID: la ausencia del símbolo v3 no permite cerrar otros caminos de Session o bases corruptas. |
| systemd | 7 / 14 | affected: 14 | Solo libsystemd0/libudev1 están instaladas desde esta fuente; no hay homed, oomd, journald ni systemd-tmpfiles en las rutas medidas. Evidencia concreta de componente ausente para esos servicios, pendiente de revisión y sin eliminar entradas del scanner. |
| sysvinit | 1 / 1 | affected: 1 | No hay init en la ruta medida; sulogin sí está presente. Se necesita evaluar el escenario de instalación/recuperación descrito, distinto del CMD web; sin excepción automática. |
| tar | 5 / 5 | affected: 5 | tar y rmt están presentes. Deben revisarse extracción/restauración y argumentos con archivos no confiables; no se ejecutaron exploits. Los parches citados y las condiciones se conservan por ID. |
| util-linux | 6 / 54 | affected: 54 | mount es SUID 4755; nsenter y login existen. fstab está sin configurar. Los cuatro HIGH requieren hooks/montajes o nsenter privilegiado; el kernel del laboratorio es 6.1, pero el kernel de despliegue futuro no está validado. chfn/chsh son de shadow y Debian indica que no se compilan desde util-linux. |
| xz-utils | 2 / 2 | fixed: 2 | DSA y TEMP remiten a la misma GHSA, sin CVE asignado. La extensión Python _lzma enlaza liblzma.so.5. Hay backport estable u2 verificado por APT; el cambio está escrito, aún requiere inventario y nuevo scan de la imagen construida. |
| zlib | 2 / 2 | affected: 2 | La biblioteca está presente. Se requieren llamadas concretas a crc32_combine64 o gz* y sus precondiciones. No se asume seguridad porque la aplicación use una API de compresión distinta. |

El seguimiento por ID está completo en el CSV/JSON; esta tabla resume corrección y decisión sin reproducir descripciones ajenas.

| ID / primaria | Fuente | Entradas / estado | Corrección observada | Aplicabilidad / decisión |
|---|---|---|---|---|
| [CVE-2005-2541](https://security-tracker.debian.org/tracker/CVE-2005-2541) | tar | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2007-5686](https://security-tracker.debian.org/tracker/CVE-2007-5686) | shadow | 2 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2010-4756](https://security-tracker.debian.org/tracker/CVE-2010-4756) | glibc | 2 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2011-3374](https://security-tracker.debian.org/tracker/CVE-2011-3374) | apt | 2 / affected | No establecida en esta pasada | component_absence_for_review; abierto |
| [CVE-2011-4116](https://security-tracker.debian.org/tracker/CVE-2011-4116) | perl | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2013-4392](https://security-tracker.debian.org/tracker/CVE-2013-4392) | systemd | 2 / affected | No establecida en esta pasada | component_absence_for_review; abierto |
| [CVE-2017-18018](https://security-tracker.debian.org/tracker/CVE-2017-18018) | coreutils | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2018-20796](https://security-tracker.debian.org/tracker/CVE-2018-20796) | glibc | 2 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2019-1010022](https://security-tracker.debian.org/tracker/CVE-2019-1010022) | glibc | 2 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2019-1010023](https://security-tracker.debian.org/tracker/CVE-2019-1010023) | glibc | 2 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2019-1010024](https://security-tracker.debian.org/tracker/CVE-2019-1010024) | glibc | 2 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2019-1010025](https://security-tracker.debian.org/tracker/CVE-2019-1010025) | glibc | 2 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2019-9192](https://security-tracker.debian.org/tracker/CVE-2019-9192) | glibc | 2 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2021-45346](https://security-tracker.debian.org/tracker/CVE-2021-45346) | sqlite3 | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2022-0563](https://security-tracker.debian.org/tracker/CVE-2022-0563) | util-linux | 9 / affected | No establecida en esta pasada | source_component_mapping_for_review; abierto |
| [CVE-2023-31437](https://security-tracker.debian.org/tracker/CVE-2023-31437) | systemd | 2 / affected | No establecida en esta pasada | component_absence_for_review; abierto |
| [CVE-2023-31438](https://security-tracker.debian.org/tracker/CVE-2023-31438) | systemd | 2 / affected | No establecida en esta pasada | component_absence_for_review; abierto |
| [CVE-2023-31439](https://security-tracker.debian.org/tracker/CVE-2023-31439) | systemd | 2 / affected | No establecida en esta pasada | component_absence_for_review; abierto |
| [CVE-2024-56433](https://security-tracker.debian.org/tracker/CVE-2024-56433) | shadow | 2 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2025-5278](https://security-tracker.debian.org/tracker/CVE-2025-5278) | coreutils | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2025-6141](https://security-tracker.debian.org/tracker/CVE-2025-6141) | ncurses | 4 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | ncurses | 4 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2025-70873](https://security-tracker.debian.org/tracker/CVE-2025-70873) | sqlite3 | 1 / affected | No establecida en esta pasada | component_absence_for_review; abierto |
| [CVE-2026-102010](https://security-tracker.debian.org/tracker/CVE-2026-102010) | gcc-14 | 3 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-102473](https://security-tracker.debian.org/tracker/CVE-2026-102473) | dash | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2026-102474](https://security-tracker.debian.org/tracker/CVE-2026-102474) | dash | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2026-15059](https://security-tracker.debian.org/tracker/CVE-2026-15059) | systemd | 2 / affected | Parche upstream citado | component_absence_for_review; abierto |
| [CVE-2026-15534](https://security-tracker.debian.org/tracker/CVE-2026-15534) | perl | 1 / fix_deferred | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | systemd | 2 / affected | Parche upstream citado | component_absence_for_review; abierto |
| [CVE-2026-18374](https://security-tracker.debian.org/tracker/CVE-2026-18374) | glibc | 2 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-18477](https://security-tracker.debian.org/tracker/CVE-2026-18477) | tar | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2026-18508](https://security-tracker.debian.org/tracker/CVE-2026-18508) | tar | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2026-19499](https://security-tracker.debian.org/tracker/CVE-2026-19499) | glibc | 2 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-19542](https://security-tracker.debian.org/tracker/CVE-2026-19542) | glibc | 2 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-27171](https://security-tracker.debian.org/tracker/CVE-2026-27171) | zlib | 1 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-3184](https://security-tracker.debian.org/tracker/CVE-2026-3184) | util-linux | 9 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-40228](https://security-tracker.debian.org/tracker/CVE-2026-40228) | systemd | 2 / affected | No establecida en esta pasada | component_absence_for_review; abierto |
| [CVE-2026-42250](https://security-tracker.debian.org/tracker/CVE-2026-42250) | bzip2 | 1 / affected | Parche upstream citado | component_absence_for_review; abierto |
| [CVE-2026-50812](https://security-tracker.debian.org/tracker/CVE-2026-50812) | sqlite3 | 1 / affected | Debian sid/forky corregido | symbol_absence_for_review; abierto |
| [CVE-2026-50813](https://security-tracker.debian.org/tracker/CVE-2026-50813) | sqlite3 | 1 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-53910](https://security-tracker.debian.org/tracker/CVE-2026-53910) | diffutils | 1 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-5435](https://security-tracker.debian.org/tracker/CVE-2026-5435) | glibc | 2 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | acl | 1 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-54370](https://security-tracker.debian.org/tracker/CVE-2026-54370) | acl | 1 / affected | Parche upstream citado | component_absence_for_review; abierto |
| [CVE-2026-54371](https://security-tracker.debian.org/tracker/CVE-2026-54371) | attr | 1 / affected | Parche upstream citado | component_absence_for_review; abierto |
| [CVE-2026-54411](https://security-tracker.debian.org/tracker/CVE-2026-54411) | pam | 4 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [CVE-2026-56391](https://security-tracker.debian.org/tracker/CVE-2026-56391) | coreutils | 1 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-56392](https://security-tracker.debian.org/tracker/CVE-2026-56392) | coreutils | 1 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-5704](https://security-tracker.debian.org/tracker/CVE-2026-5704) | tar | 1 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-6238](https://security-tracker.debian.org/tracker/CVE-2026-6238) | glibc | 2 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-6368](https://security-tracker.debian.org/tracker/CVE-2026-6368) | glibc | 2 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-6791](https://security-tracker.debian.org/tracker/CVE-2026-6791) | glibc | 2 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | util-linux | 9 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-77117](https://security-tracker.debian.org/tracker/CVE-2026-77117) | glibc | 2 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | util-linux | 9 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | util-linux | 9 / affected | Debian sid/forky corregido | deployment_preconditions_unproven; abierto |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | util-linux | 9 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-80489](https://security-tracker.debian.org/tracker/CVE-2026-80489) | glibc | 2 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-82560](https://security-tracker.debian.org/tracker/CVE-2026-82560) | perl | 1 / affected | Parche upstream citado | component_absence_for_review; abierto |
| [CVE-2026-85091](https://security-tracker.debian.org/tracker/CVE-2026-85091) | zlib | 1 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-8674](https://security-tracker.debian.org/tracker/CVE-2026-8674) | glibc | 2 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-86805](https://security-tracker.debian.org/tracker/CVE-2026-86805) | glibc | 2 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-89092](https://security-tracker.debian.org/tracker/CVE-2026-89092) | glibc | 2 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | perl | 1 / fix_deferred | Debian sid/forky corregido | component_absence_for_review; abierto |
| [CVE-2026-95619](https://security-tracker.debian.org/tracker/CVE-2026-95619) | gcc-14 | 3 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [CVE-2026-95818](https://security-tracker.debian.org/tracker/CVE-2026-95818) | glibc | 2 / affected | Parche upstream citado | reachability_unproven; abierto |
| [CVE-2026-97399](https://security-tracker.debian.org/tracker/CVE-2026-97399) | glibc | 2 / affected | Debian sid/forky corregido | reachability_unproven; abierto |
| [DSA-6549-1](https://security-tracker.debian.org/tracker/DSA-6549-1) | xz-utils | 1 / fixed | trixie 5.8.1-1+deb13u2 | stable_fix_available_unbuilt; abierto |
| [TEMP-0290435-0B57B5](https://security-tracker.debian.org/tracker/TEMP-0290435-0B57B5) | tar | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [TEMP-0517018-A83CE6](https://security-tracker.debian.org/tracker/TEMP-0517018-A83CE6) | sysvinit | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [TEMP-0628843-DBAD28](https://security-tracker.debian.org/tracker/TEMP-0628843-DBAD28) | shadow | 2 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [TEMP-0841856-B18BAF](https://security-tracker.debian.org/tracker/TEMP-0841856-B18BAF) | bash | 1 / affected | No establecida en esta pasada | reachability_unproven; abierto |
| [TEMP-1147318-639065](https://security-tracker.debian.org/tracker/TEMP-1147318-639065) | xz-utils | 1 / fixed | trixie 5.8.1-1+deb13u2 | stable_fix_available_unbuilt; abierto |
