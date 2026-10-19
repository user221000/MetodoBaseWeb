# Asociación de etiquetas en ambos login

Delta de producto separado: sólo `for/id` de correo y `for` de contraseña en `login_gym.html` y `login_usuario.html`. La preimagen exacta es el commit UI `fa48edf3568ab9c3e753c8cf5ef69c784f69e065` (y su cherry `933f19f`), que conserva el contenido anterior en `evidence/mfa-ui/vm-tested-raw.zip`.

`login-labels-before.log/xml`: dos rojos por no existir asociación programática entre las etiquetas visibles y esos campos. La misma prueba y condiciones pasan después: `pages-labels-after.log/xml` registra dos casos de etiquetas y ocho del router de páginas existente, diez verdes. No se modifican las expectativas para acomodar el producto. El controlador, endpoints, auth/Storage y transporte quedan idénticos a la freeze VM.

La primera captura del navegador posterior detectó contraste durante una animación de opacidad aún activa. La salida y el frame están preservados. Al esperar sólo las animaciones finitas antes de axe, el mismo producto pasó sin modificación CSS; no se presenta aquel frame como un defecto de contraste permanente ni se oculta el primer rojo.
