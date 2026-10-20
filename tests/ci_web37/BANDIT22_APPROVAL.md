Root aprobó el registro `bandit22-approval.json` el 2026-10-20 para sus 22
ocurrencias y contexto delimitado, con caducidad el 2026-11-19. La propuesta y
el matcher independientes fc08 se conservan literalmente:
continúan declarando approved=false y exceptions_applied=0. El baseline histórico
de seis entradas no se modifica ni se vuelve a aprobar.

El consumidor exige una aprobación separada de Root, los 22 occurrence IDs
exactos, los dos revisores, Bandit 1.9.4 y fecha entre 2026-10-20 y 2026-11-19.
Un cambio de multiset, regla, span, AST, función, fragmento, import/caller,
dependencia, contexto o caducidad rechaza el conjunto completo.

Hay 5 entradas de fuente y 13 de dependencia: 17 paths únicos porque una versión
aparece en ambos grupos. Se autentican dos conjuntos completos de bytes:
captured_main_raw y authenticated_git_lf. Para los 17 paths, el productor cotejó
el blob Git de f060 con la captura SEC; doce difieren únicamente por el framing
LF→CRLF exacto y cinco son iguales. El consumidor no transforma fuentes ni admite
mezclas entre ambos conjuntos. Los doce inputs Docker no se modifican.

Los veinte B608 corresponden al SQL estático revisado. B108/B310 se limitan a la
entrada exacta expat-build del Docker actual, después de verificar sus doce
inputs y catálogo57. La comprobación estática no demuestra aislamiento del SO,
seguridad de ejecución compartida, runtime de imagen ni cierre SCA/CVE.

```text
python -B -X utf8 tests/ci_web37/run_web.py --suite registry-controls --private <privado-nuevo-absoluto> --output <publico-nuevo-absoluto>
python -B -X utf8 tests/ci_web37/quality.py security
```

Antes de esa decisión el registro se conservó pendiente; las fases históricas
de controles y sus rechazos no cambian. Los 17 controles construyen una autorización sintética explícita para los
positivos y una autorización pendiente explícita para su negativo. Funcionan
antes y después de la decisión real de Root. Pasar controles no aprueba el JSON
real: el consumidor exige también el registro de aprobación independiente.

En el replay RAW GitLF 2c0aeebfb33488e2e6c9cd80eeec7827d4f9edae, el gate real
Bandit1.9.4 obtuvo 28 hallazgos: seis históricos preservados y 22 coincidencias
aprobadas, cero pendientes/errores. Lint, sintaxis y nueve pruebas negativas con
seis controles positivos terminaron con exit0; 17 controles WEB92 también
pasaron. La fuente y ambas instalaciones permanecieron quietas. El entorno de
herramientas tiene 81 distribuciones y carece de pip; no se afirma consistencia
pip para él. Esta aceptación pertenece sólo a esa fuente; Main posterior debe
ejecutar su propio gate. No acredita release, SCA o aislamiento del SO.
