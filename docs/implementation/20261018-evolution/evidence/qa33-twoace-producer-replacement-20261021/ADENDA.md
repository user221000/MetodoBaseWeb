La conformidad del productor de recibos anterior se RECHAZA. Las carpetas externas
`metodobase-test-qa33-all-fixed-private-20261021-v2` y
`metodobase-test-qa33-real-complete-private-20261021-v1` conservaban cuatro ACE
explícitas: User, SYSTEM, Administrators y OWNER RIGHTS. El helper histórico
`private_directory` retiraba herencia y añadía permisos, pero dejaba esas ACE
explícitas. Sus doce documentos originales y todos los RAW se conservan intactos.
La afirmación de acceso restringido sólo a User/SYSTEM no aplica a esas raíces.

Los 45 resultados técnicos anteriores y los dos controles reales no se borran ni
se reinterpretan. El subdirectorio creado por producción
`native-private-evidence` sí tenía dos ACE y su comprobación semántica era válida.
El canario independiente b93c2ab37bd7d7d2eadd7b01606bca5e9f668c08245b8a909950534b5d49f21f
conserva los dos rechazos de raíces anteriores y ese control positivo; el sello
independiente original es 44a26b024559b7182efae3048d18ff40527c2e36.

El productor nuevo crea una raíz NUEVA mediante `scan_secrets._private_evidence`:
establece la DACL protegida exacta User/SYSTEM y verifica ambas ACE por WinAPI
antes de escribir drivers, fotografías, logs o datos de prueba. No se modificó
el helper histórico ni se corrigieron permisos de carpetas anteriores. Los dos
drivers ejecutados se conservaron en un tercer ZIP privado, también con la
frontera de dos ACE desde su creación. Los tres resúmenes adjuntos son copias
byte exactas, protegidas por atributos finitos contra conversión de EOL.

La repetición focal v3 produjo 45/45 PASS, 0 fallos, errores o skips, con IDs
exactos y pip check 0/0. Los dos controles nativos v2 produjeron salida 0 con
cero hallazgos y salida 1 con un hallazgo sintético no clasificado; duraron
1.656 y 1.671 segundos. Se conservó el límite de diez segundos del conductor,
la configuración real, redacción 100%, resumen completo y stdout vacío. La
producción mantiene timeout externo 600 e interno cero. Las seis fuentes no
cambiaron desde b3b1846a; la ejecución quedó ligada a 4d3568c3.

Las fotografías de fuente, intérprete, 92 distribuciones y los 157 archivos de
tres paquetes Node permanecieron quietas. Las tres raíces nuevas conservaron
dos ACE semánticamente verificadas antes y después. Se leyeron todos los
174 + 73 + 5 miembros de sus ZIP cerrados. El contraste independiente posterior,
sólo lectura, se selló en ac8a3a5161892a305d66949515d75a481b39beee.

La auditoría final observó cero procesos Gitleaks y el binario fijado intacto.
No se ejecutaron PostgreSQL, Chrome, Redis, VM, pytest paralelo ni un escaneo del
proyecto. Main25d1/43532 sigue sin aceptación como escaneo completo. Estos
recibos nuevos sustituyen únicamente la evidencia de conformidad del productor.
