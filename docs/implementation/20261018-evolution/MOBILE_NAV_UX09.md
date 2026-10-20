# Menú móvil y títulos de cuenta

Base: `5666a9ba8e03741ae6e983b6d21dfd93de466836`, worktree exclusivo
`F:/mb-mobile-nav-20261020`. Corrección focal de presentación UX-09/R13.

Se inspeccionaron con view_image las capturas históricas `account-ready-390`,
`personal-security-390` y `new-kit-masked`, del prefijo
`qa-r31-native-mfa35-dom-independent-20261020/mfa_ui_browser`. Son evidencia
de esquema 35 y no se presentan como aceptación del runtime 37 actual.

Los dos botones de menú estaban fijados al viewport con top 16/18px y z-index
superior al contenido. El relleno superior de main sólo protege la apertura
inicial: el foco o desplazamiento puede colocar un título detrás del botón.
Además session-shell conserva la isla de kit MFA moviendo su mismo nodo antes
de main al invalidar la sesión; ese nodo deja de beneficiarse del relleno de main.
No corresponde mover, copiar ni serializar sus datos para corregir el layout.

El cambio pone el botón en el flujo anterior al contenido, conservando
su posición DOM, ID, aria-controls/expanded y manejadores actuales. Se ajusta
únicamente el relleno móvil que compensaba su posición fija. Así botón y título
se desplazan juntos; al enfocar un título situado más abajo, el botón queda
fuera del viewport en lugar de cubrirlo. El menú continúa disponible arriba de
la página y vuelve a ser visible al recibir el foco. En escritorio permanece
oculto y la barra lateral conserva su layout. No se reduce la fuente ni se
oculta el desbordamiento como sustituto.

Sólo se modifican `styles.css`, `styles-usuario.css` y `account-security37.css`.
En la base profesional se elimina el override de padding-top 80px y permanece el
padding móvil 20px existente; en la personal el padding 70px pasa a 10px tras la
fila del botón. Se elimina sólo el padding-top 4rem específico de cuenta, que
duplicaría espacio con el nuevo flujo. El botón personal pasa de 42px a 44px.

Ámbito de validación: `/cuenta/seguridad`, `/mi-seguridad`, `/recordatorios` y
`/mis-recordatorios`, con las dos bases; también la isla MFA preservada fuera
de main. Objetivos geométricos: 320/390/768/1440, intersección nula entre menú
y título, texto sin bloqueo de puntero, foco visible, menú accionable y ausencia
de desbordamiento de documento. QA conserva el canario antes/después con fuente
propia e inmutable. No se interpreta axe sin errores como prueba de legibilidad.

`tests/test_mobile_navigation_markup.py` usa sólo Jinja sintético sin app/auth/API:
cuatro plantillas reales conservan un menú único con nombre y relación ARIA,
main e h1 únicos y scripts con nonce. Es una regresión semántica, no una prueba
geométrica ni una aceptación de MFA, Google, notificaciones o permisos.

El autor no ejecuta Chrome/PG en esta fase; ROOT concedió la ventana focal de
Chrome offline a QA. No se modifican JS, APIs, contratos, sesiones, privacidad,
business assertions, nonces, backend ni desktop. Las preimágenes RAW se guardan
con -text antes de editar. El manifiesto distingue RAW/GitLF y las dependencias
protegidas y registra la inversa exacta del cambio CSS.

QA cerró el antes geométrico con 16/16 rojos, cero pageErrors, sin SQL y Chrome
propio cerrado. Su oráculo 91963fd5 y driver ef7c8dca quedan intactos: foco y
scrollIntoView sobre cada título real, intersección e hit-test de texto contra
el menú y desbordamiento horizontal. El DOM inerte usa CSS/markup reales de 37;
no valida autenticación, operaciones, red ni interfaz funcional. Referencia:
`qa-native37-mobile-before-20261020/freeze.json` en el worktree de QA. El after
geométrico y la tanda nativa 37 son revisiones independientes posteriores.

Regresión semántica del autor: 4/4 antes y 4/4 después, sin contar 8 criterios
distintos. Comando desde este worktree, con el entorno Python existente:

```text
python -X utf8 -m pytest tests/test_mobile_navigation_markup.py -q --tb=short --noconftest
```

El autor no afirma axe, navegación funcional, autorización ni aceptación general
de accesibilidad. El gate global de secretos sigue abierto; un escaneo acotado
de las fuentes de este cambio no clasifica el árbol ni su historia.
