R25 backend contract proposed for review, before product/DDL
==========================================================

Base bd34893c4b6f806041b0cc6b7f156e9286886748. Migration32 is reserved for
this work only. No runtime/DB claim follows from this design. The rejected
CI31 candidate files and targets22-31 remain outside this change. PostgreSQL
has not been used; QA173 has priority. Root owns router mounting in api/app.py
and web/main_web.py and its observability package/middleware.

Direction and authority
-----------------------

The initial direction is MEMBER -> the exact linked gym team. No reciprocal
professional-history access is granted to the member. No personal profile is
adopted from the professional client, email, role history, row counts or timing.

Personal eligibility follows the existing R14 boundary: a persisted active,
not-deleted, non-invited account with a valid non-OWNER role and personal/member
context. Validate the canonical parent of a professional member as well.
An ambiguous usuario/OWNER does not gain a personal space. A legitimate gym
OWNER can still use existing R12 recipient features, without a new R25 personal
profile grant. Personal writes remain ordinary self operations, even when that
person is also an ADMIN/nutritionist in a professional team.

Professional reads require the current canonical gym and OWNER, ADMIN or
NUTRIOLOGO from persisted identity; VIEWER/unknown roles fail closed. The
effective gym comes only from this identity. Every professional resource query
also pins the route client and gym. Every recipient query pins link.user_id to
the actor, including a legitimate OWNER whose id is also a gym id.

There are NO new professional mutations in R25. No new role permissions or MFA
registry actions are introduced. Existing team/billing mutations keep their
exact MFA grants. Measurement/consent writes are ordinary personal operations;
withdrawal never requires an extra factor or action grant.

Measurements: reuse ClientProgress
----------------------------------

Do not change legacy id, gym_id, id_cliente, fecha, values or notas. Add fields:

* record_key: nullable UUID string, globally unique, explicit for new records.
* source_kind: legacy_unverified (default) or self_reported.
* measured_on: nullable Date; required only for new self reports.
* recorded_by_id: nullable FK Usuario RESTRICT, required self subject for new.
* recorded_at/updated_at: nullable UTCDateTime; new records use server UTC.
* version: Integer default1 with a bounded CAS, no authorship implication.
* withdrawn_at: nullable UTCDateTime, no automatic erasure or retention claim.

All historical rows remain legacy_unverified with the new source/date/author
fields NULL. fecha is merely the legacy stored timestamp, never backfilled as
a verified measurement date. New self reports set fecha to their recording
instant for old consumers while measured_on remains the explicitly reported
local measurement date. No clinically verified source, diagnosis or outcome.
Not even a valid historical number/date is silently converted to self_reported.

New inputs are finite strict numbers, reject bool/NaN/Infinity, and use the
existing weight20..300kg/body-fat3..60percent constraints. Optional lean mass
is an explicit self-reported kg value, finite, >0 and <=300kg as a technical
bound; it is not derived from other measurements. At least one value is
required. These are technical input constraints, not medical recommendations.
Only explicit values in their declared units are accepted; no unit guessing.
No notes or other health fields can be submitted through the R25 DTO.

The caller explicitly selects a source_profile_id. The server requires both
ClientProgress.gym_id==subject and Cliente.gym_id==subject plus exact profile
id and live Cliente. New writes do not call get_or_create_self_cliente. Missing
profile is an explicit setup state; multiple profiles are listed for explicit
selection, never silently chosen. Mixed-owner and deleted profiles fail closed.

New record_key is generated/retained by the client in memory before the first
PUT. expected_version0 creates; expected_versionN replaces the same existing
self report after exact ownership checks. A lost ACK is followed by GET of
the same key; blindly retrying creation with another UUID is not the contract.
Replay of expected_version0 after success is409, never a second record. A
withdraw operation increments version and records withdrawn_at, preserving
the stored data for the separate retention/deletion policy. Legacy rows are
read-only through new R25 mutation endpoints.

Consent: one append-only table, not a mutable boolean
----------------------------------------------------

progress_consents stores immutable events:
id(UUID), link_id, gym_id, client_id, user_id, version, link_version,
event(grant|withdraw), protocol(progress_share_v1), source_profile_id,
share_weight/share_body_fat/share_lean_mass/share_completion,
from_date, through_date(nullable means explicitly ongoing), created_atUTC.

Composite FK (link_id,gym_id,client_id,user_id) references the exact accepted
ClientAccountLink tuple, with RESTRICT. Composite FK (user_id,source_profile_id)
references Cliente(gym_id,id_cliente), RESTRICT; it is mandatory if any body
measurement is shared. Completion-only consent does not invent a profile link.
Unique(link_id,version); no UPDATE or DELETE from the app role. The latest
event is authoritative. Past grants remain historical events and are never
interpreted as current permissions. There is no automatic grant/default share.

