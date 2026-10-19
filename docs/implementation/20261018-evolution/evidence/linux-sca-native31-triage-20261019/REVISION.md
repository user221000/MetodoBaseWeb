# Triage de la imagen 99c y sus componentes nativos

La imagen real sigue abierta por sus 164 entradas OS, 71 identificadores y SEC09. Esta pasada conserva el escaneo íntegro, contrasta las fuentes y prepara una corrección aislada para retirar instaladores del runtime. No se arrancó QEMU, reconstruyó la imagen ni inició el producto.

Imagen: `sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c`; fuente `bc365c13b9af9e24129a56b4068059a67bb3afa0`. Inventario previo real: 87 paquetes Debian, 55 distribuciones Python y 811 ELF de 64 bits. Los nuevos análisis no convierten esos datos históricos en una ejecución nueva.

## Prioridades concretas

1. **OpenSSL vendorizado de psycopg2-binary:** 3.5.8 coincide con las 13 CNA de SEC09. La corrección Debian del OpenSSL del sistema no modifica esta copia. El candidato fuente `d038f1c3860296f42ba41ce9ee64a8a4e6300ebc` sustituye el adaptador binario por psycopg2 compilado contra libpq y OpenSSL Debian fijados; su build, linkage, pruebas y SCA siguen pendientes.
2. **Expat embebido:** CVE-2026-77214 incluye la versión 2.8.5 observada. El código exacto de CPython 3.12.15 carece del guard de capacidad upstream. Las entradas estándar de Python inspeccionadas acotan las longitudes y reservan el buffer correctamente; eso limita esas rutas, sin demostrar ausencia global de alcanzabilidad ni reparar la función nativa. Un `apt upgrade libexpat` no reemplaza este código embebido. Preparar un contrato de base CPython con backport verificado o una base oficial que realmente lo contenga.
3. **Instaladores del runtime:** el wheel fijado de pip 26.2.1 contiene tres funciones de urllib3 2.7.0 sin los fixes de CVE-2026-97687/97688/97689. Tres mocks pequeños ejecutaron cuerpos exactos de esas funciones sin red, loops ni buffers grandes. El candidato `af548f71a8a763ba523853e85903a9ab8cf2b0a7`, hijo de d038, elimina pip, sus metadatos y scripts, y todo ensurepip con sus wheels, sólo en la etapa final. Conserva las herramientas de build para su auditoría. La imagen aún no fue construida: la postcondición esperada pasa de 55 a 54 distribuciones de aplicación.
4. **zlib:** CVE-2026-27171 coincide con la versión y función presentes en libz 1.3.1. El fix upstream es `ba829a458576d1ff0f26fc7230c6de816d1f6a77`, incorporado en 1.3.2; no aparece un backport trixie en la fuente primaria actual. No actualizar ciegamente a 1.3.2: esa versión entra en el rango de otro aviso, CVE-2026-85091.

No se propone mezclar sid/forky, elevar paquetes Essential ni actualizar locks de aplicación o desktop. Un paquete propio de zlib o una base CPython recompilada necesitan contrato, procedencia, revisión y pruebas adicionales antes de autorizar un build compuesto.

## Fuentes y límites de versiones

