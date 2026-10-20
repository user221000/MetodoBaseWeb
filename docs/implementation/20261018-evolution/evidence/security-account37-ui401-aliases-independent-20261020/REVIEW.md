Additional QA-28 alias canaries and independent UI boundaries

Product c91a18bbb7a21cc92616574280ec61959fd8caa5 is unchanged.
Six additional VM canaries fail for own-account context, factorStatus and
verify aliases (API and controller). A typed resource401 keeps the exact
old access and context. These are the same local retirement defect as the
six real HTTP failures in ffee085f; they are not six more real HTTP cases.
The intended fix belongs to accountSecurity wrappers. Wrong-primary401
from mfa.reauth remains correctable and must not revoke a valid actor.

Eighteen separate own independent VM/minimal DOM boundaries pass: full
ACK shared lock, queued refresh fence, body capture before lock and
primary await, late401 after genuine newer login for the unlocked status
read, late401 preserving an external epoch for both locked POSTs, wrong
primary401, Storage fail-closed, network/JSON/ACK uncertainty without a
server revocation claim, opaque private errors, and six GIS intent cases.
GIS checks cover per-view nonce, fresh state after cancel, edited intent,
single-use callback dispatch, pagehide and session boundary. SDK, Storage,
WebLock and transport are doubles; no native/provider acceptance is claimed.
No product, PG, Chrome, Main, fullscan or whole-requirement closure change.
The three initial QA-28 canaries and original proof receipt remain unchanged.
