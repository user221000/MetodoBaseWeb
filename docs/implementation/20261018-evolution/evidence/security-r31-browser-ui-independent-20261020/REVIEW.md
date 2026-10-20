Independent R31 browser frontend security review

Source: 8878d64ccb8975726dadc482e948f1a6e0b90d23. Product was read only.
26 independent VM cases passed, repeated under a source/package/binary quiet gate.
The two executions cover the same 26 cases and are not 52 unique requirements.
Four exact private source mutations were rejected: unseen epoch checks, captured
cookie body, refresh JSON exclusion and authentic single-use acknowledgement.
The independent harness imports only the actual api.js, not the author harness.

Review confirmed RAM-only access and identity metadata, immediate legacy key
purge before migration, a nonsecret UUID-only epoch channel, cookie mutations
serialized through response JSON, no fabricated/replayed acknowledgement, old
tab invalidation without identity adoption, and no refresh/replay for exact-access
nutrition/followup requests. Late JSON, hidden/restored pages and uncertain refresh
are fenced before access or old private results can be exposed. Public recovery
contains no authentication bootstrap and uses a separate fragment-in-RAM flow.
Session shell clears remaining legacy sensitive DOM after owners clear secrets in
the same event/microtask turn; shown-once MFA kits remain subject to their owner.

No additional confirmed security defect was found in this bounded review.
Acceptance is limited to reviewed source and VM transport/Storage/Lock doubles.
It does not prove native browser storage/network behavior, server semantics,
PostgreSQL isolation, production deployment, or completion of R31 retention work.