| Componente real | Evidencia y evaluación | Estado de esta pasada |
|---|---|---|
| `_ssl`, OpenSSL 3.5.7; Debian `3.5.7-1~deb13u3` | DSA-6531-1 y changelog instalado cubren las 13 CNA; importa la versión Debian con backports, no sólo el texto de la API | Backport de esas 13 ya documentado; no declaración general de seguridad |
| cryptography 50.0.2, OpenSSL 4.0.3 | Las 13 CNA tienen rama afectada `>=4.0.0,<4.0.3`. Se conservaron todas las ramas y probaron 52 casos de frontera | Fuera de esos 13 rangos en el límite corregido; otras dependencias Rust/nativas no agotadas |
| psycopg2-binary 2.9.13, OpenSSL 3.5.8 y libpq 17.11 | Coincidencia de las 13 CNA. Los 16 ELF del wheel Linux fijado coinciden por SHA con el inventario real | SEC09 abierto; no prueba de explotación o flujo TLS del producto |
| Otras bibliotecas del wheel psycopg2-binary | Se conservan libldap, liblber, krb5, GSSAPI, SASL, com_err, keyutils, crypt, selinux y PCRE. Una cadena identifica `krb5-1.15.1-final`; no establece sus backports | No inferir versiones de release desde SONAME, ni cobertura Debian para estos binarios vendorizados |
| Expat 2.8.5 | CVE-2026-77214: rango y fuente coinciden. CVE-2026-102633 requiere 32 bits; los 811 ELF observados son de 64 bits | Caso nuevo separado de los 71 OS y las 13 CNA; revisión de alcance pendiente |
| SQLite 3.46.1, Debian `3.46.1-7+deb13u2` | Cuatro IDs OS preservados. CVE-2026-50812 nombra `sqlite3changeset_apply_v3` de 3.53.1, ausente del header/source 3.46.1 y del ELF oficial que coincide por SHA | Desajuste específico pendiente de revisión independiente; no elimina los otros tres IDs |
| zlib 1.3.1 | CVE-2026-27171: función y código sin guard presentes. CVE-2026-85091 comienza en 1.3.1.2; `gz_vacate` no existe en el orig Debian y no hay parches Debian | Un caso pendiente de corrección y un desajuste primario de alcance; escaneo conservado |
| liblzma sistema 5.8.1, Debian `5.8.1-1+deb13u2` | El rescan real previo retiró los dos aliases XZ después del backport verificado | No se reabren ni se suman como dos paquetes distintos |
| Pillow, liblzma 5.8.4 | Límite corregido upstream de GHSA-5qpq-xqfv-j9pg, independiente del paquete Debian | Evaluación sólo de ese aviso; no se hereda el backport del sistema |
| Pillow 13.0.0, 26 ELF | API observada: FreeType 2.14.3, LCMS 2.19, WebP 1.6.0, AVIF 1.4.2, libjpeg-turbo 3.2.0, OpenJPEG 2.5.4, libtiff 4.7.2, zlib-ng 2.3.3. También hay ELF de png, brotli, zstd, harfbuzz, Xau/xcb y sharpyuv | Inventariados y conservados, sin afirmar exhaustividad de avisos nativos a partir de SCA PyPI |
| Qt/PySide6 | PySide6 no importable y cero ELF con nombre Qt en las raíces inspeccionadas | Alcance exacto del inventario; no afirmación genérica de ausencia fuera de esas raíces |

`elf811-native-association.json` conserva cada ruta, SHA, clase ELF, DT_NEEDED, RPATH, RUNPATH, SONAME y dueño observado, con su asociación de paquete fuente. Hay 665 ELF con dueño dpkg, 64 con dueño de distribución Python y 82 sin dueño en esos metadatos; el origen CPython de estos últimos se registra como inferencia de ruta/base, no como reconstrucción binaria demostrada. Una asociación al paquete fuente no prueba que todas sus bibliotecas contengan la función vulnerable.

