# Follow-up34: author SQLite candidate, PostgreSQL pending

The technical wire is the immutable RAW contract SHA256 `33bfe88f33705cb33b70c2ef2b57951e9ee59cb7176466143e93d3822fd83f91`. Its original pending-runtime status is preserved. ROOT signed the DTO technically in a separate receipt; this is not independent security, UI or runtime acceptance.

## Scope and authority

Revision34 adds Task and append-only Event tables. An Event INSERT is the sole mutation primitive; invoker triggers validate the transition and atomically apply the current Task projection. History is not rewritten. A partial unique index permits one open task per gym/client/cause; terminal tasks can recur only through a new explicit creation with current evidence. Typed snapshots store counts/dates/cause and operational declarations, with no contact, payment, health-note or arbitrary JSON field. RESTRICT is an integrity boundary pending separately reviewed whole-scope purge under R31, not a retention policy.

Canonical persisted OWNER/ADMIN manage gym tasks. The explicit Nutri permission reads only currently assigned tasks and completes only its eligible assignment. It does not enable global statistics, reassignment or membership rights. Every resource query repeats gym/client ownership and active/non-deleted client predicates. Actor/assignee eligibility uses strict invitation NULL, valid current session version and persisted same-gym membership. Unavailable historical identities return a neutral null name; their new-context names or contacts are not queried. Reactivation eligibility follows the current same-gym UUID, without an invented employment epoch.

All required Usuario rows are acquired in total ID order with NOWAIT before client/task resources; lock-set changes abort the whole operation. SQLite writers use an explicit BEGIN IMMEDIATE. PostgreSQL SQL and targets remain unexecuted in this candidate. Its planned two FORCE tenant policies are tenant isolation, not proof of an authenticated actor: the shared SQL app role can set GUCs. No progress/MFA capability or SECURITY DEFINER is introduced. Authentication, assignee scope and request hashes are enforced again in the service. Raw SQL actor fields do not become cryptographic signatures.

## HTTP and durability

The signed contract defines bounded pages, strict duplicate-free UTF-8 JSON, 8 KiB body reads, explicit confirmation and lowercase UUID idempotency keys. The server computes a canonical actor/gym/method/path/body hash. Stable cause hashes exclude moving now/cutoff values and creation checks current facts and qualification again. No client invents a hash. Fresh operation ACK and inert DTOs are captured before commit but emitted only after commit and owned-session cleanup. A failed or uncertain commit/close returns an opaque 503; there is no automatic retry or readback. An explicit identical replay is authorized again and returns only its durable operation ACK plus read_required, never a historical snapshot represented as current state.

Task, history and directory queries are bounded; metrics use America/Mexico_City and at most 62 observational dates. Counts mean persisted actor declarations. Completion does not prove contact, plan delivery, payment, renewal, clinical adherence or retention. Response overflow fails as a whole rather than truncating success.

The ROOT mount modifies exactly two lines in each real factory. The own-session adapter has no dependency finalizer that can commit after response headers. Exact API route shapes, /seguimiento and slash redirects are private on every status, including early 429, validation, auth, 405 and opaque 500. Neighbours and existing Google/GIS, retirement, MFA and diary policies are preserved.

## Preservation and pending work

All targets22-33 and historical helper/restore sources remain untouched. The new restore34 is a complete separate copy of restore33 with marked extension blocks; its inverse reconstructs the complete original LF text/AST, including all 67 assertions. Its added witness has four task states, six events, exact replay and neutral departed-worker history. It has not run against PostgreSQL. Expected 37 ORM / 38 physical / 28 FORCE and function/trigger counts are not global runtime facts until real PostgreSQL capture and replay.

ROOT QA17 fix8a5e is imported as exactly its google_link.py and new regression test blobs, with an import receipt. No documentary composition history or historical targets were copied. This adjacent accepted correction is identified separately from follow-up34 changes.

PostgreSQL55483 remains exclusively leased to QA33. This candidate makes no PostgreSQL connection, restore, Chrome, provider, deployment, performance or end-to-end R23 acceptance claim. The next phase must capture the real PostgreSQL34 target, exercise restricted NOSUPER/NOBYPASS/no-owner RLS, NOWAIT/role/assignment/source races, rollback and populated restore34. UI, QA and security acceptance follow separately.
