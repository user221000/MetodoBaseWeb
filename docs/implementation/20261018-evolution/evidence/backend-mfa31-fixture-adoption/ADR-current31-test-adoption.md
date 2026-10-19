Current31 fixture adoption and authorization precedence
======================================================

Scope
-----

This isolated branch starts at 913cb66061ac754ad09344fc24e8f769b5722997.
It changes tests only. Application code, migration31, targets22-31, historical
fixture helpers, conftest.py, CI and browser fixtures remain unchanged.

The coordinator's immutable diagnostic stopped at20 failures:92 executed,
72 passed and20 failed, all first failures in test_team_invitation_contract.
This was not the result of the complete selected suite. Exact original
artifacts were copied to the author's private Temp directory and hashed;
only scanned projections and safe metadata are published here.

Cause and adoption
------------------

The old team fixture substituted get_usuario_actual with a mutable dictionary
and supplied no Authorization header. The real current31 business adapter
therefore failed at the missing bearer check with mfa_identity_unavailable,
before evaluating a grant. It also used its own SQLite engine and partial
settings object: those static fixture assumptions were incompatible with
coherent primary authentication, factor configuration and business sessions.
They are not described as independently reproduced product defects.

The opt-in MfaContractClient now performs the real password login, recent
primary reauthentication, enrollment, TOTP confirmation and recovery-code
login. Seed/kit/pairs stay in RAM; helper assertion messages never print them.
Only a known persisted synthetic account and its actual password can enroll.
Identity is resolved by the normal bearer dependency, without auth/MFA
overrides. Separate encryption-key configuration is synthetic, not a factor
bypass. No clock, MFA service, permission checker or business operation is
patched. The existing email transport remains captured/offline.

Before each protected action the helper requests a fresh exact method, path,
body and optional Idempotency-Key grant. It always sends the original real
mutation, including after an issue rejection. It never returns an issue
response as if it were the business response, retries a business mutation,
refreshes a failed session, or alters a resource to make a grant valid.
Cached account tokens are restored only on an explicit fixture actor switch;
the backend still checks persisted SV/role on every request.

The adaptation is local to team_case and the entitlement module's fixture.
The ordinary conftest primary-only clients keep their previous behavior,
verified by a negative control requiring MFA enrollment for the billing portal.
The admin seed now has an actual known password instead of the unusable
"unused" placeholder. Roles, parent associations and business assertions are
unchanged.

The diary change is setup only in the one existing membership-revocation
test: its Web OWNER obtains real MFA and an exact revoke grant. The API branch
still exercises the existing service because that factory does not mount team
management. The diary fixture and all original diary assertions are intact.

Intentional HTTP31 precedence
----------------------------

The current31 MFA authorizer validates the scoped target before the business
router reaches _target. Consequently role/remove/resend against another gym
now return403 mfa_action_forbidden, rather than the historical30 _target404.
The coordinator approved exactly those three parameterized expectations after
the original three reds and a causal matrix were preserved.

There is one changed source Assert node, parameterized over three actions.
Of110 original team/entitlement Assert nodes,109 remain exact AST matches;
the changed node is exactly404 to403. All test function names and parameter
IDs remain. Additional checks require the exact error code, equal foreign and
missing-resource responses, intact foreign state and no new action grant.
The original current30 source/preimage still asserts404. No historical30
criterion or archived runtime is rewritten to claim31 compatibility.

The independent-of-business causal matrix covers all three actions with:

* A legitimate owner and a grant for its own resource used against another.
* A denied foreign issue followed by the actual mutation without capability.
* An actual foreign mutation with no grant.

Foreign and missing targets return equal403 bodies in every mode. No foreign
email/name/owner leaks in the body; membership, role, SV and invitation digest
remain unchanged. A capability issued for the owner's resource remains unused.
No email or other side-effect port is invoked. These are author checks,
pending independent QA review; they do not claim operational MFA completion.

Inventory limits
----------------

Affected and adopted: team invitation contracts, team entitlement review and
the Web membership-revocation case in the personal-diary security review.

The diagnostic's auth/billing modules passed their69 cases without adaptation;
the other3 of its72 passes were standalone team tests. The RBAC module is pure
permission/hierarchy evaluation.
The API team/private-plan storage review mutates plan generation, not the
newly protected team/billing actions. Redis/rate boundary fixtures deliberately
test rejection before auth and need no enrollment. These modules were read;
no general fixture or their assertions were changed by this branch.

The old team full-stack browser fixture also predates current31 enrollment;
that is a separate current31 browser/CI adoption, not tested or edited here.
No PostgreSQL, Chrome, real provider or email was used in this task.

Evidence handling
-----------------

Private raw logs/XML are retained with hashes. Public projections are scanned
for signed two-part tokens, timestamp.token.signature CSRF values, otpauth URIs
and labeled opaque capabilities. A scanner is a bounded publication control,
not a general guarantee of secret detection. Helper errors avoid dumping
authentication responses in the first place. Actual scans recorded zero
substitutions for the published test outputs. RAW evidence has * -text from
creation; normal source code retains GitLF normalization with both hashes.
