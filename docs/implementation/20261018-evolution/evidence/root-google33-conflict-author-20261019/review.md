# Google33: colisiones durante flush previo al commit

Fuente 8a5e5dc235e96a47488befb743fc02a24b491939. El peer original halló
una carrera real de alta gym: 200+503 en vez de 200+409. La transacción sí
conservaba una cuenta, vínculo, perfil y cinco plantillas; no hubo adopción de
cuenta ni credenciales para el perdedor. El flush del perfil ocurría fuera del
catch estrecho. En confirm, autoflush True podía adelantar la misma colisión.

La frontera de IntegrityError ahora cubre todos los flush de ambas escrituras.
Sólo rollback confirmado permite409; incertidumbre de rollback permanece503.
Sin retry, relectura, adopción del ganador ni cambio de identidad, DTO o DDL.
La inversa completa recupera el servicio anterior. El test final conserva el
AST de su función original; sólo cambia el framing de importación de fixtures.

Baseline HTTP sintético de fallo de constraint: dos FAIL y dos PASS, mismos
cuatro casos por fábrica y disponibilidad de rollback. Corrección:4PASS;
58 regresiones existentes PASS; replay de framing final4PASS. Estos replays
se solapan y no se suman. Fuente842,92 paquetes y Python quietos,pip0.
Ruff del test0; los ocho diagnósticos preexistentes del servicio no aumentan.

Los originales fallidos completos quedan en archivo privado protegido antes
del payload y verificado tras readback. La tabla de casos pública es derivada,
no RAW; conserva los hashes originales. El directorio inicial no tiene
atestación retroactiva de ACL. No ejecutó SQL PostgreSQL ni prueba Google real.
La carrera multiproceso espera revisión independiente sobre este commit.
No cierra Google33, R05 global, CI o la release completa.
