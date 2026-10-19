Propuesta de refresco **sólo de metadata**, preparada sobre 7c013f12dd66b68dc15769e185756610eb2ca2e5. Requiere revisión independiente antes de cualquier nuevo build. No se recompiló, instaló ni validó pyexpat/libpq, y no se modifica la imagen final, su cuenta 54 ni sus otros gates.

El primer target expat-build falló cerrado en native-runtime: sha256sum rechazó trixie-updates/InRelease después de validar APT las firmas. Se conserva el container detenido y el contexto/tar exacto del primer intento. El pin anterior 1ff5b5841ba7a91e3e4c1f43a5a0886d0a5987f1ab03c5fa3a04dbca0c6e7edf corresponde al firmado de 08:07:51 UTC. El propuesto 3ea800baec602255b1b450a0434052c05cf9eb72636eaf0b0144e0bd0a181080 corresponde al firmado de 14:08:25 UTC del mismo 19 de octubre de 2026.

GPGv devuelve 0 para ambos documentos, con fingerprints exactos 4CB50190207B4758A3F73A796ED0E7B82643E131 y B8E5F13176D2A7A75220028078DBA3BC47EF2265. Se empleó un directorio temporal vacío, sin keyserver ni keyring global, y el keyring binario exacto de la base fijada por digest. Su SHA-256 es 506b815cbb32d9b6066b4a2aa524071e071761e7e7f68c3ac74f3061ba852017. El alias .gpg es un symlink del paquete a .pgp; el primer extractor conservador lo rechazó y quedó conservado. La extracción corregida sólo admite ese destino exacto. El recibo compara esos bytes con un container creado desde el digest base y nunca iniciado, y verifica la prefijación de layers de la imagen fallida. No se ejecuta negocio ni se comparte un directorio host.

El diff del contenido firmado cambia únicamente Date y Valid-Until. La vigencia anterior acaba el 26 de octubre de 2026 a las 08:07:51 UTC; la nueva, a las 14:08:25 UTC. Ambas estaban vigentes durante la preparación. Las 409 entradas SHA256 del índice updates son idénticas. El índice comprimido completo amd64 continúa con SHA10012cb384dc2613586d7b3d391d92a5637c9faa36017239739f2a6109a0d45f y tamaño4412. Los InRelease de stable/security permanecen idénticos por bytes y GPGv0; sus índices comprimidos completos también conservan sus hashes firmados.

Se volvieron a leer y autenticar los tres Packages.xz completos preservados. Los once registros originales seleccionados de compilador/libc/libpq/OpenSSL, incluidos Version, Depends, Filename, Size y SHA256, son idénticos. También lo son los diez registros del cierre runtime previsto. Libpq sigue17.11-0+deb13u1; OpenSSL/libssl sigue3.5.7-1~deb13u3; gcc sigue4:14.2.0-1 y libc6-dev sigue2.41-12+deb13u4. No cambió ningún índice de paquetes, por lo que no se recalculó ni se descargó un conjunto alternativo para hacer pasar la propuesta. No se afirma una nueva simulación APT ni una instalación exitosa.

La comparación de before.tsv con el dpkg/status del container fallido confirma87 paquetes base idénticos y libssl3t64=3.5.7-1~deb13u3. Libpq/gcc aún no estaban instalados: el fallo ocurrió antes de esas órdenes. Esta invariancia corresponde al PREIMAGE fallido y no a un builder o runtime ya reparados.

El único cambio fuera de este directorio de pruebas es una línea en requirements-container-apt-metadata.lock. Se congelaron por hashes antes/después los otros once locks y Dockerfile/helper/patch/pins Expat. El archivo original, el freeze7c y el primer build rojo no se alteran.

Archivos de revisión:

- old-updates.InRelease y current-updates.InRelease: documentos firmados completos.
- debian-archive-keyring.gpg y base-keyring-receipt-source.json: keyring exacto y vínculo al digest base inmutable.
- old-signature-source.json, current-signature-source.json y current-updates.gpgv.*: recibos y firmas verificadas.
- signed-payload.diff y lock-one-line.diff: ambos deltas exactos.
- proposal-source.json: fechas, hojas SHA, registros de paquetes/dependencias y snapshots de archivos protegidos.
- base-dpkg-invariance-source.json: paquete base antes/después del fallo.
- prepare_metadata_refresh.py y drivers auxiliares: operaciones de lectura/preparación ejecutadas.
- manifest.json: tamaños/hashes de esta evidencia.

La lease del QEMU propio permanece idle por instrucción explícita de root. Se conserva fingerprint PID/birth/exe/CMDhash, puertos53105/53106 propios y SSH por clave privada no divulgada. No hay nuevo servicio ni puerto, acceso PG o proveedor, cambios al hipervisor/sistema, borrado de imágenes/datos ajenos ni nuevo build autorizado por esta propuesta.

