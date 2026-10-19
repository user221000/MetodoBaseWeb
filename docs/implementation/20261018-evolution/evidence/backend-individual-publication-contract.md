# Individual publication recovery contract — proposal

Status: implementation authorized by the coordinator after QA's real PostgreSQL
reproduction: 2 failed / 1 passed in 25.92 seconds. Both delivery-error variants
observed credit 0 -> 1 at worker commit -> 0 after compensation, with Plan and
ready PDF still persisted. Initial 401 fixture failures are test setup errors,
not evidence of the product defect; their artifacts remain unchanged.

## Observed gap

`web/routes/usuario.py:generar_plan_usuario` reserves a credit, then calls the
shared worker without passing the individual reservation. The worker commits
Plan and ready-object reference independently. If its return/delivery raises,
`generation_quota.finish_generation(..., success=False)` releases the credit
using only `status == reserved`. The committed result is not consulted or linked
atomically. A later success-finalization failure also leaves a committed result
with an unlinked reserved request.

## Proposed internal interface and transaction

Add kw-only `individual_reservation_id=None` to the web worker wrapper,
`generate_plan`, `build_plan`, its internal builder and `repository.registrar_plan`.
It is distinct from, and mutually exclusive with, the existing gym
`reservation_id`. No HTTP caller can choose the reservation subject: the personal
route passes the ID it reserved for its authenticated canonical user.

Extend `GenerationReservation` with `persisted_at` (nullable `UTCDateTime`) and
`publication_protocol` (integer, legacy 0, new reservations explicitly 1).
There is no new table, second timestamp or result JSON. Retain the existing
`plan_id` FK with `ON DELETE SET NULL`.

After pending metadata commits and PUT finishes, the final worker transaction:

1. Locks the canonical Usuario row, then reloads the individual reservation.
   It requires the same user, protocol 1, reserved status, no persisted marker
   and no linked plan. The client must belong to that user. A released,
   completed, foreign or legacy reservation cannot publish another plan.
2. Stages ready-object status and the Plan, its exact object reference and client
   counters. The repository atomically links the exact Plan to that reservation,
   sets `persisted_at` and `status=completed`, requiring exactly one eligible row.
3. Commits all of those writes together. Failure rolls them back together;
   independently committed pending metadata/bytes remain for review.

`finish_generation(success=True)` verifies this durable completed association
under the same account lock and is idempotent. It must not adopt an arbitrary
owned Plan supplied by its caller. A missing Plan, mismatched ID, legacy reserved
row or absent marker yields a stable reconciliation response rather than a
refund. A completed legacy row retains its consumption even with a NULL FK.

## Failure, replay and uncertain commit

Capture reservation/user IDs as primitives before entering the worker. On worker
failure, compensate only after a protected rollback; open a new transaction,
lock the account, and reload the ledger with `populate_existing`. Release/debit
reversal is allowed only for protocol 1, reserved, unlinked, unpersisted rows.
The monthly counter is decremented conditionally only in the captured period
and only once. Never release completed or persisted rows, including after Plan
deletion has cleared `plan_id`.

Worker publication uses the same account lock. If compensation wins first,
the final publication transaction rejects the released reservation; if publication
wins, compensation observes completed/persisted state and preserves the credit.
An uncertain COMMIT is resolved by that fresh durable read under lock, not by the
exception class or a timeout. Failure of rollback, locking, reload or compensation
commit returns 503 `generation_reconciliation_required`; it does not claim a
refund. A repeated compensation rechecks state, so a committed-but-unacknowledged
release cannot decrement twice.

Completed retries load only the exact linked authorized Plan and return the
existing personal response, without generation or another debit. Missing/deleted
results return an unavailable/reconciliation status without releasing consumption.
An idempotency key for a released or unresolved request does not start more work.

## Legacy and schema boundary

The new revision follows `20261018_stored_objects`, preflights its exact frozen
schema/security contract and adds only these columns/checks. Existing rows are
protocol 0 with NULL persisted marker. No association or timestamp is inferred
from nearby Plan IDs, dates, owner-only matches or PDF paths. Existing completed
and released states remain unchanged; reserved legacy rows require review.

At least enforce protocol in (0,1), no released row with a persisted marker, and
no persisted marker without protocol 1. Do not require a non-NULL Plan FK for a
persisted/completed row because `SET NULL` must preserve the durable accounting.
Keep targets and fixtures for revisions 24/25 byte-for-byte unchanged. This is a
new revision, still 25 business tables and 19 RLS families, not the diary table.

## Files and acceptance

Product: `web/routes/usuario.py`, `web/routes/planes.py`,
`web/services/generation_quota.py`, `web/services/plan_generation.py`,
`web/database/repository.py`, `web/database/models.py`, a new Alembic revision,
`schema_control.py`, and new per-dialect targets/test SQL fixtures. Tenant policies,
factories and entrypoint need no new behavior: existing startup gates require the
new exact head. Their tests must prove old-head refusal and current-head success.

Tests: retain QA's real core/PDF/auth/RLS postcommit reproduction; add rollback
before publication, missing/foreign/mixed reservation parameters, no arbitrary
Plan adoption, exact replay, SET NULL survival, month rollover, concurrent
publish-versus-release and uncertain commit/rollback handling. Test actual UTC
binds for the new instant under UTC and Mexico City sessions. Verify populated
25-to-new-head migration, no-op rerun, injected DDL rollback, FK preservation and
restore of the current head. Pin historical stored-object migration tests to
revision 25 instead of letting their expected revision follow `head`. Adjust the
existing synthetic billing success test to publish through the new explicit
contract rather than teaching production code to accept an unlinked mock Plan.

The coordinator approved this contract and local implementation. Product and
DDL will be frozen for independent review before broader gates; this document
does not itself establish acceptance, deployment or production reconciliation.
