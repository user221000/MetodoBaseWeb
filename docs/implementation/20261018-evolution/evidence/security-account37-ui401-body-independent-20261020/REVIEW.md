QA-28 candidate d2 replay and residual401-header boundary

Candidate d2a96508fa6d4eac712d892ad92b7f4b2c75d51f is imported byte-exact
as7af030ad; only api.js changes product. The original five own canaries
remain byte-exact. Six original real HTTP cases now pass (both factories,
real MFA/cookie login, persisted SV invalidation, no refresh/replay). Twelve
original VM401 cases and six403/422 controls pass. Ten author DOM cases pass.

The companion keeps the original18-case source08de intact and checks an exact,
single reversible replacement of its late401 timing fixture. Three loop cases
delay arrival of the transport/headers instead of delaying the JSON body;
all actor/epoch assertions and scheduling actions are unchanged. These are
15 original cases plus3 explicitly adapted clocks, not18 literal replays.
The new POST behavior correctly never reads a401 JSON error body. The original
clock is therefore not an acceptance gate and its empty output is not PASS.

Six further own canaries deliver401 headers while explicitly blocking and
then draining the error body. Four GET authority reads (context, verify,
factorStatus and status) keep usable access until that body arrives:4 RED.
The two POST controls retire immediately:2 PASS. This is the remaining local
retirement edge of QA-28, not a server bypass or a new finding identifier.
Candidate d2 is not declared fully accepted while this criterion is reviewed.

Per-phase source/Node photos are quiet; the real HTTP gate additionally binds
Python/92 distributions and pip0/0. Only own tests/evidence and imported ROOT
product are touched in this isolated WT. No PG, Chrome, real provider or
delivery, Main edits, fullscan or global requirement closure is claimed.
