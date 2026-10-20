Independent account security37 review: bounded SQLite/HTTP acceptance

Product25ec3ced246f50e8d067c6129853f421c266c811 was not edited. Twenty
independent cases pass first, then the same twenty unchanged plus four explicit
contact/foreign-actor cases pass:24 distinct cases, not44 unique requirements.
Each phase has quiet sources,92 distributions, Python binaries and pip0/0.
Three new test modules have0 Ruff diagnostics. No new confirmed defect was found.

Checks cover non-interchangeability of email and primary purpose proofs; binding
to one exact valid signed access even for the same persisted subject; expiry;
password/factor/proof/session atomicity under both pre-commit failure and commit
ACK loss; current recovery methods and factor continuity; failed-factor durable
budget without consuming primary/contact evidence; and owned Session close
failure never returning an acknowledgement or sending mail after issue.

Actual real SaaS/API factories exercise54 rejected header/Origin/content/query
probes, all with0 SQL and0 optional token verification before rejection. Unexpected
status/confirmation/password errors are opaque private503 and no success claim.
BearerB plus contact proofA confirms onlyA contact evidence, retaining B identity,
cookies, password/SV/roles/context/refresh/factor state and A authentication state.
Public GET cannot consume/echo a valid proof. Both pending and already-confirmed
A-to-B-to-A contact histories require a fresh proof for the advanced epoch.

The stronger recovery tests use real enrollment/TOTP confirmation and recovery
login service protocols, not injected MFA state or dependency overrides. Email
transport is synthetic only. Public script source reads only a fragment, cleans
history before interaction, retains proof in RAM and explicitly submits with
credentials omitted; it contains no Api bootstrap, identity or Storage access.

Acceptance is bounded to these sources, SQLite and TestClient/service protocols.
No PostgreSQL37 lease, restricted-role physical behavior, restore37, authenticated
UI/native browser, real provider acceptance/delivery or deployment is proved.
Existing MFA locking/authority primitives and historical fixtures are unchanged.
The inherited public registration/Bearer QA26 issue is separately under ROOT
review; this receipt does not close it or all of R16/R31/R32.