Las primarias OpenSSL completas ya estaban congeladas en `linux-runtime28-native-20261019/native-openssl-sec09/`. Se reutilizaron sin modificarlas. [CNA de OpenSSL](https://openssl-library.org/news/vulnerabilities/), [DSA-6531-1](https://www.debian.org/security/2026/dsa-6531).

## Expat: evidencia reproducible y alcance

[CNA CVE-2026-77214](https://cveawg.mitre.org/api/cve/CVE-2026-77214), publicado `2026-10-07T14:35:42.794Z`, actualizado `2026-10-10T02:26:09.470Z`; RAW SHA256 `1f845cc77f36438cb3e107dee6d0a8f290e561a58789d7529effb14a77ae622e`. Fix del mantenedor: [13c5f63a7f1c52c2feee3b16a1134d4fb68e9ea0](https://github.com/libexpat/libexpat/commit/13c5f63a7f1c52c2feee3b16a1134d4fb68e9ea0). La revisión del registro MAIN no encontró SEC10 ni este ID; la asignación de registro queda a cargo de root.

Tar PSF `Python-3.12.15.tar.xz` SHA256 `c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a`, obtenido de [python.org](https://www.python.org/ftp/python/3.12.15/Python-3.12.15.tar.xz), coincide con el hash de la receta oficial de la base. Tag anotado `f9e83c56c657be0a74ede2b5c523de4f9191d117` → commit [e848e4b09ca4bc67c0041c9ce7526dae471d4c36](https://github.com/python/cpython/tree/e848e4b09ca4bc67c0041c9ce7526dae471d4c36). Los cuatro archivos `pyexpat.c`, `_elementtree.c`, `expat/xmlparse.c` y `expat/expat.h` se verificaron contra tar, contenido por commit de la API y SHA Git de cada blob. No se ejecutó verificación GPG local ni se reconstruyeron sus ELF.

`XML_ParseBuffer` carece de `len > m_bufferLim - m_bufferEnd` antes de avanzar `m_bufferEnd`. El mismo patrón aparece legítimamente en `XML_GetBuffer`; por ello el análisis final se limita a la función correcta y conserva el error inicial del harness que buscaba sobre todo el archivo. `xmlparse.c` SHA256 `9a4969bb0ac497803866705f3fa233cc4b487e7685800d9222bd0ab38d1b8a20`.

`pyexpat.Parse` llama XML_Parse por chunks de 1 MiB con límite INT_MAX. `ParseFile` obtiene un buffer nuevo de 2048 bytes en cada iteración y rechaza una lectura mayor antes de copiar. ElementTree usa el C API de XML_Parse y comprueba INT_MAX en sus rutas de entrada. La revisión conserva líneas y archivos exactos, 16 guardas/modelos de longitudes y la condición de 64 bits. No se ejecutaron XML maliciosos, buffers enormes, PoC de fuga, segfaults ni un consumo de RAM significativo. Las rutas nativas externas, ctypes y todos los consumidores de C API no están agotados.

La rama actual 3.12 y la receta oficial consultadas siguen con Expat 2.8.5/CPython 3.12.15. La URL de release 3.12.16 devolvió 404; eso no prueba que jamás vaya a existir. Un candidato de corrección debe fijar fuente PSF, patch upstream exacto, hash, toolchain, receta y pruebas de ABI/imports/parseo; no basta cambiar una etiqueta o instalar libexpat Debian.

## OS: los 20 grupos siguen visibles

Se descargó de nuevo el [JSON primario Debian](https://security-tracker.debian.org/tracker/data/json). RAW actual SHA256 `77afe2bcef529dc75a5a25bafbfff60a438525d96af724a5a187c904ea2ab01d`; las 71 filas trixie mantienen exactamente el estado anterior: abiertas, sin `fixed_version`. El JSON completo grande permanece en LAB; la selección íntegra de filas y sus hashes/fechas/headers se publican con este informe. No es un rescan Trivy nuevo.

| Fuente | IDs | Siguiente acción focal |
|---|---:|---|
| acl | 2 | Separar funciones libacl de las tres utilidades CLI ausentes en rutas canónicas; no usar 2.4.0 de forky como backport estable |
| apt | 1 | apt-key canónico ausente; revisar bug Debian 642480 y el componente concreto |
| attr | 1 | getfattr/setfattr canónicos ausentes; libattr presente, alcance por componente |
| bash | 1 | Mantener condición TEMP y revisar argumentos/caller, sin excepción por severidad |
| bzip2 | 1 | bzip2recover canónico ausente; libbz2 cargada es un componente distinto |
| coreutils | 4 | Aplicar condiciones por chown/chgrp/sort y parches enlazados por ID |
| dash | 2 | Verificar flags de compilación y funciones pmatch/printf antes de inferir alcance |
| diffutils | 1 | Revisar patch upstream enlazado y su backport estable pendiente |
| gcc-14 | 2 | Separar templates de headers y operador de asignación de libstdc++ instalado |
| glibc | 21 | Función, arquitectura y callers reales; no mezclar glibc 2.43 de sid/forky |
| ncurses | 2 | Revisar funciones y backports, sin sustituir por releases ajenas a trixie |
| pam | 1 | Módulos presentes; comprobar callers y configuración de autenticación |
| perl | 4 | File::Temp y motor regex presentes; Pod::Text/Archive::Tar ausentes sólo del archivo perl-base inspeccionado |
| shadow | 3 | Utilidades y bits SUID presentes; aplicar las precondiciones de cada ID |
| sqlite3 | 4 | Un desajuste API; tres casos restantes requieren extensión, DB y caller específicos |
| systemd | 7 | libsystemd0/libudev1 presentes; daemons homed/oomd/journald canónicos ausentes, sin extrapolación a todas las APIs |
| sysvinit | 1 | TEMP conservado, sin asumir que un init del producto se ejecutó |
| tar | 5 | tar/rmt presentes; argumentos y archivos no confiables pendientes de revisión |
| util-linux | 6 | Login/chfn/chsh/mount/nsenter presentes; no replicar una función a todas las bibliotecas del paquete fuente |
| zlib | 2 | Backport de 27171 pendiente; discrepancia de rango/fuente 85091 explícita |

`os-findings71-triage.json` mantiene cada ID, binario/versiones reales, status del scanner, estado Debian de todas las releases, enlaces a parches upstream citados por Debian y la acción pendiente. `os-scan164-preserved.json` conserva los 164 objetos del scanner sin filtro. Los 71 identificadores son 67 CVE y cuatro TEMP; `id-set-relationships.json` publica los conjuntos y su intersección con SEC09, sin presentar los alcances como una suite homogénea.

Las dos discrepancias de zlib/SQLite se respaldan con paquetes oficiales descargados por hash APT y ELF idéntico al real. El source Debian de zlib tiene `debian/patches/series` vacío, carece de `gz_vacate` y del guard de `len2` para 27171. Se verificaron hashes del orig/debian.tar contra el `.dsc` primario; no se verificó su firma GPG en este host. Se conservan los IDs y la discrepancia con el tracker, pendientes de revisión independiente.

## Imagen actual, candidato y build son alcances distintos

| Alcance | Resultado observado o esperado | Pendiente |
|---|---|---|
| 55 distribuciones reales de 99c | Consulta OSV actual de los 55 nombres/versiones: cero coincidencias de distribución | No cubre vendorizados, stdlib, OS, crates Rust ni todo el código nativo |
| Wheel pip 26.2.1 fijado, CRC/hash verificados | Seis CVE por versiones vendorizadas; tres funciones urllib3 presentes y sin los fixes. Msgpack requiere Cython ausente; los dos avisos setuptools requieren archivos ausentes del subconjunto pkg_resources | Comprobación del filesystem real del próximo build; ninguna prueba de explotación remota |
| Ensurepip de la fuente PSF fijada | Wheel pip 25.0.1 SHA `c46efd13b6aa8279f33f2864459c8ce587ea6a1a59ee20de055868d8f7688f7f`; 19 consultas OSV producen 20 aliases CVE distintos, sólo coincidencias de versión | No es una distribución pip 25 instalada; bytes reales del asset en imagen pendientes. Funciones/subconjuntos de esos 20 no agotados |
| Build propuesto, pip 26.2.1 + setuptools 84.0.0 | Ambas distribuciones sin coincidencias OSV de paquete; 12 vendors setuptools sin coincidencias por versión; vendors de pip revisados separadamente | No se creó el venv. Deben inventariarse sus componentes y assets reales, incluido ensurepip, y documentar los casos abiertos durante build |
| Diez nuevos paquetes OS de d038 | Archivos `.deb` fijados verificados y sólo leídos; 14 filas de avisos fuente seleccionadas, dos krb5 ya resueltas por u1 y 12 abiertas | APT simulado, firma/expiry de índices, instalación, SBOM y SCA real pendientes |
| Runtime candidato af548 | Retira pip/ensurepip/wheels/scripts; invariante esperada 54; 53 bloques del lock de aplicación conservados en d038 y los 12 locks sin cambios en af548 | Build y revisión SEC; no cierre de 71 OS ni de SEC09 |

Los diez paquetes previstos son libpq5 `17.11-0+deb13u1`; cuatro bibliotecas krb5 `1.21.3-5+deb13u1`; libldap2 `2.6.10+dfsg-1`; libsasl2-2 y libsasl2-modules-db `2.1.28+dfsg1-9`; libcom-err2 `1.47.2-3+b12`; libkeyutils1 `1.6.3-6`. No están instalados en 99c. Las bibliotecas vendorizadas actuales de nombre parecido no son esos paquetes Debian.

Debian u1 corrige krb5 CVE-2026-40355/40356. Otros avisos requieren separar KDC/LDAP-KDB del código GSSAPI de biblioteca. CVE-2026-107778 nombra make_cred_list/rd_cred y servicios aceptores GSS; la biblioteca propuesta puede contenerlo, sin afirmar que el cliente libpq lo alcanza. DIGEST-MD5 de CVE-2026-107161 no está en los dos archivos SASL previstos; no se propone libsasl2-modules. libldap2 no incluye slapd ni mdb_load. Los avisos NSS/RFC6125 de LDAP requieren backend/configuración reales, no una comparación de major ni un descarte por severidad. Cada fila y su fuente primaria completa se conservan en `candidate10-os-dependency-triage.json`.

Una alternativa futura para reducir esas dependencias sería compilar libpq con TLS OpenSSL y sin GSSAPI/LDAP si el contrato funcional del producto lo permite; no está implementada ni sustituye la evaluación de las bibliotecas ya presentes. El candidato actual mantiene libpq Debian firmado y su closure explícito.

Los errores iniciales del harness (espaciado de macros, guard parecido en otra función, TEMP sin descripción y continuaciones del shell) se preservan con scripts y SHA. La revisión final usa las revisiones corregidas y no altera RAW, fuente, imágenes o registros congelados anteriores. Los checks de fuentes, mocks, fronteras y guardas Docker tienen alcances separados y no se suman como una aceptación única.