CAS binds the latest event id+version and current link version, not a latest
lookup substituted for a caller's stale observation. Absent consent is virtual
idNULL/version0, with no GET write. Grant/replacement appends versionN+1 only
under the account/link locks; a withdrawal appends the next event. Overflow is
an explicit409. The text/protocol version and selected categories/date scope
are persisted. through_dateNULL requires explicit ongoing:true input, never
an omitted value that defaults to perpetual sharing. A fixed end and ongoing
are mutually exclusive. A grant requires the exact active accepted link,
canonical source gym, live professional client and selected personal profile.

Withdrawal requires only the legitimate personal actor, the latest own event
and CAS. It must still work if the source gym/client/link became inactive or
invisible. It copies the previous immutable link tuple, never reassigns it, and
does not require a source-owner eligibility check or additional MFA. An own
withdrawal can serialize using the actor/parent User locks and own consent
history without reading or adopting an inaccessible professional resource.

Each grant is effective only while it is latest, link is still active with
the same user/gym/client/version, current participants are eligible, its date
scope covers the request and the selected source profile is live. Reactivation
or a new link does not adopt a prior grant. A revoked link need not rewrite
the consent history: it immediately makes the previous grant ineffective.

Live minimal shared projection
------------------------------

NEVER grant the gym SELECT on personal_daily_logs or a personal tenant Session.
No raw diary row, meal names, food/macros, water, notes, contacts or plan bodies
are returned by R25 shared reads. No professional copy/cache is persisted.

Proposed narrow SECURITY INVOKER SQL accessor for PostgreSQL completion:

1. Require a verified, transaction-local app.progress_actor installed by the
   backend, the matching professional current_tenant, READ COMMITTED and a
   root transaction. Derive participants from link+latest consent, not arguments
   claiming a gym/user. Revalidate canonical roles, SV and exact versions under
   the locks. There is no SECURITY DEFINER, new role or BYPASSRLS.
2. Capture ALL settings that this accessor will touch. Scope source reads only
   to the derived recipient inside this audited function, then restore settings
   before return and in the exception path. Session.info and Python tenant
   context are never rebound; no source Session escapes. A failed restoration
   fails/aborts the transaction; no result is returned. Commit/rollback/pool
   begin hooks reset progress_actor, including residual session-level values.
3. Execute SQL aggregation ONLY: the bounded source text is checked before
   JSON parsing; return local_date, registered_snapshots, completed_snapshots,
   ratio and source/status. No raw JSON is selected into Python or returned by
   the function. No SELECT policy is broadened on the diary table. The function
   exposes no generic source id selector or arbitrary query entrypoint.
4. registered counts actual stored snapshots; completed counts their true
   completed flags. ratio=completed/registered; ratio is NULL with denominator0.
   An absent day is absent, not four prescribed/consumed meals or a fabricated
   adherence value. Water-only days can say no_registered_snapshots. Corrupt
   legacy JSON fails the whole relevant projection with a review error.

Measurement sharing likewise selects only consented valid numeric fields and
dates from the exact source_profile_id, never notes or nonconsented values.
Rows with no selected values are excluded. Shared output does not reveal
unselected event counts or use hidden fields to shape a graph. Legacy rows
remain visible only to the native owner context with unknown provenance;
they are not implicitly published as personal self reports.

The accessor is a design hypothesis requiring specific security review and
real PostgreSQL adversarial tests before acceptance. If context restoration or
bounded output cannot be established, it must be revised rather than granting
general diary RLS access or returning a cached substitute.

Lock/transaction protocol
-------------------------

Use persisted principal and SV at every request. All required Usuario ids
(actor, own parent, source gym, recipient and recipient parent) are acquired
in global id order with NOWAIT, before resources; revalidate the participant
set and associations afterwards. R12's existing client/link order is preserved:
lock the affected Cliente rows in a stable order, then exact link, then latest
consent; source measurement/day reads follow. New source writes use User ->
own Cliente -> measurement row. A withdrawn source/profile or changed scope
after lock acquisition rejects the operation. Direct guards fail closed on
NULL and enforce the same append/version/source-owner invariants.

Readonly GET acquires the required authorization/source locks and performs no
data DML/implicit bootstrap. A mutation owns one root transaction and one
confirmed commit. Build scalar response data before commit, return success
only after its ACK. Commit uncertainty or failed rollback returns503
progress_unconfirmed, no fabricated compensation or automatic retry. Logs
contain technical class/request correlation only, not measurement values,
notes, contact data, tokens or SQL exception parameters.

Wire proposal
-------------

All paths are mounted with /api by root in both real factories. New router
has bounded streaming JSON parsing, duplicate-key/nonfinite rejection, exact
private error headers/no-store/no-referrer for all statuses, opaque500/503.
No changes to auth endpoints or MFA grants are proposed.

Personal:

* GET /usuario/progreso/contexto -> today/timezone, eligible scope, paged own
  source profiles, capabilities. No profile/bootstrap write.
* GET /usuario/progreso/mediciones?source_profile_id&from&through&limit&cursor
  -> records, truthful date/source/units, next_after.
