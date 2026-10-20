QA-28: account37 retains stale local account after a real HTTP401

Independent review of c91a18bbb7a21cc92616574280ec61959fd8caa5. Product
was not edited. Three immutable own canary files are bound by manifest hashes.

Definitive HTTP gate: six failures, zero errors/skips, both API and SaaS
factories, three operations (status, email request and password change). Each
uses real registration, enrollment/TOTP confirmation, recovery login and a
browser HttpOnly session. The owned SQLite record advances session_version
from1 to2 immediately before the target HTTP call. For password this occurs
after successful real primary reauthentication. Every target correctly returns
401 exactly once. No automatic refresh or replay occurs; original password
remains valid and proposed password is not committed. Nonetheless RAM access
and controller context remain active. Email/password retain both old account
projections; status already removes its projections but keeps the stale access
and context. This is local retirement/privacy behavior, not a server bypass.

Independent VM gate: six401 failures (API and controller for all three
operations), six separate403/422 controls pass and retain valid local access.
These controls are typed transport doubles, not six additional HTTP controls.
Wrong-primary-password401 on the MFA reauthentication endpoint is distinct
from a persisted-identity401 on an own-account resource and must remain a
correctable primary rejection. A late old401 must never clear a newer actor.

The earlier exploratory HTTP capture contains four confirmed failures and two
IPC concurrency failures during parallel status reads. Its original worker and
RAW outputs are preserved privately; only the final drained six-case gate is
the definitive HTTP evidence. Python/92 distributions/pip0/0 and all1170
inventoried source files remained quiet during that gate. The VM gate also
binds the Node binary. No PostgreSQL, native browser, real provider, external
delivery, Main edit, full secret scan or global requirement closure is claimed.
