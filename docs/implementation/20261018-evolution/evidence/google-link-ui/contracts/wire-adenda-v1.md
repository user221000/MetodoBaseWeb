# Wire v1 precision, without rewriting the original RAW

Original wire SHA256: 45fdbf38cd98d462c88852ab95036ba9e2ce702a2e7116e849f701551c208b5b.

Only the new link command DTOs forbid extra fields. `/api/auth/google` preserves
the old onboarding contract: unknown legacy id/gym_id fields are ignored, never
authority. Its JSON is nevertheless stream bounded to32768 bytes, rejects
duplicate/nonfinite values, and the credential is bounded to16384 characters.

The only new SSR is `/cuenta/google` and its slash variant. It has no-store and
no-referrer at every status and fixed minimal GIS CSP: first-party plus only
accounts.google.com/gsi/client script, /gsi/style style and /gsi/ connect/frame;
nonce for bootstrap, no unsafe-inline/CDN or arbitrary downstream policy. The
exact API link paths keep the closed first-party policy. Existing login pages
keep their GIS policies. Actual GIS configuration/browser/provider acceptance
remain external gates.

Fresh Google primary requires real auth_time requested via supported GIS
`essential_claims: 'auth_time'` and enabled provider configuration. A fresh iat,
select_account or consent prompt does not prove fresh authentication. Missing,
old, invalid or future auth_time fails closed even for a correct bound subject.

Production verification uses google-auth2.62.0 and already pinned PyJWT2.15.1:
verify_token with the fixed HTTPS Google JWKS URL. Its2.62.0 source constructs
PyJWKSet from fetched JSON, without a second PyJWKClient network fetch. The
adapter rejects other URLs/methods. Keys are stream bounded131072 bytes with
timeout10s/no redirects before library parsing. No credential/sub/kid selects
an endpoint. Issuer accepts accounts.google.com or https://accounts.google.com
and persists the latter. Original SEC8 first passed unchanged using tokeninfo,
so association correction precedes the library transition. Final mapping uses
signed JWTs and JWKS, changing only provider/credential/current-schema seams
and truthful transport predicate/URL; business expectations remain intact.

Binding owner/issuer/sub/creation remain unchanged. Explicit revoke and
same-owner relink increment the binding version and append audit events keyed
by identity ID/version. Password reset or email changes never implicitly
transfer, revoke or relink a subject. A revoked subject assigned to another
user stays unavailable regardless of a newly matching contact email.

New APIs close their Session before returning a response. Admission commits
separately; start consumes the current factor with its confirmed intent.
Confirm consumes only that intent, not a second OTP. Unlink always needs a new
independent password and current factor. Commit/rollback/close uncertainty
returns503 without proof, token or success.
