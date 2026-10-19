R25 revision32 ? scoped author handoff

Base: 5637b4daed86fa6ce3024c521aafdb6742373b08. Worktree: F:/mb-r25-progress32-20261019.
This is a backend candidate for independent QA and specific security review. No MAIN integration, UI acceptance, clinical validation, production recovery, delivery or operational claim.

Authority and data

Personal measures are explicit self-reports with declared units and a civil measured_on date. A legacy fecha remains only an unverified recording timestamp; no backfill invents measurement date or authorship. Existing legacy columns, notes and prior rows remain unchanged. The optional lean mass is reported, not calculated. Technical numeric bounds reject the whole request, not a clinical conclusion.

The new append-only ProgressConsent binds the exact link tuple, its observed version, an explicit personal source profile, selected categories and a data-date interval. Replacements and withdrawals append with exact id/version CAS under the persisted account lock. A withdrawn event never becomes a grant through account toggles or replacement links. An account OFF?ON with the same unchanged link and current consent may qualify again. Future consent data dates are allowed explicitly; actual data queries and reported measurements cannot be in the future. Queries cover at most62 inclusive civil days.

The direction is member?the exact gym team. OWNER/ADMIN/NUTRIOLOGO professional readers are revalidated from persisted membership, canonical parent/gym and a locked, fresh eligible subscription with the existing progresion_clientes right. The current catalog grants that right only to clinica; no catalog, price or grace was changed. Professional native history is a separate exact-gym projection, not a reciprocal member permission. VIEWER cannot read professional projections. There are no new professional mutations or MFA actions.

Own consent discovery/retirement is intentionally narrower than personal-space eligibility. A valid persisted active account with invitation_token IS NULL and current inclusive0..2147483647 SV can inspect its own event metadata and withdraw its own latest grant, even after becoming OWNER or losing source visibility. This cannot create a profile, grant, measurement or personal-space adoption; no hidden gym/contact/source lookup is used for the OWNER branch. Absence does not bootstrap an event. All other OWNER personal-space barriers remain.

Private source-reader mechanism (SEC acceptance pending)

1. The principal comes from actual authenticated factories. The service rereads/locks all required Usuario rows in total order with NOWAIT, canonical gym/parent/recipient, exact active Cliente/link, latest consent and eligible Subscription. The read transaction retains these locks until the inert result has been produced and its session closes.
2. The reader obtains the SAME physical Connection from that principal Session. It creates one explicit SAVEPOINT after authority locks. No second checkout or new source Session is needed with pool_size1/max_overflow0. An existing nested transaction is rejected.
3. Source identity is derived only from the locked link/consent tuple. Only inside this private scope does the reader set LOCAL app.current_tenant. GUCs identify context, not a signature or independent authority. There is no progress_actor authorization hook, SQL source-reading function, SECURITY DEFINER, bypass role or relaxed diary RLS. The trusted app role already can set existing tenant GUCs via SQL; this service adds no arbitrary SQL impersonation endpoint.
4. Core SQL selects only declared measure columns and counters. Source profile and data rows receive read locks. JSON byte length is checked through nested CASE BEFORE parsing; invalid, duplicate, oversized or structurally inconsistent content rejects the whole result. Only local_date/registered/completed/valid leave the aggregate query. No raw diary/food/notes/ORM/source Session/Connection escapes. Counts mean completed snapshots divided by registered snapshots, not four meals, inferred ingestion, adherence or a health result.
5. The reader explicitly restores current_tenant, verifies all three existing tenant/invitation/MFA GUC values and unchanged Session/Connection identity plus Python ContextVar, and then releases its SAVEPOINT. A failing SQL statement rolls back to the SAVEPOINT before any result is visible. If rollback/restoration cannot be confirmed, the connection is invalidated and the root operation fails visibly. No partial retry adopts another context.
6. Existing diary writes lock Usuario; new self-report and consent guards also lock the subject. Existing rows are SQL read-locked; an insertion ordered after an aggregate snapshot may appear in a later read. No cache is an authority. Concurrent withdrawal/new self-report against a paused authorized read returns busy without partial writes; a later successful withdrawal makes the old consent tuple fail.

Read/commit and export

GET uses a dedicated local Session without the global auto-commit finalizer. Writes capture bounded inert DTOs before one service-owned COMMIT and return only after its ACK. An uncertain commit returns503/progress_unconfirmed and requires exact-resource readback; no blind retry or false success. Body reading stops at8192 bytes before JSON parsing. Numeric epochs are rejected in JSON and date queries. Route errors and middleware families keep no-store/no-referrer.

