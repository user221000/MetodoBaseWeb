# Own consent retirement, wire v1

These two public POST operations prove the account again for every call. They
return no access/refresh token, login challenge, action grant or personal-space
authority. General login, account recovery and their parent eligibility checks
are unchanged. No schema/policy/target changes are made.

## Requests

`POST /api/auth/progress-retirement/metadata`:

```json
{"primary":{"method":"password","email":"synthetic@example.invalid","password":"Example only, not a credential"},"limit":50,"after":null}
```

Optional `factor` is exactly `{"code":"123456"}` or
`{"recovery_code":"SYNTHETIC_ONLY_EXAMPLE"}`; the actual recovery value must be
22 URL-safe ASCII characters. Both examples are synthetic, never a real proof.
When an existing factor is active, one such factor is mandatory. An enrollment
confirmation or previous operation may have already consumed the current TOTP.
Each page consumes a distinct current TOTP or unused recovery code. No factor
is accepted for an account without an active factor.

`POST /api/auth/progress-retirement/withdraw`:

```json
{"primary":{"method":"password","email":"synthetic@example.invalid","password":"Example only, not a credential"},"link_id":"11111111-1111-4111-8111-111111111111","expected_consent_id":"22222222-2222-4222-8222-222222222222","expected_version":1}
```

The same optional factor field applies. IDs are lowercase canonical UUIDs;
versions are integers 1..2147483647, never bool. No source, gym, actor, profile,
scope tuple, grant event or access token is accepted in either body. Unknown
fields, duplicate JSON keys, nonfinite JSON and malformed input are rejected
whole. The stream is bounded to8192 bytes before parsing. POST JSON only.

## Responses

Metadata200, synthetic full shape:

```json
{"scope":"own_consent_retirement_only","items":[{"link_id":"11111111-1111-4111-8111-111111111111","consent":{"id":"22222222-2222-4222-8222-222222222222","version":1,"event":"grant","protocol":"progress_share_v1","link_version":2,"categories":{"weight":false,"body_fat":false,"lean_mass":false,"completion":true},"from_date":"2026-10-01","through_date":null,"ongoing":true,"created_at":"2026-10-19T12:00:00+00:00"},"capabilities":{"withdraw":true,"grant":false}}],"next_after":null}
```

`limit`1..100 (default50). `after` is the last observed lowercase `link_id`,
strictly greater SQL keyset. Only the latest event for each own link appears,
including a withdrawn event or an ineffective/hidden source. No source lookup,
recipient contact, professional name, profile ID, measurements or diary data is
returned. Empty history is200 with `items:[]` and `next_after:null`; it creates
no consent event. Capability never means personal-space or grant permission.

Withdrawal200:

```json
{"scope":"own_consent_retirement_only","link_id":"11111111-1111-4111-8111-111111111111","consent":{"id":"33333333-3333-4333-8333-333333333333","version":2,"event":"withdraw","protocol":"progress_share_v1","link_version":2,"categories":{"weight":false,"body_fat":false,"lean_mass":false,"completion":true},"from_date":"2026-10-01","through_date":null,"ongoing":true,"created_at":"2026-10-19T12:01:00+00:00"},"capabilities":{"withdraw":false,"grant":false},"effective":false}
```

The exact existing latest grant is copied server-side into one append-only
withdraw event. Absence never creates a scope. A replacement or already
withdrawn scope conflicts. No automatic retry, latest substitution or regrant.

## Errors and UX

`detail` is `{code,message}`. Primary failures, inactive/deleted/invited account,
wrong password and unknown account use401
`progress_retirement_verification_failed`. Invalid/reused factor is also401;
an unavailable existing factor key is503 `mfa_service_unavailable`.
Conflicts retain existing codes:404 `progress_consent_unavailable`,409
`progress_version_conflict`/`progress_scope_changed`/`progress_version_overflow`.
Content errors use413/415/422 with existing `progress_*` codes. Admission uses429
`progress_retirement_throttled`; Redis uncertainty is503
`rate_limit_backend_unavailable`. Account contention is409
`progress_retirement_busy`. Commit/rollback uncertainty is503
`progress_retirement_unconfirmed`: do not show success, retry or reuse a factor;
ask for another explicit metadata read with a new valid factor. A lost ACK can
mean the original operation already committed.

All statuses and slash redirects on these exact paths use no-store,
no-referrer and the fixed first-party CSP. No secrets in URL, Storage, DOM
serialization, telemetry or logs. Primary/factor inputs live only in the form
operation and are cleared on completion/error/close/account change. The API
does not require or refresh a general bearer, and supplies no session event.

## Authority and budget

Password-only primary verification is admitted. Google inputs are fail-closed
503 `progress_retirement_primary_unavailable`, without a provider call or email
fallback. Current Google login uses its fixed verified-provider transport;
this work does not allege a signature bypass. There is no persisted provider
subject association authorizing this exceptional purpose. Google-only accounts
and loss of all factors still require a separately reviewed recovery process.

An active, nondeleted account with invitation_token IS NULL and integer SV
0..MAX is reloaded under NOWAIT lock. Its role is valid; OWNER, including
ambiguous personal-space identities, gets only own immutable consent metadata
and retirement. Parent availability is ignored solely here. No SV/factor/role/
team/password mutation is performed. Actor IDs are never accepted from input.

IP30/300s and normalized-account-HMAC10/300s admission is shared by both paths;
production requires Redis and fails closed on outage. A separate confirmed
database admission under the actor lock records at most10 attempts/300s before
the operation transaction, including primary/MFA/CAS/rollback failures. It is
not primary proof or a portable capability. The next transaction verifies the
current password/SV under lock, installs its own subject/MFA context, and
confirms factor consumption, minimal audit and query/withdrawal in one commit.
Only a primitive DTO captured before commit is returned after its ACK.

Wire freeze is a contract handoff, not runtime/security/QA acceptance.
