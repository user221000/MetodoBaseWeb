# Reconciliación local de 155 criterios

Draft independiente de lectura de código, contratos y recibos existentes, fechado 2026-10-21. [JSON completo](RECONCILIACION_155.json): una fila por ID original, sin renumeración ni cambios del texto del criterio; cada fila conserva el SHA-256 UTF-8 del criterio del registro congelado en `29c583830d3afc8aaf7f65bac58cbb4250b08a40`. Runtime de aplicación `59b64e029e06e1cdff69f7f4702aa8d664b65f66`. Main no fue editado y no se ejecutaron pruebas, SQL, servicios, navegador, red ni escáneres en esta revisión.

Las propuestas distinguen implementación existente, trabajo técnico faltante, gate ya planeado y validación externa. `verificado` significa aceptación **local del criterio acotado**, sin despliegue, correo recibido, cumplimiento global ni aceptación de un criterio padre. Son propuestas para revisión del coordinador, no modificaciones al registro oficial.

| Prioridad | Corrección del backlog | Acción vigente |
|---|---|---|
| QA-29 | Bootstrap léxico `Api` corregido; Native35 actual contiene las18agrupaciones de cuenta/notificaciones con0pageErrors. | Cerrar localmente. Conservar35grupos en4fases y32capturas como alcance real. |
| R22 | PG16autor+19peer y navegador2R22 ya aceptados. | Retirar bloqueos técnicos vencidos. Faltan5dueños+5socios reales y contrato de procedencia/separación de demo. |
| OPS07 | VM/Linux y builds históricos ya existen. | Construir imagen57 actual con presupuesto de disco; capturar digest/inventario/SBOM/SCA/rollback. No pedir habilitar virtualización otra vez. |
| R31 | RAM/cookie, export y consentimientos/retiros específicos están implementados. | Faltan cierre/purga integral de cuenta/objetos/copias, soporte acotado y política legal de retención. |
| B02/B03/B05 | Suscripción unificada, reserva atómica y tenant por transacción ya están implementados. | Sustituir `pendiente` por revisión de evidencia local; conservar sandbox/adopción y gates globales pertinentes. |
| UX-03/04/10/11/15 | Persistencia civil, consumo real, CTA y gestión de cuenta están implementados y tienen controles locales. | Propuesta de cierre local; no equivale a correo recibido ni piloto humano. UX-06/07/12/17 también tienen implementación y no requieren rehacer sus flujos por estados viejos. |
| R36 | ReplayPG30autor+12peer PPL ya terminó dentro dePG53. | Cerrar localmente el catálogo con su evidencia de navegador; no atribuirle11R30 ni53HTTP. |

Trabajo local que una nueva corrida broad no implementa por sí sola:

- **B19:** el validador común sólo comprueba tipo, mínimo12 y máximo72bytes UTF-8; falta bloqueo por contraseña completa comprometida/común. Root asignó implementación aislada posterior a este draft. No cambiar login de contraseñas existentes.
- **B13:** conciliadores existen, pero búsqueda en scripts/services/routes sólo encuentra llamadas desde callbacks; falta job/CLI periódico. Reutilizar verdad canónica/locks/idempotencia, sin inventar derechos legacy.
- **B20:** no se encontró procedimiento técnico completo de rotación de `SECRET_KEY`, cutover, revocación y rollback. El criterio no obliga `kid`/keyring ni formato nuevo. Root prepara runbook y ejercicio técnico.
- **R07/B11:** inventario histórico readonly no aplica objetos. Faltan apply con procedencia aprobada, coordinación de escritores, CAS y journal; después validar durabilidad/redeploy con proveedor real.
- **R20/R31:** actualizar `PRIVACIDAD.md`: aún afirma tokens en localStorage, MFA pendiente y ausencia de consentimientos/diario. Los consentimientos existentes son específicos; no sustituyen revisión legal general. Cierre/borrado integral requiere contrato/política y una implementación posterior.
- **R22/R30:** la analítica declara `unclassified_no_persisted_flag` para demo. Definir procedencia/separación sin inferir ni backfillear usuarios arbitrariamente.

Los gates ya planeados siguen abiertos: CI completo serial/n2/cobertura, fullscan correcto QA-33, imagen57 real/SBOM/SCA/rollback y Redis/carga. La matriz CI sí incluye Python3.11/3.12. Integración de126helpers y colección5536 no equivalen a esos resultados. La nueva política B19 cambiará fuente: Native35/PG53 permanecerán como evidencia anterior, sin atribución automática al candidato posterior.

Continúan externas la recepción/entregabilidad de correo, sandbox operativo de pagos, backups/proveedor/retención/RPO/RTO, revisión nutricional/legal, recuperación excepcional/custodia y piloto5+5. Cola general R28 y PWA R35 son condicionales a métricas/decisión; reservas/replay no prueban una cola general y no justifican implementarla por inercia.

Se conservan30criterios ya verificados. Se proponen24cierres locales adicionales; los demás permanecen en revisión/curso o fuera de alcance. QA-19 y la parte offline/hardware de SEC01 son históricos desktop excluidos por el usuario; no generan trabajo desktop. Free web es10clientes/1plan por cliente al día/10totales diarios/20mensuales.

El catálogo de referencias del JSON explicita que PG429 es composición29fases, PG53 son53IDs con un caso puro, Native35 son grupos/fases y el helperR30 sigue provisional, sin baseline poblacional ni procedencia verificada. Un ACK del proveedor nunca se trata como entrega externa. Los cierres propuestos deben revisarse granularmente; este informe no declara finalizado el backlog.
