# Google subject binding, wire v1 (synthetic examples)

Revision33; local tokens remain the existing two-part payload/HMAC format.
Provider credentials are Google JWTs verified by google-auth2.62.0 against the
fixed HTTPS Google JWKS endpoint. No email match creates an existing-account
session or reauthentication proof. No payment association is reused.

## Login and new registration

`POST /api/auth/google` keeps `{credential, tipo?}` (tipo usuario/gym). A bound,
active issuer/sub resolves the persisted account and its current MFA/parent/SV.
Provider email never updates the contact or selects a different account. MFA
returns202 with the existing challenge; tokens follow only its real verification.
No factor returns the existing200 token pair after confirmed commits.

An unbound assertion with an already registered contact returns409
`google_link_required`, without tokens/proof/account adoption. A genuinely new
contact can create ONLY its new empty account and issuer/sub together. A
third-party/no-hd email is contact metadata, not a general verified-mailbox flag.
No existing Cliente, membership, subscriptions, plans or rights are adopted.
New gym defaults follow the ordinary registration contract. Concurrent contact
or subject collision returns409 `google_link_conflict` with no pair before ACK.
A revoked subject stays historically assigned to the same local account and
cannot create or select another user even if its provider email changed.

## Explicit link, authenticated exact access

`GET /api/auth/google/link/status?after=<lowercase UUID>` is read-only:
`{provider:"google",can_link:true,items:[{id,version,active,created_at,revoked_at}],next_after:null}`.
At most20 items, UUID keyset; no subject, provider credential or contact lookup.
`can_link` is false at exhausted local SV. Ordinary persisted identity gates
still apply. This never creates personal-space or professional authority.

`POST /api/auth/google/link/start`:
`{password:"new independent proof",google_credential:"Google JWT",code?:"6digits",recovery_code?:"22URLsafe"}`.
One factor input at most. Active MFA requires a distinct current TOTP or unused
recovery code, even if this access recently passed MFA. No factor is accepted
for an account without enabled MFA. Password is checked against the actor's
persisted local primary; neither a Google-created random hash nor an old access
claim substitutes for knowing it. Google must have a real auth_time <300s old,
with no iat fallback. Provider I/O holds no DB transaction/account locks.

Confirmed200: `{intent:"43URLsafe",expires_at:"UTC",provider:"google",google_email:"provider contact for explicit confirmation",confirmation_required:true}`.
The email is display-only. Intent is hash-only/durable, purpose google_link,
issuer/sub/actor/SV/factor-generation/exact-access bound, TTL min(300s,
Google-auth_time+300s, access.exp); no mutation extends it. Keep it only in RAM.
No principal/subject/local actor is accepted from the body. Same-owner explicit
relink of a revoked identity is allowed; cross-account reassignment never is.

`POST /api/auth/google/link/confirm`: `{intent:"43URLsafe",confirm:true}` under
EXACT same access. Confirmed200:
`{success:true,provider:"google",linked:true,reauthenticate:true}`.
One transaction consumes intent, publishes/relinks exact association, increments
SV and revokes refresh sessions, then ACK precedes response. No new tokens.
The consumer closes its old session and authenticates again. No automatic
retry, refresh/replay or implicit readback mutation after409/503. Another access,
SV, factor generation, expired/replayed token or wrong actor never consumes it.

## Explicit unlink

`POST /api/auth/google/link/unlink`:
`{identity_id:"observed lowercase UUID",expected_version:1,password:"fresh local proof",code?:"6digits",recovery_code?:"22URLsafe"}`.
Uses the same independent-password + current-factor rule. Password knowledge
is required before disabling Google, so a random unknown Google-only primary
cannot strand its user via an unrelated session. No email/Google-only fallback.
Confirmed200: `{success:true,provider:"google",identity_id:"observed UUID",version:2,linked:false,reauthenticate:true}`.
Revocation + version increment + audit + SV++/refresh revoke commit together.
Binding owner/issuer/sub/creation history never changes or deletes. Revoked
identity cannot login/reauth. Explicit same-owner relink increments its version
and preserves immutable owner/creation plus append audit history.

## Errors and privacy

Every exact link path (including slash redirect, all statuses/methods) has
no-store/no-referrer and fixed first-party CSP. Login/Google pages keep their
existing GIS policy; neighbouring paths gain no new privacy route authority.
All request parsers reject malformed/extra/duplicate/nonfinite evidence whole;
link JSON is stream-bounded32768 bytes. Never put passwords/JWT/intent/factors
in URLs, logs, analytics, DOM serialization, local/sessionStorage or snapshots.

401 google_link_verification_failed: independent primary unavailable/incorrect.
401 existing mfa_identity_unavailable: persisted identity/access is unavailable.
409 google_link_required: use an independent local login/recovery then explicit link.
409 google_link_conflict: unique collision or observed identity/version changed.
409 google_link_intent_unavailable: unavailable/stale/expired/different-session proof.
409 google_link_session_version_exhausted: no increment or consumption at MAX.
409 mfa_busy: whole transaction rolled back after account NOWAIT contention.
400 mfa_verification_failed: real factor failed; budget survives rollback.
422 mfa_invalid_input/google_link_invalid_input: reject whole command; no coercion.
429 mfa_throttled/google_link_throttled: actor+purpose/IP admission, no lock reset.
503 google_link_unconfirmed: commit/rollback/close uncertain; no claim of success.
501 Google not configured or401 google_identity_invalid: no fallback identity.
403 mfa_primary_reauthentication_required: Google auth_time absent/stale/future.

Durable actor admission10/300s per start/confirm/unlink precedes later work;
IP30/300s is shared/Redis fail-closed in production. Factor has existing durable
per-actor purposes too. No provider error, CAS rollback, new session or intent
resets a committed admission. All account locks use the existing global User
order/NOWAIT and revalidate canonical identity; app role remains restricted.

## Existing accounts and scope

Password reset28 keeps its own verification contract and does not disable MFA
or implicitly unlink Google. A valid restored LOCAL access may explicitly link
a newly verified subject; this does not recover or infer a historical unknown
Google sub. Legacy Google-only continuity with no stored sub stays unresolved;
no backfill/email adoption, real delivery or manual procedure is invented.
Lost factors/configuration are fail-closed. Retirement32 remains password-only.
No UI, live provider, email delivery, ASVS/AAL certification is claimed here.
