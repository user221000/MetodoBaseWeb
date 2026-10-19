# Author freeze 33: explicit Google subject association

This is author evidence for an isolated candidate based on fcfb55e. Independent
security/QA, UI composition, CI evolution, image/SBOM and real provider settings
remain separate. No mail, Google account, deployment, browser or VM was used.

The repair first reproduced the immutable eight SEC17 cases with the original
tokeninfo transport: four association failures and four controls. The same
eight passed after repairing association before replacing that transport.
Production now uses official google-auth 2.62.0, real signed RSA JWTs in tests
and a fixed JWKS transport. New current33 adapters retain all 17 SEC assertions,
eight MFA assertions and seven identity assertions, with only the documented
tokeninfo/JWKS metadata predicates mapped. Historical source files are intact.

Directed author results are recorded per artifact in `proofs/case-projections.json`;
they are not summed as unique criteria:

* Final92 SQLite/JWKS/business/cleanup/local-recovery batch: 68 passed.
* Stream bound plus actual PG pool1/no-lock/cleanup focus: six passed.
* Concurrent new signup: four passed, both factories and same/different emails
  for one subject; 200/409 and exactly one committed user and binding.
* Restored prior Google success audit plus close-failure checks: four passed.
* Final migrations and restricted-role guards: 13 passed (ten SQLite/PG
  migration criteria and three PostgreSQL guard criteria).
* Full populated restore33 plus the initial signup race: three passed. The
  restore itself passed with both UUID databases and all earlier contracts.
* Earlier service/race/onboarding runs and their failed initial attempts are
  listed separately; the logs stay private. No fresh full broad suite is claimed.

The last source has 35 application tables / 36 including alembic, 26 FORCE RLS
families and nine authentication/control-plane tables. Two of those tables are
new. There are two new PG trigger-only SECURITY INVOKER functions and two new PG
triggers; aggregate signed counts are 26 functions and 12 noninternal triggers.
SQLite adds four triggers. There is no new definer, RPC or GUC authority.
Direct calls to both trigger functions fail with 0A000, app ALTER OWNER and
identity/proof reassignment/deletion fail with 42501. Runtime attests the
function body, owner-relative-to-table, search_path and predecessor signatures.
DDL owner privileges remain separate from the application role.

All 50 baseline migration/target files are RAW unchanged. Six web-inclusive
locks append only three pinned/hashed distributions; every prior lock byte is
preserved as a prefix. GUI-only manifests/locks do not change. The shared WEB89
package/version set is unchanged. The private final environment is exactly its
89 versions plus google-auth, pyasn1 and pyasn1-modules (92), with pip check 0;
the initial 69-package environment is explicitly not that complete environment.
Syntax, F821 and reviewed Bandit checks passed (six existing findings, zero new).

The new restore33 copy reverses to the complete original32 module AST after
removing additive33 blocks and explicit version/table-count substitutions.
There are 60 assertions in the original test function (61 including its lease
fixture); 58/59 are literal matches and two map only revision/table count. The
old three-actor MFA oracle receives its explicit three-row projection, while a
complete four-credential set is independently exact and rejects any missing,
altered or extra original/new actor. No old helper or assertion is changed.

The HTTP fixture initially creates five Google refresh rows. The unchanged
source init_auth cleanup is observed over ALL refresh rows: five before, two
after, exactly the three revoked Google rows removed and no collateral row
change. It then seeds eight original recovery and three MFA rows, yielding 13
physical rows in the backup. Target startup cleanup is predicted separately.
Both original credential cohorts, all new associations/intents and private
objects remain in the full physical snapshot. Restored HTTP checks cover stable
subject despite changed email, other actor, revoked subject, pending intent
with exact original access, one-use confirmation, stale access and replay.

New Session cleanup models cover failure before/after close, commit/rollback
failure, and invalidate failure. A response is 503 before any success/proof
escapes. Only the owned Session is invalidated. If both cleanup primitives are
unavailable, the held test Session exposes exactly one bounded checkout, then
its own finalizer releases it; no shared engine is disposed. The login-success
audit block from the predecessor was restored, without provider/session secrets.

Thirty-one author33 leases are closed, each with OID/owner verification,
zero sessions before non-FORCE DROP and fresh absence. This says nothing about
old ambiguous31 residues or other agents' resources. No production database,
global role or HBA changed.

## Failed attempts and evidence limits

The RAW originals and saved source preimages remain in the protected private
archive identified by hash; public case projections never include credentials.
Failures are not retrospectively all attributed to product:

* The first JWKS mapping used an incorrect observer shape; its RAW log,
  harness preimage and source photos survive. Its XML path was reused by the
  corrected runner, so the original XML does **not** survive. The remaining
  `after-jwks.xml` is the later green result; it is not a reconstructed first run.
* Early HTTP ACK injection missed autoflush and an unbound-login fixture used
  a genuinely new email. Their RAW logs remain; later corrected setups retain
  the intended assertions. Not every exploratory XML survives those old fixed
  runner output paths; no complete RAW claim is made for them.
* Initial mapped contract setup lacked a fixture import; the first combined92
  invocation lacked the standalone SEC receipt coordinate. Both are preserved
  as setup/harness failures, followed by the same criteria under valid setup.
* The first SQL barrier shared a TestClient event loop. A separate causal probe
  recorded the same worker thread and timeout; two independent ASGI portals
  then exercised the actual UNIQUE race. No assertion was weakened.
* New cleanup tests found actual candidate defects: close-after-ACK originally
  produced 500; later tests found absent invalidation before release. Their
  failing logs/source preimages and the corrected same criteria are retained.
* First restore setup counted an extra pair emitted by registration. The next
  attempt expected revoked Google refresh rows that source init_auth had
  legitimately cleaned. Complete stage/cleanup witnesses now establish the
  exact five-to-two transition rather than hiding/deleting rows for an oracle.

`wire-v1.md` RAW hash45fdbf38 and adenda462ca784 remain immutable. Auth_time must
be enabled/configured with the real provider; GIS essential_claims is a string,
not an OIDC claims object or a freshness guarantee from account selection.
Unknown legacy Google-only continuity and real provider/image acceptance remain
open. Recovery28 does not recover an unknown historical subject.
