# Registro web: contraseña de siete caracteres y acceso con Google

Petición del 6 de noviembre de 2026, limitada al servicio web. Candidato sobre
`772fabdc3dc1e8f493127cbc259742afbb57ae3b` en
`E:/MetodoBaseWorkspace/releases/registration-seven-google-20261106`, rama
`codex/registration-seven-google-20261106`. El usuario autorizó su publicación
el 6 de noviembre con el mensaje de commit exacto `correcion google`. El
resultado del push, deployment y comprobación pública se registra por separado
en `E:/MetodoBaseWorkspace/evidence/registration-seven-google-publish-20261106/`.

La política central para nuevas contraseñas baja de 15 a 7 puntos de código
Unicode. Registro, recuperación, invitaciones y cambio de contraseña muestran
y validan el mismo mínimo en servidor y navegador. Se conservan la lista de
contraseñas comunes, los 72 bytes UTF-8 máximos, los valores sin normalizar,
la comprobación de confirmación y los requisitos de identidad/factor existentes.
Los hashes y el acceso de cuentas anteriores conservan su comportamiento.

En `/registro`, Google aparece después del selector de cuenta y antes del
formulario manual. La comprobación pública anónima confirmó un iframe Google
real en ambas audiencias: anteriormente estaba fuera de la primera pantalla,
a unos 1288 px en móvil de 390 px y 1191 px en escritorio de 1440 px, con ventana
de 900 px de alto. La versión publicada conservaba entonces el mínimo de 15.

El componente compartido informa preparación y carga; si falla el SDK, tarda
más de diez segundos o no crea el botón, muestra un aviso y permite reintentar.
Un fallo al preparar la sesión se comunica fuera del panel oculto y mantiene
bloqueado el acceso. No se cambia OAuth, la configuración de Google, CSP, OTP,
la autoridad de sesión ni el esquema de datos.

Validación local con datos sintéticos y proveedores externos bloqueados:

- Backend: 56 pruebas aprobadas sobre SQLite migrada al esquema actual y ambas
  factories. Incluye alta/login de las dos audiencias, rechazo de menos de
  siete caracteres, blocklist, 72 bytes, acceso de cuentas anteriores y
  recuperación/invitación/cambio con sus verificaciones existentes.
- QA independiente: 16 casos HTTP/SSR aprobados. Registro y acceso personal y
  de negocio con siete caracteres ASCII y Unicode; seis rechazados sin alta;
  duplicados, correo/nombre inválidos, contraseña común y exceso de bytes.
- Root: 25 comprobaciones Node de los cuatro formularios/controladores y del
  transporte de cambio de contraseña aprobadas. DOM mínimo declarado; este
  resultado no acredita navegador, HTTP o base de datos.
- Regresión Google: 33 comprobaciones Node aprobadas sobre el controlador.
- QA Chromium: 11 escenarios aprobados, ocho capturas en 320/390/768/1440 px
  para las dos audiencias. Sin errores de página, desbordamientos ni hallazgos
  axe A/AA en las regiones comprobadas. Incluye validación de campos, Google
  hasta el OTP con proveedor simulado, SDK lento/bloqueado/sin botón, reintento,
  sesión pendiente/rechazada y configuración ausente. Navegador cerrado y
  fuentes estables comprobados.

Los resultados tienen alcances propios y no se suman como cobertura global.
No se crean cuentas productivas, envían códigos reales ni hacen cargos. La
inspección pública sólo permite GET y un refresh anónimo sin credenciales que
devuelve 401; no acredita un inicio de sesión OAuth real. Los primeros ensayos
de esa inspección bloquearon el refresh por el instrumento y no se consideran
fallos del producto; se conservan junto a la repetición corregida.

El repositorio activo tiene cambios previos independientes. La integración
local usa una combinación de tres versiones de cada ruta,
con preimágenes y comprobación de HEAD/índice; no se copia el árbol completo.
Los recibos e históricos originales permanecen intactos. Las pruebas visuales
con hashes históricos conservan sus fixtures; no se declara un gate global de
CI ni se amplían aprobaciones de otras funciones. El sondeo focal del
comparador histórico conserva nueve comprobaciones aprobadas y dos rechazos
de hash en invitación/recuperación: tras invertir exclusivamente 7 a 15, las
fuentes coinciden con la versión publicada anterior, que ya difería de la
fixture por su enlace a `workspace.css`. Se conserva el resultado rechazado
y no se modifica la aprobación histórica para ocultarlo.

Evidencia y recibos de esta tarea:
`E:/MetodoBaseWorkspace/evidence/registration-seven-google-20261106/`.