Export adds only progress_consents as the eighth paged dataset before the personal-space early return. It exposes own scope metadata, no gym/client/user/contact data or raw sources. after_progress_consent is exact lowercase UUID; the seven historical cursors are unchanged. The section budget stays131072 bytes and the total becomes1064960. The exact wire-v1.json SHA982c26596daaf6a315661151ab8ad76bb42a61290dcec7bc6833e3c5aa7533a0 remains immutable.

Schema and preservation

Revision20261019_personal_progress follows31. It adds provenance to ClientProgress and one ProgressConsent table, bringing the physical contract to33 business tables/26 FORCE RLS families. Only32 targets are new. Twenty-eight prior targets/contract files in historical-contracts.json remain GitLF identical. No historical test was edited. Downgrade refuses destructive loss of authored measures or consent; empty rollback31 is tested. Startup rejects31 at current32 before upgrade.

The new populated restore copies the whole31 test. Removing the explicitly marked32 blocks and reversing the declared metadata-only pairs restores the ENTIRE historical test-function AST exactly:58 previous assertions remain and two32 assertions are added. The original31 source is unchanged. New fixtures use individually attributed UUID/OID leases and never FORCE DROP. Restoration compares full rows, signatures, policies, objects, prior26?31 markers/diary/links/recovery/MFA and new32 events/values/authority.

Validation and limits

See validation-summary.json for exact runs and overlapping scopes; counts must not be added as unique tests. Preliminary author runs were made during implementation and do not claim a cryptographic before/after source snapshot for their entire interval. The final source freeze identifies the candidate to be independently replayed. Installed89 distribution name/version metadata is recorded; it is not a hash of every runtime byte.

Actual32 PostgreSQL tests use a NOSUPER/NOBYPASS/NOCREATEDB/NOCREATEROLE application role with no table-owner membership and FORCE RLS. The first11 cases passed (6 actual-factory HTTP/pool1/context +5 migration cases). The adversarial suite passed8, then the two corrected fixture-date cases passed separately. Restore32 passed1 with two own databases. The final14 cases verify strict query ISO replay, bounded aggregate semantics and actual32 pool1 reads in both factories. All15 recorded own UUID leases are closed, and a later independent read-only catalog query found none of those exact names. No foreign DB/HBA/global-role changes, termination or external providers were used.

Preserved development findings and errata

- Initial actual32 HTTP had4 product reds: two valid aggregates were rejected due to an unqualified SQLite correlation alias, and two JSON measured_on=0 inputs were accepted as epochs. Their HTTP raw/JUnit and reader/schema preimages remain private and immutable; replay10 passed after alias/ISO corrections.
- A later strict-query check had2 actual HTTP reds: from=0&through=0 returned200. The same immutable tests now return422 via a before-coercion civil-date validator. Wire fields did not change.
- retirement_actor hardening had2 direct-service reds with a synthetic principal matching a deliberately persisted negative SV. This is helper hardening, not a demonstrated HTTP exploit or a new vulnerability ID. InclusiveMAX was already a positive control; bool/negative/out-of-range are rejected, no counter is decremented or wrapped.
- Four early adversarial failures were test-harness errors: an invalid catalog plan literal and a wrong DTO import. Two subsequent setup failures used date values in UTCDateTime. Same semantic assertions were retained; these are not product defects. The first restore launcher failed before any connection because Path.with_name received a slash. The next restore stopped on a new test expecting a SQL exception for a denied DELETE; RLS correctly returned zero rows, so the new test now requires rowcount0 and preserved data. One command used a wrong Temp directory and could not launch; no test or DB ran.
- The small auxiliary counts-causal.json was inadvertently overwritten by a later auxiliary probe. It is NOT claimed preserved, and no original RAW has been reconstructed from a transcript. Original HTTP failures and original reader code bytes remain intact; the overwritten auxiliary is excluded from the proof claim. Future receipts/probes are created exclusively; a live resource lease updates only its own originally exclusive identity.

Pending acceptance

Specific independent SEC review of the source-reader threat model, context restoration and all authority transitions; independent QA of32/restore/HTTP/negative races; UI composition and current32 CI transition. Archived/current31 acceptance remains separate and is not re-attributed to32. No broad suite or operational/clinical completion is claimed here.
