# Backend review of personal UI query delta

Commit `40fd2af0bb73326181093e59e9d3f3e6f5fbd441`, base `6d33b9e`, reviewed
read-only in its isolated worktree. No author or main files were edited.

No blocking finding in the backend delta. The extracted query retains both Plan
and Cliente owner predicates and both NULL deleted_at predicates, while permitting
inactive historical clients. ID reads add the exact Plan ID. Current-plan/history
queries retain the already selected personal profile's id_cliente; they do not
skip a deleted profile to substitute another profile. Ordering is explicit in
SQL, including the Plan ID tie breaker.

The portion from _lock_account through reservation, atomic publication verification
and compensation is identical to the base after newline normalization. No ledger,
catalog, model, migration or tenant policy changed. plan_id/pdf_url are additive
DTO fields, and the personal URL contains the exact persisted positive Plan ID;
the existing protected PDF endpoint remains authoritative.

Independent directed execution: 42 passed in 7.30 s, including all 13 independent
reader/security cases, the two monthly cases, quota/publication cases, new UI query
contracts and exact personal PDF identifier regression. A separate own Temp probe
used actual SQLAlchemy query events and HTTP history responses: one and 25 Plan
rows both required two SELECTs, including one joined Plan/Cliente query (no SQL
N+1). That probe passed in 3.67 s.

Before/after JSON records verify eight source/test hashes unchanged, exact commit
and clean worktree. This is backend-only review; frontend browser evidence remains
the author's/QA's separate acceptance. Existing unbounded history pagination is
explicitly deferred, not declared solved. There are 25 business tables at revision
26; this delta does not add a table or revision.
