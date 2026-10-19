# Revisión independiente MFA31: preimagen original

Fuente examinada: 56e810b3a0518231ba013cab29d68ee0aba0bacd, checkout propio. Este hito conserva los fallos originales; no los atribuye a correcciones posteriores. La primera revisión de aliases permanece inmutable en security-mfa31-initial-independent-20261019/source.json (adfd99db...).

Los seis conjuntos finales de este hito contienen 45 casos: 37 verdes y ocho rojos reales. Los dos rojos PRIMARY son respuestas503 ante key ausente con Referrer-Policy insuficiente. Otros dos son grants emitidos para ADMIN cuyo OWNER padre tiene invitation_token no NULL; cuatro adicionales cubren literal vacío no NULL del actor OWNER o padre. Los estados ambiguos fueron preparados directamente en una base sintética: no se afirma que la API actual los introduzca, ni se ejecutó invitación, cobro o acción con esos grants. No se demostró fuga de credenciales ni salto del segundo factor.

El driver inicial de atomicidad tuvo cuatro errores de criterio/preparación: tres recorridos asumieron router de equipo montado en api.app y otro exigió400 cuando el contrato de binding usa403. Se conserva íntegro (6 casos, 2 verdes/4 fallos); la variante nueva v2 limita HTTP de equipo a la factory Web realmente soportada y exige403 exacto. Sus tres casos finales verdes comprueban mutación+consumo de grant+SV en la misma TX y rechazos de body/recurso/método que no consumen el grant. No se contabilizan ambos intentos como casos únicos adicionales. También se conserva el error de quoting de shell, sin ejecución de producto.

| Frontera revisada | Evidencia independiente y límite |
|---|---|
| Primaria/desafío/sesión | 202 sin par ni refresh durable prematuro; tampering y vencimiento300s; falta de key no elimina MFA. PRIMARY headers queda rojo aquí. |
| Criptografía/dominios | AESGCM rechaza otro usuario, factor_id, generación, propósito, key o ciphertext alterado; sin key por defecto. Semilla sólo en respuesta autorizada. |
| Un uso | OTP usado en login rechazado en step-up/reemplazo; recovery consumido en step-up rechazado en login; contador durable y challenge. Contención real propia en hito PG separado. |
| Acciones/autoridad | Registro cerrado y DTO normalizado; acceso/cuenta/propósito distintos rechazados; binding recurso/body/método no consume grant. Idempotency-Key de aliases se documentó rojo en el primer hito. Elegibilidad canónica requiere corrección SEC13. |
| Testigo reciente | Instante durable original conservado al consumir/emitir; refresh conserva login original y no copia testigo posterior de otro access; límite300s sin deslizamiento. |
| Commit/ACK | Antes/después del commit real de login, confirmación de factor y mutación Web:503 opaco sin par/kit/éxito prematuro; los efectos durables no se compensan ni resucitan. |
| RLS/contextos | Lectura estática de cap personal app.mfa_actor, sin otorgar tenant profesional; ejecución PG propia y pool1 en hito separado. No es defensa frente a SQL arbitrario de un proceso comprometido. |
| Locks/SV | Orden Usuario.id total y NOWAIT antes de recursos; logout/reset invalidan challenge/proof/grant/refresh y conservan factor. Carreras reales de logout en hito PG. |
| Admisión | Presupuesto actor+propósito sobrevive nuevas sesiones/desafíos; Redis requerido en producción falla cerrado aunque flag legacy esté desactivado. Puertos sintéticos. |
| Google | Respuesta tokeninfo sintética fija: auth_time original requerido, iat no lo sustituye; identidad distinta y tiempos ausente/futuro/vencido rechazados. Sin contacto real. |
| Wire/privacidad | Stream32768, JSON duplicado/no finito, tipos y extra-fields rechazados sin crear autoridad; errores operativos registran clase técnica, no parámetros/secretos. No auditoría universal de logs históricos. |
| Esquema/ciclo | Modelo/migración31 leídos; comparación Git confirma políticas previas y targets22–30 intactos. Reemplazo mantiene factor previo hasta confirmar, cambia generación/AAD y corta material anterior. Restore31 y UI no se atribuyen a este hito. |

Alcance pendiente: revisión de integración/UI y de restauración por QA, avisos de cambio por correo, custodia/rotación/recuperación real de la key, disponibilidad/configuración real de Google/Redis/correo y pérdida total de factores con prueba equivalente. No existe bypass local de recuperación. TOTP no resiste phishing; no se declara ASVS, AAL2, cumplimiento legal, retención, rendimiento ni cierre total R32/R31.
