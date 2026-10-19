# R12: publicación exacta por ID y versión

Follow-up aislado sobre `4e192d2`, después de los freezes independientes de
consumer y exportación. Fuente: adenda nueva
`backend-r12-api-contract-v2-delta.md`, RAW SHA256
`98be0cae55a02b92cbda1a699c13e14d07f1c99e4f4f7bce3251275c9509b8c6`.
La adenda407 y los cuerpos/tests anteriores se conservan en sus commits/ZIPs.

La solicitud de publicación incluye siempre expected_publication_id. Crear
exige null/version0; reemplazar exige el UUID canónico y la versión que se
mostraron. Se rechazan pares mixtos/omitidos antes del fetch. No se suman
versiones ni se interpreta una versión1 nueva como la publicación anterior.
La UI muestra plan y fecha publicados y mantiene bloqueadas las mutaciones
tras conflicto/ACK incierto. Sólo una reconsulta visible seguida de otra
confirmación genera una intención basada en el nuevo ID observado.

Se fortalecieron dos expectativas de las pruebas propias del helper para el
cuerpo aprobado y se añadieron tres pares inválidos. En el consumer se exige
el ID observado. Antes:21/23 helper y14/15 consumer; tres rojos conservados
con fuentes/driver RAW. Después:23/23 y15/15. Un caso adicional verifica la
reconsulta/confirmación tras409, incluido el cambio de ID con la misma versión1:
consumer final16/16, total focal39. Se mantienen las aserciones previas; no se
edita ningún driver independiente ni expectativas de backend por conveniencia.

Syntax Node pasa. El resto del Api RAW es idéntico al freeze export4e19 y no
cambia transporte, autenticación, cuotas o autoridad. El driver de navegador
añade la expectativa null, pero no se ejecutó en esta ventana QEMU/Ops. Sigue
pendiente la composición backend29 congelada y sus gates HTTP/browser reales;
estos resultados son VM con transportes/DOM sintéticos.
