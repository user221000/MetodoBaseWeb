# Puente de MFA R31 sobre HTTP real

Los cuatro casos pasan: lifecycle y late-ack contra api.app y web.main_web.
El JavaScript real se comunica por IPC privado con TestClient HTTPS, cookie
HttpOnly y Origin coherentes. Se usa migración de sesión, enrolamiento/TOTP
real y acciones protegidas; sólo el puerto externo de pago está doblado.

El ACK tardío no adopta la identidadB ni publica sus credenciales. La RAM queda
vacía y bloqueada; una comprobación HTTP independiente demuestra queB conserva
su sesión. Las19 aserciones de lifecycle y7 de Python se conservan del fixture
previo. Fuentes1215/Python/92 distribuciones/Node quedan estables durante16.375s.
No es navegador nativo, PostgreSQL, imagen, despliegue o cierre global deR31.
Sólo servicio web.
