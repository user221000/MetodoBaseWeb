# Preparación CI33, todavía inactiva

Esta carpeta es un borrador revisable sobre `6f822ff50d93e01bb10249556a9bfc4e1a3b246b`. No está lista para integrarse. No acredita esquema33, PostgreSQL, imagen, Chromium, Actions ni un proveedor. El workflow activo `.github/workflows/ci.yml` permanece intacto; la receta nueva `workflow.py` todavía no se ha generado sobre él.

Los tres imports de fixtures unitarios se han preparado para33, pero sus dependencias Google33 sólo existirán después de componer el HEAD común congelado. No se debe ejecutar una regresión general de este borrador sobre6f como si ya fuese el producto33.

## Preparado

- Materializador31/32 con commit/árbol/tamaño/modo y cada blob Git autenticados. Registra un worktree `--no-checkout` y su índice para los drivers que requieren HEAD/ls-files; los archivos siguen proviniendo exclusivamente de `cat-file`, sin archive, checkout ni filtros. No se materializaron las copias históricas durante esta preparación.
- Oráculo31 canónico `de506b6077ba055587f02e7d839387e7f5c56f84`, árbol `d5c3fabe32468ceb1f4048e0739d3ebf61f20d03`:10,208 archivos y465,700,270 bytes. Oráculo32 `6f822ff50d93e01bb10249556a9bfc4e1a3b246b`, árbol `20007e9f273d7406990cb9a607985317f3473935`:12,364 archivos y650,870,175 bytes.
- Treinta adaptaciones explícitas: diez de fixtures/R12/R24/unit, ocho de suites y doce de framing browser/export. Mapas con SHA normalizado y completa inversa o importación exacta de las funciones de negocio originales. Ningún helper23 de CI30 ni target22–32 se edita.
- Guardia portátil de recursos optativa para descendientes del runner: lease exclusiva antes de CREATE, OID/owner/PID+nacimiento, cero sesiones y DROP ordinario con ausencia fresca. La aceptación real de esa guardia en PG sigue pendiente. El adaptador portátil de retirement32 sustituye sólo su dueño de recursos Windows, conservando los blobs y criterios32.
- Contrato físico33 desde consultas reales:35 ORM/36 físicas/26 FORCE/26 funciones/12 triggers, FKs validadas, rol4flags false/noowner, pool1 y GUCs vacíos. Es código preparado y todavía no ejecutado. Los pools mayores de las carreras y browsers existentes se conservan como excepciones de concurrencia explícitas.
- Receta de separación historical30, historical31, historical32 y current33, conservando serial/cobertura/SDK/n2/no-skips/desktop/Redis. Los jobs antiguos31 no se presentan como ejecuciones33.
- Adapters export de fixture7→8: conservan los17/21 callbacks y sus asserts. Preparación Node sobre fuente32:17/21, progress_export38 y retirement36/DOM9; son ejecuciones de framing32, con repeticiones declaradas, no criterios únicos ni aceptación33.

## Dependencias para completar después

1. HEAD común33 y entorno Backend92 congelados. No se ejecutó ni atribuyó su WIP. Los paquetes se compararán antes/después por plataforma;92 de Windows no será un número impuesto aLinux.
2. Root incorporará ancestry canónica31 en COMMON33 mediante el `merge -s ours` autorizado, sólo si falta, probando write-tree idéntico. En6f, `merge-base --is-ancestor de506 HEAD` devuelve1. Ningún fetch de ref mutable sustituye este requisito.
3. Completar `run_postgres.py`, `check_google33_reports.py` y `verify_google33_ci.py`; la receta referencia esos nombres futuros y no está activa. Coleccionar los nodeIDs reales sólo después del freeze, fijar JSON y ancla del ejecutable completo, y reproducir positivos y mutantes por API y CLI (identidad, dialecto, duplicados, counters, estados, firmas, falso main0 y uploads sin RAW).
4. Insertar/validar los testigos globales completos en todos los marcadores browser/imagen preparados. Los frames33 actuales conservan los checks previos y actualizan head/conteos, pero todavía no se atribuyen a una ejecución global33. Verificar hashes de binarios y fuentes Google33 definitivas.
5. Resolver explícitamente la autodiscovery de oráculos Google31 con Root/Backend antes de mover archivos. `test_identity_security.py` contiene dos casos Google y otros casos/fixtures que siguen siendo consumidos; no se debe mover el módulo entero. Backend conserva2 funciones/7 asserts en identity33,4 funciones/14 casos/8 asserts en reauth33 (URL tokeninfo→JWKS),3 funciones/8 casos/17 asserts en asociación33 (metadata tokeninfo→JWKS). Su mapa completo y firmas provendrán del freeze. No se aplicaron ignores, skips, xfails, renombres ni alteraciones de esos criterios.
6. Completar publicación cerrada de testigos, metadatos, origen y JUnit estructural; medir PG real con UUID nuevas y cierre normal. Histórico31 debe conservar y ejecutar sus gates propios; histórico32 debe declarar su adaptación de recursos. La proyección sensible debe fallar cerrada.
7. Generar el workflow final, revisar cada referencia y bloque Bash, ejecutar suites actuales y negativas sobre el HEAD común y después congelar una aceptación acotada. Imagen/browser/Actions requieren ventanas separadas; esta preparación no los acredita.

El primer generador se detuvo por la capitalización `Current31` antes de escribir adapters; el sucesor corrige ese framing y mantiene todos sus guardias. El error original de herramienta se conserva en la conversación y se declara como proyección en la evidencia, sin inventar un RAW inexistente.
