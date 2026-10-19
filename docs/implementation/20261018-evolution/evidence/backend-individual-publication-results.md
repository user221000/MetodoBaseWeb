# Individual publication containment: author handoff

The coordinator approved implementation after QA reproduced two PostgreSQL
postcommit credit refunds with a physically persisted Plan and ready PDF.
Those before artifacts and their separate fixture-setup errors are unchanged.

The individual route now passes its reservation explicitly to the shared worker.
Under the canonical account lock, publication commits Plan, ready-object reference,
exact reservation association, UTC persisted marker and completed status together.
The repository refuses foreign, legacy, released or already published requests.
Successful finalization only verifies that association. Compensation reloads durable
state after a protected rollback and never releases published or ambiguous legacy
consumption; uncertainty yields a sanitized 503. The marker survives Plan FK
SET NULL. Compensation of an old period cannot debit another period.

Independent review found a second, real month-boundary defect: the old reserve
flow read its clock separately for the conditional increment and ledger period.
The final delta captures `sub.mes_actual` under the existing lock and uses exactly
that value for both. Root's two previously failing regressions now pass.

Author validation:

- Initial integrated gate: 73 passed in 96.15 s (58 unit/billing, 12 real SQLite/PG
  migration checks, 3 restricted-role PG lock/COMMIT acknowledgement cases).
- Worker, PDF, nutrition and startup regression: 109 passed in 74.75 s, including
  refusal of revision 25 before auth initialization in both factories.
- Final period delta: 60 passed in 8.88 s, including the two independent boundary
  regressions and all individual/billing unit checks.
- Targeted Ruff and Bandit passed. The warning emitted by tests is the existing
  Starlette/httpx deprecation, not an accounting failure.

The original 19-source freeze is
`backend-individual-publication-source.json` (digest d353e78e63c0cd3fa62d5994ad03f548e49822a3665610dae0f1b8f70a664fe0).
Final freeze is `backend-individual-publication-final-source.json` (digest
a621ebad709be5b75e3327d240f91437394076f12ade83116eead569a16bd9c6).
Only `generation_quota.py` changed between them. The DDL, targets, models and
publication path remain unchanged, so the earlier migration/publication and
worker-regression evidence remains applicable to those unchanged components.
QA's independent 7-case pre-period gate was stable and green; the coordinator is
collecting the final affected-case and current-head restore acceptance separately.

New revision `20261018_individual_publication` adds two columns and three CHECKs
only in `generation_reservations`; it still has 25 business tables and 19 tenant
families. The structural diff and source manifest verify all 20 prior frozen
targets/fixtures are unchanged. Historical object migration tests explicitly
target revision 25. No factory startup DDL, new tenant policy, storage backend or
commercial entitlement was introduced.

Operational limits: no production migration, deployment, provider operation or
legacy reconciliation was performed. Mixed old/new workers retain the old
behavior in old processes; deployment must drain them before reopening
generation. Legacy reserved requests remain protocol 0 and need evidence-based
review. A legacy released row cannot be associated with a nearby Plan to repair
past undercounting. No timestamps, associations or credits were fabricated for
those cases. No automatic orphan cleanup or retention policy was added.