* GET /usuario/progreso/mediciones/{record_key} -> exact own self report.
* PUT /usuario/progreso/mediciones/{record_key} -> expected_version,
  source_profile_id, measured_on, values{peso_kg,grasa_corporal_pct,masa_magra_kg}.
* POST /usuario/progreso/mediciones/{record_key}/retirar -> expected_version.
* GET /usuario/progreso/completados?from&through -> observed days and explicit
  counts/ratio basis only, no foods/water or inferred prescribed meals.
* GET /usuario/vinculos/{link_id}/progreso/consentimiento -> latest own event
  (virtualNULL/0 if absent) and effective state; retained after revoked link.
* PUT same consent path -> expected_consent_id(nullable explicit),
  expected_version, expected_link_version, event:grant, source_profile_id,
  categories, from_date, through_date(nullable explicit), ongoing(bool),
  protocol:progress_share_v1.
* POST same path + /retirar -> expected_consent_id, expected_version. No source
  scope or actor is accepted from the body.

Professional readonly:

* GET /clientes/{client_id}/progreso -> native gym/client history, minimum
  numeric data/provenance, no notes. No new member access to this history.
* GET /clientes/{client_id}/vinculacion/{link_id}/progreso/contexto -> latest
  minimum consent state/capabilities, no private metric data without grant.
* GET same path without /contexto -> expected_link_version,
  expected_consent_id/version, date range and bounded cursor; returns only
  selected self-report fields and/or observed completion counters.

Dates are ISO civil dates in America/Mexico_City, instants UTC. Bootstrap GET
returns server today; a missing from+through defaults to the latest30 civil
days. Only one bound is422; queries max62 days and future data is rejected.
Measurements page max100; response budget256KiB, JSON body8KiB. A changed
cursor filter/scope does not grant access; all queries repeat authority.
No interpolation, invented zero, target attainment or clinical conclusion.

Errors: progress_identity_unavailable401, progress_context_requires_review409,
progress_permission_denied403, progress_source_unavailable404,
progress_version_conflict409 (own authorized current_version only),
progress_version_overflow409, progress_consent_unavailable404,
progress_scope_changed409, progress_source_requires_review409,
progress_invalid_input422, progress_volume_limit413, progress_busy409,
progress_unconfirmed503. Foreign/missing resources are opaque and equal.

Export and migration32
----------------------

Existing measurements export keeps its integer cursor and gains explicit
source/date/version metadata. Add one own-only progress_consents dataset with
UUID after_progress_consent cursor, including immutable grant/withdraw scope
metadata only. No professional portfolio data, other recipients or contacts.
This is an additive eighth dataset; declare updated coverage/budget and
coordinate the strict frontend export consumer before integration. Do not call
the seven-dataset UI complete for32 without that adaptation.

Migration32: strict31 preflight; additive ClientProgress columns/defaults and
the one append-only consent table with composite RESTRICT FKs, indexes/CHECKs,
FORCE RLS, precise guards and narrow invoker accessor. Preserve legacy values,
dates, notes, RLS policies and targets22-31. New target32 includes all existing
security/physical contracts plus the new functions/table/guards. No create_all
or stamp in runtime. Rollback must refuse nonempty32-specific authored/consent
data rather than silently dropping it; empty safe rollback restores31 exactly.
Restore32 is a new populated test, never a retargeted31 restore.

Proposed source ownership
-------------------------

New domain/schema/router/service modules for personal_progress/progress_share;
models.py; migration20261019_personal_progress.py; new progress_policy/security
contract and target32; schema_control expected-head registry; focused
ClientProgress/consent guards. Focal tenant-engine hook addition only to install
and reset progress_actor, without changing existing tenant/MFA semantics.
Focal privacy_export and its route DTO/cursor, client-link capability fields
after coordinating their exact helpers, security_headers/progress_paths for
new exact privacy family. No auth, MFA31, ledger, prices, CI or observability
source changes. Root mounts the new router and coordinates export UI.

Acceptance plan, not executed
-----------------------------

Baseline actual missing routes/consent capabilities, not ModuleNotFound called
a security failure. Domain and actual register/login HTTP in both factories;
no session-token mint as acceptance, no dependency/MFA bypass. Own/profile,
role/parent/invitation/SV and two-tenant negatives. Exact consent id/version,
date/category/source-profile scope, append-only revisions, no reciprocal share.
Withdraw while source gym/link inactive; no cached access after withdrawal.
Real restricted PostgreSQL: actorA/B/null, direct raw diary deny, all GUCs
restored after success/error/rollback/savepoint/reused pool1/poolexhaustion,
NOWAIT/cross-owner compatibility, reader/withdraw/source-update races. No raw
row/food/notas can escape the accessor. Readonly inventory RR stays unaffected.
Empty/populated31->32, rerun/idempotence, reject drift and unsafe downgrade,
safe rollback31, populated restore32 and complete structural/security/index
signatures. Peer QA/security and UI acceptance remain separate gates.
