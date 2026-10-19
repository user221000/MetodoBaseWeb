# Independent R07 consumer review

Reviewed private object publication/readiness/reads, logo decoding, exact plan reads, shared generation, notifications, runtime/configuration composition, both factories, the PDF/logo/personal routes, repository fields and the local/S3 adapters. Product files were read only. The author's DDL25 remains subject to separate coordinator/QA acceptance.

One contract observation was sent to the coordinator: personal download used a truthiness check for an optional integer, so an explicit zero selected latest. The coordinator added Query bounds `1..2147483647` and an explicit `is not None` branch before the independent test ran. The new regression accepts latest only when omitted and verifies zero, negative and overflow IDs fail with 422. No pre-fix execution is claimed. The standalone API does not mount the personal router; its 404 in an initial over-broad test parametrization was a review-fixture assumption, not a product regression.

The final independent gate passed 14 cases in 46.82 seconds: five new PostgreSQL cases, the new SaaS personal-identifier case, and eight existing publication regressions. PostgreSQL used fresh migrated UUID databases, the restricted application role, actual tenant hooks, a one-connection pool, real core/PDF generation and the real local object adapter. No auth, tenant, nutrition engine, PDF renderer or storage implementation was replaced; replacements were limited to selecting the owned engine/destination and injecting the two I/O/commit failures described below.

The new cases prove:

- Two owners generate and persist their own ready objects, exact PDF URL and quota result; foreign plan reads return 404, missing tenant reads see nothing, and the pool starts a blank tenant transaction after work.
- The pending record is visible to another session before PUT. Both a failure before writing and an uncertain failure after bytes are actually written retain pending metadata without a plan reference or public readability.
- A failure injected after the real repository flush, after PUT but before consumer commit, rolls back readiness, plan and persisted quota marker together. Bytes remain associated with the pending descriptor; compensation releases the unpersisted reservation once.
- After a successful worker commit, compensation retains the durable quota marker and ready object. Repeated completion produces one persisted plan and the same result.
- Temporary render directories are removed, and DTOs contain neither their paths nor `ruta_pdf`.

Code review confirmed that pending is committed before external I/O, ready plus plan/profile reference share a transaction, references do not fall back to legacy files, reads enforce owner/kind/readiness/backend and content hash/size, and new logo uploads decode bounded single-frame images before re-encoding without input metadata. Public responses do not expose object keys or internal paths. No new high/critical observation remains in this reviewed scope.

QA's old/new-PDF browser harness was also read: it generates two actual same-client plans, proves their hashes differ, contrasts the latest compatibility route, then checks that keyboard activation of the old history row fetches its exact ID with Bearer and downloads the old hash. Its setup is explicitly a synthetic Clinic/24-table SQLite snapshot; it is not migration/RLS evidence. Browser routing intercepts browser traffic rather than APIRequestContext, whose requests are currently all restricted by the hard-coded loopback base URL guard.

The evidence is local and does not approve a real bucket, mounted production volume, production cutover, retention or automatic orphan deletion. Legacy migration, logo UI and populated revision-25 restore are separately coordinated. Final source hashes and unchanged-during-check status are recorded in `backend-r07-consumers-review-source.json`; output is `backend-r07-consumers-final-independent.log/xml`.
